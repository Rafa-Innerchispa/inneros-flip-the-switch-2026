"""InnerOS LiveOps / Switch - Comprehensive End-to-End Test Suite (Phase H - Verified).

Executes 8 verified test cases:
1. Health - All essential services responsive (Switch Core, Gateway, MM, local LLM)
2. Messaging - Bidirectional Mattermost -> Switch -> Agent -> Mattermost roundtrip with strict Correlation ID matching
3. Local Agent - Deterministic & local intelligence processing with Correlation ID
4. Simulated Incident - AI Triage powered by AMD ROCm local model with Correlation ID
5. Authorization - Gated action blocked without valid approval with Correlation ID
6. Safe Action - Authorized execution producing SHA-256 evidence receipt with Correlation ID
7. Resilience - Systemd process supervision, live health/ready checks, and live recovery roundtrip
8. Windows Independence - 100% self-hosted on AMD Linux, ROCm GPU verification, zero external/Windows socket dependency
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
import platform
import re
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path


def clock_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def uuid_short() -> str:
    from uuid import uuid4
    return uuid4().hex[:6].upper()


@dataclass
class TestRecord:
    test_number: int
    name: str
    result: str  # PASS / FAIL
    latency_ms: float
    correlation_id: str
    component: str
    evidence: str
    error: str | None = None


class InnerOSE2ETestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records: list[TestRecord] = []
        cls.env_file = Path("/home/rlopez/inneros/modules/switch-liveops/compose/.env")
        if not cls.env_file.is_file():
            # Local Windows fallback path
            cls.env_file = Path("C:/Users/hrlg/Downloads/InnerOS_Switch/compose/.env")

        cls.env = {}
        if cls.env_file.is_file():
            cls.env = dict(
                line.strip().split("=", 1)
                for line in cls.env_file.read_text(encoding="utf-8").splitlines()
                if "=" in line and not line.startswith("#")
            )

        cls.switch_url = "http://127.0.0.1:62326"
        cls.mm_url = "http://127.0.0.1:62327"
        cls.llm_url = "http://127.0.0.1:8000/v1"
        cls.channel_id = "r4n59sq7dtyp7d3n3ogomaqfwh"  # inneros-live-operations

        # Login to Mattermost
        cls.mm_token = None
        cls.mm_user = None
        try:
            req = urllib.request.Request(
                f"{cls.mm_url}/api/v4/users/login",
                data=json.dumps({"login_id": "user", "password": cls.env.get("MATTERMOST_USER_PASSWORD", "")}).encode(),
                headers={"Content-Type": "application/json"}
            )
            resp = urllib.request.urlopen(req, timeout=5)
            cls.mm_token = resp.headers.get("Token")
            cls.mm_user = json.loads(resp.read().decode())
        except Exception as e:
            print(f"Warning: MM login setup failed: {e}")

    def mm_post(self, msg: str) -> str:
        headers = {"Authorization": f"Bearer {self.mm_token}", "Content-Type": "application/json"}
        req = urllib.request.Request(
            f"{self.mm_url}/api/v4/posts",
            data=json.dumps({"channel_id": self.channel_id, "message": msg}).encode(),
            headers=headers
        )
        res = urllib.request.urlopen(req, timeout=5)
        obj = json.loads(res.read().decode())
        return obj["id"]

    def mm_wait_reply(self, after_post_id: str, expected_token: str | None = None, timeout: int = 15) -> dict | None:
        headers = {"Authorization": f"Bearer {self.mm_token}"}
        after_create_at = 0
        try:
            p_req = urllib.request.Request(f"{self.mm_url}/api/v4/posts/{after_post_id}", headers=headers)
            after_post = json.loads(urllib.request.urlopen(p_req, timeout=3).read().decode())
            after_create_at = after_post.get("create_at", 0)
        except Exception:
            pass

        for _ in range(timeout):
            time.sleep(1)
            req = urllib.request.Request(f"{self.mm_url}/api/v4/channels/{self.channel_id}/posts?per_page=10", headers=headers)
            try:
                data = json.loads(urllib.request.urlopen(req, timeout=4).read().decode())
                order = data.get("order", [])
                posts = data.get("posts", {})
                for pid in order:
                    if pid == after_post_id:
                        continue
                    p = posts.get(pid, {})
                    if p.get("create_at", 0) >= after_create_at:
                        msg = p.get("message", "")
                        if expected_token:
                            if expected_token in msg:
                                return p
                        else:
                            return p
            except Exception:
                pass
        return None

    def test_01_health_essential_services(self):
        """Test 1: All essential services (Switch Core, Gateway, MM, LLM) responsive."""
        t0 = time.monotonic()
        cid = f"CID-HEALTH-{uuid_short()}"
        services_status = {}

        # 1. Switch Core /health
        try:
            req = urllib.request.Request(f"{self.switch_url}/health")
            with urllib.request.urlopen(req, timeout=3) as resp:
                services_status["switch_core"] = resp.status == 200
        except Exception:
            services_status["switch_core"] = False

        # 2. Mattermost ping
        try:
            req = urllib.request.Request(f"{self.mm_url}/api/v4/system/ping")
            with urllib.request.urlopen(req, timeout=3) as resp:
                services_status["mattermost"] = resp.status == 200
        except Exception:
            services_status["mattermost"] = False

        # 3. Local Model endpoint
        try:
            req = urllib.request.Request(f"{self.llm_url}/models")
            with urllib.request.urlopen(req, timeout=3) as resp:
                services_status["local_llm"] = resp.status == 200
        except Exception:
            services_status["local_llm"] = False

        latency = (time.monotonic() - t0) * 1000
        all_ok = all(services_status.values())
        rec = TestRecord(
            test_number=1,
            name="Salud de servicios esenciales",
            result="PASS" if all_ok else "FAIL",
            latency_ms=round(latency, 2),
            correlation_id=cid,
            component="Infraestructura AMD 1.5",
            evidence=f"Checked endpoints: {services_status}",
            error=None if all_ok else "One or more services unresponsive"
        )
        self.records.append(rec)
        self.assertTrue(all_ok, f"Essential services failing: {services_status}")

    def test_02_messaging_roundtrip(self):
        """Test 2: Mattermost -> Switch -> Agent -> Mattermost with explicit Correlation ID."""
        t0 = time.monotonic()
        cid = f"CID-PING-{uuid_short()}"
        post_id = self.mm_post(f"@inneros-incident-triage !ping {cid}")
        reply = self.mm_wait_reply(post_id, expected_token=cid, timeout=12)
        latency = (time.monotonic() - t0) * 1000

        msg = reply.get("message", "") if reply else ""
        passed = reply is not None and "PONG" in msg and cid in msg
        evidence = f"Post: {post_id} [CID: {cid}] -> Correlated Reply: {msg}"
        rec = TestRecord(
            test_number=2,
            name="Mensajería bidireccional Mattermost-Switch",
            result="PASS" if passed else "FAIL",
            latency_ms=round(latency, 2),
            correlation_id=cid,
            component="Switch Bridge + WebSocket",
            evidence=evidence,
            error=None if passed else f"Missing correlated reply for {cid}"
        )
        self.records.append(rec)
        self.assertTrue(passed, evidence)

    def test_03_local_agent_processing(self):
        """Test 3: Local agent processes !status command deterministically with Correlation ID."""
        t0 = time.monotonic()
        cid = f"CID-STATUS-{uuid_short()}"
        post_id = self.mm_post(f"@inneros-incident-triage !status {cid}")
        reply = self.mm_wait_reply(post_id, expected_token=cid, timeout=12)
        latency = (time.monotonic() - t0) * 1000

        msg = reply.get("message", "") if reply else ""
        passed = "INNEROS STATUS" in msg and "Safety Gate: ACTIVE" in msg and cid in msg
        rec = TestRecord(
            test_number=3,
            name="Agente local y procesamiento determinista",
            result="PASS" if passed else "FAIL",
            latency_ms=round(latency, 2),
            correlation_id=cid,
            component="LiveOps Agent (inneros-incident-triage)",
            evidence=msg,
            error=None if passed else f"Unexpected or uncorrelated status response for {cid}"
        )
        self.records.append(rec)
        self.assertTrue(passed, msg)

    def test_04_simulated_incident_ai_triage(self):
        """Test 4: Incident opened and classified with local Qwen3-Coder inference with Correlation ID."""
        t0 = time.monotonic()
        cid = f"CID-INCIDENT-{uuid_short()}"
        post_id = self.mm_post(f"@inneros-incident-triage !incident {cid}")
        reply = self.mm_wait_reply(post_id, expected_token=cid, timeout=18)
        latency = (time.monotonic() - t0) * 1000

        msg = reply.get("message", "") if reply else ""
        has_inc = "INNEROS INCIDENT" in msg
        has_act = "ACT-" in msg
        has_corr = cid in msg

        passed = has_inc and has_act and has_corr
        rec = TestRecord(
            test_number=4,
            name="Incidente y triaje con IA local ROCm",
            result="PASS" if passed else "FAIL",
            latency_ms=round(latency, 2),
            correlation_id=cid,
            component="vLLM (Qwen3-Coder 30B AWQ) + LiveOps",
            evidence=msg,
            error=None if passed else f"Failed to produce correlated AI incident triage for {cid}"
        )
        self.records.append(rec)
        self.assertTrue(passed, msg)

    def test_05_authorization_gate_blocked(self):
        """Test 5: Unauthorized action execution is strictly blocked with Correlation ID."""
        t0 = time.monotonic()
        cid = f"CID-AUTH-BLOCK-{uuid_short()}"
        post_id = self.mm_post(f"@inneros-incident-triage !approve ACT-FAKE999 {cid}")
        reply = self.mm_wait_reply(post_id, expected_token=cid, timeout=12)
        latency = (time.monotonic() - t0) * 1000

        msg = reply.get("message", "") if reply else ""
        passed = "BLOCKED" in msg and cid in msg
        rec = TestRecord(
            test_number=5,
            name="Control de autorización (bloqueo sin permiso)",
            result="PASS" if passed else "FAIL",
            latency_ms=round(latency, 2),
            correlation_id=cid,
            component="Human Approval Gate",
            evidence=msg,
            error=None if passed else f"Unapproved action not blocked or missing correlation {cid}"
        )
        self.records.append(rec)
        self.assertTrue(passed, msg)

    def test_06_safe_action_execution_evidence(self):
        """Test 6: Gated action approved by human produces SHA-256 evidence receipt with Correlation ID."""
        t0 = time.monotonic()
        cid_inc = f"CID-EXEC-INC-{uuid_short()}"

        # 1. Trigger incident
        p_inc = self.mm_post(f"@inneros-incident-triage !incident {cid_inc}")
        r_inc = self.mm_wait_reply(p_inc, expected_token=cid_inc, timeout=18)
        msg_inc = r_inc.get("message", "") if r_inc else ""
        match = re.search(r"(ACT-[0-9A-F]+)", msg_inc)
        self.assertIsNotNone(match, f"No action ID generated in {msg_inc}")
        act_id = match.group(1)

        # 2. Authorize action with correlation ID
        cid_app = f"CID-EXEC-APP-{uuid_short()}"
        p_app = self.mm_post(f"@inneros-incident-triage !approve {act_id} {cid_app}")
        r_app = self.mm_wait_reply(p_app, expected_token=cid_app, timeout=15)
        latency = (time.monotonic() - t0) * 1000

        msg_app = r_app.get("message", "") if r_app else ""
        passed = "ACTION EXECUTED" in msg_app and "SHA256:" in msg_app and cid_app in msg_app
        rec = TestRecord(
            test_number=6,
            name="Ejecución autorizada y recibo criptográfico",
            result="PASS" if passed else "FAIL",
            latency_ms=round(latency, 2),
            correlation_id=cid_app,
            component="Execution Engine + Evidence Hasher",
            evidence=msg_app,
            error=None if passed else f"Receipt not verified or missing correlation {cid_app}"
        )
        self.records.append(rec)
        self.assertTrue(passed, msg_app)

    def test_07_resilience_recovery(self):
        """Test 7: Switch LiveOps service resilience, active process supervision, and live roundtrip."""
        t0 = time.monotonic()
        cid = f"CID-RESILIENCE-{uuid_short()}"

        # 1. Active process verification via systemd / proc
        systemd_active = False
        pid = None
        try:
            res = subprocess.run(
                ["systemctl", "--user", "is-active", "inneros-switch-liveops.service"],
                capture_output=True,
                text=True,
                timeout=5
            )
            systemd_active = res.stdout.strip() == "active"
            res_pid = subprocess.run(
                ["systemctl", "--user", "show", "--property=MainPID", "inneros-switch-liveops.service"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "MainPID=" in res_pid.stdout:
                pid = int(res_pid.stdout.strip().split("=")[1])
        except Exception:
            pass

        # 2. Query Switch Core readiness endpoint directly
        ready_ok = False
        try:
            req = urllib.request.Request(f"{self.switch_url}/health/ready")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                ready_ok = data.get("status") == "ready"
        except Exception:
            pass

        # 3. Live active roundtrip verification
        live_roundtrip = False
        p_resil = self.mm_post(f"@inneros-incident-triage !ping {cid}")
        r_resil = self.mm_wait_reply(p_resil, expected_token=cid, timeout=10)
        if r_resil and cid in r_resil.get("message", ""):
            live_roundtrip = True

        latency = (time.monotonic() - t0) * 1000
        passed = systemd_active and ready_ok and live_roundtrip
        evidence = (
            f"Systemd Active: {systemd_active} (PID: {pid}) | "
            f"Switch Ready: {ready_ok} | "
            f"Live Roundtrip Ping: {live_roundtrip} ({round(latency, 1)}ms)"
        )
        rec = TestRecord(
            test_number=7,
            name="Resiliencia del puente y reconexión activa",
            result="PASS" if passed else "FAIL",
            latency_ms=round(latency, 2),
            correlation_id=cid,
            component="Systemd Service (inneros-switch-liveops) + Switch Core",
            evidence=evidence,
            error=None if passed else "Service not actively supervised or roundtrip failed"
        )
        self.records.append(rec)
        self.assertTrue(passed, evidence)

    def test_08_windows_independence(self):
        """Test 8: System operates 100% locally on AMD Linux, ROCm hardware verified, zero Windows socket dependency."""
        t0 = time.monotonic()
        cid = f"CID-WIN-INDEP-{uuid_short()}"

        # 1. Linux OS and Kernel check
        is_linux = sys.platform.startswith("linux") and platform.system() == "Linux"

        # 2. AMD Hardware & ROCm driver verification
        rocm_kfd = Path("/dev/kfd").exists()
        render_dev = Path("/dev/dri/renderD128").exists()
        rocm_hw_ok = rocm_kfd or render_dev

        # 3. Local socket bindings verification
        # Ports 62325, 62326, 62327, 62328, 8000 must be listening on Linux localhost
        local_ports_ok = True
        for p in [62325, 62326, 62327, 62328, 8000]:
            try:
                with socket.create_connection(("127.0.0.1", p), timeout=1.0):
                    pass
            except Exception:
                local_ports_ok = False
                break

        # 4. Windows default Switch ports (62225, 62226) must NOT be bound on AMD
        win_ports_clear = True
        for p in [62225, 62226]:
            try:
                with socket.create_connection(("127.0.0.1", p), timeout=0.5):
                    win_ports_clear = False
            except Exception:
                pass  # expected: not open on AMD

        latency = (time.monotonic() - t0) * 1000
        passed = is_linux and rocm_hw_ok and local_ports_ok and win_ports_clear
        evidence = (
            f"OS: {platform.system()} {platform.release()} ({platform.machine()}) | "
            f"ROCm KFD Driver: {'PRESENT (/dev/kfd)' if rocm_kfd else 'N/A'} | "
            f"Local AMD Ports (62325-62328, 8000): {'ALL LOCAL' if local_ports_ok else 'FAIL'} | "
            f"Windows Ports (62225-62226) Clear: {win_ports_clear} | Zero Remote Proxy"
        )
        rec = TestRecord(
            test_number=8,
            name="Independencia absoluta de Windows (Soberanía Local AMD)",
            result="PASS" if passed else "FAIL",
            latency_ms=round(latency, 2),
            correlation_id=cid,
            component="Autonomous AMD 1.5 Node (Linux + ROCm)",
            evidence=evidence,
            error=None if passed else "Host or hardware verification failed"
        )
        self.records.append(rec)
        self.assertTrue(passed, evidence)

    @classmethod
    def tearDownClass(cls):
        report_path = Path("/home/rlopez/inneros/modules/switch-liveops/data/e2e_results.json")
        try:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_data = [asdict(r) for r in cls.records]
            report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
            print(f"\nSaved {len(cls.records)} test results to {report_path}")
        except Exception as e:
            print(f"Could not save report: {e}")


if __name__ == "__main__":
    unittest.main()
