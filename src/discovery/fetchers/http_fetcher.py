"""Static HTTP page fetching."""

from __future__ import annotations

from dataclasses import dataclass

import requests

from common.config.settings import DiscoverySettings
from common.exceptions import DiscoveryError

from .base import FetchedPage, PageFetcher


@dataclass(slots=True)
class HTTPPageFetcher(PageFetcher):
    """Fetch HTML pages with plain HTTP requests."""

    settings: DiscoverySettings

    def __post_init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self.settings.user_agent})

    def fetch(self, url: str) -> FetchedPage:
        """Fetch a page over HTTP and capture the response body."""

        try:
            response = self._session.get(url, timeout=self.settings.timeout_seconds, allow_redirects=True)
        except requests.RequestException as exc:
            raise DiscoveryError(f"Static fetch failed for {url}: {exc}") from exc

        content_type = response.headers.get("Content-Type")
        return FetchedPage(
            requested_url=url,
            final_url=response.url,
            html=response.text,
            status_code=response.status_code,
            content_type=content_type,
        )

