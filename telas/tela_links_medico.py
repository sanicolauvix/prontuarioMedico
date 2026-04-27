"""
tela_links_medico.py — Koios Prontuário
Gestão de links de acesso para médicos.
"""
import logging
import flet as ft
import webbrowser
from ..dados.model_prontuario import (
    listar_medicos, criar_link_medico,
    listar_links_medicos, revogar_link_medico,
)

logger = logging.getLogger(__name__)

# ── Paleta ────────────────────────────────────────────────────
BG   = "#0D1117";  CARD = "#161B22";  BD  = "#21262D";  BD2 = "#30363D"
TXT  = "#E6EDF3";  SEC  = "#8B949E";  MUT = "#484F58"
AZUL = "#58A6FF";  VERD = "#3FB950";  LAR = "#F0883E"
VERM = "#DA3633"


def _detectar_base_url(page) -> str:
    """Retorna a URL HTTP do servidor médico (porta 8551).
    page.url expõe ws:// do Flet interno — converte para http:// e troca a porta.
    """
    try:
        if hasattr(page, "url") and page.url:
            from urllib.parse import urlparse
            p = urlparse(page.url)
            host = p.hostname or "localhost"
            return f"http://{host}:8551"
    except Exception:
        pass
    return "http://localhost:8551"


# ══════════════════════════════════════════════════════════════
# ABA: LINKS
# ══════════════════════════════════════════════════════════════

def _conteudo_links(page):
    base_url     = [_detectar_base_url(page)]
    lista_links  = ft.Column(spacing=6)
    txt_feedback = ft.Text("", size=12, color=VERD)

    def carregar():
        lista_links.controls.clear()
        links = listar_links_medicos()

        if not links:
            lista_links.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.LINK_OFF_ROUNDED, size=36, color=MUT),
                    ft.Text("Nenhum link gerado ainda.", size=13, color=MUT),
                    ft.Text("Gere um link abaixo para compartilhar com o médico.",
                            size=11, color=MUT),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=40,
                alignment=ft.alignment.Alignment(0, 0),
            ))
        else:
            for lk in links:
                _card_link(lk)

        try: page.update()
        except Exception: pass

    def _card_link(lk: dict):
        ativo        = lk.get("ativo", 1)
        cor_status   = VERD if ativo else MUT
        label_status = "Ativo" if ativo else "Revogado"
        url_completa = f"{base_url[0]}/?medico={lk['token']}"
        ultimo       = lk.get("ultimo_acesso", "")
        acessos      = lk.get("acessos", 0)

        def copiar_link(e, url=url_completa):
            page.set_clipboard(url)
            txt_feedback.value = f"✓ Link copiado: {lk['nome_medico']}"
            txt_feedback.color = VERD
            try: page.update()
            except Exception: pass

        def abrir_link(e, url=url_completa):
            webbrowser.open(url)

        def revogar(e, token=lk["token"], nome=lk["nome_medico"]):
            revogar_link_medico(token)
            logger.info("Link revogado: %s token=%s...", nome, token[:8])
            txt_feedback.value = f"Link revogado: {nome}"
            txt_feedback.color = LAR
            carregar()

        acoes = ft.Row([
            ft.TextButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.COPY_ROUNDED, size=13, color=AZUL),
                    ft.Text("Copiar link", size=11, color=AZUL),
                ], spacing=4, tight=True),
                on_click=copiar_link,
                disabled=not ativo,
            ),
            ft.TextButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.OPEN_IN_NEW_ROUNDED, size=13, color=SEC),
                    ft.Text("Testar", size=11, color=SEC),
                ], spacing=4, tight=True),
                on_click=abrir_link,
                disabled=not ativo,
            ),
        ] + ([
            ft.TextButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.BLOCK_ROUNDED, size=13, color=VERM),
                    ft.Text("Revogar", size=11, color=VERM),
                ], spacing=4, tight=True),
                on_click=revogar,
            ),
        ] if ativo else []),
        spacing=4)

        lista_links.controls.append(ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.PERSON, size=14, color=cor_status),
                            ft.Text(lk["nome_medico"], size=13, color=TXT,
                                    weight=ft.FontWeight.W_600),
                            ft.Container(
                                content=ft.Text(label_status, size=9,
                                                color=cor_status),
                                bgcolor=f"{cor_status}22", border_radius=4,
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            ),
                        ], spacing=6),
                        ft.Text(
                            f"{acessos} acesso(s)  ·  "
                            f"Último: {(ultimo or 'nunca')[:16]}",
                            size=10, color=MUT,
                        ),
                    ], spacing=3, expand=True),
                ]),
                ft.Container(
                    content=ft.Text(
                        url_completa[:70] + "..." if len(url_completa) > 70
                        else url_completa,
                        size=10, color=MUT, font_family="monospace",
                        selectable=True,
                    ),
                    bgcolor=BG, border_radius=4,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                ) if ativo else ft.Container(),
                acoes,
            ], spacing=6),
            bgcolor=CARD, border_radius=10, padding=12,
            border=ft.Border(
                left=ft.BorderSide(2, cor_status),
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                right=ft.BorderSide(1, BD),
            ),
            opacity=1.0 if ativo else 0.5,
        ))

    # ── Gerar novo link ──────────────────────────────────────
    medicos      = listar_medicos(so_ativos=True)
    med_id_sel   = [None]   # id selecionado via autocomplete

    f_medico = ft.TextField(
        label="Médico",
        hint_text="Digite para buscar…",
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, expand=True,
    )
    sug_med = ft.Column(spacing=2, visible=False)

    def _filtrar_med(e):
        termo = (f_medico.value or "").strip().upper()
        sug_med.controls.clear()
        if not termo:
            sug_med.visible = False
            med_id_sel[0] = None
            try: page.update()
            except Exception: pass
            return
        encontrados = [m for m in medicos if termo in m["nome"].upper()][:6]
        for m in encontrados:
            def _sel(e, med=m):
                f_medico.value  = med["nome"]
                med_id_sel[0]   = med["id"]
                sug_med.controls.clear()
                sug_med.visible = False
                try: page.update()
                except Exception: pass
            especialidade = m.get("especialidade") or ""
            sug_med.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.PERSON, size=14, color=AZUL),
                    ft.Column([
                        ft.Text(m["nome"], size=12, color=TXT),
                        ft.Text(especialidade, size=10, color=MUT),
                    ], spacing=1, tight=True),
                ], spacing=8),
                bgcolor=BD, border_radius=6,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                on_click=_sel, ink=True,
            ))
        sug_med.visible = bool(encontrados)
        try: page.update()
        except Exception: pass

    f_medico.on_change = _filtrar_med

    f_url_base = ft.TextField(
        label="URL base do servidor médico",
        value=base_url[0],
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC),
        text_style=ft.TextStyle(color=TXT, font_family="monospace"),
        border_radius=8, expand=True,
        hint_text="http://localhost:8551",
        hint_style=ft.TextStyle(color=MUT),
    )

    def gerar_link(e):
        txt_feedback.value = ""
        if not med_id_sel[0]:
            txt_feedback.value = "Selecione um médico da lista."
            txt_feedback.color = VERM
            try: page.update()
            except Exception: pass
            return
        if f_url_base.value.strip():
            base_url[0] = f_url_base.value.strip().rstrip("/")
        medico_id   = med_id_sel[0]
        nome_medico = next(
            (m["nome"] for m in medicos if m["id"] == medico_id), "Médico"
        )
        token      = criar_link_medico(medico_id, nome_medico)
        url_gerada = f"{base_url[0]}/?medico={token}"
        page.set_clipboard(url_gerada)
        logger.info("Link gerado para %s: %s...", nome_medico, token[:8])
        txt_feedback.value = f"✓ Link gerado e copiado para {nome_medico}!"
        txt_feedback.color = VERD
        f_medico.value = ""
        med_id_sel[0]  = None
        carregar()

    aviso = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.SECURITY_ROUNDED, size=13, color=MUT),
            ft.Text(
                "Cada médico tem um link único. "
                "Revogue quando não precisar mais do acesso. "
                "Acessos são registrados para auditoria LGPD.",
                size=10, color=MUT, expand=True,
            ),
        ], spacing=8),
        bgcolor=BG, border_radius=6,
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
    )

    carregar()

    return [
        aviso,
        ft.Container(height=4),
        ft.Text("Gerar novo link", size=11, color=MUT,
                weight=ft.FontWeight.W_700),
        f_url_base,
        ft.Column([f_medico, sug_med], spacing=0),
        ft.Row([
            ft.FilledButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.ADD_LINK_ROUNDED, size=16),
                    ft.Text("Gerar Link", size=13, weight=ft.FontWeight.W_600),
                ], spacing=6, tight=True),
                style=ft.ButtonStyle(
                    bgcolor=AZUL,
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=16, vertical=12),
                ),
                on_click=gerar_link,
            ),
        ]),
        txt_feedback,
        ft.Container(height=1, bgcolor=BD, margin=ft.margin.symmetric(vertical=8)),
        ft.Text("Links existentes", size=11, color=MUT,
                weight=ft.FontWeight.W_700),
        lista_links,
    ]


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL
# ══════════════════════════════════════════════════════════════

def criar_tela_links_medico(page: ft.Page, voltar_fn):
    area_conteudo = ft.Column(spacing=8, expand=True, scroll=ft.ScrollMode.AUTO)

    def _rebuild_conteudo():
        area_conteudo.controls.clear()
        area_conteudo.controls.extend(_conteudo_links(page))
        try: page.update()
        except Exception: pass

    _rebuild_conteudo()

    cabecalho = ft.Container(
        content=ft.Row([
            ft.TextButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.ARROW_BACK, size=16),
                    ft.Text("Voltar", size=13),
                ], spacing=4, tight=True),
                on_click=lambda e: voltar_fn(),
            ),
            ft.Row([
                ft.Icon(ft.Icons.LINK_ROUNDED, size=18, color=AZUL),
                ft.Text("Links de Acesso Médico", size=16,
                        weight=ft.FontWeight.W_700, color=TXT),
            ], spacing=8, tight=True),
            ft.Container(expand=True),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
    )

    try:
        larg = page.width or 0
    except Exception:
        larg = 0

    corpo = ft.Column([
        cabecalho,
        ft.Container(
            content=area_conteudo,
            padding=ft.padding.all(16),
            expand=True,
        ),
    ], expand=True)

    if larg > 500:
        conteudo_final = ft.Row([
            ft.Container(expand=True),
            ft.Container(content=corpo, width=480),
            ft.Container(expand=True),
        ], expand=True)
    else:
        conteudo_final = corpo

    wrapper = ft.Column(expand=True)
    wrapper.controls.append(ft.Container(bgcolor=BG, expand=True,
                                          content=conteudo_final))
    return wrapper
