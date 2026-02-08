"""Cleanup test data from knowledge_base

Revision ID: 004
Revises: 003
Create Date: 2024-01-01

"""
from typing import Sequence, Union

from alembic import op


revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Удаляем тестовую запись с ценой 3000 из базы знаний
    op.execute("DELETE FROM knowledge_base WHERE answer LIKE '%3000%'")


def downgrade() -> None:
    pass
