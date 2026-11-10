import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database.session import get_db
from app.models.media_asset import MediaAsset
from app.models.project import Project
from app.models.project_image_layer import ProjectImageLayer
from app.models.project_version import ProjectVersion
from app.models.user import User
from app.schemas.auth import Credentials, TokenResponse, UserResponse
from app.schemas.media import MediaAssetResponse
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectSave, ProjectVersionResponse
from app.services.media_storage import display_filename, media_path, save_upload, validate_media_type
from app.services.project_image_layers import project_response, sync_project_image_layers

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/media", response_model=list[MediaAssetResponse])
def list_media(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(MediaAsset).where(MediaAsset.owner_id == user.id).order_by(MediaAsset.created_at.desc())))


@router.post("/media", response_model=MediaAssetResponse, status_code=status.HTTP_201_CREATED)
def upload_media(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        mime_type, extension = validate_media_type(file.content_type)
        asset_id = str(uuid4())
        storage_key = f"{user.id}/{asset_id}{extension}"
        size = save_upload(file, storage_key)
        asset = MediaAsset(id=asset_id, owner_id=user.id, name=display_filename(file.filename), mime_type=mime_type, size=size, storage_key=storage_key)
        try:
            db.add(asset)
            db.commit()
            db.refresh(asset)
        except Exception:
            db.rollback()
            stored_path = media_path(storage_key)
            if stored_path.exists():
                stored_path.unlink()
            raise
    finally:
        file.file.close()
    return asset


@router.get("/media/{asset_id}/content")
def get_media_content(asset_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    asset = db.scalar(select(MediaAsset).where(MediaAsset.id == asset_id, MediaAsset.owner_id == user.id))
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")
    path = media_path(asset.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Media file is unavailable")
    return FileResponse(path, media_type=asset.mime_type, filename=asset.name)


@router.delete("/media/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(asset_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    asset = db.scalar(select(MediaAsset).where(MediaAsset.id == asset_id, MediaAsset.owner_id == user.id))
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    path = media_path(asset.storage_key)
    tombstone = path.with_name(f".{path.name}.{uuid4().hex}.deleting")
    moved_file = path.is_file()
    if moved_file:
        path.replace(tombstone)
    try:
        db.delete(asset)
        db.commit()
    except Exception:
        db.rollback()
        if moved_file and tombstone.is_file():
            tombstone.replace(path)
        raise

    if moved_file:
        try:
            tombstone.unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not remove deleted media file %s", tombstone)


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: Credentials, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id), user=UserResponse(id=user.id, email=user.email, is_admin=user.is_admin))


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    return TokenResponse(access_token=create_access_token(user.id), user=UserResponse(id=user.id, email=user.email, is_admin=user.is_admin))


@router.get("/auth/me", response_model=UserResponse)
def get_current_user(user: User = Depends(current_user)):
    return UserResponse(id=user.id, email=user.email, is_admin=user.is_admin)


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(user: User = Depends(current_user), db: Session = Depends(get_db)):
    projects = list(db.scalars(select(Project).where(Project.owner_id == user.id).order_by(Project.updated_at.desc())))
    if not projects:
        return []
    rows = list(db.scalars(select(ProjectImageLayer).where(ProjectImageLayer.project_id.in_([project.id for project in projects])).order_by(ProjectImageLayer.project_id, ProjectImageLayer.position)))
    layers_by_project: dict[str, list[ProjectImageLayer]] = {}
    for row in rows:
        layers_by_project.setdefault(row.project_id, []).append(row)
    return [project_response(project, layers_by_project.get(project.id, [])) for project in projects]


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = Project(owner_id=user.id, name=payload.name, document=payload.document.model_dump(exclude_unset=True))
    db.add(project)
    db.flush()
    sync_project_image_layers(db, project.id, payload.document.imageLayers)
    db.commit()
    db.refresh(project)
    rows = list(db.scalars(select(ProjectImageLayer).where(ProjectImageLayer.project_id == project.id).order_by(ProjectImageLayer.position)))
    return project_response(project, rows)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    rows = list(db.scalars(select(ProjectImageLayer).where(ProjectImageLayer.project_id == project.id).order_by(ProjectImageLayer.position)))
    return project_response(project, rows)


@router.put("/projects/{project_id}", response_model=ProjectResponse)
def save_project(project_id: str, payload: ProjectSave, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.name = payload.name
    project.document = payload.document.model_dump(exclude_unset=True)
    sync_project_image_layers(db, project.id, payload.document.imageLayers)
    db.commit()
    db.refresh(project)
    rows = list(db.scalars(select(ProjectImageLayer).where(ProjectImageLayer.project_id == project.id).order_by(ProjectImageLayer.position)))
    return project_response(project, rows)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.execute(delete(ProjectImageLayer).where(ProjectImageLayer.project_id == project.id))
    db.execute(delete(ProjectVersion).where(ProjectVersion.project_id == project.id))
    db.delete(project)
    db.commit()


@router.get("/projects/{project_id}/versions", response_model=list[ProjectVersionResponse])
def list_project_versions(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return list(db.scalars(select(ProjectVersion).where(ProjectVersion.project_id == project.id).order_by(ProjectVersion.version_number.desc())))


@router.post("/projects/{project_id}/versions", response_model=ProjectVersionResponse, status_code=status.HTTP_201_CREATED)
def create_project_version(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    latest = db.scalar(select(func.max(ProjectVersion.version_number)).where(ProjectVersion.project_id == project.id)) or 0
    version = ProjectVersion(
        project_id=project.id,
        created_by=user.id,
        version_number=latest + 1,
        name=project.name,
        document=project.document,
    )
    db.add(version)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A project version was created concurrently. Retry the request.") from exc
    db.refresh(version)
    return version


@router.post("/projects/{project_id}/versions/{version_id}/restore", response_model=ProjectResponse)
def restore_project_version(project_id: str, version_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    version = db.scalar(select(ProjectVersion).where(ProjectVersion.id == version_id, ProjectVersion.project_id == project.id))
    if not version:
        raise HTTPException(status_code=404, detail="Project version not found")
    restored = ProjectSave(name=version.name, document=version.document)
    project.name = restored.name
    project.document = restored.document.model_dump(exclude_unset=True)
    sync_project_image_layers(db, project.id, restored.document.imageLayers)
    db.commit()
    db.refresh(project)
    rows = list(db.scalars(select(ProjectImageLayer).where(ProjectImageLayer.project_id == project.id).order_by(ProjectImageLayer.position)))
    return project_response(project, rows)
