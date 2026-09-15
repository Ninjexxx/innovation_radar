"""Structured output models for the M3 Opportunity AI layer.

These models define the *contract* the radar expects from any LLM provider. The
shape follows ``docs/02_ARCHITECTURE.md`` section 11 and the analysis questions in
``docs/03_MVP_SCOPE.md`` (M3). The models are deliberately provider-agnostic: no
field depends on a specific vendor, and the values are plain data so results can be
serialized, stored and compared reproducibly.

The analysis never decides on its own. ``recommendation`` is a suggestion for a
human analyst, mirroring the invariant that human review stays the final layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class SignalType(str, Enum):
    """The five overlapping signal types defined by the Signal Policy v0.2."""

    NEW_CAPABILITY = "new_capability"
    NEW_APPLICATION = "new_application"
    NEW_BEHAVIOR = "new_behavior"
    ENABLING_TESTABLE = "enabling_testable"
    STRATEGIC_SHIFT = "strategic_shift"
    UNCLEAR = "unclear"


class Traction(str, Enum):
    """Traction is complementary evidence of maturity, never a ranking motor."""

    WEAK = "weak"
    GROWING = "growing"
    STRONG = "strong"
    CONSOLIDATED = "consolidated"
    UNKNOWN = "unknown"


class Recommendation(str, Enum):
    """The three destinations a signal can take, decided by a human afterwards."""

    INVESTIGATE = "investigate"
    WATCHLIST = "watchlist"
    ARCHIVE = "archive"


SCORE_FIELDS = (
    "novelty_score",
    "capability_score",
    "product_score",
    "namu_score",
    "timing_score",
)
MIN_SCORE = 1
MAX_SCORE = 5


@dataclass(frozen=True, slots=True)
class OpportunityAnalysis:
    """One structured opportunity assessment for a single collected item.

    Scores are explanatory signals on a 1-5 scale, not a weighted ranking. They
    exist to make the reasoning inspectable, mirroring the Signal Policy note that
    the criteria "help explain the judgement; they do not constitute a score" as a
    decision mechanism.
    """

    signal_type: SignalType
    summary: str
    what_is_new: str
    new_capability: str
    product_possibility: str
    namu_relevance: str
    developer_tooling: bool
    novelty_score: int
    capability_score: int
    product_score: int
    namu_score: int
    timing_score: int
    traction: Traction
    recommendation: Recommendation
    evidence: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.signal_type, SignalType):
            raise ValueError("signal_type must be a SignalType")
        if not isinstance(self.traction, Traction):
            raise ValueError("traction must be a Traction")
        if not isinstance(self.recommendation, Recommendation):
            raise ValueError("recommendation must be a Recommendation")
        if not isinstance(self.developer_tooling, bool):
            raise ValueError("developer_tooling must be a boolean")

        for text_field in (
            "summary",
            "what_is_new",
            "new_capability",
            "product_possibility",
            "namu_relevance",
        ):
            value = getattr(self, text_field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{text_field} must be a non-empty string")

        for score_field in SCORE_FIELDS:
            value = getattr(self, score_field)
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"{score_field} must be an integer")
            if not MIN_SCORE <= value <= MAX_SCORE:
                raise ValueError(
                    f"{score_field} must be between {MIN_SCORE} and {MAX_SCORE}"
                )

        if not isinstance(self.evidence, tuple) or any(
            not isinstance(entry, str) or not entry.strip() for entry in self.evidence
        ):
            raise ValueError("evidence must be a tuple of non-empty strings")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready mapping with stable, sorted-friendly keys."""

        return {
            "signal_type": self.signal_type.value,
            "summary": self.summary,
            "what_is_new": self.what_is_new,
            "new_capability": self.new_capability,
            "product_possibility": self.product_possibility,
            "namu_relevance": self.namu_relevance,
            "developer_tooling": self.developer_tooling,
            "novelty_score": self.novelty_score,
            "capability_score": self.capability_score,
            "product_score": self.product_score,
            "namu_score": self.namu_score,
            "timing_score": self.timing_score,
            "traction": self.traction.value,
            "recommendation": self.recommendation.value,
            "evidence": list(self.evidence),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "OpportunityAnalysis":
        """Build an analysis from a provider payload, validating enums and scores.

        This is the boundary where untrusted provider output (including an LLM
        response) is checked before it enters the rest of the system.
        """

        if not isinstance(payload, Mapping):
            raise ValueError("analysis payload must be a mapping")

        try:
            signal_type = SignalType(str(payload["signal_type"]))
            traction = Traction(str(payload.get("traction", "unknown")))
            recommendation = Recommendation(str(payload["recommendation"]))
        except KeyError as error:
            raise ValueError(f"analysis payload missing field: {error}") from error
        except ValueError as error:
            raise ValueError(f"analysis payload has invalid enum: {error}") from error

        raw_evidence = payload.get("evidence", ())
        if isinstance(raw_evidence, (list, tuple)):
            evidence = tuple(str(entry) for entry in raw_evidence if str(entry).strip())
        else:
            raise ValueError("evidence must be an array when provided")

        def _score(name: str) -> int:
            value = payload.get(name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
            return value

        return cls(
            signal_type=signal_type,
            summary=str(payload.get("summary", "")),
            what_is_new=str(payload.get("what_is_new", "")),
            new_capability=str(payload.get("new_capability", "")),
            product_possibility=str(payload.get("product_possibility", "")),
            namu_relevance=str(payload.get("namu_relevance", "")),
            developer_tooling=bool(payload.get("developer_tooling", False)),
            novelty_score=_score("novelty_score"),
            capability_score=_score("capability_score"),
            product_score=_score("product_score"),
            namu_score=_score("namu_score"),
            timing_score=_score("timing_score"),
            traction=traction,
            recommendation=recommendation,
            evidence=evidence,
        )


@dataclass(frozen=True, slots=True)
class AnalyzedItem:
    """An analyzed item, or a skipped item that never reached the provider."""

    item_id: str
    title: str
    source: str
    analysis: OpportunityAnalysis | None
    skipped_reason: str | None = None

    def __post_init__(self) -> None:
        for text_field in ("item_id", "title", "source"):
            value = getattr(self, text_field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{text_field} must be a non-empty string")
        if self.analysis is None and not self.skipped_reason:
            raise ValueError("a skipped item must provide skipped_reason")
        if self.analysis is not None and self.skipped_reason is not None:
            raise ValueError("an analyzed item must not carry a skipped_reason")

    @property
    def analyzed(self) -> bool:
        return self.analysis is not None
