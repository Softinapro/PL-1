from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.trip import Trip, TripStatus
from app.models.route import Route, RouteStatus
from app.models.point import Point, PointStatus
from app.api.v1.deps.auth import verify_api_key
from app.core.integrations.max_bot import MaxBotAPI
from pydantic import BaseModel
from datetime import date
from decimal import Decimal
from typing import List, Optional

router = APIRouter(prefix="/import", tags=["Import"])

# Создаём один экземпляр бота для всего модуля
bot = MaxBotAPI()


# ========== СХЕМЫ ДЛЯ ВХОДНЫХ ДАННЫХ ==========

class PointImportSchema(BaseModel):
    code: str                              # код точки из 1С
    order_number: int
    address: str
    weight: Optional[Decimal] = None       # вес, кг


class RouteImportSchema(BaseModel):
    order_number: int
    name: Optional[str] = None
    points: List[PointImportSchema]


class TripImportSchema(BaseModel):
    driver_code: str                       # код водителя (физлицо)
    logist_code: Optional[str] = None      # код логиста (пользователи), необязателен
    info: Optional[str] = None
    routes: List[RouteImportSchema]


class TripsImportRequest(BaseModel):
    date: date                             # одна дата на весь запрос
    trips: List[TripImportSchema]


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def validate_trip(trip_data: TripImportSchema) -> Optional[str]:
    """
    Проверяет структуру Trip'а.
    Возвращает текст ошибки или None, если всё ок.
    """
    if not trip_data.routes:
        return "У Trip'а нет маршрутов"
    for route_data in trip_data.routes:
        if not route_data.points:
            return f"У маршрута #{route_data.order_number} нет точек"
    return None


def calculate_totals(routes: List[RouteImportSchema]) -> dict:
    """
    Считает итоги по рейсу из входных данных:
    - количество маршрутов
    - количество точек
    - общий вес (Decimal или None)
    """
    routes_count = len(routes)
    points_count = sum(len(route.points) for route in routes)

    weights = [
        point.weight
        for route in routes
        for point in route.points
        if point.weight is not None
    ]
    total_weight = sum(weights, start=Decimal("0")) if weights else None

    return {
        "routes_count": routes_count,
        "points_count": points_count,
        "total_weight": total_weight,
    }


async def send_trip_notification(
    driver: User,
    trip_id: int,
    trip_date: str,
    routes_count: int,
    points_count: int,
    total_weight: Optional[Decimal],
    is_update: bool = False,
) -> dict:
    """
    Отправляет уведомление водителю о новом рейсе.
    Возвращает {"sent": bool, "error": str | None}.
    """
    if not driver.max_user_id:
        return {
            "sent": False,
            "error": "У водителя нет max_user_id (не привязан к MAX)",
        }

    try:
        await bot.send_notification(
            user_id=driver.max_user_id,
            trip_id=trip_id,
            trip_date=trip_date,
            routes_count=routes_count,
            points_count=points_count,
            total_weight=total_weight,
            is_update=is_update,
        )
        return {"sent": True, "error": None}
    except Exception as e:
        return {"sent": False, "error": str(e)}


# ========== ЭНДПОИНТ ==========

@router.post("/trips")
async def import_trips(
    request: TripsImportRequest,
    _: bool = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Импорт рейсов из 1С.
    Одна дата на весь запрос. Каждый Trip обрабатывается в своей транзакции.
    Если рейс на дату уже есть — затирает старый.
    После создания — отправляет уведомление водителю в MAX.
    """
    created = []
    errors = []
    shipment_date = request.date

    for trip_data in request.trips:
        # 1. Валидация структуры (до транзакции)
        validation_error = validate_trip(trip_data)
        if validation_error:
            errors.append({
                "driver_code": trip_data.driver_code,
                "error": validation_error,
            })
            continue

        try:
            # 2. Находим водителя по коду
            driver_result = await db.execute(
                select(User).where(User.code == trip_data.driver_code)
            )
            driver = driver_result.scalar_one_or_none()
            if not driver:
                errors.append({
                    "driver_code": trip_data.driver_code,
                    "error": "Водитель не найден",
                })
                continue

            # 3. Считаем итоги из входных данных
            totals = calculate_totals(trip_data.routes)

                        # 4. Если рейс на эту дату уже есть — УДАЛЯЕМ (затираем)
            existing_trip_result = await db.execute(
                select(Trip).where(
                    Trip.driver_id == driver.id,
                    Trip.date == shipment_date,
                )
            )
            existing_trip = existing_trip_result.scalar_one_or_none()
            is_update = existing_trip is not None
            if existing_trip:
                await db.delete(existing_trip)
                await db.flush()

            # 5. Создаём рейс
            trip = Trip(
                driver_id=driver.id,
                logist_id=None,
                logist_code=trip_data.logist_code,
                date=shipment_date,
                status=TripStatus.PENDING,
                info=trip_data.info,
            )
            db.add(trip)
            await db.flush()

            # 6. Создаём маршруты
            for route_data in trip_data.routes:
                route = Route(
                    trip_id=trip.id,
                    order_number=route_data.order_number,
                    name=route_data.name,
                    status=RouteStatus.PENDING,
                )
                db.add(route)
                await db.flush()

                # 7. Создаём точки
                for point_data in route_data.points:
                    point = Point(
                        route_id=route.id,
                        code=point_data.code,
                        date=shipment_date,
                        order_number=point_data.order_number,
                        address=point_data.address,
                        weight=point_data.weight,
                        status=PointStatus.PENDING,
                    )
                    db.add(point)

            # 8. Коммитим всё для этого Trip
            await db.commit()

            # 9. Отправляем уведомление водителю
            notif_result = await send_trip_notification(
                driver=driver,
                trip_id=trip.id,
                trip_date=shipment_date.strftime("%d.%m.%Y"),
                routes_count=totals["routes_count"],
                points_count=totals["points_count"],
                total_weight=totals["total_weight"],
                is_update=is_update,
            )

            # 10. Формируем результат
            result_entry = {
                "driver_code": trip_data.driver_code,
                "status": "created",
                "trip_id": trip.id,
                "routes_count": totals["routes_count"],
                "points_count": totals["points_count"],
                "total_weight": str(totals["total_weight"]) if totals["total_weight"] is not None else None,
                "notification_sent": notif_result["sent"],
            }
            if not notif_result["sent"]:
                result_entry["notification_error"] = notif_result["error"]
            created.append(result_entry)

        except Exception as e:
            await db.rollback()
            errors.append({
                "driver_code": trip_data.driver_code,
                "error": str(e),
            })

    return {
        "status": "completed",
        "date": shipment_date.isoformat(),
        "created": created,
        "errors": errors,
    }