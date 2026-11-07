import json
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

# 2. Post @inneros-incident-triage !ping
post_req = urllib.request.Request(
    f'{mm_url}/api/v4/posts',
    data=json.dumps({
        'channel_id': channel_id,
        'message': '@inneros-incident-triage !ping'
    }).encode(),
    headers=headers
)
post_resp = urllib.request.urlopen(post_req)
post_obj = json.loads(post_resp.read().decode())
post_id = post_obj['id']
print(f"Posted message [id: {post_id}]: '@inneros-incident-triage !ping'")

# 3. Wait for bot response
print("Waiting up to 10 seconds for bot response in Mattermost...")
replied = False
for i in range(10):
    time.sleep(1)
    posts_req = urllib.request.Request(f'{mm_url}/api/v4/channels/{channel_id}/posts', headers=headers)
    posts_data = json.loads(urllib.request.urlopen(posts_req).read().decode())
    order = posts_data.get('order', [])
    posts_dict = posts_data.get('posts', {})
    if order and order[0] != post_id:
        latest = posts_dict[order[0]]
        print(f"\n🎉 BOT RESPONSE RECEIVED IN MATTERMOST!")
        print(f"Author User ID: {latest.get('user_id')}")
        print(f"Message Content: {latest.get('message')}")
        replied = True
        break

if not replied:
    print("No reply received in 10s. Checking recent posts:")
    posts_req = urllib.request.Request(f'{mm_url}/api/v4/channels/{channel_id}/posts', headers=headers)
    posts_data = json.loads(urllib.request.urlopen(posts_req).read().decode())
    for pid in posts_data.get('order', [])[:5]:
        p = posts_data.get('posts', {}).get(pid, {})
        print(f" - [{p.get('create_at')}] {p.get('user_id')}: {p.get('message')}")
