"""BPIP: dependency-free HTTP application, SQLite persistence and SMTP outbox.

Run `python3 server.py --demo` locally, or `python3 server.py init` to create users.
"""
import argparse
import base64
import getpass
import hashlib
import hmac
import json
import logging
import mimetypes
import os
import re
import secrets
import smtplib
import sqlite3
import ssl
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from email.message import EmailMessage
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
for line in (ROOT / '.env').read_text().splitlines() if (ROOT / '.env').exists() else []:
    if '=' in line and not line.strip().startswith('#'):
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

PRODUCTION = os.getenv('APP_ENV', 'development') == 'production'
DB_PATH = Path(os.getenv('DATABASE_PATH', str(ROOT / 'data/bpip.sqlite3')))
BASE_URL = (os.getenv('PUBLIC_BASE_URL') or os.getenv('RENDER_EXTERNAL_URL') or 'http://localhost:8000').rstrip('/')
MAIL_MODE = os.getenv('MAIL_MODE', 'console')
BANK_NAME = os.getenv('BANK_NAME', 'BPIP Document Confirmation')
MAX_FILE = 5 * 1024 * 1024
MAX_BODY = 8 * 1024 * 1024
SESSION_TTL = 8 * 3600
DEMO = False
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, email TEXT UNIQUE, name TEXT, role TEXT, password TEXT);
CREATE TABLE IF NOT EXISTS sessions(hash TEXT PRIMARY KEY, user_id TEXT, csrf TEXT, expires REAL);
CREATE TABLE IF NOT EXISTS login_attempts(ip TEXT, email TEXT, at REAL);
CREATE INDEX IF NOT EXISTS attempts_time ON login_attempts(at);
CREATE TABLE IF NOT EXISTS customers(cif TEXT PRIMARY KEY, name TEXT, account TEXT, person TEXT, email TEXT);
CREATE TABLE IF NOT EXISTS archived_documents(doc_id TEXT PRIMARY KEY, archived_at TEXT, actor TEXT);
CREATE TABLE IF NOT EXISTS documents(
 id TEXT PRIMARY KEY, cif TEXT, customer_name TEXT, account TEXT, person TEXT, email TEXT,
 kind TEXT, nominal INTEGER, description TEXT, maker TEXT, version INTEGER,
 customer_status TEXT, sol_status TEXT, sol_notes TEXT DEFAULT '', created TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS versions(
 doc_id TEXT, version INTEGER, filename TEXT, mime TEXT, content BLOB, sha256 TEXT,
 nominal INTEGER, token_hash TEXT UNIQUE, expires REAL, used_at TEXT, created TEXT,
 PRIMARY KEY(doc_id,version));
CREATE TABLE IF NOT EXISTS audit(
 id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id TEXT, version INTEGER, action TEXT,
 actor TEXT, notes TEXT, at TEXT, ip TEXT, agent TEXT);
CREATE TABLE IF NOT EXISTS outbox(
 id TEXT PRIMARY KEY, doc_id TEXT, version INTEGER, recipient TEXT, subject TEXT,
 body TEXT, status TEXT, attempts INTEGER DEFAULT 0, next_attempt REAL DEFAULT 0,
 error TEXT DEFAULT '', created TEXT, sent_at TEXT);
"""

def now():
    return datetime.now(timezone.utc).isoformat()

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    result = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 310000).hex()
    return salt + ':' + result

def password_matches(password, encoded):
    return hmac.compare_digest(password_hash(password, encoded.split(':')[0]), encoded)

@contextmanager
def database(write=False):
    connection = sqlite3.connect(DB_PATH, timeout=15)
    connection.row_factory = sqlite3.Row
    try:
        if write:
            connection.execute('BEGIN IMMEDIATE')
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def initialize():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with database() as db:
        db.executescript(SCHEMA)
    os.chmod(DB_PATH, 0o600)

def create_user(email, name, role, password):
    if role not in ('petugas', 'sol') or len(password) < 12:
        raise ValueError('Peran harus petugas/sol dan password minimal 12 karakter.')
    email = valid_email(email)
    with database(True) as db:
        db.execute('INSERT INTO users VALUES(?,?,?,?,?)', (secrets.token_hex(12), email, name, role, password_hash(password)))

def bootstrap_users():
    """Create both initial users atomically, only on an empty persistent DB.

    Environment values are never printed, returned by the API or used to reset
    existing passwords. Remove BOOTSTRAP_* secrets after the first deploy.
    """
    with database(True) as db:
        if db.execute('SELECT COUNT(*) FROM users').fetchone()[0]:
            return False
        values = []
        for role in ('petugas', 'sol'):
            prefix = 'BOOTSTRAP_' + role.upper()
            email = valid_email(os.getenv(prefix + '_EMAIL', ''))
            name = text_field({'name': os.getenv(prefix + '_NAME', '')}, 'name')
            password = os.getenv(prefix + '_PASSWORD', '')
            require(12 <= len(password) <= 500, f'{prefix}_PASSWORD harus 12–500 karakter.')
            require(not PRODUCTION or password not in ('PetugasDemo!2026', 'SolDemo!2026'), 'Password demo tidak boleh dipakai saat production.')
            values.append((secrets.token_hex(12), email, name, role, password_hash(password)))
        require(values[0][1] != values[1][1], 'Email petugas dan SOL harus berbeda.')
        db.executemany('INSERT INTO users VALUES(?,?,?,?,?)', values)
    return True

class AppError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message

def require(condition, message, status=400):
    if not condition:
        raise AppError(status, message)

def text_field(data, key, limit=250, required=True):
    value = data.get(key, '')
    require(isinstance(value, str), 'Format ' + key + ' tidak valid.')
    value = value.strip()
    require((bool(value) or not required) and len(value) <= limit, 'Isi ' + key + ' dengan benar.')
    require('\x00' not in value, 'Karakter tidak valid.')
    return value

def valid_email(email):
    require(isinstance(email, str) and len(email) <= 254 and bool(re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', email)), 'Alamat email tidak valid.')
    return email.strip().lower()

def secret_field(data, key):
    value = data.get(key)
    require(isinstance(value, str) and 0 < len(value) <= 500, 'Password tidak valid.')
    return value

def read_file(data):
    upload = data.get('file')
    require(isinstance(upload, dict), 'Unggah surat PDF, JPG, atau PNG.')
    name = text_field(upload, 'name', 150)
    require('/' not in name and '\\' not in name, 'Nama file tidak valid.')
    try:
        content = base64.b64decode(upload.get('base64', ''), validate=True)
    except (ValueError, TypeError):
        raise AppError(400, 'File tidak valid.')
    require(0 < len(content) <= MAX_FILE, 'Ukuran file maksimal 5 MB.')
    mime = 'application/pdf' if content.startswith(b'%PDF-') else 'image/png' if content.startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg' if content.startswith(b'\xff\xd8\xff') else None
    require(mime is not None, 'Format surat harus PDF, JPG, atau PNG yang valid.')
    return name, mime, content, hashlib.sha256(content).hexdigest()

def transaction_fields(data):
    kind = text_field(data, 'kind')
    nominal = data.get('nominal')
    require(kind in ('Standing Instruction', 'Warkat'), 'Jenis dokumen tidak valid.')
    require(type(nominal) is int and 0 < nominal <= 999999999999999, 'Nominal harus bilangan bulat positif, maksimal Rp 999.999.999.999.999.')
    return kind, nominal, text_field(data, 'description', 1500, False)

def add_audit(db, doc, action, actor, notes='', ip='', agent=''):
    db.execute('INSERT INTO audit(doc_id,version,action,actor,notes,at,ip,agent) VALUES(?,?,?,?,?,?,?,?)', (doc['id'], doc['version'], action, actor, notes, now(), ip, agent[:300]))

def enqueue(db, doc, upload, actor, ip, agent):
    token = secrets.token_urlsafe(32)
    stamp = now()
    expiry = time.time() + int(os.getenv('TOKEN_TTL_HOURS', '24')) * 3600
    db.execute('INSERT INTO versions VALUES(?,?,?,?,?,?,?,?,?,?,?)', (doc['id'], doc['version'], *upload, doc['nominal'], digest(token), expiry, None, stamp))
    amount = f"Rp {doc['nominal']:,}".replace(',', '.')
    subject = f"Konfirmasi {doc['kind']} • {doc['id']} • Versi {doc['version']}"
    body = f"""Yth. {doc['person']},

Mohon periksa dan konfirmasikan surat berikut:
Nasabah: {doc['customer_name']}
Dokumen: {doc['id']} (versi {doc['version']})
Jenis: {doc['kind']}
Nominal: {amount}

Buka halaman konfirmasi untuk melihat surat, lalu pilih Setujui atau Tolak:
{BASE_URL}/#confirm/{token}

Tautan berlaku {os.getenv('TOKEN_TTL_HOURS', '24')} jam dan hanya menerima satu keputusan. Membuka email atau tautan tidak memberikan persetujuan otomatis. Jangan teruskan tautan ini kepada pihak lain.

Jika detail tidak sesuai, pilih Tolak dan tuliskan alasan Anda. Persetujuan nasabah akan diperiksa kembali oleh SOL sebelum pengajuan disetujui.

{BANK_NAME}
"""
    db.execute('INSERT INTO outbox(id,doc_id,version,recipient,subject,body,status,created) VALUES(?,?,?,?,?,?,?,?)', (secrets.token_hex(16), doc['id'], doc['version'], doc['email'], subject, body, 'queued', stamp))
    add_audit(db, doc, 'Pengajuan dikirim untuk konfirmasi nasabah', actor, f"Email: {doc['email']} · {amount}", ip, agent)

def document_summary(db, row):
    doc = dict(row)
    maker = db.execute('SELECT name FROM users WHERE id=?', (doc['maker'],)).fetchone()
    doc['maker_name'] = maker['name'] if maker else 'Petugas'
    mail = db.execute('SELECT id,status,error,sent_at FROM outbox WHERE doc_id=? AND version=? ORDER BY created DESC LIMIT 1', (doc['id'], doc['version'])).fetchone()
    doc['mail'] = dict(mail) if mail else None
    version = db.execute('SELECT filename,mime,sha256,expires,used_at FROM versions WHERE doc_id=? AND version=?', (doc['id'], doc['version'])).fetchone()
    doc['file'] = dict(version) if version else None
    return doc

def owned_document(db, doc_id, user):
    doc = db.execute('SELECT * FROM documents WHERE id=?', (doc_id,)).fetchone()
    require(doc is not None, 'Pengajuan tidak ditemukan.', 404)
    require(user['role'] == 'sol' or doc['maker'] == user['id'], 'Anda tidak memiliki akses ke pengajuan ini.', 403)
    require(not db.execute('SELECT 1 FROM archived_documents WHERE doc_id=?', (doc_id,)).fetchone(), 'Pengajuan telah dihapus dari daftar. SOL dapat memulihkannya.', 404)
    return doc

def archive_document(db, doc, user, ip, agent):
    db.execute('INSERT INTO archived_documents VALUES(?,?,?)', (doc['id'], now(), user['id']))
    db.execute('UPDATE versions SET expires=0 WHERE doc_id=?', (doc['id'],))
    db.execute("UPDATE outbox SET status='cancelled' WHERE doc_id=? AND status IN ('queued','retry','failed')", (doc['id'],))
    add_audit(db, doc, 'SOL menghapus pengajuan dari daftar', user['name'] + ' (SOL)', 'Disimpan di arsip dan dapat dipulihkan. Tautan konfirmasi dinonaktifkan.', ip, agent)

def portal_document(db, token):
    require(isinstance(token, str) and 20 <= len(token) <= 100, 'Tautan konfirmasi tidak valid.', 404)
    version = db.execute('SELECT * FROM versions WHERE token_hash=?', (digest(token),)).fetchone()
    require(version is not None, 'Tautan konfirmasi tidak ditemukan.', 404)
    doc = db.execute('SELECT * FROM documents WHERE id=?', (version['doc_id'],)).fetchone()
    require(not db.execute('SELECT 1 FROM archived_documents WHERE doc_id=?', (doc['id'],)).fetchone(), 'Pengajuan sudah dihapus dari daftar.', 410)
    require(doc['sol_status'] != 'cancelled', 'Pengajuan telah dibatalkan oleh petugas.', 410)
    require(doc['version'] == version['version'], 'Surat telah direvisi. Gunakan tautan dari email terbaru.', 410)
    require(not version['used_at'], 'Keputusan Anda sudah tercatat. Tautan ini telah digunakan.', 410)
    require(version['expires'] > time.time(), 'Tautan telah kedaluwarsa. Hubungi petugas untuk meminta email baru.', 410)
    require(doc['customer_status'] == 'pending', 'Pengajuan ini tidak lagi menerima konfirmasi.', 409)
    return doc, version

def deliver_one():
    """Single worker. Stale leases retry after restart; SMTP is at-least-once."""
    with database(True) as db:
        row = db.execute("SELECT * FROM outbox WHERE status IN ('queued','retry','sending') AND next_attempt<=? ORDER BY created LIMIT 1", (time.time(),)).fetchone()
        if not row:
            return False
        doc = db.execute('SELECT * FROM documents WHERE id=?', (row['doc_id'],)).fetchone()
        version = db.execute('SELECT * FROM versions WHERE doc_id=? AND version=?', (row['doc_id'], row['version'])).fetchone()
        if not doc or db.execute('SELECT 1 FROM archived_documents WHERE doc_id=?', (row['doc_id'],)).fetchone() or doc['sol_status'] == 'cancelled' or doc['version'] != row['version'] or version['used_at'] or version['expires'] <= time.time():
            db.execute("UPDATE outbox SET status='cancelled' WHERE id=?", (row['id'],))
            return True
        db.execute("UPDATE outbox SET status='sending', attempts=attempts+1, next_attempt=? WHERE id=?", (time.time() + 120, row['id']))
    message = EmailMessage()
    message['Subject'] = row['subject']
    message['From'] = os.getenv('SMTP_FROM') or os.getenv('SMTP_USER') or 'BPIP <noreply@localhost>'
    message['To'] = row['recipient']
    message['Message-ID'] = f"<{row['id']}@{urlsplit(BASE_URL).hostname or 'localhost'}>"
    message.set_content(row['body'])
    try:
        if MAIL_MODE == 'console':
            folder = DB_PATH.parent / 'outbox'
            folder.mkdir(exist_ok=True, mode=0o700)
            target = folder / (row['id'] + '.eml')
            target.write_bytes(message.as_bytes())
            os.chmod(target, 0o600)
            status, action = 'local', 'Email tersedia di kotak email lokal (belum terkirim ke nasabah)'
        else:
            host = os.environ['SMTP_HOST']
            port = int(os.getenv('SMTP_PORT', '587'))
            tls = os.getenv('SMTP_TLS', 'starttls')
            smtp_class = smtplib.SMTP_SSL if tls == 'ssl' else smtplib.SMTP
            options = {'context': ssl.create_default_context()} if tls == 'ssl' else {}
            with smtp_class(host, port, timeout=20, **options) as client:
                if tls != 'ssl':
                    client.starttls(context=ssl.create_default_context())
                if os.getenv('SMTP_USER'):
                    client.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
                client.send_message(message)
            status, action = 'sent', 'Email diterima server SMTP'
        with database(True) as db:
            db.execute('UPDATE outbox SET status=?,sent_at=?,error=? WHERE id=?', (status, now(), '', row['id']))
            add_audit(db, doc, action, 'Sistem', f"Versi email {row['version']}")
    except Exception:
        logging.exception('Pengiriman email gagal; id=%s', row['id'])
        attempts = row['attempts'] + 1
        with database(True) as db:
            db.execute('UPDATE outbox SET status=?,next_attempt=?,error=? WHERE id=?', ('failed' if attempts >= 5 else 'retry', time.time() + min(3600, 30 * 2 ** attempts), 'Pengiriman gagal. Periksa konfigurasi SMTP dan log server.', row['id']))
    return True

def worker(stop):
    while not stop.is_set():
        try:
            deliver_one()
        except Exception:
            logging.exception('Outbox worker error')
        stop.wait(2)

class Handler(BaseHTTPRequestHandler):
    server_version = 'BPIP'

    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def log_message(self, fmt, *args):
        # Never log tokens, request bodies or customer data.
        logging.info('%s %s', self.command, urlsplit(self.path).path)

    def headers_common(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; connect-src 'self'; frame-src blob:; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        if PRODUCTION:
            self.send_header('Strict-Transport-Security', 'max-age=31536000')

    def respond(self, value, status=200, cookie=None):
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.headers_common()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        require(self.headers.get('Content-Type', '').split(';')[0] == 'application/json', 'Gunakan JSON.', 415)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            require(0 < length <= MAX_BODY, 'Permintaan terlalu besar atau kosong.', 413)
            data = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeError):
            raise AppError(400, 'JSON tidak valid.')
        require(isinstance(data, dict), 'Format JSON tidak valid.')
        return data

    def session(self, db, mutate=False):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
        except Exception:
            pass
        raw = cookie.get('bpip_session')
        row = db.execute('SELECT u.*,s.csrf,s.expires FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.hash=? AND s.expires>?', (digest(raw.value) if raw else '', time.time())).fetchone()
        require(row is not None, 'Sesi berakhir. Silakan masuk kembali.', 401)
        if mutate:
            require(hmac.compare_digest(self.headers.get('X-CSRF-Token', ''), row['csrf']), 'Token sesi tidak sesuai. Muat ulang halaman.', 403)
        return dict(row)

    def user_payload(self, user):
        return {key: user[key] for key in ('id', 'email', 'name', 'role')}

    def origin_check(self):
        origin = self.headers.get('Origin')
        require(not origin or origin == BASE_URL, 'Origin tidak diizinkan.', 403)
        require(self.headers.get('Sec-Fetch-Site') not in ('cross-site',), 'Permintaan lintas situs tidak diizinkan.', 403)

    def do_GET(self):
        try:
            self.get_route()
        except AppError as err:
            self.respond({'error': err.message}, err.status)
        except Exception:
            logging.exception('GET error')
            self.respond({'error': 'Terjadi kesalahan server.'}, 500)

    def get_route(self):
        path = urlsplit(self.path).path
        if path == '/api/config':
            return self.respond({'demo': DEMO, 'mail_mode': MAIL_MODE, 'bank_name': BANK_NAME})
        if path == '/api/session':
            with database() as db:
                user = self.session(db)
                return self.respond({'user': self.user_payload(user), 'csrf': user['csrf']})
        if path.startswith('/api/'):
            with database() as db:
                user = self.session(db)
                if path == '/api/customers':
                    return self.respond({'customers': [dict(r) for r in db.execute('SELECT * FROM customers ORDER BY name')]})
                if path == '/api/documents':
                    visible = 'NOT EXISTS (SELECT 1 FROM archived_documents a WHERE a.doc_id=documents.id)'
                    rows = db.execute('SELECT * FROM documents WHERE '+visible+' ORDER BY updated DESC') if user['role'] == 'sol' else db.execute('SELECT * FROM documents WHERE '+visible+' AND maker=? ORDER BY updated DESC', (user['id'],))
                    return self.respond({'documents': [document_summary(db, r) for r in rows], 'archived_count': db.execute('SELECT COUNT(*) FROM archived_documents').fetchone()[0] if user['role']=='sol' else 0})
                historic = re.fullmatch(r'/api/documents/([^/]+)/versions/([0-9]+)/file', path)
                if historic:
                    doc = owned_document(db, historic[1], user)
                    version = db.execute('SELECT * FROM versions WHERE doc_id=? AND version=?', (doc['id'], int(historic[2]))).fetchone()
                    require(version is not None, 'Versi surat tidak ditemukan.', 404)
                    return self.send_file(version)
                match = re.fullmatch(r'/api/documents/([^/]+)(/file)?', path)
                if match:
                    doc = owned_document(db, match[1], user)
                    if match[2]:
                        version = db.execute('SELECT * FROM versions WHERE doc_id=? AND version=?', (doc['id'], doc['version'])).fetchone()
                        return self.send_file(version)
                    result = document_summary(db, doc)
                    result['audit'] = [dict(r) for r in db.execute('SELECT * FROM audit WHERE doc_id=? ORDER BY id DESC', (doc['id'],))]
                    result['versions'] = [dict(r) for r in db.execute('SELECT version,filename,sha256,nominal,created FROM versions WHERE doc_id=? ORDER BY version DESC', (doc['id'],))]
                    return self.respond({'document': result})
                if path == '/api/outbox' and MAIL_MODE == 'console' and not PRODUCTION:
                    rows = db.execute('SELECT o.*,d.customer_name FROM outbox o JOIN documents d ON d.id=o.doc_id ORDER BY o.created DESC') if user['role'] == 'sol' else db.execute('SELECT o.*,d.customer_name FROM outbox o JOIN documents d ON d.id=o.doc_id WHERE d.maker=? ORDER BY o.created DESC', (user['id'],))
                    return self.respond({'messages': [dict(r) for r in rows]})
            raise AppError(404, 'Halaman tidak ditemukan.')
        allowed = {'/': 'index.html', '/index.html': 'index.html', '/css/main.css': 'css/main.css', '/js/app.js': 'js/app.js'}
        require(path in allowed, 'Halaman tidak ditemukan.', 404)
        file = ROOT / 'web' / allowed[path]
        body = file.read_bytes()
        self.send_response(200)
        self.headers_common()
        self.send_header('Content-Type', (mimetypes.guess_type(file)[0] or 'application/octet-stream') + '; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, version):
        self.send_response(200)
        self.headers_common()
        self.send_header('Content-Type', version['mime'])
        self.send_header('Content-Disposition', 'attachment; filename="surat-v' + str(version['version']) + ('.pdf' if version['mime'] == 'application/pdf' else '.png' if version['mime'] == 'image/png' else '.jpg') + '"')
        self.send_header('Content-Length', str(len(version['content'])))
        self.end_headers()
        self.wfile.write(version['content'])

    def do_POST(self):
        try:
            self.origin_check()
            data = self.body()
            self.post_route(urlsplit(self.path).path, data)
        except AppError as err:
            self.respond({'error': err.message}, err.status)
        except Exception:
            logging.exception('POST error')
            self.respond({'error': 'Terjadi kesalahan server. Silakan coba kembali.'}, 500)

    def post_route(self, path, data):
        ip, agent = self.client_address[0], self.headers.get('User-Agent', '')
        if path == '/api/login':
            email = text_field(data, 'email').lower()
            password = secret_field(data, 'password')
            with database(True) as db:
                db.execute('DELETE FROM login_attempts WHERE at<?', (time.time() - 900,))
                count = db.execute('SELECT COUNT(*) FROM login_attempts WHERE ip=? OR email=?', (ip, email)).fetchone()[0]
                require(count < 10, 'Terlalu banyak percobaan masuk. Coba lagi dalam 15 menit.', 429)
                user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
                dummy = '0' * 32 + ':' + '0' * 64
                ok = password_matches(password, user['password'] if user else dummy)
                if not user or not ok:
                    db.execute('INSERT INTO login_attempts VALUES(?,?,?)', (ip, email, time.time()))
                    db.commit()
                    raise AppError(401, 'Email atau password tidak sesuai.')
                db.execute('DELETE FROM login_attempts WHERE email=?', (email,))
                db.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
                raw, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
                db.execute('INSERT INTO sessions VALUES(?,?,?,?)', (digest(raw), user['id'], csrf, time.time() + SESSION_TTL))
                result = {'user': self.user_payload(user), 'csrf': csrf}
            cookie = f'bpip_session={raw}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_TTL}' + ('; Secure' if PRODUCTION else '')
            return self.respond(result, cookie=cookie)
        if path in ('/api/portal', '/api/portal/decision', '/api/portal/file'):
            with database(True) as db:
                doc, version = portal_document(db, data.get('token'))
                if path.endswith('/file'):
                    return self.send_file(version)
                if path.endswith('/decision'):
                    decision = data.get('decision')
                    require(decision in ('confirmed', 'rejected'), 'Keputusan tidak valid.')
                    require(data.get('acknowledged') is True, 'Periksa detail surat dan centang pernyataan terlebih dahulu.')
                    notes = text_field(data, 'notes', 1500, decision == 'rejected')
                    stamp = now()
                    db.execute('UPDATE versions SET used_at=? WHERE doc_id=? AND version=?', (stamp, doc['id'], doc['version']))
                    db.execute('UPDATE documents SET customer_status=?,updated=? WHERE id=?', (decision, stamp, doc['id']))
                    add_audit(db, doc, 'Nasabah menyetujui surat' if decision == 'confirmed' else 'Nasabah menolak surat', doc['person'] + ' (Nasabah)', notes + f" · Nominal Rp {doc['nominal']:,} · Pernyataan diperiksa dan disetujui", ip, agent)
                    db.commit()
                    return self.respond({'message': 'Keputusan Anda berhasil dicatat.', 'decision': decision})
                return self.respond({'document': {key: doc[key] for key in ('id', 'customer_name', 'person', 'kind', 'nominal', 'description', 'version', 'created')}, 'file': {'filename': version['filename'], 'mime': version['mime'], 'sha256': version['sha256']}, 'expires': version['expires']})
        with database(True) as db:
            user = self.session(db, True)
            if path == '/api/logout':
                db.execute('DELETE FROM sessions WHERE user_id=? AND csrf=?', (user['id'], user['csrf']))
                db.commit()
                return self.respond({'ok': True}, cookie='bpip_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0' + ('; Secure' if PRODUCTION else ''))
            if path == '/api/password':
                current = secret_field(data, 'current')
                password = secret_field(data, 'password')
                require(password_matches(current, user['password']), 'Password saat ini tidak sesuai.', 403)
                require(len(password) >= 12, 'Password baru minimal 12 karakter.')
                db.execute('UPDATE users SET password=? WHERE id=?', (password_hash(password), user['id']))
                db.execute('DELETE FROM sessions WHERE user_id=? AND csrf<>?', (user['id'], user['csrf']))
                db.commit()
                return self.respond({'ok': True})
            if path in ('/api/documents/archive-all', '/api/documents/restore-all'):
                require(user['role'] == 'sol', 'Hanya SOL yang dapat menghapus atau memulihkan pengajuan.', 403)
                if path.endswith('/archive-all'):
                    docs = list(db.execute('SELECT * FROM documents WHERE NOT EXISTS (SELECT 1 FROM archived_documents a WHERE a.doc_id=documents.id)'))
                    ids = data.get('ids')
                    require(isinstance(ids, list) and all(isinstance(i,str) for i in ids), 'Daftar pengajuan tidak valid.')
                    require(len(ids)==len(docs) and set(ids)=={d['id'] for d in docs}, 'Daftar pengajuan berubah. Muat ulang dan konfirmasi kembali.', 409)
                    for doc in docs:
                        archive_document(db, doc, user, ip, agent)
                else:
                    docs = list(db.execute('SELECT d.* FROM documents d JOIN archived_documents a ON a.doc_id=d.id'))
                    for doc in docs:
                        add_audit(db, doc, 'SOL memulihkan pengajuan', user['name']+' (SOL)', 'Tautan konfirmasi lama tetap tidak berlaku.', ip, agent)
                    db.execute('DELETE FROM archived_documents')
                db.commit()
                return self.respond({'ok':True,'count':len(docs)})
            if path == '/api/customers':
                require(user['role'] == 'sol', 'Hanya SOL yang dapat menambah nasabah.', 403)
                cif = text_field(data, 'cif', 30)
                require(re.fullmatch(r'[0-9]{3,30}', cif), 'CIF harus 3–30 digit.')
                account = text_field(data, 'account', 50)
                require(re.fullmatch(r'[0-9]{15}', account), 'Nomor rekening harus berupa tepat 15 digit angka.')
                values = (cif, text_field(data, 'name'), account, text_field(data, 'person'), valid_email(text_field(data, 'email')))
                require(not db.execute('SELECT 1 FROM customers WHERE cif=?', (cif,)).fetchone(), 'CIF sudah terdaftar.', 409)
                db.execute('INSERT INTO customers VALUES(?,?,?,?,?)', values)
                db.commit()
                return self.respond({'ok': True}, 201)
            if path == '/api/documents':
                require(user['role'] == 'petugas', 'Hanya petugas yang dapat membuat pengajuan.', 403)
                customer = db.execute('SELECT * FROM customers WHERE cif=?', (text_field(data, 'cif', 30),)).fetchone()
                require(customer is not None, 'Nasabah belum terdaftar.')
                kind, nominal, description = transaction_fields(data)
                upload = read_file(data)
                doc_id = ('SI' if kind == 'Standing Instruction' else 'WK') + '-' + datetime.now().strftime('%Y') + '-' + secrets.token_hex(4).upper()
                stamp = now()
                values = (doc_id, customer['cif'], customer['name'], customer['account'], customer['person'], customer['email'], kind, nominal, description, user['id'], 1, 'pending', 'pending', '', stamp, stamp)
                db.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', values)
                doc = db.execute('SELECT * FROM documents WHERE id=?', (doc_id,)).fetchone()
                enqueue(db, doc, upload, user['name'], ip, agent)
                db.commit()
                return self.respond({'id': doc_id}, 201)
            match = re.fullmatch(r'/api/documents/([^/]+)/(review|revise|resend|cancel|archive)', path)
            require(match is not None, 'Endpoint tidak ditemukan.', 404)
            doc = owned_document(db, match[1], user)
            operation = match[2]
            if operation == 'archive':
                require(user['role'] == 'sol', 'Hanya SOL yang dapat menghapus pengajuan.', 403)
                require(data.get('version') == doc['version'], 'Versi surat telah berubah. Muat ulang pengajuan.', 409)
                archive_document(db, doc, user, ip, agent)
            elif operation == 'cancel':
                require(user['role'] == 'petugas' and doc['maker'] == user['id'], 'Hanya petugas pembuat yang dapat membatalkan pengajuan.', 403)
                require(data.get('version') == doc['version'], 'Versi surat telah berubah. Muat ulang pengajuan.', 409)
                require(doc['sol_status'] in ('pending', 'revision_requested'), 'Pengajuan dengan keputusan akhir tidak dapat dibatalkan.', 409)
                notes = text_field(data, 'notes', 1500)
                db.execute("UPDATE documents SET sol_status='cancelled',updated=? WHERE id=?", (now(), doc['id']))
                db.execute('UPDATE versions SET expires=0 WHERE doc_id=?', (doc['id'],))
                db.execute("UPDATE outbox SET status='cancelled' WHERE doc_id=? AND status IN ('queued','retry','failed')", (doc['id'],))
                add_audit(db, doc, 'Petugas membatalkan pengajuan', user['name'], notes, ip, agent)
            elif operation == 'review':
                require(user['role'] == 'sol', 'Hanya SOL yang dapat memutuskan pengajuan.', 403)
                require(data.get('version') == doc['version'], 'Versi surat telah berubah. Muat ulang pengajuan.', 409)
                require(doc['customer_status'] in ('confirmed', 'rejected'), 'Tunggu respons nasabah sebelum melakukan review.', 409)
                require(doc['sol_status'] == 'pending', 'Pengajuan ini sudah direview.', 409)
                decision = data.get('decision')
                require(decision in ('approved', 'rejected', 'revision_requested'), 'Keputusan tidak valid.')
                require(decision != 'approved' or doc['customer_status'] == 'confirmed', 'SOL tidak dapat menyetujui surat yang ditolak nasabah.', 409)
                notes = text_field(data, 'notes', 1500, decision != 'approved')
                db.execute('UPDATE documents SET sol_status=?,sol_notes=?,updated=? WHERE id=?', (decision, notes, now(), doc['id']))
                add_audit(db, doc, {'approved': 'SOL menyetujui pengajuan', 'rejected': 'SOL menolak pengajuan', 'revision_requested': 'SOL meminta revisi surat'}[decision], user['name'] + ' (SOL)', notes, ip, agent)
            else:
                require(user['role'] == 'petugas' and doc['maker'] == user['id'], 'Hanya petugas pembuat yang dapat melakukan tindakan ini.', 403)
                require(data.get('version') == doc['version'], 'Versi surat telah berubah. Muat ulang pengajuan.', 409)
                if operation == 'revise':
                    require(doc['sol_status'] == 'revision_requested', 'Revisi hanya tersedia setelah diminta oleh SOL.', 409)
                    kind, nominal, description = transaction_fields(data)
                    upload = read_file(data)
                    notes = text_field(data, 'notes', 1500)
                    db.execute("UPDATE documents SET kind=?,nominal=?,description=?,version=version+1,customer_status='pending',sol_status='pending',sol_notes='',updated=? WHERE id=?", (kind, nominal, description, now(), doc['id']))
                else:
                    require(doc['customer_status'] == 'pending' and doc['sol_status'] == 'pending', 'Email baru hanya dapat dikirim saat menunggu nasabah.', 409)
                    previous = db.execute('SELECT * FROM versions WHERE doc_id=? AND version=?', (doc['id'], doc['version'])).fetchone()
                    latest_mail = db.execute('SELECT created FROM outbox WHERE doc_id=? ORDER BY created DESC LIMIT 1', (doc['id'],)).fetchone()
                    require(time.time() - datetime.fromisoformat(latest_mail['created']).timestamp() >= 60, 'Tunggu satu menit sebelum mengirim email baru.', 429)
                    upload = (previous['filename'], previous['mime'], previous['content'], previous['sha256'])
                    notes = 'Tautan sebelumnya dibatalkan. Email baru diterbitkan.'
                    db.execute('UPDATE documents SET version=version+1,updated=? WHERE id=?', (now(), doc['id']))
                db.execute("UPDATE outbox SET status='cancelled' WHERE doc_id=? AND status IN ('queued','retry','failed')", (doc['id'],))
                doc = db.execute('SELECT * FROM documents WHERE id=?', (doc['id'],)).fetchone()
                add_audit(db, doc, 'Petugas mengunggah revisi surat' if operation == 'revise' else 'Petugas meminta email konfirmasi baru', user['name'], notes, ip, agent)
                enqueue(db, doc, upload, user['name'], ip, agent)
            db.commit()
            return self.respond({'ok': True, 'id': doc['id']})

def seed_demo():
    with database() as db:
        if db.execute('SELECT COUNT(*) FROM users').fetchone()[0]:
            return
    create_user('petugas@bpip.local', 'Rina Wulandari', 'petugas', 'PetugasDemo!2026')
    create_user('sol@bpip.local', 'Bambang Haryanto', 'sol', 'SolDemo!2026')
    with database(True) as db:
        db.executemany('INSERT INTO customers VALUES(?,?,?,?,?)', [
            ('1234567', 'PT Maju Bersama', '001234567890', 'Budi Santoso', 'budi@example.com'),
            ('9876543', 'CV Karya Mandiri', '002987654321', 'Ahmad Fadli', 'ahmad@example.com'),
            ('5551234', 'PT Sentra Niaga Global', '003555123456', 'Dewi Lestari', 'dewi@example.com')])

def validate_config():
    require(MAIL_MODE in ('console', 'smtp'), 'MAIL_MODE harus console atau smtp.')
    parsed = urlsplit(BASE_URL)
    require(parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.path and not parsed.query and not parsed.fragment, 'PUBLIC_BASE_URL harus origin tanpa path.')
    require(int(os.getenv('TOKEN_TTL_HOURS', '24')) in range(1, 169), 'Masa berlaku token 1–168 jam.')
    if MAIL_MODE == 'smtp':
        require(bool(os.getenv('SMTP_HOST')) and bool(os.getenv('SMTP_FROM') or os.getenv('SMTP_USER')), 'SMTP_HOST dan alamat pengirim (SMTP_USER atau SMTP_FROM) wajib diisi.')
        require(os.getenv('SMTP_TLS', 'starttls') in ('starttls', 'ssl'), 'SMTP wajib menggunakan starttls atau ssl.')
        require(not os.getenv('SMTP_USER') or bool(os.getenv('SMTP_PASSWORD')), 'SMTP_PASSWORD wajib untuk SMTP_USER.')
    if PRODUCTION:
        require(parsed.scheme == 'https' and MAIL_MODE == 'smtp', 'Production wajib HTTPS dan SMTP.')
        with database() as db:
            for user in db.execute('SELECT password FROM users'):
                require(not any(password_matches(p, user['password']) for p in ('PetugasDemo!2026', 'SolDemo!2026')), 'Ganti seluruh password demo sebelum production.')

def main():
    global DEMO
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', choices=('serve', 'init'), default='serve')
    parser.add_argument('--demo', action='store_true', help='Akun demo untuk pengujian lokal, tanpa email nyata.')
    args = parser.parse_args()
    initialize()
    if args.command == 'init':
        for role in ('petugas', 'sol'):
            print(f'Buat akun {role}')
            create_user(input('Email: ').strip(), input('Nama: ').strip(), role, getpass.getpass('Password (min. 12 karakter): '))
        print('Akun berhasil dibuat.')
        return
    if args.demo:
        require(not PRODUCTION and MAIL_MODE == 'console', 'Mode demo hanya untuk development dengan email lokal.')
        seed_demo()
        DEMO = True
    validate_config()
    with database() as db:
        require(db.execute('SELECT COUNT(*) FROM users').fetchone()[0] > 0, 'Buat akun dengan python3 server.py init atau gunakan --demo.')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    stop = threading.Event()
    threading.Thread(target=worker, args=(stop,), daemon=True).start()
    server = ThreadingHTTPServer((os.getenv('HOST', '127.0.0.1'), int(os.getenv('PORT', '8000'))), Handler)
    server.daemon_threads = True
    print(f'BPIP berjalan: {BASE_URL} | Email: {MAIL_MODE}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()

if __name__ == '__main__':
    try:
        main()
    except (AppError, ValueError, sqlite3.IntegrityError) as err:
        raise SystemExit(getattr(err, 'message', str(err)))
