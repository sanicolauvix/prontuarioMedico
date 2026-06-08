# -*- coding: utf-8 -*-
# Prontuario | utils/oauth_callback_server.py
# Servidor HTTP que captura o callback OAuth do Google e notifica a sessao Flet correta.
#
# Fluxo:
#   1. Flet gera URL OAuth com redirect_uri = https://koios.app.br/oauth/callback
#   2. Nginx repassa /oauth/callback para este servidor (porta 8557)
#   3. Este servidor troca o codigo por token, salva mycreds.json
#   4. Redireciona o browser para https://koios.app.br/?oauth=ok&sid=SESSION_ID
#   5. Flet detecta ?oauth=ok via page.on_route_change e abre o hub

import http.server
import threading
import logging
import os
import urllib.parse

log = logging.getLogger(__name__)

_PORT        = 8557
_CALLBACK    = "/oauth/callback"
_APP_URL     = "https://koios.app.br"
_pendentes   = {}   # sid -> {"secrets": ..., "callback": fn(ok, erro)}
_lock        = threading.Lock()
_iniciado    = [False]


def registrar_sessao(sid: str, secrets: dict, callback_fn) -> None:
    """Registra uma sessao aguardando o callback OAuth."""
    with _lock:
        _pendentes[sid] = {"secrets": secrets, "callback": callback_fn}
    log.info("[OAuthSrv] sessao registrada sid=%s", sid)


def remover_sessao(sid: str) -> None:
    with _lock:
        _pendentes.pop(sid, None)


class _Handler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        parsed   = urllib.parse.urlparse(self.path)
        params   = urllib.parse.parse_qs(parsed.query)
        path     = parsed.path

        if path != _CALLBACK:
            self._responder(404, "Not found")
            return

        codigo = (params.get("code", [None])[0] or "").strip()
        sid    = (params.get("state", [None])[0] or "").strip()
        erro   = (params.get("error", [None])[0] or "").strip()

        if erro:
            log.warning("[OAuthSrv] Google retornou erro: %s", erro)
            self._redirecionar(f"{_APP_URL}/?oauth=erro&msg={urllib.parse.quote(erro)}")
            with _lock:
                entry = _pendentes.pop(sid, None)
            if entry:
                threading.Thread(target=entry["callback"],
                                 args=(False, erro), daemon=True).start()
            return

        if not codigo or not sid:
            self._responder(400, "Parametros ausentes")
            return

        with _lock:
            entry = _pendentes.pop(sid, None)

        if not entry:
            log.warning("[OAuthSrv] sid nao encontrado: %s", sid)
            self._redirecionar(f"{_APP_URL}/?oauth=erro&msg=sessao+expirada")
            return

        secrets  = entry["secrets"]
        callback = entry["callback"]

        # Troca o codigo por token em background
        def _trocar():
            try:
                from shared.auth import trocar_codigo_por_token
                ok, msg, _ = trocar_codigo_por_token(secrets, codigo)
                callback(ok, msg if not ok else "")
            except Exception as ex:
                log.exception("[OAuthSrv] trocar_codigo: %s", ex)
                callback(False, str(ex))

        threading.Thread(target=_trocar, daemon=True).start()

        # Retorna pagina HTML que fecha a aba — a aba original detecta via polling
        self._pagina_fechar_aba()

    def _pagina_fechar_aba(self):
        html = (
            "<!DOCTYPE html><html><head>"
            "<meta charset='utf-8'>"
            "<title>Login realizado</title>"
            "<style>body{background:#0D1117;color:#E6EDF3;font-family:sans-serif;"
            "display:flex;align-items:center;justify-content:center;height:100vh;margin:0}"
            ".box{text-align:center}</style></head><body>"
            "<div class='box'>"
            "<div style='font-size:48px'>&#10003;</div>"
            "<h2 style='color:#3FB950'>Login realizado!</h2>"
            "<p style='color:#8B949E'>Pode fechar esta aba e voltar ao Prontuario.</p>"
            "</div>"
            "<script>setTimeout(function(){window.close()},1500);</script>"
            "</body></html>"
        )
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirecionar(self, url: str):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def _responder(self, code: int, msg: str):
        body = msg.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def iniciar() -> None:
    """Inicia o servidor de callback em background — chama uma vez no startup."""
    with _lock:
        if _iniciado[0]:
            return
        _iniciado[0] = True

    def _run():
        try:
            srv = http.server.HTTPServer(("0.0.0.0", _PORT), _Handler)
            log.info("[OAuthSrv] escutando na porta %d", _PORT)
            srv.serve_forever()
        except Exception as ex:
            log.exception("[OAuthSrv] falha ao iniciar: %s", ex)

    threading.Thread(target=_run, daemon=True, name="OAuthCallbackServer").start()
