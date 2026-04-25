# 08 -- Deployment Guide

> Sourced from `Dockerfile`, `docker-compose.yml`, `core_lms/settings.py`,
> `requirements.txt`, and `.env.example`. Production uses only the
> Dockerfile; docker-compose is for local dev / test only.

## Overview

Production stack:
- **Django / Gunicorn** container built from this repository.
- **Managed PostgreSQL** (NeonDB in production) via `DATABASE_URL`.
- **AWS S3** (public read via bucket policy) for both media and
  collected static files.
- **AxiomEngine Go microservice** (sister repo `axiom-reasoning-svc`),
  reachable at `AXIOM_ENGINE_URL`.

## Environment variables

Read at process start. Missing required variables either raise
`ImproperlyConfigured` (AWS) or yield connection failures (DB).

| Variable | Required | Source citation | Notes |
|----------|----------|-----------------|-------|
| `SECRET_KEY` | yes | `core_lms/settings.py:9` | Django secret; default is an insecure placeholder. |
| `DEBUG` | no | `core_lms/settings.py:10` | Parsed as truthy string (`"true"`, `"1"`, `"yes"`). Default `False`. |
| `ALLOWED_HOSTS` | yes | `core_lms/settings.py:11` | Comma-separated; default `"*"`. Restrict in prod. |
| `DJANGO_ENV` | situational | `core_lms/settings.py:82, 212-213` | Set to `"test"` to route DB to `POSTGRES_*` and relax cookie-secure flags. Any other value → `DATABASE_URL`. |
| `DATABASE_URL` | yes (prod) | `core_lms/settings.py:76` | NeonDB DSN including `sslmode=require&channel_binding=require`. |
| `POSTGRES_USER`/`_PASSWORD`/`_HOST`/`_PORT`/`_DB` | when `DJANGO_ENV=test` | `core_lms/settings.py:77-81` | Used only in test env. |
| `AXIOM_ENGINE_URL` | yes | `core_lms/settings.py:157` | Base URL of the Go service; default `http://localhost:8080`. |
| `AWS_ACCESS_KEY_ID` | yes | `core_lms/settings.py:162` | IAM key. |
| `AWS_SECRET_ACCESS_KEY` | yes | `core_lms/settings.py:163` | IAM secret. |
| `AWS_STORAGE_BUCKET_NAME` | yes | `core_lms/settings.py:166` | Default `"core-lms-bucket"`. |
| `AWS_S3_REGION_NAME` | no | `core_lms/settings.py:165` | Default `"us-east-1"`. |
| `CORS_ALLOWED_ORIGINS` | yes (prod) | `core_lms/settings.py:45-51` | Comma-separated; default `"http://localhost:4200"`. |
| `LOG_LEVEL` | no | `core_lms/settings.py:237, 247` | Default `"INFO"`. |
| `SECURE_SSL_REDIRECT` | no | `core_lms/settings.py:211` | Set to `"True"` behind TLS terminator. |
| `PORT` | no | `Dockerfile:20` | Gunicorn bind port; default `8000`. |

AWS-credential guard (`core_lms/settings.py:195-206`): Django raises
`ImproperlyConfigured` if any of `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME` is unset — except
for `test`, `makemigrations`, and `collectstatic` commands.

## Dockerfile (production)

File: `Dockerfile` — 20 lines total.

- Base image: `python:3.11-slim` (line 1).
- ENV: `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`,
  `PYTHONPATH=/app` (lines 3-5).
- WORKDIR `/app` (line 7).
- apt packages installed: `gcc`, `libpq-dev`, `curl`, `jq`
  (line 9-11).
- `pip install --no-cache-dir -r requirements.txt` (line 14).
- `EXPOSE 8000` (line 18).
- **CMD** (line 20):
  ```sh
  sh -c "python manage.py collectstatic --noinput && \
         gunicorn core_lms.wsgi:application \
           --bind 0.0.0.0:${PORT:-8000} \
           --workers 2 \
           --timeout 60"
  ```

Note: production uses **2 Gunicorn workers** with a 60-second timeout.
`docker-compose.yml` uses 3 workers for local dev.

## docker-compose.yml (local / test only)

Services:
- `db` — Postgres 15, `tmpfs:/var/lib/postgresql/data` so data is
  wiped on every restart. Port 5432 exposed on host.
- `web` — this image. Runs `python manage.py migrate && gunicorn
  --bind 0.0.0.0:8000 --workers 3 --timeout 60`. Mounts the repo as
  `/app`. `env_file: .env`. Depends on `db` healthy and `axiom-engine`
  healthy.
- `axiom-engine` — built from `../../../go/axiom-reasoning-svc`. Port
  8080. Receives AWS credentials via env.

All three share a `lms_network` bridge.

## Pre-deployment checklist

Complete before promoting a build:

- [ ] All 48 E2E tests pass in Docker:
      `docker compose exec web bash scripts/e2e_qa.sh`
- [ ] All Django unit+integration tests pass:
      `docker compose exec -e DJANGO_ENV=test web python manage.py test apps/ --verbosity=2`
- [ ] Go unit tests pass in the `axiom-engine` container.
- [ ] NeonDB reachable from the deployment environment (network +
      credentials + SSL).
- [ ] S3 bucket exists with public-read bucket policy on `static/*`,
      `submissions/*`, `resources/*`; CORS allows `GET` from the
      frontend origin.
- [ ] S3 bucket static-files layout:
      the production Dockerfile runs `collectstatic` on start
      (`Dockerfile:20`), which uploads static assets into
      `s3://{bucket}/static/` via the `staticfiles` storage backend
      (`core_lms/settings.py:183-192`). Make sure the IAM policy
      permits both `s3:PutObject` and `s3:GetObject` on
      `{bucket}/static/*`.
- [ ] `AXIOM_ENGINE_URL` resolves to a reachable Go service
      (`http://.../health` returns 200).
- [ ] DB migrations applied manually:
      `python manage.py migrate` — the container does **not** migrate
      on startup.
- [ ] `SECRET_KEY` unique; `ALLOWED_HOSTS` restricted; `DEBUG` unset
      or False; `CORS_ALLOWED_ORIGINS` restricted.
- [ ] `SECURE_SSL_REDIRECT=True` behind an HTTPS terminator.

## Build

```bash
docker build -t core-lms-backend:latest .
```

The Dockerfile installs Python dependencies listed in
`requirements.txt:1-13`:

```
Django==5.1.7
djangorestframework==3.15.2
djangorestframework-simplejwt==5.5.1
django-cors-headers==4.9.0
psycopg2-binary==2.9.10
requests==2.32.3
python-dotenv==1.1.0
drf-yasg==1.21.9
gunicorn==23.0.0
boto3==1.35.99
django-storages==1.14.4
django-filter==24.3
django-ratelimit==4.1.0
```

## Build & run the AxiomEngine Go microservice

The Go service lives in the sister repository `axiom-reasoning-svc`. Its
entrypoint is `cmd/server/main.go` and it binds to `:${PORT:-8080}`.

```bash
# Local build + run (from axiom-reasoning-svc/)
make generate    # runs baml-cli to regenerate Go bindings under baml_client/
make build       # go build -o bin/axiom-server ./cmd/server
make run         # runs ./bin/axiom-server

# Docker (multi-stage; CGO_ENABLED=1 is required for BAML's FFI runtime)
docker build -t axiom-reasoning-svc:latest .
docker run -p 8080:8080 --env-file .env axiom-reasoning-svc:latest

# Or via the repo-local docker compose (this Django repo)
docker compose build axiom-engine
docker compose up axiom-engine
```

The Fiber server registers routes via `handler.RegisterRoutes(app)` in
`cmd/server/main.go` and exposes `GET /health` for orchestrator probes.
The pipeline expects AWS Bedrock credentials (Nova Micro) at runtime.

## Run

```bash
docker run \
  -p 8000:8000 \
  --env-file .env \
  core-lms-backend:latest
```

Container behavior on start (`Dockerfile:20`):
1. `python manage.py collectstatic --noinput` — uploads collected
   static assets to `s3://{bucket}/static/` via django-storages.
2. `gunicorn core_lms.wsgi:application --bind 0.0.0.0:${PORT:-8000}
   --workers 2 --timeout 60`.

Migrations are **not** run on start.

## Migrations

Migrations live in `apps/<app>/migrations/` (committed to git). To
apply them to the production database:

```bash
python manage.py migrate
```

Run this once before starting the app container against a fresh DB or
after pulling schema changes, typically from a CI pipeline or a
jump host. Do not rely on container startup to apply migrations in
production.

## S3 bucket requirements

Configured in `core_lms/settings.py:171-193` via the `STORAGES` dict
(Django 5.x format).

### Default (media) backend — `STORAGES["default"]`
- `backend`: `storages.backends.s3boto3.S3Boto3Storage`
- `default_acl`: `None` (no per-object ACL; bucket policy handles access)
- `querystring_auth`: `False` (direct public URLs)
- `file_overwrite`: `False` (preserves history)

### Static files backend — `STORAGES["staticfiles"]`
- Same backend
- `location`: `"static"` (objects land under `s3://{bucket}/static/...`)
- `querystring_auth`: `False` (static assets served as public URLs)
- `file_overwrite`: `True`

### CORS policy (bucket-level)
Allow `GET` from the production frontend origin(s) and from
`http://localhost:4200` for local development.

### STATIC_URL
`f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/static/"`
(`core_lms/settings.py:173`). Django templates and collected assets
reference this base.

## Observability

- Logs: stdout, format
  `{levelname} {asctime} {module} {message}`
  (`core_lms/settings.py:224-227`).
- `LOG_LEVEL` controls verbosity (default `INFO`); Django core logger
  is pinned at `WARNING` regardless (`core_lms/settings.py:240-244`).
- Health check: `GET /health/` returns
  `{"status": "ok"}`. Suitable for container healthchecks and
  external uptime monitors
  (`apps/learning/viewsets/health_viewset.py:14-18`).

## What not to do

- Do **not** run `docker compose up` in production — compose is for
  local dev and tests only.
- Do **not** set `DEBUG=True` in production
  (`core_lms/settings.py:10`).
- Do **not** use `ALLOWED_HOSTS="*"` in production.
- Do **not** set `DEFAULT_FILE_STORAGE=InMemoryStorage` outside tests.
- Do **not** apply migrations automatically on container start.
- Do **not** commit credentials.
