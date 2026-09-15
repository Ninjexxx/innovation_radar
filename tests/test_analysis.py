import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from innovation_radar.analysis import (
    HeuristicProvider,
    OpportunityProvider,
    analyze_items,
    build_provider,
)
from innovation_radar.analysis.engine import analyze_items as engine_analyze_items
from innovation_radar.analysis.models import (
    AnalyzedItem,
    OpportunityAnalysis,
    Recommendation,
    SignalType,
    Traction,
)
from innovation_radar.analysis.provider import ProviderContext
from innovation_radar.config import ANALYSIS_PROVIDER_ENV, DATABASE_PATH_ENV, Settings
from innovation_radar.filtering.evaluation import load_gold_set_cases
from innovation_radar.models import RawItem
from innovation_radar.reports.opportunity_analysis import (
    render_opportunity_analysis_report,
)


NOW = datetime(2026, 8, 27, 12, tzinfo=timezone.utc)
GOLD_SET_PATH = Path(__file__).parent / "fixtures" / "signal_gold_set.json"


def _item(
    item_id: str,
    *,
    source: str = "hacker_news",
    source_item_id: str | None = None,
    title: str | None = None,
    url: str | None = None,
    description: str | None = "Useful and detailed context describing the item well.",
    metrics: dict | None = None,
    payload: dict | None = None,
) -> RawItem:
    return RawItem(
        id=item_id,
        source=source,
        source_item_id=source_item_id or item_id,
        title=title or f"Title for {item_id}",
        url=url or f"https://example.com/{item_id}",
        description=description,
        first_seen_at=NOW,
        collected_at=NOW,
        raw_metrics=metrics or {},
        raw_payload=payload,
    )


# --- models ----------------------------------------------------------------


def _valid_analysis(**overrides) -> OpportunityAnalysis:
    base = dict(
        signal_type=SignalType.NEW_CAPABILITY,
        summary="A summary.",
        what_is_new="Something new.",
        new_capability="A capability.",
        product_possibility="A product path.",
        namu_relevance="A relevance note.",
        developer_tooling=False,
        novelty_score=3,
        capability_score=3,
        product_score=3,
        namu_score=3,
        timing_score=3,
        traction=Traction.UNKNOWN,
        recommendation=Recommendation.WATCHLIST,
        evidence=("Some evidence.",),
    )
    base.update(overrides)
    return OpportunityAnalysis(**base)


def test_opportunity_analysis_rejects_out_of_range_score() -> None:
    with pytest.raises(ValueError):
        _valid_analysis(novelty_score=6)


def test_opportunity_analysis_rejects_bool_score() -> None:
    with pytest.raises(ValueError):
        _valid_analysis(capability_score=True)


def test_opportunity_analysis_roundtrips_through_mapping() -> None:
    analysis = _valid_analysis()
    restored = OpportunityAnalysis.from_mapping(analysis.to_dict())
    assert restored == analysis


def test_from_mapping_rejects_invalid_enum() -> None:
    payload = _valid_analysis().to_dict()
    payload["recommendation"] = "delete"
    with pytest.raises(ValueError):
        OpportunityAnalysis.from_mapping(payload)


def test_analyzed_item_requires_reason_when_skipped() -> None:
    with pytest.raises(ValueError):
        AnalyzedItem(item_id="x:1", title="t", source="s", analysis=None)


# --- provider --------------------------------------------------------------


def test_heuristic_provider_is_deterministic() -> None:
    provider = HeuristicProvider()
    context = ProviderContext.from_raw_item(
        _item("hn:1", title="A new on-device capability that enables local health tracking")
    )
    first = provider.analyze(context)
    second = provider.analyze(context)
    assert first == second


def test_heuristic_provider_detects_developer_tooling() -> None:
    provider = HeuristicProvider()
    context = ProviderContext.from_raw_item(
        _item("hn:2", title="A new SDK and framework wrapper for developers")
    )
    analysis = provider.analyze(context)
    assert analysis.developer_tooling is True


def test_heuristic_provider_archives_noise() -> None:
    provider = HeuristicProvider()
    context = ProviderContext.from_raw_item(
        _item("hn:3", title="Top 10 best tools trends to watch", description="")
    )
    analysis = provider.analyze(context)
    assert analysis.recommendation is Recommendation.ARCHIVE


def test_heuristic_provider_conforms_to_protocol() -> None:
    assert isinstance(HeuristicProvider(), OpportunityProvider)


def test_build_provider_default_and_unknown() -> None:
    assert isinstance(build_provider("heuristic-offline"), HeuristicProvider)
    with pytest.raises(ValueError):
        build_provider("mystery-model")


# --- engine ----------------------------------------------------------------


def test_engine_skips_discard_candidates_only() -> None:
    duplicate_url = "https://example.com/shared"
    items = (
        _item("hn:a", url=duplicate_url),
        _item("hn:b", url=duplicate_url),  # duplicate canonical URL -> discard_candidate
    )
    report = analyze_items(items)
    assert report.total == 2
    assert report.analyzed_count == 1
    assert report.skipped_count == 1
    skipped = [item for item in report.analyzed if not item.analyzed]
    assert skipped[0].item_id == "hn:b"
    assert "discard_candidate" in (skipped[0].skipped_reason or "")


def test_engine_accepts_custom_provider() -> None:
    class ConstantProvider:
        name = "constant"

        def analyze(self, context: ProviderContext) -> OpportunityAnalysis:
            return _valid_analysis(recommendation=Recommendation.INVESTIGATE)

    report = engine_analyze_items((_item("hn:c"),), ConstantProvider())
    assert report.provider_name == "constant"
    assert report.recommendation_counts.get("investigate") == 1


def test_engine_runs_over_gold_set_without_dropping_items() -> None:
    cases = load_gold_set_cases(GOLD_SET_PATH)
    items = tuple(case.item for case in cases)
    report = analyze_items(items)
    assert report.total == 130
    # 8 discard_candidate items from M2 must be skipped, not analyzed.
    assert report.skipped_count == 8
    assert report.analyzed_count == 122
    assert sum(report.recommendation_counts.values()) == 122


# --- report ----------------------------------------------------------------


def test_report_renders_expected_sections() -> None:
    report = analyze_items((_item("hn:d"),))
    rendered = render_opportunity_analysis_report(report)
    assert "# Opportunity Analysis — M3" in rendered
    assert "heuristic-offline" in rendered
    assert "## Recomendações" in rendered
    assert "revisão humana permanece a decisão final" in rendered


# --- config ----------------------------------------------------------------


def test_settings_default_analysis_provider() -> None:
    settings = Settings.from_env({})
    assert settings.analysis_provider == "heuristic-offline"


def test_settings_rejects_unknown_analysis_provider() -> None:
    with pytest.raises(ValueError):
        Settings.from_env({ANALYSIS_PROVIDER_ENV: "gpt-does-not-exist"})


# --- cli -------------------------------------------------------------------


def test_analyze_opportunities_cli(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    report_path = tmp_path / "analysis.md"
    database_path = tmp_path / "cli.sqlite3"
    environment = os.environ.copy()
    environment[DATABASE_PATH_ENV] = str(database_path)
    environment["PYTHONPATH"] = str(project_root / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "innovation_radar",
            "analyze-opportunities",
            "--source",
            "gold-set",
            "--gold-set-path",
            str(GOLD_SET_PATH),
            "--report-path",
            str(report_path),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert report_path.is_file()
    assert "Opportunity Analysis — M3" in report_path.read_text(encoding="utf-8")
    assert "analyzed=122" in result.stderr
