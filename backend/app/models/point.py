from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class PointStatus(str, enum.Enum):
    """Статусы торговой точки."""
    PENDING = "pending"          # Ожидает решения
    CONFIRMED = "confirmed"      # Подтверждена водителем
    REJECTED = "rejected"        # Отклонена водителем

class Point(BaseModel):
    """Модель торговой точки в составе маршрута."""
    __tablename__ = "points"

    # Связь с маршрутом
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False, index=True)
    
    # Данные точки
    order_number = Column(Integer, nullable=False, comment="Порядковый номер в маршруте")
    address = Column(String(255), nullable=False, comment="Адрес торговой точки")
    status = Column(Enum(PointStatus), nullable=False, default=PointStatus.PENDING, comment="Статус точки")
    rejection_reason = Column(Text, nullable=True, comment="Причина отказа (если отклонена)")
    
    # Отношения
    route = relationship("Route", back_populates="points")
