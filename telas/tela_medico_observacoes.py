# -*- coding: utf-8 -*-
# Prontuario | telas/tela_medico_observacoes.py
# Aba Observacoes do hub_medico: lista + formulario + upload PDF
import flet as ft
import logging

log = logging.getLogger(__name__)

BG    = "#0D1117"; CARD  = "#161B22"; BD   = "#21262D"; BD2   = "#30363D"
TXT   = "#E6EDF3"; SEC   = "#8B949E"; MUT  = "#484F58"
AZUL  = "#58A6FF"; VERD  = "#3FB950"; AMAR = "#D29922"
VERM  = "#F85149"; LRNJ  = "#F0883E"


def _para_display(s: str) -> str:
    if s and len(s) >= 10 and s[4] == "-":
        try:
            from datetime import datetime
            return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            pass
    return s or ""


def criar_aba_observacoes(page: ft.Page,
                           medico_id,
                           nome_medico: str,
                           upd_fn) -> ft.Control:
    """Retorna o widget completo da aba Observacoes."""
    import threading
    import datetime
    from dados.model_prontuario import (
        salvar_observacao_medico,
        listar_observacoes_medico,
        marcar_observacao_lida,
    )

    def _notify():
        try:
            from backup.backup_watcher import notify_db_changed
            notify_db_changed()
        except Exception:
            pass

    area_lista = ft.Column(spacing=6)
    area_form  = ft.Column(spacing=10)
    _mostrar_form = [False]
    _arquivo_selecionado = [None]   # {"path": str, "nome": str}

    # ── helpers UI ───────────────────────────────────────────
    def _snack(msg: str, cor: str = AZUL):
        snack = ft.SnackBar(
            content=ft.Text(msg, color=TXT), bgcolor=CARD)
        page.overlay.append(snack)
        snack.open = True
        try: page.update()
        except Exception: pass

    def _load_lista():
        area_lista.controls.clear()
        try:
            obs = listar_observacoes_medico(medico_id if medico_id else None)
            if not obs:
                area_lista.controls.append(
                    ft.Text("Nenhuma observacao registrada.", size=12, color=SEC))
            for o in obs:
                cor_lida = MUT if o["lida_paciente"] else LRNJ
                badge = ft.Container(
                    content=ft.Text(
                        "Nao lida" if not o["lida_paciente"] else "Lida",
                        size=9, color=cor_lida),
                    bgcolor=ft.Colors.with_opacity(0.10, cor_lida),
                    border_radius=4,
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                )
                has_pdf = bool(o.get("nome_arquivo"))
                pdf_row = []
                if has_pdf:
                    pdf_row.append(ft.Row([
                        ft.Icon("picture_as_pdf_rounded", size=12, color=VERM),
                        ft.Text(o["nome_arquivo"], size=10, color=SEC),
                    ], spacing=4))

                card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(_para_display(o["data"]),
                                    size=10, color=AMAR),
                            ft.Text(o.get("nome_medico") or "", size=10, color=SEC,
                                    expand=True),
                            badge,
                        ], spacing=6),
                        ft.Text(o["texto"] or "", size=12, color=TXT,
                                max_lines=4),
                        *pdf_row,
                    ], spacing=4, tight=True),
                    bgcolor=CARD,
                    border=ft.border.all(1, BD),
                    border_radius=8,
                    padding=ft.padding.all(12),
                )
                area_lista.controls.append(card)
        except Exception as ex:
            log.warning("[OBS_MEDICO] listar: %s", ex)
            area_lista.controls.append(
                ft.Text(f"Erro ao carregar: {ex}", size=11, color=VERM))
        upd_fn()

    # ── Formulario ───────────────────────────────────────────
    f_texto = ft.TextField(
        label="Observacao",
        multiline=True, min_lines=3, max_lines=8,
        bgcolor=CARD, border_color=BD2, focused_border_color=LRNJ,
        label_style=ft.TextStyle(color=SEC, size=11),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8,
    )

    txt_arquivo = ft.Text("Nenhum arquivo selecionado",
                          size=11, color=MUT)
    btn_pdf = ft.Container(
        content=ft.Row([
            ft.Icon("attach_file_rounded", size=14, color=SEC),
            ft.Text("Anexar PDF", size=12, color=SEC),
        ], spacing=5, tight=True),
        bgcolor=ft.Colors.with_opacity(0.06, SEC),
        border=ft.border.all(1, BD),
        border_radius=8, ink=True,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
    )

    _picker_ref = [None]

    def _on_picker_result(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            f = e.files[0]
            _arquivo_selecionado[0] = {"path": f.path, "nome": f.name}
            txt_arquivo.value = f.name
            try: page.update()
            except Exception: pass
        else:
            _arquivo_selecionado[0] = None
            txt_arquivo.value = "Nenhum arquivo selecionado"
            try: page.update()
            except Exception: pass

    def _abrir_picker(e=None):
        if not _picker_ref[0]:
            picker = ft.FilePicker(on_result=_on_picker_result)
            _picker_ref[0] = picker
            page.overlay.append(picker)
            try: page.update()
            except Exception: pass
        _picker_ref[0].pick_files(
            dialog_title="Selecionar PDF",
            allowed_extensions=["pdf"],
            allow_multiple=False,
        )

    btn_pdf.on_click = _abrir_picker

    def _salvar(e=None):
        texto = (f_texto.value or "").strip()
        if not texto:
            _snack("Informe o texto da observacao", AMAR)
            return

        hoje = datetime.date.today().isoformat()
        dados = {
            "medico_id":  medico_id,
            "nome_medico": nome_medico,
            "data":       hoje,
            "texto":      texto,
        }

        arq = _arquivo_selecionado[0]

        def _run():
            # upload PDF ao Drive se houver
            drive_id = None
            drive_nome = None
            if arq:
                try:
                    from utils.drive_sync import upload_arquivo
                    pasta = "Koios/Prontuario/observacoes_medico"
                    drive_id = upload_arquivo(arq["path"], pasta, arq["nome"])
                    drive_nome = arq["nome"]
                except Exception as ex:
                    log.warning("[OBS_MEDICO] upload pdf: %s", ex)
                    drive_nome = arq["nome"]

            dados["drive_file_id"] = drive_id
            dados["nome_arquivo"]  = drive_nome

            try:
                salvar_observacao_medico(dados)
                _notify()
                f_texto.value = ""
                _arquivo_selecionado[0] = None
                txt_arquivo.value = "Nenhum arquivo selecionado"
                _mostrar_form[0] = False
                _load_lista()
                _rebuild_form()
                _snack("Observacao salva", VERD)
            except Exception as ex:
                log.exception("[OBS_MEDICO] salvar: %s", ex)
                _snack(f"Erro ao salvar: {ex}", VERM)

        threading.Thread(target=_run, daemon=True, name="SalvarObs").start()

    btn_salvar = ft.Container(
        content=ft.Row([
            ft.Icon("check_rounded", size=14, color=BG),
            ft.Text("Salvar Observacao", size=13, color=BG,
                    weight=ft.FontWeight.W_600),
        ], spacing=5, tight=True),
        bgcolor=LRNJ, border_radius=10, ink=True,
        padding=ft.padding.symmetric(horizontal=18, vertical=10),
    )
    btn_salvar.on_click = _salvar

    btn_cancelar = ft.Container(
        content=ft.Text("Cancelar", size=12, color=SEC),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border_radius=8, bgcolor=ft.Colors.with_opacity(0.06, SEC), ink=True,
    )

    def _cancelar(e=None):
        _mostrar_form[0] = False
        f_texto.value = ""
        _arquivo_selecionado[0] = None
        txt_arquivo.value = "Nenhum arquivo selecionado"
        _rebuild_form()

    btn_cancelar.on_click = _cancelar

    def _rebuild_form():
        area_form.controls.clear()
        if _mostrar_form[0]:
            area_form.controls.extend([
                ft.Divider(height=1, color=BD),
                ft.Text("Nova observacao", size=12, color=LRNJ,
                        weight=ft.FontWeight.W_700),
                f_texto,
                ft.Row([btn_pdf, txt_arquivo], spacing=10,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([btn_cancelar, btn_salvar], spacing=10,
                       alignment=ft.MainAxisAlignment.END),
            ])
        upd_fn()

    btn_nova = ft.Container(
        content=ft.Row([
            ft.Icon("add_rounded", size=14, color=LRNJ),
            ft.Text("Nova Observacao", size=12, color=LRNJ,
                    weight=ft.FontWeight.W_600),
        ], spacing=5, tight=True),
        bgcolor=ft.Colors.with_opacity(0.10, LRNJ),
        border=ft.border.all(1, ft.Colors.with_opacity(0.35, LRNJ)),
        border_radius=8, ink=True,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
    )

    def _toggle_form(e=None):
        _mostrar_form[0] = not _mostrar_form[0]
        _rebuild_form()

    btn_nova.on_click = _toggle_form

    _load_lista()

    return ft.Column([
        ft.Row([
            ft.Text("OBSERVACOES DO MEDICO", size=10, color=LRNJ,
                    weight=ft.FontWeight.W_700, expand=True),
            btn_nova,
        ], spacing=8),
        ft.Container(height=4),
        area_lista,
        area_form,
    ], spacing=4, tight=True)
