from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, timedelta
from app.database import get_db
from app.models.user import User
from app.models.trip import Trip, TripStatus
from app.models.route import Route, RouteStatus
from app.models.point import Point, PointStatus
from app.api.v1.deps.auth import require_role

router = APIRouter(prefix="/driver", tags=["Driver"])

async def get_trip_with_details(db: AsyncSession, trip: Trip):
    """Загружает маршруты и точки для рейса с использованием selectinload"""
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip.id)
        .options(
            selectinload(Trip.routes).selectinload(Route.points)
        )
    )
    return result.scalar_one()


@router.get("/trips/today")
async def get_today_trip(
    current_user: User = Depends(require_role("driver")),
    db: AsyncSession = Depends(get_db),
):
    """Получить рейс на сегодня"""
    from sqlalchemy.orm import selectinload
    
    today = date.today()
    
    result = await db.execute(
        select(Trip)
        .where(Trip.driver_id == current_user.id)
        .where(Trip.date == today)
        .options(
            selectinload(Trip.routes).selectinload(Route.points)
        )
    )
    trip = result.scalar_one_or_none()
    
    if not trip:
        return {"status": "no_trip", "message": "Сегодня рейсов нет"}
    
    return {
        "id": trip.id,
        "date": trip.date.isoformat(),
        "status": trip.status,
        "routes": [
            {
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
                    for p in route.points
                ]
            }
            for route in trip.routes
        ]
    }


@router.get("/trips/upcoming")
async def get_upcoming_trip(
    current_user: User = Depends(require_role("driver")),
    db: AsyncSession = Depends(get_db),
):
    """Получить ближайший рейс (сегодня или завтра)"""
    from sqlalchemy.orm import selectinload
    
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    result = await db.execute(
        select(Trip)
        .where(Trip.driver_id == current_user.id)
        .where(Trip.date.in_([today, tomorrow]))
        .order_by(Trip.date)
        .limit(1)
        .options(
            selectinload(Trip.routes).selectinload(Route.points)
        )
    )
    trip = result.scalar_one_or_none()
    
    if not trip:
        return {"status": "no_trip", "message": "Ближайших рейсов нет"}
    
    return {
        "id": trip.id,
        "date": trip.date.isoformat(),
        "status": trip.status,
        "routes": [
            {
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
                    for p in route.points
                ]
            }
            for route in trip.routes
        ]
    }


@router.post("/trips/{trip_id}/confirm")
async def confirm_trip(
    trip_id: int,
    current_user: User = Depends(require_role("driver")),
    db: AsyncSession = Depends(get_db),
):
    """Подтвердить весь рейс"""
    
    result = await db.execute(
        select(Trip).where(Trip.id == trip_id, Trip.driver_id == current_user.id)
    )
    trip = result.scalar_one_or_none()
    
    if not trip:
        raise HTTPException(status_code=404, detail="Рейс не найден")
    
    if trip.status in [TripStatus.CONFIRMED, TripStatus.REJECTED]:
        raise HTTPException(status_code=400, detail="Рейс уже обработан")
    
    trip.status = TripStatus.CONFIRMED
    await db.commit()
    await db.refresh(trip)
    
    return {"status": "ok", "message": "Рейс подтверждён"}


@router.post("/trips/{trip_id}/reject")
async def reject_trip(
    trip_id: int,
    current_user: User = Depends(require_role("driver")),
    db: AsyncSession = Depends(get_db),
):
    """Отказаться от всего рейса"""
    
    result = await db.execute(
        select(Trip).where(Trip.id == trip_id, Trip.driver_id == current_user.id)
    )
    trip = result.scalar_one_or_none()
    
    if not trip:
        raise HTTPException(status_code=404, detail="Рейс не найден")
    
    if trip.status in [TripStatus.CONFIRMED, TripStatus.REJECTED]:
        raise HTTPException(status_code=400, detail="Рейс уже обработан")
    
    trip.status = TripStatus.REJECTED
    await db.commit()
    await db.refresh(trip)
    
    return {"status": "ok", "message": "Отказ от рейса принят"}


@router.post("/routes/{route_id}/reject")
async def reject_route(
    route_id: int,
    reason: str,
    current_user: User = Depends(require_role("driver")),
    db: AsyncSession = Depends(get_db),
):
    """Отказаться от маршрута (с указанием причины)"""
    
    result = await db.execute(
        select(Route)
        .join(Trip)
        .where(Route.id == route_id, Trip.driver_id == current_user.id)
    )
    route = result.scalar_one_or_none()
    
    if not route:
        raise HTTPException(status_code=404, detail="Маршрут не найден")
    
    if route.status != RouteStatus.PENDING:
        raise HTTPException(status_code=400, detail="Маршрут уже обработан")
    
    route.status = RouteStatus.REJECTED
    route.rejection_reason = reason
    
    await db.commit()
    await db.refresh(route)
    
    return {"status": "ok", "message": "Отказ от маршрута принят"}


@router.post("/points/{point_id}/reject")
async def reject_point(
    point_id: int,
    reason: str,
    current_user: User = Depends(require_role("driver")),
    db: AsyncSession = Depends(get_db),
):
    """Отказаться от торговой точки (с указанием причины)"""
    
    result = await db.execute(
        select(Point)
        .join(Route)
        .join(Trip)
        .where(Point.id == point_id, Trip.driver_id == current_user.id)
    )
    point = result.scalar_one_or_none()
    
    if not point:
        raise HTTPException(status_code=404, detail="Точка не найдена")
    
    if point.status != PointStatus.PENDING:
        raise HTTPException(status_code=400, detail="Точка уже обработана")
    
    point.status = PointStatus.REJECTED
    point.rejection_reason = reason
    
    await db.commit()
    await db.refresh(point)
    
    return {"status": "ok", "message": "Отказ от точки принят"}
