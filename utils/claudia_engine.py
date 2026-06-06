# -*- coding: utf-8 -*-
# Prontuario Medico | utils/claudia_engine.py
# Motor da Claudia: cliente Anthropic + tools que consultam o banco
import os
import json
import logging
import sqlite3
from typing import Any

log = logging.getLogger(__name__)

_MODELO = "claude-sonnet-4-6"

_SYSTEM_PROMPT = """Voce e a Dra. Claudia, medica generalista especializada em Psiquiatria,
Reumatologia, Ortopedia, Urologia/Andrologia, Oftalmologia e Saude Esportiva.

Voce esta integrada ao prontuario pessoal de Sebastiao Alves Nicolau (Nico), 55 anos, Vitoria-ES.
Condicoes ativas conhecidas: Gastrite atrofica, Osteoporose (femur), Artrose, TDAH,
Espectro Bipolar, Suspeita AuDHD, HPB pos-cirurgia, Ansiedade cronica.

Tom: empatica, clara, objetiva — como uma medica de confianca de longa data.
Idioma: sempre portugues brasileiro.

Quando o usuario pedir analise de exames ou dados de saude:
1. Use as ferramentas disponiveis para buscar os dados do banco
2. Analise clinicamente os resultados
3. Retorne SEMPRE um JSON com dois campos:
   - "texto": sua analise clinica em linguagem acessivel
   - "grafico": objeto com dados para visualizacao (null se nao aplicavel)

Formato do campo "grafico" quando aplicavel:
{
  "tipo": "linha" | "barra" | "pizza",
  "titulo": "Titulo do grafico",
  "unidade": "ng/dL" | "%" | etc,
  "ref_min": valor numerico ou null,
  "ref_max": valor numerico ou null,
  "series": [
    {
      "label": "Nome da serie",
      "cor": "#58A6FF",
      "pontos": [{"x": "2024-01", "y": 450.0}, ...]
    }
  ]
}

Para respostas puramente textuais (sem grafico), retorne:
{"texto": "...", "grafico": null}

Limites eticos: nao prescreve medicamentos, nao diagnostica definitivamente.
Sugere exames, orienta sobre classes de medicamentos, alerta sobre sintomas criticos."""


# ══════════════════════════════════════════════════════════════
# CLIENTE
# ══════════════════════════════════════════════════════════════

def _get_key() -> str:
    """Lê a chave da API do banco de dados (prioridade) ou env var."""
    try:
        from dados.model_prontuario import get_config
        chave = get_config("anthropic_api_key", "")
        if chave:
            return chave
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY", "")


def get_client():
    """Retorna cliente Anthropic configurado com a chave do banco."""
    import anthropic
    chave = _get_key()
    if not chave:
        raise ValueError(
            "Chave da API Anthropic nao configurada.\n"
            "Va em Configuracoes > Geral > Claudia IA e informe a chave."
        )
    return anthropic.Anthropic(api_key=chave)


# ══════════════════════════════════════════════════════════════
# TOOLS — consultas ao banco
# ══════════════════════════════════════════════════════════════

_TOOLS: list[dict[str, Any]] = [
    {
        "name": "buscar_exames",
        "description": (
            "Busca resultados de exames do paciente por parametro (ex: 'Testosterona', "
            "'Hemoglobina', 'TSH'). Retorna serie historica com datas e valores. "
            "Use quando o usuario pedir analise de exames especificos."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "parametro": {
                    "type": "string",
                    "description": "Nome do parametro a buscar (ex: 'Testosterona Total', 'TSH', 'Glicose')",
                },
                "data_inicio": {
                    "type": "string",
                    "description": "Data inicial no formato YYYY-MM-DD (opcional)",
                },
                "data_fim": {
                    "type": "string",
                    "description": "Data final no formato YYYY-MM-DD (opcional)",
                },
            },
            "required": ["parametro"],
        },
    },
    {
        "name": "buscar_todos_exames_recentes",
        "description": (
            "Retorna todos os parametros de exames registrados nos ultimos meses, "
            "agrupados por tipo. Use para dar um panorama geral dos exames do paciente."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "meses": {
                    "type": "integer",
                    "description": "Quantos meses para tras buscar (padrao: 12)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "buscar_remedios_ativos",
        "description": "Lista todos os remedios em uso ativo com dosagem, frequencia e horarios.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "buscar_consultas",
        "description": "Retorna historico de consultas medicas, opcionalmente filtrado por especialidade.",
        "input_schema": {
            "type": "object",
            "properties": {
                "especialidade": {
                    "type": "string",
                    "description": "Nome da especialidade para filtrar (opcional)",
                },
                "limite": {
                    "type": "integer",
                    "description": "Maximo de consultas a retornar (padrao: 10)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "perfil_paciente",
        "description": "Retorna dados do perfil do paciente: nome, idade, peso, altura, condicoes cronicas.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "buscar_rotina_diario",
        "description": (
            "Retorna o historico de alteracoes da rotina diaria do paciente: suspensoes de alimentos, "
            "reducoes de porcao, adicoes, observacoes e sintomas registrados. "
            "Use para correlacionar mudancas de habito com variacoes nos exames ou sintomas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "dias": {
                    "type": "integer",
                    "description": "Quantos dias de historico retornar (default 60).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "conhecimento_exame",
        "description": (
            "Retorna conhecimento clinico detalhado sobre um exame: o que mede, sistema/orgao avaliado, "
            "o que significa quando alto ou baixo, faixa de alerta, quem solicita, interferentes, "
            "preparo do paciente e curiosidade clinica. "
            "Use SEMPRE que o usuario perguntar sobre um exame especifico ou pedir interpretacao de resultado."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "parametro": {
                    "type": "string",
                    "description": "Nome do exame ou parametro (ex: 'Glicemia de Jejum', 'HbA1c', 'Creatinina').",
                },
            },
            "required": ["parametro"],
        },
    },
]


# ══════════════════════════════════════════════════════════════
# EXECUTORES DE TOOLS
# ══════════════════════════════════════════════════════════════

def _exec_conhecimento_exame(parametro: str) -> dict:
    """Retorna conhecimento clinico do exame (exame_conhecimento) para enriquecer resposta da Claudia."""
    try:
        from dados.model_prontuario import DB_PATH
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT ek.o_que_mede, ek.sistema_orgao, ek.alterado_alto, ek.alterado_baixo,
                       ek.faixa_alerta, ek.quem_solicita, ek.interferentes,
                       ek.preparo_paciente, ek.curiosidade_clinica, ek.fonte,
                       ep.nome_oficial
                FROM exame_conhecimento ek
                JOIN exames_padrao ep ON ep.id = ek.exame_padrao_id
                WHERE UPPER(ep.nome_oficial) LIKE UPPER(?)
                LIMIT 1
            """, (f"%{parametro}%",)).fetchone()
            if row:
                return {"encontrado": True, "dados": dict(row)}
            return {"encontrado": False}
    except Exception as ex:
        return {"erro": str(ex)}


def _exec_buscar_exames(parametro: str, data_inicio: str = "", data_fim: str = "") -> dict:
    try:
        from dados.model_prontuario import DB_PATH
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            params: list[Any] = [f"%{parametro}%"]
            sql = """
                SELECT e.data_exame, e.laboratorio,
                       r.parametro, r.valor, r.unidade, r.referencia, r.nivel_interpretacao
                FROM exame_resultados r
                JOIN exames e ON r.exame_id = e.id
                WHERE r.parametro LIKE ?
            """
            if data_inicio:
                sql += " AND e.data_exame >= ?"
                params.append(data_inicio)
            if data_fim:
                sql += " AND e.data_exame <= ?"
                params.append(data_fim)
            sql += " ORDER BY e.data_exame ASC"
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        return {"parametro": parametro, "total": len(rows), "resultados": rows}
    except Exception as ex:
        return {"erro": str(ex)}


def _exec_buscar_todos_exames_recentes(meses: int = 12) -> dict:
    try:
        from dados.model_prontuario import DB_PATH
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT e.data_exame, e.laboratorio,
                       r.parametro, r.valor, r.unidade, r.nivel_interpretacao
                FROM exame_resultados r
                JOIN exames e ON r.exame_id = e.id
                WHERE e.data_exame >= date('now', ? || ' months')
                ORDER BY e.data_exame DESC, r.parametro ASC
            """, (f"-{meses}",)).fetchall()
            return {"meses": meses, "total": len(rows), "resultados": [dict(r) for r in rows]}
    except Exception as ex:
        return {"erro": str(ex)}


def _exec_buscar_remedios_ativos() -> dict:
    try:
        from dados.model_prontuario import DB_PATH
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            remedios = conn.execute("""
                SELECT r.nome, r.dosagem, r.frequencia, r.data_inicio,
                       r.estoque_atual, r.estoque_minimo, r.observacoes,
                       GROUP_CONCAT(h.hora, ', ') AS horarios
                FROM remedios r
                LEFT JOIN remedios_horarios h ON h.remedio_id = r.id
                WHERE r.ativo = 1
                GROUP BY r.id
                ORDER BY r.nome
            """).fetchall()
        return {"total": len(remedios), "remedios": [dict(r) for r in remedios]}
    except Exception as ex:
        return {"erro": str(ex)}


def _exec_buscar_consultas(especialidade: str = "", limite: int = 10) -> dict:
    try:
        from dados.model_prontuario import DB_PATH
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            params: list[Any] = []
            sql = """
                SELECT c.data, c.hora, c.tipo, c.local, c.observacoes,
                       m.nome AS medico, m.especialidade
                FROM consultas c
                LEFT JOIN medicos m ON c.medico_id = m.id
                WHERE 1=1
            """
            if especialidade:
                sql += " AND m.especialidade LIKE ?"
                params.append(f"%{especialidade}%")
            sql += " ORDER BY c.data DESC LIMIT ?"
            params.append(limite)
            rows = conn.execute(sql, params).fetchall()
        return {"total": len(rows), "consultas": [dict(r) for r in rows]}
    except Exception as ex:
        return {"erro": str(ex)}


def _exec_perfil_paciente() -> dict:
    try:
        from dados.model_prontuario import carregar_perfil, get_config
        perfil = carregar_perfil() or {}
        # calcula idade
        from datetime import date
        dn = perfil.get("data_nasc", "")
        idade = None
        if dn:
            try:
                ano, mes, dia = map(int, dn.split("-"))
                hoje = date.today()
                idade = hoje.year - ano - ((hoje.month, hoje.day) < (mes, dia))
            except Exception:
                pass
        return {
            "nome":              perfil.get("nome", ""),
            "idade":             idade,
            "peso":              perfil.get("peso"),
            "altura":            perfil.get("altura"),
            "tipo_sanguineo":    perfil.get("tipo_sanguineo", ""),
            "condicoes_cronicas": perfil.get("condicoes_cronicas", ""),
        }
    except Exception as ex:
        return {"erro": str(ex)}


def _exec_buscar_rotina_diario(dias: int = 60) -> dict:
    try:
        from dados.model_prontuario import listar_rotina_diario
        from datetime import date, timedelta
        desde = (date.today() - timedelta(days=dias)).isoformat()
        registros = listar_rotina_diario(limite=200)
        filtrados = [r for r in registros if r.get("data", "") >= desde]
        return {"dias": dias, "total": len(filtrados), "registros": filtrados}
    except Exception as ex:
        return {"erro": str(ex)}


_EXEC_MAP = {
    "buscar_exames":               lambda i: _exec_buscar_exames(**i),
    "buscar_todos_exames_recentes": lambda i: _exec_buscar_todos_exames_recentes(**i),
    "buscar_remedios_ativos":      lambda _: _exec_buscar_remedios_ativos(),
    "buscar_consultas":            lambda i: _exec_buscar_consultas(**i),
    "perfil_paciente":             lambda _: _exec_perfil_paciente(),
    "buscar_rotina_diario":        lambda i: _exec_buscar_rotina_diario(**i),
    "conhecimento_exame":          lambda i: _exec_conhecimento_exame(**i),
}


# ══════════════════════════════════════════════════════════════
# ENVIAR MENSAGEM (agentic loop com tool use)
# ══════════════════════════════════════════════════════════════

def enviar_mensagem(historico: list[dict], mensagem_usuario: str) -> dict:
    """
    Envia mensagem para a Claudia e retorna dict com:
      {"texto": "...", "grafico": {...} | null}

    historico: lista de {"role": "user"|"assistant", "content": "..."}
    Raises: ValueError se chave nao configurada, Exception em erro de API.
    """
    import anthropic

    client    = get_client()
    mensagens = historico[-18:] + [{"role": "user", "content": mensagem_usuario}]

    # Agentic loop com tool use
    for _tentativa in range(5):
        resp = client.messages.create(
            model=_MODELO,
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            tools=_TOOLS,
            messages=mensagens,
        )

        # Acrescentar resposta do assistente ao historico interno
        mensagens.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason == "tool_use":
            # Executar todas as tools pedidas
            tool_results = []
            for bloco in resp.content:
                if bloco.type == "tool_use":
                    executor = _EXEC_MAP.get(bloco.name)
                    if executor:
                        resultado = executor(bloco.input)
                    else:
                        resultado = {"erro": f"tool desconhecida: {bloco.name}"}
                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": bloco.id,
                        "content":     json.dumps(resultado, ensure_ascii=False),
                    })
            mensagens.append({"role": "user", "content": tool_results})
            continue  # proxima iteracao com os resultados

        # stop_reason == "end_turn" — parsear resposta final
        texto_bruto = ""
        for bloco in resp.content:
            if hasattr(bloco, "text"):
                texto_bruto += bloco.text

        # Tentar extrair JSON {"texto": ..., "grafico": ...}
        try:
            # Suporte a ```json ... ``` e JSON solto
            raw = texto_bruto.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            resultado = json.loads(raw)
            if "texto" not in resultado:
                resultado = {"texto": texto_bruto, "grafico": None}
        except Exception:
            resultado = {"texto": texto_bruto, "grafico": None}

        return resultado

    return {"texto": "Limite de iteracoes atingido. Tente reformular a pergunta.", "grafico": None}
