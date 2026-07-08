"""Source validation for registry rows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from common.config.settings import DiscoverySettings
from common.exceptions import SourceValidationError

from discovery.canonicalizer import URLCanonicalizer
from discovery.models import CrawlStrategy, Source


@dataclass(slots=True)
class SourceValidator:
    """Validate registry rows and convert them into `Source` records."""

    settings: DiscoverySettings
    canonicalizer: URLCanonicalizer

    def validate_row(self, row: dict[str, Any]) -> Source:
        """Validate a registry row and return a typed source model."""

        normalized = {key.strip().lower(): self._normalize_value(value) for key, value in row.items()}
        self._validate_required_fields(normalized)

        source_id = self._require_text(normalized, "source_id")
        name = self._require_text(normalized, "name")
        url = self._canonicalize_url(self._require_text(normalized, "url"))
        crawl_strategy = self._parse_strategy(self._require_text(normalized, "crawl_strategy"))
        trust_level = self._parse_trust_level(self._require_text(normalized, "trust_level"))

        return Source(
            source_id=source_id,
            name=name,
            abbr=self._optional_text(normalized, "abbr"),
            authority_type=self._optional_text(normalized, "authority_type"),
            owner=self._optional_text(normalized, "owner"),
            url=url,
            trust_level=trust_level,
            crawl_strategy=crawl_strategy,
            enabled=self._parse_bool(normalized.get("enabled")),
            status=self._require_text(normalized, "status"),
            active=self._parse_bool(normalized.get("active")),
            raw_row={k: "" if v is None else str(v) for k, v in row.items()},
        )

    def _validate_required_fields(self, row: dict[str, Any]) -> None:
        required = ["source_id", "name", "url", "trust_level", "crawl_strategy", "enabled", "status", "active"]
        missing = [field for field in required if field not in row or row.get(field) is None or str(row.get(field)).strip() == ""]
        if missing:
            raise SourceValidationError(f"Missing required source fields: {', '.join(missing)}")

    def _canonicalize_url(self, url: str) -> str:
        try:
            canonical = self.canonicalizer.canonicalize(url)
        except Exception as exc:  # pragma: no cover - defensive branch
            raise SourceValidationError(f"Invalid source URL: {url!r}") from exc
        parsed = urlparse(canonical)
        if not parsed.scheme or not parsed.netloc:
            raise SourceValidationError(f"Invalid source URL: {url!r}")
        return canonical

    def _parse_strategy(self, value: str) -> CrawlStrategy:
        try:
            strategy = CrawlStrategy[value.upper()]
        except KeyError as exc:
            raise SourceValidationError(f"Unsupported crawl strategy: {value}") from exc
        if strategy.value not in self.settings.supported_crawl_strategies:
            raise SourceValidationError(f"Unsupported crawl strategy: {value}")
        return strategy

    def _parse_trust_level(self, value: str) -> str:
        trust_level = value.strip().upper()
        if trust_level not in self.settings.supported_trust_levels:
            raise SourceValidationError(f"Unsupported trust level: {value}")
        return trust_level

    def _parse_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
        raise SourceValidationError(f"Invalid boolean value: {value!r}")

    def _require_text(self, row: dict[str, Any], key: str) -> str:
        value = row.get(key)
        if value is None:
            raise SourceValidationError(f"Missing required field: {key}")
        text = str(value).strip()
        if not text:
            raise SourceValidationError(f"Missing required field: {key}")
        return text

    def _optional_text(self, row: dict[str, Any], key: str) -> str | None:
        value = row.get(key)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _normalize_value(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        return value
