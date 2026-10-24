# YAQin

YAQin (Yakin, Amalin, Mutqin) adalah aplikasi pendampingan hafalan Juz 30. Repository ini menggunakan monorepo dengan Next.js untuk web dan FastAPI untuk API.

## Prasyarat

- Node.js 24 atau lebih baru
- pnpm 11 atau lebih baru
- uv 0.12 atau lebih baru (Python 3.14 akan dikelola oleh uv)

Docker Engine dengan Compose v2 dibutuhkan untuk menjalankan stack development dalam container.

## Mulai cepat

```bash
pnpm install
pnpm --filter @yaqin/api setup
pnpm dev
```

Pada Windows, gunakan skrip berikut untuk menyiapkan dependency yang belum ada dan
menjalankan Next.js serta FastAPI sekaligus:

```cmd
dev.cmd
```

Web tersedia di `http://localhost:3000`, sedangkan API development di `http://localhost:8000`. Salin `.env.example` menjadi `.env` saat konfigurasi runtime mulai diperlukan; jangan commit `.env`.

## Docker Compose development

Stack development saat ini berisi Next.js, FastAPI, dan PostgreSQL:

```bash
docker compose up --build --wait
docker compose ps
```

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`
- PostgreSQL hanya tersedia pada network privat Compose dan tidak membuka port host.

Hentikan container tanpa menghapus data:

```bash
docker compose down
```

Gunakan `docker compose down --volumes` hanya ketika database development memang ingin dihapus.

## Perintah utama

| Perintah | Fungsi |
|---|---|
| `pnpm dev` | Menjalankan web dan API secara paralel |
| `pnpm lint` | Menjalankan ESLint dan Ruff |
| `pnpm typecheck` | Menjalankan TypeScript dan mypy |
| `pnpm test` | Menjalankan Vitest dan Pytest |
| `pnpm build` | Membangun Next.js dan memvalidasi paket API |
| `pnpm db:migrate` | Menjalankan migration Alembic hingga revision terbaru |
| `pnpm check` | Menjalankan seluruh pemeriksaan lokal |
| `pnpm compose:config` | Memvalidasi konfigurasi Compose |
| `pnpm compose:build` | Membangun image web dan API |
| `pnpm compose:up` | Membangun dan menjalankan stack sampai sehat |
| `pnpm compose:down` | Menghentikan stack tanpa menghapus volume database |

## Struktur

```text
apps/web/           Next.js App Router
apps/api/           FastAPI modular monolith dan worker
packages/api-client Client TypeScript hasil OpenAPI (mulai TASK-010)
packages/ui/        Komponen UI bersama (mulai TASK-009)
packages/config/    Konfigurasi TypeScript bersama
infra/              Catatan Compose, gateway, script, dan monitoring
tests/e2e/          Pengujian lintas service
docs/operations/    Runbook operasional
```

Keputusan akademik `DEC-001` sampai `DEC-003` sengaja tidak ditentukan dalam bootstrap repository.

