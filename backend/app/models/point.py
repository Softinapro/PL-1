from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Text, Numeric, Date, UniqueConstraint
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
    code = Column(String(10), nullable=False, index=True, comment="Код точки из 1С")
    date = Column(Date, nullable=False, index=True, comment="Дата отгрузки")
    order_number = Column(Integer, nullable=False, comment="Порядковый номер")
    address = Column(String(255), nullable=False, comment="Адрес точки")
    weight = Column(Numeric(10, 3), nullable=True, comment="Вес товара, кг")
    status = Column(Enum(PointStatus), nullable=False, default=PointStatus.PENDING, comment="Статус")
    rejection_reason = Column(Text, nullable=True, comment="Причина отказа")

    __table_args__ = (
        UniqueConstraint('code', 'date', name='uq_point_code_date'),
    )

    route = relationship("Route", back_populates="points")
    
    def __repr__(self):
        return f"<Point #{self.id} code={self.code} date={self.date} address={self.address[:30]}>"
