"""Small text normalization helpers shared by collectors."""

from __future__ import annotations

import re
from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def html_to_text(value: str | None) -> str | None:
    """Convert a short HTML fragment to readable single-spaced text."""

    if value is None or not value.strip():
        return None
    parser = _TextExtractor()
    parser.feed(value)
    text = " ".join(" ".join(parser.parts).split())
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    return text or None
