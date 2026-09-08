"""
FloodInstance — owns one flood: its workers, shared counters, and live stats.
"""

import multiprocessing as mp
import logging
from datetime import datetime

from methods.base import WorkerArgs
from methods import get_worker

logger = logging.getLogger(__name__)


class FloodInstance:
    def __init__(
        self,
        instance_id:     str,
        target_ip:       str,
        target_port:     int,
        packet_size:     int,
        duration:        int,
        processes:       int,
        interface:       str,
        use_random_ports: bool,
        method_id:       int,
        proxies:         list = None,   # list of socks5://... strings
    ):
        self.instance_id      = instance_id
        self.target_ip        = target_ip
        self.target_port      = target_port
        self.packet_size      = packet_size
        self.duration         = duration
        self.processes        = processes
        self.interface        = interface
        self.use_random_ports = use_random_ports
        self.method_id        = method_id
        self.proxies          = proxies or []

        self.start_time      = None
        self.end_time        = None
        self.is_running_flag = False
        self.workers:  list[mp.Process] = []

        # Shared memory counters
        self.packets_sent = mp.Value('Q', 0)
        self.counter_lock = mp.Lock()

        self.max_history = 60
        self.stats: dict = {
            'packets_sent':       0,
            'calc_pps':           0,
            'calc_mbps':          0,
            'real_mbps':          0,
            'cpu_usage':          0,
            'elapsed':            0,
            'active_workers':     0,
            'packet_loss_warning': False,
            'historical':         [],
        }

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start_flood(self):
        self.is_running_flag = True
        self.start_time      = __import__('time').time()
        worker_fn            = get_worker(self.method_id)

        for i in range(self.processes):
            # Distribute proxies round-robin across workers (None if no proxies)
            proxy = self.proxies[i % len(self.proxies)] if self.proxies else None
            args = WorkerArgs(
                worker_id=i,
                target_ip=self.target_ip,
                target_port=self.target_port,
                packet_size=self.packet_size,
                duration=self.duration,
                use_random_ports=self.use_random_ports,
                is_running_flag=True,
                packets_sent=self.packets_sent,
                counter_lock=self.counter_lock,
                proxy=proxy,
            )
            p = mp.Process(target=worker_fn, args=(args,), daemon=True)
            p.start()
            self.workers.append(p)

        logger.info(
            f"[{self.instance_id}] Started {len(self.workers)} workers "
            f"(method {self.method_id}) → {self.target_ip}:{self.target_port}"
        )

    def stop_flood(self):
        self.is_running_flag = False
        self.end_time = __import__('time').time()
        for p in self.workers:
            p.terminate()
            p.join(timeout=2)
        self.workers.clear()
        logger.info(f"[{self.instance_id}] All workers stopped")

    def is_running(self) -> bool:
        return self.is_running_flag and any(p.is_alive() for p in self.workers)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def update_stats(self, new_stats: dict):
        self.stats.update(new_stats)
        entry = {k: v for k, v in new_stats.items() if k != 'historical'}
        self.stats['historical'].append(entry)
        if len(self.stats['historical']) > self.max_history:
            self.stats['historical'] = self.stats['historical'][-self.max_history:]

    def get_interface_bytes(self):
        try:
            with open('/proc/net/dev') as f:
                for line in f:
                    if self.interface in line:
                        parts = line.split()
                        if len(parts) >= 10:
                            return int(parts[9])
        except Exception:
            pass
        return None

    def get_status(self) -> dict:
        return {
            'instance_id':       self.instance_id,
            'method_id':         self.method_id,
            'target_ip':         self.target_ip,
            'target_port':       self.target_port,
            'packet_size':       self.packet_size,
            'duration':          self.duration,
            'processes':         self.processes,
            'interface':         self.interface,
            'use_random_ports':  self.use_random_ports,
            'is_running':        self.is_running_flag,
            'start_time':        datetime.fromtimestamp(self.start_time).isoformat()
                                 if self.start_time else None,
            'end_time':          datetime.fromtimestamp(self.end_time).isoformat()
                                 if self.end_time else None,
            'total_packets_sent': self.packets_sent.value,
            'stats':             self.stats,
        }
