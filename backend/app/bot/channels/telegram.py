import logging

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import CommandStart

from app.bot.ai.assistant import clean_response, generate_response, needs_operator
from app.core.config import settings
from app.db.database import async_session
from app.db.models.models import (
    ChannelType,
    ConversationStatus,
    MessageSender,
)
from app.services.conversation import (
    create_conversation,
    get_active_conversation,
    get_conversation_history,
    get_or_create_client,
    save_message,
)

logger = logging.getLogger(__name__)

router = Router()
bot: Bot | None = None
dp: Dispatcher | None = None


@router.message(CommandStart())
async def handle_start(message: types.Message):
    """Обработка команды /start."""
    async with async_session() as session:
        await get_or_create_client(
            session=session,
            channel=ChannelType.telegram,
            channel_user_id=str(message.from_user.id),
            name=message.from_user.full_name,
            username=message.from_user.username,
        )

    await message.answer(
        "Здравствуйте! Добро пожаловать в SKERAMOS — "
        "гончарную мастерскую и бутик-отель в Бишкеке.\n\n"
        "Я виртуальный ассистент. Могу помочь с:\n"
        "• Записью на мастер-класс\n"
        "• Бронированием номера\n"
        "• Ответами на вопросы\n\n"
        "Напишите ваш вопрос!"
    )


@router.message()
async def handle_message(message: types.Message):
    """Обработка любого текстового сообщения."""
    if not message.text:
        await message.answer("Пока я понимаю только текстовые сообщения.")
        return

    async with async_session() as session:
        # 1. Найти или создать клиента
        client = await get_or_create_client(
            session=session,
            channel=ChannelType.telegram,
            channel_user_id=str(message.from_user.id),
            name=message.from_user.full_name,
            username=message.from_user.username,
        )

        # 2. Найти активный диалог или создать новый
        conversation = await get_active_conversation(session, client.id)
        if not conversation:
            conversation = await create_conversation(session, client.id)

        # 3. Сохранить сообщение клиента
        await save_message(
            session, conversation.id, MessageSender.client, message.text
        )

        # 4. Если диалог ведёт оператор — не отвечать ботом
        if conversation.status == ConversationStatus.operator_active:
            return

        # 5. Получить историю и сгенерировать ответ AI
        history = await get_conversation_history(session, conversation.id)
        response_text = await generate_response(history)

        # 6. Проверить нужен ли менеджер
        if needs_operator(response_text):
            conversation.status = ConversationStatus.needs_operator
            response_text = clean_response(response_text)

        # 7. Сохранить ответ бота
        await save_message(
            session, conversation.id, MessageSender.bot, response_text
        )

        await session.commit()

    # 8. Отправить ответ клиенту
    await message.answer(response_text)


async def start_bot():
    """Запуск Telegram бота (polling)."""
    global bot, dp

    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN не задан — бот не запущен")
        return

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("Telegram бот запускается...")
    await dp.start_polling(bot)


def get_bot() -> Bot | None:
    """Получить экземпляр бота (для отправки из админки)."""
    return bot


async def stop_bot():
    """Остановка Telegram бота."""
    global bot, dp
    if dp:
        await dp.stop_polling()
    if bot:
        await bot.session.close()
    logger.info("Telegram бот остановлен")
