# cloud-deployment-platform

A beginner-friendly DevOps portfolio project: a task management API with persistent
PostgreSQL storage, containers, automated checks, backup recovery, and local Infrastructure as Code.

**Current status: Phase 4 and 5 implementation is present; hosted CI and the live backup/restore drill still need verification.**
See [PROGRESS.md](PROGRESS.md) for actual checks and the remaining phases.

The project addresses a practical problem: delivering a small API repeatably, proving
that its data survives restarts, and understanding how to diagnose and recover failures.
It demonstrates Python backend development, Linux, Docker, CI, database operations,
secrets handling, and Terraform without requiring AWS credentials or cloud spending.

## Planned architecture

```mermaid
flowchart LR
    User[Local client] -->|127.0.0.1:8000| API[FastAPI container]
    API -->|Private Docker network| DB[PostgreSQL container]
    Migration[Controlled Alembic step] --> DB
    DB --> Volume[(Named data volume)]
    DB --> Backup[Protected local backups]
    CI[GitHub Actions validation] --> Image[Docker image build]
    TF[Optional local Terraform] -.-> Network[Dedicated Docker network]
```

Technology: Python 3.12+, FastAPI, PostgreSQL, SQLAlchemy 2, Alembic, Pydantic,
Pytest, Ruff, Docker Compose, GitHub Actions, and Terraform. Container base images and
Python dependency versions are pinned. The lock files target Python 3.12 on Linux and
do not pin package artifact hashes. Refresh both lock files together whenever runtime
or development dependencies change.

## Project structure

```text
cloud-deployment-platform/
├── .github/workflows/       # Phase 4 workflow
├── app/                    # Phase 2 API package
├── docs/
│   ├── architecture.md
│   ├── interview-guide.md
│   └── troubleshooting.md
├── infra/terraform/        # Phase 6 optional local network
├── migrations/versions/    # Phase 2 Alembic revisions
├── scripts/                # Phase 5 operational scripts
├── tests/
│   ├── integration/
│   └── unit/
├── .dockerignore
├── .env.example
├── .gitattributes
├── .gitignore
├── PROGRESS.md
├── README.md
└── pyproject.toml
```

## Prerequisites and Phase 1 setup

Use Ubuntu WSL2 with Python 3.12+, Git, and Docker Desktop WSL integration.
Terraform is optional until Phase 6. No AWS account is needed.

```bash
git --version
python3 --version
docker --version
docker compose version
docker info
python3 -m venv .venv
source .venv/bin/activate
```

If Python's venv module is missing on Ubuntu, install `python3-venv` using apt.
If Docker cannot connect, start Desktop and check WSL integration; do not make the
Docker socket world-writable. Terraform installation guidance is in
[infra/terraform/README.md](infra/terraform/README.md).

Install the locked development dependencies using `python -m pip install -r requirements-dev.lock`.
See the Phase 3 setup below to run the API and PostgreSQL with Compose.

## Environment variables

Copy `.env.example` to `.env` and choose a fresh local password.
Keep the password in `DATABASE_URL` consistent with `POSTGRES_PASSWORD`.
URL-encode special characters in the URL password. Never commit `.env`.

| Variable | Purpose | Example |
| --- | --- | --- |
| `POSTGRES_DB` | Database initialized by PostgreSQL | `tasks` |
| `POSTGRES_USER` | Local database role | `tasks_app` |
| `POSTGRES_PASSWORD` | Local development password | Fake value in `.env.example` |
| `DATABASE_URL` | SQLAlchemy psycopg URL | Compose hostname `db`, port `5432` |
| `LOG_LEVEL` | Structured application log threshold | `INFO` |

The initial local PostgreSQL role will need schema-management privileges for migrations.
A future production deployment should separate migration and application roles.

## API and testing

The API provides `GET /health`, `GET /ready`, `GET /tasks`, `GET /tasks/{id}`,
`POST /tasks`, `PUT /tasks/{id}`, and `DELETE /tasks/{id}`.
Tasks have id, title, description, completed, created_at, and updated_at fields.
PUT replaces the task: title is required; omitted description/completed reset to null/false.
POST returns 201 with a Location header, DELETE returns 204, missing IDs return 404,
and invalid input returns 422. Database failures return a sanitized 503.

After starting the API:

```bash
curl -f http://localhost:8000/health
curl -f http://localhost:8000/ready
curl -f -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"Verify deployment","description":"Portfolio demo","completed":false}'
curl -f http://localhost:8000/tasks
python -m pytest -m unit
python -m pytest -m integration
ruff check .
```

Integration tests require `TEST_DATABASE_URL` pointing to an isolated, migrated
PostgreSQL database. They skip explicitly when it is absent and never fall back to
`DATABASE_URL`. They create and clean up only their own task records.

## Phase 2 local setup (host-run API)

For host-run development, use an existing disposable PostgreSQL instance or start a
dedicated development container. The example values below are
public, disposable development values; do not reuse them in production.

```bash
source .venv/bin/activate
python -m pip install -r requirements-dev.lock
cp -n .env.example .env
# Edit .env: use 127.0.0.1:55432 instead of db:5432 in DATABASE_URL.
# Match the database, role, and password to this disposable database.
docker run -d --name cloud-platform-phase2-db \
  --tmpfs /var/lib/postgresql/data \
  -e POSTGRES_DB=tasks_phase2 -e POSTGRES_USER=tasks_app \
  -e POSTGRES_PASSWORD=phase2_disposable_only \
  -p 127.0.0.1:55432:5432 postgres:17.6-bookworm
docker exec cloud-platform-phase2-db pg_isready -U tasks_app -d tasks_phase2
# Wait until pg_isready reports accepting connections.
# .env DATABASE_URL for this example:
# postgresql+psycopg://tasks_app:phase2_disposable_only@127.0.0.1:55432/tasks_phase2
alembic upgrade head
alembic current
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The temporary PostgreSQL storage above is deliberately disposable: stopping this
container loses its data. Phase 3 supplies the persistent named-volume deployment.
The API never runs migrations on startup. Run `alembic upgrade head` as a separate
controlled step before serving traffic. `alembic downgrade` can delete data and
should only be used after deliberate review and backup.

For integration tests, set `TEST_DATABASE_URL` through your shell environment
without embedding production credentials in command history. With the disposable
`.env` configured as above, this command safely loads the same test-only URL:

```bash
python -m pytest -m unit
python - <<'PYTEST'
import os
import subprocess
import sys
from app.config import get_settings

# Use only with the disposable development .env described above.
os.environ["TEST_DATABASE_URL"] = get_settings().database_url.get_secret_value()
raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "-m", "integration"]))
PYTEST
ruff check .
```

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.
`/health` checks the process; `/ready` performs a database query (200 or 503).
Readiness checks connectivity, not schema version; check `alembic current` during deployment.

## Phase 3 container deployment

The runtime image uses a pinned Python base image, a separate build stage, and a
non-root user. Compose publishes the API only on `127.0.0.1`; the API connects to a
host-facing network and a private backend network, while PostgreSQL has no host port
and joins only the private backend. Its named volume persists across ordinary
container recreation. `.env.example` provides disposable local values; replace the
password and keep `DATABASE_URL` synchronized with `POSTGRES_PASSWORD`. URL-encode
special characters in the URL password, and keep the Compose hostname as `db`.

```bash
cp -n .env.example .env
# Edit .env and set a fresh local password in both locations.
docker compose build
docker compose up -d db
docker compose run --rm migrate
docker compose up -d api
docker compose ps
curl -f http://127.0.0.1:8000/health
curl -f http://127.0.0.1:8000/ready
```

The `migrate` service runs only when explicitly requested and never runs as part of
API startup. For later schema updates, start the database, run the migration command,
then recreate the API as needed. The healthcheck checks process liveness; `/ready`
checks database connectivity.

If port 8000 is already in use, set `API_PORT` in `.env` to another local port.
The `db` service uses a named volume called `postgres_data`. `docker compose down`
preserves it; `docker compose down -v` deletes database data and should only be used
after deliberate review and backup.

## Container lifecycle

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=100
docker compose down
```

`down` removes the stack's containers and managed networks while retaining named
volumes. `docker compose down -v` also deletes named volumes and their PostgreSQL
data. Review the data impact before running it.

## Phase 4 continuous integration

The GitHub Actions workflow in `.github/workflows/ci.yml` installs pinned versions from
`requirements-dev.lock` and runs Ruff, migrations,
unit tests, PostgreSQL integration tests, and a Docker image build on pushes, pull
requests, and manual dispatch. CI uses a disposable PostgreSQL service and read-only
repository permissions. No real GitHub Actions run has been checked yet. Terraform
formatting and validation will be added once its configuration exists in Phase 6.
Optional GHCR publishing will use minimal permissions and trusted events, separately
from validation. Deployment to AWS will remain manual.

## Remaining operational phases

## Phase 5 operations

The API writes one JSON request log per request with request ID, method, path, status,
and duration. A valid incoming `X-Request-ID` is preserved; invalid or missing values
are replaced. The response returns the selected ID in `X-Request-ID`. `LOG_LEVEL` sets
the application log threshold.

Run backups from this project checkout with the Compose stack running:

```bash
scripts/backup.sh
scripts/restore.sh backups/tasks-YYYYMMDDTHHMMSSZ.dump restore_verify_drill
scripts/verify.sh tasks
```

`backup.sh` writes a private, archive-validated custom-format dump under `backups/`.
`restore.sh` requires a new `restore_verify_` database name, refuses to overwrite an
existing database, restores the archive, and verifies the schema. It leaves the
verification database in place for inspection; remove it only after confirming the
name and contents. Store backups with restricted access and define a retention policy;
backup files are excluded from Git.

Phase 6 adds the optional Docker network using Terraform. The Compose-only path
will remain usable. See [infrastructure notes](infra/terraform/README.md).

Phase 7 verifies the complete workflow and expands these instructions with actual
commands and evidence. Monitoring currently consists only of the documented design;
see [troubleshooting](docs/troubleshooting.md) and [architecture](docs/architecture.md).

## Security, future AWS approach, and limitations

The planned API is an unauthenticated local learning service. Bind it only to localhost.
Do not expose it to the Internet without authentication, TLS, rate controls, and review.
Production secrets belong in a managed secret store, never in Git or Docker images.
Ignored state and backup files still require protection on disk.

A future AWS proposal could use ECS/Fargate with an application load balancer, private
RDS PostgreSQL, Secrets Manager, and managed logs. This is a proposal, not executable
infrastructure. Obtain approval and estimate costs before creating cloud resources;
databases, load balancers, logs, and retained backups can continue incurring charges.
Cleanup must inventory resources and retained storage before deleting anything.

Known limitations: containers, CI, backup/restore, and Terraform remain in later phases.
There is no authentication, TLS, metrics platform,
or high availability. Future improvements include those controls, recovery drills,
artifact hash verification, and release promotion. Kubernetes, microservices, Redis, and a
frontend remain outside scope.

For interview explanations, read [docs/interview-guide.md](docs/interview-guide.md).
Be ready to explain why a volume is not a backup, why readiness differs from liveness,
why CI should not deploy untrusted changes, and why Terraform state must be protected.
