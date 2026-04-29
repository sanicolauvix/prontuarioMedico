# -*- coding: utf-8 -*-
"""
tela_laboratorios.py — Koios Prontuário
Laboratórios detectados nos exames + ferramenta IA para novos layouts.
Padrão visual: idêntico a tela_exames.py (header + barra de abas + área de conteúdo)
"""
import logging
import threading
import flet as ft
from dados.model_prontuario import listar_laboratorios

logger = logging.getLogger(__name__)

# ── Paleta ────────────────────────────────────────────────────
BG   = "#0D1117";  CARD = "#161B22";  BD  = "#21262D";  BD2 = "#30363D"
TXT  = "#E6EDF3";  SEC  = "#8B949E";  MUT = "#484F58"
AZUL = "#58A6FF";  VERD = "#3FB950";  LAR = "#F0883E"
AMAR = "#D29922";  VERM = "#DA3633";  ROXO = "#BC8CFF"
CORAL = "#FF7B72"

# Extratores conhecidos
EXTRATORES = {
    "Tommasi":      {"status": "manual",   "cor": VERD, "desc": "Regex completo"},
    "Cremasco":     {"status": "manual",   "cor": VERD, "desc": "Regex completo"},
    "Pretti":       {"status": "manual",   "cor": VERD, "desc": "Coordenadas PDF"},
    "Virchow":      {"status": "manual",   "cor": VERD, "desc": "Regex laudo"},
    "MedSênior":    {"status": "manual",   "cor": VERD, "desc": "Imagem/laudo"},
    "Zeiss":        {"status": "auto",     "cor": AZUL, "desc": "Campo visual"},
    "Topcon":       {"status": "auto",     "cor": AZUL, "desc": "Retinografia"},
    "DynaMapa":     {"status": "falha",    "cor": VERM, "desc": "Fonte codificada"},
    "Desconhecido": {"status": "genérico", "cor": AMAR, "desc": "Extrator genérico"},
}


# ══════════════════════════════════════════════════════════════
# ABA 1: LISTA DE LABORATÓRIOS
# ══════════════════════════════════════════════════════════════

def _conteudo_labs(page):
    lista = ft.Column(spacing=8)

    def _carregar():
        lista.controls.clear()
        labs = listar_laboratorios()

        if not labs:
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("biotech_rounded", size=48, color=MUT),
                    ft.Text("Nenhum laboratório detectado.", color=SEC, size=13),
                    ft.Text("Importe exames para detectar automaticamente.",
                            color=MUT, size=11),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=40))
            try: page.update()
            except Exception: pass
            return

        total_labs   = len(labs)
        total_exames = sum(l["total_exames"] for l in labs)
        lista.controls.append(ft.Container(
            content=ft.Row([
                ft.Text(f"{total_labs} laboratório(s)", size=12, color=CORAL,
                        weight=ft.FontWeight.W_600, expand=True),
                ft.Container(
                    content=ft.Text(f"{total_exames} exames no total",
                                    size=10, color=MUT),
                    bgcolor=f"{CORAL}12", border_radius=8,
                    padding=ft.padding.symmetric(horizontal=8, vertical=3)),
            ]),
            padding=ft.padding.only(bottom=4)))

        for lab in labs:
            nome   = lab["laboratorio"]
            ext    = EXTRATORES.get(nome, EXTRATORES["Desconhecido"])
            cor    = ext["cor"]
            status = ext["status"]
            desc   = ext["desc"]

            if status == "manual":
                badge_txt = "✓ Extrator manual";  badge_cor = VERD
            elif status == "auto":
                badge_txt = "◎ Auto-detectado";   badge_cor = AZUL
            elif status == "falha":
                badge_txt = "✗ Falha extração";   badge_cor = VERM
            else:
                badge_txt = "⚠ Genérico";         badge_cor = AMAR

            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            content=ft.Icon("biotech_rounded", size=20, color=cor),
                            bgcolor=f"{cor}1A", border_radius=8,
                            width=40, height=40,
                            alignment=ft.alignment.Alignment(0, 0)),
                        ft.Column([
                            ft.Text(nome, size=14, color=TXT,
                                    weight=ft.FontWeight.W_600),
                            ft.Text(desc, size=11, color=SEC),
                        ], spacing=2, expand=True),
                        ft.Column([
                            ft.Text(str(lab["total_exames"]), size=16, color=cor,
                                    weight=ft.FontWeight.W_700),
                            ft.Text("exames", size=8, color=MUT),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                           spacing=0),
                    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row([
                        ft.Container(
                            content=ft.Text(badge_txt, size=10, color=badge_cor,
                                            weight=ft.FontWeight.W_600),
                            bgcolor=f"{badge_cor}18", border_radius=8,
                            padding=ft.padding.symmetric(horizontal=8, vertical=3)),
                        ft.Container(expand=True),
                        ft.Text(
                            f'{lab.get("primeiro", "")} — {lab.get("ultimo", "")}',
                            size=10, color=MUT),
                    ], spacing=6),
                ], spacing=6),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                border=ft.Border(
                    left=ft.BorderSide(2, cor),
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD)),
            ))

        try: page.update()
        except Exception: pass

    _carregar()
    return [lista]


# ══════════════════════════════════════════════════════════════
# ABA 2: FERRAMENTA IA
# ══════════════════════════════════════════════════════════════

def _conteudo_ia(page):
    txt_status = ft.Text("", size=11, color=VERD)
    f_pdf_path = ft.TextField(
        label="Caminho do PDF novo",
        hint_text="C:/Downloads/exame_novo.pdf",
        hint_style=ft.TextStyle(color=MUT, size=11),
        bgcolor=CARD, border_color=BD2, focused_border_color=ROXO,
        label_style=ft.TextStyle(color=SEC),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, expand=True,
    )

    resultado_col = ft.Column(spacing=0, visible=False)

    def _analisar(e):
        caminho = f_pdf_path.value.strip()
        if not caminho:
            txt_status.value = "Informe o caminho do PDF."
            txt_status.color = VERM
            try: page.update()
            except Exception: pass
            return
        txt_status.value = "Analisando layout com IA..."
        txt_status.color = AZUL
        resultado_col.visible = False
        try: page.update()
        except Exception: pass

        def _run():
            try:
                import os
                import pdfplumber
                import io
                import anthropic
                import json

                if not os.path.exists(caminho):
                    page.pubsub.send_all({"_tipo": "lab_ia", "erro": "Arquivo não encontrado."})
                    return

                from pathlib import Path
                conteudo = Path(caminho).read_bytes()

                texto = ""
                with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
                    for pg in pdf.pages[:5]:
                        texto += (pg.extract_text(x_tolerance=3, y_tolerance=3) or "") + "\n"

                if not texto.strip():
                    page.pubsub.send_all({"_tipo": "lab_ia", "erro": "PDF sem texto extraível (imagem?)."})
                    return

                prompt = f"""Analise o texto extraído deste PDF de exame laboratorial.
Identifique:
1. Nome do laboratório
2. Layout/formato dos resultados (tabular, lista, laudo textual)
3. Padrão de cada linha de resultado (nome, valor, unidade, referência)
4. Sugira um regex Python para extrair os resultados

Texto do PDF (primeiras 5 páginas):
\"\"\"
{texto[:3000]}
\"\"\"

Responda em JSON:
{{"laboratorio": "nome", "formato": "tabular|lista|laudo", "padrao_linha": "descrição", "regex_sugerido": "regex python", "observacoes": "notas"}}"""

                client = anthropic.Anthropic()
                resp = client.messages.create(
                    model="claude-sonnet-4-20250514", max_tokens=1500,
                    messages=[{"role": "user", "content": prompt}])
                raw = resp.content[0].text.strip()

                try:
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
                    dados = json.loads(raw)
                    formatado = (
                        f"Lab: {dados.get('laboratorio', '?')}\n"
                        f"Formato: {dados.get('formato', '?')}\n"
                        f"Padrão: {dados.get('padrao_linha', '?')}\n"
                        f"Regex: {dados.get('regex_sugerido', '?')}\n"
                        f"Obs: {dados.get('observacoes', '')}"
                    )
                except Exception:
                    formatado = raw[:500]

                page.pubsub.send_all({"_tipo": "lab_ia", "resultado": formatado})

            except Exception as ex:
                logger.error("Análise IA laboratório: %s", str(ex), exc_info=True)
                page.pubsub.send_all({"_tipo": "lab_ia", "erro": str(ex)[:80]})

        _subscribed = [False]

        def _on_msg(msg):
            if not isinstance(msg, dict) or msg.get("_tipo") != "lab_ia":
                return
            if "erro" in msg:
                txt_status.value = msg["erro"]
                txt_status.color = VERM
            else:
                txt_status.value = "✓ Análise concluída!"
                txt_status.color = VERD
                resultado_col.controls.clear()
                resultado_col.controls.append(ft.Container(
                    content=ft.Text(msg["resultado"], size=12, color=SEC,
                                    selectable=True),
                    bgcolor=f"{ROXO}0A", border_radius=8,
                    padding=12,
                    border=ft.Border(left=ft.BorderSide(2, ROXO),
                                     top=ft.BorderSide(1, BD),
                                     bottom=ft.BorderSide(1, BD),
                                     right=ft.BorderSide(1, BD)),
                ))
                resultado_col.visible = True
            try: page.update()
            except Exception: pass

        if not _subscribed[0]:
            page.pubsub.subscribe(_on_msg)
            _subscribed[0] = True

        threading.Thread(target=_run, daemon=True).start()

    return [
        ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon("psychology_rounded", size=16, color=ROXO),
                    ft.Text("Analisar PDF de laboratório desconhecido",
                            size=13, color=ROXO, weight=ft.FontWeight.W_600),
                ], spacing=8),
                ft.Text("A IA identifica o layout e sugere regex para extração.",
                        size=11, color=MUT),
                f_pdf_path,
                ft.Row([
                    ft.FilledButton(
                        content=ft.Row([
                            ft.Icon("psychology_rounded", size=14),
                            ft.Text("Analisar com IA", size=12),
                        ], spacing=4, tight=True),
                        style=ft.ButtonStyle(
                            bgcolor=ROXO,
                            shape=ft.RoundedRectangleBorder(radius=8),
                            padding=ft.padding.symmetric(horizontal=14, vertical=8),
                        ),
                        on_click=_analisar,
                    ),
                    txt_status,
                ], spacing=8),
                resultado_col,
            ], spacing=10),
            bgcolor=f"{ROXO}0A", border_radius=10,
            padding=ft.padding.all(14),
            border=ft.Border(
                left=ft.BorderSide(3, ROXO),
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                right=ft.BorderSide(1, BD)),
        ),
    ]


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL
# ══════════════════════════════════════════════════════════════

def criar_tela_laboratorios(page: ft.Page, voltar_fn):
    ABAS = [
        (0, "biotech_rounded",     "Laboratórios", CORAL),
        (1, "psychology_rounded",  "IA",            ROXO),
    ]
    aba_ativa = [0]

    barra_abas    = ft.Row(spacing=0)
    area_conteudo = ft.Column(spacing=8, expand=True, scroll=ft.ScrollMode.AUTO)

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

    def _rebuild_conteudo():
        area_conteudo.controls.clear()
        if aba_ativa[0] == 0:
            area_conteudo.controls.extend(_conteudo_labs(page))
        else:
            area_conteudo.controls.extend(_conteudo_ia(page))
        try: page.update()
        except Exception: pass

    _rebuild_abas()
    _rebuild_conteudo()

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
                ft.Icon("biotech_rounded", size=20, color=CORAL),
                ft.Text("Laboratórios", size=18,
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

    return ft.Container(bgcolor=BG, expand=True, content=conteudo_final)
