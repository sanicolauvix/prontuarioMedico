# -*- coding: utf-8 -*-
# Prontuario | utils/layout_medico.py
# Layout desktop do hub medico — compartilhado por main_medico.py e main_web.py
import flet as ft

from versao import APP_VERSAO

BG    = "#0D1117"; CARD  = "#161B22"; BD   = "#21262D"
TXT   = "#E6EDF3"; SEC   = "#8B949E"; MUT  = "#484F58"
AZUL  = "#58A6FF"; VERD  = "#3FB950"; VERM = "#FF4444"
ROXO  = "#BC8CFF"; AMAR  = "#D29922"


def montar_layout_desktop(page: ft.Page, pw: int, wrapper, nav_fn,
                          modo_medico: bool = True) -> None:
    """
    Monta o layout desktop do hub medico:
    - Coluna esquerda: grade 2x2 (paciente | monitor vital / resumo | monitor vital)
    - Coluna direita: silhueta + cards de sistemas
    """
    partes = getattr(wrapper, "_hub_partes", None)
    if partes is None:
        nav_fn(wrapper)
        return

    from telas.silhueta_orgaos import criar_silhueta

    ph = int(page.height or 700)
    altura_util = ph - 28 - 56 - 24 - 18 - 58 - 8

    larg_prop = int(altura_util * 644 / 551)
    larg_max  = pw - int(pw / 2)
    larg_sil  = min(larg_prop, max(larg_max - 140, 300))

    def _on_orgao(oid):
        pass

    silhueta = criar_silhueta(page, on_orgao_click=_on_orgao,
                              largura=larg_sil, mostrar_borda=False)

    monitor  = partes.get("monitor_widget")
    resumo   = partes.get("resumo_widget")
    cards_sis = partes.get("cards_sistemas", [])

    # tornar segunda linha do resumo visivel
    try:
        if resumo and len(resumo.controls) > 1:
            resumo.controls[1].visible = True
    except Exception:
        pass

    # dados do paciente
    try:
        from dados.model_prontuario import carregar_perfil
        pac = carregar_perfil() or {}
    except Exception:
        pac = {}

    nome_pac  = pac.get("nome") or "Paciente"
    nasc      = pac.get("data_nasc") or ""
    sexo      = pac.get("sexo") or ""
    tipo_sang = pac.get("tipo_sanguineo") or ""
    peso      = pac.get("peso")
    altura_p  = pac.get("altura")
    foto      = pac.get("foto_url") or pac.get("foto_path") or ""

    try:
        from datetime import date
        nasc_d    = date.fromisoformat(nasc[:10])
        hoje      = date.today()
        anos      = hoje.year - nasc_d.year - (
            (hoje.month, hoje.day) < (nasc_d.month, nasc_d.day))
        idade_str = f"{anos} anos"
        nasc_fmt  = nasc_d.strftime("%d/%m/%Y")
    except Exception:
        idade_str = ""
        nasc_fmt  = nasc

    sexo_label = {"M": "Masculino", "F": "Feminino"}.get(sexo, sexo)

    import os as _os
    if foto and _os.path.isfile(foto):
        avatar = ft.Container(
            content=ft.Image(src=foto, width=60, height=60, fit=ft.ImageFit.COVER),
            width=60, height=60, border_radius=30,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            border=ft.border.all(2, AZUL),
        )
    else:
        initials = "".join(w[0].upper() for w in nome_pac.split()[:2] if w)
        avatar = ft.Container(
            content=ft.Text(initials or "P", size=20,
                            weight=ft.FontWeight.W_700, color=AZUL),
            width=60, height=60, border_radius=30,
            bgcolor=ft.Colors.with_opacity(0.12, AZUL),
            border=ft.border.all(2, ft.Colors.with_opacity(0.40, AZUL)),
            alignment=ft.alignment.center,
        )

    def _linha(label, valor):
        if not valor:
            return ft.Container(height=0)
        return ft.Row([
            ft.Text(label, size=10, color=SEC, width=70),
            ft.Text(str(valor), size=11, color=TXT, weight=ft.FontWeight.W_600),
        ], spacing=6)

    h_quad = int(altura_util / 2)

    def _quadrante(titulo, cor_titulo, conteudo, icone="", centralizar=False):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(icone, size=12, color=cor_titulo) if icone else ft.Container(),
                    ft.Text(titulo, size=10, weight=ft.FontWeight.W_700, color=cor_titulo),
                ], spacing=6),
                ft.Container(height=4),
                ft.Container(
                    content=conteudo, expand=True,
                    alignment=ft.alignment.center if centralizar else ft.alignment.top_left,
                ),
            ], spacing=0, expand=True,
               horizontal_alignment=ft.CrossAxisAlignment.CENTER if centralizar
               else ft.CrossAxisAlignment.START),
            bgcolor=CARD, border_radius=10,
            padding=ft.padding.all(8),
            border=ft.border.all(1, BD),
            expand=True, height=h_quad,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )

    # quadrante 1: PACIENTE (medico) ou CLAUDIA (paciente) — troca por visibilidade
    q_paciente = _quadrante("PACIENTE", AZUL, ft.Column([
        ft.Row([avatar, ft.Column([
            ft.Text(nome_pac, size=12, color=TXT, weight=ft.FontWeight.W_700),
            ft.Text(idade_str, size=10, color=SEC) if idade_str else ft.Container(),
        ], spacing=2, tight=True, expand=True)], spacing=8),
        ft.Container(height=4),
        _linha("Nascimento", nasc_fmt),
        _linha("Sexo",       sexo_label),
        _linha("Sangue",     tipo_sang),
        _linha("Peso",       f"{peso} kg" if peso else ""),
        _linha("Altura",     f"{altura_p} cm" if altura_p else ""),
    ], spacing=3, tight=True, scroll=ft.ScrollMode.AUTO),
    icone="person_rounded")
    q_paciente.visible = modo_medico

    # card Claudia para o paciente
    claudia_widget = partes.get("claudia_card")
    q_claudia = _quadrante("CLAUDIA", ROXO,
        claudia_widget if claudia_widget else ft.Column([
            ft.Row([
                ft.Container(
                    content=ft.Text("C", size=20, weight=ft.FontWeight.W_900, color=ROXO),
                    width=44, height=44, border_radius=22,
                    bgcolor=ft.Colors.with_opacity(0.10, ROXO),
                    border=ft.border.all(2, ROXO),
                    alignment=ft.alignment.center,
                ),
                ft.Column([
                    ft.Text("Claudia", size=13, color=TXT, weight=ft.FontWeight.W_700),
                    ft.Text("Toque para conversar", size=10, color=MUT),
                ], spacing=2, tight=True, expand=True),
            ], spacing=10),
        ], spacing=0, tight=True),
    icone="psychology_rounded")
    q_claudia.visible = not modo_medico

    # container que exibe um ou outro no mesmo espaco
    q1 = ft.Container(
        content=ft.Stack([q_paciente, q_claudia]),
        expand=True, height=h_quad,
    )

    col_pac_resumo = ft.Column([
        q1,
        _quadrante("RESUMO DO DIA", AMAR,
                   ft.Container(content=resumo, expand=True),
                   icone="insights_rounded"),
    ], spacing=8, expand=True)

    col_monitor = ft.Column([
        _quadrante("MONITOR VITAL", "#FF7675",
                   ft.Container(content=monitor, expand=True),
                   icone="monitor_heart_rounded", centralizar=True),
    ], spacing=0, expand=True)

    grade_2x2 = ft.Row([col_pac_resumo, col_monitor], spacing=8, expand=True)

    # cards de sistemas ao lado da silhueta
    h_card = int((altura_util - 8 * max(len(cards_sis) - 1, 0)) / len(cards_sis)) \
             if cards_sis else 100
    col_sistemas = ft.Column(
        [ft.Container(content=c, height=h_card, width=120,
                      clip_behavior=ft.ClipBehavior.HARD_EDGE,
                      border_radius=8) for c in cards_sis],
        spacing=8, tight=True,
    ) if cards_sis else ft.Container()

    area_central = ft.Row([
        ft.Container(
            content=grade_2x2,
            width=int(pw / 2),
            expand=False,
            bgcolor=BG,
            border=ft.border.only(right=ft.BorderSide(1, BD)),
            padding=ft.padding.only(left=8, right=8, top=8),
        ),
        ft.Container(
            expand=True, bgcolor=BG,
            padding=ft.padding.only(left=4, right=4, top=4),
            content=ft.Column([
                ft.Text("Clique no Órgão que Deseja Pesquisar",
                        size=11, color=SEC, text_align="center",
                        weight=ft.FontWeight.W_600),
                ft.Container(height=4),
                ft.Row([
                    ft.Container(
                        content=silhueta,
                        alignment=ft.alignment.top_center,
                        height=altura_util,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    ),
                    col_sistemas,
                ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.START),
            ], horizontal_alignment=ft.CrossAxisAlignment.START,
               spacing=0, tight=True),
        ),
    ], expand=True, spacing=0,
       vertical_alignment=ft.CrossAxisAlignment.START)

    # versao no cabecalho
    partes["versao"].visible = False
    header = partes["header"]
    try:
        # evitar duplicar versao se ja foi adicionada
        ultimo = header.content.controls[-1]
        if not (isinstance(ultimo, ft.Text) and ultimo.value and ultimo.value.startswith("v")):
            header.content.controls.append(
                ft.Text(f"v{APP_VERSAO}", size=10, color=MUT)
            )
    except Exception:
        pass

    rodape = ft.Column([partes["row_sync"], partes["nav_bar"]], spacing=0)

    layout = ft.Column([
        partes["spacer_topo"],
        header,
        ft.Container(content=area_central, expand=True, bgcolor=BG),
        rodape,
    ], spacing=0, expand=True)

    nav_fn(ft.Container(content=layout, expand=True, bgcolor=BG))
