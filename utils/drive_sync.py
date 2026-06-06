# -*- coding: utf-8 -*-
# SHARED | utils/drive_sync.py -- gerenciado por flet_shared/sync_shared.py
# --- SHARED PARAMS ---
_MP_BOUNDARY  = "prontuario_mp_"
_IMG_BOUNDARY = "prontuario_img_"
# --- END SHARED PARAMS ---
"""
DriveSync -- sincronizacao com Google Drive usando urllib puro.
Sem googleapiclient.discovery (evita roundtrip de network no Android).
"""

import os, json, logging, urllib.request, urllib.parse

_DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"
_UPLOAD_URL  = "https://www.googleapis.com/upload/drive/v3/files"

# ID da pasta de exames PDF no Drive (resolvido dinamicamente na primeira chamada)
_EXAMES_PDF_ID = None   # placeholder — _liberar usa garantir_pasta() se None


def _get_creds():
    """Le credenciais do mycreds.json e renova se expirado."""
    from shared.auth import _CREDS_PATH, SCOPES
    if not os.path.exists(_CREDS_PATH):
        raise FileNotFoundError("mycreds.json nao encontrado")
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    creds = Credentials.from_authorized_user_file(_CREDS_PATH, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            try:
                with open(_CREDS_PATH, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())
            except Exception as ex:
                logging.warning(f"[DRIVE] salvar creds: {ex}")
        else:
            raise Exception("Token invalido e sem refresh_token")
    return creds


def _req(url: str, creds, method: str = "GET",
         body: bytes = None, extra_headers: dict = None) -> dict:
    """Faz requisicao HTTP simples, retorna dict do JSON de resposta."""
    headers = {"Authorization": f"Bearer {creds.token}",
               "Content-Type":  "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def garantir_pasta(nome: str, pai_id: str = None, creds=None) -> str:
    """Encontra (ou cria) pasta com esse nome no Drive. Retorna o ID da pasta."""
    if creds is None:
        creds = _get_creds()
    q = f"name='{nome}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if pai_id:
        q += f" and '{pai_id}' in parents"
    url = _DRIVE_FILES + "?" + urllib.parse.urlencode({
        "q": q, "fields": "files(id,name)", "spaces": "drive",
    })
    result = _req(url, creds)
    files = result.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": nome, "mimeType": "application/vnd.google-apps.folder"}
    if pai_id:
        meta["parents"] = [pai_id]
    result = _req(_DRIVE_FILES, creds, method="POST",
                  body=json.dumps(meta).encode("utf-8"))
    return result["id"]


def upload_batch(eventos: list, nome_batch: str, pasta_id: str, creds=None) -> str:
    """
    Faz upload de um batch de eventos como arquivo JSON no Drive.
    Retorna o ID do arquivo criado.
    """
    if creds is None:
        creds = _get_creds()
    conteudo = json.dumps(eventos, ensure_ascii=False).encode("utf-8")
    boundary = _MP_BOUNDARY + nome_batch[:12].replace(".", "_")
    meta = json.dumps({
        "name": nome_batch, "parents": [pasta_id],
        "mimeType": "application/json",
    }).encode("utf-8")
    body  = b"--" + boundary.encode() + b"\r\n"
    body += b"Content-Type: application/json; charset=UTF-8\r\n\r\n"
    body += meta + b"\r\n"
    body += b"--" + boundary.encode() + b"\r\n"
    body += b"Content-Type: application/json\r\n\r\n"
    body += conteudo + b"\r\n"
    body += b"--" + boundary.encode() + b"--"
    url = _UPLOAD_URL + "?uploadType=multipart"
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": f"multipart/related; boundary={boundary}",
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result.get("id", "")


def listar_batches_novos(pasta_id: str, desde_ts: str = None, creds=None) -> list:
    """
    Lista arquivos JSON na pasta de eventos mais recentes que desde_ts.
    desde_ts: string ISO ex '2026-04-11T10:00:00Z' (UTC). None = todos.
    Retorna lista de dicts {id, name, createdTime}.
    """
    if creds is None:
        creds = _get_creds()
    q = f"'{pasta_id}' in parents and mimeType='application/json' and trashed=false"
    if desde_ts:
        # Drive usa RFC 3339; garantir sufixo Z
        ts = desde_ts if desde_ts.endswith("Z") else desde_ts + "Z"
        q += f" and createdTime > '{ts}'"
    todos = []
    page_token = None
    while True:
        params = {
            "q": q, "fields": "nextPageToken,files(id,name,createdTime)",
            "orderBy": "createdTime", "pageSize": "100",
        }
        if page_token:
            params["pageToken"] = page_token
        url = _DRIVE_FILES + "?" + urllib.parse.urlencode(params)
        result = _req(url, creds)
        todos.extend(result.get("files", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return todos


def upload_foto(path_abs: str, nome: str, pasta_id: str, creds=None) -> str:
    """
    Faz upload de arquivo de imagem para o Drive.
    Retorna o drive_file_id do arquivo criado.
    """
    if creds is None:
        creds = _get_creds()
    if not os.path.exists(path_abs):
        raise FileNotFoundError(f"Foto nao encontrada: {path_abs}")
    import mimetypes
    mime = mimetypes.guess_type(path_abs)[0] or "image/jpeg"
    with open(path_abs, "rb") as f:
        conteudo = f.read()
    boundary = _IMG_BOUNDARY + nome[:10].replace(".", "_")
    meta = json.dumps({
        "name": nome, "parents": [pasta_id], "mimeType": mime,
    }).encode("utf-8")
    body  = b"--" + boundary.encode() + b"\r\n"
    body += b"Content-Type: application/json; charset=UTF-8\r\n\r\n"
    body += meta + b"\r\n"
    body += b"--" + boundary.encode() + b"\r\n"
    body += f"Content-Type: {mime}\r\n\r\n".encode()
    body += conteudo + b"\r\n"
    body += b"--" + boundary.encode() + b"--"
    url = _UPLOAD_URL + "?uploadType=multipart"
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": f"multipart/related; boundary={boundary}",
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result.get("id", "")


def baixar_foto(file_id: str, dest_path: str, creds=None) -> bool:
    """Baixa arquivo do Drive para dest_path. Retorna True se OK."""
    if creds is None:
        creds = _get_creds()
    url = f"{_DRIVE_FILES}/{file_id}?alt=media"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {creds.token}"})
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with urllib.request.urlopen(req, timeout=60) as resp:
            with open(dest_path, "wb") as f:
                f.write(resp.read())
        return True
    except Exception as ex:
        logging.warning(f"[DRIVE] baixar_foto {file_id}: {ex}")
        return False


def baixar_batch(file_id: str, creds=None) -> list:
    """Baixa conteudo de um batch e retorna lista de eventos."""
    if creds is None:
        creds = _get_creds()
    url = f"{_DRIVE_FILES}/{file_id}?alt=media"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {creds.token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))
