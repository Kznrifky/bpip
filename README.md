# BRI VISTA

Verification, Integration & Secure Tracking Application

Aplikasi web untuk pengajuan petugas, konfirmasi surat melalui email, dan keputusan SOL. Backend Python + SQLite; frontend HTML/CSS/JavaScript. Python 3.10+; mode lokal tidak memerlukan npm. Ekspor PDF menggunakan ReportLab dan pypdf. Deployment menggunakan Gunicorn melalui `requirements.txt`; lihat `DEPLOY.md`.

## Jalankan dan coba

```sh
cd /Users/kznrifky/Documents/BPIP
python3 -m pip install -r requirements.txt
python3 server.py --demo
```

Buka **http://localhost:8000**. Jalankan melalui server ini, bukan dengan membuka `web/index.html` langsung atau Live Server.

Akun lokal petugas: `petugas@bpip.local`, password `PetugasDemo!2026`.
Akun lokal SOL: `sol@bpip.local`, password `SolDemo!2026`.

1. Masuk sebagai petugas. Buka Pengajuan baru.
2. Pilih CIF `1234567`, masukkan nominal `250000000`, rekening tujuan `000123456789012`, atas nama `PT Tujuan Pembayaran`, dan unggah `docs/surat-demo.pdf`.
3. Centang pernyataan pemeriksaan lalu kirim konfirmasi.
4. Buka Kotak email lokal. Buka halaman konfirmasi nasabah di tab baru.
5. Periksa surat; centang pernyataan dan pilih Setujui/Tolak. Penolakan memerlukan alasan.
6. Keluar dari akun petugas lalu masuk sebagai SOL. Klik baris pengajuan untuk membuka detail dan surat.
7. Pilih Setujui atau Tolak. Catatan wajib untuk penolakan.
8. Pengajuan selesai atau ditolak masuk History; gunakan filter Berhasil/Ditolak. Dokumen pelaksanaan dapat diunduh setelah nasabah dan SOL menyetujui.


Data tersimpan pada `data/bpip.sqlite3` dan bertahan saat server dimatikan. Akun/data demo hanya dibuat ketika database belum memiliki akun. Mengaktifkan `--demo` pada database yang sudah berisi akun tidak mengubah password akun tersebut. Prototipe awal disimpan di `prototype-original/`.

## Perilaku aplikasi

- Semua Officer melihat daftar pengajuan dan history bersama. Nama pengaju ditampilkan di halaman detail; daftar tetap ringkas tanpa kolom Pengaju. Hanya Officer pembuat yang dapat mengirim konfirmasi dan menerbitkan ulang link pengajuannya. Officer, SOL, dan BOH membuka detail dengan klik baris pengajuan. BOH membaca detail dan surat tanpa tindakan operasional. Pembatasan tindakan diberlakukan oleh backend.
- Nasabah tidak membutuhkan akun web; akses melalui token acak 256 bit, berumur 24 jam dan sekali keputusan. Pembukaan email/tautan tidak memberikan persetujuan otomatis.
- Dashboard dan Pengajuan hanya menampilkan pengajuan yang masih diproses. Persetujuan nasabah dan SOL masuk History sebagai Berhasil; penolakan salah satunya masuk sebagai Ditolak. Pengajuan lama yang dibatalkan tetap tersimpan dalam kelompok Ditolak; filter pembatalan tidak tersedia. Standing Instruction dan Warkat mengikuti aturan yang sama; angka KPI dan antrean hanya menghitung pengajuan aktif. Data, surat, dan audit tetap tersimpan.
- Konfirmasi nasabah dan keputusan SOL merupakan dua status yang berbeda. Nasabah setuju belum berarti pengajuan telah disetujui SOL.
- SOL hanya dapat menyetujui atau menolak setelah nasabah menyetujui surat. Penolakan nasabah langsung masuk History dan menghentikan alur persetujuan. Backend tetap mengizinkan SOL mencatat penolakan penutup pada data lama yang ditolak nasabah.
- Permintaan revisi dan pembatalan Officer dinonaktifkan pada UI dan API. Pengajuan lama yang menunggu revisi dapat diselesaikan SOL dengan Setujui/Tolak; file dan audit lamanya tetap tersimpan. Keputusan akhir SOL tidak dapat diedit.
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

Password dapat diganti di menu Pengaturan. Sesi lain dicabut setelah perubahan password.

### Role IT dan persetujuan akun Officer

IT membuka **Kelola Akun → Ajukan akun Officer**, mengisi nama, email, serta kata sandi awal minimal 12 karakter. Akun belum dapat login selama statusnya **Menunggu BOH**. BOH membuka **Persetujuan Akun → Periksa** dan memilih **Setujui akun** atau **Tolak** dengan alasan. Persetujuan membuat akun dengan role Officer; penolakan tidak membuat akun. Keputusan hanya dapat diberikan sekali dan email yang sedang menunggu tidak dapat diajukan dua kali.

IT memilih **Edit** pada daftar **Akun Officer Aktif**, lalu mengajukan nama baru ke BOH. Nama lama tetap berlaku sampai BOH menyetujui perubahan. Perubahan mempertahankan email, kata sandi, role, ID akun, dan kepemilikan pengajuan. Nama baru muncul pada sesi Officer saat data diperbarui dan pada kolom Pengaju. Pembuatan, keputusan BOH, serta perubahan nama dicatat dalam audit pengelolaan. API pengelolaan tidak mengembalikan kata sandi atau hash; hash sementara hanya disimpan sampai pengajuan diputuskan.

IT memilih **Hapus**, mengisi alasan, lalu mengajukan penghapusan ke BOH. Akun tetap aktif selama menunggu. Persetujuan BOH menonaktifkan akun dan mencabut seluruh sesinya, sehingga akun tidak dapat login lagi. ID, nama akun, data pengajuan, surat, dan riwayat tetap tersimpan. Akun hilang dari daftar Officer aktif; emailnya tetap tercatat dan tidak dapat digunakan untuk membuat akun pengganti. Pengajuan perubahan nama dan penghapusan pada akun yang sama tidak dapat menunggu bersamaan. Penolakan BOH wajib disertai catatan dan mempertahankan akun.

IT memiliki akses pengelolaan akun Officer dan kata sandi sendiri. Role ini tidak memiliki akses data nasabah, transaksi, surat, laporan PDF, atau antrean email. SOL dan Officer tidak dapat mengajukan atau memutuskan pengelolaan akun. BOH memutuskan pengajuan akun baru, perubahan nama, dan penghapusan dari IT; BOH tidak membuat akun langsung. Startup menambahkan status aktif pada akun lama tanpa mengganti ID, nama, maupun kata sandi.

Administrator menyiapkan akun IT pertama melalui terminal pada database yang dituju:

```sh
python3 server.py create-user --role it
```

Perintah meminta email, nama, dan kata sandi yang tidak ditampilkan saat diketik. Akun BOH awal juga dapat disiapkan dengan `--role boh`. Perintah ini tidak mengubah akun yang sudah ada; jangan menjalankannya tanpa memastikan database yang dituju. Fitur tidak membuat akun IT atau BOH produksi secara otomatis saat startup.

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
node --test tests/test_submission_lists.js
node --check web/js/app.js
```

Tes menggunakan server HTTP sementara dan database terpisah. Mencakup alur approval/penolakan, pemisahan daftar aktif dan History, penonaktifan revisi/pembatalan, penolakan nasabah, RBAC/ownership, CSRF/origin, validasi nominal/file/rekening tujuan, migrasi data lama, tautan kedaluwarsa dan pembatalan token, dua keputusan bersamaan, persistensi, outbox lokal, SMTP dengan mock, retry gagal, password/sesi dan limit login. Tidak mengirim email nyata. Surat contoh yang disediakan hanya untuk pengujian.

Rekening tujuan dan atas nama rekening tujuan wajib diisi untuk setiap pengajuan baru dan revisi, baik Standing Instruction maupun Warkat. Nomor tujuan disimpan sebagai teks agar nol di depan tetap utuh (rekening BRI, tepat 15 digit angka); nama pemilik maksimal 250 karakter. Keduanya tersimpan pada setiap versi dan ditampilkan pada email, konfirmasi nasabah, detail pengajuan, serta PDF pelaksanaan. Startup menambahkan kolom secara otomatis tanpa menghapus data lama; rekening tujuan pada pengajuan lama yang belum dicatat ditampilkan sebagai “Belum tercatat”.

Nomor rekening untuk nasabah baru harus terdiri dari tepat 15 digit, termasuk nol di depan. Petugas dapat membatalkan pengajuannya sendiri selama belum disetujui atau ditolak SOL, termasuk saat diminta revisi. Alasan wajib dicatat; surat dan audit dipertahankan, tautan nasabah dinonaktifkan, serta email yang belum diproses dibatalkan. Email yang sedang dikirim atau sudah terkirim tidak dapat ditarik kembali.

SOL dapat menghapus satu pengajuan lewat halaman detail, atau semua pengajuan lewat Antrean review → Hapus semua pengajuan. Tindakan ini mengosongkan daftar bagi SOL dan petugas dengan memindahkan pengajuan ke arsip. Akun, data nasabah, surat, dan audit tetap tersimpan. Tombol Pulihkan pengajuan mengembalikan seluruh arsip ke daftar; tautan nasabah lama tetap tidak berlaku. Untuk pengajuan yang masih menunggu nasabah, petugas dapat meminta tautan baru. Penghapusan meminta konfirmasi dan tidak menjalankan pengiriman email baru.

Pencarian nama nasabah atau CIF tersedia pada tabel Data nasabah (SOL) dan formulir Pengajuan baru (petugas). SOL dapat menghapus nasabah dari daftar dan memulihkannya; nasabah yang dihapus tidak dapat dipilih untuk pengajuan baru. Pengajuan lama menggunakan snapshot sehingga surat, konfirmasi, dan revisinya tetap tersedia.

### Arsip dan pemantauan BOH

SOL menghapus nasabah/pengajuan ke arsip dengan password akun yang sedang login. Tombol Pulihkan membuka daftar arsip untuk pemulihan per data. Hapus permanen hanya tersedia di arsip, memerlukan password SOL serta CIF/ID yang diketik ulang. Penghapusan master nasabah mempertahankan snapshot surat dan pengajuan lama. Penghapusan permanen pengajuan menghapus dokumen, semua file versinya, dan antrean email; catatan audit tetap disimpan. Tautan lama tidak diaktifkan kembali saat pemulihan.

Akun BOH yang sudah tersedia dapat login melalui halaman masuk. Pembuatan akun BOH melalui SOL sudah dinonaktifkan. BOH dapat membaca ringkasan dashboard, detail, surat, dan audit semua pengajuan, memutuskan pembaruan data nasabah dari SOL, dan mengelola password akun sendiri. API BOH tetap menolak akses daftar master nasabah, PDF pelaksanaan, email, pembuatan transaksi, dan tindakan operasional SOL. Data nasabah lama dan usulan perubahan tersedia hanya pada daftar persetujuan nasabah bagi SOL dan BOH.

### Pengiriman email dan Inbox

Email konfirmasi menyertakan Date, Message-ID, identitas pengirim, Reply-To, serta versi teks dan HTML yang berisi informasi yang sama. Saat memakai smtp.gmail.com, alamat From dan envelope sender menggunakan SMTP_USER agar sesuai dengan akun Gmail yang diautentikasi; SMTP_FROM tidak dapat menyamar sebagai alamat lain. Gmail/penyedia email tetap menentukan penempatan Inbox atau Spam. Format email tidak menggantikan SPF, DKIM, DMARC atau reputasi pengirim. Untuk Gmail pribadi, autentikasi domain gmail.com dikelola Google; untuk domain sendiri, konfigurasikan DNS melalui penyedia domain/email. Periksa Authentication-Results pada email yang diterima, bukan hanya status sent pada aplikasi.

## PDF pelaksanaan setelah persetujuan

Buka detail pengajuan yang telah disetujui nasabah dan SOL, lalu pilih **Unduh PDF pelaksanaan**. Semua Officer dan SOL dapat mengunduh; BOH tidak memiliki akses unduhan PDF transaksi. PDF memuat surat konfirmasi pelaksanaan, identitas pembuat, pernyataan serta waktu konfirmasi nasabah, persetujuan SOL, log aktivitas, dan surat terakhir yang disetujui. File asli disertakan sebagai lampiran PDF dan hash SHA-256 dicantumkan. PDF/JPG/PNG didukung. PDF rusak atau dilindungi kata sandi menghasilkan pesan kesalahan, bukan laporan tanpa dokumen asli.

Surat ini merupakan bukti selesainya alur persetujuan, bukan bukti eksekusi transaksi atau tanda tangan digital tersertifikasi. Tidak ada penanda versi yang ditampilkan; snapshot revisi tetap disimpan secara internal.

### Edit data nasabah dengan persetujuan BOH

Saat mode Edit aktif, tombol atas menjadi **Batal — Edit — Tambah nasabah**. Saat mode Hapus aktif, tombol menjadi **Batal — Hapus — Tambah nasabah**. Memilih nasabah dalam mode Hapus langsung membuka konfirmasi dan kolom password SOL; data belum dihapus sebelum konfirmasi dikirim.

SOL memilih **Data Nasabah → Edit**, lalu memilih nasabah untuk langsung membuka formulir. SOL mengubah nama, nomor rekening, jabatan, email, atau nomor HP, lalu mengisi alasan dan memilih **Ajukan ke BOH**. CIF tetap menjadi identitas nasabah. Usulan masuk ke menu **Update Data** pada SOL dan BOH; jumlah yang menunggu ditampilkan pada navigasi dan diperbarui otomatis.

BOH memilih **Periksa** untuk membandingkan data sebelumnya dan usulan SOL. **Setujui perubahan** memperbarui master nasabah secara atomik; **Tolak** wajib disertai catatan dan mempertahankan data lama. Pemohon, alasan, data sebelum/sesudah, keputusan, catatan, dan waktu tersimpan dalam riwayat. Satu nasabah hanya memiliki satu usulan yang menunggu persetujuan. Data yang berubah sejak pengajuan mencegah persetujuan usulan lama; penghapusan nasabah membatalkan usulan yang masih menunggu.

Pengajuan transaksi yang sudah dibuat tetap menggunakan snapshot data nasabah sebelumnya. Pengajuan baru setelah persetujuan menggunakan data yang telah diperbarui. Endpoint perubahan nomor HP juga masuk antrean BOH dan tidak memperbarui master secara langsung. Startup menambahkan tabel usulan dan nomor revisi master tanpa menghapus data lama. Fitur ini menggunakan akun BOH yang sudah tersedia; tidak membuat atau mengubah akun produksi.

Pengiriman konfirmasi dicatat per link: Email dan WhatsApp yang sudah dipilih tidak dapat dipilih lagi untuk link yang sama, termasuk setelah halaman dimuat ulang. Memilih Keduanya mengunci kedua pilihan setelah diproses; WhatsApp tetap dikirim manual dari pratinjau, sehingga status pilihan bukan laporan pengiriman dari WhatsApp. Kanal yang belum dipilih dapat menggunakan link yang masih aktif tanpa membuat versi baru. Kirim ulang menerbitkan link baru setelah 24 jam atau ketika link lama kedaluwarsa.
