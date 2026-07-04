"""add created_at index on audit_logs

Revision ID: 007_audit_logs_created_at_index
Revises: 006_audit_log_turn_id_uuid
"""

from typing import Sequence, Union

from alembic import op

revision: str = "007_audit_logs_created_at_index"
down_revision: Union[str, Sequence[str], None] = "006_audit_log_turn_id_uuid"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        op.f("ix_audit_logs_created_at"),
        "audit_logs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_user_id_created_at",
        "audit_logs",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_user_id_created_at", table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
