"""Shared data models for collected items and execution records."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _as_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _validate_json(value: Any, field_name: str) -> None:
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field_name} must contain valid JSON data") from error


@dataclass(frozen=True, slots=True)
class RawItem:
    """A collected item with source metadata and optional raw JSON payload."""

    id: str
    source: str
    source_item_id: str
    title: str
    url: str
    first_seen_at: datetime
    collected_at: datetime
    description: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    raw_metrics: Mapping[str, Any] = field(default_factory=dict)
    raw_payload: Any | None = None

    def __post_init__(self) -> None:
        for field_name in ("id", "source", "source_item_id", "title", "url"):
            _require_text(getattr(self, field_name), field_name)

        if not isinstance(self.raw_metrics, Mapping):
            raise ValueError("raw_metrics must be a mapping")

        raw_metrics = dict(self.raw_metrics)
        _validate_json(raw_metrics, "raw_metrics")
        if self.raw_payload is not None:
            _validate_json(self.raw_payload, "raw_payload")

        object.__setattr__(
            self, "first_seen_at", _as_utc(self.first_seen_at, "first_seen_at")
        )
        object.__setattr__(
            self, "collected_at", _as_utc(self.collected_at, "collected_at")
        )
        if self.published_at is not None:
            object.__setattr__(
                self, "published_at", _as_utc(self.published_at, "published_at")
            )
        object.__setattr__(self, "raw_metrics", raw_metrics)


@dataclass(frozen=True, slots=True)
class ItemReview:
    """One human review decision persisted so an item is not shown again."""

    item_id: str
    human_label: str
    reviewed_at: datetime
    human_reason: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.item_id, "item_id")
        _require_text(self.human_label, "human_label")
        object.__setattr__(
            self, "reviewed_at", _as_utc(self.reviewed_at, "reviewed_at")
        )
        if self.human_reason is not None and not isinstance(self.human_reason, str):
            raise ValueError("human_reason must be a string when provided")


@dataclass(frozen=True, slots=True)
class RunRecord:
    """A minimal record of one radar execution."""

    id: str
    started_at: datetime
    status: str
    finished_at: datetime | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.id, "id")
        _require_text(self.status, "status")

        started_at = _as_utc(self.started_at, "started_at")
        finished_at = (
            _as_utc(self.finished_at, "finished_at")
            if self.finished_at is not None
            else None
        )
        if finished_at is not None and finished_at < started_at:
            raise ValueError("finished_at must not be earlier than started_at")

        object.__setattr__(self, "started_at", started_at)
        object.__setattr__(self, "finished_at", finished_at)
