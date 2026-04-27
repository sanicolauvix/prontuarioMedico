"""Pacote prontuario — reorganizado em subpastas."""
import os, sys

# Garantir que o diretório do projeto está no path
_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _dir not in sys.path:
    sys.path.insert(0, _dir)
