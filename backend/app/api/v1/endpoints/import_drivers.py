from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List

from app.database import get_db
from app.models.user import User, UserRole
from app.api.v1.deps.auth import verify_api_key
from app.utils.phone_utils import normalize_phone

router = APIRouter(prefix="/import", tags=["Import"])


class DriverImportSchema(BaseModel):
    code: str          # код из 1С (физлицо)
    phone: str         # телефон, 9001234567
    full_name: str     # ФИО


@router.post("/drivers")
async def import_drivers(
    drivers_data: List[DriverImportSchema],
    _: bool = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Импорт/обновление справочника водителей из 1С.
    По коду находит водителя, обновляет телефон и ФИО (после валидации).
    """
    created = []
    updated = []
    unchanged = []
    errors = []

    for driver_data in drivers_data:
        try:
            # 1. Нормализуем телефон
            try:
                normalized_phone = normalize_phone(driver_data.phone)
            except ValueError as e:
                errors.append({
                    "code": driver_data.code,
                    "error": f"Некорректный телефон: {e}",
                })
                continue

            # 2. Ищем пользователя по коду
            result = await db.execute(
                select(User).where(User.code == driver_data.code)
            )
            user = result.scalar_one_or_none()

            if user is None:
                # 3. Новый водитель — создаём
                user = User(
                    code=driver_data.code,
                    phone=normalized_phone,
                    full_name=driver_data.full_name,
                    role=UserRole.DRIVER,
                )
                db.add(user)
                created.append({
                    "code": driver_data.code,
                    "phone": normalized_phone,
                    "full_name": driver_data.full_name,
                })

            elif user.phone != normalized_phone or user.full_name != driver_data.full_name:
                # 4. Что-то изменилось — обновляем
                old_phone = user.phone
                old_name = user.full_name
                user.phone = normalized_phone
                user.full_name = driver_data.full_name
                updated.append({
                    "code": driver_data.code,
                    "old_phone": old_phone,
                    "new_phone": normalized_phone,
                    "old_name": old_name,
                    "new_name": driver_data.full_name,
                })

            else:
                # 5. Ничего не изменилось
                unchanged.append({"code": driver_data.code})

        except Exception as e:
            errors.append({
                "code": driver_data.code,
                "error": str(e),
            })

    await db.commit()

    return {
        "status": "completed",
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "errors": errors,
    }