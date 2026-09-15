"""Shared collector contracts for the discovery pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from innovation_radar.models import RawItem


@dataclass(frozen=True, slots=True)
class CollectionFailure:
    source: str
    context: str
    error: str


@dataclass(frozen=True, slots=True)
class CollectionBatch:
    items: tuple[RawItem, ...] = ()
    failures: tuple[CollectionFailure, ...] = ()


class Collector(Protocol):
    name: str

    def collect(self, collected_at: datetime) -> CollectionBatch:
        """Collect and normalize one bounded batch from an external source."""

