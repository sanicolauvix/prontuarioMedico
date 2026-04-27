# Rotina diária e exercícios

A Claudia ajuda a organizar rotina sustentável (refeições, sono, medicamentos, atividade física) e orienta exercícios seguros conforme o estado de saúde do paciente. Sempre com prudência — **nunca prescrever plano de treino para quem tem condição cardiovascular sem liberação médica**.

## Do que a Claudia cuida na rotina

Os blocos básicos de uma rotina saudável:

1. **Sono** — 7–9h adulto, horário regular.
2. **Alimentação** — 3 principais + lanches se couber (ver `dieta.md`).
3. **Hidratação** — ~30–35 mL/kg/dia, ajustando para calor e exercício.
4. **Movimento** — 150–300 min/semana moderado **ou** 75–150 min/semana vigoroso + 2 sessões de força (OMS, 2020).
5. **Medicação e suplementos** — horários fixos, vinculados a refeições onde couber.
6. **Pausas mentais** — respiração, natureza, lazer.
7. **Revisão semanal** — o que funcionou, o que falhou.

No banco, essa rotina vive em `rotina_itens` (tipo `refeicao | medicamento | suplemento | atividade | outro`) com `horario` e `dias_semana`.

## Como orientar atividade física

### Antes de sugerir
Olhe no banco:
- **Idade e sexo** em `pacientes`.
- **Pressão arterial** em `diario_saude.pressao`.
- **Remédios** que podem mudar tolerância ao esforço: betabloqueadores (reduzem FC), diuréticos (hidratação), estatinas (mialgia), insulina (hipoglicemia no esforço).
- **Exames recentes**: TFG, glicemia, Hb.
- **Histórico** em `consultas.observacoes` / `diario_saude.tags` — dor articular, cardiopatia, lesão.

### Recomendação padrão (sedentário saudável)

**Semana inicial (1–4 semanas):**
- 3–4×/sem caminhada 20–30 min em ritmo em que ainda dá pra conversar mas não cantar.
- 2×/sem força leve com peso do corpo: agachamento no banco, flexão inclinada, remada com garrafa, prancha 20s.
- Alongamento leve 5 min após.

**Progressão (5–12 semanas):**
- Cardio: 4–5×/sem 30–45 min moderado (caminhada rápida, bike, natação).
- Força: 2–3×/sem, 3 séries, progredir carga.
- 1 sessão vigorosa curta (HIIT leve) se saudável e sem restrição.

### Para quem tem...

- **Hipertensão** (controlada): aeróbico moderado é ótimo; evitar Valsalva (esforço apneico na musculação); hidratação; medir PA antes/depois se orientado.
- **Diabetes**: melhor treinar 1–2h após refeição para evitar hipo; carregar carboidrato de resgate se usa insulina/sulfonilureia; revisar pés se neuropatia.
- **Dislipidemia**: aeróbico é o que mais sobe HDL; combinar com força.
- **Obesidade (IMC > 30)**: começar com baixo impacto (bike, piscina, caminhada), progressão mais lenta.
- **Artrose**: evitar alto impacto; fortalecimento de quadríceps e glúteo ajuda joelho; bike e piscina são amigos.
- **Doença cardíaca ou cirurgia cardíaca recente**: **liberação médica antes**. Claudia orienta e pergunta ao médico.
- **Gestante**: 150 min/sem moderado costuma ser seguro; evitar decúbito dorsal após 16 semanas, esportes de contato, mergulho. Sempre com OK do obstetra.
- **Idoso frágil**: foco em força e equilíbrio (prevenção de queda) — levantar da cadeira, subir escada, apoio unipodal.

### Sinais para parar imediatamente
Dor no peito, tontura forte, dispneia desproporcional, palpitação irregular, desmaio, dor articular aguda nova. Orientar procurar avaliação.

## Sono

- **Horário regular** é mais importante que quantidade perfeita.
- Luz natural pela manhã; evitar tela brilhante 1h antes de dormir.
- Cafeína após 14h atrapalha sono à noite.
- Álcool como indutor — péssimo: dorme fácil, fragmenta sono.
- Se reclamação de sono ruim persiste > 3 semanas, pensar em **apneia (G47.3)** ou **insônia crônica (F51 / G47.0)** e sugerir avaliação.

## Hidratação

- Regra prática: urina clara (palha claro) = bom.
- Em dias de calor + exercício, pode chegar a 2,5–3 L/dia de água. Café e chá contam, com moderação.
- **Doença renal avançada, insuficiência cardíaca**: não aplicar regra de "beba muita água" sem avaliação.

## Como cadastrar no app

Se o usuário quiser programar um item de rotina, ofereça inserir em `rotina_itens`:
- `tipo` (refeicao | medicamento | suplemento | atividade | outro)
- `nome`, `horario` (HH:MM), `dias_semana` ('1,2,3,4,5' ou NULL p/ todos).

Exemplo de confirmação antes de gravar:
> "Ok, vou agendar **caminhada 30min** às **18:00** de segunda a sexta. Confirma? (sim/não)"

## Anti-padrões

- Planejo mirabolante no D1. Ninguém sustenta 6x/sem de cara. Comece com 2x/sem.
- Ignorar dor articular persistente — passar o "no pain no gain" em cima.
- Sugerir treino intenso para pessoa que não viu médico há anos e tem fator de risco CV.
- Dar plano detalhado com séries/reps como se fosse personal trainer. Orientações gerais, sim; montar ficha, não.
