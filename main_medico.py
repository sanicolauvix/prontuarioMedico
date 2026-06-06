# -*- coding: utf-8 -*-
# Prontuario | main_medico.py -- entry point web para visao do medico
# Uso: python main_medico.py
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


def main(page: ft.Page):
    page.title      = "Koios — Visao Medico"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = BG
    page.padding    = 0
    page.window_maximized = True
    try:
        page.window.maximized = True
    except Exception:
        pass

    def _nav(tela):
        page.controls.clear()
        page.controls.append(tela)
        try: page.update()
        except Exception: pass

    _nav(ft.Container(
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
    ))

    def _abrir_hub():
        from telas.tela_hub import criar_tela_hub
        _nav(criar_tela_hub(page, voltar_fn=None, modo_medico=True))

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
    # no servidor Linux headless: nao abrir browser, so servir web
    _view = None if _os.name != "nt" else ft.AppView.WEB_BROWSER
    ft.app(
        target=main,
        port=8553,
        host="0.0.0.0",
        view=_view,
    )
