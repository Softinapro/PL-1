from fastapi import APIRouter, Request
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User
from app.config import settings

router = APIRouter()

# Функция отправки сообщения с кнопками
async def send_message_with_buttons(chat_id: int, text: str, buttons: list):
    async with httpx.AsyncClient() as client:
        url = f"https://platform-api2.max.ru/bot{settings.MAX_BOT_TOKEN}/sendMessage"
        await client.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "reply_markup": {"inline_keyboard": buttons}
        })

# Функция отправки обычного сообщения
async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient() as client:
        url = f"https://platform-api2.max.ru/bot{settings.MAX_BOT_TOKEN}/sendMessage"
        await client.post(url, json={"chat_id": chat_id, "text": text})

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
        if data.get('update_type') == 'message_created':
            message = data.get('message', {})
            text = message.get('body', {}).get('text', '')
            chat_id = message.get('recipient', {}).get('chat_id')
            sender = message.get('sender', {})
            max_user_id = sender.get('user_id')
            first_name = sender.get('first_name', 'Пользователь')

            print(f"💬 Сообщение от {first_name} (max_id: {max_user_id}): {text}")

            # 2. Ищем пользователя в БД по max_user_id
            user = await find_user_by_max_id(max_user_id)

            if not user:
                # Пользователь не найден
                await send_message(
                    chat_id,
                    f"👋 Здравствуйте, {first_name}!\n\n"
                    "❌ Вы не зарегистрированы в системе.\n\n"
                    "Обратитесь к логисту, чтобы он добавил вас.\n"
                    "После регистрации вы сможете:\n"
                    "• Получать рейсы\n"
                    "• Подтверждать маршруты\n"
                    "• Получать уведомления"
                )
                return {"status": "ok"}

            # 3. Пользователь найден → приветствие с меню
            await send_message_with_buttons(
                chat_id,
                f"👋 Здравствуйте, {user.full_name}!\n\n"
                "Вы зарегистрированы в системе как водитель.\n"
                "Выберите действие:",
                [
                    [{"text": "📋 Мой рейс", "callback_data": "my_trip"}],
                    [{"text": "ℹ️ Помощь", "callback_data": "help"}],
                    [{"text": "📞 Связаться с логистом", "callback_data": "contact_logist"}]
                ]
            )

        # 4. Обработка нажатия на кнопки (callback)
        elif data.get('update_type') == 'callback_query':
            callback = data.get('callback_query', {})
            data_callback = callback.get('data', '')
            chat_id = callback.get('chat_id')
            max_user_id = callback.get('user_id')

            print(f"🔘 Нажата кнопка: {data_callback}")

            # Находим пользователя
            user = await find_user_by_max_id(max_user_id)

            if data_callback == 'my_trip':
                if user:
                    await send_message(
                        chat_id,
                        f"🚛 Ваш рейс на сегодня:\n\n"
                        "Маршрут 1: ул. Ленина → ул. Пушкина\n"
                        "  📍 Магазин Продукты\n"
                        "  📍 Аптека №3\n"
                        "Маршрут 2: ул. Гагарина → ул. Мира\n"
                        "  📍 ТЦ Атлант\n\n"
                        "Статус: ⏳ Ожидает подтверждения"
                    )
                else:
                    await send_message(chat_id, "❌ Пользователь не найден. Обратитесь к логисту.")

            elif data_callback == 'help':
                await send_message(
                    chat_id,
                    "ℹ️ Помощь:\n\n"
                    "• /start — показать меню\n"
                    "• 'Мой рейс' — показать сегодняшний рейс\n"
                    "• 'Связаться с логистом' — запросить помощь\n\n"
                    "Если у вас есть вопросы, обратитесь к логисту."
                )

            elif data_callback == 'contact_logist':
                await send_message(
                    chat_id,
                    "📞 Запрос отправлен логисту.\n"
                    "Ожидайте, скоро с вами свяжутся."
                )

            # Отвечаем на callback (убираем "часики")
            async with httpx.AsyncClient() as client:
                url = f"https://platform-api2.max.ru/bot{settings.MAX_BOT_TOKEN}/answerCallbackQuery"
                await client.post(url, json={"callback_query_id": callback.get('id')})

        return {"status": "ok"}
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return {"status": "error", "detail": str(e)}
