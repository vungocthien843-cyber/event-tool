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

async def fetch_repo_tree(client: httpx.AsyncClient, repo_full_name: str, branch: str) -> list[str]:
    url = f"https://api.github.com/repos/{repo_full_name}/git/trees/{branch}"
    headers = {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = await client.get(url, headers=headers, params={"recursive": "1"})
    
    if response.status_code == 404:
        # Nhánh không tồn tại hoặc bị xóa
        return []
    
    response.raise_for_status()
    data = response.json()
    
    yaml_files = []
    for item in data.get("tree", []):
        path = item.get("path", "")
        if item.get("type") == "blob" and (path.endswith(".yaml") or path.endswith(".yml")):
            yaml_files.append(path)
            
    return yaml_files
