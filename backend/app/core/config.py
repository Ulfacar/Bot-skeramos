from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Приложение
    app_name: str = "SKERAMOS Bot"
    debug: bool = True

    # База данных
    database_url: str = "postgresql+asyncpg://postgres:password@db:5432/skeramos"

    # Telegram
    telegram_bot_token: str = ""

    # WhatsApp (Twilio)
    whatsapp_account_sid: str = ""
    whatsapp_auth_token: str = ""
    whatsapp_phone_number: str = ""

    # AI
    anthropic_api_key: str = ""

    # JWT для админки
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 480

    class Config:
        env_file = ".env"


settings = Settings()
