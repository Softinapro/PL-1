from sqlalchemy import Column, String, Boolean, Enum
from app.models.base import BaseModel
import enum

class UserRole(str, enum.Enum):
    """Роли пользователей в системе."""
    ADMIN = "admin"
    LOGIST = "logist"
    DRIVER = "driver"

class User(BaseModel):
    """Модель пользователя. Может быть администратором, логистом или водителем."""
    __tablename__ = "users"

    # Основная информация
    phone = Column(String(20), unique=True, nullable=False, index=True, comment="Номер телефона")
    full_name = Column(String(100), nullable=False, comment="Полное имя")
    
    # Роль и статус
    role = Column(Enum(UserRole), nullable=False, default=UserRole.DRIVER, comment="Роль в системе")
    is_active = Column(Boolean, default=True, comment="Активен (не заблокирован)")
    is_archived = Column(Boolean, default=False, comment="В архиве (скрыт из списков)")
