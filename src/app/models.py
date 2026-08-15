import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Service(Base):
    __tablename__ = "services"

    service_key: Mapped[str] = mapped_column(primary_key=True)

    domain: Mapped[str]
    commit_hash: Mapped[str] = mapped_column(comment="git commit SHA that last wrote this row")
    source_commit_ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        comment="head_commit.timestamp from the webhook payload; drives idempotency ordering",
    )

    system: Mapped[str]
    namespace: Mapped[str]
    service_id: Mapped[str]
    service_type: Mapped[str]
    name: Mapped[str]
    description: Mapped[str | None] = mapped_column(Text)
    review_branch: Mapped[str]
    raw_yaml: Mapped[str] = mapped_column(Text)

    repo_full_name: Mapped[str]
    file_path: Mapped[str]

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    members: Mapped[list["ServiceMember"]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )
    dependencies: Mapped[list["ServiceDependency"]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("repo_full_name", "file_path", name="uq_services_repo_file_path"),
    )


class ServiceMember(Base):
    __tablename__ = "service_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_key: Mapped[str] = mapped_column(
        ForeignKey("services.service_key", ondelete="CASCADE")
    )
    user_email: Mapped[str]
    role: Mapped[str]

    service: Mapped["Service"] = relationship(back_populates="members")


class ServiceDependency(Base):
    __tablename__ = "service_dependencies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_key: Mapped[str] = mapped_column(
        ForeignKey("services.service_key", ondelete="CASCADE")
    )
    target_ref: Mapped[str]
    ref_kind: Mapped[str]
    protocol: Mapped[str | None]
    reason: Mapped[str | None] = mapped_column(Text)

    service: Mapped["Service"] = relationship(back_populates="dependencies")
