# -*- coding: utf-8 -*-
# Prontuario | telas/tela_acido_urico.py -- Ácido Úrico: medições domésticas + lab
import datetime
import sqlite3
import flet as ft
import logging
from shared.layout import Layout
from shared.widgets import abrir_sub_grafico
from shared.date_field import campo_data
from dados.model_prontuario import (
    listar_leituras_marcador, salvar_leitura_marcador,
    DB_PATH, normalizar_data,
)
from telas.tela_exames import buscar_historico_exame

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; AMAR = "#D29922"
VERM = "#F85149"; VERM_INT = "#CC1111"; COR = "#FFD93D"; ROXO = "#BC8CFF"

_TERMOS = ["acido urico", "urico", "uratos", "ácido úrico"]

# (label, referencia_display, limite_alto_m, limite_alto_f)
# Ref normal: homem 3.5-7.2 mg/dL, mulher 2.6-6.0 mg/dL
_MOMENTOS = [
    ("Jejum",        "H: 3.5-7.2 / M: 2.6-6.0",  7.2),
    ("Apos refeicao","H: 3.5-7.2 / M: 2.6-6.0",  7.2),
    ("Aleatoria",    "H: 3.5-7.2 / M: 2.6-6.0",  7.2),
]


def _label_sec(texto, cor=MUT):
    return ft.Text(texto, size=10, color=cor, weight=ft.FontWeight.W_700)


def _avaliar_cor(valor_str):
    try:
        v = float(str(valor_str).replace(",", "."))
        if v < 2.0:    return VERM_INT   # muito baixo
        if v < 2.6:    return VERM       # baixo
        if v <= 7.2:   return AZUL       # normal
        if v <= 8.5:   return AMAR       # atenção (hiperuricemia leve)
        if v <= 10.0:  return VERM       # alto
        return VERM_INT                  # muito alto (risco gota aguda)
    except Exception:
        return AZUL


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
    return dt.strftime("%d/%m/%Y")


def _para_display(s):
    if s and len(s) >= 10 and s[4:5] == "-":
        try:
            return datetime.datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            pass
    return s or ""


def _fora_do_range(valor: float) -> bool:
    return valor > 7.2 or valor < 2.6


def _listar_exames_urico(limite: int = 100) -> list[dict]:
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.row_factory = sqlite3.Row
            # LOWER() no SQLite nao converte acentos — buscar o id do padrao via INSTR
            # que e sensivel ao case mas funciona com Unicode, filtrando falsos positivos
            # ('Ferro Serico', 'Teste Ergometrico') pela ausencia de 'Urico'/'Urica' no nome
            padrao_rows = conn.execute(
                "SELECT id, nome_oficial FROM exames_padrao "
                "WHERE nome_oficial LIKE '%rico%' OR nome_oficial LIKE '%Uric%'"
            ).fetchall()
            ids_urico = [
                r[0] for r in padrao_rows
                if "ferro" not in (r[1] or "").lower()
                and "ergom" not in (r[1] or "").lower()
            ]
            if not ids_urico:
                return []
            placeholders = ",".join("?" * len(ids_urico))
            rows = conn.execute(f"""
                SELECT re.*, ep.nome_oficial AS parametro, ep.unidade,
                       e.data_exame, re.exame_padrao_id
                FROM exame_resultados re
                LEFT JOIN exames_padrao ep ON ep.id = re.exame_padrao_id
                LEFT JOIN exames e ON e.id = re.exame_id
                WHERE re.exame_padrao_id IN ({placeholders})
                ORDER BY e.data_exame DESC
                LIMIT ?
            """, ids_urico + [limite]).fetchall()
            return [dict(r) for r in rows]
    except Exception as ex:
        log.warning("[URICO] listar_exames: %s", ex)
        return []


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL
# ══════════════════════════════════════════════════════════════

def criar_tela_acido_urico(page: ft.Page, voltar_fn):
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
                log.warning("[URICO] sync: %s", ex)
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

    def _abrir_grafico(titulo, exame_dict):
        abrir_sub_grafico(page, wrapper, lay, titulo, exame_dict, _mostrar_principal)

    # ── Overlay: contexto Claudia ────────────────────────────────

    def _claudia_ctx(param, val, unidade, ref, leitura_id):
        ref_ov = [None]

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        tf_ctx = ft.TextField(
            label="O que estava acontecendo?",
            hint_text="Ex: comi muita carne, bebida alcoolica, falta de agua...",
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
                    log.warning("[URICO] salvar_ctx: %s", ex)
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

        val_str = f"{val:.2f}" if isinstance(val, float) else str(val)

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("psychology_rounded", size=18, color=ROXO),
                        ft.Text("Claudia", size=14, color=ROXO,
                                weight=ft.FontWeight.W_700),
                    ], spacing=6),
                    ft.Container(height=4),
                    ft.Text(f"Registrei {val_str} {unidade} ({param}).",
                            size=13, color=TXT, weight=ft.FontWeight.W_600),
                    ft.Text(f"Valor fora do esperado ({ref}).", size=12, color=VERM),
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
        _momento_ini = "Jejum"
        _obs_ini     = ""
        if _obs_raw.startswith("[") and "]" in _obs_raw:
            _end         = _obs_raw.index("]")
            _momento_ini = _obs_raw[1:_end].strip() or "Jejum"
            _obs_ini     = _obs_raw[_end + 1:].strip()
        elif leitura:
            _obs_ini = _obs_raw

        _momento_ref = [_momento_ini]

        _val_ini = ""
        if leitura:
            try:
                _val_ini = f"{float(str(leitura['valor']).replace(',', '.')):.2f}"
            except Exception:
                _val_ini = str(leitura.get("valor", ""))

        tf_valor = ft.TextField(
            label="Ácido Úrico (mg/dL)",
            value=_val_ini,
            bgcolor=CARD, border_color=BD2, focused_border_color=COR,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            keyboard_type=ft.KeyboardType.NUMBER,
            autofocus=not bool(leitura),
        )
        dd_momento = ft.Dropdown(
            label="Momento",
            bgcolor=CARD, border_color=BD2, focused_border_color=COR,
            label_style=ft.TextStyle(color=SEC),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            value=_momento_ini,
            options=[ft.dropdown.Option(m[0]) for m in _MOMENTOS],
        )
        _data_ini = (_para_display(leitura.get("data_medicao", "")) if leitura
                     else datetime.date.today().strftime("%d/%m/%Y"))
        row_data, tf_data = campo_data(
            page, "Data",
            value=_data_ini,
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
        tf_obs = ft.TextField(
            label="Observacao (opcional)",
            value=_obs_ini,
            bgcolor=CARD, border_color=BD2, focused_border_color=COR,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, multiline=True, min_lines=1, max_lines=2,
        )
        txt_erro = ft.Text("", size=11, color=VERM, visible=False)

        dd_momento.on_change = lambda e: _momento_ref.__setitem__(0, dd_momento.value or "Jejum")

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        def _salvar(e):
            val_str  = (tf_valor.value or "").strip().replace(",", ".")
            data_str = (tf_data.value or "").strip()
            momento  = _momento_ref[0]

            if not val_str or not data_str:
                txt_erro.value   = "Preencha valor e data."
                txt_erro.visible = True
                try: page.update()
                except Exception: pass
                return
            try:
                val_num = float(val_str)
            except ValueError:
                txt_erro.value   = "Valor invalido."
                txt_erro.visible = True
                try: page.update()
                except Exception: pass
                return

            ref_str = next((m[1] for m in _MOMENTOS if m[0] == momento), "3.5 - 7.2")

            dados = {
                "parametro":    "Acido Urico",
                "categoria":    "Metabolico",
                "valor":        val_num,
                "valor_txt":    f"{val_num:.2f}",
                "unidade":      "mg/dL",
                "referencia":   ref_str,
                "data_medicao": data_str,
                "hora_medicao": (tf_hora.value or "").strip() or None,
                "fonte":        "manual",
                "observacoes":  f"[{momento}] " + ((tf_obs.value or "").strip()),
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
                if not _edit_id and _fora_do_range(val_num):
                    _claudia_ctx("Acido Urico", val_num, "mg/dL", ref_str, leitura_id)

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
        tf_valor.on_submit = _salvar

        _titulo_form = "Editar Leitura" if leitura else "Nova Leitura — Ácido Úrico"

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("science_rounded", size=16, color=COR),
                        ft.Text(_titulo_form, size=15, color=TXT,
                                weight=ft.FontWeight.W_700),
                    ], spacing=8),
                    ft.Container(height=4),
                    tf_valor, dd_momento,
                    ft.Row([
                        ft.Container(content=row_data, expand=True),
                        ft.Container(content=tf_hora, expand=True),
                    ], spacing=8),
                    tf_obs, txt_erro,
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
            for r in _leituras_ref[0]:
                _data_disp = _para_display(r.get("data_medicao", ""))
                try:
                    val_txt = f"{float(str(r['valor']).replace(',', '.')):.2f}"
                except Exception:
                    val_txt = str(r.get("valor", "--"))
                cor_v = _avaliar_cor(str(r["valor"]))

                _obs_raw      = (r.get("observacoes") or "")
                _momento_disp = ""
                if _obs_raw.startswith("[") and "]" in _obs_raw:
                    _end          = _obs_raw.index("]")
                    _momento_disp = _obs_raw[1:_end].strip()

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
                            content=ft.Text(val_txt, size=17,
                                            weight=ft.FontWeight.W_900, color=cor_v),
                            width=56, alignment=ft.alignment.Alignment(0, 0),
                        ),
                        ft.Column([
                            ft.Text(f"{val_txt} mg/dL", size=13, color=TXT,
                                    weight=ft.FontWeight.W_600),
                            ft.Text(sub_txt, size=11, color=SEC),
                            ft.Text(f"Ref: {r.get('referencia','3.5 - 7.2')}",
                                    size=10, color=MUT),
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
                ft.Icon("science_rounded", size=14, color=COR),
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
                    content=ft.Text(val_txt, size=18,
                                    weight=ft.FontWeight.W_900, color=cor_val),
                    width=56, alignment=ft.alignment.Alignment(0, 0),
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
        exames   = _listar_exames_urico()

        # (data, valor, fonte) — fonte: "manual" ou "lab"
        todos_vals = []
        for r in leituras:
            try:
                todos_vals.append((r.get("data_medicao") or "",
                                   float(str(r["valor"]).replace(",", ".")),
                                   "manual"))
            except Exception: pass
        for r in exames:
            try:
                todos_vals.append((r.get("data_exame") or "",
                                   float(str(r["valor"]).replace(",", ".")),
                                   "lab"))
            except Exception: pass

        todos_vals.sort(key=lambda x: x[0], reverse=True)

        if todos_vals:
            data_ult, val_ult, fonte_ult = todos_vals[0]
            media   = sum(v for _, v, _ in todos_vals) / len(todos_vals)
            cor_ult = _avaliar_cor(str(val_ult))
            cor_med = _avaliar_cor(str(media))
            fonte_label = "Lab" if fonte_ult == "lab" else "Manual"

            area_lista.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Column([
                            _label_sec("ULTIMA MEDICAO"),
                            ft.Text(f"{val_ult:.2f}", size=26,
                                    weight=ft.FontWeight.W_900, color=cor_ult),
                            ft.Text(f"mg/dL  •  {_dias_txt(data_ult)}  •  {fonte_label}",
                                    size=11, color=SEC),
                        ], spacing=2, expand=True),
                        ft.Container(width=1, bgcolor=BD2),
                        ft.Container(
                            content=ft.Column([
                                _label_sec("MEDIA"),
                                ft.Text(f"{media:.2f}", size=22,
                                        weight=ft.FontWeight.W_700, color=cor_med),
                                ft.Text(f"{len(todos_vals)} medicoes",
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

        # Card: Medições Domésticas
        if leituras:
            ult   = leituras[0]
            cor_v = _avaliar_cor(ult["valor"])
            try:
                val_txt = f"{float(str(ult['valor']).replace(',', '.')):.2f}"
            except Exception:
                val_txt = "--"
            sub_dom = f"{len(leituras)}x  •  {_dias_txt(ult.get('data_medicao',''))}"
            unidade = ult.get("unidade", "mg/dL")

            def _click_dom(e, _leit=leituras):
                _mostrar_lista_leituras(_leit)
        else:
            cor_v   = MUT
            val_txt = "--"
            sub_dom = "sem registros  •  toque para registrar"
            unidade = "mg/dL"
            _click_dom = _abrir_form

        area_lista.controls.append(
            _mk_card(cor_v, val_txt, cor_v,
                     "Medicoes Domesticas", sub_dom, unidade, _click_dom))

        # Cards: exames de laboratório
        if exames:
            grupos = {}
            for r in exames:
                key = (r.get("parametro") or "Desconhecido").strip().lower()
                if key not in grupos:
                    grupos[key] = {
                        "parametro":       (r.get("parametro") or "Desconhecido").strip(),
                        "exame_padrao_id": r.get("exame_padrao_id"),
                        "resultados":      [],
                    }
                grupos[key]["resultados"].append(r)

            for grupo in grupos.values():
                regs   = grupo["resultados"]
                ultimo = regs[0]
                cor_v  = _avaliar_cor(ultimo["valor"])
                try:
                    val_txt = f"{float(str(ultimo['valor']).replace(',', '.')):.2f}"
                except Exception:
                    val_txt = "--"
                sub_lab = f"{len(regs)}x  •  {_dias_txt(ultimo.get('data_exame',''))}"
                unidade = ultimo.get("unidade", "mg/dL")
                titulo  = grupo["parametro"].title()
                ep_id   = grupo["exame_padrao_id"]

                def _click_lab(e, _titulo=titulo, _ep_id=ep_id, _unidade=unidade):
                    hist = buscar_historico_exame(_ep_id) if _ep_id else []
                    _abrir_grafico(_titulo,
                                   {"nome_oficial": _titulo,
                                    "unidade": _unidade, "historico": hist})

                area_lista.controls.append(
                    _mk_card(cor_v + "88", val_txt, cor_v,
                             titulo, sub_lab, unidade, _click_lab))

        if _montado[0]:
            try: page.update()
            except Exception: pass

    # ── Layout principal ─────────────────────────────────────────

    area_principal = ft.Column([
        ft.Container(
            content=ft.Row([
                ft.Icon("biotech_rounded", size=12, color=AZUL),
                _label_sec("ÁCIDO ÚRICO", AZUL),
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
        "Ácido Úrico", lambda e=None: _sair(voltar_fn),
        icone_titulo="science_rounded",
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
