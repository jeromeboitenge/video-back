import uuid

from fastapi.testclient import TestClient

from app.main import app


def create_account(client: TestClient, label: str) -> dict:
    email = f"{label}-{uuid.uuid4().hex}@example.com"
    response = client.post("/api/v1/auth/register", json={"email": email, "password": "strong enough password"})
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_project_routes_require_authentication():
    with TestClient(app) as client:
        response = client.get("/api/v1/projects")
        assert response.status_code == 401


def test_authenticated_project_is_owned_by_creator():
    with TestClient(app) as client:
        suffix = uuid.uuid4().hex
        first = client.post("/api/v1/auth/register", json={"email": f"first-{suffix}@example.com", "password": "correct horse battery"})
        second = client.post("/api/v1/auth/register", json={"email": f"second-{suffix}@example.com", "password": "another strong pass"})
        assert first.status_code == 201
        assert second.status_code == 201
        document = {"version": 1, "project": {}, "canvas": {"width": 1080}, "tracks": [], "clips": [], "assets": [], "settings": {}}
        created = client.post("/api/v1/projects", json={"name": "First edit", "document": document}, headers={"Authorization": f"Bearer {first.json()['access_token']}"})
        assert created.status_code == 201
        project_id = created.json()["id"]
        own_read = client.get(f"/api/v1/projects/{project_id}", headers={"Authorization": f"Bearer {first.json()['access_token']}"})
        other_read = client.get(f"/api/v1/projects/{project_id}", headers={"Authorization": f"Bearer {second.json()['access_token']}"})
        assert own_read.status_code == 200
        assert own_read.json()["document"] == document
        assert other_read.status_code == 404


def test_duplicate_registration_is_rejected():
    with TestClient(app) as client:
        email = f"duplicate-{uuid.uuid4().hex}@example.com"
        payload = {"email": email, "password": "strong enough password"}
        assert client.post("/api/v1/auth/register", json=payload).status_code == 201
        assert client.post("/api/v1/auth/register", json=payload).status_code == 409


def test_media_upload_and_content_are_owner_scoped(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.media_storage.settings.media_root", str(tmp_path))
    with TestClient(app) as client:
        owner_headers = create_account(client, "media-owner")
        other_headers = create_account(client, "media-other")
        upload = client.post(
            "/api/v1/media",
            headers=owner_headers,
            files={"file": ("../../scene.mp4", b"sample video bytes", "video/mp4")},
        )
        assert upload.status_code == 201
        asset = upload.json()
        assert asset["name"] == "scene.mp4"
        assert asset["mime_type"] == "video/mp4"
        assert asset["size"] == len(b"sample video bytes")

        content = client.get(f"/api/v1/media/{asset['id']}/content", headers=owner_headers)
        assert content.status_code == 200
        assert content.content == b"sample video bytes"
        assert content.headers["content-type"] == "video/mp4"

        assert client.get(f"/api/v1/media/{asset['id']}/content", headers=other_headers).status_code == 404
        assert [item["id"] for item in client.get("/api/v1/media", headers=owner_headers).json()] == [asset["id"]]
        assert client.get("/api/v1/media", headers=other_headers).json() == []


def test_media_upload_requires_auth_and_rejects_unsupported_or_oversized_files(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.media_storage.settings.media_root", str(tmp_path))
    monkeypatch.setattr("app.services.media_storage.settings.media_max_bytes", 4)
    with TestClient(app) as client:
        assert client.post("/api/v1/media", files={"file": ("scene.mp4", b"data", "video/mp4")}).status_code == 401
        headers = create_account(client, "media-validation")
        unsupported = client.post("/api/v1/media", headers=headers, files={"file": ("script.txt", b"data", "text/plain")})
        oversized = client.post("/api/v1/media", headers=headers, files={"file": ("scene.mp4", b"too large", "video/mp4")})
        empty = client.post("/api/v1/media", headers=headers, files={"file": ("empty.mp4", b"", "video/mp4")})
        assert unsupported.status_code == 415
        assert oversized.status_code == 413
        assert empty.status_code == 400
        assert not [path for path in tmp_path.rglob("*") if path.is_file()]
