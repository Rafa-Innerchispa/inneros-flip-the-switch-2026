import json
import requests
import time

base = "http://127.0.0.1:62227"
user_token = "or5bgyy6oigd5ed1ykyxsbhu8e"
channel_id = "zq5zdesbp38d9f6idwu6xrpsuy" # inneros-live-operations

headers = {"Authorization": f"Bearer {user_token}"}

print("Posting message as 'user'...")
resp = requests.post(f"{base}/api/v4/posts", headers=headers, json={
    "channel_id": channel_id,
    "message": "@inneros-incident-triage !ping"
})
print("Post status:", resp.status_code, resp.json().get("id"))
post_id = resp.json().get("id")

print("Waiting 10 seconds for bot response...")
for i in range(10):
    time.sleep(1)
    posts = requests.get(f"{base}/api/v4/channels/{channel_id}/posts", headers=headers).json()
    order = posts.get("order", [])
    posts_dict = posts.get("posts", {})
    if order and order[0] != post_id:
        latest = posts_dict.get(order[0], {})
        print(f"NEW POST ARRIVED: [{latest.get('user_id')}] {latest.get('message')}")
        break

print("\nRecent 5 posts in channel:")
posts = requests.get(f"{base}/api/v4/channels/{channel_id}/posts", headers=headers).json()
for pid in posts.get("order", [])[:5]:
    p = posts.get("posts", {}).get(pid, {})
    print(f" - [{p.get('create_at')}] user={p.get('user_id')}: {p.get('message')}")

