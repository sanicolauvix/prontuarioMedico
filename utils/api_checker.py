# -*- coding: utf-8 -*-
"""
api_checker.py — Verificacao de creditos da API Claude antes de operacoes.

Compartilhado entre todos os apps que usam a API Anthropic.

Uso padrao:
    from utils.api_checker import exigir_creditos, SemCreditosError
    from utils.claudia_engine import get_client

    # No inicio de qualquer operacao com a API:
    exigir_creditos(get_client)   # levanta SemCreditosError se sem creditos

    # Ou para verificar sem levantar excecao:
    if not verificar_creditos(get_client):
        mostrar_mensagem("Sem creditos")
"""

import logging
import time

_MODELO_PING  = "claude-haiku-4-5-20251001"  # modelo mais barato para o ping
_CACHE_SEG    = 300                            # 5 min entre verificacoes
_MSG_SEM_CRED = (
    "Sem créditos na API Claude — "
    "adicione fundos em console.anthropic.com/settings/billing"
)

_cache: dict = {"ts": 0.0, "ok": False}


class SemCreditosError(Exception):
    """Saldo de créditos insuficiente na API Claude."""


def _detectar_sem_creditos(ex: Exception) -> bool:
    return "credit balance" in str(ex).lower()


def verificar_creditos(get_client_fn, cache_min: int = 5) -> bool:
    """
    Verifica se a chave API tem creditos fazendo uma chamada minima (ping).
    Resultado cacheado por cache_min minutos.
    Retorna True se OK, False se sem creditos ou erro de autenticacao.
    """
    global _cache
    agora  = time.time()
    validade = cache_min * 60

    if agora - _cache["ts"] < validade:
        logging.debug(f"[API_CHECK] cache — ok={_cache['ok']}")
        return _cache["ok"]

    try:
        client = get_client_fn()
        client.messages.create(
            model=_MODELO_PING,
            max_tokens=1,
            messages=[{"role": "user", "content": "ok"}],
        )
        _cache = {"ts": agora, "ok": True}
        logging.info("[API_CHECK] creditos OK")
        return True

    except Exception as ex:
        sem_cred = _detectar_sem_creditos(ex)
        _cache = {"ts": agora, "ok": not sem_cred}
        if sem_cred:
            logging.warning(f"[API_CHECK] sem creditos: {ex}")
        else:
            logging.warning(f"[API_CHECK] erro no ping (chave invalida?): {ex}")
            # Erro de chave invalida ou outro — nao bloqueia (pode ser problema temporario)
            return True
        return False


def exigir_creditos(get_client_fn, cache_min: int = 5) -> None:
    """
    Como verificar_creditos, mas levanta SemCreditosError se sem creditos.
    Use antes de qualquer operacao custosa com a API.
    """
    if not verificar_creditos(get_client_fn, cache_min):
        raise SemCreditosError(_MSG_SEM_CRED)


def invalidar_cache() -> None:
    """Forca nova verificacao na proxima chamada (use apos adicionar creditos)."""
    global _cache
    _cache = {"ts": 0.0, "ok": False}
    logging.info("[API_CHECK] cache invalidado")
