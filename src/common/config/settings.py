"""Centralized application settings.

Purpose:
    Provide reusable configuration objects for discovery and future ingestion
    components without scattering constants through the codebase.
Inputs:
    Environment variables or explicit constructor values.
Outputs:
    Strongly typed settings objects with safe defaults.
Assumptions:
    Settings should remain lightweight and dependency-free in Phase 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os


@dataclass(slots=True)
class LoggingSettings:
    """Logging configuration shared across the application."""

    level: str = "INFO"
    log_dir: Path = Path("logs")
    file_name: str = "nidarsha.log"
    json_format: bool = True

    @property
    def file_path(self) -> Path:
        return self.log_dir / self.file_name


@dataclass(slots=True)
class DiscoverySettings:
    """Discovery-specific configuration defaults."""

    crawl_depth: int = 1
    retries: int = 3
    timeout_seconds: int = 30
    playwright_timeout_seconds: int = 90
    playwright_render_wait_seconds: int = 60
    user_agent: str = "NidarshaDiscoveryBot/0.1"
    prefer_https: bool = False
    manifest_output_dir: Path = Path("artifacts") / "discovery"
    supported_crawl_strategies: tuple[str, ...] = ("STATIC", "PLAYWRIGHT", "AUTO")
    supported_trust_levels: tuple[str, ...] = ("LOW", "MEDIUM", "HIGH", "OFFICIAL", "UNKNOWN")


@dataclass(slots=True)
class RegistrySettings:
    """Source registry configuration."""

    sheet_url: str | None = None
    discovery_sheet_url: str | None = None
    service_account_file: Path | None = None
    scopes: tuple[str, ...] = (
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    )


@dataclass(slots=True)
class AppConfig:
    """Top-level application configuration container."""

    logging: LoggingSettings = field(default_factory=LoggingSettings)
    discovery: DiscoverySettings = field(default_factory=DiscoverySettings)
    registry: RegistrySettings = field(default_factory=RegistrySettings)


def load_config() -> AppConfig:
    """Load application settings from environment variables.

    Purpose:
        Centralize configuration resolution for command-line tools and future
        runtime entry points.
    Inputs:
        Environment variables prefixed with `NIDARSHA_`.
    Outputs:
        A populated `AppConfig` instance.
    """

    logging_settings = LoggingSettings(
        level=os.getenv("NIDARSHA_LOG_LEVEL", "INFO"),
        log_dir=Path(os.getenv("NIDARSHA_LOG_DIR", "logs")),
        file_name=os.getenv("NIDARSHA_LOG_FILE", "nidarsha.log"),
        json_format=os.getenv("NIDARSHA_LOG_JSON", "true").strip().lower() in {"1", "true", "yes"},
    )

    discovery_settings = DiscoverySettings(
        crawl_depth=int(os.getenv("NIDARSHA_CRAWL_DEPTH", "1")),
        retries=int(os.getenv("NIDARSHA_RETRIES", "3")),
        timeout_seconds=int(os.getenv("NIDARSHA_TIMEOUT_SECONDS", "30")),
        playwright_timeout_seconds=int(os.getenv("NIDARSHA_PLAYWRIGHT_TIMEOUT_SECONDS", "90")),
        playwright_render_wait_seconds=int(os.getenv("NIDARSHA_PLAYWRIGHT_RENDER_WAIT_SECONDS", "60")),
        user_agent=os.getenv("NIDARSHA_USER_AGENT", "NidarshaDiscoveryBot/0.1"),
        prefer_https=os.getenv("NIDARSHA_PREFER_HTTPS", "false").strip().lower() in {"1", "true", "yes"},
        manifest_output_dir=Path(os.getenv("NIDARSHA_MANIFEST_OUTPUT_DIR", "artifacts/discovery")),
    )

    registry_scopes = tuple(
        scope.strip()
        for scope in os.getenv(
            "NIDARSHA_GOOGLE_SCOPES",
            "https://www.googleapis.com/auth/spreadsheets.readonly,https://www.googleapis.com/auth/drive.readonly",
        ).split(",")
        if scope.strip()
    )

    registry_settings = RegistrySettings(
        sheet_url=os.getenv("NIDARSHA_REGISTRY_SHEET_URL") or None,
        discovery_sheet_url=os.getenv("NIDARSHA_DISCOVERY_SHEET_URL") or None,
        service_account_file=Path(os.getenv("NIDARSHA_GOOGLE_SERVICE_ACCOUNT_FILE")) if os.getenv("NIDARSHA_GOOGLE_SERVICE_ACCOUNT_FILE") else None,
        scopes=registry_scopes,
    )

    return AppConfig(logging=logging_settings, discovery=discovery_settings, registry=registry_settings)
