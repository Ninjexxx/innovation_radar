"""Conservative, explainable rules for objective discovery noise.

The layer intentionally runs in shadow mode: it returns derived decisions while
preserving every input ``RawItem`` in its original order.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from innovation_radar.models import RawItem


TRACKING_QUERY_PARAMETERS = frozenset(
    {
        "fbclid",
        "gclid",
        "utm_campaign",
        "utm_content",
        "utm_id",
        "utm_medium",
        "utm_source",
        "utm_term",
    }
)


class FilterOutcome(str, Enum):
    """The three non-semantic outcomes supported by the deterministic layer."""

    KEEP = "keep"
    NOISE_FLAG = "noise_flag"
    DISCARD_CANDIDATE = "discard_candidate"


@dataclass(frozen=True, slots=True)
class RuleResult:
    """One explainable result emitted by a deterministic rule."""

    rule_id: str
    outcome: FilterOutcome
    reason: str
    evidence: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class FilterDecision:
    """The strongest outcome and all rule evidence for one raw item."""

    item_id: str
    outcome: FilterOutcome
    rule_results: tuple[RuleResult, ...]


@dataclass(frozen=True, slots=True)
class ShadowFilterReport:
    """Derived filter results that never remove or mutate their input items."""

    items: tuple[RawItem, ...]
    decisions: tuple[FilterDecision, ...]
    shadow_mode: bool = True

    def count(self, outcome: FilterOutcome) -> int:
        return sum(decision.outcome is outcome for decision in self.decisions)

    @property
    def discard_candidate_count(self) -> int:
        return self.count(FilterOutcome.DISCARD_CANDIDATE)

    @property
    def noise_flag_count(self) -> int:
        return self.count(FilterOutcome.NOISE_FLAG)

    @property
    def keep_count(self) -> int:
        return self.count(FilterOutcome.KEEP)


@dataclass(frozen=True, slots=True)
class FilteringContext:
    """Batch context available to rules without coupling them to collectors."""

    items: tuple[RawItem, ...]
    index: int
    external_identity_first: Mapping[tuple[str, str], int]
    canonical_url_first: Mapping[str, int]
    github_repository_id_first: Mapping[str, int]


class DeterministicRule(Protocol):
    rule_id: str
    outcome: FilterOutcome

    def evaluate(
        self, item: RawItem, context: FilteringContext
    ) -> RuleResult | None:
        """Return an explainable match or ``None`` when the rule does not apply."""


class DuplicateExternalIdentityRule:
    rule_id = "duplicate_external_identity"
    outcome = FilterOutcome.DISCARD_CANDIDATE

    def evaluate(
        self, item: RawItem, context: FilteringContext
    ) -> RuleResult | None:
        identity = (item.source, item.source_item_id)
        first_index = context.external_identity_first[identity]
        if first_index == context.index:
            return None
        first_item = context.items[first_index]
        return RuleResult(
            rule_id=self.rule_id,
            outcome=self.outcome,
            reason="The same external source identity already appeared in this batch.",
            evidence={
                "source": item.source,
                "source_item_id": item.source_item_id,
                "first_item_id": first_item.id,
            },
        )


class DuplicateCanonicalUrlRule:
    rule_id = "duplicate_canonical_url"
    outcome = FilterOutcome.DISCARD_CANDIDATE

    def evaluate(
        self, item: RawItem, context: FilteringContext
    ) -> RuleResult | None:
        canonical_url = canonicalize_url(item.url)
        if canonical_url is None:
            return None
        first_index = context.canonical_url_first[canonical_url]
        if first_index == context.index:
            return None
        first_item = context.items[first_index]
        return RuleResult(
            rule_id=self.rule_id,
            outcome=self.outcome,
            reason="Another item in this batch points to the same canonical URL.",
            evidence={
                "canonical_url": canonical_url,
                "first_item_id": first_item.id,
            },
        )


class DuplicateGitHubRepositoryIdRule:
    rule_id = "duplicate_github_repository_id"
    outcome = FilterOutcome.DISCARD_CANDIDATE

    def evaluate(
        self, item: RawItem, context: FilteringContext
    ) -> RuleResult | None:
        if item.source != "github":
            return None
        first_index = context.github_repository_id_first[item.source_item_id]
        if first_index == context.index:
            return None
        first_item = context.items[first_index]
        return RuleResult(
            rule_id=self.rule_id,
            outcome=self.outcome,
            reason="The stable GitHub repository ID already appeared in this batch.",
            evidence={
                "repository_id": item.source_item_id,
                "first_item_id": first_item.id,
            },
        )


class ConsolidatedMultipleLensesRule:
    rule_id = "consolidated_multiple_lenses"
    outcome = FilterOutcome.KEEP

    def evaluate(
        self, item: RawItem, context: FilteringContext
    ) -> RuleResult | None:
        del context
        payload = item.raw_payload if isinstance(item.raw_payload, dict) else {}
        raw_lenses = payload.get("discovery_lenses")
        if not isinstance(raw_lenses, list):
            return None
        lenses = tuple(
            dict.fromkeys(
                lens for lens in raw_lenses if isinstance(lens, str) and lens.strip()
            )
        )
        if len(lenses) < 2:
            return None
        return RuleResult(
            rule_id=self.rule_id,
            outcome=self.outcome,
            reason=(
                "One external item was found by multiple lenses; provenance is "
                "already consolidated and is not duplicate content."
            ),
            evidence={"discovery_lenses": list(lenses)},
        )


class GitHubExplicitProfileDisclaimerRule:
    rule_id = "github_explicit_profile_disclaimer"
    outcome = FilterOutcome.DISCARD_CANDIDATE
    _markers = (
        "this is not our api",
        "independent, third-party profile",
        "independent third-party profile",
    )

    def evaluate(
        self, item: RawItem, context: FilteringContext
    ) -> RuleResult | None:
        del context
        if item.source != "github":
            return None
        text = _available_descriptive_text(item).casefold()
        marker = next((value for value in self._markers if value in text), None)
        if marker is None:
            return None
        return RuleResult(
            rule_id=self.rule_id,
            outcome=self.outcome,
            reason=(
                "The repository explicitly describes itself as a third-party "
                "profile rather than the represented API or implementation."
            ),
            evidence={"matched_marker": marker},
        )


class GitHubCompanyCatalogSignatureRule:
    rule_id = "github_company_catalog_signature"
    outcome = FilterOutcome.DISCARD_CANDIDATE

    def evaluate(
        self, item: RawItem, context: FilteringContext
    ) -> RuleResult | None:
        del context
        if item.source != "github":
            return None
        topics = _github_topics(item)
        language = item.raw_metrics.get("language")
        if not {"apis-json", "company"}.issubset(topics) or _has_text(language):
            return None
        return RuleResult(
            rule_id=self.rule_id,
            outcome=self.outcome,
            reason=(
                "The repository has the combined metadata signature of a company "
                "API catalog/profile and no detected implementation language."
            ),
            evidence={
                "required_topics": ["apis-json", "company"],
                "language": language,
            },
        )


class GitHubApiMetadataProfileRule:
    rule_id = "github_api_metadata_profile"
    outcome = FilterOutcome.NOISE_FLAG

    def evaluate(
        self, item: RawItem, context: FilteringContext
    ) -> RuleResult | None:
        del context
        if item.source != "github":
            return None
        topics = _github_topics(item)
        language = item.raw_metrics.get("language")
        if "apis-json" not in topics or _has_text(language):
            return None
        return RuleResult(
            rule_id=self.rule_id,
            outcome=self.outcome,
            reason=(
                "API metadata without a detected implementation language can be a "
                "profile or catalog, but this evidence is insufficient to discard."
            ),
            evidence={"matched_topic": "apis-json", "language": language},
        )


class InsufficientDescriptionRule:
    rule_id = "insufficient_description"
    outcome = FilterOutcome.NOISE_FLAG

    def evaluate(
        self, item: RawItem, context: FilteringContext
    ) -> RuleResult | None:
        del context
        if _has_text(item.description) or _has_structured_description(item):
            return None
        return RuleResult(
            rule_id=self.rule_id,
            outcome=self.outcome,
            reason=(
                "No description or supported structured context is available; the "
                "title and URL remain available for later review."
            ),
            evidence={
                "description_present": False,
                "structured_context_present": False,
            },
        )


class ArchivedGitHubRepositoryRule:
    rule_id = "github_archived_repository"
    outcome = FilterOutcome.NOISE_FLAG

    def evaluate(
        self, item: RawItem, context: FilteringContext
    ) -> RuleResult | None:
        del context
        if item.source != "github" or item.raw_metrics.get("archived") is not True:
            return None
        return RuleResult(
            rule_id=self.rule_id,
            outcome=self.outcome,
            reason=(
                "GitHub marks the repository as archived; archived work may still "
                "contain relevant evidence and is not discarded."
            ),
            evidence={"archived": True},
        )


DEFAULT_RULES: tuple[DeterministicRule, ...] = (
    DuplicateExternalIdentityRule(),
    DuplicateCanonicalUrlRule(),
    DuplicateGitHubRepositoryIdRule(),
    ConsolidatedMultipleLensesRule(),
    GitHubExplicitProfileDisclaimerRule(),
    GitHubCompanyCatalogSignatureRule(),
    GitHubApiMetadataProfileRule(),
    InsufficientDescriptionRule(),
    ArchivedGitHubRepositoryRule(),
)


def evaluate_in_shadow(
    items: Sequence[RawItem],
    rules: Sequence[DeterministicRule] = DEFAULT_RULES,
) -> ShadowFilterReport:
    """Evaluate rules deterministically without dropping or mutating raw items."""

    raw_items = tuple(items)
    external_identity_first: dict[tuple[str, str], int] = {}
    canonical_url_first: dict[str, int] = {}
    github_repository_id_first: dict[str, int] = {}
    for index, item in enumerate(raw_items):
        external_identity_first.setdefault((item.source, item.source_item_id), index)
        canonical_url = canonicalize_url(item.url)
        if canonical_url is not None:
            canonical_url_first.setdefault(canonical_url, index)
        if item.source == "github":
            github_repository_id_first.setdefault(item.source_item_id, index)

    decisions: list[FilterDecision] = []
    for index, item in enumerate(raw_items):
        context = FilteringContext(
            items=raw_items,
            index=index,
            external_identity_first=external_identity_first,
            canonical_url_first=canonical_url_first,
            github_repository_id_first=github_repository_id_first,
        )
        results = tuple(
            result
            for rule in rules
            if (result := rule.evaluate(item, context)) is not None
        )
        if not results:
            results = (
                RuleResult(
                    rule_id="no_noise_detected",
                    outcome=FilterOutcome.KEEP,
                    reason="No configured deterministic noise rule matched.",
                    evidence={},
                ),
            )
        decisions.append(
            FilterDecision(
                item_id=item.id,
                outcome=max(results, key=lambda result: _severity(result.outcome)).outcome,
                rule_results=results,
            )
        )

    return ShadowFilterReport(items=raw_items, decisions=tuple(decisions))


def canonicalize_url(value: str) -> str | None:
    """Return a conservative HTTP(S) canonical URL for exact duplicate checks."""

    try:
        parsed = urlsplit(value.strip())
        if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
            return None
        port = parsed.port
    except ValueError:
        return None

    scheme = parsed.scheme.casefold()
    hostname = parsed.hostname.casefold()
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    default_port = (scheme == "http" and port == 80) or (
        scheme == "https" and port == 443
    )
    netloc = hostname if port is None or default_port else f"{hostname}:{port}"
    path = parsed.path.rstrip("/") or "/"
    query_pairs = sorted(
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.casefold() not in TRACKING_QUERY_PARAMETERS
    )
    return urlunsplit((scheme, netloc, path, urlencode(query_pairs, doseq=True), ""))


def _severity(outcome: FilterOutcome) -> int:
    return {
        FilterOutcome.KEEP: 0,
        FilterOutcome.NOISE_FLAG: 1,
        FilterOutcome.DISCARD_CANDIDATE: 2,
    }[outcome]


def _github_topics(item: RawItem) -> set[str]:
    raw_topics = item.raw_metrics.get("topics")
    if not isinstance(raw_topics, list):
        return set()
    return {
        topic.casefold()
        for topic in raw_topics
        if isinstance(topic, str) and topic.strip()
    }


def _available_descriptive_text(item: RawItem) -> str:
    values = [item.description or ""]
    payload = item.raw_payload if isinstance(item.raw_payload, dict) else {}
    readme = payload.get("readme")
    if isinstance(readme, dict) and isinstance(readme.get("excerpt"), str):
        values.append(readme["excerpt"])
    return " ".join(values)


def _has_structured_description(item: RawItem) -> bool:
    payload = item.raw_payload if isinstance(item.raw_payload, dict) else {}
    readme = payload.get("readme")
    if isinstance(readme, dict) and _has_text(readme.get("excerpt")):
        return True
    post = payload.get("post")
    return isinstance(post, dict) and _has_text(post.get("selftext"))


def _has_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())
