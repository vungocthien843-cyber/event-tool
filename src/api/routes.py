import hashlib
import hmac
import httpx
from pathlib import PurePosixPath
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from src.core.config import settings
from src.core.database import async_session_maker
from src.models.schemas import GitHubPushPayload
from src.services.github import fetch_file_content, GitHubClientError
from src.services.catalog import process_catalog_upsert, process_catalog_removal

router = APIRouter()

import hashlib
import hmac

def _verify_signature(secret: str, body: bytes, signature_header: str | None) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)

def _collect_catalog_paths(payload: GitHubPushPayload) -> tuple[list[str], list[str]]:
    upsert_paths: dict[str, bool] = {}
    for commit in payload.commits:
        for path in commit.added + commit.modified:
            if path.endswith(".yaml") or path.endswith(".yml"):
                upsert_paths[path] = True
        for path in commit.removed:
            if path.endswith(".yaml") or path.endswith(".yml"):
                upsert_paths[path] = False
    added_or_modified = [p for p, keep in upsert_paths.items() if keep]
    removed = [p for p, keep in upsert_paths.items() if not keep]
    return added_or_modified, removed

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

    added_or_modified, removed = _collect_catalog_paths(payload)
    repo_full_name = payload.repository.full_name
    commit_sha = payload.head_commit.id
    commit_ts = payload.head_commit.timestamp

    # Synchronous processing for Serverless environment
    async with httpx.AsyncClient(timeout=10.0) as client:
        for file_path in removed:
            async with async_session_maker() as session:
                await process_catalog_removal(session, repo_full_name=repo_full_name, file_path=file_path)

        for file_path in added_or_modified:
            try:
                content = await fetch_file_content(client, repo_full_name=repo_full_name, file_path=file_path, ref=commit_sha)
            except GitHubClientError:
                continue
            
            async with async_session_maker() as session:
                await process_catalog_upsert(
                    session, repo_full_name=repo_full_name, file_path=file_path,
                    commit_sha=commit_sha, commit_ts=commit_ts, raw_yaml=content
                )

    return JSONResponse(status_code=200, content={"status": "success"})
