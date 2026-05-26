# -*- coding: utf-8 -*-
# Prontuario | telas/tela_bioimpedancia.py -- Bioimpedância: medições domésticas + lab
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

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; AMAR = "#D29922"
VERM = "#F85149"; VERM_INT = "#CC1111"; COR = "#3FB950"; ROXO = "#BC8CFF"

_TERMOS = ["gordura", "massa magra", "massa muscular", "imc", "bioimpedancia",
           "gordura corporal", "gordura visceral", "agua corporal"]

# Parâmetros por sessão de bioimpedância
_PARAMS = [
    # (chave, label, unidade, ref_display)
    ("gordura",          "Gordura Corporal",  "%",   "H: 8-25  M: 20-35"),
    ("massa_muscular",   "Massa Muscular",     "kg",  "varia por estatura"),
    ("massa_magra",      "Massa Magra",        "kg",  "varia por estatura"),
    ("imc",              "IMC",                "",    "18.5 - 24.9"),
    ("agua_corporal",    "Água Corporal",      "%",   "H: 55-65  M: 45-60"),
    ("gordura_visceral", "Gordura Visceral",   "",    "< 10"),
    ("massa_ossea",      "Massa Óssea",        "kg",  "varia por sexo"),
    ("taxa_metabolica",  "Taxa Metabólica",    "kcal",""),
]

_PARAM_KEYS = [p[0] for p in _PARAMS]


def _label_sec(texto, cor=MUT):
    return ft.Text(texto, size=10, color=cor, weight=ft.FontWeight.W_700)


def _avaliar_cor_gordura(v: float) -> str:
    # Usando ref masculina como padrão geral
    if v < 8:    return VERM
    if v <= 25:  return AZUL
    if v <= 30:  return AMAR
    if v <= 35:  return VERM
    return VERM_INT


def _avaliar_cor_imc(v: float) -> str:
    if v < 16:    return VERM_INT
    if v < 18.5:  return VERM
    if v <= 24.9: return AZUL
    if v <= 29.9: return AMAR
    if v <= 34.9: return VERM
    return VERM_INT


def _avaliar_cor_gordura_visc(v: float) -> str:
    if v < 10:  return AZUL
    if v < 15:  return AMAR
    return VERM


def _avaliar_cor_param(chave: str, valor: float) -> str:
    if chave == "gordura":          return _avaliar_cor_gordura(valor)
    if chave == "imc":              return _avaliar_cor_imc(valor)
    if chave == "gordura_visceral": return _avaliar_cor_gordura_visc(valor)
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


def _parse_sessao(leituras: list[dict], data_medicao: str) -> dict:
    """Agrupa leituras de um mesmo dia como uma sessão."""
    sessao = {}
    for r in leituras:
        if r.get("data_medicao") == data_medicao:
            param = (r.get("parametro") or "").lower().replace(" ", "_")
            for k, lbl, _, _ in _PARAMS:
                if k in param or lbl.lower().replace(" ", "_") in param:
                    try:
                        sessao[k] = float(str(r["valor"]).replace(",", "."))
                    except Exception:
                        pass
    return sessao


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL
# ══════════════════════════════════════════════════════════════

def criar_tela_bioimpedancia(page: ft.Page, voltar_fn):
    lay      = Layout(page)
    _montado = [False]
    wrapper  = ft.Column(expand=True)
    area_lista = ft.Column(spacing=8)

    # ── Overlay: nova / editar sessão ────────────────────────────

    def _abrir_form(e=None, sessao_data=None, on_salvo=None):
        """sessao_data = {'data': 'YYYY-MM-DD', 'gordura': 28.5, 'imc': 26.1, ...}"""
        ref_ov = [None]
        _data_ini = (_para_display(sessao_data.get("data", "")) if sessao_data
                     else datetime.date.today().strftime("%d/%m/%Y"))

        tf_campos = {}
        for chave, lbl, unidade, ref in _PARAMS:
            ini_val = ""
            if sessao_data and chave in sessao_data:
                try:
                    ini_val = f"{float(sessao_data[chave]):.1f}"
                except Exception:
                    pass
            lbl_full = f"{lbl}" + (f" ({unidade})" if unidade else "")
            tf_campos[chave] = ft.TextField(
                label=lbl_full,
                value=ini_val,
                bgcolor=CARD, border_color=BD2, focused_border_color=COR,
                label_style=ft.TextStyle(color=SEC, size=10),
                text_style=ft.TextStyle(color=TXT),
                border_radius=8, keyboard_type=ft.KeyboardType.NUMBER,
                height=52,
            )

        row_data, tf_data = campo_data(
            page, "Data", value=_data_ini,
            cor_acento=COR, bgcolor=CARD, border_color=BD2,
        )
        tf_hora = ft.TextField(
            label="Hora (opcional)",
            bgcolor=CARD, border_color=BD2, focused_border_color=COR,
            label_style=ft.TextStyle(color=SEC, size=10),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, height=52,
        )
        txt_erro = ft.Text("", size=11, color=VERM, visible=False)

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        def _salvar(e):
            data_str = (tf_data.value or "").strip()
            if not data_str:
                txt_erro.value   = "Informe a data."
                txt_erro.visible = True
                try: page.update()
                except Exception: pass
                return

            # Salva uma leitura por parâmetro preenchido
            hora_val = (tf_hora.value or "").strip() or None
            salvou = False
            for chave, lbl, unidade, ref in _PARAMS:
                val_str = (tf_campos[chave].value or "").strip().replace(",", ".")
                if not val_str:
                    continue
                try:
                    val_num = float(val_str)
                except ValueError:
                    continue
                salvou = True
                salvar_leitura_marcador({
                    "parametro":    lbl,
                    "categoria":    "Bioimpedancia",
                    "valor":        val_num,
                    "valor_txt":    f"{val_num:.1f}",
                    "unidade":      unidade,
                    "referencia":   ref,
                    "data_medicao": data_str,
                    "hora_medicao": hora_val,
                    "fonte":        "manual",
                    "observacoes":  f"[Sessao] {chave}",
                })

            if not salvou:
                txt_erro.value   = "Preencha ao menos um parametro."
                txt_erro.visible = True
                try: page.update()
                except Exception: pass
                return

            _fechar()
            if on_salvo:
                on_salvo()
            else:
                _carregar()

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

        # Grid 2 colunas de campos
        _chaves = _PARAM_KEYS
        rows_campos = []
        for i in range(0, len(_chaves), 2):
            pair = _chaves[i:i + 2]
            row_items = [ft.Container(content=tf_campos[k], expand=True) for k in pair]
            if len(row_items) == 1:
                row_items.append(ft.Container(expand=True))
            rows_campos.append(ft.Row(row_items, spacing=8))

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("accessibility_new_rounded", size=16, color=COR),
                        ft.Text("Nova Sessão — Bioimpedância", size=14, color=TXT,
                                weight=ft.FontWeight.W_700),
                    ], spacing=8),
                    ft.Container(height=4),
                    ft.Row([
                        ft.Container(content=row_data, expand=True),
                        ft.Container(content=tf_hora, width=110),
                    ], spacing=8),
                    *rows_campos,
                    txt_erro,
                    ft.Container(height=4),
                    ft.Row([btn_cancel, btn_ok], spacing=8,
                           alignment=ft.MainAxisAlignment.CENTER),
                ], spacing=8, tight=True,
                   scroll=ft.ScrollMode.AUTO),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20), width=360,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass

    # ── Lista de sessões ─────────────────────────────────────────

    def _mostrar_lista_sessoes(sessoes):
        area_sess = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

        def _rebuild():
            area_sess.controls.clear()
            for s in sessoes:
                data_disp = _para_display(s["data"])
                items = []
                for chave, lbl, unidade, _ in _PARAMS:
                    if chave in s:
                        v = s[chave]
                        cor_v = _avaliar_cor_param(chave, v)
                        items.append(
                            ft.Text(f"{lbl}: {v:.1f}{' '+unidade if unidade else ''}",
                                    size=11, color=cor_v)
                        )

                card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon("accessibility_new_rounded", size=14, color=COR),
                            ft.Text(data_disp, size=13, color=TXT,
                                    weight=ft.FontWeight.W_600, expand=True),
                            ft.Text(_dias_txt(s["data"]), size=10, color=MUT),
                        ], spacing=6),
                        ft.Container(height=4),
                        ft.Column(items, spacing=3),
                    ], spacing=2),
                    bgcolor=CARD, border_radius=8,
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    border=ft.Border(
                        left=ft.BorderSide(3, COR),
                        top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                        right=ft.BorderSide(1, BD),
                    ),
                )
                area_sess.controls.append(card)

            if not sessoes:
                area_sess.controls.append(
                    ft.Text("Nenhuma sessao registrada.", color=MUT, size=12))
            try: page.update()
            except Exception: pass

        _rebuild()

        btn_voltar = ft.Container(
            content=ft.Icon("arrow_back_rounded", size=20, color=TXT),
            padding=ft.padding.all(8), border_radius=8, ink=True,
        )
        btn_voltar.on_click = lambda e: _mostrar_principal()

        btn_add = ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=16, color=COR),
                ft.Text("Nova Sessao", size=13, color=COR),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_radius=8, ink=True,
        )
        btn_add.on_click = lambda e: _abrir_form(on_salvo=lambda: _mostrar_lista_sessoes(
            _carregar_sessoes()))

        cab_lista = ft.Container(
            content=ft.Row([
                btn_voltar,
                ft.Icon("accessibility_new_rounded", size=14, color=COR),
                ft.Text("Sessoes Registradas", size=15, color=TXT,
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
            ft.Container(content=area_sess,
                         padding=ft.padding.symmetric(horizontal=12, vertical=8),
                         expand=True),
        ], spacing=0, expand=True)

        wrapper.controls.clear()
        wrapper.controls.append(ft.Container(bgcolor=BG, expand=True, content=corpo_lista))
        try: page.update()
        except Exception: pass

    def _carregar_sessoes() -> list[dict]:
        leituras = listar_leituras_marcador(_TERMOS)
        # Agrupa por data
        datas = {}
        for r in leituras:
            d = r.get("data_medicao") or ""
            if d not in datas:
                datas[d] = {"data": d}
            param = (r.get("parametro") or "").lower().replace(" ", "_")
            for chave, lbl, _, _ in _PARAMS:
                if chave in param or lbl.lower().replace(" ", "_") in param:
                    try:
                        datas[d][chave] = float(str(r["valor"]).replace(",", "."))
                    except Exception:
                        pass
        return sorted(datas.values(), key=lambda x: x["data"], reverse=True)

    # ── Carregamento ─────────────────────────────────────────────

    def _carregar():
        area_lista.controls.clear()

        sessoes = _carregar_sessoes()

        if sessoes:
            ult = sessoes[0]
            data_ult = ult["data"]
            imc_v = ult.get("imc")
            gord_v = ult.get("gordura")

            vals_summary = []
            for chave, lbl, unidade, _ in _PARAMS[:4]:
                if chave in ult:
                    v = ult[chave]
                    cor_v = _avaliar_cor_param(chave, v)
                    vals_summary.append(
                        ft.Column([
                            ft.Text(f"{v:.1f}", size=18,
                                    weight=ft.FontWeight.W_900, color=cor_v),
                            ft.Text(f"{lbl}{' ('+unidade+')' if unidade else ''}",
                                    size=9, color=SEC),
                        ], spacing=1,
                           horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                           expand=True)
                    )

            if vals_summary:
                area_lista.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                _label_sec("ULTIMA SESSAO"),
                                ft.Container(expand=True),
                                ft.Text(_dias_txt(data_ult), size=10, color=MUT),
                            ]),
                            ft.Container(height=4),
                            ft.Row(vals_summary, spacing=8),
                        ], spacing=4),
                        bgcolor=CARD, border_radius=8,
                        padding=ft.padding.symmetric(horizontal=14, vertical=12),
                        border=ft.Border(
                            left=ft.BorderSide(3, COR),
                            top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                            right=ft.BorderSide(1, BD),
                        ),
                    )
                )
                area_lista.controls.append(ft.Divider(color=BD2, height=1))

            # Card: histórico de sessões
            sub_txt = f"{len(sessoes)} sessoes  •  {_dias_txt(data_ult)}"
            cor_card = _avaliar_cor_param("gordura", gord_v) if gord_v else COR
            val_display = f"{gord_v:.1f}%" if gord_v else "--"

            def _click_hist(e):
                _mostrar_lista_sessoes(_carregar_sessoes())

            card_hist = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Text(val_display, size=16,
                                        weight=ft.FontWeight.W_900, color=cor_card),
                        width=52, alignment=ft.alignment.Alignment(0, 0),
                    ),
                    ft.Column([
                        ft.Text("Sessoes Registradas", size=12, color=TXT,
                                weight=ft.FontWeight.W_600),
                        ft.Text(sub_txt, size=11, color=SEC),
                        ft.Text("Gordura Corporal + mais", size=10, color=MUT),
                    ], spacing=1, expand=True),
                    ft.Row([
                        ft.Icon("chevron_right_rounded", size=14, color=MUT),
                    ], spacing=4, tight=True),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD, border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border=ft.Border(left=ft.BorderSide(3, cor_card),
                                 top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                                 right=ft.BorderSide(1, BD)),
            )
            card_hist.on_click = _click_hist
            area_lista.controls.append(card_hist)
        else:
            area_lista.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon("accessibility_new_rounded", size=32, color=MUT),
                        ft.Container(height=8),
                        ft.Text("Nenhuma sessao registrada.", color=MUT, size=13),
                        ft.Text("Use o botao Registrar para adicionar.", color=MUT, size=11),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                    padding=ft.padding.symmetric(vertical=32),
                    alignment=ft.alignment.center,
                )
            )

        if _montado[0]:
            try: page.update()
            except Exception: pass

    # ── Layout principal ─────────────────────────────────────────

    area_principal = ft.Column([
        ft.Container(
            content=ft.Row([
                ft.Icon("biotech_rounded", size=12, color=AZUL),
                _label_sec("BIOIMPEDÂNCIA", AZUL),
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
        "Bioimpedância", voltar_fn,
        icone_titulo="accessibility_new_rounded",
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
    return wrapper
