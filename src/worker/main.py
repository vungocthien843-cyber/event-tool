import httpx
from arq.connections import RedisSettings
from urllib.parse import urlparse
from src.core.config import settings
from src.worker.tasks import job_process_catalog, job_remove_catalog

# Phân tích chuỗi kết nối REDIS_URL từ cấu hình
parsed = urlparse(settings.redis_url)
redis_settings = RedisSettings(
    host=parsed.hostname or 'localhost',
    port=parsed.port or 6379,
    database=int(parsed.path.strip('/')) if parsed.path and parsed.path.strip('/') else 0,
    password=parsed.password,
    ssl=parsed.scheme == 'rediss'
)

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
    functions = [job_process_catalog, job_remove_catalog]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10  # Tối ưu cho Neon Postgres để tránh nghẽn Connection Pool
