from sqlalchemy import Column, Integer, DateTime, func
from app.database import Base

class BaseModel(Base):
    """Базовая модель с общими полями для всех таблиц."""
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
