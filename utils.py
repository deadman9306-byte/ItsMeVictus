"""
General-purpose utilities.
"""

import os
import signal
import subprocess
import time


def kill_port(port: int) -> bool:
    """Forcefully free a TCP port by killing whatever process owns it."""
    try:
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True, text=True
        )
        if not result.stdout.strip():
            print(f"✅ Port {port} is already free")
            return True

        killed = []
        for pid in result.stdout.strip().split('\n'):
            if not pid:
                continue
            try:
                print(f"🔴 Killing PID {pid} on port {port}")
                os.kill(int(pid), signal.SIGTERM)
                time.sleep(0.3)
                try:
                    os.kill(int(pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                killed.append(pid)
            except ProcessLookupError:
                pass
            except Exception as e:
                print(f"⚠️  Error killing PID {pid}: {e}")

        print(f"✅ Killed {len(killed)} process(es) on port {port}" if killed
              else f"✅ Port {port} is already free")
        return True

    except FileNotFoundError:
        # lsof not available — try fuser
        try:
            subprocess.run(['fuser', '-k', f'{port}/tcp'],
                           capture_output=True, text=True)
            print(f"✅ Port {port} freed via fuser")
            return True
        except Exception:
            print(f"⚠️  Could not free port {port} (lsof/fuser unavailable)")
            return False

    except Exception as e:
        print(f"⚠️  kill_port error: {e}")
        return False
