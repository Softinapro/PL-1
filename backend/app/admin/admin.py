from sqladmin import ModelView
from app.models import (
    User, DriverProfile, Trip, Route, Point, MaxWebhookLog
)

# ========== ПОЛЬЗОВАТЕЛИ ==========
class UserAdmin(ModelView, model=User):
    column_list = [
        User.id,
        User.phone,
        User.full_name,
        User.role,
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
        User.is_active: "Активен",
        User.is_archived: "В архиве",
        User.created_at: "Дата создания",
        User.updated_at: "Дата обновления",
    }
    column_choices = {
        User.role: [
            ("admin", "Администратор"),
            ("logist", "Логист"),
            ("driver", "Водитель"),
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
    column_searchable_list = [User.phone, User.full_name]
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
        Trip.date,
        Trip.status,
        Trip.sent_at,
        Trip.created_at,
        Trip.updated_at,
    ]
    column_labels = {
        Trip.id: "ID",
        Trip.driver_id: "Водитель",
        Trip.logist_id: "Логист",
        Trip.date: "Дата рейса",
        Trip.status: "Статус",
        Trip.sent_at: "Отправлен в MAX",
        Trip.created_at: "Дата создания",
        Trip.updated_at: "Дата обновления",
    }
    column_choices = {
        Trip.status: [
            ("pending", "⏳ Ожидает"),
            ("sent", "📨 Отправлен"),
            ("confirmed", "✅ Подтверждён"),
            ("partial", "⚠️ Частично"),
            ("rejected", "❌ Отклонён"),
        ]
    }
    column_searchable_list = [Trip.driver_id, Trip.logist_id]
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
        Route.status,
        Route.address_start,
        Route.address_end,
        Route.rejection_reason,
        Route.created_at,
        Route.updated_at,
    ]
    column_labels = {
        Route.id: "ID",
        Route.trip_id: "Рейс",
        Route.order_number: "Порядковый номер",
        Route.status: "Статус",
        Route.address_start: "Начало маршрута",
        Route.address_end: "Конец маршрута",
        Route.rejection_reason: "Причина отказа",
        Route.created_at: "Дата создания",
        Route.updated_at: "Дата обновления",
    }
    column_choices = {
        Route.status: [
            ("pending", "⏳ Ожидает"),
            ("confirmed", "✅ Подтверждён"),
            ("rejected", "❌ Отклонён"),
        ]
    }
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
        Point.order_number: "Порядковый номер",
        Point.address: "Адрес",
        Point.status: "Статус",
        Point.rejection_reason: "Причина отказа",
        Point.created_at: "Дата создания",
        Point.updated_at: "Дата обновления",
    }
    column_choices = {
        Point.status: [
            ("pending", "⏳ Ожидает"),
            ("confirmed", "✅ Подтверждена"),
            ("rejected", "❌ Отклонена"),
        ]
    }
    column_filters = [Point.status, Point.route_id]
    column_sortable_list = [Point.id, Point.order_number, Point.created_at]
    name = "Торговая точка"
    name_plural = "Торговые точки"
    icon = "fa-solid fa-location-dot"

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
    DriverProfileAdmin,
    TripAdmin,
    RouteAdmin,
    PointAdmin,
    MaxWebhookLogAdmin,
]
