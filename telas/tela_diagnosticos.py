# -*- coding: utf-8 -*-
# Prontuario | telas/tela_diagnosticos.py
# Lista, inclusao e edicao de diagnosticos medicos
import flet as ft
import logging
from shared.layout import Layout
from shared.date_field import campo_data
from dados.model_prontuario import (
    normalizar_data,
    listar_diagnosticos, salvar_diagnostico, excluir_diagnostico,
)

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; AMAR = "#D29922"
VERM = "#F85149"; ROXO = "#BC8CFF"; LAR  = "#F0883E"

_STATUS_COR = {
    "ativo":    LAR,
    "cronico":  VERM,
    "resolvido":VERD,
    "suspeito": AMAR,
}
_STATUS_OPTS  = ["ativo", "cronico", "resolvido", "suspeito"]
_CERTEZA_OPTS = ["confirmado", "provavel", "suspeito", "descartado"]
_SISTEMAS = [
    "Cardiaco", "Visceral", "Sangue", "Ortopedia",
    "Psiquiatria", "Visao & Audicao", "Outros",
]


def _para_display(s):
    if s and len(s) >= 10 and s[4:5] == "-":
        try:
            from datetime import datetime
            return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            pass
    return s or ""


def criar_tela_diagnosticos(page: ft.Page, voltar_fn=None,
                             sistema_filtro: str = None):
    lay      = Layout(page)
    area     = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
    _montado = [False]

    def _snack(msg, cor=VERD):
        s = ft.SnackBar(content=ft.Text(msg, color=TXT), bgcolor=CARD)
        page.overlay.append(s)
        s.open = True
        try: page.update()
        except Exception: pass

    # -- Overlay confirmacao exclusao --------------------------------
    def _confirmar_excluir(did, titulo):
        ref_ov = [None]

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        def _excluir(e):
            excluir_diagnostico(did)
            _fechar()
            _carregar()
            _snack("Diagnóstico removido.")

        btn_cancel = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{SEC}22", ink=True,
        )
        btn_cancel.on_click = _fechar
        btn_ok = ft.Container(
            content=ft.Text("Remover", size=13, color=VERM,
                            weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{VERM}22", ink=True,
        )
        btn_ok.on_click = _excluir

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Icon("delete_outline_rounded", size=32, color=VERM),
                    ft.Text("Remover diagnóstico?", size=14, color=TXT,
                            weight=ft.FontWeight.W_700, text_align="center"),
                    ft.Text(titulo[:50], size=12, color=SEC,
                            text_align="center"),
                    ft.Container(height=8),
                    ft.Row([btn_cancel, btn_ok], spacing=8,
                           alignment=ft.MainAxisAlignment.CENTER),
                ], spacing=8, tight=True,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(24), width=300,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass

    # -- Form overlay ------------------------------------------------
    def _abrir_form(diag=None):
        ref_ov = [None]
        _id = diag.get("id") if diag else None

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        tf_titulo = ft.TextField(
            label="Título / Nome do diagnóstico *",
            value=diag.get("titulo","") if diag else "",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, autofocus=not bool(diag),
        )
        tf_cid = ft.TextField(
            label="CID (opcional)",
            value=diag.get("cid","") if diag else "",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            hint_text="Ex: I25.1, E11, F41.1",
            hint_style=ft.TextStyle(color=MUT, size=11),
        )
        tf_descricao = ft.TextField(
            label="Descrição / O que foi dito",
            value=diag.get("descricao","") if diag else "",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, multiline=True, min_lines=2, max_lines=4,
            hint_text="Ex: Verrucosidades nas veias coronárias com risco de obstrução...",
            hint_style=ft.TextStyle(color=MUT, size=10),
        )
        dd_sistema = ft.Dropdown(
            label="Sistema corporal",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            value=diag.get("sistema") if diag else sistema_filtro,
            options=[ft.dropdown.Option(s) for s in _SISTEMAS],
        )
        dd_status = ft.Dropdown(
            label="Status",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            value=diag.get("status","ativo") if diag else "ativo",
            options=[ft.dropdown.Option(s) for s in _STATUS_OPTS],
        )
        dd_certeza = ft.Dropdown(
            label="Certeza diagnóstica",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            value=diag.get("certeza","confirmado") if diag else "confirmado",
            options=[ft.dropdown.Option(s) for s in _CERTEZA_OPTS],
        )
        row_data_diag, tf_data_diag = campo_data(
            page, "Data do diagnóstico",
            value=_para_display(diag.get("data_diagnostico","")) if diag else "",
            cor_acento=AZUL, bgcolor=CARD, border_color=BD2,
        )
        tf_obs = ft.TextField(
            label="Observações",
            value=diag.get("observacoes","") if diag else "",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, multiline=True, min_lines=1, max_lines=3,
        )
        txt_erro = ft.Text("", size=11, color=VERM, visible=False)

        dd_sistema.on_change = lambda e: None
        dd_status.on_change  = lambda e: None
        dd_certeza.on_change = lambda e: None

        def _salvar(e=None):
            titulo = (tf_titulo.value or "").strip()
            if not titulo:
                txt_erro.value = "Informe o título do diagnóstico."
                txt_erro.visible = True
                try: page.update()
                except Exception: pass
                return
            dados = {
                "titulo":           titulo,
                "cid":              (tf_cid.value or "").strip() or None,
                "descricao":        (tf_descricao.value or "").strip() or None,
                "sistema":          dd_sistema.value,
                "status":           dd_status.value or "ativo",
                "certeza":          dd_certeza.value or "confirmado",
                "data_diagnostico": normalizar_data(tf_data_diag.value)
                                    if tf_data_diag.value else None,
                "observacoes":      (tf_obs.value or "").strip() or None,
            }
            if _id:
                dados["id"] = _id
            salvar_diagnostico(dados)
            _fechar()
            _carregar()
            _snack("Salvo com sucesso.")

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
        tf_titulo.on_submit = _salvar

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("diagnosis_rounded", size=16, color=AZUL),
                        ft.Text("Editar Diagnóstico" if _id else "Novo Diagnóstico",
                                size=15, color=TXT, weight=ft.FontWeight.W_700,
                                expand=True),
                    ], spacing=8),
                    ft.Divider(color=BD, height=1),
                    tf_titulo,
                    tf_cid,
                    tf_descricao,
                    ft.Row([dd_sistema, dd_status], spacing=8),
                    dd_certeza,
                    row_data_diag,
                    tf_obs,
                    txt_erro,
                    ft.Container(height=4),
                    ft.Row([btn_cancel, btn_ok], spacing=8,
                           alignment=ft.MainAxisAlignment.END),
                ], spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20), width=360, height=520,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass

    # -- Lista -------------------------------------------------------
    def _carregar():
        area.controls.clear()
        diags = listar_diagnosticos(sistema=sistema_filtro)

        if not diags:
            area.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("diagnosis_rounded", size=48, color=MUT),
                    ft.Text("Nenhum diagnóstico registrado.", size=14, color=SEC),
                    ft.Text("Toque em + Novo para adicionar.", size=12, color=MUT),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                alignment=ft.alignment.Alignment(0, 0), padding=50,
            ))
        else:
            _ORDEM = ["ativo", "cronico", "suspeito", "resolvido"]
            grupos = {}
            for d in diags:
                grupos.setdefault(d.get("status","ativo"), []).append(d)

            for status in _ORDEM:
                lista = grupos.get(status, [])
                if not lista: continue
                cor_s = _STATUS_COR.get(status, SEC)
                area.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Container(width=8, height=8, bgcolor=cor_s,
                                     border_radius=4),
                        ft.Text(status.upper(), size=10, color=cor_s,
                                weight=ft.FontWeight.W_700),
                        ft.Text(f"({len(lista)})", size=10, color=MUT),
                    ], spacing=6),
                    padding=ft.padding.only(top=8, bottom=4),
                ))
                for d in lista:
                    cor_d  = _STATUS_COR.get(d.get("status",""), MUT)
                    certeza = d.get("certeza","")
                    data_txt = _para_display(d.get("data_diagnostico",""))
                    sis_txt  = d.get("sistema") or ""
                    desc     = (d.get("descricao") or "")[:100]

                    btn_edit = ft.Container(
                        content=ft.Icon("edit_rounded", size=15, color=SEC),
                        padding=ft.padding.all(8), border_radius=8, ink=True,
                    )
                    btn_del = ft.Container(
                        content=ft.Icon("delete_outline_rounded", size=15,
                                        color=VERM),
                        padding=ft.padding.all(8), border_radius=8, ink=True,
                    )
                    _d = dict(d)
                    btn_edit.on_click = lambda e, x=_d: _abrir_form(x)
                    btn_del.on_click  = lambda e, x=_d: _confirmar_excluir(
                        x["id"], x["titulo"])

                    _card = ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Column([
                                    ft.Row([
                                        ft.Text(d.get("titulo",""), size=14,
                                                color=TXT,
                                                weight=ft.FontWeight.W_700,
                                                expand=True),
                                        ft.Container(
                                            content=ft.Text(
                                                certeza, size=9, color=cor_d,
                                                weight=ft.FontWeight.W_600),
                                            bgcolor=ft.Colors.with_opacity(
                                                0.12, cor_d),
                                            border_radius=6,
                                            padding=ft.padding.symmetric(
                                                horizontal=6, vertical=2),
                                        ),
                                    ], spacing=6),
                                    ft.Row([
                                        ft.Text(f"CID {d.get('cid','')}",
                                                size=10, color=AZUL,
                                                visible=bool(d.get("cid"))),
                                        ft.Text(sis_txt, size=10, color=SEC,
                                                visible=bool(sis_txt)),
                                        ft.Text(data_txt, size=10, color=MUT,
                                                visible=bool(data_txt)),
                                    ], spacing=8),
                                    ft.Text(desc, size=11, color=SEC,
                                            visible=bool(desc)),
                                ], spacing=3, expand=True),
                                ft.Row([btn_edit, btn_del], spacing=0),
                            ], spacing=8,
                               vertical_alignment=ft.CrossAxisAlignment.START),
                        ], spacing=4),
                        bgcolor=CARD, border_radius=10,
                        padding=ft.padding.symmetric(horizontal=14, vertical=12),
                        border=ft.Border(
                            left=ft.BorderSide(3, cor_d),
                            top=ft.BorderSide(1, BD),
                            bottom=ft.BorderSide(1, BD),
                            right=ft.BorderSide(1, BD),
                        ),
                        ink=True,
                    )
                    _card.on_click = lambda e, x=_d: _abrir_tratamento(x)
                    area.controls.append(_card)

        if _montado[0]:
            try: page.update()
            except Exception: pass

    _carregar()

    btn_novo = ft.Container(
        content=ft.Row([
            ft.Icon("add_rounded", size=16, color=AZUL),
            ft.Text("Novo", size=13, color=AZUL),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8, ink=True,
    )
    btn_novo.on_click = lambda e: _abrir_form()

    def _abrir_tratamento(diag: dict):
        ref = [None]

        def _fechar(e=None):
            if ref[0] in page.overlay:
                page.overlay.remove(ref[0])
            try: page.update()
            except Exception: pass

        # buscar médicos e remédios para os dropdowns
        try:
            from dados.model_prontuario import listar_medicos, listar_remedios
            medicos  = listar_medicos() or []
            remedios = listar_remedios() or []
        except Exception:
            medicos  = []
            remedios = []

        cor_d   = _STATUS_COR.get(diag.get("status", ""), MUT)
        titulo  = diag.get("titulo", "")
        origem  = diag.get("origem", "diagnosticos")

        # --- médico: busca padrão Koios ---
        _medico_sel = [None]  # {"id": ..., "nome": ...}
        # pre-selecionar se já tem médico
        if diag.get("medico_id"):
            _m = next((m for m in medicos if m["id"] == diag["medico_id"]), None)
            if _m:
                _medico_sel[0] = _m

        txt_medico_sel = ft.Text(
            _medico_sel[0]["nome"] if _medico_sel[0] else "Nenhum selecionado",
            size=11, color=AZUL if _medico_sel[0] else MUT,
        )

        f_busca_med = ft.TextField(
            label="Buscar médico",
            prefix_icon="search_rounded",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            value="",
            autofocus=False,
        )
        lista_med_col = ft.Column([], spacing=4)

        def _filtrar_medicos(e=None):
            q = (f_busca_med.value or "").lower()
            lista_med_col.controls.clear()
            if not q:
                try: page.update()
                except Exception: pass
                return
            for m in medicos:
                if q not in m["nome"].lower():
                    continue
                _m = dict(m)
                sel = _medico_sel[0] and _medico_sel[0]["id"] == m["id"]
                item = ft.Container(
                    content=ft.Row([
                        ft.Icon("check_circle_rounded" if sel else "person_rounded",
                                size=14, color=AZUL if sel else SEC),
                        ft.Text(m["nome"], size=12,
                                color=AZUL if sel else TXT, expand=True),
                    ], spacing=8),
                    bgcolor=f"{AZUL}18" if sel else CARD,
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    border=ft.border.all(1, AZUL if sel else BD),
                    ink=True,
                )
                item.on_click = lambda e, x=_m: _sel_medico(x)
                lista_med_col.controls.append(item)
            try: page.update()
            except Exception: pass

        def _sel_medico(m):
            _medico_sel[0] = m
            txt_medico_sel.value = m["nome"]
            txt_medico_sel.color = AZUL
            _filtrar_medicos()

        f_busca_med.on_change = _filtrar_medicos
        _filtrar_medicos()

        # --- remédios: busca + seleção ---
        _remedios_sel = set()
        f_busca_rem = ft.TextField(
            label="Buscar remédio",
            prefix_icon="search_rounded",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            value="",
            autofocus=False,
        )
        lista_rem_col = ft.Column([], spacing=4)
        selecionados_col = ft.Column([], spacing=4)

        def _rebuild_selecionados():
            selecionados_col.controls.clear()
            for rid in list(_remedios_sel):
                rem = next((r for r in remedios if str(r.get("id","")) == rid), None)
                if not rem:
                    continue
                chip = ft.Container(
                    content=ft.Row([
                        ft.Text(rem.get("nome",""), size=11, color=BG, expand=True),
                        ft.Icon("close_rounded", size=12, color=BG),
                    ], spacing=6),
                    bgcolor=AZUL, border_radius=20,
                    padding=ft.padding.symmetric(horizontal=10, vertical=5),
                    ink=True,
                )
                chip.on_click = lambda e, r=rid: (_remedios_sel.discard(r),
                                                   _rebuild_selecionados(),
                                                   _filtrar_remedios())
                selecionados_col.controls.append(chip)
            try: page.update()
            except Exception: pass

        def _filtrar_remedios(e=None):
            q = (f_busca_rem.value or "").lower()
            lista_rem_col.controls.clear()
            if not q:
                try: page.update()
                except Exception: pass
                return
            for rem in remedios:
                rid = str(rem.get("id",""))
                if rid in _remedios_sel:
                    continue
                if q not in rem.get("nome","").lower():
                    continue
                item = ft.Container(
                    content=ft.Row([
                        ft.Icon("add_rounded", size=14, color=VERD),
                        ft.Text(rem.get("nome",""), size=12,
                                color=TXT, expand=True),
                    ], spacing=8),
                    bgcolor=CARD, border_radius=8,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    border=ft.border.all(1, BD),
                    ink=True,
                )
                item.on_click = lambda e, r=rid: (
                    _remedios_sel.add(r),
                    setattr(f_busca_rem, "value", ""),
                    _rebuild_selecionados(),
                    _filtrar_remedios(),
                )
                lista_rem_col.controls.append(item)
            try: page.update()
            except Exception: pass

        _filtrar_remedios()

        f_obs = ft.TextField(
            label="Observações do tratamento",
            multiline=True, min_lines=3, max_lines=6,
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            value=diag.get("observacoes") or "",
        )

        def _salvar_tratamento(e=None):
            if origem == "diagnosticos" and diag.get("id"):
                try:
                    from dados.model_prontuario import salvar_diagnostico
                    dados_upd = dict(diag)
                    dados_upd["observacoes"] = f_obs.value
                    if _medico_sel[0]:
                        dados_upd["medico_id"] = _medico_sel[0]["id"]
                    salvar_diagnostico(dados_upd)
                except Exception as ex:
                    log.warning("salvar_tratamento: %s", ex)
            _fechar()
            _carregar()

        btn_salvar = ft.Container(
            content=ft.Row([
                ft.Icon("save_rounded", size=16, color=BG),
                ft.Text("Salvar", size=13, color=BG, weight=ft.FontWeight.W_600),
            ], spacing=6, tight=True),
            bgcolor=VERD, border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
        )
        btn_salvar.on_click = _salvar_tratamento

        btn_fechar = ft.Container(
            content=ft.Text("Fechar", size=13, color=SEC),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            bgcolor=f"{SEC}22",
        )
        btn_fechar.on_click = _fechar

        conteudo = ft.Container(
            content=ft.Column([
                # cabecalho
                ft.Container(
                    content=ft.Row([
                        ft.Container(width=4, height=40, bgcolor=cor_d,
                                     border_radius=2),
                        ft.Column([
                            ft.Text(titulo, size=15, color=TXT,
                                    weight=ft.FontWeight.W_700),
                            ft.Text("Plano de Tratamento", size=10, color=SEC),
                        ], spacing=0, tight=True, expand=True),
                        ft.Container(
                            content=ft.Icon("close_rounded", size=18, color=SEC),
                            ink=True, border_radius=8,
                            padding=ft.padding.all(6),
                            on_click=_fechar,
                        ),
                    ], spacing=10),
                    padding=ft.padding.only(bottom=12),
                    border=ft.Border(bottom=ft.BorderSide(1, BD)),
                ),
                ft.Container(height=12),
                # medico
                ft.Text("Médico Responsável", size=11, color=SEC,
                        weight=ft.FontWeight.W_600),
                ft.Container(height=4),
                ft.Row([
                    ft.Icon("person_rounded", size=14, color=AZUL),
                    txt_medico_sel,
                ], spacing=6),
                ft.Container(height=6),
                f_busca_med,
                ft.Container(
                    content=lista_med_col,
                    height=140,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                ),
                ft.Container(height=16),
                # remedios
                ft.Text("Remédios Vinculados", size=11, color=SEC,
                        weight=ft.FontWeight.W_600),
                ft.Container(height=4),
                ft.Container(
                    content=selecionados_col,
                    visible=True,
                ),
                ft.Container(height=6),
                f_busca_rem,
                ft.Container(
                    content=lista_rem_col,
                    height=140,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                ) if remedios else ft.Text("Nenhum remédio cadastrado",
                                           size=11, color=MUT),
                ft.Container(height=16),
                # observacoes
                ft.Text("Observações do Tratamento", size=11, color=SEC,
                        weight=ft.FontWeight.W_600),
                ft.Container(height=4),
                f_obs,
                ft.Container(height=20),
                # botoes
                ft.Row([btn_fechar, btn_salvar],
                       alignment=ft.MainAxisAlignment.END, spacing=10),
            ], spacing=0, scroll=ft.ScrollMode.AUTO),
            bgcolor=CARD, border_radius=14,
            padding=ft.padding.all(20),
            width=520,
        )

        ref[0] = ft.Container(
            content=ft.Row([
                ft.Container(expand=True),
                ft.Container(
                    content=conteudo,
                    alignment=ft.alignment.center,
                ),
                ft.Container(expand=True),
            ], alignment=ft.MainAxisAlignment.CENTER,
               vertical_alignment=ft.CrossAxisAlignment.CENTER,
               expand=True),
            bgcolor="#CC000000", expand=True,
            alignment=ft.alignment.center,
        )
        ref[0].on_click = _fechar
        page.overlay.append(ref[0])
        try: page.update()
        except Exception: pass

    titulo_tela = f"Diagnósticos — {sistema_filtro}" if sistema_filtro \
                  else "Diagnósticos"

    cabecalho = lay.criar_cabecalho(
        titulo_tela,
        lambda e=None: voltar_fn() if voltar_fn else None,
        icone_titulo="diagnosis_rounded",
        cor_titulo=AZUL,
        acoes=[btn_novo],
    )

    rodape = ft.Container(
        content=ft.Text("Diagnósticos — Prontuário Médico",
                        size=10, color="#30363D", text_align="center"),
        padding=ft.padding.symmetric(horizontal=20, vertical=12),
        border=ft.Border(top=ft.BorderSide(1, "#21262D")),
    )

    corpo = ft.Column([
        ft.Container(height=lay.spacer_topo, bgcolor=BG),
        cabecalho,
        ft.Container(content=area,
                     padding=ft.padding.only(left=20, right=20, top=12, bottom=12),
                     expand=True),
        rodape,
    ], spacing=0, expand=True)

    _montado[0] = True
    return ft.Container(bgcolor=BG, expand=True, content=corpo)
