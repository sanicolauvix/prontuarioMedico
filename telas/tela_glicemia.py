# -*- coding: utf-8 -*-
# Prontuario | telas/tela_glicemia.py -- Glicemia no padrao tela_sangue
import flet as ft
import sqlite3

from dados.model_prontuario import DB_PATH

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
VERD = "#3FB950"; VERM = "#DA3633"; COR = "#FF6B6B"

# Dois grupos fixos de glicemia — filtragem por nome_oficial
_GRUPOS_GLIC = [
    {
        "id":     "direta",
        "nome":   "Glicose Direta",
        "icone":  "water_drop_rounded",
        "desc":   "Glicemia de jejum, pos-prandial, dextrosol",
        "nomes":  {
            "glicose", "glicemia", "glicemia de jejum", "glicose em jejum",
            "glicemia media estimada", "glicemia 1h pos-dextrosol",
            "glicemia 2h pos-dextrosol", "glicemia pos-prandial",
        },
    },
    {
        "id":     "controle",
        "nome":   "Controle Glicemico",
        "icone":  "monitor_heart_rounded",
        "desc":   "HbA1c, insulina, HOMA-IR, frutosamina",
        "nomes":  {
            "hemoglobina glicada", "hemoglobina glicada (hba1c)",
            "insulina", "insulina basal", "homa-ir", "frutosamina",
            "glicemia media estimada",
        },
    },
]


def _montar_exame_selecionado(param_nome: str) -> dict | None:
    """
    Igual a tela_sangue mas inclui tambem marcadores_leituras (medicoes caseiras)
    unificadas pelo mesmo nome de parametro.
    """
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)

        rows_lab = conn.execute("""
            SELECT er.valor, er.unidade, e.data_exame, er.referencia,
                   er.nivel_interpretacao,
                   COALESCE(ep.nome_oficial, er.parametro),
                   COALESCE(ep.unidade, er.unidade),
                   COALESCE(e.laboratorio, '')
            FROM exame_resultados er
            JOIN exames e ON e.id = er.exame_id
            LEFT JOIN exames_padrao ep ON ep.id = er.exame_padrao_id
            WHERE UPPER(COALESCE(ep.nome_oficial, er.parametro)) = UPPER(?)
              AND er.valor IS NOT NULL AND er.valor != ''
              AND (e.status IS NULL OR e.status NOT IN ('rascunho','revisao'))
        """, (param_nome,)).fetchall()

        rows_cas = conn.execute("""
            SELECT valor, unidade, data_medicao, referencia,
                   NULL, parametro, unidade, 'Caseiro'
            FROM marcadores_leituras
            WHERE UPPER(parametro) = UPPER(?)
        """, (param_nome,)).fetchall()

        conn.close()
    except Exception:
        return None

    todas = rows_lab + rows_cas
    if not todas:
        return None

    def _dt(r):
        from datetime import datetime
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try: return datetime.strptime((r[2] or "")[:10], fmt)
            except: pass
        from datetime import datetime as _dt2
        return _dt2.min

    todas.sort(key=_dt)

    nome_oficial = rows_lab[0][5] if rows_lab else param_nome
    unidade      = rows_lab[0][6] if rows_lab else (str(rows_cas[0][1]) if rows_cas else "mg/dL")

    historico = [
        {
            "valor":       str(r[0]),
            "unidade":     r[1] or unidade,
            "data":        r[2] or "",
            "referencia":  r[3] or "",
            "nivel":       r[4] or "sem_referencia",
            "laboratorio": r[7] or "",
        }
        for r in todas
    ]

    return {"nome_oficial": nome_oficial, "unidade": unidade, "historico": historico}


def criar_tela_glicemia(page: ft.Page, voltar_fn=None) -> ft.Column:

    _nivel       = [0]
    _grupo_atual = [None]   # dict do _GRUPOS_GLIC
    _selecionados = set()

    titulo    = ft.Text("Glicemia", size=18, color=TXT,
                        weight=ft.FontWeight.W_700)
    subtitulo = ft.Text("", size=12, color=SEC)
    area      = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    def _voltar_grupos(e=None):
        _nivel[0] = 0
        _grupo_atual[0] = None
        _selecionados.clear()
        titulo.value    = "Glicemia"
        subtitulo.value = ""
        _renderizar_grupos()

    # -- Nivel 1: dois grupos fixos -----------------------------------
    def _renderizar_grupos():
        area.controls.clear()

        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            # conta quantos resultados existem para cada conjunto de nomes
            contagens = {}
            for g in _GRUPOS_GLIC:
                placeholders = ",".join("?" * len(g["nomes"]))
                row = conn.execute(f"""
                    SELECT COUNT(DISTINCT er.id)
                    FROM exame_resultados er
                    JOIN exames e ON e.id = er.exame_id
                    LEFT JOIN exames_padrao ep ON ep.id = er.exame_padrao_id
                    WHERE LOWER(COALESCE(ep.nome_oficial, er.parametro)) IN ({placeholders})
                      AND (e.status IS NULL OR e.status NOT IN ('rascunho','revisao'))
                """, list(g["nomes"])).fetchone()
                contagens[g["id"]] = row[0] if row else 0
            conn.close()
        except Exception:
            contagens = {g["id"]: 0 for g in _GRUPOS_GLIC}

        subtitulo.value = "2 grupos"

        for g in _GRUPOS_GLIC:
            n       = contagens.get(g["id"], 0)
            cor_brd = COR if n > 0 else MUT
            card = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(g["icone"], size=22, color=COR),
                        bgcolor=ft.Colors.with_opacity(0.12, COR),
                        border_radius=10, width=44, height=44,
                        alignment=ft.alignment.Alignment(0, 0),
                    ),
                    ft.Column([
                        ft.Text(g["nome"], size=14, color=TXT,
                                weight=ft.FontWeight.W_600),
                        ft.Text(g["desc"], size=11, color=SEC,
                                no_wrap=True,
                                overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(
                            f"{n} resultado(s)" if n else "Nenhum resultado ainda",
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
            card.on_click = lambda e, _g=g: _abrir_grupo(_g)
            area.controls.append(card)

        try: page.update()
        except Exception: pass

    # -- Nivel 2: parametros do grupo ---------------------------------
    def _abrir_grupo(g):
        _nivel[0]       = 1
        _grupo_atual[0] = g
        titulo.value    = g["nome"]
        _carregar_params(g, selecionar_primeiro=True)

    def _carregar_params(g, selecionar_primeiro=False):
        nomes = g["nomes"]
        placeholders = ",".join("?" * len(nomes))
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            params = conn.execute(f"""
                SELECT DISTINCT COALESCE(ep.nome_oficial, er.parametro) AS nome
                FROM exame_resultados er
                JOIN exames e ON e.id = er.exame_id
                LEFT JOIN exames_padrao ep ON ep.id = er.exame_padrao_id
                WHERE LOWER(COALESCE(ep.nome_oficial, er.parametro)) IN ({placeholders})
                  AND (e.status IS NULL OR e.status NOT IN ('rascunho','revisao'))
                ORDER BY nome
            """, list(nomes)).fetchall()
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

        titulo.value = g["nome"]
        _renderizar_nivel2(params, g)

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

    # -- Form rapido: nova medicao caseira ----------------------------
    def _abrir_form_caseiro(on_salvo):
        import datetime
        from shared.date_field import campo_data
        from dados.model_prontuario import normalizar_data

        _MOMENTOS = [
            ("Jejum",       "70 - 99",  "Glicemia de Jejum"),
            ("Apos 1h",     "< 180",    "Glicemia 1h Pos-Dextrosol"),
            ("Apos 2h",     "< 140",    "Glicemia 2h Pos-Dextrosol"),
            ("Pos-Prandial","< 140",    "Glicemia Pos-Prandial"),
            ("Aleatoria",   "70 - 140", "Glicemia de Jejum"),
        ]

        ref_ov = [None]

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        tf_valor = ft.TextField(
            label="Glicemia (mg/dL)",
            bgcolor=CARD, border_color=BD, focused_border_color=COR,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, keyboard_type=ft.KeyboardType.NUMBER,
            autofocus=True,
        )
        dd_momento = ft.Dropdown(
            label="Momento",
            bgcolor=CARD, border_color=BD, focused_border_color=COR,
            label_style=ft.TextStyle(color=SEC),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, value="Jejum",
            options=[ft.dropdown.Option(m[0]) for m in _MOMENTOS],
        )
        row_data, tf_data = campo_data(
            page, "Data",
            value=datetime.date.today().strftime("%d/%m/%Y"),
            cor_acento=COR, bgcolor=CARD, border_color=BD,
        )
        txt_erro = ft.Text("", size=11, color=VERM, visible=False)

        def _salvar(e=None):
            val_str = (tf_valor.value or "").strip().replace(",", ".")
            if not val_str:
                txt_erro.value = "Informe o valor."
                txt_erro.visible = True
                try: page.update()
                except Exception: pass
                return
            try:
                val_num = float(val_str)
            except ValueError:
                txt_erro.value = "Valor invalido."
                txt_erro.visible = True
                try: page.update()
                except Exception: pass
                return

            momento = dd_momento.value or "Jejum"
            ref_str, param_nome = next(
                ((m[1], m[2]) for m in _MOMENTOS if m[0] == momento),
                ("70 - 99", "Glicose em Jejum"),
            )
            data_iso = normalizar_data(tf_data.value) or datetime.date.today().isoformat()

            try:
                conn = sqlite3.connect(DB_PATH, timeout=10)
                # cria registro pai em exames
                conn.execute("""
                    INSERT INTO exames
                        (tipo, tipo_exame, data_exame, laboratorio, status, grupo_id)
                    VALUES ('laboratorial', 'Glicemia Caseira', ?, 'Caseiro', 'ok', 2)
                """, (data_iso,))
                exame_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                # busca exame_padrao_id
                row = conn.execute(
                    "SELECT id FROM exames_padrao WHERE LOWER(nome_oficial) = LOWER(?)",
                    (param_nome,)
                ).fetchone()
                ep_id = row[0] if row else None
                conn.execute("""
                    INSERT INTO exame_resultados
                        (exame_id, parametro, valor, unidade, referencia,
                         exame_padrao_id, grupo_id)
                    VALUES (?, ?, ?, 'mg/dL', ?, ?, 2)
                """, (exame_id, param_nome, str(val_num), ref_str, ep_id))
                conn.commit()
                conn.close()
            except Exception as ex:
                txt_erro.value = f"Erro: {ex}"
                txt_erro.visible = True
                try: page.update()
                except Exception: pass
                return

            _fechar()
            on_salvo()

        dd_momento.on_change = lambda e: None

        btn_cancel = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{SEC}22", ink=True,
        )
        btn_cancel.on_click = _fechar

        btn_ok = ft.Container(
            content=ft.Text("Salvar", size=13, color=VERD,
                            weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{VERD}22", ink=True,
        )
        btn_ok.on_click = _salvar
        tf_valor.on_submit = _salvar

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("water_drop_rounded", size=16, color=COR),
                        ft.Text("Nova Medicao — Glicemia", size=15, color=TXT,
                                weight=ft.FontWeight.W_700),
                    ], spacing=8),
                    ft.Container(height=4),
                    tf_valor,
                    dd_momento,
                    row_data,
                    txt_erro,
                    ft.Container(height=4),
                    ft.Row([btn_cancel, btn_ok], spacing=8,
                           alignment=ft.MainAxisAlignment.CENTER),
                ], spacing=10, tight=True),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20), width=340,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass

    def _renderizar_nivel2(params, g):
        area.controls.clear()
        n_sel = len(_selecionados)
        subtitulo.value = f"{len(params)} parametro(s) — {n_sel} selecionado(s)"

        # botao medicoes caseiras apenas no grupo Glicose Direta
        if g["id"] == "direta":
            btn_add = ft.Container(
                content=ft.Row([
                    ft.Icon("home_rounded", size=14, color=COR),
                    ft.Text("Medicoes Caseiras", size=12, color=COR),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=10, vertical=7),
                border_radius=8,
                bgcolor=ft.Colors.with_opacity(0.10, COR),
                border=ft.border.all(1, ft.Colors.with_opacity(0.3, COR)),
                ink=True,
            )
            def _abrir_medicoes_caseiras(e):
                from telas.tela_medicoes_caseiras import criar_tela_medicoes_caseiras

                def _voltar_cas():
                    page.controls.clear()
                    page.controls.append(_tela)
                    try: page.update()
                    except Exception: pass

                nova = criar_tela_medicoes_caseiras(page, voltar_fn=_voltar_cas)
                page.controls.clear()
                page.controls.append(nova)
                try: page.update()
                except Exception: pass

            btn_add.on_click = _abrir_medicoes_caseiras
            area.controls.append(ft.Row(
                [ft.Container(expand=True), btn_add],
            ))

        _atualizar_grafico()
        area.controls.append(grafico_container)
        area.controls.append(ft.Divider(color=BD, height=1))
        area.controls.append(ft.Text(
            "Toque para selecionar/deselecionar — multiplos no mesmo grafico",
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

            def _toggle(e, _n=nome, _params=params, _g=g):
                if _n in _selecionados:
                    if len(_selecionados) > 1:
                        _selecionados.discard(_n)
                else:
                    _selecionados.add(_n)
                _renderizar_nivel2(_params, _g)

            def _abrir_historico(e, _n=nome):
                from telas.tela_historico_parametro import criar_tela_historico_parametro

                def _voltar_hist():
                    page.controls.clear()
                    page.controls.append(_tela)
                    try: page.update()
                    except Exception: pass

                nova = criar_tela_historico_parametro(
                    page, param_nome=_n, voltar_fn=_voltar_hist,
                    grupo_nome=g["nome"],
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

    # -- carga inicial ------------------------------------------------
    _renderizar_grupos()

    # -- tela ---------------------------------------------------------
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
                ft.Icon("water_drop_rounded", size=16, color=COR),
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
