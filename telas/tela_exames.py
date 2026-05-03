# -*- coding: utf-8 -*-
"""
tela_exames.py - Consulta de Exames
VERSAO: 2.0 — aba Medico com fluxo proprio
3 abas:
  1. Buscar   — busca por nome -> seleciona -> resultado
  2. Medico   — seleciona medico -> grid de exames -> seleciona -> resultado
  3. Exames   — lista de PDFs importados -> visualizar / excluir
Resultado (parte inferior, compartilhado entre abas 1 e 2):
  - Numerico -> grafico + tabela
  - Laudo    -> texto
"""

import os
import flet as ft
import sqlite3
import logging as _LOG
_LOG.basicConfig(level=_LOG.INFO)
_LOG.info("[tela_exames] CARREGANDO VERSAO 2.0")
print("[tela_exames] VERSAO 2.0 CARREGADA", flush=True)
from dados.model_prontuario import DB_PATH, listar_especialidades
try:
    from shared.koios_log import klog, kdebug
except ImportError:
    def klog(*a, **k): pass
    def kdebug(*a, **k): pass


# ══════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════

# Paleta Koios (atalhos locais)
BG   = "#0D1117";  CARD = "#161B22";  BD  = "#21262D";  BD2  = "#30363D"
TXT  = "#E6EDF3";  SEC  = "#8B949E";  MUT = "#484F58"
AZUL = "#58A6FF";  VERD = "#3FB950";  LAR = "#F0883E"
VERM = "#DA3633";  ROXO = "#BC8CFF";  AMAR= "#D29922"

CORES_NIVEL = {
    "critico_baixo":    "#FF4444",
    "baixo":            "#F0883E",
    "otimo":            "#3FB950",
    "alto":             "#F0883E",
    "critico_alto":     "#FF4444",
    "sem_referencia":   "#58A6FF",
    "nao_identificado": "#8B949E",
}

LABELS_NIVEL = {
    "critico_baixo":    "Critico v",
    "baixo":            "Baixo v",
    "otimo":            "Otimo OK",
    "alto":             "Alto ^",
    "critico_alto":     "Critico ^",
    "sem_referencia":   "-",
    "nao_identificado": "?",
}

CORES_EXAME = ["#58A6FF", "#3FB950", "#F0883E", "#BC8CFF"]


# ══════════════════════════════════════════════════════════════
# DADOS
# ══════════════════════════════════════════════════════════════

def buscar_todos_exames_padrao() -> list:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur  = conn.cursor()
    cur.execute("""
        SELECT ep.id, ep.nome_oficial, ep.categoria, ep.unidade,
               COUNT(r.id) as qtd_realizados
        FROM exames_padrao ep
        LEFT JOIN resultados_estruturados r ON r.exame_padrao_id = ep.id
        GROUP BY ep.id
        ORDER BY ep.categoria, ep.nome_oficial
    """)
    rows = cur.fetchall()
    tipos = {}
    for row in rows:
        if row[4] > 0:
            cur.execute("""
                SELECT e.tipo FROM exames e
                JOIN resultados_estruturados r ON r.exame_id = e.id
                WHERE r.exame_padrao_id = ? LIMIT 1
            """, (row[0],))
            t = cur.fetchone()
            tipos[row[0]] = t[0] if t else "numerico"
    conn.close()
    return [
        {
            "id":           row[0],
            "nome_oficial": row[1],
            "categoria":    row[2],
            "unidade":      row[3],
            "realizado":    row[4] > 0,
            "qtd":          row[4],
            "tipo":         tipos.get(row[0], "numerico"),
        }
        for row in rows
    ]


def buscar_historico_exame(exame_padrao_id) -> list:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur  = conn.cursor()
    cur.execute("""
        SELECT r.valor, r.unidade, r.referencia, r.nivel_interpretacao,
               e.data_exame, e.laboratorio, e.arquivo_origem, e.drive_file_id
        FROM resultados_estruturados r
        JOIN exames e ON r.exame_id = e.id
        WHERE r.exame_padrao_id = ?
          AND r.valor IS NOT NULL AND r.valor != ''
          AND (r.nivel_interpretacao IS NULL OR r.nivel_interpretacao != 'ignorado')
        ORDER BY e.data_exame ASC
    """, (exame_padrao_id,))
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "valor":       row[0],
            "unidade":     row[1] or "",
            "referencia":  row[2] or "",
            "nivel":       row[3] or "sem_referencia",
            "data":        row[4] or "",
            "laboratorio": row[5] or "",
            "arquivo":     row[6] or "",
            "drive_id":    row[7] or "",
        }
        for row in rows
    ]


def buscar_laudos(filtro: str = "") -> list:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur  = conn.cursor()
    cur.execute("""
        SELECT e.id, e.tipo_exame, e.data_exame, e.laboratorio,
               e.drive_file_id, e.arquivo_origem,
               l.conclusao, l.resumo, l.texto_completo
        FROM exames e
        JOIN laudos l ON l.exame_id = e.id
        WHERE e.tipo IN ('laudo', 'imagem')
        ORDER BY e.data_exame DESC
    """)
    rows = cur.fetchall()
    conn.close()
    resultado = [
        {
            "exame_id":       row[0],
            "tipo_exame":     row[1] or "Laudo",
            "data":           row[2] or "",
            "laboratorio":    row[3] or "",
            "drive_id":       row[4] or "",
            "arquivo":        row[5] or "",
            "conclusao":      row[6] or "",
            "resumo":         row[7] or "",
            "texto_completo": row[8] or "",
        }
        for row in rows
    ]
    if filtro:
        fu = filtro.upper()
        resultado = [
            r for r in resultado
            if fu in r["tipo_exame"].upper()
            or fu in r["conclusao"].upper()
            or fu in r["laboratorio"].upper()
        ]
    return resultado


def buscar_medicos_com_exames() -> list:
    """Retorna medicos que aparecem em exames (via medico_id FK ou medico_solicit texto)."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur  = conn.cursor()
    # Medicos com FK direto
    cur.execute("""
        SELECT m.id, m.nome, m.especialidade, COUNT(DISTINCT ex.id) as total
        FROM medicos m
        JOIN exames ex ON ex.medico_id = m.id
        WHERE ex.status = 'ativo'
        GROUP BY m.id ORDER BY m.nome
    """)
    por_fk = {r[0]: {"id": r[0], "nome": r[1],
                      "especialidade": r[2] or "", "total": r[3]}
              for r in cur.fetchall()}

    # Medicos referenciados por medico_solicit (nome no texto)
    cur.execute("SELECT id, nome, especialidade FROM medicos ORDER BY nome")
    todos_medicos = cur.fetchall()
    for med_id, nome, espec in todos_medicos:
        if med_id in por_fk:
            continue
        cur.execute("""
            SELECT COUNT(*) FROM exames
            WHERE UPPER(medico_solicit) LIKE UPPER(?)
              AND (status = 'ativo' OR status IS NULL)
        """, (f"%{nome}%",))
        qtd = cur.fetchone()[0]
        if qtd > 0:
            por_fk[med_id] = {"id": med_id, "nome": nome,
                               "especialidade": espec or "", "total": qtd}

    # Exames sem medico vinculado
    cur.execute("""
        SELECT COUNT(*) FROM exames
        WHERE medico_id IS NULL
          AND (medico_solicit IS NULL OR medico_solicit = '')
          AND (status = 'ativo' OR status IS NULL)
    """)
    sem = cur.fetchone()[0]
    conn.close()
    resultado = list(por_fk.values())
    resultado.sort(key=lambda x: x["nome"])
    if sem:
        resultado.append({"id": None, "nome": "Sem medico vinculado",
                          "especialidade": "", "total": sem})
    return resultado


def buscar_exames_do_medico(medico_id, nome_medico="") -> list:
    """Busca exames por medico_id (FK) OU por medico_solicit (texto do PDF)."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur  = conn.cursor()
    if medico_id is None or medico_id == "sem_medico":
        cur.execute("""
            SELECT e.id, e.tipo_exame, e.tipo, e.data_exame,
                   e.laboratorio, e.arquivo_origem, e.drive_file_id
            FROM exames e
            WHERE e.medico_id IS NULL
              AND (e.medico_solicit IS NULL OR e.medico_solicit = '')
              AND (e.status = 'ativo' OR e.status IS NULL)
            ORDER BY e.data_exame DESC
        """)
    elif isinstance(medico_id, str) and str(medico_id).startswith("_sol_"):
        # Médico só existe em medico_solicit — busca só pelo nome
        cur.execute("""
            SELECT e.id, e.tipo_exame, e.tipo, e.data_exame,
                   e.laboratorio, e.arquivo_origem, e.drive_file_id
            FROM exames e
            WHERE UPPER(TRIM(e.medico_solicit)) LIKE UPPER(TRIM(?))
            ORDER BY e.data_exame DESC
        """, (f"%{nome_medico}%",))
    else:
        cur.execute("""
            SELECT e.id, e.tipo_exame, e.tipo, e.data_exame,
                   e.laboratorio, e.arquivo_origem, e.drive_file_id
            FROM exames e
            WHERE (e.medico_id = ?
                   OR (? != '' AND UPPER(e.medico_solicit) LIKE UPPER(?)))
              AND (e.status = 'ativo' OR e.status IS NULL)
            ORDER BY e.data_exame DESC
        """, (medico_id, nome_medico, f"%{nome_medico}%"))
    rows = cur.fetchall()
    resultado = []
    for row in rows:
        exame_id, tipo_exame, tipo, data, lab, arquivo, drive_id = row
        if tipo == "numerico":
            cur.execute("""
                SELECT DISTINCT ep.id, ep.nome_oficial, ep.categoria, ep.unidade
                FROM resultados_estruturados r
                JOIN exames_padrao ep ON ep.id = r.exame_padrao_id
                WHERE r.exame_id = ?
            """, (exame_id,))
            padraos = cur.fetchall()
            for ep in padraos:
                resultado.append({
                    "id":           ep[0],
                    "exame_db_id":  exame_id,
                    "nome_oficial": ep[1],
                    "categoria":    ep[2] or "",
                    "unidade":      ep[3] or "",
                    "tipo":         "numerico",
                    "data":         data or "",
                    "laboratorio":  lab or "",
                    "arquivo":      arquivo or "",
                    "drive_id":     drive_id or "",
                    "realizado":    True,
                    "qtd":          1,
                })
        else:
            resultado.append({
                "id":           "laudo_" + str(exame_id),
                "exame_db_id":  exame_id,
                "nome_oficial": tipo_exame or "Laudo",
                "categoria":    "Laudo",
                "unidade":      "",
                "tipo":         tipo or "laudo",
                "data":         data or "",
                "laboratorio":  lab or "",
                "arquivo":      arquivo or "",
                "drive_id":     drive_id or "",
                "realizado":    True,
                "qtd":          1,
            })
    conn.close()
    return resultado


def buscar_todos_exames_fisicos() -> list:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur  = conn.cursor()
    cur.execute("""
        SELECT e.id, e.tipo, e.tipo_exame, e.data_exame,
               e.laboratorio, e.arquivo_origem, e.drive_file_id,
               m.nome as medico_nome, e.status
        FROM exames e
        LEFT JOIN medicos m ON m.id = e.medico_id
        ORDER BY e.data_exame DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id":          row[0],
            "tipo":        row[1] or "numerico",
            "tipo_exame":  row[2] or "",
            "data":        row[3] or "",
            "laboratorio": row[4] or "",
            "arquivo":     row[5] or "",
            "drive_id":    row[6] or "",
            "medico":      row[7] or "Sem medico",
            "status":      row[8] or "ativo",
        }
        for row in rows
    ]


def excluir_exame_fisico(exame_id: int) -> str:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur  = conn.cursor()
    cur.execute("SELECT arquivo_origem FROM exames WHERE id = ?", (exame_id,))
    row = cur.fetchone()
    arquivo = row[0] if row else None
    cur.execute("DELETE FROM resultados_estruturados WHERE exame_id = ?", (exame_id,))
    cur.execute("DELETE FROM laudos WHERE exame_id = ?", (exame_id,))
    cur.execute("DELETE FROM exames WHERE id = ?", (exame_id,))
    conn.commit()
    conn.close()
    return arquivo or ""


def buscar_especialidades_com_exames() -> list:
    """Retorna especialidades que possuem exames realizados."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur  = conn.cursor()
    cur.execute("""
        SELECT COALESCE(esp.nome, m.especialidade) as nome,
               COUNT(DISTINCT ex.id) as total
        FROM exames ex
        JOIN medicos m ON m.id = ex.medico_id
        LEFT JOIN especialidades esp ON esp.id = m.especialidade_id
        WHERE (ex.status = 'ativo' OR ex.status IS NULL)
          AND COALESCE(esp.nome, m.especialidade) IS NOT NULL
          AND COALESCE(esp.nome, m.especialidade) != ''
        GROUP BY COALESCE(esp.nome, m.especialidade)
        ORDER BY COALESCE(esp.nome, m.especialidade)
    """)
    rows = cur.fetchall()
    conn.close()
    return [{"nome": r[0], "total": r[1]} for r in rows if r[1] > 0]


def buscar_exames_da_especialidade(nome_especialidade: str) -> list:
    """Busca exames de todos os médicos de uma especialidade (por nome)."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur  = conn.cursor()
    cur.execute("""
        SELECT DISTINCT e.id, e.tipo_exame, e.tipo, e.data_exame,
               e.laboratorio, e.arquivo_origem, e.drive_file_id
        FROM exames e
        JOIN medicos m ON m.id = e.medico_id
        LEFT JOIN especialidades esp ON esp.id = m.especialidade_id
        WHERE UPPER(COALESCE(esp.nome, m.especialidade)) = UPPER(?)
          AND (e.status = 'ativo' OR e.status IS NULL)
        ORDER BY e.data_exame DESC
    """, (nome_especialidade,))
    rows = cur.fetchall()
    resultado = []
    seen_ids  = set()
    for row in rows:
        exame_id, tipo_exame, tipo, data, lab, arquivo, drive_id = row
        if tipo == "numerico":
            cur.execute("""
                SELECT DISTINCT ep.id, ep.nome_oficial, ep.categoria, ep.unidade
                FROM resultados_estruturados r
                JOIN exames_padrao ep ON ep.id = r.exame_padrao_id
                WHERE r.exame_id = ?
            """, (exame_id,))
            for ep in cur.fetchall():
                if ep[0] not in seen_ids:
                    seen_ids.add(ep[0])
                    resultado.append({
                        "id": ep[0], "exame_db_id": exame_id,
                        "nome_oficial": ep[1], "categoria": ep[2] or "",
                        "unidade": ep[3] or "", "tipo": "numerico",
                        "data": data or "", "laboratorio": lab or "",
                        "arquivo": arquivo or "", "drive_id": drive_id or "",
                        "realizado": True, "qtd": 1,
                    })
        else:
            key = "laudo_" + str(exame_id)
            if key not in seen_ids:
                seen_ids.add(key)
                resultado.append({
                    "id": key, "exame_db_id": exame_id,
                    "nome_oficial": tipo_exame or "Laudo", "categoria": "Laudo",
                    "unidade": "", "tipo": tipo or "laudo",
                    "data": data or "", "laboratorio": lab or "",
                    "arquivo": arquivo or "", "drive_id": drive_id or "",
                    "realizado": True, "qtd": 1,
                })
    conn.close()
    return resultado


def buscar_categorias_com_exames() -> list:
    """Retorna categorias de exames_padrao com ao menos um resultado realizado."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur  = conn.cursor()
    cur.execute("""
        SELECT ep.categoria, COUNT(DISTINCT ep.id) as total
        FROM resultados_estruturados r
        JOIN exames_padrao ep ON ep.id = r.exame_padrao_id
        WHERE ep.categoria IS NOT NULL AND ep.categoria != ''
        GROUP BY ep.categoria
        ORDER BY ep.categoria
    """)
    rows = cur.fetchall()
    conn.close()
    return [{"categoria": r[0], "total": r[1]} for r in rows]


def buscar_exames_da_categoria(categoria: str) -> list:
    """Retorna exames_padrao realizados de uma categoria específica."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur  = conn.cursor()
    cur.execute("""
        SELECT ep.id, ep.nome_oficial, ep.categoria, ep.unidade,
               COUNT(r.id) as qtd
        FROM exames_padrao ep
        JOIN resultados_estruturados r ON r.exame_padrao_id = ep.id
        WHERE ep.categoria = ?
        GROUP BY ep.id
        ORDER BY ep.nome_oficial
    """, (categoria,))
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "nome_oficial": r[1], "categoria": r[2] or "",
            "unidade": r[3] or "", "tipo": "numerico",
            "realizado": True, "qtd": r[4],
        }
        for r in rows
    ]


def buscar_todas_categorias() -> list:
    """Todas as categorias de exames_padrao com contagem de realizados (0 se nenhum)."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur  = conn.cursor()
    cur.execute("""
        SELECT ep.categoria,
               COUNT(DISTINCT ep.id) as total_padrao,
               COUNT(DISTINCT r.id)  as realizados
        FROM exames_padrao ep
        LEFT JOIN resultados_estruturados r ON r.exame_padrao_id = ep.id
        WHERE ep.categoria IS NOT NULL AND ep.categoria != ''
        GROUP BY ep.categoria
        ORDER BY ep.categoria
    """)
    rows = cur.fetchall()
    conn.close()
    return [{"categoria": r[0], "total": r[1], "realizados": r[2]} for r in rows]


def _valor_float(v: str):
    try:
        return float(v.replace(",", ".").strip())
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
# RENDERIZADORES
# ══════════════════════════════════════════════════════════════

def _parse_referencia(ref_str: str):
    """Extrai (min, max) de strings como '22,0 - 280,0' ou '< 5' ou '> 10'."""
    import re
    if not ref_str:
        return None, None
    ref_str = ref_str.replace(",", ".").strip()
    # Formato: 22.0 - 280.0  ou  22.0 a 280.0
    m = re.search(r"([\d.]+)\s*(?:-|a)\s*([\d.]+)", ref_str)
    if m:
        return float(m.group(1)), float(m.group(2))
    # Formato: < 5.0
    m = re.search(r"<\s*([\d.]+)", ref_str)
    if m:
        return None, float(m.group(1))
    # Formato: > 10.0
    m = re.search(r">\s*([\d.]+)", ref_str)
    if m:
        return float(m.group(1)), None
    return None, None


def _gerar_grafico_flet(historicos: list) -> ft.Control:
    """Grafico nativo Flet — sem dependencias externas, funciona no Android."""
    from datetime import datetime

    CORES_EX = ["#58A6FF", "#3FB950", "#F0883E", "#BC8CFF", "#D29922"]
    NIVEL_COR = {
        "critico_baixo": "#FF4444", "baixo": "#F0883E",
        "otimo": "#3FB950",         "alto":  "#F0883E",
        "critico_alto": "#FF4444",
    }

    def _pd(d):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime((d or "")[:10], fmt)
            except Exception:
                pass
        return None

    # Preparar series
    series = []
    for idx, (ex, hist) in enumerate(historicos):
        ent = sorted(
            [h for h in hist
             if _valor_float(h.get("valor")) is not None
             and h.get("data") and _pd(h["data"])],
            key=lambda h: _pd(h["data"]),
        )
        if not ent:
            continue
        ref_min = ref_max = None
        for h in ent:
            rm, rx = _parse_referencia(h.get("referencia", ""))
            if rm is not None or rx is not None:
                ref_min, ref_max = rm, rx
                break
        series.append({
            "ex": ex, "ent": ent,
            "cor": CORES_EX[idx % len(CORES_EX)],
            "ref_min": ref_min, "ref_max": ref_max,
            "uni": ex.get("unidade") or (ent[0].get("unidade") if ent else "") or "",
            "nome": ex.get("nome_oficial", ""),
        })

    if not series:
        return ft.Text("Sem valores numericos.", size=12, color="#484F58")

    # Eixo X: todas as datas ordenadas
    todas_datas = sorted({
        _pd(h["data"])
        for s in series for h in s["ent"] if _pd(h["data"])
    })
    if not todas_datas:
        return ft.Text("Sem datas validas.", size=12, color="#484F58")

    didx = {d: i for i, d in enumerate(todas_datas)}

    # Escala Y global (inclui limites de referencia)
    todos_ys = [
        _valor_float(h["valor"])
        for s in series for h in s["ent"]
        if _valor_float(h["valor"]) is not None
    ]
    y_min = min(todos_ys) if todos_ys else 0.0
    y_max = max(todos_ys) if todos_ys else 100.0
    for s in series:
        if s["ref_min"] is not None:
            y_min = min(y_min, s["ref_min"])
        if s["ref_max"] is not None:
            y_max = max(y_max, s["ref_max"])
    y_pad = max((y_max - y_min) * 0.18, 1.0)

    # Construir series do grafico
    chart_series = []
    for s in series:
        points = []
        for h in s["ent"]:
            d = _pd(h["data"])
            v = _valor_float(h["valor"])
            if d is None or v is None:
                continue
            nivel = h.get("nivel", "")
            cor_pt = NIVEL_COR.get(nivel, s["cor"])
            uni_str = h.get("unidade") or s["uni"]
            data_str = (h.get("data") or "")[:10]
            points.append(ft.LineChartDataPoint(
                x=float(didx[d]),
                y=float(v),
                tooltip=f"{h.get('valor','')} {uni_str}\n{data_str}",
                point=ft.ChartCirclePoint(radius=5, color=cor_pt,
                                          stroke_color="#0D1117", stroke_width=1.5),
                selected_point=ft.ChartCirclePoint(radius=7, color=cor_pt,
                                                   stroke_color="#0D1117", stroke_width=2),
            ))

        if not points:
            continue

        chart_series.append(ft.LineChartData(
            data_points=points,
            color=s["cor"],
            stroke_width=2.4,
            curved=False,
            stroke_cap_round=True,
        ))

        # Linhas de referencia (tracejadas) como serie separada
        if s["ref_min"] is not None and s["ref_max"] is not None:
            n = float(len(todas_datas) - 1)
            for ref_y, suffix in [(s["ref_min"], "min"), (s["ref_max"], "max")]:
                chart_series.append(ft.LineChartData(
                    data_points=[
                        ft.LineChartDataPoint(x=0.0, y=float(ref_y)),
                        ft.LineChartDataPoint(x=n,   y=float(ref_y)),
                    ],
                    color=s["cor"] + "55",
                    stroke_width=1.0,
                    dash_pattern=[5, 5],
                    curved=False,
                ))

    if not chart_series:
        return ft.Text("Sem pontos para exibir.", size=12, color="#484F58")

    # Rotulos do eixo X
    x_labels = [
        ft.ChartAxisLabel(
            value=float(i),
            label=ft.Container(
                content=ft.Text(d.strftime("%d/%m"), size=9, color="#8B949E"),
                padding=ft.padding.only(top=4),
            ),
        )
        for i, d in enumerate(todas_datas)
    ]

    chart = ft.LineChart(
        data_series=chart_series,
        bgcolor="#161B22",
        tooltip_bgcolor="#161B22",
        tooltip_rounded_radius=6,
        border=ft.Border(
            bottom=ft.BorderSide(1, "#21262D"),
            left=ft.BorderSide(1, "#21262D"),
        ),
        horizontal_grid_lines=ft.ChartGridLines(
            color="#21262D", width=0.5, dash_pattern=[4, 4],
        ),
        vertical_grid_lines=ft.ChartGridLines(color="#00000000"),
        left_axis=ft.ChartAxis(labels_size=44, show_labels=True),
        bottom_axis=ft.ChartAxis(labels=x_labels, labels_size=30),
        min_y=y_min - y_pad,
        max_y=y_max + y_pad,
        min_x=-0.3,
        max_x=float(len(todas_datas) - 1) + 0.3,
        expand=True,
        interactive=True,
    )

    return ft.Container(
        content=chart,
        height=260,
        bgcolor="#161B22",
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=4, vertical=8),
        border=ft.border.all(1, "#21262D"),
    )


def renderizar_grafico_combinado(page: ft.Page, exames_selecionados: list) -> ft.Control:
    """
    Gráfico único com chips de legenda clicáveis.
    Clicar num chip → tela de detalhe com todos os resultados + PDF.
    Tela de detalhe tem botão Voltar → volta ao gráfico.
    """
    import webbrowser, logging

    historicos = [(ex, ex.get("historico", []))
                  for ex in exames_selecionados if ex.get("historico")]
    if not historicos:
        return ft.Text("Nenhum dado para exibir.", size=12, color="#484F58")

    CORES_EX = ["#58A6FF", "#3FB950", "#F0883E", "#BC8CFF", "#D29922"]
    NIVEL_COR = {
        "critico_baixo": "#FF4444", "baixo": "#F0883E",
        "otimo": "#3FB950",         "alto":  "#F0883E",
        "critico_alto": "#FF4444",  "sem_referencia": "#58A6FF",
        "nao_identificado": "#8B949E",
    }
    NIVEL_LABEL = {
        "critico_baixo": "Critico v", "baixo": "Baixo v",
        "otimo": "Otimo ok",          "alto":  "Alto ^",
        "critico_alto": "Critico ^",  "sem_referencia": "—",
        "nao_identificado": "?",
    }

    grafico_ctrl = _gerar_grafico_flet(historicos)

    # Chips de legenda clicáveis (um por exame)
    def _fazer_chip(idx, ex, hist):
        cor  = CORES_EX[idx % len(CORES_EX)]
        nome = ex.get("nome_oficial", "")
        uni  = ex.get("unidade", "")

        def _abrir(e, _ex=ex, _hist=hist, _cor=cor):
            _mostrar_detalhe(_ex, _hist, _cor)

        return ft.Container(
            content=ft.Row([
                ft.Container(width=10, height=10, bgcolor=cor,
                             border_radius=2),
                ft.Text(nome, size=11, color="#E6EDF3",
                        weight=ft.FontWeight.W_500),
                ft.Text(f"[{uni}]" if uni else "", size=9, color="#484F58"),
                ft.Icon("chevron_right_rounded", size=12, color=cor),
            ], spacing=5, tight=True),
            bgcolor="#161B22", border_radius=16,
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            border=ft.Border(
                top=ft.BorderSide(1, cor + "66"),
                bottom=ft.BorderSide(1, cor + "66"),
                left=ft.BorderSide(2, cor),
                right=ft.BorderSide(1, cor + "66"),
            ),
            on_click=_abrir, ink=True,
        )

    chips_legenda = ft.Row(
        controls=[_fazer_chip(i, ex, hist)
                  for i, (ex, hist) in enumerate(historicos)],
        spacing=8, wrap=True,
    )

    vista_grafico = ft.Column([
        grafico_ctrl,
        ft.Container(
            content=ft.Column([
                ft.Text("Clique num exame para ver os detalhes:",
                        size=10, color="#484F58"),
                chips_legenda,
            ], spacing=6),
            padding=ft.padding.symmetric(horizontal=4, vertical=6),
        ),
    ], spacing=6, visible=True)

    # ── Vista B: Detalhe de um exame ──────────────────────────────────────────
    detalhe_col = ft.Column(spacing=10, visible=False)

    def _mostrar_detalhe(ex, hist, cor):
        nome    = ex.get("nome_oficial", "")
        unidade = ex.get("unidade", "")

        # Filtrar entradas válidas, ordenar por data
        from datetime import datetime
        def _pd(d):
            for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                try: return datetime.strptime((d or "")[:10], fmt)
                except: pass
            return datetime.min

        entradas = sorted(
            [h for h in hist if h.get("valor") and h.get("data")],
            key=lambda h: _pd(h["data"]),
            reverse=True,  # mais recente primeiro
        )

        detalhe_col.controls.clear()

        # Cabeçalho com voltar
        btn_voltar = ft.Container(
            content=ft.Row([
                ft.Icon("arrow_back_rounded", size=14, color="#8B949E"),
                ft.Text("Voltar ao gráfico", size=12, color="#8B949E"),
            ], spacing=6, tight=True),
            on_click=lambda e: _voltar_grafico(),
            ink=True, border_radius=6,
            padding=ft.padding.symmetric(horizontal=8, vertical=6),
        )

        detalhe_col.controls.append(ft.Row([
            btn_voltar,
            ft.Row([
                ft.Container(width=3, height=16, bgcolor=cor, border_radius=2),
                ft.Container(width=6),
                ft.Text(nome, size=14, color="#E6EDF3",
                        weight=ft.FontWeight.W_700),
                ft.Text(f"[{unidade}]" if unidade else "",
                        size=11, color="#484F58"),
            ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

        detalhe_col.controls.append(
            ft.Text(f"{len(entradas)} resultado(s) — mais recente primeiro",
                    size=10, color="#484F58"))

        # Card por resultado
        for h in entradas:
            nivel  = h.get("nivel", "sem_referencia")
            cor_n  = NIVEL_COR.get(nivel, "#58A6FF")
            label  = NIVEL_LABEL.get(nivel, "?")
            uni    = h.get("unidade") or unidade
            ref    = h.get("referencia") or "—"
            lab    = h.get("laboratorio") or ""
            data   = (h.get("data") or "")[:10]
            valor  = h.get("valor") or ""
            did    = h.get("drive_id") or ""

            btn_pdf = ft.Container(
                content=ft.Row([
                    ft.Icon("picture_as_pdf_rounded", size=13, color="#FF4444"),
                    ft.Text("Ver PDF", size=11, color="#58A6FF"),
                ], spacing=4, tight=True),
                bgcolor="#0D1117", border_radius=6,
                padding=ft.padding.symmetric(horizontal=8, vertical=5),
                border=ft.Border(
                    top=ft.BorderSide(1, "#30363D"),
                    bottom=ft.BorderSide(1, "#30363D"),
                    left=ft.BorderSide(1, "#30363D"),
                    right=ft.BorderSide(1, "#30363D"),
                ),
                ink=True, visible=bool(did),
            )
            if did:
                btn_pdf.on_click = lambda e, d=did: webbrowser.open(
                    f"https://drive.google.com/file/d/{d}/view")

            detalhe_col.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(data, size=11, color="#8B949E"),
                        ft.Container(expand=True),
                        btn_pdf,
                    ]),
                    ft.Container(height=6),
                    ft.Row([
                        ft.Column([
                            ft.Text("Valor", size=9, color="#484F58"),
                            ft.Row([
                                ft.Text(str(valor), size=22, color=cor_n,
                                        weight=ft.FontWeight.W_700),
                                ft.Text(uni, size=11, color="#484F58"),
                            ], spacing=4,
                               vertical_alignment=ft.CrossAxisAlignment.END),
                        ], spacing=1),
                        ft.VerticalDivider(color="#21262D", width=24),
                        ft.Column([
                            ft.Text("Referência", size=9, color="#484F58"),
                            ft.Text(ref, size=11, color="#8B949E"),
                        ], spacing=1),
                        ft.VerticalDivider(color="#21262D", width=24),
                        ft.Column([
                            ft.Text("Nível", size=9, color="#484F58"),
                            ft.Text(label, size=12, color=cor_n,
                                    weight=ft.FontWeight.W_600),
                        ], spacing=1),
                    ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(height=4),
                    ft.Text(lab, size=9, color="#58A6FF"),
                ], spacing=0),
                bgcolor="#161B22", border_radius=8,
                padding=ft.padding.all(14),
                border=ft.Border(
                    left=ft.BorderSide(3, cor_n),
                    top=ft.BorderSide(1, "#21262D"),
                    bottom=ft.BorderSide(1, "#21262D"),
                    right=ft.BorderSide(1, "#21262D"),
                ),
            ))

        vista_grafico.visible = False
        detalhe_col.visible   = True
        try: page.update()
        except Exception: pass

    def _voltar_grafico():
        detalhe_col.visible   = False
        vista_grafico.visible = True
        try: page.update()
        except Exception: pass

    return ft.Column([vista_grafico, detalhe_col], spacing=0)


def renderizar_tabela_exame(page: ft.Page, exame: dict) -> ft.Control:
    hist = exame.get("historico", [])
    if not hist:
        return ft.Text("Sem historico.", size=12, color="#484F58")

    cabecalho = ft.Row([
        ft.Container(ft.Text("Data",       size=11, color="#484F58", weight=ft.FontWeight.W_600), expand=2),
        ft.Container(ft.Text("Valor",      size=11, color="#484F58", weight=ft.FontWeight.W_600), expand=2),
        ft.Container(ft.Text("Referencia", size=11, color="#484F58", weight=ft.FontWeight.W_600), expand=3),
        ft.Container(ft.Text("Nivel",      size=11, color="#484F58", weight=ft.FontWeight.W_600), expand=2),
    ], spacing=4)

    linhas = [cabecalho, ft.Divider(color="#21262D", height=4)]
    for h in hist:
        nivel = h.get("nivel", "sem_referencia")
        cor   = CORES_NIVEL.get(nivel, "#8B949E")
        label = LABELS_NIVEL.get(nivel, "?")
        linhas.append(ft.Row([
            ft.Container(ft.Text(h["data"][:10] if h["data"] else "?",
                                 size=11, color="#8B949E"), expand=2),
            ft.Container(ft.Text(f"{h['valor']} {h['unidade']}",
                                 size=12, color=cor,
                                 weight=ft.FontWeight.W_600), expand=2),
            ft.Container(ft.Text(h.get("referencia") or "-",
                                 size=11, color="#484F58"), expand=3),
            ft.Container(ft.Text(label, size=11, color=cor), expand=2),
        ], spacing=4))

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text(exame["nome_oficial"], size=13, color="#E6EDF3",
                        weight=ft.FontWeight.W_600),
                ft.Text(exame.get("unidade", ""), size=11, color="#484F58"),
            ], spacing=6),
            ft.Container(height=4),
            *linhas,
        ], spacing=3),
        bgcolor="#161B22", border_radius=8, padding=12,
        border=ft.Border(
            top=ft.BorderSide(1, "#21262D"), bottom=ft.BorderSide(1, "#21262D"),
            left=ft.BorderSide(2, CORES_EXAME[0]),
            right=ft.BorderSide(1, "#21262D"),
        ),
    )


def renderizar_card_laudo(page: ft.Page, laudo: dict) -> ft.Control:
    import webbrowser
    expandido = [False]

    texto_container = ft.Container(
        content=ft.Column([
            ft.Text("Resumo / Macroscopia:", size=11, color="#484F58",
                    weight=ft.FontWeight.W_600),
            ft.Text(laudo.get("resumo") or "-", size=12, color="#8B949E",
                    selectable=True),
            ft.Divider(color="#21262D", height=8),
            ft.Text("Conclusao / Diagnostico:", size=11, color="#484F58",
                    weight=ft.FontWeight.W_600),
            ft.Text(laudo.get("conclusao") or "-", size=13, color="#E6EDF3",
                    weight=ft.FontWeight.W_600, selectable=True),
        ], spacing=6),
        bgcolor="#0D1117", border_radius=8, padding=12,
        border=ft.Border(
            top=ft.BorderSide(1, "#21262D"), bottom=ft.BorderSide(1, "#21262D"),
            left=ft.BorderSide(1, "#21262D"), right=ft.BorderSide(1, "#21262D"),
        ),
        visible=False,
    )

    icone_exp = ft.Icon("expand_more_rounded", size=16, color="#8B949E")

    def toggle(e):
        expandido[0] = not expandido[0]
        texto_container.visible = expandido[0]
        icone_exp.name = "expand_less_rounded" if expandido[0] else "expand_more_rounded"
        try: page.update()
        except Exception: pass

    cabecalho = ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Icon("description_rounded", size=16, color="#BC8CFF"),
                bgcolor="#BC8CFF22", border_radius=6,
                width=32, height=32, alignment=ft.alignment.Alignment(0, 0),
            ),
            ft.Column([
                ft.Text(laudo.get("tipo_exame", "Laudo"), size=13, color="#E6EDF3",
                        weight=ft.FontWeight.W_600),
                ft.Row([
                    ft.Text(laudo["data"][:10] if laudo.get("data") else "?",
                            size=11, color="#8B949E"),
                    ft.Text("-", size=11, color="#484F58"),
                    ft.Text(laudo.get("laboratorio", ""), size=11, color="#58A6FF"),
                ], spacing=4),
            ], spacing=2, expand=True),
            ft.Container(
                content=ft.Row([
                    ft.Icon("picture_as_pdf_rounded", size=13, color="#FF7B7B"),
                    ft.Text("PDF", size=10, color="#58A6FF"),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                ink=True,
                on_click=lambda e: webbrowser.open(
                    "https://drive.google.com/file/d/" + laudo["drive_id"] + "/view"
                ),
            ) if laudo.get("drive_id") else ft.Container(),
            icone_exp,
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        bgcolor="#161B22", border_radius=8, on_click=toggle, ink=True,
        border=ft.Border(
            top=ft.BorderSide(1, "#21262D"), bottom=ft.BorderSide(1, "#21262D"),
            left=ft.BorderSide(2, "#BC8CFF"), right=ft.BorderSide(1, "#21262D"),
        ),
    )
    return ft.Column([cabecalho, texto_container], spacing=2)



# ══════════════════════════════════════════════════════════════
# AREA DE RESULTADO
# ══════════════════════════════════════════════════════════════

def criar_area_resultado(page: ft.Page):
    import threading, logging as _lg

    # ── Spinner ───────────────────────────────────────────────────────────
    _spinner = ft.Container(
        content=ft.Row([
            ft.ProgressRing(width=20, height=20, stroke_width=2,
                            color="#58A6FF"),
            ft.Column([
                ft.Text("Gerando gráfico...", size=13, color="#E6EDF3",
                        weight=ft.FontWeight.W_500),
                ft.Text("Aguarde um momento", size=11, color="#8B949E"),
            ], spacing=2),
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor="#161B22",
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=16, vertical=14),
        border=ft.Border(
            top=ft.BorderSide(1, "#21262D"), bottom=ft.BorderSide(1, "#21262D"),
            left=ft.BorderSide(3, "#58A6FF"), right=ft.BorderSide(1, "#21262D"),
        ),
        visible=False,
    )

    col_resultado = ft.Column([_spinner], spacing=10, visible=False)
    _subscribed   = [False]

    def fn_limpar():
        _spinner.visible = False
        col_resultado.controls.clear()
        col_resultado.controls.append(_spinner)
        col_resultado.visible = False
        try: page.update()
        except Exception: pass

    def fn_renderizar(selecionados: list):
        if not selecionados:
            fn_limpar()
            return

        # Mostra spinner imediatamente
        _spinner.visible = True
        col_resultado.controls.clear()
        col_resultado.controls.append(_spinner)
        col_resultado.visible = True
        try: page.update()
        except Exception: pass

        _sel = list(selecionados)

        def _montar():
            """Roda em thread — monta controles sem tocar na UI."""
            numericos = [s for s in _sel if s.get("tipo") == "numerico"]
            laudos    = [s for s in _sel if s.get("tipo") not in ("numerico",)]
            controles = []
            if numericos:
                try:
                    # Um único gráfico com todas as linhas
                    controles.append(renderizar_grafico_combinado(page, numericos))
                except Exception as ex:
                    _lg.error(f"[RENDER] grafico: {ex}")
                    controles.append(
                        ft.Text(f"Gráfico indisponível: {ex}",
                                size=11, color="#F0883E"))
            for laudo in laudos:
                try:
                    controles.append(renderizar_card_laudo(page, laudo))
                except Exception as ex:
                    _lg.error(f"[RENDER] laudo: {ex}")
            page.pubsub.send_all({"_tipo": "grafico_pronto", "controles": controles})

        def _on_msg(msg):
            if not isinstance(msg, dict): return
            if msg.get("_tipo") != "grafico_pronto": return
            _spinner.visible = False
            col_resultado.controls.clear()
            for c in msg["controles"]:
                col_resultado.controls.append(c)
            col_resultado.visible = True
            try: page.update()
            except Exception: pass

        if not _subscribed[0]:
            page.pubsub.subscribe(_on_msg)
            _subscribed[0] = True

        threading.Thread(target=_montar, daemon=True).start()

    return col_resultado, fn_renderizar, fn_limpar


# ══════════════════════════════════════════════════════════════
# GESTOR DE SELECAO
# ══════════════════════════════════════════════════════════════

def criar_gestor_selecao(page: ft.Page, fn_renderizar, fn_limpar):
    selecionados = []
    chips_row    = ft.Row(wrap=True, spacing=6, visible=False)

    def _rebuild_chips():
        chips_row.controls.clear()
        if not selecionados:
            chips_row.visible = False
            return
        chips_row.visible = True
        for i, ex in enumerate(selecionados):
            def _rem(e, idx=i):
                selecionados.pop(idx)
                _rebuild_chips()
                if selecionados:
                    fn_renderizar(selecionados)
                else:
                    fn_limpar()
                try: page.update()
                except Exception: pass
            chips_row.controls.append(ft.Container(
                content=ft.Row([
                    ft.Text(ex["nome_oficial"], size=11, color="#E6EDF3"),
                    ft.Icon("close_rounded", size=11, color="#8B949E"),
                ], spacing=4, tight=True),
                bgcolor="#21262D", border_radius=12,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                on_click=_rem,
            ))
        chips_row.controls.append(ft.Container(
            content=ft.Text("Limpar tudo", size=13, color="#F0883E"),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=8, ink=True,
            on_click=lambda e: _limpar_tudo(),
        ))

    def _limpar_tudo():
        selecionados.clear()
        _rebuild_chips()
        fn_limpar()
        try: page.update()
        except Exception: pass

    def fn_adicionar(exame: dict):
        if any(s["id"] == exame["id"] for s in selecionados):
            return "Exame ja selecionado."
        numericos = [s for s in selecionados if s.get("tipo") == "numerico"]
        if exame.get("tipo") == "numerico" and len(numericos) >= 5:
            return "Maximo 5 exames numericos."
        if exame.get("tipo") == "numerico":
            hist = buscar_historico_exame(exame["id"])
            exame["historico"] = hist
        else:
            laudos = buscar_laudos(exame.get("nome_oficial", ""))
            exame["historico"] = laudos
        selecionados.append(exame)
        _rebuild_chips()
        fn_renderizar(selecionados)
        try: page.update()
        except Exception: pass
        return None

    return selecionados, chips_row, fn_adicionar, _limpar_tudo


# ══════════════════════════════════════════════════════════════
# ABA 1 - BUSCAR
# ══════════════════════════════════════════════════════════════

def _conteudo_buscar(page, fn_adicionar, chips_row, txt_info, col_resultado, selecionados=None):
    """
    Aba buscar:
      - modo BUSCA: campo + lista de sugestões
      - modo RESULTADO: chips selecionados + gráfico + botão "Adicionar exame"
    """
    exames_todos = buscar_todos_exames_padrao() + [
        {
            "id":           "laudo_" + str(l["exame_id"]),
            "nome_oficial": l["tipo_exame"] or "Laudo",
            "categoria":    "Laudo",
            "unidade":      "",
            "realizado":    True,
            "qtd":          1,
            "tipo":         "laudo",
            "historico":    [l],
        }
        for l in buscar_laudos()
    ]
    realizados = [e for e in exames_todos if e.get("realizado")]

    txt_busca = ft.TextField(
        hint_text="Buscar exame...",
        bgcolor="#161B22", border_color="#30363D",
        focused_border_color="#58A6FF",
        hint_style=ft.TextStyle(color="#484F58"),
        text_style=ft.TextStyle(color="#E6EDF3"),
        border_radius=8, height=42,
        prefix_icon="search_rounded",
    )
    lista = ft.Column(spacing=4)

    # Container do modo busca
    area_busca = ft.Column([txt_busca, lista, txt_info], spacing=6, visible=True)

    # Botão para abrir busca novamente no modo resultado
    btn_add_mais = ft.Container(
        content=ft.Row([
            ft.Icon("add_circle_outline_rounded", size=14, color="#58A6FF"),
            ft.Text("Adicionar exame", size=12, color="#58A6FF"),
        ], spacing=5, tight=True),
        visible=False,
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        ink=True,
        on_click=lambda e: _entrar_modo_busca(),
    )

    def _entrar_modo_busca():
        txt_busca.value = ""
        lista.controls.clear()
        area_busca.visible = True
        btn_add_mais.visible = False
        _filtrar()

    def _entrar_modo_resultado():
        area_busca.visible = False
        btn_add_mais.visible = True
        try: page.update()
        except Exception: pass

    def _filtrar(e=None):
        lista.controls.clear()
        q = (txt_busca.value or "").strip().upper()
        ids_sel = {s["id"] for s in (selecionados or [])}
        encontrados = [
            ex for ex in realizados
            if ex["id"] not in ids_sel
            and (not q or q in ex["nome_oficial"].upper())
        ][:10]
        for ex in encontrados:
            _eh_laudo = ex.get("tipo") in ("laudo", "imagem")
            cor = "#BC8CFF" if _eh_laudo else "#58A6FF"
            sub = ex.get("categoria","") + ("  •  " + str(ex["qtd"]) + "x" if ex.get("qtd") else "")
            def _add(e, exame=ex):
                err = fn_adicionar(exame)
                if err:
                    txt_info.value = err
                    try: page.update()
                    except Exception: pass
                else:
                    txt_info.value = ""
                    _entrar_modo_resultado()
            lista.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("description_rounded" if _eh_laudo
                            else "show_chart_rounded", size=13, color=cor),
                    ft.Column([
                        ft.Text(ex["nome_oficial"], size=12, color="#E6EDF3"),
                        ft.Text(sub, size=10, color="#484F58"),
                    ], spacing=1, expand=True),
                    ft.Icon("add_circle_outline_rounded", size=14, color=cor),
                ], spacing=8),
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                border_radius=6, bgcolor="#161B22",
                border=ft.Border(
                    top=ft.BorderSide(1,"#21262D"), bottom=ft.BorderSide(1,"#21262D"),
                    left=ft.BorderSide(2, cor),     right=ft.BorderSide(1,"#21262D"),
                ),
                on_click=_add, ink=True,
                on_hover=lambda e: setattr(e.control,"bgcolor",
                    "#21262D" if e.data=="true" else "#161B22") or page.update(),
            ))
        try: page.update()
        except Exception: pass

    txt_busca.on_change = _filtrar
    _filtrar()
    return [area_busca, chips_row, btn_add_mais, col_resultado]


# ══════════════════════════════════════════════════════════════
# MOTOR COMPARTILHADO — seleção e renderização de exames
# Usado pelas abas: Médico, Especialidade, Classificação
# ══════════════════════════════════════════════════════════════

def _criar_motor_selecao_exames(page, pubsub_tag: str):
    """
    Encapsula todo o estado e UI compartilhados entre as abas que seguem
    o padrão: selecionar entidade → buscar exame → chips + gráfico/laudo.

    Retorna dict com:
      - controles: lista de ft.Control para montar na aba
      - fn_carregar_itens(exames, hint): popula itens e entra no modo busca
    """
    import threading

    selecionados    = []
    itens           = []
    _subscribed     = [False]
    _render_version = [0]

    txt_sem   = ft.Text("", size=12, color=MUT)
    chips_row = ft.Row(wrap=True, spacing=6, visible=False)

    spinner = ft.Container(
        content=ft.Row([
            ft.ProgressRing(width=20, height=20, stroke_width=2, color=AZUL),
            ft.Column([
                ft.Text("Gerando gráfico...", size=13, color=TXT,
                        weight=ft.FontWeight.W_500),
                ft.Text("Aguarde um momento", size=11, color=SEC),
            ], spacing=2),
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=CARD, border_radius=8,
        padding=ft.padding.symmetric(horizontal=16, vertical=14),
        border=ft.Border(
            top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
            left=ft.BorderSide(3, AZUL), right=ft.BorderSide(1, BD),
        ),
        visible=False,
    )
    col_resultado = ft.Column([spinner], spacing=10, visible=False)

    txt_busca = ft.TextField(
        hint_text="Buscar exame...",
        bgcolor=CARD, border_color=BD2,
        focused_border_color=AZUL,
        hint_style=ft.TextStyle(color=MUT),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, height=44,
        prefix_icon="search_rounded",
        visible=False,
    )
    lista_exames = ft.Column(spacing=4, visible=False)
    txt_info     = ft.Text("", size=12, color=LAR, visible=False)

    btn_add_mais = ft.Container(
        content=ft.Row([
            ft.Icon("add_circle_outline_rounded", size=14, color=AZUL),
            ft.Text("Adicionar exame", size=12, color=AZUL,
                    weight=ft.FontWeight.W_500),
        ], spacing=6, tight=True),
        bgcolor=CARD, border_radius=8,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        border=ft.Border(
            top=ft.BorderSide(1, BD2), bottom=ft.BorderSide(1, BD2),
            left=ft.BorderSide(1, BD2), right=ft.BorderSide(1, BD2),
        ),
        visible=False, ink=True,
    )
    btn_add_mais.on_click = lambda e: _modo_busca()

    # ── modos ────────────────────────────────────────────────────────────

    def _modo_busca():
        txt_busca.value       = ""
        txt_busca.visible     = True
        lista_exames.visible  = True
        txt_info.visible      = True
        btn_add_mais.visible  = False
        col_resultado.visible = False
        txt_info.value        = ""
        lista_exames.controls.clear()
        _filtrar()

    def _modo_resultado():
        txt_busca.visible     = False
        lista_exames.visible  = False
        txt_info.visible      = False
        btn_add_mais.visible  = True
        _renderizar()

    # ── chips ────────────────────────────────────────────────────────────

    def _rebuild_chips():
        chips_row.controls.clear()
        if not selecionados:
            chips_row.visible = False
            return
        chips_row.visible = True
        for i, ex in enumerate(selecionados):
            def _rem(e, idx=i):
                selecionados.pop(idx)
                _rebuild_chips()
                if selecionados: _renderizar()
                else: _limpar()
                try: page.update()
                except Exception: pass
            chips_row.controls.append(ft.Container(
                content=ft.Row([
                    ft.Text(ex["nome_oficial"], size=11, color=TXT),
                    ft.Icon("close_rounded", size=11, color=SEC),
                ], spacing=4, tight=True),
                bgcolor=BD, border_radius=12,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                on_click=_rem,
            ))
        chips_row.controls.append(ft.Container(
            content=ft.Text("Limpar tudo", size=13, color=LAR),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=8, ink=True,
            on_click=lambda e: _limpar_tudo(),
        ))

    # ── limpeza ──────────────────────────────────────────────────────────

    def _limpar():
        spinner.visible = False
        col_resultado.controls.clear()
        col_resultado.controls.append(spinner)
        col_resultado.visible = False
        btn_add_mais.visible  = False
        _modo_busca()

    def _limpar_tudo():
        _render_version[0] += 1
        selecionados.clear()
        _rebuild_chips()
        _limpar()

    # ── adicionar ────────────────────────────────────────────────────────

    def _adicionar(exame):
        if any(s["id"] == exame["id"] for s in selecionados):
            return "Exame já selecionado."
        numericos = [s for s in selecionados if s.get("tipo") == "numerico"]
        if exame.get("tipo") == "numerico" and len(numericos) >= 5:
            return "Máximo 5 exames numéricos."
        if exame.get("tipo") == "numerico":
            exame["historico"] = buscar_historico_exame(exame["id"])
        else:
            exame["historico"] = buscar_laudos(exame.get("nome_oficial", ""))
        selecionados.append(exame)
        _rebuild_chips()
        _modo_resultado()
        return None

    # ── adicionar em lote (sem busca manual — auto-add por categoria/esp) ──

    def fn_adicionar_lote(exames_lista):
        """Adiciona todos os exames da lista de uma vez (respeita max-5 e duplicatas)."""
        adicionados = 0
        for exame in exames_lista:
            if any(s["id"] == exame["id"] for s in selecionados):
                continue
            numericos = [s for s in selecionados if s.get("tipo") == "numerico"]
            if exame.get("tipo") == "numerico" and len(numericos) >= 5:
                continue
            ex = dict(exame)
            if ex.get("tipo") == "numerico":
                ex["historico"] = buscar_historico_exame(ex["id"])
            else:
                ex["historico"] = buscar_laudos(ex.get("nome_oficial", ""))
            selecionados.append(ex)
            adicionados += 1
        if adicionados > 0:
            _rebuild_chips()
            _renderizar()

    # ── filtrar ──────────────────────────────────────────────────────────

    def _filtrar(e=None):
        lista_exames.controls.clear()
        q = (txt_busca.value or "").strip().upper()
        ids_sel = {s["id"] for s in selecionados}
        encontrados = [
            ex for ex in itens
            if ex.get("id") not in ids_sel
            and (not q or q in ex["nome_oficial"].upper())
        ][:10]
        for ex in encontrados:
            eh_laudo = ex.get("tipo") in ("laudo", "imagem", "mapa")
            cor = ROXO if eh_laudo else AZUL
            sub = (ex.get("categoria") or "") + (
                f"  •  {ex.get('qtd', 0)}x" if ex.get("qtd") else "")
            def _add(e, exame=ex):
                err = _adicionar(exame)
                if err:
                    txt_info.value   = err
                    txt_info.visible = True
                    try: page.update()
                    except Exception: pass
            lista_exames.controls.append(ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(
                            "description_rounded" if eh_laudo
                            else "show_chart_rounded",
                            size=14, color=cor),
                        bgcolor=f"{cor}18", border_radius=6,
                        width=30, height=30,
                        alignment=ft.alignment.Alignment(0, 0)),
                    ft.Column([
                        ft.Text(ex["nome_oficial"], size=12, color=TXT,
                                weight=ft.FontWeight.W_500),
                        ft.Text(sub, size=10, color=MUT),
                    ], spacing=1, expand=True),
                    ft.Icon("add_circle_outline_rounded", size=16, color=cor),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                border_radius=6, bgcolor=CARD,
                border=ft.Border(
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    left=ft.BorderSide(2, cor), right=ft.BorderSide(1, BD),
                ),
                on_click=_add, ink=True,
            ))
        try: page.update()
        except Exception: pass

    txt_busca.on_change = _filtrar

    # ── renderizar ───────────────────────────────────────────────────────

    def _renderizar():
        if not selecionados: return
        _render_version[0] += 1
        my_version = _render_version[0]
        spinner.visible = True
        col_resultado.controls.clear()
        col_resultado.controls.append(spinner)
        col_resultado.visible = True
        try: page.update()
        except Exception: pass
        _sel = list(selecionados)

        def _montar():
            controles = []
            numericos = [s for s in _sel if s.get("tipo") == "numerico"]
            laudos    = [s for s in _sel if s.get("tipo") not in ("numerico",)]
            if numericos:
                try:
                    controles.append(renderizar_grafico_combinado(page, numericos))
                except Exception as ex:
                    controles.append(ft.Text(f"Gráfico indisponível: {ex}",
                                             size=11, color=LAR))
            for laudo in laudos:
                try:
                    controles.append(renderizar_card_laudo(page, laudo))
                except Exception: pass
            page.pubsub.send_all({"_tipo": pubsub_tag, "controles": controles,
                                  "_ver": my_version})

        def _on_msg(msg):
            if not isinstance(msg, dict): return
            if msg.get("_tipo") != pubsub_tag: return
            if msg.get("_ver") != _render_version[0]: return  # render obsoleto
            spinner.visible = False
            col_resultado.controls.clear()
            for c in msg["controles"]:
                col_resultado.controls.append(c)
            col_resultado.visible = True
            try: page.update()
            except Exception: pass

        if not _subscribed[0]:
            page.pubsub.subscribe(_on_msg)
            _subscribed[0] = True
        threading.Thread(target=_montar, daemon=True).start()

    # ── carregar itens (chamado pela aba ao selecionar entidade) ─────────

    def fn_carregar_itens(exames_lista, hint="Buscar exame...", acumular=False):
        itens.clear()
        itens.extend(exames_lista)
        if not acumular:
            selecionados.clear()
            _rebuild_chips()
        # quando acumular=True: NÃO toca chips_row — mantém seleção anterior intacta
        # cancela qualquer render em voo (evita race condition com thread de gráfico)
        _render_version[0] += 1
        txt_sem.value         = ""
        txt_busca.visible     = False
        lista_exames.visible  = False
        txt_info.visible      = False
        btn_add_mais.visible  = False
        col_resultado.visible = False
        if not exames_lista:
            txt_sem.value = "Nenhum exame encontrado." if not acumular or not selecionados \
                            else "Nenhum exame novo nesta categoria."
            try: page.update()
            except Exception: pass
            return
        txt_busca.hint_text = hint
        _modo_busca()

    return {
        "controles": [txt_sem, chips_row, txt_busca,
                      lista_exames, txt_info, btn_add_mais, col_resultado],
        "chips_row":         chips_row,
        "col_resultado":     col_resultado,
        "fn_carregar_itens": fn_carregar_itens,
        "fn_adicionar_lote": fn_adicionar_lote,
        "fn_limpar_tudo":    _limpar_tudo,
    }


# ══════════════════════════════════════════════════════════════
# ABA 2 - MEDICO
# ══════════════════════════════════════════════════════════════

def _conteudo_medico(page):
    medicos = buscar_medicos_com_exames()
    motor   = _criar_motor_selecao_exames(page, "graf_medico_v2")
    fn_car  = motor["fn_carregar_itens"]

    med_sel = [None]   # médico selecionado: dict ou None

    f_medico = ft.TextField(
        label="Médico",
        hint_text="Digite para buscar…",
        bgcolor=CARD, border_color=BD2, focused_border_color=VERD,
        label_style=ft.TextStyle(color=SEC),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8,
    )
    sug_med = ft.Column(spacing=2, visible=False)

    def _filtrar(e):
        termo = (f_medico.value or "").strip().upper()
        sug_med.controls.clear()
        if not termo:
            sug_med.visible = False
            med_sel[0] = None
            try: page.update()
            except Exception: pass
            return
        encontrados = [m for m in medicos if termo in m["nome"].upper()][:8]
        for m in encontrados:
            def _sel(e, med=m):
                f_medico.value  = med["nome"]
                med_sel[0]      = med
                sug_med.controls.clear()
                sug_med.visible = False
                mid_r = med["id"] if med["id"] is not None else None
                fn_car(buscar_exames_do_medico(mid_r, med["nome"]),
                       f"Buscar exame de {med['nome']}...")
                try: page.update()
                except Exception: pass
            esp = m.get("especialidade") or ""
            total = m.get("total", 0)
            sug_med.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("person_rounded", size=14, color=VERD),
                    ft.Column([
                        ft.Text(m["nome"], size=12, color=TXT),
                        ft.Row([
                            ft.Text(esp, size=10, color=MUT),
                            ft.Text(f"· {total} exame(s)", size=10, color=MUT),
                        ], spacing=4),
                    ], spacing=1, tight=True),
                ], spacing=8),
                bgcolor=BD, border_radius=6,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                on_click=_sel, ink=True,
            ))
        sug_med.visible = bool(encontrados)
        try: page.update()
        except Exception: pass

    f_medico.on_change = _filtrar
    return [ft.Column([f_medico, sug_med], spacing=0)] + motor["controles"]


# ══════════════════════════════════════════════════════════════
# ABA 3 - ESPECIALIDADE
# ══════════════════════════════════════════════════════════════

def _conteudo_especialidades(page):
    todas       = listar_especialidades(so_ativas=True)
    esps_exames = {e["nome"]: e["total"] for e in buscar_especialidades_com_exames()}
    motor    = _criar_motor_selecao_exames(page, "graf_especialidade_v1")
    fn_lote  = motor["fn_adicionar_lote"]

    if not todas:
        return [ft.Container(
            content=ft.Column([
                ft.Icon("medical_services_outlined_rounded", size=36, color=MUT),
                ft.Text("Nenhuma especialidade cadastrada.", size=13,
                        color=SEC, weight=ft.FontWeight.W_600),
                ft.Text("Execute: python -m prontuario.dados.fix_seed",
                        size=11, color=MUT),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            padding=ft.padding.all(24), alignment=ft.alignment.center,
        )]

    esps_sel  = []   # nomes das especialidades escolhidas
    expandido = [False]

    lista_esp  = ft.Column(spacing=3, height=190, scroll=ft.ScrollMode.AUTO)
    txt_filtro = ft.TextField(
        hint_text="Filtrar especialidade...",
        bgcolor=CARD, border_color=BD2, focused_border_color=AMAR,
        hint_style=ft.TextStyle(color=MUT), text_style=ft.TextStyle(color=TXT),
        border_radius=8, height=44, prefix_icon="search_rounded",
    )
    lbl_ver_mais = ft.Text(f"▼ Ver todas as especialidades ({len(todas)})",
                           size=11, color=AMAR)

    def _toggle_expand(e):
        expandido[0] = not expandido[0]
        lista_esp.height = None if expandido[0] else 190
        lbl_ver_mais.value = ("▲ Recolher" if expandido[0]
                              else f"▼ Ver todas as especialidades ({len(todas)})")
        page.update()

    btn_ver_mais = ft.Container(
        content=lbl_ver_mais, on_click=_toggle_expand,
        padding=ft.padding.symmetric(horizontal=4, vertical=2), ink=True,
    )
    estagio1 = ft.Column(
        controls=[txt_filtro, lista_esp, btn_ver_mais],
        spacing=8, visible=True,
    )

    # ── chips das especialidades escolhidas + botão Adicionar ─────
    esps_chips = ft.Row(wrap=True, spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def _rebuild_esp_chips():
        esps_chips.controls.clear()
        for nome in esps_sel:
            def _rem(e, n=nome):
                esps_sel.remove(n)
                _rebuild_esp_chips()
                if esps_sel:
                    motor["fn_limpar_tudo"]()
                    for s in esps_sel:
                        fn_lote(buscar_exames_da_especialidade(s))
                else:
                    motor["fn_limpar_tudo"]()
                    _ir_seletor()
                try: page.update()
                except Exception: pass
            esps_chips.controls.append(ft.Container(
                content=ft.Row([
                    ft.Text(nome, size=11, color=AMAR, weight=ft.FontWeight.W_500),
                    ft.Icon("close_rounded", size=11, color=MUT),
                ], spacing=4, tight=True),
                bgcolor=f"{AMAR}18", border_radius=12,
                border=ft.Border(
                    top=ft.BorderSide(1, f"{AMAR}60"), bottom=ft.BorderSide(1, f"{AMAR}60"),
                    left=ft.BorderSide(1, f"{AMAR}60"), right=ft.BorderSide(1, f"{AMAR}60"),
                ),
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                on_click=_rem, ink=True,
            ))
        esps_chips.controls.append(ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=13, color=AMAR),
                ft.Text("Adicionar especialidade", size=12, color=AMAR),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=12, ink=True,
            on_click=lambda e: _ir_seletor(),
        ))

    def _ir_seletor(e=None):
        _rebuild_esp_list(txt_filtro.value or "")
        estagio1.visible = True
        estagio2.visible = False
        try: page.update()
        except Exception: pass

    def _limpar_tudo(e=None):
        esps_sel.clear()
        motor["fn_limpar_tudo"]()
        _rebuild_esp_chips()
        _ir_seletor()

    barra_topo = ft.Row([
        esps_chips,
        ft.Container(expand=True),
        ft.Container(
            content=ft.Row([
                ft.Icon("clear_all_rounded", size=14, color=LAR),
                ft.Text("Limpar tudo", size=12, color=LAR),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            ink=True,
            on_click=_limpar_tudo,
        ),
    ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

    estagio2 = ft.Column(
        controls=[barra_topo, motor["chips_row"], motor["col_resultado"]],
        spacing=8, visible=False,
    )

    def _rebuild_esp_list(filtro=""):
        lista_esp.controls.clear()
        fu = filtro.upper()
        encontrados = [e for e in todas if not fu or fu in e["nome"].upper()]
        if not encontrados:
            lista_esp.controls.append(
                ft.Text("Nenhuma especialidade encontrada.", size=12, color=MUT))
            return
        for esp in encontrados:
            nome  = esp["nome"]
            total = esps_exames.get(nome, 0)
            ja_sel = nome in esps_sel

            def _click(e, n=nome):
                is_new = n not in esps_sel
                if is_new:
                    esps_sel.append(n)
                _rebuild_esp_chips()
                estagio1.visible = False
                estagio2.visible = True
                try: page.update()
                except Exception: pass
                if is_new:
                    fn_lote(buscar_exames_da_especialidade(n))

            lista_esp.controls.append(ft.Container(
                content=ft.Row([
                    ft.Text(nome, size=12,
                            color=AMAR if ja_sel else SEC,
                            weight=ft.FontWeight.W_600 if ja_sel else ft.FontWeight.W_400,
                            expand=True),
                    ft.Container(
                        content=ft.Text(str(total), size=10, color="#0D1117",
                                        weight=ft.FontWeight.W_600),
                        bgcolor=AMAR if total > 0 else "#30363D",
                        border_radius=10,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    ),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=f"{AMAR}0A" if ja_sel else CARD,
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=7),
                border=ft.Border(
                    top=ft.BorderSide(1, f"{AMAR}60" if ja_sel else BD2),
                    bottom=ft.BorderSide(1, f"{AMAR}60" if ja_sel else BD2),
                    left=ft.BorderSide(2 if ja_sel else 1, AMAR if ja_sel else BD2),
                    right=ft.BorderSide(1, f"{AMAR}60" if ja_sel else BD2),
                ),
                on_click=_click, ink=True,
            ))

    txt_filtro.on_change = lambda e: (_rebuild_esp_list(txt_filtro.value or ""), page.update())
    _rebuild_esp_list()
    return [estagio1, estagio2]


# ══════════════════════════════════════════════════════════════
# ABA 4 - CLASSIFICAÇÃO
# ══════════════════════════════════════════════════════════════

def _conteudo_classificacao(page):
    categorias = buscar_todas_categorias()
    motor      = _criar_motor_selecao_exames(page, "graf_classificacao_v1")
    fn_lote    = motor["fn_adicionar_lote"]

    cats_sel = []   # nomes das categorias escolhidas

    lista_cat  = ft.Column(spacing=3, height=190, scroll=ft.ScrollMode.AUTO)
    txt_filtro = ft.TextField(
        hint_text="Filtrar categoria...",
        bgcolor=CARD, border_color=BD2, focused_border_color=ROXO,
        hint_style=ft.TextStyle(color=MUT), text_style=ft.TextStyle(color=TXT),
        border_radius=8, height=44, prefix_icon="search_rounded",
    )
    estagio1 = ft.Column(controls=[txt_filtro, lista_cat], spacing=8, visible=True)

    # ── chips das categorias escolhidas + botão Adicionar ────────
    cats_chips = ft.Row(wrap=True, spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def _rebuild_cat_chips():
        cats_chips.controls.clear()
        for nome in cats_sel:
            def _rem(e, n=nome):
                cats_sel.remove(n)
                _rebuild_cat_chips()
                if cats_sel:
                    motor["fn_limpar_tudo"]()
                    for c in cats_sel:
                        fn_lote(buscar_exames_da_categoria(c))
                else:
                    motor["fn_limpar_tudo"]()
                    _ir_seletor()
                try: page.update()
                except Exception: pass
            cats_chips.controls.append(ft.Container(
                content=ft.Row([
                    ft.Text(nome, size=11, color=ROXO, weight=ft.FontWeight.W_500),
                    ft.Icon("close_rounded", size=11, color=MUT),
                ], spacing=4, tight=True),
                bgcolor=f"{ROXO}18", border_radius=12,
                border=ft.Border(
                    top=ft.BorderSide(1, f"{ROXO}60"), bottom=ft.BorderSide(1, f"{ROXO}60"),
                    left=ft.BorderSide(1, f"{ROXO}60"), right=ft.BorderSide(1, f"{ROXO}60"),
                ),
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                on_click=_rem, ink=True,
            ))
        cats_chips.controls.append(ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=13, color=ROXO),
                ft.Text("Adicionar categoria", size=12, color=ROXO),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=12, ink=True,
            on_click=lambda e: _ir_seletor(),
        ))

    def _ir_seletor(e=None):
        _rebuild_cat_list(txt_filtro.value or "")
        estagio1.visible = True
        estagio2.visible = False
        try: page.update()
        except Exception: pass

    def _limpar_tudo(e=None):
        cats_sel.clear()
        motor["fn_limpar_tudo"]()
        _rebuild_cat_chips()
        _ir_seletor()

    barra_topo = ft.Row([
        cats_chips,
        ft.Container(expand=True),
        ft.Container(
            content=ft.Row([
                ft.Icon("clear_all_rounded", size=14, color=LAR),
                ft.Text("Limpar tudo", size=12, color=LAR),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            ink=True,
            on_click=_limpar_tudo,
        ),
    ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

    estagio2 = ft.Column(
        controls=[barra_topo, motor["chips_row"], motor["col_resultado"]],
        spacing=8, visible=False,
    )

    def _rebuild_cat_list(filtro=""):
        lista_cat.controls.clear()
        fu = filtro.upper()
        encontrados = [c for c in categorias if not fu or fu in c["categoria"].upper()]
        if not encontrados:
            lista_cat.controls.append(
                ft.Text("Nenhuma categoria encontrada.", size=12, color=MUT))
            return
        for cat in encontrados:
            nome   = cat["categoria"]
            realiz = cat["realizados"]
            ja_sel = nome in cats_sel

            def _click(e, n=nome):
                is_new = n not in cats_sel
                if is_new:
                    cats_sel.append(n)
                _rebuild_cat_chips()
                estagio1.visible = False
                estagio2.visible = True
                try: page.update()
                except Exception: pass
                if is_new:
                    fn_lote(buscar_exames_da_categoria(n))

            lista_cat.controls.append(ft.Container(
                content=ft.Row([
                    ft.Text(nome, size=12,
                            color=ROXO if ja_sel else SEC,
                            weight=ft.FontWeight.W_600 if ja_sel else ft.FontWeight.W_400,
                            expand=True),
                    ft.Container(
                        content=ft.Text(str(realiz), size=10, color="#0D1117",
                                        weight=ft.FontWeight.W_600),
                        bgcolor=ROXO if realiz > 0 else "#30363D",
                        border_radius=10,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    ),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=f"{ROXO}0A" if ja_sel else CARD,
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=7),
                border=ft.Border(
                    top=ft.BorderSide(1, f"{ROXO}60" if ja_sel else BD2),
                    bottom=ft.BorderSide(1, f"{ROXO}60" if ja_sel else BD2),
                    left=ft.BorderSide(2 if ja_sel else 1, ROXO if ja_sel else BD2),
                    right=ft.BorderSide(1, f"{ROXO}60" if ja_sel else BD2),
                ),
                on_click=_click, ink=True,
            ))

    txt_filtro.on_change = lambda e: (_rebuild_cat_list(txt_filtro.value or ""), page.update())
    _rebuild_cat_list()
    return [estagio1, estagio2]


# ══════════════════════════════════════════════════════════════
# ABA 3 - EXAMES FISICOS
# ══════════════════════════════════════════════════════════════

def _conteudo_exames(page):
    import webbrowser
    exames = buscar_todos_exames_fisicos()

    txt_busca = ft.TextField(
        hint_text="Buscar exame...",
        bgcolor="#161B22", border_color="#30363D",
        focused_border_color="#F0883E",
        hint_style=ft.TextStyle(color="#484F58"),
        text_style=ft.TextStyle(color="#E6EDF3"),
        border_radius=8, height=44,
        prefix_icon="search_rounded",
    )
    lista = ft.Column(spacing=4)

    def _construir_card(ex):
        _eh_laudo = ex.get("tipo") in ("laudo", "imagem")
        cor   = "#BC8CFF" if _eh_laudo else "#58A6FF"
        label = ex.get("tipo_exame") or ex.get("tipo", "")
        data  = ex["data"][:10] if ex.get("data") else "?"

        def _ver(e, exame=ex):
            if exame.get("drive_id"):
                webbrowser.open("https://drive.google.com/file/d/" + exame["drive_id"] + "/view")
            elif exame.get("arquivo"):
                webbrowser.open("file:///" + exame["arquivo"])

        def _del(e, exame=ex, lbl=label, dt=data):
            overlay_ref = [None]

            def _fechar():
                if overlay_ref[0] and overlay_ref[0] in page.overlay:
                    page.overlay.remove(overlay_ref[0])
                try: page.update()
                except Exception: pass

            def _confirmar(e2):
                _fechar()
                arquivo = excluir_exame_fisico(exame["id"])
                if arquivo and os.path.isfile(arquivo):
                    try: os.remove(arquivo)
                    except Exception: pass
                exames[:] = buscar_todos_exames_fisicos()
                _filtrar()

            def _cancelar(e2):
                _fechar()

            _btn_cancelar_exc = ft.Container(
                content=ft.Text("Cancelar", size=13, color="#8B949E"),
                padding=ft.padding.symmetric(horizontal=14, vertical=9),
                border_radius=8, bgcolor="#8B949E22", ink=True,
            )
            _btn_cancelar_exc.on_click = _cancelar

            _btn_excluir_ok = ft.Container(
                content=ft.Text("Excluir", size=13, color="#F85149",
                                weight=ft.FontWeight.W_600),
                padding=ft.padding.symmetric(horizontal=14, vertical=9),
                border_radius=8, bgcolor="#F8514922", ink=True,
            )
            _btn_excluir_ok.on_click = _confirmar

            overlay_ref[0] = ft.Container(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Confirmar exclusao", size=16, color="#E6EDF3",
                                weight=ft.FontWeight.W_600),
                        ft.Container(height=8),
                        ft.Text("Excluir '" + lbl + "' de " + dt + "?\nEsta acao nao pode ser desfeita.",
                                color="#8B949E", size=13),
                        ft.Container(height=16),
                        ft.Row([
                            _btn_cancelar_exc,
                            _btn_excluir_ok,
                        ], alignment=ft.MainAxisAlignment.END, spacing=8),
                    ], tight=True),
                    bgcolor="#161B22", border_radius=12, padding=ft.padding.all(24), width=320,
                    border=ft.Border(
                        top=ft.BorderSide(1,"#30363D"), bottom=ft.BorderSide(1,"#30363D"),
                        left=ft.BorderSide(1,"#30363D"), right=ft.BorderSide(1,"#30363D"),
                    ),
                ),
                bgcolor="#00000088", expand=True,
                alignment=ft.alignment.Alignment(0,0),
            )
            page.overlay.append(overlay_ref[0])
            try: page.update()
            except Exception: pass

        return ft.Container(
            content=ft.Row([
                ft.Icon("description_rounded" if _eh_laudo
                        else "show_chart_rounded", size=13, color=cor),
                ft.Column([
                    ft.Text(label, size=12, color="#E6EDF3"),
                    ft.Row([
                        ft.Text(data, size=10, color="#484F58"),
                        ft.Text("·", size=10, color="#21262D"),
                        ft.Text(ex.get("medico",""), size=10, color="#8B949E"),
                        ft.Text("·", size=10, color="#21262D"),
                        ft.Text(ex.get("laboratorio",""), size=10, color="#58A6FF"),
                    ], spacing=4),
                ], spacing=1, expand=True),
                ft.IconButton("visibility_rounded",
                              icon_color="#58A6FF", icon_size=16, on_click=_ver),
                ft.IconButton("delete_rounded",
                              icon_color="#F85149", icon_size=16, on_click=_del),
            ], spacing=8),
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_radius=6, bgcolor="#161B22",
            border=ft.Border(
                top=ft.BorderSide(1,"#21262D"), bottom=ft.BorderSide(1,"#21262D"),
                left=ft.BorderSide(2, cor),     right=ft.BorderSide(1,"#21262D"),
            ),
        )

    def _filtrar(e=None):
        lista.controls.clear()
        q = (txt_busca.value or "").strip().upper()
        encontrados = [
            ex for ex in exames
            if not q
            or q in (ex.get("tipo_exame") or ex.get("tipo", "")).upper()
            or q in (ex.get("medico") or "").upper()
            or q in (ex.get("laboratorio") or "").upper()
        ]
        if not encontrados:
            lista.controls.append(
                ft.Text("Nenhum exame encontrado.", size=12, color="#484F58"))
        else:
            for ex in encontrados:
                lista.controls.append(_construir_card(ex))
        try: page.update()
        except Exception: pass

    txt_busca.on_change = _filtrar
    _filtrar()

    return [txt_busca, lista]


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL
# ══════════════════════════════════════════════════════════════

def criar_tela_consulta(page: ft.Page, voltar_fn):
    from shared.layout import Layout
    lay = Layout(page)

    ABAS = [
        (0, "search_rounded",            "Buscar",         AZUL),
        (1, "person_rounded",            "Médico",          VERD),
        (2, "medical_services_rounded",  "Especialidade",   AMAR),
        (3, "folder_rounded",    "Exames",          LAR),
        (4, "category_rounded",          "Classificação",   ROXO),
    ]
    aba_ativa = [0]

    col_resultado, fn_renderizar, fn_limpar = criar_area_resultado(page)
    txt_info_b = ft.Text("", size=12, color="#F0883E")
    txt_info_m = ft.Text("", size=12, color="#F0883E")
    selecionados_b, chips_b, fn_add_b, _ = criar_gestor_selecao(page, fn_renderizar, fn_limpar)
    selecionados_m, chips_m, fn_add_m, _ = criar_gestor_selecao(page, fn_renderizar, fn_limpar)

    barra_abas    = ft.Row(spacing=0)
    area_conteudo = ft.Column(spacing=8, expand=True, scroll=ft.ScrollMode.AUTO)

    def _rebuild_abas():
        barra_abas.controls.clear()
        for idx, icone, label, cor in ABAS:
            ativo = idx == aba_ativa[0]
            def _click(e, i=idx):
                aba_ativa[0] = i
                _rebuild_abas()
                _rebuild_conteudo()
            barra_abas.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon(icone, size=16, color=cor if ativo else "#8B949E"),
                    ft.Text(label, size=10,
                            color=cor if ativo else "#8B949E",
                            weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.W_400),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2, tight=True),
                expand=True,
                padding=ft.padding.symmetric(vertical=10),
                border=ft.Border(bottom=ft.BorderSide(2, cor if ativo else "#00000000")),
                on_click=_click,
            ))
        try: page.update()
        except Exception: pass

    def _rebuild_conteudo():
        area_conteudo.controls.clear()
        if aba_ativa[0] == 0:
            area_conteudo.controls.extend(
                _conteudo_buscar(page, fn_add_b, chips_b, txt_info_b, col_resultado, selecionados_b))
        elif aba_ativa[0] == 1:
            area_conteudo.controls.extend(_conteudo_medico(page))
        elif aba_ativa[0] == 2:
            area_conteudo.controls.extend(_conteudo_especialidades(page))
        elif aba_ativa[0] == 3:
            area_conteudo.controls.extend(_conteudo_exames(page))
        else:
            area_conteudo.controls.extend(_conteudo_classificacao(page))
        try: page.update()
        except Exception: pass

    _rebuild_abas()
    _rebuild_conteudo()

    cabecalho = lay.criar_cabecalho(
        "Consulta de Exames", voltar_fn,
        icone_titulo="search_rounded",
        cor_titulo=AZUL,
    )

    corpo = ft.Column([
        ft.Container(height=lay.spacer_topo, bgcolor=BG),
        cabecalho,
        ft.Container(content=barra_abas,
                     border=ft.Border(bottom=ft.BorderSide(1, BD))),
        ft.Container(
            content=area_conteudo,
            padding=ft.padding.all(16),
            expand=True,
        ),
    ], expand=True, spacing=0)

    return lay.wrap(ft.Container(bgcolor=BG, expand=True, content=corpo))
