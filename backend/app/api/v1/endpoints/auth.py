from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User, UserRole
from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login")
async def login(phone: str, db: AsyncSession = Depends(get_db)):
    """Вход по номеру телефона. Возвращает JWT токен."""
    
    # Ищем пользователя
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь заблокирован"
        )
    
    # Создаём JWT
    token_data = {
        "sub": str(user.id),
        "phone": user.phone,
        "role": user.role.value,
    }
    access_token = create_access_token(token_data)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "phone": user.phone,
            "full_name": user.full_name,
            "role": user.role.value,
        }
    }

# ============================================================
# ПРИВЯЗКА К MAX
# ============================================================

@router.post("/max/bind")
async def bind_to_max(
    init_data: str,
    phone: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Привязка аккаунта MAX к водителю.
    Принимает initData от MAX и номер телефона из deep link.
    """
    from app.core.integrations.max_validator import validate_init_data
    from app.core.security import create_access_token
    
    # 1. Нормализуем телефон
    from app.utils.phone_utils import normalize_phone
    try:
        phone_normalized = normalize_phone(phone)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # 2. Ищем водителя
    result = await db.execute(
        select(User).where(User.phone == phone_normalized)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Водитель не найден")
    
    if user.role != UserRole.DRIVER:
        raise HTTPException(status_code=403, detail="Только водители могут привязываться")
    
    # 3. Валидируем initData
    try:
        max_user_data = validate_init_data(init_data)
        max_user_id = max_user_data.get('id')
        if not max_user_id:
            raise ValueError("User ID not found in initData")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Ошибка валидации: {str(e)}")
    
    # 4. Проверяем, не привязан ли уже этот MAX ID к другому пользователю
    existing = await db.execute(
        select(User).where(User.max_user_id == str(max_user_id))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Этот аккаунт MAX уже привязан к другому пользователю")
    
    # 5. Сохраняем max_user_id
    user.max_user_id = str(max_user_id)
    await db.commit()
    await db.refresh(user)
    
    # 6. Выдаём JWT
    token_data = {
        "sub": str(user.id),
        "phone": user.phone,
        "role": user.role.value,
    }
    access_token = create_access_token(token_data)
    
    return {
        "status": "ok",
        "message": "Аккаунт MAX привязан",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "phone": user.phone,
            "full_name": user.full_name,
            "role": user.role.value,
        }
    }
