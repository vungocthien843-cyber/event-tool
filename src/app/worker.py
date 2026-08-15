import logging
from pathlib import PurePosixPath

import httpx
from arq.connections import RedisSettings

from app.config import settings
from app.database import async_session_maker, init_db
from app.github_client import GitHubClientError, fetch_file_content
from app.notifier import send_change_notification
from app.schemas import GitHubPushPayload
from app.webhook_handler import process_catalog_removal, process_catalog_upsert

logger = logging.getLogger(__name__)

CATALOG_FILENAME = "catalog-info.yaml"


async def startup(ctx: dict) -> None:
    await init_db()
    ctx["http_client"] = httpx.AsyncClient(timeout=10.0)


async def shutdown(ctx: dict) -> None:
    await ctx["http_client"].aclose()


def _collect_catalog_paths(payload: GitHubPushPayload) -> tuple[list[str], list[str]]:
    """Union of added/modified and removed catalog-info.yaml paths across all commits.

    Later commits in the push win for a given path (last-write-wins), matching
    the order GitHub lists commits in (oldest first).
    """
    upsert_paths: dict[str, bool] = {}

    for commit in payload.commits:
        for path in commit.added + commit.modified:
            if PurePosixPath(path).name == CATALOG_FILENAME:
                upsert_paths[path] = True
        for path in commit.removed:
            if PurePosixPath(path).name == CATALOG_FILENAME:
                upsert_paths[path] = False

    added_or_modified = [p for p, keep in upsert_paths.items() if keep]
    removed = [p for p, keep in upsert_paths.items() if not keep]
    return added_or_modified, removed


async def sync_catalog_from_push(ctx: dict, payload: dict) -> dict:
    push = GitHubPushPayload.model_validate(payload)

    if push.head_commit is None:
        logger.info("Push payload for %s has no head_commit, nothing to do", push.repository.full_name)
        return {"processed": 0}

    repo_full_name = push.repository.full_name
    commit_sha = push.head_commit.id
    commit_ts = push.head_commit.timestamp

    added_or_modified, removed = _collect_catalog_paths(push)

    http_client: httpx.AsyncClient = ctx["http_client"]
    results: list[dict] = []

    for file_path in removed:
        async with async_session_maker() as session:
            try:
                service_key = await process_catalog_removal(
                    session, repo_full_name=repo_full_name, file_path=file_path
                )
            except Exception:
                logger.exception("Failed to process removal of %s/%s", repo_full_name, file_path)
                continue

        if service_key:
            results.append({"event": "deleted", "service_key": service_key, "path": file_path})
            await send_change_notification(
                http_client,
                event="deleted",
                service_key=service_key,
                repo_full_name=repo_full_name,
                file_path=file_path,
            )

    for file_path in added_or_modified:
        try:
            content = await fetch_file_content(
                http_client, repo_full_name=repo_full_name, file_path=file_path, ref=commit_sha
            )
        except GitHubClientError:
            logger.exception("Failed to fetch %s/%s@%s", repo_full_name, file_path, commit_sha)
            continue

        async with async_session_maker() as session:
            try:
                service_key = await process_catalog_upsert(
                    session,
                    repo_full_name=repo_full_name,
                    file_path=file_path,
                    commit_sha=commit_sha,
                    commit_ts=commit_ts,
                    raw_yaml=content,
                )
            except Exception:
                logger.exception("Failed to process upsert of %s/%s", repo_full_name, file_path)
                continue

        if service_key:
            results.append({"event": "upserted", "service_key": service_key, "path": file_path})
            await send_change_notification(
                http_client,
                event="upserted",
                service_key=service_key,
                repo_full_name=repo_full_name,
                file_path=file_path,
            )

    return {"processed": len(results), "results": results}


class WorkerSettings:
    functions = [sync_catalog_from_push]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    job_timeout = 60
    max_jobs = 10
