import hashlib
import hmac
from pathlib import PurePosixPath
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from src.core.config import settings
from src.models.schemas import GitHubPushPayload

router = APIRouter()

def _verify_signature(secret: str, body: bytes, signature_header: str | None) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)

# Bỏ hàm _collect_catalog_paths vì không cần phân tích từng commit nữa

@router.post("/v1/test_api")
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
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}")

    if payload.head_commit is None:
        return JSONResponse(status_code=202, content={"status": "no head_commit"})

    if payload.ref not in ["refs/heads/master", "refs/heads/main"]:
        return JSONResponse(status_code=202, content={"status": "ignored", "reason": "not master/main branch"})

    repo_full_name = payload.repository.full_name
    commit_sha = payload.head_commit.id
    commit_ts = payload.head_commit.timestamp

    # Lấy đối tượng kết nối Redis
    redis = request.app.state.redis

    # Đẩy tác vụ Full Sync vào hàng đợi (Queue)
    await redis.enqueue_job("job_full_sync", repo_full_name, commit_sha, commit_ts)
    print(f"Enqueued job_full_sync for {repo_full_name} at commit {commit_sha}")

    # Lập tức trả về 200 OK cho GitHub
    return JSONResponse(
        status_code=200, 
        content={"status": "success", "jobs_enqueued": 1}
    )
