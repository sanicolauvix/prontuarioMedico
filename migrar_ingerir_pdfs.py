"""
Roda ingerir_pdf para cada internacao que tem documento_local
mas nao tem paginas em pdf_paginas ainda.
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dados.model_prontuario import DB_PATH
from utils.drive_sync import _get_creds
from utils.processador_pdf import ingerir_pdf

con = sqlite3.connect(DB_PATH)
rows = con.execute("""
    SELECT i.id, i.hospital, i.data_entrada, i.documento_local
    FROM internacoes i
    WHERE i.documento_local IS NOT NULL
      AND i.documento_local != ''
      AND NOT EXISTS (
          SELECT 1 FROM pdf_paginas p WHERE p.internacao_id = i.id
      )
    ORDER BY i.data_entrada
""").fetchall()
con.close()

if not rows:
    print("Nenhuma internacao pendente — tudo ja tem paginas no banco.")
    sys.exit(0)

print(f"{len(rows)} internacao(oes) para ingerir:\n")
for r in rows:
    print(f"  id={r[0]} | {r[1]} | {r[2]} | {r[3]}")

print()
creds = _get_creds()

for internacao_id, hospital, data_entrada, doc_local in rows:
    if not os.path.exists(doc_local):
        print(f"[SKIP] id={internacao_id} — arquivo nao encontrado: {doc_local}")
        continue

    print(f"[INGERINDO] id={internacao_id} | {hospital} | {data_entrada}")

    def _prog(pag, total, msg):
        print(f"   pag {pag}/{total}: {msg}")

    try:
        result = ingerir_pdf(
            doc_local,
            internacao_id=internacao_id,
            db_path=DB_PATH,
            on_progress=_prog,
            creds=creds,
        )
        print(f"   OK: {result['total']} paginas gravadas, ids={result['ids']}\n")
    except Exception as ex:
        print(f"   ERRO: {ex}\n")

print("Concluido.")
