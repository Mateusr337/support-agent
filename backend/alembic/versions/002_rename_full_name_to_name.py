"""rename full_name to name on users

Revision ID: 002_rename_full_name_to_name
Revises: 001_create_users
Create Date: 2026-07-02 22:36:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "002_rename_full_name_to_name"
down_revision: Union[str, Sequence[str], None] = "001_create_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "full_name", new_column_name="name")


def downgrade() -> None:
    op.alter_column("users", "name", new_column_name="full_name")
