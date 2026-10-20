# Product Requirements Document (PRD)

## Aplikasi Pendampingan Hafalan Juz 30 YAQin

| Atribut | Nilai |
|---|---|
| Nama produk | YAQin - Aplikasi Pendampingan Hafalan Juz 30 |
| Kepanjangan | Yakin, Amalin, Mutqin |
| Jenis produk | Aplikasi web responsif, PWA-ready, dengan API yang dapat digunakan ulang oleh aplikasi Android |
| Status dokumen | Draft untuk peninjauan dan pengesahan |
| Versi PRD | 1.0 |
| Tanggal | 20 Oktober 2026 |
| Sumber utama | `Rancangan Aplikasi Tahfidz v 01.pdf` |
| Cakupan rilis | MVP pilot web |

> Dokumen ini menerjemahkan rancangan aplikasi menjadi kebutuhan produk. Aturan yang telah diputuskan diperlakukan sebagai baseline. Butir yang belum disahkan tetap ditandai sebagai keputusan terbuka dan tidak boleh dijadikan perilaku otomatis aplikasi.

---

## 1. Ringkasan Eksekutif

YAQin adalah aplikasi pendampingan hafalan Juz 30 yang menyatukan target belajar, latihan, setoran, umpan balik mentor, pemantauan progres, ujian dosen, dan pelaporan program dalam satu riwayat yang dapat ditelusuri.

Produk melayani lima peran utama: Peserta, Mentor, Dosen, Admin Jurusan, dan Admin Fakultas. MVP dibangun sebagai web responsif yang nyaman digunakan melalui ponsel dan komputer. Backend menyediakan API bersama agar aturan akademik, data, dan audit dapat digunakan kembali oleh aplikasi Android pada tahap lanjutan.

Program menggunakan 44 tema dalam lima bagian dengan distribusi 10, 8, 6, 5, dan 15 tema. Setoran tema berlangsung sinkron melalui tatap muka atau video call, sedangkan setoran per bagian berlangsung asinkron melalui rekaman video. Setelah lima bagian berstatus Cukup, peserta mengikuti Ujian Dosen. Kelulusan program hanya dapat dihitung ketika seluruh komponen nilai lengkap dan ujian telah difinalkan.

MVP berfokus pada pencatatan dan penilaian oleh manusia. Penilaian AI, gamifikasi, aplikasi Android, video call internal, unggah video langsung, dan sinkronisasi penilaian offline berada di luar lingkup pilot inti.

## 2. Latar Belakang dan Masalah

Proses hafalan memerlukan kesinambungan antara target, latihan mandiri, koreksi, setoran, murajaah, dan tindak lanjut. Tanpa sistem terpadu, peserta sulit mengetahui tugas berikutnya, mentor sulit mempertahankan konsistensi pencatatan, dan pengelola sulit memantau progres tanpa memeriksa setiap catatan atau rekaman secara manual.

Masalah yang hendak diselesaikan:

1. Riwayat latihan, setoran, koreksi, dan progres belum terhubung secara konsisten.
2. Peserta memerlukan target, tenggat, status, hasil, dan arahan perbaikan yang mudah dipahami.
3. Mentor memerlukan antrean binaan dan formulir penilaian yang cepat tetapi tetap dapat diaudit.
4. Dosen memerlukan prasyarat ujian, paket soal, penilaian, dan validasi kelulusan yang terkontrol.
5. Admin memerlukan pengelolaan pengguna, penugasan, kalender, kebijakan, dan laporan sesuai lingkup organisasi.
6. Perubahan aturan, hasil, penugasan, dan tenggat perlu memiliki riwayat agar keputusan akademik dapat dijelaskan.
7. Data dan media peserta perlu dilindungi hingga tingkat objek, bukan hanya disembunyikan dari menu.

## 3. Visi Produk

Menjadi sarana pendampingan hafalan Juz 30 yang terstruktur, dapat dijelaskan, dan aman, sehingga peserta mengetahui apa yang harus dipelajari dan diperbaiki, pembimbing dapat memberi penilaian yang konsisten, dan pengelola dapat memantau program tanpa menghilangkan peran keputusan manusia.

## 4. Tujuan Produk

### 4.1 Tujuan utama

- Mendukung hafalan Juz 30 berdasarkan tema dan bagian.
- Menghubungkan latihan, setoran, koreksi, pengulangan, dan progres dalam satu riwayat.
- Menyediakan penilaian yang dapat dijelaskan melalui kejadian, bukti, rubrik, dan catatan penilai.
- Membantu mentor dan dosen mengenali peserta yang memerlukan perhatian.
- Mendukung orientasi YAQin: ketelitian dan ketahanan hafalan (Mutqin), pemahaman dan penghayatan makna (Yakin), serta pengamalan (Amalin).
- Menyediakan data dan aturan bisnis bersama untuk web dan pengembangan Android di masa depan.
- Menjaga setiap perubahan penting melalui versi, audit, dan koreksi yang tidak menimpa riwayat.

### 4.2 Sasaran keberhasilan pilot

Sasaran berikut adalah gate awal pilot dan wajib dikalibrasi melalui keputusan L07:

- Seluruh alur inti dari akun hingga ujian dapat diselesaikan oleh peran yang berwenang.
- Tidak ada kebocoran akses lintas peserta, binaan, jurusan, atau mandat.
- Tidak ada hasil akademik ganda akibat klik ulang, retry, atau permintaan bersamaan.
- Perhitungan K dan N konsisten terhadap dataset acuan.
- Semua kasus uji P0 dalam lingkup rilis lulus dan tidak ada masalah S1/S2 terbuka.
- Restore basis data dan sampel media berhasil di lingkungan terisolasi.
- Seluruh lima peran menyelesaikan tugas UAT inti.
- Kandidat stabil melewati sedikitnya 10 hari kerja pilot tanpa insiden kritis baru, jika kriteria ini disahkan pada L07.
- Sasaran awal performa staging: 30 sesi pengguna bersamaan selama 30 menit, p95 API nonmedia maksimal 2 detik, dan kegagalan teknis di bawah 1%. Angka ini belum merupakan SLA dan harus disahkan untuk ukuran pilot aktual.

## 5. Non-Tujuan dan Batas Produk

MVP tidak bertujuan untuk:

- Menggantikan keputusan akademik Mentor, Dosen, atau pengelola dengan AI.
- Menilai keimanan peserta atau menjadikan refleksi/pengamalan sebagai skor otomatis.
- Menyediakan video call internal; sesi sinkron dapat memakai tatap muka atau layanan eksternal.
- Menyediakan aplikasi Android sebelum web dan kontrak API stabil.
- Menjalankan finalisasi akademik tanpa koneksi internet.
- Mengunggah dan menyimpan video langsung di platform pada versi pilot; MVP menggunakan tautan video yang diizinkan.
- Menjamin semua fungsi berjalan offline hanya karena aplikasi PWA-ready.
- Membuka seluruh rekaman individual kepada admin hanya karena admin dapat melihat laporan agregat.
- Menetapkan agregasi M/D, jumlah atau bobot soal, aturan ujian ulang, dan kebijakan retensi sebelum disahkan.

## 6. Pengguna dan Hak Akses

### 6.1 Peserta

Tujuan pengguna:

- Melihat target, kalender, progres, dan tugas berikutnya.
- Mengajukan setoran tema dan mengirim tautan video bagian.
- Melihat hasil, koreksi, audio mentor, dan tindak lanjut.
- Mengetahui kesiapan ujian dan nilai ketika komponen telah lengkap.

Batas akses: hanya data, media, jadwal, dan hasil milik sendiri. Peserta tidak boleh menerima acuan jawaban penguji.

### 6.2 Mentor

Tujuan pengguna:

- Mengelola antrean peserta binaan.
- Mencatat sesi setoran tema, kejadian, skor, hasil, dan arahan perbaikan.
- Memeriksa kelayakan video sebelum melakukan penilaian akademik.
- Memberi penilaian video, audio umpan balik, dan memantau riwayat peserta.

Batas akses: peserta yang berada dalam penugasan aktif. Mentor tidak menetapkan nilai Dosen atau mengakses peserta di luar binaan.

### 6.3 Dosen

Tujuan pengguna:

- Melihat peserta yang memenuhi prasyarat ujian.
- Menyusun paket soal dari sumber aplikasi atau soal dosen.
- Melaksanakan, menyimpan draft, dan memfinalkan ujian.
- Meninjau rekap ujian dan kelengkapan nilai.

Batas akses: peserta ujian sesuai penugasan. Acuan jawaban hanya tersedia untuk penguji berwenang.

### 6.4 Admin Jurusan

Tujuan pengguna:

- Mengelola peserta, angkatan, mentor, dosen, dan masa penugasan.
- Mengelola kalender angkatan dan perubahan tenggat sesuai mandat.
- Melihat laporan operasional jurusan dan mengekspor data yang diizinkan.

Batas akses: jurusan sendiri. Akses laporan tidak otomatis memberikan hak mengubah skor atau membaca seluruh media.

### 6.5 Admin Fakultas

Tujuan pengguna:

- Mengelola admin jurusan dan kebijakan lintas jurusan.
- Meninjau laporan agregat, versi rubrik, status pengesahan, dan audit.
- Mengesahkan kebijakan atau perubahan hanya jika memiliki mandat eksplisit.

Batas akses: fakultas dan mandat pengesahan yang diberikan. Hak koreksi hasil dan akses media harus dinyatakan secara terpisah.

## 7. Prinsip Produk

1. **Keputusan manusia tetap utama.** Sistem mendukung dan memvalidasi proses, bukan menggantikan penilai.
2. **Bukti dipisahkan dari keputusan.** Kejadian, kesalahan terhitung, skor manual, status capaian, dan kelulusan adalah konsep yang berbeda.
3. **Draft berbeda dari final.** Draft boleh belum lengkap; final wajib lolos validasi data, kewenangan, prasyarat, dan versi.
4. **Riwayat tidak ditimpa.** Perubahan penilaian, tenggat, kebijakan, media, dan penugasan dibuat sebagai versi atau koreksi baru.
5. **Server menjadi sumber kebenaran.** Nomor kesempatan, progres, kesiapan ujian, nilai, dan status kelulusan dihitung oleh backend.
6. **Akses diperiksa per objek.** Peran saja tidak cukup; organisasi, penugasan, masa berlaku, kepemilikan, dan status objek juga diperiksa.
7. **Nilai kosong bukan nol.** Komponen yang belum tersedia ditampilkan sebagai `Belum dinilai` dan tidak boleh diganti dengan 0 atau 1.
8. **Status teknis berbeda dari status akademik.** Video tidak layak secara teknis tidak berarti hafalan gagal.
9. **Warna bukan satu-satunya penanda.** Semua status harus memiliki label teks, penjelasan, dan tindakan berikutnya.

## 8. Lingkup MVP

### 8.1 P0 - wajib untuk pilot

- Akun, login, pemulihan akun, sesi, lima peran, dan penugasan berbatas waktu.
- Kurikulum 44 tema dalam lima bagian dan kalender 52 pekan.
- Pengajuan dan pencatatan setoran tema sinkron.
- Penilaian tema per kesempatan 1-5.
- Pengiriman tautan video bagian, pemeriksaan kelayakan, dan versi media pengganti.
- Penilaian akademik video, insiden/kesalahan, skor manual, audio mentor, dan riwayat revisi.
- Progres tema, bagian, kesiapan ujian, dan tindak lanjut.
- Paket soal, pelaksanaan Ujian Dosen, skor manual, dan rekap ujian.
- Skor keaktifan K, komponen M dan D setelah agregasinya disahkan, nilai akhir N, dan status kelulusan.
- Audit, koreksi hasil, laporan dasar, backup, restore, monitoring, dan dukungan pilot.
- 20 layar inti sebagaimana dirinci pada Bagian 13.

### 8.2 P1 - setelah alur inti stabil

- Pengingat otomatis.
- Ekspor dan laporan lanjutan.

### 8.3 Ditunda

- Penilaian AI.
- Gamifikasi dan leaderboard.
- Aplikasi Android.
- Video call internal.
- Unggah video langsung ke platform.
- Sinkronisasi penilaian offline.

## 9. Struktur Kurikulum dan Kalender

### 9.1 Kurikulum

- Total 44 tema.
- Bagian 1: 10 tema.
- Bagian 2: 8 tema.
- Bagian 3: 6 tema.
- Bagian 4: 5 tema.
- Bagian 5: 15 tema.
- Model data wajib mendukung satu tema yang terdiri atas lebih dari satu rentang ayat atau surah.
- Kurikulum harus memiliki versi; versi yang sudah diterbitkan tidak boleh ditimpa.

### 9.2 Kalender program

| Periode | Aktivitas |
|---|---|
| Pekan 1-10 | Tema Bagian 1 |
| Pekan 11 | Video Bagian 1 |
| Pekan 12-19 | Tema Bagian 2 |
| Pekan 20 | Video Bagian 2 |
| Pekan 21-26 | Tema Bagian 3 |
| Pekan 27 | Video Bagian 3 |
| Pekan 28-32 | Tema Bagian 4 |
| Pekan 33 | Video Bagian 4 |
| Pekan 34-48 | Tema Bagian 5 |
| Pekan 49 | Video Bagian 5 |
| Pekan 50-51 | Cadangan |
| Pekan 52 | Ujian Dosen |

Tanggal riil, hari libur, dan tenggat efektif ditetapkan per angkatan. Semua tampilan tanggal dan perhitungan hari menggunakan zona waktu Asia/Jakarta.

## 10. Alur Utama Produk

### 10.1 Pendaftaran dan penugasan

1. Admin Jurusan membuat atau mengimpor akun peserta.
2. Admin menetapkan jurusan, angkatan, versi kurikulum, Mentor, Dosen, dan masa berlaku penugasan.
3. Sistem memvalidasi duplikasi dan lingkup organisasi.
4. Perubahan penugasan membuat riwayat baru tanpa menghapus atribusi penilai sebelumnya.
5. Pengguna hanya memperoleh menu dan data sesuai mandat aktif.

### 10.2 Setoran tema sinkron

1. Peserta memilih minimal satu tema dari bagian aktif.
2. Semua tema dalam satu pengajuan harus berasal dari bagian yang sama.
3. Peserta memilih metode tatap muka atau video call, mengusulkan waktu, dan menambahkan catatan.
4. Pengajuan dijadwalkan bersama Mentor.
5. Saat sesi benar-benar berlangsung, Mentor mencatat tanggal aktual, kejadian, tindakan bantuan, koreksi, skor manual 1-10, dan hasil per tema.
6. Mentor menyimpan draft, meninjau data, lalu memfinalkan.
7. Hasil tema adalah `Cukup` atau `Mengulang`.
8. Kesempatan per tema bernomor 1-5. Hasil belum Cukup pada kesempatan kelima menjadi `Perlu Tindak Lanjut Mentor`; sistem tidak membuka kesempatan keenam otomatis.
9. Tanggal setoran pertama hanya berasal dari sesi aktual pertama yang sah dan tidak berubah akibat pengajuan jadwal atau pengulangan.

### 10.3 Setoran video bagian

1. Video hanya dapat dikirim setelah semua tema pada bagian tersebut berstatus Cukup.
2. Peserta memilih bagian, siklus/revisi, memasukkan tautan video, tanggal rekam, dan pernyataan kelengkapan.
3. Mentor melakukan pemeriksaan teknis berdasarkan checklist.
4. Jika `Tidak Layak`, Mentor wajib memberi alasan. Peserta mengirim versi media pengganti pada slot akademik yang sama.
5. Jika `Layak`, Mentor melanjutkan ke penilaian akademik.
6. Mentor mencatat kejadian, kategori utama, lokasi ayat/waktu, koreksi mandiri, skor manual, catatan, dan audio umpan balik.
7. Audio mentor wajib tersedia sebelum finalisasi penilaian video.
8. Total 0-3 kesalahan terhitung menghasilkan `Cukup`; 4 atau lebih menghasilkan `Belum Cukup`.
9. Status Cukup tidak memiliki ambang skor manual tambahan.
10. Satu siklus memiliki setoran awal (`revisi 0`) dan maksimal tiga revisi akademik (`revisi 1-3`). Jika revisi 3 tetap Belum Cukup, sistem membuka siklus baru pada revisi 0.
11. Video Cukup membuka bagian berikutnya. Lima bagian Cukup membuka Ujian Dosen.

### 10.4 Ujian Dosen

1. Sistem menampilkan peserta yang seluruh lima bagiannya Cukup.
2. Dosen yang ditugaskan menyusun paket soal dari bank aplikasi dan/atau soal Dosen.
3. Jenis soal yang didukung: sambung tiga ayat, pengenalan/urutan surah, dan pelafalan surah atau tema.
4. Acuan jawaban hanya dapat dibaca penguji berwenang.
5. Dosen mencatat bukti pelaksanaan, bantuan/kesalahan, catatan, serta skor manual 1-10.
6. Draft dapat ditinjau. Finalisasi mewajibkan prasyarat, paket soal sah, bukti pelaksanaan, dan skor valid.
7. Ujian final wajib ada sebelum peserta dapat dinyatakan Lulus.

### 10.5 Nilai dan kelulusan

1. Sistem menghitung K dari ketepatan waktu 44 tema.
2. Sistem menghitung M dan D hanya setelah metode agregasinya disahkan.
3. Ketika K, M, dan D lengkap dan Ujian Dosen final, sistem menghitung:

   `N = 0,2K + 0,4M + 0,4D`

4. Peserta Lulus jika N minimal 6.
5. Tidak ada ambang nilai Dosen tersendiri.
6. Nilai kosong tidak diganti dengan 0 atau 1.
7. Koreksi membuat snapshot nilai baru dan mempertahankan snapshot lama.
8. Jika koreksi mencabut prasyarat, hasil terkait menjadi `Perlu Peninjauan` dan kelulusan baru diblokir sampai dampaknya diselesaikan.

## 11. Aturan Penilaian

### 11.1 Skor manual Mentor dan Dosen

| Skor | Predikat | Pedoman |
|---|---|---|
| 1-4 | Perlu banyak bimbingan | Hafalan/jawaban belum dikuasai, sering terhenti atau keliru, banyak bantuan, dan pelafalan masih memerlukan banyak perbaikan. |
| 5-7 | Mulai menguasai | Sebagian besar benar tetapi belum konsisten, masih memerlukan beberapa kode/bantuan, dan masih ada kesalahan pelafalan yang perlu diperbaiki. |
| 8-10 | Menguasai dengan baik | Hafalan lancar, jawaban tepat, pelafalan baik, dan dapat menyelesaikan mandiri atau dengan sedikit kode. |

Angka bawah digunakan ketika peserta baru memenuhi kriteria, angka tengah ketika cukup konsisten, dan angka atas ketika memenuhi dengan kuat. Skor 10 menunjukkan penguasaan sangat baik dan mandiri. Input kosong, kurang dari 1, atau lebih dari 10 ditolak. Dukungan skor desimal menunggu keputusan L05.

### 11.2 Kejadian dan kesalahan

Setiap kejadian penilaian minimal menyimpan:

- Lokasi ayat dan/atau waktu video.
- Satu kategori utama.
- Konteks kejadian.
- Tindakan Mentor: tanpa bantuan, kode/isyarat, atau bantuan jawaban.
- Apakah peserta mengoreksi diri.
- Apakah kejadian dihitung sebagai kesalahan.
- Alasan penghitungan atau pengecualian.
- Catatan penilai.

Kategori pelafalan meliputi huruf, syiddah, mad, tajwid, dan waqf-ibtida. Pada video bagian, kategori hafalan juga mencakup kesalahan harakat, huruf, atau pilihan kata.

Koreksi mandiri yang memenuhi aturan tidak dihitung sebagai kesalahan. Satu kejadian hanya memiliki satu kategori utama. Detail koreksi setelah isyarat, arti `langsung`, dan kejadian berulang mengikuti keputusan L04.

### 11.3 Rangkaian diam pada setoran tema

Baseline yang telah ditetapkan:

1. Peserta diam.
2. Mentor menunggu maksimal 30 detik.
3. Mentor memberi bantuan.
4. Peserta mengulang.
5. Jika tetap diam, kejadian dihitung salah.

Detail jendela pengulangan dan dampak variasi bantuan tetap menunggu L04.

### 11.4 Skor keaktifan K

| Waktu setoran pertama dibanding tenggat | Skor K per tema |
|---|---:|
| Tepat waktu atau lebih awal | 10 |
| Terlambat 1-7 hari | 9 |
| Terlambat 8-14 hari | 8 |
| Terlambat 15-21 hari | 7 |
| Terlambat 22-28 hari | 6 |
| Terlambat 29-35 hari | 5 |
| Terlambat 36-42 hari | 4 |
| Terlambat 43-49 hari | 3 |
| Terlambat lebih dari 49 hari | 2 |
| Belum setor saat periode ditutup | 1 |

K final adalah rata-rata seluruh 44 tema. Pada rekap sementara, sistem wajib menampilkan cakupan yang sudah dinilai dan jumlah target tertunggak. Target yang belum jatuh tempo tidak otomatis bernilai 1. Hasil tema `Mengulang` tidak mengubah skor ketepatan waktu setoran pertama.

## 12. Kebutuhan Fungsional

Kode `FR` di bawah mempertahankan keterlacakan ke katalog `F01-F36` pada rancangan sumber.

### 12.1 Administrasi dan tata kelola

| ID | Kebutuhan | Prioritas MVP |
|---|---|---|
| FR-F01 | Ringkasan fakultas per jurusan/periode, termasuk progres dan kelulusan; skor AI hanya jika fitur tersedia. | P0 - laporan dasar |
| FR-F02 | Laporan periodik dan ekspor sesuai hak akses. | P1 untuk ekspor lanjutan |
| FR-F03 | Pengangkatan, penonaktifan, dan penugasan Admin Jurusan. | P0 |
| FR-F04 | Pengelolaan kebijakan program, target periode, dan parameter kelulusan yang berversi. | P0 setelah keputusan terkait disahkan |
| FR-F05 | Riwayat tindakan penting dan perubahan data. | P0 |
| FR-F06 | Pendaftaran, impor, perubahan status, dan penugasan pengguna jurusan. | P0 |
| FR-F07 | Ringkasan operasional jurusan dan peserta yang memerlukan perhatian. | P0 |
| FR-F08 | Pengelolaan data Mentor, kapasitas, kualifikasi, dan perpindahan binaan. | P0; parameter kapasitas terbuka |
| FR-F09 | Pengelolaan kurikulum, tema, target, dan catatan program. | P0 |
| FR-F10 | Pengelolaan periode, jadwal evaluasi, kuota, dan pengajuan khusus. | P0 sesuai mandat |
| FR-F11 | Laporan jurusan menurut peserta, angkatan, Dosen, dan Mentor. | P0 - laporan dasar |

### 12.2 Pengawasan Dosen dan pendampingan Mentor

| ID | Kebutuhan | Prioritas MVP |
|---|---|---|
| FR-F12 | Dashboard Dosen untuk Mentor dan peserta dalam pembinaannya. | P0 |
| FR-F13 | Peninjauan riwayat dan validasi kelulusan akhir disertai catatan. | P0 |
| FR-F14 | Pemantauan kualitas penilaian Mentor; perbandingan AI hanya jika kelak dinyatakan layak. | P0 tanpa AI |
| FR-F15 | Rekomendasi bimbingan khusus dan perbaikan kurikulum. | P0 berupa catatan/rekomendasi |
| FR-F16 | Ekspor data riset dengan penghilangan identitas dan kontrol akses. | Di luar P0 hingga mandat/retensi disahkan |
| FR-F17 | Daftar binaan, antrean setoran, filter progres, dan pemberitahuan. | P0; notifikasi otomatis P1 |
| FR-F18 | Riwayat latihan, penilaian, pola kesalahan, dan progres individu. | P0 |
| FR-F19 | Form penilaian tema dan video bagian dengan kategori dan koreksi mandiri. | P0 |
| FR-F20 | Catatan bimbingan teknis dan motivasi yang terlihat oleh pihak berwenang. | P0 |
| FR-F21 | Laporan binaan dan rekomendasi evaluasi akhir. | P0 - laporan dasar |

### 12.3 Aktivitas peserta

| ID | Kebutuhan | Prioritas MVP |
|---|---|---|
| FR-F22 | Dashboard target, progres, hasil, dan tindak lanjut pribadi. | P0 |
| FR-F23 | Daftar tema, rentang ayat, materi, urutan, dan target latihan. | P0 |
| FR-F24 | Latihan mandiri dan umpan balik AI jika diaktifkan. | Latihan dasar P0; AI ditunda |
| FR-F25 | Riwayat kesalahan menurut lokasi, kategori, waktu, dan perbaikan. | P0 |
| FR-F26 | Pengajuan setoran tema dan pemilihan jadwal yang tersedia. | P0 |
| FR-F27 | Tampilan hasil Mentor, catatan, status, dan rekomendasi latihan. | P0 |
| FR-F28 | Penghargaan aktivitas, pengingat, motivasi, dan leaderboard opsional. | Pengingat P1; gamifikasi ditunda |
| FR-F29 | Pengiriman rekaman video bagian dan kepastian status penerimaannya. | P0 sebagai tautan video |
| FR-F30 | Pencatatan siklus latihan, murajaah, dan target yang disesuaikan. | P0 untuk riwayat dasar |
| FR-F31 | Materi makna, refleksi, dan pengamalan pendukung YAQin. | Konten dasar bila tersedia; bentuk/visibilitas terbuka |

### 12.4 Kebutuhan lintas pengguna

| ID | Kebutuhan | Prioritas MVP |
|---|---|---|
| FR-F32 | Login, sesi, pemulihan akses, dan batas akses per objek. | P0 |
| FR-F33 | Riwayat percobaan setoran, versi rubrik, dan alasan revisi hasil. | P0 |
| FR-F34 | Penanganan unggahan gagal dan retry tanpa duplikasi. | P0 untuk audio/aksi finalisasi |
| FR-F35 | Notifikasi kegiatan dan antrean yang relevan. | P1; indikator dalam aplikasi P0 |
| FR-F36 | Kurikulum yang mendukung tema lintas surah dan pemetaan bagian. | P0 |

## 13. Kebutuhan Layar

### 13.1 Layar umum dan peserta

| ID | Layar | Informasi utama | Tindakan/perilaku utama |
|---|---|---|---|
| G01 | Masuk dan pemulihan akun | Identitas akun, sandi, pemulihan, konteks peran sah | Masuk tanpa membocorkan keberadaan akun pada pesan gagal |
| P01 | Beranda peserta | Target pekan, tugas berikutnya, progres tema/bagian, jadwal, tunggakan | Membuka tugas paling relevan atau mengajak mengajukan sesi |
| P02 | Target dan kalender | 44 tema, lima bagian, tenggat efektif, tanggal pertama, hasil, K | Memilih tema aktif; bagian terkunci menampilkan alasan |
| P03 | Pengajuan sesi | Tema, metode, usulan waktu, catatan | Minimal satu tema dan hanya satu bagian per pengajuan |
| P04 | Kirim video bagian | Bagian, siklus/revisi, tautan, tanggal rekam, checklist peserta | Aktif setelah semua tema Cukup; pengganti teknis mempertahankan slot revisi |
| P05 | Hasil dan tindak lanjut | Hasil tema/video, alasan teknis, insiden, catatan, audio | Menawarkan tindakan sesuai status: ganti media atau revisi hafalan |
| P06 | Ujian dan nilai | Kesiapan lima bagian, jadwal ujian, K/M/D/N | Menampilkan `Siap Ujian`, `Belum dinilai`, atau hasil tanpa kelulusan manual |

### 13.2 Layar Mentor

| ID | Layar | Informasi utama | Tindakan/perilaku utama |
|---|---|---|---|
| M01 | Binaan dan antrean | Binaan, sesi hari ini, video menunggu, tindak lanjut | Filter pekerjaan tanpa akses lintas penugasan |
| M02 | Catatan pembimbingan | Sesi, tema, kesempatan, kejadian, skor, catatan, hasil | Simpan draft/final; kesempatan kelima gagal menjadi tindak lanjut |
| M03 | Kelayakan video | Versi video, checklist, Layak/Tidak Layak, alasan | Hanya Layak yang membuka penilaian; penolakan wajib beralasan |
| M04 | Penilaian video | Kejadian, kategori, lokasi, koreksi mandiri, skor, audio | Hitung status dari kesalahan; audio wajib sebelum final |
| M05 | Rekap peserta | Riwayat tema/bagian, K, penilaian efektif, tindak lanjut | Meninjau komponen M; agregasi tidak aktif sebelum disahkan |

### 13.3 Layar Dosen

| ID | Layar | Informasi utama | Tindakan/perilaku utama |
|---|---|---|---|
| D01 | Antrean ujian | Peserta dengan lima bagian Cukup, jadwal, riwayat | Memulai ujian hanya untuk peserta dan Dosen yang berhak |
| D02 | Paket soal | Sumber, jenis soal, stimulus/cakupan, acuan jawaban | Menyimpan paket sesuai kebijakan jumlah/bobot yang disahkan |
| D03 | Pelaksanaan ujian | Paket, catatan bantuan/kesalahan, skor, tanggal, penguji | Simpan draft; finalisasi wajib bukti dan skor sah |
| D04 | Rekap ujian | Jawaban, skor, hasil ujian, nilai gabungan | Nilai kosong tetap kosong; tidak ada ambang Dosen terpisah |

### 13.4 Layar admin

| ID | Layar | Informasi utama | Tindakan/perilaku utama |
|---|---|---|---|
| J01 | Peserta dan penugasan | Akun, NIM, jurusan, angkatan, Mentor, Dosen, masa berlaku | Validasi duplikat dan pertahankan riwayat penugasan |
| J02 | Kalender angkatan | Tanggal awal/tutup, 52 pekan, 44 target, jadwal, libur | Pratinjau dampak; perubahan tenggat wajib alasan/persetujuan/audit |
| J03 | Laporan jurusan | Progres, keterlambatan, antrean video/ujian, nilai belum lengkap | Filter angkatan dan ekspor sesuai mandat |
| F01 | Kebijakan dan laporan fakultas | Versi rubrik, status persetujuan, agregat, audit | Versi baru tidak menimpa penilaian lama; pengesahan sesuai mandat |

## 14. Status dan Perilaku Antarmuka

Status minimum yang perlu dimodelkan secara eksplisit:

- Sesi: `Diajukan`, `Dijadwalkan`, `Berlangsung`, `Selesai`, `Tidak Hadir`, `Dibatalkan`.
- Penilaian: `Draft`, `Final`, `Perlu Peninjauan`.
- Tema: `Belum`, `Latihan`, `Cukup`, `Mengulang`, `Perlu Tindak Lanjut`.
- Versi media: `Draft`, `Dikirim`, `Memproses`, `Siap`, `Gagal`.
- Kelayakan video: `Belum Diperiksa`, `Layak`, `Tidak Layak`.
- Video bagian: `Belum Dikirim`, `Dalam Review`, `Cukup`, `Belum Cukup`.
- Program: `Belum Siap`, `Siap Ujian`, `Ujian Berlangsung`, `Menunggu Nilai`, `Lulus`, `Belum Lulus`, `Perlu Tindak Lanjut`.
- Kebijakan: `Draft`, `Disetujui`, `Terbit`, `Nonaktif`.

Contoh pesan wajib:

- Bagian terkunci: jelaskan prasyarat yang belum selesai dan sediakan tautan ke hasil sebelumnya.
- Video tidak layak: tampilkan alasan dan jelaskan bahwa penggantian teknis tidak memakai revisi hafalan.
- Nilai belum lengkap: sebutkan komponen yang belum tersedia.
- Konflik versi: minta pengguna memuat ulang dan meninjau perubahan sebelum finalisasi.
- Koneksi terputus: nyatakan bahwa data belum terkonfirmasi tersimpan dan sediakan retry aman.

## 15. Model Data Konseptual

Kelompok entitas minimum:

### 15.1 Identitas dan organisasi

- `users`
- `organizations` dengan struktur fakultas/jurusan
- `role_grants` dengan masa berlaku
- `cohorts`
- `enrollments`
- `assignments`

### 15.2 Kurikulum dan kalender

- `curriculum_versions`
- `parts`
- `themes`
- `theme_ranges` untuk satu atau lebih rentang per tema
- `targets`
- `deadline_changes`

### 15.3 Pembimbingan dan video

- `sessions`
- `theme_assessments`
- `video_attempts`
- `video_versions`
- `eligibility_reviews`
- `video_assessments`
- `incidents`
- `media_assets`
- `corrections`

### 15.4 Ujian, nilai, dan audit

- `question_bank`
- `exams`
- `exam_items` dengan snapshot soal dan acuan
- `exam_scores`
- `policy_versions`
- `grade_snapshots`
- `audit_events`

Semua entitas menggunakan ID internal stabil. NIM dan identitas login adalah atribut unik dalam lingkup institusi, bukan pengganti primary key. Seluruh relasi akademik menggunakan foreign key. Timestamp disimpan sebagai waktu absolut; tanggal tenggat dan hitungan hari menggunakan Asia/Jakarta.

## 16. API dan Integrasi

### 16.1 Prinsip API

- API berversi dengan prefix `/api/v1`.
- Web dan Android menggunakan aturan bisnis serta sumber data yang sama.
- Respons berhasil memuat `data`, `version`, dan `request_id`.
- Respons gagal memuat `code`, `message`, `field_errors` bila relevan, dan `request_id`.
- Gunakan 401 untuk sesi tidak sah, 403 untuk tindakan terlarang, 404 untuk objek di luar lingkup/tidak tersedia, 409 untuk konflik versi atau prasyarat, 422 untuk data tidak valid, dan 429 untuk pembatasan permintaan.
- Operasi finalisasi mengirim `expected_version` dan `Idempotency-Key`.
- Kunci idempotensi diikat pada aktor, endpoint, dan hash isi.

### 16.2 Kontrak awal

| Operasi | Endpoint awal |
|---|---|
| Baca target sendiri | `GET /api/v1/me/targets` |
| Ajukan sesi | `POST /api/v1/sessions` |
| Finalkan tema | `POST /api/v1/theme-assessments/{id}/finalize` |
| Kirim versi video | `POST /api/v1/video-attempts/{id}/versions` |
| Finalkan kelayakan | `POST /api/v1/video-versions/{id}/eligibility` |
| Finalkan penilaian video | `POST /api/v1/video-assessments/{id}/finalize` |
| Buat ujian | `POST /api/v1/exams` |
| Finalkan ujian | `POST /api/v1/exams/{id}/finalize` |
| Baca rekap | `GET /api/v1/enrollments/{id}/grades` |
| Ajukan koreksi | `POST /api/v1/corrections` |

OpenAPI lengkap dibuat saat implementasi setelah keputusan yang memengaruhi skema disahkan.

## 17. Kebutuhan Nonfungsional

### 17.1 Keamanan dan privasi

- Seluruh komunikasi menggunakan HTTPS.
- Akses diperiksa di server berdasarkan peran, kepemilikan, organisasi, penugasan, masa berlaku, dan status objek.
- ID yang sulit ditebak tidak dianggap sebagai kontrol akses.
- Untuk web satu domain, gunakan cookie `Secure`, `HttpOnly`, dan `SameSite`, serta proteksi CSRF pada perubahan data.
- Kredensial di-hash dengan pustaka yang terpelihara.
- Akun admin menggunakan faktor tambahan bila infrastruktur mendukung.
- Audio disimpan privat; URL akses berumur pendek diberikan setelah pemeriksaan izin.
- Video eksternal dibatasi ke skema HTTPS dan host yang diizinkan tanpa server melakukan fetch ke URL sembarang.
- Jangan mencatat sandi, token, cookie, URL media bertanda tangan, atau isi rekaman pada log umum.
- Kebijakan persetujuan penggunaan rekaman, retensi, penghapusan, akses setelah lulus, dan penggunaan riset harus disahkan sebelum data nyata dipakai.
- Tidak ada izin tersirat untuk memakai rekaman sebagai data pelatihan AI.

### 17.2 Keandalan dan integritas

- Finalisasi penilaian, audit, progres, dan event outbox disimpan dalam satu transaksi atomik.
- Unique constraint dan idempotensi mencegah hasil atau kesempatan ganda.
- Retry setelah timeout menggunakan kunci yang sama dan dapat membaca hasil transaksi sebelumnya.
- Pekerja latar tidak boleh membatalkan transaksi akademik yang telah sah.
- Penggantian teknis media tidak menggunakan slot revisi akademik.
- Koreksi dan versi baru tidak menimpa riwayat final.

### 17.3 Performa dan kapasitas

- Target awal p95 API nonmedia maksimal 2 detik pada profil pilot yang disahkan.
- Media diukur terpisah berdasarkan ukuran dan koneksi.
- Daftar menggunakan paginasi dan filter server-side.
- Target kapasitas pilot, persentil, beban, dan error budget ditetapkan melalui L07.

### 17.4 Responsivitas dan aksesibilitas

- Bahasa utama adalah Bahasa Indonesia.
- Teks Arab, arah baca, font, dan rentang ayat diuji di perangkat nyata.
- Layar diuji pada lebar 390, 768, dan 1280 piksel serta zoom 200%.
- Semua input memiliki label yang selalu terlihat.
- Urutan fokus, Tab, Shift+Tab, Enter, dialog, dan pesan kesalahan dapat digunakan dengan keyboard.
- Status tidak bergantung pada warna dan perubahan status diumumkan melalui area yang dapat dibaca screen reader.
- Tabel lebar bergulir di area sendiri tanpa membuat seluruh halaman melebar.
- Target sentuh memadai dan fokus keyboard terlihat.
- Audio tidak diputar otomatis.

### 17.5 Backup, pemulihan, dan observabilitas

- Pisahkan lingkungan development, staging, dan pilot production.
- Basis data tidak dapat diakses langsung dari internet.
- Backup basis data dilakukan harian dan sebelum migrasi; media memiliki versioning/backup.
- Restore diuji di lingkungan terisolasi sebelum pilot.
- Usulan awal RPO 24 jam dan RTO 4 jam menunggu pengesahan L07.
- Pantau kegagalan API, waktu respons, antrean review, penyimpanan, pekerja latar, dan backup.
- Gunakan `request_id` untuk penelusuran tanpa membocorkan data pribadi.

## 18. Arsitektur Produk

MVP menggunakan pola modular monolith:

- Web responsif untuk lima peran.
- Satu API bersama.
- Modul domain: akun, kurikulum, kalender, pembimbingan, video, ujian, penilaian, laporan, dan audit.
- Satu basis data relasional.
- Penyimpanan privat untuk audio dan lampiran.
- Pekerja latar untuk ekspor dan pekerjaan tertunda.

Pemilihan framework, versi perangkat lunak, penyedia hosting, dan biaya operasional tidak dikunci oleh PRD ini. Keputusan teknologi mempertimbangkan kemampuan tim, dukungan hosting, pemeliharaan, keamanan, dan biaya.

## 19. Analitik Produk dan Pelaporan

Data operasional minimum yang perlu tersedia:

- Jumlah peserta aktif per jurusan/angkatan.
- Progres tema dan bagian.
- Tema atau peserta tertunggak.
- Antrean setoran tema, video, dan ujian.
- Jumlah video Tidak Layak beserta kategori alasan.
- Jumlah peserta pada status Perlu Tindak Lanjut.
- Kelengkapan K/M/D/N tanpa mengganti nilai kosong.
- Jumlah dan jenis koreksi hasil/tenggat.
- Keberhasilan/gagal finalisasi dan konflik versi.
- Insiden akses, error API, pekerjaan latar, backup, dan restore.

Pelaporan agregat tidak memberikan akses otomatis ke media individual. Ekspor harus dibatasi mandat, diaudit, dan menerapkan penghilangan identitas bila dipakai untuk riset.

## 20. Kriteria Penerimaan Utama

| ID | Skenario | Hasil yang diharapkan |
|---|---|---|
| AC-01 | Peserta mengirim video sebelum semua tema Cukup | Ditolak dengan daftar tema yang belum Cukup |
| AC-02 | Satu sesi memuat tema dari dua bagian | Tidak dapat difinalkan |
| AC-03 | Tema tepat waktu tetapi hasil Mengulang | Skor keaktifan tetap 10 |
| AC-04 | Setoran pertama terlambat 8 hari | Skor K tema = 8 |
| AC-05 | Video tidak layak dua kali | Slot revisi akademik tetap; alasan dan versi media tersimpan |
| AC-06 | Video layak dengan empat kejadian dan satu koreksi mandiri yang sah | Total terhitung 3; status Cukup jika audio dan data lain lengkap |
| AC-07 | Video layak dengan tiga kesalahan tanpa audio | Finalisasi diblokir |
| AC-08 | Skor kosong, 0, atau 11 | Ditolak; 1 dan 10 diterima |
| AC-09 | Revisi akademik 3 tetap Belum Cukup | Sistem membuka siklus baru pada revisi 0 |
| AC-10 | K=10, M=10, tetapi belum ujian | Belum Lulus; status tetap Siap Ujian |
| AC-11 | K=10, M=10, D=1 dan ujian final | N=6,4 dan Lulus |
| AC-12 | Pengguna di luar penugasan mencoba membaca rekaman | API menolak akses |
| AC-13 | Dua penilai memfinalkan versi berbeda | Konflik ditampilkan; hasil tidak tertimpa |
| AC-14 | Layar pada lebar 390 piksel dan navigasi keyboard | Isi terbaca, tindakan terjangkau, dan fokus terlihat |
| AC-15 | Retry finalisasi dengan Idempotency-Key yang sama | Hanya satu hasil dan satu kenaikan kesempatan |
| AC-16 | Nilai M atau D belum tersedia | N tidak dihitung; komponen tampil `Belum dinilai` |
| AC-17 | Perubahan tenggat disahkan | Nilai lama/baru, alasan, penyetuju, dan dampak K tercatat |
| AC-18 | Mentor pengganti mengakses peserta setelah masa penugasan aktif | Akses baru sah; atribusi penilai lama tetap ada |

## 21. Strategi Pengujian

### 21.1 Lapisan pengujian

- **Unit:** batas hari K, hitungan kesalahan, validasi skor, prasyarat, dan rumus.
- **Integrasi:** izin, relasi data, media, transaksi, konflik versi, retry, dan audit.
- **Sistem:** alur layar ke API, basis data, dan pembacaan ulang setelah login ulang.
- **Keamanan:** akses lintas objek, CSRF, sesi, media privat, input berbahaya, dan data sensitif pada log.
- **Operabilitas:** backup, restore, migrasi, rollback, monitoring, dan kegagalan pekerja latar.
- **UAT:** perwakilan lima peran menyelesaikan tugas nyata dengan bahasa operasional.
- **Kinerja:** profil beban yang disahkan untuk staging dan pilot.

### 21.2 Data uji minimum

- Dua jurusan dan dua angkatan.
- Kelima peran.
- Peserta pada setiap status utama.
- Penugasan aktif dan kedaluwarsa.
- 44 target dalam lima bagian.
- Sesi tema kesempatan 1-5.
- Video awal, revisi, dan beberapa versi media.
- Paket yang memuat tiga jenis soal.
- Nilai lengkap dan kosong.
- Audio dummy yang legal dipakai, berkas rusak, ukuran berlebih, dan URL kedaluwarsa.
- Tenggat tepat pada batas hari Asia/Jakarta.
- Dataset koreksi dan konflik versi.

### 21.3 Penerimaan UAT

- Semua tugas inti peran selesai.
- Hasil akademik sama dengan dataset acuan independen.
- Tidak ada isu S1 atau S2 terbuka.
- Isu S3/S4 hanya dapat ditunda dengan alasan, pemilik, target perbaikan, dan cara aman melanjutkan.
- Penerimaan dicatat pada berita acara; penerimaan tampilan saja tidak cukup.

## 22. Rencana Implementasi

Urutan paket tidak menjadi komitmen durasi sebelum kapasitas tim dan keputusan L01-L08 tersedia.

| Urutan | Paket | Hasil demonstrasi/gate |
|---:|---|---|
| 1 | Fondasi akun, akses, kurikulum, kalender | Lima peran dibatasi dengan benar; 44 tema dan 52 pekan terbaca |
| 2 | Pengajuan dan pencatatan sesi tema | Beberapa tema satu bagian; tanggal pertama dan kesempatan benar |
| 3 | Video dua tahap dan audio | Versi teknis terpisah dari revisi; audio wajib; progres bagian benar |
| 4 | Keaktifan dan rekap Mentor | Batas hari K benar; agregasi M disahkan sebelum rekap final |
| 5 | Paket dan Ujian Dosen | Prasyarat, jenis soal, jumlah/bobot, dan agregasi D disahkan |
| 6 | Nilai akhir, laporan, koreksi | Kelengkapan, formula, audit, dan riwayat koreksi berfungsi |
| 7 | Verifikasi rilis | Uji terpadu, keamanan, UAT, beban, restore, dan perbaikan |
| 8 | Pilot dan stabilisasi | Penggunaan nyata terbatas, evaluasi, uji ulang, dan keputusan perluasan |

Skenario jadwal awal pada rancangan adalah 18 minggu dengan dua pengembang penuh waktu, QA setengah waktu, dukungan operasi seperlima waktu, dan wakil pengelola yang aktif mengambil keputusan. Jadwal ini hanya asumsi perencanaan dan harus dihitung ulang setelah paket fondasi.

## 23. Strategi Pilot dan Rilis

### 23.1 Usulan pilot

- Satu jurusan.
- Kelompok kecil sekitar 10-30 peserta.
- Mentor, Dosen, dan admin terkait.
- Dua minggu untuk memvalidasi operasional yang terjadi selama periode tersebut.
- Staging dengan fixture status lengkap digunakan untuk menguji alur satu tahun yang tidak mungkin dibuktikan hanya melalui pilot dua minggu.

Ukuran final pilot, perangkat/browser, kapasitas media, jam dukungan, dan kriteria stabil harus disahkan pada L07.

### 23.2 Gate rilis

- Semua P0 dalam lingkup kandidat selesai.
- Kasus wajib lulus pada build yang diketahui.
- Keputusan kebijakan yang diperlukan telah disahkan.
- Tidak ada kasus wajib berstatus terhalang.
- Akses, media privat, retry, konflik, backup/restore, ujian, dan nilai telah diverifikasi.
- Build, migrasi, konfigurasi, kebijakan, dan rencana rollback tercatat.
- Pengguna pilot, orientasi, kanal insiden, dan petugas dukungan tersedia.
- Keputusan `Go` atau `Tunda` dicatat oleh pihak berwenang.

## 24. Risiko dan Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Rubrik atau agregasi belum disahkan | Hasil Mentor/Dosen dan nilai akhir tidak konsisten | Sahkan aturan berversi dengan contoh kasus sebelum modul final |
| Segmentasi kurikulum keliru | Target dan progres salah | Verifikasi ahli dan gunakan kurikulum berversi |
| Video berat atau tautan tidak dapat diakses | Setoran tertunda | Gunakan tautan pada MVP, validasi host, retry aman, dan alasan teknis jelas |
| Antrean review Mentor meningkat | Umpan balik terlambat | Pantau kapasitas binaan dan antrean; tetapkan batas pada L07 |
| Akses lintas binaan/jurusan | Pelanggaran privasi | Otorisasi per objek, uji negatif, media privat, dan audit |
| Perubahan aturan tanpa versi | Nilai lama tidak dapat dijelaskan | `policy_versions`, snapshot, koreksi, dan audit |
| Retry atau finalisasi bersamaan | Hasil/attempt ganda | Transaksi, row lock, expected version, unique constraint, dan idempotensi |
| Fitur terlalu banyak pada awal | Pilot terlambat | Pertahankan P0/P1/ditunda dan gate perubahan lingkup |
| Integrasi AI belum layak | Ketergantungan biaya/teknis | AI tidak menjadi prasyarat MVP |
| Retensi media belum ditetapkan | Risiko hukum, privasi, dan kapasitas | Sahkan L06 sebelum data nyata |
| Backup belum pernah dipulihkan | Kesiapan semu | Wajib melakukan restore terisolasi sebelum pilot |

## 25. Dependensi

- Pengesahan daftar kurikulum 44 tema dan rentang ayat.
- Penunjukan pemilik akademik, pengelola proyek, dan pihak pengesah kebijakan.
- Ketersediaan Mentor dan Dosen untuk peninjauan rubrik dan UAT.
- Keputusan L01-L08.
- Penyediaan hosting, basis data, penyimpanan privat audio, domain/HTTPS, dan kanal dukungan.
- Sumber audio, teks, terjemahan, serta konten lain yang memiliki izin penggunaan.
- Akun atau metode akses video eksternal yang sesuai kebijakan privasi.

## 26. Keputusan Terbuka

| ID | Keputusan yang diperlukan | Dampak |
|---|---|---|
| L01 | Sumber dan agregasi M: nilai terakhir, terbaik, rata-rata, atau metode lain | Rekap Mentor dan N belum dapat diprogram final |
| L02 | Jumlah/bobot soal, agregasi D, jawaban sebagian, dan ujian ulang | Paket soal dan nilai ujian |
| L03 | Tindak lanjut setelah lima penilaian tema | Alur lanjutan tanpa asumsi kesempatan keenam |
| L04 | Detail diam, bantuan, koreksi setelah isyarat, arti `langsung`, dan kejadian berulang | Konsistensi pencatatan Mentor/Dosen |
| L05 | Skor desimal, pembulatan, penutupan periode, dan peserta terlambat selesai | Validasi dan penerbitan nilai |
| L06 | Mandat koreksi/tenggat/keberatan serta akses dan retensi media | Hak admin, privasi, dan pengesahan perubahan |
| L07 | Ukuran pilot, perangkat/browser, kapasitas, dukungan, RPO/RTO, performa, dan indikator stabil | Uji lapangan dan gate rilis |
| L08 | Teknologi, hosting, komposisi, dan kapasitas tim | Arsitektur implementasi dan jadwal |

Setiap keputusan ditutup dengan isi keputusan, contoh kasus, pihak pengesah, tanggal, versi efektif, dan daftar kebutuhan/API/tes yang terdampak.

## 27. Kriteria Selesai Produk MVP

MVP dapat dinyatakan selesai untuk pilot apabila:

1. Seluruh fungsi P0 yang disetujui tersedia dari layar hingga penyimpanan dan pembacaan ulang.
2. Implementasi tidak bergantung pada data simulasi atau kontrol pergantian peran prototipe.
3. API memeriksa izin, prasyarat, validasi, versi, dan idempotensi.
4. Semua keputusan yang diperlukan oleh lingkup rilis telah disahkan dan berversi.
5. Migrasi, backup, restore, monitoring, audit, dan rollback telah diuji.
6. Semua kasus penerimaan wajib lulus; tidak ada isu S1/S2 terbuka.
7. UAT lima peran diterima secara tertulis.
8. Panduan lima peran dan runbook operasi tersedia.
9. Pengelola dapat mereset akun dan memulihkan layanan melalui prosedur yang telah diuji.
10. Pengelola mencatat keputusan Go/Tunda untuk pilot.

## 28. Glosarium

| Istilah | Definisi |
|---|---|
| Tema | Unit hafalan berdasarkan kandungan; dapat terdiri atas beberapa rentang ayat/surah. |
| Bagian | Kelompok surah dalam lima pembagian Juz 30. |
| Ziyadah | Penambahan hafalan baru. |
| Murajaah | Pengulangan untuk menjaga dan memperkuat hafalan. |
| Setoran sinkron | Peserta dan Mentor berinteraksi pada waktu yang sama. |
| Setoran asinkron | Rekaman dikirim dan dinilai pada waktu yang berbeda. |
| Koreksi mandiri | Peserta membetulkan bacaan sendiri menurut batas aturan yang disahkan. |
| Isyarat/kode | Penanda bahwa bacaan salah tanpa memberikan lafaz jawaban. |
| Bantuan jawaban | Mentor memberi isi bacaan yang diperlukan agar peserta dapat melanjutkan. |
| Kejadian | Peristiwa yang dicatat dalam penilaian dan belum tentu dihitung sebagai kesalahan. |
| Rubrik | Aturan penilaian, kategori, pengecualian, dan keputusan hasil. |
| PWA-ready | Web disiapkan untuk dikembangkan menjadi Progressive Web App; bukan janji offline penuh. |
| K | Nilai keaktifan berdasarkan ketepatan waktu 44 tema. |
| M | Komponen nilai Mentor; cara agregasi menunggu L01. |
| D | Komponen nilai Dosen; cara agregasi menunggu L02. |
| N | Nilai akhir: 0,2K + 0,4M + 0,4D. |

## 29. Keterlacakan Sumber

PRD ini disusun dari rancangan aplikasi yang memuat hasil analisis kebutuhan, workflow dan rubrik, ERD/DFD, lingkup MVP, arsitektur teknis, rancangan halaman/prototipe, serta rencana implementasi dan pengujian. Kode kebutuhan F01-F36, layar G/P/M/D/J/F, keputusan K01-K15, dan keputusan terbuka L01-L08 dipertahankan atau dipetakan agar pengembangan dan pengujian dapat ditelusuri kembali ke rancangan tersebut.

