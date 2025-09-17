import os
import hmac
import hashlib
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from .sheets import SheetsDB


class WebhookEnvelope(BaseModel):
    event_type: str | None = None
    original_event_type: str | None = None
    data: dict | None = None
    included: list | None = None


app = FastAPI(title="Patreon App Auth", version="0.1.0")
db = SheetsDB.from_env()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


def verify_signature(secret: str | None, signature: str | None, body: bytes) -> bool:
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.md5).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.post("/webhook")
async def patreon_webhook(
    request: Request,
    x_patreon_signature: str | None = Header(default=None, alias="X-Patreon-Signature"),
    x_patreon_event: str | None = Header(default=None, alias="X-Patreon-Event"),
):
    body = await request.body()
    secret = os.getenv("PATREON_WEBHOOK_SECRET")
    
    if not verify_signature(secret, x_patreon_signature, body):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        envelope = WebhookEnvelope.model_validate_json(body.decode())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    
    event_type = envelope.original_event_type or envelope.event_type
    user_id = None
    
    if envelope.data and envelope.data.get("type") == "member":
        user_data = envelope.data.get("relationships", {}).get("user", {}).get("data", {})
        user_id = user_data.get("id")
    
    if user_id:
        if event_type and "delete" in event_type.lower():
            await db.delete_user(user_id)
        else:
            await db.upsert_user(user_id, {"last_seen": "now", "event": event_type})
    
    return {"success": True, "event": event_type or "unknown", "user_id": user_id}


# Compatibility route for existing infrastructure
@app.post("/patreon/webhooks")
async def patreon_webhook_compat(
    request: Request,
    x_patreon_signature: str | None = Header(default=None, alias="X-Patreon-Signature"),
    x_patreon_event: str | None = Header(default=None, alias="X-Patreon-Event"),
):
    return await patreon_webhook(request, x_patreon_signature, x_patreon_event)