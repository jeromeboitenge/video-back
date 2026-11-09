import uuid

from sqlalchemy import select
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User


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
        document = {
            "version": 1,
            "project": {},
            "canvas": {"width": 1080},
            "tracks": [],
            "clips": [],
            "assets": [{"id": "asset-1", "name": "scene.mp4", "kind": "video", "mimeType": "video/mp4", "size": 1}],
            "effects": [{"id": "effect-1", "assetId": "asset-1", "type": "vivid", "strength": 75, "enabled": True}],
            "settings": {},
        }
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


def test_media_upload_rejects_declared_type_that_does_not_match_file_content(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.media_storage.settings.media_root", str(tmp_path))
    with TestClient(app) as client:
        headers = create_account(client, "media-signature")
        response = client.post(
            "/api/v1/media",
            headers=headers,
            files={"file": ("fake.png", b"not a valid png image", "image/png")},
        )
        assert response.status_code == 415
        assert not [path for path in tmp_path.rglob("*") if path.is_file()]


def test_organization_requests_and_admin_management_are_authorized_and_complete(isolated_test_database):
    suffix = uuid.uuid4().hex[:10]
    admin_email = f"org-admin-{suffix}@example.com"
    requested_slug = f"northstar-{suffix}"
    direct_slug = f"frameforge-labs-{suffix}"
    with TestClient(app) as client:
        admin_registration = client.post(
            "/api/v1/auth/register",
            json={"email": admin_email, "password": "secure admin password", "is_admin": True},
        )
        member_headers = create_account(client, "org-member")
        assert admin_registration.status_code == 201
        assert admin_registration.json()["user"]["is_admin"] is False
        administrator = isolated_test_database.scalar(select(User).where(User.email == admin_email))
        assert administrator is not None
        administrator.is_admin = True
        isolated_test_database.commit()
        admin_headers = {"Authorization": f"Bearer {admin_registration.json()['access_token']}"}
        assert client.get("/api/v1/auth/me", headers=admin_headers).json()["is_admin"] is True
        initial_stats = client.get("/api/v1/admin/dashboard/stats", headers=admin_headers).json()

        assert client.get("/api/v1/admin/dashboard/stats").status_code == 401
        assert client.get("/api/v1/admin/organizations", headers=member_headers).status_code == 403
        assert client.post("/api/v1/admin/organizations", headers=member_headers, json={
            "name": "Unauthorized", "slug": "unauthorized",
        }).status_code == 403

        requested = client.post("/api/v1/organizations/requests", headers=member_headers, json={
            "name": "Northstar Media", "slug": requested_slug.upper(), "description": "Creative team",
        })
        assert requested.status_code == 201
        request_id = requested.json()["id"]
        assert requested.json()["slug"] == requested_slug
        assert client.get("/api/v1/organizations/requests/mine", headers=member_headers).json()[0]["id"] == request_id
        assert client.post("/api/v1/organizations/requests", headers=member_headers, json={
            "name": "Northstar Media", "slug": requested_slug,
        }).status_code == 409
        assert client.get("/api/v1/admin/organization-requests", headers=member_headers).status_code == 403

        pending = client.get("/api/v1/admin/organization-requests", headers=admin_headers)
        assert pending.status_code == 200
        assert [item["id"] for item in pending.json()] == [request_id]
        approved = client.post(
            f"/api/v1/admin/organization-requests/{request_id}/approve",
            headers=admin_headers,
            json={"note": "Verified"},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"
        assert approved.json()["review_note"] == "Verified"
        assert client.post(
            f"/api/v1/admin/organization-requests/{request_id}/approve",
            headers=admin_headers,
            json={},
        ).status_code == 409

        created = client.post("/api/v1/admin/organizations", headers=admin_headers, json={
            "name": "Frameforge Labs", "slug": direct_slug,
        })
        assert created.status_code == 201
        org_slugs = {item["slug"] for item in client.get("/api/v1/admin/organizations", headers=admin_headers).json()}
        assert {requested_slug, direct_slug} <= org_slugs
        assert client.post("/api/v1/admin/organizations", headers=admin_headers, json={
            "name": "Duplicate", "slug": direct_slug,
        }).status_code == 409

        rejected_request = client.post("/api/v1/organizations/requests", headers=member_headers, json={
            "name": "Rejected Group", "slug": f"rejected-group-{suffix}",
        })
        rejected = client.post(
            f"/api/v1/admin/organization-requests/{rejected_request.json()['id']}/reject",
            headers=admin_headers,
            json={"note": "Please contact support"},
        )
        assert rejected.status_code == 200
        assert rejected.json()["status"] == "rejected"
        stats = client.get("/api/v1/admin/dashboard/stats", headers=admin_headers).json()
        assert stats["organizations"] == initial_stats["organizations"] + 2
        assert stats["pending_requests"] == initial_stats["pending_requests"]
        assert stats["approved_requests"] == initial_stats["approved_requests"] + 1
        assert stats["rejected_requests"] == initial_stats["rejected_requests"] + 1
        assert stats["users"] >= 2

        support = client.post("/api/v1/support-tickets", headers=member_headers, json={
            "subject": "Cannot export video", "message": "My video export fails every time.",
        })
        assert support.status_code == 201
        ticket_id = support.json()["id"]
        assert support.json()["requester_email"].startswith("org-member-")
        assert client.get("/api/v1/support-tickets/mine", headers=member_headers).json()[0]["id"] == ticket_id
        assert client.get("/api/v1/support-tickets/mine", headers=admin_headers).json() == []
        assert client.get("/api/v1/admin/support-tickets", headers=member_headers).status_code == 403
        updated_ticket = client.patch(
            f"/api/v1/admin/support-tickets/{ticket_id}",
            headers=admin_headers,
            json={"status": "in_progress", "admin_note": "We are investigating."},
        )
        assert updated_ticket.status_code == 200
        assert updated_ticket.json()["status"] == "in_progress"
        assert updated_ticket.json()["admin_note"] == "We are investigating."

        assert client.get("/api/v1/admin/settings", headers=member_headers).status_code == 403
        assert client.get("/api/v1/admin/settings", headers=admin_headers).json() == {"require_rejection_note": False}
        assert client.put("/api/v1/admin/settings", headers=admin_headers, json={
            "require_rejection_note": True,
        }).json() == {"require_rejection_note": True}
        note_required_request = client.post("/api/v1/organizations/requests", headers=member_headers, json={
            "name": "Needs Review", "slug": f"needs-review-{suffix}",
        })
        assert client.post(
            f"/api/v1/admin/organization-requests/{note_required_request.json()['id']}/reject",
            headers=admin_headers,
            json={},
        ).status_code == 422
        assert client.post(
            f"/api/v1/admin/organization-requests/{note_required_request.json()['id']}/reject",
            headers=admin_headers,
            json={"note": "Incomplete details"},
        ).status_code == 200

        assert client.get("/api/v1/admin/profile", headers=admin_headers).json()["email"] == admin_email
        assert client.get("/api/v1/admin/profile", headers=member_headers).status_code == 403
        assert client.post("/api/v1/admin/profile/password", headers=admin_headers, json={
            "current_password": "wrong password", "new_password": "updated admin password",
        }).status_code == 400
        assert client.post("/api/v1/admin/profile/password", headers=admin_headers, json={
            "current_password": "secure admin password", "new_password": "updated admin password",
        }).status_code == 200
        assert client.post("/api/v1/auth/login", json={
            "email": admin_email, "password": "updated admin password",
        }).status_code == 200

        audit = client.get("/api/v1/admin/audit-events?limit=100", headers=admin_headers)
        assert audit.status_code == 200
        assert any(event["action"] == "support_ticket.updated" for event in audit.json())
        assert client.get("/api/v1/admin/audit-events", headers=member_headers).status_code == 403
        report = client.get("/api/v1/admin/reports/summary", headers=admin_headers)
        assert report.status_code == 200
        assert report.json()["organizations"] == stats["organizations"]
        assert report.json()["support_in_progress"] == 1
        assert report.json()["organization_requests"] == initial_stats["pending_requests"] + 3
