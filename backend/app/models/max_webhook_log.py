from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from app.models.base import BaseModel

class MaxWebhookLog(BaseModel):
    """Логи всех входящих webhook от MAX. Для отладки и аудита."""
    __tablename__ = "max_webhook_logs"

    event_type = Column(String(50), nullable=False, comment="Тип события от MAX")
    payload = Column(JSON, nullable=False, comment="Полный payload от MAX")
    processed = Column(Boolean, default=False, comment="Обработано ли событие")
    processed_at = Column(DateTime, nullable=True, comment="Время обработки")
