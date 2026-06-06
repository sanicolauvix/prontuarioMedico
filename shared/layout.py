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

    # ── Overlays padrao Koios ────────────────────────────────────────────────

    _BORDA2 = "#30363D"
    _CARD   = "#161B22"
    _TXT    = "#E6EDF3"
    _SEC    = "#8B949E"
    _AZUL2  = "#58A6FF"
    _VERM   = "#FF4444"

    def loading(
        self,
        msg: str = "Aguarde...",
        cor_spinner: str = "",
        cor_fundo: str = "",
        cor_txt: str = "",
    ):
        """
        Overlay bloqueante com spinner + mensagem.
        Padrao Koios para qualquer operacao assincrona (upload, sync, IA...).

        Uso:
            fechar = lay.loading("Enviando foto...")
            # ... operacao assincrona ...
            fechar()   # remove o overlay

        Retorna funcao _fechar() que remove o overlay ao ser chamada.
        """
        spin = cor_spinner or self._AZUL2
        bg   = cor_fundo   or self._CARD
        txt  = cor_txt     or self._TXT
        ov   = [None]

        def _fechar():
            if ov[0] and ov[0] in self.page.overlay:
                self.page.overlay.remove(ov[0])
            try: self.page.update()
            except Exception: pass

        ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.ProgressRing(width=32, height=32, stroke_width=3, color=spin),
                    ft.Container(height=12),
                    ft.Text(msg, size=13, color=txt, weight=ft.FontWeight.W_600,
                            text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   alignment=ft.MainAxisAlignment.CENTER, tight=True, spacing=0),
                bgcolor=bg, border_radius=14,
                padding=ft.padding.symmetric(horizontal=32, vertical=24),
                border=ft.Border(
                    top=ft.BorderSide(1, self._BORDA2),
                    bottom=ft.BorderSide(1, self._BORDA2),
                    left=ft.BorderSide(1, self._BORDA2),
                    right=ft.BorderSide(1, self._BORDA2),
                ),
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        self.page.overlay.append(ov[0])
        try: self.page.update()
        except Exception: pass
        return _fechar

    def upload_foto_com_loading(
        self,
        path_abs: str,
        pasta_drive: str,
        on_concluido=None,
        on_erro=None,
        nome_arquivo: str = "",
        msg_loading: str = "Enviando foto...",
    ) -> None:
        """
        Padrao Koios completo de upload de foto:
          1. Exibe overlay loading
          2. Faz upload em background via upload_foto_imediato
          3. Fecha loading ao concluir ou ao errar
          4. Chama on_concluido(drive_id, nome) ou on_erro(msg)

        Uso:
            lay.upload_foto_com_loading(
                path_abs   = "/path/local/foto.jpg",
                pasta_drive= "fotos/clientes/42",
                on_concluido = lambda fid, nome: salvar_no_banco(fid, nome),
                on_erro      = lambda msg: snack(f"Erro: {msg}"),
            )
        """
        fechar = self.loading(msg_loading)

        def _ok(drive_id, nome):
            fechar()
            if on_concluido:
                on_concluido(drive_id, nome)

        def _err(msg):
            fechar()
            if on_erro:
                on_erro(msg)

        from utils.foto_picker import upload_foto_imediato
        upload_foto_imediato(
            self.page, path_abs, pasta_drive,
            on_concluido=_ok,
            on_erro=_err,
            nome_arquivo=nome_arquivo,
        )
