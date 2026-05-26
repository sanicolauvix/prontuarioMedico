# -*- coding: utf-8 -*-
"""
test_mock_chunks.py
Testa o pipeline completo de extracao sem chamar a API real.
Substitui o cliente Claude por um mock que retorna respostas fixas.

Roda: python test_mock_chunks.py
"""
import sys, os, json, logging
sys.path.insert(0, os.path.dirname(__file__))
logging.basicConfig(level=logging.INFO, format="%(message)s")

PDF_PATH = r"C:\pessoal\exames\clonoscopia endoscopiaa-sebastiao__000429.pdf"

# ── Respostas simuladas (o que Claude deveria retornar para cada chunk) ──────
RESP_CHUNK1 = {
    "tipo": "laudo",
    "tipo_exame": "EDA",
    "laboratorio": "IAGE",
    "paciente_nome": "SEBASTIAO ALVES NICOLAU",
    "data_exame": "02/04/2024",
    "medico_solicit": "BERNARDO MUNIZ FRIZZERA BORGES",
    "resultados": [],
    "laudo": {
        "tipo_exame": "EDA",
        "texto_completo": "Esofago: calibre e distensibilidade preservados. Gastrite enantematosa.",
        "resumo": "Esofagite erosiva leve distal. Gastrite enantematosa leve de corpo e antro.",
        "conclusao": "1. Esofagite erosiva leve distal (grau A de Los Angeles). 2. Gastrite. 3. Bulboduodenite."
    }
}

RESP_CHUNK2 = {
    "tipo": "laudo",
    "tipo_exame": "Colonoscopia",
    "laboratorio": "IAGE",
    "paciente_nome": "SEBASTIAO ALVES NICOLAU",
    "data_exame": "02/04/2024",
    "medico_solicit": "BERNARDO MUNIZ FRIZZERA BORGES",
    "resultados": [],
    "laudo": {
        "tipo_exame": "Colonoscopia",
        "texto_completo": "Introducao do colonoscopio ate o ileo terminal. Colonoscopia dentro dos padroes da normalidade.",
        "resumo": "Colonoscopia dentro dos padroes da normalidade.",
        "conclusao": "1. Exame ate ileo terminal. 2. Colonoscopia dentro dos padroes da normalidade."
    }
}

# ── Mock do cliente Anthropic ─────────────────────────────────────────────────
class _MockContent:
    def __init__(self, text): self.text = text

class _MockResponse:
    def __init__(self, text): self.content = [_MockContent(text)]

class _MockMessages:
    def __init__(self, responses):
        self._resps = responses
        self._n = 0
    def create(self, **kwargs):
        r = self._resps[self._n % len(self._resps)]
        self._n += 1
        print(f"  [MOCK] chamada {self._n}: retornando tipo_exame={r.get('tipo_exame')}")
        return _MockResponse(json.dumps(r))

class _MockClient:
    def __init__(self, responses):
        self.messages = _MockMessages(responses)

# ── Patch get_client antes de importar extrator_api ──────────────────────────
import utils.claudia_engine as _engine
_engine._mock_client = _MockClient([RESP_CHUNK1, RESP_CHUNK2])
_original_get_client = _engine.get_client
_engine.get_client = lambda: _engine._mock_client

# ── Executar teste ─────────────────────────────────────────────────────────────
def main():
    if not os.path.exists(PDF_PATH):
        print(f"[ERRO] PDF nao encontrado: {PDF_PATH}")
        sys.exit(1)

    pdf_bytes = open(PDF_PATH, "rb").read()
    print(f"\n=== TESTE MOCK — SEM API REAL ===")
    print(f"PDF: {os.path.basename(PDF_PATH)} ({len(pdf_bytes):,} bytes)")

    print("\n--- [1] DIVISAO EM CHUNKS ---")
    from extratores.extrator_api import _pdf_em_chunks
    chunks = _pdf_em_chunks(pdf_bytes, paginas_por_chunk=2)
    print(f"  Total chunks: {len(chunks)}")
    for i, c in enumerate(chunks):
        print(f"  Chunk {i+1}: {len(c):,} bytes ({len(c)//1024} KB)")

    print("\n--- [2] EXTRACAO COMPLETA (mock) ---")
    from extratores.extrator_api import extrair_via_api_pdf
    resultado = extrair_via_api_pdf(pdf_bytes, os.path.basename(PDF_PATH))

    print("\n--- [3] RESULTADO ---")
    if resultado is None:
        print("  FALHOU: retornou None")
        sys.exit(1)

    multiplos = resultado.get("multiplos_laudos", False)
    print(f"  multiplos_laudos: {multiplos}")

    if multiplos:
        laudos = resultado.get("laudos", [])
        print(f"  Numero de laudos: {len(laudos)}")
        for i, l in enumerate(laudos):
            print(f"  Laudo {i+1}: tipo_exame={l.get('tipo_exame')}")
            print(f"    resumo: {l.get('resumo', '')[:80]}")
        print()
        if len(laudos) == 2:
            print("  PASS: 2 laudos extraidos corretamente")
        else:
            print(f"  FAIL: esperado 2 laudos, obteve {len(laudos)}")
    else:
        print(f"  tipo_exame: {resultado.get('tipo_exame')}")
        print("  FAIL: esperado multiplos_laudos=True, obteve exame unico")

    print("\n--- [4] FLOW _processar_reprocessando (simulado) ---")
    if multiplos:
        print("  dados.get('multiplos_laudos') = True")
        print("  -> fase[0] = 'selecao_laudo'  (tela de selecao aparece)")
        print("  PASS: tela correta seria exibida")
    else:
        print("  FAIL: iria para conferencia com dados vazios")

    print("\n=== FIM ===\n")

if __name__ == "__main__":
    try:
        main()
    finally:
        _engine.get_client = _original_get_client
