from contextlib import asynccontextmanager
from httpx import AsyncClient
from pathlib import Path
from typing import Annotated
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from platformdirs import PlatformDirs

from app import __version__ as version

PLATFORM_DIRS = PlatformDirs("feedwright", "semicolonsoftware")


class HttpSettings(BaseSettings):
    model_config: SettingsConfigDict = SettingsConfigDict(
        env_prefix="FEEDWRIGHT_HTTP_", env_file=".env", env_file_encoding="utf-8"
    )

    user_agent: str = Field(
        f"feedwright/{version}",
        description="The User-Agent header to use for HTTP requests",
    )

    verify_ssl: bool = Field(
        True, description="Whether to verify SSL certificates when making HTTP requests"
    )

    follow_redirects: bool = Field(
        True, description="Whether to follow redirects when making HTTP requests"
    )

    @asynccontextmanager
    async def get_async_client(self):
        async with AsyncClient(
            verify=self.verify_ssl,
            headers={"User-Agent": self.user_agent},
            follow_redirects=self.follow_redirects,
        ) as client:
            yield client


class GeneratorSettings(BaseSettings):
    model_config: SettingsConfigDict = SettingsConfigDict(
        env_prefix="FEEDWRIGHT_GENERATOR_", env_file=".env", env_file_encoding="utf-8"
    )

    name: str = Field(
        "feedwright", description="The name to use in the feed generator tag"
    )

    version: str | None = Field(
        version, description="The version to use in the feed generator tag"
    )


class Settings(BaseSettings):
    model_config: SettingsConfigDict = SettingsConfigDict(
        env_prefix="FEEDWRIGHT_", env_file=".env", env_file_encoding="utf-8"
    )

    require_token: str | None = Field(
        None,
        description="If not None, require this token to be passed as a bearer token for all API requests",
    )

    config_paths: Annotated[list[Path], NoDecode] = Field(
        [
            PLATFORM_DIRS.site_config_path,
            Path(__file__).parent.parent / "config",
            PLATFORM_DIRS.user_config_path,
        ],
        description="Paths to look for configuration files",
        examples=[["/etc/xdg/feedwright", "/home/user/.config/feedwright"]],
    )

    http: HttpSettings = HttpSettings()
    generator: GeneratorSettings = GeneratorSettings()

    @field_validator("config_paths", mode="before")
    @classmethod
    def split_paths(cls, v: str | list[Path]) -> list[Path]:
        """Parse str path lists using the customary : delimiter"""
        if isinstance(v, str):
            return [Path(p) for p in v.split(":")]  # or ","
        return v


settings = Settings()
