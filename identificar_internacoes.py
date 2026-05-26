"""
Roda Fase 1 do extrator em cada PDF de prontuario/exames (sebastiao 1-13).
SEM salvar nada no banco — apenas identifica e exibe o resultado para revisao.

Uso:
    python identificar_internacoes.py
    python identificar_internacoes.py "sebastiao 1.pdf"   # so um arquivo
"""
import os, sys, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

PASTA = os.path.join(os.path.dirname(__file__), "exames")

# Ordem: 1 a 13 + ATEN
NOMES = [
    "sebastião 1.pdf",
    "sebastião 2.pdf",
    "sebastiao 3.pdf",
    "sebastião 4.pdf",
    "SEBASTIÃO 5.pdf",
    "SEBASTIÃO 6.pdf",
    "SEBASTIÃO 7.pdf",
    "SEBASTIÃO 8.pdf",
    "SEBASTIÃO 9.pdf",
    "SEBASTIÃO 10.pdf",
    "SEBASTIÃO 11.pdf",
    "SEBASTIÃO 12.pdf",
    "SEBASTIÃO 13.pdf",
]

# filtro por argumento
if len(sys.argv) > 1:
    filtro = sys.argv[1].lower()
    NOMES = [n for n in NOMES if filtro in n.lower()]
    if not NOMES:
        print(f"Nenhum PDF encontrado com '{filtro}'")
        sys.exit(1)


def _extrair_fase1(pdf_bytes, nome):
    from extratores.extrator_prontuario import extrair_internacoes_pdf
    def _prog(msg):
        print(f"  {msg}", flush=True)
    return extrair_internacoes_pdf(pdf_bytes, nome_arquivo=nome, on_progress=_prog)


resultados = []

for nome in NOMES:
    path = os.path.join(PASTA, nome)
    if not os.path.exists(path):
        print(f"\n[AVISO] Nao encontrado: {nome}")
        continue

    tam_mb = os.path.getsize(path) / 1_048_576
    print(f"\n{'='*70}")
    print(f"Processando: {nome}  ({tam_mb:.1f} MB)")
    print(f"{'='*70}")

    try:
        with open(path, "rb") as f:
            pdf_bytes = f.read()

        resultado = _extrair_fase1(pdf_bytes, nome)
        internacoes = resultado.get("internacoes") or []

        print(f"  Paciente: {resultado.get('paciente_nome','?')}")
        print(f"  Internacoes encontradas: {len(internacoes)}")
        for i, intern in enumerate(internacoes, 1):
            print(f"\n  [{i}] {intern.get('hospital','?')}")
            print(f"       entrada : {intern.get('data_entrada','null')}")
            print(f"       saida   : {intern.get('data_saida','null')}")
            print(f"       tipo    : {intern.get('tipo','?')} | objetivo: {intern.get('objetivo','?')}")
            print(f"       motivo  : {str(intern.get('motivo',''))[:100]}")
            print(f"       CID     : {intern.get('cid_entrada','null')}")

        resultados.append({"arquivo": nome, "resultado": resultado})

    except Exception as ex:
        print(f"  ERRO: {ex}")
        resultados.append({"arquivo": nome, "erro": str(ex)})

# salvar resultado completo em JSON para consulta posterior
saida = os.path.join(os.path.dirname(__file__), "temp", "identificacao_internacoes.json")
os.makedirs(os.path.dirname(saida), exist_ok=True)
with open(saida, "w", encoding="utf-8") as f:
    json.dump(resultados, f, ensure_ascii=False, indent=2)

print(f"\n\nResultado completo salvo em: {saida}")
