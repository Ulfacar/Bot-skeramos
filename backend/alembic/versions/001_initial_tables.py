"""Создание всех таблиц

Revision ID: 001
Revises:
Create Date: 2025-01-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Клиенты ---
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column(
            "channel",
            sa.Enum("telegram", "whatsapp", name="channeltype"),
            nullable=False,
        ),
        sa.Column("channel_user_id", sa.String(255), nullable=False),
        sa.Column(
            "language",
            sa.Enum("ru", "ky", name="language"),
            server_default="ru",
        ),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now()
        ),
    )

    # --- Операторы ---
    op.create_table(
        "operators",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), server_default="false"),
        sa.Column("telegram_id", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now()
        ),
    )

    # --- Диалоги ---
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("clients.id"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "in_progress",
                "bot_completed",
                "needs_operator",
                "operator_active",
                "closed",
                name="conversationstatus",
            ),
            server_default="in_progress",
        ),
        sa.Column(
            "category",
            sa.Enum(
                "master_class",
                "hotel",
                "custom_order",
                "general",
                name="conversationcategory",
            ),
            server_default="general",
        ),
        sa.Column(
            "assigned_operator_id",
            sa.Integer(),
            sa.ForeignKey("operators.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now()
        ),
    )

    # --- Сообщения ---
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column(
            "sender",
            sa.Enum("client", "bot", "operator", name="messagesender"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now()
        ),
    )

    # --- Бронирования ---
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("clients.id"),
            nullable=False,
        ),
        sa.Column(
            "category",
            sa.Enum(
                "master_class",
                "hotel",
                "custom_order",
                "general",
                name="conversationcategory",
            ),
            nullable=False,
        ),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("confirmed", sa.Boolean(), server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("bookings")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("operators")
    op.drop_table("clients")

    op.execute("DROP TYPE IF EXISTS channeltype")
    op.execute("DROP TYPE IF EXISTS language")
    op.execute("DROP TYPE IF EXISTS conversationstatus")
    op.execute("DROP TYPE IF EXISTS conversationcategory")
    op.execute("DROP TYPE IF EXISTS messagesender")
