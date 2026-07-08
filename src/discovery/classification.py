"""Resource classification helpers for discovered links."""

from __future__ import annotations

from enum import Enum
from urllib.parse import urlparse


class ContentClass(str, Enum):
    """Coarse content classes used by discovery outputs."""

    WEB_PAGE = "WEB_PAGE"
    PDF = "PDF"
    DOCUMENT = "DOCUMENT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    OTHER = "OTHER"


_WEB_PAGE_EXTENSIONS = {
    "",
    ".htm",
    ".html",
    ".php",
    ".asp",
    ".aspx",
    ".jsp",
    ".cfm",
    ".shtml",
}

_DOCUMENT_EXTENSIONS = {
    ".doc",
    ".docx",
    ".docm",
    ".dot",
    ".dotx",
    ".odt",
    ".rtf",
    ".txt",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".csv",
}

_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".svg",
}

_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".m4v",
    ".avi",
    ".mkv",
    ".webm",
    ".wmv",
    ".flv",
}


def classify_content(url: str, content_type: str | None = None) -> ContentClass:
    """Classify a URL using the URL path and optional response content type."""

    normalized_content_type = (content_type or "").lower()
    path = urlparse(url).path.lower()

    if "pdf" in normalized_content_type or path.endswith(".pdf"):
        return ContentClass.PDF

    if any(token in normalized_content_type for token in ("msword", "wordprocessingml", "officedocument", "presentationml", "spreadsheetml", "text/csv", "text/plain")):
        return ContentClass.DOCUMENT

    if normalized_content_type.startswith("image/"):
        return ContentClass.IMAGE

    if normalized_content_type.startswith("video/"):
        return ContentClass.VIDEO

    if "html" in normalized_content_type or "xhtml" in normalized_content_type:
        return ContentClass.WEB_PAGE

    suffix = _path_suffix(path)
    if suffix in _WEB_PAGE_EXTENSIONS:
        return ContentClass.WEB_PAGE

    if suffix in _DOCUMENT_EXTENSIONS:
        return ContentClass.DOCUMENT

    if suffix in _IMAGE_EXTENSIONS:
        return ContentClass.IMAGE

    if suffix in _VIDEO_EXTENSIONS:
        return ContentClass.VIDEO

    return ContentClass.OTHER


def _path_suffix(path: str) -> str:
    if "." not in path.rsplit("/", 1)[-1]:
        return ""
    return "." + path.rsplit(".", 1)[-1]
