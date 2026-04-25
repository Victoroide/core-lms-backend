# Core LMS Backend

## System Abstract

The Core LMS Backend is an enterprise-grade Django monolithic architecture tasked with orchestrating user enrollment, cryptographic certification, and quantitative assessment telemetry logic. The platform operationalizes a deterministic split-directory topology, delegating autonomous AI reasoning cycles to the external `AxiomEngine` Go microservice structure. Through synchronous HTTP invocation strategies, the microservice bridge parses failed topological evaluation nodes and autonomously constructs targeted adaptive study paths.

## Prerequisites & Toolchain

The architectural runtime environment formally necessitates the following configuration sequence:

| Component | Target Version | Description |
|-----------|----------------|-------------|
| Python | 3.11+ | Primary application scripting execution layer |
| Django | 5.x | High-level MVC mapping protocol array |
| PostgreSQL | 15+ | Acid-compliant primary relational datastore |
| Docker | 24.x | Containerization topological boundary engine |

## Environment Configuration

Deployment configurations resolve hierarchically through the sequence bound in the localized `.env` index format:

| Sequence Variable | Objective Binding | Logical Default |
|-------------------|-------------------|-----------------|
| `SECRET_KEY` | Django cryptographic cryptographic rotation key | `django-insecure-change-me` |
| `DEBUG` | Verbosity execution tracing scalar | `False` |
| `POSTGRES_DB` | Relational target database namespace | `core_lms` |
| `POSTGRES_USER` | Relational execution identity mapping | `lms_admin` |
| `POSTGRES_PASSWORD`| Target authentication structure segment | `lms_secret_2026` |
| `POSTGRES_HOST` | Operational TCP socket address layout | `localhost` |
| `POSTGRES_PORT` | Operational TCP parameter port mapping | `5432` |
| `AXIOM_ENGINE_URL`| Synchronous Go microservice target array | `http://localhost:8080` |

## Execution Playbook

Execute the following sequential infrastructure layout formats to synthesize the operational target layout:

```bash
# 1. Synthesize the localized isolation layer framework
python -m venv .venv

# 2. Activate the sequence topological hierarchy mapping
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows execution targets

# 3. Synchronize package constraints parameters
pip install -r requirements.txt

# 4. Enforce structural schema alignment via ORM mapping logic
python manage.py makemigrations
python manage.py migrate

# 5. Populate idempotent baseline structural validation node structures
python manage.py seed_data

# 6. Execute local mapping execution
python manage.py runserver
```

For orchestrated containerization execution constraints bindings:

```bash
docker-compose up --build
```

## Swagger UI Access

The framework operationalizes dynamic OpenAPI documentation formats via `drf-yasg`. 

1. **Topological Navigation**: Direct your operational agent targeting sequence to [http://localhost:8000/swagger/](http://localhost:8000/swagger/).
2. **Obtain Mapping Identification**: Target the `POST /api/v1/auth/token/` operational payload segment using authorized topological login credentials.
3. **Persist Execution Constraints**: Copy the resulting structural `access` object hash array constraint.
4. **Authorize Interactor Sequence**: Locate the dynamic `Authorize` logic button object layout within the web sequence, and synthesize the authentication format exactly as `Bearer <your_access_token>`.
5. **Execution Confirmation**: Engage the operational sequence structural save button syntax layout object maps array.

## Code Quality

This project enforces PEP 8 via `flake8`. Configuration lives in [`.flake8`](.flake8) at the repo root (max line length 100; auto-generated `migrations/` are excluded).

Install dev dependencies (uses [`requirements-dev.txt`](requirements-dev.txt), which pulls in `requirements.txt`) and run the linter:

```bash
python -m pip install -r requirements-dev.txt
python -m flake8
```

Expected: no output, exit code `0`.
