# -*- coding: utf-8 -*-
# SHARED | backup/db_backup.py -- gerenciado por flet_shared/sync_shared.py
"""
Backup e restauracao de bancos SQLite no Google Drive.
Compartilhado entre todos os apps Koios.

Uso em cada app:
    from backup.db_backup import BackupConfig, fazer_backup, restaurar_backup

    CONFIG = BackupConfig(
        pasta_raiz="Koios_MeuApp",
        dbs={
            "meuapp_db": "/caminho/absoluto/meuapp.db",
            "koios_db":  "/caminho/absoluto/koios.db",
        },
        hist_path="/caminho/historico.json",
        hash_path="/caminho/hashes.json",
    )

    ok, msg = fazer_backup(CONFIG, forcar=True)
    ok, msg = restaurar_backup(CONFIG)
    ok, msg = sincronizar_ao_iniciar(CONFIG)

Implementacao: urllib puro (sem google-auth).
Funciona em Android sem --source-packages extras.
"""
import hashlib
import json
import logging
import os
import secrets
import shutil
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import urlencode
from typing import Optional

log = logging.getLogger(__name__)

_DRIVE_FILES  = "https://www.googleapis.com/drive/v3/files"
_DRIVE_UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"


# ── Configuracao por app ──────────────────────────────────────────────────────

@dataclass
class BackupConfig:
    """Define o que e onde fazer backup para um app especifico."""
    pasta_raiz:   str        # Pasta raiz no Drive (ex: "Koios_Prontuario")
    dbs:          dict       # {subfolder_drive: caminho_absoluto_db}
    hist_path:    str        # JSON de historico de backups local
    hash_path:    str        # JSON de hashes para detectar mudancas
    max_arquivos: int = 5    # Quantos backups manter por DB no Drive


# ── MD5 e hashes ─────────────────────────────────────────────────────────────

def _md5(caminho: str) -> str:
    try:
        h = hashlib.md5()
        with open(caminho, "rb") as f:
            for bloco in iter(lambda: f.read(65536), b""):
                h.update(bloco)
        return h.hexdigest()
    except Exception:
        return ""


def _carregar_hashes(config: BackupConfig) -> dict:
    try:
        if os.path.exists(config.hash_path):
            with open(config.hash_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _salvar_hashes(config: BackupConfig, hashes: dict) -> None:
    try:
        os.makedirs(os.path.dirname(config.hash_path), exist_ok=True)
        with open(config.hash_path, "w", encoding="utf-8") as f:
            json.dump(hashes, f, indent=2)
    except Exception as ex:
        log.warning("[BACKUP] salvar_hashes: %s", ex)


def houve_mudanca(config: BackupConfig) -> bool:
    """Retorna True se algum DB mudou desde o ultimo backup registrado."""
    antigos = _carregar_hashes(config)
    atuais  = {k: _md5(v) for k, v in config.dbs.items()}
    return antigos != atuais


# ── Token (urllib, sem google-auth) ──────────────────────────────────────────

def _creds_path() -> str:
    try:
        from shared.auth import _CREDS_PATH
        return _CREDS_PATH
    except Exception:
        return ""


def _obter_token() -> str:
    """Retorna access_token valido, renovando via urllib se expirado."""
    path = _creds_path()
    if not path or not os.path.exists(path):
        raise RuntimeError("Faca login primeiro. Credenciais nao encontradas.")
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

    refresh = data.get("refresh_token", "")
    if not refresh:
        raise RuntimeError("Sessao expirada. Faca login novamente.")

    payload = urlencode({
        "client_id":     data.get("client_id", ""),
        "client_secret": data.get("client_secret", ""),
        "refresh_token": refresh,
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
        raise RuntimeError(f"Falha ao renovar token: {resp.get('error', '?')}")

    data["token"] = resp["access_token"]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return resp["access_token"]


# ── Primitivos Drive REST ─────────────────────────────────────────────────────

def _drive_get(token: str, url: str, params: dict = None) -> dict:
    url = url + ("?" + urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _drive_post_json(token: str, url: str, body: dict,
                     params: dict = None) -> dict:
    url = url + ("?" + urlencode(params) if params else "")
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
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
        if e.code not in (200, 204, 404):
            raise


def _drive_upload_arquivo(token: str, caminho: str, nome: str,
                          pasta_id: str) -> Optional[str]:
    boundary = "koios_" + secrets.token_hex(8)
    meta = json.dumps({"name": nome, "parents": [pasta_id]}).encode()
    with open(caminho, "rb") as f:
        conteudo = f.read()
    body = (
        f"--{boundary}\r\nContent-Type: application/json\r\n\r\n".encode()
        + meta
        + f"\r\n--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n".encode()
        + conteudo
        + f"\r\n--{boundary}--\r\n".encode()
    )
    req = urllib.request.Request(
        f"{_DRIVE_UPLOAD}?uploadType=multipart&fields=id",
        data=body,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": f"multipart/related; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read()).get("id")


def _drive_download_arquivo(token: str, file_id: str, destino: str) -> bool:
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
                     order: str = "createdTime asc") -> list:
    return _drive_get(token, _DRIVE_FILES, {
        "q":       f"'{pasta_id}' in parents and trashed=false",
        "fields":  "files(id,name,size,createdTime)",
        "orderBy": order,
    }).get("files", [])


def _garantir_pasta(token: str, nome: str, pai_id: str = None) -> str:
    q = (f"name='{nome}' and mimeType='application/vnd.google-apps.folder'"
         f" and trashed=false")
    if pai_id:
        q += f" and '{pai_id}' in parents"
    arqs = _drive_get(token, _DRIVE_FILES,
                      {"q": q, "fields": "files(id)"}).get("files", [])
    if arqs:
        return arqs[0]["id"]
    meta: dict = {"name": nome, "mimeType": "application/vnd.google-apps.folder"}
    if pai_id:
        meta["parents"] = [pai_id]
    return _drive_post_json(token, _DRIVE_FILES, meta, {"fields": "id"})["id"]


def _estrutura_pastas(token: str, config: BackupConfig) -> dict:
    raiz = _garantir_pasta(token, config.pasta_raiz)
    return {k: _garantir_pasta(token, k, raiz) for k in config.dbs}


def _rotacionar(token: str, pasta_id: str, max_arqs: int) -> None:
    arqs = _listar_arquivos(token, pasta_id, "createdTime asc")
    for arq in (arqs[:-max_arqs] if len(arqs) > max_arqs else []):
        try:
            _drive_delete(token, arq["id"])
        except Exception as ex:
            log.warning("[BACKUP] rotacao: %s", ex)


# ── Historico local ───────────────────────────────────────────────────────────

def carregar_historico(config: BackupConfig) -> list:
    try:
        if os.path.exists(config.hist_path):
            with open(config.hist_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _registrar_historico(config: BackupConfig, ts: str, enviados: int) -> None:
    hist = carregar_historico(config)
    hist.insert(0, {
        "ts":       ts,
        "data_fmt": time.strftime("%d/%m/%Y %H:%M",
                                  time.strptime(ts, "%Y%m%d_%H%M%S")),
        "enviados": enviados,
        "status":   "ok",
    })
    hist = hist[:10]
    try:
        os.makedirs(os.path.dirname(config.hist_path), exist_ok=True)
        with open(config.hist_path, "w", encoding="utf-8") as f:
            json.dump(hist, f, indent=2, ensure_ascii=False)
    except Exception as ex:
        log.warning("[BACKUP] historico: %s", ex)


# ── API publica ───────────────────────────────────────────────────────────────

def verificar_credenciais() -> tuple:
    try:
        _obter_token()
        return True, ""
    except RuntimeError as ex:
        return False, str(ex)
    except Exception as ex:
        return False, f"Erro: {str(ex)[:100]}"


def fazer_backup(config: BackupConfig, forcar: bool = False,
                 callback=None) -> tuple:
    """
    Faz backup de todos os DBs do config para o Drive.
    forcar=True: ignora deteccao de mudancas.
    callback(msg): chamado com mensagens de progresso.
    Retorna (bool, str).
    """
    def _prog(msg: str) -> None:
        log.debug("[BACKUP] %s", msg)
        if callback:
            try:
                callback(msg)
            except Exception:
                pass

    tmp_files: list = []
    try:
        if not forcar:
            _prog("Verificando mudancas...")
            if not houve_mudanca(config):
                return True, "Sem mudancas desde o ultimo backup."

        _prog("Verificando autenticacao...")
        token = _obter_token()

        _prog("Preparando pastas no Drive...")
        ids = _estrutura_pastas(token, config)

        ts      = time.strftime("%Y%m%d_%H%M%S")
        tmp_dir = os.path.dirname(config.hash_path)
        os.makedirs(tmp_dir, exist_ok=True)
        enviados = 0

        for nome_sub, caminho_db in config.dbs.items():
            if not os.path.exists(caminho_db):
                log.warning("[BACKUP] DB ausente: %s", caminho_db)
                continue
            _prog(f"Enviando {os.path.basename(caminho_db)}...")
            tmp = os.path.join(tmp_dir, f"_tmp_{nome_sub}_{ts}.db")
            shutil.copy2(caminho_db, tmp)
            tmp_files.append(tmp)
            fid = _drive_upload_arquivo(token, tmp, f"{nome_sub}_{ts}.db",
                                        ids[nome_sub])
            if fid:
                _rotacionar(token, ids[nome_sub], config.max_arquivos)
                enviados += 1
                log.info("[BACKUP] enviado: %s", caminho_db)

        _salvar_hashes(config, {k: _md5(v) for k, v in config.dbs.items()})
        _registrar_historico(config, ts, enviados)

        msg = f"Backup concluido — {enviados} banco(s) enviado(s)"
        _prog(msg)
        return True, msg

    except RuntimeError as ex:
        return False, str(ex)
    except Exception as ex:
        log.exception("[BACKUP] Erro inesperado")
        return False, f"Erro: {str(ex)[:120]}"
    finally:
        for tmp in tmp_files:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass


def restaurar_backup(config: BackupConfig, callback=None) -> tuple:
    """
    Restaura o backup mais recente do Drive para cada DB.
    Retorna (bool, str).
    """
    def _prog(msg: str) -> None:
        log.info("[RESTORE] %s", msg)
        if callback:
            try:
                callback(msg)
            except Exception:
                pass

    tmp_files: list = []
    tmp_dir = os.path.dirname(config.hash_path)

    try:
        _prog("Verificando autenticacao...")
        token = _obter_token()

        _prog("Localizando backups no Drive...")
        ids = _estrutura_pastas(token, config)
        restaurados = 0

        for nome_sub, caminho_db in config.dbs.items():
            _prog(f"Baixando {nome_sub}...")
            arqs = _listar_arquivos(token, ids[nome_sub], "createdTime desc")
            if not arqs:
                log.warning("[RESTORE] Sem backup no Drive: %s", nome_sub)
                continue
            tmp = os.path.join(tmp_dir, f"_restore_{nome_sub}.db")
            tmp_files.append(tmp)
            if _drive_download_arquivo(token, arqs[0]["id"], tmp):
                os.makedirs(os.path.dirname(caminho_db), exist_ok=True)
                shutil.copy2(tmp, caminho_db)
                restaurados += 1
                log.info("[RESTORE] restaurado: %s <- %s", caminho_db, arqs[0]["name"])

        msg = f"Restauracao concluida! {restaurados} banco(s) recuperado(s)."
        _prog(msg)
        return True, msg

    except RuntimeError as ex:
        return False, str(ex)
    except Exception as ex:
        log.exception("[RESTORE] Erro inesperado")
        return False, f"Erro: {str(ex)[:120]}"
    finally:
        for tmp in tmp_files:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass


def listar_backups_drive(config: BackupConfig) -> tuple:
    """Lista backups disponíveis no Drive. Retorna (bool, dict)."""
    try:
        token = _obter_token()
        ids   = _estrutura_pastas(token, config)
        resultado = {}
        for sub, pid in ids.items():
            arqs = _listar_arquivos(token, pid, "createdTime desc")
            resultado[sub] = [
                {
                    "id":        a["id"],
                    "nome":      a["name"],
                    "tamanho":   int(a.get("size", 0)),
                    "criado_em": a.get("createdTime", ""),
                }
                for a in arqs
            ]
        return True, resultado
    except RuntimeError:
        return False, {}
    except Exception:
        log.exception("[BACKUP] listar_drive")
        return False, {}


def sincronizar_ao_iniciar(config: BackupConfig, callback=None) -> tuple:
    """
    Estrategia de sync no startup:
    - Drive sem backup → faz backup local→Drive (primeiro uso / nova instalacao)
    - Banco local ausente → restaura Drive→local
    - Drive mais recente (>60s) → restaura Drive→local
    - Banco local atualizado → nada
    Retorna (bool, str).
    """
    import datetime as _dt

    def _prog(msg: str) -> None:
        log.debug("[SYNC_INIT] %s", msg)
        if callback:
            try:
                callback(msg)
            except Exception:
                pass

    try:
        if not os.path.exists(_creds_path()):
            return True, "Sem credenciais"

        _prog("Verificando autenticacao...")
        token = _obter_token()
        ids   = _estrutura_pastas(token, config)

        # DB principal: primeiro da lista
        primeiro_sub     = next(iter(config.dbs))
        caminho_principal = config.dbs[primeiro_sub]
        pasta_principal  = ids[primeiro_sub]

        arqs = _listar_arquivos(token, pasta_principal, "createdTime desc")

        if not arqs:
            # Drive vazio: envia banco local (primeiro uso)
            if os.path.exists(caminho_principal):
                _prog("Drive vazio — fazendo backup inicial...")
                return fazer_backup(config, forcar=True, callback=callback)
            return True, "Sem banco local e sem backup — novo usuario"

        # Banco local ausente: restaurar do Drive
        if not os.path.exists(caminho_principal):
            _prog("Banco local ausente — restaurando do Drive...")
            return restaurar_backup(config, callback)

        # Comparar timestamps
        ts_str = arqs[0].get("createdTime", "")
        try:
            drive_dt = _dt.datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S")
            drive_ts = drive_dt.replace(tzinfo=_dt.timezone.utc).timestamp()
        except Exception:
            return True, "Nao foi possivel verificar data do Drive"

        local_mtime = os.path.getmtime(caminho_principal)

        if drive_ts > local_mtime + 60:
            _prog("Drive mais recente — sincronizando...")
            return restaurar_backup(config, callback)

        return True, "Banco local atualizado"

    except RuntimeError:
        return True, "Sem credenciais validas"
    except Exception as ex:
        log.warning("[SYNC_INIT] Erro: %s", ex)
        return False, str(ex)[:120]
