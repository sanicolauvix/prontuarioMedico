# -*- coding: utf-8 -*-
# Prontuario | telas/tela_clinicas.py -- Cadastro de clinicas e locais de atendimento
import json as _json
import logging
import threading
import flet as ft
from shared.layout import Layout
from dados.model_prontuario import listar_clinicas, salvar_clinica, excluir_clinica

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; LAR = "#F0883E"
AMAR = "#D29922"; VERM = "#F85149"; ROXO = "#BC8CFF"

TIPOS_CLINICA = [
    ("clinica",       "Clinica / Consultorio", "local_hospital_rounded",     AZUL),
    ("laboratorio",   "Laboratorio",           "science_rounded",            AMAR),
    ("fisioterapia",  "Fisioterapia",           "self_improvement_rounded",   VERD),
    ("hospital",      "Hospital",               "emergency_rounded",          VERM),
    ("outro",         "Outro",                  "place_rounded",              MUT),
]

_TIPO_MAP = {t[0]: t for t in TIPOS_CLINICA}


def _icone_tipo(tipo: str):
    return _TIPO_MAP.get(tipo, _TIPO_MAP["outro"])[2]


def _cor_tipo(tipo: str):
    return _TIPO_MAP.get(tipo, _TIPO_MAP["outro"])[3]


def _label_tipo(tipo: str):
    return _TIPO_MAP.get(tipo, _TIPO_MAP["outro"])[1]


def _campo(label, valor="", largura=None, multiline=False, min_lines=1,
           hint=None, keyboard=ft.KeyboardType.TEXT):
    kw = dict(
        label=label, value=valor or "",
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC, size=11),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, multiline=multiline, min_lines=min_lines,
        keyboard_type=keyboard,
    )
    if hint:
        kw["hint_text"] = hint
        kw["hint_style"] = ft.TextStyle(color=MUT, size=11)
    if largura:
        kw["width"] = largura
    else:
        kw["expand"] = True
    return ft.TextField(**kw)


def _label_sec(texto, cor=MUT):
    return ft.Text(texto, size=10, color=cor, weight=ft.FontWeight.W_700)


# ══════════════════════════════════════════════════════════════
# FORMULÁRIO DE CLÍNICA
# ══════════════════════════════════════════════════════════════

def _tela_form_clinica(page, clinica, voltar_fn):
    lay           = Layout(page)
    is_new        = clinica is None
    _modo_edicao  = [is_new]
    _status_banco = ["normal"]
    _handler_ant  = [None]
    titulo        = "Nova Clinica" if is_new else "Clinica"

    def _sync(apos_sync_fn=None):
        ov = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.ProgressRing(color=AZUL, width=36, height=36, stroke_width=3),
                    ft.Container(height=10),
                    ft.Text("Sincronizando com Drive...", size=13, color=TXT,
                            weight=ft.FontWeight.W_600, text_align="center"),
                    ft.Text("Aguarde", size=11, color=SEC, text_align="center"),
                ], tight=True, spacing=2,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD, border_radius=14, padding=ft.padding.all(24), width=240,
            ),
            bgcolor="#DD000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        page.overlay.append(ov)
        try: page.update()
        except Exception: pass
        def _run():
            try:
                from backup.drive_backup import fazer_backup
                fazer_backup(forcar=True)
            except Exception as ex:
                log.warning("[clinicas] sync erro: %s", ex)
            finally:
                _status_banco[0] = "normal"
                if ov in page.overlay: page.overlay.remove(ov)
                try: page.update()
                except Exception: pass
                if apos_sync_fn: apos_sync_fn()
        threading.Thread(target=_run, daemon=True).start()

    def _sair(destino_fn):
        _desregistrar_voltar_hw()
        if _modo_edicao[0]:
            _salvar(None)
        elif _status_banco[0] == "em_edicao":
            _sync(destino_fn)
        else:
            destino_fn()

    def _registrar_voltar_hw():
        _handler_ant[0] = page.on_keyboard_event
        def _on_hw(e):
            if e.key == "Escape": _sair(voltar_fn)
        page.on_keyboard_event = _on_hw

    def _desregistrar_voltar_hw():
        page.on_keyboard_event = _handler_ant[0]

    end_atual = [{}]
    if clinica and clinica.get("endereco_json"):
        try:
            end_atual[0] = _json.loads(clinica["endereco_json"])
        except Exception:
            end_atual[0] = {}

    tipo_sel = [clinica.get("tipo", "clinica") if clinica else "clinica"]

    ro = not _modo_edicao[0]
    f_nome    = _campo("Nome *", clinica["nome"] if clinica else "")
    f_tel     = _campo("Telefone", clinica.get("telefone","") if clinica else "",
                       largura=160, keyboard=ft.KeyboardType.PHONE)
    f_email   = _campo("E-mail", clinica.get("email","") if clinica else "",
                       keyboard=ft.KeyboardType.EMAIL)
    f_website = _campo("Website", clinica.get("website","") if clinica else "")
    f_obs     = _campo("Observacoes", clinica.get("observacoes","") if clinica else "",
                       multiline=True, min_lines=2)
    for _f in [f_nome, f_tel, f_email, f_website, f_obs]:
        _f.read_only = ro
    txt_erro  = ft.Text("", color=VERM, size=12)

    # Endereco resumido
    def _resumo_end() -> str:
        e = end_atual[0]
        if not e:
            return "Nenhum endereco cadastrado"
        partes = []
        if e.get("logradouro"):
            partes.append(f"{e['logradouro']}, {e.get('numero','')}")
        if e.get("bairro"):
            partes.append(e["bairro"])
        if e.get("cidade"):
            partes.append(f"{e['cidade']}/{e.get('estado','')}")
        return " — ".join(p for p in partes if p)

    txt_end = ft.Text(_resumo_end(), size=12, color=SEC)

    # Chips de tipo
    chips_tipo = ft.Row(spacing=6, wrap=True)

    def _rebuild_chips_tipo():
        chips_tipo.controls.clear()
        for chave, label, icone, cor in TIPOS_CLINICA:
            ativo = chave == tipo_sel[0]
            def _on(e, c=chave):
                tipo_sel[0] = c
                _rebuild_chips_tipo()
            chips_tipo.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon(icone, size=13, color=cor if ativo else MUT),
                    ft.Text(label, size=11,
                            color=cor if ativo else MUT,
                            weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.W_400),
                ], spacing=5, tight=True),
                bgcolor=f"{cor}22" if ativo else BD,
                border_radius=20,
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                border=ft.border.all(1, cor if ativo else BD2),
                on_click=_on,
            ))
        try: page.update()
        except Exception: pass

    _rebuild_chips_tipo()

    def _abrir_endereco(e):
        from telas_shared.tela_endereco import criar_tela_endereco

        def _on_salvar(end: dict):
            end_atual[0] = end
            txt_end.value = _resumo_end()
            try: page.update()
            except Exception: pass

        wrapper.controls.clear()
        wrapper.controls.append(
            criar_tela_endereco(
                page=page,
                voltar_fn=lambda: (
                    wrapper.controls.clear(),
                    wrapper.controls.append(_form),
                    page.update(),
                ),
                endereco=end_atual[0],
                on_salvar=_on_salvar,
                titulo="Endereco da Clinica",
            )
        )
        try: page.update()
        except Exception: pass

    btn_end = ft.Container(
        content=ft.Row([
            ft.Icon("edit_location_alt_rounded", size=14, color=AZUL),
            ft.Text("Editar Endereco", size=12, color=AZUL),
        ], spacing=6, tight=True),
        padding=ft.padding.symmetric(horizontal=12, vertical=9),
        border_radius=8, bgcolor=AZUL + "18",
        border=ft.border.all(1, AZUL + "44"), ink=True,
    )
    btn_end.on_click = _abrir_endereco

    def _salvar(e):
        if not f_nome.value.strip():
            txt_erro.value = "Nome e obrigatorio."
            try: page.update()
            except Exception: pass
            return
        end_json = _json.dumps(end_atual[0], ensure_ascii=False) if end_atual[0] else None
        salvar_clinica({
            "id":           clinica["id"] if clinica else None,
            "nome":         f_nome.value.strip(),
            "tipo":         tipo_sel[0],
            "telefone":     f_tel.value.strip() or None,
            "email":        f_email.value.strip() or None,
            "website":      f_website.value.strip() or None,
            "endereco_json": end_json,
            "observacoes":  f_obs.value.strip() or None,
        })
        _status_banco[0] = "em_edicao"
        _sync(voltar_fn)

    def _ativar_edicao(e=None):
        _modo_edicao[0] = True
        for _f in [f_nome, f_tel, f_email, f_website, f_obs]:
            _f.read_only = False
        btn_end.visible    = True
        btn_salvar_hdr.visible = True
        btn_editar.visible = False
        try: page.update()
        except Exception: pass

    btn_salvar_hdr = ft.Container(
        content=ft.Row([
            ft.Icon("save_rounded", size=15, color=BG),
            ft.Text("Salvar", size=13, color=BG, weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        bgcolor=AZUL, border_radius=8, ink=True,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        visible=is_new,
    )
    btn_salvar_hdr.on_click = _salvar

    btn_editar = ft.Container(
        content=ft.Row([
            ft.Icon("edit_rounded", size=15, color=AZUL),
            ft.Text("Editar", size=13, color=AZUL),
        ], spacing=5, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8, bgcolor=ft.Colors.with_opacity(0.12, AZUL), ink=True,
        visible=not is_new,
    )
    btn_editar.on_click = _ativar_edicao

    btn_end.visible = _modo_edicao[0]

    cabecalho = lay.criar_cabecalho(
        titulo, lambda e=None: _sair(voltar_fn),
        icone_titulo="local_hospital_rounded",
        cor_titulo=AZUL,
        acoes=[btn_editar, btn_salvar_hdr],
    )

    area = ft.Column([
        ft.Container(height=lay.spacer_topo, bgcolor=BG),
        cabecalho,
        ft.Container(
            content=ft.Column([
                _label_sec("TIPO"),
                chips_tipo,
                ft.Container(height=4),
                _label_sec("NOME"),
                f_nome,
                ft.Container(height=4),
                _label_sec("CONTATO"),
                ft.Row([f_tel, ft.Container(width=8), f_email], spacing=0),
                ft.Container(height=4),
                _label_sec("WEBSITE"),
                f_website,
                ft.Container(height=4),
                _label_sec("ENDERECO"),
                ft.Row([txt_end, ft.Container(expand=True), btn_end],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(height=4),
                _label_sec("OBSERVACOES"),
                f_obs,
                ft.Container(height=8),
                txt_erro,
                ft.Container(height=20),
            ], spacing=8, scroll=ft.ScrollMode.AUTO),
            padding=ft.padding.all(16),
            expand=True,
        ),
    ], expand=True, spacing=0)

    _form = ft.Container(bgcolor=BG, expand=True, content=area)
    wrapper = ft.Column(expand=True)
    wrapper.controls.append(_form)
    _registrar_voltar_hw()
    return wrapper


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL
# ══════════════════════════════════════════════════════════════

def criar_tela_clinicas(page: ft.Page, voltar_fn):
    lay      = Layout(page)
    _montado = [False]
    area     = ft.Column(spacing=8, expand=True, scroll=ft.ScrollMode.AUTO)
    wrapper  = ft.Column(expand=True)

    def _rebuild():
        area.controls.clear()
        clinicas = listar_clinicas(so_ativas=False)
        if not clinicas:
            area.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("local_hospital_rounded", size=40, color=MUT),
                    ft.Text("Nenhuma clinica cadastrada.", size=13, color=SEC),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=40, alignment=ft.alignment.Alignment(0, 0),
            ))
        for cl in clinicas:
            _card(cl)
        if _montado[0]:
            try: page.update()
            except Exception: pass

    def _card(cl: dict):
        ativo   = cl.get("ativo", 1)
        cor     = _cor_tipo(cl["tipo"])
        icone   = _icone_tipo(cl["tipo"])
        label_t = _label_tipo(cl["tipo"])

        end_txt = ""
        if cl.get("endereco_json"):
            try:
                e = _json.loads(cl["endereco_json"])
                partes = []
                if e.get("logradouro"):
                    partes.append(f"{e['logradouro']}, {e.get('numero','')}")
                if e.get("cidade"):
                    partes.append(f"{e['cidade']}/{e.get('estado','')}")
                end_txt = " — ".join(p for p in partes if p)
            except Exception:
                pass

        def _editar(e, c=cl):
            def _voltar():
                _rebuild()
                _mostrar_lista()
            wrapper.controls.clear()
            wrapper.controls.append(_tela_form_clinica(page, c, _voltar))
            try: page.update()
            except Exception: pass

        def _excluir(e, cid=cl["id"], nome=cl["nome"]):
            excluir_clinica(cid)
            _rebuild()

        acoes_row = ft.Row([
            ft.Container(
                content=ft.Row([
                    ft.Icon("edit_rounded", size=13, color=MUT),
                    ft.Text("Editar", size=11, color=MUT),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                ink=True, on_click=_editar,
            ),
        ] + ([
            ft.Container(
                content=ft.Row([
                    ft.Icon("delete_outline_rounded", size=13, color=VERM),
                    ft.Text("Remover", size=11, color=VERM),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                ink=True, on_click=_excluir,
            ),
        ] if ativo else []), spacing=4)

        area.controls.append(ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(icone, size=20, color=cor),
                        bgcolor=f"{cor}18", border_radius=10,
                        width=40, height=40,
                        alignment=ft.alignment.Alignment(0, 0),
                    ),
                    ft.Column([
                        ft.Text(cl["nome"], size=13, color=TXT if ativo else MUT,
                                weight=ft.FontWeight.W_600),
                        ft.Text(label_t, size=10, color=cor),
                    ], spacing=1, expand=True),
                    ft.Container(
                        content=ft.Text("Inativo" if not ativo else "",
                                        size=9, color=MUT),
                        visible=not bool(ativo),
                    ),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([
                    ft.Icon("location_on_outlined_rounded", size=12, color=MUT),
                    ft.Text(end_txt or "Sem endereco", size=11, color=SEC, expand=True),
                ], spacing=6) if end_txt or True else ft.Container(),
                ft.Row([
                    ft.Icon("phone_rounded", size=11, color=MUT),
                    ft.Text(cl.get("telefone") or "—", size=11, color=SEC),
                    ft.Container(width=12),
                    ft.Icon("email_rounded", size=11, color=MUT),
                    ft.Text(cl.get("email") or "—", size=11, color=SEC, expand=True),
                ], spacing=4),
                acoes_row,
            ], spacing=6),
            bgcolor=CARD, border_radius=10,
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            border=ft.Border(
                left=ft.BorderSide(2, cor if ativo else MUT),
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                right=ft.BorderSide(1, BD),
            ),
            opacity=1.0 if ativo else 0.55,
        ))

    def _mostrar_lista():
        btn_nova = ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=16, color=BG),
                ft.Text("+ Nova", size=13, color=BG, weight=ft.FontWeight.W_600),
            ], spacing=6, tight=True),
            bgcolor=AZUL, border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            ink=True,
        )

        def _nova(e):
            def _voltar():
                _rebuild()
                _mostrar_lista()
            wrapper.controls.clear()
            wrapper.controls.append(_tela_form_clinica(page, None, _voltar))
            try: page.update()
            except Exception: pass

        btn_nova.on_click = _nova

        cabecalho = lay.criar_cabecalho(
            "Clinicas", voltar_fn,
            icone_titulo="local_hospital_rounded",
            cor_titulo=AZUL,
            acoes=[btn_nova],
        )
        corpo = ft.Column([
            ft.Container(height=lay.spacer_topo, bgcolor=BG),
            cabecalho,
            ft.Container(content=area, padding=ft.padding.all(16), expand=True),
        ], expand=True, spacing=0)

        wrapper.controls.clear()
        wrapper.controls.append(ft.Container(bgcolor=BG, expand=True, content=corpo))
        try: page.update()
        except Exception: pass

    _rebuild()
    _mostrar_lista()
    _montado[0] = True
    return wrapper
