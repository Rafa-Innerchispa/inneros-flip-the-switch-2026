"""Offline security regression tests; generated fixtures are not deployed credentials."""
import http.client
import importlib.util
import os
from pathlib import Path
import secrets
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("liveops_auth_under_test", ROOT / "site/server.py")
web = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(web)


class OperatorAuthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.base = patch.object(web, "BASE_DIR", self.tmp.name)
        self.base.start()
        self.addCleanup(self.base.stop)
        self.token = secrets.token_urlsafe(32)  # SYNTHETIC fixture; never logged.

    def test_no_credential_fails_closed_even_with_headers(self):
        self.assertIsNone(web.get_operator_token())
        self.assertFalse(web.is_authorized_operator({"Authorization": "Bearer " + self.token}, {}))
        self.assertFalse(web.is_authorized_operator({"X-Operator-Token": self.token}, {}))
        self.assertFalse(web.is_authorized_operator({"Authorization": "Bearer "}, {}))

    def test_no_builtin_default_credential(self):
        self.assertFalse(hasattr(web, "DEFAULT_OPERATOR_TOKEN"))

    def test_existing_environment_credential_is_preserved(self):
        os.environ["LIVEOPS_OPERATOR_TOKEN"] = self.token
        self.assertEqual(web.get_operator_token(), self.token)
        self.assertTrue(web.is_authorized_operator({"Authorization": "Bearer " + self.token}, {}))
        self.assertTrue(web.is_authorized_operator({"X-Operator-Token": self.token}, {}))
        self.assertFalse(web.is_authorized_operator({"Authorization": "Bearer incorrect-fixture"}, {}))

    def test_correct_query_credential_never_authenticates(self):
        os.environ["LIVEOPS_OPERATOR_TOKEN"] = self.token
        self.assertFalse(web.is_authorized_operator({}, {"token": [self.token]}))

    @unittest.skipUnless(os.name == "posix", "POSIX ownership/mode semantics")
    def test_private_file_credential(self):
        p = Path(self.tmp.name) / ".operator_token"
        p.write_text(self.token)
        p.chmod(0o600)
        self.assertEqual(web.get_operator_token(), self.token)

    @unittest.skipUnless(os.name == "posix", "POSIX ownership/mode semantics")
    def test_group_readable_file_fails_closed(self):
        p = Path(self.tmp.name) / ".operator_token"
        p.write_text(self.token)
        p.chmod(0o640)
        self.assertIsNone(web.get_operator_token())

    @unittest.skipUnless(os.name == "posix", "POSIX no-follow semantics")
    def test_symlink_file_fails_closed(self):
        p = Path(self.tmp.name) / "private-source"
        p.write_text(self.token)
        p.chmod(0o600)
        (Path(self.tmp.name) / ".operator_token").symlink_to(p)
        self.assertIsNone(web.get_operator_token())

    def test_public_page_and_anonymous_inference_auth_over_http(self):
        os.environ["LIVEOPS_OPERATOR_TOKEN"] = self.token

        class QuietHandler(web.SecureLiveOpsHandler):
            def log_message(self, *_):
                pass  # Never log query credential fixtures.

        srv = web.ServerClass(("127.0.0.1", 0), QuietHandler)
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.object(web, "run_real_qwen_inference") as inference:
                for method in ("GET", "POST", "HEAD"):
                    for suffix in ("", "?token=invalid-fixture", "?token=" + self.token):
                        conn = http.client.HTTPConnection(*srv.server_address, timeout=3)
                        conn.request(method, "/api/liveops/test_ai" + suffix, body="" if method == "POST" else None)
                        response = conn.getresponse()
                        response.read()
                        self.assertEqual(response.status, 401)
                        conn.close()
                inference.assert_not_called()
            with patch.object(web, "BASE_DIR", str(ROOT / "site")):
                conn = http.client.HTTPConnection(*srv.server_address, timeout=3)
                conn.request("GET", "/")
                response = conn.getresponse()
                body = response.read()
                self.assertEqual(response.status, 200)
                self.assertIn(b"InnerOS LiveOps", body)
                conn.close()
        finally:
            srv.shutdown()
            srv.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
