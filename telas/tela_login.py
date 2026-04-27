# -*- coding: utf-8 -*-
# SHARED | telas/tela_login.py -- gerenciado por flet_shared/sync_shared.py
# --- SHARED PARAMS ---
_APP_NOME       = "Prontuario Medico"
_APP_SUBTITULO  = "Seu historico de saude"
_APP_ICON_FILE  = "icon.png"
_APP_ICON_VAZIO = "medical_services_rounded"
_LOGIN_MSG      = "Volte ao Prontuario para continuar."
# --- END SHARED PARAMS ---
"""
Fluxo Android:
  1. Botao "Entrar com Google" -> gerar_url_autorizacao()
  2. page.launch_url(url) abre browser nativo
  3. Servidor HTTP local porta 8080 captura redirect automaticamente
  4. Fallback apos 8s: painel para colar URL manualmente
  5. Token salvo -> on_login_sucesso()

Fluxo Desktop:
  login_google_desktop() -> oauthlib captura automaticamente
"""
import logging
import os
import threading

import flet as ft

log = logging.getLogger(__name__)

BG    = "#0D1117"; CARD  = "#161B22"; BORDA = "#21262D"; BORDA2 = "#30363D"
TXT   = "#E6EDF3"; SEC   = "#8B949E"; DIS   = "#484F58"
AZUL  = "#58A6FF"; VERD  = "#3FB950"; VERM  = "#FF4444"; AMAR  = "#D29922"

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)


def _is_android() -> bool:
    import sys
    exe = getattr(sys, "executable", "") or ""
    if "/data/" in exe:
        return True
    if os.environ.get("FLET_PLATFORM", "").lower() == "android":
        return True
    try:
        import tkinter
        return False
    except Exception:
        return True


def _passo(numero: str, texto: str) -> ft.Row:
    return ft.Row([
        ft.Container(
            content=ft.Text(numero, size=11, color=BG, weight=ft.FontWeight.W_700),
            width=22, height=22, border_radius=11,
            bgcolor=AZUL, alignment=ft.Alignment(0, 0),
        ),
        ft.Text(texto, size=12, color=TXT, expand=True),
    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START)


def _extrair_codigo(url: str):
    try:
        from urllib.parse import urlparse, parse_qs
        params  = parse_qs(urlparse(url).query)
        codigos = params.get("code", [])
        if codigos:
            return codigos[0]
        for parte in url.split("&"):
            if "code=" in parte:
                return parte.split("code=", 1)[-1].split("&")[0]
    except Exception as ex:
        log.warning("[Login] _extrair_codigo: %s", ex)
    return None


def criar_tela_login(page: ft.Page, on_login_sucesso) -> ft.Container:

    android = _is_android()
    _estado = {"fase": "aguardando", "secrets": None}

    spinner    = ft.ProgressRing(color=AZUL, width=26, height=26, visible=False)
    txt_status = ft.Text("", size=12, color=SEC, text_align="center")

    campo_url = ft.TextField(
        hint_text="Cole aqui a URL completa do navegador...",
        hint_style=ft.TextStyle(color=DIS),
        color=TXT, bgcolor=CARD,
        border_color=BORDA2, focused_border_color=AZUL,
        border_radius=10, text_size=13,
        multiline=True, min_lines=2, max_lines=4,
        visible=False,
    )

    def _colar_url(e):
        try:
            clip = page.get_clipboard()
            if clip and clip.strip():
                campo_url.value = clip.strip()
                try: page.update()
                except Exception: pass
        except Exception as ex:
            log.warning("[Login] _colar_url: %s", ex)

    btn_colar = ft.Container(
        visible=False,
        content=ft.Row([
            ft.Icon("content_paste_rounded", size=14, color=AZUL),
            ft.Text("Colar URL", size=12, color=AZUL),
        ], spacing=6, tight=True),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        border_radius=8, bgcolor=f"{AZUL}22", ink=True,
    )
    btn_colar.on_click = _colar_url

    painel_instrucoes = ft.Container(
        visible=False,
        content=ft.Column([
            ft.Row([
                ft.Icon("info_rounded", size=15, color=AZUL),
                ft.Text("O que fazer agora:", size=13, color=AZUL,
                        weight=ft.FontWeight.W_600),
            ], spacing=8),
            ft.Container(height=10),
            _passo("1", "O navegador abriu -- faca login com sua conta Google"),
            ft.Container(height=6),
            _passo("2", "Apos autorizar, o app voltara automaticamente"),
            ft.Container(height=6),
            _passo("3", "Se nao voltar, copie a URL e clique em Colar URL"),
            ft.Container(height=12),
            campo_url,
            ft.Container(height=6),
            ft.Row([btn_colar], alignment=ft.MainAxisAlignment.END),
        ], spacing=0),
        padding=ft.padding.all(14),
        border_radius=10,
        bgcolor=f"{AZUL}11",
        border=ft.Border(
            top=ft.BorderSide(1, f"{AZUL}44"),
            bottom=ft.BorderSide(1, f"{AZUL}44"),
            left=ft.BorderSide(3, AZUL),
            right=ft.BorderSide(1, f"{AZUL}44"),
        ),
    )

    btn_confirmar = ft.Container(
        visible=False,
        content=ft.Row([
            ft.Icon("check_rounded", size=16, color=BG),
            ft.Text("Confirmar e entrar", size=14, color=BG,
                    weight=ft.FontWeight.W_600),
        ], spacing=8, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=20, vertical=14),
        border_radius=10, bgcolor=VERD, ink=True,
    )

    btn_cancelar = ft.Container(
        visible=False,
        content=ft.Text("Cancelar", size=13, color=SEC),
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        border_radius=8, ink=True,
    )

    btn_entrar = ft.Container(
        content=ft.Row([
            ft.Icon("account_circle_rounded", size=20, color=TXT),
            ft.Text("Entrar com Google", size=15, color=TXT,
                    weight=ft.FontWeight.W_600),
        ], spacing=10, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=24, vertical=16),
        border_radius=12, bgcolor=CARD, ink=True,
        border=ft.Border(
            top=ft.BorderSide(1, BORDA2), bottom=ft.BorderSide(1, BORDA2),
            left=ft.BorderSide(1, BORDA2), right=ft.BorderSide(1, BORDA2),
        ),
    )

    # ── Modo auxiliar / codigo de convite ─────────────────────────────────
    try:
        from shared.multi_usuario import (
            is_auxiliar as _is_aux, get_principal_email as _get_principal,
            salvar_como_auxiliar as _salvar_aux,
            decodificar_convite as _decode_convite,
            desvincular_auxiliar as _desvincular,
        )
        _ja_auxiliar    = _is_aux()
        _principal_email = _get_principal() if _ja_auxiliar else ""
    except Exception:
        _ja_auxiliar     = False
        _principal_email = ""

    def _overlay_codigo_acesso() -> None:
        tf_codigo = ft.TextField(
            label="Codigo de convite",
            hint_text="Cole o codigo enviado pelo proprietario...",
            bgcolor=CARD, border_color=BORDA2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, multiline=True, min_lines=2, max_lines=4,
        )
        msg = ft.Text("", size=12, color=VERM)
        ref = [None]

        def _fechar(e=None):
            if ref[0] and ref[0] in page.overlay:
                page.overlay.remove(ref[0])
            try: page.update()
            except Exception: pass

        def _confirmar(e):
            codigo = tf_codigo.value.strip()
            if not codigo:
                msg.value = "Cole o codigo antes de confirmar."
                try: page.update()
                except Exception: pass
                return
            try:
                invite = _decode_convite(codigo)
                _salvar_aux(invite)
                _fechar()
                # Atualiza badge sem reconstruir a tela
                badge_aux.visible        = True
                lbl_aux_email.value      = invite.get("owner", "")
                btn_tem_codigo.visible   = False
                separador_aux.visible    = False
                try: page.update()
                except Exception: pass
            except ValueError as ex:
                msg.value = str(ex)
                try: page.update()
                except Exception: pass

        def _colar_codigo(e):
            try:
                clip = page.get_clipboard()
                if clip:
                    tf_codigo.value = clip.strip()
                    try: page.update()
                    except Exception: pass
            except Exception: pass

        btn_colar_cod = ft.Container(
            content=ft.Row([
                ft.Icon("content_paste_rounded", size=13, color=AZUL),
                ft.Text("Colar", size=12, color=AZUL),
            ], spacing=4, tight=True),
            bgcolor=f"{AZUL}22", border_radius=6, ink=True,
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            on_click=_colar_codigo,
        )

        ref[0] = ft.Container(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Codigo de acesso", size=15, color=TXT,
                                weight=ft.FontWeight.W_700),
                        ft.Container(height=6),
                        ft.Text(
                            "Cole o codigo enviado pelo proprietario do app.",
                            size=12, color=SEC,
                        ),
                        ft.Container(height=10),
                        tf_codigo,
                        ft.Row([btn_colar_cod],
                               alignment=ft.MainAxisAlignment.END),
                        ft.Container(height=4),
                        msg,
                        ft.Container(height=10),
                        ft.Row(
                            [
                                ft.Container(
                                    content=ft.Text("Cancelar", size=13, color=SEC),
                                    bgcolor=CARD, border_radius=8, ink=True,
                                    padding=ft.padding.symmetric(
                                        horizontal=16, vertical=11),
                                    on_click=_fechar,
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        "Confirmar", size=13, color=BG,
                                        weight=ft.FontWeight.W_600),
                                    bgcolor=AZUL, border_radius=8, ink=True,
                                    padding=ft.padding.symmetric(
                                        horizontal=16, vertical=11),
                                    on_click=_confirmar,
                                ),
                            ],
                            spacing=8,
                            alignment=ft.MainAxisAlignment.END,
                        ),
                    ],
                    tight=True,
                ),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20), width=300,
            ),
            bgcolor="#CC000000", expand=True,
            alignment=ft.Alignment(0, 0),
        )
        page.overlay.append(ref[0])
        try: page.update()
        except Exception: pass

    # Badge exibido quando ja e auxiliar
    lbl_aux_email = ft.Text(_principal_email, size=10, color=SEC)
    badge_aux = ft.Container(
        content=ft.Row(
            [
                ft.Icon("shield_rounded", size=12, color=AMAR),
                ft.Text("Modo auxiliar  ", size=11, color=AMAR),
                lbl_aux_email,
                ft.Container(width=8),
                ft.Container(
                    content=ft.Text("desvincular", size=10, color=SEC),
                    ink=True, border_radius=4,
                    padding=ft.padding.symmetric(horizontal=4, vertical=2),
                    on_click=lambda e: (
                        _desvincular(),
                        setattr(badge_aux, "visible", False),
                        setattr(btn_tem_codigo, "visible", True),
                        setattr(separador_aux, "visible", True),
                        page.update(),
                    ),
                ),
            ],
            spacing=2, tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        bgcolor=f"{AMAR}11", border_radius=8,
        border=ft.Border(
            top=ft.BorderSide(1, f"{AMAR}44"),
            bottom=ft.BorderSide(1, f"{AMAR}44"),
            left=ft.BorderSide(1, f"{AMAR}44"),
            right=ft.BorderSide(1, f"{AMAR}44"),
        ),
        visible=_ja_auxiliar,
    )

    separador_aux = ft.Container(
        content=ft.Row(
            [ft.Container(height=1, expand=True, bgcolor=BORDA),
             ft.Text("  ou  ", size=10, color=DIS),
             ft.Container(height=1, expand=True, bgcolor=BORDA)],
            spacing=0,
        ),
        visible=not _ja_auxiliar,
    )

    btn_tem_codigo = ft.Container(
        content=ft.Row(
            [
                ft.Icon("vpn_key_rounded", size=13, color=SEC),
                ft.Text("Tenho codigo de acesso", size=12, color=SEC),
            ],
            spacing=6, tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=9),
        border_radius=8, ink=True,
        on_click=lambda e: _overlay_codigo_acesso(),
        visible=not _ja_auxiliar,
    )

    _icon_path = os.path.join(_ROOT, "assets", _APP_ICON_FILE)
    if os.path.exists(_icon_path):
        logo = ft.Image(src=_APP_ICON_FILE, width=90, height=90, fit="contain")
    else:
        logo = ft.Container(
            content=ft.Icon(_APP_ICON_VAZIO, size=44, color=AZUL),
            width=90, height=90, border_radius=20,
            bgcolor=f"{AZUL}22", alignment=ft.Alignment(0, 0),
        )

    _subscribed = [True]

    def _on_msg(msg):
        if not isinstance(msg, dict) or msg.get("_src") != "login":
            return
        t = msg.get("tipo")
        if not _subscribed[0] and t != "_navegar_hub":
            return

        if t == "status":
            txt_status.value = msg.get("txt", "")
            txt_status.color = msg.get("cor", SEC)
            spinner.visible  = msg.get("spin", False)
            try: page.update()
            except Exception: pass

        elif t == "instrucoes":
            _estado["fase"]    = "instrucoes"
            _estado["secrets"] = msg.get("secrets")
            btn_entrar.visible = False
            spinner.visible    = True
            txt_status.value   = "Aguardando autorizacao..."
            txt_status.color   = SEC
            threading.Timer(8.0, lambda: _pub({"tipo": "_fallback_instrucoes"})).start()
            try: page.update()
            except Exception: pass

        elif t == "_fallback_instrucoes":
            if _estado.get("fase") != "instrucoes":
                return
            painel_instrucoes.visible = True
            campo_url.visible         = True
            btn_colar.visible         = True
            campo_url.value           = ""
            btn_confirmar.visible     = True
            btn_cancelar.visible      = True
            spinner.visible           = False
            txt_status.value          = ""
            try: page.update()
            except Exception: pass

        elif t == "processando":
            _estado["fase"]           = "processando"
            spinner.visible           = True
            txt_status.value          = "Autenticando..."
            txt_status.color          = SEC
            btn_confirmar.visible     = False
            btn_cancelar.visible      = False
            painel_instrucoes.visible = False
            try: page.update()
            except Exception: pass

        elif t == "_reset_login":
            _resetar()
            try: page.update()
            except Exception: pass

        elif t == "erro":
            _resetar()
            txt_status.value = msg.get("txt", "Erro")
            txt_status.color = VERM
            try: page.update()
            except Exception: pass

        elif t == "sucesso":
            _subscribed[0]   = False
            spinner.visible  = False
            txt_status.value = "Login realizado!"
            txt_status.color = VERD
            try: page.update()
            except Exception: pass
            threading.Timer(0.6, lambda: _pub({"tipo": "_navegar_hub"})).start()

        elif t == "_navegar_hub":
            log.info("[Login] navegando para hub")
            on_login_sucesso()

    page.pubsub.subscribe(_on_msg)

    def _pub(dados: dict):
        dados["_src"] = "login"
        page.pubsub.send_all(dados)

    def _resetar():
        _estado["fase"]           = "aguardando"
        _estado["secrets"]        = None
        btn_entrar.visible        = True
        spinner.visible           = False
        painel_instrucoes.visible = False
        btn_confirmar.visible     = False
        btn_cancelar.visible      = False
        campo_url.value           = ""
        txt_status.color          = SEC
        txt_status.value          = ""

    def _clicou_entrar(e):
        if _estado["fase"] != "aguardando": return
        _estado["fase"]    = "processando"
        btn_entrar.visible = False
        spinner.visible    = True
        txt_status.value   = "Preparando autenticacao..."
        txt_status.color   = SEC
        try: page.update()
        except Exception: pass
        threading.Thread(target=_executar_login, daemon=True).start()

    def _clicou_confirmar(e):
        if _estado["fase"] != "instrucoes": return
        url = (campo_url.value or "").strip()
        if not url:
            try:
                clip = page.get_clipboard()
                if clip:
                    url = clip.strip()
            except Exception: pass
        if not url:
            txt_status.value = "Cole a URL antes de confirmar."
            txt_status.color = AMAR
            try: page.update()
            except Exception: pass
            return
        codigo = _extrair_codigo(url)
        if not codigo:
            txt_status.value = "URL invalida -- codigo nao encontrado."
            txt_status.color = VERM
            try: page.update()
            except Exception: pass
            return
        secrets = _estado.get("secrets")
        if not secrets:
            _pub({"tipo": "erro", "txt": "Sessao expirada. Clique em Entrar novamente."})
            return
        _pub({"tipo": "processando"})
        threading.Thread(target=_trocar_codigo, args=(secrets, codigo), daemon=True).start()

    def _clicou_cancelar(e):
        try:
            page.window_close()
        except Exception:
            import sys
            sys.exit(0)

    btn_entrar.on_click    = _clicou_entrar
    btn_confirmar.on_click = _clicou_confirmar
    btn_cancelar.on_click  = _clicou_cancelar

    def _processar_url_redirect(url: str) -> bool:
        try:
            from shared.auth import is_redirect_url, extrair_codigo_da_url
            if not is_redirect_url(url):
                return False
            codigo = extrair_codigo_da_url(url)
            if not codigo:
                return False
            secrets = _estado.get("secrets")
            if not secrets:
                return False
            log.info("[Login] deep link: %s", url[:80])
            _pub({"tipo": "processando"})
            threading.Thread(target=_trocar_codigo, args=(secrets, codigo), daemon=True).start()
            return True
        except Exception as ex:
            log.warning("[Login] _processar_url_redirect: %s", ex)
            return False

    def _on_lifecycle(e):
        estado = str(getattr(e, "state", "") or "").lower()
        if _estado.get("fase") != "instrucoes":
            return
        for attr in ("data", "url", "uri", "view", "route", "path"):
            url = str(getattr(e, attr, "") or "").strip()
            if url and _processar_url_redirect(url):
                return
        if "resume" in estado or "foreground" in estado:
            def _clip():
                import time; time.sleep(0.8)
                try:
                    clip = (page.get_clipboard() or "").strip()
                    if clip and _processar_url_redirect(clip):
                        return
                except Exception: pass
                if _estado.get("fase") == "instrucoes":
                    _pub({"tipo": "_reset_login"})
            threading.Thread(target=_clip, daemon=True).start()

    page.on_app_lifecycle_state_change = _on_lifecycle

    def _on_route(e):
        url = str(getattr(e, "route", "") or "").strip()
        if url and _estado.get("fase") == "instrucoes":
            _processar_url_redirect(url)

    page.on_route_change = _on_route

    def _executar_login():
        try:
            if android:
                _login_android()
            else:
                _login_desktop()
        except Exception as ex:
            log.exception("[Login] _executar_login: %s", ex)
            _pub({"tipo": "erro", "txt": str(ex)[:120]})

    def _login_android():
        try:
            _pub({"tipo": "status", "txt": "Iniciando autenticacao...", "spin": True})
            from shared.auth import gerar_url_autorizacao
            ok, url, secrets = gerar_url_autorizacao()
            if not ok:
                _pub({"tipo": "erro", "txt": url})
                return

            import http.server, threading as _th, urllib.parse as _up
            codigo_recebido = [None]

            class _OAuthHandler(http.server.BaseHTTPRequestHandler):
                def do_GET(self):
                    try:
                        params = _up.parse_qs(_up.urlparse(self.path).query)
                        if "code" in params:
                            codigo_recebido[0] = params["code"][0]
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.end_headers()
                        self.wfile.write((
                            "<html><body style='background:#0D1117;color:#E6EDF3;"
                            "font-family:sans-serif;text-align:center;padding-top:80px'>"
                            "<h2>&#10003; Login realizado!</h2>"
                            f"<p>{_LOGIN_MSG}</p>"
                            "</body></html>"
                        ).encode("utf-8"))
                    except Exception: pass
                def log_message(self, *a): pass

            def _iniciar_servidor():
                try:
                    srv = http.server.HTTPServer(("127.0.0.1", 8080), _OAuthHandler)
                    srv.handle_request()
                    srv.server_close()
                    if codigo_recebido[0]:
                        _pub({"tipo": "processando"})
                        _th.Thread(target=_trocar_codigo, args=(secrets, codigo_recebido[0]), daemon=True).start()
                except Exception as ex:
                    log.warning("[Login] servidor local: %s", ex)

            _th.Thread(target=_iniciar_servidor, daemon=True).start()
            _pub({"tipo": "status", "txt": "Abrindo navegador...", "spin": True})
            try:
                page.launch_url(url)
            except Exception as ex:
                import webbrowser
                webbrowser.open(url)
            _pub({"tipo": "instrucoes", "secrets": secrets})

        except Exception as ex:
            log.exception("[Login Android] %s", ex)
            _pub({"tipo": "erro", "txt": f"Erro ao gerar URL: {str(ex)[:100]}"})

    def _login_desktop():
        try:
            _pub({"tipo": "status", "txt": "Abrindo janela do Google...", "spin": True})
            from shared.auth import login_google_desktop
            ok, msg, _ = login_google_desktop()
            if ok:
                _pub({"tipo": "sucesso"})
            else:
                _pub({"tipo": "erro", "txt": msg})
        except Exception as ex:
            log.exception("[Login Desktop] %s", ex)
            _pub({"tipo": "erro", "txt": str(ex)[:120]})

    def _trocar_codigo(secrets: dict, codigo: str):
        try:
            _pub({"tipo": "status", "txt": "Trocando codigo por token...", "spin": True})
            from shared.auth import trocar_codigo_por_token
            ok, msg, _ = trocar_codigo_por_token(secrets, codigo)
            if ok:
                _pub({"tipo": "sucesso"})
            else:
                _pub({"tipo": "erro", "txt": msg})
        except Exception as ex:
            log.exception("[Login] trocar_codigo: %s", ex)
            _pub({"tipo": "erro", "txt": str(ex)[:120]})

    bloco_central = ft.Column(
        [
            logo,
            ft.Container(height=16),
            ft.Text(_APP_NOME, size=24, weight=ft.FontWeight.W_900,
                    color=TXT, text_align=ft.TextAlign.CENTER),
            ft.Text(_APP_SUBTITULO, size=11, color=AZUL,
                    weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
            ft.Container(height=32),
            btn_entrar,
            ft.Container(height=10),
            separador_aux,
            ft.Container(height=6),
            btn_tem_codigo,
            badge_aux,
            ft.Container(height=10),
            painel_instrucoes,
            ft.Container(height=8),
            btn_confirmar,
            ft.Container(height=4),
            ft.Row([btn_cancelar], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=14),
            ft.Row([spinner],    alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([txt_status], alignment=ft.MainAxisAlignment.CENTER),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=0, tight=True, width=320,
    )

    rodape = ft.Row(
        [ft.Text("v1.0", size=10, color=DIS)],
        alignment=ft.MainAxisAlignment.CENTER,
    )

    return ft.Container(
        bgcolor=BG, expand=True,
        padding=ft.padding.only(left=24, right=24, top=0, bottom=16),
        content=ft.Column(
            [
                ft.Container(expand=True),
                ft.Row([bloco_central], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(expand=True),
                rodape,
                ft.Container(height=8),
            ],
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        ),
    )
