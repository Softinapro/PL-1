from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.trip import Trip
from app.api.v1.deps.auth import verify_api_key
from app.core.integrations.max_bot import MaxBotAPI
from pydantic import BaseModel
from datetime import date
from typing import List

router = APIRouter(prefix="/import", tags=["Import"])

# Один экземпляр бота для модуля
bot = MaxBotAPI()


# ========== СХЕМА ==========

class RevokeTripsRequest(BaseModel):
    date: date
    driver_codes: List[str]


# ========== ЭНДПОИНТ ==========

@router.post("/trips/revoke")
async def revoke_trips(
    request: RevokeTripsRequest,
    _: bool = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Отзыв предложений из 1С.
    Одна дата на весь запрос. По каждому водителю — удаляем Trip на дату.
    После удаления — уведомление водителю в MAX.
    """
    revoked = []
    errors = []
    shipment_date = request.date

    for driver_code in request.driver_codes:
        try:
            # 1. Находим водителя
            driver_result = await db.execute(
                select(User).where(User.code == driver_code)
            )
            driver = driver_result.scalar_one_or_none()
            if not driver:
                errors.append({
                    "driver_code": driver_code,
                    "error": "Водитель не найден",
                })
                continue

            # 2. Находим Trip на дату
            trip_result = await db.execute(
                select(Trip).where(
                    Trip.driver_id == driver.id,
                    Trip.date == shipment_date,
                )
            )
            trip = trip_result.scalar_one_or_none()
            if not trip:
                errors.append({
                    "driver_code": driver_code,
                    "error": "Trip не найден",
                })
                continue

            # 3. Запоминаем ДО удаления
            trip_id = trip.id
            max_user_id = driver.max_user_id

            # 4. Удаляем (cascade: Route + Point)
            await db.delete(trip)
            await db.commit()

            # 5. Уведомление
            notification_sent = False
            notification_error = None
            if max_user_id:
                try:
                    await bot.send_revoked_notification(
                        user_id=max_user_id,
                        trip_date=shipment_date.strftime("%d.%m.%Y"),
                    )
                    notification_sent = True
                except Exception as e:
                    notification_error = str(e)

            # 6. Формируем результат
            entry = {
                "driver_code": driver_code,
                "trip_id": trip_id,
                "notification_sent": notification_sent,
            }
            if notification_error:
                entry["notification_error"] = notification_error
            revoked.append(entry)

        except Exception as e:
            await db.rollback()
            errors.append({
                "driver_code": driver_code,
                "error": str(e),
            })

    return {
        "status": "completed",
        "date": shipment_date.isoformat(),
        "revoked": revoked,
        "errors": errors,
    }