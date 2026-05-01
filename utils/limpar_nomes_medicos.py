# -*- coding: utf-8 -*-
"""
Roda UMA VEZ para limpar nomes sujos de médicos já no banco.
python limpar_nomes_medicos.py
"""
import sqlite3, sys
sys.path.insert(0, ".")
from dados.model_prontuario import DB_PATH, _limpar_nome_medico

# Testa o normalizador primeiro
testes = [
    "CINTIA NASCIMENTO Data Nascimento : 02/04/1962",
    "PEDRO DAHER CARNEIRO GAMBERINCIRM: 11448 UF: ES",
    "RICARDO BARRETO CONTAO Dt. Atend: 02/04/2024 - 13:56:27",
    "Sem solicitacao Medica Data Nascimento : 02/04/1962",
    "MARCIO SECUNDINO ANDRADE DA SILVA",
    "MARCEL ORLANDI PAIANO Data Nascimento : 02/04/1962",
]
print("Teste normalizador:")
for t in testes:
    print(f"  '{t}'")
    print(f"  → '{_limpar_nome_medico(t)}'")
    print()

resp = input("Aplicar limpeza no banco? (s/n): ")
if resp.lower() != "s":
    print("Cancelado.")
    exit()

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

cur.execute("SELECT id, nome FROM medicos ORDER BY nome")
medicos = cur.fetchall()

atualizados = 0
removidos   = 0
for mid, nome in medicos:
    nome_limpo = _limpar_nome_medico(nome)
    if nome_limpo == nome:
        continue
    print(f"  '{nome}' → '{nome_limpo}'")
    # Verifica duplicata
    cur.execute("SELECT id FROM medicos WHERE UPPER(TRIM(nome))=UPPER(?) AND id!=?",
                (nome_limpo, mid))
    dup = cur.fetchone()
    if dup:
        cur.execute("UPDATE exames SET medico_id=? WHERE medico_id=?", (dup[0], mid))
        cur.execute("DELETE FROM medicos WHERE id=?", (mid,))
        print(f"    → mesclado com id={dup[0]}, registro removido")
        removidos += 1
    else:
        cur.execute("UPDATE medicos SET nome=? WHERE id=?", (nome_limpo, mid))
        atualizados += 1

conn.commit()
conn.close()
print(f"\n✅ {atualizados} atualizados, {removidos} removidos (mesclados).")