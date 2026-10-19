from sqladmin import ModelView
from app.models import (
    User, DriverProfile, Trip, Route, Point, MaxWebhookLog,
    RejectionReason, RejectionScope,
)
from app.models.user import UserRole
from app.models.trip import TripStatus
from app.models.route import RouteStatus
from app.models.point import PointStatus

# ========== ФОРМАТТЕРЫ ДЛЯ СТАТУСОВ ==========

def format_trip_status(model, attr):
    mapping = {
        TripStatus.PENDING: "⏳ Ожидает",
        TripStatus.SENT: "📨 Отправлен",
        TripStatus.CONFIRMED: "✅ Подтверждён",
        TripStatus.PARTIAL: "⚠️ Частично",
        TripStatus.REJECTED: "❌ Отклонён",
    }
    return mapping.get(model.status, model.status.value)


def format_route_status(model, attr):
    mapping = {
        RouteStatus.PENDING: "⏳ Ожидает",
        RouteStatus.CONFIRMED: "✅ Подтверждён",
        RouteStatus.PARTIAL: "⚠️ Частично",
        RouteStatus.REJECTED: "❌ Отклонён",
    }
    return mapping.get(model.status, model.status.value)


def format_point_status(model, attr):
    mapping = {
        PointStatus.PENDING: "⏳ Ожидает",
        PointStatus.CONFIRMED: "✅ Подтверждена",
        PointStatus.REJECTED: "❌ Отклонена",
    }
    return mapping.get(model.status, model.status.value)


def format_user_role(model, attr):
    mapping = {
        UserRole.ADMIN: "Администратор",
        UserRole.LOGIST: "Логист",
        UserRole.DRIVER: "Водитель",
    }
    return mapping.get(model.role, model.role.value)


def format_rejection_scope(model, attr):
    mapping = {
        RejectionScope.TRIP: "🚛 Рейс",
        RejectionScope.ROUTE: "🛣 Маршрут",
        RejectionScope.POINT: "📍 Точка",
    }
    return mapping.get(model.scope, model.scope.value)


# ========== ПОЛЬЗОВАТЕЛИ ==========
class UserAdmin(ModelView, model=User):
    column_list = [
        User.id,
        User.phone,
        User.full_name,
        User.role,
        User.code,
        User.max_user_id,
        User.is_active,
        User.is_archived,
        User.created_at,
        User.updated_at,
    ]
    column_labels = {
        User.id: "ID",
        User.phone: "Телефон",
        User.full_name: "ФИО",
        User.role: "Роль",
        User.code: "Код 1С",
        User.max_user_id: "ID в MAX",
        User.is_active: "Активен",
        User.is_archived: "В архиве",
        User.created_at: "Дата создания",
        User.updated_at: "Дата обновления",
    }
    column_formatters = {
        User.role: format_user_role,
    }
    column_choices = {
        User.role: [
            (UserRole.ADMIN, "Администратор"),
            (UserRole.LOGIST, "Логист"),
            (UserRole.DRIVER, "Водитель"),
        ],
        User.is_active: [
            (True, "✅ Да"),
            (False, "❌ Нет"),
        ],
        User.is_archived: [
            (True, "✅ Да"),
            (False, "❌ Нет"),
        ],
    }
    column_searchable_list = [User.phone, User.full_name, User.code, User.max_user_id]
    column_filters = [User.role, User.is_active, User.is_archived]
    column_sortable_list = [User.id, User.created_at, User.full_name]
    column_default_sort = [(User.created_at, True)]
    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-user"


# ========== ПРОФИЛИ ВОДИТЕЛЕЙ ==========
class DriverProfileAdmin(ModelView, model=DriverProfile):
    column_list = [
        DriverProfile.id,
        DriverProfile.user_id,
        DriverProfile.max_user_id,
        DriverProfile.is_verified,
        DriverProfile.created_at,
        DriverProfile.updated_at,
    ]
    column_labels = {
        DriverProfile.id: "ID",
        DriverProfile.user_id: "Пользователь",
        DriverProfile.max_user_id: "ID в MAX",
        DriverProfile.is_verified: "Подтверждён",
        DriverProfile.created_at: "Дата создания",
        DriverProfile.updated_at: "Дата обновления",
    }
    column_choices = {
        DriverProfile.is_verified: [
            (True, "✅ Да"),
            (False, "❌ Нет"),
        ],
    }
    column_filters = [DriverProfile.is_verified]
    column_sortable_list = [DriverProfile.id, DriverProfile.created_at]
    name = "Профиль водителя"
    name_plural = "Профили водителей"
    icon = "fa-solid fa-id-card"


# ========== РЕЙСЫ ==========
class TripAdmin(ModelView, model=Trip):
    column_list = [
        Trip.id,
        Trip.driver_id,
        Trip.logist_id,
        Trip.logist_code,
        Trip.date,
        Trip.status,
        Trip.info,
        Trip.sent_at,
        Trip.created_at,
        Trip.updated_at,
    ]
    column_labels = {
        Trip.id: "ID",
        Trip.driver_id: "Водитель",
        Trip.logist_id: "Логист",
        Trip.logist_code: "Код логиста",
        Trip.date: "Дата рейса",
        Trip.status: "Статус",
        Trip.info: "Инфо",
        Trip.sent_at: "Отправлен в MAX",
        Trip.created_at: "Дата создания",
        Trip.updated_at: "Дата обновления",
    }
    column_formatters = {
        Trip.status: format_trip_status,
    }
    column_choices = {
        Trip.status: [
            (TripStatus.PENDING, "⏳ Ожидает"),
            (TripStatus.SENT, "📨 Отправлен"),
            (TripStatus.CONFIRMED, "✅ Подтверждён"),
            (TripStatus.PARTIAL, "⚠️ Частично"),
            (TripStatus.REJECTED, "❌ Отклонён"),
        ]
    }
    column_searchable_list = [Trip.driver_id, Trip.logist_id, Trip.logist_code]
    column_filters = [Trip.status, Trip.date]
    column_sortable_list = [Trip.id, Trip.date, Trip.created_at]
    column_default_sort = [(Trip.date, True)]
    name = "Рейс"
    name_plural = "Рейсы"
    icon = "fa-solid fa-truck"


# ========== МАРШРУТЫ ==========
class RouteAdmin(ModelView, model=Route):
    column_list = [
        Route.id,
        Route.trip_id,
        Route.order_number,
        Route.name,
        Route.status,
        Route.rejection_reason,
        Route.created_at,
        Route.updated_at,
    ]
    column_labels = {
        Route.id: "ID",
        Route.trip_id: "Рейс",
        Route.order_number: "Порядковый номер",
        Route.name: "Название",
        Route.status: "Статус",
        Route.rejection_reason: "Причина отказа",
        Route.created_at: "Дата создания",
        Route.updated_at: "Дата обновления",
    }
    column_formatters = {
        Route.status: format_route_status,
    }
    column_choices = {
        Route.status: [
            (RouteStatus.PENDING, "⏳ Ожидает"),
            (RouteStatus.CONFIRMED, "✅ Подтверждён"),
            (RouteStatus.PARTIAL, "⚠️ Частично"),
            (RouteStatus.REJECTED, "❌ Отклонён"),
        ]
    }
    column_searchable_list = [Route.name, Route.rejection_reason]
    column_filters = [Route.status, Route.trip_id]
    column_sortable_list = [Route.id, Route.order_number, Route.created_at]
    name = "Маршрут"
    name_plural = "Маршруты"
    icon = "fa-solid fa-route"


# ========== ТОРГОВЫЕ ТОЧКИ ==========
class PointAdmin(ModelView, model=Point):
    column_list = [
        Point.id,
        Point.route_id,
        Point.code,
        Point.order_number,
        Point.address,
        Point.status,
        Point.rejection_reason,
        Point.created_at,
        Point.updated_at,
    ]
    column_labels = {
        Point.id: "ID",
        Point.route_id: "Маршрут",
        Point.code: "Код точки",
        Point.order_number: "Порядковый номер",
        Point.address: "Адрес",
        Point.status: "Статус",
        Point.rejection_reason: "Причина отказа",
        Point.created_at: "Дата создания",
        Point.updated_at: "Дата обновления",
    }
    column_formatters = {
        Point.status: format_point_status,
    }
    column_choices = {
        Point.status: [
            (PointStatus.PENDING, "⏳ Ожидает"),
            (PointStatus.CONFIRMED, "✅ Подтверждена"),
            (PointStatus.REJECTED, "❌ Отклонена"),
        ]
    }
    column_searchable_list = [Point.code, Point.address, Point.rejection_reason]
    column_filters = [Point.status, Point.route_id]
    column_sortable_list = [Point.id, Point.order_number, Point.created_at]
    name = "Торговая точка"
    name_plural = "Торговые точки"
    icon = "fa-solid fa-location-dot"


# ========== ПРИЧИНЫ ОТКАЗА ==========
class RejectionReasonAdmin(ModelView, model=RejectionReason):
    column_list = [
        RejectionReason.id,
        RejectionReason.scope,
        RejectionReason.text,
        RejectionReason.is_active,
        RejectionReason.created_at,
        RejectionReason.updated_at,
    ]
    column_labels = {
        RejectionReason.id: "ID",
        RejectionReason.scope: "Уровень",
        RejectionReason.text: "Текст причины",
        RejectionReason.is_active: "Активна",
        RejectionReason.created_at: "Дата создания",
        RejectionReason.updated_at: "Дата обновления",
    }
    column_formatters = {
        RejectionReason.scope: format_rejection_scope,
    }
    column_choices = {
        RejectionReason.scope: [
            (RejectionScope.TRIP, "🚛 Рейс (отказ от всего)"),
            (RejectionScope.ROUTE, "🛣 Маршрут"),
            (RejectionScope.POINT, "📍 Точка"),
        ],
        RejectionReason.is_active: [
            (True, "✅ Да"),
            (False, "❌ Нет"),
        ],
    }
    column_searchable_list = [RejectionReason.text]
    column_filters = [RejectionReason.scope, RejectionReason.is_active]
    column_sortable_list = [RejectionReason.id, RejectionReason.scope, RejectionReason.created_at]
    column_default_sort = [(RejectionReason.scope, False), (RejectionReason.id, False)]
    name = "Причина отказа"
    name_plural = "Причины отказа"
    icon = "fa-solid fa-circle-xmark"


# ========== ЛОГИ MAX ==========
class MaxWebhookLogAdmin(ModelView, model=MaxWebhookLog):
    column_list = [
        MaxWebhookLog.id,
        MaxWebhookLog.event_type,
        MaxWebhookLog.processed,
        MaxWebhookLog.processed_at,
        MaxWebhookLog.created_at,
        MaxWebhookLog.updated_at,
    ]
    column_labels = {
        MaxWebhookLog.id: "ID",
        MaxWebhookLog.event_type: "Тип события",
        MaxWebhookLog.payload: "Данные",
        MaxWebhookLog.processed: "Обработано",
        MaxWebhookLog.processed_at: "Время обработки",
        MaxWebhookLog.created_at: "Дата создания",
        MaxWebhookLog.updated_at: "Дата обновления",
    }
    column_choices = {
        MaxWebhookLog.processed: [
            (True, "✅ Да"),
            (False, "❌ Нет"),
        ],
    }
    column_filters = [MaxWebhookLog.event_type, MaxWebhookLog.processed]
    column_sortable_list = [MaxWebhookLog.id, MaxWebhookLog.created_at]
    column_default_sort = [(MaxWebhookLog.created_at, True)]
    name = "Лог MAX"
    name_plural = "Логи MAX"
    icon = "fa-solid fa-list"


# ========== СПИСОК ВСЕХ АДМИНОК ==========
admin_views = [
    UserAdmin,
    # DriverProfileAdmin,  # Скрыт
    TripAdmin,
    RouteAdmin,
    PointAdmin,
    RejectionReasonAdmin,
    MaxWebhookLogAdmin,
]