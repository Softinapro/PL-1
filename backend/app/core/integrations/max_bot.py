import warnings
import httpx
from decimal import Decimal
from typing import Optional
from app.config import settings

warnings.filterwarnings("ignore", message="Unverified HTTPS request")


class MaxBotAPI:
    def __init__(self):
        self.token = settings.MAX_BOT_TOKEN
        self.base_url = "https://platform-api2.max.ru"
        self.headers = {
            "Authorization": self.token,
            "Content-Type": "application/json",
        }

    # ========== БАЗОВЫЕ МЕТОДЫ ==========

    async def send_message(
        self,
        user_id: str,
        text: str,
        buttons: Optional[list] = None,
    ) -> dict:
        """Отправить сообщение пользователю MAX."""
        body = {
            "text": text,
            "format": "html",
        }

        if buttons:
            body["attachments"] = [
                {
                    "type": "inline_keyboard",
                    "payload": {"buttons": buttons},
                }
            ]

        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                params={"user_id": user_id},
                json=body,
            )
            return response.json()

    async def answer_callback(self, callback_id: str) -> dict:
        """Ответить на нажатие кнопки — убрать «часики»."""
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.post(
                f"{self.base_url}/answers",
                headers=self.headers,
                params={"callback_id": callback_id},
            )
            return response.json()

    async def edit_message(
        self,
        message_id: str,
        text: str,
        buttons: Optional[list] = None,
    ) -> dict:
        """Отредактировать сообщение."""
        body = {
            "text": text,
            "format": "html",
        }

        if buttons:
            body["attachments"] = [
                {
                    "type": "inline_keyboard",
                    "payload": {"buttons": buttons},
                }
            ]

        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.put(
                f"{self.base_url}/messages",
                headers=self.headers,
                params={"message_id": message_id},
                json=body,
            )
            return response.json()

    # ========== БИЗНЕС-УВЕДОМЛЕНИЯ ==========

    async def send_notification(
        self,
        user_id: str,
        trip_id: int,
        trip_date: str,
        routes_count: int,
        points_count: int,
        total_weight: Optional[Decimal] = None,
    ) -> dict:
        """Уведомление о новом рейсе с кнопкой «Посмотреть предложение»."""
        bot_name = settings.MAX_BOT_NAME
        deep_link = f"https://max.ru/{bot_name}?startapp=trip_{trip_id}"

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
            f'👉 <a href="{deep_link}">Открыть в приложении</a>'
        )

        buttons = [
            [{"type": "callback", "text": "📋 Посмотреть предложение", "payload": f"view_trip:{trip_id}"}],
        ]

        return await self.send_message(user_id, text, buttons=buttons)

    async def send_revoked_notification(
        self,
        user_id: str,
        trip_date: str,
    ) -> dict:
        """Уведомление об отзыве рейса."""
        text = (
            f"🚫 <b>Рейс на {trip_date} отозван логистом.</b>\n"
            f"\n"
            f"Если есть вопросы — свяжитесь с логистом."
        )

        return await self.send_message(user_id, text)