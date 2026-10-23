# Implementation progress

## Phase 1 — inspection and scaffold

Implemented:
- Inspected the repository, parent instruction paths, hidden workspace directories, and tools.
- Confirmed Git was already installed; did not reinstall or reinitialize it.
- Created package, test, migration, workflow, script, documentation, and infrastructure directories.
- Added Python project metadata, dependency ranges, Ruff configuration, and Pytest markers.
- Added environment template, Git exclusions, Docker context exclusions, and LF rules for WSL scripts.
- Documented architecture, environment variables, phased setup, troubleshooting, and interview concepts.

Why this matters: a predictable layout, explicit tooling contract, and secret exclusions
make changes reviewable and reduce deployment mistakes before application code is added.

Inspection evidence (2026-10-20):

| Command | Actual result |
| --- | --- |
| `git --version` | Git 2.43.0 |
| `git status --short --branch` | Initialized `main`, no commits or existing project files |
| `git remote -v` | No remote configured |
| `git config --get user.name` / `user.email` | Both configured; values omitted here |
| `python3 --version` | Python 3.12.3 |
| `python3 -m pip --version` | pip 24.0 |
| Python imports of `venv`, `ensurepip` | Available |
| `docker --version` | Docker 29.1.3 |
| `docker compose version` | Compose 2.40.3 |
| `docker info --format '{{.ServerVersion}}'` | Sandbox socket permission denied; approved check outside sandbox returned 29.1.3 |
| `terraform version` | Not installed; installation guidance recorded in infra README |
| `command -v curl ss ps df free journalctl` (individual checks) | All present |

Scaffold verification:
- `python3 -m venv .venv`: passed; local virtual environment created and ignored.
- `.venv/bin/python` with `tomllib` and `import app`: passed; project metadata parses and package imports.
- `git diff --check`: passed before staging; staged whitespace check also required before commit.
- `git check-ignore` verified `.env`, `.env.production`, `.venv/bin/python`,
  `backups/example.dump`, Terraform state, private tfvars, overrides, and `.aws/credentials` are ignored.
- No application tests were run: tests and application behavior begin in Phase 2.

Phase 1 is complete. Run the prerequisite commands in README.md to repeat the
environment checks. Phase 2 implementation is recorded below.

## Remaining work

- Phase 3 runtime verification: image build, Compose startup, health checks, and persistence after restart.
- Phase 4 runtime verification: real GitHub Actions execution; package artifact hashes remain unpinned.
- Phase 5: health/readiness, structured logs, safe backup and isolated restore verification.
- Phase 6: optional local Docker-network Terraform configuration and checks.
- Phase 7: complete runtime verification, persistence/recovery drill, final documentation.

Deployment verification pending: image build, Compose startup, database
health in Compose, persistence after container restart, backup/restore,
Terraform fmt/validate, and real GitHub workflow execution. None are claimed successful.
Terraform checks additionally require installation. AWS remains optional and unprovisioned.

No data deleted, cloud resources created, images published, or changes pushed.


## Phase 2 — API and PostgreSQL integration

Implemented:
- FastAPI application factory with lifespan-managed SQLAlchemy engine and session cleanup.
- PostgreSQL-only environment configuration, secret redaction, connection pre-ping,
  connection timeout, and SQL parameter hiding.
- Task persistence model and explicit Alembic `0001` migration. Startup does not mutate schema.
- CRUD endpoints with Pydantic validation, bounded positive IDs, title trimming,
  timezone-aware timestamps, 201/204/404/422 responses, and sanitized database errors (503).
- Basic process liveness and database readiness endpoints; structured request logging
  and deployment health checks remain in Phase 5.
- Unit tests plus a disposable-PostgreSQL integration test covering CRUD and persistence
  across a fresh application instance. Integration tests require TEST_DATABASE_URL.
- README local setup and controlled migration instructions in migrations/README.md.

Why this matters: the service now has a schema lifecycle independent of process startup,
explicit configuration, predictable API failures, and a verifiable persistence contract.
This is the application foundation for container deployment in Phase 3.

Verification (2026-10-21):
- `python3 -m compileall -q app migrations tests`: passed.
- `.venv` dependencies are installed, including FastAPI, SQLAlchemy, Alembic,
  psycopg, Pytest, and Ruff.
- `ruff check .`, `git diff --check`, and Python compilation: passed.
- In the restricted assistant environment, `TestClient` startup hangs, including
  for a minimal FastAPI app. The same smoke check passed in the user's regular WSL
  terminal, and `python -m pytest -m unit -q` passed there: 8 passed, 1 integration
  test deselected. Added `httpx2` to development dependencies for fresh installs.
- In the user's WSL terminal, the disposable PostgreSQL container started, accepted
  connections, and `alembic upgrade head` completed. `python -m pytest -m integration
  -q` passed: 1 passed, 8 unit tests deselected.
- Docker socket access remains unavailable to the assistant environment, so runtime
  database verification was performed by the user in WSL.
- No Dockerfile/Compose app build, backup/restore, Terraform, or real GitHub Actions
  run is claimed in this phase.

## Phase 3 — container deployment implementation

Implemented:
- Added a multi-stage Dockerfile with a pinned Python base image and non-root runtime user.
- Added Compose services for PostgreSQL, the API, and an explicitly invoked Alembic migration.
- Kept PostgreSQL off host ports, bound the API to localhost, and added a private network
  plus a named database volume. The API uses a separate host-facing network so the
  localhost-published port is reachable while the database remains isolated.
- Added database and API liveness health checks and documented controlled startup,
  migration, and volume lifecycle commands.

Verification:
- `docker compose --env-file .env.example config --quiet`: passed.
- `git diff --check`: passed.
- In the user's WSL terminal, the image build completed, PostgreSQL and API containers
  became healthy, and the API was published as `127.0.0.1:8000->8000/tcp`.
- `GET /health` and `GET /ready` both returned HTTP 200 from the user's WSL terminal.
- Created task ID 1, restarted the PostgreSQL container, waited for it to become
  healthy, and retrieved the same task afterward. Database volume persistence passed.

## Phase 4 — continuous integration implementation

Implemented:
- Added a GitHub Actions workflow for linting, database migration, unit and PostgreSQL
  integration tests, and a Docker image build.
- Restricted workflow permissions to repository read access and used an isolated
  PostgreSQL service with disposable credentials.
- Added Linux/Python 3.12 runtime and development dependency locks; Docker and CI now
  install from the matching lock file.
- Documented workflow triggers and checks in README.md.

Verification remains pending: no hosted GitHub Actions run has been observed yet.
Terraform checks remain outstanding; Terraform configuration is planned for Phase 6.

Dependency versions are pinned in `requirements.lock` and `requirements-dev.lock` for
Python 3.12 on Linux. The lock files were resolved from the project's installed
environment; artifact hashes are not pinned.

## Phase 5 — operations implementation

Implemented:
- Added JSON request logs with request IDs, HTTP method/path/status, and request duration.
- Added configurable log levels and echoed the selected request ID in the response.
- Added private custom-format backups with archive validation and a restore script that
  creates a new `restore_verify_` database without overwriting existing databases.
- Added database verification and documented the backup and restore workflow.

Verification remains pending: scripts and request logs have not been exercised against
the running Compose stack. A successful backup/restore drill remains to be completed.
README.md now documents a manual seven-day local retention policy and an off-machine
copy recommendation for important data. Backup and restore scripts accept
`COMPOSE_ENV_FILE`, which supports stacks started with `--env-file .env.example`.

Verification update (2026-10-23):
- `.venv/bin/ruff check .`, `docker compose --env-file .env.example config --quiet`,
  `bash -n scripts/backup.sh scripts/restore.sh scripts/verify.sh`, and
  `git diff --check`: passed in the assistant shell.
- `timeout 45 .venv/bin/python -m pytest -m unit -q` timed out without output in the
  restricted assistant shell. This environment has previously hung during FastAPI
  `TestClient` startup; the user's WSL unit tests passed earlier in Phase 2.
- Docker socket access is denied in this shell, so the live backup/restore drill must
  run from the user's Ubuntu terminal against the already-running Compose stack.
- The GitHub Actions workflow has not run: this shell cannot reach the GitHub API, and
  the GitHub CLI credential available here is invalid even though the user's Ubuntu
  terminal reports a valid `hadiw-dev` login. Push from that authenticated terminal.
- Package versions are pinned in the lock files, but artifact hashes are not.
