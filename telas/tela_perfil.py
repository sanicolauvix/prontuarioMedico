# -*- coding: utf-8 -*-
# Prontuario | telas/tela_perfil.py
import flet as ft
import logging
import threading

from shared.layout import Layout

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


def criar_tela_perfil(page: ft.Page, voltar_fn=None):
    _montado      = [False]
    _status_banco = ["normal"]
    _handler_ant  = [None]

    def _sync(apos_sync_fn=None):
        ov = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.ProgressRing(color=AZUL, width=36, height=36, stroke_width=3),
                    ft.Container(height=10),
                    ft.Text("Sincronizando com Drive...", size=13, color=TXT,
                            weight=ft.FontWeight.W_600, text_align="center"),
                    ft.Text("Aguarde", size=11, color=SEC, text_align="center"),
                ], tight=True, spacing=2,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD, border_radius=14, padding=ft.padding.all(24), width=240,
            ),
            bgcolor="#DD000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        page.overlay.append(ov)
        try: page.update()
        except Exception: pass
        def _run():
            try:
                from backup.drive_backup import fazer_backup
                fazer_backup(forcar=True)
            except Exception as ex:
                logging.warning("[perfil] sync erro: %s", ex)
            finally:
                _status_banco[0] = "normal"
                if ov in page.overlay: page.overlay.remove(ov)
                try: page.update()
                except Exception: pass
                if apos_sync_fn: apos_sync_fn()
        threading.Thread(target=_run, daemon=True).start()

    def _sair():
        _desregistrar_voltar_hw()
        if _status_banco[0] == "em_edicao":
            _sync(voltar_fn)
        elif voltar_fn:
            voltar_fn()

    def _registrar_voltar_hw():
        _handler_ant[0] = page.on_keyboard_event
        def _on_hw(e):
            if e.key == "Escape": _sair()
        page.on_keyboard_event = _on_hw

    def _desregistrar_voltar_hw():
        page.on_keyboard_event = _handler_ant[0]

    def _atualizar_ui():
        if _montado[0]:
            try:
                page.update()
            except Exception:
                pass

    # ── Campos editáveis ──────────────────────────────────────────
    def _campo(label, valor="", hint="", largura=None):
        tf = ft.TextField(
            label=label,
            value=str(valor) if valor not in (None, "") else "",
            hint_text=hint,
            border_color=BD,
            focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=12),
            text_style=ft.TextStyle(color=TXT, size=13),
            bgcolor=CARD,
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
            width=largura,
        )
        return tf

    perfil = {}
    try:
        from dados.model_prontuario import carregar_perfil
        perfil = carregar_perfil() or {}
    except Exception:
        pass

    email_google = ""
    try:
        import os, json
        from shared.auth import _CREDS_PATH
        if os.path.exists(_CREDS_PATH):
            with open(_CREDS_PATH, "r", encoding="utf-8") as f:
                cd = json.load(f)
            email_google = cd.get("email", "")
    except Exception:
        pass

    email_atual = perfil.get("email") or email_google

    f_nome       = _campo("Nome completo",  perfil.get("nome", ""))
    f_data_nasc  = _campo("Data nasc.",     perfil.get("data_nasc", ""), hint="AAAA-MM-DD", largura=160)
    f_peso       = _campo("Peso (kg)",      perfil.get("peso", ""),      hint="70.5",       largura=120)
    f_altura     = _campo("Altura (cm)",    perfil.get("altura", ""),    hint="175",         largura=120)

    dd_sexo = ft.Dropdown(
        label="Sexo",
        value=perfil.get("sexo", ""),
        options=[
            ft.dropdown.Option("M", "Masculino"),
            ft.dropdown.Option("F", "Feminino"),
            ft.dropdown.Option("O", "Outro"),
        ],
        border_color=BD,
        focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC, size=12),
        text_style=ft.TextStyle(color=TXT, size=13),
        bgcolor=CARD,
        border_radius=8,
        expand=True,
    )

    dd_sangue = ft.Dropdown(
        label="Tipo sanguíneo",
        value=perfil.get("tipo_sanguineo", ""),
        options=[ft.dropdown.Option(t) for t in
                 ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Não sei"]],
        border_color=BD,
        focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC, size=12),
        text_style=ft.TextStyle(color=TXT, size=13),
        bgcolor=CARD,
        border_radius=8,
        expand=True,
    )

    f_cond = _campo(
        "Condições crônicas",
        ", ".join(perfil.get("condicoes_cronicas") or []),
        hint="Ex: Hipertensão, Diabetes",
    )
    f_contato = _campo("Contato de emergência", perfil.get("contato_emergencia", ""))
    f_tel     = _campo("Telefone emergência",   perfil.get("tel_emergencia", ""), hint="(99) 99999-9999")

    txt_status = ft.Text("", size=12, color=VERD)

    def _salvar(e):
        try:
            condicoes_raw = f_cond.value.strip()
            condicoes = [c.strip() for c in condicoes_raw.split(",") if c.strip()] if condicoes_raw else []

            dados = {
                "nome":               f_nome.value.strip() or None,
                "email":              email_atual,
                "data_nasc":          f_data_nasc.value.strip() or None,
                "sexo":               dd_sexo.value or None,
                "foto_url":           perfil.get("foto_url"),
                "peso":               float(f_peso.value.replace(",", ".")) if f_peso.value.strip() else None,
                "altura":             float(f_altura.value.replace(",", ".")) if f_altura.value.strip() else None,
                "tipo_sanguineo":     dd_sangue.value or None,
                "condicoes_cronicas": condicoes,
                "contato_emergencia": f_contato.value.strip() or None,
                "tel_emergencia":     f_tel.value.strip() or None,
                "tema":               perfil.get("tema", "dark"),
                "accent_color":       perfil.get("accent_color", "#58A6FF"),
                "tamanho_fonte":      perfil.get("tamanho_fonte", "medio"),
            }
            from dados.model_prontuario import salvar_perfil
            salvar_perfil(dados)
            txt_status.value = "Perfil salvo!"
            txt_status.color = VERD
            _status_banco[0] = "em_edicao"
            logging.info("[PERFIL] Salvo")
        except Exception as ex:
            txt_status.value = f"Erro: {ex}"
            txt_status.color = VERM
            logging.exception("[PERFIL] Erro ao salvar")
        _atualizar_ui()
        if _status_banco[0] == "em_edicao":
            _sync()

    # ── Backup / Restore ─────────────────────────────────────────
    txt_backup_status = ft.Text("", size=12, color=SEC)
    txt_backup_hist   = ft.Text("", size=11, color=MUT)
    progress_backup   = ft.ProgressBar(visible=False, color=AZUL, bgcolor=BD)

    def _upd_backup():
        if _montado[0]:
            try: page.update()
            except Exception: pass

    def _carregar_hist_backup():
        try:
            from backup.drive_backup import carregar_historico
            hist = carregar_historico()
            if hist:
                ult = hist[0]
                txt_backup_hist.value = f"Ultimo: {ult.get('data_fmt', '—')}  ({ult.get('enviados',0)} banco(s))"
            else:
                txt_backup_hist.value = "Nenhum backup registrado."
        except Exception:
            txt_backup_hist.value = ""
        _upd_backup()

    def _fazer_backup(e):
        progress_backup.visible = True
        txt_backup_status.value = "Conectando ao Drive..."
        txt_backup_status.color = AZUL
        _upd_backup()

        def _run():
            try:
                from backup.drive_backup import fazer_backup
                ok, msg = fazer_backup(
                    forcar=True,
                    callback_progresso=lambda m: (
                        setattr(txt_backup_status, "value", m[:70]),
                        _upd_backup(),
                    ),
                )
                txt_backup_status.value = msg[:70]
                txt_backup_status.color = VERD if ok else VERM
                if ok:
                    _carregar_hist_backup()
            except Exception as ex:
                txt_backup_status.value = f"Erro: {str(ex)[:60]}"
                txt_backup_status.color = VERM
            finally:
                progress_backup.visible = False
                _upd_backup()

        threading.Thread(target=_run, daemon=True).start()

    def _restaurar(e):
        ref_ov = [None]

        def _fechar(ev=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        def _confirmar(ev):
            _fechar()
            progress_backup.visible = True
            txt_backup_status.value = "Restaurando..."
            txt_backup_status.color = AMAR
            _upd_backup()

            def _run():
                try:
                    from backup.drive_backup import restaurar_backup_completo
                    ok, msg = restaurar_backup_completo(
                        callback_progresso=lambda m: (
                            setattr(txt_backup_status, "value", m[:70]),
                            _upd_backup(),
                        ),
                    )
                    txt_backup_status.value = msg[:70]
                    txt_backup_status.color = VERD if ok else VERM
                    if ok:
                        _carregar_hist_backup()
                except Exception as ex:
                    txt_backup_status.value = f"Erro: {str(ex)[:60]}"
                    txt_backup_status.color = VERM
                finally:
                    progress_backup.visible = False
                    _upd_backup()

            threading.Thread(target=_run, daemon=True).start()

        btn_cancel = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{SEC}22", ink=True,
        )
        btn_cancel.on_click = _fechar

        btn_ok = ft.Container(
            content=ft.Text("Restaurar", size=13, color=VERM,
                            weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{VERM}22", ink=True,
        )
        btn_ok.on_click = _confirmar

        ref_ov[0] = ft.Container(
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
                    ft.Row([btn_cancel, btn_ok], spacing=8,
                           alignment=ft.MainAxisAlignment.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(24), width=300,
            ),
            bgcolor="#CC000000", expand=True,
            alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass

    def _abrir_tela_backup():
        tela_pai = page.controls[0]

        def _voltar_bk():
            page.controls.clear()
            page.controls.append(tela_pai)
            try: page.update()
            except Exception: pass

        from telas_sistema.tela_config import criar_tela_config
        page.controls.clear()
        page.controls.append(criar_tela_config(page, _voltar_bk, aba_inicial=1))
        try: page.update()
        except Exception: pass

    btn_fazer_backup = ft.Container(
        content=ft.Row([
            ft.Icon("cloud_upload_rounded", size=15, color=BG),
            ft.Text("Fazer Backup", size=13, color=BG, weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        bgcolor=AZUL, border_radius=8, ink=True,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        expand=True, alignment=ft.alignment.Alignment(0, 0),
    )
    btn_fazer_backup.on_click = _fazer_backup

    btn_restaurar = ft.Container(
        content=ft.Row([
            ft.Icon("cloud_download_rounded", size=15, color=VERM),
            ft.Text("Restaurar", size=13, color=VERM),
        ], spacing=6, tight=True),
        bgcolor=f"{VERM}18", border_radius=8, ink=True,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border=ft.Border(
            top=ft.BorderSide(1, f"{VERM}44"), bottom=ft.BorderSide(1, f"{VERM}44"),
            left=ft.BorderSide(1, f"{VERM}44"), right=ft.BorderSide(1, f"{VERM}44"),
        ),
        expand=True, alignment=ft.alignment.Alignment(0, 0),
    )
    btn_restaurar.on_click = _restaurar

    btn_ver_backup = ft.Container(
        content=ft.Row([
            ft.Icon("history_rounded", size=14, color=SEC),
            ft.Text("Historico completo", size=12, color=SEC),
            ft.Container(expand=True),
            ft.Icon("chevron_right_rounded", size=14, color=MUT),
        ], spacing=6),
        ink=True,
    )
    btn_ver_backup.on_click = lambda e: _abrir_tela_backup()

    _carregar_hist_backup()

    # ── Header padrao ────────────────────────────────────────────
    lay = Layout(page)

    btn_salvar_hdr = ft.Container(
        content=ft.Row([
            ft.Icon("save_rounded", size=14, color=AZUL),
            ft.Text("Salvar", size=13, color=AZUL),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        border_radius=8, ink=True,
    )
    btn_salvar_hdr.on_click = _salvar

    header = lay.criar_cabecalho(
        "Perfil", lambda e=None: _sair(),
        icone_titulo="manage_accounts_rounded",
        cor_titulo=AZUL,
        acoes=[btn_salvar_hdr],
    )

    def _secao(titulo):
        return ft.Text(titulo, size=10, weight=ft.FontWeight.W_700, color=SEC)

    def _card_section(controles):
        return ft.Container(
            content=ft.Column(controles, spacing=10),
            bgcolor=CARD,
            border=ft.border.all(1, BD),
            border_radius=10,
            padding=16,
        )

    # E-mail (read-only)
    email_row = ft.Container(
        content=ft.Row([
            ft.Text("E-mail", size=12, color=SEC, expand=True),
            ft.Text(email_atual or "—", size=12, color=MUT),
        ]),
        padding=ft.padding.symmetric(vertical=4),
    )

    area = ft.ListView(
        spacing=12,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        expand=True,
    )

    area.controls += [
        _secao("DADOS PESSOAIS"),
        _card_section([
            f_nome,
            email_row,
            ft.Row([f_data_nasc, dd_sexo], spacing=10),
        ]),
        _secao("DADOS CLÍNICOS"),
        _card_section([
            ft.Row([f_peso, f_altura, dd_sangue], spacing=10),
            f_cond,
        ]),
        _secao("EMERGÊNCIA"),
        _card_section([
            f_contato,
            f_tel,
        ]),
        txt_status,
        ft.Container(height=8),
        _secao("BACKUP & SINCRONIZACAO"),
        _card_section([
            ft.Row([btn_fazer_backup, btn_restaurar], spacing=8),
            progress_backup,
            txt_backup_status,
            txt_backup_hist,
            ft.Divider(color=BD, height=1),
            btn_ver_backup,
        ]),
        ft.Container(height=16),
    ]

    corpo = lay.criar_corpo(header, area)
    _montado[0] = True
    _registrar_voltar_hw()
    return ft.Container(bgcolor=BG, expand=True, content=corpo)
