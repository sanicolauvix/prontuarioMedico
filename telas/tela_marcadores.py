# -*- coding: utf-8 -*-
# Prontuario | telas/tela_marcadores.py
import flet as ft
import logging
import sqlite3

from shared.layout import Layout

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
ROXO = "#BC8CFF"; AZUL = "#58A6FF"; VERD = "#3FB950"
AMAR = "#D29922"; VERM = "#F85149"

log = logging.getLogger(__name__)

# ── Categorias e marcadores configurados ────────────────────────────────────
_CATEGORIAS = [
    ("Metabolico", "bar_chart_rounded", AMAR, [
        ("Glicose",        "mg/dL",  "70-100",  ["glicose", "glucose", "glicemia"]),
        ("Glicemia Jejum", "mg/dL",  "70-99",   ["glicemia em jejum", "glicose em jejum"]),
        ("HbA1c",          "%",      "<5.7",    ["hba1c", "hemoglobina glicada"]),
        ("Insulina",       "uUI/mL", "2-25",    ["insulina"]),
        ("Acido Urico",    "mg/dL",  "<7.0",    ["acido urico", "urico", "uratos"]),
        ("HOMA-IR",        "",       "<2.7",    ["homa", "homa-ir"]),
    ]),
    ("Cardiovascular", "favorite_rounded", "#4ECDC4", [
        ("Pressao Sist.",  "mmHg",  "<120",    ["sistolica", "pressao arterial"]),
        ("Pressao Diast.", "mmHg",  "<80",     ["diastolica"]),
        ("Colesterol",     "mg/dL", "<200",    ["colesterol total"]),
        ("HDL",            "mg/dL", ">60",     ["hdl"]),
        ("LDL",            "mg/dL", "<100",    ["ldl"]),
        ("Triglicerides",  "mg/dL", "<150",    ["triglicerides", "triglicerideo"]),
        ("nao-HDL",        "mg/dL", "<130",    ["nao-hdl", "nao hdl"]),
    ]),
    ("Inflamacao", "local_fire_department_rounded", "#FF7675", [
        ("PCR",            "mg/L",  "<1.0",    ["pcr", "proteina c reativa"]),
        ("PCR ultrassens", "mg/L",  "<1.0",    ["pcr ultrassens", "proteina c reativa ultr"]),
        ("VHS",            "mm/h",  "<20",     ["vhs", "velocidade de hemossediment"]),
        ("Leucocitos",     "K/uL",  "4.5-11",  ["leucocitos", "leucocito"]),
        ("Ferritina",      "ng/mL", "12-300",  ["ferritina"]),
        ("Fibrinogenio",   "mg/dL", "200-400", ["fibrinogenio"]),
        ("IL-6",           "pg/mL", "<7.0",    ["il-6", "interleucina 6"]),
    ]),
    ("Hormonal", "psychology_alt_rounded", "#A29BFE", [
        ("TSH",            "uUI/mL", "0.5-4.0", ["tsh"]),
        ("T4 Livre",       "ng/dL",  "0.8-1.8", ["t4 livre", "t4l", "tiroxina livre"]),
        ("T3 Livre",       "pg/mL",  "2.3-4.2", ["t3 livre", "t3l"]),
        ("Cortisol",       "ug/dL",  "6-23",    ["cortisol"]),
        ("Testosterona",   "ng/dL",  "240-950", ["testosterona total"]),
        ("Estradiol",      "pg/mL",  "10-40",   ["estradiol"]),
        ("DHEA-S",         "ug/dL",  "80-560",  ["dhea", "dhea-s"]),
        ("Insulina",       "uUI/mL", "2-25",    ["insulina"]),
    ]),
    ("Vitaminas", "wb_sunny_rounded", "#FDCB6E", [
        ("Vitamina D",     "ng/mL", "40-80",   ["vitamina d", "25-oh", "25oh", "colecalciferol"]),
        ("Vitamina B12",   "pg/mL", "400-900", ["b12", "vitamina b12", "cobalamina"]),
        ("Folato",         "ng/mL", ">10",     ["folato", "acido folico", "folico"]),
        ("Vitamina B6",    "ng/mL", "20-100",  ["b6", "piridoxal"]),
        ("Vitamina E",     "mg/L",  "5-18",    ["vitamina e", "tocoferol"]),
        ("Zinco",          "ug/dL", "60-120",  ["zinco"]),
        ("Magnesio",       "mg/dL", "1.6-2.6", ["magnesio"]),
    ]),
    ("Renal", "water_drop_rounded", AZUL, [
        ("Creatinina",     "mg/dL",  "0.6-1.2", ["creatinina"]),
        ("Ureia",          "mg/dL",  "15-45",   ["ureia", "ureia serica"]),
        ("TFG",            "mL/min", ">60",     ["tfg", "taxa de filtracao glomerular", "tfge"]),
        ("Microalbuminuria","ug/min", "<30",     ["microalbuminuria", "albumina urinaria"]),
        ("Cistatina C",    "mg/L",   "0.6-1.0", ["cistatina"]),
    ]),
    ("Hepatico", "science_rounded", VERD, [
        ("ALT/TGP",        "U/L",   "<40",     ["alt", "tgp", "alanina aminotransferase"]),
        ("AST/TGO",        "U/L",   "<40",     ["ast", "tgo", "aspartato aminotransferase"]),
        ("GGT",            "U/L",   "<50",     ["ggt", "gama glutamiltransferase"]),
        ("Bilirrubina T.", "mg/dL", "0.2-1.2", ["bilirrubina total"]),
        ("Fosfatase Alc.", "U/L",   "40-130",  ["fosfatase alcalina", "fal"]),
        ("Albumina",       "g/dL",  "3.5-5.0", ["albumina serica"]),
    ]),
]


def _avaliar_cor(valor_str: str, referencia_str: str) -> str:
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
    return SEC


def _fmt_data(d: str) -> str:
    if d and len(d) >= 10:
        return f"{d[8:10]}/{d[5:7]}/{d[2:4]}"
    return ""


def _e_fora_range(val: float, ref: str) -> bool:
    if not ref or val is None:
        return False
    ref = ref.strip()
    try:
        if ref.startswith("<"):
            return float(val) >= float(ref[1:])
        if ref.startswith(">"):
            return float(val) <= float(ref[1:])
        if "-" in ref:
            lo, hi = ref.split("-", 1)
            return not (float(lo) <= float(val) <= float(hi))
    except Exception:
        pass
    return False


def criar_tela_marcadores(page: ft.Page, voltar_fn) -> ft.Container:
    from dados.model_prontuario import DB_PATH

    lay      = Layout(page)
    area     = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
    _montado = [False]
    _dados: dict = {}

    # ── Carregar dados ──────────────────────────────────────────
    def _carregar():
        _dados.clear()
        try:
            conn = sqlite3.connect(DB_PATH, timeout=30)
            try:
                for cat, _ico, _cor, marcadores in _CATEGORIAS:
                    for param, unidade, ref_padrao, termos in marcadores:
                        row = None
                        for termo in termos:
                            row = conn.execute("""
                                SELECT r.valor, r.unidade, e.data_exame, 'exame'
                                FROM resultados_estruturados r
                                JOIN exames e ON r.exame_id = e.id
                                WHERE LOWER(r.parametro) LIKE ?
                                  AND r.valor IS NOT NULL AND r.valor != ''
                                ORDER BY e.data_exame DESC LIMIT 1
                            """, (f"%{termo}%",)).fetchone()
                            if row:
                                break
                        # Manual/bluetooth pode ser mais recente
                        try:
                            for termo in termos:
                                mrow = conn.execute("""
                                    SELECT CAST(valor AS TEXT), unidade,
                                           data_medicao, fonte
                                    FROM marcadores_leituras
                                    WHERE LOWER(parametro) LIKE ?
                                    ORDER BY data_medicao DESC LIMIT 1
                                """, (f"%{termo}%",)).fetchone()
                                if mrow:
                                    if not row or (mrow[2] or "") > (row[2] or ""):
                                        row = mrow
                                    break
                        except Exception:
                            pass
                        if row:
                            val, unit, data, fonte = row
                            _dados[(cat, param)] = {
                                "val":   str(val),
                                "unit":  unit or unidade,
                                "ref":   ref_padrao,
                                "data":  data or "",
                                "fonte": fonte,
                            }
            finally:
                conn.close()
        except Exception as ex:
            log.exception("[MARC] carregar: %s", ex)
        _rebuild()

    # ── Historico de um marcador ────────────────────────────────
    def _mostrar_historico(param: str, termos: list, cor: str):
        linhas = []
        try:
            conn = sqlite3.connect(DB_PATH, timeout=30)
            try:
                for termo in termos:
                    rows = conn.execute("""
                        SELECT r.valor, r.unidade, e.data_exame
                        FROM resultados_estruturados r
                        JOIN exames e ON r.exame_id = e.id
                        WHERE LOWER(r.parametro) LIKE ?
                          AND r.valor IS NOT NULL AND r.valor != ''
                        ORDER BY e.data_exame DESC LIMIT 10
                    """, (f"%{termo}%",)).fetchall()
                    if rows:
                        linhas.extend([("exame", v, u, d) for v, u, d in rows])
                        break
                try:
                    for termo in termos:
                        mrows = conn.execute("""
                            SELECT CAST(valor AS TEXT), unidade, data_medicao
                            FROM marcadores_leituras
                            WHERE LOWER(parametro) LIKE ?
                            ORDER BY data_medicao DESC LIMIT 10
                        """, (f"%{termo}%",)).fetchall()
                        if mrows:
                            linhas.extend([("manual", v, u, d) for v, u, d in mrows])
                            break
                except Exception:
                    pass
            finally:
                conn.close()
        except Exception:
            pass

        linhas.sort(key=lambda x: x[3] or "", reverse=True)

        ref_ov = [None]

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try:
                page.update()
            except Exception:
                pass

        items = []
        for fonte, val, unit, data in linhas[:12]:
            items.append(ft.Container(
                content=ft.Row([
                    ft.Icon("circle", size=8,
                            color=AZUL if fonte == "exame" else VERD),
                    ft.Text(_fmt_data(data), size=11, color=SEC, width=70),
                    ft.Text(str(val), size=13,
                            weight=ft.FontWeight.W_700, color=TXT),
                    ft.Text(str(unit or ""), size=10, color=MUT),
                ], spacing=8),
                padding=ft.padding.symmetric(horizontal=4, vertical=6),
                border=ft.Border(bottom=ft.BorderSide(1, BD)),
            ))

        if not items:
            items.append(ft.Text("Sem leituras registradas", size=12, color=MUT))

        legenda = ft.Row([
            ft.Icon("circle", size=8, color=AZUL),
            ft.Text("Exame PDF", size=10, color=SEC),
            ft.Container(width=12),
            ft.Icon("circle", size=8, color=VERD),
            ft.Text("Manual/BT", size=10, color=SEC),
        ], spacing=4)

        btn_fechar = ft.Container(
            content=ft.Text("Fechar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            border_radius=8, bgcolor=f"{SEC}22", ink=True,
        )
        btn_fechar.on_click = _fechar

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(width=8, height=8, border_radius=4, bgcolor=cor),
                        ft.Text(param, size=15, color=TXT,
                                weight=ft.FontWeight.W_700),
                    ], spacing=8),
                    ft.Container(height=6),
                    legenda,
                    ft.Divider(color=BD, height=1),
                    ft.Column(items, spacing=0, scroll=ft.ScrollMode.AUTO,
                              height=min(len(items) * 38 + 10, 300)),
                    ft.Container(height=12),
                    ft.Row([btn_fechar],
                           alignment=ft.MainAxisAlignment.CENTER),
                ], tight=True, spacing=6),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20), width=340,
            ),
            bgcolor="#CC000000", expand=True,
            alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try:
            page.update()
        except Exception:
            pass

    # ── Overlay: Claudia pergunta contexto apos leitura anormal ────
    def _claudia_perguntar_contexto(param, val, unidade, ref, leitura_id):
        ref_ov = [None]

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try:
                page.update()
            except Exception:
                pass

        tf_ctx = ft.TextField(
            label="O que estava acontecendo antes?",
            hint_text="Ex: acabei de comer, estresse no trabalho, medicacao nova...",
            bgcolor=CARD, border_color=BD2, focused_border_color=ROXO,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, multiline=True, min_lines=2, max_lines=3,
        )

        def _salvar_ctx(e):
            ctx = (tf_ctx.value or "").strip()
            if ctx and leitura_id:
                try:
                    conn = sqlite3.connect(DB_PATH, timeout=30)
                    try:
                        conn.execute(
                            "UPDATE marcadores_leituras SET contexto = ? WHERE id = ?",
                            (ctx, leitura_id))
                        conn.commit()
                    finally:
                        conn.close()
                except Exception as ex:
                    log.warning("[MARC] salvar_ctx: %s", ex)
            _fechar()

        btn_pular = ft.Container(
            content=ft.Text("Pular", size=12, color=SEC),
            padding=ft.padding.symmetric(horizontal=14, vertical=9),
            border_radius=8, bgcolor=f"{SEC}22", ink=True,
        )
        btn_pular.on_click = _fechar

        btn_ctx = ft.Container(
            content=ft.Text("Salvar contexto", size=12, color=ROXO,
                            weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=14, vertical=9),
            border_radius=8, bgcolor=f"{ROXO}22", ink=True,
        )
        btn_ctx.on_click = _salvar_ctx

        val_str = f"{val:.1f}" if isinstance(val, float) else str(val)
        unit_str = f" {unidade}" if unidade else ""

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("psychology_rounded", size=18, color=ROXO),
                        ft.Text("Claudia", size=14, color=ROXO,
                                weight=ft.FontWeight.W_700),
                    ], spacing=6),
                    ft.Container(height=4),
                    ft.Text(
                        f"Registrei {val_str}{unit_str} para {param}.",
                        size=13, color=TXT, weight=ft.FontWeight.W_600,
                    ),
                    ft.Text(
                        f"Valor fora do esperado ({ref}).",
                        size=12, color=VERM,
                    ),
                    ft.Container(height=8),
                    tf_ctx,
                    ft.Container(height=12),
                    ft.Row([btn_pular, btn_ctx], spacing=8,
                           alignment=ft.MainAxisAlignment.END),
                ], tight=True, spacing=4),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20), width=320,
            ),
            bgcolor="#CC000000", expand=True,
            alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try:
            page.update()
        except Exception:
            pass

    # ── Overlay: adicionar leitura manual ───────────────────────
    def _abrir_form():
        ref_ov = [None]

        todas_cats = [cat for cat, _, _, _ in _CATEGORIAS]
        params_por_cat = {
            cat: [(p, u, r) for p, u, r, _ in marc]
            for cat, _, _, marc in _CATEGORIAS
        }

        dd_cat = ft.Dropdown(
            label="Categoria",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            options=[ft.dropdown.Option(c) for c in todas_cats],
        )
        dd_param = ft.Dropdown(
            label="Marcador",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            options=[],
        )
        tf_valor = ft.TextField(
            label="Valor",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        tf_data = ft.TextField(
            label="Data (YYYY-MM-DD)",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            value=__import__("datetime").date.today().isoformat(),
        )
        txt_unit = ft.Text("", size=11, color=SEC)

        def _on_cat(e):
            cat_sel = dd_cat.value
            dd_param.options = [
                ft.dropdown.Option(p)
                for p, _, _ in params_por_cat.get(cat_sel, [])
            ]
            dd_param.value = None
            txt_unit.value = ""
            try:
                page.update()
            except Exception:
                pass

        def _on_param(e):
            cat_sel  = dd_cat.value
            param_sel = dd_param.value
            for p, u, _ in params_por_cat.get(cat_sel, []):
                if p == param_sel:
                    txt_unit.value = u
                    break
            try:
                page.update()
            except Exception:
                pass

        dd_cat.on_change   = _on_cat
        dd_param.on_change = _on_param

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try:
                page.update()
            except Exception:
                pass

        def _salvar(e):
            cat_sel   = dd_cat.value
            param_sel = dd_param.value
            val_str   = (tf_valor.value or "").strip()
            data_str  = (tf_data.value or "").strip()
            if not cat_sel or not param_sel or not val_str or not data_str:
                return
            unidade = ref_txt = ""
            for p, u, r in params_por_cat.get(cat_sel, []):
                if p == param_sel:
                    unidade = u
                    ref_txt = r
                    break
            try:
                val_num = float(val_str.replace(",", "."))
                leitura_id = None
                conn = sqlite3.connect(DB_PATH, timeout=30)
                try:
                    cur = conn.execute("""
                        INSERT INTO marcadores_leituras
                            (parametro, categoria, valor, unidade, referencia,
                             data_medicao, fonte)
                        VALUES (?, ?, ?, ?, ?, ?, 'manual')
                    """, (param_sel, cat_sel, val_num, unidade, ref_txt, data_str))
                    leitura_id = cur.lastrowid
                    conn.commit()
                finally:
                    conn.close()
                _fechar()
                _carregar()
                if _e_fora_range(val_num, ref_txt):
                    _claudia_perguntar_contexto(
                        param_sel, val_num, unidade, ref_txt, leitura_id)
            except Exception as ex:
                log.exception("[MARC] salvar: %s", ex)

        btn_cancel = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{SEC}22", ink=True,
        )
        btn_cancel.on_click = _fechar

        btn_ok = ft.Container(
            content=ft.Text("Salvar", size=13, color=VERD,
                            weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{VERD}22", ink=True,
        )
        btn_ok.on_click = _salvar

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Nova Leitura Manual", size=15, color=TXT,
                            weight=ft.FontWeight.W_700, text_align="center"),
                    ft.Container(height=6),
                    dd_cat,
                    dd_param,
                    ft.Row([
                        ft.Container(content=tf_valor, expand=True),
                        ft.Container(
                            content=txt_unit,
                            padding=ft.padding.only(top=14),
                            width=50,
                        ),
                    ], spacing=8),
                    tf_data,
                    ft.Container(height=8),
                    ft.Row([btn_cancel, btn_ok], spacing=8,
                           alignment=ft.MainAxisAlignment.CENTER),
                ], spacing=10, tight=True),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20), width=320,
            ),
            bgcolor="#CC000000", expand=True,
            alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try:
            page.update()
        except Exception:
            pass

    # ── Rebuild lista ───────────────────────────────────────────
    def _rebuild():
        area.controls.clear()

        # resumo rapido: quantos marcadores com dado / total
        total = sum(len(m) for _, _, _, m in _CATEGORIAS)
        com_dado = len(_dados)
        area.controls.append(
            ft.Container(
                content=ft.Row([
                    ft.Icon("info_outline_rounded", size=12, color=SEC),
                    ft.Text(
                        f"{com_dado} de {total} marcadores com leituras",
                        size=11, color=SEC,
                    ),
                ], spacing=6),
                padding=ft.padding.symmetric(horizontal=4, vertical=2),
            )
        )

        for cat, ico, cor, marcadores in _CATEGORIAS:
            # conta marcadores com dado nesta categoria
            n_com = sum(1 for p, _, _, _ in marcadores if (cat, p) in _dados)
            if n_com == 0:
                badge_cor = MUT
            elif n_com == len(marcadores):
                badge_cor = VERD
            else:
                badge_cor = AMAR

            rows = []
            for param, unidade, ref_padrao, termos in marcadores:
                d = _dados.get((cat, param))
                if d:
                    val_str  = d["val"]
                    unit_str = d["unit"]
                    data_str = _fmt_data(d["data"])
                    s_cor    = _avaliar_cor(val_str, ref_padrao)
                    # ícone de fonte: exame PDF vs manual
                    src_ico  = "description_rounded" if d["fonte"] == "exame" else "edit_rounded"
                else:
                    val_str  = "--"
                    unit_str = unidade
                    data_str = ""
                    s_cor    = MUT
                    src_ico  = "remove_rounded"

                row = ft.Container(
                    content=ft.Row([
                        ft.Container(
                            width=8, height=8, border_radius=4, bgcolor=s_cor,
                        ),
                        ft.Text(param, size=12, color=TXT, expand=True),
                        ft.Text(val_str, size=13,
                                weight=ft.FontWeight.W_700, color=s_cor),
                        ft.Container(
                            content=ft.Text(unit_str, size=9, color=MUT),
                            width=46,
                        ),
                        ft.Container(
                            content=ft.Text(data_str, size=9, color=MUT),
                            width=52,
                        ),
                        ft.Icon(src_ico, size=11, color=MUT),
                    ], spacing=8),
                    padding=ft.padding.symmetric(horizontal=14, vertical=9),
                    border=ft.Border(bottom=ft.BorderSide(1, BD)),
                    ink=True,
                )
                # captura closures corretas
                row.on_click = (
                    lambda e, p=param, t=termos, c=s_cor:
                    _mostrar_historico(p, t, c)
                )
                rows.append(row)

            area.controls.append(
                ft.Column([
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ico, size=12, color=cor),
                            ft.Text(cat.upper(), size=10,
                                    weight=ft.FontWeight.W_700, color=cor),
                            ft.Container(expand=True),
                            ft.Container(
                                width=7, height=7, border_radius=4,
                                bgcolor=badge_cor,
                            ),
                            ft.Text(f"{n_com}/{len(marcadores)}", size=9, color=MUT),
                        ], spacing=6),
                        padding=ft.padding.only(top=4, bottom=6),
                    ),
                    ft.Container(
                        content=ft.Column(rows, spacing=0),
                        bgcolor=CARD,
                        border_radius=10,
                        border=ft.border.all(1, BD),
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                ], spacing=4)
            )

        if _montado[0]:
            try:
                page.update()
            except Exception:
                pass

    # ── Montar tela ─────────────────────────────────────────────
    _carregar()

    btn_add = ft.Container(
        content=ft.Row([
            ft.Icon("add_rounded", size=16, color=VERD),
            ft.Text("Registrar", size=13, color=VERD),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8, ink=True,
    )
    btn_add.on_click = lambda e: _abrir_form()

    cabecalho = lay.criar_cabecalho(
        "Marcadores de Saude", voltar_fn,
        icone_titulo="biotech_rounded",
        cor_titulo=AZUL,
        acoes=[btn_add],
    )
    corpo = lay.criar_corpo(cabecalho, area)
    _montado[0] = True
    return ft.Container(bgcolor=BG, expand=True, content=corpo)
