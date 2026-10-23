# Controlled schema changes

Configure `DATABASE_URL` in the ignored `.env` file or process environment. Use the
same URL as the target API. Alembic reads settings directly; credentials are never
stored in `alembic.ini`.

```bash
source .venv/bin/activate
alembic upgrade head
alembic current
alembic check
```

`upgrade head` applies missing revisions once, in order. Revision `0001` creates
`tasks` with PostgreSQL timezone-aware timestamps. No tables are created when the
API starts. Apply migrations as one controlled deployment step, before starting
or updating API instances; do not run competing migration jobs.

For future changes, update models, run `alembic revision --autogenerate -m 'describe
change'`, and inspect the generated upgrade and downgrade before committing.
Autogeneration needs a running database already at the current revision.
`alembic check` detects differences between mapped metadata and the database.

Downgrading revision `0001` drops the tasks table and deletes its records. Do not
run downgrades on valuable data without explicit approval and a verified backup.
`updated_at` is refreshed by SQLAlchemy on API updates; direct SQL writers must
set it themselves. Migrations and application access share a development role;
production should separate their privileges.
