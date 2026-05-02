# -*- coding: utf-8 -*-
# Prontuario | telas/tela_rotinas.py
import flet as ft
import logging
from shared.layout import Layout
from dados.model_prontuario import (
    listar_templates, salvar_template, excluir_template,
    listar_momentos, salvar_momento, excluir_momento,
    listar_itens, salvar_item, excluir_item,
    listar_remedios,
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
    return ft.Text(txt, size=10, color=cor, weight=ft.FontWeight.W_600,
                   letter_spacing=1.0)


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
            max_height=page.height * 0.85 if page.height else 600,
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

    def _form_template(template=None):
        f_nome = _campo("Nome da rotina *", template["nome"] if template else "",
                        hint="ex: Dia de Trabalho, Final de Semana…")
        icone_sel = [template["icone"] if template else "today_rounded"]
        cor_sel   = [template["cor"] if template else "#58A6FF"]
        padrao    = [bool(template.get("padrao", False)) if template else False]

        row_icones = ft.Row(spacing=6, wrap=True)
        row_cores  = ft.Row(spacing=6, wrap=True)
        sw_padrao  = ft.Switch(
            label="Rotina padrao (aparece primeiro)",
            value=padrao[0], active_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=12),
        )

        def _rebuild_icones():
            row_icones.controls.clear()
            for ic in _ICONES_TEMPLATE:
                sel = ic == icone_sel[0]
                c = ft.Container(
                    content=ft.Icon(ic, size=20, color=cor_sel[0] if sel else SEC),
                    bgcolor=f"{cor_sel[0]}33" if sel else CARD,
                    border_radius=8, width=40, height=40,
                    alignment=ft.alignment.Alignment(0, 0),
                    border=ft.Border(
                        top=ft.BorderSide(1, cor_sel[0] if sel else BD),
                        bottom=ft.BorderSide(1, cor_sel[0] if sel else BD),
                        left=ft.BorderSide(1, cor_sel[0] if sel else BD),
                        right=ft.BorderSide(1, cor_sel[0] if sel else BD),
                    ),
                    ink=True,
                )
                def _sel_ic(e, i=ic):
                    icone_sel[0] = i; _rebuild_icones()
                    try: page.update()
                    except Exception: pass
                c.on_click = _sel_ic
                row_icones.controls.append(c)

        def _rebuild_cores():
            row_cores.controls.clear()
            for hex_c, _ in _CORES_TEMPLATE:
                sel = hex_c == cor_sel[0]
                c = ft.Container(
                    bgcolor=hex_c, border_radius=20, width=32, height=32,
                    border=ft.Border(
                        top=ft.BorderSide(2, TXT if sel else "#00000000"),
                        bottom=ft.BorderSide(2, TXT if sel else "#00000000"),
                        left=ft.BorderSide(2, TXT if sel else "#00000000"),
                        right=ft.BorderSide(2, TXT if sel else "#00000000"),
                    ),
                    ink=True,
                )
                def _sel_cor(e, h=hex_c):
                    cor_sel[0] = h; _rebuild_cores(); _rebuild_icones()
                    try: page.update()
                    except Exception: pass
                c.on_click = _sel_cor
                row_cores.controls.append(c)

        _rebuild_icones()
        _rebuild_cores()

        txt_err = ft.Text("", color=VERM, size=12)

        def _salvar(e):
            if not (f_nome.value or "").strip():
                txt_err.value = "Nome obrigatorio."; page.update(); return
            salvar_template({
                "id": template["id"] if template else None,
                "nome": f_nome.value.strip(),
                "icone": icone_sel[0],
                "cor": cor_sel[0],
                "padrao": sw_padrao.value,
                "ativo": 1,
            })
            _fechar_overlay(ref)
            _mostrar_lista()

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
            _label_sec("NOVA ROTINA" if not template else "EDITAR ROTINA"),
            ft.Container(height=8),
            f_nome,
            ft.Container(height=8),
            _label_sec("ICONE"),
            row_icones,
            ft.Container(height=8),
            _label_sec("COR"),
            row_cores,
            ft.Container(height=8),
            ft.Row([sw_padrao]),
            txt_err,
            ft.Container(height=12),
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
    # VISTA: LISTA DE TEMPLATES
    # ══════════════════════════════════════════════════════

    def _mostrar_lista():
        _vista[0] = "lista"
        templates = listar_templates()
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
            for t in templates:
                icone, cor = t.get("icone","today_rounded"), t.get("cor","#58A6FF")
                card = ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Icon(icone, size=22, color=cor),
                            bgcolor=f"{cor}22", border_radius=10, width=44, height=44,
                            alignment=ft.alignment.Alignment(0, 0),
                        ),
                        ft.Column([
                            ft.Row([
                                ft.Text(t["nome"], size=14, color=TXT, weight=ft.FontWeight.W_600),
                                ft.Container(
                                    content=ft.Text("padrao", size=8, color=cor, weight=ft.FontWeight.W_700),
                                    bgcolor=f"{cor}22", border_radius=4,
                                    padding=ft.padding.symmetric(horizontal=4, vertical=1),
                                ) if t.get("padrao") else ft.Container(),
                            ], spacing=6, tight=True),
                            ft.Text(f"{t.get('total_momentos',0)} momento(s)", size=11, color=SEC),
                        ], spacing=2, expand=True),
                        ft.Row([
                            _btn_icon("edit_rounded", SEC, lambda e, tt=t: _form_template(tt)),
                            _btn_icon("delete_outline_rounded", VERM, lambda e, tt=t: _confirmar_exclusao(
                                "Excluir rotina?",
                                f"'{tt['nome']}' e todos os seus momentos serao excluidos.",
                                lambda tid=tt["id"]: [excluir_template(tid), _mostrar_lista()],
                            )),
                        ], spacing=4),
                    ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD, border_radius=10, padding=ft.padding.all(12),
                    border=ft.Border(
                        top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                        left=ft.BorderSide(3, cor), right=ft.BorderSide(1, BD),
                    ),
                    ink=True,
                )
                card.on_click = lambda e, tt=t: _mostrar_detalhe(tt)
                area.controls.append(card)

        # Botao nova rotina
        btn_nova = ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=16, color=VERD),
                ft.Text("Nova Rotina", size=13, color=VERD),
            ], spacing=4, tight=True, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=f"{VERD}11", border_radius=10,
            padding=ft.padding.symmetric(vertical=14),
            border=ft.Border(
                top=ft.BorderSide(1, f"{VERD}44"), bottom=ft.BorderSide(1, f"{VERD}44"),
                left=ft.BorderSide(1, f"{VERD}44"), right=ft.BorderSide(1, f"{VERD}44"),
            ),
            ink=True,
        )
        btn_nova.on_click = lambda e: _form_template()
        area.controls.append(btn_nova)

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
            itens_col = ft.Column(spacing=3)
            for it in itens[:6]:
                ic_it = "restaurant_rounded" if it["tipo"]=="alimento" else (
                    "medication_rounded" if it["tipo"]=="remedio" else "directions_run_rounded")
                cor_it = VERD if it["tipo"]=="alimento" else (AZUL if it["tipo"]=="remedio" else LAR)
                linha = ft.Row([
                    ft.Icon(ic_it, size=12, color=cor_it),
                    ft.Text(it["descricao"], size=11, color=SEC, expand=True),
                    ft.Text(it.get("horario","") or "", size=10, color=MUT),
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
                        content=ft.Column([itens_col, btn_add_item], spacing=4),
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

        # Botao adicionar momento
        btn_add_momento = ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=16, color=cor_t),
                ft.Text("Adicionar Momento", size=13, color=cor_t),
            ], spacing=4, tight=True, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=f"{cor_t}11", border_radius=10,
            padding=ft.padding.symmetric(vertical=14),
            border=ft.Border(
                top=ft.BorderSide(1, f"{cor_t}44"), bottom=ft.BorderSide(1, f"{cor_t}44"),
                left=ft.BorderSide(1, f"{cor_t}44"), right=ft.BorderSide(1, f"{cor_t}44"),
            ),
            ink=True,
        )
        btn_add_momento.on_click = lambda e: _form_momento(template["id"])
        area.controls.append(btn_add_momento)

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
                    ft.Text("Nova", size=13, color=VERD),
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

    # Header inicial placeholder (sera substituido por _atualizar_header)
    cab_inicial = lay.criar_cabecalho(
        "Rotinas Diarias", voltar_fn,
        icone_titulo="calendar_today_rounded", cor_titulo=AZUL,
    )
    _cab_container.content = cab_inicial

    corpo = ft.Column([
        ft.Container(height=lay.spacer_topo, bgcolor=BG),
        _cab_container,
        ft.Container(
            content=area, padding=ft.padding.all(12), expand=True,
        ),
    ], expand=True, spacing=0)

    _montado[0] = True
    return ft.Container(bgcolor=BG, expand=True, content=lay.wrap(corpo))
