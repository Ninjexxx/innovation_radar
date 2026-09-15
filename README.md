# Innovation Radar

Radar automatizado de inovação orientado a **novas possibilidades**, e não apenas a tendências ou popularidade tecnológica.

## Objetivo

O projeto busca sinais emergentes que possam representar novas capacidades, novos comportamentos, combinações pouco convencionais de tecnologias, experimentos ou oportunidades de produto, serviço e experiência relevantes para a Namu.

A lógica do radar é:

**Automação descobre → IA filtra → equipe investiga**

O sistema não deve se transformar em um agregador de notícias, GitHub Trending interno ou catálogo de ferramentas para desenvolvedores.

## Princípios

1. **Popularidade é evidência, não descoberta.**
2. O radar procura **novas possibilidades**, não necessariamente tecnologias novas.
3. Ferramentas de desenvolvimento só são relevantes quando habilitam claramente uma nova capacidade de produto, serviço ou experiência.
4. A fonte original não precisa falar de saúde para que o sinal seja relevante.
5. A decisão final continua sendo humana.
6. A arquitetura deve começar simples e evoluir apenas quando houver uma limitação observada.

## Estrutura

```text
innovation-radar/
├── README.md
├── AGENTS.md
├── pyproject.toml
├── .gitignore
├── docs/
│   ├── 01_CONCEPT.md
│   ├── 02_ARCHITECTURE.md
│   ├── 03_MVP_SCOPE.md
│   ├── 04_DECISIONS.md
│   ├── 05_SIGNAL_POLICY.md
│   ├── 06_EVALUATION.md
│   ├── 07_HUMAN_JUDGMENT_ANALYSIS.md
│   ├── 08_GITHUB_DISCOVERY_ANALYSIS.md
│   ├── 09_REDDIT_DISCOVERY.md
│   └── 10_DETERMINISTIC_FILTER_EVALUATION.md
├── src/
│   └── innovation_radar/
│       ├── __main__.py
│       ├── config.py
│       ├── models.py
│       ├── logging_config.py
│       ├── pipeline.py
│       ├── collectors/
│       │   ├── github.py
│       │   ├── hackernews.py
│       │   ├── reddit.py
│       │   └── rss.py
│       ├── normalization/
│       ├── filtering/
│       │   ├── deterministic.py
│       │   └── evaluation.py
│       ├── analysis/
│       ├── reviews/
│       │   └── gold_set.py
│       ├── storage/
│       └── reports/
│           ├── deterministic_filtering.py
│           ├── human_judgment.py
│           ├── markdown.py
│           └── review_sample.py
├── tests/
│   └── fixtures/
└── data/
    ├── raw/
    ├── processed/
    └── reports/
```

## M0 — Foundation

O M0 fornece uma base executável sem coletores, rede ou IA. Ele usa somente a biblioteca padrão do Python em runtime e cria um banco SQLite local com os modelos mínimos `RawItem` e `RunRecord`.

### Requisitos

- Python 3.11 ou superior.

### Criar e ativar o ambiente

No PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

No Linux ou macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

### Instalar

```bash
python -m pip install -e ".[dev]"
```

### Executar os testes

```bash
python -m pytest
```

### Inicializar o banco

```bash
python -m innovation_radar init-db
```

Por padrão, o arquivo é criado em `data/innovation_radar.sqlite3`. Bancos locais são ignorados pelo Git.

As configurações podem ser alteradas diretamente por variáveis de ambiente:

| Variável | Default | Valores |
|---|---|---|
| `INNOVATION_RADAR_DB_PATH` | `data/innovation_radar.sqlite3` | Caminho não vazio para o banco local |
| `INNOVATION_RADAR_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL` |
| `INNOVATION_RADAR_REPORT_DIR` | `data/reports` | Diretório dos relatórios brutos |
| `INNOVATION_RADAR_HN_LIMIT` | `2` | Itens por superfície HN, entre 1 e 100 |
| `INNOVATION_RADAR_RSS_LIMIT` | `2` | Itens por feed, entre 1 e 100 |
| `INNOVATION_RADAR_RSS_FEEDS` | Três feeds de validação | Array JSON de feeds com `id`, `name`, `url` e `category` opcional |
| `INNOVATION_RADAR_REVIEW_SAMPLE_LIMIT` | `12` | Máximo de itens na amostra de revisão, entre 1 e 100 |
| `INNOVATION_RADAR_GITHUB_LENSES` | Cinco lentes conceituais | Array JSON com `id`, `description` e `query` |
| `INNOVATION_RADAR_GITHUB_LIMIT` | `2` | Repositórios por lente, entre 1 e 20 |
| `INNOVATION_RADAR_GITHUB_RECENCY_DAYS` | `60` | Janela de atividade em dias, entre 1 e 3650 |
| `INNOVATION_RADAR_GITHUB_MIN_STARS` | `0` | Piso opcional contra spam, entre 0 e 100; não é ranking |
| `INNOVATION_RADAR_GITHUB_README_LIMIT` | `10` | Máximo de READMEs consultados por execução, entre 0 e 50 |
| `GITHUB_TOKEN` | Ausente | Token opcional para ampliar os limites da API pública |
| `INNOVATION_RADAR_REDDIT_LENSES` | Cinco lenses comportamentais | Array JSON com `id`, `description`, `queries` e `subreddits` |
| `INNOVATION_RADAR_REDDIT_LIMIT` | `8` | Máximo selecionado por lens, entre 1 e 20 |
| `INNOVATION_RADAR_REDDIT_NEW_LIMIT` | `2` | Itens solicitados da superfície `/new` por subreddit, entre 0 e 10 |
| `INNOVATION_RADAR_REDDIT_RECENCY_DAYS` | `30` | Janela recente, entre 1 e 365 dias |
| `REDDIT_CLIENT_ID` | Ausente | ID de um cliente OAuth explicitamente aprovado pelo Reddit |
| `REDDIT_CLIENT_SECRET` | Ausente | Secret do cliente aprovado; nunca é persistido ou registrado |
| `INNOVATION_RADAR_REDDIT_USER_AGENT` | Ausente | Identificação no formato `plataforma:app:versão (by /u/usuário)` |
| `INNOVATION_RADAR_ANALYSIS_PROVIDER` | `heuristic-offline` | Provedor de análise do M3; atualmente apenas `heuristic-offline` |

Exemplo no PowerShell:

```powershell
$env:INNOVATION_RADAR_DB_PATH = "data/local.sqlite3"
$env:INNOVATION_RADAR_LOG_LEVEL = "DEBUG"
python -m innovation_radar init-db
```

O M0 não usa credenciais e não carrega arquivos `.env`.

## M1A — Discovery com Hacker News e RSS

O M1A coleta e normaliza uma amostra pequena, persiste os itens no SQLite e gera um relatório bruto Markdown. Ele não classifica relevância, não calcula score de oportunidade e não ordena itens por popularidade.

### Executar uma coleta

```bash
python -m innovation_radar run
```

Cada execução cria ou atualiza um `RunRecord` e grava o relatório em `data/reports` por padrão. Os status possíveis são `completed`, `partial` e `failed`.

Um item externo é identificado por `(source, source_item_id)`. Reencontros preservam `first_seen_at`, atualizam `collected_at`, métricas e payload, e não criam uma nova linha.

### Hacker News

O coletor usa a API pública oficial:

- `https://hacker-news.firebaseio.com/v0/newstories.json`;
- `https://hacker-news.firebaseio.com/v0/showstories.json`;
- `https://hacker-news.firebaseio.com/v0/beststories.json`;
- `https://hacker-news.firebaseio.com/v0/item/<id>.json`.

As superfícies são consultadas nessa ordem. Score e comentários são armazenados apenas como métricas brutas.

### Feeds RSS de validação

Os defaults usam um identificador técnico estável separado do nome de exibição:

| ID | Nome | Categoria | URL |
|---|---|---|---|
| `mit_ai` | MIT News — Artificial Intelligence | `research` | `https://news.mit.edu/rss/topic/artificial-intelligence2` |
| `google_health` | Google — Health | `health` | `https://blog.google/technology/health/rss/` |
| `medium_healthtech` | Medium — Healthtech | `health` | `https://medium.com/feed/tag/healthtech` |

Para substituir a lista no PowerShell:

```powershell
$env:INNOVATION_RADAR_RSS_FEEDS = '[{"id":"custom","name":"Custom feed","url":"https://example.com/feed.xml","category":"validation"}]'
python -m innovation_radar run
```

O `id` deve permanecer estável; alterações em `name` não alteram a identidade dos itens. O coletor aceita RSS e Atom, inclusive o formato de feed documentado pelo Medium. Ele não segue links para fazer scraping do conteúdo completo.

## M1B — Amostra para revisão humana

Por padrão, o radar coleta uma amostra pequena e diária, adequada para revisão humana leve. Basta executar, sem configurar limites:

```powershell
python -m innovation_radar run
python -m innovation_radar export-review-sample
```

Com os defaults (HN=2, RSS=2, GitHub=2, amostra=12), a lista final fica em torno de uma dúzia de itens diversos, no rodízio entre fontes. A amostra continua neutra: nenhum ranking, score ou julgamento automático decide o que entra.

Para um ciclo maior de validação (por exemplo, entre 60 e 100 itens), aumente os limites explicitamente:

```powershell
$env:INNOVATION_RADAR_HN_LIMIT = "20"
$env:INNOVATION_RADAR_RSS_LIMIT = "10"
$env:INNOVATION_RADAR_REVIEW_SAMPLE_LIMIT = "100"
python -m innovation_radar run
python -m innovation_radar export-review-sample
```

O segundo comando lê os itens únicos do SQLite e grava, no diretório configurado por `INNOVATION_RADAR_REPORT_DIR`:

- `review_sample.csv`: amostra UTF-8 pronta para revisão, com `human_label` e `human_reason` vazios;
- `review_sample_summary.md`: contagens por fonte e superfície/feed, período coberto, duplicatas evitadas e falhas da execução mais recente.

A seleção faz um rodízio determinístico entre grupos de proveniência para preservar diversidade. Ela não usa score, comentários ou qualquer outra métrica de popularidade para ordenar, classificar ou interpretar os itens. A transformação posterior em `tests/fixtures/signal_gold_set.json` depende de revisão humana explícita.

### Página de revisão (HTML estático)

Para revisar de forma mais confortável que no CSV, gere uma página HTML estática a partir da amostra:

```powershell
python -m innovation_radar export-review-page
```

Por default, o comando lê `review_sample.csv` e grava `review.html` no diretório configurado por `INNOVATION_RADAR_REPORT_DIR`. Use `--csv-path` e `--html-path` para caminhos específicos.

A página abre direto no navegador, sem servidor, framework ou rede. Ela mostra a lista enxuta (fonte, título com link, descrição), permite filtrar por fonte e rótulo, marcar cada item como `interesting`, `maybe` ou `irrelevant` com um motivo opcional, e baixar um CSV rotulado (`review_sample_labeled.csv`). Não há ranking, score ou julgamento automático: a ordem é a mesma amostra por rodízio, e a decisão continua humana. O conteúdo coletado é tratado como dado externo não confiável e nunca é interpretado como HTML.

### Memória de revisão (ciclo diário)

Para não revisar o mesmo item duas vezes, registre os rótulos baixados de volta no radar:

```powershell
python -m innovation_radar mark-reviewed "C:\caminho\review_sample_labeled.csv"
```

O comando lê o CSV rotulado, valida os rótulos (`interesting`, `maybe`, `irrelevant`), ignora linhas ainda sem rótulo e grava as decisões numa memória local no SQLite. A partir daí, `export-review-sample` exclui automaticamente qualquer item já revisado. Um item revisado não reaparece; se todos os candidatos já tiverem sido revisados, o export falha pedindo uma nova coleta.

O ciclo diário fica:

```powershell
python -m innovation_radar run
python -m innovation_radar export-review-sample
python -m innovation_radar export-review-page
# abrir review.html, marcar, baixar review_sample_labeled.csv
python -m innovation_radar mark-reviewed review_sample_labeled.csv
```

## M1C — Gold Set v0.1 e análise do julgamento humano

Depois que `review_sample.xlsx` estiver integralmente revisado, importe-o com:

```powershell
python -m innovation_radar import-gold-set "C:\caminho\review_sample.xlsx" --expected-count 90
```

O comando valida toda a planilha antes de escrever qualquer resultado. Ele falha claramente quando encontra:

- label diferente de `interesting`, `maybe` ou `irrelevant`;
- label ou motivo vazio;
- `item_id` duplicado;
- coluna obrigatória ausente;
- métrica que não seja um objeto JSON válido;
- quantidade diferente de `--expected-count`.

Saídas padrão:

- `tests/fixtures/signal_gold_set.json`: referência determinística com os julgamentos humanos e SHA-256 do workbook;
- `docs/07_HUMAN_JUDGMENT_ANALYSIS.md`: distribuição geral, qualidade por superfície/feed, indicadores textuais dos motivos e possíveis pontos de calibração da política.

A análise usa apenas contagens e correspondência lexical transparente. Ela não corrige labels, não decide divergências, não altera `docs/05_SIGNAL_POLICY.md` e não utiliza LLM.

## M1D — GitHub Discovery

O GitHub participa do mesmo comando e pipeline sequencial já usados pelas fontes anteriores:

```powershell
python -m innovation_radar run
python -m innovation_radar export-review-sample
```

O coletor usa somente a API REST oficial:

- `GET https://api.github.com/search/repositories` para encontrar repositórios;
- `GET https://api.github.com/repos/<owner>/<repo>/readme` para enriquecer uma quantidade limitada de candidatos quando o README estiver disponível.

As buscas são separadas em cinco lentes configuráveis: saúde e bem-estar; wearables e sensores; voz, visão computacional e multimodalidade; capacidades locais e novas interfaces; dados pessoais e experimentos transferíveis. Cada busca recebe uma janela `pushed:>=...`, limite próprio e ordenação por `updated`. Os resultados finais passam por rodízio entre lentes e deduplicação pelo ID numérico do repositório. Não há ordenação final por stars.

Stars, forks, issues, linguagem, tópicos e datas permanecem metadados descritivos. O default `INNOVATION_RADAR_GITHUB_MIN_STARS=0` não exclui projetos pequenos; se configurado, esse piso serve somente como controle simples de spam.

Para substituir as lentes no PowerShell:

```powershell
$env:INNOVATION_RADAR_GITHUB_LENSES = '[{"id":"wearable_trials","description":"Wearable experiments","query":"wearable OR biosensor"}]'
$env:INNOVATION_RADAR_GITHUB_RECENCY_DAYS = "30"
python -m innovation_radar run
```

`GITHUB_TOKEN` é opcional. Sem ele, o coletor acessa apenas dados públicos e fica sujeito ao limite de busca não autenticada informado pelo GitHub. Com ele, envia `Authorization: Bearer ...`; o valor nunca é gravado no SQLite, nos relatórios ou nos logs. Não há carregamento de `.env`.

O enriquecimento de README é deliberadamente limitado: somente os primeiros candidatos diversos, até `INNOVATION_RADAR_GITHUB_README_LIMIT`, são consultados. O SQLite preserva um trecho de até 1.200 caracteres, a URL de origem e metadados do arquivo, não uma cópia completa do README. Use `0` para desabilitar essas chamadas adicionais.

Na amostra CSV, a coluna de proveniência contém as lentes que encontraram o repositório, `available_metrics` contém datas e metadados GitHub, e `short_description` inclui o trecho de README quando disponível. Os campos de julgamento humano continuam vazios.

## M1D.1 — Gold Set v0.2 e análise das discovery lenses

Depois da revisão humana de `review_sample_github.xlsx`, faça o merge sobre o Gold Set v0.1 com:

```powershell
python -m innovation_radar merge-github-gold-set "C:\caminho\review_sample_github.xlsx"
```

Antes de escrever, o comando valida os 43 registros, exige exatamente 40 itens com `source=github`, confere a distribuição `interesting=17`, `maybe=4`, `irrelevant=19` e preserva os 90 itens não GitHub já existentes. Os três registros de Hacker News presentes no workbook são validados, mas não entram no merge.

Saídas padrão:

- `tests/fixtures/signal_gold_set.json`: Gold Set v0.2 determinístico com 130 julgamentos e proveniência dos dois workbooks;
- `docs/08_GITHUB_DISCOVERY_ANALYSIS.md`: distribuição por lens, padrões textuais de ruído, comparação com HN/RSS e possíveis pontos de calibração.

O comando pode ser repetido sobre o próprio Gold Set v0.2: registros idênticos não são duplicados e qualquer conflito no conteúdo de um `item_id` interrompe o processo. A análise não altera labels, lentes, queries, filtros ou a Signal Policy e não utiliza LLM.

## M1E — Reddit Discovery

**Status:** Implemented — real validation pending external Reddit approval.

O coletor usa exclusivamente a [Reddit Data API](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki), com OAuth application-only e escopo de leitura. As regras atuais exigem aprovação explícita; usos por ou em nome de empresas também exigem autorização escrita. Não existe fallback para scraping ou endpoints JSON anônimos.

Depois de obter a aprovação e registrar um cliente compatível, configure no PowerShell:

```powershell
$env:REDDIT_CLIENT_ID = "client-id-aprovado"
$env:REDDIT_CLIENT_SECRET = "client-secret-aprovado"
$env:INNOVATION_RADAR_REDDIT_USER_AGENT = "windows:namu-opportunity-radar:v0.1 (by /u/usuario-do-app)"
$env:INNOVATION_RADAR_REDDIT_RECENCY_DAYS = "30"
python -m innovation_radar run
python -m innovation_radar export-review-sample
```

Sem as três variáveis de acesso, a fonte Reddit registra uma falha explícita de autenticação e as demais fontes continuam isoladas. Credenciais não são carregadas de `.env`, persistidas no SQLite ou exibidas nos logs.

As cinco lenses padrão são:

| Lens | Comunidades candidatas padrão |
|---|---|
| `personal_health_behavior` | `r/QuantifiedSelf`, `r/ouraring`, `r/Garmin` |
| `unmet_needs` | `r/QuantifiedSelf`, `r/caregiving`, `r/disability` |
| `ai_in_real_life` | `r/LocalLLaMA`, `r/selfhosted`, `r/ChatGPT` |
| `accessibility_care_interfaces` | `r/accessibility`, `r/caregiving`, `r/AgingParents` |
| `personal_data_and_automation` | `r/selfhosted`, `r/homeassistant`, `r/ObsidianMD` |

Cada comunidade é consultada por busca com `sort=new`; uma amostra pequena de `/new` também é combinada quando `INNOVATION_RADAR_REDDIT_NEW_LIMIT` é maior que zero. O timestamp do post aplica a janela exata, e o rodízio por lens e comunidade evita ordenar por upvotes. O mesmo ID encontrado em várias buscas gera um único `RawItem` com todas as proveniências preservadas.

Para substituir lenses e comunidades:

```powershell
$env:INNOVATION_RADAR_REDDIT_LENSES = '[{"id":"care_needs","description":"Care needs and workarounds","queries":["I wish","how do you manage"],"subreddits":["caregiving","AgingParents"]}]'
```

A amostra CSV apresenta `r/<subreddit>` e todas as discovery lenses na coluna de proveniência. Score, número de comentários e flair aparecem apenas em `available_metrics`; `human_label` e `human_reason` permanecem vazios.

Por minimização de dados, o coletor preserva no máximo 2.000 caracteres do corpo público e não consulta perfis, mensagens privadas ou árvores de comentários. Autores deletados não são armazenados. O uso operacional deve também cumprir as obrigações do Reddit de remover conteúdo ou identificadores que tenham sido apagados na origem.

## M2 — Filtros determinísticos em shadow mode

O M2 calcula ruído objetivo depois da persistência do `RawItem`, sem remover ou alterar itens. Cada decisão é explicável e usa somente:

- `keep`;
- `noise_flag`;
- `discard_candidate`;
- `rule_id`, motivo e evidência observável.

Para reproduzir a avaliação sobre os 130 julgamentos do Gold Set v0.2:

```powershell
python -m innovation_radar evaluate-filters
```

O comando valida `tests/fixtures/signal_gold_set.json` e recria `docs/10_DETERMINISTIC_FILTER_EVALUATION.md`. No conjunto atual, o cenário observado é 8 `discard_candidate`, 48 itens somente com `noise_flag` e 74 `keep`; os 8 candidatos são `irrelevant`, com zero `interesting` e zero `maybe`.

O comando `run` também calcula essas decisões em shadow mode e as registra no relatório bruto. Todos os itens continuam em `DiscoveryResult.items` e no SQLite. Não há classificação de oportunidade, filtro de developer tooling, duplicação semântica, LLM ou componente do M3.

## M3 — Opportunity AI

O M3 introduz a primeira camada de interpretação. Ele produz uma análise estruturada por item seguindo as perguntas de `docs/01_CONCEPT.md` e o contrato de `docs/02_ARCHITECTURE.md` seção 11. A saída não é um ranking e a recomendação (`investigate`, `watchlist`, `archive`) é uma sugestão; a decisão final permanece humana.

O provedor de IA é substituível por trás do protocolo `OpportunityProvider`. O default é `heuristic-offline`: determinístico, sem rede e sem credenciais, para que o pipeline continue executável sem qualquer chave de API. Um provedor de LLM real implementaria o mesmo protocolo sem alterar o motor, a CLI ou o relatório.

Somente itens que sobrevivem ao filtro determinístico do M2 são enviados ao provedor. Itens marcados como `discard_candidate` são pulados e listados no relatório com o motivo.

Para analisar o Gold Set v0.2 e gravar o relatório:

```powershell
python -m innovation_radar analyze-opportunities
```

Para analisar os itens já persistidos no SQLite local:

```powershell
python -m innovation_radar analyze-opportunities --source sqlite
```

Por default, o relatório é gravado em `docs/11_OPPORTUNITY_ANALYSIS.md`. Cada item recebe tipo de sinal, resumo, o que há de novo, nova capacidade, potencial de produto, relevância Namu, sinalização de developer tooling, cinco scores explicativos de 1 a 5, tração e a recomendação sugerida. Nenhum label humano do Gold Set é alterado e nenhuma chave de API é exigida, persistida ou registrada.

## M4 — Calibration

O M4 compara as recomendações do M3 com os labels humanos do Gold Set v0.2, seguindo `docs/06_EVALUATION.md`. Ele mede divergências; não valida o sistema como correto e não ajusta regras ou prompts automaticamente.

O mapeamento é explícito:

- `interesting` ↔ `investigate`
- `maybe` ↔ `watchlist`
- `irrelevant` ↔ `archive`

Itens pulados pelo filtro determinístico do M2 (`discard_candidate`) nunca chegaram ao provedor; sua decisão efetiva é tratada como `archive`, então um item `interesting` pulado conta como falso negativo.

```powershell
python -m innovation_radar calibrate
```

Por default, o relatório é gravado em `docs/12_CALIBRATION.md`. Ele traz concordância exata, matriz de confusão, falsos positivos (sistema pede atenção quando o humano marcou `irrelevant`), falsos negativos (sistema arquiva quando o humano marcou `interesting`), divergências em `maybe` com o motivo humano, e recortes por fonte, tipo de sinal e developer tooling. Os falsos negativos têm prioridade sobre os falsos positivos. As divergências são evidência para decisão humana, não correção automática, e nenhum label do Gold Set é alterado.

## Primeira fase

O primeiro objetivo não é usar IA.

O MVP inicial deve provar que as fontes escolhidas conseguem trazer material que vale a pena analisar:

**Reddit + Hacker News + GitHub + Medium/RSS → normalização → SQLite → relatório Markdown**

Somente depois de validar a matéria-prima entra a camada de IA.

Leia `docs/03_MVP_SCOPE.md` antes de implementar.
