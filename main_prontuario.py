"""
prontuario/main_prontuario.py — MINIMO v2
Sem logging em arquivo, sem imports pesados no topo.
"""

import flet as ft
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

ASSETS_DIR = os.path.join(_ROOT, "assets")
ACENTO = "#BC8CFF"
BG     = "#0D1117"
TXT    = "#E6EDF3"
MUT    = "#8B949E"


def main(page: ft.Page):
    page.title      = "Koios Prontuario"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = BG
    page.padding    = 0
    try:
        page.window.width  = 420
        page.window.height = 820
    except Exception:
        pass

    def _nav(tela):
        page.controls.clear()
        page.controls.append(tela)
        page.update()

    def _tela_ok(msg: str):
        _nav(ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Container(expand=True),
                ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color="#3FB950", size=48)],
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=12),
                ft.Row([ft.Text(msg, size=14, color=TXT, text_align=ft.TextAlign.CENTER)],
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(expand=True),
            ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=32,
        ))

    def _tela_erro(msg: str):
        _nav(ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Container(expand=True),
                ft.Row([ft.Icon(ft.Icons.ERROR_OUTLINE, color="#F85149", size=48)],
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=12),
                ft.Row([ft.Text(msg, size=13, color="#F85149",
                                text_align=ft.TextAlign.CENTER)],
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(expand=True),
            ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=32,
        ))

    # Tela inicial imediata — sem nenhum import pesado
    _nav(ft.Container(
        bgcolor=BG, expand=True,
        content=ft.Column([
            ft.Container(expand=True),
            ft.Row([ft.ProgressRing(color=ACENTO)],
                   alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=12),
            ft.Row([ft.Text("Iniciando...", size=13, color=MUT)],
                   alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(expand=True),
        ], expand=True),
    ))

    def _abrir_prontuario():
        try:
            from prontuario.app import criar_tela_prontuario
            _nav(criar_tela_prontuario(page, voltar_fn=None))
        except Exception as ex:
            _tela_erro(f"Erro ao abrir prontuário:\n{type(ex).__name__}: {ex}")

    def _iniciar():
        try:
            from shared.auth import verificar_sessao_ativa
            if verificar_sessao_ativa():
                _abrir_prontuario()
                return
        except Exception:
            pass  # sem sessao — normal

        try:
            from prontuario.telas.tela_login import criar_tela_login

            def _on_login(token, perfil):
                _abrir_prontuario()

            _nav(criar_tela_login(page, on_login_sucesso=_on_login))
        except Exception as ex:
            _tela_erro(f"Erro ao abrir login:\n{type(ex).__name__}: {ex}")

    import threading
    threading.Thread(target=_iniciar, daemon=True).start()


if __name__ == "__main__":
    ft.app(
        target=main,
        assets_dir=ASSETS_DIR,
        port=8552,
        view=ft.AppView.WEB_BROWSER,
    )
