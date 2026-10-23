#!/usr/bin/env bash
set -Eeuo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

backup_dir="$project_dir/backups"
umask 077
mkdir -p -- "$backup_dir"
chmod 700 -- "$backup_dir"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$backup_dir/tasks-${stamp}.dump"
temporary_file="$backup_dir/.tasks-${stamp}.dump.tmp.$$"
trap 'rm -f -- "$temporary_file"' EXIT

docker compose exec -T db sh -c \
  'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' \
  > "$temporary_file"

if [[ ! -s "$temporary_file" ]]; then
  echo "Backup is empty; refusing to keep it." >&2
  exit 1
fi

# Validate the archive using PostgreSQL's own client inside the database container.
docker compose exec -T db pg_restore --list < "$temporary_file" > /dev/null
chmod 600 -- "$temporary_file"
mv -- "$temporary_file" "$backup_file"
trap - EXIT

echo "Backup created and archive-validated: $backup_file"
