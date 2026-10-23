#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 BACKUP_FILE restore_verify_NAME" >&2
  echo "The target must be a new database with the restore_verify_ prefix." >&2
  exit 2
fi

backup_file="$(realpath -- "$1")"
target_database="$2"
if [[ ! -f "$backup_file" || ! -s "$backup_file" ]]; then
  echo "Backup file must exist and be nonempty." >&2
  exit 2
fi
if [[ ! "$target_database" =~ ^restore_verify_[A-Za-z0-9_]{1,47}$ ]]; then
  echo "Target must match restore_verify_NAME using letters, digits, and underscores." >&2
  exit 2
fi

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

docker compose exec -T db pg_restore --list < "$backup_file" > /dev/null

# createdb fails if the target exists; restore never drops or overwrites a database.
docker compose exec -T db sh -c \
  'exec createdb -U "$POSTGRES_USER" "$1"' sh "$target_database"
docker compose exec -T db sh -c \
  'exec pg_restore --exit-on-error --no-owner --no-privileges \
    -U "$POSTGRES_USER" -d "$1"' sh "$target_database" \
  < "$backup_file"

"$project_dir/scripts/verify.sh" "$target_database"
echo "Restore completed into isolated database: $target_database"
