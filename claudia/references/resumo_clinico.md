# Resumo clínico e preparação para consulta

A Claudia organiza a história do paciente em dois formatos principais: **sumário para o paciente** (preparar a consulta) e **sumário técnico para o médico** (quando a tela ativadora é `tela_medico_view` ou o usuário logado é médico).

## Fontes no banco

Compor o sumário cruzando:
- `pacientes` (idade, sexo).
- `diario_saude` últimos 30–90 dias (sintomas, humor, sono, peso, PA).
- `consultas` últimas (o que foi relatado, CID, plano).
- `exames` + `resultados_estruturados` últimos 6–12 meses.
- `remedios` ativos + `remedios_tomadas` adesão últimos 30 dias.
- `receitas` recentes.

Use `db_helper.resumo_clinico(dias=90)` para pegar o essencial em um dicionário.

## Formato: sumário para paciente (pré-consulta)

Estrutura simples:

```
# Sua consulta com Dr(a). [nome] em [data]

## Como você está
- Peso hoje: X kg (variação últimos 30d: ...)
- Pressão: ...
- Humor/energia: ...
- Sono: ...

## O que mudou desde a última consulta
- [sintoma novo] em [data]
- [exame X] alterado em [data]
- [remédio Y] iniciado/suspenso

## Medicações em uso
- [remédio, dose, frequência, adesão X%]

## Suas 3 perguntas para o médico
1. ...
2. ...
3. ...

## O que levar
- Exames: [lista]
- Lista de remédios
- Este resumo
```

As "3 perguntas" você ajuda a formular com base nas dúvidas do usuário. Limitar a 3–5 perguntas; mais que isso, consulta não rende.

## Formato: sumário técnico (médico)

Seja conciso, use vocabulário técnico. Modelo:

```
Pac. [iniciais], [sexo], [idade]a.

## Antecedentes
HAS (I10) desde 20XX, em uso de losartana 50 mg MID.
DM2 (E11) desde 20XX, HbA1c 7.4% (última, 15/03/2026).
Dislipidemia, LDL 142 (20/03/2026), sob sinvastatina 20 mg.

## Queixa atual
Relato em diário (10–18/04): cansaço, dor lombar em piora, sono fragmentado (~5h).

## Exames recentes (últimos 6m)
Hb 13.1 → 12.4 (↓ dentro limite). HbA1c 7.4. LDL 142 (↑).
TSH 2.8 (normal). Cr 1.0 / TFG 78.

## Medicações
Losartana 50 mg MID — adesão 92% últimos 30d.
Metformina 850 mg BID — adesão 85%.
Sinvastatina 20 mg à noite — adesão 70% (queixa de dor muscular?).

## Avaliação (hipóteses)
- Dislipidemia parcialmente controlada (LDL alvo <100 em DM).
- Possível mialgia por estatina; considerar switch.
- Investigar causa de astenia: descartar hipotireoidismo subclínico, B12, anemia inicial.

## Plano sugerido para discussão
1. Hemograma + ferritina + B12 + TSH + CPK.
2. Avaliar troca sinvastatina → rosuvastatina / pitavastatina.
3. Reforçar adesão metformina.
4. Orientação exercício (ver rotina).
```

## Quando sinalizar "vermelho"

No sumário, destaque no topo se houver:
- Valor crítico em exame recente.
- Adesão < 50% em remédio essencial (anti-hipertensivo, anticoagulante, insulina, antirretroviral).
- Sintomas sugestivos de urgência (dor torácica, dispneia nova, sangramento, edema intenso, confusão).
- PA sistólica ≥ 180 ou < 90, glicemia > 300, FC < 40 ou > 120 em repouso.

Esses pontos vão **antes** de qualquer outra seção.

## O que evitar

- Fazer sumário **sem dados** — se o banco estiver vazio, peça consulta em branco ao invés de inventar.
- Dar "plano terapêutico" para paciente leigo como se fosse o médico.
- Ocultar efeito colateral relatado para "não preocupar" — ele precisa ir ao médico.
- Copiar o diário inteiro — resumir, o que importa.
