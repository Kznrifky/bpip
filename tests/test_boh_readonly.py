"""BOH can track and inspect submissions but cannot change business data."""
import unittest
import test_app as workflow

app, Client = workflow.app, workflow.Client


class BOHReadOnlyTests(unittest.TestCase):
    setUp = workflow.WorkflowTests.setUp
    tearDown = workflow.WorkflowTests.tearDown
    create = workflow.WorkflowTests.create
    customer_edit = workflow.WorkflowTests.customer_edit
    boh_client = workflow.WorkflowTests.boh_client

    def test_tracking_history_and_original_letters_remain_readable(self):
        pending, complete = self.create(), self.create()
        with app.database(True) as db:
            db.execute("UPDATE documents SET customer_status='confirmed',sol_status='approved' WHERE id=?", (complete,))
        boh = self.boh_client()
        status, result, _ = boh.call('/documents')
        self.assertEqual(status, 200)
        self.assertEqual({row['id'] for row in result['documents']}, {pending, complete})
        for row in result['documents']:
            self.assertTrue({'customer_status', 'checker_status', 'sol_status', 'review_flow'} <= row.keys())
        for doc in (pending, complete):
            status, detail, _ = boh.call('/documents/' + doc)
            self.assertEqual(status, 200)
            self.assertTrue(detail['document']['audit'])
            self.assertEqual(detail['document']['file']['filename'], 'surat.pdf')
            for endpoint in ('/file', '/versions/1/file'):
                status, content, _ = boh.call('/documents/' + doc + endpoint)
                self.assertEqual(status, 200)
                self.assertTrue(content.startswith(b'%PDF-'))
        for endpoint in ('/customers', '/customer-edit-requests', '/outbox', '/customers/archived', '/documents/archived', '/documents/' + complete + '/execution-pdf'):
            self.assertEqual(boh.call(endpoint)[0], 403, endpoint)

    def test_all_business_writes_including_customer_approval_are_denied(self):
        doc = self.create()
        request_id = self.checker.call('/customers/1234567/edit-requests', self.customer_edit())[1]['id']
        boh = self.boh_client()
        with app.database() as db:
            before = {table: [tuple(row) for row in db.execute('SELECT * FROM ' + table)] for table in ('documents', 'customers', 'customer_edit_requests', 'audit', 'management_audit', 'outbox')}
        attempts = [('/documents/' + doc + '/' + action, {'version': 1, 'decision': decision, 'notes': 'BOH must not decide'})
                    for action in ('review', 'checker-review', 'send-confirmation', 'resend', 'revise', 'cancel', 'archive', 'restore', 'purge')
                    for decision in ('approved', 'rejected')]
        attempts += [('/customer-edit-requests/' + request_id + '/review', {'decision': decision, 'notes': 'Forbidden'}) for decision in ('approved', 'rejected')]
        attempts += [('/customer-create-requests', {}), ('/customers', {}), ('/documents', {}), ('/customers/1234567/edit-requests', self.customer_edit()),
                     ('/customers/1234567/phone', {'phone': '081234567899'}), ('/customers/delete-selected', {'cifs': ['1234567']}),
                     ('/documents/archive-selected', {'documents': [{'id': doc, 'version': 1}]})]
        for endpoint, payload in attempts:
            self.assertEqual(boh.call(endpoint, payload)[0], 403, endpoint)
        with app.database() as db:
            after = {table: [tuple(row) for row in db.execute('SELECT * FROM ' + table)] for table in before}
        self.assertEqual(before, after)

    def test_self_password_and_logout_remain_available(self):
        boh = self.boh_client()
        self.assertEqual(boh.call('/password', {'current': 'BohApproval!2026', 'password': 'BOHReadOnly!2026'}, csrf=False)[0], 403)
        self.assertEqual(boh.call('/password', {'current': 'BohApproval!2026', 'password': 'BOHReadOnly!2026'})[0], 200)
        self.assertEqual(boh.call('/logout', {})[0], 200)
        self.assertEqual(boh.call('/documents')[0], 401)
