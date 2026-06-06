# -*- coding: utf-8 -*-
"""
tela_historico_parametro.py — Koios Prontuário
Histórico analítico completo de um parâmetro:
  - Todas as medições com data, valor, referência, nível
  - Laboratório e link para PDF
  - Anexos quando disponíveis
"""
import flet as ft
import sqlite3
import webbrowser

from dados.model_prontuario import DB_PATH
from shared.grafico import renderizar_grafico_combinado, NIVEL_COR, NIVEL_LABEL

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; AMAR = "#D29922"
VERM = "#DA3633"; COR  = "#FF9500"


def _buscar_conhecimento(conn_fechado, nomes: list) -> dict | None:
    """Busca exame_conhecimento + referencias_padrao para o primeiro nome que tiver registro."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        for nome in nomes:
            row = conn.execute("""
                SELECT ek.o_que_mede, ek.sistema_orgao, ek.alterado_alto, ek.alterado_baixo,
                       ek.faixa_alerta, ek.quem_solicita, ek.interferentes,
                       ek.preparo_paciente, ek.curiosidade_clinica, ek.fonte,
                       ep.nome_oficial, ep.id as ep_id, ep.unidade
                FROM exame_conhecimento ek
                JOIN exames_padrao ep ON ep.id = ek.exame_padrao_id
                WHERE UPPER(ep.nome_oficial) = UPPER(?)
                LIMIT 1
            """, (nome,)).fetchone()
            if row:
                d = dict(row)
                # busca referencias por faixa etaria
                refs = conn.execute("""
                    SELECT sexo, idade_min, idade_max,
                           critico_baixo, limite_baixo, otimo_min, otimo_max,
                           limite_alto, critico_alto, observacoes, fonte
                    FROM referencias_padrao
                    WHERE exame_padrao_id = ?
                    ORDER BY sexo, idade_min
                """, (d["ep_id"],)).fetchall()
                d["referencias"] = [dict(r) for r in refs]
                conn.close()
                return d
        conn.close()
    except Exception:
        pass
    return None


def _widget_referencias(refs: list, unidade: str = "") -> ft.Control:
    """Tabela compacta de valores de referência por faixa etária/sexo."""
    if not refs:
        return ft.Container(height=0)

    def _fmt(v):
        if v is None: return "—"
        try: return str(int(v)) if float(v) == int(float(v)) else f"{float(v):.1f}"
        except: return str(v)

    def _sexo(s):
        if s == "M": return "♂"
        if s == "F": return "♀"
        return "♂♀"

    def _idade(mn, mx):
        if mn is None and mx is None: return "Geral"
        if mx is None or mx >= 999: return f"{mn}+ anos"
        if mn == 0 and mx == 0: return "RN"
        if mn == 0: return f"0-{mx} anos"
        return f"{mn}-{mx} anos"

    linhas = []
    for r in refs:
        obs  = r.get("observacoes") or ""
        fnte = r.get("fonte") or ""
        # linha de referencia
        ref_txt = []
        if r.get("critico_baixo") is not None:
            ref_txt.append(f"Crítico↓<{_fmt(r['critico_baixo'])}")
        if r.get("limite_baixo") is not None:
            ref_txt.append(f"↓ {_fmt(r['limite_baixo'])}")
        if r.get("otimo_min") is not None and r.get("otimo_max") is not None:
            ref_txt.append(f"OK {_fmt(r['otimo_min'])}-{_fmt(r['otimo_max'])}")
        elif r.get("otimo_max") is not None:
            ref_txt.append(f"<{_fmt(r['otimo_max'])}")
        if r.get("limite_alto") is not None:
            ref_txt.append(f"↑ {_fmt(r['limite_alto'])}")
        if r.get("critico_alto") is not None:
            ref_txt.append(f"Crítico↑>{_fmt(r['critico_alto'])}")

        label = f"{_sexo(r.get('sexo'))} {_idade(r.get('idade_min'), r.get('idade_max'))}"
        if obs: label += f" ({obs})"

        linhas.append(ft.Container(
            content=ft.Row([
                ft.Text(label, size=10, color=SEC, expand=True),
                ft.Text(f"{' | '.join(ref_txt)} {unidade}".strip(),
                        size=10, color=TXT),
            ], spacing=8),
            padding=ft.padding.symmetric(vertical=3),
            border=ft.Border(bottom=ft.BorderSide(1, BD)),
        ))

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon("straighten_rounded", size=12, color=AMAR),
                ft.Text("Valores de Referência", size=10, color=AMAR,
                        weight=ft.FontWeight.W_600),
            ], spacing=6),
            ft.Container(height=4),
            *linhas,
        ], spacing=0),
        padding=ft.padding.symmetric(horizontal=4, vertical=6),
    )


def _card_conhecimento(k: dict, page) -> ft.Control:
    """Card expansível com conhecimento clínico do exame."""
    expandido = [False]

    def _linha(icone, label, valor, cor=None):
        if not valor:
            return ft.Container(height=0)
        return ft.Container(
            content=ft.Row([
                ft.Icon(icone, size=13, color=cor or SEC),
                ft.Column([
                    ft.Text(label, size=9, color=MUT),
                    ft.Text(str(valor), size=11, color=cor or TXT,
                            selectable=True),
                ], spacing=1, expand=True),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START),
            padding=ft.padding.only(bottom=6),
        )

    detalhe = ft.Column([
        _linha("straighten_rounded",    "O que mede",      k.get("o_que_mede")),
        _linha("account_tree_rounded",  "Sistema/Órgão",   k.get("sistema_orgao"), AZUL),
        _linha("arrow_upward_rounded",  "Alto indica",     k.get("alterado_alto"), "#F0883E"),
        _linha("arrow_downward_rounded","Baixo indica",    k.get("alterado_baixo"), "#58A6FF"),
        _linha("warning_amber_rounded", "Faixa de alerta", k.get("faixa_alerta"), "#D29922"),
        _widget_referencias(k.get("referencias") or [], k.get("unidade") or ""),
        _linha("person_search_rounded", "Quem solicita",   k.get("quem_solicita")),
        _linha("science_rounded",       "Interferentes",   k.get("interferentes")),
        _linha("restaurant_rounded",    "Preparo",         k.get("preparo_paciente")),
        _linha("lightbulb_rounded",     "Curiosidade",     k.get("curiosidade_clinica"), "#BC8CFF"),
        _linha("menu_book_rounded",     "Fonte",           k.get("fonte")),
    ], spacing=0, visible=False)

    icone_expand = ft.Icon("expand_more_rounded", size=16, color=SEC)

    cabecalho = ft.Container(
        content=ft.Row([
            ft.Icon("info_outline_rounded", size=14, color=AZUL),
            ft.Text("Conhecimento Clínico", size=12, color=AZUL,
                    weight=ft.FontWeight.W_600, expand=True),
            icone_expand,
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        ink=True,
    )

    def _toggle(e=None):
        expandido[0] = not expandido[0]
        detalhe.visible = expandido[0]
        icone_expand.name = "expand_less_rounded" if expandido[0] else "expand_more_rounded"
        try: page.update()
        except Exception: pass

    cabecalho.on_click = _toggle

    return ft.Container(
        content=ft.Column([cabecalho, detalhe], spacing=0),
        bgcolor=f"{AZUL}0A",
        border_radius=8,
        border=ft.border.all(1, f"{AZUL}33"),
        margin=ft.margin.only(top=6, bottom=6),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def criar_tela_historico_parametro(
    page: ft.Page,
    param_nome: str,
    voltar_fn=None,
    grupo_nome: str = None,
    param_nomes: list = None,
) -> ft.Column:
    """
    param_nome    — nome do exame individual (usado como titulo se grupo_nome=None)
    grupo_nome    — nome do grupo para o cabecalho (ex: "Glicose Direta")
    param_nomes   — lista de todos os nomes do grupo; se None usa so param_nome
    """
    _titulo = grupo_nome or param_nome
    _nomes  = param_nomes if param_nomes else [param_nome]

    area = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    def _voltar(e=None):
        if voltar_fn:
            voltar_fn()

    def carregar():
        area.controls.clear()
        try:
            conn = sqlite3.connect(DB_PATH, timeout=30)
            conn.row_factory = sqlite3.Row

            rows_lab = conn.execute(f"""
                SELECT
                    er.valor, er.unidade, er.referencia,
                    er.nivel_interpretacao,
                    e.data_exame, e.laboratorio, e.drive_file_id,
                    e.id as exame_id,
                    COALESCE(ep.nome_oficial, er.parametro) as nome,
                    0 as caseiro
                FROM exame_resultados er
                JOIN exames e ON e.id = er.exame_id
                LEFT JOIN exames_padrao ep ON ep.id = er.exame_padrao_id
                WHERE UPPER(COALESCE(ep.nome_oficial, er.parametro)) IN
                      ({",".join("UPPER(?)" for _ in _nomes)})
                  AND er.valor IS NOT NULL AND er.valor != ''
                  AND (e.status IS NULL OR e.status NOT IN ('rascunho','revisao'))
            """, _nomes).fetchall()

            # medicoes caseiras (marcadores_leituras) com mesmo nome
            rows_cas = conn.execute(f"""
                SELECT
                    CAST(valor AS TEXT) as valor,
                    unidade,
                    referencia,
                    NULL as nivel_interpretacao,
                    data_medicao as data_exame,
                    'Caseiro' as laboratorio,
                    NULL as drive_file_id,
                    -1 as exame_id,
                    parametro as nome,
                    1 as caseiro
                FROM marcadores_leituras
                WHERE UPPER(parametro) IN
                      ({",".join("UPPER(?)" for _ in _nomes)})
            """, _nomes).fetchall()

            # une e ordena por data desc
            from datetime import datetime as _dt
            def _sort_key(r):
                d = (r["data_exame"] or "")
                for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                    try: return _dt.strptime(d[:10], fmt)
                    except: pass
                return _dt.min

            rows = sorted(list(rows_lab) + list(rows_cas), key=_sort_key, reverse=True)

            # Buscar anexos por exame_id (so lab)
            exame_ids = list({r["exame_id"] for r in rows_lab})
            anexos_map = {}
            if exame_ids:
                ph2 = ",".join("?" * len(exame_ids))
                anx = conn.execute(f"""
                    SELECT exame_id, drive_file_id, nome_arquivo, arquivo_local
                    FROM exame_anexos
                    WHERE exame_id IN ({ph2})
                    ORDER BY exame_id, ordem
                """, exame_ids).fetchall()
                for a in anx:
                    anexos_map.setdefault(a["exame_id"], []).append(dict(a))
            conn.close()
        except Exception as ex:
            rows = []
            anexos_map = {}

        if not rows:
            area.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("bar_chart_rounded", size=48, color=MUT),
                    ft.Text("Nenhum resultado encontrado.", size=14, color=SEC),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                alignment=ft.alignment.Alignment(0, 0), padding=60,
            ))
            try: page.update()
            except Exception: pass
            return

        # ── Gráfico no topo ───────────────────────────────────────────────────
        historico_graf = []
        for r in reversed(rows):  # cronológico para o gráfico
            historico_graf.append({
                "valor":       r["valor"],
                "unidade":     r["unidade"] or "",
                "data":        r["data_exame"] or "",
                "referencia":  r["referencia"] or "",
                "nivel":       r["nivel_interpretacao"] or "sem_referencia",
                "laboratorio": r["laboratorio"] or "",
                "drive_id":    r["drive_file_id"] or "",
            })

        ex_sel = {
            "nome_oficial": param_nome,
            "unidade":      rows[0]["unidade"] or "",
            "historico":    historico_graf,
        }
        grafico = renderizar_grafico_combinado(page, [ex_sel])
        area.controls.append(grafico)

        # ── Card de conhecimento clínico ──────────────────────────────────────
        conhecimento = _buscar_conhecimento(conn, _nomes)
        if conhecimento:
            area.controls.append(_card_conhecimento(conhecimento, page))

        area.controls.append(ft.Divider(color=BD, height=1))
        area.controls.append(ft.Text(
            f"{len(rows)} medição(ões) — mais recente primeiro",
            size=11, color=MUT,
        ))

        # ── Cards analíticos ──────────────────────────────────────────────────
        for r in rows:
            nivel   = r["nivel_interpretacao"] or "sem_referencia"
            cor_n   = NIVEL_COR.get(nivel, AZUL)
            label_n = NIVEL_LABEL.get(nivel, "—")
            unidade = r["unidade"] or ""
            ref     = r["referencia"] or "—"
            lab     = r["laboratorio"] or ""
            did     = r["drive_file_id"] or ""
            eid     = r["exame_id"]
            is_cas  = (r["caseiro"] == 1)

            # Formata data
            data_raw = str(r["data_exame"] or "")[:10]
            if len(data_raw) == 10 and data_raw[4] == "-":
                try:
                    from datetime import datetime as _dt
                    data_raw = _dt.strptime(data_raw, "%Y-%m-%d").strftime("%d/%m/%Y")
                except Exception:
                    pass

            # Botão PDF ou badge caseiro
            if is_cas:
                btn_pdf = ft.Container(
                    content=ft.Row([
                        ft.Icon("home_rounded", size=13, color=SEC),
                        ft.Text("Caseiro", size=11, color=SEC),
                    ], spacing=4, tight=True),
                    bgcolor=ft.Colors.with_opacity(0.08, SEC),
                    border_radius=6,
                    padding=ft.padding.symmetric(horizontal=8, vertical=5),
                    border=ft.border.all(1, BD),
                )
            else:
                btn_pdf = ft.Container(
                    content=ft.Row([
                        ft.Icon("picture_as_pdf_rounded", size=13, color=VERM),
                        ft.Text("PDF", size=11, color=AZUL),
                    ], spacing=4, tight=True),
                    bgcolor=ft.Colors.with_opacity(0.08, VERM),
                    border_radius=6,
                    padding=ft.padding.symmetric(horizontal=8, vertical=5),
                    border=ft.border.all(1, BD),
                    ink=True, visible=bool(did),
                )
                if did:
                    btn_pdf.on_click = lambda e, d=did: webbrowser.open(
                        f"https://drive.google.com/file/d/{d}/view")

            # Anexos de imagem (so lab)
            anexos = [] if is_cas else anexos_map.get(eid, [])
            anexos_row = ft.Row(spacing=6, wrap=True, visible=bool(anexos))
            for a in anexos:
                src = None
                if a.get("arquivo_local"):
                    import os
                    if os.path.exists(a["arquivo_local"]):
                        src = a["arquivo_local"].replace("\\", "/")
                if not src and a.get("drive_file_id"):
                    src = f"https://drive.google.com/thumbnail?id={a['drive_file_id']}&sz=w120"
                if src:
                    img = ft.Container(
                        content=ft.Image(
                            src=src, width=80, height=60,
                            fit=ft.ImageFit.COVER,
                            error_content=ft.Icon("broken_image_rounded",
                                                  size=16, color=MUT),
                        ),
                        border_radius=6,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        border=ft.border.all(1, BD),
                        ink=True,
                    )
                    # click abre em tamanho real
                    def _abrir_img(e, _src=src):
                        webbrowser.open(_src)
                    img.on_click = _abrir_img
                    anexos_row.controls.append(img)

            card = ft.Container(
                content=ft.Column([
                    # Nome do parametro (so mostra se grupo tem varios)
                    ft.Text(
                        r["nome"] or param_nome,
                        size=12, color=COR, weight=ft.FontWeight.W_600,
                        visible=len(_nomes) > 1,
                    ),
                    # Cabecalho: data + lab + PDF
                    ft.Row([
                        ft.Text(data_raw, size=12, color=AMAR,
                                weight=ft.FontWeight.W_700),
                        ft.Text(lab, size=11, color=SEC, expand=True),
                        btn_pdf,
                    ], spacing=8,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),

                    # Valor + unidade + nível
                    ft.Row([
                        ft.Column([
                            ft.Text("Valor", size=9, color=MUT),
                            ft.Row([
                                ft.Text(str(r["valor"]), size=26, color=cor_n,
                                        weight=ft.FontWeight.W_800),
                                ft.Text(unidade, size=12, color=MUT),
                            ], spacing=4,
                               vertical_alignment=ft.CrossAxisAlignment.END),
                        ], spacing=1),
                        ft.VerticalDivider(color=BD, width=20),
                        ft.Column([
                            ft.Text("Referência", size=9, color=MUT),
                            ft.Text(ref, size=11, color=SEC),
                        ], spacing=1, expand=True),
                        ft.VerticalDivider(color=BD, width=20),
                        ft.Column([
                            ft.Text("Nível", size=9, color=MUT),
                            ft.Container(
                                content=ft.Text(label_n, size=11, color=cor_n,
                                                weight=ft.FontWeight.W_600),
                                bgcolor=ft.Colors.with_opacity(0.12, cor_n),
                                border_radius=6,
                                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            ),
                        ], spacing=1),
                    ], spacing=0,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),

                    # Anexos
                    anexos_row,
                ], spacing=8),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.all(14),
                border=ft.Border(
                    left=ft.BorderSide(3, cor_n),
                    top=ft.BorderSide(1, BD),
                    bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
            )
            area.controls.append(card)

        try: page.update()
        except Exception: pass

    carregar()

    from shared.layout import Layout
    lay = Layout(page)

    def _abrir_sobre(e=None):
        k = _buscar_conhecimento(None, _nomes)
        if not k:
            return
        ref_ov = [None]

        def _fechar(ev=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        def _linha_ov(icone, label, valor, cor=None):
            if not valor: return ft.Container(height=0)
            return ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(icone, size=13, color=cor or AZUL),
                        ft.Text(label, size=10, color=MUT,
                                weight=ft.FontWeight.W_600),
                    ], spacing=6),
                    ft.Text(str(valor), size=12, color=cor or TXT,
                            selectable=True),
                ], spacing=2),
                padding=ft.padding.only(bottom=10),
            )

        btn_fechar = ft.Container(
            content=ft.Text("Fechar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{SEC}22", ink=True,
        )
        btn_fechar.on_click = _fechar

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("info_outline_rounded", size=16, color=AZUL),
                        ft.Text(k.get("nome_oficial") or _titulo,
                                size=14, color=TXT,
                                weight=ft.FontWeight.W_700, expand=True),
                    ], spacing=8),
                    ft.Divider(color=BD, height=1),
                    ft.Container(
                        content=ft.Column([
                            _linha_ov("straighten_rounded",    "O que mede",       k.get("o_que_mede")),
                            _linha_ov("account_tree_rounded",  "Sistema / Órgão",  k.get("sistema_orgao"), AZUL),
                            _linha_ov("arrow_upward_rounded",  "Alto indica",      k.get("alterado_alto"), "#F0883E"),
                            _linha_ov("arrow_downward_rounded","Baixo indica",     k.get("alterado_baixo"), "#58A6FF"),
                            _linha_ov("warning_amber_rounded", "Faixa de alerta",  k.get("faixa_alerta"), AMAR),
                            _widget_referencias(k.get("referencias") or [], k.get("unidade") or ""),
                            _linha_ov("person_search_rounded", "Quem solicita",    k.get("quem_solicita")),
                            _linha_ov("science_rounded",       "Interferentes",    k.get("interferentes")),
                            _linha_ov("restaurant_rounded",    "Preparo",          k.get("preparo_paciente")),
                            _linha_ov("lightbulb_rounded",     "Curiosidade",      k.get("curiosidade_clinica"), "#BC8CFF"),
                            _linha_ov("menu_book_rounded",     "Fonte",            k.get("fonte")),
                        ], spacing=0, scroll=ft.ScrollMode.AUTO),
                        height=340,
                    ),
                    ft.Row([btn_fechar], alignment=ft.MainAxisAlignment.END),
                ], spacing=8, tight=True),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20), width=340,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass

    # botao info — so aparece se houver conhecimento
    _tem_conhecimento = _buscar_conhecimento(None, _nomes) is not None
    btn_info = ft.Container(
        content=ft.Icon("info_outline_rounded", size=18, color=AZUL),
        padding=ft.padding.all(8), border_radius=8, ink=True,
        tooltip="Sobre este exame",
        visible=_tem_conhecimento,
    )
    btn_info.on_click = _abrir_sobre

    return ft.Container(
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
                    on_click=_voltar,
                ),
                ft.Container(expand=True),
                ft.Icon("show_chart_rounded", size=16, color=COR),
                ft.Container(width=6),
                ft.Text(_titulo, size=16, color=TXT,
                        weight=ft.FontWeight.W_700,
                        no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Container(expand=True),
                btn_info,
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Divider(color=BD, height=1),
            ft.Container(height=4),
            ft.Container(
                content=area,
                padding=ft.padding.symmetric(horizontal=12),
                expand=True,
            ),
        ], spacing=6, expand=True),
    )
