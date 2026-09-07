import hashlib
import hmac
import json
from urllib.parse import urlparse, parse_qs
from app.config import settings

def validate_init_data(init_data: str) -> dict:
    """
    Проверяет подпись initData от MAX.
    Возвращает данные пользователя, если подпись верна.
    
    Формат initData:
    user=%7B%22id%22%3A12345%2C%22first_name%22%3A%22John%22%7D&auth_date=1234567890&hash=...
    """
    # Парсим строку
    parsed = parse_qs(init_data)
    
    # Извлекаем hash
    received_hash = parsed.get('hash', [None])[0]
    if not received_hash:
        raise ValueError("Missing hash in initData")
    
    # Удаляем hash из данных для проверки
    parsed.pop('hash', None)
    
    # Сортируем и собираем строку для проверки
    sorted_items = sorted(parsed.items())
    data_check_string = '\n'.join([f"{k}={v[0]}" for k, v in sorted_items])
    
    # Вычисляем HMAC-SHA256
    secret_key = hashlib.sha256(settings.MAX_BOT_TOKEN.encode()).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    if computed_hash != received_hash:
        raise ValueError("Invalid initData signature")
    
    # Парсим user
    user_data = parsed.get('user', [None])[0]
    if user_data:
        try:
            user = json.loads(user_data)
            return user
        except json.JSONDecodeError:
            raise ValueError("Invalid user data in initData")
    
    # Если user нет — пробуем получить другие данные
    return {
        'id': parsed.get('id', [None])[0],
        'first_name': parsed.get('first_name', [None])[0],
        'last_name': parsed.get('last_name', [None])[0],
        'username': parsed.get('username', [None])[0],
    }
