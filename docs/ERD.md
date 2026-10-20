# Entity Relationship Diagram - YAQin

## Aplikasi Pendampingan Hafalan Juz 30

| Atribut | Nilai |
|---|---|
| Produk | YAQin - Yakin, Amalin, Mutqin |
| Dokumen | ERD logis dan relasi data |
| Versi | 1.0 |
| Tanggal | 20 Oktober 2026 |
| Status | Baseline implementasi untuk ditinjau |
| Database | PostgreSQL |
| Jumlah entitas domain | 32 |
| Dokumen terkait | `docs/database.md`, `docs/API.md`, `docs/Arsitektur.md`, `docs/PRD-Aplikasi-Tahfidz-YAQin.md` |

> Dokumen ini memvisualisasikan model relasional YAQin. Diagram dibagi per domain agar dapat dibaca dan dirender dengan baik. `docs/database.md` tetap menjadi kamus kolom dan constraint terperinci; migration SQL menjadi spesifikasi fisik yang dapat dieksekusi.

---

## 1. Tujuan dan Ruang Lingkup

ERD ini mencakup:

1. Identitas, organisasi, peran, angkatan, kepesertaan, dan penugasan.
2. Kebijakan, kurikulum, lima bagian, 44 tema, serta rentang ayat.
3. Target, tenggat, sesi pembimbingan, dan penilaian tema.
4. Siklus/revisi video, versi media, kelayakan teknis, penilaian akademik, dan audio.
5. Soal, ujian, penilaian Dosen, snapshot nilai, koreksi, dan audit.

ERD tidak memaksakan keputusan akademik yang belum disahkan, khususnya agregasi M, agregasi D, pembulatan, ujian ulang, dan detail alur koreksi lanjutan.

## 2. Notasi

| Notasi | Makna |
|---|---|
| `PK` | Primary key |
| `FK` | Foreign key |
| `UK` | Unique key atau bagian dari unique constraint |
| `||` | Tepat satu |
| `o|` | Nol atau satu |
| `|{` | Satu atau lebih |
| `o{` | Nol atau lebih |

Catatan:

- Semua primary key domain menggunakan UUID.
- Kolom `row_version` digunakan pada aggregate yang memerlukan optimistic concurrency.
- Timestamp disimpan sebagai `timestamptz`; tanggal tenggat memakai `date`.
- Diagram menampilkan kolom domain utama. Kolom standar seperti `created_at`, `created_by`, dan `updated_at` ditambahkan sesuai pedoman pada `database.md`.
- Relasi audit ke objek domain disimpan sebagai `object_type` dan `object_reference`, sehingga bukan foreign key fisik.

## 3. Peta Relasi Global

Diagram berikut menunjukkan alur relasi utama tanpa seluruh atribut.

```mermaid
flowchart LR
  ORG[organizations] --> RG[role_grants]
  USR[users] --> RG
  ORG --> COH[cohorts]
  CUR[curriculum_versions] --> COH
  POL[policy_versions] --> COH
  CUR --> PART[parts]
  PART --> THEME[themes]
  THEME --> RANGE[theme_ranges]

  USR --> ENR[enrollments]
  COH --> ENR
  ENR --> ASN[assignments]
  USR --> ASN
  ENR --> TGT[targets]
  THEME --> TGT
  TGT --> DLC[deadline_changes]

  ENR --> SES[sessions]
  SES --> STH[session_themes]
  THEME --> STH

  ENR --> AR[assessment_records]
  AR --> INC[incidents]
  AR --> TA[theme_assessments]
  STH --> TA

  ENR --> VA[video_attempts]
  PART --> VA
  VA --> VV[video_versions]
  VV --> ER[eligibility_reviews]
  ER --> EC[eligibility_checks]
  AR --> VAS[video_assessments]
  VV --> VAS
  ER --> VAS
  MEDIA[media_assets] --> VAS

  ENR --> EX[exams]
  EX --> EI[exam_items]
  QV[question_versions] --> EI
  AR --> EA[exam_assessments]
  EI --> EA

  ENR --> GS[grade_snapshots]
  GS --> GSO[grade_sources]
  AR --> GSO
  AR --> CR[correction_requests]
  USR --> AUD[audit_events]
```

## 4. ERD Identitas dan Organisasi

```mermaid
erDiagram
  organizations {
    uuid id PK
    uuid parent_id FK "nullable"
    text kind
    text name
    text code "nullable"
    text status
  }

  users {
    uuid id PK
    text login_identifier UK
    text name
    text account_status
    text password_hash "nullable"
    timestamptz last_login_at "nullable"
  }

  role_grants {
    uuid id PK
    uuid user_id FK
    uuid organization_id FK
    text role
    timestamptz valid_from
    timestamptz valid_to "nullable"
  }

  organizations o|--o{ organizations : "parent of"
  users ||--o{ role_grants : "receives"
  organizations ||--o{ role_grants : "scopes"
```

Aturan relasi:

- Fakultas berada pada akar dan jurusan memiliki tepat satu fakultas induk dalam cakupan sistem.
- Rantai `parent_id` tidak boleh bersiklus.
- Satu pengguna dapat memiliki beberapa peran dan beberapa lingkup organisasi, selama interval mandat sah.
- Role grant tidak sama dengan assignment. Role grant memberi kapasitas peran; assignment mengikat petugas pada peserta tertentu.

## 5. ERD Kebijakan, Kurikulum, dan Program

```mermaid
erDiagram
  policy_versions {
    uuid id PK
    text version UK
    text status
    jsonb rules
    uuid approved_by FK "nullable"
    timestamptz approved_at "nullable"
    timestamptz effective_from "nullable"
  }

  curriculum_versions {
    uuid id PK
    text version UK
    text status
    text title
    timestamptz published_at "nullable"
  }

  cohorts {
    uuid id PK
    uuid organization_id FK
    uuid curriculum_version_id FK
    uuid policy_version_id FK
    text name
    date start_date
    date close_date "nullable"
    text status
  }

  enrollments {
    uuid id PK
    uuid user_id FK
    uuid cohort_id FK
    text nim_snapshot
    text status
    timestamptz joined_at
  }

  assignments {
    uuid id PK
    uuid enrollment_id FK
    uuid staff_id FK
    text role
    timestamptz valid_from
    timestamptz valid_to "nullable"
    text reason "nullable"
  }

  parts {
    uuid id PK
    uuid curriculum_version_id FK
    smallint sequence_no
    text title
  }

  themes {
    uuid id PK
    uuid part_id FK
    smallint sequence_no
    text title
    text description "nullable"
  }

  theme_ranges {
    uuid id PK
    uuid theme_id FK
    smallint sequence_no
    smallint surah_no
    smallint ayah_start
    smallint ayah_end
  }

  organizations {
    uuid id PK
  }

  users {
    uuid id PK
  }

  users o|--o{ policy_versions : "approves"
  organizations ||--o{ cohorts : "owns"
  curriculum_versions ||--o{ cohorts : "selected by"
  policy_versions ||--o{ cohorts : "governs"
  cohorts ||--o{ enrollments : "contains"
  users ||--o{ enrollments : "joins"
  enrollments ||--o{ assignments : "has history"
  users ||--o{ assignments : "staff member"
  curriculum_versions ||--|{ parts : "contains"
  parts ||--|{ themes : "contains"
  themes ||--|{ theme_ranges : "covers"
```

Constraint utama:

- `UNIQUE(users.id, cohorts.id)` diwujudkan sebagai `UNIQUE(user_id, cohort_id)` pada `enrollments`.
- `UNIQUE(curriculum_version_id, sequence_no)` pada `parts`.
- `parts.sequence_no` berada pada 1-5.
- `UNIQUE(part_id, sequence_no)` pada `themes`.
- `UNIQUE(theme_id, sequence_no)` pada `theme_ranges`.
- Versi kurikulum pilot yang diterbitkan harus memiliki 5 bagian dan total 44 tema dengan distribusi 10, 8, 6, 5, dan 15.
- Kurikulum dan kebijakan yang sudah digunakan tidak ditimpa; perubahan menghasilkan versi baru.
- Assignment lama tetap tersimpan ketika Mentor atau Dosen diganti.

## 6. ERD Kalender dan Tenggat

```mermaid
erDiagram
  enrollments {
    uuid id PK
    uuid cohort_id FK
    uuid user_id FK
  }

  themes {
    uuid id PK
    uuid part_id FK
  }

  targets {
    uuid id PK
    uuid enrollment_id FK
    uuid theme_id FK
    date initial_due_date
    date effective_due_date
    text status
  }

  deadline_changes {
    uuid id PK
    uuid target_id FK
    uuid requested_by FK
    uuid approved_by FK "nullable"
    date old_date
    date new_date
    text reason
    text status
    timestamptz decided_at "nullable"
  }

  users {
    uuid id PK
  }

  enrollments ||--o{ targets : "receives"
  themes ||--o{ targets : "scheduled as"
  targets ||--o{ deadline_changes : "has change history"
  users ||--o{ deadline_changes : "requests"
  users o|--o{ deadline_changes : "approves"
```

Aturan relasi:

- Satu peserta memiliki paling banyak satu target untuk satu tema: `UNIQUE(enrollment_id, theme_id)`.
- Tema target harus berasal dari versi kurikulum milik cohort peserta.
- `initial_due_date` tidak berubah.
- `effective_due_date` hanya berubah bersama approval `deadline_changes` dalam satu transaksi.
- Nilai lama, nilai baru, pemohon, penyetuju, dan alasan selalu dipertahankan.

## 7. ERD Pembimbingan dan Penilaian Tema

```mermaid
erDiagram
  users {
    uuid id PK
  }

  enrollments {
    uuid id PK
  }

  parts {
    uuid id PK
  }

  themes {
    uuid id PK
    uuid part_id FK
  }

  policy_versions {
    uuid id PK
  }

  sessions {
    uuid id PK
    uuid enrollment_id FK
    uuid part_id FK
    uuid mentor_id FK
    timestamptz scheduled_at "nullable"
    timestamptz actual_at "nullable"
    text mode
    text status
    text notes "nullable"
  }

  session_themes {
    uuid id PK
    uuid session_id FK
    uuid theme_id FK
  }

  assessment_records {
    uuid id PK
    uuid enrollment_id FK
    uuid assessor_id FK
    uuid policy_version_id FK
    text kind
    numeric manual_score "nullable"
    text status
    timestamptz finalized_at "nullable"
    bigint row_version
  }

  incidents {
    uuid id PK
    uuid assessment_id FK
    text category
    text location
    text assistance_type
    boolean self_corrected
    boolean counted
    text count_reason "nullable"
    text notes "nullable"
  }

  theme_assessments {
    uuid id PK, FK
    uuid session_theme_id FK
    smallint attempt_no
    text outcome
    text notes "nullable"
  }

  enrollments ||--o{ sessions : "requests"
  parts ||--o{ sessions : "scopes"
  users ||--o{ sessions : "mentors"
  sessions ||--|{ session_themes : "includes"
  themes ||--o{ session_themes : "selected in"

  enrollments ||--o{ assessment_records : "is assessed"
  users ||--o{ assessment_records : "assesses"
  policy_versions ||--o{ assessment_records : "governs"
  assessment_records ||--o{ incidents : "documents"
  assessment_records ||--o| theme_assessments : "subtype theme"
  session_themes ||--o{ theme_assessments : "is assessed by"
```

Aturan relasi:

- `UNIQUE(session_id, theme_id)` pada `session_themes`.
- Satu sesi memiliki minimal satu tema dan seluruh tema berada pada `sessions.part_id`.
- `actual_at`, bukan `scheduled_at`, menjadi kandidat tanggal setoran pertama.
- Nomor kesempatan dialokasikan server per peserta-tema pada rentang 1-5.
- Penilaian kelima yang belum Cukup menghasilkan `follow_up`; sistem tidak membuat kesempatan keenam.
- Koreksi membuat assessment pengganti dan tidak menaikkan `attempt_no`.

## 8. Pola Supertype Penilaian

Semua penilaian memiliki induk yang sama. Setiap `assessment_records` harus memiliki tepat satu subtype sesuai `kind`.

```mermaid
erDiagram
  assessment_records {
    uuid id PK
    uuid enrollment_id FK
    uuid assessor_id FK
    uuid policy_version_id FK
    text kind "theme, video, exam"
    numeric manual_score "nullable on draft"
    text status
    timestamptz finalized_at "nullable"
    bigint row_version
  }

  theme_assessments {
    uuid id PK, FK
    uuid session_theme_id FK
    smallint attempt_no
    text outcome
  }

  video_assessments {
    uuid id PK, FK
    uuid video_version_id FK
    uuid eligibility_review_id FK
    uuid audio_asset_id FK "nullable on draft"
    integer counted_errors
    text outcome
  }

  exam_assessments {
    uuid id PK, FK
    uuid exam_item_id FK
    text notes "nullable"
  }

  incidents {
    uuid id PK
    uuid assessment_id FK
    text category
    boolean counted
  }

  assessment_records ||--o| theme_assessments : "kind theme"
  assessment_records ||--o| video_assessments : "kind video"
  assessment_records ||--o| exam_assessments : "kind exam"
  assessment_records ||--o{ incidents : "has evidence"
```

Mermaid hanya dapat menunjukkan bahwa setiap subtype opsional terhadap induk. Constraint tambahan wajib menjamin XOR berikut:

```text
count(theme_assessments, video_assessments, exam_assessments) = 1
assessment_records.kind = jenis subtype yang tersedia
```

Constraint tersebut diterapkan melalui service finalisasi transaksional dan deferred constraint trigger. Record final tidak diedit in-place.

## 9. ERD Video, Kelayakan, dan Media

```mermaid
erDiagram
  users {
    uuid id PK
  }

  enrollments {
    uuid id PK
  }

  parts {
    uuid id PK
  }

  assessment_records {
    uuid id PK
  }

  video_attempts {
    uuid id PK
    uuid enrollment_id FK
    uuid part_id FK
    integer cycle_no
    smallint revision_no
    text status
  }

  video_versions {
    uuid id PK
    uuid attempt_id FK
    integer version_no
    text video_url
    date recorded_date
    timestamptz submitted_at
    text status
  }

  eligibility_reviews {
    uuid id PK
    uuid video_version_id FK
    uuid reviewer_id FK
    text checklist_version
    text decision
    text reason "nullable"
    text status
    timestamptz finalized_at "nullable"
  }

  eligibility_checks {
    uuid id PK
    uuid review_id FK
    text criterion_code
    boolean passed
    text notes "nullable"
  }

  media_assets {
    uuid id PK
    uuid owner_id FK
    text storage_key UK
    text mime_type
    bigint size_bytes
    text checksum
    text status
    timestamptz created_at
  }

  video_assessments {
    uuid id PK, FK
    uuid video_version_id FK
    uuid eligibility_review_id FK
    uuid audio_asset_id FK "nullable on draft"
    integer counted_errors
    text outcome
  }

  enrollments ||--o{ video_attempts : "submits"
  parts ||--o{ video_attempts : "is assessed by"
  video_attempts ||--|{ video_versions : "has media versions"
  video_versions ||--o{ eligibility_reviews : "is reviewed"
  users ||--o{ eligibility_reviews : "reviews"
  eligibility_reviews ||--|{ eligibility_checks : "contains"
  assessment_records ||--o| video_assessments : "subtype video"
  video_versions ||--o{ video_assessments : "is academically assessed"
  eligibility_reviews ||--o{ video_assessments : "authorizes"
  users ||--o{ media_assets : "owns"
  media_assets o|--o{ video_assessments : "feedback audio"
```

Constraint utama:

- `UNIQUE(enrollment_id, part_id, cycle_no, revision_no)` pada `video_attempts`.
- `revision_no` berada pada 0-3; `cycle_no` dimulai dari 1.
- `UNIQUE(attempt_id, version_no)` pada `video_versions`.
- Penggantian teknis menambah `version_no`, bukan `revision_no`.
- `UNIQUE(review_id, criterion_code)` pada `eligibility_checks`.
- Review yang digunakan penilaian harus final, `eligible`, dan menunjuk versi video yang sama.
- `counted_errors` sama dengan jumlah `incidents.counted = true` pada assessment induk.
- Baseline kebijakan: 0-3 kesalahan menghasilkan `enough`, 4 atau lebih menghasilkan `not_enough`.
- Skor manual pada induk tidak mengubah status video.
- Audio boleh kosong pada draft, tetapi wajib berstatus `available` ketika final.

## 10. ERD Soal dan Ujian

```mermaid
erDiagram
  users {
    uuid id PK
  }

  enrollments {
    uuid id PK
  }

  policy_versions {
    uuid id PK
  }

  assessment_records {
    uuid id PK
  }

  question_versions {
    uuid id PK
    uuid author_id FK "nullable for system"
    text source
    text kind
    text stimulus
    jsonb answer_reference
    jsonb scope
    integer version_no
    text status
  }

  exams {
    uuid id PK
    uuid enrollment_id FK
    uuid lecturer_id FK
    uuid policy_version_id FK
    timestamptz actual_at "nullable"
    text status
    bigint row_version
    timestamptz finalized_at "nullable"
  }

  exam_items {
    uuid id PK
    uuid exam_id FK
    uuid question_version_id FK
    integer sequence_no
    jsonb question_snapshot
    numeric weight "nullable"
  }

  exam_assessments {
    uuid id PK, FK
    uuid exam_item_id FK
    text notes "nullable"
  }

  users o|--o{ question_versions : "authors"
  enrollments ||--o{ exams : "takes"
  users ||--o{ exams : "examines"
  policy_versions ||--o{ exams : "governs"
  exams ||--|{ exam_items : "contains"
  question_versions ||--o{ exam_items : "snapshotted in"
  assessment_records ||--o| exam_assessments : "subtype exam"
  exam_items ||--o{ exam_assessments : "is assessed by"
```

Constraint utama:

- Ujian hanya dibuat untuk enrollment dengan lima bagian Cukup.
- Dosen memiliki assignment aktif kepada peserta.
- `UNIQUE(exam_id, sequence_no)` pada `exam_items`.
- `question_snapshot` tidak berubah jika bank soal mendapat versi baru.
- `answer_reference` dan snapshot acuan hanya dapat dibaca penguji berwenang.
- Bobot item tetap `NULL` sampai kebijakan bobot disahkan.
- Ujian final memiliki paket dan penilaian lengkap sesuai policy version.

## 11. ERD Nilai, Koreksi, dan Audit

```mermaid
erDiagram
  users {
    uuid id PK
  }

  enrollments {
    uuid id PK
  }

  policy_versions {
    uuid id PK
  }

  assessment_records {
    uuid id PK
    uuid enrollment_id FK
    text kind
    text status
  }

  grade_snapshots {
    uuid id PK
    uuid enrollment_id FK
    uuid policy_version_id FK
    numeric k_value "nullable"
    numeric m_value "nullable"
    numeric d_value "nullable"
    numeric n_value "nullable"
    text status
    jsonb source_context
    timestamptz calculated_at
    uuid supersedes_id FK "nullable"
  }

  grade_sources {
    uuid id PK
    uuid grade_snapshot_id FK
    uuid assessment_id FK
    text component
    numeric contribution "nullable"
  }

  correction_requests {
    uuid id PK
    uuid original_assessment_id FK
    uuid replacement_assessment_id FK "nullable"
    uuid requested_by FK
    uuid approved_by FK "nullable"
    text reason
    text status
    timestamptz decided_at "nullable"
  }

  audit_events {
    uuid id PK
    uuid actor_id FK "nullable for system"
    text action
    text object_type
    text object_reference
    uuid request_id "nullable"
    jsonb before_data "nullable"
    jsonb after_data "nullable"
    timestamptz occurred_at
  }

  enrollments ||--o{ grade_snapshots : "has history"
  policy_versions ||--o{ grade_snapshots : "governs"
  grade_snapshots o|--o| grade_snapshots : "supersedes"
  grade_snapshots ||--o{ grade_sources : "uses"
  assessment_records ||--o{ grade_sources : "contributes to"

  assessment_records ||--o{ correction_requests : "original"
  assessment_records o|--o{ correction_requests : "replacement"
  users ||--o{ correction_requests : "requests"
  users o|--o{ correction_requests : "approves"
  users o|--o{ audit_events : "acts in"
```

Catatan penting:

- `supersedes_id` membentuk rantai snapshot yang tidak boleh bersiklus.
- `UNIQUE(grade_snapshot_id, assessment_id, component)` pada `grade_sources`.
- Sumber M/D hanya berasal dari assessment final, efektif, dan milik enrollment yang sama.
- Konteks K disimpan pada `grade_snapshots.source_context` karena bukan satu assessment tunggal.
- M dan D dapat `NULL`; N hanya dihitung bila K/M/D lengkap dan ujian final tersedia.
- Koreksi tidak mengubah hasil asli. `replacement_assessment_id` menunjuk record baru setelah koreksi diterapkan.
- Jika koreksi mencabut prasyarat, snapshot baru berstatus `needs_review`.
- `audit_events.object_reference` adalah relasi logis ke berbagai aggregate dan sengaja bukan FK polymorphic.

## 12. Daftar 32 Entitas Domain

| No | Entitas | Aggregate/domain | Parent utama |
|---:|---|---|---|
| 1 | `organizations` | Identitas | Self-reference opsional |
| 2 | `users` | Identitas | - |
| 3 | `role_grants` | Identitas | `users`, `organizations` |
| 4 | `policy_versions` | Kebijakan | `users` sebagai approver opsional |
| 5 | `curriculum_versions` | Kurikulum | - |
| 6 | `cohorts` | Program | `organizations`, versi kurikulum/kebijakan |
| 7 | `enrollments` | Program | `users`, `cohorts` |
| 8 | `assignments` | Program | `enrollments`, `users` |
| 9 | `parts` | Kurikulum | `curriculum_versions` |
| 10 | `themes` | Kurikulum | `parts` |
| 11 | `theme_ranges` | Kurikulum | `themes` |
| 12 | `targets` | Kalender | `enrollments`, `themes` |
| 13 | `deadline_changes` | Kalender | `targets`, `users` |
| 14 | `sessions` | Pembimbingan | `enrollments`, `parts`, `users` |
| 15 | `session_themes` | Pembimbingan | `sessions`, `themes` |
| 16 | `assessment_records` | Penilaian | `enrollments`, `users`, `policy_versions` |
| 17 | `incidents` | Penilaian | `assessment_records` |
| 18 | `theme_assessments` | Penilaian tema | `assessment_records`, `session_themes` |
| 19 | `video_attempts` | Video | `enrollments`, `parts` |
| 20 | `video_versions` | Video | `video_attempts` |
| 21 | `eligibility_reviews` | Video | `video_versions`, `users` |
| 22 | `eligibility_checks` | Video | `eligibility_reviews` |
| 23 | `media_assets` | Media | `users` |
| 24 | `video_assessments` | Penilaian video | `assessment_records`, video/review/media |
| 25 | `question_versions` | Ujian | `users` sebagai author opsional |
| 26 | `exams` | Ujian | `enrollments`, `users`, `policy_versions` |
| 27 | `exam_items` | Ujian | `exams`, `question_versions` |
| 28 | `exam_assessments` | Penilaian ujian | `assessment_records`, `exam_items` |
| 29 | `grade_snapshots` | Nilai | `enrollments`, `policy_versions`, self-reference |
| 30 | `grade_sources` | Nilai | `grade_snapshots`, `assessment_records` |
| 31 | `correction_requests` | Koreksi | assessment lama/baru, `users` |
| 32 | `audit_events` | Audit | `users`; objek memakai referensi logis |

## 13. Foreign Key dan Kebijakan Delete

Baseline PostgreSQL yang disarankan:

| Jenis relasi | `ON DELETE` | Alasan |
|---|---|---|
| Data master yang sudah dipakai | `RESTRICT` | Menjaga sejarah dan keterlacakan |
| User ke role/assignment/assessment | `RESTRICT` | Akun dinonaktifkan, bukan dihapus |
| Cohort ke enrollment | `RESTRICT` | Kepesertaan historis harus tetap ada |
| Curriculum ke part/theme/range | `RESTRICT` setelah publish | Versi terbit immutable |
| Session ke session theme | `RESTRICT` | Sesi historis tidak dihapus |
| Assessment ke subtype/incident | `RESTRICT` | Final record immutable |
| Video attempt ke version/review | `RESTRICT` | Versi media dan keputusan harus terlacak |
| Exam ke item/assessment | `RESTRICT` | Paket dan hasil ujian historis |
| Grade snapshot ke source | `RESTRICT` | Snapshot harus dapat direkonstruksi |
| Draft yang belum direferensikan | Diputuskan per use case | Lebih aman memakai status/cancel daripada hard delete |

Hard delete tidak digunakan untuk hasil final. Penonaktifan, `valid_to`, status, koreksi, dan supersession menjadi mekanisme utama.

## 14. Constraint Lintas Entitas

Constraint berikut tidak cukup diwakili oleh garis ERD dan wajib diterapkan pada domain service, transaksi, atau deferred trigger:

1. Tema target berasal dari curriculum version cohort peserta.
2. Bagian pada sesi dan video berasal dari curriculum version yang sama.
3. Seluruh tema dalam satu sesi berasal dari `sessions.part_id`.
4. Enrollment konsisten pada sesi, video, ujian, assessment, dan snapshot.
5. Assessor memiliki role grant serta assignment aktif pada waktu tindakan.
6. Satu `assessment_records` memiliki tepat satu subtype yang sesuai dengan `kind`.
7. Eligibility review untuk video assessment final, Layak, dan menunjuk video version yang sama.
8. Audio feedback final berstatus `available`.
9. `counted_errors` sama dengan jumlah incident terhitung.
10. Attempt tema dialokasikan per peserta-tema dan tidak lebih dari lima.
11. Siklus dan revisi video dialokasikan server dari hasil efektif.
12. Hanya hasil final dan efektif yang memperbarui progres.
13. Grade source final, efektif, dan milik enrollment snapshot yang sama.
14. Rantai correction dan supersession tidak bersiklus.
15. Kelulusan memerlukan lima bagian Cukup, ujian final, serta K/M/D lengkap.

## 15. Aggregate dan Batas Transaksi

| Aggregate | Root | Entitas yang berubah atomik |
|---|---|---|
| Penilaian tema | `assessment_records` | `theme_assessments`, `incidents`, progres terkait, audit, outbox |
| Kelayakan video | `eligibility_reviews` | `eligibility_checks`, status video, audit, outbox |
| Penilaian video | `assessment_records` | `video_assessments`, `incidents`, progres bagian, audit, outbox |
| Ujian | `exams` | `exam_items`, `assessment_records`, `exam_assessments`, snapshot bila siap, audit, outbox |
| Tenggat | `deadline_changes` | `targets.effective_due_date`, audit, outbox |
| Nilai | `grade_snapshots` | `grade_sources`, source context, audit, outbox |
| Koreksi | `correction_requests` | replacement assessment, status lama, progres/snapshot terdampak, audit, outbox |

Row lock disarankan pada:

- peserta-tema saat mengalokasikan `attempt_no`;
- peserta-bagian saat mengalokasikan `cycle_no` dan `revision_no`;
- ujian saat finalisasi;
- peserta saat menerbitkan snapshot nilai.

## 16. Tabel Teknis di Luar 32 Entitas Domain

Arsitektur menggunakan beberapa tabel operasional. Tabel ini bukan bagian dari ERD domain sumber, tetapi diperlukan untuk keandalan implementasi.

```mermaid
erDiagram
  users {
    uuid id PK
  }

  api_idempotency {
    uuid id PK
    uuid actor_id FK
    text method
    text normalized_path
    text idempotency_key
    text request_hash
    text status
    integer response_status "nullable"
    jsonb response_body "nullable"
    timestamptz expires_at
  }

  outbox_events {
    uuid id PK
    text event_type
    text aggregate_type
    uuid aggregate_id
    jsonb payload
    timestamptz created_at
    timestamptz available_at
    timestamptz processed_at "nullable"
    integer attempt_count
    text last_error "nullable"
    timestamptz locked_at "nullable"
  }

  job_runs {
    uuid id PK
    uuid requested_by FK
    text job_type
    text status
    jsonb parameters
    jsonb result "nullable"
    timestamptz created_at
    timestamptz completed_at "nullable"
  }

  users ||--o{ api_idempotency : "issues commands"
  users ||--o{ job_runs : "requests"
```

`outbox_events.aggregate_id` adalah referensi logis karena event dapat berasal dari berbagai aggregate. Event dibuat pada transaksi yang sama dengan perubahan domain.

## 17. Urutan Migration yang Disarankan

1. Extension UUID dan schema `app`, `ops`, serta `alembic` bila digunakan.
2. `organizations`, `users`.
3. `role_grants`, `policy_versions`, `curriculum_versions`.
4. `cohorts`, `enrollments`, `assignments`.
5. `parts`, `themes`, `theme_ranges`.
6. `targets`, `deadline_changes`.
7. `sessions`, `session_themes`.
8. `assessment_records`, lalu `incidents`.
9. `theme_assessments`.
10. `video_attempts`, `video_versions`, `eligibility_reviews`, `eligibility_checks`, `media_assets`, `video_assessments`.
11. `question_versions`, `exams`, `exam_items`, `exam_assessments`.
12. `grade_snapshots`, `grade_sources`.
13. `correction_requests`, `audit_events`.
14. Tabel teknis `api_idempotency`, `outbox_events`, dan `job_runs`.
15. Deferred constraint trigger, partial unique index, view, dan seed data.

## 18. Indeks Relasi Utama

Selain indeks otomatis pada PK dan unique constraint:

| Entitas | Indeks |
|---|---|
| `role_grants` | `(user_id, role, organization_id, valid_to)` |
| `enrollments` | `(cohort_id, status)` |
| `assignments` | `(enrollment_id, role, valid_to)` |
| `targets` | `(enrollment_id, effective_due_date, status)` |
| `sessions` | `(mentor_id, scheduled_at, status)`, `(enrollment_id, actual_at)` |
| `assessment_records` | `(enrollment_id, kind, status, finalized_at)` |
| `incidents` | `(assessment_id, counted)` |
| `video_attempts` | `(enrollment_id, part_id, status)` |
| `video_versions` | `(attempt_id, version_no DESC)` |
| `eligibility_reviews` | `(video_version_id, status, finalized_at)` |
| `exams` | `(lecturer_id, status, actual_at)` |
| `grade_snapshots` | `(enrollment_id, calculated_at DESC)` |
| `correction_requests` | `(original_assessment_id, status)` |
| `audit_events` | `(object_type, object_reference, occurred_at DESC)` |

## 19. Validasi ERD

ERD dianggap konsisten jika pengujian berikut lulus:

- Seluruh foreign key menunjuk record yang valid.
- Tidak ada organisasi, correction chain, atau snapshot chain yang bersiklus.
- Target tidak dapat memakai tema dari curriculum version lain.
- Sesi tidak dapat berisi tema lintas bagian.
- Tepat satu subtype tersedia untuk setiap assessment.
- Peserta pada assessment sama dengan peserta pada objek akademik.
- Eligibility review dan video assessment menunjuk video version yang sama.
- Attempt tema tidak ganda pada request bersamaan.
- Revisi akademik video tidak berubah karena penggantian teknis.
- Snapshot nilai hanya memakai assessment final dan efektif.
- Record final, snapshot, dan versi kebijakan lama tidak ditimpa.
- Audit tidak menyimpan secret atau isi media.

## 20. Definition of Done ERD

ERD siap diturunkan menjadi migration ketika:

- Seluruh 32 entitas, PK, FK, cardinality, dan self-reference telah ditinjau.
- Constraint lintas tabel memiliki lokasi implementasi yang jelas.
- Delete policy dan retensi data telah disahkan.
- Enum/status telah dipetakan ke check constraint atau reference table.
- Partial unique index untuk mandat/assignment aktif telah dirancang.
- Deferred trigger untuk subtype assessment dan rantai historis telah diuji.
- Keputusan akademik yang masih terbuka tidak memiliki default tersembunyi.
- Migration dapat dijalankan dari database kosong dan di-rollback sesuai kebijakan.
- Seed data kurikulum dan policy version tervalidasi.
- Diagram, kamus database, API, dan model ORM menggunakan nama yang konsisten.

---

Dokumen ini adalah representasi logis. Implementasi fisik final harus diverifikasi melalui migration PostgreSQL, constraint test, dan pemeriksaan bahwa OpenAPI tidak mengekspos field privat atau relasi di luar lingkup pengguna.
