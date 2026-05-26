# -*- coding: utf-8 -*-
"""
tela_compromissos.py — Koios Prontuario
Compromissos medicos: consultas, coletas, fisioterapia e outros.
Renomeado de tela_consultas_medicas; inclui tipo_compromisso e picker de clinica.
"""
import logging
import threading
import datetime
import json as _json
import flet as ft
from shared.layout import Layout
from shared.auth import IS_ANDROID
from dados.model_prontuario import (
    listar_consultas, salvar_consulta, listar_medicos,
    salvar_receita, listar_receitas,
    listar_clinicas, normalizar_data as _norm_data,
    listar_remedios, iniciar_periodo_uso, vincular_receita_remedio,
    listar_periodos_uso, total_dias_uso,
)

logger = logging.getLogger(__name__)

# ── Paleta ────────────────────────────────────────────────────
BG   = "#0D1117";  CARD = "#161B22";  BD  = "#21262D";  BD2 = "#30363D"
TXT  = "#E6EDF3";  SEC  = "#8B949E";  MUT = "#484F58"
AZUL = "#58A6FF";  VERD = "#3FB950";  LAR = "#F0883E"


def _flex_parse(s: str) -> "datetime.datetime | None":
    """Parse de data aceita YYYY-MM-DD e DD/MM/YYYY."""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime((s or "")[:10], fmt)
        except ValueError:
            pass
    return None


def _para_display(s: str | None) -> str:
    """Converte YYYY-MM-DD para DD/MM/YYYY para exibicao. DD/MM/YYYY passa sem alteracao."""
    if not s:
        return ""
    s = str(s).strip()
    if len(s) >= 10 and s[4] == "-":
        try:
            return datetime.datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            pass
    return s

AMAR = "#D29922";  VERM = "#DA3633";  ROXO = "#BC8CFF"

_LABEL_CLINICA_TIPO = {
    "clinica":      "Clinica / Consultorio",
    "laboratorio":  "Laboratorio",
    "fisioterapia": "Fisioterapia",
    "hospital":     "Hospital",
    "outro":        "Outro",
}

# Status do compromisso
CORES_STATUS = {
    "agendada":  (AZUL, "calendar_today_rounded"),
    "realizada": (VERD, "check_circle_outline_rounded"),
    "cancelada": (MUT,  "cancel_outlined_rounded"),
}

# Tipo do compromisso
TIPOS_COMP = {
    "consulta":    (AZUL, "event_note_rounded",        "Consulta Medica"),
    "coleta":      (AMAR, "science_rounded",           "Coleta Lab."),
    "fisioterapia":(VERD, "self_improvement_rounded",  "Fisioterapia"),
    "outro":       (MUT,  "event_rounded",             "Outro"),
}

# Label do campo medico por tipo de compromisso
_LABEL_PROF = {
    "consulta":    "MEDICO",
    "coleta":      "MEDICO SOLICITANTE",
    "fisioterapia":"FISIOTERAPEUTA",
    "outro":       "PROFISSIONAL",
}


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _campo(label, valor="", largura=None, multiline=False, min_lines=1,
           hint=None, keyboard=ft.KeyboardType.TEXT):
    kw = dict(
        label=label, value=valor or "",
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, multiline=multiline,
        min_lines=min_lines, keyboard_type=keyboard,
    )
    if hint:
        kw["hint_text"] = hint
        kw["hint_style"] = ft.TextStyle(color=MUT, size=11)
    if largura:
        kw["width"] = largura
    else:
        kw["expand"] = True
    return ft.TextField(**kw)


def _label_sec(texto, cor=MUT):
    return ft.Text(texto, size=10, color=cor, weight=ft.FontWeight.W_700)


def _badge_status(tipo):
    cor, icone = CORES_STATUS.get(tipo, (SEC, "help_outline_rounded"))
    return ft.Container(
        content=ft.Row([
            ft.Icon(icone, size=11, color=cor),
            ft.Text(tipo.capitalize(), size=10, color=cor, weight=ft.FontWeight.W_600),
        ], spacing=4, tight=True),
        bgcolor=f"{cor}18", border_radius=10,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
    )


def _badge_tipo(tipo_comp):
    cor, icone, label = TIPOS_COMP.get(tipo_comp, TIPOS_COMP["outro"])
    return ft.Container(
        content=ft.Row([
            ft.Icon(icone, size=11, color=cor),
            ft.Text(label, size=10, color=cor, weight=ft.FontWeight.W_600),
        ], spacing=4, tight=True),
        bgcolor=f"{cor}18", border_radius=10,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
    )


def _chip_status(tipo, selecionado, on_click):
    cor, icone = CORES_STATUS.get(tipo, (SEC, "help_outline_rounded"))
    ativo = tipo == selecionado
    return ft.Container(
        content=ft.Row([
            ft.Icon(icone, size=13, color=cor if ativo else MUT),
            ft.Text(tipo.capitalize(), size=12,
                    color=cor if ativo else MUT,
                    weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.W_400),
        ], spacing=5, tight=True),
        bgcolor=f"{cor}22" if ativo else BD,
        border_radius=20,
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        border=ft.border.all(1, cor if ativo else BD2),
        on_click=on_click,
    )


def _chip_tipo_comp(tipo, selecionado, on_click):
    cor, icone, label = TIPOS_COMP.get(tipo, TIPOS_COMP["outro"])
    ativo = tipo == selecionado
    return ft.Container(
        content=ft.Row([
            ft.Icon(icone, size=13, color=cor if ativo else MUT),
            ft.Text(label, size=12,
                    color=cor if ativo else MUT,
                    weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.W_400),
        ], spacing=5, tight=True),
        bgcolor=f"{cor}22" if ativo else BD,
        border_radius=20,
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        border=ft.border.all(1, cor if ativo else BD2),
        on_click=on_click,
    )


def _centralizar(corpo, page):
    try:
        larg = page.width or 800
    except Exception:
        larg = 800
    if larg > 500:
        return ft.Container(bgcolor=BG, expand=True, content=ft.Row([
            ft.Container(expand=True),
            ft.Container(content=corpo, width=480),
            ft.Container(expand=True),
        ], expand=True))
    return ft.Container(bgcolor=BG, expand=True, content=corpo)


def _agendar_alarme_windows(data_str, hora_str, descricao):
    import subprocess
    try:
        d = _flex_parse(data_str)
        if d is None:
            return False, "data invalida"
        data_win = d.strftime("%Y-%m-%d")
        hora_win = hora_str or "08:00"
        nome_tarefa = f"Koios_Compromisso_{data_win}_{hora_win.replace(':','')}"
        cmd = (
            f'schtasks /create /tn "{nome_tarefa}" /tr '
            f'"msg * Compromisso: {descricao}" '
            f'/sc once /d {data_win} /st {hora_win} /f'
        )
        subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return True, nome_tarefa
    except Exception as ex:
        return False, str(ex)


# ══════════════════════════════════════════════════════════════
# PICKER DE MÉDICO
# ══════════════════════════════════════════════════════════════

def _campo_medico(page, medicos, med_id_sel, valor_ini="", label_override=None, read_only=False):
    lbl = label_override or "MEDICO"

    med_chip = ft.Container(
        content=ft.Row([
            ft.Icon("person_rounded", size=13, color=AZUL),
            ft.Text("", size=12, color=AZUL, weight=ft.FontWeight.W_600),
            ft.Icon("close_rounded", size=13, color=AZUL),
        ], spacing=6, tight=True),
        bgcolor=f"{AZUL}18", border_radius=16,
        padding=ft.padding.symmetric(horizontal=10, vertical=5),
        visible=False,
    )

    tf = ft.TextField(
        hint_text="Buscar...",
        prefix_icon="search_rounded",
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        hint_style=ft.TextStyle(color=MUT),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, expand=True, height=42,
        visible=not bool(valor_ini),
    )
    sugestoes = ft.Column(spacing=4, visible=False)

    def _mostrar_chip(nome):
        med_chip.content.controls[1].value = nome
        med_chip.visible = True
        tf.visible = False
        sugestoes.controls.clear()
        sugestoes.visible = False
        try: page.update()
        except Exception: pass

    def _limpar(e=None):
        med_id_sel[0] = None
        med_chip.visible = False
        tf.value = ""
        tf.visible = True
        sugestoes.controls.clear()
        sugestoes.visible = False
        try: page.update()
        except Exception: pass

    if not read_only:
        med_chip.on_click = _limpar

    if valor_ini:
        _mostrar_chip(valor_ini)

    if read_only:
        tf.visible = False

    def _filtrar(e):
        if read_only:
            return
        termo = (tf.value or "").strip().upper()
        sugestoes.controls.clear()
        if not termo:
            sugestoes.visible = False
            try: page.update()
            except Exception: pass
            return
        matches = [m for m in medicos if termo in m["nome"].upper()][:8]
        if not matches:
            sugestoes.controls.append(ft.Container(
                content=ft.Text("Nenhum encontrado.", size=12, color=MUT),
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            ))
            sugestoes.visible = True
            try: page.update()
            except Exception: pass
            return
        for m in matches:
            esp = m.get("especialidade") or ""
            def make_sel(med=m):
                def sel(e):
                    med_id_sel[0] = str(med["id"])
                    _mostrar_chip(med["nome"])
                return sel
            sugestoes.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("person_rounded", size=13, color=AZUL),
                    ft.Column([
                        ft.Text(m["nome"], size=13, color=TXT),
                        ft.Text(esp, size=10, color=MUT) if esp else ft.Container(),
                    ], spacing=1, expand=True, tight=True),
                    ft.Icon("add_circle_outline_rounded", size=14, color=AZUL),
                ], spacing=8),
                bgcolor=CARD, border_radius=6,
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                border=ft.border.all(1, BD), on_click=make_sel(), ink=True,
            ))
        sugestoes.visible = True
        try: page.update()
        except Exception: pass

    tf.on_change = _filtrar

    lbl_txt = [ft.Text(lbl, size=10, color=MUT, weight=ft.FontWeight.W_700)]
    col = ft.Column([*lbl_txt, med_chip, tf, sugestoes], spacing=4)
    col._tf_medico   = tf
    col._chip_medico = med_chip
    col._limpar_fn   = _limpar
    return col, lbl_txt[0]


# ══════════════════════════════════════════════════════════════
# PICKER DE CLÍNICA
# ══════════════════════════════════════════════════════════════

def _campo_clinica(page, clinicas, clinica_id_sel, valor_ini="", read_only=False):
    cl_chip = ft.Container(
        content=ft.Row([
            ft.Icon("local_hospital_rounded", size=13, color=VERD),
            ft.Text("", size=12, color=VERD, weight=ft.FontWeight.W_600),
            ft.Icon("close_rounded", size=13, color=VERD),
        ], spacing=6, tight=True),
        bgcolor=f"{VERD}18", border_radius=16,
        padding=ft.padding.symmetric(horizontal=10, vertical=5),
        visible=False,
    )

    tf = ft.TextField(
        hint_text="Buscar clinica...",
        prefix_icon="search_rounded",
        bgcolor=CARD, border_color=BD2, focused_border_color=VERD,
        hint_style=ft.TextStyle(color=MUT),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, expand=True, height=42,
        visible=not bool(valor_ini),
    )
    sugestoes = ft.Column(spacing=4, visible=False)

    def _mostrar_chip(nome):
        cl_chip.content.controls[1].value = nome
        cl_chip.visible = True
        tf.visible = False
        sugestoes.controls.clear()
        sugestoes.visible = False
        try: page.update()
        except Exception: pass

    def _limpar(e=None):
        clinica_id_sel[0] = None
        cl_chip.visible = False
        tf.value = ""
        tf.visible = True
        sugestoes.controls.clear()
        sugestoes.visible = False
        try: page.update()
        except Exception: pass

    if not read_only:
        cl_chip.on_click = _limpar

    if valor_ini:
        _mostrar_chip(valor_ini)

    if read_only:
        tf.visible = False

    def _filtrar(e):
        if read_only:
            return
        termo = (tf.value or "").strip().upper()
        sugestoes.controls.clear()
        if not termo:
            sugestoes.visible = False
            try: page.update()
            except Exception: pass
            return
        matches = [c for c in clinicas if termo in c["nome"].upper()][:8]
        if not matches:
            sugestoes.controls.append(ft.Container(
                content=ft.Text("Nenhuma clinica encontrada.", size=12, color=MUT),
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            ))
            sugestoes.visible = True
            try: page.update()
            except Exception: pass
            return
        for c in matches:
            def make_sel(cl=c):
                def sel(e):
                    clinica_id_sel[0] = cl["id"]
                    _mostrar_chip(cl["nome"])
                return sel
            sugestoes.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("local_hospital_rounded", size=13, color=VERD),
                    ft.Column([
                        ft.Text(c["nome"], size=13, color=TXT),
                        ft.Text(_LABEL_CLINICA_TIPO.get(c["tipo"], "Outro"), size=10, color=MUT),
                    ], spacing=1, expand=True, tight=True),
                    ft.Icon("add_circle_outline_rounded", size=14, color=VERD),
                ], spacing=8),
                bgcolor=CARD, border_radius=6,
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                border=ft.border.all(1, BD), on_click=make_sel(), ink=True,
            ))
        sugestoes.visible = True
        try: page.update()
        except Exception: pass

    tf.on_change = _filtrar

    col = ft.Column([
        _label_sec("CLINICA / LOCAL"),
        cl_chip, tf, sugestoes,
    ], spacing=4)
    col._tf_clinica   = tf
    col._chip_clinica = cl_chip
    col._limpar_fn    = _limpar
    return col


# ══════════════════════════════════════════════════════════════
# TELA DE RECEITA (mantida sem alteracao)
# ══════════════════════════════════════════════════════════════

def _tela_receita(page, consulta, voltar_fn, pode_editar=True):
    import os as _os
    lay            = Layout(page)
    lista_rec      = ft.Column(spacing=8)
    txt_status_ia  = ft.Text("", size=12, color=SEC)
    progress_ia    = ft.ProgressBar(width=float("inf"), color=ROXO, bgcolor=BD, visible=False, height=3)
    col_vinculos   = ft.Column(spacing=6, visible=False)   # painel de vínculos pós-extração
    _receita_id_salva = [None]  # id da receita salva (preenchido em _salvar_receita)
    txt_instrucoes = _campo("Instrucoes de uso extraidas", multiline=True, min_lines=4)
    fotos_paths    = []        # lista de caminhos selecionados
    _editando      = [pode_editar]
    _houve_edicao  = [False]   # para sync ao sair

    # ── diretório de assets para fotos de receita ─────────────
    _ASSETS_DIR = _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
        "assets", "fotos_receitas"
    )

    def _copiar_para_assets(caminho_orig: str) -> str:
        """Copia foto para assets/fotos_receitas e retorna path relativo."""
        try:
            import shutil, time as _time
            _os.makedirs(_ASSETS_DIR, exist_ok=True)
            ext  = caminho_orig.rsplit(".", 1)[-1].lower() or "jpg"
            nome = f"rec_{int(_time.time() * 1000)}.{ext}"
            dest = _os.path.join(_ASSETS_DIR, nome)
            shutil.copy2(caminho_orig, dest)
            return dest
        except Exception as ex:
            logger.error("_copiar_para_assets: %s", ex)
            return caminho_orig

    # ── viewer ampliado com filtros ───────────────────────────
    def _abrir_viewer(foto_path: str):
        if not foto_path or not _os.path.exists(foto_path):
            return
        ov      = [None]
        src     = [foto_path]
        ocupado = [False]
        img_ctrl = ft.Image(src=src[0], width=300, height=380,
                            fit=ft.ImageFit.CONTAIN, border_radius=8)
        txt_st   = ft.Text("", size=10, color=SEC)

        def _fechar(e=None):
            if ov[0] in page.overlay:
                page.overlay.remove(ov[0])
            try: page.update()
            except Exception: pass

        def _aplicar(operacao):
            if ocupado[0]:
                return
            ocupado[0] = True
            txt_st.value = "Processando..."
            try: page.update()
            except Exception: pass
            def _run():
                try:
                    from PIL import Image as _PILImage
                    import time as _time, re as _re
                    path_abs = src[0]
                    img = _PILImage.open(path_abs)
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    if operacao == "rotate_cw":
                        img = img.rotate(-90, expand=True)
                    elif operacao == "rotate_ccw":
                        img = img.rotate(90, expand=True)
                    elif operacao == "flip_h":
                        img = img.transpose(_PILImage.FLIP_LEFT_RIGHT)
                    elif operacao == "flip_v":
                        img = img.transpose(_PILImage.FLIP_TOP_BOTTOM)
                    stem, ext = _os.path.splitext(path_abs)
                    stem_clean = _re.sub(r"_e\d+$", "", stem)
                    novo_abs = f"{stem_clean}_e{int(_time.time())}{ext or '.jpg'}"
                    img.save(novo_abs)
                    try:
                        if _os.path.abspath(path_abs) != _os.path.abspath(novo_abs):
                            _os.remove(path_abs)
                    except Exception: pass
                    src[0] = novo_abs
                    img_ctrl.src = novo_abs
                    txt_st.value = ""
                except ImportError:
                    txt_st.value = "Pillow nao instalado"
                except Exception as ex:
                    txt_st.value = f"Erro: {ex}"
                finally:
                    ocupado[0] = False
                try: page.update()
                except Exception: pass
            threading.Thread(target=_run, daemon=True).start()

        def _btn_ed(icone, label, cor, op):
            c = ft.Container(
                content=ft.Column([
                    ft.Icon(icone, size=20, color=cor),
                    ft.Text(label, size=9, color=cor),
                ], spacing=2, tight=True,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=68, height=54, border_radius=8, bgcolor=CARD, ink=True,
                border=ft.border.all(1, BD2),
            )
            c.on_click = lambda e, o=op: _aplicar(o)
            return c

        dlg = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Foto da receita", size=14, color=TXT,
                            weight=ft.FontWeight.W_700, expand=True),
                    ft.Container(
                        content=ft.Icon("close_rounded", size=18, color=SEC),
                        width=32, height=32, border_radius=6,
                        alignment=ft.alignment.center, ink=True, on_click=_fechar),
                ]),
                ft.Container(height=8),
                ft.Container(content=img_ctrl, alignment=ft.alignment.center),
                txt_st,
                ft.Container(height=10),
                ft.Row([
                    _btn_ed("rotate_left_rounded",  "Girar Esq", AZUL, "rotate_ccw"),
                    _btn_ed("rotate_right_rounded", "Girar Dir", AZUL, "rotate_cw"),
                    _btn_ed("flip_rounded",         "Espelhar H", VERD, "flip_h"),
                    _btn_ed("swap_vert_rounded",    "Espelhar V", VERD, "flip_v"),
                ], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
            ], spacing=4, tight=True,
               horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=CARD, border_radius=14, padding=ft.padding.all(20),
            border=ft.border.all(1, BD2), width=340,
            on_click=lambda e: None,
        )
        ov[0] = ft.Container(
            content=ft.Column([dlg],
                              alignment=ft.MainAxisAlignment.CENTER,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#CC000000", expand=True,
            alignment=ft.alignment.center,
        )
        ov[0].on_click = _fechar
        page.overlay.append(ov[0])
        try: page.update()
        except Exception: pass

    def _carregar_lista():
        lista_rec.controls.clear()
        recs = listar_receitas(consulta["id"])
        if not recs:
            lista_rec.controls.append(ft.Container(
                content=ft.Text("Nenhuma receita cadastrada.", color=SEC, size=13),
                padding=ft.padding.symmetric(vertical=12),
            ))
        for r in recs:
            foto = r.get("foto_path") or ""
            if foto and _os.path.exists(foto):
                thumb = ft.Container(
                    content=ft.Image(src=foto, width=52, height=52,
                                     fit=ft.ImageFit.COVER, border_radius=6),
                    width=52, height=52, border_radius=6,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ink=True, on_click=lambda e, p=foto: _abrir_viewer(p),
                )
            else:
                thumb = ft.Container(
                    content=ft.Icon("receipt_long_rounded", size=22, color=ROXO),
                    width=52, height=52, border_radius=6,
                    bgcolor=ft.Colors.with_opacity(0.12, ROXO),
                    alignment=ft.alignment.center,
                )
            lista_rec.controls.append(ft.Container(
                content=ft.Row([
                    thumb,
                    ft.Column([
                        ft.Text(r.get("nome_arquivo") or "Receita", size=13,
                                color=TXT, weight=ft.FontWeight.W_600),
                        ft.Text(r.get("observacoes") or "", size=11, color=SEC,
                                max_lines=2),
                    ], spacing=2, expand=True),
                    ft.Text(_para_display(r.get("data") or ""), size=11, color=MUT),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border=ft.border.all(1, BD),
            ))
        try: page.update()
        except Exception: pass

    # ── grid de previews das fotos ────────────────────────────
    fotos_col = ft.Column(spacing=6)

    def _rebuild_fotos():
        fotos_col.controls.clear()
        for idx, caminho in enumerate(fotos_paths):
            nome = caminho.replace("\\", "/").split("/")[-1]
            def _rm(e, i=idx):
                del fotos_paths[i]
                _rebuild_fotos()
                btn_extrair.visible = bool(fotos_paths)
                if not fotos_paths:
                    txt_status_ia.value = ""
                try: page.update()
                except Exception: pass
            fotos_col.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("image_rounded", size=13, color=ROXO),
                        ft.Text(nome, size=11, color=TXT, expand=True),
                        ft.Container(
                            content=ft.Icon("close_rounded", size=13, color=MUT),
                            padding=4, border_radius=4, ink=True, on_click=_rm,
                        ),
                    ], spacing=6),
                    ft.Image(src=caminho, border_radius=6,
                             width=300, fit=ft.ImageFit.CONTAIN),
                ], spacing=4, tight=True),
                bgcolor=CARD, border_radius=8,
                border=ft.border.all(1, BD),
                padding=ft.padding.all(8),
            ))
        try: page.update()
        except Exception: pass

    btn_extrair = ft.Container(
        content=ft.Row([
            ft.Icon("auto_awesome_rounded", size=15, color=ROXO),
            ft.Text("Extrair com IA", size=13, color=ROXO, weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        bgcolor=ft.Colors.with_opacity(0.12, ROXO),
        border=ft.border.all(1, ft.Colors.with_opacity(0.4, ROXO)),
        border_radius=8, ink=True, visible=False,
        padding=ft.padding.symmetric(horizontal=12, vertical=9),
    )

    def _selecionar_foto(e):
        def _picker():
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk(); root.withdraw()
                root.attributes("-topmost", True)
                caminhos = filedialog.askopenfilenames(
                    title="Fotos da receita (pode selecionar varias)",
                    filetypes=[("Imagens", "*.jpg *.jpeg *.png *.webp")],
                )
                root.destroy()
                if not caminhos:
                    return

                # Para cada foto: processa + mostra janela de confirmação
                from utils.image_processor import confirmar_processamento_documento
                processadas = []
                for c in caminhos:
                    page.pubsub.send_all({
                        "_tipo": "rec_foto_comp", "status": "processando",
                        "msg": f"Processando {_os.path.basename(c)}..."
                    })
                    try:
                        resultado = confirmar_processamento_documento(c, _ASSETS_DIR)
                        if resultado is not None:
                            processadas.append(resultado)
                        # None = cancelado pelo usuário — simplesmente ignora essa foto
                    except Exception as ex_proc:
                        logger.warning("[RECEITA] confirmacao falhou: %s — usando original", ex_proc)
                        processadas.append(c)  # fallback: original sem processar

                if processadas:
                    page.pubsub.send_all({"_tipo": "rec_foto_comp", "caminhos": processadas})

            except Exception as ex:
                page.pubsub.send_all({"_tipo": "rec_foto_comp", "erro": str(ex)})

        _sub = [False]
        def _on_foto(msg):
            if not isinstance(msg, dict) or msg.get("_tipo") != "rec_foto_comp":
                return
            if msg.get("status") == "processando":
                txt_status_ia.value = msg.get("msg", "Processando imagem...")
                txt_status_ia.color = AZUL
                try: page.update()
                except Exception: pass
                return
            if "erro" in msg:
                txt_status_ia.value = f"Erro: {msg['erro']}"
                txt_status_ia.color = VERM
            else:
                novos = [c for c in msg["caminhos"] if c not in fotos_paths]
                fotos_paths.extend(novos)
                _rebuild_fotos()
                btn_extrair.visible = True
                txt_status_ia.value = f"{len(fotos_paths)} foto(s) processada(s) — clique em Extrair com IA"
                txt_status_ia.color = SEC
            try: page.update()
            except Exception: pass

        if not _sub[0]:
            page.pubsub.subscribe(_on_foto)
            _sub[0] = True
        threading.Thread(target=_picker, daemon=True).start()

    def _extrair_ia(e):
        if not fotos_paths:
            txt_status_ia.value = "Selecione ao menos uma foto."
            try: page.update()
            except Exception: pass
            return
        n = len(fotos_paths)
        txt_status_ia.value = f"Analisando {n} foto(s) com IA..."
        txt_status_ia.color = AZUL
        btn_extrair.disabled = True
        progress_ia.visible = True
        try: page.update()
        except Exception: pass

        def _analisar():
            try:
                import base64
                from utils.claudia_engine import get_client
                MIME = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                        "png": "image/png", "webp": "image/webp"}
                content = []
                for caminho in fotos_paths:
                    with open(caminho, "rb") as f:
                        img_b64 = base64.b64encode(f.read()).decode()
                    ext  = caminho.rsplit(".", 1)[-1].lower()
                    mime = MIME.get(ext, "image/jpeg")
                    content.append({"type": "image", "source": {
                        "type": "base64", "media_type": mime, "data": img_b64}})
                content.append({"type": "text", "text": (
                    f"Estas sao {n} foto(s) de uma receita medica (podem ser frente e verso "
                    "ou paginas diferentes da mesma receita). "
                    "Extraia e liste TODOS os medicamentos prescritos com: "
                    "nome, dosagem, frequencia e duracao. "
                    "Formato: um por linha, ex:\n"
                    "• Amoxicilina 500mg — 1 capsula de 8 em 8h por 7 dias\n"
                    "Se nao conseguir ler algum campo, use '?'. "
                    "Responda apenas a lista consolidada, sem introducao."
                )})
                client = get_client()
                resp = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1500,
                    messages=[{"role": "user", "content": content}],
                )
                texto = "".join(b.text for b in resp.content if hasattr(b, "text"))
                page.pubsub.send_all({"_tipo": "rec_ia_comp", "texto": texto.strip()})
            except Exception as ex:
                logger.error("_extrair_ia receita: %s", ex)
                page.pubsub.send_all({"_tipo": "rec_ia_comp", "erro": str(ex)[:100]})
            finally:
                btn_extrair.disabled = False
                progress_ia.visible  = False

        _sub2 = [False]
        def _on_ia(msg):
            if not isinstance(msg, dict) or msg.get("_tipo") != "rec_ia_comp":
                return
            if "erro" in msg:
                txt_status_ia.value = f"Erro IA: {msg['erro']}"
                txt_status_ia.color = VERM
                try: page.update()
                except Exception: pass
                return

            txt_instrucoes.value = msg["texto"]
            txt_status_ia.value  = "Extracao concluida — revise e salve"
            txt_status_ia.color  = VERD

            # Montar painel de vínculo com remédios cadastrados
            _montar_vinculos(msg["texto"])
            try: page.update()
            except Exception: pass

        def _montar_vinculos(texto_extraido: str):
            """Sugere vínculos entre nomes extraídos pela IA e remédios cadastrados."""
            col_vinculos.controls.clear()
            col_vinculos.visible = False

            remedios_cad = listar_remedios(so_ativos=False)
            if not remedios_cad:
                return

            # Identificar nomes de remédios no texto extraído (linhas com •)
            nomes_extraidos = []
            for linha in texto_extraido.splitlines():
                linha = linha.strip().lstrip("•- ").strip()
                if linha:
                    # Pegar só a parte antes de números/dosagem
                    partes = linha.split()
                    if partes:
                        nomes_extraidos.append(partes[0].lower())

            if not nomes_extraidos:
                return

            # Match fuzzy simples: nome do remédio cadastrado contém alguma palavra extraída
            sugestoes = []
            for rem in remedios_cad:
                nome_rem = (rem.get("nome") or "").lower()
                prin_rem = (rem.get("principio_ativo") or "").lower()
                for ne in nomes_extraidos:
                    if len(ne) >= 4 and (ne in nome_rem or ne in prin_rem or nome_rem.startswith(ne)):
                        sugestoes.append(rem)
                        break

            if not sugestoes:
                return

            # Montar UI
            col_vinculos.controls.append(
                ft.Container(height=1, bgcolor=BD, margin=ft.margin.symmetric(vertical=4))
            )
            col_vinculos.controls.append(
                _label_sec("VINCULAR A REMEDIOS CADASTRADOS", VERD)
            )
            col_vinculos.controls.append(
                ft.Text("Ao salvar a receita, os vínculos marcados serão criados automaticamente.",
                        size=11, color=SEC)
            )

            _checks = {}  # remedio_id → ft.Checkbox

            for rem in sugestoes:
                rid    = rem["id"]
                nome   = rem.get("nome", "")
                dos    = rem.get("dosagem", "")
                periodos = listar_periodos_uso(rid)
                total    = total_dias_uso(rid)
                ativo_agora = any(p["ativo"] for p in periodos)

                # Info de uso acumulado
                if periodos:
                    ultimo = periodos[0]
                    if ativo_agora:
                        info_uso = f"Em uso há {ultimo['dias_uso']} dias · {total} dias acumulados"
                        cor_info = VERD
                    else:
                        info_uso = f"Suspenso · {total} dias acumulados"
                        cor_info = AMAR
                else:
                    info_uso = "Sem histórico de uso"
                    cor_info = SEC

                cb = ft.Checkbox(value=True, label="", active_color=VERD)
                _checks[rid] = cb

                col_vinculos.controls.append(
                    ft.Container(
                        content=ft.Row([
                            cb,
                            ft.Column([
                                ft.Text(f"{nome}  {dos}".strip(), size=13, color=TXT,
                                        weight=ft.FontWeight.W_500),
                                ft.Text(info_uso, size=11, color=cor_info),
                            ], spacing=2, expand=True),
                        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor=ft.Colors.with_opacity(0.06, VERD),
                        border=ft.border.all(1, ft.Colors.with_opacity(0.25, VERD)),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    )
                )

            col_vinculos.visible = True

            # Guardar checks para uso no _salvar_receita
            col_vinculos._checks = _checks

        if not _sub2[0]:
            page.pubsub.subscribe(_on_ia)
            _sub2[0] = True
        threading.Thread(target=_analisar, daemon=True).start()

    btn_extrair.on_click = _extrair_ia

    def _salvar_receita(e):
        if not fotos_paths and not txt_instrucoes.value.strip():
            txt_status_ia.value = "Adicione uma foto ou instrucoes."
            try: page.update()
            except Exception: pass
            return
        obs = txt_instrucoes.value.strip() or None
        if fotos_paths:
            for caminho in fotos_paths:
                # Se já está em _ASSETS_DIR (processado pelo image_processor), não re-copiar
                if _os.path.normpath(caminho).startswith(_os.path.normpath(_ASSETS_DIR)):
                    foto_local = caminho
                else:
                    foto_local = _copiar_para_assets(caminho)
                drive_id   = None
                nome_arq   = caminho.replace("\\", "/").split("/")[-1]
                try:
                    from shared.drive_connector import upload_foto_medico
                    drive_id = upload_foto_medico(foto_local)
                except Exception as ex:
                    logger.error("upload receita Drive: %s", ex)
                rid = salvar_receita({
                    "consulta_id":   consulta["id"],
                    "medico_id":     consulta.get("medico_id"),
                    "drive_file_id": drive_id,
                    "nome_arquivo":  nome_arq,
                    "data":          datetime.date.today().isoformat(),
                    "observacoes":   obs,
                    "foto_path":     foto_local,
                })
                _receita_id_salva[0] = rid
        else:
            rid = salvar_receita({
                "consulta_id":   consulta["id"],
                "medico_id":     consulta.get("medico_id"),
                "drive_file_id": None,
                "nome_arquivo":  "",
                "data":          datetime.date.today().isoformat(),
                "observacoes":   obs,
                "foto_path":     None,
            })
            _receita_id_salva[0] = rid
        _houve_edicao[0] = True

        # Processar vínculos com remédios se houver
        checks = getattr(col_vinculos, "_checks", {})
        if checks and _receita_id_salva[0]:
            hoje = datetime.date.today().isoformat()
            for rid, cb in checks.items():
                if cb.value:
                    try:
                        vincular_receita_remedio(_receita_id_salva[0], rid, hoje)
                    except Exception as ex:
                        logger.warning("[RECEITA] vincular remedio %s: %s", rid, ex)

        fotos_paths.clear()
        txt_instrucoes.value = ""
        txt_status_ia.value  = "Receita(s) salva(s)!"
        txt_status_ia.color  = VERD
        btn_extrair.visible  = False
        col_vinculos.controls.clear()
        col_vinculos.visible = False
        _rebuild_fotos()
        _carregar_lista()

    _carregar_lista()

    secao_adicionar = ft.Column([
        ft.Container(height=1, bgcolor=BD, margin=ft.margin.symmetric(vertical=8)),
        _label_sec("ADICIONAR RECEITA", ROXO),
        ft.Container(
            content=ft.Row([
                ft.Icon("add_photo_alternate_rounded", size=15, color=ROXO),
                ft.Text("Adicionar foto(s) da receita", size=12, color=ROXO),
            ], spacing=6, tight=True),
            bgcolor=ft.Colors.with_opacity(0.12, ROXO),
            border=ft.border.all(1, ft.Colors.with_opacity(0.4, ROXO)),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=12, vertical=9),
            on_click=_selecionar_foto,
        ),
        fotos_col,
        btn_extrair,
        progress_ia,
        txt_status_ia,
        _label_sec("MEDICAMENTOS EXTRAIDOS / OBSERVACOES"),
        txt_instrucoes,
        col_vinculos,
        ft.Container(
            content=ft.Row([
                ft.Icon("save_rounded", size=15, color=BG),
                ft.Text("Salvar Receita", size=13, color=BG, weight=ft.FontWeight.W_600),
            ], spacing=6, tight=True),
            bgcolor=AZUL, border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            on_click=_salvar_receita,
        ),
    ], spacing=10, visible=_editando[0])

    btn_editar_rec = ft.Container(
        content=ft.Row([
            ft.Icon("edit_rounded", size=15, color=ROXO),
            ft.Text("Editar", size=13, color=ROXO),
        ], spacing=5, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8, bgcolor=ft.Colors.with_opacity(0.12, ROXO), ink=True,
        visible=not _editando[0],
    )

    def _ativar_edicao_rec(e=None):
        _editando[0] = True
        secao_adicionar.visible = True
        btn_editar_rec.visible = False
        try: page.update()
        except Exception: pass

    btn_editar_rec.on_click = _ativar_edicao_rec

    # ── sync ao sair ──────────────────────────────────────────
    _handler_ant = [None]

    def _sync_e_sair(destino_fn):
        if not _houve_edicao[0]:
            destino_fn()
            return
        _desreg_hw()
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
            bgcolor="#DD000000", expand=True, alignment=ft.alignment.center,
        )
        page.overlay.append(ov)
        try: page.update()
        except Exception: pass
        def _run():
            try:
                from backup.drive_backup import fazer_backup
                fazer_backup(forcar=True)
            except Exception as ex:
                logger.warning("[receitas] sync erro: %s", ex)
            finally:
                if ov in page.overlay: page.overlay.remove(ov)
                try: page.update()
                except Exception: pass
                destino_fn()
        threading.Thread(target=_run, daemon=True).start()

    def _voltar(e=None):
        _sync_e_sair(voltar_fn)

    def _reg_hw():
        _handler_ant[0] = page.on_keyboard_event
        def _on_hw(e):
            if e.key == "Escape": _voltar()
        page.on_keyboard_event = _on_hw

    def _desreg_hw():
        page.on_keyboard_event = _handler_ant[0]

    cabecalho = lay.criar_cabecalho(
        "Receitas", _voltar,
        icone_titulo="receipt_long_rounded",
        cor_titulo=ROXO,
        acoes=[btn_editar_rec],
    )

    area = ft.Column([
        _label_sec("RECEITAS CADASTRADAS"),
        lista_rec,
        secao_adicionar,
        ft.Container(height=20),
    ], spacing=10, scroll=ft.ScrollMode.AUTO)

    corpo = ft.Column([
        ft.Container(height=lay.spacer_topo, bgcolor=BG),
        cabecalho,
        ft.Container(content=area, padding=ft.padding.all(16), expand=True),
    ], expand=True, spacing=0)

    _reg_hw()
    return _centralizar(corpo, page)


# ══════════════════════════════════════════════════════════════
# FORMULÁRIO DE COMPROMISSO
# ══════════════════════════════════════════════════════════════

def _tela_ficha_compromisso(page, consulta, voltar_fn, medicos, clinicas, receitas_fn=None):
    lay           = Layout(page)
    is_new        = consulta is None
    _modo_edicao  = [is_new]
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
                logger.warning("[compromissos] sync erro: %s", ex)
            finally:
                _status_banco[0] = "normal"
                if ov in page.overlay: page.overlay.remove(ov)
                try: page.update()
                except Exception: pass
                if apos_sync_fn: apos_sync_fn()
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
            if e.key == "Escape": _sair(voltar_fn)
        page.on_keyboard_event = _on_hw

    def _desregistrar_voltar_hw():
        page.on_keyboard_event = _handler_ant[0]

    med_map       = {str(m["id"]): m["nome"] for m in medicos}
    med_id_sel    = [str(consulta["medico_id"])
                     if consulta and consulta.get("medico_id") else None]
    clinica_id_sel = [consulta.get("clinica_id")
                      if consulta else None]
    valor_med_ini = med_map.get(med_id_sel[0], "") if med_id_sel[0] else ""
    valor_cl_ini  = (consulta.get("clinica_nome") or "") if consulta else ""

    tipo_comp_sel = [
        consulta.get("tipo_compromisso", "consulta") if consulta else "consulta"
    ]

    from shared.date_field import campo_data as _campo_data

    ro = not _modo_edicao[0]

    col_medico, lbl_medico = _campo_medico(
        page, medicos, med_id_sel, valor_med_ini,
        label_override=_LABEL_PROF.get(tipo_comp_sel[0], "PROFISSIONAL"),
        read_only=ro,
    )
    col_clinica = _campo_clinica(page, clinicas, clinica_id_sel, valor_cl_ini, read_only=ro)

    row_data, f_data = _campo_data(
        page,
        label="Data",
        value=consulta["data"] if consulta else "",
        obrigatorio=True,
        cor_acento=AZUL,
        largura=160,
    )
    f_data.read_only = ro

    f_hora = _campo("Hora", consulta.get("hora","") if consulta else "",
                    hint="HH:MM", largura=90)
    def _mask_hora(e):
        raw = "".join(c for c in (f_hora.value or "") if c.isdigit())[:4]
        out = (raw[:2] + ":" + raw[2:]) if len(raw) >= 3 else raw
        if f_hora.value != out:
            f_hora.value = out
            try: f_hora.update()
            except Exception: pass
    f_hora.on_change = _mask_hora

    f_obs  = _campo("Observacoes", consulta.get("observacoes","") if consulta else "",
                    multiline=True, min_lines=3)
    for _f in [f_hora, f_obs]:
        _f.read_only = ro

    # ── Pauta ───────────────────────────────────────────────
    _pauta_raw = consulta.get("pauta", "[]") if consulta else "[]"
    try:
        _pauta_lista = _json.loads(_pauta_raw) if isinstance(_pauta_raw, str) else (_pauta_raw or [])
    except Exception:
        _pauta_lista = []
    pauta_itens = list(_pauta_lista)

    f_novo_item = _campo("Adicionar item a pauta...", largura=None)
    pauta_col   = ft.Column(spacing=6)

    def _rebuild_pauta():
        pauta_col.controls.clear()
        em_ro = not _modo_edicao[0]
        for idx, item in enumerate(pauta_itens):
            def _rm(e, i=idx):
                del pauta_itens[i]; _rebuild_pauta()
            btn_rm = ft.Container(
                content=ft.Icon("close_rounded", size=13, color=MUT),
                padding=4, border_radius=4, ink=True, on_click=_rm,
                visible=not em_ro,
            )
            pauta_col.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("check_circle_outline_rounded", size=14, color=AZUL),
                    ft.Text(item, size=12, color=TXT, expand=True),
                    btn_rm,
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD, border=ft.border.all(1, BD), border_radius=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
            ))
        if not pauta_itens:
            pauta_col.controls.append(ft.Text("Nenhum item adicionado.", size=11, color=MUT))
        try: page.update()
        except Exception: pass

    def _add_item(e=None):
        txt = f_novo_item.value.strip()
        if not txt: return
        pauta_itens.append(txt); f_novo_item.value = ""; _rebuild_pauta()

    f_novo_item.on_submit = _add_item
    btn_add_item = ft.Container(
        content=ft.Row([
            ft.Icon("add_rounded", size=14, color=AZUL),
            ft.Text("Adicionar item", size=12, color=AZUL),
        ], spacing=4, alignment=ft.MainAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=10, vertical=10),
        border_radius=8, bgcolor=ft.Colors.with_opacity(0.12, AZUL),
        border=ft.border.all(1, ft.Colors.with_opacity(0.3, AZUL)), ink=True,
    )
    btn_add_item.on_click = _add_item
    row_nova_pauta = ft.Row([f_novo_item, btn_add_item], spacing=8, visible=not ro)
    _rebuild_pauta()

    # ── Chips de tipo_compromisso ────────────────────────────
    chips_tipo_comp = ft.Row(spacing=8, wrap=True)

    def _rebuild_chips_tipo():
        chips_tipo_comp.controls.clear()
        for tp in ["consulta", "coleta", "fisioterapia", "outro"]:
            def _on(e, t=tp):
                if not _modo_edicao[0]:
                    return
                tipo_comp_sel[0] = t
                lbl_medico.value = _LABEL_PROF.get(t, "PROFISSIONAL")
                _rebuild_chips_tipo()
            chips_tipo_comp.controls.append(_chip_tipo_comp(tp, tipo_comp_sel[0], _on))
        try: page.update()
        except Exception: pass

    # ── Chips de status ──────────────────────────────────────
    status_sel = [consulta.get("tipo","agendada") if consulta else "agendada"]
    chips_status = ft.Row(spacing=8)

    def _rebuild_chips_status():
        chips_status.controls.clear()
        for t in ["agendada", "realizada", "cancelada"]:
            def _on(e, tp=t):
                if not _modo_edicao[0]:
                    return
                status_sel[0] = tp; _rebuild_chips_status()
            chips_status.controls.append(_chip_status(t, status_sel[0], _on))
        try: page.update()
        except Exception: pass

    txt_erro   = ft.Text("", color=VERM, size=12)
    txt_alarme = ft.Text("", size=11, color=VERD)

    def _agendar(e):
        data = f_data.value.strip()
        if not data:
            txt_alarme.value = "Informe a data primeiro."
            try: page.update()
            except Exception: pass
            return
        hora     = f_hora.value.strip() or "08:00"
        med_nome = med_map.get(med_id_sel[0], "") if med_id_sel[0] else ""
        _, _, label_t = TIPOS_COMP.get(tipo_comp_sel[0], TIPOS_COMP["outro"])
        desc = med_nome or label_t
        ok, info = _agendar_alarme_windows(data, hora, desc)
        txt_alarme.value = (f"Alarme: {data} as {hora}" if ok else f"Erro: {info}")
        txt_alarme.color = VERD if ok else LAR
        try: page.update()
        except Exception: pass

    def _salvar(e):
        if not f_data.value.strip():
            txt_erro.value = "Data e obrigatoria."
            try: page.update()
            except Exception: pass
            return
        salvar_consulta({
            "id":               consulta["id"] if consulta else None,
            "medico_id":        int(med_id_sel[0]) if med_id_sel[0] else None,
            "data":             _norm_data(f_data.value.strip()),
            "hora":             f_hora.value.strip() or None,
            "tipo":             status_sel[0],
            "tipo_compromisso": tipo_comp_sel[0],
            "clinica_id":       clinica_id_sel[0],
            "observacoes":      f_obs.value.strip() or None,
            "pauta":            pauta_itens,
        })
        _status_banco[0] = "em_edicao"
        _sync(voltar_fn)

    def _ativar_edicao(e=None):
        _modo_edicao[0] = True
        f_data.read_only = False
        for _f in [f_hora, f_obs]:
            _f.read_only = False
        # reativa médico
        col_medico._tf_medico.visible   = not bool(med_id_sel[0])
        col_medico._chip_medico.on_click = col_medico._limpar_fn
        # reativa clínica
        col_clinica._tf_clinica.visible   = not bool(clinica_id_sel[0])
        col_clinica._chip_clinica.on_click = col_clinica._limpar_fn
        # reativa pauta
        row_nova_pauta.visible = True
        _rebuild_pauta()
        btn_salvar.visible = True
        btn_editar.visible = False
        try: page.update()
        except Exception: pass

    _rebuild_chips_tipo()
    _rebuild_chips_status()

    titulo = "Novo Compromisso" if is_new else "Compromisso"

    btn_salvar = ft.Container(
        content=ft.Row([
            ft.Icon("save_rounded", size=15, color=BG),
            ft.Text("Salvar", size=13, color=BG, weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        bgcolor=AZUL, border_radius=8, ink=True,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        visible=is_new,
    )
    btn_salvar.on_click = _salvar

    btn_editar = ft.Container(
        content=ft.Row([
            ft.Icon("edit_rounded", size=15, color=AZUL),
            ft.Text("Editar", size=13, color=AZUL),
        ], spacing=5, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8, bgcolor=ft.Colors.with_opacity(0.12, AZUL), ink=True,
        visible=not is_new,
    )
    btn_editar.on_click = _ativar_edicao

    cabecalho = lay.criar_cabecalho(
        titulo, lambda e=None: _sair(voltar_fn),
        icone_titulo="event_note_rounded",
        cor_titulo=AZUL,
        acoes=[btn_editar, btn_salvar],
    )

    corpo = ft.Column([
        ft.Container(height=lay.spacer_topo, bgcolor=BG),
        cabecalho,
        ft.Container(
            content=ft.Column([
                _label_sec("TIPO DE COMPROMISSO"),
                chips_tipo_comp,
                ft.Container(height=4),
                col_medico,
                ft.Container(height=4),
                col_clinica,
                ft.Container(height=4),
                _label_sec("DATA E HORA"),
                ft.Row([row_data, f_hora], spacing=8),
                ft.Container(height=4),
                _label_sec("STATUS"),
                chips_status,
                ft.Container(height=4),
                _label_sec("ITENS A TRATAR"),
                row_nova_pauta,
                pauta_col,
                ft.Container(height=4),
                _label_sec("OBSERVACOES"),
                f_obs,
                ft.Container(height=8),
                ft.Container(
                    content=ft.Row([
                        ft.Icon("alarm_add_rounded", size=16, color=AMAR),
                        ft.Text("Agendar Alarme", size=13, color=AMAR),
                    ], spacing=6, tight=True),
                    bgcolor=ft.Colors.with_opacity(0.12, AMAR),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.4, AMAR)),
                    border_radius=8, ink=True,
                    padding=ft.padding.symmetric(horizontal=16, vertical=10),
                    on_click=_agendar,
                    visible=not IS_ANDROID,
                ),
                txt_alarme,
                *([] if not receitas_fn else [
                    ft.Container(
                        content=ft.Row([
                            ft.Icon("receipt_long_rounded", size=15, color=ROXO),
                            ft.Text("Ver Receitas", size=13, color=ROXO),
                        ], spacing=6, tight=True),
                        bgcolor=ft.Colors.with_opacity(0.12, ROXO),
                        border=ft.border.all(1, ft.Colors.with_opacity(0.4, ROXO)),
                        border_radius=8, ink=True,
                        padding=ft.padding.symmetric(horizontal=16, vertical=10),
                        on_click=lambda e: receitas_fn(_modo_edicao[0]),
                    ),
                ]),
                txt_erro,
                ft.Container(height=20),
            ], spacing=8, scroll=ft.ScrollMode.AUTO),
            padding=ft.padding.all(16),
            expand=True,
        ),
    ], expand=True, spacing=0)

    _registrar_voltar_hw()
    return _centralizar(corpo, page)


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL
# ══════════════════════════════════════════════════════════════

def criar_tela_compromissos(page: ft.Page, voltar_fn):
    lay      = Layout(page)
    medicos  = listar_medicos(so_ativos=True)
    clinicas = listar_clinicas(so_ativas=True)

    ABAS = [
        (0, "event_note_rounded",           "Todos",       AZUL),
        (1, "calendar_today_rounded",        "Agendados",   AZUL),
        (2, "check_circle_outline_rounded",  "Realizados",  VERD),
        (3, "cancel_outlined_rounded",       "Cancelados",  MUT),
    ]
    FILTROS = [None, "agendada", "realizada", "cancelada"]
    aba_ativa = [0]

    barra_abas    = ft.Row(spacing=0)
    area_conteudo = ft.Column(spacing=8, expand=True, scroll=ft.ScrollMode.AUTO)
    wrapper       = ft.Column(expand=True, spacing=0)
    lista         = ft.Column(spacing=8)
    hoje          = datetime.date.today()

    def _rebuild_abas():
        barra_abas.controls.clear()
        for idx, icone, label, cor in ABAS:
            ativo = idx == aba_ativa[0]
            def _click(e, i=idx):
                aba_ativa[0] = i
                _rebuild_abas(); _carregar(); _rebuild_conteudo()
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

    def _carregar():
        lista.controls.clear()
        filtro    = FILTROS[aba_ativa[0]]
        registros = listar_consultas(tipo=filtro)

        if not registros:
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("event_busy_rounded", size=40, color=MUT),
                    ft.Text("Nenhum compromisso cadastrado.", color=SEC, size=13),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=40, alignment=ft.alignment.Alignment(0, 0),
            ))
            try: page.update()
            except Exception: pass
            return

        for c in registros:
            cor_st, icone_st = CORES_STATUS.get(c["tipo"], (SEC, "help_outline_rounded"))
            cor_tc, icone_tc, label_tc = TIPOS_COMP.get(
                c.get("tipo_compromisso","consulta"), TIPOS_COMP["consulta"])

            info_data = ""
            try:
                _dt   = _flex_parse(c["data"])
                dt    = _dt.date() if _dt else None
                if dt is None:
                    raise ValueError("data invalida")
                delta = (dt - hoje).days
                if c["tipo"] == "agendada":
                    if delta == 0:   info_data = "Hoje!"
                    elif delta == 1: info_data = "Amanha"
                    elif delta > 0:  info_data = f"Em {delta} dias"
                    else:            info_data = f"Ha {abs(delta)} dias"
            except Exception:
                pass

            prof_label = c.get("medico") or ""
            local_label = (c.get("clinica_nome") or c.get("local") or "Local nao informado")

            def _make_ficha(cons):
                def _click(e): _abrir_ficha(cons)
                return _click

            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            content=ft.Icon(icone_tc, size=20, color=cor_tc),
                            bgcolor=f"{cor_tc}18", border_radius=10,
                            width=40, height=40,
                            alignment=ft.alignment.Alignment(0, 0),
                        ),
                        ft.Column([
                            ft.Text(prof_label or label_tc, size=14, color=TXT,
                                    weight=ft.FontWeight.W_600),
                            ft.Text(c.get("especialidade") or label_tc,
                                    size=11, color=cor_tc),
                        ], spacing=1, expand=True),
                        _badge_status(c["tipo"]),
                    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row([
                        ft.Icon("calendar_today_rounded", size=12, color=MUT),
                        ft.Text(f"{c['data']}  {c.get('hora') or ''}", size=12, color=SEC),
                        ft.Container(expand=True),
                        ft.Text(info_data, size=11,
                                color=AMAR if info_data in ("Hoje!", "Amanha") else MUT),
                    ], spacing=6),
                    ft.Row([
                        ft.Icon("location_on_outlined_rounded", size=12, color=MUT),
                        ft.Text(local_label, size=11, color=SEC, expand=True),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon("edit_rounded", size=13, color=MUT),
                                ft.Text("Editar", size=11, color=MUT),
                            ], spacing=4, tight=True),
                            padding=ft.padding.symmetric(horizontal=8, vertical=8),
                            ink=True, on_click=_make_ficha(c),
                        ),
                    ], spacing=4),
                ], spacing=8),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                border=ft.Border(
                    left=ft.BorderSide(2, cor_tc),
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
            ))
        try: page.update()
        except Exception: pass

    def _rebuild_conteudo():
        area_conteudo.controls.clear()
        area_conteudo.controls.append(lista)
        try: page.update()
        except Exception: pass

    def _abrir_receitas(consulta, voltar_para_ficha=False, pode_editar=True):
        def _voltar():
            if voltar_para_ficha:
                _abrir_ficha(consulta)
            else:
                _carregar(); _mostrar_principal()
        wrapper.controls.clear()
        wrapper.controls.append(_tela_receita(page, consulta, _voltar, pode_editar=pode_editar))
        try: page.update()
        except Exception: pass

    def _abrir_ficha(consulta):
        def _voltar():
            _carregar(); _mostrar_principal()

        rec_fn = None if consulta is None else (
            lambda pode, cons=consulta: _abrir_receitas(cons, voltar_para_ficha=True, pode_editar=pode)
        )
        wrapper.controls.clear()
        wrapper.controls.append(
            _tela_ficha_compromisso(page, consulta, _voltar, medicos, clinicas,
                                    receitas_fn=rec_fn))
        try: page.update()
        except Exception: pass

    def _mostrar_principal():
        btn_nova = ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=16, color=BG),
                ft.Text("+ Novo", size=13, color=BG, weight=ft.FontWeight.W_600),
            ], spacing=6, tight=True),
            bgcolor=AZUL, border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            ink=True,
        )
        btn_nova.on_click = lambda e: _abrir_ficha(None)

        cabecalho = lay.criar_cabecalho(
            "Compromissos", voltar_fn,
            icone_titulo="event_note_rounded",
            cor_titulo=AZUL,
            acoes=[btn_nova],
        )

        corpo = ft.Column([
            ft.Container(height=lay.spacer_topo, bgcolor=BG),
            cabecalho,
            ft.Container(content=barra_abas,
                         border=ft.Border(bottom=ft.BorderSide(1, BD))),
            ft.Container(content=area_conteudo, padding=ft.padding.all(16), expand=True),
        ], expand=True, spacing=0)

        wrapper.controls.clear()
        wrapper.controls.append(ft.Container(bgcolor=BG, expand=True, content=corpo))
        try: page.update()
        except Exception: pass

    _rebuild_abas()
    _carregar()
    _rebuild_conteudo()
    _mostrar_principal()

    return wrapper
