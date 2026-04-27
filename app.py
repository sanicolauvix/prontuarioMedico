"""
koios/prontuario/app.py
Módulo 01 — Prontuário Médico
Exporta: criar_tela_prontuario(page, voltar_fn)
"""

import flet as ft
import threading
import logging
import os
import sys

# Garante que koios/ está no path
_HERE = os.path.dirname(os.path.abspath(__file__))
_KOIOS_ROOT = os.path.dirname(_HERE)
if _KOIOS_ROOT not in sys.path:
    sys.path.insert(0, _KOIOS_ROOT)

from .dados.model_prontuario import criar_tabelas, DB_PATH


# ══════════════════════════════════════════════════════════════
# NAVEGAÇÃO INTERNA DO MÓDULO
# ══════════════════════════════════════════════════════════════

def _navegar(page: ft.Page, tela_fn, *args, **kwargs):
    import traceback
    nome = getattr(tela_fn, "__name__", str(tela_fn))
    logging.info(f"[PRON] navegar → {nome}")
    try:
        nova_tela = tela_fn(page, *args, **kwargs)
        page.controls.clear()
        page.controls.append(nova_tela)
        page.update()
    except Exception as ex:
        erro_txt = traceback.format_exc()
        logging.exception(f"[PRON] ERRO ao navegar para {nome}: {ex}")
        print(f"[ERRO NAVEGAR] {nome}: {erro_txt}")
        page.controls.clear()
        page.controls.append(ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.ERROR, size=40, color="#DA3633"),
                ft.Text(f"Erro: {nome}", size=14,
                        color="#E6EDF3", weight=ft.FontWeight.W_600),
                ft.Text(str(ex), size=12, color="#F0883E"),
                ft.Container(
                    content=ft.Text(erro_txt, size=10,
                                    color="#8B949E", selectable=True),
                    bgcolor="#161B22", border_radius=8, padding=12,
                ),
                ft.TextButton("Voltar", on_click=lambda e: (
                    args[0]() if args and callable(args[0]) else None
                )),
            ], spacing=10, scroll=ft.ScrollMode.AUTO),
            bgcolor="#0D1117", expand=True, padding=20,
        ))
        page.update()


def _btn_nav(label, icon, destino_fn, page, *args, **kwargs):
    return ft.TextButton(
        content=ft.Row([
            ft.Icon(icon, size=16, color="#8B949E"),
            ft.Text(label, size=13, color="#8B949E"),
        ], spacing=6, tight=True),
        on_click=lambda e: _navegar(page, destino_fn, *args, **kwargs),
    )


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL DO PRONTUÁRIO
# ══════════════════════════════════════════════════════════════

def _tela_principal(page: ft.Page, voltar_fn=None):
    """Hub principal do Prontuário — dashboard visual com Claudia."""
    from datetime import datetime, date, timedelta
    import sqlite3 as _sq
    from prontuario.dados.model_prontuario import (
        carregar_perfil, listar_remedios, listar_consultas,
        listar_tomadas_hoje, resumo_adesao, DB_PATH,
    )

    BG   = "#0D1117"
    CARD = "#161B22"
    BD   = "#21262D"
    TXT  = "#E6EDF3"
    SEC  = "#8B949E"
    MUT  = "#484F58"
    ROXO = "#BC8CFF"
    AZUL = "#58A6FF"
    VERD = "#3FB950"
    AMAR = "#D29922"
    VERM = "#F85149"

    aba_ativa = [0]
    _montado  = [False]

    def _atualizar_ui():
        if _montado[0]:
            try:
                page.update()
            except Exception:
                pass

    def _voltar_hub(*_):
        _navegar(page, _tela_principal, voltar_fn)

    def _ir(tela_fn):
        _navegar(page, tela_fn, _voltar_hub)

    def _lazy_fn(modulo, funcao):
        def _handler():
            import importlib
            mod = importlib.import_module(f"prontuario.telas.{modulo}")
            _ir(getattr(mod, funcao))
        return _handler

    # ── Nome e saudação ─────────────────────────────────────────
    _nome = [""]
    try:
        p = carregar_perfil()
        _nome[0] = (p.get("nome") or "").split()[0] if p else ""
    except Exception:
        pass

    hora = datetime.now().hour
    _saudacao = "Bom dia" if hora < 12 else ("Boa tarde" if hora < 18 else "Boa noite")

    # ── Helpers ─────────────────────────────────────────────────
    def _secao_titulo(titulo, icone, cor):
        return ft.Row([
            ft.Icon(icone, size=12, color=cor),
            ft.Text(titulo, size=10, weight=ft.FontWeight.W_700, color=cor),
        ], spacing=6)

    def _chip(label, cor, icone, fn):
        return ft.Container(
            content=ft.Row([
                ft.Icon(icone, size=13, color=cor),
                ft.Text(label, size=12, color=cor, weight=ft.FontWeight.W_500),
            ], spacing=5, tight=True),
            bgcolor=cor + "18",
            border=ft.border.all(1, cor + "55"),
            border_radius=20,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            on_click=lambda e: fn(),
            ink=True,
        )

    # ══════════════════════════════════════════════════════════════
    # CLAUDIA AVATAR
    # ══════════════════════════════════════════════════════════════
    nome_display = f", {_nome[0]}" if _nome[0] else ""

    claudia_avatar = ft.Stack([
        ft.Container(
            width=68, height=68, border_radius=34,
            bgcolor="#BC8CFF10",
            border=ft.border.all(1, "#BC8CFF33"),
        ),
        ft.Container(
            width=60, height=60, border_radius=30,
            bgcolor="#1A0E2E",
            border=ft.border.all(2, ROXO),
            alignment=ft.alignment.Alignment(0, 0),
            content=ft.Text("C", size=26, weight=ft.FontWeight.W_900, color=ROXO),
            left=4, top=4,
        ),
        ft.Container(
            width=12, height=12, border_radius=6,
            bgcolor=VERD,
            border=ft.border.all(2, BG),
            right=2, bottom=2,
        ),
    ], width=68, height=68)

    card_claudia = ft.Container(
        content=ft.Row([
            claudia_avatar,
            ft.Column([
                ft.Text(f"{_saudacao}{nome_display}!", size=15,
                        weight=ft.FontWeight.W_700, color=TXT),
                ft.Row([
                    ft.Container(width=7, height=7, border_radius=4, bgcolor=VERD),
                    ft.Text("Claudia disponível", size=11, color=VERD),
                ], spacing=5, tight=True),
                ft.Text("Toque para conversar", size=10, color=MUT),
            ], spacing=3, tight=True, expand=True),
            ft.Icon(ft.Icons.CHEVRON_RIGHT, size=18, color=ROXO),
        ], spacing=14),
        bgcolor=CARD,
        border=ft.border.all(1, "#BC8CFF33"),
        border_radius=14,
        padding=ft.padding.symmetric(horizontal=16, vertical=14),
        on_click=lambda e: _lazy_fn("tela_parecer", "criar_tela_parecer")(),
        ink=True,
    )

    # ══════════════════════════════════════════════════════════════
    # SCORE DE SAÚDE
    # ══════════════════════════════════════════════════════════════
    barra_score   = ft.ProgressBar(value=0, color=AZUL, bgcolor=BD, height=8)
    txt_score_num = ft.Text("--", size=22, weight=ft.FontWeight.W_900, color=AZUL)
    txt_score_rot = ft.Text("/100", size=12, color=SEC)
    txt_nota      = ft.Text("--", size=13, weight=ft.FontWeight.W_600, color=SEC)
    txt_tendencia = ft.Text("", size=11, color=SEC)
    txt_detalhes  = ft.Text("", size=10, color=MUT)

    card_score = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.FAVORITE, size=14, color=VERM),
                ft.Text("SCORE DE SAÚDE", size=10, weight=ft.FontWeight.W_700, color=SEC),
                ft.Container(expand=True),
                txt_tendencia,
            ], spacing=6),
            ft.Container(height=6),
            ft.Row([
                ft.Row([txt_score_num, txt_score_rot], spacing=2, tight=True),
                ft.Container(expand=True),
                txt_nota,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=6),
            barra_score,
            ft.Container(height=4),
            txt_detalhes,
        ], spacing=0),
        bgcolor=CARD,
        border=ft.border.all(1, BD),
        border_radius=14,
        padding=ft.padding.symmetric(horizontal=16, vertical=14),
    )

    # ══════════════════════════════════════════════════════════════
    # ALERTAS DO DIA
    # ══════════════════════════════════════════════════════════════
    chips_hoje = ft.Row(spacing=8, wrap=True)

    # ══════════════════════════════════════════════════════════════
    # MINI STATS
    # ══════════════════════════════════════════════════════════════
    txt_stat_remedios = ft.Text("--", size=18, weight=ft.FontWeight.W_700, color=AMAR)
    txt_stat_consulta = ft.Text("--", size=12, weight=ft.FontWeight.W_700, color=AZUL,
                                 text_align=ft.TextAlign.CENTER)
    txt_stat_exames   = ft.Text("--", size=18, weight=ft.FontWeight.W_700, color=ROXO)

    def _mini_stat(val_ctrl, label, cor, icone):
        return ft.Container(
            content=ft.Column([
                ft.Icon(icone, size=16, color=cor),
                val_ctrl,
                ft.Text(label, size=9, color=SEC, text_align=ft.TextAlign.CENTER),
            ], alignment=ft.MainAxisAlignment.CENTER,
               horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               spacing=4),
            bgcolor=CARD,
            border=ft.border.all(1, BD),
            border_radius=10,
            padding=10,
            expand=True,
            alignment=ft.alignment.Alignment(0, 0),
        )

    mini_stats = ft.Row([
        _mini_stat(txt_stat_remedios, "Remédios",        AMAR, ft.Icons.MEDICATION),
        _mini_stat(txt_stat_consulta, "Próx.\nConsulta", AZUL, ft.Icons.EVENT_NOTE),
        _mini_stat(txt_stat_exames,   "Exames/mês",      ROXO, ft.Icons.BIOTECH),
    ], spacing=8)

    # ══════════════════════════════════════════════════════════════
    # SYNC BAR
    # ══════════════════════════════════════════════════════════════
    ico_sync = ft.Icon(ft.Icons.CLOUD_DONE_ROUNDED, size=14, color=MUT)
    txt_sync = ft.Text("Sincronização não configurada", size=11, color=MUT)

    def _on_backup_status(topic, msg):
        txt = (msg.get("msg", "") if isinstance(msg, dict) else str(msg))
        txt_sync.value = (txt[:60] if txt else "Backup automático ativo")
        txt_sync.color = VERD
        ico_sync.color = VERD
        _atualizar_ui()

    page.pubsub.subscribe_topic("_backup_status", _on_backup_status)

    row_sync = ft.Container(
        content=ft.Row([
            ico_sync,
            txt_sync,
            ft.Container(expand=True),
        ], spacing=6),
        bgcolor=BG,
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
        border=ft.Border(top=ft.BorderSide(1, BD)),
    )

    # ══════════════════════════════════════════════════════════════
    # ABAS E NAVEGAÇÃO
    # ══════════════════════════════════════════════════════════════
    ABAS = [
        ("Início",  ft.Icons.HOME_ROUNDED,     AZUL),
        ("Exames",  ft.Icons.FOLDER_OPEN,       ROXO),
        ("Clínico", ft.Icons.HEALTH_AND_SAFETY, VERD),
        ("Mais",    ft.Icons.GRID_VIEW_ROUNDED, SEC),
    ]
    barra_abas_row = ft.Row(spacing=0)
    area_conteudo  = ft.ListView(spacing=12, padding=ft.padding.all(16), expand=True)

    def _rebuild_abas():
        barra_abas_row.controls.clear()
        for i, (label, icone, cor) in enumerate(ABAS):
            ativa = aba_ativa[0] == i
            barra_abas_row.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon(icone, size=20, color=cor if ativa else MUT),
                    ft.Text(label, size=9,
                            color=cor if ativa else MUT,
                            weight=ft.FontWeight.W_600 if ativa else ft.FontWeight.W_400),
                ], alignment=ft.MainAxisAlignment.CENTER,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=2),
                expand=True,
                border=ft.Border(top=ft.BorderSide(2, cor if ativa else "transparent")),
                padding=ft.padding.symmetric(vertical=8),
                alignment=ft.alignment.Alignment(0, 0),
                on_click=lambda e, idx=i: _trocar_aba(idx),
                ink=True,
            ))

    # ── ABA 0: Início ────────────────────────────────────────────
    def _conteudo_inicio():
        return [
            card_claudia,
            _secao_titulo("SCORE DE SAÚDE", ft.Icons.FAVORITE, VERM),
            card_score,
            _secao_titulo("HOJE", ft.Icons.TODAY, AMAR),
            chips_hoje,
            _secao_titulo("RESUMO", ft.Icons.INSIGHTS, ROXO),
            mini_stats,
        ]

    # ── ABA 2: Clínico ───────────────────────────────────────────
    def _conteudo_clinico():
        def _btn_item(icone, label, desc, cor, fn):
            return ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(icone, size=15, color=cor),
                        bgcolor=cor + "18", border_radius=8,
                        width=32, height=32,
                        alignment=ft.alignment.Alignment(0, 0),
                    ),
                    ft.Column([
                        ft.Text(label, size=13, color=TXT, weight=ft.FontWeight.W_500),
                        ft.Text(desc, size=10, color=SEC),
                    ], spacing=0, tight=True, expand=True),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, size=16, color=MUT),
                ], spacing=12),
                bgcolor=CARD,
                padding=ft.padding.symmetric(horizontal=16, vertical=11),
                border=ft.Border(bottom=ft.BorderSide(1, BD)),
                on_click=lambda e: fn(),
                ink=True,
            )
        return [
            ft.Container(
                content=ft.Column([
                    _btn_item(ft.Icons.EVENT_NOTE, "Consultas",
                              "Histórico de consultas", VERD,
                              _lazy_fn("tela_consultas_medicas", "criar_tela_consultas_medicas")),
                    _btn_item(ft.Icons.MEDICATION, "Medicamentos",
                              "Remédios e horários", AMAR,
                              _lazy_fn("tela_remedios", "criar_tela_remedios")),
                    _btn_item(ft.Icons.RESTAURANT_MENU, "Dieta & Diário",
                              "Alimentação e saúde", VERD,
                              _lazy_fn("tela_dieta", "criar_tela_dieta")),
                    _btn_item(ft.Icons.PSYCHOLOGY, "Parecer IA",
                              "Análise com Claude", ROXO,
                              _lazy_fn("tela_parecer", "criar_tela_parecer")),
                ], spacing=0),
                bgcolor=CARD,
                border_radius=12,
                border=ft.border.all(1, BD),
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            ),
        ]

    # ── ABA 3: Mais ──────────────────────────────────────────────
    def _conteudo_mais():
        def _item(icon, label, desc, cor, fn):
            return ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(icon, size=15, color=cor),
                        bgcolor=cor + "18", border_radius=8,
                        width=32, height=32,
                        alignment=ft.alignment.Alignment(0, 0),
                    ),
                    ft.Column([
                        ft.Text(label, size=13, color=TXT, weight=ft.FontWeight.W_500),
                        ft.Text(desc, size=10, color=SEC),
                    ], spacing=0, tight=True, expand=True),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, size=16, color=MUT),
                ], spacing=12),
                bgcolor=CARD,
                padding=ft.padding.symmetric(horizontal=16, vertical=11),
                border=ft.Border(bottom=ft.BorderSide(1, BD)),
                on_click=lambda e: fn(),
                ink=True,
            )

        def _group(titulo, cor, icone, items):
            return ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(icone, size=12, color=cor),
                        ft.Text(titulo, size=10, weight=ft.FontWeight.W_700, color=cor),
                    ], spacing=6),
                    padding=ft.padding.only(bottom=6, top=4),
                ),
                ft.Container(
                    content=ft.Column(items, spacing=0),
                    bgcolor=CARD,
                    border_radius=12,
                    border=ft.border.all(1, BD),
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                ),
            ], spacing=4)

        def _nav_perfil():
            try:
                from tela_perfil import criar_tela_perfil
                _ir(criar_tela_perfil)
            except ImportError:
                _lazy_fn("tela_perfil", "criar_tela_perfil")()

        return [
            _group("EXAMES", AZUL, ft.Icons.FOLDER_OPEN, [
                _item(ft.Icons.UPLOAD_FILE, "Incluir Exame", "Importar PDF", AZUL,
                      lambda: _navegar(page, _tela_incluir_exame, _voltar_hub)),
                _item(ft.Icons.ANALYTICS, "Histórico", "Gráficos e evolução", VERD,
                      _lazy_fn("tela_exames", "criar_tela_consulta")),
                _item(ft.Icons.DESCRIPTION, "Processados", "Exames importados", AMAR,
                      _lazy_fn("tela_exames_processados", "criar_tela_exames_processados")),
                _item(ft.Icons.SCIENCE, "Exames Padrão", "Referências e cadastro", ROXO,
                      _lazy_fn("tela_exames_padrao", "criar_tela_exames_padrao")),
                _item(ft.Icons.LOCAL_HOSPITAL, "Especialidades", "Áreas médicas", AMAR,
                      _lazy_fn("tela_especialidades", "criar_tela_especialidades")),
                _item(ft.Icons.BIOTECH, "Laboratórios", "Labs e extratores", VERM,
                      _lazy_fn("tela_laboratorios", "criar_tela_laboratorios")),
            ]),
            _group("MÉDICOS", ROXO, ft.Icons.PEOPLE, [
                _item(ft.Icons.PEOPLE, "Médicos", "Cadastro e histórico", ROXO,
                      _lazy_fn("tela_medicos", "criar_tela_medicos")),
                _item(ft.Icons.LINK, "Links Médico", "Tokens de acesso", AZUL,
                      _lazy_fn("tela_links_medico", "criar_tela_links_medico")),
            ]),
            _group("CONFIGURAÇÕES", SEC, ft.Icons.SETTINGS, [
                _item(ft.Icons.SETTINGS, "Configurações",
                      "Perfil, Backup e Drive", SEC,
                      _lazy_fn("tela_config", "criar_tela_config")),
            ]),
        ]

    def _rebuild_conteudo():
        area_conteudo.controls.clear()
        idx = aba_ativa[0]
        if idx == 0:
            for c in _conteudo_inicio():
                area_conteudo.controls.append(c)
        elif idx == 2:
            for c in _conteudo_clinico():
                area_conteudo.controls.append(c)
        elif idx == 3:
            for c in _conteudo_mais():
                area_conteudo.controls.append(c)

    def _trocar_aba(idx):
        if idx == 1:
            _lazy_fn("tela_exames", "criar_tela_consulta")()
            return
        aba_ativa[0] = idx
        _rebuild_abas()
        _rebuild_conteudo()
        _atualizar_ui()

    # ══════════════════════════════════════════════════════════════
    # CARREGAR DADOS EM BACKGROUND
    # ══════════════════════════════════════════════════════════════

    def _carregar_tudo_sync():
        """Carrega dados sincrono — já estamos em thread de background (_iniciar)."""
        remedios_ativos = []

        # ── Score de Saúde ───────────────────────────────────────
        try:
            conn = _sq.connect(DB_PATH, timeout=30)
            try:
                rows = conn.execute("""
                    SELECT valor, referencia FROM resultados_estruturados
                    WHERE referencia IS NOT NULL AND referencia != ''
                    ORDER BY rowid DESC LIMIT 200
                """).fetchall()
            finally:
                conn.close()

            dentro = 0
            for valor_str, ref_str in rows:
                try:
                    v = float(str(valor_str).replace(",", "."))
                    ref = str(ref_str).strip()
                    if " - " in ref or " – " in ref:
                        partes = ref.replace(" – ", " - ").split(" - ")
                        lo, hi = float(partes[0]), float(partes[1])
                        dentro += 1 if lo <= v <= hi else 0
                    elif ref.startswith("<"):
                        dentro += 1 if v < float(ref[1:].strip()) else 0
                    elif ref.startswith(">"):
                        dentro += 1 if v > float(ref[1:].strip()) else 0
                    else:
                        dentro += 1
                except Exception:
                    dentro += 1
            score_ex = round(dentro / len(rows) * 100, 1) if rows else 100.0
        except Exception:
            score_ex = 100.0

        try:
            remedios_ativos = listar_remedios(so_ativos=True)
            if remedios_ativos:
                perc_list = [resumo_adesao(r["id"])["percentual"] for r in remedios_ativos]
                score_ad = round(sum(perc_list) / len(perc_list), 1)
            else:
                score_ad = 100.0
        except Exception:
            score_ad = 100.0

        try:
            cutoff = (date.today() - timedelta(days=90)).isoformat()
            realizadas = [
                c for c in listar_consultas(tipo="realizada")
                if (c["data"] or "") >= cutoff
            ]
            score_co = 100.0 if realizadas else 50.0
        except Exception:
            score_co = 50.0

        score_final = round(score_ex * 0.60 + score_ad * 0.30 + score_co * 0.10, 1)
        if score_final >= 90:
            nota, cor_s = "Excelente", VERD
        elif score_final >= 75:
            nota, cor_s = "Bom", AZUL
        elif score_final >= 60:
            nota, cor_s = "Regular", AMAR
        else:
            nota, cor_s = "Atenção", VERM

        barra_score.value   = score_final / 100
        barra_score.color   = cor_s
        txt_score_num.value = str(int(score_final))
        txt_score_num.color = cor_s
        txt_nota.value      = nota
        txt_nota.color      = cor_s
        txt_detalhes.value  = f"Exames {score_ex:.0f}%  ·  Remédios {score_ad:.0f}%"

        # ── Mini stats ───────────────────────────────────────────
        try:
            agendadas = sorted(
                [
                    c for c in listar_consultas(tipo="agendada")
                    if (c["data"] or "") >= date.today().isoformat()
                ],
                key=lambda x: x["data"],
            )
            proxima = agendadas[0]["data"] if agendadas else None
            d_txt = (proxima[8:10] + "/" + proxima[5:7]) if proxima else "Nenhuma"

            conn = _sq.connect(DB_PATH, timeout=30)
            try:
                mes = date.today().strftime("%Y-%m")
                n_ex = conn.execute(
                    "SELECT COUNT(*) FROM exames WHERE strftime('%Y-%m', data_exame) = ?",
                    (mes,),
                ).fetchone()[0]
            finally:
                conn.close()

            txt_stat_remedios.value = str(len(remedios_ativos))
            txt_stat_consulta.value = d_txt
            txt_stat_exames.value   = str(n_ex)
        except Exception as ex:
            logging.exception("[HUB] Erro stats: %s", ex)

        # ── Chips de hoje ────────────────────────────────────────
        try:
            tomadas   = listar_tomadas_hoje()
            pendentes = [t for t in tomadas if t["status"] == "pendente"]
            hoje_str  = date.today().isoformat()
            cons_hoje = [
                c for c in listar_consultas(tipo="agendada")
                if c["data"] == hoje_str
            ]
            pend = len(pendentes)
            cons = len(cons_hoje)
        except Exception:
            pend, cons = 0, 0

        chips_hoje.controls.clear()
        if pend > 0:
            chips_hoje.controls.append(
                _chip(f"{pend} remédio(s)", AMAR, ft.Icons.MEDICATION,
                      _lazy_fn("tela_remedios", "criar_tela_remedios"))
            )
        if cons > 0:
            chips_hoje.controls.append(
                _chip(f"{cons} consulta(s)", AZUL, ft.Icons.EVENT_NOTE,
                      _lazy_fn("tela_consultas_medicas", "criar_tela_consultas_medicas"))
            )
        if not pend and not cons:
            chips_hoje.controls.append(
                _chip("Dia tranquilo", VERD, ft.Icons.CHECK_CIRCLE, lambda: None)
            )

        # ── Sync bar — estado inicial (creds existem = autenticado) ─
        try:
            from shared.auth import _CREDS_PATH as _auth_cp
            if os.path.exists(_auth_cp):
                ico_sync.color = VERD
                txt_sync.value = "Backup automático ativo"
                txt_sync.color = VERD
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════
    # HEADER
    # ══════════════════════════════════════════════════════════════
    btn_voltar = ft.Container()
    if voltar_fn:
        btn_voltar = ft.TextButton(
            content=ft.Row([
                ft.Icon(ft.Icons.ARROW_BACK, size=16, color=SEC),
                ft.Text("Voltar", size=13, color=SEC),
            ], spacing=4, tight=True),
            on_click=lambda _: voltar_fn(),
        )

    def _nav_perfil(e=None):
        from prontuario.telas.tela_perfil import criar_tela_perfil
        _ir(criar_tela_perfil)

    def _deslogar():
        def _confirmar(e2):
            dlg.open = False
            page.update()
            try:
                from prontuario.backup import backup_watcher as _bw
                if _bw._instancia:
                    _bw._instancia.parar()
            except Exception:
                pass
            try:
                from shared.auth import _CREDS_PATH
                if os.path.exists(_CREDS_PATH):
                    os.remove(_CREDS_PATH)
            except Exception:
                pass
            from prontuario.telas_shared.tela_login import criar_tela_login

            def _on_login(token, perfil):
                try:
                    from prontuario.backup.backup_watcher import BackupWatcher
                    watcher = BackupWatcher()
                    watcher.iniciar(
                        callback_ui=lambda msg: page.pubsub.send_all_on_topic(
                            "_backup_status", {"msg": msg}
                        )
                    )
                except Exception:
                    pass
                tela = _tela_principal(page, None)
                page.pubsub.send_all({"tipo": "nav", "tela": tela})

            try:
                tela_login = criar_tela_login(page, on_login_sucesso=_on_login)
                page.controls.clear()
                page.controls.append(tela_login)
                page.update()
            except Exception as ex:
                logging.exception("[HUB] Erro ao deslogar: %s", ex)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Deslogar?", color=TXT),
            content=ft.Text(
                "Tem certeza que deseja sair?\n"
                "Será necessário fazer login novamente.",
                size=13, color=SEC,
            ),
            actions=[
                ft.ElevatedButton(
                    "Cancelar",
                    bgcolor=BD, color=TXT,
                    on_click=lambda e2: (setattr(dlg, "open", False), page.update()),
                ),
                ft.TextButton(
                    "Deslogar",
                    style=ft.ButtonStyle(color=VERM),
                    on_click=_confirmar,
                ),
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    menu_usuario = ft.PopupMenuButton(
        content=ft.Container(
            content=ft.Icon(ft.Icons.PERSON_OUTLINE, size=20, color=SEC),
            padding=ft.padding.all(8),
        ),
        items=[
            ft.PopupMenuItem(
                icon=ft.Icons.MANAGE_ACCOUNTS,
                text="Perfil",
                on_click=_nav_perfil,
            ),
            ft.PopupMenuItem(),
            ft.PopupMenuItem(
                icon=ft.Icons.LOGOUT,
                text="Deslogar",
                on_click=lambda e: _deslogar(),
            ),
        ],
    )

    header = ft.Container(
        content=ft.Row([
            btn_voltar,
            ft.Row([
                ft.Icon(ft.Icons.MEDICAL_SERVICES, size=18, color=AZUL),
                ft.Text("Prontuário", size=16, weight=ft.FontWeight.W_700, color=TXT),
            ], spacing=8, tight=True),
            ft.Container(expand=True),
            menu_usuario,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
    )

    # ══════════════════════════════════════════════════════════════
    # MONTAR LAYOUT
    # ══════════════════════════════════════════════════════════════
    _rebuild_abas()
    _rebuild_conteudo()

    nav_bar = ft.Container(
        content=barra_abas_row,
        bgcolor=CARD,
        border=ft.Border(top=ft.BorderSide(1, BD)),
        height=58,
    )

    spacer_topo = ft.Container(height=28, bgcolor=BG)

    corpo = ft.Column([
        spacer_topo,
        header,
        area_conteudo,
        row_sync,
        nav_bar,
    ], spacing=0, expand=True)

    larg = 0
    try:
        larg = page.width or 0
    except Exception:
        pass

    if larg > 500:
        conteudo_final = ft.Row([
            ft.Container(expand=True),
            ft.Container(content=corpo, width=480),
            ft.Container(expand=True),
        ], expand=True)
    else:
        conteudo_final = corpo

    wrapper = ft.Column(expand=True)
    wrapper.controls.append(ft.Container(bgcolor=BG, expand=True, content=conteudo_final))

    _carregar_tudo_sync()
    _montado[0] = True
    return wrapper


# ══════════════════════════════════════════════════════════════
# ENTRYPOINT DO MÓDULO
# ══════════════════════════════════════════════════════════════

def criar_tela_prontuario(page: ft.Page, voltar_fn=None):
    """Entrypoint do módulo Prontuário."""
    criar_tabelas()
    return _tela_principal(page, voltar_fn)


# ══════════════════════════════════════════════════════════════
# TELAS INTERNAS (importadas do app.py original)
# ══════════════════════════════════════════════════════════════

# Importa as telas internas do app.py original via sys.path
# (mantidas no mesmo diretório prontuario/)
def _tela_incluir_exame(page, voltar_fn=None):
    from .telas.tela_incluir_exame import criar_tela_incluir_exame
    def _voltar():
        if voltar_fn: voltar_fn()
    return criar_tela_incluir_exame(page, _voltar)