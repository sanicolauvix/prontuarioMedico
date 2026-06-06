# -*- coding: utf-8 -*-
"""
popular_conhecimento.py
Carga completa de conhecimento clínico no banco do Prontuário.

O que faz:
  1. Migra banco (colunas novas em exames_padrao, referencias_padrao, cria exame_conhecimento)
  2. Popula exame_conhecimento a partir de help/exames_laboratoriais_completo.json
  3. Expande referencias_padrao com faixas etárias completas (M/F por idade)
  4. Vincula tudo via exame_padrao_id

Executar uma vez após criar as tabelas:
    cd prontuario
    python dados/popular_conhecimento.py

Pode ser executado novamente sem duplicar (usa INSERT OR IGNORE + UPDATE).
"""

import sqlite3
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

DB_PATH    = Path(__file__).parent / "prontuario.db"
JSON_PATH  = Path(__file__).parent.parent.parent / "help" / "exames_laboratoriais_completo.json"


# ══════════════════════════════════════════════════════════════════════════════
# 1. MIGRAÇÃO — garante que todas as colunas existem
# ══════════════════════════════════════════════════════════════════════════════

def _migrar(conn: sqlite3.Connection):
    cur = conn.cursor()

    # exames_padrao — colunas novas
    for col, typedef in [
        ("subcategoria", "TEXT"),
    ]:
        try:
            cur.execute(f"ALTER TABLE exames_padrao ADD COLUMN {col} {typedef}")
            logging.info(f"[MIGRAR] exames_padrao.{col} adicionada")
        except sqlite3.OperationalError:
            pass  # já existe

    # referencias_padrao — coluna fonte
    try:
        cur.execute("ALTER TABLE referencias_padrao ADD COLUMN fonte TEXT")
        logging.info("[MIGRAR] referencias_padrao.fonte adicionada")
    except sqlite3.OperationalError:
        pass

    # exame_conhecimento — criar se não existe
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exame_conhecimento (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            exame_padrao_id     INTEGER UNIQUE REFERENCES exames_padrao(id) ON DELETE CASCADE,
            o_que_mede          TEXT,
            marcadores          TEXT,
            sistema_orgao       TEXT,
            alterado_alto       TEXT,
            alterado_baixo      TEXT,
            faixa_alerta        TEXT,
            quem_solicita       TEXT,
            especialidades      TEXT,
            frequencia          TEXT,
            indicacoes          TEXT,
            interferentes       TEXT,
            preparo_paciente    TEXT,
            curiosidade_clinica TEXT,
            fonte               TEXT,
            atualizado_em       TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    logging.info("[MIGRAR] exame_conhecimento verificada/criada")


# ══════════════════════════════════════════════════════════════════════════════
# 2. HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _buscar_padrao_id(cur, nome_oficial: str) -> int | None:
    """Busca exame_padrao.id por nome_oficial exato ou por sinônimo."""
    row = cur.execute(
        "SELECT id FROM exames_padrao WHERE UPPER(nome_oficial)=UPPER(?)",
        (nome_oficial,)
    ).fetchone()
    if row:
        return row[0]
    # Tenta por sinônimo (campo TEXT com nomes separados por vírgula)
    row = cur.execute(
        "SELECT id FROM exames_padrao WHERE UPPER(sinonimos) LIKE UPPER(?)",
        (f"%{nome_oficial}%",)
    ).fetchone()
    return row[0] if row else None


def _garantir_padrao(cur, nome: str, sinonimos: list, categoria: str,
                     subcategoria: str, unidade: str) -> int:
    """Insere exame_padrao se não existir. Retorna id."""
    row = cur.execute(
        "SELECT id FROM exames_padrao WHERE UPPER(nome_oficial)=UPPER(?)",
        (nome,)
    ).fetchone()
    if row:
        # Atualiza subcategoria e unidade se estavam vazios
        cur.execute("""
            UPDATE exames_padrao
            SET subcategoria = COALESCE(NULLIF(subcategoria,''), ?),
                unidade      = COALESCE(NULLIF(unidade,''), ?),
                categoria    = COALESCE(NULLIF(categoria,''), ?)
            WHERE id = ?
        """, (subcategoria, unidade, categoria, row[0]))
        return row[0]

    sins_txt = ", ".join(sinonimos) if sinonimos else ""
    cur.execute("""
        INSERT INTO exames_padrao (nome_oficial, sinonimos, categoria, subcategoria, tipo, unidade, ativo)
        VALUES (?, ?, ?, ?, 'numerico', ?, 1)
    """, (nome, sins_txt, categoria, subcategoria, unidade))
    return cur.lastrowid


def _inserir_conhecimento(cur, pid: int, k: dict):
    """Insere ou atualiza exame_conhecimento para o exame_padrao_id."""
    marcadores   = json.dumps(k.get("marcadores",   []), ensure_ascii=False)
    especialidades = json.dumps(k.get("especialidades", []), ensure_ascii=False)

    existing = cur.execute(
        "SELECT id FROM exame_conhecimento WHERE exame_padrao_id=?", (pid,)
    ).fetchone()

    if existing:
        cur.execute("""
            UPDATE exame_conhecimento SET
                o_que_mede=?, marcadores=?, sistema_orgao=?,
                alterado_alto=?, alterado_baixo=?, faixa_alerta=?,
                quem_solicita=?, especialidades=?, frequencia=?,
                indicacoes=?, interferentes=?, preparo_paciente=?,
                curiosidade_clinica=?, fonte=?, atualizado_em=datetime('now')
            WHERE exame_padrao_id=?
        """, (
            k.get("o_que_mede"), marcadores, k.get("sistema_orgao"),
            k.get("alterado_alto_indica") or k.get("alterado_alto"),
            k.get("alterado_baixo_indica") or k.get("alterado_baixo"),
            k.get("faixa_alerta"),
            k.get("quem_solicita"), especialidades, k.get("frequencia"),
            k.get("indicacoes"), k.get("interferentes"),
            k.get("preparo_paciente"), k.get("curiosidade_clinica"),
            k.get("fonte"), pid,
        ))
    else:
        cur.execute("""
            INSERT INTO exame_conhecimento
                (exame_padrao_id, o_que_mede, marcadores, sistema_orgao,
                 alterado_alto, alterado_baixo, faixa_alerta,
                 quem_solicita, especialidades, frequencia,
                 indicacoes, interferentes, preparo_paciente,
                 curiosidade_clinica, fonte)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            pid,
            k.get("o_que_mede"),
            marcadores,
            k.get("sistema_orgao"),
            k.get("alterado_alto_indica") or k.get("alterado_alto"),
            k.get("alterado_baixo_indica") or k.get("alterado_baixo"),
            k.get("faixa_alerta"),
            k.get("quem_solicita"),
            especialidades,
            k.get("frequencia"),
            k.get("indicacoes"),
            k.get("interferentes"),
            k.get("preparo_paciente"),
            k.get("curiosidade_clinica"),
            k.get("fonte"),
        ))


def _inserir_referencias(cur, pid: int, refs: list):
    """Insere referências por faixa etária — não duplica."""
    for r in refs:
        sexo     = r.get("sexo")
        imin     = r.get("idade_min", 0)
        imax     = r.get("idade_max", 999)
        obs      = r.get("observacoes") or r.get("obs", "")
        fonte    = r.get("fonte", "SBPC/ML 2023")

        exists = cur.execute("""
            SELECT id FROM referencias_padrao
            WHERE exame_padrao_id=? AND sexo IS ? AND idade_min=? AND idade_max=?
              AND (observacoes IS ? OR (observacoes IS NULL AND ? IS NULL))
        """, (pid, sexo, imin, imax, obs, obs)).fetchone()

        if exists:
            cur.execute("""
                UPDATE referencias_padrao SET
                    critico_baixo=?, limite_baixo=?, otimo_min=?, otimo_max=?,
                    limite_alto=?, critico_alto=?, observacoes=?, fonte=?
                WHERE id=?
            """, (
                r.get("critico_baixo"), r.get("limite_baixo"),
                r.get("otimo_min"),    r.get("otimo_max"),
                r.get("limite_alto"),  r.get("critico_alto"),
                obs, fonte, exists[0],
            ))
        else:
            cur.execute("""
                INSERT INTO referencias_padrao
                    (exame_padrao_id, sexo, idade_min, idade_max,
                     critico_baixo, limite_baixo, otimo_min, otimo_max,
                     limite_alto, critico_alto, observacoes, fonte)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                pid, sexo, imin, imax,
                r.get("critico_baixo"), r.get("limite_baixo"),
                r.get("otimo_min"),    r.get("otimo_max"),
                r.get("limite_alto"),  r.get("critico_alto"),
                obs, fonte,
            ))


# ══════════════════════════════════════════════════════════════════════════════
# 3. CARGA DO JSON DA PESQUISA (conhecimento clínico)
# ══════════════════════════════════════════════════════════════════════════════

def _carregar_json_conhecimento(conn: sqlite3.Connection):
    if not JSON_PATH.exists():
        logging.warning(f"[JSON] Arquivo não encontrado: {JSON_PATH}")
        return 0

    with open(JSON_PATH, encoding="utf-8") as f:
        exames = json.load(f)

    cur = conn.cursor()
    ok = 0
    for ex in exames:
        nome       = ex.get("nome_oficial", "").strip()
        sins       = ex.get("sinonimos", [])
        cat        = ex.get("categoria", "")
        subcat     = ex.get("subcategoria", "")
        unidade    = ex.get("unidade_padrao", "")

        if not nome:
            continue

        pid = _garantir_padrao(cur, nome, sins, cat, subcat, unidade)
        _inserir_conhecimento(cur, pid, ex)
        ok += 1

    conn.commit()
    logging.info(f"[JSON] {ok} exames com conhecimento clínico carregados")
    return ok


# ══════════════════════════════════════════════════════════════════════════════
# 4. CARGA DAS REFERÊNCIAS COMPLETAS POR FAIXA ETÁRIA
# ══════════════════════════════════════════════════════════════════════════════

def _r(sexo, imin, imax, baixo, alto,
       cbaixo=None, calto=None, omin=None, omax=None,
       obs="", fonte="SBPC/ML 2023"):
    return {"sexo": sexo, "idade_min": imin, "idade_max": imax,
            "critico_baixo": cbaixo, "limite_baixo": baixo,
            "otimo_min": omin, "otimo_max": omax,
            "limite_alto": alto, "critico_alto": calto,
            "observacoes": obs, "fonte": fonte}


def _am(imin, imax, baixo, alto, **kw):
    return [_r("M", imin, imax, baixo, alto, **kw),
            _r("F", imin, imax, baixo, alto, **kw)]


# Mapa: nome_oficial → lista de referências expandidas
REFERENCIAS_EXPANDIDAS = {

    # ── HEMOGRAMA ─────────────────────────────────────────────────────────────
    "Hemácias": [
        _r("M", 0,   0,  4.0, 6.6, obs="RN"),
        _r("M", 0,   1,  3.0, 5.4, obs="1-30 dias"),
        _r("M", 1,   6,  2.7, 4.9, obs="1-6 meses"),
        _r("M", 6,  24,  3.0, 5.4, obs="6m-2 anos"),
        _r("M", 2,  12,  3.7, 5.3, obs="2-12 anos"),
        _r("M", 12, 18,  4.2, 5.6, obs="12-18 anos"),
        _r("M", 18,999,  4.5, 5.9, cbaixo=2.0, calto=7.0, obs="adulto"),
        _r("F", 0,   0,  4.0, 6.6, obs="RN"),
        _r("F", 2,  12,  3.7, 5.3, obs="2-12 anos"),
        _r("F", 12, 18,  3.8, 5.2, obs="12-18 anos"),
        _r("F", 18,999,  4.0, 5.2, cbaixo=2.0, calto=7.0, obs="adulta"),
    ],
    "Hemoglobina": [
        _r("M", 0,   0, 13.5,19.5, cbaixo=7.0,calto=25.0, obs="RN"),
        _r("M", 0,   1,  9.5,13.5, obs="1-30 dias"),
        _r("M", 1,   2,  9.0,14.0, obs="1-2 meses"),
        _r("M", 2,   6,  9.5,13.5, obs="2-6 meses"),
        _r("M", 6,  24, 10.5,14.0, obs="6m-2 anos"),
        _r("M", 2,   6, 11.5,13.5, obs="2-6 anos"),
        _r("M", 6,  12, 11.5,15.5, obs="6-12 anos"),
        _r("M", 12, 18, 13.0,16.0, obs="12-18 anos"),
        _r("M", 18,999, 13.5,17.5, cbaixo=7.0,calto=20.0, omin=13.5,omax=17.5, obs="adulto",
           fonte="HTCT Brasil 2022 / PNS-IBGE"),
        _r("F", 2,   6, 11.5,13.5, obs="2-6 anos"),
        _r("F", 6,  12, 11.5,15.5, obs="6-12 anos"),
        _r("F", 12, 18, 12.0,16.0, obs="12-18 anos"),
        _r("F", 18,999, 12.0,16.0, cbaixo=7.0,calto=20.0, omin=12.0,omax=16.0, obs="adulta"),
        _r("F", 18,999, 11.0,14.0, obs="gestante", fonte="OMS 2011"),
    ],
    "Hematócrito": [
        _r("M", 0,   0, 44, 64, obs="RN"),
        _r("M", 0,   1, 31, 55, obs="1-30 dias"),
        _r("M", 1,   6, 28, 42, obs="1-6 meses"),
        _r("M", 6,  24, 33, 42, obs="6m-2 anos"),
        _r("M", 2,  12, 34, 40, obs="2-12 anos"),
        _r("M", 12, 18, 37, 49, obs="12-18 anos"),
        _r("M", 18,999, 40, 52, cbaixo=18,calto=60, obs="adulto"),
        _r("F", 12, 18, 36, 46, obs="12-18 anos"),
        _r("F", 18,999, 36, 46, cbaixo=18,calto=60, obs="adulta"),
        _r("F", 18,999, 33, 42, obs="gestante"),
    ],
    "VCM": [
        _r("M", 0,   0, 100,128, obs="RN"),
        _r("M", 0,   6,  85,123, obs="0-6 meses"),
        _r("M", 6,  24,  70, 86, obs="6m-2 anos"),
        _r("M", 2,  12,  73, 89, obs="2-12 anos"),
        _r("M", 12,999,  80,100, obs="adolescente/adulto"),
        _r("F", 12,999,  80,100, obs="adolescente/adulto"),
    ],
    "HCM": [
        _r("M", 0,   0,  31, 37, obs="RN"),
        _r("M", 2,  12,  25, 33, obs="2-12 anos"),
        _r("M", 12,999,  27, 34, obs="adulto"),
        _r("F", 12,999,  27, 34, obs="adulta"),
    ],
    "CHCM": [*_am(0, 999, 31, 36, obs="todas idades")],
    "RDW":  [*_am(18,999, 11.5, 14.5, obs="adulto")],
    "Leucócitos": [
        _r("M",  0,  0,  9.0,38.0, cbaixo=1.0,calto=50.0, obs="RN"),
        _r("M",  0,  1,  5.0,21.0, obs="1-30 dias"),
        _r("M",  1,  6,  6.0,17.5, obs="1-6 meses"),
        _r("M",  6, 24,  6.0,17.0, obs="6m-2 anos"),
        _r("M",  2,  6,  5.0,15.5, obs="2-6 anos"),
        _r("M",  6, 12,  4.5,13.5, obs="6-12 anos"),
        _r("M", 12,999,  4.5,11.0, cbaixo=1.0,calto=30.0, obs="adulto",
           fonte="HTCT Brasil 2022"),
        _r("F", 12,999,  4.5,11.0, cbaixo=1.0,calto=30.0, obs="adulta"),
    ],
    "Neutrófilos Segmentados": [
        _r("M", 18,999, 45, 70, obs="adulto %"),
        _r("F", 18,999, 45, 70, obs="adulta %"),
    ],
    "Linfócitos Típicos": [
        _r("M",  0,  6, 42, 72, obs="lactente"),
        _r("M",  2, 12, 25, 50, obs="2-12 anos"),
        _r("M", 12,999, 20, 45, obs="adulto %"),
        _r("F", 12,999, 20, 45, obs="adulta %"),
    ],
    "Eosinófilos":           [*_am(18,999, 1,  5, obs="adulto %")],
    "Basófilos":             [*_am(18,999, 0,  1, obs="adulto %")],
    "Monócitos":             [*_am(18,999, 2, 10, obs="adulto %")],
    "Neutrófilos Bastonetes":[*_am(18,999, 0,  5, obs="adulto %")],
    "Plaquetas": [
        _r("M", 0, 0,   150,450, cbaixo=20,calto=1000, obs="RN"),
        _r("M", 0,999,  150,450, cbaixo=20,calto=1000, obs="todas idades"),
        _r("F", 0,999,  150,450, cbaixo=20,calto=1000, obs="todas idades"),
    ],
    "VPM": [*_am(18,999, 7.5,12.5, obs="adulto")],
    "Volume Plaquetário Médio (MPV)": [*_am(18,999, 7.5,12.5, obs="adulto")],
    "MPV": [*_am(18,999, 7.5,12.5, obs="adulto")],

    # ── METABOLISMO GLICÍDICO ─────────────────────────────────────────────────
    "Glicemia de Jejum": [
        _r("M",  0,  0,  45,110, cbaixo=40,calto=150, obs="RN"),
        _r("M",  2, 12,  60,100, obs="criança"),
        _r("M", 12,999,  70, 99, cbaixo=50,calto=500, omin=70,omax=99, obs="normal adulto"),
        _r("F", 12,999,  70, 99, cbaixo=50,calto=500, omin=70,omax=99, obs="normal adulta"),
        _r("F", 18,999,  70, 92, obs="gestante", fonte="IADPSG 2010"),
    ],
    "Hemoglobina Glicada (HbA1c)": [
        _r("M", 18,999, None,5.6, omin=4.0,omax=5.6, obs="normal adulto",         fonte="SBD 2024"),
        _r("M", 18,999,  5.7,6.4, obs="pré-diabetes"),
        _r("F", 18,999, None,5.6, omin=4.0,omax=5.6, obs="normal adulta"),
        _r("F", 18,999,  5.7,6.4, obs="pré-diabetes"),
    ],
    "Insulina Basal": [
        *_am(18,999, 2.0,25.0, omin=2.0,omax=10.0, obs="adulto jejum"),
    ],

    # ── LIPÍDIOS ──────────────────────────────────────────────────────────────
    "Colesterol Total": [
        _r("M",  2, 19, None,170, obs="criança/adolescente", fonte="SBC 2023"),
        _r("M", 20,999, None,190, omin=0,omax=190, calto=500, obs="adulto desejável"),
        _r("F",  2, 19, None,170, obs="criança/adolescente"),
        _r("F", 20,999, None,190, omin=0,omax=190, calto=500, obs="adulta desejável"),
    ],
    "Colesterol HDL": [
        _r("M",  2, 19,  45,None, obs="criança"),
        _r("M", 20,999,  40,None, omin=60,omax=999, cbaixo=25, obs="adulto > 40; ótimo > 60"),
        _r("F",  2, 19,  45,None, obs="criança"),
        _r("F", 20,999,  50,None, omin=60,omax=999, cbaixo=25, obs="adulta > 50; ótimo > 60"),
    ],
    "Colesterol LDL": [
        _r("M",  2, 19, None,110, obs="criança ótimo"),
        _r("M", 20,999, None,130, omin=0,omax=100, obs="adulto risco baixo"),
        _r("M", 20,999, None,100, omin=0,omax=70,  obs="adulto risco intermediário"),
        _r("M", 20,999, None, 70, omin=0,omax=50,  obs="adulto risco alto"),
        _r("M", 20,999, None, 50, omin=0,omax=30,  obs="adulto risco muito alto"),
        _r("F",  2, 19, None,110, obs="criança ótimo"),
        _r("F", 20,999, None,130, omin=0,omax=100, obs="adulta risco baixo"),
    ],
    "Colesterol VLDL":    [*_am(18,999, None,30, obs="adulto")],
    "Colesterol Não-HDL": [
        _r("M", 20,999, None,160, omin=0,omax=130, obs="adulto risco baixo"),
        _r("M", 20,999, None,130, omin=0,omax=100, obs="adulto risco alto"),
        _r("M", 20,999, None,100, omin=0,omax=80,  obs="adulto risco muito alto"),
        _r("F", 20,999, None,160, omin=0,omax=130, obs="adulta risco baixo"),
    ],
    "Triglicerídeos": [
        _r("M",  2, 19, None,130, obs="criança/adolescente"),
        _r("M", 20,999, None,150, omin=0,omax=150, calto=1000, obs="adulto desejável"),
        _r("M", 20,999, 150, 199, obs="limítrofe"),
        _r("M", 20,999, 200, 499, obs="alto"),
        _r("M", 20,999, 500,None, calto=1000, obs="muito alto — risco pancreatite"),
        _r("F", 20,999, None,150, omin=0,omax=150, calto=1000, obs="adulta desejável"),
    ],

    # ── FUNÇÃO RENAL ──────────────────────────────────────────────────────────
    "Creatinina": [
        _r("M",  0,  0, 0.3,1.0, obs="RN"),
        _r("M",  0,  6, 0.2,0.4, obs="lactente"),
        _r("M",  1,  3, 0.2,0.6, obs="1-3 anos"),
        _r("M",  3, 12, 0.3,0.8, obs="3-12 anos"),
        _r("M", 12, 18, 0.5,1.0, obs="12-18 anos"),
        _r("M", 18,999, 0.7,1.3, cbaixo=0.3,calto=10.0, obs="adulto"),
        _r("F", 12, 18, 0.4,0.9, obs="12-18 anos"),
        _r("F", 18,999, 0.5,1.1, cbaixo=0.3,calto=10.0, obs="adulta"),
        _r("F", 18,999, 0.4,0.8, obs="gestante"),
    ],
    "Ureia": [
        _r("M",  0, 12,  3, 15, obs="lactente"),
        _r("M",  1, 12,  5, 18, obs="1-12 anos"),
        _r("M", 12,999, 10, 50, cbaixo=3,calto=200, obs="adulto"),
        _r("F", 12,999, 10, 45, cbaixo=3,calto=200, obs="adulta"),
    ],
    "Ácido Úrico": [
        _r("M",  2, 12, 2.0,5.5, obs="criança"),
        _r("M", 12, 18, 2.0,7.0, obs="adolescente"),
        _r("M", 18,999, 3.4,7.0, cbaixo=1.0,calto=12.0, omin=3.4,omax=6.0,
           obs="adulto; meta gota < 6 mg/dL"),
        _r("F",  2, 12, 2.0,5.5, obs="criança"),
        _r("F", 12, 18, 2.0,6.0, obs="adolescente"),
        _r("F", 18, 50, 2.4,6.0, cbaixo=1.0,calto=10.0, obs="adulta pré-menopausa"),
        _r("F", 50,999, 2.4,7.0, obs="pós-menopausa"),
    ],
    "eRFG (CKD-EPI)": [
        _r("M", 18,999, 60,None, omin=90,omax=999, obs="normal ≥ 60; ótimo ≥ 90"),
        _r("F", 18,999, 60,None, omin=90,omax=999, obs="normal ≥ 60; ótimo ≥ 90"),
    ],
    "eRFG": [
        _r("M", 18,999, 60,None, omin=90,omax=999, obs="normal ≥ 60; ótimo ≥ 90"),
        _r("F", 18,999, 60,None, omin=90,omax=999, obs="normal ≥ 60; ótimo ≥ 90"),
    ],

    # ── FUNÇÃO HEPÁTICA ───────────────────────────────────────────────────────
    "TGO (AST)": [
        _r("M",  0,  0,  25, 75, obs="RN"),
        _r("M",  0, 12,  20, 60, obs="lactente"),
        _r("M",  1,  6,  20, 50, obs="1-6 anos"),
        _r("M",  6, 12,  15, 40, obs="6-12 anos"),
        _r("M", 12, 18,  10, 40, obs="12-18 anos"),
        _r("M", 18,999,  10, 40, calto=400, obs="adulto"),
        _r("F", 12, 18,  10, 35, obs="12-18 anos"),
        _r("F", 18,999,  10, 32, calto=400, obs="adulta"),
    ],
    "TGP (ALT)": [
        _r("M",  0, 12,  10, 45, obs="lactente"),
        _r("M",  1, 12,  10, 35, obs="1-12 anos"),
        _r("M", 12, 18,  10, 35, obs="12-18 anos"),
        _r("M", 18,999,   7, 56, calto=500, obs="adulto"),
        _r("F", 12, 18,   7, 35, obs="12-18 anos"),
        _r("F", 18,999,   7, 40, calto=500, obs="adulta"),
    ],
    "GGT": [
        _r("M",  0,  6,   0,185, obs="RN/lactente"),
        _r("M",  6, 12,   0, 34, obs="6m-1 ano"),
        _r("M",  1, 12,   0, 22, obs="1-12 anos"),
        _r("M", 12, 18,   0, 27, obs="12-18 anos"),
        _r("M", 18,999,   9, 72, calto=500, obs="adulto"),
        _r("F", 12, 18,   0, 22, obs="12-18 anos"),
        _r("F", 18,999,   7, 45, calto=500, obs="adulta"),
    ],
    "Fosfatase Alcalina": [
        _r("M",  0,  2,  75,316, obs="RN/lactente"),
        _r("M",  2,  6,  80,280, obs="2-6 anos"),
        _r("M",  6, 12, 100,350, obs="6-12 anos"),
        _r("M", 12, 18, 100,400, obs="12-18 anos (pico puberdade)"),
        _r("M", 18,999,  44,147, calto=1000, obs="adulto"),
        _r("F", 12, 18, 100,380, obs="12-18 anos"),
        _r("F", 18,999,  40,130, calto=1000, obs="adulta"),
        _r("F", 18,999,  40,400, obs="gestante 3º trimestre"),
    ],
    "Bilirrubina Total": [
        _r("M",  0,  0,  1.0,10.0, calto=20.0, obs="RN"),
        _r("M",  0,  1,  0.0, 5.0, obs="1-30 dias"),
        _r("M",  1,999,  0.2, 1.2, calto=15.0, obs="criança/adulto"),
        _r("F",  1,999,  0.2, 1.0, calto=15.0, obs="adulta"),
    ],
    "Bilirrubina Direta":   [*_am(1,999, 0, 0.3, obs="adulto")],
    "Bilirrubina Indireta": [*_am(1,999, 0, 0.9, obs="adulto")],
    "Albumina": [
        _r("M",  0,  0,  2.5,3.4, obs="RN"),
        _r("M",  0,  6,  2.8,4.8, obs="lactente"),
        _r("M",  1, 12,  3.2,5.0, obs="1-12 anos"),
        _r("M", 12,999,  3.5,5.0, cbaixo=2.0, obs="adulto"),
        _r("F", 12,999,  3.5,5.0, cbaixo=2.0, obs="adulta"),
    ],
    "LDH": [
        _r("M",  0,  0, 300,1500, obs="RN"),
        _r("M",  1, 12, 150, 400, obs="1-12 anos"),
        _r("M", 12,999, 140, 280, calto=600, obs="adulto"),
        _r("F", 12,999, 140, 280, calto=600, obs="adulta"),
    ],

    # ── TIREOIDE ──────────────────────────────────────────────────────────────
    "TSH": [
        _r("M",  0,  0,  1.0,39.0, obs="RN — pico fisiológico"),
        _r("M",  0,  1,  1.7,10.0, obs="1-30 dias"),
        _r("M",  1,  6,  0.8, 8.2, obs="1-6 meses"),
        _r("M",  6, 12,  0.7, 6.0, obs="6m-1 ano"),
        _r("M",  1,  6,  0.6, 5.5, obs="1-6 anos"),
        _r("M",  6, 12,  0.5, 4.5, obs="6-12 anos"),
        _r("M", 12,999,  0.4, 4.0, cbaixo=0.01,calto=20.0, omin=0.5,omax=2.5, obs="adulto"),
        _r("F", 12,999,  0.4, 4.0, cbaixo=0.01,calto=20.0, obs="adulta"),
        _r("F", 18,999,  0.1, 2.5, obs="gestante 1º trimestre", fonte="ATA 2017"),
        _r("F", 18,999,  0.2, 3.0, obs="gestante 2º trimestre"),
        _r("F", 18,999,  0.3, 3.0, obs="gestante 3º trimestre"),
    ],
    "T4 Livre": [
        _r("M",  0,  0,  0.9,2.3, obs="RN"),
        _r("M",  0,  6,  0.7,2.0, obs="lactente"),
        _r("M",  1, 12,  0.7,1.8, obs="1-12 anos"),
        _r("M", 12,999,  0.8,1.8, cbaixo=0.3,calto=4.0, obs="adulto"),
        _r("F", 12,999,  0.8,1.8, cbaixo=0.3,calto=4.0, obs="adulta"),
    ],
    "T3 Total":  [*_am(12,999, 60,200, obs="adolescente/adulto")],
    "Anti-TPO":  [*_am(18,999, None,35, obs="negativo < 35 UI/mL")],

    # ── HORMÔNIOS SEXUAIS ─────────────────────────────────────────────────────
    "Testosterona Total": [
        _r("M",  0,  0,  75, 400, obs="RN — pico fisiológico"),
        _r("M",  0,  6,   5, 150, obs="mini-puberdade"),
        _r("M",  6,  9,   0,  12, obs="pré-puberal"),
        _r("M",  9, 12,   0,  20, obs="9-12 anos"),
        _r("M", 12, 14,  30, 300, obs="início puberdade"),
        _r("M", 14, 18, 200, 800, obs="14-18 anos"),
        _r("M", 18, 50, 300,1000, cbaixo=100,calto=1500, omin=400,omax=800, obs="adulto jovem"),
        _r("M", 50,999, 200, 800, cbaixo=100,calto=1500, obs="adulto > 50 anos"),
        _r("F",  0,  9,   0,   7, obs="pré-puberal"),
        _r("F",  9, 18,   7,  75, obs="puberdade"),
        _r("F", 18,999,  12,  60, obs="adulta"),
        _r("F", 50,999,   8,  40, obs="pós-menopausa"),
    ],
    "Testosterona Livre": [
        _r("M", 18, 50,  9.3,26.5, obs="adulto jovem"),
        _r("M", 50,999,  6.5,18.0, obs="adulto > 50"),
        _r("F", 18,999,  0.3, 1.9, obs="adulta"),
    ],
    "SHBG": [
        _r("M", 18,999, 17,  66, obs="adulto"),
        _r("F", 18,999, 18, 144, obs="adulta"),
        _r("F", 50,999, 40, 120, obs="pós-menopausa"),
    ],
    "Estradiol (E2)": [
        _r("M", 18,999, None, 52.0, obs="homem adulto"),
        _r("F", 18,999, 19.5,144.2, obs="fase folicular"),
        _r("F", 18,999, 63.9,356.7, obs="pico ovulatório"),
        _r("F", 18,999, 55.8,214.2, obs="fase lútea"),
        _r("F", 50,999, None, 32.2, obs="pós-menopausa"),
    ],
    "LH": [
        _r("M", 18,999,  1.5,  9.3, obs="homem adulto"),
        _r("F", 18,999,  1.9, 12.5, obs="fase folicular"),
        _r("F", 18,999,  8.7, 76.3, obs="pico ovulatório"),
        _r("F", 18,999,  0.5, 16.9, obs="fase lútea"),
        _r("F", 50,999, 11.3, 39.8, obs="pós-menopausa"),
    ],
    "FSH": [
        _r("M", 18,999,  1.4, 18.1, obs="homem adulto"),
        _r("F", 18,999,  2.5, 10.2, obs="fase folicular — 3º dia"),
        _r("F", 18,999,  3.4, 33.4, obs="pico ovulatório"),
        _r("F", 18,999,  1.5, 11.0, obs="fase lútea"),
        _r("F", 50,999, 23.0,116.3, obs="pós-menopausa"),
    ],
    "Prolactina": [
        _r("M", 18,999,  2.1, 17.7, obs="homem adulto"),
        _r("F", 18,999,  2.8, 29.2, obs="adulta não grávida"),
        _r("F", 18,999, None,300.0, obs="gestação/lactação"),
    ],
    "PSA Total": [
        _r("M", 18, 49, None, 2.5, omin=0,omax=2.5, obs="< 50 anos"),
        _r("M", 50, 59, None, 3.5, obs="50-59 anos"),
        _r("M", 60, 69, None, 4.5, obs="60-69 anos"),
        _r("M", 70,999, None, 6.5, obs="> 70 anos"),
    ],
    "Cortisol Basal": [
        _r("M", 18,999, 5, 23, cbaixo=3,calto=40, obs="adulto matinal 7h-9h"),
        _r("M", 18,999, 3, 16, obs="adulto vespertino 16h-18h"),
        _r("F", 18,999, 5, 23, cbaixo=3,calto=40, obs="adulta matinal"),
    ],
    "DHEA-S": [
        _r("M", 18, 30, 280,640, obs="18-30 anos"),
        _r("M", 30, 50, 120,520, obs="30-50 anos"),
        _r("M", 50,999,  45,345, obs="> 50 anos"),
        _r("F", 18, 30, 145,395, obs="18-30 anos"),
        _r("F", 30, 50,  65,380, obs="30-50 anos"),
        _r("F", 50,999,  15,200, obs="pós-menopausa"),
    ],

    # ── VITAMINAS E MINERAIS ──────────────────────────────────────────────────
    "Vitamina D (25-OH)": [
        _r("M",  0, 18,  20, 60, obs="criança/adolescente"),
        _r("M", 18,999,  30, 60, omin=40,omax=60,calto=100, obs="adulto — ideal 30-60"),
        _r("M", 60,999,  30, 60, obs="idoso"),
        _r("F",  0, 18,  20, 60, obs="criança/adolescente"),
        _r("F", 18,999,  30, 60, omin=40,omax=60,calto=100, obs="adulta"),
        _r("F", 18,999,  40, 60, obs="gestante"),
    ],
    "Vitamina B12": [
        *_am(18,999, 197,866, cbaixo=100,omin=400,omax=866, obs="adulto"),
    ],
    "Ácido Fólico (Vitamina B9)": [
        *_am(18,999, 3.0,17.0, omin=5.0,omax=17.0, obs="adulto"),
    ],
    "Ferritina": [
        _r("M",  0,  1,  25,200, obs="RN"),
        _r("M",  1,  6,   6, 80, obs="lactente"),
        _r("M",  1, 12,   7, 84, obs="1-12 anos"),
        _r("M", 12, 18,  12,150, obs="12-18 anos"),
        _r("M", 18,999,  30,300, cbaixo=10,calto=1000, omin=100,omax=300, obs="adulto"),
        _r("F", 12, 18,  12, 80, obs="12-18 anos"),
        _r("F", 18, 50,  12,150, cbaixo=10,omin=50,omax=150, obs="adulta pré-menopausa"),
        _r("F", 50,999,  30,300, obs="pós-menopausa"),
    ],
    "Ferro Sérico": [
        _r("M",  0,  0, 100,250, obs="RN"),
        _r("M",  0,  6,  40,100, obs="lactente"),
        _r("M",  1, 12,  50,120, obs="1-12 anos"),
        _r("M", 12,999,  60,160, cbaixo=30,calto=300, obs="adulto"),
        _r("F", 12,999,  50,150, cbaixo=30,calto=300, obs="adulta"),
    ],
    "Magnésio":    [*_am(18,999, 1.6,2.6, cbaixo=1.2,calto=4.0, obs="adulto")],
    "Cálcio Total": [
        _r("M",  0, 10,  8.8,11.2, cbaixo=7.0,calto=14.0, obs="criança"),
        _r("M", 10,999,  8.5,10.5, cbaixo=7.0,calto=14.0, obs="adulto"),
        _r("F", 10,999,  8.5,10.5, cbaixo=7.0,calto=14.0, obs="adulta"),
    ],
    "Fósforo": [
        _r("M",  0,  2,  4.5,8.3, obs="RN/lactente"),
        _r("M",  2, 12,  4.5,6.5, obs="2-12 anos"),
        _r("M", 12, 18,  3.5,5.5, obs="adolescente"),
        _r("M", 18,999,  2.5,4.5, obs="adulto"),
        _r("F", 12, 18,  3.5,5.5, obs="adolescente"),
        _r("F", 18,999,  2.5,4.5, obs="adulta"),
        _r("F", 50,999,  2.8,4.7, obs="pós-menopausa"),
    ],

    # ── MARCADORES CARDÍACOS ──────────────────────────────────────────────────
    "CPK Total":    [
        _r("M", 18,999, 29,168, calto=2000, obs="adulto repouso 72h"),
        _r("F", 18,999, 25,130, calto=2000, obs="adulta repouso"),
    ],
    "CK-MB":        [*_am(18,999, None,24, obs="adulto — < 24 U/L")],
    "Troponina I":  [*_am(18,999, None,0.04, obs="adulto — varia por método")],
    "Homocisteína": [
        _r("M", 18,999, 5.0,15.0, omin=5.0,omax=10.0, obs="adulto — ótimo < 10"),
        _r("F", 18,999, 5.0,12.0, omin=5.0,omax=10.0, obs="adulta"),
    ],

    # ── MARCADORES INFLAMATÓRIOS ──────────────────────────────────────────────
    "PCR (Proteína C-Reativa)": [
        *_am(18,999, None,5.0, omin=0,omax=1.0, obs="adulto — desejável < 1 mg/L"),
    ],
    "PCR": [*_am(18,999, None,5.0, omin=0,omax=1.0, obs="adulto — desejável < 1 mg/L")],
    "PCR (Proteína C Reativa)": [*_am(18,999, None,5.0, omin=0,omax=1.0, obs="adulto")],
    "PCR Ultrassensível": [
        *_am(18,999, None,3.0, omin=0,omax=1.0, obs="adulto — ótimo < 1 mg/L"),
    ],
    "VHS": [
        _r("M", 18, 50, None,15, obs="adulto jovem Westergren"),
        _r("M", 50,999, None,20, obs="adulto > 50"),
        _r("F", 18, 50, None,20, obs="adulta jovem"),
        _r("F", 50,999, None,30, obs="adulta > 50"),
    ],

    # ── ELETRÓLITOS ───────────────────────────────────────────────────────────
    "Sódio":    [*_am(0,999, 136,145, cbaixo=120,calto=160, obs="todas idades")],
    "Potássio": [
        _r("M",  0,  1, 3.5,7.0, cbaixo=2.5,calto=7.0, obs="RN/lactente"),
        _r("M",  1,999, 3.5,5.0, cbaixo=2.5,calto=7.0, obs="criança/adulto"),
        _r("F",  1,999, 3.5,5.0, cbaixo=2.5,calto=7.0, obs="criança/adulta"),
    ],

    # ── COAGULAÇÃO ────────────────────────────────────────────────────────────
    "TP/TAP (%)": [*_am(18,999, 70,100, cbaixo=30, obs="adulto — atividade %")],
    "Tempo de Protrombina (TAP/TP)": [*_am(18,999, 70,100, cbaixo=30, obs="adulto — atividade %")],
    "Atividade de Protrombina": [*_am(18,999, 70,100, cbaixo=30, obs="adulto — atividade %")],
    "Tempo de Protrombina": [*_am(18,999, 11,14, obs="adulto — segundos")],
    "INR":        [*_am(18,999, 0.8,1.2, calto=5.0, obs="sem anticoagulante")],
    "TTPa":       [*_am(18,999, 25,35, obs="adulto — varia por reagente")],
    "D-Dímero": [
        _r("M", 18, 50, None,500, obs="adulto jovem ng/mL FEU"),
        _r("M", 50,999, None,500, obs="ajustar: idade × 10 ng/mL"),
        _r("F", 18, 50, None,500, obs="adulta"),
        _r("F", 18,999, None,1000, obs="gestação"),
    ],

    # ── PÂNCREAS ──────────────────────────────────────────────────────────────
    "Amilase": [*_am(18,999, 25,125, calto=1000, obs="adulto")],
    "Lipase":  [*_am(18,999, 13, 60, calto=1000, obs="adulto")],

    # ── METABOLISMO ÓSSEO ─────────────────────────────────────────────────────
    "PTH (Paratormônio)": [*_am(18,999, 15,65, obs="adulto")],

    # ── MARCADORES TUMORAIS ───────────────────────────────────────────────────
    "PSA Total": [
        _r("M", 18, 49, None,2.5, omin=0,omax=2.5, obs="< 50 anos"),
        _r("M", 50, 59, None,3.5, obs="50-59 anos"),
        _r("M", 60, 69, None,4.5, obs="60-69 anos"),
        _r("M", 70,999, None,6.5, obs="> 70 anos"),
    ],
    "CEA": [
        _r("M", 18,999, None,3.0, obs="não fumante"),
        _r("M", 18,999, None,5.0, obs="fumante"),
        _r("F", 18,999, None,3.0, obs="não fumante"),
        _r("F", 18,999, None,5.0, obs="fumante"),
    ],
    "CA 19-9": [*_am(18,999, None,37, obs="adulto")],
    "AFP":     [*_am(18,999, None, 7.0, obs="adulto não gestante")],
    "CA 125":  [_r("F", 18,999, None,35, obs="adulta")],
}


def _carregar_referencias_expandidas(conn: sqlite3.Connection):
    cur = conn.cursor()
    ok = 0
    nf = 0
    for nome, refs in REFERENCIAS_EXPANDIDAS.items():
        pid = _buscar_padrao_id(cur, nome)
        if not pid:
            # Tenta variantes comuns
            for variante in [nome.upper(), nome.lower()]:
                pid = _buscar_padrao_id(cur, variante)
                if pid:
                    break
        if not pid:
            logging.warning(f"[REFS] exame não encontrado no banco: {nome}")
            nf += 1
            continue
        _inserir_referencias(cur, pid, refs)
        ok += 1

    conn.commit()
    logging.info(f"[REFS] {ok} exames com referências expandidas | {nf} não encontrados")
    return ok


# ══════════════════════════════════════════════════════════════════════════════
# 5. FUNÇÃO PÚBLICA — chamar de qualquer lugar
# ══════════════════════════════════════════════════════════════════════════════

def popular_conhecimento(db_path: str | Path = None) -> dict:
    """
    Carga completa de conhecimento clínico no banco.
    Retorna dict com contagens.
    """
    path = Path(db_path) if db_path else DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row

    try:
        _migrar(conn)
        n_json = _carregar_json_conhecimento(conn)
        n_refs = _carregar_referencias_expandidas(conn)
        logging.info(f"[OK] Conhecimento carregado — JSON:{n_json} REFS:{n_refs}")
        return {"json_exames": n_json, "refs_expandidas": n_refs}
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# 6. EXECUÇÃO DIRETA
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  PRONTUÁRIO — Carga de Conhecimento Clínico")
    print("=" * 60)
    resultado = popular_conhecimento()
    print(f"\n  Exames com conhecimento clínico : {resultado['json_exames']}")
    print(f"  Referências por faixa etária    : {resultado['refs_expandidas']} exames")
    print("\n  Concluído.")
