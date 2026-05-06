# -*- coding: utf-8 -*-
# Prontuario | telas/tela_remedios.py
import logging
import re
import flet as ft
import threading
import webbrowser
from datetime import date, datetime, timedelta
from shared.layout import Layout
from dados.model_prontuario import (
    listar_remedios, salvar_remedio,
    remedios_estoque_baixo, listar_medicos, salvar_medico,
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
from utils.foto_picker import (
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


def _add_months(dt: date, meses: int) -> date:
    import calendar
    mes = dt.month + meses
    ano = dt.year + (mes - 1) // 12
    mes = (mes - 1) % 12 + 1
    max_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(dt.day, max_dia))


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
                    ft.Icon("check_circle_outline_rounded", size=48, color=VERD),
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
                    ft.Icon("today_rounded", size=16, color=AZUL),
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
                        ft.Icon("access_time_rounded", size=14, color=AMAR),
                        ft.Text(hora_atual, size=14, color=AMAR,
                                weight=ft.FontWeight.W_700),
                    ], spacing=6),
                    padding=ft.padding.only(top=14, left=4, bottom=2)))

            status = t["status"]
            if status == "tomou":
                cor = VERD; icone = "check_circle_rounded"; opa = 0.55
            elif status == "nao_tomou":
                cor = VERM; icone = "cancel_rounded"; opa = 0.55
            else:
                cor = AMAR; icone = "circle_outlined_rounded"; opa = 1.0

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
                    ft.IconButton("check_rounded", icon_color=VERD, icon_size=22,
                        on_click=_mk_tomou(),
                        style=ft.ButtonStyle(bgcolor="#0D1C12",
                            shape=ft.RoundedRectangleBorder(radius=8))),
                    ft.IconButton("close_rounded", icon_color=VERM, icon_size=22,
                        on_click=_mk_nao(),
                        style=ft.ButtonStyle(bgcolor="#1C1014",
                            shape=ft.RoundedRectangleBorder(radius=8))),
                ]
            else:
                botoes.controls = [
                    ft.Container(content=ft.Text("Desfazer", size=10, color=MUT),
                                  padding=ft.padding.symmetric(horizontal=8, vertical=8),
                        ink=True,
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


# (label, intervalo_horas, icone)
# intervalo > 0  → horário fixo, calcula automaticamente
# intervalo = -1 → refeição/evento, sem horário fixo
_FREQ_SUGESTOES = [
    # ── Por horario ──────────────────────────────────────────
    ("1x ao dia",               24, "schedule_rounded"),
    ("2x ao dia",               12, "schedule_rounded"),
    ("3x ao dia",                8, "schedule_rounded"),
    ("4x ao dia",                6, "schedule_rounded"),
    ("A cada 4 horas",           4, "schedule_rounded"),
    ("A cada 6 horas",           6, "schedule_rounded"),
    ("A cada 8 horas",           8, "schedule_rounded"),
    ("A cada 12 horas",         12, "schedule_rounded"),
    # ── Por refeicao ─────────────────────────────────────────
    ("Ao acordar",              -1, "wb_sunny_rounded"),
    ("Em jejum (antes do cafe)",-1, "free_breakfast_rounded"),
    ("Apos o cafe da manha",    -1, "free_breakfast_rounded"),
    ("No lanche da manha",      -1, "lunch_dining_rounded"),
    ("Antes do almoco",         -1, "restaurant_rounded"),
    ("Apos o almoco",           -1, "restaurant_rounded"),
    ("No lanche da tarde",      -1, "lunch_dining_rounded"),
    ("Antes do jantar",         -1, "dinner_dining_rounded"),
    ("Apos o jantar",           -1, "dinner_dining_rounded"),
    ("Antes de dormir",         -1, "bedtime_rounded"),
    ("Apos as refeicoes",       -1, "restaurant_rounded"),
    ("Conforme necessidade",    -1, "healing_rounded"),
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

    # ── Médico (autocomplete + cadastro rapido) ───────────
    medicos    = listar_medicos(so_ativos=True)
    _medicos   = list(medicos)  # copia mutavel local
    med_id_sel = [str(remedio.get("medico_id","")) if remedio and remedio.get("medico_id") else None]

    nome_med_ini = ""
    if med_id_sel[0]:
        for _m in _medicos:
            if str(_m["id"]) == med_id_sel[0]:
                nome_med_ini = _m["nome"]
                break

    f_medico = _campo("Medico prescritor",
                      nome_med_ini,
                      hint="Digite para buscar ou cadastrar…")
    sug_med  = ft.Column(spacing=2, visible=False)

    def _cadastrar_medico_rapido(nome_inicial=""):
        ref_ov = [None]
        f_med_nome = _campo("Nome do medico *", nome_inicial)
        f_med_esp  = _campo("Especialidade", hint="ex: Cardiologia, Clínico Geral…")

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        def _salvar_med(e):
            nome_str = (f_med_nome.value or "").strip()
            if not nome_str:
                return
            novo_id = salvar_medico({
                "id": None,
                "nome": nome_str,
                "especialidade": (f_med_esp.value or "").strip() or None,
                "ativo": 1,
            })
            novo = {"id": novo_id, "nome": nome_str,
                    "especialidade": (f_med_esp.value or "").strip()}
            _medicos.append(novo)
            f_medico.value = nome_str
            med_id_sel[0]  = str(novo_id)
            sug_med.controls.clear()
            sug_med.visible = False
            _fechar()

        btn_c = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{SEC}22", ink=True,
        )
        btn_c.on_click = _fechar
        btn_s = ft.Container(
            content=ft.Text("Cadastrar", size=13, color=VERD,
                            weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8, bgcolor=f"{VERD}22", ink=True,
        )
        btn_s.on_click = _salvar_med

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Novo Medico", size=15, color=TXT,
                            weight=ft.FontWeight.W_700, text_align="center"),
                    ft.Container(height=6),
                    f_med_nome, f_med_esp,
                    ft.Container(height=8),
                    ft.Row([btn_c, btn_s], spacing=8,
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
        try: page.update()
        except Exception: pass

    def _filtrar_med(e):
        termo = (f_medico.value or "").strip().upper()
        sug_med.controls.clear()
        if not termo:
            sug_med.visible = False; med_id_sel[0] = None
            try: page.update()
            except Exception: pass
            return
        encontrados = [m for m in _medicos if termo in m["nome"].upper()][:6]
        for m in encontrados:
            def _sel(e, med=m):
                f_medico.value = med["nome"]; med_id_sel[0] = str(med["id"])
                sug_med.controls.clear(); sug_med.visible = False
                try: page.update()
                except Exception: pass
            esp = m.get("especialidade") or ""
            item = ft.Container(
                content=ft.Row([
                    ft.Icon("person_rounded", size=14, color=ROXO),
                    ft.Column([
                        ft.Text(m["nome"], size=13, color=TXT),
                        ft.Text(esp, size=10, color=MUT) if esp else ft.Container(),
                    ], spacing=0, expand=True),
                ], spacing=8),
                bgcolor=BD, border_radius=6,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                ink=True,
            )
            item.on_click = _sel
            sug_med.controls.append(item)
        # botao "Cadastrar" se nao encontrado
        btn_cad = ft.Container(
            content=ft.Row([
                ft.Icon("person_add_rounded", size=14, color=VERD),
                ft.Text(f'Cadastrar "{(f_medico.value or "").strip()}"',
                        size=12, color=VERD),
            ], spacing=8),
            bgcolor=f"{VERD}18", border_radius=6,
            padding=ft.padding.symmetric(horizontal=12, vertical=9),
            ink=True,
        )
        btn_cad.on_click = lambda e: _cadastrar_medico_rapido(
            (f_medico.value or "").strip())
        sug_med.controls.append(btn_cad)
        sug_med.visible = True
        try: page.update()
        except Exception: pass
    f_medico.on_change = _filtrar_med

    # ── Nome + Principio Ativo ────────────────────────────
    f_nome = _campo("Nome do remedio/suplemento *", remedio["nome"] if remedio else "")
    f_pa   = _campo("Principio ativo (generico)",
                    remedio.get("principio_ativo","") if remedio else "",
                    hint="ex: losartana, omeprazol, whey protein…")

    # ── Tipo (remedio / suplemento) + Prescrito ───────────
    _tipo_ini      = remedio.get("tipo","remedio") == "suplemento" if remedio else False
    _prescrito_ini = bool(remedio.get("prescrito", 0)) if remedio else False

    sw_tipo = ft.Switch(
        label="Suplemento (nao prescrito por medico por default)",
        value=_tipo_ini, active_color=ROXO, label_style=ft.TextStyle(color=SEC, size=12),
    )
    sw_prescrito = ft.Switch(
        label="Prescrito pelo medico",
        value=_prescrito_ini, active_color=AZUL, label_style=ft.TextStyle(color=SEC, size=12),
    )
    bloco_medico = ft.Container(
        content=ft.Column([
            ft.Container(height=4),
            _label_sec("MEDICO PRESCRITOR"),
            ft.Column([f_medico, sug_med], spacing=0),
        ], spacing=6),
        visible=_prescrito_ini,
    )

    def _on_prescrito(e):
        bloco_medico.visible = sw_prescrito.value
        # Se desativar prescrito, limpar medico
        if not sw_prescrito.value:
            f_medico.value = ""
            med_id_sel[0] = None
        try: page.update()
        except Exception: pass
    sw_prescrito.on_change = _on_prescrito

    def _on_tipo(e):
        # Suplemento raramente e prescrito — sugerir desligar prescrito
        if sw_tipo.value and sw_prescrito.value:
            pass  # manter a escolha do usuario
        try: page.update()
        except Exception: pass
    sw_tipo.on_change = _on_tipo

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
                    ft.Icon("info_outline_rounded", size=14, color=SEC),
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
                        ft.Icon("edit_note_rounded", size=13, color=MUT),
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
        iv = None
        for label, fiv, _ico in _FREQ_SUGESTOES:
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
        itens = [(lbl, iv, ico) for lbl, iv, ico in _FREQ_SUGESTOES
                 if not termo or termo in lbl.upper()]
        ultimo_grupo = None
        for label, iv, ico in itens:
            grupo = "horario" if iv > 0 else "refeicao"
            if grupo != ultimo_grupo:
                ultimo_grupo = grupo
                sep_lbl = "POR HORARIO" if grupo == "horario" else "POR REFEICAO"
                sug_freq.controls.append(ft.Container(
                    content=ft.Text(sep_lbl, size=9, color=MUT,
                                    weight=ft.FontWeight.W_700),
                    padding=ft.padding.only(left=12, top=6, bottom=2),
                ))
            cor = CORAL if iv > 0 else SEC
            def _sel(e, lbl=label):
                f_freq.value = lbl
                sug_freq.controls.clear(); sug_freq.visible = False
                _aplicar_freq(lbl)
            item = ft.Container(
                content=ft.Row([
                    ft.Icon(ico, size=14, color=cor),
                    ft.Text(label, size=13, color=cor),
                ], spacing=8),
                bgcolor=BD, border_radius=6,
                padding=ft.padding.symmetric(horizontal=12, vertical=9),
                ink=True,
            )
            item.on_click = _sel
            sug_freq.controls.append(item)
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
    _data_fim_raw = remedio.get("data_fim","") if remedio else ""
    _continuo_ini = (_data_fim_raw == "continuo")

    f_ini = _campo("Inicio", remedio.get("data_inicio","") if remedio else "",
                   hint="DD/MM/AAAA", largura=140)
    f_fim = _campo("Fim previsto", "" if _continuo_ini else _data_fim_raw,
                   hint="DD/MM/AAAA", largura=140)
    _mask_data(f_ini)
    _mask_data(f_fim)

    sw_continuo = ft.Switch(
        label="Uso continuo",
        value=_continuo_ini,
        active_color=VERD,
        label_style=ft.TextStyle(color=SEC, size=12),
    )
    row_fim = ft.Row([f_fim], visible=not _continuo_ini)

    def _on_continuo(e):
        row_fim.visible = not sw_continuo.value
        if sw_continuo.value:
            f_fim.value = ""
        try: page.update()
        except Exception: pass
    sw_continuo.on_change = _on_continuo

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
        ft.IconButton("remove_rounded", icon_color=VERM, icon_size=18,
            on_click=lambda e: _ajustar(-1),
            style=ft.ButtonStyle(bgcolor="#1C1014", shape=ft.RoundedRectangleBorder(radius=8))),
        f_est,
        ft.IconButton("add_rounded", icon_color=VERD, icon_size=18,
            on_click=lambda e: _ajustar(+1),
            style=ft.ButtonStyle(bgcolor="#0D1C12", shape=ft.RoundedRectangleBorder(radius=8))),
        ft.Container(width=8), f_min,
    ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    # ── Galeria de fotos (separada por tipo) ─────────────
    # _fotos_novas: [(path_rel, legenda, tipo, data_validade)]
    _fotos_novas  = []
    galeria_rem   = ft.Column(spacing=8)   # tipo='remedio'
    galeria_rec   = ft.Column(spacing=8)   # tipo='receita'
    _id_salvas    = listar_fotos_remedio(remedio["id"]) if remedio and remedio.get("id") else []
    fotos_salvas_rem = [f for f in _id_salvas if (f.get("tipo") or "remedio") == "remedio"]
    fotos_salvas_rec = [f for f in _id_salvas if (f.get("tipo") or "remedio") == "receita"]

    def _mini_grid(fotos_salvas_list, fotos_novas_list, galeria_col, tipo_filtro):
        galeria_col.controls.clear()
        todas = list(fotos_salvas_list) + [
            {"id": None, "path": p, "legenda": lg, "tipo": tp, "data_validade": dv}
            for p, lg, tp, dv in fotos_novas_list if tp == tipo_filtro
        ]
        if not todas:
            galeria_col.controls.append(ft.Text("Nenhuma foto.", size=11, color=MUT))
            return
        linha = ft.Row(wrap=True, spacing=8, run_spacing=8)
        for foto in todas:
            def _excluir(e, f=foto, sl=fotos_salvas_list):
                if f.get("id"):
                    excluir_foto_remedio(f["id"])
                    sl[:] = [x for x in sl if x.get("id") != f["id"]]
                else:
                    _fotos_novas[:] = [(p, l, t, d) for p, l, t, d in _fotos_novas
                                       if p != f["path"]]
                _rebuild_galerias()
            linha.controls.append(ft.Stack([
                ft.Container(
                    content=ft.Image(
                        src=foto["path"].replace("\\", "/"),
                        width=90, height=90, fit=ft.ImageFit.COVER),
                    width=90, height=90, border_radius=8,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    border=ft.border.all(1, BD)),
                ft.Container(
                    content=ft.Icon("close_rounded", size=14, color=TXT),
                    bgcolor="#CC000000", border_radius=ft.border_radius.only(
                        top_right=8, bottom_left=8),
                    padding=2, right=0, top=0,
                    on_click=_excluir, ink=True),
            ]))
        galeria_col.controls.append(linha)

    def _rebuild_galerias():
        _mini_grid(fotos_salvas_rem, _fotos_novas, galeria_rem, "remedio")
        _mini_grid(fotos_salvas_rec, _fotos_novas, galeria_rec, "receita")
        try: page.update()
        except Exception: pass

    def _on_foto_remedio(path_abs):
        path_rel = processar_foto(path_abs, "fotos_remedios")
        if path_rel:
            _fotos_novas.append((path_rel, "", "remedio", None))
            _rebuild_galerias()

    def _on_foto_receita(path_abs):
        path_rel = processar_foto(path_abs, "fotos_remedios")
        if path_rel:
            _fotos_novas.append((path_rel, "", "receita", validade_data[0] or None))
            _rebuild_galerias()

    # Validade da receita — chips com calculo automatico
    _VALID_OPCOES = [
        ("unica",    "Unica",    None),
        ("continua", "Continua", None),
        ("6meses",   "6 meses",  6),
        ("1ano",     "1 ano",    12),
    ]
    validade_sel  = [None]
    validade_data = [""]
    chips_validade    = ft.Row(spacing=6, wrap=True)
    txt_data_validade = ft.Text("", size=11, color=VERD)

    def _rebuild_chips_validade():
        chips_validade.controls.clear()
        for key, label, meses in _VALID_OPCOES:
            ativo = validade_sel[0] == key
            cor   = AZUL if ativo else MUT
            def _on_val(e, k=key, m=meses, lb=label):
                validade_sel[0] = k
                if m is not None:
                    dt_fim = _add_months(date.today(), m)
                    validade_data[0]          = dt_fim.strftime("%d/%m/%Y")
                    txt_data_validade.value   = f"Validade: {validade_data[0]}"
                    txt_data_validade.color   = VERD
                else:
                    validade_data[0]          = k
                    txt_data_validade.value   = f"Receita {lb.lower()}"
                    txt_data_validade.color   = SEC if k == "continua" else AMAR
                _rebuild_chips_validade()
            chips_validade.controls.append(ft.Container(
                content=ft.Text(label, size=11, color=cor, weight=ft.FontWeight.W_600),
                bgcolor=f"{AZUL}22" if ativo else BD, border_radius=12,
                padding=ft.padding.symmetric(horizontal=10, vertical=5),
                border=ft.border.all(1, cor), ink=True, on_click=_on_val,
            ))
        try: page.update()
        except Exception: pass

    _rebuild_chips_validade()

    btn_add_foto = criar_btn_seletor_foto(
        page=page,
        on_arquivo=_on_foto_remedio,
        titulo_menu="Foto do remedio / caixa",
        label_btn="Adicionar foto",
    )

    btn_add_receita = criar_btn_seletor_foto(
        page=page,
        on_arquivo=_on_foto_receita,
        titulo_menu="Foto da receita",
        label_btn="Adicionar receita",
    )

    _rebuild_galerias()

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

        _btn_compra = ft.Container(
            content=ft.Row([
                ft.Icon("shopping_cart_rounded", size=14, color=BG),
                ft.Text("Registrar", size=12, color=BG),
            ], spacing=4, tight=True),
            bgcolor=AMAR, border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
        )
        _btn_compra.on_click = _salvar_compra_rapida

        btn_registrar_compra = _card_border(AMAR, ft.Column([
            _label_sec("REGISTRAR COMPRA", AMAR),
            ft.Row([f_cqtd, f_cval, dd_farm], spacing=6),
            ft.Row([
                _btn_compra,
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

        data_fim_val = "continuo" if sw_continuo.value else (f_fim.value.strip() or None)

        # Auto-cadastra medico digitado mas nao selecionado da lista
        if sw_prescrito.value and not med_id_sel[0] and (f_medico.value or "").strip():
            novo_mid = salvar_medico({"nome": f_medico.value.strip()})
            med_id_sel[0] = novo_mid

        dados = {
            "id": remedio["id"] if remedio else None,
            "nome": f_nome.value.strip(),
            "dosagem": f_dos.value.strip() or None,
            "frequencia": f_freq.value.strip() or None,
            "data_inicio": f_ini.value.strip() or None,
            "data_fim": data_fim_val,
            "medico_id": int(med_id_sel[0]) if med_id_sel[0] and sw_prescrito.value else None,
            "estoque_atual": est, "estoque_minimo": mn,
            "observacoes": f_obs.value.strip() or None,
            "ativo": 1 if sw_ativo.value else 0,
            "principio_ativo": f_pa.value.strip() or None,
            "tipo": "suplemento" if sw_tipo.value else "remedio",
            "prescrito": 1 if sw_prescrito.value else 0,
        }
        rid = salvar_remedio(dados)

        horas = [h.strip() for h in (f_horarios.value or "").split(",") if h.strip()]
        salvar_horarios_remedio(rid, horas)

        for path_rel, legenda, tipo_foto, data_val in _fotos_novas:
            adicionar_foto_remedio(rid, path_rel, legenda, tipo_foto, data_val)

        voltar_fn()

    # ── Layout da ficha ───────────────────────────────────
    titulo = "Nova Medicacao" if is_novo else "Editar Medicacao"
    lay    = Layout(page)

    cabecalho = lay.criar_cabecalho(
        titulo, voltar_fn,
        icone_titulo="medication_rounded",
        cor_titulo=AMAR,
    )

    btn_salvar_fundo = ft.Container(
        content=ft.Row([
            ft.Icon("save_rounded", size=16, color=BG),
            ft.Text("Salvar", size=14, color=BG, weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=VERD, border_radius=10, ink=True,
        padding=ft.padding.symmetric(vertical=14),
        alignment=ft.alignment.Alignment(0, 0),
    )
    btn_salvar_fundo.on_click = _salvar

    campos_col = ft.Column([
        # ── NOME + PRINCIPIO ATIVO ────────────────────────
        _label_sec("IDENTIFICACAO"),
        f_nome,
        f_pa,
        ft.Row([sw_tipo], spacing=8),
        ft.Row([sw_prescrito], spacing=8),

        # ── DOSAGEM ───────────────────────────────────────
        ft.Container(height=4),
        _label_sec("DOSAGEM"),
        ft.Column([f_dos, sug_dos], spacing=0),

        # ── FREQUÊNCIA + HORÁRIOS (integrados) ───────────
        ft.Container(height=4),
        _label_sec("FREQUÊNCIA DE USO"),
        ft.Column([f_freq, sug_freq], spacing=0),
        bloco_horarios,

        # ── MÉDICO (visivel so se prescrito) ──────────────
        bloco_medico,

        # ── PERÍODO ───────────────────────────────────────
        ft.Container(height=4),
        _label_sec("PERIODO DE USO"),
        ft.Row([sw_continuo], spacing=8),
        ft.Row([f_ini], spacing=8),
        row_fim,

        # ── ESTOQUE ───────────────────────────────────────
        ft.Container(height=4),
        _label_sec("ESTOQUE ATUAL  ·  ALERTA MÍNIMO"),
        ctrl_est,

        # ── FOTOS DO REMEDIO/CAIXA ────────────────────────
        ft.Container(height=4),
        _label_sec("FOTO DO REMEDIO / CAIXA"),
        btn_add_foto,
        galeria_rem,

        # ── RECEITAS/PRESCRICOES ──────────────────────────
        ft.Container(height=4),
        _label_sec("RECEITAS / PRESCRICOES"),
        _label_sec("VALIDADE DA RECEITA", SEC),
        chips_validade,
        txt_data_validade,
        btn_add_receita,
        galeria_rec,

        # ── ADESÃO / COMPRAS / OBSERVAÇÕES ───────────────
        ft.Container(height=4), widget_adesao,
        ft.Container(height=4), widget_compras,
        ft.Container(height=4), btn_registrar_compra,
        ft.Container(height=4),
        _label_sec("OBSERVAÇÕES"), f_obs,
        ft.Container(height=8), sw_ativo, txt_erro,
        ft.Container(height=16),
        btn_salvar_fundo,
        ft.Container(height=16),
    ], spacing=6, scroll=ft.ScrollMode.AUTO)

    corpo_ficha = lay.criar_corpo(
        cabecalho, campos_col,
        padding_area=ft.padding.all(16),
    )
    return lay.wrap(ft.Container(bgcolor=BG, expand=True, content=corpo_ficha))


# ══════════════════════════════════════════════════════════════
# ABA 2 — LISTA DE REMÉDIOS
# ══════════════════════════════════════════════════════════════

def _lista_remedios(page, abrir_ficha_fn):
    """Retorna lista de controles para a aba Remedios."""
    lista     = ft.Column(spacing=8)
    so_ativos = [True]
    tipo_sel  = [None]   # None=Todos, "remedio", "suplemento"

    _TIPOS = [
        (None,         "Todos"),
        ("remedio",    "Remedio"),
        ("suplemento", "Supl"),
    ]

    chips_row = ft.Row(spacing=6, wrap=False)

    def _rebuild_chips():
        chips_row.controls.clear()
        for tp, label in _TIPOS:
            ativo = tipo_sel[0] == tp
            cor   = AZUL if ativo else MUT
            chips_row.controls.append(ft.Container(
                content=ft.Text(label, size=11, color=cor, weight=ft.FontWeight.W_600),
                bgcolor=f"{AZUL}22" if ativo else BD,
                border_radius=12,
                padding=ft.padding.symmetric(horizontal=10, vertical=5),
                border=ft.Border(
                    top=ft.BorderSide(1, cor), bottom=ft.BorderSide(1, cor),
                    left=ft.BorderSide(1, cor), right=ft.BorderSide(1, cor)),
                ink=True,
                on_click=lambda e, t=tp: _set_tipo(t),
            ))

    def _set_tipo(tp):
        tipo_sel[0] = tp
        _rebuild_chips()
        _carregar()

    def _carregar():
        lista.controls.clear()
        remedios = listar_remedios(so_ativos=so_ativos[0], tipo=tipo_sel[0])
        baixos   = remedios_estoque_baixo()

        if baixos:
            nomes = ", ".join(r["nome"] for r in baixos[:3])
            mais  = f" +{len(baixos)-3}" if len(baixos) > 3 else ""
            lista.controls.append(_card_border(VERM, ft.Row([
                ft.Icon("warning_rounded", size=16, color=VERM),
                ft.Text(f"Estoque baixo: {nomes}{mais}", size=12, color=VERM, expand=True),
            ], spacing=8)))

        if not remedios:
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("medication_rounded", size=40, color=MUT),
                    ft.Text("Nenhum remedio cadastrado.", color=SEC, size=13),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=40))
            try: page.update()
            except Exception: pass
            return

        for r in remedios:
            est = r.get("estoque_atual",0) or 0; mn = r.get("estoque_minimo",5) or 5
            cor = _cor_estoque(est, mn); ativo = r.get("ativo",1)
            foto = r.get("foto_thumb")
            med_txt  = r.get("medico") or ""
            prescrito = r.get("prescrito", 0)

            def _mk(rem=r):
                def _fn(e): abrir_ficha_fn(rem)
                return _fn

            if foto:
                icone_widget = ft.Container(
                    content=ft.Image(
                        src=foto.replace("\\", "/"),
                        width=44, height=44, fit=ft.ImageFit.COVER),
                    width=44, height=44, border_radius=10,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    border=ft.border.all(1, BD))
            else:
                icone_widget = ft.Container(
                    content=ft.Icon("medication_rounded", size=22, color=cor),
                    bgcolor=f"{cor}1A", border_radius=10, width=44, height=44,
                    alignment=ft.alignment.Alignment(0, 0))

            if prescrito and med_txt:
                med_row = ft.Text(med_txt, size=10, color=ROXO)
            elif not prescrito:
                med_row = ft.Text("Sem prescricao medica", size=10, color=MUT)
            else:
                med_row = ft.Container()

            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        icone_widget,
                        ft.Column([
                            ft.Row([
                                ft.Text(r["nome"], size=13, color=TXT, weight=ft.FontWeight.W_600),
                                ft.Container(
                                    content=ft.Text("SUPL", size=8, color=ROXO, weight=ft.FontWeight.W_700),
                                    bgcolor=f"{ROXO}22", border_radius=4,
                                    padding=ft.padding.symmetric(horizontal=4, vertical=1),
                                ) if r.get("tipo") == "suplemento" else ft.Container(),
                            ], spacing=6, tight=True),
                            ft.Row([
                                ft.Text(r.get("principio_ativo") or "", size=10, color=MUT),
                            ], spacing=4) if r.get("principio_ativo") else ft.Container(),
                            ft.Row([
                                ft.Text(r.get("dosagem") or "", size=11, color=SEC),
                                ft.Text("·" if r.get("dosagem") and r.get("frequencia") else "", size=11, color=MUT),
                                ft.Text(r.get("frequencia") or "", size=11, color=SEC),
                                ft.Text("· Continuo", size=10, color=VERD) if r.get("data_fim") == "continuo" else ft.Container(),
                            ], spacing=4),
                            med_row,
                        ], spacing=2, expand=True),
                        ft.Column([
                            ft.Text(str(est), size=16, color=cor, weight=ft.FontWeight.W_700),
                            ft.Text("unid.", size=9, color=MUT),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                        ft.Icon("chevron_right_rounded", size=16, color=MUT),
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

    sw = ft.Switch(label="So ativos", value=so_ativos[0], active_color=VERD,
                   label_style=ft.TextStyle(color=SEC, size=12))
    def _toggle(e): so_ativos[0] = sw.value; _carregar()
    sw.on_change = _toggle

    def _abrir_busca(e=None):
        todos_rem = listar_remedios(so_ativos=False)
        ref_ov    = [None]

        f_search = ft.TextField(
            hint_text="Nome, principio ativo ou medico...",
            prefix_icon="search_rounded",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            hint_style=ft.TextStyle(color=MUT),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, autofocus=True,
        )
        resultado = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        def _pesquisar(e):
            termo = (f_search.value or "").strip().upper()
            resultado.controls.clear()
            if not termo:
                resultado.controls.append(
                    ft.Text("Digite para buscar...", size=12, color=MUT))
                try: page.update()
                except Exception: pass
                return
            matches = [r for r in todos_rem if
                       termo in r["nome"].upper() or
                       termo in (r.get("principio_ativo") or "").upper() or
                       termo in (r.get("medico") or "").upper()]
            if not matches:
                resultado.controls.append(
                    ft.Text("Nenhum resultado.", size=12, color=MUT))
                try: page.update()
                except Exception: pass
                return
            for r in matches[:25]:
                est = r.get("estoque_atual", 0) or 0
                mn  = r.get("estoque_minimo", 5) or 5
                cor = _cor_estoque(est, mn)
                med_txt = r.get("medico") or ""
                def _sel(e, rem=r):
                    _fechar()
                    abrir_ficha_fn(rem)
                resultado.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Icon("medication_rounded", size=18, color=cor),
                            bgcolor=f"{cor}1A", border_radius=8, width=36, height=36,
                            alignment=ft.alignment.Alignment(0, 0)),
                        ft.Column([
                            ft.Row([
                                ft.Text(r["nome"], size=13, color=TXT,
                                        weight=ft.FontWeight.W_600),
                                ft.Container(
                                    content=ft.Text("INATIVO", size=8, color=MUT),
                                    bgcolor=f"{MUT}22", border_radius=4,
                                    padding=ft.padding.symmetric(horizontal=4, vertical=1),
                                ) if not r.get("ativo", 1) else ft.Container(),
                            ], spacing=6, tight=True),
                            ft.Text(r.get("principio_ativo") or "", size=10, color=MUT)
                                if r.get("principio_ativo") else ft.Container(),
                            ft.Text(med_txt, size=10, color=ROXO)
                                if med_txt else ft.Container(),
                        ], spacing=1, expand=True),
                        ft.Text(f"{est} un.", size=11, color=cor),
                        ft.Icon("chevron_right_rounded", size=14, color=MUT),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD, border_radius=8, ink=True,
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    border=ft.Border(
                        left=ft.BorderSide(2, cor), top=ft.BorderSide(1, BD),
                        bottom=ft.BorderSide(1, BD), right=ft.BorderSide(1, BD)),
                    on_click=_sel,
                ))
            try: page.update()
            except Exception: pass

        f_search.on_change = _pesquisar
        resultado.controls.append(ft.Text("Digite para buscar...", size=12, color=MUT))

        btn_fechar = ft.Container(
            content=ft.Icon("arrow_back_rounded", size=18, color=TXT),
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            ink=True, border_radius=8,
        )
        btn_fechar.on_click = _fechar

        ref_ov[0] = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        btn_fechar,
                        ft.Text("Buscar remedio", size=16, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True),
                    ], spacing=4),
                    padding=ft.padding.symmetric(horizontal=8, vertical=12),
                    border=ft.Border(bottom=ft.BorderSide(1, BD)),
                ),
                ft.Container(
                    content=ft.Column([
                        f_search,
                        ft.Container(height=8),
                        resultado,
                    ], spacing=6, expand=True),
                    padding=ft.padding.all(16),
                    expand=True,
                ),
            ], spacing=0, expand=True),
            bgcolor=BG, expand=True,
        )
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass

    _rebuild_chips()
    _carregar()

    _btn_busca = ft.Container(
        content=ft.Icon("search_rounded", size=18, color=SEC),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8, ink=True,
        border=ft.border.all(1, BD),
    )
    _btn_busca.on_click = _abrir_busca

    _btn_novo_rem = ft.Container(
        content=ft.Row([
            ft.Icon("add_rounded", size=16, color=BG),
            ft.Text("Novo", size=13, color=BG),
        ], spacing=6, tight=True),
        bgcolor=VERD, border_radius=8, ink=True,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
    )
    _btn_novo_rem.on_click = lambda e: abrir_ficha_fn(None)

    return [
        ft.Container(
            content=ft.Column([
                ft.Row([
                    chips_row,
                    ft.Container(expand=True),
                    _btn_busca,
                    ft.Container(width=6),
                    _btn_novo_rem,
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([sw], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=4),
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
                            ft.Icon("send_rounded", size=14, color=VERD),
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

        _btn_ia = ft.Container(
            content=ft.Row([
                ft.Icon("psychology_rounded", size=14, color=BG),
                ft.Text("Analisar com IA", size=12, color=BG),
            ], spacing=4, tight=True),
            bgcolor=ROXO, border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
        )
        _btn_ia.on_click = _analisar_resposta

        lista.controls.append(_card_border(ROXO, ft.Column([
            _label_sec("ANALISAR RESPOSTA DE ORÇAMENTO", ROXO),
            f_resposta,
            ft.Row([
                _btn_ia,
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
                    ft.Icon("storefront_rounded", size=40, color=MUT),
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
                        content=ft.Icon("storefront_rounded", size=20,
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
                    ft.Icon("chevron_right_rounded", size=16, color=MUT),
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

        _btn_salvar_farm = ft.Container(
            content=ft.Row([
                ft.Icon("save_rounded", size=16, color=BG),
                ft.Text("Salvar", size=13, color=BG),
            ], spacing=6, tight=True),
            bgcolor=VERD, border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
        )
        _btn_salvar_farm.on_click = _salvar_farm

        lista.controls.clear()
        lista.controls.append(ft.Container(
            bgcolor=BG, expand=True,
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Row([
                            ft.Icon("arrow_back_rounded", size=16),
                            ft.Text("Voltar", size=13),
                        ], spacing=4, tight=True),
                        padding=ft.padding.symmetric(horizontal=8, vertical=8),
                        ink=True,
                        on_click=lambda e: _carregar()),
                    ft.Text("Nova Farmácia" if is_nova else "Editar Farmácia",
                            size=16, weight=ft.FontWeight.W_700, color=TXT, expand=True),
                    _btn_salvar_farm,
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                f_n, f_e, ft.Row([f_t, f_w], spacing=8), f_s, f_a,
                ft.Row([sw_del, sw_pref], spacing=16), f_obs_f,
            ], spacing=8, scroll=ft.ScrollMode.AUTO),
            padding=ft.padding.all(16)))
        try: page.update()
        except Exception: pass

    _carregar()

    _btn_nova_farm = ft.Container(
        content=ft.Row([
            ft.Icon("add_rounded", size=16, color=BG),
            ft.Text("Nova Farmacia", size=13, color=BG),
        ], spacing=6, tight=True),
        bgcolor=AZUL, border_radius=8, ink=True,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
    )
    _btn_nova_farm.on_click = lambda e: _abrir_ficha_farm(None)

    return [
        ft.Container(
            content=ft.Row([
                ft.Container(expand=True),
                _btn_nova_farm,
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
        (0, "today_rounded",       "Hoje",      AZUL),
        (1, "medication_rounded",  "Remédios",  AMAR),
        (2, "storefront_rounded",  "Farmácias", VERD),
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

    lay = Layout(page)
    cabecalho = lay.criar_cabecalho(
        "Remedio / Suplemento", voltar_fn,
        icone_titulo="medication_rounded",
        cor_titulo=AMAR,
    )

    corpo = ft.Column([
        ft.Container(height=lay.spacer_topo, bgcolor=BG),
        cabecalho,
        ft.Container(content=barra_abas,
                     border=ft.Border(bottom=ft.BorderSide(1, BD))),
        ft.Container(content=area, padding=ft.padding.all(16), expand=True),
    ], expand=True, spacing=0)

    tela_principal = lay.wrap(ft.Container(bgcolor=BG, expand=True, content=corpo))
    logger.info("[REMEDIOS] tela_principal montada, retornando")
    return tela_principal
