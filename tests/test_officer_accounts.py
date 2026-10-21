"""Retired IT access and web account administration stay disabled."""
import time
import unittest

from tests import test_app as workflow

app, Client = workflow.app, workflow.Client


class RetiredAccountManagementTests(unittest.TestCase):
    setUp = workflow.WorkflowTests.setUp
    tearDown = workflow.WorkflowTests.tearDown

    def legacy_it(self):
        raw = 'legacy-it-session-fixture'
        with app.database(True) as db:
            db.execute('INSERT INTO users(id,email,name,role,password) VALUES(?,?,?,?,?)',
                       ('legacy-it', 'legacy.it@example.test', 'Legacy IT', 'it', app.password_hash('LegacyITTest!2026')))
            db.execute('INSERT INTO sessions VALUES(?,?,?,?)', (app.digest(raw), 'legacy-it', 'legacy-csrf', time.time()+3600))
        client = Client(self.url)
        client.opener.addheaders = [('Cookie', 'bpip_session='+raw)]
        client.csrf = 'legacy-csrf'
        return client

    def test_it_cannot_be_created_or_authenticated_even_before_restart(self):
        with self.assertRaises(ValueError):
            app.create_user('new.it@example.test', 'New IT', 'it', 'NewITTest!2026')
        legacy = self.legacy_it()
        self.assertEqual(Client(self.url).call('/login', {'email':'legacy.it@example.test','password':'LegacyITTest!2026'})[0], 401)
        for path in ('/session','/documents','/customers','/officers','/officer-account-requests'):
            self.assertEqual(legacy.call(path)[0], 401, path)
        self.assertEqual(legacy.call('/password', {'current':'LegacyITTest!2026','password':'ChangedITTest!2026'})[0], 401)

    def test_retirement_is_idempotent_and_preserves_history_and_other_users(self):
        self.legacy_it()
        doc = workflow.WorkflowTests.create(self)
        with app.database(True) as db:
            db.execute('INSERT INTO officer_account_requests(id,email,name,password_hash,requested_by,requested_name,created) VALUES(?,?,?,?,?,?,?)',
                       ('a'*24,'pending@example.test','Pending Officer',app.password_hash('PendingOfficer!2026'),'legacy-it','Legacy IT',app.now()))
            db.execute('INSERT INTO management_audit(entity,action,actor,at) VALUES(?,?,?,?)', ('legacy-it','Historic account action','legacy-it',app.now()))
            before = {table:[tuple(row) for row in db.execute('SELECT * FROM '+table)] for table in ('documents','versions','audit','officer_account_requests','management_audit')}
            users = [tuple(row) for row in db.execute("SELECT * FROM users WHERE role<>'it'")]
        app.initialize();app.initialize()
        with app.database() as db:
            self.assertEqual(db.execute("SELECT active FROM users WHERE id='legacy-it'").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM sessions WHERE user_id='legacy-it'").fetchone()[0],0)
            self.assertEqual(users,[tuple(row) for row in db.execute("SELECT * FROM users WHERE role<>'it'")])
            for table, rows in before.items():
                self.assertEqual(rows,[tuple(row) for row in db.execute('SELECT * FROM '+table)],table)
        self.assertEqual(self.maker.call('/session')[0],200)
        self.assertEqual(self.sol.call('/session')[0],200)
        self.assertEqual(self.maker.call('/documents/'+doc)[0],200)

    def test_removed_web_endpoints_cannot_create_rename_disable_or_approve(self):
        app.create_user('boh.accounts@example.test','BOH Accounts','boh','BOHLocalTest!2026')
        boh=Client(self.url)
        status,session,_=boh.call('/login',{'email':'boh.accounts@example.test','password':'BOHLocalTest!2026'})
        self.assertEqual(status,200);boh.csrf=session['csrf']
        user_id=self.maker.call('/session')[1]['user']['id']
        paths=('/officers','/officer-account-requests','/officer-account-requests/'+'a'*24+'/review',
               '/officers/'+user_id+'/name','/officers/'+user_id+'/delete-requests','/officer-change-requests/'+'b'*24+'/review')
        with app.database() as db:
            before=[tuple(row) for row in db.execute('SELECT * FROM users')]
        for client in (self.maker,self.sol,boh):
            for path in paths:
                self.assertEqual(client.call(path)[0],404,path)
                self.assertEqual(client.call(path,{'email':'new@example.test','name':'Changed','password':'NewOfficerTest!2026','decision':'approved','notes':'Test','reason':'Test'})[0],404,path)
        with app.database() as db:
            self.assertEqual(before,[tuple(row) for row in db.execute('SELECT * FROM users')])
        self.assertEqual(boh.call('/documents')[0],200)
        self.assertEqual(boh.call('/customer-edit-requests')[0],403)
        self.assertEqual(self.sol.call('/customers')[0],200)
