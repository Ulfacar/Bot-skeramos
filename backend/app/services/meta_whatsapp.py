"""
Meta WhatsApp Cloud API клиент.
Документация: https://developers.facebook.com/docs/whatsapp/cloud-api
"""
import logging
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def is_whatsapp_configured() -> bool:
    """Проверить настроен ли WhatsApp."""
    return bool(settings.whatsapp_token and settings.whatsapp_phone_id)


async def send_whatsapp_message(to: str, text: str) -> bool:
    """
    Отправить текстовое сообщение через Meta WhatsApp Cloud API.

    Args:
        to: Номер получателя (только цифры, например: 996555123456)
        text: Текст сообщения

    Returns:
        True если отправлено успешно
    """
    if not is_whatsapp_configured():
        logger.error("WhatsApp (Meta Cloud API) не настроен")
        return False

    phone = "".join(filter(str.isdigit, to))

    url = f"{GRAPH_API_BASE}/{settings.whatsapp_phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text},
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)

            if 200 <= response.status_code < 300:
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id", "unknown")
                logger.info(f"WhatsApp сообщение отправлено (Meta): {message_id}")
                return True
            else:
                logger.error(f"Ошибка Meta API: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        logger.error(f"Ошибка отправки WhatsApp (Meta): {e}")
        return False


def parse_webhook_message(data: dict) -> dict | None:
    """
    Парсинг входящего сообщения из Meta WhatsApp webhook.

    Returns:
        dict с полями: phone, name, text
        или None если это не текстовое сообщение
    """
    try:
        # Meta Cloud API формат
        entry = data.get("entry", [])
        if not entry:
            return None

        changes = entry[0].get("changes", [])
        if not changes:
            return None

        value = changes[0].get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return None

        message = messages[0]

        # Только текстовые сообщения
        if message.get("type") != "text":
            logger.info(f"Пропускаем сообщение типа: {message.get('type')}")
            return None

        contacts = value.get("contacts", [])
        contact_name = contacts[0].get("profile", {}).get("name", "") if contacts else ""

        return {
            "phone": message.get("from", ""),
            "name": contact_name,
            "text": message.get("text", {}).get("body", ""),
            "message_id": message.get("id", ""),
        }

    except Exception as e:
        logger.error(f"Ошибка парсинга Meta webhook: {e}")
        return None
