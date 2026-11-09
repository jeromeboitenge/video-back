"""Add organisations and approval requests."""
from alembic import op
import sqlalchemy as sa

revision = "0003_organizations"
down_revision = "0002_media_assets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)
    op.create_table(
        "organization_requests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requested_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reviewed_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("review_note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_organization_requests_slug", "organization_requests", ["slug"])
    op.create_index("ix_organization_requests_status", "organization_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_organization_requests_status", table_name="organization_requests")
    op.drop_index("ix_organization_requests_slug", table_name="organization_requests")
    op.drop_table("organization_requests")
    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_table("organizations")
