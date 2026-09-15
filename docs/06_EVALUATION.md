# Avaliação e Calibração do Radar

## Objetivo

Medir se o radar reduz ruído sem perder sinais interessantes.

A primeira validação deve comparar a seleção do sistema com julgamento humano.

---

# 1. Gold Set

Criar uma amostra de 50 a 100 itens reais coletados pelo radar.

Classificação humana:
- `interesting`
- `maybe`
- `irrelevant`

Cada item deve incluir uma justificativa curta.

Arquivo:

```text
tests/fixtures/signal_gold_set.json
```

O gold set não é um dataset definitivo. Ele deve evoluir conforme o radar encontra novos tipos de sinal.

---

# 2. O que medir

## Falsos positivos
Itens que o sistema recomenda, mas o analista considera irrelevantes.

Pergunta:

> Quantas coisas inúteis ainda estão consumindo tempo humano?

## Falsos negativos
Itens que o sistema arquiva, mas o analista consideraria interessantes.

Pergunta:

> O radar está eliminando justamente os sinais pequenos e incomuns que deveria encontrar?

## Divergência `maybe`
Casos em que a oportunidade depende de contexto ou investigação adicional.

---

# 3. Prioridade inicial

Evitar otimizar apenas uma “acurácia” geral.

O radar deve dar atenção especial a:
1. não perder sinais de alta novidade;
2. não deixar developer tooling dominar a saída;
3. manter diversidade de tipos de oportunidade;
4. explicar por que um sinal foi recomendado.

---

# 4. Registro de feedback

Toda revisão humana pode registrar:

```json
{
  "system_decision": "investigate",
  "human_decision": "irrelevant",
  "reason": "Developer tooling without product impact."
}
```

Esses casos devem ser usados para:
- ajustar prompts;
- melhorar filtros;
- ampliar exemplos positivos e negativos;
- identificar lacunas na política de sinais.

---

# 5. Avaliação do relatório

Perguntas:
- Os sinais são compreensíveis?
- Existe evidência suficiente?
- O texto explica o que é novo?
- A conexão com Namu é plausível ou forçada?
- Há diversidade de fontes?
- O relatório trouxe algo que a equipe provavelmente não encontraria sozinha?

---

# 6. Métrica principal do MVP

> **O radar encontrou algo relevante que a equipe provavelmente não encontraria manualmente?**

Essa resposta deve ser registrada por ciclo.

---

# 7. Critério para avançar de fase

Não adicionar complexidade automaticamente.

Antes de avançar:
- M1 → M2: confirmar que as fontes geram matéria-prima útil;
- M2 → M3: confirmar que os filtros não eliminam bons exemplos;
- M3 → M4: ter gold set suficiente para comparação;
- M4 → M5: classificador apresentar qualidade razoável;
- M5 → M6: agrupamento realmente melhorar a leitura;
- M6 → M7: watchlist trazer valor temporal.

---

# 8. Falhas que devem ser observadas

- excesso de notícias comerciais;
- excesso de ferramentas para dev;
- relação com Namu inventada;
- preferência excessiva por conteúdo popular;
- repetição do mesmo tema;
- perda de projetos pequenos;
- classificação de tecnologia consolidada como emergente;
- dependência excessiva de uma única fonte.

---

# 9. Avaliação humana é parte do produto

A revisão humana não é uma etapa temporária a ser removida.

O radar existe para reduzir o universo de busca e aumentar a qualidade da análise.

A decisão sobre relevância e oportunidade continua sendo contextual.
