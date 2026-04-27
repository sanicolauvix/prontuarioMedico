"""
tela_dieta.py — Koios Prontuário
Rotina diária (alimentação, medicamentos, suplementos) + Diário de Saúde.
Padrão visual: idêntico a tela_exames.py (header + barra de abas + área de conteúdo)
"""
import logging
import threading
from datetime import date, datetime
import flet as ft
from ..dados.model_prontuario import (
    listar_rotina, salvar_rotina_item, excluir_rotina_item,
    listar_diario, salvar_diario_entrada, excluir_diario_entrada,
    tendencias_diario, tags_frequentes,
)

logger = logging.getLogger(__name__)

# ── Paleta ────────────────────────────────────────────────────
BG   = "#0D1117";  CARD = "#161B22";  BD  = "#21262D";  BD2 = "#30363D"
TXT  = "#E6EDF3";  SEC  = "#8B949E";  MUT = "#484F58"
AZUL = "#58A6FF";  VERD = "#3FB950";  LAR = "#F0883E"
AMAR = "#D29922";  VERM = "#DA3633";  ROXO = "#BC8CFF"
CORAL = "#FF7B72"

# Tipos de item de rotina
TIPOS = {
    "refeicao":    (ft.Icons.RESTAURANT,      "Refeição",     VERD),
    "medicamento": (ft.Icons.MEDICATION,       "Medicamento",  AZUL),
    "suplemento":  (ft.Icons.HEALTH_AND_SAFETY,"Suplemento",   ROXO),
    "atividade":   (ft.Icons.FITNESS_CENTER,   "Atividade",    LAR),
    "outro":       (ft.Icons.CIRCLE,           "Outro",        MUT),
}

# Emojis de humor/energia
HUMOR_EMOJI  = ["", "😩", "😕", "😐", "😊", "😄"]
ENERGIA_EMOJI = ["", "🪫", "😴", "⚡", "💪", "🔥"]


# ══════════════════════════════════════════════════════════════
# HELPERS VISUAIS
# ══════════════════════════════════════════════════════════════

def _campo(label, valor="", multiline=False, min_lines=1, hint=None,
           keyboard=ft.KeyboardType.TEXT, largura=None):
    kw = dict(
        label=label, value=valor or "",
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC),
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

def _badge(texto, cor):
    return ft.Container(
        content=ft.Text(texto, size=10, color=cor, weight=ft.FontWeight.W_600),
        bgcolor=f"{cor}18", border_radius=10,
        padding=ft.padding.symmetric(horizontal=8, vertical=3))

def _card_border(cor_esq, conteudo, opa=1.0):
    return ft.Container(
        content=conteudo, bgcolor=CARD, border_radius=10, opacity=opa,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border=ft.Border(
            left=ft.BorderSide(3, cor_esq),
            top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
            right=ft.BorderSide(1, BD)))

def _label_sec(texto, cor=MUT):
    return ft.Text(texto, size=10, color=cor, weight=ft.FontWeight.W_700)


# ══════════════════════════════════════════════════════════════
# ABA 1 — ROTINA DIÁRIA
# ══════════════════════════════════════════════════════════════

def _conteudo_rotina(page, wrapper):
    lista = ft.Column(spacing=8)

    def _carregar():
        lista.controls.clear()
        itens = listar_rotina(so_ativos=False)

        if not itens:
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.SCHEDULE, size=48, color=MUT),
                    ft.Text("Nenhum item na rotina.", color=SEC, size=13),
                    ft.Text("Adicione refeições, medicamentos e suplementos.",
                            color=MUT, size=11),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=40))
            try: page.update()
            except Exception: pass
            return

        # Agrupar por horário
        por_horario: dict = {}
        sem_hora = []
        for it in itens:
            h = it.get("horario") or ""
            if h:
                por_horario.setdefault(h, []).append(it)
            else:
                sem_hora.append(it)

        for h in sorted(por_horario.keys()):
            lista.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.ACCESS_TIME, size=13, color=AMAR),
                    ft.Text(h, size=13, color=AMAR, weight=ft.FontWeight.W_700),
                ], spacing=6),
                padding=ft.padding.only(top=10, left=4, bottom=2)))
            for it in por_horario[h]:
                lista.controls.append(_card_item(it))

        if sem_hora:
            lista.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.SCHEDULE, size=13, color=MUT),
                    ft.Text("Sem horário fixo", size=13, color=MUT,
                            weight=ft.FontWeight.W_700),
                ], spacing=6),
                padding=ft.padding.only(top=10, left=4, bottom=2)))
            for it in sem_hora:
                lista.controls.append(_card_item(it))

        try: page.update()
        except Exception: pass

    def _card_item(it):
        icone_tipo, label_tipo, cor_tipo = TIPOS.get(
            it.get("tipo","outro"), TIPOS["outro"])
        ativo = it.get("ativo", 1)

        def _editar(e, item=it):
            _abrir_ficha(item)

        def _toggle_ativo(e, item=it):
            item["ativo"] = 0 if item.get("ativo", 1) else 1
            salvar_rotina_item(item)
            _carregar()

        dias = it.get("dias_semana") or ""
        if dias:
            mapa = {"1":"Seg","2":"Ter","3":"Qua","4":"Qui","5":"Sex","6":"Sab","7":"Dom"}
            dias_txt = " · ".join(mapa.get(d.strip(), d.strip()) for d in dias.split(",") if d.strip())
        else:
            dias_txt = "Todo dia"

        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icone_tipo, size=20, color=cor_tipo),
                    bgcolor=f"{cor_tipo}1A", border_radius=8,
                    width=40, height=40,
                    alignment=ft.alignment.Alignment(0, 0)),
                ft.Column([
                    ft.Row([
                        ft.Text(it["nome"], size=13, color=TXT,
                                weight=ft.FontWeight.W_600),
                        _badge(label_tipo, cor_tipo),
                    ], spacing=6),
                    ft.Row([
                        ft.Text(it.get("quantidade") or "", size=11, color=SEC),
                        ft.Text("·" if it.get("quantidade") and it.get("descricao") else "",
                                size=11, color=MUT),
                        ft.Text(it.get("descricao") or "", size=11, color=SEC),
                    ], spacing=4),
                    ft.Text(dias_txt, size=10, color=MUT),
                ], spacing=2, expand=True),
                ft.Column([
                    ft.IconButton(
                        ft.Icons.EDIT_ROUNDED, icon_color=AZUL, icon_size=16,
                        on_click=_editar,
                        style=ft.ButtonStyle(
                            padding=ft.padding.all(4),
                            shape=ft.RoundedRectangleBorder(radius=6))),
                    ft.IconButton(
                        ft.Icons.VISIBILITY_OFF if ativo else ft.Icons.VISIBILITY,
                        icon_color=MUT, icon_size=16,
                        on_click=_toggle_ativo,
                        style=ft.ButtonStyle(
                            padding=ft.padding.all(4),
                            shape=ft.RoundedRectangleBorder(radius=6))),
                ], spacing=0),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=CARD, border_radius=10,
            opacity=1.0 if ativo else 0.4,
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border=ft.Border(
                left=ft.BorderSide(3, cor_tipo if ativo else MUT),
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                right=ft.BorderSide(1, BD)),
            on_click=_editar, ink=True)

    def _abrir_ficha(item=None):
        is_novo = item is None

        f_nome = _campo("Nome *", item["nome"] if item else "")
        f_qtd  = _campo("Quantidade", item.get("quantidade","") if item else "",
                         hint="1 comprimido, 200g…", largura=160)
        f_hora = _campo("Horário", item.get("horario","") if item else "",
                         hint="08:00", largura=100,
                         keyboard=ft.KeyboardType.DATETIME)
        f_dias = _campo("Dias (1=Seg…7=Dom)",
                         item.get("dias_semana","") if item else "",
                         hint="1,2,3,4,5 — vazio = todo dia", largura=200)
        f_desc = _campo("Descrição / observação",
                         item.get("descricao","") if item else "",
                         multiline=True, min_lines=2)

        tipo_sel = [item.get("tipo","refeicao") if item else "refeicao"]

        chips_tipo = ft.Row(wrap=True, spacing=6)

        def _rebuild_chips():
            chips_tipo.controls.clear()
            for t_key, (t_ico, t_lab, t_cor) in TIPOS.items():
                sel = t_key == tipo_sel[0]
                def _sel_tipo(e, k=t_key):
                    tipo_sel[0] = k
                    _rebuild_chips()
                    try: page.update()
                    except Exception: pass
                chips_tipo.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Icon(t_ico, size=12, color=t_cor if sel else MUT),
                        ft.Text(t_lab, size=11,
                                color=t_cor if sel else MUT,
                                weight=ft.FontWeight.W_600 if sel else ft.FontWeight.W_400),
                    ], spacing=4, tight=True),
                    bgcolor=f"{t_cor}22" if sel else BD,
                    border_radius=20,
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    border=ft.Border(
                        top=ft.BorderSide(1, t_cor if sel else BD2),
                        bottom=ft.BorderSide(1, t_cor if sel else BD2),
                        left=ft.BorderSide(1, t_cor if sel else BD2),
                        right=ft.BorderSide(1, t_cor if sel else BD2)),
                    on_click=_sel_tipo, ink=True))
        _rebuild_chips()

        sw_ativo = ft.Switch(label="Ativo",
            value=bool(item.get("ativo",1)) if item else True,
            active_color=VERD,
            label_text_style=ft.TextStyle(color=SEC, size=13))

        txt_erro = ft.Text("", color=VERM, size=12)

        def _salvar(e):
            if not f_nome.value.strip():
                txt_erro.value = "Nome é obrigatório."
                try: page.update()
                except Exception: pass
                return
            salvar_rotina_item({
                "id": item["id"] if item else None,
                "tipo": tipo_sel[0],
                "nome": f_nome.value.strip(),
                "horario": f_hora.value.strip() or None,
                "dias_semana": f_dias.value.strip() or None,
                "descricao": f_desc.value.strip() or None,
                "quantidade": f_qtd.value.strip() or None,
                "ativo": 1 if sw_ativo.value else 0,
            })
            _carregar()
            _mostrar_lista()

        def _excluir(e):
            if item and item.get("id"):
                excluir_rotina_item(item["id"])
                _carregar()
                _mostrar_lista()

        ficha = ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.TextButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.ARROW_BACK, size=16),
                                ft.Text("Voltar", size=13),
                            ], spacing=4, tight=True),
                            on_click=lambda e: (_carregar(), _mostrar_lista())),
                        ft.Row([
                            ft.Icon(ft.Icons.SCHEDULE, size=18, color=VERD),
                            ft.Text("Nova Rotina" if is_novo else "Editar Rotina",
                                    size=16, weight=ft.FontWeight.W_700, color=TXT),
                        ], spacing=8, tight=True),
                        ft.Container(expand=True),
                        ft.FilledButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.SAVE, size=16),
                                ft.Text("Salvar", size=13),
                            ], spacing=6, tight=True),
                            style=ft.ButtonStyle(
                                bgcolor=VERD,
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.padding.symmetric(horizontal=16, vertical=10)),
                            on_click=_salvar),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.padding.symmetric(horizontal=16, vertical=12),
                    border=ft.Border(bottom=ft.BorderSide(1, BD))),
                ft.Container(
                    content=ft.Column([
                        _label_sec("TIPO"), chips_tipo,
                        ft.Container(height=4),
                        f_nome,
                        ft.Row([f_qtd, f_hora, f_dias], spacing=8),
                        f_desc,
                        ft.Container(height=4), sw_ativo,
                        txt_erro,
                    ] + ([
                        ft.Container(height=8),
                        ft.TextButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.DELETE_OUTLINE, size=14, color=VERM),
                                ft.Text("Excluir item", size=12, color=VERM),
                            ], spacing=4, tight=True),
                            on_click=_excluir),
                    ] if item else []),
                    spacing=8, scroll=ft.ScrollMode.AUTO),
                    padding=ft.padding.all(16), expand=True),
            ], expand=True, spacing=0))

        wrapper.controls.clear()
        wrapper.controls.append(ficha)
        try: page.update()
        except Exception: pass

    def _mostrar_lista():
        wrapper.controls.clear()
        wrapper.controls.append(ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Container(expand=True),
                        ft.FilledButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.ADD, size=16),
                                ft.Text("Novo Item", size=13),
                            ], spacing=6, tight=True),
                            style=ft.ButtonStyle(
                                bgcolor=VERD,
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.padding.symmetric(horizontal=14, vertical=10)),
                            on_click=lambda e: _abrir_ficha(None)),
                    ]),
                    padding=ft.padding.symmetric(horizontal=0, vertical=4)),
                ft.Container(
                    content=ft.Column([lista], scroll=ft.ScrollMode.AUTO),
                    expand=True),
            ], expand=True, spacing=8)))
        try: page.update()
        except Exception: pass

    _carregar()
    _mostrar_lista()


# ══════════════════════════════════════════════════════════════
# ABA 2 — DIÁRIO DE SAÚDE
# ══════════════════════════════════════════════════════════════

def _conteudo_diario(page):
    lista = ft.Column(spacing=8)
    painel_stats = ft.Column(spacing=6)

    def _carregar_stats():
        painel_stats.controls.clear()
        tend = tendencias_diario(30)
        tags = tags_frequentes(90, 8)

        if tend.get("total", 0) == 0:
            return

        itens_stat = []
        if tend.get("avg_humor"):
            itens_stat.append(ft.Row([
                ft.Text("Humor médio (30d):", size=11, color=SEC, expand=True),
                ft.Text(
                    f'{HUMOR_EMOJI[int(tend["avg_humor"])] if 1 <= int(tend["avg_humor"]) <= 5 else ""} '
                    f'{tend["avg_humor"]}',
                    size=12, color=AMAR, weight=ft.FontWeight.W_600),
            ]))
        if tend.get("avg_energia"):
            itens_stat.append(ft.Row([
                ft.Text("Energia média (30d):", size=11, color=SEC, expand=True),
                ft.Text(
                    f'{ENERGIA_EMOJI[int(tend["avg_energia"])] if 1 <= int(tend["avg_energia"]) <= 5 else ""} '
                    f'{tend["avg_energia"]}',
                    size=12, color=AZUL, weight=ft.FontWeight.W_600),
            ]))
        if tend.get("avg_sono"):
            itens_stat.append(ft.Row([
                ft.Text("Sono médio (30d):", size=11, color=SEC, expand=True),
                ft.Text(f'{tend["avg_sono"]}h', size=12, color=ROXO,
                        weight=ft.FontWeight.W_600),
            ]))
        if tend.get("avg_peso"):
            itens_stat.append(ft.Row([
                ft.Text("Peso médio (30d):", size=11, color=SEC, expand=True),
                ft.Text(f'{tend["avg_peso"]} kg', size=12, color=CORAL,
                        weight=ft.FontWeight.W_600),
            ]))

        if tags:
            chips = ft.Row(wrap=True, spacing=6)
            for tag, cnt in tags:
                chips.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Text(tag, size=10, color=MUT),
                        ft.Text(str(cnt), size=9, color=AMAR),
                    ], spacing=4, tight=True),
                    bgcolor=BD, border_radius=12,
                    padding=ft.padding.symmetric(horizontal=8, vertical=3)))
            itens_stat.append(ft.Container(
                content=ft.Column([
                    _label_sec("TAGS FREQUENTES (90d)"),
                    chips,
                ], spacing=6),
                padding=ft.padding.only(top=4)))

        painel_stats.controls.append(_card_border(AMAR, ft.Column(
            [_label_sec("TENDÊNCIAS", AMAR)] + itens_stat, spacing=6)))

    def _carregar():
        lista.controls.clear()
        _carregar_stats()
        entradas = listar_diario(limite=60)

        if not entradas:
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.BOOK, size=48, color=MUT),
                    ft.Text("Nenhum relato no diário.", color=SEC, size=13),
                    ft.Text("Registre como você está se sentindo.", color=MUT, size=11),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=40))
            try: page.update()
            except Exception: pass
            return

        data_atual = ""
        for en in entradas:
            if en["data"] != data_atual:
                data_atual = en["data"]
                try:
                    d = datetime.strptime(data_atual, "%Y-%m-%d")
                    label_data = d.strftime("%d/%m/%Y")
                except Exception:
                    label_data = data_atual
                lista.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CALENDAR_TODAY, size=13, color=AZUL),
                        ft.Text(label_data, size=13, color=AZUL,
                                weight=ft.FontWeight.W_700),
                    ], spacing=6),
                    padding=ft.padding.only(top=12, left=4, bottom=4)))
            lista.controls.append(_card_entrada(en))

        try: page.update()
        except Exception: pass

    def _card_entrada(en):
        humor  = en.get("humor") or 0
        energia = en.get("energia") or 0
        tags_txt = en.get("tags") or ""
        hora_txt = (en.get("hora") or "")[:5]

        badges = ft.Row(wrap=True, spacing=6)
        if 1 <= humor <= 5:
            badges.controls.append(_badge(f"{HUMOR_EMOJI[humor]} {humor}/5", AMAR))
        if 1 <= energia <= 5:
            badges.controls.append(_badge(f"{ENERGIA_EMOJI[energia]} {energia}/5", AZUL))
        if en.get("sono_horas"):
            badges.controls.append(_badge(f"💤 {en['sono_horas']}h", ROXO))
        if en.get("peso"):
            badges.controls.append(_badge(f"⚖ {en['peso']}kg", CORAL))
        if en.get("pressao"):
            badges.controls.append(_badge(f"❤ {en['pressao']}", VERM))

        tags_row = ft.Row(wrap=True, spacing=4)
        if tags_txt:
            for t in tags_txt.split(","):
                t = t.strip()
                if t:
                    tags_row.controls.append(ft.Container(
                        content=ft.Text(t, size=10, color=MUT),
                        bgcolor=BD, border_radius=10,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2)))

        def _editar(e, entrada=en):
            _abrir_formulario(entrada)

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(hora_txt, size=11, color=MUT),
                    ft.Container(expand=True),
                    ft.IconButton(
                        ft.Icons.EDIT_ROUNDED, icon_color=MUT, icon_size=15,
                        on_click=_editar,
                        style=ft.ButtonStyle(
                            padding=ft.padding.all(2),
                            shape=ft.RoundedRectangleBorder(radius=6))),
                ], spacing=4),
                ft.Text(en["relato"], size=13, color=TXT),
                badges if badges.controls else ft.Container(),
                tags_row if tags_row.controls else ft.Container(),
                ft.Text(f'Remédio: {en["remedio_tomado"]}', size=10, color=LAR)
                    if en.get("remedio_tomado") else ft.Container(),
            ], spacing=5),
            bgcolor=CARD, border_radius=10,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.Border(
                left=ft.BorderSide(3, AZUL),
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                right=ft.BorderSide(1, BD)),
            on_click=_editar, ink=True)

    def _abrir_formulario(entrada=None):
        is_nova = entrada is None

        f_data    = _campo("Data *",
                            entrada["data"] if entrada else date.today().isoformat(),
                            largura=140)
        f_hora    = _campo("Hora", (entrada.get("hora") or "")[:5] if entrada else
                            datetime.now().strftime("%H:%M"),
                            largura=90, keyboard=ft.KeyboardType.DATETIME)
        f_relato  = _campo("Relato *",
                            entrada.get("relato","") if entrada else "",
                            multiline=True, min_lines=4,
                            hint="Hoje acordei gripado e tomei um Benegrip…")
        f_tags    = _campo("Tags (vírgula)",
                            entrada.get("tags","") if entrada else "",
                            hint="gripe, dor_cabeca, cansaço",
                            largura=None)
        f_remedio = _campo("Remédio tomado",
                            entrada.get("remedio_tomado","") if entrada else "",
                            hint="Ex: Benegrip, Paracetamol",
                            largura=None)
        f_sono    = _campo("Horas de sono",
                            str(entrada.get("sono_horas","")) if entrada and entrada.get("sono_horas") else "",
                            largura=110, keyboard=ft.KeyboardType.NUMBER,
                            hint="8.0")
        f_peso    = _campo("Peso (kg)",
                            str(entrada.get("peso","")) if entrada and entrada.get("peso") else "",
                            largura=100, keyboard=ft.KeyboardType.NUMBER,
                            hint="70.5")
        f_pressao = _campo("Pressão",
                            entrada.get("pressao","") if entrada else "",
                            largura=100, hint="120/80")

        # Humor e Energia — seletores 1-5
        humor_sel  = [entrada.get("humor") or 3 if entrada else 3]
        energia_sel = [entrada.get("energia") or 3 if entrada else 3]

        humor_row  = ft.Row(spacing=8)
        energia_row = ft.Row(spacing=8)

        def _build_selector(row, sel_ref, emojis, cor, label):
            row.controls.clear()
            row.controls.append(ft.Text(label, size=11, color=SEC))
            for i in range(1, 6):
                sel = i == sel_ref[0]
                def _clk(e, v=i, r=sel_ref, _row=row):
                    r[0] = v
                    _build_selector(_row, r, emojis, cor, label)
                    try: page.update()
                    except Exception: pass
                row.controls.append(ft.Container(
                    content=ft.Text(emojis[i], size=20),
                    bgcolor=f"{cor}30" if sel else "transparent",
                    border_radius=8,
                    padding=ft.padding.all(6),
                    on_click=_clk, ink=True,
                    border=ft.Border(
                        top=ft.BorderSide(1, cor if sel else "transparent"),
                        bottom=ft.BorderSide(1, cor if sel else "transparent"),
                        left=ft.BorderSide(1, cor if sel else "transparent"),
                        right=ft.BorderSide(1, cor if sel else "transparent"))))

        _build_selector(humor_row,  humor_sel,  HUMOR_EMOJI,  AMAR, "Humor")
        _build_selector(energia_row, energia_sel, ENERGIA_EMOJI, AZUL, "Energia")

        txt_erro = ft.Text("", color=VERM, size=12)

        def _salvar(e):
            if not f_relato.value.strip():
                txt_erro.value = "O relato é obrigatório."
                try: page.update()
                except Exception: pass
                return
            try:
                sono = float(f_sono.value.replace(",",".")) if f_sono.value.strip() else None
            except ValueError:
                sono = None
            try:
                peso = float(f_peso.value.replace(",",".")) if f_peso.value.strip() else None
            except ValueError:
                peso = None

            salvar_diario_entrada({
                "id": entrada["id"] if entrada else None,
                "data": f_data.value.strip() or date.today().isoformat(),
                "hora": f_hora.value.strip() or None,
                "humor": humor_sel[0],
                "energia": energia_sel[0],
                "sono_horas": sono,
                "peso": peso,
                "pressao": f_pressao.value.strip() or None,
                "relato": f_relato.value.strip(),
                "tags": f_tags.value.strip() or None,
                "remedio_tomado": f_remedio.value.strip() or None,
            })
            _carregar()
            _mostrar_lista()

        def _excluir(e):
            if entrada and entrada.get("id"):
                excluir_diario_entrada(entrada["id"])
                _carregar()
                _mostrar_lista()

        return ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.TextButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.ARROW_BACK, size=16),
                                ft.Text("Voltar", size=13),
                            ], spacing=4, tight=True),
                            on_click=lambda e: (_carregar(), _mostrar_lista())),
                        ft.Row([
                            ft.Icon(ft.Icons.EDIT_NOTE, size=18, color=AZUL),
                            ft.Text("Novo Relato" if is_nova else "Editar Relato",
                                    size=16, weight=ft.FontWeight.W_700, color=TXT),
                        ], spacing=8, tight=True),
                        ft.Container(expand=True),
                        ft.FilledButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.SAVE, size=16),
                                ft.Text("Salvar", size=13),
                            ], spacing=6, tight=True),
                            style=ft.ButtonStyle(
                                bgcolor=AZUL,
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.padding.symmetric(horizontal=16, vertical=10)),
                            on_click=_salvar),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.padding.symmetric(horizontal=16, vertical=12),
                    border=ft.Border(bottom=ft.BorderSide(1, BD))),
                ft.Container(
                    content=ft.Column([
                        ft.Row([f_data, f_hora], spacing=8),
                        ft.Container(height=4),
                        _label_sec("COMO VOCÊ SE SENTE"),
                        humor_row, energia_row,
                        ft.Container(height=4),
                        f_relato,
                        ft.Container(height=4),
                        _label_sec("MÉTRICAS (opcional)"),
                        ft.Row([f_sono, f_peso, f_pressao], spacing=8),
                        f_remedio,
                        ft.Container(height=4),
                        f_tags,
                        txt_erro,
                    ] + ([
                        ft.Container(height=8),
                        ft.TextButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.DELETE_OUTLINE, size=14, color=VERM),
                                ft.Text("Excluir relato", size=12, color=VERM),
                            ], spacing=4, tight=True),
                            on_click=_excluir),
                    ] if entrada else []),
                    spacing=8, scroll=ft.ScrollMode.AUTO),
                    padding=ft.padding.all(16), expand=True),
            ], expand=True, spacing=0))

    # wrapper para navegação lista ↔ formulário
    wrapper_diario = ft.Column(expand=True, spacing=0)

    def _mostrar_lista():
        wrapper_diario.controls.clear()
        wrapper_diario.controls.append(ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Container(expand=True),
                        ft.FilledButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.ADD, size=16),
                                ft.Text("Novo Relato", size=13),
                            ], spacing=6, tight=True),
                            style=ft.ButtonStyle(
                                bgcolor=AZUL,
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.padding.symmetric(horizontal=14, vertical=10)),
                            on_click=lambda e: _abrir_novo()),
                    ]),
                    padding=ft.padding.symmetric(horizontal=0, vertical=4)),
                ft.Container(
                    content=ft.Column([painel_stats, lista], scroll=ft.ScrollMode.AUTO),
                    expand=True),
            ], expand=True, spacing=8)))
        try: page.update()
        except Exception: pass

    def _abrir_novo():
        ficha = _abrir_formulario(None)
        wrapper_diario.controls.clear()
        wrapper_diario.controls.append(ficha)
        try: page.update()
        except Exception: pass

    # sobrescreve _abrir_formulario para integrar com wrapper_diario
    _orig_abrir = _abrir_formulario

    def _abrir_formulario_nav(entrada=None):
        ficha = _orig_abrir(entrada)
        wrapper_diario.controls.clear()
        wrapper_diario.controls.append(ficha)
        try: page.update()
        except Exception: pass

    # patch local: reconstruir _card_entrada para usar versão nav
    def _card_entrada_nav(en):
        humor  = en.get("humor") or 0
        energia = en.get("energia") or 0
        tags_txt = en.get("tags") or ""
        hora_txt = (en.get("hora") or "")[:5]

        badges = ft.Row(wrap=True, spacing=6)
        if 1 <= humor <= 5:
            badges.controls.append(_badge(f"{HUMOR_EMOJI[humor]} {humor}/5", AMAR))
        if 1 <= energia <= 5:
            badges.controls.append(_badge(f"{ENERGIA_EMOJI[energia]} {energia}/5", AZUL))
        if en.get("sono_horas"):
            badges.controls.append(_badge(f"💤 {en['sono_horas']}h", ROXO))
        if en.get("peso"):
            badges.controls.append(_badge(f"⚖ {en['peso']}kg", CORAL))
        if en.get("pressao"):
            badges.controls.append(_badge(f"❤ {en['pressao']}", VERM))

        tags_row = ft.Row(wrap=True, spacing=4)
        if tags_txt:
            for t in tags_txt.split(","):
                t = t.strip()
                if t:
                    tags_row.controls.append(ft.Container(
                        content=ft.Text(t, size=10, color=MUT),
                        bgcolor=BD, border_radius=10,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2)))

        def _editar(e, entrada=en):
            _abrir_formulario_nav(entrada)

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(hora_txt, size=11, color=MUT),
                    ft.Container(expand=True),
                    ft.IconButton(
                        ft.Icons.EDIT_ROUNDED, icon_color=MUT, icon_size=15,
                        on_click=_editar,
                        style=ft.ButtonStyle(
                            padding=ft.padding.all(2),
                            shape=ft.RoundedRectangleBorder(radius=6))),
                ], spacing=4),
                ft.Text(en["relato"], size=13, color=TXT),
                badges if badges.controls else ft.Container(),
                tags_row if tags_row.controls else ft.Container(),
                ft.Text(f'Remédio: {en["remedio_tomado"]}', size=10, color=LAR)
                    if en.get("remedio_tomado") else ft.Container(),
            ], spacing=5),
            bgcolor=CARD, border_radius=10,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.Border(
                left=ft.BorderSide(3, AZUL),
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                right=ft.BorderSide(1, BD)),
            on_click=_editar, ink=True)

    def _carregar_nav():
        lista.controls.clear()
        _carregar_stats()
        entradas = listar_diario(limite=60)

        if not entradas:
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.BOOK, size=48, color=MUT),
                    ft.Text("Nenhum relato no diário.", color=SEC, size=13),
                    ft.Text("Registre como você está se sentindo.", color=MUT, size=11),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=40))
            try: page.update()
            except Exception: pass
            return

        data_atual = ""
        for en in entradas:
            if en["data"] != data_atual:
                data_atual = en["data"]
                try:
                    d = datetime.strptime(data_atual, "%Y-%m-%d")
                    label_data = d.strftime("%d/%m/%Y")
                except Exception:
                    label_data = data_atual
                lista.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CALENDAR_TODAY, size=13, color=AZUL),
                        ft.Text(label_data, size=13, color=AZUL,
                                weight=ft.FontWeight.W_700),
                    ], spacing=6),
                    padding=ft.padding.only(top=12, left=4, bottom=4)))
            lista.controls.append(_card_entrada_nav(en))

        try: page.update()
        except Exception: pass

    def _mostrar_lista_final():
        wrapper_diario.controls.clear()
        wrapper_diario.controls.append(ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Container(expand=True),
                        ft.FilledButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.ADD, size=16),
                                ft.Text("Novo Relato", size=13),
                            ], spacing=6, tight=True),
                            style=ft.ButtonStyle(
                                bgcolor=AZUL,
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.padding.symmetric(horizontal=14, vertical=10)),
                            on_click=lambda e: _abrir_formulario_nav(None)),
                    ]),
                    padding=ft.padding.symmetric(horizontal=0, vertical=4)),
                ft.Container(
                    content=ft.Column([painel_stats, lista], scroll=ft.ScrollMode.AUTO),
                    expand=True),
            ], expand=True, spacing=8)))
        try: page.update()
        except Exception: pass

    # Patch: _abrir_formulario_nav usa _mostrar_lista_final no voltar
    def _orig_abrir_v2(entrada=None):
        is_nova = entrada is None

        f_data    = _campo("Data *",
                            entrada["data"] if entrada else date.today().isoformat(),
                            largura=140)
        f_hora    = _campo("Hora", (entrada.get("hora") or "")[:5] if entrada else
                            datetime.now().strftime("%H:%M"),
                            largura=90, keyboard=ft.KeyboardType.DATETIME)
        f_relato  = _campo("Relato *",
                            entrada.get("relato","") if entrada else "",
                            multiline=True, min_lines=4,
                            hint="Hoje acordei gripado e tomei um Benegrip…")
        f_tags    = _campo("Tags (vírgula)",
                            entrada.get("tags","") if entrada else "",
                            hint="gripe, dor_cabeca, cansaço")
        f_remedio = _campo("Remédio tomado",
                            entrada.get("remedio_tomado","") if entrada else "",
                            hint="Ex: Benegrip, Paracetamol")
        f_sono    = _campo("Horas de sono",
                            str(entrada.get("sono_horas","")) if entrada and entrada.get("sono_horas") else "",
                            largura=110, keyboard=ft.KeyboardType.NUMBER, hint="8.0")
        f_peso    = _campo("Peso (kg)",
                            str(entrada.get("peso","")) if entrada and entrada.get("peso") else "",
                            largura=100, keyboard=ft.KeyboardType.NUMBER, hint="70.5")
        f_pressao = _campo("Pressão", entrada.get("pressao","") if entrada else "",
                            largura=100, hint="120/80")

        humor_sel  = [entrada.get("humor") or 3 if entrada else 3]
        energia_sel = [entrada.get("energia") or 3 if entrada else 3]

        humor_row  = ft.Row(spacing=8)
        energia_row = ft.Row(spacing=8)

        def _build_selector(row, sel_ref, emojis, cor, label):
            row.controls.clear()
            row.controls.append(ft.Text(label, size=11, color=SEC))
            for i in range(1, 6):
                sel = i == sel_ref[0]
                def _clk(e, v=i, r=sel_ref, _row=row):
                    r[0] = v
                    _build_selector(_row, r, emojis, cor, label)
                    try: page.update()
                    except Exception: pass
                row.controls.append(ft.Container(
                    content=ft.Text(emojis[i], size=20),
                    bgcolor=f"{cor}30" if sel else "transparent",
                    border_radius=8, padding=ft.padding.all(6),
                    on_click=_clk, ink=True,
                    border=ft.Border(
                        top=ft.BorderSide(1, cor if sel else "transparent"),
                        bottom=ft.BorderSide(1, cor if sel else "transparent"),
                        left=ft.BorderSide(1, cor if sel else "transparent"),
                        right=ft.BorderSide(1, cor if sel else "transparent"))))

        _build_selector(humor_row,  humor_sel,  HUMOR_EMOJI,  AMAR, "Humor")
        _build_selector(energia_row, energia_sel, ENERGIA_EMOJI, AZUL, "Energia")

        txt_erro = ft.Text("", color=VERM, size=12)

        def _salvar(e):
            if not f_relato.value.strip():
                txt_erro.value = "O relato é obrigatório."
                try: page.update()
                except Exception: pass
                return
            try:
                sono = float(f_sono.value.replace(",",".")) if f_sono.value.strip() else None
            except ValueError:
                sono = None
            try:
                peso = float(f_peso.value.replace(",",".")) if f_peso.value.strip() else None
            except ValueError:
                peso = None

            salvar_diario_entrada({
                "id": entrada["id"] if entrada else None,
                "data": f_data.value.strip() or date.today().isoformat(),
                "hora": f_hora.value.strip() or None,
                "humor": humor_sel[0],
                "energia": energia_sel[0],
                "sono_horas": sono,
                "peso": peso,
                "pressao": f_pressao.value.strip() or None,
                "relato": f_relato.value.strip(),
                "tags": f_tags.value.strip() or None,
                "remedio_tomado": f_remedio.value.strip() or None,
            })
            _carregar_nav()
            _mostrar_lista_final()

        def _excluir(e):
            if entrada and entrada.get("id"):
                excluir_diario_entrada(entrada["id"])
                _carregar_nav()
                _mostrar_lista_final()

        return ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.TextButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.ARROW_BACK, size=16),
                                ft.Text("Voltar", size=13),
                            ], spacing=4, tight=True),
                            on_click=lambda e: (_carregar_nav(), _mostrar_lista_final())),
                        ft.Row([
                            ft.Icon(ft.Icons.EDIT_NOTE, size=18, color=AZUL),
                            ft.Text("Novo Relato" if is_nova else "Editar Relato",
                                    size=16, weight=ft.FontWeight.W_700, color=TXT),
                        ], spacing=8, tight=True),
                        ft.Container(expand=True),
                        ft.FilledButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.SAVE, size=16),
                                ft.Text("Salvar", size=13),
                            ], spacing=6, tight=True),
                            style=ft.ButtonStyle(
                                bgcolor=AZUL,
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.padding.symmetric(horizontal=16, vertical=10)),
                            on_click=_salvar),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.padding.symmetric(horizontal=16, vertical=12),
                    border=ft.Border(bottom=ft.BorderSide(1, BD))),
                ft.Container(
                    content=ft.Column([
                        ft.Row([f_data, f_hora], spacing=8),
                        ft.Container(height=4),
                        _label_sec("COMO VOCÊ SE SENTE"),
                        humor_row, energia_row,
                        ft.Container(height=4),
                        f_relato,
                        ft.Container(height=4),
                        _label_sec("MÉTRICAS (opcional)"),
                        ft.Row([f_sono, f_peso, f_pressao], spacing=8),
                        f_remedio,
                        ft.Container(height=4),
                        f_tags,
                        txt_erro,
                    ] + ([
                        ft.Container(height=8),
                        ft.TextButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.DELETE_OUTLINE, size=14, color=VERM),
                                ft.Text("Excluir relato", size=12, color=VERM),
                            ], spacing=4, tight=True),
                            on_click=_excluir),
                    ] if entrada else []),
                    spacing=8, scroll=ft.ScrollMode.AUTO),
                    padding=ft.padding.all(16), expand=True),
            ], expand=True, spacing=0))

    def _abrir_formulario_nav(entrada=None):
        ficha = _orig_abrir_v2(entrada)
        wrapper_diario.controls.clear()
        wrapper_diario.controls.append(ficha)
        try: page.update()
        except Exception: pass

    _carregar_nav()
    _mostrar_lista_final()

    return wrapper_diario


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL
# ══════════════════════════════════════════════════════════════

def criar_tela_dieta(page: ft.Page, voltar_fn):
    ABAS = [
        (0, ft.Icons.SCHEDULE,  "Rotina",  VERD),
        (1, ft.Icons.EDIT_NOTE, "Diário",  AZUL),
    ]
    aba_ativa = [0]

    barra_abas    = ft.Row(spacing=0)
    area_conteudo = ft.Column(spacing=8, expand=True, scroll=ft.ScrollMode.AUTO)

    wrapper_rotina  = ft.Column(expand=True, spacing=0)

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
        if aba_ativa[0] == 0:
            _conteudo_rotina(page, wrapper_rotina)
            area_conteudo.controls.append(wrapper_rotina)
        else:
            area_conteudo.controls.append(_conteudo_diario(page))
        try: page.update()
        except Exception: pass

    _rebuild_abas()
    _rebuild_conteudo()

    cabecalho = ft.Container(
        content=ft.Row([
            ft.TextButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.ARROW_BACK, size=16),
                    ft.Text("Voltar", size=13),
                ], spacing=4, tight=True),
                on_click=lambda e: voltar_fn(),
            ),
            ft.Row([
                ft.Icon(ft.Icons.RESTAURANT_MENU, size=20, color=VERD),
                ft.Text("Rotina & Diário", size=18,
                        weight=ft.FontWeight.W_700, color=TXT),
            ], spacing=8, tight=True),
            ft.Container(expand=True),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=16, vertical=14),
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
    )

    corpo = ft.Column([
        cabecalho,
        ft.Container(
            content=barra_abas,
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
