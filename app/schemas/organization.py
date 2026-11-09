import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrganizationInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Organization name must have at least two characters")
        return value

    @field_validator("slug")
    @classmethod
    def clean_slug(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,78}[a-z0-9])", value):
            raise ValueError("Use lowercase letters, numbers, and internal hyphens for the slug")
        return value

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class OrganizationCreate(OrganizationInput):
    pass


class OrganizationRequestCreate(OrganizationInput):
    pass


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    description: str | None
    created_by: str
    created_at: datetime


class OrganizationRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    description: str | None
    requested_by: str
    requester_email: str | None = None
    status: str
    reviewed_by: str | None
    review_note: str | None
    created_at: datetime
    reviewed_at: datetime | None


class OrganizationReview(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class OrganizationStats(BaseModel):
    organizations: int
    pending_requests: int
    approved_requests: int
    rejected_requests: int
    users: int
