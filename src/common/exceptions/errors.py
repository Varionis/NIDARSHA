"""Application exceptions with clear operational meaning.

Purpose:
    Provide a small, reusable exception hierarchy for discovery and future
    ingestion components.
Inputs:
    Error conditions raised by validators, readers, and normalizers.
Outputs:
    Typed exceptions that are easy to catch and distinguish.
Assumptions:
    The codebase will continue to expand under the same shared error model.
"""

from __future__ import annotations


class DiscoveryError(Exception):
    """Base class for discovery pipeline failures."""


class ConfigurationError(DiscoveryError):
    """Raised when application configuration is invalid or incomplete."""


class RegistryError(DiscoveryError):
    """Raised when the source registry cannot be loaded or parsed."""


class RegistryValidationError(RegistryError):
    """Raised when registry structure or content does not meet expectations."""


class SourceValidationError(DiscoveryError):
    """Raised when a source row cannot be converted into a valid source model."""


class CanonicalizationError(DiscoveryError):
    """Raised when URL normalization fails."""


class StrategyResolutionError(DiscoveryError):
    """Raised when a crawl strategy cannot be resolved."""


class ManifestError(DiscoveryError):
    """Raised when a discovery manifest cannot be constructed or published."""

