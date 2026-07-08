"""Deterministic identifier helpers."""

from __future__ import annotations

from hashlib import sha256


def generate_manifest_id(source_id: str, canonical_url: str) -> str:
    """Generate a deterministic manifest identifier."""

    normalized = f"{source_id.strip()}::{canonical_url.strip()}"
    return sha256(normalized.encode("utf-8")).hexdigest()

