from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class DriverProfile(BaseModel):
    __tablename__ = "driver_profiles"

    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True, comment="ID пользователя")
    max_user_id = Column(String(100), unique=True, nullable=True, comment="ID в MAX")
    is_verified = Column(Boolean, default=False, comment="Подтверждён в MAX")
    
    user = relationship("User", backref="driver_profile")
    
    def __repr__(self):
        return f"<DriverProfile user_id={self.user_id}>"
