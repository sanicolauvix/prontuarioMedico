# -*- coding: utf-8 -*-
# Prontuario | telas/tela_historico_clinico.py
# Linha do tempo clínica pessoal — substitui tela_internacoes para uso pessoal.
import datetime
import sqlite3
import flet as ft
import logging
from shared.layout import Layout
from shared.date_field import campo_data
from dados.model_prontuario import DB_PATH

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; AMAR = "#D29922"
VERM = "#F85149"; VERM_INT = "#CC1111"; ROXO = "#BC8CFF"; LAR = "#F0883E"

_TIPOS = [
    ("evento_cardiaco", "favorite_rounded",          VERM,  "Evento Cardíaco"),
    ("cirurgia",        "local_hospital_rounded",    LAR,   "Cirurgia"),
    ("procedimento",    "medical_services_rounded",  AZUL,  "Procedimento"),
    ("internacao",      "bed_rounded",               AMAR,  "Internação"),
    ("diagnostico",     "diagnosis_rounded",         ROXO,  "Diagnóstico"),
    ("condicao_cronica","monitor_heart_rounded",     "#4ECDC4", "Condição Crônica"),
    ("alergia",         "warning_rounded",           VERM_INT, "Alergia"),
    ("infancia",        "child_care_rounded",        VERD,  "Infância"),
    ("exame",           "biotech_rounded",           SEC,   "Exame"),
    ("outro",           "event_note_rounded",        MUT,   "Outro"),
]

_TIPO_MAP = {k: (ico, cor, lbl) for k, ico, cor, lbl in _TIPOS}


def _para_display(s):
    if not s: return "—"
    s = str(s).strip()
    if len(s) >= 10 and s[4:5] == "-":
        try: return datetime.datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception: pass
    if len(s) == 7 and s[4:5] == "-":   # YYYY-MM
        try:
            m = datetime.datetime.strptime(s, "%Y-%m")
            return m.strftime("%m/%Y")
        except Exception: pass
    if len(s) == 4:  return s           # YYYY
    return s


def _label_sec(txt, cor=MUT):
    return ft.Text(txt, size=10, color=cor, weight=ft.FontWeight.W_700)


def _listar_historico() -> list[dict]:
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT id, data_aprox, tipo, titulo, descricao,
                       local, medico, sequela, alerta, fonte, criado_em
                FROM historico_medico
                ORDER BY data_aprox DESC, criado_em DESC
            """).fetchall()
            return [dict(r) for r in rows]
    except Exception as ex:
        log.warning("[HIST] listar: %s", ex)
        return []


def _salvar_historico(dados: dict) -> int:
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            if dados.get("id"):
                conn.execute("""
                    UPDATE historico_medico
                    SET data_aprox=?, tipo=?, titulo=?, descricao=?,
                        local=?, medico=?, sequela=?, alerta=?, fonte=?
                    WHERE id=?
                """, (dados.get("data_aprox"), dados.get("tipo","outro"),
                      dados["titulo"], dados.get("descricao"),
                      dados.get("local"), dados.get("medico"),
                      dados.get("sequela"), int(dados.get("alerta", 0)),
                      dados.get("fonte","paciente"), dados["id"]))
                conn.commit()
                return dados["id"]
            else:
                cur = conn.execute("""
                    INSERT INTO historico_medico
                        (data_aprox, tipo, titulo, descricao, local,
                         medico, sequela, alerta, fonte)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (dados.get("data_aprox"), dados.get("tipo","outro"),
                      dados["titulo"], dados.get("descricao"),
                      dados.get("local"), dados.get("medico"),
                      dados.get("sequela"), int(dados.get("alerta", 0)),
                      dados.get("fonte","paciente")))
                conn.commit()
                return cur.lastrowid
    except Exception as ex:
        log.warning("[HIST] salvar: %s", ex)
        return 0


def _excluir_historico(hid: int):
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute("DELETE FROM historico_medico WHERE id=?", (hid,))
            conn.commit()
    except Exception as ex:
        log.warning("[HIST] excluir: %s", ex)


# ══════════════════════════════════════════════════════════════
# TELA
# ══════════════════════════════════════════════════════════════

def criar_tela_historico_clinico(page: ft.Page, voltar_fn, readonly=False):
    import threading as _thr
    lay           = Layout(page)
    _montado      = [False]
    _status_banco = ["normal"]
    _handler_ant  = [None]
    area          = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    def _sync(apos_sync_fn=None):
        ov = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.ProgressRing(color=AZUL, width=36, height=36, stroke_width=3),
                    ft.Container(height=10),
                    ft.Text("Sincronizando com Drive...", size=13, color=TXT,
                            weight=ft.FontWeight.W_600, text_align="center"),
                    ft.Text("Aguarde", size=11, color=SEC, text_align="center"),
                ], tight=True, spacing=2,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(24), width=240,
            ),
            bgcolor="#DD000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        page.overlay.append(ov)
        try: page.update()
        except Exception: pass

        def _run():
            try:
                from backup.drive_backup import fazer_backup
                fazer_backup(forcar=True)
            except Exception as ex:
                log.warning("[HIST] sync: %s", ex)
            finally:
                _status_banco[0] = "normal"
                if ov in page.overlay:
                    page.overlay.remove(ov)
                try: page.update()
                except Exception: pass
                if apos_sync_fn:
                    apos_sync_fn()

        _thr.Thread(target=_run, daemon=True).start()

    def _sair(destino_fn):
        _desregistrar_voltar_hw()
        if _status_banco[0] == "em_edicao":
            _sync(destino_fn)
        else:
            destino_fn()

    def _registrar_voltar_hw():
        _handler_ant[0] = page.on_keyboard_event
        def _on_hw(e):
            if e.key == "Escape":
                _sair(voltar_fn)
        page.on_keyboard_event = _on_hw

    def _desregistrar_voltar_hw():
        page.on_keyboard_event = _handler_ant[0]

    # ── Overlay: form ───────────────────────────────────────────

    def _abrir_form(registro: dict = None):
        ref_ov = [None]
        r = registro or {}
        tipo_sel = [r.get("tipo", "outro")]
        alerta_sel = [bool(r.get("alerta", 0))]

        tf_titulo = ft.TextField(
            label="Título *",
            value=r.get("titulo", ""),
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, autofocus=not bool(r),
        )
        tf_data = ft.TextField(
            label="Data (AAAA, AAAA-MM ou AAAA-MM-DD)",
            value=r.get("data_aprox", ""),
            hint_text="Ex: 2008, 2008-03, 2008-03-15",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            hint_style=ft.TextStyle(color=MUT, size=10),
            border_radius=8,
        )
        tf_desc = ft.TextField(
            label="Descrição",
            value=r.get("descricao", ""),
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, multiline=True, min_lines=2, max_lines=4,
        )
        tf_local = ft.TextField(
            label="Local / Hospital",
            value=r.get("local", ""),
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
        )
        tf_medico = ft.TextField(
            label="Médico responsável",
            value=r.get("medico", ""),
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
        )
        tf_sequela = ft.TextField(
            label="Sequela / consequência permanente",
            value=r.get("sequela", ""),
            hint_text="Ex: 4 stents coronarianos, estenose uretral...",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            hint_style=ft.TextStyle(color=MUT, size=10),
            border_radius=8,
        )

        tipo_row = ft.Row(spacing=6, wrap=True)

        def _rebuild_tipos():
            tipo_row.controls.clear()
            for chave, ico, cor, lbl in _TIPOS:
                ativo = chave == tipo_sel[0]
                btn = ft.Container(
                    content=ft.Row([
                        ft.Icon(ico, size=11, color=cor if ativo else SEC),
                        ft.Text(lbl, size=10,
                                color=cor if ativo else SEC,
                                weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.NORMAL),
                    ], spacing=3, tight=True),
                    padding=ft.padding.symmetric(horizontal=8, vertical=5),
                    border_radius=16, ink=True,
                    bgcolor=ft.Colors.with_opacity(0.15, cor) if ativo else BD,
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

        # Chip de alerta
        def _mk_chip_alerta():
            ativo = alerta_sel[0]
            c = ft.Container(
                content=ft.Row([
                    ft.Icon("warning_rounded", size=12, color=VERM if ativo else SEC),
                    ft.Text("Alerta crítico" if ativo else "Marcar como alerta",
                            size=11, color=VERM if ativo else SEC,
                            weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.NORMAL),
                ], spacing=4, tight=True),
                bgcolor=ft.Colors.with_opacity(0.15, VERM) if ativo else BD,
                border_radius=16,
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                ink=True,
                border=ft.Border(
                    top=ft.BorderSide(1, VERM if ativo else BD2),
                    bottom=ft.BorderSide(1, VERM if ativo else BD2),
                    left=ft.BorderSide(1, VERM if ativo else BD2),
                    right=ft.BorderSide(1, VERM if ativo else BD2)),
            )
            def _toggle(e):
                alerta_sel[0] = not alerta_sel[0]
                chip_alerta_row.controls.clear()
                chip_alerta_row.controls.append(_mk_chip_alerta())
                try: page.update()
                except Exception: pass
            c.on_click = _toggle
            return c

        chip_alerta_row = ft.Row([_mk_chip_alerta()], spacing=0)

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        def _salvar(e):
            titulo = (tf_titulo.value or "").strip()
            if not titulo:
                tf_titulo.error_text = "Obrigatório"
                try: page.update()
                except Exception: pass
                return
            _salvar_historico({
                "id":         r.get("id"),
                "data_aprox": (tf_data.value or "").strip() or None,
                "tipo":       tipo_sel[0],
                "titulo":     titulo,
                "descricao":  (tf_desc.value or "").strip() or None,
                "local":      (tf_local.value or "").strip() or None,
                "medico":     (tf_medico.value or "").strip() or None,
                "sequela":    (tf_sequela.value or "").strip() or None,
                "alerta":     alerta_sel[0],
                "fonte":      "paciente",
            })
            _status_banco[0] = "em_edicao"
            _fechar()
            _carregar()
            _sync()

        btn_ok = ft.Container(
            content=ft.Text("Salvar", size=13, color=AZUL,
                            weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            border_radius=8, bgcolor=ft.Colors.with_opacity(0.13, AZUL),
            ink=True, expand=True, alignment=ft.Alignment(0, 0))
        btn_ok.on_click = _salvar

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("event_note_rounded", size=16, color=AZUL),
                        ft.Text("Novo Evento" if not r else "Editar Evento",
                                size=15, color=TXT, weight=ft.FontWeight.W_700),
                    ], spacing=8),
                    ft.Container(height=4),
                    _label_sec("TIPO DE EVENTO"),
                    tipo_row,
                    tf_titulo,
                    tf_data,
                    tf_desc,
                    ft.Row([
                        ft.Container(content=tf_local, expand=True),
                        ft.Container(content=tf_medico, expand=True),
                    ], spacing=8),
                    tf_sequela,
                    chip_alerta_row,
                    ft.Container(height=4),
                    btn_ok,
                ], spacing=10, tight=True,
                   scroll=ft.ScrollMode.AUTO),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20), width=380,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass

    # ── Confirmação de exclusão ─────────────────────────────────

    def _confirmar_del(hid: int, titulo: str):
        ref_ov = [None]
        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass
        def _ok(e):
            _fechar()
            _excluir_historico(hid)
            _carregar()
        btn_c = ft.Container(
            content=ft.Text("Cancelar", size=13, color=TXT,
                            weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=BD2, ink=True, expand=True,
            alignment=ft.Alignment(0, 0))
        btn_c.on_click = _fechar
        btn_d = ft.Container(
            content=ft.Text("Excluir", size=13, color=VERM,
                            weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8,
            bgcolor=ft.Colors.with_opacity(0.13, VERM),
            ink=True, expand=True, alignment=ft.Alignment(0, 0),
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.with_opacity(0.40, VERM)),
                bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.40, VERM)),
                left=ft.BorderSide(1, ft.Colors.with_opacity(0.40, VERM)),
                right=ft.BorderSide(1, ft.Colors.with_opacity(0.40, VERM))))
        btn_d.on_click = _ok
        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Excluir evento?", size=15, color=TXT,
                            weight=ft.FontWeight.W_700),
                    ft.Container(height=4),
                    ft.Text(titulo, size=13, color=SEC),
                    ft.Container(height=12),
                    ft.Row([btn_c, ft.Container(width=8), btn_d]),
                ], spacing=0, tight=True),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20), width=320),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0))
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass

    # ── Carregamento ─────────────────────────────────────────────

    def _carregar():
        area.controls.clear()
        registros = _listar_historico()

        # Alertas críticos no topo
        alertas = [r for r in registros if r.get("alerta")]
        if alertas:
            chips_alerta = []
            for a in alertas:
                _, cor_t, _ = _TIPO_MAP.get(a.get("tipo","outro"), ("event_note_rounded", VERM, ""))
                chips_alerta.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon("warning_rounded", size=11, color=VERM_INT),
                            ft.Text(a["titulo"], size=11, color=VERM_INT,
                                    weight=ft.FontWeight.W_700),
                        ], spacing=4, tight=True),
                        bgcolor=ft.Colors.with_opacity(0.13, VERM_INT),
                        border_radius=16,
                        padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    )
                )
            area.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("warning_rounded", size=13, color=VERM_INT),
                        _label_sec("ALERTAS CRÍTICOS", VERM_INT),
                    ], spacing=6),
                    ft.Container(height=6),
                    ft.Row(chips_alerta, spacing=6, wrap=True),
                ], spacing=0),
                bgcolor=ft.Colors.with_opacity(0.07, VERM_INT),
                border_radius=10,
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border=ft.Border(
                    top=ft.BorderSide(1, ft.Colors.with_opacity(0.30, VERM_INT)),
                    bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.30, VERM_INT)),
                    left=ft.BorderSide(3, VERM_INT),
                    right=ft.BorderSide(1, ft.Colors.with_opacity(0.30, VERM_INT))),
            ))

        if not registros:
            area.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("timeline_rounded", size=36, color=MUT),
                    ft.Text("Nenhum evento registrado.", size=13, color=SEC,
                            text_align=ft.TextAlign.CENTER),
                    ft.Text("Use + para adicionar eventos da sua história clínica.",
                            size=11, color=MUT, text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=8, tight=True),
                padding=ft.padding.symmetric(vertical=40),
                alignment=ft.alignment.center,
            ))
        else:
            # Agrupa por ano
            ano_atual = None
            for r in registros:
                data_raw = r.get("data_aprox") or ""
                ano = data_raw[:4] if data_raw else "?"
                if ano != ano_atual:
                    ano_atual = ano
                    area.controls.append(ft.Container(
                        content=ft.Text(ano, size=12, color=SEC,
                                        weight=ft.FontWeight.W_700),
                        padding=ft.padding.only(top=12, bottom=4),
                    ))

                ico_t, cor_t, lbl_t = _TIPO_MAP.get(
                    r.get("tipo","outro"), ("event_note_rounded", MUT, "Outro"))

                linhas = [
                    ft.Row([
                        ft.Icon(ico_t, size=13, color=cor_t),
                        ft.Text(r["titulo"], size=13, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True),
                        ft.Text(_para_display(r.get("data_aprox")),
                                size=10, color=MUT),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START),
                ]
                if r.get("local") or r.get("medico"):
                    sub = "  •  ".join(
                        p for p in [r.get("local"), r.get("medico")] if p)
                    linhas.append(ft.Text(sub, size=11, color=SEC))
                if r.get("descricao"):
                    linhas.append(ft.Text(r["descricao"], size=11, color=SEC))
                if r.get("sequela"):
                    linhas.append(ft.Row([
                        ft.Icon("arrow_forward_rounded", size=10, color=AMAR),
                        ft.Text(r["sequela"], size=11, color=AMAR),
                    ], spacing=4))

                btn_edit = ft.Container(
                    content=ft.Icon("edit_rounded", size=14, color=SEC),
                    padding=ft.padding.all(6), border_radius=6, ink=True,
                    visible=not readonly)
                btn_del = ft.Container(
                    content=ft.Icon("delete_outline_rounded", size=14, color=VERM),
                    padding=ft.padding.all(6), border_radius=6, ink=True,
                    visible=not readonly)

                _r = dict(r)
                btn_edit.on_click = lambda e, _reg=_r: _abrir_form(_reg)
                btn_del.on_click  = lambda e, _hid=r["id"], _t=r["titulo"]: _confirmar_del(_hid, _t)

                area.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Column(linhas, spacing=3, tight=True, expand=True),
                        ft.Row([btn_edit, btn_del], spacing=0),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                       vertical_alignment=ft.CrossAxisAlignment.START),
                    bgcolor=CARD, border_radius=8,
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    border=ft.Border(
                        left=ft.BorderSide(3, cor_t),
                        top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                        right=ft.BorderSide(1, BD)),
                ))

        area.controls.append(ft.Container(height=20))
        if _montado[0]:
            try: page.update()
            except Exception: pass

    # ── Layout ───────────────────────────────────────────────────

    btn_add = ft.Container(
        content=ft.Row([
            ft.Icon("add_rounded", size=16, color=AZUL),
            ft.Text("Adicionar", size=13, color=AZUL),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8, ink=True,
        visible=not readonly,
    )
    btn_add.on_click = lambda e: _abrir_form()

    cabecalho = lay.criar_cabecalho(
        "Histórico Clínico", lambda e=None: _sair(voltar_fn),
        icone_titulo="timeline_rounded",
        cor_titulo=AZUL,
        acoes=[] if readonly else [btn_add],
    )

    area_scroll = ft.Container(
        content=area,
        expand=True,
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
    )

    corpo = ft.Column([
        ft.Container(height=lay.spacer_topo, bgcolor=BG),
        cabecalho,
        area_scroll,
    ], expand=True, spacing=0)

    _carregar()
    _montado[0] = True
    _registrar_voltar_hw()
    return ft.Container(bgcolor=BG, expand=True, content=lay.wrap(corpo))
