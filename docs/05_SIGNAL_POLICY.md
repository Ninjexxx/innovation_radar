# Política de Sinais do Radar

**Versão:** 0.2  
**Base de calibração:** Gold Set v0.1, com 90 julgamentos humanos.

## Objetivo

Definir o que o radar deve considerar interessante, irrelevante ou ambíguo sem substituir a decisão humana.

Este documento é a principal referência para classificação e prompts futuros de IA. Os tipos e critérios descritos aqui não são scores e não produzem uma decisão automática.

---

# 1. Princípios preservados

1. **Popularidade é evidência, não descoberta.**
2. O radar procura **novas possibilidades**, não apenas tecnologias novas.
3. Developer tooling não é foco por padrão.
4. Relação explícita com saúde não é suficiente para definir relevância.
5. Um sinal de outro setor pode ser relevante quando sua capacidade for plausivelmente transferível.
6. Testabilidade amplifica o interesse, mas não é requisito obrigatório nem prova de relevância.
7. A decisão final permanece humana.
8. O radar não deve se transformar em catálogo de ferramentas para desenvolvedores, agregador de notícias ou ranking de popularidade.

---

# 2. Tipos principais de sinal

Os tipos podem se sobrepor. Eles servem para explicar por que algo merece atenção, não para calcular um score.

## A. Nova capacidade

Algo passou a ser possível, mais barato, mais simples, mais rápido ou mais acessível.

Pergunta útil:

> **Que barreira prática deixou de existir ou diminuiu materialmente?**

## B. Nova aplicação ou combinação

Tecnologias conhecidas são aplicadas ou combinadas de forma diferente, criando uma possibilidade de produto, serviço, experiência ou operação.

Pergunta útil:

> **A novidade está na tecnologia ou no modo como componentes existentes foram combinados?**

## C. Novo comportamento ou necessidade

Pessoas, organizações ou mercados começam a agir de uma forma que produtos e serviços atuais ainda não atendem bem.

Pergunta útil:

> **Existe uma mudança observável de comportamento, expectativa, risco ou necessidade?**

## D. Tecnologia habilitadora e testável

Uma tecnologia, inclusive developer tooling, remove uma barreira importante ou permite experimentar de forma simples algo que antes não era viável.

Pergunta útil:

> **O que podemos aprender ao testar isso, e qual consequência plausível esse aprendizado teria para produto, serviço ou experiência?**

## E. Mudança estratégica

Uma mudança de mercado, regulação, comportamento, infraestrutura ou modelo de cuidado pode alterar decisões futuras, mesmo quando o conteúdo é informativo e não há experimento imediato.

Pergunta útil:

> **Que decisão futura pode mudar se essa transformação continuar?**

---

# 3. Interpretação dos julgamentos

## `interesting`

Existe evidência clara de pelo menos um tipo de sinal e uma consequência plausível para produto, serviço, experiência, operação ou aprendizado estratégico.

Testabilidade simples pode fortalecer esse julgamento, mas não é obrigatória.

## `maybe`

Existe uma possibilidade plausível, mas a consequência, evidência, transferibilidade, timing ou capacidade de ação ainda é incerta.

Usar `maybe` para preservar casos em que investigação adicional pode esclarecer o valor.

## `irrelevant`

O conteúdo não demonstra consequência relevante além do tema, da popularidade, da utilidade técnica isolada ou da informação comum.

Ser testável, popular, recente ou relacionado a saúde não impede um item de ser `irrelevant`.

---

# 4. O que normalmente não queremos

Por padrão, reduzir prioridade de:

- novos frameworks de agentes sem consequência além do desenvolvimento;
- SDKs, wrappers de LLM e bibliotecas genéricas;
- bancos vetoriais, observabilidade e infraestrutura de inferência sem nova possibilidade associada;
- ferramentas de prompt, editores, monitores e utilitários técnicos de uso restrito;
- benchmark puramente técnico;
- clone de produto existente;
- lançamento comercial sem nova capacidade ou mudança estratégica;
- artigo genérico de “tendências de IA”;
- lista de ferramentas;
- conteúdo SEO sem evidência concreta;
- notícia comum sem consequência para decisões futuras;
- conteúdo healthtech cuja única evidência de relevância seja mencionar saúde.

Esses itens podem ser reconsiderados quando houver evidência concreta de um dos cinco tipos de sinal.

---

# 5. Developer tooling

Developer tooling continua **não sendo foco por padrão**.

Pode ser relevante quando:

- habilita uma capacidade nova;
- remove uma barreira importante;
- reduz materialmente custo ou complexidade;
- permite experimentar algo que antes não era viável;
- possui consequência plausível para produto, serviço, experiência ou aprendizado futuro.

Popularidade, stars, novidade técnica ou facilidade de instalação não são justificativas suficientes.

Perguntas de verificação:

1. O que se torna possível além da atividade de desenvolvimento?
2. Qual barreira concreta é removida?
3. Existe um experimento simples capaz de produzir aprendizado relevante?
4. Há consequência plausível para produto, serviço, experiência, operação ou estratégia?
5. Se a utilidade se limitar ao fluxo de trabalho de desenvolvedores, existe algum motivo adicional para o radar acompanhar?

Se as respostas se limitarem a “é uma ferramenta útil ou popular”, normalmente não priorizar.

---

# 6. Testabilidade como amplificador

Testabilidade não é requisito obrigatório e não substitui novidade, capacidade ou consequência.

Uma tecnologia não deve ser descartada apenas porque ainda não pode ser testada. Mudanças estratégicas, pesquisas e capacidades emergentes podem ser relevantes antes de existir acesso prático.

Ao mesmo tempo:

> **Nova capacidade + possibilidade de experimentação simples é um sinal particularmente interessante para a área de inovação.**

Um teste tem valor quando ajuda a responder uma pergunta relevante. Ser fácil de executar, por si só, não transforma uma ferramenta técnica em oportunidade.

---

# 7. Conteúdo informativo e mudança estratégica

Conteúdo informativo não é automaticamente irrelevante.

É necessário separar:

## Informação comum sem consequência

Notícia, anúncio ou artigo que apenas relata um fato, repete uma tendência ou descreve uma tecnologia, sem indicar nova capacidade ou impacto plausível em decisões futuras.

Normalmente recebe baixa prioridade.

## Mudança estratégica

Informação que evidencia transformação de mercado, regulação, comportamento, infraestrutura ou modelo de cuidado com potencial para alterar decisões futuras.

Pode ser relevante mesmo sem teste imediato.

Perguntas de verificação:

1. O fato muda alguma premissa importante?
2. Indica uma direção que outros atores podem seguir?
3. Cria, remove ou desloca uma barreira?
4. Pode alterar uma decisão futura da Namu?

Afinidade temática, menção a inovação ou interesse intelectual isolado não são suficientes.

---

# 8. Saúde e transferibilidade

Não exigir que o conteúdo original mencione health, healthcare, wellness, medical ou patient.

Uma capacidade criada para outro setor pode ser relevante quando sua transferência para saúde, bem-estar, prevenção, experiência ou operação for plausível.

Da mesma forma, conteúdo healthtech pode ser irrelevante quando for genérico, puramente informativo ou não demonstrar consequência concreta.

Perguntas de verificação:

1. Qual capacidade ou mudança existe além do tema “saúde”?
2. A aplicação para a Namu é plausível ou apenas uma associação por palavra-chave?
3. Se o vocabulário de saúde fosse removido, ainda existiria um sinal relevante?

## Contexto da Namu para transferibilidade e PoC

O radar cobre saúde, mas o pilar mais amplo é **bem-estar, hábitos, comportamento e cuidado**. O que se busca é a **métrica de relevância**, não uma lista de temas: um sinal interessa quando abre uma nova possibilidade plausivelmente transferível para produto, experiência ou operação da Namu, e de preferência **testável como uma PoC**.

O critério, em uma frase:

> Isso revela uma capacidade ou comportamento novo que a Namu poderia transformar em experiência, produto ou serviço de bem-estar — e conseguiríamos testar isso?

Um sinal não precisa nascer na saúde. Vale por transferibilidade, não por afinidade temática. Projetos open-source pesam mais quando dão pra virar um experimento concreto.

Para calibrar o tom — e **apenas como ilustração**, não como alvos a caçar — capacidades que já se conectaram a experimentos internos (por exemplo, visão computacional aplicada ao rosto e estimativa de sinais por câmera, na linha do VitalScan/rPPG; wearables e dados pessoais de sono e hábitos; capacidades locais e novas interfaces) mostram o *tipo* de transferência que interessa. São referências de sentido, não palavras-chave.

Consequências disso: um item que bate exatamente com um desses temas ainda pode ser irrelevante (genérico, sem nova capacidade), e um item totalmente fora deles pode ser relevante se abrir uma possibilidade transferível. A decisão final permanece humana.

---

# 9. Critérios principais

Os critérios ajudam a explicar o julgamento; não constituem um score nesta versão.

## Novidade

Existe algo diferente ou uma mudança relevante de contexto?

## Nova capacidade

Torna algo possível que antes era difícil, caro ou inviável?

## Potencial de produto

Pode gerar ou alterar uma experiência, produto ou serviço?

## Relevância Namu

Existe conexão plausível com saúde, bem-estar, prevenção, experiência, operação ou estratégia da empresa?

## Timing

Está cedo o suficiente para exploração, acompanhamento ou preparação?

## Testabilidade

Existe uma forma simples de experimentar e produzir aprendizado? Este critério amplifica, mas não determina, o interesse.

## Consequência estratégica

O sinal pode alterar decisões futuras mesmo sem aplicação ou teste imediato?

---

# 10. Tração

Tração não entra no núcleo da descoberta.

Stars, votos, comentários, adoção e crescimento podem ser evidências complementares de maturidade ou atenção.

Uma tração consolidada pode reduzir o valor como sinal emergente. Uma evidência pequena pode ser relevante quando demonstra uma capacidade incomum.

> **Popularidade é evidência, não descoberta.**

---

# 11. Exemplos positivos

Os exemplos abaixo foram generalizados a partir dos aprendizados do Gold Set v0.1.

### Exemplo 1 — Nova capacidade

Uma ferramenta transforma documentos complexos e pouco estruturados em dados utilizáveis por fluxos de produto, com custo e esforço menores do que abordagens anteriores.

**Por que entra:** nova capacidade + consequência comercial plausível + possibilidade de experimentação.

### Exemplo 2 — Nova aplicação ou combinação

Uma assistência inteligente deixa de apenas responder perguntas e passa a apoiar o manejo contínuo de condições de saúde.

**Por que entra:** nova aplicação de uma capacidade técnica + possível transformação da experiência de cuidado.

### Exemplo 3 — Novo comportamento ou necessidade

Empresas de saúde passam a tratar conhecimento clínico como parte indispensável do desenho e da expansão do produto, em vez de incorporá-lo somente após a escala.

**Por que entra:** mudança de comportamento organizacional + necessidade de produto e operação ainda mal atendida.

### Exemplo 4 — Tecnologia habilitadora e testável

Um pequeno componente self-hosted torna simples experimentar memória e contexto entre serviços, reduzindo uma barreira que antes exigia infraestrutura significativa.

**Por que entra:** tecnologia habilitadora + teste acessível + aprendizado potencial para novas experiências.

### Exemplo 5 — Mudança estratégica

Uma análise mostra uma mudança relevante em como organizações estruturam colaboração e decisões para inovar, com possíveis efeitos sobre futuros modelos de trabalho e produto.

**Por que entra:** transformação estratégica plausível; ausência de teste imediato não elimina o sinal.

---

# 12. Exemplos negativos

### Exemplo 1 — Popularidade sem consequência

“Novo framework técnico alcança milhares de stars.”

**Por que não entra:** popularidade e utilidade para desenvolvedores sem nova capacidade clara de produto.

### Exemplo 2 — Ferramenta técnica isolada

Um editor, monitor de servidor ou utilitário de comparação recebe uma nova implementação, mas sua consequência termina no próprio fluxo técnico.

**Por que não entra:** testabilidade e qualidade técnica, sozinhas, não demonstram oportunidade.

### Exemplo 3 — Saúde apenas como tema

Um artigo descreve de forma genérica que IA transformará hospitais, sem experimento, evidência nova ou consequência estratégica específica.

**Por que não entra:** relação explícita com saúde sem nova possibilidade.

### Exemplo 4 — Informação comum

Uma notícia relata aquisição, premiação, lançamento de hardware ou acontecimento geral sem mudança relevante para produto, cuidado, comportamento ou estratégia.

**Por que não entra:** conteúdo informativo sem consequência.

### Exemplo 5 — Agregação genérica

“Principais ferramentas de IA para usar neste mês.”

**Por que não entra:** catálogo genérico sem evidência concreta de nova capacidade.

---

# 13. Casos ambíguos

Quando houver dúvida, não descartar automaticamente. Marcar como `maybe` ou manter para revisão humana quando investigação adicional puder esclarecer o valor.

### Exemplo 1 — Tecnologia testável com consequência incerta

Uma ferramenta pode ser executada facilmente e parece habilitar algo novo, mas ainda não existe consequência plausível bem definida para produto ou aprendizado estratégico.

**Por que é ambíguo:** testabilidade amplifica interesse, mas não prova relevância.

### Exemplo 2 — Conteúdo informativo estrategicamente alinhado

Um artigo aborda um problema muito próximo à realidade da Namu, porém traz pouca evidência nova e nenhuma ação imediata.

**Por que é ambíguo:** afinidade estratégica pode justificar investigação, mas não é suficiente para `interesting` por si só.

### Exemplo 3 — Mudança regulatória inicial

Uma decisão regulatória autoriza uma nova forma de monitoramento contínuo por dispositivo de consumo, mas seu efeito no mercado e sua aplicação ainda são incertos.

**Por que é ambíguo:** pode representar mudança estratégica, embora exista apenas uma evidência inicial.

### Exemplo 4 — Capacidade futura sem acesso atual

Uma pesquisa ou tecnologia demonstra potencial relevante, mas ainda não existe forma prática de testar ou aplicar.

**Por que é ambíguo:** ausência de testabilidade não elimina o sinal; timing e consequência ainda precisam de investigação.

### Exemplo 5 — Saúde sem nova capacidade clara

Um conteúdo descreve uma iniciativa relevante de saúde, mas não permite distinguir entre notícia comum e transformação de modelo de cuidado.

**Por que é ambíguo:** o tema justifica atenção inicial, não uma conclusão automática.

---

# 14. Decisão humana

Os tipos, critérios e exemplos ajudam a reduzir inconsistência, mas não substituem contexto ou investigação.

- Um item pode combinar vários tipos de sinal.
- Um item pode ser testável e ainda ser irrelevante.
- Um item pode não ser testável e ainda ser interessante.
- Saúde, novidade técnica e popularidade não determinam relevância isoladamente.
- A revisão humana permanece a camada final de decisão.

---

# 15. Pergunta central

> **O que isso torna possível, muda ou revela que antes não era comum, e por que isso pode importar para produto, serviço, saúde, bem-estar, experiência, operação ou decisões futuras?**
