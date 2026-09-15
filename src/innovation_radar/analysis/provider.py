"""Replaceable opportunity-analysis providers.

Invariant 9 requires the LLM vendor to be replaceable and to stay out of the
system architecture. Invariant 10 requires the MVP to run without any LLM API
key. This module satisfies both:

* ``OpportunityProvider`` is a small protocol every backend implements.
* ``ProviderContext`` is the neutral request the engine hands to a provider, so
  no provider ever touches storage, collectors or configuration.
* ``HeuristicProvider`` is a deterministic, offline default. It uses only local,
  transparent signals to produce a structured ``OpportunityAnalysis``. It is not
  an intelligence layer; it exists so the pipeline is exercisable end to end and
  so remote providers have a reference contract to match.

A real LLM provider (OpenAI, Anthropic, Google, local model) would implement the
same protocol, build a prompt from ``docs/05_SIGNAL_POLICY.md`` plus the context,
call its API, and parse the response through ``OpportunityAnalysis.from_mapping``.
No such provider is added here: none is needed to validate the M3 contract, and
adding one now would violate the "no vendor in the architecture" invariant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable

from innovation_radar.analysis.models import (
    OpportunityAnalysis,
    Recommendation,
    SignalType,
    Traction,
)
from innovation_radar.models import RawItem


@dataclass(frozen=True, slots=True)
class ProviderContext:
    """The neutral, provider-agnostic view of one item to be analyzed.

    The engine derives this from a ``RawItem``. Providers must depend only on
    these fields, never on storage or collector internals.
    """

    item_id: str
    source: str
    title: str
    url: str
    description: str
    provenance: tuple[str, ...]
    metrics: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw_item(cls, item: RawItem) -> "ProviderContext":
        return cls(
            item_id=item.id,
            source=item.source,
            title=item.title,
            url=item.url,
            description=(item.description or "").strip(),
            provenance=_provenance(item),
            metrics=dict(item.raw_metrics),
        )

    @property
    def text(self) -> str:
        """Lowercased title + description used for transparent lexical checks."""

        return f"{self.title}\n{self.description}".casefold()


@runtime_checkable
class OpportunityProvider(Protocol):
    """Any backend that turns a ``ProviderContext`` into a structured analysis."""

    name: str

    def analyze(self, context: ProviderContext) -> OpportunityAnalysis:
        """Return a structured opportunity assessment for one item."""


# --- Deterministic offline default -----------------------------------------

# Transparent lexical hints. These are NOT a relevance verdict; they only shape a
# reproducible baseline so the pipeline runs without a model. Real judgement is
# deferred to an LLM provider and, ultimately, to human review.
_DEV_TOOLING_HINTS = (
    "sdk",
    "framework",
    "cli",
    "wrapper",
    "boilerplate",
    "vector database",
    "vector db",
    "observability",
    "prompt tool",
    "library for developers",
    "developer tool",
)
_CAPABILITY_HINTS = (
    "now possible",
    "for the first time",
    "on-device",
    "local-first",
    "real-time",
    "breakthrough",
    "enables",
    "makes it possible",
)
_HEALTH_HINTS = (
    "health",
    "wellness",
    "medical",
    "patient",
    "clinical",
    "care",
    "wearable",
    "biosensor",
    "sleep",
    "mental health",
)
_BEHAVIOR_HINTS = (
    "i built",
    "i made",
    "i wish",
    "workaround",
    "how do you",
    "my workflow",
    "self-tracking",
    "quantified self",
)
_STRATEGIC_HINTS = (
    "regulation",
    "policy",
    "market shift",
    "funding",
    "acquisition",
    "standard",
    "shift in how",
)
_NOISE_HINTS = (
    "top 10",
    "best tools",
    "died",
    "obituary",
    "award",
    "sports",
    "trends to watch",
)
_WORD_PATTERN = re.compile(r"\w+", re.UNICODE)


class HeuristicProvider:
    """Deterministic, offline provider used as the default M3 backend.

    Same input always yields the same output. It reads only the neutral context
    and applies documented lexical hints. It never calls the network and needs no
    credentials.
    """

    name = "heuristic-offline"

    def analyze(self, context: ProviderContext) -> OpportunityAnalysis:
        text = context.text
        developer_tooling = self._matches(text, _DEV_TOOLING_HINTS)
        has_capability = self._matches(text, _CAPABILITY_HINTS)
        has_behavior = self._matches(text, _BEHAVIOR_HINTS)
        has_strategic = self._matches(text, _STRATEGIC_HINTS)
        has_health = self._matches(text, _HEALTH_HINTS)
        looks_like_noise = self._matches(text, _NOISE_HINTS)
        thin_context = len(context.description) < 40

        signal_type = self._signal_type(
            has_capability=has_capability,
            has_behavior=has_behavior,
            has_strategic=has_strategic,
            developer_tooling=developer_tooling,
            thin_context=thin_context,
        )

        novelty = self._score(base=2, up=has_capability or has_strategic, down=looks_like_noise)
        capability = self._score(base=2, up=has_capability, down=thin_context or looks_like_noise)
        product = self._score(
            base=2,
            up=has_capability or has_behavior,
            down=developer_tooling or looks_like_noise,
        )
        namu = self._score(base=2, up=has_health or has_behavior, down=looks_like_noise)
        timing = self._score(base=3, up=has_capability, down=looks_like_noise)

        recommendation = self._recommendation(
            signal_type=signal_type,
            looks_like_noise=looks_like_noise,
            thin_context=thin_context,
            developer_tooling=developer_tooling,
            score_total=novelty + capability + product + namu + timing,
        )

        return OpportunityAnalysis(
            signal_type=signal_type,
            summary=self._summary(context),
            what_is_new=self._what_is_new(has_capability, has_strategic, thin_context),
            new_capability=(
                "Sinais lexicais indicam uma capacidade potencialmente nova."
                if has_capability
                else "Nenhuma nova capacidade clara foi identificada por heurística."
            ),
            product_possibility=(
                "Possível caminho de produto/experiência a investigar."
                if product >= 3
                else "Consequência de produto pouco evidente nesta heurística."
            ),
            namu_relevance=(
                "Tema com afinidade plausível a saúde/bem-estar; confirmar transferibilidade."
                if has_health or namu >= 3
                else "Relação com a Namu não é evidente sem investigação humana."
            ),
            developer_tooling=developer_tooling,
            novelty_score=novelty,
            capability_score=capability,
            product_score=product,
            namu_score=namu,
            timing_score=timing,
            traction=self._traction(context.metrics),
            recommendation=recommendation,
            evidence=self._evidence(
                developer_tooling=developer_tooling,
                has_capability=has_capability,
                has_behavior=has_behavior,
                has_strategic=has_strategic,
                has_health=has_health,
                looks_like_noise=looks_like_noise,
                thin_context=thin_context,
            ),
        )

    @staticmethod
    def _matches(text: str, hints: tuple[str, ...]) -> bool:
        return any(hint in text for hint in hints)

    @staticmethod
    def _score(*, base: int, up: bool, down: bool) -> int:
        value = base + (1 if up else 0) - (1 if down else 0)
        return max(1, min(5, value))

    @staticmethod
    def _signal_type(
        *,
        has_capability: bool,
        has_behavior: bool,
        has_strategic: bool,
        developer_tooling: bool,
        thin_context: bool,
    ) -> SignalType:
        if thin_context and not (has_capability or has_behavior or has_strategic):
            return SignalType.UNCLEAR
        if has_capability and developer_tooling:
            return SignalType.ENABLING_TESTABLE
        if has_capability:
            return SignalType.NEW_CAPABILITY
        if has_behavior:
            return SignalType.NEW_BEHAVIOR
        if has_strategic:
            return SignalType.STRATEGIC_SHIFT
        if developer_tooling:
            return SignalType.ENABLING_TESTABLE
        return SignalType.NEW_APPLICATION

    @staticmethod
    def _recommendation(
        *,
        signal_type: SignalType,
        looks_like_noise: bool,
        thin_context: bool,
        developer_tooling: bool,
        score_total: int,
    ) -> Recommendation:
        if looks_like_noise or signal_type is SignalType.UNCLEAR:
            return Recommendation.ARCHIVE
        if score_total >= 16 and not developer_tooling:
            return Recommendation.INVESTIGATE
        if thin_context and score_total < 12:
            return Recommendation.ARCHIVE
        return Recommendation.WATCHLIST

    @staticmethod
    def _summary(context: ProviderContext) -> str:
        title = " ".join(context.title.split())
        if context.description:
            snippet = " ".join(context.description.split())[:180]
            return f"{title} — {snippet}"
        return title

    @staticmethod
    def _what_is_new(
        has_capability: bool, has_strategic: bool, thin_context: bool
    ) -> str:
        if has_capability:
            return "Linguagem sugere que algo passou a ser possível ou mais acessível."
        if has_strategic:
            return "Pode indicar uma mudança de mercado, regulação ou comportamento."
        if thin_context:
            return "Contexto textual insuficiente para afirmar novidade."
        return "Aplicação ou combinação possivelmente incomum, a confirmar."

    @staticmethod
    def _traction(metrics: Mapping[str, Any]) -> Traction:
        score = metrics.get("score")
        stars = metrics.get("stars") or metrics.get("stargazers_count")
        signal = max(
            value for value in (score, stars, 0) if isinstance(value, (int, float))
        )
        if signal <= 0:
            return Traction.UNKNOWN
        if signal < 50:
            return Traction.WEAK
        if signal < 500:
            return Traction.GROWING
        if signal < 5000:
            return Traction.STRONG
        return Traction.CONSOLIDATED

    @staticmethod
    def _evidence(
        *,
        developer_tooling: bool,
        has_capability: bool,
        has_behavior: bool,
        has_strategic: bool,
        has_health: bool,
        looks_like_noise: bool,
        thin_context: bool,
    ) -> tuple[str, ...]:
        evidence: list[str] = []
        if developer_tooling:
            evidence.append("Sinais de developer tooling no texto.")
        if has_capability:
            evidence.append("Marcadores de nova capacidade.")
        if has_behavior:
            evidence.append("Relato de comportamento ou necessidade pessoal.")
        if has_strategic:
            evidence.append("Marcadores de mudança estratégica.")
        if has_health:
            evidence.append("Vocabulário de saúde/bem-estar presente.")
        if looks_like_noise:
            evidence.append("Padrão textual associado a ruído informativo.")
        if thin_context:
            evidence.append("Descrição curta ou ausente.")
        if not evidence:
            evidence.append("Nenhum marcador lexical forte; requer revisão humana.")
        return tuple(evidence)


def _provenance(item: RawItem) -> tuple[str, ...]:
    payload = item.raw_payload if isinstance(item.raw_payload, dict) else {}
    for key in ("discovery_lenses", "discovery_surfaces"):
        values = payload.get(key)
        if isinstance(values, list):
            provenance = tuple(
                value for value in values if isinstance(value, str) and value.strip()
            )
            if provenance:
                return provenance
    feed = payload.get("feed")
    if isinstance(feed, dict) and isinstance(feed.get("id"), str):
        return (feed["id"],)
    return ()
