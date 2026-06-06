# -*- coding: utf-8 -*-
"""
tela_fornecedores.py — Koios Prontuário
Cadastro de fornecedores / farmácias. Padrão visual Koios.
"""
import logging
import flet as ft
from shared.layout import Layout
from dados.model_prontuario import listar_farmacias, salvar_farmacia

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; AMAR = "#D29922"; VERM = "#DA3633"
ROXO = "#BC8CFF"


def _campo(label, valor="", largura=None, multiline=False, min_lines=1,
           hint=None, read_only=False, keyboard=ft.KeyboardType.TEXT):
    kw = dict(
        label=label, value=valor or "",
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, multiline=multiline, min_lines=min_lines,
        read_only=read_only, keyboard_type=keyboard,
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


def criar_tela_fornecedores(page: ft.Page, voltar_fn, modo_aba: bool = False):
    lay     = Layout(page)
    wrapper = ft.Column(expand=True, spacing=0)

    # ── Lista ──────────────────────────────────────────────────────────
    def _mostrar_lista():
        fornecedores = listar_farmacias(so_ativas=False)
        lista_col = ft.Column(spacing=8)

        btn_novo = ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=16, color=BG),
                ft.Text("Novo", size=13, color=BG, weight=ft.FontWeight.W_600),
            ], spacing=6, tight=True),
            bgcolor=AZUL, border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
        )
        btn_novo.on_click = lambda e: _mostrar_ficha(None)

        cabecalho = lay.criar_cabecalho(
            "Fornecedores", voltar_fn,
            icone_titulo="storefront_rounded",
            cor_titulo=AZUL,
            acoes=[btn_novo],
        )

        if not fornecedores:
            lista_col.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("storefront_rounded", size=40, color=MUT),
                    ft.Text("Nenhum fornecedor cadastrado.", size=13, color=SEC),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=ft.padding.symmetric(vertical=40),
                alignment=ft.alignment.center,
            ))
        else:
            for f in fornecedores:
                canais = []
                if f.get("whatsapp"): canais.append("WhatsApp")
                if f.get("site"):     canais.append("Site")
                if f.get("app"):      canais.append("App")
                if f.get("delivery"): canais.append("Delivery")
                ativo = bool(f.get("ativo", 1))
                cor_borda = AZUL if f.get("preferida") else (BD if ativo else MUT)

                card = ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Icon("storefront_rounded", size=20,
                                            color=AZUL if f.get("preferida") else SEC),
                            bgcolor=ft.Colors.with_opacity(0.12, AZUL if f.get("preferida") else SEC),
                            border_radius=10, width=40, height=40,
                            alignment=ft.alignment.center,
                        ),
                        ft.Column([
                            ft.Row([
                                ft.Text(f.get("nome_exibicao") or f["nome"],
                                        size=13, color=TXT if ativo else MUT,
                                        weight=ft.FontWeight.W_600, expand=True),
                                *([ ft.Container(
                                    content=ft.Text("Preferida", size=9, color=AMAR,
                                                    weight=ft.FontWeight.W_600),
                                    bgcolor=ft.Colors.with_opacity(0.12, AMAR),
                                    border_radius=4,
                                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                ) ] if f.get("preferida") else []),
                                *([ ft.Container(
                                    content=ft.Text("Inativa", size=9, color=MUT,
                                                    weight=ft.FontWeight.W_600),
                                    bgcolor=ft.Colors.with_opacity(0.10, MUT),
                                    border_radius=4,
                                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                ) ] if not ativo else []),
                            ], spacing=6),
                            # Razão social como secundário
                            *([ ft.Text(f.get("razao_social") or "", size=10,
                                        color=MUT, max_lines=1)
                              ] if f.get("razao_social") and f.get("razao_social") != f.get("nome") else []),
                            ft.Text(f.get("endereco") or "", size=10, color=SEC, max_lines=1),
                            ft.Text(" · ".join(canais), size=10, color=MUT) if canais else ft.Container(),
                        ], spacing=2, expand=True, tight=True),
                        ft.Icon("chevron_right_rounded", size=16, color=MUT),
                    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD, border_radius=10, ink=True,
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    border=ft.Border(
                        left=ft.BorderSide(2, cor_borda),
                        top=ft.BorderSide(1, BD),
                        bottom=ft.BorderSide(1, BD),
                        right=ft.BorderSide(1, BD),
                    ),
                    on_click=lambda e, farm=f: _mostrar_ficha(farm),
                )
                lista_col.controls.append(card)

        if modo_aba:
            corpo = ft.Column([
                ft.Row([
                    ft.Text("FORNECEDORES", size=10, color=MUT,
                            weight=ft.FontWeight.W_700, expand=True),
                    btn_novo,
                ], spacing=8),
                ft.Column([lista_col], scroll=ft.ScrollMode.AUTO, expand=True),
            ], expand=True, spacing=8)
            wrapper.controls.clear()
            wrapper.controls.append(ft.Container(bgcolor=BG, expand=True, content=corpo))
        else:
            corpo = ft.Column([
                ft.Container(height=lay.spacer_topo, bgcolor=BG),
                cabecalho,
                ft.Container(
                    content=ft.Column([lista_col], scroll=ft.ScrollMode.AUTO),
                    padding=ft.padding.all(16), expand=True,
                ),
            ], expand=True, spacing=0)
            wrapper.controls.clear()
            wrapper.controls.append(ft.Container(bgcolor=BG, expand=True, content=corpo))
        try: page.update()
        except Exception: pass

    # ── Ficha ──────────────────────────────────────────────────────────
    def _mostrar_ficha(farm):
        is_novo      = farm is None
        _modo_ed     = [is_novo]
        _status_banco = ["normal"]  # "normal" | "em_edicao"
        _end_atual   = [{}]

        if farm and farm.get("endereco"):
            _end_atual[0] = {"endereco_fmt": farm["endereco"]}

        f_nome = _campo("Nome fantasia *", farm.get("nome","") if farm else "",
                        read_only=not is_novo)
        f_razao = _campo("Razão social", farm.get("razao_social","") if farm else "",
                         read_only=not is_novo)
        f_tel  = _campo("Telefone", farm.get("telefone","") if farm else "",
                        largura=160, read_only=not is_novo)
        f_wpp  = _campo("WhatsApp", farm.get("whatsapp","") if farm else "",
                        largura=160, hint="5527999998888", read_only=not is_novo)
        f_site = _campo("Site", farm.get("site","") if farm else "", read_only=not is_novo)
        f_app  = _campo("App", farm.get("app","") if farm else "", read_only=not is_novo)
        f_obs  = _campo("Observações", farm.get("observacoes","") if farm else "",
                        multiline=True, min_lines=2, read_only=not is_novo)

        sw_del  = ft.Switch(label="Delivery",  value=bool(farm.get("delivery",0)) if farm else False,
                            active_color=VERD, label_style=ft.TextStyle(color=SEC, size=12),
                            disabled=not is_novo)
        sw_pref = ft.Switch(label="Preferida", value=bool(farm.get("preferida",0)) if farm else False,
                            active_color=AMAR, label_style=ft.TextStyle(color=SEC, size=12),
                            disabled=not is_novo)
        sw_ativ = ft.Switch(label="Ativo",     value=bool(farm.get("ativo",1)) if farm else True,
                            active_color=AZUL, label_style=ft.TextStyle(color=SEC, size=12),
                            disabled=not is_novo)

        txt_end = ft.Text(
            _end_atual[0].get("endereco_fmt") or "Endereço não informado",
            size=12, color=SEC if _end_atual[0] else MUT,
        )

        # Botão endereço
        btn_end = ft.Container(
            content=ft.Row([
                ft.Icon("edit_location_alt_rounded", size=13, color=AZUL),
                ft.Text("Editar Endereço", size=12, color=AZUL),
            ], spacing=6, tight=True),
            bgcolor=ft.Colors.with_opacity(0.10, AZUL),
            border=ft.border.all(1, ft.Colors.with_opacity(0.3, AZUL)),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=10, vertical=7),
            visible=_modo_ed[0],
        )

        def _abrir_endereco(e):
            from telas_shared.tela_endereco import criar_tela_endereco
            def _on_salvar(end: dict):
                _end_atual[0] = end
                txt_end.value = end.get("endereco_fmt") or ""
                txt_end.color = SEC
                try: page.update()
                except Exception: pass

            wrapper.controls.clear()
            wrapper.controls.append(criar_tela_endereco(
                page=page,
                voltar_fn=lambda: _mostrar_ficha(farm),
                endereco=_end_atual[0],
                on_salvar=_on_salvar,
                titulo="Endereço do Fornecedor",
            ))
            try: page.update()
            except Exception: pass

        btn_end.on_click = _abrir_endereco

        txt_erro = ft.Text("", color=VERM, size=12)

        def _fazer_sync(apos_fn):
            fechar = lay.loading("Sincronizando com Drive...")
            import threading as _thr
            def _run():
                try:
                    from backup.drive_backup import fazer_backup
                    fazer_backup(forcar=True)
                except Exception as ex:
                    log.warning("[FORNEC] sync: %s", ex)
                finally:
                    fechar()
                    apos_fn()
            _thr.Thread(target=_run, daemon=True).start()

        def _salvar_dados():
            if not f_nome.value.strip() and not f_razao.value.strip():
                txt_erro.value = "Nome fantasia ou razão social é obrigatório."
                try: page.update()
                except Exception: pass
                return False
            salvar_farmacia({
                "id":           farm["id"] if farm else None,
                "nome":         f_nome.value.strip(),
                "razao_social": f_razao.value.strip() or None,
                "endereco":     _end_atual[0].get("endereco_fmt") or None,
                "telefone":     f_tel.value.strip() or None,
                "whatsapp":     f_wpp.value.strip() or None,
                "site":         f_site.value.strip() or None,
                "app":          f_app.value.strip() or None,
                "delivery":     1 if sw_del.value else 0,
                "preferida":    1 if sw_pref.value else 0,
                "ativo":        1 if sw_ativ.value else 0,
                "observacoes":  f_obs.value.strip() or None,
            })
            _status_banco[0] = "em_edicao"
            return True

        def _salvar(e):
            if _salvar_dados():
                _fazer_sync(_mostrar_lista)

        def _sair(destino_fn):
            if _modo_ed[0]:
                # Em modo edição — salva automaticamente ao sair
                if _salvar_dados():
                    _fazer_sync(destino_fn)
                else:
                    destino_fn()
            elif _status_banco[0] == "em_edicao":
                _fazer_sync(destino_fn)
            else:
                destino_fn()

        def _ativar_edicao(e=None):
            _modo_ed[0] = True
            for f_ in [f_nome, f_razao, f_tel, f_wpp, f_site, f_app, f_obs]:
                f_.read_only = False
            sw_del.disabled = False
            sw_pref.disabled = False
            sw_ativ.disabled = False
            btn_end.visible = True
            btn_salvar.visible = True
            btn_editar.visible = False
            try: page.update()
            except Exception: pass

        btn_salvar = ft.Container(
            content=ft.Row([
                ft.Icon("save_rounded", size=15, color=BG),
                ft.Text("Salvar", size=13, color=BG, weight=ft.FontWeight.W_600),
            ], spacing=6, tight=True),
            bgcolor=AZUL, border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            visible=is_novo,
        )
        btn_salvar.on_click = _salvar

        btn_editar = ft.Container(
            content=ft.Row([
                ft.Icon("edit_rounded", size=15, color=AZUL),
                ft.Text("Editar", size=13, color=AZUL),
            ], spacing=5, tight=True),
            bgcolor=ft.Colors.with_opacity(0.12, AZUL),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            visible=not is_novo,
        )
        btn_editar.on_click = _ativar_edicao

        titulo = "Novo Fornecedor" if is_novo else "Fornecedor"
        cabecalho = lay.criar_cabecalho(
            titulo, lambda e=None: _sair(_mostrar_lista),
            icone_titulo="storefront_rounded",
            cor_titulo=AZUL,
            acoes=[btn_editar, btn_salvar],
        )

        conteudo = ft.Column([
            _label_sec("IDENTIFICAÇÃO"),
            f_nome,
            f_razao,
            _label_sec("ENDEREÇO"),
            txt_end,
            btn_end,
            _label_sec("CONTATO"),
            ft.Row([f_tel, f_wpp], spacing=8),
            f_site,
            f_app,
            _label_sec("CONFIGURAÇÕES"),
            ft.Row([sw_del, sw_pref, sw_ativ], spacing=16),
            _label_sec("OBSERVAÇÕES"),
            f_obs,
            txt_erro,
            ft.Container(height=20),
        ], spacing=8, scroll=ft.ScrollMode.AUTO)

        spacer = 0 if modo_aba else lay.spacer_topo
        corpo = ft.Column([
            ft.Container(height=spacer, bgcolor=BG),
            cabecalho,
            ft.Container(content=conteudo, padding=ft.padding.all(16), expand=True),
        ], expand=True, spacing=0)

        wrapper.controls.clear()
        wrapper.controls.append(ft.Container(bgcolor=BG, expand=True, content=corpo))
        try: page.update()
        except Exception: pass

    _mostrar_lista()
    return wrapper


def abrir_ficha_fornecedor(page: ft.Page, farmacia_id: int, voltar_fn):
    """
    Retorna a tela de fornecedores já posicionada na ficha do fornecedor indicado.
    Ao voltar da ficha chama voltar_fn (retorna para o contexto do chamador).
    """
    from dados.model_prontuario import listar_farmacias
    lay     = Layout(page)
    wrapper = ft.Column(expand=True, spacing=0)
    farm    = next((f for f in listar_farmacias(so_ativas=False)
                    if f["id"] == farmacia_id), None)

    # Reutiliza criar_tela_fornecedores mas substituindo o voltar_lista pelo voltar_fn
    # Cria a tela normalmente e logo após navega para a ficha
    tela_base = criar_tela_fornecedores(page, voltar_fn)

    if farm:
        # A tela já foi criada com _mostrar_lista — precisamos chamar _mostrar_ficha
        # Fazemos isso criando uma nova tela que começa direto na ficha
        # usando o mesmo padrão interno mas com farm já definido
        _tela_direta = _criar_ficha_direta(page, farm, voltar_fn)
        return _tela_direta

    return tela_base


def _criar_ficha_direta(page: ft.Page, farm: dict, voltar_fn):
    """Cria a tela posicionada direto na ficha do fornecedor — sem passar pela lista."""
    lay     = Layout(page)
    wrapper = ft.Column(expand=True, spacing=0)

    def _voltar():
        voltar_fn()

    # Instancia a tela completa e força navegação para a ficha
    tela = criar_tela_fornecedores(page, _voltar)
    # Hack: a tela começa na lista (_mostrar_lista já foi chamado).
    # Precisamos limpar o wrapper e colocar a ficha.
    # A forma correta: recriar só a ficha usando as funções internas.
    # Como _mostrar_ficha é closure, criamos a ficha diretamente aqui:
    is_novo   = False
    _modo_ed  = [False]
    _end_atual = [{"endereco_fmt": farm.get("endereco") or ""}]

    def _campo_f(label, valor="", largura=None, multiline=False,
                 min_lines=1, hint=None, read_only=True):
        kw = dict(
            label=label, value=valor or "",
            bgcolor="#161B22", border_color="#30363D",
            focused_border_color="#58A6FF",
            label_style=ft.TextStyle(color="#8B949E"),
            text_style=ft.TextStyle(color="#E6EDF3"),
            border_radius=8, multiline=multiline,
            min_lines=min_lines, read_only=read_only,
        )
        if hint:
            kw["hint_text"] = hint
            kw["hint_style"] = ft.TextStyle(color="#484F58", size=11)
        if largura:
            kw["width"] = largura
        else:
            kw["expand"] = True
        return ft.TextField(**kw)

    from dados.model_prontuario import salvar_farmacia

    f_nome  = _campo_f("Nome fantasia", farm.get("nome",""))
    f_razao = _campo_f("Razão social",  farm.get("razao_social",""))
    f_tel   = _campo_f("Telefone",      farm.get("telefone",""), largura=160)
    f_wpp   = _campo_f("WhatsApp",      farm.get("whatsapp",""), largura=160)
    f_site  = _campo_f("Site",          farm.get("site",""))
    f_app   = _campo_f("App",           farm.get("app",""))
    f_obs   = _campo_f("Observações",   farm.get("observacoes",""),
                        multiline=True, min_lines=2)

    txt_end = ft.Text(
        _end_atual[0].get("endereco_fmt") or "Endereço não informado",
        size=12, color="#8B949E" if _end_atual[0].get("endereco_fmt") else "#484F58",
    )

    sw_del  = ft.Switch(label="Delivery",  value=bool(farm.get("delivery",0)),
                        active_color="#3FB950",
                        label_style=ft.TextStyle(color="#8B949E", size=12),
                        disabled=True)
    sw_pref = ft.Switch(label="Preferida", value=bool(farm.get("preferida",0)),
                        active_color="#D29922",
                        label_style=ft.TextStyle(color="#8B949E", size=12),
                        disabled=True)
    sw_ativ = ft.Switch(label="Ativo",     value=bool(farm.get("ativo",1)),
                        active_color="#58A6FF",
                        label_style=ft.TextStyle(color="#8B949E", size=12),
                        disabled=True)

    _modo_ed_d    = [False]
    _status_banco_d = ["normal"]

    txt_erro = ft.Text("", color="#DA3633", size=12)
    btn_salvar = ft.Container(
        content=ft.Row([
            ft.Icon("save_rounded", size=15, color="#0D1117"),
            ft.Text("Salvar", size=13, color="#0D1117", weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        bgcolor="#58A6FF", border_radius=8, ink=True,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        visible=False,
    )

    def _fazer_sync_d(apos_fn):
        fechar = lay.loading("Sincronizando com Drive...")
        import threading as _thr
        def _run():
            try:
                from backup.drive_backup import fazer_backup
                fazer_backup(forcar=True)
            except Exception as ex:
                log.warning("[FORNEC] backup: %s", ex)
            finally:
                fechar()
                apos_fn()
        _thr.Thread(target=_run, daemon=True).start()

    def _salvar_dados_d():
        if not f_nome.value.strip() and not f_razao.value.strip():
            txt_erro.value = "Nome ou razão social é obrigatório."
            try: page.update()
            except Exception: pass
            return False
        salvar_farmacia({
            "id":           farm["id"],
            "nome":         f_nome.value.strip(),
            "razao_social": f_razao.value.strip() or None,
            "endereco":     _end_atual[0].get("endereco_fmt") or None,
            "telefone":     f_tel.value.strip() or None,
            "whatsapp":     f_wpp.value.strip() or None,
            "site":         f_site.value.strip() or None,
            "app":          f_app.value.strip() or None,
            "delivery":     1 if sw_del.value else 0,
            "preferida":    1 if sw_pref.value else 0,
            "ativo":        1 if sw_ativ.value else 0,
            "observacoes":  f_obs.value.strip() or None,
        })
        _status_banco_d[0] = "em_edicao"
        return True

    def _salvar(e):
        if _salvar_dados_d():
            _fazer_sync_d(_voltar)

    def _sair_d():
        if _modo_ed_d[0]:
            if _salvar_dados_d():
                _fazer_sync_d(_voltar)
            else:
                _voltar()
        elif _status_banco_d[0] == "em_edicao":
            _fazer_sync_d(_voltar)
        else:
            _voltar()

    btn_salvar.on_click = _salvar

    btn_editar = ft.Container(
        content=ft.Row([
            ft.Icon("edit_rounded", size=15, color="#58A6FF"),
            ft.Text("Editar", size=13, color="#58A6FF"),
        ], spacing=5, tight=True),
        bgcolor=ft.Colors.with_opacity(0.12, "#58A6FF"),
        border_radius=8, ink=True,
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
    )

    def _ativar_edicao(e=None):
        _modo_ed_d[0] = True
        for f_ in [f_nome, f_razao, f_tel, f_wpp, f_site, f_app, f_obs]:
            f_.read_only = False
        sw_del.disabled = False; sw_pref.disabled = False; sw_ativ.disabled = False
        btn_salvar.visible = True; btn_editar.visible = False
        try: page.update()
        except Exception: pass

    btn_editar.on_click = _ativar_edicao

    cab = lay.criar_cabecalho(
        "Fornecedor", lambda e=None: _sair_d(),
        icone_titulo="storefront_rounded", cor_titulo="#58A6FF",
        acoes=[btn_editar, btn_salvar],
    )
    conteudo = ft.Column([
        ft.Text("IDENTIFICAÇÃO", size=10, color="#484F58", weight=ft.FontWeight.W_700),
        f_nome, f_razao,
        ft.Text("ENDEREÇO", size=10, color="#484F58", weight=ft.FontWeight.W_700),
        txt_end,
        ft.Text("CONTATO", size=10, color="#484F58", weight=ft.FontWeight.W_700),
        ft.Row([f_tel, f_wpp], spacing=8),
        f_site, f_app,
        ft.Text("CONFIGURAÇÕES", size=10, color="#484F58", weight=ft.FontWeight.W_700),
        ft.Row([sw_del, sw_pref, sw_ativ], spacing=16),
        ft.Text("OBSERVAÇÕES", size=10, color="#484F58", weight=ft.FontWeight.W_700),
        f_obs,
        txt_erro,
        ft.Container(height=20),
    ], spacing=8, scroll=ft.ScrollMode.AUTO)

    return ft.Container(
        bgcolor="#0D1117", expand=True,
        content=ft.Column([
            ft.Container(height=lay.spacer_topo, bgcolor="#0D1117"),
            cab,
            ft.Container(content=conteudo, padding=ft.padding.all(16), expand=True),
        ], expand=True, spacing=0),
    )
