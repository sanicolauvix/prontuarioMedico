# -*- coding: utf-8 -*-
# Prontuario | telas/tela_diagnosticos.py
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

_STATUS_COR  = {"ativo": LAR, "cronico": VERM, "resolvido": VERD, "suspeito": AMAR}
_STATUS_OPTS  = ["ativo", "cronico", "resolvido", "suspeito"]
_CERTEZA_OPTS = ["confirmado", "provavel", "suspeito", "descartado"]
_SISTEMAS = ["Cardiaco","Visceral","Sangue","Ortopedia","Psiquiatria","Visao & Audicao","Outros"]


def _para_display(s):
    if s and len(s) >= 10 and s[4:5] == "-":
        try:
            from datetime import datetime
            return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            pass
    return s or ""


def criar_tela_diagnosticos(page: ft.Page, voltar_fn=None, sistema_filtro: str = None):
    lay      = Layout(page)
    area     = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
    _montado = [False]

    def _snack(msg, cor=VERD):
        s = ft.SnackBar(content=ft.Text(msg, color=TXT), bgcolor=CARD)
        page.overlay.append(s)
        s.open = True
        try: page.update()
        except Exception: pass

    def _upd():
        if _montado[0]:
            try: page.update()
            except Exception: pass

    # ── Confirmar exclusão ────────────────────────────────────────────────────
    def _confirmar_excluir(did, titulo):
        ref_ov = [None]
        def _fechar(e=None):
            if ref_ov[0] in page.overlay: page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass
        def _excluir(e):
            excluir_diagnostico(did); _fechar(); _carregar()
            _snack("Diagnóstico removido.")
        btn_cancel = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{SEC}22", ink=True,
        )
        btn_cancel.on_click = _fechar
        btn_ok = ft.Container(
            content=ft.Text("Remover", size=13, color=VERM, weight=ft.FontWeight.W_600),
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
                    ft.Text(titulo[:50], size=12, color=SEC, text_align="center"),
                    ft.Container(height=8),
                    ft.Row([btn_cancel, btn_ok], spacing=8,
                           alignment=ft.MainAxisAlignment.CENTER),
                ], spacing=8, tight=True,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD, border_radius=14, padding=ft.padding.all(24), width=300,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass

    # ── Form overlay (novo/editar diagnóstico) ────────────────────────────────
    def _abrir_form(diag=None):
        ref_ov = [None]
        _id = diag.get("id") if diag else None
        def _fechar(e=None):
            if ref_ov[0] in page.overlay: page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass
        tf_titulo = ft.TextField(
            label="Título / Nome do diagnóstico *",
            value=diag.get("titulo","") if diag else "",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT), border_radius=8,
            autofocus=not bool(diag),
        )
        tf_cid = ft.TextField(
            label="CID", value=diag.get("cid","") if diag else "",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT), border_radius=8,
        )
        tf_desc = ft.TextField(
            label="Descrição",
            value=diag.get("descricao","") if diag else "",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT), border_radius=8,
            multiline=True, min_lines=2, max_lines=4,
        )
        dd_status = ft.Dropdown(
            label="Status",
            value=diag.get("status","ativo") if diag else "ativo",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT), border_radius=8,
            options=[ft.dropdown.Option(s) for s in _STATUS_OPTS],
        )
        dd_status.on_change = lambda e: None
        dd_certeza = ft.Dropdown(
            label="Certeza",
            value=diag.get("certeza","confirmado") if diag else "confirmado",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT), border_radius=8,
            options=[ft.dropdown.Option(c) for c in _CERTEZA_OPTS],
        )
        dd_certeza.on_change = lambda e: None
        dd_sistema = ft.Dropdown(
            label="Sistema",
            value=diag.get("sistema") if diag else None,
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT), border_radius=8,
            options=[ft.dropdown.Option(s) for s in _SISTEMAS],
        )
        dd_sistema.on_change = lambda e: None
        row_data, f_data = campo_data(
            page, label="Data do diagnóstico",
            value=diag.get("data_diagnostico","") if diag else "",
            cor_acento=AZUL,
        )

        def _salvar(e):
            if not tf_titulo.value.strip():
                tf_titulo.error_text = "Obrigatório"
                try: page.update()
                except Exception: pass
                return
            dados = {
                "id":               _id,
                "titulo":           tf_titulo.value.strip(),
                "cid":              tf_cid.value.strip(),
                "descricao":        tf_desc.value.strip(),
                "status":           dd_status.value,
                "certeza":          dd_certeza.value,
                "sistema":          dd_sistema.value,
                "data_diagnostico": normalizar_data(f_data.value),
                "ativo":            1,
            }
            salvar_diagnostico(dados)
            _fechar(); _carregar()
            _snack("Diagnóstico salvo.")

        btn_cancel = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{SEC}22", ink=True,
        )
        btn_cancel.on_click = _fechar
        btn_ok = ft.Container(
            content=ft.Text("Salvar", size=13, color=AZUL, weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{AZUL}22", ink=True,
        )
        btn_ok.on_click = _salvar

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Novo Diagnóstico" if not _id else "Editar Diagnóstico",
                            size=14, color=TXT, weight=ft.FontWeight.W_700),
                    ft.Container(height=8),
                    tf_titulo, tf_cid,
                    ft.Row([dd_status, dd_certeza], spacing=8),
                    dd_sistema,
                    row_data,
                    tf_desc,
                    ft.Container(height=8),
                    ft.Row([btn_cancel, btn_ok], spacing=8,
                           alignment=ft.MainAxisAlignment.END),
                ], spacing=8, scroll=ft.ScrollMode.AUTO),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20), width=480,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass

    # ── Tratamento colapsável inline ──────────────────────────────────────────
    def _mk_tratamento_widget(d: dict, cor_d: str):
        """Retorna o widget de tratamento colapsável para um diagnóstico."""
        origem    = d.get("origem", "diagnosticos")
        origem_id = d.get("id", 0)
        _aberto   = [False]
        _editando = [False]

        corpo_trat   = ft.Column([], spacing=0)
        ico_chevron  = ft.Icon("expand_more_rounded", size=14, color=SEC)

        try:
            from dados.model_prontuario import (
                listar_medicos, listar_remedios,
                carregar_tratamento_diagnostico, salvar_tratamento_diagnostico,
            )
            medicos   = listar_medicos() or []
            remedios  = listar_remedios() or []
        except Exception:
            medicos  = []
            remedios = []

            def carregar_tratamento_diagnostico(*a): return {"medico_id": None, "observacoes": "", "data_revisao": "", "remedios": []}
            def salvar_tratamento_diagnostico(*a, **k): return False

        def _carregar_trat():
            return carregar_tratamento_diagnostico(origem, origem_id)

        def _nome_medico(mid):
            if not mid: return None
            m = next((x for x in medicos if x["id"] == mid), None)
            return m["nome"] if m else None

        # ── View (somente leitura) ──
        def _montar_view(trat):
            col = ft.Column([], spacing=4)
            med_nome = _nome_medico(trat.get("medico_id"))
            if med_nome:
                col.controls.append(ft.Row([
                    ft.Icon("person_rounded", size=12, color=AZUL),
                    ft.Text(med_nome, size=11, color=AZUL),
                ], spacing=6))
            for rem in trat.get("remedios", []):
                dos  = rem.get("dosagem","")
                freq = rem.get("frequencia","")
                col.controls.append(ft.Row([
                    ft.Icon("medication_rounded", size=12, color=SEC),
                    ft.Text(f"{rem['nome']}  {dos}  {freq}".strip(),
                            size=11, color=TXT),
                ], spacing=6))
            rev = _para_display(trat.get("data_revisao",""))
            per = trat.get("periodicidade") or ""
            rep = trat.get("repeticoes") or 1
            if rev:
                per_txt = f" · {per}" if per else ""
                rep_txt = f" · {rep}x" if per and rep > 1 else ""
                col.controls.append(ft.Row([
                    ft.Icon("event_rounded", size=12, color=AMAR),
                    ft.Text(f"Revisão: {rev}{per_txt}{rep_txt}",
                            size=11, color=AMAR),
                ], spacing=6))
            obs = trat.get("observacoes","")
            if obs:
                col.controls.append(ft.Text(obs, size=11, color=SEC))

            if not col.controls:
                col.controls.append(
                    ft.Text("Nenhum tratamento registrado.", size=11, color=MUT))

            btn_edit = ft.Container(
                content=ft.Row([
                    ft.Icon("edit_rounded", size=12, color=AZUL),
                    ft.Text("Editar", size=11, color=AZUL),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border_radius=6, bgcolor=f"{AZUL}18", ink=True,
            )
            btn_edit.on_click = lambda e: _abrir_edicao()

            btn_rem_trat = ft.Container(
                content=ft.Row([
                    ft.Icon("delete_outline_rounded", size=12, color=VERM),
                    ft.Text("Remover", size=11, color=VERM),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border_radius=6, bgcolor=f"{VERM}18", ink=True,
            )
            btn_rem_trat.on_click = lambda e: _remover_tratamento()

            return ft.Container(
                content=ft.Column([
                    col,
                    ft.Container(height=6),
                    ft.Row([btn_edit, btn_rem_trat], spacing=8),
                ], spacing=0),
                bgcolor=f"{cor_d}0A",
                border_radius=ft.border_radius.only(
                    bottom_left=8, bottom_right=8),
                padding=ft.padding.only(left=14, right=14, top=8, bottom=10),
                border=ft.Border(
                    left=ft.BorderSide(2, cor_d),
                    bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
            )

        # ── Form de edição inline ──
        def _abrir_edicao():
            _editando[0] = True
            trat = _carregar_trat()

            # médico
            _med_sel = [None]
            if trat.get("medico_id"):
                _med_sel[0] = next(
                    (m for m in medicos if m["id"] == trat["medico_id"]), None)

            txt_med = ft.Text(
                _med_sel[0]["nome"] if _med_sel[0] else "Nenhum",
                size=11, color=AZUL if _med_sel[0] else MUT,
            )
            f_med = ft.TextField(
                hint_text="Buscar médico...",
                prefix_icon="search_rounded",
                bgcolor=BG, border_color=BD2, focused_border_color=AZUL,
                hint_style=ft.TextStyle(color=MUT, size=11),
                text_style=ft.TextStyle(color=TXT, size=11),
                border_radius=6, dense=True, value="",
            )
            lista_med = ft.Column([], spacing=2)

            def _filtrar_med(e=None):
                q = (f_med.value or "").lower().strip()
                lista_med.controls.clear()
                if not q:
                    try: page.update()
                    except Exception: pass
                    return
                for m in medicos:
                    if q not in m["nome"].lower(): continue
                    _m2 = dict(m)
                    it = ft.Container(
                        content=ft.Row([
                            ft.Icon("person_rounded", size=12, color=SEC),
                            ft.Text(m["nome"], size=11, color=TXT, expand=True),
                        ], spacing=6),
                        bgcolor=BG, border_radius=6,
                        padding=ft.padding.symmetric(horizontal=8, vertical=6),
                        border=ft.border.all(1, BD), ink=True,
                    )
                    it.on_click = lambda e, x=_m2: _sel_med(x)
                    lista_med.controls.append(it)
                try: page.update()
                except Exception: pass

            def _sel_med(m):
                _med_sel[0] = m
                txt_med.value = m["nome"]; txt_med.color = AZUL
                f_med.value = ""; lista_med.controls.clear()
                try: page.update()
                except Exception: pass

            f_med.on_change = _filtrar_med

            # remédios
            _rem_sel = {}
            for rem in trat.get("remedios", []):
                _rem_sel[str(rem["remedio_id"])] = {
                    "dosagem": rem.get("dosagem",""),
                    "frequencia": rem.get("frequencia",""),
                }

            f_rem = ft.TextField(
                hint_text="Buscar remédio...",
                prefix_icon="search_rounded",
                bgcolor=BG, border_color=BD2, focused_border_color=AZUL,
                hint_style=ft.TextStyle(color=MUT, size=11),
                text_style=ft.TextStyle(color=TXT, size=11),
                border_radius=6, dense=True, value="",
            )
            lista_rem  = ft.Column([], spacing=2)
            selecionados = ft.Column([], spacing=4)

            def _rebuild_sel():
                selecionados.controls.clear()
                for rid, dados in list(_rem_sel.items()):
                    rem = next((r for r in remedios
                                if str(r.get("id","")) == rid), None)
                    if not rem: continue
                    f_dos = ft.TextField(
                        value=dados.get("dosagem",""),
                        hint_text="Dosagem",
                        hint_style=ft.TextStyle(color=MUT, size=10),
                        text_style=ft.TextStyle(color=TXT, size=11),
                        bgcolor=BG, border_color=BD2,
                        focused_border_color=AZUL,
                        border_radius=6, dense=True, expand=True,
                    )
                    f_freq = ft.TextField(
                        value=dados.get("frequencia",""),
                        hint_text="Frequência",
                        hint_style=ft.TextStyle(color=MUT, size=10),
                        text_style=ft.TextStyle(color=TXT, size=11),
                        bgcolor=BG, border_color=BD2,
                        focused_border_color=AZUL,
                        border_radius=6, dense=True, expand=True,
                    )
                    def _on_dos(e, r=rid):  _rem_sel[r]["dosagem"] = e.control.value
                    def _on_freq(e, r=rid): _rem_sel[r]["frequencia"] = e.control.value
                    f_dos.on_change  = _on_dos
                    f_freq.on_change = _on_freq
                    btn_x = ft.Container(
                        content=ft.Icon("close_rounded", size=13, color=VERM),
                        padding=ft.padding.all(3), border_radius=4, ink=True,
                    )
                    def _del(e, r=rid):
                        _rem_sel.pop(r, None); _rebuild_sel(); _filtrar_rem()
                    btn_x.on_click = _del
                    selecionados.controls.append(ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon("medication_rounded", size=12, color=AZUL),
                                ft.Text(rem.get("nome",""), size=11, color=TXT,
                                        weight=ft.FontWeight.W_600, expand=True),
                                btn_x,
                            ], spacing=6),
                            ft.Row([f_dos, f_freq], spacing=6),
                        ], spacing=4),
                        bgcolor=BG, border_radius=6,
                        padding=ft.padding.symmetric(horizontal=8, vertical=6),
                        border=ft.border.all(1, AZUL),
                    ))
                try: page.update()
                except Exception: pass

            def _filtrar_rem(e=None):
                q = (f_rem.value or "").lower().strip()
                lista_rem.controls.clear()
                if not q:
                    try: page.update()
                    except Exception: pass
                    return
                for rem in remedios:
                    rid = str(rem.get("id",""))
                    if rid in _rem_sel: continue
                    if q not in rem.get("nome","").lower(): continue
                    dos  = rem.get("dosagem","") or ""
                    freq = rem.get("frequencia","") or ""
                    it = ft.Container(
                        content=ft.Row([
                            ft.Icon("add_rounded", size=12, color=VERD),
                            ft.Column([
                                ft.Text(rem.get("nome",""), size=11, color=TXT),
                                ft.Text(f"{dos}  {freq}".strip(), size=10, color=SEC)
                                if dos or freq else ft.Container(height=0),
                            ], spacing=0, tight=True, expand=True),
                        ], spacing=6),
                        bgcolor=BG, border_radius=6,
                        padding=ft.padding.symmetric(horizontal=8, vertical=6),
                        border=ft.border.all(1, BD), ink=True,
                    )
                    def _add(e, r=rid, rem_d=dict(rem)):
                        _rem_sel[r] = {
                            "dosagem":    rem_d.get("dosagem","") or "",
                            "frequencia": rem_d.get("frequencia","") or "",
                        }
                        f_rem.value = ""; lista_rem.controls.clear()
                        _rebuild_sel()
                    it.on_click = _add
                    lista_rem.controls.append(it)
                try: page.update()
                except Exception: pass

            f_rem.on_change = _filtrar_rem
            _rebuild_sel()

            # data revisão + periodicidade + repetições
            row_rev, f_rev = campo_data(
                page, label="Data de revisão",
                value=trat.get("data_revisao","") or "",
                cor_acento=AMAR,
            )
            _PERIODOS = ["semanal","quinzenal","mensal","bimestral",
                         "trimestral","semestral","anual"]
            dd_periodo = ft.Dropdown(
                label="Periodicidade",
                value=trat.get("periodicidade") or None,
                bgcolor=BG, border_color=BD2, focused_border_color=AMAR,
                label_style=ft.TextStyle(color=SEC, size=11),
                text_style=ft.TextStyle(color=TXT, size=11),
                border_radius=6, dense=True,
                options=[ft.dropdown.Option("", "Sem repetição")] +
                        [ft.dropdown.Option(p) for p in _PERIODOS],
            )
            dd_periodo.on_change = lambda e: None
            f_rep = ft.TextField(
                label="Repetições",
                value=str(trat.get("repeticoes") or 1),
                bgcolor=BG, border_color=BD2, focused_border_color=AMAR,
                label_style=ft.TextStyle(color=SEC, size=11),
                text_style=ft.TextStyle(color=TXT, size=11),
                border_radius=6, dense=True,
                keyboard_type=ft.KeyboardType.NUMBER,
                width=100,
            )

            # observações
            f_obs = ft.TextField(
                label="Observações",
                multiline=True, min_lines=2, max_lines=4,
                bgcolor=BG, border_color=BD2, focused_border_color=AZUL,
                label_style=ft.TextStyle(color=SEC, size=11),
                text_style=ft.TextStyle(color=TXT),
                border_radius=6,
                value=trat.get("observacoes","") or "",
            )

            def _salvar_trat(e=None):
                rems_list = [
                    {"remedio_id": int(rid), **dados}
                    for rid, dados in _rem_sel.items()
                ]
                try:
                    n_rep = max(1, int(f_rep.value or 1))
                except Exception:
                    n_rep = 1
                salvar_tratamento_diagnostico(
                    origem=origem,
                    origem_id=origem_id,
                    medico_id=_med_sel[0]["id"] if _med_sel[0] else None,
                    observacoes=f_obs.value.strip() or None,
                    data_revisao=normalizar_data(f_rev.value) or None,
                    periodicidade=dd_periodo.value or None,
                    repeticoes=n_rep,
                    remedios=rems_list,
                )
                _editando[0] = False
                _rebuild_corpo()
                _snack("Tratamento salvo.")

            def _cancelar_edicao(e=None):
                _editando[0] = False
                _rebuild_corpo()

            btn_salvar = ft.Container(
                content=ft.Row([
                    ft.Icon("save_rounded", size=13, color=BG),
                    ft.Text("Salvar", size=12, color=BG, weight=ft.FontWeight.W_600),
                ], spacing=4, tight=True),
                bgcolor=VERD, border_radius=6, ink=True,
                padding=ft.padding.symmetric(horizontal=12, vertical=7),
            )
            btn_salvar.on_click = _salvar_trat

            btn_cancelar = ft.Container(
                content=ft.Text("Cancelar", size=12, color=SEC),
                border_radius=6, ink=True,
                padding=ft.padding.symmetric(horizontal=12, vertical=7),
                bgcolor=f"{SEC}22",
            )
            btn_cancelar.on_click = _cancelar_edicao

            corpo_trat.controls.clear()
            corpo_trat.controls.append(ft.Container(
                content=ft.Column([
                    ft.Text("Médico Responsável", size=10, color=SEC,
                            weight=ft.FontWeight.W_600),
                    ft.Row([
                        ft.Icon("person_rounded", size=12, color=AZUL),
                        txt_med,
                    ], spacing=6),
                    f_med, lista_med,
                    ft.Container(height=8),
                    ft.Text("Remédios", size=10, color=SEC,
                            weight=ft.FontWeight.W_600),
                    f_rem, lista_rem,
                    selecionados,
                    ft.Container(height=8),
                    ft.Text("Data de Revisão", size=10, color=SEC,
                            weight=ft.FontWeight.W_600),
                    row_rev,
                    ft.Row([dd_periodo, f_rep], spacing=8),
                    ft.Container(height=4),
                    f_obs,
                    ft.Container(height=8),
                    ft.Row([btn_cancelar, btn_salvar], spacing=8,
                           alignment=ft.MainAxisAlignment.END),
                ], spacing=4),
                bgcolor=f"{cor_d}0A",
                border_radius=ft.border_radius.only(bottom_left=8, bottom_right=8),
                padding=ft.padding.only(left=14, right=14, top=8, bottom=10),
                border=ft.Border(
                    left=ft.BorderSide(2, cor_d),
                    bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
            ))
            try: page.update()
            except Exception: pass

        def _remover_tratamento():
            try:
                from dados.model_prontuario import salvar_tratamento_diagnostico
                salvar_tratamento_diagnostico(
                    origem=origem, origem_id=origem_id,
                    medico_id=None, observacoes=None,
                    data_revisao=None, remedios=[],
                )
            except Exception as ex:
                log.warning("remover tratamento: %s", ex)
            _rebuild_corpo()
            _snack("Tratamento removido.")

        def _rebuild_corpo():
            corpo_trat.controls.clear()
            if _aberto[0] and not _editando[0]:
                trat = _carregar_trat()
                corpo_trat.controls.append(_montar_view(trat))
            try: page.update()
            except Exception: pass

        def _toggle(e=None):
            if _editando[0]: return
            _aberto[0] = not _aberto[0]
            ico_chevron.name = ("expand_less_rounded" if _aberto[0]
                                else "expand_more_rounded")
            _rebuild_corpo()

        header_trat = ft.Container(
            content=ft.Row([
                ft.Icon("medical_services_rounded", size=12, color=cor_d),
                ft.Text("Plano de Tratamento", size=10, color=cor_d,
                        weight=ft.FontWeight.W_600, expand=True),
                ico_chevron,
            ], spacing=6),
            padding=ft.padding.only(left=14, right=14, top=6, bottom=6),
            border=ft.Border(top=ft.BorderSide(1, BD)),
            ink=True,
        )
        header_trat.on_click = _toggle

        return ft.Column([header_trat, corpo_trat], spacing=0)

    # ── Carregar lista ────────────────────────────────────────────────────────
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
                    _d      = dict(d)
                    cor_d   = _STATUS_COR.get(d.get("status",""), MUT)
                    certeza = d.get("certeza","")
                    data_txt = _para_display(d.get("data_diagnostico",""))
                    sis_txt  = d.get("sistema") or ""
                    desc     = (d.get("descricao") or "")[:100]

                    btn_edit = ft.Container(
                        content=ft.Icon("edit_rounded", size=15, color=SEC),
                        padding=ft.padding.all(8), border_radius=8, ink=True,
                    )
                    btn_del = ft.Container(
                        content=ft.Icon("delete_outline_rounded", size=15, color=VERM),
                        padding=ft.padding.all(8), border_radius=8, ink=True,
                    )
                    btn_edit.on_click = lambda e, x=_d: _abrir_form(x)
                    btn_del.on_click  = lambda e, x=_d: _confirmar_excluir(
                        x["id"], x["titulo"])

                    trat_widget = _mk_tratamento_widget(_d, cor_d)

                    card = ft.Container(
                        content=ft.Column([
                            ft.Container(
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
                                                    bgcolor=ft.Colors.with_opacity(0.12, cor_d),
                                                    border_radius=6,
                                                    padding=ft.padding.symmetric(
                                                        horizontal=6, vertical=2),
                                                ) if certeza else ft.Container(),
                                            ], spacing=6),
                                            ft.Row([
                                                ft.Text(f"CID {d.get('cid','')}", size=10,
                                                        color=AZUL,
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
                                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                            ),
                            trat_widget,
                        ], spacing=0),
                        bgcolor=CARD, border_radius=10,
                        border=ft.Border(
                            left=ft.BorderSide(3, cor_d),
                            top=ft.BorderSide(1, BD),
                            bottom=ft.BorderSide(1, BD),
                            right=ft.BorderSide(1, BD),
                        ),
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    )
                    area.controls.append(card)

        _upd()

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

    titulo_tela = f"Diagnósticos — {sistema_filtro}" if sistema_filtro else "Diagnósticos"
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
