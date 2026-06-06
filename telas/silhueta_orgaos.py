# -*- coding: utf-8 -*-
# Prontuario | telas/silhueta_orgaos.py
# Componente: mapa anatomico com hotspots clicaveis
#
# Imagem base: assets/silueta_anatomia.png (644x551)
# Dividida em 3 secoes horizontais:
#   Secao 1 - Torso (orgaos internos):  x=0   ate x=230
#   Secao 2 - Sistema urinario:         x=230  ate x=420
#   Secao 3 - Esqueleto (ortopedia):    x=420  ate x=644
#
# Hotspots: ft.Container(ink=True) posicionados em ft.Stack
# Coordenadas em pixels da imagem original 644x551, escaladas pela largura.
#
# Uso:
#   from telas.silhueta_orgaos import criar_silhueta, ORGAOS
#   widget = criar_silhueta(page, on_orgao_click=fn, largura=600)
#   fn(id: str) -> None

import flet as ft
import os
import logging

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"
TXT  = "#E6EDF3"; SEC  = "#8B949E"
AZUL = "#58A6FF"; VERD = "#3FB950"; VERM  = "#FF4545"
ROXO = "#BC8CFF"; AMAR = "#D29922"; LRNJ  = "#F0883E"
CIAN = "#4ECDC4"; VIOL = "#A29BFE"; ROSA  = "#FDCB6E"

# Dimensoes da imagem original
IMG_W = 644
IMG_H = 551

# ── Hotspots calibrados (pixels da imagem 644x551) ──────────────────────────
# Formato: (id, label, cor, sistema, x, y, largura, altura)
# x,y = canto superior esquerdo
#
# SECAO 1 — TORSO (x: 0-230)
# Mapeados clicando no torso com ferramenta de coordenadas
#
# SECAO 2 — URINARIO (x: 230-420)
# A mapear
#
# SECAO 3 — ESQUELETO (x: 420-644)
# A mapear

HOTSPOTS_RAW = [

    # ── SECAO 1: TORSO ───────────────────────────────────────────────────────
    # Coordenadas mapeadas diretamente na silueta_anatomia.png (644x551)
    # usando main_test_silhueta.py (4 cliques por orgao)

    ("coracao",   "Coracao",             VERM, "Cardiovascular", 247, 235,  40,  30),
    ("visceral",  "Estomago e Intestino", AZUL, "Visceral",       180, 344, 149, 108),
    ("cerebro",   "Cerebro",             ROXO, "Psiquiatria",    199,   1,  66,  32),
    ("olhos",     "Visão",               CIAN, "Visão & Audição",  200,  44,  24,  20),
    ("urinario",  "Urinário, Próstata e Pênis", AZUL, "Urinario", 425, 293, 191, 205),

    # ── SECAO 2: IMAGENS SEPARADAS (x: 230-644) ──────────────────────────────
    ("coracao2",  "Coracao",   VERM, "Cardiovascular", 445,  78, 137, 159),

    ("pulmao_dir","Pulmoes",   AZUL, "Respiratorio",
     int(390*230/679), int(248*551/710), int(109*230/679), int(102*551/710)),

    ("pulmao_esq","Pulmoes",   AZUL, "Respiratorio",
     int(218*230/679), int(265*551/710), int(126*230/679), int(78*551/710)),

    ("figado",    "Figado",    LRNJ, "Digestivo",
     int(242*230/679), int(372*551/710), int(178*230/679), int(41*551/710)),

    ("intestino", "Intestinos",AMAR, "Digestivo",
     int(254*230/679), int(423*551/710), int(190*230/679), int(83*551/710)),

    # Pendentes de mapeamento no torso:
    # olhos, orelha, tireoide, estomago, baco

    # ── SECAO 2: SISTEMA URINARIO (x base = 230) ─────────────────────────────
    # A mapear -- usar main_test_silhueta.py e clicar nos orgaos do urinario

    # ── SECAO 3: ESQUELETO (x base = 420) ────────────────────────────────────
    # A mapear -- usar main_test_silhueta.py e clicar nas regioes do esqueleto
]

# Lista publica de orgaos (usada pelo hub para montar o menu)
ORGAOS = [
    {"id": h[0], "label": h[1], "cor": h[2], "sistema": h[3]}
    for h in HOTSPOTS_RAW
]


def criar_silhueta(
    page: ft.Page,
    on_orgao_click,
    largura: int = 600,
    mostrar_borda: bool = False,
) -> ft.Container:
    """
    Retorna ft.Container com as 3 imagens anatomicas e hotspots clicaveis.

    Args:
        page: ft.Page atual
        on_orgao_click: callable(id: str) chamado ao tocar num orgao
        largura: largura total em pixels (altura proporcional 644:551)
        mostrar_borda: True = exibe borda dos hotspots (modo debug/calibracao)
    """
    escala = largura / IMG_W
    altura = int(IMG_H * escala)

    _dir     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    img_path = os.path.join(_dir, "assets", "silueta_anatomia.png")

    if not os.path.isfile(img_path):
        log.warning("[SILHUETA] silueta_anatomia.png nao encontrado em %s", _dir)
        return ft.Container(
            width=largura, height=altura, bgcolor=CARD,
            content=ft.Text("silueta_anatomia.png nao encontrado", color=SEC, size=11),
            alignment=ft.alignment.center,
        )

    fundo = ft.Image(
        src=img_path,
        width=largura,
        height=altura,
        fit=ft.ImageFit.FILL,
    )

    # Linhas divisoras das secoes (visivel apenas no modo debug)
    divisoras = []
    if mostrar_borda:
        for x_orig, cor_div in [(230, "#FF444466"), (420, "#FF444466")]:
            x_esc = int(x_orig * escala)
            divisoras.append(ft.Container(
                left=x_esc, top=0,
                width=1, height=altura,
                bgcolor="#FF4444",
            ))

    # Hotspots
    hotspots = []
    for (oid, label, cor, sistema, rx, ry, rw, rh) in HOTSPOTS_RAW:
        x = int(rx * escala)
        y = int(ry * escala)
        w = max(int(rw * escala), 20)
        h = max(int(rh * escala), 20)

        area = ft.Container(
            width=w, height=h,
            border_radius=8,
            bgcolor=ft.Colors.with_opacity(0.0, cor),
            border=ft.border.all(
                1.5, ft.Colors.with_opacity(0.7 if mostrar_borda else 0.0, cor)),
            ink=True,
            ink_color=ft.Colors.with_opacity(0.35, cor),
            tooltip=label,
        )

        def _click(e, _id=oid):
            on_orgao_click(_id)

        area.on_click = _click
        hotspots.append(ft.Container(content=area, left=x, top=y))

    stack = ft.Stack(
        controls=[fundo, *divisoras, *hotspots],
        width=largura,
        height=altura,
    )

    return ft.Container(
        content=stack,
        width=largura,
        height=altura,
        border_radius=12,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )
