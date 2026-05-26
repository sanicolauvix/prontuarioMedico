import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dados.model_prontuario import criar_tabelas, DB_PATH
import sqlite3

criar_tabelas()

con = sqlite3.connect(DB_PATH)
tabs = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
print("=== tabelas ===")
for t in tabs:
    cnt = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t}: {cnt}")

print("\n=== pdf_paginas colunas ===")
for r in con.execute("PRAGMA table_info(pdf_paginas)").fetchall():
    print(f"  {r[1]} {r[2]}")

print("\n=== importacoes_pdf colunas ===")
for r in con.execute("PRAGMA table_info(importacoes_pdf)").fetchall():
    print(f"  {r[1]} {r[2]}")

con.close()
