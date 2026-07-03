"""change audit_logs.turn_id from integer to uuid

Revision ID: 006_audit_log_turn_id_uuid
Revises: 005_add_audit_log_status
Create Date: 2026-07-03 15:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_audit_log_turn_id_uuid"
down_revision: Union[str, Sequence[str], None] = "005_add_audit_log_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_turn_id"), table_name="audit_logs")
    op.alter_column(
        "audit_logs",
        "turn_id",
        existing_type=sa.Integer(),
        type_=sa.Uuid(),
        postgresql_using="gen_random_uuid()",
    )
    op.create_index(op.f("ix_audit_logs_turn_id"), "audit_logs", ["turn_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_turn_id"), table_name="audit_logs")
    op.alter_column(
        "audit_logs",
        "turn_id",
        existing_type=sa.Uuid(),
        type_=sa.Integer(),
        postgresql_using="0",
    )
    op.create_index(op.f("ix_audit_logs_turn_id"), "audit_logs", ["turn_id"], unique=False)
