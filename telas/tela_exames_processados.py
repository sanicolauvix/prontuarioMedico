# -*- coding: utf-8 -*-
"""
tela_exames_processados.py
Tela de exames processados com 3 abas:
  1. Exames       — busca por texto + filtros
  2. Por Médico   — busca médico → exames associados
  3. Classificação — por categoria (Hormônios, Vitaminas, etc.)
"""
import flet as ft
import sqlite3
import webbrowser
from dados.model_prontuario import DB_PATH

BG   = "#0D1117";  CARD = "#161B22";  BD  = "#21262D";  BD2 = "#30363D"
TXT  = "#E6EDF3";  SEC  = "#8B949E";  MUT = "#484F58"
AZUL = "#58A6FF";  VERD = "#3FB950";  VERM = "#DA3633"
AMAR = "#D29922";  ROXO = "#BC8CFF";  LAR  = "#F0883E"

# ── Cores por categoria ──────────────────────────────────────────────────────
_CAT_COR = {
    "Glicemia":         "#58A6FF",
    "Lipídios":         "#F0883E",
    "Hemograma":        "#DA3633",
    "Hormônios":        "#BC8CFF",
    "Vitaminas":        "#3FB950",
    "Tireoide":         "#58A6FF",
    "Função Renal":     "#D29922",
    "Função Hepática":  "#F0883E",
    "Enzimas":          "#D29922",
    "Minerais":         "#3FB950",
    "Proteínas":        "#8B949E",
    "Ferroe":           "#D29922",
    "Ferro":            "#D29922",
    "Coagulação":       "#DA3633",
    "Inflamação":       "#F0883E",
    "Infectologia":     "#DA3633",
    "Imunologia":       "#BC8CFF",
    "Urina":            "#58A6FF",
    "MAPA":             "#3FB950",
}

def _cor_cat(categoria):
    if not categoria:
        return MUT
    for k, v in _CAT_COR.items():
        if k.lower() in (categoria or "").lower():
            return v
    return MUT

# ── Queries ──────────────────────────────────────────────────────────────────

def _listar_exames(filtro_tipo=None, filtro_lab=None, filtro_texto=None):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        sql = """
            SELECT e.id, e.tipo, e.tipo_exame, e.data_exame, e.laboratorio,
                   e.medico_solicit, e.arquivo_origem, e.drive_file_id,
                   e.importado_em, p.nome as paciente,
                   (SELECT COUNT(*) FROM exame_resultados r WHERE r.exame_id = e.id) as qtd_params,
                   (SELECT COUNT(*) FROM laudos l WHERE l.exame_id = e.id) as tem_laudo
            FROM exames e
            LEFT JOIN pacientes p ON p.id = e.paciente_id
            WHERE 1=1
        """
        params = []
        if filtro_tipo:
            sql += " AND e.tipo = ?"; params.append(filtro_tipo)
        if filtro_lab:
            sql += " AND UPPER(e.laboratorio) LIKE UPPER(?)"; params.append(f"%{filtro_lab}%")
        if filtro_texto:
            sql += " AND (UPPER(e.tipo_exame) LIKE UPPER(?) OR UPPER(e.arquivo_origem) LIKE UPPER(?))"
            params.extend([f"%{filtro_texto}%", f"%{filtro_texto}%"])
        sql += " ORDER BY e.data_exame DESC, e.importado_em DESC"
        rows = conn.execute(sql, params).fetchall()
        cols = ["id","tipo","tipo_exame","data_exame","laboratorio","medico_solicit",
                "arquivo_origem","drive_file_id","importado_em","paciente","qtd_params","tem_laudo"]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def _listar_medicos():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        rows = conn.execute(
            "SELECT id, nome, especialidade FROM medicos ORDER BY nome"
        ).fetchall()
        return [{"id": r[0], "nome": r[1], "especialidade": r[2]} for r in rows]
    finally:
        conn.close()


def _exames_do_medico(medico_id):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        rows = conn.execute("""
            SELECT e.id, e.tipo, e.tipo_exame, e.data_exame, e.laboratorio,
                   e.arquivo_origem, e.drive_file_id,
                   (SELECT COUNT(*) FROM exame_resultados r WHERE r.exame_id = e.id) as qtd_params
            FROM exames e
            WHERE UPPER(e.medico_solicit) LIKE UPPER((SELECT '%'||nome||'%' FROM medicos WHERE id=?))
               OR e.medico_solicit LIKE (SELECT '%'||nome||'%' FROM medicos WHERE id=?)
            ORDER BY e.data_exame DESC
        """, (medico_id, medico_id)).fetchall()
        cols = ["id","tipo","tipo_exame","data_exame","laboratorio","arquivo_origem","drive_file_id","qtd_params"]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def _listar_categorias():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        rows = conn.execute(
            "SELECT DISTINCT categoria FROM exames_padrao WHERE categoria IS NOT NULL ORDER BY categoria"
        ).fetchall()
        return [r[0] for r in rows if r[0]]
    finally:
        conn.close()


def _resultados_por_categoria(categoria, filtro_texto=None):
    """Retorna resultados estruturados agrupados pela categoria do exame_padrao."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        sql = """
            SELECT r.parametro, r.valor, r.unidade, r.referencia,
                   e.data_exame, e.laboratorio, e.id as exame_id,
                   ep.categoria, ep.nome_oficial
            FROM exame_resultados r
            JOIN exames e ON e.id = r.exame_id
            LEFT JOIN exames_padrao ep ON ep.id = r.exame_padrao_id
            WHERE (ep.categoria = ? OR (ep.categoria IS NULL AND ? = 'Outros'))
        """
        params = [categoria, categoria]
        if filtro_texto:
            sql += " AND UPPER(r.parametro) LIKE UPPER(?)"
            params.append(f"%{filtro_texto}%")
        sql += " ORDER BY e.data_exame DESC, r.parametro"
        rows = conn.execute(sql, params).fetchall()
        cols = ["parametro","valor","unidade","referencia","data_exame","laboratorio",
                "exame_id","categoria","nome_oficial"]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def _labs_distintos():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        rows = conn.execute(
            "SELECT DISTINCT laboratorio FROM exames WHERE laboratorio IS NOT NULL ORDER BY laboratorio"
        ).fetchall()
        return [r[0] for r in rows if r[0]]
    finally:
        conn.close()


def _resultados_exame(exame_id):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        res = conn.execute("""
            SELECT parametro, valor, unidade, referencia
            FROM exame_resultados WHERE exame_id = ? ORDER BY id
        """, (exame_id,)).fetchall()
        lau = conn.execute(
            "SELECT conclusao FROM laudos WHERE exame_id = ?", (exame_id,)
        ).fetchone()
        return res, lau
    finally:
        conn.close()


# ── Helpers visuais ──────────────────────────────────────────────────────────

def _chip_tipo(tipo):
    label = {"numerico": "Numérico", "laudo": "Laudo", "mapa": "MAPA",
             "imagem": "Imagem"}.get(tipo, tipo or "?")
    cor   = {"numerico": AZUL, "laudo": LAR, "mapa": VERD, "imagem": ROXO}.get(tipo, MUT)
    return ft.Container(
        content=ft.Text(label, size=9, color=cor, weight=ft.FontWeight.W_600),
        bgcolor=f"{cor}18", border_radius=4,
        padding=ft.padding.symmetric(horizontal=6, vertical=2),
        border=ft.Border(
            top=ft.BorderSide(1, f"{cor}40"), bottom=ft.BorderSide(1, f"{cor}40"),
            left=ft.BorderSide(1, f"{cor}40"), right=ft.BorderSide(1, f"{cor}40"),
        ))


def _card_exame(ex, on_click_fn, on_pdf_fn, on_edit_fn=None, on_reprocess_fn=None):
    tipo    = ex.get("tipo", "")
    cor     = {"numerico": AZUL, "laudo": LAR, "mapa": VERD, "imagem": ROXO}.get(tipo, MUT)
    icone   = {"numerico": "analytics_rounded", "laudo": "article_rounded",
               "mapa": "monitor_heart_rounded", "imagem": "photo_rounded"}.get(tipo, "description_rounded")
    tipo_ex = (ex.get("tipo_exame") or "")[:48]
    arquivo = (ex.get("arquivo_origem") or "").split("/")[-1].split("\\")[-1]
    titulo  = tipo_ex or arquivo or f"Exame #{ex['id']}"
    data    = ex.get("data_exame") or "sem data"
    lab     = ex.get("laboratorio") or ""
    medico  = ex.get("medico_solicit") or ""
    params  = ex.get("qtd_params", 0)
    tem_pdf = bool(ex.get("arquivo_origem") or ex.get("drive_file_id"))

    btn_reprocess = ft.Container(
        content=ft.Row([
            ft.Icon("refresh_rounded", size=11, color=AZUL),
            ft.Text("Reprocessar", size=10, color=AZUL),
        ], spacing=3, tight=True),
        padding=ft.padding.symmetric(horizontal=8, vertical=6),
        border_radius=6,
        bgcolor=ft.Colors.with_opacity(0.10, AZUL),
        border=ft.border.all(1, ft.Colors.with_opacity(0.3, AZUL)),
        ink=True,
        visible=tem_pdf and on_reprocess_fn is not None,
    )
    if on_reprocess_fn:
        btn_reprocess.on_click = on_reprocess_fn

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Container(
                    content=ft.Icon(icone, size=18, color=cor),
                    bgcolor=f"{cor}18", border_radius=6,
                    width=36, height=36,
                    alignment=ft.alignment.Alignment(0, 0)),
                ft.Column([
                    ft.Row([
                        ft.Text(titulo, size=12, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True,
                                no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                        _chip_tipo(tipo),
                    ], spacing=6),
                    ft.Row([
                        ft.Icon("calendar_today_outlined_rounded", size=10, color=MUT),
                        ft.Text(data, size=10, color=SEC),
                        ft.Text("·", size=10, color=MUT) if lab else ft.Container(),
                        ft.Text(lab, size=10, color=ROXO),
                    ], spacing=3),
                ], spacing=2, expand=True),
                ft.Column([
                    ft.Text(str(params), size=13, color=cor, weight=ft.FontWeight.W_700),
                    ft.Text("params", size=8, color=MUT),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0,
                   tight=True),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([
                ft.Row([
                    ft.Icon("person_outline_rounded", size=10, color=MUT),
                    ft.Text(medico[:40], size=10, color=SEC),
                ], spacing=3, expand=True) if medico else ft.Container(expand=True),
                btn_reprocess,
                ft.Container(
                    content=ft.Icon("edit_rounded", size=13, color=SEC),
                    padding=ft.padding.symmetric(horizontal=8, vertical=8),
                    ink=True,
                    tooltip="Editar",
                    on_click=on_edit_fn,
                    visible=on_edit_fn is not None,
                ),
                ft.Container(
                    content=ft.Row([
                        ft.Icon("picture_as_pdf_rounded", size=11, color=VERM),
                        ft.Text("PDF", size=10, color=SEC),
                    ], spacing=3, tight=True),
                    padding=ft.padding.symmetric(horizontal=8, vertical=8),
                    ink=True,
                    on_click=on_pdf_fn),
            ], spacing=4),
        ], spacing=5),
        bgcolor=CARD, border_radius=8,
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border=ft.Border(
            left=ft.BorderSide(2, cor),
            top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
            right=ft.BorderSide(1, BD),
        ),
        on_click=on_click_fn, ink=True)


def _campo_busca(label, hint, on_change):
    return ft.TextField(
        label=label, hint_text=hint,
        prefix_icon="search_rounded",
        bgcolor=CARD, border_color=BD, focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC),
        hint_style=ft.TextStyle(color=MUT),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, expand=True,
        on_change=on_change)


# ════════════════════════════════════════════════════════════════════════════
# TELA PRINCIPAL
# ════════════════════════════════════════════════════════════════════════════

def criar_tela_exames_processados(page: ft.Page, voltar_fn):

    try:
        larg = page.width or 800
    except Exception:
        larg = 800
    compacto = larg < 600

    # ── Aba ativa ────────────────────────────────────────────
    aba_ativa = ["exames"]   # "exames" | "medico" | "classificacao"

    # ── Containers de conteúdo ───────────────────────────────
    corpo_exames    = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
    corpo_medico    = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
    corpo_classif   = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

    # ── Campos de busca ──────────────────────────────────────
    busca_exames = _campo_busca("Buscar exame", "nome, tipo ou arquivo...",
                                lambda e: _carregar_exames())

    dd_tipo = ft.Dropdown(
        label="Tipo", bgcolor=CARD, border_color=BD,
        focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, width=130,
        on_change=lambda e: _carregar_exames(),
        options=[
            ft.dropdown.Option("", "Todos"),
            ft.dropdown.Option("numerico", "Numérico"),
            ft.dropdown.Option("laudo", "Laudo"),
            ft.dropdown.Option("mapa", "MAPA"),
            ft.dropdown.Option("imagem", "Imagem"),
        ])

    dd_lab = ft.Dropdown(
        label="Laboratório", bgcolor=CARD, border_color=BD,
        focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, width=150,
        on_change=lambda e: _carregar_exames(),
        options=[ft.dropdown.Option("", "Todos")] +
                [ft.dropdown.Option(l, l) for l in _labs_distintos()])

    busca_medico = _campo_busca("Buscar médico", "nome ou especialidade...",
                                lambda e: _carregar_medicos())

    busca_classif = _campo_busca("Buscar parâmetro", "ex: testosterona, vitamina D...",
                                 lambda e: _carregar_classif())

    cat_selecionada = [None]

    # ── Estado dos botões de aba ─────────────────────────────
    _btn_exames  = ft.Ref[ft.Container]()
    _btn_medico  = ft.Ref[ft.Container]()
    _btn_classif = ft.Ref[ft.Container]()

    # ── Diálogo de detalhe ───────────────────────────────────
    def _abrir_detalhe(exame_id, titulo):
        results, laudo = _resultados_exame(exame_id)
        itens = []
        if results:
            for r in results[:30]:
                ref = r[3] or ""
                itens.append(ft.Container(
                    content=ft.Row([
                        ft.Text(r[0] or "", size=11, color=TXT, expand=True),
                        ft.Column([
                            ft.Row([
                                ft.Text(r[1] or "", size=12, color=AZUL,
                                        weight=ft.FontWeight.W_700),
                                ft.Text(r[2] or "", size=10, color=MUT),
                            ], spacing=3),
                            ft.Text(ref[:40], size=9, color=MUT) if ref else ft.Container(),
                        ], spacing=1, horizontal_alignment=ft.CrossAxisAlignment.END),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    border=ft.Border(bottom=ft.BorderSide(1, BD)),
                    padding=ft.padding.symmetric(vertical=5),
                ))
            if len(results) > 30:
                itens.append(ft.Text(f"... +{len(results)-30} parâmetros", size=10, color=MUT))
        elif laudo:
            conc = laudo[0] or "Sem conclusão"
            itens.append(ft.Container(
                content=ft.Text(conc[:400], size=12, color=SEC),
                padding=ft.padding.all(8),
                bgcolor=f"{AZUL}0D", border_radius=6,
            ))
        else:
            itens.append(ft.Text("Sem resultados disponíveis.", size=12, color=MUT))

        ref = [None]

        def _fechar_dlg(e=None):
            if ref[0] and ref[0] in page.overlay:
                page.overlay.remove(ref[0])
            try: page.update()
            except Exception: pass

        btn_fechar = ft.Container(
            content=ft.Text("Fechar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=8, bgcolor=f"{SEC}22", ink=True,
        )
        btn_fechar.on_click = _fechar_dlg

        ref[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("analytics_rounded", size=16, color=AZUL),
                        ft.Text(titulo[:50], size=13, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True),
                    ], spacing=8),
                    ft.Divider(color=BD, height=1),
                    ft.Container(
                        content=ft.Column(itens, spacing=0,
                                          scroll=ft.ScrollMode.AUTO),
                        height=280,
                    ),
                    ft.Row([btn_fechar], alignment=ft.MainAxisAlignment.END),
                ], spacing=8, tight=True),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(16), width=340,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref[0].on_click = _fechar_dlg
        page.overlay.append(ref[0])
        try: page.update()
        except Exception: pass

    def _abrir_edicao(ex):
        from shared.date_field import campo_data
        from dados.model_prontuario import normalizar_data
        import threading

        ref_ov = [None]

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        # Labs distintos para sugestao
        labs = _labs_distintos()

        tf_lab = ft.TextField(
            label="Laboratório",
            value=ex.get("laboratorio") or "",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
        )
        tf_medico = ft.TextField(
            label="Médico solicitante",
            value=ex.get("medico_solicit") or "",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
        )

        data_ini = ex.get("data_exame") or ""
        if data_ini and len(data_ini) == 10 and data_ini[4] == "-":
            d, mo, y = data_ini[8:], data_ini[5:7], data_ini[:4]
            data_ini = f"{d}/{mo}/{y}"
        row_data, tf_data = campo_data(
            page, "Data coleta", value=data_ini,
            cor_acento=AZUL, bgcolor=CARD, border_color=BD2,
        )

        txt_status = ft.Text("", size=11, color=VERD, visible=False)

        def _salvar(e=None):
            data_iso = normalizar_data(tf_data.value) if tf_data.value else None
            try:
                conn = sqlite3.connect(DB_PATH, timeout=10)
                conn.execute("""
                    UPDATE exames SET
                        laboratorio   = ?,
                        medico_solicit = ?,
                        data_exame    = COALESCE(?, data_exame)
                    WHERE id = ?
                """, (
                    (tf_lab.value or "").strip() or None,
                    (tf_medico.value or "").strip() or None,
                    data_iso,
                    ex["id"],
                ))
                conn.commit()
                conn.close()
            except Exception as err:
                txt_status.value = f"Erro: {err}"
                txt_status.color = VERM
                txt_status.visible = True
                try: page.update()
                except Exception: pass
                return
            txt_status.value = "Salvo."
            txt_status.color = VERD
            txt_status.visible = True
            try: page.update()
            except Exception: pass
            import time; time.sleep(0.6)
            _fechar()
            _carregar_exames()

        # arquivo selecionado pelo usuario (pode trocar)
        _arquivo_sel = [ex.get("arquivo_origem") or ""]
        txt_arquivo = ft.Text(
            _arquivo_sel[0].split("\\")[-1].split("/")[-1] if _arquivo_sel[0] else "Nenhum arquivo",
            size=10, color=SEC if _arquivo_sel[0] else MUT,
            no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
        )

        def _trocar_pdf(e=None):
            import tkinter as tk
            from tkinter import filedialog
            try:
                root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
                path = filedialog.askopenfilename(
                    title="Selecionar PDF",
                    filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")],
                )
                root.destroy()
                if path:
                    _arquivo_sel[0] = path
                    txt_arquivo.value = path.split("\\")[-1].split("/")[-1]
                    txt_arquivo.color = VERD
                    txt_status.value = "PDF selecionado. Clique em Reprocessar."
                    txt_status.color = AZUL
                    txt_status.visible = True
                    try: page.update()
                    except Exception: pass
            except Exception as err:
                txt_status.value = f"Erro ao abrir seletor: {err}"
                txt_status.color = VERM
                txt_status.visible = True
                try: page.update()
                except Exception: pass

        def _reprocessar(e=None):
            arquivo = _arquivo_sel[0]
            if not arquivo:
                txt_status.value = "Selecione um PDF primeiro."
                txt_status.color = AMAR
                txt_status.visible = True
                try: page.update()
                except Exception: pass
                return
            txt_status.value = "Reprocessando..."
            txt_status.color = AZUL
            txt_status.visible = True
            try: page.update()
            except Exception: pass

            def _run():
                try:
                    from extratores.extrator_pdf import extrair_dados_pdf
                    from extratores.processador_exame import salvar_exame
                    dados = extrair_dados_pdf(arquivo)
                    if dados:
                        conn2 = sqlite3.connect(DB_PATH, timeout=10)
                        conn2.execute("DELETE FROM exame_resultados WHERE exame_id=?", (ex["id"],))
                        conn2.execute("UPDATE exames SET arquivo_origem=? WHERE id=?",
                                      (arquivo, ex["id"]))
                        conn2.commit()
                        conn2.close()
                        salvar_exame(dados, exame_id_existente=ex["id"])
                        txt_status.value = "Reprocessado com sucesso."
                        txt_status.color = VERD
                    else:
                        txt_status.value = "Nao foi possivel extrair dados do PDF."
                        txt_status.color = AMAR
                except Exception as err:
                    txt_status.value = f"Erro: {err}"
                    txt_status.color = VERM
                txt_status.visible = True
                try: page.update()
                except Exception: pass
            threading.Thread(target=_run, daemon=True).start()

        btn_cancel = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border_radius=8, bgcolor=f"{SEC}22", ink=True,
        )
        btn_cancel.on_click = _fechar

        btn_salvar = ft.Container(
            content=ft.Text("Salvar", size=13, color=VERD,
                            weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border_radius=8, bgcolor=f"{VERD}22", ink=True,
        )
        btn_salvar.on_click = _salvar

        btn_trocar = ft.Container(
            content=ft.Row([
                ft.Icon("upload_file_rounded", size=13, color=LAR),
                ft.Text("Trocar PDF", size=12, color=LAR),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_radius=8,
            bgcolor=ft.Colors.with_opacity(0.10, LAR),
            border=ft.border.all(1, ft.Colors.with_opacity(0.3, LAR)),
            ink=True,
        )
        btn_trocar.on_click = _trocar_pdf

        btn_reproces = ft.Container(
            content=ft.Row([
                ft.Icon("refresh_rounded", size=13, color=AZUL),
                ft.Text("Reprocessar", size=12, color=AZUL),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_radius=8,
            bgcolor=ft.Colors.with_opacity(0.10, AZUL),
            border=ft.border.all(1, ft.Colors.with_opacity(0.3, AZUL)),
            ink=True,
        )
        btn_reproces.on_click = _reprocessar

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("edit_rounded", size=16, color=AZUL),
                        ft.Text("Editar Exame", size=15, color=TXT,
                                weight=ft.FontWeight.W_700, expand=True),
                    ], spacing=8),
                    ft.Text(
                        (ex.get("tipo_exame") or ex.get("arquivo_origem") or f"#{ex['id']}")[:50],
                        size=11, color=MUT,
                    ),
                    ft.Divider(color=BD, height=1),
                    tf_lab,
                    row_data,
                    tf_medico,
                    ft.Divider(color=BD, height=1),
                    ft.Row([
                        ft.Icon("picture_as_pdf_rounded", size=12, color=MUT),
                        txt_arquivo,
                    ], spacing=6),
                    ft.Row([btn_trocar, btn_reproces], spacing=8),
                    txt_status,
                    ft.Row([btn_cancel, btn_salvar], spacing=8,
                           alignment=ft.MainAxisAlignment.END),
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

    def _abrir_pdf(drive_id):
        if drive_id:
            webbrowser.open(f"https://drive.google.com/file/d/{drive_id}/view")
        else:
            page.snack_bar = ft.SnackBar(
                content=ft.Text("PDF não disponível no Drive", color=TXT), bgcolor=CARD)
            page.snack_bar.open = True
            page.update()

    # ── ABA 1: EXAMES ────────────────────────────────────────
    def _carregar_exames():
        corpo_exames.controls.clear()
        exames = _listar_exames(
            filtro_tipo=dd_tipo.value or None,
            filtro_lab=dd_lab.value or None,
            filtro_texto=busca_exames.value.strip() or None,
        )
        total = len(exames)
        num   = sum(1 for e in exames if e["tipo"] == "numerico")
        lau   = sum(1 for e in exames if e["tipo"] == "laudo")
        mapa  = sum(1 for e in exames if e["tipo"] == "mapa")

        # Resumo
        corpo_exames.controls.append(ft.Container(
            content=ft.Row([
                ft.Text(f"{total} exame(s)", size=12, color=AZUL,
                        weight=ft.FontWeight.W_600, expand=True),
                ft.Container(
                    content=ft.Text(
                        f"{num} numéricos · {lau} laudos" + (f" · {mapa} MAPA" if mapa else ""),
                        size=10, color=MUT),
                    bgcolor=f"{AZUL}12", border_radius=6,
                    padding=ft.padding.symmetric(horizontal=8, vertical=3)),
            ]),
            padding=ft.padding.only(bottom=4)))

        if not exames:
            corpo_exames.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("search_off_rounded", size=40, color=MUT),
                    ft.Text("Nenhum exame encontrado.", color=SEC, size=13),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=40))
        else:
            for ex in exames:
                def _mk(e=ex):
                    def _reprocess_direto(ev, x=e):
                        arquivo = x.get("arquivo_origem") or ""
                        if not arquivo:
                            return
                        # overlay de progresso
                        ref_ov_r = [None]
                        txt_prog = ft.Text("Reprocessando...", size=12, color=AZUL)
                        ref_ov_r[0] = ft.Container(
                            content=ft.Container(
                                content=ft.Column([
                                    ft.ProgressRing(color=AZUL, width=32, height=32, stroke_width=3),
                                    ft.Container(height=8),
                                    txt_prog,
                                ], tight=True, spacing=4,
                                   horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                bgcolor=CARD, border_radius=14,
                                padding=ft.padding.all(24), width=260,
                            ),
                            bgcolor="#CC000000", expand=True,
                            alignment=ft.alignment.Alignment(0, 0),
                        )
                        page.overlay.append(ref_ov_r[0])
                        try: page.update()
                        except Exception: pass

                        def _run():
                            try:
                                from extratores.extrator_pdf import extrair_dados_pdf
                                from extratores.processador_exame import salvar_exame
                                dados = extrair_dados_pdf(arquivo)
                                if dados:
                                    conn2 = sqlite3.connect(DB_PATH, timeout=10)
                                    conn2.execute("DELETE FROM exame_resultados WHERE exame_id=?", (x["id"],))
                                    conn2.commit(); conn2.close()
                                    salvar_exame(dados, exame_id_existente=x["id"])
                                    txt_prog.value = "Reprocessado com sucesso!"
                                    txt_prog.color = VERD
                                else:
                                    txt_prog.value = "Não foi possível extrair dados."
                                    txt_prog.color = AMAR
                            except Exception as err:
                                txt_prog.value = f"Erro: {err}"
                                txt_prog.color = VERM
                            try: page.update()
                            except Exception: pass
                            import time; time.sleep(1.5)
                            if ref_ov_r[0] in page.overlay:
                                page.overlay.remove(ref_ov_r[0])
                            _carregar_exames()
                            try: page.update()
                            except Exception: pass

                        import threading
                        threading.Thread(target=_run, daemon=True).start()

                    return _card_exame(
                        e,
                        on_click_fn=lambda ev, x=e: _abrir_detalhe(
                            x["id"], x.get("tipo_exame") or x.get("arquivo_origem") or f"Exame #{x['id']}"),
                        on_pdf_fn=lambda ev, d=e.get("drive_file_id"): _abrir_pdf(d),
                        on_edit_fn=lambda ev, x=e: _abrir_edicao(x),
                        on_reprocess_fn=_reprocess_direto,
                    )
                corpo_exames.controls.append(_mk())

        if aba_ativa[0] == "exames":
            page.update()

    # ── ABA 2: MÉDICO ────────────────────────────────────────
    medico_selecionado = [None]
    lista_medicos_col  = ft.Column(spacing=4)
    exames_medico_col  = ft.Column(spacing=6)

    def _carregar_medicos():
        lista_medicos_col.controls.clear()
        exames_medico_col.controls.clear()
        medico_selecionado[0] = None
        texto = busca_medico.value.strip().lower()
        medicos = _listar_medicos()
        if texto:
            medicos = [m for m in medicos
                       if texto in (m["nome"] or "").lower()
                       or texto in (m["especialidade"] or "").lower()]

        if not medicos:
            lista_medicos_col.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon("person_search_rounded", size=36, color=MUT),
                        ft.Text("Nenhum médico encontrado.", color=SEC, size=12),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                    padding=24))
        else:
            for m in medicos:
                def _mk_btn(med=m):
                    def _sel(e):
                        medico_selecionado[0] = med
                        _carregar_exames_medico(med)
                    return ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Icon("person_outline_rounded", size=16, color=AZUL),
                                bgcolor=f"{AZUL}18", border_radius=6,
                                width=32, height=32,
                                alignment=ft.alignment.Alignment(0, 0)),
                            ft.Column([
                                ft.Text(med["nome"] or "Sem nome", size=12,
                                        color=TXT, weight=ft.FontWeight.W_600),
                                ft.Text(med["especialidade"] or "sem especialidade",
                                        size=10, color=SEC),
                            ], spacing=1, expand=True),
                            ft.Icon("chevron_right_rounded", size=14, color=MUT),
                        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor=CARD, border_radius=8,
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        border=ft.Border(
                            top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                            left=ft.BorderSide(1, BD), right=ft.BorderSide(1, BD)),
                        on_click=_sel, ink=True)
                lista_medicos_col.controls.append(_mk_btn())

        if aba_ativa[0] == "medico":
            page.update()

    def _carregar_exames_medico(medico):
        exames_medico_col.controls.clear()
        exames = _exames_do_medico(medico["id"])

        exames_medico_col.controls.append(ft.Container(
            content=ft.Row([
                ft.Icon("assignment_outlined_rounded", size=14, color=AZUL),
                ft.Text(f"{len(exames)} exame(s) de {medico['nome']}",
                        size=12, color=AZUL, weight=ft.FontWeight.W_600),
            ], spacing=6),
            padding=ft.padding.only(bottom=4, top=8)))

        if not exames:
            exames_medico_col.controls.append(
                ft.Text("Nenhum exame vinculado a este médico.", size=12, color=MUT))
        else:
            for ex in exames:
                def _mk(e=ex):
                    return _card_exame(
                        e,
                        on_click_fn=lambda ev, x=e: _abrir_detalhe(
                            x["id"], x.get("tipo_exame") or f"Exame #{x['id']}"),
                        on_pdf_fn=lambda ev, d=e.get("drive_file_id"): _abrir_pdf(d),
                    )
                exames_medico_col.controls.append(_mk())

        page.update()

    corpo_medico.controls.extend([
        ft.Container(content=busca_medico,
                     padding=ft.padding.only(bottom=8)),
        lista_medicos_col,
        exames_medico_col,
    ])

    # ── ABA 3: CLASSIFICAÇÃO ─────────────────────────────────
    cat_col     = ft.Column(spacing=4)
    result_col  = ft.Column(spacing=4)

    def _carregar_classif():
        if cat_selecionada[0]:
            _carregar_resultados_cat(cat_selecionada[0])
        else:
            _montar_categorias()

    def _montar_categorias():
        cat_col.controls.clear()
        result_col.controls.clear()
        categorias = _listar_categorias()

        cat_col.controls.append(ft.Container(
            content=ft.Text("Selecione uma categoria", size=12,
                            color=SEC, weight=ft.FontWeight.W_600),
            padding=ft.padding.only(bottom=6)))

        for cat in categorias:
            cor = _cor_cat(cat)
            def _mk(c=cat):
                def _sel(e):
                    cat_selecionada[0] = c
                    _carregar_resultados_cat(c)
                return ft.Container(
                    content=ft.Row([
                        ft.Container(width=4, height=36, bgcolor=cor, border_radius=2),
                        ft.Container(width=8),
                        ft.Text(c, size=12, color=TXT,
                                weight=ft.FontWeight.W_500, expand=True),
                        ft.Icon("chevron_right_rounded", size=14, color=MUT),
                    ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD, border_radius=8,
                    padding=ft.padding.symmetric(vertical=4, horizontal=6),
                    border=ft.Border(
                        top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                        left=ft.BorderSide(1, BD), right=ft.BorderSide(1, BD)),
                    on_click=_sel, ink=True)
            cat_col.controls.append(_mk())

        if aba_ativa[0] == "classificacao":
            page.update()

    def _carregar_resultados_cat(categoria):
        result_col.controls.clear()
        cor   = _cor_cat(categoria)
        texto = busca_classif.value.strip() or None
        rows  = _resultados_por_categoria(categoria, filtro_texto=texto)

        # Header com botão voltar
        result_col.controls.append(ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Row([
                        ft.Icon("arrow_back_rounded", size=13, color=SEC),
                        ft.Text("Categorias", size=11, color=SEC),
                    ], spacing=4, tight=True),
                    padding=ft.padding.symmetric(horizontal=8, vertical=8),
                    ink=True,
                    on_click=lambda e: _voltar_categorias()),
                ft.Container(
                    content=ft.Row([
                        ft.Container(width=3, height=18, bgcolor=cor, border_radius=1),
                        ft.Container(width=6),
                        ft.Text(categoria, size=13, color=TXT,
                                weight=ft.FontWeight.W_600),
                        ft.Text(f"  {len(rows)} resultado(s)", size=11, color=MUT),
                    ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    expand=True),
            ], spacing=4),
            padding=ft.padding.only(bottom=8)))

        if not rows:
            result_col.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon("science_outlined_rounded", size=36, color=MUT),
                        ft.Text("Nenhum resultado nesta categoria.", color=SEC, size=12),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                    padding=24))
        else:
            for r in rows:
                ref  = r.get("referencia") or ""
                data = r.get("data_exame") or ""
                lab  = r.get("laboratorio") or ""
                result_col.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(r["parametro"] or "", size=12, color=TXT,
                                    weight=ft.FontWeight.W_500),
                            ft.Row([
                                ft.Text(data[:10], size=9, color=MUT),
                                ft.Text("·", size=9, color=MUT) if lab else ft.Container(),
                                ft.Text(lab, size=9, color=ROXO),
                            ], spacing=3),
                        ], spacing=1, expand=True),
                        ft.Column([
                            ft.Row([
                                ft.Text(r["valor"] or "", size=13, color=cor,
                                        weight=ft.FontWeight.W_700),
                                ft.Text(r["unidade"] or "", size=10, color=MUT),
                            ], spacing=3),
                            ft.Text(ref[:30], size=8, color=MUT) if ref else ft.Container(),
                        ], spacing=1, horizontal_alignment=ft.CrossAxisAlignment.END),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD, border_radius=7,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    border=ft.Border(
                        left=ft.BorderSide(2, cor),
                        top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                        right=ft.BorderSide(1, BD)),
                    on_click=lambda ev, eid=r["exame_id"], par=r["parametro"]: _abrir_detalhe(eid, par),
                    ink=True))

        cat_col.controls.clear()
        if aba_ativa[0] == "classificacao":
            page.update()

    def _voltar_categorias():
        cat_selecionada[0] = None
        result_col.controls.clear()
        _montar_categorias()

    corpo_classif.controls.extend([
        ft.Container(content=busca_classif,
                     padding=ft.padding.only(bottom=8)),
        cat_col,
        result_col,
    ])

    # ── Abas (tabs customizadas) ─────────────────────────────
    def _cor_aba(nome):
        return AZUL if aba_ativa[0] == nome else MUT

    def _peso_aba(nome):
        return ft.FontWeight.W_600 if aba_ativa[0] == nome else ft.FontWeight.W_400

    def _borda_aba(nome):
        return ft.Border(bottom=ft.BorderSide(2, AZUL)) if aba_ativa[0] == nome \
               else ft.Border(bottom=ft.BorderSide(2, "transparent"))

    def _tab(icone, label, nome, ref_container):
        return ft.Container(
            ref=ref_container,
            content=ft.Row([
                ft.Icon(icone, size=14, color=_cor_aba(nome)),
                ft.Text(label, size=12, color=_cor_aba(nome),
                        weight=_peso_aba(nome)),
            ], spacing=5, tight=True),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border=_borda_aba(nome),
            on_click=lambda e, n=nome: _trocar_aba(n),
            ink=True)

    aba_exames_tab  = _tab("description_outlined_rounded", "Exames", "exames", _btn_exames)
    aba_medico_tab  = _tab("person_outlined_rounded",      "Médico", "medico", _btn_medico)
    aba_classif_tab = _tab("category_outlined_rounded",    "Classificação", "classificacao", _btn_classif)

    conteudo_area = ft.Container(expand=True)

    def _trocar_aba(nome):
        aba_ativa[0] = nome

        # Atualizar visual dos tabs
        for tab, n in [(aba_exames_tab, "exames"),
                       (aba_medico_tab, "medico"),
                       (aba_classif_tab, "classificacao")]:
            row = tab.content
            row.controls[0].color = _cor_aba(n)
            row.controls[1].color = _cor_aba(n)
            row.controls[1].weight = _peso_aba(n)
            tab.border = _borda_aba(n)

        # Trocar conteúdo
        if nome == "exames":
            conteudo_area.content = ft.Column([
                ft.Container(
                    content=ft.Column([
                        busca_exames,
                        ft.Row([dd_tipo, dd_lab], spacing=8),
                    ], spacing=8),
                    padding=ft.padding.only(bottom=8)),
                ft.Container(content=corpo_exames, expand=True),
            ], spacing=0, expand=True)
            _carregar_exames()
        elif nome == "medico":
            conteudo_area.content = ft.Container(content=corpo_medico, expand=True)
            _carregar_medicos()
        elif nome == "classificacao":
            conteudo_area.content = ft.Container(content=corpo_classif, expand=True)
            _montar_categorias()

        page.update()

    # Carga inicial
    _trocar_aba("exames")

    # ── Layout responsivo ────────────────────────────────────
    tabs_row = ft.Container(
        content=ft.Row(
            [aba_exames_tab, aba_medico_tab, aba_classif_tab],
            spacing=0),
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
        bgcolor=CARD)

    header = ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Row([
                    ft.Icon("arrow_back_rounded", size=14, color=SEC),
                    ft.Text("Voltar", size=12, color=SEC),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                ink=True,
                on_click=lambda e: voltar_fn()),
            ft.Row([
                ft.Icon("description_rounded", size=18, color=AMAR),
                ft.Text("Exames Processados", size=16,
                        weight=ft.FontWeight.W_700, color=TXT),
            ], spacing=6, tight=True, expand=True),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        border=ft.Border(bottom=ft.BorderSide(1, BD)))

    corpo_scroll = ft.Container(
        content=conteudo_area,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        expand=True)

    tela = ft.Container(
        bgcolor=BG, expand=True,
        content=ft.Column([header, tabs_row, corpo_scroll],
                          spacing=0, expand=True))

    # Responsividade — centraliza em telas largas
    if larg > 600:
        return ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Row([
                ft.Container(expand=True),
                ft.Container(content=tela, width=520),
                ft.Container(expand=True),
            ], expand=True))

    return tela
