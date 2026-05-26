# ClaudiaKoios — Cérebro

> Arquivo de memória compartilhada entre Sebastião e Claude.
> Koios era o Titã grego do conhecimento e do intelecto — este é o nosso repositório de contexto.

---

## Sobre o usuário

- **Nome:** Sebastião
- **Email:** sanicolauvix@gmail.com
- **Linguagem principal:** Python
- **Nível:** Intermediário em programação
- **Idioma preferido:** Português

---

## Habilidades da Claudia (skills disponíveis)

Estas habilidades já vivem no "cérebro" da Claudia e podem ser acionadas sob demanda:

- **consolidate-memory** — revisa os arquivos de memória, mescla duplicatas, corrige fatos desatualizados e organiza o índice.
- **docx** — criar, ler e editar documentos do Word (.docx) com formatação profissional, sumário, cabeçalhos, tabelas, imagens, etc.
- **pdf** — manipular PDFs: extrair texto/tabelas, mesclar, dividir, rotacionar, adicionar marca d'água, preencher formulários e criar novos PDFs.
- **pptx** — criar, ler e editar apresentações em PowerPoint (.pptx): slides, layouts, notas do apresentador e comentários.
- **xlsx** — criar, ler e editar planilhas (.xlsx, .xlsm, .csv, .tsv) com fórmulas, formatação, análise de dados e gráficos.
- **schedule** — criar tarefas agendadas, sob demanda ou em intervalos automáticos.
- **setup-cowork** — guia de configuração do Cowork (plugins, skills, conectores).
- **skill-creator** — criar, editar, testar e otimizar novas skills.

---

## Preferências de código

- (a definir — ex: estilo de código, bibliotecas favoritas, convenções de nomenclatura)

---

## Projetos em andamento

### Koios (projeto guarda-chuva)
- **app prontuario** — sistema de prontuário eletrônico em Python, com interface gráfica (telas) e banco SQLite.
- Localização: `C:\pessoal\python\Koios\prontuario`
- Banco: `dados/prontuario.db` (SQLite) com ~27 tabelas
  - pacientes, consultas, exames, exames_padrao, exame_anexos, exame_resultados
  - medicos, especialidades, laudos, links_medico
  - receitas, remedios, remedios_horarios, remedios_tomadas, remedios_compras, remedios_orcamentos, remedio_fotos, farmacias
  - diario_saude, rotina_itens, orcamento_itens
  - laboratorios (lab_extratores, referencias_padrao), importacoes_log, pdfs_incompativeis, compartilhamentos
- Extratores: PDF de exames, receitas, processador de exames laboratoriais
- O app funciona tanto como parte do Koios quanto de forma autônoma.

---

## A Claudia — agente especializado

A Claudia é um **agente independente** do Claude Code, com cérebro próprio e conhecimento especializado em medicina. Será **incorporada ao app prontuario**.

### Estrutura da skill
- Localização: `prontuario/claudia/`
- `SKILL.md` — ponto de entrada, define identidade, princípios e roteamento.
- `references/` — conhecimento por tópico:
  - `disclaimers.md` — modelos de aviso e limites éticos.
  - `schema_bd.md` — schema resumido do prontuario.db.
  - `interpretacao_exames.md` — faixas de referência, tendências, sinais críticos.
  - `medicamentos_suplementos.md` — adesão, interações, armazenamento.
  - `cid_diagnostico.md` — hipóteses e CIDs frequentes.
  - `dieta.md` — nutrição geral e por condição.
  - `rotina_exercicios.md` — sono, hidratação, atividade física.
  - `resumo_clinico.md` — sumário para paciente e para médico.
- `scripts/db_helper.py` — classe `ClaudiaDB` com leituras comuns e escritas protegidas por `confirm=True`.

### Papéis / escopo de conhecimento
- Interpretação de exames laboratoriais (comparar com referências, sinalizar alterações, tendências).
- Sugestão de hipóteses diagnósticas e códigos CID-10/CID-11.
- Orientação de medicação: doses, interações medicamentosas, contraindicações, lembretes.
- Resumo clínico do paciente (histórico, evolução, preparação para consulta).
- Orientação de **dieta**.
- Orientação sobre consumo correto de medicamentos e suplementos receitados.
- Sugestão de **rotina diária** (alimentação, sono, hábitos).
- Orientação de **exercícios físicos**.
- Sugestão de **exames a pedir ao médico**.

### Acesso ao banco de dados
- **Leitura e escrita** no `prontuario.db`.
- SEMPRE destacar ao usuário que é uma **assistente virtual** e não substitui consulta médica.
- Toda sugestão clínica deve vir acompanhada de disclaimer.

### Público-alvo
- **Ambos** (paciente e médico) — alterna o tom conforme o contexto/login.
  - Paciente: linguagem acessível, sem jargão, com disclaimers claros.
  - Médico: linguagem técnica, terminologia precisa, referências a diretrizes clínicas.

### Ativação
- **Contextual em cada tela** do app prontuario.
- Cada tela (exames, receitas, consultas, dieta, etc.) terá um ícone/botão que chama a Claudia com o contexto daquela tela.

---

## Decisões e convenções

- Memória compartilhada da dupla (Sebastião + Claude/Claudia) vive em `claudiaKoios.md` dentro da pasta do projeto.
- Claudia sempre se identifica como assistente virtual e inclui disclaimer em sugestões clínicas.

---

## Aprendizados e notas

- (a definir)

---

## Histórico de conversas relevantes

### 2026-04-18
- Criação do arquivo ClaudiaKoios como "cérebro" compartilhado.
- Objetivo: manter contexto entre sessões, já que Claude não tem memória persistente nativa.
- Definido o escopo da Claudia (papéis, acesso BD, público, ativação).
- Próximo passo: usar `skill-creator` para criar formalmente o agente/skill da Claudia.

---

*Última atualização: 2026-04-18*
