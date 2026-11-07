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
import urllib.request
import urllib.error
import http.server
import socketserver
from datetime import datetime, timezone
from urllib.parse import urlparse

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

    # 4. Evidence Matrix check
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

    # 5. Last Verified Live Operation Receipt
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
                "latest_incident_record": f"RECORDED_SYNTHETIC: {last_inc_id}" if last_inc_id else None,
                "latest_cryptographic_digest": f"SHA256:{last_hash}" if last_hash else None,
                "evidence_timestamp": last_op_ts
            }
        },
        "public_disclosure": {
            "web_mode": "PUBLIC_DEMO_AND_READONLY_TELEMETRY",
            "interactive_simulation": "All web buttons on this page run simulated workflows. No physical devices are actuated from the web.",
            "operational_boundary": "Live actuation is restricted exclusively to authenticated operators inside the sovereign Mattermost room on AMD 1.5."
        }
    }

def get_sanitized_evidence():
    ev_path = os.path.join(DATA_DIR, "live_mattermost_evidence.json")
    if not os.path.exists(ev_path):
        return []

    sanitized = []
    try:
        with open(ev_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        for item in raw:
            step = item.get("step", "UNKNOWN")
            cid = item.get("correlation_id", "N/A")
            latency = item.get("latency_ms", 0.0)
            status = item.get("status", "UNKNOWN")

            # Redact raw user IDs, post IDs, auth tokens, internal paths
            if step == "PING":
                desc = "Bidirectional heartbeat: Mattermost -> Switch Core WS -> Agent -> Switch Core HTTP -> Mattermost"
            elif step == "STATUS":
                desc = "Agent self-report: Node AMD-1.5, Room #inneros-live-operations, Local LLM Online, Safety Gate Active"
            elif step == "INCIDENT_TRIAGE":
                desc = "Synthetic incident triage: Telemetry latency anomaly analyzed by local Qwen3-Coder 30B AWQ; safe diagnostic action proposed"
            elif step == "AUTH_BLOCK":
                desc = "Deterministic policy block: Unauthorized or nonexistent action ID rejected; zero physical action taken"
            elif step == "APPROVE_EXECUTE":
                desc = "Authorized execution: Gated safe diagnostic cycle executed on edge target; cryptographic SHA-256 receipt recorded"
            else:
                desc = "System coordination event"

            record = {
                "step": step,
                "correlation_id": cid,
                "latency_ms": latency,
                "result": status,
                "classification": "RECORDED_TEST_RESULT",
                "summary": desc,
            }
            if item.get("receipt_hash"):
                record["receipt_digest"] = "SHA256:" + str(item.get("receipt_hash"))

            sanitized.append(record)
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
        if path in ("/", "/index.html", "/api/liveops/status", "/api/liveops/evidence"):
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

        # 4. Operator Endpoints (Protected - require valid authentication)
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

        # 5. Safe Static Files (Explicitly allowlisted extensions only)
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


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    print(f"Starting Secure InnerOS LiveOps Web Server on {HOST}:{PORT}")
    with socketserver.TCPServer((HOST, PORT), SecureLiveOpsHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
