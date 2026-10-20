import hashlib
import hmac
import json
import time
from typing import Optional
from urllib.parse import unquote, parse_qsl


def validate_init_data(
    raw_init_data: str,
    bot_token: str,
    max_age_seconds: int = 3600,
) -> Optional[dict]:
    """
    Валидирует initData из MAX WebApp (Bridge).

    Возвращает распарсенный dict (с ключом "user" — уже распакованным JSON)
    при успехе, либо None при любой ошибке.

    Алгоритм (официальная дока MAX):
      1. Парсим raw_init_data по "&" -> [(key, value), ...] (значения не декодируем).
      2. Проверяем уникальность ключей. Дубликат -> fail.
      3. Извлекаем и исключаем "hash" (сохраняем оригинал).
      4. URL-декодируем все values.
      5. Сортируем пары по ключу (a -> z).
      6. Собираем launch_params = "k1=v1\\nk2=v2\\n...".
      7. secret_key = HMAC-SHA256(key=b"WebAppData", msg=bot_token).
      8. signature  = HMAC-SHA256(key=secret_key,   msg=launch_params).hexdigest()
      9. hmac.compare_digest(signature, hash).
     10. Проверяем auth_date (TTL).
    """
    if not raw_init_data:
        return None

    # --- 1. Парсим пары, не декодируя values ---
    try:
        pairs = [tuple(pair.split("=", 1)) for pair in raw_init_data.split("&")]
    except ValueError:
        return None

    # --- 2. Проверка уникальности ключей ---
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        return None

    # --- 3. Извлекаем и исключаем hash ---
    hash_from_data = None
    filtered_pairs = []
    for k, v in pairs:
        if k == "hash":
            hash_from_data = v
        else:
            filtered_pairs.append((k, v))

    if not hash_from_data:
        return None

    # --- 4. URL-декодируем values ---
    decoded_pairs = [(k, unquote(v)) for k, v in filtered_pairs]

    # --- 5. Сортируем по ключу ---
    decoded_pairs.sort(key=lambda kv: kv[0])

    # --- 6. Собираем launch_params через "\n" ---
    launch_params = "\n".join(f"{k}={v}" for k, v in decoded_pairs)

    # --- 7. secret_key = HMAC-SHA256(key="WebAppData", msg=bot_token) ---
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode(),
        digestmod=hashlib.sha256,
    ).digest()

    # --- 8. signature = HMAC-SHA256(key=secret_key, msg=launch_params) ---
    signature = hmac.new(
        key=secret_key,
        msg=launch_params.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    # --- 9. Сравнение с hash (constant-time) ---
    if not hmac.compare_digest(signature, hash_from_data):
        return None

    # --- 10. Проверка TTL ---
    result: dict = dict(decoded_pairs)

    auth_date_raw = result.get("auth_date")
    if auth_date_raw is None:
        return None
    try:
        auth_date = int(auth_date_raw)
    except (TypeError, ValueError):
        return None

    if time.time() - auth_date > max_age_seconds:
        return None

    # --- Распаковываем "user", если он есть (это JSON) ---
    user_raw = result.get("user")
    if user_raw:
        try:
            result["user"] = json.loads(user_raw)
        except json.JSONDecodeError:
            return None

    return result

def validate_contact_hash(
    phone: str,
    auth_date: str,
    user_id: str,
    received_hash: str,
    bot_token: str,
) -> bool:
    """
    Проверяет hash от window.WebApp.requestContact().
    Формула: HMAC_SHA256(key=botToken, msg="authDate=...\nphone=...\nuserId=...")
    Важно: phone без знака '+'.
    """
    clean_phone = phone.lstrip("+")
    launch_params = f"authDate={auth_date}\nphone={clean_phone}\nuserId={user_id}"
    
    signature = hmac.new(
        key=bot_token.encode(),
        msg=launch_params.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    
    return hmac.compare_digest(signature, received_hash)
