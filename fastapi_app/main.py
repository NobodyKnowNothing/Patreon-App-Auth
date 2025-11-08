import os
import hmac
import hashlib
import logging
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from .sheets import SheetsDB
from dotenv import load_dotenv

# --- Suggested Improvement: Configure Logging ---
# Set up structured logging to get clearer, more useful output than print()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()

# --- Suggested Improvement: Fail-fast if critical config is missing ---
PATREON_WEBHOOK_SECRET = os.getenv("PATREON_WEBHOOK_SECRET")
if not PATREON_WEBHOOK_SECRET:
    logging.error("FATAL: PATREON_WEBHOOK_SECRET environment variable not set.")
    # In a real app, you might raise an exception here to prevent it from starting
    # raise ValueError("FATAL: PATREON_WEBHOOK_SECRET environment variable not set.")

class WebhookEnvelope(BaseModel):
    event_type: str | None = None
    original_event_type: str | None = None
    data: dict | None = None
    included: list | None = None


app = FastAPI(title="Patreon App Auth", version="0.1.0")
db = SheetsDB.from_env()


@app.get("/check_patron/{user_id}")
async def check_patron_status(user_id: str):
    """
    Checks if a user exists in the database.
    This is the endpoint the Tkinter app calls for authorization.
    """
    logging.info(f"Checking patron status for user_id: {user_id}")
    patron_data = await db.get_user(user_id)

    if patron_data is not None:
        logging.info(f"Patron found: {user_id}")
        return {"is_patron": True, "user_id": user_id, "data": patron_data}
    else:
        logging.warning(f"Patron not found: {user_id}")
        raise HTTPException(
            status_code=404, 
            detail="Patron not found"
        )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


def verify_signature(secret: str, signature: str | None, body: bytes) -> bool:
    if not signature:
        return False
    # Patreon's signature is the MD5 hash of the webhook body, using the secret as the key.
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.md5).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.post("/webhook")
async def patreon_webhook(
    request: Request,
    x_patreon_signature: str | None = Header(default=None, alias="X-Patreon-Signature"),
):
    body = await request.body()
    
    if not verify_signature(PATREON_WEBHOOK_SECRET, x_patreon_signature, body):
        logging.error("Webhook signature verification failed.")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        envelope = WebhookEnvelope.model_validate_json(body.decode())
    except Exception as e:
        logging.error(f"Failed to parse webhook JSON: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    
    event_type = envelope.original_event_type or envelope.event_type
    logging.info(f"Received webhook event: {event_type}")

    # Extract user data from the "included" list for a more complete record
    user_attributes = {}
    if envelope.included:
        for item in envelope.included:
            if item.get("type") == "user":
                user_attributes = item.get("attributes", {})
                break # Found the user data, no need to loop further
    
    # Extract user ID from the main data block
    user_id = None
    if envelope.data and envelope.data.get("type") == "member":
        user_data = envelope.data.get("relationships", {}).get("user", {}).get("data", {})
        user_id = user_data.get("id")
    
    if not user_id:
        logging.warning("Webhook received but no user_id could be extracted.")
        return {"success": False, "detail": "No user ID found in payload"}
        
    if event_type and ("delete" in event_type.lower() or "destroy" in event_type.lower()):
        logging.info(f"Deleting patron due to '{event_type}' event. User ID: {user_id}")
        await db.delete_user(user_id)
        return {"status": "deleted", "user_id": user_id}
    else:
        # --- Suggested Improvement: Store more useful patron data ---
        patron_data_to_store = {
            "full_name": user_attributes.get("full_name"),
            "email": user_attributes.get("email"),
            "last_event": event_type,
        }
        logging.info(f"Upserting patron. User ID: {user_id}, Data: {patron_data_to_store}")
        await db.upsert_user(user_id, patron_data_to_store)
        return {"status": "upserted", "user_id": user_id}


# Compatibility route for existing infrastructure
@app.post("/patreon/webhooks")
async def patreon_webhook_compat(
    request: Request,
    x_patreon_signature: str | None = Header(default=None, alias="X-Patreon-Signature"),
):
    return await patreon_webhook(request, x_patreon_signature)