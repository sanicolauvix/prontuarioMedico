"""
tela_parecer.py - Exibe o parecer clínico gerado pela IA
"""
import flet as ft
import threading
import logging


COR_TITULO   = "#E6EDF3"
COR_SUBTITULO= "#8B949E"
COR_CARD     = "#161B22"
COR_BORDA    = "#21262D"

NIVEL_COR = {
    "alto":      "#FF4444",
    "moderado":  "#F0883E",
    "baixo":     "#3FB950",
    "sem_risco": "#484F58",
}
NIVEL_ICON = {
    "alto":      ft.Icons.WARNING_ROUNDED,
    "moderado":  ft.Icons.INFO_ROUNDED,
    "baixo":     ft.Icons.CHECK_CIRCLE_ROUNDED,
    "sem_risco": ft.Icons.REMOVE_CIRCLE_OUTLINE_ROUNDED,
}
TENDENCIA_ICON = {
    "subindo":      ("↑", "#F0883E"),
    "descendo":     ("↓", "#58A6FF"),
    "estavel":      ("→", "#3FB950"),
    "unico_ponto":  ("•", "#8B949E"),
}
RELEVANCIA_COR = {
    "alta":  "#BC8CFF",
    "media": "#58A6FF",
    "baixa": "#484F58",
}


# ══════════════════════════════════════════════════════════════
# HELPERS DE CARD
# ══════════════════════════════════════════════════════════════

def _card(conteudo: ft.Control, cor_borda: str = COR_BORDA) -> ft.Container:
    return ft.Container(
        content=conteudo,
        bgcolor=COR_CARD,
        border_radius=10,
        padding=14,
        border=ft.Border(
            top=ft.BorderSide(1, cor_borda), bottom=ft.BorderSide(1, cor_borda),
            left=ft.BorderSide(1, cor_borda), right=ft.BorderSide(1, cor_borda),
        ),
    )


def _secao_titulo(icone, titulo: str, cor: str) -> ft.Row:
    return ft.Row([
        ft.Icon(icone, size=18, color=cor),
        ft.Text(titulo, size=14, color=cor, weight=ft.FontWeight.W_700),
    ], spacing=8)


# ══════════════════════════════════════════════════════════════
# SEÇÕES DO PARECER
# ══════════════════════════════════════════════════════════════

def _secao_tendencias(tendencias: list) -> ft.Control:
    if not tendencias:
        return ft.Container()

    itens = []
    for t in tendencias:
        seta, cor_seta = TENDENCIA_ICON.get(t.get("tendencia",""), ("?", "#8B949E"))
        alerta = t.get("alerta", False)
        cor_borda_item = "#F0883E44" if alerta else COR_BORDA

        itens.append(
            ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Text(seta, size=20, color=cor_seta,
                                        weight=ft.FontWeight.W_700),
                        width=32, alignment=ft.alignment.Alignment(0,0),
                    ),
                    ft.Column([
                        ft.Row([
                            ft.Text(t.get("exame",""), size=13, color=COR_TITULO,
                                    weight=ft.FontWeight.W_600),
                            ft.Container(
                                content=ft.Text(
                                    t.get("tendencia","").replace("_"," ").capitalize(),
                                    size=9, color=cor_seta,
                                ),
                                bgcolor=f"{cor_seta}22",
                                border_radius=4,
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            ),
                            ft.Icon(ft.Icons.WARNING_AMBER, size=13,
                                    color="#F0883E") if alerta else ft.Container(),
                        ], spacing=6),
                        ft.Text(t.get("descricao",""), size=12, color=COR_SUBTITULO),
                    ], spacing=3, expand=True),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START),
                bgcolor="#0D1117",
                border_radius=8,
                padding=10,
                border=ft.Border(
                    top=ft.BorderSide(1, cor_borda_item),
                    bottom=ft.BorderSide(1, cor_borda_item),
                    left=ft.BorderSide(2, cor_seta),   # borda esquerda colorida
                    right=ft.BorderSide(1, cor_borda_item),
                ),
            )
        )

    return _card(ft.Column([
        _secao_titulo(ft.Icons.SHOW_CHART_ROUNDED, "Tendências Temporais", "#58A6FF"),
        ft.Container(height=8),
        ft.Column(itens, spacing=6),
    ], spacing=0))


def _secao_correlacoes(correlacoes: list) -> ft.Control:
    if not correlacoes:
        return ft.Container()

    itens = []
    for c in correlacoes:
        rel  = c.get("relevancia", "baixa")
        cor  = RELEVANCIA_COR.get(rel, "#484F58")
        nomes = " + ".join(c.get("exames", []))

        itens.append(
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(nomes, size=12, color=cor,
                                weight=ft.FontWeight.W_600),
                        ft.Container(
                            content=ft.Text(
                                f"Relevância {rel}",
                                size=9, color=cor,
                            ),
                            bgcolor=f"{cor}22",
                            border_radius=4,
                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        ),
                    ], spacing=8),
                    ft.Text(c.get("descricao",""), size=12, color=COR_SUBTITULO),
                ], spacing=4),
                bgcolor="#0D1117",
                border_radius=8,
                padding=10,
                border=ft.Border(
                    top=ft.BorderSide(1, COR_BORDA),
                    bottom=ft.BorderSide(1, COR_BORDA),
                    left=ft.BorderSide(2, cor),
                    right=ft.BorderSide(1, COR_BORDA),
                ),
            )
        )

    return _card(ft.Column([
        _secao_titulo(ft.Icons.HUB_ROUNDED, "Correlações entre Exames", "#BC8CFF"),
        ft.Container(height=8),
        ft.Column(itens, spacing=6),
    ], spacing=0))


def _secao_riscos(riscos: list) -> ft.Control:
    if not riscos:
        return ft.Container()

    itens = []
    for r in riscos:
        nivel = r.get("nivel", "baixo")
        cor   = NIVEL_COR.get(nivel, "#484F58")
        icone = NIVEL_ICON.get(nivel, ft.Icons.INFO_ROUNDED)

        itens.append(
            ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(icone, size=20, color=cor),
                        bgcolor=f"{cor}22",
                        border_radius=8,
                        width=38, height=38,
                        alignment=ft.alignment.Alignment(0,0),
                    ),
                    ft.Column([
                        ft.Row([
                            ft.Text(r.get("categoria",""), size=13,
                                    color=COR_TITULO, weight=ft.FontWeight.W_600),
                            ft.Container(
                                content=ft.Text(
                                    f"Risco {nivel}".replace("_"," "),
                                    size=9, color=cor,
                                ),
                                bgcolor=f"{cor}22",
                                border_radius=4,
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            ),
                        ], spacing=8),
                        ft.Text(r.get("descricao",""), size=12, color=COR_SUBTITULO),
                    ], spacing=3, expand=True),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START),
                bgcolor="#0D1117",
                border_radius=8,
                padding=10,
                border=ft.Border(
                    top=ft.BorderSide(1, COR_BORDA),
                    bottom=ft.BorderSide(1, COR_BORDA),
                    left=ft.BorderSide(2, cor),
                    right=ft.BorderSide(1, COR_BORDA),
                ),
            )
        )

    return _card(ft.Column([
        _secao_titulo(ft.Icons.MONITOR_HEART_ROUNDED, "Riscos Identificados", "#F0883E"),
        ft.Container(height=8),
        ft.Column(itens, spacing=6),
    ], spacing=0))


def _secao_recomendacoes(recomendacoes: list) -> ft.Control:
    if not recomendacoes:
        return ft.Container()

    itens = [
        ft.Row([
            ft.Container(
                content=ft.Text(str(i+1), size=10, color="#3FB950",
                                weight=ft.FontWeight.W_700),
                bgcolor="#3FB95022",
                border_radius=10,
                width=22, height=22,
                alignment=ft.alignment.Alignment(0,0),
            ),
            ft.Text(rec, size=12, color=COR_TITULO, expand=True),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START)
        for i, rec in enumerate(recomendacoes)
    ]

    return _card(ft.Column([
        _secao_titulo(ft.Icons.LIGHTBULB_ROUNDED, "Recomendações", "#3FB950"),
        ft.Container(height=8),
        ft.Column(itens, spacing=8),
    ], spacing=0))


def _secao_resumo(resumo: str) -> ft.Control:
    if not resumo:
        return ft.Container()

    return _card(
        ft.Column([
            _secao_titulo(ft.Icons.SUMMARIZE_ROUNDED, "Síntese Geral", "#E6EDF3"),
            ft.Container(height=8),
            ft.Text(resumo, size=13, color=COR_TITULO, selectable=True),
        ], spacing=0),
        cor_borda="#30363D",
    )


def _aviso_legal() -> ft.Container:
    return ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color="#484F58"),
            ft.Text(
                "Este parecer é auxiliar e educacional. "
                "Consulte seu médico para avaliação e conduta clínica.",
                size=10, color="#484F58", expand=True,
            ),
        ], spacing=8),
        bgcolor="#0D1117",
        border_radius=6,
        padding=10,
        border=ft.Border(
            top=ft.BorderSide(1, "#21262D"), bottom=ft.BorderSide(1, "#21262D"),
            left=ft.BorderSide(1, "#21262D"), right=ft.BorderSide(1, "#21262D"),
        ),
    )


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL DO PARECER
# ══════════════════════════════════════════════════════════════

def criar_tela_parecer(page: ft.Page,
                       exames_selecionados: list[dict],
                       voltar_fn):
    from ..utils.parecer_medico import gerar_parecer, idade_atual, sexo_extenso, nome_paciente

    conteudo   = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
    prog_ring  = ft.ProgressRing(width=32, height=32, stroke_width=3,
                                  color="#BC8CFF")
    txt_status = ft.Text("Gerando parecer com IA...", size=13, color="#8B949E")

    nomes_exames = " · ".join(ex["nome_oficial"] for ex in exames_selecionados)
    idade        = idade_atual()
    sexo         = "Masculino" if sexo_extenso() == "masculino" else "Feminino"

    btn_voltar = ft.TextButton(
        content=ft.Row([
            ft.Icon(ft.Icons.ARROW_BACK, size=16),
            ft.Text("Voltar", size=13),
        ], spacing=4, tight=True),
        on_click=voltar_fn,
    )

    # Estado de carregamento
    area_loading = ft.Column([
        ft.Container(height=40),
        ft.Row([prog_ring], alignment=ft.MainAxisAlignment.CENTER),
        ft.Container(height=12),
        ft.Row([txt_status], alignment=ft.MainAxisAlignment.CENTER),
    ], visible=True)

    area_resultado = ft.Column(spacing=10, visible=False)

    def _gerar():
        logging.info("[PARECER] Iniciando geração...")
        try:
            resultado = gerar_parecer(exames_selecionados)
        except Exception as ex:
            logging.exception("[PARECER] Erro")
            resultado = {"erro": str(ex)}

        # Monta UI com o resultado
        area_resultado.controls.clear()

        if "erro" in resultado:
            area_resultado.controls.append(
                _card(ft.Column([
                    ft.Icon(ft.Icons.ERROR_ROUNDED, size=32, color="#FF4444"),
                    ft.Text(f"Erro ao gerar parecer:\n{resultado['erro']}",
                            size=13, color="#FF4444", text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8))
            )
        else:
            area_resultado.controls += [
                _secao_resumo(resultado.get("resumo_geral", "")),
                _secao_tendencias(resultado.get("tendencias", [])),
                _secao_correlacoes(resultado.get("correlacoes", [])),
                _secao_riscos(resultado.get("riscos", [])),
                _secao_recomendacoes(resultado.get("recomendacoes", [])),
                _aviso_legal(),
            ]

        area_loading.visible  = False
        area_resultado.visible = True
        try:
            page.update()
        except Exception:
            pass

    # Dispara geração em thread
    threading.Thread(target=_gerar, daemon=True, name="PareceIA").start()

    return ft.Column([
        btn_voltar,
        ft.Row([
            ft.Column([
                ft.Text("Parecer Clínico", size=24,
                        weight=ft.FontWeight.W_700, color=COR_TITULO),
                ft.Text(nomes_exames, size=12, color="#58A6FF"),
            ], spacing=2, expand=True),
            ft.Container(
                content=ft.Column([
                    ft.Text(f"{idade} anos", size=13, color="#BC8CFF",
                            weight=ft.FontWeight.W_600,
                            text_align=ft.TextAlign.CENTER),
                    ft.Text(sexo, size=10, color="#484F58",
                            text_align=ft.TextAlign.CENTER),
                ], spacing=1, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor="#BC8CFF22",
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=14, vertical=8),
                border=ft.Border(
                    top=ft.BorderSide(1, "#BC8CFF44"),
                    bottom=ft.BorderSide(1, "#BC8CFF44"),
                    left=ft.BorderSide(1, "#BC8CFF44"),
                    right=ft.BorderSide(1, "#BC8CFF44"),
                ),
            ),
        ]),
        ft.Divider(color="#21262D"),
        area_loading,
        area_resultado,
    ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
