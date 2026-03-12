"""
WhatsApp канал через Meta Cloud API.
Обработка входящих сообщений и отправка ответов.
"""
import logging
from fastapi import APIRouter, Request, Query
from fastapi.responses import PlainTextResponse

from app.bot.ai.assistant import (
    bot_completed,
    clean_response,
    generate_response,
    needs_operator,
    format_knowledge_answer,
)
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
from app.services.notification import notify_operators_new_request
from app.services.knowledge import search_knowledge_base
from app.services.meta_whatsapp import (
    send_whatsapp_message,
    parse_webhook_message,
    is_whatsapp_configured,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/webhook/whatsapp")
async def whatsapp_webhook_verify(
    hub_mode: str = Query(default=None, alias="hub.mode"),
    hub_verify_token: str = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str = Query(default=None, alias="hub.challenge"),
):
    """
    Верификация webhook от Meta (GET запрос).
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token and hub_challenge:
        logger.info("WhatsApp webhook верифицирован")
        return PlainTextResponse(hub_challenge)

    logger.warning("WhatsApp webhook верификация провалена")
    return PlainTextResponse("Forbidden", status_code=403)


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Webhook для приёма сообщений от Meta WhatsApp Cloud API.
    """
    if not is_whatsapp_configured():
        logger.warning("WhatsApp (Meta Cloud API) не настроен, игнорируем webhook")
        return PlainTextResponse("OK")

    try:
        data = await request.json()
    except Exception:
        logger.error("WhatsApp webhook: не удалось распарсить JSON")
        return PlainTextResponse("OK")

    logger.info(f"WhatsApp webhook получен: {data}")

    # Парсим сообщение
    message_data = parse_webhook_message(data)
    if not message_data:
        return PlainTextResponse("OK")

    # Обрабатываем сообщение
    try:
        await handle_whatsapp_message(
            phone_number=message_data["phone"],
            message_text=message_data["text"],
            profile_name=message_data["name"],
        )
    except Exception as e:
        logger.error(f"Ошибка обработки WhatsApp сообщения: {e}")

    return PlainTextResponse("OK")


async def handle_whatsapp_message(
    phone_number: str,
    message_text: str,
    profile_name: str,
):
    """
    Обработка входящего WhatsApp сообщения.
    Логика аналогична Telegram боту.
    """
    if not message_text.strip():
        return

    async with async_session() as session:
        # 1. Найти или создать клиента
        client = await get_or_create_client(
            session=session,
            channel=ChannelType.whatsapp,
            channel_user_id=phone_number,
            name=profile_name or phone_number,
            username=None,
        )

        # 2. Найти активный диалог или создать новый
        conversation = await get_active_conversation(session, client.id)
        is_new_conversation = conversation is None
        if not conversation:
            conversation = await create_conversation(session, client.id)

        # 2.1. Приветственное сообщение для нового диалога
        if is_new_conversation:
            greeting = (
                "Здравствуйте! Я виртуальный ассистент SKERAMOS 🏺\n"
                "Помогу ответить на вопросы о нашей керамической студии, "
                "мини-отеле и мероприятиях.\n\n"
                "Если потребуется — подключу менеджера. Чем могу помочь?"
            )
            await send_whatsapp_message(phone_number, greeting)
            await save_message(
                session, conversation.id, MessageSender.bot, greeting
            )
            await session.commit()

        # 3. Сохранить сообщение клиента
        await save_message(
            session, conversation.id, MessageSender.client, message_text
        )

        # 4. Если диалог ведёт оператор — пересылаем ему сообщение
        if conversation.status == ConversationStatus.operator_active:
            if conversation.assigned_operator_id:
                from app.db.models.models import Operator
                from app.bot.channels.telegram import get_bot
                from sqlalchemy import select as sa_select

                op_result = await session.execute(
                    sa_select(Operator).where(Operator.id == conversation.assigned_operator_id)
                )
                assigned_operator = op_result.scalar_one_or_none()
                tg_bot = get_bot()
                if assigned_operator and assigned_operator.telegram_id and tg_bot:
                    try:
                        await tg_bot.send_message(
                            chat_id=assigned_operator.telegram_id,
                            text=f"💬 Новое сообщение от гостя в WhatsApp (диалог #{conversation.id}):\n\n{message_text}",
                        )
                    except Exception as e:
                        logger.error(f"Ошибка уведомления менеджера о WhatsApp сообщении: {e}")
            await session.commit()
            return

        # 5. Ищем ответ в базе знаний
        knowledge_entry = await search_knowledge_base(session, message_text)

        if knowledge_entry:
            # Нашли ответ в базе знаний
            response_text = format_knowledge_answer(knowledge_entry.answer)
            logger.info(f"WhatsApp: ответ из базы знаний (id={knowledge_entry.id})")
        else:
            # Спрашиваем AI
            history = await get_conversation_history(session, conversation.id)
            response_text = await generate_response(history)

            # Проверяем нужен ли менеджер
            need_operator = needs_operator(response_text)
            if need_operator:
                conversation.status = ConversationStatus.needs_operator
            elif bot_completed(response_text):
                conversation.status = ConversationStatus.bot_completed

            response_text = clean_response(response_text)

            # Уведомляем менеджеров если нужно
            if need_operator:
                await session.commit()
                from app.bot.channels.telegram import get_bot

                bot = get_bot()
                if bot:
                    await notify_operators_new_request(
                        bot=bot,
                        session=session,
                        conversation=conversation,
                        client=client,
                        last_message=message_text,
                    )

        # 6. Сохранить ответ бота
        await save_message(
            session, conversation.id, MessageSender.bot, response_text
        )
        await session.commit()

        # 7. Отправить ответ клиенту через WhatsApp
        await send_whatsapp_message(phone_number, response_text)


async def send_operator_reply_to_whatsapp(phone_number: str, message: str) -> bool:
    """
    Отправить ответ оператора клиенту в WhatsApp.
    Используется из Telegram при ответе менеджера.
    """
    return await send_whatsapp_message(phone_number, message)
