import logging

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Приложение
    app_name: str = "SKERAMOS Bot"
    debug: bool = True

    # База данных
    database_url: str = "postgresql+asyncpg://postgres:password@db:5432/skeramos"
    database_ssl: bool = False

    # CORS (через запятую)
    cors_origins: str = "http://localhost:3000"

    # Telegram
    telegram_bot_token: str = ""

    # WhatsApp (Gupshup)
    # WhatsApp (Meta Cloud API)
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""
    whatsapp_verify_token: str = "skeramos_webhook_verify"

    # AI (OpenRouter)
    openrouter_api_key: str = ""
    ai_model: str = "deepseek/deepseek-chat"

    # JWT для админки
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 480

    class Config:
        env_file = ".env"


settings = Settings()

if settings.secret_key == "change-me-in-production" and not settings.debug:
    logger.critical("SECRET_KEY не изменён! Установите уникальный SECRET_KEY в .env")

if not settings.openrouter_api_key:
    logger.warning("OPENROUTER_API_KEY не задан — бот будет отвечать заглушкой")
