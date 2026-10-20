# Architecture and implementation decisions

Status: design for the remaining phases, not a deployed system.

The application is a single synchronous FastAPI service using SQLAlchemy 2 sessions
and psycopg to connect to PostgreSQL. Alembic owns schema changes; application startup
must not create tables or run migrations implicitly. A controlled deployment command
will run migrations before the API starts serving traffic.

Compose will expose only `127.0.0.1:8000`. PostgreSQL will have no host port and will
persist data in a named volume. A private service network carries database traffic.
Docker health checks and database dependency conditions aid startup; the application
still needs to handle database outages after startup.

`/health` will report process liveness independently of PostgreSQL. `/ready` will check
database connectivity and return 503 when the service cannot use its database.
CRUD operations will use validation, explicit transaction handling, and useful status codes.
Logs will contain request IDs, durations, method, path, and status without credentials
or request bodies. Containers will run the API as a non-root user and forward shutdown signals.

Unit tests will isolate business logic and validation. Integration tests will use a
disposable PostgreSQL database and real migrations. CI will validate changes without
deploying them. Optional GHCR publishing will be separated and limited to trusted events.

Backup scripts will use PostgreSQL custom-format dumps and `pg_restore`. Restoration
must first be verified against an isolated development database. Backups require
restricted permissions and a retention policy; they must stay out of Git and images.

No Kubernetes, Redis, frontend, or additional application services are planned.
