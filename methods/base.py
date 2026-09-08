"""
Shared worker utilities and the WorkerArgs dataclass.
All method workers receive a WorkerArgs instance as their only argument.
"""

import multiprocessing as mp
from dataclasses import dataclass


@dataclass
class WorkerArgs:
    worker_id:       int
    target_ip:       str
    target_port:     int
    packet_size:     int
    duration:        float
    use_random_ports: bool
    is_running_flag: bool          # True at spawn; process is killed externally
    packets_sent:    mp.Value      # shared counter ('Q')
    counter_lock:    mp.Lock
    proxy:           str = None    # socks5://[user:pass@]host:port  (optional)
