# -*- coding: utf-8 -*-
"""
grupo_resolver.py
Resolve o grupo_id de um exame ou parâmetro individual.

Lógica:
  1. Se tem exame_padrao_id → pega grupo_id direto de exames_padrao (rápido, sem custo)
  2. Se não tem → tenta mapear pelo campo 'categoria' do extrator (texto livre)
  3. Se não consegue → retorna None (fica pendente para o usuário classificar)

Uso:
    from dados.grupo_resolver import resolver_grupo_parametro, resolver_grupo_exame

    # Para um parâmetro individual:
    gid = resolver_grupo_parametro(conn, exame_padrao_id=45, categoria="Hormônios")

    # Para o exame inteiro (vários parâmetros):
    gid = resolver_grupo_exame(conn, resultados=[...])
"""

import sqlite3
import logging
from typing import Optional

# ══════════════════════════════════════════════════════════════════════════════
# MAPA categoria (texto livre do extrator) → grupo_id
# Cobre as categorias que os extratores Pretti, Cremasco, Tommasi, MedSênior
# e a Claude API costumam retornar.
# ══════════════════════════════════════════════════════════════════════════════

_CATEGORIA_PARA_GRUPO: dict[str, int] = {
    # ── Hematologia (1) ───────────────────────────────────────────────────────
    "hematologia":              1,
    "hemograma":                1,
    "serie vermelha":           1,
    "série vermelha":           1,
    "serie branca":             1,
    "série branca":             1,
    "plaquetas":                1,
    "leucograma":               1,
    "eritrograma":              1,

    # ── Bioquímica Metabólica (2) ─────────────────────────────────────────────
    "glicemia":                 2,
    "glicídico":                2,
    "glicidico":                2,
    "metabolismo glicídico":    2,
    "metabolismo glicidico":    2,
    "lipídios":                 2,
    "lipidios":                 2,
    "lipidico":                 2,
    "lipídico":                 2,
    "colesterol":               2,
    "triglicerídeos":           2,
    "triglicerideos":           2,
    "proteínas":                2,
    "proteinas":                2,
    "bioquímica":               2,
    "bioquimica":               2,
    "bioquímica metabólica":    2,

    # ── Função de Órgãos (3) ──────────────────────────────────────────────────
    "função renal":             3,
    "funcao renal":             3,
    "renal":                    3,
    "função hepática":          3,
    "funcao hepatica":          3,
    "hepático":                 3,
    "hepatico":                 3,
    "hepatica":                 3,
    "função hepática":          3,
    "transaminases":            3,
    "bilirrubinas":             3,
    "colestase":                3,
    "enzimas":                  3,
    "função pancreática":       3,
    "pâncreas":                 3,
    "pancreas":                 3,
    "marcadores cardíacos":     3,
    "marcadores cardiacos":     3,
    "cardíaco":                 3,
    "cardiaco":                 3,
    "enzimas musculares":       3,
    "troponinas":               3,

    # ── Imunidade e Inflamação (4) ────────────────────────────────────────────
    "imunidade":                4,
    "imunologia":               4,
    "inflamação":               4,
    "inflamacao":               4,
    "marcadores inflamatórios": 4,
    "marcadores inflamatorios": 4,
    "sorologia":                4,
    "sorologias":               4,
    "infectologia":             4,
    "autoimunidade":            4,

    # ── Hormônios e Endocrinologia (5) ────────────────────────────────────────
    "hormônios":                5,
    "hormonios":                5,
    "endocrinologia":           5,
    "tireoide":                 5,
    "tireóide":                 5,
    "hormônios tireoidianos":   5,
    "hormonios tireoidianos":   5,
    "hormônios sexuais":        5,
    "hormonios sexuais":        5,
    "hormônios sexuais masculinos": 5,
    "andrógenos":               5,
    "androgenos":               5,
    "estrogênios":              5,
    "estrogenios":              5,
    "gonadotrofinas":           5,
    "hipófise":                 5,
    "hipofise":                 5,
    "hormônios adrenais":       5,
    "hormonios adrenais":       5,
    "adrenal":                  5,
    "cortisol":                 5,
    "suprarrenal":              5,
    "função adrenal":           5,
    "metabolismo ósseo":        5,
    "paratireoide":             5,

    # ── Vitaminas e Micronutrientes (6) ───────────────────────────────────────
    "vitaminas":                6,
    "vitaminas e minerais":     6,
    "micronutrientes":          6,
    "minerais":                 6,
    "ferro":                    6,
    "eletrólitos":              6,
    "eletrolitos":              6,

    # ── Coagulação e Hemostasia (7) ───────────────────────────────────────────
    "coagulação":               7,
    "coagulacao":               7,
    "hemostasia":               7,
    "coagulação e hemostasia":  7,

    # ── Marcadores Tumorais (8) ───────────────────────────────────────────────
    "marcadores tumorais":      8,
    "oncologia":                8,
    "tumor":                    8,

    # ── Urina e Líquidos (9) ──────────────────────────────────────────────────
    "urina":                    9,
    "urinálise":                9,
    "urinalise":                9,
    "líquidos corporais":       9,
    "liquidos corporais":       9,
    "microbiologia":            9,  # culturas de urina

    # ── Imagem ────────────────────────────────────────────────────────────────
    "radiologia":              10,
    "ultrassonografia":        11,
    "ultrassom":               11,
    "doppler":                 11,
    "tomografia":              12,
    "ressonância":             13,
    "ressonancia":             13,
    "medicina nuclear":        14,
    "cintilografia":           14,
    "cardiologia de imagem":   15,
    "ecocardiograma":          15,
    "endoscopia":              16,
    "colonoscopia":            16,

    # ── Outros ────────────────────────────────────────────────────────────────
    "funcionais":              17,
    "eletrocardiograma":       17,
    "mapa":                    17,
    "espirometria":            17,
    "oftalmologia":            17,
    "anatomia patológica":     18,
    "anatomia patologica":     18,
    "histopatológico":         18,
    "histopatologico":         18,
    "anatomopatológico":       18,
    "microbiologia cultura":   19,
    "genética":                20,
    "genetica":                20,
}


def _normalizar(texto: str) -> str:
    return (texto or "").strip().lower()


def resolver_grupo_por_categoria(categoria: str) -> Optional[int]:
    """Mapeia texto livre de categoria para grupo_id. Retorna None se não encontrar."""
    cat = _normalizar(categoria)
    if not cat:
        return None
    # Busca exata
    if cat in _CATEGORIA_PARA_GRUPO:
        return _CATEGORIA_PARA_GRUPO[cat]
    # Busca parcial — verifica se alguma chave está contida na categoria
    for chave, gid in _CATEGORIA_PARA_GRUPO.items():
        if chave in cat or cat in chave:
            return gid
    return None


def resolver_grupo_parametro(
    conn: sqlite3.Connection,
    exame_padrao_id: Optional[int] = None,
    categoria: Optional[str] = None,
    parametro: Optional[str] = None,
) -> Optional[int]:
    """
    Resolve grupo_id para um parâmetro individual.

    Ordem:
      1. exame_padrao_id → exames_padrao.grupo_id  (mais confiável)
      2. categoria (texto livre do extrator)
      3. nome do parâmetro (tenta buscar em exames_padrao por sinônimo)
      4. None
    """
    # 1. Pelo dicionário
    if exame_padrao_id:
        row = conn.execute(
            "SELECT grupo_id FROM exames_padrao WHERE id=?",
            (exame_padrao_id,)
        ).fetchone()
        if row and row[0]:
            return row[0]

    # 2. Pela categoria do extrator
    gid = resolver_grupo_por_categoria(categoria)
    if gid:
        return gid

    # 3. Pelo nome do parâmetro — busca em exames_padrao
    if parametro:
        row = conn.execute("""
            SELECT ep.grupo_id
            FROM exames_padrao ep
            WHERE ep.grupo_id IS NOT NULL
              AND (UPPER(ep.nome_oficial) = UPPER(?)
                   OR UPPER(ep.sinonimos) LIKE UPPER(?))
            LIMIT 1
        """, (parametro, f"%{parametro}%")).fetchone()
        if row and row[0]:
            return row[0]

    return None


def resolver_grupo_exame(
    conn: sqlite3.Connection,
    resultados: list[dict],
    tipo_exame: str = "",
    laboratorio: str = "",
) -> Optional[int]:
    """
    Resolve grupo_id para um exame inteiro com base nos seus parâmetros.

    Lógica: vota pelo grupo mais frequente entre os parâmetros.
    Em caso de empate, usa o grupo do primeiro parâmetro.
    """
    votos: dict[int, int] = {}

    for r in resultados:
        gid = resolver_grupo_parametro(
            conn,
            exame_padrao_id=r.get("exame_padrao_id"),
            categoria=r.get("categoria"),
            parametro=r.get("parametro"),
        )
        if gid:
            votos[gid] = votos.get(gid, 0) + 1

    if not votos:
        # Fallback: tenta pelo tipo_exame ou laboratorio
        gid = resolver_grupo_por_categoria(tipo_exame)
        if not gid:
            gid = resolver_grupo_por_categoria(laboratorio)
        return gid

    # Grupo com mais votos
    return max(votos, key=lambda g: votos[g])


def aplicar_grupos_exame(
    conn: sqlite3.Connection,
    exame_id: int,
    resultados: list[dict],
    tipo_exame: str = "",
    commit: bool = True,
) -> Optional[int]:
    """
    Resolve e grava grupo_id em exames + grupo_id em cada exame_resultados.
    Chamado após salvar os resultados no banco.
    Retorna o grupo_id resolvido (ou None).
    """
    cur = conn.cursor()

    # Resolver grupo para cada resultado individual
    for r in resultados:
        resultado_id = r.get("_resultado_id")  # id do registro em exame_resultados
        if not resultado_id:
            continue
        gid = resolver_grupo_parametro(
            conn,
            exame_padrao_id=r.get("exame_padrao_id"),
            categoria=r.get("categoria"),
            parametro=r.get("parametro"),
        )
        if gid:
            cur.execute(
                "UPDATE exame_resultados SET grupo_id=? WHERE id=?",
                (gid, resultado_id)
            )

    # Resolver grupo predominante para o exame inteiro
    grupo_exame = resolver_grupo_exame(conn, resultados, tipo_exame)
    if grupo_exame:
        cur.execute(
            "UPDATE exames SET grupo_id=? WHERE id=?",
            (grupo_exame, exame_id)
        )
        logging.info(f"[GRUPO] exame_id={exame_id} → grupo_id={grupo_exame}")
    else:
        logging.info(f"[GRUPO] exame_id={exame_id} → sem grupo (ficará pendente)")

    if commit:
        conn.commit()

    return grupo_exame


def retroativo_todos(conn: sqlite3.Connection) -> dict:
    """
    Resolve grupo_id para todos os exames e resultados já no banco sem grupo.
    Chamado uma única vez na migração.
    """
    cur = conn.cursor()
    ok_exames = 0
    ok_resultados = 0

    # ── exame_resultados sem grupo ────────────────────────────────────────────
    rows = cur.execute("""
        SELECT er.id, er.parametro, er.exame_padrao_id, ep.categoria
        FROM exame_resultados er
        LEFT JOIN exames_padrao ep ON ep.id = er.exame_padrao_id
        WHERE er.grupo_id IS NULL
    """).fetchall()

    for rid, parametro, padrao_id, categoria in rows:
        gid = resolver_grupo_parametro(conn, padrao_id, categoria, parametro)
        if gid:
            cur.execute("UPDATE exame_resultados SET grupo_id=? WHERE id=?", (gid, rid))
            ok_resultados += 1

    # ── exames sem grupo ──────────────────────────────────────────────────────
    exames = cur.execute(
        "SELECT id, tipo_exame FROM exames WHERE grupo_id IS NULL"
    ).fetchall()

    for eid, tipo_exame in exames:
        # Busca os resultados desse exame
        resultados = cur.execute("""
            SELECT er.parametro, er.exame_padrao_id, ep.categoria
            FROM exame_resultados er
            LEFT JOIN exames_padrao ep ON ep.id = er.exame_padrao_id
            WHERE er.exame_id = ?
        """, (eid,)).fetchall()

        lista = [
            {"parametro": r[0], "exame_padrao_id": r[1], "categoria": r[2]}
            for r in resultados
        ]
        gid = resolver_grupo_exame(conn, lista, tipo_exame or "")
        if gid:
            cur.execute("UPDATE exames SET grupo_id=? WHERE id=?", (gid, eid))
            ok_exames += 1

    conn.commit()
    logging.info(f"[RETROATIVO] exames:{ok_exames} resultados:{ok_resultados}")
    return {"exames": ok_exames, "resultados": ok_resultados}
