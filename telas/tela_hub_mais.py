# -*- coding: utf-8 -*-
import flet as ft
from shared.layout import Layout

BG = "#0D1117"; CARD = "#161B22"; BD = "#21262D"
TXT = "#E6EDF3"; SEC = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; VERM = "#FF4444"
ROXO = "#BC8CFF"; AMAR = "#D29922"


def criar_tela_hub_mais(page: ft.Page, voltar_fn, ir_fn, lazy_fn) -> ft.Container:
    lay = Layout(page)

    def _item(icon, label, desc, cor, fn):
        c = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icon, size=15, color=cor),
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

    def _group(titulo, cor, icone, items):
        return ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Icon(icone, size=12, color=cor),
                    ft.Text(titulo, size=10, weight=ft.FontWeight.W_700, color=cor),
                ], spacing=6),
                padding=ft.padding.only(bottom=6, top=4),
            ),
            ft.Container(
                content=ft.Column(items, spacing=0),
                bgcolor=CARD, border_radius=12,
                border=ft.border.all(1, BD),
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            ),
        ], spacing=4)

    def _nav_perfil():
        lazy_fn("tela_perfil", "criar_tela_perfil")()

    area = ft.Column([
        _group("EXAMES", AZUL, "folder_open_rounded", [
            _item("analytics_rounded", "Historico",
                  "Graficos e evolucao", VERD,
                  lazy_fn("tela_exames", "criar_tela_consulta")),
            _item("description_rounded", "Processados",
                  "Exames importados", AMAR,
                  lazy_fn("tela_exames_processados", "criar_tela_exames_processados")),
            _item("science_rounded", "Exames Padrao",
                  "Referencias e cadastro", ROXO,
                  lazy_fn("tela_exames_padrao", "criar_tela_exames_padrao")),
            _item("local_hospital_rounded", "Especialidades",
                  "Areas medicas", AMAR,
                  lazy_fn("tela_especialidades", "criar_tela_especialidades")),
            _item("biotech_rounded", "Laboratorios",
                  "Labs e extratores", VERM,
                  lazy_fn("tela_laboratorios", "criar_tela_laboratorios")),
        ]),
        _group("MEDICOS", ROXO, "people_rounded", [
            _item("people_rounded", "Medicos",
                  "Cadastro e historico", ROXO,
                  lazy_fn("tela_medicos", "criar_tela_medicos")),
            _item("local_hospital_rounded", "Clinicas",
                  "Locais de atendimento", AZUL,
                  lazy_fn("tela_clinicas", "criar_tela_clinicas")),
            _item("storefront_rounded", "Fornecedores",
                  "Farmacias e fornecedores", VERD,
                  lazy_fn("tela_fornecedores", "criar_tela_fornecedores")),
            _item("link_rounded", "Links Medico",
                  "Tokens de acesso", AZUL,
                  lazy_fn("tela_links_medico", "criar_tela_links_medico")),
        ]),
        _group("CONFIGURACOES", SEC, "settings_rounded", [
            _item("person_rounded", "Perfil", "Dados pessoais", SEC, _nav_perfil),
            _item("settings_rounded", "Configuracoes",
                  "Backup e Drive", SEC,
                  lazy_fn("telas_sistema.tela_config", "criar_tela_config")),
            _item("medical_services_rounded", "Acessos Medicos",
                  "Gerar e revogar codigos", AZUL,
                  lazy_fn("telas.tela_codigos_medico", "criar_tela_codigos_medico")),
        ]),
    ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    cab = lay.criar_cabecalho("Mais", voltar_fn,
                              icone_titulo="grid_view_rounded",
                              cor_titulo=SEC)
    corpo = lay.criar_corpo(cab, area)
    return ft.Container(bgcolor=BG, expand=True, content=corpo)
