"""Page fetching adapters for discovery crawlers."""

from .base import FetchedPage, PageFetcher
from .http_fetcher import HTTPPageFetcher
from .playwright_fetcher import PlaywrightPageFetcher

__all__ = ["FetchedPage", "PageFetcher", "HTTPPageFetcher", "PlaywrightPageFetcher"]

