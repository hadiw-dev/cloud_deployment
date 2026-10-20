# Troubleshooting

These are diagnostic commands; container commands become usable after Phase 3.
Do not delete volumes to fix startup problems.

| Symptom | Diagnostic command | Likely cause | Fix | Verification |
| --- | --- | --- | --- | --- |
| Docker unavailable | `docker info` | Desktop stopped, WSL integration disabled, or socket permission denied | Start Docker Desktop and enable the Ubuntu WSL integration; in an agent sandbox request permission for daemon access | `docker info` |
| Terraform missing | `command -v terraform` | CLI not installed in Ubuntu | Follow the official installation link in `infra/terraform/README.md` | `terraform version` |
| API stopped | `docker compose ps -a` and `docker compose logs api` | Startup error | Resolve the logged error before restarting | `curl -f http://localhost:8000/health` |
| Database unavailable | `docker compose logs db` | Database startup failure | Check volume permissions, disk space, and database logs | `docker compose ps` |
| Incorrect password | `docker compose logs api` | Credentials do not match the initialized volume | Restore matching configuration or rotate credentials deliberately; changing an environment file does not reset an existing database password | `curl -f http://localhost:8000/ready` |
| Port in use | `ss -ltnp` | Another process owns port 8000 | Stop the conflicting development process or choose a different localhost port | `docker compose ps` |
| Missing migrations | `docker compose run --rm api alembic current` | Schema was never upgraded | Run the documented controlled migration step from Phase 3 | `docker compose run --rm api alembic current` |
| Connection refused | `docker compose ps -a` | Service stopped or incorrect hostname | Use `db` inside Compose, check logs and health | `curl -f http://localhost:8000/ready` |
| Health check failing | `docker inspect --format '{{json .State.Health}}' CONTAINER_NAME` | Check failing or process unavailable | Inspect health output and service logs | `docker compose ps` |
| CI test failure | Read the failed job logs on GitHub | Dependency, migration, lint, or test failure | Reproduce the failed command locally using the same Python version and a disposable test database | Rerun the failed check, then the workflow |

Useful host diagnostics: `ps aux`, `df -h`, `free -h`, `ss -ltnp`.
Use `docker logs CONTAINER_NAME` for container output. On hosts with systemd-managed
Docker, `journalctl -u docker --since '15 minutes ago'` helps diagnose daemon failures.
Docker Desktop's daemon may not be managed by Ubuntu's systemd; use Desktop diagnostics there.
