from datetime import date as date_type
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.trip import TripStatus
from app.models.route import RouteStatus
from app.models.point import PointStatus


class PointPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    order_number: int
    address: str
    weight: Optional[Decimal] = None
    status: PointStatus
    rejection_reason: Optional[str] = None


class RoutePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: int
    name: Optional[str] = None
    status: RouteStatus
    rejection_reason: Optional[str] = None
    points: list[PointPublic]


class TripPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    status: TripStatus
    info: Optional[str] = None
    routes: list[RoutePublic]

    routes_count: int
    points_count: int
    total_weight: Optional[Decimal] = None
    is_actionable: bool
