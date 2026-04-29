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
- DB: `dados/prontuario.db`
- Tabelas principais: `usuarios`, `medicos`, `consultas`, `exames`, `remedios`, etc.
- Migracoes via ALTER TABLE IF NOT EXISTS (padrao do projeto)

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

## Diferenca vs Prestanista

- **COM**: extracao de PDF, IA (Claudia), remedios, dieta, parecer medico
- **SEM**: financeiro, vendas, parcelas, fornecedores, catalogo, compras
- Sem sync Drive bidirecional (apenas backup simples)
