# YAQin API

FastAPI modular monolith untuk seluruh aturan domain YAQin.

```bash
uv sync
uv run fastapi dev app/main.py --port 8000
DATABASE_URL=postgresql://yaqin:secret@localhost:5432/yaqin uv run python -m app.db.migrations
uv run pytest
```

Endpoint bootstrap:

- `GET /`: identitas service.
- `GET /health/live`: pemeriksaan process tanpa dependency eksternal.
- `GET /health/ready`: pemeriksaan koneksi PostgreSQL tanpa membocorkan detail koneksi.
- `GET /api/v1`: identitas kontrak API v1.

Konfigurasi runtime divalidasi dari environment oleh Pydantic Settings. Database memakai
SQLAlchemy async dengan psycopg, pool terukur, timeout PostgreSQL, dan transaksi eksplisit
melalui `SqlAlchemyUnitOfWork`. Alembic menyimpan version table di schema `alembic`, tabel
domain di `app`, dan tabel operasional di `ops`.

Perintah migration:

```bash
uv run python -m app.db.migrations                 # upgrade head
uv run python -m app.db.migrations current
uv run python -m app.db.migrations downgrade base
```

Migration test membutuhkan database PostgreSQL kosong yang boleh diubah:

```bash
MIGRATION_TEST_DATABASE_URL=postgresql://yaqin:secret@localhost:5432/yaqin_test \
  uv run pytest tests/test_migrations.py --no-cov
```

