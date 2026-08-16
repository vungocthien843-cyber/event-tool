import httpx
from arq.connections import RedisSettings
from urllib.parse import urlparse
from src.core.config import settings
from src.worker.tasks import job_full_sync

# Khởi tạo cấu hình Redis từ chuỗi kết nối
redis_settings = RedisSettings.from_dsn(settings.redis_url)

async def startup(ctx):
    # Mở một HTTP client dùng chung cho toàn bộ Worker
    ctx["httpx_client"] = httpx.AsyncClient(timeout=10.0)
    print("Worker is ready to process YAML files!")

async def shutdown(ctx):
    # Dọn dẹp đóng kết nối HTTP khi tắt Worker
    await ctx["httpx_client"].aclose()
    print("Worker shut down gracefully.")

class WorkerSettings:
    redis_settings = redis_settings
    functions = [job_full_sync]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10  # Tối ưu cho Neon Postgres để tránh nghẽn Connection Pool
