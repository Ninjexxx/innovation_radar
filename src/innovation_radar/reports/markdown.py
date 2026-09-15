"""Diagnostic Markdown report for raw discovery material."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from innovation_radar.filtering.deterministic import FilterDecision
from innovation_radar.models import RawItem
from innovation_radar.pipeline import DiscoveryResult


DEFAULT_SAMPLE_LIMIT = 50
MAX_DESCRIPTION_LENGTH = 800


def write_raw_report(
    result: DiscoveryResult,
    report_directory: str | Path,
    sample_limit: int = DEFAULT_SAMPLE_LIMIT,
) -> Path:
    directory = Path(report_directory)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = result.run_record.started_at.strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"raw_{timestamp}_{result.run_record.id[:8]}.md"
    path.write_text(render_raw_report(result, sample_limit), encoding="utf-8")
    return path


def render_raw_report(
    result: DiscoveryResult, sample_limit: int = DEFAULT_SAMPLE_LIMIT
) -> str:
    if sample_limit < 1:
        raise ValueError("sample_limit must be positive")

    run = result.run_record
    lines = [
        "# Relatório bruto de descoberta",
        "",
        "> Relatório diagnóstico em ordem de coleta. Não contém ranking ou análise de oportunidade. Descrições longas são exibidas como trechos; o payload completo permanece no SQLite.",
        "",
        f"- Execução: `{_one_line(run.id)}`",
        f"- Início: `{_format_datetime(run.started_at)}`",
        f"- Fim: `{_format_datetime(run.finished_at)}`",
        f"- Status: `{_one_line(run.status)}`",
        f"- Total coletado: **{result.total}**",
        f"- Novos itens: **{result.new_count}**",
        f"- Itens conhecidos/atualizados: **{result.updated_count}**",
        "",
        "## Quantidade por fonte",
        "",
        "| Fonte | Total | Novos | Atualizados |",
        "|---|---:|---:|---:|",
    ]
    if result.source_stats:
        lines.extend(
            f"| {_table_text(stats.source)} | {stats.total} | {stats.new} | {stats.updated} |"
            for stats in result.source_stats
        )
    else:
        lines.append("| — | 0 | 0 | 0 |")

    filters = result.filter_report
    lines.extend(
        [
            "",
            "## Filtros determinísticos — shadow mode",
            "",
            "> Decisões derivadas e explicáveis. Nenhum item foi removido ou "
            "alterado; todos permanecem no pipeline e no SQLite.",
            "",
            f"- `discard_candidate`: **{filters.discard_candidate_count}**",
            f"- `noise_flag`: **{filters.noise_flag_count}**",
            f"- `keep`: **{filters.keep_count}**",
        ]
    )

    lines.extend(["", "## Falhas de coleta", ""])
    if result.failures:
        lines.extend(
            f"- `{_one_line(failure.source)}` / `{_one_line(failure.context)}`: "
            f"{_one_line(failure.error)}"
            for failure in result.failures
        )
    else:
        lines.append("Nenhuma falha registrada.")

    shown_items = result.items[:sample_limit]
    shown_decisions = result.filter_report.decisions[:sample_limit]
    lines.extend(
        [
            "",
            "## Itens coletados",
            "",
            f"Exibindo {len(shown_items)} de {result.total} itens, na ordem de coleta.",
            "",
        ]
    )
    if not shown_items:
        lines.append("Nenhum item coletado.")
    for index, (item, decision) in enumerate(
        zip(shown_items, shown_decisions, strict=True), start=1
    ):
        lines.extend(_render_item(index, item, decision))

    return "\n".join(lines).rstrip() + "\n"


def _render_item(
    index: int, item: RawItem, decision: FilterDecision
) -> list[str]:
    metrics = (
        json.dumps(item.raw_metrics, ensure_ascii=False, sort_keys=True)
        if item.raw_metrics
        else "—"
    )
    safe_metrics = metrics.replace("`", "\\`")
    description = (
        _truncate(_one_line(item.description), MAX_DESCRIPTION_LENGTH)
        if item.description
        else "—"
    )
    lines = [
        f"### {index}. {_heading_text(item.title)}",
        "",
        f"- Fonte: `{_one_line(item.source)}`",
        f"- URL: <{item.url.replace('>', '%3E')}>",
        f"- Publicação: `{_format_datetime(item.published_at)}`",
        f"- Autor: {_one_line(item.author) if item.author else '—'}",
        f"- Métricas: `{safe_metrics}`",
        f"- Descrição original: {description}",
    ]
    lines.append(f"- Resultado do filtro shadow: `{decision.outcome.value}`")
    for result in decision.rule_results:
        evidence = json.dumps(
            result.evidence,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).replace("`", "\\`")
        lines.append(
            f"  - `{_one_line(result.rule_id)}`: {_one_line(result.reason)} "
            f"— evidência: `{evidence}`"
        )
    lines.append("")
    return lines


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _one_line(value: object) -> str:
    return " ".join(str(value).split())


def _heading_text(value: str) -> str:
    return _one_line(value).replace("#", "\\#")


def _table_text(value: str) -> str:
    return _one_line(value).replace("|", "\\|")


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"
