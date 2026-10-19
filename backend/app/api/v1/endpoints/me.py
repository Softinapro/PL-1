from datetime import date as date_type, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User, UserRole
from app.models.trip import Trip, TripStatus
from app.models.route import Route, RouteStatus
from app.models.point import Point, PointStatus
from app.models.rejection_reason import RejectionReason, RejectionScope
from app.api.v1.deps.auth import get_current_user
from app.api.v1.schemas.trips import TripPublic, RoutePublic, PointPublic
from app.api.v1.schemas.rejection_reasons import RejectionReasonPublic
from app.api.v1.schemas.reject import RejectRequest


router = APIRouter(prefix="/me", tags=["Profile"])


def get_active_date() -> date_type:
    """Активный день — завтра."""
    return date_type.today() + timedelta(days=1)


def _build_trip_public(trip: Trip) -> TripPublic:
    """Собирает TripPublic из ORM-объекта с вычисляемыми полями."""
    weights = [
        p.weight for r in trip.routes for p in r.points if p.weight is not None
    ]
    total_weight: Optional[Decimal] = sum(weights) if weights else None

    return TripPublic(
        id=trip.id,
        date=trip.date,
        status=trip.status,
        info=trip.info,
        routes=[RoutePublic.model_validate(r) for r in trip.routes],
        routes_count=len(trip.routes),
        points_count=sum(len(r.points) for r in trip.routes),
        total_weight=total_weight,
        is_actionable=trip.date > date_type.today(),
    )


def _recalc_route_status(route: Route) -> RouteStatus:
    """Пересчёт статуса Route по статусам его Point."""
    if not route.points:
        return route.status
    statuses = {p.status for p in route.points}
    if statuses == {PointStatus.CONFIRMED}:
        return RouteStatus.CONFIRMED
    if statuses == {PointStatus.REJECTED}:
        return RouteStatus.REJECTED
    if PointStatus.PENDING in statuses:
        return RouteStatus.PENDING
    return RouteStatus.PARTIAL


def _recalc_trip_status(trip: Trip) -> TripStatus:
    """Пересчёт статуса Trip по статусам его Route."""
    if not trip.routes:
        return TripStatus.PENDING
    statuses = {r.status for r in trip.routes}
    if statuses == {RouteStatus.CONFIRMED}:
        return TripStatus.CONFIRMED
    if statuses == {RouteStatus.REJECTED}:
        return TripStatus.REJECTED
    if RouteStatus.PENDING in statuses:
        return TripStatus.PENDING
    return TripStatus.PARTIAL


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


@router.get("/trips", response_model=list[TripPublic])
async def get_my_trips(
    date: Optional[date_type] = Query(
        None,
        description="Дата рейса (YYYY-MM-DD). По умолчанию — завтра.",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Рейсы текущего водителя на указанную дату.

    - Доступно только водителям (DRIVER).
    - По умолчанию — активный день (завтра).
    - Возвращает список (0 или 1 элемент).
    """
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для водителей",
        )

    target_date = date or get_active_date()

    result = await db.execute(
        select(Trip)
        .where(Trip.driver_id == current_user.id, Trip.date == target_date)
        .options(selectinload(Trip.routes).selectinload(Route.points))
    )
    trips = result.scalars().all()

    return [_build_trip_public(t) for t in trips]


@router.get("/rejection-reasons", response_model=list[RejectionReasonPublic])
async def get_rejection_reasons(
    scope: RejectionScope = Query(
        ...,
        description="Уровень отказа: trip / route / point",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Справочник активных причин отказа для указанного уровня.

    - Доступно только водителям (DRIVER).
    - `scope` обязателен: trip / route / point.
    - Возвращает только `is_active=True`, отсортированные по id.
    """
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для водителей",
        )

    result = await db.execute(
        select(RejectionReason)
        .where(
            RejectionReason.scope == scope,
            RejectionReason.is_active == True,
        )
        .order_by(RejectionReason.id)
    )
    reasons = result.scalars().all()

    return list(reasons)


@router.post("/trips/{trip_id}/confirm", response_model=TripPublic)
async def confirm_trip(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Подтвердить весь рейс.

    - Только DRIVER.
    - Только на будущее (date > today).
    - Если уже CONFIRMED — idempotent (200, без изменений).
    - Из любого другого статуса (PENDING / SENT / PARTIAL / REJECTED)
      подтверждает всё и сбрасывает отказы.
      Логику «начудил ли водитель» контролирует 1С.
    """
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для водителей",
        )

    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id, Trip.driver_id == current_user.id)
        .options(selectinload(Trip.routes).selectinload(Route.points))
    )
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Рейс не найден",
        )

    if trip.date <= date_type.today():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Рейс неактуален. Действия недоступны.",
        )

    # Idempotent: уже подтверждён — возвращаем как есть
    if trip.status == TripStatus.CONFIRMED:
        return _build_trip_public(trip)

    # Подтверждаем всё: сбрасываем отказы
    for route in trip.routes:
        route.status = RouteStatus.CONFIRMED
        route.rejection_reason = None
        for point in route.points:
            point.status = PointStatus.CONFIRMED
            point.rejection_reason = None
    trip.status = TripStatus.CONFIRMED

    await db.commit()

    # Перечитываем, чтобы получить актуальное состояние (expire_on_commit)
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id)
        .options(selectinload(Trip.routes).selectinload(Route.points))
    )
    trip = result.scalar_one_or_none()

    return _build_trip_public(trip)


@router.post("/trips/{trip_id}/reject", response_model=TripPublic)
async def reject_trip(
    trip_id: int,
    request: RejectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Отказ от рейса (полностью или частично).

    Формат запроса:
      - trip_reason_id: отказ от всего рейса (нельзя комбинировать с routes/points)
      - routes: список {route_id, reason_id}
      - points: список {point_id, reason_id}

    Правила:
      - Только DRIVER.
      - Только на будущее (date > today).
      - Если уже REJECTED — 409.
      - Если CONFIRMED — разрешаем отказ (водитель передумал).
      - trip_reason_id + routes/points — 400 (нельзя комбинировать).
      - Пустой запрос — 400.
    """
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для водителей",
        )

    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id, Trip.driver_id == current_user.id)
        .options(selectinload(Trip.routes).selectinload(Route.points))
    )
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Рейс не найден",
        )

    if trip.date <= date_type.today():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Рейс неактуален. Действия недоступны.",
        )

    if trip.status == TripStatus.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Рейс уже отклонён.",
        )

    # Валидация: нельзя комбинировать
    has_trip = request.trip_reason_id is not None
    has_routes = len(request.routes) > 0
    has_points = len(request.points) > 0

    if has_trip and (has_routes or has_points):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя комбинировать отказ от всего рейса с частичным",
        )

    if not has_trip and not has_routes and not has_points:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет решений об отказе",
        )

    # Проверка reason_id по scope
    async def _get_reason_text(reason_id: int, expected_scope: RejectionScope) -> str:
        res = await db.execute(
            select(RejectionReason).where(
                RejectionReason.id == reason_id,
                RejectionReason.is_active == True,
            )
        )
        reason = res.scalar_one_or_none()
        if not reason or reason.scope != expected_scope:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Причина {reason_id} не найдена или неверный scope",
            )
        return reason.text

    # ========== СЦЕНАРИЙ A: отказ от всего рейса ==========
    if has_trip:
        reason_text = None
        if request.trip_reason_id is not None:
            reason_text = await _get_reason_text(
                request.trip_reason_id, RejectionScope.TRIP
            )

        for route in trip.routes:
            route.status = RouteStatus.REJECTED
            route.rejection_reason = reason_text
            for point in route.points:
                point.status = PointStatus.REJECTED
                point.rejection_reason = reason_text
        trip.status = TripStatus.REJECTED

    # ========== СЦЕНАРИЙ B: частичный отказ ==========
    else:
        trip_route_ids = {r.id for r in trip.routes}
        trip_point_ids = {p.id for r in trip.routes for p in r.points}

        for item in request.routes:
            if item.route_id not in trip_route_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Маршрут {item.route_id} не принадлежит рейсу",
                )

        for item in request.points:
            if item.point_id not in trip_point_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Точка {item.point_id} не принадлежит рейсу",
                )

        routes_reasons: dict[int, Optional[str]] = {}
        for item in request.routes:
            text = None
            if item.reason_id is not None:
                text = await _get_reason_text(item.reason_id, RejectionScope.ROUTE)
            routes_reasons[item.route_id] = text

        points_reasons: dict[int, Optional[str]] = {}
        for item in request.points:
            text = None
            if item.reason_id is not None:
                text = await _get_reason_text(item.reason_id, RejectionScope.POINT)
            points_reasons[item.point_id] = text

        for route in trip.routes:
            if route.id in routes_reasons:
                reason_text = routes_reasons[route.id]
                route.status = RouteStatus.REJECTED
                route.rejection_reason = reason_text
                for point in route.points:
                    point.status = PointStatus.REJECTED
                    point.rejection_reason = reason_text
            else:
                for point in route.points:
                    if point.id in points_reasons:
                        point.status = PointStatus.REJECTED
                        point.rejection_reason = points_reasons[point.id]
                    else:
                        point.status = PointStatus.CONFIRMED
                        point.rejection_reason = None

                route.status = _recalc_route_status(route)
                route.rejection_reason = None

        trip.status = _recalc_trip_status(trip)

    await db.commit()

    # Перечитываем
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id)
        .options(selectinload(Trip.routes).selectinload(Route.points))
    )
    trip = result.scalar_one_or_none()

    return _build_trip_public(trip)