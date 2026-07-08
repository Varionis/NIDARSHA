"""Discovery manifest models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from common.utils import generate_manifest_id

from discovery.classification import ContentClass, classify_content
from discovery.models import CrawlStrategy


@dataclass(slots=True, frozen=True)
class DiscoveryManifest:
    """A canonical URL record produced by the discovery stage.

    Purpose:
        Represent a discovered URL in a deterministic, manifest-friendly form.
    Inputs:
        Source metadata, canonical URL, and optional link context.
    Outputs:
        A strongly typed record that can be serialized by downstream publishers.
    Assumptions:
        Manifest records are immutable after creation.
    """

    manifest_id: str
    run_id: str
    source_id: str
    raw_url: str
    canonical_url: str
    parent_manifest_id: str | None = None
    anchor_text: str | None = None
    url_type: str | None = None
    content_class: ContentClass = ContentClass.WEB_PAGE
    content_type: str | None = None
    depth: int = 0
    http_status: int | None = None
    crawl_strategy: CrawlStrategy = CrawlStrategy.STATIC
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    review_status: str = "PENDING"

    @classmethod
    def create(
        cls,
        run_id: str,
        source_id: str,
        raw_url: str,
        canonical_url: str,
        crawl_strategy: CrawlStrategy,
        depth: int = 0,
        content_type: str | None = None,
        content_class: ContentClass | None = None,
        **kwargs,
    ) -> "DiscoveryManifest":
        """Create a manifest record with a deterministic identifier."""

        manifest_id = generate_manifest_id(source_id, canonical_url)
        resolved_content_class = content_class or classify_content(canonical_url, content_type)
        return cls(
            manifest_id=manifest_id,
            run_id=run_id,
            source_id=source_id,
            raw_url=raw_url,
            canonical_url=canonical_url,
            crawl_strategy=crawl_strategy,
            depth=depth,
            content_type=content_type,
            content_class=resolved_content_class,
            **kwargs,
        )
