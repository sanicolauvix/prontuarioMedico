"""
prontuario/telas/tela_backup.py
Tela de Backup & Restore — Google Drive.
"""

import threading
import flet as ft


BG   = "#0D1117"
CARD = "#161B22"
BD   = "#21262D"
TXT  = "#E6EDF3"
SEC  = "#8B949E"
MUT  = "#484F58"
AZUL = "#58A6FF"
VERDE = "#3FB950"
ERRO  = "#F85149"
AMARELO = "#D29922"


def criar_tela_backup(page: ft.Page, voltar_fn=None):

    # ── Estado ────────────────────────────────────────────────
    status_txt  = ft.Text("", size=13, color=SEC)
    progress    = ft.ProgressBar(visible=False, color=AZUL, bgcolor=BD)
    historico_col = ft.Column([], spacing=6)

    def _set_status(msg: str, cor: str = SEC) -> None:
        status_txt.value = msg
        status_txt.color = cor
        page.update()

    def _set_loading(visible: bool) -> None:
        progress.visible = visible
        page.update()

    # ── Histórico ─────────────────────────────────────────────
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
                            ft.Icon(ft.Icons.CHECK_CIRCLE, size=14, color=VERDE),
                            ft.Text(h.get("data_fmt", "—"), size=12, color=TXT),
                            ft.Text(
                                f"{h.get('enviados', 0)} banco(s)",
                                size=11, color=SEC,
                            ),
                        ], spacing=8),
                        bgcolor=CARD,
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        border_radius=8,
                        border=ft.border.all(1, BD),
                    )
                )
        page.update()

    # ── Ações ─────────────────────────────────────────────────
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
                _set_status(msg, VERDE if ok else ERRO)
                if ok:
                    _carregar_historico()
            except Exception as ex:
                _set_status(f"Erro: {ex}", ERRO)
            finally:
                _set_loading(False)

        threading.Thread(target=_run, daemon=True).start()

    def _restaurar(e) -> None:
        def _confirmar(e2) -> None:
            dlg.open = False
            page.update()
            _set_loading(True)
            _set_status("Restaurando backup...", AMARELO)

            def _run() -> None:
                try:
                    from prontuario.backup.drive_backup import restaurar_backup_completo
                    ok, msg = restaurar_backup_completo(
                        callback_progresso=lambda m: _set_status(m, AMARELO),
                    )
                    _set_status(msg, VERDE if ok else ERRO)
                except Exception as ex:
                    _set_status(f"Erro: {ex}", ERRO)
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
                ft.TextButton("Cancelar", on_click=lambda e2: (setattr(dlg, "open", False), page.update())),
                ft.ElevatedButton(
                    "Restaurar",
                    bgcolor=ERRO, color=TXT,
                    on_click=_confirmar,
                ),
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # ── Build da UI ───────────────────────────────────────────
    _carregar_historico()

    header = ft.Container(
        content=ft.Row([
            ft.TextButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.ARROW_BACK, size=14, color=SEC),
                    ft.Text("Voltar", size=12, color=SEC),
                ], spacing=4, tight=True),
                on_click=lambda e: voltar_fn() if voltar_fn else None,
            ),
            ft.Row([
                ft.Icon(ft.Icons.BACKUP, size=18, color=AZUL),
                ft.Text("Backup & Restore", size=15,
                        weight=ft.FontWeight.W_700, color=TXT),
            ], spacing=8, tight=True),
            ft.Container(expand=True),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border=ft.border.all(0, BD),
    )

    secao_acoes = ft.Container(
        content=ft.Column([
            ft.Text("AÇÕES", size=10, color=SEC, weight=ft.FontWeight.W_700),
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
                        color=AMARELO,
                        side=ft.BorderSide(1, AMARELO),
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
        bgcolor=CARD,
        padding=16,
        border_radius=10,
        border=ft.border.all(1, BD),
        margin=ft.margin.symmetric(horizontal=12, vertical=8),
    )

    secao_hist = ft.Container(
        content=ft.Column([
            ft.Text("ÚLTIMOS BACKUPS", size=10, color=SEC, weight=ft.FontWeight.W_700),
            ft.Container(height=8),
            historico_col,
        ]),
        bgcolor=CARD,
        padding=16,
        border_radius=10,
        border=ft.border.all(1, BD),
        margin=ft.margin.symmetric(horizontal=12, vertical=4),
    )

    secao_info = ft.Container(
        content=ft.Column([
            ft.Text("INFORMAÇÕES", size=10, color=SEC, weight=ft.FontWeight.W_700),
            ft.Container(height=6),
            ft.Text(
                "Backups salvos em: Google Drive / Koios_Prontuario/\n"
                "• prontuario_db/ — prontuario.db (máx 5 versões)\n"
                "• koios_db/      — koios.db       (máx 5 versões)\n\n"
                "O backup automático ocorre 30 min após qualquer alteração no banco.",
                size=11, color=MUT,
            ),
        ]),
        bgcolor=CARD,
        padding=16,
        border_radius=10,
        border=ft.border.all(1, BD),
        margin=ft.margin.symmetric(horizontal=12, vertical=4),
    )

    corpo = ft.Column([
        header,
        ft.Container(
            content=ft.Column([
                secao_acoes,
                secao_hist,
                secao_info,
                ft.Container(height=20),
            ], scroll=ft.ScrollMode.AUTO),
            expand=True,
        ),
    ], expand=True)

    return ft.Container(bgcolor=BG, expand=True, content=corpo)
