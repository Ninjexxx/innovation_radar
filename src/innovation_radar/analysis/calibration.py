"""M4 calibration: compare M3 recommendations against human Gold Set labels.

This layer measures whether the radar reduces noise without dropping interesting
signals, following ``docs/06_EVALUATION.md``. It does not change human labels, it
does not auto-tune rules or prompts, and it does not use an LLM to judge quality.
It only compares the system recommendation with the human label and reports the
divergences so a human can calibrate later.

Label <-> recommendation mapping (docs/06 sections 2 and 4):

* ``interesting`` <-> ``investigate``
* ``maybe``       <-> ``watchlist``
* ``irrelevant``  <-> ``archive``

An item skipped by M3 (a deterministic ``discard_candidate``) never reached the
provider; its effective system decision is treated as ``archive``, so a skipped
``interesting`` item is counted as a false negative just like an archived one.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from innovation_radar.analysis.engine import AnalysisReport, analyze_items
from innovation_radar.analysis.models import Recommendation
from innovation_radar.analysis.provider import OpportunityProvider
from innovation_radar.filtering.evaluation import GoldSetCase


# Human label -> the recommendation that would agree with it.
LABEL_TO_RECOMMENDATION: Mapping[str, Recommendation] = {
    "interesting": Recommendation.INVESTIGATE,
    "maybe": Recommendation.WATCHLIST,
    "irrelevant": Recommendation.ARCHIVE,
}
# Reverse map for readable reporting.
RECOMMENDATION_TO_LABEL: Mapping[Recommendation, str] = {
    recommendation: label for label, recommendation in LABEL_TO_RECOMMENDATION.items()
}


@dataclass(frozen=True, slots=True)
class CalibrationCase:
    """One item with both its human label and the system's decision."""

    item_id: str
    title: str
    source: str
    human_label: str
    human_reason: str
    recommendation: Recommendation
    skipped_by_filter: bool
    signal_type: str | None
    developer_tooling: bool | None

    @property
    def expected_recommendation(self) -> Recommendation:
        return LABEL_TO_RECOMMENDATION[self.human_label]

    @property
    def agrees(self) -> bool:
        return self.recommendation is self.expected_recommendation

    @property
    def is_false_positive(self) -> bool:
        """System asks a human to look (investigate/watchlist) but label is irrelevant."""

        return (
            self.human_label == "irrelevant"
            and self.recommendation is not Recommendation.ARCHIVE
        )

    @property
    def is_false_negative(self) -> bool:
        """System archives, but the human considered it interesting."""

        return (
            self.human_label == "interesting"
            and self.recommendation is Recommendation.ARCHIVE
        )

    @property
    def is_maybe_divergence(self) -> bool:
        return self.human_label == "maybe" and not self.agrees


@dataclass(frozen=True, slots=True)
class CategoryBreakdown:
    """Agreement and divergence counts for one category value."""

    key: str
    total: int
    agreements: int
    false_positives: int
    false_negatives: int
    maybe_divergences: int

    @property
    def agreement_rate(self) -> float:
        return self.agreements / self.total if self.total else 0.0


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    """Full comparison between system recommendations and human labels."""

    provider_name: str
    cases: tuple[CalibrationCase, ...]

    @property
    def total(self) -> int:
        return len(self.cases)

    @property
    def agreement_count(self) -> int:
        return sum(case.agrees for case in self.cases)

    @property
    def agreement_rate(self) -> float:
        return self.agreement_count / self.total if self.total else 0.0

    @property
    def false_positives(self) -> tuple[CalibrationCase, ...]:
        return tuple(case for case in self.cases if case.is_false_positive)

    @property
    def false_negatives(self) -> tuple[CalibrationCase, ...]:
        return tuple(case for case in self.cases if case.is_false_negative)

    @property
    def maybe_divergences(self) -> tuple[CalibrationCase, ...]:
        return tuple(case for case in self.cases if case.is_maybe_divergence)

    @property
    def label_counts(self) -> Mapping[str, int]:
        return dict(Counter(case.human_label for case in self.cases))

    @property
    def confusion_matrix(self) -> Mapping[str, Mapping[str, int]]:
        """Rows are human labels; columns are the system recommendation labels."""

        matrix: dict[str, Counter[str]] = {
            label: Counter() for label in LABEL_TO_RECOMMENDATION
        }
        for case in self.cases:
            system_label = RECOMMENDATION_TO_LABEL[case.recommendation]
            matrix[case.human_label][system_label] += 1
        return {label: dict(counts) for label, counts in matrix.items()}

    def breakdown_by(self, attribute: str) -> tuple[CategoryBreakdown, ...]:
        groups: dict[str, list[CalibrationCase]] = {}
        for case in self.cases:
            value = getattr(case, attribute)
            key = _category_key(value)
            groups.setdefault(key, []).append(case)
        breakdowns = [
            CategoryBreakdown(
                key=key,
                total=len(group),
                agreements=sum(case.agrees for case in group),
                false_positives=sum(case.is_false_positive for case in group),
                false_negatives=sum(case.is_false_negative for case in group),
                maybe_divergences=sum(case.is_maybe_divergence for case in group),
            )
            for key, group in groups.items()
        ]
        return tuple(sorted(breakdowns, key=lambda item: item.key))


def calibrate(
    gold_set_cases: Sequence[GoldSetCase],
    provider: OpportunityProvider | None = None,
) -> CalibrationResult:
    """Analyze the Gold Set with M3 and compare each decision to the human label."""

    items = tuple(case.item for case in gold_set_cases)
    report = analyze_items(items, provider)
    return _calibrate_from_report(gold_set_cases, report)


def _calibrate_from_report(
    gold_set_cases: Sequence[GoldSetCase],
    report: AnalysisReport,
) -> CalibrationResult:
    analyzed_by_id = {item.item_id: item for item in report.analyzed}
    cases: list[CalibrationCase] = []
    for gold_case in gold_set_cases:
        analyzed = analyzed_by_id.get(gold_case.item.id)
        if analyzed is None:
            raise ValueError(
                f"analysis report is missing item {gold_case.item.id!r}"
            )
        if analyzed.analysis is not None:
            recommendation = analyzed.analysis.recommendation
            signal_type: str | None = analyzed.analysis.signal_type.value
            developer_tooling: bool | None = analyzed.analysis.developer_tooling
            skipped = False
        else:
            # Skipped by the deterministic filter: effective decision is archive.
            recommendation = Recommendation.ARCHIVE
            signal_type = None
            developer_tooling = None
            skipped = True
        cases.append(
            CalibrationCase(
                item_id=gold_case.item.id,
                title=gold_case.item.title,
                source=gold_case.item.source,
                human_label=gold_case.human_label,
                human_reason=gold_case.human_reason,
                recommendation=recommendation,
                skipped_by_filter=skipped,
                signal_type=signal_type,
                developer_tooling=developer_tooling,
            )
        )
    return CalibrationResult(
        provider_name=report.provider_name, cases=tuple(cases)
    )


def _category_key(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


__all__ = [
    "CalibrationCase",
    "CalibrationResult",
    "CategoryBreakdown",
    "LABEL_TO_RECOMMENDATION",
    "RECOMMENDATION_TO_LABEL",
    "calibrate",
]
