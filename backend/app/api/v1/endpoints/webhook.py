from fastapi import APIRouter, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.trip import Trip, TripStatus
from app.models.route import Route, RouteStatus
from app.models.point import Point, PointStatus
from app.core.integrations.max_bot import MaxBotAPI

router = APIRouter()

bot = MaxBotAPI()


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

async def find_user_by_max_id(max_user_id: int) -> User | None:
    """Поиск пользователя по max_user_id."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.max_user_id == str(max_user_id))
        )
        return result.scalar_one_or_none()


async def find_trip_by_id(trip_id: int) -> Trip | None:
    """Поиск Trip со связями (routes → points)."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Trip)
            .where(Trip.id == trip_id)
            .options(selectinload(Trip.routes).selectinload(Route.points))
        )
        return result.scalar_one_or_none()


def format_trip_card(trip: Trip, trip_date: str) -> str:
    """Формирует текст карточки рейса."""
    # Общие итоги
    routes_count = len(trip.routes)
    points_count = sum(len(r.points) for r in trip.routes)

    weights = [
        p.weight for r in trip.routes for p in r.points if p.weight is not None
    ]
    total_weight = sum(weights) if weights else None
    weight_str = f"{total_weight} кг" if total_weight else "не указан"

    # Статус
    status_map = {
        TripStatus.PENDING: "⏳ Ожидает подтверждения",
        TripStatus.SENT: "📨 Отправлено",
        TripStatus.CONFIRMED: "✅ Подтверждён",
        TripStatus.PARTIAL: "⚠️ Частично подтверждён",
        TripStatus.REJECTED: "❌ Отклонён",
    }
    status_str = status_map.get(trip.status, "—")

    lines = [
        f"🚛 <b>Рейс на {trip_date}</b>",
        f"<i>{status_str}</i>",
        "",
        f"<b>Итого:</b> маршрутов {routes_count}, точек {points_count}, вес {weight_str}",
        "",
    ]

    # Каждый маршрут
    sorted_routes = sorted(trip.routes, key=lambda r: r.order_number)
    for route in sorted_routes:
        route_points_count = len(route.points)
        route_weights = [p.weight for p in route.points if p.weight is not None]
        route_weight = sum(route_weights) if route_weights else None
        route_weight_str = f"{route_weight} кг" if route_weight else "—"

        route_name = route.name or f"Маршрут #{route.order_number}"
        lines.append(
            f"<b>Маршрут {route.order_number}: {route_name}</b> "
            f"({route_points_count} точек, {route_weight_str})"
        )

        sorted_points = sorted(route.points, key=lambda p: p.order_number)
        for point in sorted_points:
            point_weight = f"{point.weight} кг" if point.weight else "—"
            lines.append(f"  📍 {point.address} ({point_weight})")

        lines.append("")

    return "\n".join(lines).strip()


async def confirm_all_points_and_routes(trip_id: int) -> Trip | None:
    """Подтверждает все Route и Point в Trip, ставит Trip = CONFIRMED."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Trip)
            .where(Trip.id == trip_id)
            .options(selectinload(Trip.routes).selectinload(Route.points))
        )
        trip = result.scalar_one_or_none()
        if not trip:
            return None

        for route in trip.routes:
            route.status = RouteStatus.CONFIRMED
            for point in route.points:
                point.status = PointStatus.CONFIRMED

        trip.status = TripStatus.CONFIRMED

        await db.commit()

        # Перечитываем, чтобы вернуть актуальные данные
        result = await db.execute(
            select(Trip)
            .where(Trip.id == trip_id)
            .options(selectinload(Trip.routes).selectinload(Route.points))
        )
        return result.scalar_one_or_none()


# ========== ВЕБХУК ==========

@router.post("/webhook")
async def max_webhook(request: Request):
    try:
        data = await request.json()
        print("📩 Webhook received:", data)

        # ========== 1. СООБЩЕНИЕ ==========
        if data.get("update_type") == "message_created":
            message = data.get("message", {})
            text = message.get("body", {}).get("text", "")
            sender = message.get("sender", {})
            max_user_id = sender.get("user_id")
            first_name = sender.get("first_name", "Пользователь")

            print(f"💬 Сообщение от {first_name} (max_id: {max_user_id}): {text}")

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

            # Меню без my_trip
            await bot.send_message(
                max_user_id,
                f"👋 Здравствуйте, {user.full_name}!\n\n"
                "Вы зарегистрированы в системе как водитель.\n"
                "Выберите действие:",
                buttons=[
                    [{"type": "callback", "text": "ℹ️ Помощь", "payload": "help"}],
                    [{"type": "callback", "text": "📞 Связаться с логистом", "payload": "contact_logist"}],
                ],
            )

        # ========== 2. CALLBACK ==========
        elif data.get("update_type") == "message_callback":
            callback = data.get("callback", {})
            payload = callback.get("payload", "")
            max_user_id = callback.get("user", {}).get("user_id")
            callback_id = callback.get("callback_id")
            message_id = callback.get("message", {}).get("body", {}).get("mid")

            print(f"🔘 Нажата кнопка: {payload}")

            user = await find_user_by_max_id(max_user_id)

            # ---------- help ----------
            if payload == "help":
                await bot.send_message(
                    max_user_id,
                    "ℹ️ <b>Помощь:</b>\n\n"
                    "• «Посмотреть предложение» — открыть карточку рейса\n"
                    "• «Подтвердить всё» — согласиться со всем рейсом\n"
                    "• «Отказаться» — отказаться от рейса\n"
                    "• «Связаться с логистом» — запросить помощь\n\n"
                    "Если у вас есть вопросы, обратитесь к логисту.",
                )

            # ---------- contact_logist ----------
            elif payload == "contact_logist":
                await bot.send_message(
                    max_user_id,
                    "📞 Запрос отправлен логисту.\n"
                    "Ожидайте, скоро с вами свяжутся.",
                )

            # ---------- view_trip:{trip_id} ----------
            elif payload.startswith("view_trip:"):
                trip_id = int(payload.split(":")[1])
                trip = await find_trip_by_id(trip_id)

                if not trip:
                    await bot.send_message(max_user_id, "❌ Рейс не найден.")
                elif not user or trip.driver_id != user.id:
                    await bot.send_message(max_user_id, "❌ Этот рейс не ваш.")
                else:
                    trip_date = trip.date.strftime("%d.%m.%Y")
                    text = format_trip_card(trip, trip_date)

                    # Если Trip уже подтверждён — без кнопок
                    if trip.status == TripStatus.CONFIRMED:
                        text += "\n\n✅ <b>Рейс подтверждён.</b>"
                        await bot.send_message(max_user_id, text)
                    else:
                        buttons = [
                            [{"type": "callback", "text": "✅ Подтвердить всё", "payload": f"confirm_all:{trip_id}"}],
                            [{"type": "callback", "text": "🚫 Отказаться", "payload": f"reject_start:{trip_id}"}],
                        ]
                        await bot.send_message(max_user_id, text, buttons=buttons)

            # ---------- confirm_all:{trip_id} ----------
            elif payload.startswith("confirm_all:"):
                trip_id = int(payload.split(":")[1])
                trip = await find_trip_by_id(trip_id)

                if not trip:
                    await bot.send_message(max_user_id, "❌ Рейс не найден.")
                elif not user or trip.driver_id != user.id:
                    await bot.send_message(max_user_id, "❌ Этот рейс не ваш.")
                elif trip.status == TripStatus.CONFIRMED:
                    await bot.send_message(max_user_id, "✅ Рейс уже подтверждён.")
                else:
                    trip = await confirm_all_points_and_routes(trip_id)
                    await bot.send_message(
                        max_user_id,
                        "✅ <b>Рейс подтверждён.</b>\n\n"
                        "Логист увидит ваш ответ. Спасибо!",
                    )

            # ---------- reject_start:{trip_id} ----------
            elif payload.startswith("reject_start:"):
                trip_id = int(payload.split(":")[1])
                # Заглушка — FSM в Шаге 6.4
                await bot.send_message(
                    max_user_id,
                    "🚫 <b>Отказ от рейса</b>\n\n"
                    "Функция в разработке. Ожидайте обновления.",
                )

            # ---------- неизвестный payload ----------
            else:
                print(f"⚠️ Неизвестный payload: {payload}")

            # Отвечаем на callback (убираем «часики»)
            if callback_id:
                await bot.answer_callback(callback_id)

        return {"status": "ok"}
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return {"status": "error", "detail": str(e)}