"""
tela_incluir_exame.py
"""
import flet as ft
import threading
import logging
import os
from pathlib import Path


def criar_tela_incluir_exame(page: ft.Page, voltar_fn):

    is_web = getattr(page, "web", False)

    try:
        larg = page.width or 800
    except Exception:
        larg = 800

    # Estado
    caminho_sel = [""]
    nome_ref    = ft.Ref[ft.Text]()
    card_arq    = ft.Ref[ft.Container]()
    txt_status  = ft.Ref[ft.Text]()
    pb_ref      = ft.Ref[ft.ProgressBar]()

    def _set_status(msg, cor="#8B949E", prog=None):
        txt_status.current.value   = msg
        txt_status.current.color   = cor
        txt_status.current.visible = True
        if prog is not None:
            pb_ref.current.value   = prog
            pb_ref.current.visible = True
        page.update()

    def _reset():
        caminho_sel[0]             = ""
        nome_ref.current.value     = ""
        card_arq.current.visible   = False
        txt_status.current.value   = ""
        txt_status.current.visible = False
        pb_ref.current.visible     = False
        pb_ref.current.value       = 0
        page.update()

    def _set_arquivo(caminho):
        caminho_sel[0]             = caminho
        nome_ref.current.value     = os.path.basename(caminho)
        card_arq.current.visible   = True
        txt_status.current.value   = ""
        txt_status.current.visible = False
        page.update()

    def _processar(e):
        caminho = caminho_sel[0].strip()
        if not caminho:
            _set_status("Nenhum arquivo selecionado.", "#DA3633")
            return
        if not os.path.exists(caminho):
            _set_status("Arquivo nao encontrado.", "#DA3633")
            return

        from .extratores.extrator_pdf    import extrair_pdf_bytes
        from .dados.model_prontuario           import salvar_exame
        from .dados.limpeza         import executar_limpeza
        from .drive_connector import upload_arquivo

        nome     = os.path.basename(caminho)
        conteudo = Path(caminho).read_bytes()
        dados    = [None]

        def _run():
            try:
                _set_status(f"Enviando {nome}...", "#58A6FF", 0.2)
                drive_id           = upload_arquivo(caminho)
                _set_status("Extraindo com IA...", "#58A6FF", 0.5)
                d                  = extrair_pdf_bytes(conteudo, nome, drive_id)
                d["drive_file_id"] = drive_id
                dados[0]           = d
                _set_status("Salvando no banco...", "#58A6FF", 0.75)
                salvar_exame(dados[0])
                _set_status("Vinculando parametros...", "#58A6FF", 0.9)
                if dados[0] and dados[0].get("tipo", "numerico") == "numerico":
                    executar_limpeza()
                _set_status("Concluido com sucesso!", "#3FB950", 1.0)
            except Exception as ex:
                logging.exception(f"[INCLUIR] {ex}")
                _set_status(f"Erro: {str(ex)[:80]}", "#DA3633")

        threading.Thread(target=_run, daemon=True).start()

    # Selecao de arquivo
    if is_web:
        area_sel = ft.TextField(
            label="Caminho completo do PDF",
            hint_text="Ex: C:/Users/usuario/Downloads/exame.pdf",
            hint_style=ft.TextStyle(color="#484F58"),
            bgcolor="#161B22", border_color="#21262D",
            focused_border_color="#58A6FF",
            label_style=ft.TextStyle(color="#8B949E"),
            text_style=ft.TextStyle(color="#E6EDF3"),
            border_radius=8,
            prefix_icon=ft.Icons.FOLDER_OPEN,
            on_change=lambda e: _set_arquivo(e.control.value or ""),
        )
    else:
        def _on_picked(e: ft.FilePickerResultEvent):
            if e.files:
                _set_arquivo(e.files[0].path)

        fp = ft.FilePicker()
        fp.on_result = _on_picked
        page.overlay.append(fp)
        page.update()

        area_sel = ft.FilledButton(
            content=ft.Row([
                ft.Icon(ft.Icons.FOLDER_OPEN_ROUNDED, size=18),
                ft.Text("Procurar PDF...", size=14, weight=ft.FontWeight.W_600),
            ], spacing=8, tight=True),
            style=ft.ButtonStyle(
                bgcolor="#484F58",
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding(left=24, right=24, top=12, bottom=12),
            ),
            on_click=lambda e: fp.pick_files(
                dialog_title="Selecione um PDF",
                allowed_extensions=["pdf"],
                allow_multiple=False,
            ),
        )

    btn_voltar = ft.TextButton(
        content=ft.Row([
            ft.Icon(ft.Icons.ARROW_BACK, size=14, color="#8B949E"),
            ft.Text("Voltar", size=12, color="#8B949E"),
        ], spacing=4, tight=True),
        on_click=lambda e: voltar_fn(),
    )

    # Corpo — igual ao app.py
    corpo = ft.Column([
        # Cabecalho
        ft.Container(
            content=ft.Row([
                btn_voltar,
                ft.Row([
                    ft.Icon(ft.Icons.UPLOAD_FILE, size=20, color="#58A6FF"),
                    ft.Text("Incluir Exame", size=18,
                            weight=ft.FontWeight.W_700, color="#E6EDF3"),
                ], spacing=8, tight=True),
                ft.Container(expand=True),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.padding.symmetric(horizontal=16, vertical=14),
            border=ft.Border(bottom=ft.BorderSide(1, "#21262D")),
        ),
        # Conteudo
        ft.Container(
            content=ft.Column([
                ft.Text(
                    "Envie um PDF de exame para o Drive e processe com IA.",
                    size=13, color="#8B949E",
                ),
                ft.Container(height=8),
                area_sel,
                ft.Container(
                    ref=card_arq,
                    visible=False,
                    content=ft.Row([
                        ft.Icon(ft.Icons.PICTURE_AS_PDF, size=18, color="#DA3633"),
                        ft.Text("", ref=nome_ref, size=13, color="#E6EDF3",
                                expand=True, no_wrap=True,
                                overflow=ft.TextOverflow.ELLIPSIS),
                        ft.IconButton(
                            ft.Icons.CLOSE, icon_size=14, icon_color="#8B949E",
                            on_click=lambda e: _reset(),
                        ),
                    ], spacing=10),
                    bgcolor="#161B22", border_radius=8, padding=10,
                    border=ft.Border(
                        left=ft.BorderSide(2, "#DA3633"),
                        top=ft.BorderSide(1, "#21262D"),
                        bottom=ft.BorderSide(1, "#21262D"),
                        right=ft.BorderSide(1, "#21262D"),
                    ),
                ),
                ft.Container(height=8),
                ft.ProgressBar(ref=pb_ref, visible=False, value=0,
                               bgcolor="#21262D", color="#58A6FF"),
                ft.Text(ref=txt_status, value="", size=12,
                        color="#8B949E", visible=False,
                        text_align=ft.TextAlign.CENTER),
                ft.Container(height=8),
                ft.Row([
                    ft.FilledButton(
                        content=ft.Row([
                            ft.Icon(ft.Icons.CLOUD_UPLOAD_OUTLINED, size=18),
                            ft.Text("Enviar e Processar", size=14,
                                    weight=ft.FontWeight.W_600),
                        ], spacing=8, tight=True),
                        style=ft.ButtonStyle(
                            bgcolor="#58A6FF",
                            shape=ft.RoundedRectangleBorder(radius=8),
                            padding=ft.Padding(left=32, right=32, top=14, bottom=14),
                        ),
                        on_click=_processar,
                    ),
                ], alignment=ft.MainAxisAlignment.CENTER),
            ], spacing=6,
               horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
               scroll=ft.ScrollMode.AUTO, expand=True),
            padding=ft.padding.all(16),
            expand=True,
        ),
    ], expand=True, scroll=ft.ScrollMode.AUTO)

    # Responsivo — igual ao app.py
    if larg > 500:
        conteudo_final = ft.Row([
            ft.Container(expand=True),
            ft.Container(content=corpo, width=480),
            ft.Container(expand=True),
        ], expand=True)
    else:
        conteudo_final = corpo

    return ft.Container(
        bgcolor="#0D1117",
        expand=True,
        content=conteudo_final,
    )