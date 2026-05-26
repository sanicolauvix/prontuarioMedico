# Padrão de Processamento de Documentos — Prontuário Koios

## Regra geral de pasta para anexos
```
prontuario/
  exames/
    organizados/           ← páginas individuais já separadas por data
      YYYY-MM-DD/
        YYYY-MM-DD_origem_pNN_titulo.pdf
    internacao_{id}/       ← anexos vinculados a uma internação específica
      resultado_lab/
      ecg/
      prescricao/
      evolucao/
      imagem/              ← rx, eco, usg, mapa
```

---

## GRUPO A — Tabela `exames` + `exame_resultados` + `exame_anexos`

### A1. Resultado laboratorial (`resultado_lab`)
**Tabela principal:** `exames`
- `tipo` = 'laboratorial'
- `tipo_exame` = nome do painel (ex: 'Hemograma Completo', 'Bioquímica UTI')
- `data_exame` = data da coleta
- `laboratorio` = nome do laboratório
- `medico_solicit` = médico solicitante
- `internacao_id` = FK para internação relacionada
- `status` = 'resultado' (tem valor) | 'solicitado' (só pedido)
- `resultado_texto` = laudo completo em texto

**Tabela filha:** `exame_resultados`
- Um row por parâmetro: parametro, valor, unidade, referencia
- `nivel_interpretacao` = 'normal' | 'alterado_leve' | 'alterado_grave' | 'critico'

**Tabela anexo:** `exame_anexos`
- `arquivo_local` = caminho relativo ao PDF da página
- `drive_file_id` = após sync com Drive

**PDF anexo:** `exames/internacao_{id}/resultado_lab/YYYY-MM-DD_nome.pdf`

---

### A2. ECG (`ecg`)
**Tabela principal:** `exames`
- `tipo` = 'ecg'
- `tipo_exame` = 'ECG 12 derivações'
- `resultado_texto` = laudo automático do aparelho

**Tabela filha:** `exame_resultados`
- Parâmetros: FC, PR, QRS, QT, QTc, Eixo, Ritmo, Alterações

**Tabela filha:** `laudos`
- `texto_completo` = laudo completo
- `conclusao` = interpretação resumida

**PDF anexo:** `exames/internacao_{id}/ecg/YYYY-MM-DD_HHmm_ecg.pdf`

---

### A3. Resultado de imagem (`resultado_imagem`, `resultado_exame`)
USG, Doppler, Ecocardiograma, RX, MAPA

**Tabela principal:** `exames`
- `tipo` = 'imagem' | 'funcional'
- `tipo_exame` = nome específico (ex: 'USG Próstata', 'Ecocardiograma Stress', 'MAPA 24h')

**Tabela filha:** `laudos`
- `texto_completo` = laudo completo do médico
- `conclusao` = conclusão/impressão diagnóstica

**Tabela filha:** `exame_resultados` (para parâmetros numéricos)
- Ex MAPA: PA_media_vigilia, PA_media_sono, carga_sistolica, etc.
- Ex Eco: FEVE, dimensões, conclusão isquemia sim/não

**PDF anexo:** `exames/internacao_{id}/imagem/YYYY-MM-DD_nome.pdf`

---

## GRUPO B — Dados da internação

### B1. Prescrição médica (`prescricao_medica`)
**Tabela:** `remedios` com `internacao_id`
- Um row por medicamento prescrito
- `nome`, `dosagem`, `frequencia`, `tipo` = 'prescrito_internacao'
- `data_inicio` = data da prescrição
- `internacao_id` = FK
- `prescrito` = 1

**PDF anexo:** `exames/internacao_{id}/prescricao/YYYY-MM-DD_pNN_prescricao.pdf`

---

### B2. Sinais vitais / Balanço hídrico (`sinais_vitais`, `balanco_hidrico`)
**Tabela:** `sinais_internacao`
- Um row por medição horária: sinal, momento (hora), valor, unidade
- `momento` = formato 'YYYY-MM-DD HH:MM' ou 'turno_manha' etc.
- `fonte` = 'folha_sinais_vitais'

**PDF anexo:** `exames/internacao_{id}/evolucao/YYYY-MM-DD_sinais.pdf`

---

### B3. Evolução médica / Enfermagem (`evolucao_medica`, `evolucao_enfermagem`)
**Tabela:** `internacao_dados_brutos`
- `categoria` = 'evolucao_medica' | 'evolucao_enfermagem'
- `conteudo` = texto estruturado da evolução
- `pagina_origem` = número da página no PDF original

**PDF anexo:** `exames/internacao_{id}/evolucao/YYYY-MM-DD_evolucao.pdf`

---

### B4. Procedimento cirúrgico (`registro_cirurgia`, `relatorio_cirurgico`)
**Tabela:** `procedimentos`
- `nome`, `tipo`, `data`, `cid`, `resultado`, `observacoes`
- `internacao_id` = FK

**PDF anexo:** `exames/internacao_{id}/evolucao/YYYY-MM-DD_cirurgia.pdf`

---

### B5. Ficha de transporte (`ficha_transporte`)
**Tabela:** `sinais_internacao`
- Sinais vitais antes/depois da transferência
- `momento` = 'transferencia_saida_{setor}' | 'transferencia_chegada_{setor}'

**Tabela:** `internacao_dados_brutos`
- `categoria` = 'transporte_ps_uti' | 'transporte_intra'

**PDF anexo:** `exames/internacao_{id}/evolucao/YYYY-MM-DD_transporte.pdf`

---

### B6. Alta hospitalar (`alta`)
**Tabela:** `internacoes`
- Atualizar: `data_saida`, `diagnostico_saida`, `cid_saida`, `observacoes`

**Tabela:** `internacao_dados_brutos`
- `categoria` = 'alta'
- `conteudo` = orientações de alta + medicações de saída

**PDF anexo:** `exames/internacao_{id}/evolucao/YYYY-MM-DD_alta.pdf`

---

### B7. Ficha de admissão (`ficha_admissao`)
**Tabela:** `internacoes`
- Complementar: `motivo`, `cid_entrada`, `cidade`, `uf`

**Tabela:** `internacao_dados_brutos`
- `categoria` = 'admissao'
- `conteudo` = queixa principal + histórico + dados de entrada

**PDF anexo:** `exames/internacao_{id}/admissao/YYYY-MM-DD_admissao.pdf`

---

## GRUPO C — Descarte (não processa)
- `administrativo` (CNH, carteirinha, orientações visita)
- `termo` (consentimentos, responsabilidade)
- `checklist_cirurgico`, `checagem_pre_operatoria`
- `rastreabilidade_material_esteril`
- `solicitacao_internacao` (apenas guia burocrática)
- `controle_materiais`

---

## Mapeamento tipo → grupo

| tipo_documento            | grupo | tabela_principal          | subfasta_anexo  |
|---------------------------|-------|---------------------------|-----------------|
| resultado_lab             | A1    | exames + resultados_estru | resultado_lab/  |
| ecg                       | A2    | exames + laudos           | ecg/            |
| resultado_exame           | A3    | exames + laudos           | imagem/         |
| resultado_imagem          | A3    | exames + laudos           | imagem/         |
| mapa                      | A3    | exames + resultados_estru | imagem/         |
| prescricao_medica         | B1    | remedios                  | prescricao/     |
| sinais_vitais             | B2    | sinais_internacao         | evolucao/       |
| balanco_hidrico           | B2    | sinais_internacao         | evolucao/       |
| evolucao_medica           | B3    | internacao_dados_brutos   | evolucao/       |
| evolucao_enfermagem       | B3    | internacao_dados_brutos   | evolucao/       |
| prescricao_enfermagem     | B3    | internacao_dados_brutos   | evolucao/       |
| registro_cirurgia         | B4    | procedimentos             | evolucao/       |
| ficha_transporte          | B5    | sinais_internacao         | evolucao/       |
| alta                      | B6    | internacoes               | evolucao/       |
| ficha_admissao            | B7    | internacoes               | admissao/       |
| avaliacao_riscos          | B3    | internacao_dados_brutos   | evolucao/       |
| administrativo            | C     | —                         | —               |
| termo                     | C     | —                         | —               |
| checklist_cirurgico       | C     | —                         | —               |
| checagem_pre_operatoria   | C     | —                         | —               |
| rastreabilidade_material  | C     | —                         | —               |
| solicitacao_internacao    | C     | —                         | —               |
| controle_materiais        | C     | —                         | —               |
| cnh                       | C     | —                         | —               |
| solicitacao_exame         | C     | —                         | —               |
