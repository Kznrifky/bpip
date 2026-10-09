"""Integration checks against an actual HTTP server and temporary SQLite DB."""
import base64
from io import BytesIO
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
from unittest.mock import patch
from pypdf import PdfReader
from reportlab.pdfgen import canvas
from PIL import Image

spec = importlib.util.spec_from_file_location('bpip', Path(__file__).resolve().parents[1] / 'server.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)
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

class WorkflowTests(unittest.TestCase):
    def test_execution_pdf_approval_access_and_original_appendix(self):
        original=BytesIO()
        sheet=canvas.Canvas(original)
        sheet.drawString(50,750,'ORIGINAL SI TEST DOCUMENT')
        sheet.showPage();sheet.save()
        upload={'name':'si-original.pdf','base64':base64.b64encode(original.getvalue()).decode()}
        payload={'cif':'1234567','kind':'Standing Instruction','nominal':250000000,'description':'Pembayaran vendor','file':upload}
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
        for expected in ['SURAT KONFIRMASI PELAKSANAAN','RIWAYAT PERNYATAAN','LOG AKTIVITAS','ORIGINAL SI TEST DOCUMENT','SOL menyetujui pengajuan','Nasabah menyetujui surat','Rp 250.000.000','Rina Wulandari','Bambang Haryanto','Budi Santoso']:
            self.assertIn(expected,text)
        self.assertEqual(reader.attachments['si-original.pdf'][0],original.getvalue())
        self.assertNotIn(self.token(doc),text)
        self.assertEqual(self.sol.call(route)[0],200)
        app.create_user('observer@example.test','BOH','boh','ObserverTest!2026')
        boh=Client(self.url);boh.call('/login',{'email':'observer@example.test','password':'ObserverTest!2026'})
        self.assertEqual(boh.call(route)[0],403)
        app.create_user('other@example.test','Other Maker','petugas','OtherMaker!2026')
        other=Client(self.url);other.call('/login',{'email':'other@example.test','password':'OtherMaker!2026'})
        self.assertEqual(other.call(route)[0],403)
        self.sol.call('/documents/'+doc+'/archive',{'version':1,'password':'SolDemo!2026'})
        self.assertEqual(self.sol.call(route)[0],404)

    def test_execution_pdf_images_and_unreadable_original(self):
        image=BytesIO();Image.new('RGB',(800,1200),'white').save(image,format='PNG')
        payload={'cif':'1234567','kind':'Standing Instruction','nominal':1,'file':{'name':'si.png','base64':base64.b64encode(image.getvalue()).decode()}}
        doc=self.maker.call('/documents',payload)[1]['id']
        self.respond(self.token(doc));self.sol.call('/documents/'+doc+'/review',{'version':1,'decision':'approved','notes':''})
        status,body,_=self.sol.call('/documents/'+doc+'/execution-pdf')
        self.assertEqual(status,200)
        reader=PdfReader(BytesIO(body))
        self.assertEqual(len(reader.pages),3)
        self.assertEqual(reader.attachments['si.png'][0],image.getvalue())
        malformed=self.create();self.respond(self.token(malformed));self.sol.call('/documents/'+malformed+'/review',{'version':1,'decision':'approved','notes':''})
        self.assertEqual(self.sol.call('/documents/'+malformed+'/execution-pdf')[0],422)

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
        self.maker=Client(self.url);self.maker.login('petugas')
        self.sol=Client(self.url);self.sol.login('sol')
        self.customer=Client(self.url)
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
        self.temp.cleanup()
    def create(self, client=None):
        status,result,_=(client or self.maker).call('/documents',{'cif':'1234567','kind':'Standing Instruction','nominal':250000000,'description':'Pembayaran vendor','file':FILE})
        self.assertEqual(status,201,result)
        return result['id']
    def token(self, doc_id):
        with app.database() as db:
            row=db.execute('SELECT body FROM outbox WHERE doc_id=? ORDER BY version DESC LIMIT 1',(doc_id,)).fetchone()
        return row['body'].split('/#confirm/')[1].split()[0]
    def respond(self, token, decision='confirmed'):
        return self.customer.call('/portal/decision',{'token':token,'decision':decision,'notes':'Tidak sesuai' if decision=='rejected' else '', 'acknowledged':True})
    def test_full_revision_and_approval_flow(self):
        doc_id=self.create();token1=self.token(doc_id)
        # Opening portal has no consent side effects.
        for _ in range(2):
            status,result,_=self.customer.call('/portal',{'token':token1})
            self.assertEqual(status,200)
            self.assertEqual(result['document']['nominal'],250000000)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':1,'decision':'approved','notes':''})[0],409)
        self.assertEqual(self.respond(token1)[0],200)
        self.assertEqual(self.respond(token1)[0],410)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':1,'decision':'revision_requested','notes':'Perbaiki tanggal surat'})[0],200)
        revision={'version':1,'kind':'Standing Instruction','nominal':260000000,'description':'Nominal diperbaiki','notes':'Tanggal diperbaiki','file':FILE}
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/revise',revision)[0],200)
        token2=self.token(doc_id)
        self.assertNotEqual(token1,token2)
        self.assertEqual(self.customer.call('/portal',{'token':token1})[0],410)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':1,'decision':'approved','notes':''})[0],409)
        self.assertEqual(self.respond(token2)[0],200)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':2,'decision':'approved','notes':'Surat sesuai'})[0],200)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':2,'decision':'rejected','notes':'Ubah keputusan'})[0],409)
        status,result,_=self.maker.call('/documents/'+doc_id)
        d=result['document']
        self.assertEqual(d['sol_status'],'approved')
        self.assertEqual(len(d['versions']),2)
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/versions/1/file')[0],200)
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/versions/3/file')[0],404)
        self.assertTrue(any(a['action']=='SOL meminta revisi surat' for a in d['audit']))
        self.assertTrue(any(a['ip'] for a in d['audit']))
        self.assertEqual(self.customer.call('/documents')[0],401)
    def test_rejected_customer_cannot_be_approved(self):
        doc_id=self.create()
        self.assertEqual(self.respond(self.token(doc_id),'rejected')[0],200)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':1,'decision':'approved','notes':''})[0],409)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':1,'decision':'rejected','notes':''})[0],400)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':1,'decision':'rejected','notes':'Nasabah menolak surat'})[0],200)
    def test_roles_csrf_and_ownership(self):
        doc_id=self.create()
        self.assertEqual(self.sol.call('/documents',{'cif':'1234567','kind':'Warkat','nominal':1,'file':FILE})[0],403)
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/review',{'version':1,'decision':'approved'})[0],403)
        self.assertEqual(self.maker.call('/customers',{'cif':'888','name':'PT Baru','account':'000123456789012','person':'Ani','email':'ani@example.com'},csrf=False)[0],403)
        self.assertEqual(self.maker.call('/logout',{},origin='https://evil.example')[0],403)
        app.create_user('other@example.com','Other maker','petugas','OtherSecret!2026')
        other=Client(self.url)
        status,res,_=other.call('/login',{'email':'other@example.com','password':'OtherSecret!2026'})
        other.csrf=res['csrf']
        self.assertEqual(other.call('/documents/'+doc_id)[0],403)
        self.assertEqual(other.call('/documents/'+doc_id+'/file')[0],403)
        self.assertEqual(other.call('/documents')[1]['documents'],[])
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
        self.assertEqual(self.maker.call('/documents',{'cif':'888','kind':'Warkat','nominal':100,'file':FILE})[0],201)
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
        self.assertEqual(self.sol.call('/customers/887/phone',{'phone':'short'})[0],400)
        self.assertEqual(stored_phone(), '081234567890')
        self.assertEqual(self.sol.call('/customers/887/phone',{'phone':'+62 812-3456-7890'})[0],200)
        self.assertEqual(stored_phone(), '+6281234567890')
        self.assertEqual(self.sol.call('/customers/887/phone',{'phone':''})[0],400)
        self.assertEqual(stored_phone(), '+6281234567890')
        self.assertEqual(self.sol.call('/customers/999999/phone',{'phone':'081234567890'})[0],404)
    def test_cancel_preserves_history_and_invalidates_customer_link(self):
        doc_id=self.create();token=self.token(doc_id)
        payload={'version':1,'notes':'Transaksi tidak dilanjutkan'}
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/cancel',payload)[0],403)
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/cancel',{'version':1,'notes':''})[0],400)
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/cancel',{'version':2,'notes':'Uji'})[0],409)
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/cancel',payload)[0],200)
        self.assertEqual(self.customer.call('/portal',{'token':token})[0],410)
        self.assertEqual(self.respond(token)[0],410)
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/resend',{'version':1})[0],409)
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/revise',{'version':1})[0],409)
        d=self.maker.call('/documents/'+doc_id)[1]['document']
        self.assertEqual(d['sol_status'],'cancelled')
        self.assertEqual(len(d['versions']),1)
        self.assertTrue(any(a['notes']==payload['notes'] for a in d['audit']))
        self.assertFalse(app.deliver_one())
    def test_final_sol_decision_cannot_be_cancelled(self):
        doc_id=self.create();self.respond(self.token(doc_id))
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':1,'decision':'approved','notes':''})[0],200)
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/cancel',{'version':1,'notes':'Uji'})[0],409)
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
        self.assertTrue(any(a['action']=='SOL memulihkan pengajuan' for a in d['audit']))
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
        self.assertEqual(self.maker.call('/documents',{'cif':'1234567','kind':'Warkat','nominal':10,'file':FILE})[0],409)
        self.assertEqual(self.maker.call('/documents/'+doc_id)[1]['document']['customer_name'],'PT Maju Bersama')
        self.assertEqual(self.respond(self.token(doc_id))[0],200)
        self.assertEqual(self.sol.call('/documents/'+doc_id+'/review',{'version':1,'decision':'revision_requested','notes':'Perbaiki surat'})[0],200)
        self.assertEqual(self.maker.call('/documents/'+doc_id+'/revise',{'version':1,'kind':'Warkat','nominal':10,'file':FILE,'notes':'Diperbaiki'})[0],200)
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
    def test_boh_dashboard_only_and_password_lockout(self):
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
        for path in ['/customers','/outbox','/documents/'+doc,'/documents/'+doc+'/file','/customers/archived']:
            self.assertEqual(boh.call(path)[0],403)
        for path,payload in [('/customers',{}),('/documents',{}),('/documents/'+doc+'/review',{}),('/customers/1234567/archive',{}),('/users/boh',account)]:
            self.assertEqual(boh.call(path,payload)[0],403)
        for _ in range(5):
            self.assertEqual(self.sol.call('/customers/1234567/archive',{'password':'wrong'})[0],403)
        self.assertEqual(self.sol.call('/customers/1234567/archive',{'password':'SolDemo!2026'})[0],429)
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
            status,_,_=self.maker.call('/documents',{'cif':'1234567','kind':'Warkat','nominal':invalid,'file':FILE})
            self.assertEqual(status,400)
        bad_file={'name':'payload.html','base64':base64.b64encode(b'<script>alert(1)</script>').decode()}
        self.assertEqual(self.maker.call('/documents',{'cif':'1234567','kind':'Warkat','nominal':100,'file':bad_file})[0],400)
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
        row['body']='Yth. <script>alert(1)</script>,\n\n'+app.BASE_URL+'/#confirm/test_token\n\nJangan bagikan tautan ini.'
        with patch.dict(os.environ,{'SMTP_HOST':'smtp.gmail.com','SMTP_USER':'sender@gmail.com','SMTP_FROM':'BPIP <other@example.com>'}):
            message,sender=app.build_confirmation_email(row)
        self.assertEqual(sender,'sender@gmail.com')
        self.assertEqual(app.parseaddr(message['From'])[1],sender)
        self.assertEqual(app.parseaddr(message['Reply-To'])[1],sender)
        self.assertIsNotNone(message['Date'])
        self.assertEqual(message['Message-ID'],f"<{row['id']}@gmail.com>")
        self.assertEqual(message.get_content_type(),'multipart/alternative')
        self.assertEqual(message.get_body(preferencelist=('plain',)).get_content(),row['body']+'\n')
        html_body=message.get_body(preferencelist=('html',)).get_content()
        self.assertIn('href="'+app.BASE_URL+'/#confirm/test_token"',html_body)
        self.assertNotIn('<script>',html_body)
        self.assertIn('&lt;script&gt;',html_body)
        self.assertNotIn('DKIM-Signature',message)
        self.assertIn('BRI VISTA',html_body)
        self.assertIn('Verification, Integration &amp; Secure Tracking Application',html_body)
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
