# Database migrations

PR-Agent uses [Alembic](https://alembic.sqlalchemy.org/) for schema changes.
The API service runs pending migrations automatically on startup — you only
need the CLI locally when **authoring** a new revision.

## Runtime (no manual steps)

At process startup, `pr_agent.db.init_database()` calls the programmatic
runner in `pr_agent/db/migrations_runner.py` and reconciles one of three
states:

| State | Signals | Action |
|-------|---------|--------|
| Greenfield | no tables at all | `SQLModel.metadata.create_all` + `alembic stamp head` |
| Legacy | tables exist, no `alembic_version` | `alembic stamp 0001_baseline` + `alembic upgrade head` |
| Normal | `alembic_version` present | `alembic upgrade head` |

The runner synthesizes its own `Config` in-memory, so `alembic.ini` does not
need to be shipped into the Docker image. Only the API service (`pr-agent-api`)
runs migrations; webhook services (`pr-agent-github`, `pr-agent-gitlab`, …)
are intentionally read-only against the schema.

## Authoring a new revision

From `pr-agent/` with the venv active and `DATABASE_URL` pointing at a dev
database that is already at `head`:

```bash
# Autogenerate from model diff (review the output — don't trust it blindly)
alembic revision --autogenerate -m "add best_practices_yaml column"

# Pure hand-written revision (prefer this for data migrations)
alembic revision -m "backfill default git provider"
```

Each revision file lives in `pr_agent/db/migrations/versions/` and is named
`<rev_id>_<slug>.py`. Use short rev IDs (`0003`, `0004`, …) and descriptive
slugs.

### Writing the `upgrade()` / `downgrade()` bodies

- Prefer explicit `op.add_column`, `op.create_table`, etc. over
  `SQLModel.metadata.create_all`. Each revision should describe a self-
  contained delta that is stable against future model changes.
- When you need to mutate data, use `op.get_bind()` + `sa.text(...)` rather
  than the ORM (models can drift between revisions).
- Always write `downgrade()` unless the operation is irreversible — document
  why in a comment if it is.

### Testing locally

```bash
# Apply
alembic upgrade head

# Roll back one step
alembic downgrade -1

# Preview SQL without touching the DB
alembic upgrade head --sql
```

### Coordinating with the model file

Every column/table added in a migration must also exist in
`pr_agent/db/models.py` with matching types — otherwise the ORM will fail at
runtime. Conversely, if you add a `Field` in `models.py` without a matching
migration, existing databases won't have the column.

## Baseline revision

`0001_baseline` is an intentionally empty marker. It exists so legacy
installs (databases created by older builds via `create_all`) can be
stamped at a known point and upgraded forward. Never put schema into this
revision — add a new revision for any change.
