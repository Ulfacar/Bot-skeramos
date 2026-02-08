# API для базы знаний
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.database import get_session
from app.db.models.models import KnowledgeBase, Operator
from app.core.auth import get_current_operator

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeEntryOut(BaseModel):
    id: int
    question: str
    answer: str
    keywords: str | None
    is_active: bool
    times_used: int
    added_by_name: str | None
    created_at: str

    class Config:
        from_attributes = True


class KnowledgeEntryCreate(BaseModel):
    question: str
    answer: str


class KnowledgeEntryUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    is_active: bool | None = None


@router.get("", response_model=list[KnowledgeEntryOut])
async def get_knowledge_entries(
    session: AsyncSession = Depends(get_session),
    current_operator: Operator = Depends(get_current_operator),
):
    """Получить все записи базы знаний."""
    result = await session.execute(
        select(KnowledgeBase).order_by(KnowledgeBase.times_used.desc())
    )
    entries = list(result.scalars().all())

    # Получаем имена операторов
    response = []
    for entry in entries:
        added_by_name = None
        if entry.added_by_id:
            op_result = await session.execute(
                select(Operator).where(Operator.id == entry.added_by_id)
            )
            operator = op_result.scalar_one_or_none()
            if operator:
                added_by_name = operator.name

        response.append(KnowledgeEntryOut(
            id=entry.id,
            question=entry.question,
            answer=entry.answer,
            keywords=entry.keywords,
            is_active=entry.is_active,
            times_used=entry.times_used,
            added_by_name=added_by_name,
            created_at=entry.created_at.isoformat() if entry.created_at else "",
        ))

    return response


@router.post("", response_model=KnowledgeEntryOut)
async def create_knowledge_entry(
    data: KnowledgeEntryCreate,
    session: AsyncSession = Depends(get_session),
    current_operator: Operator = Depends(get_current_operator),
):
    """Создать новую запись в базе знаний."""
    from app.services.knowledge import extract_keywords

    entry = KnowledgeBase(
        question=data.question,
        answer=data.answer,
        keywords=extract_keywords(data.question),
        added_by_id=current_operator.id,
        is_active=True,
        times_used=0,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)

    return KnowledgeEntryOut(
        id=entry.id,
        question=entry.question,
        answer=entry.answer,
        keywords=entry.keywords,
        is_active=entry.is_active,
        times_used=entry.times_used,
        added_by_name=current_operator.name,
        created_at=entry.created_at.isoformat() if entry.created_at else "",
    )


@router.put("/{entry_id}", response_model=KnowledgeEntryOut)
async def update_knowledge_entry(
    entry_id: int,
    data: KnowledgeEntryUpdate,
    session: AsyncSession = Depends(get_session),
    current_operator: Operator = Depends(get_current_operator),
):
    """Обновить запись в базе знаний."""
    from app.services.knowledge import extract_keywords

    result = await session.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == entry_id)
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if data.question is not None:
        entry.question = data.question
        entry.keywords = extract_keywords(data.question)
    if data.answer is not None:
        entry.answer = data.answer
    if data.is_active is not None:
        entry.is_active = data.is_active

    await session.commit()
    await session.refresh(entry)

    # Получаем имя оператора
    added_by_name = None
    if entry.added_by_id:
        op_result = await session.execute(
            select(Operator).where(Operator.id == entry.added_by_id)
        )
        operator = op_result.scalar_one_or_none()
        if operator:
            added_by_name = operator.name

    return KnowledgeEntryOut(
        id=entry.id,
        question=entry.question,
        answer=entry.answer,
        keywords=entry.keywords,
        is_active=entry.is_active,
        times_used=entry.times_used,
        added_by_name=added_by_name,
        created_at=entry.created_at.isoformat() if entry.created_at else "",
    )


@router.delete("/{entry_id}")
async def delete_knowledge_entry(
    entry_id: int,
    session: AsyncSession = Depends(get_session),
    current_operator: Operator = Depends(get_current_operator),
):
    """Удалить запись из базы знаний."""
    result = await session.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == entry_id)
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    await session.delete(entry)
    await session.commit()

    return {"ok": True, "message": "Запись удалена"}
