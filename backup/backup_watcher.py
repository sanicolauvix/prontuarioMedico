"""
prontuario/backup/backup_watcher.py
Observador automático de mudanças com debounce de 30 min.

Uso:
    from prontuario.backup.backup_watcher import BackupWatcher, notify_db_changed

    watcher = BackupWatcher()
    watcher.iniciar()             # após login bem-sucedido

    # em qualquer função que altere o banco:
    notify_db_changed()
"""

import logging
import os
import threading
import time
from typing import Optional

log = logging.getLogger(__name__)

DEBOUNCE_MINUTOS = 30
_INITIAL_DELAY   = 10.0

_HERE      = os.path.dirname(os.path.abspath(__file__))
_KOIOS_ROOT = os.path.dirname(os.path.dirname(_HERE))
_HIST_PATH = os.path.join(_KOIOS_ROOT, "database", "historico_backup_prontuario.json")

_instancia: Optional["BackupWatcher"] = None


def _primeiro_backup() -> bool:
    return not os.path.exists(_HIST_PATH)


def notify_db_changed() -> None:
    global _instancia
    if _instancia and _instancia.ativo:
        _instancia._on_mudanca()


class BackupWatcher:

    def __init__(self, debounce_min: int = DEBOUNCE_MINUTOS) -> None:
        self.debounce_seg  = debounce_min * 60
        self.ativo         = False
        self._timer: Optional[threading.Timer] = None
        self._lock         = threading.Lock()
        self._pendente     = False
        self._ultimo_envio = 0.0
        self._callback_ui  = None

    def iniciar(self, callback_ui=None) -> None:
        global _instancia
        _instancia        = self
        self.ativo        = True
        self._callback_ui = callback_ui
        log.info("[Watcher] Iniciado — debounce %d min", self.debounce_seg // 60)

        if _primeiro_backup():
            log.info("[Watcher] Primeiro uso — backup inicial em %ds", int(_INITIAL_DELAY))
            t = threading.Timer(_INITIAL_DELAY, self._executar_primeiro_backup)
            t.daemon = True
            t.start()

    def parar(self) -> None:
        self.ativo = False
        self._cancelar_timer()
        log.info("[Watcher] Parado")

    def _executar_primeiro_backup(self) -> None:
        if not self.ativo:
            return
        self._notificar_ui("Iniciando primeiro backup automático...")

        def _run() -> None:
            try:
                from prontuario.backup.drive_backup import fazer_backup
                ok, msg = fazer_backup(forcar=True)
                self._ultimo_envio = time.time()
                if ok:
                    self._notificar_ui("Primeiro backup concluído!")
                else:
                    self._notificar_ui(f"Primeiro backup falhou: {msg[:60]}")
            except Exception as exc:
                log.exception("[Watcher] Erro no primeiro backup")
                self._notificar_ui(f"Erro no backup: {str(exc)[:60]}")

        threading.Thread(target=_run, daemon=True).start()

    def _on_mudanca(self) -> None:
        with self._lock:
            self._pendente = True
            self._cancelar_timer()
            self._timer = threading.Timer(self.debounce_seg, self._disparar_backup)
            self._timer.daemon = True
            self._timer.start()

    def _disparar_backup(self) -> None:
        if not self.ativo:
            return
        with self._lock:
            if not self._pendente:
                return
            self._pendente = False

        def _run() -> None:
            try:
                from prontuario.backup.drive_backup import fazer_backup
                ok, msg = fazer_backup(forcar=False)
                self._ultimo_envio = time.time()
                if ok:
                    self._notificar_ui(f"Backup automático: {msg}")
                else:
                    self._notificar_ui(f"Backup falhou: {msg[:60]}")
            except Exception as exc:
                log.exception("[Watcher] Erro no backup automático")
                self._notificar_ui(f"Erro no backup: {str(exc)[:60]}")

        threading.Thread(target=_run, daemon=True).start()

    def _cancelar_timer(self) -> None:
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _notificar_ui(self, msg: str) -> None:
        if self._callback_ui:
            try:
                self._callback_ui(msg)
            except Exception:
                pass

    @property
    def status(self) -> str:
        if not self.ativo:
            return "inativo"
        return "pendente" if self._pendente else "ativo"

    @property
    def primeiro_uso(self) -> bool:
        return _primeiro_backup()
