from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import OperatorCreate, OperatorOut
from app.core.auth import get_current_operator, hash_password
from app.db.database import get_session
from app.db.models.models import Operator

router = APIRouter(prefix="/operators", tags=["Operators"])


@router.get("/", response_model=list[OperatorOut])
async def list_operators(
    session: AsyncSession = Depends(get_session),
    current: Operator = Depends(get_current_operator),
):
    """Список всех менеджеров. Только для админов."""
    if not current.is_admin:
        raise HTTPException(status_code=403, detail="Только для админов")

    result = await session.execute(
        select(Operator).order_by(Operator.created_at.asc())
    )
    return result.scalars().all()


@router.post("/", response_model=OperatorOut, status_code=201)
async def create_operator(
    data: OperatorCreate,
    session: AsyncSession = Depends(get_session),
    current: Operator = Depends(get_current_operator),
):
    """Создать нового менеджера. Только для админов."""
    if not current.is_admin:
        raise HTTPException(status_code=403, detail="Только для админов")

    # Проверяем уникальность email
    result = await session.execute(
        select(Operator).where(Operator.email == data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email уже используется")

    operator = Operator(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        is_admin=data.is_admin,
        telegram_id=data.telegram_id,
    )
    session.add(operator)
    await session.commit()
    await session.refresh(operator)
    return operator


@router.patch("/{operator_id}/deactivate", response_model=OperatorOut)
async def deactivate_operator(
    operator_id: int,
    session: AsyncSession = Depends(get_session),
    current: Operator = Depends(get_current_operator),
):
    """Деактивировать менеджера. Только для админов."""
    if not current.is_admin:
        raise HTTPException(status_code=403, detail="Только для админов")

    result = await session.execute(
        select(Operator).where(Operator.id == operator_id)
    )
    operator = result.scalar_one_or_none()
    if not operator:
        raise HTTPException(status_code=404, detail="Менеджер не найден")

    operator.is_active = False
    await session.commit()
    await session.refresh(operator)
    return operator
