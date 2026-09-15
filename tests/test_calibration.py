import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from innovation_radar.analysis.calibration import (
    LABEL_TO_RECOMMENDATION,
    calibrate,
)
from innovation_radar.analysis.models import (
    OpportunityAnalysis,
    Recommendation,
    SignalType,
    Traction,
)
from innovation_radar.analysis.provider import ProviderContext
from innovation_radar.config import DATABASE_PATH_ENV
from innovation_radar.filtering.evaluation import GoldSetCase, load_gold_set_cases
from innovation_radar.models import RawItem
from innovation_radar.reports.calibration import render_calibration_report


NOW = datetime(2026, 8, 27, 12, tzinfo=timezone.utc)
GOLD_SET_PATH = Path(__file__).parent / "fixtures" / "signal_gold_set.json"


def _case(
    item_id: str,
    *,
    label: str,
    source: str = "hacker_news",
    url: str | None = None,
    description: str = "A detailed, useful description with enough context here.",
) -> GoldSetCase:
    return GoldSetCase(
        item=RawItem(
            id=item_id,
            source=source,
            source_item_id=item_id,
            title=f"Title for {item_id}",
            url=url or f"https://example.com/{item_id}",
            description=description,
            first_seen_at=NOW,
            collected_at=NOW,
        ),
        source_surface_or_feed="newstories",
        human_label=label,
        human_reason=f"reason for {item_id}",
    )


class _FixedProvider:
    """Provider that always returns the same recommendation for testing."""

    name = "fixed"

    def __init__(self, recommendation: Recommendation) -> None:
        self._recommendation = recommendation

    def analyze(self, context: ProviderContext) -> OpportunityAnalysis:
        return OpportunityAnalysis(
            signal_type=SignalType.NEW_APPLICATION,
            summary="s",
            what_is_new="w",
            new_capability="c",
            product_possibility="p",
            namu_relevance="n",
            developer_tooling=False,
            novelty_score=3,
            capability_score=3,
            product_score=3,
            namu_score=3,
            timing_score=3,
            traction=Traction.UNKNOWN,
            recommendation=self._recommendation,
            evidence=("e",),
        )


def test_label_mapping_is_complete() -> None:
    assert set(LABEL_TO_RECOMMENDATION) == {"interesting", "maybe", "irrelevant"}


def test_agreement_when_provider_matches_labels() -> None:
    # Provider always says investigate; only interesting items agree.
    cases = (
        _case("hn:1", label="interesting"),
        _case("hn:2", label="irrelevant"),
    )
    result = calibrate(cases, _FixedProvider(Recommendation.INVESTIGATE))
    assert result.total == 2
    assert result.agreement_count == 1  # the interesting one
    # The irrelevant item recommended for attention is a false positive.
    assert len(result.false_positives) == 1
    assert result.false_positives[0].item_id == "hn:2"


def test_false_negative_when_interesting_is_archived() -> None:
    cases = (_case("hn:3", label="interesting"),)
    result = calibrate(cases, _FixedProvider(Recommendation.ARCHIVE))
    assert len(result.false_negatives) == 1
    assert result.false_negatives[0].item_id == "hn:3"
    assert len(result.false_positives) == 0


def test_maybe_divergence_counted() -> None:
    cases = (_case("hn:4", label="maybe"),)
    # investigate != watchlist -> maybe divergence, and not a FP (label not irrelevant)
    result = calibrate(cases, _FixedProvider(Recommendation.INVESTIGATE))
    assert len(result.maybe_divergences) == 1
    assert len(result.false_positives) == 0


def test_skipped_discard_candidate_counts_as_archive_false_negative() -> None:
    # Two items sharing a canonical URL: the second becomes discard_candidate (M2)
    # and is skipped by M3, so its effective decision is archive.
    shared = "https://example.com/shared"
    cases = (
        _case("hn:5", label="irrelevant", url=shared),
        _case("hn:6", label="interesting", url=shared),
    )
    result = calibrate(cases, _FixedProvider(Recommendation.INVESTIGATE))
    skipped = [case for case in result.cases if case.skipped_by_filter]
    assert len(skipped) == 1
    assert skipped[0].item_id == "hn:6"
    # Skipped interesting item -> archived effectively -> false negative.
    assert any(fn.item_id == "hn:6" for fn in result.false_negatives)


def test_confusion_matrix_totals_match() -> None:
    cases = (
        _case("hn:7", label="interesting"),
        _case("hn:8", label="maybe"),
        _case("hn:9", label="irrelevant"),
    )
    result = calibrate(cases, _FixedProvider(Recommendation.WATCHLIST))
    matrix = result.confusion_matrix
    total = sum(sum(row.values()) for row in matrix.values())
    assert total == 3


def test_calibration_is_deterministic_over_gold_set() -> None:
    cases = load_gold_set_cases(GOLD_SET_PATH)
    first = calibrate(cases)
    second = calibrate(cases)
    assert first.total == 130
    assert first.agreement_count == second.agreement_count
    assert len(first.false_positives) == len(second.false_positives)
    assert len(first.false_negatives) == len(second.false_negatives)


def test_report_renders_expected_sections() -> None:
    cases = (
        _case("hn:10", label="interesting"),
        _case("hn:11", label="irrelevant"),
    )
    result = calibrate(cases, _FixedProvider(Recommendation.INVESTIGATE))
    rendered = render_calibration_report(result)
    assert "# Calibration — M4" in rendered
    assert "Matriz de confusão" in rendered
    assert "Falsos negativos" in rendered
    assert "Falsos positivos" in rendered
    assert "decisão final permanece humana" in rendered


def test_calibrate_cli(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    report_path = tmp_path / "calibration.md"
    database_path = tmp_path / "cli.sqlite3"
    environment = os.environ.copy()
    environment[DATABASE_PATH_ENV] = str(database_path)
    environment["PYTHONPATH"] = str(project_root / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "innovation_radar",
            "calibrate",
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
    assert "Calibration — M4" in report_path.read_text(encoding="utf-8")
    assert "total=130" in result.stderr
