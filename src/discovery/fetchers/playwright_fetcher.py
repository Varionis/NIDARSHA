"""Playwright page fetching."""

from __future__ import annotations

from dataclasses import dataclass

from common.config.settings import DiscoverySettings
from common.exceptions import DiscoveryError

from .base import FetchedPage, PageFetcher


@dataclass(slots=True)
class PlaywrightPageFetcher(PageFetcher):
    """Fetch HTML pages by rendering them in Chromium via Playwright."""

    settings: DiscoverySettings
    headless: bool = True

    def fetch(self, url: str) -> FetchedPage:
        """Render a page and return the resulting HTML."""

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise DiscoveryError("Playwright is not installed.") from exc

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=self.headless)
                context = browser.new_context(user_agent=self.settings.user_agent)
                page = context.new_page()
                timeout_ms = self.settings.playwright_timeout_seconds * 1000
                response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_timeout(self.settings.playwright_render_wait_seconds * 1000)
                html = page.content()
                title = page.title()
                final_url = page.url
                status_code = response.status if response is not None else None
                content_type = response.headers.get("content-type") if response is not None else None
                context.close()
                browser.close()
        except Exception as exc:  # pragma: no cover - browser/runtime dependent
            raise DiscoveryError(f"Playwright fetch failed for {url}: {exc}") from exc

        return FetchedPage(
            requested_url=url,
            final_url=final_url,
            html=html,
            status_code=status_code,
            content_type=content_type,
            title=title,
        )
