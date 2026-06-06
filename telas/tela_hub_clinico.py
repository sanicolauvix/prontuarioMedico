# -*- coding: utf-8 -*-
import flet as ft
from shared.layout import Layout

BG = "#0D1117"; CARD = "#161B22"; BD = "#21262D"
TXT = "#E6EDF3"; SEC = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; VERM = "#FF4444"
ROXO = "#BC8CFF"; AMAR = "#D29922"


def criar_tela_hub_clinico(page: ft.Page, voltar_fn, ir_fn, lazy_fn) -> ft.Container:
    lay = Layout(page)

    def _btn(icone, label, desc, cor, fn):
        c = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icone, size=15, color=cor),
                    bgcolor=ft.Colors.with_opacity(0.10, cor),
                    border_radius=8, width=32, height=32,
                    alignment=ft.alignment.Alignment(0, 0),
                ),
                ft.Column([
                    ft.Text(label, size=13, color=TXT, weight=ft.FontWeight.W_500),
                    ft.Text(desc, size=10, color=SEC),
                ], spacing=0, tight=True, expand=True),
                ft.Icon("chevron_right_rounded", size=16, color=MUT),
            ], spacing=12),
            bgcolor=CARD,
            padding=ft.padding.symmetric(horizontal=16, vertical=11),
            border=ft.Border(bottom=ft.BorderSide(1, BD)),
            ink=True,
        )
        c.on_click = lambda e: fn()
        return c

    itens = [
        _btn("health_and_safety_rounded", "Checkup de Saude",
             "Visao geral — alertas, sistemas e tendencias", VERD,
             lazy_fn("tela_checkup", "criar_tela_checkup")),
        _btn("favorite_rounded", "Sistema Cardiaco",
             "Diagnosticos, exames, historico, medicos e remedios", "#FF6B6B",
             lazy_fn("tela_orgao_cardiaco", "criar_tela_orgao_cardiaco")),
        _btn("diagnosis_rounded", "Diagnosticos",
             "Todos os diagnosticos medicos", AZUL,
             lazy_fn("tela_diagnosticos", "criar_tela_diagnosticos")),
        _btn("event_note_rounded", "Compromissos",
             "Consultas, coletas e fisioterapia", VERD,
             lazy_fn("tela_compromissos", "criar_tela_compromissos")),
        _btn("medication_rounded", "Medicacao",
             "Remedios e suplementos", AMAR,
             lazy_fn("tela_remedios", "criar_tela_remedios")),
        _btn("storefront_rounded", "Fornecedores",
             "Farmacias e fornecedores", ROXO,
             lazy_fn("tela_fornecedores", "criar_tela_fornecedores")),
        _btn("today_rounded", "Rotinas Diarias",
             "Agua do dia e rotinas de habitos", AZUL,
             lazy_fn("tela_rotina_diaria", "criar_tela_rotina_diaria")),
        _btn("psychology_rounded", "Claudia IA",
             "Conversar com Claudia", ROXO,
             lazy_fn("tela_claudia", "criar_tela_claudia")),
        _btn("biotech_rounded", "Marcadores",
             "Sinais vitais e historico", "#4ECDC4",
             lazy_fn("tela_marcadores", "criar_tela_marcadores")),
        _btn("timeline_rounded", "Historico Clinico",
             "Linha do tempo e alertas clinicos", VERM,
             lazy_fn("tela_historico_clinico", "criar_tela_historico_clinico")),
        _btn("folder_open_rounded", "Prontuarios",
             "PDFs importados e paginas", ROXO,
             lazy_fn("tela_prontuarios", "criar_tela_prontuarios")),
        _btn("analytics_rounded", "Diagnosticos (todos)",
             "CID, certeza e tipo por internacao", AMAR,
             lazy_fn("tela_diagnosticos", "criar_tela_diagnosticos")),
    ]

    area = ft.Column([
        ft.Container(
            content=ft.Column(itens, spacing=0),
            bgcolor=CARD, border_radius=12,
            border=ft.border.all(1, BD),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        ),
    ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    cab = lay.criar_cabecalho("Clinico", voltar_fn,
                              icone_titulo="health_and_safety_rounded",
                              cor_titulo=VERD)
    corpo = lay.criar_corpo(cab, area)
    return ft.Container(bgcolor=BG, expand=True, content=corpo)
