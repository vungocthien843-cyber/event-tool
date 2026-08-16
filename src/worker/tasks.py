import httpx
from arq import Retry
from datetime import datetime
from src.core.database import async_session_maker
from src.services.github import fetch_file_content, GitHubClientError
from src.services.catalog import process_catalog_upsert, process_catalog_removal

async def job_process_catalog(ctx, repo_full_name: str, file_path: str, commit_sha: str, commit_ts: datetime):
    client: httpx.AsyncClient = ctx.get("httpx_client")
    
    print(f"[Worker] Fetching {file_path} from GitHub...")
    try:
        content = await fetch_file_content(client, repo_full_name=repo_full_name, file_path=file_path, ref=commit_sha)
        print(f"[Worker] Successfully fetched {len(content)} bytes.")
    except GitHubClientError as e:
        print(f"[Worker] Failed to fetch {file_path}: {e}")
        return
    except Exception as e:
        print(f"[Worker] Unexpected error fetching {file_path}: {e}")
        # Lỗi kết nối mạng hoặc lỗi server GitHub (401/403/500), thử lại sau 10 giây
        raise Retry(defer=10) 

    print(f"[Worker] Upserting {file_path} to DB...")
    async with async_session_maker() as session:
        res = await process_catalog_upsert(
            session, repo_full_name=repo_full_name, file_path=file_path,
            commit_sha=commit_sha, commit_ts=commit_ts, raw_yaml=content
        )
        if res:
            print(f"[Worker] Successfully upserted {res} to DB!")
        else:
            print(f"[Worker] Skipped DB upsert (Invalid YAML format or stale event)")

async def job_remove_catalog(ctx, repo_full_name: str, file_path: str):
    print(f"[Worker] Removing {file_path} from DB...")
    async with async_session_maker() as session:
        await process_catalog_removal(session, repo_full_name=repo_full_name, file_path=file_path)
