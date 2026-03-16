# Deployment checklist (production-like)

## TLS / reverse proxy

- [ ] Terminate TLS at a reverse proxy (Nginx/Caddy/ALB) with modern ciphers.
- [ ] Force HTTPS and enable strict transport security (HSTS) once stable:
  - `SECURE_SSL_REDIRECT=True`
  - `SESSION_COOKIE_SECURE=True`
  - `CSRF_COOKIE_SECURE=True`
  - (Add) `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`
- [ ] Set correct proxy headers (e.g., `SECURE_PROXY_SSL_HEADER`) if behind a load balancer.

## App config hygiene

- [ ] `DEBUG=False` in production.
- [ ] Tight `ALLOWED_HOSTS` and correct `CSRF_TRUSTED_ORIGINS` for your domain(s).
- [ ] Centralize secrets in a secret manager (not `.env` on disk).

## Private file storage (medical images)

- [ ] Use private object storage (S3/Spaces) for DICOM + derived assets.
- [ ] Ensure bucket policies block public access; use SSE-KMS encryption.
- [ ] Serve previews via authenticated endpoints or time-limited signed URLs.

## Runtime

- [ ] Run web workers (Gunicorn/uvicorn) separately from Celery workers.
- [ ] Run Redis in a private network; require auth where appropriate.
- [ ] Add monitoring (health checks, metrics, error tracking).

