"""Deterministic analysis of labels and reasons supplied by a human reviewer."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from innovation_radar.reviews.gold_set import ALLOWED_LABELS


@dataclass(frozen=True, slots=True)
class LabelStatistics:
    total: int
    interesting: int
    maybe: int
    irrelevant: int

    @property
    def interesting_percentage(self) -> float:
        return _percentage(self.interesting, self.total)

    @property
    def useful_percentage(self) -> float:
        return _percentage(self.interesting + self.maybe, self.total)


@dataclass(frozen=True, slots=True)
class TextualReasonGroup:
    name: str
    terms: tuple[str, ...]
    item_ids: tuple[str, ...]
    examples: tuple[str, ...]

    @property
    def count(self) -> int:
        return len(self.item_ids)


REASON_RULES = (
    (
        "Ausência de valor, vínculo ou aplicação",
        ("sem valor", "não tem valor", "nao tem valor", "irrelevante", "sem vínculo", "sem vinculo"),
    ),
    (
        "Conteúdo informativo, notícia ou artigo genérico",
        ("informativ", "notícia", "noticia", "artigo", "genéric", "generic"),
    ),
    (
        "Testabilidade ou impossibilidade de testar",
        ("test" , "executável", "executavel", "demo", "protótip", "prototip"),
    ),
    (
        "Relação explícita com saúde, wellness ou Namu",
        ("health", "saúde", "namu", "wellness", "medical", "paciente", "farmaco", "wearable", "werable"),
    ),
    (
        "Potencial futuro ou valor ainda incerto",
        ("futuro", "mais pra frente", "algum momento", "potencial", "aprofundamento", "não sabemos", "nao sabemos"),
    ),
    (
        "Acesso ou conteúdo insuficiente",
        ("404", "não foi possível acessar", "nao foi possivel acessar", "incompleto", "limitação do medium", "limitacao do medium"),
    ),
)


POLICY_RULES = (
    {
        "title": "Developer tooling marcado como interesting",
        "labels": ("interesting",),
        "terms": (
            "framework",
            "sdk",
            "library",
            "biblioteca",
            "developer",
            "coding agent",
            "mcp",
            "database",
            "sqlite",
            "netcat",
            "tailscale",
            "terminal",
        ),
        "basis": "As seções 2 e 3 da Signal Policy normalmente reduzem developer tooling sem consequência clara para produto.",
        "question": "A exceção de nova capacidade de produto precisa ser detalhada ou a testabilidade prática está recebendo peso próprio?",
    },
    {
        "title": "Conteúdo informativo marcado como interesting",
        "labels": ("interesting",),
        "terms": ("informativ", "artigo", "conteúdo", "notícia", "noticia"),
        "basis": "A seção 2 reduz artigos genéricos e conteúdo sem evidência concreta.",
        "question": "Afinidade estratégica ou tema de inovação pode justificar interesting mesmo sem ação ou teste imediato?",
    },
    {
        "title": "Testabilidade aparece em julgamentos positivos",
        "labels": ("interesting", "maybe"),
        "terms": ("test", "executável", "executavel", "demo", "protótip", "prototip"),
        "basis": "A política enfatiza novidade, capacidade e produto, mas não define testabilidade como critério principal isolado.",
        "question": "Testabilidade deve se tornar critério explícito ou permanecer evidência operacional de investigação?",
    },
    {
        "title": "Potencial futuro sem aplicação imediata recebe julgamento positivo",
        "labels": ("interesting", "maybe"),
        "terms": ("futuro", "mais pra frente", "algum momento", "não agora", "nao agora", "não sabemos", "nao sabemos"),
        "basis": "As seções 5 e 9 aceitam timing inicial e aplicação ainda pouco clara, especialmente como maybe.",
        "question": "A política precisa distinguir melhor potencial futuro suficiente para interesting daquele que deve permanecer maybe?",
    },
    {
        "title": "Relação direta com saúde aparece em itens maybe",
        "labels": ("maybe",),
        "terms": ("health", "saúde", "medical", "paciente", "farmaco", "wearable", "werable"),
        "basis": "A seção 4 diz que saúde não precisa estar na fonte e, por si só, não comprova nova possibilidade.",
        "question": "A relação direta com saúde está funcionando apenas como sinal para investigação ou recebendo peso maior do que o documentado?",
    },
)


def calculate_overall_statistics(items: Iterable[dict[str, Any]]) -> LabelStatistics:
    item_list = tuple(items)
    counts = Counter(str(item["human_label"]) for item in item_list)
    return LabelStatistics(
        total=len(item_list),
        interesting=counts["interesting"],
        maybe=counts["maybe"],
        irrelevant=counts["irrelevant"],
    )


def calculate_source_statistics(
    items: Iterable[dict[str, Any]],
) -> dict[str, LabelStatistics]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        source = str(item["source_surface_or_feed"])
        groups.setdefault(source, []).append(item)
    return {
        source: calculate_overall_statistics(group)
        for source, group in sorted(groups.items())
    }


def group_human_reasons(
    items: Iterable[dict[str, Any]],
) -> tuple[TextualReasonGroup, ...]:
    item_list = tuple(items)
    groups: list[TextualReasonGroup] = []
    for name, terms in REASON_RULES:
        matches = [
            item
            for item in item_list
            if _contains_any(str(item["human_reason"]), terms)
        ]
        groups.append(
            TextualReasonGroup(
                name=name,
                terms=terms,
                item_ids=tuple(str(item["item_id"]) for item in matches),
                examples=tuple(
                    str(item["human_reason"]) for item in matches[:3]
                ),
            )
        )
    return tuple(groups)


def write_human_judgment_report(
    items: tuple[dict[str, Any], ...],
    output_path: str | Path,
) -> Path:
    if not items:
        raise ValueError("human judgment report requires at least one item")
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_human_judgment_report(items), encoding="utf-8")
    return destination


def render_human_judgment_report(items: tuple[dict[str, Any], ...]) -> str:
    overall = calculate_overall_statistics(items)
    source_statistics = calculate_source_statistics(items)
    reason_groups = group_human_reasons(items)
    repeated_reasons = _repeated_reasons(items)

    lines = [
        "# Human Judgment Analysis — Gold Set v0.1",
        "",
        "> Este relatório analisa exclusivamente labels e motivos fornecidos pela revisão humana. Não contém classificação automática, Opportunity Score ou julgamento sobre a correção das decisões humanas.",
        "",
        "## Distribuição geral",
        "",
        "| Label | Quantidade | Percentual |",
        "|---|---:|---:|",
    ]
    for label in ALLOWED_LABELS:
        count = getattr(overall, label)
        lines.append(f"| `{label}` | {count} | {_percentage(count, overall.total):.1f}% |")
    lines.extend(
        [
            f"| **Total** | **{overall.total}** | **100.0%** |",
            "",
            "## Qualidade por fonte",
            "",
            "| Superfície/feed | Total | Interesting | Maybe | Irrelevant | % interesting | % interesting + maybe |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for source, statistics in source_statistics.items():
        lines.append(
            f"| {_table_text(source)} | {statistics.total} | "
            f"{statistics.interesting} | {statistics.maybe} | "
            f"{statistics.irrelevant} | {statistics.interesting_percentage:.1f}% | "
            f"{statistics.useful_percentage:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Motivos humanos",
            "",
            "Os agrupamentos abaixo são indicadores lexicais não exclusivos: um mesmo item pode aparecer em mais de um grupo. As regras e os termos usados são mostrados explicitamente; nenhuma categoria altera o label humano.",
            "",
            "| Indicador textual | Itens correspondentes | Termos procurados |",
            "|---|---:|---|",
        ]
    )
    for group in reason_groups:
        terms = ", ".join(f"`{term}`" for term in group.terms)
        lines.append(f"| {_table_text(group.name)} | {group.count} | {terms} |")

    lines.extend(["", "### Exemplos por indicador", ""])
    for group in reason_groups:
        lines.extend([f"#### {group.name}", ""])
        if not group.examples:
            lines.append("Nenhum motivo correspondeu à regra textual.")
        else:
            lines.extend(f"- {_one_line(reason)}" for reason in group.examples)
        lines.append("")

    lines.extend(["## Frequência literal aproximada", ""])
    if repeated_reasons:
        lines.extend(
            f"- **{count}×** — {_one_line(reason)}"
            for reason, count in repeated_reasons
        )
    else:
        lines.append("Não existem motivos completos repetidos após normalização de caixa e espaços.")

    lines.extend(
        [
            "",
            "## Possible Policy Calibration Points",
            "",
            "Os pontos abaixo são candidatos a discussão, encontrados por correspondência textual transparente. Eles não indicam erro do humano nem autorizam mudança automática em `docs/05_SIGNAL_POLICY.md`.",
            "",
        ]
    )
    for rule in POLICY_RULES:
        matches = _policy_matches(items, rule)
        lines.extend(
            [
                f"### {rule['title']}",
                "",
                f"- Regra documental relacionada: {rule['basis']}",
                f"- Questão para decisão humana: {rule['question']}",
                f"- Correspondências textuais: **{len(matches)}**",
                "",
            ]
        )
        if not matches:
            lines.append("Nenhum exemplo encontrado por esta regra.")
        for item in matches[:5]:
            lines.extend(
                [
                    f"- `{_one_line(item['item_id'])}` — **{_one_line(item['title'])}** "
                    f"(`{item['human_label']}`)",
                    f"  - Motivo humano: {_one_line(item['human_reason'])}",
                ]
            )
        if len(matches) > 5:
            lines.append(f"- Mais {len(matches) - 5} correspondência(s) não exibida(s).")
        lines.append("")

    lines.extend(
        [
            "## Limitações",
            "",
            "- Correspondência por substring não entende contexto, negação, ironia ou equivalência semântica.",
            "- Os grupos de motivos se sobrepõem e não devem ser tratados como classes ou scores.",
            "- A amostra cobre somente Hacker News e os feeds RSS do M1B.",
            "- Qualquer alteração da Signal Policy continua dependendo de decisão humana explícita.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _policy_matches(
    items: tuple[dict[str, Any], ...], rule: dict[str, Any]
) -> list[dict[str, Any]]:
    labels = set(rule["labels"])
    terms = tuple(rule["terms"])
    return [
        item
        for item in items
        if item["human_label"] in labels
        and _contains_any(
            " ".join(
                str(item[field])
                for field in ("title", "short_description", "human_reason")
            ),
            terms,
        )
    ]


def _repeated_reasons(
    items: tuple[dict[str, Any], ...], limit: int = 10
) -> tuple[tuple[str, int], ...]:
    originals: dict[str, str] = {}
    counts: Counter[str] = Counter()
    for item in items:
        reason = _one_line(item["human_reason"])
        normalized = reason.casefold()
        originals.setdefault(normalized, reason)
        counts[normalized] += 1
    repeated = [
        (originals[normalized], count)
        for normalized, count in counts.most_common()
        if count > 1
    ]
    return tuple(repeated[:limit])


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    normalized = _one_line(text).casefold()
    return any(
        re.search(r"(?<!\w)" + re.escape(term.casefold()), normalized)
        for term in terms
    )


def _percentage(value: int, total: int) -> float:
    return (value / total * 100.0) if total else 0.0


def _one_line(value: object) -> str:
    return " ".join(str(value).split())


def _table_text(value: str) -> str:
    return _one_line(value).replace("|", "\\|")
