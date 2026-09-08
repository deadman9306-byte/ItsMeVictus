"""
Global configuration — all tuneable values live here.
"""

import socket

# ── Server ────────────────────────────────────────────────────────────────────
API_PORT = 5000

# ── Packet limits ─────────────────────────────────────────────────────────────
MAX_PACKET_SIZE = 65507
MIN_PACKET_SIZE = 64
DEFAULT_PACKET_SIZE = 1400
DEFAULT_DURATION = 999999

# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL   = "https://YOUR_PROJECT.supabase.co"
SUPABASE_KEY   = "YOUR_SERVICE_ROLE_KEY"
SUPABASE_TABLE = "YOUR_TABLE_NAME"

# ── Linux socket optimisations ────────────────────────────────────────────────
try:
    USE_SENDMMSG = hasattr(socket, "sendmmsg")
except Exception:
    USE_SENDMMSG = False

SO_REUSEPORT = 15
SEND_BUFFER = 8_000_000  # 8 MB SO_SNDBUF
