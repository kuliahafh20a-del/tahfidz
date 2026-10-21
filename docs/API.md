# API Specification - YAQin

## FastAPI REST API untuk Aplikasi Pendampingan Hafalan Juz 30

| Atribut | Nilai |
|---|---|
| Produk | YAQin - Yakin, Amalin, Mutqin |
| Dokumen | Kontrak REST API |
| Versi dokumen | 1.0 |
| Versi API | v1 |
| Tanggal | 20 Oktober 2026 |
| Status | Baseline implementasi untuk ditinjau |
| Backend | FastAPI |
| Format | JSON UTF-8 melalui HTTPS |
| Sumber kebenaran kontrak | OpenAPI yang dihasilkan FastAPI |
| Dokumen terkait | `docs/PRD-Aplikasi-Tahfidz-YAQin.md`, `docs/database.md`, `docs/Arsitektur.md`, `docs/design.md` |

> Dokumen ini mendefinisikan kontrak awal API YAQin. Aturan akademik yang belum disahkan tetap menjadi keputusan terbuka dan tidak boleh diwujudkan sebagai default tersembunyi dalam endpoint, schema, atau frontend.

---

## 1. Tujuan

API YAQin harus:

1. Menjadi satu-satunya pintu untuk menjalankan aturan bisnis dan akademik.
2. Melayani Next.js pada MVP dan dapat digunakan klien Android pada tahap berikutnya.
3. Membatasi akses berdasarkan akun, peran, organisasi, kepemilikan, penugasan, masa berlaku, dan status objek.
4. Menjamin finalisasi akademik aman terhadap klik ganda, retry, timeout, dan perubahan bersamaan.
5. Memisahkan draft, finalisasi, koreksi, dan data historis.
6. Tidak mengubah nilai yang belum tersedia menjadi `0` atau nilai buatan lain.
7. Menyediakan OpenAPI yang cukup stabil untuk menghasilkan client TypeScript.

## 2. Batas API MVP

- API berbasis REST JSON dengan prefix `/api/v1`.
- Autentikasi web menggunakan session cookie. Token perangkat Android belum termasuk MVP.
- Video disimpan sebagai tautan HTTPS dari host yang diizinkan, bukan diunggah ke PostgreSQL.
- Audio Mentor disimpan di object storage privat melalui alur upload bertanda tangan.
- Finalisasi akademik tidak didukung secara offline.
- Ekspor, notifikasi, dan pemrosesan media dapat berjalan asinkron melalui worker.
- Agregasi M, agregasi D, pembulatan, ujian ulang, dan koreksi lanjutan hanya aktif setelah kebijakannya disahkan.

## 3. URL dan Versi

### 3.1 Base URL

```text
Development: http://localhost/api/v1
Staging:     https://staging.example.ac.id/api/v1
Production:  https://yaqin.example.ac.id/api/v1
```

Hostname final ditentukan saat deployment. Browser memakai satu origin melalui reverse proxy:

- `/` dan `/_next/*` menuju Next.js.
- `/api/v1/*` menuju FastAPI.
- `/health/live` dan `/health/ready` menuju FastAPI tanpa prefix versi.

### 3.2 Kebijakan versi

- Perubahan kompatibel ditambahkan ke `/api/v1`.
- Field respons baru boleh ditambahkan dan harus diabaikan oleh klien lama.
- Field tidak dihapus atau diubah maknanya selama v1 aktif.
- Breaking change membutuhkan `/api/v2` atau masa transisi yang disepakati.
- Status domain memakai kode stabil berbahasa Inggris; label Bahasa Indonesia menjadi tanggung jawab presentation layer.

## 4. Konvensi Umum

### 4.1 Header

| Header | Arah | Wajib | Keterangan |
|---|---|---:|---|
| `Content-Type: application/json` | Request | Ya untuk body JSON | Encoding UTF-8 |
| `Accept: application/json` | Request | Disarankan | Format respons |
| `X-Request-ID` | Keduanya | Disarankan | UUID dari klien atau dibuat server |
| `X-CSRF-Token` | Request mutasi web | Ya | Proteksi CSRF untuk session cookie |
| `Idempotency-Key` | Command kritis | Ya | UUID unik per operasi logis |
| `Retry-After` | Response 429/503 | Jika relevan | Waktu tunggu dalam detik |
| `Cache-Control: no-store` | Response sensitif | Ya | Identitas, nilai, antrean, media, penilaian |

`Idempotency-Key` tidak boleh digunakan ulang untuk operasi yang berbeda. Kunci diikat pada aktor, method, normalized path, dan hash payload.

### 4.2 Identitas dan waktu

- Semua ID publik memakai UUID dalam bentuk string.
- Timestamp memakai RFC 3339 dengan offset, contoh `2026-10-20T14:30:00+07:00`.
- Tanggal tanpa waktu memakai ISO 8601, contoh `2026-10-20`.
- Server menyimpan waktu sebagai `timestamptz` dan menghitung hari kalender pada zona `Asia/Jakarta`.
- Nilai desimal dikirim sebagai JSON number, tetapi server menghitung dengan tipe desimal, bukan floating point biner.

### 4.3 Penamaan field

- Field JSON menggunakan `snake_case`.
- Nilai enum menggunakan huruf kecil dan underscore.
- Nilai yang belum tersedia dikirim sebagai `null`, bukan `0`, string kosong, atau field palsu.
- Field rahasia, hash, token internal, dan object storage key mentah tidak pernah dikirim ke klien.

### 4.4 Bentuk respons berhasil

```json
{
  "data": {},
  "version": 7,
  "request_id": "8f5e2d79-9dc1-453d-b353-626c9fc8d596"
}
```

Aturan:

- `data` berisi resource, command result, atau collection.
- `version` berisi `row_version` resource utama.
- Pada collection atau operasi tanpa resource berversi, `version` bernilai `null`.
- `request_id` juga dikirim melalui header `X-Request-ID`.

### 4.5 Bentuk respons gagal

```json
{
  "code": "ASSESSMENT_VERSION_CONFLICT",
  "message": "Data telah berubah. Muat ulang sebelum memfinalkan.",
  "field_errors": {
    "expected_version": ["Versi yang dikirim tidak lagi berlaku."]
  },
  "details": {
    "current_version": 8
  },
  "request_id": "8f5e2d79-9dc1-453d-b353-626c9fc8d596"
}
```

`details` hanya memuat informasi yang aman dan dapat ditindaklanjuti. Stack trace, SQL, token, URL media bertanda tangan, dan data pengguna lain tidak boleh muncul.

## 5. Status HTTP

| Status | Penggunaan |
|---:|---|
| 200 | Pembacaan atau command berhasil |
| 201 | Resource berhasil dibuat |
| 202 | Pekerjaan asinkron diterima |
| 400 | Request tidak dapat diproses karena format/protokol |
| 401 | Session hilang, kedaluwarsa, atau tidak sah |
| 403 | Aktor tidak memiliki kewenangan |
| 404 | Resource tidak ditemukan atau berada di luar lingkup aktor |
| 409 | Konflik versi, status, prasyarat, duplikasi, atau idempotensi |
| 413 | Lampiran melampaui batas |
| 415 | Media type tidak didukung |
| 422 | Field atau kombinasi input tidak valid |
| 429 | Rate limit terlampaui |
| 500 | Kegagalan internal yang tidak diharapkan |
| 503 | Dependensi kritis belum siap atau sedang dipulihkan |

API memakai 404 untuk resource di luar lingkup ketika keberadaan resource tidak boleh dibocorkan.

## 6. Kode Error Standar

| Code | HTTP | Makna |
|---|---:|---|
| `AUTHENTICATION_REQUIRED` | 401 | Session tidak tersedia |
| `SESSION_EXPIRED` | 401 | Session kedaluwarsa |
| `INVALID_CREDENTIALS` | 401 | Login gagal tanpa membocorkan akun |
| `CSRF_TOKEN_INVALID` | 403 | Token CSRF tidak sah |
| `ACCESS_DENIED` | 403 | Aktor tidak berwenang |
| `RESOURCE_NOT_FOUND` | 404 | Resource tidak tersedia dalam lingkup |
| `VALIDATION_ERROR` | 422 | Input tidak valid |
| `VERSION_CONFLICT` | 409 | `expected_version` tidak sama dengan versi server |
| `INVALID_STATE_TRANSITION` | 409 | Transisi status tidak diizinkan |
| `PREREQUISITE_NOT_MET` | 409 | Prasyarat domain belum terpenuhi |
| `DUPLICATE_RESOURCE` | 409 | Melanggar keunikan bisnis |
| `IDEMPOTENCY_KEY_REQUIRED` | 400 | Command kritis tanpa kunci |
| `IDEMPOTENCY_KEY_REUSED` | 409 | Kunci sama dipakai dengan payload berbeda |
| `POLICY_NOT_APPROVED` | 409 | Operasi bergantung pada kebijakan terbuka |
| `MEDIA_NOT_AVAILABLE` | 409 | Media belum selesai, gagal, atau dikarantina |
| `RATE_LIMITED` | 429 | Terlalu banyak request |
| `INTERNAL_ERROR` | 500 | Error internal generik |
| `SERVICE_UNAVAILABLE` | 503 | Service belum siap |

Modul boleh menambahkan code yang lebih spesifik, misalnya `VIDEO_NOT_ELIGIBLE` atau `EXAM_NOT_ELIGIBLE`, selama HTTP status dan bentuk error tetap konsisten.

## 7. Pagination, Filter, Sort, dan Search

### 7.1 Cursor pagination

Endpoint antrean dan riwayat yang berubah cepat menggunakan cursor:

```http
GET /api/v1/mentor/queue?limit=25&cursor=eyJ...
```

```json
{
  "data": {
    "items": [],
    "page": {
      "next_cursor": "eyJ...",
      "has_more": true
    }
  },
  "version": null,
  "request_id": "uuid"
}
```

Aturan:

- Default `limit` adalah 25.
- Maksimum `limit` adalah 100.
- Cursor bersifat opaque dan tidak boleh dibentuk oleh klien.
- Urutan selalu memiliki tie-breaker stabil, biasanya `created_at DESC, id DESC`.

### 7.2 Filter dan sort

- Filter memakai query parameter eksplisit, misalnya `status=proposed`.
- Filter berulang memakai parameter berulang, misalnya `status=draft&status=final`.
- Sort memakai `sort=scheduled_at` atau `sort=-scheduled_at` untuk descending.
- Hanya field pada allowlist endpoint yang dapat dipakai untuk sort.
- Search bebas memakai `q`, dibatasi panjangnya, dan tidak menggantikan filter scope.
- Authorization scope diterapkan sebelum pagination dan agregasi.

## 8. Autentikasi dan Session

### 8.1 Cookie web

Session memakai opaque ID yang menunjuk record server-side:

- `Secure` pada HTTPS.
- `HttpOnly`.
- `SameSite=Lax` atau lebih ketat sesuai alur.
- Masa hidup terbatas dan dapat dicabut.
- ID session dirotasi setelah login serta perubahan hak penting.

Frontend mengambil token CSRF dari response session/bootstrap. Token tidak disimpan di `localStorage`.

### 8.2 Endpoint autentikasi

| Method | Endpoint | Akses | Tujuan |
|---|---|---|---|
| POST | `/auth/login` | Publik | Membuat session web |
| POST | `/auth/logout` | Login | Mencabut session aktif |
| GET | `/auth/session` | Login | Membaca user, role, organisasi, CSRF, dan masa session |
| POST | `/auth/password-recovery` | Publik | Memulai pemulihan tanpa membocorkan akun |
| POST | `/auth/password-reset` | Publik | Menggunakan token satu kali |
| GET | `/me` | Login | Profil dan konteks otorisasi aktif |

#### POST `/auth/login`

```json
{
  "identifier": "peserta@example.ac.id",
  "password": "secret"
}
```

Respons `200`:

```json
{
  "data": {
    "user": {
      "id": "uuid",
      "display_name": "Ahmad",
      "roles": ["participant"]
    },
    "active_context": {
      "role": "participant",
      "organization_id": "uuid"
    },
    "csrf_token": "opaque",
    "expires_at": "2026-10-20T22:30:00+07:00"
  },
  "version": 3,
  "request_id": "uuid"
}
```

Login dan pemulihan memakai rate limit per IP dan identitas ternormalisasi. Pesan gagal tidak membedakan akun tidak ada, tidak aktif, atau kata sandi salah.

### 8.3 Konteks peran

Pengguna dengan beberapa role grant dapat memilih konteks yang memang aktif. Pilihan role di frontend tidak memberikan hak baru. Setiap request tetap mengevaluasi role grant dan assignment terbaru.

## 9. Otorisasi

Setiap endpoint resource memeriksa:

1. Akun aktif.
2. Role grant aktif.
3. Organisasi sesuai.
4. Kepemilikan enrollment atau assignment aktif.
5. Masa berlaku penugasan.
6. Status resource memungkinkan tindakan.
7. Policy version dan prasyarat akademik sesuai.
8. Resource belum digantikan atau dikoreksi oleh versi yang lebih baru.

### 9.1 Matriks akses ringkas

| Domain | Peserta | Mentor | Dosen | Admin Jurusan | Admin Fakultas |
|---|---:|---:|---:|---:|---:|
| Data diri dan target sendiri | RW terbatas | R peserta binaan | R peserta ujian | R lingkup jurusan | Agregat |
| Pengajuan sesi | C/R sendiri | R/U binaan | - | R | Agregat |
| Penilaian tema | R hasil | C/R/U binaan | R sesuai mandat | R | Agregat |
| Kiriman video | C/R sendiri | R/U binaan | R bila diperlukan | R terbatas | Agregat |
| Kelayakan dan nilai video | R hasil | C/R/U binaan | R sesuai mandat | R | Agregat |
| Ujian | R hasil/jadwal | R ringkas | C/R/U peserta tugas | R | Agregat |
| Penugasan | - | R sendiri | R sendiri | C/R/U lingkup | R agregat |
| Kalender/tenggat | R efektif | R efektif | R efektif | C/R/U sesuai mandat | R/approval sesuai mandat |
| Kebijakan | R versi berlaku | R versi berlaku | R versi berlaku | R | C/R/U sesuai mandat |
| Audit | Audit sendiri terbatas | Objek tugas terbatas | Objek tugas terbatas | Lingkup jurusan | Lingkup mandat |

`C/R/U` bukan izin tabel mentah. Setiap tindakan tetap dibatasi oleh state transition dan use case.

## 10. Enum Domain Utama

| Domain | Nilai API |
|---|---|
| Role | `participant`, `mentor`, `lecturer`, `department_admin`, `faculty_admin` |
| Akun | `pending`, `active`, `inactive`, `locked` |
| Sesi | `proposed`, `scheduled`, `in_progress`, `completed`, `no_show`, `cancelled` |
| Status penilaian | `draft`, `final`, `superseded`, `needs_review` |
| Hasil tema | `enough`, `repeat`, `follow_up` |
| Kelayakan video | `eligible`, `ineligible` |
| Hasil video | `enough`, `not_enough` |
| Media | `uploading`, `available`, `failed`, `quarantined`, `deleted` |
| Koreksi | `pending`, `approved`, `rejected`, `applied`, `cancelled` |
| Rekap | `incomplete`, `ready_for_exam`, `awaiting_exam`, `awaiting_components`, `graduated`, `not_graduated`, `needs_review` |
| Metode sesi | `in_person`, `video_call` |
| Jenis penilaian | `theme`, `video`, `exam` |

Label UI diterjemahkan di frontend, misalnya `enough` menjadi **Cukup** dan `not_enough` menjadi **Belum Cukup**.

## 11. Endpoint Sistem dan Referensi

| Method | Endpoint | Tujuan |
|---|---|---|
| GET | `/health/live` | Memastikan process hidup |
| GET | `/health/ready` | Memastikan API dan dependensi kritis siap |
| GET | `/reference/assessment-rubric` | Rubric versi aktif untuk aktor |
| GET | `/reference/curriculum` | Struktur kurikulum versi konteks |
| GET | `/reference/policies/current` | Ringkasan policy version efektif |

Seluruh endpoint pada tabel kontrak menggunakan base path `/api/v1`, kecuali health check yang ditulis sebagai path absolut. Health response tidak mengungkap secret, connection string, hostname internal, atau detail database.

## 12. Endpoint Peserta

### 12.1 Ringkasan endpoint

| Method | Endpoint | Prioritas | Layar |
|---|---|---:|---|
| GET | `/me/dashboard` | P0 | P01 |
| GET | `/me/targets` | P0 | P01, P02 |
| GET | `/me/progress` | P0 | P01, P06 |
| GET | `/me/results` | P0 | P05 |
| GET | `/me/exam-readiness` | P0 | P06 |
| GET | `/me/grades` | P0 | P06 |
| POST | `/sessions` | P0 | P03 |
| GET | `/sessions/{session_id}` | P0 | P03 |
| POST | `/sessions/{session_id}/cancel` | P1 | P03 |
| POST | `/video-attempts` | P0 | P04 |
| GET | `/video-attempts/{attempt_id}` | P0 | P04, P05 |
| POST | `/video-attempts/{attempt_id}/versions` | P0 | P04 |

### 12.2 GET `/me/targets`

Query yang didukung:

- `part_id`
- `status`
- `due_from`
- `due_to`
- `limit`
- `cursor`

Item minimum:

```json
{
  "id": "uuid",
  "theme": {
    "id": "uuid",
    "code": "T12",
    "name": "Tema 12",
    "part_no": 2
  },
  "effective_due_date": "2026-11-02",
  "status": "active",
  "first_valid_submission_at": null,
  "activity_score": null,
  "allowed_actions": ["request_session"]
}
```

### 12.3 POST `/sessions`

Membuat pengajuan sesi peserta.

```json
{
  "theme_ids": ["uuid", "uuid"],
  "method": "video_call",
  "proposed_at": "2026-10-22T15:00:00+07:00",
  "participant_note": "Mohon fokus pada kelancaran ayat akhir."
}
```

Validasi:

- Minimal satu tema.
- Semua tema berada pada enrollment peserta, bagian aktif yang sama, dan dapat diajukan.
- `proposed_at` berada dalam rentang yang diizinkan.
- Assignment Mentor aktif tersedia.

Respons `201` memuat sesi berstatus `proposed` dan `allowed_actions`.

### 12.4 POST `/video-attempts`

Membuka slot akademik video jika server menyatakan bagian memenuhi prasyarat.

```json
{
  "part_id": "uuid"
}
```

Server menentukan `cycle_no` dan `revision_no`; klien tidak boleh mengalokasikannya.

### 12.5 POST `/video-attempts/{attempt_id}/versions`

Mengirim versi media untuk slot akademik yang sama.

```json
{
  "video_url": "https://www.youtube.com/watch?v=example",
  "recorded_on": "2026-10-20",
  "completeness_declared": true,
  "expected_version": 2
}
```

Header `Idempotency-Key` wajib. Server:

- Hanya menerima HTTPS dan host allowlist.
- Tidak melakukan server-side fetch ke URL sembarang.
- Menambah `video_version_no`.
- Tidak menambah `revision_no` bila pengiriman mengganti media yang ditolak secara teknis.

## 13. Endpoint Mentor dan Pembimbingan

### 13.1 Antrean dan peserta

| Method | Endpoint | Tujuan |
|---|---|---|
| GET | `/mentor/queue` | Antrean sesi, video, dan tindak lanjut |
| GET | `/mentor/participants` | Daftar peserta dalam assignment aktif |
| GET | `/mentor/participants/{enrollment_id}` | Rekap peserta binaan |
| GET | `/enrollments/{enrollment_id}/assessment-history` | Riwayat penilaian sesuai scope |

Filter `/mentor/queue`:

- `work_type=session|video_eligibility|video_assessment|follow_up`
- `status`
- `scheduled_from`
- `scheduled_to`
- `q`
- `cursor`
- `limit`

Setiap item memuat `allowed_actions`. Data di luar assignment aktif tidak boleh ikut dalam jumlah agregat atau pagination.

### 13.2 Manajemen sesi

| Method | Endpoint | Tujuan |
|---|---|---|
| PATCH | `/sessions/{session_id}` | Menjadwalkan atau mengubah draft sesi |
| POST | `/sessions/{session_id}/start` | Mengubah sesi menjadi `in_progress` |
| POST | `/sessions/{session_id}/complete` | Menutup sesi setelah penilaian selesai |
| POST | `/sessions/{session_id}/no-show` | Mencatat ketidakhadiran |

Contoh PATCH:

```json
{
  "scheduled_at": "2026-10-22T15:30:00+07:00",
  "method": "video_call",
  "mentor_note": "Tautan pertemuan dikirim terpisah.",
  "expected_version": 1
}
```

### 13.3 Penilaian tema

| Method | Endpoint | Tujuan |
|---|---|---|
| POST | `/sessions/{session_id}/theme-assessments` | Membuat draft penilaian tema |
| GET | `/theme-assessments/{assessment_id}` | Membaca draft/final |
| PATCH | `/theme-assessments/{assessment_id}` | Memperbarui draft |
| POST | `/theme-assessments/{assessment_id}/finalize` | Finalisasi satu penilaian tema |

Draft penilaian:

```json
{
  "theme_id": "uuid",
  "actual_at": "2026-10-22T15:35:00+07:00",
  "manual_score": 7,
  "outcome": "enough",
  "mentor_note": "Kelancaran cukup, tajwid perlu dirapikan.",
  "incidents": [
    {
      "location_text": "QS An-Naba ayat 12",
      "video_second": null,
      "primary_category": "tajwid",
      "context": "Panjang bacaan kurang",
      "assistance": "cue",
      "self_corrected": true,
      "counted": false,
      "counting_reason": "Koreksi mandiri sesuai kebijakan",
      "note": null
    }
  ]
}
```

Finalisasi:

```http
POST /api/v1/theme-assessments/{assessment_id}/finalize
Idempotency-Key: 2e1f6930-f4ba-4fd1-8b45-b58ae7264855
X-CSRF-Token: opaque
```

```json
{
  "expected_version": 4
}
```

Server mengalokasikan `attempt_no` 1-5 dalam transaksi. Hasil belum Cukup pada kesempatan kelima menjadi `follow_up`; kesempatan keenam tidak dibuat otomatis.

Respons final minimum:

```json
{
  "data": {
    "assessment_id": "uuid",
    "status": "final",
    "attempt_no": 3,
    "outcome": "enough",
    "manual_score": 7,
    "finalized_at": "2026-10-22T16:00:00+07:00",
    "policy_version_id": "uuid",
    "allowed_actions": []
  },
  "version": 5,
  "request_id": "uuid"
}
```

## 14. Endpoint Video dan Media

### 14.1 Pemeriksaan kelayakan teknis

| Method | Endpoint | Tujuan |
|---|---|---|
| GET | `/video-versions/{video_version_id}` | Detail versi dan status review |
| PUT | `/video-versions/{video_version_id}/eligibility-draft` | Simpan draft checklist |
| POST | `/video-versions/{video_version_id}/eligibility` | Finalisasi kelayakan teknis |

Finalisasi kelayakan:

```json
{
  "decision": "ineligible",
  "reason": "Audio tidak terdengar pada sebagian besar rekaman.",
  "checks": [
    {"code": "duration_ok", "passed": true, "note": null},
    {"code": "audio_clear", "passed": false, "note": "Audio hilang setelah menit 03:12"},
    {"code": "continuous_recording", "passed": true, "note": null}
  ],
  "expected_version": 2
}
```

Header `Idempotency-Key` wajib. `reason` wajib jika `decision` adalah `ineligible`. Hanya `eligible` yang membuka penilaian akademik.

### 14.2 Penilaian video

| Method | Endpoint | Tujuan |
|---|---|---|
| POST | `/video-versions/{video_version_id}/assessment` | Membuat draft penilaian |
| GET | `/video-assessments/{assessment_id}` | Membaca draft/final |
| PATCH | `/video-assessments/{assessment_id}` | Memperbarui draft |
| POST | `/video-assessments/{assessment_id}/finalize` | Finalisasi penilaian video |

Contoh draft:

```json
{
  "manual_score": 8,
  "mentor_note": "Hafalan lancar dengan beberapa koreksi mandiri.",
  "feedback_audio_id": "uuid",
  "incidents": [
    {
      "location_text": "QS An-Naziat ayat 8",
      "video_second": 132,
      "primary_category": "word_choice",
      "context": "Pilihan kata tertukar",
      "assistance": "none",
      "self_corrected": false,
      "counted": true,
      "counting_reason": "Tidak dikoreksi mandiri",
      "note": null
    }
  ]
}
```

Finalisasi hanya menerima:

```json
{
  "expected_version": 6
}
```

Server menghitung jumlah insiden `counted=true`, menentukan hasil dari policy version, dan mengabaikan hasil buatan klien. Baseline rancangan adalah 0-3 `enough` dan 4 atau lebih `not_enough`. Audio harus berstatus `available`.

### 14.3 Upload audio privat

| Method | Endpoint | Tujuan |
|---|---|---|
| POST | `/media/audio/upload-intents` | Membuat intent dan signed upload URL |
| POST | `/media/{media_id}/complete` | Mengonfirmasi upload untuk validasi worker |
| GET | `/media/{media_id}` | Membaca metadata aman |
| POST | `/media/{media_id}/playback-url` | Membuat signed read URL berumur pendek |

Request intent:

```json
{
  "file_name": "umpan-balik.m4a",
  "content_type": "audio/mp4",
  "size_bytes": 824312,
  "sha256": "hex-encoded-sha256",
  "purpose": "mentor_feedback"
}
```

Respons:

```json
{
  "data": {
    "media_id": "uuid",
    "upload_url": "https://object-storage.example/signed-path",
    "upload_method": "PUT",
    "required_headers": {"Content-Type": "audio/mp4"},
    "expires_at": "2026-10-20T14:40:00+07:00"
  },
  "version": 1,
  "request_id": "uuid"
}
```

Signed URL tidak disimpan pada log atau telemetry. Endpoint playback memeriksa authorization saat dipanggil dan tidak menganggap kepemilikan `media_id` sebagai izin.

## 15. Endpoint Dosen dan Ujian

### 15.1 Ringkasan endpoint

| Method | Endpoint | Tujuan |
|---|---|---|
| GET | `/lecturer/exam-queue` | Peserta dengan lima bagian Cukup |
| POST | `/exams` | Membuat draft ujian |
| GET | `/exams/{exam_id}` | Detail ujian sesuai scope |
| PATCH | `/exams/{exam_id}` | Memperbarui jadwal/catatan draft |
| PUT | `/exams/{exam_id}/items` | Mengganti daftar item saat masih draft |
| POST | `/exams/{exam_id}/start` | Memulai pelaksanaan |
| PUT | `/exams/{exam_id}/assessment-draft` | Menyimpan penilaian dan bukti draft |
| POST | `/exams/{exam_id}/finalize` | Finalisasi ujian |
| GET | `/exams/{exam_id}/summary` | Rekap ujian dan nilai tersedia |

### 15.2 POST `/exams`

```json
{
  "enrollment_id": "uuid",
  "scheduled_at": "2026-12-15T09:00:00+07:00"
}
```

Server memverifikasi lima bagian Cukup dan assignment Dosen aktif. Respons memuat policy version dan `allowed_actions`.

### 15.3 PUT `/exams/{exam_id}/items`

```json
{
  "items": [
    {
      "source": "application",
      "question_version_id": "uuid",
      "question_type": "continue_three_verses",
      "scope": {"surah": "An-Naba", "start_verse": 10},
      "answer_reference": "Tersedia untuk penguji berwenang",
      "weight": null
    }
  ],
  "expected_version": 2
}
```

Jika jumlah atau bobot soal belum disahkan, endpoint dapat menyimpan draft tetapi finalisasi mengembalikan `POLICY_NOT_APPROVED`.

### 15.4 POST `/exams/{exam_id}/finalize`

```json
{
  "actual_at": "2026-12-15T09:05:00+07:00",
  "manual_score": 8,
  "examiner_note": "Peserta menjawab seluruh item.",
  "evidence_media_ids": ["uuid"],
  "expected_version": 5
}
```

Header `Idempotency-Key` wajib. Server memverifikasi eligibility, paket soal, bukti, skor 1-10, assignment, dan versi kebijakan. Agregasi D hanya dihitung jika metodenya telah disahkan.

## 16. Endpoint Nilai dan Progres

| Method | Endpoint | Akses | Tujuan |
|---|---|---|---|
| GET | `/enrollments/{enrollment_id}/progress` | Sesuai scope | Progres tema, bagian, video, ujian |
| GET | `/enrollments/{enrollment_id}/grades` | Sesuai scope | Snapshot nilai terbaru |
| GET | `/enrollments/{enrollment_id}/grades/history` | Admin/penilai sesuai mandat | Riwayat snapshot |
| POST | `/enrollments/{enrollment_id}/grades/publish` | Mandat khusus | Membuat snapshot nilai baru |

Contoh rekap:

```json
{
  "data": {
    "enrollment_id": "uuid",
    "status": "awaiting_components",
    "exam_readiness": "ready_for_exam",
    "components": {
      "k": {"value": 8.25, "weight": 0.20, "status": "available"},
      "m": {"value": null, "weight": 0.40, "status": "policy_pending"},
      "d": {"value": null, "weight": 0.40, "status": "not_assessed"}
    },
    "final_score": null,
    "graduation_status": null,
    "policy_version_id": "uuid",
    "calculated_at": "2026-10-20T14:30:00+07:00",
    "missing_requirements": ["mentor_aggregation_policy", "final_exam"]
  },
  "version": 4,
  "request_id": "uuid"
}
```

Aturan:

- K dihitung dari tanggal sesi aktual pertama yang sah terhadap tenggat efektif.
- M dan D tetap `null` jika metode agregasinya belum disahkan.
- N hanya dihitung ketika K, M, D, dan ujian final tersedia.
- Formula kebijakan baseline adalah `N = 0.2K + 0.4M + 0.4D` dengan ambang 6.
- Tidak ada ambang Dosen terpisah kecuali policy version menetapkannya.
- Snapshot lama tidak ditimpa.

## 17. Endpoint Admin Jurusan

### 17.1 Peserta dan penugasan

| Method | Endpoint | Tujuan |
|---|---|---|
| GET | `/department/enrollments` | Daftar peserta lingkup jurusan |
| POST | `/department/enrollments` | Membuat kepesertaan |
| GET | `/department/enrollments/{enrollment_id}` | Detail peserta |
| PATCH | `/department/enrollments/{enrollment_id}` | Perubahan data yang diizinkan |
| POST | `/department/enrollments/{enrollment_id}/assignments` | Membuat assignment Mentor/Dosen |
| POST | `/department/assignments/{assignment_id}/end` | Mengakhiri assignment |
| GET | `/department/enrollments/{enrollment_id}/assignments` | Riwayat assignment |
| POST | `/department/imports/enrollments` | Impor peserta asinkron, P1 |

Membuat assignment:

```json
{
  "role": "mentor",
  "assignee_user_id": "uuid",
  "valid_from": "2026-10-20T00:00:00+07:00",
  "valid_to": null,
  "reason": "Penugasan awal angkatan 2026",
  "expected_version": 1
}
```

Perubahan petugas tidak menimpa assignment lama. Server mengakhiri interval lama dan membuat record baru dalam transaksi.

### 17.2 Kalender dan tenggat

| Method | Endpoint | Tujuan |
|---|---|---|
| GET | `/department/cohorts` | Daftar angkatan |
| GET | `/department/cohorts/{cohort_id}/calendar` | Kalender 52 pekan dan 44 target |
| POST | `/department/cohorts/{cohort_id}/deadline-changes` | Mengajukan perubahan tenggat |
| POST | `/department/deadline-changes/{change_id}/approve` | Menyetujui sesuai mandat |
| POST | `/department/deadline-changes/{change_id}/reject` | Menolak sesuai mandat |

Pengajuan perubahan tenggat:

```json
{
  "target_ids": ["uuid"],
  "new_due_date": "2026-11-16",
  "reason": "Penyesuaian kalender akademik fakultas",
  "impact_note": "Target berikutnya bergeser dua pekan",
  "expected_version": 3
}
```

Respons pratinjau harus menunjukkan tanggal lama, tanggal baru, target terdampak, dan kebutuhan persetujuan. Persetujuan final memakai `Idempotency-Key`.

### 17.3 Laporan jurusan

| Method | Endpoint | Tujuan |
|---|---|---|
| GET | `/department/reports/progress` | Progres dan keterlambatan |
| GET | `/department/reports/queues` | Antrean video dan ujian |
| GET | `/department/reports/incomplete-grades` | Komponen nilai belum lengkap |
| POST | `/department/exports` | Membuat ekspor sesuai filter dan mandat |
| GET | `/department/exports/{job_id}` | Status dan hasil ekspor |

Laporan tidak memberikan akses otomatis ke media. Endpoint ekspor mengembalikan `202` dan job ID. Download URL bersifat privat, berumur pendek, dan hanya dibuat setelah otorisasi ulang.

## 18. Endpoint Admin Fakultas dan Kebijakan

| Method | Endpoint | Tujuan |
|---|---|---|
| GET | `/faculty/policies` | Daftar versi kebijakan |
| POST | `/faculty/policies` | Membuat draft versi baru |
| GET | `/faculty/policies/{policy_id}` | Detail kebijakan dan status approval |
| PATCH | `/faculty/policies/{policy_id}` | Mengubah draft |
| POST | `/faculty/policies/{policy_id}/approve` | Menyetujui sesuai mandat |
| POST | `/faculty/policies/{policy_id}/publish` | Menerbitkan versi efektif |
| GET | `/faculty/reports/aggregate` | Laporan agregat lintas jurusan |
| GET | `/faculty/audit` | Audit sesuai mandat |

Aturan:

- Policy yang telah dipakai oleh penilaian tidak diedit in-place.
- Perubahan aturan membuat versi baru dengan periode berlaku.
- Publish dan approval memakai `expected_version` serta `Idempotency-Key`.
- Respons kebijakan memisahkan rule yang disahkan dari keputusan yang masih terbuka.

## 19. Endpoint Koreksi dan Audit

### 19.1 Koreksi

| Method | Endpoint | Tujuan |
|---|---|---|
| POST | `/corrections` | Mengajukan koreksi terhadap hasil final |
| GET | `/corrections/{correction_id}` | Detail dan status koreksi |
| GET | `/corrections` | Daftar sesuai scope |
| POST | `/corrections/{correction_id}/approve` | Menyetujui koreksi |
| POST | `/corrections/{correction_id}/reject` | Menolak koreksi |
| POST | `/corrections/{correction_id}/apply` | Membuat record pengganti dan dampak |

Request koreksi:

```json
{
  "original_assessment_id": "uuid",
  "reason_code": "data_entry_error",
  "reason": "Skor pada formulir final tidak sesuai lembar pemeriksaan.",
  "requested_change": {
    "manual_score": 7
  }
}
```

Koreksi tidak mengubah record final lama. Apply membuat record pengganti, menandai hasil sebelumnya `superseded`, membuat snapshot nilai baru bila diperlukan, dan mencatat audit.

### 19.2 Audit

| Method | Endpoint | Tujuan |
|---|---|---|
| GET | `/audit/events` | Daftar event sesuai scope |
| GET | `/audit/objects/{object_type}/{object_id}` | Riwayat satu objek |

Audit response memuat aktor, waktu, tindakan, object reference, request ID, dan perubahan aman. Nilai secret, password, token, signed URL, serta isi media tidak disertakan.

## 20. Idempotensi

### 20.1 Command yang wajib idempotent

- Finalisasi penilaian tema.
- Finalisasi kelayakan video.
- Finalisasi penilaian video.
- Pembuatan versi video.
- Finalisasi ujian.
- Approval/publish kebijakan.
- Approval/apply koreksi.
- Approval perubahan tenggat.
- Penerbitan snapshot nilai.

### 20.2 Perilaku server

| Kondisi | Hasil |
|---|---|
| Kunci baru, payload valid | Jalankan operasi dan simpan hasil aman |
| Kunci sama, payload dan aktor sama | Kembalikan status/body hasil pertama |
| Kunci sama, payload berbeda | `409 IDEMPOTENCY_KEY_REUSED` |
| Request pertama masih diproses | `409` atau `202` dengan status operasi yang dapat dibaca |
| Hasil lama telah kedaluwarsa | Perlakukan sesuai retensi yang didokumentasikan, jangan jalankan diam-diam |

Klien yang mengalami timeout mengirim ulang request yang sama dengan kunci yang sama atau membaca resource resmi. Klien tidak membuat kunci baru sebelum status operasi pertama diketahui.

## 21. Optimistic Concurrency

- Resource yang dapat berubah memiliki `row_version`.
- Respons utama menyalin nilai tersebut ke field envelope `version`.
- Mutasi membawa `expected_version` pada body.
- Ketidaksesuaian menghasilkan `409 VERSION_CONFLICT` dengan `current_version` yang aman.
- Klien memuat ulang, meninjau perubahan, dan meminta konfirmasi ulang.
- Server tidak melakukan last-write-wins pada data akademik.

Contoh:

```json
{
  "code": "VERSION_CONFLICT",
  "message": "Data telah diperbarui oleh pengguna lain.",
  "field_errors": {},
  "details": {
    "current_version": 9,
    "reload_url": "/api/v1/video-assessments/uuid"
  },
  "request_id": "uuid"
}
```

## 22. State Transition Utama

### 22.1 Sesi

```text
proposed -> scheduled -> in_progress -> completed
    |           |              |
    +-----------+--------------+-> cancelled
                +-----------------> no_show
```

### 22.2 Penilaian

```text
draft -> final -> superseded
           |
           +-> needs_review
```

Record final tidak kembali menjadi draft. Koreksi membuat versi pengganti.

### 22.3 Video

```text
versi dikirim -> eligible -> draft assessment -> final assessment
             \-> ineligible -> versi media pengganti pada attempt yang sama
```

### 22.4 Nilai

```text
incomplete -> ready_for_exam -> awaiting_exam -> awaiting_components
                                             -> graduated
                                             -> not_graduated
                                             -> needs_review
```

Server mengembalikan `allowed_actions` untuk membantu UI, tetapi field tersebut bukan pengganti pemeriksaan otorisasi saat command dijalankan.

## 23. Validasi Domain Kritis

### 23.1 Penilaian umum

- Skor final wajib 1-10 sesuai policy version.
- Policy version awal hanya menerima bilangan bulat 1-10; tipe penyimpanan tetap desimal untuk kompatibilitas kebijakan masa depan.
- Insiden memiliki tepat satu kategori utama.
- Keputusan `counted` dan alasannya disimpan.
- Draft boleh belum lengkap, tetapi finalisasi tidak.

### 23.2 Tema

- Semua tema dalam satu sesi berasal dari bagian yang sama.
- Nomor kesempatan ditentukan server pada rentang 1-5.
- Tanggal pengajuan/jadwal tidak menjadi tanggal setoran pertama.
- Tanggal aktual pertama dari hasil efektif menjadi sumber skor K.

### 23.3 Video

- Bagian hanya dapat dikirim setelah seluruh temanya Cukup.
- Penolakan teknis tidak menambah revisi akademik.
- Review Layak dan penilaian menunjuk video version yang sama.
- Audio Mentor harus `available` sebelum finalisasi penilaian.
- Skor manual tidak menentukan hasil Cukup/Belum Cukup.

### 23.4 Ujian dan nilai

- Ujian hanya tersedia setelah lima bagian Cukup.
- Paket soal dan bukti wajib lengkap sebelum finalisasi.
- Ujian final wajib ada sebelum kelulusan.
- Komponen belum tersedia tetap `null`.
- Snapshot nilai baru tidak mengubah snapshot historis.

## 24. Operasi Asinkron

Ekspor, validasi media, notifikasi, dan pekerjaan berat menggunakan job resource.

Respons `202`:

```json
{
  "data": {
    "job_id": "uuid",
    "status": "queued",
    "status_url": "/api/v1/jobs/uuid"
  },
  "version": 1,
  "request_id": "uuid"
}
```

Endpoint umum:

| Method | Endpoint | Tujuan |
|---|---|---|
| GET | `/jobs/{job_id}` | Status job sesuai pemilik/scope |
| POST | `/jobs/{job_id}/cancel` | Membatalkan bila state mengizinkan |

Status minimum: `queued`, `running`, `succeeded`, `failed`, `cancelled`. Kegagalan worker tidak membatalkan transaksi akademik yang sudah commit.

## 25. Rate Limiting

Baseline awal:

| Endpoint | Batas awal |
|---|---|
| Login | 5 percobaan per 15 menit per IP dan identitas |
| Password recovery | 3 per jam per IP dan identitas |
| Signed media URL | 30 per menit per user |
| Endpoint baca umum terautentikasi | 120 per menit per session |
| Endpoint mutasi | 60 per menit per session |
| Ekspor | 5 job aktif per user |

Nilai final disesuaikan berdasarkan pengujian beban. Respons 429 memuat `Retry-After`. Rate limit tidak menggantikan lock akun dan deteksi penyalahgunaan.

## 26. Keamanan API

- Semua production traffic memakai HTTPS.
- CORS dinonaktifkan untuk origin lain pada MVP kecuali kebutuhan eksplisit disahkan.
- Mutasi session-cookie memerlukan token CSRF.
- Password, token pemulihan, cookie, dan API secret tidak dicatat pada log.
- URL media bertanda tangan berumur pendek dan tidak masuk analytics.
- Video URL divalidasi berdasarkan scheme dan hostname allowlist tanpa arbitrary server fetch.
- Input teks memiliki batas panjang dan dinormalisasi tanpa menghilangkan bukti akademik.
- Query dinamis memakai parameter binding dan allowlist sort/filter.
- Acuan jawaban ujian hanya dikirim kepada Dosen berwenang.
- Respons laporan dan ekspor menerapkan scope sebelum agregasi.
- UUID sulit ditebak tidak dianggap sebagai kontrol akses.
- Error 404 dipakai bila 403 dapat membocorkan keberadaan objek sensitif.

## 27. Observability

Setiap request mencatat data terstruktur yang aman:

- `request_id`
- trace/span ID
- method dan route template, bukan URL dengan token
- status code
- durasi
- actor ID ter-pseudonim bila diperlukan
- organization ID
- error code
- idempotency result tanpa key mentah

Jangan mencatat:

- Password, cookie, CSRF token, recovery token.
- Signed URL.
- Isi audio/video.
- Acuan jawaban ujian.
- Catatan akademik lengkap atau PII yang tidak diperlukan.

Metrics minimum:

- Latency dan error rate per route.
- Jumlah 401, 403, 409, 422, dan 429.
- Idempotency hit/conflict.
- Finalisasi berhasil/gagal per jenis.
- Kedalaman antrean outbox/job.
- Kegagalan upload dan validasi media.

## 28. OpenAPI dan Client Generation

FastAPI OpenAPI adalah kontrak executable:

- `operation_id` stabil dan unik.
- Semua request/response memakai Pydantic model eksplisit.
- Enum domain didefinisikan terpusat.
- Endpoint mencantumkan kemungkinan error domain utama.
- Contoh payload tidak memakai data pribadi nyata.
- Schema rahasia dipisahkan dari schema response.
- Client TypeScript dihasilkan otomatis pada CI dan tidak diedit manual.

OpenAPI tersedia di development/staging. Dokumentasi interaktif production dimatikan atau dibatasi untuk admin teknis.

## 29. Struktur Modul FastAPI

```text
apps/api/app/
  api/
    dependencies.py
    errors.py
    pagination.py
    v1/
      auth.py
      me.py
      sessions.py
      assessments.py
      videos.py
      media.py
      exams.py
      grades.py
      department.py
      faculty.py
      corrections.py
      audit.py
      jobs.py
  modules/
    identity/
    organizations/
    cohorts/
    curriculum/
    calendar/
    mentoring/
    video/
    media/
    exams/
    grading/
    corrections/
    reporting/
    audit/
```

Router hanya menangani parsing, dependency, schema, dan HTTP mapping. Alokasi kesempatan, hasil video, nilai, kelulusan, transaksi, audit, serta outbox berada di application/domain service.

## 30. Strategi Pengujian API

### 30.1 Contract test

- OpenAPI berubah hanya melalui review.
- Generated TypeScript client dapat dikompilasi.
- Semua endpoint mengembalikan envelope dan error schema yang sesuai.
- Enum dan nullability sama antara API, database mapping, dan client.

### 30.2 Authorization test

- Peserta tidak dapat membaca enrollment lain.
- Mentor tidak dapat menilai peserta di luar assignment aktif.
- Dosen tidak dapat membuka acuan jawaban ujian di luar tugas.
- Admin Jurusan tidak dapat mengakses jurusan lain.
- Laporan agregat tidak otomatis membuka media privat.
- Penugasan kedaluwarsa berlaku pada request berikutnya.

### 30.3 Concurrency dan idempotency test

- Dua finalisasi tema bersamaan hanya menghasilkan satu attempt number.
- Retry dengan kunci dan payload sama mengembalikan hasil yang sama.
- Kunci sama dengan payload berbeda menghasilkan 409.
- `expected_version` lama menghasilkan 409 tanpa overwrite.
- Timeout setelah commit dapat dipulihkan tanpa finalisasi ganda.

### 30.4 Domain test

- Tema lintas bagian ditolak dalam satu pengajuan sesi.
- Kesempatan keenam tidak dibuat otomatis.
- Penolakan teknis tidak menaikkan revisi akademik.
- Video dengan tiga kesalahan tetapi tanpa audio tidak dapat difinalkan.
- Empat insiden dengan satu koreksi mandiri sah dihitung sebagai tiga kesalahan.
- Skor manual tidak mengubah hasil berdasarkan jumlah kesalahan.
- Ujian ditolak jika lima bagian belum Cukup.
- Nilai yang belum tersedia tetap `null`.
- Koreksi menghasilkan record dan snapshot baru.

### 30.5 Security test

- CSRF pada seluruh mutasi web.
- Session fixation dan session revocation.
- Rate limiting login/recovery.
- Host allowlist untuk video URL.
- Tidak ada secret atau signed URL pada log/error.
- Uji object-level authorization pada semua UUID.

## 31. Keputusan Terbuka

Kontrak final menunggu keputusan berikut:

- Metode agregasi nilai Mentor menjadi M.
- Jumlah, bobot, dan agregasi soal menjadi D.
- Aturan pembulatan N.
- Ujian ulang dan penilaian ulang.
- Mandat approval untuk perubahan tenggat, koreksi, dan publish kebijakan.
- Batas ukuran, format, serta retensi audio.
- Daftar host video yang diizinkan.
- Retensi idempotency record dan job result.
- Mekanisme OAuth/OIDC untuk aplikasi Android.

Endpoint boleh menyimpan draft yang tidak bergantung pada keputusan terbuka. Finalisasi yang memerlukan keputusan tersebut harus mengembalikan `409 POLICY_NOT_APPROVED` sampai policy version tersedia.

## 32. Definition of Done API

API v1 siap untuk pilot ketika:

- Endpoint P0 tercakup dalam OpenAPI dan client TypeScript berhasil dihasilkan.
- Session, CSRF, rate limit, dan object-level authorization teruji.
- Semua command kritis idempotent dan memakai optimistic concurrency.
- Transaksi finalisasi menghasilkan audit serta outbox dalam commit yang sama.
- Draft dan final tidak tercampur; hasil final tidak diubah langsung.
- Nilai kosong tetap `null` dan keputusan terbuka diblokir secara eksplisit.
- Error code, message, field error, dan request ID konsisten.
- Pagination stabil dan scope diterapkan sebelum query/agregasi.
- Signed media URL privat, singkat, dan tidak tercatat di log.
- Contract, integration, concurrency, domain, dan security test lulus.
- Dokumentasi endpoint serta contoh payload sesuai implementasi aktual.

---

Dokumen ini adalah baseline kontrak. Saat implementasi dimulai, OpenAPI FastAPI menjadi spesifikasi executable dan perubahan kontrak harus ditinjau bersama frontend, backend, database, keamanan, serta pemilik kebijakan akademik.
