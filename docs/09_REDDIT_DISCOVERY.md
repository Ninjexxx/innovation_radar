# Reddit Discovery — M1E

## Objetivo

Usar discussões públicas para encontrar problemas não atendidos, comportamentos emergentes, experimentos pessoais, combinações incomuns e tentativas de solução. A pergunta da fonte é:

> **Que problema, comportamento ou tentativa de solução as pessoas estão revelando?**

O coletor não interpreta relevância, não produz Opportunity Score e não ordena por upvotes.

## Arquitetura e método de acesso

```text
Reddit Data API aprovada
  → OAuth application-only
  → search sort=new + /new
  → rodízio por lens e subreddit
  → deduplicação pelo post ID
  → RawItem
  → SQLite
  → relatório bruto
  → review_sample.csv
  → revisão humana
```

O acesso usa somente:

- `POST https://www.reddit.com/api/v1/access_token`, com `grant_type=client_credentials`;
- `GET https://oauth.reddit.com/r/<subreddit>/search`, com `restrict_sr=true`, `sort=new` e intervalo temporal oficial aproximado;
- `GET https://oauth.reddit.com/r/<subreddit>/new` para uma amostra pequena de posts recentes.

A janela exata é reaplicada localmente sobre `created_utc`. Não há scraping HTML nem fallback anônimo.

Referências oficiais consultadas:

- [Developer Platform & Accessing Reddit Data](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data)
- [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy)
- [Reddit Data API Wiki](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki)
- [Data API Terms](https://redditinc.com/policies/data-api-terms)
- [API endpoint documentation](https://www.reddit.com/dev/api/oauth)

## Autenticação e acesso

Em 27 de agosto de 2026, a documentação oficial informa que:

- o acesso à Data API depende de solicitação e aprovação explícita;
- clientes devem usar OAuth e User-Agent identificável;
- tráfego sem OAuth é bloqueado;
- uso por ou em nome de uma empresa exige autorização escrita e pode exigir contrato;
- o limite gratuito documentado para clientes elegíveis é 100 queries por minuto, calculado como média sobre dez minutos;
- `X-Ratelimit-Used`, `X-Ratelimit-Remaining` e `X-Ratelimit-Reset` devem ser observados.

Configuração necessária, somente por variáveis de ambiente:

```text
REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET
INNOVATION_RADAR_REDDIT_USER_AGENT
```

O User-Agent deve seguir o formato recomendado pelo Reddit, incluindo um usuário de contato. Secrets não entram em URLs, SQLite, relatórios ou logs.

## Discovery lenses e comunidades padrão

As queries são pistas de descoberta. Elas não são regras de relevância ou classificação.

| Lens | Pistas de busca | Comunidades candidatas |
|---|---|---|
| `personal_health_behavior` | self tracking, sleep tracking, symptoms, wearable, biomarkers, health dashboard | `r/QuantifiedSelf`, `r/ouraring`, `r/Garmin` |
| `unmet_needs` | is there anything, does anyone know a way, why doesn't, I wish, how do you track/manage | `r/QuantifiedSelf`, `r/caregiving`, `r/disability` |
| `ai_in_real_life` | I built, I use AI, I made, I combined, my workflow | `r/LocalLLaMA`, `r/selfhosted`, `r/ChatGPT` |
| `accessibility_care_interfaces` | accessibility, caregiver, remote care, elderly, voice, ambient computing | `r/accessibility`, `r/caregiving`, `r/AgingParents` |
| `personal_data_and_automation` | personal data, automation, dashboard, sensors, local tools, personal workflow | `r/selfhosted`, `r/homeassistant`, `r/ObsidianMD` |

Uma comunidade pode servir a mais de uma lens. Lenses, queries e comunidades são substituíveis por `INNOVATION_RADAR_REDDIT_LENSES`.

## Limites da coleta padrão

- Janela: **30 dias**.
- Seleção máxima: **8 posts por lens**, até 40 antes de deduplicações entre lenses.
- Superfície `/new`: **2 posts por subreddit**.
- Busca: ordenada por `new`, nunca por `top`, `hot`, score ou comentários.
- Comentários: somente `num_comments`; nenhuma árvore é consultada.
- Sem retentativas automáticas ou tentativa de contornar HTTP 401, 403 ou 429.

## Identidade, normalização e reencontro

`source_item_id` é o ID estável base36 do post. A identidade persistida é `(reddit, post_id)`. Quando um post aparece em várias lenses, comunidades ou superfícies, ele é mantido uma única vez e acumula os contextos de descoberta.

Campos normalizados:

- título e trecho público do corpo;
- permalink canônico;
- autor público, salvo quando disponível;
- subreddit, data UTC e flair;
- score e quantidade de comentários como metadados;
- lentes, comunidades e URLs de consulta no payload de auditoria.

## Conteúdo pessoal público e privacidade

- O corpo é limitado a 2.000 caracteres.
- O payload contém uma allowlist dos campos necessários, não a resposta completa da API.
- Não são consultados perfis, histórico do autor, mensagens privadas ou comentários.
- Autores `[deleted]` ou `[removed]` são descartados.
- Não há correlação de autores entre comunidades nem enriquecimento fora do Reddit.
- Relatos pessoais não são convertidos em afirmações ou inferências clínicas.
- Nenhum conteúdo Reddit é usado para treinamento, embeddings ou outra forma de IA.
- Conteúdo e identificadores apagados na origem devem ser removidos conforme as políticas do Reddit; a operação prolongada exige um processo compatível de retenção e remoção.

## Exportação para revisão humana

`review_sample.csv` preserva:

- título, trecho, permalink, autor e publicação;
- `r/<subreddit>` e todas as discovery lenses na proveniência;
- score, comentários, subreddit e flair em `available_metrics`;
- `human_label` e `human_reason` vazios.

O resumo Markdown adiciona contagens específicas por lens e subreddit. Nenhuma qualidade é inferida.

## Validação real do M1E

**Status:** Implemented — real validation pending external Reddit approval.

Nenhuma variável Reddit está disponível no ambiente e não existe evidência local de aprovação escrita para o uso empresarial. Seguindo a política oficial e o escopo do milestone, não foi tentado scraping, endpoint anônimo ou credencial improvisada.

Consequentemente, ainda não existem resultados reais para:

- quantidade coletada;
- distribuição por lens ou subreddit;
- duplicatas reais evitadas;
- distribuição real de score/comentários;
- comportamento de uma segunda execução;
- headers de rate limit do cliente aprovado;
- inspeção de uma amostra real para revisão.

A validação sem rede usa payloads controlados e confirma normalização, janela temporal, diversidade, deduplicação, reencontro no SQLite, exportação e falhas de autenticação/acesso. Esses dados de fixture não são apresentados como resultado real.

## Condição para concluir a validação real

1. Obter aprovação do Reddit para o caso de uso da Namu.
2. Configurar as três variáveis de acesso sem versioná-las.
3. Executar uma coleta em banco temporário e registrar os headers de rate limit.
4. Inspecionar 30 a 40 posts e a exportação neutra.
5. Repetir a execução para confirmar reencontros pelo ID.
6. Definir um processo operacional de retenção e remoção antes de conservar conteúdo por período prolongado.
