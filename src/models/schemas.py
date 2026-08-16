from datetime import datetime
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
