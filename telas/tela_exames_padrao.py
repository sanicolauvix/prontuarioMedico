# -*- coding: utf-8 -*-
"""
tela_exames_padrao.py — Koios Prontuário
Gerenciamento de Exames Padrão (CRUD)
Padrão visual: idêntico a tela_exames.py (header + barra de abas + área de conteúdo)
"""
import logging
import flet as ft
from dados.model_prontuario import (
    DB_PATH,
    listar_exames_padrao,
    salvar_exame_padrao,
    excluir_exame_padrao,
)

logger = logging.getLogger(__name__)

# ── Paleta ────────────────────────────────────────────────────
BG   = "#0D1117";  CARD = "#161B22";  BD  = "#21262D";  BD2 = "#30363D"
TXT  = "#E6EDF3";  SEC  = "#8B949E";  MUT = "#484F58"
AZUL = "#58A6FF";  VERD = "#3FB950";  LAR = "#F0883E"
VERM = "#DA3633";  ROXO = "#BC8CFF";  AMAR = "#D29922"


# ══════════════════════════════════════════════════════════════
# DIALOGS
# ══════════════════════════════════════════════════════════════

def _dialog_exame_padrao(page, titulo, dados, on_salvar):
    def _tf(label, valor, hint=None, largura=None):
        tf = ft.TextField(
            label=label,
            value=str(valor) if valor else "",
            hint_text=hint,
            bgcolor=BD,
            border_color=BD2,
            focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )
        if largura:
            tf.width = largura
        else:
            tf.expand = True
        return tf

    tf_nome      = _tf("Nome oficial *", dados.get("nome", ""))
    tf_categoria = _tf("Categoria", dados.get("categoria", ""), hint="ex: Hematologia")
    tf_unidade   = _tf("Unidade", dados.get("unidade", ""), hint="ex: mg/dL", largura=120)
    tf_ref_min   = _tf("Ref. mínima", dados.get("ref_min", ""), hint="0.0", largura=100)
    tf_ref_max   = _tf("Ref. máxima", dados.get("ref_max", ""), hint="10.0", largura=100)
    txt_erro     = ft.Text("", size=11, color=VERM)

    ref = [None]

    def _fechar(e=None):
        if ref[0] and ref[0] in page.overlay:
            page.overlay.remove(ref[0])
        try: page.update()
        except Exception: pass

    def _salvar(e):
        nome = tf_nome.value.strip()
        if not nome:
            txt_erro.value = "Nome oficial e obrigatorio."
            try: page.update()
            except Exception: pass
            return

        def _to_float(v):
            try:
                return float(v.replace(",", ".")) if v.strip() else None
            except ValueError:
                return None

        _fechar()
        on_salvar({
            "nome":      nome,
            "categoria": tf_categoria.value.strip() or "Geral",
            "unidade":   tf_unidade.value.strip(),
            "ref_min":   _to_float(tf_ref_min.value),
            "ref_max":   _to_float(tf_ref_max.value),
        })

    btn_cancel = ft.Container(
        content=ft.Text("Cancelar", size=13, color=SEC),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        border_radius=8, bgcolor=f"{SEC}22", ink=True,
    )
    btn_cancel.on_click = _fechar

    btn_salvar = ft.Container(
        content=ft.Text("Salvar", size=13, color=AZUL,
                        weight=ft.FontWeight.W_600),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        border_radius=8, bgcolor=f"{AZUL}22", ink=True,
    )
    btn_salvar.on_click = _salvar

    ref[0] = ft.Container(
        content=ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon("science_rounded", color=AZUL, size=18),
                    ft.Text(titulo, size=15, weight=ft.FontWeight.W_700, color=TXT),
                ], spacing=8),
                ft.Container(height=10),
                tf_nome,
                ft.Row([tf_categoria, tf_unidade], spacing=8,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([
                    ft.Text("Ref:", size=12, color=SEC),
                    tf_ref_min,
                    ft.Text("-", size=12, color=SEC),
                    tf_ref_max,
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                txt_erro,
                ft.Container(height=8),
                ft.Row([btn_cancel, btn_salvar], spacing=8,
                       alignment=ft.MainAxisAlignment.END),
            ], spacing=8, tight=True),
            bgcolor=CARD, border_radius=14,
            padding=ft.padding.all(20), width=340,
        ),
        bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
    )
    page.overlay.append(ref[0])
    try: page.update()
    except Exception: pass


def _dialog_confirmar_excluir(page, nome, on_confirmar):
    ref = [None]

    def _fechar(e=None):
        if ref[0] and ref[0] in page.overlay:
            page.overlay.remove(ref[0])
        try: page.update()
        except Exception: pass

    def _confirmar(e):
        _fechar()
        on_confirmar()

    btn_cancel = ft.Container(
        content=ft.Text("Cancelar", size=13, color=SEC),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        border_radius=8, bgcolor=f"{SEC}22", ink=True,
    )
    btn_cancel.on_click = _fechar

    btn_excluir = ft.Container(
        content=ft.Text("Excluir", size=13, color=VERM,
                        weight=ft.FontWeight.W_600),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        border_radius=8, bgcolor=f"{VERM}22", ink=True,
    )
    btn_excluir.on_click = _confirmar

    ref[0] = ft.Container(
        content=ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon("delete_outline_rounded", color=VERM, size=18),
                    ft.Text("Excluir exame padrao?", size=15,
                            weight=ft.FontWeight.W_700, color=TXT),
                ], spacing=8),
                ft.Container(height=8),
                ft.Text(f'"{nome}"', size=13, color=LAR,
                        weight=ft.FontWeight.W_600),
                ft.Text(
                    "Isso removera o exame padrao e todos os vinculos.\n"
                    "Os resultados gravados nao serao apagados.",
                    size=12, color=SEC,
                ),
                ft.Container(height=16),
                ft.Row([btn_cancel, btn_excluir], spacing=8,
                       alignment=ft.MainAxisAlignment.END),
            ], spacing=6, tight=True),
            bgcolor=CARD, border_radius=14,
            padding=ft.padding.all(20), width=320,
        ),
        bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
    )
    ref[0].on_click = _fechar
    page.overlay.append(ref[0])
    try: page.update()
    except Exception: pass


# ══════════════════════════════════════════════════════════════
# ABA: LISTA DE EXAMES PADRÃO
# ══════════════════════════════════════════════════════════════

def _conteudo_lista(page, parametro_pendente=None, voltar_fn=None):
    estado = {"todos": []}

    lista     = ft.Column(spacing=4)
    txt_total = ft.Text("", size=12, color=SEC)
    tf_busca  = ft.TextField(
        hint_text="Buscar por nome ou categoria...",
        prefix_icon="search_rounded",
        bgcolor=CARD,
        border_color=BD2,
        focused_border_color=AZUL,
        hint_style=ft.TextStyle(color=MUT),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        expand=True,
    )

    def _snack(msg, cor=SEC):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, color=TXT), bgcolor=CARD)
        page.snack_bar.open = True
        page.update()

    def _renderizar(items):
        lista.controls.clear()
        if not items:
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("search_off_rounded", size=44, color=MUT),
                    ft.Text("Nenhum exame padrão encontrado.", size=14, color=SEC),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                alignment=ft.alignment.center, padding=40,
            ))
            try: page.update()
            except Exception: pass
            return

        for ep in items:
            eid  = ep["id"]
            nome = ep.get("nome_oficial", "")
            cat  = ep.get("categoria", "")
            unid = ep.get("unidade", "")
            rmin = ep.get("ref_min")
            rmax = ep.get("ref_max")

            partes = []
            if cat:  partes.append(cat)
            if unid: partes.append(unid)
            if rmin is not None and rmax is not None:
                partes.append(f"ref: {rmin} – {rmax}")
            elif rmin is not None:
                partes.append(f"ref min: {rmin}")
            elif rmax is not None:
                partes.append(f"ref max: {rmax}")
            sub = "  •  ".join(partes) if partes else "sem detalhes"

            def _editar(e, ep=ep):
                _dialog_exame_padrao(
                    page, "Editar Exame Padrão",
                    {
                        "nome":      ep.get("nome_oficial", ""),
                        "categoria": ep.get("categoria", ""),
                        "unidade":   ep.get("unidade", ""),
                        "ref_min":   str(ep["ref_min"]) if ep.get("ref_min") is not None else "",
                        "ref_max":   str(ep["ref_max"]) if ep.get("ref_max") is not None else "",
                    },
                    lambda d, i=ep["id"]: _on_edicao(i, d),
                )

            def _del(e, id=eid, nm=nome):
                _dialog_confirmar_excluir(page, nm, lambda: _on_excluir(id, nm))

            lista.controls.append(ft.Container(
                content=ft.Row([
                    ft.Container(width=3, bgcolor=AZUL, border_radius=2,
                                 height=36),
                    ft.Column([
                        ft.Text(nome, size=13, color=TXT,
                                weight=ft.FontWeight.W_600),
                        ft.Text(sub, size=11, color=SEC),
                    ], spacing=2, expand=True, tight=True),
                    ft.IconButton(
                        "edit_outlined_rounded",
                        icon_color=AZUL, icon_size=18,
                        padding=ft.padding.all(4),
                        on_click=_editar,
                    ),
                    ft.IconButton(
                        "delete_outline_rounded",
                        icon_color=VERM, icon_size=18,
                        padding=ft.padding.all(4),
                        on_click=_del,
                    ),
                ], spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD, border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border=ft.Border(
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    left=ft.BorderSide(1, BD), right=ft.BorderSide(1, BD),
                ),
            ))
        try: page.update()
        except Exception: pass

    def carregar():
        resultado = listar_exames_padrao()
        if resultado is None:
            logger.error("Falha ao carregar exames padrão do banco.")
            resultado = []
        estado["todos"] = resultado
        txt_total.value = f"{len(resultado)} exame(s) padrão"
        _filtrar()

    def _filtrar(e=None):
        termo = (tf_busca.value or "").lower().strip()
        if not termo:
            _renderizar(estado["todos"])
        else:
            _renderizar([
                ep for ep in estado["todos"]
                if termo in ep.get("nome_oficial", "").lower()
                or termo in ep.get("categoria", "").lower()
            ])

    tf_busca.on_change = _filtrar

    def _on_novo(dados):
        novo_id = salvar_exame_padrao(dados)
        if novo_id is None:
            _snack("Erro ao salvar exame padrão.", VERM)
            return
        if parametro_pendente:
            try:
                from dados.limpeza import vincular_manualmente, executar_limpeza
                vincular_manualmente(parametro_pendente, novo_id)
                try:
                    executar_limpeza()
                except Exception as ex:
                    logger.error("Erro em executar_limpeza: %s", str(ex), exc_info=True)
            except Exception as ex:
                logger.error("Erro ao vincular parâmetro: %s", str(ex), exc_info=True)
            _snack(f"'{dados['nome']}' criado e vinculado!", VERD)
            if voltar_fn:
                voltar_fn()
        else:
            carregar()
            _snack(f"'{dados['nome']}' criado.", VERD)

    def _on_edicao(exame_id, dados):
        ok = salvar_exame_padrao(dados, exame_id=exame_id)
        if ok is None:
            _snack("Erro ao atualizar.", VERM)
            return
        carregar()
        _snack(f"'{dados['nome']}' atualizado.", AZUL)

    def _on_excluir(exame_id, nome):
        ok = excluir_exame_padrao(exame_id)
        if not ok:
            _snack("Erro ao excluir.", VERM)
            return
        carregar()
        _snack(f"'{nome}' excluído.", LAR)

    def _novo(e):
        nome_pre = ""
        unid_pre = ""
        if parametro_pendente:
            import re
            match = re.match(r'^(.*?)\s+([\d]+[,.][\d]+|[\d]+)\s*$',
                             parametro_pendente.strip())
            nome_pre = match.group(1).strip() if match else parametro_pendente.strip()
            unid_pre = match.group(2).strip() if match else ""
        _dialog_exame_padrao(
            page, "Novo Exame Padrão",
            {"nome": nome_pre, "categoria": "", "unidade": unid_pre,
             "ref_min": "", "ref_max": ""},
            _on_novo,
        )

    carregar()

    return [
        ft.Row([
            tf_busca,
            ft.FilledButton(
                content=ft.Row([
                    ft.Icon("add_rounded", size=16),
                    ft.Text("Novo", size=13, weight=ft.FontWeight.W_600),
                ], spacing=6, tight=True),
                style=ft.ButtonStyle(
                    bgcolor=VERD,
                    shape=ft.RoundedRectangleBorder(radius=7),
                    padding=ft.padding.symmetric(horizontal=12, vertical=7),
                ),
                on_click=_novo,
            ),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        txt_total,
        lista,
    ]


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL
# ══════════════════════════════════════════════════════════════

def criar_tela_exames_padrao(page: ft.Page, voltar_fn=None,
                             parametro_pendente: str = None):
    """
    voltar_fn: lambda sem args
    parametro_pendente: se vier da tela de pendências, abre o dialog
                        com o nome pré-preenchido e vincula ao salvar
    """
    ABAS = [
        (0, "science_outlined_rounded", "Exames Padrão", AZUL),
    ]
    aba_ativa = [0]

    barra_abas    = ft.Row(spacing=0)
    area_conteudo = ft.Column(spacing=8, expand=True, scroll=ft.ScrollMode.AUTO)

    def _rebuild_abas():
        barra_abas.controls.clear()
        for idx, icone, label, cor in ABAS:
            ativo = idx == aba_ativa[0]
            def _click(e, i=idx):
                aba_ativa[0] = i
                _rebuild_abas()
                _rebuild_conteudo()
            barra_abas.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon(icone, size=16, color=cor if ativo else SEC),
                    ft.Text(label, size=10,
                            color=cor if ativo else SEC,
                            weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.W_400),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=2, tight=True),
                expand=True,
                padding=ft.padding.symmetric(vertical=10),
                border=ft.Border(bottom=ft.BorderSide(2, cor if ativo else "#00000000")),
                on_click=_click,
            ))
        try: page.update()
        except Exception: pass

    def _rebuild_conteudo():
        area_conteudo.controls.clear()
        area_conteudo.controls.extend(
            _conteudo_lista(page, parametro_pendente, voltar_fn)
        )
        try: page.update()
        except Exception: pass

    _rebuild_abas()
    _rebuild_conteudo()

    cabecalho = ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Row([
                    ft.Icon("arrow_back_rounded", size=16),
                    ft.Text("Voltar", size=13),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                ink=True,
                on_click=lambda e: voltar_fn() if voltar_fn else None,
            ),
            ft.Row([
                ft.Icon("science_outlined_rounded", size=20, color=AZUL),
                ft.Text("Exames Padrão", size=18,
                        weight=ft.FontWeight.W_700, color=TXT),
            ], spacing=8, tight=True),
            ft.Container(expand=True),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=16, vertical=14),
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
    )

    corpo = ft.Column([
        cabecalho,
        ft.Container(content=barra_abas,
                     border=ft.Border(bottom=ft.BorderSide(1, BD))),
        ft.Container(
            content=area_conteudo,
            padding=ft.padding.all(16),
            expand=True,
        ),
    ], expand=True)

    try:
        larg = page.width or 800
    except Exception:
        larg = 800

    if larg > 500:
        conteudo_final = ft.Row([
            ft.Container(expand=True),
            ft.Container(content=corpo, width=480),
            ft.Container(expand=True),
        ], expand=True)
    else:
        conteudo_final = corpo

    return ft.Container(bgcolor=BG, expand=True, content=conteudo_final)
