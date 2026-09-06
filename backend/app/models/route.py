from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class RouteStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"

class Route(BaseModel):
    __tablename__ = "routes"

    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False, index=True, comment="Рейс")
    order_number = Column(Integer, nullable=False, comment="Порядковый номер")
    status = Column(Enum(RouteStatus), nullable=False, default=RouteStatus.PENDING, comment="Статус")
    rejection_reason = Column(Text, nullable=True, comment="Причина отказа")
    address_start = Column(String(255), nullable=False, comment="Адрес начала")
    address_end = Column(String(255), nullable=False, comment="Адрес конца")
    
    trip = relationship("Trip", back_populates="routes")
    points = relationship("Point", back_populates="route", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Route #{self.id} trip={self.trip_id} order={self.order_number}>"
