# -*- coding: utf-8 -*-
"""
prontuario/backup/drive_backup.py
Backup / Restore no Google Drive via urllib puro.
Sem dependência de google-auth ou googleapiclient — funciona no APK Android.
"""

import hashlib
import json
import logging
import os
import secrets
import shutil
import time
import urllib.request
import urllib.error
from urllib.parse import urlencode
from typing import Optional

log = logging.getLogger(__name__)

_HERE         = os.path.dirname(os.path.abspath(__file__))
_PRONTUARIO   = os.path.dirname(_HERE)
_KOIOS_ROOT   = os.path.dirname(_PRONTUARIO)

_HASH_PATH    = os.path.join(_KOIOS_ROOT, "database", "ultimo_backup_prontuario.json")
_HIST_PATH    = os.path.join(_KOIOS_ROOT, "database", "historico_backup_prontuario.json")

_PASTA_RAIZ   = "Koios_Prontuario"
_MAX_ARQUIVOS = 5

_PRONTUARIO_DB = os.path.join(_PRONTUARIO, "dados", "prontuario.db")
_KOIOS_DB      = os.path.join(_KOIOS_ROOT, "database", "koios.db")

_DRIVE_FILES  = "https://www.googleapis.com/drive/v3/files"
_DRIVE_UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"


def _creds_path() -> str:
    try:
        from shared.auth import _CREDS_PATH
        return _CREDS_PATH
    except Exception:
        return os.path.join(_KOIOS_ROOT, "mycreds.json")


# ── MD5 ───────────────────────────────────────────────────────────────────────

def _md5_arquivo(caminho: str) -> str:
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
    except Exception as exc:
        log.warning("[Backup] Erro ao carregar hashes: %s", exc)
    return {}


def _salvar_hashes(hashes: dict) -> None:
    try:
        os.makedirs(os.path.dirname(_HASH_PATH), exist_ok=True)
        with open(_HASH_PATH, "w", encoding="utf-8") as f:
            json.dump(hashes, f, indent=2)
    except Exception as exc:
        log.warning("[Backup] Erro ao salvar hashes: %s", exc)


def _calcular_hashes_atuais() -> dict:
    return {
        "prontuario_db": _md5_arquivo(_PRONTUARIO_DB),
        "koios_db":      _md5_arquivo(_KOIOS_DB),
    }


def houve_mudanca() -> bool:
    return _carregar_hashes() != _calcular_hashes_atuais()


# ── Token (sem google-auth) ───────────────────────────────────────────────────

def _obter_token() -> str:
    """Retorna access_token válido, renovando via urllib se expirado."""
    path = _creds_path()
    if not os.path.exists(path):
        raise RuntimeError("Faça login primeiro. mycreds.json não encontrado.")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    token = data.get("token") or data.get("access_token", "")

    if token:
        try:
            req = urllib.request.Request(
                f"https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={token}",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                info = json.loads(r.read())
            if "error" not in info and int(info.get("expires_in", 0)) > 60:
                return token
        except Exception:
            pass

    refresh_token = data.get("refresh_token", "")
    if not refresh_token:
        raise RuntimeError("Sessão expirada. Faça login novamente.")

    payload = urlencode({
        "client_id":     data.get("client_id", ""),
        "client_secret": data.get("client_secret", ""),
        "refresh_token": refresh_token,
        "grant_type":    "refresh_token",
    }).encode()

    req = urllib.request.Request(
        data.get("token_uri", "https://oauth2.googleapis.com/token"),
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read())

    if "access_token" not in resp:
        raise RuntimeError(f"Falha ao renovar token: {resp.get('error', 'unknown')}")

    data["token"] = resp["access_token"]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    return resp["access_token"]


# ── Helpers Drive REST ────────────────────────────────────────────────────────

def _drive_get(token: str, endpoint: str, params: dict = None) -> dict:
    url = endpoint + ("?" + urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _drive_post_json(token: str, endpoint: str, body: dict,
                     params: dict = None) -> dict:
    url = endpoint + ("?" + urlencode(params) if params else "")
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _drive_delete(token: str, file_id: str) -> None:
    req = urllib.request.Request(
        f"{_DRIVE_FILES}/{file_id}",
        headers={"Authorization": f"Bearer {token}"},
        method="DELETE",
    )
    try:
        urllib.request.urlopen(req, timeout=30).close()
    except urllib.error.HTTPError as e:
        if e.code not in (204, 200):
            raise


def _drive_upload(token: str, caminho: str, nome: str,
                  pasta_id: str) -> Optional[str]:
    boundary = "koios_" + secrets.token_hex(8)
    meta = json.dumps({"name": nome, "parents": [pasta_id]}).encode()

    with open(caminho, "rb") as f:
        file_bytes = f.read()

    body = (
        f"--{boundary}\r\nContent-Type: application/json\r\n\r\n".encode()
        + meta
        + f"\r\n--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n".encode()
        + file_bytes
        + f"\r\n--{boundary}--\r\n".encode()
    )

    req = urllib.request.Request(
        f"{_DRIVE_UPLOAD}?uploadType=multipart&fields=id",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  f"multipart/related; boundary={boundary}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read()).get("id")


def _drive_download(token: str, file_id: str, destino: str) -> bool:
    req = urllib.request.Request(
        f"{_DRIVE_FILES}/{file_id}?alt=media",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "wb") as f:
            f.write(r.read())
    return True


def _listar_arquivos(token: str, pasta_id: str,
                     order_by: str = "createdTime asc") -> list:
    return _drive_get(token, _DRIVE_FILES, {
        "q":       f"'{pasta_id}' in parents and trashed=false",
        "fields":  "files(id,name,size,createdTime)",
        "orderBy": order_by,
    }).get("files", [])


# ── Pastas Drive ──────────────────────────────────────────────────────────────

def _obter_ou_criar_pasta(token: str, nome: str,
                           pai_id: Optional[str] = None) -> str:
    q = (
        f"name='{nome}' and mimeType='application/vnd.google-apps.folder'"
        f" and trashed=false"
        + (f" and '{pai_id}' in parents" if pai_id else "")
    )
    arquivos = _drive_get(token, _DRIVE_FILES,
                          {"q": q, "fields": "files(id)"}).get("files", [])
    if arquivos:
        return arquivos[0]["id"]

    meta: dict = {"name": nome, "mimeType": "application/vnd.google-apps.folder"}
    if pai_id:
        meta["parents"] = [pai_id]
    return _drive_post_json(token, _DRIVE_FILES, meta, {"fields": "id"})["id"]


def _estrutura_pastas(token: str) -> dict:
    raiz_id = _obter_ou_criar_pasta(token, _PASTA_RAIZ)
    return {
        "prontuario_db": _obter_ou_criar_pasta(token, "prontuario_db", raiz_id),
        "koios_db":      _obter_ou_criar_pasta(token, "koios_db",      raiz_id),
    }


def _rotacionar(token: str, pasta_id: str) -> None:
    arquivos = _listar_arquivos(token, pasta_id, "createdTime asc")
    for arq in arquivos[:-_MAX_ARQUIVOS] if len(arquivos) > _MAX_ARQUIVOS else []:
        try:
            _drive_delete(token, arq["id"])
            log.info("[Backup] Rotação: deletado %s", arq["name"])
        except Exception as exc:
            log.warning("[Backup] Erro ao deletar arquivo antigo: %s", exc)


# ── API pública ────────────────────────────────────────────────────────────────

def verificar_credenciais() -> tuple[bool, str]:
    try:
        _obter_token()
        return True, ""
    except RuntimeError as ex:
        return False, str(ex)
    except Exception as ex:
        return False, f"Erro: {str(ex)[:100]}"


def fazer_backup(forcar: bool = False,
                 callback_progresso=None) -> tuple[bool, str]:
    def _prog(msg: str) -> None:
        log.debug("[Backup] %s", msg)
        if callback_progresso:
            try:
                callback_progresso(msg)
            except Exception:
                pass

    tmp_files: list = []

    try:
        if not forcar:
            _prog("Verificando mudanças...")
            if not houve_mudanca():
                return True, "Sem mudanças desde o último backup."

        _prog("Verificando autenticação...")
        token = _obter_token()

        _prog("Preparando pastas no Drive...")
        ids = _estrutura_pastas(token)

        ts      = time.strftime("%Y%m%d_%H%M%S")
        enviados = 0
        tmp_dir  = os.path.join(_KOIOS_ROOT, "database")
        os.makedirs(tmp_dir, exist_ok=True)

        if os.path.exists(_PRONTUARIO_DB):
            _prog("Enviando prontuario.db...")
            tmp = os.path.join(tmp_dir, f"_tmp_pron_{ts}.db")
            shutil.copy2(_PRONTUARIO_DB, tmp)
            tmp_files.append(tmp)
            fid = _drive_upload(token, tmp, f"prontuario_{ts}.db",
                                ids["prontuario_db"])
            if fid:
                _rotacionar(token, ids["prontuario_db"])
                enviados += 1
                log.info("[Backup] prontuario.db enviado")

        if os.path.exists(_KOIOS_DB):
            _prog("Enviando koios.db...")
            tmp = os.path.join(tmp_dir, f"_tmp_koios_{ts}.db")
            shutil.copy2(_KOIOS_DB, tmp)
            tmp_files.append(tmp)
            fid = _drive_upload(token, tmp, f"koios_{ts}.db", ids["koios_db"])
            if fid:
                _rotacionar(token, ids["koios_db"])
                enviados += 1
                log.info("[Backup] koios.db enviado")

        _salvar_hashes(_calcular_hashes_atuais())
        _registrar_historico(ts, enviados)

        msg = f"Backup concluído — {enviados} banco(s) enviado(s)"
        _prog(msg)
        return True, msg

    except RuntimeError as ex:
        return False, str(ex)
    except Exception as ex:
        log.exception("[Backup] Erro inesperado")
        return False, f"Erro inesperado: {str(ex)[:120]}"
    finally:
        for tmp in tmp_files:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass


def listar_backups_drive() -> tuple[bool, dict]:
    try:
        token     = _obter_token()
        ids       = _estrutura_pastas(token)
        resultado = {}
        for sub, pasta_id in ids.items():
            arquivos = _listar_arquivos(token, pasta_id, "createdTime desc")
            resultado[sub] = [
                {
                    "id":        f["id"],
                    "nome":      f["name"],
                    "tamanho":   int(f.get("size", 0)),
                    "criado_em": f.get("createdTime", ""),
                }
                for f in arquivos
            ]
        return True, resultado
    except RuntimeError:
        return False, {}
    except Exception:
        log.exception("[Backup] Erro ao listar")
        return False, {}


# ── Histórico local ────────────────────────────────────────────────────────────

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
        os.makedirs(os.path.dirname(_HIST_PATH), exist_ok=True)
        with open(_HIST_PATH, "w", encoding="utf-8") as f:
            json.dump(hist, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        log.warning("[Backup] Erro ao salvar histórico: %s", exc)


def carregar_historico() -> list[dict]:
    try:
        if os.path.exists(_HIST_PATH):
            with open(_HIST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


# ── Sincronização inicial (Drive → local) ────────────────────────────────────

def sincronizar_ao_iniciar(callback_progresso=None) -> tuple[bool, str]:
    """Ao iniciar: baixa do Drive se banco local ausente ou Drive tem versão mais nova."""
    import datetime as _dt

    def _prog(msg: str) -> None:
        log.debug("[SyncInit] %s", msg)
        if callback_progresso:
            try:
                callback_progresso(msg)
            except Exception:
                pass

    try:
        if not os.path.exists(_creds_path()):
            return True, "Sem credenciais"

        # Banco local ausente → restaurar sempre
        if not os.path.exists(_PRONTUARIO_DB):
            _prog("Banco local ausente — restaurando do Drive...")
            return restaurar_backup_completo(callback_progresso)

        _prog("Verificando versão no Drive...")
        token    = _obter_token()
        ids      = _estrutura_pastas(token)
        arquivos = _listar_arquivos(token, ids["prontuario_db"], "createdTime desc")

        if not arquivos:
            return True, "Sem backup no Drive — banco local mantido"

        # Comparar timestamps: Drive (UTC ISO 8601) vs mtime local (Unix ts)
        ts_str = arquivos[0].get("createdTime", "")
        try:
            drive_dt = _dt.datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S")
            drive_ts = drive_dt.replace(tzinfo=_dt.timezone.utc).timestamp()
        except Exception:
            return True, "Não foi possível verificar data do Drive"

        local_mtime = os.path.getmtime(_PRONTUARIO_DB)

        if drive_ts > local_mtime + 60:  # Drive mais novo por >1 min
            _prog("Drive mais recente — sincronizando...")
            return restaurar_backup_completo(callback_progresso)

        return True, "Banco local atualizado"

    except RuntimeError:
        return True, "Sem credenciais válidas"
    except Exception as ex:
        log.warning("[SyncInit] Erro: %s", ex)
        return False, str(ex)[:120]


# ── Restauração ────────────────────────────────────────────────────────────────

def restaurar_backup_completo(callback_progresso=None) -> tuple[bool, str]:
    def _prog(msg: str) -> None:
        log.info("[Restore] %s", msg)
        if callback_progresso:
            try:
                callback_progresso(msg)
            except Exception:
                pass

    tmp_files: list = []
    tmp_dir   = os.path.join(_KOIOS_ROOT, "database")

    try:
        _prog("Verificando autenticação...")
        token = _obter_token()

        _prog("Localizando backups no Drive...")
        ids = _estrutura_pastas(token)

        restaurados = 0

        _prog("Baixando prontuario.db...")
        arquivos = _listar_arquivos(token, ids["prontuario_db"], "createdTime desc")
        if arquivos:
            arq = arquivos[0]
            tmp = os.path.join(tmp_dir, "_restore_prontuario.db")
            tmp_files.append(tmp)
            if _drive_download(token, arq["id"], tmp):
                shutil.copy2(tmp, _PRONTUARIO_DB)
                restaurados += 1
                log.info("[Restore] prontuario.db: %s", arq["name"])
        else:
            log.warning("[Restore] Nenhum prontuario.db no Drive")

        _prog("Baixando koios.db...")
        arquivos = _listar_arquivos(token, ids["koios_db"], "createdTime desc")
        if arquivos:
            arq = arquivos[0]
            tmp = os.path.join(tmp_dir, "_restore_koios.db")
            tmp_files.append(tmp)
            if _drive_download(token, arq["id"], tmp):
                shutil.copy2(tmp, _KOIOS_DB)
                restaurados += 1
                log.info("[Restore] koios.db: %s", arq["name"])
        else:
            log.warning("[Restore] Nenhum koios.db no Drive")

        msg = f"Restauração concluída! {restaurados} banco(s) recuperado(s)."
        _prog(msg)
        return True, msg

    except RuntimeError as ex:
        return False, str(ex)
    except Exception as ex:
        log.exception("[Restore] Erro inesperado")
        return False, f"Erro inesperado: {str(ex)[:120]}"
    finally:
        for tmp in tmp_files:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
