import uuid

from fastapi.testclient import TestClient

from app.main import app


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
