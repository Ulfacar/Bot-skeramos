"""Clear telegram_id temporarily for testing

Revision ID: 003
Revises: 002
Create Date: 2024-01-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Временно убираем telegram_id для тестирования
    op.execute("UPDATE operators SET telegram_id = NULL WHERE telegram_id = '1857459997'")


def downgrade() -> None:
    # Возвращаем telegram_id
    op.execute("UPDATE operators SET telegram_id = '1857459997' WHERE email = 'admin@skeramos.com'")
