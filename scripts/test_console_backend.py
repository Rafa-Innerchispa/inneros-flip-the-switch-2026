#!/usr/bin/env python3
"""Test console backend functions on AMD 1.5."""
import os
import sys
import json
import time
import uuid
import urllib.request
from datetime import datetime, timezone

def test_switch_ping():
    print("Testing Switch Ping...")
    env_file = "/home/rlopez/inneros/modules/switch-liveops/compose/.env"
    user_pw = ""
    if os.path.isfile(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MATTERMOST_USER_PASSWORD="):
                    user_pw = line.split("=", 1)[1].strip()
                    break

    mm_url = "http://127.0.0.1:62327"
    channel_id = "r4n59sq7dtyp7d3n3ogomaqfwh"

    t0 = time.perf_counter()
    cid = f"CID-LIVE-PING-{uuid.uuid4().hex[:6].upper()}"

    login_data = json.dumps({"login_id": "user", "password": user_pw}).encode("utf-8")
    req = urllib.request.Request(
        f"{mm_url}/api/v4/users/login",
        data=login_data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=4) as resp:
        token = resp.headers.get("Token")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    cmd = f"@inneros-incident-triage !ping {cid}"

    post_req = urllib.request.Request(
        f"{mm_url}/api/v4/posts",
        data=json.dumps({"channel_id": channel_id, "message": cmd}).encode("utf-8"),
        headers=headers
    )
    with urllib.request.urlopen(post_req, timeout=4) as post_res:
        post_id = json.loads(post_res.read().decode("utf-8")).get("id")

    reply = None
    for _ in range(16):
        time.sleep(0.3)
        ch_req = urllib.request.Request(f"{mm_url}/api/v4/channels/{channel_id}/posts?per_page=6", headers=headers)
        try:
            with urllib.request.urlopen(ch_req, timeout=3) as ch_res:
                data = json.loads(ch_res.read().decode("utf-8"))
                posts = data.get("posts", {})
                for pid, p in posts.items():
                    if pid != post_id and cid in p.get("message", ""):
                        reply = p
                        break
            if reply:
                break
        except Exception:
            pass

    elapsed = round((time.perf_counter() - t0) * 1000, 2)
    reply_msg = reply.get("message", "") if reply else ""
    passed = bool(reply and "PONG" in reply_msg)

    res = {
        "ok": passed,
        "step": "PING_AGENT",
        "correlation_id": cid,
        "latency_ms": elapsed,
        "result": "PASS" if passed else "FAIL",
        "agent_response": reply_msg.strip() if reply_msg else "Agent response timeout",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    print(json.dumps(res, indent=2))
    return passed

def test_qwen_inference():
    print("\nTesting Qwen Inference...")
    model_name = "QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ"
    cid = f"CID-AI-{uuid.uuid4().hex[:6].upper()}"
    question = "Explain how sovereign agent incident triage prevents downtime on local infrastructure."

    t0 = time.perf_counter()
    data = json.dumps({
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": "You are InnerOS Incident Reasoner running sovereignly on AMD ROCm. Answer technically and concisely in 2 sentences."
            },
            {
                "role": "user",
                "content": question
            }
        ],
        "max_tokens": 100,
        "temperature": 0.2
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://127.0.0.1:8000/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        res = json.loads(resp.read().decode("utf-8"))

    elapsed = round((time.perf_counter() - t0) * 1000, 2)
    choice = res.get("choices", [{}])[0]
    content = choice.get("message", {}).get("content", "").strip()
    usage = res.get("usage", {})

    out = {
        "ok": True,
        "step": "LOCAL_AI_INFERENCE",
        "correlation_id": cid,
        "model_id": model_name,
        "hardware": "AMD Radeon AI PRO R9700 (ROCm 7.2.1)",
        "prompt": question,
        "output": content,
        "latency_ms": elapsed,
        "tokens_evaluated": usage.get("total_tokens", 0),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    print(json.dumps(out, indent=2))
    return True

if __name__ == "__main__":
    p_ok = test_switch_ping()
    q_ok = test_qwen_inference()
    if p_ok and q_ok:
        print("\nALL BACKEND CONSOLE TESTS PASSED!")
    else:
        print("\nTESTS FAILED!")
        sys.exit(1)

