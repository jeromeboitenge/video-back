from datetime import datetime
from pydantic import BaseModel, Field


class ProjectDocument(BaseModel):
    version: int = Field(ge=1)
    project: dict = Field(default_factory=dict)
    canvas: dict = Field(default_factory=dict)
    tracks: list[dict] = Field(default_factory=list)
    clips: list[dict] = Field(default_factory=list)
    assets: list[dict] = Field(default_factory=list)
    effects: list[dict] = Field(default_factory=list)
    settings: dict = Field(default_factory=dict)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    document: ProjectDocument


class ProjectSave(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    document: ProjectDocument


class ProjectResponse(BaseModel):
    id: str
    name: str
    document: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
