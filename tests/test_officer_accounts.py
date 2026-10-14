"""Officer provisioning requires IT submission and a separate BOH decision."""
import concurrent.futures
import json
import unittest

from tests import test_app as workflow

app, Client = workflow.app, workflow.Client


class OfficerAccountTests(unittest.TestCase):
    def setUp(self):
        workflow.WorkflowTests.setUp(self)
        app.create_user('it@example.test', 'IT', 'it', 'ITLocalTest!2026')
        app.create_user('boh.accounts@example.test', 'BOH Accounts', 'boh', 'BOHLocalTest!2026')
        self.it = self.client('it@example.test', 'ITLocalTest!2026')
        self.boh = self.client('boh.accounts@example.test', 'BOHLocalTest!2026')

    tearDown = workflow.WorkflowTests.tearDown

    def client(self, email, password):
        client = Client(self.url)
        status, result, _ = client.call('/login', {'email': email, 'password': password})
        self.assertEqual(status, 200, result)
        client.csrf = result['csrf']
        return client

    def payload(self, **changes):
        return {'email': 'officer.new@example.test', 'name': 'Officer Baru', 'password': 'NewOfficerTest!2026', **changes}

    def submit(self, **changes):
        status, result, _ = self.it.call('/officer-account-requests', self.payload(**changes))
        self.assertEqual(status, 201, result)
        return result['id']

    def review(self, request_id, decision='approved', notes='', client=None):
        return (client or self.boh).call('/officer-account-requests/' + request_id + '/review', {'decision': decision, 'notes': notes})

    def test_pending_account_cannot_login_then_boh_activates_once(self):
        request_id = self.submit()
        app.initialize()
        self.assertEqual(Client(self.url).call('/login', {'email': self.payload()['email'], 'password': self.payload()['password']})[0], 401)
        requests = self.boh.call('/officer-account-requests')[1]['requests']
        self.assertEqual(requests[0]['status'], 'pending')
        self.assertNotIn('password', json.dumps(requests))
        self.assertNotIn(self.payload()['password'], json.dumps(requests))
        self.assertEqual(self.review(request_id, client=self.it)[0], 403)
        with app.database() as db:
            pending = db.execute('SELECT password_hash FROM officer_account_requests WHERE id=?', (request_id,)).fetchone()
            self.assertTrue(app.password_matches(self.payload()['password'], pending['password_hash']))
            self.assertNotEqual(pending['password_hash'], self.payload()['password'])
            self.assertIsNone(db.execute('SELECT id FROM users WHERE email=?', (self.payload()['email'],)).fetchone())
        self.assertEqual(self.review(request_id)[0], 200)
        officer = self.client(self.payload()['email'], self.payload()['password'])
        self.assertEqual(officer.call('/session')[1]['user']['role'], 'petugas')
        self.assertEqual(officer.call('/session')[1]['user']['name'], 'Officer Baru')
        self.assertEqual(officer.call('/customers')[0], 200)
        self.assertEqual(self.review(request_id)[0], 409)
        with app.database() as db:
            request = db.execute('SELECT * FROM officer_account_requests WHERE id=?', (request_id,)).fetchone()
            self.assertIsNone(request['password_hash'])
            self.assertEqual(request['status'], 'approved')
            self.assertEqual(request['user_id'], officer.call('/session')[1]['user']['id'])
            self.assertEqual(db.execute('SELECT COUNT(*) FROM users WHERE email=?', (self.payload()['email'],)).fetchone()[0], 1)

    def test_rejection_requires_reason_and_never_creates_account(self):
        request_id = self.submit()
        self.assertEqual(self.review(request_id, 'rejected')[0], 400)
        self.assertEqual(self.review(request_id, 'rejected', 'Belum memenuhi persyaratan')[0], 200)
        self.assertEqual(self.review(request_id)[0], 409)
        self.assertEqual(Client(self.url).call('/login', {'email': self.payload()['email'], 'password': self.payload()['password']})[0], 401)
        app.initialize()
        request = self.it.call('/officer-account-requests')[1]['requests'][0]
        self.assertEqual(request['status'], 'rejected')
        self.assertEqual(request['review_notes'], 'Belum memenuhi persyaratan')
        with app.database() as db:
            self.assertIsNone(db.execute('SELECT password_hash FROM officer_account_requests WHERE id=?', (request_id,)).fetchone()['password_hash'])
        self.assertNotEqual(self.submit(), request_id)

    def test_roles_csrf_and_origin_are_enforced(self):
        for client in (self.maker, self.sol, Client(self.url)):
            expected = 401 if not client.csrf else 403
            for endpoint in ('/officers', '/officer-account-requests'):
                self.assertEqual(client.call(endpoint)[0], expected)
            self.assertEqual(client.call('/officer-account-requests', self.payload())[0], expected)
        self.assertEqual(self.boh.call('/officer-account-requests', self.payload())[0], 403)
        for endpoint in ('/customers', '/documents', '/outbox', '/customer-edit-requests', '/customers/archived', '/documents/archived'):
            self.assertEqual(self.it.call(endpoint)[0], 403, endpoint)
        self.assertEqual(self.it.call('/customers', {'name': 'test'})[0], 403)
        self.assertEqual(self.it.call('/documents', {})[0], 403)
        self.assertEqual(self.it.call('/officer-account-requests', self.payload(), csrf=False)[0], 403)
        self.assertEqual(self.it.call('/officer-account-requests', self.payload(), origin='https://wrong.example.test')[0], 403)
        for role in ('it', 'boh', 'sol'):
            self.assertEqual(self.it.call('/officer-account-requests', self.payload(role=role))[0], 400)
        self.assertEqual(self.it.call('/officer-account-requests', self.payload(password='short'))[0], 400)
        self.assertEqual(self.it.call('/officer-account-requests', self.payload(name=''))[0], 400)
        self.assertEqual(self.it.call('/officer-account-requests', self.payload(email='invalid'))[0], 400)
        self.assertEqual(self.it.call('/officer-account-requests')[1]['requests'], [])

    def test_duplicate_emails_and_approval_collision_preserve_pending_request(self):
        self.assertEqual(self.it.call('/officer-account-requests', self.payload(email='PETUGAS@BPIP.LOCAL'))[0], 409)
        request_id = self.submit(email='Officer.New@Example.Test')
        self.assertEqual(self.it.call('/officer-account-requests', self.payload())[0], 409)
        app.create_user(self.payload()['email'], 'Existing account', 'sol', 'ExistingAccount!2026')
        self.assertEqual(self.review(request_id)[0], 409)
        request = self.boh.call('/officer-account-requests')[1]['requests'][0]
        self.assertEqual(request['status'], 'pending')
        with app.database() as db:
            self.assertEqual(db.execute('SELECT role FROM users WHERE email=?', (self.payload()['email'],)).fetchone()['role'], 'sol')

    def test_concurrent_reviews_create_exactly_one_officer(self):
        request_id = self.submit()
        second_boh = self.client('boh.accounts@example.test', 'BOHLocalTest!2026')
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.review, request_id, client=client) for client in (self.boh, second_boh)]
            results = sorted(future.result()[0] for future in futures)
        self.assertEqual(results, [200, 409])
        with app.database() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM users WHERE email=?', (self.payload()['email'],)).fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM management_audit WHERE entity=? AND action LIKE 'BOH menyetujui%'", ('officer-accounts/' + request_id,)).fetchone()[0], 1)

    def test_it_rename_preserves_login_ownership_and_cannot_change_other_roles(self):
        doc = workflow.WorkflowTests.create(self)
        original = self.maker.call('/session')[1]['user']
        endpoint = '/officers/' + original['id'] + '/name'
        for client in (self.boh, self.sol, self.maker):
            self.assertEqual(client.call(endpoint, {'name': 'Officer Baru'})[0], 403)
        self.assertEqual(self.it.call(endpoint, {'name': 'Officer Baru'}, csrf=False)[0], 403)
        self.assertEqual(self.it.call(endpoint, {'name': ''})[0], 400)
        self.assertEqual(self.it.call(endpoint, {'name': 'Officer Baru', 'role': 'sol'})[0], 400)
        status, request, _ = self.it.call(endpoint, {'name': 'Officer Baru'})
        self.assertEqual(status, 201)
        self.assertEqual(self.maker.call('/session')[1]['user'], original)
        app.initialize()
        proposal = self.boh.call('/officer-account-requests')[1]['requests'][0]
        self.assertEqual(proposal['type'], 'rename')
        self.assertEqual(proposal['old_name'], original['name'])
        self.assertEqual(proposal['name'], 'Officer Baru')
        review = '/officer-change-requests/' + request['id'] + '/review'
        for client in (self.it, self.sol, self.maker):
            self.assertEqual(client.call(review, {'decision': 'approved', 'notes': ''})[0], 403)
        self.assertEqual(self.boh.call(review, {'decision': 'approved', 'notes': ''}, csrf=False)[0], 403)
        self.assertEqual(self.boh.call(review, {'decision': 'approved', 'notes': ''})[0], 200)
        self.assertEqual(self.boh.call(review, {'decision': 'approved', 'notes': ''})[0], 409)
        changed = self.maker.call('/session')[1]['user']
        self.assertEqual(changed, original | {'name': 'Officer Baru'})
        self.assertEqual(self.maker.call('/documents/' + doc)[0], 200)
        self.assertEqual(self.client('petugas@bpip.local', 'PetugasDemo!2026').call('/session')[1]['user']['name'], 'Officer Baru')
        for client in (self.it, self.boh, self.sol):
            user_id = client.call('/session')[1]['user']['id']
            self.assertEqual(self.it.call('/officers/' + user_id + '/name', {'name': 'Changed'})[0], 404)
        self.assertEqual(self.it.call('/documents/' + doc)[0], 403)
        self.assertEqual(self.it.call('/documents/' + doc + '/execution-pdf')[0], 403)
        with app.database() as db:
            audit = db.execute("SELECT action FROM management_audit WHERE entity=? ORDER BY id DESC LIMIT 1", ('users/' + original['id'],)).fetchone()['action']
            self.assertIn(original['name'], audit)
            self.assertIn('Officer Baru', audit)

    def test_name_rejection_preserves_account_and_allows_new_proposal(self):
        original = self.maker.call('/session')[1]['user']
        endpoint = '/officers/' + original['id'] + '/name'
        self.assertEqual(self.it.call(endpoint, {'name': original['name']})[0], 400)
        request_id = self.it.call(endpoint, {'name': 'Usulan Nama'})[1]['id']
        self.assertEqual(self.it.call(endpoint, {'name': 'Usulan Lain'})[0], 409)
        review = '/officer-change-requests/' + request_id + '/review'
        self.assertEqual(self.boh.call(review, {'decision': 'rejected', 'notes': ''})[0], 400)
        self.assertEqual(self.boh.call(review, {'decision': 'rejected', 'notes': 'Nama belum sesuai'})[0], 200)
        self.assertEqual(self.maker.call('/session')[1]['user'], original)
        self.assertEqual(self.it.call(endpoint, {'name': 'Usulan Baru'})[0], 201)

    def test_name_approval_detects_stale_account(self):
        original = self.maker.call('/session')[1]['user']
        request_id = self.it.call('/officers/' + original['id'] + '/name', {'name': 'Usulan Nama'})[1]['id']
        with app.database(True) as db:
            db.execute('UPDATE users SET name=? WHERE id=?', ('Nama diubah administrator', original['id']))
        review = '/officer-change-requests/' + request_id + '/review'
        self.assertEqual(self.boh.call(review, {'decision': 'approved', 'notes': ''})[0], 409)
        self.assertEqual(self.maker.call('/session')[1]['user']['name'], 'Nama diubah administrator')
        self.assertEqual(self.it.call('/officer-account-requests')[1]['requests'][0]['status'], 'pending')

    def test_concurrent_name_reviews_allow_only_one_decision(self):
        original = self.maker.call('/session')[1]['user']
        request_id = self.it.call('/officers/' + original['id'] + '/name', {'name': 'Usulan Nama'})[1]['id']
        second_boh = self.client('boh.accounts@example.test', 'BOHLocalTest!2026')
        review = '/officer-change-requests/' + request_id + '/review'
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(client.call, review, {'decision': 'approved', 'notes': ''}) for client in (self.boh, second_boh)]
            self.assertEqual(sorted(future.result()[0] for future in futures), [200, 409])
        self.assertEqual(self.maker.call('/session')[1]['user']['name'], 'Usulan Nama')

    def test_shared_documents_keep_maker_and_limit_mutations_to_creator(self):
        doc = workflow.WorkflowTests.create(self)
        original = self.maker.call('/session')[1]['user']
        app.create_user('shared.officer@example.test', 'Officer Kedua', 'petugas', 'SharedOfficer!2026')
        other = self.client('shared.officer@example.test', 'SharedOfficer!2026')
        summary = other.call('/documents')[1]['documents'][0]
        self.assertEqual(summary['id'], doc)
        self.assertEqual(summary['maker'], original['id'])
        self.assertEqual(summary['maker_name'], original['name'])
        for path in ('/documents/' + doc, '/documents/' + doc + '/file', '/documents/' + doc + '/versions/1/file'):
            self.assertEqual(other.call(path)[0], 200)
        for suffix, data in (
            ('/send-confirmation', {'version': 1, 'channel': 'email'}),
            ('/resend', {'version': 1}),
            ('/cancel', {'version': 1, 'notes': 'Tidak boleh'}),
            ('/revise', {}),
            ('/review', {'version': 1, 'decision': 'approved'}),
        ):
            self.assertEqual(other.call('/documents/' + doc + suffix, data)[0], 403, suffix)
        self.assertEqual(other.call('/documents/' + doc + '/whatsapp-preview')[0], 403)
        self.assertEqual(other.call('/outbox')[1]['messages'], [])
        second = workflow.WorkflowTests.create(self, other)
        docs = self.maker.call('/documents')[1]['documents']
        self.assertEqual({d['id'] for d in docs}, {doc, second})
        self.assertEqual(next(d for d in docs if d['id'] == second)['maker_name'], 'Officer Kedua')

    def test_delete_requires_boh_and_preserves_documents_after_revoking_sessions(self):
        doc = workflow.WorkflowTests.create(self)
        original = self.maker.call('/session')[1]['user']
        app.create_user('shared.officer@example.test', 'Officer Kedua', 'petugas', 'SharedOfficer!2026')
        other = self.client('shared.officer@example.test', 'SharedOfficer!2026')
        endpoint = '/officers/' + original['id'] + '/delete-requests'
        payload = {'reason': 'Officer sudah tidak bertugas'}
        for client in (self.maker, self.sol, self.boh):
            self.assertEqual(client.call(endpoint, payload)[0], 403)
        self.assertEqual(self.it.call(endpoint, payload, csrf=False)[0], 403)
        self.assertEqual(self.it.call(endpoint, {'reason': ''})[0], 400)
        status, request, _ = self.it.call(endpoint, payload)
        self.assertEqual(status, 201)
        self.assertEqual(self.maker.call('/session')[0], 200)
        self.assertEqual(self.it.call('/officers/' + original['id'] + '/name', {'name': 'Nama baru'})[0], 409)
        self.assertEqual(self.it.call(endpoint, payload)[0], 409)
        proposal = self.boh.call('/officer-account-requests')[1]['requests'][0]
        self.assertEqual(proposal['type'], 'delete')
        self.assertEqual(proposal['reason'], payload['reason'])
        route = '/officer-change-requests/' + request['id'] + '/review'
        self.assertEqual(self.it.call(route, {'decision': 'approved', 'notes': ''})[0], 403)
        self.assertEqual(self.boh.call(route, {'decision': 'approved', 'notes': ''}, csrf=False)[0], 403)
        self.assertEqual(self.boh.call(route, {'decision': 'approved', 'notes': ''})[0], 200)
        self.assertEqual(self.boh.call(route, {'decision': 'approved', 'notes': ''})[0], 409)
        self.assertEqual(self.maker.call('/session')[0], 401)
        self.assertEqual(Client(self.url).call('/login', {'email': original['email'], 'password': 'PetugasDemo!2026'})[0], 401)
        self.assertNotIn(original['id'], [o['id'] for o in self.it.call('/officers')[1]['officers']])
        saved = other.call('/documents/' + doc)[1]['document']
        self.assertEqual(saved['maker'], original['id'])
        self.assertEqual(saved['maker_name'], original['name'])
        self.assertEqual(other.call('/documents/' + doc + '/file')[0], 200)
        with app.database() as db:
            self.assertEqual(db.execute('SELECT active FROM users WHERE id=?', (original['id'],)).fetchone()['active'], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sessions WHERE user_id=?', (original['id'],)).fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM documents WHERE maker=?', (original['id'],)).fetchone()[0], 1)

    def test_delete_rejection_keeps_account_active_and_protects_privileged_roles(self):
        original = self.maker.call('/session')[1]['user']
        endpoint = '/officers/' + original['id'] + '/delete-requests'
        request_id = self.it.call(endpoint, {'reason': 'Permintaan IT'})[1]['id']
        route = '/officer-change-requests/' + request_id + '/review'
        self.assertEqual(self.boh.call(route, {'decision': 'rejected', 'notes': ''})[0], 400)
        self.assertEqual(self.boh.call(route, {'decision': 'rejected', 'notes': 'Officer masih bertugas'})[0], 200)
        self.assertEqual(self.maker.call('/session')[0], 200)
        self.assertEqual(self.it.call('/officers/' + original['id'] + '/name', {'name': 'Usulan Baru'})[0], 201)
        for client in (self.it, self.boh, self.sol):
            user_id = client.call('/session')[1]['user']['id']
            self.assertEqual(self.it.call('/officers/' + user_id + '/delete-requests', {'reason': 'Tidak boleh'})[0], 404)

    def test_concurrent_delete_reviews_and_legacy_user_migration(self):
        original = self.maker.call('/session')[1]['user']
        request_id = self.it.call('/officers/' + original['id'] + '/delete-requests', {'reason': 'Officer tidak bertugas'})[1]['id']
        second_boh = self.client('boh.accounts@example.test', 'BOHLocalTest!2026')
        route = '/officer-change-requests/' + request_id + '/review'
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(client.call, route, {'decision': 'approved', 'notes': ''}) for client in (self.boh, second_boh)]
            self.assertEqual(sorted(future.result()[0] for future in futures), [200, 409])
        original_path = app.DB_PATH
        try:
            app.DB_PATH = original_path.parent / 'legacy.sqlite3'
            with app.sqlite3.connect(app.DB_PATH) as db:
                db.execute('CREATE TABLE users(id TEXT PRIMARY KEY,email TEXT UNIQUE,name TEXT,role TEXT,password TEXT)')
                db.execute('INSERT INTO users VALUES(?,?,?,?,?)', ('legacy', 'legacy@example.test', 'Officer Lama', 'petugas', 'original-hash'))
            db.close()
            app.initialize()
            with app.database() as db:
                row = db.execute('SELECT * FROM users WHERE id=?', ('legacy',)).fetchone()
                self.assertEqual(row['active'], 1)
                self.assertEqual(row['password'], 'original-hash')
                self.assertEqual(row['name'], 'Officer Lama')
        finally:
            app.DB_PATH = original_path


if __name__ == '__main__':
    unittest.main()
