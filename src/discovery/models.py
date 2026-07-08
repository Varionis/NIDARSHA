"""Strongly typed discovery domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class CrawlStrategy(str, Enum):
    """Supported crawl strategy values."""

    STATIC = "STATIC"
    PLAYWRIGHT = "PLAYWRIGHT"
    AUTO = "AUTO"


@dataclass(slots=True)
class Source:
    """A registry source entry that can be processed by discovery.

    Purpose:
        Capture normalized source metadata from the registry.
    Inputs:
        Registry fields such as source ID, URL, and strategy configuration.
    Outputs:
        A validated, typed source record.
    Assumptions:
        Disabled or inactive rows are filtered before model creation.
    """

    source_id: str
    name: str
    abbr: str | None
    authority_type: str | None
    owner: str | None
    url: str
    trust_level: str
    crawl_strategy: CrawlStrategy
    enabled: bool
    status: str
    active: bool
    raw_row: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class DiscoveryRun:
    """Metadata describing a single discovery execution."""

    run_id: str
    started_at: datetime
    status: str
    finished_at: datetime | None = None
    source_count: int = 0
    note: str | None = None

