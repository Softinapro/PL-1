from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.trip import Trip, TripStatus
from app.models.route import Route, RouteStatus
from app.models.point import Point, PointStatus
from app.api.v1.deps.auth import verify_api_key
from pydantic import BaseModel
from datetime import date
from decimal import Decimal
from typing import List, Optional

router = APIRouter(prefix="/import", tags=["Import"])


# ========== СХЕМЫ ДЛЯ ВХОДНЫХ ДАННЫХ ==========

class PointImportSchema(BaseModel):
    code: str                              # код точки из 1С
    order_number: int
    address: str
    weight: Optional[Decimal] = None       # вес, кг


class RouteImportSchema(BaseModel):
    order_number: int
    name: Optional[str] = None
    address_start: str
    address_end: str
    points: List[PointImportSchema]


class TripImportSchema(BaseModel):
    driver_code: str                       # код водителя (физлицо)
    logist_code: Optional[str] = None      # код логиста (пользователи), необязателен
    date: date
    info: Optional[str] = None
    routes: List[RouteImportSchema]


# ========== ЭНДПОИНТ ==========

@router.post("/trips")
async def import_trips(
    trips_data: List[TripImportSchema],
    _: bool = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Импорт рейсов из 1С.
    Ожидает список рейсов с маршрутами и точками.
    Если рейс на дату уже есть — затирает старый.
    """
    results = []
    errors = []

    for trip_data in trips_data:
        try:
            # 1. Находим водителя по коду
            driver_result = await db.execute(
                select(User).where(User.code == trip_data.driver_code)
            )
            driver = driver_result.scalar_one_or_none()
            if not driver:
                errors.append({
                    "driver_code": trip_data.driver_code,
                    "error": "Водитель не найден"
                })
                continue

            # 2. Логист не ищется в User — только фиксируем код из 1С

            # 3. Если рейс на эту дату уже есть — УДАЛЯЕМ (затираем)
            existing_trip_result = await db.execute(
                select(Trip).where(
                    Trip.driver_id == driver.id,
                    Trip.date == trip_data.date
                )
            )
            existing_trip = existing_trip_result.scalar_one_or_none()
            if existing_trip:
                # Cascade удалит Route и Point
                await db.delete(existing_trip)
                await db.flush()

            # 4. Создаём рейс
            trip = Trip(
                driver_id=driver.id,
                logist_id=None,                          # ← всегда None (пока)
                logist_code=trip_data.logist_code,       # ← код из 1С
                date=trip_data.date,
                status=TripStatus.PENDING,
                info=trip_data.info,
            )
            db.add(trip)
            await db.flush()

            # 5. Создаём маршруты
            for route_data in trip_data.routes:
                route = Route(
                    trip_id=trip.id,
                    order_number=route_data.order_number,
                    name=route_data.name,
                    address_start=route_data.address_start,
                    address_end=route_data.address_end,
                    status=RouteStatus.PENDING,
                )
                db.add(route)
                await db.flush()

                # 6. Создаём точки
                for point_data in route_data.points:
                    point = Point(
                        route_id=route.id,
                        code=point_data.code,
                        date=trip_data.date,
                        order_number=point_data.order_number,
                        address=point_data.address,
                        weight=point_data.weight,
                        status=PointStatus.PENDING,
                    )
                    db.add(point)

            # 7. Коммитим ВСЁ для этого Trip
            await db.commit()
            results.append({
                "driver_code": trip_data.driver_code,
                "date": trip_data.date.isoformat(),
                "status": "created",
                "trip_id": trip.id,
                "routes_count": len(trip_data.routes),
            })

        except Exception as e:
            await db.rollback()
            errors.append({
                "driver_code": trip_data.driver_code,
                "error": str(e)
            })

    return {
        "status": "completed",
        "created": results,
        "errors": errors,
    }