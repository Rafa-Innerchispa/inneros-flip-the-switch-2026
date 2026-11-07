from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import register_agent_local_admin as reg

class MockGateway(BaseHTTPRequestHandler):
    calls=[]
    def log_message(self, *_args):
        pass
    def send(self, code, data, cookie=False):
        b=json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(b)))
        if cookie:self.send_header('Set-Cookie','switch_auth=fake-session; Path=/; HttpOnly')
        self.end_headers()
        self.wfile.write(b)
    def do_GET(self):
        self.calls.append(('GET',self.path))
        self.send(200,{'status':'ok'})
    def do_POST(self):
        n=int(self.headers.get('Content-Length','0'))
        data=json.loads(self.rfile.read(n) or b'{}')
        self.calls.append(('POST',self.path))
        if self.path=='/gateway/auth/login':
            self.send(200,{'role':'admin'}, cookie=True)
        elif self.path=='/gateway/api-keys':
            assert 'switch_auth=' in self.headers.get('Cookie','')
            self.send(201,{'id':'key-1','key':'personal-registration-secret-123456789'})
        elif self.path=='/agents':
            assert self.headers.get('Authorization')=='Bearer personal-registration-secret-123456789'
            self.send(201,{'id':'agent-1','api_key':'agent-specific-secret-123456789'})
        else:self.send(404,{'detail':'unknown'})
    def do_DELETE(self):
        self.calls.append(('DELETE',self.path))
        self.send(200,{'ok':True})

class TestLocalAdminRegistration(unittest.TestCase):
    def setUp(self):
        MockGateway.calls=[]
        self.server=ThreadingHTTPServer(('127.0.0.1',0),MockGateway)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.temp=tempfile.TemporaryDirectory()
        self.dir=Path(self.temp.name)
        self.envfile=self.dir/'switch-core.env'
        self.envfile.write_text('GATEWAY_ADMIN_EMAIL=admin@switch.local\nGATEWAY_ADMIN_PASSWORD=local-only-secret\nSERVER_PORT='+str(self.server.server_port)+'\n')
        self.target=self.dir/'credentials.json'
    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(1)
        self.temp.cleanup()
    def test_register_and_revoke_temporary_key(self):
        result=reg.enroll('http://127.0.0.1:'+str(self.server.server_port),self.target,self.envfile)
        self.assertTrue(result['registered'])
        self.assertTrue(self.target.exists())
        self.assertEqual([c for c in MockGateway.calls if c[0]=='DELETE'],[('DELETE','/gateway/api-keys/key-1')])
        self.assertNotIn('local-only-secret',self.target.read_text())
        self.assertNotIn('personal-registration-secret',self.target.read_text())
        self.assertIn('agent-specific-secret',self.target.read_text())
    def test_existing_credentials_do_not_trigger_http_or_create_key(self):
        self.target.write_text('{"ok":true}')
        result=reg.enroll('http://127.0.0.1:'+str(self.server.server_port),self.target,self.envfile)
        self.assertTrue(result['already_registered'])
        self.assertEqual(MockGateway.calls,[])

if __name__=='__main__':
    unittest.main()
