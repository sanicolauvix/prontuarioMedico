# -*- coding: utf-8 -*-
# Prontuario Medico | main.py -- entry point standalone (flet build apk)
import flet as ft
import os
import sys
import threading
import logging
import logging.handlers

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Logging rotativo: captura erros de execucao brusca e crashes
_LOG_DIR  = os.path.join(_ROOT, "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_FILE = os.path.join(_LOG_DIR, "prontuario_runtime.log")

_fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
_fh  = logging.handlers.RotatingFileHandler(
    _LOG_FILE, maxBytes=500_000, backupCount=3, encoding="utf-8"
)
_fh.setFormatter(_fmt)
_sh = logging.StreamHandler()
_sh.setFormatter(_fmt)
_root_log = logging.getLogger()
_root_log.setLevel(logging.DEBUG)
_root_log.addHandler(_fh)
_root_log.addHandler(_sh)

_SENTINELA = os.path.join(_LOG_DIR, ".app_running")


def _excepthook(exc_type, exc_value, exc_tb):
    import traceback as _tb
    logging.getLogger("CRASH").critical(
        "UNCAUGHT EXCEPTION:\n%s",
        "".join(_tb.format_exception(exc_type, exc_value, exc_tb)),
    )

sys.excepthook = _excepthook


def _verificar_crash_anterior() -> bool:
    """True se o app nao encerrou normalmente na sessao anterior."""
    return os.path.exists(_SENTINELA)


def _marcar_inicio() -> None:
    """Cria sentinela que indica que o app esta rodando."""
    try:
        with open(_SENTINELA, "w", encoding="utf-8") as f:
            import datetime
            f.write(datetime.datetime.now().isoformat())
    except Exception:
        pass


def _marcar_encerramento_normal() -> None:
    """Remove sentinela ao encerrar normalmente."""
    try:
        if os.path.exists(_SENTINELA):
            os.remove(_SENTINELA)
    except Exception:
        pass


def _exportar_log_crash_drive() -> None:
    """Envia o log de crash para a pasta Koios_Prontuario/logs_crash no Drive."""
    def _run():
        try:
            if not os.path.exists(_LOG_FILE):
                return
            with open(_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                conteudo = f.read()
            if "CRITICAL" not in conteudo and "ERROR" not in conteudo:
                return
            from backup.db_backup import _obter_token, _garantir_pasta, _drive_upload_arquivo
            import datetime
            token     = _obter_token()
            pasta_raiz = _garantir_pasta(token, "Koios_Prontuario")
            pasta_log  = _garantir_pasta(token, "logs_crash", pasta_raiz)
            nome = f"crash_prontuario_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            _drive_upload_arquivo(token, _LOG_FILE, nome, pasta_log)
            logging.getLogger("CRASH").info("Log de crash exportado: %s", nome)
        except Exception as ex:
            logging.getLogger("CRASH").warning("Nao foi possivel exportar log: %s", ex)
    threading.Thread(target=_run, daemon=True).start()


_marcar_inicio()

ACENTO = "#BC8CFF"
BG     = "#0D1117"
TXT    = "#E6EDF3"
MUT    = "#8B949E"

# Flag de modulo: persiste entre reconexoes do WebSocket (app voltando do background)
_app_ja_iniciou = [False]


def main(page: ft.Page):
    page.title      = "Prontuario Medico"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = BG
    page.padding    = 0
    try:
        page.window.width  = 420
        page.window.height = 820
    except Exception:
        pass

    def _nav(tela: ft.Control) -> None:
        page.controls.clear()
        page.controls.append(tela)
        try:
            page.update()
        except Exception:
            pass

    def _tela_erro(msg: str):
        _nav(ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Container(expand=True),
                ft.Row([ft.Icon("error_outline", color="#F85149", size=48)],
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=12),
                ft.Row([ft.Text(msg, size=13, color="#F85149",
                                text_align=ft.TextAlign.CENTER)],
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(expand=True),
            ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=32,
        ))

    def _iniciar_watcher():
        try:
            from backup import backup_watcher as _bw
            if _bw._instancia and _bw._instancia.ativo:
                return
            from backup.backup_watcher import BackupWatcher
            w = BackupWatcher()
            w.iniciar(
                callback_ui=lambda m: page.pubsub.send_all_on_topic(
                    "_backup_status",
                    m if isinstance(m, dict) else {"fase": "msg", "msg": m}
                )
            )
        except Exception:
            pass

    def _abrir_prontuario():
        _app_ja_iniciou[0] = True
        _iniciar_watcher()
        try:
            from app import criar_tela_prontuario
            _nav(criar_tela_prontuario(page, voltar_fn=None))
        except Exception as ex:
            import traceback
            _tela_erro(f"Erro ao abrir prontuario:\n{traceback.format_exc()[-400:]}")

    # Reconexao apos background: pular splash, ir direto sem checar sessao
    # (verifica ANTES de mostrar qualquer tela para evitar flash do splash)
    if _app_ja_iniciou[0]:
        _abrir_prontuario()
        return

    _splash_status = ft.Text("Iniciando...", size=13, color=MUT)

    _nav(ft.Container(
        bgcolor=BG, expand=True,
        content=ft.Column([
            ft.Container(expand=True),
            ft.Row([ft.ProgressRing(color=ACENTO)],
                   alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=12),
            ft.Row([_splash_status],
                   alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(expand=True),
        ], expand=True),
    ))

    def _set_splash(msg: str) -> None:
        _splash_status.value = msg
        try:
            page.update()
        except Exception:
            pass

    def _iniciar():
        # Detecta crash da sessao anterior e exporta log para Drive
        if _verificar_crash_anterior():
            logging.getLogger("CRASH").warning(
                "Sessao anterior encerrou abruptamente -- exportando log"
            )
            _exportar_log_crash_drive()
        # Recria sentinela para esta sessao
        _marcar_inicio()

        try:
            from shared.auth import verificar_sessao_ativa
            if verificar_sessao_ativa():
                try:
                    from backup.drive_backup import sincronizar_ao_iniciar
                    sincronizar_ao_iniciar(callback_progresso=_set_splash)
                except Exception:
                    pass
                _abrir_prontuario()
                return
        except Exception:
            pass

        try:
            from telas_shared.tela_login import criar_tela_login

            def _on_login():
                try:
                    from backup.drive_backup import sincronizar_ao_iniciar
                    sincronizar_ao_iniciar()
                except Exception:
                    pass
                _abrir_prontuario()

            _nav(criar_tela_login(page, on_login_sucesso=_on_login))
        except Exception as ex:
            import traceback
            _tela_erro(f"Erro ao abrir login:\n{traceback.format_exc()[-600:]}")

    threading.Thread(target=_iniciar, daemon=True).start()


ft.app(target=main)
