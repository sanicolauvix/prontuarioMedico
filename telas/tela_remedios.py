"""
tela_remedios.py — Koios Prontuário
Controle completo de medicamentos.
Padrão visual: idêntico a tela_exames.py (header + barra de abas + área de conteúdo)
Abas: HOJE | REMÉDIOS | FARMÁCIAS
"""
import logging
import re
import flet as ft
import threading
import webbrowser
from datetime import date, datetime, timedelta
from ..dados.model_prontuario import (
    listar_remedios, salvar_remedio,
    remedios_estoque_baixo, listar_medicos,
    salvar_horarios_remedio, listar_horarios_remedio,
    registrar_tomada, listar_tomadas_hoje, resumo_adesao,
    atualizar_foto_remedio,
    listar_fotos_remedio, adicionar_foto_remedio, excluir_foto_remedio,
    listar_farmacias, salvar_farmacia,
    salvar_compra, listar_compras_remedio, estatisticas_preco_remedio,
    criar_orcamento, salvar_resposta_orcamento,
    gerar_mensagem_orcamento, link_whatsapp,
    analisar_resposta_orcamento_ia,
)
from ..utils.foto_picker import (
    criar_btn_seletor_foto, processar_foto, _is_android,
)

logger = logging.getLogger(__name__)

# ── Paleta ────────────────────────────────────────────────────
BG   = "#0D1117";  CARD = "#161B22";  BD  = "#21262D";  BD2 = "#30363D"
TXT  = "#E6EDF3";  SEC  = "#8B949E";  MUT = "#484F58"
AZUL = "#58A6FF";  VERD = "#3FB950";  LAR = "#F0883E"
AMAR = "#D29922";  VERM = "#DA3633";  ROXO = "#BC8CFF";  CORAL = "#FF7B72"


# ══════════════════════════════════════════════════════════════
# HELPERS VISUAIS
# ══════════════════════════════════════════════════════════════

def _cor_estoque(atual, minimo):
    if atual <= 0:      return VERM
    if atual <= minimo:  return LAR
    return VERD

def _campo(label, valor="", largura=None, multiline=False, min_lines=1,
           hint=None, keyboard=ft.KeyboardType.TEXT):
    kw = dict(label=label, value=valor or "", bgcolor=CARD, border_color=BD2,
              focused_border_color=AZUL, label_style=ft.TextStyle(color=SEC),
              text_style=ft.TextStyle(color=TXT), border_radius=8,
              multiline=multiline, min_lines=min_lines, keyboard_type=keyboard)
    if hint:
        kw["hint_text"] = hint; kw["hint_style"] = ft.TextStyle(color=MUT, size=11)
    if largura: kw["width"] = largura
    else:       kw["expand"] = True
    return ft.TextField(**kw)

def _label_sec(texto, cor=MUT):
    return ft.Text(texto, size=10, color=cor, weight=ft.FontWeight.W_700)

def _badge(texto, cor):
    return ft.Container(
        content=ft.Text(texto, size=10, color=cor, weight=ft.FontWeight.W_600),
        bgcolor=f"{cor}18", border_radius=10,
        padding=ft.padding.symmetric(horizontal=8, vertical=3))

def _card_border(cor_esq, conteudo):
    return ft.Container(content=conteudo, bgcolor=CARD, border_radius=10,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border=ft.Border(left=ft.BorderSide(3, cor_esq),
            top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
            right=ft.BorderSide(1, BD)))


def _mask_hora(campo: ft.TextField):
    """on_change: formata HH:MM automaticamente enquanto digita."""
    def _on(e):
        raw = re.sub(r"\D", "", campo.value or "")[:4]
        if len(raw) >= 3:
            novo = raw[:2] + ":" + raw[2:]
        else:
            novo = raw
        if campo.value != novo:
            campo.value = novo
            try: campo.update()
            except Exception: pass
    campo.on_change = _on


def _mask_data(campo: ft.TextField):
    """on_change: formata DD/MM/AAAA automaticamente enquanto digita."""
    def _on(e):
        raw = re.sub(r"\D", "", campo.value or "")[:8]
        if len(raw) >= 5:
            novo = raw[:2] + "/" + raw[2:4] + "/" + raw[4:]
        elif len(raw) >= 3:
            novo = raw[:2] + "/" + raw[2:]
        else:
            novo = raw
        if campo.value != novo:
            campo.value = novo
            try: campo.update()
            except Exception: pass
    campo.on_change = _on


# ══════════════════════════════════════════════════════════════
# ABA 1 — HOJE (painel de tomadas diárias)
# ══════════════════════════════════════════════════════════════

def _build_aba_hoje(page):
    lista = ft.Column(spacing=8)
    data_hoje = [date.today().isoformat()]

    def _carregar():
        lista.controls.clear()
        tomadas = listar_tomadas_hoje(data_hoje[0])

        if not tomadas:
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=48, color=VERD),
                    ft.Text("Nenhum remédio programado para hoje!",
                            color=SEC, size=14, text_align=ft.TextAlign.CENTER),
                    ft.Text("Cadastre remédios com horários na aba Remédios.",
                            color=MUT, size=11, text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=40))
            try: page.update()
            except Exception: pass
            return

        # Progresso do dia
        total = len(tomadas)
        tomou = sum(1 for t in tomadas if t["status"] == "tomou")
        nao   = sum(1 for t in tomadas if t["status"] == "nao_tomou")
        pend  = total - tomou - nao
        pct   = tomou / total if total > 0 else 0

        cor_pct = VERD if pct >= 0.8 else (AMAR if pct >= 0.5 else VERM)
        lista.controls.append(ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.TODAY, size=16, color=AZUL),
                    ft.Text(f"Hoje — {date.today().strftime('%d/%m/%Y')}",
                            size=13, color=AZUL, weight=ft.FontWeight.W_600, expand=True),
                    ft.Text(f"{tomou}/{total}", size=15, color=cor_pct,
                            weight=ft.FontWeight.W_700),
                ]),
                ft.ProgressBar(value=pct, color=cor_pct, bgcolor=BD, height=6),
                ft.Row([
                    _badge(f"✓ {tomou} tomou", VERD),
                    _badge(f"✗ {nao} não tomou", VERM) if nao > 0 else ft.Container(),
                    _badge(f"◦ {pend} pendente", AMAR) if pend > 0 else ft.Container(),
                ], spacing=6),
            ], spacing=6),
            bgcolor=CARD, border_radius=10,
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            border=ft.border.all(1, BD)))

        # Cartões agrupados por hora
        hora_atual = ""
        for t in tomadas:
            if t["hora"] != hora_atual:
                hora_atual = t["hora"]
                lista.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.ACCESS_TIME, size=14, color=AMAR),
                        ft.Text(hora_atual, size=14, color=AMAR,
                                weight=ft.FontWeight.W_700),
                    ], spacing=6),
                    padding=ft.padding.only(top=14, left=4, bottom=2)))

            status = t["status"]
            if status == "tomou":
                cor = VERD; icone = ft.Icons.CHECK_CIRCLE; opa = 0.55
            elif status == "nao_tomou":
                cor = VERM; icone = ft.Icons.CANCEL; opa = 0.55
            else:
                cor = AMAR; icone = ft.Icons.CIRCLE_OUTLINED; opa = 1.0

            rid, hora = t["remedio_id"], t["hora"]

            def _mk_tomou(r=rid, h=hora):
                def _fn(e): registrar_tomada(r, data_hoje[0], h, "tomou"); _carregar()
                return _fn
            def _mk_nao(r=rid, h=hora):
                def _fn(e): registrar_tomada(r, data_hoje[0], h, "nao_tomou"); _carregar()
                return _fn
            def _mk_desfazer(r=rid, h=hora):
                def _fn(e): registrar_tomada(r, data_hoje[0], h, "pendente"); _carregar()
                return _fn

            botoes = ft.Row(spacing=4)
            if status == "pendente":
                botoes.controls = [
                    ft.IconButton(ft.Icons.CHECK, icon_color=VERD, icon_size=22,
                        on_click=_mk_tomou(),
                        style=ft.ButtonStyle(bgcolor="#0D1C12",
                            shape=ft.RoundedRectangleBorder(radius=8))),
                    ft.IconButton(ft.Icons.CLOSE, icon_color=VERM, icon_size=22,
                        on_click=_mk_nao(),
                        style=ft.ButtonStyle(bgcolor="#1C1014",
                            shape=ft.RoundedRectangleBorder(radius=8))),
                ]
            else:
                botoes.controls = [
                    ft.TextButton(content=ft.Text("Desfazer", size=10, color=MUT),
                                  on_click=_mk_desfazer())]

            est = t.get("estoque_atual", 0) or 0
            mn  = t.get("estoque_minimo", 5) or 5

            lista.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon(icone, size=24, color=cor),
                    ft.Column([
                        ft.Text(t["nome"], size=13, color=TXT,
                                weight=ft.FontWeight.W_600),
                        ft.Text(t.get("dosagem") or "", size=11, color=SEC),
                    ], spacing=1, expand=True),
                    ft.Column([
                        ft.Text(str(est), size=14, color=_cor_estoque(est, mn),
                                weight=ft.FontWeight.W_700),
                        ft.Text("unid.", size=8, color=MUT),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                    botoes,
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD, border_radius=10, opacity=opa,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                border=ft.Border(left=ft.BorderSide(3, cor),
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD))))

        try: page.update()
        except Exception: pass

    _carregar()
    return [lista]


# ══════════════════════════════════════════════════════════════
# ABA 2 — REMÉDIOS (lista + ficha de cadastro)
# ══════════════════════════════════════════════════════════════

def _calcular_horarios(intervalo_h: int, hora_inicio: str) -> list[str]:
    """Gera lista de horários distribuídos a partir de hora_inicio."""
    try:
        h, m = map(int, hora_inicio.split(":"))
    except Exception:
        h, m = 8, 0
    resultado = []
    qtd = round(24 / intervalo_h)
    for i in range(qtd):
        total_min = h * 60 + m + i * intervalo_h * 60
        total_min = total_min % (24 * 60)
        resultado.append(f"{total_min // 60:02d}:{total_min % 60:02d}")
    return resultado


# Tabela: (label, intervalo_horas)
# intervalo > 0  → baseado em horas fixas, calcula horários automaticamente
# intervalo = -1 → baseado em refeições/eventos, sem horário fixo
_FREQ_SUGESTOES = [
    ("1× ao dia",             24),
    ("2× ao dia",             12),
    ("3× ao dia",              8),
    ("4× ao dia",              6),
    ("A cada 4h",              4),
    ("A cada 6h",              6),
    ("A cada 8h",              8),
    ("A cada 12h",            12),
    ("Em jejum",              -1),
    ("Após café da manhã",    -1),
    ("Após almoço",           -1),
    ("Após jantar",           -1),
    ("Após refeições",        -1),
    ("Conforme necessidade",  -1),
]

_DOS_SUGESTOES = [
    "10mg", "20mg", "25mg", "40mg", "50mg",
    "75mg", "100mg", "150mg", "200mg", "250mg",
    "500mg", "1g", "1 comprimido", "2 comprimidos",
    "5ml", "10ml", "1 cápsula",
]


def _build_ficha_remedio(page, remedio, voltar_fn):
    """Ficha de cadastro/edição com estoque, horários, compras, adesão."""
    is_novo = remedio is None

    # ── Médico (autocomplete) ─────────────────────────────
    medicos    = listar_medicos(so_ativos=True)
    med_map    = {str(m["id"]): m["nome"] for m in medicos}
    med_id_sel = [str(remedio.get("medico_id","")) if remedio else None]

    f_medico = _campo("Médico que prescreveu",
                      med_map.get(med_id_sel[0], "") if med_id_sel[0] else "",
                      hint="Digite para buscar…")
    sug_med  = ft.Column(spacing=2, visible=False)

    def _filtrar_med(e):
        termo = (f_medico.value or "").strip().upper()
        sug_med.controls.clear()
        if not termo:
            sug_med.visible = False; med_id_sel[0] = None
            try: page.update()
            except Exception: pass
            return
        encontrados = [m for m in medicos if termo in m["nome"].upper()][:6]
        for m in encontrados:
            def _sel(e, med=m):
                f_medico.value = med["nome"]; med_id_sel[0] = str(med["id"])
                sug_med.controls.clear(); sug_med.visible = False
                try: page.update()
                except Exception: pass
            especialidade = m.get("especialidade") or ""
            sug_med.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.PERSON, size=14, color=ROXO),
                    ft.Column([
                        ft.Text(m["nome"], size=13, color=TXT),
                        ft.Text(especialidade, size=10, color=MUT) if especialidade else ft.Container(),
                    ], spacing=0, expand=True),
                ], spacing=8),
                bgcolor=BD, border_radius=6,
                padding=ft.padding.symmetric(horizontal=12, vertical=8), on_click=_sel,
                ink=True))
        sug_med.visible = bool(encontrados)
        try: page.update()
        except Exception: pass
    f_medico.on_change = _filtrar_med

    # ── Nome ──────────────────────────────────────────────
    f_nome = _campo("Nome do medicamento *", remedio["nome"] if remedio else "")

    # ── Dosagem (campo + dropdown de sugestões) ───────────
    f_dos = _campo("Dosagem", remedio.get("dosagem","") if remedio else "",
                   hint="ex: 500mg, 1 comprimido, 5ml…")
    sug_dos = ft.Column(spacing=2, visible=False)

    def _item_sug(label, cor, campo, lista_sug, on_select=None):
        def _sel(e):
            campo.value = label
            lista_sug.controls.clear(); lista_sug.visible = False
            if on_select: on_select(label)
            try: page.update()
            except Exception: pass
        return ft.Container(
            content=ft.Text(label, size=13, color=cor),
            bgcolor=BD, border_radius=6,
            padding=ft.padding.symmetric(horizontal=12, vertical=9),
            on_click=_sel, ink=True)

    def _abrir_sug_dos(e):
        sug_dos.controls.clear()
        termo = (f_dos.value or "").strip().upper()
        itens = [d for d in _DOS_SUGESTOES if termo in d.upper()] if termo else _DOS_SUGESTOES
        for d in itens[:10]:
            sug_dos.controls.append(_item_sug(d, AZUL, f_dos, sug_dos))
        sug_dos.visible = bool(sug_dos.controls)
        try: page.update()
        except Exception: pass

    f_dos.on_focus  = _abrir_sug_dos
    f_dos.on_change = _abrir_sug_dos

    # ── Frequência (campo + dropdown) ────────────────────
    f_freq = _campo("Frequência", remedio.get("frequencia","") if remedio else "",
                    hint="ex: 1× ao dia, a cada 8h…")
    sug_freq = ft.Column(spacing=2, visible=False)

    # ── Bloco de horários (visível/oculto conforme frequência) ──
    horas_existentes = listar_horarios_remedio(remedio["id"]) if remedio and remedio.get("id") else []

    # Campo "1ª dose às" — hora de início para calcular os demais
    f_hora_inicio = _campo("1ª dose às", "08:00", hint="HH:MM", largura=110)

    # Texto calculado exibindo os horários resultantes
    txt_horarios_calc = ft.Text("", size=13, color=VERD, weight=ft.FontWeight.W_600)

    # Campo livre para edição manual (preenchido automaticamente, editável)
    f_horarios = _campo("Horários",
                        ", ".join(h["hora"] for h in horas_existentes),
                        hint="08:00, 16:00, 22:00…")

    # Container que agrupa tudo relacionado a horários
    bloco_horarios = ft.Column(spacing=6, visible=False)

    # Intervalo atual (closure)
    intervalo_atual = [0]

    def _recalc(e):
        """Máscara HH:MM + recalcula horários ao alterar 1ª dose."""
        raw = re.sub(r"\D", "", f_hora_inicio.value or "")[:4]
        novo = (raw[:2] + ":" + raw[2:]) if len(raw) >= 3 else raw
        if f_hora_inicio.value != novo:
            f_hora_inicio.value = novo
            try: f_hora_inicio.update()
            except Exception: pass
        iv = intervalo_atual[0]
        if iv > 0:
            horas = _calcular_horarios(iv, f_hora_inicio.value or "08:00")
            f_horarios.value = ", ".join(horas)
            txt_horarios_calc.value = " → ".join(horas)
            try: txt_horarios_calc.update()
            except Exception: pass
            try: f_horarios.update()
            except Exception: pass

    f_hora_inicio.on_change = _recalc

    def _rebuild_bloco_horarios():
        iv = intervalo_atual[0]
        bloco_horarios.controls.clear()

        if iv == -1:
            # frequência por refeição/evento — sem horário
            bloco_horarios.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=SEC),
                    ft.Text("Esta frequência não requer horário fixo.", size=12, color=SEC),
                ], spacing=8),
                padding=ft.padding.only(top=2, bottom=2)))
            f_horarios.value = ""
        elif iv > 0:
            horas = _calcular_horarios(iv, f_hora_inicio.value or "08:00")
            f_horarios.value = ", ".join(horas)
            txt_horarios_calc.value = " → ".join(horas)

            bloco_horarios.controls.append(
                ft.Row([
                    ft.Column([
                        _label_sec("1ª DOSE ÀS"),
                        f_hora_inicio,
                    ], spacing=4),
                    ft.Container(
                        content=ft.Column([
                            _label_sec("HORÁRIOS CALCULADOS"),
                            txt_horarios_calc,
                        ], spacing=4),
                        expand=True,
                        padding=ft.padding.only(left=12)),
                ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.START))
            bloco_horarios.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.EDIT_NOTE, size=13, color=MUT),
                        ft.Text("Editar manualmente:", size=11, color=MUT),
                    ], spacing=6),
                    padding=ft.padding.only(top=4)))
            bloco_horarios.controls.append(f_horarios)
        else:
            # frequência livre (digitada) — campo manual simples
            bloco_horarios.controls.append(f_horarios)

        bloco_horarios.visible = True
        try: page.update()
        except Exception: pass

    def _aplicar_freq(freq_label):
        """Determina intervalo da frequência e reconstrói bloco de horários."""
        iv = None
        for label, fiv in _FREQ_SUGESTOES:
            if label.lower() == freq_label.lower():
                iv = fiv; break
        if iv is None:
            m = re.search(r"(\d+)\s*h", freq_label.lower())
            if m: iv = int(m.group(1))
        if iv is None:
            iv = 0  # livre, mostra campo manual
        intervalo_atual[0] = iv
        _rebuild_bloco_horarios()

    def _abrir_sug_freq(e):
        sug_freq.controls.clear()
        termo = (f_freq.value or "").strip().upper()
        itens = [(lbl, iv) for lbl, iv in _FREQ_SUGESTOES
                 if not termo or termo in lbl.upper()]
        for label, iv in itens:
            cor = CORAL if iv > 0 else SEC
            def _sel(e, lbl=label):
                f_freq.value = lbl
                sug_freq.controls.clear(); sug_freq.visible = False
                _aplicar_freq(lbl)
            sug_freq.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.SCHEDULE if iv > 0 else ft.Icons.RESTAURANT, size=14,
                            color=cor),
                    ft.Text(label, size=13, color=cor),
                ], spacing=8),
                bgcolor=BD, border_radius=6,
                padding=ft.padding.symmetric(horizontal=12, vertical=9),
                on_click=_sel, ink=True))
        sug_freq.visible = bool(sug_freq.controls)
        try: page.update()
        except Exception: pass

    f_freq.on_focus  = _abrir_sug_freq
    f_freq.on_change = _abrir_sug_freq

    # Se já há frequência salva, reconstrói o bloco imediatamente
    if remedio and remedio.get("frequencia"):
        _aplicar_freq(remedio["frequencia"])
    elif horas_existentes:
        # tem horários salvos mas sem frequência clara — mostra campo manual
        intervalo_atual[0] = 0
        _rebuild_bloco_horarios()

    # ── Período ───────────────────────────────────────────
    f_ini = _campo("Início", remedio.get("data_inicio","") if remedio else "",
                   hint="DD/MM/AAAA", largura=150)
    f_fim = _campo("Fim", remedio.get("data_fim","") if remedio else "",
                   hint="DD/MM/AAAA", largura=150)
    _mask_data(f_ini)
    _mask_data(f_fim)

    # ── Observações ───────────────────────────────────────
    f_obs  = _campo("Observações", remedio.get("observacoes","") if remedio else "",
                    multiline=True, min_lines=2)

    # ── Estoque ───────────────────────────────────────────
    f_est = _campo("Estoque", str(remedio.get("estoque_atual",0)) if remedio else "0",
                   largura=100, keyboard=ft.KeyboardType.NUMBER)
    f_min = _campo("Alerta mín.", str(remedio.get("estoque_minimo",5)) if remedio else "5",
                   largura=100, keyboard=ft.KeyboardType.NUMBER)

    def _ajustar(d):
        try:
            f_est.value = str(max(0, int(f_est.value or 0) + d))
            page.update()
        except Exception: pass

    ctrl_est = ft.Row([
        ft.IconButton(ft.Icons.REMOVE, icon_color=VERM, icon_size=18,
            on_click=lambda e: _ajustar(-1),
            style=ft.ButtonStyle(bgcolor="#1C1014", shape=ft.RoundedRectangleBorder(radius=8))),
        f_est,
        ft.IconButton(ft.Icons.ADD, icon_color=VERD, icon_size=18,
            on_click=lambda e: _ajustar(+1),
            style=ft.ButtonStyle(bgcolor="#0D1C12", shape=ft.RoundedRectangleBorder(radius=8))),
        ft.Container(width=8), f_min,
    ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    # ── Galeria de fotos ──────────────────────────────────
    _fotos_novas   = []   # [(path_abs, legenda)] aguardando salvar
    galeria_col    = ft.Column(spacing=8)
    fotos_salvas   = listar_fotos_remedio(remedio["id"]) if remedio and remedio.get("id") else []

    def _rebuild_galeria():
        galeria_col.controls.clear()
        todas = list(fotos_salvas) + [{"id": None, "path": p, "legenda": lg}
                                       for p, lg in _fotos_novas]
        if not todas:
            galeria_col.controls.append(
                ft.Text("Nenhuma foto ainda.", size=11, color=MUT))
            try: page.update()
            except Exception: pass
            return
        linha = ft.Row(wrap=True, spacing=8, run_spacing=8)
        for foto in todas:
            def _excluir(e, f=foto):
                if f.get("id"):
                    excluir_foto_remedio(f["id"])
                    fotos_salvas[:] = [x for x in fotos_salvas if x.get("id") != f["id"]]
                else:
                    _fotos_novas[:] = [(p, l) for p, l in _fotos_novas if p != f["path"]]
                _rebuild_galeria()
            linha.controls.append(ft.Stack([
                ft.Container(
                    content=ft.Image(
                        src=foto["path"].replace("\\", "/"),
                        width=90, height=90, fit=ft.ImageFit.COVER),
                    width=90, height=90, border_radius=8,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    border=ft.border.all(1, BD)),
                ft.Container(
                    content=ft.Icon(ft.Icons.CLOSE, size=14, color=TXT),
                    bgcolor="#CC000000", border_radius=ft.border_radius.only(
                        top_right=8, bottom_left=8),
                    padding=2,
                    right=0, top=0,
                    on_click=_excluir, ink=True),
            ]))
        galeria_col.controls.append(linha)
        try: page.update()
        except Exception: pass

    def _on_foto_selecionada(path_abs):
        path_rel = processar_foto(path_abs, "fotos_remedios")
        if path_rel:
            _fotos_novas.append((path_rel, ""))
            _rebuild_galeria()

    btn_add_foto = criar_btn_seletor_foto(
        page=page,
        on_arquivo=_on_foto_selecionada,
        titulo_menu="Foto da receita / caixa",
        label_btn="Adicionar foto",
    )

    _rebuild_galeria()

    # ── Switch ativo ──────────────────────────────────────
    sw_ativo = ft.Switch(label="Ativo",
        value=bool(remedio.get("ativo",1)) if remedio else True,
        active_color=VERD, label_style=ft.TextStyle(color=SEC, size=13))

    # ── Adesão (se editando) ──────────────────────────────
    widget_adesao = ft.Container()
    if remedio and remedio.get("id"):
        res = resumo_adesao(remedio["id"], 30)
        if res["total"] > 0:
            cor_a = VERD if res["percentual"] >= 80 else (AMAR if res["percentual"] >= 50 else VERM)
            widget_adesao = _card_border(cor_a, ft.Column([
                _label_sec("ADESÃO (30 dias)", cor_a),
                ft.Row([
                    ft.Text(f'{res["percentual"]}%', size=22, color=cor_a,
                            weight=ft.FontWeight.W_700),
                    ft.Column([
                        ft.Text(f'✓ {res["tomou"]} tomou', size=11, color=VERD),
                        ft.Text(f'✗ {res["nao_tomou"]} não tomou', size=11, color=VERM),
                    ], spacing=1, expand=True),
                ], spacing=16),
                ft.ProgressBar(value=res["percentual"]/100, color=cor_a, bgcolor=BD, height=4),
            ], spacing=6))

    # ── Compras (se editando) ─────────────────────────────
    widget_compras = ft.Container()
    if remedio and remedio.get("id"):
        stats   = estatisticas_preco_remedio(remedio["id"])
        compras = listar_compras_remedio(remedio["id"])
        if stats.get("preco_medio") or compras:
            itens_compra = []
            if stats.get("preco_medio"):
                itens_compra.append(ft.Row([
                    ft.Text("Preço médio:", size=11, color=SEC, expand=True),
                    ft.Text(f'R$ {stats["preco_medio"]:.2f}', size=12, color=TXT,
                            weight=ft.FontWeight.W_600),
                ]))
            if stats.get("melhor_preco_valor"):
                itens_compra.append(ft.Row([
                    ft.Text("Melhor preço:", size=11, color=SEC, expand=True),
                    ft.Text(f'R$ {stats["melhor_preco_valor"]:.2f} — {stats["melhor_farmacia"] or "?"}',
                            size=12, color=VERD, weight=ft.FontWeight.W_600),
                ]))
            if stats.get("ultimo_preco"):
                itens_compra.append(ft.Row([
                    ft.Text("Última compra:", size=11, color=SEC, expand=True),
                    ft.Text(f'R$ {stats["ultimo_preco"]:.2f} em {stats["ultima_data"] or "?"}',
                            size=12, color=TXT),
                ]))
            for c in compras[:3]:
                itens_compra.append(ft.Row([
                    ft.Text(c.get("data_compra",""), size=10, color=MUT),
                    ft.Text(c.get("farmacia","?"), size=10, color=ROXO, expand=True),
                    ft.Text(f'{c.get("quantidade",0)}x', size=10, color=SEC),
                    ft.Text(f'R$ {c["preco_total"]:.2f}' if c.get("preco_total") else "-",
                            size=10, color=TXT),
                ], spacing=6))

            widget_compras = _card_border(AZUL, ft.Column(
                [_label_sec("COMPRAS", AZUL)] + itens_compra, spacing=4))

    # ── Registrar compra rápida ───────────────────────────
    btn_registrar_compra = ft.Container()
    if remedio and remedio.get("id"):
        f_cqtd = _campo("Qtd", "1", largura=70, keyboard=ft.KeyboardType.NUMBER)
        f_cval = _campo("R$ unit.", "", largura=100, keyboard=ft.KeyboardType.NUMBER)
        farmacias = listar_farmacias()
        dd_farm = ft.Dropdown(label="Farmácia", bgcolor=CARD, border_color=BD2,
            focused_border_color=AZUL, label_style=ft.TextStyle(color=SEC),
            text_style=ft.TextStyle(color=TXT), border_radius=8, expand=True,
            options=[ft.dropdown.Option(str(f["id"]), f["nome"]) for f in farmacias])
        txt_compra_ok = ft.Text("", size=11, color=VERD)

        def _salvar_compra_rapida(e):
            try:
                qtd = int(f_cqtd.value or 1)
                punit = float((f_cval.value or "0").replace(",","."))
                salvar_compra({
                    "remedio_id": remedio["id"],
                    "farmacia_id": int(dd_farm.value) if dd_farm.value else None,
                    "data_compra": date.today().isoformat(),
                    "quantidade": qtd,
                    "preco_unitario": punit,
                    "preco_total": round(punit * qtd, 2),
                })
                txt_compra_ok.value = f"✓ Compra registrada! +{qtd} unidades"
                f_est.value = str(int(f_est.value or 0) + qtd)
                try: page.update()
                except Exception: pass
            except Exception as ex:
                logger.error("Erro ao registrar compra: %s", str(ex), exc_info=True)
                txt_compra_ok.value = f"Erro: {ex}"; txt_compra_ok.color = VERM
                try: page.update()
                except Exception: pass

        btn_registrar_compra = _card_border(AMAR, ft.Column([
            _label_sec("REGISTRAR COMPRA", AMAR),
            ft.Row([f_cqtd, f_cval, dd_farm], spacing=6),
            ft.Row([
                ft.FilledButton(content=ft.Row([
                    ft.Icon(ft.Icons.SHOPPING_CART, size=14),
                    ft.Text("Registrar", size=12)], spacing=4, tight=True),
                    style=ft.ButtonStyle(bgcolor=AMAR,
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=14, vertical=8)),
                    on_click=_salvar_compra_rapida),
                txt_compra_ok,
            ], spacing=8),
        ], spacing=6))

    # ── Salvar ────────────────────────────────────────────
    txt_erro = ft.Text("", color=VERM, size=12)

    def _salvar(e):
        if not f_nome.value.strip():
            txt_erro.value = "Nome é obrigatório."
            try: page.update()
            except Exception: pass
            return
        try:
            est = int(f_est.value or 0); mn = int(f_min.value or 5)
        except ValueError:
            txt_erro.value = "Estoque deve ser número."
            try: page.update()
            except Exception: pass
            return

        dados = {
            "id": remedio["id"] if remedio else None,
            "nome": f_nome.value.strip(), "dosagem": f_dos.value.strip() or None,
            "frequencia": f_freq.value.strip() or None,
            "data_inicio": f_ini.value.strip() or None,
            "data_fim": f_fim.value.strip() or None,
            "medico_id": int(med_id_sel[0]) if med_id_sel[0] else None,
            "estoque_atual": est, "estoque_minimo": mn,
            "observacoes": f_obs.value.strip() or None,
            "ativo": 1 if sw_ativo.value else 0,
        }
        rid = salvar_remedio(dados)

        horas = [h.strip() for h in (f_horarios.value or "").split(",") if h.strip()]
        salvar_horarios_remedio(rid, horas)

        for path_rel, legenda in _fotos_novas:
            adicionar_foto_remedio(rid, path_rel, legenda)

        voltar_fn()

    # ── Layout da ficha ───────────────────────────────────
    titulo = "Novo Remédio" if is_novo else "Editar Remédio"
    larg = page.width or 0

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
                ft.Icon(ft.Icons.MEDICATION, size=18, color=AMAR),
                ft.Text(titulo, size=16, weight=ft.FontWeight.W_700, color=TXT),
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
                    padding=ft.padding.symmetric(horizontal=18, vertical=10),
                ),
                on_click=_salvar,
            ),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
    )

    campos_col = ft.Column([
        # ── NOME ──────────────────────────────────────────
        _label_sec("IDENTIFICAÇÃO"),
        f_nome,

        # ── DOSAGEM ───────────────────────────────────────
        ft.Container(height=4),
        _label_sec("DOSAGEM"),
        ft.Column([f_dos, sug_dos], spacing=0),

        # ── FREQUÊNCIA + HORÁRIOS (integrados) ───────────
        ft.Container(height=4),
        _label_sec("FREQUÊNCIA DE USO"),
        ft.Column([f_freq, sug_freq], spacing=0),
        bloco_horarios,

        # ── MÉDICO ────────────────────────────────────────
        ft.Container(height=4),
        _label_sec("MÉDICO QUE PRESCREVEU"),
        ft.Column([f_medico, sug_med], spacing=0),

        # ── PERÍODO ───────────────────────────────────────
        ft.Container(height=4),
        _label_sec("PERÍODO DE USO"),
        ft.Row([f_ini, f_fim], spacing=8),

        # ── ESTOQUE ───────────────────────────────────────
        ft.Container(height=4),
        _label_sec("ESTOQUE ATUAL  ·  ALERTA MÍNIMO"),
        ctrl_est,

        # ── GALERIA DE FOTOS ──────────────────────────────
        ft.Container(height=4),
        _label_sec("FOTOS DA RECEITA / CAIXA"),
        btn_add_foto,
        galeria_col,

        # ── ADESÃO / COMPRAS / OBSERVAÇÕES ───────────────
        ft.Container(height=4), widget_adesao,
        ft.Container(height=4), widget_compras,
        ft.Container(height=4), btn_registrar_compra,
        ft.Container(height=4),
        _label_sec("OBSERVAÇÕES"), f_obs,
        ft.Container(height=8), sw_ativo, txt_erro,
    ], spacing=6, scroll=ft.ScrollMode.AUTO)

    if larg > 500:
        corpo_campos = ft.Row([
            ft.Container(expand=True),
            ft.Container(content=campos_col, width=480, padding=ft.padding.all(16)),
            ft.Container(expand=True),
        ], expand=True)
    else:
        corpo_campos = ft.Container(
            content=campos_col, padding=ft.padding.all(16), expand=True)

    corpo_ficha = ft.Column([cabecalho, corpo_campos], expand=True, spacing=0)

    return ft.Container(bgcolor=BG, expand=True, content=corpo_ficha)


# ══════════════════════════════════════════════════════════════
# ABA 2 — LISTA DE REMÉDIOS
# ══════════════════════════════════════════════════════════════

def _lista_remedios(page, abrir_ficha_fn):
    """Retorna lista de controles para a aba Remédios."""
    lista     = ft.Column(spacing=8)
    so_ativos = [True]

    def _carregar():
        lista.controls.clear()
        remedios = listar_remedios(so_ativos=so_ativos[0])
        baixos   = remedios_estoque_baixo()

        if baixos:
            nomes = ", ".join(r["nome"] for r in baixos[:3])
            mais  = f" +{len(baixos)-3}" if len(baixos) > 3 else ""
            lista.controls.append(_card_border(VERM, ft.Row([
                ft.Icon(ft.Icons.WARNING, size=16, color=VERM),
                ft.Text(f"Estoque baixo: {nomes}{mais}", size=12, color=VERM, expand=True),
            ], spacing=8)))

        if not remedios:
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.MEDICATION, size=40, color=MUT),
                    ft.Text("Nenhum remédio cadastrado.", color=SEC, size=13),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=40))
            try: page.update()
            except Exception: pass
            return

        for r in remedios:
            est = r.get("estoque_atual",0) or 0; mn = r.get("estoque_minimo",5) or 5
            cor = _cor_estoque(est, mn); ativo = r.get("ativo",1)

            def _mk(rem=r):
                def _fn(e): abrir_ficha_fn(rem)
                return _fn

            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            content=ft.Icon(ft.Icons.MEDICATION, size=22, color=cor),
                            bgcolor=f"{cor}1A", border_radius=10, width=44, height=44,
                            alignment=ft.alignment.Alignment(0, 0)),
                        ft.Column([
                            ft.Text(r["nome"], size=13, color=TXT, weight=ft.FontWeight.W_600),
                            ft.Row([
                                ft.Text(r.get("dosagem") or "", size=11, color=SEC),
                                ft.Text("·" if r.get("dosagem") and r.get("frequencia") else "", size=11, color=MUT),
                                ft.Text(r.get("frequencia") or "", size=11, color=SEC),
                            ], spacing=4),
                            ft.Text(r.get("medico") or "", size=10, color=ROXO),
                        ], spacing=2, expand=True),
                        ft.Column([
                            ft.Text(str(est), size=16, color=cor, weight=ft.FontWeight.W_700),
                            ft.Text("unid.", size=9, color=MUT),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT, size=16, color=MUT),
                    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(
                        content=ft.ProgressBar(
                            value=min(1.0, est/max(mn*2,1)),
                            color=cor, bgcolor=BD, height=3),
                        border_radius=2) if mn > 0 else ft.Container(),
                ], spacing=6),
                bgcolor=CARD, border_radius=10, opacity=1.0 if ativo else 0.45,
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                border=ft.Border(
                    left=ft.BorderSide(2, cor), top=ft.BorderSide(1, BD),
                    bottom=ft.BorderSide(1, BD), right=ft.BorderSide(1, BD)),
                on_click=_mk(), ink=True))

        try: page.update()
        except Exception: pass

    sw = ft.Switch(label="Só ativos", value=so_ativos[0], active_color=VERD,
                   label_style=ft.TextStyle(color=SEC, size=12))
    def _toggle(e): so_ativos[0] = sw.value; _carregar()
    sw.on_change = _toggle

    _carregar()

    return [
        ft.Container(
            content=ft.Row([
                sw,
                ft.Container(expand=True),
                ft.FilledButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.ADD, size=16),
                        ft.Text("Novo Remédio", size=13),
                    ], spacing=6, tight=True),
                    style=ft.ButtonStyle(
                        bgcolor=VERD,
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=14, vertical=10)),
                    on_click=lambda e: abrir_ficha_fn(None)),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.only(bottom=8)),
        lista,
    ]


# ══════════════════════════════════════════════════════════════
# ABA 3 — FARMÁCIAS + ORÇAMENTO WHATSAPP
# ══════════════════════════════════════════════════════════════

def _conteudo_farmacias(page):
    lista = ft.Column(spacing=8)

    def _carregar():
        lista.controls.clear()
        farmacias = listar_farmacias()

        msg, itens = gerar_mensagem_orcamento()
        if msg and farmacias:
            orcamento_row = ft.Column(spacing=4)
            for f in [f for f in farmacias if f.get("whatsapp")]:
                url = link_whatsapp(f["whatsapp"], msg)
                if url:
                    def _mk_abrir(u=url):
                        def _fn(e): webbrowser.open(u)
                        return _fn
                    orcamento_row.controls.append(ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.SEND, size=14, color=VERD),
                            ft.Text(f["nome"], size=12, color=TXT, expand=True),
                            ft.Text("WhatsApp", size=10, color=VERD),
                        ], spacing=8),
                        bgcolor="#0D1C12", border_radius=8,
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        on_click=_mk_abrir(), ink=True))

            if orcamento_row.controls:
                lista.controls.append(_card_border(VERD, ft.Column([
                    _label_sec("PEDIR ORÇAMENTO (estoque baixo)", VERD),
                    ft.Text(f"{len(itens)} remédio(s) precisando de reposição",
                            size=11, color=SEC),
                    orcamento_row,
                ], spacing=6)))

        # Analisar resposta de orçamento com IA
        f_resposta = _campo("Cole aqui a resposta da farmácia",
                            multiline=True, min_lines=4, hint="Texto, preços, etc.")
        txt_ia_status = ft.Text("", size=11, color=VERD)
        resultado_ia  = ft.Column(spacing=4)

        def _analisar_resposta(e):
            if not f_resposta.value.strip():
                txt_ia_status.value = "Cole a resposta primeiro."
                txt_ia_status.color = VERM
                try: page.update()
                except Exception: pass
                return
            txt_ia_status.value = "Analisando com IA..."
            txt_ia_status.color = AZUL
            try: page.update()
            except Exception: pass

            def _run():
                try:
                    _, itens_p = gerar_mensagem_orcamento()
                    precos = analisar_resposta_orcamento_ia(f_resposta.value, itens_p)
                    page.pubsub.send_all({
                        "_tipo": "farm_ia",
                        "precos": precos,
                    })
                except Exception as ex:
                    logger.error("Erro IA orçamento: %s", str(ex), exc_info=True)
                    page.pubsub.send_all({
                        "_tipo": "farm_ia",
                        "erro": str(ex)[:80],
                    })

            _subscribed = [False]

            def _on_msg(msg):
                if not isinstance(msg, dict) or msg.get("_tipo") != "farm_ia":
                    return
                if "erro" in msg:
                    txt_ia_status.value = msg["erro"]
                    txt_ia_status.color = VERM
                else:
                    precos = msg["precos"]
                    resultado_ia.controls.clear()
                    for p in precos:
                        disp = "✓" if p.get("disponivel") else "✗"
                        cor = VERD if p.get("disponivel") else VERM
                        preco_txt = f'R$ {p["preco"]:.2f}' if p.get("preco") else "sem preço"
                        resultado_ia.controls.append(ft.Row([
                            ft.Text(disp, size=12, color=cor),
                            ft.Text(p.get("nome_pedido","?"), size=12, color=TXT, expand=True),
                            ft.Text(preco_txt, size=12, color=cor, weight=ft.FontWeight.W_600),
                        ], spacing=8))
                    txt_ia_status.value = f"✓ {len(precos)} itens analisados"
                    txt_ia_status.color = VERD
                try: page.update()
                except Exception: pass

            if not _subscribed[0]:
                page.pubsub.subscribe(_on_msg)
                _subscribed[0] = True

            threading.Thread(target=_run, daemon=True).start()

        lista.controls.append(_card_border(ROXO, ft.Column([
            _label_sec("ANALISAR RESPOSTA DE ORÇAMENTO", ROXO),
            f_resposta,
            ft.Row([
                ft.FilledButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.PSYCHOLOGY, size=14),
                        ft.Text("Analisar com IA", size=12),
                    ], spacing=4, tight=True),
                    style=ft.ButtonStyle(
                        bgcolor=ROXO,
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=14, vertical=8)),
                    on_click=_analisar_resposta),
                txt_ia_status,
            ], spacing=8),
            resultado_ia,
        ], spacing=6)))

        lista.controls.append(ft.Container(
            content=ft.Text("FARMÁCIAS CADASTRADAS", size=10, color=MUT,
                            weight=ft.FontWeight.W_700),
            padding=ft.padding.only(top=12, left=4, bottom=4)))

        if not farmacias:
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.STOREFRONT, size=40, color=MUT),
                    ft.Text("Nenhuma farmácia cadastrada.", color=SEC, size=13),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=30))

        for f in farmacias:
            canais = []
            if f.get("whatsapp"): canais.append("WhatsApp")
            if f.get("site"):     canais.append("Site")
            if f.get("app"):      canais.append("App")
            if f.get("delivery"): canais.append("Delivery")

            lista.controls.append(ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.STOREFRONT, size=20,
                            color=AZUL if f.get("preferida") else SEC),
                        bgcolor=f"{AZUL}1A" if f.get("preferida") else f"{SEC}1A",
                        border_radius=10, width=40, height=40,
                        alignment=ft.alignment.Alignment(0, 0)),
                    ft.Column([
                        ft.Row([
                            ft.Text(f["nome"], size=13, color=TXT, weight=ft.FontWeight.W_600),
                            _badge("⭐ Preferida", AMAR) if f.get("preferida") else ft.Container(),
                        ], spacing=6),
                        ft.Text(" · ".join(canais) if canais else "", size=10, color=MUT),
                        ft.Text(f.get("endereco") or "", size=10, color=SEC),
                    ], spacing=1, expand=True),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, size=16, color=MUT),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD, border_radius=10, ink=True,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                border=ft.border.all(1, BD),
                on_click=lambda e, farm=f: _abrir_ficha_farm(farm)))

        try: page.update()
        except Exception: pass

    def _abrir_ficha_farm(farm):
        is_nova = farm is None
        f_n = _campo("Nome *", farm["nome"] if farm else "")
        f_e = _campo("Endereço", farm.get("endereco","") if farm else "")
        f_t = _campo("Telefone", farm.get("telefone","") if farm else "", largura=160)
        f_w = _campo("WhatsApp", farm.get("whatsapp","") if farm else "", largura=160,
                     hint="5527999998888")
        f_s = _campo("Site", farm.get("site","") if farm else "")
        f_a = _campo("App", farm.get("app","") if farm else "")
        sw_del  = ft.Switch(label="Delivery", value=bool(farm.get("delivery",0)) if farm else False,
                            active_color=VERD, label_style=ft.TextStyle(color=SEC, size=12))
        sw_pref = ft.Switch(label="Preferida", value=bool(farm.get("preferida",0)) if farm else False,
                            active_color=AMAR, label_style=ft.TextStyle(color=SEC, size=12))
        f_obs_f = _campo("Observações", farm.get("observacoes","") if farm else "",
                         multiline=True, min_lines=2)

        def _salvar_farm(e):
            if not f_n.value.strip(): return
            salvar_farmacia({
                "id": farm["id"] if farm else None,
                "nome": f_n.value.strip(), "endereco": f_e.value.strip() or None,
                "telefone": f_t.value.strip() or None, "whatsapp": f_w.value.strip() or None,
                "site": f_s.value.strip() or None, "app": f_a.value.strip() or None,
                "delivery": 1 if sw_del.value else 0, "preferida": 1 if sw_pref.value else 0,
                "observacoes": f_obs_f.value.strip() or None,
            })
            _carregar()

        lista.controls.clear()
        lista.controls.append(ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Row([
                    ft.TextButton(
                        content=ft.Row([
                            ft.Icon(ft.Icons.ARROW_BACK, size=16),
                            ft.Text("Voltar", size=13),
                        ], spacing=4, tight=True),
                        on_click=lambda e: _carregar()),
                    ft.Text("Nova Farmácia" if is_nova else "Editar Farmácia",
                            size=16, weight=ft.FontWeight.W_700, color=TXT, expand=True),
                    ft.FilledButton(
                        content=ft.Row([
                            ft.Icon(ft.Icons.SAVE, size=16),
                            ft.Text("Salvar", size=13),
                        ], spacing=6, tight=True),
                        style=ft.ButtonStyle(
                            bgcolor=VERD,
                            shape=ft.RoundedRectangleBorder(radius=8),
                            padding=ft.padding.symmetric(horizontal=14, vertical=10)),
                        on_click=_salvar_farm),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                f_n, f_e, ft.Row([f_t, f_w], spacing=8), f_s, f_a,
                ft.Row([sw_del, sw_pref], spacing=16), f_obs_f,
            ], spacing=8, scroll=ft.ScrollMode.AUTO),
            padding=ft.padding.all(16)))
        try: page.update()
        except Exception: pass

    _carregar()

    return [
        ft.Container(
            content=ft.Row([
                ft.Container(expand=True),
                ft.FilledButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.ADD, size=16),
                        ft.Text("Nova Farmácia", size=13),
                    ], spacing=6, tight=True),
                    style=ft.ButtonStyle(
                        bgcolor=AZUL,
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=14, vertical=10)),
                    on_click=lambda e: _abrir_ficha_farm(None)),
            ]),
            padding=ft.padding.symmetric(horizontal=0, vertical=4)),
        lista,
    ]


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL
# ══════════════════════════════════════════════════════════════

def criar_tela_remedios(page: ft.Page, voltar_fn):
    """
    Navegação interna via page.controls (igual _navegar do app.py).
    criar_tela_remedios retorna a tela principal.
    Ficha de remédio substitui page.controls[0] via _ir_ficha/_voltar.
    """
    logger.info("[REMEDIOS] criar_tela_remedios iniciado")

    try:
        larg = page.width or 800
    except Exception:
        larg = 800

    # ── Estrutura da tela principal (construída uma vez) ──────
    aba_ativa  = [1]   # começa na aba Remédios
    barra_abas = ft.Row(spacing=0)
    area       = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    ABAS = [
        (0, ft.Icons.TODAY,       "Hoje",      AZUL),
        (1, ft.Icons.MEDICATION,  "Remédios",  AMAR),
        (2, ft.Icons.STOREFRONT,  "Farmácias", VERD),
    ]

    def _ir_ficha(remedio):
        logger.info("[REMEDIOS] _ir_ficha: %s", remedio["nome"] if remedio else "NOVO")
        ficha = _build_ficha_remedio(page, remedio, _voltar_lista)
        page.controls.clear()
        page.controls.append(ficha)
        page.update()

    def _voltar_lista():
        logger.info("[REMEDIOS] _voltar_lista")
        _rebuild_conteudo()
        page.controls.clear()
        page.controls.append(tela_principal)
        page.update()

    def _rebuild_abas():
        barra_abas.controls.clear()
        for idx, icone, label, cor in ABAS:
            ativo = idx == aba_ativa[0]
            def _click(e, i=idx):
                logger.info("[REMEDIOS] click aba %s", i)
                aba_ativa[0] = i
                _rebuild_abas()
                _rebuild_conteudo()
                page.update()
            barra_abas.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon(icone, size=16, color=cor if ativo else SEC),
                    ft.Text(label, size=10,
                            color=cor if ativo else SEC,
                            weight=ft.FontWeight.W_600 if ativo
                                   else ft.FontWeight.W_400),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=2, tight=True),
                expand=True,
                padding=ft.padding.symmetric(vertical=10),
                border=ft.Border(
                    bottom=ft.BorderSide(2, cor if ativo else "#00000000")),
                on_click=_click,
            ))

    def _rebuild_conteudo():
        logger.info("[REMEDIOS] _rebuild_conteudo aba=%s", aba_ativa[0])
        area.controls.clear()
        try:
            if aba_ativa[0] == 0:
                controles = _build_aba_hoje(page)
            elif aba_ativa[0] == 1:
                controles = _lista_remedios(page, _ir_ficha)
            else:
                controles = _conteudo_farmacias(page)
            area.controls.extend(controles)
            logger.info("[REMEDIOS] %s controles carregados na area", len(area.controls))
        except Exception as ex:
            logger.error("[REMEDIOS] erro _rebuild_conteudo: %s", ex, exc_info=True)
            area.controls.append(ft.Text(f"Erro interno: {ex}", color=VERM, size=12))

    # ── Montar estrutura principal ────────────────────────────
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
                ft.Icon(ft.Icons.MEDICATION, size=20, color=AMAR),
                ft.Text("Remédios", size=18,
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
        ft.Container(content=area, padding=ft.padding.all(16), expand=True),
    ], expand=True)

    if larg > 500:
        conteudo_final = ft.Row([
            ft.Container(expand=True),
            ft.Container(content=corpo, width=480),
            ft.Container(expand=True),
        ], expand=True)
    else:
        conteudo_final = corpo

    tela_principal = ft.Container(bgcolor=BG, expand=True, content=conteudo_final)
    logger.info("[REMEDIOS] tela_principal montada, retornando")
    return tela_principal
