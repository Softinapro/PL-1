from fastapi import APIRouter
from app.api.v1.endpoints import auth, me, driver, import_trips, webhook

router = APIRouter()

router.include_router(auth.router)
router.include_router(me.router)
router.include_router(driver.router)
router.include_router(import_trips.router)
router.include_router(webhook.router)

@router.get("/ping")
async def ping():
    return {"message": "pong"}
