from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import ConversationOut, ConversationUpdate
from app.core.auth import get_current_operator
from app.db.database import get_session
from app.db.models.models import Conversation, ConversationStatus, Operator

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("/", response_model=list[ConversationOut])
async def list_conversations(
    status_filter: Optional[ConversationStatus] = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Список диалогов с фильтрацией по статусу."""
    query = (
        select(Conversation)
        .options(selectinload(Conversation.client))
        .order_by(Conversation.updated_at.desc())
    )

    if status_filter:
        query = query.where(Conversation.status == status_filter)

    result = await session.execute(query)
    return result.scalars().all()


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
