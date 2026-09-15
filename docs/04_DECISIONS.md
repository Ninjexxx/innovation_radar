# Registro de Decisões

Este arquivo registra decisões importantes do produto e da arquitetura.

---

## D-001 — Radar orientado a oportunidades

**Status:** Aceita

**Decisão:** O sistema será um Opportunity Radar, não um Trending Radar.

**Consequência:** Stars, votos, comentários e popularidade não serão o motor principal de priorização.

---

## D-002 — Popularidade é evidência

**Status:** Aceita

**Decisão:** Tração será armazenada e utilizada como evidência complementar.

**Consequência:** Um projeto pequeno pode ser prioritário se demonstrar uma nova capacidade relevante.

---

## D-003 — Developer tooling não é foco padrão

**Status:** Aceita

**Decisão:** Frameworks, SDKs e infraestrutura técnica serão normalmente reduzidos ou descartados.

**Exceção:** Entram quando habilitam claramente uma nova capacidade de produto, serviço ou experiência.

---

## D-004 — MVP inicial sem LLM

**Status:** Aceita

**Decisão:** A primeira versão deve coletar, normalizar, armazenar e gerar relatório sem usar API de IA.

**Motivo:** Primeiro é necessário validar a qualidade da matéria-prima.

---

## D-005 — SQLite no MVP

**Status:** Aceita

**Decisão:** SQLite será utilizado inicialmente.

**Motivo:** Baixa complexidade e volume esperado compatível.

**Gatilho para revisão:** Somente se limitações reais de concorrência, volume ou operação aparecerem.

---

## D-006 — Relatório Markdown antes de dashboard

**Status:** Aceita

**Decisão:** A primeira interface será um relatório Markdown.

**Motivo:** Um dashboard não melhora uma descoberta ruim.

---

## D-007 — LLM provider substituível

**Status:** Aceita

**Decisão:** Nenhuma regra central do sistema dependerá de um fornecedor específico de IA.

---

## D-008 — Novas fontes exigem justificativa

**Status:** Aceita

**Decisão:** Uma nova fonte só será adicionada para resolver uma lacuna observada.

---

## D-009 — Fundação do M0 com biblioteca padrão

**Status:** Aceita

**Decisão:** O M0 terá a CLI mínima `python -m innovation_radar init-db`, usará `sqlite3` diretamente, configuração por variáveis de ambiente e logging da biblioteca padrão. Não haverá suporte a `.env`, ORM, SQLAlchemy ou Alembic.

**Consequência:** O M0 permanece com zero dependências de runtime e uma estrutura local, explícita e testável.

---

## D-010 — Modelos mínimos e datas em UTC

**Status:** Aceita

**Decisão:** O M0 terá somente os modelos `RawItem` e `RunRecord`. Todas as datas serão normalizadas e persistidas em UTC.

**Consequência:** Entidades de sinal, scores, watchlist e resultados de análise serão adiadas até que seus milestones sejam validados.

---

## D-011 — SQLite como fonte de verdade dos itens brutos

**Status:** Aceita

**Decisão:** No MVP, o SQLite será a fonte de verdade dos itens coletados. Quando necessário, o payload bruto será armazenado como JSON/TEXT no próprio registro.

**Consequência:** O M0 não cria uma segunda persistência em `data/raw` nem referências ou hashes entre banco e arquivos. A pasta permanece reservada para evolução futura.

---

## D-012 — M0 sem credenciais

**Status:** Aceita

**Decisão:** O M0 não requer credenciais. Configurações locais serão fornecidas pelo ambiente, e secrets e bancos locais permanecerão fora do versionamento.

**Consequência:** Nenhuma variável de API, integração externa ou carregador de secrets será criado neste milestone.

---

## D-013 — M1A limitado a Hacker News e RSS

**Status:** Aceita

**Decisão:** A primeira fatia de Discovery será identificada como M1A e utilizará somente Hacker News e RSS. O Human Sample / Gold Set passa a ser M1B e não será implementado nesta etapa.

**Consequência:** GitHub, Reddit e qualquer análise de oportunidade permanecem fora do escopo até uma decisão posterior.

---

## D-014 — Identidade externa e reencontro de itens

**Status:** Aceita

**Decisão:** Um item externo é único pela combinação `(source, source_item_id)`.

**Consequência:** Ao reencontrar um item, o sistema preserva `first_seen_at` e o identificador interno, atualiza `collected_at`, metadados, métricas e payload bruto quando disponíveis, sem criar uma nova linha em `raw_items`.

---

## D-015 — Superfícies de descoberta do Hacker News

**Status:** Aceita

**Decisão:** O coletor usará a API pública oficial para consultar `newstories`, `showstories` e `beststories`. A ordem de coleta não será substituída por ordenação baseada em popularidade.

**Consequência:** Score e quantidade de comentários serão preservados somente como metadados. O coletor não decidirá se um item representa inovação.

---

## D-016 — Coletor RSS genérico e configurável

**Status:** Substituída por D-017

**Decisão:** RSS e Atom serão tratados por um único coletor, com feeds definidos por configuração contendo nome, URL e categoria opcional.

**Consequência:** Novos feeds não exigem um coletor por site. O M1A usará somente uma lista pequena e documentada de feeds de validação, sem crawler ou scraping amplo.

---

## D-017 — Identidade técnica estável dos feeds

**Status:** Aceita

**Contexto:** O nome de um feed é texto de exibição e pode mudar sem que a fonte ou os itens tenham mudado.

**Decisão:** Cada feed configurado terá `id` técnico estável, `name` de exibição, `url` e `category` opcional. A identidade externa dos itens RSS usará o `id`, nunca o `name`.

**Consequência:** Alterar somente o nome de exibição não cria uma nova identidade para os itens. Bancos anteriores ao M1B são considerados temporários e não receberão migração. O feed de tópico do Medium será apenas mais uma configuração do coletor RSS/Atom genérico, sem coletor específico ou scraping.

---

## D-018 — Amostra neutra para revisão humana

**Status:** Aceita

**Decisão:** O M1B exportará no máximo 100 itens brutos em CSV, selecionados de forma determinística por rodízio entre grupos de fonte, superfície e feed. Métricas disponíveis serão apenas reproduzidas; popularidade não será usada para ordenar ou classificar. `human_label` e `human_reason` permanecerão vazios.

**Consequência:** O resumo da amostra terá somente contagens, período e falhas. O Gold Set será criado apenas a partir de revisão humana posterior, sem preenchimento automático de rótulos.

---

## D-019 — Julgamento humano como fonte de verdade do Gold Set v0.1

**Status:** Aceita

**Contexto:** Os 90 itens exportados no M1B foram classificados manualmente com `interesting`, `maybe` ou `irrelevant` e receberam justificativas humanas.

**Decisão:** O M1C importará o XLSX somente após validar integralmente quantidade, labels, motivos e unicidade de `item_id`. O JSON será determinístico, preservará os julgamentos e registrará o hash SHA-256 do workbook. Nenhum label ou motivo será inferido, corrigido ou normalizado.

**Consequência:** A análise terá apenas estatísticas e correspondências lexicais explicitamente documentadas. Possíveis divergências serão apresentadas como perguntas de calibração para decisão humana, sem alteração automática da Signal Policy. O Gold Set não será usado para treinamento ou classificação nesta etapa.

---

## D-020 — Signal Policy v0.2 calibrada pelo Gold Set v0.1

**Status:** Aceita

**Contexto:** A análise de 90 julgamentos humanos mostrou que testabilidade apareceu com frequência nas justificativas, que alguns developer tools foram considerados interessantes por seu potencial experimental, que conteúdo informativo pode representar mudança estratégica e que relação explícita com saúde não garantiu relevância.

**Decisão:** A Signal Policy v0.2 mantém os princípios originais do Opportunity Radar e incorpora cinco tipos de sinal sobrepostos: nova capacidade, nova aplicação ou combinação, novo comportamento ou necessidade, tecnologia habilitadora e testável, e mudança estratégica. Testabilidade passa a ser amplificador, não requisito ou decisão automática. Developer tooling continua fora do foco padrão e só entra quando remove barreira ou tem consequência plausível além da utilidade técnica. Conteúdo informativo passa a ser distinguido entre informação comum e mudança estratégica. Relação com saúde permanece evidência insuficiente isoladamente.

**Consequência:** Exemplos positivos, negativos e ambíguos foram calibrados a partir do Gold Set v0.1 sem alterar seus labels ou motivos. Os tipos não são scores, a popularidade permanece evidência complementar e a decisão final continua humana. Nenhuma regra foi implementada em código nesta etapa.

---

## D-021 — GitHub Discovery por lentes e identidade numérica

**Status:** Aceita

**Contexto:** O GitHub pode revelar novas capacidades e experimentos, mas uma consulta global ordenada por stars reproduziria a lógica de GitHub Trending e favoreceria projetos já consolidados.

**Decisão:** O M1D usará `GET /search/repositories` da API REST oficial com lentes conceituais configuráveis, janela de atividade baseada em `pushed`, limite por lente e ordenação por `updated`. A lista resultante será composta por rodízio entre lentes, sem ordenação final por stars. O ID numérico do repositório será o `source_item_id` estável.

**Consequência:** Renames não criam uma nova identidade e um repositório encontrado por várias lentes aparece uma única vez, preservando todas as proveniências. Stars, forks e demais sinais de tração são armazenados somente como metadados. O piso de stars é opcional, limitado e zero por default; nenhuma política de relevância ou regra de developer tooling é codificada no coletor.

---

## D-022 — Autenticação opcional e contexto limitado de README no GitHub

**Status:** Aceita

**Contexto:** Descrições curtas nem sempre permitem entender um experimento, mas baixar todos os READMEs aumentaria chamadas, volume e acoplamento sem evidência de necessidade.

**Decisão:** O coletor poderá consultar `GET /repos/{owner}/{repo}/readme` para uma quantidade global configurável de candidatos já diversificados. Será preservado apenas um trecho de até 1.200 caracteres com URL de origem e metadados do arquivo. `GITHUB_TOKEN` será opcional; sua ausência mantém a coleta pública funcional e sua presença apenas adiciona autenticação às chamadas oficiais.

**Consequência:** O enriquecimento melhora a revisão humana de uma amostra limitada sem criar uma segunda persistência ou crawler. O token não é registrado, não é exigido por testes e não há suporte a `.env`. Os limites devolvidos nos headers da API ficam disponíveis para inspeção operacional, sem retentativas ou infraestrutura adicional.

---

## D-023 — Gold Set v0.2 preserva o histórico e isola a revisão GitHub

**Status:** Aceita

**Contexto:** O workbook do ciclo M1D contém 43 julgamentos humanos: 40 registros GitHub e três registros de Hacker News que não pertencem à expansão desta fonte. A distribuição validada dos registros GitHub é `interesting=17`, `maybe=4` e `irrelevant=19`.

**Decisão:** O M1D.1 expande o Gold Set v0.1 por merge determinístico: preserva os 90 itens anteriores sem alteração, inclui somente os 40 itens cuja fonte é `github`, recusa IDs conflitantes e registra a proveniência dos dois workbooks. O workbook GitHub de referência tem SHA-256 `48d108ccfbfed71d57280626b8bdb7293b5b578432d0e84af787980435c9868b`.

**Consequência:** O Gold Set v0.2 contém 130 julgamentos humanos e permanece uma referência de avaliação, não um conjunto de treinamento. A análise por lens e os padrões de ruído produzem apenas pontos possíveis de calibração. Nenhuma lens, query, regra de filtragem, Signal Policy ou classificação humana é alterada automaticamente.

---

## D-024 — Reddit somente pela Data API oficial com acesso aprovado

**Status:** Aceita

**Estado da implementação:** Implemented — real validation pending external Reddit approval.

**Contexto:** Em agosto de 2026, a política oficial exige aprovação explícita e OAuth para acessar dados do Reddit. Tráfego não autenticado é bloqueado, e uso por ou em nome de uma empresa exige autorização escrita. O ambiente local do M1E não possui um cliente Reddit aprovado configurado.

**Decisão:** O coletor usa OAuth application-only com `client_credentials`, solicita dados apenas em `https://oauth.reddit.com`, envia User-Agent identificável e observa os headers oficiais de rate limit. `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` e `INNOVATION_RADAR_REDDIT_USER_AGENT` são fornecidos exclusivamente pelo ambiente e nunca são persistidos ou registrados. Não haverá scraping HTML, endpoint anônimo ou biblioteca não oficial como fallback.

**Consequência:** O código, a normalização e os testes podem ser validados sem rede por fixtures. A coleta real permanece bloqueada até existir aprovação do Reddit e credenciais correspondentes; na ausência delas, o pipeline registra falha de autenticação clara e continua isolando as demais fontes.

---

## D-025 — Reddit orientado a comportamentos com minimização de dados pessoais

**Status:** Aceita

**Contexto:** Posts públicos podem revelar necessidades e experimentos úteis, mas também podem conter relatos pessoais de saúde. Upvotes e comentários não medem oportunidade, e o mesmo post pode aparecer em várias lenses ou superfícies.

**Decisão:** O M1E combina cinco lenses comportamentais configuráveis, buscas `sort=new` e uma amostra pequena de `/new`, aplica janela temporal objetiva e diversifica a saída por lens e subreddit. O ID estável do post define a identidade. São preservados somente o post público e os metadados necessários, com corpo limitado a 2.000 caracteres; não são coletados perfis, mensagens privadas, árvores de comentários ou inferências sobre usuários.

**Consequência:** Score e número de comentários permanecem contexto descritivo. A amostra de revisão mostra subreddit e todas as lenses e mantém `human_label` e `human_reason` vazios. Remoções e retenção de conteúdo continuam sujeitas às regras do Reddit e precisam ser consideradas antes de qualquer uso operacional prolongado.

---

## D-026 — Filtros determinísticos conservadores em shadow mode

**Status:** Aceita

**Contexto:** O Gold Set v0.2 contém 130 julgamentos humanos. Descrição ausente atinge 4 itens `interesting` e 8 `maybe`; a assinatura ampla de metadados GitHub `apis-json` sem linguagem atinge 1 `maybe`. Duas assinaturas mais específicas de perfil/catálogo atingem 8 itens, todos `irrelevant`. O conjunto já está deduplicado e não mede a precisão das regras de duplicação exata.

**Decisão:** O M2 retorna somente `keep`, `noise_flag` ou `discard_candidate`, sempre com `rule_id`, motivo e evidência. Regras de duplicação objetiva e assinaturas específicas de perfil/catálogo podem produzir candidatos a descarte. Evidência insuficiente, metadados amplos de perfil e estado arquivado produzem no máximo flags. Uma origem encontrada por múltiplas lenses é mantida como proveniência consolidada. Nesta versão, todas as regras operam em shadow mode depois da persistência bruta.

**Consequência:** Nenhum item é removido ou alterado. A avaliação observada produz 8 `discard_candidate`, todos `irrelevant`, 48 itens cujo resultado final é `noise_flag` e redução hipotética de 6,2%, com zero `interesting` e zero `maybe` candidatos a descarte. Owner, stars, forks, idade, fonte, lens, developer tooling, saúde, IA, testabilidade e relação Namu não são critérios determinísticos de descarte. A liberação de descarte real exige nova decisão humana baseada em evidência futura.

---

## D-027 — Opportunity AI (M3) com provedor substituível e default offline

**Status:** Aceita

**Contexto:** Os milestones anteriores validaram a matéria-prima (coleta, normalização, SQLite, relatório, Gold Set) e os filtros determinísticos em shadow mode. O M3 introduz a primeira camada de IA. As invariantes exigem que o fornecedor de LLM seja substituível, que ele não defina a arquitetura, que o pipeline possa rodar sem qualquer chave de API e que apenas itens pós-filtro sejam enviados ao modelo.

**Decisão:** O M3 define um contrato de saída estruturada (`OpportunityAnalysis`) seguindo `docs/02_ARCHITECTURE.md` seção 11 e as perguntas de análise do M3: tipo de sinal, resumo, o que há de novo, nova capacidade, potencial de produto, relevância Namu, sinalização de developer tooling, cinco scores explicativos de 1 a 5, tração e recomendação (`investigate`, `watchlist`, `archive`). A camada expõe um protocolo `OpportunityProvider` e um `ProviderContext` neutro derivado do `RawItem`. O provedor padrão é `heuristic-offline`, determinístico, sem rede e sem credenciais. O motor `analyze_items` aplica o filtro determinístico do M2 e envia ao provedor somente itens que não são `discard_candidate`; itens pulados são reportados com motivo. Um provedor real de LLM implementaria o mesmo protocolo sem alterar motor, CLI ou relatório.

**Consequência:** O comando `analyze-opportunities` produz um relatório Markdown descritivo (`docs/11_OPPORTUNITY_ANALYSIS.md` por default) a partir do Gold Set ou do SQLite. Os scores são explicativos, não um ranking; a recomendação é uma sugestão e a decisão final permanece humana. Nenhum label do Gold Set é alterado. Nenhuma chave de API é exigida, persistida ou registrada. O provedor heurístico existe para exercitar o pipeline e servir de referência de contrato, não como classificador definitivo.

**Gatilho para revisão:** Integração de um provedor de LLM real, mudança do contrato de saída ou avanço para o M4 (calibração contra o julgamento humano).

---

## D-028 — Calibração (M4) por comparação, sem ajuste automático

**Status:** Aceita

**Contexto:** O M3 produz recomendações estruturadas (`investigate`, `watchlist`, `archive`). O `docs/06_EVALUATION.md` define que a primeira validação real deve comparar a seleção do sistema com o julgamento humano, priorizando não perder sinais interessantes e não deixar developer tooling dominar a saída. O Gold Set v0.2 contém 130 julgamentos humanos (`interesting`, `maybe`, `irrelevant`).

**Decisão:** O M4 compara cada recomendação do M3 com o label humano usando um mapeamento explícito: `interesting`↔`investigate`, `maybe`↔`watchlist`, `irrelevant`↔`archive`. Itens pulados pelo filtro determinístico do M2 (`discard_candidate`) nunca chegam ao provedor; sua decisão efetiva é tratada como `archive`, de modo que um item `interesting` pulado conta como falso negativo. A camada calcula concordância exata, matriz de confusão, falsos positivos (sistema pede atenção quando o humano marcou `irrelevant`), falsos negativos (sistema arquiva quando o humano marcou `interesting`), divergências em `maybe` e recortes por fonte, tipo de sinal e developer tooling. O comando `calibrate` gera `docs/12_CALIBRATION.md`.

**Consequência:** A calibração é descritiva e determinística. Ela não altera labels ou motivos humanos, não ajusta regras determinísticas, prompts, lenses ou a Signal Policy, e não usa LLM para julgar qualidade. As divergências são apresentadas como evidência para decisão humana. Priorizam-se explicitamente os falsos negativos (Prioridade 1) sobre os falsos positivos (Prioridade 2), conforme o `docs/06`. As métricas descrevem apenas os 130 itens e o provedor avaliado; não são previsão nem nota absoluta de qualidade.

**Gatilho para revisão:** Integração de um provedor de LLM real, mudança do mapeamento label↔recomendação, ou uma decisão futura de ajustar regras/prompts com base nas divergências observadas.

---

## D-029 — Interface de revisão como página HTML estática

**Status:** Aceita

**Contexto:** A revisão humana é o fluxo central do radar e a decisão de relevância permanece com a pessoa. Revisar itens direto no CSV é funcional, mas pouco confortável para curadoria. O `docs/03` e o `AGENTS.md` pedem para não criar dashboard, aplicação web ou infraestrutura nova antes de o MVP estar validado.

**Decisão:** O comando `export-review-page` gera uma única página HTML estática a partir do `review_sample.csv` já existente. A página não usa servidor, framework, banco ou rede; embute os dados como JSON e renderiza o conteúdo via `textContent`/atributos (nunca `innerHTML`), tratando o material coletado como dado externo não confiável. A pessoa lê a lista enxuta, filtra por fonte e rótulo, marca `interesting`/`maybe`/`irrelevant` com motivo opcional e baixa um CSV rotulado no mesmo schema esperado por `import-gold-set`. Não há salvamento automático de volta ao arquivo, o que evitaria exigir um servidor local.

**Consequência:** A interface facilita a curadoria sem introduzir infraestrutura persistente: o arquivo abre no navegador e some ao fechar. Nenhum ranking, score ou julgamento automático é adicionado — a ordem é a mesma amostra por rodízio do CSV. A geração do HTML é uma função pura e testável, incluindo o escaping de segurança. Nenhuma dependência de runtime foi adicionada.

**Gatilho para revisão:** Necessidade observada de persistir rótulos automaticamente, colaborar entre várias pessoas ou exibir volume que o formato de arquivo único não comporte.

---

## D-030 — Memória de revisão: item revisado não reaparece

**Status:** Aceita

**Contexto:** No uso diário, a amostra de revisão era selecionada a partir de todo o SQLite por rodízio determinístico, sem noção do que já havia sido revisado. Como a identidade `(source, source_item_id)` faz o reencontro atualizar o item em vez de criar linha nova, executar o ciclo repetidamente tendia a reapresentar itens já julgados. Reavaliar o mesmo conteúdo é desperdício e quebra o fluxo de ~12 itens novos por dia.

**Decisão:** Uma tabela `item_reviews` (item_id, human_label, human_reason, reviewed_at) registra cada decisão humana. O comando `mark-reviewed <csv>` ingere o CSV rotulado baixado da página de revisão, validando `human_label` em `interesting`/`maybe`/`irrelevant`, ignorando linhas sem rótulo e recusando `item_id` duplicado. O `export-review-sample` passa a excluir qualquer item já presente na memória de revisão antes do rodízio. Nesta versão, um item revisado nunca reaparece (Opção 1); mudanças posteriores do item não o reabrem automaticamente.

**Consequência:** O ciclo diário `run → export-review-sample → export-review-page → (revisar e baixar) → mark-reviewed` deixa de repetir itens. Se todos os candidatos já foram revisados, o export falha de forma clara pedindo uma nova coleta. A memória é local, não usa IA e não interpreta conteúdo — apenas confia no rótulo humano. Reabrir itens que evoluíram (por tração ou mudança de estado) fica adiado como parte do M6 completo, quando houver necessidade observada.

**Gatilho para revisão:** Necessidade de reavaliar itens que mudaram materialmente, ou de compartilhar a memória de revisão entre várias pessoas/máquinas.

---

## Template

### D-XXX — Título

**Status:** Proposta / Aceita / Substituída

**Contexto:**  
...

**Decisão:**  
...

**Consequências:**  
...

**Gatilho para revisão:**  
...
