# -*- coding: utf-8 -*-
# Prontuario | telas/tela_rotina_diaria.py
# Exibe a rotina base (template padrao) + log de excecoes/observacoes diarias.
import flet as ft
import logging
import threading
import json
from datetime import date, timedelta
from shared.layout import Layout
from dados.model_prontuario import (
    listar_templates, listar_momentos, listar_itens,
    listar_rotina_diario, listar_alteracoes_ativas,
    salvar_rotina_diario, excluir_rotina_diario,
    salvar_nutricao_item,
    registrar_agua, total_agua_dia, definir_total_agua_dia,
    meta_agua_template, salvar_meta_agua,
    listar_desafios_ativos, salvar_desafio, encerrar_desafio,
    normalizar_data as _norm_data,
)

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2  = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"; DIS  = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; LAR = "#F0883E"; VERM = "#DA3633"
ROXO = "#BC8CFF"; AMAR = "#D29922"

_TIPOS = {
    "suspensao":  ("block_rounded",        VERM, "Suspensao"),
    "reducao":    ("arrow_downward_rounded",AMAR, "Reducao"),
    "adicao":     ("add_circle_outline",   VERD, "Adicao"),
    "observacao": ("notes_rounded",        AZUL, "Observacao"),
    "sintoma":    ("warning_rounded",      LAR,  "Sintoma"),
}

_TIPOS_MOMENTO = {
    "despertar":  ("wb_sunny_rounded",       AMAR, "Despertar"),
    "refeicao":   ("restaurant_rounded",     VERD, "Refeicao"),
    "lanche":     ("lunch_dining_rounded",   LAR,  "Lanche"),
    "trabalho":   ("work_rounded",           AZUL, "Trabalho"),
    "atividade":  ("directions_run_rounded", LAR,  "Atividade"),
    "dormir":     ("bedtime_rounded",        ROXO, "Dormir"),
    "remedio":    ("medication_rounded",     AZUL, "Remedio"),
    "outro":      ("schedule_rounded",       SEC,  "Outro"),
}


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


def criar_tela_rotina_diaria(page: ft.Page, voltar_fn, navegar_fn=None) -> ft.Container:
    lay      = Layout(page)
    _montado = [False]
    _aba     = [0]   # 0=Rotina 1=Historico

    # ── Overlay helpers ────────────────────────────────────────────

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
                ft.Row([
                    ft.Container(expand=True),
                    btn_close,
                ], alignment=ft.MainAxisAlignment.END),
                *conteudo_col,
            ], spacing=12, scroll=ft.ScrollMode.AUTO,
               horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            bgcolor=CARD, border_radius=14, padding=ft.padding.all(20),
            border=ft.Border(top=ft.BorderSide(1, BD2), bottom=ft.BorderSide(1, BD2),
                             left=ft.BorderSide(1, BD2),  right=ft.BorderSide(1, BD2)),
            width=min(page.width - 32, 440) if page.width else 380,
        )
        ref[0] = ft.Container(
            content=ft.Column([painel],
                              alignment=ft.MainAxisAlignment.CENTER,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref[0].on_click = _fechar
        page.overlay.append(ref[0])
        try: page.update()
        except Exception: pass
        return ref

    def _confirmar(titulo, msg, fn_sim):
        ref = [None]
        def _fechar(e=None): _fechar_overlay(ref)
        def _ok(e): _fechar(); fn_sim()
        btn_c = ft.Container(
            content=ft.Text("Cancelar", size=13, color=TXT, weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=BD2, ink=True, expand=True,
            alignment=ft.Alignment(0, 0))
        btn_o = ft.Container(
            content=ft.Text("Excluir", size=13, color=VERM, weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{VERM}22", ink=True, expand=True,
            alignment=ft.Alignment(0, 0),
            border=ft.Border(top=ft.BorderSide(1, f"{VERM}66"),
                             bottom=ft.BorderSide(1, f"{VERM}66"),
                             left=ft.BorderSide(1, f"{VERM}66"),
                             right=ft.BorderSide(1, f"{VERM}66")))
        btn_c.on_click = _fechar
        btn_o.on_click = _ok
        dlg = ft.Container(
            content=ft.Column([
                ft.Text(titulo, size=15, color=TXT, weight=ft.FontWeight.W_700),
                ft.Container(height=4),
                ft.Text(msg, size=13, color=SEC),
                ft.Container(height=14),
                ft.Row([btn_c, ft.Container(width=8), btn_o]),
            ], spacing=0, tight=True),
            bgcolor=CARD, border_radius=14, padding=ft.padding.all(20),
            border=ft.Border(top=ft.BorderSide(1, BD2), bottom=ft.BorderSide(1, BD2),
                             left=ft.BorderSide(1, BD2),  right=ft.BorderSide(1, BD2)),
            width=min(page.width - 32, 360) if page.width else 340)
        ref[0] = ft.Container(
            content=ft.Column([dlg], alignment=ft.MainAxisAlignment.CENTER,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0))
        ref[0].on_click = _fechar
        page.overlay.append(ref[0])
        try: page.update()
        except Exception: pass

    # ── Formulario de registro ─────────────────────────────────────

    def _abrir_form(registro=None, item_id=None, item_nome=None):
        hoje = date.today().isoformat()
        r = registro or {}

        from shared.date_field import campo_data as _campo_data
        row_data, f_data = _campo_data(page, "Data", value=r.get("data", hoje), obrigatorio=True)
        f_item    = _campo("Item afetado (opcional)", r.get("item_nome", item_nome or ""),
                           hint="ex: Cafe com acucar, Caminhada...")
        f_desc    = _campo("Descricao *", r.get("descricao", ""),
                           hint="O que mudou ou foi observado", multiline=True, min_lines=2)
        f_motivo  = _campo("Motivo (opcional)", r.get("motivo", ""),
                           hint="ex: Glicose alta, Dor no joelho")
        row_fim, f_fim = _campo_data(page, "Ate quando (opcional)", value=r.get("data_fim", ""))

        tipo_sel  = [r.get("tipo", "observacao")]
        tipo_row  = ft.Row(spacing=6, wrap=True)

        def _rebuild_tipos():
            tipo_row.controls.clear()
            for chave, (icone, cor, label) in _TIPOS.items():
                ativo = chave == tipo_sel[0]
                btn = ft.Container(
                    content=ft.Row([
                        ft.Icon(icone, size=12, color=cor if ativo else SEC),
                        ft.Text(label, size=11,
                                color=cor if ativo else SEC,
                                weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.NORMAL),
                    ], spacing=4, tight=True),
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    border_radius=20, ink=True,
                    bgcolor=f"{cor}22" if ativo else BD,
                    border=ft.Border(
                        top=ft.BorderSide(1, cor if ativo else BD2),
                        bottom=ft.BorderSide(1, cor if ativo else BD2),
                        left=ft.BorderSide(1, cor if ativo else BD2),
                        right=ft.BorderSide(1, cor if ativo else BD2)),
                )
                def _sel(e, k=chave):
                    tipo_sel[0] = k
                    _rebuild_tipos()
                    try: page.update()
                    except Exception: pass
                btn.on_click = _sel
                tipo_row.controls.append(btn)

        _rebuild_tipos()

        def _salvar(e=None):
            if not f_desc.value.strip():
                f_desc.error_text = "Campo obrigatorio"
                try: page.update()
                except Exception: pass
                return
            f_desc.error_text = None
            dados = {
                "id":        r.get("id"),
                "data":      _norm_data(f_data.value.strip()) or hoje,
                "item_id":   item_id or r.get("item_id"),
                "item_nome": f_item.value.strip() or None,
                "tipo":      tipo_sel[0],
                "descricao": f_desc.value.strip(),
                "motivo":    f_motivo.value.strip() or None,
                "data_fim":  _norm_data(f_fim.value.strip()) or None,
            }
            salvar_rotina_diario(dados)
            _fechar_overlay(ref_ov)
            _rebuild()
            def _fazer_sync():
                try:
                    from backup.drive_backup import fazer_backup
                    fazer_backup(forcar=True)
                except Exception as ex:
                    log.warning("[rotina_diaria] sync erro: %s", ex)
            threading.Thread(target=_fazer_sync, daemon=True).start()

        btn_salvar = ft.Container(
            content=ft.Row([
                ft.Icon("check_rounded", size=14, color=BG),
                ft.Text("Salvar", size=13, color=BG, weight=ft.FontWeight.W_700),
            ], spacing=6, tight=True, alignment=ft.MainAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            border_radius=10, bgcolor=AZUL, ink=True, expand=True,
            alignment=ft.Alignment(0, 0))
        btn_salvar.on_click = _salvar

        titulo = "Editar registro" if r.get("id") else "Novo registro"
        ref_ov = _abrir_overlay([
            ft.Text(titulo, size=15, color=TXT, weight=ft.FontWeight.W_700),
            ft.Container(height=4),
            _label_sec("TIPO"),
            tipo_row,
            row_data,
            f_item,
            f_desc,
            f_motivo,
            row_fim,
            ft.Container(height=4),
            btn_salvar,
        ])

    # ── Formulario de item do template ────────────────────────────

    def _abrir_form_item(item: dict, momento_id: int):
        _TIPOS_ITEM = [
            ("alimento",  "restaurant_rounded",     VERD, "Alimento"),
            ("remedio",   "medication_rounded",     AZUL, "Remedio"),
            ("atividade", "directions_run_rounded", LAR,  "Atividade"),
        ]
        _FREQS = [
            ("diario",     "Diario"),
            ("2x_semana",  "2x/sem"),
            ("3x_semana",  "3x/sem"),
            ("semanal",    "Semanal"),
            ("eventual",   "Eventual"),
        ]

        tipo_sel = [item.get("tipo", "alimento")]
        freq_sel = [item.get("frequencia", "diario")]

        f_desc = _campo("Descricao *", item.get("descricao", ""),
                        hint="ex: Cafe com leite, Losartana 50mg")
        f_qty  = _campo("Quantidade", item.get("quantidade", ""),
                        hint="ex: 200", keyboard=ft.KeyboardType.NUMBER)
        f_unid = _campo("Unidade", item.get("unidade", ""),
                        hint="ex: ml, mg, comprimido")

        tipo_row = ft.Row(spacing=6, wrap=True)
        freq_row = ft.Row(spacing=6, wrap=True)

        def _rebuild_tipo_row():
            tipo_row.controls.clear()
            for chave, icone, cor, label in _TIPOS_ITEM:
                ativo = chave == tipo_sel[0]
                btn = ft.Container(
                    content=ft.Row([
                        ft.Icon(icone, size=12, color=cor if ativo else SEC),
                        ft.Text(label, size=11,
                                color=cor if ativo else SEC,
                                weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.NORMAL),
                    ], spacing=4, tight=True),
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    border_radius=20, ink=True,
                    bgcolor=ft.Colors.with_opacity(0.15, cor) if ativo else BD,
                    border=ft.Border(
                        top=ft.BorderSide(1, cor if ativo else BD2),
                        bottom=ft.BorderSide(1, cor if ativo else BD2),
                        left=ft.BorderSide(1, cor if ativo else BD2),
                        right=ft.BorderSide(1, cor if ativo else BD2)),
                )
                def _sel_tipo(e, k=chave):
                    tipo_sel[0] = k
                    _rebuild_tipo_row()
                    try: page.update()
                    except Exception: pass
                btn.on_click = _sel_tipo
                tipo_row.controls.append(btn)

        def _rebuild_freq_row():
            freq_row.controls.clear()
            for chave, label in _FREQS:
                ativo = chave == freq_sel[0]
                btn = ft.Container(
                    content=ft.Text(label, size=11,
                                    color=AZUL if ativo else SEC,
                                    weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.NORMAL),
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    border_radius=20, ink=True,
                    bgcolor=ft.Colors.with_opacity(0.15, AZUL) if ativo else BD,
                    border=ft.Border(
                        top=ft.BorderSide(1, AZUL if ativo else BD2),
                        bottom=ft.BorderSide(1, AZUL if ativo else BD2),
                        left=ft.BorderSide(1, AZUL if ativo else BD2),
                        right=ft.BorderSide(1, AZUL if ativo else BD2)),
                )
                def _sel_freq(e, k=chave):
                    freq_sel[0] = k
                    _rebuild_freq_row()
                    try: page.update()
                    except Exception: pass
                btn.on_click = _sel_freq
                freq_row.controls.append(btn)

        _rebuild_tipo_row()
        _rebuild_freq_row()

        def _salvar_item(e=None):
            desc = f_desc.value.strip()
            if not desc:
                f_desc.error_text = "Campo obrigatorio"
                try: page.update()
                except Exception: pass
                return
            f_desc.error_text = None
            salvar_item({
                "id":          item.get("id"),
                "momento_id":  momento_id,
                "tipo":        tipo_sel[0],
                "descricao":   desc,
                "quantidade":  f_qty.value.strip() or None,
                "unidade":     f_unid.value.strip() or None,
                "frequencia":  freq_sel[0],
                "ordem":       item.get("ordem", 0),
            })
            _fechar_overlay(ref_ov)
            _rebuild()
            import threading as _th
            def _sync():
                try:
                    from backup.drive_backup import fazer_backup
                    fazer_backup(forcar=True)
                except Exception: pass
            _th.Thread(target=_sync, daemon=True).start()

        btn_salvar_item = ft.Container(
            content=ft.Row([
                ft.Icon("check_rounded", size=14, color=BG),
                ft.Text("Salvar", size=13, color=BG, weight=ft.FontWeight.W_700),
            ], spacing=6, tight=True, alignment=ft.MainAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            border_radius=10, bgcolor=AZUL, ink=True, expand=True,
            alignment=ft.Alignment(0, 0))
        btn_salvar_item.on_click = _salvar_item

        titulo_form = "Editar item" if item.get("id") else "Novo item"
        ref_ov = _abrir_overlay([
            ft.Text(titulo_form, size=15, color=TXT, weight=ft.FontWeight.W_700),
            ft.Container(height=4),
            _label_sec("TIPO"),
            tipo_row,
            f_desc,
            ft.Row([f_qty, f_unid], spacing=8),
            _label_sec("FREQUENCIA"),
            freq_row,
            ft.Container(height=4),
            btn_salvar_item,
        ])

    # ── Aba Rotina (base + marcacao de alteracoes ativas) ──────────

    def _conteudo_rotina():
        controles = []

        # ── Widget de água ─────────────────────────────────────────
        controles.append(_mk_widget_agua())

        # ── Receitas + Nutricional ─────────────────────────────────
        controles.append(_mk_btn_receitas())

        # ── Separador Itens ────────────────────────────────────────
        controles.append(ft.Row([
            ft.Container(height=1, expand=True, bgcolor=BD2),
            ft.Text("  Itens  ", size=10, color=SEC, weight=ft.FontWeight.W_600),
            ft.Container(height=1, expand=True, bgcolor=BD2),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=0))

        templates = listar_templates(so_ativos=True)

        if not templates:
            btn_ir_rotinas = ft.Container(
                content=ft.Row([
                    ft.Icon("add_rounded", size=14, color=AZUL),
                    ft.Text("Configurar Rotina", size=13, color=AZUL,
                            weight=ft.FontWeight.W_600),
                ], spacing=6, tight=True),
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                border_radius=10,
                bgcolor=ft.Colors.with_opacity(0.08, AZUL),
                border=ft.border.all(1, ft.Colors.with_opacity(0.3, AZUL)),
                ink=True,
            )
            def _ir_rotinas(e):
                from telas.tela_rotinas import criar_tela_rotinas
                def _voltar_rot():
                    from telas.tela_rotina_diaria import criar_tela_rotina_diaria
                    page.controls.clear()
                    page.controls.append(
                        criar_tela_rotina_diaria(page, voltar_fn, navegar_fn))
                    try: page.update()
                    except Exception: pass
                page.controls.clear()
                page.controls.append(criar_tela_rotinas(page, _voltar_rot))
                try: page.update()
                except Exception: pass
            btn_ir_rotinas.on_click = _ir_rotinas
            controles.append(ft.Container(
                content=ft.Column([
                    ft.Icon("event_note_rounded", size=36, color=MUT),
                    ft.Text("Nenhuma rotina cadastrada.", size=13, color=SEC,
                            text_align="center"),
                    ft.Container(height=8),
                    btn_ir_rotinas,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=8, tight=True),
                padding=ft.padding.symmetric(vertical=40),
                alignment=ft.Alignment(0, 0),
            ))
        else:
            # ── Resumo nutricional único — somando todas as rotinas ────
            _nutr_aberto  = [False]
            nutr_body_geral = ft.Column(spacing=3, tight=True, visible=False)
            ico_exp_geral   = ft.Icon("expand_more_rounded", size=14, color=MUT)

            def _toggle_nutr_geral(e, nb=nutr_body_geral, ie=ico_exp_geral,
                                    ab=_nutr_aberto, tmpls=templates):
                ab[0] = not ab[0]
                if ab[0]:
                    nb.controls.clear()
                    from dados.model_prontuario import (
                        calcular_nutricao_momento as _cnm,
                        calcular_gasto_template   as _cgt,
                    )
                    # ingestão
                    tot = {}
                    for t in tmpls:
                        for m in listar_momentos(t["id"]):
                            n = _cnm(m["id"])
                            if n:
                                for k, v in n.items():
                                    if v: tot[k] = tot.get(k, 0.0) + float(v)
                    # gasto — peso do perfil
                    try:
                        from dados.model_prontuario import DB_PATH as _DB
                        import sqlite3 as _sq
                        with _sq.connect(_DB, timeout=5) as _c:
                            rp = _c.execute("SELECT peso FROM perfil_usuario LIMIT 1").fetchone()
                        peso = float(rp[0]) if rp and rp[0] else 80.0
                    except Exception:
                        peso = 80.0
                    gasto_total = sum(_cgt(t["id"], peso) for t in tmpls)

                    def _row(lbl, val, unid, cor=SEC, bold=False):
                        return ft.Row([
                            ft.Text(lbl, size=11, color=MUT, expand=True),
                            ft.Text(f"{val:.1f}" if val is not None else "—",
                                    size=11, color=cor,
                                    weight=ft.FontWeight.W_700 if bold else ft.FontWeight.NORMAL),
                            ft.Text(f" {unid}", size=10, color=MUT),
                        ], spacing=2)

                    ingestao = tot.get("kcal", 0.0) or 0.0
                    saldo    = ingestao - gasto_total
                    cor_saldo = VERD if saldo >= 0 else VERM

                    nb.controls += [
                        # bloco ingestão
                        ft.Container(
                            content=ft.Text("INGESTÃO", size=9, color=VERD,
                                            weight=ft.FontWeight.W_700),
                            padding=ft.padding.only(top=4)),
                        _row("Energia",      ingestao,              "kcal", LAR,  True),
                        _row("Carboidratos", tot.get("carboidratos"), "g"),
                        _row("Proteínas",    tot.get("proteinas"),   "g",  VERD, True),
                        _row("Gorduras",     tot.get("gorduras"),    "g"),
                        _row("Fibras",       tot.get("fibras"),      "g"),
                        _row("Sódio",        tot.get("sodio"),       "mg"),
                        ft.Divider(height=1, color=BD2),
                        # bloco gasto
                        ft.Container(
                            content=ft.Text("GASTO ESTIMADO", size=9, color=VERM,
                                            weight=ft.FontWeight.W_700),
                            padding=ft.padding.only(top=2)),
                        _row("Atividades e trabalho", gasto_total, "kcal", VERM, True),
                        ft.Divider(height=1, color=BD2),
                        # saldo
                        ft.Container(
                            content=ft.Text("SALDO DO DIA", size=9, color=cor_saldo,
                                            weight=ft.FontWeight.W_700),
                            padding=ft.padding.only(top=2)),
                        _row("Ingestão − Gasto", saldo, "kcal", cor_saldo, True),
                    ] if tot else [
                        ft.Text("Sem dados nutricionais ainda.", size=11, color=MUT),
                    ]
                nb.visible = ab[0]
                ie.name = "expand_less_rounded" if ab[0] else "expand_more_rounded"
                try: page.update()
                except Exception: pass

            btn_nutr_geral = ft.Container(
                content=ft.Row([
                    ft.Icon("local_fire_department_rounded", size=13, color=LAR),
                    ft.Text("Resumo nutricional", size=12, color=LAR,
                            weight=ft.FontWeight.W_600, expand=True),
                    ico_exp_geral,
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border_radius=8, ink=True,
                bgcolor=ft.Colors.with_opacity(0.08, LAR),
                border=ft.Border(
                    top=ft.BorderSide(1, ft.Colors.with_opacity(0.3, LAR)),
                    bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.3, LAR)),
                    left=ft.BorderSide(3, LAR),
                    right=ft.BorderSide(1, ft.Colors.with_opacity(0.3, LAR))),
            )
            btn_nutr_geral.on_click = _toggle_nutr_geral

            for tmpl in templates:
                cor_t  = tmpl.get("cor", AZUL)
                nome_t = tmpl.get("nome", "Rotina")
                hora_t = tmpl.get("horario") or ""

                def _abrir_overlay_rotina(e, t=tmpl):
                    from telas.tela_rotinas import _criar_overlay_form_template
                    _criar_overlay_form_template(page, t, on_salvo=_rebuild)

                def _confirmar_delete_tmpl(e, t=tmpl):
                    ref_c = [None]
                    def _fechar_c(e2=None):
                        if ref_c[0] in page.overlay:
                            page.overlay.remove(ref_c[0])
                        try: page.update()
                        except Exception: pass
                    def _ok_c(e2=None):
                        _fechar_c()
                        from dados.model_prontuario import excluir_template
                        excluir_template(t["id"])
                        _rebuild()
                        def _bkp():
                            try:
                                from backup.drive_backup import fazer_backup
                                fazer_backup(forcar=True)
                            except Exception: pass
                        threading.Thread(target=_bkp, daemon=True).start()
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
                    btn_c.on_click = _fechar_c
                    btn_o.on_click = _ok_c
                    ref_c[0] = ft.Container(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text("Excluir rotina?", size=15, color=TXT,
                                        weight=ft.FontWeight.W_700,
                                        text_align=ft.TextAlign.CENTER),
                                ft.Container(height=4),
                                ft.Text(f"'{t['nome']}' e todos os seus momentos e itens serao excluidos.",
                                        size=12, color=SEC, text_align=ft.TextAlign.CENTER),
                                ft.Container(height=16),
                                ft.Row([btn_c, ft.Container(width=8), btn_o]),
                            ], spacing=0, tight=True,
                               horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            bgcolor=CARD, border_radius=14, padding=ft.padding.all(20),
                            width=min((page.width or 360) - 32, 320)),
                        bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0))
                    ref_c[0].on_click = _fechar_c
                    page.overlay.append(ref_c[0])
                    try: page.update()
                    except Exception: pass

                momentos = listar_momentos(tmpl["id"])

                # horário: usa horario simples OU inicio–fim
                hi = tmpl.get("hora_inicio") or ""
                hf = tmpl.get("hora_fim") or ""
                if hi and hf:
                    hora_label = f"{hi}–{hf}"
                elif hora_t:
                    hora_label = hora_t
                else:
                    hora_label = ""

                card_t = ft.Container(
                    content=ft.Row([
                        ft.Icon(tmpl.get("icone", "today_rounded"), size=16, color=cor_t),
                        ft.Column([
                            ft.Text(nome_t, size=13, color=cor_t,
                                    weight=ft.FontWeight.W_700),
                            ft.Text(hora_label, size=10, color=MUT,
                                    visible=bool(hora_label)),
                        ], spacing=1, tight=True, expand=True),
                        ft.Container(
                            content=ft.Icon("edit_rounded", size=13, color=MUT),
                            padding=ft.padding.all(4), border_radius=6, ink=True,
                            on_click=_abrir_overlay_rotina,
                        ),
                        ft.Container(
                            content=ft.Icon("delete_outline_rounded", size=13, color=VERM),
                            padding=ft.padding.all(4), border_radius=6, ink=True,
                            on_click=_confirmar_delete_tmpl,
                        ),
                        ft.Icon("chevron_right_rounded", size=16, color=MUT),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(horizontal=12, vertical=12),
                    border_radius=10, bgcolor=CARD, ink=True,
                    border=ft.Border(
                        top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                        left=ft.BorderSide(3, cor_t), right=ft.BorderSide(1, BD)),
                )
                card_t.on_click = _abrir_overlay_rotina

                controles.append(card_t)

        return controles

    # ── Aba Historico ──────────────────────────────────────────────

    def _conteudo_historico():
        registros = listar_rotina_diario(limite=90)
        controles = []

        # ── Desafios ativos ────────────────────────────────────────
        controles.extend(_mk_widget_desafios())
        if not listar_desafios_ativos():
            btn_desafio = ft.Container(
                content=ft.Row([
                    ft.Icon("flag_rounded", size=13, color=ROXO),
                    ft.Text("Iniciar desafio de saude", size=12, color=ROXO),
                ], spacing=6, tight=True),
                padding=ft.padding.symmetric(horizontal=14, vertical=9),
                border_radius=10, ink=True,
                border=ft.Border(
                    top=ft.BorderSide(1, ft.Colors.with_opacity(0.35, ROXO)),
                    bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.35, ROXO)),
                    left=ft.BorderSide(1, ft.Colors.with_opacity(0.35, ROXO)),
                    right=ft.BorderSide(1, ft.Colors.with_opacity(0.35, ROXO))),
            )
            btn_desafio.on_click = _abrir_form_desafio
            controles.append(btn_desafio)

        # ── Botao nova observacao ──────────────────────────────────
        btn_obs = ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=14, color=AZUL),
                ft.Text("Adicionar observacao do dia", size=13, color=AZUL),
            ], spacing=6, tight=True),
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border_radius=10, ink=True,
            border=ft.Border(top=ft.BorderSide(1, f"{AZUL}55"),
                             bottom=ft.BorderSide(1, f"{AZUL}55"),
                             left=ft.BorderSide(1, f"{AZUL}55"),
                             right=ft.BorderSide(1, f"{AZUL}55")))
        btn_obs.on_click = lambda e: _abrir_form()
        controles.append(btn_obs)

        if not registros:
            controles.append(ft.Container(
                content=ft.Column([
                    ft.Icon("history_rounded", size=36, color=MUT),
                    ft.Text("Nenhum registro ainda.", size=13, color=SEC,
                            text_align="center"),
                    ft.Text("Use 'Alterar' em um item ou 'Adicionar observacao'.",
                            size=12, color=MUT, text_align="center"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=8, tight=True),
                padding=ft.padding.symmetric(vertical=40),
                alignment=ft.Alignment(0, 0),
            ))
        else:
            data_atual = None
            for r in registros:
                if r["data"] != data_atual:
                    data_atual = r["data"]
                    try:
                        d = date.fromisoformat(data_atual)
                        label_data = d.strftime("%d/%m/%Y")
                    except Exception:
                        label_data = data_atual
                    controles.append(ft.Container(
                        content=ft.Text(label_data, size=11, color=SEC,
                                        weight=ft.FontWeight.W_600),
                        padding=ft.padding.only(top=12, bottom=4),
                    ))

                icone_t, cor_t, label_t = _TIPOS.get(
                    r.get("tipo", "observacao"), ("notes_rounded", AZUL, "Observacao"))

                nome_item = r.get("item_nome") or r.get("item_descricao_fk") or ""
                titulo_card = label_t
                if nome_item:
                    titulo_card += f" — {nome_item}"

                linhas = [
                    ft.Row([
                        ft.Icon(icone_t, size=13, color=cor_t),
                        ft.Text(titulo_card, size=13, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True),
                    ], spacing=6),
                ]
                if r.get("descricao"):
                    linhas.append(ft.Text(r["descricao"], size=12, color=SEC))
                if r.get("motivo"):
                    linhas.append(ft.Row([
                        ft.Icon("info_outline_rounded", size=11, color=MUT),
                        ft.Text(r["motivo"], size=11, color=MUT),
                    ], spacing=4))
                if r.get("data_fim"):
                    try:
                        df = date.fromisoformat(r["data_fim"])
                        hoje = date.today()
                        if df >= hoje:
                            delta = (df - hoje).days
                            txt_fim = f"Ate {df.strftime('%d/%m')} ({delta}d restantes)"
                        else:
                            txt_fim = f"Encerrado em {df.strftime('%d/%m/%Y')}"
                    except Exception:
                        txt_fim = f"Ate {r['data_fim']}"
                    linhas.append(ft.Row([
                        ft.Icon("event_rounded", size=11, color=AMAR),
                        ft.Text(txt_fim, size=11, color=AMAR),
                    ], spacing=4))

                btn_edit = ft.Container(
                    content=ft.Icon("edit_rounded", size=14, color=SEC),
                    padding=6, ink=True, border_radius=6)
                btn_del  = ft.Container(
                    content=ft.Icon("delete_outline_rounded", size=14, color=VERM),
                    padding=6, ink=True, border_radius=6)
                _rid = r["id"]
                def _edit(e, reg=r): _abrir_form(registro=reg)
                def _del(e, rid=_rid):
                    _confirmar("Excluir registro?",
                               "O registro sera removido do historico.",
                               lambda: (excluir_rotina_diario(rid), _rebuild()))
                btn_edit.on_click = _edit
                btn_del.on_click  = _del

                controles.append(ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Column(linhas, spacing=4, tight=True, expand=True),
                            ft.Row([btn_edit, btn_del], spacing=0),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                           vertical_alignment=ft.CrossAxisAlignment.START),
                    ], spacing=0, tight=True),
                    padding=ft.padding.all(12),
                    border_radius=10, bgcolor=CARD,
                    border=ft.Border(
                        top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                        left=ft.BorderSide(3, cor_t), right=ft.BorderSide(1, BD)),
                ))

        # Botao Claudia
        btn_claudia = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text("C", size=12, color=BG, weight=ft.FontWeight.W_700),
                    width=22, height=22, border_radius=11, bgcolor=ROXO,
                    alignment=ft.Alignment(0, 0)),
                ft.Text("Analisar historico com Claudia", size=13, color=ROXO),
            ], spacing=8, tight=True),
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            border_radius=10, ink=True,
            border=ft.Border(top=ft.BorderSide(1, f"{ROXO}55"),
                             bottom=ft.BorderSide(1, f"{ROXO}55"),
                             left=ft.BorderSide(1, f"{ROXO}55"),
                             right=ft.BorderSide(1, f"{ROXO}55")))
        btn_claudia.on_click = _abrir_claudia
        controles.append(ft.Container(height=8))
        controles.append(btn_claudia)

        return controles

    # ── Abrir Claudia com contexto ─────────────────────────────────

    def _abrir_claudia(e=None):
        registros = listar_rotina_diario(limite=30)
        if not registros:
            prompt = ("Ainda nao tenho registros de alteracoes na minha rotina. "
                      "O que voce recomenda para comecar a monitorar meus habitos?")
        else:
            linhas = []
            for r in registros[:20]:
                _, _, label_t = _TIPOS.get(r.get("tipo", "observacao"),
                                           ("notes_rounded", AZUL, "Observacao"))
                item   = r.get("item_nome") or ""
                motivo = f" (motivo: {r['motivo']})" if r.get("motivo") else ""
                fim    = f", ate {r['data_fim']}" if r.get("data_fim") else ""
                linhas.append(f"- {r['data']} [{label_t}] {item}: {r['descricao']}{motivo}{fim}")
            prompt = (
                "Aqui estao as minhas ultimas alteracoes de rotina:\n\n"
                + "\n".join(linhas)
                + "\n\nAnalise esses registros considerando meus exames recentes "
                  "e me diga se ha padroes preocupantes, se as suspensoes foram "
                  "adequadas e o que mais devo ajustar para melhorar minha saude."
            )
        import importlib
        mod = importlib.import_module("telas.tela_claudia")
        def _voltar_rotina():
            page.controls.clear()
            page.controls.append(
                criar_tela_rotina_diaria(page, voltar_fn, navegar_fn))
            try: page.update()
            except Exception: pass
        nova = mod.criar_tela_claudia(page, _voltar_rotina, prompt_inicial=prompt)
        page.controls.clear()
        page.controls.append(nova)
        try: page.update()
        except Exception: pass

    # ── Resumo do Dia — overlay fullscreen ────────────────────────

    def _abrir_resumo_dia():
        ref_ov = [None]

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        from shared.layout import Layout as _Lay
        _lay2 = _Lay(page)
        cab = _lay2.criar_cabecalho(
            "Resumo do Dia", _fechar,
            icone_titulo="balance_rounded", cor_titulo=AZUL)

        area = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

        def _row(lbl, val, unid, cor=SEC, bold=False):
            return ft.Row([
                ft.Text(lbl, size=12, color=MUT, expand=True),
                ft.Text(f"{val:.0f}" if val is not None else "—",
                        size=12, color=cor,
                        weight=ft.FontWeight.W_700 if bold else ft.FontWeight.NORMAL),
                ft.Text(f" {unid}", size=11, color=MUT),
            ], spacing=2)

        templates = listar_templates(so_ativos=True)

        # ── Ingestão ──────────────────────────────────────────────
        from dados.model_prontuario import calcular_nutricao_momento as _cnm
        tot = {}
        for t in templates:
            for m in listar_momentos(t["id"]):
                n = _cnm(m["id"])
                if n:
                    for k, v in n.items():
                        if v: tot[k] = tot.get(k, 0.0) + float(v)

        kcal_in = tot.get("kcal") or 0.0

        area.controls.append(ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon("restaurant_rounded", size=14, color=VERD),
                    ft.Text("INGESTÃO", size=10, color=VERD,
                            weight=ft.FontWeight.W_700),
                ], spacing=6),
                ft.Divider(height=1, color=VERD),
                _row("Energia",      kcal_in,               "kcal", LAR,  True),
                _row("Carboidratos", tot.get("carboidratos"), "g"),
                _row("Proteínas",    tot.get("proteinas"),   "g",  VERD, True),
                _row("Gorduras",     tot.get("gorduras"),    "g"),
                _row("Fibras",       tot.get("fibras"),      "g"),
                _row("Sódio",        tot.get("sodio"),       "mg"),
            ], spacing=6, tight=True),
            bgcolor=CARD, border_radius=10,
            padding=ft.padding.all(14),
            border=ft.Border(
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                left=ft.BorderSide(3, VERD), right=ft.BorderSide(1, BD)),
        ))

        # ── Gasto ─────────────────────────────────────────────────
        from dados.model_prontuario import (
            calcular_gasto_item as _cgi,
            calcular_tmb        as _ctmb,
            DB_PATH             as _DB)
        import sqlite3 as _sq2

        # TMB — metabolismo basal
        tmb_dados = _ctmb()
        tmb       = tmb_dados.get("tmb") or 0.0
        peso      = tmb_dados.get("peso") or 80.0

        # bloco TMB
        if tmb_dados.get("completo"):
            tmb_txt = (
                f"Mifflin-St Jeor · {tmb_dados['sexo']} · "
                f"{tmb_dados['idade']} anos · "
                f"{peso:.0f}kg · {tmb_dados['altura']:.0f}cm"
            )
        else:
            tmb_txt = "Complete o perfil (peso, altura, data nasc., sexo)"

        area.controls.append(ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon("bedtime_rounded", size=14, color=SEC),
                    ft.Text("METABOLISMO BASAL (TMB)", size=10, color=SEC,
                            weight=ft.FontWeight.W_700),
                ], spacing=6),
                ft.Divider(height=1, color=BD2),
                ft.Row([
                    ft.Text("Gasto em repouso total", size=12, color=MUT,
                            expand=True),
                    ft.Text(f"−{tmb:.0f} kcal" if tmb else "—",
                            size=13, color=AMAR, weight=ft.FontWeight.W_700),
                ], spacing=4),
                ft.Text(tmb_txt, size=10, color=MUT),
                ft.Text("Energia minima para respirar, circulacao e funcoes vitais.",
                        size=10, color=MUT),
            ], spacing=6, tight=True),
            bgcolor=CARD, border_radius=10,
            padding=ft.padding.all(14),
            border=ft.Border(
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                left=ft.BorderSide(3, AMAR), right=ft.BorderSide(1, BD)),
        ))

        # gasto por atividade
        _TIPOS_GASTO = {"exercicio", "trabalho", "estudo"}
        linhas_gasto = []
        kcal_ativ = 0.0
        for t in templates:
            if t.get("tipo") not in _TIPOS_GASTO: continue
            hi = t.get("hora_inicio") or ""
            hf = t.get("hora_fim")    or ""
            if not (hi and hf): continue
            eh_fis = t.get("tipo") == "exercicio" or bool(t.get("intensidade_fisica"))
            r = _cgi(hi, hf,
                     t.get("intensidade_fisica") if     eh_fis else None,
                     t.get("intensidade_mental") if not eh_fis else None,
                     peso)
            if not r: continue
            kcal_ativ += r["kcal_gasto"]
            h2 = r["duracao_min"] // 60; m2 = r["duracao_min"] % 60
            dur = f"{h2}h{m2:02d}min" if h2 else f"{m2}min"
            linhas_gasto.append(ft.Row([
                ft.Icon("local_fire_department_rounded", size=12, color=VERM),
                ft.Text(t["nome"], size=12, color=TXT, expand=True),
                ft.Text(f"{hi}–{hf}  {dur}", size=10, color=MUT),
                ft.Text(f"−{r['kcal_gasto']:.0f} kcal", size=12,
                        color=VERM, weight=ft.FontWeight.W_600),
            ], spacing=6))

        kcal_out = tmb + kcal_ativ  # gasto total = TMB + atividades

        gasto_col = ft.Column([
            ft.Row([
                ft.Icon("directions_run_rounded", size=14, color=VERM),
                ft.Text("GASTO POR ATIVIDADE", size=10, color=VERM,
                        weight=ft.FontWeight.W_700),
            ], spacing=6),
            ft.Divider(height=1, color=VERM),
            *(linhas_gasto if linhas_gasto else
              [ft.Text("Nenhuma atividade com horario definido.",
                       size=11, color=MUT)]),
            ft.Divider(height=1, color=BD2),
            _row("Atividades", kcal_ativ, "kcal", VERM, True),
            _row("TMB (basal)", tmb, "kcal", AMAR, False),
            _row("Gasto total do dia", kcal_out, "kcal", VERM, True),
        ], spacing=6, tight=True)

        area.controls.append(ft.Container(
            content=gasto_col, bgcolor=CARD, border_radius=10,
            padding=ft.padding.all(14),
            border=ft.Border(
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                left=ft.BorderSide(3, VERM), right=ft.BorderSide(1, BD)),
        ))

        # ── Saldo ─────────────────────────────────────────────────
        saldo     = kcal_in - kcal_out
        cor_s     = VERD if saldo >= 0 else VERM
        sinal     = "+" if saldo >= 0 else ""
        icon_s    = "trending_up_rounded" if saldo >= 0 else "trending_down_rounded"

        area.controls.append(ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon("balance_rounded", size=14, color=AZUL),
                    ft.Text("SALDO DO DIA", size=10, color=AZUL,
                            weight=ft.FontWeight.W_700),
                ], spacing=6),
                ft.Divider(height=1, color=AZUL),
                ft.Row([
                    ft.Icon(icon_s, size=20, color=cor_s),
                    ft.Text(f"{sinal}{saldo:.0f} kcal", size=22, color=cor_s,
                            weight=ft.FontWeight.W_900),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([
                    ft.Text("Ingestão", size=11, color=MUT, expand=True),
                    ft.Text(f"+{kcal_in:.0f} kcal", size=11, color=LAR),
                ], spacing=4),
                ft.Row([
                    ft.Text("Gasto", size=11, color=MUT, expand=True),
                    ft.Text(f"−{kcal_out:.0f} kcal", size=11, color=VERM),
                ], spacing=4),
                ft.ProgressBar(
                    value=min(kcal_in / kcal_out, 1.0) if kcal_out > 0 else 1.0,
                    color=cor_s, bgcolor=BD2, height=6),
            ], spacing=8, tight=True),
            bgcolor=CARD, border_radius=10,
            padding=ft.padding.all(14),
            border=ft.Border(
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                left=ft.BorderSide(3, AZUL), right=ft.BorderSide(1, BD)),
        ))

        ref_ov[0] = ft.Container(
            content=ft.Column([
                ft.Container(height=_lay2.spacer_topo, bgcolor=BG),
                cab,
                ft.Container(
                    content=area, expand=True,
                    padding=ft.padding.symmetric(horizontal=16, vertical=8)),
            ], spacing=0, expand=True),
            bgcolor=BG, expand=True,
        )
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass

    # ── Botao Receitas ─────────────────────────────────────────────

    def _mk_btn_receitas() -> ft.Row:
        _img_rec   = "assets/receitas.png"
        _img_nutr  = "assets/nutricional.png"

        def _voltar_rotina():
            page.controls.clear()
            page.controls.append(
                criar_tela_rotina_diaria(page, voltar_fn, navegar_fn))
            try: page.update()
            except Exception: pass

        def _ir_receitas(e=None):
            from telas.tela_receitas import criar_tela_receitas
            page.controls.clear()
            page.controls.append(criar_tela_receitas(page, _voltar_rotina))
            try: page.update()
            except Exception: pass

        def _ir_nutricional(e=None):
            from telas.tela_nutricional import criar_tela_nutricional
            page.controls.clear()
            page.controls.append(criar_tela_nutricional(page, _voltar_rotina))
            try: page.update()
            except Exception: pass

        _img_res   = "assets/resumo.png"

        def _ir_resumo_dia(e=None):
            _abrir_resumo_dia()

        def _mk_card(img_path, icone, label, cor, on_click_fn, tooltip):
            if img_path:
                conteudo = ft.Image(
                    src=img_path,
                    fit=ft.ImageFit.COVER,
                    width=float("inf"),
                    expand=True,
                )
            else:
                conteudo = ft.Column([
                    ft.Icon(icone, size=20, color=cor),
                    ft.Text(label, size=11, color=cor, weight=ft.FontWeight.W_600,
                            text_align=ft.TextAlign.CENTER),
                ], alignment=ft.MainAxisAlignment.CENTER,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=4, tight=True)
            card = ft.Container(
                content=conteudo,
                height=76, expand=True,
                border_radius=10,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                bgcolor=CARD,
                border=ft.Border(
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    left=ft.BorderSide(3, cor), right=ft.BorderSide(1, BD),
                ),
                tooltip=tooltip,
                ink=True,
            )
            card.on_click = on_click_fn
            return card

        return ft.Row([
            _mk_card(_img_rec,  "menu_book_rounded",    "Receitas",    LAR,  _ir_receitas,    "Minhas Receitas"),
            _mk_card(_img_nutr, "local_dining_rounded", "Nutricional", VERD, _ir_nutricional, "Tabela Nutricional"),
            _mk_card(_img_res,  "balance_rounded",      "Resumo",      AZUL, _ir_resumo_dia,  "Ingestao, Gasto e Saldo do Dia"),
        ], spacing=8)

    # ── Widget de água ──────────────────────────────────────────────

    _agua_ref      = {"total": 0, "meta": 2500, "txt": None, "barra": None, "pct": None}
    _tf_agua_livre = ft.Ref()
    _agua_editando = [False]
    _row_agua_input = ft.Ref()

    def _mk_widget_agua() -> ft.Container:
        meta  = meta_agua_template()
        total = total_agua_dia()
        _agua_ref["total"] = total
        _agua_ref["meta"]  = meta
        pct   = min(total / meta, 1.0) if meta > 0 else 0.0
        cor   = VERD if pct >= 1.0 else (AZUL if pct >= 0.6 else (AMAR if pct >= 0.3 else VERM))

        txt_total = ft.Text(f"{total} ml", size=15, color=cor, weight=ft.FontWeight.W_900)
        txt_meta  = ft.Text(f"/ {meta} ml", size=11, color=SEC)
        txt_pct   = ft.Text(f"{int(pct*100)}%", size=10, color=cor)
        _agua_ref["txt"]  = txt_total
        _agua_ref["pct"]  = txt_pct

        barra_inner = ft.Container(
            width=0,
            height=6, border_radius=3, bgcolor=cor,
        )
        barra_outer = ft.Container(
            content=barra_inner,
            height=6, border_radius=3,
            bgcolor=BD2, expand=True,
        )
        _agua_ref["barra"] = (barra_inner, barra_outer, cor)

        btn_meta = ft.Container(
            content=ft.Icon("settings_rounded", size=13, color=MUT),
            padding=ft.padding.all(6), border_radius=6, ink=True,
        )
        btn_meta.on_click = _abrir_form_meta_agua

        _ico_edit = ft.Icon("edit_rounded", size=13, color=AZUL)
        btn_edit = ft.Container(
            content=_ico_edit,
            padding=ft.padding.all(6), border_radius=6, ink=True,
            tooltip="Registrar quantidade",
        )

        row_input = ft.Row([
            ft.TextField(
                label="Total de agua hoje (ml)",
                keyboard_type=ft.KeyboardType.NUMBER,
                bgcolor=CARD, border_color=BD2,
                focused_border_color=AZUL,
                label_style=ft.TextStyle(color=SEC, size=10),
                text_style=ft.TextStyle(color=TXT, size=13),
                border_radius=8, expand=True,
                height=44,
                content_padding=ft.padding.symmetric(
                    horizontal=10, vertical=6),
                ref=_tf_agua_livre,
            ),
            ft.Container(
                content=ft.Icon("check_rounded", size=16, color=VERD),
                width=44, height=44,
                border_radius=8,
                bgcolor=ft.Colors.with_opacity(0.10, VERD),
                border=ft.border.all(
                    1, ft.Colors.with_opacity(0.30, VERD)),
                alignment=ft.alignment.Alignment(0, 0),
                ink=True,
                on_click=lambda e: _registrar_agua_livre(),
            ),
        ], spacing=8, visible=_agua_editando[0], ref=_row_agua_input)

        def _toggle_edit(e=None):
            _agua_editando[0] = not _agua_editando[0]
            row_input.visible = _agua_editando[0]
            _ico_edit.name = "keyboard_arrow_up_rounded" if _agua_editando[0] \
                             else "edit_rounded"
            # pre-preenche com o total atual ao abrir
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
                    ft.Text("ÁGUA DO DIA", size=10, color=AZUL,
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

    def _registrar_agua(ml: int):
        registrar_agua(ml)
        _agua_ref["total"] += ml
        total = _agua_ref["total"]
        meta  = _agua_ref["meta"]
        pct   = min(total / meta, 1.0) if meta > 0 else 0.0
        cor   = VERD if pct >= 1.0 else (AZUL if pct >= 0.6 else (AMAR if pct >= 0.3 else VERM))
        if _agua_ref["txt"]:
            _agua_ref["txt"].value = f"{total} ml"
            _agua_ref["txt"].color = cor
        if _agua_ref["pct"]:
            _agua_ref["pct"].value = f"{int(pct*100)}%"
            _agua_ref["pct"].color = cor
        if _agua_ref["barra"]:
            inner, outer, _ = _agua_ref["barra"]
            inner.bgcolor = cor
            _agua_ref["barra"] = (inner, outer, cor)
            # atualiza largura proporcional via expand trick
            inner.width = None
            inner.expand = pct
            outer.content = inner
        try: page.update()
        except Exception: pass

    def _registrar_agua_livre():
        import threading
        try:
            tf = _tf_agua_livre.current
            if not tf: return
            val = (tf.value or "").strip()
            if not val: return
            ml = int(float(val))
            if ml < 0: return
            tf.value = ""
            # recolhe o campo
            _agua_editando[0] = False
            row = _row_agua_input.current
            if row: row.visible = False
            try: page.update()
            except Exception: pass
            # substitui o total do dia pelo valor informado
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
            # sync Drive
            def _sync():
                try:
                    from backup.drive_backup import fazer_backup
                    fazer_backup(forcar=True)
                except Exception: pass
            threading.Thread(target=_sync, daemon=True).start()
        except (ValueError, TypeError):
            pass

    def _abrir_form_meta_agua(e=None):
        from dados.model_prontuario import carregar_perfil
        perfil   = carregar_perfil() or {}
        peso_db  = perfil.get("peso") or 0

        # metodo_sel: "peso35" | "peso40" | "manual"
        metodo_sel = ["peso35"]
        tf_manual  = ft.TextField(
            label="Meta manual (ml)",
            value=str(_agua_ref["meta"]),
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, keyboard_type=ft.KeyboardType.NUMBER,
            visible=False,
        )
        tf_peso = ft.TextField(
            label="Peso (kg)",
            value=str(int(peso_db)) if peso_db else "",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, keyboard_type=ft.KeyboardType.NUMBER,
        )
        txt_resultado = ft.Text("", size=13, color=AZUL, weight=ft.FontWeight.W_700)

        _METODOS = [
            ("peso35", "35 ml/kg",    "Recomendacao padrao OMS"),
            ("peso40", "40 ml/kg",    "Para atividade fisica intensa"),
            ("manual", "Definir",     "Valor manual"),
        ]
        metodos_col = ft.Column(spacing=6)

        def _calcular():
            try:
                p = float((tf_peso.value or "").strip())
            except Exception:
                p = 0
            if metodo_sel[0] == "peso35":
                v = int(p * 35)
            elif metodo_sel[0] == "peso40":
                v = int(p * 40)
            else:
                try: v = int((tf_manual.value or "").strip())
                except Exception: v = 0
            if v > 0:
                txt_resultado.value = f"Meta: {v} ml/dia"
            else:
                txt_resultado.value = ""
            try: page.update()
            except Exception: pass
            return v

        def _rebuild_metodos():
            metodos_col.controls.clear()
            for chave, label, desc in _METODOS:
                ativo = chave == metodo_sel[0]
                btn = ft.Container(
                    content=ft.Row([
                        ft.Text(label, size=12, color=AZUL if ativo else TXT,
                                weight=ft.FontWeight.W_700 if ativo else ft.FontWeight.NORMAL,
                                expand=True),
                        ft.Text(desc, size=10, color=SEC),
                    ], spacing=8),
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    border_radius=8, ink=True,
                    bgcolor=ft.Colors.with_opacity(0.12, AZUL) if ativo else BD,
                    border=ft.Border(
                        top=ft.BorderSide(1, AZUL if ativo else BD2),
                        bottom=ft.BorderSide(1, AZUL if ativo else BD2),
                        left=ft.BorderSide(2, AZUL if ativo else BD2),
                        right=ft.BorderSide(1, AZUL if ativo else BD2)),
                )
                def _sel(e, k=chave):
                    metodo_sel[0] = k
                    tf_manual.visible = k == "manual"
                    tf_peso.visible   = k != "manual"
                    _rebuild_metodos()
                    _calcular()
                btn.on_click = _sel
                metodos_col.controls.append(btn)

        _rebuild_metodos()
        tf_peso.on_change    = lambda e: _calcular()
        tf_manual.on_change  = lambda e: _calcular()
        _calcular()

        ref_ov = [None]
        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        def _salvar(e=None):
            v = _calcular()
            if v > 0:
                salvar_meta_agua(v)
                _agua_ref["meta"] = v
            _fechar()
            _rebuild()

        btn_ok = ft.Container(
            content=ft.Text("Salvar", size=13, color=VERD, weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            border_radius=8, bgcolor=ft.Colors.with_opacity(0.13, VERD),
            ink=True, expand=True, alignment=ft.Alignment(0, 0))
        btn_ok.on_click = _salvar

        btn_fechar = ft.Container(
            content=ft.Icon("close_rounded", size=16, color=SEC),
            padding=6, ink=True, border_radius=6)
        btn_fechar.on_click = _fechar

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("water_drop_rounded", size=15, color=AZUL),
                        ft.Text("Meta de Agua", size=14, color=TXT,
                                weight=ft.FontWeight.W_700, expand=True),
                        btn_fechar,
                    ], spacing=8),
                    ft.Container(height=4),
                    _label_sec("METODO DE CALCULO"),
                    metodos_col,
                    tf_peso,
                    tf_manual,
                    txt_resultado,
                    ft.Container(height=4),
                    btn_ok,
                ], spacing=8, tight=True),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20),
                width=min(page.width - 32, 380) if page.width else 340,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass

    # ── Desafios de suspensão ───────────────────────────────────────

    def _mk_widget_desafios() -> list:
        desafios = listar_desafios_ativos()
        if not desafios:
            return []
        controles = []
        _CORES_TIPO = {
            "suspensao": VERM,
            "reducao":   AMAR,
            "adicao":    VERD,
            "pratica":   AZUL,
        }
        chips = []
        for d in desafios:
            cor_d = _CORES_TIPO.get(d.get("tipo", "suspensao"), VERM)
            data_ini = d.get("data_inicio", "")
            try:
                from datetime import date as _date
                dias_str = f"dia {(_date.today() - _date.fromisoformat(data_ini[:10])).days + 1}"
            except Exception:
                dias_str = ""

            icone_tipo = {
                "suspensao": "block_rounded",
                "reducao":   "arrow_downward_rounded",
                "adicao":    "add_circle_outline",
                "pratica":   "fitness_center_rounded",
            }.get(d.get("tipo","suspensao"), "block_rounded")

            chip = ft.Container(
                content=ft.Row([
                    ft.Icon(icone_tipo, size=11, color=cor_d),
                    ft.Text(d["nome"], size=11, color=cor_d, weight=ft.FontWeight.W_600),
                    ft.Text(dias_str, size=10, color=ft.Colors.with_opacity(0.70, cor_d)),
                    ft.Icon("close_rounded", size=11, color=ft.Colors.with_opacity(0.60, cor_d)),
                ], spacing=4, tight=True),
                bgcolor=ft.Colors.with_opacity(0.13, cor_d),
                border_radius=20,
                padding=ft.padding.symmetric(horizontal=10, vertical=5),
                ink=True,
            )
            _did = d["id"]
            def _encerrar(e, did=_did):
                encerrar_desafio(did)
                _rebuild()
            chip.on_click = _encerrar
            chips.append(chip)

        btn_add_desafio = ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=12, color=ROXO),
                ft.Text("Novo desafio", size=11, color=ROXO),
            ], spacing=4, tight=True),
            bgcolor=ft.Colors.with_opacity(0.10, ROXO),
            border_radius=20,
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            ink=True,
        )
        btn_add_desafio.on_click = _abrir_form_desafio

        controles.append(ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon("flag_rounded", size=12, color=ROXO),
                    ft.Text("DESAFIOS ATIVOS", size=10, color=ROXO,
                            weight=ft.FontWeight.W_700),
                ], spacing=6),
                ft.Container(height=4),
                ft.Row([*chips, btn_add_desafio], spacing=6, wrap=True),
            ], spacing=0),
            bgcolor=CARD, border_radius=10,
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border=ft.Border(
                left=ft.BorderSide(3, ROXO),
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                right=ft.BorderSide(1, BD)),
        ))
        return controles

    def _abrir_form_desafio(e=None):
        ref_ov = [None]
        tipo_sel = ["suspensao"]
        _TIPOS_DESAFIO = [
            ("suspensao", "block_rounded",            VERM, "Suspender"),
            ("reducao",   "arrow_downward_rounded",   AMAR, "Reduzir"),
            ("adicao",    "add_circle_outline",       VERD, "Adicionar"),
            ("pratica",   "fitness_center_rounded",   AZUL, "Praticar"),
        ]
        _MARCADORES_SUGERIDOS = [
            "Colesterol LDL", "Glicemia", "Ácido Úrico", "Triglicerídeos",
            "PCR", "Pressão Arterial", "IMC", "Gordura Corporal",
        ]
        tf_nome = ft.TextField(
            label="O que suspender/reduzir/adicionar?",
            hint_text="Ex: Açúcar, Carne vermelha, Álcool, Café...",
            bgcolor=CARD, border_color=BD2, focused_border_color=ROXO,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, autofocus=True,
        )
        tf_motivo = ft.TextField(
            label="Para melhorar qual marcador? (opcional)",
            hint_text="Ex: Colesterol LDL, Glicemia...",
            bgcolor=CARD, border_color=BD2, focused_border_color=ROXO,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
        )
        tf_fim = ft.TextField(
            label="Até quando? (dd/mm/aaaa, opcional)",
            bgcolor=CARD, border_color=BD2, focused_border_color=ROXO,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
        )
        tipo_row = ft.Row(spacing=6, wrap=True)

        def _rebuild_tipos_desafio():
            tipo_row.controls.clear()
            for chave, icone, cor, label in _TIPOS_DESAFIO:
                ativo = chave == tipo_sel[0]
                btn = ft.Container(
                    content=ft.Row([
                        ft.Icon(icone, size=12, color=cor if ativo else SEC),
                        ft.Text(label, size=11, color=cor if ativo else SEC,
                                weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.NORMAL),
                    ], spacing=4, tight=True),
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    border_radius=20, ink=True,
                    bgcolor=ft.Colors.with_opacity(0.15, cor) if ativo else BD,
                    border=ft.Border(
                        top=ft.BorderSide(1, cor if ativo else BD2),
                        bottom=ft.BorderSide(1, cor if ativo else BD2),
                        left=ft.BorderSide(1, cor if ativo else BD2),
                        right=ft.BorderSide(1, cor if ativo else BD2)),
                )
                def _sel_tipo(e, k=chave):
                    tipo_sel[0] = k
                    _rebuild_tipos_desafio()
                    try: page.update()
                    except Exception: pass
                btn.on_click = _sel_tipo
                tipo_row.controls.append(btn)

        _rebuild_tipos_desafio()

        # Chips de marcadores sugeridos
        chips_marc = ft.Row(spacing=6, wrap=True)
        for m in _MARCADORES_SUGERIDOS:
            chip = ft.Container(
                content=ft.Text(m, size=10, color=SEC),
                bgcolor=BD, border_radius=14,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                ink=True,
            )
            def _sel_marc(e, _m=m):
                tf_motivo.value = _m
                try: page.update()
                except Exception: pass
            chip.on_click = _sel_marc
            chips_marc.controls.append(chip)

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        def _salvar(e):
            nome = (tf_nome.value or "").strip()
            if not nome:
                tf_nome.error_text = "Obrigatorio"
                try: page.update()
                except Exception: pass
                return
            from datetime import date as _date
            fim_str = None
            fim_raw = (tf_fim.value or "").strip()
            if fim_raw:
                for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        import datetime as _dt
                        fim_str = _dt.datetime.strptime(fim_raw, fmt).strftime("%Y-%m-%d")
                        break
                    except Exception: pass
            salvar_desafio({
                "nome":            nome,
                "tipo":            tipo_sel[0],
                "motivo_marcador": (tf_motivo.value or "").strip() or None,
                "data_inicio":     _date.today().isoformat(),
                "data_fim":        fim_str,
            })
            _fechar()
            _rebuild()

        btn_ok = ft.Container(
            content=ft.Text("Iniciar Desafio", size=13, color=ROXO,
                            weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            border_radius=8, bgcolor=ft.Colors.with_opacity(0.13, ROXO),
            ink=True, expand=True, alignment=ft.Alignment(0, 0))
        btn_ok.on_click = _salvar

        btn_fechar_desafio = ft.Container(
            content=ft.Icon("close_rounded", size=18, color=SEC),
            padding=ft.padding.all(6), border_radius=6, ink=True,
        )
        btn_fechar_desafio.on_click = _fechar

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("flag_rounded", size=16, color=ROXO),
                        ft.Text("Novo Desafio", size=15, color=TXT,
                                weight=ft.FontWeight.W_700, expand=True),
                        btn_fechar_desafio,
                    ], spacing=8,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(height=4),
                    _label_sec("TIPO"),
                    tipo_row,
                    tf_nome,
                    _label_sec("PARA BAIXAR QUAL MARCADOR?"),
                    chips_marc,
                    tf_motivo,
                    tf_fim,
                    ft.Container(height=4),
                    btn_ok,
                ], spacing=10, tight=True),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20), width=360,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass

    # ── Calcular nutrição via Claudia (background thread + pubsub) ─

    _calculando = [False]

    def _calcular_nutricao(mom_nome, itens_lista):
        if _calculando[0]:
            return
        _calculando[0] = True
        page.pubsub.send_all_on_topic("_nutricao_status", {"status": "calculando"})

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
                    f"Calcule os valores nutricionais aproximados de cada item de '{mom_nome}':\n"
                    + "\n".join(linhas)
                    + "\n\nRetorne SOMENTE JSON valido no formato:\n"
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
                page.pubsub.send_all_on_topic("_nutricao_status", {
                    "status": "ok", "itens_db": itens_lista, "dados": dados,
                })
            except SemCreditosError:
                page.pubsub.send_all_on_topic("_nutricao_status", {
                    "status": "erro",
                    "msg": (
                        "Sem creditos na API Claude.\n"
                        "Acesse console.anthropic.com/settings/billing\n"
                        "para adicionar fundos e tentar novamente."
                    ),
                })
            except Exception as ex:
                page.pubsub.send_all_on_topic("_nutricao_status", {
                    "status": "erro", "msg": str(ex),
                })
        threading.Thread(target=_run, daemon=True, name="NutricaoCalc").start()

    def _on_nutricao_status(topic, msg):
        if not isinstance(msg, dict): return
        _calculando[0] = False
        if msg["status"] == "ok":
            itens_db = msg["itens_db"]
            dados    = msg["dados"]
            for i, it_db in enumerate(itens_db):
                itens_resp = dados.get("itens", [])
                if i < len(itens_resp):
                    n = itens_resp[i]
                    salvar_nutricao_item(
                        it_db["id"],
                        n.get("calorias"), n.get("proteinas"),
                        n.get("vitaminas", ""),
                    )
            _rebuild()
        elif msg["status"] == "erro":
            print(f"[NUTRICAO] erro: {msg.get('msg')}", flush=True)
            _rebuild()
            return
        else:
            _rebuild()

    page.pubsub.subscribe_topic("_nutricao_status", _on_nutricao_status)

    def _card_nutricao(mom_nome, itens):
        total_cal  = sum(it.get("calorias")  or 0 for it in itens)
        total_prot = sum(it.get("proteinas") or 0 for it in itens)
        vits = sorted(set(
            v.strip()
            for it in itens
            for v in (it.get("vitaminas") or "").split(",")
            if v.strip()
        ))
        tem_dados = total_cal > 0 or total_prot > 0

        filhos = []
        if tem_dados:
            filhos.append(ft.Row([
                ft.Container(
                    content=ft.Row([
                        ft.Icon("local_fire_department_rounded", size=12, color=LAR),
                        ft.Text(f"{total_cal:.0f} kcal", size=11, color=LAR,
                                weight=ft.FontWeight.W_600),
                    ], spacing=3, tight=True),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=8, bgcolor=f"{LAR}18"),
                ft.Container(
                    content=ft.Row([
                        ft.Icon("fitness_center_rounded", size=12, color=VERD),
                        ft.Text(f"{total_prot:.1f}g prot", size=11, color=VERD,
                                weight=ft.FontWeight.W_600),
                    ], spacing=3, tight=True),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=8, bgcolor=f"{VERD}18"),
            ], spacing=6, wrap=True))
            if vits:
                filhos.append(ft.Row([
                    ft.Icon("medication_liquid_rounded", size=11, color=AZUL),
                    ft.Text("Vit: " + ", ".join(vits), size=11, color=AZUL),
                ], spacing=4))

        lbl_btn = "Recalcular com Claudia" if tem_dados else "Calcular com Claudia"
        cor_btn = ROXO
        btn = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text("C", size=10, color=BG, weight=ft.FontWeight.W_700),
                    width=18, height=18, border_radius=9, bgcolor=cor_btn,
                    alignment=ft.Alignment(0, 0)),
                ft.Text(
                    "Calculando…" if _calculando[0] else lbl_btn,
                    size=11, color=cor_btn),
            ], spacing=6, tight=True),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border_radius=8, ink=True,
            border=ft.Border(
                top=ft.BorderSide(1, f"{cor_btn}44"), bottom=ft.BorderSide(1, f"{cor_btn}44"),
                left=ft.BorderSide(1, f"{cor_btn}44"), right=ft.BorderSide(1, f"{cor_btn}44")),
        )
        def _click_calc(e, mn=mom_nome, il=itens):
            _calcular_nutricao(mn, il)
        btn.on_click = _click_calc
        filhos.append(btn)

        return ft.Container(
            content=ft.Column(filhos, spacing=6, tight=True),
            padding=ft.padding.only(left=8, top=8, right=8, bottom=4),
            border=ft.Border(top=ft.BorderSide(1, BD)),
            margin=ft.margin.only(top=6),
        )

    # ── Barra de abas ──────────────────────────────────────────────

    _ABAS = [
        (0, "list_alt_rounded",  "Rotina",   AZUL),
        (1, "history_rounded",   "Historico", ROXO),
    ]
    barra = ft.Row(spacing=0)
    corpo_abas = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    def _rebuild_barra():
        barra.controls.clear()
        for idx, icone, label, cor in _ABAS:
            ativo = idx == _aba[0]
            tab = ft.Container(
                content=ft.Column([
                    ft.Icon(icone, size=16, color=cor if ativo else SEC),
                    ft.Text(label, size=10,
                            color=cor if ativo else SEC,
                            weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.NORMAL),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=2, tight=True),
                expand=True,
                padding=ft.padding.symmetric(vertical=10),
                border=ft.Border(bottom=ft.BorderSide(2, cor if ativo else "#00000000")),
                ink=True,
            )
            def _click(e, i=idx): _trocar_aba(i)
            tab.on_click = _click
            barra.controls.append(tab)
        if _montado[0]:
            try: page.update()
            except Exception: pass

    def _trocar_aba(idx):
        _aba[0] = idx
        _rebuild_barra()
        _rebuild_corpo()

    def _rebuild_corpo():
        corpo_abas.controls.clear()
        if _aba[0] == 0:
            corpo_abas.controls.extend(_conteudo_rotina())
        else:
            corpo_abas.controls.extend(_conteudo_historico())
        if _montado[0]:
            try: page.update()
            except Exception: pass

    def _rebuild():
        _rebuild_barra()
        _rebuild_corpo()

    # Montar layout
    _rebuild_barra()
    _rebuild_corpo()

    barra_container = ft.Container(
        content=barra,
        border=ft.Border(bottom=ft.BorderSide(1, BD)))

    area_scroll = ft.Container(
        content=corpo_abas,
        expand=True,
        padding=ft.padding.symmetric(horizontal=16, vertical=8))

    def _nova_rotina(e=None):
        from telas.tela_rotinas import _criar_overlay_form_template
        # template vazio com dados mínimos para criar novo
        tmpl_vazio = {"id": None, "nome": "", "tipo": "alimentacao",
                      "horario": None, "padrao": 0, "cor": AZUL}
        _criar_overlay_form_template(page, tmpl_vazio, on_salvo=_rebuild)

    btn_novo_obs = ft.Container(
        content=ft.Row([
            ft.Icon("add_rounded", size=16, color=AZUL),
            ft.Text("Nova", size=13, color=AZUL),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        border_radius=8, ink=True,
    )
    btn_novo_obs.on_click = _nova_rotina

    cabecalho = lay.criar_cabecalho(
        "Rotina Diaria", voltar_fn,
        icone_titulo="today_rounded", cor_titulo=AZUL,
        acoes=[btn_novo_obs])

    corpo = ft.Column([
        ft.Container(height=lay.spacer_topo, bgcolor=BG),
        cabecalho,
        barra_container,
        area_scroll,
    ], expand=True, spacing=0)

    _montado[0] = True
    return ft.Container(bgcolor=BG, expand=True,
                        content=lay.wrap(corpo))
