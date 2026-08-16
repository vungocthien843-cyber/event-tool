import hashlib
import hmac
import logging
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from app.database import init_db
from app.schemas import GitHubPushPayload

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    yield
    await app.state.arq_pool.close()


app = FastAPI(title="IDP Catalog Webhook Ingest", lifespan=lifespan)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _verify_signature(secret: str, body: bytes, signature_header: str | None) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/webhook/github", status_code=202)
async def github_webhook(request: Request):
    body = await request.body()

    signature = request.headers.get("X-Hub-Signature-256")
    if not _verify_signature(settings.webhook_secret, body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    event = request.headers.get("X-GitHub-Event")
    if event == "ping":
        return JSONResponse(status_code=200, content={"status": "pong"})
    if event != "push":
        return JSONResponse(status_code=202, content={"status": "ignored", "event": event})

    try:
        payload = GitHubPushPayload.model_validate_json(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}") from exc

    await request.app.state.arq_pool.enqueue_job(
        "sync_catalog_from_push", payload.model_dump(mode="json")
    )

    return JSONResponse(status_code=202, content={"status": "accepted"})
