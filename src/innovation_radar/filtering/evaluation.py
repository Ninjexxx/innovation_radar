"""Gold Set evaluation for deterministic shadow-filter rules."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from innovation_radar.filtering.deterministic import (
    DEFAULT_RULES,
    DeterministicRule,
    FilterOutcome,
    ShadowFilterReport,
    evaluate_in_shadow,
)
from innovation_radar.models import RawItem


ALLOWED_LABELS = frozenset({"interesting", "maybe", "irrelevant"})
DEFAULT_EXPECTED_GOLD_SET_SIZE = 130
REFERENCE_TIME = datetime(2026, 8, 27, tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class GoldSetCase:
    item: RawItem
    source_surface_or_feed: str
    human_label: str
    human_reason: str


@dataclass(frozen=True, slots=True)
class RuleExample:
    item_id: str
    title: str
    human_label: str


@dataclass(frozen=True, slots=True)
class RuleEvaluation:
    rule_id: str
    configured_outcome: FilterOutcome
    affected_count: int
    label_counts: Mapping[str, int]
    examples: tuple[RuleExample, ...]

    @property
    def interesting_count(self) -> int:
        return self.label_counts.get("interesting", 0)

    @property
    def maybe_count(self) -> int:
        return self.label_counts.get("maybe", 0)

    @property
    def irrelevant_count(self) -> int:
        return self.label_counts.get("irrelevant", 0)

    @property
    def correct_discard_rate(self) -> float | None:
        if (
            self.configured_outcome is not FilterOutcome.DISCARD_CANDIDATE
            or self.affected_count == 0
        ):
            return None
        return self.irrelevant_count / self.affected_count

    @property
    def false_positive_count(self) -> int:
        return self.interesting_count + self.maybe_count

    @property
    def safe_discard_observed(self) -> bool:
        return (
            self.configured_outcome is FilterOutcome.DISCARD_CANDIDATE
            and self.affected_count > 0
            and self.false_positive_count == 0
        )


@dataclass(frozen=True, slots=True)
class GoldSetFilterEvaluation:
    cases: tuple[GoldSetCase, ...]
    shadow_report: ShadowFilterReport
    rule_evaluations: tuple[RuleEvaluation, ...]

    @property
    def total(self) -> int:
        return len(self.cases)

    @property
    def label_counts(self) -> Mapping[str, int]:
        return dict(Counter(case.human_label for case in self.cases))

    @property
    def outcome_label_counts(self) -> Mapping[FilterOutcome, Mapping[str, int]]:
        labels_by_id = {case.item.id: case.human_label for case in self.cases}
        counts: dict[FilterOutcome, Counter[str]] = {
            outcome: Counter() for outcome in FilterOutcome
        }
        for decision in self.shadow_report.decisions:
            counts[decision.outcome][labels_by_id[decision.item_id]] += 1
        return {outcome: dict(values) for outcome, values in counts.items()}

    @property
    def interesting_discard_candidates(self) -> int:
        return self.outcome_label_counts[FilterOutcome.DISCARD_CANDIDATE].get(
            "interesting", 0
        )

    @property
    def maybe_discard_candidates(self) -> int:
        return self.outcome_label_counts[FilterOutcome.DISCARD_CANDIDATE].get(
            "maybe", 0
        )


def evaluate_gold_set(
    path: str | Path,
    *,
    expected_count: int = DEFAULT_EXPECTED_GOLD_SET_SIZE,
    rules: Sequence[DeterministicRule] = DEFAULT_RULES,
) -> GoldSetFilterEvaluation:
    """Load the human reference and evaluate every rule without changing it."""

    cases = load_gold_set_cases(path, expected_count=expected_count)
    items = tuple(case.item for case in cases)
    labels_by_id = {case.item.id: case.human_label for case in cases}
    case_by_id = {case.item.id: case for case in cases}
    rule_evaluations: list[RuleEvaluation] = []

    for rule in rules:
        individual_report = evaluate_in_shadow(items, rules=(rule,))
        affected_ids = tuple(
            decision.item_id
            for decision in individual_report.decisions
            if any(result.rule_id == rule.rule_id for result in decision.rule_results)
        )
        label_counts = Counter(labels_by_id[item_id] for item_id in affected_ids)
        example_ids = _representative_ids(affected_ids, labels_by_id)
        examples = tuple(
            RuleExample(
                item_id=item_id,
                title=case_by_id[item_id].item.title,
                human_label=labels_by_id[item_id],
            )
            for item_id in example_ids
        )
        rule_evaluations.append(
            RuleEvaluation(
                rule_id=rule.rule_id,
                configured_outcome=rule.outcome,
                affected_count=len(affected_ids),
                label_counts=dict(label_counts),
                examples=examples,
            )
        )

    return GoldSetFilterEvaluation(
        cases=cases,
        shadow_report=evaluate_in_shadow(items, rules=rules),
        rule_evaluations=tuple(rule_evaluations),
    )


def load_gold_set_cases(
    path: str | Path,
    *,
    expected_count: int = DEFAULT_EXPECTED_GOLD_SET_SIZE,
) -> tuple[GoldSetCase, ...]:
    """Validate the evaluation reference and adapt only observable fields."""

    source_path = Path(path)
    try:
        document = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Gold Set is not readable: {source_path}: {error}") from error
    if not isinstance(document, dict) or not isinstance(document.get("items"), list):
        raise ValueError("Gold Set must contain an items array")
    raw_items = document["items"]
    if document.get("item_count") != len(raw_items):
        raise ValueError("Gold Set item_count does not match its items array")
    if len(raw_items) != expected_count:
        raise ValueError(
            f"expected {expected_count} Gold Set items, found {len(raw_items)}"
        )

    cases: list[GoldSetCase] = []
    seen_ids: set[str] = set()
    for index, raw_case in enumerate(raw_items, start=1):
        if not isinstance(raw_case, dict):
            raise ValueError(f"Gold Set item {index} must be an object")
        item_id = _required_text(raw_case, "item_id", index)
        if item_id in seen_ids:
            raise ValueError(f"Gold Set contains duplicate item_id {item_id!r}")
        seen_ids.add(item_id)
        source = _required_text(raw_case, "source", index)
        label = _required_text(raw_case, "human_label", index)
        if label not in ALLOWED_LABELS:
            raise ValueError(f"Gold Set item {index} has invalid human_label {label!r}")
        reason = _required_text(raw_case, "human_reason", index)
        metrics = raw_case.get("available_metrics")
        if not isinstance(metrics, dict):
            raise ValueError(
                f"Gold Set item {index} available_metrics must be an object"
            )
        surface = str(raw_case.get("source_surface_or_feed") or "")
        published_at = _optional_datetime(raw_case.get("published_at"), index)
        cases.append(
            GoldSetCase(
                item=RawItem(
                    id=item_id,
                    source=source,
                    source_item_id=_source_item_id(item_id, source),
                    title=_required_text(raw_case, "title", index),
                    url=_required_text(raw_case, "url", index),
                    description=_optional_text(raw_case.get("short_description")),
                    author=_optional_text(raw_case.get("author")),
                    published_at=published_at,
                    first_seen_at=REFERENCE_TIME,
                    collected_at=REFERENCE_TIME,
                    raw_metrics=metrics,
                    raw_payload=_evaluation_payload(source, surface),
                ),
                source_surface_or_feed=surface,
                human_label=label,
                human_reason=reason,
            )
        )
    return tuple(cases)


def _evaluation_payload(source: str, surface: str) -> dict[str, Any]:
    """Recreate provenance only; human labels and reasons never enter a rule."""

    parts = [part.strip() for part in surface.split("|") if part.strip()]
    if source == "github":
        return {"discovery_lenses": parts}
    if source == "hacker_news":
        return {"discovery_surfaces": parts}
    if source == "rss":
        feed_id = surface
        if "[" in surface and surface.endswith("]"):
            feed_id = surface.rsplit("[", 1)[1][:-1]
        return {"feed": {"id": feed_id, "name": surface}}
    return {"source_surface_or_feed": surface}


def _source_item_id(item_id: str, source: str) -> str:
    prefix = f"{source}:"
    return item_id[len(prefix) :] if item_id.startswith(prefix) else item_id


def _representative_ids(
    affected_ids: tuple[str, ...], labels_by_id: Mapping[str, str]
) -> tuple[str, ...]:
    selected: list[str] = []
    for label in ("interesting", "maybe", "irrelevant"):
        matching = next(
            (item_id for item_id in affected_ids if labels_by_id[item_id] == label),
            None,
        )
        if matching is not None:
            selected.append(matching)
    for item_id in affected_ids:
        if item_id not in selected:
            selected.append(item_id)
        if len(selected) == 5:
            break
    return tuple(selected)


def _required_text(case: Mapping[str, Any], key: str, index: int) -> str:
    value = case.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Gold Set item {index} {key} must be non-empty text")
    return value


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Gold Set optional text fields must contain text")
    return value or None


def _optional_datetime(value: object, index: int) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError(f"Gold Set item {index} published_at must contain text")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(
            f"Gold Set item {index} published_at is not an ISO datetime"
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"Gold Set item {index} published_at must include timezone")
    return parsed.astimezone(timezone.utc)
