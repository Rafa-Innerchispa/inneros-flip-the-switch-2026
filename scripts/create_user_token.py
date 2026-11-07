import asyncio
import asyncpg
import json
import os
import requests
import sys
from pathlib import Path

env_file = Path(os.getenv('APPDATA')) / 'switchdash' / 'local-switch-server' / 'native' / 'run' / 'switch-core.env'
env = dict(line.strip().split('=', 1) for line in env_file.read_text(encoding='utf-8-sig').splitlines() if '=' in line)

core_dir = Path(r'C:\Users\hrlg\AppData\Roaming\switchdash\local-switch-server\native\switch-core\0.31.0\src\core')
sys.path.insert(0, str(core_dir))

from switch_core.keys import Keyring
kr = Keyring.parse(env['SECRET_KEYS'], legacy_secret=env.get('JWT_SECRET_KEY'))

async def get_mm_creds():
    conn = await asyncpg.connect(
        host=env['DB_HOST'], port=int(env['DB_PORT']),
        user=env['DB_OWNER_USER'], password=env['DB_OWNER_PASSWORD'],
        database=env['DB_NAME']
    )
    rows = await conn.fetch("SELECT * FROM collaboration_bridges WHERE type='mattermost'")
    r = rows[0]
    cfg = json.loads(r['connection_config'])
    plain = kr.decrypt(cfg['_enc'])
    parsed = json.loads(plain)
    await conn.close()
    return parsed

mm_cfg = asyncio.run(get_mm_creds())
base = "http://127.0.0.1:62227"

# Login as admin
resp = requests.post(f"{base}/api/v4/users/login", json={
    "login_id": mm_cfg["admin_user"],
    "password": mm_cfg["admin_password"]
})
admin_token = resp.headers.get("Token")
admin_headers = {"Authorization": f"Bearer {admin_token}"}

# Find user 'user'
user_obj = requests.get(f"{base}/api/v4/users/username/user", headers=admin_headers).json()
user_id = user_obj["id"]
print("User ID:", user_id)

# Create user access token
tok_resp = requests.post(f"{base}/api/v4/users/{user_id}/tokens", headers=admin_headers, json={
    "description": "test-ping-token"
})
print("Token creation status:", tok_resp.status_code)
if tok_resp.status_code == 201:
    user_token = tok_resp.json()["token"]
    print("User token created successfully!")
else:
    print("Response:", tok_resp.text)

