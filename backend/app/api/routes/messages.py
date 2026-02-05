import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import MessageCreate, MessageOut
from app.bot.channels.telegram import get_bot
from app.core.auth import get_current_operator
from app.db.database import get_session
from app.db.models.models import (
    ChannelType,
    Conversation,
    ConversationStatus,
    Message,
    MessageSender,
    Operator,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations/{conversation_id}/messages", tags=["Messages"])


@router.get("/", response_model=list[MessageOut])
async def get_messages(
    conversation_id: int,
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Получить все сообщения диалога."""
    result = await session.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Диалог не найден")

    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return result.scalars().all()


@router.post("/", response_model=MessageOut, status_code=201)
async def send_message(
    conversation_id: int,
    data: MessageCreate,
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Менеджер отправляет сообщение в диалог."""
    result = await session.execute(
        select(Conversation)
        .options(selectinload(Conversation.client))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Диалог не найден")

    # Переводим диалог в статус "оператор отвечает"
    if conversation.status != ConversationStatus.operator_active:
        conversation.status = ConversationStatus.operator_active
        conversation.assigned_operator_id = operator.id

    message = Message(
        conversation_id=conversation_id,
        sender=MessageSender.operator,
        text=data.text,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)

    # Отправляем сообщение клиенту в мессенджер
    client = conversation.client
    tg_bot = get_bot()
    if client.channel == ChannelType.telegram and tg_bot:
        try:
            await tg_bot.send_message(
                chat_id=int(client.channel_user_id),
                text=data.text,
            )
        except Exception as e:
            logger.error(f"Ошибка отправки в Telegram: {e}")

    return message
