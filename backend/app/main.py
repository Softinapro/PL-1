from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqladmin import Admin
from app.config import settings
from app.api.v1.router import router as v1_router
from app.database import engine
from app.admin.authentication import authentication_backend
from app.admin.admin import admin_views

app = FastAPI(
    title="Logistics API",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "logistics-api"}

# Подключаем API
app.include_router(v1_router, prefix="/api/v1")

# ========== НАСТРОЙКА АДМИНКИ SQLADMIN ==========
admin = Admin(app, engine, authentication_backend=authentication_backend)

# Регистрируем все модели
for view in admin_views:
    admin.add_view(view)  # <--- ИЗМЕНЕНО: add_view

# Админка автоматически доступна по /admin
# Добавляем webhook роутер отдельно (без префикса /api/v1)
from app.api.v1.endpoints.webhook import router as webhook_router
app.include_router(webhook_router)
