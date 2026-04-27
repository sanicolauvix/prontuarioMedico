"""
fix_seed.py — Alimenta banco prontuario.db existente com dados iniciais.

Execute pelo terminal na raiz do projeto Koios:
    python -m prontuario.dados.fix_seed
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prontuario.dados.model_prontuario import seed_especialidades, DB_PATH

if __name__ == "__main__":
    print(f"Banco: {DB_PATH}")
    print("Inserindo especialidades médicas pré-configuradas...")
    seed_especialidades()
    print("Concluído. Banco atualizado com sucesso.")
