from functools import lru_cache
from urllib.parse import parse_qs, urlsplit, urlunsplit
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    github_token: str
    webhook_secret: str
    
    app_env: str = "development"
    app_port: int = 8000
    app_host: str = "0.0.0.0"
    cors_origins: str = ""
    log_level: str = "INFO"

    @property
    def async_database_url(self) -> str:
        parts = urlsplit(self.database_url)
        scheme = "postgresql+asyncpg"
        return urlunsplit((scheme, parts.netloc, parts.path, "", ""))

    @property
    def asyncpg_connect_args(self) -> dict:
        parts = urlsplit(self.database_url)
        query = parse_qs(parts.query)
        connect_args: dict = {}
        sslmode = query.get("sslmode", [None])[0]
        if sslmode in ("require", "verify-ca", "verify-full"):
            connect_args["ssl"] = "require"
        options = query.get("options", [None])[0]
        if options:
            search_path = None
            for token in options.split():
                if token.startswith("-c"):
                    key, _, value = token[2:].partition("=")
                    if key == "search_path":
                        search_path = value
            if search_path:
                connect_args["server_settings"] = {"search_path": search_path}
        return connect_args

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
