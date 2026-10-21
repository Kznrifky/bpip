"""Integration checks against an actual HTTP server and temporary SQLite DB."""
import base64
from io import BytesIO
from email.parser import BytesParser
import concurrent.futures
import http.cookiejar
import importlib.util
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.parse import urlsplit, parse_qs
from unittest.mock import patch
from pypdf import PdfReader
from reportlab.pdfgen import canvas
from PIL import Image
from confirmation_email import expiry_label

spec = importlib.util.spec_from_file_location('bpip', Path(__file__).resolve().parents[1] / 'server.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)
DESTINATION = {'destination_bank': 'BRI', 'destination_account': '000123456789012', 'destination_name': 'PT Tujuan Pembayaran'}
FILE = {'name': 'surat.pdf', 'base64': base64.b64encode(b'%PDF-1.4\nSample integration fixture\n%%EOF').decode()}

class Client:
    def __init__(self, url):
        self.url=url
        self.opener=build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.csrf=''
    def call(self, path, data=None, csrf=True, origin=None):
        headers = {}
        if data is not None:
            headers['Content-Type']='application/json'
            headers['X-CSRF-Token']=self.csrf if csrf else 'invalid'
        if origin:
            headers['Origin']=origin
        request=Request(self.url+'/api'+path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
        try:
            res=self.opener.open(request)
        except HTTPError as e:
            res=e
        body=res.read()
        value=json.loads(body) if 'application/json' in res.headers.get('Content-Type','') else body
        return res.status,value,res.headers
    def login(self, role):
        status,data,headers=self.call('/login',{'email':role+'@bpip.local','password':'PetugasDemo!2026' if role=='petugas' else 'SolDemo!2026'})
        assert status==200,data
        self.csrf=data['csrf']
        return headers

class LegacyDocumentClient(Client):
    """Keep the existing regression suite on historical pre-checker records.

    New checker-flow tests use the plain Client and assert the new default.
    """
    def call(self, path, data=None, **options):
        result=super().call(path,data,**options)
        if path=='/documents' and data is not None and result[0]==201:
            with app.database(True) as db:
                db.execute('UPDATE documents SET review_flow=1 WHERE id=?',(result[1]['id'],))
        return result

class WorkflowTests(unittest.TestCase):
    def boh_client(self, email='boh.approval@example.test'):
        app.create_user(email, 'BOH Approval', 'boh', 'BohApproval!2026')
        client = Client(self.url)
        result = client.call('/login', {'email': email, 'password': 'BohApproval!2026'})[1]
        client.csrf = result['csrf']
        return client

    def customer_edit(self, cif='1234567', **changes):
        customer = next(row for row in self.sol.call('/customers')[1]['customers'] if row['cif'] == cif)
        return {**customer, 'account': '000123456789012', 'phone': '081234567890', 'reason': 'Pembaruan data nasabah', **changes}

    def test_customer_edit_approval_updates_master_only(self):
        reviewer = self.sol
        existing_doc = self.create()
        payload = self.customer_edit(name='PT Nama Baru', email='baru@example.test', person='Direktur Baru')
        status, result, _ = self.checker.call('/customers/1234567/edit-requests', payload)
        self.assertEqual(status, 201, result)
        request_id = result['id']
        self.assertEqual(self.maker.call('/customers')[1]['customers'][0]['revision'], 0)
        self.assertEqual(self.maker.call('/documents/' + existing_doc)[1]['document']['customer_name'], 'PT Maju Bersama')
        before = next(c for c in self.maker.call('/customers')[1]['customers'] if c['cif'] == '1234567')
        self.assertEqual(before['email'], 'budi@example.com')
        app.initialize()  # Pending requests survive startup.
        request = reviewer.call('/customer-edit-requests')[1]['requests'][0]
        self.assertEqual(request['new_data']['email'], payload['email'])
        self.assertEqual(request['old_data']['email'], before['email'])
        self.assertEqual(request['status'], 'pending')
        route = '/customer-edit-requests/' + request_id + '/review'
        self.assertEqual(reviewer.call(route, {'decision': 'approved', 'notes': 'Data sesuai'})[0], 200)
        after = next(c for c in self.maker.call('/customers')[1]['customers'] if c['cif'] == '1234567')
        for key in app.CUSTOMER_FIELDS:
            self.assertEqual(after[key], payload[key])
        self.assertEqual(after['revision'], 1)
        old = self.maker.call('/documents/' + existing_doc)[1]['document']
        self.assertEqual(old['email'], before['email'])
        self.assertEqual(old['customer_name'], before['name'])
        new_doc = self.create()
        self.assertEqual(self.maker.call('/documents/' + new_doc)[1]['document']['email'], payload['email'])
        reviewed = self.sol.call('/customer-edit-requests')[1]['requests'][0]
        self.assertEqual(reviewed['status'], 'approved')
        self.assertEqual(reviewed['review_notes'], 'Data sesuai')
        self.assertTrue(reviewed['reviewed_at'])
        with app.database() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM management_audit WHERE action LIKE 'AMOL menyetujui pembaruan:%'").fetchone()[0], 1)

    def test_customer_edit_rejection_permissions_and_csrf(self):
        reviewer = self.sol
        boh = self.boh_client()
        payload = self.customer_edit()
        endpoint = '/customers/1234567/edit-requests'
        self.assertEqual(self.maker.call(endpoint, payload)[0], 403)
        self.assertEqual(self.sol.call(endpoint, payload)[0], 403)
        self.assertEqual(boh.call(endpoint, payload)[0], 403)
        self.assertEqual(self.checker.call(endpoint, payload, csrf=False)[0], 403)
        self.assertEqual(self.maker.call('/customer-edit-requests')[0], 403)
        self.assertEqual(self.customer.call('/customer-edit-requests')[0], 401)
        request_id = self.checker.call(endpoint, payload)[1]['id']
        route = '/customer-edit-requests/' + request_id + '/review'
        decision = {'decision': 'approved'}
        for client in (self.checker, self.maker, boh):
            self.assertEqual(client.call(route, decision)[0], 403)
        self.assertEqual(reviewer.call(route, decision, csrf=False)[0], 403)
        self.assertEqual(reviewer.call(route, {'decision': 'invalid'})[0], 400)
        self.assertEqual(reviewer.call(route, {'decision': 'rejected', 'notes': ' '})[0], 400)
        self.assertEqual(reviewer.call(route, {'decision': 'rejected', 'notes': 'Email belum terverifikasi'})[0], 200)
        self.assertEqual(reviewer.call(route, decision)[0], 409)
        customer = next(c for c in self.sol.call('/customers')[1]['customers'] if c['cif'] == '1234567')
        self.assertEqual(customer['revision'], 0)
        self.assertEqual(customer['account'], '001234567890')
        self.assertEqual(self.sol.call('/customer-edit-requests')[1]['requests'][0]['review_notes'], 'Email belum terverifikasi')

    def test_customer_edit_validation_duplicate_and_stale_data(self):
        reviewer = self.sol
        payload = self.customer_edit()
        endpoint = '/customers/1234567/edit-requests'
        for key, invalid in [('name', ''), ('person', ''), ('email', 'invalid'), ('account', '123'), ('phone', 'abc'), ('reason', ''), ('cif', '999')]:
            with self.subTest(key=key):
                self.assertEqual(self.checker.call(endpoint, {**payload, key: invalid})[0], 400)
        self.assertEqual(self.checker.call(endpoint, {**payload, 'revision': 1})[0], 409)
        request_id = self.checker.call(endpoint, payload)[1]['id']
        self.assertEqual(self.checker.call(endpoint, payload)[0], 409)
        route = '/customer-edit-requests/' + request_id + '/review'
        with app.database(True) as db:
            db.execute("UPDATE customers SET email='external@example.test' WHERE cif='1234567'")
        self.assertEqual(reviewer.call(route, {'decision': 'approved'})[0], 409)
        self.assertEqual(reviewer.call(route, {'decision': 'rejected', 'notes': 'Data sudah berubah'})[0], 200)
        payload = self.customer_edit(email='baru@example.test')
        next_id = self.checker.call(endpoint, payload)[1]['id']
        self.assertEqual(reviewer.call('/customer-edit-requests/' + next_id + '/review', {'decision': 'approved'})[0], 200)
        self.assertEqual(self.checker.call(endpoint, payload)[0], 409)
        self.assertEqual(self.checker.call(endpoint, self.customer_edit(email='baru@example.test'))[0], 400)  # No changed fields.

    def test_customer_edit_concurrent_decisions_are_atomic(self):
        first = self.sol
        second = Client(self.url); second.login('sol')
        request_id = self.checker.call('/customers/1234567/edit-requests', self.customer_edit())[1]['id']
        route = '/customer-edit-requests/' + request_id + '/review'
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda client: client.call(route, {'decision': 'approved'})[0], (first, second)))
        self.assertEqual(sorted(results), [200, 409])
        with app.database() as db:
            self.assertEqual(db.execute("SELECT revision FROM customers WHERE cif='1234567'").fetchone()[0], 1)

    def test_legacy_customer_request_cannot_be_reviewed_by_its_own_requester(self):
        request_id = self.checker.call('/customers/1234567/edit-requests', self.customer_edit())[1]['id']
        with app.database(True) as db:
            amol_id = db.execute("SELECT id FROM users WHERE email='sol@bpip.local'").fetchone()[0]
            db.execute('UPDATE customer_edit_requests SET requested_by=? WHERE id=?', (amol_id, request_id))
        app.initialize()
        route = '/customer-edit-requests/' + request_id + '/review'
        for decision in ('approved', 'rejected'):
            self.assertEqual(self.sol.call(route, {'decision': decision, 'notes': 'Own request'})[0], 403)
        self.assertEqual(self.sol.call('/customer-edit-requests')[1]['requests'][0]['status'], 'pending')
        other = Client(self.url)
        session = other.call('/login', {'email': 'amol@example.test', 'password': 'AmolDemo!2026'})[1]
        other.csrf = session['csrf']
        self.assertEqual(other.call(route, {'decision': 'approved'})[0], 200)

    def test_customer_edit_role_boundaries_and_requester_identity(self):
        payload = self.customer_edit()
        self.assertEqual(self.sol.call('/customers/1234567/phone', {'phone': '081234567891'})[0], 403)
        self.assertEqual(self.checker.call('/customers', payload)[0], 403)
        self.assertEqual(self.checker.call('/customers/delete-selected', {'cifs': ['1234567']})[0], 403)
        request_id = self.checker.call('/customers/1234567/edit-requests', payload)[1]['id']
        request = self.checker.call('/customer-edit-requests')[1]['requests'][0]
        checker_id = self.checker.call('/session')[1]['user']['id']
        self.assertEqual(request['id'], request_id)
        self.assertEqual(request['requested_by'], checker_id)
        self.assertEqual(request['status'], 'pending')
        self.assertEqual(self.checker.call('/customer-edit-requests/' + request_id + '/review', {'decision': 'approved'})[0], 403)

    def test_customer_delete_cancels_pending_edits(self):
        reviewer = self.sol
        request_id = self.checker.call('/customers/1234567/edit-requests', self.customer_edit())[1]['id']
        self.assertEqual(self.sol.call('/customers/delete-selected', {'cifs': ['1234567'], 'password': 'SolDemo!2026'})[0], 200)
        self.assertEqual(reviewer.call('/customer-edit-requests/' + request_id + '/review', {'decision': 'approved'})[0], 409)
        request = reviewer.call('/customer-edit-requests')[1]['requests'][0]
        self.assertEqual(request['status'], 'cancelled')
        self.assertEqual(request['old_data']['name'], 'PT Maju Bersama')

    def test_destination_required_and_preserved_in_confirmation(self):
        payload = {'cif': '1234567', 'kind': 'Warkat', 'nominal': 100, 'file': FILE, **DESTINATION}
        for field in DESTINATION:
            for invalid in (None, '', '   ', 123):
                with self.subTest(field=field, value=invalid):
                    self.assertEqual(self.maker.call('/documents', {**payload, field: invalid})[0], 400)
            missing = {key: value for key, value in payload.items() if key != field}
            self.assertEqual(self.maker.call('/documents', missing)[0], 400)
        for invalid in ('123abc', '1' * 14, '1' * 16, '1' * 31):
            self.assertEqual(self.maker.call('/documents', {**payload, 'destination_account': invalid})[0], 400)
        self.assertEqual(self.maker.call('/documents', {**payload, 'destination_name': 'a' * 251})[0], 400)
        doc = self.maker.call('/documents', {**payload, 'destination_name': ' PT Tujuan Pembayaran '})[1]['id']
        detail = self.maker.call('/documents/' + doc)[1]['document']
        portal = self.customer.call('/portal', {'token': self.token(doc)})[1]['document']
        for field, expected in DESTINATION.items():
            self.assertEqual(detail[field], expected)
            self.assertEqual(portal[field], expected)
            self.assertEqual(detail['versions'][0][field], expected)
        with app.database() as db:
            body = db.execute('SELECT body FROM outbox WHERE doc_id=?', (doc,)).fetchone()['body']
        self.assertIn(DESTINATION['destination_account'], body)
        self.assertIn(DESTINATION['destination_name'], body)
        self.assertIn('Bank Rekening Tujuan: BRI', body)

    def test_destination_account_lengths_follow_selected_bank(self):
        payload = {'cif': '1234567', 'kind': 'Warkat', 'nominal': 100, 'file': FILE, **DESTINATION}
        configured = self.maker.call('/config')[1]['destination_banks']
        self.assertEqual({bank['value'] for bank in configured}, {'BRI', 'BCA', 'BNI', 'Mandiri', 'BSI', 'CIMB Niaga', 'BTN', 'Danamon', 'OCBC'})
        for bank in configured:
            for length in bank['lengths']:
                account = '0' + '1' * (length - 1)
                with self.subTest(bank=bank['value'], length=length):
                    status, result, _ = self.maker.call('/documents', {**payload, 'destination_bank': bank['value'], 'destination_account': account})
                    self.assertEqual(status, 201, result)
                    detail = self.maker.call('/documents/' + result['id'])[1]['document']
                    self.assertEqual(detail['destination_bank'], bank['value'])
                    self.assertEqual(detail['destination_account'], account)
                    self.assertEqual(detail['versions'][0]['destination_bank'], bank['value'])
            for invalid in ('1' * (min(bank['lengths']) - 1), '1' * (max(bank['lengths']) + 1), '1a' * 5, '１２３４５６７８９０'):
                self.assertEqual(self.maker.call('/documents', {**payload, 'destination_bank': bank['value'], 'destination_account': invalid})[0], 400)
        for invalid in ('Bank Palsu', '<script>', [], {}):
            self.assertEqual(self.maker.call('/documents', {**payload, 'destination_bank': invalid})[0], 400)
        for invalid in ('PT Tujuan 123', 'PT. Tujuan', 'Tujuan-Penerima', 'Éka', '   '):
            self.assertEqual(self.maker.call('/documents', {**payload, 'destination_name': invalid})[0], 400)

    def test_execution_download_busy_request_does_not_release_active_lock(self):
        doc = self.create(); self.respond(self.token(doc))
        self.assertEqual(self.sol.call('/documents/'+doc+'/review', {'version':1,'decision':'approved'})[0], 200)
        app.EXECUTION_PDF_LOCK.acquire()
        try:
            status, result, _ = self.maker.call('/documents/'+doc+'/execution-pdf')
            self.assertEqual(status, 503)
            self.assertIn('sedang diproses', result['error'])
            self.assertTrue(app.EXECUTION_PDF_LOCK.locked())
        finally:
            app.EXECUTION_PDF_LOCK.release()

    def test_disabled_revision_preserves_destination_snapshot(self):
        doc = self.create()
        self.respond(self.token(doc))
        before = self.maker.call('/documents/' + doc)[1]['document']
        self.assertEqual(self.sol.call('/documents/' + doc + '/review', {'version': 1, 'decision': 'revision_requested', 'notes': 'Perbaiki rekening tujuan'})[0], 400)
        payload = {'version': 1, 'kind': 'Standing Instruction', 'nominal': 250000000, 'notes': 'Ubah rekening', 'file': FILE, 'destination_account': '009876543210000', 'destination_name': 'PT Baru'}
        self.assertEqual(self.maker.call('/documents/' + doc + '/revise', payload)[0], 410)
        detail = self.maker.call('/documents/' + doc)[1]['document']
        self.assertEqual(detail['version'], 1)
        self.assertEqual(detail['updated'], before['updated'])
        self.assertEqual(detail['audit'], before['audit'])
        for field in DESTINATION:
            self.assertEqual(detail[field], DESTINATION[field])
            self.assertEqual(detail['versions'][0][field], DESTINATION[field])

    def test_destination_migration_preserves_legacy_records(self):
        doc = self.create()
        with app.database(True) as db:
            for table in ('documents', 'versions'):
                for column in DESTINATION:
                    db.execute(f'ALTER TABLE {table} DROP COLUMN {column}')
        app.initialize()
        app.initialize()  # Repeated startup must be safe.
        detail = self.maker.call('/documents/' + doc)[1]['document']
        self.assertEqual(detail['customer_name'], 'PT Maju Bersama')
        self.assertEqual(detail['nominal'], 250000000)
        for field in DESTINATION:
            self.assertEqual(detail[field], '')
            self.assertEqual(detail['versions'][0][field], '')
        self.assertEqual(self.customer.call('/portal', {'token': self.token(doc)})[0], 200)

    def test_execution_pdf_approval_access_and_original_appendix(self):
        original=BytesIO()
        sheet=canvas.Canvas(original)
        sheet.drawString(50,750,'ORIGINAL SI TEST DOCUMENT')
        sheet.showPage();sheet.save()
        upload={'name':'si-original.pdf','base64':base64.b64encode(original.getvalue()).decode()}
        payload={**DESTINATION,'cif':'1234567','kind':'Standing Instruction','nominal':250000000,'description':'Pembayaran vendor','file':upload}
        status,result,_=self.maker.call('/documents',payload)
        self.assertEqual(status,201)
        doc=result['id'];route='/documents/'+doc+'/execution-pdf'
        self.assertEqual(self.maker.call(route)[0],409)
        self.assertEqual(Client(self.url).call(route)[0],401)
        self.respond(self.token(doc))
        self.assertEqual(self.sol.call(route)[0],409)
        self.assertEqual(self.sol.call('/documents/'+doc+'/review',{'version':1,'decision':'approved','notes':'Surat telah diperiksa.'})[0],200)
        status,body,headers=self.maker.call(route)
        self.assertEqual(status,200)
        self.assertEqual(headers['Content-Type'],'application/pdf')
        reader=PdfReader(BytesIO(body))
        self.assertEqual(len(reader.pages),3)  # Two report pages plus the original, no blank cover.
        text='\n'.join(page.extract_text() for page in reader.pages)
        for expected in ['SURAT KONFIRMASI PELAKSANAAN','RIWAYAT PERNYATAAN','LOG AKTIVITAS','ORIGINAL SI TEST DOCUMENT','AMOL menyetujui pengajuan','Nasabah menyetujui surat','Rp 250.000.000','000123456789012','PT Tujuan Pembayaran','Rina Wulandari','Bambang Haryanto','Budi Santoso']:
            self.assertIn(expected,text)
        self.assertEqual(reader.attachments['si-original.pdf'][0],original.getvalue())
        self.assertNotIn(self.token(doc),text)
        # Existing audit rows retain their original wording in storage while
        # the current UI and PDF use the renamed reviewer label.
        with app.database(True) as db:
            db.execute("UPDATE audit SET action=replace(action,'AMOL','SOL'),actor=replace(actor,'(AMOL)','(SOL)') WHERE doc_id=?", (doc,))
        status, legacy_pdf, _ = self.maker.call(route)
        self.assertEqual(status, 200)
        legacy_text = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(legacy_pdf)).pages)
        self.assertIn('AMOL menyetujui pengajuan', legacy_text)
        self.assertNotIn('SOL menyetujui pengajuan', legacy_text)
        actions = self.maker.call('/documents/'+doc)[1]['document']['audit']
        self.assertTrue(any(a['action']=='AMOL menyetujui pengajuan' for a in actions))
        with app.database() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE doc_id=? AND action='SOL menyetujui pengajuan'", (doc,)).fetchone()[0], 1)
        self.assertEqual(self.sol.call(route)[0],200)
        app.create_user('observer@example.test','BOH','boh','ObserverTest!2026')
        boh=Client(self.url);boh.call('/login',{'email':'observer@example.test','password':'ObserverTest!2026'})
        self.assertEqual(boh.call(route)[0],403)
        app.create_user('other@example.test','Other Maker','petugas','OtherMaker!2026')
        other=Client(self.url);other.call('/login',{'email':'other@example.test','password':'OtherMaker!2026'})
        self.assertEqual(other.call(route)[0],200)
        self.assertEqual(self.sol.call('/documents/'+doc+'/archive',{'version':1,'password':'SolDemo!2026'})[0],409)
        self.assertEqual(self.sol.call(route)[0],200)

    def test_execution_pdf_images_and_unreadable_original(self):
        image=BytesIO()
        with Image.new('RGBA',(10646,4965),(255,255,255,0)) as source:
            source.save(image,format='PNG')
        payload={**DESTINATION,'cif':'1234567','kind':'Standing Instruction','nominal':1,'file':{'name':'si.png','base64':base64.b64encode(image.getvalue()).decode()}}
        doc=self.maker.call('/documents',payload)[1]['id']
        self.respond(self.token(doc));self.sol.call('/documents/'+doc+'/review',{'version':1,'decision':'approved','notes':''})
        status,body,_=self.sol.call('/documents/'+doc+'/execution-pdf')
        self.assertEqual(status,200)
        reader=PdfReader(BytesIO(body))
        self.assertEqual(len(reader.pages),3)
        self.assertEqual(reader.attachments['si.png'][0],image.getvalue())
        embedded = reader.pages[-1].images[0].image
        self.assertLessEqual(embedded.width, 1240)
        self.assertLessEqual(embedded.height, 1754)
        self.assertEqual(embedded.convert('RGB').getpixel((0,0)), (255,255,255))
        malformed=self.create();self.respond(self.token(malformed));self.sol.call('/documents/'+malformed+'/review',{'version':1,'decision':'approved','notes':''})
        self.assertEqual(self.sol.call('/documents/'+malformed+'/execution-pdf')[0],422)
        self.assertFalse(app.EXECUTION_PDF_LOCK.locked())

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        app.DB_PATH=Path(self.temp.name)/'bpip.sqlite3'
        app.MAIL_MODE='console'
        app.PRODUCTION=False
        app.initialize()
        app.seed_demo()
        self.server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        self.url='http://127.0.0.1:'+str(self.server.server_port)
        app.BASE_URL=self.url
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.maker=LegacyDocumentClient(self.url);self.maker.login('petugas')
        self.sol=Client(self.url);self.sol.login('sol')
        self.checker=Client(self.url)
        result=self.checker.call('/login',{'email':'sol@example.test','password':'SolCheckerDemo!2026'})[1]
        self.checker.csrf=result['csrf']
        self.customer=Client(self.url)
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
        self.temp.cleanup()
    def create(self, client=None):
        status,result,_=(client or self.maker).call('/documents',{**DESTINATION,'cif':'1234567','kind':'Standing Instruction','nominal':250000000,'description':'Pembayaran vendor','file':FILE})
        self.assertEqual(status,201,result)
        return result['id']
    def token(self, doc_id):
        with app.database() as db:
            row=db.execute('SELECT body FROM outbox WHERE doc_id=? ORDER BY version DESC LIMIT 1',(doc_id,)).fetchone()
        return row['body'].split('/#confirm/')[1].split()[0]
    def respond(self, token, decision='confirmed'):
        return self.customer.call('/portal/decision',{'token':token,'decision':decision,'notes':'Tidak sesuai' if decision=='rejected' else '', 'acknowledged':True})

    def test_delivery_channel_email_whatsapp_and_both(self):
        with app.database(True) as db:
            db.execute("UPDATE customers SET phone='081234567890' WHERE cif='1234567'")
        for channel in ('whatsapp', 'email', 'both'):
            with self.subTest(channel=channel):
                status,result,_=self.maker.call('/documents',{**DESTINATION,'cif':'1234567','kind':'Standing Instruction','nominal':1,'file':FILE,'channel':channel})
                self.assertEqual(status,201,result)
                doc=result['id']
                with app.database() as db:
                    row=db.execute('SELECT * FROM outbox WHERE doc_id=?',(doc,)).fetchone()
                self.assertEqual(row['status'],'whatsapp_manual' if channel=='whatsapp' else 'queued')
                if channel=='whatsapp':
                    self.assertFalse(app.deliver_one())
                    messages=self.maker.call('/outbox')[1]['messages']
                    self.assertFalse(any(m['doc_id']==doc for m in messages))
                else:
                    self.assertTrue(app.deliver_one())
                if channel=='email':
                    self.assertIsNone(result['whatsapp'])
                else:
                    self.assertEqual(result['whatsapp']['phone'],'6281234567890')
                    self.assertIn(self.token(doc),result['whatsapp']['message'])
                    self.assertEqual(self.respond(self.token(doc))[0],200)
                    self.assertEqual(self.maker.call('/documents/'+doc+'/whatsapp-preview')[0],409)

    def test_delivery_channel_invalid_or_missing_phone_rolls_back(self):
        payload={**DESTINATION,'cif':'1234567','kind':'Standing Instruction','nominal':1,'file':FILE}
        with app.database(True) as db:
            db.execute("UPDATE customers SET phone='' WHERE cif='1234567'")
        for channel in ('sms','whatsapp','both',None):
            self.assertEqual(self.maker.call('/documents',{**payload,'channel':channel})[0],400)
        with app.database() as db:
            for table in ('documents','versions','outbox'):
                self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)
        self.assertEqual(self.maker.call('/documents',{**payload,'channel':'email'})[0],201)

    def test_delivery_channel_resend_with_revision_disabled(self):
        doc=self.create()
        with app.database(True) as db:
            db.execute("UPDATE customers SET phone='081234567890' WHERE cif='1234567'")
            db.execute("UPDATE outbox SET created='2020-01-01T00:00:00+00:00' WHERE doc_id=?",(doc,))
        old_token=self.token(doc)
        result=self.maker.call('/documents/'+doc+'/resend',{'version':1,'channel':'whatsapp'})
        self.assertEqual(result[0],200,result[1])
        self.assertIn(self.token(doc),result[1]['whatsapp']['message'])
        self.assertNotEqual(self.token(doc),old_token)
        self.assertEqual(self.respond(old_token)[0],410)
        self.assertFalse(app.deliver_one())
        self.respond(self.token(doc))
        self.assertEqual(self.sol.call('/documents/'+doc+'/review',{'version':2,'decision':'revision_requested','notes':'Perbaiki surat'})[0],400)
        result=self.maker.call('/documents/'+doc+'/revise',{**DESTINATION,'version':2,'kind':'Standing Instruction','nominal':2,'notes':'Diperbaiki','file':FILE,'channel':'both'})
        self.assertEqual(result[0],410,result[1])
        self.assertFalse(app.deliver_one())

    def test_both_channels_lock_current_link_and_resend_resets_selection(self):
        with app.database(True) as db:
            db.execute("UPDATE customers SET phone='081234567890' WHERE cif='1234567'")
        payload={**DESTINATION,'cif':'1234567','kind':'Standing Instruction','nominal':1,'file':FILE,'channel':'both'}
        status,result,_=self.maker.call('/documents',payload)
        self.assertEqual(status,201)
        doc=result['id'];token=self.token(doc);route='/documents/'+doc+'/send-confirmation'
        for _ in range(2):
            self.assertEqual(self.maker.call('/documents/'+doc)[1]['document']['delivery'],{'email_requested':True,'whatsapp_prepared':True})
        for channel in ('email','whatsapp','both'):
            self.assertEqual(self.maker.call(route,{'version':1,'channel':channel})[0],409)
        self.assertEqual(self.maker.call('/documents/'+doc+'/resend',{'version':1,'channel':'both'})[0],429)
        self.assertEqual(self.token(doc),token)
        with app.database(True) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM outbox WHERE doc_id=?',(doc,)).fetchone()[0],1)
            db.execute('UPDATE versions SET expires=? WHERE doc_id=?',(time.time()-1,doc))
        self.assertEqual(self.maker.call('/documents/'+doc+'/resend',{'version':1,'channel':'email'})[0],200)
        detail=self.maker.call('/documents/'+doc)[1]['document']
        self.assertEqual(detail['version'],2)
        self.assertEqual(detail['delivery'],{'email_requested':True,'whatsapp_prepared':False})

    def test_add_missing_channel_reuses_link_and_blocks_duplicate_requests(self):
        with app.database(True) as db:
            db.execute("UPDATE customers SET phone='081234567890' WHERE cif='1234567'")
        payload={**DESTINATION,'cif':'1234567','kind':'Standing Instruction','nominal':1,'file':FILE}
        for initial,remaining in (('email','whatsapp'),('whatsapp','email')):
            with self.subTest(initial=initial):
                doc=self.maker.call('/documents',{**payload,'channel':initial})[1]['id'];token=self.token(doc)
                route='/documents/'+doc+'/send-confirmation';data={'version':1,'channel':remaining}
                self.assertEqual(self.sol.call(route,data)[0],403)
                self.assertEqual(self.maker.call(route,data,csrf=False)[0],403)
                self.assertEqual(self.maker.call(route,{**data,'version':2})[0],409)
                status,result,_=self.maker.call(route,data)
                self.assertEqual(status,200,result)
                if remaining=='whatsapp': self.assertIn(token,result['whatsapp']['message'])
                else: self.assertIsNone(result['whatsapp'])
                self.assertEqual(self.token(doc),token)
                self.assertEqual(self.maker.call(route,data)[0],409)
                detail=self.maker.call('/documents/'+doc)[1]['document']
                self.assertEqual(detail['version'],1)
                self.assertEqual(detail['delivery'],{'email_requested':True,'whatsapp_prepared':True})
                with app.database() as db:
                    rows=list(db.execute('SELECT status FROM outbox WHERE doc_id=?',(doc,)))
                    self.assertEqual(len(rows),1)
                    self.assertEqual(rows[0]['status'],'queued')

    def test_current_confirmation_expiry_response_and_validation(self):
        doc=self.create();route='/documents/'+doc+'/send-confirmation';data={'version':1,'channel':'whatsapp'}
        self.assertEqual(self.maker.call(route,{'version':1,'channel':'sms'})[0],400)
        self.assertEqual(self.maker.call(route,data)[0],400)
        self.assertFalse(self.maker.call('/documents/'+doc)[1]['document']['delivery']['whatsapp_prepared'])
        with app.database(True) as db:
            db.execute("UPDATE customers SET phone='081234567890' WHERE cif='1234567'")
            db.execute('UPDATE versions SET expires=? WHERE doc_id=?',(time.time()-1,doc))
        self.assertEqual(self.maker.call(route,data)[0],409)
        with app.database(True) as db:
            db.execute('UPDATE versions SET expires=? WHERE doc_id=?',(time.time()+3600,doc))
        self.assertEqual(self.respond(self.token(doc))[0],200)
        self.assertEqual(self.maker.call(route,data)[0],409)

    def test_concurrent_current_whatsapp_selection_only_records_once(self):
        doc=self.create()
        with app.database(True) as db:
            db.execute("UPDATE customers SET phone='081234567890' WHERE cif='1234567'")
        clients=[Client(self.url),Client(self.url)]
        for client in clients: client.login('petugas')
        route='/documents/'+doc+'/send-confirmation';payload={'version':1,'channel':'whatsapp'}
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda client:client.call(route,payload)[0],clients))
        self.assertEqual(sorted(results),[200,409])
        with app.database() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE doc_id=? AND action='Konfirmasi WhatsApp disiapkan'",(doc,)).fetchone()[0],1)

    def test_whatsapp_preview_reuses_token_without_sending_or_renewing(self):
        doc=self.create();token=self.token(doc)
        with app.database() as db:
            db.execute("UPDATE customers SET phone='081234567890' WHERE cif='1234567'")
            before={table:[tuple(row) for row in db.execute('SELECT * FROM '+table)] for table in ('versions','outbox','audit')}
        route='/documents/'+doc+'/whatsapp-preview'
        status,preview,_=self.maker.call(route)
        self.assertEqual(status,200,preview)
        self.assertEqual(preview['phone'],'6281234567890')
        self.assertIn(app.BASE_URL+'/#confirm/'+token,preview['message'])
        self.assertNotIn(DESTINATION['destination_account'],preview['message'])
        self.assertNotIn('CIF',preview['message'])
        url=urlsplit(preview['url'])
        self.assertEqual((url.scheme,url.netloc,url.path),('https','wa.me','/6281234567890'))
        self.assertEqual(parse_qs(url.query)['text'],[preview['message']])
        with app.database() as db:
            after={table:[tuple(row) for row in db.execute('SELECT * FROM '+table)] for table in before}
        self.assertEqual(before,after)
        self.assertEqual(self.respond(token)[0],200)
        self.assertEqual(self.maker.call(route)[0],409)
        self.assertEqual(self.respond(token)[0],410)

    def test_whatsapp_preview_enforces_roles_ownership_and_current_link(self):
        doc=self.create();route='/documents/'+doc+'/whatsapp-preview'
        app.create_user('other@example.test','Other Officer','petugas','OtherOfficer!2026')
        other=Client(self.url)
        other.call('/login',{'email':'other@example.test','password':'OtherOfficer!2026'})
        self.assertEqual(other.call(route)[0],403)
        self.assertEqual(self.sol.call(route)[0],403)
        self.assertEqual(self.boh_client().call(route)[0],403)
        self.assertEqual(self.customer.call(route)[0],401)
        with app.database() as db:
            db.execute("UPDATE customers SET phone='' WHERE cif='1234567'")
        self.assertEqual(self.maker.call(route)[0],400)
        with app.database() as db:
            db.execute("UPDATE customers SET phone='+6281234567890' WHERE cif='1234567'")
            db.execute('UPDATE versions SET expires=? WHERE doc_id=?',(time.time()-1,doc))
        self.assertEqual(self.maker.call(route)[0],409)
        with app.database() as db:
            db.execute('UPDATE versions SET expires=?,token_hash=? WHERE doc_id=?',(time.time()+3600,app.digest('old-token'),doc))
        self.assertEqual(self.maker.call(route)[0],409)
        with app.database() as db:
            db.execute("UPDATE documents SET sol_status='cancelled' WHERE id=?",(doc,))
        self.assertEqual(self.maker.call(route)[0],409)

    def test_whatsapp_preview_uses_phone_changes_only_after_amol_approval(self):
        doc=self.create();route='/documents/'+doc+'/whatsapp-preview'
        with app.database() as db:
            db.execute("UPDATE customers SET phone='081234567890' WHERE cif='1234567'")
        status,request,_=self.checker.call('/customers/1234567/phone',{'phone':'+6285712345678','reason':'Nomor terbaru'})
        self.assertEqual(status,200,request)
        self.assertEqual(self.maker.call(route)[1]['phone'],'6281234567890')
        reviewer=self.sol
        self.assertEqual(reviewer.call('/customer-edit-requests/'+request['id']+'/review',{'decision':'approved'})[0],200)
        self.assertEqual(self.maker.call(route)[1]['phone'],'6285712345678')

    def test_whatsapp_preview_follows_resend_current_version(self):
        doc=self.create();old_token=self.token(doc)
        with app.database() as db:
            db.execute("UPDATE customers SET phone='081234567890' WHERE cif='1234567'")
            stamp=app.datetime.fromtimestamp(time.time()-90000,app.timezone.utc).isoformat()
            db.execute('UPDATE outbox SET created=?,sent_at=NULL WHERE doc_id=?',(stamp,doc))
        self.assertEqual(self.maker.call('/documents/'+doc+'/resend',{'version':1})[0],200)
        new_token=self.token(doc)
        status,preview,_=self.maker.call('/documents/'+doc+'/whatsapp-preview')
        self.assertEqual(status,200,preview)
        self.assertIn('/#confirm/'+new_token,preview['message'])
        self.assertNotIn(old_token,preview['message'])
        with app.database() as db:
            version=db.execute('SELECT expires FROM versions WHERE doc_id=? AND version=2',(doc,)).fetchone()
        self.assertEqual(preview['expires'],version['expires'])

    def test_simple_resend_and_approval_flow(self):
        doc_id=self.create();token1=self.token(doc_id)
        for _ in range(2):
            status,result,_=self.customer.call('/portal',{'token':token1})
            self.assertEqual(status,200)
            self.assertEqual(result['document']['nominal'],250000000)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':1,'decision':'approved','notes':''})[0],409)
        with app.database(True) as db:
            db.execute('UPDATE versions SET expires=? WHERE doc_id=?',(time.time()-1,doc_id))
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/resend',{'version':1})[0],200)
        token2=self.token(doc_id)
        self.assertNotEqual(token1,token2)
        self.assertEqual(self.customer.call('/portal',{'token':token1})[0],410)
        self.assertEqual(self.respond(token2)[0],200)
        self.assertEqual(self.respond(token2)[0],410)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':2,'decision':'revision_requested','notes':'Perbaiki surat'})[0],400)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':1,'decision':'approved','notes':''})[0],409)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':2,'decision':'approved','notes':'Surat sesuai'})[0],200)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':2,'decision':'rejected','notes':'Ubah keputusan'})[0],409)
        d=self.maker.call('/documents/'+doc_id)[1]['document']
        self.assertEqual(d['sol_status'],'approved')
        self.assertEqual(len(d['versions']),2)
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/versions/1/file')[0],200)
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/versions/3/file')[0],404)
        self.assertTrue(any(a['action']=='AMOL menyetujui pengajuan' for a in d['audit']))
        self.assertTrue(any(a['ip'] for a in d['audit']))
        self.assertEqual(self.customer.call('/documents')[0],401)

    def test_rejected_customer_cannot_continue_to_approval_or_revision(self):
        doc_id=self.create()
        self.assertEqual(self.respond(self.token(doc_id),'rejected')[0],200)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':1,'decision':'approved','notes':''})[0],409)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':1,'decision':'revision_requested','notes':'Perbaiki surat'})[0],400)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':1,'decision':'rejected','notes':''})[0],400)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':1,'decision':'rejected','notes':'Nasabah menolak surat'})[0],200)
    def test_legacy_revision_request_cannot_reopen_customer_rejection(self):
        doc_id=self.create()
        self.assertEqual(self.respond(self.token(doc_id),'rejected')[0],200)
        with app.database(write=True) as db:
            db.execute("UPDATE documents SET sol_status='revision_requested' WHERE id=?",(doc_id,))
        revision={**DESTINATION,'version':1,'kind':'Standing Instruction','nominal':260000000,'description':'Perbaikan surat','notes':'Surat diperbaiki','file':FILE}
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/revise',revision)[0],410)
        detail=self.maker.call('/documents/'+doc_id)[1]['document']
        self.assertEqual(detail['version'],1)
        self.assertEqual(detail['customer_status'],'rejected')

    def test_roles_csrf_and_ownership(self):
        doc_id=self.create()
        self.assertEqual(self.sol.call('/documents',{**DESTINATION,'cif':'1234567','kind':'Warkat','nominal':1,'file':FILE})[0],403)
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/review',{'version':1,'decision':'approved'})[0],403)
        self.assertEqual(self.maker.call('/customers',{'cif':'888','name':'PT Baru','account':'000123456789012','person':'Ani','email':'ani@example.com'},csrf=False)[0],403)
        self.assertEqual(self.maker.call('/logout',{},origin='https://evil.example')[0],403)
        app.create_user('other@example.com','Other maker','petugas','OtherSecret!2026')
        other=Client(self.url)
        status,res,_=other.call('/login',{'email':'other@example.com','password':'OtherSecret!2026'})
        other.csrf=res['csrf']
        self.assertEqual(other.call('/documents/'+doc_id)[0],200)
        self.assertEqual(other.call('/documents/'+doc_id+'/file')[0],200)
        self.assertEqual(other.call('/documents')[1]['documents'][0]['id'],doc_id)
        self.assertEqual(other.call('/documents/'+doc_id+'/cancel',{'version':1,'notes':'Tidak berwenang'})[0],403)
    def test_only_sol_can_add_customer_and_maker_can_use_it(self):
        customer={'cif':'888','name':'PT Baru','account':'000123456789012','person':'Ani','email':'ani@example.com','phone':'081234567890'}
        self.assertEqual(self.maker.call('/customers',customer)[0],403)
        self.assertEqual(self.customer.call('/customers',customer)[0],401)
        self.assertEqual(self.sol.call('/customers',customer,csrf=False)[0],403)
        self.assertEqual(self.sol.call('/customers',customer)[0],201)
        self.assertEqual(self.sol.call('/customers',customer)[0],409)
        status,result,_=self.maker.call('/customers')
        self.assertEqual(status,200)
        self.assertTrue(any(c['cif']=='888' for c in result['customers']))
        self.assertEqual(self.maker.call('/documents',{**DESTINATION,'cif':'888','kind':'Warkat','nominal':100,'file':FILE})[0],201)
    def test_account_requires_exactly_fifteen_digits(self):
        customer={'cif':'889','name':'Uji','account':'12345678901234','person':'Ani','email':'ani@example.com','phone':'081234567890'}
        for account in ('12345678901234','12345678901234x','1234567890123456','1'*51):
            customer['account']=account
            self.assertEqual(self.sol.call('/customers',customer)[0],400)
        customer['account']='000123456789012'
        self.assertEqual(self.sol.call('/customers',customer)[0],201)
        rows=self.maker.call('/customers')[1]['customers']
        self.assertEqual(next(c['account'] for c in rows if c['cif']=='889'),customer['account'])

    def test_customer_phone_create_update_and_permissions(self):
        customer={'cif':'887','name':'Uji HP','account':'000123456789012','person':'Direktur','email':'hp@example.com','phone':'081234567890'}
        for phone in ('', '   ', 'abc'):
            self.assertEqual(self.sol.call('/customers',{**customer,'phone':phone})[0],400)
        self.assertEqual(self.sol.call('/customers',{k:v for k,v in customer.items() if k != 'phone'})[0],400)
        self.assertEqual(self.sol.call('/customers',customer)[0],201)
        def stored_phone():
            rows=self.maker.call('/customers')[1]['customers']
            return next(c['phone'] for c in rows if c['cif']=='887')
        self.assertEqual(stored_phone(), '081234567890')
        self.assertEqual(self.maker.call('/customers/887/phone',{'phone':'+6281234567890'})[0],403)
        self.assertEqual(self.checker.call('/customers/887/phone',{'phone':'short'})[0],400)
        self.assertEqual(stored_phone(), '081234567890')
        status,result,_=self.checker.call('/customers/887/phone',{'phone':'+62 812-3456-7890'})
        self.assertEqual(status,200)
        self.assertEqual(stored_phone(), '081234567890')
        reviewer=self.sol
        self.assertEqual(reviewer.call('/customer-edit-requests/'+result['id']+'/review',{'decision':'approved'})[0],200)
        self.assertEqual(stored_phone(), '+6281234567890')
        self.assertEqual(self.checker.call('/customers/887/phone',{'phone':''})[0],400)
        self.assertEqual(stored_phone(), '+6281234567890')
        self.assertEqual(self.checker.call('/customers/999999/phone',{'phone':'081234567890'})[0],404)
    def test_cancel_is_disabled_without_changing_document_or_token(self):
        doc_id=self.create();token=self.token(doc_id)
        before=self.maker.call('/documents/'+doc_id)[1]['document']
        payload={'version':1,'notes':'Transaksi tidak dilanjutkan'}
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/cancel',payload)[0],403)
        for data in (payload, {'version':1,'notes':''}, {'version':2,'notes':'Uji'}):
            self.assertEqual(self.maker.call('/documents/'+doc_id+'/cancel',data)[0],410)
        d=self.maker.call('/documents/'+doc_id)[1]['document']
        self.assertEqual(d['sol_status'],'pending')
        self.assertEqual(d['updated'],before['updated'])
        self.assertEqual(d['audit'],before['audit'])
        self.assertEqual(len(d['versions']),1)
        self.assertEqual(self.customer.call('/portal',{'token':token})[0],200)
        self.assertEqual(self.respond(token)[0],200)

    def test_final_sol_decision_cannot_be_cancelled(self):
        doc_id=self.create();self.respond(self.token(doc_id))
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':1,'decision':'approved','notes':''})[0],200)
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/cancel',{'version':1,'notes':'Uji'})[0],410)
    def test_legacy_revision_request_can_only_receive_final_sol_decision(self):
        for decision in ('approved','rejected'):
            with self.subTest(decision=decision):
                doc_id=self.create()
                self.assertEqual(self.respond(self.token(doc_id))[0],200)
                path='/documents/'+doc_id
                with app.database(True) as db:
                    db.execute("UPDATE documents SET sol_status='revision_requested' WHERE id=?",(doc_id,))
                self.assertEqual(self.maker.call(path+'/cancel',{'version':1,'notes':'Uji'})[0],410)
                self.assertEqual(self.maker.call(path+'/revise',{**DESTINATION,'version':1,'kind':'Warkat','nominal':100,'file':FILE,'notes':'Revisi'})[0],410)
                self.assertEqual(self.sol.call(path+'/review',{'version':1,'decision':decision,'notes':'Keputusan akhir'})[0],200)
                self.assertEqual(self.maker.call(path)[1]['document']['sol_status'],decision)

    def test_customer_approval_blocks_single_and_bulk_document_deletion(self):
        pending = self.create()
        approved = self.create()
        self.assertEqual(self.respond(self.token(approved))[0], 200)
        password = {'password': 'SolDemo!2026'}
        self.assertEqual(self.sol.call('/documents/' + approved + '/archive', {**password, 'version': 1})[0], 409)
        selection = [{'id': pending, 'version': 1}, {'id': approved, 'version': 1}]
        self.assertEqual(self.sol.call('/documents/archive-selected', {**password, 'documents': selection})[0], 409)
        self.assertEqual(self.sol.call('/documents/archive-all', {**password, 'ids': [pending, approved]})[0], 409)
        self.assertEqual(self.sol.call('/documents')[1]['archived_count'], 0)
        self.assertEqual(self.sol.call('/documents/' + pending)[0], 200)
        self.assertEqual(self.sol.call('/documents/' + approved)[1]['document']['customer_status'], 'confirmed')
        # Older approved records already in the archive must also retain their evidence.
        with app.database(True) as db:
            db.execute('INSERT INTO archived_documents VALUES(?,?,?)', (approved, app.now(), 'legacy'))
        self.assertEqual(self.sol.call('/documents/' + approved + '/purge', {**password, 'confirmation': approved})[0], 409)
        with app.database() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM versions WHERE doc_id=?', (approved,)).fetchone()[0], 1)
    def test_selected_documents_archive_only_selection_atomically(self):
        first=self.create();second=self.create()
        first_token=self.token(first);second_token=self.token(second)
        endpoint='/documents/archive-selected'
        payload={'documents':[{'id':first,'version':1}],'password':'SolDemo!2026'}
        self.assertEqual(self.maker.call(endpoint,payload)[0],403)
        self.assertEqual(self.sol.call(endpoint,payload,csrf=False)[0],403)
        self.assertEqual(self.sol.call(endpoint,{**payload,'password':'wrong'})[0],403)
        for selection,code in [([],400),([{'id':first,'version':1}]*2,400),([{'id':first,'version':1},{'id':second,'version':2}],409),([{'id':first,'version':1},{'id':'missing','version':1}],409)]:
            self.assertEqual(self.sol.call(endpoint,{**payload,'documents':selection})[0],code)
            self.assertEqual(len(self.maker.call('/documents')[1]['documents']),2)
        self.assertEqual(self.sol.call(endpoint,payload)[1]['count'],1)
        self.assertEqual([d['id'] for d in self.maker.call('/documents')[1]['documents']],[second])
        self.assertEqual(self.sol.call('/documents')[1]['archived_count'],1)
        self.assertEqual(self.customer.call('/portal',{'token':first_token})[0],410)
        self.assertEqual(self.customer.call('/portal',{'token':second_token})[0],200)
        self.assertEqual(self.sol.call(endpoint,payload)[0],409)
        with app.database() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM documents').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM versions WHERE doc_id=?',(first,)).fetchone()[0],1)
        self.assertEqual(len(self.sol.call('/customers')[1]['customers']),3)

    def test_sol_archive_all_and_restore_preserve_records(self):
        doc_id=self.create();token=self.token(doc_id)
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/archive',{'version':1})[0],403)
        self.assertEqual(self.maker.call('/documents/archive-all',{'ids':[doc_id]})[0],403)
        self.assertEqual(self.sol.call('/documents/archive-all',{'ids':[],'password':'SolDemo!2026'})[0],409)
        self.assertEqual(self.sol.call('/documents/archive-all',{'ids':[doc_id],'password':'SolDemo!2026'},csrf=False)[0],403)
        self.assertEqual(self.sol.call('/documents/archive-all',{'ids':[doc_id],'password':'SolDemo!2026'})[0],200)
        self.assertEqual(self.maker.call('/documents')[1]['documents'],[])
        self.assertEqual(self.sol.call('/documents')[1]['archived_count'],1)
        self.assertEqual(self.maker.call('/documents/'+doc_id)[0],404)
        self.assertEqual(self.customer.call('/portal',{'token':token})[0],410)
        self.assertEqual(self.respond(token)[0],410)
        self.assertFalse(app.deliver_one())
        self.assertEqual(self.maker.call('/documents/restore-all',{})[0],403)
        self.assertEqual(self.sol.call('/documents/restore-all',{})[0],200)
        d=self.sol.call('/documents/'+doc_id)[1]['document']
        self.assertEqual(len(d['versions']),1)
        self.assertTrue(any(a['action']=='AMOL memulihkan pengajuan' for a in d['audit']))
        self.assertEqual(self.customer.call('/portal',{'token':token})[0],410)
        self.assertEqual(len(self.maker.call('/customers')[1]['customers']),3)
    def test_customer_delete_preserves_existing_documents_and_restore(self):
        doc_id=self.create()
        self.assertEqual(self.maker.call('/customers/1234567/archive',{})[0],403)
        self.assertEqual(self.sol.call('/customers/1234567/archive',{'password':'SolDemo!2026'},csrf=False)[0],403)
        self.assertEqual(self.sol.call('/customers/1234567/archive',{'password':'SolDemo!2026'})[0],200)
        self.assertEqual(self.sol.call('/customers/1234567/archive',{'password':'SolDemo!2026'})[0],409)
        self.assertFalse(any(c['cif']=='1234567' for c in self.maker.call('/customers')[1]['customers']))
        self.assertEqual(self.sol.call('/customers')[1]['archived_count'],1)
        self.assertEqual(self.maker.call('/documents',{**DESTINATION,'cif':'1234567','kind':'Warkat','nominal':10,'file':FILE})[0],409)
        self.assertEqual(self.maker.call('/documents/'+doc_id)[1]['document']['customer_name'],'PT Maju Bersama')
        self.assertEqual(self.respond(self.token(doc_id))[0],200)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':1,'decision':'approved','notes':''})[0],200)
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/revise',{**DESTINATION,'version':1,'kind':'Warkat','nominal':10,'file':FILE,'notes':'Diperbaiki'})[0],410)
        self.assertEqual(self.maker.call('/customers/restore-all',{})[0],403)
        self.assertEqual(self.sol.call('/customers/restore-all',{})[0],200)
        self.assertTrue(any(c['cif']=='1234567' for c in self.maker.call('/customers')[1]['customers']))
    def test_selected_customers_delete_master_and_preserve_history(self):
        doc_id=self.create()
        payload={'cifs':['1234567','9876543'],'password':'SolDemo!2026'}
        self.assertEqual(self.maker.call('/customers/delete-selected',payload)[0],403)
        self.assertEqual(self.sol.call('/customers/delete-selected',{**payload,'password':'wrong'})[0],403)
        self.assertEqual(self.sol.call('/customers/delete-selected',{**payload,'cifs':['1234567','999999']})[0],409)
        self.assertEqual(len(self.sol.call('/customers')[1]['customers']),3)
        self.assertEqual(self.sol.call('/customers/delete-selected',{**payload,'cifs':['1234567','1234567']})[0],400)
        self.assertEqual(self.sol.call('/customers/delete-selected',payload)[0],200)
        self.assertEqual([c['cif'] for c in self.sol.call('/customers')[1]['customers']],['5551234'])
        self.assertEqual(self.maker.call('/documents/'+doc_id)[0],200)
        with app.database() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM customers WHERE cif IN (?,?)',tuple(payload['cifs'])).fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM archived_customers').fetchone()[0],0)
        self.assertEqual(self.sol.call('/customers/restore-all',{})[0],200)
        self.assertEqual(len(self.sol.call('/customers')[1]['customers']),1)
        document=self.maker.call('/documents/'+doc_id)[1]['document']
        self.assertEqual(document['customer_name'],'PT Maju Bersama')
        self.assertEqual(document['account'],'001234567890')
        self.assertEqual(self.respond(self.token(doc_id))[0],200)
    def test_single_archive_does_not_hide_other_documents(self):
        first=self.create();second=self.create()
        self.assertEqual(self.sol.call('/documents/'+first+'/archive',{'version':2,'password':'SolDemo!2026'})[0],409)
        self.assertEqual(self.sol.call('/documents/'+first+'/archive',{'version':1,'password':'SolDemo!2026'})[0],200)
        self.assertEqual([d['id'] for d in self.sol.call('/documents')[1]['documents']],[second])
    def test_password_selective_restore_and_permanent_deletion(self):
        doc=self.create()
        self.assertEqual(self.sol.call('/customers/1234567/archive',{'password':'wrong'})[0],403)
        self.assertEqual(self.sol.call('/customers/1234567/archive',{'password':'SolDemo!2026'})[0],200)
        self.assertEqual(self.maker.call('/customers/archived')[0],403)
        self.assertEqual(self.sol.call('/customers/archived')[1]['items'][0]['cif'],'1234567')
        self.assertEqual(self.sol.call('/customers/1234567/restore',{})[0],200)
        self.assertEqual(self.sol.call('/customers/1234567/archive',{'password':'SolDemo!2026'})[0],200)
        purge={'password':'SolDemo!2026','confirmation':'wrong'}
        self.assertEqual(self.sol.call('/customers/1234567/purge',purge)[0],400)
        purge['confirmation']='1234567'
        self.assertEqual(self.sol.call('/customers/1234567/purge',purge)[0],200)
        self.assertEqual(self.sol.call('/documents/'+doc)[0],200)
        self.assertEqual(self.sol.call('/documents/'+doc+'/archive',{'version':1,'password':'SolDemo!2026'})[0],200)
        self.assertEqual(self.sol.call('/documents/'+doc+'/restore',{})[0],200)
        self.assertEqual(self.sol.call('/documents/'+doc+'/archive',{'version':1,'password':'SolDemo!2026'})[0],200)
        self.assertEqual(self.sol.call('/documents/'+doc+'/purge',{'password':'SolDemo!2026','confirmation':doc})[0],200)
        with app.database() as db:
            for table,col in [('documents','id'),('versions','doc_id'),('outbox','doc_id')]:
                self.assertEqual(db.execute(f'SELECT COUNT(*) FROM {table} WHERE {col}=?',(doc,)).fetchone()[0],0)
            self.assertGreater(db.execute('SELECT COUNT(*) FROM audit WHERE doc_id=?',(doc,)).fetchone()[0],0)
    def test_boh_document_read_only_and_password_lockout(self):
        doc=self.create()
        account={'name':'BOH Uji','email':'boh@example.test','new_password':'ObserverTest!2026','password':'SolDemo!2026'}
        self.assertEqual(self.maker.call('/users/boh',account)[0],404)
        self.assertEqual(self.sol.call('/users/boh',account)[0],404)
        app.create_user(account['email'],account['name'],'boh',account['new_password'])
        boh=Client(self.url)
        status,data,_=boh.call('/login',{'email':account['email'],'password':account['new_password']})
        self.assertEqual(status,200);boh.csrf=data['csrf']
        rows=boh.call('/documents')[1]['documents']
        self.assertEqual(rows[0]['id'],doc)
        self.assertNotIn('email',rows[0]);self.assertNotIn('account',rows[0]);self.assertNotIn('file',rows[0])
        for path in ['/customers','/outbox','/customers/archived']:
            self.assertEqual(boh.call(path)[0],403)
        for path in ['/documents/'+doc,'/documents/'+doc+'/file','/documents/'+doc+'/versions/1/file']:
            self.assertEqual(boh.call(path)[0],200)
        for path,payload in [('/customers',{}),('/documents',{}),('/customers/1234567/archive',{}),('/users/boh',account)] + [('/documents/'+doc+'/'+action,{'version':1,'decision':'approved'}) for action in ('review','resend','send-confirmation','revise','cancel','archive')]:
            self.assertEqual(boh.call(path,payload)[0],403)
        for _ in range(5):
            self.assertEqual(self.sol.call('/customers/1234567/archive',{'password':'wrong'})[0],403)
        self.assertEqual(self.sol.call('/customers/1234567/archive',{'password':'SolDemo!2026'})[0],429)
    def test_resend_waits_24_hours_and_restarts_after_each_send(self):
        doc_id = self.create()
        path = '/documents/' + doc_id
        original_token = self.token(doc_id)
        original = self.maker.call(path)[1]['document']
        self.assertGreater(original['resend_available_at'], time.time() + 86300)
        self.assertEqual(self.maker.call(path + '/resend', {'version': 1})[0], 429)
        with app.database(True) as db:
            nearly = app.datetime.fromtimestamp(time.time() - 86400 + 60, app.timezone.utc).isoformat()
            db.execute('UPDATE outbox SET created=? WHERE doc_id=?', (nearly, doc_id))
        self.assertEqual(self.maker.call(path + '/resend', {'version': 1})[0], 429)
        unchanged = self.maker.call(path)[1]['document']
        self.assertEqual(unchanged['version'], 1)
        self.assertEqual(len(unchanged['versions']), 1)
        self.assertEqual(self.token(doc_id), original_token)
        with app.database(True) as db:
            boundary = app.datetime.fromtimestamp(time.time() - 86400, app.timezone.utc).isoformat()
            db.execute('UPDATE outbox SET created=? WHERE doc_id=?', (boundary, doc_id))
        self.assertEqual(self.maker.call(path + '/resend', {'version': 1})[0], 200)
        updated = self.maker.call(path)[1]['document']
        self.assertEqual(updated['version'], 2)
        self.assertEqual(len(updated['versions']), 2)
        self.assertNotEqual(self.token(doc_id), original_token)
        self.assertEqual(self.respond(original_token)[0], 410)
        self.assertEqual(self.maker.call(path + '/resend', {'version': 2})[0], 429)
        self.assertEqual(self.maker.call(path + '/cancel', {'version': 2, 'notes': 'Pembatalan oleh petugas'})[0], 410)

    def test_resend_waits_from_actual_email_delivery(self):
        doc_id = self.create()
        path = '/documents/' + doc_id
        with app.database(True) as db:
            created = app.datetime.fromtimestamp(time.time() - 172800, app.timezone.utc).isoformat()
            sent = app.datetime.fromtimestamp(time.time() - 3600, app.timezone.utc).isoformat()
            db.execute('UPDATE outbox SET created=?,sent_at=? WHERE doc_id=?', (created, sent, doc_id))
        self.assertEqual(self.maker.call(path + '/resend', {'version': 1})[0], 429)
        with app.database(True) as db:
            sent = app.datetime.fromtimestamp(time.time() - 86400, app.timezone.utc).isoformat()
            db.execute('UPDATE outbox SET sent_at=? WHERE doc_id=?', (sent, doc_id))
        self.assertEqual(self.maker.call(path + '/resend', {'version': 1})[0], 200)

    def test_resend_accepts_expired_link_before_24_hours_for_all_channels(self):
        with app.database(True) as db:
            db.execute("UPDATE customers SET phone='081234567890' WHERE cif='1234567'")
        for channel in ('email','whatsapp','both'):
            with self.subTest(channel=channel):
                doc=self.create();old_token=self.token(doc)
                self.assertEqual(self.maker.call('/documents/'+doc+'/resend',{'version':1,'channel':channel})[0],429)
                with app.database(True) as db:
                    db.execute('UPDATE versions SET expires=? WHERE doc_id=?',(time.time()-1,doc))
                status,result,_=self.maker.call('/documents/'+doc+'/resend',{'version':1,'channel':channel})
                self.assertEqual(status,200,result)
                new_token=self.token(doc)
                self.assertNotEqual(new_token,old_token)
                self.assertEqual(self.customer.call('/portal',{'token':old_token})[0],410)
                self.assertEqual(self.customer.call('/portal',{'token':new_token})[0],200)
                self.assertEqual(self.maker.call('/documents/'+doc+'/resend',{'version':2,'channel':channel})[0],429)

    def test_expired_links_validation_and_resend(self):
        doc_id=self.create();token=self.token(doc_id)
        self.assertEqual(self.customer.call('/portal/decision',{'token':token,'decision':'confirmed','acknowledged':False})[0],400)
        self.assertEqual(self.customer.call('/portal/decision',{'token':token,'decision':'rejected','acknowledged':True,'notes':''})[0],400)
        with app.database(True) as db:
            db.execute('UPDATE versions SET expires=? WHERE doc_id=?',(time.time()-1,doc_id))
            db.execute('UPDATE outbox SET created=? WHERE doc_id=?',('2020-01-01T00:00:00+00:00',doc_id))
        self.assertEqual(self.respond(token)[0],410)
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/resend',{'version':1})[0],200)
        new_token=self.token(doc_id)
        self.assertNotEqual(token,new_token)
        self.assertEqual(self.respond(new_token)[0],200)
        for invalid in (-1,0,1.5,True,'1000',1000000000000000):
            status,_,_=self.maker.call('/documents',{**DESTINATION,'cif':'1234567','kind':'Warkat','nominal':invalid,'file':FILE})
            self.assertEqual(status,400)
        bad_file={'name':'payload.html','base64':base64.b64encode(b'<script>alert(1)</script>').decode()}
        self.assertEqual(self.maker.call('/documents',{**DESTINATION,'cif':'1234567','kind':'Warkat','nominal':100,'file':bad_file})[0],400)
    def test_concurrent_decisions_single_use(self):
        doc_id=self.create();token=self.token(doc_id)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(self.respond,token,decision) for decision in ('confirmed','rejected')]
            statuses=sorted(f.result()[0] for f in futures)
        self.assertEqual(statuses,[200,410])
        with app.database() as db:
            count=db.execute("SELECT COUNT(*) FROM audit WHERE doc_id=? AND action LIKE 'Nasabah %'",(doc_id,)).fetchone()[0]
        self.assertEqual(count,1)
    def test_outbox_local_smtp_retry_and_persistence(self):
        doc_id=self.create()
        self.assertTrue(app.deliver_one())
        status,res,_=self.maker.call('/outbox')
        self.assertEqual(status,200)
        self.assertEqual(res['messages'][0]['status'],'local')
        self.assertEqual(len(list((app.DB_PATH.parent/'outbox').glob('*.eml'))),1)
        app.initialize() # Startup preserves data.
        self.assertEqual(self.maker.call('/documents')[1]['documents'][0]['id'],doc_id)
        app.MAIL_MODE='smtp'
        with app.database(True) as db:
            db.execute("UPDATE outbox SET status='queued',next_attempt=0")
        smtp=unittest.mock.MagicMock()
        with patch.dict(os.environ,{'SMTP_HOST':'smtp.example.com','SMTP_FROM':'sender@example.com','SMTP_USER':'sender','SMTP_PASSWORD':'secret'}),patch.object(app.smtplib,'SMTP',return_value=smtp):
            self.assertTrue(app.deliver_one())
            smtp.__enter__.return_value.starttls.assert_called_once()
            smtp.__enter__.return_value.send_message.assert_called_once()
        self.assertEqual(self.maker.call('/documents/'+doc_id)[1]['document']['mail']['status'],'sent')
        with app.database(True) as db:
            db.execute("UPDATE outbox SET status='queued',next_attempt=0,attempts=4")
        with patch.dict(os.environ,{'SMTP_HOST':'smtp.example.com'}),patch.object(app.smtplib,'SMTP',side_effect=OSError('test disconnect')),patch.object(app.logging,'exception'):
            app.deliver_one()
        self.assertEqual(self.maker.call('/documents/'+doc_id)[1]['document']['mail']['status'],'failed')
        self.assertEqual(self.maker.call('/outbox')[0],404) # Token previews absent in SMTP mode.
    def test_confirmation_email_format_sender_and_escaped_html(self):
        doc_id=self.create()
        with app.database() as db:
            row=dict(db.execute('SELECT * FROM outbox WHERE doc_id=?',(doc_id,)).fetchone())
            expires=db.execute('SELECT expires FROM versions WHERE doc_id=? AND version=1',(doc_id,)).fetchone()['expires']
        self.assertIn(expiry_label(expires),row['body'])
        self.assertIn('Verifikasi Transaksi',row['subject'])
        row['body']='Yth. <script>alert(1)</script>,\n\n'+app.BASE_URL+'/#confirm/test_token\n\nJangan bagikan tautan ini.'
        with patch.dict(os.environ,{'SMTP_HOST':'smtp.gmail.com','SMTP_USER':'sender@gmail.com','SMTP_FROM':'BPIP <other@example.com>'}):
            message,sender=app.build_confirmation_email(row)
        message=BytesParser(policy=app.SMTP).parsebytes(message.as_bytes())
        self.assertEqual(sender,'sender@gmail.com')
        self.assertEqual(app.parseaddr(message['From'])[1],sender)
        self.assertEqual(app.parseaddr(message['Reply-To'])[1],sender)
        self.assertIsNotNone(message['Date'])
        self.assertEqual(message['Message-ID'],f"<{row['id']}@gmail.com>")
        self.assertEqual(message.get_content_type(),'multipart/alternative')
        self.assertEqual(message.get_body(preferencelist=('plain',)).get_content().replace('\r\n','\n'),row['body']+'\n')
        html_body=message.get_body(preferencelist=('html',)).get_content()
        self.assertIn('href="'+app.BASE_URL+'/#confirm/test_token"',html_body)
        self.assertNotIn('<script>',html_body)
        self.assertIn('&lt;script&gt;',html_body)
        self.assertNotIn('DKIM-Signature',message)
        self.assertIn('BRI VISTA',html_body)
        self.assertIn('Verification, Integration &amp; Secure Tracking Application',html_body)
        self.assertNotIn('<img',html_body)
        self.assertNotIn('/assets/',html_body)
        self.assertNotIn('cid:',html_body)
        self.assertEqual([part.get_content_type() for part in message.walk()],['multipart/alternative','text/plain','text/html'])
        self.assertEqual(list(message.iter_attachments()),[])
        self.assertFalse(any(part.get('Content-ID') or part.get_filename() for part in message.walk()))
        self.assertNotIn('(v1)',row['subject'])
        with patch.dict(os.environ,{'SMTP_HOST':'smtp.gmail.com','SMTP_USER':''}):
            with self.assertRaises(app.AppError):app.build_confirmation_email(row)
    def test_login_limits_headers_password_and_logout(self):
        headers=self.maker.login('petugas')
        self.assertIn('HttpOnly',headers['Set-Cookie'])
        self.assertIn('SameSite=Strict',headers['Set-Cookie'])
        self.assertEqual(headers['Referrer-Policy'],'no-referrer')
        self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
        self.assertEqual(self.maker.call('/password',{'current':'PetugasDemo!2026','password':'UpdatedSecret!2026'})[0],200)
        self.assertEqual(self.maker.call('/logout',{})[0],200)
        self.assertEqual(self.maker.call('/documents')[0],401)
        client=Client(self.url)
        for _ in range(10):
            self.assertEqual(client.call('/login',{'email':'wrong@example.com','password':'wrong'})[0],401)
        self.assertEqual(client.call('/login',{'email':'wrong@example.com','password':'wrong'})[0],429)

if __name__=='__main__':
    unittest.main(verbosity=2)
