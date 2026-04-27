# -*- coding: utf-8 -*-
# SHARED | shared/layout.py -- gerenciado por flet_shared/sync_shared.py
# Helpers de responsividade -- use em todas as telas
#
# USO:
#   from shared.layout import Layout
#   lay = Layout(page)
#   lay.mobile      -> True se celular/Android
#   lay.padding_h   -> padding horizontal da tela
#   lay.card_width  -> largura maxima de cards
#   lay.wrap(conteudo) -> centraliza no desktop, expande no mobile

import flet as ft
from shared.auth import IS_ANDROID


class Layout:
    """
    Responsividade centralizada.
    Instanciar no inicio de cada tela:
        lay = Layout(page)
    """

    def __init__(self, page: ft.Page):
        self.page    = page
        self._width  = self._get_width()
        self.mobile  = IS_ANDROID or self._width < 600

    def _get_width(self) -> float:
        try:
            return float(self.page.width or 800)
        except Exception:
            return 800

    #  Dimensoes

    @property
    def padding_h(self) -> int:
        """Padding horizontal padrao da tela."""
        return 16 if self.mobile else 32

    @property
    def padding_v(self) -> int:
        """Padding vertical padrao."""
        return 12 if self.mobile else 20

    @property
    def card_width(self) -> float:
        """Largura maxima de cards e formularios."""
        if self.mobile:
            return self._width
        return min(self._width, 520)

    @property
    def font_titulo(self) -> int:
        return 18 if self.mobile else 22

    @property
    def font_corpo(self) -> int:
        return 13 if self.mobile else 14

    @property
    def font_label(self) -> int:
        return 11 if self.mobile else 12

    @property
    def icon_size(self) -> int:
        return 20 if self.mobile else 22

    @property
    def btn_height(self) -> int:
        """Altura dos botoes de acao."""
        return 48 if self.mobile else 44

    @property
    def spacer_topo(self) -> int:
        """Espaco no topo para nao colar na barra de status."""
        return 28 if self.mobile else 0

    #  Layout helpers

    def wrap(self, conteudo: ft.Control) -> ft.Control:
        """
        No mobile: retorna o conteudo expandido.
        No desktop: centraliza em coluna com largura maxima.
        """
        if self.mobile:
            return conteudo
        return ft.Row([
            ft.Container(expand=True),
            ft.Container(content=conteudo, width=self.card_width),
            ft.Container(expand=True),
        ], expand=True)

    def padding_tela(self) -> ft.Padding:
        """Padding padrao para o corpo da tela."""
        return ft.padding.symmetric(
            horizontal=self.padding_h,
            vertical=self.padding_v,
        )

    def cabecalho_padding(self) -> ft.Padding:
        """Padding do cabecalho -- considera barra de status no mobile."""
        return ft.padding.only(
            left=self.padding_h,
            right=8,
            top=self.spacer_topo + 4,
            bottom=6,
        )

    # ──────────────────────────────────────────────────────────────────
    #  Construtores de cabecalho padrao
    # ──────────────────────────────────────────────────────────────────

    # Paleta centralizada -- igual em todos os apps
    _BG    = "#0D1117"
    _CARD  = "#161B22"
    _BORDA = "#21262D"
    _TXT   = "#E6EDF3"
    _AZUL  = "#58A6FF"

    def criar_cabecalho(
        self,
        titulo: str,
        voltar_fn,
        icone_titulo: str = "",
        cor_titulo: str = "#E6EDF3",
        acoes: list = None,
    ) -> ft.Container:
        """
        Retorna o cabecalho padrao (btn_voltar + titulo + acoes opcionais).

        Uso:
            lay = Layout(page)
            cab = lay.criar_cabecalho(
                "Clientes", voltar_fn,
                icone_titulo="people_rounded", cor_titulo=VERD,
                acoes=[btn_novo],
            )

        acoes: lista de ft.Container (botoes no lado direito).
        """
        btn_voltar = ft.Container(
            content=ft.Row(
                [
                    ft.Icon("arrow_back", size=16, color=self._AZUL),
                    ft.Text("Voltar", size=13, color=self._AZUL),
                ],
                spacing=4, tight=True,
            ),
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            border_radius=8, ink=True,
        )
        btn_voltar.on_click = lambda e: voltar_fn()

        titulo_items = []
        if icone_titulo:
            titulo_items.append(ft.Icon(icone_titulo, size=20, color=cor_titulo))
        titulo_items.append(
            ft.Text(titulo, size=18, weight=ft.FontWeight.W_700, color=self._TXT)
        )
        titulo_row = ft.Row(titulo_items, spacing=8, tight=True)

        lado_direito = ft.Row(acoes or [], spacing=4, tight=True)

        return ft.Container(
            content=ft.Row(
                [btn_voltar, titulo_row, lado_direito],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=self.cabecalho_padding(),
            border=ft.Border(bottom=ft.BorderSide(1, self._BORDA)),
        )

    def criar_corpo(
        self,
        cabecalho: ft.Container,
        area: ft.Control,
        padding_area: ft.Padding = None,
    ) -> ft.Column:
        """
        Retorna o corpo padrao da tela: spacer_topo + cabecalho + area.

        Uso:
            corpo = lay.criar_corpo(cabecalho, area_principal)
            return ft.Container(bgcolor=BG, expand=True, content=corpo)
        """
        return ft.Column(
            [
                ft.Container(height=self.spacer_topo, bgcolor=self._BG),
                cabecalho,
                ft.Container(
                    content=area,
                    padding=padding_area or self.padding_tela(),
                    expand=True,
                ),
            ],
            expand=True, spacing=0,
        )
