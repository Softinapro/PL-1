from fastapi import APIRouter, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.trip import Trip, TripStatus
from app.models.route import Route, RouteStatus
from app.models.point import Point, PointStatus
from app.models.rejection_reason import RejectionReason, RejectionScope
from app.core.integrations.max_bot import MaxBotAPI
from app.core.redis_client import get_draft, save_draft, clear_draft

router = APIRouter()

bot = MaxBotAPI()


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

async def find_user_by_max_id(max_user_id: int) -> User | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.max_user_id == str(max_user_id))
        )
        return result.scalar_one_or_none()


async def find_trip_by_id(trip_id: int) -> Trip | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Trip)
            .where(Trip.id == trip_id)
            .options(selectinload(Trip.routes).selectinload(Route.points))
        )
        return result.scalar_one_or_none()


async def find_reasons_by_scope(scope: RejectionScope) -> list[RejectionReason]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(RejectionReason)
            .where(
                RejectionReason.scope == scope,
                RejectionReason.is_active == True,
            )
            .order_by(RejectionReason.id)
        )
        return list(result.scalars().all())


def format_trip_card(trip: Trip, trip_date: str) -> str:
    routes_count = len(trip.routes)
    points_count = sum(len(r.points) for r in trip.routes)

    weights = [
        p.weight for r in trip.routes for p in r.points if p.weight is not None
    ]
    total_weight = sum(weights) if weights else None
    weight_str = f"{total_weight} кг" if total_weight else "не указан"

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

        result = await db.execute(
            select(Trip)
            .where(Trip.id == trip_id)
            .options(selectinload(Trip.routes).selectinload(Route.points))
        )
        return result.scalar_one_or_none()


async def reject_whole_trip(trip_id: int, reason_text: str | None) -> Trip | None:
    """Отказ от всего Trip: все Route и Point → REJECTED, Trip → REJECTED."""
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
            route.status = RouteStatus.REJECTED
            route.rejection_reason = reason_text
            for point in route.points:
                point.status = PointStatus.REJECTED
                point.rejection_reason = reason_text

        trip.status = TripStatus.REJECTED

        await db.commit()

        result = await db.execute(
            select(Trip)
            .where(Trip.id == trip_id)
            .options(selectinload(Trip.routes).selectinload(Route.points))
        )
        return result.scalar_one_or_none()


def recalc_trip_status(trip: Trip) -> TripStatus:
    """Пересчёт статуса Trip по статусам его Route."""
    if not trip.routes:
        return TripStatus.PENDING

    statuses = {r.status for r in trip.routes}

    if statuses == {RouteStatus.CONFIRMED}:
        return TripStatus.CONFIRMED
    if statuses == {RouteStatus.REJECTED}:
        return TripStatus.REJECTED
    if RouteStatus.PENDING in statuses:
        return TripStatus.PENDING
    return TripStatus.PARTIAL


def format_routes_choices(trip: Trip, draft: dict) -> str:
    """Текст экрана выбора маршрутов."""
    trip_date = trip.date.strftime("%d.%m.%Y")
    selected = draft.get("selected", {}) if draft else {}

    lines = [
        f"✏️ <b>Частичный отказ</b>",
        f"Рейс на {trip_date}",
        "",
        "Выберите маршруты, от которых отказываетесь:",
        "",
    ]

    sorted_routes = sorted(trip.routes, key=lambda r: r.order_number)
    for route in sorted_routes:
        route_name = route.name or f"Маршрут #{route.order_number}"
        points_count = len(route.points)

        if route.status == RouteStatus.CONFIRMED:
            lines.append(f"✅ {route_name} ({points_count} точек) — подтверждён")
        elif route.status == RouteStatus.REJECTED:
            lines.append(f"❌ {route_name} ({points_count} точек) — отклонён")
        elif str(route.id) in selected:
            reason = selected[str(route.id)].get("reason_text") or "без причины"
            lines.append(f"❌ {route_name} ({points_count} точек) — {reason}")
        else:
            lines.append(f"🚫 {route_name} ({points_count} точек)")

    return "\n".join(lines)


def build_routes_buttons(trip: Trip, draft: dict) -> list:
    """Кнопки экрана выбора маршрутов."""
    selected = draft.get("selected", {}) if draft else {}
    buttons = []

    sorted_routes = sorted(trip.routes, key=lambda r: r.order_number)
    for route in sorted_routes:
        route_name = route.name or f"Маршрут #{route.order_number}"

        # Подтверждённые — не показываем в выборе (они уже ок)
        if route.status == RouteStatus.CONFIRMED:
            continue

        # Отклонённые в БД — не кликабельны (показываем текстом в карточке)
        if route.status == RouteStatus.REJECTED:
            continue

        if str(route.id) in selected:
            buttons.append([{
                "type": "callback",
                "text": f"❌ {route_name} — снять",
                "payload": f"reject_route_unpick:{trip.id}:{route.id}",
            }])
        else:
            buttons.append([{
                "type": "callback",
                "text": f"🚫 {route_name}",
                "payload": f"reject_route_pick:{trip.id}:{route.id}",
            }])

    buttons.append([{
        "type": "callback",
        "text": "✅ Применить",
        "payload": f"reject_partial_apply:{trip.id}",
    }])
    buttons.append([{
        "type": "callback",
        "text": "← Назад",
        "payload": f"reject_start:{trip.id}",
    }])

    return buttons


async def apply_partial_reject(trip_id: int, draft: dict) -> Trip | None:
    """Применить частичный отказ: выбранные Route → REJECTED, остальные → CONFIRMED."""
    selected = draft.get("selected", {}) if draft else {}

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
            if str(route.id) in selected:
                reason_text = selected[str(route.id)].get("reason_text")
                route.status = RouteStatus.REJECTED
                route.rejection_reason = reason_text
                for point in route.points:
                    point.status = PointStatus.REJECTED
                    point.rejection_reason = reason_text
            else:
                route.status = RouteStatus.CONFIRMED
                route.rejection_reason = None
                for point in route.points:
                    point.status = PointStatus.CONFIRMED
                    point.rejection_reason = None

        trip.status = recalc_trip_status(trip)

        await db.commit()

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
                    "Обратитесь к логисту, чтобы он добавил вас.",
                )
                return {"status": "ok"}

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
                    "• «Связаться с логистом» — запросить помощь",
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

                    if trip.status == TripStatus.CONFIRMED:
                        text += "\n\n✅ <b>Рейс подтверждён.</b>"
                        await bot.send_message(max_user_id, text)
                    elif trip.status == TripStatus.REJECTED:
                        text += "\n\n❌ <b>Рейс отклонён.</b>"
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
                    await confirm_all_points_and_routes(trip_id)
                    await clear_draft(max_user_id)
                    await bot.send_message(
                        max_user_id,
                        "✅ <b>Рейс подтверждён.</b>\n\n"
                        "Логист увидит ваш ответ. Спасибо!",
                    )

            # ---------- reject_start:{trip_id} ----------
            elif payload.startswith("reject_start:"):
                trip_id = int(payload.split(":")[1])
                trip = await find_trip_by_id(trip_id)

                if not trip:
                    await bot.send_message(max_user_id, "❌ Рейс не найден.")
                elif not user or trip.driver_id != user.id:
                    await bot.send_message(max_user_id, "❌ Этот рейс не ваш.")
                elif trip.status in (TripStatus.REJECTED, TripStatus.CONFIRMED):
                    await bot.send_message(
                        max_user_id,
                        "❌ Рейс уже обработан — отказ невозможен.",
                    )
                else:
                    trip_date = trip.date.strftime("%d.%m.%Y")
                    await bot.send_message(
                        max_user_id,
                        f"🚫 <b>Отказ от рейса на {trip_date}</b>\n\n"
                        "Как отказаться?",
                        buttons=[
                            [{"type": "callback", "text": "🚫 От всего", "payload": f"reject_scope:trip:{trip_id}"}],
                            [{"type": "callback", "text": "✏️ Частично", "payload": f"reject_scope:partial:{trip_id}"}],
                            [{"type": "callback", "text": "← Назад", "payload": f"view_trip:{trip_id}"}],
                        ],
                    )

            # ---------- reject_scope:trip:{trip_id} ----------
            elif payload.startswith("reject_scope:trip:"):
                trip_id = int(payload.split(":")[2])
                trip = await find_trip_by_id(trip_id)

                if not trip or not user or trip.driver_id != user.id:
                    await bot.send_message(max_user_id, "❌ Рейс не найден.")
                else:
                    reasons = await find_reasons_by_scope(RejectionScope.TRIP)

                    if not reasons:
                        await reject_whole_trip(trip_id, None)
                        await clear_draft(max_user_id)
                        await bot.send_message(
                            max_user_id,
                            "❌ <b>Рейс отклонён.</b>\n\n"
                            "Логист увидит ваш отказ.",
                        )
                    else:
                        buttons = [
                            [{
                                "type": "callback",
                                "text": r.text,
                                "payload": f"reject_reason:trip:{trip_id}:{r.id}",
                            }]
                            for r in reasons
                        ]
                        buttons.append(
                            [{"type": "callback", "text": "← Назад", "payload": f"reject_start:{trip_id}"}]
                        )
                        await bot.send_message(
                            max_user_id,
                            "🚫 <b>Укажите причину отказа:</b>",
                            buttons=buttons,
                        )

            # ---------- reject_reason:trip:{trip_id}:{reason_id} ----------
            elif payload.startswith("reject_reason:trip:"):
                parts = payload.split(":")
                trip_id = int(parts[2])
                reason_id = int(parts[3])

                trip = await find_trip_by_id(trip_id)
                if not trip or not user or trip.driver_id != user.id:
                    await bot.send_message(max_user_id, "❌ Рейс не найден.")
                else:
                    async with AsyncSessionLocal() as db:
                        result = await db.execute(
                            select(RejectionReason).where(RejectionReason.id == reason_id)
                        )
                        reason = result.scalar_one_or_none()

                    reason_text = reason.text if reason else None

                    await reject_whole_trip(trip_id, reason_text)
                    await clear_draft(max_user_id)
                    await bot.send_message(
                        max_user_id,
                        f"❌ <b>Рейс отклонён.</b>\n\n"
                        f"Причина: {reason_text or '—'}\n\n"
                        "Логист увидит ваш отказ.",
                    )

            # ---------- reject_scope:partial:{trip_id} ----------
            elif payload.startswith("reject_scope:partial:"):
                trip_id = int(payload.split(":")[2])
                trip = await find_trip_by_id(trip_id)

                if not trip or not user or trip.driver_id != user.id:
                    await bot.send_message(max_user_id, "❌ Рейс не найден.")
                else:
                    draft = await get_draft(max_user_id) or {
                        "trip_id": trip_id,
                        "selected": {},
                    }
                    draft["trip_id"] = trip_id

                    text = format_routes_choices(trip, draft)
                    buttons = build_routes_buttons(trip, draft)

                    await bot.send_message(max_user_id, text, buttons=buttons)

            # ---------- reject_route_pick:{trip_id}:{route_id} ----------
            elif payload.startswith("reject_route_pick:"):
                parts = payload.split(":")
                trip_id = int(parts[1])
                route_id = int(parts[2])

                trip = await find_trip_by_id(trip_id)
                if not trip or not user or trip.driver_id != user.id:
                    await bot.send_message(max_user_id, "❌ Рейс не найден.")
                else:
                    route = next((r for r in trip.routes if r.id == route_id), None)
                    if not route:
                        await bot.send_message(max_user_id, "❌ Маршрут не найден.")
                    else:
                        reasons = await find_reasons_by_scope(RejectionScope.ROUTE)

                        if not reasons:
                            # Нет причин — сразу в selected с null
                            draft = await get_draft(max_user_id) or {
                                "trip_id": trip_id,
                                "selected": {},
                            }
                            draft["selected"][str(route_id)] = {
                                "reason_id": None,
                                "reason_text": None,
                            }
                            await save_draft(max_user_id, draft)

                            # Возврат к списку маршрутов
                            text = format_routes_choices(trip, draft)
                            buttons = build_routes_buttons(trip, draft)
                            await bot.send_message(max_user_id, text, buttons=buttons)
                        else:
                            route_name = route.name or f"Маршрут #{route.order_number}"
                            buttons = [
                                [{
                                    "type": "callback",
                                    "text": r.text,
                                    "payload": f"reject_reason:route:{trip_id}:{route_id}:{r.id}",
                                }]
                                for r in reasons
                            ]
                            buttons.append([
                                {"type": "callback", "text": "← Назад",
                                 "payload": f"reject_scope:partial:{trip_id}"}
                            ])
                            await bot.send_message(
                                max_user_id,
                                f"🚫 <b>Причина отказа для «{route_name}»:</b>",
                                buttons=buttons,
                            )

            # ---------- reject_reason:route:{trip_id}:{route_id}:{reason_id} ----------
            elif payload.startswith("reject_reason:route:"):
                parts = payload.split(":")
                trip_id = int(parts[2])
                route_id = int(parts[3])
                reason_id = int(parts[4])

                trip = await find_trip_by_id(trip_id)
                if not trip or not user or trip.driver_id != user.id:
                    await bot.send_message(max_user_id, "❌ Рейс не найден.")
                else:
                    async with AsyncSessionLocal() as db:
                        result = await db.execute(
                            select(RejectionReason).where(RejectionReason.id == reason_id)
                        )
                        reason = result.scalar_one_or_none()

                    reason_text = reason.text if reason else None

                    draft = await get_draft(max_user_id) or {
                        "trip_id": trip_id,
                        "selected": {},
                    }
                    draft["selected"][str(route_id)] = {
                        "reason_id": reason_id,
                        "reason_text": reason_text,
                    }
                    await save_draft(max_user_id, draft)

                    # Возврат к списку маршрутов
                    text = format_routes_choices(trip, draft)
                    buttons = build_routes_buttons(trip, draft)
                    await bot.send_message(max_user_id, text, buttons=buttons)

            # ---------- reject_route_unpick:{trip_id}:{route_id} ----------
            elif payload.startswith("reject_route_unpick:"):
                parts = payload.split(":")
                trip_id = int(parts[1])
                route_id = int(parts[2])

                trip = await find_trip_by_id(trip_id)
                if not trip or not user or trip.driver_id != user.id:
                    await bot.send_message(max_user_id, "❌ Рейс не найден.")
                else:
                    draft = await get_draft(max_user_id) or {
                        "trip_id": trip_id,
                        "selected": {},
                    }
                    draft["selected"].pop(str(route_id), None)
                    await save_draft(max_user_id, draft)

                    text = format_routes_choices(trip, draft)
                    buttons = build_routes_buttons(trip, draft)
                    await bot.send_message(max_user_id, text, buttons=buttons)

            # ---------- reject_partial_apply:{trip_id} ----------
            elif payload.startswith("reject_partial_apply:"):
                trip_id = int(payload.split(":")[1])

                trip = await find_trip_by_id(trip_id)
                if not trip or not user or trip.driver_id != user.id:
                    await bot.send_message(max_user_id, "❌ Рейс не найден.")
                else:
                    draft = await get_draft(max_user_id) or {
                        "trip_id": trip_id,
                        "selected": {},
                    }

                    trip = await apply_partial_reject(trip_id, draft)
                    await clear_draft(max_user_id)

                    rejected_count = len(draft.get("selected", {}))
                    total_routes = len(trip.routes) if trip else 0
                    confirmed_count = total_routes - rejected_count

                    await bot.send_message(
                        max_user_id,
                        f"✅ <b>Готово!</b>\n\n"
                        f"Отклонено маршрутов: {rejected_count}\n"
                        f"Подтверждено маршрутов: {confirmed_count}\n\n"
                        "Логист увидит ваш ответ.",
                    )

            # ---------- неизвестный payload ----------
            else:
                print(f"⚠️ Неизвестный payload: {payload}")

            if callback_id:
                await bot.answer_callback(callback_id)

        return {"status": "ok"}
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return {"status": "error", "detail": str(e)}