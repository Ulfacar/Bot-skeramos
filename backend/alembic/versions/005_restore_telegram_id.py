"""Restore telegram_id after testing

Revision ID: 005
Revises: 004
Create Date: 2024-01-01

"""
from typing import Sequence, Union

from alembic import op


revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Возвращаем telegram_id админу
    op.execute("UPDATE operators SET telegram_id = '1857459997' WHERE email = 'admin@skeramos.com'")


def downgrade() -> None:
    op.execute("UPDATE operators SET telegram_id = NULL WHERE email = 'admin@skeramos.com'")
