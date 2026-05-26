# -*- coding: utf-8 -*-
# Prontuario | telas/tela_pressao.py -- Pressão Arterial: medições domésticas + lab
import datetime
import sqlite3
import flet as ft
import logging
from shared.layout import Layout
from shared.date_field import campo_data
from dados.model_prontuario import (
    listar_leituras_marcador, salvar_leitura_marcador,
    DB_PATH,
)
from telas.tela_exames import buscar_historico_exame

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; AMAR = "#D29922"
VERM = "#F85149"; VERM_INT = "#CC1111"; COR = "#4ECDC4"; ROXO = "#BC8CFF"

_TERMOS_SIS = ["sistolica", "pressao arterial", "pa sistolica", "pa sis"]
_TERMOS_DIA = ["diastolica", "pa diastolica", "pa dia"]
_TERMOS     = _TERMOS_SIS + _TERMOS_DIA

_MOMENTOS = [
    ("Repouso",     "< 120/80"),
    ("Apos exerc.", "< 140/90"),
    ("Ao acordar",  "< 120/80"),
    ("Noturna",     "< 120/80"),
    ("Aleatoria",   "< 140/90"),
]


def _label_sec(texto, cor=MUT):
    return ft.Text(texto, size=10, color=cor, weight=ft.FontWeight.W_700)


def _avaliar_cor_sis(v: float) -> str:
    if v < 90:    return VERM_INT
    if v < 100:   return VERM
    if v < 120:   return AZUL
    if v < 130:   return VERD
    if v < 140:   return AMAR
    if v < 160:   return VERM
    return VERM_INT


def _avaliar_cor_dia(v: float) -> str:
    if v < 60:    return VERM_INT
    if v < 65:    return VERM
    if v < 80:    return AZUL
    if v < 85:    return VERD
    if v < 90:    return AMAR
    if v < 100:   return VERM
    return VERM_INT


def _avaliar_cor_par(sis: float, dia: float) -> str:
    cs = _avaliar_cor_sis(sis)
    cd = _avaliar_cor_dia(dia)
    ordem = [AZUL, VERD, AMAR, VERM, VERM_INT]
    return cs if ordem.index(cs) >= ordem.index(cd) else cd


def _parse_data(data_str):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime((data_str or "")[:10], fmt).date()
        except ValueError:
            pass
    return None


def _dias_txt(data_str):
    dt = _parse_data(data_str)
    if dt is None:
        return data_str[:10] if data_str else "—"
    dias = (datetime.date.today() - dt).days
    if dias == 0:  return "hoje"
    if dias == 1:  return "1 dia atras"
    return f"{dias} dias atras"


def _para_display(s):
    if s and len(s) >= 10 and s[4:5] == "-":
        try:
            return datetime.datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            pass
    return s or ""


def _parse_pressao(obs: str):
    """Extrai (sis, dia) de observacoes no formato '[Momento] 120/80'."""
    raw = obs or ""
    if "]" in raw:
        raw = raw[raw.index("]") + 1:].strip()
    if "/" in raw:
        parts = raw.split("/", 1)
        try:
            return float(parts[0].strip()), float(parts[1].strip())
        except Exception:
            pass
    return None, None


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL
# ══════════════════════════════════════════════════════════════

def criar_tela_pressao(page: ft.Page, voltar_fn):
    import threading as _thr
    lay           = Layout(page)
    _montado      = [False]
    _status_banco = ["normal"]
    _handler_ant  = [None]
    wrapper       = ft.Column(expand=True)
    area_lista    = ft.Column(spacing=8)

    def _sync(apos_sync_fn=None):
        ov = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.ProgressRing(color=COR, width=36, height=36, stroke_width=3),
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
                log.warning("[PRESS] sync: %s", ex)
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

    # ── Overlay: contexto Claudia ────────────────────────────────

    def _claudia_ctx(val_sis, val_dia, leitura_id):
        ref_ov = [None]

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        tf_ctx = ft.TextField(
            label="O que estava acontecendo?",
            hint_text="Ex: estresse, cafeina, sem medicacao, exercicio...",
            bgcolor=CARD, border_color=BD2, focused_border_color=ROXO,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, multiline=True, min_lines=2, max_lines=3,
        )

        def _salvar_ctx(e):
            ctx = (tf_ctx.value or "").strip()
            if ctx and leitura_id:
                try:
                    with sqlite3.connect(DB_PATH, timeout=30) as conn:
                        conn.execute(
                            "UPDATE marcadores_leituras SET contexto = ? WHERE id = ?",
                            (ctx, leitura_id),
                        )
                except Exception as ex:
                    log.warning("[PRESS] salvar_ctx: %s", ex)
            _fechar()

        btn_pular = ft.Container(
            content=ft.Text("Pular", size=12, color=SEC),
            padding=ft.padding.symmetric(horizontal=14, vertical=9),
            border_radius=8, bgcolor=ft.Colors.with_opacity(0.13, SEC), ink=True,
        )
        btn_pular.on_click = _fechar

        btn_ctx = ft.Container(
            content=ft.Text("Salvar contexto", size=12, color=ROXO,
                            weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=14, vertical=9),
            border_radius=8, bgcolor=ft.Colors.with_opacity(0.13, ROXO), ink=True,
        )
        btn_ctx.on_click = _salvar_ctx

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("psychology_rounded", size=18, color=ROXO),
                        ft.Text("Claudia", size=14, color=ROXO,
                                weight=ft.FontWeight.W_700),
                    ], spacing=6),
                    ft.Container(height=4),
                    ft.Text(f"Registrei {val_sis:.0f}/{val_dia:.0f} mmHg (Pressao).",
                            size=13, color=TXT, weight=ft.FontWeight.W_600),
                    ft.Text("Valor fora do esperado (< 120/80).", size=12, color=VERM),
                    ft.Container(height=8),
                    tf_ctx,
                    ft.Container(height=12),
                    ft.Row([btn_pular, btn_ctx], spacing=8,
                           alignment=ft.MainAxisAlignment.END),
                ], tight=True, spacing=4),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20), width=320,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass

    # ── Overlay: nova / editar leitura ───────────────────────────

    def _abrir_form(e=None, leitura=None, on_salvo=None):
        ref_ov   = [None]
        _edit_id = leitura["id"] if leitura else None

        _obs_raw     = (leitura.get("observacoes") or "") if leitura else ""
        _momento_ini = "Repouso"
        if _obs_raw.startswith("[") and "]" in _obs_raw:
            _momento_ini = _obs_raw[1:_obs_raw.index("]")].strip() or "Repouso"

        _momento_ref = [_momento_ini]

        _sis_ini, _dia_ini = "", ""
        if leitura:
            _sis_v, _dia_v = _parse_pressao(_obs_raw)
            if _sis_v is not None:
                _sis_ini = f"{_sis_v:.0f}"
                _dia_ini = f"{_dia_v:.0f}"
            else:
                try:
                    _sis_ini = f"{float(str(leitura['valor']).replace(',', '.')):.0f}"
                except Exception: pass

        tf_sis = ft.TextField(
            label="Sistólica (mmHg)",
            value=_sis_ini,
            bgcolor=CARD, border_color=BD2, focused_border_color=COR,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, keyboard_type=ft.KeyboardType.NUMBER,
            autofocus=not bool(leitura),
        )
        tf_dia = ft.TextField(
            label="Diastólica (mmHg)",
            value=_dia_ini,
            bgcolor=CARD, border_color=BD2, focused_border_color=COR,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, keyboard_type=ft.KeyboardType.NUMBER,
        )
        dd_momento = ft.Dropdown(
            label="Momento",
            bgcolor=CARD, border_color=BD2, focused_border_color=COR,
            label_style=ft.TextStyle(color=SEC),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, value=_momento_ini,
            options=[ft.dropdown.Option(m[0]) for m in _MOMENTOS],
        )
        _data_ini = (_para_display(leitura.get("data_medicao", "")) if leitura
                     else datetime.date.today().strftime("%d/%m/%Y"))
        row_data, tf_data = campo_data(
            page, "Data", value=_data_ini,
            cor_acento=COR, bgcolor=CARD, border_color=BD2,
        )
        tf_hora = ft.TextField(
            label="Hora (opcional, HH:MM)",
            value=(leitura.get("hora_medicao") or "") if leitura else "",
            bgcolor=CARD, border_color=BD2, focused_border_color=COR,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
        )
        txt_erro = ft.Text("", size=11, color=VERM, visible=False)

        dd_momento.on_change = lambda e: _momento_ref.__setitem__(0, dd_momento.value or "Repouso")

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        def _salvar(e):
            sis_str  = (tf_sis.value or "").strip().replace(",", ".")
            dia_str  = (tf_dia.value or "").strip().replace(",", ".")
            data_str = (tf_data.value or "").strip()
            momento  = _momento_ref[0]

            if not sis_str or not dia_str or not data_str:
                txt_erro.value   = "Preencha sistolica, diastolica e data."
                txt_erro.visible = True
                try: page.update()
                except Exception: pass
                return
            try:
                sis_num = float(sis_str)
                dia_num = float(dia_str)
            except ValueError:
                txt_erro.value   = "Valores invalidos."
                txt_erro.visible = True
                try: page.update()
                except Exception: pass
                return

            ref_str = next((m[1] for m in _MOMENTOS if m[0] == momento), "< 120/80")

            dados = {
                "parametro":    "Sistolica",
                "categoria":    "Cardiovascular",
                "valor":        sis_num,
                "valor_txt":    f"{sis_num:.0f}",
                "unidade":      "mmHg",
                "referencia":   ref_str,
                "data_medicao": data_str,
                "hora_medicao": (tf_hora.value or "").strip() or None,
                "fonte":        "manual",
                "observacoes":  f"[{momento}] {sis_num:.0f}/{dia_num:.0f}",
            }
            if _edit_id:
                dados["id"] = _edit_id

            leitura_id = salvar_leitura_marcador(dados)
            _status_banco[0] = "em_edicao"
            _fechar()
            if on_salvo:
                on_salvo()
            else:
                _carregar()

            def _apos_sync():
                if not _edit_id and (sis_num >= 140 or dia_num >= 90 or sis_num < 90):
                    _claudia_ctx(sis_num, dia_num, leitura_id)

            _sync(_apos_sync)

        btn_cancel = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=ft.Colors.with_opacity(0.13, SEC), ink=True,
        )
        btn_cancel.on_click = _fechar

        btn_ok = ft.Container(
            content=ft.Text("Salvar", size=13, color=VERD, weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=ft.Colors.with_opacity(0.13, VERD), ink=True,
        )
        btn_ok.on_click = _salvar
        tf_sis.on_submit = lambda e: tf_dia.focus()
        tf_dia.on_submit = _salvar

        _titulo_form = "Editar Leitura" if leitura else "Nova Leitura — Pressão"

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("favorite_rounded", size=16, color=COR),
                        ft.Text(_titulo_form, size=15, color=TXT,
                                weight=ft.FontWeight.W_700),
                    ], spacing=8),
                    ft.Container(height=4),
                    ft.Row([
                        ft.Container(content=tf_sis, expand=True),
                        ft.Container(content=tf_dia, expand=True),
                    ], spacing=8),
                    dd_momento,
                    ft.Row([
                        ft.Container(content=row_data, expand=True),
                        ft.Container(content=tf_hora, expand=True),
                    ], spacing=8),
                    txt_erro,
                    ft.Container(height=4),
                    ft.Row([btn_cancel, btn_ok], spacing=8,
                           alignment=ft.MainAxisAlignment.CENTER),
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

    # ── Lista de medições domésticas ─────────────────────────────

    def _mostrar_lista_leituras(leituras_ini):
        area_leituras = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
        _leituras_ref = [leituras_ini]

        def _refresh_lista():
            _leituras_ref[0] = listar_leituras_marcador(_TERMOS)
            _rebuild_lista()
            _carregar()

        def _rebuild_lista():
            area_leituras.controls.clear()
            seen_ids = set()
            for r in _leituras_ref[0]:
                # skip diastolica duplicate rows — grouped with sistolica
                key = (r.get("data_medicao", ""), r.get("hora_medicao", ""))
                if key in seen_ids:
                    continue
                seen_ids.add(key)

                _obs_raw = (r.get("observacoes") or "")
                _momento_disp = ""
                if _obs_raw.startswith("[") and "]" in _obs_raw:
                    _momento_disp = _obs_raw[1:_obs_raw.index("]")].strip()

                sis_v, dia_v = _parse_pressao(_obs_raw)
                if sis_v is not None:
                    val_txt = f"{sis_v:.0f}/{dia_v:.0f}"
                    cor_v   = _avaliar_cor_par(sis_v, dia_v)
                else:
                    try:
                        v = float(str(r["valor"]).replace(",", "."))
                        val_txt = f"{v:.0f}"
                        cor_v   = _avaliar_cor_sis(v)
                    except Exception:
                        val_txt = "--"
                        cor_v   = MUT

                _data_disp = _para_display(r.get("data_medicao", ""))
                hora_txt   = (r.get("hora_medicao") or "").strip()
                _sub_parts = [p for p in [_data_disp, hora_txt, _momento_disp] if p]
                sub_txt    = "  •  ".join(_sub_parts)

                btn_edit = ft.Container(
                    content=ft.Icon("edit_rounded", size=16, color=SEC),
                    padding=ft.padding.all(8), border_radius=8, ink=True,
                )
                _lr = dict(r)
                btn_edit.on_click = lambda e, lr=_lr: _abrir_form(leitura=lr, on_salvo=_refresh_lista)

                card = ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Text(val_txt, size=15,
                                            weight=ft.FontWeight.W_900, color=cor_v),
                            width=64, alignment=ft.alignment.Alignment(0, 0),
                        ),
                        ft.Column([
                            ft.Text(f"{val_txt} mmHg", size=13, color=TXT,
                                    weight=ft.FontWeight.W_600),
                            ft.Text(sub_txt, size=11, color=SEC),
                        ], spacing=1, expand=True),
                        btn_edit,
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD, border_radius=8,
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    border=ft.Border(
                        left=ft.BorderSide(3, cor_v),
                        top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                        right=ft.BorderSide(1, BD),
                    ),
                )
                area_leituras.controls.append(card)

            if not _leituras_ref[0]:
                area_leituras.controls.append(
                    ft.Text("Nenhuma medicao registrada.", color=MUT, size=12))
            try: page.update()
            except Exception: pass

        _rebuild_lista()

        btn_voltar = ft.Container(
            content=ft.Icon("arrow_back_rounded", size=20, color=TXT),
            padding=ft.padding.all(8), border_radius=8, ink=True,
        )
        btn_voltar.on_click = lambda e: _sair(_mostrar_principal)

        btn_add = ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=16, color=COR),
                ft.Text("Registrar", size=13, color=COR),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_radius=8, ink=True,
        )
        btn_add.on_click = lambda e: _abrir_form(on_salvo=_refresh_lista)

        cab_lista = ft.Container(
            content=ft.Row([
                btn_voltar,
                ft.Icon("favorite_rounded", size=14, color=COR),
                ft.Text("Medicoes Domesticas", size=15, color=TXT,
                        weight=ft.FontWeight.W_700, expand=True),
                btn_add,
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=CARD,
            padding=ft.padding.symmetric(horizontal=8, vertical=6),
            border=ft.Border(bottom=ft.BorderSide(1, BD2)),
        )

        corpo_lista = ft.Column([
            ft.Container(height=lay.spacer_topo, bgcolor=BG),
            cab_lista,
            ft.Container(content=area_leituras,
                         padding=ft.padding.symmetric(horizontal=12, vertical=8),
                         expand=True),
        ], spacing=0, expand=True)

        wrapper.controls.clear()
        wrapper.controls.append(ft.Container(bgcolor=BG, expand=True, content=corpo_lista))
        try: page.update()
        except Exception: pass

    # ── Card reutilizável ────────────────────────────────────────

    def _mk_card(cor_borda, val_txt, cor_val, titulo, subtitulo, unidade, on_click_fn):
        card = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text(val_txt, size=16,
                                    weight=ft.FontWeight.W_900, color=cor_val),
                    width=64, alignment=ft.alignment.Alignment(0, 0),
                ),
                ft.Column([
                    ft.Text(titulo, size=12, color=TXT, weight=ft.FontWeight.W_600),
                    ft.Text(subtitulo, size=11, color=SEC),
                ], spacing=1, expand=True),
                ft.Row([
                    ft.Text(unidade, size=10, color=MUT),
                    ft.Icon("chevron_right_rounded", size=14, color=MUT),
                ], spacing=4, tight=True),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=CARD, border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border=ft.Border(left=ft.BorderSide(3, cor_borda),
                             top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                             right=ft.BorderSide(1, BD)),
        )
        card.on_click = on_click_fn
        return card

    # ── Carregamento ─────────────────────────────────────────────

    def _carregar():
        area_lista.controls.clear()

        leituras = listar_leituras_marcador(_TERMOS)

        # Filtrar só as linhas de sistólica (evita duplicatas dia)
        leituras_sis = [r for r in leituras
                        if any(t in (r.get("parametro") or "").lower()
                               for t in _TERMOS_SIS)]
        if not leituras_sis:
            leituras_sis = leituras

        todos_pares = []
        for r in leituras_sis:
            sis_v, dia_v = _parse_pressao(r.get("observacoes", ""))
            if sis_v is not None:
                todos_pares.append((r.get("data_medicao", ""), sis_v, dia_v))

        if todos_pares:
            data_ult, sis_ult, dia_ult = todos_pares[0]
            cor_ult = _avaliar_cor_par(sis_ult, dia_ult)
            sis_med = sum(x[1] for x in todos_pares) / len(todos_pares)
            dia_med = sum(x[2] for x in todos_pares) / len(todos_pares)
            cor_med = _avaliar_cor_par(sis_med, dia_med)

            area_lista.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Column([
                            _label_sec("ULTIMA MEDICAO"),
                            ft.Text(f"{sis_ult:.0f}/{dia_ult:.0f}", size=24,
                                    weight=ft.FontWeight.W_900, color=cor_ult),
                            ft.Text(f"mmHg  •  {_dias_txt(data_ult)}",
                                    size=11, color=SEC),
                        ], spacing=2, expand=True),
                        ft.Container(width=1, bgcolor=BD2),
                        ft.Container(
                            content=ft.Column([
                                _label_sec("MEDIA"),
                                ft.Text(f"{sis_med:.0f}/{dia_med:.0f}", size=20,
                                        weight=ft.FontWeight.W_700, color=cor_med),
                                ft.Text(f"{len(todos_pares)} medicoes",
                                        size=10, color=MUT),
                            ], spacing=2,
                               horizontal_alignment=ft.CrossAxisAlignment.END),
                            padding=ft.padding.only(left=14),
                        ),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=14),
                    bgcolor=CARD, border_radius=8,
                    padding=ft.padding.symmetric(horizontal=14, vertical=12),
                    border=ft.Border(
                        left=ft.BorderSide(3, cor_ult),
                        top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                        right=ft.BorderSide(1, BD),
                    ),
                )
            )
            area_lista.controls.append(ft.Divider(color=BD2, height=1))

        if leituras_sis and todos_pares:
            ult   = leituras_sis[0]
            sis_v, dia_v = todos_pares[0][1], todos_pares[0][2]
            cor_v = _avaliar_cor_par(sis_v, dia_v)
            val_txt = f"{sis_v:.0f}/{dia_v:.0f}"
            sub_dom = f"{len(todos_pares)}x  •  {_dias_txt(ult.get('data_medicao',''))}"

            def _click_dom(e, _leit=leituras):
                _mostrar_lista_leituras(_leit)
        else:
            cor_v   = MUT
            val_txt = "--/--"
            sub_dom = "sem registros  •  toque para registrar"
            _click_dom = _abrir_form

        area_lista.controls.append(
            _mk_card(cor_v, val_txt, cor_v,
                     "Medicoes Domesticas", sub_dom, "mmHg", _click_dom))

        # ── Exames de lab (MAPA e similares) ─────────────────────
        try:
            from telas.tela_exames import abrir_overlay_exame_mapa

            def _card_mapa(eid, tipo_exame, data, lab):
                """Card clicavel que abre o mesmo overlay de detalhe do card cardiaco."""
                card = ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Icon("monitor_heart_rounded", size=16, color=COR),
                            bgcolor=ft.Colors.with_opacity(0.15, COR),
                            border_radius=6, width=32, height=32,
                            alignment=ft.alignment.Alignment(0, 0),
                        ),
                        ft.Column([
                            ft.Text(tipo_exame or "MAPA", size=13, color=TXT,
                                    weight=ft.FontWeight.W_600),
                            ft.Row([
                                ft.Text(data[:10] if data else "?", size=11, color=SEC),
                                ft.Text("-", size=11, color=MUT),
                                ft.Text(lab or "", size=11, color=AZUL),
                            ], spacing=4),
                        ], spacing=2, expand=True),
                        ft.Icon("chevron_right_rounded", size=18, color=SEC),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD,
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    border=ft.Border(
                        top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                        left=ft.BorderSide(2, COR), right=ft.BorderSide(1, BD),
                    ),
                    ink=True,
                )
                card.on_click = lambda e, _id=eid: abrir_overlay_exame_mapa(page, _id)
                return card

            _ids_vistos = set()

            # 1. MAPA com resultados numericos (Total - PAS)
            with sqlite3.connect(DB_PATH, timeout=20) as _c:
                _sis = _c.execute("""
                    SELECT e.id, e.tipo_exame, e.data_exame, e.laboratorio
                    FROM exame_resultados r
                    JOIN exames e ON r.exame_id = e.id
                    WHERE r.parametro LIKE '%Total - PAS%'
                      AND r.valor IS NOT NULL AND r.valor != ''
                    GROUP BY e.id
                    ORDER BY e.data_exame DESC LIMIT 10
                """).fetchall()
            for _eid, _tpe, _data, _lab in _sis:
                _ids_vistos.add(_eid)
                area_lista.controls.append(_card_mapa(_eid, _tpe, _data, _lab))

            # 2. MAPA tipo='mapa' sem resultados numericos (so laudo)
            with sqlite3.connect(DB_PATH, timeout=10) as _c2:
                _mapass = _c2.execute("""
                    SELECT e.id, e.tipo_exame, e.data_exame, e.laboratorio
                    FROM exames e
                    WHERE e.tipo = 'mapa'
                    ORDER BY e.data_exame DESC LIMIT 10
                """).fetchall()
            for _eid, _tpe, _data, _lab in _mapass:
                if _eid in _ids_vistos:
                    continue
                area_lista.controls.append(_card_mapa(_eid, _tpe, _data, _lab))
        except Exception as _ex_lab:
            log.warning("[PRESS] lab: %s", _ex_lab)

        if _montado[0]:
            try: page.update()
            except Exception: pass

    # ── Layout principal ─────────────────────────────────────────

    area_principal = ft.Column([
        ft.Container(
            content=ft.Row([
                ft.Icon("biotech_rounded", size=12, color=AZUL),
                _label_sec("PRESSÃO ARTERIAL", AZUL),
            ], spacing=6),
        ),
        area_lista,
        ft.Container(height=20),
    ], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    btn_registrar = ft.Container(
        content=ft.Row([
            ft.Icon("add_rounded", size=16, color=COR),
            ft.Text("Registrar", size=13, color=COR),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8, ink=True,
    )
    btn_registrar.on_click = _abrir_form

    cabecalho = lay.criar_cabecalho(
        "Pressão Arterial", lambda e=None: _sair(voltar_fn),
        icone_titulo="favorite_rounded",
        cor_titulo=COR,
        acoes=[btn_registrar],
    )
    corpo = lay.criar_corpo(cabecalho, area_principal)

    def _mostrar_principal():
        wrapper.controls.clear()
        wrapper.controls.append(ft.Container(bgcolor=BG, expand=True, content=corpo))
        if _montado[0]:
            try: page.update()
            except Exception: pass

    _carregar()
    wrapper.controls.append(ft.Container(bgcolor=BG, expand=True, content=corpo))
    _montado[0] = True
    _registrar_voltar_hw()
    return wrapper
