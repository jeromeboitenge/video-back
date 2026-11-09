from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SupportTicketCreate(BaseModel):
    subject: str = Field(min_length=4, max_length=120)
    message: str = Field(min_length=10, max_length=4000)


class SupportTicketUpdate(BaseModel):
    status: Literal["open", "in_progress", "closed"]
    admin_note: str | None = Field(default=None, max_length=1000)


class SupportTicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    requester_id: str
    requester_email: str
    subject: str
    message: str
    status: str
    admin_note: str | None
    created_at: datetime
    updated_at: datetime


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_id: str | None
    actor_email: str
    action: str
    target_type: str
    target_id: str | None
    summary: str
    details: dict[str, object]
    created_at: datetime


class AdminSettingsResponse(BaseModel):
    require_rejection_note: bool


class AdminSettingsUpdate(BaseModel):
    require_rejection_note: bool


class AdminReportResponse(BaseModel):
    organizations: int
    users: int
    projects: int
    media_assets: int
    media_bytes: int
    organization_requests: int
    support_open: int
    support_in_progress: int
    support_closed: int
    organizations_created_30_days: int
    users_created_30_days: int


class AdminProfileResponse(BaseModel):
    id: str
    email: str
    is_admin: bool
    created_at: datetime


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)
