# Database Design - YAQin

## Aplikasi Pendampingan Hafalan Juz 30

| Atribut | Nilai |
|---|---|
| Dokumen | Rancangan basis data logis dan pedoman implementasi |
| Produk | YAQin - Yakin, Amalin, Mutqin |
| Versi | 1.0 |
| Tanggal | 20 Oktober 2026 |
| Status | Draft untuk peninjauan teknis dan akademik |
| Sumber utama | `Rancangan Aplikasi Tahfidz v 01.pdf` |
| Dokumen terkait | `docs/PRD-Aplikasi-Tahfidz-YAQin.md` |

> Dokumen ini menjabarkan model data relasional YAQin berdasarkan ERD, DFD, arsitektur, aturan bisnis, dan rencana implementasi pada rancangan sumber. Ini belum merupakan migration SQL. Tipe data, indeks, dan constraint yang ditulis sebagai rekomendasi harus disesuaikan dengan database yang dipilih dan keputusan akademik yang telah disahkan.

---

## 1. Tujuan

Rancangan basis data harus:

1. Menyimpan identitas, organisasi, peran, kepesertaan, dan penugasan berbatas waktu.
2. Menyimpan kurikulum 44 tema dalam lima bagian dan kalender program 52 pekan secara berversi.
3. Menjaga riwayat setoran tema, setoran video, ujian, skor, insiden, audio, dan progres.
4. Memisahkan status teknis media dari hasil akademik.
5. Menyimpan hasil final sebagai data historis yang tidak ditimpa.
6. Menyediakan sumber perhitungan K, M, D, dan N yang dapat diperiksa kembali.
7. Mencegah penilaian, kesempatan, revisi, atau finalisasi ganda.
8. Mendukung kontrol akses berdasarkan peran, organisasi, kepemilikan, penugasan, masa berlaku, dan status objek.
9. Menyediakan audit dan koreksi tanpa menghapus konteks hasil sebelumnya.
10. Menjadi sumber data bersama untuk web dan aplikasi Android di masa depan.

## 2. Ruang Lingkup dan Batas Keputusan

Model mencakup 32 entitas logis yang dikelompokkan dalam:

- Identitas dan organisasi.
- Kurikulum, kebijakan, kalender, dan target.
- Sesi pembimbingan dan penilaian tema.
- Video, kelayakan, penilaian, dan media privat.
- Ujian dan soal.
- Rekap nilai, koreksi, dan audit.

Keputusan berikut belum boleh dipaksakan menjadi nilai bawaan di database:

- Cara agregasi nilai Mentor menjadi M.
- Jumlah/bobot soal dan cara agregasi nilai Dosen menjadi D.
- Dukungan skor desimal dan aturan pembulatan.
- Tindak lanjut setelah penilaian tema kelima.
- Detail koreksi setelah isyarat, arti koreksi langsung, dan kejadian berulang.
- Mandat koreksi, perubahan tenggat, akses media, dan retensi media.
- Pilihan database, penyedia hosting, serta kapasitas pilot.

Nilai M, D, dan N harus tetap `NULL` selama sumber atau kebijakan yang diperlukan belum lengkap.

## 3. Pilihan Teknologi yang Direkomendasikan

Rancangan sumber tidak mengunci database tertentu. Untuk implementasi awal, PostgreSQL direkomendasikan karena mendukung:

- Foreign key, unique constraint, check constraint, dan transaksi kuat.
- `uuid`, `timestamptz`, `date`, `numeric`, dan `jsonb`.
- Partial index dan expression index.
- Row locking untuk alokasi nomor kesempatan dan revisi.
- Deferrable constraint dan trigger untuk aturan lintas tabel.
- Row-Level Security sebagai lapisan tambahan bila tim memilih menggunakannya.

Rekomendasi ini bukan keputusan final. Jika database lain dipilih, semua jaminan integritas dalam dokumen ini tetap harus tersedia dengan mekanisme setara.

## 4. Konvensi Umum

### 4.1 Penamaan

- Nama tabel dan kolom menggunakan `snake_case` berbahasa Inggris.
- Primary key menggunakan kolom `id` bertipe UUID.
- Foreign key menggunakan pola `<entity>_id`.
- Kode status disimpan sebagai nilai stabil berbahasa Inggris; antarmuka menerjemahkannya ke Bahasa Indonesia.
- Nama constraint dan indeks menggunakan pola:
  - `pk_<table>`
  - `fk_<table>__<referenced_table>`
  - `uq_<table>__<columns>`
  - `ck_<table>__<rule>`
  - `ix_<table>__<columns>`

### 4.2 Kolom standar

Kecuali tabel penghubung sederhana, tabel operasional disarankan memiliki:

| Kolom | Tipe rekomendasi | Keterangan |
|---|---|---|
| `id` | `uuid` | Primary key internal, tidak berubah |
| `created_at` | `timestamptz` | Waktu pembuatan |
| `created_by` | `uuid`, nullable | Aktor pembuat jika relevan |
| `updated_at` | `timestamptz` | Waktu perubahan terakhir |
| `row_version` | `bigint` | Optimistic concurrency; naik setiap perubahan |

Tabel historis/final tidak memakai hard delete. Jika perlu menonaktifkan data, gunakan status, `valid_to`, atau `deleted_at` sesuai kebijakan retensi.

### 4.3 Waktu

- Timestamp disimpan sebagai waktu absolut menggunakan `timestamptz`.
- Tanggal tenggat disimpan sebagai `date`.
- Perhitungan hari kalender memakai zona `Asia/Jakarta`.
- `scheduled_at` tidak dianggap sebagai tanggal setoran pertama.
- Tanggal setoran pertama berasal dari `actual_at` pada sesi aktual pertama dengan hasil efektif yang sah.

### 4.4 Angka dan skor

- Skor manual Mentor/Dosen berada pada rentang 1 sampai 10.
- Kolom skor direkomendasikan memakai `numeric(4,2)` agar dapat mendukung keputusan desimal tanpa migrasi tipe; API dan constraint kebijakan menentukan apakah pecahan diizinkan.
- Jumlah kesalahan memakai integer non-negatif.
- Nilai komponen K/M/D/N dapat `NULL`.
- Perhitungan nilai menggunakan aritmetika desimal, bukan floating point.

### 4.5 JSON

`jsonb` boleh digunakan untuk:

- Aturan dalam versi kebijakan.
- Snapshot soal dan acuan jawaban.
- Konteks sumber rekap nilai.
- Detail perubahan audit yang tidak menjadi relasi domain.

`jsonb` tidak boleh menggantikan foreign key untuk peserta, tema, penilaian, ujian, hasil, atau entitas utama lain.

## 5. Ringkasan Entitas

| No | Tabel | Domain | Fungsi utama |
|---:|---|---|---|
| 1 | `organizations` | Identitas | Struktur fakultas dan jurusan |
| 2 | `users` | Identitas | Akun seluruh pengguna |
| 3 | `role_grants` | Identitas | Mandat peran pada organisasi |
| 4 | `cohorts` | Program | Angkatan dan versi aturan yang digunakan |
| 5 | `enrollments` | Program | Kepesertaan pengguna pada angkatan |
| 6 | `assignments` | Program | Penugasan Mentor/Dosen kepada peserta |
| 7 | `policy_versions` | Kebijakan | Rubrik dan aturan akademik berversi |
| 8 | `curriculum_versions` | Kurikulum | Versi kurikulum yang dapat dibekukan |
| 9 | `parts` | Kurikulum | Lima bagian Juz 30 |
| 10 | `themes` | Kurikulum | Tema dalam satu bagian |
| 11 | `theme_ranges` | Kurikulum | Rentang surah/ayat per tema |
| 12 | `targets` | Kalender | Target peserta per tema dan tenggat efektif |
| 13 | `deadline_changes` | Kalender | Usulan dan persetujuan perubahan tenggat |
| 14 | `sessions` | Pembimbingan | Pengajuan, jadwal, dan pelaksanaan setoran sinkron |
| 15 | `session_themes` | Pembimbingan | Tema yang disertakan dalam satu sesi |
| 16 | `assessment_records` | Penilaian | Induk untuk penilaian tema, video, dan ujian |
| 17 | `incidents` | Penilaian | Bukti kejadian dan keputusan dihitung/tidak |
| 18 | `theme_assessments` | Penilaian | Subtipe penilaian tema |
| 19 | `video_attempts` | Video | Slot siklus dan revisi akademik |
| 20 | `video_versions` | Video | Versi media/tautan dalam satu slot akademik |
| 21 | `eligibility_reviews` | Video | Keputusan kelayakan versi video |
| 22 | `eligibility_checks` | Video | Butir checklist kelayakan |
| 23 | `media_assets` | Media | Metadata audio/lampiran privat |
| 24 | `video_assessments` | Penilaian | Subtipe penilaian akademik video |
| 25 | `question_versions` | Ujian | Soal dan acuan jawaban berversi |
| 26 | `exams` | Ujian | Pelaksanaan Ujian Dosen |
| 27 | `exam_items` | Ujian | Snapshot butir soal pada ujian |
| 28 | `exam_assessments` | Penilaian | Subtipe penilaian jawaban ujian |
| 29 | `grade_snapshots` | Nilai | Snapshot K/M/D/N dan status program |
| 30 | `grade_sources` | Nilai | Penilaian yang menjadi sumber snapshot |
| 31 | `correction_requests` | Koreksi | Koreksi hasil tanpa menimpa hasil lama |
| 32 | `audit_events` | Audit | Jejak tindakan dan perubahan penting |

## 6. Peta Relasi Utama

```text
organizations
  +-- organizations (parent-child fakultas/jurusan)
  +-- role_grants -- users
  +-- cohorts

cohorts
  +-- curriculum_versions -- parts -- themes -- theme_ranges
  +-- policy_versions
  +-- enrollments -- users
        +-- assignments -- users (Mentor/Dosen)
        +-- targets -- themes -- deadline_changes
        +-- sessions -- session_themes -- themes
        |     +-- theme_assessments -- assessment_records -- incidents
        +-- video_attempts -- video_versions
        |     +-- eligibility_reviews -- eligibility_checks
        |     +-- video_assessments -- assessment_records -- incidents
        |           +-- media_assets (audio)
        +-- exams -- exam_items -- question_versions
        |     +-- exam_assessments -- assessment_records -- incidents
        +-- grade_snapshots -- grade_sources -- assessment_records
        +-- correction_requests -- assessment_records
        +-- audit_events
```

## 7. Kamus Tabel

### 7.1 `organizations`

Menyimpan struktur organisasi bertingkat.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `parent_id` | `uuid` | Ya | FK ke `organizations.id`; fakultas induk jurusan |
| `kind` | `text` | Tidak | `faculty` atau `department` |
| `name` | `text` | Tidak | Nama organisasi |
| `code` | `text` | Ya | Kode institusi bila tersedia |
| `status` | `text` | Tidak | `active` atau `inactive` |

Constraint dan indeks:

- Cegah organisasi menjadi induk dirinya sendiri.
- Cegah siklus pada rantai `parent_id` melalui trigger atau validasi transaksi.
- Jurusan wajib memiliki induk fakultas; fakultas tidak memiliki induk dalam cakupan sistem ini.
- `UNIQUE(parent_id, code)` jika kode organisasi digunakan.
- Indeks pada `parent_id`, `kind`, dan `status`.

### 7.2 `users`

Menyimpan akun seluruh peran. Identitas akademik peserta tidak dijadikan primary key.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `login_identifier` | `text` | Tidak | Unik, dinormalisasi |
| `name` | `text` | Tidak | Nama tampilan |
| `account_status` | `text` | Tidak | `pending`, `active`, `inactive`, `locked` |
| `password_hash` | `text` | Ya | Rahasia autentikasi; dapat kosong bila memakai SSO |
| `last_login_at` | `timestamptz` | Ya | Waktu login terakhir |

Constraint dan indeks:

- `UNIQUE(lower(login_identifier))`.
- Pengguna nonaktif tidak memperoleh sesi baru dan sesi aktifnya dicabut.
- Sandi, token, dan rahasia lain tidak dicatat di `audit_events` atau log umum.

### 7.3 `role_grants`

Menyimpan mandat peran pada lingkup organisasi.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `user_id` | `uuid` | Tidak | FK ke `users.id` |
| `organization_id` | `uuid` | Tidak | FK ke `organizations.id` |
| `role` | `text` | Tidak | `participant`, `mentor`, `lecturer`, `department_admin`, `faculty_admin` |
| `valid_from` | `timestamptz` | Tidak | Awal mandat |
| `valid_to` | `timestamptz` | Ya | Akhir mandat |

Constraint dan indeks:

- `valid_to > valid_from` jika `valid_to` tersedia.
- Hindari mandat aktif yang identik dan saling tumpang tindih.
- Indeks aktif pada `(user_id, role, organization_id, valid_to)`.
- Jenis organisasi harus sesuai peran admin.

### 7.4 `policy_versions`

Menyimpan rubrik, formula, parameter, dan status pengesahan secara berversi.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `version` | `text` | Tidak | Nomor/label versi unik |
| `status` | `text` | Tidak | `draft`, `approved`, `published`, `inactive` |
| `rules` | `jsonb` | Tidak | Aturan berversi yang telah divalidasi |
| `approved_by` | `uuid` | Ya | FK ke `users.id` |
| `approved_at` | `timestamptz` | Ya | Waktu pengesahan |
| `effective_from` | `timestamptz` | Ya | Awal berlaku |

Aturan:

- Versi `published` tidak diedit; perubahan membuat versi baru.
- `approved_by` dan `approved_at` wajib ketika status mencapai `approved` atau `published`.
- `rules` tidak boleh berisi asumsi agregasi M/D yang belum disahkan.

### 7.5 `curriculum_versions`

Menyimpan versi kurikulum.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `version` | `text` | Tidak | Unik |
| `status` | `text` | Tidak | `draft`, `published`, `inactive` |
| `title` | `text` | Tidak | Nama versi kurikulum |
| `published_at` | `timestamptz` | Ya | Waktu terbit |

Versi terbit tidak ditimpa. Perubahan struktur tema membuat versi baru.

### 7.6 `cohorts`

Mengikat angkatan ke organisasi, versi kurikulum, dan versi kebijakan.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `organization_id` | `uuid` | Tidak | FK ke jurusan |
| `curriculum_version_id` | `uuid` | Tidak | FK ke `curriculum_versions.id` |
| `policy_version_id` | `uuid` | Tidak | FK ke `policy_versions.id` |
| `name` | `text` | Tidak | Nama angkatan |
| `start_date` | `date` | Tidak | Awal program |
| `close_date` | `date` | Ya | Penutupan program |
| `status` | `text` | Tidak | `draft`, `active`, `closed`, `archived` |

Constraint:

- `close_date >= start_date`.
- Organisasi harus berjenis jurusan.
- Kurikulum dan kebijakan harus berstatus layak digunakan sebelum angkatan aktif.

### 7.7 `enrollments`

Menghubungkan akun peserta ke angkatan.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `user_id` | `uuid` | Tidak | FK ke `users.id` |
| `cohort_id` | `uuid` | Tidak | FK ke `cohorts.id` |
| `nim_snapshot` | `text` | Tidak | Snapshot NIM saat kepesertaan |
| `status` | `text` | Tidak | `active`, `completed`, `withdrawn`, `inactive` |
| `joined_at` | `timestamptz` | Tidak | Waktu bergabung |

Constraint dan indeks:

- `UNIQUE(user_id, cohort_id)`.
- NIM tidak menjadi primary key.
- `UNIQUE(cohort_id, nim_snapshot)` bila NIM unik per angkatan/jurusan.

### 7.8 `assignments`

Menyimpan penugasan Mentor atau Dosen kepada satu kepesertaan.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `enrollment_id` | `uuid` | Tidak | FK ke `enrollments.id` |
| `staff_id` | `uuid` | Tidak | FK ke `users.id` |
| `role` | `text` | Tidak | `mentor` atau `lecturer` |
| `valid_from` | `timestamptz` | Tidak | Awal penugasan |
| `valid_to` | `timestamptz` | Ya | Akhir penugasan |
| `reason` | `text` | Ya | Alasan perubahan/pemindahan |

Aturan:

- Petugas harus memiliki `role_grants` aktif dan sesuai organisasi.
- Hindari penugasan aktif yang tumpang tindih jika kebijakan hanya mengizinkan satu Mentor/Dosen aktif.
- Penugasan lama tidak dihapus ketika petugas berubah.

### 7.9 `parts`

Menyimpan lima bagian pada satu versi kurikulum.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `curriculum_version_id` | `uuid` | Tidak | FK ke `curriculum_versions.id` |
| `sequence_no` | `smallint` | Tidak | 1 sampai 5 |
| `title` | `text` | Tidak | Nama bagian |

Constraint:

- `CHECK(sequence_no BETWEEN 1 AND 5)`.
- `UNIQUE(curriculum_version_id, sequence_no)`.

### 7.10 `themes`

Menyimpan tema pada satu bagian.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `part_id` | `uuid` | Tidak | FK ke `parts.id` |
| `sequence_no` | `smallint` | Tidak | Urutan dalam bagian |
| `title` | `text` | Tidak | Judul tema |
| `description` | `text` | Ya | Ringkasan materi |

Constraint:

- `sequence_no > 0`.
- `UNIQUE(part_id, sequence_no)`.
- Versi kurikulum pilot harus menghasilkan jumlah tema per bagian 10, 8, 6, 5, dan 15. Pemeriksaan ini dilakukan saat menerbitkan versi, bukan pada setiap insert tunggal.

### 7.11 `theme_ranges`

Menyimpan satu atau lebih rentang surah/ayat untuk suatu tema.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `theme_id` | `uuid` | Tidak | FK ke `themes.id` |
| `sequence_no` | `smallint` | Tidak | Urutan rentang dalam tema |
| `surah_no` | `smallint` | Tidak | 78 sampai 114 untuk Juz 30 |
| `ayah_start` | `smallint` | Tidak | Ayat awal |
| `ayah_end` | `smallint` | Tidak | Ayat akhir |

Constraint:

- `CHECK(surah_no BETWEEN 78 AND 114)`.
- `CHECK(ayah_start > 0 AND ayah_end >= ayah_start)`.
- `UNIQUE(theme_id, sequence_no)`.
- Mendukung tema lintas surah seperti Al-Ikhlas, Al-Falaq, dan An-Nas.

### 7.12 `targets`

Memetakan peserta ke tema dan tenggat.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `enrollment_id` | `uuid` | Tidak | FK ke `enrollments.id` |
| `theme_id` | `uuid` | Tidak | FK ke `themes.id` |
| `initial_due_date` | `date` | Tidak | Tenggat awal |
| `effective_due_date` | `date` | Tidak | Tenggat yang saat ini berlaku |
| `status` | `text` | Tidak | `scheduled`, `active`, `completed`, `closed` |

Constraint:

- `UNIQUE(enrollment_id, theme_id)`.
- Tema harus berasal dari versi kurikulum angkatan peserta.
- `effective_due_date` hanya berubah melalui perubahan tenggat yang disahkan.
- Indeks `(enrollment_id, effective_due_date, status)`.

### 7.13 `deadline_changes`

Mencatat usulan dan persetujuan perubahan tenggat.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `target_id` | `uuid` | Tidak | FK ke `targets.id` |
| `requested_by` | `uuid` | Tidak | FK ke `users.id` |
| `approved_by` | `uuid` | Ya | FK ke `users.id` |
| `old_date` | `date` | Tidak | Tenggat sebelum perubahan |
| `new_date` | `date` | Tidak | Tenggat yang diusulkan |
| `reason` | `text` | Tidak | Alasan wajib |
| `status` | `text` | Tidak | `pending`, `approved`, `rejected`, `cancelled` |
| `decided_at` | `timestamptz` | Ya | Waktu keputusan |

Aturan:

- Hanya perubahan berstatus `approved` yang memperbarui `targets.effective_due_date`.
- Persetujuan dan perubahan target terjadi dalam satu transaksi.
- Nilai lama dan baru tidak dihapus.

### 7.14 `sessions`

Menyimpan pengajuan, jadwal, dan pelaksanaan setoran tema sinkron.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `enrollment_id` | `uuid` | Tidak | FK ke `enrollments.id` |
| `part_id` | `uuid` | Tidak | FK ke `parts.id` |
| `mentor_id` | `uuid` | Tidak | FK ke `users.id` |
| `scheduled_at` | `timestamptz` | Ya | Jadwal yang disepakati |
| `actual_at` | `timestamptz` | Ya | Pelaksanaan aktual |
| `mode` | `text` | Tidak | `in_person` atau `video_call` |
| `status` | `text` | Tidak | `proposed`, `scheduled`, `in_progress`, `completed`, `no_show`, `cancelled` |
| `notes` | `text` | Ya | Catatan sesi |

Aturan:

- `actual_at` hanya diisi ketika sesi benar-benar berlangsung.
- Mentor harus memiliki penugasan aktif kepada peserta pada waktu sesi.
- `part_id` harus berasal dari versi kurikulum angkatan peserta.
- Sesi selesai hanya jika seluruh penilaian yang hendak difinalkan valid.

### 7.15 `session_themes`

Tabel penghubung sesi dengan tema.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `session_id` | `uuid` | Tidak | FK ke `sessions.id` |
| `theme_id` | `uuid` | Tidak | FK ke `themes.id` |

Constraint:

- `UNIQUE(session_id, theme_id)`.
- Semua tema dalam satu sesi harus berada pada `sessions.part_id`.
- Satu sesi minimal memiliki satu tema sebelum dijadwalkan/final.

### 7.16 `assessment_records`

Induk bersama untuk tiga jenis penilaian: tema, video, dan ujian.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `enrollment_id` | `uuid` | Tidak | FK ke `enrollments.id` |
| `assessor_id` | `uuid` | Tidak | FK ke `users.id` |
| `policy_version_id` | `uuid` | Tidak | FK ke `policy_versions.id` |
| `kind` | `text` | Tidak | `theme`, `video`, atau `exam` |
| `manual_score` | `numeric(4,2)` | Ya | 1 sampai 10 ketika diisi |
| `status` | `text` | Tidak | `draft`, `final`, `superseded`, `needs_review` |
| `finalized_at` | `timestamptz` | Ya | Waktu finalisasi |
| `row_version` | `bigint` | Tidak | Kontrol konflik |

Aturan penting:

- Tepat satu subtype harus memakai `id` yang sama: `theme_assessments`, `video_assessments`, atau `exam_assessments`.
- `kind` harus sesuai subtype.
- Penilai harus memiliki mandat aktif atas peserta/objek saat tindakan dilakukan.
- Skor dapat kosong pada draft dan wajib sesuai kebijakan saat final.
- Record final tidak diedit; koreksi membuat record pengganti.

Aturan tepat satu subtype membutuhkan deferred trigger/constraint atau prosedur finalisasi transaksional karena tiga foreign key terpisah tidak cukup.

### 7.17 `incidents`

Menyimpan bukti kejadian pada semua jenis penilaian.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `assessment_id` | `uuid` | Tidak | FK ke `assessment_records.id` |
| `category` | `text` | Tidak | Satu kategori utama |
| `location` | `text` | Tidak | Ayat, posisi, atau timestamp |
| `assistance_type` | `text` | Tidak | `none`, `signal`, `answer` |
| `self_corrected` | `boolean` | Tidak | Koreksi mandiri |
| `counted` | `boolean` | Tidak | Dihitung sebagai kesalahan atau tidak |
| `count_reason` | `text` | Ya | Alasan keputusan hitung |
| `notes` | `text` | Ya | Catatan penilai |

Aturan:

- Satu kejadian memiliki satu kategori utama.
- `counted` tidak ditentukan oleh klien secara bebas saat final; layanan domain memvalidasi terhadap versi kebijakan.
- Data insiden final tidak ditimpa.
- Indeks `(assessment_id, counted)`.

### 7.18 `theme_assessments`

Subtipe penilaian tema.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK sekaligus FK ke `assessment_records.id` |
| `session_theme_id` | `uuid` | Tidak | FK ke `session_themes.id` |
| `attempt_no` | `smallint` | Tidak | 1 sampai 5 per peserta-tema |
| `outcome` | `text` | Tidak | `enough`, `repeat`, `follow_up` |
| `notes` | `text` | Ya | Catatan hasil |

Constraint:

- `CHECK(attempt_no BETWEEN 1 AND 5)`.
- Nomor kesempatan dialokasikan server dengan lock pada progres peserta-tema.
- Penilaian kelima yang belum Cukup menghasilkan `follow_up`.
- Koreksi hasil tidak menaikkan `attempt_no`.
- Peserta pada `assessment_records` harus sama dengan peserta pada sesi.

### 7.19 `video_attempts`

Menyimpan slot akademik video berdasarkan bagian, siklus, dan revisi.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `enrollment_id` | `uuid` | Tidak | FK ke `enrollments.id` |
| `part_id` | `uuid` | Tidak | FK ke `parts.id` |
| `cycle_no` | `integer` | Tidak | Dimulai dari 1 |
| `revision_no` | `smallint` | Tidak | 0 untuk awal, 1 sampai 3 untuk revisi |
| `status` | `text` | Tidak | `open`, `submitted`, `under_review`, `finalized`, `closed` |

Constraint:

- `CHECK(cycle_no >= 1)`.
- `CHECK(revision_no BETWEEN 0 AND 3)`.
- `UNIQUE(enrollment_id, part_id, cycle_no, revision_no)`.
- Slot hanya dibuka server berdasarkan hasil efektif.
- Revisi 3 yang masih Belum Cukup membuka siklus berikutnya pada revisi 0.

### 7.20 `video_versions`

Menyimpan versi media/tautan pada satu slot akademik.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `attempt_id` | `uuid` | Tidak | FK ke `video_attempts.id` |
| `version_no` | `integer` | Tidak | Nomor versi media |
| `video_url` | `text` | Tidak | Tautan HTTPS pada host yang diizinkan |
| `recorded_date` | `date` | Tidak | Tanggal rekaman |
| `submitted_at` | `timestamptz` | Tidak | Waktu pengiriman |
| `status` | `text` | Tidak | `submitted`, `available`, `failed`, `replaced` |

Constraint:

- `version_no >= 1`.
- `UNIQUE(attempt_id, version_no)`.
- Penggantian teknis menambah `version_no` tetapi tidak mengubah `revision_no`.
- Server tidak mengambil URL sembarang; validasi skema dan allowlist host.

### 7.21 `eligibility_reviews`

Menyimpan review kelayakan untuk versi video tertentu.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `video_version_id` | `uuid` | Tidak | FK ke `video_versions.id` |
| `reviewer_id` | `uuid` | Tidak | FK ke `users.id` |
| `checklist_version` | `text` | Tidak | Versi checklist |
| `decision` | `text` | Tidak | `eligible` atau `ineligible` |
| `reason` | `text` | Ya | Wajib jika tidak layak |
| `status` | `text` | Tidak | `draft`, `final`, `superseded` |
| `finalized_at` | `timestamptz` | Ya | Waktu finalisasi |

Aturan:

- Review final `ineligible` wajib memiliki alasan.
- Review `eligible` hanya valid jika semua butir wajib lulus.
- Review menunjuk versi video, bukan seluruh attempt.

### 7.22 `eligibility_checks`

Menyimpan setiap butir checklist.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `review_id` | `uuid` | Tidak | FK ke `eligibility_reviews.id` |
| `criterion_code` | `text` | Tidak | Kode butir stabil |
| `passed` | `boolean` | Tidak | Hasil pemeriksaan |
| `notes` | `text` | Ya | Penjelasan bila perlu |

Constraint:

- `UNIQUE(review_id, criterion_code)`.
- Daftar butir yang diwajibkan mengikuti `checklist_version`.

### 7.23 `media_assets`

Menyimpan metadata media privat. Berkas berada di object storage privat, bukan blob database.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `owner_id` | `uuid` | Tidak | FK ke `users.id` |
| `storage_key` | `text` | Tidak | Kunci internal unik, bukan URL publik |
| `mime_type` | `text` | Tidak | Jenis berkas yang tervalidasi |
| `size_bytes` | `bigint` | Tidak | Ukuran berkas |
| `checksum` | `text` | Tidak | Integritas/duplikasi |
| `status` | `text` | Tidak | `uploading`, `available`, `failed`, `quarantined`, `deleted` |
| `created_at` | `timestamptz` | Tidak | Waktu pembuatan |

Aturan:

- `UNIQUE(storage_key)`.
- `size_bytes > 0`.
- Finalisasi hanya dapat memakai media berstatus `available`.
- URL akses dibuat sementara setelah otorisasi; tidak disimpan permanen.
- Penghapusan media tidak menghapus jejak akademik atau audit.

### 7.24 `video_assessments`

Subtipe penilaian akademik video.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK sekaligus FK ke `assessment_records.id` |
| `video_version_id` | `uuid` | Tidak | FK ke `video_versions.id` |
| `eligibility_review_id` | `uuid` | Tidak | FK ke `eligibility_reviews.id` |
| `audio_asset_id` | `uuid` | Ya | FK ke `media_assets.id`; wajib saat final |
| `counted_errors` | `integer` | Tidak | Dihitung server dari insiden |
| `outcome` | `text` | Tidak | `enough` atau `not_enough` |

Aturan:

- Review harus final, `eligible`, dan menunjuk `video_version_id` yang sama.
- `counted_errors` sama dengan jumlah `incidents.counted = true`.
- `counted_errors >= 0`.
- 0 sampai 3 menghasilkan `enough`; 4 atau lebih menghasilkan `not_enough`.
- `audio_asset_id` boleh kosong pada draft, tetapi wajib dan `available` saat final.
- Skor manual pada induk tidak menentukan status video.

### 7.25 `question_versions`

Menyimpan soal berversi dari aplikasi atau Dosen.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `author_id` | `uuid` | Ya | FK ke `users.id`; kosong untuk soal sistem |
| `source` | `text` | Tidak | `application` atau `lecturer` |
| `kind` | `text` | Tidak | `continue_verses`, `surah_order`, `recitation` |
| `stimulus` | `text` | Tidak | Stimulus soal |
| `answer_reference` | `jsonb` | Tidak | Acuan privat untuk penguji |
| `scope` | `jsonb` | Tidak | Surah, tema, dan rentang yang diizinkan |
| `version_no` | `integer` | Tidak | Versi soal |
| `status` | `text` | Tidak | `draft`, `verified`, `inactive` |

Aturan:

- Soal sambung ayat menyimpan referensi tiga ayat jawaban secara eksplisit.
- Kandidat di batas akhir cakupan ditahan dari pemilihan otomatis sampai aturan disahkan.
- Acuan jawaban tidak boleh terkirim pada respons peserta.

### 7.26 `exams`

Menyimpan pelaksanaan Ujian Dosen.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `enrollment_id` | `uuid` | Tidak | FK ke `enrollments.id` |
| `lecturer_id` | `uuid` | Tidak | FK ke `users.id` |
| `policy_version_id` | `uuid` | Tidak | FK ke `policy_versions.id` |
| `actual_at` | `timestamptz` | Ya | Waktu ujian berlangsung |
| `status` | `text` | Tidak | `draft`, `scheduled`, `in_progress`, `final`, `cancelled` |
| `row_version` | `bigint` | Tidak | Kontrol konflik |
| `finalized_at` | `timestamptz` | Ya | Waktu finalisasi |

Aturan:

- Peserta harus memiliki lima bagian Cukup berdasarkan hasil efektif.
- Dosen harus memiliki penugasan aktif.
- Ujian final wajib memiliki butir dan penilaian lengkap sesuai kebijakan paket.

### 7.27 `exam_items`

Memetakan versi soal ke ujian dan menyimpan snapshot historis.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `exam_id` | `uuid` | Tidak | FK ke `exams.id` |
| `question_version_id` | `uuid` | Tidak | FK ke `question_versions.id` |
| `sequence_no` | `integer` | Tidak | Urutan dalam paket |
| `question_snapshot` | `jsonb` | Tidak | Salinan stimulus, cakupan, dan acuan |
| `weight` | `numeric(6,3)` | Ya | Kosong sampai kebijakan bobot disahkan |

Constraint:

- `UNIQUE(exam_id, sequence_no)`.
- `sequence_no > 0`.
- Snapshot tidak berubah ketika bank soal diedit.
- Jumlah dan bobot soal mengikuti versi kebijakan, bukan nilai bawaan database.

### 7.28 `exam_assessments`

Subtipe penilaian jawaban lisan pada satu butir ujian.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK sekaligus FK ke `assessment_records.id` |
| `exam_item_id` | `uuid` | Tidak | FK ke `exam_items.id` |
| `notes` | `text` | Ya | Catatan performa/jawaban lisan |

Aturan:

- Induk `assessment_records.kind` harus `exam`.
- Peserta dan Dosen pada induk harus sama dengan ujian.
- Skor manual berada pada induk dan divalidasi 1 sampai 10.
- Cara agregasi D menunggu kebijakan yang disahkan.

### 7.29 `grade_snapshots`

Menyimpan rekap nilai pada satu titik waktu beserta konteks sumbernya.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `enrollment_id` | `uuid` | Tidak | FK ke `enrollments.id` |
| `policy_version_id` | `uuid` | Tidak | FK ke `policy_versions.id` |
| `k_value` | `numeric(6,3)` | Ya | Komponen keaktifan |
| `m_value` | `numeric(6,3)` | Ya | Komponen Mentor |
| `d_value` | `numeric(6,3)` | Ya | Komponen Dosen |
| `n_value` | `numeric(6,3)` | Ya | Nilai akhir |
| `status` | `text` | Tidak | Lihat status di bawah |
| `source_context` | `jsonb` | Tidak | Tenggat, tanggal pertama, cutoff, cakupan, versi input |
| `calculated_at` | `timestamptz` | Tidak | Waktu perhitungan |
| `supersedes_id` | `uuid` | Ya | FK ke snapshot sebelumnya |

Status yang direkomendasikan:

- `incomplete`
- `ready_for_exam`
- `awaiting_exam`
- `awaiting_components`
- `graduated`
- `not_graduated`
- `needs_review`

Aturan:

- K final memakai seluruh 44 target.
- Rekap sementara menyimpan cakupan dan jumlah target tertunggak.
- Tema yang belum jatuh tempo tidak otomatis diberi nilai 1.
- M/D tetap `NULL` sampai sumber lengkap dan agregasi disahkan.
- N hanya dihitung jika K/M/D lengkap dan ujian final tersedia.
- Formula N: `0.2 * K + 0.4 * M + 0.4 * D`.
- Lulus jika N minimal 6, lima bagian Cukup, dan ujian final.
- Koreksi menghasilkan snapshot baru; snapshot lama tetap tersedia.

### 7.30 `grade_sources`

Menghubungkan snapshot nilai dengan record penilaian yang benar-benar digunakan.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `grade_snapshot_id` | `uuid` | Tidak | FK ke `grade_snapshots.id` |
| `assessment_id` | `uuid` | Tidak | FK ke `assessment_records.id` |
| `component` | `text` | Tidak | `K`, `M`, atau `D` |
| `contribution` | `numeric(8,4)` | Ya | Kontribusi jika kebijakan mendefinisikannya |

Constraint:

- `UNIQUE(grade_snapshot_id, assessment_id, component)`.
- Hanya penilaian final dan efektif yang boleh menjadi sumber.
- Penilaian harus milik peserta yang sama dengan snapshot.

Konteks K yang bukan satu `assessment_record` disimpan di `grade_snapshots.source_context`, termasuk tenggat efektif, tanggal pertama, cutoff, dan cakupan 44 target.

### 7.31 `correction_requests`

Menyimpan permintaan koreksi hasil penilaian.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `original_assessment_id` | `uuid` | Tidak | FK ke `assessment_records.id` |
| `replacement_assessment_id` | `uuid` | Ya | FK ke `assessment_records.id` |
| `requested_by` | `uuid` | Tidak | FK ke `users.id` |
| `approved_by` | `uuid` | Ya | FK ke `users.id` |
| `reason` | `text` | Tidak | Alasan koreksi |
| `status` | `text` | Tidak | `pending`, `approved`, `rejected`, `applied`, `cancelled` |
| `decided_at` | `timestamptz` | Ya | Waktu keputusan |

Aturan:

- Hasil asli tidak diubah atau dihapus.
- Pengganti harus mempunyai peserta, jenis subtype, dan objek akademik yang sama.
- Rantai koreksi tidak boleh melingkar.
- Koreksi tidak menaikkan kesempatan tema/revisi video.
- Ketika koreksi mencabut prasyarat, snapshot nilai baru berstatus `needs_review` dibuat.

### 7.32 `audit_events`

Menyimpan jejak tindakan penting. Audit bukan pengganti relasi domain.

| Kolom | Tipe | Null | Aturan |
|---|---|---:|---|
| `id` | `uuid` | Tidak | PK |
| `actor_id` | `uuid` | Ya | FK ke `users.id`; kosong untuk proses sistem |
| `action` | `text` | Tidak | Kode tindakan |
| `object_type` | `text` | Tidak | Jenis objek |
| `object_reference` | `text` | Tidak | ID/referensi untuk penelusuran log |
| `request_id` | `uuid` | Ya | Korelasi permintaan |
| `before_data` | `jsonb` | Ya | Data relevan sebelum perubahan |
| `after_data` | `jsonb` | Ya | Data relevan setelah perubahan |
| `occurred_at` | `timestamptz` | Tidak | Waktu kejadian |

Aturan:

- Audit mencatat perubahan kebijakan, penugasan, tenggat, penilaian, koreksi, dan nilai.
- Audit tidak menyimpan sandi, token, cookie, URL bertanda tangan, atau isi rekaman.
- Akses baca audit dibatasi sesuai mandat.
- Indeks `(object_type, object_reference, occurred_at)` dan `(actor_id, occurred_at)`.

## 8. Constraint Lintas Tabel

Aturan berikut tidak cukup dijamin oleh satu foreign key dan perlu domain service, trigger, atau transaksi terkontrol:

1. Tema target harus berasal dari versi kurikulum angkatan peserta.
2. Bagian pada sesi/video harus berasal dari versi kurikulum yang sama.
3. Semua tema dalam sesi harus berasal dari satu bagian yang sama dengan `sessions.part_id`.
4. Peserta pada sesi, video, ujian, penilaian, dan snapshot harus konsisten.
5. Penilai harus memiliki mandat aktif dan sesuai jenis penilaian.
6. Tepat satu subtype harus ada untuk setiap `assessment_records`.
7. `assessment_records.kind` harus sesuai subtype.
8. Review video yang digunakan oleh `video_assessments` harus berstatus Layak dan menunjuk versi video yang sama.
9. Audio final harus tersedia dan dapat diakses oleh penilai yang sah.
10. `counted_errors` harus sama dengan jumlah insiden terhitung.
11. Nomor kesempatan tema dialokasikan per peserta-tema, bukan per sesi.
12. Nomor siklus/revisi video dialokasikan server berdasarkan hasil efektif.
13. Hanya hasil final dan efektif yang boleh memperbarui progres.
14. Sumber snapshot nilai harus menunjuk hasil final yang efektif dan milik peserta yang sama.
15. Rantai koreksi tidak boleh melingkar atau berpindah objek akademik.
16. Kelulusan hanya dapat diterbitkan setelah lima bagian Cukup, ujian final, dan K/M/D lengkap.

## 9. Status Referensi

Implementasi dapat memakai tabel referensi atau kolom `text` dengan `CHECK`. Menggunakan kode teks dengan constraint lebih fleksibel untuk pilot selama perubahan status tetap melalui migration.

| Domain | Nilai minimum |
|---|---|
| Peran | `participant`, `mentor`, `lecturer`, `department_admin`, `faculty_admin` |
| Akun | `pending`, `active`, `inactive`, `locked` |
| Kebijakan | `draft`, `approved`, `published`, `inactive` |
| Kurikulum | `draft`, `published`, `inactive` |
| Sesi | `proposed`, `scheduled`, `in_progress`, `completed`, `no_show`, `cancelled` |
| Jenis penilaian | `theme`, `video`, `exam` |
| Status penilaian | `draft`, `final`, `superseded`, `needs_review` |
| Hasil tema | `enough`, `repeat`, `follow_up` |
| Kelayakan video | `eligible`, `ineligible` |
| Hasil video | `enough`, `not_enough` |
| Media | `uploading`, `available`, `failed`, `quarantined`, `deleted` |
| Koreksi | `pending`, `approved`, `rejected`, `applied`, `cancelled` |
| Rekap | `incomplete`, `ready_for_exam`, `awaiting_exam`, `awaiting_components`, `graduated`, `not_graduated`, `needs_review` |

Label UI Bahasa Indonesia dipetakan di lapisan aplikasi, misalnya `enough` menjadi `Cukup` dan `not_enough` menjadi `Belum Cukup`.

## 10. Indeks yang Direkomendasikan

Selain indeks PK dan UNIQUE:

| Tabel | Indeks | Tujuan |
|---|---|---|
| `role_grants` | `(user_id, role, organization_id, valid_to)` | Pemeriksaan mandat aktif |
| `enrollments` | `(cohort_id, status)` | Daftar peserta angkatan |
| `assignments` | `(enrollment_id, role, valid_to)` | Petugas aktif per peserta |
| `targets` | `(enrollment_id, effective_due_date, status)` | Kalender dan tunggakan |
| `sessions` | `(mentor_id, scheduled_at, status)` | Antrean Mentor |
| `sessions` | `(enrollment_id, actual_at)` | Riwayat dan tanggal setoran pertama |
| `assessment_records` | `(enrollment_id, kind, status, finalized_at)` | Riwayat penilaian |
| `incidents` | `(assessment_id, counted)` | Hitungan kesalahan |
| `video_attempts` | `(enrollment_id, part_id, status)` | Progres video |
| `video_versions` | `(attempt_id, version_no DESC)` | Versi media terbaru |
| `eligibility_reviews` | `(video_version_id, status, finalized_at)` | Review efektif |
| `exams` | `(lecturer_id, status, actual_at)` | Antrean Dosen |
| `grade_snapshots` | `(enrollment_id, calculated_at DESC)` | Rekap terbaru |
| `correction_requests` | `(original_assessment_id, status)` | Koreksi aktif |
| `audit_events` | `(object_type, object_reference, occurred_at DESC)` | Audit objek |

Indeks parsial untuk status aktif/final dapat ditambahkan setelah pola query aktual diukur. Hindari indeks berlebih sebelum profil beban tersedia.

## 11. Transaksi Kritis

### 11.1 Finalisasi penilaian tema

Dalam satu transaksi:

1. Verifikasi sesi, peserta, Mentor, dan mandat aktif.
2. Kunci progres peserta-tema.
3. Periksa `expected_version` dan Idempotency-Key.
4. Alokasikan `attempt_no` berikutnya pada rentang 1-5.
5. Validasi skor, insiden, catatan, dan outcome.
6. Simpan `assessment_records` dan `theme_assessments`.
7. Simpan `incidents`.
8. Perbarui proyeksi progres tema.
9. Catat `audit_events` dan event outbox.
10. Commit sebelum mengirim respons berhasil.

### 11.2 Finalisasi kelayakan video

Dalam satu transaksi:

1. Verifikasi versi video dan Mentor.
2. Periksa checklist lengkap.
3. Wajibkan alasan jika Tidak Layak.
4. Simpan review final dan checklist.
5. Perbarui status versi/attempt yang relevan.
6. Catat audit dan outbox.

Penolakan teknis tidak membuat `video_attempts` baru dan tidak menaikkan `revision_no`.

### 11.3 Finalisasi penilaian video

Dalam satu transaksi:

1. Kunci progres peserta-bagian.
2. Verifikasi versi video dan review Layak yang sama.
3. Verifikasi penugasan, versi kebijakan, dan konflik versi.
4. Validasi insiden dan hitung jumlah `counted = true` di server.
5. Verifikasi audio `available`.
6. Tentukan `enough` untuk 0-3 atau `not_enough` untuk minimal 4.
7. Simpan induk, subtype, insiden, progres, audit, dan outbox.
8. Jika Belum Cukup, buka revisi/siklus berikut hanya sesuai aturan server.
9. Commit.

### 11.4 Finalisasi ujian

Dalam satu transaksi:

1. Verifikasi lima bagian Cukup dan penugasan Dosen.
2. Verifikasi paket soal, snapshot, dan kelengkapan setiap penilaian.
3. Simpan status ujian final dan penilaian final.
4. Hitung D hanya jika agregasi sudah disahkan.
5. Buat snapshot nilai baru atau status belum lengkap.
6. Catat audit dan outbox.

### 11.5 Penerbitan rekap nilai

Dalam satu transaksi konsisten:

1. Tentukan versi kebijakan dan cutoff sumber.
2. Hitung K berdasarkan tenggat efektif dan tanggal pertama di Asia/Jakarta.
3. Kumpulkan sumber M/D yang final dan efektif.
4. Jika aturan/sumber belum lengkap, simpan status serta komponen yang tersedia tanpa nilai palsu.
5. Jika lengkap, hitung N dengan aritmetika desimal.
6. Simpan `grade_snapshots`, `grade_sources`, `source_context`, dan audit.
7. Jangan mengubah snapshot lama.

## 12. Idempotensi dan Konkurensi

- Setiap finalisasi menerima `expected_version`.
- Setiap permintaan perubahan akademik kritis menerima `Idempotency-Key`.
- Kunci diikat pada aktor, endpoint, dan hash payload.
- Retry identik mengembalikan hasil sebelumnya.
- Kunci sama dengan payload berbeda ditolak.
- Row lock digunakan pada unit alokasi:
  - peserta-tema untuk kesempatan tema;
  - peserta-bagian untuk siklus/revisi video;
  - ujian untuk finalisasi paket;
  - peserta untuk penerbitan snapshot nilai.
- Unique constraint tetap wajib walaupun UI mencegah klik ganda.
- Timeout klien tidak dianggap sebagai bukti transaksi gagal; klien harus memeriksa status dengan request/kunci yang sama.

Tabel teknis idempotensi dan outbox boleh ditambahkan saat implementasi. Keduanya tidak termasuk 32 entitas domain pada ERD sumber.

## 13. Perhitungan Keaktifan K

Untuk setiap target tema:

| Selisih tanggal pertama terhadap tenggat efektif | Skor |
|---|---:|
| Tepat waktu atau lebih awal | 10 |
| 1-7 hari | 9 |
| 8-14 hari | 8 |
| 15-21 hari | 7 |
| 22-28 hari | 6 |
| 29-35 hari | 5 |
| 36-42 hari | 4 |
| 43-49 hari | 3 |
| Lebih dari 49 hari | 2 |
| Belum setor saat periode ditutup | 1 |

Aturan penyimpanan:

- Tanggal pertama diturunkan dari sesi aktual pertama pada hasil efektif.
- Mengulang tidak mengganti tanggal pertama.
- Perubahan tenggat yang sah mengubah konteks perhitungan, bukan riwayat target lama.
- `source_context` pada snapshot menyimpan tenggat efektif, tanggal pertama, cutoff, skor per tema, cakupan, dan jumlah tunggakan.
- K final adalah rata-rata seluruh 44 tema.
- K sementara hanya memakai cakupan yang sah dan tidak memberi skor 1 untuk target yang belum jatuh tempo.

## 14. Nilai Akhir dan Snapshot

Setelah M dan D dapat dihitung berdasarkan kebijakan yang disahkan:

```text
N = 0.2 * K + 0.4 * M + 0.4 * D
```

Syarat `graduated`:

1. Lima bagian memiliki hasil efektif Cukup.
2. Ujian Dosen berstatus final.
3. K, M, dan D tidak `NULL`.
4. N minimal 6.

Tidak ada ambang Dosen terpisah. Contoh hasil yang harus didukung:

- K=8, M=8, D=3 menghasilkan N=6.00 dan Lulus jika ujian final.
- K=10, M=10, D=1 menghasilkan N=6.40 dan Lulus jika ujian final.
- K=10, M=10, D=NULL menghasilkan status belum lengkap, bukan Lulus.
- Nilai kosong tidak menjadi 0 atau 1.

Presisi, pembulatan tampilan, dan perbandingan nilai dekat ambang menunggu keputusan akademik. Simpan nilai mentah desimal dan versi kebijakan agar hasil dapat dihitung ulang.

## 15. Keamanan dan Privasi Data

### 15.1 Otorisasi

Setiap query/command domain memeriksa:

- Peran.
- Organisasi.
- Kepemilikan peserta.
- Penugasan dan masa berlakunya.
- Status akun.
- Status objek.
- Jenis tindakan.

Admin laporan tidak otomatis dapat membaca media atau mengubah skor. Pergantian Mentor tidak menghapus atribusi penilai lama.

### 15.2 Media

- Audio disimpan pada object storage privat.
- Database hanya menyimpan metadata dan `storage_key`.
- URL bertanda tangan berumur pendek dibuat setelah otorisasi.
- Video MVP disimpan sebagai tautan HTTPS, bukan blob.
- Server tidak melakukan fetch ke URL video sembarang.
- Retensi dan penghapusan mengikuti keputusan pengelola.

### 15.3 Data sensitif

- Rahasia autentikasi tidak masuk audit/log.
- Acuan jawaban tidak tersedia dalam query peserta.
- Ekspor riset memerlukan mandat, penghilangan identitas, dan audit.
- Rekaman tidak boleh digunakan untuk pelatihan AI tanpa keputusan dan dasar izin terpisah.

### 15.4 Row-Level Security

RLS dapat dipakai sebagai defense in depth, tetapi tidak menggantikan authorization pada service. Jika digunakan, `organization_id` dan `enrollment_id` yang diperlukan untuk kebijakan harus dapat ditelusuri secara efisien tanpa memperkenalkan duplikasi yang tidak terkontrol.

## 16. Data Store DFD ke Tabel

| Store | Isi logis | Tabel utama |
|---|---|---|
| D1 | Akun, peserta, penugasan | `users`, `role_grants`, `enrollments`, `assignments` |
| D2 | Kurikulum, kebijakan, kalender | `organizations`, `cohorts`, `policy_versions`, `curriculum_versions`, `parts`, `themes`, `theme_ranges`, `targets`, `deadline_changes` |
| D3 | Pembimbingan tema | `sessions`, `session_themes`, `assessment_records`, `theme_assessments`, `incidents` |
| D4 | Video, kelayakan, penilaian | `video_attempts`, `video_versions`, `eligibility_reviews`, `eligibility_checks`, `assessment_records`, `video_assessments`, `incidents` |
| D5 | Ujian | `question_versions`, `exams`, `exam_items`, `assessment_records`, `exam_assessments`, `incidents` |
| D6 | Media privat | `media_assets` dan object storage privat |
| D7 | Nilai dan sumber | `grade_snapshots`, `grade_sources` |
| D8 | Audit dan koreksi | `audit_events`, `correction_requests` |

`assessment_records` dan `incidents` digunakan bersama D3, D4, dan D5. Keduanya tetap satu tabel fisik, bukan diduplikasi per jenis penilaian.

## 17. Migrasi dan Seed Data

### 17.1 Urutan migrasi yang direkomendasikan

1. Ekstensi dan fungsi dasar UUID.
2. `organizations`, `users`, dan `role_grants`.
3. `policy_versions` dan `curriculum_versions`.
4. `cohorts`, `enrollments`, dan `assignments`.
5. `parts`, `themes`, `theme_ranges`, `targets`, dan `deadline_changes`.
6. `sessions` dan `session_themes`.
7. `assessment_records`, subtype tema, dan `incidents`.
8. Tabel video, kelayakan, media, dan subtype video.
9. Tabel soal, ujian, item, dan subtype ujian.
10. Tabel snapshot nilai, sumber, koreksi, dan audit.
11. Trigger/constraint lintas tabel, view/projection, dan indeks.

Migrasi produksi harus bersifat maju-kompatibel: tambahkan struktur baru sebelum menghapus struktur lama. Rollback aplikasi tidak dianggap otomatis mengembalikan skema database.

### 17.2 Seed data minimum

- Struktur fakultas dan jurusan contoh.
- Lima kode peran.
- Satu versi kebijakan draft dan satu versi yang disahkan untuk pengujian.
- Satu kurikulum dengan lima bagian dan 44 tema.
- Rentang ayat yang mendukung tema lintas surah.
- Checklist kelayakan video berversi.
- Data uji dua jurusan, dua angkatan, dan pengguna pada setiap peran/status.

Seed pengembangan/staging tidak boleh memakai data pribadi nyata.

## 18. Backup, Restore, dan Retensi

- Backup database harian dan sebelum migrasi.
- Salinan backup disimpan terpisah dan terenkripsi.
- Object storage memakai versioning atau backup setara.
- Restore diuji di lingkungan terisolasi sebelum pilot.
- Pemeriksaan restore mencakup jumlah peserta, penilaian, relasi, sampel audio, dan versi kebijakan.
- Usulan awal RPO 24 jam dan RTO 4 jam menunggu pengesahan.
- Retensi audit, hasil akademik, audio, dan tautan video ditetapkan sebelum data nyata digunakan.
- Hard delete hasil akademik final tidak diperbolehkan kecuali ada kebijakan dan proses hukum/operasional yang jelas; jejak minimal tetap harus dipertahankan sesuai aturan yang berlaku.

## 19. View dan Projection yang Direkomendasikan

View berikut dapat membantu query tanpa menjadikannya sumber kebenaran baru:

- `v_active_role_grants`
- `v_active_assignments`
- `v_effective_theme_assessments`
- `v_effective_video_assessments`
- `v_part_progress`
- `v_exam_eligibility`
- `v_latest_grade_snapshot`
- `v_mentor_queue`
- `v_department_progress`

Materialized view hanya digunakan jika kebutuhan performa terbukti. Refresh tidak boleh menyebabkan UI menampilkan status akademik lama sebagai hasil final tanpa penanda waktu.

## 20. Validasi dan Kasus Uji Database

### 20.1 Integritas referensial

- Semua foreign key menunjuk record yang tersedia.
- Tema lintas surah memiliki beberapa `theme_ranges` yang berurutan.
- Target tidak dapat menunjuk tema dari kurikulum lain.
- Sesi tidak dapat memuat tema dari dua bagian.
- Penilaian tidak dapat berpindah peserta atau objek akademik melalui koreksi.

### 20.2 Kesempatan dan versi

- Kesempatan tema hanya 1-5 dan tidak ganda pada permintaan bersamaan.
- Pengganti teknis video menambah versi media, bukan revisi akademik.
- Revisi akademik hanya 0-3 per siklus.
- Revisi 3 gagal membuka siklus berikut, revisi 0.
- Hasil lama tetap tersedia setelah koreksi.

### 20.3 Penilaian

- Skor kosong, 0, dan lebih dari 10 ditolak saat final sesuai kebijakan.
- Tepat satu subtype dimiliki setiap induk penilaian.
- Review Layak dan penilaian video selalu menunjuk versi yang sama.
- Tiga kesalahan tanpa audio tidak dapat difinalkan.
- Empat insiden dengan satu koreksi mandiri sah menghasilkan tiga kesalahan terhitung.
- Skor manual tidak mengubah aturan 0-3 Cukup dan 4+ Belum Cukup.

### 20.4 Nilai

- Uji batas keterlambatan hari 0, 1, 7, 8, 49, dan 50.
- Target belum jatuh tempo tidak bernilai 1 pada rekap sementara.
- K=10, M=10 tanpa ujian tidak menghasilkan Lulus.
- K=10, M=10, D=1 dengan ujian final menghasilkan N=6.40.
- Komponen kosong tetap `NULL` dan menghasilkan status belum lengkap.
- Koreksi tenggat/hasil membuat snapshot baru dan dapat ditelusuri.

### 20.5 Konkurensi

- Dua finalisasi bersamaan hanya menghasilkan satu hasil.
- Retry dengan kunci yang sama tidak menambah kesempatan.
- Kunci sama dengan payload berbeda ditolak.
- Konflik `row_version` menghasilkan respons konflik dan tidak menimpa data.
- Kegagalan di tengah transaksi tidak meninggalkan hasil parsial.

### 20.6 Keamanan

- Peserta tidak dapat membaca record peserta lain.
- Mentor tidak dapat membaca binaan di luar penugasan.
- Admin Jurusan tidak dapat membaca jurusan lain.
- Akun nonaktif dan penugasan kedaluwarsa ditolak.
- Acuan soal tidak muncul pada query/API peserta.
- URL media sementara hanya diberikan setelah otorisasi.

## 21. Observabilitas Database

Pantau sekurang-kurangnya:

- Waktu query p50/p95/p99.
- Query lambat dan sequential scan pada tabel besar.
- Deadlock dan lock wait pada finalisasi.
- Konflik versi dan retry idempotensi.
- Pertumbuhan `audit_events`, `incidents`, dan `grade_snapshots`.
- Kegagalan foreign key/check/unique constraint.
- Kapasitas database dan object storage.
- Status backup dan hasil restore terakhir.
- Lag pekerjaan outbox/background.

Log aplikasi menggunakan `request_id` untuk menghubungkan permintaan, transaksi, audit, dan pekerjaan latar tanpa menyimpan data sensitif.

## 22. Keputusan yang Harus Ditutup Sebelum Migration Final

| ID | Keputusan | Bagian schema yang terdampak |
|---|---|---|
| DB-01 | PostgreSQL atau database relasional lain | Tipe, trigger, RLS, indeks, dan tooling migrasi |
| DB-02 | Sumber dan agregasi M | `grade_sources`, `grade_snapshots`, policy rules |
| DB-03 | Jumlah/bobot soal, agregasi D, dan ujian ulang | `exam_items.weight`, `exam_assessments`, snapshot |
| DB-04 | Dukungan desimal dan pembulatan | Presisi `numeric` dan constraint skor/nilai |
| DB-05 | Tindak lanjut kesempatan tema kelima | Status/proses setelah `follow_up` |
| DB-06 | Detail koreksi mandiri dan kejadian berulang | Validasi `incidents` dan policy rules |
| DB-07 | Mandat koreksi dan perubahan tenggat | Authorization, `correction_requests`, `deadline_changes` |
| DB-08 | Retensi audio, video, audit, dan hasil | Lifecycle `media_assets` dan kebijakan arsip |
| DB-09 | Ukuran pilot, RPO/RTO, dan kapasitas | Indeks, backup, monitoring, dan sizing |

## 23. Definition of Done Database

Basis data siap untuk pilot apabila:

1. Seluruh migration dapat diterapkan dari database kosong dan diuji pada staging.
2. Seluruh 32 entitas domain, relasi, dan constraint utama tersedia.
3. Data kurikulum 44 tema dalam lima bagian tervalidasi.
4. Authorization service dapat menelusuri lingkup organisasi dan penugasan aktif.
5. Finalisasi tema, video, ujian, dan nilai bersifat atomik serta idempoten.
6. Riwayat koreksi, tenggat, kebijakan, dan snapshot tidak ditimpa.
7. Semua kasus uji integritas, konkurensi, nilai, dan akses lulus.
8. Backup dan restore database serta media telah dibuktikan.
9. Query layar inti memenuhi target performa yang disahkan.
10. Kamus data, migration, ERD aktual, dan OpenAPI menggunakan nama/aturan yang konsisten.

## 24. Keterlacakan ke Rancangan

Dokumen ini mempertahankan nama 32 entitas pada tujuh ERD sumber:

- ER01: identitas, angkatan, dan penugasan.
- ER02: kurikulum, kebijakan, dan target.
- ER03: sesi dan penilaian tema.
- ER04A: slot video, versi, dan kelayakan.
- ER04B: penilaian video dan audio.
- ER05: soal ujian dan penilaiannya.
- ER06: rekap, sumber nilai, koreksi, dan audit.

Pemetaan D1-D8 serta aturan transaksi mengikuti DFD konteks, Level 0, enam proses Level 1, dan dua proses Level 2 pada rancangan. Penambahan kolom operasional seperti timestamp, `row_version`, checksum, dan konteks audit merupakan rekomendasi implementasi yang tidak mengubah aturan akademik sumber.

