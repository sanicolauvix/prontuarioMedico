# -*- coding: utf-8 -*-
"""
tela_exames_por_grupo.py
Lista os exames do paciente filtrados por grupo_id.
"""
import flet as ft
import sqlite3

from dados.model_prontuario import DB_PATH

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; AMAR = "#D29922"
VERM = "#DA3633"


def criar_tela_exames_por_grupo(
    page: ft.Page,
    grupo_id: int,
    grupo_nome: str,
    grupo_cor: str = "#58A6FF",
    voltar_fn=None,
) -> ft.Column:

    lista   = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
    txt_sub = ft.Text("", size=12, color=SEC)

    def _voltar(e=None):
        if voltar_fn:
            voltar_fn()

    def _abrir_exame(exame_id):
        from telas.tela_exames_processados import criar_tela_exames_processados
        nova = criar_tela_exames_processados(
            page, exame_id=exame_id, voltar_fn=lambda: _recarregar()
        )
        page.controls.clear()
        page.controls.append(nova)
        try: page.update()
        except Exception: pass

    def _recarregar():
        page.controls.clear()
        page.controls.append(
            criar_tela_exames_por_grupo(
                page, grupo_id, grupo_nome, grupo_cor, voltar_fn
            )
        )
        try: page.update()
        except Exception: pass

    def carregar():
        lista.controls.clear()
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row

        exames = conn.execute("""
            SELECT e.id, e.tipo_exame, e.laboratorio, e.data_exame,
                   p.nome as paciente,
                   COUNT(er.id) as n_resultados
            FROM exames e
            LEFT JOIN pacientes p ON p.id = e.paciente_id
            LEFT JOIN exame_resultados er ON er.exame_id = e.id
            WHERE e.grupo_id = ?
            GROUP BY e.id
            ORDER BY e.data_exame DESC
        """, (grupo_id,)).fetchall()

        conn.close()

        txt_sub.value = (
            f"{len(exames)} exame(s) neste grupo" if exames
            else "Nenhum exame neste grupo ainda"
        )

        if not exames:
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("inbox_rounded", size=44, color=MUT),
                    ft.Text("Nenhum exame neste grupo.", size=14, color=SEC),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                alignment=ft.alignment.Alignment(0, 0),
                padding=60,
            ))
            try: page.update()
            except Exception: pass
            return

        for ex in exames:
            data_fmt = str(ex["data_exame"] or "")[:10]
            # Formatar DD/MM/AAAA
            if len(data_fmt) == 10 and data_fmt[4] == "-":
                data_fmt = f"{data_fmt[8:10]}/{data_fmt[5:7]}/{data_fmt[:4]}"

            n = ex["n_resultados"]
            cor_n = VERD if n > 0 else MUT

            card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("science_rounded", size=14, color=grupo_cor),
                        ft.Text(
                            ex["tipo_exame"] or "Exame",
                            size=13, color=TXT,
                            weight=ft.FontWeight.W_600,
                            expand=True,
                            no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(data_fmt, size=11, color=AMAR,
                                weight=ft.FontWeight.W_600),
                    ], spacing=8,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row([
                        ft.Text(ex["laboratorio"] or "Lab desconhecido",
                                size=11, color=SEC),
                        ft.Container(expand=True),
                        ft.Container(
                            content=ft.Text(
                                f"{n} resultado(s)" if n else "Sem resultados",
                                size=10, color=cor_n,
                                weight=ft.FontWeight.W_600,
                            ),
                            bgcolor=ft.Colors.with_opacity(0.15, cor_n),
                            border_radius=8,
                            padding=ft.padding.symmetric(horizontal=7, vertical=2),
                        ),
                    ], spacing=6,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ], spacing=6),
                bgcolor=CARD,
                border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                border=ft.Border(
                    left=ft.BorderSide(3, grupo_cor),
                    top=ft.BorderSide(1, BD),
                    bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
                ink=True,
            )
            card.on_click = lambda e, eid=ex["id"]: _abrir_exame(eid)
            lista.controls.append(card)

        try: page.update()
        except Exception: pass

    carregar()

    return ft.Column([
        # Cabeçalho
        ft.Row([
            ft.Container(
                content=ft.Row([
                    ft.Icon("arrow_back_rounded", size=14, color=SEC),
                    ft.Text("Voltar", size=12, color=SEC),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                ink=True, on_click=_voltar,
            ),
            ft.Container(expand=True),
            ft.Icon("bloodtype_rounded", size=16, color=grupo_cor),
            ft.Text(grupo_nome, size=16, color=TXT,
                    weight=ft.FontWeight.W_700),
            ft.Container(expand=True),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),

        ft.Divider(color=BD, height=1),
        ft.Container(height=2),
        txt_sub,
        ft.Container(height=4),
        lista,
    ], spacing=6, expand=True)
