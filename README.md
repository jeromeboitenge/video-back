# Frameforge API

Python 3.12+ FastAPI service. Run `pip install -e '.[dev,postgres]'`, then `alembic upgrade head`, then `uvicorn app.main:app --reload`. API docs are at `/docs`; health is at `/api/v1/health`.

Copy `.env.example` to `.env` and set a private JWT secret for any shared environment. Local development defaults to SQLite. For PostgreSQL, run `docker compose up -d db` and set `DATABASE_URL=postgresql+psycopg://frameforge:frameforge@localhost:5432/frameforge`, then install `.[postgres]`.

`alembic upgrade head` applies schema migrations for both SQLite and PostgreSQL. The app never changes schema on startup.

Project responses include an integer `revision`. Clients should include it as `expected_revision` when updating a project or restoring a version. If another client saved first, the API returns `409 project_conflict` with the current revision and does not apply the stale document.

Authenticated media uploads are stored under `MEDIA_ROOT` (default `./media`) using generated storage names. `MEDIA_MAX_BYTES` defaults to 524288000 (500 MiB). Configure a persistent volume for `MEDIA_ROOT` when running the API; media bytes are not stored in the database.

Administrator access is a database-backed role and is never granted through public registration. Provision an administrator from the backend host with `python -m app.cli create-admin admin@example.com`; the command prompts for a password and promotes or resets that account. The dashboard and organization-management API require this role.
