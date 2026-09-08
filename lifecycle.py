"""
Signal handlers and shutdown logic.
Call register_handlers() once at startup.
"""

import sys
import signal
import atexit
import logging

import state
from config import API_PORT
from utils import kill_port

logger = logging.getLogger(__name__)


def _shutdown(signal_name: str):
    print(f"\n{'='*60}")
    print(f"🔄  {signal_name} — shutting down (URL kept in Supabase)")
    if state.current_url and state.url_registered:
        print(f"🔗  {state.current_url}")
    print('='*60)

    if state.manager:
        state.manager.stop_all_floods()

    kill_port(API_PORT)
    print("👋  Done\n")


def signal_handler(sig, frame):
    if state.shutdown_in_progress:
        return
    state.shutdown_in_progress = True
    state.cleanup_done = True

    names = {
        signal.SIGINT:  'SIGINT (Ctrl+C)',
        signal.SIGTERM: 'SIGTERM',
        signal.SIGHUP:  'SIGHUP',
    }
    _shutdown(names.get(sig, f'signal {sig}'))
    sys.exit(0)


def cleanup_on_exit():
    if state.cleanup_done or state.flask_shutting_down:
        return
    state.cleanup_done = True
    _shutdown('Normal exit')


def register_handlers():
    """Register signal handlers and atexit hook. Call once at startup."""
    signal.signal(signal.SIGINT,  signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGHUP,  signal_handler)
    atexit.register(cleanup_on_exit)
