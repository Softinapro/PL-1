from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import date as date_type

from app.database import get_db
from app.models.user import User
from app.models.trip import Trip
from app.models.route import Route
from app.api.v1.deps.auth import verify_api_key

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/trips")
async def export_trips(
    date: date_type,
    _: bool = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Экспорт всех рейсов на указанную дату отгрузки.
    Используется 1С для получения актуальных статусов.
    """
    # 1. Ищем все Trip на дату с подгрузкой связей
    result = await db.execute(
        select(Trip)
        .where(Trip.date == date)
        .options(
            selectinload(Trip.driver),
            selectinload(Trip.routes).selectinload(Route.points),
        )
        .order_by(Trip.id)
    )
    trips = result.scalars().all()

    # 2. Формируем ответ
    trips_data = []
    for trip in trips:
        # Сортируем маршруты и точки по order_number
        sorted_routes = sorted(trip.routes, key=lambda r: r.order_number)
        
        routes_data = []
        for route in sorted_routes:
            sorted_points = sorted(route.points, key=lambda p: p.order_number)
            
            points_data = []
            for point in sorted_points:
                points_data.append({
                    "point_id": point.id,
                    "code": point.code,
                    "order_number": point.order_number,
                    "address": point.address,
                    "weight": str(point.weight) if point.weight is not None else None,
                    "status": point.status.value,
                    "rejection_reason": point.rejection_reason,
                })
            
            routes_data.append({
                "route_id": route.id,
                "name": route.name,
                "order_number": route.order_number,
                "status": route.status.value,
                "rejection_reason": route.rejection_reason,
                "address_start": route.address_start,
                "address_end": route.address_end,
                "points": points_data,
            })
        
        trips_data.append({
            "trip_id": trip.id,
            "driver_code": trip.driver.code,
            "driver_name": trip.driver.full_name,
            "driver_phone": trip.driver.phone,
            "logist_code": trip.logist_code,
            "status": trip.status.value,
            "info": trip.info,
            "routes": routes_data,
        })

    return {
        "date": date.isoformat(),
        "trips": trips_data,
    }