from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database.session import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.auth import Credentials, TokenResponse, UserResponse
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectSave

router = APIRouter()


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: Credentials, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id), user=UserResponse(id=user.id, email=user.email))


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    return TokenResponse(access_token=create_access_token(user.id), user=UserResponse(id=user.id, email=user.email))


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(Project).where(Project.owner_id == user.id).order_by(Project.updated_at.desc())))


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = Project(owner_id=user.id, name=payload.name, document=payload.document.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/projects/{project_id}", response_model=ProjectResponse)
def save_project(project_id: str, payload: ProjectSave, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.name = payload.name
    project.document = payload.document.model_dump()
    db.commit()
    db.refresh(project)
    return project
