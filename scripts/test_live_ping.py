import json
import time
import urllib.request
from pathlib import Path

env_file = Path('/home/rlopez/inneros/modules/switch-liveops/compose/.env')
env = dict(line.strip().split('=', 1) for line in env_file.read_text().splitlines() if '=' in line and not line.startswith('#'))

opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
login_req = urllib.request.Request(
    'http://127.0.0.1:62326/gateway/auth/login',
    data=json.dumps({'email': env['GATEWAY_ADMIN_EMAIL'], 'password': env['GATEWAY_ADMIN_PASSWORD']}).encode(),
    headers={'Content-Type': 'application/json'}
)
opener.open(login_req)

status = json.loads(Path('/home/rlopez/.config/inneros-switch/liveops-status.json').read_text())
room_id = status['room_id']

print("Sending '@inneros-incident-triage !ping' to room", room_id)
msg_req = urllib.request.Request(
    f'http://127.0.0.1:62326/gateway/rooms/{room_id}/messages',
    data=json.dumps({'content': '@inneros-incident-triage !ping'}).encode(),
    headers={'Content-Type': 'application/json'}
)
res = opener.open(msg_req)
sent_msg = json.loads(res.read().decode())
print('POST STATUS:', res.status, 'Message ID:', sent_msg.get('id'))

print("Waiting 5s for agent reply...")
time.sleep(3)

# Read room messages
msgs_req = urllib.request.Request(f'http://127.0.0.1:62326/gateway/rooms/{room_id}/messages')
msgs = json.loads(opener.open(msgs_req).read().decode())

print("\nRecent messages in room:")
for m in msgs[-5:]:
    sender = m.get('sender_id') or m.get('sender')
    content = m.get('content') or m.get('body')
    print(f"[{m.get('created_at') or m.get('sent_at')}] {sender}: {content}")
