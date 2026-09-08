"""
Supabase URL registration.
Registers the Replit dev URL so the website knows where this API lives.
"""

import requests
from datetime import datetime

import config
import state


def register_url(url: str) -> bool:
    """
    Upsert the API URL into Supabase.
    Returns True on success (including already-registered).
    """
    if not url:
        return False

    headers = {
        'apikey': config.SUPABASE_KEY,
        'Authorization': f'Bearer {config.SUPABASE_KEY}',
    }

    try:
        print(f"📝 Registering URL with Supabase...")
        print(f"   🔗 {url}")

        # Check if already registered
        check = requests.get(
            f"{config.SUPABASE_URL}/rest/v1/{config.SUPABASE_TABLE}"
            f"?url=eq.{url}&select=id",
            headers=headers,
            timeout=10,
        )
        if check.status_code == 200 and check.json():
            print("   ℹ️  Already registered — skipping insert")
            state.current_url    = url
            state.url_registered = True
            return True

        # Insert new record
        resp = requests.post(
            f"{config.SUPABASE_URL}/rest/v1/{config.SUPABASE_TABLE}",
            headers={**headers,
                     'Content-Type': 'application/json',
                     'Prefer': 'return=representation'},
            json={'url': url, 'registered_at': datetime.now().isoformat()},
            timeout=10,
        )

        if resp.status_code in [200, 201, 409]:
            print("   ✅ Registered successfully")
            state.current_url    = url
            state.url_registered = True
            return True

        print(f"   ⚠️  Registration failed — HTTP {resp.status_code}: {resp.text}")
        return False

    except Exception as e:
        print(f"   ⚠️  Supabase error: {e}")
        return False
