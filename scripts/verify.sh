#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 DATABASE_NAME" >&2
  exit 2
fi

database_name="$1"
if [[ ! "$database_name" =~ ^[A-Za-z0-9_][A-Za-z0-9_-]{0,62}$ ]]; then
  echo "Invalid database name." >&2
  exit 2
fi

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

compose_env_file="${COMPOSE_ENV_FILE:-.env}"
if [[ ! -f "$compose_env_file" ]]; then
  echo "Compose env file not found: $compose_env_file (set COMPOSE_ENV_FILE if needed)." >&2
  exit 2
fi

result="$(docker compose --env-file "$compose_env_file" exec -T db sh -c \
  'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$1" -Atqc \
  "SELECT (SELECT count(*) FROM tasks), (SELECT count(*) FROM alembic_version)"' \
  sh "$database_name")"

if [[ ! "$result" =~ ^[0-9]+\|1$ ]]; then
  echo "Database verification failed: expected tasks and one Alembic revision." >&2
  exit 1
fi

printf 'Verified database %s: tasks=%s, Alembic revision present.\n' \
  "$database_name" "${result%%|*}"
