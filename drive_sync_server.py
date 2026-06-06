# -*- coding: utf-8 -*-
# Prontuario | drive_sync_server.py
# Roda no Hetzner como servico separado.
# Baixa prontuario.db do Drive a cada INTERVALO_MIN minutos.
# Usa as mesmas credenciais do app (mycreds.json).

import json
import logging
import os
import shutil
import sys
import time
import urllib.request
import urllib.parse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "logs", "drive_sync.log"),
            encoding="utf-8",
        ),
    ],
)
log = logging.getLogger("drive_sync_server")

_HERE        = os.path.dirname(os.path.abspath(__file__))
_CREDS_PATH  = os.path.join(_HERE, "mycreds.json")
_DB_PATH     = os.path.join(_HERE, "dados", "prontuario.db")
_DB_TMP      = os.path.join(_HERE, "dados", "_sync_tmp.db")

INTERVALO_MIN   = 5     # baixar do Drive a cada 5 minutos
PASTA_KOIOS     = "Eco_Koios"
PASTA_PRONTUARIO = "Prontuario"
PASTA_DB        = "prontuario_db"
NOME_DB         = "app.db"


def _obter_token() -> str:
    """Le e renova o token do mycreds.json."""
    if not os.path.exists(_CREDS_PATH):
        raise FileNotFoundError(f"mycreds.json nao encontrado em {_CREDS_PATH}")

    with open(_CREDS_PATH, "r", encoding="utf-8") as f:
        creds = json.load(f)

    token     = creds.get("token") or creds.get("access_token", "")
    exp       = creds.get("token_expiry") or creds.get("expiry", "")
    client_id = creds.get("client_id", "")
    client_secret = creds.get("client_secret", "")
    refresh_token = creds.get("refresh_token", "")

    # Renovar se expirado
    if refresh_token and client_id and client_secret:
        try:
            from datetime import datetime, timezone
            if exp:
                exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
                agora  = datetime.now(timezone.utc)
                if (exp_dt - agora).total_seconds() < 300:
                    token = _renovar_token(client_id, client_secret, refresh_token, creds)
        except Exception as ex:
            log.warning("Verificacao de expiry: %s", ex)

    return token


def _renovar_token(client_id, client_secret, refresh_token, creds_atual) -> str:
    """Renova o access token via refresh_token e salva no mycreds.json."""
    dados = urllib.parse.urlencode({
        "client_id":     client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type":    "refresh_token",
    }).encode()
    import urllib.parse
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=dados,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        resp = json.loads(r.read())

    novo_token = resp.get("access_token", "")
    if novo_token:
        creds_atual["token"]        = novo_token
        creds_atual["access_token"] = novo_token
        from datetime import datetime, timezone, timedelta
        exp = datetime.now(timezone.utc) + timedelta(seconds=resp.get("expires_in", 3600))
        creds_atual["token_expiry"] = exp.isoformat()
        creds_atual["expiry"]       = exp.isoformat()
        with open(_CREDS_PATH, "w", encoding="utf-8") as f:
            json.dump(creds_atual, f, indent=2)
        log.info("Token renovado com sucesso")

    return novo_token


def _drive_get(token: str, url: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def _encontrar_pasta(token: str, nome: str, pai_id: str = None) -> str | None:
    q = f"name='{nome}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if pai_id:
        q += f" and '{pai_id}' in parents"
    url = (
        "https://www.googleapis.com/drive/v3/files"
        f"?q={urllib.parse.quote(q)}&fields=files(id,name)&pageSize=1"
    )
    import urllib.parse
    data = _drive_get(token, url)
    files = data.get("files", [])
    return files[0]["id"] if files else None


def _encontrar_arquivo(token: str, nome: str, pasta_id: str) -> str | None:
    import urllib.parse
    q = f"name='{nome}' and '{pasta_id}' in parents and trashed=false"
    url = (
        "https://www.googleapis.com/drive/v3/files"
        f"?q={urllib.parse.quote(q)}&fields=files(id,name,md5Checksum)&pageSize=1"
    )
    data = _drive_get(token, url)
    files = data.get("files", [])
    return files[0] if files else None


def _baixar_arquivo(token: str, file_id: str, destino: str) -> bool:
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            with open(destino, "wb") as f:
                shutil.copyfileobj(r, f)
        return True
    except Exception as ex:
        log.error("Erro ao baixar arquivo: %s", ex)
        return False


def sincronizar() -> bool:
    """Baixa prontuario.db do Drive se houver versao mais nova. Retorna True se atualizou."""
    import urllib.parse
    try:
        token = _obter_token()

        # Navegar: Eco_Koios -> Prontuario -> prontuario_db -> app.db
        id_koios = _encontrar_pasta(token, PASTA_KOIOS)
        if not id_koios:
            log.warning("Pasta '%s' nao encontrada no Drive", PASTA_KOIOS)
            return False

        id_prontuario = _encontrar_pasta(token, PASTA_PRONTUARIO, id_koios)
        if not id_prontuario:
            log.warning("Pasta '%s' nao encontrada", PASTA_PRONTUARIO)
            return False

        id_db_pasta = _encontrar_pasta(token, PASTA_DB, id_prontuario)
        if not id_db_pasta:
            log.warning("Pasta '%s' nao encontrada", PASTA_DB)
            return False

        arquivo = _encontrar_arquivo(token, NOME_DB, id_db_pasta)
        if not arquivo:
            log.warning("Arquivo '%s' nao encontrado no Drive", NOME_DB)
            return False

        file_id  = arquivo["id"]
        md5_drive = arquivo.get("md5Checksum", "")

        # Comparar MD5 com banco local para evitar download desnecessario
        if os.path.exists(_DB_PATH) and md5_drive:
            import hashlib
            h = hashlib.md5()
            with open(_DB_PATH, "rb") as f:
                for bloco in iter(lambda: f.read(65536), b""):
                    h.update(bloco)
            if h.hexdigest() == md5_drive:
                log.debug("Banco ja esta atualizado (MD5 igual)")
                return False

        # Baixar para arquivo temporario e substituir atomicamente
        log.info("Atualizacao detectada — baixando banco do Drive...")
        ok = _baixar_arquivo(token, file_id, _DB_TMP)
        if not ok:
            return False

        os.replace(_DB_TMP, _DB_PATH)
        log.info("Banco atualizado com sucesso")
        return True

    except Exception as ex:
        log.error("Erro no sync: %s", ex)
        return False


def main():
    log.info("Drive Sync Server iniciado — intervalo: %d minutos", INTERVALO_MIN)
    os.makedirs(os.path.join(_HERE, "dados"), exist_ok=True)
    os.makedirs(os.path.join(_HERE, "logs"), exist_ok=True)

    # Sync imediato na inicializacao
    sincronizar()

    while True:
        time.sleep(INTERVALO_MIN * 60)
        sincronizar()


if __name__ == "__main__":
    main()
