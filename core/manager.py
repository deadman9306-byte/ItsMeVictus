"""
FloodManager — creates, tracks, and tears down FloodInstances.
"""

import time
import threading
import multiprocessing as mp
import subprocess
import uuid
import logging
from datetime import datetime

import config
import state
from core.instance import FloodInstance
from methods import DEFAULT_METHOD

logger = logging.getLogger(__name__)


class FloodManager:
    def __init__(self):
        self._floods:  dict[str, FloodInstance]    = {}
        self._threads: dict[str, threading.Thread] = {}
        self._lock     = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    def create_flood(
        self,
        target_ip:       str,
        target_port:     int,
        packet_size:     int  = config.DEFAULT_PACKET_SIZE,
        duration:        int  = config.DEFAULT_DURATION,
        processes:       int  = None,
        interface:       str  = 'auto',
        use_random_ports: bool = False,
        method_id:       int  = DEFAULT_METHOD,
        proxies:         list = None,
    ) -> str:
        instance_id = str(uuid.uuid4())[:8]

        if not processes or processes < 1:
            processes = mp.cpu_count()
        processes = max(1, min(processes, mp.cpu_count()))

        if interface == 'auto':
            interface = self._detect_interface()

        instance = FloodInstance(
            instance_id=instance_id,
            target_ip=target_ip,
            target_port=target_port,
            packet_size=packet_size,
            duration=duration,
            processes=processes,
            interface=interface,
            use_random_ports=use_random_ports,
            method_id=method_id,
            proxies=proxies,
        )

        with self._lock:
            self._floods[instance_id] = instance
            instance.start_flood()
            t = threading.Thread(
                target=self._stats_monitor, args=(instance,),
                daemon=True, name=f'stats-{instance_id}'
            )
            t.start()
            self._threads[instance_id] = t

        logger.info(f"Created flood {instance_id} (method {method_id}): "
                    f"{target_ip}:{target_port}")
        return instance_id

    def stop_flood(self, instance_id: str) -> bool:
        with self._lock:
            inst = self._floods.pop(instance_id, None)
            if inst is None:
                return False
            inst.stop_flood()
            self._threads.pop(instance_id, None)
        logger.info(f"Stopped flood {instance_id}")
        return True

    def stop_all_floods(self) -> int:
        with self._lock:
            count = len(self._floods)
            for inst in list(self._floods.values()):
                inst.stop_flood()
            self._floods.clear()
            self._threads.clear()
        logger.info(f"Stopped all {count} floods")
        return count

    def get_status(self, instance_id: str = None) -> dict:
        with self._lock:
            if instance_id:
                inst = self._floods.get(instance_id)
                return inst.get_status() if inst else {'error': 'Instance not found'}
            return {
                'active_instances': len(self._floods),
                'instances': {k: v.get_status() for k, v in self._floods.items()},
            }

    def get_all_stats(self) -> dict:
        with self._lock:
            return {
                'total_active': len(self._floods),
                'instances':    {k: v.stats for k, v in self._floods.items()},
            }

    # ── Internals ─────────────────────────────────────────────────────────────

    @staticmethod
    def _detect_interface() -> str:
        try:
            out = subprocess.run(
                ['ip', 'route', 'show', 'default'],
                capture_output=True, text=True
            ).stdout
            for part in out.split():
                if part.startswith(('eth', 'wlan', 'enp', 'ens')):
                    return part
        except Exception:
            pass
        return 'eth0'

    def _stats_monitor(self, instance: FloodInstance):
        start_time  = time.time()
        last_pkt    = 0
        last_bytes  = instance.get_interface_bytes()
        last_time   = start_time
        last_idle   = last_total = 0

        try:
            with open('/proc/stat') as f:
                parts      = f.readline().split()
                last_idle  = int(parts[4])
                last_total = sum(int(x) for x in parts[1:])
        except Exception:
            pass

        while instance.is_running() and not state.shutdown_in_progress:
            time.sleep(1)
            now        = time.time()
            elapsed    = now - start_time
            delta_time = max(now - last_time, 1e-6)

            cur_pkt     = instance.packets_sent.value
            delta_pkt   = cur_pkt - last_pkt
            calc_pps    = delta_pkt / delta_time
            calc_mbps   = (delta_pkt * instance.packet_size * 8) / (delta_time * 1e6)

            cur_bytes = instance.get_interface_bytes()
            real_mbps = real_mbs = 0.0
            if cur_bytes is not None and last_bytes is not None:
                db        = cur_bytes - last_bytes
                real_mbps = (db * 8) / (delta_time * 1e6)
                real_mbs  = db / (delta_time * 1e6)

            cpu_usage = 0.0
            try:
                with open('/proc/stat') as f:
                    parts       = f.readline().split()
                    idle        = int(parts[4])
                    total       = sum(int(x) for x in parts[1:])
                    idle_delta  = idle  - last_idle
                    total_delta = total - last_total
                    cpu_usage   = 100 * (1 - idle_delta / total_delta) if total_delta else 0
                last_idle, last_total = idle, total
            except Exception:
                pass

            instance.update_stats({
                'timestamp':           datetime.now().isoformat(),
                'elapsed':             elapsed,
                'packets_sent':        cur_pkt,
                'packets_delta':       delta_pkt,
                'calc_pps':            calc_pps,
                'calc_mbps':           calc_mbps,
                'real_mbps':           real_mbps,
                'real_mb_per_sec':     real_mbs,
                'cpu_usage':           cpu_usage,
                'active_workers':      len(instance.workers),
                'sendmmsg_enabled':    config.USE_SENDMMSG,
                'packet_loss_warning': real_mbps > 0 and calc_mbps > real_mbps * 1.2,
            })

            last_pkt   = cur_pkt
            last_bytes = cur_bytes
            last_time  = now

            if elapsed >= instance.duration or state.shutdown_in_progress:
                instance.stop_flood()
                break
