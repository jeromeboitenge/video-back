# Backend development status

Status reflects implemented code and available verification evidence. This backend is independently runnable and deployable from the `backend/` repository.

| Feature | Frontend | Backend | Database | Tests | Status |
|---|---|---|---|---|---|
| Authentication | Login/register client and token use | Password hashing, JWT access tokens, ownership/admin dependencies | Users and admin roles persist through SQLAlchemy migrations | API tests exist; runtime verification currently stalls in this environment | Partial |
| Projects | Local drafts, account project list/open/save, duplicate, delete, and version controls | Owner-scoped create/list/fetch/update/delete and version snapshot/list/restore; deletion removes project-layer rows transactionally | Project documents in SQLAlchemy JSON, relational image layers, and `project_versions` snapshots (`0007`) | Direct create/save/fetch/delete/version restore and owner-check tests pass; HTTP client suite remains unverified here | Partial |
| Image-layer project data | Image Studio edits, fetches, autosaves and exports layers | Typed validation; create/save sync transactionally; list/fetch responses hydrate ordered layer data from relational rows | Stored in project document JSON and mirrored to `project_image_layers` by migration `0006` | Direct create/save/fetch route and relational sync tests pass; HTTP client suite remains unverified in this environment | Partial |
| Media | Browser IndexedDB plus authenticated cloud uploads/restores and uploaded-copy deletion | Authenticated upload/list/content/delete; deletion checks ownership and coordinates database removal with a staged file rename | Asset metadata rows; file bytes on configured local disk | Upload API tests exist; deletion flow not yet independently verified; full runtime suite not verified here | Partial |
| Administration | Admin workspace and account tools | Admin-protected reports, organization requests, support, audit, and settings routes | SQLAlchemy records and migrations | Existing API/UI test coverage; runtime suite not verified here | Partial |
| Video/image/audio processing | Browser preview, timeline editing, local WebM and PNG output | No FFmpeg/Pillow/OpenCV processing pipeline or durable export-job API | No export/job records | Not implemented | Planned |
| Background jobs and object storage | No job progress UI | No Redis/Celery workers or S3 adapter | No job/object-store tables | Not implemented | Planned |
| Production database | API client uses versioned REST | PostgreSQL URL support; SQLite development default | Alembic migrations; project documents use JSON | PostgreSQL deployment not exercised here | Partial |

## Current verification blocker

The backend virtual environment points to Python 3.14. A direct `TestClient` health request does not return in this execution environment, and the HTTP project API test consequently times out before producing a result. The Pydantic schema, direct project route functions, database synchronization tests, Alembic upgrade, Python compilation, and OpenAPI generation were exercised independently. Do not treat HTTP transport/auth integration as verified until the API tests complete in a working runtime.

## Next backend work

1. Run the HTTP tests in a supported, responsive Python environment and fix any failures.
2. Verify authenticated HTTP create, update, and fetch plus PostgreSQL persistence of image-layer project documents.
3. Implement asynchronous media processing/export jobs before advertising server-side rendering.
4. Add durable object storage and production operational controls.
