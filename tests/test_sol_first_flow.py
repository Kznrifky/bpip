"""SOL releases customer links only after checking; AMOL remains the final approver."""
import concurrent.futures
from io import BytesIO
import base64
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from reportlab.pdfgen import canvas
from pypdf import PdfReader
import test_app as workflow

app, Client = workflow.app, workflow.Client


class SolFirstFlowTests(unittest.TestCase):
    tearDown = workflow.WorkflowTests.tearDown

    def setUp(self):
        workflow.WorkflowTests.setUp(self)
        self.maker = Client(self.url)
        self.maker.login('petugas')
        self.choices={}
        with app.database(True) as db:
            db.execute("UPDATE customers SET phone='081234567890' WHERE cif='1234567'")

    def create(self, channel='email', dual=False, real_pdf=False):
        if dual:
            with app.database(True) as db:
                db.execute("UPDATE customers SET verification_count=2,verifier_name='Direktur Satu',second_name='Direktur Dua',second_person='Komisaris',second_email='second@example.test',second_phone='081234567891' WHERE cif='1234567'")
        file = workflow.FILE
        if real_pdf:
            stream = BytesIO(); sheet = canvas.Canvas(stream)
            sheet.drawString(50, 750, 'ORIGINAL SOL FIRST'); sheet.save()
            file = {'name': 'original.pdf', 'base64': base64.b64encode(stream.getvalue()).decode()}
        status, result, _ = self.maker.call('/documents', {**workflow.DESTINATION, 'cif': '1234567', 'kind': 'Standing Instruction', 'nominal': 250000, 'file': file})
        self.assertEqual(status, 201, result)
        self.assertIsNone(result['whatsapp'])
        self.choices[result['id']]=channel
        return result['id']

    def detail(self, doc):
        return self.maker.call('/documents/' + doc)[1]['document']

    def review(self, doc, client=None, decision='approved', version=1):
        client = client or self.checker
        return client.call('/documents/' + doc + ('/review' if client is self.sol else '/checker-review'), {'version': version, 'decision': decision, 'notes': 'Data tidak sesuai' if decision == 'rejected' else ''})

    def send(self, doc, client=None, channel=None):
        return (client or self.checker).call('/documents/'+doc+'/send-confirmation', {'version':self.detail(doc)['version'],'channel':channel or self.choices[doc]})

    def approve_and_send(self, doc):
        self.assertEqual(self.review(doc)[0],200)
        return self.send(doc)

    def tokens(self, doc):
        with app.database() as db:
            rows = db.execute('SELECT body FROM outbox WHERE doc_id=? AND version=(SELECT version FROM documents WHERE id=?) ORDER BY recipient', (doc, doc)).fetchall()
        return [row['body'].split('/#confirm/')[1].split()[0] for row in rows]

    def respond(self, token, decision='confirmed'):
        return Client(self.url).call('/portal/decision', {'token': token, 'decision': decision, 'acknowledged': True, 'notes': 'Tidak sesuai' if decision == 'rejected' else ''})

    def test_sol_then_customer_then_amol_for_one_or_two_verifiers(self):
        for dual in (False, True):
            with self.subTest(dual=dual):
                doc = self.create(dual=dual)
                detail = self.detail(doc)
                self.assertEqual(detail['review_flow'], 3)
                self.assertEqual(detail['verification']['required'], 2 if dual else 1)
                self.assertEqual(self.tokens(doc), [])
                self.assertEqual(detail['file']['expires'], 0)
                with app.database() as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM outbox WHERE doc_id=?', (doc,)).fetchone()[0], 0)
                self.assertEqual(self.review(doc, self.sol)[0], 409)
                self.assertEqual(self.maker.call('/documents/' + doc + '/resend', {'version': 1})[0], 409)
                self.assertEqual(self.maker.call('/documents/' + doc + '/send-confirmation', {'version': 1, 'channel': 'email'})[0], 403)
                self.assertEqual(self.review(doc)[0], 200)
                self.assertEqual(self.tokens(doc),[])
                self.assertEqual(self.detail(doc)['delivery_channel'],'')
                self.assertEqual(self.send(doc)[0],200)
                tokens = self.tokens(doc)
                self.assertEqual(len(tokens), 2 if dual else 1)
                self.assertAlmostEqual(self.detail(doc)['file']['expires'] - time.time(), 300, delta=3)
                self.assertEqual(self.review(doc, self.sol)[0], 409)
                for index, token in enumerate(tokens):
                    self.assertEqual(self.respond(token)[0], 200)
                    if index == 0 and dual:
                        self.assertEqual(self.review(doc, self.sol)[0], 409)
                self.assertEqual(self.review(doc, self.sol)[0], 200)
                self.assertEqual(self.review(doc)[0], 409)

    def test_rejection_at_each_stage_stops_the_flow(self):
        for stage in ('SOL', 'nasabah', 'AMOL'):
            with self.subTest(stage=stage):
                doc = self.create()
                self.assertEqual((self.review(doc, decision='rejected') if stage=='SOL' else self.approve_and_send(doc))[0], 200)
                if stage == 'SOL':
                    self.assertEqual(self.tokens(doc), [])
                    self.assertFalse(app.deliver_one())
                else:
                    self.assertEqual(self.respond(self.tokens(doc)[0], 'rejected' if stage == 'nasabah' else 'confirmed')[0], 200)
                    if stage == 'AMOL':
                        self.assertEqual(self.review(doc, self.sol, 'rejected')[0], 200)
                self.assertEqual(self.maker.call('/documents/' + doc + '/execution-pdf')[0], 409)
                self.assertEqual(self.maker.call('/documents/' + doc + '/resend', {'version': 1})[0], 409)

    def test_link_clock_starts_at_sol_delivery_and_opening_does_not_extend_it(self):
        doc = self.create()
        future = time.time() + 1800
        with patch.object(app.time, 'time', return_value=future):
            self.assertEqual(self.review(doc)[0], 200)
        self.assertEqual(self.detail(doc)['file']['expires'],0)
        with patch.object(app.time,'time',return_value=future+60):
            self.assertEqual(self.send(doc)[0],200)
        expiry = self.detail(doc)['file']['expires']
        self.assertEqual(expiry, future + 60 + 300)
        token = self.tokens(doc)[0]
        with patch.object(app.time, 'time', return_value=expiry - 1):
            self.assertEqual(Client(self.url).call('/portal', {'token': token})[0], 200)
        self.assertEqual(self.detail(doc)['file']['expires'], expiry)
        with patch.object(app.time, 'time', return_value=expiry):
            for endpoint, payload in (('/portal', {'token': token}), ('/portal/file', {'token': token}), ('/portal/decision', {'token': token, 'decision': 'confirmed', 'acknowledged': True})):
                self.assertEqual(Client(self.url).call(endpoint, payload)[0], 410)

    def test_manual_whatsapp_is_prepared_after_sol_and_has_private_links(self):
        for dual in (False, True):
            with self.subTest(dual=dual):
                doc = self.create('whatsapp', dual=dual)
                self.assertEqual(self.checker.call('/documents/' + doc + '/whatsapp-preview')[0], 409)
                self.assertEqual(self.review(doc)[0],200)
                self.assertEqual(self.tokens(doc),[])
                status, result, _ = self.send(doc)
                self.assertEqual(status, 200, result)
                previews = result['whatsapp'] if dual else [result['whatsapp']]
                self.assertEqual(len(previews), 2 if dual else 1)
                self.assertFalse(app.deliver_one())
                self.assertEqual({item['phone'] for item in previews}, {'6281234567890', '6281234567891'} if dual else {'6281234567890'})
                for item, token in zip(previews, self.tokens(doc)):
                    self.assertIn(token, item['message'])
                self.assertEqual(self.checker.call('/documents/' + doc + '/whatsapp-preview')[0], 200)
                self.assertEqual(self.sol.call('/documents/' + doc + '/whatsapp-preview')[0], 403)
                self.assertEqual(self.detail(doc)['delivery'], {'email_requested': False, 'whatsapp_prepared': True})

    def test_resend_keeps_sol_approval_and_only_reissues_unconfirmed_verifier(self):
        doc = self.create('whatsapp',dual=True, real_pdf=True); self.approve_and_send(doc)
        first, second = self.tokens(doc)
        self.assertEqual(self.respond(first)[0], 200)
        self.assertEqual(self.maker.call('/documents/' + doc + '/resend', {'version': 1, 'channel': 'whatsapp'})[0], 429)
        with app.database(True) as db:
            db.execute('UPDATE versions SET expires=0 WHERE doc_id=?', (doc,))
        status, result, _ = self.maker.call('/documents/' + doc + '/resend', {'version': 1, 'channel': 'whatsapp'})
        self.assertEqual(status, 200, result)
        self.assertEqual(len(result['whatsapp']), 1)
        detail = self.detail(doc)
        self.assertEqual(detail['checker_status'], 'approved')
        self.assertEqual(detail['verification']['confirmed'], 1)
        self.assertEqual(Client(self.url).call('/portal', {'token': second})[0], 410)
        self.assertAlmostEqual(detail['file']['expires'] - time.time(), 300, delta=3)
        self.assertEqual(self.respond(self.tokens(doc)[0])[0], 200)
        self.assertEqual(self.review(doc, self.sol, version=2)[0], 200)
        self.assertEqual(self.maker.call('/documents/' + doc + '/execution-pdf')[0], 200)

    def test_duplicate_sol_approvals_release_only_one_link(self):
        doc = self.create()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            statuses = list(pool.map(lambda _: self.review(doc)[0], range(2)))
        self.assertEqual(sorted(statuses), [200, 409])
        self.assertEqual(self.tokens(doc),[])
        with concurrent.futures.ThreadPoolExecutor() as pool:
            sends=list(pool.map(lambda _:self.send(doc)[0],range(2)))
        self.assertEqual(sorted(sends),[200,409])
        self.assertEqual(len(self.tokens(doc)),1)

    def test_old_hour_configuration_cannot_extend_the_five_minute_window(self):
        with patch.dict(app.os.environ, {'TOKEN_TTL_HOURS': '24'}):
            doc = self.create(); self.approve_and_send(doc)
        self.assertAlmostEqual(self.detail(doc)['file']['expires'] - time.time(), 300, delta=3)

    def test_both_channel_is_rejected_and_teller_cannot_bypass_sol(self):
        payload = {**workflow.DESTINATION, 'cif': '1234567', 'kind': 'Standing Instruction', 'nominal': 1, 'file': workflow.FILE}
        self.assertEqual(self.maker.call('/documents', {**payload, 'channel': 'both'})[0], 400)
        doc = self.create()
        self.assertEqual(self.maker.call('/documents/' + doc + '/checker-review', {'version': 1, 'decision': 'approved'})[0], 403)
        self.assertEqual(self.checker.call('/documents/' + doc + '/checker-review', {'version': 2, 'decision': 'approved'})[0], 409)
        self.assertEqual(self.approve_and_send(doc)[0],200)
        self.assertEqual(self.maker.call('/documents/' + doc + '/whatsapp-preview')[0],403)

    def test_only_sol_selects_initial_method_and_officer_resends_after_expiry(self):
        payload = {**workflow.DESTINATION, 'cif': '1234567', 'kind': 'Standing Instruction', 'nominal': 1, 'file': workflow.FILE}
        for channel in ('email','whatsapp','both'):
            self.assertEqual(self.maker.call('/documents',{**payload,'channel':channel})[0],400)
        doc=self.create('whatsapp')
        self.assertEqual(self.send(doc)[0],409)
        self.assertEqual(self.review(doc)[0],200)
        self.assertEqual(self.tokens(doc),[])
        self.assertEqual(self.detail(doc)['file']['expires'],0)
        self.assertEqual(self.send(doc,client=self.maker)[0],403)
        self.assertEqual(self.send(doc,client=self.sol)[0],403)
        route='/documents/'+doc+'/send-confirmation'
        self.assertEqual(self.checker.call(route,{'version':1,'channel':'email'},csrf=False)[0],403)
        self.assertEqual(self.checker.call(route,{'version':2,'channel':'email'})[0],409)
        self.assertEqual(self.checker.call(route,{'version':1,'channel':'both'})[0],400)
        self.assertEqual(self.detail(doc)['delivery_channel'],'')
        self.assertEqual(self.maker.call('/documents/'+doc+'/resend',{'version':1})[0],409)
        self.assertEqual(self.send(doc)[0],200)
        self.assertEqual(self.detail(doc)['delivery_channel'],'whatsapp')
        self.assertEqual(self.send(doc,channel='email')[0],409)
        self.assertEqual(self.maker.call('/documents/'+doc+'/whatsapp-preview')[0],403)
        self.assertEqual(self.maker.call('/documents/'+doc+'/resend',{'version':1})[0],429)
        with app.database(True) as db:db.execute('UPDATE versions SET expires=0 WHERE doc_id=?',(doc,))
        self.assertEqual(self.checker.call('/documents/'+doc+'/resend',{'version':1})[0],403)
        self.assertEqual(self.maker.call('/documents/'+doc+'/resend',{'version':1,'channel':'email'})[0],409)
        self.assertEqual(self.detail(doc)['version'],1)
        self.assertEqual(self.maker.call('/documents/'+doc+'/resend',{'version':1})[0],200)
        self.assertEqual(self.detail(doc)['delivery_channel'],'whatsapp')
        self.assertEqual(self.maker.call('/documents/'+doc+'/whatsapp-preview')[0],200)

    def test_pdf_and_audit_follow_sol_first_order(self):
        doc = self.create(dual=True, real_pdf=True); self.approve_and_send(doc)
        for token in self.tokens(doc): self.assertEqual(self.respond(token)[0], 200)
        self.assertEqual(self.review(doc, self.sol)[0], 200)
        status, pdf, _ = self.maker.call('/documents/' + doc + '/execution-pdf')
        self.assertEqual(status, 200)
        text = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
        approvals = text.split('RIWAYAT PERNYATAAN DAN PERSETUJUAN', 1)[1].split('LOG AKTIVITAS', 1)[0]
        self.assertLess(approvals.index('\nSOL\n'), approvals.index('Verifikator 1'))
        self.assertLess(approvals.index('Verifikator 2'), approvals.index('\nAMOL\n'))
        self.assertIn('ORIGINAL SOL FIRST', text)
        self.assertIn('Pembuat pengajuan: Rina Wulandari', text)
        self.assertNotIn('Pembuat pengajuan: SOL', text)
        Path('/private/tmp/bri-sol-first-flow.pdf').write_bytes(pdf)
