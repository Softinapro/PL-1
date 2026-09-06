from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date
from app.database import get_db
from app.models.user import User
from app.models.trip import Trip, TripStatus
from app.models.route import Route, RouteStatus
from app.models.point import Point, PointStatus
from app.api.v1.deps.auth import get_current_user, require_role

router = APIRouter(prefix="/driver", tags=["Driver"])

@router.get("/trips/today")
async def get_today_trip(
    current_user: User = Depends(require_role("driver")),
    db: AsyncSession = Depends(get_db),
):
    """Получить сегодняшний рейс для водителя"""
    
    today = date.today()
    
    # Ищем рейс на сегодня
    result = await db.execute(
        select(Trip)
        .where(Trip.driver_id == current_user.id)
        .where(Trip.date == today)
    )
    trip = result.scalar_one_or_none()
    
    if not trip:
        return {
            "status": "no_trip",
            "message": "Сегодня рейсов нет"
        }
    
    # Загружаем маршруты
    result = await db.execute(
        select(Route)
        .where(Route.trip_id == trip.id)
        .order_by(Route.order_number)
    )
    routes = result.scalars().all()
    
    # Загружаем точки для каждого маршрута
    trip_data = {
        "id": trip.id,
        "date": trip.date.isoformat(),
        "status": trip.status,
        "routes": []
    }
    
    for route in routes:
        result = await db.execute(
            select(Point)
            .where(Point.route_id == route.id)
            .order_by(Point.order_number)
        )
        points = result.scalars().all()
        
        trip_data["routes"].append({
            "id": route.id,
            "order_number": route.order_number,
            "status": route.status,
            "address_start": route.address_start,
            "address_end": route.address_end,
            "rejection_reason": route.rejection_reason,
            "points": [
                {
                    "id": p.id,
                    "order_number": p.order_number,
                    "address": p.address,
                    "status": p.status,
                    "rejection_reason": p.rejection_reason,
                }
                for p in points
            ]
        })
    
    return trip_data
