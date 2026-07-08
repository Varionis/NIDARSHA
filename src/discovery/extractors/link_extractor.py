"""HTML link extraction utilities.

Purpose:
    Extract normalized link targets and anchor text from rendered HTML.
Inputs:
    A base URL and HTML document.
Outputs:
    Typed link records ready for discovery crawling.
Assumptions:
    Discovery focuses on anchor links and ignores non-HTTP schemes.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


@dataclass(slots=True)
class DiscoveredLink:
    """A link discovered on a page."""

    raw_url: str
    absolute_url: str
    anchor_text: str | None = None


class LinkExtractor:
    """Extract links from HTML documents."""

    def extract(self, base_url: str, html: str, allowed_netlocs: set[str] | None = None) -> list[DiscoveredLink]:
        """Return normalized links discovered in the HTML document."""

        soup = BeautifulSoup(html, "html.parser")
        links: list[DiscoveredLink] = []
        seen: set[str] = set()

        for tag in soup.find_all("a", href=True):
            href = str(tag["href"]).strip()
            if not href:
                continue

            lowered = href.lower()
            if lowered.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue

            absolute_url = urljoin(base_url, href)
            parsed = urlparse(absolute_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                continue

            if allowed_netlocs and parsed.netloc not in allowed_netlocs:
                continue

            if absolute_url in seen:
                continue

            seen.add(absolute_url)
            anchor_text = " ".join(tag.get_text(" ", strip=True).split()) or None
            links.append(DiscoveredLink(raw_url=href, absolute_url=absolute_url, anchor_text=anchor_text))

        return links

