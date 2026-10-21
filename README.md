# BRI VISTA

Verification, Integration & Secure Tracking Application

Aplikasi web untuk pengajuan petugas, konfirmasi surat melalui email, dan keputusan AMOL. Backend Python + SQLite; frontend HTML/CSS/JavaScript. Python 3.10+; mode lokal tidak memerlukan npm. Ekspor PDF menggunakan ReportLab dan pypdf. Deployment menggunakan Gunicorn melalui `requirements.txt`; lihat `DEPLOY.md`.

## Jalankan dan coba

```sh
cd /Users/kznrifky/Documents/BPIP
python3 -m pip install -r requirements.txt
python3 server.py --demo
```

Buka **http://localhost:8000**. Jalankan melalui server ini, bukan dengan membuka `web/index.html` langsung atau Live Server.

Akun lokal petugas: `petugas@bpip.local`, password `PetugasDemo!2026`.
Akun lokal AMOL: `sol@bpip.local`, password `SolDemo!2026`.

1. Masuk sebagai petugas. Buka Pengajuan baru.
2. Pilih CIF `1234567`, masukkan nominal `250000000`, rekening tujuan `000123456789012`, atas nama `PT Tujuan Pembayaran`, dan unggah `docs/surat-demo.pdf`.
3. Centang pernyataan pemeriksaan lalu kirim konfirmasi.
4. Buka Kotak email lokal. Buka halaman konfirmasi nasabah di tab baru.
5. Periksa surat; centang pernyataan dan pilih Setujui/Tolak. Penolakan memerlukan alasan.
6. Keluar dari akun petugas lalu masuk sebagai AMOL. Klik baris pengajuan untuk membuka detail dan surat.
7. Pilih Setujui atau Tolak. Catatan wajib untuk penolakan.
8. Pengajuan selesai atau ditolak masuk History; gunakan filter Berhasil/Ditolak. Dokumen pelaksanaan dapat diunduh setelah nasabah dan AMOL menyetujui.


Data tersimpan pada `data/bpip.sqlite3` dan bertahan saat server dimatikan. Akun/data demo hanya dibuat ketika database belum memiliki akun. Mengaktifkan `--demo` pada database yang sudah berisi akun tidak mengubah password akun tersebut. Prototipe awal disimpan di `prototype-original/`.

## Perilaku aplikasi

- Semua Officer melihat daftar pengajuan dan history bersama. Nama pengaju ditampilkan di halaman detail; daftar tetap ringkas tanpa kolom Pengaju. Hanya Officer pembuat yang dapat mengirim konfirmasi dan menerbitkan ulang link pengajuannya. Officer, AMOL, dan BOH membuka detail dengan klik baris pengajuan. BOH membaca detail dan surat tanpa tindakan operasional. Pembatasan tindakan diberlakukan oleh backend.
- Nasabah tidak membutuhkan akun web; akses melalui token acak 256 bit, berumur 24 jam dan sekali keputusan. Pembukaan email/tautan tidak memberikan persetujuan otomatis.
- Dashboard dan Pengajuan hanya menampilkan pengajuan yang masih diproses. Persetujuan nasabah dan AMOL masuk History sebagai Berhasil; penolakan salah satunya masuk sebagai Ditolak. Pengajuan lama yang dibatalkan tetap tersimpan dalam kelompok Ditolak; filter pembatalan tidak tersedia. Standing Instruction dan Warkat mengikuti aturan yang sama; angka KPI dan antrean hanya menghitung pengajuan aktif. Data, surat, dan audit tetap tersimpan.
- Konfirmasi nasabah dan keputusan AMOL merupakan dua status yang berbeda. Nasabah setuju belum berarti pengajuan telah disetujui AMOL.
- AMOL hanya dapat menyetujui atau menolak setelah nasabah menyetujui surat. Penolakan nasabah langsung masuk History dan menghentikan alur persetujuan. Backend tetap mengizinkan AMOL mencatat penolakan penutup pada data lama yang ditolak nasabah.
- Permintaan revisi dan pembatalan Officer dinonaktifkan pada UI dan API. Pengajuan lama yang menunggu revisi dapat diselesaikan AMOL dengan Setujui/Tolak; file dan audit lamanya tetap tersimpan. Keputusan akhir AMOL tidak dapat diedit.
- Kirim tautan baru tersedia saat menunggu nasabah, dengan jeda minimum satu menit. Tautan lama dibatalkan. Penerbitan tautan baru menggunakan nomor versi berikutnya untuk mengikat token ke snapshot surat.
- Email antrean diproses worker setiap dua detik. Kegagalan mencoba ulang dengan jeda bertambah, maksimal lima percobaan. Status `sent` berarti diterima server SMTP, bukan bukti email dibaca atau masuk inbox. SMTP tidak menjamin pengiriman tepat satu kali; retry setelah koneksi terputus dapat menghasilkan email duplikat, tetapi keputusan nasabah tetap hanya sekali.
- Dashboard disinkronkan setiap sepuluh detik. Filter pencarian, jenis surat dan status tersedia. Jika catatan AMOL sedang diisi, detail tidak ditimpa otomatis; gunakan tombol Perbarui setelah selesai.
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

Perintah `init` meminta email, nama dan password untuk petugas dan AMOL. Password minimal 12 karakter dan tidak ditampilkan saat diketik. Hanya AMOL yang dapat menambahkan nasabah melalui menu Data nasabah. Petugas memilih nasabah yang sudah didaftarkan AMOL untuk membuat pengajuan. Data demo menggunakan `example.com`, sehingga harus diganti dengan data master yang diverifikasi untuk pengiriman nyata. Setiap pengajuan menyimpan snapshot data nasabah, bukan bergantung pada perubahan data master berikutnya.

Password dapat diganti di menu Pengaturan. Sesi lain dicabut setelah perubahan password.

### Role dan pengelolaan akun

Aplikasi menggunakan role Officer (`petugas`), SOL checker (`checker`), AMOL (`sol`, kode internal lama), dan BOH (`boh`). Role IT dan fitur pengelolaan akun melalui web sudah dihapus, termasuk menu persetujuan akun di BOH. Endpoint pengelolaan akun lama tidak dapat digunakan lagi.

Akun IT lama dinonaktifkan dan sesinya dicabut saat startup. Identitas akun serta riwayat pengajuan dan audit lama tetap tersimpan; akun Officer, AMOL, dan BOH tidak diubah. Pengajuan akun yang dahulu menunggu persetujuan tidak diproses otomatis.

Administrator menyiapkan akun melalui terminal pada database yang dituju:

```sh
python3 server.py create-user --role petugas
```

Gunakan `--role sol` untuk AMOL atau `--role boh` untuk BOH. Perintah meminta email, nama, dan kata sandi yang tidak ditampilkan saat diketik. Perintah tidak mengubah akun yang sudah ada; pastikan database yang dituju sebelum menjalankannya.

### Pemeriksaan SOL sebelum approval AMOL

Pengajuan baru mengikuti Officer → Verifikator Nasabah (1 atau 2 orang) → SOL checker → AMOL. Seluruh verifikator harus menyetujui sebelum SOL bisa memutuskan. AMOL baru dapat menyetujui atau menolak setelah SOL menyetujui. Penolakan pada salah satu tahap menghentikan pengajuan; alasan wajib diisi saat menolak. Checker tidak memiliki fitur Data Nasabah, Update Data, pengajuan surat, atau penghapusan. Seluruh fitur administratif AMOL sebelumnya tetap berada pada role internal `sol`.

Startup menambahkan status pemeriksaan dan menaikkan pengajuan lama yang masih aktif ke alur baru. Surat yang sudah selesai tetap menggunakan riwayat alur sebelumnya; keputusan lama tidak diubah. PDF untuk alur baru wajib memuat persetujuan nasabah, SOL, dan AMOL dengan pelaku serta waktunya masing-masing.

Siapkan akun checker melalui `python3 server.py create-user --role checker`, dan akun AMOL melalui `--role sol`. Saat memindahkan akun lama, pastikan `sol@example.test` menjadi `checker` dan `amol@example.test` menjadi `sol`; cabut sesi akun yang berganti role. Jangan mengubah role seluruh akun `sol` secara massal karena kode internal itu tetap berarti AMOL.

Untuk penyiapan dua akun yang telah dikonfirmasi pemilik aplikasi, administrator dapat menjalankan satu kali melalui terminal pada database tujuan:

```sh
python3 server.py configure-reviewers --checker-email sol@example.test --approver-email amol@example.test
```

Perintah ini **tidak dijalankan otomatis saat deploy**. Akun yang sudah ada mempertahankan ID dan kata sandinya; sesi dicabut jika rolenya berubah. Akun baru memperoleh kata sandi acak yang ditampilkan sekali pada hasil terminal. Menjalankan ulang tidak mereset kata sandi. Email Officer, BOH, atau akun nonaktif tidak ditimpa. Simpan keluaran kata sandi di tempat aman dan jangan masukkan ke Git.

Mode demo lokal menyediakan `sol@example.test` / `SolCheckerDemo!2026` dan `amol@example.test` / `AmolDemo!2026`. Kredensial demo tidak dibuat otomatis dalam produksi dan ditolak oleh pemeriksaan konfigurasi produksi.

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

Bank tujuan, rekening tujuan, dan nama rekening tujuan wajib diisi untuk pengajuan baru, baik Standing Instruction maupun Warkat. Nomor tujuan hanya menerima angka dan disimpan sebagai teks agar nol di depan tetap utuh. Panjang mengikuti bank yang dipilih: BRI 15, BCA/BNI/BSI/Danamon 10, Mandiri 13, CIMB Niaga 12 atau 13, BTN 16, dan OCBC 12 digit. Nama rekening hanya menerima huruf A–Z dan spasi, maksimal 250 karakter. Ketiganya tersimpan pada setiap versi dan ditampilkan pada email, konfirmasi nasabah, detail pengajuan, serta PDF pelaksanaan. Startup menambahkan kolom secara otomatis tanpa menghapus data lama; rekening tujuan pada pengajuan lama yang belum dicatat ditampilkan sebagai “Belum tercatat”.

Nomor rekening untuk nasabah baru harus terdiri dari tepat 15 digit, termasuk nol di depan. Petugas dapat membatalkan pengajuannya sendiri selama belum disetujui atau ditolak AMOL, termasuk saat diminta revisi. Alasan wajib dicatat; surat dan audit dipertahankan, tautan nasabah dinonaktifkan, serta email yang belum diproses dibatalkan. Email yang sedang dikirim atau sudah terkirim tidak dapat ditarik kembali.

AMOL dapat menghapus satu pengajuan lewat halaman detail, atau semua pengajuan lewat Antrean review → Hapus semua pengajuan. Tindakan ini mengosongkan daftar bagi AMOL dan petugas dengan memindahkan pengajuan ke arsip. Akun, data nasabah, surat, dan audit tetap tersimpan. Tombol Pulihkan pengajuan mengembalikan seluruh arsip ke daftar; tautan nasabah lama tetap tidak berlaku. Untuk pengajuan yang masih menunggu nasabah, petugas dapat meminta tautan baru. Penghapusan meminta konfirmasi dan tidak menjalankan pengiriman email baru.

Pencarian nama nasabah atau CIF tersedia pada tabel Data nasabah (AMOL) dan formulir Pengajuan baru (petugas). AMOL dapat menghapus nasabah dari daftar dan memulihkannya; nasabah yang dihapus tidak dapat dipilih untuk pengajuan baru. Pengajuan lama menggunakan snapshot sehingga surat, konfirmasi, dan revisinya tetap tersedia.

### Arsip dan pemantauan BOH

AMOL menghapus nasabah/pengajuan ke arsip dengan password akun yang sedang login. Tombol Pulihkan membuka daftar arsip untuk pemulihan per data. Hapus permanen hanya tersedia di arsip, memerlukan password AMOL serta CIF/ID yang diketik ulang. Penghapusan master nasabah mempertahankan snapshot surat dan pengajuan lama. Penghapusan permanen pengajuan menghapus dokumen, semua file versinya, dan antrean email; catatan audit tetap disimpan. Tautan lama tidak diaktifkan kembali saat pemulihan.

Akun BOH yang sudah tersedia dapat login melalui halaman masuk. Pembuatan akun BOH melalui AMOL sudah dinonaktifkan. Navigasi BOH hanya menampilkan **Dashboard** dan **History**. BOH dapat melihat KPI, tracking seluruh pengajuan, detail, surat asli, versi surat, dan log aktivitas. BOH tidak dapat memberi persetujuan atau penolakan, mengubah data, membuat atau menghapus pengajuan, maupun memproses pembaruan nasabah. Pembatasan diterapkan pada API, termasuk endpoint persetujuan pembaruan nasabah lama. Akses master nasabah, PDF pelaksanaan, dan email tetap ditolak. Penggantian kata sandi akun sendiri dan logout tetap tersedia melalui API sesi.

### Pengiriman email dan Inbox

Email konfirmasi menyertakan Date, Message-ID, identitas pengirim, Reply-To, serta versi teks dan HTML yang berisi informasi yang sama. Saat memakai smtp.gmail.com, alamat From dan envelope sender menggunakan SMTP_USER agar sesuai dengan akun Gmail yang diautentikasi; SMTP_FROM tidak dapat menyamar sebagai alamat lain. Gmail/penyedia email tetap menentukan penempatan Inbox atau Spam. Format email tidak menggantikan SPF, DKIM, DMARC atau reputasi pengirim. Untuk Gmail pribadi, autentikasi domain gmail.com dikelola Google; untuk domain sendiri, konfigurasikan DNS melalui penyedia domain/email. Periksa Authentication-Results pada email yang diterima, bukan hanya status sent pada aplikasi.

## PDF pelaksanaan setelah persetujuan

Buka detail pengajuan yang telah disetujui nasabah dan AMOL, lalu pilih **Unduh PDF pelaksanaan**. Semua Officer dan AMOL dapat mengunduh; BOH tidak memiliki akses unduhan PDF transaksi. PDF memuat surat konfirmasi pelaksanaan, identitas pembuat, pernyataan serta waktu konfirmasi nasabah, persetujuan AMOL, log aktivitas, dan surat terakhir yang disetujui. File asli disertakan sebagai lampiran PDF dan hash SHA-256 dicantumkan. PDF/JPG/PNG didukung. PDF rusak atau dilindungi kata sandi menghasilkan pesan kesalahan, bukan laporan tanpa dokumen asli.

Surat ini merupakan bukti selesainya alur persetujuan, bukan bukti eksekusi transaksi atau tanda tangan digital tersertifikasi. Tidak ada penanda versi yang ditampilkan; snapshot revisi tetap disimpan secara internal.

### Perubahan data nasabah: SOL mengajukan, AMOL menyetujui

SOL memilih **Data Nasabah → Edit**, memilih nasabah, mengubah data, lalu mengisi alasan dan memilih **Ajukan ke AMOL**. CIF tidak dapat diubah. SOL dapat membaca master nasabah dan riwayat perubahan, tetapi tidak dapat menambah atau menghapus nasabah. Fitur tambah dan hapus nasabah yang sudah ada tetap tersedia untuk AMOL.

Menu **Update Data** tersedia untuk SOL dan AMOL. AMOL membandingkan data sebelumnya dan usulan, lalu memilih **Setujui perubahan** atau **Tolak**. Penolakan wajib disertai alasan. SOL, Officer, dan BOH tidak dapat memutuskan permintaan perubahan. Akun pengaju tidak dapat menyetujui atau menolak permintaannya sendiri, termasuk permintaan lama; AMOL yang berbeda harus menanganinya. Identitas pengaju dan pemeriksa tetap disimpan.

Data nasabah diperbarui secara atomik setelah persetujuan AMOL. Satu nasabah hanya dapat memiliki satu permintaan yang menunggu. Revisi master dan snapshot dibandingkan untuk mencegah persetujuan data usang; penghapusan nasabah membatalkan permintaan yang masih menunggu. Pengajuan transaksi yang sudah dibuat tetap menggunakan snapshot data nasabah sebelumnya. Pengajuan baru setelah persetujuan menggunakan data yang telah diperbarui. Perubahan nomor HP mengikuti persetujuan AMOL yang sama.

Permintaan dan audit lama tetap tersimpan tanpa persetujuan otomatis atau penggantian identitas pengaju. BOH hanya memiliki menu Dashboard dan History, tanpa akses perubahan data nasabah atau approval. Perubahan role dan akun produksi tidak dijalankan otomatis.

Pengiriman konfirmasi dicatat per link: Email dan WhatsApp yang sudah dipilih tidak dapat dipilih lagi untuk link yang sama, termasuk setelah halaman dimuat ulang. Memilih Keduanya mengunci kedua pilihan setelah diproses; WhatsApp tetap dikirim manual dari pratinjau, sehingga status pilihan bukan laporan pengiriman dari WhatsApp. Kanal yang belum dipilih dapat menggunakan link yang masih aktif tanpa membuat versi baru. Kirim ulang menerbitkan link baru setelah 24 jam atau ketika link lama kedaluwarsa.
