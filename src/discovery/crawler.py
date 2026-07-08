"""Discovery crawling orchestration."""

from __future__ import annotations

from urllib.parse import urlparse

from common.config.settings import AppConfig
from common.exceptions import DiscoveryError
from common.logging import StructuredLogger, get_logger
from common.tracing import RunContext

from discovery.canonicalizer import URLCanonicalizer
from discovery.classification import classify_content
from discovery.extractors import LinkExtractor
from discovery.fetchers import HTTPPageFetcher, PlaywrightPageFetcher, PageFetcher
from discovery.manifest.models import DiscoveryManifest
from discovery.models import CrawlStrategy, Source
from discovery.strategy.resolver import CrawlStrategyResolver


class DiscoveryCrawler:
    """Crawl source landing pages and emit discovery manifests."""

    def __init__(
        self,
        config: AppConfig,
        logger: StructuredLogger | None = None,
        fetchers: dict[CrawlStrategy, PageFetcher] | None = None,
        link_extractor: LinkExtractor | None = None,
    ) -> None:
        self.config = config
        self.logger = logger or get_logger("discovery.crawler", config.logging)
        self._canonicalizer = URLCanonicalizer.from_settings(config.discovery)
        self._strategy_resolver = CrawlStrategyResolver()
        self._link_extractor = link_extractor or LinkExtractor()
        self._fetchers: dict[CrawlStrategy, PageFetcher] = fetchers or {
            CrawlStrategy.STATIC: HTTPPageFetcher(config.discovery),
            CrawlStrategy.PLAYWRIGHT: PlaywrightPageFetcher(config.discovery, headless=True),
        }

    def crawl_source(self, run: RunContext, source: Source) -> list[DiscoveryManifest]:
        """Crawl a single source landing page and return discovery manifests."""

        strategy = self._strategy_resolver.resolve(source.crawl_strategy)
        fetcher = self._fetchers.get(strategy)
        if fetcher is None:
            raise DiscoveryError(f"Unsupported crawl strategy: {source.crawl_strategy}")

        root_url = self._canonicalizer.canonicalize(source.url)
        manifests: list[DiscoveryManifest] = []

        page = fetcher.fetch(root_url)
        final_canonical_url = self._canonicalizer.canonicalize(page.final_url)

        root_manifest = DiscoveryManifest.create(
            run_id=run.run_id,
            source_id=source.source_id,
            raw_url=root_url,
            canonical_url=final_canonical_url,
            parent_manifest_id=None,
            anchor_text=None,
            depth=0,
            http_status=page.status_code,
            content_type=page.content_type,
            crawl_strategy=strategy,
            url_type="LANDING_PAGE",
            content_class=classify_content(final_canonical_url, page.content_type),
        )
        manifests.append(root_manifest)

        if self.config.discovery.crawl_depth < 1:
            return manifests

        allowed_netlocs = self._allowed_netlocs(source.url) if strategy is CrawlStrategy.STATIC else None
        extracted_links = self._link_extractor.extract(
            base_url=page.final_url,
            html=page.html,
            allowed_netlocs=allowed_netlocs,
        )
        self.logger.info(
            "Extracted links",
            source_id=source.source_id,
            current_depth=0,
            link_count=len(extracted_links),
        )
        seen_children: set[str] = set()
        for link in extracted_links:
            child_canonical_url = self._canonicalizer.canonicalize(link.absolute_url)
            if child_canonical_url in seen_children:
                continue
            seen_children.add(child_canonical_url)
            manifests.append(
                DiscoveryManifest.create(
                    run_id=run.run_id,
                    source_id=source.source_id,
                    raw_url=link.raw_url,
                    canonical_url=child_canonical_url,
                    parent_manifest_id=root_manifest.manifest_id,
                    anchor_text=link.anchor_text,
                    depth=1,
                    http_status=None,
                    content_type=None,
                    crawl_strategy=strategy,
                    url_type="LINK",
                    content_class=classify_content(child_canonical_url, None),
                )
            )

        return manifests

    def _allowed_netlocs(self, source_url: str) -> set[str]:
        parsed = urlparse(source_url)
        netlocs = {parsed.netloc.lower()}
        if parsed.netloc.lower().startswith("www."):
            netlocs.add(parsed.netloc.lower()[4:])
        else:
            netlocs.add(f"www.{parsed.netloc.lower()}")
        return {netloc for netloc in netlocs if netloc}
