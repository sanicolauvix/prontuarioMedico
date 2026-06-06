# -*- coding: utf-8 -*-
"""
shared/grafico.py — Koios Prontuário
Rotina única de gráfico de linha para todo o app.

Exports públicos:
    valor_float(v)               — converte string em float
    parse_referencia(ref_str)    — extrai (min, max) de texto de referência
    gerar_grafico_flet(historicos) — widget LineChart com pontos e linhas de ref
    renderizar_grafico_combinado(page, exames_selecionados) — gráfico + chips + detalhe

Formato de entrada de exames_selecionados:
    [
      {
        "nome_oficial": "Hemoglobina",
        "unidade": "g/dL",
        "historico": [
            {"valor": "14.2", "unidade": "g/dL", "data": "2024-03-15",
             "referencia": "12.0 - 16.0", "nivel": "otimo",
             "laboratorio": "Pretti", "drive_id": "..."},
            ...
        ]
      },
      ...
    ]
"""

import flet as ft
import re

# ── Paleta ────────────────────────────────────────────────────────────────────
CORES_EXAME = ["#58A6FF", "#3FB950", "#F0883E", "#BC8CFF", "#D29922"]

NIVEL_COR = {
    "critico_baixo":    "#FF4444",
    "baixo":            "#F0883E",
    "otimo":            "#3FB950",
    "alto":             "#F0883E",
    "critico_alto":     "#FF4444",
    "sem_referencia":   "#58A6FF",
    "nao_identificado": "#8B949E",
}

NIVEL_LABEL = {
    "critico_baixo":    "Critico v",
    "baixo":            "Baixo v",
    "otimo":            "Otimo OK",
    "alto":             "Alto ^",
    "critico_alto":     "Critico ^",
    "sem_referencia":   "—",
    "nao_identificado": "?",
}

_BG   = "#0D1117"; _CARD = "#161B22"; _BD = "#21262D"
_TXT  = "#E6EDF3"; _SEC  = "#8B949E"; _MUT = "#484F58"


# ── Helpers ───────────────────────────────────────────────────────────────────

def valor_float(v) -> float | None:
    """Converte string/número em float. Retorna None se inválido."""
    try:
        return float(str(v).replace(",", ".").strip())
    except Exception:
        return None


def parse_referencia(ref_str: str):
    """Extrai (min, max) de strings como '22,0 - 280,0', '< 5' ou '> 10'."""
    if not ref_str:
        return None, None
    s = ref_str.replace(",", ".").strip()
    m = re.search(r"([\d.]+)\s*(?:-|a)\s*([\d.]+)", s)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"<\s*([\d.]+)", s)
    if m:
        return None, float(m.group(1))
    m = re.search(r">\s*([\d.]+)", s)
    if m:
        return float(m.group(1)), None
    return None, None


def _parse_data(d: str):
    from datetime import datetime
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime((d or "")[:10], fmt)
        except Exception:
            pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
# GRÁFICO — widget puro (sem cabeçalho, sem navegação)
# ══════════════════════════════════════════════════════════════════════════════

def gerar_grafico_flet(historicos: list) -> ft.Control:
    """
    Recebe lista de (exame_dict, historico_list) e devolve ft.Container
    com LineChart interativo, pontos coloridos por nível e linhas de referência.
    """
    series = []
    for idx, (ex, hist) in enumerate(historicos):
        ent = sorted(
            [h for h in hist
             if valor_float(h.get("valor")) is not None
             and h.get("data") and _parse_data(h["data"])],
            key=lambda h: _parse_data(h["data"]),
        )
        if not ent:
            continue
        ref_min = ref_max = None
        for h in ent:
            rm, rx = parse_referencia(h.get("referencia", ""))
            if rm is not None or rx is not None:
                ref_min, ref_max = rm, rx
                break
        series.append({
            "ex": ex, "ent": ent,
            "cor": CORES_EXAME[idx % len(CORES_EXAME)],
            "ref_min": ref_min, "ref_max": ref_max,
            "uni":  ex.get("unidade") or (ent[0].get("unidade") if ent else "") or "",
            "nome": ex.get("nome_oficial", ""),
        })

    if not series:
        return ft.Text("Sem valores numéricos.", size=12, color=_MUT)

    todas_datas = sorted({
        _parse_data(h["data"])
        for s in series for h in s["ent"] if _parse_data(h["data"])
    })
    if not todas_datas:
        return ft.Text("Sem datas válidas.", size=12, color=_MUT)

    didx  = {d: i for i, d in enumerate(todas_datas)}
    todos_ys = [
        valor_float(h["valor"])
        for s in series for h in s["ent"]
        if valor_float(h["valor"]) is not None
    ]
    y_min = min(todos_ys) if todos_ys else 0.0
    y_max = max(todos_ys) if todos_ys else 100.0
    for s in series:
        if s["ref_min"] is not None: y_min = min(y_min, s["ref_min"])
        if s["ref_max"] is not None: y_max = max(y_max, s["ref_max"])
    y_pad = max((y_max - y_min) * 0.18, 1.0)

    chart_series = []
    for s in series:
        points = []
        for h in s["ent"]:
            d = _parse_data(h["data"])
            v = valor_float(h["valor"])
            if d is None or v is None:
                continue
            _nivel_h = h.get("nivel", "")
            # Só muda cor do ponto se for nível crítico/fora — caso contrário usa cor da série
            if _nivel_h in ("critico_baixo", "baixo", "alto", "critico_alto"):
                cor_pt = NIVEL_COR[_nivel_h]
            else:
                cor_pt = s["cor"]
            uni_str  = h.get("unidade") or s["uni"]
            data_fmt = d.strftime("%d/%m/%Y")
            points.append(ft.LineChartDataPoint(
                x=float(didx[d]), y=float(v),
                tooltip=f"{h.get('valor','')} {uni_str}\n{data_fmt}",
                point=ft.ChartCirclePoint(
                    radius=5, color=cor_pt,
                    stroke_color=_BG, stroke_width=1.5),
                selected_point=ft.ChartCirclePoint(
                    radius=7, color=cor_pt,
                    stroke_color=_BG, stroke_width=2),
            ))
        if not points:
            continue
        chart_series.append(ft.LineChartData(
            data_points=points, color=s["cor"],
            stroke_width=2.4, curved=False, stroke_cap_round=True,
        ))
        if s["ref_min"] is not None and s["ref_max"] is not None:
            n = float(len(todas_datas) - 1)
            for ref_y in (s["ref_min"], s["ref_max"]):
                chart_series.append(ft.LineChartData(
                    data_points=[
                        ft.LineChartDataPoint(x=0.0, y=float(ref_y)),
                        ft.LineChartDataPoint(x=n,   y=float(ref_y)),
                    ],
                    color=s["cor"] + "55", stroke_width=1.0,
                    dash_pattern=[5, 5], curved=False,
                ))

    if not chart_series:
        return ft.Text("Sem pontos para exibir.", size=12, color=_MUT)

    n_datas  = len(todas_datas)
    step     = max(1, n_datas // 7)
    x_labels = [
        ft.ChartAxisLabel(
            value=float(i),
            label=ft.Container(
                content=ft.Column([
                    ft.Text(d.strftime("%d/%m"), size=9, color=_SEC,
                            text_align=ft.TextAlign.CENTER),
                    ft.Text(d.strftime("%Y"),    size=8, color=_MUT,
                            text_align=ft.TextAlign.CENTER),
                ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.only(top=2),
            ),
        )
        for i, d in enumerate(todas_datas)
        if i % step == 0 or i == n_datas - 1
    ]

    chart = ft.LineChart(
        data_series=chart_series,
        bgcolor=_CARD,
        tooltip_bgcolor=_CARD,
        tooltip_rounded_radius=6,
        tooltip_fit_inside_horizontally=True,
        tooltip_fit_inside_vertically=True,
        border=ft.Border(
            bottom=ft.BorderSide(1, _BD),
            left=ft.BorderSide(1, _BD),
        ),
        horizontal_grid_lines=ft.ChartGridLines(
            color=_BD, width=0.5, dash_pattern=[4, 4]),
        vertical_grid_lines=ft.ChartGridLines(color="#00000000"),
        left_axis=ft.ChartAxis(labels_size=44, show_labels=True),
        bottom_axis=ft.ChartAxis(labels=x_labels, labels_size=44),
        min_y=y_min - y_pad, max_y=y_max + y_pad,
        min_x=-0.3, max_x=float(len(todas_datas) - 1) + 0.3,
        expand=True, interactive=True,
    )

    return ft.Container(
        content=chart, height=280, bgcolor=_CARD,
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=4, vertical=8),
        border=ft.border.all(1, _BD),
    )


# ══════════════════════════════════════════════════════════════════════════════
# GRÁFICO COMBINADO — gráfico + chips de legenda + detalhe por exame
# ══════════════════════════════════════════════════════════════════════════════

def renderizar_grafico_combinado(page: ft.Page,
                                 exames_selecionados: list) -> ft.Control:
    """
    Gráfico único com chips de legenda clicáveis.
    Clicar num chip → vista de detalhe com todos os resultados + link PDF.
    Voltar → volta ao gráfico.
    """
    import webbrowser

    historicos = [(ex, ex.get("historico", []))
                  for ex in exames_selecionados if ex.get("historico")]
    if not historicos:
        return ft.Text("Nenhum dado para exibir.", size=12, color=_MUT)

    grafico_ctrl = gerar_grafico_flet(historicos)

    def _fazer_chip(idx, ex, hist):
        cor  = CORES_EXAME[idx % len(CORES_EXAME)]
        nome = ex.get("nome_oficial", "")
        uni  = ex.get("unidade", "")

        chip = ft.Container(
            content=ft.Row([
                ft.Container(width=10, height=10, bgcolor=cor, border_radius=2),
                ft.Text(nome, size=11, color=_TXT, weight=ft.FontWeight.W_500),
                ft.Text(f"[{uni}]" if uni else "", size=9, color=_MUT),
                ft.Icon("chevron_right_rounded", size=12, color=cor),
            ], spacing=5, tight=True),
            bgcolor=_CARD, border_radius=16,
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            border=ft.Border(
                top=ft.BorderSide(1, cor + "66"),
                bottom=ft.BorderSide(1, cor + "66"),
                left=ft.BorderSide(2, cor),
                right=ft.BorderSide(1, cor + "66"),
            ),
            ink=True,
        )
        chip.on_click = lambda e, _ex=ex, _h=hist, _c=cor: _mostrar_detalhe(_ex, _h, _c)
        return chip

    chips_legenda = ft.Row(
        controls=[_fazer_chip(i, ex, hist) for i, (ex, hist) in enumerate(historicos)],
        spacing=8, wrap=True,
    )

    vista_grafico = ft.Column([
        grafico_ctrl,
        ft.Container(
            content=ft.Column([
                ft.Text("Clique num exame para ver os detalhes:",
                        size=10, color=_MUT),
                chips_legenda,
            ], spacing=6),
            padding=ft.padding.symmetric(horizontal=4, vertical=6),
        ),
    ], spacing=6, visible=True)

    detalhe_col = ft.Column(spacing=10, visible=False)

    def _voltar_grafico():
        detalhe_col.visible   = False
        vista_grafico.visible = True
        try: page.update()
        except Exception: pass

    def _mostrar_detalhe(ex, hist, cor):
        from datetime import datetime as _dt

        nome    = ex.get("nome_oficial", "")
        unidade = ex.get("unidade", "")

        def _pd(d):
            for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                try: return _dt.strptime((d or "")[:10], fmt)
                except: pass
            return _dt.min

        entradas = sorted(
            [h for h in hist if h.get("valor") and h.get("data")],
            key=lambda h: _pd(h["data"]), reverse=True,
        )

        detalhe_col.controls.clear()

        btn_voltar = ft.Container(
            content=ft.Row([
                ft.Icon("arrow_back_rounded", size=14, color=_SEC),
                ft.Text("Voltar ao gráfico", size=12, color=_SEC),
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
                ft.Text(nome, size=14, color=_TXT, weight=ft.FontWeight.W_700),
                ft.Text(f"[{unidade}]" if unidade else "", size=11, color=_MUT),
            ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

        detalhe_col.controls.append(
            ft.Text(f"{len(entradas)} resultado(s) — mais recente primeiro",
                    size=10, color=_MUT))

        for h in entradas:
            nivel = h.get("nivel", "sem_referencia")
            cor_n = NIVEL_COR.get(nivel, "#58A6FF")
            label = NIVEL_LABEL.get(nivel, "?")
            uni   = h.get("unidade") or unidade
            ref   = h.get("referencia") or "—"
            lab   = h.get("laboratorio") or ""
            did   = h.get("drive_id") or ""

            d_raw = (h.get("data") or "")[:10]
            if len(d_raw) == 10 and d_raw[4] == "-":
                try:
                    d_raw = _dt.strptime(d_raw, "%Y-%m-%d").strftime("%d/%m/%Y")
                except Exception:
                    pass

            btn_pdf = ft.Container(
                content=ft.Row([
                    ft.Icon("picture_as_pdf_rounded", size=13, color="#FF4444"),
                    ft.Text("Ver PDF", size=11, color="#58A6FF"),
                ], spacing=4, tight=True),
                bgcolor=_BG, border_radius=6,
                padding=ft.padding.symmetric(horizontal=8, vertical=5),
                border=ft.border.all(1, _BD),
                ink=True, visible=bool(did),
            )
            if did:
                btn_pdf.on_click = lambda e, d=did: webbrowser.open(
                    f"https://drive.google.com/file/d/{d}/view")

            detalhe_col.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(d_raw, size=11, color=_SEC),
                        ft.Container(expand=True),
                        btn_pdf,
                    ]),
                    ft.Container(height=6),
                    ft.Row([
                        ft.Column([
                            ft.Text("Valor", size=9, color=_MUT),
                            ft.Row([
                                ft.Text(str(h.get("valor", "")), size=22,
                                        color=cor_n, weight=ft.FontWeight.W_700),
                                ft.Text(uni, size=11, color=_MUT),
                            ], spacing=4,
                               vertical_alignment=ft.CrossAxisAlignment.END),
                        ], spacing=1),
                        ft.VerticalDivider(color=_BD, width=24),
                        ft.Column([
                            ft.Text("Referência", size=9, color=_MUT),
                            ft.Text(ref, size=11, color=_SEC),
                        ], spacing=1),
                        ft.VerticalDivider(color=_BD, width=24),
                        ft.Column([
                            ft.Text("Nível", size=9, color=_MUT),
                            ft.Text(label, size=12, color=cor_n,
                                    weight=ft.FontWeight.W_600),
                        ], spacing=1),
                    ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(height=4),
                    ft.Text(lab, size=9, color="#58A6FF"),
                ], spacing=0),
                bgcolor=_CARD, border_radius=8, padding=ft.padding.all(14),
                border=ft.Border(
                    left=ft.BorderSide(3, cor_n),
                    top=ft.BorderSide(1, _BD),
                    bottom=ft.BorderSide(1, _BD),
                    right=ft.BorderSide(1, _BD),
                ),
            ))

        vista_grafico.visible = False
        detalhe_col.visible   = True
        try: page.update()
        except Exception: pass

    return ft.Column([vista_grafico, detalhe_col], spacing=0)
