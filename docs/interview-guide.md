# Interview guide

Phase 1 establishes these design choices; runtime examples will be added as each
feature is implemented and verified.

| Topic | Explanation and project example |
| --- | --- |
| Containers vs virtual machines | A VM has its own guest kernel. Linux containers share a kernel while isolating processes. Docker Desktop provides the Linux environment used by containers on Windows. |
| Images vs containers | An image is a packaged filesystem and startup configuration. A container is a running instance with its own writable layer. Rebuilding an API image does not migrate the database. |
| Volumes | A named PostgreSQL volume persists beyond the lifetime of a container. It is storage, not a backup. |
| Networking | Compose services discover each other by service name. The API connects to `db:5432`; localhost inside a container means that container itself. |
| Compose | A declarative definition of the local services, networks, volumes, and health checks. |
| CI vs CD | CI verifies each change; CD prepares or deploys releases. This project will validate changes without automatically deploying to AWS. |
| GitHub Actions | Repository workflows execute jobs on runners. Permissions and trusted triggers control optional image publishing. |
| PostgreSQL persistence | Transactions protect updates; a named volume retains database files; Alembic tracks schema revisions. |
| Liveness vs readiness | Liveness answers whether the process is running. Readiness answers whether it can serve database-backed requests. |
| Observability | Structured logs and request IDs help trace failures. Health checks provide signals, but are not a full metrics or alerting system. |
| Infrastructure as Code | Versioned configuration describes infrastructure. The optional Terraform phase will manage a local Docker network. |
| Terraform state | State maps configuration to real resources and can contain secrets. Review plans and protect state before apply or destroy. |
| Secrets | Local environment files must be excluded from Git. Production should use a secret manager and restricted access. |
| Production deployment | TLS, authentication, database access controls, tested recovery, monitoring, and controlled releases need additional work beyond this local demo. |
