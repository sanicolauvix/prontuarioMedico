# -*- coding: utf-8 -*-
# shared/exame_card.py -- Padrao de exibicao de exames fora da tela_exames
#
# Navegacao em pilha (cada nivel empilha sem fechar o anterior):
#   Hub
#   -> Lista de tipos          (overlay nivel 0)
#      -> Mapa / card unico    (overlay nivel 1)
#         -> Historico         (overlay nivel 2)
#         <- voltar remove nivel 2
#      <- voltar remove nivel 1
#   <- voltar remove nivel 0
#
# grupos = lista de dicts:
#   {
#     "label":      str,
#     "n":          int,
#     "ultimo_val": str,
#     "unidade":    str,
#     "ultima_data": str,       -- YYYY-MM-DD ou DD/MM/AAAA
#     "referencia": str,        -- opcional
#     "cor_val":    str,
#     "historico":  list[dict], -- [{valor, data, unidade, referencia, cor_val}]
#   }

import flet as ft
import math

BG   = "#1A1A2E"; CARD = "#161B22"; BD  = "#21262D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; VERM = "#F85149"
AMAR = "#D29922"; ROXO = "#BC8CFF"


def _parse_float(v):
    try:
        return float(str(v).replace(",", ".").strip())
    except Exception:
        return None


def _para_display(s):
    if s and len(s) >= 10 and s[4:5] == "-":
        import datetime
        try:
            return datetime.datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            pass
    return s or ""


def _pop_overlay(page, ref_list):
    """Remove o overlay no topo da pilha (ultimo da ref_list)."""
    if ref_list and ref_list[-1] in page.overlay:
        page.overlay.remove(ref_list[-1])
        ref_list.pop()
    try: page.update()
    except Exception: pass


# ── Sparkline simples ─────────────────────────────────────────────────────────

def _sparkline(historico, cor, largura=260, altura=80):
    vals = []
    for h in reversed(historico):
        v = _parse_float(h.get("valor"))
        if v is not None:
            vals.append(v)

    if len(vals) < 2:
        return ft.Container(
            content=ft.Text(
                str(vals[0]) if vals else "--", size=28,
                weight=ft.FontWeight.W_900, color=cor,
                text_align=ft.TextAlign.CENTER,
            ),
            height=altura, alignment=ft.alignment.Alignment(0, 0),
        )

    v_min   = min(vals)
    v_max   = max(vals)
    v_range = (v_max - v_min) or 1.0
    n       = len(vals)
    pad_x, pad_y = 8, 8
    w_util  = largura - 2 * pad_x
    h_util  = altura  - 2 * pad_y

    def _x(i): return pad_x + i * w_util / (n - 1)
    def _y(v): return pad_y + (1 - (v - v_min) / v_range) * h_util

    controls = []
    for i in range(n - 1):
        x1, y1 = _x(i),     _y(vals[i])
        x2, y2 = _x(i + 1), _y(vals[i + 1])
        dx, dy = x2 - x1, y2 - y1
        length = (dx ** 2 + dy ** 2) ** 0.5
        angle  = math.radians(math.degrees(math.atan2(dy, dx)))
        controls.append(ft.Container(
            width=length, height=2,
            bgcolor=ft.Colors.with_opacity(0.55, cor),
            border_radius=1,
            left=x1, top=y1 - 1,
            rotate=ft.Rotate(angle=angle,
                             alignment=ft.alignment.center_left),
        ))
    for i, v in enumerate(vals):
        x, y = _x(i), _y(v)
        controls.append(ft.Container(
            width=6, height=6, border_radius=3,
            bgcolor=cor, left=x - 3, top=y - 3,
        ))

    return ft.Container(
        content=ft.Stack(controls, width=largura, height=altura),
        width=largura, height=altura,
    )


# ── Helpers de overlay ────────────────────────────────────────────────────────

def _btn_voltar(label, fn):
    c = ft.Container(
        content=ft.Row([
            ft.Icon("arrow_back_rounded", size=14, color=AZUL),
            ft.Text(label, size=12, color=AZUL, weight=ft.FontWeight.W_600),
        ], spacing=4, tight=True),
        ink=True,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
    )
    c.on_click = lambda e: fn()
    return c


def _overlay_container(page, conteudo, pilha, fn_fechar_fundo=None):
    """
    Monta um overlay sobre fundo semi-transparente.
    Clicar no fundo chama fn_fechar_fundo se fornecido; caso contrario nao fecha.
    """
    w = min((page.width  or 380) - 32, 400)
    h = min((page.height or 700) * 0.82, 560)

    inner = ft.Container(
        content=conteudo,
        bgcolor=BG, border_radius=16,
        padding=ft.padding.symmetric(horizontal=16, vertical=16),
        width=w, height=h,
    )
    outer = ft.Container(
        content=inner,
        bgcolor=ft.Colors.with_opacity(0.60, "#000000"),
        alignment=ft.alignment.Alignment(0, 0),
        expand=True,
    )
    if fn_fechar_fundo:
        outer.on_click = lambda e: fn_fechar_fundo()
    pilha.append(outer)
    page.overlay.append(outer)
    try: page.update()
    except Exception: pass


# ── Nivel 2: Historico ────────────────────────────────────────────────────────

def _abrir_historico(page, grupo, cor, pilha):
    hist  = grupo.get("historico", [])
    label = grupo.get("label", "Historico")
    uni   = grupo.get("unidade", "")

    def _voltar():
        _pop_overlay(page, pilha)

    corpo = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
    for h in hist:
        val   = h.get("valor", "--")
        data  = _para_display(h.get("data", ""))
        ref   = h.get("referencia", "")
        cor_v = h.get("cor_val") or cor
        corpo.controls.append(ft.Container(
            content=ft.Row([
                ft.Text(data, size=10, color=MUT, expand=True),
                ft.Text(f"{val} {uni}", size=13, color=cor_v,
                        weight=ft.FontWeight.W_700),
                ft.Text(f"ref: {ref}" if ref else "", size=9, color=MUT),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            border=ft.Border(bottom=ft.BorderSide(1, BD)),
            padding=ft.padding.symmetric(horizontal=4, vertical=8),
        ))

    if not hist:
        corpo.controls.append(ft.Container(
            content=ft.Text("Sem registros", size=12, color=MUT),
            padding=ft.padding.symmetric(vertical=20),
            alignment=ft.alignment.Alignment(0, 0),
        ))

    conteudo = ft.Column([
        ft.Row([_btn_voltar(label, _voltar),
                ft.Text("Historico", size=14, color=cor,
                        weight=ft.FontWeight.W_700, expand=True)],
               spacing=4),
        ft.Divider(color=BD, height=1),
        corpo,
    ], spacing=0, expand=True)

    _overlay_container(page, conteudo, pilha)


# ── Nivel 1: Mapa (sparkline ou card unico) ───────────────────────────────────

def _abrir_mapa(page, grupo, cor, titulo, pilha):
    n     = grupo.get("n", 0)
    val   = grupo.get("ultimo_val", "--")
    uni   = grupo.get("unidade", "")
    data  = _para_display(grupo.get("ultima_data", ""))
    ref   = grupo.get("referencia", "")
    cor_v = grupo.get("cor_val", cor)
    hist  = grupo.get("historico", [])
    w_card = min((page.width or 380) - 64, 340)

    def _voltar():
        _pop_overlay(page, pilha)

    def _abrir_hist():
        _abrir_historico(page, grupo, cor, pilha)

    if n == 1:
        # card direto: valor + data + referencia
        linhas = [
            ft.Row([
                ft.Text(val, size=36, weight=ft.FontWeight.W_900, color=cor_v),
                ft.Container(
                    content=ft.Text(uni, size=12, color=SEC),
                    padding=ft.padding.only(top=18),
                ),
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START),
        ]
        if data:
            linhas.append(ft.Text(data, size=11, color=SEC))
        if ref:
            linhas.append(ft.Row([
                ft.Text("Ref:", size=10, color=MUT),
                ft.Text(ref, size=10, color=MUT),
            ], spacing=4))
        corpo_mapa = ft.Column(linhas, spacing=6, tight=True)

    else:
        # sparkline + botao historico
        spark = _sparkline(hist, cor_v, largura=w_card, altura=80)

        btn_hist = ft.Container(
            content=ft.Row([
                ft.Icon("history_rounded", size=13, color=AZUL),
                ft.Text("Historico", size=11, color=AZUL,
                        weight=ft.FontWeight.W_600),
                ft.Text(f"({n})", size=10, color=MUT),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border_radius=8,
            bgcolor=ft.Colors.with_opacity(0.10, AZUL),
            border=ft.border.all(1, ft.Colors.with_opacity(0.25, AZUL)),
            ink=True,
        )
        btn_hist.on_click = lambda e: _abrir_hist()

        corpo_mapa = ft.Column([
            ft.Row([
                ft.Text(val, size=26, weight=ft.FontWeight.W_900, color=cor_v),
                ft.Container(
                    content=ft.Text(uni, size=11, color=SEC),
                    padding=ft.padding.only(top=12),
                ),
                ft.Container(expand=True),
                ft.Text(data, size=10, color=MUT),
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START),
            spark,
            ft.Row([ft.Container(expand=True), btn_hist]),
        ], spacing=6, tight=True)

    conteudo = ft.Column([
        ft.Row([_btn_voltar(titulo, _voltar),
                ft.Text(grupo["label"], size=14, color=cor,
                        weight=ft.FontWeight.W_700, expand=True)],
               spacing=4),
        ft.Divider(color=BD, height=1),
        ft.Container(height=8),
        corpo_mapa,
    ], spacing=0, tight=True)

    _overlay_container(page, conteudo, pilha)


# ── Nivel 0: Lista de tipos ───────────────────────────────────────────────────

def abrir_overlay_exame(page, titulo, cor, grupos, icone="biotech_rounded"):
    """
    Ponto de entrada. Abre a lista de tipos de exame.
    Cada nivel empilha sobre o anterior; voltar remove so o topo.
    """
    pilha = []   # referencia compartilhada entre os 3 niveis

    def _voltar_lista():
        _pop_overlay(page, pilha)

    def _abrir_detalhe(grupo):
        _abrir_mapa(page, grupo, cor, titulo, pilha)

    corpo = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
    for grupo in grupos:
        n     = grupo.get("n", 0)
        val   = grupo.get("ultimo_val", "--")
        uni   = grupo.get("unidade", "")
        data  = _para_display(grupo.get("ultima_data", ""))
        cor_v = grupo.get("cor_val", cor)

        item = ft.Container(
            content=ft.Row([
                ft.Container(width=4, height=36, bgcolor=cor_v, border_radius=2),
                ft.Column([
                    ft.Text(grupo["label"], size=13, color=TXT,
                            weight=ft.FontWeight.W_600),
                    ft.Text(f"{n}x  •  {data}" if n > 1 else data,
                            size=10, color=MUT),
                ], spacing=2, expand=True),
                ft.Text(f"{val} {uni}", size=13, color=cor_v,
                        weight=ft.FontWeight.W_700),
                ft.Icon("chevron_right_rounded", size=16, color=MUT),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=CARD,
            border=ft.Border(bottom=ft.BorderSide(1, BD)),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            ink=True,
        )
        item.on_click = lambda e, g=grupo: _abrir_detalhe(g)
        corpo.controls.append(item)

    if not grupos:
        corpo.controls.append(ft.Container(
            content=ft.Text("Nenhum dado registrado", size=12, color=MUT),
            padding=ft.padding.symmetric(vertical=20),
            alignment=ft.alignment.Alignment(0, 0),
        ))

    conteudo = ft.Column([
        ft.Row([
            _btn_voltar("Hub", _voltar_lista),
            ft.Icon(icone, size=14, color=cor),
            ft.Text(titulo, size=14, color=cor,
                    weight=ft.FontWeight.W_700, expand=True),
        ], spacing=6),
        ft.Divider(color=BD, height=1),
        corpo,
    ], spacing=0, expand=True)

    _overlay_container(page, conteudo, pilha)
