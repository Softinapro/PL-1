from sqlalchemy import Column, String, Boolean, Enum
from app.models.base import BaseModel
import enum

class UserRole(str, enum.Enum):
    """Роли пользователей в системе."""
    ADMIN = "admin"
    LOGIST = "logist"
    DRIVER = "driver"

class User(BaseModel):
    __tablename__ = "users"

    phone = Column(String(20), unique=True, nullable=False, index=True, comment="Номер телефона")
    full_name = Column(String(100), nullable=False, comment="Полное имя")
    role = Column(Enum(UserRole), nullable=False, default=UserRole.DRIVER, comment="Роль")
    is_active = Column(Boolean, default=True, comment="Активен")
    is_archived = Column(Boolean, default=False, comment="В архиве")
    max_user_id = Column(String(100), unique=True, nullable=True, comment="ID пользователя в MAX")
    
    def __repr__(self):
        return f"<User {self.full_name}>"
