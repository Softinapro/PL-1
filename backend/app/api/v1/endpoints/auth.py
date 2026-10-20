from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, UserRole
from app.config import settings
from app.core.security import create_access_token
from app.core.integrations.max_validator import validate_init_data
from app.api.v1.schemas.auth import TokenResponse, UserPublic


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/max/bind", response_model=TokenResponse)
async def bind_to_max(
    x_max_init_data: str = Header(..., alias="X-Max-InitData"),
    db: AsyncSession = Depends(get_db),
):
    """
    Вход водителя через мини-приложение MAX.

    Принимает initData из MAX Bridge в заголовке X-Max-InitData,
    валидирует подпись, находит User по max_user_id и выдаёт JWT.
    """
    parsed = validate_init_data(x_max_init_data, settings.MAX_BOT_TOKEN)
    if not parsed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный initData",
        )

    max_user = parsed.get("user") or {}
    max_user_id = str(max_user.get("id") or "").strip()
    if not max_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MAX не передал идентификатор пользователя",
        )

    result = await db.execute(
        select(User).where(User.max_user_id == max_user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Вы не зарегистрированы в системе. Обратитесь к логисту.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь заблокирован",
        )
    if user.is_archived:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь в архиве",
        )
    if user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для водителей",
        )

    access_token = create_access_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        user=UserPublic.model_validate(user),
    )


from app.utils.phone_utils import normalize_phone
from app.api.v1.schemas.auth import ContactBindRequest
from app.core.integrations.max_validator import validate_contact_hash


@router.post("/max/contact", response_model=TokenResponse)
async def bind_by_contact(
    request: ContactBindRequest,
    db: AsyncSession = Depends(get_db),
):
    """Привязка по номеру телефона через requestContact()."""
    if not validate_contact_hash(
        phone=request.phone,
        auth_date=request.auth_date,
        user_id=request.user_id,
        received_hash=request.hash,
        bot_token=settings.MAX_BOT_TOKEN,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный hash от requestContact",
        )

    try:
        normalized_phone = normalize_phone(request.phone)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось распознать номер телефона",
        )

    result = await db.execute(
        select(User).where(User.phone == normalized_phone)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Вы не зарегистрированы в системе. Обратитесь к логисту.",
        )

    max_user_id_str = str(request.user_id)
    if user.max_user_id and user.max_user_id != max_user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Этот номер уже привязан к другому MAX-аккаунту.",
        )

    if not user.max_user_id:
        user.max_user_id = max_user_id_str
        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise HTTPException(403, "Пользователь заблокирован")
    if user.is_archived:
        raise HTTPException(403, "Пользователь в архиве")
    if user.role != UserRole.DRIVER:
        raise HTTPException(403, "Доступ только для водителей")

    access_token = create_access_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        user=UserPublic.model_validate(user),
    )
