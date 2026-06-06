# -*- coding: utf-8 -*-
# Prontuario | main_web.py -- entry point web unificado (usuario + medico)
# Uso no servidor: python main_web.py
import flet as ft
import os
import sys
import threading

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from versao import APP_VERSAO

BG    = "#0D1117"; CARD  = "#161B22"; BD   = "#21262D"
TXT   = "#E6EDF3"; SEC   = "#8B949E"; MUT  = "#484F58"
AZUL  = "#58A6FF"; VERD  = "#3FB950"; VERM = "#FF4444"
ROXO  = "#BC8CFF"; AMAR  = "#D29922"


def main(page: ft.Page):
    page.title      = "Prontuario Medico"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = BG
    page.padding    = 0
    page.window_maximized = True

    _hub_wrapper  = [None]
    _layout_feito = [False]

    def _nav(tela):
        page.controls.clear()
        page.controls.append(tela)
        try: page.update()
        except Exception: pass

    def _splash(msg="Carregando..."):
        return ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Container(expand=True),
                ft.ProgressRing(color=AZUL),
                ft.Container(height=12),
                ft.Text(msg, size=13, color=MUT),
                ft.Container(expand=True),
            ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               spacing=4),
        )

    # ── Tela de escolha ───────────────────────────────────────────────────────
    def _tela_escolha():
        btn_usuario = ft.Container(
            content=ft.Column([
                ft.Icon("person_rounded", size=40, color=AZUL),
                ft.Container(height=8),
                ft.Text("Sou o Paciente", size=15, color=TXT,
                        weight=ft.FontWeight.W_700, text_align="center"),
                ft.Text("Acesso completo\nautenticação Google",
                        size=11, color=SEC, text_align="center"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               spacing=4, tight=True),
            bgcolor=CARD, border=ft.border.all(1, f"{AZUL}44"),
            border_radius=16, padding=ft.padding.all(28), ink=True, width=200,
        )
        btn_medico = ft.Container(
            content=ft.Column([
                ft.Icon("medical_services_rounded", size=40, color=VERD),
                ft.Container(height=8),
                ft.Text("Sou Médico", size=15, color=TXT,
                        weight=ft.FontWeight.W_700, text_align="center"),
                ft.Text("Acesso com\ncódigo de autorização",
                        size=11, color=SEC, text_align="center"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               spacing=4, tight=True),
            bgcolor=CARD, border=ft.border.all(1, f"{VERD}44"),
            border_radius=16, padding=ft.padding.all(28), ink=True, width=200,
        )
        btn_usuario.on_click = lambda e: _ir_usuario()
        btn_medico.on_click  = lambda e: _ir_medico()

        return ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Container(expand=True),
                ft.Row([
                    ft.Icon("medical_services_rounded", size=22, color=ROXO),
                    ft.Text("Prontuário Médico", size=20, color=TXT,
                            weight=ft.FontWeight.W_700),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                ft.Text(f"v{APP_VERSAO}", size=10, color=MUT,
                        text_align="center"),
                ft.Container(height=40),
                ft.Row([btn_usuario, btn_medico],
                       alignment=ft.MainAxisAlignment.CENTER, spacing=24),
                ft.Container(expand=True),
            ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               spacing=8),
        )

    # ── Fluxo Paciente ────────────────────────────────────────────────────────
    def _ir_usuario():
        _nav(_splash("Verificando sessão..."))
        def _iniciar():
            from dados.model_prontuario import criar_tabelas
            criar_tabelas()
            from shared.auth import verificar_sessao_ativa
            if not verificar_sessao_ativa():
                from telas_shared.tela_login import criar_tela_login
                def _on_login():
                    threading.Thread(target=_abrir_usuario, daemon=True).start()
                _nav(criar_tela_login(page, on_login_sucesso=_on_login))
            else:
                _abrir_usuario()
        threading.Thread(target=_iniciar, daemon=True).start()

    def _abrir_usuario():
        from backup.drive_backup import restaurar_backup_completo
        from dados.model_prontuario import criar_tabelas
        restaurar_backup_completo()
        criar_tabelas()
        from app import criar_tela_prontuario
        _nav(criar_tela_prontuario(page, voltar_fn=None))

    # ── Fluxo Médico ──────────────────────────────────────────────────────────
    def _ir_medico():
        f_codigo = ft.TextField(
            label="Código de acesso",
            hint_text="XXXX-XXXX",
            bgcolor=CARD, border_color=BD, focused_border_color=VERD,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT, size=18, font_family="monospace"),
            border_radius=8, width=220, text_align=ft.TextAlign.CENTER,
            capitalization=ft.TextCapitalization.CHARACTERS,
        )
        txt_erro = ft.Text("", size=12, color=VERM, text_align="center")

        btn_entrar = ft.Container(
            content=ft.Row([
                ft.Icon("login_rounded", size=16, color=BG),
                ft.Text("Entrar", size=14, color=BG, weight=ft.FontWeight.W_700),
            ], spacing=8, tight=True),
            bgcolor=VERD, border_radius=10, ink=True,
            padding=ft.padding.symmetric(horizontal=32, vertical=14),
        )
        btn_voltar = ft.Container(
            content=ft.Text("← Voltar", size=12, color=SEC),
            ink=True, border_radius=6,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )
        btn_voltar.on_click = lambda e: _nav(_tela_escolha())

        def _validar(e=None):
            codigo = (f_codigo.value or "").strip().upper()
            if not codigo:
                txt_erro.value = "Digite o código de acesso"
                try: page.update()
                except Exception: pass
                return
            from dados.model_prontuario import validar_codigo_acesso
            medico = validar_codigo_acesso(codigo)
            if not medico:
                txt_erro.value = "Código inválido ou revogado"
                try: page.update()
                except Exception: pass
                return
            _tela_boas_vindas(medico)

        btn_entrar.on_click = _validar
        f_codigo.on_submit  = _validar

        _nav(ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Container(expand=True),
                ft.Icon("medical_services_rounded", size=48, color=VERD),
                ft.Container(height=8),
                ft.Text("Acesso Médico", size=18, color=TXT,
                        weight=ft.FontWeight.W_700),
                ft.Text("Digite o código fornecido pelo paciente",
                        size=12, color=SEC, text_align="center"),
                ft.Container(height=24),
                f_codigo,
                ft.Container(height=4),
                txt_erro,
                ft.Container(height=16),
                btn_entrar,
                ft.Container(height=12),
                btn_voltar,
                ft.Container(expand=True),
            ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               spacing=4),
        ))

    # ── Boas-vindas médico ────────────────────────────────────────────────────
    def _tela_boas_vindas(medico: dict):
        nome = medico.get("nome_medico", "Doutor(a)")

        # numero do whatsapp do usuario (Sebastiao)
        WHATSAPP = "5519999999999"  # substituir pelo numero real
        WHATSAPP_MSG = (
            "Olá! Acessei seu prontuário digital e gostaria de deixar "
            "uma sugestão / elogio / crítica."
        )
        wpp_url = (
            f"https://wa.me/{WHATSAPP}"
            f"?text={WHATSAPP_MSG.replace(' ', '%20')}"
        )

        btn_entrar = ft.Container(
            content=ft.Row([
                ft.Icon("login_rounded", size=16, color=BG),
                ft.Text("Acessar Prontuário", size=14, color=BG,
                        weight=ft.FontWeight.W_700),
            ], spacing=8, tight=True),
            bgcolor=VERD, border_radius=12, ink=True,
            padding=ft.padding.symmetric(horizontal=32, vertical=16),
        )
        btn_entrar.on_click = lambda e: _abrir_hub_medico(medico)

        btn_wpp = ft.Container(
            content=ft.Row([
                ft.Image(src="assets/whatsapp.png", width=20, height=20)
                if False else  # usar icone texto pois svg pode nao carregar
                ft.Container(
                    content=ft.Text("💬", size=18),
                ),
                ft.Text("Enviar mensagem ao paciente",
                        size=13, color="#25D366"),
            ], spacing=8, tight=True),
            bgcolor=ft.Colors.with_opacity(0.08, "#25D366"),
            border=ft.border.all(1, ft.Colors.with_opacity(0.35, "#25D366")),
            border_radius=10, ink=True,
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
        )
        btn_wpp.on_click = lambda e: page.launch_url(wpp_url)

        _nav(ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Container(expand=True),

                # saudacao
                ft.Text(f"Bem-vindo(a), {nome}",
                        size=20, color=TXT, weight=ft.FontWeight.W_700,
                        text_align="center"),
                ft.Container(height=24),

                # card com a mensagem
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon("info_outline_rounded", size=20, color=AZUL),
                            ft.Text("Sobre este prontuário", size=14,
                                    color=AZUL, weight=ft.FontWeight.W_700),
                        ], spacing=8),
                        ft.Container(height=12),
                        ft.Text(
                            "Este sistema foi desenvolvido com o único objetivo de "
                            "organizar e centralizar informações de saúde — "
                            "não para substituir seu julgamento clínico nem "
                            "orientar decisões médicas.",
                            size=13, color=TXT, text_align="center",
                        ),
                        ft.Container(height=8),
                        ft.Text(
                            "Você, como profissional, é o único capaz de interpretar "
                            "estes dados no contexto do paciente. "
                            "Aqui você encontrará histórico de exames, medicamentos, "
                            "consultas e marcadores de saúde organizados para "
                            "facilitar sua consulta.",
                            size=13, color=SEC, text_align="center",
                        ),
                        ft.Container(height=16),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon("favorite_rounded", size=14, color=VERM),
                                ft.Text(
                                    "Críticas, sugestões e elogios são muito bem-vindos!",
                                    size=12, color=TXT,
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.Icon("favorite_rounded", size=14, color=VERM),
                            ], spacing=8, tight=True,
                               alignment=ft.MainAxisAlignment.CENTER),
                            alignment=ft.alignment.center,
                        ),
                    ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD,
                    border=ft.border.all(1, f"{AZUL}33"),
                    border_radius=16,
                    padding=ft.padding.all(24),
                    width=520,
                ),

                ft.Container(height=28),
                btn_wpp,
                ft.Container(height=20),
                btn_entrar,
                ft.Container(expand=True),
            ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               spacing=4),
        ))

    # ── Hub médico ────────────────────────────────────────────────────────────
    def _voltar_para_hub():
        pw = int(page.width or 0)
        if pw >= 600 and _hub_wrapper[0]:
            _montar_hub_medico(pw)
        elif _hub_wrapper[0]:
            _nav(_hub_wrapper[0])

    def _abrir_hub_medico(medico: dict):
        _nav(_splash(f"Bem-vindo, {medico.get('nome_medico', 'Médico')}"))
        def _iniciar():
            from dados.model_prontuario import criar_tabelas
            criar_tabelas()
            from telas.tela_hub import criar_tela_hub
            wrapper = criar_tela_hub(page, voltar_fn=_voltar_para_hub,
                                     modo_medico=True)
            _hub_wrapper[0]  = wrapper
            _layout_feito[0] = False
            pw = int(page.width or 0)
            if pw >= 600:
                _montar_hub_medico(pw)
            else:
                _nav(wrapper)
        threading.Thread(target=_iniciar, daemon=True).start()

    def _montar_hub_medico(pw: int):
        from utils.layout_medico import montar_layout_desktop
        montar_layout_desktop(page, pw, _hub_wrapper[0], _nav)

    def _on_resized(e=None):
        pw = int(page.width or 0)
        if pw < 600 or _layout_feito[0]:
            return
        if _hub_wrapper[0]:
            _layout_feito[0] = True
            _montar_hub_medico(pw)

    page.on_resized = _on_resized

    # ── Iniciar ───────────────────────────────────────────────────────────────
    def _init():
        from dados.model_prontuario import criar_tabelas
        criar_tabelas()
        _nav(_tela_escolha())

    threading.Thread(target=_init, daemon=True).start()


if __name__ == "__main__":
    import os as _os
    _view = None if _os.name != "nt" else ft.AppView.WEB_BROWSER
    ft.app(target=main, port=8553, host="0.0.0.0", view=_view)
