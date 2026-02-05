from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.db.models.models import (
    ChannelType,
    ConversationCategory,
    ConversationStatus,
    Language,
    MessageSender,
)


# --- Auth ---

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Operator ---

class OperatorCreate(BaseModel):
    name: str
    email: str
    password: str
    is_admin: bool = False
    telegram_id: Optional[str] = None


class OperatorOut(BaseModel):
    id: int
    name: str
    email: str
    is_admin: bool
    telegram_id: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Client ---

class ClientOut(BaseModel):
    id: int
    name: Optional[str]
    phone: Optional[str]
    username: Optional[str]
    channel: ChannelType
    channel_user_id: str
    language: Language
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Conversation ---

class ConversationOut(BaseModel):
    id: int
    client_id: int
    status: ConversationStatus
    category: ConversationCategory
    assigned_operator_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    client: Optional[ClientOut] = None

    model_config = {"from_attributes": True}


class ConversationUpdate(BaseModel):
    status: Optional[ConversationStatus] = None
    category: Optional[ConversationCategory] = None
    assigned_operator_id: Optional[int] = None


# --- Message ---

class MessageOut(BaseModel):
    id: int
    conversation_id: int
    sender: MessageSender
    text: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    text: str
