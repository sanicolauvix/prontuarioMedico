# -*- coding: utf-8 -*-
# Prontuario | telas/tela_glicemia.py -- Glicemia: medicoes domesticas + exames de lab
import datetime
import sqlite3
import flet as ft
import logging
from shared.layout import Layout
from shared.widgets import abrir_sub_grafico
from dados.model_prontuario import (
    listar_exames_glicemia, listar_leituras_marcador,
    salvar_leitura_marcador, DB_PATH,
)
from telas.tela_exames import buscar_historico_exame

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; AMAR = "#D29922"
VERM = "#F85149"; COR  = "#FF6B6B"; ROXO = "#BC8CFF"

_TERMOS = ["glicose", "glucose", "glicemia", "glicada", "hba1c"]

# (label, referencia, limite_alto_para_claudia)
_MOMENTOS = [
    ("Jejum",      "70 - 99",  99),
    ("Apos 1h",    "< 180",   180),
    ("Apos 2h",    "< 140",   140),
    ("Ao acordar", "70 - 99",  99),
    ("Aleatoria",  "70 - 140", 140),
]


def _label_sec(texto, cor=MUT):
    return ft.Text(texto, size=10, color=cor, weight=ft.FontWeight.W_700)


def _avaliar_cor(valor_str):
    try:
        v = float(str(valor_str).replace(",", "."))
        if 70 <= v <= 99:
            return VERD
        if 100 <= v <= 125:
            return AMAR
        return VERM
    except Exception:
        return AZUL


def _nivel_glicemia(valor_str):
    try:
        v = float(str(valor_str).replace(",", "."))
        if v < 70:   return "critico_baixo"
        if v <= 99:  return "otimo"
        if v <= 125: return "alto"
        return "critico_alto"
    except Exception:
        return "sem_referencia"


def _parse_data(data_str):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime((data_str or "")[:10], fmt).date()
        except ValueError:
            pass
    return None


def _dias_txt(data_str):
    dt = _parse_data(data_str)
    if dt is None:
        return data_str[:10] if data_str else "—"
    dias = (datetime.date.today() - dt).days
    if dias == 0:  return "hoje"
    if dias == 1:  return "1 dia atras"
    return f"{dias} dias atras"


def _fora_do_range(valor: float, momento_label: str) -> bool:
    ref_limite = {m[0]: m[2] for m in _MOMENTOS}
    limite = ref_limite.get(momento_label, 140)
    return valor > limite or valor < 70


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL
# ══════════════════════════════════════════════════════════════

def criar_tela_glicemia(page: ft.Page, voltar_fn):
    lay      = Layout(page)
    _montado = [False]
    wrapper  = ft.Column(expand=True)

    area_lista = ft.Column(spacing=8)

    def _abrir_grafico(titulo, exame_dict):
        abrir_sub_grafico(page, wrapper, lay, titulo, exame_dict, _mostrar_principal)

    # ── Overlay: contexto Claudia apos valor anormal ────────────

    def _claudia_ctx(param, val, unidade, ref, leitura_id):
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
            hint_text="Ex: comi carboidrato, estresse, esqueci o remedio...",
            bgcolor=CARD, border_color=BD2, focused_border_color=ROXO,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, multiline=True, min_lines=2, max_lines=3,
        )

        def _salvar_ctx(e):
            ctx = (tf_ctx.value or "").strip()
            if ctx and leitura_id:
                try:
                    with sqlite3.connect(DB_PATH, timeout=30) as conn:
                        conn.execute(
                            "UPDATE marcadores_leituras SET contexto = ? WHERE id = ?",
                            (ctx, leitura_id),
                        )
                except Exception as ex:
                    log.warning("[GLIC] salvar_ctx: %s", ex)
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
                        f"Registrei {val_str} {unidade} ({param}).",
                        size=13, color=TXT, weight=ft.FontWeight.W_600,
                    ),
                    ft.Text(f"Valor fora do esperado ({ref}).", size=12, color=VERM),
                    ft.Container(height=8),
                    tf_ctx,
                    ft.Container(height=12),
                    ft.Row([btn_pular, btn_ctx], spacing=8,
                           alignment=ft.MainAxisAlignment.END),
                ], tight=True, spacing=4),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20), width=320,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try:
            page.update()
        except Exception:
            pass

    # ── Overlay: nova leitura de glicemia ───────────────────────

    def _abrir_form(e=None):
        ref_ov = [None]
        _momento_ref = ["Jejum"]

        tf_valor = ft.TextField(
            label="Glicemia (mg/dL)",
            bgcolor=CARD, border_color=BD2, focused_border_color=COR,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            keyboard_type=ft.KeyboardType.NUMBER,
            autofocus=True,
        )
        dd_momento = ft.Dropdown(
            label="Momento",
            bgcolor=CARD, border_color=BD2, focused_border_color=COR,
            label_style=ft.TextStyle(color=SEC),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            value="Jejum",
            options=[ft.dropdown.Option(m[0]) for m in _MOMENTOS],
        )
        tf_data = ft.TextField(
            label="Data",
            bgcolor=CARD, border_color=BD2, focused_border_color=COR,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            value=datetime.date.today().isoformat(),
        )
        tf_hora = ft.TextField(
            label="Hora (opcional, HH:MM)",
            bgcolor=CARD, border_color=BD2, focused_border_color=COR,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
        )
        tf_obs = ft.TextField(
            label="Observacao (opcional)",
            bgcolor=CARD, border_color=BD2, focused_border_color=COR,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, multiline=True, min_lines=1, max_lines=2,
        )
        txt_erro = ft.Text("", size=11, color=VERM, visible=False)

        def _on_momento(e):
            _momento_ref[0] = dd_momento.value or "Jejum"

        dd_momento.on_change = _on_momento

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try:
                page.update()
            except Exception:
                pass

        def _salvar(e):
            val_str  = (tf_valor.value or "").strip().replace(",", ".")
            data_str = (tf_data.value or "").strip()
            momento  = _momento_ref[0]

            if not val_str or not data_str:
                txt_erro.value   = "Preencha valor e data."
                txt_erro.visible = True
                try:
                    page.update()
                except Exception:
                    pass
                return

            try:
                val_num = float(val_str)
            except ValueError:
                txt_erro.value   = "Valor invalido."
                txt_erro.visible = True
                try:
                    page.update()
                except Exception:
                    pass
                return

            ref_str = next((m[1] for m in _MOMENTOS if m[0] == momento), "70 - 99")

            dados = {
                "parametro":    "Glicose",
                "categoria":    "Metabolico",
                "valor":        val_num,
                "valor_txt":    f"{val_num:.1f}",
                "unidade":      "mg/dL",
                "referencia":   ref_str,
                "data_medicao": data_str,
                "hora_medicao": (tf_hora.value or "").strip() or None,
                "fonte":        "manual",
                "observacoes":  f"[{momento}] " + ((tf_obs.value or "").strip()),
            }

            leitura_id = salvar_leitura_marcador(dados)
            _fechar()
            _carregar()

            if _fora_do_range(val_num, momento):
                _claudia_ctx("Glicose", val_num, "mg/dL", ref_str, leitura_id)

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
        tf_valor.on_submit = _salvar

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("water_drop_rounded", size=16, color=COR),
                        ft.Text("Nova Leitura — Glicemia", size=15, color=TXT,
                                weight=ft.FontWeight.W_700),
                    ], spacing=8),
                    ft.Container(height=4),
                    tf_valor,
                    dd_momento,
                    ft.Row([
                        ft.Container(content=tf_data, expand=True),
                        ft.Container(content=tf_hora, expand=True),
                    ], spacing=8),
                    tf_obs,
                    txt_erro,
                    ft.Container(height=4),
                    ft.Row([btn_cancel, btn_ok], spacing=8,
                           alignment=ft.MainAxisAlignment.CENTER),
                ], spacing=10, tight=True),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20), width=340,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try:
            page.update()
        except Exception:
            pass

    # ── Card reutilizavel ───────────────────────────────────────

    def _mk_card(cor_borda, val_txt, cor_val, titulo, subtitulo, unidade, on_click_fn):
        card = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text(val_txt, size=18,
                                    weight=ft.FontWeight.W_900, color=cor_val),
                    width=56, alignment=ft.alignment.Alignment(0, 0),
                ),
                ft.Column([
                    ft.Text(titulo, size=12, color=TXT, weight=ft.FontWeight.W_600),
                    ft.Text(subtitulo, size=11, color=SEC),
                ], spacing=1, expand=True),
                ft.Row([
                    ft.Text(unidade, size=10, color=MUT),
                    ft.Icon("chevron_right_rounded", size=14, color=MUT),
                ], spacing=4, tight=True),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=CARD, border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border=ft.Border(left=ft.BorderSide(3, cor_borda),
                             top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                             right=ft.BorderSide(1, BD)),
        )
        card.on_click = on_click_fn
        return card

    # ── Carregamento ────────────────────────────────────────────

    def _carregar():
        area_lista.controls.clear()

        # ── Card: Medicoes Domesticas ──────────────────────────
        leituras = listar_leituras_marcador(_TERMOS)

        if leituras:
            ult   = leituras[0]
            cor_v = _avaliar_cor(ult["valor"])
            try:
                val_txt = f"{float(str(ult['valor']).replace(',', '.')):.1f}"
            except Exception:
                val_txt = "--"
            n       = len(leituras)
            sub_dom = f"{n}x  •  {_dias_txt(ult.get('data_medicao',''))}"
            unidade = ult.get("unidade", "mg/dL")

            def _click_dom(e, _leit=leituras):
                hist = [
                    {
                        "valor":       r.get("valor_txt") or str(r["valor"]),
                        "unidade":     r.get("unidade", "mg/dL"),
                        "referencia":  r.get("referencia", "70 - 99"),
                        "nivel":       _nivel_glicemia(r["valor"]),
                        "data":        r.get("data_medicao", ""),
                        "laboratorio": "Domiciliar",
                        "arquivo":     "",
                        "drive_id":    "",
                    }
                    for r in _leit
                ]
                _abrir_grafico("Medicoes Domesticas",
                               {"nome_oficial": "Glicemia Domestica",
                                "unidade": "mg/dL", "historico": hist})
        else:
            cor_v   = MUT
            val_txt = "--"
            sub_dom = "sem registros  •  toque para registrar"
            unidade = "mg/dL"
            _click_dom = _abrir_form  # sem leituras: abre o form direto

        area_lista.controls.append(
            _mk_card(COR, val_txt, cor_v,
                     "Medicoes Domesticas", sub_dom, unidade, _click_dom))

        # ── Cards: Exames de laboratorio ───────────────────────
        exames = listar_exames_glicemia(_TERMOS)

        if not exames:
            area_lista.controls.append(
                ft.Text("Nenhum exame de laboratorio encontrado.", color=MUT, size=12))
        else:
            grupos = {}
            for r in exames:
                key = (r.get("parametro") or "Desconhecido").strip().lower()
                if key not in grupos:
                    grupos[key] = {
                        "parametro":       (r.get("parametro") or "Desconhecido").strip(),
                        "exame_padrao_id": r.get("exame_padrao_id"),
                        "resultados":      [],
                    }
                grupos[key]["resultados"].append(r)

            for grupo in grupos.values():
                regs   = grupo["resultados"]
                ultimo = regs[0]
                cor_v  = _avaliar_cor(ultimo["valor"])
                n      = len(regs)
                try:
                    val_txt = f"{float(str(ultimo['valor']).replace(',', '.')):.1f}"
                except Exception:
                    val_txt = "--"
                sub_lab = f"{n}x  •  {_dias_txt(ultimo.get('data_exame',''))}"
                unidade = ultimo.get("unidade", "mg/dL")
                titulo  = grupo["parametro"].title()
                ep_id   = grupo["exame_padrao_id"]

                def _click_lab(e, _titulo=titulo, _ep_id=ep_id, _unidade=unidade):
                    hist = buscar_historico_exame(_ep_id) if _ep_id else []
                    _abrir_grafico(_titulo,
                                   {"nome_oficial": _titulo,
                                    "unidade": _unidade, "historico": hist})

                area_lista.controls.append(
                    _mk_card(cor_v + "88", val_txt, cor_v,
                             titulo, sub_lab, unidade, _click_lab))

        if _montado[0]:
            try:
                page.update()
            except Exception:
                pass

    # ── Layout principal ────────────────────────────────────────

    area_principal = ft.Column([
        ft.Container(
            content=ft.Row([
                ft.Icon("biotech_rounded", size=12, color=AZUL),
                _label_sec("GLICEMIA", AZUL),
            ], spacing=6),
        ),
        area_lista,
        ft.Container(height=20),
    ], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    btn_registrar = ft.Container(
        content=ft.Row([
            ft.Icon("add_rounded", size=16, color=COR),
            ft.Text("Registrar", size=13, color=COR),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8, ink=True,
    )
    btn_registrar.on_click = _abrir_form

    cabecalho = lay.criar_cabecalho(
        "Glicemia", voltar_fn,
        icone_titulo="water_drop_rounded",
        cor_titulo=COR,
        acoes=[btn_registrar],
    )
    corpo = lay.criar_corpo(cabecalho, area_principal)

    def _mostrar_principal():
        wrapper.controls.clear()
        wrapper.controls.append(ft.Container(bgcolor=BG, expand=True, content=corpo))
        if _montado[0]:
            try:
                page.update()
            except Exception:
                pass

    _carregar()

    wrapper.controls.append(ft.Container(bgcolor=BG, expand=True, content=corpo))
    _montado[0] = True
    return wrapper
