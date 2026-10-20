from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class UserPublic(BaseModel):
    """Публичный профиль пользователя — то, что отдаём фронту."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    full_name: str | None
    role: UserRole


class TokenResponse(BaseModel):
    """Ответ на успешную аутентификацию."""

    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class ContactBindRequest(BaseModel):
    phone: str
    auth_date: str
    user_id: str
    hash: str
