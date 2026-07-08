"""Discovery Engine orchestration.

Purpose:
    Coordinate registry reading, validation, canonicalization, and manifest
    preparation without implementing crawling.
Inputs:
    Registry reader, validators, canonicalizer, and configuration objects.
Outputs:
    Validated sources and discovery run metadata.
Assumptions:
    Crawling and publishing are deferred to later phases or external adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Iterator

from common.config.settings import AppConfig, load_config
from common.logging import StructuredLogger, get_logger
from common.tracing import RunContext, trace_run

from discovery.canonicalizer import URLCanonicalizer
from discovery.crawler import DiscoveryCrawler
from discovery.manifest.models import DiscoveryManifest
from discovery.registry.reader import RegistryReader
from discovery.models import DiscoveryRun, Source


@dataclass(slots=True)
class DiscoveryEngine:
    """Coordinate the Phase 1 discovery foundation.

    Purpose:
        Provide a reusable orchestration layer for future discovery workflows.
    Inputs:
        Registry reader and optional configuration.
    Outputs:
        Validated sources, canonicalized URLs, and manifest-ready records.
    Assumptions:
        The engine stops short of crawling and content extraction.
    """

    registry_reader: RegistryReader
    config: AppConfig | None = None
    logger: StructuredLogger | None = None
    _canonicalizer: URLCanonicalizer = field(init=False, repr=False)
    _crawler: DiscoveryCrawler = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.config is None:
            self.config = load_config()
        if self.logger is None:
            self.logger = get_logger("discovery.engine", self.config.logging)

        self._canonicalizer = URLCanonicalizer.from_settings(self.config.discovery)
        self._crawler = DiscoveryCrawler(self.config, self.logger)

    def create_run(self) -> DiscoveryRun:
        """Create a new discovery run record."""

        return DiscoveryRun(
            run_id=create_run_id(),
            started_at=datetime.now(timezone.utc),
            status="INITIALIZED",
        )

    @contextmanager
    def run_context(self) -> Iterator[RunContext]:
        """Activate a run-scoped tracing context for discovery work."""

        with trace_run() as run:
            yield run

    def load_sources(self) -> list[Source]:
        """Read and validate registry sources."""

        self.logger.info("Loading registry sources")
        rows = self.registry_reader.read()
        self.logger.info("Loaded sources", source_count=len(rows))
        return list(rows)

    def discover(self) -> tuple[DiscoveryRun, list[DiscoveryManifest]]:
        """Execute discovery for all enabled sources."""

        with self.run_context() as context:
            run = DiscoveryRun(
                run_id=context.run_id,
                started_at=context.started_at,
                status="INITIALIZED",
            )
            sources = self.load_sources()
            manifests: list[DiscoveryManifest] = []
            for source in sources:
                manifests.extend(self._crawler.crawl_source(context, source))
        run.status = "COMPLETED"
        run.source_count = len(sources)
        run.finished_at = datetime.now(timezone.utc)
        return run, manifests
