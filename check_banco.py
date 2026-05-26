import sqlite3, json
con = sqlite3.connect("dados/prontuario.db")

print("=== internacoes ===")
rows = con.execute("SELECT id, hospital, data_entrada, data_saida FROM internacoes ORDER BY data_entrada").fetchall()
for r in rows:
    print(f"  id={r[0]} | {r[1]} | {r[2]} -> {r[3]}")

print(f"\n=== pdf_paginas: {con.execute('SELECT COUNT(*) FROM pdf_paginas').fetchone()[0]} total ===")
rows = con.execute("SELECT internacao_id, status, COUNT(*) FROM pdf_paginas GROUP BY internacao_id, status ORDER BY internacao_id").fetchall()
for r in rows:
    print(f"  internacao_id={r[0]} | {r[1]} | {r[2]} pags")

print("\n=== registros_clinicos ===")
rows = con.execute("SELECT internacao_id, tipo, data_registro, profissional FROM registros_clinicos ORDER BY internacao_id, data_registro").fetchall()
for r in rows:
    print(f"  int={r[0]} | {r[1]} | {r[2]} | {(r[3] or '')[:40]}")

print("\n=== sinais_internacao ===")
cnt = con.execute("SELECT COUNT(*) FROM sinais_internacao").fetchone()[0]
print(f"  {cnt} registros")

print("\n=== exames ===")
rows = con.execute("SELECT internacao_id, tipo, tipo_exame, data_exame FROM exames ORDER BY internacao_id, data_exame").fetchall()
for r in rows:
    print(f"  int={r[0]} | {r[1]} | {r[2]} | {r[3]}")

con.close()
