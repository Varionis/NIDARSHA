"""File-based discovery manifest publisher.

Purpose:
    Persist discovery manifests to a local JSON artifact for inspection and
    downstream handoff.
Inputs:
    A sequence of `DiscoveryManifest` records and an output directory.
Outputs:
    A JSON file containing the run summary and discovered source links.
Assumptions:
    Phase 1 only needs a local artifact, not a database or sheet writer.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from discovery.classification import ContentClass
from discovery.manifest.models import DiscoveryManifest

from .base import ManifestPublisher


class FileManifestPublisher(ManifestPublisher):
    """Write discovery manifests to a JSON artifact."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def publish(self, manifests: Iterable[DiscoveryManifest]) -> Path:
        """Write manifests to a JSON file and return the file path."""

        manifest_list = list(manifests)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if manifest_list:
            run_id = manifest_list[0].run_id
        else:
            run_id = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        output_path = self.output_dir / f"discovery_manifest_{run_id}.json"

        payload = {
            "run_id": run_id,
            "manifest_count": len(manifest_list),
            "published_at": datetime.utcnow().isoformat() + "Z",
            "manifests": [self._serialize_manifest(manifest) for manifest in manifest_list],
        }
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path

    def _serialize_manifest(self, manifest: DiscoveryManifest) -> dict[str, Any]:
        data = asdict(manifest)
        data["crawl_strategy"] = manifest.crawl_strategy.value
        data["content_class"] = self._enum_value(manifest.content_class)
        data["discovered_at"] = manifest.discovered_at.isoformat()
        return data

    def _enum_value(self, value: Any) -> Any:
        if isinstance(value, ContentClass):
            return value.value
        return value
