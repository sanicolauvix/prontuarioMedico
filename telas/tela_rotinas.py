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
    listar_remedios, salvar_rotina_diario,
    salvar_nutricao_item, listar_nutricao_por_template,
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


def criar_tela_rotinas(page: ft.Page, voltar_fn, navegar_fn=None) -> ft.Container:
    lay      = Layout(page)
    area     = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
    _montado = [False]

    # Estado de navegacao interna: lista | detalhe | momento
    _vista        = ["lista"]
    _template_sel = [None]   # dict do template atual
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
        ("lazer",       "weekend_rounded",         ROXO, "Lazer"),
    ]
    _TIPO_ITEM_MAP = {
        "alimentacao": ("refeicao",  "alimento",  "Itens da refeicao"),
        "exercicio":   ("atividade", "atividade", "Atividades"),
        "trabalho":    ("trabalho",  "atividade", "Tarefas"),
        "lazer":       ("outro",     "atividade", "Atividades de lazer"),
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
        f_nome    = _campo("Nome *", template["nome"] if template else "",
                           hint="ex: Cafe da Manha, Treino, Trabalho…")
        f_horario = _campo("Horario (HH:MM)", template.get("horario","") if template else "",
                           hint="ex: 07:00", keyboard=ft.KeyboardType.NUMBER)
        tipo_sel  = [template.get("tipo","alimentacao") if template else "alimentacao"]
        row_tipos = ft.Row(spacing=6, wrap=True)

        # ── Itens inline ──────────────────────────────────────────
        # Cada entrada: {"f": TextField, "freq": [str], "susp_de": TextField,
        #                "susp_ate": TextField, "susp_open": [bool], "id": int|None}
        itens_data = []
        itens_col  = ft.Column(spacing=8, tight=True)
        lbl_itens  = ft.Text("Itens", size=10, color=SEC, weight=ft.FontWeight.W_600)

        def _novo_item_entry(desc="", qty="", unid="Unidade", freq="diario", iid=None):
            dd = ft.Dropdown(
                label="Unidade",
                options=[ft.dropdown.Option(key=k, text=v) for k, v in _UNIDADES],
                value=unid,
                bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
                label_style=ft.TextStyle(color=SEC, size=11),
                text_style=ft.TextStyle(color=TXT, size=12),
                border_radius=8,
            )
            dd.on_change = lambda e: None
            return {
                "f":         _campo("Descricao *", desc,
                                    hint="ex: ovos caipiras - omeletes"),
                "qty":       _campo("Qtd", qty, hint="3", keyboard=ft.KeyboardType.NUMBER),
                "unidade_dd": dd,
                "freq":      [freq],
                "susp_de":   _campo("De (AAAA-MM-DD)", hint=date.today().isoformat(),
                                    keyboard=ft.KeyboardType.NUMBER),
                "susp_ate":  _campo("Ate (AAAA-MM-DD)", hint="indefinido = vazio",
                                    keyboard=ft.KeyboardType.NUMBER),
                "susp_open": [False],
                "id":        iid,
            }

        if template:
            try:
                moms = listar_momentos(template["id"])
                if moms:
                    for it in listar_itens(moms[0]["id"]):
                        itens_data.append(_novo_item_entry(
                            it.get("descricao",""),
                            it.get("quantidade","") or "",
                            it.get("unidade","Unidade") or "Unidade",
                            it.get("frequencia","diario"),
                            it.get("id")))
            except Exception:
                pass

        def _freq_row(entry):
            row = ft.Row(spacing=4, wrap=True)
            for chave, label in _FREQUENCIAS:
                sel = chave == entry["freq"][0]
                cor = AZUL if sel else SEC
                btn = ft.Container(
                    content=ft.Text(label, size=10, color=cor,
                                    weight=ft.FontWeight.W_600 if sel else ft.FontWeight.NORMAL),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=12, ink=True,
                    bgcolor=f"{AZUL}22" if sel else BD,
                    border=ft.Border(
                        top=ft.BorderSide(1, f"{AZUL}88" if sel else BD2),
                        bottom=ft.BorderSide(1, f"{AZUL}88" if sel else BD2),
                        left=ft.BorderSide(1, f"{AZUL}88" if sel else BD2),
                        right=ft.BorderSide(1, f"{AZUL}88" if sel else BD2)),
                )
                def _sel_f(e, k=chave, en=entry):
                    en["freq"][0] = k
                    _refresh_itens()
                    try: page.update()
                    except Exception: pass
                btn.on_click = _sel_f
                row.controls.append(btn)
            return row

        def _refresh_itens():
            _, _, lbl = _TIPO_ITEM_MAP.get(tipo_sel[0], ("outro","atividade","Itens"))
            lbl_itens.value = lbl
            itens_col.controls.clear()
            for i, en in enumerate(itens_data):
                btn_rem = ft.Container(
                    content=ft.Icon("close_rounded", size=14, color=VERM),
                    padding=ft.padding.all(4), ink=True, border_radius=6)
                def _rem(e, idx=i):
                    itens_data.pop(idx)
                    _refresh_itens()
                    try: page.update()
                    except Exception: pass
                btn_rem.on_click = _rem

                aberto = en["susp_open"][0]
                cor_susp = VERM if aberto else MUT
                lbl_susp = "Cancelar suspensao" if aberto else "Suspender por periodo"
                btn_susp = ft.Container(
                    content=ft.Row([
                        ft.Icon("event_busy_rounded", size=11, color=cor_susp),
                        ft.Text(lbl_susp, size=10, color=cor_susp),
                    ], spacing=4, tight=True),
                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                    border_radius=10, ink=True,
                )
                def _toggle_susp(e, en=en):
                    en["susp_open"][0] = not en["susp_open"][0]
                    if not en["susp_open"][0]:
                        en["susp_de"].value  = ""
                        en["susp_ate"].value = ""
                    _refresh_itens()
                    try: page.update()
                    except Exception: pass
                btn_susp.on_click = _toggle_susp

                filhos = [
                    ft.Row([en["f"], btn_rem], spacing=4),
                    ft.Row([
                        ft.Container(content=en["qty"], width=80),
                        ft.Container(content=en["unidade_dd"], expand=True),
                    ], spacing=6),
                    _freq_row(en),
                    btn_susp,
                ]
                if aberto:
                    filhos += [
                        ft.Row([en["susp_de"], en["susp_ate"]], spacing=6),
                    ]

                itens_col.controls.append(ft.Container(
                    content=ft.Column(filhos, spacing=4, tight=True),
                    bgcolor=BG, border_radius=8,
                    padding=ft.padding.symmetric(horizontal=8, vertical=6),
                    border=ft.Border(
                        top=ft.BorderSide(1, f"{VERM}55" if aberto else BD2),
                        bottom=ft.BorderSide(1, f"{VERM}55" if aberto else BD2),
                        left=ft.BorderSide(3, VERM if aberto else BD2),
                        right=ft.BorderSide(1, f"{VERM}55" if aberto else BD2)),
                ))

        _refresh_itens()

        btn_add = ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=12, color=AZUL),
                ft.Text("Adicionar item", size=12, color=AZUL),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border_radius=8, ink=True,
            border=ft.Border(
                top=ft.BorderSide(1, f"{AZUL}55"), bottom=ft.BorderSide(1, f"{AZUL}55"),
                left=ft.BorderSide(1, f"{AZUL}55"), right=ft.BorderSide(1, f"{AZUL}55")))
        def _add_item(e=None):
            itens_data.append(_novo_item_entry())
            _refresh_itens()
            try: page.update()
            except Exception: pass
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
            tipo_mom, tipo_item, _ = _TIPO_ITEM_MAP.get(tipo_sel[0], ("outro","atividade","Itens"))
            try:
                moms = listar_momentos(tid)
                if moms:
                    mid = moms[0]["id"]
                    salvar_momento({"id": mid, "template_id": tid,
                                    "nome": f_nome.value.strip(),
                                    "tipo": tipo_mom, "horario": hora or None})
                    for it in listar_itens(mid):
                        excluir_item(it["id"])
                else:
                    mid = salvar_momento({"template_id": tid,
                                          "nome": f_nome.value.strip(),
                                          "tipo": tipo_mom, "horario": hora or None})
                for i, en in enumerate(itens_data):
                    desc = (en["f"].value or "").strip()
                    if not desc:
                        continue
                    novo_id = salvar_item({"momento_id": mid, "tipo": tipo_item,
                                           "descricao": desc,
                                           "quantidade": (en["qty"].value or "").strip() or None,
                                           "unidade":    en["unidade_dd"].value or "un",
                                           "frequencia": en["freq"][0],
                                           "ordem": i})
                    susp_de  = (en["susp_de"].value  or "").strip()
                    susp_ate = (en["susp_ate"].value or "").strip()
                    if susp_de or susp_ate:
                        salvar_rotina_diario({
                            "data":      susp_de or date.today().isoformat(),
                            "item_id":   novo_id,
                            "item_nome": desc,
                            "tipo":      "suspensao",
                            "descricao": f"Suspenso: {desc}",
                            "data_fim":  susp_ate or None,
                        })
            except Exception as ex:
                print(f"[ROTINAS] salvar itens: {ex}", flush=True)
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
            lbl_itens,
            itens_col,
            btn_add,
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

    def _form_item(momento_id, item=None):
        tipo_item_sel = [item["tipo"] if item else "alimento"]

        _TIPOS_ITEM = [
            ("alimento",  "restaurant_rounded",  VERD, "Alimento"),
            ("remedio",   "medication_rounded",  AZUL, "Remedio"),
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

                card = ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Icon(icone, size=22, color=cor),
                            bgcolor=f"{cor}22", border_radius=10, width=44, height=44,
                            alignment=ft.alignment.Alignment(0, 0),
                        ),
                        ft.Column(info_col_filhos, spacing=2, expand=True),
                        ft.Row([
                            _btn_icon("edit_rounded", SEC, lambda e, tt=t: _form_template(tt)),
                            _btn_icon("delete_outline_rounded", VERM, lambda e, tt=t: _confirmar_exclusao(
                                "Excluir rotina?",
                                f"'{tt['nome']}' e todos os seus momentos serao excluidos.",
                                lambda tid=tt["id"]: [excluir_template(tid), _mostrar_lista()],
                            )),
                        ], spacing=4),
                    ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
                    bgcolor=CARD, border_radius=10, padding=ft.padding.all(12),
                    border=ft.Border(
                        top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                        left=ft.BorderSide(3, cor), right=ft.BorderSide(1, BD),
                    ),
                    ink=True,
                )
                card.on_click = lambda e, tt=t: _mostrar_detalhe(tt)
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

    def _atualizar_header():
        if _vista[0] == "lista":
            btn_novo = ft.Container(
                content=ft.Row([
                    ft.Icon("add_rounded", size=16, color=VERD),
                    ft.Text("+ Nova", size=13, color=VERD),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                border_radius=8, ink=True,
            )
            btn_novo.on_click = lambda e: _form_template()
            novo_cab = lay.criar_cabecalho(
                "Rotinas Diarias", voltar_fn,
                icone_titulo="calendar_today_rounded", cor_titulo=AZUL,
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
