from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class RouteStatus(str, enum.Enum):
    """Статусы маршрута."""
    PENDING = "pending"          # Ожидает решения
    CONFIRMED = "confirmed"      # Подтверждён водителем
    REJECTED = "rejected"        # Отклонён водителем

class Route(BaseModel):
    """Модель маршрута в составе рейса."""
    __tablename__ = "routes"

    # Связь с рейсом
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False, index=True)
    
    # Данные маршрута
    order_number = Column(Integer, nullable=False, comment="Порядковый номер в рейсе")
    status = Column(Enum(RouteStatus), nullable=False, default=RouteStatus.PENDING, comment="Статус маршрута")
    rejection_reason = Column(Text, nullable=True, comment="Причина отказа (если отклонён)")
    
    # Адреса
    address_start = Column(String(255), nullable=False, comment="Адрес начала маршрута")
    address_end = Column(String(255), nullable=False, comment="Адрес конца маршрута")
    
    # Отношения
    trip = relationship("Trip", back_populates="routes")
    points = relationship("Point", back_populates="route", cascade="all, delete-orphan")
