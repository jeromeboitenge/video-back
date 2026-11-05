# Frameforge API

Python 3.12+ FastAPI service. Run `pip install -e '.[dev,postgres]'`, then `alembic upgrade head`, then `uvicorn app.main:app --reload`. API docs are at `/docs`; health is at `/api/v1/health`.

Copy `.env.example` to `.env` and set a private JWT secret for any shared environment. Local development defaults to SQLite. For PostgreSQL, run `docker compose up -d db` and set `DATABASE_URL=postgresql+psycopg://frameforge:frameforge@localhost:5432/frameforge`, then install `.[postgres]`.

`alembic upgrade head` applies schema migrations for both SQLite and PostgreSQL. The app never changes schema on startup.

Authenticated media uploads are stored under `MEDIA_ROOT` (default `./media`) using generated storage names. `MEDIA_MAX_BYTES` defaults to 524288000 (500 MiB). Configure a persistent volume for `MEDIA_ROOT` when running the API; media bytes are not stored in the database.
