import httpx
from app.config import settings

class MaxBotAPI:
    def __init__(self):
        self.token = settings.MAX_BOT_TOKEN        
        self.base_url = "https://platform-api2.max.ru/bot"
    
    async def send_message(self, user_id: str, text: str) -> dict:
        """Отправить сообщение пользователю MAX"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{self.token}/sendMessage",
                json={
                    "chat_id": user_id,
                    "text": text,
                    "parse_mode": "HTML"
                }
            )
            return response.json()
    
    async def send_notification(self, user_id: str, trip_id: int, trip_date: str):
        """Отправить уведомление о новом рейсе"""
        bot_name = settings.MAX_BOT_NAME
        deep_link = f"https://max.ru/{bot_name}?startapp=trip_{trip_id}"
        
        text = f"""
        🚛 <b>Новый рейс!</b>
        
        Дата: {trip_date}
        
        Нажмите на кнопку ниже, чтобы открыть приложение и подтвердить рейс:
        
        👉 <a href="{deep_link}">Открыть рейс</a>
        """
        
        return await self.send_message(user_id, text)
