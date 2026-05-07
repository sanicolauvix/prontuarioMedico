# -*- coding: utf-8 -*-
# KOIOS v1.0 | extrator_api.py
"""
extrator_api.py - Extração de exames via Claude API.

Substitui os parsers regex por laboratório por uma chamada à API Claude,
que retorna JSON estruturado para qualquer laboratório e formato.

Usado por extrair_pdf_bytes() como tentativa principal.
Fallback automático para regex se API indisponível.
"""

import base64
import json
import logging
import re

_MODELO = "claude-sonnet-4-6"
_MAX_TEXTO = 12000   # chars — suficiente para qualquer laudo; evita estourar tokens

_SYSTEM = (
    "Voce e um extrator de exames medicos laboratoriais brasileiros. "
    "Analise o texto de um PDF de laboratorio e retorne SOMENTE JSON valido, "
    "sem texto adicional, sem explicacoes, sem code fences."
)

_PROMPT = """Texto extraido de PDF de laboratorio:

{texto}

Retorne JSON com este formato exato (sem comentarios, sem texto extra):
{{
  "laboratorio": "nome do laboratorio (ex: MedSenior, Cremasco, Pretti, Virchow)",
  "paciente_nome": "NOME COMPLETO EM MAIUSCULAS ou null",
  "data_exame": "DD/MM/YYYY ou null",
  "medico_solicit": "nome do medico solicitante ou null",
  "tipo": "numerico",
  "tipo_exame": "nome(s) dos exames principais separados por virgula (ex: TSH, SHBG)",
  "resultados": [
    {{
      "parametro": "nome oficial normalizado em portugues (ex: SHBG, TSH, Glicemia de Jejum)",
      "valor": 48.4,
      "unidade": "nmol/L",
      "referencia": "texto da referencia como esta no PDF",
      "ref_min": 13.2,
      "ref_max": 89.5,
      "sub_resultados": []
    }}
  ],
  "laudo": null
}}

Regras obrigatorias:
- tipo "numerico": exames com valores numericos → resultados preenchido, laudo=null
- tipo "laudo": laudos descritivos (histopatologico, parasitologico, urocultura, endoscopia) → resultados=[], laudo={{tipo_exame,texto_completo,resumo,conclusao}}
- tipo "mapa": MAPA de pressao arterial ambulatorial → resultados com PA sist/diast/FC, laudo com resumo
- parametro: nome canonico portugues padronizado, sem abreviacoes desnecessarias
- valor: numero float (ponto como decimal), null se nao houver valor numerico claro
- ref_min/ref_max: float ou null; extraia do intervalo de referencia (ex: "13,2 a 89,5" → 13.2, 89.5)
- Para intervalos por sexo/idade, use o intervalo masculino adulto como padrao
- Ignore linhas de rodape, assinaturas, disclaimers e separadores (----)
- sub_resultados: lista de resultados filhos (ex: eRFG como filho de Creatinina), normalmente []
"""


def extrair_via_api(texto: str, nome_arquivo: str = "") -> dict | None:
    """
    Envia texto bruto do PDF para Claude API e retorna dict no mesmo formato
    de extrair_pdf_bytes(). Retorna None em qualquer falha (permite fallback).
    """
    try:
        from utils.claudia_engine import get_client
        client = get_client()
    except Exception as ex:
        logging.warning(f"[API_EXT] cliente indisponivel: {ex}")
        return None

    texto_truncado = texto[:_MAX_TEXTO]

    try:
        resp = client.messages.create(
            model=_MODELO,
            max_tokens=2048,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": _PROMPT.format(texto=texto_truncado),
            }],
        )
        raw = resp.content[0].text.strip()

        # Remove code fences que Claude as vezes adiciona mesmo com instrucao contraria
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        dados = json.loads(raw)

        dados.setdefault("arquivo_origem", nome_arquivo)
        dados.setdefault("drive_file_id",  None)
        dados.setdefault("laboratorio",    "Desconhecido")
        dados.setdefault("paciente_nome",  None)
        dados.setdefault("paciente_cpf",   None)
        dados.setdefault("data_exame",     None)
        dados.setdefault("medico_solicit", None)

        # Multiplos laudos: retorna como esta
        if dados.get("multiplos_laudos"):
            logging.info(
                f"[API_EXT] multiplos laudos — lab={dados['laboratorio']} "
                f"n={len(dados.get('laudos', []))}"
            )
            return dados

        # Exame unico: completa campos obrigatorios
        dados.setdefault("resultado_texto",        texto)
        dados.setdefault("tipo",                   "numerico")
        dados.setdefault("tipo_exame",             "")
        dados.setdefault("resultados",             [])
        dados.setdefault("laudo",                  None)
        dados.setdefault("modelo_nao_configurado", False)
        dados.setdefault("subtipo",                None)

        for r in dados.get("resultados", []):
            r.setdefault("sub_resultados", [])
            v = r.get("valor")
            if isinstance(v, str):
                try:
                    r["valor"] = float(v.replace(",", "."))
                except ValueError:
                    r["valor"] = None

        logging.info(
            f"[API_EXT] OK — lab={dados['laboratorio']} "
            f"tipo={dados['tipo']} resultados={len(dados['resultados'])}"
        )
        return dados

    except json.JSONDecodeError as ex:
        logging.warning(f"[API_EXT] JSON invalido na resposta: {ex} | raw={raw[:200]}")
        return None
    except Exception as ex:
        logging.warning(f"[API_EXT] falha na extracao: {ex}")
        return None


_PROMPT_PDF = """Analise este documento PDF de exame medico (pode ser escaneado).
Ignore paginas de fotos/imagens endoscopicas — extraia apenas as paginas de laudo textual.

Se o PDF contiver MAIS DE UM laudo/exame distintos (ex: EDA + Colonoscopia no mesmo PDF),
retorne SOMENTE este formato:
{
  "multiplos_laudos": true,
  "laboratorio": "nome do lab",
  "paciente_nome": "NOME COMPLETO EM MAIUSCULAS ou null",
  "data_exame": "DD/MM/YYYY ou null",
  "medico_solicit": "nome do medico ou null",
  "laudos": [
    {
      "tipo_exame": "EDA",
      "texto_completo": "texto integral do laudo EDA",
      "resumo": "achados principais",
      "conclusao": "conclusao/diagnostico"
    },
    {
      "tipo_exame": "Colonoscopia",
      "texto_completo": "texto integral do laudo Colonoscopia",
      "resumo": "achados principais",
      "conclusao": "conclusao/diagnostico"
    }
  ]
}

Se o PDF contiver apenas UM laudo/exame, retorne:
{
  "laboratorio": "nome do lab",
  "paciente_nome": "NOME COMPLETO EM MAIUSCULAS ou null",
  "data_exame": "DD/MM/YYYY ou null",
  "medico_solicit": "nome do medico ou null",
  "tipo": "numerico" ou "laudo",
  "tipo_exame": "nome do exame (ex: EDA, Colonoscopia, TSH)",
  "resultados": [],
  "laudo": {
    "tipo_exame": "nome do exame",
    "texto_completo": "texto integral do laudo",
    "resumo": "achados principais em topicos",
    "conclusao": "conclusao/diagnostico"
  }
}

Para exames numericos (hemograma, bioquimica): tipo='numerico', resultados=[{parametro,valor,unidade,referencia,ref_min,ref_max}], laudo=null.
Para laudos descritivos (endoscopia, colonoscopia, histopatologico): tipo='laudo', resultados=[], laudo={...}.
Retorne SOMENTE JSON valido, sem texto adicional, sem code fences."""


def extrair_via_api_pdf(pdf_bytes: bytes, nome_arquivo: str = "") -> dict | None:
    """
    Envia o PDF bruto (bytes) para Claude via visao nativa (document content block).
    Usado para PDFs escaneados onde pdfplumber nao extrai texto suficiente.
    Retorna None em qualquer falha (permite fallback para regex).
    """
    try:
        from utils.claudia_engine import get_client
        client = get_client()
    except Exception as ex:
        logging.warning(f"[API_PDF] cliente indisponivel: {ex}")
        return None

    _pdf_kb = len(pdf_bytes) // 1024
    logging.info(f"[API_PDF] enviando PDF — {_pdf_kb} KB")

    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    try:
        resp = client.messages.create(
            model=_MODELO,
            max_tokens=4096,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": _PROMPT_PDF,
                    },
                ],
            }],
        )
        raw = resp.content[0].text.strip()

        # Remove code fences eventuais
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        dados = json.loads(raw)

        dados.setdefault("arquivo_origem",  nome_arquivo)
        dados.setdefault("drive_file_id",   None)
        dados.setdefault("resultado_texto", "")
        dados.setdefault("laboratorio",     "Desconhecido")
        dados.setdefault("paciente_nome",   None)
        dados.setdefault("paciente_cpf",    None)
        dados.setdefault("data_exame",      None)
        dados.setdefault("medico_solicit",  None)

        # Multiplos laudos: retorna como esta, sem completar campos de exame unico
        if dados.get("multiplos_laudos"):
            logging.info(
                f"[API_PDF] multiplos laudos — lab={dados['laboratorio']} "
                f"n={len(dados.get('laudos', []))}"
            )
            return dados

        # Exame unico: completa campos obrigatorios
        dados.setdefault("tipo",                   "laudo")
        dados.setdefault("tipo_exame",             "")
        dados.setdefault("resultados",             [])
        dados.setdefault("laudo",                  None)
        dados.setdefault("modelo_nao_configurado", False)
        dados.setdefault("subtipo",                None)

        logging.info(
            f"[API_PDF] OK — lab={dados['laboratorio']} "
            f"tipo={dados['tipo']} exame={dados['tipo_exame']}"
        )
        return dados

    except json.JSONDecodeError as ex:
        _msg = f"[API_PDF] JSON invalido: {ex} | raw={raw[:300]}"
        logging.warning(_msg)
        _log_arquivo(_msg)
        return None
    except Exception as ex:
        _msg = f"[API_PDF] FALHA ({type(ex).__name__}): {ex}"
        logging.warning(_msg)
        _log_arquivo(_msg)
        return None


def _log_arquivo(msg: str) -> None:
    """Grava msg em logs/erro_processar.log para diagnostico."""
    try:
        from pathlib import Path as _Path
        from datetime import datetime as _dt
        log_path = _Path(__file__).parent.parent / "logs" / "erro_processar.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{_dt.now()} {msg}\n")
    except Exception:
        pass
