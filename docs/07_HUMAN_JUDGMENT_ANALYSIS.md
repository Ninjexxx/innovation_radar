# Human Judgment Analysis — Gold Set v0.1

> Este relatório analisa exclusivamente labels e motivos fornecidos pela revisão humana. Não contém classificação automática, Opportunity Score ou julgamento sobre a correção das decisões humanas.

## Distribuição geral

| Label | Quantidade | Percentual |
|---|---:|---:|
| `interesting` | 10 | 11.1% |
| `maybe` | 22 | 24.4% |
| `irrelevant` | 58 | 64.4% |
| **Total** | **90** | **100.0%** |

## Qualidade por fonte

| Superfície/feed | Total | Interesting | Maybe | Irrelevant | % interesting | % interesting + maybe |
|---|---:|---:|---:|---:|---:|---:|
| Google — Health [google_health] | 10 | 1 | 6 | 3 | 10.0% | 70.0% |
| MIT News — Artificial Intelligence [mit_ai] | 10 | 1 | 2 | 7 | 10.0% | 30.0% |
| Medium — Healthtech [medium_healthtech] | 9 | 1 | 4 | 4 | 11.1% | 55.6% |
| beststories | 20 | 3 | 5 | 12 | 15.0% | 40.0% |
| newstories | 21 | 2 | 3 | 16 | 9.5% | 23.8% |
| showstories | 20 | 2 | 2 | 16 | 10.0% | 20.0% |

## Motivos humanos

Os agrupamentos abaixo são indicadores lexicais não exclusivos: um mesmo item pode aparecer em mais de um grupo. As regras e os termos usados são mostrados explicitamente; nenhuma categoria altera o label humano.

| Indicador textual | Itens correspondentes | Termos procurados |
|---|---:|---|
| Ausência de valor, vínculo ou aplicação | 25 | `sem valor`, `não tem valor`, `nao tem valor`, `irrelevante`, `sem vínculo`, `sem vinculo` |
| Conteúdo informativo, notícia ou artigo genérico | 38 | `informativ`, `notícia`, `noticia`, `artigo`, `genéric`, `generic` |
| Testabilidade ou impossibilidade de testar | 20 | `test`, `executável`, `executavel`, `demo`, `protótip`, `prototip` |
| Relação explícita com saúde, wellness ou Namu | 14 | `health`, `saúde`, `namu`, `wellness`, `medical`, `paciente`, `farmaco`, `wearable`, `werable` |
| Potencial futuro ou valor ainda incerto | 4 | `futuro`, `mais pra frente`, `algum momento`, `potencial`, `aprofundamento`, `não sabemos`, `nao sabemos` |
| Acesso ou conteúdo insuficiente | 4 | `404`, `não foi possível acessar`, `nao foi possivel acessar`, `incompleto`, `limitação do medium`, `limitacao do medium` |

### Exemplos por indicador

#### Ausência de valor, vínculo ou aplicação

- Artigo interessante de IA mas genérico e sem vínculo com o que podemos construir
- Conteúdo legal mas informativo sem valor inicial
- Sem valor para a Namu, é uma ferramenta interessante mas não usaríamos

#### Conteúdo informativo, notícia ou artigo genérico

- Notícia informativa/geopolítica sem nova capacidade ou oportunidade clara de produto
- É a notícia da morte de uma pessoa
- Artigo genérico sobre IA

#### Testabilidade ou impossibilidade de testar

- Pode virar oportunidade, mas ainda parece experimental e não tem mais detalhes de como começar ou testar
- Esse contéudo não tem como testar inicialmente, mas o conteúdo é muito interessante e lembra o Hippocratic AI
- É um conteúdo informativo da Apple, não tem valor e nem é possível testar nada

#### Relação explícita com saúde, wellness ou Namu

- É tipo uma trilha de aprendizado, pode ser útil para colaboradores internos aprender mas não gera nenhum valor no sentido de criação de uma tecnologia/produto pra Namu, é um produto fechado
- Sem valor para a Namu, é uma ferramenta interessante mas não usaríamos
- Sem conteúdo que agregue a Namu

#### Potencial futuro ou valor ainda incerto

- É possível testar e tem grande uso comercial mesmo que não agora, mas futuro
- É uma ferramenta mas necessário mais aprofundamento para entender o valor
- Notícia interessante sobre FDA autorizar dispositivos werables para monitorar algumas coisas de forma contínua. Pode ser algo interessante mais pra frente.

#### Acesso ou conteúdo insuficiente

- Conteúdo incompleto mas com proposta curiosa
- Artigo interessante, mas não consegui ler completo pela limitação do Medium
- Deu problema 404

## Frequência literal aproximada

- **16×** — Sem valor algum
- **2×** — Conteúdo informativo
- **2×** — Artigo informativo
- **2×** — É possível testar mesmo que não saibamos o valor comercial

## Possible Policy Calibration Points

Os pontos abaixo são candidatos a discussão, encontrados por correspondência textual transparente. Eles não indicam erro do humano nem autorizam mudança automática em `docs/05_SIGNAL_POLICY.md`.

### Developer tooling marcado como interesting

- Regra documental relacionada: As seções 2 e 3 da Signal Policy normalmente reduzem developer tooling sem consequência clara para produto.
- Questão para decisão humana: A exceção de nova capacidade de produto precisa ser detalhada ou a testabilidade prática está recebendo peso próprio?
- Correspondências textuais: **4**

- `hacker_news:49437049` — **Show HN: LatticeDB – Like SQLite but for graph databases** (`interesting`)
  - Motivo humano: Tem valor real mesmo que não inicial e é possível testar
- `hacker_news:49464404` — **A self-hostable MCP for all your connections, memory, skills, and secrets** (`interesting`)
  - Motivo humano: É possível testar mesmo que não saibamos o valor comercial
- `hacker_news:49455537` — **Show HN: Devx – Autonomous AI coding agent built for Android Termux and desktop** (`interesting`)
  - Motivo humano: É possível testar mesmo que não saibamos o valor comercial
- `hacker_news:49452990` — **Tailcat – Like netcat, but over Tailscale’s data plane** (`interesting`)
  - Motivo humano: É possível testar por mais que seja nichado é muito interessante e recente

### Conteúdo informativo marcado como interesting

- Regra documental relacionada: A seção 2 reduz artigos genéricos e conteúdo sem evidência concreta.
- Questão para decisão humana: Afinidade estratégica ou tema de inovação pode justificar interesting mesmo sem ação ou teste imediato?
- Correspondências textuais: **3**

- `rss:google_health:https://blog.google/innovation-and-ai/models-and-research/google-research/amie-for-disease-management-in-nature/` — **New research shows how AMIE, our medical AI, could help manage health conditions.** (`interesting`)
  - Motivo humano: Esse contéudo não tem como testar inicialmente, mas o conteúdo é muito interessante e lembra o Hippocratic AI
- `rss:mit_ai:https://news.mit.edu/2026/qa-eugene-fitzgerald-rethinking-how-innovation-happens-0817` — **Q&A: Rethinking how innovation happens** (`interesting`)
  - Motivo humano: É informativo, mas classifiquei como interessante apenas por se tratar de inovação
- `rss:medium_healthtech:https://medium.com/p/0ec5e76961db` — **Why Healthcare Startups Need Clinical Expertise Before They Scale** (`interesting`)
  - Motivo humano: Classificado como interessante apenas pelo artigo combinar bastante com a nossa empresa Namu, mas é apenas informativo

### Testabilidade aparece em julgamentos positivos

- Regra documental relacionada: A política enfatiza novidade, capacidade e produto, mas não define testabilidade como critério principal isolado.
- Questão para decisão humana: Testabilidade deve se tornar critério explícito ou permanecer evidência operacional de investigação?
- Correspondências textuais: **16**

- `rss:google_health:https://blog.google/innovation-and-ai/technology/health/open-health-stack-software-foundation/` — **Building the future of global health, together** (`maybe`)
  - Motivo humano: Pode virar oportunidade, mas ainda parece experimental e não tem mais detalhes de como começar ou testar
- `rss:google_health:https://blog.google/innovation-and-ai/models-and-research/google-research/amie-for-disease-management-in-nature/` — **New research shows how AMIE, our medical AI, could help manage health conditions.** (`interesting`)
  - Motivo humano: Esse contéudo não tem como testar inicialmente, mas o conteúdo é muito interessante e lembra o Hippocratic AI
- `rss:google_health:https://blog.google/innovation-and-ai/technology/health/mental-health-updates/` — **An update on our mental health work** (`maybe`)
  - Motivo humano: Artigo informativo bem interessante, mas sem a possibilidade de testar ou ser um ativo proprietário porque é do Gemini
- `rss:medium_healthtech:https://medium.com/p/fcbb9b3ba9bd` — **How to Build a Pharmacovigilance Case Intake Platform for Multi-Source Safety Reporting** (`maybe`)
  - Motivo humano: Artigo informativo relacionado a saúde e a farmaco, mas sem possibilidade de teste
- `hacker_news:49464448` — **Cohere Parse: Enterprise document intelligence at scale** (`interesting`)
  - Motivo humano: É possível testar e tem grande uso comercial mesmo que não agora, mas futuro
- Mais 11 correspondência(s) não exibida(s).

### Potencial futuro sem aplicação imediata recebe julgamento positivo

- Regra documental relacionada: As seções 5 e 9 aceitam timing inicial e aplicação ainda pouco clara, especialmente como maybe.
- Questão para decisão humana: A política precisa distinguir melhor potencial futuro suficiente para interesting daquele que deve permanecer maybe?
- Correspondências textuais: **3**

- `hacker_news:49464448` — **Cohere Parse: Enterprise document intelligence at scale** (`interesting`)
  - Motivo humano: É possível testar e tem grande uso comercial mesmo que não agora, mas futuro
- `hacker_news:49439017` — **FDA authorizes first wearable device that monitors ketone and blood sugar levels** (`maybe`)
  - Motivo humano: Notícia interessante sobre FDA autorizar dispositivos werables para monitorar algumas coisas de forma contínua. Pode ser algo interessante mais pra frente.
- `hacker_news:49464312` — **Shieldprompt – test your LLM against prompt injection – no dependencies** (`maybe`)
  - Motivo humano: Projeto para testar prompt injection, como inovação não é tão interessante, mas pode ser útil em algum momento. Além disso o projto tem apenas uma estrela, então não sei se é muito confiável

### Relação direta com saúde aparece em itens maybe

- Regra documental relacionada: A seção 4 diz que saúde não precisa estar na fonte e, por si só, não comprova nova possibilidade.
- Questão para decisão humana: A relação direta com saúde está funcionando apenas como sinal para investigação ou recebendo peso maior do que o documentado?
- Correspondências textuais: **11**

- `rss:google_health:https://blog.google/innovation-and-ai/technology/health/open-health-stack-software-foundation/` — **Building the future of global health, together** (`maybe`)
  - Motivo humano: Pode virar oportunidade, mas ainda parece experimental e não tem mais detalhes de como começar ou testar
- `rss:medium_healthtech:https://medium.com/p/3bb24cfb5e5d` — **VitalChain: Building a Smarter Future for Health Data with AI and Blockchain** (`maybe`)
  - Motivo humano: É um artigo informativo que tem seu valor, mas não podemos fazer nada com essas informações
- `rss:medium_healthtech:https://medium.com/p/40b37d3e4c32` — **Why Digitally Enabled Rehabilitation Centers Represent the Future of Healthcare** (`maybe`)
  - Motivo humano: Conteúdo incompleto mas com proposta curiosa
- `rss:google_health:https://blog.google/innovation-and-ai/technology/health/mental-health-updates/` — **An update on our mental health work** (`maybe`)
  - Motivo humano: Artigo informativo bem interessante, mas sem a possibilidade de testar ou ser um ativo proprietário porque é do Gemini
- `rss:medium_healthtech:https://medium.com/p/fcbb9b3ba9bd` — **How to Build a Pharmacovigilance Case Intake Platform for Multi-Source Safety Reporting** (`maybe`)
  - Motivo humano: Artigo informativo relacionado a saúde e a farmaco, mas sem possibilidade de teste
- Mais 6 correspondência(s) não exibida(s).

## Limitações

- Correspondência por substring não entende contexto, negação, ironia ou equivalência semântica.
- Os grupos de motivos se sobrepõem e não devem ser tratados como classes ou scores.
- A amostra cobre somente Hacker News e os feeds RSS do M1B.
- Qualquer alteração da Signal Policy continua dependendo de decisão humana explícita.
