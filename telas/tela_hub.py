# -*- coding: utf-8 -*-
# telas/tela_hub.py -- Hub principal do Prontuario Medico
import flet as ft
import threading
import logging
import os

from dados.model_prontuario import DB_PATH
from versao import APP_VERSAO

log = logging.getLogger(__name__)

BG       = "#1A1A2E"; CARD = "#161B22"; BD  = "#21262D"
TXT      = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
ROXO     = "#BC8CFF"; AZUL = "#58A6FF"; VERD = "#3FB950"
AMAR     = "#D29922"; VERM = "#F85149"; VERM_INT = "#CC1111"

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def _asset(nome: str) -> str:
    """Retorna path absoluto no desktop, relativo no web/Android."""
    caminho_abs = os.path.join(_ASSETS_DIR, nome)
    if os.path.isfile(caminho_abs):
        try:
            import tkinter  # noqa
            return caminho_abs  # desktop
        except ModuleNotFoundError:
            pass
    return f"assets/{nome}"  # web / Android


def criar_tela_hub(page: ft.Page, voltar_fn=None, modo_medico: bool = False) -> ft.Column:
    from datetime import datetime
    import sqlite3 as _sq
    from dados.model_prontuario import carregar_perfil

    aba_ativa = [0]
    _montado  = [False]

    def _atualizar_ui():
        if _montado[0]:
            try: page.update()
            except Exception: pass

    def _navegar(tela_fn, *args, **kwargs):
        import traceback
        nome = getattr(tela_fn, "__name__", str(tela_fn))
        log.info("[HUB] navegar -> %s", nome)
        try:
            nova_tela = tela_fn(page, *args, **kwargs)
            page.controls.clear()
            page.controls.append(nova_tela)
            try: page.update()
            except Exception: pass
        except Exception as ex:
            erro_txt = traceback.format_exc()
            log.exception("[HUB] ERRO ao navegar para %s: %s", nome, ex)
            btn_v = ft.Container(
                content=ft.Text("Voltar", size=13, color=SEC),
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                border_radius=8, bgcolor=f"{SEC}22", ink=True,
            )
            btn_v.on_click = lambda e: _voltar_hub()
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

    def _voltar_hub(*_):
        from telas.tela_hub import criar_tela_hub as _hub
        _navegar(_hub, voltar_fn)

    def _ir(tela_fn):
        _navegar(tela_fn, _voltar_hub)

    def _lazy_fn(modulo, funcao, **kw):
        def _handler():
            import importlib
            caminho = modulo if "." in modulo else f"telas.{modulo}"
            mod = importlib.import_module(caminho)
            fn = getattr(mod, funcao)
            if kw:
                _ir(lambda pg, vfn, fn=fn, kw=kw: fn(pg, vfn, **kw))
            else:
                _ir(fn)
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
            bgcolor=ft.Colors.with_opacity(0.10, cor),
            border=ft.border.all(1, ft.Colors.with_opacity(0.35, cor)),
            border_radius=20,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            ink=True,
        )
        c.on_click = lambda e: fn()
        return c

    # ══════════════════════════════════════════════════════════
    # CARD TOPO — Claudia (modo paciente) ou dados do paciente (modo medico)
    # ══════════════════════════════════════════════════════════
    def _card_topo() -> ft.Container:
        if not modo_medico:
            # ── Claudia ──────────────────────────────────────
            nome_display = f", {_nome[0]}" if _nome[0] else ""
            avatar = ft.Stack([
                ft.Container(
                    width=52, height=52, border_radius=26,
                    bgcolor=ft.Colors.with_opacity(0.06, ROXO),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.20, ROXO)),
                ),
                ft.Container(
                    width=46, height=46, border_radius=23,
                    bgcolor="#1A0E2E",
                    border=ft.border.all(2, ROXO),
                    alignment=ft.alignment.Alignment(0, 0),
                    content=ft.Text("C", size=20, weight=ft.FontWeight.W_900, color=ROXO),
                    left=3, top=3,
                ),
                ft.Container(
                    width=10, height=10, border_radius=5,
                    bgcolor=VERD, border=ft.border.all(2, BG),
                    right=1, bottom=1,
                ),
            ], width=52, height=52)

            card = ft.Container(
                content=ft.Row([
                    avatar,
                    ft.Column([
                        ft.Text(f"{_saudacao}{nome_display}!", size=13,
                                weight=ft.FontWeight.W_700, color=TXT),
                        ft.Row([
                            ft.Container(width=6, height=6, border_radius=3, bgcolor=VERD),
                            ft.Text("Claudia disponivel", size=10, color=VERD),
                        ], spacing=4, tight=True),
                        ft.Text("Toque para conversar", size=9, color=MUT),
                    ], spacing=2, tight=True, expand=True),
                    ft.Icon("chevron_right_rounded", size=16, color=ROXO),
                ], spacing=10),
                bgcolor=CARD,
                border=ft.border.all(1, ft.Colors.with_opacity(0.20, ROXO)),
                border_radius=12,
                padding=ft.padding.symmetric(horizontal=14, vertical=8),
                ink=True,
            )
            card.on_click = lambda e: _lazy_fn("tela_claudia", "criar_tela_claudia")()
            return card

        # ── Dados do paciente (modo medico) ──────────────────
        pac = {}
        try:
            pac = carregar_perfil() or {}
        except Exception:
            pass

        import os as _os

        nome_pac  = pac.get("nome") or "Paciente"
        nasc      = pac.get("data_nasc") or ""
        sexo      = pac.get("sexo") or ""
        foto      = pac.get("foto_url") or ""
        tipo_sang = pac.get("tipo_sanguineo") or ""
        peso      = pac.get("peso")
        altura    = pac.get("altura")

        try:
            from datetime import date
            nasc_d    = date.fromisoformat(nasc[:10])
            hoje      = date.today()
            anos      = hoje.year - nasc_d.year - (
                (hoje.month, hoje.day) < (nasc_d.month, nasc_d.day))
            idade_str = f"{anos} anos"
            nasc_fmt  = nasc_d.strftime("%d/%m/%Y")
        except Exception:
            idade_str = ""
            nasc_fmt  = nasc

        sexo_label = {"M": "Masculino", "F": "Feminino"}.get(sexo, sexo)
        info_line  = "  •  ".join(p for p in [idade_str, sexo_label, tipo_sang] if p)

        def _mk_avatar(size, font_size, radius):
            if foto and _os.path.isfile(foto):
                return ft.Container(
                    content=ft.Image(src=foto, width=size, height=size,
                                     fit=ft.ImageFit.COVER),
                    width=size, height=size, border_radius=radius,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    border=ft.border.all(2, AZUL),
                )
            initials = "".join(w[0].upper() for w in nome_pac.split()[:2] if w)
            return ft.Container(
                content=ft.Text(initials or "P", size=font_size,
                                weight=ft.FontWeight.W_700, color=AZUL),
                width=size, height=size, border_radius=radius,
                bgcolor=ft.Colors.with_opacity(0.12, AZUL),
                border=ft.border.all(2, ft.Colors.with_opacity(0.40, AZUL)),
                alignment=ft.alignment.Alignment(0, 0),
            )

        def _abrir_overlay_paciente(e=None):
            ov_ref = [None]

            def _fechar(ev=None):
                if ov_ref[0] in page.overlay:
                    page.overlay.remove(ov_ref[0])
                try: page.update()
                except Exception: pass

            def _linha(label, valor, cor_val=TXT):
                if not valor:
                    return ft.Container()
                return ft.Row([
                    ft.Text(label, size=11, color=SEC, width=90),
                    ft.Text(str(valor), size=12, color=cor_val,
                            weight=ft.FontWeight.W_600),
                ], spacing=8)

            peso_txt   = f"{peso} kg" if peso else ""
            altura_txt = f"{altura} m" if altura else ""

            ov_ref[0] = ft.Container(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Icon("close_rounded", size=16, color=SEC),
                                padding=ft.padding.all(4), border_radius=8, ink=True,
                                on_click=_fechar,
                            ),
                        ], alignment=ft.MainAxisAlignment.END),
                        ft.Row([
                            _mk_avatar(72, 24, 36),
                            ft.Text(nome_pac, size=15, color=TXT,
                                    weight=ft.FontWeight.W_700),
                        ], spacing=14),
                        ft.Divider(color=BD, height=16),
                        _linha("Nascimento", nasc_fmt),
                        _linha("Idade",      idade_str),
                        _linha("Sexo",       sexo_label),
                        _linha("Sangue",     tipo_sang, VERM),
                        _linha("Peso",       peso_txt),
                        _linha("Altura",     altura_txt),
                        ft.Container(height=4),
                    ], spacing=6, tight=True),
                    bgcolor=CARD,
                    border_radius=16,
                    padding=ft.padding.all(20),
                    width=min((page.width or 380) - 48, 320),
                ),
                bgcolor=ft.Colors.with_opacity(0.60, "#000000"),
                expand=True,
                alignment=ft.alignment.Alignment(0, 0),
                on_click=_fechar,
            )
            page.overlay.append(ov_ref[0])
            try: page.update()
            except Exception: pass

        card = ft.Container(
            content=ft.Row([
                _mk_avatar(44, 16, 22),
                ft.Column([
                    ft.Text(nome_pac, size=13, weight=ft.FontWeight.W_700,
                            color=TXT, expand=True),
                    ft.Text(info_line, size=10, color=SEC) if info_line
                    else ft.Container(),
                ], spacing=2, expand=True, tight=True),
                ft.Icon("expand_more_rounded", size=16, color=SEC),
            ], spacing=10),
            bgcolor=CARD,
            border=ft.border.all(1, BD),
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            ink=True,
        )
        card.on_click = _abrir_overlay_paciente
        return card

    card_claudia = _card_topo()

    # ══════════════════════════════════════════════════════════
    # MONITOR VITAL
    # ══════════════════════════════════════════════════════════
    txt_score_num = ft.Text("--", size=13, weight=ft.FontWeight.W_700, color=AZUL)
    txt_nota      = ft.Text("--", size=11, color=SEC)
    txt_detalhes  = ft.Text("",   size=10, color=MUT)
    _score_cache  = [{}]

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
            content=ft.Row([
                ft.Icon("arrow_back_rounded", size=14, color=AZUL),
                ft.Text("Voltar", size=12, color=AZUL, weight=ft.FontWeight.W_600),
            ], spacing=4, tight=True),
            ink=True, on_click=_fechar,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

        ref = [None]
        ref[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        btn_fechar,
                        ft.Text("Score de Saude", size=15, color=TXT,
                                weight=ft.FontWeight.W_700, expand=True),
                        ft.Text(f"{d['final']:.0f}", size=28, color=cor,
                                weight=ft.FontWeight.W_900),
                    ], spacing=8),
                    ft.Divider(color=BD, height=1),
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
                    _barra("Compromissos (ultimos 90 dias)",
                           d.get("consultas",0), 10, _COR_CO),
                    ft.Container(height=4),
                    ft.Text("Formula: Exames x60%  +  Adesao x30%  +  Compromissos x10%",
                            size=9, color=MUT, text_align=ft.TextAlign.CENTER),
                ], tight=True),
                bgcolor=CARD, border_radius=14, padding=ft.padding.all(24), width=320,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref[0].on_click = _fechar
        page.overlay.append(ref[0])
        try: page.update()
        except Exception: pass

    # termos: partes ASCII que aparecem no parametro/nome_oficial sem depender de LOWER(acento)
    _UTI_CANAIS = [
        ("Glicemia",      "water_drop_rounded",            "#FF6B6B",
         ["glicose", "glucose", "glicemia", "glicada", "hba1c"]),
        ("Ac.Urico",      "science_rounded",               "#FFD93D",
         ["rico", "urato"]),
        ("Pressao",       "favorite_rounded",              "#4ECDC4",
         ["Total - PAS", "sistolica", "pressao arterial"]),
        ("Bioimpedancia", "accessibility_new_rounded",     "#3FB950",
         ["gordura", "massa magra", "massa muscular", "imc", "bioimpedancia"]),
        ("Vitaminas",     "wb_sunny_rounded",              "#FDCB6E",
         ["vitamina d", "25-oh", "vitamina b12"]),
        ("Inflamacao",    "local_fire_department_rounded", "#FF7675",
         ["pcr", "proteina c reativa", "vhs"]),
        ("Hormonios",     "psychology_alt_rounded",        "#A29BFE",
         ["tsh", "t4 livre", "cortisol"]),
        ("Renal",         "water_drop_rounded",            "#4ECDC4",
         ["creatinina", "ureia", "erfg", "microalbuminuria"]),
    ]

    def _avaliar_status_cor(valor_str, referencia_str):
        try:
            v = float(str(valor_str).replace(",", ".").strip())
            ref = str(referencia_str or "").strip()
            if " - " in ref:
                lo, hi = [float(x) for x in ref.split(" - ", 1)]
                if lo <= v <= hi:   return AZUL
                m1 = (hi - lo) * 0.25
                if (lo - m1) <= v <= (hi + m1): return AMAR
                m2 = (hi - lo) * 0.6
                if (lo - m2) <= v <= (hi + m2): return VERM
                return VERM_INT
            elif ref.startswith("<"):
                lim = float(ref[1:].strip())
                if v < lim:         return AZUL
                if v < lim * 1.25:  return AMAR
                if v < lim * 1.6:   return VERM
                return VERM_INT
            elif ref.startswith(">"):
                lim = float(ref[1:].strip())
                if v > lim:         return AZUL
                if v > lim * 0.8:   return AMAR
                if v > lim * 0.6:   return VERM
                return VERM_INT
        except Exception:
            pass
        return AZUL

    _uti_refs: list = []
    # 2 linhas: 4 canais domésticos na primeira, 3 canais de lab na segunda
    _uti_row1 = ft.Row(spacing=6)
    _uti_row2 = ft.Row(spacing=6)

    def _abrir_grafico_canal(lbl, termos, cor):
        from telas.tela_grafico_marcador import criar_tela_grafico_marcador
        _navegar(lambda p, v: criar_tela_grafico_marcador(p, v, lbl, termos, cor),
                 _voltar_hub)

    def _abrir_glicemia():
        from telas.tela_glicemia import criar_tela_glicemia
        _navegar(criar_tela_glicemia, _voltar_hub)

    def _overlay_glicemia_padrao():
        import sqlite3 as _sqg
        from shared.exame_card import abrir_overlay_exame
        _TERMOS = ["glicose", "glucose", "glicemia", "glicada", "hba1c",
                   "frutosamina", "insulina", "homa"]
        COR = "#FF6B6B"

        def _avaliar_cor_glic(val_str):
            try:
                v = float(str(val_str).replace(",", "."))
                if v < 70 or v > 200: return VERM
                if v > 125:           return AMAR
                if v > 99:            return AMAR
                return VERD
            except Exception:
                return AZUL

        grupos = []
        try:
            conn_g = _sqg.connect(DB_PATH, timeout=30)

            # medicoes domesticas (marcadores_leituras)
            dom_rows = conn_g.execute("""
                SELECT valor, unidade, referencia, data_medicao
                FROM marcadores_leituras
                WHERE """ + " OR ".join([f"LOWER(parametro) LIKE ?" for _ in _TERMOS]) + """
                ORDER BY data_medicao DESC
            """, [f"%{t}%" for t in _TERMOS]).fetchall()

            if dom_rows:
                hist_dom = [{"valor": r[0], "unidade": r[1] or "mg/dL",
                              "referencia": r[2] or "", "data": r[3] or "",
                              "cor_val": _avaliar_cor_glic(r[0])} for r in dom_rows]
                ult = dom_rows[0]
                grupos.append({
                    "label":      "Medicoes Domesticas",
                    "n":          len(dom_rows),
                    "ultimo_val": str(ult[0]),
                    "unidade":    ult[1] or "mg/dL",
                    "ultima_data": ult[3] or "",
                    "referencia": "70 - 99",
                    "cor_val":    _avaliar_cor_glic(ult[0]),
                    "historico":  hist_dom,
                })

            # exames de laboratorio agrupados por parametro
            lab_rows = conn_g.execute("""
                SELECT COALESCE(ep.nome_oficial, r.parametro) AS param,
                       r.valor, r.unidade, r.referencia, e.data_exame
                FROM exame_resultados r
                JOIN exames e ON r.exame_id = e.id
                LEFT JOIN exames_padrao ep ON r.exame_padrao_id = ep.id
                WHERE (""" + " OR ".join([f"LOWER(COALESCE(ep.nome_oficial, r.parametro)) LIKE ?" for _ in _TERMOS]) + """)
                  AND r.valor IS NOT NULL AND r.valor != ''
                ORDER BY param, e.data_exame DESC
            """, [f"%{t}%" for t in _TERMOS]).fetchall()
            conn_g.close()

            _por_param = {}
            for param, val, uni, ref, data in lab_rows:
                key = (param or "").strip().lower()
                if key not in _por_param:
                    _por_param[key] = {"label": (param or "").strip().title(),
                                       "registros": []}
                _por_param[key]["registros"].append(
                    {"valor": val, "unidade": uni or "", "referencia": ref or "",
                     "data": data or "", "cor_val": _avaliar_cor_glic(val)})

            for key, info in _por_param.items():
                regs = info["registros"]
                ult  = regs[0]
                grupos.append({
                    "label":       info["label"],
                    "n":           len(regs),
                    "ultimo_val":  str(ult["valor"]),
                    "unidade":     ult["unidade"] or "mg/dL",
                    "ultima_data": ult["data"],
                    "referencia":  ult["referencia"],
                    "cor_val":     _avaliar_cor_glic(ult["valor"]),
                    "historico":   regs,
                })

        except Exception as ex:
            log.warning("[HUB] overlay_glicemia: %s", ex)

        abrir_overlay_exame(page, "Glicemia", COR, grupos,
                            icone="water_drop_rounded")

    def _abrir_acido_urico():
        from telas.tela_acido_urico import criar_tela_acido_urico
        _navegar(criar_tela_acido_urico, _voltar_hub)

    def _abrir_pressao():
        from telas.tela_pressao import criar_tela_pressao
        _navegar(criar_tela_pressao, _voltar_hub)

    def _abrir_bioimpedancia():
        from telas.tela_bioimpedancia import criar_tela_bioimpedancia
        _navegar(criar_tela_bioimpedancia, _voltar_hub)

    def _abrir_overlay_canal(ref_dict):
        """Overlay ampliado do card UTI — mostra detalhes e botao Abrir tela completa."""
        lbl = ref_dict["lbl"]
        cor = ref_dict["cor"]
        ico = ref_dict.get("ico", "show_chart_rounded")

        val_txt   = ref_dict["val"].value  or "--"
        unit_txt  = ref_dict["unit"].value or ""
        data_txt  = ref_dict["data"].value or ""
        media_txt = ref_dict["media"].value or ""

        _nav_fn_map = {
            "Glicemia":      _abrir_glicemia,
            "Ac.Urico":      _abrir_acido_urico,
            "Pressao":       _abrir_pressao,
            "Bioimpedancia": _abrir_bioimpedancia,
        }

        ov_ref = [None]

        def _fechar(e=None):
            if ov_ref[0] in page.overlay:
                page.overlay.remove(ov_ref[0])
            try: page.update()
            except Exception: pass

        def _abrir_tela(e):
            _fechar()
            fn = _nav_fn_map.get(lbl)
            if fn:
                fn()
            else:
                _abrir_grafico_canal(lbl, ref_dict["termos"], cor)

        btn_fechar = ft.Container(
            content=ft.Icon("close_rounded", size=18, color=SEC),
            padding=ft.padding.all(6), border_radius=8, ink=True,
        )
        btn_fechar.on_click = _fechar

        btn_abrir = ft.Container(
            content=ft.Row([
                ft.Icon("open_in_full_rounded", size=14, color=BG),
                ft.Text("Abrir", size=13, color=BG, weight=ft.FontWeight.W_700),
            ], spacing=5, tight=True),
            bgcolor=cor, border_radius=10, ink=True,
            padding=ft.padding.symmetric(horizontal=18, vertical=10),
        )
        btn_abrir.on_click = _abrir_tela

        linhas_detalhe = [
            ft.Row([
                ft.Text(val_txt, size=48, weight=ft.FontWeight.W_900, color=cor),
                ft.Container(
                    content=ft.Text(unit_txt, size=14, color=SEC),
                    padding=ft.padding.only(top=28),
                ),
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START),
        ]
        if data_txt:
            linhas_detalhe.append(
                ft.Text(data_txt, size=13, color=SEC))
        if media_txt:
            linhas_detalhe.append(
                ft.Row([
                    ft.Text("Media:", size=11, color=MUT),
                    ft.Text(media_txt, size=13, color=SEC, weight=ft.FontWeight.W_600),
                ], spacing=6))

        card_interno = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ico, size=16, color=cor),
                    ft.Text(lbl, size=15, color=cor, weight=ft.FontWeight.W_700,
                            expand=True),
                    btn_fechar,
                ], spacing=8),
                ft.Divider(height=1, color=BD),
                ft.Container(height=4),
                *linhas_detalhe,
                ft.Container(height=8),
                ft.Text("Toque aqui para abrir",
                        size=10, color=ft.Colors.with_opacity(0.45, cor),
                        text_align=ft.TextAlign.CENTER),
                ft.Container(height=4),
            ], tight=True, spacing=6),
            bgcolor=CARD, border_radius=16,
            padding=ft.padding.all(24),
            width=(page.width or 380) - 48,
            border=ft.border.all(1, ft.Colors.with_opacity(0.35, cor)),
            ink=True,
        )
        card_interno.on_click = _abrir_tela

        ov_ref[0] = ft.Container(
            content=card_interno,
            bgcolor="#CC000000", expand=True,
            alignment=ft.Alignment(0, 0),
        )
        ov_ref[0].on_click = _fechar
        page.overlay.append(ov_ref[0])
        try: page.update()
        except Exception: pass

    def _abrir_overlay_vitaminas(cor):
        import sqlite3 as _sqv
        from telas.tela_exames import _gerar_grafico_flet as _graf_vit

        conn_v = _sqv.connect(DB_PATH, timeout=30)
        rows_v = conn_v.execute("""
            SELECT r.parametro, r.valor, r.unidade, r.referencia, e.data_exame
            FROM exame_resultados r
            JOIN exames e ON r.exame_id = e.id
            JOIN exames_padrao ep ON ep.id = r.exame_padrao_id
            WHERE LOWER(ep.categoria) = 'vitaminas'
              AND r.valor IS NOT NULL AND r.valor != ''
            ORDER BY ep.nome_oficial, e.data_exame DESC
        """).fetchall()
        conn_v.close()

        # agrupa por parametro, deduplica sinonimos
        _por_param = {}
        _nome_display = {}
        for param, val, uni, ref_r, data_r in rows_v:
            key = param.strip().lower()
            if key not in _por_param:
                _por_param[key] = []
                _nome_display[key] = param
            _por_param[key].append((val, uni, ref_r, data_r))

        CORES_V = ["#FDCB6E", "#58A6FF", "#3FB950", "#BC8CFF", "#F0883E",
                   "#FF6B6B", "#4ECDC4", "#FF9500"]
        series_v = []
        for i, (key, medidas) in enumerate(sorted(_por_param.items())):
            nome = _nome_display[key]
            hist = [{"valor": v, "unidade": u, "referencia": r, "data": d, "nivel": ""}
                    for v, u, r, d in medidas]
            series_v.append({
                "nome": nome,
                "unidade": medidas[0][1] or "",
                "hist": hist,
                "cor": CORES_V[i % len(CORES_V)],
                "ultimo_val": medidas[0][0],
                "ultima_data": medidas[0][3] or "",
            })

        def _fechar_v(e=None):
            if ref_v[0] in page.overlay:
                page.overlay.remove(ref_v[0])
            try: page.update()
            except Exception: pass

        corpo_v = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

        def _mostrar_detalhe(item):
            """Segundo overlay com grafico + tabela da vitamina selecionada."""
            ref_d = [None]

            def _fechar_d(e=None):
                if ref_d[0] in page.overlay:
                    page.overlay.remove(ref_d[0])
                try: page.update()
                except Exception: pass

            ex_meta = {"nome_oficial": item["nome"], "unidade": item["unidade"]}
            corpo_d = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

            corpo_d.controls.append(ft.Container(
                content=_graf_vit([(ex_meta, item["hist"])]),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=4, vertical=6),
            ))
            for h in item["hist"]:
                corpo_d.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Text(h["data"][:10] if h["data"] else "s/data",
                                size=10, color=MUT, expand=True),
                        ft.Text(f"{h['valor']} {h['unidade'] or ''}",
                                size=13, color=item["cor"],
                                weight=ft.FontWeight.W_700),
                        ft.Text(f"ref: {h['referencia']}" if h["referencia"] else "",
                                size=9, color=MUT),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    border=ft.Border(bottom=ft.BorderSide(1, BD)),
                    padding=ft.padding.symmetric(horizontal=4, vertical=6),
                ))

            btn_vol_d = ft.Container(
                content=ft.Row([
                    ft.Icon("arrow_back_rounded", size=14, color=AZUL),
                    ft.Text("Vitaminas", size=12, color=AZUL,
                            weight=ft.FontWeight.W_600),
                ], spacing=4, tight=True),
                ink=True, on_click=_fechar_d,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            )
            ref_d[0] = ft.Container(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([btn_vol_d,
                                ft.Text(item["nome"], size=14, color=item["cor"],
                                        weight=ft.FontWeight.W_700, expand=True)],
                               spacing=4),
                        ft.Divider(color=BD, height=1),
                        corpo_d,
                    ], spacing=0, expand=True),
                    bgcolor=BG, border_radius=16,
                    padding=ft.padding.symmetric(horizontal=16, vertical=16),
                    width=min(page.width * 0.92, 480) if page.width else 400,
                    height=min(page.height * 0.88, 680) if page.height else 580,
                ),
                bgcolor=ft.Colors.with_opacity(0.55, "#000000"),
                alignment=ft.alignment.Alignment(0, 0),
                expand=True,
            )
            ref_d[0].on_click = _fechar_d
            page.overlay.append(ref_d[0])
            try: page.update()
            except Exception: pass

        # lista de vitaminas
        if series_v:
            for item in series_v:
                row_item = ft.Container(
                    content=ft.Row([
                        ft.Container(width=4, height=36, bgcolor=item["cor"],
                                     border_radius=2),
                        ft.Column([
                            ft.Text(item["nome"], size=13, color=TXT,
                                    weight=ft.FontWeight.W_600),
                            ft.Text(f"{item['ultima_data'][:10]}",
                                    size=10, color=MUT),
                        ], spacing=2, expand=True),
                        ft.Text(f"{item['ultimo_val']} {item['unidade']}",
                                size=13, color=item["cor"],
                                weight=ft.FontWeight.W_700),
                        ft.Icon("chevron_right_rounded", size=16, color=MUT),
                    ], spacing=10,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD,
                    border=ft.Border(bottom=ft.BorderSide(1, BD)),
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    ink=True,
                )
                row_item.on_click = lambda e, _it=item: _mostrar_detalhe(_it)
                corpo_v.controls.append(row_item)
        else:
            corpo_v.controls.append(
                ft.Container(
                    content=ft.Text("Nenhuma vitamina registrada", size=12, color=MUT),
                    padding=ft.padding.symmetric(vertical=20),
                    alignment=ft.alignment.Alignment(0, 0),
                )
            )

        btn_vol_v = ft.Container(
            content=ft.Row([
                ft.Icon("arrow_back_rounded", size=14, color=AZUL),
                ft.Text("Voltar", size=12, color=AZUL,
                        weight=ft.FontWeight.W_600),
            ], spacing=4, tight=True),
            ink=True, on_click=_fechar_v,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

        ref_v = [None]
        ref_v[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([btn_vol_v,
                            ft.Text("Vitaminas", size=14, color=TXT,
                                    weight=ft.FontWeight.W_700, expand=True)],
                           spacing=4),
                    ft.Divider(color=BD, height=1),
                    corpo_v,
                ], spacing=0, expand=True),
                bgcolor=BG, border_radius=16,
                padding=ft.padding.symmetric(horizontal=16, vertical=16),
                width=min(page.width * 0.92, 480) if page.width else 400,
                height=min(page.height * 0.88, 680) if page.height else 580,
            ),
            bgcolor=ft.Colors.with_opacity(0.55, "#000000"),
            alignment=ft.alignment.Alignment(0, 0),
            expand=True,
        )
        ref_v[0].on_click = _fechar_v
        page.overlay.append(ref_v[0])
        try: page.update()
        except Exception: pass

    def _abrir_overlay_inflamacao(cor):
        import sqlite3 as _sqi
        from telas.tela_exames import _gerar_grafico_flet as _graf_inf

        conn_i = _sqi.connect(DB_PATH, timeout=30)
        rows_i = conn_i.execute("""
            SELECT r.parametro, r.valor, r.unidade, r.referencia, e.data_exame
            FROM exame_resultados r
            JOIN exames e ON r.exame_id = e.id
            JOIN exames_padrao ep ON ep.id = r.exame_padrao_id
            WHERE (LOWER(ep.categoria) IN ('inflamacao','inflamação','imunologia','imunidade')
                   OR LOWER(r.parametro) LIKE '%pcr%'
                   OR LOWER(r.parametro) LIKE '%proteina c reativa%'
                   OR LOWER(r.parametro) LIKE '%vhs%'
                   OR LOWER(r.parametro) LIKE '%fator reumatoide%'
                   OR LOWER(r.parametro) LIKE '%fan%'
                   OR LOWER(r.parametro) LIKE '%anti-transglutaminase%')
              AND r.valor IS NOT NULL AND r.valor != ''
            ORDER BY ep.nome_oficial, e.data_exame DESC
        """).fetchall()
        conn_i.close()

        _por_param = {}
        _nome_display = {}
        for param, val, uni, ref_r, data_r in rows_i:
            key = param.strip().lower()
            if key not in _por_param:
                _por_param[key] = []
                _nome_display[key] = param
            _por_param[key].append((val, uni, ref_r, data_r))

        CORES_I = ["#FF7675", "#FF6B6B", "#FDCB6E", "#58A6FF",
                   "#3FB950", "#BC8CFF", "#F0883E", "#4ECDC4"]
        series_i = []
        for i, (key, medidas) in enumerate(sorted(_por_param.items())):
            nome = _nome_display[key]
            hist = [{"valor": v, "unidade": u, "referencia": r, "data": d, "nivel": ""}
                    for v, u, r, d in medidas]
            series_i.append({
                "nome": nome,
                "unidade": medidas[0][1] or "",
                "hist": hist,
                "cor": CORES_I[i % len(CORES_I)],
                "ultimo_val": medidas[0][0],
                "ultima_data": medidas[0][3] or "",
            })

        def _fechar_i(e=None):
            if ref_i[0] in page.overlay:
                page.overlay.remove(ref_i[0])
            try: page.update()
            except Exception: pass

        corpo_i = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

        def _mostrar_detalhe_i(item):
            ref_d = [None]

            def _fechar_d(e=None):
                if ref_d[0] in page.overlay:
                    page.overlay.remove(ref_d[0])
                try: page.update()
                except Exception: pass

            ex_meta = {"nome_oficial": item["nome"], "unidade": item["unidade"]}
            corpo_d = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
            corpo_d.controls.append(ft.Container(
                content=_graf_inf([(ex_meta, item["hist"])]),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=4, vertical=6),
            ))
            for h in item["hist"]:
                corpo_d.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Text(h["data"][:10] if h["data"] else "s/data",
                                size=10, color=MUT, expand=True),
                        ft.Text(f"{h['valor']} {h['unidade'] or ''}",
                                size=13, color=item["cor"],
                                weight=ft.FontWeight.W_700),
                        ft.Text(f"ref: {h['referencia']}" if h["referencia"] else "",
                                size=9, color=MUT),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    border=ft.Border(bottom=ft.BorderSide(1, BD)),
                    padding=ft.padding.symmetric(horizontal=4, vertical=6),
                ))

            btn_vol_d = ft.Container(
                content=ft.Row([
                    ft.Icon("arrow_back_rounded", size=14, color=AZUL),
                    ft.Text("Inflamacao", size=12, color=AZUL,
                            weight=ft.FontWeight.W_600),
                ], spacing=4, tight=True),
                ink=True, on_click=_fechar_d,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            )
            ref_d[0] = ft.Container(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([btn_vol_d,
                                ft.Text(item["nome"], size=14, color=item["cor"],
                                        weight=ft.FontWeight.W_700, expand=True)],
                               spacing=4),
                        ft.Divider(color=BD, height=1),
                        corpo_d,
                    ], spacing=0, expand=True),
                    bgcolor=BG, border_radius=16,
                    padding=ft.padding.symmetric(horizontal=16, vertical=16),
                    width=min(page.width * 0.92, 480) if page.width else 400,
                    height=min(page.height * 0.88, 680) if page.height else 580,
                ),
                bgcolor=ft.Colors.with_opacity(0.55, "#000000"),
                alignment=ft.alignment.Alignment(0, 0),
                expand=True,
            )
            ref_d[0].on_click = _fechar_d
            page.overlay.append(ref_d[0])
            try: page.update()
            except Exception: pass

        if series_i:
            for item in series_i:
                row_item = ft.Container(
                    content=ft.Row([
                        ft.Container(width=4, height=36, bgcolor=item["cor"],
                                     border_radius=2),
                        ft.Column([
                            ft.Text(item["nome"], size=13, color=TXT,
                                    weight=ft.FontWeight.W_600),
                            ft.Text(item["ultima_data"][:10], size=10, color=MUT),
                        ], spacing=2, expand=True),
                        ft.Text(f"{item['ultimo_val']} {item['unidade']}",
                                size=13, color=item["cor"],
                                weight=ft.FontWeight.W_700),
                        ft.Icon("chevron_right_rounded", size=16, color=MUT),
                    ], spacing=10,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD,
                    border=ft.Border(bottom=ft.BorderSide(1, BD)),
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    ink=True,
                )
                row_item.on_click = lambda e, _it=item: _mostrar_detalhe_i(_it)
                corpo_i.controls.append(row_item)
        else:
            corpo_i.controls.append(ft.Container(
                content=ft.Text("Nenhum marcador de inflamacao registrado",
                                size=12, color=MUT),
                padding=ft.padding.symmetric(vertical=20),
                alignment=ft.alignment.Alignment(0, 0),
            ))

        btn_vol_i = ft.Container(
            content=ft.Row([
                ft.Icon("arrow_back_rounded", size=14, color=AZUL),
                ft.Text("Voltar", size=12, color=AZUL, weight=ft.FontWeight.W_600),
            ], spacing=4, tight=True),
            ink=True, on_click=_fechar_i,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

        ref_i = [None]
        ref_i[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([btn_vol_i,
                            ft.Text("Inflamacao", size=14, color=TXT,
                                    weight=ft.FontWeight.W_700, expand=True)],
                           spacing=4),
                    ft.Divider(color=BD, height=1),
                    corpo_i,
                ], spacing=0, expand=True),
                bgcolor=BG, border_radius=16,
                padding=ft.padding.symmetric(horizontal=16, vertical=16),
                width=min(page.width * 0.92, 480) if page.width else 400,
                height=min(page.height * 0.88, 680) if page.height else 580,
            ),
            bgcolor=ft.Colors.with_opacity(0.55, "#000000"),
            alignment=ft.alignment.Alignment(0, 0),
            expand=True,
        )
        ref_i[0].on_click = _fechar_i
        page.overlay.append(ref_i[0])
        try: page.update()
        except Exception: pass

    def _abrir_overlay_hormonios(cor):
        import sqlite3 as _sqh
        from telas.tela_exames import _gerar_grafico_flet as _graf_hor

        conn_h = _sqh.connect(DB_PATH, timeout=30)
        rows_h = conn_h.execute("""
            SELECT r.parametro, r.valor, r.unidade, r.referencia, e.data_exame
            FROM exame_resultados r
            JOIN exames e ON r.exame_id = e.id
            JOIN exames_padrao ep ON ep.id = r.exame_padrao_id
            WHERE LOWER(ep.categoria) IN ('hormonios','hormônios','hormônio','hormonio')
              AND r.valor IS NOT NULL AND r.valor != ''
            ORDER BY ep.nome_oficial, e.data_exame DESC
        """).fetchall()
        conn_h.close()

        _por_param = {}
        _nome_display = {}
        for param, val, uni, ref_r, data_r in rows_h:
            key = param.strip().lower()
            if key not in _por_param:
                _por_param[key] = []
                _nome_display[key] = param
            _por_param[key].append((val, uni, ref_r, data_r))

        CORES_H = ["#A29BFE", "#BC8CFF", "#FF9500", "#58A6FF",
                   "#3FB950", "#FDCB6E", "#FF6B6B", "#4ECDC4"]
        series_h = []
        for i, (key, medidas) in enumerate(sorted(_por_param.items())):
            nome = _nome_display[key]
            hist = [{"valor": v, "unidade": u, "referencia": r, "data": d, "nivel": ""}
                    for v, u, r, d in medidas]
            series_h.append({
                "nome": nome,
                "unidade": medidas[0][1] or "",
                "hist": hist,
                "cor": CORES_H[i % len(CORES_H)],
                "ultimo_val": medidas[0][0],
                "ultima_data": medidas[0][3] or "",
            })

        def _fechar_h(e=None):
            if ref_h[0] in page.overlay:
                page.overlay.remove(ref_h[0])
            try: page.update()
            except Exception: pass

        corpo_h = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

        def _mostrar_detalhe_h(item):
            ref_d = [None]

            def _fechar_d(e=None):
                if ref_d[0] in page.overlay:
                    page.overlay.remove(ref_d[0])
                try: page.update()
                except Exception: pass

            ex_meta = {"nome_oficial": item["nome"], "unidade": item["unidade"]}
            corpo_d = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
            corpo_d.controls.append(ft.Container(
                content=_graf_hor([(ex_meta, item["hist"])]),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=4, vertical=6),
            ))
            for h in item["hist"]:
                corpo_d.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Text(h["data"][:10] if h["data"] else "s/data",
                                size=10, color=MUT, expand=True),
                        ft.Text(f"{h['valor']} {h['unidade'] or ''}",
                                size=13, color=item["cor"],
                                weight=ft.FontWeight.W_700),
                        ft.Text(f"ref: {h['referencia']}" if h["referencia"] else "",
                                size=9, color=MUT),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    border=ft.Border(bottom=ft.BorderSide(1, BD)),
                    padding=ft.padding.symmetric(horizontal=4, vertical=6),
                ))

            btn_vol_d = ft.Container(
                content=ft.Row([
                    ft.Icon("arrow_back_rounded", size=14, color=AZUL),
                    ft.Text("Hormonios", size=12, color=AZUL,
                            weight=ft.FontWeight.W_600),
                ], spacing=4, tight=True),
                ink=True, on_click=_fechar_d,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            )
            ref_d[0] = ft.Container(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([btn_vol_d,
                                ft.Text(item["nome"], size=14, color=item["cor"],
                                        weight=ft.FontWeight.W_700, expand=True)],
                               spacing=4),
                        ft.Divider(color=BD, height=1),
                        corpo_d,
                    ], spacing=0, expand=True),
                    bgcolor=BG, border_radius=16,
                    padding=ft.padding.symmetric(horizontal=16, vertical=16),
                    width=min(page.width * 0.92, 480) if page.width else 400,
                    height=min(page.height * 0.88, 680) if page.height else 580,
                ),
                bgcolor=ft.Colors.with_opacity(0.55, "#000000"),
                alignment=ft.alignment.Alignment(0, 0),
                expand=True,
            )
            ref_d[0].on_click = _fechar_d
            page.overlay.append(ref_d[0])
            try: page.update()
            except Exception: pass

        if series_h:
            for item in series_h:
                row_item = ft.Container(
                    content=ft.Row([
                        ft.Container(width=4, height=36, bgcolor=item["cor"],
                                     border_radius=2),
                        ft.Column([
                            ft.Text(item["nome"], size=13, color=TXT,
                                    weight=ft.FontWeight.W_600),
                            ft.Text(item["ultima_data"][:10], size=10, color=MUT),
                        ], spacing=2, expand=True),
                        ft.Text(f"{item['ultimo_val']} {item['unidade']}",
                                size=13, color=item["cor"],
                                weight=ft.FontWeight.W_700),
                        ft.Icon("chevron_right_rounded", size=16, color=MUT),
                    ], spacing=10,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD,
                    border=ft.Border(bottom=ft.BorderSide(1, BD)),
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    ink=True,
                )
                row_item.on_click = lambda e, _it=item: _mostrar_detalhe_h(_it)
                corpo_h.controls.append(row_item)
        else:
            corpo_h.controls.append(ft.Container(
                content=ft.Text("Nenhum hormonio registrado", size=12, color=MUT),
                padding=ft.padding.symmetric(vertical=20),
                alignment=ft.alignment.Alignment(0, 0),
            ))

        btn_vol_h = ft.Container(
            content=ft.Row([
                ft.Icon("arrow_back_rounded", size=14, color=AZUL),
                ft.Text("Voltar", size=12, color=AZUL, weight=ft.FontWeight.W_600),
            ], spacing=4, tight=True),
            ink=True, on_click=_fechar_h,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

        ref_h = [None]
        ref_h[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([btn_vol_h,
                            ft.Text("Hormonios", size=14, color=TXT,
                                    weight=ft.FontWeight.W_700, expand=True)],
                           spacing=4),
                    ft.Divider(color=BD, height=1),
                    corpo_h,
                ], spacing=0, expand=True),
                bgcolor=BG, border_radius=16,
                padding=ft.padding.symmetric(horizontal=16, vertical=16),
                width=min(page.width * 0.92, 480) if page.width else 400,
                height=min(page.height * 0.88, 680) if page.height else 580,
            ),
            bgcolor=ft.Colors.with_opacity(0.55, "#000000"),
            alignment=ft.alignment.Alignment(0, 0),
            expand=True,
        )
        ref_h[0].on_click = _fechar_h
        page.overlay.append(ref_h[0])
        try: page.update()
        except Exception: pass

    def _abrir_overlay_renal(cor):
        import sqlite3 as _sqr
        from telas.tela_exames import _gerar_grafico_flet as _graf_ren

        conn_r = _sqr.connect(DB_PATH, timeout=30)
        rows_r = conn_r.execute("""
            SELECT r.parametro, r.valor, r.unidade, r.referencia, e.data_exame
            FROM exame_resultados r
            JOIN exames e ON r.exame_id = e.id
            JOIN exames_padrao ep ON ep.id = r.exame_padrao_id
            WHERE LOWER(ep.categoria) IN ('funcao renal','função renal','proteinas','proteínas')
               OR LOWER(r.parametro) LIKE '%microalbuminu%'
               OR LOWER(r.parametro) LIKE '%psa%'
            AND r.valor IS NOT NULL AND r.valor != ''
            ORDER BY ep.nome_oficial, e.data_exame DESC
        """).fetchall()
        conn_r.close()

        _por_param = {}
        _nome_display = {}
        for param, val, uni, ref_r, data_r in rows_r:
            key = param.strip().lower()
            if key not in _por_param:
                _por_param[key] = []
                _nome_display[key] = param
            _por_param[key].append((val, uni, ref_r, data_r))

        CORES_R = ["#4ECDC4", "#58A6FF", "#3FB950", "#FDCB6E",
                   "#BC8CFF", "#F0883E", "#FF6B6B", "#A29BFE"]
        series_r = []
        for i, (key, medidas) in enumerate(sorted(_por_param.items())):
            nome = _nome_display[key]
            hist = [{"valor": v, "unidade": u, "referencia": r, "data": d, "nivel": ""}
                    for v, u, r, d in medidas]
            series_r.append({
                "nome": nome,
                "unidade": medidas[0][1] or "",
                "hist": hist,
                "cor": CORES_R[i % len(CORES_R)],
                "ultimo_val": medidas[0][0],
                "ultima_data": medidas[0][3] or "",
            })

        def _fechar_r(e=None):
            if ref_r[0] in page.overlay:
                page.overlay.remove(ref_r[0])
            try: page.update()
            except Exception: pass

        corpo_r = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

        def _mostrar_detalhe_r(item):
            ref_d = [None]

            def _fechar_d(e=None):
                if ref_d[0] in page.overlay:
                    page.overlay.remove(ref_d[0])
                try: page.update()
                except Exception: pass

            ex_meta = {"nome_oficial": item["nome"], "unidade": item["unidade"]}
            corpo_d = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
            corpo_d.controls.append(ft.Container(
                content=_graf_ren([(ex_meta, item["hist"])]),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=4, vertical=6),
            ))
            for h in item["hist"]:
                corpo_d.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Text(h["data"][:10] if h["data"] else "s/data",
                                size=10, color=MUT, expand=True),
                        ft.Text(f"{h['valor']} {h['unidade'] or ''}",
                                size=13, color=item["cor"],
                                weight=ft.FontWeight.W_700),
                        ft.Text(f"ref: {h['referencia']}" if h["referencia"] else "",
                                size=9, color=MUT),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    border=ft.Border(bottom=ft.BorderSide(1, BD)),
                    padding=ft.padding.symmetric(horizontal=4, vertical=6),
                ))

            btn_vol_d = ft.Container(
                content=ft.Row([
                    ft.Icon("arrow_back_rounded", size=14, color=AZUL),
                    ft.Text("Renal", size=12, color=AZUL, weight=ft.FontWeight.W_600),
                ], spacing=4, tight=True),
                ink=True, on_click=_fechar_d,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            )
            ref_d[0] = ft.Container(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([btn_vol_d,
                                ft.Text(item["nome"], size=14, color=item["cor"],
                                        weight=ft.FontWeight.W_700, expand=True)],
                               spacing=4),
                        ft.Divider(color=BD, height=1),
                        corpo_d,
                    ], spacing=0, expand=True),
                    bgcolor=BG, border_radius=16,
                    padding=ft.padding.symmetric(horizontal=16, vertical=16),
                    width=min(page.width * 0.92, 480) if page.width else 400,
                    height=min(page.height * 0.88, 680) if page.height else 580,
                ),
                bgcolor=ft.Colors.with_opacity(0.55, "#000000"),
                alignment=ft.alignment.Alignment(0, 0),
                expand=True,
            )
            ref_d[0].on_click = _fechar_d
            page.overlay.append(ref_d[0])
            try: page.update()
            except Exception: pass

        if series_r:
            for item in series_r:
                row_item = ft.Container(
                    content=ft.Row([
                        ft.Container(width=4, height=36, bgcolor=item["cor"],
                                     border_radius=2),
                        ft.Column([
                            ft.Text(item["nome"], size=13, color=TXT,
                                    weight=ft.FontWeight.W_600),
                            ft.Text(item["ultima_data"][:10], size=10, color=MUT),
                        ], spacing=2, expand=True),
                        ft.Text(f"{item['ultimo_val']} {item['unidade']}",
                                size=13, color=item["cor"],
                                weight=ft.FontWeight.W_700),
                        ft.Icon("chevron_right_rounded", size=16, color=MUT),
                    ], spacing=10,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD,
                    border=ft.Border(bottom=ft.BorderSide(1, BD)),
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    ink=True,
                )
                row_item.on_click = lambda e, _it=item: _mostrar_detalhe_r(_it)
                corpo_r.controls.append(row_item)
        else:
            corpo_r.controls.append(ft.Container(
                content=ft.Text("Nenhum exame renal registrado", size=12, color=MUT),
                padding=ft.padding.symmetric(vertical=20),
                alignment=ft.alignment.Alignment(0, 0),
            ))

        btn_vol_r = ft.Container(
            content=ft.Row([
                ft.Icon("arrow_back_rounded", size=14, color=AZUL),
                ft.Text("Voltar", size=12, color=AZUL, weight=ft.FontWeight.W_600),
            ], spacing=4, tight=True),
            ink=True, on_click=_fechar_r,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

        ref_r = [None]
        ref_r[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([btn_vol_r,
                            ft.Text("Funcao Renal", size=14, color=TXT,
                                    weight=ft.FontWeight.W_700, expand=True)],
                           spacing=4),
                    ft.Divider(color=BD, height=1),
                    corpo_r,
                ], spacing=0, expand=True),
                bgcolor=BG, border_radius=16,
                padding=ft.padding.symmetric(horizontal=16, vertical=16),
                width=min(page.width * 0.92, 480) if page.width else 400,
                height=min(page.height * 0.88, 680) if page.height else 580,
            ),
            bgcolor=ft.Colors.with_opacity(0.55, "#000000"),
            alignment=ft.alignment.Alignment(0, 0),
            expand=True,
        )
        ref_r[0].on_click = _fechar_r
        page.overlay.append(ref_r[0])
        try: page.update()
        except Exception: pass

    def _mk_click_uti(lbl, termos, cor):
        def _h(e, _lbl=lbl, _termos=termos, _cor=cor):
            if _lbl == "Glicemia":
                _abrir_glicemia()
                return
            if _lbl == "Vitaminas":
                ref_vit = next((r for r in _uti_refs if r["lbl"] == "Vitaminas"), None)
                _score_txt = ref_vit["val"].value  if ref_vit else "--"
                _sub_txt   = ref_vit["data"].value if ref_vit else ""
                _cor_score = ref_vit["val"].color  if ref_vit else _cor
                ov_vit = [None]

                def _fechar_vit(e=None):
                    if ov_vit[0] in page.overlay:
                        page.overlay.remove(ov_vit[0])
                    try: page.update()
                    except Exception: pass

                def _abrir_lista(e):
                    _fechar_vit()
                    _abrir_overlay_vitaminas(_cor)

                btn_f = ft.Container(
                    content=ft.Icon("close_rounded", size=18, color=SEC),
                    padding=ft.padding.all(6), border_radius=8, ink=True,
                )
                btn_f.on_click = _fechar_vit

                card_vit = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon("wb_sunny_rounded", size=16, color=_cor_score),
                            ft.Text("Vitaminas", size=15, color=_cor_score,
                                    weight=ft.FontWeight.W_700, expand=True),
                            btn_f,
                        ], spacing=8),
                        ft.Divider(height=1, color=BD),
                        ft.Container(height=4),
                        ft.Row([
                            ft.Text(_score_txt, size=48, weight=ft.FontWeight.W_900,
                                    color=_cor_score),
                            ft.Container(
                                content=ft.Text("%", size=14, color=SEC),
                                padding=ft.padding.only(top=28),
                            ),
                        ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START),
                        ft.Text(_sub_txt, size=13, color=SEC),
                        ft.Container(height=8),
                        ft.Text("Toque aqui para ver a lista",
                                size=10,
                                color=ft.Colors.with_opacity(0.45, _cor_score),
                                text_align=ft.TextAlign.CENTER),
                        ft.Container(height=4),
                    ], tight=True, spacing=6),
                    bgcolor=CARD, border_radius=16,
                    padding=ft.padding.all(24),
                    width=(page.width or 380) - 48,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.35, _cor_score)),
                    ink=True,
                )
                card_vit.on_click = _abrir_lista

                ov_vit[0] = ft.Container(
                    content=card_vit,
                    bgcolor="#CC000000", expand=True,
                    alignment=ft.Alignment(0, 0),
                )
                ov_vit[0].on_click = _fechar_vit
                page.overlay.append(ov_vit[0])
                try: page.update()
                except Exception: pass
                return
            if _lbl == "Inflamacao":
                ref_inf = next((r for r in _uti_refs if r["lbl"] == "Inflamacao"), None)
                _score_txt = ref_inf["val"].value  if ref_inf else "--"
                _sub_txt   = ref_inf["data"].value if ref_inf else ""
                _cor_score = ref_inf["val"].color  if ref_inf else _cor
                ov_inf = [None]

                def _fechar_inf(e=None):
                    if ov_inf[0] in page.overlay:
                        page.overlay.remove(ov_inf[0])
                    try: page.update()
                    except Exception: pass

                def _abrir_lista_inf(e):
                    _fechar_inf()
                    _abrir_overlay_inflamacao(_cor)

                btn_f_i = ft.Container(
                    content=ft.Icon("close_rounded", size=18, color=SEC),
                    padding=ft.padding.all(6), border_radius=8, ink=True,
                )
                btn_f_i.on_click = _fechar_inf

                card_inf = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon("local_fire_department_rounded", size=16, color=_cor_score),
                            ft.Text("Inflamacao", size=15, color=_cor_score,
                                    weight=ft.FontWeight.W_700, expand=True),
                            btn_f_i,
                        ], spacing=8),
                        ft.Divider(height=1, color=BD),
                        ft.Container(height=4),
                        ft.Row([
                            ft.Text(_score_txt, size=48, weight=ft.FontWeight.W_900,
                                    color=_cor_score),
                            ft.Container(
                                content=ft.Text("/10", size=14, color=SEC),
                                padding=ft.padding.only(top=28),
                            ),
                        ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START),
                        ft.Text(_sub_txt, size=13, color=SEC),
                        ft.Container(height=8),
                        ft.Text("Toque aqui para ver a lista",
                                size=10,
                                color=ft.Colors.with_opacity(0.45, _cor_score),
                                text_align=ft.TextAlign.CENTER),
                        ft.Container(height=4),
                    ], tight=True, spacing=6),
                    bgcolor=CARD, border_radius=16,
                    padding=ft.padding.all(24),
                    width=(page.width or 380) - 48,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.35, _cor_score)),
                    ink=True,
                )
                card_inf.on_click = _abrir_lista_inf

                ov_inf[0] = ft.Container(
                    content=card_inf,
                    bgcolor="#CC000000", expand=True,
                    alignment=ft.Alignment(0, 0),
                )
                ov_inf[0].on_click = _fechar_inf
                page.overlay.append(ov_inf[0])
                try: page.update()
                except Exception: pass
                return
            if _lbl == "Hormonios":
                ref_hor = next((r for r in _uti_refs if r["lbl"] == "Hormonios"), None)
                _score_txt = ref_hor["val"].value  if ref_hor else "--"
                _sub_txt   = ref_hor["data"].value if ref_hor else ""
                _cor_score = ref_hor["val"].color  if ref_hor else _cor
                ov_hor = [None]

                def _fechar_hor(e=None):
                    if ov_hor[0] in page.overlay:
                        page.overlay.remove(ov_hor[0])
                    try: page.update()
                    except Exception: pass

                def _abrir_lista_hor(e):
                    _fechar_hor()
                    _abrir_overlay_hormonios(_cor)

                btn_f_h = ft.Container(
                    content=ft.Icon("close_rounded", size=18, color=SEC),
                    padding=ft.padding.all(6), border_radius=8, ink=True,
                )
                btn_f_h.on_click = _fechar_hor

                card_hor = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon("psychology_alt_rounded", size=16, color=_cor_score),
                            ft.Text("Hormonios", size=15, color=_cor_score,
                                    weight=ft.FontWeight.W_700, expand=True),
                            btn_f_h,
                        ], spacing=8),
                        ft.Divider(height=1, color=BD),
                        ft.Container(height=4),
                        ft.Row([
                            ft.Text(_score_txt, size=48, weight=ft.FontWeight.W_900,
                                    color=_cor_score),
                            ft.Container(
                                content=ft.Text("/10", size=14, color=SEC),
                                padding=ft.padding.only(top=28),
                            ),
                        ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START),
                        ft.Text(_sub_txt, size=13, color=SEC),
                        ft.Container(height=8),
                        ft.Text("Toque aqui para ver a lista",
                                size=10,
                                color=ft.Colors.with_opacity(0.45, _cor_score),
                                text_align=ft.TextAlign.CENTER),
                        ft.Container(height=4),
                    ], tight=True, spacing=6),
                    bgcolor=CARD, border_radius=16,
                    padding=ft.padding.all(24),
                    width=(page.width or 380) - 48,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.35, _cor_score)),
                    ink=True,
                )
                card_hor.on_click = _abrir_lista_hor

                ov_hor[0] = ft.Container(
                    content=card_hor,
                    bgcolor="#CC000000", expand=True,
                    alignment=ft.Alignment(0, 0),
                )
                ov_hor[0].on_click = _fechar_hor
                page.overlay.append(ov_hor[0])
                try: page.update()
                except Exception: pass
                return
            if _lbl == "Renal":
                ref_ren = next((r for r in _uti_refs if r["lbl"] == "Renal"), None)
                _score_txt = ref_ren["val"].value  if ref_ren else "--"
                _sub_txt   = ref_ren["data"].value if ref_ren else ""
                _cor_score = ref_ren["val"].color  if ref_ren else _cor
                ov_ren = [None]

                def _fechar_ren(e=None):
                    if ov_ren[0] in page.overlay:
                        page.overlay.remove(ov_ren[0])
                    try: page.update()
                    except Exception: pass

                def _abrir_lista_ren(e):
                    _fechar_ren()
                    _abrir_overlay_renal(_cor)

                btn_f_r = ft.Container(
                    content=ft.Icon("close_rounded", size=18, color=SEC),
                    padding=ft.padding.all(6), border_radius=8, ink=True,
                )
                btn_f_r.on_click = _fechar_ren

                card_ren = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon("water_drop_rounded", size=16, color=_cor_score),
                            ft.Text("Funcao Renal", size=15, color=_cor_score,
                                    weight=ft.FontWeight.W_700, expand=True),
                            btn_f_r,
                        ], spacing=8),
                        ft.Divider(height=1, color=BD),
                        ft.Container(height=4),
                        ft.Row([
                            ft.Text(_score_txt, size=48, weight=ft.FontWeight.W_900,
                                    color=_cor_score),
                            ft.Container(
                                content=ft.Text("/10", size=14, color=SEC),
                                padding=ft.padding.only(top=28),
                            ),
                        ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START),
                        ft.Text(_sub_txt, size=13, color=SEC),
                        ft.Container(height=8),
                        ft.Text("Toque aqui para ver a lista",
                                size=10,
                                color=ft.Colors.with_opacity(0.45, _cor_score),
                                text_align=ft.TextAlign.CENTER),
                        ft.Container(height=4),
                    ], tight=True, spacing=6),
                    bgcolor=CARD, border_radius=16,
                    padding=ft.padding.all(24),
                    width=(page.width or 380) - 48,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.35, _cor_score)),
                    ink=True,
                )
                card_ren.on_click = _abrir_lista_ren

                ov_ren[0] = ft.Container(
                    content=card_ren,
                    bgcolor="#CC000000", expand=True,
                    alignment=ft.Alignment(0, 0),
                )
                ov_ren[0].on_click = _fechar_ren
                page.overlay.append(ov_ren[0])
                try: page.update()
                except Exception: pass
                return
            ref = next((r for r in _uti_refs if r["lbl"] == _lbl), None)
            if ref:
                _abrir_overlay_canal(ref)
        return _h

    _CANAIS_DOMESTICOS = {"Glicemia", "Ac.Urico", "Pressao", "Bioimpedancia"}
    for _idx, (_lbl, _ico, _cor, _termos) in enumerate(_UTI_CANAIS):
        _eh_bio = (_lbl == "Bioimpedancia")
        _tv  = ft.Text("--", size=16 if _eh_bio else 14, weight=ft.FontWeight.W_900,
                       color=_cor, text_align=ft.TextAlign.CENTER)
        _tu  = ft.Text("",   size=8,  color=SEC, text_align=ft.TextAlign.CENTER)
        _td  = ft.Text("",   size=8,  color=MUT, text_align=ft.TextAlign.CENTER)
        _tm  = ft.Text("",   size=8,  color=MUT, text_align=ft.TextAlign.CENTER)
        _dot = ft.Container(width=6, height=6, border_radius=3, bgcolor=MUT)
        _card_uti = ft.Container(
            content=ft.Column([
                ft.Row([_dot], alignment=ft.MainAxisAlignment.CENTER),
                ft.Icon(_ico, size=12, color=ft.Colors.with_opacity(0.60, _cor)),
                ft.Text(_lbl, size=8, color=SEC,
                        text_align=ft.TextAlign.CENTER,
                        weight=ft.FontWeight.W_600),
                ft.Container(height=2),
                _tv, _tu, _td,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               spacing=1, tight=True),
            bgcolor="#080C11",
            border=ft.border.all(1, ft.Colors.with_opacity(0.20, _cor)),
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=6, vertical=8),
            expand=True, ink=True,
        )
        _card_uti.on_click = _mk_click_uti(_lbl, _termos, _cor)
        _uti_refs.append({
            "val": _tv, "unit": _tu, "data": _td, "media": _tm,
            "dot": _dot, "card": _card_uti, "cor": _cor,
            "termos": _termos, "lbl": _lbl, "ico": _ico,
        })
        if _idx < 4:
            _uti_row1.controls.append(_card_uti)
        else:
            _uti_row2.controls.append(_card_uti)

    _btn_marc = ft.Container(
        content=ft.Row([
            ft.Icon("bar_chart_rounded", size=12, color=AZUL),
            ft.Text("Gerenciar", size=10, color=AZUL),
        ], spacing=3, tight=True),
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        border_radius=8, bgcolor=ft.Colors.with_opacity(0.10, AZUL), ink=True,
    )
    _btn_marc.on_click = lambda e: _lazy_fn("tela_marcadores", "criar_tela_marcadores")()

    _row_score = ft.Container(
        content=ft.Row([
            ft.Text("Score", size=10, color=MUT),
            txt_score_num, txt_nota,
            ft.Icon("info_outline_rounded", size=11, color=MUT),
        ], spacing=4, tight=True),
        border_radius=8, ink=True,
        padding=ft.padding.symmetric(horizontal=4, vertical=2),
    )
    _row_score.on_click = _mostrar_score_breakdown

    card_monitor_uti = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon("monitor_heart_rounded", size=12, color="#FF7675"),
                ft.Text("MONITOR VITAL", size=9,
                        weight=ft.FontWeight.W_700, color=SEC),
                ft.Container(expand=True),
                _row_score,
                _btn_marc,
            ], spacing=4),
            ft.Container(height=6),
            _uti_row1,
            ft.Container(height=4),
            _uti_row2,
        ], spacing=0),
        bgcolor=CARD,
        border=ft.border.all(1, BD),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=10, vertical=10),
    )

    # ══════════════════════════════════════════════════════════
    # CARDS DE SISTEMAS
    # ══════════════════════════════════════════════════════════
    # SISTEMAS — mapeamento de categorias e keywords por sistema
    # ══════════════════════════════════════════════════════════
    _SISTEMAS = [
        ("Cardiaco",    "favorite_rounded",      "#FF6B6B", {
            "categorias":      ["Cardiologia", "Lipídios", "Coagulação", "Inflamação"],
            "tipo_exame":      ["eco", "cardio", "cintilo", "eletro", "holter", "mapa",
                                "angiotomo", "coronario", "cateter", "angioplastia",
                                "doppler", "carotid", "vertebral", "duplex"],
            "historico_tipos": ["evento_cardiaco", "cirurgia", "procedimento"],
            "historico_kw":    ["stent", "safena", "mamaria", "infarto", "coronar",
                                "cardiaco", "revasculariz"],
            "especialidades":  ["cardiologia", "cardiologista", "hemodinamic"],
            "medico_kw":       ["cardio", "iara", "yara", "pazolini", "arantes", "vascular"],
            "remedios_kw":     ["propranolol", "atenolol", "metoprolol", "bisoprolol",
                                "carvedilol", "losartana", "valsartana", "enalapril",
                                "ramipril", "amlodipina", "nifedipina", "diltiazem",
                                "espironolactona", "furosemida", "hidroclorotiazida",
                                "digoxina", "amiodarona", "sinvastatina", "atorvastatina",
                                "rosuvastatina", "aspirina", "clopidogrel", "warfarina",
                                "rivaroxabana", "apixabana", "nitroglicerina", "isossorbida",
                                "anlodipino", "hidralazina", "captopril"],
        }),
        ("Visceral",    "bubble_chart_rounded",  "#58A6FF", {
            "categorias":      ["Função Renal", "Urina", "Função Hepática",
                                "Gastroenterologia", "Digestivo"],
            "tipo_exame":      ["prostata", "urologico", "cistoscopia", "urografia",
                                "uretro", "bexiga", "rins", "ultrassom renal",
                                "urofluxo", "urodinam",
                                "endoscopia", "colonoscopia", "ecografia abdominal",
                                "ultrassom abdominal", "gastro", "intestin",
                                "esofago", "estomago", "duodeno", "colon",
                                "hepato", "hepatico", "figado"],
            "historico_tipos": ["cirurgia", "procedimento", "internacao", "condicao_cronica"],
            "historico_kw":    ["prostata", "urinario", "bexiga", "ureta", "rtu",
                                "sonda", "urologico", "renal", "rim",
                                "gastro", "intestin", "esofago", "estomago",
                                "colon", "figado", "hepatite", "ulcera",
                                "refluxo", "hemorragia", "colonoscopia"],
            "especialidades":  ["urologi", "nefrologi", "gastroenterologi",
                                "hepatologi", "proctologi"],
            "medico_kw":       ["urologi", "nefro", "gastro", "hepato", "procto"],
            "remedios_kw":     ["tamsulosina", "dutasterida", "finasterida", "silodosina",
                                "alfuzosina", "omeprazol", "pantoprazol", "lansoprazol",
                                "esomeprazol", "ranitidina", "domperidona", "metoclopramida",
                                "ondansetrona", "loperamida", "mesalazina", "sulfassalazina",
                                "prednisona", "budesonida", "rifaximina", "metronidazol",
                                "ciprofloxacino", "lactulose", "bisacodil", "macrogol",
                                "ursodiol", "acido ursodesoxicolico", "espasmo"],
        }),
        ("Psiquiatria", "psychology_rounded",    "#BC8CFF", {
            "categorias":      [],
            "tipo_exame":      ["psiquiatrico", "neurologico", "eletroencefalo",
                                "ressonancia cranio", "tomografia cranio", "neuropsicologico",
                                "eeg", "potencial evocado"],
            "historico_tipos": ["diagnostico", "condicao_cronica", "infancia"],
            "historico_kw":    ["tdah", "bipolar", "panico", "psiquiatria", "ansiedade",
                                "depressao", "cisticercose", "neurologico", "emocional",
                                "humor", "mania", "hiperatividade", "atencao"],
            "especialidades":  ["psiquiatri", "neurologi", "psicologi"],
            "medico_kw":       ["psiquiatri", "neurologi", "luisa", "luísa", "stephan"],
            "remedios_kw":     ["ritalin", "clonazepam", "rivotril", "zolpidem",
                                "pregabalina", "divalproato", "divalcom",
                                "metilfenidato", "litio", "quetiapina",
                                "olanzapina", "risperidona", "lamotrigina"],
        }),
        ("Ortopedia",   "accessibility_rounded", "#3FB950", {
            "categorias":      ["Vitaminas"],
            "tipo_exame":      ["raio-x", "rx ", "densitometria", "ortopedico",
                                "articulacao", "coluna", "joelho", "quadril", "ressonancia"],
            "historico_tipos": ["diagnostico", "procedimento"],
            "historico_kw":    ["artrose", "ortopedia", "osso", "fratura", "coluna",
                                "articular", "densitometria"],
            "especialidades":  ["ortopedi", "reumatologi", "fisiatri"],
            "medico_kw":       ["ortopedi", "reumato"],
            "remedios_kw":     ["calcio", "vitamina d", "colecalciferol", "calcitriol",
                                "alendronato", "risedronato", "zoledronato", "denosumabe",
                                "teriparatida", "ibandronato", "raloxifeno",
                                "diclofenaco", "ibuprofeno", "naproxeno", "celecoxibe",
                                "meloxicam", "nimesulida", "etoricoxibe",
                                "tramadol", "codeina", "ciclobenzaprina", "carisoprodol",
                                "metocarbamol", "colageno", "glucosamina", "condroitina"],
        }),
        ("Sangue",      "bloodtype_rounded",     "#FF9500", {
            "categorias":      ["Hemograma", "Coagulação", "Enzimas", "Minerais",
                                "Função Renal", "Função Hepática", "Glicemia",
                                "Lipídios", "Ferro", "Proteínas", "Vitaminas",
                                "Inflamação", "Imunologia", "Infectologia", "Hormônios"],
            "tipo_exame":      ["hemograma", "hematologia", "coagulo", "bioquimica",
                                "hemostasia", "glicemia", "colesterol", "triglice",
                                "perfil lipidico", "perfil metabol", "tireoide",
                                "hormonio", "vitamina", "ferritina", "troponina",
                                "sorologica", "sorologia", "infectolog"],
            "historico_tipos": ["diagnostico", "procedimento"],
            "historico_kw":    ["anemia", "hemograma", "leucemia", "coagulacao",
                                "plaqueta", "hematologico", "colesterol", "glicemia",
                                "diabete", "tireoide", "vitamina"],
            "especialidades":  ["hematologi", "clinica medica", "clínica médica",
                                "endocrinologi", "infectologi"],
            "medico_kw":       ["hematologi", "clinico", "endocrin", "infectolog"],
            "remedios_kw":     ["metformina", "glibenclamida", "glipizida", "glimepirida",
                                "sitagliptina", "empagliflozina", "dapagliflozina",
                                "insulina", "levotiroxina", "metimazol", "propiltiouracil",
                                "ferro", "sulfato ferroso", "acido folico", "vitamina b12",
                                "eritropoetina", "hidroxiureia", "acido acetilsalicilico",
                                "enoxaparina", "heparina", "fenitoina", "aciclovir",
                                "fluconazol", "itraconazol"],
        }),
        ("Visão & Audição", "visibility_rounded",  "#00BCD4", {
            "categorias":      ["Oftalmologia", "Audiologia"],
            "tipo_exame":      ["campo visual", "campimetria", "retinografia", "oct",
                                "tonometria", "paquimetria", "biomicroscopia",
                                "fundo de olho", "oftalmolog", "glaucoma",
                                "audiometria", "impedanciometria", "timpanometria",
                                "audiolog", "otoscopia", "bera", "oae",
                                "potencial evocado", "otorrinolaringolog"],
            "historico_tipos": ["diagnostico", "procedimento", "condicao_cronica"],
            "historico_kw":    ["glaucoma", "catarata", "retina", "pressao intraocular",
                                "campo visual", "oftalmolog", "visao",
                                "surdez", "hipoacusia", "audiometria", "zumbido",
                                "otite", "ouvido", "audicao"],
            "especialidades":  ["oftalmologi", "otorrinolaringologi", "audiologi",
                                "fonoaudiologi"],
            "medico_kw":       ["oftalmolog", "oculist", "otorrino", "audiolog",
                                "fonoaudiolog"],
            "remedios_kw":     ["timolol", "brimonidina", "latanoprosta", "bimatoprosta",
                                "travoprosta", "dorzolamida", "brinzolamida", "acetazolamida",
                                "betaxolol", "colírio", "colirio", "tobramicina", "ciprofloxacino",
                                "dexametasona", "prednisolona", "lubrificante ocular",
                                "lagrima artificial", "betaistina", "flunarizina",
                                "meclizina", "prometazina", "corticosteroide nasal",
                                "montelucaste", "loratadina", "cetirizina"],
        }),
    ]

    def _abrir_sistema(label, icone, cor, cfg):
        import sqlite3 as _sq2

        def _fechar(e=None):
            if ref[0] in page.overlay:
                page.overlay.remove(ref[0])
            try: page.update()
            except Exception: pass

        # estado de expansão de cada secao: dict titulo -> bool
        _expandido = {}

        def _secao_colapsavel(titulo, cor_s, items, aberto=True):
            _expandido[titulo] = aberto
            corpo = ft.Column(controls=list(items), spacing=6,
                              visible=aberto)

            icone_ref = ft.Icon(
                "expand_less_rounded" if aberto else "expand_more_rounded",
                size=14, color=cor_s,
            )

            def _toggle(e, _titulo=titulo, _corpo=corpo, _icone=icone_ref):
                _expandido[_titulo] = not _expandido[_titulo]
                _corpo.visible = _expandido[_titulo]
                _icone.name = ("expand_less_rounded" if _expandido[_titulo]
                               else "expand_more_rounded")
                try: page.update()
                except Exception: pass

            header = ft.Container(
                content=ft.Row([
                    ft.Container(width=3, height=14, bgcolor=cor_s, border_radius=2),
                    ft.Text(titulo, size=10, color=cor_s,
                            weight=ft.FontWeight.W_700, expand=True),
                    icone_ref,
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.only(top=12, bottom=4),
                ink=True,
                on_click=_toggle,
            )
            return [header, corpo]

        lista = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

        # ── Histórico médico ────────────────────────────────
        try:
            conn2 = _sq2.connect(DB_PATH, timeout=30)
            tipos_ph = ",".join("?" * len(cfg["historico_tipos"]))
            kw_conds = " OR ".join(
                ["LOWER(titulo) LIKE ? OR LOWER(descricao) LIKE ? OR LOWER(sequela) LIKE ?"]
                * len(cfg["historico_kw"])
            )
            kw_params = []
            for kw in cfg["historico_kw"]:
                kw_params += [f"%{kw}%", f"%{kw}%", f"%{kw}%"]
            rows_h = conn2.execute(f"""
                SELECT data_aprox, tipo, titulo, descricao, sequela, alerta
                FROM historico_medico
                WHERE tipo IN ({tipos_ph}) AND ({kw_conds})
                ORDER BY data_aprox NULLS LAST
            """, cfg["historico_tipos"] + kw_params).fetchall()
            conn2.close()
        except Exception:
            rows_h = []

        if rows_h:
            items_h = []
            for data, tipo, titulo, desc, sequela, alerta in rows_h:
                cor_tipo = VERM if alerta else MUT
                items_h.append(ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(data or "s/data", size=10, color=MUT),
                            ft.Container(expand=True),
                            ft.Container(
                                content=ft.Text(tipo.replace("_"," "), size=9, color=cor_tipo),
                                bgcolor=ft.Colors.with_opacity(0.12, cor_tipo),
                                border_radius=6,
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            ),
                        ]),
                        ft.Text(titulo, size=12, color=TXT, weight=ft.FontWeight.W_600),
                        ft.Text(desc or "", size=10, color=SEC, max_lines=2),
                        ft.Text(f"Sequela: {sequela}", size=10, color=AMAR,
                                italic=True) if sequela else ft.Container(),
                    ], spacing=3, tight=True),
                    bgcolor=CARD,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.30, cor)),
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                ))
            for ctrl in _secao_colapsavel("HISTÓRICO", cor, items_h, aberto=False):
                lista.controls.append(ctrl)

        # ── helper: abre detalhe de um exame (resultados + laudo + imagens) ──
        # ── Hemograma: grupos por nome do parametro no resultado ──────────
        # usa o nome do resultado_estruturado (não nome_oficial) para busca
        _HEMOGRAMA_GRUPOS = [
            ("Série Vermelha", VERM, [
                "Eritrócitos", "Hemácias", "Hemacias",
                "Hemoglobina",
                "Hematócrito", "Hematocrito",
                "V.C.M.", "VCM",
                "H.C.M.", "H.C.M", "HCM",
                "C.H.B.C.M.", "C.H.C.M", "CHCM",
                "RDW",
            ]),
            ("Série Branca", AZUL, [
                "Leucócitos",
                "Promielócitos", "Mielócitos", "Metamielócitos",
                "Bastonetes", "Neutrófilos Bastonetes",
                "Segmentados", "Neutrófilos", "Neutrófilos Segmentados",
                "Eosinófilos",
                "Basófilos",
                "Linfócitos", "Linfócitos Atípicos",
                "Monócitos",
                "Blastos", "NLR",
            ]),
            ("Plaquetas", AMAR, [
                "Plaquetas", "MPV", "Reticulócitos",
            ]),
        ]

        def _abrir_detalhe_hemograma(exame_ids):
            from telas.tela_exames import _gerar_grafico_flet as _graf_fn
            import os as _os

            conn_h = _sq2.connect(DB_PATH, timeout=30)
            # busca pelo nome do resultado (r.parametro) — cobre todos os nomes reais
            all_rows = conn_h.execute("""
                SELECT r.parametro, r.valor, r.unidade, r.referencia, e.data_exame
                FROM exame_resultados r
                JOIN exames e ON r.exame_id = e.id
                WHERE r.exame_id IN (%s)
                ORDER BY r.parametro, e.data_exame DESC
            """ % ",".join("?" * len(exame_ids)), exame_ids).fetchall()

            img_rows = conn_h.execute("""
                SELECT pp.jpeg_local, a.ordem
                FROM exame_anexos a
                JOIN prontuario_paginas pp
                  ON pp.id = CAST(REPLACE(a.nome_arquivo,'.jpg','') AS INTEGER)
                WHERE a.exame_id IN (%s)
                ORDER BY a.ordem
            """ % ",".join("?" * len(exame_ids)), exame_ids).fetchall()
            conn_h.close()

            # índice pelo nome do parametro como está no banco
            por_param = {}
            for param, val, uni, ref_r, data_r in all_rows:
                if val and val.strip():
                    por_param.setdefault(param, []).append((val, uni, ref_r, data_r))

            imgs_validas = []
            for jpeg_local, ordem in img_rows:
                if jpeg_local:
                    p = _os.path.normpath(jpeg_local)
                    if _os.path.exists(p):
                        imgs_validas.append(p)

            def _fechar_h(e=None):
                if ref_h[0] in page.overlay:
                    page.overlay.remove(ref_h[0])
                try: page.update()
                except Exception: pass

            # ── abre segundo overlay com gráfico do grupo ──────
            def _abrir_grupo(grupo_nome, cor_g, params_g):
                # coleta séries — deduplica nomes sinônimos (pega só o primeiro encontrado)
                vistos = set()
                series_g = []
                CORES_EX = ["#58A6FF", "#3FB950", "#F0883E", "#BC8CFF", "#D29922",
                             "#FF6B6B", "#8BC34A", "#FF9500"]
                for p in params_g:
                    medidas = por_param.get(p, [])
                    if not medidas or p in vistos:
                        continue
                    vistos.add(p)
                    ex_meta = {"nome_oficial": p, "unidade": medidas[0][1]}
                    hist = [{"valor": v, "unidade": u, "referencia": r,
                             "data": d, "nivel": ""}
                            for v, u, r, d in medidas]
                    series_g.append((ex_meta, hist))

                def _fechar_g(e=None):
                    if ref_g[0] in page.overlay:
                        page.overlay.remove(ref_g[0])
                    try: page.update()
                    except Exception: pass

                corpo_g = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

                if series_g:
                    _cor_g = {em["nome_oficial"]: CORES_EX[i % len(CORES_EX)]
                              for i, (em, _) in enumerate(series_g)}
                    # radio: só o primeiro ativo no início
                    _nomes_g  = [em["nome_oficial"] for em, _ in series_g]
                    _ativos_g = {n: (i == 0) for i, n in enumerate(_nomes_g)}

                    ct_graf_g = ft.Container(
                        bgcolor=CARD, border_radius=10,
                        padding=ft.padding.symmetric(horizontal=4, vertical=6),
                    )
                    ct_tab_g = ft.Column(spacing=0)

                    def _rebuild_g():
                        sel = [(em, h) for em, h in series_g
                               if _ativos_g.get(em["nome_oficial"])]
                        ct_graf_g.content = _graf_fn(sel) if sel else ft.Text(
                            "Selecione ao menos um parâmetro", size=11, color=MUT,
                            text_align=ft.TextAlign.CENTER)
                        ct_tab_g.controls.clear()
                        for em, hist in sel:
                            cor_linha = _cor_g[em["nome_oficial"]]
                            for h in hist:
                                ct_tab_g.controls.append(ft.Container(
                                    content=ft.Row([
                                        ft.Text(h["data"][:10] if h["data"] else "s/data",
                                                size=9, color=MUT, width=72),
                                        ft.Text(em["nome_oficial"], size=10, color=SEC,
                                                expand=True),
                                        ft.Text(f"{h['valor']} {h['unidade'] or ''}",
                                                size=11, color=cor_linha,
                                                weight=ft.FontWeight.W_600),
                                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                    border=ft.Border(bottom=ft.BorderSide(1, BD)),
                                    padding=ft.padding.symmetric(horizontal=4, vertical=4),
                                ))
                        try: page.update()
                        except Exception: pass

                    # chips — sempre visíveis para ligar/desligar séries
                    _chip_g = {}
                    row_chips_g = ft.Row(wrap=True, spacing=6, run_spacing=6)

                    def _toggle_g(nome):
                        # radio: ativa o clicado, desativa todos os outros
                        for n in _ativos_g:
                            _ativos_g[n] = (n == nome)
                            cor_n = _cor_g[n]
                            _chip_g[n].bgcolor = (
                                ft.Colors.with_opacity(0.18, cor_n)
                                if _ativos_g[n] else CARD)
                            _chip_g[n].border = ft.border.all(
                                1, cor_n if _ativos_g[n] else BD)
                            _chip_g[n].content.controls[0].bgcolor = (
                                cor_n if _ativos_g[n] else MUT)
                            _chip_g[n].content.controls[1].color = (
                                TXT if _ativos_g[n] else MUT)
                        _rebuild_g()

                    for i, (em, _) in enumerate(series_g):
                        nome_c  = em["nome_oficial"]
                        cor_c   = _cor_g[nome_c]
                        ativo_c = _ativos_g[nome_c]
                        chip = ft.Container(
                            content=ft.Row([
                                ft.Container(width=8, height=8, border_radius=4,
                                             bgcolor=cor_c if ativo_c else MUT),
                                ft.Text(nome_c, size=10,
                                        color=TXT if ativo_c else MUT),
                            ], spacing=5, tight=True),
                            bgcolor=(ft.Colors.with_opacity(0.18, cor_c)
                                     if ativo_c else CARD),
                            border=ft.border.all(1, cor_c if ativo_c else BD),
                            border_radius=20,
                            padding=ft.padding.symmetric(horizontal=10, vertical=5),
                            ink=True,
                            on_click=lambda e, n=nome_c: _toggle_g(n),
                        )
                        _chip_g[nome_c] = chip
                        row_chips_g.controls.append(chip)

                    corpo_g.controls.append(
                        ft.Container(content=row_chips_g,
                                     padding=ft.padding.only(bottom=4))
                    )
                    _rebuild_g()
                    corpo_g.controls.append(ct_graf_g)
                    corpo_g.controls.append(ct_tab_g)
                else:
                    corpo_g.controls.append(
                        ft.Text("Sem dados", size=12, color=MUT)
                    )

                btn_vol_g = ft.Container(
                    content=ft.Row([
                        ft.Icon("arrow_back_rounded", size=14, color=AZUL),
                        ft.Text("Voltar", size=12, color=AZUL,
                                weight=ft.FontWeight.W_600),
                    ], spacing=4, tight=True),
                    ink=True, on_click=_fechar_g,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                )
                ref_g = [None]
                ref_g[0] = ft.Container(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([btn_vol_g,
                                    ft.Text(grupo_nome, size=14, color=TXT,
                                            weight=ft.FontWeight.W_700, expand=True),
                                    ], spacing=4),
                            ft.Divider(color=BD, height=1),
                            corpo_g,
                        ], spacing=0, expand=True),
                        bgcolor=BG, border_radius=16,
                        padding=ft.padding.symmetric(horizontal=16, vertical=16),
                        width=min(page.width * 0.92, 480) if page.width else 400,
                        height=min(page.height * 0.88, 680) if page.height else 580,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.55, "#000000"),
                    alignment=ft.alignment.Alignment(0, 0),
                    expand=True,
                )
                page.overlay.append(ref_g[0])
                try: page.update()
                except Exception: pass

            # ── corpo principal: cards dos grupos ──────────────
            corpo_h = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

            for grupo_nome, cor_g, params_g in _HEMOGRAMA_GRUPOS:
                # conta quantos parâmetros existem no banco
                n = sum(1 for p in params_g if p in por_param)
                if n == 0:
                    continue
                # resumo: primeiros 3 parâmetros com valores
                resumo_vals = []
                for p in params_g:
                    if p in por_param and len(resumo_vals) < 3:
                        v, u = por_param[p][0][0], por_param[p][0][1]
                        resumo_vals.append(f"{p}: {v} {u or ''}")

                card_g = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Container(width=4, height=16, bgcolor=cor_g,
                                         border_radius=2),
                            ft.Text(grupo_nome, size=13, color=cor_g,
                                    weight=ft.FontWeight.W_700, expand=True),
                            ft.Text(f"{n} param.", size=9, color=MUT),
                            ft.Icon("chevron_right_rounded", size=14, color=MUT),
                        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Text("\n".join(resumo_vals), size=10, color=SEC,
                                max_lines=3),
                    ], spacing=4, tight=True),
                    bgcolor=CARD,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.25, cor_g)),
                    border_radius=12,
                    padding=ft.padding.symmetric(horizontal=14, vertical=12),
                    ink=True,
                    on_click=lambda e, gn=grupo_nome, cg=cor_g, pg=params_g:
                        _abrir_grupo(gn, cg, pg),
                )
                corpo_h.controls.append(card_g)

            # imagens
            if imgs_validas:
                img_idx_h = [0]
                img_h = ft.Image(src=imgs_validas[0], fit=ft.ImageFit.CONTAIN,
                                 expand=True, height=260)
                ct_h = ft.Text(f"1 / {len(imgs_validas)}", size=10, color=MUT)

                def _nav_h(delta):
                    img_idx_h[0] = (img_idx_h[0] + delta) % len(imgs_validas)
                    img_h.src = imgs_validas[img_idx_h[0]]
                    ct_h.value = f"{img_idx_h[0]+1} / {len(imgs_validas)}"
                    try: page.update()
                    except Exception: pass

                def _zoom_h(e):
                    _abrir_detalhe_exame("Hemograma", exame_ids)

                corpo_h.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("IMAGENS", size=10, color=VERD,
                                    weight=ft.FontWeight.W_700, expand=True),
                            ct_h,
                            ft.IconButton("zoom_in_rounded", icon_color=VERD,
                                          icon_size=18, on_click=_zoom_h),
                        ]),
                        ft.GestureDetector(content=img_h, on_tap=_zoom_h),
                        ft.Row([
                            ft.IconButton("chevron_left_rounded", icon_color=TXT,
                                          icon_size=18,
                                          on_click=lambda e: _nav_h(-1),
                                          visible=len(imgs_validas) > 1),
                            ft.Container(expand=True),
                            ft.IconButton("chevron_right_rounded", icon_color=TXT,
                                          icon_size=18,
                                          on_click=lambda e: _nav_h(1),
                                          visible=len(imgs_validas) > 1),
                        ]),
                    ], spacing=6, tight=True),
                    bgcolor=CARD,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.20, VERD)),
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=8, vertical=8),
                ))

            btn_vol_h = ft.Container(
                content=ft.Row([
                    ft.Icon("arrow_back_rounded", size=14, color=AZUL),
                    ft.Text("Voltar", size=12, color=AZUL, weight=ft.FontWeight.W_600),
                ], spacing=4, tight=True),
                ink=True, on_click=_fechar_h,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            )

            ref_h = [None]
            ref_h[0] = ft.Container(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            btn_vol_h,
                            ft.Text("Hemograma", size=14, color=TXT,
                                    weight=ft.FontWeight.W_700, expand=True),
                        ], spacing=4),
                        ft.Divider(color=BD, height=1),
                        corpo_h,
                    ], spacing=0, expand=True),
                    bgcolor=BG, border_radius=16,
                    padding=ft.padding.symmetric(horizontal=16, vertical=16),
                    width=min(page.width * 0.92, 480) if page.width else 400,
                    height=min(page.height * 0.88, 680) if page.height else 580,
                ),
                bgcolor=ft.Colors.with_opacity(0.55, "#000000"),
                alignment=ft.alignment.Alignment(0, 0),
                expand=True,
            )
            page.overlay.append(ref_h[0])
            try: page.update()
            except Exception: pass

        def _abrir_detalhe_exame(nome_exame, exame_ids, filtrar_parametro=None):
            import os as _os
            conn_d = _sq2.connect(DB_PATH, timeout=30)

            # resultados: se filtrar_parametro informado, só aquele exame_padrao
            if filtrar_parametro:
                # busca o exame_padrao_id pelo nome_oficial
                ep_row = conn_d.execute(
                    "SELECT id FROM exames_padrao WHERE nome_oficial = ? LIMIT 1",
                    (filtrar_parametro,)
                ).fetchone()
                ep_id = ep_row[0] if ep_row else None
                if ep_id:
                    res_rows = conn_d.execute("""
                        SELECT r.parametro, r.valor, r.unidade, r.referencia, e.data_exame
                        FROM exame_resultados r
                        JOIN exames e ON r.exame_id = e.id
                        WHERE r.exame_id IN (%s)
                          AND r.exame_padrao_id = ?
                          AND r.valor IS NOT NULL AND r.valor != ''
                        ORDER BY e.data_exame DESC
                    """ % ",".join("?" * len(exame_ids)), exame_ids + [ep_id]).fetchall()
                else:
                    # fallback: filtra pelo nome do parametro
                    res_rows = conn_d.execute("""
                        SELECT r.parametro, r.valor, r.unidade, r.referencia, e.data_exame
                        FROM exame_resultados r
                        JOIN exames e ON r.exame_id = e.id
                        WHERE r.exame_id IN (%s)
                          AND LOWER(r.parametro) = LOWER(?)
                          AND r.valor IS NOT NULL AND r.valor != ''
                        ORDER BY e.data_exame DESC
                    """ % ",".join("?" * len(exame_ids)), exame_ids + [filtrar_parametro]).fetchall()
            else:
                res_rows = conn_d.execute("""
                    SELECT r.parametro, r.valor, r.unidade, r.referencia, e.data_exame
                    FROM exame_resultados r
                    JOIN exames e ON r.exame_id = e.id
                    WHERE r.exame_id IN (%s)
                      AND r.valor IS NOT NULL AND r.valor != ''
                    ORDER BY r.parametro, e.data_exame DESC
                """ % ",".join("?" * len(exame_ids)), exame_ids).fetchall()

            # laudo texto de cada exame
            laudo_rows = conn_d.execute("""
                SELECT id, data_exame, laboratorio, resultado_texto, tipo
                FROM exames
                WHERE id IN (%s) AND resultado_texto IS NOT NULL AND resultado_texto != ''
                ORDER BY data_exame DESC
            """ % ",".join("?" * len(exame_ids)), exame_ids).fetchall()

            # laudos estruturados (tabela laudos) — inclui exames tipo mapa
            laudo_struct = conn_d.execute("""
                SELECT e.data_exame, e.laboratorio, l.resumo, l.conclusao
                FROM laudos l
                JOIN exames e ON e.id = l.exame_id
                WHERE l.exame_id IN (%s)
                ORDER BY e.data_exame DESC
            """ % ",".join("?" * len(exame_ids)), exame_ids).fetchall()

            # imagens via prontuario_paginas JOIN exame_anexos
            img_rows = conn_d.execute("""
                SELECT pp.jpeg_local, pp.pagina_num, a.ordem
                FROM exame_anexos a
                JOIN prontuario_paginas pp ON pp.id = CAST(REPLACE(a.nome_arquivo,'.jpg','') AS INTEGER)
                WHERE a.exame_id IN (%s)
                ORDER BY a.exame_id, a.ordem
            """ % ",".join("?" * len(exame_ids)), exame_ids).fetchall()
            conn_d.close()

            # normalizar caminhos das imagens
            imgs_validas = []
            for jpeg_local, pnum, ordem in img_rows:
                if jpeg_local:
                    p = _os.path.normpath(jpeg_local)
                    if _os.path.exists(p):
                        imgs_validas.append(p)

            def _fechar_det(e=None):
                if ref_det[0] in page.overlay:
                    page.overlay.remove(ref_det[0])
                try: page.update()
                except Exception: pass

            corpo_det = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

            # exames de monitoramento ambulatorial (MAPA) nao usam grafico —
            # tem 40+ parametros de uma sessao unica, nao serie temporal
            _eh_mapa = "mapa" in nome_exame.lower()

            # ── gráfico de resultados numéricos (nao para MAPA) ──
            grupos_r = {}
            for param, val, uni, ref_r, data_r in res_rows:
                if param not in grupos_r:
                    grupos_r[param] = []
                grupos_r[param].append((val, uni, ref_r, data_r))

            if grupos_r and not _eh_mapa:
                from telas.tela_exames import _gerar_grafico_flet as _graf_fn

                corpo_det.controls.append(
                    ft.Text("RESULTADOS", size=10, color=AZUL, weight=ft.FontWeight.W_700)
                )

                CORES_EX = ["#58A6FF", "#3FB950", "#F0883E", "#BC8CFF", "#D29922",
                            "#FF6B6B", "#8BC34A", "#FF9500", "#4ECDC4", "#E84393"]

                # monta series completas
                _series_todas = []
                for param, medidas in grupos_r.items():
                    ex_meta = {"nome_oficial": param,
                               "unidade": medidas[0][1] if medidas else ""}
                    hist = [{"valor": val, "unidade": uni, "referencia": ref_r,
                             "data": data_r, "nivel": ""}
                            for val, uni, ref_r, data_r in medidas]
                    _series_todas.append((ex_meta, hist))

                _cor_serie = {em["nome_oficial"]: CORES_EX[i % len(CORES_EX)]
                              for i, (em, _) in enumerate(_series_todas)}

                # radio: só o primeiro ativo no início
                _nomes_det  = [em["nome_oficial"] for em, _ in _series_todas]
                _ativos_det = {n: (i == 0) for i, n in enumerate(_nomes_det)}

                ct_graf_det = ft.Container(
                    bgcolor=CARD, border_radius=10,
                    padding=ft.padding.symmetric(horizontal=4, vertical=6),
                )

                def _rebuild_graf_det():
                    sel = [(em, h) for em, h in _series_todas
                           if _ativos_det.get(em["nome_oficial"])]
                    ct_graf_det.content = _graf_fn(sel) if sel else ft.Text(
                        "Selecione ao menos um parâmetro", size=11, color=MUT,
                        text_align=ft.TextAlign.CENTER)
                    try: page.update()
                    except Exception: pass

                # chips — só exibe se houver mais de 1 série
                if len(_series_todas) > 1:
                    _chip_ctrls = {}
                    row_chips_det = ft.Row(wrap=True, spacing=6, run_spacing=6)

                    def _toggle_det(nome):
                        # radio: ativa o clicado, desativa todos os outros
                        for n in _ativos_det:
                            _ativos_det[n] = (n == nome)
                            cor_n = _cor_serie[n]
                            _chip_ctrls[n].bgcolor = (
                                ft.Colors.with_opacity(0.18, cor_n)
                                if _ativos_det[n] else CARD)
                            _chip_ctrls[n].border = ft.border.all(
                                1, cor_n if _ativos_det[n] else BD)
                            _chip_ctrls[n].content.controls[0].bgcolor = (
                                cor_n if _ativos_det[n] else MUT)
                            _chip_ctrls[n].content.controls[1].color = (
                                TXT if _ativos_det[n] else MUT)
                        _rebuild_graf_det()

                    for i, (em, _) in enumerate(_series_todas):
                        nome_c  = em["nome_oficial"]
                        cor_c   = _cor_serie[nome_c]
                        ativo_c = _ativos_det[nome_c]
                        chip = ft.Container(
                            content=ft.Row([
                                ft.Container(width=8, height=8, border_radius=4,
                                             bgcolor=cor_c if ativo_c else MUT),
                                ft.Text(nome_c, size=10,
                                        color=TXT if ativo_c else MUT),
                            ], spacing=5, tight=True),
                            bgcolor=(ft.Colors.with_opacity(0.18, cor_c)
                                     if ativo_c else CARD),
                            border=ft.border.all(1, cor_c if ativo_c else BD),
                            border_radius=20,
                            padding=ft.padding.symmetric(horizontal=10, vertical=5),
                            ink=True,
                            on_click=lambda e, n=nome_c: _toggle_det(n),
                        )
                        _chip_ctrls[nome_c] = chip
                        row_chips_det.controls.append(chip)

                    corpo_det.controls.append(
                        ft.Container(content=row_chips_det,
                                     padding=ft.padding.only(bottom=4))
                    )

                _rebuild_graf_det()
                corpo_det.controls.append(ct_graf_det)

                # tabela detalhada por parâmetro abaixo do gráfico
                for param, medidas in grupos_r.items():
                    linhas_tabela = []
                    for val, uni, ref_r, data_r in medidas:
                        linhas_tabela.append(ft.Container(
                            content=ft.Row([
                                ft.Text(data_r[:10] if data_r else "s/data",
                                        size=10, color=MUT, expand=True),
                                ft.Text(f"{val} {uni or ''}",
                                        size=12, color=AZUL, weight=ft.FontWeight.W_600),
                                ft.Text(f"ref: {ref_r}" if ref_r else "",
                                        size=9, color=MUT),
                            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            border=ft.Border(bottom=ft.BorderSide(1, BD)),
                            padding=ft.padding.symmetric(horizontal=4, vertical=5),
                        ))
                    corpo_det.controls.append(ft.Container(
                        content=ft.Column([
                            ft.Text(param, size=10, color=SEC,
                                    weight=ft.FontWeight.W_600),
                            *linhas_tabela,
                        ], spacing=2, tight=True),
                        bgcolor=CARD,
                        border=ft.Border(bottom=ft.BorderSide(1, BD)),
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    ))

            # ── laudo estruturado (tabela laudos) ──────────────
            for data_e, lab, resumo, conclusao in laudo_struct:
                partes = []
                if resumo:
                    partes.append(("RESUMO", resumo))
                if conclusao:
                    partes.append(("CONCLUSAO", conclusao))
                for titulo_l, texto_l in partes:
                    corpo_det.controls.append(ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(titulo_l, size=10, color=ROXO,
                                        weight=ft.FontWeight.W_700),
                                ft.Container(expand=True),
                                ft.Text(f"{data_e[:10] if data_e else ''}  {lab or ''}",
                                        size=9, color=MUT),
                            ]),
                            ft.Text(texto_l, size=11, color=SEC, selectable=True),
                        ], spacing=6, tight=True),
                        bgcolor=CARD,
                        border=ft.border.all(1, ft.Colors.with_opacity(0.20, ROXO)),
                        border_radius=10,
                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    ))

            # ── laudo texto (resultado_texto do exame) ──────────
            for eid, data_e, lab, txt, tipo_e in laudo_rows:
                if not txt:
                    continue
                corpo_det.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("LAUDO", size=10, color=ROXO, weight=ft.FontWeight.W_700),
                            ft.Container(expand=True),
                            ft.Text(f"{data_e[:10] if data_e else ''}  {lab or ''}",
                                    size=9, color=MUT),
                        ]),
                        ft.Text(txt, size=11, color=SEC, selectable=True),
                    ], spacing=6, tight=True),
                    bgcolor=CARD,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.20, ROXO)),
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                ))

            # ── botão imagens ──────────────────────────────────
            if imgs_validas:
                img_idx = [0]
                img_view = ft.Image(
                    src=imgs_validas[0],
                    fit=ft.ImageFit.CONTAIN,
                    expand=True,
                    height=300,
                )
                contador_img = ft.Text(
                    f"1 / {len(imgs_validas)}", size=10, color=MUT,
                )

                def _nav_img(delta, _idx=img_idx, _iv=img_view, _ct=contador_img,
                             _zoom_iv=None):
                    _idx[0] = (_idx[0] + delta) % len(imgs_validas)
                    _iv.src = imgs_validas[_idx[0]]
                    _ct.value = f"{_idx[0]+1} / {len(imgs_validas)}"
                    if _zoom_iv is not None:
                        _zoom_iv.src = imgs_validas[_idx[0]]
                    try: page.update()
                    except Exception: pass

                # ── lightbox (tela cheia) ─────────────────────
                def _abrir_zoom(e, _idx=img_idx):
                    zoom_img = ft.Image(
                        src=imgs_validas[_idx[0]],
                        fit=ft.ImageFit.CONTAIN,
                        expand=True,
                    )
                    zoom_ct = ft.Text(
                        f"{_idx[0]+1} / {len(imgs_validas)}", size=11, color=TXT,
                    )
                    ref_zoom = [None]

                    def _fechar_zoom(e=None):
                        if ref_zoom[0] in page.overlay:
                            page.overlay.remove(ref_zoom[0])
                        try: page.update()
                        except Exception: pass

                    def _nav_zoom(delta):
                        _idx[0] = (_idx[0] + delta) % len(imgs_validas)
                        zoom_img.src = imgs_validas[_idx[0]]
                        img_view.src = imgs_validas[_idx[0]]
                        contador_img.value = f"{_idx[0]+1} / {len(imgs_validas)}"
                        zoom_ct.value = f"{_idx[0]+1} / {len(imgs_validas)}"
                        try: page.update()
                        except Exception: pass

                    ref_zoom[0] = ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Container(
                                    content=ft.Row([
                                        ft.Icon("arrow_back_rounded", size=16, color=AZUL),
                                        ft.Text("Voltar", size=13, color=AZUL,
                                                weight=ft.FontWeight.W_600),
                                    ], spacing=4, tight=True),
                                    ink=True, on_click=_fechar_zoom,
                                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                                ),
                                ft.Container(expand=True),
                                zoom_ct,
                                ft.IconButton(
                                    icon="chevron_left_rounded", icon_color=TXT, icon_size=22,
                                    on_click=lambda e: _nav_zoom(-1),
                                    visible=len(imgs_validas) > 1,
                                ),
                                ft.IconButton(
                                    icon="chevron_right_rounded", icon_color=TXT, icon_size=22,
                                    on_click=lambda e: _nav_zoom(1),
                                    visible=len(imgs_validas) > 1,
                                ),
                            ], spacing=0),
                            zoom_img,
                        ], spacing=0, expand=True),
                        bgcolor="#000000",
                        expand=True,
                        alignment=ft.alignment.Alignment(0, 0),
                    )
                    page.overlay.append(ref_zoom[0])
                    try: page.update()
                    except Exception: pass

                btn_ant = ft.IconButton(
                    icon="chevron_left_rounded", icon_color=TXT, icon_size=20,
                    on_click=lambda e: _nav_img(-1),
                    visible=len(imgs_validas) > 1,
                )
                btn_prox = ft.IconButton(
                    icon="chevron_right_rounded", icon_color=TXT, icon_size=20,
                    on_click=lambda e: _nav_img(1),
                    visible=len(imgs_validas) > 1,
                )
                btn_zoom = ft.IconButton(
                    icon="zoom_in_rounded", icon_color=VERD, icon_size=20,
                    tooltip="Ampliar",
                    on_click=_abrir_zoom,
                )

                corpo_det.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("IMAGENS", size=10, color=VERD, weight=ft.FontWeight.W_700,
                                    expand=True),
                            contador_img,
                            btn_zoom,
                        ]),
                        ft.GestureDetector(
                            content=img_view,
                            on_tap=_abrir_zoom,
                        ),
                        ft.Row([btn_ant, ft.Container(expand=True), btn_prox],
                               vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ], spacing=6, tight=True),
                    bgcolor=CARD,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.20, VERD)),
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=8, vertical=8),
                ))

            if not grupos_r and not laudo_rows and not imgs_validas:
                corpo_det.controls.append(ft.Container(
                    content=ft.Text("Nenhum dado disponível", size=12, color=MUT),
                    padding=ft.padding.symmetric(vertical=20),
                    alignment=ft.alignment.Alignment(0, 0),
                ))

            btn_fc_det = ft.Container(
                content=ft.Row([
                    ft.Icon("arrow_back_rounded", size=14, color=AZUL),
                    ft.Text("Voltar", size=12, color=AZUL, weight=ft.FontWeight.W_600),
                ], spacing=4, tight=True),
                ink=True, on_click=_fechar_det,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            )

            ref_det = [None]
            ref_det[0] = ft.Container(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            btn_fc_det,
                            ft.Text(nome_exame, size=14, color=TXT,
                                    weight=ft.FontWeight.W_700, expand=True),
                        ], spacing=4),
                        ft.Divider(color=BD, height=1),
                        corpo_det,
                    ], spacing=0, expand=True),
                    bgcolor=BG,
                    border_radius=16,
                    padding=ft.padding.symmetric(horizontal=16, vertical=16),
                    width=min(page.width * 0.92, 480) if page.width else 400,
                    height=min(page.height * 0.88, 680) if page.height else 580,
                ),
                bgcolor=ft.Colors.with_opacity(0.55, "#000000"),
                alignment=ft.alignment.Alignment(0, 0),
                expand=True,
            )
            page.overlay.append(ref_det[0])
            try: page.update()
            except Exception: pass

        # ── Exames de laboratório ───────────────────────────
        # Grupos condensados: categorias que viram um card único (como Hemograma)
        # Cada grupo: (label, cor_hex, [nomes_parametro_no_banco...], [categorias_excluidas_da_lista])
        _GRUPOS_COND = [
            ("Colesterol & Lipídios", "#F0883E", [
                "Colesterol Total", "Colesterol HDL", "Colesterol LDL",
                "Colesterol VLDL", "Colesterol Não-HDL", "Triglicerídeos",
            ], {"lipídios"}),
            ("Glicemia", "#FDCB6E", [
                "Glicemia de Jejum", "GLICOSE JEJUM",
                "Hemoglobina Glicada (HbA1c)",
                "Glicemia Média Estimada", "Frutosamina",
                "Glicemia 1h Pós-Dextrosol", "Glicemia 2h Pós-Dextrosol",
                "Insulina", "Insulina Basal", "HOMA-IR",
            ], {"glicemia"}),
            ("Função Hepática", "#8BC34A", [
                "TGO (AST)", "TGP (ALT)", "GGT",
                "Fosfatase Alcalina", "Albumina", "Globulinas", "Proteínas Totais",
                "Bilirrubina Total", "Bilirrubina Direta", "Bilirrubina Indireta",
                "LDH", "Amilase", "Lipase",
            ], {"função hepática", "proteínas", "enzimas"}),
            ("Função Renal", "#4ECDC4", [
                "Creatinina", "Ureia", "BUN (Nitrogênio Ureico)",
                "eRFG", "Ácido Úrico",
                "MICROALBUMINURIA", "RESERVA ALCALINA - BICARBONATO",
            ], {"função renal"}),
            ("Minerais & Eletrólitos", "#58A6FF", [
                "Sódio", "SÓDIO", "Potássio", "POTASSIO",
                "Cálcio", "CÁLCIO", "Cálcio Total", "Cálcio Ionizado (mmol/L)",
                "Cálcio Ionizado (mg/dL)", "Cálcio Ionizado (mEq/L)", "Cálcio Iônico",
                "Magnésio", "Fósforo", "FOSFORO", "Zinco",
                "Cloro", "Reserva Alcalina", "RESERVA ALCALINA - BICARBONATO",
            ], {"minerais"}),
            ("Tireoide", "#BC8CFF", [
                "TSH", "T4 Livre", "T3 Livre", "T4 Total", "T3 Total",
                "T3 Reverso", "Anti-TPO", "Anti-Tireoglobulina",
            ], {"tireoide"}),
            ("Hormônios", "#FF9500", [
                "Testosterona Total", "Testosterona Livre",
                "SHBG", "Estradiol (E2)", "DHT (Di-Hidrotestosterona)",
                "FSH", "LH", "Prolactina", "Cortisol", "DHEA-S",
                "PTH (Paratormônio)", "PARATORMÔNIO PTH INTACTO (MOLÉCULA INTEIRA)",
                "IGF-1",
            ], {"hormônios"}),
            ("Ferro", "#D29922", [
                "Ferritina", "FERRITINA SÉRICA", "Ferro Sérico", "FERRO SÉRICO",
                "Transferrina", "Saturação de Transferrina",
            ], {"ferro"}),
            ("Vitaminas", "#FDCB6E", [
                "Vitamina D (25-OH)", "Vitamina B12",
                "Ácido Fólico (Vitamina B9)", "Vitamina A (Retinol)",
                "Homocisteína", "HOMOCISTEÍNA", "Serotonina",
            ], {"vitaminas"}),
            ("Inflamação & Imunidade", "#FF6B6B", [
                "PCR", "VHS",
                "Anti-Transglutaminase IgA", "Imunoglobulina A (IgA)",
                "Fator Reumatoide", "FAN (ANA)",
            ], {"inflamação", "imunologia"}),
            ("Enzimas Cardíacas", "#E84393", [
                "CPK Total", "CPK-MB", "CK-MB", "Troponina I", "Troponina T",
                "LDH", "Mioglobina",
            ], set()),  # CPK/LDH já aparecem em Hep — não exclui categoria inteira
            ("Coagulação", "#A29BFE", [
                "Fibrinogênio", "INR", "Tempo de Protrombina",
                "TTPA", "Atividade de Protrombina", "D-Dímero",
            ], {"coagulação"}),
        ]

        # categorias totalmente absorvidas pelos grupos (não aparecem como itens soltos)
        _CAT_CONDENSADAS = set()
        for _, _, _, cats_exc in _GRUPOS_COND:
            _CAT_CONDENSADAS.update(cats_exc)
        _CAT_CONDENSADAS.add("hemograma")
        _CAT_HEMOGRAMA = {"hemograma"}

        # coleta todos os resultados para grupos condensados e itens soltos
        # rows_e: (nome_oficial, categoria, exame_id, data_exame, parametro_real)
        try:
            conn3b = _sq2.connect(DB_PATH, timeout=30)
            cat_ph2       = ",".join("?" * len(cfg["categorias"]))
            cat_params2   = [c.lower() for c in cfg["categorias"]]
            kw_med_conds2 = " OR ".join(["LOWER(e.medico_solicit) LIKE ?" for _ in cfg["medico_kw"]])
            kw_med_params2 = [f"%{k}%" for k in cfg["medico_kw"]]
            rows_e2 = conn3b.execute(f"""
                SELECT ep.nome_oficial, ep.categoria, e.id, e.data_exame, r.parametro
                FROM exame_resultados r
                JOIN exames e ON r.exame_id = e.id
                JOIN exames_padrao ep ON r.exame_padrao_id = ep.id
                WHERE r.valor IS NOT NULL AND r.valor != ''
                  AND (
                    LOWER(ep.categoria) IN ({cat_ph2})
                    OR ({kw_med_conds2})
                  )
                ORDER BY ep.nome_oficial, e.data_exame DESC
            """, cat_params2 + kw_med_params2).fetchall()
            conn3b.close()
        except Exception:
            rows_e2 = []

        # IDs dos exames de hemograma
        _tem_hemograma = "Hemograma" in cfg["categorias"]
        _eids_hemograma = []
        for _, cat, eid, _, _ in rows_e2:
            if (cat or "").lower() == "hemograma" and eid not in _eids_hemograma:
                _eids_hemograma.append(eid)

        # Para cada grupo condensado: mapeia param_real -> eids com dados
        # _gc_dados[grupo_label] = {param_real: [eid, ...]}
        _gc_eids = {}    # label -> set(eid)
        _gc_params = {}  # label -> {param_real: True}
        for gl, gcor, gparams, _ in _GRUPOS_COND:
            _gc_eids[gl]   = set()
            _gc_params[gl] = set()
        for nome_of, cat, eid, data_e, param_real in rows_e2:
            cat_low = (cat or "").lower()
            if cat_low == "hemograma":
                continue
            for gl, gcor, gparams, cats_exc in _GRUPOS_COND:
                if param_real in gparams or nome_of in gparams or cat_low in cats_exc:
                    _gc_eids[gl].add(eid)
                    _gc_params[gl].add(param_real)

        # Parâmetros já absorvidos por algum grupo (não aparecem como item solto)
        _params_absorvidos = set()
        for gl, gcor, gparams, cats_exc in _GRUPOS_COND:
            if _gc_eids[gl]:
                _params_absorvidos.update(_gc_params[gl])
                _params_absorvidos.update(gp.lower() for gp in gparams)

        # Itens soltos: nome_oficial não absorvido por grupo nem hemograma
        grupos_soltos = {}
        for nome_of, cat, eid, data_e, param_real in rows_e2:
            cat_low = (cat or "").lower()
            if cat_low == "hemograma":
                continue
            if param_real in _params_absorvidos or param_real.lower() in _params_absorvidos:
                continue
            if nome_of not in grupos_soltos:
                grupos_soltos[nome_of] = []
            grupos_soltos[nome_of].append((eid, data_e))

        if rows_e2:
            # ── monta lista completa de itens de laboratório ──────────────
            _items_lab_todos = []   # Container flet
            _items_lab_dados = []   # (chave_lower, container) para busca

            def _card_grupo_cond(label, cor_g, eids_g):
                """Card condensado clicável — abre overlay igual ao Hemograma."""
                eids_list = sorted(eids_g)
                try:
                    conn_gc = _sq2.connect(DB_PATH, timeout=30)
                    ultima_gc = conn_gc.execute(
                        "SELECT MAX(data_exame) FROM exames WHERE id IN (%s)"
                        % ",".join("?" * len(eids_list)), eids_list
                    ).fetchone()[0] or ""
                    conn_gc.close()
                    ultima_gc = ultima_gc[:10]
                except Exception:
                    ultima_gc = ""

                n_params = len(_gc_params.get(label, set()))
                _c_g = ft.Container(
                    content=ft.Row([
                        ft.Container(width=4, height=14, bgcolor=cor_g, border_radius=2),
                        ft.Text(label, size=12, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True),
                        ft.Text(f"{n_params} param.", size=9, color=MUT),
                        ft.Text(ultima_gc, size=9, color=MUT),
                        ft.Icon("chevron_right_rounded", size=13, color=MUT),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.20, cor_g)),
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    ink=True,
                    on_click=lambda e, _l=label, _cg=cor_g, _el=eids_list:
                        _abrir_grupo_cond(_l, _cg, _el),
                )
                return _c_g

            def _abrir_grupo_cond(label, cor_g, eids_list):
                """Lista de parâmetros do grupo → clica → gráfico/detalhe."""
                from telas.tela_exames import _gerar_grafico_flet as _graf_fn2

                conn_gc2 = _sq2.connect(DB_PATH, timeout=30)
                gc_rows = conn_gc2.execute("""
                    SELECT r.parametro, r.valor, r.unidade, r.referencia, e.data_exame
                    FROM exame_resultados r
                    JOIN exames e ON r.exame_id = e.id
                    WHERE r.exame_id IN (%s) AND r.valor IS NOT NULL AND r.valor != ''
                    ORDER BY r.parametro, e.data_exame DESC
                """ % ",".join("?" * len(eids_list)), eids_list).fetchall()
                conn_gc2.close()

                por_param_gc = {}
                for param, val, uni, ref_r, data_r in gc_rows:
                    if val and val.strip():
                        por_param_gc.setdefault(param, []).append((val, uni, ref_r, data_r))

                CORES_GC = ["#58A6FF", "#3FB950", "#F0883E", "#BC8CFF", "#D29922",
                            "#FF6B6B", "#8BC34A", "#FF9500", "#4ECDC4", "#E84393"]

                # lista ordenada de parâmetros com dados
                vistos_gc = set()
                series_gc_todas = []
                for p in sorted(_gc_params.get(label, set())):
                    if p not in por_param_gc or p in vistos_gc:
                        continue
                    vistos_gc.add(p)
                    medidas = por_param_gc[p]
                    ex_meta = {"nome_oficial": p, "unidade": medidas[0][1]}
                    hist = [{"valor": v, "unidade": u, "referencia": r,
                             "data": d, "nivel": ""}
                            for v, u, r, d in medidas]
                    series_gc_todas.append((ex_meta, hist))

                def _fechar_gc(e=None):
                    if ref_gc[0] in page.overlay:
                        page.overlay.remove(ref_gc[0])
                    try: page.update()
                    except Exception: pass

                # ── detalhe de um parâmetro (2º nível) ────────────────────
                def _abrir_detalhe_param(em, hist, cor_p):
                    def _fechar_dp(e=None):
                        if ref_dp[0] in page.overlay:
                            page.overlay.remove(ref_dp[0])
                        try: page.update()
                        except Exception: pass

                    corpo_dp = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
                    corpo_dp.controls.append(ft.Container(
                        content=_graf_fn2([(em, hist)]),
                        bgcolor=CARD, border_radius=10,
                        padding=ft.padding.symmetric(horizontal=4, vertical=6),
                    ))
                    for h in hist:
                        corpo_dp.controls.append(ft.Container(
                            content=ft.Row([
                                ft.Text(h["data"][:10] if h["data"] else "s/data",
                                        size=9, color=MUT, width=72),
                                ft.Text(f"{h['valor']} {h['unidade'] or ''}",
                                        size=13, color=cor_p,
                                        weight=ft.FontWeight.W_700),
                                ft.Container(expand=True),
                                ft.Text(h["referencia"] or "", size=9, color=MUT),
                            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            border=ft.Border(bottom=ft.BorderSide(1, BD)),
                            padding=ft.padding.symmetric(horizontal=4, vertical=6),
                        ))

                    btn_vol_dp = ft.Container(
                        content=ft.Row([
                            ft.Icon("arrow_back_rounded", size=14, color=AZUL),
                            ft.Text(label, size=12, color=AZUL,
                                    weight=ft.FontWeight.W_600),
                        ], spacing=4, tight=True),
                        ink=True, on_click=_fechar_dp,
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    )
                    ref_dp = [None]
                    ref_dp[0] = ft.Container(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Row([btn_vol_dp,
                                        ft.Text(em["nome_oficial"], size=14, color=TXT,
                                                weight=ft.FontWeight.W_700, expand=True)],
                                       spacing=4),
                                ft.Divider(color=BD, height=1),
                                corpo_dp,
                            ], spacing=0, expand=True),
                            bgcolor=BG, border_radius=16,
                            padding=ft.padding.symmetric(horizontal=16, vertical=16),
                            width=min(page.width * 0.92, 480) if page.width else 400,
                            height=min(page.height * 0.88, 680) if page.height else 580,
                        ),
                        bgcolor=ft.Colors.with_opacity(0.55, "#000000"),
                        alignment=ft.alignment.Alignment(0, 0),
                        expand=True,
                    )
                    page.overlay.append(ref_dp[0])
                    try: page.update()
                    except Exception: pass

                # ── 1º nível: lista de parâmetros ────────────────────────
                corpo_gc = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)

                if series_gc_todas:
                    for i, (em, hist) in enumerate(series_gc_todas):
                        cor_p  = CORES_GC[i % len(CORES_GC)]
                        ultima = hist[0]["data"][:10] if hist and hist[0]["data"] else ""
                        ult_v  = f"{hist[0]['valor']} {hist[0]['unidade'] or ''}".strip() if hist else ""
                        corpo_gc.controls.append(ft.Container(
                            content=ft.Row([
                                ft.Container(width=4, height=30, bgcolor=cor_p,
                                             border_radius=2),
                                ft.Column([
                                    ft.Text(em["nome_oficial"], size=12, color=TXT,
                                            weight=ft.FontWeight.W_500),
                                    ft.Text(ult_v, size=11, color=cor_p,
                                            weight=ft.FontWeight.W_700),
                                ], spacing=1, tight=True, expand=True),
                                ft.Column([
                                    ft.Text(ultima, size=9, color=MUT,
                                            text_align=ft.TextAlign.RIGHT),
                                    ft.Text(f"{len(hist)}×", size=9, color=MUT,
                                            text_align=ft.TextAlign.RIGHT),
                                ], spacing=1, tight=True,
                                   horizontal_alignment=ft.CrossAxisAlignment.END),
                                ft.Icon("chevron_right_rounded", size=13, color=MUT),
                            ], spacing=10,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            bgcolor=CARD,
                            border=ft.Border(bottom=ft.BorderSide(1, BD)),
                            padding=ft.padding.symmetric(horizontal=12, vertical=10),
                            ink=True,
                            on_click=lambda e, _em=em, _h=hist, _cp=cor_p:
                                _abrir_detalhe_param(_em, _h, _cp),
                        ))
                else:
                    corpo_gc.controls.append(ft.Text("Sem dados", size=12, color=MUT))

                btn_vol_gc = ft.Container(
                    content=ft.Row([
                        ft.Icon("arrow_back_rounded", size=14, color=AZUL),
                        ft.Text("Voltar", size=12, color=AZUL,
                                weight=ft.FontWeight.W_600),
                    ], spacing=4, tight=True),
                    ink=True, on_click=_fechar_gc,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                )
                ref_gc = [None]
                ref_gc[0] = ft.Container(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([btn_vol_gc,
                                    ft.Text(label, size=14, color=TXT,
                                            weight=ft.FontWeight.W_700, expand=True)],
                                   spacing=4),
                            ft.Divider(color=BD, height=1),
                            corpo_gc,
                        ], spacing=0, expand=True),
                        bgcolor=BG, border_radius=16,
                        padding=ft.padding.symmetric(horizontal=16, vertical=16),
                        width=min(page.width * 0.92, 480) if page.width else 400,
                        height=min(page.height * 0.88, 680) if page.height else 580,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.55, "#000000"),
                    alignment=ft.alignment.Alignment(0, 0),
                    expand=True,
                )
                page.overlay.append(ref_gc[0])
                try: page.update()
                except Exception: pass

            # ── Hemograma primeiro ─────────────────────────────────────────
            if _tem_hemograma and _eids_hemograma:
                ultima_hemo = ""
                try:
                    conn_hd = _sq2.connect(DB_PATH, timeout=30)
                    r_hd = conn_hd.execute(
                        "SELECT MAX(data_exame) FROM exames WHERE id IN (%s)"
                        % ",".join("?" * len(_eids_hemograma)), _eids_hemograma
                    ).fetchone()
                    conn_hd.close()
                    ultima_hemo = (r_hd[0] or "")[:10]
                except Exception:
                    pass
                _c_hemo = ft.Container(
                    content=ft.Row([
                        ft.Container(width=4, height=14, bgcolor=VERM, border_radius=2),
                        ft.Text("Hemograma", size=12, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True),
                        ft.Text(ultima_hemo, size=9, color=MUT),
                        ft.Icon("chevron_right_rounded", size=13, color=MUT),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.20, VERM)),
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    ink=True,
                    on_click=lambda e, _eids=_eids_hemograma: _abrir_detalhe_hemograma(_eids),
                )
                _items_lab_todos.append(_c_hemo)
                _items_lab_dados.append(("hemograma", _c_hemo))

            # ── Grupos condensados ─────────────────────────────────────────
            for gl, gcor, _, _ in _GRUPOS_COND:
                if not _gc_eids.get(gl):
                    continue
                _c_gc = _card_grupo_cond(gl, gcor, _gc_eids[gl])
                _items_lab_todos.append(_c_gc)
                _items_lab_dados.append((gl.lower(), _c_gc))

            # ── Itens soltos (não cobertos por nenhum grupo) ───────────────
            for nome, ocorrs in grupos_soltos.items():
                eids = list({o[0] for o in ocorrs})
                datas = sorted({o[1][:10] for o in ocorrs if o[1]}, reverse=True)
                ultima = datas[0] if datas else ""

                def _click_e(e, _nome=nome, _eids=eids):
                    _abrir_detalhe_exame(_nome, _eids, filtrar_parametro=_nome)

                _c = ft.Container(
                    content=ft.Row([
                        ft.Text(nome, size=12, color=TXT, weight=ft.FontWeight.W_500,
                                expand=True),
                        ft.Text(f"{len(datas)}×", size=9, color=MUT),
                        ft.Text(ultima, size=9, color=MUT),
                        ft.Icon("chevron_right_rounded", size=13, color=MUT),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD,
                    border=ft.Border(bottom=ft.BorderSide(1, BD)),
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    ink=True,
                    on_click=_click_e,
                )
                _items_lab_todos.append(_c)
                _items_lab_dados.append((nome.lower(), _c))

            # ── campo de busca + coluna dinâmica ──────────────────────────
            _col_lab = ft.Column(controls=list(_items_lab_todos), spacing=0)

            _tf_lab = ft.TextField(
                hint_text="Buscar exame...",
                prefix_icon="search_rounded",
                bgcolor=CARD, border_color=BD,
                focused_border_color=AZUL,
                hint_style=ft.TextStyle(color=MUT, size=11),
                text_size=12, height=40,
                content_padding=ft.padding.symmetric(horizontal=10, vertical=0),
                border_radius=8,
            )

            def _filtrar_lab(e):
                termo = (_tf_lab.value or "").lower().strip()
                _col_lab.controls = [
                    c for chave, c in _items_lab_dados
                    if not termo or termo in chave
                ]
                try: _col_lab.update()
                except Exception: pass

            _tf_lab.on_change = _filtrar_lab

            items_e = [_tf_lab, _col_lab]
            for ctrl in _secao_colapsavel("EXAMES DE LABORATÓRIO", AZUL, items_e, aberto=False):
                lista.controls.append(ctrl)

        # ── Exames de imagem / laudos ───────────────────────
        try:
            conn4 = _sq2.connect(DB_PATH, timeout=30)
            kw_tipo_conds  = " OR ".join(["LOWER(tipo_exame) LIKE ?"    for _ in cfg["tipo_exame"]])
            kw_medic_conds = " OR ".join(["LOWER(medico_solicit) LIKE ?" for _ in cfg["medico_kw"]])
            kw_tipo_params  = [f"%{k}%" for k in cfg["tipo_exame"]]
            kw_medic_params = [f"%{k}%" for k in cfg["medico_kw"]]
            rows_i = conn4.execute(f"""
                SELECT id, tipo_exame, data_exame
                FROM exames
                WHERE tipo != 'numerico'
                  AND (({kw_tipo_conds}) OR ({kw_medic_conds}))
                ORDER BY tipo_exame, data_exame DESC
                LIMIT 60
            """, kw_tipo_params + kw_medic_params).fetchall()
            conn4.close()
        except Exception:
            rows_i = []

        if rows_i:
            grupos_i = {}
            for eid, tipo_e, data_e in rows_i:
                nome_i = tipo_e or "Exame"
                if nome_i not in grupos_i:
                    grupos_i[nome_i] = []
                grupos_i[nome_i].append((eid, data_e))

            items_i = []
            for nome_i, ocorrs in grupos_i.items():
                eids_i = [o[0] for o in ocorrs]
                datas_i = sorted({o[1][:10] for o in ocorrs if o[1]}, reverse=True)
                ultima_i = datas_i[0] if datas_i else ""

                def _click_i(e, _nome=nome_i, _eids=eids_i):
                    _abrir_detalhe_exame(_nome, _eids)

                items_i.append(ft.Container(
                    content=ft.Row([
                        ft.Text(nome_i, size=12, color=TXT, weight=ft.FontWeight.W_500,
                                expand=True),
                        ft.Text(f"{len(datas_i)}×", size=9, color=MUT),
                        ft.Text(ultima_i, size=9, color=MUT),
                        ft.Icon("chevron_right_rounded", size=13, color=MUT),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.20, ROXO)),
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    ink=True,
                    on_click=_click_i,
                ))
            for ctrl in _secao_colapsavel("EXAMES DE IMAGEM / LAUDOS", ROXO, items_i, aberto=True):
                lista.controls.append(ctrl)

        # ── Médicos da especialidade ────────────────────────
        try:
            conn5 = _sq2.connect(DB_PATH, timeout=30)
            esp_conds  = " OR ".join(["LOWER(e.nome) LIKE ?" for _ in cfg["especialidades"]])
            kw_conds_m = " OR ".join(["LOWER(m.nome) LIKE ?" for _ in cfg["medico_kw"]])
            esp_params  = [f"%{s}%" for s in cfg["especialidades"]]
            kw_params_m = [f"%{k}%" for k in cfg["medico_kw"]]
            # médicos que aparecem em histórico relacionado ao sistema (campo medico=texto)
            hm_conds   = " OR ".join(["LOWER(hm.titulo) LIKE ? OR LOWER(hm.descricao) LIKE ?"
                                      for _ in cfg["historico_kw"]])
            hm_params  = []
            for kw in cfg["historico_kw"]:
                hm_params += [f"%{kw}%", f"%{kw}%"]
            rows_m = conn5.execute(f"""
                SELECT DISTINCT m.id, m.nome, m.crm, e.nome as esp, m.telefone
                FROM medicos m
                LEFT JOIN especialidades e ON e.id = m.especialidade_id
                WHERE m.ativo = 1 AND (
                    ({esp_conds}) OR ({kw_conds_m})
                    OR m.nome IN (
                        SELECT DISTINCT hm.medico FROM historico_medico hm
                        WHERE hm.medico IS NOT NULL AND ({hm_conds})
                    )
                )
                ORDER BY m.nome
            """, esp_params + kw_params_m + hm_params).fetchall()
            conn5.close()
        except Exception:
            rows_m = []

        items_m = []
        for mid, mnome, mcrm, mesp, mtel in rows_m:
            items_m.append(ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon("person_rounded", size=16, color=VERD),
                        bgcolor=ft.Colors.with_opacity(0.12, VERD),
                        border_radius=8, width=32, height=32,
                        alignment=ft.alignment.Alignment(0, 0),
                    ),
                    ft.Column([
                        ft.Text(mnome, size=12, color=TXT,
                                weight=ft.FontWeight.W_500),
                        ft.Text(
                            "  •  ".join(filter(None, [mesp, f"CRM {mcrm}" if mcrm else None, mtel])) or "sem dados",
                            size=10, color=SEC,
                        ),
                    ], spacing=1, tight=True, expand=True),
                ], spacing=10),
                bgcolor=CARD,
                border=ft.Border(bottom=ft.BorderSide(1, BD)),
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            ))
        if not items_m:
            items_m.append(ft.Container(
                content=ft.Row([
                    ft.Icon("person_add_rounded", size=16, color=MUT),
                    ft.Text("Nenhum médico cadastrado para esta especialidade",
                            size=11, color=MUT, italic=True),
                ], spacing=8),
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
            ))
        for ctrl in _secao_colapsavel("MÉDICOS", VERD, items_m, aberto=True):
            lista.controls.append(ctrl)

        # ── Remédios (quando cfg tem remedios_kw) ──────────────
        rows_rem = []
        if cfg.get("remedios_kw"):
            try:
                conn6 = _sq2.connect(DB_PATH, timeout=30)
                kw_rem_conds = " OR ".join(
                    ["LOWER(r.nome) LIKE ? OR LOWER(r.principio_ativo) LIKE ?"
                     for _ in cfg["remedios_kw"]]
                )
                kw_rem_params = []
                for kw in cfg["remedios_kw"]:
                    kw_rem_params += [f"%{kw}%", f"%{kw}%"]
                # também pega remédios do médico da especialidade
                if rows_m:
                    med_ids = [row[0] for row in rows_m]
                    med_ph  = ",".join("?" * len(med_ids))
                    rows_rem = conn6.execute(f"""
                        SELECT r.nome, r.principio_ativo, r.dosagem, r.ativo,
                               m.nome as medico, r.data_inicio, r.data_fim
                        FROM remedios r
                        LEFT JOIN medicos m ON m.id = r.medico_id
                        WHERE ({kw_rem_conds}) OR r.medico_id IN ({med_ph})
                        ORDER BY r.ativo DESC, r.nome
                    """, kw_rem_params + med_ids).fetchall()
                else:
                    rows_rem = conn6.execute(f"""
                        SELECT r.nome, r.principio_ativo, r.dosagem, r.ativo,
                               m.nome as medico, r.data_inicio, r.data_fim
                        FROM remedios r
                        LEFT JOIN medicos m ON m.id = r.medico_id
                        WHERE ({kw_rem_conds})
                        ORDER BY r.ativo DESC, r.nome
                    """, kw_rem_params).fetchall()
                conn6.close()
            except Exception:
                rows_rem = []

        if cfg.get("remedios_kw") is not None:
            items_rem = []
            for rnome, rprinc, rdos, rativo, rmed, rinicio, rfim in rows_rem:
                cor_r = VERD if rativo else MUT
                sub = "  •  ".join(filter(None, [
                    rprinc,
                    rdos,
                    f"desde {rinicio[:7]}" if rinicio else None,
                    rmed,
                ]))
                items_rem.append(ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Icon("medication_rounded", size=14, color=cor_r),
                            bgcolor=ft.Colors.with_opacity(0.12, cor_r),
                            border_radius=6, width=28, height=28,
                            alignment=ft.alignment.Alignment(0, 0),
                        ),
                        ft.Column([
                            ft.Text(rnome, size=12, color=TXT if rativo else MUT,
                                    weight=ft.FontWeight.W_500),
                            ft.Text(sub or "sem dados", size=9, color=SEC),
                        ], spacing=1, tight=True, expand=True),
                        ft.Container(
                            content=ft.Text("ativo" if rativo else "inativo",
                                            size=8, color=cor_r),
                            bgcolor=ft.Colors.with_opacity(0.12, cor_r),
                            border_radius=4,
                            padding=ft.padding.symmetric(horizontal=5, vertical=2),
                        ),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD,
                    border=ft.Border(bottom=ft.BorderSide(1, BD)),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                ))
            if not items_rem:
                items_rem.append(ft.Container(
                    content=ft.Row([
                        ft.Icon("medication_rounded", size=16, color=MUT),
                        ft.Text("Nenhum remédio cadastrado para esta especialidade",
                                size=11, color=MUT, italic=True),
                    ], spacing=8),
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                ))
            for ctrl in _secao_colapsavel("REMÉDIOS", AMAR, items_rem, aberto=True):
                lista.controls.append(ctrl)

        if not rows_h and not rows_e2 and not rows_i:
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("inbox_rounded", size=32, color=MUT),
                    ft.Text("Nenhum dado encontrado", size=13, color=MUT),
                    ft.Text("Processe páginas do prontuário para\npopular este sistema",
                            size=11, color=MUT, text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=8, tight=True),
                padding=ft.padding.symmetric(vertical=40),
                alignment=ft.alignment.Alignment(0, 0),
            ))

        btn_fechar = ft.Container(
            content=ft.Row([
                ft.Icon("arrow_back_rounded", size=14, color=AZUL),
                ft.Text("Voltar", size=12, color=AZUL, weight=ft.FontWeight.W_600),
            ], spacing=4, tight=True),
            ink=True, on_click=_fechar,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

        ref = [None]
        ref[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        btn_fechar,
                        ft.Icon(icone, size=16, color=cor),
                        ft.Text(label, size=15, color=TXT,
                                weight=ft.FontWeight.W_700, expand=True),
                    ], spacing=8),
                    ft.Divider(color=BD, height=1),
                    lista,
                ], spacing=0, expand=True),
                bgcolor=BG,
                border_radius=16,
                padding=ft.padding.symmetric(horizontal=16, vertical=16),
                width=440,
                height=600,
            ),
            bgcolor="#CC000000", expand=True,
            alignment=ft.Alignment(0, 0),
        )
        ref[0].on_click = _fechar
        page.overlay.append(ref[0])
        try: page.update()
        except Exception: pass

    def _card_sistema(slbl, sico, scor, scfg):
        sc = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Icon(sico, size=16, color=scor),
                    bgcolor=ft.Colors.with_opacity(0.12, scor),
                    border_radius=8, width=32, height=32,
                    alignment=ft.alignment.Alignment(0, 0),
                ),
                ft.Text(slbl, size=9, color=TXT, weight=ft.FontWeight.W_600,
                        text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               spacing=4, tight=True),
            bgcolor=CARD,
            border=ft.border.all(1, ft.Colors.with_opacity(0.25, scor)),
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=6, vertical=8),
            expand=True, ink=True,
            alignment=ft.alignment.Alignment(0, 0),
        )
        sc.on_click = lambda e, l=slbl, i=sico, c=scor, cfg=scfg: _abrir_sistema(l, i, c, cfg)
        return sc

    def _card_imagem(slbl, sico, scor, scfg, img_src, img_fit=ft.ImageFit.COVER):
        sc = ft.Container(
            content=ft.Image(
                src=img_src,
                fit=img_fit,
                width=float("inf"),
                height=float("inf"),
            ),
            bgcolor=CARD,
            border=ft.border.all(1, ft.Colors.with_opacity(0.25, scor)),
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=6, vertical=8),
            expand=True, ink=True,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            tooltip=slbl,
            height=96,
        )
        sc.on_click = lambda e, l=slbl, i=sico, c=scor, cfg=scfg: _abrir_sistema(l, i, c, cfg)
        return sc

    _CARD_IMAGENS = {
        "Ortopedia": (_asset("imagens.jpg"), ft.ImageFit.COVER),
        "Sangue":    (_asset("sangue.jpg"),  ft.ImageFit.COVER),
    }

    def _build_card(s):
        if s[0] == "Sangue":
            img_src, img_fit = _CARD_IMAGENS["Sangue"]
            card = _card_imagem("Exames de Sangue", s[1], s[2], s[3], img_src, img_fit)
            card.on_click = lambda e: _navegar(
                __import__("telas.tela_sangue", fromlist=["criar_tela_sangue"])
                .criar_tela_sangue,
                voltar_fn=_voltar_hub,
            )
            return card
        if s[0] == "Ortopedia":
            img_src, img_fit = _CARD_IMAGENS["Ortopedia"]
            card = _card_imagem("Exames (outros)", s[1], s[2], s[3], img_src, img_fit)
            card.on_click = lambda e: _navegar(
                __import__("telas.tela_imagens", fromlist=["criar_tela_imagens"])
                .criar_tela_imagens,
                voltar_fn=_voltar_hub,
            )
            return card
        if s[0] in _CARD_IMAGENS:
            img_src, img_fit = _CARD_IMAGENS[s[0]]
            return _card_imagem(s[0], s[1], s[2], s[3], img_src, img_fit)
        return _card_sistema(*s)

    # card Resumo do Dia
    _res_hub_content = ft.Image(
            src=_asset("resumo.png"), fit=ft.ImageFit.COVER,
            width=float("inf"), expand=True)

    card_resumo_hub = ft.Container(
        content=_res_hub_content,
        height=96, expand=True, border_radius=10,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        bgcolor=CARD, tooltip="Resultado Energetico",
        border=ft.border.all(1, ft.Colors.with_opacity(0.25, AZUL)),
        ink=True,
    )

    def _click_resumo_hub(e=None):
        # abre tela_rotina_diaria e dispara o overlay de resumo calorico
        from telas.tela_rotina_diaria import criar_tela_rotina_diaria
        from dados.model_prontuario import (
            listar_templates, listar_momentos,
            calcular_nutricao_momento as _cnm,
            calcular_gasto_item as _cgi,
            calcular_tmb as _ctmb,
            calcular_vitaminas_minerais_rotina as _cvmr,
            _VITS_LABEL as _VL,
            DB_PATH as _DB,
        )
        import sqlite3 as _sq3, json as _json3

        templates = listar_templates(so_ativos=True)

        # ingestão
        tot = {}
        for t in templates:
            for m in listar_momentos(t["id"]):
                n = _cnm(m["id"])
                if n:
                    for k, v in n.items():
                        if v: tot[k] = tot.get(k, 0.0) + float(v)
        kcal_in = tot.get("kcal") or 0.0

        # TMB
        tmb_d = _ctmb()
        tmb   = tmb_d.get("tmb") or 0.0
        try:
            with _sq3.connect(_DB, timeout=5) as _c3:
                rp3 = _c3.execute("SELECT peso FROM perfil_usuario LIMIT 1").fetchone()
            peso = float(rp3[0]) if rp3 and rp3[0] else 80.0
        except Exception:
            peso = 80.0

        # gasto atividades
        _TIPOS_G = {"exercicio", "trabalho", "estudo"}
        kcal_ativ = 0.0
        linhas_g  = []
        for t in templates:
            if t.get("tipo") not in _TIPOS_G: continue
            hi = t.get("hora_inicio") or ""; hf = t.get("hora_fim") or ""
            if not (hi and hf): continue
            eh_f = t.get("tipo") == "exercicio" or bool(t.get("intensidade_fisica"))
            r = _cgi(hi, hf,
                     t.get("intensidade_fisica") if eh_f else None,
                     t.get("intensidade_mental") if not eh_f else None,
                     peso)
            if not r: continue
            kcal_ativ += r["kcal_gasto"]
            h2 = r["duracao_min"] // 60; m2 = r["duracao_min"] % 60
            dur = f"{h2}h{m2:02d}min" if h2 else f"{m2}min"
            linhas_g.append((t["nome"], hi, hf, dur, r["kcal_gasto"]))

        kcal_out  = tmb + kcal_ativ
        saldo     = kcal_in - kcal_out
        cor_s     = "#3FB950" if saldo >= 0 else "#DA3633"
        sinal     = "+" if saldo >= 0 else ""

        _LAR  = "#F0883E"; _BD2 = "#30363D"

        def _row(lbl, val, unid, cor=TXT, bold=False):
            return ft.Row([
                ft.Text(lbl, size=12, color=MUT, expand=True),
                ft.Text(f"{val:.0f}" if val is not None else "—",
                        size=12, color=cor,
                        weight=ft.FontWeight.W_700 if bold else ft.FontWeight.NORMAL),
                ft.Text(f" {unid}", size=11, color=MUT),
            ], spacing=2)

        ref_ov = [None]
        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        def _abrir_ingredientes(item_nome, item_id, campo, unid, cor):
            """Nivel 2: ingredientes de um item especifico."""
            from dados.model_prontuario import (
                _porcao_em_gramas as _peg, _nutricao_proporcional as _np,
                carregar_nutricao as _cn, DB_PATH as _DB2,
            )
            import sqlite3 as _sq2

            with _sq2.connect(_DB2, timeout=5) as _c:
                ings = _c.execute("""
                    SELECT ii.id, ii.tipo, ii.descricao, ii.quantidade, ii.unidade,
                           ii.sub_receita_id, ii.calorias, ii.proteinas, ii.peso_unitario_g,
                           r.nome
                    FROM item_ingredientes ii
                    LEFT JOIN receitas r ON r.id = ii.sub_receita_id
                    WHERE ii.item_id=?
                """, (item_id,)).fetchall()

            linhas_ing = []
            for iid, tipo, desc, qty, unid_i, sub_rid, cal_m, prot_m, peso_u, rec_nome in ings:
                nome_ing = desc if tipo == "item" else (rec_nome or "Receita")
                if (unid_i or "").strip() == "Unidade" and peso_u:
                    try:    gramas = float(qty or 1) * peso_u
                    except: gramas = peso_u
                else:
                    gramas = _peg(qty, unid_i or "g")
                if tipo == "receita" and sub_rid:
                    n = _cn("receita", sub_rid)
                    ni = _np(n, gramas) if n else {}
                else:
                    n = _cn("ingrediente_item", iid)
                    ni = _np(n, gramas) if n else {}
                if not ni and cal_m:
                    ni = {"kcal": cal_m * gramas / 100,
                          "proteinas": (prot_m or 0) * gramas / 100}
                v = ni.get(campo) or 0
                qty_txt = f"{qty} {unid_i}".strip() if qty else ""
                linhas_ing.append((nome_ing, qty_txt, v))

            linhas_ing = [(n, q, v) for n, q, v in linhas_ing if v > 0]
            linhas_ing.sort(key=lambda x: x[2], reverse=True)
            total_ing = sum(x[2] for x in linhas_ing)

            ref_ing = [None]
            def _fechar_ing(e=None):
                if ref_ing[0] in page.overlay:
                    page.overlay.remove(ref_ing[0])
                try: page.update()
                except Exception: pass

            col_ing = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
            if not linhas_ing:
                col_ing.controls.append(
                    ft.Text("Sem detalhamento de ingredientes.", size=12, color=MUT))
            else:
                for nome_ing, qty_txt, v in linhas_ing:
                    pct = (v / total_ing * 100) if total_ing else 0
                    card = ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(nome_ing, size=12, color=TXT, expand=True),
                                ft.Text(f"{v:.1f}".rstrip("0").rstrip("."),
                                        size=13, color=cor, weight=ft.FontWeight.W_700),
                                ft.Text(f" {unid}", size=11, color=MUT),
                            ], spacing=2),
                            ft.Row([
                                ft.Text(qty_txt, size=10, color=MUT, expand=True),
                                ft.Text(f"{pct:.0f}%", size=10, color=MUT),
                            ], spacing=2),
                            ft.ProgressBar(value=pct/100, color=cor,
                                           bgcolor=_BD2, height=3),
                        ], spacing=3, tight=True),
                        bgcolor=CARD, border_radius=8,
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        border=ft.Border(
                            left=ft.BorderSide(2, cor),
                            top=ft.BorderSide(1, _BD2), bottom=ft.BorderSide(1, _BD2),
                            right=ft.BorderSide(1, _BD2)),
                    )
                    col_ing.controls.append(card)

                col_ing.controls.append(ft.Container(height=4))
                col_ing.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Text("TOTAL", size=11, color=MUT,
                                weight=ft.FontWeight.W_700, expand=True),
                        ft.Text(f"{total_ing:.1f}".rstrip("0").rstrip("."),
                                size=14, color=cor, weight=ft.FontWeight.W_900),
                        ft.Text(f" {unid}", size=11, color=MUT),
                    ], spacing=2),
                    bgcolor=CARD, border_radius=8,
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    border=ft.Border(
                        left=ft.BorderSide(3, cor),
                        top=ft.BorderSide(1, _BD2), bottom=ft.BorderSide(1, _BD2),
                        right=ft.BorderSide(1, _BD2)),
                ))

            from shared.layout import Layout as _Lay4
            _lay4 = _Lay4(page)
            _cab_ing = _lay4.criar_cabecalho(
                item_nome, _fechar_ing,
                icone_titulo="format_list_bulleted_rounded", cor_titulo=cor)
            ref_ing[0] = ft.Container(
                content=ft.Column([
                    ft.Container(height=_lay4.spacer_topo, bgcolor=BG),
                    _cab_ing,
                    ft.Container(
                        content=col_ing, expand=True,
                        padding=ft.padding.symmetric(horizontal=16, vertical=8)),
                ], spacing=0, expand=True),
                bgcolor=BG, expand=True)
            page.overlay.append(ref_ing[0])
            try: page.update()
            except Exception: pass

        def _abrir_analitico(titulo, campo, unid, cor):
            """Nivel 1: template > item > valor. Click no item abre nivel 2 (ingredientes)."""
            from dados.model_prontuario import (
                calcular_nutricao_item as _cni2,
                DB_PATH as _DB2,
            )
            import sqlite3 as _sq2

            # monta lista: (tnome, iid, desc, qty, unid_item, val)
            linhas = []
            for t in templates:
                for m in listar_momentos(t["id"]):
                    with _sq2.connect(_DB2, timeout=5) as _c:
                        itens_m = _c.execute(
                            "SELECT id, descricao, quantidade, unidade FROM itens_momento WHERE momento_id=?",
                            (m["id"],)
                        ).fetchall()
                    for iid, desc, qty, unid_item in itens_m:
                        ni = _cni2(iid)
                        v = ni.get(campo)
                        if v:
                            linhas.append((t["nome"], iid, desc, qty, unid_item, float(v)))

            linhas.sort(key=lambda x: x[5], reverse=True)
            total = sum(x[5] for x in linhas)

            ref_an = [None]
            def _fechar_an(e=None):
                if ref_an[0] in page.overlay:
                    page.overlay.remove(ref_an[0])
                try: page.update()
                except Exception: pass

            col_itens = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
            if not linhas:
                col_itens.controls.append(
                    ft.Text("Nenhum item com dados nutricionais.", size=12, color=MUT))
            else:
                template_atual = ""
                for tnome, iid, desc, qty, unid_item, val in linhas:
                    if tnome != template_atual:
                        template_atual = tnome
                        col_itens.controls.append(ft.Container(
                            content=ft.Row([
                                ft.Icon("restaurant_rounded", size=11, color=VERD),
                                ft.Text(tnome, size=10, color=VERD,
                                        weight=ft.FontWeight.W_700),
                            ], spacing=4),
                            padding=ft.padding.only(top=6, bottom=2)))
                    pct = (val / total * 100) if total else 0
                    qty_txt = f"{qty} {unid_item}".strip() if qty else ""
                    card = ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(desc or "—", size=12, color=TXT, expand=True),
                                ft.Text(f"{val:.1f}".rstrip("0").rstrip("."),
                                        size=13, color=cor, weight=ft.FontWeight.W_700),
                                ft.Text(f" {unid}", size=11, color=MUT),
                                ft.Icon("chevron_right_rounded", size=12, color=MUT),
                            ], spacing=2),
                            ft.Row([
                                ft.Text(qty_txt, size=10, color=MUT, expand=True),
                                ft.Text(f"{pct:.0f}%", size=10, color=MUT),
                            ], spacing=2),
                            ft.ProgressBar(value=pct/100, color=cor,
                                           bgcolor=_BD2, height=3),
                        ], spacing=3, tight=True),
                        bgcolor=CARD, border_radius=8, ink=True,
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        border=ft.Border(
                            left=ft.BorderSide(2, cor),
                            top=ft.BorderSide(1, _BD2), bottom=ft.BorderSide(1, _BD2),
                            right=ft.BorderSide(1, _BD2)),
                    )
                    card.on_click = lambda e, n=desc, i=iid, _c=campo, _u=unid, _cr=cor: \
                        _abrir_ingredientes(n or "Item", i, _c, _u, _cr)
                    col_itens.controls.append(card)

                col_itens.controls.append(ft.Container(height=4))
                col_itens.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Text("TOTAL", size=11, color=MUT,
                                weight=ft.FontWeight.W_700, expand=True),
                        ft.Text(f"{total:.1f}".rstrip("0").rstrip("."),
                                size=14, color=cor, weight=ft.FontWeight.W_900),
                        ft.Text(f" {unid}", size=11, color=MUT),
                    ], spacing=2),
                    bgcolor=CARD, border_radius=8,
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    border=ft.Border(
                        left=ft.BorderSide(3, cor),
                        top=ft.BorderSide(1, _BD2), bottom=ft.BorderSide(1, _BD2),
                        right=ft.BorderSide(1, _BD2)),
                ))

            from shared.layout import Layout as _Lay3
            _lay3 = _Lay3(page)
            _cab_an = _lay3.criar_cabecalho(titulo, _fechar_an,
                                            icone_titulo="analytics_rounded",
                                            cor_titulo=cor)
            ref_an[0] = ft.Container(
                content=ft.Column([
                    ft.Container(height=_lay3.spacer_topo, bgcolor=BG),
                    _cab_an,
                    ft.Container(
                        content=col_itens, expand=True,
                        padding=ft.padding.symmetric(horizontal=16, vertical=8)),
                ], spacing=0, expand=True),
                bgcolor=BG, expand=True)
            page.overlay.append(ref_an[0])
            try: page.update()
            except Exception: pass

        def _row_click(lbl, val, unid, cor=TXT, bold=False, campo=None):
            """Linha clicavel — abre analitico se campo fornecido."""
            txt_val = ft.Text(
                f"{val:.0f}" if val is not None else "—",
                size=12, color=cor,
                weight=ft.FontWeight.W_700 if bold else ft.FontWeight.NORMAL)
            row = ft.Container(
                content=ft.Row([
                    ft.Text(lbl, size=12, color=MUT, expand=True),
                    txt_val,
                    ft.Text(f" {unid}", size=11, color=MUT),
                    ft.Icon("chevron_right_rounded", size=12, color=MUT)
                    if campo else ft.Container(width=12),
                ], spacing=2),
                border_radius=6, ink=bool(campo),
                padding=ft.padding.symmetric(vertical=2),
            )
            if campo:
                row.on_click = lambda e, l=lbl, c=campo, u=unid, cr=cor: \
                    _abrir_analitico(l, c, u, cr)
            return row

        from shared.layout import Layout as _Lay2
        _lay2 = _Lay2(page)
        cab = _lay2.criar_cabecalho("Resumo do Dia", _fechar,
                                    icone_titulo="balance_rounded", cor_titulo=AZUL)

        area = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

        # TMB
        _tmb_completo = tmb_d.get("completo")
        _tmb_info = (f"Mifflin-St Jeor · {tmb_d['sexo']} · {tmb_d['idade']} anos · "
                     f"{peso:.0f}kg · {tmb_d['altura']:.0f}cm"
                     if _tmb_completo
                     else "Complete o perfil: peso, altura, data nasc. e sexo")

        # vitaminas e minerais
        _vits, _mins = _cvmr()

        # ingestão — macros + micronutrientes
        def _card_micro(titulo, icone, cor, dados):
            aberto = [False]
            rows_dados = [ft.Row([
                ft.Text(_VL.get(k, k), size=11, color=SEC, expand=True),
                ft.Text(f"{v:.1f}".rstrip("0").rstrip("."),
                        size=12, color=TXT, weight=ft.FontWeight.W_600),
                ft.Text(f" {u}", size=10, color=MUT),
            ], spacing=2)
            for k, (v, u) in sorted(dados.items(), key=lambda x: _VL.get(x[0], x[0]))]
            corpo_col = ft.Column(rows_dados, spacing=4, visible=False)
            seta = ft.Icon("expand_more_rounded", size=14, color=cor)
            def _tog(e=None):
                aberto[0] = not aberto[0]
                corpo_col.visible = aberto[0]
                seta.name = "expand_less_rounded" if aberto[0] else "expand_more_rounded"
                try: page.update()
                except Exception: pass
            cab = ft.Container(
                content=ft.Row([
                    ft.Icon(icone, size=13, color=cor),
                    ft.Text(titulo, size=10, color=cor, weight=ft.FontWeight.W_700, expand=True),
                    ft.Text(f"{len(dados)} itens", size=10, color=MUT),
                    seta,
                ], spacing=6), ink=True,
            )
            cab.on_click = _tog
            return ft.Column([
                ft.Divider(height=1, color=_BD2),
                cab, corpo_col,
            ], spacing=4, tight=True)

        _micro_widgets = []
        if _vits:
            _micro_widgets.append(_card_micro("VITAMINAS", "science_rounded", ROXO, _vits))
        if _mins:
            _micro_widgets.append(_card_micro("MINERAIS", "diamond_rounded", AZUL, _mins))

        area.controls.append(ft.Container(
            content=ft.Column([
                ft.Row([ft.Icon("restaurant_rounded", size=14, color=VERD),
                        ft.Text("INGESTÃO", size=10, color=VERD, weight=ft.FontWeight.W_700)], spacing=6),
                ft.Divider(height=1, color=VERD),
                _row_click("Energia",      kcal_in,                "kcal", _LAR, True,  "kcal"),
                _row_click("Carboidratos", tot.get("carboidratos"), "g",   TXT,  False, "carboidratos"),
                _row_click("Proteínas",    tot.get("proteinas"),    "g",   VERD, True,  "proteinas"),
                _row_click("Gorduras",     tot.get("gorduras"),     "g",   TXT,  False, "gorduras"),
                _row_click("Fibras",       tot.get("fibras"),       "g",   TXT,  False, "fibras"),
                _row_click("Sódio",        tot.get("sodio"),        "mg",  TXT,  False, "sodio"),
                *_micro_widgets,
            ], spacing=6, tight=True),
            bgcolor=CARD, border_radius=10, padding=ft.padding.all(14),
            border=ft.Border(top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                             left=ft.BorderSide(3, VERD), right=ft.BorderSide(1, BD))))

        # gasto atividades
        linhas_ctrl = [
            ft.Row([ft.Icon("local_fire_department_rounded", size=12, color=VERM),
                    ft.Text(nome, size=12, color=TXT, expand=True),
                    ft.Text(f"{hi}–{hf}  {dur}", size=10, color=MUT),
                    ft.Text(f"−{kcal:.0f} kcal", size=12, color=VERM,
                            weight=ft.FontWeight.W_600)], spacing=6)
            for nome, hi, hf, dur, kcal in linhas_g
        ] or [ft.Text("Nenhuma atividade com horario definido.", size=11, color=MUT)]

        area.controls.append(ft.Container(
            content=ft.Column([
                ft.Row([ft.Icon("directions_run_rounded", size=14, color=VERM),
                        ft.Text("GASTO POR ATIVIDADE", size=10, color=VERM,
                                weight=ft.FontWeight.W_700)], spacing=6),
                ft.Divider(height=1, color=VERM),
                *linhas_ctrl,
                ft.Divider(height=1, color=_BD2),
                _row("Atividades",        kcal_ativ, "kcal", VERM, True),
                ft.Row([
                    ft.Text("TMB (basal)", size=12, color=MUT, expand=True),
                    ft.Text(f"−{tmb:.0f}" if _tmb_completo else "—",
                            size=12, color=VERM if _tmb_completo else MUT,
                            weight=ft.FontWeight.W_700 if _tmb_completo else ft.FontWeight.NORMAL),
                    ft.Text(" kcal" if _tmb_completo else "", size=11, color=MUT),
                ], spacing=2),
                ft.Text(_tmb_info, size=9, color=MUT if _tmb_completo else _LAR),
                _row("Gasto total do dia", kcal_out,  "kcal", VERM, True),
            ], spacing=6, tight=True),
            bgcolor=CARD, border_radius=10, padding=ft.padding.all(14),
            border=ft.Border(top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                             left=ft.BorderSide(3, VERM), right=ft.BorderSide(1, BD))))

        # saldo
        icon_s = "trending_up_rounded" if saldo >= 0 else "trending_down_rounded"
        area.controls.append(ft.Container(
            content=ft.Column([
                ft.Row([ft.Icon("balance_rounded", size=14, color=AZUL),
                        ft.Text("SALDO DO DIA", size=10, color=AZUL,
                                weight=ft.FontWeight.W_700)], spacing=6),
                ft.Divider(height=1, color=AZUL),
                ft.Row([ft.Icon(icon_s, size=20, color=cor_s),
                        ft.Text(f"{sinal}{saldo:.0f} kcal", size=22, color=cor_s,
                                weight=ft.FontWeight.W_900)], spacing=8,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([ft.Text("Ingestão", size=11, color=MUT, expand=True),
                        ft.Text(f"+{kcal_in:.0f} kcal", size=11, color=_LAR)], spacing=4),
                ft.Row([ft.Text("Gasto", size=11, color=MUT, expand=True),
                        ft.Text(f"−{kcal_out:.0f} kcal", size=11, color=VERM)], spacing=4),
                ft.ProgressBar(
                    value=min(kcal_in / kcal_out, 1.0) if kcal_out > 0 else 1.0,
                    color=cor_s, bgcolor=_BD2, height=6),
            ], spacing=8, tight=True),
            bgcolor=CARD, border_radius=10, padding=ft.padding.all(14),
            border=ft.Border(top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                             left=ft.BorderSide(3, AZUL), right=ft.BorderSide(1, BD))))

        ref_ov[0] = ft.Container(
            content=ft.Column([
                ft.Container(height=_lay2.spacer_topo, bgcolor=BG),
                cab,
                ft.Container(content=area, expand=True,
                             padding=ft.padding.symmetric(horizontal=16, vertical=8)),
            ], spacing=0, expand=True),
            bgcolor=BG, expand=True)
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass

    card_resumo_hub.on_click = _click_resumo_hub

    # card Checkup com imagem
    card_checkup_hub = ft.Container(
        content=ft.Image(
            src=_asset("checkup.jpg"), fit=ft.ImageFit.COVER,
            width=float("inf"), height=float("inf"),
        ),
        bgcolor=CARD,
        border=ft.border.all(1, ft.Colors.with_opacity(0.25, VERD)),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=6, vertical=8),
        expand=True, ink=True,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        tooltip="Checkup de Saúde",
        height=96,
    )
    card_checkup_hub.on_click = lambda e: _navegar(
        __import__("telas.tela_checkup", fromlist=["criar_tela_checkup"])
        .criar_tela_checkup,
        voltar_fn=_voltar_hub,
    )

    # sistemas que NAO estao na silhueta + resumo + checkup em rows de 4
    _SISTEMAS_SILHUETA = {"Cardiaco", "Visceral", "Psiquiatria", "Visão & Audição"}
    _todos = [s for s in _SISTEMAS if s[0] not in _SISTEMAS_SILHUETA] + [None, "checkup"]
    _rows_sis = []
    for i in range(0, len(_todos), 4):
        grupo = _todos[i:i+4]
        cards = []
        for s in grupo:
            if s is None:
                cards.append(card_resumo_hub)
            elif s == "checkup":
                cards.append(card_checkup_hub)
            else:
                cards.append(_build_card(s))
        # preencher linha se menos de 4
        while len(cards) < 4:
            cards.append(ft.Container(expand=True))
        _rows_sis.append(ft.Row(cards, spacing=8))

    row_sistemas = ft.Column(_rows_sis, spacing=8)

    # ══════════════════════════════════════════════════════════
    # RESUMO — Linha do Tempo, Remédios, Rotina, Consultas
    # ══════════════════════════════════════════════════════════
    txt_n_eventos   = ft.Text("--", size=15, weight=ft.FontWeight.W_700, color=VERM)
    txt_n_diag      = ft.Text("--", size=15, weight=ft.FontWeight.W_700, color=AMAR)
    txt_n_remedios  = ft.Text("--", size=15, weight=ft.FontWeight.W_700, color=VERD)
    txt_n_rotinas   = ft.Text("--", size=15, weight=ft.FontWeight.W_700, color=AZUL)
    txt_n_consultas = ft.Text("--", size=15, weight=ft.FontWeight.W_700, color=ROXO)

    def _card_resumo(val_ctrl, label, icone, cor, fn):
        c = ft.Container(
            content=ft.Column([
                ft.Icon(icone, size=14, color=cor),
                val_ctrl,
                ft.Text(label, size=8, color=SEC, text_align=ft.TextAlign.CENTER),
            ], alignment=ft.MainAxisAlignment.CENTER,
               horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               spacing=3, tight=True),
            bgcolor=CARD, border=ft.border.all(1, BD),
            border_radius=8, padding=7, expand=True, height=72,
            alignment=ft.alignment.Alignment(0, 0), ink=True,
        )
        c.on_click = lambda e: fn()
        return c

    row_resumo = ft.Column([
        ft.Row([
            _card_resumo(txt_n_eventos,  "Historico",   "timeline_rounded",      VERM,
                         _lazy_fn("tela_historico_clinico", "criar_tela_historico_clinico",
                                  readonly=modo_medico)),
            _card_resumo(txt_n_diag,     "Diagnosticos","analytics_rounded",      AMAR,
                         _lazy_fn("tela_diagnosticos", "criar_tela_diagnosticos")),
            _card_resumo(txt_n_remedios, "Medicacao",   "medication_rounded",     VERD,
                         _lazy_fn("tela_remedios", "criar_tela_remedios", readonly=True)),
        ], spacing=8, height=72),
        ft.Row([
            _card_resumo(txt_n_rotinas,  "Rotinas","today_rounded", AZUL,
                         _lazy_fn("tela_rotina_diaria", "criar_tela_rotina_diaria")),
            _card_resumo(txt_n_consultas,"Compromissos", "event_note_rounded",     ROXO,
                         _lazy_fn("tela_compromissos", "criar_tela_compromissos")),
        ], spacing=8, height=72, visible=not modo_medico),
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
                            "fase": "_tick", "txt": f"Backup em {restante}",
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
            _iniciar_countdown(); return
        _parar_countdown()
        if fase == "_tick":
            txt_sync.value = msg.get("txt", "")
            txt_sync.color = AMAR; ico_sync.color = AMAR
            ico_sync.name  = "cloud_sync_rounded"
        elif fase == "executando":
            txt_sync.value = "Fazendo backup..."
            txt_sync.color = AZUL; ico_sync.color = AZUL
            ico_sync.name  = "cloud_upload_rounded"
        elif fase == "concluido":
            txt_sync.value = "Backup concluido"
            txt_sync.color = VERD; ico_sync.color = VERD
            ico_sync.name  = "cloud_done_rounded"
        elif fase == "erro":
            txt_sync.value = f"Erro: {msg.get('msg', '')[:50]}"
            txt_sync.color = VERM; ico_sync.color = VERM
            ico_sync.name  = "cloud_off_rounded"
        else:
            txt = msg.get("msg", "")
            txt_sync.value = txt[:60] if txt else "Backup automatico ativo"
            txt_sync.color = VERD; ico_sync.color = VERD
            ico_sync.name  = "cloud_done_rounded"
        _atualizar_ui()

    page.pubsub.subscribe_topic("_backup_status", _on_backup_status)

    row_sync = ft.Container(
        content=ft.Row([ico_sync, txt_sync, ft.Container(expand=True)], spacing=6),
        bgcolor=BG,
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
        border=ft.Border(top=ft.BorderSide(1, BD)),
    )

    # ══════════════════════════════════════════════════════════
    # ABAS
    # ══════════════════════════════════════════════════════════
    ABAS = [
        ("Inicio",  "home_rounded",              AZUL),
        ("Exames",  "folder_open_rounded",       ROXO),
        ("Clinico", "health_and_safety_rounded", VERD),
    ] if modo_medico else [
        ("Inicio",  "home_rounded",              AZUL),
        ("Exames",  "folder_open_rounded",       ROXO),
        ("Clinico", "health_and_safety_rounded", VERD),
        ("Mais",    "grid_view_rounded",         SEC),
    ]
    barra_abas_row = ft.Row(spacing=0)
    area_conteudo  = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    def _rebuild_abas():
        barra_abas_row.controls.clear()
        for i, (label, icone, cor) in enumerate(ABAS):
            ativa = aba_ativa[0] == i
            # no modo_medico a aba Clínico (idx=2) fica desabilitada
            desabilitada = modo_medico and label == "Clinico"
            cor_ef  = MUT if desabilitada else (cor if ativa else MUT)
            peso_ef = ft.FontWeight.W_400 if desabilitada else (
                      ft.FontWeight.W_600 if ativa else ft.FontWeight.W_400)
            tab = ft.Container(
                content=ft.Column([
                    ft.Icon(icone, size=20, color=cor_ef),
                    ft.Text(label, size=9, color=cor_ef, weight=peso_ef),
                ], alignment=ft.MainAxisAlignment.CENTER,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=2),
                expand=True,
                border=ft.Border(top=ft.BorderSide(2, cor if ativa else "transparent")),
                padding=ft.padding.symmetric(vertical=8),
                alignment=ft.alignment.Alignment(0, 0),
                ink=not desabilitada,
                opacity=0.35 if desabilitada else 1.0,
            )
            if not desabilitada:
                tab.on_click = lambda e, idx=i: _trocar_aba(idx)
            barra_abas_row.controls.append(tab)

    # ── Silhueta anatomica ───────────────────────────────────
    def _criar_widget_silhueta():
        try:
            from telas.silhueta_orgaos import criar_silhueta
            _pw = page.width or 0
            _pw = _pw if _pw > 100 else 360
            # desktop: silhueta ocupa o espaco restante apos coluna esq (300px) + padding
            if modo_medico and _pw >= 600:
                larg = min(int(_pw - 300 - 48), 600)
                larg = max(larg, 280)
            else:
                larg = min(int(_pw - 32), 400)

            # Mapa orgao -> (label, icone, cor, cfg_sistema)
            def _cfg(label):
                return next((cfg for lbl, ico, cor, cfg in _SISTEMAS if lbl == label), {})
            def _ico(label):
                return next((ico for lbl, ico, cor, cfg in _SISTEMAS if lbl == label), "")
            def _cor(label):
                return next((cor for lbl, ico, cor, cfg in _SISTEMAS if lbl == label), SEC)

            _ORGAO_SISTEMA = {
                "coracao":  ("Cardiaco", _ico("Cardiaco"), _cor("Cardiaco"), _cfg("Cardiaco")),
                "coracao2": ("Cardiaco", _ico("Cardiaco"), _cor("Cardiaco"), _cfg("Cardiaco")),
                "visceral": ("Visceral",    _ico("Visceral"),    _cor("Visceral"),    _cfg("Visceral")),
                "cerebro":  ("Psiquiatria",    _ico("Psiquiatria"),    _cor("Psiquiatria"),    _cfg("Psiquiatria")),
                "olhos":    ("Visão & Audição", _ico("Visão & Audição"), _cor("Visão & Audição"), _cfg("Visão & Audição")),
                "urinario": None,  # TODO: tela urinario/prostata/penis a definir
            }

            def _on_orgao(nome_id: str):
                entry = _ORGAO_SISTEMA.get(nome_id)
                if entry is None:
                    # Orgao mapeado mas tela ainda nao definida
                    snack = ft.SnackBar(
                        content=ft.Text("Em desenvolvimento...", color="#E6EDF3"),
                        bgcolor="#161B22",
                    )
                    page.overlay.append(snack)
                    snack.open = True
                    try: page.update()
                    except Exception: pass
                elif entry:
                    _abrir_sistema(entry[0], entry[1], entry[2], entry[3])

            return ft.Container(
                content=ft.Column([
                    ft.Text(
                        "Clique no Órgão que Deseja Pesquisar",
                        size=12, color=SEC, text_align="center",
                        weight=ft.FontWeight.W_600,
                    ),
                    ft.Container(height=6),
                    criar_silhueta(
                        page,
                        on_orgao_click=_on_orgao,
                        largura=larg,
                        mostrar_borda=False,
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=0, tight=True),
                alignment=ft.alignment.center,
                padding=ft.padding.symmetric(vertical=8),
            )
        except Exception as ex:
            log.warning("[HUB] silhueta erro: %s", ex)
            return ft.Container(height=0)

    _widget_silhueta = _criar_widget_silhueta()

    # ── ABA 0: Inicio ────────────────────────────────────────
    _claudia_aberta = [False]
    _monitor_aberto = [False]
    _resumo_aberto  = [False]

    _claudia_corpo  = ft.Column([card_claudia],     visible=False, spacing=0)
    _monitor_corpo  = ft.Column([card_monitor_uti], visible=False, spacing=0)
    _resumo_corpo   = ft.Column([row_resumo],       visible=False, spacing=8)

    _ico_claudia = ft.Icon("expand_more_rounded", size=14, color=ROXO)
    _ico_monitor = ft.Icon("expand_more_rounded", size=14, color=SEC)
    _ico_resumo  = ft.Icon("expand_more_rounded", size=14, color=ROXO)

    def _toggle_claudia(e=None):
        _claudia_aberta[0] = not _claudia_aberta[0]
        _claudia_corpo.visible = _claudia_aberta[0]
        _ico_claudia.name = ("expand_less_rounded" if _claudia_aberta[0]
                             else "expand_more_rounded")
        try: page.update()
        except Exception: pass

    def _toggle_monitor(e=None):
        _monitor_aberto[0] = not _monitor_aberto[0]
        _monitor_corpo.visible = _monitor_aberto[0]
        _ico_monitor.name = ("expand_less_rounded" if _monitor_aberto[0]
                             else "expand_more_rounded")
        try: page.update()
        except Exception: pass

    def _toggle_resumo(e=None):
        _resumo_aberto[0] = not _resumo_aberto[0]
        _resumo_corpo.visible = _resumo_aberto[0]
        _ico_resumo.name = ("expand_less_rounded" if _resumo_aberto[0]
                            else "expand_more_rounded")
        try: page.update()
        except Exception: pass

    _header_claudia = ft.Container(
        content=ft.Row([
            ft.Icon("auto_awesome_rounded", size=12, color=ROXO),
            ft.Text("CLAUDIA", size=10, weight=ft.FontWeight.W_700, color=ROXO),
            ft.Container(expand=True),
            _ico_claudia,
        ], spacing=6),
        padding=ft.padding.symmetric(horizontal=4, vertical=4),
        border_radius=8, ink=True,
    )
    _header_claudia.on_click = _toggle_claudia

    _header_monitor = ft.Container(
        content=ft.Row([
            ft.Icon("monitor_heart_rounded", size=12, color="#FF7675"),
            ft.Text("MONITOR VITAL", size=10, weight=ft.FontWeight.W_700, color=SEC),
            ft.Container(expand=True),
            _ico_monitor,
        ], spacing=6),
        padding=ft.padding.symmetric(horizontal=4, vertical=4),
        border_radius=8, ink=True,
    )
    _header_monitor.on_click = _toggle_monitor

    _header_resumo = ft.Container(
        content=ft.Row([
            ft.Icon("insights_rounded", size=12, color=ROXO),
            ft.Text("RESUMO", size=10, weight=ft.FontWeight.W_700, color=ROXO),
            ft.Container(expand=True),
            _ico_resumo,
        ], spacing=6),
        padding=ft.padding.symmetric(horizontal=4, vertical=4),
        border_radius=8, ink=True,
    )
    _header_resumo.on_click = _toggle_resumo

    def _conteudo_inicio():
        topo = [card_claudia] if modo_medico else [_header_claudia, _claudia_corpo]
        _pw = page.width or 0

        # layout desktop: coluna esquerda (conteudo) + silhueta direita
        # apenas no modo_medico (web) -- no app normal fica sempre empilhado
        if modo_medico and _pw >= 600:
            col_esq = ft.Column([
                *topo,
                _header_monitor,
                _monitor_corpo,
                _header_resumo,
                _resumo_corpo,
                _secao_titulo("SISTEMAS", "category_rounded", AZUL),
                row_sistemas,
            ], spacing=8, width=300, scroll=ft.ScrollMode.AUTO)

            return [
                ft.Row([
                    col_esq,
                    ft.Container(
                        content=_widget_silhueta,
                        expand=True,
                        alignment=ft.alignment.center,
                    ),
                ], spacing=16,
                   vertical_alignment=ft.CrossAxisAlignment.START,
                   expand=True),
            ]

        # layout mobile: empilhado
        return [
            *topo,
            _header_monitor,
            _monitor_corpo,
            _header_resumo,
            _resumo_corpo,
            _secao_titulo("SISTEMAS", "category_rounded", AZUL),
            _widget_silhueta,
            row_sistemas,
        ]

    # ── ABA 2: Clinico ───────────────────────────────────────
    def _conteudo_clinico():
        def _btn_item(icone, label, desc, cor, fn):
            c = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(icone, size=15, color=cor),
                        bgcolor=ft.Colors.with_opacity(0.10, cor),
                        border_radius=8, width=32, height=32,
                        alignment=ft.alignment.Alignment(0, 0),
                    ),
                    ft.Column([
                        ft.Text(label, size=13, color=TXT, weight=ft.FontWeight.W_500),
                        ft.Text(desc,  size=10, color=SEC),
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

        if modo_medico:
            itens = [
                _btn_item("medication_rounded", "Medicacao",
                          "Remedios e suplementos", AMAR,
                          _lazy_fn("tela_remedios", "criar_tela_remedios", readonly=True)),
                _btn_item("timeline_rounded", "Historico Clinico",
                          "Linha do tempo e alertas clinicos", VERM,
                          _lazy_fn("tela_historico_clinico", "criar_tela_historico_clinico",
                                   readonly=True)),
                _btn_item("folder_open_rounded", "Prontuarios",
                          "PDFs importados e paginas", ROXO,
                          _lazy_fn("tela_prontuarios", "criar_tela_prontuarios")),
                _btn_item("analytics_rounded", "Diagnosticos",
                          "CID, certeza e tipo por internacao", AMAR,
                          _lazy_fn("tela_diagnosticos", "criar_tela_diagnosticos")),
            ]
        else:
            itens = [
                _btn_item("health_and_safety_rounded", "Checkup de Saude",
                          "Visao geral — alertas, sistemas e tendencias", VERD,
                          _lazy_fn("tela_checkup", "criar_tela_checkup")),
                _btn_item("favorite_rounded", "Sistema Cardiaco",
                          "Diagnosticos, exames, historico, medicos e remedios",
                          "#FF6B6B",
                          _lazy_fn("tela_orgao_cardiaco",
                                   "criar_tela_orgao_cardiaco")),
                _btn_item("diagnosis_rounded", "Diagnosticos",
                          "Todos os diagnosticos medicos", AZUL,
                          _lazy_fn("tela_diagnosticos",
                                   "criar_tela_diagnosticos")),
                _btn_item("event_note_rounded", "Compromissos",
                          "Consultas, coletas e fisioterapia", VERD,
                          _lazy_fn("tela_compromissos", "criar_tela_compromissos")),
                _btn_item("medication_rounded", "Medicacao",
                          "Remedios e suplementos", AMAR,
                          _lazy_fn("tela_remedios", "criar_tela_remedios")),
                _btn_item("storefront_rounded", "Fornecedores",
                          "Farmacias e fornecedores", ROXO,
                          _lazy_fn("tela_fornecedores", "criar_tela_fornecedores")),
                _btn_item("today_rounded", "Rotinas Diarias",
                          "Agua do dia e rotinas de habitos", AZUL,
                          _lazy_fn("tela_rotina_diaria", "criar_tela_rotina_diaria")),
                _btn_item("psychology_rounded", "Claudia IA",
                          "Conversar com Claudia", ROXO,
                          _lazy_fn("tela_claudia", "criar_tela_claudia")),
                _btn_item("biotech_rounded", "Marcadores",
                          "Sinais vitais e historico", "#4ECDC4",
                          _lazy_fn("tela_marcadores", "criar_tela_marcadores")),
                _btn_item("timeline_rounded", "Historico Clinico",
                          "Linha do tempo e alertas clinicos", VERM,
                          _lazy_fn("tela_historico_clinico", "criar_tela_historico_clinico")),
                _btn_item("folder_open_rounded", "Prontuarios",
                          "PDFs importados e paginas", ROXO,
                          _lazy_fn("tela_prontuarios", "criar_tela_prontuarios")),
                _btn_item("analytics_rounded", "Diagnosticos",
                          "CID, certeza e tipo por internacao", AMAR,
                          _lazy_fn("tela_diagnosticos", "criar_tela_diagnosticos")),
            ]
        return [
            ft.Container(
                content=ft.Column(itens, spacing=0),
                bgcolor=CARD, border_radius=12,
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
                        bgcolor=ft.Colors.with_opacity(0.10, cor),
                        border_radius=8, width=32, height=32,
                        alignment=ft.alignment.Alignment(0, 0),
                    ),
                    ft.Column([
                        ft.Text(label, size=13, color=TXT, weight=ft.FontWeight.W_500),
                        ft.Text(desc,  size=10, color=SEC),
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
                        ft.Text(titulo, size=10, weight=ft.FontWeight.W_700, color=cor),
                    ], spacing=6),
                    padding=ft.padding.only(bottom=6, top=4),
                ),
                ft.Container(
                    content=ft.Column(items, spacing=0),
                    bgcolor=CARD, border_radius=12,
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
                      lambda: _navegar(_tela_incluir_exame, _voltar_hub)),
                _item("analytics_rounded", "Historico",
                      "Graficos e evolucao", VERD,
                      _lazy_fn("tela_exames", "criar_tela_consulta")),
                _item("description_rounded", "Processados",
                      "Exames importados", AMAR,
                      _lazy_fn("tela_exames_processados", "criar_tela_exames_processados")),
                _item("science_rounded", "Exames Padrao",
                      "Referencias e cadastro", ROXO,
                      _lazy_fn("tela_exames_padrao", "criar_tela_exames_padrao")),
                _item("local_hospital_rounded", "Especialidades",
                      "Areas medicas", AMAR,
                      _lazy_fn("tela_especialidades", "criar_tela_especialidades")),
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
                _item("storefront_rounded", "Fornecedores",
                      "Farmacias e fornecedores", VERD,
                      _lazy_fn("tela_fornecedores", "criar_tela_fornecedores")),
                _item("link_rounded", "Links Medico",
                      "Tokens de acesso", AZUL,
                      _lazy_fn("tela_links_medico", "criar_tela_links_medico")),
                _item("medical_services_rounded", "Visao Medico",
                      "Hub do medico (teste)", ROXO,
                      lambda: _navegar(
                          lambda p, v: __import__(
                              "telas.tela_hub_medico",
                              fromlist=["criar_tela_hub_medico"]
                          ).criar_tela_hub_medico(p, v, None),
                          _voltar_hub)),
            ]),
            _group("CONFIGURACOES", SEC, "settings_rounded", [
                _item("person_rounded", "Perfil", "Dados pessoais", SEC, _nav_perfil),
                _item("settings_rounded", "Configuracoes",
                      "Backup e Drive", SEC,
                      _lazy_fn("telas_sistema.tela_config", "criar_tela_config")),
            ]),
        ]

    def _rebuild_conteudo():
        area_conteudo.controls.clear()
        idx = aba_ativa[0]
        if idx == 0:
            # garante estado consistente dos dropdowns
            _claudia_aberta[0] = False; _claudia_corpo.visible = False
            _monitor_aberto[0] = False; _monitor_corpo.visible = False
            _resumo_aberto[0]  = False; _resumo_corpo.visible  = False
            _ico_claudia.name  = "expand_more_rounded"
            _ico_monitor.name  = "expand_more_rounded"
            _ico_resumo.name   = "expand_more_rounded"
            area_conteudo.controls.extend(_conteudo_inicio())
        elif idx == 2:
            area_conteudo.controls.extend(_conteudo_clinico())
        elif idx == 3:
            area_conteudo.controls.extend(_conteudo_mais())

    def _trocar_aba(idx):
        if idx == 1:
            _lazy_fn("tela_exames", "criar_tela_consulta", readonly=modo_medico)()
            return
        aba_ativa[0] = idx
        _rebuild_abas()
        _rebuild_conteudo()
        _atualizar_ui()

    # ══════════════════════════════════════════════════════════
    # CARREGAR DADOS EM BACKGROUND
    # ══════════════════════════════════════════════════════════
    def _carregar_tudo_sync():
        # Score de saúde — baseado em resultados de exames
        try:
            conn = _sq.connect(DB_PATH, timeout=30)
            try:
                rows = conn.execute("""
                    SELECT valor, referencia FROM exame_resultados
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
                    if " - " in ref:
                        partes = ref.split(" - ")
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
            rows = []

        score_final = score_ex
        if score_final >= 90:   nota, cor_s = "Excelente", VERD
        elif score_final >= 75: nota, cor_s = "Bom",       AZUL
        elif score_final >= 60: nota, cor_s = "Regular",   AMAR
        else:                   nota, cor_s = "Atencao",   VERM

        txt_score_num.value = str(int(score_final))
        txt_score_num.color = cor_s
        txt_nota.value      = nota
        txt_nota.color      = cor_s
        txt_detalhes.value  = f"{len(rows)} resultados avaliados"
        _score_cache[0] = {
            "final": score_final, "nota": nota, "cor": cor_s,
            "exames": score_ex, "adesao": 100.0, "consultas": 100.0,
            "n_exames": len(rows), "n_remedios": 0,
        }

        # Contadores para Resumo
        try:
            conn_res = _sq.connect(DB_PATH, timeout=30)
            try:
                n_hist = conn_res.execute(
                    "SELECT COUNT(*) FROM historico_medico"
                ).fetchone()[0]
                n_diag_int = conn_res.execute(
                    "SELECT COUNT(*) FROM diagnosticos_internacao"
                ).fetchone()[0]
                n_diag = n_hist + n_diag_int
                try:
                    n_rem = conn_res.execute(
                        "SELECT COUNT(*) FROM remedios WHERE ativo=1"
                    ).fetchone()[0]
                except Exception:
                    n_rem = 0
                try:
                    n_rot = conn_res.execute(
                        "SELECT COUNT(*) FROM rotinas_templates WHERE ativo=1"
                    ).fetchone()[0]
                except Exception:
                    n_rot = 0
                try:
                    n_con = conn_res.execute(
                        "SELECT COUNT(*) FROM consultas WHERE data_consulta >= date('now','-90 days')"
                    ).fetchone()[0]
                except Exception:
                    n_con = 0
            finally:
                conn_res.close()
            txt_n_eventos.value  = str(n_hist)
            txt_n_diag.value     = str(n_diag) if n_diag else "--"
            txt_n_remedios.value = str(n_rem)  if n_rem  else "--"
            txt_n_rotinas.value  = str(n_rot)  if n_rot  else "--"
            txt_n_consultas.value= str(n_con)  if n_con  else "--"
        except Exception:
            txt_n_eventos.value   = "--"
            txt_n_diag.value      = "--"
            txt_n_remedios.value  = "--"
            txt_n_rotinas.value   = "--"
            txt_n_consultas.value = "--"

        try:
            conn_uti = _sq.connect(DB_PATH, timeout=30)
            try:
                for ref_u in _uti_refs:
                    # Vitaminas: score ponderado por faixas de referencia fixas
                    if ref_u["lbl"] == "Vitaminas":
                        try:
                            _vit_rows = conn_uti.execute("""
                                SELECT r.parametro, r.valor, e.data_exame
                                FROM exame_resultados r
                                JOIN exames e ON r.exame_id = e.id
                                JOIN exames_padrao ep ON ep.id = r.exame_padrao_id
                                WHERE LOWER(ep.categoria) = 'vitaminas'
                                  AND r.valor IS NOT NULL AND r.valor != ''
                                ORDER BY ep.nome_oficial, e.data_exame DESC
                            """).fetchall()

                            # pega apenas o valor mais recente por parametro (key=lower)
                            _vit_recente = {}
                            for _p, _v, _d in _vit_rows:
                                _k = _p.strip().lower()
                                if _k not in _vit_recente:
                                    _vit_recente[_k] = (_p, _v)

                            # faixas de referencia fixas: (min, max) ou None = sem limite
                            # valor None no limite = sem limite naquele lado
                            # invertido=True: menor e pior (ex: homocisteina)
                            _REFS_VIT = {
                                "vitamina d":        (30.0,  100.0, False),
                                "vitamina b12":      (200.0, 900.0, False),
                                "vitamina b12 (cobalamina)": (200.0, 900.0, False),
                                "vitamina a (retinol)": (0.3,  1.4,  False),
                                "acido folico":      (3.1,   None,  False),
                                "acido folico (vitamina b9)": (3.1, None, False),
                                "homocisteina":      (None,  15.0,  True),
                                "serotonina":        (50.0,  200.0, False),
                            }

                            _scores = []
                            _fora = 0
                            for _k, (_nome, _vs) in _vit_recente.items():
                                try:
                                    _vf = float(str(_vs).replace(",", "."))
                                except Exception:
                                    continue
                                # normaliza chave para busca
                                _kb = _k.replace("é","e").replace("á","a").replace("â","a").replace("ô","o").replace("ó","o").replace("ã","a").replace("í","i").replace("ú","u").replace("ç","c")
                                _ref = next((v for rk, v in _REFS_VIT.items()
                                             if rk in _kb or _kb in rk), None)
                                if _ref is None:
                                    _scores.append(100)  # sem ref conhecida = neutro
                                    continue
                                _rmin, _rmax, _inv = _ref
                                if _rmin is not None and _vf < _rmin:
                                    # abaixo do minimo: penaliza proporcional
                                    _pct = max(0, _vf / _rmin) * 100
                                    _scores.append(_pct)
                                    _fora += 1
                                elif _rmax is not None and _vf > _rmax:
                                    # acima do maximo
                                    _excesso = (_vf - _rmax) / _rmax
                                    _pct = max(0, 100 - _excesso * 100)
                                    _scores.append(_pct)
                                    _fora += 1
                                else:
                                    _scores.append(100)

                            _score_vit = round(sum(_scores) / len(_scores)) if _scores else 100
                            _n_tipos = len(_vit_recente)
                            _cor_score = (VERD if _score_vit >= 90
                                          else AZUL if _score_vit >= 75
                                          else AMAR if _score_vit >= 60
                                          else VERM)
                            ref_u["val"].value   = str(_score_vit)
                            ref_u["val"].color   = _cor_score
                            ref_u["unit"].value  = "%"
                            ref_u["data"].value  = (f"{_fora} fora" if _fora
                                                    else f"{_n_tipos} tipos ok")
                            ref_u["dot"].bgcolor = _cor_score
                            ref_u["card"].border = ft.border.all(
                                1, ft.Colors.with_opacity(0.35, _cor_score))
                        except Exception:
                            pass
                        continue

                    # Inflamacao: score ponderado por marcadores inflamatorios
                    if ref_u["lbl"] == "Inflamacao":
                        try:
                            _inf_rows = conn_uti.execute("""
                                SELECT r.parametro, r.valor, r.referencia, e.data_exame
                                FROM exame_resultados r
                                JOIN exames e ON r.exame_id = e.id
                                JOIN exames_padrao ep ON ep.id = r.exame_padrao_id
                                WHERE (LOWER(ep.categoria) IN ('inflamacao','inflamação','imunologia','imunidade')
                                       OR LOWER(r.parametro) LIKE '%pcr%'
                                       OR LOWER(r.parametro) LIKE '%proteina c reativa%'
                                       OR LOWER(r.parametro) LIKE '%vhs%'
                                       OR LOWER(r.parametro) LIKE '%fator reumatoide%'
                                       OR LOWER(r.parametro) LIKE '%fan%'
                                       OR LOWER(r.parametro) LIKE '%anti-transglutaminase%')
                                  AND r.valor IS NOT NULL AND r.valor != ''
                                ORDER BY e.data_exame DESC
                            """).fetchall()
                            # pega o mais recente por parametro
                            _inf_recente = {}
                            for _p, _v, _ref_str, _d in _inf_rows:
                                _k = _p.strip().lower()
                                if _k not in _inf_recente:
                                    _inf_recente[_k] = (_p, _v, _ref_str or "")
                            # indice 0-10: 0=sem inflamacao, 10=muito inflamado
                            # formula: indice_marcador = min(10, (valor/limite)*10)
                            # indice final = media dos marcadores com ref conhecida
                            _REFS_INF = {
                                "pcr":                       0.5,
                                "proteina c reativa":        0.5,
                                "vhs":                       15.0,
                                "fator reumatoide":          20.0,
                                "anti-transglutaminase iga": 20.0,
                                "imunoglobulina a":          591.0,
                            }
                            _indices_i = []
                            _fora_i = 0
                            for _k, (_nome, _vs, _ref_str) in _inf_recente.items():
                                try:
                                    _vf = float(str(_vs).replace(",", "."))
                                except Exception:
                                    continue
                                _kb = _k.replace("é","e").replace("á","a").replace("â","a").replace("ã","a").replace("í","i").replace("ú","u").replace("ç","c")
                                _rlim = next((v for rk, v in _REFS_INF.items()
                                              if rk in _kb or _kb in rk), None)
                                if _rlim is None:
                                    continue  # sem ref = nao entra no calculo
                                _idx = min(10.0, (_vf / _rlim) * 10.0)
                                _indices_i.append(_idx)
                                if _vf > _rlim:
                                    _fora_i += 1
                            _indice_inf = round(sum(_indices_i) / len(_indices_i), 1) if _indices_i else 0.0
                            _n_inf = len(_inf_recente)
                            # cor: 0-2=verde, 3-4=azul, 5-6=amarelo, 7+=vermelho
                            _cor_inf = (VERD if _indice_inf <= 2
                                        else AZUL if _indice_inf <= 4
                                        else AMAR if _indice_inf <= 6
                                        else VERM)
                            ref_u["val"].value   = str(_indice_inf)
                            ref_u["val"].color   = _cor_inf
                            ref_u["unit"].value  = "/10"
                            ref_u["data"].value  = (f"{_fora_i} elevado(s)" if _fora_i
                                                    else f"{_n_inf} marcadores ok")
                            ref_u["dot"].bgcolor = _cor_inf
                            ref_u["card"].border = ft.border.all(
                                1, ft.Colors.with_opacity(0.35, _cor_inf))
                        except Exception:
                            pass
                        continue

                    # Hormonios: score ponderado por faixas de referencia fixas
                    if ref_u["lbl"] == "Hormonios":
                        try:
                            _hor_rows = conn_uti.execute("""
                                SELECT r.parametro, r.valor, e.data_exame
                                FROM exame_resultados r
                                JOIN exames e ON r.exame_id = e.id
                                JOIN exames_padrao ep ON ep.id = r.exame_padrao_id
                                WHERE LOWER(ep.categoria) IN ('hormonios','hormônios','hormônio','hormonio')
                                  AND r.valor IS NOT NULL AND r.valor != ''
                                ORDER BY ep.nome_oficial, e.data_exame DESC
                            """).fetchall()
                            _hor_recente = {}
                            for _p, _v, _d in _hor_rows:
                                _k = _p.strip().lower()
                                if _k not in _hor_recente:
                                    _hor_recente[_k] = (_p, _v)
                            # faixas (min, max) para homens adultos
                            _REFS_HOR = {
                                "testosterona total":   (249.0, 836.0),
                                "testosterona livre":   (5.0,   21.0),
                                "shbg":                 (13.2,  89.5),
                                "dht":                  (143.0, 842.0),
                                "estradiol":            (10.0,  40.0),
                                "insulina basal":       (2.0,   13.0),
                                "pth":                  (18.5,  88.0),
                                "paratormonio":         (18.5,  88.0),
                            }
                            # indice 0-10: dentro da faixa=10, fora penaliza proporcional
                            _indices_h = []
                            _fora_h = 0
                            for _k, (_nome, _vs) in _hor_recente.items():
                                try:
                                    _vs_n = str(_vs).replace(",", ".")
                                    _vf = float(_vs_n)
                                except Exception:
                                    continue
                                _kb = _k.replace("é","e").replace("á","a").replace("â","a").replace("ã","a").replace("í","i").replace("ú","u").replace("ç","c")
                                _ref = next((v for rk, v in _REFS_HOR.items()
                                             if rk in _kb or _kb in rk), None)
                                if _ref is None:
                                    continue  # sem ref = nao entra no calculo
                                _rmin, _rmax = _ref
                                if _vf < _rmin:
                                    _indices_h.append(max(0.0, (_vf / _rmin) * 10.0))
                                    _fora_h += 1
                                elif _vf > _rmax:
                                    _excesso = (_vf - _rmax) / _rmax
                                    _indices_h.append(max(0.0, 10.0 - _excesso * 10.0))
                                    _fora_h += 1
                                else:
                                    _indices_h.append(10.0)
                            _indice_hor = round(sum(_indices_h) / len(_indices_h), 1) if _indices_h else 10.0
                            _n_hor = len(_hor_recente)
                            _cor_hor = (VERD if _indice_hor >= 8
                                        else AZUL if _indice_hor >= 6
                                        else AMAR if _indice_hor >= 4
                                        else VERM)
                            ref_u["val"].value   = str(_indice_hor)
                            ref_u["val"].color   = _cor_hor
                            ref_u["unit"].value  = "/10"
                            ref_u["data"].value  = (f"{_fora_h} fora" if _fora_h
                                                    else f"{_n_hor} hormonios ok")
                            ref_u["dot"].bgcolor = _cor_hor
                            ref_u["card"].border = ft.border.all(
                                1, ft.Colors.with_opacity(0.35, _cor_hor))
                        except Exception:
                            pass
                        continue

                    # Renal: indicadores de funcao renal (0=ruim, 10=otimo)
                    if ref_u["lbl"] == "Renal":
                        try:
                            _ren_rows = conn_uti.execute("""
                                SELECT r.parametro, r.valor, e.data_exame
                                FROM exame_resultados r
                                JOIN exames e ON r.exame_id = e.id
                                JOIN exames_padrao ep ON ep.id = r.exame_padrao_id
                                WHERE LOWER(ep.categoria) IN ('funcao renal','função renal','proteinas','proteínas')
                                   OR LOWER(r.parametro) LIKE '%microalbuminu%'
                                AND r.valor IS NOT NULL AND r.valor != ''
                                ORDER BY ep.nome_oficial, e.data_exame DESC
                            """).fetchall()
                            _ren_recente = {}
                            for _p, _v, _d in _ren_rows:
                                _k = _p.strip().lower()
                                if _k not in _ren_recente:
                                    _ren_recente[_k] = (_p, _v)
                            # eRFG: maior=melhor (>=90=ok, <60=alerta, <30=critico)
                            # Creatinina, Ureia, Ac.Urico, Microalbuminuria: menor=melhor
                            # indice 0-10: 10=otimo
                            _REFS_REN = {
                                # (min_ok, max_ok, tipo)
                                # tipo "faixa": dentro=10
                                # tipo "max": acima penaliza
                                # tipo "erfg": especial — maior=melhor, 90+=10
                                "erfg":              (90.0,  "erfg"),
                                "creatinina":        (1.2,   "max"),
                                "ureia":             (50.0,  "max"),
                                "bun":               (20.0,  "max"),
                                "acido urico":       (7.0,   "max"),
                                "microalbuminuria":  (30.0,  "max"),
                                "albumina":          (3.5,   5.2,   "faixa"),
                            }
                            _indices_r = []
                            _fora_r = 0
                            for _k, (_nome, _vs) in _ren_recente.items():
                                try:
                                    _vf = float(str(_vs).replace(",", "."))
                                except Exception:
                                    continue
                                _kb = _k.replace("é","e").replace("á","a").replace("â","a").replace("ã","a").replace("í","i").replace("ú","u").replace("ç","c")
                                _ref = next((v for rk, v in _REFS_REN.items()
                                             if rk in _kb or _kb in rk), None)
                                if _ref is None:
                                    continue
                                if _ref[-1] == "erfg":
                                    # eRFG: 90+=10, 60-89=proporcional, <60 penaliza
                                    _lim = _ref[0]
                                    _idx = min(10.0, (_vf / _lim) * 10.0)
                                    _indices_r.append(_idx)
                                    if _vf < 60:
                                        _fora_r += 1
                                elif _ref[-1] == "max":
                                    # menor=melhor: no limite=5, zero=10
                                    _lim = _ref[0]
                                    if _vf <= _lim:
                                        _idx = 10.0 - (_vf / _lim) * 5.0
                                        _indices_r.append(_idx)
                                    else:
                                        _excesso = (_vf - _lim) / _lim
                                        _indices_r.append(max(0.0, 5.0 - _excesso * 10.0))
                                        _fora_r += 1
                                elif _ref[-1] == "faixa":
                                    _rmin, _rmax = _ref[0], _ref[1]
                                    if _vf < _rmin:
                                        _indices_r.append(max(0.0, (_vf / _rmin) * 10.0))
                                        _fora_r += 1
                                    elif _vf > _rmax:
                                        _excesso = (_vf - _rmax) / _rmax
                                        _indices_r.append(max(0.0, 10.0 - _excesso * 10.0))
                                        _fora_r += 1
                                    else:
                                        _indices_r.append(10.0)
                            _indice_ren = round(sum(_indices_r) / len(_indices_r), 1) if _indices_r else 10.0
                            _n_ren = len(_ren_recente)
                            _cor_ren = (VERD if _indice_ren >= 8
                                        else AZUL if _indice_ren >= 6
                                        else AMAR if _indice_ren >= 4
                                        else VERM)
                            ref_u["val"].value   = str(_indice_ren)
                            ref_u["val"].color   = _cor_ren
                            ref_u["unit"].value  = "/10"
                            ref_u["data"].value  = (f"{_fora_r} fora" if _fora_r
                                                    else f"{_n_ren} indicadores ok")
                            ref_u["dot"].bgcolor = _cor_ren
                            ref_u["card"].border = ft.border.all(
                                1, ft.Colors.with_opacity(0.35, _cor_ren))
                        except Exception:
                            pass
                        continue

                    row = None
                    _excl = " AND r.parametro NOT LIKE '%erro%'" \
                            if ref_u["lbl"] == "Ac.Urico" else ""
                    for termo in ref_u["termos"]:
                        row = conn_uti.execute(f"""
                            SELECT r.valor, r.unidade, r.referencia, e.data_exame
                            FROM exame_resultados r
                            JOIN exames e ON r.exame_id = e.id
                            WHERE r.parametro LIKE ?{_excl}
                              AND r.valor IS NOT NULL AND r.valor != ''
                            ORDER BY e.data_exame DESC LIMIT 1
                        """, (f"%{termo}%",)).fetchone()
                        if row: break
                    try:
                        for termo in ref_u["termos"]:
                            mrow = conn_uti.execute("""
                                SELECT CAST(valor AS TEXT), unidade,
                                       referencia, data_medicao
                                FROM marcadores_leituras
                                WHERE parametro LIKE ?
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
                        try:
                            _vf = float(str(val_s).replace(",", "."))
                            _disp = f"{_vf:.1f}" if _vf != int(_vf) else f"{int(_vf)}"
                        except Exception:
                            _disp = str(val_s) or "--"
                        # Pressao: buscar PAD do mesmo exame e exibir SIS/DIA
                        if ref_u["lbl"] == "Pressao":
                            try:
                                _pad = conn_uti.execute("""
                                    SELECT r.valor FROM exame_resultados r
                                    JOIN exames e ON r.exame_id = e.id
                                    WHERE r.parametro LIKE '%Total - PAD%'
                                      AND e.data_exame = ?
                                    LIMIT 1
                                """, (data_s[:10] if data_s else "",)).fetchone()
                                if _pad:
                                    _vd = float(str(_pad[0]).replace(",", "."))
                                    _disp = f"{int(_vf)}/{int(_vd)}"
                            except Exception:
                                pass
                        ref_u["val"].value  = _disp[:7]
                        ref_u["unit"].value = (unit_s or "")[:6]
                        if data_s and len(data_s) >= 10:
                            d = data_s[:10]
                            try:
                                import datetime as _dt
                                _dobj = _dt.date.fromisoformat(d)
                                _dias = (_dt.date.today() - _dobj).days
                                if _dias == 0:   _dtxt = "hoje"
                                elif _dias == 1: _dtxt = "1 dia atras"
                                else:            _dtxt = f"{_dias} dias atras"
                                ref_u["data"].value = _dtxt
                            except Exception:
                                ref_u["data"].value = f"{d[8:10]}/{d[5:7]}"
                        s_cor = _avaliar_status_cor(val_s, ref_s)
                        ref_u["dot"].bgcolor = s_cor
                        ref_u["val"].color   = s_cor
                        ref_u["card"].border = ft.border.all(1, ft.Colors.with_opacity(0.35, s_cor))
                    try:
                        vals30 = []
                        for termo in ref_u["termos"]:
                            r30 = conn_uti.execute(f"""
                                SELECT r.valor FROM exame_resultados r
                                JOIN exames e ON r.exame_id = e.id
                                WHERE r.parametro LIKE ?{_excl}
                                  AND r.valor IS NOT NULL AND r.valor != ''
                                ORDER BY e.data_exame DESC LIMIT 30
                            """, (f"%{termo}%",)).fetchall()
                            for (v,) in r30:
                                try: vals30.append(float(str(v).replace(",", ".")))
                                except Exception: pass
                            try:
                                m30 = conn_uti.execute("""
                                    SELECT CAST(valor AS TEXT) FROM marcadores_leituras
                                    WHERE parametro LIKE ?
                                    ORDER BY data_medicao DESC LIMIT 30
                                """, (f"%{termo}%",)).fetchall()
                                for (v,) in m30:
                                    try: vals30.append(float(str(v).replace(",", ".")))
                                    except Exception: pass
                            except Exception:
                                pass
                            if vals30: break
                        if vals30:
                            med = sum(vals30) / len(vals30)
                            ref_u["media"].value = f"med:{med:.1f}"
                    except Exception:
                        pass
            finally:
                conn_uti.close()
        except Exception as _ex_uti:
            log.warning("[HUB] UTI monitor: %s", _ex_uti)

        try:
            from shared.auth import _CREDS_PATH as _auth_cp
            if os.path.exists(_auth_cp):
                ico_sync.color = VERD
                txt_sync.value = "Backup automatico ativo"
                txt_sync.color = VERD
        except Exception:
            pass

        if _montado[0]:
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
        def _fazer():
            try:
                from backup import backup_watcher as _bw
                if getattr(_bw, "_instancia", None): _bw._instancia.parar()
            except Exception: pass
            try:
                from shared.auth import _CREDS_PATH
                if os.path.exists(_CREDS_PATH): os.remove(_CREDS_PATH)
            except Exception: pass
            try:
                from telas_shared.tela_login import criar_tela_login
                def _on_login():
                    from telas.tela_hub import criar_tela_hub as _hub
                    _navegar(_hub, None)
                tela_login = criar_tela_login(page, on_login_sucesso=_on_login)
                page.controls.clear()
                page.controls.append(tela_login)
                try: page.update()
                except Exception: pass
            except Exception as ex:
                log.exception("[HUB] Erro ao deslogar: %s", ex)

        _mostrar_confirmar("Deslogar?",
                           "Tem certeza que deseja sair?\nSera necessario fazer login novamente.",
                           _fazer)

    def _mostrar_confirmar(titulo, msg, fn_sim):
        ref = [None]
        def _fechar(e=None):
            if ref[0] and ref[0] in page.overlay:
                page.overlay.remove(ref[0])
            try: page.update()
            except Exception: pass
        def _confirmar(e):
            _fechar(); fn_sim()
        btn_cancel = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=ft.Colors.with_opacity(0.13, SEC), ink=True,
        )
        btn_cancel.on_click = _fechar
        btn_ok = ft.Container(
            content=ft.Text("Confirmar", size=13, color=VERM, weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=ft.Colors.with_opacity(0.13, VERM), ink=True,
        )
        btn_ok.on_click = _confirmar
        ref[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Text(titulo, size=15, color=TXT, weight=ft.FontWeight.W_700,
                            text_align="center"),
                    ft.Container(height=8),
                    ft.Text(msg, size=13, color=SEC, text_align="center"),
                    ft.Container(height=20),
                    ft.Row([btn_cancel, btn_ok], spacing=8,
                           alignment=ft.MainAxisAlignment.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                bgcolor=CARD, border_radius=14, padding=ft.padding.all(24), width=300,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref[0].on_click = _fechar
        page.overlay.append(ref[0])
        try: page.update()
        except Exception: pass

    menu_usuario = ft.PopupMenuButton(
        content=ft.Container(
            content=ft.Icon("person_outline_rounded", size=20, color=SEC),
            padding=ft.padding.all(8),
        ),
        items=[
            ft.PopupMenuItem(text="Perfil",   on_click=_nav_perfil),
            ft.PopupMenuItem(),
            ft.PopupMenuItem(text="Deslogar", on_click=lambda e: _deslogar()),
        ],
    )

    header = ft.Container(
        content=ft.Row([
            btn_voltar,
            ft.Row([
                ft.Icon("medical_services_rounded", size=18, color=AZUL),
                ft.Text("Prontuario", size=16, weight=ft.FontWeight.W_700, color=TXT),
            ], spacing=8, tight=True),
            ft.Container(expand=True),
            ft.Container() if modo_medico else menu_usuario,
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

    corpo = ft.Column([
        ft.Container(height=28, bgcolor=BG),
        header,
        ft.Container(content=area_conteudo, expand=True, bgcolor=BG),
        row_sync,
        ft.Container(
            content=ft.Text(f"v{APP_VERSAO}", size=10, color=MUT,
                            text_align="center"),
            alignment=ft.Alignment(0, 0),
            padding=ft.padding.symmetric(vertical=2),
        ),
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
    wrapper.controls.append(ft.Container(bgcolor=BG, expand=True, content=conteudo_final))

    _montado[0] = True
    threading.Thread(target=_carregar_tudo_sync, daemon=True,
                     name="HubCarregar").start()
    return wrapper


def _tela_incluir_exame(page, voltar_fn=None):
    from telas.tela_incluir_exame import criar_tela_incluir_exame
    def _voltar():
        if voltar_fn: voltar_fn()
    return criar_tela_incluir_exame(page, _voltar)
