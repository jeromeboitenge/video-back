import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class ProjectImageLayer(Base):
    """Queryable relational projection of the image layers in a project document."""

    __tablename__ = "project_image_layers"
    __table_args__ = (UniqueConstraint("project_id", "layer_id", name="uq_project_image_layers_project_layer"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    layer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    asset_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    visible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    opacity: Mapped[float] = mapped_column(Float, nullable=False)
    blend_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    scale: Mapped[float] = mapped_column(Float, nullable=False)
    rotation: Mapped[float] = mapped_column(Float, nullable=False)
    crop_left: Mapped[float] = mapped_column(Float, nullable=False)
    crop_top: Mapped[float] = mapped_column(Float, nullable=False)
    crop_right: Mapped[float] = mapped_column(Float, nullable=False)
    crop_bottom: Mapped[float] = mapped_column(Float, nullable=False)
