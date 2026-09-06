from sqlalchemy import Column, Integer, String, Date, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class TripStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    CONFIRMED = "confirmed"
    PARTIAL = "partial"
    REJECTED = "rejected"

class Trip(BaseModel):
    __tablename__ = "trips"

    driver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="Водитель")
    logist_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="Логист")
    date = Column(Date, nullable=False, index=True, comment="Дата рейса")
    status = Column(Enum(TripStatus), nullable=False, default=TripStatus.PENDING, comment="Статус")
    sent_at = Column(DateTime, nullable=True, comment="Отправлено в MAX")
    
    driver = relationship("User", foreign_keys=[driver_id], backref="trips_as_driver")
    logist = relationship("User", foreign_keys=[logist_id], backref="trips_as_logist")
    routes = relationship("Route", back_populates="trip", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Trip #{self.id} driver={self.driver_id} date={self.date}>"
