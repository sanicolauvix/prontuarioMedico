# -*- coding: utf-8 -*-
"""
tela_medicos.py — Koios Prontuário
Cadastro, listagem e histórico de médicos.
Padrão visual: idêntico a tela_exames.py (header + barra de abas + área de conteúdo)
"""
import logging
import threading
import flet as ft
from shared.layout import Layout
from dados.model_prontuario import (
    listar_medicos, salvar_medico, listar_especialidades, exames_do_medico,
)

logger = logging.getLogger(__name__)

# ── Paleta ────────────────────────────────────────────────────
BG   = "#0D1117";  CARD = "#161B22";  BD  = "#21262D";  BD2 = "#30363D"
TXT  = "#E6EDF3";  SEC  = "#8B949E";  MUT = "#484F58"
AZUL = "#58A6FF";  VERD = "#3FB950";  LAR = "#F0883E"
VERM = "#DA3633";  ROXO = "#BC8CFF"


# ══════════════════════════════════════════════════════════════
# FICHA DE CADASTRO / EDIÇÃO
# ══════════════════════════════════════════════════════════════

def _tela_ficha_medico(page: ft.Page, medico, voltar_fn):
    especialidades = listar_especialidades()
    is_novo        = medico is None
    _modo_edicao   = [is_novo]   # novo abre direto em edicao; existente abre read-only
    _status_banco  = ["normal"]
    _handler_ant   = [None]
    lay            = Layout(page)

    # ── sync padrao Koios ─────────────────────────────────────
    def _sync(apos_sync_fn=None):
        ov = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.ProgressRing(color=ROXO, width=36, height=36, stroke_width=3),
                    ft.Container(height=10),
                    ft.Text("Sincronizando com Drive...", size=13, color=TXT,
                            weight=ft.FontWeight.W_600, text_align="center"),
                    ft.Text("Aguarde", size=11, color=SEC, text_align="center"),
                ], tight=True, spacing=2,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(24), width=240,
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
                logger.warning("[medicos] sync erro: %s", ex)
            finally:
                _status_banco[0] = "normal"
                if ov in page.overlay:
                    page.overlay.remove(ov)
                try: page.update()
                except Exception: pass
                if apos_sync_fn:
                    apos_sync_fn()

        threading.Thread(target=_run, daemon=True).start()

    def _sair(destino_fn):
        _desregistrar_voltar_hw()
        if _modo_edicao[0]:
            _salvar(None)
        elif _status_banco[0] == "em_edicao":
            _sync(destino_fn)
        else:
            destino_fn()

    def _registrar_voltar_hw():
        _handler_ant[0] = page.on_keyboard_event
        def _on_hw(e):
            if e.key == "Escape":
                _sair(voltar_fn)
        page.on_keyboard_event = _on_hw

    def _desregistrar_voltar_hw():
        page.on_keyboard_event = _handler_ant[0]

    # ── helpers visuais ───────────────────────────────────────
    def _url_foto(drive_id):
        if not drive_id:
            return ""
        return f"https://drive.google.com/thumbnail?id={drive_id}&sz=w200"

    def _campo(label, valor="", largura=None, multiline=False, min_lines=1, read_only=False):
        kwargs = dict(
            label=label, value=valor,
            bgcolor=CARD, border_color=BD2,
            focused_border_color=ROXO,
            label_style=ft.TextStyle(color=SEC),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            multiline=multiline,
            min_lines=min_lines,
            read_only=read_only,
        )
        if largura:
            kwargs["width"] = largura
        else:
            kwargs["expand"] = True
        return ft.TextField(**kwargs)

    def _label_sec(texto):
        return ft.Text(texto, size=10, color=MUT, weight=ft.FontWeight.W_700)

    # ── foto ──────────────────────────────────────────────────
    foto_drive_id   = [medico.get("foto_drive_id", "") if medico else ""]
    txt_status_foto = ft.Text("", size=10, color=SEC)

    img_preview = ft.Image(
        src=_url_foto(foto_drive_id[0]),
        width=72, height=72, fit="cover", border_radius=36,
        visible=bool(foto_drive_id[0]),
    )
    icone_sem_foto = ft.Container(
        content=ft.Column([
            ft.Icon("person_rounded", size=30, color=MUT),
            ft.Text("Foto", size=9, color=MUT),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
        width=72, height=72, border_radius=36,
        bgcolor=ft.Colors.with_opacity(0.13, ROXO),
        alignment=ft.alignment.Alignment(0, 0),
        visible=not bool(foto_drive_id[0]),
    )

    def _selecionar_foto(e):
        if not _modo_edicao[0]:
            return
        def _picker():
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk(); root.withdraw()
                root.attributes("-topmost", True)
                caminho = filedialog.askopenfilename(
                    title="Selecionar foto",
                    filetypes=[("Imagens", "*.jpg *.jpeg *.png *.webp *.bmp")],
                )
                root.destroy()
                if not caminho:
                    return
                page.pubsub.send_all({"_tipo": "foto_medico", "status": "Enviando para o Drive..."})
                try:
                    from utils.drive_prontuario import upload_foto_medico
                    drive_id = upload_foto_medico(caminho)
                    foto_drive_id[0] = drive_id
                    page.pubsub.send_all({"_tipo": "foto_medico", "drive_id": drive_id,
                                          "status": "Foto salva no Drive"})
                except Exception as ex:
                    logger.error("upload foto medico: %s", ex, exc_info=True)
                    foto_drive_id[0] = caminho
                    page.pubsub.send_all({"_tipo": "foto_medico", "drive_id": caminho,
                                          "status": "Foto local (Drive indisponivel)"})
            except Exception as ex:
                logger.error("_selecionar_foto: %s", ex, exc_info=True)
                page.pubsub.send_all({"_tipo": "foto_medico", "status": f"Erro: {ex}"})

        _subscribed = [False]
        def _on_msg(msg):
            if not isinstance(msg, dict) or msg.get("_tipo") != "foto_medico":
                return
            txt_status_foto.value = msg.get("status", "")
            if "drive_id" in msg:
                img_preview.src        = _url_foto(msg["drive_id"])
                img_preview.visible    = True
                icone_sem_foto.visible = False
            try: page.update()
            except Exception: pass
        if not _subscribed[0]:
            page.pubsub.subscribe(_on_msg)
            _subscribed[0] = True
        threading.Thread(target=_picker, daemon=True).start()

    icone_editar_foto = ft.Container(
        content=ft.Icon("edit_rounded", size=14, color="#FFFFFF"),
        width=22, height=22, border_radius=11,
        bgcolor="#00000088",
        alignment=ft.alignment.Alignment(0, 0),
        right=0, bottom=0,
        visible=_modo_edicao[0],
    )
    avatar_btn = ft.Container(
        content=ft.Stack([img_preview, icone_sem_foto, icone_editar_foto]),
        width=72, height=72, border_radius=36,
        on_click=_selecionar_foto,
    )
    foto_row = ft.Row([
        avatar_btn,
        ft.Column([
            ft.Text("Foto de perfil", size=12, color=SEC),
            ft.Text("Clique no avatar para selecionar", size=10, color=MUT),
            txt_status_foto,
        ], spacing=3),
    ], spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    # ── campos ────────────────────────────────────────────────
    ro = not _modo_edicao[0]   # read_only inicial
    f_nome  = _campo("Nome completo *", medico["nome"] if medico else "",           read_only=ro)
    f_crm   = _campo("CRM",  medico.get("crm", "")  if medico else "", largura=120, read_only=ro)
    f_uf    = _campo("UF",   medico.get("uf", "")   if medico else "", largura=65,  read_only=ro)
    f_tel   = _campo("Telefone",  medico.get("telefone", "")  if medico else "",    read_only=ro)
    f_email = _campo("E-mail",    medico.get("email", "")     if medico else "",    read_only=ro)
    f_end   = _campo("Endereço do consultório",
                     medico.get("endereco", "") if medico else "",                  read_only=ro)
    f_obs   = _campo("Observações", medico.get("observacoes", "") if medico else "",
                     multiline=True, min_lines=3,                                   read_only=ro)
    sw_ativo = ft.Switch(
        label="Ativo", value=bool(medico.get("ativo", 1)) if medico else True,
        active_color=ROXO, disabled=ro,
    )

    # ── especialidade busca + chip ────────────────────────────
    esp_id_sel   = [None]
    esp_nome_ini = ""
    if medico:
        if medico.get("especialidade_id"):
            esp_id_sel[0] = str(medico["especialidade_id"])
            match = next((e for e in especialidades
                          if str(e["id"]) == str(medico["especialidade_id"])), None)
            if match:
                esp_nome_ini = match["nome"]
        if not esp_nome_ini and medico.get("especialidade"):
            esp_nome_ini = medico["especialidade"]
            match = next((e for e in especialidades if e["nome"] == esp_nome_ini), None)
            if match:
                esp_id_sel[0] = str(match["id"])

    esp_chip = ft.Container(
        content=ft.Row([
            ft.Icon("local_hospital_rounded", size=13, color=ROXO),
            ft.Text(esp_nome_ini, size=12, color=ROXO, weight=ft.FontWeight.W_600),
            ft.Icon("close_rounded", size=13, color=ROXO,
                    visible=_modo_edicao[0]),   # X visivel so em edicao
        ], spacing=6, tight=True),
        bgcolor=ft.Colors.with_opacity(0.12, ROXO), border_radius=16,
        padding=ft.padding.symmetric(horizontal=10, vertical=5),
        ink=_modo_edicao[0], visible=bool(esp_nome_ini),
    )
    f_esp_txt = ft.TextField(
        hint_text="Buscar especialidade...",
        prefix_icon="search_rounded",
        bgcolor=CARD, border_color=BD2, focused_border_color=ROXO,
        hint_style=ft.TextStyle(color=MUT),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, expand=True, height=42,
        visible=_modo_edicao[0] and not bool(esp_nome_ini),
    )
    sugestoes_esp = ft.Column(spacing=4, visible=False)

    def _mostrar_chip_esp(nome):
        esp_chip.content.controls[1].value = nome
        esp_chip.visible = True
        f_esp_txt.visible = False
        sugestoes_esp.controls.clear()
        sugestoes_esp.visible = False
        try: page.update()
        except Exception: pass

    def _limpar_esp(e=None):
        if not _modo_edicao[0]:
            return
        esp_id_sel[0] = None
        esp_chip.visible = False
        f_esp_txt.value = ""
        f_esp_txt.visible = True
        sugestoes_esp.controls.clear()
        sugestoes_esp.visible = False
        try: page.update()
        except Exception: pass

    esp_chip.on_click = _limpar_esp

    def _filtrar_esp(e):
        if not _modo_edicao[0]:
            return
        termo = (f_esp_txt.value or "").strip().upper()
        sugestoes_esp.controls.clear()
        if not termo:
            sugestoes_esp.visible = False
            try: page.update()
            except Exception: pass
            return
        matches = [esp for esp in especialidades if termo in esp["nome"].upper()][:8]
        if not matches:
            sugestoes_esp.controls.append(ft.Container(
                content=ft.Text("Nenhuma especialidade encontrada.", size=12, color=MUT),
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            ))
            sugestoes_esp.visible = True
            try: page.update()
            except Exception: pass
            return
        for esp in matches:
            desc = esp.get("descricao") or ""
            def make_sel(item=esp):
                def sel(ev):
                    esp_id_sel[0] = str(item["id"])
                    _mostrar_chip_esp(item["nome"])
                return sel
            sugestoes_esp.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("local_hospital_rounded", size=13, color=ROXO),
                    ft.Column([
                        ft.Text(esp["nome"], size=13, color=TXT),
                        ft.Text(desc, size=10, color=MUT) if desc else ft.Container(),
                    ], spacing=1, expand=True, tight=True),
                    ft.Icon("add_circle_outline_rounded", size=14, color=ROXO),
                ], spacing=8),
                bgcolor=CARD, border_radius=6,
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                border=ft.Border(
                    left=ft.BorderSide(2, ROXO),
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
                on_click=make_sel(), ink=True,
            ))
        sugestoes_esp.visible = True
        try: page.update()
        except Exception: pass

    f_esp_txt.on_change = _filtrar_esp

    # ── exames vinculados (read-only) ─────────────────────────
    exames_section = ft.Container()
    if medico:
        exames = exames_do_medico(medico["id"])
        if exames:
            linhas_ex = [
                ft.Row([
                    ft.Icon("science_rounded", size=12, color=AZUL),
                    ft.Text(
                        f"{ex['data_exame'] or '?'} — "
                        f"{ex['tipo_exame'] or ex['laboratorio'] or '?'}",
                        size=12, color=SEC, expand=True,
                    ),
                ], spacing=6)
                for ex in exames[:10]
            ]
            exames_section = ft.Container(
                content=ft.Column([
                    _label_sec(f"EXAMES VINCULADOS ({len(exames)})"),
                    ft.Container(height=4),
                ] + linhas_ex, spacing=6),
                bgcolor=BG, border_radius=8, padding=12,
                border=ft.Border(
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    left=ft.BorderSide(2, AZUL), right=ft.BorderSide(1, BD),
                ),
            )

    # ── botao salvar (visivel so em edicao) ───────────────────
    txt_erro = ft.Text("", color=VERM, size=12)

    btn_salvar_med = ft.Container(
        content=ft.Row([
            ft.Icon("save_rounded", size=16, color=BG),
            ft.Text("Salvar Médico", size=14, color=BG, weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=ROXO, border_radius=10, ink=True,
        padding=ft.padding.symmetric(vertical=14),
        alignment=ft.alignment.Alignment(0, 0),
        visible=_modo_edicao[0],
    )

    def _salvar(e):
        if not (f_nome.value or "").strip():
            txt_erro.value = "Nome é obrigatório."
            try: page.update()
            except Exception: pass
            return
        salvar_medico({
            "id":               medico["id"] if medico else None,
            "nome":             (f_nome.value or "").strip(),
            "crm":              (f_crm.value or "").strip() or None,
            "uf":               (f_uf.value or "").strip().upper() or None,
            "especialidade_id": int(esp_id_sel[0]) if esp_id_sel[0] else None,
            "telefone":         (f_tel.value or "").strip() or None,
            "email":            (f_email.value or "").strip() or None,
            "endereco":         (f_end.value or "").strip() or None,
            "site":             None,
            "redes_sociais":    "{}",
            "foto_drive_id":    foto_drive_id[0] or None,
            "observacoes":      (f_obs.value or "").strip() or None,
            "ativo":            1 if sw_ativo.value else 0,
        })
        _status_banco[0] = "em_edicao"
        _sync(voltar_fn)

    btn_salvar_med.on_click = _salvar

    # ── ativar modo edicao ────────────────────────────────────
    def _ativar_edicao(e=None):
        _modo_edicao[0] = True
        for f in [f_nome, f_crm, f_uf, f_tel, f_email, f_end, f_obs]:
            f.read_only = False
        sw_ativo.disabled = False
        icone_editar_foto.visible = True
        # chip: mostrar X e habilitar ink
        esp_chip.content.controls[2].visible = True
        esp_chip.ink = True
        # campo busca: mostrar se nao ha especialidade selecionada
        if not esp_id_sel[0]:
            f_esp_txt.visible = True
        btn_salvar_med.visible = True
        btn_editar.visible     = False
        try: page.update()
        except Exception: pass

    btn_editar = ft.Container(
        content=ft.Row([
            ft.Icon("edit_rounded", size=15, color=ROXO),
            ft.Text("Editar", size=13, color=ROXO),
        ], spacing=5, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8,
        bgcolor=ft.Colors.with_opacity(0.12, ROXO),
        ink=True,
        visible=not is_novo,   # novo ja abre em edicao, sem botao editar
    )
    btn_editar.on_click = _ativar_edicao

    # ── cabecalho ─────────────────────────────────────────────
    titulo = "Novo Médico" if is_novo else "Médico"
    cabecalho = lay.criar_cabecalho(
        titulo, lambda e=None: _sair(voltar_fn),
        icone_titulo="person_rounded",
        cor_titulo=ROXO,
        acoes=[btn_editar],
    )

    campos_col = ft.Column([
        _label_sec("IDENTIFICAÇÃO"),
        foto_row,
        f_nome,
        ft.Row([f_crm, f_uf], spacing=8),
        ft.Column([
            ft.Text("Especialidade", size=10, color=MUT,
                    weight=ft.FontWeight.W_700),
            esp_chip,
            f_esp_txt,
            sugestoes_esp,
        ], spacing=4),
        ft.Container(height=6),
        _label_sec("CONTATO"),
        f_tel,
        f_email,
        f_end,
        ft.Container(height=6),
        _label_sec("OBSERVAÇÕES"),
        f_obs,
        ft.Container(height=6),
        sw_ativo,
        txt_erro,
        ft.Container(height=16),
        btn_salvar_med,
        ft.Container(height=8),
        exames_section,
        ft.Container(height=20),
    ], spacing=8, scroll=ft.ScrollMode.AUTO)

    corpo = lay.criar_corpo(cabecalho, campos_col,
                            padding_area=ft.padding.symmetric(horizontal=16, vertical=12))
    _registrar_voltar_hw()
    return lay.wrap(ft.Container(bgcolor=BG, expand=True, content=corpo))


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL — LISTA DE MÉDICOS
# ══════════════════════════════════════════════════════════════

def criar_tela_medicos(page: ft.Page, voltar_fn):
    especialidades = listar_especialidades()   # compartilhado por todas as abas

    ABAS = [
        (0, "people_rounded",              "Médicos",        ROXO),
        (1, "local_hospital_rounded", "Especialidades", AZUL),
    ]
    aba_ativa = [0]

    barra_abas    = ft.Row(spacing=0)
    area_conteudo = ft.Column(spacing=8, expand=True, scroll=ft.ScrollMode.AUTO)

    # wrapper permite substituir por ficha sem sair da tela
    wrapper = ft.Column(expand=True, spacing=0)

    def _rebuild_abas():
        barra_abas.controls.clear()
        for idx, icone, label, cor in ABAS:
            ativo = idx == aba_ativa[0]
            def _click(e, i=idx):
                aba_ativa[0] = i
                _rebuild_abas()
                _rebuild_conteudo()
            barra_abas.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon(icone, size=16, color=cor if ativo else SEC),
                    ft.Text(label, size=10,
                            color=cor if ativo else SEC,
                            weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.W_400),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=2, tight=True),
                expand=True,
                padding=ft.padding.symmetric(vertical=10),
                border=ft.Border(bottom=ft.BorderSide(2, cor if ativo else "#00000000")),
                on_click=_click,
            ))
        try: page.update()
        except Exception: pass

    # ── ABA 0: lista de médicos ───────────────────────────────
    lista    = ft.Column(spacing=8)
    txt_busca = ft.TextField(
        hint_text="Buscar médico...",
        prefix_icon="search_rounded",
        bgcolor=CARD, border_color=BD2, focused_border_color=ROXO,
        hint_style=ft.TextStyle(color=MUT),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, expand=True,
    )

    def carregar(filtro=""):
        lista.controls.clear()
        medicos = listar_medicos(so_ativos=False)
        if filtro:
            medicos = [m for m in medicos if filtro.upper() in m["nome"].upper()]

        if not medicos:
            lista.controls.append(ft.Container(
                content=ft.Text("Nenhum médico cadastrado.", color=SEC, size=13),
                padding=20,
            ))
            try: page.update()
            except Exception: pass
            return

        for m in medicos:
            esp       = m.get("especialidade") or "Especialidade não informada"
            crm       = f"CRM {m['crm']}/{m['uf']}" if m.get("crm") else ""
            ativo     = m.get("ativo", 1)
            cor_status= VERD if ativo else MUT
            foto      = m.get("foto_drive_id", "")

            avatar = ft.Image(
                src=foto, width=50, height=50, fit="cover", border_radius=12,
            ) if foto else ft.Container(
                content=ft.Icon("person_rounded", size=26, color=ROXO),
                bgcolor=ft.Colors.with_opacity(0.13, ROXO), border_radius=12,
                width=50, height=50,
                alignment=ft.alignment.Alignment(0, 0),
            )

            def make_click(medico):
                def click(e): _abrir_ficha(medico)
                return click

            lista.controls.append(ft.Container(
                content=ft.Row([
                    avatar,
                    ft.Column([
                        ft.Text(m["nome"], size=14, color=TXT,
                                weight=ft.FontWeight.W_600),
                        ft.Row([
                            ft.Text(esp, size=11, color=ROXO),
                            ft.Text("·", size=11, color=MUT),
                            ft.Text(crm, size=11, color=SEC),
                        ], spacing=4),
                    ], spacing=2, expand=True),
                    ft.Container(width=8, height=8, bgcolor=cor_status,
                                 border_radius=4),
                    ft.Icon("chevron_right_rounded", size=16, color=MUT),
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                border=ft.Border(
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    left=ft.BorderSide(1, BD), right=ft.BorderSide(1, BD),
                ),
                on_click=make_click(m), ink=True,
            ))
        try: page.update()
        except Exception: pass

    txt_busca.on_change = lambda e: carregar(txt_busca.value or "")

    def _conteudo_medicos():
        _btn_novo_med = ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=16, color=BG),
                ft.Text("Novo", size=13, color=BG),
            ], spacing=6, tight=True),
            bgcolor=ROXO, border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
        )
        _btn_novo_med.on_click = lambda e: _abrir_ficha(None)

        return [
            ft.Row([
                txt_busca,
                _btn_novo_med,
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            lista,
        ]

    def _conteudo_especialidades():
        todos_medicos  = listar_medicos(so_ativos=False)
        esp_sel        = [None]   # None = sem filtro, "sem" = sem especialidade

        # ── chip da especialidade selecionada ─────────────────
        esp_chip = ft.Container(
            content=ft.Row([
                ft.Icon("local_hospital_rounded", size=13, color=AZUL),
                ft.Text("", size=12, color=AZUL, weight=ft.FontWeight.W_600),
                ft.Icon("close_rounded", size=13, color=AZUL),
            ], spacing=6, tight=True),
            bgcolor=ft.Colors.with_opacity(0.12, AZUL), border_radius=16,
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            visible=False,
        )

        # ── lista de médicos filtrada ─────────────────────────
        lista_esp = ft.Column(spacing=6)

        def _renderizar_medicos():
            lista_esp.controls.clear()
            sel = esp_sel[0]          # None | "__sem__" | nome da especialidade
            if sel is None:
                medicos_fil = []
            elif sel == "__sem__":
                medicos_fil = [m for m in todos_medicos
                               if not m.get("especialidade")]
            else:
                medicos_fil = [m for m in todos_medicos
                               if (m.get("especialidade") or "").upper() == sel.upper()]

            if not medicos_fil:
                lista_esp.controls.append(ft.Container(
                    content=ft.Text("Nenhum médico nesta especialidade.",
                                    size=12, color=MUT),
                    padding=ft.padding.symmetric(vertical=12),
                ))
            else:
                for m in medicos_fil:
                    crm = f"CRM {m['crm']}/{m['uf']}" if m.get("crm") else ""
                    foto = m.get("foto_drive_id", "")
                    avatar = ft.Image(
                        src=foto, width=40, height=40,
                        fit="cover", border_radius=8,
                    ) if foto else ft.Container(
                        content=ft.Icon("person_rounded", size=20, color=ROXO),
                        bgcolor=ft.Colors.with_opacity(0.13, ROXO), border_radius=8,
                        width=40, height=40,
                        alignment=ft.alignment.Alignment(0, 0),
                    )

                    def make_click(med):
                        def click(e): _abrir_ficha(med)
                        return click

                    lista_esp.controls.append(ft.Container(
                        content=ft.Row([
                            avatar,
                            ft.Column([
                                ft.Text(m["nome"], size=13, color=TXT,
                                        weight=ft.FontWeight.W_600),
                                ft.Text(crm, size=11, color=SEC),
                            ], spacing=2, expand=True),
                            ft.Container(
                                width=8, height=8,
                                bgcolor=VERD if m.get("ativo", 1) else MUT,
                                border_radius=4),
                            ft.Icon("chevron_right_rounded", size=14, color=MUT),
                        ], spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor=CARD, border_radius=8,
                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                        border=ft.Border(
                            top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                            left=ft.BorderSide(1, BD), right=ft.BorderSide(1, BD),
                        ),
                        on_click=make_click(m), ink=True,
                    ))
            try: page.update()
            except Exception: pass

        # ── campo de busca de especialidade ───────────────────
        tf_esp = ft.TextField(
            hint_text="Buscar especialidade...",
            prefix_icon="search_rounded",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            hint_style=ft.TextStyle(color=MUT),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, expand=True, height=42,
        )
        sugestoes_esp = ft.Column(spacing=4, visible=False)

        def _selecionar_esp(esp_id, nome):
            esp_sel[0] = esp_id
            esp_chip.content.controls[1].value = nome
            esp_chip.visible = True
            tf_esp.visible = False
            sugestoes_esp.controls.clear()
            sugestoes_esp.visible = False
            _renderizar_medicos()

        def _limpar_esp(e=None):
            esp_sel[0] = None
            esp_chip.visible = False
            tf_esp.value = ""
            tf_esp.visible = True
            sugestoes_esp.controls.clear()
            sugestoes_esp.visible = False
            lista_esp.controls.clear()
            try: page.update()
            except Exception: pass

        esp_chip.on_click = _limpar_esp

        def _filtrar_esp(e):
            termo = (tf_esp.value or "").strip().upper()
            sugestoes_esp.controls.clear()
            if not termo:
                sugestoes_esp.visible = False
                try: page.update()
                except Exception: pass
                return

            # opção "sem especialidade"
            opcoes = []
            if "SEM" in termo or "SEM ESPEC" in termo:
                opcoes.append({"id": "__sem__", "nome": "Sem especialidade informada",
                               "descricao": ""})

            matches = [e for e in especialidades if termo in e["nome"].upper()]
            opcoes += matches[:8]

            if not opcoes:
                sugestoes_esp.controls.append(ft.Container(
                    content=ft.Text("Nenhuma especialidade encontrada.",
                                    size=12, color=MUT),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                ))
                sugestoes_esp.visible = True
                try: page.update()
                except Exception: pass
                return

            for op in opcoes:
                cor_item = MUT if op["id"] == "__sem__" else AZUL
                icone_item = ("person_off_rounded"
                              if op["id"] == "__sem__"
                              else "local_hospital_rounded")
                desc = op.get("descricao") or ""
                def make_sel(o=op):
                    def sel(e):
                        _selecionar_esp(o["nome"], o["nome"])
                    return sel
                sugestoes_esp.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Icon(icone_item, size=13, color=cor_item),
                        ft.Column([
                            ft.Text(op["nome"], size=13, color=TXT),
                            ft.Text(desc, size=10, color=MUT) if desc else ft.Container(),
                        ], spacing=1, expand=True, tight=True),
                        ft.Icon("chevron_right_rounded", size=14, color=cor_item),
                    ], spacing=8),
                    bgcolor=CARD, border_radius=6,
                    padding=ft.padding.symmetric(horizontal=10, vertical=8),
                    border=ft.Border(
                        left=ft.BorderSide(2, cor_item),
                        top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                        right=ft.BorderSide(1, BD),
                    ),
                    on_click=make_sel(), ink=True,
                ))
            sugestoes_esp.visible = True
            try: page.update()
            except Exception: pass

        tf_esp.on_change = _filtrar_esp

        # atalho rápido "sem especialidade" sempre visível
        btn_sem = ft.Container(
            content=ft.Row([
                ft.Icon("person_off_rounded", size=13, color=MUT),
                ft.Text("Sem especialidade informada", size=12, color=MUT),
                ft.Container(expand=True),
                ft.Text(
                    str(sum(1 for m in todos_medicos
                            if not m.get("especialidade"))),
                    size=12, color=MUT, weight=ft.FontWeight.W_600),
            ], spacing=8),
            bgcolor=CARD, border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border=ft.Border(
                left=ft.BorderSide(2, MUT),
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                right=ft.BorderSide(1, BD),
            ),
            on_click=lambda e: _selecionar_esp("__sem__",
                                               "Sem especialidade informada"),
            ink=True,
        )

        return [
            esp_chip,
            tf_esp,
            sugestoes_esp,
            btn_sem,
            ft.Container(
                height=1, bgcolor=BD,
                margin=ft.margin.symmetric(vertical=4)),
            lista_esp,
        ]

    def _rebuild_conteudo():
        area_conteudo.controls.clear()
        if aba_ativa[0] == 0:
            carregar(txt_busca.value or "")
            area_conteudo.controls.extend(_conteudo_medicos())
        else:
            area_conteudo.controls.extend(_conteudo_especialidades())
        try: page.update()
        except Exception: pass

    def _abrir_ficha(medico):
        def _voltar():
            _mostrar_principal()

        wrapper.controls.clear()
        wrapper.controls.append(_tela_ficha_medico(page, medico, _voltar))
        try: page.update()
        except Exception: pass

    def _mostrar_principal():
        cabecalho = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Row([
                        ft.Icon("arrow_back_rounded", size=16),
                        ft.Text("Voltar", size=13),
                    ], spacing=4, tight=True),
                    padding=ft.padding.symmetric(horizontal=8, vertical=8),
                    ink=True,
                    on_click=lambda e: voltar_fn(),
                ),
                ft.Row([
                    ft.Icon("people_rounded", size=20, color=ROXO),
                    ft.Text("Médicos", size=18,
                            weight=ft.FontWeight.W_700, color=TXT),
                ], spacing=8, tight=True),
                ft.Container(expand=True),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.padding.symmetric(horizontal=16, vertical=14),
            border=ft.Border(bottom=ft.BorderSide(1, BD)),
        )

        corpo = ft.Column([
            cabecalho,
            ft.Container(content=barra_abas,
                         border=ft.Border(bottom=ft.BorderSide(1, BD))),
            ft.Container(
                content=area_conteudo,
                padding=ft.padding.all(16),
                expand=True,
            ),
        ], expand=True)

        try:
            larg = page.width or 800
        except Exception:
            larg = 800

        if larg > 500:
            conteudo_final = ft.Row([
                ft.Container(expand=True),
                ft.Container(content=corpo, width=480),
                ft.Container(expand=True),
            ], expand=True)
        else:
            conteudo_final = corpo

        wrapper.controls.clear()
        wrapper.controls.append(
            ft.Container(bgcolor=BG, expand=True, content=conteudo_final)
        )
        try: page.update()
        except Exception: pass

    _rebuild_abas()
    _rebuild_conteudo()
    _mostrar_principal()

    return wrapper
