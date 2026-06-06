# -*- coding: utf-8 -*-
# Prontuario | main_test_silhueta.py
# Tela de teste do componente silhueta com orgaos clicaveis
# Rodar: python main_test_silhueta.py
# NAO faz parte do APK -- apenas para desenvolvimento desktop

import flet as ft

BG   = "#0D1117"; CARD = "#161B22"; BORDA = "#21262D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT   = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; VERM  = "#FF4545"
ROXO = "#BC8CFF"; AMAR = "#D29922"; LRNJ  = "#F0883E"
CIAN = "#4ECDC4"; VIOL = "#A29BFE"; ROSA  = "#FDCB6E"

# Mapa orgao -> info de exibicao no painel lateral
_INFO_ORGAOS = {
    "tireoide":        {"label": "Tireoide",     "cor": VIOL, "sistema": "Endocrino",      "icone": "psychology_alt_rounded"},
    "coracao":         {"label": "Coracao",       "cor": VERM, "sistema": "Cardiovascular", "icone": "favorite_rounded"},
    "pulmao_esq":      {"label": "Pulmao Esq",   "cor": AZUL, "sistema": "Respiratorio",   "icone": "air_rounded"},
    "pulmao_dir":      {"label": "Pulmao Dir",   "cor": AZUL, "sistema": "Respiratorio",   "icone": "air_rounded"},
    "figado":          {"label": "Figado",        "cor": LRNJ, "sistema": "Digestivo",      "icone": "science_rounded"},
    "vesicula":        {"label": "Vesicula",      "cor": ROSA, "sistema": "Digestivo",      "icone": "water_drop_rounded"},
    "estomago":        {"label": "Estomago",      "cor": VERD, "sistema": "Digestivo",      "icone": "lunch_dining_rounded"},
    "baco":            {"label": "Baco",          "cor": ROXO, "sistema": "Imunologico",    "icone": "hexagon_rounded"},
    "pancreas":        {"label": "Pancreas",      "cor": ROSA, "sistema": "Endocrino",      "icone": "water_drop_rounded"},
    "rim_esq":         {"label": "Rim Esq",       "cor": CIAN, "sistema": "Urinario",       "icone": "water_drop_rounded"},
    "rim_dir":         {"label": "Rim Dir",       "cor": CIAN, "sistema": "Urinario",       "icone": "water_drop_rounded"},
    "intestino":       {"label": "Intestinos",    "cor": VERD, "sistema": "Digestivo",      "icone": "view_timeline_rounded"},
    "bexiga":          {"label": "Bexiga",        "cor": AZUL, "sistema": "Urinario",       "icone": "water_drop_rounded"},
    "prostata":        {"label": "Prostata",      "cor": ROXO, "sistema": "Urinario",       "icone": "circle_rounded"},
}


def main(page: ft.Page):
    page.title    = "Silhueta Orgaos -- Teste"
    page.bgcolor  = BG
    page.padding  = 0
    page.theme_mode = ft.ThemeMode.DARK

    from telas.silhueta_orgaos import criar_silhueta, ORGAOS

    # ── Painel de info (lado direito ou abaixo) ───────────────────────
    txt_orgao   = ft.Text("--", size=18, color=TXT, weight=ft.FontWeight.W_700)
    txt_sistema = ft.Text("--", size=11, color=SEC)
    icone_orgao = ft.Icon("touch_app_rounded", size=28, color=MUT)
    log_col     = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)

    painel = ft.Container(
        content=ft.Column([
            ft.Text("ORGAO SELECIONADO", size=9, color=MUT,
                    weight=ft.FontWeight.W_700),
            ft.Container(height=4),
            ft.Row([
                icone_orgao,
                ft.Column([
                    txt_orgao,
                    txt_sistema,
                ], spacing=2, tight=True),
            ], spacing=10),
            ft.Divider(color=BORDA, height=16),
            ft.Text("LOG DE CLIQUES", size=9, color=MUT,
                    weight=ft.FontWeight.W_700),
            ft.Container(height=4),
            log_col,
        ], spacing=0, tight=True),
        bgcolor=CARD,
        border_radius=12,
        padding=ft.padding.all(16),
        border=ft.border.all(1, BORDA),
        expand=True,
    )

    _click_count = [0]

    def on_orgao(nome_id: str):
        info = _INFO_ORGAOS.get(nome_id, {"label": nome_id, "cor": SEC,
                                           "sistema": "?", "icone": "help_rounded"})
        cor = info["cor"]

        txt_orgao.value   = info["label"]
        txt_orgao.color   = cor
        txt_sistema.value = f"Sistema: {info['sistema']}"
        icone_orgao.name  = info["icone"]
        icone_orgao.color = cor

        _click_count[0] += 1
        entrada = ft.Container(
            content=ft.Row([
                ft.Container(width=6, height=6, border_radius=3, bgcolor=cor),
                ft.Text(f"#{_click_count[0]:02d}  {info['label']}",
                        size=11, color=TXT, expand=True),
                ft.Text(info["sistema"], size=9, color=SEC),
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            border=ft.Border(bottom=ft.BorderSide(1, BORDA)),
            padding=ft.padding.symmetric(horizontal=4, vertical=5),
        )
        log_col.controls.insert(0, entrada)
        if len(log_col.controls) > 20:
            log_col.controls.pop()

        try: page.update()
        except Exception: pass

    # ── Silhueta ──────────────────────────────────────────────────────
    larg_silhueta = 580
    _debug = [True]   # True = mostra bordas + linhas divisoras

    silhueta = criar_silhueta(
        page,
        on_orgao_click=on_orgao,
        largura=larg_silhueta,
        mostrar_borda=_debug[0],
    )

    # ── Toggle labels ─────────────────────────────────────────────────
    _labels_on = [True]

    def _toggle_labels(e):
        _debug[0] = not _debug[0]
        nova = criar_silhueta(
            page,
            on_orgao_click=on_orgao,
            largura=larg_silhueta,
            mostrar_borda=_debug[0],
        )
        area_silhueta.content = ft.Column([
            ft.GestureDetector(content=nova, on_tap_down=_on_img_click),
            ft.Container(height=6),
            ft.Text("CLICKS (orig = pixels imagem 644x551):", size=9, color=MUT),
            *txt_log,
        ], spacing=2, tight=True)
        btn_toggle.content.controls[1].value = (
            "Ocultar bordas" if _debug[0] else "Mostrar bordas"
        )
        try: page.update()
        except Exception: pass

    btn_toggle = ft.Container(
        content=ft.Row([
            ft.Icon("label_rounded", size=14, color=AZUL),
            ft.Text("Ocultar labels", size=12, color=AZUL),
        ], spacing=4, tight=True),
        bgcolor=ft.Colors.with_opacity(0.10, AZUL),
        border=ft.border.all(1, ft.Colors.with_opacity(0.35, AZUL)),
        border_radius=8, ink=True,
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
    )
    btn_toggle.on_click = _toggle_labels

    _log_lines = ["--", "--", "--", "--"]
    _log_idx   = [0]
    txt_log = [
        ft.Text("--", size=10, color=AMAR, selectable=True),
        ft.Text("--", size=10, color=AMAR, selectable=True),
        ft.Text("--", size=10, color=AMAR, selectable=True),
        ft.Text("--", size=10, color=AMAR, selectable=True),
    ]

    def _on_img_click(e: ft.TapEvent):
        escala = 580 / 644
        x_orig = int(e.local_x / escala)
        y_orig = int(e.local_y / escala)
        msg = f"#{_log_idx[0]+1}  tela=({int(e.local_x)},{int(e.local_y)})  orig=({x_orig},{y_orig})"
        idx = _log_idx[0] % 4
        txt_log[idx].value = msg
        _log_idx[0] += 1
        print(msg)
        try: page.update()
        except Exception: pass

    img_clicavel = ft.GestureDetector(
        content=silhueta,
        on_tap_down=_on_img_click,
    )

    area_silhueta = ft.Container(content=ft.Column([
        img_clicavel,
        ft.Container(height=6),
        ft.Row([
            ft.Text("CLICKS (orig = pixels imagem 679x710):", size=9, color=MUT, expand=True),
            ft.Container(
                content=ft.Text("Limpar", size=9, color=VERM),
                ink=True,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border_radius=6,
                bgcolor=ft.Colors.with_opacity(0.10, VERM),
                on_click=lambda e: _limpar_log(),
            ),
        ], spacing=4),
        *txt_log,
    ], spacing=2, tight=True))

    def _limpar_log():
        for t in txt_log:
            t.value = "--"
        _log_idx[0] = 0
        try: page.update()
        except Exception: pass

    # ── Layout principal ──────────────────────────────────────────────
    cabecalho = ft.Container(
        content=ft.Row([
            ft.Icon("accessibility_new_rounded", size=18, color=AZUL),
            ft.Text("Silhueta Orgaos -- TESTE", size=15, color=TXT,
                    weight=ft.FontWeight.W_700, expand=True),
            btn_toggle,
        ], spacing=10),
        bgcolor=CARD,
        border=ft.Border(bottom=ft.BorderSide(1, BORDA)),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
    )

    corpo = ft.Row([
        ft.Container(
            content=ft.Column([
                area_silhueta,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               alignment=ft.MainAxisAlignment.CENTER),
            padding=ft.padding.all(16),
        ),
        painel,
    ], spacing=0, expand=True,
       vertical_alignment=ft.CrossAxisAlignment.START)

    page.add(ft.Column([
        cabecalho,
        corpo,
    ], spacing=0, expand=True))


ft.app(target=main)
