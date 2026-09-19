import httpx
from decimal import Decimal
from typing import Optional
from app.config import settings


class MaxBotAPI:
    def __init__(self):
        self.token = settings.MAX_BOT_TOKEN
        self.base_url = "https://platform-api2.max.ru/bot"

    async def send_message(self, user_id: str, text: str) -> dict:
        """Отправить сообщение пользователю MAX"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}{self.token}/sendMessage",
                json={
                    "chat_id": user_id,
                    "text": text,
                    "parse_mode": "HTML"
                }
            )
            return response.json()

    async def send_notification(
        self,
        user_id: str,
        trip_id: int,
        trip_date: str,
        routes_count: int,
        points_count: int,
        total_weight: Optional[Decimal] = None,
    ) -> dict:
        """Отправить уведомление о новом рейсе (Вариант B — с деталями)"""
        bot_name = settings.MAX_BOT_NAME
        deep_link = f"https://max.ru/{bot_name}?startapp=trip_{trip_id}"

        # Формируем строку с весом
        if total_weight is not None and total_weight > 0:
            weight_str = f"Общий вес: {total_weight} кг"
        else:
            weight_str = "Общий вес: не указан"

        text = (
            f"🚛 <b>Вам назначен рейс на {trip_date}.</b>\n"
            f"\n"
            f"Маршрутов: {routes_count}\n"
            f"Точек: {points_count}\n"
            f"{weight_str}\n"
            f"\n"
            f'👉 <a href="{deep_link}">Открыть</a>'
        )

        return await self.send_message(user_id, text)