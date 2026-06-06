# -*- coding: utf-8 -*-
# Prontuario | telas/tela_nutricional.py
import flet as ft
import logging
import threading
import json
from shared.layout import Layout
from dados.model_prontuario import (
    listar_templates, listar_momentos, listar_itens,
    calcular_nutricao_momento, carregar_nutricao,
)

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2  = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; LAR = "#F0883E"; VERM = "#DA3633"
ROXO = "#BC8CFF"; AMAR = "#D29922"
BG_CARD = "#0D1117"


def _label_sec(txt, cor=SEC):
    return ft.Text(txt, size=10, color=cor, weight=ft.FontWeight.W_600)


def criar_tela_nutricional(page: ft.Page, voltar_fn, navegar_fn=None) -> ft.Container:
    lay      = Layout(page)
    area     = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
    _montado = [False]
    _calculando = [False]

    def _rebuild():
        area.controls.clear()
        _montar_tabela()
        if _montado[0]:
            try: page.update()
            except Exception: pass

    def _montar_tabela():
        templates = listar_templates(so_ativos=True)
        template  = next((t for t in templates if t.get("padrao")), None)
        if not template and templates:
            template = templates[0]

        if not template:
            area.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("no_food_rounded", size=36, color=MUT),
                    ft.Text("Nenhuma rotina padrao definida.", size=13, color=SEC,
                            text_align="center"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=8, tight=True),
                padding=ft.padding.symmetric(vertical=60),
                alignment=ft.Alignment(0, 0),
            ))
            return

        momentos = listar_momentos(template["id"])
        total_dia: dict = {}

        def _v(n, k): return n.get(k) or 0.0

        for mom in momentos:
            itens = listar_itens(mom["id"])
            if not itens:
                continue

            nutr_mom = calcular_nutricao_momento(mom["id"])
            cal_mom  = _v(nutr_mom, "kcal")
            prot_mom = _v(nutr_mom, "proteinas")
            for k, v in nutr_mom.items():
                if v: total_dia[k] = total_dia.get(k, 0.0) + v

            linhas_itens = []
            from dados.model_prontuario import calcular_nutricao_item as _calc_item
            for it in itens:
                nutr_it = _calc_item(it["id"])
                cal_it  = _v(nutr_it, "kcal")
                prot_it = _v(nutr_it, "proteinas")
                linhas_itens.append(ft.Row([
                    ft.Text(it["descricao"], size=11, color=TXT, expand=True),
                    ft.Text(f"{cal_it:.0f}", size=11, color=LAR, width=54,
                            weight=ft.FontWeight.W_600, text_align=ft.TextAlign.RIGHT),
                    ft.Text(f"{prot_it:.1f}g", size=11, color=VERD, width=46,
                            text_align=ft.TextAlign.RIGHT),
                ], spacing=4))

            header = ft.Row([
                ft.Text("Item", size=9, color=MUT, expand=True),
                ft.Text("kcal", size=9, color=LAR, width=54,
                        text_align=ft.TextAlign.RIGHT),
                ft.Text("prot", size=9, color=VERD, width=46,
                        text_align=ft.TextAlign.RIGHT),
            ], spacing=4)

            area.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(mom["nome"], size=12, color=TXT,
                                weight=ft.FontWeight.W_700, expand=True),
                        ft.Text(f"{cal_mom:.0f} kcal", size=11, color=LAR),
                    ], spacing=8),
                    ft.Container(height=4),
                    header,
                    ft.Divider(height=1, color=BD2),
                    *linhas_itens,
                ], spacing=4, tight=True),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.all(12),
                border=ft.Border(
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    left=ft.BorderSide(3, LAR), right=ft.BorderSide(1, BD)),
            ))

        # ── Totais do dia ──────────────────────────────────────────
        total_cal  = _v(total_dia, "kcal")
        total_prot = _v(total_dia, "proteinas")
        total_carb = _v(total_dia, "carboidratos")
        total_gord = _v(total_dia, "gorduras")
        total_fibr = _v(total_dia, "fibras")
        total_sod  = _v(total_dia, "sodio")

        if total_cal > 0 or total_prot > 0:

            def _chip(icone, label, cor):
                return ft.Container(
                    content=ft.Row([
                        ft.Icon(icone, size=13, color=cor),
                        ft.Text(label, size=13, color=cor, weight=ft.FontWeight.W_700),
                    ], spacing=4, tight=True),
                    padding=ft.padding.symmetric(horizontal=10, vertical=7),
                    border_radius=8, bgcolor=ft.Colors.with_opacity(0.12, cor), expand=True)

            extras = []
            if total_carb: extras.append(
                ft.Row([ft.Text("Carboidratos", size=11, color=SEC, expand=True),
                        ft.Text(f"{total_carb:.1f}g", size=11, color=TXT)], spacing=4))
            if total_gord: extras.append(
                ft.Row([ft.Text("Gorduras", size=11, color=SEC, expand=True),
                        ft.Text(f"{total_gord:.1f}g", size=11, color=TXT)], spacing=4))
            if total_fibr: extras.append(
                ft.Row([ft.Text("Fibras", size=11, color=SEC, expand=True),
                        ft.Text(f"{total_fibr:.1f}g", size=11, color=TXT)], spacing=4))
            if total_sod: extras.append(
                ft.Row([ft.Text("Sódio", size=11, color=SEC, expand=True),
                        ft.Text(f"{total_sod:.0f}mg", size=11, color=TXT)], spacing=4))

            area.controls.append(ft.Container(
                content=ft.Column([
                    ft.Text("TOTAL DO DIA", size=10, color=LAR,
                            weight=ft.FontWeight.W_700),
                    ft.Row([
                        _chip("local_fire_department_rounded",
                              f"{total_cal:.0f} kcal", LAR),
                        _chip("fitness_center_rounded",
                              f"{total_prot:.1f}g prot", VERD),
                    ], spacing=8),
                    *extras,
                ], spacing=6, tight=True),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.all(12),
                border=ft.Border(
                    top=ft.BorderSide(2, LAR), bottom=ft.BorderSide(1, BD),
                    left=ft.BorderSide(1, BD), right=ft.BorderSide(1, BD)),
            ))

        # ── Calcular com Claudia ───────────────────────────────────
        area.controls.append(_mk_btn_claudia(momentos))

    def _mk_btn_claudia(momentos) -> ft.Container:
        lbl = ft.Text(
            "Calculando..." if _calculando[0] else "Calcular com Claudia",
            size=12, color=ROXO)
        btn = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text("C", size=11, color=BG, weight=ft.FontWeight.W_700),
                    width=22, height=22, border_radius=11, bgcolor=ROXO,
                    alignment=ft.Alignment(0, 0)),
                lbl,
            ], spacing=8, tight=True),
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            border_radius=10, ink=True,
            border=ft.Border(
                top=ft.BorderSide(1, f"{ROXO}55"), bottom=ft.BorderSide(1, f"{ROXO}55"),
                left=ft.BorderSide(1, f"{ROXO}55"), right=ft.BorderSide(1, f"{ROXO}55")),
        )
        def _calcular(e=None):
            if _calculando[0]: return
            _calculando[0] = True
            lbl.value = "Calculando..."
            try: page.update()
            except Exception: pass

            todos_itens = []
            for mom in momentos:
                for it in listar_itens(mom["id"]):
                    qty  = (it.get("quantidade") or "").strip()
                    unid = (it.get("unidade") or "").strip()
                    pref = f"{qty} {unid} " if qty else ""
                    todos_itens.append({
                        "id": it["id"],
                        "descricao": f"{pref}{it['descricao']}",
                        "momento": mom["nome"],
                    })

            def _run():
                try:
                    from utils.api_checker import exigir_creditos, SemCreditosError
                    from utils.claudia_engine import get_client, _MODELO
                    from dados.model_prontuario import salvar_nutricao_item
                    exigir_creditos(get_client)
                    linhas = "\n".join(f"- [{it['momento']}] {it['descricao']}"
                                       for it in todos_itens)
                    prompt = (
                        "Calcule os valores nutricionais de cada item abaixo.\n"
                        + linhas
                        + "\n\nRetorne SOMENTE JSON valido:\n"
                        + '{"itens":[{"descricao":"nome","calorias":0.0,"proteinas":0.0,"vitaminas":"A,C"}]}'
                    )
                    client = get_client()
                    resp = client.messages.create(
                        model=_MODELO, max_tokens=2048,
                        system="Voce e um nutricionista. Retorne SOMENTE JSON valido.",
                        messages=[{"role": "user", "content": prompt}],
                    )
                    raw = "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
                    if raw.startswith("```"):
                        raw = raw.split("```")[1]
                        if raw.startswith("json"): raw = raw[4:]
                    dados = json.loads(raw)
                    for i, it in enumerate(todos_itens):
                        itens_resp = dados.get("itens", [])
                        if i < len(itens_resp):
                            n = itens_resp[i]
                            salvar_nutricao_item(
                                it["id"],
                                n.get("calorias"), n.get("proteinas"),
                                n.get("vitaminas", ""),
                            )
                    page.pubsub.send_all_on_topic("_nutricao_status", {"status": "ok_tela"})
                except Exception as ex:
                    log.warning("[NUTRICIONAL] erro: %s", ex)
                    page.pubsub.send_all_on_topic("_nutricao_status",
                                                  {"status": "erro_tela", "msg": str(ex)})

            threading.Thread(target=_run, daemon=True, name="NutricaoTela").start()

        btn.on_click = _calcular
        return btn

    def _on_nutricao(topic, msg):
        if not isinstance(msg, dict): return
        if msg.get("status") in ("ok_tela", "erro_tela"):
            _calculando[0] = False
            _rebuild()

    page.pubsub.subscribe_topic("_nutricao_status", _on_nutricao)

    _rebuild()

    cabecalho = lay.criar_cabecalho(
        "Nutricional", voltar_fn,
        icone_titulo="local_dining_rounded", cor_titulo=VERD)
    corpo = lay.criar_corpo(cabecalho, area)
    _montado[0] = True
    return ft.Container(bgcolor=BG, expand=True, content=corpo)
