"""Named Officer logins retain role boundaries and record the actual submitter."""
import importlib.util
from pathlib import Path
import sqlite3
import time
import unittest
import test_app as workflow

app, Client, FILE, DESTINATION = workflow.app, workflow.Client, workflow.FILE, workflow.DESTINATION
spec=importlib.util.spec_from_file_location('officer_setup',Path(__file__).resolve().parents[1]/'scripts/provision_officer_logins.py')
setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup);setup.app=app


class OfficerUsernameTests(unittest.TestCase):
    setUp=workflow.WorkflowTests.setUp
    tearDown=workflow.WorkflowTests.tearDown
    create=workflow.WorkflowTests.create

    def payload(self, retire=False):
        return {'accounts': {name:'FixtureTeller!2026' if name.startswith('Teller') else 'FixtureCustomerService!2026' for name in ('Teller0376-1','Teller0376-2','CS0376-3','CS0376-4')}, 'retire_emails':['petugas@bpip.local'] if retire else []}

    def login(self, identifier, password):
        client=Client(self.url)
        status,session,_=client.call('/login',{'email':identifier,'password':password})
        self.assertEqual(status,200,session);client.csrf=session['csrf']
        return client,session

    def test_four_usernames_profiles_and_audit_are_authoritative_and_isolated(self):
        payload=self.payload();result=setup.provision(payload);self.assertTrue(result['ok'])
        makers=[]
        for username,password in payload['accounts'].items():
            client,session=self.login(username,password)
            self.assertEqual(session['user']['name'],username);self.assertEqual(session['user']['role'],'petugas')
            status,result,_=client.call('/documents',{'cif':'1234567','kind':'Standing Instruction','nominal':123,'file':FILE,**DESTINATION,'maker':'spoofed','maker_name':'Someone Else','actor':'spoofed'})
            self.assertEqual(status,201,result);doc_id=result['id']
            detail=client.call('/documents/'+doc_id)[1]['document']
            makers.append(detail['maker']);self.assertEqual(detail['maker'],session['user']['id']);self.assertEqual(detail['maker_name'],username)
            submitted=[event for event in detail['audit'] if event['action'].startswith('Dokumen diajukan oleh ')]
            self.assertEqual(len(submitted),1);self.assertEqual(submitted[0]['action'],'Dokumen diajukan oleh '+username);self.assertEqual(submitted[0]['actor'],username)
            self.assertEqual(client.call('/customer-create-requests',{})[0],403)
            self.assertEqual(client.call('/documents/'+doc_id+'/checker-review',{'decision':'approved','version':1})[0],403)
            self.assertEqual(client.call('/documents/'+doc_id+'/review',{'decision':'approved','version':1})[0],403)
        self.assertEqual(len(set(makers)),4)

    def test_usernames_are_case_insensitive_email_logins_work_and_invalid_accounts_fail(self):
        payload=self.payload();setup.provision(payload)
        for username,password in payload['accounts'].items():
            first,session=self.login('  '+username.swapcase()+'  ',password)
            second,again=self.login(session['user']['email'],password)
            self.assertEqual(session['user']['id'],again['user']['id'])
        self.assertEqual(Client(self.url).call('/login',{'email':'Teller0376-1','password':'wrong'})[0],401)
        self.assertEqual(Client(self.url).call('/login',{'email':"Teller0376-1' OR 1=1 --",'password':'FixtureTeller!2026'})[0],401)
        with app.database(True) as db:db.execute("UPDATE users SET active=0 WHERE username='Teller0376-1'")
        self.assertEqual(Client(self.url).call('/login',{'email':'Teller0376-1','password':'FixtureTeller!2026'})[0],401)
        self.assertEqual(self.sol.call('/session')[0],200);self.assertEqual(self.checker.call('/session')[0],200)

    def test_old_officer_is_retired_without_reassigning_documents_or_changing_historical_audit(self):
        doc=self.create()
        with app.database() as db:
            before_doc=dict(db.execute('SELECT * FROM documents WHERE id=?',(doc,)).fetchone())
            before_audit=[dict(r) for r in db.execute('SELECT * FROM audit WHERE doc_id=?',(doc,))]
            reviewer_ids={r['id'] for r in db.execute("SELECT id FROM users WHERE role IN ('sol','checker')")}
        result=setup.provision(self.payload(retire=True));self.assertTrue(result['operational_data_preserved'])
        self.assertEqual(Path(result['backup']).stat().st_mode&0o777,0o600)
        self.assertEqual(self.maker.call('/session')[0],401)
        with app.database() as db:
            self.assertEqual(dict(db.execute('SELECT * FROM documents WHERE id=?',(doc,)).fetchone()),before_doc)
            self.assertEqual([dict(r) for r in db.execute('SELECT * FROM audit WHERE doc_id=?',(doc,))],before_audit)
            self.assertEqual({r['id'] for r in db.execute("SELECT id FROM users WHERE role IN ('sol','checker')")},reviewer_ids)
            self.assertEqual(db.execute('SELECT active FROM users WHERE id=?',(before_doc['maker'],)).fetchone()[0],0)
        self.assertEqual(self.sol.call('/documents/'+doc)[1]['document']['maker_name'],'Rina Wulandari')

    def test_repeat_setup_preserves_new_ids_and_operational_data_and_conflicts_are_atomic(self):
        payload=self.payload();setup.provision(payload)
        client,session=self.login('Teller0376-1',payload['accounts']['Teller0376-1'])
        setup.provision(payload)
        self.assertEqual(client.call('/session')[0],401)
        self.assertEqual(self.login('Teller0376-1',payload['accounts']['Teller0376-1'])[1]['user']['id'],session['user']['id'])
        with app.database() as db:before=[dict(row) for row in db.execute('SELECT id,email,name,role,active,username FROM users ORDER BY id')]
        for invalid in ({'accounts':{'Bad': 'FixtureSecret!2026'}},{'accounts':{**payload['accounts'],'Teller0376-1':'short'}},{**payload,'retire_emails':['sol@example.test']}):
            with self.assertRaises(ValueError):setup.provision(invalid)
        with app.database() as db:self.assertEqual([dict(row) for row in db.execute('SELECT id,email,name,role,active,username FROM users ORDER BY id')],before)

    def test_admin_officer_setup_accepts_requested_eleven_character_cs_password(self):
        payload=self.payload()
        payload['accounts']['CS0376-3']='F'*11
        payload['accounts']['CS0376-4']='G'*11
        setup.provision(payload)
        self.login('CS0376-3','F'*11)
        self.login('CS0376-4','G'*11)
        with self.assertRaises(ValueError):setup.provision({**payload,'accounts':{**payload['accounts'],'CS0376-3':'F'*10}})

    def test_username_and_email_share_login_rate_limit(self):
        setup.provision(self.payload())
        with app.database(True) as db:
            db.executemany('INSERT INTO login_attempts VALUES(?,?,?)',[('198.51.100.8','teller0376-1@example.test',time.time())]*9)
        self.assertEqual(Client(self.url).call('/login',{'email':'TELLER0376-1','password':'wrong'})[0],401)
        self.assertEqual(Client(self.url).call('/login',{'email':'teller0376-1@example.test','password':'FixtureTeller!2026'})[0],429)

    def test_legacy_migration_preserves_users_sessions_and_case_insensitive_uniqueness(self):
        with app.database(True) as db:
            db.execute('DROP INDEX users_username_unique');db.execute('ALTER TABLE users DROP COLUMN username')
            users=[dict(r) for r in db.execute('SELECT id,email,name,role,active FROM users ORDER BY id')]
        app.initialize();app.initialize()
        self.assertEqual(self.maker.call('/session')[0],200)
        with app.database() as db:self.assertEqual([dict(r) for r in db.execute('SELECT id,email,name,role,active FROM users ORDER BY id')],users)
        setup.provision(self.payload())
        with self.assertRaises(sqlite3.IntegrityError):
            with app.database(True) as db:db.execute("UPDATE users SET username='teller0376-1' WHERE email='sol@example.test'")
