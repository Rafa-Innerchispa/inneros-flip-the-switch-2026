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
if resp.status_code != 200:
    print("Login failed:", resp.status_code, resp.text)
    sys.exit(1)

token = resp.headers.get("Token")
headers = {"Authorization": f"Bearer {token}"}
print("Admin logged in successfully.")

# Get teams
teams = requests.get(f"{base}/api/v4/users/me/teams", headers=headers).json()
print("Teams:", [(t['id'], t['name']) for t in teams])

team_id = teams[0]['id']
# Get channels
channels = requests.get(f"{base}/api/v4/teams/{team_id}/channels", headers=headers).json()
print("\nChannels:")
target_ch = None
for c in channels:
    print(f" - {c['id']}: {c['name']} ({c['display_name']})")
    if c['name'] == 'inneros-live-operations':
        target_ch = c

if target_ch:
    print("\nTarget channel members:")
    members = requests.get(f"{base}/api/v4/channels/{target_ch['id']}/members", headers=headers).json()
    for m in members:
        u = requests.get(f"{base}/api/v4/users/{m['user_id']}", headers=headers).json()
        print(f" - {u.get('username')} ({u.get('id')}) is_bot={u.get('is_bot')}")

    print("\nRecent posts in inneros-live-operations:")
    posts = requests.get(f"{base}/api/v4/channels/{target_ch['id']}/posts", headers=headers).json()
    order = posts.get("order", [])
    posts_dict = posts.get("posts", {})
    for pid in order[:10]:
        p = posts_dict.get(pid, {})
        u = requests.get(f"{base}/api/v4/users/{p.get('user_id')}", headers=headers).json()
        print(f"[{p.get('create_at')}] {u.get('username')}: {p.get('message')[:120]}")
