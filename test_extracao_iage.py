# -*- coding: utf-8 -*-
"""
test_extracao_iage.py
Roda direto: python test_extracao_iage.py <caminho_do_pdf>
Mostra exatamente o que acontece na extracao sem precisar do app.
"""
import sys
import os
import json

# Garante imports relativos funcionem a partir da raiz do projeto
sys.path.insert(0, os.path.dirname(__file__))

PDF_FALLBACK = r"c:\Users\user\Downloads\clonoscopia endoscopiaa-sebastiao__000429.pdf"

def main():
    caminho = sys.argv[1] if len(sys.argv) > 1 else PDF_FALLBACK
    if not os.path.exists(caminho):
        print(f"[ERRO] Arquivo nao encontrado: {caminho}")
        print("Uso: python test_extracao_iage.py <caminho_do_pdf>")
        sys.exit(1)

    print(f"\n=== TESTE DE EXTRACAO ===")
    print(f"Arquivo: {caminho}")
    conteudo = open(caminho, "rb").read()
    print(f"Tamanho: {len(conteudo):,} bytes\n")

    # ── 1. pdfplumber ──────────────────────────────────────────
    print("--- [1] PDFPLUMBER ---")
    try:
        import pdfplumber
        with pdfplumber.open(caminho) as pdf:
            total_pags = len(pdf.pages)
            texto_por_pag = []
            for i, pag in enumerate(pdf.pages):
                t = pag.extract_text() or ""
                texto_por_pag.append(t)
                print(f"  Pag {i+1}: {len(t)} chars | preview: {repr(t[:80])}")
        texto_completo = "\n".join(texto_por_pag)
        print(f"\n  Total chars extraidos: {len(texto_completo.strip())}")
    except Exception as e:
        print(f"  ERRO pdfplumber: {e}")
        texto_completo = ""
        total_pags = 0

    # ── 2. Decisao de roteamento ───────────────────────────────
    print("\n--- [2] ROTEAMENTO ---")
    _pdf_escaneado = len(texto_completo.strip()) < 200

    print(f"  Chars extraidos: {len(texto_completo.strip())}")
    print(f"  Escaneado (<200 chars): {_pdf_escaneado}")
    caminho_str = "VISAO (extrair_via_api_pdf)" if _pdf_escaneado else "TEXTO (extrair_via_api)"
    print(f"  => {caminho_str}")

    # ── 3. Chamada API ─────────────────────────────────────────
    print(f"\n--- [3] API CLAUDE ---")
    try:
        if _pdf_escaneado:
            from extratores.extrator_api import extrair_via_api_pdf
            print("  Chamando extrair_via_api_pdf...")
            resultado = extrair_via_api_pdf(conteudo, os.path.basename(caminho))
        else:
            from extratores.extrator_api import extrair_via_api
            print("  Chamando extrair_via_api...")
            resultado = extrair_via_api(texto_completo, os.path.basename(caminho))

        if resultado is None:
            print("  RESULTADO: None (API falhou ou indisponivel)")
        else:
            multiplos = resultado.get("multiplos_laudos", False)
            print(f"  multiplos_laudos: {multiplos}")
            if multiplos:
                laudos = resultado.get("laudos", [])
                print(f"  Numero de laudos: {len(laudos)}")
                for i, l in enumerate(laudos):
                    print(f"    Laudo {i+1}: tipo_exame={l.get('tipo_exame')} | resumo[:60]={repr(l.get('resumo','')[:60])}")
            else:
                print(f"  tipo: {resultado.get('tipo')}")
                print(f"  tipo_exame: {resultado.get('tipo_exame')}")
                print(f"  laboratorio: {resultado.get('laboratorio')}")
            print(f"\n  JSON completo:\n{json.dumps(resultado, ensure_ascii=False, indent=2)[:800]}")
    except Exception as e:
        import traceback
        print(f"  ERRO na API: {e}")
        traceback.print_exc()

    print("\n=== FIM ===\n")

if __name__ == "__main__":
    main()
