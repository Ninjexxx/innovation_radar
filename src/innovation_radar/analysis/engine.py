"""M3 analysis engine: deterministic filtering first, then provider analysis.

The engine enforces the M3 rule that only post-filter items are sent to the
model. It reuses the M2 shadow filter to identify ``discard_candidate`` items and
skips them before any provider call, keeping deterministic filtering separate
from LLM-based analysis (AGENTS.md engineering principle).

The engine is provider-agnostic: it accepts any ``OpportunityProvider``. The
default is the offline ``HeuristicProvider`` so the pipeline runs without a key.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from innovation_radar.analysis.models import AnalyzedItem, Recommendation, SignalType
from innovation_radar.analysis.provider import (
    HeuristicProvider,
    OpportunityProvider,
    ProviderContext,
)
from innovation_radar.filtering.deterministic import (
    DEFAULT_RULES,
    DeterministicRule,
    FilterOutcome,
    evaluate_in_shadow,
)
from innovation_radar.models import RawItem


@dataclass(frozen=True, slots=True)
class AnalysisReport:
    """Result of analyzing one batch of items with one provider."""

    provider_name: str
    analyzed: tuple[AnalyzedItem, ...]

    @property
    def total(self) -> int:
        return len(self.analyzed)

    @property
    def analyzed_count(self) -> int:
        return sum(item.analyzed for item in self.analyzed)

    @property
    def skipped_count(self) -> int:
        return self.total - self.analyzed_count

    @property
    def recommendation_counts(self) -> Mapping[str, int]:
        counter: Counter[str] = Counter()
        for item in self.analyzed:
            if item.analysis is not None:
                counter[item.analysis.recommendation.value] += 1
        return dict(counter)

    @property
    def signal_type_counts(self) -> Mapping[str, int]:
        counter: Counter[str] = Counter()
        for item in self.analyzed:
            if item.analysis is not None:
                counter[item.analysis.signal_type.value] += 1
        return dict(counter)

    @property
    def developer_tooling_count(self) -> int:
        return sum(
            1
            for item in self.analyzed
            if item.analysis is not None and item.analysis.developer_tooling
        )

    def by_recommendation(self, recommendation: Recommendation) -> tuple[AnalyzedItem, ...]:
        return tuple(
            item
            for item in self.analyzed
            if item.analysis is not None
            and item.analysis.recommendation is recommendation
        )


def analyze_items(
    items: Sequence[RawItem],
    provider: OpportunityProvider | None = None,
    *,
    rules: Sequence[DeterministicRule] = DEFAULT_RULES,
) -> AnalysisReport:
    """Analyze items, skipping deterministic ``discard_candidate`` items.

    Only items that survive the M2 shadow filter reach the provider. Skipped
    items are still reported (with a reason) so nothing disappears silently.
    """

    active_provider = provider or HeuristicProvider()
    raw_items = tuple(items)
    shadow_report = evaluate_in_shadow(raw_items, rules=rules)
    outcome_by_id = {
        decision.item_id: decision.outcome for decision in shadow_report.decisions
    }

    analyzed: list[AnalyzedItem] = []
    for item in raw_items:
        outcome = outcome_by_id.get(item.id, FilterOutcome.KEEP)
        if outcome is FilterOutcome.DISCARD_CANDIDATE:
            analyzed.append(
                AnalyzedItem(
                    item_id=item.id,
                    title=item.title,
                    source=item.source,
                    analysis=None,
                    skipped_reason=(
                        "Marcado como discard_candidate pelo filtro determinístico "
                        "(M2); não enviado ao provedor."
                    ),
                )
            )
            continue

        analysis = active_provider.analyze(ProviderContext.from_raw_item(item))
        analyzed.append(
            AnalyzedItem(
                item_id=item.id,
                title=item.title,
                source=item.source,
                analysis=analysis,
            )
        )

    return AnalysisReport(
        provider_name=getattr(active_provider, "name", "unknown"),
        analyzed=tuple(analyzed),
    )


__all__ = [
    "AnalysisReport",
    "analyze_items",
    "Recommendation",
    "SignalType",
]
