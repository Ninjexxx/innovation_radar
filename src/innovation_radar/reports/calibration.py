"""Markdown divergence report for the M4 calibration.

Descriptive only: it compares the system recommendation with the human label and
surfaces divergences for human calibration. It does not change labels, rules or
prompts, and it never claims the automatic decision is correct.
"""

from __future__ import annotations

from pathlib import Path

from innovation_radar.analysis.calibration import (
    CalibrationCase,
    CalibrationResult,
    CategoryBreakdown,
)


def write_calibration_report(result: CalibrationResult, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_calibration_report(result), encoding="utf-8")
    return output_path


def render_calibration_report(result: CalibrationResult) -> str:
    labels = result.label_counts
    false_positives = result.false_positives
    false_negatives = result.false_negatives
    maybe_divergences = result.maybe_divergences

    lines = [
        "# Calibration — M4",
        "",
        "> Comparação entre a recomendação do M3 e o label humano do Gold Set "
        "v0.2. O objetivo é medir divergências, não validar o sistema como "
        "correto. Nenhum label humano, regra, prompt ou política é alterado. A "
        "decisão final permanece humana.",
        "",
        "## Mapeamento label ↔ recomendação",
        "",
        "- `interesting` ↔ `investigate`",
        "- `maybe` ↔ `watchlist`",
        "- `irrelevant` ↔ `archive`",
        "",
        "Itens pulados pelo filtro determinístico (M2) nunca chegaram ao provedor; "
        "sua decisão efetiva é tratada como `archive`.",
        "",
        "## Métricas globais",
        "",
        f"- Provedor avaliado: **`{result.provider_name}`**",
        f"- Total comparado: **{result.total}**",
        f"- Distribuição humana: **{labels.get('interesting', 0)} interesting**, "
        f"**{labels.get('maybe', 0)} maybe**, **{labels.get('irrelevant', 0)} irrelevant**",
        f"- Concordância exata (mesma categoria): **{result.agreement_count}** "
        f"({_percent(result.agreement_rate)})",
        f"- Falsos positivos (sistema pede atenção, humano marcou `irrelevant`): "
        f"**{len(false_positives)}**",
        f"- Falsos negativos (sistema arquiva, humano marcou `interesting`): "
        f"**{len(false_negatives)}**",
        f"- Divergências em `maybe`: **{len(maybe_divergences)}**",
        "",
        "As métricas descrevem apenas os 130 itens do Gold Set e o provedor "
        "avaliado. Elas não são previsão para coletas futuras nem uma nota de "
        "qualidade absoluta.",
        "",
        "## Matriz de confusão",
        "",
        "Linhas: label humano. Colunas: categoria equivalente à recomendação do sistema.",
        "",
        "| Humano ↓ / Sistema → | investigate | watchlist | archive | Total |",
        "|---|---:|---:|---:|---:|",
    ]
    matrix = result.confusion_matrix
    for human_label in ("interesting", "maybe", "irrelevant"):
        row = matrix.get(human_label, {})
        investigate = row.get("interesting", 0)
        watchlist = row.get("maybe", 0)
        archive = row.get("irrelevant", 0)
        total = investigate + watchlist + archive
        lines.append(
            f"| `{human_label}` | {investigate} | {watchlist} | {archive} | {total} |"
        )
    lines.append("")

    lines.extend(
        _priority_section(
            "Prioridade 1 — Falsos negativos (não perder sinais interessantes)",
            "O radar não deve eliminar justamente os sinais pequenos e incomuns "
            "que deveria encontrar. Cada item abaixo foi arquivado pelo sistema, "
            "mas um humano o considerou `interesting`.",
            false_negatives,
        )
    )
    lines.extend(
        _priority_section(
            "Prioridade 2 — Falsos positivos (ruído que chega ao analista)",
            "Itens que o sistema encaminharia para atenção humana, mas que foram "
            "marcados como `irrelevant`.",
            false_positives,
        )
    )
    lines.extend(
        _priority_section(
            "Divergências em `maybe`",
            "Casos em que a oportunidade depende de contexto ou investigação "
            "adicional; a recomendação do sistema diferiu de `watchlist`.",
            maybe_divergences,
        )
    )

    lines.extend(["## Divergência por fonte", ""])
    lines.extend(_breakdown_table(result.breakdown_by("source")))
    lines.extend(["", "## Divergência por tipo de sinal", ""])
    lines.extend(_breakdown_table(result.breakdown_by("signal_type")))
    lines.extend(["", "## Divergência por developer tooling", ""])
    lines.extend(_breakdown_table(result.breakdown_by("developer_tooling")))

    lines.extend(
        [
            "",
            "## Perguntas de avaliação (docs/06)",
            "",
            "- Quantas coisas irrelevantes ainda consumiriam tempo humano? "
            f"**{len(false_positives)}** falsos positivos.",
            "- O radar está eliminando sinais pequenos e incomuns? "
            f"**{len(false_negatives)}** falsos negativos.",
            "- Developer tooling está dominando a saída? Ver a tabela por "
            "developer tooling acima.",
            "- Há diversidade de tipos de oportunidade? Ver a distribuição por "
            "tipo de sinal acima.",
            "",
            "## Confirmações de escopo",
            "",
            "- Nenhum label ou `human_reason` do Gold Set foi alterado.",
            "- Nenhuma regra determinística, prompt, lens ou Signal Policy foi "
            "ajustada automaticamente por esta análise.",
            "- A calibração não usa LLM para julgar qualidade; apenas compara "
            "recomendação e label.",
            "- As divergências são evidência para decisão humana, não correção "
            "automática.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _priority_section(
    heading: str, description: str, cases: tuple[CalibrationCase, ...]
) -> list[str]:
    lines = [f"## {heading} ({len(cases)})", "", description, ""]
    if not cases:
        lines.append("- Nenhum caso nesta categoria.")
        lines.append("")
        return lines
    for case in cases:
        system_note = (
            "pulado no M2" if case.skipped_by_filter else f"`{case.recommendation.value}`"
        )
        lines.append(
            f"- `{case.item_id}` — **{_one_line(case.title)}** "
            f"(fonte `{case.source}`, sistema {system_note})"
        )
        lines.append(f"  - Motivo humano: {_one_line(case.human_reason)}")
    lines.append("")
    return lines


def _breakdown_table(breakdowns: tuple[CategoryBreakdown, ...]) -> list[str]:
    lines = [
        "| Categoria | Total | Concordância | Taxa | FP | FN | Div. maybe |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    if not breakdowns:
        lines.append("| (sem dados) | 0 | 0 | 0.0% | 0 | 0 | 0 |")
        return lines
    for breakdown in breakdowns:
        lines.append(
            f"| `{breakdown.key}` | {breakdown.total} | {breakdown.agreements} | "
            f"{_percent(breakdown.agreement_rate)} | {breakdown.false_positives} | "
            f"{breakdown.false_negatives} | {breakdown.maybe_divergences} |"
        )
    return lines


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _one_line(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")
