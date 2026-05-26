# -*- coding: utf-8 -*-
"""
test_creditos.py — Teste isolado de verificacao de creditos da API Claude.

Roda: python test_creditos.py

Mostra:
  - Se a chave esta configurada
  - Se ha creditos disponíveis
  - Tempo de resposta do ping
  - Comportamento do cache
"""
import sys
import os
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
sys.path.insert(0, os.path.dirname(__file__))

def main():
    print("\n=== TESTE DE CRÉDITOS API CLAUDE ===\n")

    # ── 1. Chave configurada? ──────────────────────────────────
    print("--- [1] CHAVE API ---")
    try:
        from utils.claudia_engine import get_client
        client = get_client()
        print("  Chave: configurada no banco")
    except Exception as ex:
        print(f"  ERRO: chave nao encontrada — {ex}")
        print("  Configure a chave em Configuracoes > Integracao IA")
        sys.exit(1)

    # ── 2. Verificacao de creditos ─────────────────────────────
    print("\n--- [2] VERIFICAÇÃO DE CRÉDITOS ---")
    from utils.api_checker import verificar_creditos, exigir_creditos, SemCreditosError, invalidar_cache

    # Garante que o cache esta limpo para testar de verdade
    invalidar_cache()

    t0 = time.time()
    ok = verificar_creditos(get_client)
    dt = time.time() - t0

    if ok:
        print(f"  Resultado: CREDITOS OK ({dt:.2f}s)")
    else:
        print(f"  Resultado: SEM CRÉDITOS ({dt:.2f}s)")
        print(f"  Acao: acesse console.anthropic.com/settings/billing")

    # ── 3. Teste do cache ──────────────────────────────────────
    print("\n--- [3] CACHE ---")
    t0 = time.time()
    ok2 = verificar_creditos(get_client)
    dt2 = time.time() - t0
    print(f"  Segunda chamada (deve ser instantanea): {dt2*1000:.1f}ms — ok={ok2}")

    if dt2 < 0.01:
        print("  Cache funcionando corretamente")
    else:
        print("  Cache pode nao estar funcionando (esperado < 10ms)")

    # ── 4. Teste da excecao ────────────────────────────────────
    print("\n--- [4] exigir_creditos() ---")
    invalidar_cache()
    try:
        exigir_creditos(get_client)
        print("  exigir_creditos(): passou — creditos OK")
    except SemCreditosError as e:
        print(f"  exigir_creditos(): SemCreditosError levantada corretamente")
        print(f"  Mensagem: {e}")

    # ── Resumo ─────────────────────────────────────────────────
    print("\n=== RESUMO ===")
    if ok:
        print("  Tudo OK — API disponivel para uso")
    else:
        print("  Sem creditos — operacoes com IA serao bloqueadas com mensagem clara")
        print("  Adicione fundos: console.anthropic.com/settings/billing")
    print()

if __name__ == "__main__":
    main()
