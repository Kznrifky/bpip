"""Smoke test the real Gunicorn process with Render-like runtime variables."""
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]

@unittest.skipUnless(importlib.util.find_spec('gunicorn'), 'Install requirements.txt to test Gunicorn startup')
class RenderRuntimeTests(unittest.TestCase):
    def test_first_start_creates_accounts_with_render_url_and_secure_cookie(self):
        with tempfile.TemporaryDirectory() as folder:
            with socket.socket() as listener:
                listener.bind(('127.0.0.1', 0))
                port = listener.getsockname()[1]
            values = {
                'APP_ENV':'production', 'HOST':'127.0.0.1', 'PORT':str(port),
                'DATABASE_PATH':str(Path(folder)/'runtime.sqlite3'),
                'PUBLIC_BASE_URL':'', 'RENDER_EXTERNAL_URL':'https://bpip-test.onrender.com',
                'MAIL_MODE':'smtp', 'SMTP_HOST':'smtp.example.com', 'SMTP_FROM':'test@example.com',
                'SMTP_USER':'', 'SMTP_PASSWORD':'', 'SMTP_TLS':'starttls',
                'GUNICORN_CMD_ARGS':'', 'BOOTSTRAP_USERS':'1',
                'BOOTSTRAP_PETUGAS_EMAIL':'maker@example.com', 'BOOTSTRAP_PETUGAS_NAME':'Maker Test',
                'BOOTSTRAP_PETUGAS_PASSWORD':'RuntimeMaker!2026',
                'BOOTSTRAP_SOL_EMAIL':'checker@example.com', 'BOOTSTRAP_SOL_NAME':'Checker Test',
                'BOOTSTRAP_SOL_PASSWORD':'RuntimeChecker!2026',
            }
            with open(Path(folder)/'gunicorn.log','wb') as log:
                process = subprocess.Popen([sys.executable,'-m','gunicorn','--config','gunicorn.conf.py','wsgi:application'],cwd=ROOT,env={**os.environ,**values},stdout=log,stderr=log)
                try:
                    url = f'http://127.0.0.1:{port}/api/config'
                    deadline = time.monotonic()+15
                    while True:
                        self.assertIsNone(process.poll(), 'Gunicorn exited before health check passed')
                        try:
                            with urlopen(url, timeout=1) as response:
                                self.assertEqual(json.load(response)['mail_mode'],'smtp')
                            break
                        except (URLError, TimeoutError):
                            if time.monotonic()>deadline:
                                self.fail('Gunicorn did not become healthy')
                            time.sleep(.1)
                    body=json.dumps({'email':'maker@example.com','password':'RuntimeMaker!2026'}).encode()
                    request=Request(f'http://127.0.0.1:{port}/api/login',data=body,headers={'Content-Type':'application/json','Origin':'https://bpip-test.onrender.com'})
                    with urlopen(request,timeout=3) as response:
                        self.assertEqual(json.load(response)['user']['role'],'petugas')
                        self.assertIn('Secure',response.headers['Set-Cookie'])
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill();process.wait(timeout=5)

if __name__=='__main__':
    unittest.main(verbosity=2)
