@../flet_shared/CLAUDE.md

---

# PRONTUARIO MEDICO -- Configuracao especifica

## Stack

- Package: `com.flet.prontuario`
- Build script: `build_prontuario.ps1` (na raiz do projeto)

## Telas ativas

- `telas_shared/tela_login.py`      -- OAuth Google (deep link + servidor local 8080)
- `app.py`                          -- Hub principal (navegacao central, 35 KB)
- `telas/tela_medicos.py`           -- Cadastro de medicos
- `telas/tela_consultas_medicas.py` -- Historico de consultas
- `telas/tela_exames.py`            -- Exames manuais
- `telas/tela_exames_padrao.py`     -- Templates de exames
- `telas/tela_exames_processados.py`-- Exames extraidos de PDF
- `telas/tela_incluir_exame.py`     -- Formulario de inclusao de exame
- `telas/tela_incluir_exame_padrao.py` -- Inclusao via template
- `telas/tela_laboratorios.py`      -- Cadastro de laboratorios
- `telas/tela_especialidades.py`    -- Especialidades medicas
- `telas/tela_remedios.py`          -- Controle de remedios
- `telas/tela_dieta.py`             -- Dieta e nutricao
- `telas/tela_rotinas.py`           -- Templates de rotina (3 niveis: template -> momentos -> itens)
- `telas/tela_rotina_diaria.py`     -- Log diario de excecoes/observacoes na rotina
- `telas/tela_parecer.py`           -- Parecer medico (IA)
- `telas/tela_pendencias.py`        -- Pendencias e lembretes
- `telas/tela_perfil.py`            -- Perfil do usuario
- `telas/tela_links_medico.py`      -- Links e contatos medicos
- `telas/tela_medico_view.py`       -- Visao do medico
- `telas_sistema/tela_config.py`    -- Configuracoes
- `telas_sistema/tela_backup.py`    -- Backup (log dedicado)

## Estrutura

```
prontuario/
  main.py                   -- entry point standalone (flet build apk)
  app.py                    -- hub/navegacao central
  pyproject.toml            -- config do flet build
  requirements_apk.txt      -- deps para o APK
  requirements.txt          -- deps para desktop (gerenciado automaticamente)
  .fletignore               -- exclui arquivos do app.zip
  build_prontuario.ps1      -- script de build

  telas/                    -- telas especificas do prontuario
  telas_shared/             -- telas compartilhadas (login, endereco)
  telas_sistema/            -- telas de sistema (config, backup)
  shared/                   -- auth.py, layout.py, widgets.py
  utils/                    -- drive_sync.py, foto_picker.py, etc.
  backup/                   -- backup_watcher.py, drive_backup.py
  extratores/               -- extrator_pdf.py, processador_exame.py
  dados/                    -- model_prontuario.py, prontuario.db
  assets/                   -- icon.png
  claudia/                  -- references e SKILL.md da Claudia
  logs/                     -- logs de build e erros
  temp/                     -- temporarios (excluido do APK)
```

## Database

- Arquivo: `dados/model_prontuario.py`
- DB: `dados/prontuario.db` — banco unico, fonte de verdade
- Drive: `Koios/Prontuario/prontuario_db/` — apenas `prontuario.db` (koios.db removido)
- Tabelas principais: `usuarios`, `medicos`, `consultas`, `exames`, `remedios`, etc.
- Migracoes via ALTER TABLE IF NOT EXISTS (padrao do projeto)
- `_ProntuarioConn`: subclasse sqlite3.Connection — todo commit() dispara notify_db_changed()

## Extracao de PDF

- `extratores/extrator_pdf.py` -- extracao de texto de PDFs de exames
- `extratores/processador_exame.py` -- processa texto e chama IA (Anthropic)
- Requer `pdfplumber` no APK (--source-packages no flet build)

## IA -- Claudia

- Modelo: `claude-sonnet-4-6` (atualizar para 4.7+ quando disponivel)
- Contexto em `claudia/references/` (markdown por dominio)
- SKILL.md em `claudia/SKILL.md`

## Auth Google

- Desktop: `client_secrets.json` na raiz
- Android: `client_secrets_android.json` na raiz
- Credenciais salvas em `dados/prontuario.db` (tabela config)

## Build

```powershell
.\build_prontuario.ps1         # menu interativo
.\build_prontuario.ps1 -modo 1 # completo (~20 min)
.\build_prontuario.ps1 -modo 2 # so .py (~5 min)
.\build_prontuario.ps1 -modo 3 # assets/pubspec (~12 min)
.\build_prontuario.ps1 -modo 4 # so instalar (<1 min)
```

## Git

```powershell
git add -A && git commit -m "feat: ..." && git push
```

## Padrao de espacamento web (definido 2026-06-06)

Todas as telas abertas no web (via `_navegar_sub` ou `_navegar`) devem usar:

```python
# Padding da area de conteudo principal
padding=ft.padding.only(left=20, right=20, top=12, bottom=12)
```

Aplicar no container que envolve a `area` (Column de scroll) antes do `lay.criar_corpo()`.
Nao aplicar no cabecalho nem na nav bar — apenas na area de conteudo.

## Diferenca vs Prestanista

- **COM**: extracao de PDF, IA (Claudia), remedios, dieta, parecer medico
- **SEM**: financeiro, vendas, parcelas, fornecedores, catalogo, compras
- Sync: Drive = banco mestre, padrao completo implementado (ver `planos/Padroes/sincronizacao_backup.md`)
  - `main.py`: verifica Drive → apaga local → restaura → `criar_tabelas()` → `BackupWatcher.iniciar()`
  - `dados/model_prontuario.py`: `_ProntuarioConn` — todo `commit()` chama `notify_db_changed()` automaticamente
  - Offline + banco local: usa local, avisa usuario
  - Offline + sem banco: redireciona para login

## UTI Domestica -- Funcionalidades Planejadas (Cowork 2026-04-30)

### Conceito

Dashboard continuo de sinais vitais, inspirado em monitor de UTI. Nao snapshot -- tendencia ao longo do tempo. Correlacionar com diario de alimentacao, suplementos e rotina para identificar causa de variacoes.

### Bluetooth -- Regra absoluta

Todos os dispositivos integrados OBRIGATORIAMENTE tem Bluetooth. Nao integrar dispositivo sem BLE. Entrada manual e fallback para casos especificos apenas.

### Kit de dispositivos recomendado

- Omron HEM-6232T -- pressao arterial com BLE (~R$250)
- G-Tech Lite Smart -- glicemia com BLE (~R$150)
- Oximetro com BLE (~R$100, a definir modelo)
- Speedguc 3 em 1 -- glicose + acido urico + colesterol (sem BLE ainda -- entrada manual para acido urico/colesterol enquanto mercado nao evolui)

### Arquitetura BLE

```
utils/bluetooth/
  ble_manager.py        # scan, connect, disconnect (bleak)
  dispositivos/
    omron_pa.py
    gtech_glicose.py
    oximetro.py
  model_sinais.py       # tabela sinais_vitais no prontuario.db
```

Biblioteca: `bleak` (BLE puro Python, compativel com Android via Flet)

### Telas a criar

- `tela_dashboard_vital.py` -- painel UTI com grafico de tendencia + alertas
- `tela_anamnese.py` -- anamnese guiada (sequencia estruturada, nao campo livre)
- `claudia/diagnostico_diferencial.py` -- engine de diagnostico diferencial (5 estados de saida)

### Diario de correlacao

- Registrar: refeicao, suplemento, atividade, sono, humor, sintoma
- Claudia correlaciona automaticamente eventos do diario com variacoes nos sinais vitais
- Exemplos: batata-yacon x glicemia, magnesio x sono, propranolol x pressao

### Engine de diagnostico (protocolo completo em claudia/references/cid_diagnostico.md)

- Anamnese estruturada -> cruzamento com exames -> 1 dos 5 estados de saida
- Nunca retorna diagnostico fechado
- Integrado a tela_parecer.py
