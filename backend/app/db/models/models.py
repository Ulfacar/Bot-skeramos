import enum
from datetime import datetime, timezone, timedelta

BISHKEK_TZ = timezone(timedelta(hours=6))


def now_bishkek():
    return datetime.now(BISHKEK_TZ).replace(tzinfo=None)

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# --- Енамы ---

class ChannelType(str, enum.Enum):
    telegram = "telegram"
    whatsapp = "whatsapp"


class ConversationStatus(str, enum.Enum):
    in_progress = "in_progress"        # Бот ведёт диалог
    bot_completed = "bot_completed"    # Бот справился сам
    needs_operator = "needs_operator"  # Требует менеджера
    operator_active = "operator_active"  # Менеджер отвечает
    closed = "closed"                  # Закрыт


class ConversationCategory(str, enum.Enum):
    master_class = "master_class"      # Мастер-класс
    hotel = "hotel"                    # Отель
    custom_order = "custom_order"      # Индивидуальный заказ
    general = "general"                # Общий вопрос


class MessageSender(str, enum.Enum):
    client = "client"
    bot = "bot"
    operator = "operator"


class Language(str, enum.Enum):
    ru = "ru"
    ky = "ky"


# --- Модели ---

class Client(Base):
    """Клиент — человек который пишет боту"""
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    username = Column(String(255), nullable=True)
    channel = Column(Enum(ChannelType), nullable=False)
    channel_user_id = Column(String(255), nullable=False)  # ID в мессенджере
    language = Column(Enum(Language), default=Language.ru)
    created_at = Column(DateTime, default=now_bishkek)

    conversations = relationship("Conversation", back_populates="client")


class Conversation(Base):
    """Диалог — одна сессия общения с клиентом"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    status = Column(Enum(ConversationStatus), default=ConversationStatus.in_progress)
    category = Column(Enum(ConversationCategory), default=ConversationCategory.general)
    assigned_operator_id = Column(Integer, ForeignKey("operators.id"), nullable=True)
    created_at = Column(DateTime, default=now_bishkek)
    updated_at = Column(DateTime, default=now_bishkek, onupdate=now_bishkek)

    client = relationship("Client", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")
    assigned_operator = relationship("Operator", back_populates="conversations")


class Message(Base):
    """Сообщение в диалоге"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender = Column(Enum(MessageSender), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=now_bishkek)

    conversation = relationship("Conversation", back_populates="messages")


class Operator(Base):
    """Менеджер / оператор в админке"""
    __tablename__ = "operators"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    telegram_id = Column(String(255), nullable=True)  # Для уведомлений в TG
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_bishkek)

    conversations = relationship("Conversation", back_populates="assigned_operator")


class Booking(Base):
    """Запись / бронирование"""
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    category = Column(Enum(ConversationCategory), nullable=False)
    details = Column(Text, nullable=True)  # JSON с деталями (дата, время, кол-во и т.д.)
    confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now_bishkek)


class KnowledgeBase(Base):
    """База знаний — ответы которые бот выучил от менеджеров"""
    __tablename__ = "knowledge_base"

    id = Column(Integer, primary_key=True)
    question = Column(Text, nullable=False)      # Вопрос клиента
    answer = Column(Text, nullable=False)        # Ответ менеджера
    keywords = Column(Text, nullable=True)       # Ключевые слова для поиска
    added_by_id = Column(Integer, ForeignKey("operators.id"), nullable=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    is_active = Column(Boolean, default=True)    # Можно отключить без удаления
    times_used = Column(Integer, default=0)      # Сколько раз использовался
    created_at = Column(DateTime, default=now_bishkek)
    updated_at = Column(DateTime, default=now_bishkek, onupdate=now_bishkek)

    added_by = relationship("Operator")
