# UI Design Specification - YAQin

## Aplikasi Pendampingan Hafalan Juz 30

| Atribut | Nilai |
|---|---|
| Produk | YAQin - Yakin, Amalin, Mutqin |
| Dokumen | Spesifikasi desain antarmuka web |
| Versi | 1.0 |
| Tanggal | 20 Oktober 2026 |
| Status | Baseline implementasi untuk ditinjau |
| Sumber utama | `Rancangan Aplikasi Tahfidz v 01.pdf`, bagian Prototipe |
| Target UI | Next.js responsif dalam container Docker |
| Dokumen terkait | `docs/PRD-Aplikasi-Tahfidz-YAQin.md`, `docs/database.md`, `docs/Arsitektur.md` |

> Dokumen ini menerjemahkan prototipe YAQin menjadi pedoman UI yang dapat diimplementasikan. Struktur layar, alur, status, dan batas akademik mengikuti rancangan sumber. Nilai token visual merupakan aproksimasi dari prototipe dan perlu divalidasi kembali pada tahap visual QA.

---

## 1. Tujuan Desain

Antarmuka YAQin harus membantu setiap pengguna menjawab tiga pertanyaan tanpa menebak:

1. Apa posisi saya dalam proses saat ini?
2. Apa pekerjaan berikutnya yang sah untuk dilakukan?
3. Mengapa sebuah tindakan tersedia, terkunci, gagal, atau membutuhkan tindak lanjut?

Desain harus:

- Menjaga alur peserta, Mentor, Dosen, Admin Jurusan, dan Admin Fakultas tetap terpisah berdasarkan kewenangan.
- Memisahkan kelayakan teknis video dari penilaian hafalan.
- Memisahkan status kelulusan tema, kelayakan ujian, dan nilai akhir.
- Menampilkan nilai yang belum tersedia sebagai **Belum dinilai**, bukan `0`, tanda kosong, atau nilai buatan.
- Menempatkan tindakan utama dekat dengan data yang dipengaruhi.
- Mendukung penggunaan desktop, tablet, ponsel, keyboard, dan pembaca layar.
- Menjaga isian pengguna ketika validasi gagal, koneksi terputus, atau pengguna kembali dari dialog konfirmasi.

## 2. Prinsip Pengalaman Pengguna

### 2.1 Jelas sebelum ringkas

Istilah akademik, status, prasyarat, dan akibat finalisasi harus ditulis eksplisit. Ikon tidak boleh menjadi satu-satunya pembawa makna.

### 2.2 Satu layar, satu keputusan utama

Setiap layar memiliki satu tindakan utama, misalnya **Ajukan sesi**, **Tinjau kelayakan**, **Finalisasi penilaian**, atau **Tinjau perubahan kalender**. Tindakan sekunder tidak boleh bersaing secara visual.

### 2.3 Draft dan final adalah keadaan berbeda

Draft dapat diubah dan belum memengaruhi hasil akademik. Finalisasi memerlukan tinjauan, konfirmasi, dan bukti yang diwajibkan. UI harus selalu memperlihatkan status tersebut.

### 2.4 Tidak ada keputusan akademik terselubung

UI tidak boleh:

- Menganggap video yang layak secara teknis otomatis lulus secara akademik.
- Mengubah jumlah kesalahan langsung menjadi skor manual.
- Menganggap status Cukup otomatis berarti skor 8 atau lebih.
- Mengisi komponen K, M, D, atau nilai akhir yang belum dinilai.
- Menyediakan tombol bebas untuk menetapkan kelulusan di luar aturan dan mandat.

### 2.5 Aman saat gagal

Klik ganda, timeout, retry, konflik versi, dan koneksi terputus tidak boleh menghasilkan finalisasi ganda. UI menunggu hasil pemeriksaan status sebelum menawarkan retry.

## 3. Karakter Visual

Bahasa visual prototipe bersifat tenang, akademik, dan ringan:

- Hijau tua digunakan untuk header, navigasi utama, teks judul, dan tombol utama.
- Putih digunakan sebagai permukaan kerja.
- Hijau-keabu sangat muda digunakan sebagai kanvas dan navigasi terpilih.
- Kuning hangat digunakan untuk informasi yang perlu diperhatikan.
- Merah digunakan hanya untuk kesalahan, penolakan, dan tindakan berisiko.
- Bayangan dibuat sangat halus; pemisahan utama memakai border dan ruang kosong.

Logo teks **YAQin** ditampilkan pada kiri atas. Tagline **Yakin, Amalin, Mutqin** dapat muncul pada halaman masuk dan materi identitas, tetapi tidak perlu diulang pada setiap panel kerja.

## 4. Design Tokens

Token berikut adalah baseline implementasi. Nama token harus dipakai di CSS/Tailwind agar warna tidak ditulis berulang sebagai nilai literal.

### 4.1 Warna

| Token | Nilai awal | Penggunaan |
|---|---:|---|
| `brand-950` | `#0D3B31` | Header aplikasi, navigasi gelap |
| `brand-900` | `#124A3D` | Tombol utama, judul kuat |
| `brand-700` | `#1D6A54` | Link, focus ring pendamping |
| `brand-100` | `#DCEDE3` | Item navigasi aktif, badge positif |
| `brand-50` | `#EEF6F0` | Panel informasi ringan |
| `canvas` | `#F4F6F1` | Latar halaman |
| `surface` | `#FFFFFF` | Card, dialog, tabel |
| `border` | `#D8E1D9` | Border card dan input |
| `text-primary` | `#173A31` | Judul dan isi utama |
| `text-secondary` | `#5F6E68` | Metadata dan bantuan |
| `warning-100` | `#FFF3D6` | Banner perhatian |
| `warning-800` | `#765610` | Teks perhatian |
| `danger-100` | `#FCE8E6` | Latar kesalahan |
| `danger-700` | `#A33A33` | Error, penolakan, destructive action |
| `info-100` | `#E7F0F7` | Informasi netral |
| `info-700` | `#315F7A` | Teks informasi netral |

Aturan penggunaan:

- Rasio kontras teks normal minimal 4.5:1 dan teks besar minimal 3:1.
- Status tidak boleh dibedakan hanya dengan warna; sertakan label dan bila perlu ikon.
- Gunakan warna perhatian secara hemat agar peringatan akademik tetap menonjol.

### 4.2 Tipografi

Gunakan font sistem agar cepat dan konsisten:

```css
font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
  "Segoe UI", sans-serif;
```

| Gaya | Ukuran / line-height | Bobot | Penggunaan |
|---|---|---:|---|
| Display | 30 / 38 px | 700 | Judul beranda peran |
| Heading 1 | 26 / 34 px | 700 | Judul halaman |
| Heading 2 | 20 / 28 px | 700 | Judul bagian dan card |
| Heading 3 | 16 / 24 px | 600 | Subbagian |
| Body | 16 / 24 px | 400 | Isi dan input |
| Body small | 14 / 20 px | 400 | Bantuan dan metadata |
| Label | 14 / 20 px | 600 | Label field dan tabel |
| Caption | 12 / 18 px | 400 | Waktu, ID, catatan ringkas |

Label field selalu terlihat. Placeholder hanya memberi contoh format dan tidak menggantikan label.

### 4.3 Spacing, ukuran, radius, dan elevasi

- Grid dasar: 4 px.
- Spacing utama: 4, 8, 12, 16, 24, 32, 48, 64 px.
- Tinggi minimum target interaksi: 44 px.
- Radius input dan tombol: 6 px.
- Radius card dan dialog: 8 px.
- Border: 1 px solid `border`.
- Bayangan card: `0 1px 2px rgb(13 59 49 / 0.06)`.
- Bayangan dialog: `0 16px 40px rgb(13 59 49 / 0.18)`.
- Focus ring: 3 px `brand-700` dengan offset 2 px.

## 5. Struktur Aplikasi

### 5.1 App shell desktop

Untuk viewport 1024 px ke atas:

1. Header setinggi 64 px, sticky di atas.
2. Sidebar peran selebar 240 px, sticky di bawah header.
3. Area konten memiliki lebar maksimum 1200 px dan padding 32 px.
4. Isi halaman dibagi menjadi:
   - Area kerja: 2/3 lebar.
   - Informasi pendamping: 1/3 lebar, ideal 280-360 px.
5. Breadcrumb muncul di atas judul halaman.
6. Status konteks diletakkan sejajar judul pada layar lebar dan di bawah judul pada layar kecil.

```text
+------------------------------------------------------------------+
| YAQin                         Konteks peran              Akun      |
+---------------+--------------------------------------------------+
| Navigasi      | Breadcrumb                         Status badge   |
| peran         | Judul halaman                                     |
|               | Penjelasan singkat                                |
|               +-------------------------------+------------------+
|               | Area kerja                    | Informasi        |
|               |                               | pendamping      |
|               +-------------------------------+------------------+
+---------------+--------------------------------------------------+
```

Pemilih peran pada prototipe hanya untuk simulasi. Pada produk nyata, pergantian peran hanya muncul jika pengguna memang memiliki lebih dari satu peran aktif.

### 5.2 Tablet

Untuk viewport 768-1023 px:

- Sidebar dapat diperkecil menjadi rail atau drawer.
- Area kerja dan informasi pendamping tetap dua kolom bila masing-masing memiliki ruang yang cukup.
- Filter panjang dipindahkan ke drawer filter.
- Dialog maksimal selebar `min(640px, calc(100vw - 32px))`.

### 5.3 Ponsel

Untuk viewport di bawah 768 px:

- Navigasi peran menjadi tab horizontal yang dapat digulir atau menu drawer.
- Semua panel menjadi satu kolom.
- Informasi pendamping muncul setelah area kerja atau sebagai disclosure **Lihat panduan**.
- Tombol utama pada formulir panjang dapat memakai action bar sticky di bawah, dengan safe-area padding.
- Tabel tidak membuat seluruh halaman bergulir horizontal. Hanya container tabel yang boleh horizontal scroll.
- Data penting pada tabel dapat berubah menjadi list card berlabel.

## 6. Navigasi Berdasarkan Peran

Kode layar tetap ditampilkan dalam dokumentasi dan telemetry, tetapi label pengguna memakai bahasa tugas.

| Peran | Urutan navigasi utama |
|---|---|
| Peserta | P01 Beranda -> P02 Target dan kalender -> P03 Ajukan sesi -> P04 Kirim video -> P05 Hasil dan tindak lanjut -> P06 Ujian dan nilai |
| Mentor | M01 Binaan dan antrean -> M02 Catatan pembimbingan -> M03 Kelayakan video -> M04 Penilaian video -> M05 Rekap peserta |
| Dosen | D01 Antrean ujian -> D02 Paket soal -> D03 Pelaksanaan ujian -> D04 Rekap ujian |
| Admin Jurusan | J01 Peserta dan penugasan -> J02 Kalender angkatan -> J03 Laporan jurusan |
| Admin Fakultas | F01 Kebijakan dan laporan fakultas |
| Bersama | G01 Masuk dan pemulihan akun |

Setiap halaman menyediakan jalan kembali ke beranda peran. Navigasi aktif memakai latar `brand-100`, teks `brand-950`, dan indikator yang juga dapat dikenali tanpa warna.

### 6.1 Peta route yang disarankan

| Kode | Route Next.js |
|---|---|
| G01 | `/login`, `/forgot-password`, `/reset-password` |
| P01-P06 | `/peserta`, `/peserta/target`, `/peserta/sesi/baru`, `/peserta/video/baru`, `/peserta/hasil`, `/peserta/ujian` |
| M01-M05 | `/mentor/antrean`, `/mentor/sesi/[sessionId]`, `/mentor/video/[submissionId]/kelayakan`, `/mentor/video/[submissionId]/penilaian`, `/mentor/peserta/[participantId]` |
| D01-D04 | `/dosen/ujian`, `/dosen/ujian/[examId]/paket`, `/dosen/ujian/[examId]/pelaksanaan`, `/dosen/ujian/[examId]/rekap` |
| J01-J03 | `/jurusan/peserta`, `/jurusan/kalender`, `/jurusan/laporan` |
| F01 | `/fakultas/kebijakan` |

Route adalah rekomendasi implementasi dan dapat berubah tanpa mengubah kode layar pada dokumen kebutuhan.

## 7. Komponen UI Inti

### 7.1 Komponen shell

| Komponen | Tanggung jawab |
|---|---|
| `AppShell` | Header, sidebar/drawer, area konten, skip link |
| `BrandHeader` | Logo YAQin, konteks organisasi, akun |
| `RoleNavigation` | Navigasi sesuai peran dan kewenangan |
| `PageHeader` | Breadcrumb, judul, deskripsi, status konteks |
| `WorkSupportLayout` | Grid Area kerja dan Informasi pendamping |
| `SupportPanel` | Ringkasan konteks, langkah berikutnya, tautan bantuan |

### 7.2 Komponen data dan status

| Komponen | Perilaku |
|---|---|
| `StatusBadge` | Label teks dan ikon; varian netral, proses, sukses, peringatan, gagal, terkunci |
| `MetricCard` | Angka, label, rentang waktu, dan tautan drill-down |
| `DataTable` | Header jelas, sort berlabel, pagination, scroll lokal, caption aksesibel |
| `FilterBar` | Filter aktif terlihat dan dapat dihapus satu per satu |
| `ProgressSummary` | Progres tema dan bagian tanpa menyamakan progres dengan nilai |
| `Timeline` | Riwayat sesi, penilaian, koreksi, dan perubahan penugasan |
| `AuditTrail` | Aktor, waktu, perubahan, alasan, dan mandat |
| `WeightSummary` | Bobot K/M/D, nilai tersedia, dan alasan agregasi belum tersedia |

### 7.3 Komponen formulir

| Komponen | Perilaku |
|---|---|
| `FormField` | Label, nilai, bantuan, error inline, dan hubungan `aria-describedby` |
| `ScoreField` | Rentang 1-10 dan rubric 1-4, 5-7, 8-10 di dekat input |
| `DateTimeField` | Zona waktu Asia/Jakarta terlihat pada jadwal dan hasil |
| `ThemeSelector` | Hanya tema dalam bagian aktif yang dapat dipilih |
| `EvidenceField` | Status unggah/tautan, progres, retry, dan bukti yang diwajibkan |
| `IncidentEditor` | Kategori, ayat/waktu, koreksi mandiri, catatan |
| `EligibilityChecklist` | Pemeriksaan teknis video dan alasan jika Tidak Layak |
| `ReviewPanel` | Ringkasan seluruh isian sebelum finalisasi |
| `ConfirmationDialog` | Ringkasan akibat, tombol kembali, dan tindakan final yang eksplisit |
| `UnsavedChangesGuard` | Peringatan saat meninggalkan draft yang berubah |

### 7.4 Hirarki tindakan

- **Primary**: satu tindakan utama per panel, latar hijau tua.
- **Secondary**: aksi aman pendamping, permukaan putih dan border hijau.
- **Tertiary**: link atau tombol tanpa latar untuk navigasi lokal.
- **Danger**: koreksi/pembatalan berisiko, merah, selalu memerlukan konteks dan konfirmasi.
- **Disabled**: bukan pengganti penjelasan. Tampilkan alasan terkunci di dekat tombol.

Saat request berjalan, tombol dinonaktifkan, label berubah menjadi bentuk progres, dan hasil request diumumkan melalui live region.

## 8. Pola Status dan Bahasa

| Status | Makna UI | Contoh teks |
|---|---|---|
| Draft | Tersimpan, belum final | Draft penilaian |
| Menunggu | Perlu tindakan peran lain | Menunggu Mentor |
| Layak | Lulus pemeriksaan teknis | Layak dinilai |
| Tidak Layak | Gagal pemeriksaan teknis | Tidak Layak - audio tidak terdengar |
| Cukup | Hasil akademik tema/bagian memenuhi aturan | Cukup |
| Belum Cukup | Perlu tindak lanjut | Belum Cukup |
| Siap Ujian | Lima bagian Cukup dan belum ujian | Siap Ujian |
| Belum dinilai | Komponen nilai belum tersedia | Belum dinilai |
| Terkunci | Prasyarat atau kewenangan belum terpenuhi | Terkunci - selesaikan Bagian 2 |
| Final | Tidak dapat diedit melalui alur biasa | Final |

Pedoman microcopy:

- Gunakan kalimat tindakan: **Kirim video pengganti**, bukan **Perbaiki** tanpa objek.
- Jelaskan penyebab dan solusi: **Audio belum terunggah. Unggah bukti audio sebelum finalisasi.**
- Hindari pesan menyalahkan pengguna.
- Gunakan istilah yang sama di UI, API message mapping, bantuan, dan laporan.
- Tampilkan waktu absolut untuk keputusan akademik, misalnya **20 Okt 2026, 14.30 WIB**. Waktu relatif boleh menjadi informasi tambahan.

## 9. Keadaan Standar Setiap Halaman

Setiap layar wajib memiliki lima keadaan berikut:

| Keadaan | Isi minimum |
|---|---|
| Berisi | Data nyata, status, dan tindakan sesuai kewenangan |
| Kosong | Penjelasan mengapa kosong dan langkah yang relevan |
| Memuat | Skeleton yang menyerupai layout akhir, bukan spinner penuh halaman |
| Gagal | Pesan ringkas, detail aman, tombol **Coba lagi**, dan preservasi isian |
| Terkunci | Prasyarat yang belum terpenuhi, aktor yang harus bertindak, dan jalan kembali |

Tambahan untuk formulir:

- Validasi field muncul setelah blur atau submit, tidak saat pengguna baru mulai mengetik.
- Error summary muncul di atas formulir dan memindahkan fokus ke error pertama.
- Nilai valid tidak dihapus ketika field lain gagal.
- Konflik versi menawarkan **Muat versi terbaru** dan menjelaskan perubahan yang tidak dapat diterapkan.
- Timeout memicu pemeriksaan status server sebelum UI menawarkan kirim ulang.

## 10. Spesifikasi Layar

### 10.1 G01 - Masuk dan pemulihan akun

**Tujuan:** autentikasi pengguna dan pemulihan akses.

**Area kerja:** email/identitas akun, kata sandi, tampilkan/sembunyikan kata sandi, tombol masuk, tautan lupa kata sandi.

**Informasi pendamping:** dukungan akun, privasi, dan informasi bahwa peran ditentukan oleh penugasan aktif.

**Aturan:** pesan login tidak membocorkan apakah sebuah akun terdaftar. Setelah masuk, pengguna diarahkan ke beranda peran aktif.

### 10.2 P01 - Beranda peserta

**Tujuan:** memperlihatkan pekerjaan terdekat peserta.

**Area kerja:** target pekan, tema/bagian aktif, jadwal, status keterlambatan, progres, dan tabel **Target - Status - Berikutnya**.

**Tindakan utama:** membuka tugas paling relevan. Jika belum ada jadwal, tampilkan **Ajukan sesi**.

**Informasi pendamping:** ringkasan aturan progres dan tanggal efektif.

**Navigasi berikutnya:** P02.

### 10.3 P02 - Target dan kalender

**Tujuan:** melihat 44 tema dalam 5 bagian beserta tenggat efektif.

**Area kerja:** ringkasan bagian, jumlah tema, status, tanggal awal, tenggat efektif, hasil, dan skor aktivitas jika tersedia.

**Tindakan utama:** memilih tema dari bagian aktif.

**Aturan:** bagian terkunci menampilkan alasan. Tanggal yang dipakai adalah tenggat efektif setelah perubahan yang sah.

**Navigasi berikutnya:** P03.

### 10.4 P03 - Ajukan sesi

**Tujuan:** meminta sesi pembimbingan untuk satu atau beberapa tema.

**Area kerja:** pilihan tema, metode tatap muka/video call, waktu usulan, dan catatan.

**Tindakan utama:** **Tinjau pengajuan sesi**, lalu konfirmasi.

**Aturan:** minimal satu tema dan seluruh tema harus berasal dari bagian aktif yang sama.

**Navigasi berikutnya:** P01.

### 10.5 P04 - Kirim video bagian

**Tujuan:** mengirim rekaman video setelah syarat bagian terpenuhi.

**Area kerja:** bagian, siklus/revisi, tautan YouTube, tanggal rekaman, dan deklarasi kelengkapan.

**Tindakan utama:** **Tinjau kiriman video**.

**Aturan:** aktif hanya setelah semua tema pada bagian berstatus Cukup. Penggantian karena masalah teknis mempertahankan slot revisi akademik.

**Navigasi berikutnya:** P05.

### 10.6 P05 - Hasil dan tindak lanjut

**Tujuan:** melihat hasil tema dan video beserta tindakan yang diperlukan.

**Area kerja:** hasil tema, status kelayakan video, hasil akademik, alasan penolakan teknis, catatan kesalahan, dan audio Mentor.

**Tindakan utama:** kontekstual, misalnya **Kirim video pengganti** atau **Ajukan sesi revisi**.

**Aturan:** alasan teknis dan akademik harus dibedakan secara visual dan bahasa.

**Navigasi berikutnya:** P06.

### 10.7 P06 - Ujian dan nilai

**Tujuan:** menjelaskan kesiapan ujian dan komponen nilai.

**Area kerja:** status lima bagian, jadwal ujian, komponen K/M/D, bobot 20/40/40, dan nilai akhir bila semua komponen sah.

**Aturan:** lima bagian Cukup dan belum mengikuti ujian ditampilkan sebagai **Siap Ujian**. Komponen kosong ditampilkan **Belum dinilai**. UI tidak memutuskan agregasi yang belum disahkan.

**Navigasi berikutnya:** P02.

### 10.8 M01 - Binaan dan antrean

**Tujuan:** memprioritaskan pekerjaan Mentor.

**Area kerja:** peserta binaan, sesi hari ini, video menunggu, dan tindak lanjut.

**Tindakan utama:** membuka pekerjaan terpilih.

**Aturan:** filter berdasarkan jenis pekerjaan dan status, tanpa membuka peserta di luar penugasan aktif.

**Navigasi berikutnya:** M02.

### 10.9 M02 - Catatan pembimbingan

**Tujuan:** menilai beberapa tema dalam satu sesi.

**Area kerja:** tanggal sesi, tema, kesempatan, kejadian, catatan Mentor, skor manual, dan hasil per tema.

**Tindakan utama:** **Tinjau hasil tema**. Sediakan **Simpan draft** sebagai tindakan sekunder.

**Aturan:** penilaian kelima yang masih Belum Cukup masuk tindak lanjut. Finalisasi merangkum seluruh tema dan akibatnya.

**Navigasi berikutnya:** M05.

### 10.10 M03 - Kelayakan video

**Tujuan:** memeriksa kelayakan teknis sebelum penilaian akademik.

**Area kerja:** tautan rekaman, checklist teknis, hasil Layak/Tidak Layak, dan alasan.

**Tindakan utama:** **Tinjau keputusan kelayakan**.

**Aturan:** Tidak Layak mewajibkan alasan. Hanya Layak membuka M04. Keputusan ini tidak memberi skor akademik.

**Navigasi berikutnya:** M04.

### 10.11 M04 - Penilaian video

**Tujuan:** mencatat penilaian akademik video yang layak.

**Area kerja:** kategori kejadian, ayat/waktu, koreksi mandiri, skor manual, audio Mentor, dan catatan.

**Tindakan utama:** **Tinjau penilaian video**.

**Aturan:** jumlah kesalahan menentukan status sesuai kebijakan, bukan skor manual. Audio wajib sebelum finalisasi.

**Navigasi berikutnya:** M05.

### 10.12 M05 - Rekap peserta

**Tujuan:** meninjau riwayat dan komponen Mentor untuk satu peserta.

**Area kerja:** riwayat tema/bagian, status, skor, ketepatan waktu, penilaian efektif, dan tindak lanjut.

**Tindakan utama:** kembali ke antrean atau membuka item tindak lanjut.

**Aturan:** agregasi M dinonaktifkan sampai kebijakannya disahkan. Jelaskan alasan nilai belum tersedia.

**Navigasi berikutnya:** M01.

### 10.13 D01 - Antrean ujian

**Tujuan:** menemukan peserta yang berhak mengikuti ujian.

**Area kerja:** peserta dengan lima bagian Cukup, jadwal, dan riwayat ujian.

**Tindakan utama:** **Buka paket ujian**.

**Aturan:** ujian hanya dapat dimulai untuk peserta yang memenuhi prasyarat dan berada dalam lingkup Dosen.

**Navigasi berikutnya:** D02.

### 10.14 D02 - Paket soal

**Tujuan:** menyiapkan paket ujian.

**Area kerja:** sumber soal aplikasi/Dosen, jenis soal, cakupan ayat/tema, stimulus, dan acuan jawaban.

**Tindakan utama:** **Tinjau paket soal**. Sediakan **Simpan draft**.

**Aturan:** jumlah soal dan bobot mengikuti versi kebijakan yang berlaku. Jika belum disahkan, tandai sebagai keputusan terbuka dan blokir finalisasi yang bergantung padanya.

**Navigasi berikutnya:** D03.

### 10.15 D03 - Pelaksanaan ujian

**Tujuan:** mencatat pelaksanaan dan hasil ujian.

**Area kerja:** paket soal, catatan bantuan/kesalahan, skor manual, tanggal, dan penguji.

**Tindakan utama:** **Tinjau hasil ujian**. Sediakan **Simpan draft**.

**Aturan:** finalisasi mewajibkan bukti pelaksanaan dan skor valid. Draft dapat ditinjau sebelum final.

**Navigasi berikutnya:** D04.

### 10.16 D04 - Rekap ujian

**Tujuan:** meninjau jawaban, skor, hasil ujian, dan nilai gabungan.

**Area kerja:** daftar jawaban/komponen, status penilaian, skor, dan hasil agregasi bila lengkap.

**Aturan:** tidak ada ambang Dosen tersendiri kecuali kebijakan menetapkannya. Nilai kosong tidak pernah diisi otomatis.

**Navigasi berikutnya:** D01.

### 10.17 J01 - Peserta dan penugasan

**Tujuan:** mengelola peserta serta penugasan Mentor dan Dosen.

**Area kerja:** akun, NIM, jurusan, angkatan, Mentor, Dosen, dan masa berlaku.

**Tindakan utama:** **Tinjau penugasan**.

**Aturan:** validasi duplikasi dan konflik masa berlaku. Perubahan petugas mempertahankan riwayat.

**Navigasi berikutnya:** J03.

### 10.18 J02 - Kalender angkatan

**Tujuan:** mengelola kalender 52 pekan dan 44 target.

**Area kerja:** tanggal awal/akhir, tenggat, jadwal video/ujian, hari libur, alasan perubahan, dan dampak.

**Tindakan utama:** **Tinjau perubahan kalender**.

**Aturan:** tampilkan tanggal lama dan baru, alasan, pihak penyetuju, serta audit. Perubahan tenggat tidak boleh diam-diam mengubah riwayat.

**Navigasi berikutnya:** J03.

### 10.19 J03 - Laporan jurusan

**Tujuan:** melihat kondisi operasional angkatan.

**Area kerja:** progres, keterlambatan, antrean video/ujian, dan nilai belum lengkap.

**Tindakan utama:** filter angkatan, buka detail yang berwenang, atau ekspor sesuai mandat.

**Aturan:** laporan tidak otomatis memberi akses ke seluruh media atau data pribadi. Ekspor menampilkan ruang lingkup dan waktu pembuatan.

**Navigasi berikutnya:** J02.

### 10.20 F01 - Kebijakan dan laporan fakultas

**Tujuan:** melihat versi kebijakan, status persetujuan, laporan agregat, dan audit.

**Area kerja:** versi rubric, bobot, ambang, status persetujuan, periode berlaku, dan ringkasan agregat.

**Tindakan utama:** melihat ringkasan kebijakan atau mengajukan persetujuan sesuai mandat.

**Aturan:** versi baru tidak menimpa penilaian lama. UI selalu memperlihatkan versi kebijakan yang dipakai oleh sebuah hasil.

## 11. Pola Penilaian dan Finalisasi

### 11.1 Skor manual

Skor menggunakan bilangan bulat dalam rentang 1-10, tanpa angka pecahan, dan memperlihatkan rubric di titik penilaian:

- 1-4: perlu perbaikan mendasar.
- 5-7: cukup dengan catatan.
- 8-10: baik sampai sangat baik.

Deskripsi final rubric harus berasal dari versi kebijakan yang disahkan. UI tidak menghitung skor dari jumlah insiden.

### 11.2 Hasil video

Alur visual harus berurutan:

```text
Video dikirim -> Pemeriksaan teknis -> Layak -> Penilaian akademik
                                  \-> Tidak Layak -> Video pengganti
```

Jika aturan aktif menggunakan jumlah kesalahan, tampilkan ringkasannya secara terpisah dari skor manual. Contoh rancangan menyebut 0-3 kesalahan sebagai Cukup dan 4 atau lebih sebagai Belum Cukup; implementasi harus membaca nilai dari policy version, bukan hard-code di komponen.

### 11.3 Nilai akhir

UI memperlihatkan bobot rancangan K/M/D = 20/40/40 dan ambang 6 hanya sebagai kebijakan berversi. Agregasi M, agregasi D, pembulatan, ujian ulang, dan koreksi tetap ditandai sebagai keputusan terbuka sampai disahkan.

Jika komponen belum lengkap:

- Tampilkan **Belum dinilai** pada komponen terkait.
- Jangan tampilkan `0`.
- Jangan tampilkan nilai akhir sementara seolah final.
- Tampilkan komponen atau keputusan yang masih dibutuhkan.

## 12. Dialog Tinjau dan Konfirmasi

Semua finalisasi akademik memakai dua tahap:

1. **Tinjau**: tampilkan ringkasan input, bukti, status yang akan dihasilkan, dan policy version.
2. **Konfirmasi**: jelaskan bahwa data akan menjadi final dan perubahan berikutnya memerlukan alur koreksi/audit.

Dialog harus memiliki:

- Judul yang menyebut objek, misalnya **Finalisasi penilaian Tema 12**.
- Ringkasan bukan hanya pertanyaan ya/tidak.
- Tombol **Kembali dan periksa** yang mempertahankan seluruh isian.
- Tombol final yang spesifik, misalnya **Finalisasi penilaian**.
- Fokus awal pada judul dialog dan focus trap yang benar.
- Pencegahan klik ganda dan indikator proses.

## 13. Tabel, Filter, dan Ekspor

- Setiap tabel memiliki judul/caption dan header yang eksplisit.
- Kolom status tidak hanya memakai badge warna.
- Filter aktif selalu terlihat di atas hasil.
- Hasil filter mempertahankan query di URL agar dapat dibagikan dalam lingkup yang berwenang.
- Pada ponsel, prioritaskan kolom identitas, status, dan tindakan; detail lain masuk disclosure.
- Ekspor harus menampilkan rentang data, filter, klasifikasi, dan konfirmasi kewenangan.
- Laporan agregat tidak boleh menjadi pintasan untuk membuka media privat.

## 14. Aksesibilitas

Target minimum adalah WCAG 2.2 tingkat AA.

- Sediakan **Lewati ke konten utama** sebagai elemen fokus pertama.
- Semua fungsi dapat dijalankan dengan keyboard.
- Urutan fokus mengikuti urutan visual dan tidak berpindah tanpa tindakan pengguna.
- Target klik minimum 44 x 44 px.
- Input memiliki label programatik, bantuan, dan error terkait.
- Perubahan status async diumumkan lewat `aria-live="polite"`; kegagalan kritis memakai pengumuman tegas.
- Dialog memiliki nama aksesibel, focus trap, dan mengembalikan fokus ke pemicu ketika ditutup.
- Ikon dekoratif memakai `aria-hidden="true"`.
- Grafik laporan selalu memiliki ringkasan teks atau tabel ekuivalen.
- Animasi menghormati `prefers-reduced-motion`.
- Uji pada zoom 200 persen tanpa kehilangan konten atau fungsi.

## 15. Respons Sistem dan Ketahanan Koneksi

### 15.1 Loading

- Gunakan skeleton pada card, tabel, dan detail.
- Pertahankan header dan navigasi agar posisi pengguna tidak hilang.
- Untuk operasi lebih dari beberapa detik, tampilkan label proses yang jelas.

### 15.2 Error dan retry

- Error inline untuk field; error panel untuk kegagalan halaman.
- Tombol **Coba lagi** hanya muncul setelah request sebelumnya selesai atau statusnya diketahui.
- Jangan tampilkan stack trace, ID internal sensitif, atau isi media pada pesan error.
- Sertakan correlation ID yang aman untuk dukungan bila tersedia.

### 15.3 Konflik dan perubahan bersamaan

Jika data berubah sejak halaman dibuka:

1. Hentikan finalisasi.
2. Jelaskan bahwa data telah diperbarui oleh pengguna lain.
3. Tawarkan **Muat versi terbaru**.
4. Jangan menimpa data terbaru secara otomatis.

### 15.4 Koneksi terputus

- Simpan draft lokal hanya untuk data non-sensitif dan sesuai kebijakan keamanan.
- Finalisasi akademik tidak dilakukan secara offline.
- Setelah koneksi kembali, periksa status operasi sebelum mengirim ulang.

## 16. Implementasi di Next.js

Struktur komponen yang disarankan:

```text
src/
  app/
    (auth)/
    (peserta)/
    (mentor)/
    (dosen)/
    (jurusan)/
    (fakultas)/
  components/
    shell/
    navigation/
    forms/
    data-display/
    feedback/
    assessment/
  styles/
    tokens.css
```

Pedoman implementasi:

- Gunakan Server Components untuk shell dan pembacaan data yang tidak interaktif.
- Gunakan Client Components hanya untuk form, filter interaktif, dialog, dan kontrol media.
- Semua status domain dipetakan melalui satu presentation mapper agar istilah konsisten.
- Jangan menyalin aturan akademik ke frontend. FastAPI mengirim status, prasyarat, policy version, dan allowed actions.
- Tombol dirender dari `allowed_actions`, tetapi backend tetap melakukan otorisasi ulang.
- Query filter dan pagination disimpan pada search params.
- Gunakan error boundary per area kerja agar navigasi tetap tersedia ketika sebuah panel gagal.

## 17. Analitik dan Telemetry UI

Catat kejadian tanpa menyimpan isi hafalan, tautan privat, audio, atau catatan sensitif:

- `page_viewed` dengan screen code.
- `primary_action_started` dan `primary_action_completed`.
- `validation_failed` dengan nama field generik.
- `finalization_started`, `finalization_succeeded`, `finalization_failed`.
- `locked_state_viewed` dengan kode alasan.
- `retry_requested` dan `version_conflict_detected`.

Metrik UX utama:

- Waktu menemukan target pekan.
- Waktu menyelesaikan penilaian video.
- Persentase finalisasi gagal karena bukti belum lengkap.
- Persentase pengguna yang memahami perbedaan Layak dan Cukup.
- Tingkat penyelesaian tugas utama pada ponsel dan keyboard.

## 18. Skenario Uji Desain

1. Peserta menemukan target pekan dan langkah berikutnya tanpa bantuan.
2. Peserta memahami alasan bagian atau video terkunci.
3. Mentor memisahkan keputusan kelayakan teknis dari penilaian akademik.
4. Mentor menyimpan draft, meninjau, lalu memfinalisasi tanpa kehilangan data.
5. Dosen hanya dapat memulai ujian untuk peserta yang memenuhi prasyarat.
6. Admin Jurusan mengubah tenggat dan dapat menjelaskan tanggal lama, baru, alasan, serta dampaknya.
7. Admin Fakultas dapat membedakan versi kebijakan aktif dari versi historis.
8. Pengguna memulihkan diri dari koneksi terputus tanpa finalisasi ganda.
9. Pengguna kembali dari dialog konfirmasi dan seluruh isian tetap ada.
10. Tugas utama selesai pada viewport ponsel dan hanya dengan keyboard.

## 19. Keputusan Desain yang Masih Terbuka

Hal berikut perlu keputusan pemilik produk/akademik sebelum UI final:

- Deskripsi resmi rubric skor 1-10.
- Cara agregasi nilai Mentor menjadi M.
- Jumlah, bobot, dan cara agregasi soal menjadi D.
- Dukungan nilai desimal dan aturan pembulatan.
- Alur ujian ulang, penilaian ulang, dan koreksi hasil final.
- Mandat persetujuan untuk perubahan tenggat dan kebijakan.
- Retensi draft lokal dan batas ukuran audio.
- Apakah peserta dapat melihat seluruh detail kejadian atau hanya ringkasannya.

Semua keputusan harus masuk policy version atau permission model. UI tidak boleh menyelesaikan keputusan terbuka dengan default tersembunyi.

## 20. Definition of Done UI

Sebuah layar dianggap siap implementasi ketika:

- Tujuan, data, tindakan utama, prasyarat, dan kewenangannya jelas.
- Keadaan berisi, kosong, memuat, gagal, dan terkunci tersedia.
- Draft, tinjau, finalisasi, dan koreksi dapat dibedakan.
- Desktop, tablet, ponsel, keyboard, dan zoom 200 persen telah diuji.
- Teks status konsisten dengan domain dan tidak mengisi nilai yang belum ada.
- Loading, timeout, retry, klik ganda, serta konflik versi ditangani.
- Tindakan sensitif memiliki konfirmasi dan menghasilkan audit.
- Tidak ada akses data atau media yang melampaui peran dan penugasan.
- Token visual, komponen, dan pola navigasi digunakan secara konsisten.
- Product owner dan pemilik kebijakan akademik menyetujui istilah serta keputusan terbuka yang relevan.

---

Dokumen ini menjadi baseline UI. Perubahan yang memengaruhi status akademik, kewenangan, agregasi nilai, atau akses media harus diselaraskan dengan PRD, rancangan database, arsitektur, dan versi kebijakan yang berlaku.
