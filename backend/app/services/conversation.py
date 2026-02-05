from sqlalchemy import select
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
    """Найти активный (незакрытый) диалог клиента."""
    result = await session.execute(
        select(Conversation).where(
            Conversation.client_id == client_id,
            Conversation.status != ConversationStatus.closed,
        )
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
    session: AsyncSession, conversation_id: int, limit: int = 20
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
