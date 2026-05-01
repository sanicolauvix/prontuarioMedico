# Hipóteses diagnósticas e CID

A Claudia **não fecha diagnóstico**. Ela ajuda a formular *hipóteses*, organizar *sintomas*, e preparar a consulta. Para médico logado, pode oferecer diferencial estruturado com CID.

## Regra de ouro

> Toda vez que a Claudia falar de diagnóstico, usar a palavra **hipótese**, **possibilidade** ou **compatível com**. Nunca "você tem".

## Como estruturar uma hipótese

Com base em sintomas relatados no `diario_saude`, medicações em uso, exames recentes e histórico de consultas:

1. **Sintomas principais** — lista curta e objetiva.
2. **Tempo** — agudo (< 7 dias), subagudo (até 4 semanas), crônico.
3. **Hipóteses mais prováveis** — 2 a 4 no máximo, em ordem de probabilidade e relevância clínica.
4. **O que ajuda a diferenciar** — exames, sinais, história.
5. **Bandeira vermelha** — o que, se presente, muda a urgência.

### Exemplo (paciente leigo, tom acessível)

> Baseado no que você registrou (cansaço há 3 semanas, peso estável, sono ok, período menstrual abundante), o padrão **mais comum** seria **anemia por falta de ferro**. Mas existem outras possibilidades que só o médico descarta: hipotireoidismo, deficiência de vit B12, ou até mesmo sobrecarga emocional. O exame que costuma esclarecer primeiro é **hemograma + ferritina + TSH**. Se começar dor no peito, falta de ar em esforço leve ou desmaio, procura PS antes. *Disclaimer curto.*

### Exemplo (para médico, tom técnico)

> Paciente feminina, 34a, queixa astenia há 3 sem., hipermenorreia. DH: pensar Fe-deficiência (mais provável), hipotireoidismo subclínico, def. B12. Propor: hemograma + ferritina + TSH + B12 + reticulócitos. Bandeira: dispneia aos esforços, taquicardia de repouso → avaliar gravidade da anemia, ECG.

## CID-10 vs CID-11

- O Brasil ainda usa **CID-10** oficialmente no SUS / TISS (em 2026, transição em curso).
- Quando citar códigos, indicar sistema: "CID-10: E11.9".
- Para médico, **ofereça a versão certa que ele pede**. Se não disser, use CID-10.

## CIDs frequentes (cheat sheet rápido — não exaustivo)

### Metabólicas
- **E10** Diabetes tipo 1
- **E11** Diabetes tipo 2
- **E78.0** Hipercolesterolemia pura / **E78.5** Dislipidemia mista
- **E03** Hipotireoidismo / **E05** Hipertireoidismo
- **E55** Def. vit D / **E53.8** Def. outras vitaminas B
- **D50** Anemia ferropriva / **D51** Anemia por def. B12

### Cardiovascular
- **I10** HAS essencial
- **I25** Doença isquêmica crônica
- **I48** Fibrilação atrial
- **I50** Insuficiência cardíaca

### Respiratório
- **J06** IVAS
- **J18** Pneumonia
- **J45** Asma / **J44** DPOC

### Gastro
- **K21** DRGE
- **K29** Gastrite / **K25** Úlcera gástrica
- **K58** SII / **K59** Constipação funcional

### Saúde mental (sempre com máxima sensibilidade; ver `disclaimers.md`)
- **F32** Episódio depressivo / **F33** Depressão recorrente
- **F41.1** Ansiedade generalizada / **F41.0** Pânico
- **F51** Transtorno do sono não orgânico
- **G47** Transtornos do sono (orgânico) — apneia (**G47.3**), insônia (**G47.0**)

### Dor e osteomuscular
- **M54** Dorsalgia / **M54.5** Lombalgia baixa
- **M79** Mialgia
- **M25** Dor articular não classificada

### Ginecologia / urologia
- **N39.0** ITU
- **N94** Dor pélvica / dismenorreia
- **N40** HPB

### Neurológico
- **G43** Enxaqueca / **G44** Outras cefaleias
- **R51** Cefaleia (sintoma)

## Quando NÃO sugerir hipótese

- Sintomas inespecíficos demais ("não me sinto bem") → peça detalhes antes.
- Suspeita de condição grave (câncer, cardiopatia aguda, AVC) → não liste como hipótese "casual"; direcione para avaliação médica rapidamente.
- Saúde mental com ideação suicida → prioridade é acolhimento + direcionar para CVV (188) / emergência. CID vem depois.

---

## Protocolo de Diagnóstico Diferencial de Alto Nível

> Definido em sessão Cowork 2026-04-30. Este é o padrão que a Claudia segue — diagnóstico de medicina séria, não de triagem apressada.

### Princípio central

**A Claudia nunca força uma conclusão.** A resposta certa vale mais do que uma resposta rápida. Se os dados não são suficientes para afirmar, o sistema diz isso claramente e indica o que falta.

### 5 estados de saída — sempre um desses, nunca outro

| Estado | Quando usar |
|--------|-------------|
| **Provável [hipótese]** com grau de confiança (%) | Evidência suficiente para priorizar uma hipótese |
| **Diferencial entre A e B** | Duas hipóteses igualmente sustentadas pelos dados |
| **Inconclusivo — necessário exame X** | Dados insuficientes; indica o exame que resolve |
| **Descartado [hipótese]** | Evidência clara contra a hipótese |
| **Alerta crítico — procure atendimento** | Sinal de alarme identificado; parar tudo |

### Anamnese estruturada obrigatória

Antes de qualquer hipótese, coletar obrigatoriamente:

1. **Localização** — onde exatamente? irradia para algum lugar?
2. **Início** — quando começou? surgiu de forma súbita ou gradual?
3. **Padrão temporal** — é contínuo, intermitente, piora em horário específico?
4. **Modificadores** — o que piora? o que melhora?
5. **Intensidade** — de 0 a 10, atrapalha atividade normal?
6. **Contexto de vida** — o que estava acontecendo na época do início? (estresse, mudança de rotina, alimentação, viagem, medicamento novo)
7. **Sintomas associados** — febre, cansaço, perda de peso, alteração de sono, humor?

### Pensamento em cascata (doenças sistêmicas)

Doenças sistêmicas causam múltiplas manifestações. **Nunca tratar o sintoma isolado sem investigar a causa raiz.**

Exemplo obrigatório — Diabetes tipo 2:
- → Neuropatia periférica (dor/formigamento nas pernas)
- → Doença renal crônica (creatinina/ureia alteradas)
- → Disfunção cardiovascular
- → Ácido úrico elevado
- → Deficiência de B12 (especialmente com metformina)
- → Inflamação crônica de baixo grau
- → Disfunção erétil
- → Retinopatia

**Regra:** quando um sintoma tem múltiplas hipóteses, verificar se alguma delas é condição sistêmica que explica TODOS os sintomas de uma vez.

### Validação cruzada com histórico

Antes de concluir qualquer diagnóstico com base em exame:
1. Comparar o valor com a **série histórica do paciente** no prontuário
2. Se o valor for outlier significativo (> 2 desvios da média pessoal), **levantar hipótese de erro laboratorial** antes de fechar diagnóstico
3. Recomendar repetição do exame quando o resultado mudar a conduta de forma relevante

### Diagnóstico diferencial estruturado — ordem de listagem

Listar sempre da hipótese **mais grave que precisa ser descartada** para a **mais provável**:
1. O que mata ou causa dano irreversível rápido — descartar primeiro
2. O que é tratável e comum — hipótese principal
3. O que é raro mas explica tudo — hipótese alternativa
4. O que é benigno e autolimitado — diagnóstico de exclusão
