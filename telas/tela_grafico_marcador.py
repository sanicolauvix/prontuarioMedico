# -*- coding: utf-8 -*-
# Prontuario | telas/tela_grafico_marcador.py
import flet as ft
import logging
import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from shared.layout import Layout

BG    = "#0D1117"; CARD  = "#161B22"; BD   = "#21262D"; BORDA2 = "#30363D"
TXT   = "#E6EDF3"; SEC   = "#8B949E"; MUT  = "#484F58"
AZUL  = "#58A6FF"; VERD  = "#3FB950"; VERM = "#F85149"; AMAR = "#D29922"

log = logging.getLogger(__name__)


def criar_tela_grafico_marcador(
    page: ft.Page,
    voltar_fn,
    label: str,
    termos: list,
    cor: str,
) -> ft.Container:
    lay      = Layout(page)
    area     = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
    _montado = [False]

    def _rebuild():
        area.controls.clear()

        import sqlite3
        from dados.model_prontuario import DB_PATH

        # Coleta todos os pontos de ambas as fontes
        pontos = []  # list of (date_str, float_val, unit_str)
        try:
            conn = sqlite3.connect(DB_PATH, timeout=30)
            try:
                for termo in termos:
                    rows = conn.execute("""
                        SELECT r.valor, r.unidade, e.data_exame
                        FROM resultados_estruturados r
                        JOIN exames e ON r.exame_id = e.id
                        WHERE LOWER(r.parametro) LIKE ?
                          AND r.valor IS NOT NULL AND r.valor != ''
                        ORDER BY e.data_exame ASC
                    """, (f"%{termo}%",)).fetchall()
                    for (v, u, d) in rows:
                        try:
                            pontos.append((d or "", float(str(v).replace(",", ".")), u or ""))
                        except Exception:
                            pass
                    try:
                        rows2 = conn.execute("""
                            SELECT CAST(valor AS TEXT), unidade, data_medicao
                            FROM marcadores_leituras
                            WHERE LOWER(parametro) LIKE ?
                            ORDER BY data_medicao ASC
                        """, (f"%{termo}%",)).fetchall()
                        for (v, u, d) in rows2:
                            try:
                                pontos.append((d or "", float(str(v).replace(",", ".")), u or ""))
                            except Exception:
                                pass
                    except Exception:
                        pass
                    if pontos:
                        break
            finally:
                conn.close()
        except Exception as ex:
            log.warning("[GRAFICO %s] %s", label, ex)

        # Ordena por data, mantém ultimos 30
        pontos.sort(key=lambda x: x[0])
        pontos = pontos[-30:]

        if not pontos:
            area.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon("bar_chart_rounded", size=48, color=MUT),
                        ft.Text("Sem dados registrados", size=14, color=MUT),
                        ft.Text(
                            "Inclua exames ou leituras manuais para\nver o histórico aqui.",
                            size=12, color=MUT, text_align=ft.TextAlign.CENTER,
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
                    alignment=ft.alignment.center,
                    padding=ft.padding.all(40),
                )
            )
            if _montado[0]:
                try: page.update()
                except Exception: pass
            return

        vals      = [p[1] for p in pontos]
        unit      = next((p[2] for p in reversed(pontos) if p[2]), "")
        last_val  = vals[-1]
        last_date = pontos[-1][0][:10] if pontos[-1][0] else "--"
        if len(last_date) >= 10:
            last_date = f"{last_date[8:10]}/{last_date[5:7]}/{last_date[2:4]}"
        media = sum(vals) / len(vals)
        min_v = min(vals)
        max_v = max(vals)

        # Labels do eixo X
        n      = len(pontos)
        step   = max(1, n // 5)
        ax_lbs = []
        for i, (d, v, u) in enumerate(pontos):
            if i == 0 or i == n - 1 or i % step == 0:
                dl = d[:10] if d and len(d) >= 10 else ""
                dl_fmt = f"{dl[8:10]}/{dl[5:7]}" if len(dl) >= 10 else str(i)
                ax_lbs.append(
                    ft.ChartAxisLabel(
                        value=float(i),
                        label=ft.Text(dl_fmt, size=8, color=MUT),
                    )
                )

        padding_y = max((max_v - min_v) * 0.12, 1.0)
        interval_y = max((max_v - min_v) / 4.0, 0.1) if max_v != min_v else 1.0

        chart = ft.LineChart(
            data_series=[
                ft.LineChartData(
                    data_points=[
                        ft.LineChartDataPoint(x=float(i), y=v)
                        for i, (d, v, u) in enumerate(pontos)
                    ],
                    stroke_width=2.5,
                    color=cor,
                    curved=True,
                    stroke_cap_round=True,
                    below_line_bgcolor=f"{cor}1A",
                ),
            ],
            border=ft.border.all(1, BD),
            horizontal_grid_lines=ft.ChartGridLines(
                interval=interval_y, color=BORDA2, width=0.5,
            ),
            left_axis=ft.ChartAxis(labels_size=44),
            bottom_axis=ft.ChartAxis(labels=ax_lbs, labels_size=24),
            min_y=min_v - padding_y,
            max_y=max_v + padding_y,
            expand=True,
            animate=500,
        )

        # Card ultimo valor + media
        card_topo = ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text("Último valor", size=10, color=MUT),
                    ft.Row([
                        ft.Text(
                            f"{last_val:.1f}",
                            size=32,
                            weight=ft.FontWeight.W_900,
                            color=cor,
                        ),
                        ft.Text(unit, size=12, color=SEC),
                    ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.END),
                    ft.Text(last_date, size=11, color=SEC),
                ], spacing=2, expand=True),
                ft.VerticalDivider(width=1, color=BD),
                ft.Column([
                    ft.Text("Média", size=10, color=MUT,
                            text_align=ft.TextAlign.RIGHT),
                    ft.Text(
                        f"{media:.1f}",
                        size=26,
                        weight=ft.FontWeight.W_700,
                        color=SEC,
                        text_align=ft.TextAlign.RIGHT,
                    ),
                    ft.Text(
                        f"{len(vals)} exames",
                        size=10, color=MUT, text_align=ft.TextAlign.RIGHT,
                    ),
                ], spacing=2,
                   horizontal_alignment=ft.CrossAxisAlignment.END,
                   expand=True),
            ], spacing=16),
            bgcolor=CARD,
            border_radius=12,
            padding=ft.padding.all(16),
            border=ft.border.all(1, f"{cor}44"),
        )

        # Stats
        def _stat(titulo, valor_str, stat_cor):
            return ft.Container(
                content=ft.Column([
                    ft.Text(titulo, size=9, color=MUT,
                            text_align=ft.TextAlign.CENTER),
                    ft.Text(valor_str, size=14,
                            weight=ft.FontWeight.W_700,
                            color=stat_cor,
                            text_align=ft.TextAlign.CENTER),
                ], spacing=2, tight=True,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=f"{stat_cor}11",
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border=ft.border.all(1, f"{stat_cor}33"),
                expand=True,
            )

        stats_row = ft.Row([
            _stat("Mínimo", f"{min_v:.1f}", AZUL),
            _stat("Máximo", f"{max_v:.1f}", AMAR),
            _stat("Pontos", str(len(vals)), SEC),
        ], spacing=8)

        chart_wrap = ft.Container(
            content=chart,
            bgcolor=CARD,
            border_radius=12,
            padding=ft.padding.all(10),
            border=ft.border.all(1, BD),
            height=220,
        )

        area.controls.extend([card_topo, chart_wrap, stats_row])

        if _montado[0]:
            try: page.update()
            except Exception: pass

    _rebuild()

    cabecalho = lay.criar_cabecalho(
        label, voltar_fn,
        icone_titulo="bar_chart_rounded",
        cor_titulo=cor,
    )
    corpo     = lay.criar_corpo(cabecalho, area)
    _montado[0] = True
    return ft.Container(bgcolor=BG, expand=True, content=corpo)
