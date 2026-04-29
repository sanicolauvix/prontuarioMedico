# -*- coding: utf-8 -*-
"""prontuario/telas/tela_perfil.py — Perfil do usuário."""

import flet as ft
import logging

BG   = "#0D1117"
CARD = "#161B22"
BD   = "#21262D"
TXT  = "#E6EDF3"
SEC  = "#8B949E"
MUT  = "#484F58"
AZUL = "#58A6FF"
VERD = "#3FB950"
AMAR = "#D29922"
VERM = "#F85149"


def criar_tela_perfil(page: ft.Page, voltar_fn=None):
    _montado = [False]

    def _atualizar_ui():
        if _montado[0]:
            try:
                page.update()
            except Exception:
                pass

    # ── Campos editáveis ──────────────────────────────────────────
    def _campo(label, valor="", hint="", largura=None):
        tf = ft.TextField(
            label=label,
            value=str(valor) if valor not in (None, "") else "",
            hint_text=hint,
            border_color=BD,
            focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=12),
            text_style=ft.TextStyle(color=TXT, size=13),
            bgcolor=CARD,
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
            width=largura,
        )
        return tf

    perfil = {}
    try:
        from dados.model_prontuario import carregar_perfil
        perfil = carregar_perfil() or {}
    except Exception:
        pass

    email_google = ""
    try:
        import os, json
        from shared.auth import _CREDS_PATH
        if os.path.exists(_CREDS_PATH):
            with open(_CREDS_PATH, "r", encoding="utf-8") as f:
                cd = json.load(f)
            email_google = cd.get("email", "")
    except Exception:
        pass

    email_atual = perfil.get("email") or email_google

    f_nome       = _campo("Nome completo",  perfil.get("nome", ""))
    f_data_nasc  = _campo("Data nasc.",     perfil.get("data_nasc", ""), hint="AAAA-MM-DD", largura=160)
    f_peso       = _campo("Peso (kg)",      perfil.get("peso", ""),      hint="70.5",       largura=120)
    f_altura     = _campo("Altura (cm)",    perfil.get("altura", ""),    hint="175",         largura=120)

    dd_sexo = ft.Dropdown(
        label="Sexo",
        value=perfil.get("sexo", ""),
        options=[
            ft.dropdown.Option("M", "Masculino"),
            ft.dropdown.Option("F", "Feminino"),
            ft.dropdown.Option("O", "Outro"),
        ],
        border_color=BD,
        focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC, size=12),
        text_style=ft.TextStyle(color=TXT, size=13),
        bgcolor=CARD,
        border_radius=8,
        expand=True,
    )

    dd_sangue = ft.Dropdown(
        label="Tipo sanguíneo",
        value=perfil.get("tipo_sanguineo", ""),
        options=[ft.dropdown.Option(t) for t in
                 ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Não sei"]],
        border_color=BD,
        focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC, size=12),
        text_style=ft.TextStyle(color=TXT, size=13),
        bgcolor=CARD,
        border_radius=8,
        expand=True,
    )

    f_cond = _campo(
        "Condições crônicas",
        ", ".join(perfil.get("condicoes_cronicas") or []),
        hint="Ex: Hipertensão, Diabetes",
    )
    f_contato = _campo("Contato de emergência", perfil.get("contato_emergencia", ""))
    f_tel     = _campo("Telefone emergência",   perfil.get("tel_emergencia", ""), hint="(99) 99999-9999")

    txt_status = ft.Text("", size=12, color=VERD)

    def _salvar(e):
        try:
            condicoes_raw = f_cond.value.strip()
            condicoes = [c.strip() for c in condicoes_raw.split(",") if c.strip()] if condicoes_raw else []

            dados = {
                "nome":               f_nome.value.strip() or None,
                "email":              email_atual,
                "data_nasc":          f_data_nasc.value.strip() or None,
                "sexo":               dd_sexo.value or None,
                "foto_url":           perfil.get("foto_url"),
                "peso":               float(f_peso.value.replace(",", ".")) if f_peso.value.strip() else None,
                "altura":             float(f_altura.value.replace(",", ".")) if f_altura.value.strip() else None,
                "tipo_sanguineo":     dd_sangue.value or None,
                "condicoes_cronicas": condicoes,
                "contato_emergencia": f_contato.value.strip() or None,
                "tel_emergencia":     f_tel.value.strip() or None,
                "tema":               perfil.get("tema", "dark"),
                "accent_color":       perfil.get("accent_color", "#58A6FF"),
                "tamanho_fonte":      perfil.get("tamanho_fonte", "medio"),
            }
            from dados.model_prontuario import salvar_perfil
            salvar_perfil(dados)
            txt_status.value = "Perfil salvo!"
            txt_status.color = VERD
            logging.info("[PERFIL] Salvo")
        except Exception as ex:
            txt_status.value = f"Erro: {ex}"
            txt_status.color = VERM
            logging.exception("[PERFIL] Erro ao salvar")
        _atualizar_ui()

    # ── Header ────────────────────────────────────────────────────
    header = ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Row([
                    ft.Icon("arrow_back_rounded", size=16, color=SEC),
                    ft.Text("Voltar", size=13, color=SEC),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                ink=True,
                on_click=lambda e: voltar_fn() if voltar_fn else None,
            ),
            ft.Row([
                ft.Icon("manage_accounts_rounded", size=18, color=AZUL),
                ft.Text("Perfil", size=16, weight=ft.FontWeight.W_700, color=TXT),
            ], spacing=8, tight=True),
            ft.Container(expand=True),
            ft.Container(
                content=ft.Row([
                    ft.Icon("save_outlined_rounded", size=14, color=AZUL),
                    ft.Text("Salvar", size=13, color=AZUL),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                ink=True,
                on_click=_salvar,
            ),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
    )

    def _secao(titulo):
        return ft.Text(titulo, size=10, weight=ft.FontWeight.W_700, color=SEC)

    def _card_section(controles):
        return ft.Container(
            content=ft.Column(controles, spacing=10),
            bgcolor=CARD,
            border=ft.border.all(1, BD),
            border_radius=10,
            padding=16,
        )

    # E-mail (read-only)
    email_row = ft.Container(
        content=ft.Row([
            ft.Text("E-mail", size=12, color=SEC, expand=True),
            ft.Text(email_atual or "—", size=12, color=MUT),
        ]),
        padding=ft.padding.symmetric(vertical=4),
    )

    area = ft.ListView(
        spacing=12,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        expand=True,
    )

    area.controls += [
        _secao("DADOS PESSOAIS"),
        _card_section([
            f_nome,
            email_row,
            ft.Row([f_data_nasc, dd_sexo], spacing=10),
        ]),
        _secao("DADOS CLÍNICOS"),
        _card_section([
            ft.Row([f_peso, f_altura, dd_sangue], spacing=10),
            f_cond,
        ]),
        _secao("EMERGÊNCIA"),
        _card_section([
            f_contato,
            f_tel,
        ]),
        txt_status,
    ]

    corpo = ft.Column([header, area], spacing=0, expand=True)
    wrapper = ft.Column(expand=True)
    wrapper.controls.append(ft.Container(bgcolor=BG, expand=True, content=corpo))
    _montado[0] = True
    return wrapper
