"""Explicit server-admin provisioning. Never run automatically during deployment.

Credentials arrive at execution time through stdin/getpass, not source code.
Existing transaction owners and recorded audit actors are never reassigned.
"""
from contextlib import closing
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import sys
import server as app

OPERATIONAL_TABLES = ('customers', 'documents', 'versions', 'audit', 'customer_edit_requests', 'outbox')


def validate(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('accounts'), dict) or len(payload['accounts']) != 4:
        raise ValueError('Isi empat akun Officer dalam accounts.')
    result = []
    for username, password in payload['accounts'].items():
        if not isinstance(username, str) or not re.fullmatch(r'(?:Teller|CS)[0-9]{4}-[1-9][0-9]?', username):
            raise ValueError('Username wajib memakai format Teller/CS, kode uker empat digit, dan nomor akun.')
        if not isinstance(password, str) or not 11 <= len(password) <= 500:
            raise ValueError('Kata sandi wajib 11–500 karakter: ' + username)
        result.append({'username': username, 'email': username.lower() + '@example.test', 'password': password})
    if len({row['username'].lower() for row in result}) != 4:
        raise ValueError('Username setiap akun harus berbeda.')
    retired = payload.get('retire_emails', [])
    if not isinstance(retired, list) or len(retired) > 10:
        raise ValueError('Daftar akun lama tidak valid.')
    retired = [app.valid_email(email) for email in retired]
    if set(retired) & {row['email'] for row in result}:
        raise ValueError('Akun baru tidak dapat dinonaktifkan.')
    return result, retired


def locate(db, accounts, retired):
    found = []
    for values in accounts:
        rows = list(db.execute('SELECT id,email,name,username,role,active FROM users WHERE email=? OR username=? COLLATE NOCASE', (values['email'], values['username'])))
        if rows and (len(rows) != 1 or rows[0]['role'] != 'petugas' or rows[0]['email'] != values['email'] or rows[0]['username'] != values['username']):
            raise ValueError('Username atau email sudah digunakan akun lain: ' + values['username'])
        found.append(dict(rows[0]) if rows else None)
    for email in retired:
        row = db.execute('SELECT role FROM users WHERE email=?', (email,)).fetchone()
        if row and row['role'] != 'petugas':
            raise ValueError('Hanya akun Officer lama yang dapat dinonaktifkan.')
    return found


def provision(payload):
    accounts, retired = validate(payload)
    with app.database() as db:
        columns = {row['name'] for row in db.execute('PRAGMA table_info(users)')}
        if 'username' not in columns:
            raise ValueError('Deploy dukungan username terlebih dahulu.')
        locate(db, accounts, retired)
    backup = Path(str(app.DB_PATH) + '.before-officer-usernames-' + secrets.token_hex(4) + '.backup')
    descriptor = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    with closing(sqlite3.connect(app.DB_PATH)) as source, closing(sqlite3.connect(backup)) as target:
        source.backup(target)
    with app.database(True) as db:
        found = locate(db, accounts, retired)
        before = {table: db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] for table in OPERATIONAL_TABLES}
        for values, existing in zip(accounts, found):
            user_id = existing['id'] if existing else secrets.token_hex(12)
            if existing:
                db.execute('UPDATE users SET name=?,password=?,active=1 WHERE id=?', (values['username'], app.password_hash(values['password']), user_id))
            else:
                db.execute("INSERT INTO users(id,email,name,username,role,password,active) VALUES(?,?,?,?,'petugas',?,1)", (user_id, values['email'], values['username'], values['username'], app.password_hash(values['password'])))
            db.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))
            db.execute('DELETE FROM password_attempts WHERE user_id=?', (user_id,))
            db.execute('DELETE FROM login_attempts WHERE lower(email) IN (?,?)', (values['email'], values['username'].lower()))
            app.management_audit(db, 'users/' + user_id, 'Penyiapan login Officer ' + values['username'] + ' atas permintaan pemilik', {'id': 'terminal-admin'})
        for email in retired:
            row = db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
            if row:
                db.execute('UPDATE users SET active=0 WHERE id=?', (row['id'],))
                db.execute('DELETE FROM sessions WHERE user_id=?', (row['id'],))
                app.management_audit(db, 'users/' + row['id'], 'Akun Officer lama dinonaktifkan; identitas dan riwayat dipertahankan', {'id': 'terminal-admin'})
        after = {table: db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] for table in OPERATIONAL_TABLES}
        if before != after:
            raise ValueError('Data operasional berubah. Penyiapan dibatalkan.')
    return {'ok': True, 'accounts': [{'username': row['username'], 'name': row['username'], 'role': 'Officer'} for row in accounts], 'backup': str(backup), 'operational_data_preserved': True}


if __name__ == '__main__':
    try:
        raw = getpass.getpass('Tempel JSON empat akun Officer (input disembunyikan): ') if sys.stdin.isatty() else sys.stdin.read()
        print(json.dumps(provision(json.loads(raw)), indent=2))
    except Exception as error:
        print('GAGAL: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
