# hub_medico — Arquitetura

## Conceito

Visão do médico sobre o prontuário do paciente.
Acesso via link compartilhado (token) **ou direto pelo app** (durante desenvolvimento).
Somente leitura — médico pode apenas escrever observações e anexar PDFs.

---

## Arquitetura de arquivos

```
telas/tela_hub_medico.py          — tela principal (espelho do hub, visão médico)
telas/tela_medico_observacoes.py  — aba Observações: lista + form + upload anexo
main_medico.py                    — entry point web (porta 8552), valida token URL
```

---

## Fluxo de acesso

### Durante desenvolvimento (sem link)
```
app.py → botão "Visão Médico" no menu config
  → criar_tela_hub_medico(page, voltar_fn, medico_id=None)
  → tela abre sem validação de token
```

### Produção (via link compartilhado)
```
main_medico.py (web)
  → lê ?token=xxx da URL
  → valida token em links_medico (ativo=1)
  → busca medico_id e nome_medico
  → atualiza ultimo_acesso + acessos
  → criar_tela_hub_medico(page, voltar_fn=None, medico_id=medico_id)
```

---

## tela_hub_medico.py — estrutura

### Header (fixo no topo)
```
[foto paciente 44px]  Nome Paciente  •  Idade  •  Sexo
                      CID principal  •  badge "Visão Médico"
                                                [Dr(a). Nome]  [Sair]
```

### Seção sinais vitais (mini-hub read-only)
- Mesmos cards UTI do hub (Glicemia, Ac.Úrico, Pressão, etc.)
- Clique → overlay ampliado (igual hub) mas sem botão "Abrir tela completa"
- Badge "Última medição: dd/mm/aaaa" em cada card

### 3 abas

#### Aba 1 — Exames
- tela_exames embutida via `_conteudo_buscar` (somente busca + gráfico)
- Sem botões de adicionar/editar/excluir
- Flag `somente_leitura=True` passada para a tela

#### Aba 2 — Clínico
Subseções em scroll:
- **Histórico médico** — historico_medico (tipo, título, data, sequela/alerta)
- **Consultas recentes** — últimas 10 de consultas
- **Internações** — internacoes com CID e período
- **Medicamentos ativos** — remedios WHERE ativo=1
- **Alertas** — historico_medico WHERE alerta=1

#### Aba 3 — Observações
- Lista de observações já feitas pelo médico (tabela observacoes_medico)
- Formulário: texto livre + data + upload PDF opcional
- PDF vai para Drive: `Koios/Prontuario/observacoes_medico/`
- Paciente vê as observações na tela de pendências (notificação)

---

## Banco — tabela observacoes_medico

```sql
CREATE TABLE IF NOT EXISTS observacoes_medico (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    medico_id    INTEGER,
    nome_medico  TEXT,
    data         TEXT,           -- YYYY-MM-DD
    texto        TEXT NOT NULL,
    drive_file_id TEXT,          -- PDF anexado (opcional)
    nome_arquivo  TEXT,
    lida_paciente INTEGER DEFAULT 0,  -- 0=nao lida, 1=lida
    criado_em    TEXT DEFAULT (datetime('now'))
);
```

---

## Regras de leitura/escrita

| Ação                          | Permitido |
|-------------------------------|-----------|
| Ver exames, gráficos          | ✓         |
| Ver histórico, consultas      | ✓         |
| Ver remédios                  | ✓         |
| Ver internações               | ✓         |
| Escrever observação           | ✓         |
| Anexar PDF                    | ✓         |
| Editar dados do paciente      | ✗         |
| Excluir qualquer coisa        | ✗         |
| Adicionar exame/consulta      | ✗         |
| Navegar para fora da tela     | ✗         |

---

## Padrões Flet obrigatórios

- NUNCA `ft.Icons.XXX` — usar string `"icon_name"`
- NUNCA `ft.ElevatedButton` / `ft.FilledButton` — usar `ft.Container(ink=True)`
- NUNCA `ft.AlertDialog` — usar `page.overlay`
- `ft.Colors.with_opacity()` — permitido
- `_montado = [False]` — padrão obrigatório
- Icons como strings — obrigatório

---

## Integração com pendências do paciente

Quando médico salva observação:
- `lida_paciente = 0`
- Hub do paciente exibe badge de notificação na seção "Pendências"
- Ao paciente abrir a observação: UPDATE lida_paciente = 1
