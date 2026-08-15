import logging
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Service, ServiceDependency, ServiceMember
from app.parser import CatalogParseError, ParsedCatalog, parse_catalog_yaml

logger = logging.getLogger(__name__)


async def process_catalog_upsert(
    session: AsyncSession,
    *,
    repo_full_name: str,
    file_path: str,
    commit_sha: str,
    commit_ts: datetime,
    raw_yaml: str,
) -> str | None:
    """Parse and upsert a catalog-info.yaml file into the 3 tables.

    Returns the service_key that was written, or None if the event was
    skipped (parse error, stale event, or repo/service_key conflict).
    """
    try:
        parsed: ParsedCatalog = parse_catalog_yaml(raw_yaml)
    except CatalogParseError as exc:
        logger.warning("Failed to parse %s/%s@%s: %s", repo_full_name, file_path, commit_sha, exc)
        return None

    async with session.begin():
        existing = (
            await session.execute(
                select(Service).where(Service.service_key == parsed.service_key).with_for_update()
            )
        ).scalar_one_or_none()

        if existing is not None and existing.repo_full_name != repo_full_name:
            logger.warning(
                "service_key conflict: %s already owned by repo %s, ignoring update from %s",
                parsed.service_key,
                existing.repo_full_name,
                repo_full_name,
            )
            return None

        if existing is not None and existing.source_commit_ts >= commit_ts:
            logger.info(
                "Stale event for %s (incoming commit_ts=%s <= stored=%s), skipping",
                parsed.service_key,
                commit_ts,
                existing.source_commit_ts,
            )
            return None

        if existing is None:
            existing = Service(service_key=parsed.service_key)
            session.add(existing)

        existing.domain = parsed.domain
        existing.commit_hash = commit_sha
        existing.source_commit_ts = commit_ts
        existing.system = parsed.system
        existing.namespace = parsed.namespace
        existing.service_id = parsed.service_id
        existing.service_type = parsed.service_type
        existing.name = parsed.name
        existing.description = parsed.description
        existing.review_branch = parsed.review_branch
        existing.raw_yaml = raw_yaml
        existing.repo_full_name = repo_full_name
        existing.file_path = file_path

        await session.execute(
            delete(ServiceMember).where(ServiceMember.service_key == parsed.service_key)
        )
        await session.execute(
            delete(ServiceDependency).where(ServiceDependency.service_key == parsed.service_key)
        )

        for member in parsed.members:
            session.add(
                ServiceMember(
                    service_key=parsed.service_key,
                    user_email=member.user_email,
                    role=member.role,
                )
            )

        for dep in parsed.dependencies:
            session.add(
                ServiceDependency(
                    service_key=parsed.service_key,
                    target_ref=dep.target_ref,
                    ref_kind=dep.ref_kind,
                    protocol=dep.protocol,
                    reason=dep.reason,
                )
            )

    return parsed.service_key


async def process_catalog_removal(
    session: AsyncSession, *, repo_full_name: str, file_path: str
) -> str | None:
    """Delete the service (and cascaded members/dependencies) matching the removed file.

    Returns the deleted service_key, or None if no matching row was found.
    """
    async with session.begin():
        existing = (
            await session.execute(
                select(Service)
                .where(Service.repo_full_name == repo_full_name, Service.file_path == file_path)
                .with_for_update()
            )
        ).scalar_one_or_none()

        if existing is None:
            logger.info("No service found for removed file %s/%s, nothing to delete", repo_full_name, file_path)
            return None

        service_key = existing.service_key
        await session.delete(existing)

    return service_key
