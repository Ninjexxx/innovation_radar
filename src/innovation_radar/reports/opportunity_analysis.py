"""Markdown report for the M3 Opportunity AI analysis.

The report is a human-facing summary of one analysis run. It is descriptive: the
recommendation is a suggestion, and human review remains the final decision.
"""

from __future__ import annotations

from pathlib import Path

from innovation_radar.analysis.engine import AnalysisReport
from innovation_radar.analysis.models import AnalyzedItem, Recommendation


RECOMMENDATION_TITLES = {
    Recommendation.INVESTIGATE: "Investigar",
    Recommendation.WATCHLIST: "Watchlist",
    Recommendation.ARCHIVE: "Arquivar",
}

SIGNAL_TYPE_TITLES = {
    "new_capability": "Nova capacidade",
    "new_application": "Nova aplicação ou combinação",
    "new_behavior": "Novo comportamento ou necessidade",
    "enabling_testable": "Tecnologia habilitadora e testável",
    "strategic_shift": "Mudança estratégica",
    "unclear": "Indefinido",
}


def write_opportunity_analysis_report(report: AnalysisReport, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_opportunity_analysis_report(report), encoding="utf-8")
    return output_path


def render_opportunity_analysis_report(report: AnalysisReport) -> str:
    recommendation_counts = report.recommendation_counts
    signal_counts = report.signal_type_counts

    lines = [
        "# Opportunity Analysis — M3",
        "",
        "> Análise estruturada de oportunidade sobre itens que sobreviveram ao "
        "filtro determinístico do M2. A recomendação é uma sugestão; a revisão "
        "humana permanece a decisão final. O provedor de IA é substituível e o "
        "default é determinístico e offline.",
        "",
        f"- Provedor utilizado: **`{report.provider_name}`**",
        f"- Itens considerados: **{report.total}**",
        f"- Itens analisados pelo provedor: **{report.analyzed_count}**",
        f"- Itens pulados (`discard_candidate` no M2): **{report.skipped_count}**",
        f"- Marcados como developer tooling: **{report.developer_tooling_count}**",
        "",
        "## Recomendações",
        "",
        f"- Investigar: **{recommendation_counts.get('investigate', 0)}**",
        f"- Watchlist: **{recommendation_counts.get('watchlist', 0)}**",
        f"- Arquivar: **{recommendation_counts.get('archive', 0)}**",
        "",
        "## Distribuição por tipo de sinal",
        "",
    ]
    if signal_counts:
        for signal_value in sorted(signal_counts):
            title = SIGNAL_TYPE_TITLES.get(signal_value, signal_value)
            lines.append(f"- {title} (`{signal_value}`): **{signal_counts[signal_value]}**")
    else:
        lines.append("- Nenhum item analisado.")
    lines.append("")

    for recommendation in (
        Recommendation.INVESTIGATE,
        Recommendation.WATCHLIST,
        Recommendation.ARCHIVE,
    ):
        items = report.by_recommendation(recommendation)
        lines.append(f"## {RECOMMENDATION_TITLES[recommendation]} ({len(items)})")
        lines.append("")
        if not items:
            lines.append("- Nenhum item nesta recomendação.")
            lines.append("")
            continue
        for item in items:
            lines.extend(_render_item(item))

    skipped = tuple(item for item in report.analyzed if not item.analyzed)
    if skipped:
        lines.append(f"## Pulados no filtro determinístico ({len(skipped)})")
        lines.append("")
        for item in skipped:
            lines.append(
                f"- `{item.item_id}` — **{_one_line(item.title)}** "
                f"({_one_line(item.skipped_reason or '')})"
            )
        lines.append("")

    lines.extend(
        [
            "## Confirmações de escopo",
            "",
            "- Apenas itens pós-filtro foram enviados ao provedor.",
            "- O provedor é substituível; nenhuma regra central depende de um "
            "fornecedor específico de IA.",
            "- O pipeline pode rodar sem qualquer chave de API usando o provedor "
            "offline determinístico.",
            "- Nenhum label humano do Gold Set foi alterado; a decisão final "
            "permanece humana.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _render_item(item: AnalyzedItem) -> list[str]:
    analysis = item.analysis
    assert analysis is not None  # analyzed items always carry an analysis
    signal_title = SIGNAL_TYPE_TITLES.get(
        analysis.signal_type.value, analysis.signal_type.value
    )
    scores = (
        f"novelty={analysis.novelty_score}, "
        f"capability={analysis.capability_score}, "
        f"product={analysis.product_score}, "
        f"namu={analysis.namu_score}, "
        f"timing={analysis.timing_score}"
    )
    lines = [
        f"### `{item.item_id}` — {_one_line(item.title)}",
        "",
        f"- Fonte: `{item.source}`",
        f"- Tipo de sinal: {signal_title} (`{analysis.signal_type.value}`)",
        f"- Developer tooling: **{'sim' if analysis.developer_tooling else 'não'}**",
        f"- Tração: `{analysis.traction.value}`",
        f"- Scores (1-5): {scores}",
        f"- Resumo: {_one_line(analysis.summary)}",
        f"- O que há de novo: {_one_line(analysis.what_is_new)}",
        f"- Nova capacidade: {_one_line(analysis.new_capability)}",
        f"- Potencial de produto: {_one_line(analysis.product_possibility)}",
        f"- Relevância Namu: {_one_line(analysis.namu_relevance)}",
    ]
    if analysis.evidence:
        joined = "; ".join(_one_line(entry) for entry in analysis.evidence)
        lines.append(f"- Evidência: {joined}")
    lines.append("")
    return lines


def _one_line(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")
