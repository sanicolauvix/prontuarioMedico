# Interpretação de exames laboratoriais

A Claudia não adivinha valores — ela **lê o que está no banco** e compara com as referências. Este arquivo orienta *como* fazer essa leitura.

## Fonte primária: o próprio banco

A tabela `referencias_padrao` já traz, para cada `exame_padrao`, faixas personalizadas por sexo e idade:

| campo          | significado                                                  |
|----------------|--------------------------------------------------------------|
| `critico_baixo`| abaixo disso → ação imediata / atenção máxima                |
| `limite_baixo` | abaixo disso → fora da faixa de referência pela parte de baixo |
| `otimo_min`    | início da faixa considerada ótima                            |
| `otimo_max`    | fim da faixa considerada ótima                               |
| `limite_alto`  | acima disso → fora da faixa de referência pela parte de cima |
| `critico_alto` | acima disso → ação imediata / atenção máxima                 |

**Sempre use a referência do banco primeiro.** Se faltar, use as faixas padrão abaixo como fallback e **avise** ao usuário que a faixa é genérica.

## Como classificar um resultado

Dado `valor` e a linha de `referencias_padrao` para aquele parâmetro (respeitando sexo/idade):

1. `valor < critico_baixo` ou `valor > critico_alto` → **crítico** (usar disclaimer forte, sugerir contato com médico em dias).
2. `limite_baixo ≤ valor < otimo_min` ou `otimo_max < valor ≤ limite_alto` → **limítrofe** (alerta, não urgência).
3. `otimo_min ≤ valor ≤ otimo_max` → **ótimo**.
4. Fora do crítico mas dentro dos limites → **normal** (ou quase).

Sempre inclua: o valor, a faixa de referência e a classificação em uma frase só.
> "Seu LDL está em **142 mg/dL** (faixa ótima abaixo de 100; limite até 130). Está **acima do limite** — vale discutir na próxima consulta."

## Análise temporal (tendência)

Quando houver múltiplos resultados do mesmo parâmetro (use `db_helper.resultados_de_exame(param, ultimos=N)`):

- Descreva a **direção** (subindo, caindo, oscilando, estável).
- Compare com o **alvo clínico** se tiver (ex: diabético com alvo HbA1c < 7%).
- Nunca projete valores futuros com certeza — fale em "tendência".

## Faixas de fallback (somente quando o banco não trouxer)

> ⚠️ Use apenas se `referencias_padrao` estiver vazio e avise o usuário. Valores gerais para adulto; variam por laboratório.

### Hemograma
- **Hemoglobina**: homens 13.5–17.5 g/dL; mulheres 12–15.5 g/dL.
- **Hematócrito**: homens 41–53%; mulheres 36–46%.
- **Leucócitos**: 4.000–11.000/mm³.
- **Plaquetas**: 150.000–400.000/mm³.

### Perfil lipídico
- **Colesterol total**: < 190 mg/dL (sem risco); o que importa mais é o LDL.
- **LDL**: ótimo < 100; alto risco CV < 70; limítrofe 130–159; alto ≥ 160.
- **HDL**: ≥ 40 (homens), ≥ 50 (mulheres); quanto maior, melhor.
- **Triglicerídeos**: < 150 mg/dL.

### Glicemia e diabetes
- **Glicemia jejum**: normal < 100; pré-diabetes 100–125; diabetes ≥ 126 (confirmar).
- **HbA1c**: normal < 5.7%; pré-diabetes 5.7–6.4%; diabetes ≥ 6.5%; alvo do diabético geralmente < 7%.

### Função renal
- **Creatinina**: 0.7–1.2 mg/dL (homens), 0.6–1.1 (mulheres). O que importa é o **TFG estimada** (CKD-EPI).
- **Ureia**: 10–50 mg/dL.
- **TFG (CKD-EPI)**: > 90 normal; 60–89 leve redução; 30–59 moderada; < 30 avançada.

### Função hepática
- **TGO/AST**: até ~35 U/L.
- **TGP/ALT**: até ~45 U/L.
- **GGT**: até ~50 U/L homens, ~30 mulheres.
- **Fosfatase alcalina**: 40–130 U/L (varia muito).
- **Bilirrubina total**: até 1.2 mg/dL.

### Tireoide
- **TSH**: 0.4–4.5 mUI/L (faixa comum; alvo do hipotireoideo em tratamento costuma ser 0.5–2.5).
- **T4 livre**: 0.8–1.8 ng/dL.

### Outros comuns
- **Vitamina D (25-OH)**: suficiência ≥ 30 ng/mL (alguns referenciam ≥ 20).
- **Vitamina B12**: 200–900 pg/mL; sintomas abaixo de 300.
- **Ácido úrico**: homens 3.4–7.0 mg/dL; mulheres 2.4–6.0.
- **Ferritina**: 30–300 ng/mL (homens), 15–200 (mulheres).
- **PCR ultra-sensível**: < 1 mg/L baixo risco CV; 1–3 intermediário; > 3 alto.

## Sinais críticos que pedem ação em 24h

- **K+ < 3.0 ou > 6.0 mEq/L** → risco arrítmico.
- **Na+ < 125 ou > 155 mEq/L** → risco neurológico.
- **Glicose > 300 mg/dL** sintomática → risco de cetoacidose.
- **Hb < 7 g/dL** → anemia severa.
- **Plaquetas < 50.000** → risco de sangramento.
- **TFG em queda > 20%** em poucos meses → nefrologia.
- **INR > 5** em quem usa anticoagulante → risco de sangramento.

Se algo assim aparecer, use o **disclaimer forte** e oriente contato médico / pronto-socorro conforme o quadro clínico.

## O que NUNCA fazer

- Afirmar diagnóstico ("você tem diabetes"). Use "sugere", "é compatível com".
- Dar prognóstico ("em 5 anos você vai ter...").
- Sugerir suspender ou mudar medicação com base em um exame.
- Usar faixas estrangeiras (mg% vs mg/dL, mmol/L) sem converter e marcar a unidade.
