# Deployment Guide

This document describes how to deploy the AxiomLMS Core Backend to a production environment.

## Overview

Production uses only the `Dockerfile`. **Docker Compose is for local development and test runs only** -- it is not a production deployment tool in this project.

The production stack:
- **Django/Gunicorn** application container (this repository)
- **NeonDB** (managed PostgreSQL) for the database
- **AWS S3** for file storage (private ACL with pre-signed URLs)
- **AxiomEngine Go microservice** for adaptive-plan generation (separate repository)

## Environment Variables

All variables are read from the process environment. Required variables must be set or Django will fail to start (AWS credentials) or database connections will fail (NeonDB).

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| DJANGO_ENV | yes | Set to `production` or leave unset for NeonDB routing. Use `test` only inside Docker Compose for local testing. | production |
| SECRET_KEY | yes | Django secret key, 50+ random characters. Never reuse a development key. | (random) |
| DEBUG | no | Leave unset or set to `False` in production. | False |
| ALLOWED_HOSTS | yes | Comma-separated hostnames allowed by Django. | api.example.com |
| DATABASE_URL | yes | Full NeonDB connection string including sslmode and channel_binding query params. | postgresql://user:pass@host/db?sslmode=require&channel_binding=require |
| AWS_ACCESS_KEY_ID | yes | IAM key for S3 access. | AKIA... |
| AWS_SECRET_ACCESS_KEY | yes | IAM secret for S3 access. | (secret) |
| AWS_STORAGE_BUCKET_NAME | yes | S3 bucket name. | axiom-lms-files |
| AWS_S3_REGION_NAME | yes | S3 region. | us-east-1 |
| AXIOM_ENGINE_URL | yes | Base URL of the AxiomEngine Go microservice. | https://axiom.example.com |
| CORS_ALLOWED_ORIGINS | yes | Comma-separated frontend origins allowed by CORS. | https://app.example.com |
| LOG_LEVEL | no | Python logging level, default INFO. Options: DEBUG, INFO, WARNING, ERROR, CRITICAL. | INFO |
| SECURE_SSL_REDIRECT | no | Set to `True` behind an HTTPS terminator to force HTTP-to-HTTPS redirects. | True |

## Pre-deployment Checklist

Complete every item before promoting a build to production.

- [ ] All 48 E2E tests passing in Docker: `docker compose exec web bash scripts/e2e_qa.sh`
- [ ] All Django unit and integration tests passing: `docker compose exec -e DJANGO_ENV=test web python manage.py test apps/ --verbosity=2`
- [ ] Go unit tests passing: `go test ./...` (or via the axiom-engine builder image)
- [ ] NeonDB reachable from the target deployment environment (network, credentials, SSL)
- [ ] S3 bucket exists with **private** ACL
- [ ] S3 bucket CORS policy allows GET from the frontend origin for pre-signed URL access
- [ ] `AXIOM_ENGINE_URL` points to a reachable Go service
- [ ] Migrations applied manually on the target DB: `python manage.py migrate` (the container does not run migrations on startup in production)
- [ ] `SECRET_KEY` is unique and not shared with development
- [ ] `ALLOWED_HOSTS` restricted to actual production hostnames (no `*`)
- [ ] `CORS_ALLOWED_ORIGINS` restricted to production frontend origins
- [ ] `DEBUG` is unset or `False`
- [ ] `SECURE_SSL_REDIRECT=True` when terminating TLS at the edge

## Build

```
docker build -t core-lms-backend:latest .
```

The Dockerfile installs Python dependencies, copies the source tree, and sets `PYTHONPATH=/app`. The default `CMD` runs Gunicorn with three workers on port 8000.

## Run

```
docker run -p 8000:8000 --env-file .env core-lms-backend:latest
```

The container does **not** run migrations on startup in production. Migrations are a manual step (see checklist) to avoid accidental schema changes during rolling restarts or autoscaling events.

## Migrations

Migrations are committed to the repository under `apps/<app_name>/migrations/`. To apply them to the production database:

```
python manage.py migrate
```

This must run **once before** starting the application container against a new or migrated database, typically from CI/CD or a secure jump host. Never rely on container startup to apply migrations in production.

## S3 Bucket Requirements

- ACL: `private` (set in settings via `AWS_DEFAULT_ACL = "private"`)
- Pre-signed URLs: enabled (set via `AWS_QUERYSTRING_AUTH = True`)
- URL expiry: 3600 seconds (set via `AWS_QUERYSTRING_EXPIRE = 3600`)
- CORS: allow `GET` from every frontend origin that needs to download files

## Observability

- Application logs stream to stdout with the format `LEVEL TIMESTAMP module message` (see `LOGGING` in `core_lms/settings.py`).
- `LOG_LEVEL` controls verbosity.
- The `/health/` endpoint returns `{"status": "ok"}` and is suitable for container healthchecks and external uptime monitors.

## What Not To Do

- Do **not** run `docker compose up` in production.
- Do **not** set `DEBUG=True` in production.
- Do **not** use `ALLOWED_HOSTS=*` in production.
- Do **not** enable `DEFAULT_FILE_STORAGE=django.core.files.storage.InMemoryStorage` outside of tests.
- Do **not** apply migrations automatically on container startup.
- Do **not** commit credentials to the repository.
