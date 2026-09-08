"""
Method registry.

Each method module must expose a `worker(args: WorkerArgs)` function
that runs inside a multiprocessing.Process.

To add a new method:
  1. Create methods/your_method.py and implement `worker(args)`
  2. Import it here and add it to METHODS with the next integer key.
"""

from methods.udp_flood   import worker as _udp_worker
from methods.udp_flood_b import worker as _udp_worker_b

# method_id (int) → worker function
METHODS: dict[int, callable] = {
    1: _udp_worker,
    2: _udp_worker_b,
}

DEFAULT_METHOD = 1


def get_worker(method_id: int):
    """Return the worker callable for a method ID, or raise ValueError."""
    if method_id not in METHODS:
        raise ValueError(
            f"Unknown method {method_id}. Available: {list(METHODS.keys())}"
        )
    return METHODS[method_id]


def list_methods() -> dict:
    """Return a human-readable map of available methods."""
    return {
        1: "UDP Flood — fixed packet size, max speed, optional sendmmsg batching",
        2: "UDP Flood B — random port + random packet size + random delay per packet (configb.py)",
    }
