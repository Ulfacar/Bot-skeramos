from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import (
    ChannelType,
    Client,
    Conversation,
    ConversationStatus,
    Message,
    MessageSender,
)


async def get_or_create_client(
    session: AsyncSession,
    channel: ChannelType,
    channel_user_id: str,
    name: str | None = None,
    username: str | None = None,
) -> Client:
    """Найти клиента по мессенджеру или создать нового."""
    result = await session.execute(
        select(Client).where(
            Client.channel == channel,
            Client.channel_user_id == channel_user_id,
        )
    )
    client = result.scalar_one_or_none()

    if client:
        # Обновляем имя/username если изменились
        if name and client.name != name:
            client.name = name
        if username and client.username != username:
            client.username = username
        await session.commit()
        return client

    client = Client(
        channel=channel,
        channel_user_id=channel_user_id,
        name=name,
        username=username,
    )
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def get_active_conversation(
    session: AsyncSession, client_id: int
) -> Conversation | None:
    """Найти активный (незакрытый) диалог клиента.
    bot_completed и closed считаются завершёнными — для нового сообщения создаётся новый диалог."""
    result = await session.execute(
        select(Conversation)
        .where(
            Conversation.client_id == client_id,
            Conversation.status.in_([
                ConversationStatus.in_progress,
                ConversationStatus.needs_operator,
                ConversationStatus.operator_active,
            ]),
        )
        .order_by(Conversation.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_conversation(
    session: AsyncSession, client_id: int
) -> Conversation:
    """Создать новый диалог."""
    conversation = Conversation(client_id=client_id)
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def save_message(
    session: AsyncSession,
    conversation_id: int,
    sender: MessageSender,
    text: str,
) -> Message:
    """Сохранить сообщение в БД."""
    message = Message(
        conversation_id=conversation_id,
        sender=sender,
        text=text,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


async def get_conversation_history(
    session: AsyncSession, conversation_id: int, limit: int = 10
) -> list[Message]:
    """Получить последние N сообщений диалога."""
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()  # Хронологический порядок
    return messages


async def close_stale_conversations(session: AsyncSession, timeout_hours: int = 1) -> int:
    """Закрыть неактивные диалоги.
    - in_progress без активности > timeout_hours → closed
    - bot_completed без активности > timeout_hours → closed
    - needs_operator без активности > 4 часов → closed
    НЕ трогает operator_active (менеджер работает).
    Возвращает количество закрытых диалогов."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=timeout_hours)
    cutoff_long = datetime.now(timezone.utc) - timedelta(hours=4)

    # Закрываем in_progress и bot_completed
    result1 = await session.execute(
        update(Conversation)
        .where(
            Conversation.status.in_([
                ConversationStatus.in_progress,
                ConversationStatus.bot_completed,
            ]),
            Conversation.updated_at < cutoff,
        )
        .values(status=ConversationStatus.closed)
    )

    # Закрываем зависшие needs_operator (4 часа без ответа менеджера)
    result2 = await session.execute(
        update(Conversation)
        .where(
            Conversation.status == ConversationStatus.needs_operator,
            Conversation.updated_at < cutoff_long,
        )
        .values(status=ConversationStatus.closed)
    )

    await session.commit()
    return result1.rowcount + result2.rowcount
