"""Add an explicit administrator role to users."""
from alembic import op
import sqlalchemy as sa

revision = "0004_user_admin_flag"
down_revision = "0003_organizations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "is_admin")
