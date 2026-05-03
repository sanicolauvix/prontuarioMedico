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
from dados.model_prontuario import (
    listar_consultas, salvar_consulta, listar_medicos,
    salvar_receita, listar_receitas,
    listar_clinicas,
)

logger = logging.getLogger(__name__)

# ── Paleta ────────────────────────────────────────────────────
BG   = "#0D1117";  CARD = "#161B22";  BD  = "#21262D";  BD2 = "#30363D"
TXT  = "#E6EDF3";  SEC  = "#8B949E";  MUT = "#484F58"
AZUL = "#58A6FF";  VERD = "#3FB950";  LAR = "#F0883E"
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
        d = datetime.datetime.strptime(data_str, "%d/%m/%Y")
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

def _campo_medico(page, medicos, med_id_sel, valor_ini="", label_override=None):
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

    med_chip.on_click = _limpar

    if valor_ini:
        _mostrar_chip(valor_ini)

    def _filtrar(e):
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
    return col, lbl_txt[0]


# ══════════════════════════════════════════════════════════════
# PICKER DE CLÍNICA
# ══════════════════════════════════════════════════════════════

def _campo_clinica(page, clinicas, clinica_id_sel, valor_ini=""):
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

    cl_chip.on_click = _limpar

    if valor_ini:
        _mostrar_chip(valor_ini)

    def _filtrar(e):
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
    return col


# ══════════════════════════════════════════════════════════════
# TELA DE RECEITA (mantida sem alteracao)
# ══════════════════════════════════════════════════════════════

def _tela_receita(page, consulta, voltar_fn):
    lista_rec      = ft.Column(spacing=8)
    txt_status_ia  = ft.Text("", size=12, color=SEC)
    txt_instrucoes = _campo("Instrucoes de uso extraidas", multiline=True, min_lines=4)
    foto_path      = [""]

    def _carregar_lista():
        lista_rec.controls.clear()
        recs = listar_receitas(consulta["id"])
        if not recs:
            lista_rec.controls.append(ft.Container(
                content=ft.Text("Nenhuma receita cadastrada.", color=SEC, size=13),
                padding=ft.padding.symmetric(vertical=12),
            ))
        for r in recs:
            lista_rec.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("receipt_long_rounded", size=20, color=ROXO),
                    ft.Column([
                        ft.Text(r.get("nome_arquivo") or "Receita", size=13,
                                color=TXT, weight=ft.FontWeight.W_600),
                        ft.Text(r.get("observacoes") or "", size=11, color=SEC, max_lines=2),
                    ], spacing=2, expand=True),
                    ft.Text(r.get("data") or "", size=11, color=MUT),
                ], spacing=10),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                border=ft.border.all(1, BD),
            ))
        try: page.update()
        except Exception: pass

    btn_extrair = ft.Container(
        content=ft.Row([
            ft.Icon("auto_awesome_rounded", size=15, color=ROXO),
            ft.Text("Extrair com IA", size=13, color=ROXO, weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        bgcolor=f"{ROXO}18", border=ft.border.all(1, ROXO + "55"),
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
                caminho = filedialog.askopenfilename(
                    title="Foto da receita",
                    filetypes=[("Imagens", "*.jpg *.jpeg *.png *.webp")],
                )
                root.destroy()
                if not caminho:
                    return
                foto_path[0] = caminho
                nome = caminho.replace("\\", "/").split("/")[-1]
                page.pubsub.send_all({"_tipo": "receita_foto", "nome": nome})
            except Exception as ex:
                page.pubsub.send_all({"_tipo": "receita_foto", "erro": str(ex)})

        _sub = [False]
        def _on_msg(msg):
            if not isinstance(msg, dict) or msg.get("_tipo") != "receita_foto":
                return
            if "erro" in msg:
                txt_status_ia.value = f"Erro: {msg['erro']}"
                txt_status_ia.color = VERM
            else:
                txt_status_ia.value = msg["nome"]
                btn_extrair.visible = True
            try: page.update()
            except Exception: pass
        if not _sub[0]:
            page.pubsub.subscribe(_on_msg)
            _sub[0] = True
        threading.Thread(target=_picker, daemon=True).start()

    def _salvar_receita(e):
        if not foto_path[0] and not txt_instrucoes.value.strip():
            txt_status_ia.value = "Adicione uma foto ou instrucoes."
            try: page.update()
            except Exception: pass
            return
        drive_id = None; nome_arq = ""
        if foto_path[0]:
            try:
                from shared.drive_connector import upload_foto_medico
                drive_id = upload_foto_medico(foto_path[0])
                nome_arq = foto_path[0].replace("\\", "/").split("/")[-1]
            except Exception as ex:
                logger.error("upload receita Drive: %s", ex)
                nome_arq = foto_path[0].replace("\\", "/").split("/")[-1]
        salvar_receita({
            "consulta_id":   consulta["id"],
            "medico_id":     consulta.get("medico_id"),
            "drive_file_id": drive_id,
            "nome_arquivo":  nome_arq,
            "data":          datetime.date.today().strftime("%d/%m/%Y"),
            "observacoes":   txt_instrucoes.value.strip() or None,
        })
        foto_path[0] = ""; txt_instrucoes.value = ""
        txt_status_ia.value = "Receita salva!"; txt_status_ia.color = VERD
        btn_extrair.visible = False
        _carregar_lista()

    btn_extrair.on_click = lambda e: None  # IA simplificada — manter compatibilidade

    _carregar_lista()

    cabecalho = ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Row([
                    ft.Icon("arrow_back_rounded", size=16),
                    ft.Text("Voltar", size=13),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                ink=True, on_click=lambda e: voltar_fn(),
            ),
            ft.Column([
                ft.Text("Receitas", size=18, weight=ft.FontWeight.W_700, color=TXT),
                ft.Text(f"{consulta.get('medico') or 'Profissional'}  "
                        f"·  {consulta.get('data','')} {consulta.get('hora','')}",
                        size=11, color=SEC),
            ], spacing=1, expand=True),
        ]),
        padding=ft.padding.symmetric(horizontal=16, vertical=14),
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
    )

    corpo = ft.Column([
        cabecalho,
        ft.Container(
            content=ft.Column([
                _label_sec("RECEITAS CADASTRADAS"),
                lista_rec,
                ft.Container(height=1, bgcolor=BD, margin=ft.margin.symmetric(vertical=8)),
                _label_sec("ADICIONAR RECEITA", ROXO),
                ft.Container(
                    content=ft.Row([
                        ft.Icon("camera_alt_outlined_rounded", size=15, color=ROXO),
                        ft.Text("Foto da receita", size=12, color=ROXO),
                    ], spacing=6, tight=True),
                    bgcolor=f"{ROXO}18", border=ft.border.all(1, ROXO + "55"),
                    border_radius=8, ink=True,
                    padding=ft.padding.symmetric(horizontal=12, vertical=9),
                    on_click=_selecionar_foto,
                ),
                btn_extrair,
                txt_status_ia,
                txt_instrucoes,
                ft.Container(
                    content=ft.Row([
                        ft.Icon("save_rounded", size=15, color=BG),
                        ft.Text("Salvar Receita", size=13, color=BG, weight=ft.FontWeight.W_600),
                    ], spacing=6, tight=True),
                    bgcolor=AZUL, border_radius=8, ink=True,
                    padding=ft.padding.symmetric(horizontal=16, vertical=12),
                    on_click=_salvar_receita,
                ),
                ft.Container(height=20),
            ], spacing=10, scroll=ft.ScrollMode.AUTO),
            padding=ft.padding.all(16), expand=True,
        ),
    ], expand=True, spacing=0)

    return _centralizar(corpo, page)


# ══════════════════════════════════════════════════════════════
# FORMULÁRIO DE COMPROMISSO
# ══════════════════════════════════════════════════════════════

def _tela_ficha_compromisso(page, consulta, voltar_fn, medicos, clinicas):
    lay    = Layout(page)
    is_new = consulta is None

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

    col_medico, lbl_medico = _campo_medico(
        page, medicos, med_id_sel, valor_med_ini,
        label_override=_LABEL_PROF.get(tipo_comp_sel[0], "PROFISSIONAL"),
    )
    col_clinica = _campo_clinica(page, clinicas, clinica_id_sel, valor_cl_ini)

    f_data = _campo("Data *", consulta["data"] if consulta else "",
                    hint="DD/MM/AAAA", largura=140)
    f_hora = _campo("Hora", consulta.get("hora","") if consulta else "",
                    hint="HH:MM", largura=90)
    f_obs  = _campo("Observacoes", consulta.get("observacoes","") if consulta else "",
                    multiline=True, min_lines=3)

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
        for idx, item in enumerate(pauta_itens):
            def _rm(e, i=idx):
                del pauta_itens[i]; _rebuild_pauta()
            pauta_col.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("check_circle_outline_rounded", size=14, color=AZUL),
                    ft.Text(item, size=12, color=TXT, expand=True),
                    ft.Container(
                        content=ft.Icon("close_rounded", size=13, color=MUT),
                        padding=4, border_radius=4, ink=True, on_click=_rm,
                    ),
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
            ft.Text("Adicionar", size=12, color=AZUL),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8, bgcolor=AZUL + "18",
        border=ft.border.all(1, AZUL + "44"), ink=True,
    )
    btn_add_item.on_click = _add_item
    _rebuild_pauta()

    # ── Chips de tipo_compromisso ────────────────────────────
    chips_tipo_comp = ft.Row(spacing=8, wrap=True)

    def _rebuild_chips_tipo():
        chips_tipo_comp.controls.clear()
        for tp in ["consulta", "coleta", "fisioterapia", "outro"]:
            def _on(e, t=tp):
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
        _, label_t, _ = TIPOS_COMP.get(tipo_comp_sel[0], TIPOS_COMP["outro"])
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
            "data":             f_data.value.strip(),
            "hora":             f_hora.value.strip() or None,
            "tipo":             status_sel[0],
            "tipo_compromisso": tipo_comp_sel[0],
            "clinica_id":       clinica_id_sel[0],
            "observacoes":      f_obs.value.strip() or None,
            "pauta":            pauta_itens,
        })
        voltar_fn()

    _rebuild_chips_tipo()
    _rebuild_chips_status()

    cor_tc, icone_tc, _ = TIPOS_COMP.get(tipo_comp_sel[0], TIPOS_COMP["outro"])
    titulo = "Novo Compromisso" if is_new else "Editar Compromisso"

    btn_salvar = ft.Container(
        content=ft.Row([
            ft.Icon("save_rounded", size=15, color=BG),
            ft.Text("Salvar", size=13, color=BG, weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        bgcolor=AZUL, border_radius=8, ink=True,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
    )
    btn_salvar.on_click = _salvar

    cabecalho = lay.criar_cabecalho(
        titulo, voltar_fn,
        icone_titulo="event_note_rounded",
        cor_titulo=AZUL,
        acoes=[btn_salvar],
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
                ft.Row([f_data, f_hora], spacing=8),
                ft.Container(height=4),
                _label_sec("STATUS"),
                chips_status,
                ft.Container(height=4),
                _label_sec("ITENS A TRATAR"),
                ft.Row([f_novo_item, btn_add_item], spacing=8),
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
                    bgcolor=f"{AMAR}18",
                    border=ft.border.all(1, AMAR + "55"),
                    border_radius=8, ink=True,
                    padding=ft.padding.symmetric(horizontal=16, vertical=10),
                    on_click=_agendar,
                ),
                txt_alarme,
                txt_erro,
                ft.Container(height=20),
            ], spacing=8, scroll=ft.ScrollMode.AUTO),
            padding=ft.padding.all(16),
            expand=True,
        ),
    ], expand=True, spacing=0)

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
                dt    = datetime.datetime.strptime(c["data"], "%d/%m/%Y").date()
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

            def _make_rec(cons):
                def _click(e): _abrir_receitas(cons)
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
                                ft.Icon("receipt_long_rounded", size=13, color=ROXO),
                                ft.Text("Receitas", size=11, color=ROXO),
                            ], spacing=4, tight=True),
                            padding=ft.padding.symmetric(horizontal=8, vertical=8),
                            ink=True, on_click=_make_rec(c),
                        ),
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

    def _abrir_ficha(consulta):
        def _voltar():
            _carregar(); _mostrar_principal()
        wrapper.controls.clear()
        wrapper.controls.append(
            _tela_ficha_compromisso(page, consulta, _voltar, medicos, clinicas))
        try: page.update()
        except Exception: pass

    def _abrir_receitas(consulta):
        def _voltar():
            _carregar(); _mostrar_principal()
        wrapper.controls.clear()
        wrapper.controls.append(_tela_receita(page, consulta, _voltar))
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
