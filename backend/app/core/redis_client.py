import json
from typing import Optional
import redis.asyncio as aioredis
from app.config import settings


# Один клиент на всё приложение
redis_client = aioredis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
)

# TTL черновика — 2 часа
DRAFT_TTL = 7200


def _draft_key(max_user_id: int | str) -> str:
    """Ключ черновика в Redis для пользователя."""
    return f"pl1:draft:{max_user_id}"


async def get_draft(max_user_id: int | str) -> Optional[dict]:
    """
    Получить черновик отказа.
    Возвращает dict или None, если черновика нет.
    """
    data = await redis_client.get(_draft_key(max_user_id))
    if not data:
        return None
    return json.loads(data)


async def save_draft(
    max_user_id: int | str,
    draft: dict,
    ttl: int = DRAFT_TTL,
) -> None:
    """Сохранить черновик с TTL."""
    await redis_client.set(
        _draft_key(max_user_id),
        json.dumps(draft, ensure_ascii=False),
        ex=ttl,
    )


async def clear_draft(max_user_id: int | str) -> None:
    """Удалить черновик."""
    await redis_client.delete(_draft_key(max_user_id))