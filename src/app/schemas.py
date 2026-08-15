from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class GitHubCommit(BaseModel):
    id: str
    timestamp: datetime
    added: list[str] = []
    modified: list[str] = []
    removed: list[str] = []


class GitHubRepository(BaseModel):
    full_name: str


class GitHubPushPayload(BaseModel):
    ref: str
    repository: GitHubRepository
    head_commit: GitHubCommit | None = None
    commits: list[GitHubCommit] = []


class CatalogChangeNotification(BaseModel):
    event: Literal["upserted", "deleted"]
    service_key: str
    repo: str
    path: str
    timestamp: datetime
