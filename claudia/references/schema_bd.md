# Schema do banco prontuario.db

Banco SQLite em `dados/prontuario.db`. Tabelas relevantes para a Claudia, agrupadas por domínio.

## Identidade

**pacientes** — `id, nome, cpf, data_nasc, sexo, criado_em`
**medicos** — `id, nome, crm, uf, especialidade_id, telefone, email, endereco, site, redes_sociais, foto_drive_id, observacoes, ativo, especialidade, medico_solicit`
**especialidades** — `id, nome, descricao, ativo`

## Exames e laudos

**exames** — `id, paciente_id, medico_id, tipo, tipo_exame, data_exame, laboratorio, medico_solicit, resultado_texto, arquivo_origem, drive_file_id, importado_em, status`
**exame_anexos** — `id, exame_id, drive_file_id, nome_arquivo, ordem`
**exames_padrao** — `id, nome_oficial, sinonimos, categoria, tipo, unidade, observacoes, ativo`
**referencias_padrao** — `id, exame_padrao_id, sexo, idade_min, idade_max, critico_baixo, limite_baixo, otimo_min, otimo_max, limite_alto, critico_alto, observacoes` — faixa de referência por sexo/idade.
**exame_resultados** — `id, exame_id, pai_id, parametro, valor, unidade, referencia, exame_padrao_id, nivel_interpretacao` — aqui moram os valores extraídos (ex: "Hemoglobina = 13.2 g/dL").
**laudos** — `id, exame_id, texto_completo, resumo, conclusao`
**laboratorios (lab_extratores)** — `id, laboratorio, versao, tipo, prompt_extracao, ...` — metadados do pipeline de extração, NÃO escrever.

## Consultas

**consultas** — `id, medico_id, paciente_id, data, hora, tipo ('agendada'|'realizada'|'cancelada'), local, observacoes`
**receitas** — `id, consulta_id, medico_id, drive_file_id, nome_arquivo, data, observacoes`

## Medicação

**remedios** — `id, nome, dosagem, frequencia, data_inicio, data_fim, medico_id, receita_id, estoque_atual, estoque_minimo, foto_path, ativo, observacoes`
**remedios_horarios** — `id, remedio_id, hora (HH:MM)` — horários da dose.
**remedios_tomadas** — `id, remedio_id, horario_id, data, hora, status ('pendente'|'tomado'|'pulado'|'atrasado')` — log de adesão.
**remedios_compras** — `id, remedio_id, farmacia_id, data_compra, quantidade, preco_unitario, preco_total, foto_cupom, observacoes`
**remedios_orcamentos** + **orcamento_itens** — orçamentos com farmácias.
**remedio_fotos** — fotos das caixas/comprimidos.
**farmacias** — `id, nome, endereco, telefone, whatsapp, site, app, delivery, preferida, ativo`

## Rotina e diário

**rotina_itens** — `id, tipo ('refeicao'|'medicamento'|'suplemento'|'atividade'|'outro'), nome, horario, dias_semana, descricao, quantidade, ativo`
**diario_saude** — `id, data, hora, humor (1-5), energia (1-5), sono_horas, peso, pressao, relato, tags, remedio_tomado`

## Sistema (não mexer)

**importacoes_log, pdfs_incompativeis, compartilhamentos, links_medico** — auditoria e integração.

## Dicas de query

- Para pegar valores de um parâmetro específico ao longo do tempo:
  ```sql
  SELECT e.data_exame, r.valor, r.unidade, r.nivel_interpretacao
  FROM exame_resultados r
  JOIN exames e ON e.id = r.exame_id
  JOIN exames_padrao ep ON ep.id = r.exame_padrao_id
  WHERE e.paciente_id = ? AND ep.nome_oficial = ?
  ORDER BY e.data_exame DESC
  ```
- Para ver adesão ao remédio na última semana:
  ```sql
  SELECT data, hora, status FROM remedios_tomadas
  WHERE remedio_id = ? AND data >= date('now','-7 day')
  ORDER BY data DESC, hora DESC
  ```
- Para último relato do diário:
  ```sql
  SELECT data, hora, humor, energia, sono_horas, relato, tags FROM diario_saude
  WHERE date(data) >= date('now','-30 day')
  ORDER BY data DESC, hora DESC
  ```

Para operações mais complexas, prefira os métodos prontos em `scripts/db_helper.py`.
