# -*- coding: utf-8 -*-
# Prontuario Medico | telas_sistema/tela_backup.py
import threading
import flet as ft

BG      = "#0D1117"; CARD = "#161B22"; BD = "#21262D"
TXT     = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL    = "#58A6FF"; VERD = "#3FB950"; ERRO = "#F85149"; AMAR = "#D29922"


def criar_tela_backup(page: ft.Page, voltar_fn=None):

    _montado = [False]

    status_txt    = ft.Text("", size=13, color=SEC)
    progress      = ft.ProgressBar(visible=False, color=AZUL, bgcolor=BD)
    historico_col = ft.Column([], spacing=6)

    def _upd():
        if _montado[0]:
            try: page.update()
            except Exception: pass

    def _set_status(msg: str, cor: str = SEC) -> None:
        status_txt.value = msg
        status_txt.color = cor
        _upd()

    def _set_loading(visible: bool) -> None:
        progress.visible = visible
        _upd()

    # Historico
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
                historico_col.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon("check_circle_rounded", size=14, color=VERD),
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
        _upd()

    # Acoes
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
                _set_status(msg, VERD if ok else ERRO)
                if ok:
                    _carregar_historico()
            except Exception as ex:
                _set_status(f"Erro: {ex}", ERRO)
            finally:
                _set_loading(False)

        threading.Thread(target=_run, daemon=True).start()

    def _restaurar(e) -> None:
        ref = [None]

        def _fechar(ev=None):
            if ref[0] and ref[0] in page.overlay:
                page.overlay.remove(ref[0])
            try: page.update()
            except Exception: pass

        def _confirmar(ev):
            _fechar()
            _set_loading(True)
            _set_status("Restaurando backup...", AMAR)

            def _run() -> None:
                try:
                    from backup.drive_backup import restaurar_backup_completo
                    ok, msg = restaurar_backup_completo(
                        callback_progresso=lambda m: _set_status(m, AMAR),
                    )
                    _set_status(msg, VERD if ok else ERRO)
                except Exception as ex:
                    _set_status(f"Erro: {ex}", ERRO)
                finally:
                    _set_loading(False)

            threading.Thread(target=_run, daemon=True).start()

        btn_cancel = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{SEC}22", ink=True,
        )
        btn_cancel.on_click = _fechar

        btn_ok = ft.Container(
            content=ft.Text("Restaurar", size=13, color=ERRO,
                            weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{ERRO}22", ink=True,
        )
        btn_ok.on_click = _confirmar

        ref[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Restaurar Backup?", size=15, color=TXT,
                            weight=ft.FontWeight.W_700, text_align="center"),
                    ft.Container(height=8),
                    ft.Text(
                        "O banco local sera substituido pelo backup mais recente.\n"
                        "Esta acao nao pode ser desfeita.",
                        size=13, color=SEC, text_align="center",
                    ),
                    ft.Container(height=20),
                    ft.Row([btn_cancel, btn_ok], spacing=8,
                           alignment=ft.MainAxisAlignment.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(24), width=300,
            ),
            bgcolor="#CC000000", expand=True,
            alignment=ft.Alignment(0, 0),
        )
        ref[0].on_click = _fechar
        page.overlay.append(ref[0])
        try: page.update()
        except Exception: pass

    # Build da UI
    btn_voltar = ft.Container(
        content=ft.Row([
            ft.Icon("arrow_back_rounded", size=14, color=SEC),
            ft.Text("Voltar", size=12, color=SEC),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        border_radius=8, ink=True,
    )
    btn_voltar.on_click = lambda e: voltar_fn() if voltar_fn else None

    header = ft.Container(
        content=ft.Row([
            btn_voltar,
            ft.Row([
                ft.Icon("backup_rounded", size=18, color=AZUL),
                ft.Text("Backup & Restore", size=15,
                        weight=ft.FontWeight.W_700, color=TXT),
            ], spacing=8, tight=True),
            ft.Container(expand=True),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
    )

    btn_backup = ft.Container(
        content=ft.Row([
            ft.Icon("cloud_upload_rounded", size=16, color=BG),
            ft.Text("Fazer Backup Agora", size=13, color=BG,
                    weight=ft.FontWeight.W_600),
        ], spacing=8, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=AZUL, border_radius=10, ink=True,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        expand=True,
    )
    btn_backup.on_click = _fazer_backup

    btn_restaurar = ft.Container(
        content=ft.Row([
            ft.Icon("cloud_download_rounded", size=16, color=AMAR),
            ft.Text("Restaurar", size=13, color=AMAR,
                    weight=ft.FontWeight.W_600),
        ], spacing=8, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=f"{AMAR}18",
        border=ft.border.all(1, f"{AMAR}66"),
        border_radius=10, ink=True,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        expand=True,
    )
    btn_restaurar.on_click = _restaurar

    secao_acoes = ft.Container(
        content=ft.Column([
            ft.Text("ACOES", size=10, color=SEC, weight=ft.FontWeight.W_700),
            ft.Container(height=8),
            ft.Row([btn_backup, btn_restaurar], spacing=10),
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
            ft.Text("ULTIMOS BACKUPS", size=10, color=SEC,
                    weight=ft.FontWeight.W_700),
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
            ft.Text("INFORMACOES", size=10, color=SEC, weight=ft.FontWeight.W_700),
            ft.Container(height=6),
            ft.Text(
                "Backups salvos em: Google Drive / Koios_Prontuario/\n"
                "  prontuario_db/ -- prontuario.db (max 5 versoes)\n"
                "  koios_db/      -- koios.db       (max 5 versoes)\n\n"
                "O backup automatico ocorre 30 min apos qualquer alteracao.",
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

    _carregar_historico()
    _montado[0] = True
    return ft.Container(bgcolor=BG, expand=True, content=corpo)
