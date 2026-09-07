from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/webhook")
async def max_webhook(request: Request):
    try:
        data = await request.json()
        print("📩 Webhook received:", data)
        return {"status": "ok"}
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return {"status": "error", "detail": str(e)}
