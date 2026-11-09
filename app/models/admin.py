import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.user import User


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(120), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False, index=True)
    admin_note: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    requester: Mapped[User] = relationship(foreign_keys=[requester_id])

    @property
    def requester_email(self) -> str:
        return self.requester.email


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(36), index=True)
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    actor: Mapped[User | None] = relationship(foreign_keys=[actor_id])

    @property
    def actor_email(self) -> str:
        return self.actor.email if self.actor else "Deleted user"


class AdminSetting(Base):
    __tablename__ = "admin_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[bool] = mapped_column(Boolean, nullable=False)
    updated_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
