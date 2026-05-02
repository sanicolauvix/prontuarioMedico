# -*- coding: utf-8 -*-
"""
prontuario/backup/drive_backup.py
Wrapper fino sobre backup.db_backup para o app Prontuario Medico.
Toda a logica de Drive e hashes esta em backup/db_backup.py (modulo compartilhado).
"""
import os

from backup.db_backup import (
    BackupConfig,
    fazer_backup      as _fb,
    restaurar_backup  as _rb,
    sincronizar_ao_iniciar as _si,
    carregar_historico as _ch,
    listar_backups_drive as _lbd,
    verificar_credenciais,
    houve_mudanca     as _hm,
)

_HERE       = os.path.dirname(os.path.abspath(__file__))
_PRONTUARIO = os.path.dirname(_HERE)
_KOIOS_ROOT = os.path.dirname(_PRONTUARIO)

CONFIG = BackupConfig(
    pasta_raiz="Koios_Prontuario",
    dbs={
        "prontuario_db": os.path.join(_PRONTUARIO, "dados",    "prontuario.db"),
        "koios_db":      os.path.join(_KOIOS_ROOT, "database", "koios.db"),
    },
    hist_path=os.path.join(_KOIOS_ROOT, "database", "historico_backup_prontuario.json"),
    hash_path=os.path.join(_KOIOS_ROOT, "database", "ultimo_backup_prontuario.json"),
)


def fazer_backup(forcar: bool = False, callback_progresso=None):
    return _fb(CONFIG, forcar=forcar, callback=callback_progresso)


def restaurar_backup_completo(callback_progresso=None):
    return _rb(CONFIG, callback=callback_progresso)


def sincronizar_ao_iniciar(callback_progresso=None):
    return _si(CONFIG, callback=callback_progresso)


def carregar_historico():
    return _ch(CONFIG)


def listar_backups_drive():
    return _lbd(CONFIG)


def houve_mudanca():
    return _hm(CONFIG)
