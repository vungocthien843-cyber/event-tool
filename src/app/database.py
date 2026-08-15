from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


_connect_args = dict(settings.asyncpg_connect_args)
_search_path = _connect_args.pop("server_settings", {}).get("search_path")

engine = create_async_engine(
    settings.async_database_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
)

if _search_path:
    # asyncpg's `server_settings` startup param is silently ignored behind
    # Neon's connection pooler, so the search_path is set explicitly on
    # every new physical connection instead.
    @event.listens_for(engine.sync_engine, "connect")
    def _set_search_path(dbapi_connection, connection_record) -> None:
        dbapi_connection.run_async(lambda c: c.execute(f"SET search_path TO {_search_path}"))

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_maker() as session:
        yield session
