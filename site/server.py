#!/usr/bin/env python3
"""
InnerOS LiveOps Standalone Web Server
Flip the Switch 2026 Hackathon Submission
Author: InnerChispa / Rafael Lopez

Hardened against data leakage, false status claims, and unauthorized operations.
"""

import os
import sys
import json
import time
import socket
import subprocess
import uuid
import urllib.request
import urllib.error
import http.server
import socketserver
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("PORT", 8790))
HOST = os.environ.get("HOST", "0.0.0.0")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "/home/rlopez/inneros/modules/switch-liveops/data"

ALLOWED_ORIGINS = {
    "https://liveops.pcdoctor.ai",
    "http://localhost:8790",
    "http://127.0.0.1:8790",
    "http://192.168.1.5:8790",
}

SAFE_STATIC_EXTENSIONS = {".html", ".css", ".js", ".png", ".jpg", ".svg", ".ico", ".txt"}

def check_tcp(host, port, timeout=0.8):
    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, round((time.perf_counter() - t0) * 1000, 2)
    except Exception:
        return False, round((time.perf_counter() - t0) * 1000, 2)

def check_http(url, timeout=1.2):
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "InnerOS-Health/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return resp.status == 200, resp.read(), elapsed
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        return False, None, elapsed

def get_system_telemetry():
    now_utc = datetime.now(timezone.utc).isoformat()
    
    # 1. Switch Core check
    sw_http_ok, _, sw_latency = check_http("http://127.0.0.1:62326/")
    if not sw_http_ok:
        sw_http_ok, _, sw_latency = check_http("http://127.0.0.1:62326/api/v1/health")
    if not sw_http_ok:
        sw_tcp_ok, sw_latency = check_tcp("127.0.0.1", 62326)
        sw_status = "REACHABLE_TCP_ONLY" if sw_tcp_ok else "UNREACHABLE"
    else:
        sw_status = "CONNECTED"

    # 2. Mattermost check
    mm_http_ok, mm_body, mm_latency = check_http("http://127.0.0.1:62327/api/v4/system/ping")
    if mm_http_ok and mm_body and b"OK" in mm_body:
        mm_status = "CONNECTED"
    else:
        mm_tcp_ok, mm_latency = check_tcp("127.0.0.1", 62327)
        mm_status = "REACHABLE_TCP_ONLY" if mm_tcp_ok else "UNREACHABLE"

    # 3. Local LLM check on AMD ROCm
    llm_http_ok, llm_body, llm_latency = check_http("http://127.0.0.1:8000/v1/models")
    model_name = "QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ"
    if llm_http_ok and llm_body:
        try:
            m_data = json.loads(llm_body)
            models = m_data.get("data", [])
            if models and isinstance(models, list):
                model_name = models[0].get("id", model_name)
            llm_status = "ACTIVE_INFERENCE_READY"
        except Exception:
            llm_status = "REACHABLE_TCP_ONLY"
    else:
        llm_tcp_ok, llm_latency = check_tcp("127.0.0.1", 8000)
        llm_status = "REACHABLE_TCP_ONLY" if llm_tcp_ok else "UNAVAILABLE"

    # 4. Agent process check
    ag_status = "UNKNOWN"
    ag_latency = 0.0
    t_ag = time.perf_counter()
    try:
        ag_proc = subprocess.run(
            ["systemctl", "--user", "is-active", "inneros-switch-liveops.service"],
            capture_output=True, text=True, timeout=0.8
        )
        ag_latency = round((time.perf_counter() - t_ag) * 1000, 2)
        ag_status = "CONNECTED" if ag_proc.stdout.strip() == "active" else "INACTIVE"
    except Exception:
        ag_latency = round((time.perf_counter() - t_ag) * 1000, 2)

    # 5. Evidence Matrix check
    e2e_path = os.path.join(DATA_DIR, "e2e_results.json")
    if os.path.exists(e2e_path):
        try:
            mtime = os.path.getmtime(e2e_path)
            e2e_ts = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
            with open(e2e_path, "r", encoding="utf-8") as f:
                tests = json.load(f)
                e2e_total = len(tests)
                e2e_pass = sum(1 for t in tests if t.get("result") == "PASS")
                e2e_status = "RECORDED_VERIFIED"
                matrix_str = f"{e2e_pass}/{e2e_total} PASS"
        except Exception:
            e2e_status = "UNKNOWN"
            matrix_str = "UNKNOWN"
            e2e_ts = None
    else:
        e2e_status = "UNKNOWN"
        matrix_str = "UNKNOWN"
        e2e_ts = None

    # 6. Last Verified Live Operation Receipt
    ev_path = os.path.join(DATA_DIR, "live_mattermost_evidence.json")
    last_inc_id = None
    last_hash = None
    last_op_ts = None
    if os.path.exists(ev_path):
        try:
            mtime = os.path.getmtime(ev_path)
            last_op_ts = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
            with open(ev_path, "r", encoding="utf-8") as f:
                receipts = json.load(f)
                for r in receipts:
                    if r.get("step") == "INCIDENT_TRIAGE":
                        reply = r.get("reply_text", "")
                        if "INC-" in reply:
                            last_inc_id = "INC-" + reply.split("INC-")[1].split("]")[0].strip()
                    if r.get("step") == "APPROVE_EXECUTE" and r.get("receipt_hash"):
                        raw_h = r.get("receipt_hash")
                        if len(raw_h) >= 24:
                            last_hash = raw_h
        except Exception:
            pass

    return {
        "ok": True,
        "project": "InnerOS LiveOps",
        "hackathon": "Flip the Switch 2026",
        "evaluated_tracks": [
            "Best Business Workflow",
            "Best Personal or Creative Workflow",
            "Best Blog",
            "#HowISwitch"
        ],
        "host_node": "Local AMD ROCm infrastructure",
        "telemetry_timestamp": now_utc,
        "components": {
            "switch_core": {
                "status": sw_status,
                "port": 62326,
                "protocol": "WebSocket + HTTP",
                "latency_ms": sw_latency,
                "role": "Agent Communication & Room Transport"
            },
            "mattermost": {
                "status": mm_status,
                "port": 62327,
                "channel": "#inneros-live-operations",
                "latency_ms": mm_latency,
                "role": "Human-Agent Incident Room"
            },
            "qwen_local_rocm": {
                "status": llm_status,
                "model_id": model_name,
                "engine": "vLLM ROCm 7.2.1 on AMD Radeon AI PRO R9700",
                "latency_ms": llm_latency,
                "role": "Local Sovereign Inference Engine"
            },
            "inneros_agent": {
                "status": ag_status,
                "service": "inneros-switch-liveops.service",
                "node_id": "AMD-1.5",
                "latency_ms": ag_latency,
                "role": "Autonomous Incident Triage & Safety Gate Connector"
            },
            "human_safety_gate": {
                "status": "POLICY_CONFIGURED",
                "mode": "RESTRICTED_READ_ONLY_PUBLIC",
                "physical_actuation_live": False,
                "policy": "Deterministic policy requires authenticated room sender and active unexpired grant ID"
            },
            "evidence_ledger": {
                "status": e2e_status,
                "matrix_pass": matrix_str,
                "recorded_timestamp": e2e_ts,
                "latest_incident_record": f"RECORDED_TEST_INCIDENT: {last_inc_id}" if last_inc_id else None,
                "latest_cryptographic_digest": f"SHA256:{last_hash}" if last_hash else None,
                "evidence_timestamp": last_op_ts
            }
        },
        "public_disclosure": {
            "web_mode": "PUBLIC_READONLY_OPERATIONS",
            "record_source": "Switch and Mattermost evidence archive. Events are recorded tests unless independently verified as production actions.",
            "operational_boundary": "Live actuation is restricted exclusively to authenticated operators inside the sovereign Mattermost room on AMD 1.5."
        }
    }

LAST_PING_TIME = 0.0
LAST_AI_TIME = 0.0
COOLDOWN_SECONDS = 3.0

def run_real_switch_ping():
    global LAST_PING_TIME
    now = time.time()
    if now - LAST_PING_TIME < COOLDOWN_SECONDS:
        rem = round(COOLDOWN_SECONDS - (now - LAST_PING_TIME), 1)
        return {
            "ok": False,
            "step": "PING_AGENT",
            "error": "RATE_LIMITED",
            "message": f"Rate limit active. Please wait {rem}s before next diagnostic ping.",
            "retry_after_s": rem,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    LAST_PING_TIME = now

    env_file = "/home/rlopez/inneros/modules/switch-liveops/compose/.env"
    user_pw = ""
    if os.path.isfile(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MATTERMOST_USER_PASSWORD="):
                    user_pw = line.split("=", 1)[1].strip()
                    break

    mm_url = "http://127.0.0.1:62327"
    channel_id = "r4n59sq7dtyp7d3n3ogomaqfwh"  # #inneros-live-operations

    t0 = time.perf_counter()
    cid = f"CID-LIVE-PING-{uuid.uuid4().hex[:6].upper()}"

    try:
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

        return {
            "ok": passed,
            "step": "PING_AGENT",
            "correlation_id": cid,
            "latency_ms": elapsed,
            "result": "PASS" if passed else "FAIL",
            "transport": "Mattermost -> Switch Core WS -> InnerOS Agent -> Switch Core HTTP -> Mattermost",
            "agent_response": reply_msg.strip() if reply_msg else "Agent response timeout after 5s",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "ok": False,
            "step": "PING_AGENT",
            "correlation_id": cid,
            "latency_ms": elapsed,
            "result": "FAIL",
            "error": str(e),
            "transport": "Mattermost -> Switch Core WS -> InnerOS Agent -> Switch Core HTTP -> Mattermost",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

def run_real_qwen_inference(question=None):
    global LAST_AI_TIME
    now = time.time()
    if now - LAST_AI_TIME < COOLDOWN_SECONDS:
        rem = round(COOLDOWN_SECONDS - (now - LAST_AI_TIME), 1)
        return {
            "ok": False,
            "step": "LOCAL_AI_INFERENCE",
            "error": "RATE_LIMITED",
            "message": f"Rate limit active. Please wait {rem}s before next AI diagnostic.",
            "retry_after_s": rem,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    LAST_AI_TIME = now

    model_name = "QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ"
    cid = f"CID-AI-{uuid.uuid4().hex[:6].upper()}"

    if not question or not isinstance(question, str) or len(question.strip()) == 0:
        question = "Explain how sovereign agent incident triage prevents downtime on local AMD infrastructure."
    else:
        question = question.strip()[:180]

    t0 = time.perf_counter()
    try:
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

        return {
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
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "ok": False,
            "step": "LOCAL_AI_INFERENCE",
            "correlation_id": cid,
            "model_id": model_name,
            "hardware": "AMD Radeon AI PRO R9700 (ROCm 7.2.1)",
            "prompt": question,
            "error": str(e),
            "latency_ms": elapsed,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

def get_sanitized_evidence():
    ev_path = os.path.join(DATA_DIR, "live_mattermost_evidence.json")
    if not os.path.exists(ev_path):
        return []

    sanitized = []
    try:
        with open(ev_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        archive_time = datetime.fromtimestamp(os.path.getmtime(ev_path), tz=timezone.utc).isoformat()
        for item in raw:
            if not isinstance(item, dict):
                continue
            step = item.get("step", "UNKNOWN")
            if step not in {"PING", "STATUS", "INCIDENT_TRIAGE", "AUTH_BLOCK", "APPROVE_EXECUTE"}:
                continue
            cid = item.get("correlation_id", "N/A")
            latency = item.get("latency_ms", 0.0)
            status = item.get("status", "UNKNOWN")

            # Redact raw user IDs, post IDs, auth tokens, internal paths
            if step == "PING":
                desc = "Bidirectional heartbeat: Mattermost -> Switch Core WS -> Agent -> Switch Core HTTP -> Mattermost"
            elif step == "STATUS":
                desc = "Agent self-report: Node AMD-1.5, Room #inneros-live-operations, Local LLM Online, Safety Gate Active"
            elif step == "INCIDENT_TRIAGE":
                desc = "Recorded agent triage test: telemetry anomaly analyzed with local Qwen and a gated diagnostic action proposed"
            elif step == "AUTH_BLOCK":
                desc = "Deterministic policy block: Unauthorized or nonexistent action ID rejected; zero physical action taken"
            elif step == "APPROVE_EXECUTE":
                desc = "Authenticated approval test: safe diagnostic execution and SHA-256 receipt recorded; physical device actuation is not claimed"
            else:
                desc = "System coordination event"

            record = {
                "step": step,
                "correlation_id": cid,
                "latency_ms": latency,
                "result": status,
                "classification": "RECORDED_TEST_RESULT",
                "summary": desc,
                "archive_timestamp": archive_time,
            }
            digest = item.get("receipt_hash")
            if isinstance(digest, str) and len(digest.strip(".")) >= 16 and all(c in "0123456789abcdefABCDEF." for c in digest):
                clean_d = digest.strip(".")
                record["receipt_digest"] = "SHA256:" + clean_d.lower() + ("..." if len(clean_d) < 64 else "")

            sanitized.append(record)
        sanitized = sanitized[-20:]
    except Exception as e:
        sanitized = [{"error": "Unable to read evidence archive safely"}]

    return sanitized


class SecureLiveOpsHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def apply_security_headers(self, origin=None):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self' data:;")
        
        # Scoped CORS
        if origin and origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_HEAD(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html", "/api/liveops/status", "/api/liveops/evidence", "/api/liveops/ping", "/api/liveops/test_ai"):
            self.send_response(200)
            self.apply_security_headers()
            self.end_headers()
        elif path.startswith("/api/operator"):
            self.send_response(401)
            self.apply_security_headers()
            self.end_headers()
        else:
            _, ext = os.path.splitext(path)
            if ext.lower() not in SAFE_STATIC_EXTENSIONS or ".." in path:
                self.send_error(403, "Access to this resource type is forbidden")
            else:
                super().do_HEAD()

    def do_OPTIONS(self):
        origin = self.headers.get("Origin", "")
        self.send_response(204)
        self.apply_security_headers(origin)
        self.end_headers()

    def do_GET(self):
        origin = self.headers.get("Origin", "")
        parsed = urlparse(self.path)
        path = parsed.path

        # 1. Main Landing Page
        if path in ("/", "/index.html"):
            index_path = os.path.join(BASE_DIR, "index.html")
            if os.path.isfile(index_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.apply_security_headers(origin)
                self.end_headers()
                with open(index_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "Frontend file not found")
                return

        # 2. Public Live Telemetry Endpoint
        elif path == "/api/liveops/status":
            data = get_system_telemetry()
            payload = json.dumps(data, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.apply_security_headers(origin)
            self.end_headers()
            self.wfile.write(payload)
            return

        # 3. Sanitized Public Evidence Receipts
        elif path == "/api/liveops/evidence":
            data = get_sanitized_evidence()
            payload = json.dumps(data, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.apply_security_headers(origin)
            self.end_headers()
            self.wfile.write(payload)
            return

        # 4. Public Diagnostic: Ping Agent through Switch
        elif path == "/api/liveops/ping":
            data = run_real_switch_ping()
            payload = json.dumps(data, indent=2).encode("utf-8")
            status_code = 429 if data.get("error") == "RATE_LIMITED" else (200 if data.get("ok") else 500)
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.apply_security_headers(origin)
            self.end_headers()
            self.wfile.write(payload)
            return

        # 5. Public Diagnostic: Read-only Qwen AI Inference on AMD Radeon PRO R9700
        elif path == "/api/liveops/test_ai":
            params = parse_qs(parsed.query)
            q = params.get("q", [None])[0]
            data = run_real_qwen_inference(q)
            payload = json.dumps(data, indent=2).encode("utf-8")
            status_code = 429 if data.get("error") == "RATE_LIMITED" else (200 if data.get("ok") else 500)
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.apply_security_headers(origin)
            self.end_headers()
            self.wfile.write(payload)
            return

        # 6. Operator Endpoints (Protected - require valid authentication)
        elif path.startswith("/api/operator"):
            auth_header = self.headers.get("Authorization", "")
            expected_token = os.environ.get("LIVEOPS_OPERATOR_TOKEN", "")
            if not expected_token or auth_header != f"Bearer {expected_token}":
                self.send_response(401)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.apply_security_headers(origin)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Unauthorized operator access. Valid Bearer token required."}).encode("utf-8"))
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.apply_security_headers(origin)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "Authorized operator session active on AMD-1.5"}).encode("utf-8"))
            return

        # 7. Safe Static Files (Explicitly allowlisted extensions only)
        else:
            _, ext = os.path.splitext(path)
            if ext.lower() not in SAFE_STATIC_EXTENSIONS or ".." in path:
                self.send_error(403, "Access to this resource type is forbidden")
                return
            
            clean_rel = os.path.normpath(path.lstrip("/"))
            full_path = os.path.join(BASE_DIR, clean_rel)
            if not full_path.startswith(BASE_DIR) or not os.path.isfile(full_path):
                self.send_error(404, "Resource not found")
                return

            return super().do_GET()

    def do_POST(self):
        origin = self.headers.get("Origin", "")
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/liveops/ping":
            data = run_real_switch_ping()
            payload = json.dumps(data, indent=2).encode("utf-8")
            status_code = 429 if data.get("error") == "RATE_LIMITED" else (200 if data.get("ok") else 500)
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.apply_security_headers(origin)
            self.end_headers()
            self.wfile.write(payload)
            return

        elif path == "/api/liveops/test_ai":
            q = None
            try:
                length = int(self.headers.get("Content-Length", 0))
                if length > 0 and length < 2048:
                    body = self.rfile.read(length).decode("utf-8")
                    req_json = json.loads(body)
                    q = req_json.get("question") or req_json.get("q")
            except Exception:
                pass
            data = run_real_qwen_inference(q)
            payload = json.dumps(data, indent=2).encode("utf-8")
            status_code = 429 if data.get("error") == "RATE_LIMITED" else (200 if data.get("ok") else 500)
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.apply_security_headers(origin)
            self.end_headers()
            self.wfile.write(payload)
            return

        elif path == "/api/liveops/status":
            data = get_system_telemetry()
            payload = json.dumps(data, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.apply_security_headers(origin)
            self.end_headers()
            self.wfile.write(payload)
            return

        # Explicitly deny all other POST methods to prevent unauthorized actuation or state changes
        self.send_error(501, "Unsupported method ('POST'). Modifying operational state is restricted.")


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    print(f"Starting Secure InnerOS LiveOps Web Server on {HOST}:{PORT}")
    with socketserver.TCPServer((HOST, PORT), SecureLiveOpsHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
