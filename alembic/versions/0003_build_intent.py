"""build intent: pve / coop / pvp

Revision ID: 0003_build_intent
Revises: 0002_public_builds
Create Date: 2026-05-30

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_build_intent"
down_revision = "0002_public_builds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "builds",
        sa.Column("intent", sa.Text, nullable=False, server_default="pve"),
    )
    op.create_check_constraint(
        "ck_builds_intent",
        "builds",
        "intent IN ('pve','coop','pvp')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_builds_intent", "builds", type_="check")
    op.drop_column("builds", "intent")
