#!/usr/bin/env python3
"""
Ultra UDP Flood Simulator — Replit Edition  v5.0.0
Entry point: boots Flask and registers the stable Replit URL with Supabase.
"""

import multiprocessing as mp
import os
import sys
import time
import threading
import logging

# Configure logging before any local imports so all modules inherit the format.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  [%(levelname)-8s]  %(name)s — %(message)s',
    datefmt='%H:%M:%S',
)

import config
import state
from utils     import kill_port
from registry  import register_url
from lifecycle import register_handlers
from api       import create_app


# ── Banner ────────────────────────────────────────────────────────────────────

def _banner():
    print("=" * 70)
    print("  🚀  ULTRA UDP FLOOD SIMULATOR  —  REPLIT EDITION  v5.0.0")
    print("=" * 70)
    print(f"  CPU cores  :  {mp.cpu_count()}")
    print(f"  sendmmsg   :  {config.USE_SENDMMSG}")
    print(f"  Supabase   :  {config.SUPABASE_URL}")
    print("=" * 70 + "\n")


# ── Flask runner (thread) ─────────────────────────────────────────────────────

def _run_flask(app):
    try:
        app.run(host='0.0.0.0', port=config.API_PORT,
                debug=False, threaded=True)
    except Exception as e:
        print(f"⚠️  Flask error: {e}")
    finally:
        state.flask_shutting_down = True


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    mp.freeze_support()

    register_handlers()
    _banner()

    print(f"🔄  Freeing port {config.API_PORT}...")
    kill_port(config.API_PORT)
    time.sleep(0.5)

    print(f"📡  Starting Flask on port {config.API_PORT}...")
    app    = create_app()
    thread = threading.Thread(target=_run_flask, args=(app,),
                              daemon=True, name='Flask')
    thread.start()
    time.sleep(2)

    # Resolve stable Replit URL
    domain     = os.environ.get('REPLIT_DEV_DOMAIN')
    replit_url = f"https://{domain}" if domain else f"http://localhost:{config.API_PORT}"

    print(f"\n{'='*70}")
    print(f"  🌐  {replit_url}")
    print(f"{'='*70}\n")

    if register_url(replit_url):
        print(f"✅  API is live at {replit_url}\n")
    else:
        print(f"⚠️   Supabase registration failed — API still running at {replit_url}\n")

    # Keep main thread alive
    try:
        while not state.shutdown_in_progress:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
