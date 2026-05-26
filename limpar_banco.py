import sqlite3
con = sqlite3.connect("dados/prontuario.db")
tabelas = [
    "pdf_paginas", "registros_clinicos", "internacao_dados_brutos", "sinais_internacao",
    "exame_anexos", "exame_resultados", "laudos", "exames",
    "procedimentos", "remedios", "internacoes"
]
for t in tabelas:
    try:
        con.execute(f"DELETE FROM {t}")
        print(f"  {t}: limpa")
    except Exception as ex:
        print(f"  {t}: {ex}")
con.commit()
print("\nEstado atual:")
rows = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for r in rows:
    cnt = con.execute(f"SELECT COUNT(*) FROM {r[0]}").fetchone()[0]
    print(f"  {r[0]}: {cnt}")
con.close()
