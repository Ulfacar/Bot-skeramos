# Сервис уведомлений менеджерам
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Operator, Conversation, Client, Message, ChannelType

logger = logging.getLogger(__name__)

# Хранилище состояний: operator_telegram_id -> conversation_id (какой менеджер отвечает на какой диалог)
operator_reply_state: dict[str, int] = {}


def set_operator_replying(operator_telegram_id: str, conversation_id: int):
    """Установить состояние: менеджер отвечает на диалог."""
    operator_reply_state[operator_telegram_id] = conversation_id


def get_operator_replying(operator_telegram_id: str) -> int | None:
    """Получить ID диалога, на который отвечает менеджер."""
    return operator_reply_state.get(operator_telegram_id)


def clear_operator_replying(operator_telegram_id: str):
    """Очистить состояние ответа менеджера."""
    operator_reply_state.pop(operator_telegram_id, None)


async def get_operators_with_telegram(session: AsyncSession) -> list[Operator]:
    """Получить всех активных менеджеров с telegram_id."""
    result = await session.execute(
        select(Operator).where(
            Operator.is_active == True,
            Operator.telegram_id.isnot(None),
        )
    )
    return list(result.scalars().all())


async def get_operator_by_telegram_id(session: AsyncSession, telegram_id: str) -> Operator | None:
    """Найти менеджера по telegram_id."""
    result = await session.execute(
        select(Operator).where(Operator.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def notify_operators_new_request(
    bot: Bot,
    session: AsyncSession,
    conversation: Conversation,
    client: Client,
    last_message: str,
):
    """Отправить уведомление всем менеджерам о новом запросе."""
    operators = await get_operators_with_telegram(session)

    if not operators:
        logger.warning("Нет менеджеров с telegram_id для уведомления")
        return

    # Формируем текст уведомления
    client_name = client.name or "Гость"
    client_username = f"@{client.username}" if client.username else ""

    # Определяем канал
    if client.channel == ChannelType.whatsapp:
        channel_icon = "📱"
        channel_name = "WhatsApp"
    else:
        channel_icon = "✈️"
        channel_name = "Telegram"

    text = (
        f"🔔 <b>Нужна помощь!</b>\n\n"
        f"👤 <b>Гость:</b> {client_name} {client_username}\n"
        f"{channel_icon} <b>Канал:</b> {channel_name}\n"
        f"💬 <b>Вопрос:</b>\n{last_message}\n\n"
        f"📍 Диалог #{conversation.id}"
    )

    # Кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✍️ Ответить",
                callback_data=f"reply:{conversation.id}"
            ),
            InlineKeyboardButton(
                text="👀 История",
                callback_data=f"history:{conversation.id}"
            ),
        ]
    ])

    # Отправляем всем менеджерам
    for operator in operators:
        try:
            await bot.send_message(
                chat_id=operator.telegram_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            logger.info(f"Уведомление отправлено менеджеру {operator.name} (tg:{operator.telegram_id})")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления менеджеру {operator.name}: {e}")


async def send_history_to_operator(
    bot: Bot,
    session: AsyncSession,
    operator_telegram_id: str,
    conversation_id: int,
):
    """Отправить историю диалога менеджеру."""
    # Получаем сообщения
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(10)
    )
    messages = list(result.scalars().all())

    if not messages:
        await bot.send_message(
            chat_id=operator_telegram_id,
            text="История пуста",
        )
        return

    # Формируем текст истории
    lines = [f"📜 <b>История диалога #{conversation_id}</b>\n"]
    for msg in messages:
        sender_emoji = {
            "client": "👤",
            "bot": "🤖",
            "operator": "👨‍💼",
        }.get(msg.sender.value, "❓")

        # Обрезаем длинные сообщения
        text = msg.text[:200] + "..." if len(msg.text) > 200 else msg.text
        lines.append(f"{sender_emoji} {text}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✍️ Ответить",
                callback_data=f"reply:{conversation_id}"
            ),
        ]
    ])

    await bot.send_message(
        chat_id=operator_telegram_id,
        text="\n\n".join(lines),
        parse_mode="HTML",
        reply_markup=keyboard,
    )
