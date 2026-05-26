# -*- coding: utf-8 -*-
# Prontuario | telas/tela_hub_medico.py
# Hub do medico: visao somente-leitura do prontuario + observacoes com anexo
import flet as ft
import logging

log = logging.getLogger(__name__)

BG    = "#0D1117"; CARD  = "#161B22"; BD   = "#21262D"; BD2   = "#30363D"
TXT   = "#E6EDF3"; SEC   = "#8B949E"; MUT  = "#484F58"
AZUL  = "#58A6FF"; VERD  = "#3FB950"; AMAR = "#D29922"
VERM  = "#F85149"; LRNJ  = "#F0883E"; ROXO = "#BC8CFF"
VERM_INT = "#CC1111"


def _para_display(s: str) -> str:
    if s and len(s) >= 10 and s[4] == "-":
        try:
            from datetime import datetime
            return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            pass
    return s or ""


def _idade_str(data_nasc: str) -> str:
    if not data_nasc:
        return ""
    try:
        from datetime import date
        nasc = date.fromisoformat(data_nasc[:10])
        hoje = date.today()
        anos = hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))
        return f"{anos} anos"
    except Exception:
        return ""


def criar_tela_hub_medico(page: ft.Page, voltar_fn=None,
                           medico_id: int = None) -> ft.Container:
    import sqlite3 as _sq
    import threading
    from dados.model_prontuario import DB_PATH

    _montado   = [False]
    aba_ativa  = [0]

    def _upd():
        if _montado[0]:
            try: page.update()
            except Exception: pass

    # ── Carregar dados do paciente ────────────────────────────
    _paciente  = [{}]

    def _load_paciente():
        try:
            from dados.model_prontuario import carregar_perfil
            p = carregar_perfil()
            _paciente[0] = p or {}
        except Exception as ex:
            log.warning("[HUB_MED] perfil: %s", ex)

    _load_paciente()

    pac  = _paciente[0]
    nome = pac.get("nome") or "Paciente"
    sexo = pac.get("sexo") or ""
    nasc = pac.get("data_nascimento") or ""
    foto = pac.get("foto_path") or ""
    cid  = pac.get("cid_principal") or ""

    # ── nome do medico ────────────────────────────────────────
    _nome_medico = ["Dr(a). Medico"]
    if medico_id:
        try:
            with _sq.connect(DB_PATH, timeout=10) as _c:
                r = _c.execute(
                    "SELECT nome FROM medicos WHERE id=?", (medico_id,)
                ).fetchone()
                if r:
                    _nome_medico[0] = r[0]
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════
    # HEADER — identificacao do paciente
    # ══════════════════════════════════════════════════════════
    def _mk_foto():
        if foto and __import__("os").path.isfile(foto):
            return ft.Container(
                content=ft.Image(src=foto, width=44, height=44,
                                 fit=ft.ImageFit.COVER),
                width=44, height=44, border_radius=22,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                border=ft.border.all(2, AZUL),
            )
        initials = "".join(w[0].upper() for w in nome.split()[:2] if w)
        return ft.Container(
            content=ft.Text(initials or "P", size=16,
                            weight=ft.FontWeight.W_700, color=AZUL),
            width=44, height=44, border_radius=22,
            bgcolor=ft.Colors.with_opacity(0.12, AZUL),
            border=ft.border.all(2, ft.Colors.with_opacity(0.40, AZUL)),
            alignment=ft.alignment.Alignment(0, 0),
        )

    sexo_label = {"M": "Masc", "F": "Fem"}.get(sexo, sexo)
    info_parts  = [p for p in [_idade_str(nasc), sexo_label, cid] if p]
    txt_info    = "  •  ".join(info_parts) if info_parts else ""

    btn_sair = ft.Container(
        content=ft.Row([
            ft.Icon("logout_rounded", size=13, color=SEC),
            ft.Text("Sair", size=12, color=SEC),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        border_radius=8, bgcolor=ft.Colors.with_opacity(0.06, SEC), ink=True,
    )
    btn_sair.on_click = lambda e: (voltar_fn() if voltar_fn else None)

    header = ft.Container(
        content=ft.Row([
            _mk_foto(),
            ft.Column([
                ft.Row([
                    ft.Text(nome, size=13, weight=ft.FontWeight.W_700, color=TXT,
                            expand=True),
                    ft.Container(
                        content=ft.Text("Visao Medico", size=9,
                                        color=AZUL, weight=ft.FontWeight.W_700),
                        bgcolor=ft.Colors.with_opacity(0.12, AZUL),
                        border=ft.border.all(1, ft.Colors.with_opacity(0.35, AZUL)),
                        border_radius=6, padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    ),
                ], spacing=8),
                ft.Text(txt_info, size=10, color=SEC) if txt_info else ft.Container(),
                ft.Text(_nome_medico[0], size=10, color=ROXO),
            ], spacing=2, expand=True, tight=True),
            btn_sair,
        ], spacing=10),
        bgcolor=CARD,
        border=ft.border.all(1, BD),
        border_radius=0,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
    )

    # ══════════════════════════════════════════════════════════
    # SECAO UTI — sinais vitais read-only
    # ══════════════════════════════════════════════════════════
    _UTI_CANAIS = [
        ("Glicemia",      "water_drop_rounded",            "#FF6B6B",
         ["glicose", "glucose", "glicemia", "glicada", "hba1c"]),
        ("Ac.Urico",      "science_rounded",               "#FFD93D",
         ["acido urico", "urico", "uratos"]),
        ("Pressao",       "favorite_rounded",              "#4ECDC4",
         ["sistolica", "pressao arterial", "diastolica"]),
        ("Bioimpedancia", "accessibility_new_rounded",     "#3FB950",
         ["gordura", "massa magra", "massa muscular", "imc", "bioimpedancia"]),
        ("Vitaminas",     "wb_sunny_rounded",              "#FDCB6E",
         ["vitamina d", "25-oh", "vitamina b12"]),
        ("Inflamacao",    "local_fire_department_rounded", "#FF7675",
         ["pcr", "proteina c reativa", "vhs"]),
        ("Hormonios",     "psychology_alt_rounded",        "#A29BFE",
         ["tsh", "t4 livre", "cortisol"]),
    ]

    _uti_refs: list = []
    _uti_row1 = ft.Row(spacing=6)
    _uti_row2 = ft.Row(spacing=6)

    def _avaliar_status_cor(valor_str, referencia_str):
        try:
            v = float(str(valor_str).replace(",", ".").strip())
            ref_s = str(referencia_str or "").strip()
            if " - " in ref_s:
                lo, hi = [float(x) for x in ref_s.split(" - ", 1)]
                if lo <= v <= hi:    return AZUL
                m1 = (hi - lo) * 0.25
                if (lo - m1) <= v <= (hi + m1): return AMAR
                return VERM
            elif ref_s.startswith("<"):
                lim = float(ref_s[1:].strip())
                return AZUL if v < lim else (AMAR if v < lim * 1.25 else VERM)
            elif ref_s.startswith(">"):
                lim = float(ref_s[1:].strip())
                return AZUL if v > lim else (AMAR if v > lim * 0.8 else VERM)
        except Exception:
            pass
        return AZUL

    def _abrir_overlay_uti(ref_dict):
        """Overlay de detalhe do card UTI — sem botao Abrir tela (so leitura)."""
        lbl  = ref_dict["lbl"]
        cor  = ref_dict["cor"]
        ico  = ref_dict.get("ico", "show_chart_rounded")
        val_txt  = ref_dict["val"].value  or "--"
        unit_txt = ref_dict["unit"].value or ""
        data_txt = ref_dict["data"].value or ""

        ov_ref = [None]

        def _fechar(e=None):
            if ov_ref[0] in page.overlay:
                page.overlay.remove(ov_ref[0])
            try: page.update()
            except Exception: pass

        btn_fechar = ft.Container(
            content=ft.Icon("close_rounded", size=18, color=SEC),
            padding=ft.padding.all(6), border_radius=8, ink=True,
        )
        btn_fechar.on_click = _fechar

        linhas = [
            ft.Row([
                ft.Text(val_txt, size=48, weight=ft.FontWeight.W_900, color=cor),
                ft.Container(
                    content=ft.Text(unit_txt, size=14, color=SEC),
                    padding=ft.padding.only(top=28),
                ),
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START),
        ]
        if data_txt:
            linhas.append(ft.Text(data_txt, size=13, color=SEC))

        ov_ref[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ico, size=16, color=cor),
                        ft.Text(lbl, size=15, color=cor, weight=ft.FontWeight.W_700,
                                expand=True),
                        btn_fechar,
                    ], spacing=8),
                    ft.Divider(height=1, color=BD2),
                    ft.Container(height=4),
                    *linhas,
                    ft.Container(height=8),
                    ft.Text("Somente visualizacao", size=10, color=MUT,
                            text_align=ft.TextAlign.CENTER),
                ], tight=True, spacing=6),
                bgcolor=CARD, border_radius=16,
                padding=ft.padding.all(24),
                width=(page.width or 380) - 48,
                border=ft.border.all(1, ft.Colors.with_opacity(0.35, cor)),
            ),
            bgcolor="#CC000000", expand=True,
            alignment=ft.Alignment(0, 0),
        )
        ov_ref[0].on_click = _fechar
        page.overlay.append(ov_ref[0])
        try: page.update()
        except Exception: pass

    def _mk_click_uti(lbl):
        def _h(e, _lbl=lbl):
            ref = next((r for r in _uti_refs if r["lbl"] == _lbl), None)
            if ref:
                _abrir_overlay_uti(ref)
        return _h

    for _idx, (_lbl, _ico, _cor, _termos) in enumerate(_UTI_CANAIS):
        _tv  = ft.Text("--", size=14, weight=ft.FontWeight.W_900,
                       color=_cor, text_align=ft.TextAlign.CENTER)
        _tu  = ft.Text("",   size=8,  color=SEC, text_align=ft.TextAlign.CENTER)
        _td  = ft.Text("",   size=8,  color=MUT, text_align=ft.TextAlign.CENTER)
        _dot = ft.Container(width=6, height=6, border_radius=3, bgcolor=MUT)
        _card = ft.Container(
            content=ft.Column([
                ft.Row([_dot], alignment=ft.MainAxisAlignment.CENTER),
                ft.Icon(_ico, size=12, color=ft.Colors.with_opacity(0.60, _cor)),
                ft.Text(_lbl, size=8, color=SEC, text_align=ft.TextAlign.CENTER,
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
        _card.on_click = _mk_click_uti(_lbl)
        _uti_refs.append({
            "val": _tv, "unit": _tu, "data": _td,
            "dot": _dot, "card": _card, "cor": _cor,
            "termos": _termos, "lbl": _lbl, "ico": _ico,
        })
        if _idx < 4:
            _uti_row1.controls.append(_card)
        else:
            _uti_row2.controls.append(_card)

    secao_uti = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon("monitor_heart_rounded", size=11, color=SEC),
                ft.Text("SINAIS VITAIS", size=10, color=SEC,
                        weight=ft.FontWeight.W_700),
            ], spacing=5),
            ft.Container(height=4),
            _uti_row1,
            ft.Container(height=4),
            _uti_row2,
        ], spacing=0),
        bgcolor=CARD,
        border=ft.border.all(1, BD),
        border_radius=0,
        padding=ft.padding.symmetric(horizontal=10, vertical=10),
    )

    # ── Carregar UTI em background ────────────────────────────
    def _load_uti():
        try:
            with _sq.connect(DB_PATH, timeout=15) as conn:
                conn.row_factory = _sq.Row
                for ref in _uti_refs:
                    termos = ref["termos"]
                    cor    = ref["cor"]
                    placeholders = " OR ".join(
                        "LOWER(ep.nome_oficial) LIKE ?" for _ in termos
                    )
                    params = [f"%{t}%" for t in termos]

                    # leituras manuais (marcadores_leituras -- match por parametro)
                    pl_m = " OR ".join("LOWER(ml.parametro) LIKE ?" for _ in termos)
                    cur_m = conn.execute(f"""
                        SELECT ml.valor, ml.unidade, ml.data_medicao, ml.referencia
                        FROM marcadores_leituras ml
                        WHERE ({pl_m})
                        ORDER BY ml.data_medicao DESC LIMIT 1
                    """, params)
                    row_m = cur_m.fetchone()

                    # exames de laboratorio
                    cur_e = conn.execute(f"""
                        SELECT er.valor, ep.unidade, e.data_exame, er.referencia
                        FROM exame_resultados er
                        LEFT JOIN exames_padrao ep ON ep.id = er.exame_padrao_id
                        LEFT JOIN exames e ON e.id = er.exame_id
                        WHERE ({placeholders})
                        ORDER BY e.data_exame DESC LIMIT 1
                    """, params)
                    row_e = cur_e.fetchone()

                    best, data_best = None, ""
                    if row_m and row_e:
                        dm = (row_m["data_medicao"] or "")
                        de = (row_e["data_exame"]   or "")
                        if dm >= de:
                            best = row_m; data_best = dm
                        else:
                            best = row_e; data_best = de
                    elif row_m:
                        best = row_m; data_best = row_m["data_medicao"] or ""
                    elif row_e:
                        best = row_e; data_best = row_e["data_exame"] or ""

                    if best:
                        val_s = str(best["valor"] or "")
                        unit_s = best["unidade"] or ""
                        ref_s  = best["referencia"] if "referencia" in best.keys() else ""
                        cor_v  = _avaliar_status_cor(val_s, ref_s)
                        ref["val"].value  = val_s[:8]
                        ref["unit"].value = unit_s
                        ref["data"].value = _para_display(data_best)
                        ref["val"].color  = cor_v
                        ref["dot"].bgcolor = cor_v
            _upd()
        except Exception as ex:
            log.warning("[HUB_MED] uti: %s", ex)

    threading.Thread(target=_load_uti, daemon=True, name="HubMedUti").start()

    # ══════════════════════════════════════════════════════════
    # ABAS
    # ══════════════════════════════════════════════════════════
    ABAS = [
        (0, "science_rounded",    "Exames",    AZUL),
        (1, "medical_services_rounded", "Clinico", VERD),
        (2, "edit_note_rounded",  "Observacoes", LRNJ),
    ]
    area_conteudo = ft.Column(
        spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
    barra_abas = ft.Row(spacing=0)

    # ── ABA 0: EXAMES (read-only, busca simples) ─────────────
    def _conteudo_exames() -> list:
        return [_mk_secao_exames_simples()]

    def _mk_secao_exames_simples() -> ft.Control:
        area_ex = ft.Column(spacing=6)
        _txt_busca = ft.TextField(
            label="Buscar exame...", bgcolor=CARD,
            border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, height=42,
            prefix_icon="search_rounded",
        )

        def _filtrar(e=None):
            import unicodedata
            def _norm(s):
                return unicodedata.normalize("NFD", s or "").encode(
                    "ascii", "ignore").decode().upper()
            q = _norm(_txt_busca.value or "")
            area_ex.controls.clear()
            try:
                with _sq.connect(DB_PATH, timeout=15) as conn:
                    conn.row_factory = _sq.Row
                    rows = conn.execute("""
                        SELECT er.id, ep.nome_oficial, er.valor, ep.unidade,
                               ep.referencia, e.data_exame
                        FROM exame_resultados er
                        LEFT JOIN exames_padrao ep ON ep.id = er.exame_padrao_id
                        LEFT JOIN exames e ON e.id = er.exame_id
                        ORDER BY e.data_exame DESC LIMIT 200
                    """).fetchall()
                for r in rows:
                    nome_ex = r["nome_oficial"] or ""
                    if q and q not in _norm(nome_ex):
                        continue
                    data_d = _para_display(r["data_exame"] or "")
                    area_ex.controls.append(ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Text(nome_ex, size=12, color=TXT,
                                        weight=ft.FontWeight.W_600),
                                ft.Text(data_d, size=10, color=SEC),
                            ], spacing=1, expand=True, tight=True),
                            ft.Text(
                                f"{r['valor']} {r['unidade'] or ''}",
                                size=13, color=AZUL,
                                weight=ft.FontWeight.W_700),
                        ], spacing=8),
                        bgcolor=CARD,
                        border=ft.border.all(1, BD),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    ))
            except Exception as ex:
                area_ex.controls.append(
                    ft.Text(f"Erro: {ex}", size=11, color=VERM))
            _upd()

        _txt_busca.on_change = _filtrar
        _filtrar()
        return ft.Column([
            ft.Container(
                content=_txt_busca,
                padding=ft.padding.all(10)),
            area_ex,
        ], spacing=0)

    # ── ABA 1: CLINICO ────────────────────────────────────────
    def _conteudo_clinico() -> list:
        controles = []

        def _secao(titulo, ico, cor, fn_items):
            items = fn_items()
            if not items:
                return None
            col = ft.Column([
                ft.Row([
                    ft.Icon(ico, size=11, color=cor),
                    ft.Text(titulo, size=10, color=cor,
                            weight=ft.FontWeight.W_700),
                ], spacing=5),
                ft.Container(height=4),
                *items,
            ], spacing=4)
            return ft.Container(
                content=col,
                bgcolor=CARD, border=ft.border.all(1, BD),
                border_radius=10,
                padding=ft.padding.all(12),
                margin=ft.margin.only(bottom=8),
            )

        def _historico_items():
            its = []
            try:
                with _sq.connect(DB_PATH, timeout=10) as conn:
                    conn.row_factory = _sq.Row
                    rows = conn.execute("""
                        SELECT titulo, tipo, data, sequela, alerta
                        FROM historico_medico
                        ORDER BY data DESC LIMIT 20
                    """).fetchall()
                for r in rows:
                    cor_it = VERM if r["alerta"] else TXT
                    its.append(ft.Row([
                        ft.Icon("warning_rounded" if r["alerta"] else "history_rounded",
                                size=12, color=cor_it),
                        ft.Column([
                            ft.Text(r["titulo"] or "", size=12, color=cor_it,
                                    weight=ft.FontWeight.W_600),
                            ft.Text(
                                f"{r['tipo'] or ''}  •  {_para_display(r['data'])}",
                                size=10, color=SEC),
                        ], spacing=1, tight=True, expand=True),
                    ], spacing=8))
            except Exception as ex:
                its.append(ft.Text(f"Erro: {ex}", size=10, color=VERM))
            return its

        def _consultas_items():
            its = []
            try:
                with _sq.connect(DB_PATH, timeout=10) as conn:
                    conn.row_factory = _sq.Row
                    rows = conn.execute("""
                        SELECT c.data_consulta, m.nome AS medico, c.especialidade, c.resumo
                        FROM consultas c
                        LEFT JOIN medicos m ON m.id = c.medico_id
                        ORDER BY c.data_consulta DESC LIMIT 10
                    """).fetchall()
                for r in rows:
                    its.append(ft.Column([
                        ft.Row([
                            ft.Text(_para_display(r["data_consulta"]),
                                    size=10, color=AMAR),
                            ft.Text(r["especialidade"] or "", size=10, color=SEC),
                        ], spacing=8),
                        ft.Text(r["medico"] or "", size=12, color=TXT,
                                weight=ft.FontWeight.W_600),
                        ft.Text(r["resumo"] or "", size=10, color=SEC,
                                max_lines=2),
                        ft.Divider(height=1, color=BD),
                    ], spacing=2, tight=True))
            except Exception as ex:
                its.append(ft.Text(f"Erro: {ex}", size=10, color=VERM))
            return its

        def _internacoes_items():
            its = []
            try:
                with _sq.connect(DB_PATH, timeout=10) as conn:
                    conn.row_factory = _sq.Row
                    rows = conn.execute("""
                        SELECT data_entrada, data_saida, cid, motivo
                        FROM internacoes
                        ORDER BY data_entrada DESC LIMIT 10
                    """).fetchall()
                for r in rows:
                    periodo = (f"{_para_display(r['data_entrada'])} - "
                               f"{_para_display(r['data_saida']) if r['data_saida'] else 'atual'}")
                    its.append(ft.Column([
                        ft.Row([
                            ft.Text(r["cid"] or "", size=10, color=VERM),
                            ft.Text(periodo, size=10, color=SEC, expand=True),
                        ], spacing=8),
                        ft.Text(r["motivo"] or "", size=12, color=TXT),
                        ft.Divider(height=1, color=BD),
                    ], spacing=2, tight=True))
            except Exception as ex:
                its.append(ft.Text(f"Erro: {ex}", size=10, color=VERM))
            return its

        def _remedios_items():
            its = []
            try:
                with _sq.connect(DB_PATH, timeout=10) as conn:
                    conn.row_factory = _sq.Row
                    rows = conn.execute("""
                        SELECT nome, dosagem, frequencia
                        FROM remedios WHERE ativo = 1
                        ORDER BY nome
                    """).fetchall()
                for r in rows:
                    its.append(ft.Row([
                        ft.Icon("medication_rounded", size=12, color=VERD),
                        ft.Column([
                            ft.Text(r["nome"] or "", size=12, color=TXT,
                                    weight=ft.FontWeight.W_600),
                            ft.Text(
                                f"{r['dosagem'] or ''}  •  {r['frequencia'] or ''}",
                                size=10, color=SEC),
                        ], spacing=1, tight=True, expand=True),
                    ], spacing=8))
            except Exception as ex:
                its.append(ft.Text(f"Erro: {ex}", size=10, color=VERM))
            return its

        def _alertas_items():
            its = []
            try:
                with _sq.connect(DB_PATH, timeout=10) as conn:
                    conn.row_factory = _sq.Row
                    rows = conn.execute("""
                        SELECT titulo, tipo, data
                        FROM historico_medico WHERE alerta = 1
                        ORDER BY data DESC
                    """).fetchall()
                for r in rows:
                    its.append(ft.Row([
                        ft.Icon("warning_amber_rounded", size=12, color=VERM),
                        ft.Text(r["titulo"] or "", size=12, color=VERM,
                                weight=ft.FontWeight.W_600, expand=True),
                        ft.Text(_para_display(r["data"]), size=10, color=SEC),
                    ], spacing=8))
            except Exception as ex:
                its.append(ft.Text(f"Erro: {ex}", size=10, color=VERM))
            return its

        for titulo, ico, cor, fn in [
            ("Historico Medico",  "history_rounded",           AZUL,  _historico_items),
            ("Consultas Recentes","calendar_today_rounded",     AMAR,  _consultas_items),
            ("Internacoes",       "local_hospital_rounded",     VERM,  _internacoes_items),
            ("Medicamentos Ativos","medication_rounded",         VERD,  _remedios_items),
            ("Alertas",           "warning_rounded",             VERM,  _alertas_items),
        ]:
            s = _secao(titulo, ico, cor, fn)
            if s:
                controles.append(s)

        if not controles:
            controles.append(
                ft.Text("Nenhum dado clinico encontrado.", size=12, color=SEC))
        return controles

    # ── ABA 2: OBSERVACOES ───────────────────────────────────
    def _conteudo_observacoes() -> list:
        from telas.tela_medico_observacoes import criar_aba_observacoes
        return [criar_aba_observacoes(page, medico_id, _nome_medico[0], _upd)]

    _CONTEUDO_ABAS = [
        _conteudo_exames,
        _conteudo_clinico,
        _conteudo_observacoes,
    ]

    def _rebuild_abas():
        barra_abas.controls.clear()
        for idx, icone, label, cor in ABAS:
            ativo = idx == aba_ativa[0]
            tab = ft.Container(
                content=ft.Column([
                    ft.Icon(icone, size=16, color=cor if ativo else SEC),
                    ft.Text(label, size=10,
                            color=cor if ativo else SEC,
                            weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.NORMAL),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=2, tight=True),
                expand=True,
                padding=ft.padding.symmetric(vertical=10),
                border=ft.border.all(0 if not ativo else 0,
                                     "#00000000"),
                bgcolor=ft.Colors.with_opacity(0.05, cor) if ativo else "#00000000",
                ink=True,
            )
            tab.on_click = lambda e, i=idx: _trocar_aba(i)
            barra_abas.controls.append(tab)
        _upd()

    def _trocar_aba(idx):
        aba_ativa[0] = idx
        _rebuild_abas()
        area_conteudo.controls.clear()
        items = _CONTEUDO_ABAS[idx]()
        area_conteudo.controls.extend(items if items else [])
        _upd()

    _rebuild_abas()
    _trocar_aba(0)

    # ── Layout final ─────────────────────────────────────────
    corpo = ft.Column([
        header,
        secao_uti,
        ft.Container(
            content=barra_abas,
            border=ft.border.all(0, "#00000000"),
            bgcolor=CARD,
        ),
        ft.Divider(height=1, color=BD),
        ft.Container(
            content=area_conteudo,
            expand=True,
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
        ),
    ], spacing=0, expand=True)

    _montado[0] = True
    return ft.Container(bgcolor=BG, expand=True, content=corpo)
