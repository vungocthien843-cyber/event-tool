import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class GitHubClientError(Exception):
    pass


async def fetch_file_content(
    client: httpx.AsyncClient, *, repo_full_name: str, file_path: str, ref: str
) -> str:
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github.raw+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    response = await client.get(url, headers=headers, params={"ref": ref})

    if response.status_code == 404:
        raise GitHubClientError(
            f"File not found: {repo_full_name}/{file_path}@{ref}"
        )
    if response.is_error:
        logger.error(
            "GitHub API error fetching %s/%s@%s: %s %s",
            repo_full_name,
            file_path,
            ref,
            response.status_code,
            response.text,
        )
        raise GitHubClientError(
            f"GitHub API returned {response.status_code} for {repo_full_name}/{file_path}@{ref}"
        )

    return response.text
