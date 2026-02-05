import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import api_router
from app.bot.channels.telegram import start_bot, stop_bot

logging.basicConfig(level=logging.INFO)

app = FastAPI(title=settings.app_name)

# Разрешаем запросы от фронтенда (админки)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {"status": "ok", "app": settings.app_name}


@app.on_event("startup")
async def on_startup():
    """Запуск Telegram бота в фоне при старте сервера."""
    asyncio.create_task(start_bot())


@app.on_event("shutdown")
async def on_shutdown():
    """Остановка бота при выключении сервера."""
    await stop_bot()
