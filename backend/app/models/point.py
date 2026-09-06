from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class PointStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"

class Point(BaseModel):
    __tablename__ = "points"

    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False, index=True, comment="Маршрут")
    order_number = Column(Integer, nullable=False, comment="Порядковый номер")
    address = Column(String(255), nullable=False, comment="Адрес точки")
    status = Column(Enum(PointStatus), nullable=False, default=PointStatus.PENDING, comment="Статус")
    rejection_reason = Column(Text, nullable=True, comment="Причина отказа")
    
    route = relationship("Route", back_populates="points")
    
    def __repr__(self):
        return f"<Point #{self.id} route={self.route_id} address={self.address[:30]}>"
