"""public builds: tags, like_count, forked_from_id, build_likes

Revision ID: 0002_public_builds
Revises: 0001_initial
Create Date: 2026-05-29

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import TEXT, UUID

revision = "0002_public_builds"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("builds", sa.Column("tags", sa.ARRAY(TEXT), nullable=False, server_default="{}"))
    op.add_column("builds", sa.Column("like_count", sa.Integer, nullable=False, server_default="0"))
    op.add_column("builds", sa.Column("forked_from_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_builds_forked_from", "builds", "builds",
        ["forked_from_id"], ["id"], ondelete="SET NULL",
    )

    op.create_index("ix_builds_public_recent", "builds", ["is_public", "created_at"])
    op.create_index("ix_builds_public_popular", "builds", ["is_public", "like_count"])
    op.create_index("ix_builds_tags_gin", "builds", ["tags"], postgresql_using="gin")

    op.create_table(
        "build_likes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("build_id", UUID(as_uuid=True), sa.ForeignKey("builds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "build_id", name="uq_build_likes_user_build"),
    )
    op.create_index("ix_build_likes_user", "build_likes", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_build_likes_user", table_name="build_likes")
    op.drop_table("build_likes")
    op.drop_index("ix_builds_tags_gin", table_name="builds")
    op.drop_index("ix_builds_public_popular", table_name="builds")
    op.drop_index("ix_builds_public_recent", table_name="builds")
    op.drop_constraint("fk_builds_forked_from", "builds", type_="foreignkey")
    op.drop_column("builds", "forked_from_id")
    op.drop_column("builds", "like_count")
    op.drop_column("builds", "tags")
