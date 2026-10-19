from typing import Optional
from pydantic import BaseModel, Field


class RouteRejectItem(BaseModel):
    route_id: int
    reason_id: Optional[int] = None


class PointRejectItem(BaseModel):
    point_id: int
    reason_id: Optional[int] = None


class RejectRequest(BaseModel):
    trip_reason_id: Optional[int] = Field(
        None,
        description="Причина отказа от всего рейса. Нельзя комбинировать с routes/points.",
    )
    routes: list[RouteRejectItem] = Field(default_factory=list)
    points: list[PointRejectItem] = Field(default_factory=list)
