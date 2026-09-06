from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from app.models.base import BaseModel

class MaxWebhookLog(BaseModel):
    __tablename__ = "max_webhook_logs"

    event_type = Column(String(50), nullable=False, comment="Тип события")
    payload = Column(JSON, nullable=False, comment="Данные")
    processed = Column(Boolean, default=False, comment="Обработано")
    processed_at = Column(DateTime, nullable=True, comment="Время обработки")
    
    def __repr__(self):
        return f"<MaxWebhookLog #{self.id} event={self.event_type}>"
