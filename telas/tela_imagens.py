# -*- coding: utf-8 -*-
"""
tela_imagens.py -- Koios Prontuario
Reusa toda a logica de tela_sangue, filtrando grupos tipo IN ('imagem','outros').
"""
import flet as ft
import sqlite3

from dados.model_prontuario import DB_PATH

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; AMAR = "#D29922"
VERM = "#DA3633"; COR  = "#7EE8FA"   # ciano para diferenciar de sangue


def criar_tela_imagens(page: ft.Page, voltar_fn=None) -> ft.Column:
    from telas.tela_sangue import _montar_exame_selecionado

    _nivel        = [0]
    _grupo_atual  = [None, None]
    _selecionados = set()

    titulo    = ft.Text("Exames (outros)", size=18, color=TXT,
                        weight=ft.FontWeight.W_700)
    subtitulo = ft.Text("", size=12, color=SEC)
    area      = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    def _voltar_grupos(e=None):
        _nivel[0] = 0
        _grupo_atual[0] = _grupo_atual[1] = None
        _selecionados.clear()
        titulo.value    = "Exames (outros)"
        subtitulo.value = ""
        _renderizar_grupos()

    # -- Nivel 1: grupos --------------------------------------------------
    def _renderizar_grupos():
        area.controls.clear()
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            grupos = conn.execute("""
                SELECT g.id, g.nome, g.icone, g.descricao,
                       COUNT(e.id) as n_exames
                FROM grupos_exame g
                LEFT JOIN exames e ON e.grupo_id = g.id
                WHERE g.tipo IN ('imagem','outros') AND g.ativo = 1
                GROUP BY g.id ORDER BY g.ordem
            """).fetchall()
            conn.close()
        except Exception:
            grupos = []

        subtitulo.value = f"{len(grupos)} grupos"

        for gid, gnome, gicone, gdesc, n in grupos:
            cor_brd = COR if n > 0 else MUT
            card = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(gicone or "image_search_rounded",
                                        size=22, color=COR),
                        bgcolor=ft.Colors.with_opacity(0.12, COR),
                        border_radius=10, width=44, height=44,
                        alignment=ft.alignment.Alignment(0, 0),
                    ),
                    ft.Column([
                        ft.Text(gnome, size=14, color=TXT,
                                weight=ft.FontWeight.W_600),
                        ft.Text(gdesc or "", size=11, color=SEC,
                                no_wrap=True,
                                overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(
                            f"{n} exame(s)" if n else "Nenhum exame ainda",
                            size=11, color=VERD if n > 0 else MUT,
                        ),
                    ], spacing=2, expand=True),
                    ft.Icon("chevron_right_rounded", size=18, color=MUT),
                ], spacing=14,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=16, vertical=14),
                border=ft.Border(
                    left=ft.BorderSide(3, cor_brd),
                    top=ft.BorderSide(1, BD),
                    bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
                ink=True,
            )
            card.on_click = lambda e, i=gid, n=gnome: _abrir_grupo(i, n)
            area.controls.append(card)

        try: page.update()
        except Exception: pass

    # -- Nivel 2: parametros do grupo -------------------------------------
    def _abrir_grupo(grupo_id, grupo_nome):
        _nivel[0]       = 1
        _grupo_atual[0] = grupo_id
        _grupo_atual[1] = grupo_nome
        titulo.value = grupo_nome
        _carregar_params(grupo_id, selecionar_primeiro=True)

    def _carregar_params(grupo_id, selecionar_primeiro=False):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            params = conn.execute("""
                SELECT DISTINCT COALESCE(ep.nome_oficial, er.parametro) AS nome
                FROM exame_resultados er
                JOIN exames e ON e.id = er.exame_id
                LEFT JOIN exames_padrao ep ON ep.id = er.exame_padrao_id
                WHERE er.grupo_id = ?
                  AND (e.status IS NULL OR e.status NOT IN ('rascunho','revisao'))
                ORDER BY nome
            """, (grupo_id,)).fetchall()
            conn.close()
        except Exception:
            params = []

        if not params:
            area.controls.clear()
            subtitulo.value = "Nenhum resultado neste grupo"
            area.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("inbox_rounded", size=48, color=MUT),
                    ft.Text("Nenhum resultado neste grupo.", size=14, color=SEC),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                alignment=ft.alignment.Alignment(0, 0), padding=60,
            ))
            try: page.update()
            except Exception: pass
            return

        if selecionar_primeiro or not _selecionados:
            _selecionados.clear()
            _selecionados.add(params[0][0])

        titulo.value = _grupo_atual[1] or "Exames (outros)"
        _renderizar_nivel2(params, grupo_id)

    grafico_container = ft.Container(expand=False)

    def _atualizar_grafico():
        from shared.grafico import renderizar_grafico_combinado
        exames = [_montar_exame_selecionado(n) for n in sorted(_selecionados)]
        exames = [e for e in exames if e]
        if exames:
            grafico_container.content = renderizar_grafico_combinado(page, exames)
        else:
            grafico_container.content = ft.Container(
                content=ft.Column([
                    ft.Icon("bar_chart_rounded", size=36, color=MUT),
                    ft.Text("Selecione ao menos um parametro.", size=12, color=MUT),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                alignment=ft.alignment.Alignment(0, 0), padding=30,
            )
        try: page.update()
        except Exception: pass

    def _renderizar_nivel2(params, grupo_id):
        area.controls.clear()
        n_sel = len(_selecionados)
        subtitulo.value = f"{len(params)} parametro(s) -- {n_sel} selecionado(s)"

        _atualizar_grafico()
        area.controls.append(grafico_container)
        area.controls.append(ft.Divider(color=BD, height=1))
        area.controls.append(ft.Text(
            "Toque para selecionar/deselecionar -- multiplos no mesmo grafico",
            size=10, color=MUT, text_align=ft.TextAlign.CENTER,
        ))

        # batch de niveis
        _niveis = {}
        try:
            _cn = sqlite3.connect(DB_PATH, timeout=10)
            _nn = [p[0] for p in params]
            _rn = _cn.execute(f"""
                SELECT COALESCE(ep.nome_oficial, er.parametro), er.nivel_interpretacao
                FROM exame_resultados er
                JOIN exames e ON e.id = er.exame_id
                LEFT JOIN exames_padrao ep ON ep.id = er.exame_padrao_id
                WHERE UPPER(COALESCE(ep.nome_oficial, er.parametro)) IN
                      ({",".join("UPPER(?)" for _ in _nn)})
                  AND er.nivel_interpretacao IS NOT NULL
                  AND (e.status IS NULL OR e.status NOT IN ('rascunho','revisao'))
                ORDER BY e.data_exame DESC
            """, _nn).fetchall()
            _cn.close()
            for _n2, _niv in _rn:
                if _n2 not in _niveis: _niveis[_n2] = _niv
        except Exception:
            pass

        _COR_NIVEL = {
            "critico_baixo": "#FF4444", "baixo": "#F0883E",
            "alto": "#F0883E", "critico_alto": "#FF4444", "otimo": "#3FB950",
        }

        for (nome,) in params:
            sel     = nome in _selecionados
            cor_brd = COR if sel else BD
            cor_txt = TXT if sel else SEC
            peso    = ft.FontWeight.W_600 if sel else ft.FontWeight.W_400

            nivel_ult = _niveis.get(nome)
            cor_nivel = _COR_NIVEL.get(nivel_ult)
            badge_nivel = ft.Container(
                content=ft.Icon(
                    "warning_rounded" if nivel_ult in ("critico_alto","critico_baixo")
                    else "arrow_upward_rounded" if nivel_ult == "alto"
                    else "arrow_downward_rounded" if nivel_ult == "baixo"
                    else "check_circle_outline_rounded",
                    size=12, color=cor_nivel,
                ),
                tooltip=nivel_ult, visible=bool(cor_nivel),
            )

            checkbox = ft.Checkbox(
                value=sel,
                fill_color=ft.Colors.with_opacity(0.8, COR),
                check_color=BG,
                active_color=COR,
            )

            btn_hist = ft.Container(
                content=ft.Icon("arrow_forward_ios_rounded", size=13, color=COR),
                padding=ft.padding.symmetric(horizontal=8, vertical=6),
                border_radius=6,
                bgcolor=ft.Colors.with_opacity(0.10, COR),
                ink=True,
                tooltip="Ver historico completo",
            )

            card = ft.Container(
                content=ft.Row([
                    checkbox,
                    ft.Icon("show_chart_rounded", size=14,
                            color=COR if sel else MUT),
                    ft.Text(nome, size=13, color=cor_txt,
                            weight=peso, expand=True),
                    badge_nivel,
                    btn_hist,
                ], spacing=10,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=ft.Colors.with_opacity(0.08, COR) if sel else CARD,
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=10),
                border=ft.Border(
                    left=ft.BorderSide(3, cor_brd),
                    top=ft.BorderSide(1, BD),
                    bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
                ink=True,
            )

            def _toggle(e, _n=nome, _params=params, _gid=grupo_id):
                if _n in _selecionados:
                    if len(_selecionados) > 1:
                        _selecionados.discard(_n)
                else:
                    _selecionados.add(_n)
                _renderizar_nivel2(_params, _gid)

            def _abrir_historico(e, _n=nome):
                from telas.tela_historico_parametro import criar_tela_historico_parametro

                def _voltar_hist():
                    page.controls.clear()
                    page.controls.append(_tela)
                    try: page.update()
                    except Exception: pass

                nova = criar_tela_historico_parametro(
                    page, param_nome=_n, voltar_fn=_voltar_hist,
                    grupo_nome=_grupo_atual[1],
                    param_nomes=[p[0] for p in params])
                page.controls.clear()
                page.controls.append(nova)
                try: page.update()
                except Exception: pass

            card.on_click = _toggle
            checkbox.on_change = _toggle
            btn_hist.on_click = _abrir_historico
            area.controls.append(card)

        try: page.update()
        except Exception: pass

    # -- carga inicial ----------------------------------------------------
    _renderizar_grupos()

    # -- tela -------------------------------------------------------------
    from shared.layout import Layout
    lay = Layout(page)

    _tela = ft.Container(
        bgcolor=BG, expand=True,
        content=ft.Column([
            ft.Container(height=lay.spacer_topo, bgcolor=BG),
            ft.Row([
                ft.Container(
                    content=ft.Row([
                        ft.Icon("arrow_back_rounded", size=14, color=SEC),
                        ft.Text("Voltar", size=12, color=SEC),
                    ], spacing=4, tight=True),
                    padding=ft.padding.symmetric(horizontal=8, vertical=8),
                    border_radius=8, ink=True,
                    on_click=lambda e: (
                        _voltar_grupos() if _nivel[0] == 1
                        else (voltar_fn() if voltar_fn else None)
                    ),
                ),
                ft.Container(expand=True),
                ft.Icon("image_search_rounded", size=16, color=COR),
                ft.Container(width=6),
                titulo,
                ft.Container(expand=True),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Divider(color=BD, height=1),
            subtitulo,
            ft.Container(height=4),
            ft.Container(
                content=area,
                padding=ft.padding.symmetric(horizontal=12),
                expand=True,
            ),
        ], spacing=6, expand=True),
    )

    return _tela
