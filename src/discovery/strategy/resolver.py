"""Crawl strategy resolution."""

from __future__ import annotations

from dataclasses import dataclass

from common.exceptions import StrategyResolutionError

from discovery.models import CrawlStrategy


@dataclass(slots=True)
class CrawlStrategyResolver:
    """Resolve the effective crawl strategy for a source."""

    def resolve(self, configured: CrawlStrategy | str) -> CrawlStrategy:
        """Return the effective crawl strategy.

        AUTO currently resolves to the configured strategy without detection.
        """

        if isinstance(configured, str):
            try:
                configured = CrawlStrategy[configured.upper()]
            except KeyError as exc:  # pragma: no cover - defensive branch
                raise StrategyResolutionError(f"Unsupported crawl strategy: {configured}") from exc

        if configured is CrawlStrategy.AUTO:
            return CrawlStrategy.AUTO
        return configured

