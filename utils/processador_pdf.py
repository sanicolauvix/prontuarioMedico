# -*- coding: utf-8 -*-
"""
processador_pdf.py
==================
Dois estágios independentes:

  ingerir_pdf(pdf_input, internacao_id, db_path, on_progress, creds)
      → Quebra o PDF em páginas, salva JPEG + PDF de cada página no Drive,
        registra em pdf_paginas com status='pendente'.
        Retorna {"total": N, "ids": [...]}

  classificar_pagina(pagina_id, db_path, creds)
      → Roda Claude Vision (pass 1 classificar + pass 2 extrair) em uma página,
        atualiza pdf_paginas com tipo/grupo/dados_json/status='classificado'.

  gravar_pagina(pagina_id, db_path, creds)
      → Lê dados_json de pdf_paginas e grava nas tabelas corretas
        (exames / internacao_dados_brutos / sinais_internacao / etc).
        Atualiza status='gravado'.

Grupos:
  A (exame)      → exames + exame_resultados + laudos + exame_anexos
  B (internacao) → sinais_internacao / internacao_dados_brutos / procedimentos / remedios
  C (descarta)   → status='descartado', nada gravado
"""

import io, os, base64, json, logging, datetime, re, sqlite3
import pypdfium2 as pdfium

log = logging.getLogger(__name__)

_PRONTUARIO_DRIVE_ID = "1P2VPY833hVdePEz9i_yg2VKQGuJ618re"
_cache_pasta_internacao: dict[int, str] = {}
_cache_pasta_exame:      dict[int, str] = {}


# ── Classificação de tipos ────────────────────────────────────────────────────
_GRUPO_A = {
    "resultado_lab", "ecg", "resultado_exame", "resultado_imagem",
    "mapa", "ecocardiograma", "radiografia", "rx",
}
_GRUPO_B = {
    "prescricao_medica", "prescricao_enfermagem",
    "sinais_vitais", "balanco_hidrico",
    "evolucao_medica", "evolucao_enfermagem",
    "ficha_transporte", "alta", "ficha_admissao",
    "registro_cirurgia", "relatorio_cirurgico",
    "avaliacao_riscos_enfermagem", "avaliacao_riscos",
}
_GRUPO_C = {
    "administrativo", "termo", "checklist_cirurgico",
    "checagem_pre_operatoria", "checklist_seguranca_cirurgica",
    "rastreabilidade_material_esteril", "rastreabilidade_materiais_estereis",
    "solicitacao_internacao", "solicitacao_exame",
    "controle_materiais_hospitalares", "controle_materiais_enfermagem",
    "controle_materiais_hospitalar", "ficha_materiais_hospitalares",
    "cnh", "formulario_avaliacao", "checklist_administrativo",
    "evolucao_servico_social", "evolucao_assistente_social",
}

_PROMPT_CLASSIFICAR = """Página de prontuário hospitalar brasileiro escaneado.

Classifique em um dos tipos abaixo (use exatamente o snake_case):
resultado_lab | ecg | resultado_exame | resultado_imagem | mapa |
prescricao_medica | prescricao_enfermagem | sinais_vitais | balanco_hidrico |
evolucao_medica | evolucao_enfermagem | ficha_transporte | alta | ficha_admissao |
registro_cirurgia | avaliacao_riscos_enfermagem |
administrativo | termo | checklist_cirurgico | checagem_pre_operatoria |
rastreabilidade_material_esteril | solicitacao_internacao | solicitacao_exame |
controle_materiais_hospitalares | cnh

Retorne SOMENTE JSON:
{
  "tipo": "tipo_snake_case",
  "data": "YYYY-MM-DD ou null",
  "relevancia": "alta|media|baixa",
  "resumo": "1 frase"
}"""

_PROMPT_GRUPO_A_LAB = """Resultado de exame laboratorial brasileiro.
Extraia TODOS os parâmetros.
Retorne SOMENTE JSON:
{
  "data": "YYYY-MM-DD ou null",
  "hora": "HH:MM ou null",
  "laboratorio": "nome ou null",
  "medico_solicitante": "nome ou null",
  "painel": "nome do painel (ex: Hemograma, Bioquímica, Eletrólitos)",
  "parametros": [
    {"nome": "...", "valor": "...", "unidade": "...", "referencia": "...", "alterado": true/false}
  ]
}"""

_PROMPT_GRUPO_A_ECG = """ECG de 12 derivações. Extraia todos os dados.
Retorne SOMENTE JSON:
{
  "data": "YYYY-MM-DD ou null",
  "hora": "HH:MM ou null",
  "ritmo": "...",
  "fc": "bpm ou null",
  "pr_ms": "ms ou null",
  "qrs_ms": "ms ou null",
  "qtc_ms": "ms ou null",
  "eixo_graus": "graus ou null",
  "alteracoes": ["lista"],
  "laudo_automatico": "texto ou null",
  "qualidade": "boa|regular|ruim"
}"""

_PROMPT_GRUPO_A_IMAGEM = """Resultado de exame de imagem/funcional brasileiro (USG, eco, doppler, RX, MAPA, etc).
Retorne SOMENTE JSON:
{
  "data": "YYYY-MM-DD ou null",
  "tipo_exame": "nome específico",
  "medico_laudante": "nome ou null",
  "parametros": [
    {"nome": "...", "valor": "...", "unidade": "...", "referencia": "...", "alterado": true/false}
  ],
  "laudo": "texto completo do laudo",
  "conclusao": "conclusão/impressão diagnóstica"
}"""

_PROMPT_GRUPO_B_SINAIS = """Folha de sinais vitais / balanço hídrico hospitalar.
Extraia TODOS os registros horários.
Retorne SOMENTE JSON:
{
  "data": "YYYY-MM-DD ou null",
  "setor": "setor/leito ou null",
  "registros": [
    {"hora": "HH:MM", "pa": "...", "fc": "...", "fr": "...",
     "temp": "...", "spo2": "...", "glasgow": "...", "diurese": "...", "obs": "..."}
  ],
  "balanco": {"entradas_total": "...", "saidas_total": "...", "balanco_final": "..."}
}"""

_PROMPT_GRUPO_B_EVOLUCAO = """Evolução médica ou de enfermagem hospitalar.
Retorne SOMENTE JSON:
{
  "data": "YYYY-MM-DD ou null",
  "hora": "HH:MM ou null",
  "profissional": "nome ou null",
  "tipo": "medica|enfermagem",
  "quadro_clinico": "descrição resumida",
  "sinais_vitais": {"pa": null, "fc": null, "temp": null, "spo2": null, "glasgow": null},
  "dispositivos": ["lista"],
  "intercorrencias": "ou null",
  "observacoes": "..."
}"""

_PROMPT_GRUPO_B_PRESCRICAO = """Prescrição médica hospitalar.
Retorne SOMENTE JSON:
{
  "data": "YYYY-MM-DD ou null",
  "medico": "nome ou null",
  "crm": "ou null",
  "medicamentos": [
    {"nome": "...", "dose": "...", "via": "...", "frequencia": "...", "obs": "..."}
  ],
  "dieta": "ou null",
  "cuidados": ["lista"]
}"""

_PROMPT_GRUPO_B_ALTA = """Documento de alta hospitalar.
Retorne SOMENTE JSON:
{
  "data_alta": "YYYY-MM-DD ou null",
  "diagnostico_saida": "diagnóstico principal na alta",
  "cid_saida": "CID ou null",
  "medico": "nome ou null",
  "medicacoes_alta": ["lista de medicações prescritas na alta"],
  "orientacoes": "orientações ao paciente",
  "retorno": "data/local de retorno ou null"
}"""

_PROMPT_GRUPO_B_PROCEDIMENTO = """Registro cirúrgico / relato de procedimento hospitalar.
Retorne SOMENTE JSON:
{
  "data": "YYYY-MM-DD ou null",
  "nome_procedimento": "...",
  "tipo": "cirurgico|endoscopico|outro",
  "medico": "nome ou null",
  "anestesia": "tipo ou null",
  "cid": "CID ou null",
  "descricao": "descrição do procedimento",
  "resultado": "resultado/achados",
  "intercorrencias": "ou null"
}"""

_PROMPT_GRUPO_B_ADMISSAO = """Ficha de admissão hospitalar ou anamnese de entrada.
Retorne SOMENTE JSON:
{
  "data": "YYYY-MM-DD ou null",
  "hora": "HH:MM ou null",
  "medico": "nome ou null",
  "motivo_internacao": "queixa principal",
  "historia_doenca": "resumo da história clínica",
  "antecedentes": "comorbidades, cirurgias anteriores, alergias",
  "medicamentos_uso": ["lista de medicamentos em uso"],
  "exame_fisico": "achados principais",
  "hipotese_diagnostica": "hipótese diagnóstica de entrada",
  "cid": "CID ou null",
  "setor": "setor/leito de internação ou null"
}"""

_PROMPT_GRUPO_B_TRANSPORTE = """Ficha de transporte / transferência inter ou intrahospitalar.
Retorne SOMENTE JSON:
{
  "data": "YYYY-MM-DD ou null",
  "hora_saida": "HH:MM ou null",
  "hora_chegada": "HH:MM ou null",
  "setor_origem": "setor de origem",
  "setor_destino": "setor de destino",
  "motivo_transferencia": "motivo ou null",
  "sinais_saida": {"pa": null, "fc": null, "spo2": null, "glasgow": null},
  "sinais_chegada": {"pa": null, "fc": null, "spo2": null, "glasgow": null},
  "responsavel": "nome ou null",
  "ocorrencias": "intercorrências durante transporte ou null"
}"""


def _prompt_para_tipo(tipo: str) -> str:
    if tipo == "resultado_lab":            return _PROMPT_GRUPO_A_LAB
    if tipo == "ecg":                      return _PROMPT_GRUPO_A_ECG
    if tipo in ("resultado_exame", "resultado_imagem", "mapa", "ecocardiograma"):
                                           return _PROMPT_GRUPO_A_IMAGEM
    if tipo in ("sinais_vitais", "balanco_hidrico"):
                                           return _PROMPT_GRUPO_B_SINAIS
    if tipo in ("evolucao_medica", "evolucao_enfermagem",
                "prescricao_enfermagem", "avaliacao_riscos_enfermagem",
                "avaliacao_riscos"):       return _PROMPT_GRUPO_B_EVOLUCAO
    if tipo == "prescricao_medica":        return _PROMPT_GRUPO_B_PRESCRICAO
    if tipo == "alta":                     return _PROMPT_GRUPO_B_ALTA
    if tipo in ("registro_cirurgia", "relatorio_cirurgico"):
                                           return _PROMPT_GRUPO_B_PROCEDIMENTO
    if tipo == "ficha_admissao":           return _PROMPT_GRUPO_B_ADMISSAO
    if tipo == "ficha_transporte":         return _PROMPT_GRUPO_B_TRANSPORTE
    return None


def _grupo(tipo: str) -> str:
    t = (tipo or "").lower().strip()
    if t in _GRUPO_A: return "A"
    if t in _GRUPO_B: return "B"
    return "C"


def _safe_json(txt: str) -> dict:
    txt = txt.strip()
    if txt.startswith("```"):
        txt = txt.split("```")[1].lstrip("json").strip()
    try:
        return json.loads(txt)
    except Exception:
        for closing in ['"}]}\n', '"]\n}', '\n}', '}']:
            try:
                return json.loads(txt + closing)
            except Exception:
                pass
        return {"_raw": txt[:500], "_erro_parse": True}


def _render_page(page_obj, scale: float = 2.5) -> str:
    """Renderiza página PDF como JPEG base64."""
    bmp = page_obj.render(scale=scale)
    pil = bmp.to_pil()
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


def _render_page_bytes(page_obj, scale: float = 2.5) -> bytes:
    """Renderiza página PDF como bytes JPEG."""
    bmp = page_obj.render(scale=scale)
    pil = bmp.to_pil()
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def _ask(client, img_b64: str, prompt: str, max_tokens: int = 1200) -> dict:
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64",
                                         "media_type": "image/jpeg", "data": img_b64}},
            {"type": "text", "text": prompt},
        ]}],
        timeout=60,
    )
    return _safe_json(resp.content[0].text)


def _pagina_para_pdf_bytes(doc, idx: int) -> bytes:
    novo = pdfium.PdfDocument.new()
    novo.import_pages(doc, pages=[idx])
    buf = io.BytesIO()
    novo.save(buf)
    novo.close()
    return buf.getvalue()


def _upload_jpeg(jpeg_bytes: bytes, nome: str, pasta_id: str, creds) -> str:
    import urllib.request
    boundary = "pron_jpg_" + re.sub(r"[^a-zA-Z0-9]", "_", nome[:12])
    meta = json.dumps({"name": nome, "parents": [pasta_id],
                       "mimeType": "image/jpeg"}).encode()
    body  = b"--" + boundary.encode() + b"\r\n"
    body += b"Content-Type: application/json; charset=UTF-8\r\n\r\n"
    body += meta + b"\r\n"
    body += b"--" + boundary.encode() + b"\r\n"
    body += b"Content-Type: image/jpeg\r\n\r\n"
    body += jpeg_bytes + b"\r\n"
    body += b"--" + boundary.encode() + b"--"
    url  = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
    hdrs = {"Authorization": f"Bearer {creds.token}",
            "Content-Type": f"multipart/related; boundary={boundary}"}
    req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode()).get("id", "")


def _upload_pdf_pag(pdf_bytes: bytes, nome: str, pasta_id: str, creds) -> str:
    import urllib.request
    boundary = "pron_pdf_" + re.sub(r"[^a-zA-Z0-9]", "_", nome[:12])
    meta = json.dumps({"name": nome, "parents": [pasta_id],
                       "mimeType": "application/pdf"}).encode()
    body  = b"--" + boundary.encode() + b"\r\n"
    body += b"Content-Type: application/json; charset=UTF-8\r\n\r\n"
    body += meta + b"\r\n"
    body += b"--" + boundary.encode() + b"\r\n"
    body += b"Content-Type: application/pdf\r\n\r\n"
    body += pdf_bytes + b"\r\n"
    body += b"--" + boundary.encode() + b"--"
    url  = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
    hdrs = {"Authorization": f"Bearer {creds.token}",
            "Content-Type": f"multipart/related; boundary={boundary}"}
    req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode()).get("id", "")


def _garantir_pasta_internacao(internacao_id: int, creds) -> str:
    if internacao_id in _cache_pasta_internacao:
        return _cache_pasta_internacao[internacao_id]
    from utils.drive_sync import garantir_pasta
    pasta_int = garantir_pasta("internacao", _PRONTUARIO_DRIVE_ID, creds)
    pasta_id  = garantir_pasta(str(internacao_id), pasta_int, creds)
    _cache_pasta_internacao[internacao_id] = pasta_id
    return pasta_id


def _garantir_pasta_exame(exame_id: int, creds) -> str:
    if exame_id in _cache_pasta_exame:
        return _cache_pasta_exame[exame_id]
    from utils.drive_sync import garantir_pasta
    pasta_ex = garantir_pasta("exames_laboratorio", _PRONTUARIO_DRIVE_ID, creds)
    pasta_id = garantir_pasta(str(exame_id), pasta_ex, creds)
    _cache_pasta_exame[exame_id] = pasta_id
    return pasta_id


# ══════════════════════════════════════════════════════════════════════════════
# FASE 1 — SEPARAR: quebra o PDF em páginas e salva localmente
# ══════════════════════════════════════════════════════════════════════════════

def _db_path_default():
    _here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(_here, "..", "dados", "prontuario.db")


def _dir_ingestao(importacao_id: int) -> str:
    _here = os.path.dirname(os.path.abspath(__file__))
    d = os.path.join(_here, "..", "temp", "ingestao", str(importacao_id))
    os.makedirs(d, exist_ok=True)
    return d


def separar_pdf(
    pdf_input,
    internacao_ids: "list[int]",
    db_path: str = None,
    on_progress=None,   # callback(pagina, total, msg)
    importacao_id: int = None,
) -> dict:
    """
    FASE 1 — Local, sem rede.
    - Quebra o PDF em páginas
    - Salva JPEG e PDF de cada página em temp/ingestao/{importacao_id}/
    - Cria/atualiza importacoes_pdf (fase_atual=1)
    - Grava pdf_paginas com status='pendente_local'

    Se importacao_id não for passado, cria um novo registro em importacoes_pdf.
    Retorna {"importacao_id": N, "total": N, "ids": [...]}
    """
    import hashlib

    if db_path is None:
        db_path = _db_path_default()

    if isinstance(pdf_input, (str, os.PathLike)):
        arquivo_local = str(pdf_input)
        nome_pdf = os.path.basename(arquivo_local)
        with open(pdf_input, "rb") as f:
            pdf_bytes = f.read()
    else:
        arquivo_local = ""
        nome_pdf = "prontuario.pdf"
        pdf_bytes = pdf_input

    hash_pdf = hashlib.sha1(pdf_bytes).hexdigest()[:16]
    now      = datetime.datetime.now().isoformat(timespec="seconds")
    doc      = pdfium.PdfDocument(pdf_bytes)
    total    = len(doc)
    slug     = re.sub(r"[^\w]", "_", nome_pdf[:20])

    with sqlite3.connect(db_path) as con:
        if importacao_id is None:
            # verificar se esse PDF já foi importado antes pelo hash
            row = con.execute(
                "SELECT id, fase_atual FROM importacoes_pdf WHERE hash_pdf=?",
                (hash_pdf,)
            ).fetchone()
            if row:
                importacao_id = row[0]
                # se já está em fase >= 1, limpar páginas e reimportar desta fase
                con.execute(
                    "DELETE FROM pdf_paginas WHERE importacao_id=?", (importacao_id,)
                )
            else:
                con.execute("""
                    INSERT INTO importacoes_pdf
                    (arquivo_local, nome_arquivo, hash_pdf, fase_atual, total_paginas,
                     internacao_ids, criado_em, atualizado_em)
                    VALUES (?,?,?,0,?,?,?,?)
                """, (arquivo_local, nome_pdf, hash_pdf, total,
                      json.dumps(internacao_ids), now, now))
                importacao_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]

        pasta = _dir_ingestao(importacao_id)
        ids   = []

        for i in range(total):
            num = i + 1
            if on_progress:
                on_progress(num, total, f"Separando pág {num}/{total}...")
            try:
                jpeg_bytes = _render_page_bytes(doc[i], scale=2.5)
                pdf_pag    = _pagina_para_pdf_bytes(doc, i)

                nome_base  = f"{slug}_p{num:03d}"
                jpeg_local = os.path.join(pasta, nome_base + ".jpg")
                pdf_local  = os.path.join(pasta, nome_base + ".pdf")

                with open(jpeg_local, "wb") as f: f.write(jpeg_bytes)
                with open(pdf_local,  "wb") as f: f.write(pdf_pag)

                # internacao_id: usa o primeiro (será reatribuído na fase 2 se múltiplas)
                iid = internacao_ids[0] if internacao_ids else None

                con.execute("""
                    INSERT INTO pdf_paginas
                    (importacao_id, internacao_id, pdf_origem, pagina_num,
                     jpeg_local, pdf_local, status, criado_em)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (importacao_id, iid, nome_pdf, num,
                      jpeg_local, pdf_local, "pendente_local", now))
                ids.append(con.execute("SELECT last_insert_rowid()").fetchone()[0])

            except Exception as ex:
                log.error("[FASE1] pág %d erro: %s", num, ex, exc_info=True)

        con.execute("""
            UPDATE importacoes_pdf
            SET fase_atual=1, total_paginas=?, internacao_ids=?, atualizado_em=?
            WHERE id=?
        """, (total, json.dumps(internacao_ids), now, importacao_id))

    doc.close()
    log.info("[FASE1] importacao_id=%d total=%d", importacao_id, total)
    return {"importacao_id": importacao_id, "total": total, "ids": ids}


# ══════════════════════════════════════════════════════════════════════════════
# FASE 2 — ENVIAR DRIVE: sobe os arquivos locais para o Google Drive
# ══════════════════════════════════════════════════════════════════════════════

def enviar_drive(
    importacao_id: int,
    db_path: str = None,
    on_progress=None,
    creds=None,
) -> dict:
    """
    FASE 2 — Requer rede.
    - Pega todas as pdf_paginas com status='pendente_local' desta importacao
    - Faz upload JPEG + PDF para Drive em internacao/{id}/
    - Atualiza drive_img_id, drive_pdf_id, status='pendente_drive'
    - Atualiza importacoes_pdf.fase_atual=3

    Retorna {"enviadas": N, "erros": N}
    """
    from utils.drive_sync import _get_creds

    if db_path is None:
        db_path = _db_path_default()
    if creds is None:
        creds = _get_creds()

    now = datetime.datetime.now().isoformat(timespec="seconds")

    with sqlite3.connect(db_path) as con:
        rows = con.execute("""
            SELECT id, internacao_id, jpeg_local, pdf_local, pagina_num, pdf_origem
            FROM pdf_paginas
            WHERE importacao_id=? AND status='pendente_local'
            ORDER BY pagina_num
        """, (importacao_id,)).fetchall()

    total   = len(rows)
    enviadas = 0
    erros    = 0

    for i, (pid, iid, jpeg_local, pdf_local, num, pdf_origem) in enumerate(rows):
        if on_progress:
            on_progress(i + 1, total, f"Enviando pág {num} ao Drive...")
        try:
            pasta_drive  = _garantir_pasta_internacao(iid, creds)
            slug         = re.sub(r"[^\w]", "_", (pdf_origem or "pron")[:20])
            nome_base    = f"{slug}_p{num:03d}"

            with open(jpeg_local, "rb") as f: jpeg_bytes = f.read()
            with open(pdf_local,  "rb") as f: pdf_bytes  = f.read()

            drive_img_id = _upload_jpeg(jpeg_bytes, nome_base + ".jpg", pasta_drive, creds)
            drive_pdf_id = _upload_pdf_pag(pdf_bytes, nome_base + ".pdf", pasta_drive, creds)

            with sqlite3.connect(db_path) as con:
                con.execute("""
                    UPDATE pdf_paginas
                    SET drive_img_id=?, drive_pdf_id=?, status='pendente_drive'
                    WHERE id=?
                """, (drive_img_id, drive_pdf_id, pid))
            enviadas += 1
            log.info("[FASE2] pág id=%d enviada img=%s", pid, drive_img_id[:8])

        except Exception as ex:
            erros += 1
            log.error("[FASE2] pág id=%d erro: %s", pid, ex)

    with sqlite3.connect(db_path) as con:
        if erros == 0:
            con.execute(
                "UPDATE importacoes_pdf SET fase_atual=3, atualizado_em=? WHERE id=?",
                (now, importacao_id)
            )

    return {"enviadas": enviadas, "erros": erros}


# ══════════════════════════════════════════════════════════════════════════════
# CONSULTA DE ESTADO — o que tem pendente para retomar
# ══════════════════════════════════════════════════════════════════════════════

def importacoes_pendentes(db_path: str = None) -> list:
    """
    Retorna lista de importacoes_pdf com fase_atual < 4 (ainda nao concluidas).
    Cada item: {"id", "nome_arquivo", "fase_atual", "total_paginas",
                "pendente_local", "pendente_drive", "classificado", "gravado"}
    """
    if db_path is None:
        db_path = _db_path_default()
    try:
        with sqlite3.connect(db_path) as con:
            rows = con.execute("""
                SELECT i.id, i.nome_arquivo, i.fase_atual, i.total_paginas,
                       i.arquivo_local, i.internacao_ids,
                       COUNT(CASE WHEN p.status='pendente_local'   THEN 1 END),
                       COUNT(CASE WHEN p.status='pendente_drive'   THEN 1 END),
                       COUNT(CASE WHEN p.status='classificado'     THEN 1 END),
                       COUNT(CASE WHEN p.status='gravado'          THEN 1 END),
                       COUNT(CASE WHEN p.status='descartado'       THEN 1 END)
                FROM importacoes_pdf i
                LEFT JOIN pdf_paginas p ON p.importacao_id = i.id
                WHERE i.fase_atual < 4
                GROUP BY i.id
                ORDER BY i.criado_em DESC
            """).fetchall()
        return [
            {
                "id": r[0], "nome_arquivo": r[1], "fase_atual": r[2],
                "total_paginas": r[3], "arquivo_local": r[4],
                "internacao_ids": json.loads(r[5] or "[]"),
                "pendente_local": r[6], "pendente_drive": r[7],
                "classificado": r[8], "gravado": r[9], "descartado": r[10],
            }
            for r in rows
        ]
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# COMPATIBILIDADE — ingerir_pdf chama fase1 + fase2 em sequência
# ══════════════════════════════════════════════════════════════════════════════

def ingerir_pdf(
    pdf_input,
    internacao_id: int,
    db_path: str = None,
    on_progress=None,
    creds=None,
    importacao_id: int = None,
) -> dict:
    """Fase 1 (separar local) + Fase 2 (enviar Drive). Retorna {"total", "ids"}."""
    if db_path is None:
        db_path = _db_path_default()

    def _prog1(p, t, m):
        if on_progress: on_progress(p, t, m)

    r1 = separar_pdf(pdf_input, [internacao_id], db_path, _prog1, importacao_id)
    iid = r1["importacao_id"]

    def _prog2(p, t, m):
        if on_progress: on_progress(p, t, m)

    enviar_drive(iid, db_path, _prog2, creds)

    # retorna os ids das páginas criadas (compatibilidade com código existente)
    with sqlite3.connect(db_path) as con:
        ids = [r[0] for r in con.execute(
            "SELECT id FROM pdf_paginas WHERE importacao_id=? ORDER BY pagina_num",
            (iid,)
        ).fetchall()]

    return {"total": r1["total"], "ids": ids}


# ══════════════════════════════════════════════════════════════════════════════
# ESTÁGIO 2 — CLASSIFICAÇÃO (on-demand por página)
# ══════════════════════════════════════════════════════════════════════════════

def classificar_pagina(
    pagina_id: int,
    db_path: str = None,
    creds=None,
) -> dict:
    """
    Baixa a imagem do Drive, roda Claude Vision (pass 1 + pass 2),
    atualiza pdf_paginas com tipo/grupo/dados_json/status='classificado'.
    Retorna o dict com os dados extraídos.
    """
    from utils.claudia_engine import get_client
    from utils.drive_sync import _get_creds, baixar_foto

    if db_path is None:
        _here = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(_here, "..", "dados", "prontuario.db")

    if creds is None:
        creds = _get_creds()

    with sqlite3.connect(db_path) as con:
        row = con.execute(
            "SELECT drive_img_id, drive_pdf_id, jpeg_local FROM pdf_paginas WHERE id=?",
            (pagina_id,)
        ).fetchone()

    if not row:
        raise ValueError(f"pdf_paginas id={pagina_id} não encontrado")

    drive_img_id, _, jpeg_local = row

    # preferir JPEG local (mais rápido); fallback: baixar do Drive
    if jpeg_local and os.path.exists(jpeg_local):
        with open(jpeg_local, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
    elif drive_img_id:
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        tmp.close()
        ok = baixar_foto(drive_img_id, tmp.name, creds)
        if not ok:
            raise IOError(f"Falha ao baixar imagem Drive id={drive_img_id}")
        with open(tmp.name, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        os.unlink(tmp.name)
    else:
        raise ValueError(f"Página id={pagina_id} sem imagem local nem no Drive")

    client = get_client()

    # pass 1 — classificar
    info  = _ask(client, img_b64, _PROMPT_CLASSIFICAR, max_tokens=250)
    tipo  = (info.get("tipo") or "administrativo").lower().strip()
    data  = info.get("data") or ""
    grupo = _grupo(tipo)

    # pass 2 — extrair dados
    prompt2 = _prompt_para_tipo(tipo)
    dados   = {}
    if prompt2:
        dados = _ask(client, img_b64, prompt2, max_tokens=1800)
        if not dados.get("data") and data:
            dados["data"] = data

    dados_json = json.dumps(dados, ensure_ascii=False)

    with sqlite3.connect(db_path) as con:
        con.execute("""
            UPDATE pdf_paginas
            SET tipo=?, grupo=?, dados_json=?, status='classificado'
            WHERE id=?
        """, (tipo, grupo, dados_json, pagina_id))

    log.info("[CLASS] pág id=%d tipo=%s grupo=%s", pagina_id, tipo, grupo)
    return {"tipo": tipo, "grupo": grupo, "dados": dados, "data": data}


# ══════════════════════════════════════════════════════════════════════════════
# ESTÁGIO 3 — GRAVAÇÃO NAS TABELAS FINAIS
# ══════════════════════════════════════════════════════════════════════════════

def gravar_pagina(
    pagina_id: int,
    db_path: str = None,
    creds=None,
) -> dict:
    """
    Lê dados_json de pdf_paginas e grava nas tabelas corretas.
    Grupo C: apenas marca status='descartado'.
    Retorna {"grupo": "A/B/C", "id_gravado": int_ou_None}
    """
    from utils.drive_sync import _get_creds

    if db_path is None:
        _here = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(_here, "..", "dados", "prontuario.db")

    if creds is None:
        creds = _get_creds()

    con = sqlite3.connect(db_path)
    row = con.execute(
        "SELECT internacao_id, tipo, grupo, dados_json, drive_pdf_id, pdf_origem, pagina_num "
        "FROM pdf_paginas WHERE id=?", (pagina_id,)
    ).fetchone()
    con.close()

    if not row:
        raise ValueError(f"pdf_paginas id={pagina_id} não encontrado")

    internacao_id, tipo, grupo, dados_json, drive_pdf_id, pdf_origem, pagina_num = row
    dados = json.loads(dados_json or "{}")
    nome_arq = f"{pdf_origem}_p{pagina_num:03d}_{tipo}.pdf"

    # limpar registros anteriores desta página para permitir regravação limpa
    with sqlite3.connect(db_path) as _c:
        prev = _c.execute(
            "SELECT dado_bruto_id, exame_id FROM pdf_paginas WHERE id=?", (pagina_id,)
        ).fetchone()
        if prev:
            if prev[0]:
                _c.execute("DELETE FROM internacao_dados_brutos WHERE id=?", (prev[0],))
            if prev[1]:
                _c.execute("DELETE FROM exames WHERE id=?", (prev[1],))
        # apaga por pdf_pagina_id E por internacao_id+tipo (cobre registros sem FK)
        _c.execute("DELETE FROM registros_clinicos WHERE pdf_pagina_id=?", (pagina_id,))
        _c.execute(
            "DELETE FROM registros_clinicos WHERE internacao_id=? AND tipo=?",
            (internacao_id, tipo)
        )
        # também limpa internacao_dados_brutos órfãos do mesmo tipo
        _c.execute(
            "DELETE FROM internacao_dados_brutos WHERE internacao_id=? AND categoria=?",
            (internacao_id, tipo)
        )
        _c.execute("UPDATE pdf_paginas SET dado_bruto_id=NULL, exame_id=NULL WHERE id=?",
                   (pagina_id,))

    if grupo == "C":
        con = sqlite3.connect(db_path)
        con.execute("UPDATE pdf_paginas SET status='descartado' WHERE id=?", (pagina_id,))
        con.commit(); con.close()
        return {"grupo": "C", "id_gravado": None}

    if grupo == "A":
        eid = _gravar_grupo_a(dados, tipo, internacao_id, drive_pdf_id,
                              nome_arq, db_path, creds)
        con = sqlite3.connect(db_path)
        con.execute("UPDATE pdf_paginas SET status='gravado', exame_id=? WHERE id=?",
                    (eid, pagina_id))
        con.commit(); con.close()
        return {"grupo": "A", "id_gravado": eid}

    if grupo == "B":
        bid = _gravar_grupo_b(dados, tipo, internacao_id, drive_pdf_id,
                              nome_arq, db_path, creds, pagina_id=pagina_id)
        con = sqlite3.connect(db_path)
        con.execute("UPDATE pdf_paginas SET status='gravado', dado_bruto_id=? WHERE id=?",
                    (bid, pagina_id))
        con.commit(); con.close()
        return {"grupo": "B", "id_gravado": bid}

    return {"grupo": "?", "id_gravado": None}


# ══════════════════════════════════════════════════════════════════════════════
# GRAVADORES POR GRUPO (internos)
# ══════════════════════════════════════════════════════════════════════════════

def _gravar_grupo_a(dados: dict, tipo: str, internacao_id: int,
                    drive_pdf_id: str, nome_arquivo: str,
                    db_path: str, creds) -> int:
    now = datetime.datetime.now().isoformat(timespec="seconds")
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    tipo_exame  = dados.get("painel") or dados.get("tipo_exame") or tipo
    data_exame  = dados.get("data") or dados.get("data_exame") or ""
    laboratorio = dados.get("laboratorio") or ""
    medico_s    = dados.get("medico_solicitante") or dados.get("medico_laudante") or ""
    resultado_t = dados.get("laudo") or dados.get("laudo_automatico") or ""
    conclusao   = dados.get("conclusao") or ""
    if conclusao:
        resultado_t = (resultado_t + "\n" + conclusao).strip()

    cur.execute("""
        INSERT INTO exames (tipo, tipo_exame, data_exame, laboratorio,
                            medico_solicit, resultado_texto, importado_em,
                            status, internacao_id)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (tipo, tipo_exame, data_exame, laboratorio,
          medico_s, resultado_t, now, "resultado", internacao_id))
    exame_id = cur.lastrowid

    if resultado_t and tipo in ("resultado_imagem", "resultado_exame",
                                "mapa", "ecocardiograma", "ecg"):
        cur.execute("""
            INSERT INTO laudos (exame_id, texto_completo, resumo, conclusao)
            VALUES (?,?,?,?)
        """, (exame_id, resultado_t, "", dados.get("conclusao") or ""))

    parametros = dados.get("parametros", [])
    if tipo == "ecg":
        for nome, (val, uni) in {
            "FC":   (dados.get("fc"),        "bpm"),
            "PR":   (dados.get("pr_ms"),     "ms"),
            "QRS":  (dados.get("qrs_ms"),    "ms"),
            "QTc":  (dados.get("qtc_ms"),    "ms"),
            "Eixo": (dados.get("eixo_graus"),"°"),
            "Ritmo":(dados.get("ritmo"),     ""),
        }.items():
            if val:
                cur.execute("""
                    INSERT INTO exame_resultados
                    (exame_id, parametro, valor, unidade, nivel_interpretacao)
                    VALUES (?,?,?,?,?)
                """, (exame_id, nome, str(val), uni, ""))
        for alt in (dados.get("alteracoes") or []):
            cur.execute("""
                INSERT INTO exame_resultados
                (exame_id, parametro, valor, nivel_interpretacao)
                VALUES (?,?,?,?)
            """, (exame_id, "Alteracao", str(alt), "alterado"))
    else:
        for p in parametros:
            nivel = "alterado" if p.get("alterado") else "normal"
            cur.execute("""
                INSERT INTO exame_resultados
                (exame_id, parametro, valor, unidade, referencia, nivel_interpretacao)
                VALUES (?,?,?,?,?,?)
            """, (exame_id, p.get("nome",""), str(p.get("valor","")),
                  p.get("unidade","") or "", p.get("referencia","") or "", nivel))

    cur.execute("""
        INSERT INTO exame_anexos (exame_id, drive_file_id, nome_arquivo, ordem, criado_em, pendente_sync)
        VALUES (?,?,?,?,?,?)
    """, (exame_id, drive_pdf_id or "", nome_arquivo, 1, now, 0 if drive_pdf_id else 1))

    con.commit()
    con.close()
    return exame_id


def _gravar_grupo_b(dados: dict, tipo: str, internacao_id: int,
                    drive_pdf_id: str, nome_arquivo: str,
                    db_path: str, creds, pagina_id: int = None) -> int:
    """Retorna o id do registro principal gravado (internacao_dados_brutos ou outro)."""
    now = datetime.datetime.now().isoformat(timespec="seconds")
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    bid = None

    if tipo in ("sinais_vitais", "balanco_hidrico"):
        for reg in (dados.get("registros") or []):
            for sinal, campo in [("PA","pa"),("FC","fc"),("FR","fr"),
                                  ("Temp","temp"),("SpO2","spo2"),
                                  ("Glasgow","glasgow"),("Diurese","diurese")]:
                val = reg.get(campo)
                if val:
                    momento = f"{dados.get('data','')} {reg.get('hora','')}".strip()
                    cur.execute("""
                        INSERT INTO sinais_internacao
                        (internacao_id, sinal, momento, valor, fonte, criado_em)
                        VALUES (?,?,?,?,?,?)
                    """, (internacao_id, sinal, momento, str(val), "folha_sinais", now))
        bal = dados.get("balanco") or {}
        if bal.get("balanco_final"):
            cur.execute("""
                INSERT INTO sinais_internacao
                (internacao_id, sinal, momento, valor, fonte, criado_em)
                VALUES (?,?,?,?,?,?)
            """, (internacao_id, "Balanco_Hidrico",
                  dados.get("data",""), bal["balanco_final"], "folha_sinais", now))
        # registrar também como dado_bruto para rastreabilidade
        cur.execute("""
            INSERT INTO internacao_dados_brutos
            (internacao_id, categoria, conteudo, fonte, criado_em)
            VALUES (?,?,?,?,?)
        """, (internacao_id, tipo, json.dumps(dados, ensure_ascii=False), "processador_pdf", now))
        bid = cur.lastrowid

    elif tipo == "ficha_admissao":
        cur.execute("""
            INSERT INTO internacao_dados_brutos
            (internacao_id, categoria, conteudo, fonte, criado_em)
            VALUES (?,?,?,?,?)
        """, (internacao_id, tipo, json.dumps(dados, ensure_ascii=False), "processador_pdf", now))
        bid = cur.lastrowid
        motivo = dados.get("motivo_internacao") or dados.get("historia_doenca") or ""
        cid    = dados.get("cid") or ""
        medico = dados.get("medico") or ""
        if motivo:
            cur.execute("UPDATE internacoes SET motivo=? WHERE id=? AND (motivo IS NULL OR motivo='')",
                        (motivo, internacao_id))
        if cid:
            cur.execute("UPDATE internacoes SET cid_entrada=? WHERE id=? AND (cid_entrada IS NULL OR cid_entrada='')",
                        (cid, internacao_id))
        if medico:
            cur.execute("UPDATE internacoes SET medico_responsavel=? WHERE id=? AND (medico_responsavel IS NULL OR medico_responsavel='')",
                        (medico, internacao_id))
        # gravar em registros_clinicos para aparecer na aba Evolução
        cur.execute("""
            INSERT INTO registros_clinicos
            (internacao_id, tipo, data_registro, hora_registro, profissional,
             quadro_clinico, observacoes, dados_extras, pdf_pagina_id, criado_em)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            internacao_id, tipo,
            dados.get("data") or "",
            dados.get("hora") or "",
            medico,
            dados.get("historia_doenca") or dados.get("motivo_internacao") or "",
            dados.get("exame_fisico") or "",
            json.dumps({k: v for k, v in dados.items()
                        if k not in ("data","hora","medico","historia_doenca",
                                     "motivo_internacao","exame_fisico","cid")
                        and v}, ensure_ascii=False),
            pagina_id,
            now,
        ))

    elif tipo == "ficha_transporte":
        cur.execute("""
            INSERT INTO internacao_dados_brutos
            (internacao_id, categoria, conteudo, fonte, criado_em)
            VALUES (?,?,?,?,?)
        """, (internacao_id, tipo, json.dumps(dados, ensure_ascii=False), "processador_pdf", now))
        bid = cur.lastrowid
        data = dados.get("data","")
        for sinal, val in (dados.get("sinais_saida") or {}).items():
            if val:
                cur.execute("""
                    INSERT INTO sinais_internacao
                    (internacao_id, sinal, momento, valor, fonte, criado_em)
                    VALUES (?,?,?,?,?,?)
                """, (internacao_id, sinal.upper(),
                      f"transferencia_saida_{dados.get('setor_origem','ps')}",
                      str(val), "ficha_transporte", now))
        for sinal, val in (dados.get("sinais_chegada") or {}).items():
            if val:
                cur.execute("""
                    INSERT INTO sinais_internacao
                    (internacao_id, sinal, momento, valor, fonte, criado_em)
                    VALUES (?,?,?,?,?,?)
                """, (internacao_id, sinal.upper(),
                      f"transferencia_chegada_{dados.get('setor_destino','uti')}",
                      str(val), "ficha_transporte", now))

    elif tipo in ("evolucao_medica", "evolucao_enfermagem",
                  "prescricao_enfermagem", "avaliacao_riscos_enfermagem", "avaliacao_riscos"):
        cur.execute("""
            INSERT INTO internacao_dados_brutos
            (internacao_id, categoria, conteudo, fonte, criado_em)
            VALUES (?,?,?,?,?)
        """, (internacao_id, tipo, json.dumps(dados, ensure_ascii=False), "processador_pdf", now))
        bid = cur.lastrowid
        # gravar também em registros_clinicos (estruturado)
        sv = dados.get("sinais_vitais") or {}
        disp = dados.get("dispositivos") or []
        cur.execute("""
            INSERT INTO registros_clinicos
            (internacao_id, tipo, data_registro, hora_registro, profissional,
             quadro_clinico, observacoes, intercorrencias, dispositivos,
             sinais_vitais, dados_extras, pdf_pagina_id, criado_em)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            internacao_id, tipo,
            dados.get("data") or "",
            dados.get("hora") or "",
            dados.get("profissional") or dados.get("medico") or "",
            dados.get("quadro_clinico") or dados.get("descricao") or "",
            dados.get("observacoes") or "",
            dados.get("intercorrencias") or "",
            json.dumps(disp, ensure_ascii=False) if isinstance(disp, list) else str(disp),
            json.dumps({k: v for k, v in sv.items() if v}, ensure_ascii=False),
            json.dumps({k: v for k, v in dados.items()
                        if k not in ("sinais_vitais","dispositivos","quadro_clinico",
                                     "observacoes","intercorrencias","profissional",
                                     "medico","data","hora","tipo")
                        and v}, ensure_ascii=False),
            pagina_id,
            now,
        ))
        for sinal, val in sv.items():
            if val:
                cur.execute("""
                    INSERT INTO sinais_internacao
                    (internacao_id, sinal, momento, valor, fonte, criado_em)
                    VALUES (?,?,?,?,?,?)
                """, (internacao_id, sinal.upper(), dados.get("data",""), str(val), tipo, now))

    elif tipo == "prescricao_medica":
        cur.execute("""
            INSERT INTO internacao_dados_brutos
            (internacao_id, categoria, conteudo, fonte, criado_em)
            VALUES (?,?,?,?,?)
        """, (internacao_id, "prescricao_medica",
              json.dumps(dados, ensure_ascii=False), "processador_pdf", now))
        bid = cur.lastrowid
        for med in (dados.get("medicamentos") or []):
            cur.execute("""
                INSERT INTO remedios
                (nome, dosagem, frequencia, data_inicio, tipo, prescrito, internacao_id, criado_em)
                VALUES (?,?,?,?,?,?,?,?)
            """, (med.get("nome",""), med.get("dose",""), med.get("frequencia",""),
                  dados.get("data",""), "prescrito_internacao", 1, internacao_id, now))

    elif tipo == "alta":
        diag     = dados.get("diagnostico_saida") or ""
        cid      = dados.get("cid_saida") or ""
        dt_alta  = dados.get("data_alta") or ""
        if dt_alta:
            cur.execute("UPDATE internacoes SET data_saida=? WHERE id=? AND (data_saida IS NULL OR data_saida='')",
                        (dt_alta, internacao_id))
        if diag:
            cur.execute("UPDATE internacoes SET diagnostico_saida=? WHERE id=? AND diagnostico_saida IS NULL",
                        (diag, internacao_id))
        if cid:
            cur.execute("UPDATE internacoes SET cid_saida=? WHERE id=? AND cid_saida IS NULL",
                        (cid, internacao_id))
        cur.execute("""
            INSERT INTO internacao_dados_brutos
            (internacao_id, categoria, conteudo, fonte, criado_em)
            VALUES (?,?,?,?,?)
        """, (internacao_id, "alta",
              json.dumps(dados, ensure_ascii=False), "processador_pdf", now))
        bid = cur.lastrowid

    elif tipo in ("registro_cirurgia", "relatorio_cirurgico"):
        cur.execute("""
            INSERT INTO procedimentos
            (internacao_id, nome, tipo, data, cid, resultado, observacoes, criado_em)
            VALUES (?,?,?,?,?,?,?,?)
        """, (internacao_id, dados.get("nome_procedimento",""),
              dados.get("tipo","cirurgico"), dados.get("data",""),
              dados.get("cid",""), dados.get("resultado",""),
              dados.get("descricao",""), now))
        bid = cur.lastrowid
        # também registrar como dado_bruto
        cur.execute("""
            INSERT INTO internacao_dados_brutos
            (internacao_id, categoria, conteudo, fonte, criado_em)
            VALUES (?,?,?,?,?)
        """, (internacao_id, tipo, json.dumps(dados, ensure_ascii=False), "processador_pdf", now))

    else:
        cur.execute("""
            INSERT INTO internacao_dados_brutos
            (internacao_id, categoria, conteudo, fonte, criado_em)
            VALUES (?,?,?,?,?)
        """, (internacao_id, tipo, json.dumps(dados, ensure_ascii=False), "processador_pdf", now))
        bid = cur.lastrowid

    con.commit()
    con.close()
    return bid or 0


# ══════════════════════════════════════════════════════════════════════════════
# COMPATIBILIDADE — processar_pdf (chama ingerir + classificar + gravar)
# ══════════════════════════════════════════════════════════════════════════════

def processar_pdf(
    pdf_input,
    internacao_id: int,
    db_path: str = None,
    on_progress=None,
    creds=None,
) -> dict:
    """
    Pipeline completo: ingerir → classificar → gravar cada página.
    Mantido para compatibilidade com tela_internacoes._oferecer_fase2().
    """
    from utils.drive_sync import _get_creds
    if creds is None:
        creds = _get_creds()
    if db_path is None:
        _here = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(_here, "..", "dados", "prontuario.db")

    # Estágio 1 — ingestão
    ing = ingerir_pdf(pdf_input, internacao_id, db_path,
                      on_progress=lambda p, t, m: on_progress(p, t, m, "?") if on_progress else None,
                      creds=creds)
    ids   = ing["ids"]
    total = ing["total"]

    resultado = {"total": total, "grupo_a": [], "grupo_b": 0, "grupo_c": 0, "erros": []}

    # Estágios 2 + 3 — classificar e gravar cada página
    for i, pid in enumerate(ids):
        num = i + 1
        try:
            info = classificar_pagina(pid, db_path, creds)
            tipo  = info["tipo"]
            grupo = info["grupo"]
            if on_progress:
                icone = {"A": "🔬", "B": "📋", "C": "🗑"}.get(grupo, "")
                on_progress(num, total, tipo, grupo)

            r = gravar_pagina(pid, db_path, creds)
            if grupo == "A":
                resultado["grupo_a"].append(r["id_gravado"])
            elif grupo == "B":
                resultado["grupo_b"] += 1
            else:
                resultado["grupo_c"] += 1
        except Exception as ex:
            import traceback
            tb = traceback.format_exc()
            log.error("[PROC] pág id=%d erro: %s\n%s", pid, ex, tb)
            resultado["erros"].append({"pagina": num, "erro": str(ex), "tb": tb})

    return resultado
