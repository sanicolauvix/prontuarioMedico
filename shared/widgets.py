# -*- coding: utf-8 -*-
# Prontuario Medico | shared/widgets.py -- componentes reutilizaveis
"""
PainelSelecaoExame
  Encapsula o fluxo completo de selecao de exames:
    modo BUSCA     -> campo de texto + lista filtavel
    modo RESULTADO -> chips + spinner + grafico + detalhe

  Uso:
    from shared.widgets import PainelSelecaoExame
    painel = PainelSelecaoExame(page=page, itens=lista, ...)
    area.controls.extend(painel.controles())
"""

import flet as ft

BG   = "#0D1117";  CARD = "#161B22";  BD  = "#21262D";  BD2  = "#30363D"
TXT  = "#E6EDF3";  SEC  = "#8B949E";  MUT = "#484F58"
AZUL = "#58A6FF";  VERD = "#3FB950";  LAR = "#F0883E"
VERM = "#DA3633";  ROXO = "#BC8CFF";  AMAR= "#D29922"


class PainelSelecaoExame:
    """
    Componente reutilizavel de selecao + visualizacao de exames.

    Parametros
    ----------
    page          : ft.Page
    itens         : list[dict] -- exames disponíveis para este contexto
    fn_historico  : callable(exame_padrao_id) -> list[dict]
    fn_laudos     : callable(nome) -> list[dict]
    hint_busca    : str -- placeholder do campo de busca
    max_numericos : int -- maximo de exames numericos simultaneos
    fn_renderizar_grafico : callable(page, selecionados) -> ft.Control
    """

    def __init__(self, page: ft.Page, itens: list,
                 fn_historico, fn_laudos,
                 hint_busca: str = "Buscar exame...",
                 max_numericos: int = 5,
                 fn_renderizar_grafico=None):
        self.page          = page
        self.itens         = itens
        self.fn_historico  = fn_historico
        self.fn_laudos     = fn_laudos
        self.hint_busca    = hint_busca
        self.max_numericos = max_numericos
        self._fn_graf      = fn_renderizar_grafico
        self._selecionados = []
        self._build()

    def _build(self):
        self._txt_busca = ft.TextField(
            hint_text=self.hint_busca,
            bgcolor=CARD, border_color=BD2,
            focused_border_color=AZUL,
            hint_style=ft.TextStyle(color=MUT),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, height=44,
            prefix_icon="search_rounded",
            visible=True,
        )
        self._txt_busca.on_change = self._filtrar

        self._lista    = ft.Column(spacing=4, visible=True)
        self._txt_info = ft.Text("", size=12, color=LAR, visible=True)
        self._chips    = ft.Row(wrap=True, spacing=6, visible=False)

        self._btn_add = ft.Container(
            content=ft.Row([
                ft.Icon("add_circle_outline_rounded", size=14, color=AZUL),
                ft.Text("Adicionar exame", size=12, color=AZUL,
                        weight=ft.FontWeight.W_500),
            ], spacing=6, tight=True),
            bgcolor=CARD, border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border=ft.Border(
                top=ft.BorderSide(1, BD2), bottom=ft.BorderSide(1, BD2),
                left=ft.BorderSide(1, BD2), right=ft.BorderSide(1, BD2),
            ),
            visible=False,
            ink=True,
        )
        self._btn_add.on_click = lambda e: self._modo_busca()

        self._spinner = ft.Container(
            content=ft.Row([
                ft.ProgressRing(width=20, height=20, stroke_width=2, color=AZUL),
                ft.Column([
                    ft.Text("Gerando grafico...", size=13, color=TXT,
                            weight=ft.FontWeight.W_500),
                    ft.Text("Aguarde um momento", size=11, color=SEC),
                ], spacing=2),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=CARD, border_radius=8,
            padding=ft.padding.symmetric(horizontal=16, vertical=14),
            border=ft.Border(
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                left=ft.BorderSide(3, AZUL), right=ft.BorderSide(1, BD),
            ),
            visible=False,
        )

        self._col_resultado = ft.Column([self._spinner], spacing=10, visible=False)
        self._subscribed    = [False]
        self._filtrar()

    def _modo_busca(self):
        self._txt_busca.value       = ""
        self._txt_busca.visible     = True
        self._lista.visible         = True
        self._txt_info.visible      = True
        self._btn_add.visible       = False
        self._col_resultado.visible = False
        self._txt_info.value        = ""
        self._lista.controls.clear()
        self._filtrar()

    def _modo_resultado(self):
        self._txt_busca.visible = False
        self._lista.visible     = False
        self._txt_info.visible  = False
        self._btn_add.visible   = True
        self._renderizar_grafico()

    def _rebuild_chips(self):
        self._chips.controls.clear()
        if not self._selecionados:
            self._chips.visible = False
            return
        self._chips.visible = True
        for i, ex in enumerate(self._selecionados):
            def _rem(e, idx=i):
                self._selecionados.pop(idx)
                self._rebuild_chips()
                if self._selecionados:
                    self._renderizar_grafico()
                else:
                    self._limpar()
                try: self.page.update()
                except Exception: pass

            chip = ft.Container(
                content=ft.Row([
                    ft.Text(ex["nome_oficial"], size=11, color=TXT),
                    ft.Icon("close_rounded", size=11, color=SEC),
                ], spacing=4, tight=True),
                bgcolor=BD, border_radius=12,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                ink=True,
            )
            chip.on_click = _rem
            self._chips.controls.append(chip)

        btn_limpar = ft.Container(
            content=ft.Text("Limpar tudo", size=11, color=LAR),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=6, ink=True,
        )
        btn_limpar.on_click = lambda e: self._limpar_tudo()
        self._chips.controls.append(btn_limpar)

    def _limpar_tudo(self):
        self._selecionados.clear()
        self._rebuild_chips()
        self._limpar()

    def _limpar(self):
        self._spinner.visible = False
        self._col_resultado.controls.clear()
        self._col_resultado.controls.append(self._spinner)
        self._col_resultado.visible = False
        self._btn_add.visible       = False
        self._modo_busca()

    def adicionar(self, exame: dict):
        if any(s["id"] == exame["id"] for s in self._selecionados):
            return "Exame ja selecionado."
        numericos = [s for s in self._selecionados if s.get("tipo") == "numerico"]
        if exame.get("tipo") == "numerico" and len(numericos) >= self.max_numericos:
            return f"Maximo {self.max_numericos} exames numericos."
        if exame.get("tipo") == "numerico":
            exame["historico"] = self.fn_historico(exame["id"])
        else:
            exame["historico"] = self.fn_laudos(exame.get("nome_oficial", ""))
        self._selecionados.append(exame)
        self._rebuild_chips()
        self._modo_resultado()
        return None

    def _filtrar(self, e=None):
        self._lista.controls.clear()
        q       = (self._txt_busca.value or "").strip().upper()
        ids_sel = {s["id"] for s in self._selecionados}

        encontrados = [
            ex for ex in self.itens
            if ex.get("id") not in ids_sel
            and (not q or q in ex["nome_oficial"].upper())
        ][:10]

        for ex in encontrados:
            eh_laudo = ex.get("tipo") in ("laudo", "imagem", "mapa")
            cor  = ROXO if eh_laudo else AZUL
            cat  = ex.get("categoria") or ""
            qtd  = ex.get("qtd", 0)
            sub  = cat + (f"  .  {qtd}x" if qtd else "")
            icone = "description_rounded" if eh_laudo else "show_chart_rounded"

            def _add(e, exame=ex):
                err = self.adicionar(exame)
                if err:
                    self._txt_info.value   = err
                    self._txt_info.visible = True
                    try: self.page.update()
                    except Exception: pass

            item = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(icone, size=14, color=cor),
                        bgcolor=f"{cor}18", border_radius=6,
                        width=30, height=30,
                        alignment=ft.alignment.Alignment(0, 0),
                    ),
                    ft.Column([
                        ft.Text(ex["nome_oficial"], size=12, color=TXT,
                                weight=ft.FontWeight.W_500),
                        ft.Text(sub, size=10, color=MUT),
                    ], spacing=1, expand=True),
                    ft.Icon("add_circle_outline_rounded", size=16, color=cor),
                ], spacing=8,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                border_radius=6, bgcolor=CARD,
                border=ft.Border(
                    top=ft.BorderSide(1, BD),   bottom=ft.BorderSide(1, BD),
                    left=ft.BorderSide(2, cor), right=ft.BorderSide(1, BD),
                ),
                ink=True,
            )
            item.on_click = _add
            self._lista.controls.append(item)

        try: self.page.update()
        except Exception: pass

    def _renderizar_grafico(self):
        import threading
        import logging as _lg

        if not self._selecionados:
            return

        self._spinner.visible = True
        self._col_resultado.controls.clear()
        self._col_resultado.controls.append(self._spinner)
        self._col_resultado.visible = True
        try: self.page.update()
        except Exception: pass

        _sel = list(self._selecionados)

        def _montar():
            controles = []
            numericos = [s for s in _sel if s.get("tipo") == "numerico"]
            laudos    = [s for s in _sel if s.get("tipo") not in ("numerico",)]
            if numericos:
                try:
                    if self._fn_graf:
                        controles.append(self._fn_graf(self.page, numericos))
                    else:
                        from telas.tela_exames import renderizar_grafico_combinado
                        controles.append(
                            renderizar_grafico_combinado(self.page, numericos))
                except Exception as ex:
                    _lg.error("[PAINEL] grafico: %s", ex)
                    controles.append(
                        ft.Text(f"Grafico indisponivel: {ex}", size=11, color=LAR))
            for laudo in laudos:
                try:
                    from telas.tela_exames import renderizar_card_laudo
                    controles.append(renderizar_card_laudo(self.page, laudo))
                except Exception as ex:
                    _lg.error("[PAINEL] laudo: %s", ex)
            self.page.pubsub.send_all(
                {"_tipo": "painel_grafico_pronto", "controles": controles})

        def _on_msg(msg):
            if not isinstance(msg, dict):
                return
            if msg.get("_tipo") != "painel_grafico_pronto":
                return
            self._spinner.visible = False
            self._col_resultado.controls.clear()
            for c in msg["controles"]:
                self._col_resultado.controls.append(c)
            self._col_resultado.visible = True
            try: self.page.update()
            except Exception: pass

        if not self._subscribed[0]:
            self.page.pubsub.subscribe(_on_msg)
            self._subscribed[0] = True

        threading.Thread(target=_montar, daemon=True).start()

    def controles(self) -> list:
        return [
            self._txt_busca,
            self._lista,
            self._txt_info,
            self._chips,
            self._btn_add,
            self._col_resultado,
        ]

    def set_itens(self, itens: list):
        self.itens = itens
        self._limpar_tudo()
