"""SOL submits customer registrations; AMOL approval creates the master record."""
import concurrent.futures
import json
import unittest
import test_app as workflow

app, Client = workflow.app, workflow.Client


class CustomerCreationTests(unittest.TestCase):
    setUp = workflow.WorkflowTests.setUp
    tearDown = workflow.WorkflowTests.tearDown
    boh_client = workflow.WorkflowTests.boh_client
    customer_edit = workflow.WorkflowTests.customer_edit

    def payload(self, cif='772001', dual=False):
        data = {'cif': cif, 'name': 'PT Nasabah Baru', 'account': '000123456789012',
                'person': 'Direktur', 'email': 'pertama@example.test', 'phone': '081234567890', 'verification_count': 1}
        if dual:
            data.update(verification_count=2, verifier_name='Adi Contoh', second_name='Dewi Contoh',
                        second_person='Direktur Keuangan', second_email='kedua@example.test', second_phone='081234567891')
        return data

    def submit(self, data):
        status, result, _ = self.checker.call('/customer-create-requests', data)
        self.assertEqual(status, 201, result)
        return result['id']

    def review(self, request_id, decision='approved', client=None, **extra):
        return (client or self.sol).call('/customer-edit-requests/' + request_id + '/review', {'decision': decision, **extra})

    def customers(self):
        return self.maker.call('/customers')[1]['customers']

    def test_customer_becomes_usable_only_after_approval_for_one_or_two_verifiers(self):
        for dual in (False, True):
            with self.subTest(dual=dual):
                data = self.payload('772002' if dual else '772001', dual)
                request_id = self.submit(data)
                self.assertFalse(any(c['cif'] == data['cif'] for c in self.customers()))
                document = {**workflow.DESTINATION, 'cif': data['cif'], 'kind': 'Standing Instruction', 'nominal': 1000, 'file': workflow.FILE}
                self.assertEqual(self.maker.call('/documents', document)[0], 400)
                request = next(r for r in self.sol.call('/customer-edit-requests')[1]['requests'] if r['id'] == request_id)
                self.assertEqual(request['operation'], 'create');self.assertEqual(request['old_data'], {})
                self.assertEqual(request['new_data']['cif'], data['cif'])
                self.assertEqual(request['requested_by'], self.checker.call('/session')[1]['user']['id'])
                app.initialize()
                self.assertEqual(self.review(request_id)[0], 200)
                customer = next(c for c in self.customers() if c['cif'] == data['cif'])
                for key, value in data.items():self.assertEqual(customer[key], value)
                self.assertEqual(customer['revision'], 0)
                status, created, _ = self.maker.call('/documents', document);self.assertEqual(status, 201, created)
                detail = self.maker.call('/documents/' + created['id'])[1]['document']
                self.assertEqual(detail['verification']['required'], 2 if dual else 1)
                self.assertEqual(detail['review_flow'], 1)  # This shared regression fixture creates legacy documents.
                self.assertEqual(self.review(request_id)[0], 409)

    def test_rejection_needs_reason_keeps_master_empty_and_allows_a_new_request(self):
        data = self.payload();request_id = self.submit(data)
        self.assertEqual(self.review(request_id, 'rejected', notes=' ')[0], 400)
        self.assertEqual(self.review(request_id, 'rejected', notes='Periksa kembali data rekening.')[0], 200)
        self.assertFalse(any(c['cif'] == data['cif'] for c in self.customers()))
        self.assertEqual(self.review(request_id)[0], 409)
        self.assertNotEqual(self.submit(data), request_id)

    def test_roles_csrf_and_client_identity_cannot_bypass_approval(self):
        data = self.payload();boh = self.boh_client()
        for client in (self.sol, self.maker, boh):
            self.assertEqual(client.call('/customer-create-requests', data)[0], 403)
        self.assertEqual(self.customer.call('/customer-create-requests', data)[0], 401)
        self.assertEqual(self.checker.call('/customer-create-requests', data, csrf=False)[0], 403)
        self.assertEqual(self.checker.call('/customers', data)[0], 403)
        request_id = self.submit({**data, 'status': 'approved', 'requested_by': 'spoofed', 'reviewed_by': 'spoofed'})
        for client in (self.checker, self.maker, boh):
            self.assertEqual(self.review(request_id, client=client)[0], 403)
        route = '/customer-edit-requests/' + request_id + '/review'
        self.assertEqual(self.sol.call(route, {'decision': 'approved'}, csrf=False)[0], 403)
        self.assertEqual(self.review(request_id, 'invalid')[0], 400)
        request = self.sol.call('/customer-edit-requests')[1]['requests'][0]
        self.assertEqual(request['status'], 'pending');self.assertNotEqual(request['requested_by'], 'spoofed')
        self.assertFalse(any(c['cif'] == data['cif'] for c in self.customers()))

    def test_validation_duplicate_cif_and_direct_creation_conflicts(self):
        data = self.payload()
        for key, value in [('cif', 'abc'), ('name', ''), ('account', '123'), ('person', ''), ('email', 'invalid'), ('phone', ''), ('verification_count', 3)]:
            self.assertEqual(self.checker.call('/customer-create-requests', {**data, key: value})[0], 400, key)
        dual = self.payload(dual=True)
        for changes in ({'second_name': ''}, {'second_email': dual['email']}, {'second_phone': ''}):
            self.assertEqual(self.checker.call('/customer-create-requests', {**dual, **changes})[0], 400)
        self.assertEqual(self.checker.call('/customer-create-requests', self.payload('1234567'))[0], 409)
        request_id = self.submit(data)
        self.assertEqual(self.checker.call('/customer-create-requests', data)[0], 409)
        self.assertEqual(self.sol.call('/customers', data)[0], 403)
        self.assertEqual(self.review(request_id)[0], 200)
        self.assertEqual(self.checker.call('/customer-create-requests', data)[0], 409)
        self.assertEqual(self.sol.call('/customers', data)[0], 403)

    def test_concurrent_submissions_and_decisions_create_exactly_one_customer(self):
        data = self.payload()
        other_checker = Client(self.url)
        session = other_checker.call('/login', {'email': 'sol@example.test', 'password': 'SolCheckerDemo!2026'})[1];other_checker.csrf = session['csrf']
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results = list(pool.map(lambda client: client.call('/customer-create-requests', data), [self.checker, other_checker]))
        self.assertEqual(sorted(r[0] for r in results), [201, 409])
        request_id = next(result['id'] for status, result, _ in results if status == 201)
        other_amol = Client(self.url);other_amol.login('sol')
        with concurrent.futures.ThreadPoolExecutor() as pool:
            statuses = list(pool.map(lambda client: self.review(request_id, client=client)[0], [self.sol, other_amol]))
        self.assertEqual(sorted(statuses), [200, 409])
        self.assertEqual(sum(c['cif'] == data['cif'] for c in self.customers()), 1)
        with app.database() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM management_audit WHERE action LIKE 'AMOL menyetujui penambahan nasabah:%'").fetchone()[0], 1)

    def test_an_existing_master_record_is_never_overwritten_by_pending_registration(self):
        data = self.payload();request_id = self.submit(data)
        with app.database(True) as db:
            app.insert_customer(db, app.new_customer_data({**data, 'name': 'Master dari proses lain'}))
        self.assertEqual(self.review(request_id)[0], 409)
        saved = next(c for c in self.customers() if c['cif'] == data['cif'])
        self.assertEqual(saved['name'], 'Master dari proses lain')
        self.assertEqual(self.review(request_id, 'rejected', notes='CIF sudah terdaftar.')[0], 200)

    def test_operation_migration_preserves_old_pending_customer_edits(self):
        request_id = self.checker.call('/customers/1234567/edit-requests', self.customer_edit())[1]['id']
        with app.database(True) as db:
            before = dict(db.execute('SELECT * FROM customer_edit_requests WHERE id=?', (request_id,)).fetchone())
            db.execute('ALTER TABLE customer_edit_requests DROP COLUMN operation')
        app.initialize();app.initialize()
        with app.database() as db:
            after = dict(db.execute('SELECT * FROM customer_edit_requests WHERE id=?', (request_id,)).fetchone())
        self.assertEqual(after['operation'], 'update')
        self.assertEqual(before, after)
        self.assertEqual(self.review(request_id)[0], 200)
