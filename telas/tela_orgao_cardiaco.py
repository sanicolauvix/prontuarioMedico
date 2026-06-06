# -*- coding: utf-8 -*-
# Prontuario | telas/tela_orgao_cardiaco.py
# Tela do sistema Cardiaco — padrao base + topico Eventos Cardiacos
import flet as ft
import sqlite3
import logging
from shared.layout import Layout
from dados.model_prontuario import DB_PATH

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; AMAR = "#D29922"
VERM = "#F85149"; ROXO = "#BC8CFF"; LAR  = "#F0883E"
COR  = "#FF6B6B"   # cor do sistema cardiaco

_SISTEMA = "Cardiaco"

_ABAS = [
    ("Diagnósticos", "diagnosis_rounded",           AZUL),
    ("Exames",       "science_rounded",              COR),
    ("Histórico",    "history_rounded",              AMAR),
    ("Médicos",      "person_rounded",               VERD),
    ("Remédios",     "medication_rounded",           ROXO),
    ("Eventos",      "monitor_heart_rounded",        VERM),
]

# Keywords para filtrar dados por sistema cardiaco
_KW_EXAMES = ["eco", "cardio", "cintilo", "eletro", "holter", "mapa",
               "angiotomo", "coronario", "cateter", "angioplastia",
               "doppler", "carotid", "doppler", "duplex", "troponina",
               "bnp", "ck-mb", "cpk"]
_KW_REMEDIOS = ["propranolol", "atenolol", "metoprolol", "bisoprolol",
                 "carvedilol", "losartana", "valsartana", "enalapril",
                 "ramipril", "amlodipina", "nifedipina", "diltiazem",
                 "espironolactona", "furosemida", "hidroclorotiazida",
                 "digoxina", "amiodarona", "sinvastatina", "atorvastatina",
                 "rosuvastatina", "aspirina", "clopidogrel", "warfarina",
                 "rivaroxabana", "apixabana", "nitroglicerina", "isossorbida",
                 "anlodipino", "hidralazina", "captopril"]
_KW_MEDICOS = ["cardio", "iara", "yara", "pazolini", "arantes", "vascular",
               "hemodinamic"]
_KW_HISTORICO = ["stent", "safena", "mamaria", "infarto", "coronar",
                  "cardiaco", "revasculariz", "angioplastia", "ponte",
                  "marcapasso", "fibrilacao", "arritmia", "valva"]


def _para_display(s):
    if s and len(s) >= 10 and s[4:5] == "-":
        try:
            from datetime import datetime
            return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            pass
    return s or ""


def _dias_atras(s):
    try:
        from datetime import date, datetime
        d = datetime.strptime((s or "")[:10], "%Y-%m-%d").date()
        dias = (date.today() - d).days
        if dias == 0: return "hoje"
        if dias < 30: return f"{dias}d"
        if dias < 365: return f"{dias//30}m"
        return f"{dias//365}a"
    except Exception:
        return ""


def _btn_item(icone, label, desc, cor, fn):
    c = ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Icon(icone, size=14, color=cor),
                bgcolor=ft.Colors.with_opacity(0.12, cor),
                border_radius=7, width=30, height=30,
                alignment=ft.alignment.Alignment(0, 0),
            ),
            ft.Column([
                ft.Text(label, size=12, color=TXT, weight=ft.FontWeight.W_500),
                ft.Text(desc, size=10, color=SEC),
            ], spacing=0, tight=True, expand=True),
            ft.Icon("chevron_right_rounded", size=14, color=MUT),
        ], spacing=10),
        bgcolor=CARD,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
        ink=True,
    )
    c.on_click = lambda e: fn()
    return c


# ── Abas de conteudo ──────────────────────────────────────────────────────────

def _aba_diagnosticos(page, area, navegar_fn):
    area.controls.clear()
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        rows = conn.execute("""
            SELECT id, titulo, cid, descricao, status, certeza,
                   data_diagnostico
            FROM diagnosticos
            WHERE sistema = ? AND ativo = 1
            ORDER BY status, data_diagnostico DESC
        """, (_SISTEMA,)).fetchall()
        conn.close()
    except Exception:
        rows = []

    _STATUS_COR = {"ativo": LAR, "cronico": VERM, "resolvido": VERD, "suspeito": AMAR}

    if not rows:
        area.controls.append(ft.Container(
            content=ft.Column([
                ft.Icon("diagnosis_rounded", size=40, color=MUT),
                ft.Text("Nenhum diagnóstico cardíaco.", size=13, color=SEC),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            alignment=ft.alignment.Alignment(0, 0), padding=30,
        ))
    else:
        for r in rows:
            cor = _STATUS_COR.get(r[4], MUT)
            area.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(r[1], size=13, color=TXT,
                                weight=ft.FontWeight.W_700, expand=True),
                        ft.Container(
                            content=ft.Text(r[5] or "", size=9, color=cor,
                                            weight=ft.FontWeight.W_600),
                            bgcolor=ft.Colors.with_opacity(0.12, cor),
                            border_radius=5,
                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        ),
                    ], spacing=6),
                    ft.Row([
                        ft.Text(f"CID {r[2]}", size=10, color=AZUL,
                                visible=bool(r[2])),
                        ft.Text(_para_display(r[6]), size=10, color=MUT),
                    ], spacing=8),
                    ft.Text((r[3] or "")[:80], size=11, color=SEC,
                            visible=bool(r[3])),
                ], spacing=3),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                border=ft.Border(
                    left=ft.BorderSide(3, cor),
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
            ))

    # botao ir para tela completa
    btn_ver = ft.Container(
        content=ft.Row([
            ft.Icon("open_in_new_rounded", size=13, color=AZUL),
            ft.Text("Ver / gerenciar todos os diagnósticos",
                    size=12, color=AZUL),
        ], spacing=6, tight=True),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border_radius=8,
        bgcolor=ft.Colors.with_opacity(0.08, AZUL),
        border=ft.border.all(1, ft.Colors.with_opacity(0.25, AZUL)),
        ink=True,
        margin=ft.margin.only(top=8),
    )
    btn_ver.on_click = lambda e: navegar_fn("diagnosticos")
    area.controls.append(btn_ver)


def _aba_exames(page, area, navegar_fn):
    area.controls.clear()
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        like_clauses = " OR ".join(
            ["LOWER(e.tipo_exame) LIKE ?"] * len(_KW_EXAMES)
        )
        rows = conn.execute(f"""
            SELECT e.id, e.tipo_exame, e.data_exame, e.laboratorio,
                   COUNT(er.id) as n_params
            FROM exames e
            LEFT JOIN exame_resultados er ON er.exame_id = e.id
            WHERE ({like_clauses})
              AND (e.status IS NULL OR e.status NOT IN ('rascunho','revisao'))
            GROUP BY e.id
            ORDER BY e.data_exame DESC LIMIT 20
        """, [f"%{k}%" for k in _KW_EXAMES]).fetchall()

        # exames por sistema cardiaco
        rows2 = conn.execute("""
            SELECT COALESCE(ep.nome_oficial, er.parametro) as nome,
                   er.valor, er.unidade, er.nivel_interpretacao,
                   e.data_exame
            FROM exame_resultados er
            JOIN exames e ON e.id = er.exame_id
            JOIN exames_padrao ep ON ep.id = er.exame_padrao_id
            WHERE ep.sistema = ?
              AND er.valor IS NOT NULL
              AND (e.status IS NULL OR e.status NOT IN ('rascunho','revisao'))
            ORDER BY e.data_exame DESC LIMIT 15
        """, (_SISTEMA,)).fetchall()
        conn.close()
    except Exception:
        rows = []; rows2 = []

    _NIVEL_COR = {"critico_alto": VERM, "alto": LAR, "baixo": LAR,
                  "critico_baixo": VERM, "otimo": VERD}

    if rows2:
        area.controls.append(ft.Text("Resultados de Laboratório",
                                     size=11, color=MUT,
                                     weight=ft.FontWeight.W_600))
        for r in rows2:
            cor_n = _NIVEL_COR.get(r[3], SEC)
            area.controls.append(ft.Container(
                content=ft.Row([
                    ft.Text(r[0], size=12, color=TXT, expand=True,
                            no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(f"{r[1]} {r[2] or ''}".strip(), size=12,
                            color=cor_n, weight=ft.FontWeight.W_700),
                    ft.Text(_dias_atras(r[4]), size=10, color=MUT),
                ], spacing=8),
                padding=ft.padding.symmetric(vertical=6),
                border=ft.Border(bottom=ft.BorderSide(1, BD)),
            ))
        area.controls.append(ft.Container(height=8))

    if rows:
        area.controls.append(ft.Text("Exames de Imagem / Funcionais",
                                     size=11, color=MUT,
                                     weight=ft.FontWeight.W_600))
        for r in rows:
            area.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("description_rounded", size=13, color=COR),
                    ft.Text((r[1] or "")[:40], size=12, color=TXT, expand=True,
                            no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(_para_display(r[2]), size=10, color=MUT),
                ], spacing=8),
                padding=ft.padding.symmetric(vertical=6),
                border=ft.Border(bottom=ft.BorderSide(1, BD)),
            ))

    if not rows and not rows2:
        area.controls.append(ft.Container(
            content=ft.Column([
                ft.Icon("science_rounded", size=40, color=MUT),
                ft.Text("Nenhum exame cardíaco encontrado.", size=13, color=SEC),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            alignment=ft.alignment.Alignment(0, 0), padding=30,
        ))


def _aba_historico(page, area):
    area.controls.clear()
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        like_clauses = " OR ".join(
            ["LOWER(hm.descricao) LIKE ? OR LOWER(hm.titulo) LIKE ?"] * len(_KW_HISTORICO)
        )
        params = []
        for k in _KW_HISTORICO:
            params += [f"%{k}%", f"%{k}%"]
        rows = conn.execute(f"""
            SELECT hm.titulo, hm.descricao, hm.data_aprox,
                   hm.tipo, hm.sequela, hm.alerta
            FROM historico_medico hm
            WHERE ({like_clauses})
            ORDER BY hm.data_aprox DESC
        """, params).fetchall()
        conn.close()
    except Exception:
        rows = []

    _TIPO_COR = {"cirurgia": VERM, "procedimento": LAR, "diagnostico": AZUL,
                 "internacao": AMAR, "condicao_cronica": ROXO}

    if not rows:
        area.controls.append(ft.Container(
            content=ft.Column([
                ft.Icon("history_rounded", size=40, color=MUT),
                ft.Text("Nenhum histórico cardíaco.", size=13, color=SEC),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            alignment=ft.alignment.Alignment(0, 0), padding=30,
        ))
    else:
        for r in rows:
            cor = _TIPO_COR.get(r[3], SEC)
            area.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            content=ft.Text(r[3] or "", size=9, color=cor,
                                            weight=ft.FontWeight.W_600),
                            bgcolor=ft.Colors.with_opacity(0.12, cor),
                            border_radius=5,
                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        ),
                        ft.Container(expand=True),
                        ft.Text(r[2] or "", size=10, color=MUT),
                    ], spacing=6),
                    ft.Text(r[0], size=13, color=TXT,
                            weight=ft.FontWeight.W_700),
                    ft.Text((r[4] or r[1] or "")[:120], size=11, color=SEC),
                ], spacing=4),
                bgcolor=ft.Colors.with_opacity(0.05, cor),
                border_radius=10,
                padding=ft.padding.all(12),
                border=ft.Border(
                    left=ft.BorderSide(3, cor),
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
            ))


def _aba_medicos(page, area, navegar_fn):
    area.controls.clear()
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        like_clauses = " OR ".join(
            ["LOWER(m.nome) LIKE ? OR LOWER(COALESCE(e.nome, m.especialidade)) LIKE ?"]
            * len(_KW_MEDICOS)
        )
        params = []
        for k in _KW_MEDICOS:
            params += [f"%{k}%", f"%{k}%"]
        rows = conn.execute(f"""
            SELECT m.id, m.nome, COALESCE(e.nome, m.especialidade) as esp,
                   m.telefone, m.whatsapp
            FROM medicos m
            LEFT JOIN especialidades e ON e.id = m.especialidade_id
            WHERE m.ativo = 1 AND ({like_clauses})
            ORDER BY m.nome
        """, params).fetchall()
        conn.close()
    except Exception:
        rows = []

    if not rows:
        area.controls.append(ft.Container(
            content=ft.Column([
                ft.Icon("person_search_rounded", size=40, color=MUT),
                ft.Text("Nenhum médico cardíaco cadastrado.", size=13, color=SEC),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            alignment=ft.alignment.Alignment(0, 0), padding=30,
        ))
    else:
        for r in rows:
            area.controls.append(ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon("person_rounded", size=18, color=VERD),
                        bgcolor=ft.Colors.with_opacity(0.12, VERD),
                        border_radius=20, width=40, height=40,
                        alignment=ft.alignment.Alignment(0, 0),
                    ),
                    ft.Column([
                        ft.Text(r[1] or "—", size=13, color=TXT,
                                weight=ft.FontWeight.W_600),
                        ft.Text(r[2] or "sem especialidade",
                                size=11, color=SEC),
                    ], spacing=2, expand=True),
                    ft.Icon("chevron_right_rounded", size=14, color=MUT),
                ], spacing=12,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                border=ft.border.all(1, BD),
                ink=True,
            ))


def _aba_remedios(page, area):
    area.controls.clear()
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        like_clauses = " OR ".join(
            ["LOWER(r.nome) LIKE ? OR LOWER(r.principio_ativo) LIKE ?"]
            * len(_KW_REMEDIOS)
        )
        params = []
        for k in _KW_REMEDIOS:
            params += [f"%{k}%", f"%{k}%"]
        rows = conn.execute(f"""
            SELECT r.nome, r.dosagem, r.ativo, r.principio_ativo
            FROM remedios r
            WHERE ({like_clauses})
            ORDER BY r.ativo DESC, r.nome
        """, params).fetchall()
        conn.close()
    except Exception:
        rows = []

    ativos   = [r for r in rows if r[2]]
    inativos = [r for r in rows if not r[2]]

    def _chip(r):
        cor = VERD if r[2] else MUT
        return ft.Container(
            content=ft.Row([
                ft.Icon("circle_rounded", size=6, color=cor),
                ft.Text(f"{r[0]} {r[1] or ''}".strip()[:32],
                        size=11, color=TXT if r[2] else MUT),
            ], spacing=5, tight=True),
            bgcolor=CARD, border_radius=16,
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border=ft.border.all(1, BD2),
        )

    if not rows:
        area.controls.append(ft.Container(
            content=ft.Column([
                ft.Icon("medication_rounded", size=40, color=MUT),
                ft.Text("Nenhum medicamento cardíaco.", size=13, color=SEC),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            alignment=ft.alignment.Alignment(0, 0), padding=30,
        ))
    else:
        if ativos:
            area.controls.append(ft.Text("Em uso", size=11, color=VERD,
                                          weight=ft.FontWeight.W_600))
            area.controls.append(ft.Row(
                [_chip(r) for r in ativos], spacing=6, wrap=True))
        if inativos:
            area.controls.append(ft.Container(height=8))
            area.controls.append(ft.Text("Histórico", size=11, color=MUT,
                                          weight=ft.FontWeight.W_600))
            area.controls.append(ft.Row(
                [_chip(r) for r in inativos], spacing=6, wrap=True))


def _aba_eventos(page, area):
    """Topico especifico: eventos cardiacos — stents, cirurgias, internacoes."""
    area.controls.clear()

    # stents do historico_medico
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        rows_hist = conn.execute("""
            SELECT titulo, descricao, data_aprox, tipo, sequela
            FROM historico_medico
            WHERE LOWER(titulo) LIKE '%stent%'
               OR LOWER(descricao) LIKE '%stent%'
               OR LOWER(titulo) LIKE '%infart%'
               OR LOWER(titulo) LIKE '%coronar%'
               OR LOWER(titulo) LIKE '%revascular%'
               OR LOWER(titulo) LIKE '%bypass%'
               OR LOWER(titulo) LIKE '%safena%'
               OR LOWER(titulo) LIKE '%mamaria%'
            ORDER BY data_aprox DESC
        """).fetchall()

        rows_int = conn.execute("""
            SELECT i.hospital, i.motivo, i.data_entrada, i.data_saida,
                   i.cid_entrada, i.cid_saida, i.diagnostico_saida
            FROM internacoes i
            WHERE LOWER(i.motivo) LIKE '%cardiaco%'
               OR LOWER(i.motivo) LIKE '%coronar%'
               OR LOWER(i.motivo) LIKE '%infarto%'
               OR LOWER(i.cid_entrada) LIKE 'i%'
            ORDER BY i.data_entrada DESC
        """).fetchall()
        conn.close()
    except Exception:
        rows_hist = []; rows_int = []

    # card stents
    area.controls.append(ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon("favorite_rounded", size=16, color=VERM),
                ft.Text("Histórico Coronariano", size=13, color=TXT,
                        weight=ft.FontWeight.W_700),
            ], spacing=8),
            ft.Container(height=4),
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("circle_rounded", size=8, color=VERM),
                        ft.Text("8 stents coronarianos implantados",
                                size=12, color=TXT),
                    ], spacing=8),
                    ft.Row([
                        ft.Icon("circle_rounded", size=8, color=LAR),
                        ft.Text("Cirurgia de revascularização (2 safenas + 2 mamárias)",
                                size=12, color=TXT),
                    ], spacing=8),
                    ft.Row([
                        ft.Icon("circle_rounded", size=8, color=AMAR),
                        ft.Text("Evento coronariano agudo — Manaus ~2007",
                                size=12, color=TXT),
                    ], spacing=8),
                ], spacing=6),
                bgcolor=ft.Colors.with_opacity(0.06, VERM),
                border_radius=8, padding=ft.padding.all(12),
            ),
        ], spacing=0),
        bgcolor=CARD, border_radius=12,
        padding=ft.padding.all(14),
        border=ft.Border(
            left=ft.BorderSide(3, VERM),
            top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
            right=ft.BorderSide(1, BD),
        ),
    ))

    # eventos do historico
    if rows_hist:
        area.controls.append(ft.Container(height=8))
        for r in rows_hist:
            area.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(r[0], size=13, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True),
                        ft.Text(r[2] or "", size=10, color=MUT),
                    ], spacing=6),
                    ft.Text((r[4] or r[1] or "")[:100], size=11, color=SEC),
                ], spacing=3),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                border=ft.border.all(1, BD),
            ))

    # internacoes cardiacas
    if rows_int:
        area.controls.append(ft.Container(height=8))
        area.controls.append(ft.Text("Internações", size=11, color=MUT,
                                      weight=ft.FontWeight.W_600))
        for r in rows_int:
            area.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(r[0] or "Hospital", size=13, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True),
                        ft.Text(_para_display(r[2]), size=10, color=MUT),
                    ], spacing=6),
                    ft.Text(r[1] or "", size=11, color=SEC),
                    ft.Text(r[6] or r[4] or "", size=10, color=MUT),
                ], spacing=3),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                border=ft.border.all(1, BD),
            ))


# ── TELA PRINCIPAL ────────────────────────────────────────────────────────────

def criar_tela_orgao_cardiaco(page: ft.Page, voltar_fn=None):
    lay      = Layout(page)
    aba_ativa = [0]
    area     = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
    _montado = [False]

    def _navegar(destino):
        if destino == "diagnosticos":
            from telas.tela_diagnosticos import criar_tela_diagnosticos
            def _voltar_diag():
                page.controls.clear()
                page.controls.append(_tela)
                try: page.update()
                except Exception: pass
            nova = criar_tela_diagnosticos(
                page, voltar_fn=_voltar_diag, sistema_filtro=_SISTEMA)
            page.controls.clear()
            page.controls.append(nova)
            try: page.update()
            except Exception: pass

    def _carregar_aba():
        area.controls.clear()
        idx = aba_ativa[0]
        if   idx == 0: _aba_diagnosticos(page, area, _navegar)
        elif idx == 1: _aba_exames(page, area, _navegar)
        elif idx == 2: _aba_historico(page, area)
        elif idx == 3: _aba_medicos(page, area, _navegar)
        elif idx == 4: _aba_remedios(page, area)
        elif idx == 5: _aba_eventos(page, area)
        if _montado[0]:
            try: page.update()
            except Exception: pass

    barra_abas = ft.Row(spacing=0, scroll=ft.ScrollMode.AUTO)

    def _rebuild_abas():
        barra_abas.controls.clear()
        for i, (label, icone, cor) in enumerate(_ABAS):
            ativo = i == aba_ativa[0]
            tab = ft.Container(
                content=ft.Column([
                    ft.Icon(icone, size=14,
                            color=cor if ativo else MUT),
                    ft.Text(label, size=9,
                            color=cor if ativo else MUT,
                            weight=ft.FontWeight.W_600 if ativo
                                   else ft.FontWeight.NORMAL),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=2, tight=True),
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                border=ft.Border(
                    bottom=ft.BorderSide(2, cor if ativo else "#00000000")),
                ink=True,
            )
            tab.on_click = lambda e, idx=i: _trocar_aba(idx)
            barra_abas.controls.append(tab)
        if _montado[0]:
            try: page.update()
            except Exception: pass

    def _trocar_aba(idx):
        aba_ativa[0] = idx
        _rebuild_abas()
        _carregar_aba()

    _rebuild_abas()
    _carregar_aba()

    cabecalho = lay.criar_cabecalho(
        "Sistema Cardíaco",
        lambda e=None: voltar_fn() if voltar_fn else None,
        icone_titulo="favorite_rounded",
        cor_titulo=COR,
    )

    corpo = ft.Column([
        ft.Container(height=lay.spacer_topo, bgcolor=BG),
        cabecalho,
        ft.Container(
            content=barra_abas,
            border=ft.Border(bottom=ft.BorderSide(1, BD)),
        ),
        ft.Container(
            content=area,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            expand=True,
        ),
    ], spacing=0, expand=True)

    _tela = ft.Container(bgcolor=BG, expand=True, content=corpo)
    _montado[0] = True
    return _tela
