# -*- coding: utf-8 -*-
# Prontuario | telas/tela_rotinas.py
import flet as ft
import logging
import threading
import json
from datetime import date
from shared.layout import Layout
from dados.model_prontuario import (
    listar_templates, salvar_template, excluir_template,
    listar_momentos, salvar_momento, excluir_momento,
    listar_itens, salvar_item, excluir_item,
    listar_ingredientes_item, salvar_ingrediente_item, excluir_ingrediente_item,
    listar_receitas, salvar_nutricao, carregar_nutricao,
    listar_remedios, salvar_rotina_diario,
    salvar_nutricao_item, listar_nutricao_por_template,
    registrar_agua, total_agua_dia, definir_total_agua_dia,
    meta_agua_template, salvar_meta_agua,
)

log = logging.getLogger(__name__)

BG    = "#0D1117"; CARD  = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT   = "#E6EDF3"; SEC   = "#8B949E"; MUT = "#484F58"; DIS = "#484F58"
AZUL  = "#58A6FF"; VERD  = "#3FB950"; LAR = "#F0883E"; VERM = "#DA3633"
ROXO  = "#BC8CFF"; AMAR  = "#D29922"

# ── Tipos de momento e seus atributos visuais ─────────────────
_TIPOS_MOMENTO = {
    "despertar":  ("wb_sunny_rounded",      AMAR, "Despertar"),
    "refeicao":   ("restaurant_rounded",    VERD, "Refeicao"),
    "lanche":     ("lunch_dining_rounded",  LAR,  "Lanche"),
    "trabalho":   ("work_rounded",          AZUL, "Trabalho"),
    "atividade":  ("directions_run_rounded",LAR,  "Atividade"),
    "dormir":     ("bedtime_rounded",       ROXO, "Dormir"),
    "remedio":    ("medication_rounded",    AZUL, "Remedio"),
    "outro":      ("schedule_rounded",      SEC,  "Outro"),
}

# ── Tipos de atividade fisica/trabalho ─────────────────────────
_TIPOS_ATIV = [
    "Sentado", "Em pe", "Andando", "Subindo escada",
    "Carregando peso leve", "Carregando peso pesado", "Misto",
]

# ── Paleta de cores para templates ────────────────────────────
_CORES_TEMPLATE = [
    ("#58A6FF", "Azul"), ("#3FB950", "Verde"), ("#F0883E", "Laranja"),
    ("#BC8CFF", "Roxo"), ("#D29922", "Amarelo"), ("#FF4444", "Vermelho"),
    ("#8B949E", "Cinza"),
]

# ── Icones para templates ──────────────────────────────────────
_ICONES_TEMPLATE = [
    "today_rounded", "work_rounded", "weekend_rounded",
    "beach_access_rounded", "local_hospital_rounded",
    "fitness_center_rounded", "home_rounded",
]


def _campo(label, valor="", hint=None, multiline=False, min_lines=1,
           keyboard=ft.KeyboardType.TEXT):
    kw = dict(label=label, value=valor or "", bgcolor=CARD, border_color=BD2,
              focused_border_color=AZUL, label_style=ft.TextStyle(color=SEC, size=11),
              text_style=ft.TextStyle(color=TXT), border_radius=8,
              multiline=multiline, min_lines=min_lines, keyboard_type=keyboard)
    if hint:
        kw["hint_text"] = hint
        kw["hint_style"] = ft.TextStyle(color=DIS, size=11)
    return ft.TextField(**kw)


def _label_sec(txt, cor=SEC):
    return ft.Text(txt, size=10, color=cor, weight=ft.FontWeight.W_600)


def criar_tela_rotinas(page: ft.Page, voltar_fn, navegar_fn=None,
                       abrir_template_id: int = None) -> ft.Container:
    lay      = Layout(page)
    area     = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
    _montado = [False]

    # Estado de navegacao interna: lista | detalhe | momento
    _vista        = ["lista"]
    _template_sel = [None]   # dict do template atual

    # ── Widget de agua ────────────────────────────────────────────
    _agua_ref      = {"total": 0, "meta": 2500, "txt": None,
                      "barra": None, "pct": None,
                      "row_input": None, "ico_edit": None}
    _tf_agua_livre  = ft.Ref()
    _agua_editando  = [False]

    def _mk_widget_agua() -> ft.Container:
        meta  = meta_agua_template()
        total = total_agua_dia()
        _agua_ref["total"] = total
        _agua_ref["meta"]  = meta
        pct = min(total / meta, 1.0) if meta > 0 else 0.0
        cor = VERD if pct >= 1.0 else (AZUL if pct >= 0.6 else (AMAR if pct >= 0.3 else VERM))

        txt_total = ft.Text(f"{total} ml", size=15, color=cor,
                            weight=ft.FontWeight.W_900)
        txt_meta  = ft.Text(f"/ {meta} ml", size=11, color=SEC)
        txt_pct   = ft.Text(f"{int(pct*100)}%", size=10, color=cor)
        _agua_ref["txt"] = txt_total
        _agua_ref["pct"] = txt_pct

        barra_inner = ft.Container(width=0, height=6, border_radius=3, bgcolor=cor)
        barra_outer = ft.Container(
            content=barra_inner, height=6, border_radius=3,
            bgcolor=BD2, expand=True)
        _agua_ref["barra"] = (barra_inner, barra_outer, cor)

        _ico_edit = ft.Icon("edit_rounded", size=13, color=AZUL)
        _agua_ref["ico_edit"] = _ico_edit
        btn_edit  = ft.Container(
            content=_ico_edit,
            padding=ft.padding.all(6), border_radius=6, ink=True,
            tooltip="Editar total de agua",
        )
        btn_meta = ft.Container(
            content=ft.Icon("settings_rounded", size=13, color=MUT),
            padding=ft.padding.all(6), border_radius=6, ink=True,
        )
        btn_meta.on_click = _abrir_form_meta_agua

        tf_agua = ft.TextField(
            label="Total de agua hoje (ml)",
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor=CARD, border_color=BD2,
            focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=10),
            text_style=ft.TextStyle(color=TXT, size=13),
            border_radius=8, expand=True, height=44,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=6),
            ref=_tf_agua_livre,
        )
        btn_confirma = ft.Container(
            content=ft.Icon("check_rounded", size=16, color=VERD),
            width=44, height=44, border_radius=8,
            bgcolor=ft.Colors.with_opacity(0.10, VERD),
            border=ft.border.all(1, ft.Colors.with_opacity(0.30, VERD)),
            alignment=ft.alignment.Alignment(0, 0),
            ink=True,
        )
        row_input = ft.Row([tf_agua, btn_confirma],
                           spacing=8, visible=False)
        _agua_ref["row_input"] = row_input
        btn_confirma.on_click = lambda e: _salvar_agua()
        tf_agua.on_submit     = lambda e: _salvar_agua()

        def _toggle_edit(e=None):
            _agua_editando[0] = not _agua_editando[0]
            ri = _agua_ref["row_input"]
            ie = _agua_ref["ico_edit"]
            if ri: ri.visible = _agua_editando[0]
            if ie:
                ie.name = "keyboard_arrow_up_rounded" \
                          if _agua_editando[0] else "edit_rounded"
            if _agua_editando[0]:
                tf = _tf_agua_livre.current
                if tf:
                    tf.value = str(_agua_ref["total"]) \
                               if _agua_ref["total"] > 0 else ""
            try: page.update()
            except Exception: pass

        btn_edit.on_click = _toggle_edit

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon("water_drop_rounded", size=14, color=AZUL),
                    ft.Text("AGUA DO DIA", size=10, color=AZUL,
                            weight=ft.FontWeight.W_700),
                    ft.Container(expand=True),
                    txt_total, txt_meta,
                    ft.Container(width=4),
                    txt_pct,
                    btn_edit,
                    btn_meta,
                ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(height=4),
                barra_outer,
                row_input,
            ], spacing=0),
            bgcolor=CARD, border_radius=10,
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border=ft.Border(
                left=ft.BorderSide(3, AZUL),
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                right=ft.BorderSide(1, BD)),
        )

    def _salvar_agua():
        try:
            tf = _tf_agua_livre.current
            if not tf: return
            val = (tf.value or "").strip()
            if not val: return
            ml = int(float(val))
            if ml < 0: return
            # sai do modo edicao
            tf.value = ""
            _agua_editando[0] = False
            ri = _agua_ref["row_input"]
            ie = _agua_ref["ico_edit"]
            if ri: ri.visible = False
            if ie: ie.name = "edit_rounded"
            # salva no banco
            definir_total_agua_dia(ml)
            # atualiza widget
            meta = _agua_ref["meta"]
            pct  = min(ml / meta, 1.0) if meta > 0 else 0.0
            cor  = VERD if pct >= 1.0 else (AZUL if pct >= 0.6 else (AMAR if pct >= 0.3 else VERM))
            _agua_ref["total"] = ml
            if _agua_ref["txt"]:
                _agua_ref["txt"].value = f"{ml} ml"
                _agua_ref["txt"].color = cor
            if _agua_ref["pct"]:
                _agua_ref["pct"].value = f"{int(pct*100)}%"
                _agua_ref["pct"].color = cor
            if _agua_ref["barra"]:
                inner, outer, _ = _agua_ref["barra"]
                inner.bgcolor = cor
                _agua_ref["barra"] = (inner, outer, cor)
                inner.width = None
                inner.expand = pct
                outer.content = inner
            try: page.update()
            except Exception: pass
            # sync Drive em background
            def _sync():
                try:
                    from backup.drive_backup import fazer_backup
                    fazer_backup(forcar=True)
                except Exception: pass
            threading.Thread(target=_sync, daemon=True).start()
        except (ValueError, TypeError):
            pass

    def _abrir_form_meta_agua(e=None):
        ref_ov = [None]
        meta_atual = _agua_ref["meta"]
        tf = ft.TextField(
            label="Meta diaria (ml)",
            value=str(meta_atual),
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, keyboard_type=ft.KeyboardType.NUMBER,
            autofocus=True,
        )
        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass
        def _salvar(e=None):
            try:
                v = int((tf.value or "").strip())
                if v > 0:
                    salvar_meta_agua(v)
                    _agua_ref["meta"] = v
            except Exception: pass
            _fechar()
            _mostrar_lista()
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
        tf.on_submit = _salvar
        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("water_drop_rounded", size=15, color=AZUL),
                        ft.Text("Meta de Agua", size=14, color=TXT,
                                weight=ft.FontWeight.W_700, expand=True),
                    ], spacing=8),
                    ft.Container(height=4),
                    tf,
                    ft.Container(height=8),
                    ft.Row([btn_cancel, btn_ok], spacing=8,
                           alignment=ft.MainAxisAlignment.END),
                ], spacing=10, tight=True),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20), width=300,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass
    _momento_sel  = [None]   # dict do momento atual

    # ══════════════════════════════════════════════════════
    # OVERLAY HELPERS
    # ══════════════════════════════════════════════════════

    def _fechar_overlay(ref):
        if ref[0] in page.overlay:
            page.overlay.remove(ref[0])
        try: page.update()
        except Exception: pass

    def _abrir_overlay(conteudo_col):
        ref = [None]
        def _fechar(e=None):
            _fechar_overlay(ref)
        btn_close = ft.Container(
            content=ft.Icon("close_rounded", size=16, color=SEC),
            padding=8, ink=True,
        )
        btn_close.on_click = _fechar
        painel = ft.Container(
            content=ft.Column([
                ft.Row([ft.Container(expand=True), btn_close]),
                conteudo_col,
            ], spacing=0, scroll=ft.ScrollMode.AUTO),
            bgcolor=CARD, border_radius=ft.BorderRadius(14, 14, 0, 0),
            padding=ft.padding.all(20),
            width=min(480, (page.width or 480)),
            height=min(page.height * 0.85 if page.height else 600, 600),
        )
        ref[0] = ft.Container(
            content=ft.Column(
                [ft.Container(expand=True), painel],
                spacing=0,
            ),
            bgcolor="#CC000000", expand=True,
        )
        ref[0].on_click = _fechar
        page.overlay.append(ref[0])
        try: page.update()
        except Exception: pass
        return ref

    # ══════════════════════════════════════════════════════
    # FORM: TEMPLATE
    # ══════════════════════════════════════════════════════

    _TIPOS_TEMPLATE_FORM = [
        ("alimentacao", "restaurant_rounded",      VERD, "Alimentacao"),
        ("exercicio",   "directions_run_rounded",  LAR,  "Exercicios"),
        ("trabalho",    "work_rounded",            AZUL, "Trabalho"),
        ("estudo",      "computer_rounded",        ROXO, "Estudo/Dev"),
        ("lazer",       "weekend_rounded",         ROXO, "Lazer"),
        ("medicacao",   "medication_rounded",      AZUL, "Medicacao"),
        ("rotina",      "today_rounded",           SEC,  "Rotina"),
    ]
    _TIPO_ITEM_MAP = {
        "alimentacao": ("refeicao",  "alimento",  "Itens da refeicao"),
        "exercicio":   ("atividade", "atividade", "Atividades"),
        "trabalho":    ("trabalho",  "atividade", "Tarefas"),
        "estudo":      ("trabalho",  "atividade", "Estudo e desenvolvimento"),
        "lazer":       ("outro",     "atividade", "Atividades de lazer"),
        "medicacao":   ("remedio",   "remedio",   "Medicamentos"),
        "rotina":      ("outro",     "atividade", "Itens da rotina"),
    }
    _FREQUENCIAS = [
        ("diario",     "Diario"),
        ("2x_semana",  "2x/sem"),
        ("3x_semana",  "3x/sem"),
        ("semanal",    "Semanal"),
        ("eventual",   "Eventual"),
    ]
    _UNIDADES = [
        ("Unidade", "Unidade"),
        ("g",       "g"),
        ("kg",      "kg"),
        ("ml",      "ml"),
        ("Litro",   "Litro"),
        ("Xicara",  "Xicara"),
        ("C.Sopa",  "C.Sopa"),
        ("C.Cha",   "C.Cha"),
        ("Fatia",   "Fatia"),
        ("Porcao",  "Porcao"),
    ]

    def _cor_de_tipo(tipo):
        m = {t[0]: t[2] for t in _TIPOS_TEMPLATE_FORM}
        return m.get(tipo, AZUL)

    def _form_template(template=None):
        import re as _re
        f_nome    = _campo("Nome *", template["nome"] if template else "",
                           hint="ex: Cafe da Manha, Treino, Trabalho…")
        f_horario = _campo("Horario (HH:MM)", template.get("horario","") if template else "",
                           hint="ex: 07:00", keyboard=ft.KeyboardType.NUMBER)

        def _mask_hora_interno(e):
            raw = _re.sub(r"\D", "", f_horario.value or "")[:4]
            novo = (raw[:2] + ":" + raw[2:]) if len(raw) >= 3 else raw
            if f_horario.value != novo:
                f_horario.value = novo
                try: f_horario.update()
                except Exception: pass

        f_horario.on_change = _mask_hora_interno

        tipo_sel  = [template.get("tipo","alimentacao") if template else "alimentacao"]
        row_tipos = ft.Row(spacing=6, wrap=True)

        # ── Itens — lista com cards (editar/excluir) + adicionar ──────
        itens_col = ft.Column(spacing=6, tight=True)
        _momento_id = [None]

        if template:
            try:
                moms = listar_momentos(template["id"])
                if moms:
                    _momento_id[0] = moms[0]["id"]
            except Exception:
                pass

        _FREQ_LABEL = {
            "diario": "Diario", "2x_semana": "2x/sem",
            "3x_semana": "3x/sem", "semanal": "Semanal", "eventual": "Eventual",
        }

        def _refresh_itens():
            itens_col.controls.clear()
            mid = _momento_id[0]
            if not mid:
                return
            for it in listar_itens(mid):
                qty  = (it.get("quantidade") or "").strip()
                unid = (it.get("unidade") or "").strip()
                qty_str = f"{qty} {unid}  ·  " if qty else ""
                freq_label = _FREQ_LABEL.get(it.get("frequencia","diario"), "")

                btn_edit = ft.Container(
                    content=ft.Icon("edit_rounded", size=14, color=SEC),
                    padding=4, border_radius=6, ink=True)
                btn_del = ft.Container(
                    content=ft.Icon("delete_outline_rounded", size=14, color=VERM),
                    padding=4, border_radius=6, ink=True)

                def _on_edit(e, _it=it):
                    _form_item(_momento_id[0], _it, apos_salvar=_refresh_itens)
                def _on_del(e, _it=it):
                    excluir_item(_it["id"])
                    _refresh_itens()
                    try: page.update()
                    except Exception: pass

                btn_edit.on_click = _on_edit
                btn_del.on_click  = _on_del

                itens_col.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(qty_str + it["descricao"], size=12, color=TXT),
                            ft.Text(freq_label, size=10, color=MUT),
                        ], spacing=1, tight=True, expand=True),
                        btn_edit,
                        btn_del,
                    ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=BG, border_radius=8,
                    padding=ft.padding.symmetric(horizontal=10, vertical=8),
                    border=ft.Border(
                        top=ft.BorderSide(1, BD2), bottom=ft.BorderSide(1, BD2),
                        left=ft.BorderSide(2, AZUL), right=ft.BorderSide(1, BD2)),
                ))

        _refresh_itens()

        _lbl_btn_add_interno = ft.Text("Adicionar item", size=12, color=AZUL)
        btn_add = ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=12, color=AZUL),
                _lbl_btn_add_interno,
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_radius=8, ink=True,
            border=ft.Border(
                top=ft.BorderSide(1, f"{AZUL}55"), bottom=ft.BorderSide(1, f"{AZUL}55"),
                left=ft.BorderSide(1, f"{AZUL}55"), right=ft.BorderSide(1, f"{AZUL}55")))

        def _set_btn_add_state(salvando: bool):
            btn_add.disabled = salvando
            btn_add.opacity  = 0.45 if salvando else 1.0
            _lbl_btn_add_interno.value = "Salvando..." if salvando else "Adicionar item"
            try: page.update()
            except Exception: pass

        def _add_item(e=None):
            if not _momento_id[0]:
                # auto-save antes de abrir o form de item
                nome = (f_nome.value or "").strip()
                if not nome:
                    return
                _set_btn_add_state(True)
                cor_map = {t[0]: t[2] for t in _TIPOS_TEMPLATE_FORM}
                tipo_mom, _, _ = _TIPO_ITEM_MAP.get(tipo_sel[0], ("outro", "atividade", "Itens"))
                tid = salvar_template({
                    "id": template["id"] if template else None,
                    "nome": nome, "tipo": tipo_sel[0],
                    "icone": "today_rounded",
                    "cor": cor_map.get(tipo_sel[0], AZUL),
                    "padrao": 0, "ativo": 1,
                })
                if template:
                    template["id"] = tid
                moms = listar_momentos(tid)
                if moms:
                    _momento_id[0] = moms[0]["id"]
                else:
                    _momento_id[0] = salvar_momento({
                        "template_id": tid, "nome": nome,
                        "tipo": tipo_mom, "horario": None})
                _set_btn_add_state(False)
            _form_item(_momento_id[0], apos_salvar=_refresh_itens)
        btn_add.on_click = _add_item

        def _unidade_label(k):
            return dict(_UNIDADES).get(k, k)

        # ── Tipo buttons ──────────────────────────────────────────
        def _rebuild_tipos():
            row_tipos.controls.clear()
            for k, icone, cor, label in _TIPOS_TEMPLATE_FORM:
                sel = k == tipo_sel[0]
                c = ft.Container(
                    content=ft.Column([
                        ft.Icon(icone, size=16, color=cor if sel else SEC),
                        ft.Text(label, size=9, color=cor if sel else SEC),
                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                    bgcolor=f"{cor}22" if sel else CARD,
                    border_radius=8, width=72, height=52,
                    alignment=ft.alignment.Alignment(0, 0),
                    border=ft.Border(
                        top=ft.BorderSide(1, cor if sel else BD),
                        bottom=ft.BorderSide(1, cor if sel else BD),
                        left=ft.BorderSide(1, cor if sel else BD),
                        right=ft.BorderSide(1, cor if sel else BD),
                    ),
                    ink=True,
                )
                def _sel(e, kk=k):
                    tipo_sel[0] = kk; _rebuild_tipos(); _refresh_itens()
                    try: page.update()
                    except Exception: pass
                c.on_click = _sel
                row_tipos.controls.append(c)

        _rebuild_tipos()

        # ── Resumo nutricional do momento ─────────────────────────
        _nutr_aberto_m = [False]
        nutr_body_m    = ft.Column(spacing=3, tight=True, visible=False)
        ico_exp_m      = ft.Icon("expand_more_rounded", size=16, color=SEC)

        def _refresh_nutr_momento():
            nutr_body_m.controls.clear()
            mid = _momento_id[0]
            if not mid:
                nutr_body_m.controls.append(
                    ft.Text("Salve a rotina para ver o resumo.", size=11, color=MUT))
                return
            from dados.model_prontuario import calcular_nutricao_momento as _cnm
            n = _cnm(mid)
            if not n:
                nutr_body_m.controls.append(
                    ft.Text("Sem dados. Calcule nos ingredientes.", size=11, color=MUT))
                return
            def _row(label, val, unid, cor=TXT, negrito=False):
                return ft.Row([
                    ft.Text(label, size=11, color=SEC, expand=True),
                    ft.Text(f"{val:.1f}" if val is not None else "—", size=11, color=cor,
                            weight=ft.FontWeight.W_700 if negrito else ft.FontWeight.NORMAL),
                    ft.Text(f" {unid}", size=10, color=MUT),
                ], spacing=2)
            nutr_body_m.controls += [
                _row("Valor Energético", n.get("kcal"),         "kcal", LAR,  True),
                _row("Carboidratos",     n.get("carboidratos"), "g"),
                _row("Proteínas",        n.get("proteinas"),    "g",  VERD, True),
                _row("Gorduras Totais",  n.get("gorduras"),     "g"),
                _row("Fibra Alimentar",  n.get("fibras"),       "g"),
                _row("Sódio",            n.get("sodio"),        "mg"),
            ]

        def _toggle_nutr_m(e=None):
            _nutr_aberto_m[0] = not _nutr_aberto_m[0]
            if _nutr_aberto_m[0]: _refresh_nutr_momento()
            nutr_body_m.visible = _nutr_aberto_m[0]
            ico_exp_m.name = ("expand_less_rounded" if _nutr_aberto_m[0]
                              else "expand_more_rounded")
            try: page.update()
            except Exception: pass

        btn_nutr_m = ft.Container(
            content=ft.Row([
                ft.Icon("local_fire_department_rounded", size=13, color=LAR),
                ft.Text("Resumo Nutricional", size=12, color=LAR,
                        weight=ft.FontWeight.W_600, expand=True),
                ico_exp_m,
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_radius=8, ink=True,
            bgcolor=ft.Colors.with_opacity(0.08, LAR),
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.with_opacity(0.3, LAR)),
                bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.3, LAR)),
                left=ft.BorderSide(3, LAR),
                right=ft.BorderSide(1, ft.Colors.with_opacity(0.3, LAR))),
        )
        btn_nutr_m.on_click = _toggle_nutr_m

        nutr_dropdown_m = ft.Column([
            btn_nutr_m,
            ft.Container(
                content=nutr_body_m, bgcolor=CARD,
                border_radius=ft.border_radius.only(bottom_left=8, bottom_right=8),
                padding=ft.padding.only(left=10, right=10, top=6, bottom=10),
                border=ft.Border(
                    bottom=ft.BorderSide(1, BD2),
                    left=ft.BorderSide(3, LAR),
                    right=ft.BorderSide(1, BD2)),
            ),
        ], spacing=0, tight=True)

        txt_err = ft.Text("", color=VERM, size=12)

        def _salvar(e):
            if not (f_nome.value or "").strip():
                txt_err.value = "Nome obrigatorio."
                try: page.update()
                except Exception: pass
                return
            hora = (f_horario.value or "").strip()
            if hora and len(hora) == 4 and hora.isdigit():
                hora = hora[:2] + ":" + hora[2:]
            tid = salvar_template({
                "id":      template["id"] if template else None,
                "nome":    f_nome.value.strip(),
                "tipo":    tipo_sel[0],
                "horario": hora or None,
                "icone":   "today_rounded",
                "cor":     _cor_de_tipo(tipo_sel[0]),
                "padrao":  0,
                "ativo":   1,
            })
            tipo_mom, _, _ = _TIPO_ITEM_MAP.get(tipo_sel[0], ("outro","atividade","Itens"))
            try:
                moms = listar_momentos(tid)
                if moms:
                    salvar_momento({"id": moms[0]["id"], "template_id": tid,
                                    "nome": f_nome.value.strip(),
                                    "tipo": tipo_mom, "horario": hora or None})
                    _momento_id[0] = moms[0]["id"]
                else:
                    mid = salvar_momento({"template_id": tid,
                                          "nome": f_nome.value.strip(),
                                          "tipo": tipo_mom, "horario": hora or None})
                    _momento_id[0] = mid
            except Exception as ex:
                print(f"[ROTINAS] salvar template: {ex}", flush=True)
            _fechar_overlay(ref)
            _mostrar_lista()
            import threading as _thr
            def _bkp():
                try:
                    from backup.drive_backup import fazer_backup
                    fazer_backup(forcar=True)
                except Exception: pass
            _thr.Thread(target=_bkp, daemon=True).start()

        btn_salvar = ft.Container(
            content=ft.Row([
                ft.Icon("check_rounded", size=14, color=BG),
                ft.Text("Salvar", size=13, color=BG, weight=ft.FontWeight.W_600),
            ], spacing=4, tight=True),
            bgcolor=VERD, border_radius=10,
            padding=ft.padding.symmetric(horizontal=16, vertical=12), ink=True,
        )
        btn_salvar.on_click = _salvar

        col = ft.Column([
            _label_sec("NOVA ROTINA" if not template else "EDITAR ROTINA"),
            ft.Container(height=6),
            f_nome,
            f_horario,
            ft.Container(height=4),
            _label_sec("TIPO"),
            row_tipos,
            ft.Container(height=4),
            itens_col,
            btn_add,
            nutr_dropdown_m,
            txt_err,
            ft.Container(height=8),
            ft.Row([btn_salvar], alignment=ft.MainAxisAlignment.END),
        ], spacing=6)

        ref = _abrir_overlay(col)

    # ══════════════════════════════════════════════════════
    # FORM: MOMENTO
    # ══════════════════════════════════════════════════════

    def _form_momento(template_id, momento=None):
        f_nome    = _campo("Nome do momento *", momento["nome"] if momento else "",
                           hint="ex: Despertar, Cafe da manha, Trabalho…")
        f_horario = _campo("Horario (HH:MM)", momento["horario"] if momento else "",
                           hint="ex: 06:30", keyboard=ft.KeyboardType.NUMBER)

        tipo_sel = [momento["tipo"] if momento else "outro"]
        row_tipos = ft.Row(spacing=6, wrap=True)

        def _rebuild_tipos():
            row_tipos.controls.clear()
            for k, (ic, cor, label) in _TIPOS_MOMENTO.items():
                sel = k == tipo_sel[0]
                c = ft.Container(
                    content=ft.Column([
                        ft.Icon(ic, size=16, color=cor if sel else SEC),
                        ft.Text(label, size=9, color=cor if sel else SEC),
                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True),
                    bgcolor=f"{cor}22" if sel else CARD,
                    border_radius=8, width=64, height=56,
                    alignment=ft.alignment.Alignment(0, 0),
                    border=ft.Border(
                        top=ft.BorderSide(1, cor if sel else BD),
                        bottom=ft.BorderSide(1, cor if sel else BD),
                        left=ft.BorderSide(1, cor if sel else BD),
                        right=ft.BorderSide(1, cor if sel else BD),
                    ),
                    ink=True,
                )
                def _sel(e, kk=k):
                    tipo_sel[0] = kk; _rebuild_tipos()
                    try: page.update()
                    except Exception: pass
                c.on_click = _sel
                row_tipos.controls.append(c)

        _rebuild_tipos()

        txt_err = ft.Text("", color=VERM, size=12)

        def _salvar(e):
            if not (f_nome.value or "").strip():
                txt_err.value = "Nome obrigatorio."; page.update(); return
            hora = (f_horario.value or "").strip()
            # Normaliza HH:MM
            if hora and len(hora) == 4 and hora.isdigit():
                hora = hora[:2] + ":" + hora[2:]
            salvar_momento({
                "id": momento["id"] if momento else None,
                "template_id": template_id,
                "nome": f_nome.value.strip(),
                "tipo": tipo_sel[0],
                "horario": hora or None,
            })
            _fechar_overlay(ref)
            _mostrar_detalhe(_template_sel[0])
            import threading as _thr
            def _bkp():
                try:
                    from backup.drive_backup import fazer_backup
                    fazer_backup(forcar=True)
                except Exception: pass
            _thr.Thread(target=_bkp, daemon=True).start()

        btn_salvar = ft.Container(
            content=ft.Row([
                ft.Icon("check_rounded", size=14, color=BG),
                ft.Text("Salvar", size=13, color=BG, weight=ft.FontWeight.W_600),
            ], spacing=4, tight=True),
            bgcolor=VERD, border_radius=10, padding=ft.padding.symmetric(horizontal=16, vertical=12),
            ink=True,
        )
        btn_salvar.on_click = _salvar

        col = ft.Column([
            _label_sec("NOVO MOMENTO" if not momento else "EDITAR MOMENTO"),
            ft.Container(height=8),
            f_nome,
            ft.Container(height=6),
            f_horario,
            ft.Container(height=8),
            _label_sec("TIPO"),
            row_tipos,
            txt_err,
            ft.Container(height=12),
            ft.Row([btn_salvar], alignment=ft.MainAxisAlignment.END),
        ], spacing=6)

        ref = _abrir_overlay(col)

    # ══════════════════════════════════════════════════════
    # FORM: ITEM
    # ══════════════════════════════════════════════════════

    def _form_item(momento_id, item=None, apos_salvar=None):
        tipo_item_sel = [item["tipo"] if item else "alimento"]

        _TIPOS_ITEM = [
            ("alimento",  "restaurant_rounded",  VERD, "Alimento"),
            ("remedio",   "medication_rounded",  AZUL, "Medicacao"),
            ("atividade", "directions_run_rounded", LAR, "Atividade"),
        ]
        row_tipos_item = ft.Row(spacing=8)

        f_desc   = _campo("Descricao *",
                          item["descricao"] if item else "",
                          hint="ex: 1 banana da terra media / Losartana 50mg / Caminhada",
                          multiline=True, min_lines=2)
        f_det    = _campo("Detalhe / Preparo",
                          item.get("detalhe","") if item else "",
                          hint="ex: assada no airfryer, polvilhado canela / 30 min",
                          multiline=True, min_lines=2)
        f_hora   = _campo("Horario especifico (opcional)",
                          item.get("horario","") if item else "",
                          hint="ex: 06:30")

        # Dropdown de remedios
        remedios_dd_items = []
        _remedios = []
        try:
            _remedios = listar_remedios(so_ativos=True)
            remedios_dd_items = [
                ft.dropdown.Option(key=str(r["id"]), text=f"{r['nome']} {r.get('dosagem','') or ''}")
                for r in _remedios
            ]
        except Exception:
            pass

        dd_remedio = ft.Dropdown(
            label="Remedio vinculado",
            options=remedios_dd_items,
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC),
            text_style=ft.TextStyle(color=TXT), border_radius=8,
            value=str(item.get("remedio_id","")) if item and item.get("remedio_id") else None,
            visible=False,
        )

        # Dropdown de tipo de atividade
        dd_ativ = ft.Dropdown(
            label="Tipo de atividade",
            options=[ft.dropdown.Option(a) for a in _TIPOS_ATIV],
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC),
            text_style=ft.TextStyle(color=TXT), border_radius=8,
            value=item.get("detalhe") if item and item.get("tipo") == "atividade" else None,
            visible=False,
        )

        def _rebuild_tipos_item():
            row_tipos_item.controls.clear()
            for k, ic, cor, lb in _TIPOS_ITEM:
                sel = k == tipo_item_sel[0]
                c = ft.Container(
                    content=ft.Column([
                        ft.Icon(ic, size=16, color=cor if sel else SEC),
                        ft.Text(lb, size=10, color=cor if sel else SEC),
                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                    bgcolor=f"{cor}22" if sel else CARD,
                    border_radius=8, width=72, height=56,
                    alignment=ft.alignment.Alignment(0, 0),
                    border=ft.Border(
                        top=ft.BorderSide(1, cor if sel else BD),
                        bottom=ft.BorderSide(1, cor if sel else BD),
                        left=ft.BorderSide(1, cor if sel else BD),
                        right=ft.BorderSide(1, cor if sel else BD),
                    ),
                    ink=True,
                )
                def _sel_tp(e, kk=k):
                    tipo_item_sel[0] = kk
                    dd_remedio.visible = kk == "remedio"
                    dd_ativ.visible    = kk == "atividade"
                    _rebuild_tipos_item()
                    try: page.update()
                    except Exception: pass
                c.on_click = _sel_tp
                row_tipos_item.controls.append(c)

        _rebuild_tipos_item()
        dd_remedio.visible = tipo_item_sel[0] == "remedio"
        dd_ativ.visible    = tipo_item_sel[0] == "atividade"
        dd_remedio.on_change = lambda e: None
        dd_ativ.on_change    = lambda e: None

        txt_err = ft.Text("", color=VERM, size=12)

        def _salvar(e):
            desc = (f_desc.value or "").strip()
            if not desc:
                txt_err.value = "Descricao obrigatoria."; page.update(); return
            tp = tipo_item_sel[0]
            rem_id = None
            detalhe = (f_det.value or "").strip() or None
            if tp == "remedio" and dd_remedio.value:
                rem_id = int(dd_remedio.value)
            elif tp == "atividade" and dd_ativ.value:
                detalhe = dd_ativ.value
            salvar_item({
                "id": item["id"] if item else None,
                "momento_id": momento_id,
                "tipo": tp,
                "descricao": desc,
                "detalhe": detalhe,
                "horario": (f_hora.value or "").strip() or None,
                "remedio_id": rem_id,
            })
            _fechar_overlay(ref)
            if apos_salvar:
                apos_salvar()
            else:
                _mostrar_detalhe(_template_sel[0])
            import threading as _thr
            def _bkp():
                try:
                    from backup.drive_backup import fazer_backup
                    fazer_backup(forcar=True)
                except Exception: pass
            _thr.Thread(target=_bkp, daemon=True).start()

        btn_salvar = ft.Container(
            content=ft.Row([
                ft.Icon("check_rounded", size=14, color=BG),
                ft.Text("Salvar", size=13, color=BG, weight=ft.FontWeight.W_600),
            ], spacing=4, tight=True),
            bgcolor=VERD, border_radius=10, padding=ft.padding.symmetric(horizontal=16, vertical=12),
            ink=True,
        )
        btn_salvar.on_click = _salvar

        col = ft.Column([
            _label_sec("NOVO ITEM" if not item else "EDITAR ITEM"),
            ft.Container(height=8),
            _label_sec("TIPO"),
            row_tipos_item,
            ft.Container(height=6),
            f_desc,
            ft.Container(height=4),
            dd_remedio,
            dd_ativ,
            f_det,
            f_hora,
            txt_err,
            ft.Container(height=12),
            ft.Row([btn_salvar], alignment=ft.MainAxisAlignment.END),
        ], spacing=6)

        ref = _abrir_overlay(col)

    # ══════════════════════════════════════════════════════
    # CONFIRMAR EXCLUSAO
    # ══════════════════════════════════════════════════════

    def _confirmar_exclusao(titulo, msg, fn_ok):
        ref = [None]
        def _fechar(e=None):
            _fechar_overlay(ref)
        btn_ok = ft.Container(
            content=ft.Text("Excluir", size=13, color=VERM, weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            border_radius=8, bgcolor=f"{VERM}22", ink=True,
            border=ft.Border(
                top=ft.BorderSide(1, f"{VERM}66"), bottom=ft.BorderSide(1, f"{VERM}66"),
                left=ft.BorderSide(1, f"{VERM}66"), right=ft.BorderSide(1, f"{VERM}66"),
            ),
        )
        def _ok(e):
            _fechar_overlay(ref); fn_ok()
            import threading as _thr
            def _bkp():
                try:
                    from backup.drive_backup import fazer_backup
                    fazer_backup(forcar=True)
                except Exception: pass
            _thr.Thread(target=_bkp, daemon=True).start()
        btn_ok.on_click = _ok
        btn_cancel = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            border_radius=8, bgcolor=BD, ink=True,
        )
        btn_cancel.on_click = _fechar
        ref[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Text(titulo, size=15, color=TXT, weight=ft.FontWeight.W_700,
                            text_align=ft.TextAlign.CENTER),
                    ft.Container(height=8),
                    ft.Text(msg, size=13, color=SEC, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=20),
                    ft.Row([btn_cancel, btn_ok],
                           alignment=ft.MainAxisAlignment.CENTER, spacing=12),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                bgcolor=CARD, border_radius=14, padding=ft.padding.all(24), width=300,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.alignment.Alignment(0, 0),
        )
        ref[0].on_click = _fechar
        page.overlay.append(ref[0])
        try: page.update()
        except Exception: pass

    # ══════════════════════════════════════════════════════
    # NUTRIÇÃO — cálculo via Claudia + exibição no detalhe
    # ══════════════════════════════════════════════════════

    _calculando = [False]

    def _calcular_nutricao(mom_nome, itens_lista):
        if _calculando[0]:
            return
        _calculando[0] = True
        page.pubsub.send_all_on_topic("_rot_nutricao", {"status": "calculando"})

        def _run():
            try:
                from utils.api_checker import exigir_creditos, SemCreditosError
                from utils.claudia_engine import get_client, _MODELO
                exigir_creditos(get_client)
                linhas = []
                for it in itens_lista:
                    qty  = (it.get("quantidade") or "").strip()
                    unid = (it.get("unidade") or "").strip()
                    pref = f"{qty} {unid} " if qty else ""
                    linhas.append(f"- {pref}{it['descricao']}")
                prompt = (
                    f"Calcule os valores nutricionais aproximados dos itens de '{mom_nome}':\n"
                    + "\n".join(linhas)
                    + "\n\nRetorne SOMENTE JSON valido:\n"
                    + '{"itens":[{"descricao":"nome","calorias":0.0,"proteinas":0.0,"vitaminas":"A,C"}]}'
                )
                client = get_client()
                resp = client.messages.create(
                    model=_MODELO, max_tokens=1024,
                    system="Voce e um nutricionista. Retorne SOMENTE JSON valido, sem texto adicional.",
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"): raw = raw[4:]
                dados = json.loads(raw)
                page.pubsub.send_all_on_topic("_rot_nutricao", {
                    "status": "ok", "itens_db": itens_lista, "dados": dados,
                })
            except SemCreditosError as ex:
                page.pubsub.send_all_on_topic("_rot_nutricao", {
                    "status": "erro",
                    "msg": (
                        "Sem creditos na API Claude.\n"
                        "Acesse console.anthropic.com/settings/billing\n"
                        "para adicionar fundos e tentar novamente."
                    ),
                })
            except Exception as ex:
                page.pubsub.send_all_on_topic("_rot_nutricao", {
                    "status": "erro", "msg": str(ex),
                })

        threading.Thread(target=_run, daemon=True, name="RotNutricao").start()

    def _on_rot_nutricao(topic, msg):
        if not isinstance(msg, dict): return
        _calculando[0] = False
        if msg["status"] == "ok":
            for i, it_db in enumerate(msg["itens_db"]):
                itens_resp = msg["dados"].get("itens", [])
                if i < len(itens_resp):
                    n = itens_resp[i]
                    salvar_nutricao_item(
                        it_db["id"],
                        n.get("calorias"), n.get("proteinas"),
                        n.get("vitaminas", ""),
                    )
        if _template_sel[0]:
            _mostrar_detalhe(_template_sel[0])
        else:
            _mostrar_lista()

    page.pubsub.subscribe_topic("_rot_nutricao", _on_rot_nutricao)

    def _card_nutricao_detalhe(mom_nome, itens):
        total_cal  = sum(it.get("calorias")  or 0 for it in itens)
        total_prot = sum(it.get("proteinas") or 0 for it in itens)
        vits = sorted(set(
            v.strip()
            for it in itens
            for v in (it.get("vitaminas") or "").split(",")
            if v.strip()
        ))
        tem = total_cal > 0 or total_prot > 0

        filhos = []
        if tem:
            chips = [
                ft.Container(
                    content=ft.Row([
                        ft.Icon("local_fire_department_rounded", size=11, color=LAR),
                        ft.Text(f"{total_cal:.0f} kcal", size=11, color=LAR,
                                weight=ft.FontWeight.W_600),
                    ], spacing=3, tight=True),
                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                    border_radius=8, bgcolor=f"{LAR}18"),
                ft.Container(
                    content=ft.Row([
                        ft.Icon("fitness_center_rounded", size=11, color=VERD),
                        ft.Text(f"{total_prot:.1f}g prot", size=11, color=VERD,
                                weight=ft.FontWeight.W_600),
                    ], spacing=3, tight=True),
                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                    border_radius=8, bgcolor=f"{VERD}18"),
            ]
            filhos.append(ft.Row(chips, spacing=6, wrap=True))
            if vits:
                filhos.append(ft.Row([
                    ft.Icon("medication_liquid_rounded", size=11, color=AZUL),
                    ft.Text("Vit: " + ", ".join(vits), size=11, color=AZUL),
                ], spacing=4))

        lbl = "Recalcular com Claudia" if tem else "Calcular com Claudia"
        btn = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text("C", size=10, color=BG, weight=ft.FontWeight.W_700),
                    width=18, height=18, border_radius=9, bgcolor=ROXO,
                    alignment=ft.alignment.Alignment(0, 0)),
                ft.Text("Calculando…" if _calculando[0] else lbl, size=11, color=ROXO),
            ], spacing=6, tight=True),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border_radius=8, ink=True,
            border=ft.Border(
                top=ft.BorderSide(1, f"{ROXO}44"), bottom=ft.BorderSide(1, f"{ROXO}44"),
                left=ft.BorderSide(1, f"{ROXO}44"), right=ft.BorderSide(1, f"{ROXO}44")),
        )
        def _click(e, mn=mom_nome, il=itens):
            _calcular_nutricao(mn, il)
        btn.on_click = _click
        filhos.append(btn)

        return ft.Container(
            content=ft.Column(filhos, spacing=6, tight=True),
            padding=ft.padding.only(left=4, top=8, bottom=4),
            border=ft.Border(top=ft.BorderSide(1, BD)),
            margin=ft.margin.only(top=4),
        )

    # ══════════════════════════════════════════════════════
    # VISTA: LISTA DE TEMPLATES
    # ══════════════════════════════════════════════════════

    def _mostrar_lista():
        _vista[0] = "lista"
        templates = listar_templates()
        nutricao  = listar_nutricao_por_template()
        area.controls.clear()

        # agua sempre no topo
        area.controls.append(_mk_widget_agua())

        if not templates:
            area.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Container(height=40),
                        ft.Row([ft.Icon("today_rounded", size=48, color=MUT)],
                               alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=12),
                        ft.Row([ft.Text("Nenhuma rotina cadastrada", size=14, color=SEC)],
                               alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=8),
                        ft.Row([ft.Text("Crie sua rotina diaria com os momentos\ne habitos do seu dia.",
                                        size=12, color=MUT, text_align=ft.TextAlign.CENTER)],
                               alignment=ft.MainAxisAlignment.CENTER),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                )
            )
        else:
            total_cal  = 0.0
            total_prot = 0.0
            total_vits: set = set()

            for t in templates:
                icone, cor = t.get("icone","today_rounded"), t.get("cor","#58A6FF")
                nut = nutricao.get(t["id"], {})
                cal  = nut.get("calorias",  0) or 0
                prot = nut.get("proteinas", 0) or 0
                vits = nut.get("vitaminas", []) or []
                tem_nut = cal > 0 or prot > 0

                total_cal  += cal
                total_prot += prot
                total_vits.update(vits)

                # chips nutricionais do card
                chips_nut = []
                if tem_nut:
                    chips_nut = [
                        ft.Container(
                            content=ft.Row([
                                ft.Icon("local_fire_department_rounded", size=10, color=LAR),
                                ft.Text(f"{cal:.0f} kcal", size=10, color=LAR,
                                        weight=ft.FontWeight.W_600),
                            ], spacing=2, tight=True),
                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            border_radius=6, bgcolor=f"{LAR}18"),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon("fitness_center_rounded", size=10, color=VERD),
                                ft.Text(f"{prot:.1f}g prot", size=10, color=VERD,
                                        weight=ft.FontWeight.W_600),
                            ], spacing=2, tight=True),
                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            border_radius=6, bgcolor=f"{VERD}18"),
                    ]

                info_col_filhos = [
                    ft.Text(t["nome"], size=14, color=TXT, weight=ft.FontWeight.W_600),
                    ft.Text(
                        (t.get("horario") + " · " if t.get("horario") else "") +
                        f"{t.get('total_momentos',0)} momento(s)",
                        size=11, color=SEC),
                ]
                if chips_nut:
                    info_col_filhos.append(ft.Row(chips_nut, spacing=6))
                if vits:
                    info_col_filhos.append(ft.Row([
                        ft.Icon("medication_liquid_rounded", size=10, color=AZUL),
                        ft.Text("Vit: " + ", ".join(vits), size=10, color=AZUL),
                    ], spacing=3))

                # -- dropdown expansivel de momentos ------------------
                _expandido = [False]
                ico_expand = ft.Icon("expand_more_rounded", size=16, color=MUT)
                col_momentos = ft.Column(spacing=4, visible=False)

                def _build_momentos(col, tid, tcor):
                    col.controls.clear()
                    moms = listar_momentos(tid)
                    for m in moms:
                        itens = listar_itens(m["id"])
                        mi, mc, _ = _TIPOS_MOMENTO.get(
                            m.get("tipo","outro"), ("schedule_rounded", SEC, ""))

                        # cabecalho do momento
                        linhas_itens = []
                        for it in itens:
                            desc = it.get("descricao","") or ""
                            qtd  = it.get("quantidade","") or ""
                            uni  = it.get("unidade","") or ""
                            qtd_txt = f"{qtd} {uni}".strip()

                            btn_ed = ft.Container(
                                content=ft.Icon("edit_rounded", size=13, color=SEC),
                                padding=ft.padding.all(4), border_radius=6, ink=True,
                            )
                            btn_del = ft.Container(
                                content=ft.Icon("delete_outline_rounded", size=13, color=VERM),
                                padding=ft.padding.all(4), border_radius=6, ink=True,
                            )
                            _it = dict(it)
                            _m  = dict(m)
                            btn_ed.on_click  = lambda e, mm=_m, ii=_it: (
                                _mostrar_detalhe(next(
                                    (tt for tt in listar_templates()
                                     if tt["id"] == tid), {}
                                ))
                            )
                            btn_del.on_click = lambda e, iid=_it["id"], mm=_m: (
                                excluir_item(iid) or
                                _build_momentos(col, tid, tcor) or
                                (page.update() if _montado[0] else None)
                            )

                            linhas_itens.append(ft.Container(
                                content=ft.Row([
                                    ft.Text(desc, size=12, color=TXT, expand=True),
                                    ft.Text(qtd_txt, size=11, color=SEC,
                                            visible=bool(qtd_txt)),
                                    btn_ed,
                                    btn_del,
                                ], spacing=6,
                                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                padding=ft.padding.symmetric(vertical=4),
                                border=ft.Border(
                                    bottom=ft.BorderSide(1, BD)),
                            ))

                        col.controls.append(ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(mi, size=12, color=mc),
                                    ft.Text(m.get("nome",""), size=12,
                                            color=TXT, weight=ft.FontWeight.W_600),
                                    ft.Text(m.get("horario",""), size=10, color=MUT),
                                ], spacing=6),
                                *linhas_itens,
                            ], spacing=0),
                            padding=ft.padding.only(left=12, top=8, bottom=4),
                            border=ft.Border(
                                left=ft.BorderSide(2, tcor + "55")),
                            margin=ft.margin.only(bottom=4),
                        ))

                def _toggle_expand(e, col=col_momentos,
                                   ie=ico_expand, ex=_expandido,
                                   tid=t["id"], tcor=cor):
                    ex[0] = not ex[0]
                    col.visible = ex[0]
                    ie.name = "expand_less_rounded" if ex[0] \
                              else "expand_more_rounded"
                    if ex[0]:
                        _build_momentos(col, tid, tcor)
                    try: page.update()
                    except Exception: pass

                btn_expand = ft.Container(
                    content=ico_expand,
                    padding=ft.padding.all(6), border_radius=6, ink=True,
                )
                btn_expand.on_click = _toggle_expand

                card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Icon(icone, size=22, color=cor),
                                bgcolor=f"{cor}22", border_radius=10,
                                width=44, height=44,
                                alignment=ft.alignment.Alignment(0, 0),
                            ),
                            ft.Column(info_col_filhos, spacing=2, expand=True),
                            ft.Row([
                                btn_expand,
                                _btn_icon("edit_rounded", SEC,
                                          lambda e, tt=t: _form_template(tt)),
                                _btn_icon("delete_outline_rounded", VERM,
                                          lambda e, tt=t: _confirmar_exclusao(
                                              "Excluir rotina?",
                                              f"'{tt['nome']}' e todos os seus momentos serao excluidos.",
                                              lambda tid=tt["id"]: [excluir_template(tid), _mostrar_lista()],
                                          )),
                            ], spacing=4),
                        ], spacing=12,
                           vertical_alignment=ft.CrossAxisAlignment.START),
                        col_momentos,
                    ], spacing=0),
                    bgcolor=CARD, border_radius=10, padding=ft.padding.all(12),
                    border=ft.Border(
                        top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                        left=ft.BorderSide(3, cor), right=ft.BorderSide(1, BD),
                    ),
                )
                area.controls.append(card)

            # ── Resumo acumulativo ─────────────────────────────────
            if total_cal > 0 or total_prot > 0:
                vits_sorted = sorted(total_vits)
                resumo_filhos = [
                    ft.Text("Resumo diario", size=11, color=SEC, weight=ft.FontWeight.W_600),
                    ft.Row([
                        ft.Container(
                            content=ft.Row([
                                ft.Icon("local_fire_department_rounded", size=12, color=LAR),
                                ft.Text(f"{total_cal:.0f} kcal total", size=12, color=LAR,
                                        weight=ft.FontWeight.W_700),
                            ], spacing=3, tight=True),
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            border_radius=8, bgcolor=f"{LAR}18"),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon("fitness_center_rounded", size=12, color=VERD),
                                ft.Text(f"{total_prot:.1f}g prot", size=12, color=VERD,
                                        weight=ft.FontWeight.W_700),
                            ], spacing=3, tight=True),
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            border_radius=8, bgcolor=f"{VERD}18"),
                    ], spacing=8, wrap=True),
                ]
                if vits_sorted:
                    resumo_filhos.append(ft.Row([
                        ft.Icon("medication_liquid_rounded", size=11, color=AZUL),
                        ft.Text("Vit: " + ", ".join(vits_sorted), size=11, color=AZUL),
                    ], spacing=4))
                area.controls.append(ft.Container(
                    content=ft.Column(resumo_filhos, spacing=6, tight=True),
                    bgcolor=CARD, border_radius=10,
                    padding=ft.padding.all(14),
                    margin=ft.margin.only(top=8),
                    border=ft.Border(
                        top=ft.BorderSide(2, f"{LAR}66"), bottom=ft.BorderSide(1, BD),
                        left=ft.BorderSide(1, BD),      right=ft.BorderSide(1, BD)),
                ))


        _atualizar_header()
        if _montado[0]:
            try: page.update()
            except Exception: pass

    # ══════════════════════════════════════════════════════
    # VISTA: DETALHE DO TEMPLATE (momentos em timeline)
    # ══════════════════════════════════════════════════════

    def _mostrar_detalhe(template):
        _vista[0] = "detalhe"
        _template_sel[0] = template
        momentos = listar_momentos(template["id"])
        area.controls.clear()

        cor_t = template.get("cor", AZUL)

        for m in momentos:
            ic_tipo, cor_tipo, _ = _TIPOS_MOMENTO.get(m.get("tipo","outro"), _TIPOS_MOMENTO["outro"])
            itens = listar_itens(m["id"])

            # Linha de itens (preview)
            _FREQ_LABEL = {
                "diario": "Diario", "2x_semana": "2x/sem",
                "3x_semana": "3x/sem", "semanal": "Semanal", "eventual": "Eventual",
            }
            _UNID_MAP = dict(_FREQUENCIAS)  # reutiliza para lookup
            itens_col = ft.Column(spacing=3)
            for it in itens[:6]:
                ic_it = "restaurant_rounded" if it["tipo"]=="alimento" else (
                    "medication_rounded" if it["tipo"]=="remedio" else "directions_run_rounded")
                cor_it = VERD if it["tipo"]=="alimento" else (AZUL if it["tipo"]=="remedio" else LAR)
                freq_label = _FREQ_LABEL.get(it.get("frequencia","diario"), it.get("frequencia",""))
                qty   = (it.get("quantidade") or "").strip()
                unid  = (it.get("unidade") or "").strip()
                qty_str = f"{qty} {unid} · " if qty else ""
                linha = ft.Row([
                    ft.Icon(ic_it, size=12, color=cor_it),
                    ft.Text(qty_str + it["descricao"], size=11, color=SEC, expand=True),
                    ft.Text(freq_label, size=10, color=MUT),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START)
                itens_col.controls.append(linha)
            if len(itens) > 6:
                itens_col.controls.append(ft.Text(f"+ {len(itens)-6} itens…", size=10, color=MUT))

            btn_add_item = ft.Container(
                content=ft.Row([
                    ft.Icon("add_circle_outline_rounded", size=13, color=VERD),
                    ft.Text("Adicionar item", size=11, color=VERD),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(vertical=6),
                ink=True,
            )
            btn_add_item.on_click = lambda e, mid=m["id"]: _form_item(mid)

            card_momento = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            content=ft.Icon(ic_tipo, size=16, color=cor_tipo),
                            bgcolor=f"{cor_tipo}22", border_radius=8, width=32, height=32,
                            alignment=ft.alignment.Alignment(0, 0),
                        ),
                        ft.Column([
                            ft.Row([
                                ft.Text(m["nome"], size=13, color=TXT, weight=ft.FontWeight.W_600),
                                ft.Text(m.get("horario","") or "", size=11, color=cor_tipo),
                            ], spacing=8),
                            ft.Text(f"{len(itens)} item(ns)", size=10, color=MUT),
                        ], spacing=1, expand=True),
                        ft.Row([
                            _btn_icon("edit_rounded", SEC, lambda e, mm=m: _form_momento(template["id"], mm)),
                            _btn_icon("delete_outline_rounded", VERM, lambda e, mm=m: _confirmar_exclusao(
                                "Excluir momento?",
                                f"'{mm['nome']}' e todos os seus itens serao excluidos.",
                                lambda mid=mm["id"]: [excluir_momento(mid), _mostrar_detalhe(template)],
                            )),
                        ], spacing=2),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(
                        content=ft.Column([
                            itens_col,
                            btn_add_item,
                            _card_nutricao_detalhe(m["nome"], itens),
                        ], spacing=4),
                        bgcolor=BG, border_radius=8, padding=ft.padding.all(10),
                        margin=ft.margin.only(left=40, top=4),
                    ) if itens or True else ft.Container(),
                ], spacing=6),
                bgcolor=CARD, border_radius=10, padding=ft.padding.all(12),
                border=ft.Border(
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    left=ft.BorderSide(3, cor_tipo), right=ft.BorderSide(1, BD),
                ),
            )
            area.controls.append(card_momento)

        _atualizar_header()
        if _montado[0]:
            try: page.update()
            except Exception: pass

    # ══════════════════════════════════════════════════════
    # HEADER DINAMICO
    # ══════════════════════════════════════════════════════

    _cab_container = ft.Container()

    def _voltar_detalhe():
        _template_sel[0] = None
        _mostrar_lista()

    def _sair(e=None):
        def _sync_e_sair():
            try:
                from backup.drive_backup import fazer_backup
                fazer_backup(forcar=True)
            except Exception:
                pass
            if voltar_fn:
                voltar_fn()
        threading.Thread(target=_sync_e_sair, daemon=True).start()

    def _atualizar_header():
        if _vista[0] == "lista":
            btn_novo = ft.Container(
                content=ft.Row([
                    ft.Icon("add_rounded", size=16, color=VERD),
                    ft.Text("Nova", size=13, color=VERD),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                border_radius=8, ink=True,
            )
            btn_novo.on_click = lambda e: _form_template()
            novo_cab = lay.criar_cabecalho(
                "Rotinas Diarias", _sair,
                icone_titulo="today_rounded", cor_titulo=AZUL,
                acoes=[btn_novo],
            )
        else:
            t = _template_sel[0]
            btn_add = ft.Container(
                content=ft.Row([
                    ft.Icon("add_rounded", size=16, color=t.get("cor", AZUL)),
                    ft.Text("Momento", size=13, color=t.get("cor", AZUL)),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                border_radius=8, ink=True,
            )
            btn_add.on_click = lambda e: _form_momento(t["id"])
            novo_cab = lay.criar_cabecalho(
                t["nome"], _voltar_detalhe,
                icone_titulo=t.get("icone","today_rounded"),
                cor_titulo=t.get("cor", AZUL),
                acoes=[btn_add],
            )
        _cab_container.content = novo_cab
        if _montado[0]:
            try: page.update()
            except Exception: pass

    # ══════════════════════════════════════════════════════
    # HELPER: BOTAO ICONE
    # ══════════════════════════════════════════════════════

    def _btn_icon(ic, cor, fn):
        c = ft.Container(
            content=ft.Icon(ic, size=16, color=cor),
            padding=6, border_radius=6, ink=True,
        )
        c.on_click = fn
        return c

    # ══════════════════════════════════════════════════════
    # MONTAGEM
    # ══════════════════════════════════════════════════════

    if abrir_template_id is not None:
        try:
            templates = listar_templates(so_ativos=True)
            tmpl = next((t for t in templates if t["id"] == abrir_template_id), None)
            if tmpl:
                _vista[0] = "lista"
                _atualizar_header()
                _form_template(tmpl)
            else:
                _mostrar_lista()
        except Exception:
            _mostrar_lista()
    else:
        _mostrar_lista()

    corpo = ft.Column([
        ft.Container(height=lay.spacer_topo, bgcolor=BG),
        _cab_container,
        ft.Container(
            content=area, padding=ft.padding.all(12), expand=True,
        ),
    ], expand=True, spacing=0)

    _montado[0] = True
    return ft.Container(bgcolor=BG, expand=True, content=lay.wrap(corpo))


# ── Overlay standalone: form do template (usado por tela_rotina_diaria) ──

def _criar_overlay_form_template(page: ft.Page, template: dict, on_salvo=None):
    """Abre o form de edicao do template como overlay sobre a tela atual."""
    import threading as _thr

    BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2  = "#30363D"
    TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
    AZUL = "#58A6FF"; VERD = "#3FB950"; LAR = "#F0883E"; VERM = "#DA3633"
    ROXO = "#BC8CFF"; AMAR = "#D29922"

    _TIPOS_TEMPLATE = [
        ("alimentacao", "restaurant_rounded",      VERD, "Alimentacao"),
        ("exercicio",   "directions_run_rounded",  LAR,  "Exercicios"),
        ("trabalho",    "work_rounded",            AZUL, "Trabalho"),
        ("estudo",      "computer_rounded",        ROXO, "Estudo/Dev"),
        ("lazer",       "weekend_rounded",         ROXO, "Lazer"),
        ("medicacao",   "medication_rounded",      AZUL, "Medicacao"),
        ("rotina",      "today_rounded",           SEC,  "Rotina"),
    ]
    _TIPO_MOM_MAP = {
        "alimentacao": "refeicao",  "exercicio": "atividade",
        "trabalho":    "trabalho",  "estudo":    "trabalho",
        "lazer":       "outro",     "medicacao": "remedio",
        "rotina":      "outro",
    }
    # tipos que exigem hora inicio/fim + intensidade
    _TIPOS_GASTO_TMPL = {"exercicio", "trabalho", "estudo"}
    _FREQUENCIAS = [
        ("diario","Diario"),("2x_semana","2x/sem"),("3x_semana","3x/sem"),
        ("semanal","Semanal"),("eventual","Eventual"),
    ]
    _UNIDADES = [
        ("Unidade","Unidade"),("g","g"),("kg","kg"),("ml","ml"),("Litro","Litro"),
        ("Xicara","Xicara"),("C.Sopa","C.Sopa"),("C.Cha","C.Cha"),
        ("Fatia","Fatia"),("Porcao","Porcao"),
    ]
    _FREQ_LABEL = {k: v for k, v in _FREQUENCIAS}

    ref_ov = [None]

    def _fechar(e=None):
        if ref_ov[0] in page.overlay:
            page.overlay.remove(ref_ov[0])
        try: page.update()
        except Exception: pass
        if on_salvo and template.get("id"):
            on_salvo()
        def _bkp():
            try:
                from backup.drive_backup import fazer_backup
                fazer_backup(forcar=True)
            except Exception: pass
        _thr.Thread(target=_bkp, daemon=True).start()

    f_nome    = ft.TextField(
        label="Nome *", value=template.get("nome",""),
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC, size=11),
        text_style=ft.TextStyle(color=TXT), border_radius=8,
    )
    f_horario = ft.TextField(
        label="Horario (HH:MM)", value=template.get("horario","") or "",
        hint_text="ex: 07:00",
        hint_style=ft.TextStyle(color=MUT, size=11),
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC, size=11),
        text_style=ft.TextStyle(color=TXT), border_radius=8,
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    def _mask_horario(e):
        import re as _re
        raw = _re.sub(r"\D", "", f_horario.value or "")[:4]
        novo = (raw[:2] + ":" + raw[2:]) if len(raw) >= 3 else raw
        if f_horario.value != novo:
            f_horario.value = novo
            try: f_horario.update()
            except Exception: pass

    f_horario.on_change = _mask_horario

    tipo_sel  = [template.get("tipo","alimentacao")]
    row_tipos = ft.Row(spacing=6, wrap=True)
    txt_err   = ft.Text("", color=VERM, size=12)

    # ── Itens ──────────────────────────────────────────────────────
    itens_col   = ft.Column(spacing=6, tight=True)
    momento_id  = [None]

    try:
        moms = listar_momentos(template["id"])
        if moms:
            momento_id[0] = moms[0]["id"]
    except Exception:
        pass

    def _refresh_itens():
        itens_col.controls.clear()
        mid = momento_id[0]
        if not mid:
            return
        for it in listar_itens(mid):
            qty  = (it.get("quantidade") or "").strip()
            unid = (it.get("unidade") or "").strip()
            qty_str = f"{qty} {unid}  ·  " if qty else ""
            freq_label = _FREQ_LABEL.get(it.get("frequencia","diario"), "")

            btn_edit = ft.Container(
                content=ft.Icon("edit_rounded", size=14, color=SEC),
                padding=4, border_radius=6, ink=True)
            btn_del = ft.Container(
                content=ft.Icon("delete_outline_rounded", size=14, color=VERM),
                padding=4, border_radius=6, ink=True)

            def _on_edit(e, _it=it):
                _abrir_form_item(_it)
            def _on_del(e, _it=it):
                excluir_item(_it["id"])
                _refresh_itens()
                try: page.update()
                except Exception: pass

            btn_edit.on_click = _on_edit
            btn_del.on_click  = _on_del

            itens_col.controls.append(ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Text(qty_str + it["descricao"], size=12, color=TXT),
                        ft.Text(freq_label, size=10, color=MUT),
                    ], spacing=1, tight=True, expand=True),
                    btn_edit, btn_del,
                ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=BG, border_radius=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                border=ft.Border(
                    top=ft.BorderSide(1, BD2), bottom=ft.BorderSide(1, BD2),
                    left=ft.BorderSide(2, AZUL), right=ft.BorderSide(1, BD2)),
            ))
        try: page.update()
        except Exception: pass

    def _abrir_form_item(item=None):
        import re as _re2

        _TIPOS_ITEM = [
            ("alimento",  "restaurant_rounded",      VERD, "Alimento"),
            ("remedio",   "medication_rounded",      AZUL, "Medicacao"),
            ("atividade", "directions_run_rounded",  LAR,  "Atividade"),
            ("trabalho",  "computer_rounded",        ROXO, "Trabalho"),
        ]
        _TIPOS_INGESTAO = {"alimento", "remedio"}
        _TIPOS_GASTO    = {"atividade", "trabalho"}
        _INTENS_FISICO  = [
            ("leve",     "Leve",     "Alongamento, caminhada lenta",   2.5),
            ("moderado", "Moderado", "Musculacao, caminhada rapida",    5.0),
            ("intenso",  "Intenso",  "Corrida, HIIT, natacao",         9.0),
        ]
        _INTENS_MENTAL  = [
            ("leve",     "Leve",     "Leitura, reuniao passiva",        1.3),
            ("moderado", "Moderado", "Estudo, escrita, reuniao ativa",  1.6),
            ("intenso",  "Intenso",  "Programacao, resolucao complexa", 1.9),
        ]

        tipo_it  = [item.get("tipo","alimento") if item else "alimento"]
        freq_sel = [item.get("frequencia","diario") if item else "diario"]
        ref_it   = [None]

        f_desc = ft.TextField(
            label="Descricao *", value=item.get("descricao","") if item else "",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT), border_radius=8,
        )

        # ── Hora início / fim (atividade e trabalho) ──────────────
        def _mask_h(tf):
            def _on(e):
                raw = _re2.sub(r"\D", "", tf.value or "")[:4]
                novo = (raw[:2] + ":" + raw[2:]) if len(raw) >= 3 else raw
                if tf.value != novo:
                    tf.value = novo
                    try: tf.update()
                    except Exception: pass
            return _on

        f_h_ini = ft.TextField(
            label="Inicio (HH:MM)", value=item.get("hora_inicio","") if item else "",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT), border_radius=8,
            keyboard_type=ft.KeyboardType.NUMBER, expand=True,
        )
        f_h_fim = ft.TextField(
            label="Fim (HH:MM)", value=item.get("hora_fim","") if item else "",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT), border_radius=8,
            keyboard_type=ft.KeyboardType.NUMBER, expand=True,
        )
        bloco_horas = ft.Row([f_h_ini, f_h_fim], spacing=8,
                              visible=tipo_it[0] in _TIPOS_GASTO)

        txt_gasto   = ft.Text("", size=11, color=LAR, weight=ft.FontWeight.W_600)
        bloco_gasto = ft.Container(
            content=ft.Row([
                ft.Icon("local_fire_department_rounded", size=13, color=VERM),
                txt_gasto,
            ], spacing=6), visible=False, padding=ft.padding.only(top=2))

        intens_f_sel = [item.get("intensidade_fisica") if item else None]
        intens_m_sel = [item.get("intensidade_mental") if item else None]
        row_intens   = ft.Column(spacing=6, tight=True,
                                 visible=tipo_it[0] in _TIPOS_GASTO)

        def _atualizar_gasto():
            hi = (f_h_ini.value or "").strip()
            hf = (f_h_fim.value or "").strip()
            if not (hi and hf): bloco_gasto.visible = False; return
            from dados.model_prontuario import calcular_gasto_item as _cgi
            try:
                from dados.model_prontuario import DB_PATH as _DB
                import sqlite3 as _sq
                with _sq.connect(_DB, timeout=5) as _c:
                    rp = _c.execute("SELECT peso FROM perfil_usuario LIMIT 1").fetchone()
                peso = float(rp[0]) if rp and rp[0] else 80.0
            except Exception:
                peso = 80.0
            r = _cgi(hi, hf,
                     intens_f_sel[0] if tipo_it[0] == "atividade" else None,
                     intens_m_sel[0] if tipo_it[0] == "trabalho"  else None,
                     peso)
            if r:
                h = r["duracao_min"] // 60; m = r["duracao_min"] % 60
                dur = f"{h}h{m:02d}min" if h else f"{m}min"
                txt_gasto.value = f"−{r['kcal_gasto']:.0f} kcal  ({dur}  MET {r['met']})"
                bloco_gasto.visible = True
            else:
                bloco_gasto.visible = False
            try: page.update()
            except Exception: pass

        def _on_hora(e): _mask_h(f_h_ini)(e); _atualizar_gasto()
        def _on_hora2(e): _mask_h(f_h_fim)(e); _atualizar_gasto()
        f_h_ini.on_change = _on_hora
        f_h_fim.on_change = _on_hora2

        def _rebuild_intens():
            row_intens.controls.clear()
            lista    = _INTENS_FISICO if tipo_it[0] == "atividade" else _INTENS_MENTAL
            sel_ref  = intens_f_sel   if tipo_it[0] == "atividade" else intens_m_sel
            cor_int  = LAR if tipo_it[0] == "atividade" else ROXO
            row_intens.controls.append(
                ft.Text("INTENSIDADE", size=10, color=SEC, weight=ft.FontWeight.W_600))
            chips = ft.Row(spacing=6, wrap=True)
            for k, lbl, hint, met in lista:
                sel = k == sel_ref[0]
                chip = ft.Container(
                    content=ft.Column([
                        ft.Text(lbl, size=11, color=cor_int if sel else SEC,
                                weight=ft.FontWeight.W_600 if sel else ft.FontWeight.NORMAL),
                        ft.Text(f"MET {met}", size=9, color=MUT),
                    ], spacing=0, tight=True,
                       horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=ft.Colors.with_opacity(0.15, cor_int) if sel else BD,
                    border_radius=8, ink=True,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    tooltip=hint,
                    border=ft.Border(
                        top=ft.BorderSide(1, cor_int if sel else BD2),
                        bottom=ft.BorderSide(1, cor_int if sel else BD2),
                        left=ft.BorderSide(1, cor_int if sel else BD2),
                        right=ft.BorderSide(1, cor_int if sel else BD2)),
                )
                def _sel_int(e, kk=k, sr=sel_ref):
                    sr[0] = kk; _rebuild_intens(); _atualizar_gasto()
                    try: page.update()
                    except Exception: pass
                chip.on_click = _sel_int
                chips.controls.append(chip)
            row_intens.controls.append(chips)

        _rebuild_intens()
        if item and (item.get("hora_inicio") or item.get("hora_fim")):
            _atualizar_gasto()

        # ── Frequência (só ingestão) ──────────────────────────────
        freq_row = ft.Row(spacing=4, wrap=True)
        bloco_freq = ft.Column([
            ft.Text("FREQUENCIA", size=10, color=SEC, weight=ft.FontWeight.W_600),
            freq_row,
        ], spacing=6, tight=True, visible=tipo_it[0] in _TIPOS_INGESTAO)

        row_it = ft.Row(spacing=6, wrap=True)

        def _rebuild_freq():
            freq_row.controls.clear()
            for k, lbl in _FREQUENCIAS:
                sel = k == freq_sel[0]
                btn = ft.Container(
                    content=ft.Text(lbl, size=10,
                                    color=AZUL if sel else SEC,
                                    weight=ft.FontWeight.W_600 if sel else ft.FontWeight.NORMAL),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=12, ink=True,
                    bgcolor=ft.Colors.with_opacity(0.15, AZUL) if sel else BD,
                    border=ft.Border(
                        top=ft.BorderSide(1, AZUL if sel else BD2),
                        bottom=ft.BorderSide(1, AZUL if sel else BD2),
                        left=ft.BorderSide(1, AZUL if sel else BD2),
                        right=ft.BorderSide(1, AZUL if sel else BD2)),
                )
                def _sf(e, k=k):
                    freq_sel[0] = k; _rebuild_freq()
                    try: page.update()
                    except Exception: pass
                btn.on_click = _sf
                freq_row.controls.append(btn)

        _rebuild_freq()

        # ── Quantidade de unidades (comprimidos/cápsulas) ─────────
        f_qtd_rem = ft.TextField(
            label="Quantidade (comprimidos/cápsulas/unidades)",
            value=item.get("quantidade","") if item else "",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT), border_radius=8,
            keyboard_type=ft.KeyboardType.NUMBER,
            hint_text="ex: 1, 2, 4",
            hint_style=ft.TextStyle(color=MUT, size=11),
            visible=tipo_it[0] == "remedio",
        )

        # ── Preview nutricional do remédio ────────────────────────
        nutr_rem_col = ft.Column(spacing=3, tight=True,
                                  visible=tipo_it[0] == "remedio")

        def _atualizar_nutr_rem():
            nutr_rem_col.controls.clear()
            rid = _rem_id_sel[0]
            if not rid:
                try: page.update()
                except Exception: pass
                return
            from dados.model_prontuario import (
                carregar_nutricao as _cn,
                _nutricao_proporcional as _np,
            )
            n = _cn("remedio", rid)
            if not n:
                nutr_rem_col.controls.append(
                    ft.Text("Sem tabela nutricional cadastrada.",
                            size=10, color=MUT))
                try: page.update()
                except Exception: pass
                return

            por_g = float(n.get("por_100g") or 1.0)
            try:
                qtd_u = float((f_qtd_rem.value or "1").strip() or 1)
            except Exception:
                qtd_u = 1.0

            # peso por unidade salvo em vitaminas_json/_porcao
            peso_unit = por_g  # default: porção = 1 unidade
            try:
                import json as _jn
                vd = _jn.loads(n.get("vitaminas_json") or "{}")
                info = vd.get("_porcao","")  # ex: "2g = 4 unid x 0.5g"
                if "x" in info and "g" in info:
                    # extrai peso por unidade
                    parte = info.split("x")[-1].strip()  # "0.5g"
                    peso_unit = float(parte.replace("g","").strip())
            except Exception:
                pass

            gramas_total = qtd_u * peso_unit
            n_prop = _np(n, gramas_total)

            def _row(lbl, val, unid, cor=TXT, bold=False):
                return ft.Row([
                    ft.Text(lbl, size=10, color=SEC, expand=True),
                    ft.Text(f"{val:.1f}" if val is not None else "—",
                            size=10, color=cor,
                            weight=ft.FontWeight.W_700 if bold else ft.FontWeight.NORMAL),
                    ft.Text(f" {unid}", size=9, color=MUT),
                ], spacing=2)

            nutr_rem_col.controls += [
                ft.Text(f"NUTRICIONAL — {qtd_u:.0f} unid × {peso_unit:.1f}g = {gramas_total:.1f}g",
                        size=9, color=ROXO, weight=ft.FontWeight.W_700),
                ft.Divider(height=1, color=ROXO),
                _row("Energia",     n_prop.get("kcal"),         "kcal", LAR,  True),
                _row("Carboidratos",n_prop.get("carboidratos"), "g"),
                _row("Proteínas",   n_prop.get("proteinas"),    "g",  VERD, True),
                _row("Gorduras",    n_prop.get("gorduras"),      "g"),
                _row("Fibras",      n_prop.get("fibras"),        "g"),
                _row("Sódio",       n_prop.get("sodio"),         "mg"),
            ]
            try: page.update()
            except Exception: pass

        def _on_qtd_rem_change(e):
            _atualizar_nutr_rem()
        f_qtd_rem.on_change = _on_qtd_rem_change

        # ── Busca de remédio (autocomplete inline) ────────────────
        _remedios_lista = listar_remedios(so_ativos=True)
        _rem_id_sel     = [item.get("remedio_id") if item else None]

        _rem_nome_ini = ""
        if item and item.get("remedio_id"):
            _r0 = next((r for r in _remedios_lista if r["id"] == item["remedio_id"]), None)
            if _r0:
                _rem_nome_ini = f"{_r0['nome']} {_r0.get('dosagem','') or ''}".strip()

        tf_remedio = ft.TextField(
            label="Buscar remédio", value=_rem_nome_ini,
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT), border_radius=8,
        )
        sug_rem = ft.Column(spacing=2, tight=True, visible=False)
        bloco_remedio = ft.Column([tf_remedio, sug_rem], spacing=2,
                                   visible=tipo_it[0] == "remedio")

        def _filtrar_rem(e):
            termo = (tf_remedio.value or "").strip().upper()
            sug_rem.controls.clear()
            if not termo:
                sug_rem.visible = False; _rem_id_sel[0] = None
                try: page.update()
                except Exception: pass
                return
            encontrados = [r for r in _remedios_lista
                           if termo in r["nome"].upper()
                           or termo in (r.get("principio_ativo") or "").upper()][:8]
            for r in encontrados:
                nome_r = f"{r['nome']} {r.get('dosagem','') or ''}".strip()
                def _sel_rem(e, rem=r, nr=nome_r):
                    tf_remedio.value = nr; _rem_id_sel[0] = rem["id"]
                    sug_rem.controls.clear(); sug_rem.visible = False
                    _atualizar_nutr_rem()
                    try: page.update()
                    except Exception: pass
                chip = ft.Container(
                    content=ft.Row([
                        ft.Icon("medication_rounded", size=13, color=AZUL),
                        ft.Text(nome_r, size=12, color=TXT, expand=True),
                    ], spacing=8),
                    bgcolor=BD, border_radius=6,
                    padding=ft.padding.symmetric(horizontal=12, vertical=7),
                    ink=True,
                )
                chip.on_click = _sel_rem
                sug_rem.controls.append(chip)
            sug_rem.visible = bool(encontrados)
            try: page.update()
            except Exception: pass

        tf_remedio.on_change = _filtrar_rem

        def _rebuild_it():
            row_it.controls.clear()
            for k, ic, cor, lb in _TIPOS_ITEM:
                sel = k == tipo_it[0]
                c = ft.Container(
                    content=ft.Column([
                        ft.Icon(ic, size=14, color=cor if sel else SEC),
                        ft.Text(lb, size=9, color=cor if sel else SEC),
                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                    bgcolor=ft.Colors.with_opacity(0.15, cor) if sel else BD,
                    border_radius=8, width=68, height=48,
                    alignment=ft.Alignment(0, 0),
                    border=ft.Border(
                        top=ft.BorderSide(1, cor if sel else BD2),
                        bottom=ft.BorderSide(1, cor if sel else BD2),
                        left=ft.BorderSide(1, cor if sel else BD2),
                        right=ft.BorderSide(1, cor if sel else BD2)),
                    ink=True,
                )
                def _st(e, kk=k):
                    tipo_it[0] = kk
                    eh_gasto    = kk in _TIPOS_GASTO
                    eh_ingestao = kk in _TIPOS_INGESTAO
                    bloco_horas.visible   = eh_gasto
                    row_intens.visible    = eh_gasto
                    bloco_gasto.visible   = False
                    bloco_freq.visible    = eh_ingestao
                    bloco_remedio.visible  = kk == "remedio"
                    f_qtd_rem.visible      = kk == "remedio"
                    nutr_rem_col.visible   = kk == "remedio"
                    f_desc.visible         = kk != "remedio"
                    bloco_ingr.visible     = kk == "alimento"
                    _rebuild_intens(); _rebuild_it()
                    try: page.update()
                    except Exception: pass
                c.on_click = _st
                row_it.controls.append(c)

        _rebuild_it()

        def _sync_bkp():
            import threading as _thr
            def _bkp():
                try:
                    from backup.drive_backup import fazer_backup
                    fazer_backup(forcar=True)
                except Exception: pass
            _thr.Thread(target=_bkp, daemon=True).start()

        def _salvar_item(e=None):
            if tipo_it[0] == "remedio":
                desc = (tf_remedio.value or "").strip()
                if not desc and _rem_id_sel[0]:
                    rem = next((r for r in _remedios_lista
                                if r["id"] == _rem_id_sel[0]), None)
                    desc = f"{rem['nome']} {rem.get('dosagem','') or ''}".strip() if rem else ""
            else:
                desc = (f_desc.value or "").strip()
            if not desc: return
            qtd_rem = (f_qtd_rem.value or "").strip() if tipo_it[0] == "remedio" else None
            salvar_item({
                "id":                 item["id"] if item else None,
                "momento_id":         momento_id[0],
                "tipo":               tipo_it[0],
                "descricao":          desc,
                "frequencia":         freq_sel[0] if tipo_it[0] in _TIPOS_INGESTAO else None,
                "quantidade":         qtd_rem if tipo_it[0] == "remedio" else None,
                "unidade":            "Unidade" if tipo_it[0] == "remedio" else None,
                "remedio_id":         _rem_id_sel[0],
                "hora_inicio":        (f_h_ini.value or "").strip() or None,
                "hora_fim":           (f_h_fim.value or "").strip() or None,
                "intensidade_fisica": intens_f_sel[0] if tipo_it[0] == "atividade" else None,
                "intensidade_mental": intens_m_sel[0] if tipo_it[0] == "trabalho"  else None,
                "ordem":              item.get("ordem", 0) if item else 0,
            })
            if ref_it[0] in page.overlay:
                page.overlay.remove(ref_it[0])
            _refresh_itens()
            _sync_bkp()

        def _fc(e=None):
            if ref_it[0] in page.overlay:
                page.overlay.remove(ref_it[0])
            try: page.update()
            except Exception: pass
            _sync_bkp()

        btn_salvar_it = ft.Container(
            content=ft.Row([
                ft.Icon("check_rounded", size=14, color=VERD),
                ft.Text("Salvar", size=13, color=VERD, weight=ft.FontWeight.W_600),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            border_radius=8, ink=True,
        )
        btn_salvar_it.on_click = _salvar_item

        _ico_cab = {"alimento": ("restaurant_rounded", VERD),
                    "remedio":  ("medication_rounded",  AZUL),
                    "atividade":("directions_run_rounded", LAR),
                    "trabalho": ("computer_rounded",    ROXO)}
        _ic, _cc = _ico_cab.get(tipo_it[0], ("restaurant_rounded", VERD))
        titulo_item = "Editar item" if item else "Novo item"
        cab_it = _lay.criar_cabecalho(
            titulo_item, _fc,
            icone_titulo=_ic, cor_titulo=_cc,
            acoes=[btn_salvar_it],
        )

        # ── Ingredientes do item ───────────────────────────────────
        ingr_col = ft.Column(spacing=6, tight=True)
        item_id_atual = item["id"] if item else None
        _item_id_ref  = [item_id_atual]  # lista para closure seguro

        def _refresh_ingr():
            ingr_col.controls.clear()
            if not _item_id_ref[0]:
                ingr_col.controls.append(ft.Text("Lista de Ingredientes Vazia", size=11, color=MUT))
                try: page.update()
                except Exception: pass
                return
            lista = listar_ingredientes_item(_item_id_ref[0])
            if not lista:
                ingr_col.controls.append(ft.Text("Lista de Ingredientes Vazia", size=11, color=MUT))
                try: page.update()
                except Exception: pass
                return
            receitas_map = {r["id"]: r["nome"] for r in listar_receitas()}
            for ing in lista:
                if ing["tipo"] == "receita":
                    nome_ing = f"[Receita] {ing['receita_nome'] or '?'}"
                    cor_ing  = ROXO
                else:
                    nome_ing = ing["descricao"] or ""
                    cor_ing  = TXT
                qty  = (ing.get("quantidade") or "").strip()
                unid = (ing.get("unidade") or "").strip()
                qty_str = f"{qty} {unid}  · " if qty else ""

                btn_edit_i = ft.Container(
                    content=ft.Icon("edit_rounded", size=13, color=SEC),
                    padding=4, border_radius=6, ink=True)
                btn_del_i = ft.Container(
                    content=ft.Icon("delete_outline_rounded", size=13, color=VERM),
                    padding=4, border_radius=6, ink=True)

                def _edit_i(e, _ing=ing):
                    _abrir_form_ingrediente(ingrediente=_ing)

                def _excluir_ingr(iid):
                    excluir_ingrediente_item(iid)
                    _refresh_ingr()
                    import threading as _thr3
                    def _bkp():
                        try:
                            from backup.drive_backup import fazer_backup
                            fazer_backup(forcar=True)
                        except Exception: pass
                    _thr3.Thread(target=_bkp, daemon=True).start()

                def _del_i(e, iid=ing["id"], inome=nome_ing):
                    ref_conf = [None]
                    def _fechar_conf(e2=None):
                        if ref_conf[0] in page.overlay:
                            page.overlay.remove(ref_conf[0])
                        try: page.update()
                        except Exception: pass
                    def _ok_conf(e2=None):
                        _fechar_conf()
                        _excluir_ingr(iid)
                    btn_c = ft.Container(
                        content=ft.Text("Cancelar", size=13, color=TXT,
                                        weight=ft.FontWeight.W_600),
                        padding=ft.padding.symmetric(horizontal=16, vertical=10),
                        border_radius=8, bgcolor=BD2, ink=True, expand=True,
                        alignment=ft.Alignment(0, 0))
                    btn_o = ft.Container(
                        content=ft.Text("Excluir", size=13, color=VERM,
                                        weight=ft.FontWeight.W_600),
                        padding=ft.padding.symmetric(horizontal=16, vertical=10),
                        border_radius=8,
                        bgcolor=ft.Colors.with_opacity(0.13, VERM),
                        border=ft.Border(
                            top=ft.BorderSide(1, ft.Colors.with_opacity(0.4, VERM)),
                            bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.4, VERM)),
                            left=ft.BorderSide(1, ft.Colors.with_opacity(0.4, VERM)),
                            right=ft.BorderSide(1, ft.Colors.with_opacity(0.4, VERM))),
                        ink=True, expand=True, alignment=ft.Alignment(0, 0))
                    btn_c.on_click = _fechar_conf
                    btn_o.on_click = _ok_conf
                    ref_conf[0] = ft.Container(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text("Excluir ingrediente?", size=15, color=TXT,
                                        weight=ft.FontWeight.W_700,
                                        text_align=ft.TextAlign.CENTER),
                                ft.Container(height=4),
                                ft.Text(f"'{inome}' sera removido.", size=13,
                                        color=SEC, text_align=ft.TextAlign.CENTER),
                                ft.Container(height=16),
                                ft.Row([btn_c, ft.Container(width=8), btn_o]),
                            ], spacing=0, tight=True,
                               horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            bgcolor=CARD, border_radius=14,
                            padding=ft.padding.all(20),
                            width=min(page.width - 32, 320) if page.width else 300),
                        bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0))
                    ref_conf[0].on_click = _fechar_conf
                    page.overlay.append(ref_conf[0])
                    try: page.update()
                    except Exception: pass

                btn_edit_i.on_click = _edit_i
                btn_del_i.on_click  = _del_i

                tem_nutr = False
                if ing["tipo"] == "item":
                    n = carregar_nutricao("ingrediente_item", ing["id"])
                    tem_nutr = bool(n and any(
                        n.get(k) for k in ("kcal","proteinas","carboidratos","gorduras")))

                borda_esq = LAR if tem_nutr else (cor_ing if cor_ing != TXT else BD2)

                ingr_col.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Icon("local_fire_department_rounded", size=11, color=LAR,
                                visible=tem_nutr),
                        ft.Text(qty_str + nome_ing, size=12, color=cor_ing, expand=True),
                        btn_edit_i,
                        btn_del_i,
                    ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=ft.Colors.with_opacity(0.04, LAR) if tem_nutr else BG,
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=10, vertical=7),
                    border=ft.Border(
                        top=ft.BorderSide(1, BD2), bottom=ft.BorderSide(1, BD2),
                        left=ft.BorderSide(3 if tem_nutr else 2, borda_esq),
                        right=ft.BorderSide(1, BD2)),
                ))
            try: page.update()
            except Exception: pass

        def _abrir_form_ingrediente(ingrediente=None):
            nonlocal item_id_atual
            if not item_id_atual and not ingrediente:
                desc = (f_desc.value or "").strip()
                if not desc:
                    f_desc.error_text = "Salve o item antes de adicionar ingredientes"
                    try: page.update()
                    except Exception: pass
                    return
                f_desc.error_text = None
                novo_id = salvar_item({
                    "momento_id": momento_id[0],
                    "tipo":       tipo_it[0],
                    "descricao":  desc,
                    "frequencia": freq_sel[0],
                    "ordem":      0,
                })
                item_id_atual = novo_id
                _item_id_ref[0] = novo_id
                btn_add_ingr.visible = True
                try: page.update()
                except Exception: pass
            receitas_lista = listar_receitas()
            ing = ingrediente or {}
            tipo_i  = [ing.get("tipo", "item")]
            ref_fi  = [None]
            f_di    = ft.TextField(
                label="Ingrediente *", hint_text="ex: Ovo caipira, Sal",
                value=ing.get("descricao", ""),
                hint_style=ft.TextStyle(color=MUT, size=11),
                bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
                label_style=ft.TextStyle(color=SEC, size=11),
                text_style=ft.TextStyle(color=TXT), border_radius=8,
                visible=tipo_i[0] == "item",
            )
            f_qi = ft.TextField(
                label="Qtd", bgcolor=CARD, border_color=BD2,
                value=ing.get("quantidade", "") or "",
                focused_border_color=AZUL,
                label_style=ft.TextStyle(color=SEC, size=11),
                text_style=ft.TextStyle(color=TXT), border_radius=8,
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            dd_ui = ft.Dropdown(
                label="Unidade",
                options=[ft.dropdown.Option(key=k, text=v) for k, v in _UNIDADES],
                value=ing.get("unidade", "Unidade") or "Unidade",
                bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
                label_style=ft.TextStyle(color=SEC, size=11),
                text_style=ft.TextStyle(color=TXT), border_radius=8,
            )
            dd_ui.on_change = lambda e: None

            receita_sel = [ing.get("sub_receita_id")]
            dd_receita  = ft.Dropdown(
                label="Receita",
                options=[ft.dropdown.Option(key=str(r["id"]), text=r["nome"])
                         for r in receitas_lista],
                value=str(ing["sub_receita_id"]) if ing.get("sub_receita_id") else None,
                bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
                label_style=ft.TextStyle(color=SEC, size=11),
                text_style=ft.TextStyle(color=TXT), border_radius=8,
                visible=tipo_i[0] == "receita",
            )
            dd_receita.on_change = lambda e: None

            nutr_col_i = ft.Column(spacing=0, tight=True)
            tipo_row_i = ft.Row(spacing=6)

            def _rebuild_tipo_i():
                tipo_row_i.controls.clear()
                for k, label, cor in [("item","Ingrediente",AZUL),("receita","Receita",ROXO)]:
                    sel = k == tipo_i[0]
                    btn = ft.Container(
                        content=ft.Text(label, size=11,
                                        color=cor if sel else SEC,
                                        weight=ft.FontWeight.W_600 if sel else ft.FontWeight.NORMAL),
                        padding=ft.padding.symmetric(horizontal=12, vertical=7),
                        border_radius=8, ink=True,
                        bgcolor=ft.Colors.with_opacity(0.15, cor) if sel else BD,
                        border=ft.Border(
                            top=ft.BorderSide(1, cor if sel else BD2),
                            bottom=ft.BorderSide(1, cor if sel else BD2),
                            left=ft.BorderSide(1, cor if sel else BD2),
                            right=ft.BorderSide(1, cor if sel else BD2)),
                    )
                    def _st(e, kk=k):
                        tipo_i[0] = kk
                        f_di.visible          = kk == "item"
                        dd_receita.visible    = kk == "receita"
                        btn_claudia_i.visible = kk == "item"
                        btn_porcao.visible    = kk == "receita"
                        nutr_col_i.controls.clear()
                        _rebuild_tipo_i()
                        try: page.update()
                        except Exception: pass
                    btn.on_click = _st
                    tipo_row_i.controls.append(btn)

            _rebuild_tipo_i()

            # ── Tabela proporcional para tipo Receita ─────────────
            def _refresh_nutr_receita(e=None):
                nutr_col_i.controls.clear()
                if tipo_i[0] != "receita" or not dd_receita.value:
                    try: page.update()
                    except Exception: pass
                    return
                try:
                    rid = int(dd_receita.value)
                    n   = carregar_nutricao("receita", rid)
                    if not n:
                        nutr_col_i.controls.append(
                            ft.Text("Receita sem tabela nutricional calculada.",
                                    size=11, color=MUT))
                        try: page.update()
                        except Exception: pass
                        return
                    from dados.model_prontuario import _porcao_em_gramas, _nutricao_proporcional
                    qty_v  = (f_qi.value or "1").strip()
                    unid_v = dd_ui.value or "C.Sopa"
                    gramas = _porcao_em_gramas(qty_v, unid_v)
                    np_    = _nutricao_proporcional(n, gramas)

                    def _row(label, val, unid, cor=TXT, negrito=False):
                        return ft.Row([
                            ft.Text(label, size=10, color=SEC, expand=True),
                            ft.Text(f"{val:.1f}" if val is not None else "—",
                                    size=10, color=cor,
                                    weight=ft.FontWeight.W_700 if negrito else ft.FontWeight.NORMAL),
                            ft.Text(f" {unid}", size=9, color=MUT),
                        ], spacing=2)

                    linhas = [
                        ft.Text(f"TABELA NUTRICIONAL / {qty_v} {unid_v} ({gramas:.0f}g)",
                                size=9, color=ROXO, weight=ft.FontWeight.W_700),
                        ft.Divider(height=1, color=ROXO),
                        _row("Valor Energético",   np_.get("kcal"),        "kcal", LAR, True),
                        _row("Carboidratos",        np_.get("carboidratos"),"g"),
                        _row("Proteínas",           np_.get("proteinas"),   "g", VERD, True),
                        _row("Gorduras Totais",     np_.get("gorduras"),    "g"),
                        _row("Fibra Alimentar",     np_.get("fibras"),      "g"),
                        _row("Sódio",               np_.get("sodio"),       "mg"),
                    ]
                    nutr_col_i.controls.append(ft.Container(
                        content=ft.Column(linhas, spacing=3, tight=True),
                        bgcolor=CARD, border_radius=8, padding=ft.padding.all(10),
                        border=ft.Border(
                            top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                            left=ft.BorderSide(3, ROXO), right=ft.BorderSide(1, BD)),
                    ))
                except Exception as ex:
                    nutr_col_i.controls.append(
                        ft.Text(f"Erro: {ex}", size=10, color=VERM))
                try: page.update()
                except Exception: pass

            # atualiza tabela ao mudar receita, qtd ou unidade
            dd_receita.on_change = _refresh_nutr_receita
            f_qi.on_change       = _refresh_nutr_receita
            dd_ui.on_change      = _refresh_nutr_receita

            # botão explícito para calcular porção de receita
            btn_porcao = ft.Container(
                content=ft.Row([
                    ft.Icon("calculate_rounded", size=14, color=ROXO),
                    ft.Text("Ver tabela da porção", size=12, color=ROXO),
                ], spacing=6, tight=True),
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                border_radius=8, ink=True,
                border=ft.Border(
                    top=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO)),
                    bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO)),
                    left=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO)),
                    right=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO))),
                visible=tipo_i[0] == "receita",
            )
            btn_porcao.on_click = _refresh_nutr_receita

            _ingr_id_salvo = [ing.get("id")]  # captura id apos salvar

            def _salvar_ingr(e=None):
                iid = _item_id_ref[0]
                if not iid: return
                desc_v = (f_di.value or "").strip()
                qty_v  = (f_qi.value or "").strip()
                unid_v = dd_ui.value or "Unidade"
                if tipo_i[0] == "item":
                    if not desc_v: return
                    _ingr_id_salvo[0] = salvar_ingrediente_item({
                        "id":         ing.get("id"),
                        "item_id":    iid,
                        "tipo":       "item",
                        "descricao":  desc_v,
                        "quantidade": qty_v or None,
                        "unidade":    unid_v,
                    })
                else:
                    if not dd_receita.value: return
                    _ingr_id_salvo[0] = salvar_ingrediente_item({
                        "id":             ing.get("id"),
                        "item_id":        iid,
                        "tipo":           "receita",
                        "sub_receita_id": int(dd_receita.value),
                        "quantidade":     qty_v or None,
                        "unidade":        unid_v,
                    })
                if ref_fi[0] in page.overlay:
                    page.overlay.remove(ref_fi[0])
                try: page.update()
                except Exception: pass
                import asyncio as _asyncio
                async def _delayed_refresh_save():
                    await _asyncio.sleep(0.05)
                    _refresh_ingr()
                page.run_task(_delayed_refresh_save)
                # calcular tabela nutricional automaticamente em background
                if tipo_i[0] == "item" and desc_v:
                    import threading as _thr_auto
                    def _auto_nutr():
                        try:
                            import json as _json
                            from utils.claudia_engine import get_client, _MODELO
                            eh_unidade = unid_v == "Unidade"
                            prompt = (
                                f"Tabela nutricional de '{desc_v}' ({qty_v or '1'} {unid_v}) "
                                "conforme rotulo brasileiro (ANVISA RDC 429/2020). "
                                "Pode ser alimento, suplemento, vitamina ou mineral. "
                                "Use os valores reais do produto — se todos forem zero "
                                "(ex: creatina pura, vitamina C isolada), retorne zeros mesmo. "
                                "Retorne SOMENTE JSON valido com valores por 100g do produto"
                                + (" e peso_unitario_g de 1 unidade" if eh_unidade else "")
                                + ":\n"
                                '{"por_100g":100,"kcal":0,"kj":0,"carboidratos":0,"acucares":0,'
                                '"proteinas":0,"gorduras":0,"saturadas":0,"trans":0,'
                                '"fibras":0,"sodio":0'
                                + (',"peso_unitario_g":5' if eh_unidade else "")
                                + ',"vitaminas":{}}'
                                "\nInclua vitaminas/minerais apenas se o produto os contiver."
                            )
                            client = get_client()
                            resp = client.messages.create(
                                model=_MODELO, max_tokens=800,
                                system="Voce e um nutricionista. Retorne SOMENTE JSON valido.",
                                messages=[{"role": "user", "content": prompt}],
                            )
                            raw = "".join(b.text for b in resp.content
                                          if hasattr(b, "text")).strip()
                            if raw.startswith("```"):
                                raw = raw.split("```")[1]
                                if raw.startswith("json"): raw = raw[4:]
                            dados = _json.loads(raw)
                            vits = dados.pop("vitaminas", {})
                            peso_unit = dados.pop("peso_unitario_g", None)
                            # busca o id do ingrediente recém salvo
                            ingr_id = _ingr_id_salvo[0]
                            if ingr_id:
                                salvar_nutricao({
                                    "entidade_tipo": "ingrediente_item",
                                    "entidade_id":   ingr_id,
                                    **{k: dados.get(k) for k in
                                       ["por_100g","kcal","kj","carboidratos","acucares",
                                        "proteinas","gorduras","saturadas","trans","fibras","sodio"]},
                                    "vitaminas_json": _json.dumps(vits, ensure_ascii=False) if vits else None,
                                })
                                if peso_unit:
                                    from dados.model_prontuario import salvar_ingrediente_item as _sii
                                    _sii({
                                        "id": ingr_id,
                                        "item_id": iid,
                                        "tipo": "item",
                                        "descricao": desc_v,
                                        "quantidade": qty_v or None,
                                        "unidade": unid_v,
                                        "peso_unitario_g": float(peso_unit),
                                    })
                            from backup.drive_backup import fazer_backup
                            fazer_backup(forcar=True)
                        except Exception as ex:
                            log.warning("[ROTINAS] auto nutr: %s", ex)
                        finally:
                            # atualiza destaque do card apos calculo concluir
                            import asyncio as _aio_an
                            async def _dr_an():
                                await _aio_an.sleep(0.1)
                                _refresh_ingr()
                            page.run_task(_dr_an)
                    _thr_auto.Thread(target=_auto_nutr, daemon=True,
                                     name="AutoNutrIngr").start()
                else:
                    import threading as _thr2
                    def _bkp_i():
                        try:
                            from backup.drive_backup import fazer_backup
                            fazer_backup(forcar=True)
                        except Exception: pass
                    _thr2.Thread(target=_bkp_i, daemon=True).start()

            def _fechar_fi():
                if ref_fi[0] in page.overlay:
                    page.overlay.remove(ref_fi[0])
                try: page.update()
                except Exception: pass

            def _salvar_e_fechar(e=None):
                _salvar_ingr()
                # _salvar_ingr ja fecha o overlay e faz refresh

            def _fc_i(e=None):
                # auto-salva se tem dados preenchidos
                tem_desc = tipo_i[0] == "item" and (f_di.value or "").strip()
                tem_rec  = tipo_i[0] == "receita" and dd_receita.value
                if tem_desc or tem_rec:
                    _salvar_ingr()
                else:
                    _fechar_fi()

            btn_ok_i = ft.Container(
                content=ft.Row([
                    ft.Icon("check_rounded", size=14, color=VERD),
                    ft.Text("Salvar", size=13, color=VERD, weight=ft.FontWeight.W_600),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                border_radius=8, ink=True)
            btn_ok_i.on_click = _salvar_e_fechar

            cab_fi = _lay.criar_cabecalho(
                "Editar ingrediente" if ing.get("id") else "Adicionar ingrediente", _fc_i,
                icone_titulo="add_circle_outline_rounded", cor_titulo=AZUL,
                acoes=[btn_ok_i],
            )

            # ── Tabela nutricional do ingrediente simples ─────────
            _calc_nutr_i = [False]
            lbl_c_i = ft.Text("Calcular Tabela Nutricional com Claudia",
                               size=11, color=ROXO)
            btn_claudia_i = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Text("C", size=9, color=BG, weight=ft.FontWeight.W_700),
                        width=18, height=18, border_radius=9, bgcolor=ROXO,
                        alignment=ft.Alignment(0, 0)),
                    lbl_c_i,
                ], spacing=6, tight=True),
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                border_radius=8, ink=True,
                border=ft.Border(
                    top=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO)),
                    bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO)),
                    left=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO)),
                    right=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO))),
                visible=tipo_i[0] == "item",
            )

            def _refresh_nutr_i():
                nutr_col_i.controls.clear()
                ingr_id = _ingr_id_salvo[0]
                if not ingr_id: return
                n = carregar_nutricao("ingrediente_item", ingr_id)
                if not n: return
                import json as _json
                from dados.model_prontuario import _porcao_em_gramas, _nutricao_proporcional

                qty_val  = (f_qi.value or "").strip()
                unid_val = (dd_ui.value or "g").strip()

                # para Unidade: usar peso_unitario_g calculado pela IA se disponivel
                gramas = None
                try:
                    if unid_val == "Unidade":
                        ingrs = listar_ingredientes_item(_item_id_ref[0])
                        ing_atual = next((x for x in ingrs if x["id"] == ingr_id), None)
                        peso_unit = ing_atual.get("peso_unitario_g") if ing_atual else None
                        if peso_unit:
                            gramas = float(qty_val or 1) * float(peso_unit)
                        else:
                            gramas = _porcao_em_gramas(qty_val or "1", "Unidade")
                    else:
                        gramas = _porcao_em_gramas(qty_val or "1", unid_val)
                except Exception:
                    gramas = None

                if gramas and gramas > 0:
                    n_prop = _nutricao_proporcional(n, gramas)
                    titulo_tab = f"TABELA NUTRICIONAL / {qty_val} {unid_val}"
                else:
                    n_prop = n
                    titulo_tab = "TABELA NUTRICIONAL / 100g"

                def _v(campo):
                    raw = n_prop.get(campo)
                    return float(raw) if raw is not None else None

                def _row(label, val, unid, cor=TXT, negrito=False):
                    return ft.Row([
                        ft.Text(label, size=10, color=SEC, expand=True),
                        ft.Text(f"{val:.1f}" if val is not None else "—",
                                size=10, color=cor,
                                weight=ft.FontWeight.W_700 if negrito else ft.FontWeight.NORMAL),
                        ft.Text(f" {unid}", size=9, color=MUT),
                    ], spacing=2)

                linhas = [
                    ft.Text(titulo_tab, size=9, color=LAR, weight=ft.FontWeight.W_700),
                    ft.Divider(height=1, color=LAR),
                    _row("Valor Energético", _v("kcal"),         "kcal", LAR, True),
                    _row("Carboidratos",     _v("carboidratos"), "g"),
                    _row("Proteínas",        _v("proteinas"),    "g", VERD, True),
                    _row("Gorduras Totais",  _v("gorduras"),     "g"),
                    _row("Fibra Alimentar",  _v("fibras"),       "g"),
                    _row("Sódio",            _v("sodio"),        "mg"),
                ]
                vits = n.get("vitaminas_json")
                if vits:
                    try:
                        vd = _json.loads(vits)
                        if vd:
                            linhas.append(ft.Divider(height=1, color=BD2))
                            for kv, vv in list(vd.items())[:4]:
                                linhas.append(_row(kv, None, str(vv)))
                    except Exception: pass

                nutr_col_i.controls.append(ft.Container(
                    content=ft.Column(linhas, spacing=3, tight=True),
                    bgcolor=CARD, border_radius=8,
                    padding=ft.padding.all(10),
                    border=ft.Border(
                        top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                        left=ft.BorderSide(3, LAR), right=ft.BorderSide(1, BD)),
                ))
                try: page.update()
                except Exception: pass

            def _calcular_nutr_i(e=None):
                if _calc_nutr_i[0]: return
                desc = (f_di.value or "").strip()
                qty  = (f_qi.value or "").strip()
                unid = dd_ui.value or "Unidade"
                if not desc: return
                _calc_nutr_i[0] = True
                lbl_c_i.value = "Calculando..."
                try: page.update()
                except Exception: pass

                def _run():
                    try:
                        import json as _json, threading as _thr_n
                        from utils.claudia_engine import get_client, _MODELO
                        eh_unidade = (unid or "").strip() == "Unidade"
                        prompt = (
                            f"Tabela nutricional de '{desc}' ({qty or '1'} {unid}) "
                            "conforme rotulo brasileiro (ANVISA RDC 429/2020). "
                            "Pode ser alimento, suplemento, vitamina ou mineral. "
                            "Use os valores reais do produto — se todos forem zero "
                            "(ex: creatina pura, vitamina C isolada), retorne zeros mesmo. "
                            "Retorne SOMENTE JSON valido com valores por 100g do produto"
                            + (" e peso_unitario_g de 1 unidade" if eh_unidade else "")
                            + ":\n"
                            '{"por_100g":100,"kcal":0,"kj":0,"carboidratos":0,"acucares":0,'
                            '"proteinas":0,"gorduras":0,"saturadas":0,"trans":0,'
                            '"fibras":0,"sodio":0'
                            + (',"peso_unitario_g":5' if eh_unidade else "")
                            + ',"vitaminas":{}}'
                            "\nInclua vitaminas/minerais apenas se o produto os contiver."
                        )
                        client = get_client()
                        resp = client.messages.create(
                            model=_MODELO, max_tokens=800,
                            system="Voce e um nutricionista. Retorne SOMENTE JSON valido.",
                            messages=[{"role": "user", "content": prompt}],
                        )
                        raw = "".join(b.text for b in resp.content
                                      if hasattr(b, "text")).strip()
                        if raw.startswith("```"):
                            raw = raw.split("```")[1]
                            if raw.startswith("json"): raw = raw[4:]
                        dados = _json.loads(raw)
                        vits = dados.pop("vitaminas", {})
                        peso_unit = dados.pop("peso_unitario_g", None)
                        ingr_id = _ingr_id_salvo[0]
                        if ingr_id:
                            salvar_nutricao({
                                "entidade_tipo": "ingrediente_item",
                                "entidade_id":   ingr_id,
                                **{k: dados.get(k) for k in
                                   ["por_100g","kcal","kj","carboidratos","acucares",
                                    "proteinas","gorduras","saturadas","trans","fibras","sodio"]},
                                "vitaminas_json": _json.dumps(vits, ensure_ascii=False) if vits else None,
                            })
                            # salva peso unitario se retornado
                            if peso_unit:
                                from dados.model_prontuario import salvar_ingrediente_item as _sii
                                _sii({
                                    "id": ingr_id,
                                    "item_id": _item_id_ref[0],
                                    "tipo": "item",
                                    "descricao": desc,
                                    "quantidade": qty,
                                    "unidade": unid,
                                    "peso_unitario_g": float(peso_unit),
                                })
                            from backup.drive_backup import fazer_backup
                            fazer_backup(forcar=True)
                    except Exception as ex:
                        log.warning("[ROTINAS] nutr ingrediente: %s", ex)
                    finally:
                        _calc_nutr_i[0] = False
                        lbl_c_i.value = "Recalcular Tabela Nutricional"
                        _refresh_nutr_i()
                        try: page.update()
                        except Exception: pass

                import threading as _thr_ni
                _thr_ni.Thread(target=_run, daemon=True).start()

            btn_claudia_i.on_click = _calcular_nutr_i

            # carrega tabela existente se editando
            if ing.get("id"):
                _refresh_nutr_i()

            area_fi = ft.Column([
                ft.Container(height=8),
                tipo_row_i,
                f_di,
                dd_receita,
                ft.Row([
                    ft.Container(content=f_qi, width=90),
                    ft.Container(content=dd_ui, expand=True),
                ], spacing=8),
                ft.Divider(height=1, color=BD2),
                btn_claudia_i,
                btn_porcao,
                nutr_col_i,
                ft.Container(height=16),
            ], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

            ref_fi[0] = ft.Container(
                content=ft.Column([
                    ft.Container(height=_lay.spacer_topo, bgcolor=BG),
                    cab_fi,
                    ft.Container(
                        content=area_fi, expand=True,
                        padding=ft.padding.symmetric(horizontal=16),
                    ),
                ], spacing=0, expand=True),
                bgcolor=BG, expand=True,
            )
            page.overlay.append(ref_fi[0])
            try: page.update()
            except Exception: pass
            # carrega tabela após overlay montado
            if tipo_i[0] == "receita" and ing.get("sub_receita_id"):
                import asyncio as _aio_r
                async def _dr_r():
                    await _aio_r.sleep(0.05)
                    _refresh_nutr_receita()
                page.run_task(_dr_r)

        btn_add_ingr = ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=12, color=AZUL),
                ft.Text("Adicionar ingrediente", size=12, color=AZUL),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_radius=8, ink=True,
            border=ft.Border(
                top=ft.BorderSide(1, f"{AZUL}55"), bottom=ft.BorderSide(1, f"{AZUL}55"),
                left=ft.BorderSide(1, f"{AZUL}55"), right=ft.BorderSide(1, f"{AZUL}55")),
        )
        btn_add_ingr.on_click = lambda e: _abrir_form_ingrediente()

        # ── Dropdown tabela nutricional do item ───────────────────
        _nutr_aberto = [False]
        nutr_body    = ft.Column(spacing=3, tight=True, visible=False)
        ico_expand   = ft.Icon("expand_more_rounded", size=16, color=SEC)

        def _refresh_nutr_item():
            nutr_body.controls.clear()
            if not _item_id_ref[0]:
                return
            from dados.model_prontuario import calcular_nutricao_item as _cni
            n = _cni(_item_id_ref[0])
            if not n:
                nutr_body.controls.append(
                    ft.Text("Sem dados nutricionais. Calcule nas tabelas dos ingredientes.",
                            size=11, color=MUT))
                return

            def _row(label, val, unid, cor=TXT, negrito=False):
                return ft.Row([
                    ft.Text(label, size=11, color=SEC, expand=True),
                    ft.Text(f"{val:.1f}" if val is not None else "—",
                            size=11, color=cor,
                            weight=ft.FontWeight.W_700 if negrito else ft.FontWeight.NORMAL),
                    ft.Text(f" {unid}", size=10, color=MUT),
                ], spacing=2)

            nutr_body.controls += [
                _row("Valor Energético",  n.get("kcal"),         "kcal", LAR,  True),
                _row("Carboidratos",      n.get("carboidratos"), "g"),
                _row("  Açúcares",        n.get("acucares"),     "g"),
                _row("Proteínas",         n.get("proteinas"),    "g",  VERD, True),
                _row("Gorduras Totais",   n.get("gorduras"),     "g"),
                _row("  Saturadas",       n.get("saturadas"),    "g"),
                _row("  Trans",           n.get("trans"),        "g"),
                _row("Fibra Alimentar",   n.get("fibras"),       "g"),
                _row("Sódio",             n.get("sodio"),        "mg"),
            ]

        def _toggle_nutr(e=None):
            _nutr_aberto[0] = not _nutr_aberto[0]
            if _nutr_aberto[0]:
                _refresh_nutr_item()
            nutr_body.visible = _nutr_aberto[0]
            ico_expand.name = ("expand_less_rounded" if _nutr_aberto[0]
                               else "expand_more_rounded")
            try: page.update()
            except Exception: pass

        btn_nutr_header = ft.Container(
            content=ft.Row([
                ft.Icon("local_fire_department_rounded", size=13, color=LAR),
                ft.Text("Tabela Nutricional", size=12, color=LAR,
                        weight=ft.FontWeight.W_600, expand=True),
                ico_expand,
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_radius=8, ink=True,
            bgcolor=ft.Colors.with_opacity(0.08, LAR),
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.with_opacity(0.3, LAR)),
                bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.3, LAR)),
                left=ft.BorderSide(3, LAR),
                right=ft.BorderSide(1, ft.Colors.with_opacity(0.3, LAR))),
        )
        btn_nutr_header.on_click = _toggle_nutr

        nutr_dropdown = ft.Container(
            content=ft.Column([
                btn_nutr_header,
                ft.Container(
                    content=nutr_body,
                    bgcolor=CARD, border_radius=ft.border_radius.only(
                        bottom_left=8, bottom_right=8),
                    padding=ft.padding.only(left=10, right=10, top=6, bottom=10),
                    border=ft.Border(
                        bottom=ft.BorderSide(1, BD2),
                        left=ft.BorderSide(3, LAR),
                        right=ft.BorderSide(1, BD2)),
                    visible=True,
                ),
            ], spacing=0, tight=True),
            visible=item_id_atual is not None,
        )

        # ingredientes e tabela nutricional so para alimento
        bloco_ingr = ft.Column([
            ft.Divider(height=1, color=BD2),
            ft.Text("INGREDIENTES", size=10, color=SEC, weight=ft.FontWeight.W_600),
            ingr_col,
            btn_add_ingr,
            nutr_dropdown,
        ], spacing=8, tight=True,
           visible=tipo_it[0] == "alimento")

        # visibilidade inicial baseada no tipo
        f_desc.visible         = tipo_it[0] != "remedio"
        f_qtd_rem.visible      = tipo_it[0] == "remedio"
        nutr_rem_col.visible   = tipo_it[0] == "remedio"

        # carrega nutricional se editando item com remédio
        if tipo_it[0] == "remedio" and _rem_id_sel[0]:
            _atualizar_nutr_rem()

        area_it = ft.Column([
            ft.Container(height=8),
            ft.Text("TIPO", size=10, color=SEC, weight=ft.FontWeight.W_600),
            row_it,
            f_desc,
            bloco_remedio,
            f_qtd_rem,
            nutr_rem_col,
            bloco_horas,
            bloco_gasto,
            row_intens,
            bloco_freq,
            bloco_ingr,
            ft.Container(height=16),
        ], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

        ref_it[0] = ft.Container(
            content=ft.Column([
                ft.Container(height=_lay.spacer_topo, bgcolor=BG),
                cab_it,
                ft.Container(
                    content=area_it, expand=True,
                    padding=ft.padding.symmetric(horizontal=16),
                ),
            ], spacing=0, expand=True),
            bgcolor=BG, expand=True,
        )
        page.overlay.append(ref_it[0])
        try: page.update()
        except Exception: pass
        if _item_id_ref[0]:
            import asyncio as _asyncio
            async def _delayed_refresh():
                await _asyncio.sleep(0.05)
                _refresh_ingr()
            page.run_task(_delayed_refresh)

    _refresh_itens()

    # ── Campos hora início/fim para tipos de gasto ─────────────────
    import re as _re_tmpl

    def _mk_hora_tmpl(label, valor=""):
        tf = ft.TextField(
            label=label, value=valor,
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT), border_radius=8,
            keyboard_type=ft.KeyboardType.NUMBER, expand=True,
        )
        def _mask(e):
            raw = _re_tmpl.sub(r"\D", "", tf.value or "")[:4]
            novo = (raw[:2] + ":" + raw[2:]) if len(raw) >= 3 else raw
            if tf.value != novo:
                tf.value = novo
                try: tf.update()
                except Exception: pass
        tf.on_change = _mask
        return tf

    f_h_ini_tmpl = _mk_hora_tmpl("Inicio (HH:MM)", template.get("hora_inicio","") or "")
    f_h_fim_tmpl = _mk_hora_tmpl("Fim (HH:MM)",    template.get("hora_fim","")    or "")

    _INTENS_FISICO_T = [("leve","Leve",2.5),("moderado","Moderado",5.0),("intenso","Intenso",9.0)]
    _INTENS_MENTAL_T = [("leve","Leve",1.3),("moderado","Moderado",1.6),("intenso","Intenso",1.9)]
    intens_f_tmpl = [template.get("intensidade_fisica") if template else None]
    intens_m_tmpl = [template.get("intensidade_mental") if template else None]

    # para tipo "trabalho": escolha Manual ou Mental
    # "estudo" sempre mental; "exercicio" sempre fisico
    _trabalho_fisico = [bool(template.get("intensidade_fisica")) if template else False]
    row_tipo_trabalho = ft.Row(spacing=8, visible=False)

    def _rebuild_tipo_trabalho():
        row_tipo_trabalho.controls.clear()
        for eh_fis, icone, label, cor in [
            (False, "psychology_rounded", "Mental/Intelectual", ROXO),
            (True,  "construction_rounded", "Manual/Fisico",    LAR),
        ]:
            sel = _trabalho_fisico[0] == eh_fis
            chip = ft.Container(
                content=ft.Row([
                    ft.Icon(icone, size=14, color=cor if sel else SEC),
                    ft.Text(label, size=11, color=cor if sel else SEC,
                            weight=ft.FontWeight.W_600 if sel else ft.FontWeight.NORMAL),
                ], spacing=6, tight=True),
                bgcolor=ft.Colors.with_opacity(0.15, cor) if sel else CARD,
                border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border=ft.Border(
                    top=ft.BorderSide(1, cor if sel else BD),
                    bottom=ft.BorderSide(1, cor if sel else BD),
                    left=ft.BorderSide(1, cor if sel else BD),
                    right=ft.BorderSide(1, cor if sel else BD)),
            )
            def _sel_tw(e, fis=eh_fis):
                _trabalho_fisico[0] = fis
                # limpa intensidade do tipo que foi desmarcado
                if fis:
                    intens_m_tmpl[0] = None
                else:
                    intens_f_tmpl[0] = None
                _rebuild_tipo_trabalho()
                _rebuild_intens_tmpl()
                _atualizar_gasto_tmpl()
                try: page.update()
                except Exception: pass
            chip.on_click = _sel_tw
            row_tipo_trabalho.controls.append(chip)

    _rebuild_tipo_trabalho()

    def _eh_fisico_tmpl():
        """Retorna True se a rotina atual usa METs físicos."""
        if tipo_sel[0] == "exercicio": return True
        if tipo_sel[0] == "estudo":    return False  # sempre mental
        # trabalho: depende da escolha do usuário
        return _trabalho_fisico[0]

    row_intens_tmpl = ft.Row(spacing=6, wrap=True)
    txt_gasto_tmpl  = ft.Text("", size=11, color=LAR, weight=ft.FontWeight.W_600)

    def _atualizar_gasto_tmpl():
        hi = (f_h_ini_tmpl.value or "").strip()
        hf = (f_h_fim_tmpl.value or "").strip()
        if not (hi and hf): txt_gasto_tmpl.value = ""; return
        from dados.model_prontuario import calcular_gasto_item as _cgi
        try:
            from dados.model_prontuario import DB_PATH as _DB
            import sqlite3 as _sq
            with _sq.connect(_DB, timeout=5) as _c:
                rp = _c.execute("SELECT peso FROM perfil_usuario LIMIT 1").fetchone()
            peso = float(rp[0]) if rp and rp[0] else 80.0
        except Exception:
            peso = 80.0
        eh_fisico = _eh_fisico_tmpl()
        r = _cgi(hi, hf,
                 intens_f_tmpl[0] if     eh_fisico else None,
                 intens_m_tmpl[0] if not eh_fisico else None,
                 peso)
        if r:
            h = r["duracao_min"] // 60; m = r["duracao_min"] % 60
            dur = f"{h}h{m:02d}min" if h else f"{m}min"
            txt_gasto_tmpl.value = f"−{r['kcal_gasto']:.0f} kcal  ({dur}  MET {r['met']})"
        else:
            txt_gasto_tmpl.value = ""
        try: page.update()
        except Exception: pass

    def _rebuild_intens_tmpl():
        row_intens_tmpl.controls.clear()
        eh_fisico = _eh_fisico_tmpl()
        lista    = _INTENS_FISICO_T if eh_fisico else _INTENS_MENTAL_T
        sel_ref  = intens_f_tmpl    if eh_fisico else intens_m_tmpl
        cor_int  = LAR if eh_fisico else ROXO
        for k, lbl, met in lista:
            sel = k == sel_ref[0]
            chip = ft.Container(
                content=ft.Column([
                    ft.Text(lbl, size=11, color=cor_int if sel else SEC,
                            weight=ft.FontWeight.W_600 if sel else ft.FontWeight.NORMAL),
                    ft.Text(f"MET {met}", size=9, color=MUT),
                ], spacing=0, tight=True,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=ft.Colors.with_opacity(0.15, cor_int) if sel else CARD,
                border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=14, vertical=8),
                border=ft.Border(
                    top=ft.BorderSide(1, cor_int if sel else BD),
                    bottom=ft.BorderSide(1, cor_int if sel else BD),
                    left=ft.BorderSide(1, cor_int if sel else BD),
                    right=ft.BorderSide(1, cor_int if sel else BD)),
            )
            def _si(e, kk=k, sr=sel_ref):
                sr[0] = kk; _rebuild_intens_tmpl(); _atualizar_gasto_tmpl()
                try: page.update()
                except Exception: pass
            chip.on_click = _si
            row_intens_tmpl.controls.append(chip)

    _rebuild_intens_tmpl()

    bloco_gasto_tmpl = ft.Column([
        ft.Row([f_h_ini_tmpl, f_h_fim_tmpl], spacing=8),
        row_tipo_trabalho,
        ft.Text("INTENSIDADE", size=10, color=SEC, weight=ft.FontWeight.W_600),
        row_intens_tmpl,
        ft.Row([
            ft.Icon("local_fire_department_rounded", size=13, color=VERM),
            txt_gasto_tmpl,
        ], spacing=6),
    ], spacing=8, tight=True,
       visible=tipo_sel[0] in _TIPOS_GASTO_TMPL)

    # ── Tipos buttons ──────────────────────────────────────────────
    def _rebuild_tipos():
        row_tipos.controls.clear()
        for k, icone, cor, label in _TIPOS_TEMPLATE:
            sel = k == tipo_sel[0]
            c = ft.Container(
                content=ft.Column([
                    ft.Icon(icone, size=16, color=cor if sel else SEC),
                    ft.Text(label, size=9, color=cor if sel else SEC),
                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                bgcolor=ft.Colors.with_opacity(0.15, cor) if sel else CARD,
                border_radius=8, width=72, height=52,
                alignment=ft.Alignment(0, 0),
                border=ft.Border(
                    top=ft.BorderSide(1, cor if sel else BD),
                    bottom=ft.BorderSide(1, cor if sel else BD),
                    left=ft.BorderSide(1, cor if sel else BD),
                    right=ft.BorderSide(1, cor if sel else BD)),
                ink=True,
            )
            def _sel(e, kk=k):
                tipo_sel[0] = kk
                eh_gasto = kk in _TIPOS_GASTO_TMPL
                bloco_gasto_tmpl.visible  = eh_gasto
                f_horario.visible         = not eh_gasto
                btn_add.visible           = not eh_gasto
                nutr_dropdown.visible     = not eh_gasto
                gasto_dropdown.visible    = eh_gasto
                # seletor Manual/Mental só para "trabalho"
                row_tipo_trabalho.visible = kk == "trabalho"
                _rebuild_tipo_trabalho()
                _rebuild_intens_tmpl()
                _rebuild_tipos()
                try: page.update()
                except Exception: pass
            c.on_click = _sel
            row_tipos.controls.append(c)

    _rebuild_tipos()

    # ── Botao adicionar item ───────────────────────────────────────
    lbl_btn_add = ft.Text("Adicionar item", size=12, color=AZUL)
    btn_add = ft.Container(
        content=ft.Row([
            ft.Icon("add_rounded", size=12, color=AZUL),
            lbl_btn_add,
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8, ink=True,
        border=ft.Border(
            top=ft.BorderSide(1, f"{AZUL}55"), bottom=ft.BorderSide(1, f"{AZUL}55"),
            left=ft.BorderSide(1, f"{AZUL}55"), right=ft.BorderSide(1, f"{AZUL}55")))

    def _set_btn_add(salvando: bool):
        btn_add.disabled = salvando
        btn_add.opacity  = 0.45 if salvando else 1.0
        lbl_btn_add.value = "Salvando..." if salvando else "Adicionar item"
        try: page.update()
        except Exception: pass

    def _click_add_item(e=None):
        # auto-save se template ainda nao tem id
        if not template.get("id"):
            nome = (f_nome.value or "").strip()
            if not nome:
                txt_err.value = "Informe o nome da rotina primeiro."
                try: page.update()
                except Exception: pass
                return
            txt_err.value = ""
            _set_btn_add(True)
            hora = (f_horario.value or "").strip()
            if hora and len(hora) == 4 and hora.isdigit():
                hora = hora[:2] + ":" + hora[2:]
            cor_map = {"alimentacao": VERD, "exercicio": LAR, "trabalho": AZUL,
                       "lazer": ROXO, "medicacao": AZUL, "rotina": SEC, "estudo": ROXO}
            tid = salvar_template({
                "nome":    nome, "tipo": tipo_sel[0],
                "horario": hora or None,
                "icone":   "today_rounded",
                "cor":     cor_map.get(tipo_sel[0], AZUL),
                "padrao":  0, "ativo": 1,
                **_campos_gasto_tmpl(),
            })
            template["id"] = tid
            tipo_mom = _TIPO_MOM_MAP.get(tipo_sel[0], "outro")
            moms = listar_momentos(tid)
            if moms:
                momento_id[0] = moms[0]["id"]
            else:
                momento_id[0] = salvar_momento({
                    "template_id": tid, "nome": nome,
                    "tipo": tipo_mom, "horario": hora or None})
            _set_btn_add(False)
        _abrir_form_item()

    btn_add.on_click = _click_add_item

    def _campos_gasto_tmpl():
        eh_fisico = tipo_sel[0] == "exercicio"
        return {
            "hora_inicio":        (f_h_ini_tmpl.value or "").strip() or None,
            "hora_fim":           (f_h_fim_tmpl.value or "").strip() or None,
            "intensidade_fisica": intens_f_tmpl[0] if     eh_fisico else None,
            "intensidade_mental": intens_m_tmpl[0] if not eh_fisico else None,
        }

    # ── Salvar template ────────────────────────────────────────────
    def _salvar_template(e=None):
        nome = (f_nome.value or "").strip()
        if not nome:
            txt_err.value = "Nome obrigatorio."
            try: page.update()
            except Exception: pass
            return
        hora = (f_horario.value or "").strip()
        if hora and len(hora) == 4 and hora.isdigit():
            hora = hora[:2] + ":" + hora[2:]
        cor_map = {"alimentacao": VERD, "exercicio": LAR, "trabalho": AZUL,
                   "lazer": ROXO, "medicacao": AZUL, "rotina": SEC, "estudo": ROXO}
        tid = salvar_template({
            "id":      template["id"],
            "nome":    nome,
            "tipo":    tipo_sel[0],
            "horario": hora or None,
            "icone":   "today_rounded",
            "cor":     cor_map.get(tipo_sel[0], AZUL),
            "padrao":  template.get("padrao", 0),
            "ativo":   1,
            **_campos_gasto_tmpl(),
        })
        tipo_mom = _TIPO_MOM_MAP.get(tipo_sel[0], "outro")
        try:
            moms = listar_momentos(tid)
            if moms:
                salvar_momento({"id": moms[0]["id"], "template_id": tid,
                                "nome": nome, "tipo": tipo_mom, "horario": hora or None})
                momento_id[0] = moms[0]["id"]
            else:
                mid = salvar_momento({"template_id": tid, "nome": nome,
                                      "tipo": tipo_mom, "horario": hora or None})
                momento_id[0] = mid
        except Exception as ex:
            print(f"[OVERLAY_FORM] salvar: {ex}", flush=True)
        _fechar()
        if on_salvo:
            on_salvo()
        def _bkp():
            try:
                from backup.drive_backup import fazer_backup
                fazer_backup(forcar=True)
            except Exception: pass
        _thr.Thread(target=_bkp, daemon=True).start()

    btn_salvar = ft.Container(
        content=ft.Row([
            ft.Icon("check_rounded", size=14, color=BG),
            ft.Text("Salvar", size=13, color=BG, weight=ft.FontWeight.W_600),
        ], spacing=4, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=VERD, border_radius=10,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        ink=True, expand=True, alignment=ft.Alignment(0, 0))
    btn_salvar.on_click = _salvar_template

    # ── Cabecalho padrao Koios ─────────────────────────────────────
    from shared.layout import Layout as _Layout
    _lay = _Layout(page)

    btn_salvar_cab = ft.Container(
        content=ft.Row([
            ft.Icon("check_rounded", size=14, color=VERD),
            ft.Text("Salvar", size=13, color=VERD, weight=ft.FontWeight.W_600),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        border_radius=8, ink=True,
    )
    btn_salvar_cab.on_click = _salvar_template

    cabecalho = _lay.criar_cabecalho(
        "Editar Rotina", _fechar,
        icone_titulo="today_rounded", cor_titulo=AZUL,
        acoes=[btn_salvar_cab],
    )

    # ── Resumo nutricional (tipos de ingestão) ────────────────────
    _nutr_ab   = [False]
    nutr_body  = ft.Column(spacing=3, tight=True, visible=False)
    ico_exp    = ft.Icon("expand_more_rounded", size=16, color=SEC)

    def _refresh_nutr_m():
        nutr_body.controls.clear()
        mid = momento_id[0]
        if not mid:
            nutr_body.controls.append(
                ft.Text("Salve a rotina para ver o resumo.", size=11, color=MUT))
            return
        from dados.model_prontuario import calcular_nutricao_momento as _cnm
        n = _cnm(mid)
        if not n:
            nutr_body.controls.append(
                ft.Text("Sem dados. Calcule nos ingredientes.", size=11, color=MUT))
            return
        def _row(label, val, unid, cor=TXT, negrito=False):
            return ft.Row([
                ft.Text(label, size=11, color=SEC, expand=True),
                ft.Text(f"{val:.1f}" if val is not None else "—", size=11, color=cor,
                        weight=ft.FontWeight.W_700 if negrito else ft.FontWeight.NORMAL),
                ft.Text(f" {unid}", size=10, color=MUT),
            ], spacing=2)
        nutr_body.controls += [
            _row("Valor Energético", n.get("kcal"),         "kcal", LAR,  True),
            _row("Carboidratos",     n.get("carboidratos"), "g"),
            _row("Proteínas",        n.get("proteinas"),    "g",  VERD, True),
            _row("Gorduras Totais",  n.get("gorduras"),     "g"),
            _row("Fibra Alimentar",  n.get("fibras"),       "g"),
            _row("Sódio",            n.get("sodio"),        "mg"),
        ]

    def _toggle_nutr_m(e=None):
        _nutr_ab[0] = not _nutr_ab[0]
        if _nutr_ab[0]: _refresh_nutr_m()
        nutr_body.visible = _nutr_ab[0]
        ico_exp.name = "expand_less_rounded" if _nutr_ab[0] else "expand_more_rounded"
        try: page.update()
        except Exception: pass

    btn_nutr = ft.Container(
        content=ft.Row([
            ft.Icon("local_fire_department_rounded", size=13, color=LAR),
            ft.Text("Resumo Nutricional", size=12, color=LAR,
                    weight=ft.FontWeight.W_600, expand=True),
            ico_exp,
        ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8, ink=True,
        bgcolor=ft.Colors.with_opacity(0.08, LAR),
        border=ft.Border(
            top=ft.BorderSide(1, ft.Colors.with_opacity(0.3, LAR)),
            bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.3, LAR)),
            left=ft.BorderSide(3, LAR),
            right=ft.BorderSide(1, ft.Colors.with_opacity(0.3, LAR))),
    )
    btn_nutr.on_click = _toggle_nutr_m

    nutr_dropdown = ft.Column([
        btn_nutr,
        ft.Container(
            content=nutr_body, bgcolor=CARD,
            border_radius=ft.border_radius.only(bottom_left=8, bottom_right=8),
            padding=ft.padding.only(left=10, right=10, top=6, bottom=10),
            border=ft.Border(
                bottom=ft.BorderSide(1, BD2),
                left=ft.BorderSide(3, LAR),
                right=ft.BorderSide(1, BD2)),
        ),
    ], spacing=0, tight=True)

    # ── Gasto estimado (tipos de gasto) ───────────────────────────
    _gasto_ab    = [False]
    _met_claudia = [None]   # MET refinado pela Claudia
    gasto_body   = ft.Column(spacing=4, tight=True, visible=False)
    ico_exp_g    = ft.Icon("expand_more_rounded", size=16, color=SEC)
    lbl_claudia_g = ft.Text("Refinar com Claudia", size=11, color=ROXO)
    _calc_g      = [False]

    def _get_peso():
        try:
            from dados.model_prontuario import DB_PATH as _DB
            import sqlite3 as _sq
            with _sq.connect(_DB, timeout=5) as _c:
                rp = _c.execute("SELECT peso FROM perfil_usuario LIMIT 1").fetchone()
            return float(rp[0]) if rp and rp[0] else 80.0
        except Exception:
            return 80.0

    def _refresh_gasto_m():
        gasto_body.controls.clear()
        hi = (f_h_ini_tmpl.value or "").strip()
        hf = (f_h_fim_tmpl.value or "").strip()
        if not (hi and hf):
            gasto_body.controls.append(
                ft.Text("Preencha inicio e fim para ver o gasto.", size=11, color=MUT))
            gasto_body.controls.append(btn_claudia_g)
            return
        from dados.model_prontuario import calcular_gasto_item as _cgi
        peso = _get_peso()
        eh_fisico = _eh_fisico_tmpl()
        # usa MET da Claudia se disponível, senão usa intensidade selecionada
        if _met_claudia[0]:
            from datetime import datetime as _dt
            try:
                dur_min = (
                    _dt.strptime(hf, "%H:%M") - _dt.strptime(hi, "%H:%M")
                ).seconds // 60
                kcal = _met_claudia[0] * peso * (dur_min / 60.0)
                h = dur_min // 60; m = dur_min % 60
                dur = f"{h}h{m:02d}min" if h else f"{m}min"
                r = {"kcal_gasto": round(kcal, 1),
                     "duracao_min": dur_min, "met": _met_claudia[0]}
            except Exception:
                r = None
        else:
            r = _cgi(hi, hf,
                     intens_f_tmpl[0] if eh_fisico else None,
                     intens_m_tmpl[0] if not eh_fisico else None,
                     peso)
        if not r:
            gasto_body.controls.append(
                ft.Text("Nao foi possivel calcular.", size=11, color=MUT))
            gasto_body.controls.append(btn_claudia_g)
            return
        h = r["duracao_min"] // 60; m = r["duracao_min"] % 60
        dur = f"{h}h{m:02d}min" if h else f"{m}min"
        fonte = " (Claudia)" if _met_claudia[0] else ""
        gasto_body.controls += [
            ft.Row([
                ft.Text("Duracao", size=11, color=SEC, expand=True),
                ft.Text(dur, size=11, color=TXT, weight=ft.FontWeight.W_600),
            ], spacing=4),
            ft.Row([
                ft.Text(f"MET{fonte}", size=11, color=SEC, expand=True),
                ft.Text(str(r["met"]), size=11,
                        color=ROXO if _met_claudia[0] else TXT),
            ], spacing=4),
            ft.Row([
                ft.Text("Peso", size=11, color=SEC, expand=True),
                ft.Text(f"{peso:.0f} kg", size=11, color=TXT),
            ], spacing=4),
            ft.Divider(height=1, color=BD2),
            ft.Row([
                ft.Text("Gasto estimado", size=12, color=VERM,
                        weight=ft.FontWeight.W_700, expand=True),
                ft.Text(f"−{r['kcal_gasto']:.0f} kcal", size=13, color=VERM,
                        weight=ft.FontWeight.W_700),
            ], spacing=4),
            btn_claudia_g,
        ]

    def _calcular_claudia_gasto(e=None):
        if _calc_g[0]: return
        desc = (f_nome.value or "").strip()
        hi = (f_h_ini_tmpl.value or "").strip()
        hf = (f_h_fim_tmpl.value or "").strip()
        if not desc: return
        _calc_g[0] = True
        lbl_claudia_g.value = "Calculando..."
        try: page.update()
        except Exception: pass

        def _run():
            try:
                from utils.claudia_engine import get_client, _MODELO
                peso = _get_peso()
                eh_fisico = _eh_fisico_tmpl()
                tipo_esforco = "fisico/manual" if eh_fisico else "intelectual/mental"
                prompt = (
                    f"Qual e o MET (Metabolic Equivalent of Task) mais preciso para: "
                    f"'{desc}' — esforco {tipo_esforco}. "
                    f"Pessoa de {peso:.0f}kg, periodo {hi} ate {hf}. "
                    "Retorne SOMENTE JSON: {\"met\": 1.6, \"justificativa\": \"...\"}"
                )
                client = get_client()
                resp = client.messages.create(
                    model=_MODELO, max_tokens=200,
                    system="Voce e um fisiologista. Retorne SOMENTE JSON valido.",
                    messages=[{"role": "user", "content": prompt}],
                )
                import json as _json
                raw = "".join(b.text for b in resp.content
                              if hasattr(b, "text")).strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"): raw = raw[4:]
                dados = _json.loads(raw)
                _met_claudia[0] = float(dados.get("met", 1.6))
            except Exception as ex:
                log.warning("[GASTO] claudia: %s", ex)
            finally:
                _calc_g[0] = False
                lbl_claudia_g.value = "Recalcular com Claudia"
                _refresh_gasto_m()
                try: page.update()
                except Exception: pass

        import threading as _thr_g
        _thr_g.Thread(target=_run, daemon=True).start()

    btn_claudia_g = ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Text("C", size=9, color=BG, weight=ft.FontWeight.W_700),
                width=18, height=18, border_radius=9, bgcolor=ROXO,
                alignment=ft.Alignment(0, 0)),
            lbl_claudia_g,
        ], spacing=6, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8, ink=True,
        border=ft.Border(
            top=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO)),
            bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO)),
            left=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO)),
            right=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO))),
    )
    btn_claudia_g.on_click = _calcular_claudia_gasto

    def _toggle_gasto_m(e=None):
        _gasto_ab[0] = not _gasto_ab[0]
        if _gasto_ab[0]: _refresh_gasto_m()
        gasto_body.visible = _gasto_ab[0]
        ico_exp_g.name = "expand_less_rounded" if _gasto_ab[0] else "expand_more_rounded"
        try: page.update()
        except Exception: pass

    btn_gasto_acc = ft.Container(
        content=ft.Row([
            ft.Icon("local_fire_department_rounded", size=13, color=VERM),
            ft.Text("Gasto do Corpo", size=12, color=VERM,
                    weight=ft.FontWeight.W_600, expand=True),
            ico_exp_g,
        ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8, ink=True,
        bgcolor=ft.Colors.with_opacity(0.08, VERM),
        border=ft.Border(
            top=ft.BorderSide(1, ft.Colors.with_opacity(0.3, VERM)),
            bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.3, VERM)),
            left=ft.BorderSide(3, VERM),
            right=ft.BorderSide(1, ft.Colors.with_opacity(0.3, VERM))),
    )
    btn_gasto_acc.on_click = _toggle_gasto_m

    gasto_dropdown = ft.Column([
        btn_gasto_acc,
        ft.Container(
            content=gasto_body, bgcolor=CARD,
            border_radius=ft.border_radius.only(bottom_left=8, bottom_right=8),
            padding=ft.padding.only(left=10, right=10, top=6, bottom=10),
            border=ft.Border(
                bottom=ft.BorderSide(1, BD2),
                left=ft.BorderSide(3, VERM),
                right=ft.BorderSide(1, BD2)),
        ),
    ], spacing=0, tight=True)

    # estado inicial baseado no tipo já salvo
    _eh_gasto_ini = tipo_sel[0] in _TIPOS_GASTO_TMPL
    f_horario.visible         = not _eh_gasto_ini
    btn_add.visible           = not _eh_gasto_ini
    nutr_dropdown.visible     = not _eh_gasto_ini
    gasto_dropdown.visible    = _eh_gasto_ini
    row_tipo_trabalho.visible = tipo_sel[0] == "trabalho"

    area_scroll = ft.Column([
        ft.Container(height=8),
        ft.Text("TIPO", size=10, color=SEC, weight=ft.FontWeight.W_600),
        row_tipos,
        ft.Container(height=4),
        f_nome,
        f_horario,
        bloco_gasto_tmpl,
        ft.Divider(height=1, color=BD2),
        itens_col,
        btn_add,
        nutr_dropdown,
        gasto_dropdown,
        txt_err,
        ft.Container(height=16),
    ], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    tela_interna = ft.Container(
        content=ft.Column([
            ft.Container(height=_lay.spacer_topo, bgcolor=BG),
            cabecalho,
            ft.Container(
                content=area_scroll,
                expand=True,
                padding=ft.padding.symmetric(horizontal=16),
            ),
        ], spacing=0, expand=True),
        bgcolor=BG, expand=True,
    )

    ref_ov[0] = ft.Container(
        content=tela_interna,
        expand=True,
    )
    page.overlay.append(ref_ov[0])
    try: page.update()
    except Exception: pass
