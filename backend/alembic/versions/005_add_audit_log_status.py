"""add status column to audit_logs

Revision ID: 005_add_audit_log_status
Revises: 004_create_audit_logs
Create Date: 2026-07-03 15:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_add_audit_log_status"
down_revision: Union[str, Sequence[str], None] = "004_create_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "audit_logs",
        sa.Column("status", sa.String(length=16), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("audit_logs", "status")
