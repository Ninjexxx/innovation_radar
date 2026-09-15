# Escopo Incremental do MVP

## Objetivo

Evitar que o radar seja construído inteiro antes de validar se as fontes e o processo realmente produzem descoberta útil.

O projeto será evoluído em milestones pequenos e verificáveis.

---

# M0 — Foundation

## Objetivo
Preparar o repositório para desenvolvimento incremental.

## Inclui
- estrutura de pacotes;
- configuração Python;
- SQLite preparado;
- modelos mínimos de dados;
- logging básico;
- testes;
- documentação;
- configuração por ambiente;
- tratamento de secrets.

## Não inclui
- coletores reais;
- LLM;
- dashboard;
- embeddings;
- watchlist inteligente.

## Critério de aceite
A suíte de testes roda em ambiente limpo e a aplicação possui uma estrutura mínima executável.

---

# M1 — Discovery

## Objetivo
Provar que as fontes trazem matéria-prima interessante.

## Fontes iniciais
- Hacker News
- GitHub
- Reddit
- Medium / RSS

## Fluxo

```text
fontes
↓
coletores
↓
normalização
↓
SQLite
↓
relatório bruto Markdown
```

## Regras
- zero IA;
- sem ranking complexo;
- preservar fonte e data;
- evitar duplicatas exatas;
- erros de uma fonte não devem corromper dados já coletados.

## Critério de aceite
Executar o radar e produzir um relatório real com itens coletados das fontes disponíveis.

---

# M1A — Discovery com Hacker News e RSS

## Objetivo
Validar uma primeira fatia do Discovery com Hacker News e feeds RSS configuráveis.

## Inclui
- `newstories`, `showstories` e `beststories` do Hacker News;
- coletor genérico RSS/Atom;
- identidade externa por `(source, source_item_id)`;
- persistência com atualização de itens conhecidos;
- `RunRecord` por execução;
- relatório bruto Markdown para inspeção humana.

## Não inclui
- GitHub;
- Reddit;
- filtros de oportunidade;
- ranking;
- IA ou milestones posteriores.

## Critério de aceite
Executar duas coletas reais pequenas, confirmar o reencontro de itens e inspecionar o SQLite e o relatório bruto.

---

# M1B — Discovery Quality Review / Gold Set v0.1

## Objetivo
Avaliar a qualidade da matéria-prima de Hacker News e RSS antes de ensinar o sistema a priorizar.

## Inclui
- identidade técnica estável para cada feed, separada do nome de exibição;
- ao menos um feed oficial do Medium tratado pelo coletor RSS/Atom genérico;
- amostra real entre 60 e 100 itens únicos, dentro da disponibilidade das fontes;
- exportação CSV reproduzível para revisão humana;
- campos vazios para classificação humana (`human_label` e `human_reason`);
- resumo diagnóstico com contagens por fonte e proveniência, período coberto, duplicatas evitadas e falhas.

## Revisão humana
Os rótulos permitidos são:
- `interesting`;
- `maybe`;
- `irrelevant`.

O sistema não preenche rótulos nem justificativas automaticamente. Depois da revisão humana, a amostra poderá originar:

```text
tests/fixtures/signal_gold_set.json
```

## Não inclui
- novas famílias de fontes;
- ranking ou interpretação automática de qualidade;
- classificação de relevância para a Namu;
- filtros de oportunidade;
- IA, LLM ou embeddings;
- milestones posteriores.

## Critério de aceite
Produzir, a partir do SQLite, uma amostra real legível e diversa de Hacker News e dos feeds configurados, acompanhada por diagnóstico puramente descritivo e pronta para classificação humana.

---

# M1C — Gold Set v0.1 + Human Judgment Analysis

## Objetivo
Transformar a revisão humana concluída em uma referência de avaliação reproduzível e analisar somente os julgamentos fornecidos.

## Inclui
- importação do workbook XLSX revisado;
- validação explícita de labels, motivos, IDs duplicados e quantidade esperada;
- Gold Set JSON determinístico com os 90 itens e hash do arquivo de origem;
- estatísticas gerais e por superfície/feed;
- agrupamentos lexicais transparentes dos motivos humanos;
- possíveis pontos de calibração entre os exemplos reais e a Signal Policy, sem alterar a política.

## Não inclui
- inferência, correção ou geração de labels;
- treinamento, fine-tuning ou classificação automática;
- IA, LLM, embeddings, scores ou clustering;
- novas fontes;
- filtros do M2 ou milestones posteriores.

## Critério de aceite
Importar exatamente os 90 itens revisados, produzir `tests/fixtures/signal_gold_set.json`, gerar a análise Markdown e reproduzir os mesmos arquivos a partir do mesmo XLSX.

---

# M1D — GitHub Discovery

## Objetivo
Adicionar o GitHub como fonte de descoberta de capacidades e experimentos, sem transformar o radar em GitHub Trending ou aplicar julgamento automático.

## Inclui
- coletor isolado sobre a API REST oficial;
- lentes conceituais configuráveis e limitadas por busca;
- janela configurável de atividade recente;
- ordenação da API por atualização e rodízio determinístico entre lentes;
- identidade externa baseada no ID numérico estável do repositório;
- preservação de descrição, proprietário, datas, linguagem, tópicos, stars, forks, issues, licença, homepage e payload da API;
- trecho opcional e limitado de README com origem preservada;
- autenticação opcional por `GITHUB_TOKEN`;
- integração no pipeline, SQLite, relatório bruto e exportação para revisão humana.

## Não inclui
- ranking por popularidade ou Opportunity Score;
- classificação automática ou filtros derivados do Gold Set;
- eliminação de developer tooling no coletor;
- LLM, APIs de IA, embeddings ou clustering;
- Reddit ou qualquer outra fonte nova;
- filtros do M2 ou milestones posteriores.

## Critério de aceite
Executar duas coletas reais pequenas, obter aproximadamente 30 a 50 repositórios únicos distribuídos entre as lentes, observar projetos pequenos e maiores sem duplicação por rename ou lente, inspecionar os limites informados pela API e exportar uma amostra legível com campos humanos vazios.

---

# M1D.1 — GitHub Gold Set v0.2 + Discovery Lens Calibration

## Objetivo
Incorporar ao Gold Set os julgamentos humanos do ciclo GitHub e descrever a qualidade inicial das cinco discovery lenses, sem transformar a observação em filtro ou decisão automática.

## Inclui
- validação integral dos 43 registros do workbook revisado;
- inclusão exclusiva dos 40 registros cuja fonte é `github` e exclusão explícita dos três registros de Hacker News;
- merge determinístico que preserva os 90 julgamentos do Gold Set v0.1;
- Gold Set v0.2 com 130 IDs únicos e proveniência dos dois workbooks;
- estatísticas gerais e por discovery lens;
- identificação textual e auditável de padrões de ruído;
- comparação descritiva entre GitHub e a amostra HN/RSS anterior;
- possíveis pontos de calibração apresentados como evidência, problema e direção para decisão humana.

## Não inclui
- alteração de label ou motivo humano;
- alteração de lens, query, coletor, Signal Policy ou filtro;
- classificação automática, LLM, APIs de IA, embeddings, scores ou clustering;
- Reddit ou qualquer outra fonte nova;
- componentes do M2 ou milestones posteriores.

## Critério de aceite
Preservar exatamente os 90 itens anteriores, importar 40 itens GitHub com distribuição `interesting=17`, `maybe=4` e `irrelevant=19`, obter 130 IDs únicos, gerar análise reproduzível por lens e manter os três registros não GitHub do workbook fora do merge.

---

# M1E — Reddit Discovery

**Status:** Implemented — real validation pending external Reddit approval.

## Objetivo
Adicionar o Reddit como fonte de problemas não atendidos, comportamentos emergentes, experimentos pessoais e usos improvisados de tecnologia, sem tratá-lo como feed de notícias ou ranking por upvotes.

## Inclui
- coletor isolado sobre a Reddit Data API oficial com OAuth aprovado;
- cinco discovery lenses comportamentais configuráveis;
- comunidades configuráveis e sobrepostas por lens;
- buscas ordenadas por `new` e amostra limitada da superfície `/new`;
- janela temporal recente e configurável, validada também pelo timestamp do post;
- rodízio por lens e comunidade;
- identidade externa pelo ID estável do post e deduplicação entre lenses e superfícies;
- normalização para `RawItem`, SQLite, relatório bruto e amostra de revisão humana;
- score, comentários e flair somente como metadados;
- payload público minimizado, sem perfis, mensagens privadas ou árvores de comentários;
- falha explícita quando aprovação, autenticação ou acesso não estiverem disponíveis.

## Não inclui
- scraping HTML como fallback;
- classificação automática, filtros derivados do Gold Set ou Opportunity Score;
- interpretação clínica de relatos pessoais;
- enriquecimento, correlação ou identificação de autores;
- coleta de comentários completos;
- LLM, APIs de IA, embeddings, clustering ou análise de sentimento;
- novas fontes ou componentes de milestones posteriores.

## Critério de aceite
Com um cliente OAuth aprovado pelo Reddit, coletar aproximadamente 30 a 40 posts únicos e recentes, preservar subreddit e lenses, observar diversidade entre comunidades, confirmar reencontros pelo ID do post e exportar uma amostra legível com campos humanos vazios. Sem acesso aprovado, o coletor deve falhar claramente e a limitação deve ser registrada sem workaround.

---

# M2 — Deterministic Filtering

## Objetivo
Reduzir ruído óbvio antes de chamar qualquer LLM.

## Estado atual

Implementado exclusivamente em **shadow mode**: as decisões são calculadas e registradas, mas nenhum item é removido do pipeline ou do SQLite.

## Inclui
- resultados estruturados `keep`, `noise_flag` e `discard_candidate`;
- identidade externa, URL canônica e ID numérico GitHub repetidos;
- registro de uma mesma origem consolidada por múltiplas lenses;
- assinaturas objetivas e conservadoras de perfil/catálogo GitHub;
- flag de descrição/contexto insuficiente;
- flag de repositório GitHub arquivado;
- avaliação reproduzível de todas as regras contra os 130 julgamentos do Gold Set v0.2;
- relatório Markdown com impacto por label, falsos positivos e redução hipotética.

## Não inclui
- descarte físico de itens;
- duplicação semântica, embeddings ou clustering;
- filtros de developer tooling, relevância Namu ou oportunidade;
- regras baseadas somente em popularidade, idade, fonte, lens, autor ou tamanho;
- detecção de fork ou repositório trivial sem evidência estrutural disponível;
- LLM ou qualquer componente do M3.

## Critério de aceite
Executar as regras em shadow mode sobre os 130 itens, manter zero `interesting` e zero `maybe` entre os `discard_candidate` seguros e preservar integralmente os itens brutos.

---

# M3 — Opportunity AI

**Status:** Implemented — provedor default determinístico e offline; provedor de LLM real ainda não integrado.

## Objetivo
Usar IA para interpretar novas possibilidades.

## Perguntas da análise
- O que é?
- O que existe de novo?
- O que isso torna possível?
- Existe nova capacidade?
- Existe potencial de produto?
- Existe relação possível com a Namu?
- É principalmente developer tooling?
- Está emergente ou consolidado?
- Investigar, watchlist ou arquivar?

## Inclui
- contrato de saída estruturada `OpportunityAnalysis` (tipo de sinal, resumo, o que há de novo, nova capacidade, potencial de produto, relevância Namu, developer tooling, cinco scores explicativos de 1 a 5, tração, recomendação e evidência);
- protocolo `OpportunityProvider` substituível e `ProviderContext` neutro;
- provedor padrão `heuristic-offline`, determinístico e sem rede;
- motor que aplica o filtro determinístico do M2 e envia ao provedor somente itens não `discard_candidate`, reportando os pulados;
- comando `analyze-opportunities` sobre o Gold Set ou o SQLite;
- relatório Markdown descritivo.

## Regras
- saída estruturada;
- provedor substituível;
- somente itens pós-filtro são enviados ao modelo;
- o pipeline deve continuar podendo rodar sem LLM.

## Não inclui
- integração de um provedor de LLM real;
- alteração de labels do Gold Set;
- ranking por score (os scores são explicativos);
- componentes do M4 ou milestones posteriores.

## Critério de aceite
Análise reproduzível sobre o gold set e sobre uma execução real. O provedor default roda sem qualquer chave de API, apenas itens pós-filtro chegam ao provedor e a recomendação permanece uma sugestão para decisão humana.

---

# M4 — Calibration

**Status:** Implemented — comparação e relatório de divergências; ajuste de regras/prompts fica como decisão humana futura.

## Objetivo
Comparar o julgamento automático com o julgamento humano.

## Métricas iniciais
- quantos itens irrelevantes chegam ao analista;
- quantos itens interessantes são descartados;
- divergências por categoria;
- principais padrões de falso positivo e falso negativo.

## Inclui
- mapeamento explícito label↔recomendação (`interesting`↔`investigate`, `maybe`↔`watchlist`, `irrelevant`↔`archive`);
- tratamento de itens pulados pelo M2 como `archive` efetivo;
- concordância exata e matriz de confusão;
- falsos positivos, falsos negativos e divergências em `maybe`, com o motivo humano;
- recortes por fonte, tipo de sinal e developer tooling;
- comando `calibrate` e relatório Markdown determinístico.

## Não inclui
- alteração de labels, regras determinísticas, prompts, lenses ou Signal Policy;
- uso de LLM para julgar qualidade;
- ajuste automático baseado nas divergências;
- componentes do M5 ou milestones posteriores.

## Critério de aceite
Produzir um relatório de divergências reproduzível a partir do Gold Set e do provedor configurado, priorizando os falsos negativos. O ajuste de regras/prompts com base nos exemplos reais permanece uma decisão humana, fora do escopo automático desta etapa.

---

# M5 — Signals

## Objetivo
Agrupar itens que representam o mesmo movimento.

Exemplo:

```text
Reddit + GitHub + Medium + HN
↓
um sinal emergente
```

Não implementar embeddings automaticamente. Adicionar apenas se métodos simples forem insuficientes.

---

# M6 — Watchlist

## Objetivo
Permitir que um sinal acumule evidências ao longo do tempo.

Registrar:
- first_seen;
- last_seen;
- novas fontes;
- novas evidências;
- mudança de maturidade;
- mudança de recomendação.

---

# M7 — Delivery

## Objetivo
Produzir um relatório de radar claro para análise humana.

Saída inicial:
- Markdown.

Não criar dashboard antes de validar a qualidade do conteúdo.

---

# M8 — Expansion

Somente após validação dos milestones anteriores.

Possíveis fontes:
- Hugging Face
- arXiv
- TrendShift
- portais especializados
- outras comunidades

Cada nova fonte deve responder a uma lacuna observada.

---

# Fora do escopo inicial

- dashboard sofisticado;
- aplicação web completa;
- Kubernetes;
- múltiplos agentes;
- banco vetorial obrigatório;
- modelo próprio;
- processamento em tempo real;
- dezenas de fontes;
- integração com ClickUp;
- notificações complexas;
- fine-tuning.

---

# Métrica principal

O sucesso inicial não é medido pela quantidade de conteúdo.

A pergunta é:

> **O radar encontrou algo relevante que a equipe provavelmente não encontraria sozinha?**
