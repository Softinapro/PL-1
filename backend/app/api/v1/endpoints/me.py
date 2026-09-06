from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.api.v1.deps.auth import get_current_user

router = APIRouter(prefix="/me", tags=["Profile"])

@router.get("/")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Получить свой профиль (для любого авторизованного пользователя)"""
    return {
        "id": current_user.id,
        "phone": current_user.phone,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
    }

@router.get("/role")
async def get_my_role(
    current_user: User = Depends(get_current_user),
):
    """Узнать свою роль"""
    return {"role": current_user.role.value}
