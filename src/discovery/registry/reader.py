"""Registry reader for source discovery inputs.

Purpose:
    Read source registry rows, validate required structure, ignore disabled
    rows, and convert them into typed source models.
Inputs:
    A Google Sheets URL, CSV text source, or an in-memory row collection.
Outputs:
    Validated `Source` objects ready for discovery processing.
Assumptions:
    Registry content is tabular and contains a single header row.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import csv
from io import StringIO
import re
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

import gspread
import requests
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError

from common.config.settings import DiscoverySettings, RegistrySettings
from common.exceptions import RegistryError, RegistryValidationError
from common.logging import StructuredLogger, get_logger

from discovery.canonicalizer import URLCanonicalizer
from discovery.models import Source
from discovery.validator.source_validator import SourceValidator

_REQUIRED_COLUMNS = {
    "source_id",
    "name",
    "abbr",
    "authority_type",
    "owner",
    "url",
    "trust_level",
    "crawl_strategy",
    "enabled",
    "status",
    "active",
}


@dataclass(slots=True)
class RegistryReader:
    """Load and validate source registry rows."""

    sheet_url: str | None = None
    rows: Sequence[Mapping[str, Any]] | None = None
    http_get: Callable[..., Any] = requests.get
    settings: DiscoverySettings = field(default_factory=DiscoverySettings)
    registry_settings: RegistrySettings = field(default_factory=RegistrySettings)
    logger: StructuredLogger | None = None
    _canonicalizer: URLCanonicalizer = field(init=False, repr=False)
    _validator: SourceValidator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.logger is None:
            self.logger = get_logger("discovery.registry", None)
        self._canonicalizer = URLCanonicalizer.from_settings(self.settings)
        self._validator = SourceValidator(self.settings, self._canonicalizer)

    def read(self) -> list[Source]:
        """Return validated sources from the configured registry input."""

        raw_rows = self.rows if self.rows is not None else self._read_sheet_rows()
        if not raw_rows:
            return []

        self._validate_columns(raw_rows[0].keys())

        sources: list[Source] = []
        seen_ids: set[str] = set()
        for row in raw_rows:
            source = self._validator.validate_row(row)
            if not source.enabled or source.status.lower() != "active" or not source.active:
                continue
            if source.source_id in seen_ids:
                raise RegistryValidationError(f"Duplicate source_id detected: {source.source_id}")
            seen_ids.add(source.source_id)
            sources.append(source)

        self.logger.info("Registry rows loaded", row_count=len(raw_rows), source_count=len(sources))
        return sources

    def _validate_columns(self, columns: Sequence[str]) -> None:
        missing = sorted(_REQUIRED_COLUMNS - set(columns))
        if missing:
            raise RegistryValidationError(f"Registry is missing required columns: {', '.join(missing)}")

    def _read_sheet_rows(self) -> list[dict[str, Any]]:
        sheet_url = self.sheet_url or self.registry_settings.sheet_url
        if not sheet_url:
            raise RegistryError("No registry input was configured.")

        if self._can_use_authenticated_api():
            try:
                return self._read_authenticated_rows(sheet_url)
            except (PermissionError, APIError, RegistryError):
                self.logger.warning("Authenticated Google Sheets access failed; falling back to CSV export")

        response = self.http_get(self._as_csv_export_url(sheet_url), timeout=30)
        response.raise_for_status()
        reader = csv.DictReader(StringIO(response.text))
        return [dict(row) for row in reader]

    def _can_use_authenticated_api(self) -> bool:
        return bool(self.registry_settings.service_account_file)

    def _read_authenticated_rows(self, sheet_url: str) -> list[dict[str, Any]]:
        service_account_file = self.registry_settings.service_account_file
        if service_account_file is None:
            raise RegistryError("Authenticated registry access requested without credentials.")
        if not Path(service_account_file).exists():
            raise RegistryError(f"Service account file not found: {service_account_file}")

        credentials = Credentials.from_service_account_file(
            str(service_account_file),
            scopes=list(self.registry_settings.scopes),
        )
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_url(sheet_url)
        worksheet = self._select_worksheet(spreadsheet, sheet_url)
        return worksheet.get_all_records(default_blank="")

    def _select_worksheet(self, spreadsheet: gspread.Spreadsheet, sheet_url: str) -> gspread.Worksheet:
        gid = self._extract_gid(sheet_url)
        if gid is not None:
            worksheet = spreadsheet.get_worksheet_by_id(gid)
            if worksheet is None:
                raise RegistryError(f"Worksheet with gid {gid} was not found.")
            return worksheet
        return spreadsheet.sheet1

    def _extract_gid(self, url: str) -> int | None:
        parsed = urlparse(url)
        query_gid = parse_qs(parsed.query).get("gid", [None])[0]
        if query_gid and query_gid.isdigit():
            return int(query_gid)
        fragment_match = re.search(r"gid=(\d+)", parsed.fragment)
        if fragment_match:
            return int(fragment_match.group(1))
        return None

    def _as_csv_export_url(self, url: str) -> str:
        if "output=csv" in url or url.endswith(".csv"):
            return url
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
        if match:
            sheet_id = match.group(1)
            gid = self._extract_gid(url)
            gid_value = str(gid) if gid is not None else "0"
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_value}"
        return url
