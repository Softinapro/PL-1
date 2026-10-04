from fastapi import APIRouter, Request
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.user import User
from app.core.integrations.max_bot import MaxBotAPI

router = APIRouter()

bot = MaxBotAPI()


# Функция поиска пользователя по max_user_id
async def find_user_by_max_id(max_user_id: int) -> User | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.max_user_id == str(max_user_id))
        )
        return result.scalar_one_or_none()


# Обработчик команды /start (или первого запуска)
@router.post("/webhook")
async def max_webhook(request: Request):
    try:
        data = await request.json()
        print("📩 Webhook received:", data)

        # 1. Проверяем, что это событие о сообщении
        if data.get("update_type") == "message_created":
            message = data.get("message", {})
            text = message.get("body", {}).get("text", "")
            sender = message.get("sender", {})
            max_user_id = sender.get("user_id")
            first_name = sender.get("first_name", "Пользователь")

            print(f"💬 Сообщение от {first_name} (max_id: {max_user_id}): {text}")

            # 2. Ищем пользователя в БД по max_user_id
            user = await find_user_by_max_id(max_user_id)

            if not user:
                await bot.send_message(
                    max_user_id,
                    f"👋 Здравствуйте, {first_name}!\n\n"
                    "❌ Вы не зарегистрированы в системе.\n\n"
                    "Обратитесь к логисту, чтобы он добавил вас.\n"
                    "После регистрации вы сможете:\n"
                    "• Получать рейсы\n"
                    "• Подтверждать маршруты\n"
                    "• Получать уведомления",
                )
                return {"status": "ok"}

            # 3. Пользователь найден → приветствие с меню
            await bot.send_message(
                max_user_id,
                f"👋 Здравствуйте, {user.full_name}!\n\n"
                "Вы зарегистрированы в системе как водитель.\n"
                "Выберите действие:",
                buttons=[
                    [{"type": "callback", "text": "📋 Мой рейс", "payload": "my_trip"}],
                    [{"type": "callback", "text": "ℹ️ Помощь", "payload": "help"}],
                    [{"type": "callback", "text": "📞 Связаться с логистом", "payload": "contact_logist"}],
                ],
            )

        # 4. Обработка нажатия на кнопки (callback)
        elif data.get("update_type") == "message_callback":
            callback = data.get("callback", {})
            payload = callback.get("payload", "")
            max_user_id = callback.get("user", {}).get("user_id")
            callback_id = callback.get("callback_id")

            print(f"🔘 Нажата кнопка: {payload}")

            user = await find_user_by_max_id(max_user_id)

            if payload == "my_trip":
                if user:
                    await bot.send_message(
                        max_user_id,
                        "🚛 Ваш рейс на сегодня:\n\n"
                        "Маршрут 1: ул. Ленина → ул. Пушкина\n"
                        "  📍 Магазин Продукты\n"
                        "  📍 Аптека №3\n"
                        "Маршрут 2: ул. Гагарина → ул. Мира\n"
                        "  📍 ТЦ Атлант\n\n"
                        "Статус: ⏳ Ожидает подтверждения",
                    )
                else:
                    await bot.send_message(max_user_id, "❌ Пользователь не найден. Обратитесь к логисту.")

            elif payload == "help":
                await bot.send_message(
                    max_user_id,
                    "ℹ️ Помощь:\n\n"
                    "• /start — показать меню\n"
                    "• 'Мой рейс' — показать сегодняшний рейс\n"
                    "• 'Связаться с логистом' — запросить помощь\n\n"
                    "Если у вас есть вопросы, обратитесь к логисту.",
                )

            elif payload == "contact_logist":
                await bot.send_message(
                    max_user_id,
                    "📞 Запрос отправлен логисту.\n"
                    "Ожидайте, скоро с вами свяжутся.",
                )

            # Отвечаем на callback (убираем «часики»)
            if callback_id:
                await bot.answer_callback(callback_id)

        return {"status": "ok"}
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return {"status": "error", "detail": str(e)}