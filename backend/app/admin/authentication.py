from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

class AdminAuth(AuthenticationBackend):
    """Аутентификация для админки"""
    
    async def login(self, request: Request) -> bool:
        """Обработка входа в админку"""
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        
        # Временно: простой логин/пароль (позже заменим на JWT)
        if username == "admin" and password == "admin":
            request.session.update({"admin": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        """Выход из админки"""
        request.session.clear()
        return True

    async def authenticate(self, request: Request):
        """Проверка аутентификации"""
        if request.session.get("admin"):
            return True
        return False

authentication_backend = AdminAuth(secret_key="admin-secret-key-change-in-production")
