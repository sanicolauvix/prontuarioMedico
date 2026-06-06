# -*- coding: utf-8 -*-
# Prontuario | main_medico.py -- entry point web para visao do medico
import flet as ft
import os
import sys
import threading

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

ACENTO = "#BC8CFF"
BG     = "#0D1117"
MUT    = "#8B949E"
SEC    = "#8B949E"


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

        larg_max = pw - 480
        larg_sil = max(int(larg_max / 3) * 2, 300)

        def _on_orgao(oid):
            pass  # TODO: navegar para tela do orgao

        silhueta = criar_silhueta(page, on_orgao_click=_on_orgao,
                                  largura=larg_sil, mostrar_borda=False)

        # area central: col esquerda (hub) + col direita (silhueta)
        area_central = ft.Row([
            # esquerda: so area de conteudo do hub
            ft.Container(
                content=partes["area"],
                width=480,
                expand=False,
                bgcolor=BG,
            ),
            # direita: silhueta centralizada
            ft.Container(
                expand=True,
                bgcolor=BG,
                alignment=ft.alignment.center,
                content=ft.Column([
                    ft.Container(
                        content=ft.Text("Clique no Órgão que Deseja Pesquisar",
                                        size=12, color=SEC, text_align="center",
                                        weight=ft.FontWeight.W_600),
                        alignment=ft.alignment.center,
                        padding=ft.padding.only(bottom=8),
                    ),
                    ft.Container(
                        content=silhueta,
                        alignment=ft.alignment.center,
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=0),
            ),
        ], expand=True, spacing=0,
           vertical_alignment=ft.CrossAxisAlignment.START)

        # layout completo: cabeçalho + area central + rodapé
        layout = ft.Column([
            partes["spacer_topo"],
            partes["header"],
            ft.Container(content=area_central, expand=True, bgcolor=BG),
            partes["row_sync"],
            partes["versao"],
            partes["nav_bar"],
        ], spacing=0, expand=True)

        _nav(ft.Container(content=layout, expand=True, bgcolor=BG))

    def _abrir_hub():
        from telas.tela_hub import criar_tela_hub
        wrapper = criar_tela_hub(page, voltar_fn=None, modo_medico=True)
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
