# -*- coding: utf-8 -*-
# Prontuario | telas/tela_claudia.py -- Chat conversacional com Claudia
import flet as ft
import threading
import logging
import os

log = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))
_APP  = os.path.dirname(_HERE)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
ROXO = "#BC8CFF"; AZUL = "#58A6FF"; VERD = "#3FB950"; VERM = "#F85149"


def _ler_arquivo(caminho: str) -> str:
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _montar_system_prompt() -> str:
    try:
        from dados.model_prontuario import get_config as _gc
        _cerebro   = _gc("claudia_cerebro_path", "")
        _pac_config = _gc("claudia_paciente_md",  "")
    except Exception:
        _cerebro = _pac_config = ""

    _ref_dir = (os.path.join(_cerebro, "koios", "CLAUDIA.md")
                if _cerebro else "")
    skill    = (_ler_arquivo(_ref_dir) if _ref_dir
                else _ler_arquivo(os.path.join(_APP, "claudia", "SKILL.md")))
    paciente = (_ler_arquivo(_pac_config) if _pac_config
                else _ler_arquivo(os.path.join(_APP, "claudia", "references", "paciente.md")))
    interpre = _ler_arquivo(os.path.join(_APP, "claudia", "references", "interpretacao_exames.md"))
    med_supl = _ler_arquivo(os.path.join(_APP, "claudia", "references", "medicamentos_suplementos.md"))

    partes = [skill]
    if paciente:
        partes.append("---\n\n## Perfil do Paciente\n\n" + paciente)
    if interpre:
        partes.append("---\n\n## Referencia: Interpretacao de Exames\n\n" + interpre)
    if med_supl:
        partes.append("---\n\n## Referencia: Medicamentos e Suplementos\n\n" + med_supl)
    return "\n\n".join(partes)


def _bolha_usuario(texto: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(texto, size=13, color=TXT, selectable=True),
        bgcolor="#1A0E2E",
        border_radius=ft.border_radius.only(
            top_left=12, top_right=12, bottom_left=4, bottom_right=12
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border=ft.border.all(1, ROXO + "44"),
        margin=ft.margin.only(left=48),
    )


def _bolha_claudia(texto: str = "", carregando: bool = False) -> ft.Container:
    if carregando:
        conteudo = ft.Row([
            ft.ProgressRing(width=18, height=18, stroke_width=2, color=ROXO),
            ft.Text("Claudia pensando...", size=12, color=SEC),
        ], spacing=8, tight=True)
    else:
        conteudo = ft.Text(texto, size=13, color=TXT, selectable=True)
    return ft.Container(
        content=conteudo,
        bgcolor=CARD,
        border_radius=ft.border_radius.only(
            top_left=12, top_right=12, bottom_left=12, bottom_right=4
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border=ft.border.all(1, BD),
        margin=ft.margin.only(right=48),
    )


def _rotulo(quem: str, cor: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(quem, size=9, color=cor, weight=ft.FontWeight.W_600),
        margin=ft.margin.only(bottom=2),
    )


def criar_tela_claudia(page: ft.Page, voltar_fn, prompt_inicial=None) -> ft.Container:
    from shared.layout import Layout
    lay = Layout(page)

    _historico:    list[dict] = []
    _aguardando    = [False]
    _system_prompt = [None]
    _montado       = [False]

    msgs_col = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)

    campo = ft.TextField(
        hint_text="Pergunte algo...",
        multiline=True,
        min_lines=1,
        max_lines=4,
        bgcolor=CARD,
        border_color=BD2,
        focused_border_color=ROXO,
        text_style=ft.TextStyle(color=TXT, size=13),
        hint_style=ft.TextStyle(color=MUT, size=13),
        border_radius=12,
        expand=True,
        content_padding=ft.padding.symmetric(horizontal=14, vertical=10),
    )

    def _ui():
        if _montado[0]:
            try:
                page.update()
            except Exception:
                pass

    def _add(ctrl: ft.Control):
        msgs_col.controls.append(ctrl)
        _ui()

    def _enviar(e=None):
        texto = (campo.value or "").strip()
        if not texto or _aguardando[0]:
            return
        _aguardando[0] = True
        campo.value = ""

        _historico.append({"role": "user", "content": texto})
        _add(_rotulo("Voce", SEC))
        _add(_bolha_usuario(texto))
        _add(ft.Container(height=4))

        loading = _bolha_claudia(carregando=True)
        _add(_rotulo("Claudia", ROXO))
        _add(loading)
        _ui()

        def _chamar_api():
            try:
                import anthropic
                if _system_prompt[0] is None:
                    _system_prompt[0] = _montar_system_prompt()

                client = anthropic.Anthropic()
                resp   = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1500,
                    system=_system_prompt[0],
                    messages=_historico[-20:],
                )
                resposta = resp.content[0].text.strip()
                _historico.append({"role": "assistant", "content": resposta})

                if loading in msgs_col.controls:
                    msgs_col.controls.remove(loading)
                _add(_bolha_claudia(resposta))
                _add(ft.Container(height=8))

            except Exception as ex:
                log.exception("[CLAUDIA] Erro API: %s", ex)
                if loading in msgs_col.controls:
                    msgs_col.controls.remove(loading)
                _add(_bolha_claudia(f"Erro ao contatar a API: {ex}"))
            finally:
                _aguardando[0] = False
                _ui()

        threading.Thread(target=_chamar_api, daemon=True, name="ClaudiaAPI").start()

    campo.on_submit = _enviar

    btn_enviar = ft.Container(
        content=ft.Icon("send_rounded", size=20, color=ROXO),
        width=46, height=46,
        border_radius=12,
        bgcolor=ROXO + "22",
        border=ft.border.all(1, ROXO + "55"),
        alignment=ft.alignment.Alignment(0, 0),
        ink=True,
    )
    btn_enviar.on_click = _enviar

    # Boas-vindas
    msgs_col.controls += [
        _rotulo("Claudia", ROXO),
        _bolha_claudia(
            "Ola! Eu sou a Claudia, sua assistente virtual de saude.\n"
            "Posso ajudar com seus exames, medicacoes, rotinas e muito mais.\n"
            "Em que posso te ajudar hoje?"
        ),
        ft.Container(height=8),
    ]

    btn_novo = ft.Container(
        content=ft.Row([
            ft.Icon("delete_sweep_rounded", size=14, color=SEC),
            ft.Text("Limpar", size=12, color=SEC),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=8, vertical=6),
        border_radius=8, ink=True,
    )

    def _limpar(e=None):
        _historico.clear()
        msgs_col.controls.clear()
        msgs_col.controls += [
            _rotulo("Claudia", ROXO),
            _bolha_claudia(
                "Conversa reiniciada. Como posso ajudar?"
            ),
            ft.Container(height=8),
        ]
        _ui()

    btn_novo.on_click = _limpar

    cabecalho = lay.criar_cabecalho(
        "Claudia", voltar_fn,
        icone_titulo="psychology_rounded",
        cor_titulo=ROXO,
        acoes=[btn_novo],
    )

    area_msgs = ft.Container(
        content=msgs_col,
        expand=True,
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
    )

    barra_input = ft.Container(
        content=ft.Row([campo, btn_enviar], spacing=8),
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        bgcolor=CARD,
        border=ft.Border(top=ft.BorderSide(1, BD)),
    )

    corpo = ft.Column([
        ft.Container(height=lay.spacer_topo, bgcolor=BG),
        cabecalho,
        area_msgs,
        barra_input,
    ], spacing=0, expand=True)

    _montado[0] = True
    if prompt_inicial:
        campo.value = prompt_inicial
        import threading
        threading.Thread(target=lambda: (
            __import__("time").sleep(0.3), _enviar()
        ), daemon=True).start()
    return ft.Container(bgcolor=BG, expand=True, content=corpo)
