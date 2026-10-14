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
        self.assertEqual(self.it.call(endpoint, {'name': 'Officer Baru'})[0], 200)
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


if __name__ == '__main__':
    unittest.main()
