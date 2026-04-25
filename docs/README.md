# AxiomLMS Core Backend

AI-driven Learning Management System with adaptive study plans powered by
GraphRAG reasoning.

## Tech Stack

- Django 5.1.7
- Django REST Framework
- PostgreSQL (NeonDB)
- AxiomEngine (Go microservice)
- AWS S3
- JWT Authentication

## Quick Start

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd core-lms-backend
   ```

2. Copy the example environment file and fill in credentials:

   ```bash
   cp .env.example .env
   ```

3. Build and start the services:

   ```bash
   docker compose up --build
   ```

4. Seed the database with demo data:

   ```bash
   docker compose exec web python manage.py seed_data
   ```

5. Open the interactive API documentation:

   ```
   http://localhost:8000/swagger/
   ```

6. Demo credentials:

   | Role | Username | Password |
   |------|----------|----------|
   | Tutor | `prof_martinez` | `demo_pass_2026` |
   | Student | `alice` | `demo_pass_2026` |

## Documentation

| Document | Description |
|----------|-------------|
| [01_vision.md](01_vision.md) | System purpose, actors, scope, and quality attributes (security, availability, maintainability, observability). |
| [02_use_cases.md](02_use_cases.md) | High-level index of CU-01 through CU-13 (one row per use case, with primary endpoint and owning app). |
| [03_domain_model.md](03_domain_model.md) | Class diagram, relationships, and per-model field descriptions for all 22 entities. |
| [04_architecture.md](04_architecture.md) | Deployment topology, Django/Go components, communication patterns, error handling, and known contract violations. |
| [05_database_schema.md](05_database_schema.md) | Table-by-table column reference, type mappings, soft-delete policy, and migration policy. |
| [06_api_reference.md](06_api_reference.md) | Endpoint-by-endpoint reference with permissions, request/response shapes, and status codes. |
| [07_testing.md](07_testing.md) | Four-layer test strategy (unit, integration, E2E bash, Go), test files, and run commands. |
| [08_deployment.md](08_deployment.md) | Environment variables, Dockerfile, S3 bucket requirements, Go service build, and pre-deployment checklist. |
| [use_cases/](use_cases/) | Detailed end-to-end flow documentation (one file per use case: CU-01_auth.md through CU-13_certificate.md). |
