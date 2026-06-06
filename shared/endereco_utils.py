# -*- coding: utf-8 -*-
# SHARED | shared/endereco_utils.py -- gerenciado por flet_shared/sync_shared.py
"""Funcoes puras para manipulacao de dados de endereco.

Nao depende de Flet. Pode ser importado em qualquer tela.
"""
import json


def parsear_endereco(endereco_dados_raw, fallback_texto: str = "") -> dict:
    """Converte o campo endereco_dados do banco para dict.

    Aceita: string JSON, dict direto, None ou "".
    Se o resultado for vazio e fallback_texto for fornecido, retorna
    {"endereco_fmt": fallback_texto} para que tela_endereco exiba o valor legado.
    """
    if isinstance(endereco_dados_raw, dict):
        parsed = endereco_dados_raw
    elif isinstance(endereco_dados_raw, str) and endereco_dados_raw.strip():
        try:
            parsed = json.loads(endereco_dados_raw)
        except Exception:
            parsed = {}
    else:
        parsed = {}

    if not parsed and fallback_texto and fallback_texto.strip():
        parsed = {"endereco_fmt": fallback_texto.strip()}

    return parsed


def label_endereco(end: dict) -> str:
    """Retorna string de exibicao do endereco para o usuario.

    Prioridade: campo endereco_fmt > montagem dos campos individuais > "Nao informado".
    """
    if not end:
        return "Nao informado"
    if end.get("endereco_fmt"):
        return end["endereco_fmt"]
    if end.get("logradouro"):
        partes = [
            end.get("logradouro", ""),
            end.get("numero", ""),
        ]
        cidade_estado = "/".join(filter(None, [end.get("cidade", ""), end.get("estado", "")]))
        linha = ", ".join(filter(None, partes))
        if cidade_estado:
            linha = f"{linha} -- {cidade_estado}" if linha else cidade_estado
        return linha.strip(", --/") or "Nao informado"
    return "Nao informado"


def serializar_endereco(end: dict) -> tuple:
    """Retorna (endereco_fmt_str, endereco_dados_json_str, lat, lng) prontos para salvar no banco."""
    if not end:
        return "", "", None, None
    return (
        end.get("endereco_fmt", ""),
        json.dumps(end),
        end.get("lat"),
        end.get("lng"),
    )
