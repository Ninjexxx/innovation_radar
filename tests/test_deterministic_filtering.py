import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from innovation_radar.collectors.base import CollectionBatch
from innovation_radar.filtering.deterministic import (
    FilterOutcome,
    canonicalize_url,
    evaluate_in_shadow,
)
from innovation_radar.filtering.evaluation import evaluate_gold_set
from innovation_radar.models import RawItem
from innovation_radar.pipeline import run_discovery
from innovation_radar.reports.deterministic_filtering import (
    render_deterministic_filter_report,
)
from innovation_radar.storage.sqlite import SQLiteStorage


NOW = datetime(2026, 8, 27, 12, tzinfo=timezone.utc)
GOLD_SET_PATH = Path(__file__).parent / "fixtures" / "signal_gold_set.json"


def _item(
    item_id: str,
    *,
    source: str = "hacker_news",
    source_item_id: str | None = None,
    url: str | None = None,
    description: str | None = "Useful context.",
    author: str | None = "fixture-owner",
    metrics: dict | None = None,
    payload: dict | None = None,
) -> RawItem:
    return RawItem(
        id=item_id,
        source=source,
        source_item_id=source_item_id or item_id,
        title=f"Title for {item_id}",
        url=url or f"https://example.com/{item_id}",
        description=description,
        author=author,
        first_seen_at=NOW,
        collected_at=NOW,
        raw_metrics=metrics or {},
        raw_payload=payload,
    )


def _rule_ids(report, index: int) -> set[str]:
    return {result.rule_id for result in report.decisions[index].rule_results}


def test_detects_exact_identity_canonical_url_and_github_id_duplicates() -> None:
    items = (
        _item(
            "hn:first",
            source_item_id="same-external-id",
            url="https://example.com/path?b=2&utm_source=test&a=1#fragment",
        ),
        _item(
            "hn:external-copy",
            source_item_id="same-external-id",
            url="https://example.com/other",
        ),
        _item(
            "rss:url-copy",
            source="rss",
            source_item_id="rss-copy",
            url="https://EXAMPLE.com/path?a=1&b=2",
        ),
        _item(
            "github:first",
            source="github",
            source_item_id="1234",
            url="https://github.com/org/project",
        ),
        _item(
            "github:id-copy",
            source="github",
            source_item_id="1234",
            url="https://github.com/org/project-renamed",
        ),
    )

    report = evaluate_in_shadow(items)

    assert "duplicate_external_identity" in _rule_ids(report, 1)
    assert "duplicate_canonical_url" in _rule_ids(report, 2)
    assert "duplicate_external_identity" in _rule_ids(report, 4)
    assert "duplicate_github_repository_id" in _rule_ids(report, 4)
    assert report.discard_candidate_count == 3


def test_canonical_url_preserves_meaningful_query_parameters() -> None:
    first = canonicalize_url("https://youtube.com/watch?v=first")
    second = canonicalize_url("https://youtube.com/watch?v=second")

    assert first != second
    assert canonicalize_url("https://example.com:443/a/?utm_medium=rss&x=1#top") == (
        "https://example.com/a?x=1"
    )


def test_github_profile_and_catalog_rules_use_content_not_owner() -> None:
    explicit_profile = _item(
        "github:explicit",
        source="github",
        source_item_id="1",
        description="This is not our API. Independent, third-party profile.",
        author="unrelated-owner",
        metrics={"language": None, "topics": ["apis-json"]},
    )
    catalog = _item(
        "github:catalog",
        source="github",
        source_item_id="2",
        author="another-owner",
        metrics={"language": None, "topics": ["company", "apis-json"]},
    )
    owner_only = _item(
        "github:owner-only",
        source="github",
        source_item_id="3",
        author="api-evangelist",
        metrics={"language": "Python", "topics": []},
    )

    report = evaluate_in_shadow((explicit_profile, catalog, owner_only))

    assert report.decisions[0].outcome is FilterOutcome.DISCARD_CANDIDATE
    assert "github_explicit_profile_disclaimer" in _rule_ids(report, 0)
    assert report.decisions[1].outcome is FilterOutcome.DISCARD_CANDIDATE
    assert "github_company_catalog_signature" in _rule_ids(report, 1)
    assert report.decisions[2].outcome is FilterOutcome.KEEP
    assert _rule_ids(report, 2) == {"no_noise_detected"}


def test_broad_github_api_metadata_signature_is_only_a_noise_flag() -> None:
    item = _item(
        "github:metadata",
        source="github",
        source_item_id="4",
        metrics={"language": None, "topics": ["apis-json", "clinical-trials"]},
    )

    decision = evaluate_in_shadow((item,)).decisions[0]

    assert decision.outcome is FilterOutcome.NOISE_FLAG
    assert _rule_ids(evaluate_in_shadow((item,)), 0) == {
        "github_api_metadata_profile"
    }


def test_insufficient_description_flags_but_structured_context_prevents_flag() -> None:
    missing = _item("missing", description=None, payload={"score": 1})
    with_readme = _item(
        "with-readme",
        source="github",
        source_item_id="5",
        description=None,
        payload={"readme": {"excerpt": "Runnable project instructions."}},
    )

    report = evaluate_in_shadow((missing, with_readme))

    assert report.decisions[0].outcome is FilterOutcome.NOISE_FLAG
    assert "insufficient_description" in _rule_ids(report, 0)
    assert report.decisions[1].outcome is FilterOutcome.KEEP


def test_archived_repository_is_flagged_not_discarded() -> None:
    item = _item(
        "github:archived",
        source="github",
        source_item_id="6",
        metrics={"archived": True, "language": "Python", "topics": []},
    )

    decision = evaluate_in_shadow((item,)).decisions[0]

    assert decision.outcome is FilterOutcome.NOISE_FLAG
    assert "github_archived_repository" in {
        result.rule_id for result in decision.rule_results
    }


def test_multiple_lenses_are_registered_as_consolidated_keep() -> None:
    item = _item(
        "github:multi-lens",
        source="github",
        source_item_id="7",
        payload={"discovery_lenses": ["local", "health", "local"]},
    )

    decision = evaluate_in_shadow((item,)).decisions[0]

    assert decision.outcome is FilterOutcome.KEEP
    assert decision.rule_results[0].rule_id == "consolidated_multiple_lenses"
    assert decision.rule_results[0].evidence == {
        "discovery_lenses": ["local", "health"]
    }


def test_results_are_explainable_deterministic_and_non_destructive() -> None:
    raw_payload = {"nested": {"value": 1}}
    item = _item("missing", description=None, payload=raw_payload)
    before = json.dumps(raw_payload, sort_keys=True)

    first = evaluate_in_shadow((item,))
    second = evaluate_in_shadow((item,))

    assert first == second
    assert first.shadow_mode is True
    assert first.items == (item,)
    assert first.items[0] is item
    assert len(first.items) == len(first.decisions) == 1
    assert json.dumps(raw_payload, sort_keys=True) == before
    finding = first.decisions[0].rule_results[0]
    assert finding.rule_id
    assert finding.reason
    assert finding.evidence


class CatalogCollector:
    name = "github"

    def collect(self, collected_at: datetime) -> CollectionBatch:
        return CollectionBatch(
            items=(
                _item(
                    "github:persisted-catalog",
                    source="github",
                    source_item_id="8",
                    metrics={
                        "language": None,
                        "topics": ["apis-json", "company"],
                    },
                ),
            )
        )


class SequenceClock:
    def __init__(self) -> None:
        self.values = iter(
            (
                datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc),
                datetime(2026, 8, 27, 12, 1, tzinfo=timezone.utc),
                datetime(2026, 8, 27, 12, 2, tzinfo=timezone.utc),
            )
        )

    def __call__(self) -> datetime:
        return next(self.values)


def test_pipeline_persists_raw_item_before_shadow_decision(tmp_path: Path) -> None:
    storage = SQLiteStorage(tmp_path / "shadow.sqlite3")

    result = run_discovery(
        storage,
        (CatalogCollector(),),
        clock=SequenceClock(),
        run_id="shadow-run",
    )

    assert result.filter_report.discard_candidate_count == 1
    assert result.total == 1
    assert storage.count_raw_items() == 1
    stored = storage.get_raw_item("github:persisted-catalog")
    assert stored is not None
    assert stored.raw_metrics["topics"] == ["apis-json", "company"]


def test_gold_set_evaluation_has_expected_safe_outcomes() -> None:
    evaluation = evaluate_gold_set(GOLD_SET_PATH)
    outcomes = evaluation.outcome_label_counts

    assert evaluation.total == 130
    assert evaluation.label_counts == {
        "irrelevant": 77,
        "maybe": 26,
        "interesting": 27,
    }
    assert evaluation.shadow_report.discard_candidate_count == 8
    assert evaluation.shadow_report.noise_flag_count == 48
    assert evaluation.shadow_report.keep_count == 74
    assert outcomes[FilterOutcome.DISCARD_CANDIDATE] == {"irrelevant": 8}
    assert evaluation.interesting_discard_candidates == 0
    assert evaluation.maybe_discard_candidates == 0

    by_rule = {rule.rule_id: rule for rule in evaluation.rule_evaluations}
    assert by_rule["github_explicit_profile_disclaimer"].safe_discard_observed
    assert by_rule["github_company_catalog_signature"].safe_discard_observed
    assert by_rule["github_api_metadata_profile"].label_counts == {
        "irrelevant": 10,
        "maybe": 1,
    }
    assert by_rule["insufficient_description"].label_counts == {
        "irrelevant": 33,
        "maybe": 8,
        "interesting": 4,
    }


def test_gold_set_report_is_deterministic_and_records_safety() -> None:
    evaluation = evaluate_gold_set(GOLD_SET_PATH)

    first = render_deterministic_filter_report(evaluation)
    second = render_deterministic_filter_report(evaluation)

    assert first == second
    assert "Redução potencial observada: **6.2%**" in first
    assert "`interesting` entre os candidatos a descarte: **0**" in first
    assert "`maybe` entre os candidatos a descarte: **0**" in first
    assert "Descrição ausente como descarte" in first
    assert "Nenhum LLM" in first


def test_evaluate_filters_cli_writes_report(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    output = tmp_path / "filter-evaluation.md"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(project_root / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "innovation_radar",
            "evaluate-filters",
            "--gold-set-path",
            str(GOLD_SET_PATH),
            "--report-path",
            str(output),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output.is_file()
    assert "discard_candidate=8 noise_flag=48 keep=74" in result.stderr
