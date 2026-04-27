"""
reorganizar_prontuario.py — Koios
==================================
Reorganiza a pasta prontuario/ em subpastas temáticas.

ESTRUTURA NOVA:
  prontuario/
  ├── __init__.py              (atualizado)
  ├── app.py                   (atualizado)
  ├── app_prontuario_interno.py (atualizado)
  ├── telas/                   ← 14 arquivos tela_*.py
  │   └── __init__.py
  ├── extratores/              ← extrator_pdf, extrator_receita, processador
  │   └── __init__.py
  ├── dados/                   ← model, exames_padrao_dados, limpeza
  │   └── __init__.py
  └── utils/                   ← alarmes_remedios, parecer_medico
      └── __init__.py

USO:
  1. Primeiro em DRY-RUN (padrão): python reorganizar_prontuario.py
  2. Depois aplica: python reorganizar_prontuario.py --aplicar

SEGURANÇA:
  - Faz backup completo antes de alterar
  - Modo dry-run mostra tudo que vai fazer sem alterar nada
"""

import os
import sys
import shutil
import re
from datetime import datetime

PROJETO = r"C:\pessoal\python\Koios"
PRONT = os.path.join(PROJETO, "prontuario")
APLICAR = "--aplicar" in sys.argv

# ══════════════════════════════════════════════════════════════
# MAPEAMENTO: arquivo → subpasta destino
# ══════════════════════════════════════════════════════════════

MOVER = {
    # telas/ — todas as telas
    "tela_consultas_medicas.py": "telas",
    "tela_especialidades.py":    "telas",
    "tela_exames.py":            "telas",
    "tela_exames_padrao.py":     "telas",
    "tela_incluir_exame.py":     "telas",
    "tela_incluir_exame_padrao.py": "telas",
    "tela_links_medico.py":      "telas",
    "tela_login.py":             "telas",
    "tela_medico_view.py":       "telas",
    "tela_medicos.py":           "telas",
    "tela_parecer.py":           "telas",
    "tela_pendencias.py":        "telas",
    "tela_remedios.py":          "telas",

    # extratores/ — extração de PDFs
    "extrator_pdf.py":           "extratores",
    "extrator_receita.py":       "extratores",
    "processador_exame.py":      "extratores",

    # dados/ — modelo e dados
    "model.py":                  "dados",
    "exames_padrao_dados.py":    "dados",
    "limpeza.py":                "dados",

    # utils/ — utilitários
    "alarmes_remedios.py":       "utils",
    "parecer_medico.py":         "utils",
    "limpar_nomes_medicos.py":   "utils",
}

# Arquivos que FICAM na raiz do prontuario/
FICAM = ["__init__.py", "app.py", "app_prontuario_interno.py"]

# ══════════════════════════════════════════════════════════════
# REGRAS DE REESCRITA DE IMPORTS
# ══════════════════════════════════════════════════════════════
# Para cada subpasta, define como reescrever imports relativos.
# Chave: (pasta_do_arquivo, modulo_importado) → novo_prefixo

def _subpasta_do_modulo(modulo):
    """Descobre em qual subpasta um módulo vai parar."""
    arquivo = modulo + ".py"
    return MOVER.get(arquivo)

def reescrever_import(linha, pasta_atual):
    """
    Reescreve uma linha de import relativo.
    pasta_atual: subpasta onde o arquivo está (ex: 'telas', 'dados', None=raiz)
    """
    # Detectar padrão: from .MODULO import ... ou from . import MODULO
    m = re.match(r'^(\s*)(from\s+)\.(\w+)(\s+import\s+.+)$', linha)
    if not m:
        return linha

    indent, from_kw, modulo, rest = m.groups()
    destino = _subpasta_do_modulo(modulo)

    if destino is None:
        # Módulo fica na raiz do prontuario (app, app_prontuario_interno)
        if pasta_atual is None:
            return linha  # mesmo nível, não muda
        else:
            return f"{indent}{from_kw}..{modulo}{rest}\n"

    if pasta_atual == destino:
        # Mesmo subpacote — mantém relativo simples
        return linha

    if pasta_atual is None:
        # Arquivo na raiz importando de subpasta
        return f"{indent}{from_kw}.{destino}.{modulo}{rest}\n"
    else:
        # Arquivo em subpasta importando de outra subpasta
        return f"{indent}{from_kw}..{destino}.{modulo}{rest}\n"


def reescrever_import_app_interno(linha):
    """Caso especial: from . import app_prontuario_interno as _int"""
    m = re.match(r'^(\s*)(from\s+)\.\s+(import\s+app_prontuario_interno.*)$', linha)
    if m:
        return linha  # Fica na mesma pasta, não muda
    return None


def reescrever_arquivo(caminho, pasta_atual):
    """Lê arquivo, reescreve imports, retorna (conteudo_novo, n_mudancas)."""
    with open(caminho, "r", encoding="utf-8", errors="replace") as f:
        linhas = f.readlines()

    novas = []
    mudancas = 0
    for linha in linhas:
        # Pular imports absolutos (from database.X, from shared.X, from tela_perfil, etc.)
        if re.match(r'^\s*from\s+(database|shared|tela_perfil|koios_log)\b', linha):
            novas.append(linha)
            continue

        # Tentar reescrever import relativo
        nova = reescrever_import(linha, pasta_atual)
        if nova != linha:
            mudancas += 1
        novas.append(nova)

    return "".join(novas), mudancas


# ══════════════════════════════════════════════════════════════
# EXECUÇÃO
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("REORGANIZAÇÃO DO PRONTUARIO")
    print("=" * 60)

    if not os.path.isdir(PRONT):
        print(f"ERRO: pasta não encontrada: {PRONT}")
        return

    # ── Listar o que vai acontecer ────────────────────────────
    subpastas = sorted(set(MOVER.values()))
    print(f"\nSubpastas a criar: {', '.join(subpastas)}")
    print(f"Arquivos a mover: {len(MOVER)}")
    print(f"Arquivos que ficam na raiz: {', '.join(FICAM)}")

    print(f"\nMovimentações:")
    for arq, dest in sorted(MOVER.items(), key=lambda x: (x[1], x[0])):
        existe = "✓" if os.path.exists(os.path.join(PRONT, arq)) else "✗ NÃO EXISTE"
        print(f"  {arq:40s} → {dest}/{arq}  {existe}")

    # ── Verificar imports que precisam mudar ───────────────────
    print(f"\nAnálise de imports:")
    total_mudancas = 0

    # Arquivos que ficam na raiz
    for arq in FICAM:
        caminho = os.path.join(PRONT, arq)
        if not os.path.exists(caminho):
            continue
        _, n = reescrever_arquivo(caminho, None)
        if n > 0:
            print(f"  {arq}: {n} imports a ajustar")
            total_mudancas += n

    # Arquivos que vão para subpastas
    for arq, dest in MOVER.items():
        caminho = os.path.join(PRONT, arq)
        if not os.path.exists(caminho):
            continue
        _, n = reescrever_arquivo(caminho, dest)
        if n > 0:
            print(f"  {arq}: {n} imports a ajustar")
            total_mudancas += n

    print(f"\nTotal de imports a reescrever: {total_mudancas}")

    if not APLICAR:
        print(f"\n{'=' * 60}")
        print(f"MODO DRY-RUN — nada foi alterado.")
        print(f"Para aplicar: python reorganizar_prontuario.py --aplicar")
        print(f"{'=' * 60}")
        return

    # ══════════════════════════════════════════════════════════
    # APLICAR
    # ══════════════════════════════════════════════════════════

    # 1. Backup
    bkp = os.path.join(PROJETO, f"prontuario_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copytree(PRONT, bkp)
    print(f"\n✓ Backup criado: {bkp}")

    # 2. Criar subpastas
    for sub in subpastas:
        pasta = os.path.join(PRONT, sub)
        os.makedirs(pasta, exist_ok=True)
        # Criar __init__.py vazio
        init = os.path.join(pasta, "__init__.py")
        if not os.path.exists(init):
            with open(init, "w", encoding="utf-8") as f:
                f.write(f'"""Subpacote prontuario.{sub}"""\n')
        print(f"  ✓ Criada: {sub}/")

    # 3. Mover arquivos e reescrever imports
    for arq, dest in MOVER.items():
        origem = os.path.join(PRONT, arq)
        destino = os.path.join(PRONT, dest, arq)

        if not os.path.exists(origem):
            print(f"  ⚠ Pulando (não existe): {arq}")
            continue

        # Reescrever imports
        conteudo, n = reescrever_arquivo(origem, dest)
        with open(destino, "w", encoding="utf-8") as f:
            f.write(conteudo)

        # Remover original
        os.remove(origem)
        status = f"({n} imports ajustados)" if n > 0 else ""
        print(f"  ✓ {arq} → {dest}/{arq} {status}")

    # 4. Atualizar arquivos que ficam na raiz
    for arq in FICAM:
        caminho = os.path.join(PRONT, arq)
        if not os.path.exists(caminho):
            continue
        conteudo, n = reescrever_arquivo(caminho, None)
        if n > 0:
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(conteudo)
            print(f"  ✓ {arq} atualizado ({n} imports)")

    # 5. Atualizar prontuario/__init__.py com re-exports para compatibilidade
    init_path = os.path.join(PRONT, "__init__.py")
    with open(init_path, "w", encoding="utf-8") as f:
        f.write('"""Pacote prontuario — reorganizado em subpastas."""\n')
        f.write("import os, sys\n\n")
        f.write("# Garantir que o diretório do projeto está no path\n")
        f.write("_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n")
        f.write("if _dir not in sys.path:\n")
        f.write("    sys.path.insert(0, _dir)\n")
    print(f"  ✓ __init__.py atualizado")

    # 6. Limpar arquivos soltos que sobraram
    for arq in ["koios.db", "koios_prontuario.log"]:
        p = os.path.join(PRONT, arq)
        if os.path.exists(p):
            print(f"  ℹ Arquivo solto mantido: {arq}")

    print(f"\n{'=' * 60}")
    print(f"✅ REORGANIZAÇÃO CONCLUÍDA!")
    print(f"{'=' * 60}")
    print(f"\nPróximos passos:")
    print(f"  1. Limpar caches: remover __pycache__ recursivamente")
    print(f"  2. Testar: python -c \"from prontuario.app import criar_prontuario\"")
    print(f"  3. Se der erro, restaurar backup: {bkp}")


if __name__ == "__main__":
    main()
