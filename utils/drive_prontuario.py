# -*- coding: utf-8 -*-
# Prontuario | utils/drive_prontuario.py
# Funcoes Drive especificas do Prontuario -- NAO gerenciado pelo sync_shared.
"""
Funcoes de upload para pastas especificas do Prontuario no Drive.
Estrutura: Eco_Koios/Prontuario/<subpasta>/
"""

import logging
log = logging.getLogger(__name__)


def upload_receita(path_abs: str, consulta_id: int, creds=None) -> tuple:
    """
    Faz upload de receita para Eco_Koios/Prontuario/receitas/.
    Nome do arquivo: {consulta_id}_{seq:02d}.ext (seq auto por consulta).
    Retorna (drive_file_id, nome_arquivo).
    """
    from utils.drive_sync import garantir_pasta, upload_foto, _get_creds, _DRIVE_FILES
    import urllib.parse

    if creds is None:
        creds = _get_creds()

    id_koios    = garantir_pasta("Eco_Koios",   None,      creds)
    id_pront    = garantir_pasta("Prontuario",  id_koios,  creds)
    id_receitas = garantir_pasta("receitas",    id_pront,  creds)

    import os
    ext  = path_abs.rsplit(".", 1)[-1].lower() if "." in path_abs else "jpg"
    q    = (f"'{id_receitas}' in parents and trashed=false and "
            f"name contains '{consulta_id}_'")
    import urllib.request, json
    url  = _DRIVE_FILES + "?" + urllib.parse.urlencode(
        {"q": q, "fields": "files(name)", "spaces": "drive"})
    import urllib.request as _ur
    req  = _ur.Request(url, headers={"Authorization": f"Bearer {creds.token}",
                                     "Content-Type": "application/json"})
    with _ur.urlopen(req, timeout=10) as resp:
        res = json.loads(resp.read().decode())
    seq  = len(res.get("files", [])) + 1
    nome = f"{consulta_id}_{seq:02d}.{ext}"

    file_id = upload_foto(path_abs, nome, id_receitas, creds)
    log.info("[DRIVE_PRONT] upload_receita OK: %s -> %s", nome, file_id)
    return file_id, nome


def upload_nota_fiscal(path_abs: str, mov_id: int = 0, creds=None) -> tuple:
    """
    Faz upload de nota fiscal para Eco_Koios/Prontuario/compras/{mov_id}/.
    Retorna (drive_file_id, nome_arquivo).
    """
    import os
    from utils.drive_sync import garantir_pasta, upload_foto, _get_creds

    if creds is None:
        creds = _get_creds()

    id_koios  = garantir_pasta("Eco_Koios",          None,       creds)
    id_pront  = garantir_pasta("Prontuario",          id_koios,  creds)
    id_compras = garantir_pasta("compras",            id_pront,  creds)
    id_pasta  = garantir_pasta(str(mov_id) if mov_id else "avulso", id_compras, creds)
    nome_arq  = os.path.basename(path_abs)
    file_id   = upload_foto(path_abs, nome_arq, id_pasta, creds)
    log.info("[DRIVE_PRONT] upload_nota_fiscal OK: %s -> %s", nome_arq, file_id)
    return file_id, nome_arq


def upload_foto_medico(path_abs: str, creds=None) -> str:
    """
    Faz upload de foto de medico para Eco_Koios/Prontuario/fotos_medicos/.
    Retorna drive_file_id.
    """
    import os
    from utils.drive_sync import garantir_pasta, upload_foto, _get_creds

    if creds is None:
        creds = _get_creds()

    id_koios = garantir_pasta("Eco_Koios",     None,      creds)
    id_pront = garantir_pasta("Prontuario",    id_koios,  creds)
    id_pasta = garantir_pasta("fotos_medicos", id_pront,  creds)
    nome_arq = os.path.basename(path_abs)
    file_id  = upload_foto(path_abs, nome_arq, id_pasta, creds)
    log.info("[DRIVE_PRONT] upload_foto_medico OK: %s -> %s", nome_arq, file_id)
    return file_id
