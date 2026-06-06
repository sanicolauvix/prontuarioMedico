# -*- coding: utf-8 -*-
# Prontuario | telas/tela_historico_clinico.py
import flet as ft
import sqlite3
import logging
import threading
from datetime import datetime
from shared.layout import Layout
from dados.model_prontuario import DB_PATH

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; AMAR = "#D29922"
VERM = "#F85149"; ROXO = "#BC8CFF"; LAR  = "#F0883E"

_TIPOS = {
    "alergia":          ("warning_rounded",            VERM, "Alergia / Risco"),
    "condicao_cronica": ("monitor_heart_rounded",      LAR,  "Condição Crônica"),
    "diagnostico":      ("medical_information_rounded",AZUL, "Diagnóstico"),
    "cirurgia":         ("healing_rounded",            ROXO, "Cirurgia"),
    "procedimento":     ("build_rounded",              AMAR, "Procedimento"),
    "internacao":       ("local_hospital_rounded",     VERM, "Internação"),
    "infancia":         ("child_care_rounded",         SEC,  "Infância"),
    "outro":            ("circle_rounded",             MUT,  "Outro"),
}
_ORDEM_TIPOS = ["alergia","condicao_cronica","diagnostico","cirurgia",
                "procedimento","internacao","infancia","outro"]


def _campo(label, valor="", multiline=False, min_lines=1, hint=None, largura=None):
    kw = dict(
        label=label, value=valor or "",
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, multiline=multiline, min_lines=min_lines,
    )
    if hint:
        kw["hint_text"] = hint
        kw["hint_style"] = ft.TextStyle(color=MUT, size=11)
    if largura:
        kw["width"] = largura
    else:
        kw["expand"] = True
    return ft.TextField(**kw)


def _listar_historico():
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            rows = conn.execute("""
                SELECT id, data_aprox, tipo, titulo, descricao,
                       local, medico, sequela, alerta
                FROM historico_medico
                ORDER BY
                    CASE tipo
                        WHEN 'alergia' THEN 0
                        WHEN 'condicao_cronica' THEN 1
                        ELSE 2
                    END,
                    data_aprox DESC
            """).fetchall()
        cols = ["id","data_aprox","tipo","titulo","descricao",
                "local","medico","sequela","alerta"]
        return [dict(zip(cols, r)) for r in rows]
    except Exception as ex:
        log.error("[HIST] listar: %s", ex)
        return []


def _salvar_historico(dados: dict) -> int:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            if dados.get("id"):
                conn.execute("""
                    UPDATE historico_medico SET
                        data_aprox=?, tipo=?, titulo=?, descricao=?,
                        local=?, medico=?, sequela=?, alerta=?
                    WHERE id=?
                """, (dados.get("data_aprox"), dados.get("tipo"),
                      dados.get("titulo"), dados.get("descricao"),
                      dados.get("local"), dados.get("medico"),
                      dados.get("sequela"), 1 if dados.get("alerta") else 0,
                      dados["id"]))
                return dados["id"]
            else:
                cur = conn.execute("""
                    INSERT INTO historico_medico
                        (data_aprox, tipo, titulo, descricao, local, medico,
                         sequela, alerta, fonte)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (dados.get("data_aprox"), dados.get("tipo","outro"),
                      dados.get("titulo"), dados.get("descricao"),
                      dados.get("local"), dados.get("medico"),
                      dados.get("sequela"), 1 if dados.get("alerta") else 0,
                      "usuario"))
                return cur.lastrowid
    except Exception as ex:
        log.error("[HIST] salvar: %s", ex)
        return 0


def _excluir_historico(hid: int):
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("DELETE FROM historico_medico WHERE id=?", (hid,))
    except Exception as ex:
        log.error("[HIST] excluir: %s", ex)


def criar_tela_historico_clinico(page: ft.Page, voltar_fn):
    lay      = Layout(page)
    _montado = [False]
    wrapper  = ft.Column(expand=True, spacing=0)

    # ── form edição ───────────────────────────────────────────────────────────

    def _abrir_form(evento=None):
        is_novo = evento is None

        f_titulo  = _campo("Título *", evento["titulo"] if evento else "")
        f_data    = _campo("Data / Período",
                           evento.get("data_aprox","") if evento else "",
                           hint="2024  /  ~1980s  /  12/03/2008", largura=170)
        f_local   = _campo("Local / Hospital",
                           evento.get("local","") if evento else "")
        f_medico  = _campo("Médico",
                           evento.get("medico","") if evento else "")
        f_desc    = _campo("Descrição detalhada",
                           evento.get("descricao","") if evento else "",
                           multiline=True, min_lines=3)
        f_sequela = _campo("Sequela / Resultado permanente",
                           evento.get("sequela","") if evento else "",
                           multiline=True, min_lines=2,
                           hint="consequência permanente ou relevante para consultas futuras")

        tipo_sel  = [evento.get("tipo","diagnostico") if evento else "diagnostico"]
        sw_alerta = ft.Checkbox(
            label="Marcar como Alerta Crítico",
            value=bool(evento.get("alerta")) if evento else False,
            active_color=VERM,
            label_style=ft.TextStyle(color=SEC, size=13))

        chips_tipo = ft.Row(wrap=True, spacing=6)

        def _rebuild_chips():
            chips_tipo.controls.clear()
            for t_key in _ORDEM_TIPOS:
                ico, cor, lbl = _TIPOS[t_key]
                sel = t_key == tipo_sel[0]
                def _sel(e, k=t_key):
                    tipo_sel[0] = k
                    _rebuild_chips()
                    try: page.update()
                    except Exception: pass
                chips_tipo.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Icon(ico, size=11, color=cor if sel else MUT),
                        ft.Text(lbl, size=10,
                                color=cor if sel else MUT,
                                weight=ft.FontWeight.W_600 if sel else ft.FontWeight.NORMAL),
                    ], spacing=4, tight=True),
                    bgcolor=ft.Colors.with_opacity(0.18 if sel else 0.05,
                                                    cor if sel else MUT),
                    border_radius=16,
                    padding=ft.padding.symmetric(horizontal=10, vertical=5),
                    border=ft.border.all(1, ft.Colors.with_opacity(
                        0.5 if sel else 0.15, cor if sel else MUT)),
                    ink=True, on_click=_sel,
                ))
        _rebuild_chips()

        txt_erro = ft.Text("", color=VERM, size=12)

        def _salvar(e):
            if not f_titulo.value.strip():
                txt_erro.value = "Título é obrigatório."
                try: page.update()
                except Exception: pass
                return
            _salvar_historico({
                "id":         evento["id"] if evento else None,
                "tipo":       tipo_sel[0],
                "titulo":     f_titulo.value.strip(),
                "data_aprox": f_data.value.strip() or None,
                "local":      f_local.value.strip() or None,
                "medico":     f_medico.value.strip() or None,
                "descricao":  f_desc.value.strip() or None,
                "sequela":    f_sequela.value.strip() or None,
                "alerta":     sw_alerta.value,
            })
            _mostrar_lista()
            threading.Thread(target=lambda: __import__(
                "backup.drive_backup", fromlist=["fazer_backup"]
            ).fazer_backup(forcar=True), daemon=True).start()

        def _excluir(e):
            if evento and evento.get("id"):
                _excluir_historico(evento["id"])
                _mostrar_lista()

        btn_voltar = ft.Container(
            content=ft.Row([ft.Icon("arrow_back_rounded", size=14),
                            ft.Text("Voltar", size=13)], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=8, vertical=8), ink=True)
        btn_voltar.on_click = lambda e: _mostrar_lista()

        btn_salvar = ft.Container(
            content=ft.Row([ft.Icon("save_rounded", size=14, color=BG),
                            ft.Text("Salvar", size=13, color=BG)],
                           spacing=4, tight=True),
            bgcolor=AZUL, border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=16, vertical=10))
        btn_salvar.on_click = _salvar

        excluir_row = []
        if evento:
            btn_exc = ft.Container(
                content=ft.Row([
                    ft.Icon("delete_outline_rounded", size=13, color=VERM),
                    ft.Text("Excluir evento", size=12, color=VERM),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=8), ink=True)
            btn_exc.on_click = _excluir
            excluir_row = [ft.Container(height=8), btn_exc]

        form = ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        btn_voltar,
                        ft.Row([
                            ft.Icon("history_rounded", size=18, color=AZUL),
                            ft.Text("Novo Evento" if is_novo else "Editar Evento",
                                    size=16, weight=ft.FontWeight.W_700, color=TXT),
                        ], spacing=8, tight=True),
                        ft.Container(expand=True),
                        btn_salvar,
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.padding.symmetric(horizontal=16, vertical=12),
                    border=ft.Border(bottom=ft.BorderSide(1, BD))),
                ft.Container(
                    content=ft.Column([
                        ft.Text("TIPO", size=10, color=MUT, weight=ft.FontWeight.W_700),
                        chips_tipo,
                        ft.Container(height=4),
                        f_titulo,
                        ft.Row([f_data, f_local], spacing=8),
                        f_medico,
                        f_desc,
                        f_sequela,
                        ft.Container(height=4),
                        sw_alerta,
                        txt_erro,
                        *excluir_row,
                    ], spacing=8, scroll=ft.ScrollMode.AUTO),
                    padding=ft.padding.all(16), expand=True),
            ], expand=True, spacing=0))

        wrapper.controls.clear()
        wrapper.controls.append(form)
        try: page.update()
        except Exception: pass

    # ── detalhe ───────────────────────────────────────────────────────────────

    def _abrir_detalhe(ev):
        ico, cor, lbl = _TIPOS.get(ev.get("tipo","outro"), _TIPOS["outro"])
        alerta = bool(ev.get("alerta"))
        cor_card = VERM if alerta else cor

        btn_editar = ft.Container(
            content=ft.Row([ft.Icon("edit_rounded", size=13, color=AZUL),
                            ft.Text("Editar", size=12, color=AZUL)],
                           spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_radius=8, ink=True,
            bgcolor=ft.Colors.with_opacity(0.10, AZUL))
        btn_editar.on_click = lambda e: _abrir_form(ev)

        campos = []

        if alerta:
            campos.append(ft.Container(
                content=ft.Row([
                    ft.Icon("warning_rounded", size=14, color=VERM),
                    ft.Text("ALERTA CRÍTICO — informar médico sempre",
                            size=12, color=VERM, weight=ft.FontWeight.W_700),
                ], spacing=8),
                bgcolor=ft.Colors.with_opacity(0.10, VERM),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border=ft.border.all(1, ft.Colors.with_opacity(0.4, VERM))))

        def _bloco(label, valor, cor_v=TXT):
            if not valor: return
            campos.append(ft.Container(
                content=ft.Column([
                    ft.Text(label, size=9, color=MUT, weight=ft.FontWeight.W_700),
                    ft.Container(height=2),
                    ft.Text(valor, size=12, color=cor_v),
                ], spacing=0),
                bgcolor=CARD, border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border=ft.border.all(1, BD2)))

        _bloco("TIPO", lbl, cor_card)
        _bloco("DATA / PERÍODO", ev.get("data_aprox"))
        _bloco("LOCAL / HOSPITAL", ev.get("local"))
        _bloco("MÉDICO", ev.get("medico"))
        _bloco("DESCRIÇÃO", ev.get("descricao"))
        if ev.get("sequela"):
            campos.append(ft.Container(
                content=ft.Column([
                    ft.Text("SEQUELA / RESULTADO", size=9, color=MUT,
                            weight=ft.FontWeight.W_700),
                    ft.Container(height=2),
                    ft.Text(ev["sequela"], size=12, color=LAR),
                ], spacing=0),
                bgcolor=ft.Colors.with_opacity(0.06, LAR),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border=ft.border.all(1, ft.Colors.with_opacity(0.3, LAR))))

        area_det = ft.Column(campos, spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

        cab_det = lay.criar_cabecalho(
            ev.get("titulo","")[:32], _mostrar_lista,
            icone_titulo="warning_rounded" if alerta else ico,
            cor_titulo=cor_card,
            acoes=[btn_editar])

        wrapper.controls.clear()
        wrapper.controls.append(ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Container(height=lay.spacer_topo, bgcolor=BG),
                cab_det,
                ft.Container(content=area_det,
                             padding=ft.padding.symmetric(horizontal=16, vertical=8),
                             expand=True),
            ], spacing=0, expand=True)))
        try: page.update()
        except Exception: pass

    # ── lista principal ───────────────────────────────────────────────────────

    def _mostrar_lista():
        eventos = _listar_historico()
        por_tipo: dict[str, list] = {t: [] for t in _ORDEM_TIPOS}
        for ev in eventos:
            t = ev.get("tipo") or "outro"
            por_tipo.setdefault(t, []).append(ev)

        area = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

        if not eventos:
            area.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("history_rounded", size=48, color=MUT),
                    ft.Text("Nenhum evento registrado.", color=SEC, size=13),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=40))

        for tipo in _ORDEM_TIPOS:
            itens = por_tipo.get(tipo, [])
            if not itens:
                continue
            ico, cor, lbl = _TIPOS[tipo]

            area.controls.append(ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(ico, size=12, color=cor),
                        bgcolor=ft.Colors.with_opacity(0.13, cor),
                        border_radius=6, width=24, height=24,
                        alignment=ft.alignment.Alignment(0, 0)),
                    ft.Text(lbl.upper(), size=10, color=cor,
                            weight=ft.FontWeight.W_700, expand=True),
                    ft.Text(str(len(itens)), size=10, color=MUT),
                ], spacing=8),
                padding=ft.padding.only(top=12, bottom=4)))

            for ev in itens:
                alerta = bool(ev.get("alerta"))
                cor_ev = VERM if alerta else cor
                card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Icon(
                                    "warning_rounded" if alerta else ico,
                                    size=13, color=cor_ev),
                                bgcolor=ft.Colors.with_opacity(0.12, cor_ev),
                                border_radius=6, width=26, height=26,
                                alignment=ft.alignment.Alignment(0, 0)),
                            ft.Column([
                                ft.Text(ev.get("titulo",""), size=13, color=TXT,
                                        weight=ft.FontWeight.W_600,
                                        no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(ev.get("data_aprox") or "—",
                                        size=10, color=MUT),
                            ], spacing=1, expand=True),
                            ft.Icon("chevron_right_rounded", size=13, color=MUT),
                        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Text(ev.get("sequela",""), size=10, color=LAR,
                                italic=True,
                                no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
                                ) if ev.get("sequela") else ft.Container(height=0),
                    ], spacing=4, tight=True),
                    bgcolor=CARD, border_radius=10, ink=True,
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    border=ft.border.all(1,
                        ft.Colors.with_opacity(0.45, VERM) if alerta
                        else ft.Colors.with_opacity(0.2, cor) if cor != MUT
                        else BD2),
                )
                card.on_click = lambda e, ev=ev: _abrir_detalhe(ev)
                area.controls.append(card)

        btn_novo = ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=16, color=AZUL),
                ft.Text("Novo Evento", size=13, color=AZUL),
            ], spacing=6, tight=True),
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border_radius=8, ink=True,
            bgcolor=ft.Colors.with_opacity(0.10, AZUL),
            border=ft.border.all(1, ft.Colors.with_opacity(0.3, AZUL)))
        btn_novo.on_click = lambda e: _abrir_form(None)

        cab = lay.criar_cabecalho(
            "Histórico Clínico", voltar_fn,
            icone_titulo="history_rounded", cor_titulo=AZUL,
            acoes=[btn_novo])

        wrapper.controls.clear()
        wrapper.controls.append(ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Container(height=lay.spacer_topo, bgcolor=BG),
                cab,
                ft.Container(content=area,
                             padding=ft.padding.only(left=20, right=20, top=12, bottom=12),
                             expand=True),
            ], spacing=0, expand=True)))
        if _montado[0]:
            try: page.update()
            except Exception: pass

    _mostrar_lista()
    _montado[0] = True
    return wrapper
