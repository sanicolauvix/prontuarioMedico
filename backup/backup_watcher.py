# -*- coding: utf-8 -*-
# SHARED | backup/backup_watcher.py -- gerenciado por flet_shared/sync_shared.py
# --- SHARED PARAMS ---
_INITIAL_DELAY = 10.0
# --- END SHARED PARAMS ---
"""
backup/backup_watcher.py
Observador automatico de mudancas no banco de dados.

Fluxo normal (apos primeiro backup):
    1. notify_db_changed() marca "mudanca pendente"
    2. Timer de DEBOUNCE_MINUTOS e (re)iniciado a cada chamada
    3. Quando o timer dispara: houve_mudanca() -> MD5 mudou? -> upload

Fluxo primeira execucao (sem historico):
    1. iniciar() detecta que nao existe historico_backup.json
    2. Dispara backup imediato em background (sem esperar debounce)
    3. A partir dai, fluxo normal

Como integrar:
    No main.py apos login:
        from backup.backup_watcher import BackupWatcher
        watcher = BackupWatcher()
        watcher.iniciar()

    Em qualquer funcao de banco que altera dados (model.py):
        from backup.backup_watcher import notify_db_changed
        notify_db_changed()

    Para parar (ao fechar o app):
        watcher.parar()
"""

import logging
import os
import threading
import time
from typing import Optional

log = logging.getLogger(__name__)

DEBOUNCE_MINUTOS = 30

_instancia: Optional["BackupWatcher"] = None

_HERE      = os.path.dirname(os.path.abspath(__file__))
_ROOT      = os.path.dirname(_HERE)
_HIST_PATH = os.path.join(_ROOT, "database", "historico_backup.json")


def _primeiro_backup() -> bool:
    """True se ainda nao existe nenhum backup registrado."""
    return not os.path.exists(_HIST_PATH)


def notify_db_changed() -> None:
    """
    Chamado sempre que o banco e alterado (INSERT/UPDATE/DELETE).
    Reinicia o timer de debounce.
    """
    global _instancia
    if _instancia and _instancia.ativo:
        _instancia._on_mudanca()


class BackupWatcher:
    """
    Observador de mudancas com debounce configuravel.
    Na primeira execucao (sem historico), faz backup imediato.
    Thread-safe.
    """

    def __init__(self, debounce_min: int = DEBOUNCE_MINUTOS) -> None:
        self.debounce_seg  = debounce_min * 60
        self.ativo         = False
        self._timer: Optional[threading.Timer] = None
        self._lock         = threading.Lock()
        self._pendente     = False
        self._ultimo_envio = 0.0
        self._callback_ui  = None
        self._timer_start  = 0.0

    # -- Ciclo de vida ──────────────────────────────────────────────────────────

    def iniciar(self, callback_ui=None) -> None:
        """
        Inicia o watcher.

        Se nao existir historico de backup (primeira execucao),
        agenda um backup imediato -- tempo suficiente para a UI
        terminar de montar sem bloquear o startup.

        callback_ui: callable(msg: str) -- notificacao opcional para a UI.
        """
        global _instancia
        _instancia        = self
        self.ativo        = True
        self._callback_ui = callback_ui
        log.info("[Watcher] Iniciado -- debounce %d min", self.debounce_seg // 60)

        if _primeiro_backup():
            log.info("[Watcher] Primeiro uso -- backup inicial em %ds",
                     int(_INITIAL_DELAY))
            self._agendar_primeiro_backup()

    def parar(self) -> None:
        """Para o watcher e cancela qualquer timer pendente."""
        self.ativo = False
        self._cancelar_timer()
        log.info("[Watcher] Parado")

    # -- Primeiro backup ────────────────────────────────────────────────────────

    def _agendar_primeiro_backup(self) -> None:
        """Agenda backup imediato com delay configuravel para nao travar o startup."""
        t = threading.Timer(_INITIAL_DELAY, self._executar_primeiro_backup)
        t.daemon = True
        t.start()

    def _executar_primeiro_backup(self) -> None:
        """Executa o backup inicial -- forcado, ignora MD5 (nao ha referencia)."""
        if not self.ativo:
            return
        log.info("[Watcher] Executando backup inicial (primeira execucao)...")

        def _run() -> None:
            self._notificar_ui({"fase": "executando"})
            try:
                from backup.drive_backup import fazer_backup
                ok, msg = fazer_backup(
                    forcar=True,
                    callback_progresso=None,
                )
                self._ultimo_envio = time.time()
                if ok:
                    log.info("[Watcher] Primeiro backup OK: %s", msg)
                    self._notificar_ui({"fase": "concluido", "msg": msg})
                else:
                    log.warning("[Watcher] Primeiro backup falhou: %s", msg)
                    self._notificar_ui({"fase": "erro", "msg": msg[:60]})
            except Exception as exc:
                log.exception("[Watcher] Erro no primeiro backup: %s", exc)
                self._notificar_ui({"fase": "erro", "msg": str(exc)[:60]})

        threading.Thread(target=_run, daemon=True).start()

    # -- Deteccao de mudanca (fluxo normal) ──────────────────────────────────────

    def _on_mudanca(self) -> None:
        """Reinicia o timer de debounce a cada alteracao no banco."""
        with self._lock:
            self._pendente = True
            self._timer_start = time.time()
            self._cancelar_timer()
            self._timer = threading.Timer(
                self.debounce_seg, self._disparar_backup
            )
            self._timer.daemon = True
            self._timer.start()
            log.debug(
                "[Watcher] Mudanca detectada -- backup em %d min",
                self.debounce_seg // 60,
            )
        self._notificar_ui({"fase": "pendente", "proximo_em": self.debounce_seg})

    # -- Disparo do backup (fluxo normal) ────────────────────────────────────────

    def _disparar_backup(self) -> None:
        """Timer expirou -- verifica MD5 e envia se necessario."""
        if not self.ativo:
            return
        with self._lock:
            if not self._pendente:
                return
            self._pendente = False

        log.info("[Watcher] Disparando backup automatico...")

        def _run() -> None:
            self._notificar_ui({"fase": "executando"})
            try:
                from backup.drive_backup import fazer_backup
                ok, msg = fazer_backup(
                    forcar=False,
                    callback_progresso=None,
                )
                self._ultimo_envio = time.time()
                if ok:
                    log.info("[Watcher] Backup automatico OK: %s", msg)
                    self._notificar_ui({"fase": "concluido", "msg": msg})
                else:
                    log.warning("[Watcher] Backup automatico falhou: %s", msg)
                    self._notificar_ui({"fase": "erro", "msg": msg[:60]})
            except Exception as exc:
                log.exception("[Watcher] Erro no backup automatico: %s", exc)
                self._notificar_ui({"fase": "erro", "msg": str(exc)[:60]})

        threading.Thread(target=_run, daemon=True).start()

    # -- Helpers ────────────────────────────────────────────────────────────────

    def _cancelar_timer(self) -> None:
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _notificar_ui(self, msg) -> None:
        if self._callback_ui:
            try:
                self._callback_ui(msg)
            except Exception:
                pass

    # -- Propriedades de status ──────────────────────────────────────────────────

    @property
    def proximo_backup_em(self) -> str:
        """Tempo estimado ate o proximo backup. Ex: '28min 45s', '45s', '--'."""
        if not self._pendente or not self._timer:
            return "--"
        try:
            elapsed = time.time() - self._timer_start
            restante = max(0, int(self.debounce_seg - elapsed))
            if restante < 60:
                return f"{restante}s"
            return f"{restante // 60}min {restante % 60:02d}s"
        except Exception:
            return "em breve"

    @property
    def status(self) -> str:
        """'ativo' | 'pendente' | 'inativo'"""
        if not self.ativo:
            return "inativo"
        if self._pendente:
            return "pendente"
        return "ativo"

    @property
    def primeiro_uso(self) -> bool:
        """True se ainda nao existe historico de backup."""
        return _primeiro_backup()
