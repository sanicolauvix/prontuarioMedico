# -*- coding: utf-8 -*-
# Prontuario Medico | app.py -- bootstrap
import flet as ft
import logging
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from dados.model_prontuario import criar_tabelas

log = logging.getLogger(__name__)


def criar_tela_prontuario(page: ft.Page, voltar_fn=None):
    criar_tabelas()
    import threading as _thr
    def _sync_bg():
        try:
            from dados.model_prontuario import sincronizar_anexos_pendentes
            sincronizar_anexos_pendentes()
        except Exception:
            pass
    _thr.Thread(target=_sync_bg, daemon=True).start()

    from telas.tela_hub import criar_tela_hub
    return criar_tela_hub(page, voltar_fn)
