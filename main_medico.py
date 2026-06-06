# -*- coding: utf-8 -*-
# Prontuario | main_medico.py -- entry point web para visao do medico
import flet as ft
import os
import sys
import threading

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from versao import APP_VERSAO

ACENTO = "#BC8CFF"
BG     = "#0D1117"
CARD   = "#161B22"
BD     = "#21262D"
TXT    = "#E6EDF3"
MUT    = "#8B949E"
SEC    = "#8B949E"
AZUL   = "#58A6FF"


def main(page: ft.Page):
    page.title      = "Koios — Visao Medico"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = BG
    page.padding    = 0
    page.window_maximized = True

    _hub_wrapper   = [None]
    _layout_feito  = [False]

    def _nav(tela):
        page.controls.clear()
        page.controls.append(tela)
        try: page.update()
        except Exception: pass

    def _splash():
        return ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Container(expand=True),
                ft.Row([ft.ProgressRing(color=ACENTO)],
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=12),
                ft.Row([ft.Text("Carregando...", size=13, color=MUT)],
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(expand=True),
            ], expand=True),
        )

    _nav(_splash())

    def _montar_layout_desktop(pw: int):
        """
        Layout:
        ┌─────────────────────────────────────────┐
        │  CABEÇALHO (tela toda)                  │
        ├──────────────────┬──────────────────────┤
        │  CONTEÚDO HUB   │    SILHUETA           │
        │  (esquerda)      │    (centralizada)     │
        ├──────────────────┴──────────────────────┤
        │  RODAPÉ (tela toda)                     │
        └─────────────────────────────────────────┘
        """
        wrapper = _hub_wrapper[0]
        if wrapper is None:
            return

        partes = getattr(wrapper, "_hub_partes", None)
        if partes is None:
            _nav(wrapper)
            return

        from telas.silhueta_orgaos import criar_silhueta

        # altura util = altura total - spacer(28) - header(56) - backup(24) - versao(18) - navbar(58) - margem(8)
        ph = int(page.height or 700)
        altura_util = ph - 28 - 56 - 24 - 18 - 58 - 8
        # largura proporcional 644:551 para caber na altura util
        larg_prop = int(altura_util * 644 / 551)
        larg_max  = pw - 480
        larg_sil  = min(larg_prop, max(larg_max, 300))

        def _on_orgao(oid):
            pass  # TODO: navegar para tela do orgao

        silhueta = criar_silhueta(page, on_orgao_click=_on_orgao,
                                  largura=larg_sil, mostrar_borda=False)

        # card do paciente com foto
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
                content=ft.Image(src=foto, width=72, height=72,
                                 fit=ft.ImageFit.COVER),
                width=72, height=72, border_radius=36,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                border=ft.border.all(2, AZUL),
            )
        else:
            initials = "".join(w[0].upper() for w in nome_pac.split()[:2] if w)
            avatar = ft.Container(
                content=ft.Text(initials or "P", size=24,
                                weight=ft.FontWeight.W_700, color=AZUL),
                width=72, height=72, border_radius=36,
                bgcolor=ft.Colors.with_opacity(0.12, AZUL),
                border=ft.border.all(2, ft.Colors.with_opacity(0.40, AZUL)),
                alignment=ft.alignment.center,
            )

        def _linha_pac(label, valor):
            if not valor:
                return ft.Container(height=0)
            return ft.Row([
                ft.Text(label, size=10, color=SEC, width=70),
                ft.Text(str(valor), size=11, color=TXT,
                        weight=ft.FontWeight.W_600),
            ], spacing=6)

        card_paciente = ft.Container(
            content=ft.Column([
                ft.Row([
                    avatar,
                    ft.Column([
                        ft.Text(nome_pac, size=14, color=TXT,
                                weight=ft.FontWeight.W_700),
                        ft.Text(idade_str, size=11, color=SEC) if idade_str
                        else ft.Container(height=0),
                    ], spacing=2, tight=True, expand=True),
                ], spacing=12),
                ft.Container(height=8),
                ft.Container(height=1, bgcolor="#21262D"),
                ft.Container(height=8),
                _linha_pac("Nascimento", nasc_fmt),
                _linha_pac("Sexo",       sexo_label),
                _linha_pac("Sangue",     tipo_sang),
                _linha_pac("Peso",       f"{peso} kg" if peso else ""),
                _linha_pac("Altura",     f"{altura_p} cm" if altura_p else ""),
            ], spacing=4, tight=True),
            bgcolor="#161B22",
            border_radius=10,
            padding=ft.padding.all(14),
            margin=ft.margin.only(bottom=8),
        )

        # remover card do paciente duplicado do hub (primeiro item do area_conteudo)
        area_hub = partes["area"]
        if area_hub.controls and len(area_hub.controls) > 0:
            # o primeiro controle do area e o container com o layout desktop
            # que por sua vez tem a row com col_esq contendo card_claudia
            # simplesmente ocultamos o card do paciente do hub
            try:
                primeiro = area_hub.controls[0]
                # navegar ate col_esq e remover o card do paciente
                row = primeiro.content
                if hasattr(row, "controls") and len(row.controls) > 0:
                    col_esq = row.controls[0].content
                    if hasattr(col_esq, "controls") and len(col_esq.controls) > 0:
                        col_esq.controls[0].visible = False
            except Exception:
                pass

        # altura de cada quadrante = metade da area util
        h_quad = int(altura_util / 2)
        w_quad = int(pw / 4)  # cada quadrante = metade da metade da tela

        monitor  = partes.get("monitor_widget")
        resumo   = partes.get("resumo_widget")
        sistemas = partes.get("sistemas_widget")

        # tornar segunda linha do resumo visivel no desktop medico
        try:
            if resumo and len(resumo.controls) > 1:
                resumo.controls[1].visible = True
        except Exception:
            pass

        def _quadrante(titulo, cor_titulo, conteudo, icone="", centralizar=False):
            return ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(icone, size=12, color=cor_titulo) if icone else ft.Container(),
                        ft.Text(titulo, size=10, weight=ft.FontWeight.W_700, color=cor_titulo),
                    ], spacing=6),
                    ft.Container(height=6),
                    ft.Container(
                        content=conteudo,
                        expand=True,
                        alignment=ft.alignment.center if centralizar else ft.alignment.top_left,
                    ),
                ], spacing=0, expand=True,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER if centralizar else ft.CrossAxisAlignment.START),
                bgcolor=CARD,
                border_radius=10,
                padding=ft.padding.all(8),
                border=ft.border.all(1, BD),
                expand=True,
                height=h_quad,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
            )

        cards_sis = partes.get("cards_sistemas", [])

        # coluna esquerda: PACIENTE (topo) + RESUMO (baixo)
        col_pac_resumo = ft.Column([
            _quadrante("PACIENTE", AZUL, ft.Column([
                ft.Row([avatar, ft.Column([
                    ft.Text(nome_pac, size=13, color=TXT, weight=ft.FontWeight.W_700),
                    ft.Text(idade_str, size=10, color=SEC) if idade_str else ft.Container(),
                ], spacing=2, tight=True, expand=True)], spacing=10),
                ft.Container(height=6),
                _linha_pac("Nascimento", nasc_fmt),
                _linha_pac("Sexo",       sexo_label),
                _linha_pac("Sangue",     tipo_sang),
                _linha_pac("Peso",       f"{peso} kg" if peso else ""),
                _linha_pac("Altura",     f"{altura_p} cm" if altura_p else ""),
            ], spacing=4, tight=True, scroll=ft.ScrollMode.AUTO),
            icone="person_rounded"),
            _quadrante("RESUMO DO DIA", ACENTO,
                       ft.Container(content=resumo, expand=True),
                       icone="insights_rounded"),
        ], spacing=8, expand=True)

        # coluna direita: MONITOR VITAL expandido (ocupa tudo)
        col_monitor = ft.Column([
            _quadrante("MONITOR VITAL", "#FF7675",
                       ft.Container(content=monitor, expand=True),
                       icone="monitor_heart_rounded",
                       centralizar=True),
        ], spacing=0, expand=True)

        grade_2x2 = ft.Row([
            col_pac_resumo,
            col_monitor,
        ], spacing=8, expand=True)

        col_esq_content = grade_2x2

        # cards de sistemas empilhados verticalmente ao lado da silhueta
        h_card_sis = int((altura_util - 8 * (len(cards_sis) - 1)) / len(cards_sis)) if cards_sis else 100
        col_sistemas = ft.Column(
            [ft.Container(
                content=c,
                height=h_card_sis,
                width=120,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                border_radius=8,
             ) for c in cards_sis],
            spacing=8, tight=True,
        ) if cards_sis else ft.Container()

        # area central: esquerda=hub | direita=silhueta
        area_central = ft.Row([
            # esquerda: card paciente + conteudo hub (metade da tela)
            ft.Container(
                content=col_esq_content,
                width=int(pw / 2),
                expand=False,
                bgcolor=BG,
                border=ft.border.only(right=ft.BorderSide(1, BD)),
                padding=ft.padding.only(left=16, right=16),
            ),
            # direita: silhueta + cards de sistemas ao lado
            ft.Container(
                expand=True,
                bgcolor=BG,
                padding=ft.padding.only(left=4, right=4, top=4, bottom=0),
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

        rodape = ft.Column([
            partes["row_sync"],
            partes["nav_bar"],
        ], spacing=0)

        # versao no lado direito do cabecalho
        partes["versao"].visible = False
        header = partes["header"]
        try:
            header.content.controls.append(
                ft.Text(f"v{APP_VERSAO}", size=10, color=MUT)
            )
        except Exception:
            pass

        # layout completo: cabeçalho + area central + rodapé
        layout = ft.Column([
            partes["spacer_topo"],
            header,
            ft.Container(content=area_central, expand=True, bgcolor=BG),
            rodape,
        ], spacing=0, expand=True)

        _nav(ft.Container(content=layout, expand=True, bgcolor=BG))

    def _voltar_para_hub():
        """Chamado pelo hub ao voltar de uma sub-tela — remonta layout desktop."""
        pw = int(page.width or 0)
        if pw >= 600 and _hub_wrapper[0] is not None:
            _montar_layout_desktop(pw)
        elif _hub_wrapper[0] is not None:
            _nav(_hub_wrapper[0])

    def _abrir_hub():
        from telas.tela_hub import criar_tela_hub
        wrapper = criar_tela_hub(page, voltar_fn=_voltar_para_hub, modo_medico=True)
        _hub_wrapper[0] = wrapper

        pw = int(page.width or 0)
        if pw >= 600:
            _montar_layout_desktop(pw)
        else:
            _nav(wrapper)

    def _on_resized(e=None):
        pw = int(page.width or 0)
        if pw < 600:
            return
        if _layout_feito[0]:
            return
        _layout_feito[0] = True
        if _hub_wrapper[0] is not None:
            _montar_layout_desktop(pw)

    page.on_resized = _on_resized

    def _iniciar():
        try:
            from dados.model_prontuario import criar_tabelas
            criar_tabelas()
        except Exception:
            pass
        _abrir_hub()

    threading.Thread(target=_iniciar, daemon=True).start()


if __name__ == "__main__":
    import os as _os
    _view = None if _os.name != "nt" else ft.AppView.WEB_BROWSER
    ft.app(
        target=main,
        port=8553,
        host="0.0.0.0",
        view=_view,
    )
