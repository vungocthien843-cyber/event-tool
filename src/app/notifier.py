import logging
from datetime import datetime, timezone
from typing import Literal

import httpx

from app.config import settings
from app.schemas import CatalogChangeNotification

logger = logging.getLogger(__name__)


async def send_change_notification(
    client: httpx.AsyncClient,
    *,
    event: Literal["upserted", "deleted"],
    service_key: str,
    repo_full_name: str,
    file_path: str,
) -> None:
    if not settings.notification_webhook_url:
        logger.debug("NOTIFICATION_WEBHOOK_URL not set, skipping notification for %s", service_key)
        return

    notification = CatalogChangeNotification(
        event=event,
        service_key=service_key,
        repo=repo_full_name,
        path=file_path,
        timestamp=datetime.now(timezone.utc),
    )

    try:
        response = await client.post(
            settings.notification_webhook_url,
            json=notification.model_dump(mode="json"),
            timeout=5.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Failed to send change notification for %s: %s", service_key, exc)
