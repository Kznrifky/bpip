import base64
import io
import json
import tempfile
import unittest
from pathlib import Path
import server
from wsgi import application

class WSGITransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original = server.DB_PATH, server.PRODUCTION, server.MAIL_MODE
        server.DB_PATH = Path(self.temp.name) / 'wsgi.sqlite3'
        server.PRODUCTION = False
        server.MAIL_MODE = 'console'
        server.initialize()
        server.seed_demo()
    def tearDown(self):
        server.DB_PATH, server.PRODUCTION, server.MAIL_MODE = self.original
        self.temp.cleanup()
    def request(self, path, data=None, cookie='', csrf='', method=None):
        body = json.dumps(data).encode() if data is not None else b''
        environ = {'REQUEST_METHOD': method or ('POST' if data is not None else 'GET'),
                   'PATH_INFO': path, 'REMOTE_ADDR': '127.0.0.1', 'wsgi.input': io.BytesIO(body),
                   'CONTENT_TYPE': 'application/json', 'CONTENT_LENGTH': str(len(body)),
                   'HTTP_COOKIE': cookie, 'HTTP_X_CSRF_TOKEN': csrf}
        result = {}
        def start(status, headers):
            result['status'] = int(status.split()[0]);result['headers'] = dict(headers)
        result['body'] = b''.join(application(environ, start))
        return result
    def test_wsgi_login_document_portal_and_csrf(self):
        response = self.request('/api/login', {'email': 'petugas@bpip.local', 'password': 'PetugasDemo!2026'})
        self.assertEqual(response['status'], 200)
        csrf = json.loads(response['body'])['csrf']
        cookie = response['headers']['Set-Cookie'].split(';')[0]
        self.assertEqual(self.request('/api/session', cookie=cookie)['status'], 200)
        payload = {'cif':'1234567','kind':'Warkat','nominal':10000,'file':{'name':'surat.pdf','base64':base64.b64encode(b'%PDF-1.4\n%%EOF').decode()}}
        self.assertEqual(self.request('/api/documents',payload,cookie)['status'],403)
        response = self.request('/api/documents',payload,cookie,csrf)
        self.assertEqual(response['status'],201)
        doc_id=json.loads(response['body'])['id']
        with server.database() as db:
            token=db.execute('SELECT body FROM outbox WHERE doc_id=?',(doc_id,)).fetchone()['body'].split('/#confirm/')[1].split()[0]
        self.assertEqual(self.request('/api/portal',{'token':token})['status'],200)
        response=self.request('/api/portal/decision',{'token':token,'decision':'confirmed','acknowledged':True})
        self.assertEqual(response['status'],200)
        response=self.request('/api/documents/'+doc_id+'/file',cookie=cookie)
        self.assertEqual(response['status'],200)
        self.assertTrue(response['body'].startswith(b'%PDF-'))
        self.assertEqual(response['headers']['Content-Type'],'application/pdf')
    def test_static_head_method_and_unauthenticated_access(self):
        response=self.request('/',method='HEAD')
        self.assertEqual(response['status'],200)
        self.assertEqual(response['body'],b'')
        self.assertGreater(int(response['headers']['Content-Length']),0)
        self.assertEqual(self.request('/api/documents')['status'],401)
        self.assertEqual(self.request('/api/config',method='PUT')['status'],405)
        self.assertEqual(self.request('/../../.env')['status'],404)

if __name__ == '__main__':
    unittest.main(verbosity=2)
