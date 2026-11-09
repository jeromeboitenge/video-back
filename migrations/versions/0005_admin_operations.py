"""Add admin audit, support and settings."""
from alembic import op
import sqlalchemy as sa

revision = "0005_admin_operations"
down_revision = "0004_user_admin_flag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("requester_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(length=120), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("admin_note", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_support_tickets_requester_id", "support_tickets", ["requester_id"])
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("actor_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=True),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_target_id", "audit_events", ["target_id"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])
    op.create_table(
        "admin_settings",
        sa.Column("key", sa.String(length=80), primary_key=True),
        sa.Column("value", sa.Boolean(), nullable=False),
        sa.Column("updated_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("admin_settings")
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_target_id", table_name="audit_events")
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_support_tickets_status", table_name="support_tickets")
    op.drop_index("ix_support_tickets_requester_id", table_name="support_tickets")
    op.drop_table("support_tickets")
