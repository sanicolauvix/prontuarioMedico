# -*- coding: utf-8 -*-
"""
tela_docs_brutos.py
===================
Lista as páginas de PDF importadas (tabela pdf_paginas) de uma internação.
Permite ver a imagem, classificar via Claude e gravar nas tabelas finais.
"""
import flet as ft
import os, json, sqlite3, threading, base64, sys, subprocess, tempfile

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; VERM = "#DA3633"
AMAR = "#D29922"; ROXO = "#BC8CFF"; LAR  = "#F0883E"


def _rgba(hex_cor: str, alpha: float) -> str:
    """Converte cor #RRGGBB + alpha (0-1) para string rgba() compatível com Flet 0.28."""
    h = hex_cor.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

_GRUPO_COR    = {"A": AZUL, "B": VERD, "C": MUT}
_STATUS_COR   = {
    "pendente":     MUT,
    "classificado": AMAR,
    "gravado":      VERD,
    "descartado":   MUT,
}
_STATUS_ICO   = {
    "pendente":     "hourglass_empty_rounded",
    "classificado": "auto_awesome_rounded",
    "gravado":      "check_circle_rounded",
    "descartado":   "delete_outline_rounded",
}

_TIPO_ICONE = {
    "resultado_lab":         ("science_rounded",            AZUL),
    "ecg":                   ("monitor_heart_rounded",      VERM),
    "resultado_exame":       ("biotech_rounded",            AZUL),
    "resultado_imagem":      ("image_search_rounded",       AZUL),
    "mapa":                  ("show_chart_rounded",         VERD),
    "ecocardiograma":        ("favorite_border_rounded",    VERM),
    "prescricao_medica":     ("medication_rounded",         AMAR),
    "prescricao_enfermagem": ("medication_liquid_rounded",  AMAR),
    "sinais_vitais":         ("favorite_rounded",           VERM),
    "balanco_hidrico":       ("water_drop_rounded",         AZUL),
    "evolucao_medica":       ("description_rounded",        ROXO),
    "evolucao_enfermagem":   ("description_rounded",        SEC),
    "ficha_admissao":        ("person_add_rounded",         VERD),
    "ficha_transporte":      ("directions_car_rounded",     AMAR),
    "alta":                  ("exit_to_app_rounded",        VERD),
    "registro_cirurgia":     ("content_cut_rounded",        LAR),
    "avaliacao_riscos":      ("warning_rounded",            AMAR),
    "administrativo":        ("folder_rounded",             MUT),
    "termo":                 ("gavel_rounded",              MUT),
    "checklist_cirurgico":   ("checklist_rounded",          MUT),
    "checagem_pre_operatoria": ("fact_check_rounded",       MUT),
}


def _icone_tipo(tipo):
    return _TIPO_ICONE.get((tipo or "").lower(), ("picture_as_pdf_rounded", SEC))


def _listar_paginas(internacao_id: int, db_path: str) -> list:
    conn = sqlite3.connect(db_path, timeout=20)
    rows = conn.execute("""
        SELECT id, pdf_origem, pagina_num, drive_img_id, drive_pdf_id,
               tipo, grupo, dados_json, status, exame_id, dado_bruto_id, criado_em
        FROM pdf_paginas
        WHERE internacao_id = ?
        ORDER BY pdf_origem, pagina_num
    """, (internacao_id,)).fetchall()
    conn.close()
    cols = ["id","pdf_origem","pagina_num","drive_img_id","drive_pdf_id",
            "tipo","grupo","dados_json","status","exame_id","dado_bruto_id","criado_em"]
    return [dict(zip(cols, r)) for r in rows]


def criar_tela_docs_brutos(page: ft.Page, voltar_fn,
                            internacao_id: int = None,
                            embutido: bool = False) -> ft.Container:
    from dados.model_prontuario import DB_PATH

    # ── carregar internação ──
    inter = {}
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)
        row  = conn.execute(
            "SELECT id, data_entrada, data_saida, cid_entrada FROM internacoes WHERE id=?",
            (internacao_id,)
        ).fetchone()
        conn.close()
        if row:
            inter = dict(zip(["id","data_entrada","data_saida","cid_entrada"], row))
    except Exception:
        pass

    cid_label = (inter.get("cid_entrada") or "").split("—")[-1].strip() or "Internação"
    data_ent  = inter.get("data_entrada") or ""
    data_sai  = inter.get("data_saida")   or ""

    # ── estado ──
    _paginas  = [_listar_paginas(internacao_id, DB_PATH)]
    _overlay  = ft.Container(visible=False, expand=True,
                              bgcolor="#000000CC",
                              alignment=ft.alignment.center)
    _lista    = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

    def _reload():
        _paginas[0] = _listar_paginas(internacao_id, DB_PATH)
        _montar_lista()
        try: page.update()
        except Exception: pass

    def _mostrar_overlay(c):
        _overlay.content = c
        _overlay.visible = True
        try: page.update()
        except Exception: pass

    def _fechar_overlay(*_):
        _overlay.visible = False
        try: page.update()
        except Exception: pass

    # ── ver imagem do Drive ──
    def _ver_imagem(pag: dict):
        drive_img_id = pag.get("drive_img_id")
        if not drive_img_id:
            page.snack_bar = ft.SnackBar(ft.Text("Sem imagem no Drive", color=AMAR), open=True)
            try: page.update()
            except Exception: pass
            return

        prog = ft.ProgressRing(width=28, height=28, stroke_width=3, color=AZUL)
        _mostrar_overlay(ft.Column([prog,
            ft.Text("Carregando imagem...", size=12, color=SEC,
                    text_align=ft.TextAlign.CENTER)],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True, spacing=8))

        def _run():
            try:
                from utils.drive_sync import _get_creds, baixar_foto
                creds = _get_creds()
                tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                tmp.close()
                ok = baixar_foto(drive_img_id, tmp.name, creds)
                if not ok:
                    raise IOError("Falha ao baixar imagem")
                with open(tmp.name, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                os.unlink(tmp.name)

                num  = pag["pagina_num"]
                orig = pag["pdf_origem"]
                tipo = (pag.get("tipo") or "—").replace("_"," ").title()

                img_ctrl = ft.Image(
                    src_base64=img_b64,
                    fit=ft.ImageFit.CONTAIN,
                    expand=True,
                )
                conteudo = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"Pág {num} — {orig}", size=12,
                                    color=SEC, expand=True),
                            ft.Text(tipo, size=11, color=AMAR),
                            ft.IconButton("close_rounded", icon_color=SEC,
                                          icon_size=18, on_click=_fechar_overlay),
                        ], spacing=8),
                        ft.Divider(height=1, color=BD),
                        ft.Container(content=img_ctrl, expand=True,
                                     bgcolor=BD, border_radius=8),
                    ], spacing=8, expand=True),
                    bgcolor=CARD,
                    border=ft.border.all(1, BD2),
                    border_radius=14,
                    padding=14,
                    width=(page.width or 380) - 24,
                    height=580,
                )
                _mostrar_overlay(conteudo)
            except Exception as ex:
                _fechar_overlay()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Erro: {ex}"[:120], color=VERM), open=True)
                try: page.update()
                except Exception: pass

        threading.Thread(target=_run, daemon=True).start()

    # ── ver dados JSON extraídos ──
    def _ver_dados(pag: dict):
        dados_json = pag.get("dados_json") or "{}"
        try:
            dados = json.loads(dados_json)
        except Exception:
            dados = {"raw": dados_json}
        tipo  = pag.get("tipo") or "—"
        grupo = pag.get("grupo") or "?"
        cor_g = _GRUPO_COR.get(grupo, SEC)

        linhas = []
        for k, v in dados.items():
            v_txt = json.dumps(v, ensure_ascii=False, indent=2) if isinstance(v, (dict, list)) else str(v)
            linhas.append(ft.Row([
                ft.Text(k, size=11, color=SEC, width=120),
                ft.Text(v_txt, size=11, color=TXT, selectable=True,
                        expand=True, no_wrap=False),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START))

        status = pag.get("status") or "pendente"
        descartado = status == "descartado"

        # descartado → sem botão; gravado → "Regravar" azul; outros → "Processar" verde
        if descartado:
            _btn_cor_bg  = MUT
            _btn_cor_txt = SEC
            _btn_ico     = "block_rounded"
            _btn_label   = "Descartado"
        elif status == "gravado":
            _btn_cor_bg  = AZUL
            _btn_cor_txt = "#0D1117"
            _btn_ico     = "replay_rounded"
            _btn_label   = "Regravar"
        else:
            _btn_cor_bg  = VERD
            _btn_cor_txt = "#0D1117"
            _btn_ico     = "save_rounded"
            _btn_label   = "Processar"

        btn_processar_txt = ft.Text(
            _btn_label, size=12, color=_btn_cor_txt, weight=ft.FontWeight.W_600,
        )
        btn_processar = ft.Container(
            content=ft.Row([
                ft.Icon(_btn_ico, size=14, color=_btn_cor_txt),
                btn_processar_txt,
            ], spacing=5, tight=True),
            bgcolor=_btn_cor_bg,
            border_radius=8, ink=not descartado,
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
        )

        def _processar_json(e, p=pag):
            if p.get("status") == "descartado":
                return
            btn_processar_txt.value = "Processando..."
            try: page.update()
            except Exception: pass

            def _run():
                try:
                    from utils.processador_pdf import gravar_pagina
                    r = gravar_pagina(p["id"])
                    grupo_r = r.get("grupo", "?")
                    desc = {"A": "exame gravado", "B": "dado clínico gravado",
                            "C": "descartado"}.get(grupo_r, "gravado")
                    btn_processar_txt.value = "Gravado"
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"Pág {p['pagina_num']}: {desc}", color=VERD), open=True)
                    try: page.update()
                    except Exception: pass
                    _fechar_overlay()
                    _reload()
                except Exception as ex:
                    btn_processar_txt.value = "Erro"
                    page.snack_bar = ft.SnackBar(
                        ft.Text(str(ex)[:120], color=VERM), open=True)
                    try: page.update()
                    except Exception: pass

            threading.Thread(target=_run, daemon=True).start()

        btn_processar.on_click = _processar_json

        conteudo = ft.Container(
            content=ft.Column([
                # header fixo
                ft.Row([
                    ft.Container(
                        content=ft.Text(f"Grupo {grupo}", size=10, color=cor_g,
                                        weight=ft.FontWeight.W_700),
                        bgcolor=_rgba(cor_g, 0.13), border_radius=6,
                        padding=ft.padding.symmetric(horizontal=8, vertical=3),
                    ),
                    ft.Text(tipo.replace("_"," ").title(), size=13,
                            color=TXT, weight=ft.FontWeight.W_600, expand=True),
                    ft.IconButton("close_rounded", icon_color=SEC,
                                  icon_size=18, on_click=_fechar_overlay),
                ], spacing=8),
                ft.Divider(height=1, color=BD),
                # área de dados — scroll interno
                ft.Container(
                    content=ft.Column(linhas, spacing=6, scroll=ft.ScrollMode.AUTO),
                    expand=True,
                ),
                # rodapé fixo com botão processar
                ft.Divider(height=1, color=BD),
                ft.Row([ft.Container(expand=True), btn_processar], spacing=0),
            ], spacing=10, expand=True),
            bgcolor=CARD, border=ft.border.all(1, BD2),
            border_radius=14, padding=16,
            width=(page.width or 380) - 24, height=520,
        )
        _mostrar_overlay(conteudo)

    # ── classificar (pass 1 + 2) ──
    def _classificar(pag: dict):
        pid = pag["id"]

        def _run():
            try:
                from utils.processador_pdf import classificar_pagina
                classificar_pagina(pid, DB_PATH)
                _reload()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Erro: {ex}"[:120], color=VERM), open=True)
                try: page.update()
                except Exception: pass

        threading.Thread(target=_run, daemon=True).start()

    # ── gravar na tabela final ──
    def _gravar(pag: dict):
        pid = pag["id"]

        def _run():
            try:
                from utils.processador_pdf import gravar_pagina
                r = gravar_pagina(pid, DB_PATH)
                grupo = r.get("grupo","?")
                desc  = {"A": "exame gravado", "B": "dado clínico gravado",
                         "C": "descartado"}.get(grupo, "gravado")
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Pág {pag['pagina_num']}: {desc}", color=VERD), open=True)
                try: page.update()
                except Exception: pass
                _reload()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Erro: {ex}"[:120], color=VERM), open=True)
                try: page.update()
                except Exception: pass

        threading.Thread(target=_run, daemon=True).start()

    # ── classificar todos pendentes ──
    def _classificar_todos(e):
        pendentes = [p for p in _paginas[0] if p["status"] == "pendente"]
        if not pendentes:
            return
        prog_txt = ft.Text(f"0/{len(pendentes)}", size=12, color=SEC,
                           text_align=ft.TextAlign.CENTER)
        _mostrar_overlay(ft.Column([
            ft.ProgressRing(width=28, height=28, stroke_width=3, color=AMAR),
            ft.Container(height=6),
            ft.Text("Classificando páginas...", size=13, color=TXT,
                    weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
            prog_txt,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True, spacing=4))

        def _run():
            import time
            from utils.processador_pdf import classificar_pagina
            for i, pag in enumerate(pendentes):
                try:
                    classificar_pagina(pag["id"], DB_PATH)
                except Exception as ex:
                    pass
                prog_txt.value = f"{i+1}/{len(pendentes)}"
                try: page.update()
                except Exception: pass
            _fechar_overlay()
            _reload()

        threading.Thread(target=_run, daemon=True).start()

    # ── construir card ──
    def _fazer_card(pag: dict) -> ft.Container:
        status   = pag.get("status") or "pendente"
        tipo     = pag.get("tipo")
        grupo    = pag.get("grupo")
        tem_dados = bool(pag.get("dados_json") and pag["dados_json"] != "{}")

        cor_status = _STATUS_COR.get(status, MUT)
        ico_status = _STATUS_ICO.get(status, "hourglass_empty_rounded")
        ico_tipo, cor_tipo = _icone_tipo(tipo)
        cor_g = _GRUPO_COR.get(grupo, MUT) if grupo else MUT

        # linha 1: ícone tipo + origem + pág
        tipo_txt = ft.Text(
            (tipo or "pendente").replace("_"," ").title(),
            size=12, color=cor_tipo if tipo else MUT,
            weight=ft.FontWeight.W_500,
        )
        origem_txt = ft.Text(
            f"{pag['pdf_origem']}  pág {pag['pagina_num']}",
            size=10, color=MUT,
        )

        # badges
        badges = ft.Row(spacing=4, tight=True)
        if grupo:
            badges.controls.append(ft.Container(
                content=ft.Text(f"G{grupo}", size=9, color=cor_g, weight=ft.FontWeight.W_700),
                bgcolor=_rgba(cor_g, 0.13), border_radius=5,
                padding=ft.padding.symmetric(horizontal=6, vertical=2),
            ))
        badges.controls.append(ft.Container(
            content=ft.Row([
                ft.Icon(ico_status, size=10, color=cor_status),
                ft.Text(status, size=9, color=cor_status),
            ], spacing=3, tight=True),
            bgcolor=_rgba(cor_status, 0.09), border_radius=5,
            padding=ft.padding.symmetric(horizontal=6, vertical=2),
        ))

        # botões de ação
        btn_img = ft.Container(
            content=ft.Row([
                ft.Icon("image_rounded", size=12, color=AZUL),
                ft.Text("Ver", size=11, color=AZUL),
            ], spacing=3, tight=True),
            bgcolor=_rgba(AZUL, 0.09), border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=9, vertical=5),
            on_click=lambda e, p=pag: _ver_imagem(p),
        )

        if status == "pendente":
            btn_acao = ft.Container(
                content=ft.Row([
                    ft.Icon("auto_awesome_rounded", size=12, color=AMAR),
                    ft.Text("Classificar", size=11, color=AMAR),
                ], spacing=3, tight=True),
                bgcolor=_rgba(AMAR, 0.09), border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=9, vertical=5),
                on_click=lambda e, p=pag: _classificar(p),
            )
        elif status == "classificado":
            btn_acao = ft.Container(
                content=ft.Row([
                    ft.Icon("save_rounded", size=12, color=VERD),
                    ft.Text("Gravar", size=11, color=VERD),
                ], spacing=3, tight=True),
                bgcolor=_rgba(VERD, 0.09), border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=9, vertical=5),
                on_click=lambda e, p=pag: _gravar(p),
            )
        else:
            btn_acao = ft.Container()

        btn_dados = ft.Container(
            content=ft.Row([
                ft.Icon("data_object_rounded", size=12, color=ROXO),
                ft.Text("JSON", size=11, color=ROXO),
            ], spacing=3, tight=True),
            bgcolor=_rgba(ROXO, 0.09), border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=9, vertical=5),
            visible=tem_dados,
            on_click=lambda e, p=pag: _ver_dados(p),
        )

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ico_tipo, size=14, color=cor_tipo),
                    tipo_txt,
                    ft.Container(expand=True),
                    badges,
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                origem_txt,
                ft.Row([btn_img, btn_acao, btn_dados], spacing=6),
            ], spacing=5),
            bgcolor=CARD,
            border=ft.border.all(1, _rgba(cor_g, 0.27) if grupo else BD),
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
        )

    def _montar_lista():
        pags = _paginas[0]
        if not pags:
            _lista.controls = [ft.Container(
                content=ft.Column([
                    ft.Icon("inbox_rounded", size=40, color=MUT),
                    ft.Text("Nenhuma página importada", size=13, color=MUT),
                    ft.Text("Importe um PDF nesta internação primeiro",
                            size=11, color=MUT),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=6, tight=True),
                alignment=ft.alignment.center,
                padding=ft.padding.symmetric(vertical=40),
            )]
            return

        # agrupar por PDF de origem
        grupos: dict[str, list] = {}
        for p in pags:
            orig = p["pdf_origem"]
            grupos.setdefault(orig, []).append(p)

        controles = []
        for orig, items in grupos.items():
            total_o   = len(items)
            gravados  = sum(1 for i in items if i["status"] == "gravado")
            classif   = sum(1 for i in items if i["status"] == "classificado")
            pendentes = sum(1 for i in items if i["status"] == "pendente")

            controles.append(ft.Container(
                content=ft.Row([
                    ft.Icon("picture_as_pdf_rounded", size=12, color=LAR),
                    ft.Text(orig, size=11, color=LAR, weight=ft.FontWeight.W_600,
                            expand=True),
                    ft.Text(f"{total_o} págs  ✓{gravados}  ★{classif}  ○{pendentes}",
                            size=10, color=MUT),
                ], spacing=6),
                padding=ft.padding.only(left=4, top=8, right=4, bottom=4),
            ))
            for p in items:
                controles.append(_fazer_card(p))

        _lista.controls = controles

    _montar_lista()

    # ── totais para header ──
    total_pags = len(_paginas[0])
    pendentes  = sum(1 for p in _paginas[0] if p["status"] == "pendente")

    header = ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Row([
                    ft.Icon("arrow_back", size=16, color=AZUL),
                    ft.Text("Voltar", size=13, color=AZUL),
                ], spacing=4, tight=True),
                border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                on_click=lambda e: voltar_fn(),
            ),
            ft.Row([
                ft.Icon("folder_copy_rounded", size=15, color=AMAR),
                ft.Text("Documentos Brutos", size=14, color=TXT,
                        weight=ft.FontWeight.W_700),
            ], spacing=6, tight=True),
            ft.Container(expand=True),
            ft.Container(
                content=ft.Row([
                    ft.Icon("auto_awesome_rounded", size=13, color=AMAR),
                    ft.Text("Classificar todos", size=11, color=AMAR),
                ], spacing=4, tight=True),
                bgcolor=_rgba(AMAR, 0.09), border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                on_click=_classificar_todos,
                visible=pendentes > 0,
            ),
        ], spacing=8),
        border=ft.border.only(bottom=ft.BorderSide(1, BD)),
        padding=ft.padding.only(left=16, top=32, right=8, bottom=6),
    )

    sub_header = ft.Container(
        content=ft.Row([
            ft.Icon("local_hospital_rounded", size=12, color=AZUL),
            ft.Text(cid_label, size=11, color=SEC, expand=True),
            ft.Text(f"{data_ent} → {data_sai}", size=10, color=MUT),
            ft.Container(width=8),
            ft.Container(
                content=ft.Text(f"{total_pags} págs", size=10,
                                color=AZUL, weight=ft.FontWeight.W_600),
                bgcolor=_rgba(AZUL, 0.09), border_radius=6,
                padding=ft.padding.symmetric(horizontal=8, vertical=2),
            ),
        ], spacing=6),
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
    )

    corpo = ft.Container(
        content=_lista, expand=True,
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
    )

    cabecalhos = [] if embutido else [header, sub_header]
    tela = ft.Stack([
        ft.Column(cabecalhos + [corpo], spacing=0, expand=True),
        _overlay,
    ], expand=True)

    return ft.Container(
        content=ft.Column([tela], expand=True, spacing=0),
        bgcolor=BG, expand=True,
    )
