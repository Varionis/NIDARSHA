"""URL canonicalization utilities.

Purpose:
    Normalize source and discovered URLs into a stable canonical form.
Inputs:
    Raw URLs and optional canonicalization settings.
Outputs:
    Canonical URLs suitable for deduplication and manifest generation.
Assumptions:
    URL normalization should be conservative and configurable.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlparse, urlunparse
import re

from common.config.settings import DiscoverySettings
from common.exceptions import CanonicalizationError

_INDEX_SUFFIXES = ("/index.html", "/index.htm", "/index.php", "/default.aspx", "/default.html")


@dataclass(slots=True)
class URLCanonicalizer:
    """Canonicalize URLs using a small, extensible rule set."""

    prefer_https: bool = False

    @classmethod
    def from_settings(cls, settings: DiscoverySettings) -> "URLCanonicalizer":
        return cls(prefer_https=settings.prefer_https)

    def canonicalize(self, url: str) -> str:
        """Return a stable canonical URL string."""

        if not url or not url.strip():
            raise CanonicalizationError("URL cannot be empty.")

        candidate = self._ensure_scheme(url.strip())
        parsed = urlparse(candidate)
        if not parsed.netloc:
            raise CanonicalizationError(f"Invalid URL: {url!r}")

        scheme = parsed.scheme.lower()
        if self.prefer_https and scheme == "http":
            scheme = "https"

        netloc = parsed.netloc.lower()
        netloc = self._remove_default_port(scheme, netloc)

        path = re.sub(r"/{2,}", "/", parsed.path or "/")
        path = self._normalize_index_path(path)
        path = self._normalize_trailing_slash(path)

        query = self._normalize_query(parsed.query)

        normalized = parsed._replace(
            scheme=scheme,
            netloc=netloc,
            path=path,
            params="",
            query=query,
            fragment="",
        )
        return urlunparse(normalized)

    def _ensure_scheme(self, url: str) -> str:
        if "://" in url:
            return url
        return f"https://{url.lstrip('/')}"

    def _remove_default_port(self, scheme: str, netloc: str) -> str:
        if scheme == "http" and netloc.endswith(":80"):
            return netloc[:-3]
        if scheme == "https" and netloc.endswith(":443"):
            return netloc[:-4]
        return netloc

    def _normalize_index_path(self, path: str) -> str:
        lowered = path.lower()
        for suffix in _INDEX_SUFFIXES:
            if lowered.endswith(suffix):
                return path[: -len(suffix)] or "/"
        return path

    def _normalize_trailing_slash(self, path: str) -> str:
        if not path:
            return "/"
        if path != "/" and path.endswith("/"):
            return path.rstrip("/")
        return path

    def _normalize_query(self, query: str) -> str:
        if not query:
            return ""
        pairs = parse_qsl(query, keep_blank_values=True)
        if not pairs:
            return ""
        return "&".join(f"{key}={value}" if value else key for key, value in sorted(pairs))

