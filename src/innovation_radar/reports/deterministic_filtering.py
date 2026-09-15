"""Markdown report for deterministic filter evaluation against human labels."""

from __future__ import annotations

from pathlib import Path

from innovation_radar.filtering.deterministic import FilterOutcome
from innovation_radar.filtering.evaluation import (
    GoldSetFilterEvaluation,
    RuleEvaluation,
)


RULE_TITLES = {
    "duplicate_external_identity": "Identidade externa repetida",
    "duplicate_canonical_url": "URL canônica repetida",
    "duplicate_github_repository_id": "GitHub repository ID repetido",
    "consolidated_multiple_lenses": "Origem consolidada em múltiplas lenses",
    "github_explicit_profile_disclaimer": "Disclaimer explícito de perfil GitHub",
    "github_company_catalog_signature": "Assinatura de catálogo de empresa GitHub",
    "github_api_metadata_profile": "Metadados de perfil/API sem linguagem",
    "insufficient_description": "Descrição/contexto insuficiente",
    "github_archived_repository": "Repositório GitHub arquivado",
}

RULE_CRITERIA = {
    "duplicate_external_identity": "mesmo par `(source, source_item_id)` após a primeira ocorrência do lote",
    "duplicate_canonical_url": "mesma URL HTTP(S) após normalizar host, porta padrão, fragmento, ordem da query e parâmetros de tracking conhecidos",
    "duplicate_github_repository_id": "mesmo ID numérico estável GitHub após a primeira ocorrência do lote",
    "consolidated_multiple_lenses": "duas ou mais `discovery_lenses` preservadas no payload da mesma identidade",
    "github_explicit_profile_disclaimer": "texto disponível declara explicitamente que o repositório é um perfil independente e não a API representada",
    "github_company_catalog_signature": "tópicos `apis-json` + `company` e nenhuma linguagem detectada",
    "github_api_metadata_profile": "tópico `apis-json` e nenhuma linguagem detectada, sem exigir `company`",
    "insufficient_description": "descrição vazia e ausência de excerpt de README ou corpo estruturado suportado",
    "github_archived_repository": "metadado GitHub `archived=true`",
}


def write_deterministic_filter_report(
    evaluation: GoldSetFilterEvaluation, path: str | Path
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_deterministic_filter_report(evaluation), encoding="utf-8"
    )
    return output_path


def render_deterministic_filter_report(
    evaluation: GoldSetFilterEvaluation,
) -> str:
    outcomes = evaluation.outcome_label_counts
    discarded = outcomes[FilterOutcome.DISCARD_CANDIDATE]
    flagged = outcomes[FilterOutcome.NOISE_FLAG]
    kept = outcomes[FilterOutcome.KEEP]
    discard_count = sum(discarded.values())
    flag_count = sum(flagged.values())
    keep_count = sum(kept.values())
    remaining = evaluation.total - discard_count
    reduction = discard_count / evaluation.total if evaluation.total else 0.0
    label_counts = evaluation.label_counts

    lines = [
        "# Deterministic Filter Evaluation — M2",
        "",
        "> Avaliação determinística em shadow mode sobre o Gold Set v0.2. Os "
        "130 labels e motivos humanos permanecem a referência; nenhuma regra produz "
        "`interesting`, `maybe` ou `irrelevant` e nenhum item é removido do pipeline.",
        "",
        "## Escopo e critério de segurança",
        "",
        "A camada responde somente se existe evidência objetiva de duplicação, "
        "ruído técnico ou contexto insuficiente. Preservar recall tem prioridade "
        "sobre reduzir volume. `discard_candidate` é um cenário hipotético de alta "
        "confiança; nesta versão, continua sendo apenas uma decisão derivada.",
        "",
        "Uma regra candidata a descarte é considerada segura **nesta amostra** "
        "somente quando não atinge nenhum `interesting` nem `maybe`. Ausência de "
        "exemplos afetados não é tratada como validação estatística.",
        "",
        "## Métricas globais observadas",
        "",
        f"- Total do Gold Set: **{evaluation.total}**",
        f"- Distribuição humana: **{label_counts.get('interesting', 0)} interesting**, "
        f"**{label_counts.get('maybe', 0)} maybe**, "
        f"**{label_counts.get('irrelevant', 0)} irrelevant**",
        f"- Sem filtros: **{evaluation.total}** itens enviados à futura triagem",
        f"- `discard_candidate` seguro observado: **{discard_count}**",
        f"- Cenário após candidatos seguros: **{remaining}** itens",
        f"- Itens cujo resultado final é somente `noise_flag`: **{flag_count}**",
        f"- Itens com resultado final `keep`: **{keep_count}**",
        f"- Redução potencial observada: **{_percent(reduction)}**",
        f"- `interesting` entre os candidatos a descarte: "
        f"**{discarded.get('interesting', 0)}**",
        f"- `maybe` entre os candidatos a descarte: "
        f"**{discarded.get('maybe', 0)}**",
        f"- `irrelevant` entre os candidatos a descarte: "
        f"**{discarded.get('irrelevant', 0)}**",
        "",
        "A redução de volume acima é observada somente nos 130 itens do Gold Set. "
        "Ela não é previsão para coletas futuras: a frequência de duplicatas, "
        "perfis e descrições ausentes pode mudar por fonte e por ciclo.",
        "",
        "## Resumo por regra",
        "",
        "| Regra | Resultado configurado | Afetados | Interesting | Maybe | Irrelevant | FP se descartasse | Taxa de descarte correto | Estado |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    lines.extend(_rule_table_row(rule) for rule in evaluation.rule_evaluations)

    lines.extend(["", "## Avaliação regra por regra", ""])
    for rule in evaluation.rule_evaluations:
        lines.extend(_render_rule(rule))

    lines.extend(
        [
            "## Regras consideradas seguras nesta amostra",
            "",
            "- `github_explicit_profile_disclaimer`: 1/1 item afetado era "
            "`irrelevant`; nenhum `interesting` ou `maybe`.",
            "- `github_company_catalog_signature`: 7/7 itens afetados eram "
            "`irrelevant`; nenhum `interesting` ou `maybe`.",
            "",
            "As três regras de duplicação exata permanecem candidatas estruturais "
            "de alta confiança, mas afetaram zero itens porque o Gold Set já contém "
            "IDs e URLs únicos. Portanto, o Gold Set não mede sua precisão. Todas "
            "continuam em shadow mode.",
            "",
            "## Regras mantidas somente como `noise_flag`",
            "",
            "- `github_api_metadata_profile`: 11 itens; 10 `irrelevant` e 1 "
            "`maybe`. A variante ampla não pode descartar o caso `maybe`.",
            "- `insufficient_description`: 45 itens; 4 `interesting`, 8 `maybe` e "
            "33 `irrelevant`. Título e URL ainda podem conter sinal suficiente.",
            "- `github_archived_repository`: nenhum caso no Gold Set; arquivo não "
            "implica irrelevância e a regra nunca descarta.",
            "",
            "`consolidated_multiple_lenses` retorna `keep`: múltiplas lenses são "
            "proveniência consolidada da mesma identidade, não repetição a remover.",
            "",
            "## Regras rejeitadas ou não implementadas",
            "",
            "- **Owner específico:** `owner == api-evangelist` não foi implementado. "
            "O owner é evidência diagnóstica, não regra de produto, e o Gold Set "
            "contém um item `maybe` desse owner.",
            "- **Perfil amplo como descarte:** `apis-json` + linguagem ausente não "
            "pode virar descarte; atingiria 1 `maybe`. Permanece apenas como flag.",
            "- **Descrição ausente como descarte:** rejeitada; atingiria 4 "
            "`interesting` e 8 `maybe`.",
            "- **Repositório vazio/trivial:** não implementada. Os dados atuais não "
            "incluem árvore, quantidade de arquivos ou outra evidência estrutural "
            "suficiente. Stars, linguagem ausente e descrição curta não bastam.",
            "- **Fork:** não implementada. `forks` é contagem de forks recebidos, "
            "não informa se o repositório é um fork; mesmo esse estado geraria no "
            "máximo uma flag.",
            "- **Developer tooling, saúde, IA, fonte, lens, idade, popularidade, "
            "testabilidade ou relação Namu:** rejeitadas como regras determinísticas "
            "por exigirem interpretação de oportunidade.",
            "- **Duplicação semântica:** não implementada; não há embeddings, "
            "similaridade textual ou agrupamento por assunto.",
            "",
            "## Shadow mode e preservação do bruto",
            "",
            "O pipeline calcula as decisões depois que cada lote de `RawItem` já foi "
            "persistido. `DiscoveryResult.items` mantém todos os itens na ordem de "
            "coleta; o relatório bruto registra as decisões como uma camada derivada. "
            "Não há `DELETE`, alteração do schema ou substituição de payload bruto.",
            "",
            "## Limitações",
            "",
            "- O Gold Set contém 130 itens, dos quais 40 são GitHub; assinaturas "
            "perfeitas nesta amostra podem falhar em ciclos futuros.",
            "- O Gold Set já está deduplicado, então não mede a precisão das regras "
            "de identidade ou URL canônica.",
            "- A descrição usada na avaliação é o `short_description` exportado; "
            "payloads reais podem oferecer contexto adicional.",
            "- Não há exemplos arquivados nem metadado confiável de fork no conjunto.",
            "- `noise_flag` é evidência para inspeção futura, não baixa prioridade nem "
            "classificação de relevância.",
            "",
            "## Confirmações de escopo",
            "",
            "- Nenhum LLM, API de IA, embedding, score ou classificador foi usado.",
            "- Nenhum label ou `human_reason` do Gold Set foi alterado.",
            "- Nenhuma fonte, lens, collector, watchlist, dashboard ou scheduler foi adicionado.",
            "- O Reddit não foi consultado novamente e seu collector não foi alterado.",
            "- O M2 permanece em shadow mode; não houve avanço para M3.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _rule_table_row(rule: RuleEvaluation) -> str:
    rate = (
        _percent(rule.correct_discard_rate)
        if rule.correct_discard_rate is not None
        else "n/a"
    )
    return (
        f"| `{rule.rule_id}` | `{rule.configured_outcome.value}` | "
        f"{rule.affected_count} | {rule.interesting_count} | {rule.maybe_count} | "
        f"{rule.irrelevant_count} | {rule.false_positive_count} | {rate} | "
        f"{_safety_status(rule)} |"
    )


def _render_rule(rule: RuleEvaluation) -> list[str]:
    rate = (
        _percent(rule.correct_discard_rate)
        if rule.correct_discard_rate is not None
        else "não aplicável — a regra não propõe descarte ou não teve casos"
    )
    lines = [
        f"### `{rule.rule_id}` — {RULE_TITLES.get(rule.rule_id, rule.rule_id)}",
        "",
        f"- Resultado configurado: `{rule.configured_outcome.value}`",
        f"- Evidência exigida: {RULE_CRITERIA.get(rule.rule_id, 'regra objetiva documentada')}",
        f"- Itens afetados: **{rule.affected_count}**",
        f"- Distribuição: **{rule.interesting_count} interesting**, "
        f"**{rule.maybe_count} maybe**, **{rule.irrelevant_count} irrelevant**",
        f"- Taxa de descarte correto: **{rate}**",
        f"- Falsos positivos potenciais se a regra descartasse "
        f"(`interesting` + `maybe`): **{rule.false_positive_count}**",
        f"- Conclusão de segurança: {_safety_status(rule)}",
        "",
        "Exemplos:",
        "",
    ]
    if not rule.examples:
        lines.append("- Nenhum caso correspondente no Gold Set v0.2.")
    else:
        lines.extend(
            f"- `{example.item_id}` — **{_one_line(example.title)}** "
            f"(`{example.human_label}`)"
            for example in rule.examples
        )
    lines.append("")
    return lines


def _safety_status(rule: RuleEvaluation) -> str:
    if rule.configured_outcome is FilterOutcome.KEEP:
        return "evidência de consolidação; mantém o item"
    if rule.configured_outcome is FilterOutcome.NOISE_FLAG:
        return "somente flag; não descarta"
    if rule.affected_count == 0:
        return "sem casos no Gold Set; não validada pela amostra"
    if rule.safe_discard_observed:
        return "segura no Gold Set; apenas candidata em shadow mode"
    return "insegura para descarte; deve ser rebaixada ou rejeitada"


def _percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def _one_line(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")
