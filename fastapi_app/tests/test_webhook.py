import hmac
import hashlib
from fastapi.testclient import TestClient
from fastapi_app.main import app


client = TestClient(app)


def sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.md5).hexdigest()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_webhook_create(monkeypatch):
    secret = "test-secret"
    monkeypatch.setenv("PATREON_WEBHOOK_SECRET", secret)
    body = {
        "data": {
            "type": "member",
            "relationships": {"user": {"data": {"id": "u1"}}},
        },
        "original_event_type": "members:pledge:create",
    }
    import json

    b = json.dumps(body).encode()
    r = client.post(
        "/webhook",
        content=b,
        headers={
            "X-Patreon-Signature": sign(b, secret),
            "X-Patreon-Event": "members:pledge:create",
        },
    )
    assert r.status_code == 200
    assert r.json()["success"] is True


