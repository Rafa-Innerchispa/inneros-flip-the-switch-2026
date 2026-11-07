from pathlib import Path

web_path = Path("/home/rlopez/inneros/inneros-meta-guardian-2026/src/inneros_meta_guardian/web.py")
content = web_path.read_text(encoding="utf-8")

target = '        elif path == "/api/health":'
replacement = '''        elif path == "/api/liveops/status":
            status_file = Path.home() / ".config" / "inneros-switch" / "liveops-status.json"
            results_file = Path("/home/rlopez/inneros/modules/switch-liveops/data/e2e_results.json")
            data = {
                "state": "unknown",
                "node": "AMD-1.5",
                "switch_core_url": "http://127.0.0.1:62326",
                "mattermost_url": "http://127.0.0.1:62327",
                "gateway_url": "http://127.0.0.1:62325"
            }
            if status_file.is_file():
                try:
                    data.update(json.loads(status_file.read_text(encoding="utf-8")))
                except Exception:
                    pass
            if results_file.is_file():
                try:
                    data["e2e_results"] = json.loads(results_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
            self._json(200, data)
        elif path == "/api/health":'''

if target in content and "/api/liveops/status" not in content:
    new_content = content.replace(target, replacement, 1)
    web_path.write_text(new_content, encoding="utf-8")
    print("Patched web.py successfully with /api/liveops/status!")
else:
    print("Already patched or target not found.")
