# Skenario Pengecekan Manual Aplikasi YAQin

Dokumen ini digunakan untuk memeriksa apakah alur aplikasi sesuai dengan rancangan. Data acuan diambil dari database lokal aktif pada 24 Oktober 2026.

## 1. Persiapan

1. Pastikan `http://localhost:3000` dan `http://localhost:8000/health/ready` dapat dibuka.
2. Gunakan jendela incognito berbeda untuk Peserta, Mentor, Dosen, dan Admin agar sesi tidak tercampur.
3. Setelah berpindah peran, selalu keluar terlebih dahulu.
4. Catat hasil setiap skenario sebagai `Lulus`, `Gagal`, atau `Belum dapat diuji`.
5. Pengujian yang menyimpan jadwal, penilaian, atau finalisasi akan mengubah database. Gunakan akun yang disebutkan pada setiap skenario.

## 2. Akun uji

| Peran | Username | Kata sandi | Nama/kegunaan |
|---|---:|---|---|
| Peserta baru | `1217010019` | `sandi1` | Arifah, 0 tema selesai |
| Peserta dengan pengajuan | `1247010013` | `sandi1` | Aif, sesi berstatus Diajukan kepada Meutya |
| Peserta dengan jadwal | `1247010030` | `sandi1` | Taufik, 1 tema selesai dan sesi Terjadwal |
| Peserta progres awal | `1247010031` | `sandi1` | Fasya, 2 tema selesai |
| Peserta progres menengah | `1247010049` | `sandi1` | Baihaqi, 10 tema selesai |
| Peserta progres lanjut | `1247010059` | `sandi1` | Alya, 18 tema selesai |
| Peserta hampir selesai | `1247010083` | `sandi1` | Siti Amelia, 35 tema selesai |
| Mentor | `1237010009` | `Mentor1` | Meutya Frias Susyanti |
| Mentor alternatif | `1237010043` | `Mentor1` | Rezkya Syifa Adilla |
| Dosen | `197105172007012022` | `Dosen1` | Dr. Asti Meiza, M.Si. |
| Admin Jurusan Matematika | `20030101001` | `Admin1` | Dwi Ayu Rahmawati |
| Admin Jurusan Fisika | `20030202002` | `Admin1` | Aisyah, untuk uji pembatasan organisasi |
| Admin Fakultas | `20030303003` | `Admin1` | Mujtaba |

Kata sandi peka huruf besar-kecil. `Mentor1`, `Dosen1`, dan `Admin1` menggunakan huruf awal kapital.

## 3. Kondisi data awal

- Kurikulum terdiri atas 40 tema dalam lima bagian.
- Urutan dimulai dari akhir Juz 30.
- T01 adalah Al-Ikhlas, Al-Falaq, dan An-Nas.
- T02 adalah Al-Masad, An-Nasr, dan Al-Kafirun.
- T03 adalah Al-Ma'un dan Al-Kawthar.
- T04 adalah Al-Fil dan Quraysh.
- T05 adalah Al-'Asr dan Al-Humazah.
- Setiap Peserta mempunyai satu target aktif; target lainnya selesai atau terjadwal sesuai progres.
- Database awal mempunyai 168 penilaian tema, belum mempunyai setoran video, dan belum mempunyai Ujian Dosen.
- Database mempunyai snapshot nilai untuk 25 Peserta, tetapi Nilai Ujian (Dosen) belum tersedia karena belum ada ujian.

## 4. Skenario autentikasi dan akses

### AUT-01 — Login Peserta

**Data:** `1217010019 / sandi1`

**Langkah:**

1. Buka `/login`.
2. Masukkan username dan kata sandi.
3. Tekan tombol masuk.

**Hasil yang diharapkan:**

- Login berhasil tanpa pesan kesalahan.
- Pengguna diarahkan ke `/peserta`.
- Nama Arifah dan organisasi Matematika tampil.
- Menu Peserta tersedia; menu operasional Mentor atau Dosen tidak tersedia.

### AUT-02 — Login Mentor

**Data:** `1237010009 / Mentor1`

**Hasil yang diharapkan:**

- Pengguna diarahkan ke `/mentor/antrean`.
- Nama Meutya dan organisasi Matematika tampil.
- Antrean memuat Aif Suwanda dengan status Diajukan dan Taufik Setiajie dengan status Terjadwal.

### AUT-03 — Login Dosen

**Data:** `197105172007012022 / Dosen1`

**Hasil yang diharapkan:**

- Pengguna diarahkan ke `/dosen/ujian`.
- Daftar ujian masih kosong karena database awal belum mempunyai Ujian Dosen.
- Kondisi kosong dijelaskan, bukan ditampilkan sebagai kesalahan teknis.

### AUT-04 — Login gagal

**Data:** username valid dengan kata sandi `salah`

**Hasil yang diharapkan:**

- Pengguna tetap berada di halaman login.
- Pesan kegagalan tidak membocorkan apakah username atau kata sandi yang salah.
- Tidak terbentuk sesi login.

### AUT-05 — Pembatasan berdasarkan peran

**Langkah:** login sebagai Peserta lalu buka langsung `/mentor/antrean` dan `/dosen/ujian`.

**Hasil yang diharapkan:** data Mentor atau Dosen tidak boleh terbaca. API harus menolak akses yang tidak sesuai peran meskipun URL diketik secara langsung.

## 5. Skenario Peserta

### PST-01 — Memeriksa dashboard Peserta baru

**Data:** `1217010019 / sandi1`

**Hasil yang diharapkan:**

- Progres menunjukkan 0 dari 40 tema selesai.
- Hanya satu target yang aktif.
- Tema disusun dari T01 menuju T40.
- T01 adalah Al-Ikhlas, Al-Falaq, dan An-Nas.
- Tombol pengajuan sesi hanya tersedia untuk target yang diizinkan.

### PST-02 — Memeriksa variasi progres

Login secara bergantian menggunakan akun berikut dan bandingkan progres:

| Username | Tema selesai yang diharapkan | Target aktif | Target terjadwal |
|---:|---:|---:|---:|
| `1217010019` | 0 | 1 | 39 |
| `1247010031` | 2 | 1 | 37 |
| `1247010049` | 10 | 1 | 29 |
| `1247010059` | 18 | 1 | 21 |
| `1247010083` | 35 | 1 | 4 |

### PST-03 — Mengajukan sesi baru

**Data:** `1217010019 / sandi1`

**Langkah:**

1. Buka Target atau Sesi Baru.
2. Pilih tema aktif.
3. Isi waktu usulan dan catatan.
4. Kirim pengajuan.

**Hasil yang diharapkan:**

- Pengajuan berhasil dan memperoleh status `Diajukan`.
- Tema yang terkunci tidak dapat dipilih.
- Pengajuan muncul pada riwayat sesi Peserta.
- Pengajuan muncul pada antrean Mentor yang ditugaskan.

### PST-04 — Memeriksa sesi terjadwal

**Data:** `1247010030 / sandi1`

**Hasil yang diharapkan:**

- Terdapat sesi Terjadwal bersama Mentor Meutya.
- Jadwal ditampilkan sebagai 28 Oktober 2026 pukul 09.00 WIB.
- Peserta tidak memperoleh tombol penilaian Mentor.

### PST-05 — Memeriksa hasil tema

**Data:** `1247010049 / sandi1`

**Hasil yang diharapkan:**

- Halaman Hasil menampilkan riwayat tema yang sudah difinalisasi.
- Jumlah tema selesai pada ringkasan adalah 10.
- Skor adalah bilangan bulat 1–10.
- Peserta hanya dapat membaca hasilnya sendiri.

### PST-06 — Memeriksa rekap nilai

**Data:** salah satu akun Peserta, lalu buka `/peserta/ujian`.

**Hasil yang diharapkan:**

- Nama komponen ditampilkan lengkap, tanpa singkatan:
  - Nilai Keaktifan — bobot 20%.
  - Nilai Proses Hafalan (Mentor) — bobot 50%.
  - Nilai Ujian (Dosen) — bobot 30%.
- Nilai Akhir belum final jika salah satu komponen belum tersedia.
- Nilai kosong tidak diganti dengan nol atau satu.
- Ambang kelulusan tetap 6 setelah seluruh komponen dan Ujian Dosen final.

### PST-07 — Setoran video sebelum satu bagian lengkap

**Data:** `1217010019 / sandi1`

**Langkah:** buka `/peserta/video/baru`.

**Hasil yang diharapkan:**

- Sistem menjelaskan bahwa seluruh tema dalam bagian harus berstatus Cukup terlebih dahulu.
- Peserta tidak dapat mengirim video untuk bagian yang belum memenuhi syarat.

## 6. Skenario Mentor

### MTR-01 — Antrean Mentor

**Data:** `1237010009 / Mentor1`

**Hasil yang diharapkan:**

- Aif Suwanda tampil sebagai Diajukan.
- Taufik Setiajie tampil sebagai Terjadwal.
- Peserta yang ditugaskan kepada Mentor lain tidak muncul.

### MTR-02 — Menjadwalkan pengajuan

**Data awal:** gunakan pengajuan Aif Suwanda.

**Langkah:** pilih tanggal mendatang, metode sesi, dan catatan; kemudian sahkan jadwal.

**Hasil yang diharapkan:**

- Status berubah dari Diajukan menjadi Terjadwal.
- Jadwal baru tampil pada akun Mentor dan Peserta.
- Perubahan menggunakan versi data terbaru; tab lama tidak boleh menimpa perubahan baru.

### MTR-03 — Memulai dan menilai sesi

**Data awal:** sesi Taufik Setiajie yang sudah Terjadwal.

**Langkah:**

1. Mulai sesi.
2. Isi skor bulat 1–10, hasil tema, catatan, dan kejadian bila ada.
3. Simpan draft.
4. Finalisasi.

**Hasil yang diharapkan:**

- Sesi berpindah ke Sedang Berlangsung ketika dimulai.
- Skor pecahan dan skor di luar 1–10 ditolak.
- Draft masih dapat diedit sebelum finalisasi.
- Setelah finalisasi, hasil tidak dapat diedit sebagai draft biasa.
- Target Peserta berubah menjadi selesai jika hasilnya Cukup.
- Riwayat penilaian muncul pada akun Peserta.

### MTR-04 — Batas akses Mentor

**Langkah:** coba buka detail Peserta yang ditugaskan kepada Mentor lain dengan URL langsung.

**Hasil yang diharapkan:** API menolak akses dan tidak membocorkan data Peserta tersebut.

### MTR-05 — Video Mentor

**Kondisi awal:** database belum mempunyai setoran video.

**Hasil yang diharapkan:** halaman kelayakan dan penilaian video menampilkan kondisi kosong yang jelas. Setelah Peserta yang memenuhi syarat mengirim video, video muncul hanya pada Mentor yang berwenang.

## 7. Skenario Dosen dan ujian

### DSN-01 — Kondisi awal daftar ujian

**Data:** `197105172007012022 / Dosen1`

**Hasil yang diharapkan:** daftar ujian kosong, karena belum ada peserta yang menjalani alur lengkap lima bagian dan belum ada ujian pada database awal.

### DSN-02 — Paket ujian

**Prasyarat:** Admin/Dosen sudah membuat ujian bagi Peserta yang seluruh lima bagiannya Cukup.

**Hasil yang diharapkan:**

- Dosen dapat menggunakan soal aplikasi atau soal buatan Dosen.
- Paket yang belum memenuhi aturan tidak dapat disahkan.
- Acuan jawaban hanya terbaca oleh penguji berwenang.

### DSN-03 — Pelaksanaan dan finalisasi ujian

**Hasil yang diharapkan:**

- Setiap butir menerima skor bulat 1–10, catatan, dan bukti.
- Finalisasi ditolak jika butir atau bukti belum lengkap.
- Setelah finalisasi, Nilai Ujian (Dosen) tersedia.
- Nilai akhir dihitung dengan rumus: 20% Nilai Keaktifan + 50% Nilai Proses Hafalan (Mentor) + 30% Nilai Ujian (Dosen).
- Peserta lulus jika Nilai Akhir minimal 6; tidak ada ambang khusus Nilai Ujian (Dosen).

## 8. Skenario Admin Jurusan

### ADM-01 — Daftar Peserta Matematika

**Data:** `20030101001 / Admin1`

**Hasil yang diharapkan:**

- Halaman peserta hanya memuat organisasi Matematika.
- NIM, nama, status keanggotaan, dan penugasan dapat dibaca.
- Data Jurusan Fisika tidak boleh terlihat.

### ADM-02 — Pembatasan organisasi

**Data:** `20030202002 / Admin1`

**Hasil yang diharapkan:** Admin Fisika tidak dapat membaca atau mengubah Peserta Matematika melalui URL/API langsung.

### ADM-03 — Kalender dan perubahan tenggat

**Data:** `20030101001 / Admin1`, buka `/jurusan/kalender`.

**Hasil yang diharapkan:**

- Kalender menampilkan target 40 tema.
- Pratinjau perubahan menunjukkan tanggal lama, tanggal baru, dan selisih hari.
- Perubahan memerlukan alasan dan persetujuan sesuai aturan.
- Tenggat efektif berubah setelah disahkan; tenggat awal dan jejak audit tetap tersimpan.

## 9. Skenario Admin Fakultas

### FAK-01 — Login Admin Fakultas

**Data:** `20030303003 / Admin1`

**Hasil yang diharapkan saat ini:** login berhasil, tetapi belum tersedia workspace operasional khusus Admin Fakultas; pengguna diarahkan ke halaman utama. Catat sebagai celah implementasi apabila rancangan Anda mengharuskan dashboard Fakultas.

## 10. Pemeriksaan lintas alur

### E2E-01 — Siklus tema lengkap

Urutan uji: Peserta mengajukan sesi → Mentor menjadwalkan → Mentor memulai → Mentor menyimpan penilaian → Mentor memfinalisasi → Peserta melihat hasil.

**Hasil yang diharapkan:** status dan data yang sama terlihat konsisten pada kedua peran; target selesai hanya setelah hasil final yang memenuhi aturan.

### E2E-02 — Siklus bagian dan video

Urutan uji: seluruh tema satu bagian Cukup → Peserta mengirim video → Mentor menilai kelayakan → Mentor menilai video → bagian berikutnya terbuka.

**Hasil yang diharapkan:** bagian berikutnya tetap terkunci sampai hasil video Cukup. Revisi mengikuti batas yang ditentukan sistem.

### E2E-03 — Siklus kelulusan

Urutan uji: lima bagian Cukup → Ujian Dosen dibuat → paket disahkan → ujian dilaksanakan dan difinalisasi → snapshot nilai diterbitkan.

**Hasil yang diharapkan:** ketiga komponen lengkap, bobot 20%/50%/30%, Nilai Akhir dihitung, dan status Lulus hanya muncul jika Nilai Akhir minimal 6.

## 11. Format pencatatan temuan

Gunakan format berikut untuk setiap masalah:

```text
ID skenario:
Status: Lulus / Gagal / Belum dapat diuji
Akun:
Halaman:
Langkah terakhir:
Hasil yang diharapkan:
Hasil aktual:
Pesan kesalahan:
Waktu kejadian:
Screenshot:
```

## 12. Urutan pengecekan yang disarankan

1. Jalankan AUT-01 sampai AUT-05.
2. Jalankan PST-01, PST-02, PST-05, PST-06, dan PST-07 tanpa mengubah data.
3. Jalankan MTR-01, MTR-04, MTR-05, dan DSN-01 tanpa mengubah data.
4. Jalankan ADM-01, ADM-02, ADM-03, dan FAK-01.
5. Setelah hasil baca-saja sesuai, jalankan PST-03, MTR-02, dan MTR-03 yang mengubah data.
6. Terakhir jalankan rangkaian E2E-01 sampai E2E-03 menggunakan Peserta khusus pengujian.
