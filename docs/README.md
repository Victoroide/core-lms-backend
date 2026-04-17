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
| [01_vision.md](01_vision.md) | System Vision and Quality Attributes |
| [02_use_cases.md](02_use_cases.md) | Use Case Specifications |
| [03_domain_model.md](03_domain_model.md) | Domain Model and Relationships |
| [04_architecture.md](04_architecture.md) | System Architecture |
| [05_database_schema.md](05_database_schema.md) | Database Schema Reference |
| [06_api_reference.md](06_api_reference.md) | API Endpoint Reference |
| [07_testing.md](07_testing.md) | Testing Strategy and Commands |
| [08_deployment.md](08_deployment.md) | Production Deployment Guide |
