"""
Meta WhatsApp Cloud API клиент.
Документация: https://developers.facebook.com/docs/whatsapp/cloud-api
"""
import logging
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v18.0"


def is_whatsapp_configured() -> bool:
    """Проверить настроен ли WhatsApp."""
    return bool(settings.whatsapp_token and settings.whatsapp_phone_id)


async def send_whatsapp_message(to: str, text: str) -> bool:
    """
    Отправить текстовое сообщение через WhatsApp Cloud API.

    Args:
        to: Номер получателя (только цифры, например: 996555123456)
        text: Текст сообщения

    Returns:
        True если отправлено успешно
    """
    if not is_whatsapp_configured():
        logger.error("WhatsApp не настроен")
        return False

    # Убираем всё кроме цифр
    phone = "".join(filter(str.isdigit, to))

    url = f"{GRAPH_API_URL}/{settings.whatsapp_phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone,
        "type": "text",
        "text": {"body": text},
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id", "unknown")
                logger.info(f"WhatsApp сообщение отправлено: {message_id}")
                return True
            else:
                logger.error(f"Ошибка WhatsApp API: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        logger.error(f"Ошибка отправки WhatsApp: {e}")
        return False


def verify_webhook(mode: str, token: str, challenge: str) -> str | None:
    """
    Верификация webhook от Meta.
    Meta отправляет GET запрос при настройке webhook.

    Returns:
        challenge если верификация успешна, иначе None
    """
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("WhatsApp webhook верифицирован")
        return challenge
    logger.warning(f"Неверный verify_token: {token}")
    return None


def parse_webhook_message(data: dict) -> dict | None:
    """
    Парсинг входящего сообщения из webhook.

    Returns:
        dict с полями: phone, name, text
        или None если это не текстовое сообщение
    """
    try:
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})

        # Проверяем что это сообщение (не статус)
        messages = value.get("messages", [])
        if not messages:
            return None

        message = messages[0]

        # Пока поддерживаем только текст
        if message.get("type") != "text":
            logger.info(f"Пропускаем сообщение типа: {message.get('type')}")
            return None

        # Получаем информацию о контакте
        contacts = value.get("contacts", [{}])
        contact = contacts[0] if contacts else {}

        return {
            "phone": message.get("from", ""),
            "name": contact.get("profile", {}).get("name", ""),
            "text": message.get("text", {}).get("body", ""),
            "message_id": message.get("id", ""),
        }

    except Exception as e:
        logger.error(f"Ошибка парсинга webhook: {e}")
        return None
