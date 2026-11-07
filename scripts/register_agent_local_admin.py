#!/usr/bin/env python3
"""Safely register a Switch agent under the local admin, without exposing keys.

Switch Console v0.40.1 has no API Keys settings screen. Its native core keeps
GATEWAY_ADMIN_EMAIL/PASSWORD inside a private runtime env file. On 127.0.0.1:
- Login as existing local admin (never log or save the password).
- Create a short-lived-by-lifecycle personal registration key via Gateway API.
- Register exactly one InnerOS agent using POST /agents.
- Immediately revoke the temporary registration key, even on failure.
Never modify Switch runtime files, networks, or physical devices.
"""
from __future__ import annotations

import argparse
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener

from register_agent import DEFAULT_CREDENTIAL_FILE, register

AGENT_NAME = "inneros-incident-triage"


def validate_url(url: str) -> str:
    v = urlsplit(url)
    if (v.scheme != "http" or v.hostname not in {"localhost", "127.0.0.1"}
            or v.username or v.password or v.query or v.fragment
            or v.path not in {"", "/"} or not v.port):
        raise ValueError("Only a local HTTP Switch server with explicit port is allowed")
    return url.rstrip("/")


def read_local_core_config(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError("Switch native runtime env file not found")
    needed = {"GATEWAY_ADMIN_EMAIL", "GATEWAY_ADMIN_PASSWORD", "SERVER_PORT"}
    result: dict[str, str] = {}
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            key, sep, value = line.rstrip("\n\r").partition("=")
            if sep and key in needed:
                result[key] = value
    for key in ("GATEWAY_ADMIN_EMAIL", "GATEWAY_ADMIN_PASSWORD"):
        if not result.get(key):
            raise ValueError("Switch local admin credentials absent from native runtime")
    return result


def request(opener, base: str, method: str, path: str, data: dict | None = None) -> dict:
    body = json.dumps(data).encode("utf-8") if data is not None else None
    with opener.open(Request(base + path, data=body, method=method,
                             headers={"Content-Type": "application/json"}),
                     timeout=8) as resp:
        if resp.status < 200 or resp.status >= 300:
            raise RuntimeError("Unexpected local server response status")
        if method == "DELETE":
            return {}
        value = json.load(resp)
        if not isinstance(value, dict):
            raise ValueError("Switch returned unexpected JSON")
        return value


def enroll(base: str, credentials: Path, core_config_path: Path) -> dict:
    base = validate_url(base)
    if credentials.exists():
        return {"already_registered": True, "credentials_file": str(credentials)}
    cfg = read_local_core_config(core_config_path)
    port = urlsplit(base).port
    if cfg.get("SERVER_PORT") and str(port) != cfg["SERVER_PORT"]:
        raise ValueError("Switch runtime port differs from the selected server port")
    # Never send a native admin password to another host or through a proxy.
    opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()))
    check = request(opener, base, "GET", "/health")
    if check.get("status") != "ok":
        raise RuntimeError("Switch /health is not OK")
    signed = request(opener, base, "POST", "/gateway/auth/login", {
        "email": cfg["GATEWAY_ADMIN_EMAIL"],
        "password": cfg["GATEWAY_ADMIN_PASSWORD"],
    })
    if signed.get("role") != "admin":
        raise RuntimeError("Gateway login did not establish the admin account")
    created_id = ""
    cleanup_error = False
    try:
        data = request(opener, base, "POST", "/gateway/api-keys", {
            "label": "InnerOS LiveOps temporary local registration"
        })
        created_id = data.get("id", "")
        secret = data.get("key", "")
        if not isinstance(created_id, str) or not created_id or not isinstance(secret, str) or len(secret) < 20:
            raise RuntimeError("Gateway did not provide a valid temporary registration key")
        return register(base, secret, AGENT_NAME, credentials)
    finally:
        if created_id:
            try:
                # Revoke the registration key; the agent has its separate key.
                request(opener, base, "DELETE", "/gateway/api-keys/" + created_id)
            except (HTTPError, URLError, OSError, ValueError):
                cleanup_error = True
        if cleanup_error:
            print("WARNING: temporary key cleanup not confirmed. Revoke it from the Gateway later.", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Switch Console v0.40.1 local admin registration")
    parser.add_argument("--url", default="http://127.0.0.1:62226")
    parser.add_argument("--credentials", type=Path, default=DEFAULT_CREDENTIAL_FILE)
    parser.add_argument("--core-env", type=Path,
                        default=Path(os.environ.get("APPDATA", "")) / "switchdash" /
                        "local-switch-server" / "native" / "run" / "switch-core.env")
    args = parser.parse_args()
    try:
        result = enroll(args.url, args.credentials.expanduser(), args.core_env.expanduser())
        # Metadata only. Registration and admin secrets are never printed.
        print(json.dumps(result, indent=2))
        return 0
    except HTTPError as e:
        print("BLOCKED: Switch rejected admin authentication or registration (HTTP " + str(e.code) + ").", file=sys.stderr)
    except (URLError, OSError, ValueError, RuntimeError) as e:
        print("BLOCKED: " + type(e).__name__ + ". No credentials were disclosed.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
