# Upload GitHub dan deployment

Source dapat disimpan di GitHub. Aplikasi membutuhkan proses backend Python dan disk persisten; GitHub Pages saja tidak menjalankan login, database, konfirmasi, atau SMTP.

## Isi repository

Upload source, `.env.example`, dokumentasi, dan tes. `.gitignore` mengecualikan `.env`, database, email lokal, cache dan virtual environment. Data demo pada `data/` tidak ikut. `prototype-original/` menyimpan versi awal proyek.

## Deployment Docker

Gunakan host Docker Linux di belakang ingress HTTPS. Image menjalankan Gunicorn satu worker dengan empat thread dan satu worker email. Versi dependency dipin pada `requirements.txt`. Referensi: [Gunicorn settings](https://gunicorn.org/reference/settings/), [Gunicorn package](https://pypi.org/project/gunicorn/26.2.0/).

```sh
docker build -t bpip .
docker volume create bpip-data
```

Siapkan `.env` khusus deployment pada host, tanpa commit ke GitHub:

```dotenv
APP_ENV=production
HOST=0.0.0.0
PORT=8000
DATABASE_PATH=/data/bpip.sqlite3
PUBLIC_BASE_URL=https://konfirmasi.domain-anda.com
MAIL_MODE=smtp
SMTP_HOST=smtp.penyedia-anda.com
SMTP_PORT=587
SMTP_TLS=starttls
SMTP_USER=akun-pengirim
SMTP_PASSWORD=rahasia-smtp
SMTP_FROM=BPIP <konfirmasi@domain-anda.com>
```

Buat akun sendiri di database volume sebelum menjalankan layanan:

```sh
docker run --rm -it --env-file .env -v bpip-data:/data bpip python server.py init
docker run -d --name bpip --restart unless-stopped --env-file .env -p 127.0.0.1:8000:8000 -v bpip-data:/data bpip
```

Pasang reverse proxy/ingress HTTPS ke port 8000. Host platform container dapat mengatur routing ini sendiri. Volume `/data` harus persisten dan dapat ditulis UID 10001. SQLite perlu filesystem lokal yang mendukung locking, bukan volume object storage. Jangan menaikkan jumlah replica/worker tanpa memisahkan database dan worker email terlebih dahulu.

Jika hosting menyediakan Python tanpa Docker:

```sh
pip install -r requirements.txt
python server.py init
gunicorn --config gunicorn.conf.py wsgi:application
```

Gunicorn digunakan pada Linux/Unix. Set `DATABASE_PATH` ke disk persisten milik hosting. Set environment variables langsung pada dashboard hosting; jangan menyimpan rahasia di repository. `PUBLIC_BASE_URL` harus sama persis dengan origin HTTPS pengguna. Health check: `GET /api/config`.

## Pemeriksaan setelah deploy

1. Masuk dengan akun sendiri dan tambahkan nasabah uji yang Anda kuasai.
2. Kirim surat uji. Periksa SMTP, tautan HTTPS, dan keputusan nasabah.
3. Uji review SOL, revisi, tautan lama, dan audit trail.
4. Restart layanan dan pastikan akun, surat, audit dan antrean email bertahan.
5. Atur backup SQLite konsisten, pemantauan, batas request 8 MB, rate limit dan akses operasional. Baca batas keamanan di README sebelum menggunakan data nasabah nyata.

Repository, domain, layanan SMTP dan hosting perlu disiapkan pada akun Anda. Dokumen ini tidak menyatakan deployment atau pengiriman email nyata sudah dilakukan.
