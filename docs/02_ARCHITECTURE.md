# Arquitetura Técnica do Radar Automatizado de Inovação

## Objetivo

Este documento descreve como o radar pode funcionar tecnicamente, desde a descoberta de conteúdo até a entrega de poucos sinais para análise humana.

O foco não é identificar as tecnologias mais populares. O foco é encontrar novas capacidades, comportamentos, experimentos, aplicações inesperadas e combinações que possam abrir possibilidades de produto, serviço ou experiência.

---

## Visão geral

```text
FONTES
  ↓
COLETA
  ↓
NORMALIZAÇÃO
  ↓
FILTROS DETERMINÍSTICOS
  ↓
ARMAZENAMENTO
  ↓
ANÁLISE DE OPORTUNIDADE
  ↓
AGRUPAMENTO DE SINAIS
  ↓
WATCHLIST / INVESTIGAR
  ↓
ANÁLISE HUMANA
```

A primeira versão deve funcionar sem IA.

---

## 1. Fontes

### MVP inicial
- Reddit
- Hacker News
- GitHub
- Medium / RSS

### Fontes futuras
- Hugging Face
- arXiv
- TrendShift
- portais de tecnologia
- veículos de healthtech
- blogs de empresas
- outras comunidades relevantes

Novas fontes só devem ser adicionadas quando resolverem uma limitação observada.

---

## 2. Coletores

Cada fonte deve possuir um coletor isolado.

```text
src/innovation_radar/collectors/
├── reddit.py
├── hackernews.py
├── github.py
└── rss.py
```

Responsabilidade do coletor:
1. buscar conteúdo;
2. preservar metadados úteis;
3. retornar uma estrutura normalizável;
4. não decidir se o item é inovação.

Preferir APIs oficiais ou RSS. Scraping deve ser exceção, respeitando disponibilidade, termos e limitações da fonte.

---

## 3. Modelo normalizado

Todas as fontes devem ser convertidas para um formato interno comum.

Campos iniciais sugeridos:

```text
id
source
source_item_id
title
description
url
author
published_at
first_seen_at
collected_at
raw_metrics
raw_payload_reference
```

O modelo pode evoluir, mas os coletores não devem acoplar o restante da aplicação ao formato da fonte.

---

## 4. Armazenamento

### MVP
SQLite.

### Futuro
PostgreSQL somente se surgir uma limitação real.

Entidades esperadas no futuro:

```text
raw_items
signals
signal_evidence
signal_history
analysis_results
report_runs
```

No MVP 0, `raw_items` e um registro simples de execução já são suficientes.

---

## 5. Preservação do dado bruto

Sempre que tecnicamente e legalmente apropriado, o conteúdo bruto ou os principais metadados originais devem ser preservados antes da transformação.

Isso ajuda a:
- auditar mudanças;
- reproduzir resultados;
- testar novas regras;
- comparar versões do classificador.

Dados derivados nunca devem substituir silenciosamente o dado original.

---

## 6. Filtros determinísticos

Antes de utilizar IA, o pipeline pode eliminar ruído óbvio.

Exemplos:
- duplicatas exatas;
- URLs repetidas;
- reposts;
- conteúdo fora da janela temporal;
- itens sem conteúdo utilizável;
- spam;
- fontes indisponíveis;
- projetos claramente abandonados, quando houver critério objetivo.

Filtros de produto e inovação não devem ser codificados como listas rígidas de palavras-chave.

---

## 7. Filtro de developer tooling

O radar deve reduzir a prioridade de:
- frameworks de agentes;
- SDKs;
- bibliotecas;
- bancos vetoriais;
- observabilidade de LLM;
- wrappers;
- infraestrutura;
- ferramentas de prompting.

Exceção:

> A ferramenta técnica pode entrar quando habilita claramente uma nova capacidade de produto, serviço ou experiência.

Esse filtro deve ser explicável e testável.

---

## 8. Deduplicação

Uma mesma ideia pode aparecer em Reddit, GitHub, Hacker News, Medium e mídia.

No início:
- URL canônica;
- título normalizado;
- domínio;
- palavras-chave simples.

Depois, se necessário:
- similaridade textual;
- embeddings.

Embeddings não são obrigatórios no MVP.

---

## 9. Uso de IA

A IA entra somente depois que a coleta e os filtros básicos forem validados.

Funções principais:
- resumir;
- classificar;
- identificar nova capacidade;
- estimar potencial de produto;
- estimar relação com Namu;
- identificar developer tooling;
- agrupar evidências relacionadas;
- sugerir watchlist, investigar ou arquivar.

A IA não é necessária para:
- coleta;
- normalização;
- banco;
- agendamento;
- métricas básicas;
- relatório bruto.

---

## 10. Abstração de provedor

A arquitetura futura deve isolar o fornecedor de LLM.

Exemplo conceitual:

```python
class LLMProvider:
    def analyze_signal(self, signal):
        ...
```

Possíveis implementações:
- OpenAI
- Anthropic
- Google
- modelo local

A escolha de fornecedor não deve alterar a arquitetura do radar.

---

## 11. Saída estruturada da IA

A análise deve retornar dados previsíveis, não apenas prosa livre.

Exemplo:

```json
{
  "type": "experiment",
  "summary": "...",
  "what_is_new": "...",
  "new_capability": "...",
  "product_possibility": "...",
  "namu_relevance": "...",
  "developer_tooling": false,
  "novelty_score": 4,
  "capability_score": 5,
  "product_score": 4,
  "namu_score": 5,
  "timing_score": 4,
  "traction": "growing",
  "recommendation": "investigate"
}
```

---

## 12. Critérios de priorização

### Principais
- novidade;
- nova capacidade;
- potencial de produto;
- relevância para a Namu;
- timing.

### Secundário
- tração.

Tração deve ser usada como evidência, não como motor de ranking.

---

## 13. Agrupamento de sinais

O radar deve evoluir de item para sinal.

```text
post no Reddit
+
repo pequeno no GitHub
+
artigo no Medium
+
thread no Hacker News
        ↓
um mesmo movimento emergente
```

No MVP inicial isso não precisa ser sofisticado.

---

## 14. Watchlist e memória

Um sinal deve poder acumular evidências ao longo do tempo.

```text
detectado
↓
nova discussão
↓
segundo projeto
↓
paper
↓
startup
↓
empresa maior
```

O objetivo é perceber amadurecimento antes de a ideia se tornar uma categoria consolidada.

---

## 15. Agendamento

MVP:
- uma execução diária; ou
- três execuções por semana.

Não é necessário tempo real.

---

## 16. Orquestração

Primeira opção:
- Python
- GitHub Actions

Não utilizar Kubernetes, filas distribuídas ou frameworks de agentes no MVP.

---

## 17. Entrega

Primeira interface:
- relatório Markdown.

Dashboard só deve ser criado se o relatório provar valor e se tornar insuficiente.

---

## 18. Arquitetura do MVP inicial

```text
REDDIT ───────┐
HACKER NEWS ──┤
GITHUB ───────┤
MEDIUM / RSS ─┘
      │
      ▼
  COLETORES
      │
      ▼
 NORMALIZAÇÃO
      │
      ▼
 FILTROS BÁSICOS
      │
      ▼
    SQLite
      │
      ▼
RELATÓRIO MARKDOWN
      │
      ▼
ANÁLISE HUMANA
```

Sem IA.

---

## 19. Arquitetura após validação da coleta

```text
fontes
  ↓
coleta
  ↓
normalização
  ↓
filtros
  ↓
SQLite
  ↓
LLM
  ↓
análise de possibilidade
  ↓
agrupamento
  ↓
watchlist / investigar
  ↓
relatório
  ↓
analista
```

---

## 20. Regra de evolução

Nenhuma nova fonte ou camada arquitetural deve ser adicionada apenas porque parece interessante.

Ela deve resolver uma limitação observada.

Exemplos:
- adicionar arXiv se novas capacidades científicas estiverem sendo descobertas tarde;
- adicionar embeddings se deduplicação simples estiver falhando;
- trocar SQLite se o banco realmente limitar o sistema;
- criar dashboard se o Markdown deixar de ser suficiente.

---

## Pergunta principal de validação

> **O radar encontrou alguma possibilidade relevante que provavelmente não seria descoberta pela equipe acompanhando apenas as fontes habituais?**
