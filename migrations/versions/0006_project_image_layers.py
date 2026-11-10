"""Persist image-layer fields relationally alongside project documents."""
from alembic import op
import sqlalchemy as sa


revision = "0006_project_image_layers"
down_revision = "0005_admin_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_image_layers",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("layer_id", sa.String(length=100), nullable=False),
        sa.Column("asset_id", sa.String(length=100), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("visible", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.Column("opacity", sa.Float(), nullable=False),
        sa.Column("blend_mode", sa.String(length=16), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("scale", sa.Float(), nullable=False),
        sa.Column("rotation", sa.Float(), nullable=False),
        sa.Column("crop_left", sa.Float(), nullable=False),
        sa.Column("crop_top", sa.Float(), nullable=False),
        sa.Column("crop_right", sa.Float(), nullable=False),
        sa.Column("crop_bottom", sa.Float(), nullable=False),
        sa.UniqueConstraint("project_id", "layer_id", name="uq_project_image_layers_project_layer"),
    )
    op.create_index("ix_project_image_layers_project_id", "project_image_layers", ["project_id"])
    op.create_index("ix_project_image_layers_asset_id", "project_image_layers", ["asset_id"])


def downgrade() -> None:
    op.drop_index("ix_project_image_layers_asset_id", table_name="project_image_layers")
    op.drop_index("ix_project_image_layers_project_id", table_name="project_image_layers")
    op.drop_table("project_image_layers")
