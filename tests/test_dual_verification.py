"""Two independent recipients must both approve the same frozen submission."""
import concurrent.futures
import json
import re
import time
import unittest
import test_app as workflow
Client, app, DESTINATION, FILE = workflow.Client, workflow.app, workflow.DESTINATION, workflow.FILE


class DualVerificationTests(unittest.TestCase):
    setUp = workflow.WorkflowTests.setUp
    tearDown = workflow.WorkflowTests.tearDown
    boh_client = workflow.WorkflowTests.boh_client
    customer_edit = workflow.WorkflowTests.customer_edit
    create = workflow.WorkflowTests.create
    respond = workflow.WorkflowTests.respond

    def dual_customer(self, **changes):
        payload = dict(cif='2223334', name='PT Dua Verifikator', account='000123456789012', person='Direktur', email='direktur@example.test', phone='081234567890', verification_count=2, verifier_name='Adi Utama', second_name='Maya Putri', second_person='Komisaris', second_email='komisaris@example.test', second_phone='081234567891')
        payload.update(changes)
        status, result, _ = self.sol.call('/customers', payload)
        self.assertEqual(status, 201, result)
        saved = next(c for c in self.sol.call('/customers')[1]['customers'] if c['cif']==payload['cif'])
        self.assertEqual(saved['second_phone'], payload['second_phone'])
        return payload

    def dual_document(self, cif='2223334', channel='email'):
        status, result, _ = self.maker.call('/documents', {**DESTINATION, 'cif': cif, 'kind': 'Standing Instruction', 'nominal': 123456, 'file': FILE, 'channel': channel})
        self.assertEqual(status, 201, result)
        return result['id']

    def links(self, doc):
        with app.database() as db:
            rows = db.execute('SELECT recipient,body FROM outbox WHERE doc_id=? AND version=(SELECT version FROM documents WHERE id=?) ORDER BY recipient', (doc, doc)).fetchall()
        return {r['recipient']: re.search(r'/#confirm/([A-Za-z0-9_-]+)', r['body'])[1] for r in rows}

    def detail(self, doc):
        return self.maker.call('/documents/' + doc)[1]['document']

    def review(self, doc, **changes):
        return self.sol.call('/documents/' + doc + '/review', {'version': self.detail(doc)['version'], 'decision': 'approved', **changes})

    def test_two_private_emails_and_two_approvals_gate_sol(self):
        self.dual_customer(); doc = self.dual_document(); links = self.links(doc)
        self.assertEqual(set(links), {'direktur@example.test', 'komisaris@example.test'})
        self.assertEqual(len(set(links.values())), 2)
        for email, token in links.items():
            status, portal, _ = self.customer.call('/portal', {'token': token})
            self.assertEqual(status, 200, portal)
            self.assertEqual(portal['verification_required'], 2)
            self.assertNotIn('email', portal['verifier'])
            self.assertNotIn('token_hash', json.dumps(portal))
            self.assertEqual(self.customer.call('/portal/file', {'token': token})[0], 200)
        with app.database() as db:
            rows = db.execute('SELECT * FROM outbox WHERE doc_id=?', (doc,)).fetchall()
            for row in rows:
                expected = 'Adi Utama' if row['recipient'].startswith('direktur') else 'Maya Putri'
                self.assertIn(expected, row['body'])
                message, _ = app.build_confirmation_email(row)
                self.assertEqual(message['To'], row['recipient'])
                self.assertIn(links[row['recipient']], message.get_body(preferencelist=('html',)).get_content())
        self.assertEqual(self.review(doc)[0], 409)
        first = self.respond(links['direktur@example.test'])
        self.assertEqual(first[0], 200, first[1])
        self.assertEqual(first[1]['customer_status'], 'pending')
        detail = self.detail(doc)
        self.assertEqual(detail['verification']['confirmed'], 1)
        self.assertEqual(detail['verification']['verifiers'][0]['phone'], '081234567890')
        self.assertEqual(detail['verification']['verifiers'][1]['phone'], '081234567891')
        self.assertEqual(detail['customer_status'], 'pending')
        self.assertEqual(self.review(doc)[0], 409)
        self.assertEqual(self.review(doc, decision='rejected', notes='Terlalu awal')[0], 409)
        self.assertEqual(self.respond(links['direktur@example.test'])[0], 410)
        self.assertEqual(self.respond(links['komisaris@example.test'])[1]['customer_status'], 'confirmed')
        self.assertEqual(self.detail(doc)['verification']['confirmed'], 2)
        self.assertEqual(self.review(doc)[0], 200)
        self.assertNotIn('token_hash', json.dumps(self.detail(doc)))

    def test_either_verifier_rejection_ends_submission(self):
        self.dual_customer()
        for rejected_email in ('direktur@example.test', 'komisaris@example.test'):
            with self.subTest(recipient=rejected_email):
                doc = self.dual_document(); links = self.links(doc)
                self.assertEqual(self.respond(links[rejected_email], 'rejected')[0], 200)
                self.assertEqual(self.detail(doc)['customer_status'], 'rejected')
                other = next(t for e,t in links.items() if e != rejected_email)
                self.assertEqual(self.respond(other)[0], 410)
                self.assertEqual(self.review(doc)[0], 409)
                with app.database() as db:
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM outbox WHERE doc_id=? AND status='queued'", (doc,)).fetchone()[0], 0)

    def test_resend_preserves_first_approval_and_only_emails_pending_recipient(self):
        self.dual_customer(); doc = self.dual_document(); original = self.links(doc)
        self.assertEqual(self.respond(original['direktur@example.test'])[0], 200)
        self.assertEqual(self.maker.call('/documents/'+doc+'/resend', {'version': 1, 'channel':'email'})[0], 429)
        with app.database(True) as db:
            db.execute('UPDATE versions SET expires=? WHERE doc_id=?', (time.time()-1, doc))
            db.execute("UPDATE customers SET second_email='changed@example.test',second_phone='089999999999',verification_count=1 WHERE cif='2223334'")
        status, result, _ = self.maker.call('/documents/'+doc+'/resend', {'version':1, 'channel':'email'})
        self.assertEqual(status, 200, result)
        fresh = self.links(doc)
        self.assertEqual(set(fresh), {'komisaris@example.test'})
        self.assertNotEqual(fresh['komisaris@example.test'], original['komisaris@example.test'])
        self.assertEqual(self.respond(original['komisaris@example.test'])[0], 410)
        self.assertEqual(self.detail(doc)['verification']['confirmed'], 1)
        self.assertEqual(self.detail(doc)['verification']['verifiers'][1]['phone'], '081234567891')
        self.assertEqual(self.respond(fresh['komisaris@example.test'])[1]['customer_status'], 'confirmed')
        self.assertEqual(self.review(doc)[0], 200)

    def test_validation_channels_and_no_new_access(self):
        base = self.dual_customer()
        for changes in ({'verification_count':3}, {'verification_count':'2'}, {'second_email':base['email']}, {'second_email':'INVALID'}, {'second_name':''}, {'verifier_name':''}, {'second_person':''}, {'second_phone':''}, {'second_phone':'abc'}):
            status, _, _ = self.sol.call('/customers', {**base, 'cif':'9998887', **changes})
            self.assertEqual(status, 400, changes)
        for channel in ('whatsapp','both'):
            status, _, _ = self.maker.call('/documents', {**DESTINATION,'cif':base['cif'],'kind':'Standing Instruction','nominal':1,'file':FILE,'channel':channel})
            self.assertEqual(status, 400)
        doc = self.dual_document(); links = self.links(doc)
        self.assertEqual(self.maker.call('/documents/'+doc+'/whatsapp-preview')[0], 409)
        self.assertEqual(self.respond('not-a-real-verifier-token-value')[0], 404)
        token = links[base['email']]
        self.assertEqual(self.customer.call('/portal/decision', {'token':token,'decision':'confirmed','acknowledged':False})[0], 400)
        self.assertEqual(self.detail(doc)['verification']['confirmed'], 0)
        self.assertEqual(self.customer.call('/documents/'+doc)[0], 401)

    def test_customer_change_still_requires_amol_and_does_not_change_existing_documents(self):
        reviewer = self.sol; original = self.create()
        payload = self.customer_edit(verification_count=2, verifier_name='Budi', second_name='Dewi', second_person='Komisaris', second_email='dewi@example.test', second_phone='081234567891')
        status, result, _ = self.checker.call('/customers/1234567/edit-requests', payload)
        self.assertEqual(status, 201, result)
        self.assertEqual(self.detail(original)['verification']['required'], 1)
        self.assertEqual(next(c for c in self.maker.call('/customers')[1]['customers'] if c['cif']=='1234567')['verification_count'], 1)
        self.assertEqual(reviewer.call('/customer-edit-requests/'+result['id']+'/review', {'decision':'approved'})[0], 200)
        fresh = self.create()
        self.assertEqual(self.detail(fresh)['verification']['required'], 2)
        self.assertEqual(self.detail(original)['verification']['required'], 1)
        app.initialize()
        self.assertEqual(self.detail(fresh)['verification']['required'], 2)

    def test_concurrent_approvals_record_exactly_once_per_recipient(self):
        self.dual_customer(); doc = self.dual_document(); tokens = list(self.links(doc).values())
        def decide(token):
            return Client(self.url).call('/portal/decision', {'token':token,'decision':'confirmed','acknowledged':True})[0]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(decide, tokens)), [200,200])
        self.assertEqual(self.detail(doc)['customer_status'], 'confirmed')
        self.assertEqual(self.detail(doc)['verification']['confirmed'], 2)
        self.assertEqual(self.respond(tokens[0])[0], 410)

    def test_partial_approval_then_rejection_stops_the_flow(self):
        self.dual_customer(); doc = self.dual_document(); links = self.links(doc)
        self.assertEqual(self.respond(links['direktur@example.test'])[0], 200)
        self.assertEqual(self.respond(links['komisaris@example.test'], 'rejected')[0], 200)
        detail = self.detail(doc)
        self.assertEqual(detail['customer_status'], 'rejected')
        self.assertEqual(detail['verification']['confirmed'], 1)
        self.assertEqual(self.review(doc)[0], 409)
        self.assertEqual(self.maker.call('/documents/'+doc+'/resend', {'version':1, 'channel':'email'})[0], 409)

    def test_email_worker_skips_used_recipient_but_delivers_other_pending_recipient(self):
        self.dual_customer(); doc = self.dual_document(); links = self.links(doc)
        self.assertEqual(self.respond(links['direktur@example.test'])[0], 200)
        while app.deliver_one():
            pass
        with app.database() as db:
            statuses = dict(db.execute('SELECT recipient,status FROM outbox WHERE doc_id=?', (doc,)))
        self.assertEqual(statuses['direktur@example.test'], 'cancelled')
        self.assertEqual(statuses['komisaris@example.test'], 'local')
        self.assertTrue(self.detail(doc)['delivery']['email_requested'])
        self.assertEqual(self.detail(doc)['mail']['status'], 'local')
        self.assertEqual(self.respond(links['komisaris@example.test'])[0], 200)

    def test_execution_pdf_records_both_verifiers_after_resend(self):
        self.dual_customer()
        stream = workflow.BytesIO(); pdf = workflow.canvas.Canvas(stream); pdf.drawString(72,720,'Dokumen lokal'); pdf.save()
        import base64
        upload = {'name':'contoh.pdf','base64':base64.b64encode(stream.getvalue()).decode()}
        status, result, _ = self.maker.call('/documents', {**DESTINATION,'cif':'2223334','kind':'Standing Instruction','nominal':1,'file':upload})
        self.assertEqual(status, 201, result); doc = result['id']; links = self.links(doc)
        self.assertEqual(self.maker.call('/documents/'+doc+'/execution-pdf')[0], 409)
        self.respond(links['direktur@example.test'])
        with app.database(True) as db: db.execute('UPDATE versions SET expires=0 WHERE doc_id=?', (doc,))
        self.assertEqual(self.maker.call('/documents/'+doc+'/resend', {'version':1,'channel':'email'})[0], 200)
        self.respond(self.links(doc)['komisaris@example.test'])
        self.assertEqual(self.review(doc)[0], 200)
        status, report, _ = self.maker.call('/documents/'+doc+'/execution-pdf')
        self.assertEqual(status, 200)
        text = '\n'.join(page.extract_text() for page in workflow.PdfReader(workflow.BytesIO(report)).pages)
        for value in ('Adi Utama','Maya Putri','Verifikator 1','Verifikator 2','direktur@example.test','komisaris@example.test'):
            self.assertIn(value, text)
