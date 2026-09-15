# GitHub Discovery Lens Analysis — Gold Set v0.2

> Análise determinística dos julgamentos humanos do M1D.1. Não contém classificação automática, Opportunity Score, LLM ou decisão sobre ajustes nas lenses.

## Escopo validado

- Registros revisados no workbook: **43**
- Registros GitHub incluídos: **40**
- Registros não GitHub excluídos: **3**
- Itens anteriores preservados: **90**
- Gold Set v0.2: **130 julgamentos humanos**

## Distribuição dos 40 itens GitHub

| Label | Quantidade | Percentual |
|---|---:|---:|
| `interesting` | 17 | 42.5% |
| `maybe` | 4 | 10.0% |
| `irrelevant` | 19 | 47.5% |
| **Total** | **40** | **100.0%** |

## Qualidade por discovery lens

| Discovery lens | Total | Interesting | Maybe | Irrelevant | % interesting | % interesting + maybe |
|---|---:|---:|---:|---:|---:|---:|
| `health_wellness` | 8 | 0 | 1 | 7 | 0.0% | 12.5% |
| `wearables_sensors` | 8 | 2 | 0 | 6 | 25.0% | 25.0% |
| `voice_vision_multimodal` | 8 | 6 | 0 | 2 | 75.0% | 75.0% |
| `local_new_interfaces` | 8 | 5 | 2 | 1 | 62.5% | 87.5% |
| `personal_data_experiments` | 8 | 4 | 1 | 3 | 50.0% | 62.5% |

## Comparação inicial entre as lenses

- Mais `interesting`: **`voice_vision_multimodal`**, com **6** de 8.
- Mais `interesting + maybe`: **`local_new_interfaces`**, com **7** de 8 (87.5%).
- Maior ruído observado: **`health_wellness`**, com **7** de 8 itens `irrelevant`.
- A lens direta `health_wellness` produziu **1/8** itens `interesting + maybe` (12.5%).
- O agrupamento analítico de capacidades transferíveis (`voice_vision_multimodal`, `local_new_interfaces` e `personal_data_experiments`) produziu **18/24** (75.0%).

Esta diferença sugere, nesta amostra, maior eficiência das buscas orientadas a capacidades transferíveis do que da busca direta por health/wellness. Com apenas oito itens por lens e uma única coleta, ela não demonstra causalidade nem superioridade permanente.

## Padrões recorrentes de ruído

As regras abaixo são explícitas, determinísticas e não exclusivas. Um item pode aparecer em mais de um padrão. Somente itens rotulados pelo humano como `irrelevant` são contados como ruído.

| Padrão | Casos | Lenses | Regra observável |
|---|---:|---|---|
| Perfil, catálogo ou stub sem projeto executável | 10 | `health_wellness`=4, `wearables_sensors`=5, `personal_data_experiments`=1 | label=irrelevant e owner=api-evangelist, ou human_reason contém termos explícitos de perfil/stub/catálogo/ausência de software |
| Infraestrutura ou ferramenta restrita ao desenvolvimento | 2 | `health_wellness`=1, `voice_vision_multimodal`=1 | label=irrelevant e human_reason contém termos explícitos de desenvolvimento, framework/runtime ou infraestrutura |
| Implementação inexistente, muito fina ou exercício básico | 4 | `health_wellness`=1, `wearables_sensors`=1, `voice_vision_multimodal`=1, `personal_data_experiments`=1 | label=irrelevant e human_reason registra falta de implementação, conteúdo vazio, exercício básico ou projeto sem valor |

### Perfis, catálogos e stubs de empresas

- Casos `irrelevant` identificados pela regra combinada: **10**.
- Motivos que mencionam explicitamente perfil, stub, catálogo ou ausência de software: **8**.
- Owner `api-evangelist`: **11** resultados; **10 irrelevant** e **1 maybe**.
- Distribuição dos `irrelevant` desse owner: `health_wellness`=4, `personal_data_experiments`=1, `wearables_sensors`=5.
- Sinais objetivos presentes nos 11 resultados desse owner: 11 sem linguagem detectada, 11 com tópico `apis-json`, 11 com no máximo 1 star e 7 com tópico `company`.

Esses sinais podem apoiar uma futura regra auditável, mas nenhum deles deve ser usado isoladamente: ausência de linguagem ou baixa tração também ocorre em projetos pequenos legítimos.

### Owners recorrentes

- `api-evangelist`: **11** itens
- `owen282000`: **2** itens

### Exemplos — Perfil, catálogo ou stub sem projeto executável

- `github:1190450025` — **api-evangelist/coach** (`wearables_sensors`): Sem valor comercial
- `github:1311961079` — **api-evangelist/compt** (`health_wellness`): É apenas um perfil/stub de uma empresa catalogada pelo API Evangelist, sem software, protótipo ou capacidade testável para gerar valor de inovação.
- `github:1310809822` — **api-evangelist/cladwell** (`wearables_sensors`): Um perfil/stub da empresa Cladwell dentro do API Evangelist, sem software, protótipo ou funcionalidade testável para o nosso radar.
- `github:1310661333` — **api-evangelist/calibra-medical** (`wearables_sensors`): Apesar de ser uma empresa da área médica, este repositório é apenas um perfil/stub do API Evangelist, sem software, protótipo ou capacidade testável para o radar de inovação.
- `github:1288297200` — **api-evangelist/classpass** (`health_wellness`): Apesar de descrever uma plataforma real de fitness e wellness com API de parceiros, este repositório é apenas um perfil informativo do API Evangelist e não contém software ou algo que possamos prototipar diretamente.
- Mais 5 correspondência(s) não exibida(s).

### Exemplos — Infraestrutura ou ferramenta restrita ao desenvolvimento

- `github:1326527326` — **kenlin8827/opencode-prime** (`health_wellness`): Suíte multiagente voltada diretamente para engenharia de software no OpenCode, com agentes especializados, MCPs, revisão de código, guardrails e governança de modelos; útil para desenvolvedores, mas fora do foco de inovação não-dev que estamos buscando.
- `github:1314778823` — **hpnkv/a11** (`voice_vision_multimodal`): Runtime/framework para desenvolvedores construírem e orquestrarem agentes de IA, chamadas de modelos e pipelines multimodais; tecnicamente robusto, mas é infraestrutura de desenvolvimento, não uma capacidade de negócio ou experiência diretamente testável.

### Exemplos — Implementação inexistente, muito fina ou exercício básico

- `github:1348726778` — **abdullahfarooqui2004/Authentication-Module** (`health_wellness`): Projeto sem valor
- `github:1348729924` — **Monishwaran2005/Customer-personality-Data-Cleaning** (`personal_data_experiments`): Exercício básico de limpeza e pré-processamento de dados de clientes com Python/Pandas, sem tecnologia, capacidade nova ou proposta testável que gere valor de inovação por si só.
- `github:1348732903` — **eljagjonaj/Closetly-Dress-well-Feel-like-yourself** (`wearables_sensors`): Não tem nada
- `github:1348735516` — **raheemtolani30-lgtm/ai-evaluation-benchmarks** (`voice_vision_multimodal`): A proposta seria avaliar outputs de IA generativa com benchmarks de factualidade, lógica e alinhamento, mas o repositório hoje praticamente não tem implementação nem datasets para testar.

## GitHub versus HN/RSS do Gold Set anterior

| Amostra | Total | Interesting | Maybe | Irrelevant | % interesting | % maybe | % irrelevant | % interesting + maybe |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GitHub — M1D | 40 | 17 | 4 | 19 | 42.5% | 10.0% | 47.5% | 52.5% |
| HN/RSS — Gold Set v0.1 | 90 | 10 | 22 | 58 | 11.1% | 24.4% | 64.4% | 35.6% |

Nesta amostra, GitHub apresentou proporção maior de `interesting` e de `interesting + maybe`. HN/RSS apresentou proporção maior de `maybe` e `irrelevant`. O resultado é descritivo: os ciclos têm fontes, formatos de evidência e tamanhos diferentes e não demonstram superioridade definitiva de uma fonte.

## Possible Discovery Calibration Points

### 1. Concentração de perfis do owner `api-evangelist`

- Evidência: **11/40** resultados vieram do mesmo owner; **10** foram `irrelevant`.
- Possível problema: diversidade nominal entre empresas, mas baixa diversidade real de repositórios executáveis.
- Possível direção: considerar concentração por owner e marcadores explícitos de perfil/stub antes da próxima coleta, sem usar stars ou ausência de linguagem isoladamente.

### 2. `health_wellness` ampla e pouco eficiente nesta amostra

- Evidência: **7/8 irrelevant** e **12.5% interesting + maybe**.
- Possível problema: termos temáticos encontram descrições de empresas e menções de wellness sem capacidade executável.
- Possível direção: revisar humanamente termos e qualificadores da lens para distinguir tema de saúde de projeto, demo ou capacidade concreta.

### 3. `wearables_sensors` encontrou sinais e catálogos

- Evidência: **2 interesting** e **6 irrelevant**; **5** resultados vieram de `api-evangelist`.
- Possível problema: descrições comerciais de wearables competem com projetos implementados.
- Possível direção: preservar a capacidade de encontrar projetos pequenos e modelos on-device, avaliando marcadores objetivos de repositório executável.

### 4. Lenses orientadas a capacidades tiveram melhor rendimento inicial

- Evidência: **18/24** itens `interesting + maybe` no agrupamento de capacidades transferíveis.
- Possível problema: concluir cedo demais que termos de capacidade sempre superam termos de domínio.
- Possível direção: repetir a coleta em outros períodos mantendo diversidade e comparar intervalos antes de alterar as lenses.

### 5. Implementações vazias, básicas ou exclusivamente técnicas

- Evidência: **2** casos developer-only e **4** casos de implementação fina/básica pelas regras textuais.
- Possível problema: recência extrema encontra repositórios recém-criados, exercícios ou infraestrutura sem experiência de produto.
- Possível direção: investigar sinais objetivos como presença de implementação, release ou demo, sem criar filtro até validar o risco de perder experimentos emergentes.

## Pontos novos para Signal Policy

Os 40 julgamentos não revelaram contradição importante ainda não coberta pela Signal Policy v0.2. Eles reforçam três princípios existentes: saúde não basta; developer tooling sem consequência permanece fora do foco; e capacidade testável pode tornar projetos pequenos interessantes. Perfis/stubs são principalmente um problema de qualidade da descoberta, não uma nova regra de relevância.

## Limitações

- A amostra contém somente 40 itens GitHub, oito por lens, de uma única coleta.
- Os agrupamentos de ruído usam correspondência textual e metadados explícitos; não compreendem contexto semântico e podem se sobrepor.
- A concentração de um owner pode ser episódica e não deve ser generalizada sem novas coletas.
- A comparação com HN/RSS usa ciclos e formatos de conteúdo diferentes.
- Nenhuma lens, query, classificação humana ou Signal Policy foi alterada por esta análise.
