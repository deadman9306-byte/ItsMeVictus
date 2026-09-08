"""
proxy_loader.py — load and validate proxies from proxies/proxies.txt

Supported line formats:
  socks5://host:port
  socks5://user:pass@host:port
  host:port                      (assumed socks5, no auth)
  host:port:user:pass            (assumed socks5, with auth)
"""

import os
import socket
import struct
import logging
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

PROXY_FILE = os.path.join(os.path.dirname(__file__), 'proxies', 'proxies.txt')
TEST_TIMEOUT = 3   # seconds per proxy test


# ── Parsing ───────────────────────────────────────────────────────────────────

def _normalise(line: str) -> str | None:
    """Convert any supported format to socks5://[user:pass@]host:port."""
    line = line.strip()
    if not line or line.startswith('#'):
        return None

    # Already has a scheme
    if '://' in line:
        return line if line.startswith('socks5://') else None

    parts = line.split(':')

    if len(parts) == 2:
        # host:port
        return f'socks5://{parts[0]}:{parts[1]}'

    if len(parts) == 4:
        # host:port:user:pass
        host, port, user, pw = parts
        return f'socks5://{user}:{pw}@{host}:{port}'

    return None


def load_proxies() -> list[str]:
    """Read proxies/proxies.txt and return a list of normalised proxy URLs."""
    if not os.path.exists(PROXY_FILE):
        logger.warning(f"Proxy file not found: {PROXY_FILE}")
        return []

    proxies = []
    with open(PROXY_FILE) as f:
        for line in f:
            url = _normalise(line)
            if url:
                proxies.append(url)

    logger.info(f"Loaded {len(proxies)} proxies from file")
    return proxies


# ── Testing ───────────────────────────────────────────────────────────────────

def _test_one(proxy_url: str) -> tuple[str, bool, str]:
    """
    Try SOCKS5 handshake + UDP ASSOCIATE.
    Returns (proxy_url, ok, reason).
    """
    try:
        p          = urlparse(proxy_url)
        proxy_host = p.hostname
        proxy_port = p.port or 1080
        username   = p.username
        password   = p.password

        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.settimeout(TEST_TIMEOUT)
        tcp.connect((proxy_host, proxy_port))

        # Greeting
        tcp.sendall(b'\x05\x01\x02' if username else b'\x05\x01\x00')
        resp = tcp.recv(2)
        if len(resp) < 2 or resp[0] != 5:
            tcp.close()
            return proxy_url, False, 'not SOCKS5'

        if resp[1] == 0x02:
            creds = (bytes([1, len(username)]) + username.encode() +
                     bytes([len(password)]) + password.encode())
            tcp.sendall(creds)
            ar = tcp.recv(2)
            if ar[1] != 0:
                tcp.close()
                return proxy_url, False, 'auth failed'
        elif resp[1] != 0x00:
            tcp.close()
            return proxy_url, False, f'unsupported auth {resp[1]}'

        # UDP ASSOCIATE
        tcp.sendall(b'\x05\x03\x00\x01\x00\x00\x00\x00\x00\x00')
        resp = tcp.recv(10)
        tcp.close()

        if len(resp) < 2 or resp[1] != 0:
            return proxy_url, False, f'UDP ASSOCIATE failed (code {resp[1] if len(resp)>1 else "?"})'

        return proxy_url, True, 'ok'

    except Exception as e:
        return proxy_url, False, str(e)


def test_proxies(proxies: list[str], max_workers: int = 50) -> dict:
    """
    Test all proxies in parallel.
    Returns:
        {
            'total':   int,
            'working': int,
            'failed':  int,
            'proxies': [proxy_url, ...],   # only working ones
            'details': [{'proxy': ..., 'ok': bool, 'reason': str}, ...]
        }
    """
    if not proxies:
        return {'total': 0, 'working': 0, 'failed': 0, 'proxies': [], 'details': []}

    results  = []
    working  = []

    with ThreadPoolExecutor(max_workers=min(max_workers, len(proxies), 300)) as pool:
        futures = {pool.submit(_test_one, p): p for p in proxies}
        for fut in as_completed(futures):
            url, ok, reason = fut.result()
            results.append({'proxy': url, 'ok': ok, 'reason': reason})
            if ok:
                working.append(url)

    return {
        'total':   len(proxies),
        'working': len(working),
        'failed':  len(proxies) - len(working),
        'proxies': working,
        'details': results,
    }
