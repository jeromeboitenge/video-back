"""Add optimistic concurrency revisions to projects."""

from alembic import op
import sqlalchemy as sa

revision = "0008_project_revision"
down_revision = "0007_project_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("revision", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    op.drop_column("projects", "revision")
