# -*- coding: utf-8 -*-
# Prontuario | telas/tela_codigos_medico.py
# Gestao de codigos de acesso para medicos
import flet as ft
import logging
from shared.layout import Layout

log = logging.getLogger(__name__)

BG    = "#0D1117"; CARD  = "#161B22"; BD   = "#21262D"; BD2   = "#30363D"
TXT   = "#E6EDF3"; SEC   = "#8B949E"; MUT  = "#484F58"
AZUL  = "#58A6FF"; VERD  = "#3FB950"; VERM = "#FF4444"; AMAR  = "#D29922"


def criar_tela_codigos_medico(page: ft.Page, voltar_fn) -> ft.Container:
    lay     = Layout(page)
    area    = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
    _montado = [False]

    def _upd():
        if _montado[0]:
            try: page.update()
            except Exception: pass

    def _rebuild():
        from dados.model_prontuario import listar_codigos_acesso
        area.controls.clear()

        codigos = listar_codigos_acesso()

        # campo + botao para gerar novo codigo
        f_nome = ft.TextField(
            label="Nome do médico",
            hint_text="Ex: Dr. João Silva",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, expand=True,
        )

        btn_gerar = ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=14, color=BG),
                ft.Text("Gerar Código", size=13, color=BG, weight=ft.FontWeight.W_600),
            ], spacing=6, tight=True),
            bgcolor=AZUL, border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
        )

        def _gerar(e=None):
            nome = (f_nome.value or "").strip()
            if not nome:
                f_nome.error_text = "Informe o nome do médico"
                _upd()
                return
            f_nome.error_text = None
            from dados.model_prontuario import gerar_codigo_acesso
            from backup.backup_watcher import notify_db_changed
            codigo = gerar_codigo_acesso(nome)
            if codigo:
                f_nome.value = ""
                notify_db_changed()
                _rebuild()
                _snack(f"Código gerado: {codigo}", VERD)
            else:
                _snack("Erro ao gerar código", VERM)

        btn_gerar.on_click = _gerar

        area.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Text("Novo Acesso", size=12, color=SEC,
                            weight=ft.FontWeight.W_600),
                    ft.Container(height=6),
                    ft.Row([f_nome, btn_gerar], spacing=8),
                ], spacing=4),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.all(14),
                border=ft.border.all(1, BD),
            )
        )

        area.controls.append(ft.Container(height=4))

        # lista de codigos
        ativos   = [c for c in codigos if c["ativo"]]
        revogados = [c for c in codigos if not c["ativo"]]

        if not codigos:
            area.controls.append(
                ft.Container(
                    content=ft.Text("Nenhum código gerado ainda.",
                                    size=13, color=SEC, text_align="center"),
                    alignment=ft.alignment.center,
                    padding=ft.padding.all(32),
                )
            )
        else:
            if ativos:
                area.controls.append(
                    ft.Text("Ativos", size=11, color=VERD,
                            weight=ft.FontWeight.W_700)
                )
                for c in ativos:
                    area.controls.append(_card_codigo(c, ativo=True))

            if revogados:
                area.controls.append(ft.Container(height=8))
                area.controls.append(
                    ft.Text("Revogados", size=11, color=MUT,
                            weight=ft.FontWeight.W_700)
                )
                for c in revogados:
                    area.controls.append(_card_codigo(c, ativo=False))

        _upd()

    def _card_codigo(c: dict, ativo: bool) -> ft.Container:
        cor = VERD if ativo else MUT

        # codigo em fonte monoespaco grande
        txt_codigo = ft.Text(
            c["codigo"], size=18, color=cor,
            weight=ft.FontWeight.W_700,
            font_family="monospace",
        )

        def _copiar(e=None):
            page.set_clipboard(c["codigo"])
            _snack(f"Código copiado: {c['codigo']}", AZUL)

        btn_copiar = ft.Container(
            content=ft.Icon("content_copy_rounded", size=16, color=AZUL),
            ink=True, border_radius=6,
            padding=ft.padding.all(6),
            tooltip="Copiar código",
        )
        btn_copiar.on_click = _copiar

        acoes = []
        if ativo:
            btn_revogar = ft.Container(
                content=ft.Row([
                    ft.Icon("block_rounded", size=13, color=VERM),
                    ft.Text("Revogar", size=12, color=VERM),
                ], spacing=4, tight=True),
                ink=True, border_radius=6,
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                bgcolor=f"{VERM}18",
            )
            def _revogar(e=None, cid=c["id"]):
                from dados.model_prontuario import revogar_codigo_acesso
                from backup.backup_watcher import notify_db_changed
                if revogar_codigo_acesso(cid):
                    notify_db_changed()
                    _rebuild()
                    _snack("Código revogado", AMAR)
            btn_revogar.on_click = _revogar
            acoes.append(btn_copiar)
            acoes.append(btn_revogar)
        else:
            acoes.append(btn_copiar)

        # data formatada
        data = c.get("criado_em", "")[:10]
        try:
            from datetime import datetime
            data = datetime.strptime(data, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            pass

        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(c["nome_medico"], size=13, color=TXT,
                            weight=ft.FontWeight.W_600),
                    txt_codigo,
                    ft.Text(f"Gerado em {data}", size=10, color=MUT),
                ], spacing=2, tight=True, expand=True),
                ft.Row(acoes, spacing=4),
            ], spacing=12),
            bgcolor=CARD,
            border_radius=10,
            padding=ft.padding.all(14),
            border=ft.border.all(1, f"{cor}44"),
            opacity=1.0 if ativo else 0.5,
        )

    def _snack(msg: str, cor: str = AZUL):
        s = ft.SnackBar(content=ft.Text(msg, color=TXT), bgcolor=CARD)
        page.overlay.append(s)
        s.open = True
        try: page.update()
        except Exception: pass

    _rebuild()

    cabecalho = lay.criar_cabecalho(
        "Acessos Médicos", voltar_fn,
        icone_titulo="medical_services_rounded",
        cor_titulo=AZUL,
    )
    corpo = lay.criar_corpo(cabecalho, area)
    _montado[0] = True
    return ft.Container(bgcolor=BG, expand=True, content=corpo)
