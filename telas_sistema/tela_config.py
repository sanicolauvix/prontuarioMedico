"""prontuario/telas/tela_config.py — Configurações do Prontuário."""

import threading
import flet as ft

BG   = "#0D1117"
CARD = "#161B22"
BD   = "#21262D"
TXT  = "#E6EDF3"
SEC  = "#8B949E"
MUT  = "#484F58"
AZUL = "#58A6FF"
VERD = "#3FB950"
AMAR = "#D29922"
VERM = "#F85149"


def criar_tela_config(page: ft.Page, voltar_fn=None, aba_inicial: int = 0):
    aba_ativa = [aba_inicial]
    _montado  = [False]

    def _atualizar_ui():
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
        _atualizar_ui()

    def _set_loading(visible: bool) -> None:
        progress.visible = visible
        _atualizar_ui()

    def _carregar_historico() -> None:
        try:
            from prontuario.backup.drive_backup import carregar_historico
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
                historico_col.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.CHECK_CIRCLE, size=14, color=VERD),
                            ft.Text(h.get("data_fmt", "—"), size=12, color=TXT),
                            ft.Text(f"{h.get('enviados', 0)} banco(s)",
                                    size=11, color=SEC),
                        ], spacing=8),
                        bgcolor=CARD,
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        border_radius=8,
                        border=ft.border.all(1, BD),
                    )
                )
        _atualizar_ui()

    def _fazer_backup(e) -> None:
        _set_loading(True)
        _set_status("Fazendo backup...", AZUL)

        def _run() -> None:
            try:
                from prontuario.backup.drive_backup import fazer_backup
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

    def _restaurar(e) -> None:
        def _confirmar(e2) -> None:
            dlg.open = False
            page.update()
            _set_loading(True)
            _set_status("Restaurando backup...", AMAR)

            def _run() -> None:
                try:
                    from prontuario.backup.drive_backup import restaurar_backup_completo
                    ok, msg = restaurar_backup_completo(
                        callback_progresso=lambda m: _set_status(m, AMAR),
                    )
                    _set_status(msg, VERD if ok else VERM)
                except Exception as ex:
                    _set_status(f"Erro: {ex}", VERM)
                finally:
                    _set_loading(False)

            threading.Thread(target=_run, daemon=True).start()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Restaurar Backup?", color=TXT),
            content=ft.Text(
                "O banco local será substituído pelo backup mais recente do Drive.\n"
                "Esta ação não pode ser desfeita.",
                size=13, color=SEC,
            ),
            actions=[
                ft.ElevatedButton(
                    "Cancelar",
                    bgcolor=BD, color=TXT,
                    on_click=lambda e2: (setattr(dlg, "open", False), page.update()),
                ),
                ft.TextButton(
                    "Restaurar",
                    style=ft.ButtonStyle(color=VERM),
                    on_click=_confirmar,
                ),
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # ── Abas ─────────────────────────────────────────────────────
    ABAS = [("Geral", AZUL), ("Backup", VERD)]
    barra_abas    = ft.Row(spacing=0)
    area_conteudo = ft.ListView(spacing=12, padding=ft.padding.all(16), expand=True)

    def _rebuild_abas():
        barra_abas.controls.clear()
        for i, (label, cor) in enumerate(ABAS):
            ativa = aba_ativa[0] == i
            barra_abas.controls.append(ft.Container(
                content=ft.Text(
                    label, size=13,
                    color=cor if ativa else SEC,
                    weight=ft.FontWeight.W_600 if ativa else ft.FontWeight.W_400,
                ),
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                border=ft.border.only(
                    bottom=ft.BorderSide(2, cor if ativa else "transparent")
                ),
                on_click=lambda e, idx=i: _trocar_aba(idx),
                ink=True,
            ))

    def _conteudo_geral():
        try:
            from prontuario.dados.model_prontuario import carregar_perfil
            p     = carregar_perfil() or {}
            nome  = p.get("nome",  "—")
            email = p.get("email", "—")
        except Exception:
            nome, email = "—", "—"

        try:
            from prontuario.backup import backup_watcher as _bw
            bk_ativo  = bool(_bw._instancia and _bw._instancia.ativo)
            bk_status = "Ativo" if bk_ativo else "Inativo"
            bk_cor    = VERD if bk_ativo else SEC
        except Exception:
            bk_status, bk_cor = "Inativo", SEC

        def _row_info(label, valor):
            return ft.Container(
                content=ft.Row([
                    ft.Text(label, size=12, color=SEC, expand=True),
                    ft.Text(valor, size=12, color=TXT,
                            weight=ft.FontWeight.W_500),
                ], spacing=8),
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                border=ft.Border(bottom=ft.BorderSide(1, BD)),
            )

        return [
            ft.Container(
                content=ft.Column([
                    ft.Text("PERFIL", size=10, color=SEC,
                            weight=ft.FontWeight.W_700),
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
            ft.Container(
                content=ft.Column([
                    ft.Text("BACKUP AUTOMÁTICO", size=10, color=SEC,
                            weight=ft.FontWeight.W_700),
                    ft.Container(height=4),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.CLOUD_SYNC, size=16, color=bk_cor),
                            ft.Text("Status", size=12, color=SEC, expand=True),
                            ft.Text(bk_status, size=12, color=bk_cor,
                                    weight=ft.FontWeight.W_500),
                        ], spacing=10),
                        bgcolor=CARD, border_radius=10,
                        border=ft.border.all(1, BD),
                        padding=ft.padding.symmetric(horizontal=16, vertical=12),
                    ),
                    ft.Text(
                        "Backup automático ocorre 30 min após mudanças no banco.",
                        size=10, color=MUT,
                    ),
                ], spacing=6),
            ),
        ]

    def _conteudo_backup():
        return [
            ft.Container(
                content=ft.Column([
                    ft.Text("AÇÕES", size=10, color=SEC,
                            weight=ft.FontWeight.W_700),
                    ft.Container(height=8),
                    ft.Row([
                        ft.ElevatedButton(
                            "Fazer Backup Agora",
                            icon=ft.Icons.CLOUD_UPLOAD,
                            bgcolor=AZUL, color=BG,
                            on_click=_fazer_backup,
                            expand=True,
                        ),
                        ft.OutlinedButton(
                            "Restaurar",
                            icon=ft.Icons.CLOUD_DOWNLOAD,
                            style=ft.ButtonStyle(
                                color=AMAR,
                                side=ft.BorderSide(1, AMAR),
                            ),
                            on_click=_restaurar,
                            expand=True,
                        ),
                    ], spacing=10),
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
                    ft.Text("ÚLTIMOS BACKUPS", size=10, color=SEC,
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
                    "  prontuario_db/ · koios_db/ (máx 5 versões)",
                    size=10, color=MUT,
                ),
                bgcolor=CARD, padding=12, border_radius=8,
                border=ft.border.all(1, BD),
            ),
        ]

    def _rebuild_conteudo():
        area_conteudo.controls.clear()
        for c in (_conteudo_geral() if aba_ativa[0] == 0 else _conteudo_backup()):
            area_conteudo.controls.append(c)

    def _trocar_aba(idx):
        aba_ativa[0] = idx
        _rebuild_abas()
        _rebuild_conteudo()
        _atualizar_ui()

    # ── Header ────────────────────────────────────────────────────
    header = ft.Container(
        content=ft.Row([
            ft.TextButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.ARROW_BACK, size=16, color=SEC),
                    ft.Text("Voltar", size=13, color=SEC),
                ], spacing=4, tight=True),
                on_click=lambda e: voltar_fn() if voltar_fn else None,
            ),
            ft.Row([
                ft.Icon(ft.Icons.SETTINGS, size=18, color=AZUL),
                ft.Text("Configurações", size=16,
                        weight=ft.FontWeight.W_700, color=TXT),
            ], spacing=8, tight=True),
            ft.Container(expand=True),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
    )

    _rebuild_abas()
    _rebuild_conteudo()
    _carregar_historico()

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
