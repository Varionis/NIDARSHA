"""Page fetcher contracts."""

from __future__ import annotations

from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass(slots=True)
class FetchedPage:
    """Fetched HTML page metadata."""

    requested_url: str
    final_url: str
    html: str
    status_code: int | None = None
    content_type: str | None = None
    title: str | None = None


class PageFetcher(ABC):
    """Abstract page fetching contract."""

    @abstractmethod
    def fetch(self, url: str) -> FetchedPage:
        """Fetch a page and return rendered HTML plus response metadata."""

