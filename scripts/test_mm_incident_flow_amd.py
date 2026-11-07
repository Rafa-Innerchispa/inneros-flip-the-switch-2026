import json
import re
import time
import urllib.request
from pathlib import Path

env_file = Path('/home/rlopez/inneros/modules/switch-liveops/compose/.env')
env = dict(line.strip().split('=', 1) for line in env_file.read_text().splitlines() if '=' in line and not line.startswith('#'))

mm_url = 'http://127.0.0.1:62327'

# 1. Login as 'user'
login_req = urllib.request.Request(
    f'{mm_url}/api/v4/users/login',
    data=json.dumps({'login_id': 'user', 'password': env['MATTERMOST_USER_PASSWORD']}).encode(),
    headers={'Content-Type': 'application/json'}
)
resp = urllib.request.urlopen(login_req)
token = resp.headers.get('Token')
user_data = json.loads(resp.read().decode())
print(f"Logged in as '{user_data['username']}' ({user_data['id']})")

headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
channel_id = 'r4n59sq7dtyp7d3n3ogomaqfwh'  # inneros-live-operations

def post_msg(msg: str) -> str:
    req = urllib.request.Request(
        f'{mm_url}/api/v4/posts',
        data=json.dumps({'channel_id': channel_id, 'message': msg}).encode(),
        headers=headers
    )
    res = urllib.request.urlopen(req)
    obj = json.loads(res.read().decode())
    return obj['id']

def wait_reply(after_post_id: str, timeout: int = 12) -> dict | None:
    for _ in range(timeout):
        time.sleep(1)
        req = urllib.request.Request(f'{mm_url}/api/v4/channels/{channel_id}/posts', headers=headers)
        data = json.loads(urllib.request.urlopen(req).read().decode())
        order = data.get('order', [])
        posts_dict = data.get('posts', {})
        if order and order[0] != after_post_id:
            return posts_dict[order[0]]
    return None

# STEP 1: Post !status
print("\n--- STEP 1: Testing !status ---")
p1 = post_msg("@inneros-incident-triage !status")
r1 = wait_reply(p1)
if r1:
    print("STATUS REPLY:", r1.get('message'))
else:
    print("TIMEOUT on !status")

# STEP 2: Post !incident
print("\n--- STEP 2: Testing !incident (AI Triage on AMD 1.5 GPU) ---")
p2 = post_msg("@inneros-incident-triage !incident")
r2 = wait_reply(p2, timeout=15)
if r2:
    msg2 = r2.get('message', '')
    print("INCIDENT REPLY:\n", msg2)
    # Extract action ID
    match = re.search(r'(ACT-[0-9A-F]+)', msg2)
    if match:
        act_id = match.group(1)
        print(f"\nExtracted Action ID: {act_id}")

        # STEP 3: Approve action
        print(f"\n--- STEP 3: Authorizing Action {act_id} via Human Approval ---")
        p3 = post_msg(f"@inneros-incident-triage !approve {act_id}")
        r3 = wait_reply(p3, timeout=10)
        if r3:
            print("APPROVAL REPLY:\n", r3.get('message'))
        else:
            print("TIMEOUT on !approve")
    else:
        print("Could not find ACT- ID in message!")
else:
    print("TIMEOUT on !incident")
