import httpx
from arq import Retry
from datetime import datetime
from src.core.database import async_session_maker
from src.models.domain import Service
from sqlalchemy import select
from src.services.github import fetch_file_content, fetch_repo_tree, GitHubClientError
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

async def job_full_sync(ctx, repo_full_name: str, commit_sha: str, commit_ts: datetime, branch: str):
    client: httpx.AsyncClient = ctx.get("httpx_client")
    print(f"\n[Worker] BAT DAU FULL SYNC CHO REPO: {repo_full_name} (branch: {branch})")
    
    # 1. Lấy cây thư mục từ GitHub
    print(f"[Worker] Fetching Git Tree for {branch}...")
    try:
        git_files = await fetch_repo_tree(client, repo_full_name, branch)
    except Exception as e:
        print(f"[Worker] Failed to fetch git tree: {e}")
        raise Retry(defer=10)
        
    print(f"[Worker] Tìm thấy {len(git_files)} file YAML trên GitHub.")
    
    # 2. Lấy danh sách file hiện có trong Database
    print("[Worker] Fetching DB state...")
    async with async_session_maker() as session:
        result = await session.execute(
            select(Service.file_path).where(Service.repo_full_name == repo_full_name)
        )
        db_files = [row[0] for row in result.all()]
        
    print(f"[Worker] Tìm thấy {len(db_files)} file YAML trong Database.")
    
    # 3. Tính toán Ghost Data
    git_files_set = set(git_files)
    db_files_set = set(db_files)
    ghost_files = db_files_set - git_files_set
    
    # 4. Xóa Ghost Data
    for file_path in ghost_files:
        await job_remove_catalog(ctx, repo_full_name, file_path)
        
    # 5. Cập nhật các file trên Git
    for file_path in git_files:
        await job_process_catalog(ctx, repo_full_name, file_path, commit_sha, commit_ts)
        
    print(f"[Worker] HOAN THANH FULL SYNC CHO REPO: {repo_full_name}\n")
