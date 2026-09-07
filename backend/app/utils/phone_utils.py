def normalize_phone(phone: str) -> str:
    """
    Приводит номер телефона к формату 9XXXXXXXXXX (10 цифр, начинается с 9)
    Поддерживает форматы:
    - 9XXXXXXXXXX
    - 89XXXXXXXXXX
    - 79XXXXXXXXXX
    - +79XXXXXXXXXX
    - +7(9XX)XXX-XX-XX
    - 8(9XX)XXX-XX-XX
    """
    # Убираем все нецифровые символы
    cleaned = ''.join(filter(str.isdigit, phone))
    
    if not cleaned:
        raise ValueError("Номер телефона не может быть пустым")
    
    # Если номер начинается с 8 — убираем
    if cleaned.startswith('8'):
        cleaned = cleaned[1:]
    
    # Если номер начинается с 7 — убираем
    elif cleaned.startswith('7'):
        cleaned = cleaned[1:]
    
    # Проверяем, что осталось 10 цифр и начинается с 9
    if len(cleaned) == 10 and cleaned.startswith('9'):
        return cleaned
    
    # Если длина 11 (с кодом страны) — обрезаем
    if len(cleaned) == 11 and cleaned.startswith('7'):
        cleaned = cleaned[1:]
        if len(cleaned) == 10 and cleaned.startswith('9'):
            return cleaned
    
    # Если длина 11 и начинается с 8
    if len(cleaned) == 11 and cleaned.startswith('8'):
        cleaned = cleaned[1:]
        if len(cleaned) == 10 and cleaned.startswith('9'):
            return cleaned
    
    raise ValueError(f"Неверный формат номера: {phone}")
