"""Neutral CSV export for human review of raw discovery material."""

from __future__ import annotations

import csv
import json
from collections import Counter, OrderedDict, deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from innovation_radar.models import RawItem, RunRecord
from innovation_radar.storage.sqlite import SQLiteStorage


CSV_FIELDS = (
    "item_id",
    "source",
    "source_surface_or_feed",
    "title",
    "url",
    "published_at",
    "author",
    "short_description",
    "available_metrics",
    "human_label",
    "human_reason",
)
MAX_DESCRIPTION_LENGTH = 500


@dataclass(frozen=True, slots=True)
class ReviewSampleExport:
    csv_path: Path
    summary_path: Path
    item_count: int
    candidate_count: int
    duplicates_avoided: int
    already_reviewed_skipped: int = 0


def write_review_sample(
    storage: SQLiteStorage,
    report_directory: str | Path,
    limit: int,
) -> ReviewSampleExport:
    """Export a bounded, provenance-diverse sample without judging its content."""

    if not 1 <= limit <= 100:
        raise ValueError("review sample limit must be between 1 and 100")

    candidates = storage.list_raw_items()
    if not candidates:
        raise ValueError("no raw items are available for review export")

    unique_candidates, duplicates_avoided = _unique_items(candidates)
    # Review memory: never show an item that already received a human decision.
    reviewed_ids = storage.reviewed_item_ids()
    reviewed_skipped = 0
    if reviewed_ids:
        before = len(unique_candidates)
        unique_candidates = tuple(
            item for item in unique_candidates if item.id not in reviewed_ids
        )
        reviewed_skipped = before - len(unique_candidates)
        if not unique_candidates:
            raise ValueError(
                "all available items were already reviewed; run a new collection "
                "to discover fresh material"
            )
    selected = _round_robin_by_provenance(unique_candidates, limit)
    rows = tuple(_csv_row(item) for item in selected)

    directory = Path(report_directory)
    directory.mkdir(parents=True, exist_ok=True)
    csv_path = directory / "review_sample.csv"
    summary_path = directory / "review_sample_summary.md"

    with csv_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    latest_run = storage.get_latest_run_record()
    reencountered_count = (
        storage.count_reencountered_items(latest_run) if latest_run else 0
    )
    summary_path.write_text(
        _render_summary(
            selected,
            candidate_count=len(unique_candidates),
            duplicates_avoided=duplicates_avoided,
            reencountered_count=reencountered_count,
            already_reviewed_skipped=reviewed_skipped,
            latest_run=latest_run,
        ),
        encoding="utf-8",
    )
    return ReviewSampleExport(
        csv_path=csv_path,
        summary_path=summary_path,
        item_count=len(selected),
        candidate_count=len(unique_candidates),
        duplicates_avoided=duplicates_avoided,
        already_reviewed_skipped=reviewed_skipped,
    )


def _unique_items(items: tuple[RawItem, ...]) -> tuple[tuple[RawItem, ...], int]:
    seen: set[tuple[str, str]] = set()
    unique: list[RawItem] = []
    for item in items:
        identity = (item.source, item.source_item_id)
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(item)
    return tuple(unique), len(items) - len(unique)


def _round_robin_by_provenance(
    items: tuple[RawItem, ...], limit: int
) -> tuple[RawItem, ...]:
    groups: OrderedDict[str, deque[RawItem]] = OrderedDict()
    for item in items:
        groups.setdefault(_primary_provenance(item), deque()).append(item)

    selected: list[RawItem] = []
    while len(selected) < limit:
        added = False
        for group in groups.values():
            if not group:
                continue
            selected.append(group.popleft())
            added = True
            if len(selected) == limit:
                break
        if not added:
            break
    return tuple(selected)


def _primary_provenance(item: RawItem) -> str:
    payload = item.raw_payload if isinstance(item.raw_payload, dict) else {}
    if item.source == "hacker_news":
        surfaces = payload.get("discovery_surfaces")
        if isinstance(surfaces, list) and surfaces:
            return f"{item.source}:{surfaces[0]}"
    if item.source == "rss":
        feed = payload.get("feed")
        if isinstance(feed, dict) and isinstance(feed.get("id"), str):
            return f"{item.source}:{feed['id']}"
    if item.source == "github":
        lenses = payload.get("discovery_lenses")
        if isinstance(lenses, list) and lenses and isinstance(lenses[0], str):
            return f"{item.source}:{lenses[0]}"
    if item.source == "reddit":
        lenses = payload.get("discovery_lenses")
        if isinstance(lenses, list) and lenses and isinstance(lenses[0], str):
            return f"{item.source}:{lenses[0]}"
    return item.source


def _source_detail(item: RawItem) -> str:
    payload = item.raw_payload if isinstance(item.raw_payload, dict) else {}
    if item.source == "hacker_news":
        surfaces = payload.get("discovery_surfaces")
        if isinstance(surfaces, list):
            valid_surfaces = [value for value in surfaces if isinstance(value, str)]
            if valid_surfaces:
                return " | ".join(valid_surfaces)
    if item.source == "rss":
        feed = payload.get("feed")
        if isinstance(feed, dict):
            feed_id = feed.get("id")
            name = feed.get("name")
            if isinstance(feed_id, str) and isinstance(name, str):
                return f"{name} [{feed_id}]"
            if isinstance(feed_id, str):
                return feed_id
    if item.source == "github":
        lenses = payload.get("discovery_lenses")
        if isinstance(lenses, list):
            valid_lenses = [value for value in lenses if isinstance(value, str)]
            if valid_lenses:
                return " | ".join(valid_lenses)
    if item.source == "reddit":
        post = payload.get("post")
        subreddit = post.get("subreddit") if isinstance(post, dict) else None
        lenses = payload.get("discovery_lenses")
        valid_lenses = (
            [value for value in lenses if isinstance(value, str)]
            if isinstance(lenses, list)
            else []
        )
        details: list[str] = []
        if isinstance(subreddit, str) and subreddit:
            details.append(f"r/{subreddit}")
        details.extend(f"lens:{lens}" for lens in valid_lenses)
        if details:
            return " | ".join(details)
    return item.source


def _csv_row(item: RawItem) -> dict[str, str]:
    return {
        "item_id": item.id,
        "source": item.source,
        "source_surface_or_feed": _source_detail(item),
        "title": _one_line(item.title),
        "url": item.url,
        "published_at": _format_datetime(item.published_at),
        "author": _one_line(item.author) if item.author else "",
        "short_description": _review_description(item),
        "available_metrics": json.dumps(
            item.raw_metrics,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        "human_label": "",
        "human_reason": "",
    }


def _review_description(item: RawItem) -> str:
    parts: list[str] = []
    description = _one_line(item.description)
    if description:
        parts.append(description)

    payload = item.raw_payload if isinstance(item.raw_payload, dict) else {}
    readme = payload.get("readme")
    if item.source == "github" and isinstance(readme, dict):
        excerpt = _one_line(readme.get("excerpt"))
        if excerpt and excerpt not in description:
            parts.append(f"README: {excerpt}")
    return _truncate(" ".join(parts))


def _render_summary(
    items: tuple[RawItem, ...],
    candidate_count: int,
    duplicates_avoided: int,
    reencountered_count: int,
    already_reviewed_skipped: int,
    latest_run: RunRecord | None,
) -> str:
    source_counts = Counter(item.source for item in items)
    provenance_counts = Counter(_source_detail(item) for item in items)
    reddit_lens_counts: Counter[str] = Counter()
    reddit_subreddit_counts: Counter[str] = Counter()
    for item in items:
        if item.source != "reddit" or not isinstance(item.raw_payload, dict):
            continue
        lenses = item.raw_payload.get("discovery_lenses")
        if isinstance(lenses, list):
            reddit_lens_counts.update(
                lens for lens in lenses if isinstance(lens, str) and lens
            )
        post = item.raw_payload.get("post")
        subreddit = post.get("subreddit") if isinstance(post, dict) else None
        if isinstance(subreddit, str) and subreddit:
            reddit_subreddit_counts[subreddit] += 1
    published_dates = sorted(
        item.published_at for item in items if item.published_at is not None
    )

    lines = [
        "# Resumo diagnóstico da amostra de revisão",
        "",
        "> Contagens descritivas da matéria-prima. Não contém ranking, classificação ou interpretação automática de qualidade.",
        "",
        f"- Itens candidatos únicos no SQLite (após excluir já revisados): **{candidate_count}**",
        f"- Itens exportados: **{len(items)}**",
        f"- Itens ignorados por já terem sido revisados: **{already_reviewed_skipped}**",
        f"- Reencontros consolidados no SQLite na execução mais recente: **{reencountered_count}**",
        f"- Linhas duplicadas descartadas defensivamente na exportação: **{duplicates_avoided}**",
        f"- Período coberto: **{_covered_period(published_dates)}**",
        "",
        "## Quantidade por fonte",
        "",
        "| Fonte | Itens |",
        "|---|---:|",
    ]
    lines.extend(
        f"| {_table_text(source)} | {count} |"
        for source, count in sorted(source_counts.items())
    )
    lines.extend(
        [
            "",
            "## Quantidade por superfície/feed",
            "",
            "| Superfície/feed | Itens |",
            "|---|---:|",
        ]
    )
    lines.extend(
        f"| {_table_text(provenance)} | {count} |"
        for provenance, count in sorted(provenance_counts.items())
    )
    if reddit_lens_counts:
        lines.extend(
            [
                "",
                "## Reddit por discovery lens",
                "",
                "| Discovery lens | Itens |",
                "|---|---:|",
            ]
        )
        lines.extend(
            f"| `{_table_text(lens)}` | {count} |"
            for lens, count in sorted(reddit_lens_counts.items())
        )
    if reddit_subreddit_counts:
        lines.extend(
            [
                "",
                "## Reddit por subreddit",
                "",
                "| Subreddit | Itens |",
                "|---|---:|",
            ]
        )
        lines.extend(
            f"| `r/{_table_text(subreddit)}` | {count} |"
            for subreddit, count in sorted(reddit_subreddit_counts.items())
        )
    lines.extend(["", "## Falhas da execução mais recente", ""])
    if latest_run is None:
        lines.append("Nenhuma execução registrada no SQLite.")
    elif latest_run.error_message:
        lines.append(
            f"Execução `{_one_line(latest_run.id)}` com status "
            f"`{_one_line(latest_run.status)}`:"
        )
        lines.extend(
            f"- {_one_line(error)}"
            for error in latest_run.error_message.splitlines()
            if error.strip()
        )
    else:
        lines.append(
            f"Nenhuma falha registrada na execução `{_one_line(latest_run.id)}` "
            f"(status `{_one_line(latest_run.status)}`)."
        )
    return "\n".join(lines).rstrip() + "\n"


def _covered_period(values: list[datetime]) -> str:
    if not values:
        return "não disponível"
    return f"{_format_datetime(values[0])} a {_format_datetime(values[-1])}"


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _one_line(value: object | None) -> str:
    return " ".join(str(value or "").split())


def _truncate(value: str, limit: int = MAX_DESCRIPTION_LENGTH) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def _table_text(value: str) -> str:
    return _one_line(value).replace("|", "\\|")
