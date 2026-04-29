# -*- coding: utf-8 -*-
# Prontuario Medico | telas_sistema/tela_config.py
import threading
import flet as ft

BG   = "#0D1117"
CARD = "#161B22"
BD   = "#21262D"
BD2  = "#30363D"
TXT  = "#E6EDF3"
SEC  = "#8B949E"
MUT  = "#484F58"
AZUL = "#58A6FF"
VERD = "#3FB950"
AMAR = "#D29922"
VERM = "#F85149"
ROXO = "#BC8CFF"


def criar_tela_config(page: ft.Page, voltar_fn=None, aba_inicial: int = 0):
    aba_ativa = [aba_inicial]
    _montado  = [False]

    def _ui():
        if _montado[0]:
            try:
                page.update()
            except Exception:
                pass

    # ── Widgets de backup ─────────────────────────────────────────
    status_txt    = ft.Text("", size=13, color=SEC)
    progress      = ft.ProgressBar(visible=False, color=AZUL, bgcolor=BD)
    historico_col = ft.Column([], spacing=6)

    def _set_status(msg: str, cor: str = SEC) -> None:
        status_txt.value = msg
        status_txt.color = cor
        _ui()

    def _set_loading(v: bool) -> None:
        progress.visible = v
        _ui()

    def _carregar_historico() -> None:
        try:
            from backup.drive_backup import carregar_historico
            hist = carregar_historico()
        except Exception:
            hist = []
        historico_col.controls.clear()
        if not hist:
            historico_col.controls.append(
                ft.Text("Nenhum backup registrado.", size=12, color=MUT)
            )
        else:
            for h in hist:
                historico_col.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Icon("check_circle", size=14, color=VERD),
                        ft.Text(h.get("data_fmt", "—"), size=12, color=TXT),
                        ft.Text(f"{h.get('enviados', 0)} banco(s)", size=11, color=SEC),
                    ], spacing=8),
                    bgcolor=CARD,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    border_radius=8,
                    border=ft.border.all(1, BD),
                ))
        _ui()

    def _fazer_backup(e) -> None:
        _set_loading(True)
        _set_status("Fazendo backup...", AZUL)

        def _run() -> None:
            try:
                from backup.drive_backup import fazer_backup
                ok, msg = fazer_backup(
                    forcar=True,
                    callback_progresso=lambda m: _set_status(m, AZUL),
                )
                _set_status(msg, VERD if ok else VERM)
                if ok:
                    _carregar_historico()
            except Exception as ex:
                _set_status(f"Erro: {ex}", VERM)
            finally:
                _set_loading(False)

        threading.Thread(target=_run, daemon=True).start()

    def _confirmar_restaurar():
        ref = [None]

        def _fechar(e=None):
            if ref[0] in page.overlay:
                page.overlay.remove(ref[0])
            _ui()

        def _ok(e):
            _fechar()
            _set_loading(True)
            _set_status("Restaurando backup...", AMAR)

            def _run() -> None:
                try:
                    from backup.drive_backup import restaurar_backup_completo
                    ok, msg = restaurar_backup_completo(
                        callback_progresso=lambda m: _set_status(m, AMAR),
                    )
                    _set_status(msg, VERD if ok else VERM)
                except Exception as ex:
                    _set_status(f"Erro: {ex}", VERM)
                finally:
                    _set_loading(False)

            threading.Thread(target=_run, daemon=True).start()

        btn_cancel = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            border_radius=8, bgcolor=BD, ink=True,
        )
        btn_cancel.on_click = _fechar

        btn_ok = ft.Container(
            content=ft.Text("Restaurar", size=13, color=VERM, weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            border_radius=8,
            bgcolor=VERM + "22",
            border=ft.border.all(1, VERM + "66"),
            ink=True,
        )
        btn_ok.on_click = _ok

        ref[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Restaurar Backup?", size=15, color=TXT,
                            weight=ft.FontWeight.W_700, text_align="center"),
                    ft.Container(height=8),
                    ft.Text(
                        "O banco local sera substituido pelo backup mais recente do Drive.\n"
                        "Esta acao nao pode ser desfeita.",
                        size=13, color=SEC, text_align="center",
                    ),
                    ft.Container(height=20),
                    ft.Row([btn_cancel, btn_ok],
                           alignment=ft.MainAxisAlignment.CENTER, spacing=12),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                bgcolor=CARD, border_radius=14, padding=ft.padding.all(24), width=300,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.alignment.Alignment(0, 0),
        )
        ref[0].on_click = _fechar
        page.overlay.append(ref[0])
        _ui()

    # ══════════════════════════════════════════════════════════════
    # ABA GERAL
    # ══════════════════════════════════════════════════════════════
    def _conteudo_geral():
        # ── Perfil ────────────────────────────────────────────────
        try:
            from dados.model_prontuario import carregar_perfil
            p     = carregar_perfil() or {}
            nome  = p.get("nome",  "—")
            email = p.get("email", "—")
        except Exception:
            nome, email = "—", "—"

        # ── Backup watcher ────────────────────────────────────────
        try:
            from backup import backup_watcher as _bw
            bk_ativo  = bool(_bw._instancia and _bw._instancia.ativo)
            bk_status = "Ativo" if bk_ativo else "Inativo"
            bk_cor    = VERD if bk_ativo else SEC
        except Exception:
            bk_status, bk_cor = "Inativo", SEC

        # ── API key Claudia ───────────────────────────────────────
        try:
            from dados.model_prontuario import get_config
            _key_salva = get_config("anthropic_api_key", "")
        except Exception:
            _key_salva = ""

        _key_salva_ok = len(_key_salva) > 10

        def _row_info(label, valor):
            return ft.Container(
                content=ft.Row([
                    ft.Text(label, size=12, color=SEC, expand=True),
                    ft.Text(valor, size=12, color=TXT, weight=ft.FontWeight.W_500),
                ], spacing=8),
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                border=ft.Border(bottom=ft.BorderSide(1, BD)),
            )

        # Campo da API key
        f_key = ft.TextField(
            label="Chave da API Anthropic",
            hint_text="sk-ant-api03-...",
            password=True,
            can_reveal_password=True,
            value=_key_salva if _key_salva_ok else "",
            bgcolor=CARD,
            border_color=BD2,
            focused_border_color=ROXO,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            expand=True,
        )

        _feedback_key = ft.Text(
            ("Chave salva." if _key_salva_ok else "Nenhuma chave configurada."),
            size=11,
            color=(VERD if _key_salva_ok else MUT),
        )

        def _salvar_key(e):
            val = (f_key.value or "").strip()
            if not val:
                _feedback_key.value = "Digite a chave antes de salvar."
                _feedback_key.color = VERM
                _ui()
                return
            try:
                from dados.model_prontuario import set_config
                set_config("anthropic_api_key", val)
                import os
                os.environ["ANTHROPIC_API_KEY"] = val
                _feedback_key.value = "Chave salva com sucesso."
                _feedback_key.color = VERD
            except Exception as ex:
                _feedback_key.value = f"Erro: {ex}"
                _feedback_key.color = VERM
            _ui()

        def _limpar_key(e):
            try:
                from dados.model_prontuario import set_config
                set_config("anthropic_api_key", "")
                import os
                os.environ.pop("ANTHROPIC_API_KEY", None)
                f_key.value = ""
                _feedback_key.value = "Chave removida."
                _feedback_key.color = MUT
            except Exception as ex:
                _feedback_key.value = f"Erro: {ex}"
                _feedback_key.color = VERM
            _ui()

        btn_salvar_key = ft.Container(
            content=ft.Text("Salvar", size=12, color=BG, weight=ft.FontWeight.W_600),
            bgcolor=ROXO, border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
        )
        btn_salvar_key.on_click = _salvar_key

        btn_limpar_key = ft.Container(
            content=ft.Text("Remover", size=12, color=VERM),
            bgcolor=VERM + "18",
            border=ft.border.all(1, VERM + "55"),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
        )
        btn_limpar_key.on_click = _limpar_key

        return [
            # ── Perfil ────────────────────────────────────────────
            ft.Container(
                content=ft.Column([
                    ft.Text("PERFIL", size=10, color=SEC, weight=ft.FontWeight.W_700),
                    ft.Container(height=4),
                    ft.Container(
                        content=ft.Column([
                            _row_info("Nome",   nome),
                            _row_info("E-mail", email),
                        ], spacing=0),
                        bgcolor=CARD, border_radius=10,
                        border=ft.border.all(1, BD),
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                ], spacing=6),
            ),
            # ── Backup automatico ──────────────────────────────────
            ft.Container(
                content=ft.Column([
                    ft.Text("BACKUP AUTOMATICO", size=10, color=SEC,
                            weight=ft.FontWeight.W_700),
                    ft.Container(height=4),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon("cloud_sync", size=16, color=bk_cor),
                            ft.Text("Status", size=12, color=SEC, expand=True),
                            ft.Text(bk_status, size=12, color=bk_cor,
                                    weight=ft.FontWeight.W_500),
                        ], spacing=10),
                        bgcolor=CARD, border_radius=10,
                        border=ft.border.all(1, BD),
                        padding=ft.padding.symmetric(horizontal=16, vertical=12),
                    ),
                    ft.Text(
                        "Backup automatico ocorre 30 min apos mudancas no banco.",
                        size=10, color=MUT,
                    ),
                ], spacing=6),
            ),
            # ── Claudia IA ────────────────────────────────────────
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("psychology_rounded", size=12, color=ROXO),
                        ft.Text("CLAUDIA — IA", size=10, color=ROXO,
                                weight=ft.FontWeight.W_700),
                    ], spacing=6),
                    ft.Container(height=4),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(
                                "Chave da API Anthropic para analises, graficos e chat com a Claudia.",
                                size=11, color=SEC,
                            ),
                            ft.Container(height=8),
                            ft.Row([f_key, ft.Container(width=8), btn_salvar_key],
                                   alignment=ft.MainAxisAlignment.START),
                            ft.Container(height=6),
                            ft.Row([
                                _feedback_key,
                                ft.Container(expand=True),
                                btn_limpar_key,
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Container(height=4),
                            ft.Text(
                                "A chave fica salva localmente no banco de dados.\n"
                                "Nunca compartilhada com terceiros.",
                                size=10, color=MUT,
                            ),
                        ], spacing=0),
                        bgcolor=CARD, border_radius=10,
                        border=ft.border.all(1, ROXO + "44"),
                        padding=ft.padding.all(16),
                    ),
                ], spacing=6),
            ),
        ]

    # ══════════════════════════════════════════════════════════════
    # ABA BACKUP
    # ══════════════════════════════════════════════════════════════
    def _conteudo_backup():
        btn_backup = ft.Container(
            content=ft.Row([
                ft.Icon("cloud_upload", size=14, color=BG),
                ft.Text("Fazer Backup Agora", size=13, color=BG,
                        weight=ft.FontWeight.W_600),
            ], spacing=6, tight=True),
            bgcolor=AZUL, border_radius=8, ink=True, expand=True,
            padding=ft.padding.symmetric(horizontal=12, vertical=12),
        )
        btn_backup.on_click = _fazer_backup

        btn_restaurar = ft.Container(
            content=ft.Row([
                ft.Icon("cloud_download", size=14, color=AMAR),
                ft.Text("Restaurar", size=13, color=AMAR),
            ], spacing=6, tight=True),
            bgcolor=AMAR + "18",
            border=ft.border.all(1, AMAR + "66"),
            border_radius=8, ink=True, expand=True,
            padding=ft.padding.symmetric(horizontal=12, vertical=12),
        )
        btn_restaurar.on_click = lambda e: _confirmar_restaurar()

        return [
            ft.Container(
                content=ft.Column([
                    ft.Text("ACOES", size=10, color=SEC, weight=ft.FontWeight.W_700),
                    ft.Container(height=8),
                    ft.Row([btn_backup, btn_restaurar], spacing=10),
                    ft.Container(height=8),
                    progress,
                    ft.Container(height=4),
                    status_txt,
                ]),
                bgcolor=CARD, padding=16, border_radius=10,
                border=ft.border.all(1, BD),
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("ULTIMOS BACKUPS", size=10, color=SEC,
                            weight=ft.FontWeight.W_700),
                    ft.Container(height=8),
                    historico_col,
                ]),
                bgcolor=CARD, padding=16, border_radius=10,
                border=ft.border.all(1, BD),
            ),
            ft.Container(
                content=ft.Text(
                    "Backups em: Google Drive / Koios_Prontuario/\n"
                    "  prontuario_db/ · koios_db/ (max 5 versoes)",
                    size=10, color=MUT,
                ),
                bgcolor=CARD, padding=12, border_radius=8,
                border=ft.border.all(1, BD),
            ),
        ]

    # ══════════════════════════════════════════════════════════════
    # TABS
    # ══════════════════════════════════════════════════════════════
    ABAS = [("Geral", AZUL), ("Backup", VERD)]
    barra_abas    = ft.Row(spacing=0)
    area_conteudo = ft.ListView(spacing=12, padding=ft.padding.all(16), expand=True)

    def _rebuild_abas():
        barra_abas.controls.clear()
        for i, (label, cor) in enumerate(ABAS):
            ativa = aba_ativa[0] == i
            tab = ft.Container(
                content=ft.Text(
                    label, size=13,
                    color=cor if ativa else SEC,
                    weight=ft.FontWeight.W_600 if ativa else ft.FontWeight.W_400,
                ),
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                border=ft.border.only(bottom=ft.BorderSide(2, cor if ativa else "transparent")),
                ink=True,
            )
            tab.on_click = lambda e, idx=i: _trocar_aba(idx)
            barra_abas.controls.append(tab)

    def _rebuild_conteudo():
        area_conteudo.controls.clear()
        items = _conteudo_geral() if aba_ativa[0] == 0 else _conteudo_backup()
        for c in items:
            area_conteudo.controls.append(c)

    def _trocar_aba(idx):
        aba_ativa[0] = idx
        _rebuild_abas()
        _rebuild_conteudo()
        _ui()

    # ── Header ────────────────────────────────────────────────────
    btn_voltar = ft.Container(
        content=ft.Row([
            ft.Icon("arrow_back_rounded", size=16, color=SEC),
            ft.Text("Voltar", size=13, color=SEC),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        border_radius=8, ink=True,
    )
    btn_voltar.on_click = lambda e: voltar_fn() if voltar_fn else None

    header = ft.Container(
        content=ft.Row([
            btn_voltar,
            ft.Row([
                ft.Icon("settings_rounded", size=18, color=AZUL),
                ft.Text("Configuracoes", size=16, weight=ft.FontWeight.W_700, color=TXT),
            ], spacing=8, tight=True),
            ft.Container(expand=True),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
    )

    _rebuild_abas()
    _rebuild_conteudo()
    threading.Thread(target=_carregar_historico, daemon=True).start()

    corpo = ft.Column([
        header,
        ft.Container(
            content=barra_abas,
            bgcolor=CARD,
            border=ft.Border(bottom=ft.BorderSide(1, BD)),
        ),
        area_conteudo,
    ], spacing=0, expand=True)

    wrapper = ft.Column(expand=True)
    wrapper.controls.append(ft.Container(bgcolor=BG, expand=True, content=corpo))
    _montado[0] = True
    return wrapper
