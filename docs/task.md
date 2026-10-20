# Task Implementation Plan - YAQin

## Aplikasi Pendampingan Hafalan Juz 30

| Atribut | Nilai |
|---|---|
| Produk | YAQin - Yakin, Amalin, Mutqin |
| Dokumen | Todo list implementasi aplikasi |
| Versi | 1.0 |
| Tanggal | 20 Oktober 2026 |
| Status | Siap digunakan sebagai backlog awal |
| Backend | FastAPI |
| Frontend | Next.js |
| Database | PostgreSQL |
| Deployment | Docker Compose |
| Dokumen sumber | `PRD-Aplikasi-Tahfidz-YAQin.md`, `Arsitektur.md`, `database.md`, `API.md`, `ERD.md`, `design.md` |

> Checklist ini disusun dalam urutan dependency. Tugas berstatus P0 diperlukan untuk pilot, sedangkan P1 dapat dikerjakan setelah alur utama stabil.

---

## 1. Petunjuk Penggunaan

Status checkbox:

- `[ ]` Belum dikerjakan.
- `[x]` Selesai dan acceptance criteria terpenuhi.

Setiap task memiliki:

- **Prioritas**: P0 atau P1.
- **Blocked by**: task yang harus selesai lebih dahulu.
- **Hasil**: kemampuan end-to-end yang tersedia setelah task selesai.
- **Acceptance criteria**: syarat verifikasi sebelum task ditutup.

Task tidak dianggap selesai hanya karena schema, endpoint, atau halaman telah dibuat. Seluruh lapisan yang diperlukan, termasuk validasi, otorisasi, audit, dan pengujian, harus bekerja bersama.

## 2. Keputusan yang Harus Disahkan

Keputusan berikut boleh dikerjakan paralel dengan fondasi teknis, tetapi harus ditutup sebelum fitur terkait difinalkan.

### DEC-001 - Sahkan rubric skor dan dukungan desimal

**Prioritas:** P0  
**Blocked by:** Tidak ada

- [ ] Sahkan deskripsi rubric skor 1-4, 5-7, dan 8-10.
- [ ] Putuskan apakah skor pecahan diizinkan.
- [ ] Tentukan validasi serta cara menampilkan skor.
- [ ] Dokumentasikan keputusan sebagai policy version awal.

### DEC-002 - Sahkan agregasi nilai Mentor dan Dosen

**Prioritas:** P0  
**Blocked by:** DEC-001

- [ ] Tentukan sumber penilaian yang membentuk M.
- [ ] Tentukan jumlah, bobot, dan agregasi soal yang membentuk D.
- [ ] Tentukan aturan pembulatan K, M, D, dan N.
- [ ] Verifikasi formula akhir `N = 0.2K + 0.4M + 0.4D` dan ambang kelulusan 6.
- [ ] Dokumentasikan keputusan sebagai policy version.

### DEC-003 - Sahkan koreksi, ujian ulang, dan retensi media

**Prioritas:** P0  
**Blocked by:** DEC-001

- [ ] Tentukan pihak yang boleh meminta, menyetujui, dan menerapkan koreksi.
- [ ] Tentukan alur ujian ulang dan penilaian ulang.
- [ ] Tentukan format, ukuran maksimum, dan retensi audio Mentor.
- [ ] Tentukan daftar host video eksternal yang diizinkan.
- [ ] Tentukan masa retensi audit, idempotency record, dan ekspor.

## 3. Fondasi Repository dan Infrastruktur

### TASK-001 - Bootstrap struktur repository aplikasi

**Prioritas:** P0  
**Blocked by:** Tidak ada  
**Hasil:** Repository memiliki aplikasi Next.js, FastAPI, konfigurasi bersama, dan struktur pengujian yang dapat dijalankan.

- [x] Buat struktur `apps/web` untuk Next.js App Router.
- [x] Buat struktur `apps/api` untuk FastAPI modular monolith.
- [x] Buat direktori deployment, migration, test, dan dokumentasi operasional.
- [x] Tambahkan `.env.example` tanpa secret nyata.
- [x] Tetapkan formatter, linter, type checker, dan test runner.
- [x] Tambahkan perintah development, test, build, dan migration.
- [x] Pastikan aplikasi kosong dapat dibangun secara lokal.

### TASK-002 - Siapkan Docker Compose development

**Prioritas:** P0  
**Blocked by:** TASK-001  
**Hasil:** Web, API, PostgreSQL, worker, object storage, dan reverse proxy dapat dijalankan dalam container.

- [x] Buat multi-stage Dockerfile untuk Next.js.
- [x] Buat image FastAPI berbasis Python slim dan user non-root.
- [x] Konfigurasikan PostgreSQL dengan volume persisten.
- [ ] Konfigurasikan object storage privat untuk development.
- [ ] Konfigurasikan worker terpisah.
- [ ] Konfigurasikan reverse proxy dengan routing satu origin.
- [x] Tambahkan health check dan dependency startup.
- [ ] Pastikan hanya gateway membuka port publik yang diperlukan.

> Status parsial 20 Oktober 2026: Compose development untuk web, API, dan PostgreSQL sudah sehat. Object storage, worker, reverse proxy, dan pembatasan port melalui gateway ditunda sesuai cakupan implementasi saat ini.

### TASK-003 - Bangun baseline CI

**Prioritas:** P0  
**Blocked by:** TASK-001  
**Hasil:** Setiap perubahan diperiksa otomatis sebelum dapat digabungkan.

- [x] Jalankan lint dan type check frontend.
- [x] Jalankan lint, type check, dan test backend.
- [x] Validasi migration dari database kosong.
- [x] Validasi OpenAPI dan generated TypeScript client.
- [x] Build image web dan API.
- [x] Tambahkan pemeriksaan secret dan dependency vulnerability dasar.

## 4. Fondasi Backend dan Database

### TASK-004 - Implementasikan konfigurasi, database, dan migration framework

**Prioritas:** P0  
**Blocked by:** TASK-001, TASK-002  
**Hasil:** FastAPI terhubung ke PostgreSQL dengan konfigurasi aman dan migration yang dapat direproduksi.

- [ ] Implementasikan settings tervalidasi dari environment.
- [ ] Implementasikan async database session dan connection pool.
- [ ] Siapkan schema `app`, `ops`, dan version table migration.
- [ ] Tambahkan UUID generation dan timezone handling.
- [ ] Tambahkan unit of work dan transaction boundary.
- [ ] Buat migration smoke test serta rollback test yang relevan.

### TASK-005 - Implementasikan model identitas dan organisasi

**Prioritas:** P0  
**Blocked by:** TASK-004  
**Hasil:** Fakultas, jurusan, akun, dan role grant dapat disimpan serta divalidasi.

- [ ] Buat tabel dan model `organizations`.
- [ ] Buat tabel dan model `users`.
- [ ] Buat tabel dan model `role_grants`.
- [ ] Terapkan unique constraint login identifier.
- [ ] Cegah siklus organisasi dan organisasi menjadi induk dirinya sendiri.
- [ ] Validasi role admin terhadap jenis organisasi.
- [ ] Tambahkan seed fakultas dan jurusan contoh.
- [ ] Tambahkan test constraint dan scope dasar.

### TASK-006 - Implementasikan policy dan kurikulum berversi

**Prioritas:** P0  
**Blocked by:** TASK-004, DEC-001  
**Hasil:** Policy version dan kurikulum lima bagian/44 tema tersedia sebagai data immutable setelah diterbitkan.

- [ ] Buat tabel `policy_versions` dan `curriculum_versions`.
- [ ] Buat tabel `parts`, `themes`, dan `theme_ranges`.
- [ ] Terapkan urutan lima bagian dan urutan tema/rentang.
- [ ] Validasi surah 78-114 dan rentang ayat.
- [ ] Validasi distribusi tema 10, 8, 6, 5, dan 15 saat publish.
- [ ] Cegah edit versi yang sudah published.
- [ ] Seed kurikulum Juz 30 dan policy version awal.
- [ ] Sediakan endpoint reference kurikulum, rubric, dan policy aktif.

### TASK-007 - Implementasikan cohort, enrollment, dan assignment

**Prioritas:** P0  
**Blocked by:** TASK-005, TASK-006  
**Hasil:** Admin dapat membuat angkatan, mendaftarkan peserta, dan memberi penugasan Mentor/Dosen dengan riwayat.

- [ ] Buat tabel `cohorts`, `enrollments`, dan `assignments`.
- [ ] Validasi organisasi cohort sebagai jurusan.
- [ ] Validasi duplikasi peserta dan NIM dalam cohort.
- [ ] Validasi role grant petugas sebelum assignment.
- [ ] Cegah interval assignment aktif yang tidak diperbolehkan saling tumpang tindih.
- [ ] Akhiri assignment lama tanpa menghapus riwayat.
- [ ] Buat API admin untuk enrollment dan assignment.
- [ ] Buat UI J01 Peserta dan penugasan.
- [ ] Tambahkan integration test otorisasi lintas jurusan.

## 5. Autentikasi, Session, dan App Shell

### TASK-008 - Implementasikan autentikasi dan pemulihan akun

**Prioritas:** P0  
**Blocked by:** TASK-005  
**Hasil:** Pengguna dapat masuk, keluar, memulihkan akun, dan memperoleh konteks peran aktif secara aman.

- [ ] Implementasikan password hashing dengan pustaka terpelihara.
- [ ] Implementasikan opaque server-side session.
- [ ] Terapkan cookie `Secure`, `HttpOnly`, dan `SameSite`.
- [ ] Implementasikan rotasi dan pencabutan session.
- [ ] Implementasikan proteksi CSRF untuk mutasi.
- [ ] Implementasikan token pemulihan sekali pakai dan berumur pendek.
- [ ] Terapkan rate limit login dan pemulihan.
- [ ] Buat endpoint `/auth/login`, `/auth/logout`, `/auth/session`, dan pemulihan.
- [ ] Buat UI G01 Masuk dan pemulihan akun.
- [ ] Pastikan pesan gagal tidak membocorkan keberadaan akun.

### TASK-009 - Implementasikan app shell dan design system

**Prioritas:** P0  
**Blocked by:** TASK-001, TASK-008  
**Hasil:** Pengguna memperoleh navigasi responsif sesuai role dengan komponen visual yang konsisten.

- [ ] Implementasikan design tokens dari `design.md`.
- [ ] Buat header, sidebar/drawer, breadcrumb, dan page header.
- [ ] Buat layout Area kerja dan Informasi pendamping.
- [ ] Buat komponen tombol, input, status badge, card, tabel, dialog, dan state feedback.
- [ ] Implementasikan navigasi Peserta, Mentor, Dosen, Admin Jurusan, dan Admin Fakultas.
- [ ] Tampilkan role switcher hanya untuk pengguna dengan beberapa role aktif.
- [ ] Tambahkan skip link, focus ring, keyboard navigation, dan live region.
- [ ] Verifikasi layout desktop, tablet, ponsel, dan zoom 200 persen.

### TASK-010 - Implementasikan kontrak API bersama

**Prioritas:** P0  
**Blocked by:** TASK-004, TASK-008  
**Hasil:** Seluruh endpoint memakai envelope, error model, pagination, request ID, dan client TypeScript yang konsisten.

- [ ] Implementasikan success dan error envelope.
- [ ] Implementasikan request ID dan structured logging.
- [ ] Implementasikan error code domain dan field errors.
- [ ] Implementasikan cursor pagination dan filter allowlist.
- [ ] Implementasikan `expected_version` untuk optimistic concurrency.
- [ ] Implementasikan penyimpanan `Idempotency-Key` pada schema operasi.
- [ ] Publikasikan OpenAPI di development/staging.
- [ ] Hasilkan client TypeScript pada CI.
- [ ] Pastikan respons sensitif memakai `Cache-Control: no-store`.

## 6. Target dan Kalender Peserta

### TASK-011 - Bangun target 44 tema dan kalender peserta

**Prioritas:** P0  
**Blocked by:** TASK-006, TASK-007, TASK-010  
**Hasil:** Peserta dapat melihat target, tenggat efektif, bagian aktif, dan pekerjaan berikutnya.

- [ ] Buat tabel dan model `targets`.
- [ ] Generate target dari cohort dan kurikulum secara idempotent.
- [ ] Validasi satu target per enrollment dan tema.
- [ ] Buat proyeksi progres peserta.
- [ ] Buat endpoint `/me/dashboard`, `/me/targets`, dan `/me/progress`.
- [ ] Buat UI P01 Beranda peserta.
- [ ] Buat UI P02 Target dan kalender.
- [ ] Tampilkan alasan bagian terkunci dan `allowed_actions` dari server.
- [ ] Tambahkan empty, loading, error, retry, dan locked state.

### TASK-012 - Bangun perubahan tenggat dengan approval dan audit

**Prioritas:** P0  
**Blocked by:** TASK-011  
**Hasil:** Admin Jurusan dapat mengusulkan dan mengesahkan perubahan tenggat tanpa menghapus tanggal lama.

- [ ] Buat tabel `deadline_changes`.
- [ ] Implementasikan pratinjau tanggal lama, baru, dan dampak target.
- [ ] Terapkan approval sesuai mandat.
- [ ] Perbarui `effective_due_date` dalam transaksi approval.
- [ ] Pertahankan `initial_due_date` dan seluruh riwayat perubahan.
- [ ] Buat endpoint pengajuan, approval, dan rejection.
- [ ] Buat UI J02 Kalender angkatan.
- [ ] Tambahkan concurrency, idempotency, dan audit test.

## 7. Sesi dan Penilaian Tema

### TASK-013 - Implementasikan pengajuan dan penjadwalan sesi

**Prioritas:** P0  
**Blocked by:** TASK-007, TASK-009, TASK-011  
**Hasil:** Peserta dapat mengajukan sesi dan Mentor dapat menjadwalkan serta memulai sesi.

- [ ] Buat tabel `sessions` dan `session_themes`.
- [ ] Validasi minimal satu tema dan satu bagian yang sama.
- [ ] Validasi bagian aktif serta assignment Mentor.
- [ ] Implementasikan state `proposed`, `scheduled`, `in_progress`, `completed`, `no_show`, dan `cancelled`.
- [ ] Buat endpoint pengajuan dan manajemen sesi.
- [ ] Buat UI P03 Ajukan sesi.
- [ ] Tampilkan sesi pada UI M01 Binaan dan antrean.
- [ ] Pastikan jadwal tidak dianggap tanggal setoran pertama.

### TASK-014 - Implementasikan penilaian tema end-to-end

**Prioritas:** P0  
**Blocked by:** TASK-013, TASK-010, DEC-001  
**Hasil:** Mentor dapat menyimpan draft, meninjau, dan memfinalisasi hasil setiap tema secara aman.

- [ ] Buat `assessment_records`, `theme_assessments`, dan `incidents`.
- [ ] Terapkan tepat satu subtype untuk assessment bertipe tema.
- [ ] Implementasikan draft dan review sebelum finalisasi.
- [ ] Validasi skor, insiden, bantuan, koreksi mandiri, outcome, dan policy version.
- [ ] Alokasikan `attempt_no` 1-5 dengan row lock peserta-tema.
- [ ] Ubah hasil kelima yang belum Cukup menjadi `follow_up`.
- [ ] Cegah pembuatan kesempatan keenam otomatis.
- [ ] Rekam tanggal aktual pertama yang sah untuk perhitungan K.
- [ ] Buat UI M02 Catatan pembimbingan.
- [ ] Buat hasil tema pada UI P05 dan rekap M05.
- [ ] Tambahkan idempotency, concurrency, authorization, dan domain test.

## 8. Video dan Audio Mentor

### TASK-015 - Implementasikan slot akademik dan versi video

**Prioritas:** P0  
**Blocked by:** TASK-014  
**Hasil:** Peserta dapat mengirim video bagian hanya setelah semua tema pada bagian tersebut Cukup.

- [ ] Buat tabel `video_attempts` dan `video_versions`.
- [ ] Alokasikan siklus mulai 1 dan revisi 0-3 di server.
- [ ] Validasi prasyarat seluruh tema bagian berstatus Cukup.
- [ ] Validasi URL HTTPS dan host allowlist.
- [ ] Hindari server-side fetch ke URL sembarang.
- [ ] Pastikan penggantian teknis menambah versi media, bukan revisi akademik.
- [ ] Buat endpoint pembuatan attempt dan pengiriman versi.
- [ ] Buat UI P04 Kirim video bagian.
- [ ] Tambahkan test alokasi siklus/revisi dan request bersamaan.

### TASK-016 - Implementasikan pemeriksaan kelayakan video

**Prioritas:** P0  
**Blocked by:** TASK-015  
**Hasil:** Mentor dapat menentukan kelayakan teknis video tanpa memberi hasil akademik.

- [ ] Buat tabel `eligibility_reviews` dan `eligibility_checks`.
- [ ] Implementasikan checklist berversi.
- [ ] Wajibkan alasan untuk hasil `ineligible`.
- [ ] Pastikan seluruh butir wajib lulus untuk hasil `eligible`.
- [ ] Implementasikan draft dan finalisasi idempotent.
- [ ] Buat UI M03 Kelayakan video.
- [ ] Tampilkan alasan teknis dan tindakan kirim pengganti pada P05.
- [ ] Pastikan hanya video eligible yang membuka penilaian akademik.

### TASK-017 - Implementasikan upload dan playback audio privat

**Prioritas:** P0  
**Blocked by:** TASK-002, TASK-010, DEC-003  
**Hasil:** Mentor dapat mengunggah audio privat dan pengguna berwenang dapat memutarnya melalui URL sementara.

- [ ] Buat tabel `media_assets`.
- [ ] Implementasikan upload intent dan signed upload URL.
- [ ] Validasi content type, ukuran, checksum, dan status media.
- [ ] Implementasikan worker validasi media.
- [ ] Implementasikan signed playback URL berumur pendek.
- [ ] Terapkan authorization per objek saat membuat playback URL.
- [ ] Pastikan signed URL tidak masuk log, analytics, atau database permanen.
- [ ] Tambahkan test media gagal, dikarantina, dan tidak berwenang.

### TASK-018 - Implementasikan penilaian akademik video

**Prioritas:** P0  
**Blocked by:** TASK-016, TASK-017, DEC-001  
**Hasil:** Mentor dapat menilai video eligible, memberi audio, dan menghasilkan status bagian secara konsisten.

- [ ] Buat tabel `video_assessments` sebagai subtype assessment.
- [ ] Validasi review final eligible dan video version yang sama.
- [ ] Hitung `counted_errors` dari incident di server.
- [ ] Terapkan hasil 0-3 `enough` dan 4+ `not_enough` dari policy version.
- [ ] Pastikan skor manual tidak mengubah outcome.
- [ ] Wajibkan audio `available` sebelum finalisasi.
- [ ] Buka revisi/siklus berikut sesuai aturan server.
- [ ] Buat UI M04 Penilaian video.
- [ ] Perbarui UI P05 dan M05 dengan hasil serta audio.
- [ ] Tambahkan finalization transaction, idempotency, dan concurrency test.

## 9. Ujian Dosen

### TASK-019 - Implementasikan antrean ujian dan paket soal

**Prioritas:** P0  
**Blocked by:** TASK-018, TASK-006  
**Hasil:** Dosen melihat peserta yang memenuhi syarat dan dapat menyiapkan paket soal berversi.

- [ ] Buat tabel `question_versions`, `exams`, dan `exam_items`.
- [ ] Buat proyeksi eligibility lima bagian Cukup.
- [ ] Validasi assignment Dosen aktif.
- [ ] Implementasikan sumber soal aplikasi dan Dosen.
- [ ] Simpan snapshot soal serta acuan jawaban pada exam item.
- [ ] Batasi acuan jawaban hanya untuk penguji berwenang.
- [ ] Buat endpoint antrean, draft ujian, dan paket soal.
- [ ] Buat UI D01 Antrean ujian.
- [ ] Buat UI D02 Paket soal.
- [ ] Blokir finalisasi bila jumlah/bobot soal belum disahkan.

### TASK-020 - Implementasikan pelaksanaan dan finalisasi ujian

**Prioritas:** P0  
**Blocked by:** TASK-019, DEC-002  
**Hasil:** Dosen dapat mencatat, meninjau, dan memfinalisasi ujian dengan bukti serta skor yang sah.

- [ ] Buat `exam_assessments` sebagai subtype assessment.
- [ ] Implementasikan draft penilaian per exam item.
- [ ] Validasi skor 1-10, bukti pelaksanaan, paket, dan policy version.
- [ ] Implementasikan finalisasi ujian dalam satu transaksi.
- [ ] Hitung D hanya jika metode agregasi telah disahkan.
- [ ] Buat UI D03 Pelaksanaan ujian.
- [ ] Buat UI D04 Rekap ujian.
- [ ] Perbarui kesiapan ujian dan rekap peserta.
- [ ] Tambahkan idempotency, concurrency, dan authorization test.

## 10. Nilai dan Kelulusan

### TASK-021 - Implementasikan perhitungan keaktifan K

**Prioritas:** P0  
**Blocked by:** TASK-012, TASK-014  
**Hasil:** Sistem menghitung skor keaktifan dari tanggal setoran pertama dan tenggat efektif secara dapat diaudit.

- [ ] Terapkan bucket keterlambatan hari 0, 1-7, 8-14, hingga lebih dari 49.
- [ ] Gunakan zona waktu Asia/Jakarta.
- [ ] Pastikan pengulangan tidak mengganti tanggal setoran pertama.
- [ ] Jangan memberi nilai 1 pada target yang belum jatuh tempo.
- [ ] Simpan cutoff, cakupan, tenggat, tanggal pertama, dan skor tema pada source context.
- [ ] Uji batas hari 0, 1, 7, 8, 49, dan 50.

### TASK-022 - Implementasikan snapshot nilai dan kelulusan

**Prioritas:** P0  
**Blocked by:** TASK-020, TASK-021, DEC-002  
**Hasil:** Peserta dan petugas berwenang dapat melihat K/M/D/N serta status program tanpa nilai palsu.

- [ ] Buat tabel `grade_snapshots` dan `grade_sources`.
- [ ] Kumpulkan assessment final dan efektif sebagai sumber M/D.
- [ ] Biarkan komponen yang belum tersedia sebagai `NULL`.
- [ ] Hitung N dengan aritmetika desimal setelah seluruh komponen lengkap.
- [ ] Validasi lima bagian Cukup dan ujian final sebelum kelulusan.
- [ ] Pertahankan snapshot lama dan gunakan `supersedes_id`.
- [ ] Buat endpoint rekap dan riwayat nilai.
- [ ] Buat UI P06 Ujian dan nilai.
- [ ] Tampilkan policy version dan alasan komponen belum tersedia.
- [ ] Tambahkan reconstruction dan historical consistency test.

## 11. Koreksi, Audit, dan Pelaporan

### TASK-023 - Implementasikan audit trail dan transactional outbox

**Prioritas:** P0  
**Blocked by:** TASK-010  
**Hasil:** Perubahan penting dapat ditelusuri dan pekerjaan samping tidak mengganggu transaksi akademik.

- [ ] Buat tabel `audit_events` dan `outbox_events`.
- [ ] Catat aktor, tindakan, objek, request ID, serta before/after yang aman.
- [ ] Tulis audit dan outbox pada transaksi domain yang sama.
- [ ] Implementasikan worker claim, retry, backoff, dan dead-letter handling.
- [ ] Jangan simpan password, token, signed URL, atau isi media.
- [ ] Buat endpoint audit sesuai scope.
- [ ] Tambahkan test bahwa kegagalan worker tidak membatalkan commit akademik.

### TASK-024 - Implementasikan alur koreksi hasil final

**Prioritas:** P0  
**Blocked by:** TASK-022, TASK-023, DEC-003  
**Hasil:** Hasil final dapat dikoreksi tanpa menghapus atau menimpa sejarah.

- [ ] Buat tabel `correction_requests`.
- [ ] Implementasikan pengajuan, approval, rejection, dan apply.
- [ ] Buat replacement assessment dengan objek dan jenis yang sama.
- [ ] Tandai hasil lama sebagai superseded.
- [ ] Cegah rantai koreksi bersiklus.
- [ ] Jangan menaikkan attempt tema atau revisi video karena koreksi.
- [ ] Buat snapshot nilai baru setelah koreksi.
- [ ] Gunakan `needs_review` bila koreksi mencabut prasyarat.
- [ ] Tambahkan audit dan authorization test.

### TASK-025 - Implementasikan laporan jurusan

**Prioritas:** P0  
**Blocked by:** TASK-018, TASK-020, TASK-022, TASK-023  
**Hasil:** Admin Jurusan dapat memantau progres, keterlambatan, antrean, dan nilai belum lengkap sesuai lingkup.

- [ ] Buat projection/view progres jurusan.
- [ ] Buat endpoint progres, antrean video/ujian, dan incomplete grades.
- [ ] Terapkan filter cohort dan pagination stabil.
- [ ] Pastikan authorization diterapkan sebelum agregasi.
- [ ] Buat UI J03 Laporan jurusan.
- [ ] Pastikan laporan tidak otomatis membuka media privat.
- [ ] Tambahkan timestamp data dan indikator keterbaruan.

### TASK-026 - Implementasikan laporan dan kebijakan fakultas

**Prioritas:** P0  
**Blocked by:** TASK-006, TASK-022, TASK-023  
**Hasil:** Admin Fakultas dapat melihat laporan agregat serta mengelola lifecycle policy version sesuai mandat.

- [ ] Buat endpoint daftar, draft, approval, dan publish policy.
- [ ] Cegah perubahan in-place pada policy yang telah digunakan.
- [ ] Buat laporan agregat lintas jurusan tanpa membuka data pribadi yang tidak diperlukan.
- [ ] Buat UI F01 Kebijakan dan laporan fakultas.
- [ ] Tampilkan versi, periode berlaku, approval, dan audit.
- [ ] Tambahkan authorization serta historical policy test.

### TASK-027 - Implementasikan ekspor laporan asinkron

**Prioritas:** P1  
**Blocked by:** TASK-025, TASK-026  
**Hasil:** Pengguna berwenang dapat meminta dan mengunduh ekspor sesuai filter tanpa menahan request web.

- [ ] Buat tabel/job model untuk pekerjaan asinkron.
- [ ] Implementasikan endpoint create, status, dan cancel job.
- [ ] Terapkan batas job aktif per pengguna.
- [ ] Buat hasil ekspor di penyimpanan privat.
- [ ] Berikan download URL singkat setelah otorisasi ulang.
- [ ] Catat filter, ruang lingkup, waktu, dan pembuat ekspor.
- [ ] Bersihkan hasil sesuai kebijakan retensi.

## 12. Ketahanan, Keamanan, dan Operasional

### TASK-028 - Lengkapi keamanan aplikasi

**Prioritas:** P0  
**Blocked by:** TASK-008, TASK-010, TASK-017  
**Hasil:** Kontrol keamanan lintas web, API, database, media, dan container tervalidasi.

- [ ] Uji object-level authorization pada seluruh resource UUID.
- [ ] Terapkan rate limit endpoint sensitif.
- [ ] Terapkan security headers dan batas ukuran request.
- [ ] Validasi input, sort, filter, dan URL eksternal dengan allowlist.
- [ ] Pastikan secret hanya berasal dari secret/config runtime.
- [ ] Jalankan container sebagai non-root.
- [ ] Pastikan PostgreSQL dan object storage tidak terekspos publik.
- [ ] Audit log dan error agar bebas data sensitif.
- [ ] Jalankan dependency dan image vulnerability scan.

### TASK-029 - Lengkapi observability dan health monitoring

**Prioritas:** P0  
**Blocked by:** TASK-002, TASK-010, TASK-023  
**Hasil:** Operator dapat mengetahui kesehatan, performa, dan kegagalan sistem tanpa melihat data sensitif.

- [ ] Implementasikan liveness dan readiness endpoint.
- [ ] Implementasikan structured log dengan request/trace ID.
- [ ] Tambahkan metrics latency, error rate, connection pool, outbox, job, dan media.
- [ ] Tambahkan tracing untuk request dan pekerjaan worker.
- [ ] Buat dashboard serta alert dasar.
- [ ] Dokumentasikan correlation ID untuk dukungan pengguna.
- [ ] Pastikan payload akademik dan media tidak masuk telemetry.

### TASK-030 - Implementasikan backup, restore, dan disaster recovery

**Prioritas:** P0  
**Blocked by:** TASK-002, TASK-017  
**Hasil:** Database dan media dapat dipulihkan melalui prosedur yang telah diuji.

- [ ] Buat backup terjadwal PostgreSQL.
- [ ] Buat backup/versioning object storage sesuai retensi.
- [ ] Enkripsi backup dan batasi aksesnya.
- [ ] Dokumentasikan runbook backup dan restore.
- [ ] Jalankan restore drill pada lingkungan terisolasi.
- [ ] Verifikasi konsistensi database dengan referensi media.
- [ ] Catat RPO/RTO pilot setelah pengujian.

## 13. Pengujian dan Rilis Pilot

### TASK-031 - Lengkapi test suite end-to-end

**Prioritas:** P0  
**Blocked by:** TASK-012, TASK-014, TASK-018, TASK-020, TASK-022, TASK-024  
**Hasil:** Seluruh alur utama dan kegagalan kritis dapat diverifikasi otomatis.

- [ ] Uji peserta menemukan target dan mengajukan sesi.
- [ ] Uji Mentor menilai tema sampai attempt kelima.
- [ ] Uji penggantian teknis video tanpa menaikkan revisi.
- [ ] Uji kelayakan dan penilaian video sebagai dua keputusan berbeda.
- [ ] Uji audio wajib sebelum finalisasi.
- [ ] Uji eligibility dan finalisasi ujian.
- [ ] Uji nilai kosong tetap `null`.
- [ ] Uji finalisasi ganda, retry, timeout, dan version conflict.
- [ ] Uji koreksi mempertahankan hasil serta snapshot lama.
- [ ] Uji isolasi data antar peserta, jurusan, dan penugasan.

### TASK-032 - Lakukan accessibility dan responsive QA

**Prioritas:** P0  
**Blocked by:** TASK-009, TASK-025, TASK-026  
**Hasil:** Seluruh 20 layar memenuhi baseline WCAG 2.2 AA dan dapat digunakan pada perangkat target.

- [ ] Uji seluruh fungsi dengan keyboard.
- [ ] Uji pembaca layar pada form, tabel, dialog, dan status async.
- [ ] Uji kontras, focus indicator, target 44 x 44 px, dan reduced motion.
- [ ] Uji zoom 200 persen.
- [ ] Uji desktop, tablet, dan ponsel.
- [ ] Pastikan tabel hanya menggulir pada container tabel.
- [ ] Uji state berisi, kosong, loading, error, retry, dan locked pada setiap layar.
- [ ] Uji preservasi input setelah validasi gagal atau kembali dari dialog.

### TASK-033 - Siapkan staging dan UAT

**Prioritas:** P0  
**Blocked by:** TASK-028, TASK-029, TASK-030, TASK-031, TASK-032  
**Hasil:** Versi kandidat pilot dapat diuji pemilik produk dan pengguna peran pada data nonproduksi.

- [ ] Deploy staging menggunakan image yang sama dengan kandidat production.
- [ ] Jalankan migration dan seed data UAT.
- [ ] Sediakan akun uji untuk seluruh peran.
- [ ] Jalankan skenario UAT pada 20 layar.
- [ ] Verifikasi audit, backup, restore, dan monitoring staging.
- [ ] Catat temuan, severity, pemilik, dan keputusan rilis.
- [ ] Pastikan tidak ada data pribadi nyata pada staging tanpa persetujuan.

### TASK-034 - Rilis pilot dan verifikasi pascarilis

**Prioritas:** P0  
**Blocked by:** TASK-033  
**Hasil:** YAQin tersedia untuk pilot terbatas dengan prosedur rollback dan pemantauan aktif.

- [ ] Bekukan release candidate dan hasilkan image immutable.
- [ ] Backup sebelum migration production.
- [ ] Jalankan migration melalui deployment job tunggal.
- [ ] Deploy gateway, web, API, worker, database, dan storage sesuai urutan runbook.
- [ ] Jalankan smoke test autentikasi dan seluruh alur P0.
- [ ] Pantau error rate, latency, queue, koneksi database, dan media.
- [ ] Verifikasi audit serta idempotency pada transaksi contoh.
- [ ] Dokumentasikan rollback decision dan incident contact.
- [ ] Lakukan review pilot dan susun backlog P1.

## 14. Task P1 Setelah Pilot Stabil

### TASK-035 - Tambahkan notifikasi operasional

**Prioritas:** P1  
**Blocked by:** TASK-023, TASK-034

- [ ] Tentukan channel dan preference notifikasi.
- [ ] Kirim notifikasi dari outbox, bukan dari transaksi utama.
- [ ] Dukung retry serta deduplikasi.
- [ ] Hindari data sensitif dalam isi notifikasi.

### TASK-036 - Tambahkan impor peserta terkontrol

**Prioritas:** P1  
**Blocked by:** TASK-007, TASK-027

- [ ] Sediakan template impor.
- [ ] Validasi seluruh baris sebelum commit.
- [ ] Tampilkan preview error dan duplikasi.
- [ ] Jalankan impor besar sebagai job asinkron.
- [ ] Simpan hasil, audit, dan ringkasan baris.

### TASK-037 - Siapkan fondasi Android tanpa mengubah aturan domain

**Prioritas:** P1  
**Blocked by:** TASK-034

- [ ] Tentukan OAuth/OIDC atau token perangkat.
- [ ] Pertahankan kontrak domain `/api/v1` yang sama.
- [ ] Pisahkan autentikasi perangkat dari session web.
- [ ] Dokumentasikan batas offline dan penyimpanan lokal aman.
- [ ] Jangan mengizinkan finalisasi akademik offline.

## 15. Dependency Roadmap

```text
TASK-001
  +-- TASK-002
  |     +-- TASK-004
  |     +-- TASK-017
  |     +-- TASK-030
  +-- TASK-003
  +-- TASK-009

TASK-004
  +-- TASK-005 -> TASK-007 -> TASK-013 -> TASK-014
  +-- TASK-006 -> TASK-011 -> TASK-012
  +-- TASK-010

TASK-014 -> TASK-015 -> TASK-016 -> TASK-018
TASK-017 ------------------------------+

TASK-018 -> TASK-019 -> TASK-020
TASK-012 + TASK-014 -> TASK-021
TASK-020 + TASK-021 -> TASK-022
TASK-022 + TASK-023 -> TASK-024

TASK-025 + TASK-026 -> TASK-027
TASK-028 + TASK-029 + TASK-030 + TASK-031 + TASK-032
  -> TASK-033 -> TASK-034
```

## 16. Definition of Done Proyek

Proyek MVP dianggap selesai ketika:

- [ ] Seluruh task P0 selesai dan acceptance criteria terpenuhi.
- [ ] Seluruh 20 layar tersedia dengan state berisi, kosong, loading, error, dan locked.
- [ ] Peserta dapat menyelesaikan target, sesi, video, ujian, dan melihat nilai.
- [ ] Mentor dapat menilai tema dan video dengan draft serta finalisasi aman.
- [ ] Dosen dapat menyiapkan, menjalankan, dan memfinalisasi ujian.
- [ ] Admin dapat mengelola peserta, penugasan, kalender, kebijakan, dan laporan sesuai mandat.
- [ ] Nilai kosong tidak pernah diubah menjadi nilai buatan.
- [ ] Finalisasi aman terhadap klik ganda, retry, timeout, dan konflik versi.
- [ ] Hasil final, koreksi, snapshot, dan policy version dapat ditelusuri.
- [ ] Object-level authorization dan isolasi organisasi telah diuji.
- [ ] Backup dan restore drill berhasil.
- [ ] UAT diterima oleh pemilik produk dan pemilik kebijakan akademik.
- [ ] Runbook deployment, rollback, incident, backup, dan pemulihan tersedia.

---

Checklist ini harus diperbarui bersama perubahan PRD, kontrak API, ERD, arsitektur, atau keputusan akademik. Task boleh dipecah menjadi tiket lebih kecil selama hasil end-to-end, dependency, dan acceptance criteria tetap terjaga.
