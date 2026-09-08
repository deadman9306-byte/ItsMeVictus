"""
Config B — settings for Method B (randomised UDP flood).
"""

# ── Packet size range (randomised per packet) ─────────────────────────────────
B_MIN_PACKET_SIZE = 64
B_MAX_PACKET_SIZE = 2000

# ── Delay range between packets in seconds (randomised per packet) ────────────
B_MIN_DELAY = 0.0  # 0 ms  (no delay)
B_MAX_DELAY = 0.00  # 10 ms (max delay)

# ── Port range (randomised per packet) ────────────────────────────────────────
B_MIN_PORT = 1
B_MAX_PORT = 100
