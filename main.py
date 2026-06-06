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


_LOGS_CRASH_PASTA_ID = None   # ID da pasta logs_crash no Drive (configurar se necessario)
_LOGS_CRASH_MAX      = 10


def _exportar_log_crash_drive() -> None:
    """Envia log de crash para Koios/Prontuario/logs_crash e mantem maximo de 10."""
    def _run():
        try:
            if not os.path.exists(_LOG_FILE):
                return
            with open(_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                conteudo = f.read()
            if "CRITICAL" not in conteudo and "ERROR" not in conteudo:
                return
            from backup.db_backup import _obter_token, _drive_upload_arquivo, _rotacionar
            import datetime
            token = _obter_token()
            nome  = f"crash_prontuario_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            _drive_upload_arquivo(token, _LOG_FILE, nome, _LOGS_CRASH_PASTA_ID)
            _rotacionar(token, _LOGS_CRASH_PASTA_ID, _LOGS_CRASH_MAX)
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

    TIMEOUT_DRIVE = 7    # segundos para verificar conexao Drive
    TIMEOUT_RESTORE = 60  # segundos para download do banco

    def _verificar_drive() -> bool:
        """Verifica conexao com Drive (timeout TIMEOUT_DRIVE s). Retorna True se ok."""
        import urllib.request as _ureq
        resultado = [False]
        ev = threading.Event()
        def _check():
            try:
                from shared.auth import _CREDS_PATH
                import json as _j
                with open(_CREDS_PATH, "r", encoding="utf-8") as f:
                    data = _j.load(f)
                token = data.get("token") or data.get("access_token", "")
                req = _ureq.Request(
                    "https://www.googleapis.com/drive/v3/about?fields=user",
                    headers={"Authorization": f"Bearer {token}"},
                )
                with _ureq.urlopen(req, timeout=5) as r:
                    resultado[0] = r.status == 200
            except Exception:
                resultado[0] = False
            finally:
                ev.set()
        threading.Thread(target=_check, daemon=True).start()
        ev.wait(timeout=TIMEOUT_DRIVE)
        return resultado[0]

    def _restaurar_e_abrir():
        """Padrao Koios: verifica Drive, apaga local, restaura, exibe contagem, abre hub."""
        import os as _os, sqlite3 as _sql3, time as _time
        from dados.model_prontuario import DB_PATH
        _log = logging.getLogger(__name__)

        # 1. Verifica Drive antes de apagar banco local
        _set_splash("Verificando Drive...")
        drive_ok = _verificar_drive()

        if not drive_ok:
            if _os.path.exists(DB_PATH):
                _log.warning("Drive indisponivel -- usando banco local existente")
                _set_splash("Offline. Usando dados locais...")
                _time.sleep(1.0)
                try:
                    from dados.model_prontuario import criar_tabelas
                    criar_tabelas()
                except Exception: pass
                _abrir_prontuario()
            else:
                _log.warning("Drive indisponivel e sem banco local -- indo para login")
                _set_splash("Sem conexao. Reconectando...")
                _time.sleep(1.5)
                try:
                    from telas_shared.tela_login import criar_tela_login
                    def _on_login():
                        threading.Thread(target=_restaurar_e_abrir, daemon=True).start()
                    _nav(criar_tela_login(page, on_login_sucesso=_on_login))
                except Exception as ex:
                    import traceback
                    _tela_erro(f"Erro ao abrir login:\n{traceback.format_exc()[-600:]}")
            return

        # 2. Apaga banco local — Drive e sempre autoritativo
        _set_splash("Preparando banco...")
        try:
            if _os.path.exists(DB_PATH):
                _os.remove(DB_PATH)
            _log.info("Banco local removido para restore limpo do Drive")
        except Exception as ex:
            _log.warning("remover banco local (nao critico): %s", ex)

        # 3. Restaura do Drive
        _set_splash("Restaurando do Drive...")
        restaurado = False
        try:
            resultado = [False]
            def _do_restore():
                try:
                    from backup.drive_backup import restaurar_backup_completo
                    ok, _ = restaurar_backup_completo()
                    resultado[0] = ok
                except Exception:
                    resultado[0] = False
            t = threading.Thread(target=_do_restore, daemon=True)
            t.start()
            t.join(timeout=TIMEOUT_RESTORE)
            restaurado = resultado[0]
        except Exception as ex:
            _log.warning("restore startup (nao critico): %s", ex)

        # 4. Exibe contagem de registros restaurados — igual ao Prestanista
        if restaurado:
            _log.info("Banco restaurado do Drive no startup")
            try:
                conn = _sql3.connect(DB_PATH)
                def _cnt(tabela, tem_ativo=True):
                    try:
                        if tem_ativo:
                            return conn.execute(
                                f"SELECT COUNT(*) FROM {tabela} WHERE ativo=1 OR ativo IS NULL"
                            ).fetchone()[0]
                        return conn.execute(
                            f"SELECT COUNT(*) FROM {tabela}"
                        ).fetchone()[0]
                    except Exception:
                        return 0
                n_med  = _cnt("medicos")
                n_cons = _cnt("consultas", tem_ativo=False)
                n_exam = _cnt("exames")
                n_rem  = _cnt("remedios")
                conn.close()
                _set_splash(
                    f"{n_med} medico(s)  |  {n_cons} consulta(s)  |  "
                    f"{n_exam} exame(s)  |  {n_rem} remedio(s)"
                )
                _time.sleep(2.0)
            except Exception as ex:
                _log.warning("contar registros pos-restore: %s", ex)
                _set_splash("Banco atualizado!")
                _time.sleep(0.8)
        else:
            _log.warning("Drive sem backup ou restore falhou -- banco vazio")
            _set_splash("Pronto!")
            _time.sleep(0.2)

        # 5. Aplica migracoes no banco restaurado (ou cria vazio)
        try:
            from dados.model_prontuario import criar_tabelas
            criar_tabelas()
            _log.info("criar_tabelas() aplicado apos restore")
        except Exception as ex:
            _log.warning("criar_tabelas pos-restore (nao critico): %s", ex)

        _abrir_prontuario()

    def _iniciar():
        # Detecta crash da sessao anterior e exporta log para Drive
        if _verificar_crash_anterior():
            logging.getLogger("CRASH").warning(
                "Sessao anterior encerrou abruptamente -- exportando log"
            )
            _exportar_log_crash_drive()
        _marcar_inicio()

        # Verifica sessao
        sessao_ativa = False
        try:
            from shared.auth import verificar_sessao_ativa
            sessao_ativa = verificar_sessao_ativa()
        except Exception:
            pass

        if not sessao_ativa:
            try:
                from telas_shared.tela_login import criar_tela_login
                def _on_login():
                    threading.Thread(target=_restaurar_e_abrir, daemon=True).start()
                _nav(criar_tela_login(page, on_login_sucesso=_on_login))
            except Exception as ex:
                import traceback
                _tela_erro(f"Erro ao abrir login:\n{traceback.format_exc()[-600:]}")
            return

        # Sessao ativa — restaura do Drive (a funcao ja trata offline internamente)
        threading.Thread(target=_restaurar_e_abrir, daemon=True).start()

    threading.Thread(target=_iniciar, daemon=True).start()


ft.app(target=main)
