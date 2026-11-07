import asyncio
import asyncpg
import json
import os
import requests
import time
from pathlib import Path

env_file = Path(os.getenv('APPDATA')) / 'switchdash' / 'local-switch-server' / 'native' / 'run' / 'switch-core.env'
env = dict(line.strip().split('=', 1) for line in env_file.read_text(encoding='utf-8-sig').splitlines() if '=' in line)

core_dir = Path(r'C:\Users\hrlg\AppData\Roaming\switchdash\local-switch-server\native\switch-core\0.31.0\src\core')
import sys
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
token = resp.headers.get("Token")
headers = {"Authorization": f"Bearer {token}"}

channel_id = "zq5zdesbp38d9f6idwu6xrpsuy" # inneros-live-operations

print("Sending post: '@inneros-incident-triage !ping' to inneros-live-operations...")
post_resp = requests.post(f"{base}/api/v4/posts", headers=headers, json={
    "channel_id": channel_id,
    "message": "@inneros-incident-triage !ping"
})
print("Post status:", post_resp.status_code, post_resp.json().get("id"))

print("Waiting 10 seconds for bridge response...")
for i in range(10):
    time.sleep(1)
    posts = requests.get(f"{base}/api/v4/channels/{channel_id}/posts", headers=headers).json()
    order = posts.get("order", [])
    posts_dict = posts.get("posts", {})
    if order:
        latest = posts_dict.get(order[0], {})
        # If the latest post is from a bot or contains PONG
        if "PONG" in latest.get("message", "") or latest.get("user_id") != resp.json().get("id"):
            print(f"FOUND NEW POST: [{latest.get('user_id')}] {latest.get('message')}")
            break

print("Checking recent 3 posts:")
posts = requests.get(f"{base}/api/v4/channels/{channel_id}/posts", headers=headers).json()
for pid in posts.get("order", [])[:3]:
    p = posts.get("posts", {}).get(pid, {})
    print(f" - [{p.get('create_at')}] user={p.get('user_id')}: {p.get('message')}")

