import os
import threading

bind = f"{os.getenv('HOST', '0.0.0.0')}:{int(os.getenv('PORT', '8000'))}"
# One SQLite writer and one email worker; do not scale processes/replicas yet.
workers = 1
threads = 4
worker_class = 'gthread'
timeout = 60
graceful_timeout = 30
accesslog = None  # Avoid logging identifiers and confirmation URLs.
errorlog = '-'
capture_output = True


def post_worker_init(worker):
    import server
    server.initialize()
    server.validate_config()
    # Render disks are unavailable to build/pre-deploy commands. Bootstrap at
    # runtime, with secrets supplied in the dashboard, when explicitly enabled.
    if os.getenv('BOOTSTRAP_USERS') == '1':
        server.bootstrap_users()
    server.validate_config()
    with server.database() as db:
        server.require(db.execute('SELECT COUNT(*) FROM users').fetchone()[0] > 0,
                       'Buat akun dahulu menggunakan python server.py init.')
    worker.bpip_stop = threading.Event()
    worker.bpip_thread = threading.Thread(target=server.worker, args=(worker.bpip_stop,), daemon=True)
    worker.bpip_thread.start()


def worker_exit(server, worker):
    if hasattr(worker, 'bpip_stop'):
        worker.bpip_stop.set()
        worker.bpip_thread.join(timeout=25)
