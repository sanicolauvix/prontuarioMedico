# -*- coding: utf-8 -*-
# Prontuario | extratores/extrator_internacao.py
"""
Extrai dados estruturados de prontuarios hospitalares escaneados via Claude Vision.
Retorna dict com campos de internacao + lista de procedimentos identificados.
"""
import base64
import json
import logging
import os

log = logging.getLogger(__name__)

_MODELO = "claude-sonnet-4-6"
_PAGINAS_MAX = 10   # primeiras paginas: boletim de internacao + evolucoes iniciais

_SYSTEM = (
    "Voce e um extrator de documentos hospitalares brasileiros. "
    "Analise prontuarios escaneados e retorne apenas JSON valido, sem texto adicional."
)

_PROMPT = """
Analise estas paginas de um prontuario hospitalar brasileiro (PDF escaneado).
Retorne SOMENTE JSON valido, sem texto adicional, sem code fences, sem explicacoes.

Procure especialmente pelo "Boletim de Internacao" ou "Ficha de Admissao":
e' o formulario que tem nome do paciente, data de entrada, medico responsavel,
leito, CID e convenio. Esse documento tem os dados mais confiaveis.

Tambem analise evolucoes medicas (texto livre assinado por medicos) para identificar:
- Diagnostico final (pode diferir do CID de entrada)
- Procedimentos invasivos realizados (cirurgias, cateteres, cateterismos, etc.)

Ignore: contratos, termos de consentimento, prescricoes de enfermagem,
anotacoes de rotina de UTI, paginas em branco.

Retorne exatamente neste formato JSON:
{
  "hospital": "nome do hospital",
  "data_entrada": "YYYY-MM-DD",
  "data_saida": "YYYY-MM-DD ou null",
  "tipo": "eletiva ou urgencia ou emergencia",
  "leito": "numero/nome do leito ou null",
  "unidade": "nome da unidade ou null",
  "convenio": "nome do convenio ou null",
  "medico_nome": "nome completo do medico responsavel",
  "medico_crm": "numero do CRM ou null",
  "especialidade": "especialidade medica ou null",
  "cid_entrada": "codigo CID (ex: R074) ou null",
  "cid_entrada_desc": "descricao do CID ou null",
  "motivo": "motivo resumido da internacao em 1-2 frases",
  "diagnostico_saida": "diagnostico final na alta ou null",
  "cid_saida": "codigo CID de saida ou null",
  "observacoes": "historico medico relevante mencionado (ex: cirurgias previas, comorbidades) ou null",
  "procedimentos": [
    {
      "nome": "nome do procedimento",
      "tipo": "cirurgico ou diagnostico ou terapeutico ou ambulatorial",
      "data": "YYYY-MM-DD ou null",
      "hora": "HH:MM ou null",
      "anestesia": "sem ou local ou sedacao ou epidural ou geral",
      "resultado": "descricao breve do resultado ou null",
      "observacoes": "observacoes adicionais ou null"
    }
  ]
}

Exemplos de procedimentos a identificar: cirurgia de revascularizacao miocardica,
cateterismo coronario, angioplastia, implante de stent, cateter Swan-Ganz,
toracocentese, drenagem de torax, cardioversao, implante de marcapasso,
endoscopia, colonoscopia, biopsias, ECG (se seriado ou importante).

Se nao encontrar algum campo, use null. Nunca invente dados nao presentes no documento.
"""


class SemCreditosError(Exception):
    pass


def extrair_internacao_pdf(
    pdf_bytes: bytes,
    nome_arquivo: str = "",
    on_progress=None,
) -> dict:
    """
    Recebe bytes de um PDF de prontuario hospitalar e retorna dict estruturado.

    on_progress(msg: str) — callback opcional para atualizar UI durante extracao.
    Levanta SemCreditosError se API sem credito.
    Levanta Exception em erros de API ou parsing.
    """
    if on_progress:
        on_progress("Convertendo paginas para imagem...")

    imagens_b64 = _pdf_para_imagens_b64(pdf_bytes, max_pags=_PAGINAS_MAX)

    if on_progress:
        on_progress(f"Enviando {len(imagens_b64)} paginas para Claudia...")

    dados = _chamar_visao(imagens_b64)
    dados["documento_local"] = nome_arquivo

    if on_progress:
        on_progress("Extracao concluida.")

    return dados


def _pdf_para_imagens_b64(pdf_bytes: bytes, max_pags: int = 10) -> list[str]:
    try:
        import pypdfium2 as _pdfium
    except ImportError:
        raise RuntimeError("pypdfium2 nao instalado — execute: pip install pypdfium2")
    import io as _io

    doc = _pdfium.PdfDocument(pdf_bytes)
    imgs = []
    try:
        for i in range(min(max_pags, len(doc))):
            bitmap = doc[i].render(scale=1.5)  # ~162 dpi — legivel sem ser muito pesado
            pil_img = bitmap.to_pil()
            buf = _io.BytesIO()
            pil_img.save(buf, format="JPEG", quality=85)
            imgs.append(base64.b64encode(buf.getvalue()).decode())
    finally:
        doc.close()
    return imgs


def _chamar_visao(imagens_b64: list[str]) -> dict:
    try:
        from utils.claudia_engine import get_client
    except Exception as ex:
        raise RuntimeError(f"Cliente Claude indisponivel: {ex}") from ex

    try:
        from utils.api_checker import exigir_creditos as _exigir_cred
        _exigir_cred(get_client)
    except Exception as _ex_cred:
        if type(_ex_cred).__name__ == "SemCreditosError":
            raise SemCreditosError(str(_ex_cred)) from _ex_cred

    client = get_client()

    content = []
    for img in imagens_b64:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": img},
        })
    content.append({"type": "text", "text": _PROMPT})

    try:
        resp = client.messages.create(
            model=_MODELO,
            max_tokens=2048,
            system=_SYSTEM,
            messages=[{"role": "user", "content": content}],
        )
    except Exception as ex:
        if "credit balance" in str(ex).lower():
            raise SemCreditosError("Sem creditos na API Claude") from ex
        raise

    texto = resp.content[0].text.strip()

    # remover code fence residual
    if texto.startswith("```"):
        partes = texto.split("```")
        texto = partes[1] if len(partes) > 1 else texto
        if texto.startswith("json"):
            texto = texto[4:]
    texto = texto.strip()

    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as ex:
        log.error(f"[EXTRAT_INT] JSON invalido: {texto[:200]}")
        raise ValueError(f"Claude retornou JSON invalido: {ex}") from ex

    # garantir chaves obrigatorias com fallback
    dados.setdefault("hospital", "")
    dados.setdefault("procedimentos", [])

    return dados
