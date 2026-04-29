# -*- coding: utf-8 -*-
"""
tela_especialidades.py - Cadastro de especialidades médicas
Acessível via tela de médicos (botão Especialidades)
"""
import flet as ft
from dados.model_prontuario import listar_especialidades, salvar_especialidade, excluir_especialidade


COR  = "#BC8CFF"
VERM = "#DA3633"
SEC  = "#8B949E"
BD   = "#21262D"


def criar_tela_especialidades(page: ft.Page, voltar_fn):

    lista     = ft.Column(spacing=6)
    txt_busca = ft.TextField(
        label="Buscar especialidade",
        prefix_icon="search_rounded",
        bgcolor="#161B22", border_color="#30363D",
        focused_border_color=COR,
        label_style=ft.TextStyle(color="#8B949E"),
        text_style=ft.TextStyle(color="#E6EDF3"),
        border_radius=8, expand=True,
    )

    def _snack(msg, cor="#3FB950"):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, color="#E6EDF3"), bgcolor="#161B22")
        page.snack_bar.open = True
        page.update()

    def carregar(filtro=""):
        lista.controls.clear()
        esps = listar_especialidades(so_ativas=False)
        if filtro:
            esps = [e for e in esps if filtro.upper() in e["nome"].upper()]

        if not esps:
            lista.controls.append(ft.Container(
                content=ft.Text("Nenhuma especialidade encontrada.",
                                color="#8B949E", size=13),
                padding=20,
            ))
            page.update()
            return

        for esp in esps:
            ativo   = esp.get("ativo", 1)
            cor_dot = "#3FB950" if ativo else "#484F58"

            def make_editar(e_item):
                def click(e): abrir_ficha(e_item)
                return click

            def make_excluir(e_item):
                def click(e): confirmar_exclusao(e_item)
                return click

            lista.controls.append(ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Text(esp["nome"], size=13, color="#E6EDF3",
                                weight=ft.FontWeight.W_600),
                        ft.Text(esp.get("descricao") or "Sem descrição",
                                size=11, color="#8B949E"),
                    ], spacing=2, expand=True),
                    ft.Container(width=8, height=8, bgcolor=cor_dot, border_radius=4),
                    ft.IconButton(
                        "edit_rounded", icon_size=16, icon_color="#484F58",
                        tooltip="Editar",
                        on_click=make_editar(esp),
                        padding=ft.padding.all(4),
                    ),
                    ft.IconButton(
                        "delete_outline_rounded", icon_size=16, icon_color=VERM,
                        tooltip="Excluir",
                        on_click=make_excluir(esp),
                        padding=ft.padding.all(4),
                    ),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor="#161B22", border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                border=ft.Border(
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    left=ft.BorderSide(1, BD), right=ft.BorderSide(1, BD),
                ),
                opacity=1.0 if ativo else 0.5,
            ))
        page.update()

    def filtrar(e):
        carregar(txt_busca.value or "")

    txt_busca.on_change = filtrar

    def confirmar_exclusao(esp):
        ref = [None]

        def _fechar(e=None):
            if ref[0] and ref[0] in page.overlay:
                page.overlay.remove(ref[0])
            try: page.update()
            except Exception: pass

        def _excluir(e):
            _fechar()
            ok = excluir_especialidade(esp["id"])
            if ok:
                _snack(f"'{esp['nome']}' excluida.")
            else:
                _snack("Nao e possivel excluir — ha medicos vinculados.", VERM)
            carregar()

        btn_cancel = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=8, bgcolor=f"{SEC}22", ink=True,
        )
        btn_cancel.on_click = _fechar

        btn_excluir = ft.Container(
            content=ft.Text("Excluir", size=13, color=VERM,
                            weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=8, bgcolor=f"{VERM}22", ink=True,
        )
        btn_excluir.on_click = _excluir

        ref[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Confirmar exclusao", size=15, color=TXT,
                            weight=ft.FontWeight.W_700, text_align="center"),
                    ft.Container(height=8),
                    ft.Text(
                        f"Deseja excluir \"{esp['nome']}\"?\n"
                        "Medicos vinculados impedem a exclusao.",
                        size=13, color=SEC, text_align="center",
                    ),
                    ft.Container(height=20),
                    ft.Row([btn_cancel, btn_excluir], spacing=8,
                           alignment=ft.MainAxisAlignment.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(24), width=300,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref[0].on_click = _fechar
        page.overlay.append(ref[0])
        try: page.update()
        except Exception: pass

    def abrir_ficha(esp=None):
        is_novo = esp is None

        f_nome = ft.TextField(
            label="Nome da especialidade *",
            value=esp["nome"] if esp else "",
            bgcolor="#0D1117", border_color="#30363D",
            label_style=ft.TextStyle(color="#8B949E"),
            text_style=ft.TextStyle(color="#E6EDF3"),
            border_radius=6,
        )
        f_desc = ft.TextField(
            label="Descrição",
            value=esp.get("descricao", "") if esp else "",
            bgcolor="#0D1117", border_color="#30363D",
            label_style=ft.TextStyle(color="#8B949E"),
            text_style=ft.TextStyle(color="#E6EDF3"),
            border_radius=6, multiline=True, min_lines=2,
        )
        sw_ativo = ft.Switch(
            label="Ativa",
            value=bool(esp.get("ativo", 1)) if esp else True,
            active_color=COR,
        )
        txt_erro = ft.Text("", color="#FF4444", size=11)

        ref = [None]

        def _fechar_form(e=None):
            if ref[0] and ref[0] in page.overlay:
                page.overlay.remove(ref[0])
            try: page.update()
            except Exception: pass

        def salvar(e):
            if not f_nome.value.strip():
                txt_erro.value = "Nome e obrigatorio."
                try: page.update()
                except Exception: pass
                return
            salvar_especialidade({
                "id":        esp["id"] if esp else None,
                "nome":      f_nome.value.strip(),
                "descricao": f_desc.value.strip() or None,
                "ativo":     1 if sw_ativo.value else 0,
            })
            _fechar_form()
            carregar()

        btn_cancel_form = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=8, bgcolor=f"{SEC}22", ink=True,
        )
        btn_cancel_form.on_click = _fechar_form

        btn_salvar = ft.Container(
            content=ft.Text("Salvar", size=13, color=COR,
                            weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=8, bgcolor=f"{COR}22", ink=True,
        )
        btn_salvar.on_click = salvar

        ref[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("local_hospital_rounded", color=COR, size=18),
                        ft.Text(
                            "Nova Especialidade" if is_novo else "Editar Especialidade",
                            size=15, weight=ft.FontWeight.W_600, color=TXT),
                    ], spacing=8),
                    ft.Container(height=12),
                    f_nome, f_desc, sw_ativo, txt_erro,
                    ft.Container(height=12),
                    ft.Row([btn_cancel_form, btn_salvar], spacing=8,
                           alignment=ft.MainAxisAlignment.END),
                ], spacing=6, tight=True),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20), width=340,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        page.overlay.append(ref[0])
        try: page.update()
        except Exception: pass

    carregar()

    btn_voltar = ft.Container(
        content=ft.Row([
            ft.Icon("arrow_back_rounded", size=16),
            ft.Text("Voltar", size=13),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        ink=True,
        on_click=lambda e: voltar_fn(),
    )

    return ft.Column([
        btn_voltar,
        ft.Row([
            ft.Text("Especialidades", size=24, weight=ft.FontWeight.W_700,
                    color="#E6EDF3", expand=True),
            ft.FilledButton(
                content=ft.Row([
                    ft.Icon("add_rounded", size=16),
                    ft.Text("Nova", size=13),
                ], spacing=6, tight=True),
                style=ft.ButtonStyle(
                    bgcolor=COR,
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=16, vertical=10),
                ),
                on_click=lambda e: abrir_ficha(None),
            ),
        ]),
        txt_busca,
        lista,
    ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)