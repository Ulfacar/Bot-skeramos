import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import api_router
from app.bot.channels.telegram import start_bot, stop_bot
from app.bot.channels.whatsapp import router as whatsapp_router
from app.db.database import async_session
from app.services.conversation import close_stale_conversations

logging.basicConfig(level=logging.INFO)

app = FastAPI(title=settings.app_name)

# Разрешаем запросы от фронтенда (админки)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(whatsapp_router)  # WhatsApp webhook


@app.get("/")
async def root():
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/status")
async def status():
    """Статус подключений (Telegram, WhatsApp)."""
    from app.services.meta_whatsapp import is_whatsapp_configured
    from app.bot.channels.telegram import get_bot

    return {
        "telegram": {
            "configured": bool(settings.telegram_bot_token),
            "running": get_bot() is not None,
        },
        "whatsapp": {
            "configured": is_whatsapp_configured(),
            "webhook": "/webhook/whatsapp",
        },
    }


async def auto_close_loop():
    """Фоновая задача: закрывать неактивные диалоги каждые 5 минут."""
    logger = logging.getLogger(__name__)
    while True:
        await asyncio.sleep(300)  # 5 минут
        try:
            async with async_session() as session:
                closed = await close_stale_conversations(session, timeout_hours=1)
                if closed:
                    logger.info(f"Автозакрытие: {closed} диалогов")
        except Exception as e:
            logger.error(f"Ошибка автозакрытия: {e}")


@app.on_event("startup")
async def on_startup():
    """Запуск Telegram бота и автозакрытия в фоне при старте сервера."""
    asyncio.create_task(start_bot())
    asyncio.create_task(auto_close_loop())


@app.on_event("shutdown")
async def on_shutdown():
    """Остановка бота при выключении сервера."""
    await stop_bot()
