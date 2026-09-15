"""Deterministic analysis of human judgments from GitHub Discovery."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from innovation_radar.reports.human_judgment import (
    LabelStatistics,
    calculate_overall_statistics,
)


GITHUB_LENSES = (
    "health_wellness",
    "wearables_sensors",
    "voice_vision_multimodal",
    "local_new_interfaces",
    "personal_data_experiments",
)
TRANSFERABLE_CAPABILITY_LENSES = (
    "voice_vision_multimodal",
    "local_new_interfaces",
    "personal_data_experiments",
)
PROFILE_STUB_TERMS = (
    "perfil",
    "stub",
    "catálog",
    "não contém software",
    "nao contem software",
    "sem software",
)
DEVELOPER_ONLY_TERMS = (
    "desenvolvedor",
    "engenharia de software",
    "runtime/framework",
    "infraestrutura de desenvolvimento",
    "developer tooling",
)
THIN_OR_BASIC_TERMS = (
    "não tem implementação",
    "nao tem implementacao",
    "praticamente não tem implementação",
    "exercício básico",
    "não tem nada",
    "projeto sem valor",
)


@dataclass(frozen=True, slots=True)
class NoisePattern:
    id: str
    name: str
    rule: str
    items: tuple[dict[str, Any], ...]

    @property
    def count(self) -> int:
        return len(self.items)

    @property
    def lens_counts(self) -> Counter[str]:
        return Counter(
            lens for item in self.items for lens in _item_lenses(item)
        )

    @property
    def owner_counts(self) -> Counter[str]:
        return Counter(str(item.get("author", "")) for item in self.items)


def calculate_lens_statistics(
    items: Iterable[dict[str, Any]],
) -> dict[str, LabelStatistics]:
    """Calculate non-scoring label statistics for each configured lens."""

    groups: dict[str, list[dict[str, Any]]] = {lens: [] for lens in GITHUB_LENSES}
    for item in items:
        if item.get("source") != "github":
            raise ValueError("discovery lens statistics require only GitHub items")
        for lens in _item_lenses(item):
            if lens not in groups:
                raise ValueError(f"unknown GitHub discovery lens: {lens}")
            groups[lens].append(item)
    return {
        lens: calculate_overall_statistics(groups[lens]) for lens in GITHUB_LENSES
    }


def identify_noise_patterns(
    items: Iterable[dict[str, Any]],
) -> tuple[NoisePattern, ...]:
    """Apply transparent textual and metadata rules to irrelevant items."""

    github_items = tuple(items)
    irrelevant = tuple(
        item for item in github_items if item.get("human_label") == "irrelevant"
    )
    profile_items = tuple(
        item
        for item in irrelevant
        if str(item.get("author", "")).casefold() == "api-evangelist"
        or _contains_any(str(item.get("human_reason", "")), PROFILE_STUB_TERMS)
    )
    developer_items = tuple(
        item
        for item in irrelevant
        if _contains_any(str(item.get("human_reason", "")), DEVELOPER_ONLY_TERMS)
    )
    thin_items = tuple(
        item
        for item in irrelevant
        if _contains_any(str(item.get("human_reason", "")), THIN_OR_BASIC_TERMS)
    )
    return (
        NoisePattern(
            id="company_profile_or_stub",
            name="Perfil, catálogo ou stub sem projeto executável",
            rule=(
                "label=irrelevant e owner=api-evangelist, ou human_reason contém "
                "termos explícitos de perfil/stub/catálogo/ausência de software"
            ),
            items=profile_items,
        ),
        NoisePattern(
            id="developer_only",
            name="Infraestrutura ou ferramenta restrita ao desenvolvimento",
            rule=(
                "label=irrelevant e human_reason contém termos explícitos de "
                "desenvolvimento, framework/runtime ou infraestrutura"
            ),
            items=developer_items,
        ),
        NoisePattern(
            id="thin_or_basic",
            name="Implementação inexistente, muito fina ou exercício básico",
            rule=(
                "label=irrelevant e human_reason registra falta de implementação, "
                "conteúdo vazio, exercício básico ou projeto sem valor"
            ),
            items=thin_items,
        ),
    )


def write_github_discovery_report(
    github_items: tuple[dict[str, Any], ...],
    previous_items: tuple[dict[str, Any], ...],
    output_path: str | Path,
    *,
    excluded_non_github_count: int,
) -> Path:
    if not github_items:
        raise ValueError("GitHub discovery report requires GitHub items")
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        render_github_discovery_report(
            github_items,
            previous_items,
            excluded_non_github_count=excluded_non_github_count,
        ),
        encoding="utf-8",
    )
    return destination


def render_github_discovery_report(
    github_items: tuple[dict[str, Any], ...],
    previous_items: tuple[dict[str, Any], ...],
    *,
    excluded_non_github_count: int,
) -> str:
    overall = calculate_overall_statistics(github_items)
    previous = calculate_overall_statistics(previous_items)
    lens_statistics = calculate_lens_statistics(github_items)
    noise_patterns = identify_noise_patterns(github_items)
    owner_counts = Counter(str(item.get("author", "")) for item in github_items)
    recurring_owners = tuple(
        (owner, count) for owner, count in owner_counts.most_common() if count > 1
    )
    api_items = tuple(
        item for item in github_items if item.get("author") == "api-evangelist"
    )
    api_irrelevant = tuple(
        item for item in api_items if item.get("human_label") == "irrelevant"
    )
    api_wearables_count = sum(
        "wearables_sensors" in _item_lenses(item) for item in api_items
    )
    explicit_profile_items = tuple(
        item
        for item in github_items
        if item.get("human_label") == "irrelevant"
        and _contains_any(str(item.get("human_reason", "")), PROFILE_STUB_TERMS)
    )
    api_without_language = sum(
        item.get("available_metrics", {}).get("language") is None
        for item in api_items
    )
    api_with_apis_json = sum(
        "apis-json" in item.get("available_metrics", {}).get("topics", [])
        for item in api_items
    )
    api_with_company = sum(
        "company" in item.get("available_metrics", {}).get("topics", [])
        for item in api_items
    )
    api_with_at_most_one_star = sum(
        item.get("available_metrics", {}).get("stars", 0) <= 1
        for item in api_items
    )
    best_interesting = max(
        lens_statistics.items(), key=lambda entry: entry[1].interesting
    )
    best_useful = max(
        lens_statistics.items(),
        key=lambda entry: entry[1].interesting + entry[1].maybe,
    )
    noisiest = max(
        lens_statistics.items(), key=lambda entry: entry[1].irrelevant
    )
    transferable_items = tuple(
        item
        for item in github_items
        if any(
            lens in TRANSFERABLE_CAPABILITY_LENSES for lens in _item_lenses(item)
        )
    )
    transferable = calculate_overall_statistics(transferable_items)
    direct_health = lens_statistics["health_wellness"]

    lines = [
        "# GitHub Discovery Lens Analysis — Gold Set v0.2",
        "",
        "> Análise determinística dos julgamentos humanos do M1D.1. Não contém classificação automática, Opportunity Score, LLM ou decisão sobre ajustes nas lenses.",
        "",
        "## Escopo validado",
        "",
        f"- Registros revisados no workbook: **{len(github_items) + excluded_non_github_count}**",
        f"- Registros GitHub incluídos: **{len(github_items)}**",
        f"- Registros não GitHub excluídos: **{excluded_non_github_count}**",
        f"- Itens anteriores preservados: **{len(previous_items)}**",
        f"- Gold Set v0.2: **{len(previous_items) + len(github_items)} julgamentos humanos**",
        "",
        "## Distribuição dos 40 itens GitHub",
        "",
        "| Label | Quantidade | Percentual |",
        "|---|---:|---:|",
    ]
    for label in ("interesting", "maybe", "irrelevant"):
        count = getattr(overall, label)
        lines.append(f"| `{label}` | {count} | {_percentage(count, overall.total):.1f}% |")
    lines.extend(
        [
            f"| **Total** | **{overall.total}** | **100.0%** |",
            "",
            "## Qualidade por discovery lens",
            "",
            "| Discovery lens | Total | Interesting | Maybe | Irrelevant | % interesting | % interesting + maybe |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for lens in GITHUB_LENSES:
        stats = lens_statistics[lens]
        lines.append(
            f"| `{lens}` | {stats.total} | {stats.interesting} | {stats.maybe} | "
            f"{stats.irrelevant} | {stats.interesting_percentage:.1f}% | "
            f"{stats.useful_percentage:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Comparação inicial entre as lenses",
            "",
            f"- Mais `interesting`: **`{best_interesting[0]}`**, com **{best_interesting[1].interesting}** de {best_interesting[1].total}.",
            f"- Mais `interesting + maybe`: **`{best_useful[0]}`**, com **{best_useful[1].interesting + best_useful[1].maybe}** de {best_useful[1].total} ({best_useful[1].useful_percentage:.1f}%).",
            f"- Maior ruído observado: **`{noisiest[0]}`**, com **{noisiest[1].irrelevant}** de {noisiest[1].total} itens `irrelevant`.",
            f"- A lens direta `health_wellness` produziu **{direct_health.interesting + direct_health.maybe}/{direct_health.total}** itens `interesting + maybe` ({direct_health.useful_percentage:.1f}%).",
            f"- O agrupamento analítico de capacidades transferíveis (`voice_vision_multimodal`, `local_new_interfaces` e `personal_data_experiments`) produziu **{transferable.interesting + transferable.maybe}/{transferable.total}** ({transferable.useful_percentage:.1f}%).",
            "",
            "Esta diferença sugere, nesta amostra, maior eficiência das buscas orientadas a capacidades transferíveis do que da busca direta por health/wellness. Com apenas oito itens por lens e uma única coleta, ela não demonstra causalidade nem superioridade permanente.",
            "",
            "## Padrões recorrentes de ruído",
            "",
            "As regras abaixo são explícitas, determinísticas e não exclusivas. Um item pode aparecer em mais de um padrão. Somente itens rotulados pelo humano como `irrelevant` são contados como ruído.",
            "",
            "| Padrão | Casos | Lenses | Regra observável |",
            "|---|---:|---|---|",
        ]
    )
    for pattern in noise_patterns:
        lens_text = ", ".join(
            f"`{lens}`={pattern.lens_counts[lens]}"
            for lens in GITHUB_LENSES
            if pattern.lens_counts[lens]
        )
        lines.append(
            f"| {_table_text(pattern.name)} | {pattern.count} | {lens_text or '—'} | "
            f"{_table_text(pattern.rule)} |"
        )

    profile_pattern = noise_patterns[0]
    lines.extend(
        [
            "",
            "### Perfis, catálogos e stubs de empresas",
            "",
            f"- Casos `irrelevant` identificados pela regra combinada: **{profile_pattern.count}**.",
            f"- Motivos que mencionam explicitamente perfil, stub, catálogo ou ausência de software: **{len(explicit_profile_items)}**.",
            f"- Owner `api-evangelist`: **{len(api_items)}** resultados; **{len(api_irrelevant)} irrelevant** e **{len(api_items) - len(api_irrelevant)} maybe**.",
            f"- Distribuição dos `irrelevant` desse owner: {_counter_text(Counter(lens for item in api_irrelevant for lens in _item_lenses(item)))}.",
            f"- Sinais objetivos presentes nos {len(api_items)} resultados desse owner: {api_without_language} sem linguagem detectada, {api_with_apis_json} com tópico `apis-json`, {api_with_at_most_one_star} com no máximo 1 star e {api_with_company} com tópico `company`.",
            "",
            "Esses sinais podem apoiar uma futura regra auditável, mas nenhum deles deve ser usado isoladamente: ausência de linguagem ou baixa tração também ocorre em projetos pequenos legítimos.",
            "",
            "### Owners recorrentes",
            "",
        ]
    )
    if recurring_owners:
        lines.extend(f"- `{owner}`: **{count}** itens" for owner, count in recurring_owners)
    else:
        lines.append("Nenhum owner apareceu mais de uma vez.")

    for pattern in noise_patterns:
        lines.extend(["", f"### Exemplos — {pattern.name}", ""])
        if not pattern.items:
            lines.append("Nenhum item correspondeu à regra.")
            continue
        for item in pattern.items[:5]:
            lines.append(
                f"- `{_one_line(item['item_id'])}` — **{_one_line(item['title'])}** "
                f"(`{_one_line(item['source_surface_or_feed'])}`): "
                f"{_one_line(item['human_reason'])}"
            )
        if pattern.count > 5:
            lines.append(f"- Mais {pattern.count - 5} correspondência(s) não exibida(s).")

    lines.extend(
        [
            "",
            "## GitHub versus HN/RSS do Gold Set anterior",
            "",
            "| Amostra | Total | Interesting | Maybe | Irrelevant | % interesting | % maybe | % irrelevant | % interesting + maybe |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            _comparison_row("GitHub — M1D", overall),
            _comparison_row("HN/RSS — Gold Set v0.1", previous),
            "",
            "Nesta amostra, GitHub apresentou proporção maior de `interesting` e de `interesting + maybe`. HN/RSS apresentou proporção maior de `maybe` e `irrelevant`. O resultado é descritivo: os ciclos têm fontes, formatos de evidência e tamanhos diferentes e não demonstram superioridade definitiva de uma fonte.",
            "",
            "## Possible Discovery Calibration Points",
            "",
            "### 1. Concentração de perfis do owner `api-evangelist`",
            "",
            f"- Evidência: **{len(api_items)}/40** resultados vieram do mesmo owner; **{len(api_irrelevant)}** foram `irrelevant`.",
            "- Possível problema: diversidade nominal entre empresas, mas baixa diversidade real de repositórios executáveis.",
            "- Possível direção: considerar concentração por owner e marcadores explícitos de perfil/stub antes da próxima coleta, sem usar stars ou ausência de linguagem isoladamente.",
            "",
            "### 2. `health_wellness` ampla e pouco eficiente nesta amostra",
            "",
            f"- Evidência: **{direct_health.irrelevant}/{direct_health.total} irrelevant** e **{direct_health.useful_percentage:.1f}% interesting + maybe**.",
            "- Possível problema: termos temáticos encontram descrições de empresas e menções de wellness sem capacidade executável.",
            "- Possível direção: revisar humanamente termos e qualificadores da lens para distinguir tema de saúde de projeto, demo ou capacidade concreta.",
            "",
            "### 3. `wearables_sensors` encontrou sinais e catálogos",
            "",
            f"- Evidência: **{lens_statistics['wearables_sensors'].interesting} interesting** e **{lens_statistics['wearables_sensors'].irrelevant} irrelevant**; **{api_wearables_count}** resultados vieram de `api-evangelist`.",
            "- Possível problema: descrições comerciais de wearables competem com projetos implementados.",
            "- Possível direção: preservar a capacidade de encontrar projetos pequenos e modelos on-device, avaliando marcadores objetivos de repositório executável.",
            "",
            "### 4. Lenses orientadas a capacidades tiveram melhor rendimento inicial",
            "",
            f"- Evidência: **{transferable.interesting + transferable.maybe}/{transferable.total}** itens `interesting + maybe` no agrupamento de capacidades transferíveis.",
            "- Possível problema: concluir cedo demais que termos de capacidade sempre superam termos de domínio.",
            "- Possível direção: repetir a coleta em outros períodos mantendo diversidade e comparar intervalos antes de alterar as lenses.",
            "",
            "### 5. Implementações vazias, básicas ou exclusivamente técnicas",
            "",
            f"- Evidência: **{noise_patterns[1].count}** casos developer-only e **{noise_patterns[2].count}** casos de implementação fina/básica pelas regras textuais.",
            "- Possível problema: recência extrema encontra repositórios recém-criados, exercícios ou infraestrutura sem experiência de produto.",
            "- Possível direção: investigar sinais objetivos como presença de implementação, release ou demo, sem criar filtro até validar o risco de perder experimentos emergentes.",
            "",
            "## Pontos novos para Signal Policy",
            "",
            "Os 40 julgamentos não revelaram contradição importante ainda não coberta pela Signal Policy v0.2. Eles reforçam três princípios existentes: saúde não basta; developer tooling sem consequência permanece fora do foco; e capacidade testável pode tornar projetos pequenos interessantes. Perfis/stubs são principalmente um problema de qualidade da descoberta, não uma nova regra de relevância.",
            "",
            "## Limitações",
            "",
            "- A amostra contém somente 40 itens GitHub, oito por lens, de uma única coleta.",
            "- Os agrupamentos de ruído usam correspondência textual e metadados explícitos; não compreendem contexto semântico e podem se sobrepor.",
            "- A concentração de um owner pode ser episódica e não deve ser generalizada sem novas coletas.",
            "- A comparação com HN/RSS usa ciclos e formatos de conteúdo diferentes.",
            "- Nenhuma lens, query, classificação humana ou Signal Policy foi alterada por esta análise.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _item_lenses(item: dict[str, Any]) -> tuple[str, ...]:
    raw_value = str(item.get("source_surface_or_feed", ""))
    lenses = tuple(dict.fromkeys(part.strip() for part in raw_value.split("|") if part.strip()))
    if not lenses:
        raise ValueError(f"GitHub item {item.get('item_id')} has no discovery lens")
    return lenses


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    normalized = _one_line(text).casefold()
    return any(term.casefold() in normalized for term in terms)


def _comparison_row(name: str, stats: LabelStatistics) -> str:
    return (
        f"| {name} | {stats.total} | {stats.interesting} | {stats.maybe} | "
        f"{stats.irrelevant} | {_percentage(stats.interesting, stats.total):.1f}% | "
        f"{_percentage(stats.maybe, stats.total):.1f}% | "
        f"{_percentage(stats.irrelevant, stats.total):.1f}% | "
        f"{stats.useful_percentage:.1f}% |"
    )


def _percentage(value: int, total: int) -> float:
    return value / total * 100.0 if total else 0.0


def _counter_text(counts: Counter[str]) -> str:
    return ", ".join(f"`{key}`={count}" for key, count in sorted(counts.items())) or "—"


def _one_line(value: object) -> str:
    return " ".join(str(value).split())


def _table_text(value: str) -> str:
    return _one_line(value).replace("|", "\\|")
