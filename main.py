# -*- coding: utf-8 -*-
# Prontuario Medico | main.py -- entry point standalone (flet build apk)
import flet as ft
import os
import sys
import threading

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

ACENTO = "#BC8CFF"
BG     = "#0D1117"
TXT    = "#E6EDF3"
MUT    = "#8B949E"

# Flag de modulo: persiste entre reconexoes do WebSocket (app voltando do background)
_app_ja_iniciou = [False]


def main(page: ft.Page):
    page.title      = "Prontuario Medico"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = BG
    page.padding    = 0
    try:
        page.window.width  = 420
        page.window.height = 820
    except Exception:
        pass

    def _nav(tela: ft.Control) -> None:
        page.controls.clear()
        page.controls.append(tela)
        try:
            page.update()
        except Exception:
            pass

    def _tela_erro(msg: str):
        _nav(ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Container(expand=True),
                ft.Row([ft.Icon("error_outline", color="#F85149", size=48)],
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=12),
                ft.Row([ft.Text(msg, size=13, color="#F85149",
                                text_align=ft.TextAlign.CENTER)],
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(expand=True),
            ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=32,
        ))

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
        _app_ja_iniciou[0] = True
        try:
            from app import criar_tela_prontuario
            _nav(criar_tela_prontuario(page, voltar_fn=None))
        except Exception as ex:
            import traceback
            _tela_erro(f"Erro ao abrir prontuario:\n{traceback.format_exc()[-400:]}")

    # Reconexao apos background: pular splash, ir direto para o app
    if _app_ja_iniciou[0]:
        try:
            from shared.auth import verificar_sessao_ativa
            if verificar_sessao_ativa():
                _abrir_prontuario()
                return
        except Exception:
            pass

    def _iniciar():
        try:
            from shared.auth import verificar_sessao_ativa
            if verificar_sessao_ativa():
                _abrir_prontuario()
                return
        except Exception:
            pass

        try:
            from telas_shared.tela_login import criar_tela_login

            def _on_login():
                _abrir_prontuario()

            _nav(criar_tela_login(page, on_login_sucesso=_on_login))
        except Exception as ex:
            import traceback
            _tela_erro(f"Erro ao abrir login:\n{traceback.format_exc()[-600:]}")

    threading.Thread(target=_iniciar, daemon=True).start()


ft.app(target=main)
