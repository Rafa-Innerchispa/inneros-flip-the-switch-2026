#!/usr/bin/env python3
"""One-command Windows Switch Console v0.40.1 recovery and real agent bridge.

Only contacts 127.0.0.1 Switch, creates a personally owned short-lived-in-use
registration key (revoked after registration), joins an EXISTING room, and
launches a read-only ping/status responder. Does NOT actuate Home Assistant.
Any read from HA needs explicitly supplied local credentials/allowlisted lights.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote, urlsplit
from urllib.request import Request, HTTPCookieProcessor, ProxyHandler, build_opener
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:62226"
ROOM_SLUG = "inneros-live-operations"
AGENT_NAME = "inneros-incident-triage"
MARKER = "Local-first Switch agent for real Home Assistant light observations and human-approved actions"
KEY_LABEL = "InnerOS LiveOps temporary local registration"
HOME = Path.home() / ".config" / "inneros-switch"
CREDS = HOME / "agent-credentials.json"
STATUS = HOME / "bridge-status.json"
LOG = HOME / "inneros-liveops-bridge.log"
PID = HOME / "inneros-liveops-bridge.pid"
NATIVE_ENV = Path(os.getenv("APPDATA", "")) / "switchdash" / "local-switch-server" / "native" / "run" / "switch-core.env"


class StageError(RuntimeError):
    def __init__(self, phase: str, kind: str):
        self.phase = phase
        self.kind = kind
        super().__init__(f"{phase}: {kind}")


def clock():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def banner(msg):
    print("[INNEROS] " + msg, flush=True)


def safe_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    p = path.with_suffix(path.suffix + ".tmp")
    with p.open("w", encoding="utf-8") as out:
        json.dump(value, out)
    try:
        os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    p.replace(path)


def read_native():
    if not NATIVE_ENV.is_file():
        raise StageError("native-env", "missing-file")
    data = {}
    with NATIVE_ENV.open(encoding="utf-8-sig") as fh:
        for line in fh:
            k, sep, v = line.rstrip("\r\n").partition("=")
            if sep and k in {"GATEWAY_ADMIN_EMAIL", "GATEWAY_ADMIN_PASSWORD", "SERVER_PORT"}:
                data[k] = v
    if data.get("SERVER_PORT") != "62226":
        raise StageError("native-env", "port-mismatch")
    if not all(data.get(k) for k in ("GATEWAY_ADMIN_EMAIL", "GATEWAY_ADMIN_PASSWORD")):
        raise StageError("native-env", "admin-config-missing")
    return data


def client():
    # Do not send any local admin credential through a system HTTP proxy.
    return build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()))


def call(opener, phase, method, path, data=None, *, token=None, timeout=60):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = Request(BASE + path, method=method, headers=headers,
                  data=json.dumps(data).encode("utf-8") if data is not None else None)
    t = time.monotonic()
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read(3_000_000)
        result = json.loads(raw) if raw else {}
        banner(f"{phase}: HTTP OK ({time.monotonic()-t:.1f}s)")
        return result
    except HTTPError as exc:
        banner(f"{phase}: HTTP {exc.code} ({time.monotonic()-t:.1f}s)")
        raise StageError(phase, "http-" + str(exc.code)) from exc
    except (URLError, TimeoutError, socket.timeout, ConnectionError, OSError, ValueError) as exc:
        banner(f"{phase}: {type(exc).__name__} ({time.monotonic()-t:.1f}s)")
        raise StageError(phase, type(exc).__name__) from None


def want_list(x, label):
    if not isinstance(x, list):
        raise StageError(label, "not-list")
    return x


def expected_agent(agents, owner):
    matches = [a for a in agents if isinstance(a, dict) and a.get("name") == AGENT_NAME]
    if len(matches) > 1:
        raise StageError("agent-lookup", "duplicate-name")
    if not matches:
        return None
    a = matches[0]
    if (a.get("owner_id") != owner or
            not isinstance(a.get("description"), str) or
            not a["description"].startswith(MARKER[:38])):
        raise StageError("agent-lookup", "existing-agent-not-owned-by-inneros")
    return a


def create_or_reveal_key(opener):
    keys = want_list(call(opener, "KEYS-LIST", "GET", "/gateway/api-keys"), "KEYS-LIST")
    matches = [k for k in keys if isinstance(k, dict) and k.get("label") == KEY_LABEL and k.get("type") == "registration"]
    matches.sort(key=lambda a: a.get("created_at", ""), reverse=True)
    if matches:
        rec = call(opener, "KEYS-RECOVER", "GET", "/gateway/api-keys/" + quote(matches[0]["id"], safe="") + "/reveal")
        key = rec.get("key") if isinstance(rec, dict) else None
        if not isinstance(key, str) or len(key) < 20:
            raise StageError("KEYS-RECOVER", "invalid-key")
        banner("Clave temporal anterior recuperada en memoria local (no se muestra).")
        return key, matches[0]["id"]
    try:
        result = call(opener, "KEYS-CREATE", "POST", "/gateway/api-keys", {"label": KEY_LABEL})
        if not isinstance(result, dict) or not result.get("key") or not result.get("id"):
            raise StageError("KEYS-CREATE", "invalid-response")
        return result["key"], result["id"]
    except StageError as exc:
        if exc.kind not in {"TimeoutError", "timeout", "URLError"}:
            raise
        # Non-idempotent POST may have succeeded before timeout: GET+reveal, not another POST.
        banner("KEYS-CREATE: verificando si la clave ya fue creada (sin duplicar).")
        keys = want_list(call(opener, "KEYS-RECHECK", "GET", "/gateway/api-keys"), "KEYS-RECHECK")
        m = [k for k in keys if isinstance(k, dict) and k.get("label") == KEY_LABEL and k.get("type") == "registration"]
        if len(m) != 1:
            raise StageError("KEYS-RECHECK", "ambiguous-creation")
        rec = call(opener, "KEYS-RECOVER", "GET", "/gateway/api-keys/" + quote(m[0]["id"], safe="") + "/reveal")
        return rec["key"], m[0]["id"]


def registration_payload(overwrite):
    # This shape matches the published Switch Console v0.40.1 agent schema.
    return {"name": AGENT_NAME, "display_name": "InnerOS LiveOps",
            "description": MARKER, "connector_type": "inneros-local-python",
            "integration_profile": {"connection_model": "always_on", "message_exchange": True,
                                    "pre_invocation_mediation": [], "post_invocation_mediation": [],
                                    "event_reporting": []},
            "overwrite": bool(overwrite)}


def register(opener, token, preexisting, owner):
    try:
        return call(opener, "AGENT-REGISTER", "POST", "/agents",
                    registration_payload(preexisting), token=token, timeout=70)
    except StageError as exc:
        if exc.kind not in {"TimeoutError", "timeout", "URLError", "http-409"}:
            raise
        # After an uncertain write, query the registry. Do not blindly POST twice.
        agents = want_list(call(opener, "AGENT-RECHECK", "GET", "/gateway/agents"), "AGENT-RECHECK")
        found = expected_agent(agents, owner)
        if not found:
            raise StageError("AGENT-RECHECK", "registration-not-complete")
        banner("El agente existe; se recupera la clave re-registrando SOLO nuestro agente.")
        return call(opener, "AGENT-RECOVER", "POST", "/agents",
                    registration_payload(True), token=token, timeout=70)


def find_room(rooms):
    def normalize(r):
        return str(r.get("name", "")).strip().lstrip("#").split(": ")[-1].lower()
    matches = [r for r in rooms if isinstance(r, dict) and normalize(r) == ROOM_SLUG]
    if len(matches) != 1:
        raise StageError("ROOM-FIND", "room-not-unique-or-not-found")
    if not matches[0].get("id") or matches[0].get("archived"):
        raise StageError("ROOM-FIND", "invalid-room")
    return matches[0]


def verified_creds():
    if not CREDS.is_file():
        return None
    data = json.loads(CREDS.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or data.get("base_url") != BASE or
            not isinstance(data.get("agent_id"), str) or not isinstance(data.get("api_key"), str)):
        raise StageError("CREDS", "existing-credentials-invalid")
    return data


def process_running(pid):
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid)
        if not h:
            return False
        code = ctypes.c_ulong()
        try:
            return bool(ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259
        finally:
            ctypes.windll.kernel32.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def launch_bot(room, approver):
    HOME.mkdir(parents=True, exist_ok=True)
    if PID.exists():
        try:
            old = int(PID.read_text(encoding="utf-8"))
        except ValueError:
            old = -1
        if process_running(old):
            banner("BRIDGE: proceso anterior activo, no se duplica: PID " + str(old))
            return old
    status = {"state": "starting", "room": room, "at": clock()}
    safe_json(STATUS, status)
    with LOG.open("a", encoding="utf-8") as log:
        args = [sys.executable, "-u", str(Path(__file__).resolve()), "--serve",
                "--room", room, "--approver", approver]
        kw = {"stdin": subprocess.DEVNULL, "stdout": log, "stderr": subprocess.STDOUT,
              "cwd": str(ROOT), "close_fds": True}
        if os.name == "nt":
            kw["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(args, **kw)
    PID.write_text(str(proc.pid), encoding="utf-8")
    banner("BRIDGE: proceso en ejecución PID " + str(proc.pid))
    return proc.pid


def setup():
    HOME.mkdir(parents=True, exist_ok=True)
    opener = client()
    banner("Switch 0.40.1: conectando sin utilizar Codex, Cursor ni Mattermost Admin.")
    health = call(opener, "HEALTH", "GET", "/health", timeout=12)
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise StageError("HEALTH", "not-ok")
    cfg = read_native()
    login = call(opener, "ADMIN-LOGIN", "POST", "/gateway/auth/login",
                 {"email": cfg["GATEWAY_ADMIN_EMAIL"], "password": cfg["GATEWAY_ADMIN_PASSWORD"]}, timeout=70)
    if not isinstance(login, dict) or login.get("role") != "admin" or not login.get("id"):
        raise StageError("ADMIN-LOGIN", "not-admin")
    owner = login["id"]
    banner("ADMIN: sesión local autenticada; no se mostraron credenciales.")
    agents = want_list(call(opener, "AGENTS-LIST", "GET", "/gateway/agents"), "AGENTS-LIST")
    existing = expected_agent(agents, owner)
    creds = verified_creds()
    if creds:
        if not existing or existing.get("id") != creds["agent_id"]:
            raise StageError("AGENT-RESTORE", "credential-agent-mismatch")
        banner("AGENT: credencial previamente guardada; se reutiliza.")
    else:
        key = key_id = None
        try:
            key, key_id = create_or_reveal_key(opener)
            res = register(opener, key, preexisting=bool(existing), owner=owner)
            if not isinstance(res, dict) or not res.get("id") or not res.get("api_key"):
                raise StageError("AGENT-REGISTER", "invalid-response")
            creds = {"base_url": BASE, "agent_id": res["id"], "api_key": res["api_key"],
                     "created_at_utc": clock()}
            safe_json(CREDS, creds)
            banner("AGENT: REGISTRADO y credencial privada guardada.")
        finally:
            if key_id:
                try:
                    call(opener, "KEYS-REVOKE", "DELETE", "/gateway/api-keys/" + quote(key_id, safe=""), timeout=30)
                except StageError:
                    banner("ADVERTENCIA: no se confirmó la revocación de la clave temporal.")
            key = None
    rooms = want_list(call(opener, "ROOMS-LIST", "GET", "/gateway/rooms"), "ROOMS-LIST")
    target = find_room(rooms)
    room_id = target["id"]
    detail = call(opener, "ROOM-DETAIL", "GET", "/gateway/rooms/" + quote(room_id, safe=""))
    if not isinstance(detail, dict):
        raise StageError("ROOM-DETAIL", "invalid-response")
    if creds["agent_id"] not in (detail.get("agent_ids") or []):
        try:
            call(opener, "ROOM-JOIN", "POST", "/gateway/rooms/" + quote(room_id, safe="") + "/agents",
                 {"agent_ids": [creds["agent_id"]]}, timeout=65)
        except StageError:
            detail = call(opener, "ROOM-RECHECK", "GET", "/gateway/rooms/" + quote(room_id, safe=""))
            if creds["agent_id"] not in (detail.get("agent_ids") or []):
                raise
    banner("ROOM: inneros-live-operations, agente incorporado.")
    try:
        msg = ("[InnerOS LiveOps] Agent installed on real local Switch Core at " + clock() +
               ". Safe bridge booting; try @inneros-incident-triage !ping. " +
               "No Home Assistant actions have been performed.")
        call(opener, "SWITCH-POST", "POST", "/agents/" + quote(creds["agent_id"], safe="") + "/message",
             {"room_id": room_id, "content": msg}, token=creds["api_key"], timeout=40)
        banner("MESSAGE: enviado a sala Switch; verificación visual en Mattermost pendiente.")
    except StageError as exc:
        banner("MESSAGE: no confirmada (" + exc.kind + "); el puente igual puede iniciar.")
    launch_bot(room_id, owner)
    banner("Esperando confirmación del WebSocket real (máximo 12 segundos)...")
    end = time.monotonic() + 12
    while time.monotonic() < end:
        try:
            st = json.loads(STATUS.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            st = {}
        if st.get("state") == "connected" and st.get("room") == room_id:
            banner("REAL SWITCH WEBSOCKET CONNECTED: " + str(st.get("at")))
            banner("LISTO: en Mattermost envía @inneros-incident-triage !ping")
            banner("LOG privado: " + str(LOG))
            return 0
        if st.get("state") == "blocked":
            banner("BRIDGE BLOCKED: " + str(st.get("error_code", "unknown")))
            break
        time.sleep(0.7)
    banner("WebSocket no confirmado todavía. Revisar el log privado sin secretos.")
    banner("LOG: " + str(LOG))
    return 3


async def serve_bot(room, approver):
    try:
        from websockets.asyncio.client import connect
    except ImportError:
        safe_json(STATUS, {"state": "blocked", "room": room, "error_code": "websockets-package-missing"})
        return 2
    creds = verified_creds()
    if not creds:
        return 2
    cursor = 0
    conn_id = str(uuid4())
    seen = set()
    backoff = 1
    while True:
        qp = urlencode({"connection_id": conn_id, "scope": "single", "filter": "all",
                        "start_from": str(cursor) if cursor else "head", "rooms": room})
        url = BASE.replace("http:", "ws:", 1) + "/agents/" + creds["agent_id"] + "/connection/ws?" + qp
        try:
            async with connect(url, additional_headers={"Authorization": "Bearer " + creds["api_key"]},
                               open_timeout=15, ping_interval=None) as sock:
                jobs = asyncio.Queue()
                async def worker():
                    nonlocal cursor
                    while True:
                        f = await jobs.get()
                        if f is None:
                            jobs.task_done()
                            return
                        try:
                            data = f.get("data") or {}
                            if not isinstance(data, dict):
                                data = {}
                            payload = data.get("payload") or {}
                            if not isinstance(payload, dict):
                                payload = {}
                            seq = f.get("id")
                            # No message bodies, tokens, or sender IDs are written to the log.
                            banner("RX-MESSAGE room_match=" + str(data.get("room_id") == room) +
                                   " addressed=" + str(payload.get("addressed")) +
                                   " fields=" + ",".join(sorted(str(k) for k in payload.keys()))[:150])
                            mid = payload.get("message_id")
                            text = payload.get("body")
                            if not isinstance(text, str):
                                text = payload.get("content")
                            if not isinstance(text, str):
                                text = data.get("body")
                            if not isinstance(text, str):
                                text = ""
                            # Switch may omit addressed=true for Mattermost bot mentions.
                            # Only explicitly typed SAFE diagnostic commands are accepted.
                            words = text.strip().lower().split()
                            words = [w for w in words if not w.startswith("@")]
                            cmd = words[0] if words else ""
                            if data.get("room_id") == room and cmd in {"!ping", "!status", "!help"}:
                                dedup = str(mid) if mid is not None else str(seq)
                                if dedup not in seen:
                                    seen.add(dedup)
                                    if cmd == "!ping":
                                        reply = "[INNEROS REAL SWITCH] PONG | Mattermost -> Switch WS -> local Python -> Switch HTTP | " + clock() + " | No physical actions."
                                    elif cmd == "!status":
                                        reply = "[INNEROS] Online, bridge local. Physical actions disabled."
                                    else:
                                        reply = "[INNEROS] Diagnostic commands: !ping, !status, !help. No physical actions."
                                    await asyncio.to_thread(call, client(), "AGENT-REPLY", "POST",
                                                            "/agents/" + creds["agent_id"] + "/message",
                                                            {"room_id": room, "content": reply}, token=creds["api_key"], timeout=25)
                                    banner("TX-REPLY cmd=" + cmd)
                                    safe_json(STATUS, {"state": "connected", "room": room, "at": clock(),
                                                       "last_reply": cmd})
                            elif data.get("room_id") == room:
                                banner("RX-SKIPPED reason=not-explicit-diagnostic-command")
                            if isinstance(seq, int) and seq > cursor:
                                cursor = seq
                        except StageError as exc:
                            banner("REPLY-ERROR: " + exc.kind)
                        except Exception as exc:
                            banner("BRIDGE-WORKER-ERROR: " + type(exc).__name__)
                        finally:
                            jobs.task_done()
                task = asyncio.create_task(worker())
                try:
                    async for raw in sock:
                        f = json.loads(raw)
                        kind = f.get("event") or f.get("type")
                        # Structural telemetry only: never dump raw frames or message text.
                        if isinstance(f, dict):
                            frame_data = f.get("data")
                            keys = sorted(str(k) for k in frame_data.keys()) if isinstance(frame_data, dict) else []
                            banner("RX-FRAME kind=" + str(kind)[:64] +
                                   " fields=" + ",".join(keys)[:160])
                        if kind == "ping":
                            await sock.send(json.dumps({"type": "pong", "cursor": cursor}))
                        elif kind == "connection_state":
                            d = f.get("data") or {}
                            if room not in (d.get("rooms") or []):
                                raise StageError("websocket", "room-not-covered")
                            safe_json(STATUS, {"state": "connected", "room": room, "at": clock()})
                            banner("REAL SWITCH WEBSOCKET CONNECTED room=" + room)
                            backoff = 1
                        elif kind == "message":
                            await jobs.put(f)
                        elif kind in {"refused", "evicted", "gap"}:
                            d = f.get("data") or {}
                            code = str(d.get("code") or kind)[:80]
                            raise StageError("websocket", code)
                        else:
                            # Show only event names and field names, never message text.
                            d = f.get("data") or {}
                            banner("RX-EVENT event=" + str(kind)[:60] +
                                   " data_fields=" + ",".join(sorted(str(k) for k in d))[:130]
                                   if isinstance(d, dict) else "RX-EVENT unexpected-data")
                finally:
                    await jobs.put(None)
                    await task
        except StageError as exc:
            safe_json(STATUS, {"state": "blocked", "room": room, "error_code": exc.kind, "at": clock()})
            banner("WS-STAGE-ERROR: " + exc.kind)
        except Exception as exc:
            safe_json(STATUS, {"state": "retrying", "room": room,
                                   "error_code": type(exc).__name__, "at": clock()})
            banner("WS-RETRY: " + type(exc).__name__)
        await asyncio.sleep(backoff)
        backoff = min(30, backoff * 2)


def read_ha_lights():
    """Optional real HA read. Never sends a service command."""
    url = os.getenv("HA_URL", "")
    token = os.getenv("HA_TOKEN", "")
    ids = frozenset(x.strip() for x in os.getenv("HA_ALLOWED_LIGHTS", "").split(",") if x.strip())
    if not (url and token and ids):
        return "[INNEROS HA] Not connected: provide HA_URL, HA_TOKEN, HA_ALLOWED_LIGHTS locally. No data fabricated."
    try:
        from inneros_incident_room.live_homeassistant import HomeAssistantClient
        states = HomeAssistantClient(url, token).lights(ids)
        return "[INNEROS HA LIVE READ] " + ("; ".join(f"{x['entity_id']}={x['state']}" for x in states) or "No allowlisted lights found")
    except Exception as exc:
        return "[INNEROS HA] Read failed: " + type(exc).__name__ + ". No observation claimed."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--room", default="")
    ap.add_argument("--approver", default="")
    args = ap.parse_args()
    try:
        if args.serve:
            return asyncio.run(serve_bot(args.room, args.approver))
        return setup()
    except StageError as exc:
        banner("BLOCKED etapa=" + exc.phase + ", motivo=" + exc.kind)
        banner("No se borraron salas, credenciales ni dispositivos.")
        return 2
    except KeyboardInterrupt:
        banner("Interrupted by operator")
        return 130
    except Exception as exc:
        banner("BLOCKED error=" + type(exc).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

