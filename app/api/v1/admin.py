from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import current_admin, current_user
from app.core.security import hash_password, verify_password
from app.database.session import get_db
from app.models.admin import AdminSetting, AuditEvent, SupportTicket
from app.models.organization import Organization, OrganizationRequest
from app.models.media_asset import MediaAsset
from app.models.project import Project
from app.models.user import User
from app.schemas.admin import (
    AdminProfileResponse,
    AdminReportResponse,
    AdminSettingsResponse,
    AdminSettingsUpdate,
    AuditEventResponse,
    PasswordChange,
    SupportTicketCreate,
    SupportTicketResponse,
    SupportTicketUpdate,
)
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationRequestCreate,
    OrganizationRequestResponse,
    OrganizationResponse,
    OrganizationReview,
    OrganizationStats,
)

router = APIRouter()
REQUIRE_REJECTION_NOTE = "require_rejection_note"


def _record_audit(
    db: Session,
    actor: User,
    action: str,
    target_type: str,
    target_id: str | None,
    summary: str,
    details: dict[str, object] | None = None,
) -> None:
    db.add(AuditEvent(
        actor_id=actor.id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        summary=summary,
        details=details or {},
    ))


def _ensure_slug_available(db: Session, slug: str) -> None:
    if db.scalar(select(Organization.id).where(Organization.slug == slug)):
        raise HTTPException(status_code=409, detail="An organization with this slug already exists")


@router.post("/organizations/requests", response_model=OrganizationRequestResponse, status_code=status.HTTP_201_CREATED)
def request_organization(payload: OrganizationRequestCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _ensure_slug_available(db, payload.slug)
    pending = db.scalar(select(OrganizationRequest.id).where(
        OrganizationRequest.slug == payload.slug,
        OrganizationRequest.status == "pending",
    ))
    if pending:
        raise HTTPException(status_code=409, detail="A request for this organization slug is already pending")
    request = OrganizationRequest(
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        requested_by=user.id,
    )
    db.add(request)
    db.flush()
    _record_audit(db, user, "organization.requested", "organization_request", request.id, f"{user.email} requested {request.name}.")
    db.commit()
    db.refresh(request)
    return request


@router.get("/organizations/requests/mine", response_model=list[OrganizationRequestResponse])
def list_my_organization_requests(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return list(db.scalars(
        select(OrganizationRequest)
        .where(OrganizationRequest.requested_by == user.id)
        .order_by(OrganizationRequest.created_at.desc())
    ))


@router.get("/admin/dashboard/stats", response_model=OrganizationStats)
def organization_stats(_: User = Depends(current_admin), db: Session = Depends(get_db)):
    counts = dict(db.execute(
        select(OrganizationRequest.status, func.count(OrganizationRequest.id)).group_by(OrganizationRequest.status)
    ).all())
    return OrganizationStats(
        organizations=db.scalar(select(func.count(Organization.id))) or 0,
        pending_requests=counts.get("pending", 0),
        approved_requests=counts.get("approved", 0),
        rejected_requests=counts.get("rejected", 0),
        users=db.scalar(select(func.count(User.id))) or 0,
    )


@router.get("/admin/organizations", response_model=list[OrganizationResponse])
def list_organizations(_: User = Depends(current_admin), db: Session = Depends(get_db)):
    return list(db.scalars(select(Organization).order_by(Organization.created_at.desc())))


@router.post("/admin/organizations", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(payload: OrganizationCreate, user: User = Depends(current_admin), db: Session = Depends(get_db)):
    _ensure_slug_available(db, payload.slug)
    organization = Organization(
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        created_by=user.id,
    )
    db.add(organization)
    try:
        db.flush()
        _record_audit(db, user, "organization.created", "organization", organization.id, f"{user.email} created {organization.name}.", {"slug": organization.slug})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An organization with this slug already exists") from exc
    db.refresh(organization)
    return organization


@router.get("/admin/organization-requests", response_model=list[OrganizationRequestResponse])
def list_organization_requests(
    request_status: str = Query(default="pending", alias="status", pattern="^(pending|approved|rejected|all)$"),
    _: User = Depends(current_admin),
    db: Session = Depends(get_db),
):
    query = select(OrganizationRequest)
    if request_status != "all":
        query = query.where(OrganizationRequest.status == request_status)
    return list(db.scalars(query.order_by(OrganizationRequest.created_at.desc())))


@router.post("/admin/organization-requests/{request_id}/approve", response_model=OrganizationRequestResponse)
def approve_organization_request(
    request_id: str,
    payload: OrganizationReview,
    user: User = Depends(current_admin),
    db: Session = Depends(get_db),
):
    request = db.get(OrganizationRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Organization request not found")
    if request.status != "pending":
        raise HTTPException(status_code=409, detail="This organization request has already been reviewed")
    _ensure_slug_available(db, request.slug)
    organization = Organization(
        name=request.name,
        slug=request.slug,
        description=request.description,
        created_by=user.id,
    )
    request.status = "approved"
    request.reviewed_by = user.id
    request.review_note = payload.note.strip() if payload.note else None
    request.reviewed_at = datetime.now(timezone.utc)
    db.add(organization)
    try:
        db.flush()
        _record_audit(db, user, "organization_request.approved", "organization_request", request.id, f"{user.email} approved {request.name}.", {"organization_id": organization.id})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An organization with this slug already exists") from exc
    db.refresh(request)
    return request


@router.post("/admin/organization-requests/{request_id}/reject", response_model=OrganizationRequestResponse)
def reject_organization_request(
    request_id: str,
    payload: OrganizationReview,
    user: User = Depends(current_admin),
    db: Session = Depends(get_db),
):
    request = db.get(OrganizationRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Organization request not found")
    if request.status != "pending":
        raise HTTPException(status_code=409, detail="This organization request has already been reviewed")
    setting = db.get(AdminSetting, REQUIRE_REJECTION_NOTE)
    if setting and setting.value and not (payload.note and payload.note.strip()):
        raise HTTPException(status_code=422, detail="A review note is required by administrator settings")
    request.status = "rejected"
    request.reviewed_by = user.id
    request.review_note = payload.note.strip() if payload.note else None
    request.reviewed_at = datetime.now(timezone.utc)
    _record_audit(db, user, "organization_request.rejected", "organization_request", request.id, f"{user.email} rejected {request.name}.")
    db.commit()
    db.refresh(request)
    return request


@router.get("/admin/reports/summary", response_model=AdminReportResponse)
def admin_report(_: User = Depends(current_admin), db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=30)
    support_counts = dict(db.execute(
        select(SupportTicket.status, func.count(SupportTicket.id)).group_by(SupportTicket.status)
    ).all())
    return AdminReportResponse(
        organizations=db.scalar(select(func.count(Organization.id))) or 0,
        users=db.scalar(select(func.count(User.id))) or 0,
        projects=db.scalar(select(func.count(Project.id))) or 0,
        media_assets=db.scalar(select(func.count(MediaAsset.id))) or 0,
        media_bytes=db.scalar(select(func.coalesce(func.sum(MediaAsset.size), 0))) or 0,
        organization_requests=db.scalar(select(func.count(OrganizationRequest.id))) or 0,
        support_open=support_counts.get("open", 0),
        support_in_progress=support_counts.get("in_progress", 0),
        support_closed=support_counts.get("closed", 0),
        organizations_created_30_days=db.scalar(select(func.count(Organization.id)).where(Organization.created_at >= since)) or 0,
        users_created_30_days=db.scalar(select(func.count(User.id)).where(User.created_at >= since)) or 0,
    )


@router.get("/admin/audit-events", response_model=list[AuditEventResponse])
def list_audit_events(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(current_admin),
    db: Session = Depends(get_db),
):
    return list(db.scalars(
        select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset)
    ))


@router.get("/admin/support-tickets", response_model=list[SupportTicketResponse])
def list_support_tickets(
    ticket_status: str = Query(default="open", alias="status", pattern="^(open|in_progress|closed|all)$"),
    _: User = Depends(current_admin),
    db: Session = Depends(get_db),
):
    query = select(SupportTicket)
    if ticket_status != "all":
        query = query.where(SupportTicket.status == ticket_status)
    return list(db.scalars(query.order_by(SupportTicket.created_at.desc())))


@router.patch("/admin/support-tickets/{ticket_id}", response_model=SupportTicketResponse)
def update_support_ticket(
    ticket_id: str,
    payload: SupportTicketUpdate,
    user: User = Depends(current_admin),
    db: Session = Depends(get_db),
):
    ticket = db.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Support request not found")
    ticket.status = payload.status
    ticket.admin_note = payload.admin_note.strip() if payload.admin_note else None
    ticket.updated_at = datetime.now(timezone.utc)
    _record_audit(db, user, "support_ticket.updated", "support_ticket", ticket.id, f"{user.email} changed support request status to {ticket.status}.", {"status": ticket.status})
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/support-tickets", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED)
def create_support_ticket(payload: SupportTicketCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ticket = SupportTicket(requester_id=user.id, subject=payload.subject.strip(), message=payload.message.strip())
    db.add(ticket)
    db.flush()
    _record_audit(db, user, "support_ticket.created", "support_ticket", ticket.id, f"{user.email} opened a support request.")
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/support-tickets/mine", response_model=list[SupportTicketResponse])
def list_my_support_tickets(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return list(db.scalars(
        select(SupportTicket)
        .where(SupportTicket.requester_id == user.id)
        .order_by(SupportTicket.created_at.desc())
    ))


@router.get("/admin/settings", response_model=AdminSettingsResponse)
def get_admin_settings(_: User = Depends(current_admin), db: Session = Depends(get_db)):
    setting = db.get(AdminSetting, REQUIRE_REJECTION_NOTE)
    return AdminSettingsResponse(require_rejection_note=setting.value if setting else False)


@router.put("/admin/settings", response_model=AdminSettingsResponse)
def update_admin_settings(
    payload: AdminSettingsUpdate,
    user: User = Depends(current_admin),
    db: Session = Depends(get_db),
):
    setting = db.get(AdminSetting, REQUIRE_REJECTION_NOTE)
    if setting:
        setting.value = payload.require_rejection_note
        setting.updated_by = user.id
        setting.updated_at = datetime.now(timezone.utc)
    else:
        setting = AdminSetting(key=REQUIRE_REJECTION_NOTE, value=payload.require_rejection_note, updated_by=user.id)
        db.add(setting)
    _record_audit(db, user, "admin_settings.updated", "admin_setting", REQUIRE_REJECTION_NOTE, f"{user.email} updated administrator settings.", {"require_rejection_note": payload.require_rejection_note})
    db.commit()
    return AdminSettingsResponse(require_rejection_note=setting.value)


@router.get("/admin/profile", response_model=AdminProfileResponse)
def get_admin_profile(user: User = Depends(current_admin)):
    return AdminProfileResponse(id=user.id, email=user.email, is_admin=user.is_admin, created_at=user.created_at)


@router.post("/admin/profile/password")
def change_admin_password(
    payload: PasswordChange,
    user: User = Depends(current_admin),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Choose a new password different from the current password")
    user.password_hash = hash_password(payload.new_password)
    _record_audit(db, user, "admin.password_changed", "user", user.id, f"{user.email} changed their administrator password.")
    db.commit()
    return {"status": "password_updated"}
