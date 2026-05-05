# -*- coding: utf-8 -*-
# KOIOS v1.0 | extrator_api.py
"""
extrator_api.py - Extração de exames via Claude API.

Substitui os parsers regex por laboratório por uma chamada à API Claude,
que retorna JSON estruturado para qualquer laboratório e formato.

Usado por extrair_pdf_bytes() como tentativa principal.
Fallback automático para regex se API indisponível.
"""

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

        # Garante todos os campos obrigatorios
        dados.setdefault("arquivo_origem",         nome_arquivo)
        dados.setdefault("drive_file_id",          None)
        dados.setdefault("resultado_texto",        texto)
        dados.setdefault("tipo",                   "numerico")
        dados.setdefault("paciente_nome",          None)
        dados.setdefault("paciente_cpf",           None)
        dados.setdefault("data_exame",             None)
        dados.setdefault("laboratorio",            "Desconhecido")
        dados.setdefault("medico_solicit",         None)
        dados.setdefault("tipo_exame",             "")
        dados.setdefault("resultados",             [])
        dados.setdefault("laudo",                  None)
        dados.setdefault("modelo_nao_configurado", False)
        dados.setdefault("subtipo",                None)

        for r in dados.get("resultados", []):
            r.setdefault("sub_resultados", [])
            # Garante que valor e float ou None
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
