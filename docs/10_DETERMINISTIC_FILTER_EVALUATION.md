# Deterministic Filter Evaluation — M2

> Avaliação determinística em shadow mode sobre o Gold Set v0.2. Os 130 labels e motivos humanos permanecem a referência; nenhuma regra produz `interesting`, `maybe` ou `irrelevant` e nenhum item é removido do pipeline.

## Escopo e critério de segurança

A camada responde somente se existe evidência objetiva de duplicação, ruído técnico ou contexto insuficiente. Preservar recall tem prioridade sobre reduzir volume. `discard_candidate` é um cenário hipotético de alta confiança; nesta versão, continua sendo apenas uma decisão derivada.

Uma regra candidata a descarte é considerada segura **nesta amostra** somente quando não atinge nenhum `interesting` nem `maybe`. Ausência de exemplos afetados não é tratada como validação estatística.

## Métricas globais observadas

- Total do Gold Set: **130**
- Distribuição humana: **27 interesting**, **26 maybe**, **77 irrelevant**
- Sem filtros: **130** itens enviados à futura triagem
- `discard_candidate` seguro observado: **8**
- Cenário após candidatos seguros: **122** itens
- Itens cujo resultado final é somente `noise_flag`: **48**
- Itens com resultado final `keep`: **74**
- Redução potencial observada: **6.2%**
- `interesting` entre os candidatos a descarte: **0**
- `maybe` entre os candidatos a descarte: **0**
- `irrelevant` entre os candidatos a descarte: **8**

A redução de volume acima é observada somente nos 130 itens do Gold Set. Ela não é previsão para coletas futuras: a frequência de duplicatas, perfis e descrições ausentes pode mudar por fonte e por ciclo.

## Resumo por regra

| Regra | Resultado configurado | Afetados | Interesting | Maybe | Irrelevant | FP se descartasse | Taxa de descarte correto | Estado |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `duplicate_external_identity` | `discard_candidate` | 0 | 0 | 0 | 0 | 0 | n/a | sem casos no Gold Set; não validada pela amostra |
| `duplicate_canonical_url` | `discard_candidate` | 0 | 0 | 0 | 0 | 0 | n/a | sem casos no Gold Set; não validada pela amostra |
| `duplicate_github_repository_id` | `discard_candidate` | 0 | 0 | 0 | 0 | 0 | n/a | sem casos no Gold Set; não validada pela amostra |
| `consolidated_multiple_lenses` | `keep` | 0 | 0 | 0 | 0 | 0 | n/a | evidência de consolidação; mantém o item |
| `github_explicit_profile_disclaimer` | `discard_candidate` | 1 | 0 | 0 | 1 | 0 | 100.0% | segura no Gold Set; apenas candidata em shadow mode |
| `github_company_catalog_signature` | `discard_candidate` | 7 | 0 | 0 | 7 | 0 | 100.0% | segura no Gold Set; apenas candidata em shadow mode |
| `github_api_metadata_profile` | `noise_flag` | 11 | 0 | 1 | 10 | 1 | n/a | somente flag; não descarta |
| `insufficient_description` | `noise_flag` | 45 | 4 | 8 | 33 | 12 | n/a | somente flag; não descarta |
| `github_archived_repository` | `noise_flag` | 0 | 0 | 0 | 0 | 0 | n/a | somente flag; não descarta |

## Avaliação regra por regra

### `duplicate_external_identity` — Identidade externa repetida

- Resultado configurado: `discard_candidate`
- Evidência exigida: mesmo par `(source, source_item_id)` após a primeira ocorrência do lote
- Itens afetados: **0**
- Distribuição: **0 interesting**, **0 maybe**, **0 irrelevant**
- Taxa de descarte correto: **não aplicável — a regra não propõe descarte ou não teve casos**
- Falsos positivos potenciais se a regra descartasse (`interesting` + `maybe`): **0**
- Conclusão de segurança: sem casos no Gold Set; não validada pela amostra

Exemplos:

- Nenhum caso correspondente no Gold Set v0.2.

### `duplicate_canonical_url` — URL canônica repetida

- Resultado configurado: `discard_candidate`
- Evidência exigida: mesma URL HTTP(S) após normalizar host, porta padrão, fragmento, ordem da query e parâmetros de tracking conhecidos
- Itens afetados: **0**
- Distribuição: **0 interesting**, **0 maybe**, **0 irrelevant**
- Taxa de descarte correto: **não aplicável — a regra não propõe descarte ou não teve casos**
- Falsos positivos potenciais se a regra descartasse (`interesting` + `maybe`): **0**
- Conclusão de segurança: sem casos no Gold Set; não validada pela amostra

Exemplos:

- Nenhum caso correspondente no Gold Set v0.2.

### `duplicate_github_repository_id` — GitHub repository ID repetido

- Resultado configurado: `discard_candidate`
- Evidência exigida: mesmo ID numérico estável GitHub após a primeira ocorrência do lote
- Itens afetados: **0**
- Distribuição: **0 interesting**, **0 maybe**, **0 irrelevant**
- Taxa de descarte correto: **não aplicável — a regra não propõe descarte ou não teve casos**
- Falsos positivos potenciais se a regra descartasse (`interesting` + `maybe`): **0**
- Conclusão de segurança: sem casos no Gold Set; não validada pela amostra

Exemplos:

- Nenhum caso correspondente no Gold Set v0.2.

### `consolidated_multiple_lenses` — Origem consolidada em múltiplas lenses

- Resultado configurado: `keep`
- Evidência exigida: duas ou mais `discovery_lenses` preservadas no payload da mesma identidade
- Itens afetados: **0**
- Distribuição: **0 interesting**, **0 maybe**, **0 irrelevant**
- Taxa de descarte correto: **não aplicável — a regra não propõe descarte ou não teve casos**
- Falsos positivos potenciais se a regra descartasse (`interesting` + `maybe`): **0**
- Conclusão de segurança: evidência de consolidação; mantém o item

Exemplos:

- Nenhum caso correspondente no Gold Set v0.2.

### `github_explicit_profile_disclaimer` — Disclaimer explícito de perfil GitHub

- Resultado configurado: `discard_candidate`
- Evidência exigida: texto disponível declara explicitamente que o repositório é um perfil independente e não a API representada
- Itens afetados: **1**
- Distribuição: **0 interesting**, **0 maybe**, **1 irrelevant**
- Taxa de descarte correto: **100.0%**
- Falsos positivos potenciais se a regra descartasse (`interesting` + `maybe`): **0**
- Conclusão de segurança: segura no Gold Set; apenas candidata em shadow mode

Exemplos:

- `github:1190450025` — **api-evangelist/coach** (`irrelevant`)

### `github_company_catalog_signature` — Assinatura de catálogo de empresa GitHub

- Resultado configurado: `discard_candidate`
- Evidência exigida: tópicos `apis-json` + `company` e nenhuma linguagem detectada
- Itens afetados: **7**
- Distribuição: **0 interesting**, **0 maybe**, **7 irrelevant**
- Taxa de descarte correto: **100.0%**
- Falsos positivos potenciais se a regra descartasse (`interesting` + `maybe`): **0**
- Conclusão de segurança: segura no Gold Set; apenas candidata em shadow mode

Exemplos:

- `github:1311961079` — **api-evangelist/compt** (`irrelevant`)
- `github:1310809822` — **api-evangelist/cladwell** (`irrelevant`)
- `github:1310661333` — **api-evangelist/calibra-medical** (`irrelevant`)
- `github:1310616412` — **api-evangelist/breathe-technologies** (`irrelevant`)
- `github:1309517178` — **api-evangelist/alien** (`irrelevant`)

### `github_api_metadata_profile` — Metadados de perfil/API sem linguagem

- Resultado configurado: `noise_flag`
- Evidência exigida: tópico `apis-json` e nenhuma linguagem detectada, sem exigir `company`
- Itens afetados: **11**
- Distribuição: **0 interesting**, **1 maybe**, **10 irrelevant**
- Taxa de descarte correto: **não aplicável — a regra não propõe descarte ou não teve casos**
- Falsos positivos potenciais se a regra descartasse (`interesting` + `maybe`): **1**
- Conclusão de segurança: somente flag; não descarta

Exemplos:

- `github:1185766592` — **api-evangelist/cdisc** (`maybe`)
- `github:1190450025` — **api-evangelist/coach** (`irrelevant`)
- `github:1311961079` — **api-evangelist/compt** (`irrelevant`)
- `github:1310809822` — **api-evangelist/cladwell** (`irrelevant`)
- `github:1310661333` — **api-evangelist/calibra-medical** (`irrelevant`)

### `insufficient_description` — Descrição/contexto insuficiente

- Resultado configurado: `noise_flag`
- Evidência exigida: descrição vazia e ausência de excerpt de README ou corpo estruturado suportado
- Itens afetados: **45**
- Distribuição: **4 interesting**, **8 maybe**, **33 irrelevant**
- Taxa de descarte correto: **não aplicável — a regra não propõe descarte ou não teve casos**
- Falsos positivos potenciais se a regra descartasse (`interesting` + `maybe`): **12**
- Conclusão de segurança: somente flag; não descarta

Exemplos:

- `hacker_news:49464448` — **Cohere Parse: Enterprise document intelligence at scale** (`interesting`)
- `hacker_news:49463616` — **Show HN: AI engineer course where every lesson is runnable Spring Boot project** (`maybe`)
- `hacker_news:49464504` — **EU slips further behind China, US in race for critical minerals** (`irrelevant`)
- `hacker_news:49464474` — **Mljar Studio: The Claude Code for Data Science** (`maybe`)
- `hacker_news:49464464` — **Why LLMs keep failing their Big Five personality tests** (`irrelevant`)

### `github_archived_repository` — Repositório GitHub arquivado

- Resultado configurado: `noise_flag`
- Evidência exigida: metadado GitHub `archived=true`
- Itens afetados: **0**
- Distribuição: **0 interesting**, **0 maybe**, **0 irrelevant**
- Taxa de descarte correto: **não aplicável — a regra não propõe descarte ou não teve casos**
- Falsos positivos potenciais se a regra descartasse (`interesting` + `maybe`): **0**
- Conclusão de segurança: somente flag; não descarta

Exemplos:

- Nenhum caso correspondente no Gold Set v0.2.

## Regras consideradas seguras nesta amostra

- `github_explicit_profile_disclaimer`: 1/1 item afetado era `irrelevant`; nenhum `interesting` ou `maybe`.
- `github_company_catalog_signature`: 7/7 itens afetados eram `irrelevant`; nenhum `interesting` ou `maybe`.

As três regras de duplicação exata permanecem candidatas estruturais de alta confiança, mas afetaram zero itens porque o Gold Set já contém IDs e URLs únicos. Portanto, o Gold Set não mede sua precisão. Todas continuam em shadow mode.

## Regras mantidas somente como `noise_flag`

- `github_api_metadata_profile`: 11 itens; 10 `irrelevant` e 1 `maybe`. A variante ampla não pode descartar o caso `maybe`.
- `insufficient_description`: 45 itens; 4 `interesting`, 8 `maybe` e 33 `irrelevant`. Título e URL ainda podem conter sinal suficiente.
- `github_archived_repository`: nenhum caso no Gold Set; arquivo não implica irrelevância e a regra nunca descarta.

`consolidated_multiple_lenses` retorna `keep`: múltiplas lenses são proveniência consolidada da mesma identidade, não repetição a remover.

## Regras rejeitadas ou não implementadas

- **Owner específico:** `owner == api-evangelist` não foi implementado. O owner é evidência diagnóstica, não regra de produto, e o Gold Set contém um item `maybe` desse owner.
- **Perfil amplo como descarte:** `apis-json` + linguagem ausente não pode virar descarte; atingiria 1 `maybe`. Permanece apenas como flag.
- **Descrição ausente como descarte:** rejeitada; atingiria 4 `interesting` e 8 `maybe`.
- **Repositório vazio/trivial:** não implementada. Os dados atuais não incluem árvore, quantidade de arquivos ou outra evidência estrutural suficiente. Stars, linguagem ausente e descrição curta não bastam.
- **Fork:** não implementada. `forks` é contagem de forks recebidos, não informa se o repositório é um fork; mesmo esse estado geraria no máximo uma flag.
- **Developer tooling, saúde, IA, fonte, lens, idade, popularidade, testabilidade ou relação Namu:** rejeitadas como regras determinísticas por exigirem interpretação de oportunidade.
- **Duplicação semântica:** não implementada; não há embeddings, similaridade textual ou agrupamento por assunto.

## Shadow mode e preservação do bruto

O pipeline calcula as decisões depois que cada lote de `RawItem` já foi persistido. `DiscoveryResult.items` mantém todos os itens na ordem de coleta; o relatório bruto registra as decisões como uma camada derivada. Não há `DELETE`, alteração do schema ou substituição de payload bruto.

## Limitações

- O Gold Set contém 130 itens, dos quais 40 são GitHub; assinaturas perfeitas nesta amostra podem falhar em ciclos futuros.
- O Gold Set já está deduplicado, então não mede a precisão das regras de identidade ou URL canônica.
- A descrição usada na avaliação é o `short_description` exportado; payloads reais podem oferecer contexto adicional.
- Não há exemplos arquivados nem metadado confiável de fork no conjunto.
- `noise_flag` é evidência para inspeção futura, não baixa prioridade nem classificação de relevância.

## Confirmações de escopo

- Nenhum LLM, API de IA, embedding, score ou classificador foi usado.
- Nenhum label ou `human_reason` do Gold Set foi alterado.
- Nenhuma fonte, lens, collector, watchlist, dashboard ou scheduler foi adicionado.
- O Reddit não foi consultado novamente e seu collector não foi alterado.
- O M2 permanece em shadow mode; não houve avanço para M3.
