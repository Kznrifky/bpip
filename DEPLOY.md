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

## Render (pilihan proyek ini)

Repository memiliki `render.yaml` untuk satu Web Service Python di Singapore, disk persisten 1 GB pada `/var/data`, Gunicorn dan health check `/api/config`. Paket layanan ini berbayar; biaya server dan disk harus ditinjau pada dashboard sebelum membuat layanan. Auto-deploy dimatikan agar setiap release dipicu manual setelah pengujian.

1. Login ke Render dan pilih **New → Blueprint**.
2. Hubungkan repository `Kznrifky/bpip`, branch `main`, dan gunakan `render.yaml`.
3. Tinjau region, paket server dan disk beserta biaya yang ditampilkan.
4. Isi seluruh variabel yang diminta dengan `sync: false` langsung di Render. Jangan menaruh rahasia di GitHub atau chat.
5. Masukkan konfigurasi SMTP milik Anda dan alamat pengirim yang sudah diverifikasi. Default port 587/STARTTLS; jika penyedia menggunakan 465/SSL, ubah `SMTP_PORT` dan `SMTP_TLS` pada service sebelum deploy.
6. Isi nama, email dan password petugas/SOL pada `BOOTSTRAP_*`. Password minimal 12 karakter; email kedua akun harus berbeda. Akun akan dibuat secara atomik hanya saat database masih kosong. Akun demo tidak dipakai.
7. Setelah deployment pertama berhasil dan login kedua akun sudah diperiksa, hapus keenam variabel `BOOTSTRAP_PETUGAS_*`/`BOOTSTRAP_SOL_*`, lalu set `BOOTSTRAP_USERS=0`. Jangan menghapus disk. Variabel bootstrap tidak mengubah akun yang sudah tersimpan.
8. URL email otomatis menggunakan `RENDER_EXTERNAL_URL` yang disediakan Render. Jika menggunakan domain sendiri, atur `PUBLIC_BASE_URL=https://domain-anda` dan akses aplikasi melalui origin yang sama.
9. Uji email pada alamat uji milik Anda, keputusan nasabah, review SOL dan revisi. Jangan mulai memakai data nasabah nyata sebelum review keamanan dan backup disiapkan.

Database dibuat saat runtime karena persistent disk Render tidak tersedia pada build/pre-deploy/one-off job. Dengan demikian tidak perlu menjalankan `server.py init` sebagai build command. Native Python dipilih untuk menghindari kebutuhan pengaturan ownership mount Docker; Dockerfile tetap tersedia untuk host lain. Health check dapat lolos hanya setelah worker berhasil memvalidasi konfigurasi dan akun awal.

Referensi: [Blueprint specification](https://render.com/docs/blueprint-spec), [Persistent disks](https://render.com/docs/disks), [Default environment variables](https://render.com/docs/environment-variables).
