import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    projects: Mapped[list["Project"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    media_assets: Mapped[list["MediaAsset"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
