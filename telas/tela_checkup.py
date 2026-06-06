# -*- coding: utf-8 -*-
# Prontuario | telas/tela_checkup.py
# Dashboard de Checkup Geral de Saude — visao integrada de todos os sistemas
import flet as ft
import sqlite3
import logging
from datetime import datetime, date

from dados.model_prontuario import DB_PATH
from shared.layout import Layout

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; AMAR = "#D29922"
VERM = "#F85149"; ROXO = "#BC8CFF"; LAR  = "#F0883E"
COR_CARD = "#1C2128"

_COR_NIVEL = {
    "critico_baixo": VERM, "baixo": LAR,
    "alto": LAR, "critico_alto": VERM,
    "otimo": VERD, "bom": VERD,
}
_ICO_NIVEL = {
    "critico_baixo": "arrow_downward_rounded",
    "baixo":         "arrow_downward_rounded",
    "alto":          "arrow_upward_rounded",
    "critico_alto":  "arrow_upward_rounded",
    "otimo":         "check_circle_outline_rounded",
}

# Score por nivel: 0-10
_SCORE_NIVEL = {
    "otimo": 10, "bom": 8, "normal": 6,
    "baixo": 4,  "alto": 4,
    "critico_baixo": 1, "critico_alto": 1,
}

# Topicos: nome → (icone, cor, marcadores_chave_esperados, keywords_exame)
# marcadores_chave_esperados: lista de nomes que DEVEM existir — se ausentes, mostra aviso
_TOPICOS = {
    "Transporte O₂": (
        "air_rounded", "#EF5350",
        ["Hemoglobina","Ferritina","Ferro Sérico","Transferrina",
         "Saturação de Transferrina","VCM","RDW"],
        ["hemoglobina","ferritina","ferro serico","ferro sérico","transferrina",
         "saturacao de transferrina","saturação de transferrina","vcm","rdw",
         "hematocrito","hematócrito","hemacias","hemácias","eritrocito","eritrócito",
         "hcm","chcm"],
    ),
    "Imunidade": (
        "shield_rounded", AZUL,
        ["PCR (Proteína C-Reativa)","VHS","Leucócitos","Fibrinogênio","IgA"],
        ["fibrinogenio","fibrinogênio","iga","imunoglobulina",
         "leucocito","leucócito","linfocito","linfócito","nlr","vhs","hemossediment",
         "pcr","proteina c reativa","proteína c reativa","proteina c-reativa",
         "anti-transglutaminase"],
    ),
    "Metabolismo": (
        "local_fire_department_rounded", LAR,
        ["Glicemia de Jejum","Hemoglobina Glicada (HbA1c)","Colesterol HDL",
         "Colesterol LDL","Triglicerídeos"],
        ["glicemia","glicose","hba1c","hemoglobina glicada","frutosamina",
         "glicemia media","insulina","colesterol","triglicerideos","triglicerídeos",
         "vldl","hdl","ldl","nao-hdl","não-hdl","homocisteina","homocisteína"],
    ),
    "Função Renal": (
        "water_drop_rounded", "#4FC3F7",
        ["Creatinina","Ureia","Ácido Úrico","eRFG"],
        ["creatinina","ureia","ácido úrico","acido urico","erfg","erfg",
         "bun","nitrogenio ureico","nitrogênio ureico","tfg","filtração",
         "cistatina"],
    ),
    "Função Hepática": (
        "opacity_rounded", "#A5D6A7",
        ["TGO (AST)","TGP (ALT)","GGT","Albumina"],
        ["tgo","ast","tgp","alt","ggt","bilirrubina","albumina",
         "cpk","ck-mb","ck mb","ldh","lipase","amilase","fosfatase alcalina",
         "proteinas totais","proteínas totais","globulinas"],
    ),
    "Hematologia": (
        "bloodtype_rounded", "#EF9A9A",
        ["Plaquetas","Leucócitos","Neutrófilos Segmentados"],
        ["plaquetas","leucocitos","vcm","hcm","chcm","rdw","mpv",
         "neutrofilo","neutrófilo","basofilo","basófilo",
         "eosinofilo","eosinófilo","monocito","monócito","linfocito","linfócito",
         "nlr","razao neutrofilos"],
    ),
    "Hormônios": (
        "psychology_rounded", ROXO,
        ["TSH","Testosterona Total","T4 Livre"],
        ["tsh","t3","t4","testosterona","shbg","estradiol","dht",
         "pth","paratormonio","paratormônio","cortisol","igf"],
    ),
    "Vitaminas/Minerais": (
        "science_rounded", AMAR,
        ["Vitamina D","Vitamina B12","Ácido Fólico","Zinco","Magnésio"],
        ["vitamina","zinco","magnesio","magnésio","calcio","cálcio",
         "potassio","potássio","sodio","sódio","fosforo","fósforo",
         "selenio","selênio","cobre","manganes","manganês",
         "acido folico","ácido fólico","folato","serotonina"],
    ),
}


def _topico_de(nome_oficial):
    """Retorna o topico ao qual um exame pertence, ou None."""
    n = (nome_oficial or "").lower()
    for topico, (_, _, _, keywords) in _TOPICOS.items():
        if any(k in n for k in keywords):
            return topico
    return None


def _calcular_scores(marcadores):
    """
    Retorna {topico: {"score": float|None, "itens": [...],
                      "n_crit": int, "n_fora": int,
                      "ausentes": [nomes esperados mas sem dado]}}
    e nota_geral.
    Topicos sem nenhum dado ficam com score=None e aparecem como "Sem dados".
    """
    por_topico = {t: [] for t in _TOPICOS}
    for m in marcadores:
        topico = _topico_de(m.get("nome_oficial",""))
        if topico:
            por_topico[topico].append(m)

    resultado = {}
    scores_validos = []

    for topico, (_, _, chave_esperados, _) in _TOPICOS.items():
        itens = por_topico[topico]

        # marcadores chave ausentes
        nomes_presentes = {(m.get("nome_oficial") or "").lower() for m in itens}
        ausentes = [c for c in chave_esperados
                    if not any(c.lower() in n or n in c.lower()
                               for n in nomes_presentes)]

        pontos = []
        for m in itens:
            n, _, _, _ = _classificar_nivel(
                m.get("valor"), m.get("critico_baixo"), m.get("limite_baixo"),
                m.get("otimo_min"), m.get("otimo_max"),
                m.get("limite_alto"), m.get("critico_alto"))
            s = _SCORE_NIVEL.get(n)
            if s is not None:
                pontos.append(s)

        score = round(sum(pontos) / len(pontos), 1) if pontos else None
        n_crit = sum(1 for m in itens if _classificar_nivel(
            m.get("valor"), m.get("critico_baixo"), m.get("limite_baixo"),
            m.get("otimo_min"), m.get("otimo_max"),
            m.get("limite_alto"), m.get("critico_alto"))[0]
            in ("critico_baixo","critico_alto"))
        n_fora = sum(1 for m in itens if _classificar_nivel(
            m.get("valor"), m.get("critico_baixo"), m.get("limite_baixo"),
            m.get("otimo_min"), m.get("otimo_max"),
            m.get("limite_alto"), m.get("critico_alto"))[0]
            in ("baixo","alto"))

        resultado[topico] = {
            "score": score, "itens": itens,
            "n_crit": n_crit, "n_fora": n_fora,
            "ausentes": ausentes,
        }
        if score is not None:
            scores_validos.append(score)

    nota_geral = round(sum(scores_validos) / len(scores_validos), 1) if scores_validos else 0.0
    return resultado, nota_geral


def _dt(s):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try: return datetime.strptime((s or "")[:10], fmt).date()
        except: pass
    return None


def _dias_atras(s):
    d = _dt(s)
    if not d: return ""
    dias = (date.today() - d).days
    if dias == 0: return "hoje"
    if dias == 1: return "ontem"
    if dias < 30: return f"{dias}d atrás"
    if dias < 365: return f"{dias//30}m atrás"
    return f"{dias//365}a atrás"


def _fmt_data(s):
    d = _dt(s)
    if not d: return s or "—"
    return d.strftime("%d/%m/%Y")


# ── Queries de dados ──────────────────────────────────────────────────────────

def _carregar_dados():
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15)
        conn.row_factory = sqlite3.Row

        # 1. Alertas ativos — exames fora da referencia nos ultimos 12 meses
        alertas = conn.execute("""
            SELECT COALESCE(ep.nome_oficial, er.parametro) as nome,
                   er.valor, er.unidade, er.nivel_interpretacao,
                   e.data_exame, e.laboratorio,
                   ep.sistema, g.nome as grupo_nome
            FROM exame_resultados er
            JOIN exames e ON e.id = er.exame_id
            LEFT JOIN exames_padrao ep ON ep.id = er.exame_padrao_id
            LEFT JOIN grupos_exame g ON g.id = er.grupo_id
            WHERE er.nivel_interpretacao IN ('critico_alto','critico_baixo','alto','baixo')
              AND e.data_exame >= date('now', '-12 months')
              AND (e.status IS NULL OR e.status NOT IN ('rascunho','revisao'))
            ORDER BY e.data_exame DESC
        """).fetchall()

        # 2. Ultimo exame por parametro + tendencia (comparar 2 ultimos)
        tendencias = conn.execute("""
            SELECT COALESCE(ep.nome_oficial, er.parametro) as nome,
                   er.valor, er.unidade, er.nivel_interpretacao,
                   e.data_exame, ep.sistema, g.nome as grupo
            FROM exame_resultados er
            JOIN exames e ON e.id = er.exame_id
            LEFT JOIN exames_padrao ep ON ep.id = er.exame_padrao_id
            LEFT JOIN grupos_exame g ON g.id = er.grupo_id
            WHERE er.valor IS NOT NULL AND er.valor != ''
              AND (e.status IS NULL OR e.status NOT IN ('rascunho','revisao'))
            ORDER BY e.data_exame DESC
        """).fetchall()

        # 3. Historico medico (alertas = 1)
        historico = conn.execute("""
            SELECT titulo, descricao, data_aprox, tipo, sequela, alerta
            FROM historico_medico
            ORDER BY data_aprox DESC
        """).fetchall()

        # 4. Remedios ativos
        remedios = conn.execute("""
            SELECT nome, dosagem FROM remedios WHERE ativo = 1 ORDER BY nome
        """).fetchall()

        # 5. Glicemia caseira — media e tendencia
        glicemia_cas = conn.execute("""
            SELECT valor, data_medicao FROM marcadores_leituras
            WHERE UPPER(parametro) = UPPER('Glicemia de Jejum')
            ORDER BY data_medicao DESC LIMIT 10
        """).fetchall()

        # 6. Consultas proximas
        consultas = conn.execute("""
            SELECT c.data, c.hora, c.tipo, m.nome as medico, e.nome as especialidade
            FROM consultas c
            LEFT JOIN medicos m ON m.id = c.medico_id
            LEFT JOIN especialidades e ON e.id = m.especialidade_id
            WHERE c.data >= date('now')
            ORDER BY c.data ASC LIMIT 3
        """).fetchall()

        # 7. Por sistema — ultimo resultado e nivel
        por_sistema = {}
        for r in tendencias:
            sis = r["sistema"] or "Outros"
            nome = r["nome"]
            if sis not in por_sistema:
                por_sistema[sis] = {}
            if nome not in por_sistema[sis]:
                por_sistema[sis][nome] = dict(r)

        # perfil do paciente — usado nas queries 8 e 9
        perfil_row = conn.execute(
            "SELECT sexo, data_nasc FROM perfil_usuario LIMIT 1").fetchone()
        sexo_pac = (perfil_row["sexo"] or "M").upper()[:1] if perfil_row else "M"
        try:
            from datetime import date as _d
            nasc = _d.fromisoformat(str(perfil_row["data_nasc"])[:10])
            idade_pac = (_d.today().year - nasc.year -
                         ((_d.today().month, _d.today().day) < (nasc.month, nasc.day)))
        except Exception:
            idade_pac = 50

        # 8. Todos os marcadores de sangue — para score por topico
        todos_marc_rows = conn.execute("""
            SELECT ep.nome_oficial,
                   er.valor, er.unidade, e.data_exame,
                   rp.critico_baixo, rp.limite_baixo, rp.otimo_min, rp.otimo_max,
                   rp.limite_alto, rp.critico_alto
            FROM exame_resultados er
            JOIN exames e ON e.id = er.exame_id
            JOIN exames_padrao ep ON ep.id = er.exame_padrao_id
            JOIN grupos_exame g ON g.id = ep.grupo_id
            LEFT JOIN referencias_padrao rp
                   ON rp.exame_padrao_id = ep.id
                  AND (rp.sexo = 'ambos' OR rp.sexo = ?)
                  AND (rp.critico_baixo IS NOT NULL
                       OR rp.limite_baixo IS NOT NULL
                       OR rp.limite_alto IS NOT NULL)
            WHERE g.tipo = 'sangue'
              AND er.valor IS NOT NULL AND er.valor != ''
              AND (e.status IS NULL OR e.status NOT IN ('rascunho','revisao'))
            ORDER BY ep.nome_oficial, e.data_exame DESC
        """, (sexo_pac,)).fetchall()

        # pegar o mais recente por nome, preferindo linha com mais campos de ref
        def _ref_score(rd):
            return sum(1 for k in ("critico_baixo","limite_baixo","otimo_min",
                                   "otimo_max","limite_alto","critico_alto")
                       if rd.get(k) is not None)

        _marc_visto = {}
        for r in todos_marc_rows:
            rd = {"nome_oficial": r[0], "valor": r[1], "unidade": r[2],
                  "data_exame": r[3], "critico_baixo": r[4], "limite_baixo": r[5],
                  "otimo_min": r[6], "otimo_max": r[7], "limite_alto": r[8],
                  "critico_alto": r[9]}
            nome = r[0]
            if nome not in _marc_visto:
                _marc_visto[nome] = rd
            else:
                existing = _marc_visto[nome]
                # preferir: mesmo exame mais recente com mais campos de ref
                if (rd["data_exame"] == existing["data_exame"] and
                        _ref_score(rd) > _ref_score(existing)):
                    _marc_visto[nome] = rd

        # 9. Vitaminas & Minerais — ultimo resultado + referencia por sexo
        vit_min_rows = conn.execute("""
            SELECT ep.nome_oficial, ep.id as ep_id,
                   er.valor, er.unidade, e.data_exame,
                   rp.critico_baixo, rp.limite_baixo, rp.otimo_min, rp.otimo_max,
                   rp.limite_alto, rp.critico_alto
            FROM exame_resultados er
            JOIN exames e ON e.id = er.exame_id
            JOIN exames_padrao ep ON ep.id = er.exame_padrao_id
            LEFT JOIN referencias_padrao rp
                   ON rp.exame_padrao_id = ep.id
                  AND (rp.sexo = 'ambos' OR rp.sexo = ?)
                  AND (rp.critico_baixo IS NOT NULL
                       OR rp.limite_baixo IS NOT NULL
                       OR rp.limite_alto IS NOT NULL)
            WHERE ep.grupo_id = 6
              AND er.valor IS NOT NULL AND er.valor != ''
              AND (e.status IS NULL OR e.status NOT IN ('rascunho','revisao'))
            ORDER BY ep.nome_oficial, e.data_exame DESC
        """, (sexo_pac,)).fetchall()

        def _ref_score_r(rd):
            return sum(1 for k in ("critico_baixo","limite_baixo","otimo_min",
                                   "otimo_max","limite_alto","critico_alto")
                       if rd.get(k) is not None)

        vit_min_visto = {}
        for r in vit_min_rows:
            nome = r["nome_oficial"]
            rd = dict(r)
            if nome not in vit_min_visto:
                vit_min_visto[nome] = rd
            else:
                if (rd["data_exame"] == vit_min_visto[nome]["data_exame"] and
                        _ref_score_r(rd) > _ref_score_r(vit_min_visto[nome])):
                    vit_min_visto[nome] = rd

        conn.close()
        return {
            "alertas": [dict(r) for r in alertas],
            "por_sistema": por_sistema,
            "historico": [dict(r) for r in historico],
            "remedios": [dict(r) for r in remedios],
            "glicemia_cas": [dict(r) for r in glicemia_cas],
            "consultas": [dict(r) for r in consultas],
            "vit_min": list(vit_min_visto.values()),
            "todos_marc": list(_marc_visto.values()),
        }
    except Exception as ex:
        log.error("[CHECKUP] erro: %s", ex)
        return {}


# ── Widgets de secao ──────────────────────────────────────────────────────────

def _secao_titulo(titulo, icone, cor):
    return ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Icon(icone, size=16, color=cor),
                bgcolor=ft.Colors.with_opacity(0.15, cor),
                border_radius=8, width=32, height=32,
                alignment=ft.alignment.Alignment(0, 0),
            ),
            ft.Text(titulo, size=15, color=TXT, weight=ft.FontWeight.W_700),
        ], spacing=10),
        padding=ft.padding.only(top=16, bottom=8),
    )


def _classificar_nivel(valor_str, cb, lb, omin, omax, la, ca):
    """
    Classifica valor dentro da escala de referencia.
    Retorna (nivel, cor, icone, label)
    cb=critico_baixo  lb=limite_baixo  omin=otimo_min  omax=otimo_max
    la=limite_alto    ca=critico_alto
    """
    try:
        v = float(str(valor_str).replace(",", "."))
    except Exception:
        return ("sem_dado", MUT, "remove_rounded", "Sem dado")

    # critico baixo
    if cb is not None and v < cb:
        return ("critico_baixo", VERM, "arrow_downward_rounded", "Crítico")
    # critico alto
    if ca is not None and v > ca:
        return ("critico_alto", VERM, "arrow_upward_rounded", "Crítico")
    # abaixo do limite baixo
    if lb is not None and v < lb:
        return ("baixo", LAR, "arrow_downward_rounded", "Baixo")
    # acima do limite alto
    if la is not None and v > la:
        return ("alto", LAR, "arrow_upward_rounded", "Alto")
    # dentro da faixa otima
    if omin is not None and omax is not None and omin <= v <= omax:
        return ("otimo", VERD, "check_circle_outline_rounded", "Ótimo")
    # entre limite_baixo e otimo_min (bom mas abaixo do otimo)
    if omin is not None and lb is not None and lb <= v < omin:
        return ("bom", "#5CB85C", "keyboard_arrow_up_rounded", "Bom")
    # entre otimo_max e limite_alto (bom mas acima do otimo)
    if omax is not None and la is not None and omax < v <= la:
        return ("bom", "#5CB85C", "keyboard_arrow_down_rounded", "Bom")
    # sem referencia suficiente — apenas limite_baixo e limite_alto
    if lb is not None and la is not None and lb <= v <= la:
        return ("normal", AZUL, "check_circle_outline_rounded", "Normal")
    return ("sem_ref", MUT, "remove_rounded", "—")


def _barra_referencia(valor_str, cb, lb, omin, omax, la, ca, largura=240):
    """Barra visual mostrando onde o valor cai na escala de referencia."""
    try:
        v = float(str(valor_str).replace(",", "."))
    except Exception:
        return ft.Container(height=0)

    # definir escala visual: min_escala a max_escala
    vals = [x for x in [cb, lb, omin, omax, la, ca] if x is not None]
    if len(vals) < 2:
        return ft.Container(height=0)
    min_e = min(vals) * 0.85
    max_e = max(vals) * 1.15
    rng = max_e - min_e or 1

    def _pct(x):
        if x is None: return None
        return max(0.0, min(1.0, (x - min_e) / rng))

    # zonas coloridas
    zonas = []
    limites = sorted([x for x in [min_e, cb, lb, omin, omax, la, ca, max_e]
                      if x is not None])
    cores_zona = []
    for i in range(len(limites) - 1):
        mid = (limites[i] + limites[i+1]) / 2
        if cb is not None and mid < cb:       cor_z = VERM
        elif la is not None and mid > la:      cor_z = VERM
        elif ca is not None and mid > ca:      cor_z = VERM
        elif lb is not None and mid < lb:      cor_z = LAR
        elif omin is not None and omax is not None and omin <= mid <= omax: cor_z = VERD
        else:                                  cor_z = "#5CB85C"
        w_pct = (limites[i+1] - limites[i]) / rng
        zonas.append(ft.Container(
            width=largura * w_pct, height=6,
            bgcolor=ft.Colors.with_opacity(0.35, cor_z),
        ))

    # marcador do valor atual
    pct_v = _pct(v)
    nivel, cor_v, _, _ = _classificar_nivel(valor_str, cb, lb, omin, omax, la, ca)

    return ft.Stack([
        ft.Row(zonas, spacing=0),
        ft.Container(
            width=3, height=10, bgcolor=cor_v,
            border_radius=2,
            left=max(0, int(largura * pct_v) - 1),
            top=-2,
        ),
    ], width=largura, height=10)


def _card_vit_min(r, page=None):
    """Card de uma vitamina ou mineral com barra de referencia + ingestao diaria."""
    from dados.model_prontuario import ingestao_diaria_nutriente
    nome  = r.get("nome_oficial") or "—"
    valor = r.get("valor") or "—"
    unid  = r.get("unidade") or ""
    data  = r.get("data_exame") or ""
    cb    = r.get("critico_baixo")
    lb    = r.get("limite_baixo")
    omin  = r.get("otimo_min")
    omax  = r.get("otimo_max")
    la    = r.get("limite_alto")
    ca    = r.get("critico_alto")

    nivel, cor, ico, label = _classificar_nivel(valor, cb, lb, omin, omax, la, ca)
    tem_ref = any(x is not None for x in [cb, lb, omin, omax, la, ca])

    if tem_ref:
        partes = []
        if lb is not None: partes.append(f">{lb}")
        if omin is not None and omax is not None: partes.append(f"ótimo {omin}–{omax}")
        if la is not None: partes.append(f"<{la}")
        ref_txt = "  ".join(partes)
    else:
        ref_txt = "Sem referência"

    barra = _barra_referencia(valor, cb, lb, omin, omax, la, ca) if tem_ref \
            else ft.Container(height=0)

    def _dias(s):
        from datetime import date as _dd, datetime as _ddtt
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                d = _ddtt.strptime((s or "")[:10], fmt).date()
                dias = (_dd.today() - d).days
                if dias == 0: return "hoje"
                if dias < 30: return f"{dias}d"
                if dias < 365: return f"{dias//30}m"
                return f"{dias//365}a"
            except: pass
        return ""

    # ingestao diaria via rotina
    ing = ingestao_diaria_nutriente(nome)
    if ing:
        pct = ing["pct_rda"]
        tem_supl = ing.get("tem_suplemento", False)
        nomes_supl = ing.get("nomes_suplemento", [])
        cor_ing = (VERD if ing["status"] == "adequada"
                   else LAR if ing["status"] == "insuficiente"
                   else AZUL)

        # interpretacao cruzada
        interps = []
        if nivel in ("baixo","critico_baixo"):
            if tem_supl:
                interps.append(("Suplemento detectado — exame pode não refletir dose atual",
                                AZUL))
            elif ing["status"] == "adequada":
                interps.append(("Ingestão adequada — investigar absorção", AMAR))
            else:
                interps.append(("Ingestão insuficiente — aumentar na dieta", VERM))
        elif nivel in ("alto","critico_alto") and ing["status"] == "excessiva":
            interps.append(("Excesso na dieta — reduzir ingestão", LAR))

        supl_widget = ft.Container(height=0)
        if tem_supl:
            nome_supl_txt = ", ".join(nomes_supl[:2])
            supl_widget = ft.Row([
                ft.Icon("medication_rounded", size=10, color=ROXO),
                ft.Text(f"Suplemento: {nome_supl_txt}", size=9, color=ROXO),
                ft.Text("(dose não incluída na %)", size=9, color=MUT),
            ], spacing=4)

        ing_widget = ft.Container(
            content=ft.Column([
                ft.Divider(height=1, color=BD2),
                ft.Row([
                    ft.Icon("restaurant_rounded", size=11, color=cor_ing),
                    ft.Text("Dieta:", size=10, color=MUT),
                    ft.Text(f"{ing['ingestao']}{ing['unidade']}/dia",
                            size=11, color=cor_ing, weight=ft.FontWeight.W_600),
                    ft.Container(expand=True),
                    ft.Text(f"{pct:.0f}% RDA", size=10, color=cor_ing),
                ], spacing=4),
                ft.ProgressBar(
                    value=min(pct/100, 1.5),
                    color=cor_ing,
                    bgcolor=ft.Colors.with_opacity(0.15, cor_ing),
                    height=4),
                supl_widget,
                *[ft.Text(txt, size=9, color=cor, weight=ft.FontWeight.W_600)
                  for txt, cor in interps],
            ], spacing=3, tight=True),
            padding=ft.padding.only(top=4),
        )
    else:
        ing_widget = ft.Container(height=0)

    card = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Column([
                    ft.Text(nome, size=12, color=TXT, weight=ft.FontWeight.W_600,
                            no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(ref_txt, size=9, color=MUT),
                ], spacing=1, expand=True),
                ft.Column([
                    ft.Row([
                        ft.Icon(ico, size=12, color=cor),
                        ft.Text(f"{valor} {unid}".strip(), size=13, color=cor,
                                weight=ft.FontWeight.W_700),
                    ], spacing=3, tight=True),
                    ft.Row([
                        ft.Text(label, size=9, color=cor, weight=ft.FontWeight.W_600),
                        ft.Text(f"  {_dias(data)}", size=9, color=MUT),
                    ], spacing=0, tight=True),
                ], spacing=1, horizontal_alignment=ft.CrossAxisAlignment.END),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Container(height=4),
            barra,
            ing_widget,
        ], spacing=0, tight=True),
        bgcolor=COR_CARD, border_radius=10,
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border=ft.border.all(1, ft.Colors.with_opacity(0.4, cor) if nivel not in ("sem_ref","sem_dado","normal","otimo","bom") else BD2),
        ink=bool(page),
    )

    if page:
        def _abrir_detalhe(e, _nome=nome, _cor=cor,
                           _cb=cb, _lb=lb, _omin=omin, _omax=omax, _la=la, _ca=ca):
            from telas.tela_sangue import _montar_exame_selecionado
            from shared.grafico import renderizar_grafico_combinado
            from shared.layout import Layout as _LayD
            from dados.model_prontuario import DB_PATH as _DBP
            import sqlite3 as _sq

            exame = _montar_exame_selecionado(_nome)
            if not exame:
                return

            ref_ov_d = [None]
            def _fechar_d(e=None):
                if ref_ov_d[0] in page.overlay:
                    page.overlay.remove(ref_ov_d[0])
                try: page.update()
                except Exception: pass

            # historico em lista — todos os valores ordenados do mais recente
            hist = list(reversed(exame.get("historico", [])))
            _NIVEL_COR = {
                "critico_baixo": VERM, "critico_alto": VERM,
                "baixo": LAR, "alto": LAR,
                "otimo": VERD, "bom": "#5CB85C",
                "normal": AZUL,
            }
            _NIVEL_ICO = {
                "critico_baixo": "arrow_downward_rounded",
                "critico_alto":  "arrow_upward_rounded",
                "baixo": "arrow_downward_rounded",
                "alto":  "arrow_upward_rounded",
                "otimo": "check_circle_outline_rounded",
                "bom":   "check_circle_outline_rounded",
                "normal":"check_circle_outline_rounded",
            }

            col_hist = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
            for h in hist:
                h_val  = h.get("valor","—")
                h_unid = h.get("unidade","")
                h_data = h.get("data","")
                h_niv  = h.get("nivel") or ""
                h_cor  = _NIVEL_COR.get(h_niv, MUT)
                h_ico  = _NIVEL_ICO.get(h_niv, "remove_rounded")
                try:
                    from datetime import datetime as _dtt
                    d = _dtt.strptime(h_data[:10], "%Y-%m-%d")
                    h_data_fmt = d.strftime("%d/%m/%Y")
                except Exception:
                    h_data_fmt = h_data

                col_hist.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Icon(h_ico, size=12, color=h_cor),
                        ft.Text(f"{h_val} {h_unid}".strip(), size=13,
                                color=h_cor, weight=ft.FontWeight.W_700,
                                expand=True),
                        ft.Text(h_data_fmt, size=11, color=MUT),
                    ], spacing=8),
                    bgcolor=COR_CARD, border_radius=8,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.3, h_cor)
                                        if h_niv in ("critico_baixo","critico_alto","baixo","alto")
                                        else BD2),
                ))

            # grafico + lista na mesma tela
            grafico_widget = ft.Container(height=0)
            if exame.get("historico"):
                try:
                    grafico_widget = renderizar_grafico_combinado(page, [exame])
                except Exception:
                    grafico_widget = ft.Container(height=0)

            _layd = _LayD(page)
            _cab_d = _layd.criar_cabecalho(
                _nome, _fechar_d,
                icone_titulo="analytics_rounded", cor_titulo=_cor)

            ref_ov_d[0] = ft.Container(
                content=ft.Column([
                    ft.Container(height=_layd.spacer_topo, bgcolor=BG),
                    _cab_d,
                    ft.Container(
                        content=ft.Column([
                            grafico_widget,
                            ft.Divider(height=1, color=BD2),
                            col_hist,
                        ], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True),
                        expand=True,
                        padding=ft.padding.symmetric(horizontal=16, vertical=8)),
                ], spacing=0, expand=True),
                bgcolor=BG, expand=True)
            page.overlay.append(ref_ov_d[0])
            try: page.update()
            except Exception: pass

        card.on_click = _abrir_detalhe

    return card


def _chip_nivel(nivel, valor, unidade):
    cor = _COR_NIVEL.get(nivel, AZUL)
    ico = _ICO_NIVEL.get(nivel, "remove_rounded")
    return ft.Container(
        content=ft.Row([
            ft.Icon(ico, size=11, color=cor),
            ft.Text(f"{valor} {unidade}".strip(), size=11, color=cor,
                    weight=ft.FontWeight.W_600),
        ], spacing=3, tight=True),
        bgcolor=ft.Colors.with_opacity(0.12, cor),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
    )


def _card_alerta(r):
    nivel = r.get("nivel_interpretacao", "")
    cor   = _COR_NIVEL.get(nivel, LAR)
    return ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Icon(
                    "warning_rounded" if "critico" in nivel else "info_outline_rounded",
                    size=18, color=cor,
                ),
                bgcolor=ft.Colors.with_opacity(0.12, cor),
                border_radius=8, width=36, height=36,
                alignment=ft.alignment.Alignment(0, 0),
            ),
            ft.Column([
                ft.Text(r.get("nome", ""), size=13, color=TXT,
                        weight=ft.FontWeight.W_600,
                        no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Row([
                    ft.Text(f"{r.get('valor','')} {r.get('unidade','')}".strip(),
                            size=12, color=cor, weight=ft.FontWeight.W_700),
                    ft.Text("·", size=10, color=MUT),
                    ft.Text(r.get("grupo_nome") or r.get("sistema") or "",
                            size=10, color=SEC),
                ], spacing=4),
                ft.Text(_dias_atras(r.get("data_exame")), size=10, color=MUT),
            ], spacing=2, expand=True),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=ft.Colors.with_opacity(0.06, cor),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border=ft.Border(
            left=ft.BorderSide(3, cor),
            top=ft.BorderSide(1, ft.Colors.with_opacity(0.2, cor)),
            bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.2, cor)),
            right=ft.BorderSide(1, ft.Colors.with_opacity(0.2, cor)),
        ),
    )


def _card_sistema(sistema, params: dict, page=None):
    """Card de um sistema corporal com seus parametros e niveis."""
    _ICONES_SIS = {
        "Cardiaco":        ("favorite_rounded",     "#FF6B6B"),
        "Visceral":        ("bubble_chart_rounded",  AZUL),
        "Sangue":          ("bloodtype_rounded",     "#FF9500"),
        "Ortopedia":       ("accessibility_rounded", VERD),
        "Psiquiatria":     ("psychology_rounded",    ROXO),
        "Visao & Audicao": ("visibility_rounded",    "#00BCD4"),
    }
    icone, cor = _ICONES_SIS.get(sistema, ("category_rounded", SEC))

    n_alert = sum(1 for p in params.values()
                  if p.get("nivel_interpretacao") in ("critico_alto","critico_baixo","alto","baixo"))
    n_ok    = sum(1 for p in params.values()
                  if p.get("nivel_interpretacao") in ("otimo","bom"))

    if n_alert > 0:
        status_cor = VERM if any(p.get("nivel_interpretacao") in ("critico_alto","critico_baixo")
                                  for p in params.values()) else LAR
        status_txt = f"{n_alert} alerta(s)"
        status_ico = "warning_rounded"
    elif n_ok > 0:
        status_cor = VERD; status_txt = "OK"; status_ico = "check_circle_outline_rounded"
    else:
        status_cor = MUT; status_txt = "sem nível"; status_ico = "remove_rounded"

    params_list = sorted(params.values(),
                         key=lambda p: p.get("data_exame") or "", reverse=True)[:4]
    itens = []
    for p in params_list:
        cor_n = _COR_NIVEL.get(p.get("nivel_interpretacao") or "", SEC)
        itens.append(ft.Row([
            ft.Text((p.get("nome") or "")[:22], size=10, color=SEC, expand=True,
                    no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text(f"{p.get('valor','')} {(p.get('unidade') or '')[:6]}".strip(),
                    size=10, color=cor_n, weight=ft.FontWeight.W_600),
        ], spacing=4))

    card = ft.Container(
        content=ft.Column([
            # cabeçalho — icone + nome + badge numa row compacta
            ft.Row([
                ft.Container(
                    content=ft.Icon(icone, size=14, color=cor),
                    bgcolor=ft.Colors.with_opacity(0.12, cor),
                    border_radius=6, width=28, height=28,
                    alignment=ft.alignment.Alignment(0, 0),
                ),
                ft.Text(sistema, size=12, color=TXT,
                        weight=ft.FontWeight.W_700, expand=True,
                        no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Container(
                    content=ft.Row([
                        ft.Icon(status_ico, size=10, color=status_cor),
                        ft.Text(status_txt, size=9, color=status_cor,
                                weight=ft.FontWeight.W_600),
                    ], spacing=2, tight=True),
                    bgcolor=ft.Colors.with_opacity(0.12, status_cor),
                    border_radius=6,
                    padding=ft.padding.symmetric(horizontal=6, vertical=3),
                ),
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Text(f"{len(params)} parâmetro(s)", size=9, color=MUT),
            ft.Divider(color=BD, height=1),
            *itens,
        ], spacing=4, tight=True),
        bgcolor=COR_CARD, border_radius=12,
        padding=ft.padding.all(12),
        border=ft.border.all(1, BD2),
        expand=True, ink=bool(page),
    )

    if page:
        def _abrir_sistema(e, _sis=sistema, _params=params, _cor=cor, _ico=icone):
            from shared.layout import Layout as _LayS
            ref_ov_s = [None]
            def _fechar_s(ev=None):
                if ref_ov_s[0] in page.overlay:
                    page.overlay.remove(ref_ov_s[0])
                try: page.update()
                except Exception: pass

            col_s = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
            _ORD = {"critico_baixo":0,"critico_alto":1,"baixo":2,"alto":3,
                    "normal":4,"bom":5,"otimo":6,"sem_ref":7}
            itens_ord = sorted(_params.values(),
                               key=lambda p: (_ORD.get(p.get("nivel_interpretacao") or "", 8),
                                              p.get("nome") or ""))
            for p in itens_ord:
                nivel = p.get("nivel_interpretacao") or ""
                cor_n = _COR_NIVEL.get(nivel, MUT)
                ico_n = _ICO_NIVEL.get(nivel, "remove_rounded")
                nome_p = p.get("nome") or "—"
                try:
                    from datetime import datetime as _dtt
                    d = _dtt.strptime((p.get("data_exame") or "")[:10], "%Y-%m-%d")
                    data_fmt = d.strftime("%d/%m/%Y")
                except Exception:
                    data_fmt = p.get("data_exame") or "—"

                item_card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ico_n, size=12, color=cor_n),
                            ft.Text(nome_p, size=12, color=TXT,
                                    expand=True, weight=ft.FontWeight.W_600,
                                    no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(f"{p.get('valor','')} {p.get('unidade','')[:8]}".strip(),
                                    size=13, color=cor_n, weight=ft.FontWeight.W_700),
                            ft.Icon("chevron_right_rounded", size=12, color=MUT),
                        ], spacing=6),
                        ft.Row([
                            ft.Text(nivel.replace("_"," ").title() if nivel else "Sem nível",
                                    size=9, color=cor_n),
                            ft.Container(expand=True),
                            ft.Text(data_fmt, size=9, color=MUT),
                        ], spacing=4),
                    ], spacing=3, tight=True),
                    bgcolor=COR_CARD, border_radius=8, ink=True,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.35, cor_n)
                                        if nivel in ("critico_baixo","critico_alto","baixo","alto")
                                        else BD2),
                )

                def _abrir_graf_sis(e, _n=nome_p, _c=cor_n):
                    from telas.tela_sangue import _montar_exame_selecionado
                    from shared.grafico import renderizar_grafico_combinado
                    from shared.layout import Layout as _LayG2
                    exame = _montar_exame_selecionado(_n)
                    if not exame or not exame.get("historico"):
                        return
                    ref_ov_g2 = [None]
                    def _fechar_g2(ev=None):
                        if ref_ov_g2[0] in page.overlay:
                            page.overlay.remove(ref_ov_g2[0])
                        try: page.update()
                        except Exception: pass

                    # historico em lista
                    hist = list(reversed(exame.get("historico", [])))
                    col_h = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
                    grafico_w = ft.Container(height=0)
                    try:
                        grafico_w = renderizar_grafico_combinado(page, [exame])
                    except Exception:
                        pass
                    for h in hist:
                        h_val = h.get("valor","—"); h_unid = h.get("unidade","")
                        h_niv = h.get("nivel") or ""
                        h_cor = _COR_NIVEL.get(h_niv, MUT)
                        h_ico = _ICO_NIVEL.get(h_niv, "remove_rounded")
                        try:
                            hd = _dtt.strptime(h.get("data","")[:10], "%Y-%m-%d")
                            h_data = hd.strftime("%d/%m/%Y")
                        except Exception:
                            h_data = h.get("data","")
                        col_h.controls.append(ft.Container(
                            content=ft.Row([
                                ft.Icon(h_ico, size=12, color=h_cor),
                                ft.Text(f"{h_val} {h_unid}".strip(), size=13,
                                        color=h_cor, weight=ft.FontWeight.W_700, expand=True),
                                ft.Text(h_data, size=11, color=MUT),
                            ], spacing=8),
                            bgcolor=COR_CARD, border_radius=8,
                            padding=ft.padding.symmetric(horizontal=12, vertical=8),
                            border=ft.border.all(1, ft.Colors.with_opacity(0.3, h_cor)
                                                if h_niv in ("critico_baixo","critico_alto","baixo","alto")
                                                else BD2),
                        ))
                    _layg2 = _LayG2(page)
                    _cab_g2 = _layg2.criar_cabecalho(
                        _n, _fechar_g2,
                        icone_titulo="show_chart_rounded", cor_titulo=_c)
                    ref_ov_g2[0] = ft.Container(
                        content=ft.Column([
                            ft.Container(height=_layg2.spacer_topo, bgcolor=BG),
                            _cab_g2,
                            ft.Container(
                                content=ft.Column([
                                    grafico_w,
                                    ft.Divider(height=1, color=BD2),
                                    col_h,
                                ], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True),
                                expand=True,
                                padding=ft.padding.symmetric(horizontal=16, vertical=8)),
                        ], spacing=0, expand=True),
                        bgcolor=BG, expand=True)
                    page.overlay.append(ref_ov_g2[0])
                    try: page.update()
                    except Exception: pass

                item_card.on_click = _abrir_graf_sis
                col_s.controls.append(item_card)

            _lays = _LayS(page)
            _cab_s = _lays.criar_cabecalho(
                _sis, _fechar_s, icone_titulo=_ico, cor_titulo=_cor)
            ref_ov_s[0] = ft.Container(
                content=ft.Column([
                    ft.Container(height=_lays.spacer_topo, bgcolor=BG),
                    _cab_s,
                    ft.Container(content=col_s, expand=True,
                                 padding=ft.padding.symmetric(horizontal=16, vertical=8)),
                ], spacing=0, expand=True),
                bgcolor=BG, expand=True)
            page.overlay.append(ref_ov_s[0])
            try: page.update()
            except Exception: pass

        card.on_click = _abrir_sistema

    return card


def _mini_grafico_glicemia(leituras):
    """Sparkline horizontal das ultimas 7 glicemias caseiras."""
    if not leituras:
        return ft.Container(height=0)

    vals = []
    for r in reversed(leituras[:7]):
        try: vals.append(float(str(r.get("valor","")).replace(",",".")))
        except: pass

    if not vals:
        return ft.Container(height=0)

    v_min = min(vals); v_max = max(vals)
    rng   = max(v_max - v_min, 1)
    h     = 32

    # barras proprorcionais
    barras = []
    for v in vals:
        pct  = (v - v_min) / rng
        alt  = max(int(pct * h), 4)
        cor  = VERD if v <= 99 else (AMAR if v <= 125 else VERM)
        barras.append(ft.Container(
            width=14, height=alt, bgcolor=cor, border_radius=3,
        ))

    return ft.Container(
        content=ft.Column([
            ft.Text("Glicemia caseira — últimas medições", size=10, color=MUT),
            ft.Container(height=4),
            ft.Row(
                barras,
                spacing=4,
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.END,
            ),
            ft.Row([
                ft.Text(f"Min {v_min:.0f}", size=9, color=VERD),
                ft.Container(expand=True),
                ft.Text(f"Máx {v_max:.0f}", size=9,
                        color=VERD if v_max <= 99 else (AMAR if v_max <= 125 else VERM)),
            ]),
        ], spacing=0),
        bgcolor=COR_CARD, border_radius=10,
        padding=ft.padding.all(12),
        border=ft.border.all(1, BD2),
    )


# ── TELA PRINCIPAL ────────────────────────────────────────────────────────────

def criar_tela_checkup(page: ft.Page, voltar_fn=None):
    lay      = Layout(page)
    area     = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
    _montado = [False]

    def _rebuild():
        area.controls.clear()

        dados = _carregar_dados()
        alertas    = dados.get("alertas", [])
        por_sistema= dados.get("por_sistema", {})
        historico  = dados.get("historico", [])
        remedios   = dados.get("remedios", [])
        glicemia   = dados.get("glicemia_cas", [])
        consultas  = dados.get("consultas", [])
        vit_min    = dados.get("vit_min", [])
        todos_marc = dados.get("todos_marc", [])

        # ── SCORE GERAL ──────────────────────────────────────────────────────
        n_critico = sum(1 for a in alertas if "critico" in (a.get("nivel_interpretacao") or ""))
        n_alerta  = sum(1 for a in alertas if a.get("nivel_interpretacao") in ("alto","baixo"))
        n_total   = sum(len(v) for v in por_sistema.values())

        if n_critico > 0:
            score_cor = VERM; score_ico = "dangerous_rounded"
            score_txt = "Atenção Crítica"
            score_sub = f"{n_critico} parâmetro(s) crítico(s)"
        elif n_alerta > 0:
            score_cor = AMAR; score_ico = "warning_amber_rounded"
            score_txt = "Atenção"
            score_sub = f"{n_alerta} parâmetro(s) fora do ideal"
        else:
            score_cor = VERD; score_ico = "verified_rounded"
            score_txt = "Estável"
            score_sub = "Parâmetros recentes dentro do esperado"

        area.controls.append(ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(score_ico, size=36, color=score_cor),
                    bgcolor=ft.Colors.with_opacity(0.12, score_cor),
                    border_radius=16, width=64, height=64,
                    alignment=ft.alignment.Alignment(0, 0),
                ),
                ft.Column([
                    ft.Text("Status Geral de Saúde", size=11, color=MUT),
                    ft.Text(score_txt, size=22, color=score_cor,
                            weight=ft.FontWeight.W_800),
                    ft.Text(score_sub, size=12, color=SEC),
                    ft.Text(f"{n_total} parâmetros monitorados",
                            size=10, color=MUT),
                ], spacing=2, expand=True),
            ], spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=ft.Colors.with_opacity(0.06, score_cor),
            border_radius=14,
            padding=ft.padding.all(16),
            border=ft.border.all(1, ft.Colors.with_opacity(0.25, score_cor)),
        ))

        # ── MARCADORES — score por topico ────────────────────────────────────
        if todos_marc:
            scores_topicos, nota_geral = _calcular_scores(todos_marc)

            def _cor_score(s):
                if s >= 8: return VERD
                if s >= 6: return AMAR
                if s >= 4: return LAR
                return VERM

            def _abrir_analitico_topico(topico, dados_topico, so_criticos=False):
                """Overlay nivel 1: lista de topicos com score e barra."""
                ref_ov_t = [None]
                def _fechar_t(e=None):
                    if ref_ov_t[0] in page.overlay:
                        page.overlay.remove(ref_ov_t[0])
                    try: page.update()
                    except Exception: pass

                def _abrir_exames_topico(topico_nome, itens_topico, ausentes_topico=None, so_crit=False):
                    """Overlay nivel 2: exames do topico."""
                    ref_ov_e = [None]
                    def _fechar_e(e=None):
                        if ref_ov_e[0] in page.overlay:
                            page.overlay.remove(ref_ov_e[0])
                        try: page.update()
                        except Exception: pass

                    col_ex = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

                    # card de ausentes — solicitar exames
                    if ausentes_topico:
                        col_ex.controls.append(ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon("assignment_late_rounded", size=14, color=AMAR),
                                    ft.Text("Solicitar na próxima consulta",
                                            size=12, color=AMAR,
                                            weight=ft.FontWeight.W_700),
                                ], spacing=6),
                                ft.Container(height=4),
                                *[ft.Row([
                                    ft.Icon("fiber_manual_record_rounded",
                                            size=8, color=AMAR),
                                    ft.Text(a, size=11, color=TXT),
                                ], spacing=8) for a in ausentes_topico],
                            ], spacing=4, tight=True),
                            bgcolor=ft.Colors.with_opacity(0.08, AMAR),
                            border_radius=10,
                            padding=ft.padding.symmetric(horizontal=12, vertical=10),
                            border=ft.border.all(1, ft.Colors.with_opacity(0.3, AMAR)),
                        ))

                    _ORD = {"critico_baixo":0,"critico_alto":1,"baixo":2,"alto":3,
                            "normal":4,"bom":5,"otimo":6,"sem_ref":7,"sem_dado":8}

                    if not itens_topico:
                        col_ex.controls.append(ft.Container(
                            content=ft.Text("Nenhum resultado importado ainda.",
                                            size=12, color=MUT),
                            padding=ft.padding.symmetric(vertical=16),
                        ))
                    else:
                        itens_ord = sorted(itens_topico, key=lambda m: (
                            _ORD.get(_classificar_nivel(
                                m.get("valor"), m.get("critico_baixo"), m.get("limite_baixo"),
                                m.get("otimo_min"), m.get("otimo_max"),
                                m.get("limite_alto"), m.get("critico_alto"))[0], 9),
                            m.get("nome_oficial","")
                        ))
                        # se so_crit, mostrar apenas criticos
                        if so_crit:
                            itens_ord = [m for m in itens_ord if _classificar_nivel(
                                m.get("valor"), m.get("critico_baixo"), m.get("limite_baixo"),
                                m.get("otimo_min"), m.get("otimo_max"),
                                m.get("limite_alto"), m.get("critico_alto"))[0]
                                in ("critico_baixo","critico_alto")]
                        for m in itens_ord:
                            col_ex.controls.append(_card_vit_min(m, page))
                        if not itens_ord:
                            col_ex.controls.append(ft.Container(
                                content=ft.Text("Nenhum marcador crítico neste tópico.",
                                                size=12, color=MUT),
                                padding=ft.padding.symmetric(vertical=16),
                            ))

                    from shared.layout import Layout as _Lay5
                    _lay5 = _Lay5(page)
                    ico_t, cor_t, _, _ = _TOPICOS.get(
                        topico_nome, ("analytics_rounded", AZUL, [], []))
                    titulo_e = f"{topico_nome} — Críticos" if so_crit else topico_nome
                    _cab_e = _lay5.criar_cabecalho(
                        titulo_e, _fechar_e,
                        icone_titulo="warning_rounded" if so_crit else ico_t,
                        cor_titulo=VERM if so_crit else cor_t)
                    ref_ov_e[0] = ft.Container(
                        content=ft.Column([
                            ft.Container(height=_lay5.spacer_topo, bgcolor=BG),
                            _cab_e,
                            ft.Container(content=col_ex, expand=True,
                                         padding=ft.padding.symmetric(horizontal=16, vertical=8)),
                        ], spacing=0, expand=True),
                        bgcolor=BG, expand=True)
                    page.overlay.append(ref_ov_e[0])
                    try: page.update()
                    except Exception: pass

                # conteudo: lista de topicos com score + barra + click
                titulo_ov = "Críticos" if so_criticos else "Marcadores por Tópico"
                col_top = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
                _itens_ord = sorted(scores_topicos.items(), key=lambda x: (x[1]["score"] or 0))
                if so_criticos:
                    _itens_ord = [(t,d) for t,d in _itens_ord if d["n_crit"] > 0]
                for t_nome, t_dados in _itens_ord:
                    ico_t, cor_t, _, _ = _TOPICOS.get(
                        t_nome, ("analytics_rounded", AZUL, [], []))
                    s = t_dados["score"]
                    ausentes = t_dados.get("ausentes", [])
                    n_c = t_dados["n_crit"]; n_f = t_dados["n_fora"]

                    if s is None:
                        cor_s = MUT
                        score_txt = ft.Text("—", size=18, color=MUT,
                                            weight=ft.FontWeight.W_900)
                        barra = ft.Container(height=6, bgcolor=BD2,
                                            border_radius=3, expand=True)
                        status = "Sem dados"
                        status_cor = MUT
                    else:
                        cor_s = _cor_score(s)
                        score_txt = ft.Row([
                            ft.Text(f"{s:.1f}", size=18, color=cor_s,
                                    weight=ft.FontWeight.W_900),
                            ft.Text("/10", size=10, color=MUT),
                        ], spacing=2, tight=True,
                           vertical_alignment=ft.CrossAxisAlignment.END)
                        barra = ft.Row([
                            ft.Container(expand=int(s*10), height=6,
                                         bgcolor=cor_s, border_radius=3),
                            ft.Container(expand=int((10-s)*10), height=6,
                                         bgcolor=ft.Colors.with_opacity(0.15, cor_s),
                                         border_radius=3),
                        ], spacing=2)
                        status = (f"{n_c} crítico(s)" if n_c
                                  else f"{n_f} fora do ideal" if n_f
                                  else "Normal")
                        status_cor = (VERM if n_c else LAR if n_f else VERD)

                    col_info = [
                        ft.Text(f"{len(t_dados['itens'])} marcadores  •  {status}",
                                size=10, color=status_cor),
                    ]
                    if ausentes:
                        col_info.append(ft.Row([
                            ft.Icon("warning_amber_rounded", size=10, color=AMAR),
                            ft.Text(f"Solicitar: {', '.join(ausentes[:3])}"
                                    + (f" +{len(ausentes)-3}" if len(ausentes)>3 else ""),
                                    size=9, color=AMAR),
                        ], spacing=4))

                    card_t = ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Container(
                                    content=ft.Icon(ico_t, size=13, color=cor_t),
                                    bgcolor=ft.Colors.with_opacity(0.13, cor_t),
                                    border_radius=6, width=26, height=26,
                                    alignment=ft.alignment.Alignment(0,0)),
                                ft.Text(t_nome, size=13, color=TXT,
                                        weight=ft.FontWeight.W_600, expand=True),
                                score_txt,
                                ft.Icon("chevron_right_rounded", size=14, color=MUT),
                            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            ft.Container(height=4),
                            barra,
                            *col_info,
                        ], spacing=4, tight=True),
                        bgcolor=COR_CARD, border_radius=10, ink=True,
                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                        border=ft.border.all(1,
                            ft.Colors.with_opacity(0.4, VERM) if n_c
                            else ft.Colors.with_opacity(0.3, LAR) if n_f
                            else ft.Colors.with_opacity(0.3, AMAR) if ausentes
                            else BD2),
                    )
                    card_t.on_click = lambda e, tn=t_nome, td=t_dados["itens"], \
                        au=ausentes, sc=so_criticos: _abrir_exames_topico(tn, td, au, sc)
                    col_top.controls.append(card_t)

                from shared.layout import Layout as _Lay6
                _lay6 = _Lay6(page)
                _cab_t = _lay6.criar_cabecalho(
                    titulo_ov, _fechar_t,
                    icone_titulo="bar_chart_rounded" if not so_criticos else "warning_rounded",
                    cor_titulo=AZUL if not so_criticos else VERM)
                ref_ov_t[0] = ft.Container(
                    content=ft.Column([
                        ft.Container(height=_lay6.spacer_topo, bgcolor=BG),
                        _cab_t,
                        ft.Container(content=col_top, expand=True,
                                     padding=ft.padding.symmetric(horizontal=16, vertical=8)),
                    ], spacing=0, expand=True),
                    bgcolor=BG, expand=True)
                page.overlay.append(ref_ov_t[0])
                try: page.update()
                except Exception: pass

            # card principal MARCADORES com nota geral
            cor_geral = _cor_score(nota_geral)
            n_crit_total = sum(d["n_crit"] for d in scores_topicos.values())
            n_fora_total = sum(d["n_fora"] for d in scores_topicos.values())
            status_geral = (f"{n_crit_total} crítico(s)" if n_crit_total
                            else f"{n_fora_total} fora do ideal" if n_fora_total
                            else "Todos normais")

            # mini barras dos topicos
            mini_barras = ft.Row(spacing=3, wrap=False)
            for t_nome in _TOPICOS:
                if t_nome not in scores_topicos: continue
                s = scores_topicos[t_nome]["score"] or 0
                mini_barras.controls.append(ft.Column([
                    ft.Container(
                        width=28, height=max(4, int(s * 3.2)),
                        bgcolor=_cor_score(s), border_radius=2),
                    ft.Text(t_nome[:3], size=7, color=MUT),
                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER))

            # botao criticos — so abre se tiver criticos
            btn_criticos = ft.Container(
                content=ft.Row([
                    ft.Icon("warning_rounded", size=11, color=VERM),
                    ft.Text(status_geral, size=11, color=cor_geral,
                            weight=ft.FontWeight.W_600),
                ], spacing=4, tight=True),
                bgcolor=ft.Colors.with_opacity(0.12, cor_geral),
                border_radius=8, ink=bool(n_crit_total),
                padding=ft.padding.symmetric(horizontal=10, vertical=5),
            )
            if n_crit_total:
                btn_criticos.on_click = lambda e: _abrir_analitico_topico(None, None, so_criticos=True)

            # botao ver analise
            btn_ver = ft.Container(
                content=ft.Row([
                    ft.Text("Ver análise", size=11, color=AZUL),
                    ft.Icon("chevron_right_rounded", size=13, color=AZUL),
                ], spacing=2, tight=True),
                border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=6, vertical=5),
            )
            btn_ver.on_click = lambda e: _abrir_analitico_topico(None, None)

            card_marc = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Column([
                            ft.Text("MARCADORES", size=10, color=MUT,
                                    weight=ft.FontWeight.W_700),
                            ft.Row([
                                ft.Text(f"{nota_geral:.1f}", size=32,
                                        color=cor_geral, weight=ft.FontWeight.W_900),
                                ft.Text("/10", size=13, color=MUT),
                            ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.END),
                            btn_criticos,
                        ], spacing=4, expand=True),
                        ft.Column([
                            mini_barras,
                        ], horizontal_alignment=ft.CrossAxisAlignment.END),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(height=4),
                    ft.Row([
                        ft.Text(f"{len(scores_topicos)} tópicos  •  "
                                f"{len(todos_marc)} marcadores",
                                size=10, color=MUT, expand=True),
                        btn_ver,
                    ]),
                ], spacing=4, tight=True),
                bgcolor=ft.Colors.with_opacity(0.06, cor_geral),
                border_radius=14,
                padding=ft.padding.all(16),
                border=ft.border.all(1, ft.Colors.with_opacity(0.3, cor_geral)),
            )
            area.controls.append(card_marc)

        # ── ALERTAS ──────────────────────────────────────────────────────────
        if alertas:
            area.controls.append(_secao_titulo(
                f"Alertas Ativos ({len(alertas)})", "notifications_active_rounded", VERM))
            for a in alertas[:8]:
                area.controls.append(_card_alerta(a))
            if len(alertas) > 8:
                area.controls.append(ft.Text(
                    f"+ {len(alertas)-8} alertas adicionais",
                    size=11, color=MUT, text_align=ft.TextAlign.CENTER))

        # consultas removidas do checkup

        # ── VITAMINAS & MINERAIS ─────────────────────────────────────────────
        if vit_min:
            _MINERAIS_NOMES = {
                "calcio","ferro","magnesio","fosforo","potassio","zinco",
                "sodio","selenio","cobre","manganes","cloro","transferrina",
                "ferritina","saturacao","reserva",
            }
            def _eh_mineral(nome):
                return any(m in (nome or "").lower() for m in _MINERAIS_NOMES)

            _ORDEM_NIV = {"critico_baixo":0,"critico_alto":1,"baixo":2,"alto":3,
                          "normal":4,"bom":5,"otimo":6,"sem_ref":7,"sem_dado":8}
            def _sort_key(r):
                n, _, _, _ = _classificar_nivel(
                    r.get("valor"), r.get("critico_baixo"), r.get("limite_baixo"),
                    r.get("otimo_min"), r.get("otimo_max"),
                    r.get("limite_alto"), r.get("critico_alto"))
                return (_ORDEM_NIV.get(n, 9), r.get("nome_oficial",""))

            vitaminas = sorted([r for r in vit_min if not _eh_mineral(r.get("nome_oficial",""))], key=_sort_key)
            minerais  = sorted([r for r in vit_min if _eh_mineral(r.get("nome_oficial",""))],     key=_sort_key)

            # filtro: "ruins" = critico+baixo+alto | "todos" = tudo
            _RUINS = {"critico_baixo","critico_alto","baixo","alto"}
            filtro_vit = ["ruins"]  # "ruins" ou "todos"
            filtro_min = ["ruins"]

            def _grafico_barras(itens, filtro_ref, titulo, icone, cor_titulo, col_container):
                """Monta grafico de barras horizontal dentro de col_container."""
                col_container.controls.clear()
                mostrar_todos = filtro_ref[0] == "todos"
                lista = itens if mostrar_todos else [
                    r for r in itens
                    if _classificar_nivel(
                        r.get("valor"), r.get("critico_baixo"), r.get("limite_baixo"),
                        r.get("otimo_min"), r.get("otimo_max"),
                        r.get("limite_alto"), r.get("critico_alto"))[0] in _RUINS
                ]

                if not lista:
                    col_container.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Icon("check_circle_outline_rounded", size=16, color=VERD),
                                ft.Text("Todos dentro do esperado", size=12, color=VERD),
                            ], spacing=8),
                            padding=ft.padding.symmetric(vertical=12),
                        )
                    )
                    return

                for r in lista:
                    col_container.controls.append(_card_vit_min(r, page))

            def _montar_card_micro(titulo, icone, cor_titulo, itens):
                """Card compacto — badge status + botoes. Detalhes em overlay."""
                _RUINS = {"critico_baixo","critico_alto","baixo","alto"}
                n_crit = sum(1 for r in itens if _classificar_nivel(
                    r.get("valor"), r.get("critico_baixo"), r.get("limite_baixo"),
                    r.get("otimo_min"), r.get("otimo_max"),
                    r.get("limite_alto"), r.get("critico_alto"))[0]
                    in ("critico_baixo","critico_alto"))
                n_fora = sum(1 for r in itens if _classificar_nivel(
                    r.get("valor"), r.get("critico_baixo"), r.get("limite_baixo"),
                    r.get("otimo_min"), r.get("otimo_max"),
                    r.get("limite_alto"), r.get("critico_alto"))[0]
                    in ("baixo","alto"))
                status_cor = VERM if n_crit else (LAR if n_fora else VERD)
                status_txt = (f"{n_crit} crítico(s)" if n_crit
                              else f"{n_fora} fora do ideal" if n_fora
                              else "Todos normais")

                def _abrir_overlay_micro(so_ruins=False):
                    ref_ov_m = [None]
                    def _fechar_m(e=None):
                        if ref_ov_m[0] in page.overlay:
                            page.overlay.remove(ref_ov_m[0])
                        try: page.update()
                        except Exception: pass

                    filtro_ref = ["ruins" if so_ruins else "todos"]
                    col_itens = ft.Column(spacing=6)
                    _grafico_barras(itens, filtro_ref, titulo, icone, cor_titulo, col_itens)

                    # chips de filtro dentro do overlay
                    chip_ruins = ft.Container(
                        content=ft.Text("Ruins/Críticos", size=10,
                                        color=VERM if filtro_ref[0]=="ruins" else MUT,
                                        weight=ft.FontWeight.W_600),
                        bgcolor=ft.Colors.with_opacity(0.15 if filtro_ref[0]=="ruins" else 0.05, VERM),
                        border_radius=10,
                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                        ink=True,
                    )
                    chip_todos = ft.Container(
                        content=ft.Text("Todos", size=10,
                                        color=AZUL if filtro_ref[0]=="todos" else MUT,
                                        weight=ft.FontWeight.W_600),
                        bgcolor=ft.Colors.with_opacity(0.15 if filtro_ref[0]=="todos" else 0.05, AZUL),
                        border_radius=10,
                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                        ink=True,
                    )

                    def _set_ruins(e):
                        filtro_ref[0] = "ruins"
                        _grafico_barras(itens, filtro_ref, titulo, icone, cor_titulo, col_itens)
                        chip_ruins.bgcolor = ft.Colors.with_opacity(0.15, VERM)
                        chip_ruins.content.color = VERM
                        chip_todos.bgcolor = ft.Colors.with_opacity(0.05, AZUL)
                        chip_todos.content.color = MUT
                        try: page.update()
                        except Exception: pass

                    def _set_todos(e):
                        filtro_ref[0] = "todos"
                        _grafico_barras(itens, filtro_ref, titulo, icone, cor_titulo, col_itens)
                        chip_todos.bgcolor = ft.Colors.with_opacity(0.15, AZUL)
                        chip_todos.content.color = AZUL
                        chip_ruins.bgcolor = ft.Colors.with_opacity(0.05, VERM)
                        chip_ruins.content.color = MUT
                        try: page.update()
                        except Exception: pass

                    chip_ruins.on_click = _set_ruins
                    chip_todos.on_click = _set_todos

                    from shared.layout import Layout as _LayM
                    _laym = _LayM(page)
                    _cab_m = _laym.criar_cabecalho(
                        titulo, _fechar_m,
                        icone_titulo=icone, cor_titulo=cor_titulo)
                    ref_ov_m[0] = ft.Container(
                        content=ft.Column([
                            ft.Container(height=_laym.spacer_topo, bgcolor=BG),
                            _cab_m,
                            ft.Container(
                                content=ft.Column([
                                    ft.Row([chip_ruins, chip_todos], spacing=6),
                                    ft.Divider(height=1, color=BD2),
                                    col_itens,
                                ], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True),
                                expand=True,
                                padding=ft.padding.symmetric(horizontal=16, vertical=8)),
                        ], spacing=0, expand=True),
                        bgcolor=BG, expand=True)
                    page.overlay.append(ref_ov_m[0])
                    try: page.update()
                    except Exception: pass

                # badge status clicavel (so se ruins)
                btn_status = ft.Container(
                    content=ft.Text(status_txt, size=10, color=status_cor,
                                    weight=ft.FontWeight.W_600),
                    bgcolor=ft.Colors.with_opacity(0.12, status_cor),
                    border_radius=8, ink=bool(n_crit or n_fora),
                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                )
                if n_crit or n_fora:
                    btn_status.on_click = lambda e: _abrir_overlay_micro(so_ruins=True)

                # botao ver detalhes
                btn_det = ft.Container(
                    content=ft.Row([
                        ft.Text("Ver detalhes", size=11, color=cor_titulo),
                        ft.Icon("chevron_right_rounded", size=13, color=cor_titulo),
                    ], spacing=2, tight=True),
                    border_radius=8, ink=True,
                    padding=ft.padding.symmetric(horizontal=6, vertical=5),
                )
                btn_det.on_click = lambda e: _abrir_overlay_micro(so_ruins=False)

                return ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Icon(icone, size=14, color=cor_titulo),
                                bgcolor=ft.Colors.with_opacity(0.13, cor_titulo),
                                border_radius=8, width=30, height=30,
                                alignment=ft.alignment.Alignment(0, 0),
                            ),
                            ft.Text(titulo, size=13, color=TXT,
                                    weight=ft.FontWeight.W_700, expand=True),
                            btn_status,
                        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Row([
                            ft.Text(f"{len(itens)} itens", size=10, color=MUT, expand=True),
                            btn_det,
                        ]),
                    ], spacing=6, tight=True),
                    bgcolor=ft.Colors.with_opacity(0.06, cor_titulo),
                    border_radius=12,
                    padding=ft.padding.all(14),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.25, cor_titulo)),
                )

            if vitaminas:
                area.controls.append(
                    _montar_card_micro("Vitaminas", "science_rounded", ROXO, vitaminas))
            if minerais:
                area.controls.append(
                    _montar_card_micro("Minerais", "diamond_rounded", AZUL, minerais))

        # ── SISTEMAS CORPORAIS ───────────────────────────────────────────────
        _ORDEM_SISTEMAS = [
            "Cardiaco", "Visceral", "Sangue",
            "Hormônios", "Ortopedia", "Psiquiatria", "Visao & Audicao",
        ]
        sistemas_ordenados = sorted(
            por_sistema.keys(),
            key=lambda s: _ORDEM_SISTEMAS.index(s) if s in _ORDEM_SISTEMAS else 99
        )

        if sistemas_ordenados:
            area.controls.append(_secao_titulo(
                "Sistemas Corporais", "account_tree_rounded", ROXO))
            # grid 2 colunas
            pares = [sistemas_ordenados[i:i+2] for i in range(0, len(sistemas_ordenados), 2)]
            for par in pares:
                row_cards = ft.Row(spacing=8)
                for sis in par:
                    row_cards.controls.append(
                        _card_sistema(sis, por_sistema[sis], page)
                    )
                if len(par) == 1:
                    row_cards.controls.append(ft.Container(expand=True))
                area.controls.append(row_cards)

        # ── GLICEMIA CASEIRA ─────────────────────────────────────────────────
        if glicemia:
            area.controls.append(_secao_titulo(
                "Glicemia Caseira", "water_drop_rounded", "#FF6B6B"))
            media = sum(
                float(str(r.get("valor","0")).replace(",","."))
                for r in glicemia
            ) / len(glicemia)
            ult = glicemia[0]
            try:
                v_ult = float(str(ult.get("valor","")).replace(",","."))
                cor_ult = VERD if v_ult <= 99 else (AMAR if v_ult <= 125 else VERM)
            except:
                v_ult = 0; cor_ult = MUT

            area.controls.append(ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Text("Última medição", size=10, color=MUT),
                        ft.Row([
                            ft.Text(str(ult.get("valor","")), size=26,
                                    color=cor_ult, weight=ft.FontWeight.W_800),
                            ft.Text("mg/dL", size=11, color=MUT),
                        ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.END),
                        ft.Text(_dias_atras(ult.get("data_medicao")), size=10, color=MUT),
                    ], spacing=2, expand=True),
                    ft.VerticalDivider(color=BD2, width=1),
                    ft.Column([
                        ft.Text("Média", size=10, color=MUT),
                        ft.Row([
                            ft.Text(f"{media:.1f}", size=22,
                                    color=VERD if media <= 99 else (AMAR if media <= 125 else VERM),
                                    weight=ft.FontWeight.W_700),
                            ft.Text("mg/dL", size=10, color=MUT),
                        ], spacing=3, vertical_alignment=ft.CrossAxisAlignment.END),
                        ft.Text(f"{len(glicemia)} medições", size=10, color=MUT),
                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.END),
                ], spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=COR_CARD, border_radius=10,
                padding=ft.padding.all(14),
                border=ft.border.all(1, BD2),
            ))
            area.controls.append(_mini_grafico_glicemia(glicemia))

        # ── TRATAMENTOS EM ANDAMENTO ─────────────────────────────────────────
        area.controls.append(_secao_titulo(
            "Tratamentos em Andamento", "healing_rounded", LAR))
        area.controls.append(ft.Container(
            content=ft.Row([
                ft.Icon("construction_rounded", size=16, color=MUT),
                ft.Text("Conteúdo a definir", size=12, color=MUT),
            ], spacing=8),
            bgcolor=COR_CARD, border_radius=10,
            padding=ft.padding.all(16),
            border=ft.border.all(1, BD2),
        ))

        # ── HISTORICO RELEVANTE ──────────────────────────────────────────────
        hist_alertas = [h for h in historico if h.get("alerta")]
        if hist_alertas:
            area.controls.append(_secao_titulo(
                "Histórico — Eventos Relevantes", "history_rounded", AMAR))
            for h in hist_alertas[:5]:
                area.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon("report_rounded", size=13, color=AMAR),
                            ft.Text(h.get("titulo",""), size=13, color=TXT,
                                    weight=ft.FontWeight.W_600, expand=True),
                            ft.Text(h.get("data_aprox",""), size=10, color=MUT),
                        ], spacing=8),
                        ft.Text(h.get("sequela") or h.get("descricao","")[:120],
                                size=11, color=SEC),
                    ], spacing=4),
                    bgcolor=ft.Colors.with_opacity(0.05, AMAR),
                    border_radius=10,
                    padding=ft.padding.all(12),
                    border=ft.Border(
                        left=ft.BorderSide(3, AMAR),
                        top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                        right=ft.BorderSide(1, BD),
                    ),
                ))

        # ── ROTINA DIARIA ────────────────────────────────────────────────────
        area.controls.append(_secao_titulo(
            "Rotina & Correlações", "today_rounded", AZUL))
        area.controls.append(ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon("info_outline_rounded", size=14, color=MUT),
                    ft.Text("Rotina ainda não alimentada", size=12, color=MUT,
                            expand=True),
                ], spacing=8),
                ft.Text(
                    "Quando você começar a registrar o diário de rotina, "
                    "esta seção vai correlacionar automaticamente alimentação, "
                    "sono e atividades com as variações nos seus exames.",
                    size=11, color=MUT,
                ),
            ], spacing=6),
            bgcolor=COR_CARD, border_radius=10,
            padding=ft.padding.all(14),
            border=ft.border.all(1, BD2),
        ))

        # ── RODAPE ───────────────────────────────────────────────────────────
        area.controls.append(ft.Container(
            content=ft.Text(
                f"Gerado em {date.today().strftime('%d/%m/%Y')} · "
                f"{n_total} parâmetros · {len(remedios)} medicamentos",
                size=10, color=MUT, text_align=ft.TextAlign.CENTER,
            ),
            padding=ft.padding.only(top=12, bottom=20),
            alignment=ft.alignment.Alignment(0, 0),
        ))

        if _montado[0]:
            try: page.update()
            except Exception: pass

    _rebuild()

    btn_atualizar = ft.Container(
        content=ft.Row([
            ft.Icon("refresh_rounded", size=14, color=AZUL),
            ft.Text("Atualizar", size=12, color=AZUL),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8, ink=True,
    )
    btn_atualizar.on_click = lambda e: _rebuild()

    cabecalho = lay.criar_cabecalho(
        "Checkup de Saúde",
        lambda e=None: voltar_fn() if voltar_fn else None,
        icone_titulo="health_and_safety_rounded",
        cor_titulo=VERD,
        acoes=[btn_atualizar],
    )
    corpo = lay.criar_corpo(cabecalho, area)
    _montado[0] = True
    return ft.Container(bgcolor=BG, expand=True, content=corpo)
