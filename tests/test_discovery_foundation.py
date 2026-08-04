from __future__ import annotations

import sys
from pathlib import Path
import unittest


PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from common.exceptions import RegistryValidationError, SourceValidationError
from common.config.settings import AppConfig, DiscoverySettings
from common.utils import generate_manifest_id
from discovery.crawler import DiscoveryCrawler
from discovery.canonicalizer import URLCanonicalizer
from discovery.classification import ContentClass, classify_content
from discovery.fetchers.base import FetchedPage
from discovery.extractors import LinkExtractor
from discovery.manifest.models import DiscoveryManifest
from discovery.models import CrawlStrategy
from discovery.registry.reader import RegistryReader
from discovery.publisher.google_sheets import GoogleSheetsManifestPublisher
from discovery.strategy.resolver import CrawlStrategyResolver
from discovery.validator.source_validator import SourceValidator
from discovery.models import Source


class DiscoveryFoundationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = DiscoverySettings()
        self.canonicalizer = URLCanonicalizer.from_settings(self.settings)
        self.validator = SourceValidator(self.settings, self.canonicalizer)

    def test_url_canonicalization_normalizes_common_noise(self) -> None:
        canonical = self.canonicalizer.canonicalize("HTTP://Example.com//foo/index.html#section")
        self.assertEqual(canonical, "http://example.com/foo")

    def test_manifest_identifier_is_deterministic(self) -> None:
        first = generate_manifest_id("source-1", "https://example.com/policies")
        second = generate_manifest_id("source-1", "https://example.com/policies")
        self.assertEqual(first, second)

    def test_manifest_creation_uses_deterministic_identifier(self) -> None:
        manifest = DiscoveryManifest.create(
            run_id="run-1",
            source_id="source-1",
            raw_url="https://example.com",
            canonical_url="https://example.com",
            crawl_strategy=CrawlStrategy.STATIC,
        )
        self.assertEqual(manifest.manifest_id, generate_manifest_id("source-1", "https://example.com"))

    def test_content_classifier_detects_pdf_and_web_page(self) -> None:
        self.assertEqual(classify_content("https://example.com/report.pdf"), ContentClass.PDF)
        self.assertEqual(classify_content("https://example.com/about"), ContentClass.WEB_PAGE)
        self.assertEqual(classify_content("https://example.com/policy.docx"), ContentClass.DOCUMENT)
        self.assertEqual(classify_content("https://example.com/image.jpg"), ContentClass.IMAGE)
        self.assertEqual(classify_content("https://example.com/video.mp4"), ContentClass.VIDEO)
        self.assertEqual(classify_content("https://example.com/file.zip"), ContentClass.OTHER)

    def test_strategy_resolver_returns_auto_as_configured(self) -> None:
        resolver = CrawlStrategyResolver()
        self.assertEqual(resolver.resolve("AUTO"), CrawlStrategy.AUTO)

    def test_registry_reader_filters_disabled_rows(self) -> None:
        rows = [
            {
                "source_id": "source-1",
                "name": "Example",
                "abbr": "EX",
                "authority_type": "Ministry",
                "owner": "Team",
                "url": "https://example.com",
                "trust_level": "HIGH",
                "crawl_strategy": "STATIC",
                "enabled": "TRUE",
                "status": "active",
                "active": "TRUE",
            },
            {
                "source_id": "source-2",
                "name": "Disabled",
                "abbr": "DS",
                "authority_type": "Ministry",
                "owner": "Team",
                "url": "https://disabled.example.com",
                "trust_level": "LOW",
                "crawl_strategy": "STATIC",
                "enabled": "FALSE",
                "status": "inactive",
                "active": "FALSE",
            },
        ]
        reader = RegistryReader(rows=rows, settings=self.settings)
        sources = reader.read()
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].source_id, "source-1")

    def test_registry_reader_rejects_duplicate_source_ids(self) -> None:
        rows = [
            {
                "source_id": "source-1",
                "name": "Example",
                "abbr": "EX",
                "authority_type": "Ministry",
                "owner": "Team",
                "url": "https://example.com",
                "trust_level": "HIGH",
                "crawl_strategy": "STATIC",
                "enabled": "TRUE",
                "status": "active",
                "active": "TRUE",
            },
            {
                "source_id": "source-1",
                "name": "Example Two",
                "abbr": "EX2",
                "authority_type": "Ministry",
                "owner": "Team",
                "url": "https://example.org",
                "trust_level": "HIGH",
                "crawl_strategy": "STATIC",
                "enabled": "TRUE",
                "status": "active",
                "active": "TRUE",
            },
        ]
        reader = RegistryReader(rows=rows, settings=self.settings)
        with self.assertRaises(RegistryValidationError):
            reader.read()

    def test_source_validator_rejects_invalid_trust_level(self) -> None:
        with self.assertRaises(SourceValidationError):
            self.validator.validate_row(
                {
                    "source_id": "source-1",
                    "name": "Example",
                    "abbr": "EX",
                    "authority_type": "Ministry",
                    "owner": "Team",
                    "url": "https://example.com",
                    "trust_level": "UNSUPPORTED",
                    "crawl_strategy": "STATIC",
                    "enabled": "TRUE",
                    "status": "active",
                    "active": "TRUE",
                }
            )

    def test_link_extractor_filters_external_and_duplicate_links(self) -> None:
        extractor = LinkExtractor()
        html = """
        <html>
            <body>
                <a href="/alpha">Alpha</a>
                <a href="/alpha">Alpha duplicate</a>
                <a href="https://example.com/beta">Beta</a>
                <a href="https://external.example.org/">External</a>
                <a href="javascript:void(0)">Ignore</a>
            </body>
        </html>
        """

        links = extractor.extract("https://example.com", html, allowed_netlocs={"example.com"})

        self.assertEqual([link.absolute_url for link in links], ["https://example.com/alpha", "https://example.com/beta"])

    def test_static_crawler_builds_manifests_for_discovered_links(self) -> None:
        config = AppConfig(discovery=DiscoverySettings(crawl_depth=1))
        source = Source(
            source_id="source-1",
            name="Example",
            abbr=None,
            authority_type=None,
            owner=None,
            url="https://example.com",
            trust_level="OFFICIAL",
            crawl_strategy=CrawlStrategy.STATIC,
            enabled=True,
            status="active",
            active=True,
        )

        root_html = """
        <html>
            <body>
                <a href="/child">Child</a>
                <a href="https://external.example.org/">External</a>
            </body>
        </html>
        """

        class FakeFetcher:
            def __init__(self, responses: dict[str, FetchedPage]) -> None:
                self.responses = responses

            def fetch(self, url: str) -> FetchedPage:
                return self.responses[url]

        fetcher = FakeFetcher(
            {
                "https://example.com/": FetchedPage(
                    requested_url="https://example.com/",
                    final_url="https://example.com/",
                    html=root_html,
                    status_code=200,
                    content_type="text/html",
                    title="Root",
                ),
                "https://example.com/child": FetchedPage(
                    requested_url="https://example.com/child",
                    final_url="https://example.com/child",
                    html="<html><body></body></html>",
                    status_code=200,
                    content_type="text/html",
                    title="Child",
                ),
            }
        )

        crawler = DiscoveryCrawler(config=config, logger=type("Logger", (), {"info": lambda self, *args, **kwargs: None})(), fetchers={CrawlStrategy.STATIC: fetcher})
        with self.__class__._run_context() as run:
            manifests = crawler.crawl_source(run, source)

        self.assertEqual(len(manifests), 2)
        self.assertEqual(manifests[0].canonical_url, "https://example.com/")
        self.assertEqual(manifests[0].content_class, ContentClass.WEB_PAGE)
        self.assertEqual(manifests[1].canonical_url, "https://example.com/child")
        self.assertEqual(manifests[1].content_class, ContentClass.WEB_PAGE)
        self.assertEqual(manifests[1].parent_manifest_id, manifests[0].manifest_id)

    def test_playwright_crawler_uses_injected_fetcher(self) -> None:
        config = AppConfig(discovery=DiscoverySettings(crawl_depth=1))
        source = Source(
            source_id="source-2",
            name="Example PW",
            abbr=None,
            authority_type=None,
            owner=None,
            url="https://example.org",
            trust_level="OFFICIAL",
            crawl_strategy=CrawlStrategy.PLAYWRIGHT,
            enabled=True,
            status="active",
            active=True,
        )

        class FakeFetcher:
            def __init__(self, responses: dict[str, FetchedPage]) -> None:
                self.responses = responses

            def fetch(self, url: str) -> FetchedPage:
                return self.responses[url]

        fetcher = FakeFetcher(
            {
                "https://example.org/": FetchedPage(
                    requested_url="https://example.org/",
                    final_url="https://example.org/",
                    html="<html><body><a href='/child'>Child</a></body></html>",
                    status_code=200,
                    content_type="text/html",
                    title="Root",
                ),
                "https://example.org/child": FetchedPage(
                    requested_url="https://example.org/child",
                    final_url="https://example.org/child",
                    html="<html><body></body></html>",
                    status_code=200,
                    content_type="text/html",
                    title="Child",
                ),
            }
        )

        crawler = DiscoveryCrawler(config=config, logger=type("Logger", (), {"info": lambda self, *args, **kwargs: None})(), fetchers={CrawlStrategy.PLAYWRIGHT: fetcher})
        with self.__class__._run_context() as run:
            manifests = crawler.crawl_source(run, source)

        self.assertEqual(len(manifests), 2)
        self.assertEqual(manifests[0].crawl_strategy, CrawlStrategy.PLAYWRIGHT)
        self.assertEqual(manifests[0].content_class, ContentClass.WEB_PAGE)
        self.assertEqual(manifests[1].canonical_url, "https://example.org/child")

    def test_google_sheets_dedupes_by_canonical_url_only(self) -> None:
        class FakeWorksheet:
            def get_all_values(self) -> list[list[str]]:
                return [
                    [
                        "manifest_id",
                        "run_id",
                        "source_id",
                        "raw_url",
                        "canonical_url",
                        "review_status",
                        "extra_column",
                    ],
                    [
                        "m1",
                        "r1",
                        "source-1",
                        "https://example.com/page",
                        "https://example.com/page",
                        "PENDING",
                        "old",
                    ],
                ]

        publisher = GoogleSheetsManifestPublisher.__new__(GoogleSheetsManifestPublisher)
        existing = publisher._load_existing_canonical_urls(FakeWorksheet())
        self.assertEqual(existing, {"https://example.com/page"})

    def test_google_sheets_rows_include_content_class(self) -> None:
        publisher = GoogleSheetsManifestPublisher.__new__(GoogleSheetsManifestPublisher)
        manifest = DiscoveryManifest.create(
            run_id="run-1",
            source_id="source-1",
            raw_url="https://example.com/report.pdf",
            canonical_url="https://example.com/report.pdf",
            crawl_strategy=CrawlStrategy.STATIC,
            content_type="application/pdf",
            content_class=ContentClass.PDF,
        )

        row = publisher._manifest_to_row(manifest)
        self.assertIn("PDF", row)
        self.assertEqual(
            publisher._sheet_row_keys(),
            ("source_id", "raw_url", "canonical_url", "content_class", "discovered_at", "review_status"),
        )
        self.assertEqual(len(row), 6)

    @staticmethod
    def _run_context():
        from common.tracing import trace_run

        return trace_run()


if __name__ == "__main__":
    unittest.main()
