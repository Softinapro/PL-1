from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.trip import Trip, TripStatus
from app.models.route import Route, RouteStatus
from app.models.point import Point, PointStatus
from app.api.v1.deps.auth import get_current_user, require_role
from pydantic import BaseModel
from datetime import date
from typing import List, Optional

router = APIRouter(prefix="/import", tags=["Import"])

# ========== СХЕМЫ ДЛЯ ВХОДНЫХ ДАННЫХ ==========

class PointImportSchema(BaseModel):
    order_number: int
    address: str

class RouteImportSchema(BaseModel):
    order_number: int
    address_start: str
    address_end: str
    points: List[PointImportSchema]

class TripImportSchema(BaseModel):
    driver_phone: str
    logist_phone: str
    date: date
    routes: List[RouteImportSchema]


# ========== ЭНДПОИНТ ==========

@router.post("/trips")
async def import_trips(
    trips_data: List[TripImportSchema],
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Импорт рейсов из 1С.
    Ожидает список рейсов с маршрутами и точками.
    """
    results = []
    errors = []

    for trip_data in trips_data:
        try:
            # 1. Находим водителя по телефону
            driver_result = await db.execute(
                select(User).where(User.phone == trip_data.driver_phone)
            )
            driver = driver_result.scalar_one_or_none()
            if not driver:
                errors.append({
                    "driver_phone": trip_data.driver_phone,
                    "error": "Водитель не найден"
                })
                continue

            # 2. Находим логиста по телефону
            logist_result = await db.execute(
                select(User).where(User.phone == trip_data.logist_phone)
            )
            logist = logist_result.scalar_one_or_none()
            if not logist:
                errors.append({
                    "logist_phone": trip_data.logist_phone,
                    "error": "Логист не найден"
                })
                continue

            # 3. Проверяем, есть ли уже рейс на эту дату
            existing_trip = await db.execute(
                select(Trip).where(
                    Trip.driver_id == driver.id,
                    Trip.date == trip_data.date
                )
            )
            if existing_trip.scalar_one_or_none():
                errors.append({
                    "driver_phone": trip_data.driver_phone,
                    "date": trip_data.date.isoformat(),
                    "error": "Рейс на эту дату уже существует"
                })
                continue

            # 4. Создаём рейс
            trip = Trip(
                driver_id=driver.id,
                logist_id=logist.id,
                date=trip_data.date,
                status=TripStatus.PENDING,
            )
            db.add(trip)
            await db.flush()

            # 5. Создаём маршруты
            for route_data in trip_data.routes:
                route = Route(
                    trip_id=trip.id,
                    order_number=route_data.order_number,
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
                        order_number=point_data.order_number,
                        address=point_data.address,
                        status=PointStatus.PENDING,
                    )
                    db.add(point)

            results.append({
                "driver_phone": trip_data.driver_phone,
                "date": trip_data.date.isoformat(),
                "status": "created",
                "trip_id": trip.id,
                "routes_count": len(trip_data.routes),
            })

        except Exception as e:
            errors.append({
                "driver_phone": trip_data.driver_phone,
                "error": str(e)
            })

    await db.commit()

    return {
        "status": "completed",
        "created": results,
        "errors": errors,
    }
