from sqlalchemy import select

from app.api.v1.router import create_project as create_project_route
from app.api.v1.router import create_project_version as create_project_version_route
from app.api.v1.router import delete_project as delete_project_route
from app.api.v1.router import get_project as get_project_route
from app.api.v1.router import list_project_versions as list_project_versions_route
from app.api.v1.router import restore_project_version as restore_project_version_route
from app.api.v1.router import save_project as save_project_route
from app.models.project import Project
from app.models.project_image_layer import ProjectImageLayer
from app.models.project_version import ProjectVersion
from app.models.user import User
from app.schemas.project import ImageLayer
from app.schemas.project import ProjectCreate, ProjectSave
from app.services.project_image_layers import sync_project_image_layers
from fastapi import HTTPException
import pytest


def test_sync_project_image_layers_inserts_updates_reorders_and_deletes(isolated_test_database):
    user = User(email="image-layers@example.com", password_hash="test-only")
    isolated_test_database.add(user)
    isolated_test_database.flush()
    project = Project(owner_id=user.id, name="Layered composition", document={})
    isolated_test_database.add(project)
    isolated_test_database.flush()

    first = ImageLayer(id="layer-1", assetId="asset-1", name="Background", visible=True, locked=False, opacity=1, blendMode="normal")
    second = ImageLayer(id="layer-2", assetId="asset-2", name="Foreground", visible=True, locked=True, opacity=0.7, blendMode="screen", x=12, cropLeft=0.1)
    sync_project_image_layers(isolated_test_database, project.id, [first, second])
    isolated_test_database.flush()

    rows = list(isolated_test_database.scalars(select(ProjectImageLayer).where(ProjectImageLayer.project_id == project.id).order_by(ProjectImageLayer.position)))
    assert [(row.layer_id, row.position) for row in rows] == [("layer-1", 0), ("layer-2", 1)]
    assert rows[1].asset_id == "asset-2"
    assert rows[1].blend_mode == "screen"
    assert rows[1].crop_left == 0.1

    updated = first.model_copy(update={"name": "Renamed background", "visible": False})
    sync_project_image_layers(isolated_test_database, project.id, [second, updated])
    isolated_test_database.flush()
    rows = list(isolated_test_database.scalars(select(ProjectImageLayer).where(ProjectImageLayer.project_id == project.id).order_by(ProjectImageLayer.position)))
    assert [(row.layer_id, row.position) for row in rows] == [("layer-2", 0), ("layer-1", 1)]
    assert rows[1].name == "Renamed background"
    assert rows[1].visible is False

    sync_project_image_layers(isolated_test_database, project.id, [])
    isolated_test_database.flush()
    assert list(isolated_test_database.scalars(select(ProjectImageLayer).where(ProjectImageLayer.project_id == project.id))) == []


def test_project_routes_persist_and_fetch_layers_in_document_and_relational_rows(isolated_test_database):
    user = User(email="project-route-layers@example.com", password_hash="test-only")
    isolated_test_database.add(user)
    isolated_test_database.flush()
    document = {
        "version": 1,
        "project": {"id": "local-project", "name": "Canvas"},
        "assets": [{"id": "asset-1", "name": "poster.png", "kind": "image", "mimeType": "image/png", "size": 1}],
        "imageLayers": [{"id": "layer-1", "assetId": "asset-1", "name": "Poster", "blendMode": "overlay", "cropLeft": 0.2}],
    }
    created = create_project_route(ProjectCreate(name="Canvas", document=document), user, isolated_test_database)
    assert created["document"]["imageLayers"][0]["blendMode"] == "overlay"
    project_id = created["id"]
    rows = list(isolated_test_database.scalars(select(ProjectImageLayer).where(ProjectImageLayer.project_id == project_id)))
    assert len(rows) == 1
    assert rows[0].blend_mode == "overlay"
    assert rows[0].crop_left == 0.2

    document["imageLayers"][0]["name"] = "Updated poster"
    saved = save_project_route(project_id, ProjectSave(name="Canvas v2", document=document), user, isolated_test_database)
    fetched = get_project_route(project_id, user, isolated_test_database)
    assert fetched["document"]["imageLayers"][0]["name"] == "Updated poster"
    rows = list(isolated_test_database.scalars(select(ProjectImageLayer).where(ProjectImageLayer.project_id == project_id)))
    assert len(rows) == 1
    assert rows[0].name == "Updated poster"
    assert saved["name"] == "Canvas v2"

    other_user = User(email="not-project-owner@example.com", password_hash="test-only")
    isolated_test_database.add(other_user)
    isolated_test_database.flush()
    with pytest.raises(HTTPException) as forbidden_lookup:
        delete_project_route(project_id, other_user, isolated_test_database)
    assert forbidden_lookup.value.status_code == 404

    assert delete_project_route(project_id, user, isolated_test_database) is None
    assert list(isolated_test_database.scalars(select(ProjectImageLayer).where(ProjectImageLayer.project_id == project_id))) == []
    assert list(isolated_test_database.scalars(select(ProjectVersion).where(ProjectVersion.project_id == project_id))) == []
    with pytest.raises(HTTPException) as error:
        get_project_route(project_id, user, isolated_test_database)
    assert error.value.status_code == 404


def test_project_versions_snapshot_list_and_restore_document_and_relational_layers(isolated_test_database):
    user = User(email="project-versions@example.com", password_hash="test-only")
    isolated_test_database.add(user)
    isolated_test_database.flush()
    document = {
        "version": 1,
        "project": {"id": "local-versioned", "name": "Versioned design"},
        "assets": [{"id": "image-1", "name": "cover.png", "kind": "image", "mimeType": "image/png", "size": 1}],
        "imageLayers": [{"id": "layer-1", "assetId": "image-1", "name": "Original cover", "opacity": 1}],
    }
    created = create_project_route(ProjectCreate(name="Versioned design", document=document), user, isolated_test_database)
    project_id = created["id"]
    version = create_project_version_route(project_id, user, isolated_test_database)
    assert version.version_number == 1

    changed = {**document, "project": {"id": "local-versioned", "name": "Changed design"}, "imageLayers": [{**document["imageLayers"][0], "name": "Changed cover", "opacity": 0.3}]}
    save_project_route(project_id, ProjectSave(name="Changed design", document=changed), user, isolated_test_database)
    versions = list_project_versions_route(project_id, user, isolated_test_database)
    assert [item.id for item in versions] == [version.id]

    restored = restore_project_version_route(project_id, version.id, user, isolated_test_database)
    assert restored["name"] == "Versioned design"
    assert restored["document"]["imageLayers"][0]["name"] == "Original cover"
    row = isolated_test_database.scalar(select(ProjectImageLayer).where(ProjectImageLayer.project_id == project_id))
    assert row.name == "Original cover"
    assert row.opacity == 1
