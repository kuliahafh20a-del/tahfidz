# Docker Compose

Baseline development aktif berada di `/compose.yaml` dan saat ini menjalankan:

- Next.js pada port host `3000`.
- FastAPI pada port host `8000`.
- PostgreSQL pada network privat tanpa port host.

Nginx, worker, dan object storage sengaja ditunda sesuai cakupan implementasi saat ini. Override environment-specific akan ditempatkan di direktori ini ketika komponennya mulai diperlukan.

