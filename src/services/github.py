import httpx
from src.core.config import settings

class GitHubClientError(Exception):
    pass

async def fetch_file_content(client: httpx.AsyncClient, repo_full_name: str, file_path: str, ref: str) -> str:
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github.raw+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = await client.get(url, headers=headers, params={"ref": ref})
    if response.status_code == 404:
        raise GitHubClientError(f"File not found: {file_path}")
    response.raise_for_status()
    return response.text
