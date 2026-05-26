# -*- coding: utf-8 -*-
"""
prontuario/backup/drive_backup.py
Backup e restauracao do banco no Google Drive.

Estrutura de pastas no Drive:
    Koios/Prontuario/
    └── prontuario_db/  -> prontuario.db  (arquivo unico, sobrescrito a cada backup)

Reutiliza credenciais do shared/auth.py (mycreds.json / dados/prontuario.db).
"""
import hashlib
import json
import logging
import os
import shutil
import time
from typing import Optional

log = logging.getLogger(__name__)

_HERE        = os.path.dirname(os.path.abspath(__file__))
_PRONTUARIO  = os.path.dirname(_HERE)
_DB_PATH     = os.path.join(_PRONTUARIO, "dados", "prontuario.db")
_HASH_PATH   = os.path.join(_PRONTUARIO, "dados", "ultimo_backup.json")
_HIST_PATH   = os.path.join(_PRONTUARIO, "dados", "historico_backup.json")
_CREDS_PATH  = os.path.join(_PRONTUARIO, "mycreds.json")

_PASTA_KOIOS      = "Eco_Koios"
_PASTA_PRONTUARIO = "Prontuario"
_PASTA_DB         = "prontuario_db"
_NOME_DB          = "app.db"

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
]


# ── MD5 ───────────────────────────────────────────────────────────────────────

def _md5(caminho: str) -> str:
    try:
        h = hashlib.md5()
        with open(caminho, "rb") as f:
            for bloco in iter(lambda: f.read(65536), b""):
                h.update(bloco)
        return h.hexdigest()
    except Exception:
        return ""


def _carregar_hashes() -> dict:
    try:
        if os.path.exists(_HASH_PATH):
            with open(_HASH_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _salvar_hashes(hashes: dict) -> None:
    try:
        with open(_HASH_PATH, "w", encoding="utf-8") as f:
            json.dump(hashes, f, indent=2)
    except Exception as ex:
        log.warning("[Backup] erro ao salvar hashes: %s", ex)


def houve_mudanca() -> bool:
    ant = _carregar_hashes()
    agora = {"db": _md5(_DB_PATH)}
    return ant != agora


# ── Credenciais ───────────────────────────────────────────────────────────────

def _obter_creds():
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        if not os.path.exists(_CREDS_PATH):
            raise RuntimeError("mycreds.json nao encontrado — faca login primeiro.")

        creds = Credentials.from_authorized_user_file(_CREDS_PATH, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(_CREDS_PATH, "w") as f:
                f.write(creds.to_json())

        if not creds or not creds.valid:
            raise RuntimeError("Credenciais invalidas — faca login novamente.")

        return creds
    except ImportError:
        raise RuntimeError("google-auth-oauthlib nao instalado.")


import urllib.request as _urllib_req
import urllib.parse as _urllib_parse

_DRIVE_FILES  = "https://www.googleapis.com/drive/v3/files"
_DRIVE_UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"


def _drive_req(url: str, creds, method: str = "GET",
               body: bytes = None, extra_headers: dict = None) -> dict:
    headers = {"Authorization": f"Bearer {creds.token}",
               "Content-Type":  "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    req = _urllib_req.Request(url, data=body, headers=headers, method=method)
    with _urllib_req.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def verificar_credenciais() -> tuple:
    try:
        _obter_creds()
        return True, ""
    except RuntimeError as ex:
        return False, str(ex)
    except Exception as ex:
        return False, str(ex)[:100]


# ── Pastas no Drive ───────────────────────────────────────────────────────────

def _obter_ou_criar_pasta(creds, nome: str, pai_id: Optional[str] = None) -> str:
    q = (f"name='{nome}' and mimeType='application/vnd.google-apps.folder'"
         f" and trashed=false")
    if pai_id:
        q += f" and '{pai_id}' in parents"
    url  = _DRIVE_FILES + "?" + _urllib_parse.urlencode(
        {"q": q, "fields": "files(id)", "spaces": "drive"})
    res  = _drive_req(url, creds)
    arqs = res.get("files", [])
    if arqs:
        return arqs[0]["id"]
    meta = {"name": nome, "mimeType": "application/vnd.google-apps.folder"}
    if pai_id:
        meta["parents"] = [pai_id]
    res = _drive_req(_DRIVE_FILES + "?fields=id", creds, method="POST",
                     body=json.dumps(meta).encode())
    log.info("[Backup] pasta criada no Drive: %s", nome)
    return res["id"]


def _id_pasta_db(creds) -> str:
    koios_id      = _obter_ou_criar_pasta(creds, _PASTA_KOIOS)
    prontuario_id = _obter_ou_criar_pasta(creds, _PASTA_PRONTUARIO, koios_id)
    return _obter_ou_criar_pasta(creds, _PASTA_DB, prontuario_id)


# ── Upload / Download (urllib multipart, sem googleapiclient) ─────────────────

def _id_existente(creds, pasta_id: str, nome: str) -> Optional[str]:
    url  = _DRIVE_FILES + "?" + _urllib_parse.urlencode({
        "q":      f"'{pasta_id}' in parents and name='{nome}' and trashed=false",
        "fields": "files(id)",
    })
    res  = _drive_req(url, creds)
    arqs = res.get("files", [])
    return arqs[0]["id"] if arqs else None


def _upload_db(creds, caminho_tmp: str, pasta_id: str) -> Optional[str]:
    try:
        with open(caminho_tmp, "rb") as f:
            dados = f.read()
        boundary = b"koios_backup_boundary"
        mime     = b"application/octet-stream"
        existente = _id_existente(creds, pasta_id, _NOME_DB)
        if existente:
            meta = json.dumps({}).encode()
            url  = (_DRIVE_UPLOAD + f"/{existente}"
                    + "?uploadType=multipart&fields=id")
            meth = "PATCH"
        else:
            meta = json.dumps({"name": _NOME_DB, "parents": [pasta_id]}).encode()
            url  = _DRIVE_UPLOAD + "?uploadType=multipart&fields=id"
            meth = "POST"
        body = (b"--" + boundary
                + b"\r\nContent-Type: application/json\r\n\r\n" + meta
                + b"\r\n--" + boundary
                + b"\r\nContent-Type: " + mime + b"\r\n\r\n" + dados
                + b"\r\n--" + boundary + b"--")
        hdrs = {"Content-Type": f"multipart/related; boundary={boundary.decode()}"}
        res  = _drive_req(url, creds, method=meth, body=body, extra_headers=hdrs)
        return res.get("id")
    except Exception as ex:
        log.exception("[Backup] erro no upload: %s", ex)
        return None


# ── API publica ───────────────────────────────────────────────────────────────

def fazer_backup(forcar: bool = False, callback_progresso=None) -> tuple:
    def _prog(msg):
        log.debug("[Backup] %s", msg)
        if callback_progresso:
            try: callback_progresso(msg)
            except Exception: pass

    tmp = None
    try:
        if not forcar:
            _prog("Verificando mudancas...")
            if not houve_mudanca():
                return True, "Sem mudancas desde o ultimo backup."

        _prog("Verificando autenticacao...")
        creds = _obter_creds()

        _prog("Preparando pasta no Drive...")
        pasta_id = _id_pasta_db(creds)

        _prog("Enviando banco de dados...")
        ts  = time.strftime("%Y%m%d_%H%M%S")
        tmp = os.path.join(_PRONTUARIO, "dados", f"_tmp_backup_{ts}.db")
        import sqlite3 as _sq
        with _sq.connect(_DB_PATH, timeout=30) as _src:
            with _sq.connect(tmp) as _dst:
                _src.backup(_dst)

        fid = _upload_db(creds, tmp, pasta_id)
        if not fid:
            return False, "Falha no upload para o Drive."

        _salvar_hashes({"db": _md5(_DB_PATH)})
        _registrar_historico(ts, 1)

        msg = "Backup concluido — 1 banco(s) enviado(s)"
        _prog(msg)
        log.info("[Backup] %s", msg)
        return True, msg

    except RuntimeError as ex:
        log.error("[Backup] %s", ex)
        return False, str(ex)
    except Exception as ex:
        log.exception("[Backup] erro inesperado: %s", ex)
        return False, f"Erro inesperado: {str(ex)[:120]}"
    finally:
        if tmp and os.path.exists(tmp):
            try: os.remove(tmp)
            except Exception: pass


def restaurar_backup_completo(callback_progresso=None) -> tuple:
    def _prog(msg):
        log.info("[RESTORE] %s", msg)
        if callback_progresso:
            try: callback_progresso(msg)
            except Exception: pass

    tmp = None
    try:
        _prog("Verificando autenticacao...")
        creds = _obter_creds()

        _prog("Localizando backups no Drive...")
        pasta_id = _id_pasta_db(creds)

        _prog("Baixando prontuario_db...")
        url  = _DRIVE_FILES + "?" + _urllib_parse.urlencode({
            "q":        f"'{pasta_id}' in parents and name='{_NOME_DB}' and trashed=false",
            "fields":   "files(id,name,modifiedTime)",
            "pageSize": 1,
        })
        res  = _drive_req(url, creds)
        arqs = res.get("files", [])
        if not arqs:
            return False, "Nenhum backup encontrado no Drive."

        tmp = os.path.join(_PRONTUARIO, "dados", "_restore_tmp.db")
        dl_url = (_DRIVE_FILES + f"/{arqs[0]['id']}"
                  + "?" + _urllib_parse.urlencode({"alt": "media"}))
        req = _urllib_req.Request(
            dl_url,
            headers={"Authorization": f"Bearer {creds.token}"},
            method="GET",
        )
        with _urllib_req.urlopen(req, timeout=120) as resp:
            with open(tmp, "wb") as f:
                f.write(resp.read())

        shutil.copy2(tmp, _DB_PATH)
        log.info("[RESTORE] banco restaurado: %s", arqs[0].get("name", "?"))
        return True, "Restauracao concluida."

    except RuntimeError as ex:
        log.error("[RESTORE] %s", ex)
        return False, str(ex)
    except Exception as ex:
        log.exception("[RESTORE] erro inesperado: %s", ex)
        return False, f"Erro inesperado: {str(ex)[:120]}"
    finally:
        if tmp and os.path.exists(tmp):
            try: os.remove(tmp)
            except Exception: pass


def sincronizar_ao_iniciar(callback_progresso=None) -> tuple:
    """
    Startup sync:
    - Drive mais recente (modifiedTime > mtime local + 60s) -> restaura
    - Caso contrario -> usa banco local
    - Sem credenciais -> usa banco local silenciosamente
    """
    def _prog(msg):
        log.info("[RESTORE] %s", msg)
        if callback_progresso:
            try: callback_progresso(msg)
            except Exception: pass

    try:
        _prog("Verificando autenticacao...")
        creds = _obter_creds()

        _prog("Localizando backups no Drive...")
        pasta_id = _id_pasta_db(creds)

        url  = _DRIVE_FILES + "?" + _urllib_parse.urlencode({
            "q":        f"'{pasta_id}' in parents and name='{_NOME_DB}' and trashed=false",
            "fields":   "files(id,modifiedTime)",
            "pageSize": 1,
        })
        res  = _drive_req(url, creds)
        arqs = res.get("files", [])

        if not arqs:
            if not os.path.exists(_DB_PATH):
                return True, "Sem banco local e sem backup — novo usuario."
            return True, "Banco local disponivel — Drive vazio."

        import datetime as _dt
        ts_str   = arqs[0].get("modifiedTime", "")
        drive_dt = _dt.datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S")
        drive_ts = drive_dt.replace(tzinfo=_dt.timezone.utc).timestamp()

        if not os.path.exists(_DB_PATH):
            _prog("Banco local ausente — restaurando do Drive...")
            return restaurar_backup_completo(callback_progresso)

        local_mtime = os.path.getmtime(_DB_PATH)
        if drive_ts > local_mtime + 60:
            _prog("Drive mais recente — sincronizando...")
            return restaurar_backup_completo(callback_progresso)

        return True, "Banco local atualizado."

    except RuntimeError:
        return True, "Sem credenciais validas — usando banco local."
    except Exception as ex:
        log.exception("[RESTORE] sincronizar_ao_iniciar: %s", ex)
        return True, "Erro no sync — usando banco local."


def carregar_historico() -> list:
    try:
        if os.path.exists(_HIST_PATH):
            with open(_HIST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _registrar_historico(ts: str, enviados: int) -> None:
    hist = carregar_historico()
    hist.insert(0, {
        "ts":       ts,
        "data_fmt": time.strftime("%d/%m/%Y %H:%M",
                                  time.strptime(ts, "%Y%m%d_%H%M%S")),
        "enviados": enviados,
        "status":   "ok",
    })
    hist = hist[:5]
    try:
        with open(_HIST_PATH, "w", encoding="utf-8") as f:
            json.dump(hist, f, indent=2, ensure_ascii=False)
    except Exception as ex:
        log.warning("[Backup] erro ao salvar historico: %s", ex)


def listar_backups_drive() -> tuple:
    try:
        creds    = _obter_creds()
        pasta_id = _id_pasta_db(creds)
        url  = _DRIVE_FILES + "?" + _urllib_parse.urlencode({
            "q":       f"'{pasta_id}' in parents and trashed=false",
            "fields":  "files(id,name,size,modifiedTime)",
            "orderBy": "modifiedTime desc",
        })
        res  = _drive_req(url, creds)
        arqs = [{"id": f["id"], "nome": f["name"],
                 "tamanho": int(f.get("size", 0)),
                 "criado_em": f.get("modifiedTime", "")}
                for f in res.get("files", [])]
        return True, {"prontuario_db": arqs}
    except Exception as ex:
        log.exception("[Backup] listar: %s", ex)
        return False, {}


def get_email_drive() -> str:
    try:
        import sqlite3
        from dados.model_prontuario import DB_PATH
        conn = sqlite3.connect(DB_PATH, timeout=10)
        r = conn.execute(
            "SELECT valor FROM config WHERE chave='usuario_email' LIMIT 1"
        ).fetchone()
        conn.close()
        return r[0] if r else ""
    except Exception:
        return ""
