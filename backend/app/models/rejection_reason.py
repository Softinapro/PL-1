from sqlalchemy import Column, String, Enum, Boolean
from app.models.base import BaseModel
import enum


class RejectionScope(str, enum.Enum):
    TRIP = "trip"
    ROUTE = "route"
    POINT = "point"


class RejectionReason(BaseModel):
    __tablename__ = "rejection_reasons"

    scope = Column(
        Enum(RejectionScope),
        nullable=False,
        index=True,
        comment="Уровень отказа: рейс / маршрут / точка",
    )
    text = Column(
        String(255),
        nullable=False,
        comment="Текст причины (видит водитель и логист)",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Мягкое удаление: False — причина скрыта из выбора",
    )

    def __repr__(self):
        return f"<RejectionReason #{self.id} scope={self.scope} text={self.text[:30]}>"