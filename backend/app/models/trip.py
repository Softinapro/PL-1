from sqlalchemy import Column, Integer, String, Date, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class TripStatus(str, enum.Enum):
    """Статусы рейса."""
    PENDING = "pending"          # Создан, ожидает отправки
    SENT = "sent"                # Отправлено уведомление водителю
    CONFIRMED = "confirmed"      # Подтверждён полностью
    PARTIAL = "partial"          # Частично подтверждён
    REJECTED = "rejected"        # Полностью отклонён

class Trip(BaseModel):
    """Модель рейса. Один рейс на одного водителя в день."""
    __tablename__ = "trips"

    # Связи с пользователями
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    logist_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Основные данные
    date = Column(Date, nullable=False, index=True, comment="Дата рейса")
    status = Column(Enum(TripStatus), nullable=False, default=TripStatus.PENDING, comment="Статус рейса")
    
    # Отправка уведомления
    sent_at = Column(DateTime, nullable=True, comment="Когда отправлено уведомление в MAX")
    
    # Отношения
    driver = relationship("User", foreign_keys=[driver_id], backref="trips_as_driver")
    logist = relationship("User", foreign_keys=[logist_id], backref="trips_as_logist")
    routes = relationship("Route", back_populates="trip", cascade="all, delete-orphan")
