# YAQin API

FastAPI modular monolith untuk seluruh aturan domain YAQin.

```bash
uv sync
uv run fastapi dev app/main.py --port 8000
uv run pytest
```

Endpoint bootstrap:

- `GET /`: identitas service.
- `GET /health/live`: pemeriksaan process tanpa dependency eksternal.
- `GET /api/v1`: identitas kontrak API v1.

Database, readiness check, Unit of Work, dan Alembic akan diaktifkan pada `TASK-004`.

