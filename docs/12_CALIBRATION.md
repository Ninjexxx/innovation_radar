# Calibration — M4

> Comparação entre a recomendação do M3 e o label humano do Gold Set v0.2. O objetivo é medir divergências, não validar o sistema como correto. Nenhum label humano, regra, prompt ou política é alterado. A decisão final permanece humana.

## Mapeamento label ↔ recomendação

- `interesting` ↔ `investigate`
- `maybe` ↔ `watchlist`
- `irrelevant` ↔ `archive`

Itens pulados pelo filtro determinístico (M2) nunca chegaram ao provedor; sua decisão efetiva é tratada como `archive`.

## Métricas globais

- Provedor avaliado: **`heuristic-offline`**
- Total comparado: **130**
- Distribuição humana: **27 interesting**, **26 maybe**, **77 irrelevant**
- Concordância exata (mesma categoria): **60** (46.2%)
- Falsos positivos (sistema pede atenção, humano marcou `irrelevant`): **34**
- Falsos negativos (sistema arquiva, humano marcou `interesting`): **5**
- Divergências em `maybe`: **9**

As métricas descrevem apenas os 130 itens do Gold Set e o provedor avaliado. Elas não são previsão para coletas futuras nem uma nota de qualidade absoluta.

## Matriz de confusão

Linhas: label humano. Colunas: categoria equivalente à recomendação do sistema.

| Humano ↓ / Sistema → | investigate | watchlist | archive | Total |
|---|---:|---:|---:|---:|
| `interesting` | 0 | 22 | 5 | 27 |
| `maybe` | 0 | 17 | 9 | 26 |
| `irrelevant` | 0 | 34 | 43 | 77 |

## Prioridade 1 — Falsos negativos (não perder sinais interessantes) (5)

O radar não deve eliminar justamente os sinais pequenos e incomuns que deveria encontrar. Cada item abaixo foi arquivado pelo sistema, mas um humano o considerou `interesting`.

- `hacker_news:49464448` — **Cohere Parse: Enterprise document intelligence at scale** (fonte `hacker_news`, sistema `archive`)
  - Motivo humano: É possível testar e tem grande uso comercial mesmo que não agora, mas futuro
- `hacker_news:49464404` — **A self-hostable MCP for all your connections, memory, skills, and secrets** (fonte `hacker_news`, sistema `archive`)
  - Motivo humano: É possível testar mesmo que não saibamos o valor comercial
- `hacker_news:49455537` — **Show HN: Devx – Autonomous AI coding agent built for Android Termux and desktop** (fonte `hacker_news`, sistema `archive`)
  - Motivo humano: É possível testar mesmo que não saibamos o valor comercial
- `hacker_news:49452990` — **Tailcat – Like netcat, but over Tailscale’s data plane** (fonte `hacker_news`, sistema `archive`)
  - Motivo humano: É possível testar por mais que seja nichado é muito interessante e recente
- `github:1132684547` — **BuildWithAIs/voicekey** (fonte `github`, sistema `archive`)
  - Motivo humano: Aplicativo de ditado por voz local-first que transcreve fala, refina o texto com IA e injeta o resultado diretamente no campo em foco, com potencial testável para produtividade, acessibilidade e documentação em saúde.

## Prioridade 2 — Falsos positivos (ruído que chega ao analista) (34)

Itens que o sistema encaminharia para atenção humana, mas que foram marcados como `irrelevant`.

- `rss:mit_ai:https://news.mit.edu/2026/ai-helps-design-new-materials-that-work-in-real-world-0826` — **AI helps design new materials that work in the real world** (fonte `rss`, sistema `watchlist`)
  - Motivo humano: Artigo genérico sobre IA
- `hacker_news:49463403` — **Show HN: BAIhAIs – an autonomous art school for AI agents** (fonte `hacker_news`, sistema `watchlist`)
  - Motivo humano: Não tem vínculo com o nosso propósito
- `hacker_news:49458161` — **Nvidia agrees to acquire Hugging Face for $13B** (fonte `hacker_news`, sistema `watchlist`)
  - Motivo humano: É um artigo que tem haver com IA, mas é informativo, não é possível criar impacto inicial
- `rss:mit_ai:https://news.mit.edu/2026/generating-scenarios-extreme-events-without-extreme-data-0824` — **Generating scenarios for extreme events, without extreme data** (fonte `rss`, sistema `watchlist`)
  - Motivo humano: Artigo interessante de IA mas genérico e sem vínculo com o que podemos construir
- `hacker_news:49433292` — **Apple introduces M6 and M5 Ultra** (fonte `hacker_news`, sistema `watchlist`)
  - Motivo humano: É um conteúdo informativo da Apple, não tem valor e nem é possível testar nada
- `rss:mit_ai:https://news.mit.edu/2026/paving-way-for-greener-ammonia-production-0820` — **Paving the way for greener ammonia production** (fonte `rss`, sistema `watchlist`)
  - Motivo humano: Sem conteúdo que agregue a Namu
- `rss:google_health:https://blog.google/company-news/outreach-and-initiatives/google-org/ai-training-rural-health-clinics/` — **Google.org and the Johnson & Johnson Foundation are launching a $10 million initiative to train rural U.S. healthcare workers in AI.** (fonte `rss`, sistema `watchlist`)
  - Motivo humano: É relacionado a healthcare, mas é apenas informativo
- `rss:medium_healthtech:https://medium.com/p/f1edcf0c9dc1` — **The Hospital’s Open Secret: Inside the Rise of Shadow AI in Healthcare** (fonte `rss`, sistema `watchlist`)
  - Motivo humano: É informativo, por mais que seja relacionado a saúde
- `hacker_news:49452037` — **Show HN: Build your own theme park** (fonte `hacker_news`, sistema `watchlist`)
  - Motivo humano: Sem valor algum
- `hacker_news:49437283` — **Nitter and XCancel receive cease and desist notices** (fonte `hacker_news`, sistema `watchlist`)
  - Motivo humano: Sem valor algum
- `rss:mit_ai:https://news.mit.edu/2026/when-ai-art-has-no-author-generated-images-often-cant-be-traced-to-training-data-0818` — **When AI art has no author: Study finds generated images often can’t be traced to training data** (fonte `rss`, sistema `watchlist`)
  - Motivo humano: Sem valor algum
- `rss:medium_healthtech:https://medium.com/p/42f49b0f4c45` — **Clinical AI in India : A Good Algorithm Is Not Good Business** (fonte `rss`, sistema `watchlist`)
  - Motivo humano: Mesmo que seja relacionado a saúde, o conteúdo é muito informativo
- `hacker_news:49464447` — **Show HN: KnotQ – Calendar and Organization Planner** (fonte `hacker_news`, sistema `watchlist`)
  - Motivo humano: Para uso pessoal é ótimo, mas totalmente irrelevante comercialmente
- `rss:medium_healthtech:https://medium.com/p/1750427ffc87` — **Redefining Smart Jewelry: Inside KEHON Tech’s Zero-Subscription AI Ring Architecture** (fonte `rss`, sistema `watchlist`)
  - Motivo humano: Sem valor algum
- `rss:mit_ai:https://news.mit.edu/2026/solving-solvent-problem-sodium-metal-batteries-0804` — **Solving the solvent problem** (fonte `rss`, sistema `watchlist`)
  - Motivo humano: Artigo informativo mas sem valor para o que queremos
- `hacker_news:49455557` — **Show HN: We built the smallest dual-band aircraft tracker** (fonte `hacker_news`, sistema `watchlist`)
  - Motivo humano: Sem valor algum
- `rss:google_health:https://blog.google/innovation-and-ai/technology/health/google-health-check-up-2026/` — **The Check Up with Google 2026** (fonte `rss`, sistema `watchlist`)
  - Motivo humano: Sem valor algum porque a página não tem nada de interessante
- `hacker_news:49410814` — **Show HN: I wrote a BASIC interpreter that boots on UEFI machines** (fonte `hacker_news`, sistema `watchlist`)
  - Motivo humano: Deu problema 404
- `rss:mit_ai:https://news.mit.edu/2026/alexander-rakhlin-named-director-mit-statistics-data-science-center-0803` — **Alexander Rakhlin named director of the MIT Statistics and Data Science Center** (fonte `rss`, sistema `watchlist`)
  - Motivo humano: Artigo informativo genérico
- `rss:medium_healthtech:https://medium.com/p/5fd1a61d0bc5` — **TLH, Advocates & Solicitors advises Arete Institute of Medical Sciences Private Limited on its sale…** (fonte `rss`, sistema `watchlist`)
  - Motivo humano: Sem valor algum
- `rss:mit_ai:https://news.mit.edu/2026/daniela-rus-receives-bavarian-minister-presidents-high-tech-prize-0730` — **Daniela Rus receives Bavarian Minister-President's High-Tech Prize** (fonte `rss`, sistema `watchlist`)
  - Motivo humano: Sem valor algum
- `hacker_news:49441375` — **Show HN: TeXbrain, a LaTeX editor that runs pdfTeX in the browser via WASM** (fonte `hacker_news`, sistema `watchlist`)
  - Motivo humano: Ferramenta para rodar um editor LaTeX no browser
- `hacker_news:49449648` — **Show HN: How much of Hacker News is about AI?** (fonte `hacker_news`, sistema `watchlist`)
  - Motivo humano: Um contador para dizer quanto tempo desde a última notícia com o termo "AI" no título
- `github:1348726778` — **abdullahfarooqui2004/Authentication-Module** (fonte `github`, sistema `watchlist`)
  - Motivo humano: Projeto sem valor
- `github:1348729924` — **Monishwaran2005/Customer-personality-Data-Cleaning** (fonte `github`, sistema `watchlist`)
  - Motivo humano: Exercício básico de limpeza e pré-processamento de dados de clientes com Python/Pandas, sem tecnologia, capacidade nova ou proposta testável que gere valor de inovação por si só.
- `github:1326527326` — **kenlin8827/opencode-prime** (fonte `github`, sistema `watchlist`)
  - Motivo humano: Suíte multiagente voltada diretamente para engenharia de software no OpenCode, com agentes especializados, MCPs, revisão de código, guardrails e governança de modelos; útil para desenvolvedores, mas fora do foco de inovação não-dev que estamos buscando.
- `github:1348732903` — **eljagjonaj/Closetly-Dress-well-Feel-like-yourself** (fonte `github`, sistema `watchlist`)
  - Motivo humano: Não tem nada
- `github:1348734255` — **arjunkukadia/lanczos-eigensolver** (fonte `github`, sistema `watchlist`)
  - Motivo humano: Implementação acadêmica do algoritmo de Lanczos para calcular autovalores/autovetores de matrizes hermitianas e estudar convergência numérica, sem uma aplicação testável ou proposta de valor perceptível para usuário ou negócio.
- `github:1288297200` — **api-evangelist/classpass** (fonte `github`, sistema `watchlist`)
  - Motivo humano: Apesar de descrever uma plataforma real de fitness e wellness com API de parceiros, este repositório é apenas um perfil informativo do API Evangelist e não contém software ou algo que possamos prototipar diretamente.
- `github:884558341` — **api-evangelist/chainlens** (fonte `github`, sistema `watchlist`)
  - Motivo humano: O repositório é apenas um perfil do API Evangelist sobre a plataforma Chainlens; descreve APIs de blockchain e analytics, mas não contém software ou uma capacidade diretamente prototipável para o radar.
- `github:1314778823` — **hpnkv/a11** (fonte `github`, sistema `watchlist`)
  - Motivo humano: Runtime/framework para desenvolvedores construírem e orquestrarem agentes de IA, chamadas de modelos e pipelines multimodais; tecnicamente robusto, mas é infraestrutura de desenvolvimento, não uma capacidade de negócio ou experiência diretamente testável.
- `github:1348735516` — **raheemtolani30-lgtm/ai-evaluation-benchmarks** (fonte `github`, sistema `watchlist`)
  - Motivo humano: A proposta seria avaliar outputs de IA generativa com benchmarks de factualidade, lógica e alinhamento, mas o repositório hoje praticamente não tem implementação nem datasets para testar.
- `github:1347025888` — **phantomsafe42/pokemon-line-calculator** (fonte `github`, sistema `watchlist`)
  - Motivo humano: Ferramenta extremamente específica para planejar batalhas de Pokémon turno a turno, com cálculo de dano, ramificações e importação de saves; sofisticada tecnicamente, mas sem capacidade reaproveitável clara para produto, saúde ou operação.
- `github:1348672420` — **bjornpagen/fitness-ledger** (fonte `github`, sistema `watchlist`)
  - Motivo humano: Por mais que a proposta seja muito boa é vinculado ao WHOOP e no Brasil quase ninguém tem e o público é pequeno

## Divergências em `maybe` (9)

Casos em que a oportunidade depende de contexto ou investigação adicional; a recomendação do sistema diferiu de `watchlist`.

- `hacker_news:49463616` — **Show HN: AI engineer course where every lesson is runnable Spring Boot project** (fonte `hacker_news`, sistema `archive`)
  - Motivo humano: É tipo uma trilha de aprendizado, pode ser útil para colaboradores internos aprender mas não gera nenhum valor no sentido de criação de uma tecnologia/produto pra Namu, é um produto fechado
- `hacker_news:49464474` — **Mljar Studio: The Claude Code for Data Science** (fonte `hacker_news`, sistema `archive`)
  - Motivo humano: É um vídeo com propósito de ensinar, mas ainda sim é genérico
- `rss:google_health:https://blog.google/innovation-and-ai/technology/ai/google-ai-updates-march-2026/` — **The latest AI news we announced in March 2026** (fonte `rss`, sistema `archive`)
  - Motivo humano: É legal porque fala de saúde, mas não pode ser testado, é apenas informativo
- `hacker_news:49458418` — **CEO fired developers to make room for AI. Developers create open source AI CEO** (fonte `hacker_news`, sistema `archive`)
  - Motivo humano: Classifiquei como maybe porque podemos testar, mas não dá para medir o valor
- `hacker_news:49433450` — **New Mac mini, featuring M6 and M5 Pro** (fonte `hacker_news`, sistema `archive`)
  - Motivo humano: Noticia - Apple lança Mac mini com forte salto em IA e foco em processamento local e agentes de IA continuos. Pode ser interessante para experiencias wellness baseadas em IA privada
- `hacker_news:49464343` — **Hot Chips 2026: Intel's Crescent Island – By George Cozma** (fonte `hacker_news`, sistema `archive`)
  - Motivo humano: Notícia sobre nova GPU de datacenter da Intel com capacidade de memória de até 480 GB
- `hacker_news:49448819` — **Meta reaches $17B settlement over social media harms to children** (fonte `hacker_news`, sistema `archive`)
  - Motivo humano: Um talvez muito talvez. Meta terá que limitar e modificar a experi^ncia de adolescentes em suas plataformas por causa de vício. Pode sinalziar uma tendência de maior preocupação com efeitos comportamentais de produtos digitais
- `hacker_news:49439017` — **FDA authorizes first wearable device that monitors ketone and blood sugar levels** (fonte `hacker_news`, sistema `archive`)
  - Motivo humano: Notícia interessante sobre FDA autorizar dispositivos werables para monitorar algumas coisas de forma contínua. Pode ser algo interessante mais pra frente.
- `hacker_news:49464312` — **Shieldprompt – test your LLM against prompt injection – no dependencies** (fonte `hacker_news`, sistema `archive`)
  - Motivo humano: Projeto para testar prompt injection, como inovação não é tão interessante, mas pode ser útil em algum momento. Além disso o projto tem apenas uma estrela, então não sei se é muito confiável

## Divergência por fonte

| Categoria | Total | Concordância | Taxa | FP | FN | Div. maybe |
|---|---:|---:|---:|---:|---:|---:|
| `github` | 40 | 12 | 30.0% | 11 | 1 | 0 |
| `hacker_news` | 61 | 36 | 59.0% | 10 | 4 | 8 |
| `rss` | 29 | 12 | 41.4% | 13 | 0 | 1 |

## Divergência por tipo de sinal

| Categoria | Total | Concordância | Taxa | FP | FN | Div. maybe |
|---|---:|---:|---:|---:|---:|---:|
| `enabling_testable` | 6 | 2 | 33.3% | 2 | 0 | 0 |
| `n/a` | 8 | 8 | 100.0% | 0 | 0 | 0 |
| `new_application` | 56 | 13 | 23.2% | 27 | 0 | 0 |
| `new_behavior` | 3 | 0 | 0.0% | 3 | 0 | 0 |
| `new_capability` | 7 | 2 | 28.6% | 1 | 0 | 0 |
| `strategic_shift` | 2 | 1 | 50.0% | 1 | 0 | 0 |
| `unclear` | 48 | 34 | 70.8% | 0 | 5 | 9 |

## Divergência por developer tooling

| Categoria | Total | Concordância | Taxa | FP | FN | Div. maybe |
|---|---:|---:|---:|---:|---:|---:|
| `n/a` | 8 | 8 | 100.0% | 0 | 0 | 0 |
| `no` | 116 | 50 | 43.1% | 32 | 5 | 9 |
| `yes` | 6 | 2 | 33.3% | 2 | 0 | 0 |

## Perguntas de avaliação (docs/06)

- Quantas coisas irrelevantes ainda consumiriam tempo humano? **34** falsos positivos.
- O radar está eliminando sinais pequenos e incomuns? **5** falsos negativos.
- Developer tooling está dominando a saída? Ver a tabela por developer tooling acima.
- Há diversidade de tipos de oportunidade? Ver a distribuição por tipo de sinal acima.

## Confirmações de escopo

- Nenhum label ou `human_reason` do Gold Set foi alterado.
- Nenhuma regra determinística, prompt, lens ou Signal Policy foi ajustada automaticamente por esta análise.
- A calibração não usa LLM para julgar qualidade; apenas compara recomendação e label.
- As divergências são evidência para decisão humana, não correção automática.
