from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import ConversationOut, ConversationUpdate
from app.core.auth import get_current_operator
from app.db.database import get_session
from app.db.models.models import Client, Conversation, ConversationStatus, Operator

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("/", response_model=list[ConversationOut])
async def list_conversations(
    status_filter: Optional[ConversationStatus] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Список диалогов с фильтрацией по статусу и поиском по имени клиента."""
    query = (
        select(Conversation)
        .join(Client)
        .options(selectinload(Conversation.client))
        .order_by(Conversation.updated_at.desc())
    )

    if status_filter:
        query = query.where(Conversation.status == status_filter)

    if search:
        pattern = f"%{search}%"
        query = query.where(
            (Client.name.ilike(pattern)) | (Client.username.ilike(pattern))
        )

    result = await session.execute(query)
    return result.scalars().all()


@router.get("/stats", response_model=dict)
async def get_stats(
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Статистика диалогов за сегодня и всего."""
    # Сегодня по UTC+6 (Кыргызстан), но без таймзоны для совместимости с БД
    now = datetime.utcnow() + timedelta(hours=6)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Всего по статусам
    result = await session.execute(
        select(Conversation.status, func.count())
        .group_by(Conversation.status)
    )
    total_by_status = {row[0]: row[1] for row in result.all()}

    # Сегодня по статусам
    result = await session.execute(
        select(Conversation.status, func.count())
        .where(Conversation.created_at >= today_start)
        .group_by(Conversation.status)
    )
    today_by_status = {row[0]: row[1] for row in result.all()}

    total_all = sum(total_by_status.values())
    today_all = sum(today_by_status.values())

    return {
        "today": {
            "total": today_all,
            "bot_completed": today_by_status.get(ConversationStatus.bot_completed, 0),
            "needs_operator": today_by_status.get(ConversationStatus.needs_operator, 0),
            "operator_active": today_by_status.get(ConversationStatus.operator_active, 0),
            "in_progress": today_by_status.get(ConversationStatus.in_progress, 0),
            "closed": today_by_status.get(ConversationStatus.closed, 0),
        },
        "total": {
            "total": total_all,
            "bot_completed": total_by_status.get(ConversationStatus.bot_completed, 0),
            "needs_operator": total_by_status.get(ConversationStatus.needs_operator, 0),
            "operator_active": total_by_status.get(ConversationStatus.operator_active, 0),
            "in_progress": total_by_status.get(ConversationStatus.in_progress, 0),
            "closed": total_by_status.get(ConversationStatus.closed, 0),
        },
    }


@router.get("/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation_id: int,
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Получить один диалог по ID."""
    result = await session.execute(
        select(Conversation)
        .options(selectinload(Conversation.client))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Диалог не найден")
    return conversation


@router.patch("/{conversation_id}", response_model=ConversationOut)
async def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Обновить статус, категорию или назначить оператора."""
    result = await session.execute(
        select(Conversation)
        .options(selectinload(Conversation.client))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Диалог не найден")

    if data.status is not None:
        conversation.status = data.status
    if data.category is not None:
        conversation.category = data.category
    if data.assigned_operator_id is not None:
        conversation.assigned_operator_id = data.assigned_operator_id

    await session.commit()
    await session.refresh(conversation)
    return conversation
