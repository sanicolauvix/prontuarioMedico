# -*- coding: utf-8 -*-
# Prontuario | telas/tela_diagnosticos.py
import flet as ft
import logging
from shared.layout import Layout

BG    = "#0D1117"; CARD  = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT   = "#E6EDF3"; SEC   = "#8B949E"; MUT = "#484F58"; DIS = "#484F58"
AZUL  = "#58A6FF"; VERD  = "#3FB950"; LRNJ = "#F0883E"; VERM = "#FF4444"
ROXO  = "#BC8CFF"; AMAR  = "#D29922"

log = logging.getLogger(__name__)

_COR_TIPO_DIAG = {
    "entrada":    AZUL,
    "saida":      VERD,
    "secundario": SEC,
}
_COR_CERTEZA = {
    "confirmado": VERD,
    "suspeita":   LRNJ,
    "descartado": VERM,
}
_COR_HIST = {
    "diagnostico":      AMAR,
    "condicao_cronica": LRNJ,
    "cirurgia":         VERM,
    "procedimento":     AZUL,
    "internacao":       ROXO,
    "infancia":         VERD,
    "alergia":          VERM,
}
_ICON_HIST = {
    "diagnostico":      "analytics_rounded",
    "condicao_cronica": "monitor_heart_rounded",
    "cirurgia":         "medical_services_rounded",
    "procedimento":     "healing_rounded",
    "internacao":       "local_hospital_rounded",
    "infancia":         "child_care_rounded",
    "alergia":          "warning_rounded",
}


def criar_tela_diagnosticos(page: ft.Page, voltar_fn, navegar_fn=None) -> ft.Container:
    lay      = Layout(page)
    area     = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
    _montado = [False]

    # filtros
    _busca    = [""]
    _filtro_certeza = [None]   # para diagnosticos_internacao
    _aba      = ["historico"]  # "historico" | "internacao"

    # ── carrega historico_medico ─────────────────────────────────────────────

    def _carregar_historico() -> list[dict]:
        try:
            from dados.model_prontuario import DB_PATH
            import sqlite3
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                rows = conn.execute("""
                    SELECT id, data_aprox, tipo, titulo, descricao, sequela, alerta
                    FROM historico_medico
                    ORDER BY
                        CASE tipo
                            WHEN 'alergia'          THEN 1
                            WHEN 'condicao_cronica' THEN 2
                            WHEN 'diagnostico'      THEN 3
                            WHEN 'cirurgia'         THEN 4
                            WHEN 'procedimento'     THEN 5
                            WHEN 'internacao'       THEN 6
                            WHEN 'infancia'         THEN 7
                            ELSE 8
                        END,
                        data_aprox DESC NULLS LAST
                """).fetchall()
            cols = ["id","data_aprox","tipo","titulo","descricao","sequela","alerta"]
            return [dict(zip(cols, r)) for r in rows]
        except Exception as ex:
            log.exception("carregar historico_medico: %s", ex)
            return []

    # ── carrega diagnosticos_internacao ──────────────────────────────────────

    def _carregar_internacao() -> list[dict]:
        try:
            from dados.model_prontuario import DB_PATH
            import sqlite3
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                rows = conn.execute("""
                    SELECT d.id, d.internacao_id, d.cid, d.descricao,
                           d.tipo, d.certeza, d.fonte, d.criado_em,
                           i.hospital, i.data_entrada, i.data_saida,
                           d.especialidade, d.refinado
                    FROM diagnosticos_internacao d
                    JOIN internacoes i ON i.id = d.internacao_id
                    WHERE d.fonte != 'importado' OR d.refinado = 0
                    ORDER BY i.data_entrada DESC, d.tipo DESC, d.criado_em ASC
                """).fetchall()
            cols = [
                "id","internacao_id","cid","descricao","tipo","certeza","fonte","criado_em",
                "hospital","data_entrada","data_saida","especialidade","refinado",
            ]
            return [dict(zip(cols, r)) for r in rows]
        except Exception as ex:
            log.exception("carregar diagnosticos_internacao: %s", ex)
            return []

    # ── helpers ──────────────────────────────────────────────────────────────

    def _fmt(s: str) -> str:
        if s and len(s) >= 10 and s[4] == "-":
            try:
                from datetime import datetime
                return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                pass
        return s or ""

    def _badge(label: str, cor: str) -> ft.Container:
        return ft.Container(
            content=ft.Text(label, size=9, color=cor, weight=ft.FontWeight.W_600),
            bgcolor=ft.Colors.with_opacity(0.13, cor),
            border=ft.border.all(1, ft.Colors.with_opacity(0.4, cor)),
            border_radius=4,
            padding=ft.padding.symmetric(horizontal=6, vertical=2),
        )

    # ── card historico_medico ────────────────────────────────────────────────

    def _card_hist(d: dict) -> ft.Container:
        tipo   = d.get("tipo") or "diagnostico"
        titulo = (d.get("titulo") or "").strip()
        desc   = (d.get("descricao") or "").strip()
        seq    = (d.get("sequela") or "").strip()
        data   = (d.get("data_aprox") or "").strip()
        alerta = d.get("alerta")
        cor    = _COR_HIST.get(tipo, MUT)
        icone  = _ICON_HIST.get(tipo, "info_rounded")

        label_tipo = tipo.replace("_", " ").capitalize()

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(icone, size=13, color=cor),
                        bgcolor=ft.Colors.with_opacity(0.12, cor),
                        border_radius=6, width=26, height=26,
                        alignment=ft.alignment.Alignment(0, 0),
                    ),
                    ft.Column([
                        ft.Row([
                            _badge(label_tipo, cor),
                            ft.Container(expand=True),
                            ft.Text(data, size=9, color=MUT) if data else ft.Container(),
                        ], spacing=6),
                        ft.Text(titulo, size=12, color=TXT, weight=ft.FontWeight.W_600),
                    ], spacing=3, tight=True, expand=True),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Text(desc, size=10, color=SEC, max_lines=3) if desc else ft.Container(),
                ft.Container(
                    content=ft.Row([
                        ft.Icon("warning_amber_rounded", size=11, color=AMAR),
                        ft.Text(seq, size=9, color=AMAR, italic=True, expand=True),
                    ], spacing=4),
                    visible=bool(seq),
                ),
                ft.Container(
                    content=ft.Row([
                        ft.Icon("priority_high_rounded", size=11, color=VERM),
                        ft.Text("ALERTA", size=9, color=VERM,
                                weight=ft.FontWeight.W_700),
                    ], spacing=4),
                    visible=bool(alerta) and not seq,
                ),
            ], spacing=5, tight=True),
            bgcolor=CARD,
            border=ft.border.all(1, ft.Colors.with_opacity(0.3, cor) if alerta else BD2),
            border_radius=10,
            padding=ft.padding.all(12),
        )

    # ── card diagnosticos_internacao ─────────────────────────────────────────

    def _card_diag_int(d: dict) -> ft.Container:
        tipo    = d.get("tipo") or "saida"
        certeza = d.get("certeza") or "confirmado"
        cid     = (d.get("cid") or "").strip()
        desc    = (d.get("descricao") or "").strip()
        esp     = (d.get("especialidade") or "").strip()
        cor_t   = _COR_TIPO_DIAG.get(tipo, SEC)
        lbl_t   = {"entrada": "Entrada", "saida": "Alta", "secundario": "Secund."}.get(tipo, tipo.capitalize())
        cor_c   = _COR_CERTEZA.get(certeza, SEC)

        badges = [_badge(lbl_t, cor_t), _badge(certeza.capitalize(), cor_c)]
        if esp:
            badges.append(_badge(esp, ROXO))

        if cid:
            linha_nome = ft.Row([
                ft.Container(
                    content=ft.Text(f"CID {cid}", size=11, color=AMAR, weight=ft.FontWeight.W_700),
                    bgcolor=ft.Colors.with_opacity(0.13, AMAR),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.4, AMAR)),
                    border_radius=6,
                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                ),
                ft.Text(desc, size=12, color=TXT, expand=True),
            ], spacing=8, wrap=True)
        else:
            linha_nome = ft.Text(
                desc[:80] + ("..." if len(desc) > 80 else "") if desc else "Sem descricao",
                size=12, color=SEC,
            )

        return ft.Container(
            content=ft.Column([
                ft.Row(badges, spacing=6, wrap=True),
                linha_nome,
            ], spacing=6, tight=True),
            bgcolor=CARD,
            border=ft.border.all(1, BD2),
            border_radius=10,
            padding=ft.padding.all(12),
        )

    # ── tabs ─────────────────────────────────────────────────────────────────

    def _tab_btn(label, aba_val, cor):
        ativo = _aba[0] == aba_val
        def _click(e):
            _aba[0] = aba_val
            _rebuild()
        return ft.Container(
            content=ft.Text(label, size=12, color=cor if ativo else MUT,
                            weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.NORMAL),
            bgcolor=ft.Colors.with_opacity(0.12, cor) if ativo else ft.Colors.with_opacity(0.04, MUT),
            border=ft.border.all(1, ft.Colors.with_opacity(0.5, cor) if ativo else BD),
            border_radius=20,
            padding=ft.padding.symmetric(horizontal=14, vertical=6),
            ink=True,
            on_click=_click,
            expand=True,
        )

    # ── filtro certeza (só na aba internacao) ────────────────────────────────

    _row_filtros = ft.Row(spacing=6, wrap=True)

    def _chip_certeza(label, cor, val):
        ativo = _filtro_certeza[0] == val
        def _toggle(e):
            _filtro_certeza[0] = None if ativo else val
            _rebuild()
        return ft.Container(
            content=ft.Text(label, size=11,
                            color=cor if ativo else SEC,
                            weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.NORMAL),
            bgcolor=ft.Colors.with_opacity(0.13, cor) if ativo else CARD,
            border=ft.border.all(1, ft.Colors.with_opacity(0.5, cor) if ativo else BD2),
            border_radius=16,
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            ink=True,
            on_click=_toggle,
        )

    # ── rebuild ───────────────────────────────────────────────────────────────

    _txt_busca = ft.TextField(
        hint_text="Buscar diagnostico, CID, titulo...",
        hint_style=ft.TextStyle(color=DIS, size=12),
        text_style=ft.TextStyle(color=TXT, size=12),
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        border_radius=8, height=36,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=4),
        expand=True,
    )
    def _on_busca(e):
        _busca[0] = (_txt_busca.value or "").strip().lower()
        _rebuild()
    _txt_busca.on_change = _on_busca

    def _rebuild():
        busca = _busca[0]
        area.controls.clear()

        # tabs
        area.controls.append(ft.Container(
            content=ft.Row([
                _tab_btn("Histórico Clínico", "historico", AMAR),
                _tab_btn("Por Internação",    "internacao", AZUL),
            ], spacing=8),
            padding=ft.padding.only(bottom=4),
        ))

        # busca
        area.controls.append(ft.Container(
            content=ft.Row([
                ft.Icon("search_rounded", size=15, color=SEC),
                _txt_busca,
            ], spacing=6),
            bgcolor=CARD,
            border=ft.border.all(1, BD2),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
        ))

        # ── aba HISTÓRICO CLÍNICO ────────────────────────────────────────────
        if _aba[0] == "historico":
            todos = _carregar_historico()

            def _passa_h(d):
                if not busca:
                    return True
                return (busca in (d.get("titulo") or "").lower()
                     or busca in (d.get("descricao") or "").lower()
                     or busca in (d.get("tipo") or "").lower()
                     or busca in (d.get("sequela") or "").lower())

            filtrados = [d for d in todos if _passa_h(d)]

            # agrupar por tipo
            tipo_atual = [None]
            for d in filtrados:
                tipo = d.get("tipo") or "diagnostico"
                if tipo != tipo_atual[0]:
                    tipo_atual[0] = tipo
                    cor_g = _COR_HIST.get(tipo, MUT)
                    label_g = tipo.replace("_", " ").upper()
                    area.controls.append(ft.Container(
                        content=ft.Row([
                            ft.Container(width=3, height=14, bgcolor=cor_g, border_radius=2),
                            ft.Text(label_g, size=10, color=cor_g, weight=ft.FontWeight.W_700),
                        ], spacing=6),
                        padding=ft.padding.only(left=2, top=10, bottom=2),
                    ))
                area.controls.append(_card_hist(d))

            if not filtrados:
                area.controls.append(ft.Container(
                    content=ft.Text(
                        "Nenhum registro encontrado" if busca else "Nenhum historico registrado",
                        size=13, color=DIS, text_align="center"),
                    alignment=ft.alignment.center,
                    padding=ft.padding.only(top=40),
                ))

        # ── aba POR INTERNAÇÃO ───────────────────────────────────────────────
        else:
            # chips certeza
            _row_filtros.controls.clear()
            for label, cor, val in [
                ("Confirmado", VERD, "confirmado"),
                ("Suspeita",   LRNJ, "suspeita"),
                ("Descartado", VERM, "descartado"),
            ]:
                _row_filtros.controls.append(_chip_certeza(label, cor, val))
            area.controls.append(ft.Container(
                content=_row_filtros,
                padding=ft.padding.only(top=4, bottom=2),
            ))

            todos = _carregar_internacao()

            def _passa_i(d):
                if _filtro_certeza[0] and d.get("certeza") != _filtro_certeza[0]:
                    return False
                if busca:
                    return (busca in (d.get("cid") or "").lower()
                         or busca in (d.get("descricao") or "").lower()
                         or busca in (d.get("hospital") or "").lower()
                         or busca in (d.get("especialidade") or "").lower())
                return True

            filtrados = [d for d in todos if _passa_i(d)]

            area.controls.append(ft.Container(
                content=ft.Text(f"{len(filtrados)} de {len(todos)} diagnóstico(s)",
                                size=11, color=SEC),
                padding=ft.padding.only(left=2, bottom=4),
            ))

            if not filtrados:
                msg = ("Nenhum resultado" if busca or _filtro_certeza[0]
                       else "Nenhum diagnostico por internacao registrado")
                area.controls.append(ft.Container(
                    content=ft.Text(msg, size=13, color=DIS, text_align="center"),
                    alignment=ft.alignment.center,
                    padding=ft.padding.only(top=40),
                ))
            else:
                internacao_atual = [None]
                for d in filtrados:
                    iid  = d.get("internacao_id")
                    hosp = (d.get("hospital") or "?").strip()
                    periodo = _fmt(d.get("data_entrada") or "")
                    d_sai = _fmt(d.get("data_saida") or "")
                    if d_sai:
                        periodo += f" → {d_sai}"

                    if iid != internacao_atual[0]:
                        internacao_atual[0] = iid
                        area.controls.append(ft.Container(
                            content=ft.Row([
                                ft.Icon("local_hospital_rounded", size=13, color=AZUL),
                                ft.Text(hosp, size=12, color=AZUL,
                                        weight=ft.FontWeight.W_600, expand=True),
                                ft.Text(periodo, size=10, color=SEC, no_wrap=True),
                            ], spacing=6),
                            padding=ft.padding.only(left=2, top=8, bottom=2),
                        ))

                    area.controls.append(_card_diag_int(d))

        if _montado[0]:
            try:
                page.update()
            except Exception:
                pass

    _rebuild()

    cabecalho = lay.criar_cabecalho(
        "Diagnosticos", voltar_fn,
        icone_titulo="analytics_rounded",
        cor_titulo=AMAR,
    )
    corpo = lay.criar_corpo(cabecalho, area)
    _montado[0] = True
    return ft.Container(bgcolor=BG, expand=True, content=corpo)
