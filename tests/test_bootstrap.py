import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import server


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = server.DB_PATH, server.PRODUCTION
        server.DB_PATH = Path(self.temp.name) / 'initial.sqlite3'
        server.PRODUCTION = True
        server.initialize()
        self.values = {
            'BOOTSTRAP_PETUGAS_EMAIL': 'maker@example.com',
            'BOOTSTRAP_PETUGAS_NAME': 'Petugas Uji',
            'BOOTSTRAP_PETUGAS_PASSWORD': 'MakerPrivate!2026',
            'BOOTSTRAP_SOL_EMAIL': 'checker@example.com',
            'BOOTSTRAP_SOL_NAME': 'SOL Uji',
            'BOOTSTRAP_SOL_PASSWORD': 'CheckerPrivate!2026',
        }

    def tearDown(self):
        server.DB_PATH, server.PRODUCTION = self.previous
        self.temp.cleanup()

    def count(self):
        with server.database() as db:
            return db.execute('SELECT COUNT(*) FROM users').fetchone()[0]

    def test_phone_migration_preserves_existing_customer(self):
        with server.database(True) as db:
            db.execute('DROP TABLE customers')
            db.execute('CREATE TABLE customers(cif TEXT PRIMARY KEY, name TEXT, account TEXT, person TEXT, email TEXT)')
            db.execute("INSERT INTO customers VALUES('123','Lama','000123456789012','Direktur','lama@example.com')")
        server.initialize()
        server.initialize()
        with server.database() as db:
            customer = dict(db.execute('SELECT * FROM customers').fetchone())
        self.assertEqual(customer['name'], 'Lama')
        self.assertEqual(customer['account'], '000123456789012')
        self.assertEqual(customer['phone'], '')

    def test_atomic_creation_and_no_password_reset_on_restart(self):
        with patch.dict(os.environ, self.values):
            self.assertTrue(server.bootstrap_users())
        self.assertEqual(self.count(), 2)
        with server.database(True) as db:
            db.execute('UPDATE users SET password=? WHERE role=?', (server.password_hash('UpdatedPrivate!2026'), 'petugas'))
        # No secrets needed once initialized; startup never resets passwords.
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(server.bootstrap_users())
        with server.database() as db:
            user = db.execute("SELECT * FROM users WHERE role='petugas'").fetchone()
        self.assertTrue(server.password_matches('UpdatedPrivate!2026', user['password']))

    def test_invalid_sol_does_not_leave_partial_account(self):
        for overrides in ({'BOOTSTRAP_SOL_PASSWORD':'short'},
                          {'BOOTSTRAP_SOL_EMAIL':'maker@example.com'},
                          {'BOOTSTRAP_SOL_EMAIL':'bad email'},
                          {'BOOTSTRAP_SOL_PASSWORD':'SolDemo!2026'}):
            with self.subTest(overrides=overrides), patch.dict(os.environ, {**self.values, **overrides}):
                with self.assertRaises(server.AppError):
                    server.bootstrap_users()
            self.assertEqual(self.count(), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
