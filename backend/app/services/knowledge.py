# Сервис базы знаний
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import KnowledgeBase, Message, MessageSender

logger = logging.getLogger(__name__)


async def add_to_knowledge_base(
    session: AsyncSession,
    question: str,
    answer: str,
    operator_id: int | None = None,
    conversation_id: int | None = None,
) -> KnowledgeBase:
    """Добавить новую запись в базу знаний."""
    # Генерируем ключевые слова из вопроса (простая версия)
    keywords = extract_keywords(question)

    entry = KnowledgeBase(
        question=question,
        answer=answer,
        keywords=keywords,
        added_by_id=operator_id,
        conversation_id=conversation_id,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)

    logger.info(f"Добавлено в базу знаний: '{question[:50]}...' -> '{answer[:50]}...'")
    return entry


def extract_keywords(text: str) -> str:
    """Извлечь ключевые слова из текста."""
    # Стоп-слова на русском и английском
    stop_words = {
        'а', 'и', 'в', 'на', 'с', 'что', 'как', 'это', 'для', 'по', 'из',
        'у', 'к', 'о', 'не', 'да', 'но', 'же', 'ли', 'бы', 'то', 'вы',
        'мы', 'он', 'она', 'они', 'вас', 'нас', 'его', 'её', 'их', 'мне',
        'есть', 'быть', 'был', 'была', 'будет', 'можно', 'нужно', 'надо',
        'сколько', 'какой', 'какая', 'какие', 'когда', 'где', 'кто', 'чем',
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
        'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
        'from', 'or', 'and', 'not', 'but', 'if', 'this', 'that', 'these',
        'those', 'what', 'which', 'who', 'whom', 'how', 'when', 'where', 'why',
    }

    # Очищаем текст
    words = text.lower().replace('?', '').replace('!', '').replace('.', '').replace(',', '').split()
    keywords = [normalize_word(w) for w in words if w not in stop_words and len(w) > 2]

    return ' '.join(keywords)


def normalize_word(word: str) -> str:
    """Простая нормализация слова — убираем окончания."""
    # Убираем типичные русские окончания для грубого стемминга
    suffixes = [
        'ться', 'ить', 'ать', 'еть', 'уть', 'оть',  # глаголы
        'ение', 'ание', 'ость', 'есть', 'ство',  # существительные
        'ого', 'его', 'ому', 'ему', 'ым', 'им', 'ой', 'ей',  # прилагательные
        'ёт', 'ет', 'ит', 'ут', 'ют', 'ат', 'ят',  # глаголы
        'ся', 'сь',  # возвратные
    ]

    word = word.lower().strip()

    for suffix in suffixes:
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            return word[:-len(suffix)]

    return word


async def search_knowledge_base(
    session: AsyncSession,
    question: str,
    threshold: float = 0.5,
) -> KnowledgeBase | None:
    """Поиск ответа в базе знаний по вопросу."""
    keywords = extract_keywords(question)
    if not keywords:
        return None

    keyword_list = keywords.split()
    # Также нормализуем ключевые слова вопроса
    normalized_question_keywords = set(normalize_word(w) for w in keyword_list)

    # Получаем все активные записи
    result = await session.execute(
        select(KnowledgeBase).where(KnowledgeBase.is_active == True)
    )
    entries = list(result.scalars().all())

    if not entries:
        return None

    # Поиск по совпадению ключевых слов с нормализацией
    best_match = None
    best_score = 0

    for entry in entries:
        if not entry.keywords:
            continue

        entry_keywords = set(entry.keywords.split())
        # Нормализуем ключевые слова записи
        normalized_entry_keywords = set(normalize_word(w) for w in entry_keywords)

        # Считаем пересечение нормализованных слов
        common = normalized_entry_keywords.intersection(normalized_question_keywords)

        # Также проверяем частичное совпадение (начало слова)
        for eq in normalized_entry_keywords:
            for qq in normalized_question_keywords:
                if eq not in common and qq not in common:
                    # Проверяем совпадение начала слова (минимум 4 буквы)
                    if len(eq) >= 4 and len(qq) >= 4:
                        if eq.startswith(qq[:4]) or qq.startswith(eq[:4]):
                            common.add(eq)

        if not normalized_entry_keywords:
            continue

        score = len(common) / max(len(normalized_entry_keywords), len(normalized_question_keywords))

        if score > best_score and score >= threshold:
            best_score = score
            best_match = entry

    if best_match:
        logger.info(f"Найдено в базе знаний (score={best_score:.2f}): '{best_match.question[:50]}...'")
        # Увеличиваем счётчик использования
        best_match.times_used += 1
        await session.commit()

    return best_match


async def get_last_qa_pair(
    session: AsyncSession,
    conversation_id: int,
) -> tuple[str, str] | None:
    """Получить последнюю пару вопрос-ответ из диалога (вопрос клиента + ответ оператора)."""
    # Получаем последние сообщения
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    messages = list(result.scalars().all())
    messages.reverse()  # Хронологический порядок

    # Ищем последний ответ оператора и предшествующий вопрос клиента
    operator_answer = None
    client_question = None

    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if msg.sender == MessageSender.operator and not operator_answer:
            operator_answer = msg.text
        elif msg.sender == MessageSender.client and operator_answer and not client_question:
            client_question = msg.text
            break

    if client_question and operator_answer:
        return (client_question, operator_answer)

    return None


async def get_all_knowledge_entries(
    session: AsyncSession,
    only_active: bool = True,
) -> list[KnowledgeBase]:
    """Получить все записи базы знаний."""
    query = select(KnowledgeBase).order_by(KnowledgeBase.times_used.desc())
    if only_active:
        query = query.where(KnowledgeBase.is_active == True)

    result = await session.execute(query)
    return list(result.scalars().all())


def should_auto_save_to_knowledge(question: str) -> bool:
    """Определить, стоит ли автоматически сохранять вопрос в базу знаний."""
    question_lower = question.lower()

    # Слова указывающие на ЛИЧНЫЙ запрос (НЕ сохранять)
    personal_indicators = [
        # Запись/бронирование
        'запиши', 'запишите', 'записать', 'забронируй', 'забронировать',
        'бронь', 'хочу записаться', 'можно записаться',
        # Даты и время
        'на завтра', 'на сегодня', 'на послезавтра', 'на выходные',
        'на понедельник', 'на вторник', 'на среду', 'на четверг',
        'на пятницу', 'на субботу', 'на воскресенье',
        'в понедельник', 'в воскресенье',
        'на утро', 'на вечер', 'на день', 'днём', 'утром', 'вечером',
        'на 1', 'на 2', 'на 3', 'на 4', 'на 5', 'на 6', 'на 7', 'на 8',
        'на 9', 'на 10', 'на 11', 'на 12',
        ':00', ':30', 'часов', 'час дня', 'часа',
        # Личные данные
        'меня зовут', 'мой номер', 'мой телефон', 'перезвоните',
        'я буду', 'мы придём', 'нас будет', 'человек',
        # Подтверждения
        'спасибо', 'хорошо', 'ок', 'понял', 'ясно', 'отлично',
        'да', 'нет', 'рахмат', 'thanks',
    ]

    # Слова указывающие на ОБЩИЙ вопрос (сохранять)
    general_indicators = [
        # Цены
        'сколько стоит', 'какая цена', 'прайс', 'стоимость', 'цены',
        'почём', 'во сколько обойдётся',
        # Информация
        'где находитесь', 'где вы', 'адрес', 'как добраться', 'как доехать',
        'режим работы', 'во сколько открываетесь', 'до скольки работаете',
        'когда работаете', 'график работы', 'выходные',
        # Услуги
        'какие есть', 'что есть', 'что включает', 'что входит',
        'расскажите про', 'расскажи про', 'что такое',
        'чем отличается', 'в чём разница', 'какая разница',
        # Условия
        'можно ли', 'есть ли', 'а есть',
        'с детьми', 'для детей', 'для взрослых',
        'скидки', 'акции',
        # Конкретные услуги
        'мастер-класс', 'мастер класс', 'свидание', 'vip', 'silver',
        'курс', 'курсы', 'отель', 'номер', 'аренда',
    ]

    # Проверяем на личные индикаторы
    for indicator in personal_indicators:
        if indicator in question_lower:
            return False

    # Проверяем на общие индикаторы
    for indicator in general_indicators:
        if indicator in question_lower:
            return True

    # По умолчанию не сохраняем (лучше пропустить, чем засорить)
    return False
