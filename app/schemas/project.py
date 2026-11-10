from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ImageLayer(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    assetId: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    visible: bool = True
    locked: bool = False
    opacity: float = Field(default=1, ge=0, le=1)
    blendMode: Literal["normal", "multiply", "screen", "overlay"] = "normal"
    x: float = Field(default=0, ge=-100000, le=100000)
    y: float = Field(default=0, ge=-100000, le=100000)
    scale: float = Field(default=1, ge=0.1, le=5)
    rotation: float = Field(default=0, ge=-3600, le=3600)
    cropLeft: float = Field(default=0, ge=0, le=0.9)
    cropTop: float = Field(default=0, ge=0, le=0.9)
    cropRight: float = Field(default=0, ge=0, le=0.9)
    cropBottom: float = Field(default=0, ge=0, le=0.9)

    @model_validator(mode="after")
    def validate_crop_region(self):
        if self.cropLeft + self.cropRight >= 1 or self.cropTop + self.cropBottom >= 1:
            raise ValueError("Image layer crop must leave a visible area")
        return self


class ProjectDocument(BaseModel):
    model_config = ConfigDict(extra="allow")

    version: int = Field(ge=1)
    project: dict = Field(default_factory=dict)
    canvas: dict = Field(default_factory=dict)
    tracks: list[dict] = Field(default_factory=list)
    clips: list[dict] = Field(default_factory=list)
    assets: list[dict] = Field(default_factory=list)
    imageLayers: list[ImageLayer] = Field(default_factory=list)
    effects: list[dict] = Field(default_factory=list)
    textOverlays: list[dict] = Field(default_factory=list)
    settings: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_image_layer_assets(self):
        image_asset_ids = {asset.get("id") for asset in self.assets if asset.get("kind") == "image"}
        if any(layer.assetId not in image_asset_ids for layer in self.imageLayers):
            raise ValueError("Every image layer must reference an image asset in this project")
        return self


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    document: ProjectDocument


class ProjectSave(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    document: ProjectDocument
    expected_revision: int | None = Field(default=None, ge=1)


class ProjectRestore(BaseModel):
    expected_revision: int = Field(ge=1)


class ProjectResponse(BaseModel):
    id: str
    name: str
    document: dict
    created_at: datetime
    updated_at: datetime
    revision: int

    model_config = {"from_attributes": True}


class ProjectVersionResponse(BaseModel):
    id: str
    project_id: str
    version_number: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
