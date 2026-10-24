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

- Phase 6: Terraform formatting, provider initialization, validation, and plan review
  remain. Formatting passes, but provider initialization is blocked by HashiCorp's
  regional access restriction in the user's Ubuntu environment.
- Phase 7: final review is in progress; all local checks that do not require Terraform
  pass, while provider-dependent Terraform checks remain unavailable.

Phases 3-5 runtime verification is complete. AWS remains optional and unprovisioned.

At Phase 1 close, no data had been deleted, cloud resources created, images published,
or changes pushed.


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

Verification (2026-10-23): pushed commit `71df29e`; GitHub Actions run `39995887331`
completed successfully. The workflow passed lint, migration, unit tests, PostgreSQL
integration tests, and Docker image build. Terraform CI checks were added in Phase 6.

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

Verification (2026-10-23):
- Created and archive-validated `backups/tasks-20261023T175016Z.dump`.
- Restored into the new `restore_verify_phase5_2` database. Verification reported
  `tasks=1` and an Alembic revision; the original `tasks` database also verified with
  `tasks=1` and an Alembic revision.
- `GET /health` returned HTTP 200 and echoed `X-Request-ID: phase5-check-001`.
- The API emitted a JSON request log containing that same request ID, method, path,
  status code, and duration.

README.md now documents a manual seven-day local retention policy and an off-machine
copy recommendation for important data. Backup and restore scripts accept
`COMPOSE_ENV_FILE`, which supports stacks started with `--env-file .env.example`.

Verification update (2026-10-23):
- `.venv/bin/ruff check .`, `docker compose --env-file .env.example config --quiet`,
  `bash -n scripts/backup.sh scripts/restore.sh scripts/verify.sh`, and
  `git diff --check`: passed in the assistant shell.
- GitHub Actions run `39995887331` completed successfully on pushed commit `71df29e`,
  including the workflow's unit and PostgreSQL integration tests and Docker image build.
- The backup/restore, source database, HTTP request ID, and JSON log checks passed in
  the user's Ubuntu terminal; evidence is recorded under Phase 5 above.
- Package versions are pinned in the lock files, but artifact hashes are not.

## Phase 6 — local Terraform network

Implemented:
- Added a Terraform-managed Docker bridge network for the API frontend connection,
  with project and ownership labels. The Docker provider version is pinned to 4.6.0.
- Added `compose.terraform.yaml`, which replaces the Compose-managed frontend network
  with the Terraform network as an external resource. The default Compose path is unchanged.
- Added a GitHub Actions job for Terraform formatting, provider initialization, and
  configuration validation.
- Documented local setup and the plan/apply/destroy sequence. Terraform apply and destroy
  remain deliberate operator actions; no Docker network has been created by Terraform.

Verification:
- `docker compose -f compose.yaml -f compose.terraform.yaml --env-file .env.example
  config --quiet`: passed; resolved configuration uses the external Terraform network.
- At implementation time, Terraform was not installed in the assistant shell. The
  workflow defines format, init, and validate checks, but no result for that job is
  available yet.

Update (2026-10-24): The user installed Terraform in Ubuntu/WSL. `terraform fmt -check`
passed, but `terraform init -backend=false` could not discover the provider registry.
Both registry endpoints returned HTTP 404 with `x-amzn-waf-reason: geo` and an explicit
HashiCorp regional availability page. Provider installation, validation, and planning
are therefore unavailable from this environment. Do not use a VPN, proxy, or remote
runner to mask the region. The optional Compose-only deployment remains unaffected.

## Phase 7 — final review (in progress)

Reviewed the project status, Terraform instructions, CI workflow, and final README claims.
Updated the README to distinguish completed local checks from pending Terraform CLI
verification, and removed a duplicated Terraform state warning.

Verification (2026-10-24):
- `docker compose --env-file .env.example config --quiet` and the Terraform override
  config both passed.
- `.venv/bin/ruff check .`, Python compilation, `bash -n` for the operational scripts,
  and `git diff --check` passed.
- The user has Terraform installed in Ubuntu/WSL, but the provider registry returned a
  regional restriction response, so initialization and downstream validation/plan
  checks could not pass there. `gh run list` could not reach `api.github.com`, so remote
  CI status could not be checked from the assistant shell.
- No Terraform apply/destroy, cloud provisioning, or destructive database operation
  was performed.
