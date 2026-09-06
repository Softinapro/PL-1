from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class DriverProfile(BaseModel):
    """Расширение для водителей. Связывает пользователя с MAX."""
    __tablename__ = "driver_profiles"

    # Связь с пользователем
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    # Интеграция с MAX
    max_user_id = Column(String(100), unique=True, nullable=True, comment="ID пользователя в MAX")
    is_verified = Column(Boolean, default=False, comment="Подтверждён ли аккаунт MAX")
    
    # Отношения
    user = relationship("User", backref="driver_profile")
