"""New submissions require distinct SOL checking and final AMOL approval."""
import concurrent.futures
from io import BytesIO
import base64
import json
import unittest
from pathlib import Path
from reportlab.pdfgen import canvas
from pypdf import PdfReader
import test_app as workflow

app,Client=workflow.app,workflow.Client

class CheckerFlowTests(unittest.TestCase):
    tearDown=workflow.WorkflowTests.tearDown
    def setUp(self):
        workflow.WorkflowTests.setUp(self)
        self.maker=Client(self.url);self.maker.login('petugas')
        app.create_user('checker@example.test','SOL Checker','checker','CheckerFlow!2026')
        self.checker=self.login('checker@example.test','CheckerFlow!2026')
    def login(self,email,password):
        client=Client(self.url);status,result,_=client.call('/login',{'email':email,'password':password})
        self.assertEqual(status,200,result);client.csrf=result['csrf'];return client
    def create(self,dual=False,real_pdf=False):
        cif='1234567'
        if dual:
            with app.database(True) as db:
                db.execute("UPDATE customers SET verification_count=2,verifier_name='First Director',phone='081234567890',second_name='Second Director',second_person='Director',second_email='second@example.test',second_phone='081234567891' WHERE cif=?",(cif,))
        file=workflow.FILE
        if real_pdf:
            stream=BytesIO();sheet=canvas.Canvas(stream);sheet.drawString(50,750,'ORIGINAL SI CHECKER FLOW');sheet.showPage();sheet.save()
            file={'name':'original.pdf','base64':base64.b64encode(stream.getvalue()).decode()}
        status,result,_=self.maker.call('/documents',{**workflow.DESTINATION,'cif':cif,'kind':'Standing Instruction','nominal':250000,'file':file})
        self.assertEqual(status,201,result)
        return result['id']
    def detail(self,doc):return self.maker.call('/documents/'+doc)[1]['document']
    def tokens(self,doc):
        with app.database() as db:
            rows=db.execute('SELECT body FROM outbox WHERE doc_id=? ORDER BY recipient',(doc,)).fetchall()
        return [row['body'].split('/#confirm/')[1].split()[0] for row in rows]
    def respond(self,token,decision='confirmed'):
        return Client(self.url).call('/portal/decision',{'token':token,'decision':decision,'acknowledged':True,'notes':'Tidak sesuai' if decision=='rejected' else ''})
    def review(self,doc,checker=False,decision='approved',**changes):
        return (self.checker if checker else self.sol).call('/documents/'+doc+('/checker-review' if checker else '/review'),{'version':1,'decision':decision,'notes':'Alasan penolakan' if decision=='rejected' else '',**changes})
    def confirm(self,doc):
        for token in self.tokens(doc):self.assertEqual(self.respond(token)[0],200)
    def test_single_verifier_sequence_and_no_final_approval_bypass(self):
        doc=self.create();self.assertEqual(self.detail(doc)['review_flow'],2)
        self.assertEqual(self.review(doc)[0],409);self.assertEqual(self.review(doc,checker=True)[0],409)
        self.confirm(doc)
        self.assertEqual(self.review(doc)[0],409)
        self.assertEqual(self.review(doc,checker=True)[0],200)
        checked=self.detail(doc)
        self.assertEqual(checked['checker_status'],'approved');self.assertEqual(checked['sol_status'],'pending')
        self.assertEqual(self.maker.call('/documents/'+doc+'/execution-pdf')[0],409)
        self.assertEqual(self.review(doc,checker=True)[0],409)
        self.assertEqual(self.review(doc)[0],200)
        self.assertEqual(self.review(doc,decision='rejected')[0],409)
        audit=self.detail(doc)['audit'];actions=[a['action'] for a in audit]
        self.assertIn('SOL menyetujui pengajuan',actions);self.assertIn('AMOL menyetujui pengajuan',actions)
        self.assertLess(actions.index('AMOL menyetujui pengajuan'),actions.index('SOL menyetujui pengajuan'))
    def test_two_verifiers_both_required_before_sol(self):
        doc=self.create(dual=True);first,second=self.tokens(doc)
        self.assertEqual(self.respond(first)[0],200)
        self.assertEqual(self.review(doc,checker=True)[0],409);self.assertEqual(self.review(doc)[0],409)
        self.assertEqual(self.respond(second)[0],200)
        self.assertEqual(self.review(doc,checker=True)[0],200);self.assertEqual(self.review(doc)[0],200)
    def test_rejections_stop_later_stages(self):
        for stage in ('customer','checker','amol'):
            with self.subTest(stage=stage):
                doc=self.create()
                if stage=='customer':
                    self.respond(self.tokens(doc)[0],'rejected')
                    self.assertEqual(self.review(doc,checker=True)[0],409)
                else:
                    self.confirm(doc)
                    self.assertEqual(self.review(doc,checker=True,decision='rejected' if stage=='checker' else 'approved')[0],200)
                    if stage=='amol':self.assertEqual(self.review(doc,decision='rejected')[0],200)
                self.assertEqual(self.review(doc)[0],409)
                self.assertEqual(self.maker.call('/documents/'+doc+'/execution-pdf')[0],409)
    def test_role_scope_and_csrf_stale_version_and_reason(self):
        doc=self.create();self.confirm(doc)
        self.assertEqual(self.sol.call('/documents/'+doc+'/checker-review',{'version':1,'decision':'approved'})[0],403)
        self.assertEqual(self.checker.call('/documents/'+doc+'/review',{'version':1,'decision':'approved'})[0],403)
        for endpoint in ('/outbox','/documents/archived','/customers/archived'):
            self.assertEqual(self.checker.call(endpoint)[0],403,endpoint)
        for endpoint in ('/customers','/customer-edit-requests'):
            self.assertEqual(self.checker.call(endpoint)[0],200,endpoint)
        self.assertEqual(self.checker.call('/customers',{})[0],403)
        self.assertEqual(self.checker.call('/documents/'+doc+'/checker-review',{'version':1,'decision':'approved'},csrf=False)[0],403)
        self.assertEqual(self.review(doc,checker=True,version=2)[0],409)
        self.assertEqual(self.review(doc,checker=True,decision='rejected',notes='')[0],400)
        self.assertEqual(self.review(doc,checker=True,decision='revision_requested')[0],400)
        self.assertEqual(self.detail(doc)['checker_status'],'pending')
    def test_concurrent_checker_decisions_commit_once(self):
        doc=self.create();self.confirm(doc)
        clients=[self.checker,self.login('checker@example.test','CheckerFlow!2026')]
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results=list(pool.map(lambda client:client.call('/documents/'+doc+'/checker-review',{'version':1,'decision':'approved'})[0],clients))
        self.assertEqual(sorted(results),[200,409])
        self.assertEqual(sum(a['action']=='SOL menyetujui pengajuan' for a in self.detail(doc)['audit']),1)
    def test_new_pdf_preserves_separate_sol_and_amol_approvals(self):
        doc=self.create(dual=True,real_pdf=True);self.confirm(doc);self.review(doc,checker=True);self.review(doc)
        status,pdf,_=self.maker.call('/documents/'+doc+'/execution-pdf');self.assertEqual(status,200)
        reader=PdfReader(BytesIO(pdf));text='\n'.join(page.extract_text() for page in reader.pages)
        for expected in ('SOL (Checker)','SOL menyetujui pengajuan','AMOL menyetujui pengajuan','SOL Checker','Bambang Haryanto','First Director','Second Director','ORIGINAL SI CHECKER FLOW'):
            self.assertIn(expected,text)
        approvals=text.split('RIWAYAT PERNYATAAN DAN PERSETUJUAN',1)[1].split('LOG AKTIVITAS',1)[0]
        self.assertIn('\nSOL\n',approvals);self.assertIn('\nAMOL\n',approvals)
        self.assertNotIn('SOL (SOL)',approvals);self.assertNotIn('AMOL (AMOL)',approvals)
        self.assertEqual(text.count('LOG AKTIVITAS'),1)
        self.assertNotIn('SOL (SOL)',text);self.assertNotIn('AMOL (AMOL)',text)
        self.assertEqual(text.count('Email diterima server SMTP'),1)
        self.assertIn('Pengiriman email konfirmasi (2 email)',text)
        self.assertNotIn(self.tokens(doc)[0],text)
        Path('/private/tmp/bri-sol-amol-flow.pdf').write_bytes(pdf)
    def test_migration_upgrades_active_records_but_keeps_legacy_completed_documents(self):
        doc=self.create();finished=self.create()
        with app.database(True) as db:
            db.execute("UPDATE documents SET sol_status='approved',customer_status='confirmed' WHERE id=?",(finished,))
            db.execute('UPDATE documents SET review_flow=1 WHERE id=?',(doc,))
            # Emulate the pre-checker schema and let startup migrate it.
            for column in ('review_flow','checker_status','checker_notes','checker_by','checker_at'):
                db.execute('ALTER TABLE documents DROP COLUMN '+column)
        app.initialize();self.assertEqual(self.detail(doc)['review_flow'],2)
        self.assertEqual(self.detail(finished)['review_flow'],1)
        self.assertEqual(self.detail(finished)['sol_status'],'approved')
        self.confirm(doc);self.assertEqual(self.review(doc)[0],409)

    def test_account_transition_preserves_existing_password_and_revokes_old_sessions(self):
        app.create_user('sol@example.test.migrate','SOL lama','sol','ExistingSol!2026')
        existing=self.login('sol@example.test.migrate','ExistingSol!2026')
        old_id=existing.call('/session')[1]['user']['id']
        accounts=app.configure_reviewers('sol@example.test.migrate','amol@example.test.migrate')
        self.assertFalse(accounts[0]['created']);self.assertNotIn('initial_password',accounts[0])
        self.assertEqual(existing.call('/session')[0],401)
        moved=self.login('sol@example.test.migrate','ExistingSol!2026')
        self.assertEqual(moved.call('/session')[1]['user']['id'],old_id)
        self.assertEqual(moved.call('/session')[1]['user']['role'],'checker')
        amol=self.login(accounts[1]['email'],accounts[1]['initial_password'])
        self.assertEqual(amol.call('/session')[1]['user']['role'],'sol')
        repeated=app.configure_reviewers('sol@example.test.migrate','amol@example.test.migrate')
        self.assertFalse(any(a['created'] or 'initial_password' in a for a in repeated))
        self.assertEqual(amol.call('/session')[0],200)
        with self.assertRaises(app.AppError):
            app.configure_reviewers('petugas@bpip.local','new@example.test')
        self.assertEqual(self.maker.call('/session')[0],200)
