# -*- coding: utf-8 -*-
# Prontuario | telas/tela_receitas.py
import flet as ft
import logging
import threading
from shared.layout import Layout
from dados.model_prontuario import (
    listar_receitas, salvar_receita_culinaria, excluir_receita_culinaria,
    listar_ingredientes_receita, salvar_ingrediente_receita, excluir_ingrediente_receita,
    salvar_nutricao, carregar_nutricao,
)

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2  = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; LAR = "#F0883E"; VERM = "#DA3633"
ROXO = "#BC8CFF"; AMAR = "#D29922"

_UNIDADES = [
    ("Unidade","Unidade"),("g","g"),("kg","kg"),("ml","ml"),("Litro","Litro"),
    ("Xicara","Xicara"),("C.Sopa","C.Sopa"),("C.Cha","C.Cha"),
    ("Fatia","Fatia"),("Porcao","Porcao"),("Scoop","Scoop"),
    ("Pitada","Pitada"),("Ramo","Ramo"),
]

_PORCOES = [
    ("C.Sopa","C.Sopa"),("C.Cha","C.Cha"),("Scoop","Scoop"),
    ("Porcao","Porcao"),("Fatia","Fatia"),("Xicara","Xicara"),
    ("ml","ml"),("g","g"),("Unidade","Unidade"),
]


def _campo(label, valor="", hint=None, multiline=False, min_lines=1,
           keyboard=ft.KeyboardType.TEXT):
    kw = dict(label=label, value=valor or "", bgcolor=CARD, border_color=BD2,
              focused_border_color=AZUL, label_style=ft.TextStyle(color=SEC, size=11),
              text_style=ft.TextStyle(color=TXT), border_radius=8,
              multiline=multiline, min_lines=min_lines, keyboard_type=keyboard)
    if hint:
        kw["hint_text"] = hint
        kw["hint_style"] = ft.TextStyle(color=MUT, size=11)
    return ft.TextField(**kw)


def _label_sec(txt, cor=SEC):
    return ft.Text(txt, size=10, color=cor, weight=ft.FontWeight.W_600)


def criar_tela_receitas(page: ft.Page, voltar_fn, navegar_fn=None) -> ft.Container:
    lay      = Layout(page)
    area     = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
    _montado = [False]

    def _sync():
        def _bkp():
            try:
                from backup.drive_backup import fazer_backup
                fazer_backup(forcar=True)
            except Exception: pass
        threading.Thread(target=_bkp, daemon=True).start()

    # ── Lista principal ────────────────────────────────────────────

    def _rebuild():
        area.controls.clear()
        receitas = listar_receitas()
        if not receitas:
            area.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("menu_book_rounded", size=48, color=MUT),
                    ft.Text("Nenhuma receita cadastrada.", size=13, color=SEC,
                            text_align="center"),
                    ft.Text("Use + Nova para criar sua primeira receita.",
                            size=11, color=MUT, text_align="center"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=8, tight=True),
                padding=ft.padding.symmetric(vertical=60),
                alignment=ft.Alignment(0, 0),
            ))
        else:
            for r in receitas:
                ingrs = listar_ingredientes_receita(r["id"])
                n_ingr = len(ingrs)
                porcao = ""
                if r.get("porcao_qtd"):
                    porcao = f"  ·  Porção: {r['porcao_qtd']} {r.get('porcao_unid','')}"

                btn_edit = ft.Container(
                    content=ft.Icon("edit_rounded", size=14, color=SEC),
                    padding=4, border_radius=6, ink=True)
                btn_del = ft.Container(
                    content=ft.Icon("delete_outline_rounded", size=14, color=VERM),
                    padding=4, border_radius=6, ink=True)

                def _on_edit(e, _r=r): _abrir_form(_r)
                def _on_del(e, _r=r): _confirmar_excluir(_r)
                btn_edit.on_click = _on_edit
                btn_del.on_click  = _on_del

                area.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(r["nome"], size=13, color=TXT,
                                    weight=ft.FontWeight.W_600),
                            ft.Text(f"{n_ingr} ingrediente(s){porcao}",
                                    size=11, color=MUT),
                        ], spacing=2, tight=True, expand=True),
                        btn_edit, btn_del,
                    ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD, border_radius=10, padding=ft.padding.all(12),
                    border=ft.Border(
                        top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                        left=ft.BorderSide(3, LAR), right=ft.BorderSide(1, BD)),
                ))
        if _montado[0]:
            try: page.update()
            except Exception: pass

    # ── Confirmação de exclusão ────────────────────────────────────

    def _confirmar_excluir(r):
        ref = [None]
        def _fechar(e=None):
            if ref[0] in page.overlay: page.overlay.remove(ref[0])
            try: page.update()
            except Exception: pass
        def _ok(e=None):
            _fechar()
            excluir_receita_culinaria(r["id"])
            _rebuild(); _sync()
        btn_c = ft.Container(
            content=ft.Text("Cancelar", size=13, color=TXT, weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=BD2, ink=True, expand=True,
            alignment=ft.Alignment(0, 0))
        btn_o = ft.Container(
            content=ft.Text("Excluir", size=13, color=VERM, weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=ft.Colors.with_opacity(0.13, VERM),
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.with_opacity(0.4, VERM)),
                bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.4, VERM)),
                left=ft.BorderSide(1, ft.Colors.with_opacity(0.4, VERM)),
                right=ft.BorderSide(1, ft.Colors.with_opacity(0.4, VERM))),
            ink=True, expand=True, alignment=ft.Alignment(0, 0))
        btn_c.on_click = _fechar
        btn_o.on_click = _ok
        ref[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Excluir receita?", size=15, color=TXT,
                            weight=ft.FontWeight.W_700, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=4),
                    ft.Text(f"'{r['nome']}' sera removida.", size=13,
                            color=SEC, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=16),
                    ft.Row([btn_c, ft.Container(width=8), btn_o]),
                ], spacing=0, tight=True,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD, border_radius=14, padding=ft.padding.all(20),
                width=min(page.width - 32, 320) if page.width else 300),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0))
        ref[0].on_click = _fechar
        page.overlay.append(ref[0])
        try: page.update()
        except Exception: pass

    # ── Form de receita (tela fullscreen) ──────────────────────────

    def _abrir_form(receita=None):
        r       = receita or {}
        ref_ov  = [None]
        rid_ref = [r.get("id")]  # id salvo apos primeiro save

        f_nome    = _campo("Nome *", r.get("nome",""),
                           hint="ex: Tempero Verde, Mix de Castanhas")
        f_preparo = _campo("Modo de preparo", r.get("modo_preparo",""),
                           multiline=True, min_lines=3,
                           hint="Como preparar esta receita")
        f_porc_q  = _campo("Quantidade da porção", r.get("porcao_qtd",""),
                           hint="ex: 1", keyboard=ft.KeyboardType.NUMBER)
        dd_porc_u = ft.Dropdown(
            label="Unidade da porção",
            options=[ft.dropdown.Option(key=k, text=v) for k, v in _PORCOES],
            value=r.get("porcao_unid","C.Sopa") or "C.Sopa",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT), border_radius=8,
        )
        dd_porc_u.on_change = lambda e: None
        txt_err = ft.Text("", color=VERM, size=12)

        # ── Ingredientes ──────────────────────────────────────────
        ingr_col = ft.Column(spacing=6, tight=True)

        def _refresh_ingr():
            ingr_col.controls.clear()
            if not rid_ref[0]:
                ingr_col.controls.append(
                    ft.Text("Salve a receita para adicionar ingredientes.",
                            size=11, color=MUT))
                try: page.update()
                except Exception: pass
                return
            lista = listar_ingredientes_receita(rid_ref[0])
            if not lista:
                ingr_col.controls.append(
                    ft.Text("Nenhum ingrediente ainda.", size=11, color=MUT))
            else:
                for ing in lista:
                    qty  = (ing.get("quantidade") or "").strip()
                    unid = (ing.get("unidade") or "").strip()
                    qty_str = f"{qty} {unid}  · " if qty else ""
                    nome_ing = ing.get("descricao") or ing.get("sub_nome") or ""

                    btn_edit_i = ft.Container(
                        content=ft.Icon("edit_rounded", size=13, color=SEC),
                        padding=4, border_radius=6, ink=True)
                    btn_del_i = ft.Container(
                        content=ft.Icon("delete_outline_rounded", size=13, color=VERM),
                        padding=4, border_radius=6, ink=True)

                    def _on_edit_i(e, _ing=ing): _abrir_form_ingrediente(_ing)
                    def _on_del_i(e, iid=ing["id"], inome=nome_ing):
                        excluir_ingrediente_receita(iid)
                        _refresh_ingr()
                        _sync()

                    btn_edit_i.on_click = _on_edit_i
                    btn_del_i.on_click  = _on_del_i

                    ingr_col.controls.append(ft.Container(
                        content=ft.Row([
                            ft.Text(qty_str + nome_ing, size=12, color=TXT, expand=True),
                            btn_edit_i, btn_del_i,
                        ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor=BG, border_radius=8,
                        padding=ft.padding.symmetric(horizontal=10, vertical=7),
                        border=ft.Border(
                            top=ft.BorderSide(1, BD2), bottom=ft.BorderSide(1, BD2),
                            left=ft.BorderSide(2, LAR), right=ft.BorderSide(1, BD2)),
                    ))

                # ── Total calculado ───────────────────────────────
                totais = {}
                for ing in lista:
                    qty = (ing.get("quantidade") or "").strip()
                    unid = (ing.get("unidade") or "g").strip()
                    try:
                        totais[unid] = totais.get(unid, 0) + float(qty)
                    except (ValueError, TypeError):
                        pass
                if totais:
                    total_str = "  +  ".join(
                        f"{v:.0f} {u}" for u, v in totais.items())
                    ingr_col.controls.append(ft.Container(
                        content=ft.Row([
                            ft.Icon("functions_rounded", size=12, color=AMAR),
                            ft.Text(f"Total: {total_str}", size=11, color=AMAR,
                                    weight=ft.FontWeight.W_600),
                        ], spacing=6),
                        padding=ft.padding.only(top=6, left=4),
                    ))
            try: page.update()
            except Exception: pass

        def _abrir_form_ingrediente(ingrediente=None):
            ing     = ingrediente or {}
            ref_fi  = [None]
            f_desc  = _campo("Ingrediente *", ing.get("descricao",""),
                             hint="ex: Salsinha, Alho, Ovos")
            f_qty   = _campo("Quantidade", ing.get("quantidade",""),
                             hint="ex: 3", keyboard=ft.KeyboardType.NUMBER)
            dd_unid = ft.Dropdown(
                label="Unidade",
                options=[ft.dropdown.Option(key=k, text=v) for k, v in _UNIDADES],
                value=ing.get("unidade","g") or "g",
                bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
                label_style=ft.TextStyle(color=SEC, size=11),
                text_style=ft.TextStyle(color=TXT), border_radius=8,
            )
            dd_unid.on_change = lambda e: None

            def _salvar_ingr(e=None):
                desc = (f_desc.value or "").strip()
                if not desc: return
                salvar_ingrediente_receita({
                    "id":         ing.get("id"),
                    "receita_id": rid_ref[0],
                    "tipo":       "item",
                    "descricao":  desc,
                    "quantidade": (f_qty.value or "").strip() or None,
                    "unidade":    dd_unid.value or "g",
                })
                if ref_fi[0] in page.overlay:
                    page.overlay.remove(ref_fi[0])
                try: page.update()
                except Exception: pass
                import asyncio as _aio
                async def _dr():
                    await _aio.sleep(0.1)
                    _refresh_ingr()
                    await _aio.sleep(0.05)
                    try: page.update()
                    except Exception: pass
                page.run_task(_dr)
                _sync()

            def _fechar_fi():
                if ref_fi[0] in page.overlay:
                    page.overlay.remove(ref_fi[0])
                try: page.update()
                except Exception: pass

            def _fc_i(e=None):
                # auto-salva se tem descrição preenchida
                if (f_desc.value or "").strip():
                    _salvar_ingr()
                else:
                    _fechar_fi()

            btn_ok_i = ft.Container(
                content=ft.Row([
                    ft.Icon("check_rounded", size=14, color=VERD),
                    ft.Text("Salvar", size=13, color=VERD, weight=ft.FontWeight.W_600),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                border_radius=8, ink=True)
            btn_ok_i.on_click = _salvar_ingr

            titulo_i = "Editar ingrediente" if ing.get("id") else "Novo ingrediente"
            cab_i = lay.criar_cabecalho(
                titulo_i, _fc_i,
                icone_titulo="egg_rounded", cor_titulo=LAR,
                acoes=[btn_ok_i])

            ref_fi[0] = ft.Container(
                content=ft.Column([
                    ft.Container(height=lay.spacer_topo, bgcolor=BG),
                    cab_i,
                    ft.Container(
                        content=ft.Column([
                            ft.Container(height=8),
                            f_desc,
                            ft.Row([
                                ft.Container(content=f_qty, expand=True),
                                ft.Container(content=dd_unid, expand=True),
                            ], spacing=8),
                            ft.Container(height=16),
                        ], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True),
                        expand=True,
                        padding=ft.padding.symmetric(horizontal=16),
                    ),
                ], spacing=0, expand=True),
                bgcolor=BG, expand=True,
            )
            page.overlay.append(ref_fi[0])
            try: page.update()
            except Exception: pass

        lbl_btn_add_ingr = ft.Text("Adicionar ingrediente", size=12, color=LAR)
        btn_add_ingr = ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=12, color=LAR),
                lbl_btn_add_ingr,
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_radius=8, ink=True,
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.with_opacity(0.4, LAR)),
                bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.4, LAR)),
                left=ft.BorderSide(1, ft.Colors.with_opacity(0.4, LAR)),
                right=ft.BorderSide(1, ft.Colors.with_opacity(0.4, LAR))))

        def _set_btn_ingr(salvando: bool):
            btn_add_ingr.disabled = salvando
            btn_add_ingr.opacity  = 0.45 if salvando else 1.0
            lbl_btn_add_ingr.value = "Salvando..." if salvando else "Adicionar ingrediente"
            try: page.update()
            except Exception: pass

        def _click_add_ingr(e=None):
            # auto-save se receita ainda nao tem id
            if not rid_ref[0]:
                nome = (f_nome.value or "").strip()
                if not nome:
                    txt_err.value = "Informe o nome da receita primeiro."
                    try: page.update()
                    except Exception: pass
                    return
                txt_err.value = ""
                _set_btn_ingr(True)
                novo_id = salvar_receita_culinaria({
                    "nome":  nome,
                    "ativo": 1,
                })
                rid_ref[0] = novo_id
                _set_btn_ingr(False)
                btn_add_ingr.visible = True
                _refresh_ingr()
                try: page.update()
                except Exception: pass
            _abrir_form_ingrediente()

        btn_add_ingr.on_click = _click_add_ingr

        # ── Salvar receita ────────────────────────────────────────
        def _salvar(e=None):
            nome = (f_nome.value or "").strip()
            if not nome:
                txt_err.value = "Nome obrigatorio."
                try: page.update()
                except Exception: pass
                return
            txt_err.value = ""
            novo_id = salvar_receita_culinaria({
                "id":           rid_ref[0],
                "nome":         nome,
                "modo_preparo": (f_preparo.value or "").strip() or None,
                "ativo": 1,
            })
            if not rid_ref[0]:
                rid_ref[0] = novo_id
            _rebuild()
            # overlay sync bloqueante
            ov_sync = ft.Container(
                content=ft.Container(
                    content=ft.Column([
                        ft.ProgressRing(color=LAR, width=32, height=32, stroke_width=3),
                        ft.Text("Sincronizando...", size=12, color=TXT),
                    ], tight=True, spacing=8,
                       horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD, border_radius=14, padding=ft.padding.all(24), width=200),
                bgcolor="#DD000000", expand=True, alignment=ft.Alignment(0, 0))
            page.overlay.append(ov_sync)
            try: page.update()
            except Exception: pass

            def _bkp_e_atualiza():
                try:
                    from backup.drive_backup import fazer_backup
                    fazer_backup(forcar=True)
                except Exception: pass
                if ov_sync in page.overlay:
                    page.overlay.remove(ov_sync)
                btn_add_ingr.visible = True
                import asyncio as _aio3
                async def _dr3():
                    await _aio3.sleep(0.1)
                    _refresh_ingr()
                    await _aio3.sleep(0.05)
                    try: page.update()
                    except Exception: pass
                page.run_task(_dr3)
                try: page.update()
                except Exception: pass
            threading.Thread(target=_bkp_e_atualiza, daemon=True).start()

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            _rebuild()
            try: page.update()
            except Exception: pass

        btn_salvar = ft.Container(
            content=ft.Row([
                ft.Icon("check_rounded", size=14, color=VERD),
                ft.Text("Salvar", size=13, color=VERD, weight=ft.FontWeight.W_600),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            border_radius=8, ink=True)
        btn_salvar.on_click = _salvar

        titulo = "Editar receita" if r.get("id") else "Nova receita"
        cab = lay.criar_cabecalho(
            titulo, _fechar,
            icone_titulo="menu_book_rounded", cor_titulo=LAR,
            acoes=[btn_salvar])

        # ── Tabela nutricional ─────────────────────────────────────
        nutr_col = ft.Column(spacing=0, tight=True)

        def _refresh_nutricao():
            nutr_col.controls.clear()
            if not rid_ref[0]:
                return
            n = carregar_nutricao("receita", rid_ref[0])
            if not n:
                return
            import json as _json

            def _linha(label, valor, unid, cor=TXT, negrito=False):
                return ft.Row([
                    ft.Text(label, size=11, color=SEC, expand=True),
                    ft.Text(f"{valor:.1f}" if valor else "—", size=11,
                            color=cor,
                            weight=ft.FontWeight.W_700 if negrito else ft.FontWeight.NORMAL),
                    ft.Text(f" {unid}", size=10, color=MUT),
                ], spacing=2)

            def _linha_sub(label, valor, unid):
                return ft.Row([
                    ft.Container(width=16),
                    ft.Text(label, size=10, color=MUT, expand=True),
                    ft.Text(f"{valor:.1f}" if valor else "—", size=10, color=SEC),
                    ft.Text(f" {unid}", size=10, color=MUT),
                ], spacing=2)

            linhas = [
                ft.Container(
                    content=ft.Row([
                        ft.Text("TABELA NUTRICIONAL", size=10, color=LAR,
                                weight=ft.FontWeight.W_700, expand=True),
                        ft.Text(f"Porção: {n['por_100g']:.0f}g", size=10, color=SEC),
                    ]), padding=ft.padding.only(bottom=4)),
                ft.Divider(height=1, color=LAR),
                _linha("Valor Energético", n.get("kcal"), "kcal", LAR, True),
                ft.Divider(height=1, color=BD2),
                _linha("Carboidratos", n.get("carboidratos"), "g"),
                _linha_sub("Açúcares", n.get("acucares"), "g"),
                ft.Divider(height=1, color=BD2),
                _linha("Proteínas", n.get("proteinas"), "g", VERD, True),
                ft.Divider(height=1, color=BD2),
                _linha("Gorduras Totais", n.get("gorduras"), "g"),
                _linha_sub("Saturadas", n.get("saturadas"), "g"),
                _linha_sub("Trans", n.get("trans"), "g"),
                ft.Divider(height=1, color=BD2),
                _linha("Fibra Alimentar", n.get("fibras"), "g"),
                ft.Divider(height=1, color=BD2),
                _linha("Sódio", n.get("sodio"), "mg"),
            ]

            vits_json = n.get("vitaminas_json")
            if vits_json:
                try:
                    vits = _json.loads(vits_json)
                    if vits:
                        linhas.append(ft.Divider(height=1, color=BD2))
                        linhas.append(ft.Text("Vitaminas e Minerais",
                                              size=10, color=SEC,
                                              weight=ft.FontWeight.W_600))
                        for nome_v, val_v in vits.items():
                            linhas.append(ft.Row([
                                ft.Text(nome_v, size=10, color=MUT, expand=True),
                                ft.Text(str(val_v), size=10, color=SEC),
                            ]))
                except Exception: pass

            nutr_col.controls.append(ft.Container(
                content=ft.Column(linhas, spacing=3, tight=True),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.all(12),
                border=ft.Border(
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    left=ft.BorderSide(3, LAR), right=ft.BorderSide(1, BD)),
            ))
            try: page.update()
            except Exception: pass

        # ── Botão Claudia para calcular nutrição ──────────────────
        _calculando_nutr = [False]
        lbl_claudia = ft.Text("Calcular Tabela Nutricional com Claudia",
                              size=12, color=ROXO)
        btn_claudia = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text("C", size=10, color=BG, weight=ft.FontWeight.W_700),
                    width=20, height=20, border_radius=10, bgcolor=ROXO,
                    alignment=ft.Alignment(0, 0)),
                lbl_claudia,
            ], spacing=8, tight=True),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border_radius=10, ink=True,
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO)),
                bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO)),
                left=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO)),
                right=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO))),
        )

        def _calcular_nutricao(e=None):
            if _calculando_nutr[0] or not rid_ref[0]: return
            lista = listar_ingredientes_receita(rid_ref[0])
            if not lista:
                return
            _calculando_nutr[0] = True
            lbl_claudia.value = "Calculando..."
            try: page.update()
            except Exception: pass

            def _run():
                try:
                    import json as _json
                    from utils.claudia_engine import get_client, _MODELO
                    linhas = []
                    for ing in lista:
                        qty  = (ing.get("quantidade") or "").strip()
                        unid = (ing.get("unidade") or "").strip()
                        desc = ing.get("descricao") or ""
                        linhas.append(f"- {qty} {unid} de {desc}")
                    nome_rec = (f_nome.value or "").strip() or "receita"
                    prompt = (
                        f"Calcule a tabela nutricional completa da receita '{nome_rec}' "
                        f"com os seguintes ingredientes:\n" + "\n".join(linhas) +
                        "\n\nRetorne SOMENTE JSON valido:\n"
                        '{"por_100g":100,"kcal":0,"kj":0,"carboidratos":0,"acucares":0,'
                        '"proteinas":0,"gorduras":0,"saturadas":0,"trans":0,'
                        '"fibras":0,"sodio":0,'
                        '"vitaminas":{"Vit C":"0mg","Calcio":"0mg"}}'
                        "\n\nOs valores devem ser por 100g da receita pronta. "
                        "Inclua apenas vitaminas/minerais relevantes."
                    )
                    client = get_client()
                    resp = client.messages.create(
                        model=_MODELO, max_tokens=1024,
                        system="Voce e um nutricionista. Retorne SOMENTE JSON valido.",
                        messages=[{"role": "user", "content": prompt}],
                    )
                    raw = "".join(b.text for b in resp.content
                                  if hasattr(b, "text")).strip()
                    if raw.startswith("```"):
                        raw = raw.split("```")[1]
                        if raw.startswith("json"): raw = raw[4:]
                    dados = _json.loads(raw)
                    vits = dados.pop("vitaminas", {})
                    salvar_nutricao({
                        "entidade_tipo": "receita",
                        "entidade_id":   rid_ref[0],
                        **{k: dados.get(k) for k in
                           ["por_100g","kcal","kj","carboidratos","acucares",
                            "proteinas","gorduras","saturadas","trans","fibras","sodio"]},
                        "vitaminas_json": _json.dumps(vits, ensure_ascii=False) if vits else None,
                    })
                    # sync
                    from backup.drive_backup import fazer_backup
                    fazer_backup(forcar=True)
                except Exception as ex:
                    log.warning("[RECEITAS] nutricao erro: %s", ex)
                finally:
                    _calculando_nutr[0] = False
                    lbl_claudia.value = "Recalcular Tabela Nutricional com Claudia"
                    _refresh_nutricao()
                    try: page.update()
                    except Exception: pass

            threading.Thread(target=_run, daemon=True, name="NutrReceita").start()

        btn_claudia.on_click = _calcular_nutricao

        area_form = ft.Column([
            ft.Container(height=8),
            f_nome,
            _label_sec("INGREDIENTES"),
            ingr_col,
            btn_add_ingr,
            ft.Divider(height=1, color=BD2),
            btn_claudia,
            nutr_col,
            ft.Divider(height=1, color=BD2),
            _label_sec("MODO DE PREPARO"),
            f_preparo,
            txt_err,
            ft.Container(height=16),
        ], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

        ref_ov[0] = ft.Container(
            content=ft.Column([
                ft.Container(height=lay.spacer_topo, bgcolor=BG),
                cab,
                ft.Container(
                    content=area_form, expand=True,
                    padding=ft.padding.symmetric(horizontal=16),
                ),
            ], spacing=0, expand=True),
            bgcolor=BG, expand=True,
        )
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass
        if rid_ref[0]:
            import asyncio as _aio2
            async def _dr2():
                await _aio2.sleep(0.05)
                _refresh_ingr()
                _refresh_nutricao()
            page.run_task(_dr2)

    # ── Montar tela ────────────────────────────────────────────────

    _rebuild()

    btn_novo = ft.Container(
        content=ft.Row([
            ft.Icon("add_rounded", size=16, color=LAR),
            ft.Text("Nova", size=13, color=LAR),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        border_radius=8, ink=True,
    )
    btn_novo.on_click = lambda e: _abrir_form()

    cabecalho = lay.criar_cabecalho(
        "Receitas", voltar_fn,
        icone_titulo="menu_book_rounded", cor_titulo=LAR,
        acoes=[btn_novo])
    corpo = lay.criar_corpo(cabecalho, area)
    _montado[0] = True
    return ft.Container(bgcolor=BG, expand=True, content=corpo)
