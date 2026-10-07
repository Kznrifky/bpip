# BPIP — Document Confirmation

Aplikasi web untuk pengajuan petugas, konfirmasi surat melalui email, dan keputusan SOL. Backend Python + SQLite; frontend HTML/CSS/JavaScript. Python 3.10+; mode lokal tidak memerlukan npm atau dependency Python tambahan. Deployment menggunakan Gunicorn melalui `requirements.txt`; lihat `DEPLOY.md`.

## Jalankan dan coba

```sh
cd /Users/kznrifky/Documents/BPIP
python3 server.py --demo
```

Buka **http://localhost:8000**. Jalankan melalui server ini, bukan dengan membuka `web/index.html` langsung atau Live Server.

Akun lokal petugas: `petugas@bpip.local`, password `PetugasDemo!2026`.
Akun lokal SOL: `sol@bpip.local`, password `SolDemo!2026`.

1. Masuk sebagai petugas. Buka Pengajuan baru.
2. Pilih CIF `1234567`, masukkan nominal `250000000`, dan unggah `docs/surat-demo.pdf`.
3. Centang pernyataan pemeriksaan lalu kirim konfirmasi.
4. Buka Kotak email lokal. Buka halaman konfirmasi nasabah di tab baru.
5. Periksa surat; centang pernyataan dan pilih Setujui/Tolak. Penolakan memerlukan alasan.
6. Keluar dari akun petugas lalu masuk sebagai SOL. Buka Antrean review dan pengajuan tersebut.
7. Pilih Approval, Tolak, atau Minta revisi surat. Catatan wajib untuk penolakan/revisi.
8. Jika diminta revisi, masuk sebagai petugas. Buka pengajuan, pilih Unggah revisi surat, isi ringkasan perbaikan, lalu unggah surat terbaru.
9. Nasabah mendapatkan tautan baru. Versi sebelumnya tetap di riwayat, tetapi tautannya tidak dapat digunakan.

Data tersimpan pada `data/bpip.sqlite3` dan bertahan saat server dimatikan. Akun/data demo hanya dibuat ketika database belum memiliki akun. Mengaktifkan `--demo` pada database yang sudah berisi akun tidak mengubah password akun tersebut. Prototipe awal disimpan di `prototype-original/`.

## Perilaku aplikasi

- Petugas melihat dan memperbaiki pengajuan miliknya. SOL melihat seluruh pengajuan. Pembatasan akses diberlakukan oleh backend.
- Nasabah tidak membutuhkan akun web; akses melalui token acak 256 bit, berumur 24 jam dan sekali keputusan. Pembukaan email/tautan tidak memberikan persetujuan otomatis.
- Konfirmasi nasabah dan keputusan SOL merupakan dua status yang berbeda. Nasabah setuju belum berarti pengajuan telah disetujui SOL.
- SOL dapat mereview setelah nasabah setuju **atau menolak**. Approval hanya tersedia setelah nasabah setuju. Penolakan nasabah dapat ditutup dengan penolakan SOL atau ditindaklanjuti dengan revisi.
- Revisi mengunggah surat baru, menyimpan versi lama, membatalkan tautan sebelumnya, dan meminta konfirmasi nasabah ulang. Keputusan akhir SOL tidak dapat diedit.
- Kirim tautan baru tersedia saat menunggu nasabah, dengan jeda minimum satu menit. Tautan lama dibatalkan. Penerbitan tautan baru menggunakan nomor versi berikutnya untuk mengikat token ke snapshot surat.
- Email antrean diproses worker setiap dua detik. Kegagalan mencoba ulang dengan jeda bertambah, maksimal lima percobaan. Status `sent` berarti diterima server SMTP, bukan bukti email dibaca atau masuk inbox. SMTP tidak menjamin pengiriman tepat satu kali; retry setelah koneksi terputus dapat menghasilkan email duplikat, tetapi keputusan nasabah tetap hanya sekali.
- Dashboard disinkronkan setiap sepuluh detik. Filter pencarian, jenis surat dan status tersedia. Jika catatan SOL sedang diisi, detail tidak ditimpa otomatis; gunakan tombol Perbarui setelah selesai.
- Surat PDF/JPG/PNG maksimal 5 MB disimpan di database bersama hash SHA-256. Audit merekam waktu UTC, versi, aktor, catatan, nominal, IP koneksi dan user agent. Tampilan waktu menggunakan Asia/Jakarta.
- Sesi delapan jam, cookie HttpOnly/SameSite, CSRF, hash password PBKDF2, pembatasan percobaan login, dan token tersimpan sebagai hash pada tabel versi. Email outbox mengandung tautan mentah yang diperlukan untuk pengiriman; lindungi database dan backup.

## Email sungguhan

Salin `.env.example` ke `.env` dan isi konfigurasi layanan pengirim Anda. Jangan commit `.env` atau mengirim rahasia melalui chat.

```dotenv
MAIL_MODE=smtp
SMTP_HOST=smtp.penyedia-anda.com
SMTP_PORT=587
SMTP_TLS=starttls
SMTP_USER=akun-smtp
SMTP_PASSWORD=password-atau-app-password
SMTP_FROM=BPIP <konfirmasi@domain-anda.com>
PUBLIC_BASE_URL=https://konfirmasi.domain-anda.com
BANK_NAME=Nama institusi Anda
```

Untuk SMTP TLS langsung: `SMTP_PORT=465`, `SMTP_TLS=ssl`. TLS wajib dan sertifikat diperiksa. Gunakan domain/alamat pengirim yang sudah diverifikasi oleh layanan SMTP. Restart server setelah mengubah `.env`. Jangan gunakan `--demo` dalam mode SMTP.

**Tautan localhost hanya dapat dibuka pada komputer yang menjalankan server.** Untuk nasabah pada perangkat lain, pasang aplikasi pada hosting yang dapat diakses dan atur `PUBLIC_BASE_URL` ke domain HTTPS itu. Origin akses harus sama persis dengan `PUBLIC_BASE_URL`, termasuk port. `http://localhost:8000` dan `http://127.0.0.1:8000` merupakan origin berbeda.

Mode lokal `MAIL_MODE=console` menyimpan email di `data/outbox/*.eml`, yang hanya dapat dibuka melalui kotak email lokal bagi pengguna internal. Mode SMTP tidak mengekspos tautan/email mentah lewat endpoint kotak email lokal. Mode lokal tidak mengirim email ke luar.

## Akun sendiri

Gunakan database terpisah untuk data nyata, misalnya `DATABASE_PATH=data/operasional.sqlite3` di `.env`, lalu:

```sh
python3 server.py init
python3 server.py
```

Perintah `init` meminta email, nama dan password untuk petugas dan SOL. Password minimal 12 karakter dan tidak ditampilkan saat diketik. Hanya SOL yang dapat menambahkan nasabah melalui menu Data nasabah. Petugas memilih nasabah yang sudah didaftarkan SOL untuk membuat pengajuan. Data demo menggunakan `example.com`, sehingga harus diganti dengan data master yang diverifikasi untuk pengiriman nyata. Setiap pengajuan menyimpan snapshot data nasabah, bukan bergantung pada perubahan data master berikutnya.

Password dapat diganti di menu Pengaturan akun. Sesi lain dicabut setelah perubahan password.

## Hosting dan batas operasional

Hasil ini merupakan aplikasi MVP yang berjalan lokal dengan backend lengkap untuk alur di atas. Server menggunakan `http.server` Python; **jangan mengekspos port server secara langsung sebagai layanan produksi perbankan**. Sebelum penggunaan operasional, gunakan ingress/reverse proxy HTTPS dengan pembatasan ukuran body (8 MB), rate limit, timeout dan akses terkontrol; gunakan entrypoint Gunicorn yang tersedia di `wsgi.py` dan ikuti `DEPLOY.md`. Review keamanan aplikasi tetap diperlukan sesuai standar institusi. Data CIF saat ini dikelola di aplikasi, belum terintegrasi dengan core banking.

- Atur `APP_ENV=production`, `PUBLIC_BASE_URL=https://...`, dan `MAIL_MODE=smtp`.
- Mode production menolak password demo, email lokal dan URL non-HTTPS; menggunakan cookie Secure dan HSTS. Jangan menggunakan akun demo untuk data nyata.
- Jalankan satu proses aplikasi dan satu worker terhadap database yang disimpan pada disk persisten. Default bind `HOST=127.0.0.1`; biarkan hanya reverse proxy lokal yang mengakses port 8000.
- Jalankan sebagai user layanan tanpa hak administrator; batasi akses direktori `data/` dan `.env`. Siapkan backup SQLite konsisten, disk encryption, retensi data dan pemantauan kegagalan email sesuai kebijakan institusi.
- IP audit saat di belakang reverse proxy adalah IP koneksi proxy. Header `X-Forwarded-For` sengaja tidak dipercaya tanpa konfigurasi proxy tepercaya. Identitas nasabah pada audit merupakan penerima tautan, bukan verifikasi identitas tambahan/OTP atau tanda tangan digital tersertifikasi.
- Audit aplikasi belum memiliki penyimpanan eksternal tahan perubahan, scanner malware, SSO/MFA, API core banking, tracking delivery webhook, maupun bukti pembacaan email. Lakukan review keamanan dan kebijakan persetujuan institusi sebelum menangani surat nasabah nyata.

Konfigurasi, domain dan kredensial SMTP/hosting belum tersedia dalam proyek ini; pengiriman nyata dan deployment belum dilakukan.

## Pengujian

```sh
python3 -m unittest discover -s tests -v
node --check web/js/app.js
```

Tes menggunakan server HTTP sementara dan database terpisah. Mencakup alur revisi/approval, penolakan nasabah, RBAC/ownership, CSRF/origin, validasi nominal/file, tautan kedaluwarsa dan pembatalan token, dua keputusan bersamaan, persistensi, outbox lokal, SMTP dengan mock, retry gagal, password/sesi dan limit login. Tidak mengirim email nyata. Surat contoh yang disediakan hanya untuk pengujian.

Nomor rekening untuk nasabah baru harus terdiri dari tepat 15 digit, termasuk nol di depan. Petugas dapat membatalkan pengajuannya sendiri selama belum disetujui atau ditolak SOL, termasuk saat diminta revisi. Alasan wajib dicatat; surat dan audit dipertahankan, tautan nasabah dinonaktifkan, serta email yang belum diproses dibatalkan. Email yang sedang dikirim atau sudah terkirim tidak dapat ditarik kembali.

SOL dapat menghapus satu pengajuan lewat halaman detail, atau semua pengajuan lewat Antrean review → Hapus semua pengajuan. Tindakan ini mengosongkan daftar bagi SOL dan petugas dengan memindahkan pengajuan ke arsip. Akun, data nasabah, surat, dan audit tetap tersimpan. Tombol Pulihkan pengajuan mengembalikan seluruh arsip ke daftar; tautan nasabah lama tetap tidak berlaku. Untuk pengajuan yang masih menunggu nasabah, petugas dapat meminta tautan baru. Penghapusan meminta konfirmasi dan tidak menjalankan pengiriman email baru.

Pencarian nama nasabah atau CIF tersedia pada tabel Data nasabah (SOL) dan formulir Pengajuan baru (petugas). SOL dapat menghapus nasabah dari daftar dan memulihkannya; nasabah yang dihapus tidak dapat dipilih untuk pengajuan baru. Pengajuan lama menggunakan snapshot sehingga surat, konfirmasi, dan revisinya tetap tersedia.

### Arsip dan pemantauan BOH

SOL menghapus nasabah/pengajuan ke arsip dengan password akun yang sedang login. Tombol Pulihkan membuka daftar arsip untuk pemulihan per data. Hapus permanen hanya tersedia di arsip, memerlukan password SOL serta CIF/ID yang diketik ulang. Penghapusan master nasabah mempertahankan snapshot surat dan pengajuan lama. Penghapusan permanen pengajuan menghapus dokumen, semua file versinya, dan antrean email; catatan audit tetap disimpan. Tautan lama tidak diaktifkan kembali saat pemulihan.

Akun BOH yang sudah tersedia dapat login melalui halaman masuk. Pembuatan akun BOH melalui SOL sudah dinonaktifkan. BOH hanya dapat membaca ringkasan dashboard semua pengajuan dan mengelola password akun sendiri. API BOH menolak akses master nasabah, surat, audit detail, email, dan semua tindakan operasional.
