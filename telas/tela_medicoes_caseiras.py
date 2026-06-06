# -*- coding: utf-8 -*-
# Prontuario | telas/tela_medicoes_caseiras.py
# Lista e registro de medicoes caseiras de glicemia (marcadores_leituras)
import flet as ft
import sqlite3
import datetime
import logging

from dados.model_prontuario import DB_PATH, normalizar_data
from shared.layout import Layout
from shared.date_field import campo_data

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
VERD = "#3FB950"; VERM = "#F85149"; AMAR = "#D29922"; COR = "#FF6B6B"

_MOMENTOS = [
    ("Jejum",        "70 - 99",  "Glicemia de Jejum"),
    ("Apos 1h",      "< 180",    "Glicemia de Jejum"),
    ("Apos 2h",      "< 140",    "Glicemia de Jejum"),
    ("Pos-Prandial", "< 140",    "Glicemia de Jejum"),
    ("Aleatoria",    "70 - 140", "Glicemia de Jejum"),
]

_HORAS = [f"{h:02d}:00" for h in range(24)]


def _avaliar_cor(v):
    try:
        val = float(str(v).replace(",", "."))
        if val < 54:   return "#CC1111"
        if val < 70:   return VERM
        if val <= 99:  return "#58A6FF"
        if val <= 109: return VERD
        if val <= 125: return AMAR
        return VERM
    except Exception:
        return "#58A6FF"


def _para_display(s):
    if s and len(s) >= 10 and s[4:5] == "-":
        try:
            return datetime.datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            pass
    return s or ""


def _dias_txt(data_str):
    try:
        dt = datetime.datetime.strptime((data_str or "")[:10], "%Y-%m-%d").date()
        dias = (datetime.date.today() - dt).days
        if dias == 0: return "hoje"
        if dias == 1: return "ontem"
        return f"{dias} dias atras"
    except Exception:
        return data_str[:10] if data_str else ""


def criar_tela_medicoes_caseiras(page: ft.Page, voltar_fn=None):
    lay      = Layout(page)
    area     = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
    _montado = [False]

    def _snack(msg, cor=VERD):
        s = ft.SnackBar(content=ft.Text(msg, color=TXT), bgcolor=CARD)
        page.overlay.append(s)
        s.open = True
        try: page.update()
        except Exception: pass

    # -- Form overlay -------------------------------------------------
    def _abrir_form(leitura=None):
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

        _val_ini = ""
        if leitura:
            try:
                _val_ini = f"{float(str(leitura['valor']).replace(',', '.')):.1f}"
            except Exception:
                _val_ini = str(leitura.get("valor", ""))

        tf_valor = ft.TextField(
            label="Glicemia (mg/dL)",
            value=_val_ini,
            bgcolor=CARD, border_color=BD2, focused_border_color=COR,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, keyboard_type=ft.KeyboardType.NUMBER,
            autofocus=not bool(leitura),
        )
        dd_momento = ft.Dropdown(
            label="Momento",
            bgcolor=CARD, border_color=BD2, focused_border_color=COR,
            label_style=ft.TextStyle(color=SEC),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, value=_momento_ini,
            options=[ft.dropdown.Option(m[0]) for m in _MOMENTOS],
        )
        _data_ini = (
            _para_display(leitura.get("data_medicao", "")) if leitura
            else datetime.date.today().strftime("%d/%m/%Y")
        )
        row_data, tf_data = campo_data(
            page, "Data", value=_data_ini,
            cor_acento=COR, bgcolor=CARD, border_color=BD2,
        )
        _hora_ini = (leitura.get("hora_medicao") or "").strip() if leitura else ""
        if _hora_ini and len(_hora_ini) >= 5:
            _hora_ini = _hora_ini[:2] + ":00"
        if not _hora_ini:
            _hora_ini = f"{datetime.datetime.now().hour:02d}:00"
        dd_hora = ft.Dropdown(
            label="Hora",
            bgcolor=CARD, border_color=BD2, focused_border_color=COR,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, value=_hora_ini,
            options=[ft.dropdown.Option(h) for h in _HORAS],
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

        dd_momento.on_change = lambda e: None

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        def _salvar(e=None):
            val_str  = (tf_valor.value or "").strip().replace(",", ".")
            data_str = (tf_data.value or "").strip()
            momento  = dd_momento.value or "Jejum"
            if not val_str or not data_str:
                txt_erro.value = "Preencha valor e data."
                txt_erro.visible = True
                try: page.update()
                except Exception: pass
                return
            try:
                val_num = float(val_str)
            except ValueError:
                txt_erro.value = "Valor invalido."
                txt_erro.visible = True
                try: page.update()
                except Exception: pass
                return

            ref_str = next((m[1] for m in _MOMENTOS if m[0] == momento), "70 - 99")
            data_iso = normalizar_data(data_str) or datetime.date.today().isoformat()

            try:
                conn = sqlite3.connect(DB_PATH, timeout=10)
                if _edit_id:
                    conn.execute("""
                        UPDATE marcadores_leituras
                        SET parametro='Glicemia de Jejum', valor=?, unidade='mg/dL',
                            referencia=?, data_medicao=?, hora_medicao=?,
                            observacoes=?, fonte='manual'
                        WHERE id=?
                    """, (val_num, ref_str, data_iso,
                          dd_hora.value,
                          f"[{momento}] {(tf_obs.value or '').strip()}",
                          _edit_id))
                else:
                    conn.execute("""
                        INSERT INTO marcadores_leituras
                            (parametro, categoria, valor, valor_txt, unidade,
                             referencia, data_medicao, hora_medicao, fonte, observacoes)
                        VALUES ('Glicemia de Jejum','Metabolico',?,?,
                                'mg/dL',?,?,?,'manual',?)
                    """, (val_num, f"{val_num:.1f}", ref_str, data_iso,
                          dd_hora.value,
                          f"[{momento}] {(tf_obs.value or '').strip()}"))
                conn.commit()
                conn.close()
            except Exception as ex:
                txt_erro.value = f"Erro: {ex}"
                txt_erro.visible = True
                try: page.update()
                except Exception: pass
                return

            _fechar()
            _carregar()
            _snack("Salvo.")

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
        tf_valor.on_submit = _salvar

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("water_drop_rounded", size=16, color=COR),
                        ft.Text(
                            "Editar Leitura" if leitura else "Nova Leitura",
                            size=15, color=TXT, weight=ft.FontWeight.W_700,
                        ),
                    ], spacing=8),
                    ft.Container(height=4),
                    tf_valor, dd_momento,
                    ft.Row([
                        ft.Container(content=row_data, expand=True),
                        ft.Container(content=dd_hora, width=108),
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

    # -- Lista --------------------------------------------------------
    def _carregar():
        area.controls.clear()
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            rows = conn.execute("""
                SELECT id, valor, unidade, referencia,
                       data_medicao, hora_medicao, observacoes
                FROM marcadores_leituras
                WHERE UPPER(parametro) = UPPER('Glicemia de Jejum')
                ORDER BY data_medicao DESC, hora_medicao DESC
            """).fetchall()
            conn.close()
        except Exception:
            rows = []

        if not rows:
            area.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("water_drop_rounded", size=44, color=MUT),
                    ft.Text("Nenhuma medicao registrada.", size=14, color=SEC),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                alignment=ft.alignment.Alignment(0, 0), padding=40,
            ))
            if _montado[0]:
                try: page.update()
                except Exception: pass
            return

        for lid, valor, unidade, ref, data_m, hora_m, obs in rows:
            cor_v = _avaliar_cor(valor)
            try:
                val_txt = f"{float(str(valor).replace(',', '.')):.1f}"
            except Exception:
                val_txt = str(valor or "--")

            _momento_disp = ""
            if obs and obs.startswith("[") and "]" in obs:
                _momento_disp = obs[1:obs.index("]")].strip()

            sub_parts = [p for p in [
                _para_display(data_m), hora_m, _momento_disp
            ] if p]
            sub_txt = "  •  ".join(sub_parts)
            dias    = _dias_txt(data_m)

            btn_edit = ft.Container(
                content=ft.Icon("edit_rounded", size=16, color=SEC),
                padding=ft.padding.all(8), border_radius=8, ink=True,
            )
            _lr = {
                "id": lid, "valor": valor, "unidade": unidade,
                "referencia": ref, "data_medicao": data_m,
                "hora_medicao": hora_m, "observacoes": obs,
            }
            btn_edit.on_click = lambda e, lr=_lr: _abrir_form(leitura=lr)

            card = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Text(val_txt, size=20,
                                        weight=ft.FontWeight.W_900, color=cor_v),
                        width=56, alignment=ft.alignment.Alignment(0, 0),
                    ),
                    ft.Column([
                        ft.Text(f"{val_txt} {unidade or 'mg/dL'}",
                                size=13, color=TXT, weight=ft.FontWeight.W_600),
                        ft.Text(sub_txt, size=11, color=SEC),
                        ft.Text(dias, size=10, color=MUT),
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
            area.controls.append(card)

        if _montado[0]:
            try: page.update()
            except Exception: pass

    _carregar()

    btn_novo = ft.Container(
        content=ft.Row([
            ft.Icon("add_rounded", size=16, color=COR),
            ft.Text("Nova", size=13, color=COR),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8, ink=True,
    )
    btn_novo.on_click = lambda e: _abrir_form()

    cabecalho = lay.criar_cabecalho(
        "Medicoes Caseiras",
        lambda e=None: voltar_fn() if voltar_fn else None,
        icone_titulo="home_rounded",
        cor_titulo=COR,
        acoes=[btn_novo],
    )
    corpo = lay.criar_corpo(cabecalho, area)
    _montado[0] = True
    return ft.Container(bgcolor=BG, expand=True, content=corpo)
