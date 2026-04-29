# -*- coding: utf-8 -*-
"""
tela_consultas_medicas.py — Koios Prontuário
Consultas médicas: lista, cadastro, alarme Windows e receitas via IA.
Padrão visual: idêntico a tela_exames.py (header + barra de abas + área de conteúdo)
"""
import logging
import threading
import datetime
import flet as ft
from dados.model_prontuario import (
    listar_consultas, salvar_consulta, listar_medicos,
    salvar_receita, listar_receitas,
)

logger = logging.getLogger(__name__)

# ── Paleta ────────────────────────────────────────────────────
BG   = "#0D1117";  CARD = "#161B22";  BD  = "#21262D";  BD2 = "#30363D"
TXT  = "#E6EDF3";  SEC  = "#8B949E";  MUT = "#484F58"
AZUL = "#58A6FF";  VERD = "#3FB950";  LAR = "#F0883E"
AMAR = "#D29922";  VERM = "#DA3633";  ROXO = "#BC8CFF"

CORES_TIPO = {
    "agendada":  (AZUL, "calendar_today_rounded"),
    "realizada": (VERD, "check_circle_outline_rounded"),
    "cancelada": (MUT,  "cancel_outlined_rounded"),
}


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _campo(label, valor="", largura=None, multiline=False, min_lines=1, hint=None,
           keyboard=ft.KeyboardType.TEXT):
    kw = dict(
        label=label, value=valor or "",
        bgcolor=CARD, border_color=BD2,
        focused_border_color=AZUL,
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


def _badge(tipo):
    cor, icone = CORES_TIPO.get(tipo, (SEC, "help_outline_rounded"))
    return ft.Container(
        content=ft.Row([
            ft.Icon(icone, size=11, color=cor),
            ft.Text(tipo.capitalize(), size=10, color=cor,
                    weight=ft.FontWeight.W_600),
        ], spacing=4, tight=True),
        bgcolor=f"{cor}18", border_radius=10,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
    )


def _chip_tipo(tipo, selecionado, on_click):
    cor, icone = CORES_TIPO.get(tipo, (SEC, "help_outline_rounded"))
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
        border=ft.Border(
            top=ft.BorderSide(1, cor if ativo else BD2),
            bottom=ft.BorderSide(1, cor if ativo else BD2),
            left=ft.BorderSide(1, cor if ativo else BD2),
            right=ft.BorderSide(1, cor if ativo else BD2),
        ),
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
        nome_tarefa = f"Koios_Consulta_{data_win}_{hora_win.replace(':','')}"
        cmd = (
            f'schtasks /create /tn "{nome_tarefa}" /tr '
            f'"msg * Consulta: {descricao}" '
            f'/sc once /d {data_win} /st {hora_win} /f'
        )
        subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return True, nome_tarefa
    except Exception as ex:
        return False, str(ex)


# ══════════════════════════════════════════════════════════════
# CAMPO MÉDICO — padrão Koios de busca
# ══════════════════════════════════════════════════════════════

def _campo_medico(page, medicos, med_id_sel, valor_ini=""):
    """Retorna (coluna_com_busca, chip) para uso na ficha."""

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
        hint_text="Buscar médico...",
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
                content=ft.Text("Nenhum médico encontrado.", size=12, color=MUT),
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
                border=ft.Border(
                    left=ft.BorderSide(2, AZUL),
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
                on_click=make_sel(), ink=True,
            ))
        sugestoes.visible = True
        try: page.update()
        except Exception: pass

    tf.on_change = _filtrar

    col = ft.Column([
        _label_sec("MÉDICO"),
        med_chip,
        tf,
        sugestoes,
    ], spacing=4)

    return col


# ══════════════════════════════════════════════════════════════
# TELA DE RECEITA
# ══════════════════════════════════════════════════════════════

def _tela_receita(page, consulta, voltar_fn):
    lista_rec      = ft.Column(spacing=8)
    txt_status_ia  = ft.Text("", size=12, color=SEC)
    txt_instrucoes = _campo("Instruções de uso extraídas",
                            multiline=True, min_lines=4)
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
                        ft.Text(r.get("observacoes") or "", size=11, color=SEC,
                                max_lines=2),
                    ], spacing=2, expand=True),
                    ft.Text(r.get("data") or "", size=11, color=MUT),
                ], spacing=10),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                border=ft.Border(
                    left=ft.BorderSide(2, ROXO),
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
            ))
        try: page.update()
        except Exception: pass

    btn_extrair = ft.FilledButton(
        content=ft.Row([
            ft.Icon("auto_awesome_rounded", size=15),
            ft.Text("Extrair com IA", size=13, weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        style=ft.ButtonStyle(
            bgcolor=ROXO,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
        ),
        visible=False,
    )

    def _selecionar_foto(e):
        def _picker():
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk(); root.withdraw()
                root.attributes("-topmost", True)
                caminho = filedialog.askopenfilename(
                    title="Selecionar foto da receita",
                    filetypes=[("Imagens", "*.jpg *.jpeg *.png *.webp")],
                )
                root.destroy()
                if not caminho:
                    return
                foto_path[0] = caminho
                nome = caminho.replace("\\", "/").split("/")[-1]
                page.pubsub.send_all({"_tipo": "receita_foto", "nome": nome})
            except Exception as ex:
                logger.error("_selecionar_foto: %s", str(ex), exc_info=True)
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
                txt_status_ia.color = SEC
                btn_extrair.visible = True
            try: page.update()
            except Exception: pass

        if not _sub[0]:
            page.pubsub.subscribe(_on_msg)
            _sub[0] = True
        threading.Thread(target=_picker, daemon=True).start()

    def _extrair_ia(e):
        if not foto_path[0]:
            txt_status_ia.value = "Selecione uma foto primeiro."
            try: page.update()
            except Exception: pass
            return
        txt_status_ia.value = "Analisando receita com IA..."
        txt_status_ia.color = AZUL
        btn_extrair.disabled = True
        try: page.update()
        except Exception: pass

        def _analisar():
            try:
                import base64, json, urllib.request
                with open(foto_path[0], "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                ext  = foto_path[0].rsplit(".", 1)[-1].lower()
                mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                        "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
                payload = json.dumps({
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": [
                        {"type": "image", "source": {
                            "type": "base64", "media_type": mime, "data": img_b64}},
                        {"type": "text", "text": (
                            "Esta é uma foto de uma receita médica. "
                            "Extraia e liste todos os medicamentos prescritos com: "
                            "nome, dosagem, frequência e duração. "
                            "Formato: um por linha, ex:\n"
                            "• Amoxicilina 500mg — 1 cápsula de 8 em 8h por 7 dias\n"
                            "Se não conseguir ler algum campo, use '?'. "
                            "Responda apenas a lista, sem introdução."
                        )},
                    ]}],
                }).encode()
                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=payload,
                    headers={"Content-Type": "application/json",
                             "anthropic-version": "2023-06-01"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read())
                texto = "".join(
                    b.get("text", "") for b in data.get("content", [])
                    if b.get("type") == "text"
                )
                page.pubsub.send_all({"_tipo": "receita_ia", "texto": texto.strip()})
            except Exception as ex:
                logger.error("_extrair_ia: %s", str(ex), exc_info=True)
                page.pubsub.send_all({"_tipo": "receita_ia", "erro": str(ex)[:80]})
            finally:
                btn_extrair.disabled = False

        _sub2 = [False]
        def _on_ia(msg):
            if not isinstance(msg, dict) or msg.get("_tipo") != "receita_ia":
                return
            if "erro" in msg:
                txt_status_ia.value = f"Erro na IA: {msg['erro']}"
                txt_status_ia.color = VERM
            else:
                txt_instrucoes.value = msg["texto"]
                txt_status_ia.value  = "✓ Extração concluída"
                txt_status_ia.color  = VERD
            try: page.update()
            except Exception: pass

        if not _sub2[0]:
            page.pubsub.subscribe(_on_ia)
            _sub2[0] = True
        threading.Thread(target=_analisar, daemon=True).start()

    btn_extrair.on_click = _extrair_ia

    def _salvar_receita(e):
        if not foto_path[0] and not txt_instrucoes.value.strip():
            txt_status_ia.value = "Adicione uma foto ou instruções."
            try: page.update()
            except Exception: pass
            return
        drive_id = None
        nome_arq = ""
        if foto_path[0]:
            try:
                from shared.drive_connector import upload_foto_medico
                txt_status_ia.value = "Enviando para o Drive..."
                try: page.update()
                except Exception: pass
                drive_id = upload_foto_medico(foto_path[0])
                nome_arq = foto_path[0].replace("\\", "/").split("/")[-1]
            except Exception as ex:
                logger.error("upload receita Drive: %s", str(ex), exc_info=True)
                nome_arq = foto_path[0].replace("\\", "/").split("/")[-1]
        salvar_receita({
            "consulta_id":   consulta["id"],
            "medico_id":     consulta.get("medico_id"),
            "drive_file_id": drive_id,
            "nome_arquivo":  nome_arq,
            "data":          datetime.date.today().strftime("%d/%m/%Y"),
            "observacoes":   txt_instrucoes.value.strip() or None,
        })
        foto_path[0]         = ""
        txt_instrucoes.value = ""
        txt_status_ia.value  = "✓ Receita salva!"
        txt_status_ia.color  = VERD
        btn_extrair.visible  = False
        _carregar_lista()

    _carregar_lista()

    medico_txt = consulta.get("medico") or "Médico não informado"
    data_txt   = consulta.get("data") or ""
    hora_txt   = consulta.get("hora") or ""

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
            ft.Column([
                ft.Text("Receitas", size=18, weight=ft.FontWeight.W_700, color=TXT),
                ft.Text(f"{medico_txt}  ·  {data_txt} {hora_txt}",
                        size=11, color=SEC),
            ], spacing=1, expand=True),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=16, vertical=14),
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
    )

    corpo = ft.Column([
        cabecalho,
        ft.Container(
            content=ft.Column([
                _label_sec("RECEITAS CADASTRADAS"),
                lista_rec,
                ft.Container(height=1, bgcolor=BD,
                             margin=ft.margin.symmetric(vertical=8)),
                _label_sec("ADICIONAR RECEITA", ROXO),
                ft.Row([
                    ft.OutlinedButton(
                        content=ft.Row([
                            ft.Icon("camera_alt_outlined_rounded", size=15, color=ROXO),
                            ft.Text("Foto da receita", size=12, color=ROXO),
                        ], spacing=6, tight=True),
                        style=ft.ButtonStyle(
                            side=ft.BorderSide(1, ROXO),
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                        on_click=_selecionar_foto,
                    ),
                    btn_extrair,
                ], spacing=8),
                txt_status_ia,
                txt_instrucoes,
                ft.FilledButton(
                    content=ft.Row([
                        ft.Icon("save_rounded", size=15),
                        ft.Text("Salvar Receita", size=13, weight=ft.FontWeight.W_600),
                    ], spacing=6, tight=True),
                    style=ft.ButtonStyle(
                        bgcolor=AZUL,
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=20, vertical=12),
                    ),
                    on_click=_salvar_receita,
                ),
                ft.Container(height=20),
            ], spacing=10, scroll=ft.ScrollMode.AUTO),
            padding=ft.padding.all(16),
            expand=True,
        ),
    ], expand=True, spacing=0)

    return _centralizar(corpo, page)


# ══════════════════════════════════════════════════════════════
# TELA DE CADASTRO / EDIÇÃO DE CONSULTA
# ══════════════════════════════════════════════════════════════

def _tela_ficha_consulta(page, consulta, voltar_fn, medicos):
    is_novo = consulta is None
    titulo  = "Nova Consulta" if is_novo else "Editar Consulta"

    med_map    = {str(m["id"]): m["nome"] for m in medicos}
    med_id_sel = [str(consulta["medico_id"])
                  if consulta and consulta.get("medico_id") else None]
    valor_ini  = med_map.get(med_id_sel[0], "") if med_id_sel[0] else ""

    col_medico = _campo_medico(page, medicos, med_id_sel, valor_ini)

    f_data  = _campo("Data *", consulta["data"] if consulta else "",
                     hint="DD/MM/AAAA", largura=140)
    f_hora  = _campo("Hora",   consulta.get("hora", "") if consulta else "",
                     hint="HH:MM", largura=90)
    f_local = _campo("Local / Clínica",
                     consulta.get("local", "") if consulta else "")
    f_obs   = _campo("Observações",
                     consulta.get("observacoes", "") if consulta else "",
                     multiline=True, min_lines=3)

    tipo_sel  = [consulta.get("tipo", "agendada") if consulta else "agendada"]
    chips_ref = ft.Ref()
    txt_erro  = ft.Text("", color=VERM, size=12)
    txt_alarme= ft.Text("", size=11, color=VERD)

    def _rebuild_chips():
        chips_ref.current.controls.clear()
        for t in ["agendada", "realizada", "cancelada"]:
            def _on(e, tp=t):
                tipo_sel[0] = tp
                _rebuild_chips()
            chips_ref.current.controls.append(_chip_tipo(t, tipo_sel[0], _on))
        try: page.update()
        except Exception: pass

    def _agendar(e):
        data = f_data.value.strip()
        if not data:
            txt_alarme.value = "Informe a data primeiro."
            try: page.update()
            except Exception: pass
            return
        hora = f_hora.value.strip() or "08:00"
        # nome do médico a partir do chip
        desc = (chips_ref.current and
                col_medico.controls[1].content.controls[1].value) or "Consulta médica"
        ok, info = _agendar_alarme_windows(data, hora, desc)
        txt_alarme.value = (f"✓ Alarme: {data} às {hora}" if ok
                            else f"Erro no alarme: {info}")
        txt_alarme.color = VERD if ok else LAR
        try: page.update()
        except Exception: pass

    def _salvar(e):
        if not f_data.value.strip():
            txt_erro.value = "Data é obrigatória."
            try: page.update()
            except Exception: pass
            return
        salvar_consulta({
            "id":          consulta["id"] if consulta else None,
            "medico_id":   int(med_id_sel[0]) if med_id_sel[0] else None,
            "data":        f_data.value.strip(),
            "hora":        f_hora.value.strip() or None,
            "tipo":        tipo_sel[0],
            "local":       f_local.value.strip() or None,
            "observacoes": f_obs.value.strip() or None,
        })
        voltar_fn()

    _rebuild_chips()

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
                ft.Icon("event_note_rounded", size=18, color=AZUL),
                ft.Text(titulo, size=18, weight=ft.FontWeight.W_700, color=TXT),
            ], spacing=8, tight=True),
            ft.Container(expand=True),
            ft.FilledButton(
                content=ft.Row([
                    ft.Icon("save_rounded", size=16),
                    ft.Text("Salvar", size=13, weight=ft.FontWeight.W_600),
                ], spacing=6, tight=True),
                style=ft.ButtonStyle(
                    bgcolor=AZUL,
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=18, vertical=10),
                ),
                on_click=_salvar,
            ),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=16, vertical=14),
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
    )

    corpo = ft.Column([
        cabecalho,
        ft.Container(
            content=ft.Column([
                col_medico,
                ft.Container(height=4),
                _label_sec("DATA E HORA"),
                ft.Row([f_data, f_hora], spacing=8),
                ft.Container(height=4),
                _label_sec("STATUS"),
                ft.Row([], spacing=8, ref=chips_ref),
                ft.Container(height=4),
                _label_sec("LOCAL"),
                f_local,
                ft.Container(height=4),
                _label_sec("OBSERVAÇÕES"),
                f_obs,
                ft.Container(height=8),
                ft.OutlinedButton(
                    content=ft.Row([
                        ft.Icon("alarm_add_rounded", size=16, color=AMAR),
                        ft.Text("Agendar Alarme", size=13, color=AMAR),
                    ], spacing=6, tight=True),
                    style=ft.ButtonStyle(
                        side=ft.BorderSide(1, AMAR),
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=16, vertical=10),
                    ),
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

def criar_tela_consultas_medicas(page: ft.Page, voltar_fn):
    medicos = listar_medicos(so_ativos=True)

    ABAS = [
        (0, "event_note_rounded",         "Consultas",  AZUL),
        (1, "calendar_today_rounded",     "Agendadas",  AZUL),
        (2, "check_circle_outline_rounded", "Realizadas", VERD),
        (3, "cancel_outlined_rounded",    "Canceladas", MUT),
    ]
    FILTROS = [None, "agendada", "realizada", "cancelada"]
    aba_ativa = [0]

    barra_abas    = ft.Row(spacing=0)
    area_conteudo = ft.Column(spacing=8, expand=True, scroll=ft.ScrollMode.AUTO)
    wrapper       = ft.Column(expand=True, spacing=0)

    lista = ft.Column(spacing=8)

    def _rebuild_abas():
        barra_abas.controls.clear()
        for idx, icone, label, cor in ABAS:
            ativo = idx == aba_ativa[0]
            def _click(e, i=idx):
                aba_ativa[0] = i
                _rebuild_abas()
                _carregar()
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

    hoje = datetime.date.today()

    def _carregar():
        lista.controls.clear()
        filtro = FILTROS[aba_ativa[0]]
        consultas = listar_consultas(filtro)

        if not consultas:
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("event_busy_rounded", size=40, color=MUT),
                    ft.Text("Nenhuma consulta cadastrada.", color=SEC, size=13),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=40, alignment=ft.alignment.Alignment(0, 0),
            ))
            try: page.update()
            except Exception: pass
            return

        for c in consultas:
            cor_tipo, icone_tipo = CORES_TIPO.get(
                c["tipo"], (SEC, "help_outline_rounded"))

            info_data = ""
            try:
                dt = datetime.datetime.strptime(c["data"], "%d/%m/%Y").date()
                delta = (dt - hoje).days
                if c["tipo"] == "agendada":
                    if delta == 0:   info_data = "Hoje!"
                    elif delta == 1: info_data = "Amanhã"
                    elif delta > 0:  info_data = f"Em {delta} dias"
                    else:            info_data = f"Há {abs(delta)} dias"
            except Exception:
                pass

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
                            content=ft.Icon(icone_tipo, size=20, color=cor_tipo),
                            bgcolor=f"{cor_tipo}18", border_radius=10,
                            width=40, height=40,
                            alignment=ft.alignment.Alignment(0, 0)),
                        ft.Column([
                            ft.Text(c.get("medico") or "Médico não informado",
                                    size=14, color=TXT, weight=ft.FontWeight.W_600),
                            ft.Text(c.get("especialidade") or "",
                                    size=11, color=ROXO),
                        ], spacing=1, expand=True),
                        _badge(c["tipo"]),
                    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row([
                        ft.Icon("calendar_today_rounded", size=12, color=MUT),
                        ft.Text(f"{c['data']}  {c.get('hora') or ''}", size=12, color=SEC),
                        ft.Container(expand=True),
                        ft.Text(info_data, size=11,
                                color=AMAR if info_data in ("Hoje!", "Amanhã") else MUT),
                    ], spacing=6),
                    ft.Row([
                        ft.Icon("location_on_outlined_rounded", size=12, color=MUT),
                        ft.Text(c.get("local") or "Local não informado",
                                size=11, color=SEC, expand=True),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon("receipt_long_rounded", size=13, color=ROXO),
                                ft.Text("Receitas", size=11, color=ROXO),
                            ], spacing=4, tight=True),
                            padding=ft.padding.symmetric(horizontal=8, vertical=8),
                            ink=True,
                            on_click=_make_rec(c),
                        ),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon("edit_rounded", size=13, color=MUT),
                                ft.Text("Editar", size=11, color=MUT),
                            ], spacing=4, tight=True),
                            padding=ft.padding.symmetric(horizontal=8, vertical=8),
                            ink=True,
                            on_click=_make_ficha(c),
                        ),
                    ], spacing=4),
                ], spacing=8),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                border=ft.Border(
                    left=ft.BorderSide(2, cor_tipo),
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
            _carregar()
            _mostrar_principal()
        wrapper.controls.clear()
        wrapper.controls.append(
            _tela_ficha_consulta(page, consulta, _voltar, medicos))
        try: page.update()
        except Exception: pass

    def _abrir_receitas(consulta):
        def _voltar():
            _carregar()
            _mostrar_principal()
        wrapper.controls.clear()
        wrapper.controls.append(_tela_receita(page, consulta, _voltar))
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
                    ft.Icon("event_note_rounded", size=20, color=AZUL),
                    ft.Text("Consultas", size=18,
                            weight=ft.FontWeight.W_700, color=TXT),
                ], spacing=8, tight=True),
                ft.Container(expand=True),
                ft.FilledButton(
                    content=ft.Row([
                        ft.Icon("add_rounded", size=16),
                        ft.Text("Nova", size=13),
                    ], spacing=6, tight=True),
                    style=ft.ButtonStyle(
                        bgcolor=AZUL,
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    ),
                    on_click=lambda e: _abrir_ficha(None),
                ),
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
            ft.Container(bgcolor=BG, expand=True, content=conteudo_final))
        try: page.update()
        except Exception: pass

    _rebuild_abas()
    _carregar()
    _rebuild_conteudo()
    _mostrar_principal()

    return wrapper
