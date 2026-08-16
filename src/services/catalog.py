from datetime import datetime
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.domain import Service, ServiceDependency, ServiceMember
from src.services.parser import parse_catalog_yaml, CatalogParseError

async def process_catalog_upsert(
    session: AsyncSession, repo_full_name: str, file_path: str, commit_sha: str, commit_ts: datetime, raw_yaml: str
) -> str | None:
    try:
        parsed = parse_catalog_yaml(raw_yaml)
    except CatalogParseError:
        return None

    existing = (await session.execute(
        select(Service).where(Service.service_key == parsed.service_key).with_for_update()
    )).scalar_one_or_none()

    if existing and existing.source_commit_ts >= commit_ts:
        return None  # Stale event

    if not existing:
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

    await session.execute(delete(ServiceMember).where(ServiceMember.service_key == parsed.service_key))
    await session.execute(delete(ServiceDependency).where(ServiceDependency.service_key == parsed.service_key))

    for member in parsed.members:
        session.add(ServiceMember(service_key=parsed.service_key, user_email=member.user_email, role=member.role))
    for dep in parsed.dependencies:
        session.add(ServiceDependency(service_key=parsed.service_key, target_ref=dep.target_ref, ref_kind=dep.ref_kind, protocol=dep.protocol, reason=dep.reason))

    await session.commit()
    return parsed.service_key

async def process_catalog_removal(session: AsyncSession, repo_full_name: str, file_path: str) -> str | None:
    existing = (await session.execute(
        select(Service).where(Service.repo_full_name == repo_full_name, Service.file_path == file_path).with_for_update()
    )).scalar_one_or_none()

    if not existing:
        return None

    service_key = existing.service_key
    await session.delete(existing)
    await session.commit()
    return service_key
