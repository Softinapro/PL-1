#!/usr/bin/env python3
import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.models import User, UserRole

async def seed():
    async with AsyncSessionLocal() as session:
        users = [
            User(phone="+79001111111", full_name="Админ Иванов", role=UserRole.ADMIN),
            User(phone="+79002222222", full_name="Логист Петров", role=UserRole.LOGIST),
            User(phone="+79003333333", full_name="Водитель Сидоров", role=UserRole.DRIVER),
        ]
        for user in users:
            session.add(user)
        await session.commit()
        print("✅ Тестовые пользователи созданы!")

if __name__ == "__main__":
    asyncio.run(seed())
