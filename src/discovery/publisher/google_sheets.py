"""Google Sheets manifest publisher.

Purpose:
    Persist discovery manifests into a Google Sheet for operational review and
    downstream handoff.
Inputs:
    Discovery manifests, a Google Sheets URL, and service-account credentials.
Outputs:
    Appended rows in the configured Google Sheet.
Assumptions:
    The discovery sheet already exists and is shared with the service account.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict
from datetime import datetime
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import gspread
from google.oauth2.service_account import Credentials

from common.config.settings import RegistrySettings
from common.exceptions import ManifestError
from discovery.classification import ContentClass

from discovery.manifest.models import DiscoveryManifest

from .base import ManifestPublisher


class GoogleSheetsManifestPublisher(ManifestPublisher):
    """Append discovery manifests to a Google Sheets worksheet."""

    def __init__(self, sheet_url: str, registry_settings: RegistrySettings, worksheet_gid: int | None = None) -> None:
        self.sheet_url = sheet_url
        self.registry_settings = registry_settings
        self.worksheet_gid = worksheet_gid

    def publish(self, manifests: Iterable[DiscoveryManifest]) -> int:
        """Append manifests to the configured Google Sheet and return the row count."""

        manifest_list = list(manifests)
        if not manifest_list:
            return 0

        service_account_file = self.registry_settings.service_account_file
        if service_account_file is None:
            raise ManifestError("Google Sheets publishing requires a service account file.")
        if not Path(service_account_file).exists():
            raise ManifestError(f"Service account file not found: {service_account_file}")

        credentials = Credentials.from_service_account_file(
            str(service_account_file),
            scopes=list(self.registry_settings.scopes),
        )
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_url(self.sheet_url)
        worksheet = self._select_worksheet(spreadsheet)

        self._ensure_header(worksheet)
        existing_canonical_urls = self._load_existing_canonical_urls(worksheet)
        new_manifests = [manifest for manifest in manifest_list if manifest.canonical_url not in existing_canonical_urls]
        if not new_manifests:
            return 0

        rows = [self._manifest_to_row(manifest) for manifest in new_manifests]
        worksheet.append_rows(rows, value_input_option="RAW")
        return len(rows)

    def _select_worksheet(self, spreadsheet: gspread.Spreadsheet) -> gspread.Worksheet:
        if self.worksheet_gid is not None:
            worksheet = spreadsheet.get_worksheet_by_id(self.worksheet_gid)
            if worksheet is None:
                raise ManifestError(f"Worksheet with gid {self.worksheet_gid} was not found.")
            return worksheet

        parsed_gid = self._extract_gid(self.sheet_url)
        if parsed_gid is not None:
            worksheet = spreadsheet.get_worksheet_by_id(parsed_gid)
            if worksheet is None:
                raise ManifestError(f"Worksheet with gid {parsed_gid} was not found.")
            return worksheet

        return spreadsheet.sheet1

    def _ensure_header(self, worksheet: gspread.Worksheet) -> None:
        expected_header = list(self._sheet_row_keys())
        current_values = worksheet.row_values(1)
        if current_values:
            if current_values[: len(expected_header)] != expected_header:
                worksheet.update("A1", [expected_header])
            return
        worksheet.insert_row(expected_header, 1)

    def _load_existing_canonical_urls(self, worksheet: gspread.Worksheet) -> set[str]:
        values = worksheet.get_all_values()
        if not values:
            return set()

        header = values[0]
        try:
            canonical_url_index = header.index("canonical_url")
        except ValueError:
            return set()

        existing: set[str] = set()
        for row in values[1:]:
            if canonical_url_index < len(row) and row[canonical_url_index].strip():
                existing.add(row[canonical_url_index].strip())
        return existing

    def _manifest_to_row(self, manifest: DiscoveryManifest) -> list[Any]:
        data = asdict(manifest)
        data["crawl_strategy"] = manifest.crawl_strategy.value
        data["content_class"] = self._enum_value(manifest.content_class)
        data["discovered_at"] = manifest.discovered_at.isoformat()
        return [self._stringify(data[key]) for key in self._sheet_row_keys()]

    def _sheet_row_keys(self) -> tuple[str, ...]:
        return (
            "source_id",
            "raw_url",
            "canonical_url",
            "content_class",
            "discovered_at",
            "review_status",
        )

    def _stringify(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def _enum_value(self, value: Any) -> Any:
        if isinstance(value, ContentClass):
            return value.value
        return value

    def _extract_gid(self, url: str) -> int | None:
        parsed = urlparse(url)
        query_gid = parse_qs(parsed.query).get("gid", [None])[0]
        if query_gid and query_gid.isdigit():
            return int(query_gid)
        fragment_match = re.search(r"gid=(\d+)", parsed.fragment)
        if fragment_match:
            return int(fragment_match.group(1))
        return None
