# -*- coding: utf-8 -*-
# Prontuario Medico | app.py -- hub principal
import flet as ft
import threading
import logging
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from dados.model_prontuario import criar_tabelas, DB_PATH

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
ROXO = "#BC8CFF"; AZUL = "#58A6FF"; VERD = "#3FB950"
AMAR = "#D29922"; VERM = "#F85149"


# ══════════════════════════════════════════════════════════════
# NAVEGACAO INTERNA
# ══════════════════════════════════════════════════════════════

def _navegar(page: ft.Page, tela_fn, *args, **kwargs):
    import traceback
    nome = getattr(tela_fn, "__name__", str(tela_fn))
    log.info("[PRON] navegar -> %s", nome)
    try:
        nova_tela = tela_fn(page, *args, **kwargs)
        page.controls.clear()
        page.controls.append(nova_tela)
        try: page.update()
        except Exception: pass
    except Exception as ex:
        erro_txt = traceback.format_exc()
        log.exception("[PRON] ERRO ao navegar para %s: %s", nome, ex)
        btn_v = ft.Container(
            content=ft.Text("Voltar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{SEC}22", ink=True,
        )
        btn_v.on_click = lambda e: args[0]() if args and callable(args[0]) else None
        page.controls.clear()
        page.controls.append(ft.Container(
            content=ft.Column([
                ft.Icon("error_outline_rounded", size=40, color="#DA3633"),
                ft.Text(f"Erro: {nome}", size=14, color=TXT,
                        weight=ft.FontWeight.W_600),
                ft.Text(str(ex), size=12, color="#F0883E"),
                ft.Container(
                    content=ft.Text(erro_txt[-600:], size=10, color=SEC,
                                    selectable=True),
                    bgcolor=CARD, border_radius=8, padding=12,
                ),
                btn_v,
            ], spacing=10, scroll=ft.ScrollMode.AUTO),
            bgcolor=BG, expand=True, padding=20,
        ))
        try: page.update()
        except Exception: pass


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL
# ══════════════════════════════════════════════════════════════

def _tela_principal(page: ft.Page, voltar_fn=None):
    from datetime import datetime, date, timedelta
    import sqlite3 as _sq
    from dados.model_prontuario import (
        carregar_perfil, listar_remedios, listar_consultas,
        listar_tomadas_hoje, resumo_adesao, listar_templates,
    )

    aba_ativa = [0]
    _montado  = [False]

    def _atualizar_ui():
        if _montado[0]:
            try: page.update()
            except Exception: pass

    def _voltar_hub(*_):
        _navegar(page, _tela_principal, voltar_fn)

    def _ir(tela_fn):
        _navegar(page, tela_fn, _voltar_hub)

    def _lazy_fn(modulo, funcao):
        def _handler():
            import importlib
            caminho = modulo if "." in modulo else f"telas.{modulo}"
            mod = importlib.import_module(caminho)
            _ir(getattr(mod, funcao))
        return _handler

    # ── Nome e saudacao ──────────────────────────────────────
    _nome = [""]
    try:
        p = carregar_perfil()
        _nome[0] = (p.get("nome") or "").split()[0] if p else ""
    except Exception:
        pass

    hora = datetime.now().hour
    _saudacao = "Bom dia" if hora < 12 else ("Boa tarde" if hora < 18 else "Boa noite")

    def _secao_titulo(titulo, icone, cor):
        return ft.Row([
            ft.Icon(icone, size=12, color=cor),
            ft.Text(titulo, size=10, weight=ft.FontWeight.W_700, color=cor),
        ], spacing=6)

    def _chip(label, cor, icone, fn):
        c = ft.Container(
            content=ft.Row([
                ft.Icon(icone, size=13, color=cor),
                ft.Text(label, size=12, color=cor, weight=ft.FontWeight.W_500),
            ], spacing=5, tight=True),
            bgcolor=cor + "18",
            border=ft.border.all(1, cor + "55"),
            border_radius=20,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            ink=True,
        )
        c.on_click = lambda e: fn()
        return c

    # ══════════════════════════════════════════════════════════
    # CLAUDIA AVATAR
    # ══════════════════════════════════════════════════════════
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
                    ft.Text("Claudia disponivel", size=11, color=VERD),
                ], spacing=5, tight=True),
                ft.Text("Toque para conversar", size=10, color=MUT),
            ], spacing=3, tight=True, expand=True),
            ft.Icon("chevron_right_rounded", size=18, color=ROXO),
        ], spacing=14),
        bgcolor=CARD,
        border=ft.border.all(1, "#BC8CFF33"),
        border_radius=14,
        padding=ft.padding.symmetric(horizontal=16, vertical=14),
        ink=True,
    )
    card_claudia.on_click = lambda e: _lazy_fn("tela_claudia", "criar_tela_claudia")()

    # ══════════════════════════════════════════════════════════
    # MONITOR UTI -- canais vitais + score resumido
    # ══════════════════════════════════════════════════════════
    txt_score_num = ft.Text("--", size=13, weight=ft.FontWeight.W_700, color=AZUL)
    txt_nota      = ft.Text("--", size=11, color=SEC)
    txt_detalhes  = ft.Text("",   size=10, color=MUT)
    _score_cache  = [{}]  # armazena ultimo calculo para o overlay

    def _mostrar_score_breakdown(e=None):
        d = _score_cache[0]
        if not d:
            return
        cor = d.get("cor", AZUL)

        def _fechar(ev=None):
            if ref[0] in page.overlay:
                page.overlay.remove(ref[0])
            try: page.update()
            except Exception: pass

        def _barra(label, val, peso, cor_b):
            return ft.Column([
                ft.Row([
                    ft.Text(label, size=12, color=TXT, expand=True),
                    ft.Text(f"{val:.0f}%", size=12, color=cor_b,
                            weight=ft.FontWeight.W_700),
                    ft.Text(f"x{peso:.0f}%", size=10, color=MUT),
                ], spacing=8),
                ft.Container(
                    content=ft.ProgressBar(
                        value=val/100, color=cor_b, bgcolor=BD, height=6),
                    border_radius=3),
            ], spacing=4)

        _COR_EX = VERD if d.get("exames",0) >= 90 else (AMAR if d.get("exames",0) >= 70 else VERM)
        _COR_AD = VERD if d.get("adesao",0) >= 80 else (AMAR if d.get("adesao",0) >= 50 else VERM)
        _COR_CO = VERD if d.get("consultas",0) >= 80 else (AMAR if d.get("consultas",0) >= 50 else VERM)

        btn_fechar = ft.Container(
            content=ft.Text("Fechar", size=13, color=AZUL, weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            border_radius=8, bgcolor=AZUL + "22", ink=True,
            border=ft.border.all(1, AZUL + "66"),
        )
        btn_fechar.on_click = _fechar

        ref = [None]
        ref[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("Score de Saude", size=15, color=TXT,
                                weight=ft.FontWeight.W_700, expand=True),
                        ft.Text(f"{d['final']:.0f}", size=28, color=cor,
                                weight=ft.FontWeight.W_900),
                    ], spacing=8),
                    ft.Text(d.get("nota",""), size=12, color=cor),
                    ft.Container(height=12),
                    ft.Text("COMPOSICAO", size=10, color=MUT,
                            weight=ft.FontWeight.W_700),
                    ft.Container(height=6),
                    _barra(f"Exames ({d.get('n_exames',0)} resultados)",
                           d.get("exames",0), 60, _COR_EX),
                    ft.Container(height=8),
                    _barra(f"Adesao a remedios ({d.get('n_remedios',0)} ativos)",
                           d.get("adesao",0), 30, _COR_AD),
                    ft.Container(height=8),
                    _barra("Consultas (ultimos 90 dias)",
                           d.get("consultas",0), 10, _COR_CO),
                    ft.Container(height=4),
                    ft.Text("Formula: Exames x60%  +  Adesao x30%  +  Consultas x10%",
                            size=9, color=MUT, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=16),
                    ft.Row([btn_fechar], alignment=ft.MainAxisAlignment.CENTER),
                ], tight=True),
                bgcolor=CARD, border_radius=14, padding=ft.padding.all(24), width=320,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref[0].on_click = _fechar
        page.overlay.append(ref[0])
        try: page.update()
        except Exception: pass

    _UTI_CANAIS = [
        ("Glicemia",   "water_drop_rounded",            "#FF6B6B",
         ["glicose", "glucose", "glicemia", "glicada", "hba1c"]),
        ("Ac.Urico",   "science_rounded",               "#FFD93D",
         ["acido urico", "urico", "uratos"]),
        ("Pressao",    "favorite_rounded",              "#4ECDC4",
         ["sistolica", "pressao arterial"]),
        ("Hormonios",  "psychology_alt_rounded",        "#A29BFE",
         ["tsh", "t4 livre", "cortisol"]),
        ("Vitaminas",  "wb_sunny_rounded",              "#FDCB6E",
         ["vitamina d", "25-oh", "vitamina b12"]),
        ("Inflamacao", "local_fire_department_rounded", "#FF7675",
         ["pcr", "proteina c reativa", "vhs"]),
    ]

    def _avaliar_status_cor(valor_str, referencia_str):
        try:
            v = float(str(valor_str).replace(",", ".").strip())
            ref = str(referencia_str or "").strip()
            if " - " in ref:
                lo, hi = [float(x) for x in ref.split(" - ", 1)]
                if lo <= v <= hi:
                    return VERD
                m = (hi - lo) * 0.2
                if (lo - m) <= v <= (hi + m):
                    return AMAR
                return VERM
            elif ref.startswith("<"):
                lim = float(ref[1:].strip())
                if v < lim:
                    return VERD
                if v < lim * 1.25:
                    return AMAR
                return VERM
            elif ref.startswith(">"):
                lim = float(ref[1:].strip())
                if v > lim:
                    return VERD
                if v > lim * 0.8:
                    return AMAR
                return VERM
        except Exception:
            pass
        return AZUL

    _uti_refs: list = []
    _uti_row = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=8)

    def _abrir_grafico_canal(lbl, termos, cor):
        from telas.tela_grafico_marcador import criar_tela_grafico_marcador
        _navegar(page,
                 lambda p, v: criar_tela_grafico_marcador(p, v, lbl, termos, cor),
                 _voltar_hub)

    def _abrir_glicemia():
        from telas.tela_glicemia import criar_tela_glicemia
        _navegar(page, criar_tela_glicemia, _voltar_hub)

    def _mk_click_uti(lbl, termos, cor):
        if lbl == "Glicemia":
            def _h(e): _abrir_glicemia()
        else:
            def _h(e): _abrir_grafico_canal(lbl, termos, cor)
        return _h

    for _lbl, _ico, _cor, _termos in _UTI_CANAIS:
        _tv  = ft.Text("--", size=18, weight=ft.FontWeight.W_900,
                       color=_cor, text_align=ft.TextAlign.CENTER)
        _tu  = ft.Text("",   size=8,  color=SEC, text_align=ft.TextAlign.CENTER)
        _td  = ft.Text("",   size=8,  color=MUT, text_align=ft.TextAlign.CENTER)
        _tm  = ft.Text("",   size=8,  color=MUT, text_align=ft.TextAlign.CENTER)
        _dot = ft.Container(width=6, height=6, border_radius=3, bgcolor=MUT)
        _card_uti = ft.Container(
            content=ft.Column([
                ft.Row([_dot], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=1),
                ft.Icon(_ico, size=13, color=_cor + "99"),
                ft.Text(_lbl, size=9, color=SEC,
                        text_align=ft.TextAlign.CENTER,
                        weight=ft.FontWeight.W_600),
                ft.Container(height=3),
                _tv,
                _tu,
                _td,
                _tm,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               spacing=1, tight=True),
            bgcolor="#080C11",
            border=ft.border.all(1, _cor + "33"),
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=10, vertical=10),
            width=88,
            ink=True,
        )
        _card_uti.on_click = _mk_click_uti(_lbl, _termos, _cor)
        _uti_refs.append({
            "val": _tv, "unit": _tu, "data": _td, "media": _tm,
            "dot": _dot, "card": _card_uti, "cor": _cor,
            "termos": _termos, "lbl": _lbl,
        })
        _uti_row.controls.append(_card_uti)

    _btn_marc = ft.Container(
        content=ft.Row([
            ft.Icon("bar_chart_rounded", size=12, color=AZUL),
            ft.Text("Gerenciar", size=10, color=AZUL),
        ], spacing=3, tight=True),
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        border_radius=8, bgcolor=AZUL + "18", ink=True,
    )
    _btn_marc.on_click = lambda e: _lazy_fn(
        "tela_marcadores", "criar_tela_marcadores")()

    _row_score = ft.Container(
        content=ft.Row([
            ft.Text("Score", size=10, color=MUT),
            txt_score_num,
            txt_nota,
            ft.Icon("info_outline_rounded", size=11, color=MUT),
        ], spacing=4, tight=True),
        border_radius=8, ink=True, padding=ft.padding.symmetric(horizontal=4, vertical=2),
    )
    _row_score.on_click = _mostrar_score_breakdown

    card_monitor_uti = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon("monitor_heart_rounded", size=13, color="#FF7675"),
                ft.Text("MONITOR VITAL", size=10,
                        weight=ft.FontWeight.W_700, color=SEC),
                ft.Container(expand=True),
                _row_score,
                _btn_marc,
            ], spacing=6),
            ft.Container(height=8),
            _uti_row,
            ft.Container(height=4),
            txt_detalhes,
        ], spacing=0),
        bgcolor=CARD,
        border=ft.border.all(1, BD),
        border_radius=14,
        padding=ft.padding.symmetric(horizontal=12, vertical=12),
    )

    # ══════════════════════════════════════════════════════════
    # ALERTAS DO DIA
    # ══════════════════════════════════════════════════════════
    chips_hoje = ft.Row(spacing=8, wrap=True)

    # ══════════════════════════════════════════════════════════
    # MINI STATS
    # ══════════════════════════════════════════════════════════
    txt_stat_remedios  = ft.Text("--", size=18, weight=ft.FontWeight.W_700, color=AMAR)
    txt_stat_consulta  = ft.Text("--", size=12, weight=ft.FontWeight.W_700, color=AZUL,
                                 text_align=ft.TextAlign.CENTER)
    txt_stat_rotinas   = ft.Text("--", size=14, weight=ft.FontWeight.W_700, color=VERD,
                                 text_align=ft.TextAlign.CENTER)
    txt_prox_rotina    = ft.Text("",   size=9,  color=SEC,
                                 text_align=ft.TextAlign.CENTER, max_lines=1)

    def _mini_stat(val_ctrl, label, cor, icone, fn=None):
        c = ft.Container(
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
            ink=bool(fn),
        )
        if fn:
            c.on_click = lambda e: fn()
        return c

    def _mini_stat_rotinas():
        c = ft.Container(
            content=ft.Column([
                ft.Icon("calendar_today_rounded", size=16, color=VERD),
                txt_stat_rotinas,
                txt_prox_rotina,
                ft.Text("Rotinas", size=9, color=SEC, text_align=ft.TextAlign.CENTER),
            ], alignment=ft.MainAxisAlignment.CENTER,
               horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               spacing=2),
            bgcolor=CARD,
            border=ft.border.all(1, BD),
            border_radius=10,
            padding=10,
            expand=True,
            alignment=ft.alignment.Alignment(0, 0),
            ink=True,
        )
        c.on_click = lambda e: _lazy_fn("tela_rotinas", "criar_tela_rotinas")()
        return c

    mini_stats = ft.Row([
        _mini_stat(txt_stat_remedios, "Medicamentos", AMAR, "medication_rounded",
                   _lazy_fn("tela_remedios", "criar_tela_remedios")),
        _mini_stat(txt_stat_consulta, "Prox.\nCompromisso", AZUL, "event_note_rounded",
                   _lazy_fn("tela_compromissos", "criar_tela_compromissos")),
        _mini_stat_rotinas(),
    ], spacing=8)

    # ══════════════════════════════════════════════════════════
    # SYNC BAR
    # ══════════════════════════════════════════════════════════
    ico_sync = ft.Icon("cloud_done_rounded", size=14, color=MUT)
    txt_sync = ft.Text("Sincronizacao nao configurada", size=11, color=MUT)

    _countdown_ativo = [False]

    def _parar_countdown():
        _countdown_ativo[0] = False

    def _iniciar_countdown():
        _countdown_ativo[0] = True
        def _run():
            import time
            while _countdown_ativo[0]:
                try:
                    from backup import backup_watcher as _bw
                    inst = _bw._instancia
                    if inst and inst.status == "pendente":
                        restante = inst.proximo_backup_em
                        page.pubsub.send_all_on_topic("_backup_status", {
                            "fase": "_tick",
                            "txt":  f"Backup em {restante}",
                        })
                except Exception:
                    pass
                time.sleep(1)
        threading.Thread(target=_run, daemon=True).start()

    def _on_backup_status(topic, msg):
        if not isinstance(msg, dict):
            msg = {"fase": "msg", "msg": str(msg)}
        fase = msg.get("fase", "msg")
        if fase == "pendente":
            _iniciar_countdown()
            return
        _parar_countdown()
        if fase == "_tick":
            txt_sync.value = msg.get("txt", "")
            txt_sync.color = AMAR
            ico_sync.color = AMAR
            ico_sync.name = "cloud_sync_rounded"
        elif fase == "executando":
            txt_sync.value = "Fazendo backup..."
            txt_sync.color = AZUL
            ico_sync.color = AZUL
            ico_sync.name = "cloud_upload_rounded"
        elif fase == "concluido":
            txt_sync.value = "Backup concluido"
            txt_sync.color = VERD
            ico_sync.color = VERD
            ico_sync.name = "cloud_done_rounded"
        elif fase == "erro":
            txt_sync.value = f"Erro: {msg.get('msg', '')[:50]}"
            txt_sync.color = VERM
            ico_sync.color = VERM
            ico_sync.name = "cloud_off_rounded"
        else:
            txt = msg.get("msg", "")
            txt_sync.value = txt[:60] if txt else "Backup automatico ativo"
            txt_sync.color = VERD
            ico_sync.color = VERD
            ico_sync.name = "cloud_done_rounded"
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

    # ══════════════════════════════════════════════════════════
    # ABAS E NAVEGACAO
    # ══════════════════════════════════════════════════════════
    ABAS = [
        ("Inicio",  "home_rounded",             AZUL),
        ("Exames",  "folder_open_rounded",      ROXO),
        ("Clinico", "health_and_safety_rounded", VERD),
        ("Mais",    "grid_view_rounded",         SEC),
    ]
    barra_abas_row = ft.Row(spacing=0)
    area_conteudo  = ft.ListView(spacing=12, padding=ft.padding.all(16), expand=True)

    def _rebuild_abas():
        barra_abas_row.controls.clear()
        for i, (label, icone, cor) in enumerate(ABAS):
            ativa = aba_ativa[0] == i
            tab = ft.Container(
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
                ink=True,
            )
            tab.on_click = lambda e, idx=i: _trocar_aba(idx)
            barra_abas_row.controls.append(tab)

    # ── ABA 0: Inicio ────────────────────────────────────────
    def _conteudo_inicio():
        return [
            card_claudia,
            _secao_titulo("MONITOR VITAL", "monitor_heart_rounded", "#FF7675"),
            card_monitor_uti,
            _secao_titulo("HOJE", "today_rounded", AMAR),
            chips_hoje,
            _secao_titulo("RESUMO", "insights_rounded", ROXO),
            mini_stats,
        ]

    # ── ABA 2: Clinico ───────────────────────────────────────
    def _conteudo_clinico():
        def _btn_item(icone, label, desc, cor, fn):
            c = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(icone, size=15, color=cor),
                        bgcolor=cor + "18", border_radius=8,
                        width=32, height=32,
                        alignment=ft.alignment.Alignment(0, 0),
                    ),
                    ft.Column([
                        ft.Text(label, size=13, color=TXT,
                                weight=ft.FontWeight.W_500),
                        ft.Text(desc, size=10, color=SEC),
                    ], spacing=0, tight=True, expand=True),
                    ft.Icon("chevron_right_rounded", size=16, color=MUT),
                ], spacing=12),
                bgcolor=CARD,
                padding=ft.padding.symmetric(horizontal=16, vertical=11),
                border=ft.Border(bottom=ft.BorderSide(1, BD)),
                ink=True,
            )
            c.on_click = lambda e: fn()
            return c

        return [
            ft.Container(
                content=ft.Column([
                    _btn_item("event_note_rounded", "Compromissos",
                              "Consultas, coletas e fisioterapia", VERD,
                              _lazy_fn("tela_compromissos",
                                       "criar_tela_compromissos")),
                    _btn_item("medication_rounded", "Medicacao",
                              "Remedios e suplementos", AMAR,
                              _lazy_fn("tela_remedios", "criar_tela_remedios")),
                    _btn_item("calendar_today_rounded", "Rotinas Diarias",
                              "Habitos e alimentacao", VERD,
                              _lazy_fn("tela_rotinas", "criar_tela_rotinas")),
                    _btn_item("psychology_rounded", "Claudia IA",
                              "Conversar com Claudia", ROXO,
                              _lazy_fn("tela_claudia", "criar_tela_claudia")),
                    _btn_item("biotech_rounded", "Marcadores",
                              "Sinais vitais e historico", "#4ECDC4",
                              _lazy_fn("tela_marcadores", "criar_tela_marcadores")),
                ], spacing=0),
                bgcolor=CARD,
                border_radius=12,
                border=ft.border.all(1, BD),
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            ),
        ]

    # ── ABA 3: Mais ──────────────────────────────────────────
    def _conteudo_mais():
        def _item(icon, label, desc, cor, fn):
            c = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(icon, size=15, color=cor),
                        bgcolor=cor + "18", border_radius=8,
                        width=32, height=32,
                        alignment=ft.alignment.Alignment(0, 0),
                    ),
                    ft.Column([
                        ft.Text(label, size=13, color=TXT,
                                weight=ft.FontWeight.W_500),
                        ft.Text(desc, size=10, color=SEC),
                    ], spacing=0, tight=True, expand=True),
                    ft.Icon("chevron_right_rounded", size=16, color=MUT),
                ], spacing=12),
                bgcolor=CARD,
                padding=ft.padding.symmetric(horizontal=16, vertical=11),
                border=ft.Border(bottom=ft.BorderSide(1, BD)),
                ink=True,
            )
            c.on_click = lambda e: fn()
            return c

        def _group(titulo, cor, icone, items):
            return ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(icone, size=12, color=cor),
                        ft.Text(titulo, size=10, weight=ft.FontWeight.W_700,
                                color=cor),
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
                from telas.tela_perfil import criar_tela_perfil
                _ir(criar_tela_perfil)
            except ImportError:
                _lazy_fn("tela_perfil", "criar_tela_perfil")()

        return [
            _group("EXAMES", AZUL, "folder_open_rounded", [
                _item("upload_file_rounded", "Incluir Exame", "Importar PDF", AZUL,
                      lambda: _navegar(page, _tela_incluir_exame, _voltar_hub)),
                _item("analytics_rounded", "Historico",
                      "Graficos e evolucao", VERD,
                      _lazy_fn("tela_exames", "criar_tela_consulta")),
                _item("description_rounded", "Processados",
                      "Exames importados", AMAR,
                      _lazy_fn("tela_exames_processados",
                               "criar_tela_exames_processados")),
                _item("science_rounded", "Exames Padrao",
                      "Referencias e cadastro", ROXO,
                      _lazy_fn("tela_exames_padrao", "criar_tela_exames_padrao")),
                _item("local_hospital_rounded", "Especialidades",
                      "Areas medicas", AMAR,
                      _lazy_fn("tela_especialidades",
                               "criar_tela_especialidades")),
                _item("biotech_rounded", "Laboratorios",
                      "Labs e extratores", VERM,
                      _lazy_fn("tela_laboratorios", "criar_tela_laboratorios")),
            ]),
            _group("MEDICOS", ROXO, "people_rounded", [
                _item("people_rounded", "Medicos",
                      "Cadastro e historico", ROXO,
                      _lazy_fn("tela_medicos", "criar_tela_medicos")),
                _item("local_hospital_rounded", "Clinicas",
                      "Locais de atendimento", AZUL,
                      _lazy_fn("tela_clinicas", "criar_tela_clinicas")),
                _item("link_rounded", "Links Medico",
                      "Tokens de acesso", AZUL,
                      _lazy_fn("tela_links_medico", "criar_tela_links_medico")),
            ]),
            _group("CONFIGURACOES", SEC, "settings_rounded", [
                _item("settings_rounded", "Configuracoes",
                      "Perfil, Backup e Drive", SEC,
                      _lazy_fn("telas_sistema.tela_config", "criar_tela_config")),
            ]),
        ]

    def _rebuild_conteudo():
        area_conteudo.controls.clear()
        idx = aba_ativa[0]
        if idx == 0:
            area_conteudo.controls.extend(_conteudo_inicio())
        elif idx == 2:
            area_conteudo.controls.extend(_conteudo_clinico())
        elif idx == 3:
            area_conteudo.controls.extend(_conteudo_mais())

    def _trocar_aba(idx):
        if idx == 1:
            _lazy_fn("tela_exames", "criar_tela_consulta")()
            return
        aba_ativa[0] = idx
        _rebuild_abas()
        _rebuild_conteudo()
        _atualizar_ui()

    # ══════════════════════════════════════════════════════════
    # CARREGAR DADOS EM BACKGROUND
    # ══════════════════════════════════════════════════════════

    def _carregar_tudo_sync():
        remedios_ativos = []

        # Score de Saude
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
                    if " - " in ref or " - " in ref:
                        partes = ref.replace(" - ", " - ").split(" - ")
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
                perc_list = [resumo_adesao(r["id"])["percentual"]
                             for r in remedios_ativos]
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
            nota, cor_s = "Atencao", VERM

        txt_score_num.value = str(int(score_final))
        txt_score_num.color = cor_s
        txt_nota.value      = nota
        txt_nota.color      = cor_s
        txt_detalhes.value  = f"Ex {score_ex:.0f}%  .  Rem {score_ad:.0f}%"
        # Armazena breakdown para o overlay de detalhes
        _score_cache[0] = {
            "final": score_final, "nota": nota, "cor": cor_s,
            "exames": score_ex, "adesao": score_ad, "consultas": score_co,
            "n_exames": len(rows), "n_remedios": len(remedios_ativos),
        }

        # Mini stats
        try:
            hoje_iso = date.today().isoformat()
            def _dmy_to_iso(s):
                try:
                    d, m, y = s.split("/")
                    return f"{y}-{m}-{d}"
                except Exception:
                    return ""
            agendadas = sorted(
                [(c, _dmy_to_iso(c["data"] or ""))
                 for c in listar_consultas(tipo="agendada")],
                key=lambda x: x[1],
            )
            futuras = [c for c, iso in agendadas if iso >= hoje_iso]
            proxima = futuras[0]["data"] if futuras else None
            d_txt = proxima if proxima else "Nenhuma"

            try:
                templates = listar_templates()
                n_rot = len(templates)
                # Nome da primeira rotina padrao (ou a primeira disponivel)
                padrao = next((t for t in templates if t.get("padrao")), None)
                if not padrao and templates:
                    padrao = templates[0]
                txt_prox_rotina.value = padrao["nome"] if padrao else ""
            except Exception:
                n_rot = 0
                txt_prox_rotina.value = ""

            txt_stat_remedios.value = str(len(remedios_ativos))
            txt_stat_consulta.value = d_txt
            txt_stat_rotinas.value  = f"{n_rot}" if n_rot else "--"
        except Exception as ex:
            log.exception("[HUB] Erro stats: %s", ex)

        # Chips de hoje
        try:
            tomadas   = listar_tomadas_hoje()
            pendentes = [t for t in tomadas if t["status"] == "pendente"]
            hoje_str  = date.today().isoformat()
            cons_hoje = [c for c in listar_consultas(tipo="agendada")
                         if c["data"] == hoje_str]
            pend = len(pendentes)
            cons = len(cons_hoje)
        except Exception:
            pend, cons = 0, 0

        # Medicos cadastrados apenas com nome (pendente completar)
        med_incompletos = 0
        try:
            conn_mi = _sq.connect(DB_PATH, timeout=30)
            try:
                med_incompletos = conn_mi.execute("""
                    SELECT COUNT(*) FROM medicos
                    WHERE (crm IS NULL OR crm = '')
                      AND especialidade_id IS NULL
                      AND (telefone IS NULL OR telefone = '')
                      AND ativo = 1
                """).fetchone()[0]
            finally:
                conn_mi.close()
        except Exception:
            med_incompletos = 0

        chips_hoje.controls.clear()
        # Somente compromissos externos — remedios sao alertados via alarme
        if cons > 0:
            chips_hoje.controls.append(
                _chip(f"{cons} compromisso(s)", AZUL, "event_note_rounded",
                      _lazy_fn("tela_compromissos",
                               "criar_tela_compromissos"))
            )
        if med_incompletos > 0:
            chips_hoje.controls.append(
                _chip(f"{med_incompletos} medico(s) incompleto(s)", ROXO,
                      "person_add_rounded",
                      _lazy_fn("tela_medicos", "criar_tela_medicos"))
            )
        if not cons and not med_incompletos:
            chips_hoje.controls.append(
                _chip("Sem compromissos hoje", VERD, "check_circle_rounded",
                      lambda: None)
            )

        # Monitor UTI -- ultimo valor + media dos ultimos 30 de cada canal
        try:
            conn_uti = _sq.connect(DB_PATH, timeout=30)
            try:
                for ref_u in _uti_refs:
                    row = None
                    for termo in ref_u["termos"]:
                        row = conn_uti.execute("""
                            SELECT r.valor, r.unidade, r.referencia, e.data_exame
                            FROM resultados_estruturados r
                            JOIN exames e ON r.exame_id = e.id
                            WHERE LOWER(r.parametro) LIKE ?
                              AND r.valor IS NOT NULL AND r.valor != ''
                            ORDER BY e.data_exame DESC LIMIT 1
                        """, (f"%{termo}%",)).fetchone()
                        if row:
                            break
                    # leitura manual pode ser mais recente
                    try:
                        for termo in ref_u["termos"]:
                            mrow = conn_uti.execute("""
                                SELECT CAST(valor AS TEXT), unidade,
                                       referencia, data_medicao
                                FROM marcadores_leituras
                                WHERE LOWER(parametro) LIKE ?
                                ORDER BY data_medicao DESC LIMIT 1
                            """, (f"%{termo}%",)).fetchone()
                            if mrow:
                                if not row or (mrow[3] or "") > (row[3] or ""):
                                    row = mrow
                                break
                    except Exception:
                        pass
                    if row:
                        val_s, unit_s, ref_s, data_s = row
                        ref_u["val"].value  = (str(val_s) or "--")[:7]
                        ref_u["unit"].value = (unit_s or "")[:6]
                        if data_s and len(data_s) >= 10:
                            d = data_s[:10]
                            ref_u["data"].value = f"{d[8:10]}/{d[5:7]}"
                        s_cor = _avaliar_status_cor(val_s, ref_s)
                        ref_u["dot"].bgcolor  = s_cor
                        ref_u["card"].border  = ft.border.all(1, s_cor + "55")
                    # media dos ultimos 30 valores
                    try:
                        vals30 = []
                        for termo in ref_u["termos"]:
                            r30 = conn_uti.execute("""
                                SELECT r.valor FROM resultados_estruturados r
                                JOIN exames e ON r.exame_id = e.id
                                WHERE LOWER(r.parametro) LIKE ?
                                  AND r.valor IS NOT NULL AND r.valor != ''
                                ORDER BY e.data_exame DESC LIMIT 30
                            """, (f"%{termo}%",)).fetchall()
                            for (v,) in r30:
                                try: vals30.append(float(str(v).replace(",", ".")))
                                except Exception: pass
                            try:
                                m30 = conn_uti.execute("""
                                    SELECT CAST(valor AS TEXT)
                                    FROM marcadores_leituras
                                    WHERE LOWER(parametro) LIKE ?
                                    ORDER BY data_medicao DESC LIMIT 30
                                """, (f"%{termo}%",)).fetchall()
                                for (v,) in m30:
                                    try: vals30.append(float(str(v).replace(",", ".")))
                                    except Exception: pass
                            except Exception:
                                pass
                            if vals30:
                                break
                        if vals30:
                            med = sum(vals30) / len(vals30)
                            ref_u["media"].value = f"med:{med:.1f}"
                    except Exception:
                        pass
            finally:
                conn_uti.close()
        except Exception as _ex_uti:
            log.warning("[HUB] UTI monitor: %s", _ex_uti)

        # Sync bar estado inicial
        try:
            from shared.auth import _CREDS_PATH as _auth_cp
            if os.path.exists(_auth_cp):
                ico_sync.color = VERD
                txt_sync.value = "Backup automatico ativo"
                txt_sync.color = VERD
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════
    # OVERLAY DE CONFIRMACAO (padrao sem modal nativo)
    # ══════════════════════════════════════════════════════════

    def _mostrar_confirmar(titulo, msg, fn_sim):
        ref = [None]

        def _fechar(e=None):
            if ref[0] and ref[0] in page.overlay:
                page.overlay.remove(ref[0])
            try: page.update()
            except Exception: pass

        def _confirmar(e):
            _fechar()
            fn_sim()

        btn_cancel = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{SEC}22", ink=True,
        )
        btn_cancel.on_click = _fechar

        btn_ok = ft.Container(
            content=ft.Text("Confirmar", size=13, color=VERM,
                            weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{VERM}22", ink=True,
        )
        btn_ok.on_click = _confirmar

        ref[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Text(titulo, size=15, color=TXT,
                            weight=ft.FontWeight.W_700, text_align="center"),
                    ft.Container(height=8),
                    ft.Text(msg, size=13, color=SEC, text_align="center"),
                    ft.Container(height=20),
                    ft.Row([btn_cancel, btn_ok], spacing=8,
                           alignment=ft.MainAxisAlignment.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(24), width=300,
            ),
            bgcolor="#CC000000", expand=True,
            alignment=ft.Alignment(0, 0),
        )
        ref[0].on_click = _fechar
        page.overlay.append(ref[0])
        try: page.update()
        except Exception: pass

    # ══════════════════════════════════════════════════════════
    # HEADER
    # ══════════════════════════════════════════════════════════

    btn_voltar = ft.Container()
    if voltar_fn:
        btn_v = ft.Container(
            content=ft.Row([
                ft.Icon("arrow_back_rounded", size=16, color=SEC),
                ft.Text("Voltar", size=13, color=SEC),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            border_radius=8, ink=True,
        )
        btn_v.on_click = lambda e: voltar_fn()
        btn_voltar = btn_v

    def _nav_perfil(e=None):
        try:
            from telas.tela_perfil import criar_tela_perfil
            _ir(criar_tela_perfil)
        except ImportError:
            _lazy_fn("tela_perfil", "criar_tela_perfil")()

    def _deslogar():
        def _fazer_deslogar():
            try:
                from backup import backup_watcher as _bw
                if getattr(_bw, "_instancia", None):
                    _bw._instancia.parar()
            except Exception:
                pass
            try:
                from shared.auth import _CREDS_PATH
                if os.path.exists(_CREDS_PATH):
                    os.remove(_CREDS_PATH)
            except Exception:
                pass
            try:
                from telas_shared.tela_login import criar_tela_login

                def _on_login():
                    try:
                        from backup.backup_watcher import BackupWatcher
                        watcher = BackupWatcher()
                        watcher.iniciar(
                            callback_ui=lambda m: page.pubsub.send_all_on_topic(
                                "_backup_status",
                                m if isinstance(m, dict) else {"fase": "msg", "msg": m}
                            )
                        )
                    except Exception:
                        pass
                    _navegar(page, _tela_principal, None)

                tela_login = criar_tela_login(page, on_login_sucesso=_on_login)
                page.controls.clear()
                page.controls.append(tela_login)
                try: page.update()
                except Exception: pass
            except Exception as ex:
                log.exception("[HUB] Erro ao deslogar: %s", ex)

        _mostrar_confirmar(
            "Deslogar?",
            "Tem certeza que deseja sair?\nSera necessario fazer login novamente.",
            _fazer_deslogar,
        )

    btn_menu = ft.Container(
        content=ft.Icon("person_outline_rounded", size=20, color=SEC),
        padding=ft.padding.all(8), border_radius=8, ink=True,
    )

    def _toggle_menu_usuario(e):
        _mostrar_confirmar(
            "Conta",
            "O que deseja fazer?",
            _deslogar,
        )

    btn_menu.on_click = _toggle_menu_usuario

    menu_usuario = ft.PopupMenuButton(
        content=ft.Container(
            content=ft.Icon("person_outline_rounded", size=20, color=SEC),
            padding=ft.padding.all(8),
        ),
        items=[
            ft.PopupMenuItem(
                text="Perfil",
                on_click=_nav_perfil,
            ),
            ft.PopupMenuItem(),
            ft.PopupMenuItem(
                text="Deslogar",
                on_click=lambda e: _deslogar(),
            ),
        ],
    )

    header = ft.Container(
        content=ft.Row([
            btn_voltar,
            ft.Row([
                ft.Icon("medical_services_rounded", size=18, color=AZUL),
                ft.Text("Prontuario", size=16, weight=ft.FontWeight.W_700,
                        color=TXT),
            ], spacing=8, tight=True),
            ft.Container(expand=True),
            menu_usuario,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
    )

    # ══════════════════════════════════════════════════════════
    # MONTAR LAYOUT
    # ══════════════════════════════════════════════════════════
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

    try:
        larg = page.width or 0
    except Exception:
        larg = 0

    if larg > 500:
        conteudo_final = ft.Row([
            ft.Container(expand=True),
            ft.Container(content=corpo, width=480),
            ft.Container(expand=True),
        ], expand=True)
    else:
        conteudo_final = corpo

    wrapper = ft.Column(expand=True)
    wrapper.controls.append(
        ft.Container(bgcolor=BG, expand=True, content=conteudo_final)
    )

    _carregar_tudo_sync()
    _montado[0] = True
    return wrapper


# ══════════════════════════════════════════════════════════════
# TELA INCLUIR EXAME (wrapper)
# ══════════════════════════════════════════════════════════════

def _tela_incluir_exame(page, voltar_fn=None):
    from telas.tela_incluir_exame import criar_tela_incluir_exame

    def _voltar():
        if voltar_fn:
            voltar_fn()

    return criar_tela_incluir_exame(page, _voltar)


# ══════════════════════════════════════════════════════════════
# ENTRYPOINT DO MODULO
# ══════════════════════════════════════════════════════════════

def criar_tela_prontuario(page: ft.Page, voltar_fn=None):
    criar_tabelas()
    import threading as _thr
    def _sync_bg():
        try:
            from dados.model_prontuario import sincronizar_anexos_pendentes
            sincronizar_anexos_pendentes()
        except Exception:
            pass
    _thr.Thread(target=_sync_bg, daemon=True).start()
    return _tela_principal(page, voltar_fn)
