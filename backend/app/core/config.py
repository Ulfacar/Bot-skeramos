from pydantic_settings import BaseSettings


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

    # WhatsApp (Meta Cloud API)
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""
    whatsapp_verify_token: str = "skeramos_webhook_verify"

    # AI
    anthropic_api_key: str = ""

    # JWT для админки
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 480

    class Config:
        env_file = ".env"


settings = Settings()
