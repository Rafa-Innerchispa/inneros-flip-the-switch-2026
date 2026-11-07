"""Execute real Mattermost -> Switch -> Agent commands on AMD 1.5.

Records full input/output correlation logs, timestamps, post IDs, and hashes.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import time
import urllib.request
from uuid import uuid4


def main():
    env_file = Path("/home/rlopez/inneros/modules/switch-liveops/compose/.env")
    env = {}
    if env_file.is_file():
        env = dict(
            line.strip().split("=", 1)
            for line in env_file.read_text(encoding="utf-8").splitlines()
            if "=" in line and not line.startswith("#")
        )

    mm_url = "http://127.0.0.1:62327"
    channel_id = "r4n59sq7dtyp7d3n3ogomaqfwh"  # inneros-live-operations

    # 1. Login to Mattermost
    req = urllib.request.Request(
        f"{mm_url}/api/v4/users/login",
        data=json.dumps({"login_id": "user", "password": env.get("MATTERMOST_USER_PASSWORD", "")}).encode(),
        headers={"Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=5)
    token = resp.headers.get("Token")
    user = json.loads(resp.read().decode())
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def post(msg: str) -> str:
        r = urllib.request.Request(
            f"{mm_url}/api/v4/posts",
            data=json.dumps({"channel_id": channel_id, "message": msg}).encode(),
            headers=headers
        )
        res = urllib.request.urlopen(r, timeout=5)
        return json.loads(res.read().decode())["id"]

    def wait_reply(after_id: str, expected_token: str | None = None, timeout: int = 15) -> dict | None:
        p_req = urllib.request.Request(f"{mm_url}/api/v4/posts/{after_id}", headers=headers)
        after_post = json.loads(urllib.request.urlopen(p_req, timeout=3).read().decode())
        after_ts = after_post.get("create_at", 0)

        for _ in range(timeout):
            time.sleep(1)
            req = urllib.request.Request(f"{mm_url}/api/v4/channels/{channel_id}/posts?per_page=10", headers=headers)
            try:
                data = json.loads(urllib.request.urlopen(req, timeout=4).read().decode())
                order = data.get("order", [])
                posts = data.get("posts", {})
                for pid in order:
                    if pid == after_id:
                        continue
                    p = posts.get(pid, {})
                    if p.get("create_at", 0) >= after_ts:
                        msg = p.get("message", "")
                        if expected_token:
                            if expected_token in msg:
                                return p
                        else:
                            return p
            except Exception:
                pass
        return None

    results = []
    print("=== STARTING LIVE MATTERMOST -> SWITCH TEST SEQUENCE ===")

    # Test 1: !ping
    cid_ping = f"CID-LIVE-PING-{uuid4().hex[:6].upper()}"
    cmd_ping = f"@inneros-incident-triage !ping {cid_ping}"
    t0 = time.time()
    pid_ping = post(cmd_ping)
    rep_ping = wait_reply(pid_ping, expected_token=cid_ping)
    dur_ping = round((time.time() - t0) * 1000, 2)
    print(f"[TEST 1 PING] Latency: {dur_ping}ms | Response: {rep_ping['message'] if rep_ping else 'TIMEOUT'}")
    results.append({
        "step": "PING",
        "command": cmd_ping,
        "correlation_id": cid_ping,
        "post_id": pid_ping,
        "reply_post_id": rep_ping.get("id") if rep_ping else None,
        "reply_text": rep_ping.get("message") if rep_ping else None,
        "latency_ms": dur_ping,
        "status": "PASS" if rep_ping and "PONG" in rep_ping["message"] else "FAIL"
    })

    # Test 2: !status
    cid_status = f"CID-LIVE-STATUS-{uuid4().hex[:6].upper()}"
    cmd_status = f"@inneros-incident-triage !status {cid_status}"
    t0 = time.time()
    pid_status = post(cmd_status)
    rep_status = wait_reply(pid_status, expected_token=cid_status)
    dur_status = round((time.time() - t0) * 1000, 2)
    print(f"[TEST 2 STATUS] Latency: {dur_status}ms | Response: {rep_status['message'] if rep_status else 'TIMEOUT'}")
    results.append({
        "step": "STATUS",
        "command": cmd_status,
        "correlation_id": cid_status,
        "post_id": pid_status,
        "reply_post_id": rep_status.get("id") if rep_status else None,
        "reply_text": rep_status.get("message") if rep_status else None,
        "latency_ms": dur_status,
        "status": "PASS" if rep_status and "INNEROS STATUS" in rep_status["message"] else "FAIL"
    })

    # Test 3: !incident
    cid_inc = f"CID-LIVE-INC-{uuid4().hex[:6].upper()}"
    cmd_inc = f"@inneros-incident-triage !incident {cid_inc}"
    t0 = time.time()
    pid_inc = post(cmd_inc)
    rep_inc = wait_reply(pid_inc, expected_token=cid_inc, timeout=18)
    dur_inc = round((time.time() - t0) * 1000, 2)
    print(f"[TEST 3 INCIDENT] Latency: {dur_inc}ms | Response:\n{rep_inc['message'] if rep_inc else 'TIMEOUT'}")
    
    act_id = None
    if rep_inc:
        m = re.search(r"(ACT-[0-9A-F]+)", rep_inc["message"])
        if m:
            act_id = m.group(1)

    results.append({
        "step": "INCIDENT_TRIAGE",
        "command": cmd_inc,
        "correlation_id": cid_inc,
        "post_id": pid_inc,
        "reply_post_id": rep_inc.get("id") if rep_inc else None,
        "reply_text": rep_inc.get("message") if rep_inc else None,
        "generated_action_id": act_id,
        "latency_ms": dur_inc,
        "status": "PASS" if rep_inc and "INNEROS INCIDENT" in rep_inc["message"] and act_id else "FAIL"
    })

    # Test 4: Unauthorized approval rejection
    cid_block = f"CID-LIVE-BLOCK-{uuid4().hex[:6].upper()}"
    cmd_block = f"@inneros-incident-triage !approve ACT-UNAUTHORIZED99 {cid_block}"
    t0 = time.time()
    pid_block = post(cmd_block)
    rep_block = wait_reply(pid_block, expected_token=cid_block)
    dur_block = round((time.time() - t0) * 1000, 2)
    print(f"[TEST 4 AUTH BLOCK] Latency: {dur_block}ms | Response: {rep_block['message'] if rep_block else 'TIMEOUT'}")
    results.append({
        "step": "AUTH_BLOCK",
        "command": cmd_block,
        "correlation_id": cid_block,
        "post_id": pid_block,
        "reply_post_id": rep_block.get("id") if rep_block else None,
        "reply_text": rep_block.get("message") if rep_block else None,
        "latency_ms": dur_block,
        "status": "PASS" if rep_block and "BLOCKED" in rep_block["message"] else "FAIL"
    })

    # Test 5: Authorized execution + Cryptographic Receipt
    if act_id:
        cid_app = f"CID-LIVE-APP-{uuid4().hex[:6].upper()}"
        cmd_app = f"@inneros-incident-triage !approve {act_id} {cid_app}"
        t0 = time.time()
        pid_app = post(cmd_app)
        rep_app = wait_reply(pid_app, expected_token=cid_app, timeout=15)
        dur_app = round((time.time() - t0) * 1000, 2)
        print(f"[TEST 5 APPROVE & RECEIPT] Latency: {dur_app}ms | Response:\n{rep_app['message'] if rep_app else 'TIMEOUT'}")
        
        receipt_hash = None
        if rep_app:
            m_h = re.search(r"SHA256:([0-9a-fA-F]+)", rep_app["message"])
            if m_h:
                receipt_hash = m_h.group(1)

        results.append({
            "step": "APPROVE_EXECUTE",
            "command": cmd_app,
            "correlation_id": cid_app,
            "action_id": act_id,
            "post_id": pid_app,
            "reply_post_id": rep_app.get("id") if rep_app else None,
            "reply_text": rep_app.get("message") if rep_app else None,
            "receipt_hash": receipt_hash,
            "latency_ms": dur_app,
            "status": "PASS" if rep_app and "ACTION EXECUTED" in rep_app["message"] and receipt_hash else "FAIL"
        })

    out_file = Path("/home/rlopez/inneros/modules/switch-liveops/data/live_mattermost_evidence.json")
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved live evidence log to {out_file}")


if __name__ == "__main__":
    main()

