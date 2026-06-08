# -*- coding: utf-8 -*-
# gerado por flet_shared | shared/auth.py
"""
shared/auth.py -- Autenticacao Google OAuth2

Fluxo Android:
  1. gerar_url_autorizacao() -> URL sem usar oauthlib
  2. Deep link / servidor local captura redirect com code=...
  3. trocar_codigo_por_token() troca codigo por token
  4. Token salvo em mycreds.json

Fluxo Desktop:
  login_google_desktop() -> InstalledAppFlow.run_local_server
"""

import os, json, logging, importlib
from urllib.parse import urlparse, parse_qs, urlencode

# --- SHARED PARAMS ---
_DB_SET_CONFIG_MODULE = "dados.model_prontuario"
# --- END SHARED PARAMS ---

_HERE         = os.path.dirname(os.path.abspath(__file__))
_ROOT         = os.path.dirname(_HERE)
_SECRETS_PATH = os.path.join(_ROOT, "client_secrets.json")
_SECRETS_ANDROID_PATH = os.path.join(_ROOT, "client_secrets_android.json")

def _is_android() -> bool:
    import sys
    exe = getattr(sys, "executable", "") or ""
    if "/data/" in exe:
        return True
    plat = os.environ.get("FLET_PLATFORM", "").lower()
    if plat == "android":
        return True
    if plat == "web":
        return False
    try:
        import tkinter  # noqa
        return False
    except Exception:
        return True


def _get_creds_path() -> str:
    """Retorna path persistente para mycreds.json.
    No Android, o diretorio do app e resetado a cada build.
    Usa /data/user/0/{package}/files/ que persiste entre updates.
    """
    if _is_android():
        caminho = _HERE
        for _ in range(10):
            caminho = os.path.dirname(caminho)
            if os.path.basename(caminho) == "files":
                return os.path.join(caminho, "mycreds.json")
            if caminho == "/":
                break
    return os.path.join(_ROOT, "mycreds.json")

_CREDS_PATH = _get_creds_path()

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
]

def _get_redirect_uri(secrets: dict) -> str:
    """Retorna redirect_uri correto para a plataforma.
    Android: Reverse Client ID Scheme -- Google intercepta e abre o app
    Web:     https://koios.app.br -- Google redireciona o browser do usuario
    Desktop: http://localhost -- capturado pelo InstalledAppFlow
    """
    plat = os.environ.get("FLET_PLATFORM", "").lower()
    if plat == "web":
        return "http://localhost:8080"
    if _is_android():
        client_id = secrets.get("client_id", "")
        base = client_id.replace(".apps.googleusercontent.com", "")
        return f"com.googleusercontent.apps.{base}:/"
    return "http://localhost"


def _salvar_creds(creds) -> None:
    try:
        with open(_CREDS_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    except Exception as ex:
        logging.warning(f"[AUTH] _salvar_creds: {ex}")


def _perfil_do_token(token: str) -> dict:
    try:
        import urllib.request
        url = f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={token}"
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as ex:
        logging.warning(f"[AUTH] _perfil_do_token: {ex}")
        return {}


def _salvar_perfil_no_banco(perfil: dict) -> None:
    if not perfil:
        return
    try:
        _mod = importlib.import_module(_DB_SET_CONFIG_MODULE)
        set_config = getattr(_mod, "set_config", None)
        if not set_config:
            return
        nome  = perfil.get("name",  "")
        email = perfil.get("email", "")
        if nome:  set_config("usuario_nome",  nome)
        if email: set_config("usuario_email", email)
    except Exception as ex:
        logging.warning(f"[AUTH] _salvar_perfil_no_banco: {ex}")


# Constante publica -- calculada uma vez ao importar o modulo
# Use: from shared.auth import IS_ANDROID
IS_ANDROID: bool = _is_android()


def _ler_client_secrets() -> dict:
    # Android usa credencial sem client_secret
    # Desktop usa credencial com client_secret
    path = _SECRETS_ANDROID_PATH if (_is_android() and os.path.exists(_SECRETS_ANDROID_PATH)) else _SECRETS_PATH
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("installed") or data.get("web") or {}


def verificar_sessao_ativa() -> bool:
    try:
        if not os.path.exists(_CREDS_PATH):
            return False
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        creds = Credentials.from_authorized_user_file(_CREDS_PATH, SCOPES)
        if creds and creds.valid:
            return True
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _salvar_creds(creds)
            return True
    except Exception as ex:
        logging.debug(f"[AUTH] verificar_sessao_ativa: {ex}")
    return False


def encerrar_sessao() -> None:
    try:
        if os.path.exists(_CREDS_PATH):
            os.remove(_CREDS_PATH)
            logging.info("[AUTH] Sessao encerrada")
    except Exception as ex:
        logging.warning(f"[AUTH] encerrar_sessao: {ex}")


def gerar_url_autorizacao() -> tuple:
    """
    Gera URL OAuth2 manualmente sem usar oauthlib.
    Retorna (True, url, secrets_dict) ou (False, erro, None)
    """
    try:
        if not os.path.exists(_SECRETS_PATH):
            return False, "client_secrets.json nao encontrado.", None

        secrets = _ler_client_secrets()
        client_id = secrets.get("client_id", "")
        if not client_id:
            return False, "client_id nao encontrado no client_secrets.json", None

        redirect_uri = _get_redirect_uri(secrets)

        params = {
            "client_id":     client_id,
            "redirect_uri":  redirect_uri,
            "response_type": "code",
            "scope":         " ".join(SCOPES),
            "access_type":   "offline",
            "prompt":        "consent",
        }

        url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
        logging.info(f"[AUTH] URL gerada OK | redirect_uri: {redirect_uri}")
        secrets_com_redirect = dict(secrets)
        secrets_com_redirect["_redirect_uri"] = redirect_uri
        return True, url, secrets_com_redirect

    except Exception as ex:
        logging.exception(f"[AUTH] gerar_url_autorizacao: {ex}")
        return False, str(ex), None


def extrair_codigo_da_url(url: str) -> str | None:
    try:
        params = parse_qs(urlparse(url).query)
        codigos = params.get("code", [])
        return codigos[0] if codigos else None
    except Exception:
        return None


def is_redirect_url(url: str) -> bool:
    """Verifica se a URL e um redirect OAuth -- localhost, reverse scheme ou koios.app.br."""
    if "code=" not in url:
        return False
    return (url.startswith("http://localhost") or
            url.startswith("com.googleusercontent.apps.") or
            "koios.app.br" in url)


def trocar_codigo_por_token(secrets, codigo: str) -> tuple:
    """
    Troca codigo por token usando urllib puro -- sem wsgiref.
    secrets: dict retornado por gerar_url_autorizacao()
    """
    try:
        import urllib.request
        from google.oauth2.credentials import Credentials

        codigo = codigo.strip()
        if not codigo:
            return False, "Codigo invalido.", {}

        client_id     = secrets.get("client_id", "")
        client_secret = secrets.get("client_secret", "")
        token_uri     = secrets.get("token_uri", "https://oauth2.googleapis.com/token")
        redirect_uri  = secrets.get("_redirect_uri", "http://localhost")

        troca = {
            "code":         codigo,
            "client_id":    client_id,
            "redirect_uri": redirect_uri,
            "grant_type":   "authorization_code",
        }
        if client_secret:
            troca["client_secret"] = client_secret

        data = urlencode(troca).encode("utf-8")

        req = urllib.request.Request(
            token_uri,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                token_data = json.loads(resp.read().decode())
        except Exception as http_ex:
            body = getattr(http_ex, "read", lambda: b"")()
            if callable(body): body = body()
            raise Exception(f"HTTP error: {http_ex} | {body[:300] if body else ''}")

        access_token  = token_data.get("access_token", "")
        refresh_token = token_data.get("refresh_token", "")

        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )
        _salvar_creds(creds)

        perfil = _perfil_do_token(access_token)
        _salvar_perfil_no_banco(perfil)
        logging.info(f"[AUTH] Android OAuth OK: {perfil.get('email','?')}")
        return True, "ok", perfil

    except Exception as ex:
        logging.exception(f"[AUTH] trocar_codigo_por_token: {ex}")
        return False, str(ex), {}


def login_google_desktop() -> tuple:
    if _is_android():
        return False, "login_google_desktop nao disponivel no Android", {}
    try:
        if not os.path.exists(_SECRETS_PATH):
            return False, "client_secrets.json nao encontrado.", {}

        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds = None
        if os.path.exists(_CREDS_PATH):
            try:
                creds = Credentials.from_authorized_user_file(_CREDS_PATH, SCOPES)
            except Exception:
                creds = None

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds or not creds.valid:
            flow  = InstalledAppFlow.from_client_secrets_file(_SECRETS_PATH, SCOPES)
            creds = flow.run_local_server(port=0, open_browser=True)

        _salvar_creds(creds)
        perfil = _perfil_do_token(creds.token)
        _salvar_perfil_no_banco(perfil)
        logging.info(f"[AUTH] Desktop OAuth OK: {perfil.get('email','?')}")
        return True, "ok", perfil

    except Exception as ex:
        logging.exception(f"[AUTH] login_google_desktop: {ex}")
        return False, str(ex), {}
