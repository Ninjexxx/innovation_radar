"""Command-line entry point for foundation and discovery review."""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path

from innovation_radar.analysis import analyze_items, build_provider
from innovation_radar.analysis.calibration import calibrate
from innovation_radar.collectors.github import GitHubCollector
from innovation_radar.collectors.hackernews import HackerNewsCollector
from innovation_radar.collectors.reddit import RedditCollector
from innovation_radar.collectors.rss import RssCollector
from innovation_radar.config import ConfigError, Settings
from innovation_radar.filtering.evaluation import evaluate_gold_set, load_gold_set_cases
from innovation_radar.logging_config import configure_logging
from innovation_radar.pipeline import run_discovery
from innovation_radar.reports.markdown import write_raw_report
from innovation_radar.reports.human_judgment import write_human_judgment_report
from innovation_radar.reports.github_discovery import write_github_discovery_report
from innovation_radar.reports.deterministic_filtering import (
    write_deterministic_filter_report,
)
from innovation_radar.reports.calibration import write_calibration_report
from innovation_radar.reports.opportunity_analysis import (
    write_opportunity_analysis_report,
)
from innovation_radar.reports.review_page import write_review_page
from innovation_radar.reports.review_sample import write_review_sample
from innovation_radar.reviews.gold_set import (
    import_review_workbook,
    merge_github_review_workbook,
)
from innovation_radar.reviews.ingest import ingest_reviewed_csv
from innovation_radar.storage.sqlite import SQLiteStorage


LOGGER = logging.getLogger("innovation_radar.cli")
DEFAULT_GOLD_SET_PATH = Path("tests/fixtures/signal_gold_set.json")
DEFAULT_JUDGMENT_REPORT_PATH = Path("docs/07_HUMAN_JUDGMENT_ANALYSIS.md")
DEFAULT_GITHUB_DISCOVERY_REPORT_PATH = Path("docs/08_GITHUB_DISCOVERY_ANALYSIS.md")
DEFAULT_FILTER_EVALUATION_REPORT_PATH = Path(
    "docs/10_DETERMINISTIC_FILTER_EVALUATION.md"
)
DEFAULT_ANALYSIS_REPORT_PATH = Path("docs/11_OPPORTUNITY_ANALYSIS.md")
DEFAULT_CALIBRATION_REPORT_PATH = Path("docs/12_CALIBRATION.md")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m innovation_radar")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db", help="initialize the configured SQLite database")
    subparsers.add_parser(
        "run", help="collect Hacker News, RSS, GitHub and Reddit and write a raw report"
    )
    subparsers.add_parser(
        "export-review-sample",
        help="export raw SQLite items as a neutral CSV for human review",
    )
    review_page_parser = subparsers.add_parser(
        "export-review-page",
        help="build a static HTML review page from the review CSV",
    )
    review_page_parser.add_argument(
        "--csv-path",
        type=Path,
        default=None,
        help="review CSV path (default: <report-dir>/review_sample.csv)",
    )
    review_page_parser.add_argument(
        "--html-path",
        type=Path,
        default=None,
        help="output HTML path (default: <report-dir>/review.html)",
    )
    mark_reviewed_parser = subparsers.add_parser(
        "mark-reviewed",
        help="record human labels from a labeled CSV so items are not shown again",
    )
    mark_reviewed_parser.add_argument(
        "csv", type=Path, help="labeled review CSV (e.g. review_sample_labeled.csv)"
    )
    import_parser = subparsers.add_parser(
        "import-gold-set",
        help="validate a human-reviewed XLSX and create Gold Set v0.1",
    )
    import_parser.add_argument("workbook", type=Path, help="reviewed XLSX workbook")
    import_parser.add_argument(
        "--expected-count",
        type=int,
        default=90,
        help="required number of reviewed items (default: 90)",
    )
    import_parser.add_argument(
        "--gold-set-path",
        type=Path,
        default=DEFAULT_GOLD_SET_PATH,
        help=f"Gold Set output path (default: {DEFAULT_GOLD_SET_PATH})",
    )
    import_parser.add_argument(
        "--analysis-report-path",
        type=Path,
        default=DEFAULT_JUDGMENT_REPORT_PATH,
        help=f"analysis output path (default: {DEFAULT_JUDGMENT_REPORT_PATH})",
    )
    merge_parser = subparsers.add_parser(
        "merge-github-gold-set",
        help="merge the reviewed GitHub cycle into Gold Set v0.2",
    )
    merge_parser.add_argument(
        "workbook", type=Path, help="review_sample_github.xlsx workbook"
    )
    merge_parser.add_argument(
        "--base-gold-set-path",
        type=Path,
        default=DEFAULT_GOLD_SET_PATH,
        help=f"base Gold Set path (default: {DEFAULT_GOLD_SET_PATH})",
    )
    merge_parser.add_argument(
        "--gold-set-path",
        type=Path,
        default=DEFAULT_GOLD_SET_PATH,
        help=f"Gold Set v0.2 output path (default: {DEFAULT_GOLD_SET_PATH})",
    )
    merge_parser.add_argument(
        "--analysis-report-path",
        type=Path,
        default=DEFAULT_GITHUB_DISCOVERY_REPORT_PATH,
        help=f"GitHub analysis path (default: {DEFAULT_GITHUB_DISCOVERY_REPORT_PATH})",
    )
    filter_parser = subparsers.add_parser(
        "evaluate-filters",
        help="evaluate deterministic shadow filters against Gold Set v0.2",
    )
    filter_parser.add_argument(
        "--gold-set-path",
        type=Path,
        default=DEFAULT_GOLD_SET_PATH,
        help=f"Gold Set input path (default: {DEFAULT_GOLD_SET_PATH})",
    )
    filter_parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_FILTER_EVALUATION_REPORT_PATH,
        help=(
            "evaluation report path "
            f"(default: {DEFAULT_FILTER_EVALUATION_REPORT_PATH})"
        ),
    )
    analyze_parser = subparsers.add_parser(
        "analyze-opportunities",
        help="run M3 opportunity analysis over post-filter items and write a report",
    )
    analyze_parser.add_argument(
        "--source",
        choices=("gold-set", "sqlite"),
        default="gold-set",
        help="items to analyze: the Gold Set fixture or the local SQLite (default: gold-set)",
    )
    analyze_parser.add_argument(
        "--gold-set-path",
        type=Path,
        default=DEFAULT_GOLD_SET_PATH,
        help=f"Gold Set input path when --source=gold-set (default: {DEFAULT_GOLD_SET_PATH})",
    )
    analyze_parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_ANALYSIS_REPORT_PATH,
        help=f"analysis report output path (default: {DEFAULT_ANALYSIS_REPORT_PATH})",
    )
    calibrate_parser = subparsers.add_parser(
        "calibrate",
        help="compare M3 recommendations against Gold Set labels and write a report",
    )
    calibrate_parser.add_argument(
        "--gold-set-path",
        type=Path,
        default=DEFAULT_GOLD_SET_PATH,
        help=f"Gold Set input path (default: {DEFAULT_GOLD_SET_PATH})",
    )
    calibrate_parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_CALIBRATION_REPORT_PATH,
        help=f"calibration report output path (default: {DEFAULT_CALIBRATION_REPORT_PATH})",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)

    try:
        settings = Settings.from_env()
        configure_logging(settings.log_level)

        storage = SQLiteStorage(settings.database_path)
        if arguments.command == "init-db":
            storage.initialize()
            LOGGER.info("SQLite database initialized at %s", settings.database_path)
            return 0
        if arguments.command == "run":
            reddit_collector = RedditCollector(
                settings.reddit_lenses,
                settings.reddit_limit_per_lens,
                settings.reddit_recency_days,
                new_limit_per_subreddit=settings.reddit_new_limit_per_subreddit,
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                user_agent=settings.reddit_user_agent,
            )
            collectors = (
                HackerNewsCollector(settings.hn_limit_per_surface),
                RssCollector(settings.rss_feeds, settings.rss_limit_per_feed),
                GitHubCollector(
                    settings.github_lenses,
                    settings.github_limit_per_lens,
                    settings.github_recency_days,
                    min_stars=settings.github_min_stars,
                    readme_limit=settings.github_readme_limit,
                    token=settings.github_token,
                ),
                reddit_collector,
            )
            result = run_discovery(storage, collectors)
            report_path = write_raw_report(result, settings.report_directory)
            LOGGER.info(
                "Discovery run %s finished with status=%s total=%s new=%s updated=%s",
                result.run_record.id,
                result.run_record.status,
                result.total,
                result.new_count,
                result.updated_count,
            )
            LOGGER.info("Raw Markdown report written to %s", report_path)
            reddit_stats = reddit_collector.collection_stats
            LOGGER.info(
                "Reddit discovery requests=%s candidates=%s unique=%s "
                "duplicates_avoided=%s outside_window=%s selected=%s",
                reddit_stats.requests,
                reddit_stats.observed_candidates,
                reddit_stats.unique_candidates,
                reddit_stats.duplicates_avoided,
                reddit_stats.outside_time_window,
                reddit_stats.selected_items,
            )
            if reddit_collector.rate_limits:
                latest_reddit_limit = reddit_collector.rate_limits[-1]
                LOGGER.info(
                    "Reddit rate limit used=%s remaining=%s reset_seconds=%s",
                    latest_reddit_limit.used,
                    latest_reddit_limit.remaining,
                    latest_reddit_limit.reset,
                )
            for failure in result.failures:
                LOGGER.warning(
                    "Collection failure source=%s context=%s error=%s",
                    failure.source,
                    failure.context,
                    failure.error,
                )
            return 1 if result.run_record.status == "failed" else 0
        if arguments.command == "export-review-sample":
            storage.initialize()
            result = write_review_sample(
                storage,
                settings.report_directory,
                settings.review_sample_limit,
            )
            LOGGER.info(
                "Review sample exported with %s items to %s",
                result.item_count,
                result.csv_path,
            )
            LOGGER.info("Diagnostic sample summary written to %s", result.summary_path)
            return 0
        if arguments.command == "export-review-page":
            csv_path = arguments.csv_path or (
                settings.report_directory / "review_sample.csv"
            )
            html_path = arguments.html_path or (
                settings.report_directory / "review.html"
            )
            page = write_review_page(csv_path, html_path)
            LOGGER.info(
                "Review page written with %s items to %s",
                page.item_count,
                page.html_path,
            )
            return 0
        if arguments.command == "mark-reviewed":
            result = ingest_reviewed_csv(arguments.csv, storage)
            LOGGER.info(
                "Recorded %s reviewed items (%s unlabeled rows skipped); "
                "future samples will exclude them",
                result.ingested_count,
                result.skipped_unlabeled_count,
            )
            LOGGER.info(
                "Total items in review memory: %s", storage.count_reviews()
            )
            return 0
        if arguments.command == "import-gold-set":
            result = import_review_workbook(
                arguments.workbook,
                arguments.gold_set_path,
                expected_count=arguments.expected_count,
            )
            report_path = write_human_judgment_report(
                result.items,
                arguments.analysis_report_path,
            )
            LOGGER.info(
                "Gold Set imported with %s human-reviewed items to %s",
                result.item_count,
                result.output_path,
            )
            LOGGER.info("Human judgment analysis written to %s", report_path)
            return 0
        if arguments.command == "merge-github-gold-set":
            result = merge_github_review_workbook(
                arguments.workbook,
                arguments.base_gold_set_path,
                arguments.gold_set_path,
            )
            report_path = write_github_discovery_report(
                result.github_items,
                result.previous_items,
                arguments.analysis_report_path,
                excluded_non_github_count=result.excluded_item_count,
            )
            LOGGER.info(
                "Gold Set v0.2 written with %s items (%s GitHub, %s added) to %s",
                result.item_count,
                result.github_item_count,
                result.added_item_count,
                result.output_path,
            )
            LOGGER.info(
                "Excluded %s non-GitHub reviewed rows from this merge",
                result.excluded_item_count,
            )
            LOGGER.info("GitHub discovery analysis written to %s", report_path)
            return 0
        if arguments.command == "evaluate-filters":
            evaluation = evaluate_gold_set(arguments.gold_set_path)
            report_path = write_deterministic_filter_report(
                evaluation, arguments.report_path
            )
            LOGGER.info(
                "Deterministic filters evaluated in shadow mode against %s items",
                evaluation.total,
            )
            LOGGER.info(
                "Filter outcomes discard_candidate=%s noise_flag=%s keep=%s",
                evaluation.shadow_report.discard_candidate_count,
                evaluation.shadow_report.noise_flag_count,
                evaluation.shadow_report.keep_count,
            )
            LOGGER.info("Filter evaluation written to %s", report_path)
            return 0
        if arguments.command == "analyze-opportunities":
            if arguments.source == "gold-set":
                cases = load_gold_set_cases(arguments.gold_set_path)
                items = tuple(case.item for case in cases)
            else:
                storage.initialize()
                items = storage.list_raw_items()
            provider = build_provider(settings.analysis_provider)
            report = analyze_items(items, provider)
            report_path = write_opportunity_analysis_report(
                report, arguments.report_path
            )
            LOGGER.info(
                "Opportunity analysis provider=%s considered=%s analyzed=%s skipped=%s",
                report.provider_name,
                report.total,
                report.analyzed_count,
                report.skipped_count,
            )
            LOGGER.info(
                "Recommendations investigate=%s watchlist=%s archive=%s",
                report.recommendation_counts.get("investigate", 0),
                report.recommendation_counts.get("watchlist", 0),
                report.recommendation_counts.get("archive", 0),
            )
            LOGGER.info("Opportunity analysis report written to %s", report_path)
            return 0
        if arguments.command == "calibrate":
            cases = load_gold_set_cases(arguments.gold_set_path)
            provider = build_provider(settings.analysis_provider)
            result = calibrate(cases, provider)
            report_path = write_calibration_report(result, arguments.report_path)
            LOGGER.info(
                "Calibration provider=%s total=%s agreement=%s (%.1f%%)",
                result.provider_name,
                result.total,
                result.agreement_count,
                result.agreement_rate * 100,
            )
            LOGGER.info(
                "Divergences false_positives=%s false_negatives=%s maybe=%s",
                len(result.false_positives),
                len(result.false_negatives),
                len(result.maybe_divergences),
            )
            LOGGER.info("Calibration report written to %s", report_path)
            return 0
    except (ConfigError, OSError, sqlite3.Error, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    parser.error(f"unsupported command: {arguments.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
