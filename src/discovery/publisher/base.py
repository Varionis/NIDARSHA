"""Publisher interface for discovery manifests."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from discovery.manifest.models import DiscoveryManifest


class ManifestPublisher(ABC):
    """Abstract contract for discovery manifest publishers."""

    @abstractmethod
    def publish(self, manifests: Iterable[DiscoveryManifest]) -> None:
        """Persist discovery manifests to a downstream system."""

