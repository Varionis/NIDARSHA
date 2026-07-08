"""Run the Phase 1 discovery engine against the configured source registry.

Purpose:
    Provide a simple executable entrypoint for loading the registry, building
    discovery manifests, and printing a compact run summary.
Inputs:
    Environment variables from `.env` and the configured Google Sheets registry.
Outputs:
    Console summary of the discovery run and the first manifest record, if any.
Assumptions:
    Crawling and publishing remain out of scope for Phase 1.
"""

from __future__ import annotations

from pathlib import Path
import os
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ENV_FILE = ROOT / ".env"


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from a local env file into the process."""

    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    """Run discovery and print a concise execution summary."""

    load_env_file(ENV_FILE)
    sys.path.insert(0, str(SRC))

    from common.config.settings import load_config
    from discovery.engine import DiscoveryEngine
    from discovery.publisher import FileManifestPublisher, GoogleSheetsManifestPublisher
    from discovery.registry.reader import RegistryReader

    cfg = load_config()
    if not cfg.registry.sheet_url:
        raise SystemExit("NIDARSHA_REGISTRY_SHEET_URL is not configured.")

    reader = RegistryReader(
        sheet_url=cfg.registry.sheet_url,
        registry_settings=cfg.registry,
        settings=cfg.discovery,
    )
    engine = DiscoveryEngine(registry_reader=reader, config=cfg)
    publisher = FileManifestPublisher(cfg.discovery.manifest_output_dir)
    sheets_publisher = None
    if cfg.registry.discovery_sheet_url:
        sheets_publisher = GoogleSheetsManifestPublisher(
            sheet_url=cfg.registry.discovery_sheet_url,
            registry_settings=cfg.registry,
        )

    run, manifests = engine.discover()
    manifest_path = publisher.publish(manifests)
    sheet_rows = sheets_publisher.publish(manifests) if sheets_publisher else 0

    print(f"run_id={run.run_id}")
    print(f"sources={run.source_count}")
    print(f"manifests={len(manifests)}")
    print(f"manifest_path={manifest_path}")
    if sheets_publisher:
        print(f"sheet_rows_written={sheet_rows}")
    if manifests:
        print(manifests[0])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
