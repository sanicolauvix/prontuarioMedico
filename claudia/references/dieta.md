# Dieta e orientação alimentar

A Claudia **não substitui nutricionista**, mas pode orientar padrões alimentares gerais e ajustar sugestões ao contexto clínico do paciente (diabetes, dislipidemia, hipertensão, obesidade, gastrite, etc.).

## Princípios que guiam qualquer orientação

1. **Base científica + bom senso + cultura alimentar do paciente.** Dieta do Mediterrâneo e DASH são os padrões mais bem estudados; quando aplicáveis, preferir.
2. **Não prescrever dieta com macros específicos sem saber peso, altura, rotina, preferência e condição clínica.** Peça esses dados ou consulte no banco.
3. **Comida de verdade, minimamente processada.** Usar o **Guia Alimentar para a População Brasileira** como norte (evitar ultraprocessados, privilegiar in natura, refeição como ritual).
4. **Sustentável > radical.** Dietas que excluem grupos inteiros raramente se sustentam; foco em ajustes progressivos.
5. **Respeitar restrições**: vegetarianismo, religião, alergias (glúten, lactose, amendoim, frutos do mar).

## Pistas do banco que ajudam a personalizar

- `pacientes.data_nasc, sexo` → idade e sexo.
- `diario_saude.peso` ao longo do tempo → tendência.
- `exames` recentes (glicemia, perfil lipídico, TFG, TSH, ferritina, B12) → se alterado, dieta específica.
- `remedios` → alguns remédios pedem cuidado alimentar (varfarina × vit K; IMAO × tiramina; metformina × jejum prolongado; diuréticos × potássio).
- `rotina_itens` tipo `refeicao` → o que já está combinado.

## Cenários comuns

### Diabetes tipo 2 / pré-diabetes
- Prioridade: **controle da glicemia pós-prandial e peso**.
- Base: carboidratos complexos integrais, fibras (>25 g/d), proteína em toda refeição, gordura boa (azeite, castanhas, abacate).
- Limitar: açúcar livre, farinha branca, refrigerante, suco concentrado, ultraprocessados.
- Estratégia prática: **método do prato** — 1/2 vegetais não amiláceos, 1/4 proteína, 1/4 carboidrato complexo; fruta inteira, não em suco.
- Frequência: 3 refeições principais + 1–2 lanches, sem necessidade de fracionar em 6 refeições.

### Dislipidemia (LDL alto / triglicerídeos altos)
- **LDL alto**: reduzir gordura saturada (carnes gordas, manteiga, queijos amarelos), evitar gordura trans, aumentar fibras solúveis (aveia, feijão, chia), peixes gordos 2×/sem.
- **Triglicerídeos altos**: reduzir **álcool e açúcares refinados**, diminuir carboidratos simples, considerar ômega-3 (se prescrito).

### Hipertensão
- Padrão **DASH**: rico em frutas, vegetais, laticínios magros, grãos integrais; limitar sódio a < 2 g/dia (equiv. 5 g sal).
- Atenção a ultraprocessados escondidos: embutidos, temperos prontos, pão de forma, queijo industrial.
- Potássio: bananas, feijões, batata-doce, folhas verdes — **mas cuidado se o paciente tem doença renal ou usa IECA/BRA/espironolactona**.

### Doença renal crônica (TFG < 60)
- Cuidado com **potássio, fósforo, proteína e sódio**. Isso é terreno de nutricionista/nefro; a Claudia orienta conceitos gerais e encaminha.

### Anemia ferropriva
- Fontes de ferro heme (carne vermelha magra, fígado, frango, peixe) > ferro não-heme (feijão, lentilha, folhas escuras).
- **Vitamina C junto** melhora absorção do ferro não-heme (laranja, limão, kiwi).
- **Café/chá/leite longe das refeições** ricas em ferro (1h antes ou depois).

### Gastrite / DRGE
- Evitar: álcool, cafeína em excesso, frituras, chocolate, hortelã, tomate ácido, menta, refeições volumosas antes de deitar.
- Última refeição 2–3h antes de dormir; elevar a cabeceira se refluxo noturno.

### Obesidade
- **Déficit calórico sustentável** (300–500 kcal/d), não radical.
- Foco em densidade de saciedade: proteína + fibra + água.
- Movimento associado (ver `rotina_exercicios.md`).
- Paciência: 0,5–1% do peso/semana é ritmo saudável.

## Formato de resposta

- Se a pergunta é ampla ("o que devo comer?"), responda com padrão (ex: mediterrâneo) + 1 exemplo de almoço + 1 de jantar + 1 de lanche.
- Se é pontual ("posso comer banana à noite?"), responda direto, em 1–3 frases.
- Sempre termine perguntando se quer **registrar uma rotina alimentar no app** (grava em `rotina_itens` tipo `refeicao`).

## Anti-padrões

- Dieta da moda (cetogênica estrita, carnívora, low-carb radical) sem indicação clínica e acompanhamento.
- Suplemento "queimador de gordura" ou termogênico sem avaliação.
- Jejum intermitente para pessoa com DM1, grávida, histórico de TCA, criança, idoso frágil.
- Recomendação de "detox" — fígado e rim fazem isso sozinhos.
