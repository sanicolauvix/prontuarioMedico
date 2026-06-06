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
    normalizar_data as _norm_data,
)
from utils.foto_picker import (
    criar_btn_seletor_foto, processar_foto, _is_android,
)

logger = logging.getLogger(__name__)


def _para_display(s: str | None) -> str:
    """Converte YYYY-MM-DD para DD/MM/YYYY para exibicao. DD/MM/YYYY passa sem alteracao."""
    if not s or s == "continuo":
        return s or ""
    s = str(s).strip()
    if len(s) >= 10 and s[4] == "-":
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            pass
    return s


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
           hint=None, keyboard=ft.KeyboardType.TEXT, read_only=False):
    kw = dict(label=label, value=valor or "", bgcolor=CARD, border_color=BD2,
              focused_border_color=AZUL, label_style=ft.TextStyle(color=SEC),
              text_style=ft.TextStyle(color=TXT), border_radius=8,
              multiline=multiline, min_lines=min_lines, keyboard_type=keyboard,
              read_only=read_only)
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
    _modo_edicao  = [is_novo]
    _status_banco = ["normal"]
    _handler_ant  = [None]
    ro = not _modo_edicao[0]

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
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(24), width=240,
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
                logger.warning("[REMEDIOS] sync erro: %s", ex)
            finally:
                _status_banco[0] = "normal"
                if ov in page.overlay:
                    page.overlay.remove(ov)
                try: page.update()
                except Exception: pass
                if apos_sync_fn:
                    apos_sync_fn()

        threading.Thread(target=_run, daemon=True).start()

    def _desregistrar_voltar_hw():
        page.on_keyboard_event = _handler_ant[0]

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
            if e.key == "Escape":
                _sair(voltar_fn)
        page.on_keyboard_event = _on_hw

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
                      hint="Digite para buscar ou cadastrar…", read_only=ro)
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
    f_nome = _campo("Nome do remedio/suplemento *", remedio["nome"] if remedio else "",
                    read_only=ro)
    f_pa   = _campo("Principio ativo (generico)",
                    remedio.get("principio_ativo","") if remedio else "",
                    hint="ex: losartana, omeprazol, whey protein…", read_only=ro)

    # ── Tipo (remedio / suplemento) + Prescrito ───────────
    _tipo_ini      = remedio.get("tipo","remedio") == "suplemento" if remedio else False
    _prescrito_ini = bool(remedio.get("prescrito", 0)) if remedio else False

    sw_tipo = ft.Switch(
        label="Suplemento (nao prescrito por medico por default)",
        value=_tipo_ini, active_color=ROXO, label_style=ft.TextStyle(color=SEC, size=12),
        disabled=ro,
    )
    sw_prescrito = ft.Switch(
        label="Prescrito pelo medico",
        value=_prescrito_ini, active_color=AZUL, label_style=ft.TextStyle(color=SEC, size=12),
        disabled=ro,
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
                   hint="ex: 500mg, 1 comprimido, 5ml…", read_only=ro)
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
                    hint="ex: 1× ao dia, a cada 8h…", read_only=ro)
    sug_freq = ft.Column(spacing=2, visible=False)

    # ── Bloco de horários (visível/oculto conforme frequência) ──
    horas_existentes = listar_horarios_remedio(remedio["id"]) if remedio and remedio.get("id") else []

    # Campo "1ª dose às" — hora de início para calcular os demais
    f_hora_inicio = _campo("1ª dose às", "08:00", hint="HH:MM", largura=110, read_only=ro)

    # Texto calculado exibindo os horários resultantes
    txt_horarios_calc = ft.Text("", size=13, color=VERD, weight=ft.FontWeight.W_600)

    # Campo livre para edição manual (preenchido automaticamente, editável)
    f_horarios = _campo("Horários",
                        ", ".join(h["hora"] for h in horas_existentes),
                        hint="08:00, 16:00, 22:00…", read_only=ro)

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

    from shared.date_field import campo_data as _campo_data
    row_ini, f_ini = _campo_data(
        page, "Inicio",
        value=remedio.get("data_inicio","") if remedio else "",
        cor_acento=AMAR, largura=140)
    f_ini.read_only = ro
    row_data_fim, f_fim = _campo_data(
        page, "Fim previsto",
        value="" if _continuo_ini else _data_fim_raw,
        cor_acento=AMAR, largura=140)
    f_fim.read_only = ro

    sw_continuo = ft.Switch(
        label="Uso continuo",
        value=_continuo_ini,
        active_color=VERD,
        label_style=ft.TextStyle(color=SEC, size=12),
        disabled=ro,
    )
    row_data_fim.visible = not _continuo_ini

    def _on_continuo(e):
        row_data_fim.visible = not sw_continuo.value
        if sw_continuo.value:
            f_fim.value = ""
        try: page.update()
        except Exception: pass
    sw_continuo.on_change = _on_continuo

    # ── Observações ───────────────────────────────────────
    f_obs  = _campo("Observações", remedio.get("observacoes","") if remedio else "",
                    multiline=True, min_lines=2, read_only=ro)

    # ── Estoque ───────────────────────────────────────────
    f_est = _campo("Estoque", str(remedio.get("estoque_atual",0)) if remedio else "0",
                   largura=100, keyboard=ft.KeyboardType.NUMBER, read_only=ro)
    f_min = _campo("Alerta mín.", str(remedio.get("estoque_minimo",5)) if remedio else "5",
                   largura=100, keyboard=ft.KeyboardType.NUMBER, read_only=ro)

    def _ajustar(d):
        try:
            f_est.value = str(max(0, int(f_est.value or 0) + d))
            page.update()
        except Exception: pass

    _btn_est_menos = ft.IconButton("remove_rounded", icon_color=VERM, icon_size=18,
        on_click=lambda e: _ajustar(-1),
        style=ft.ButtonStyle(bgcolor="#1C1014", shape=ft.RoundedRectangleBorder(radius=8)),
        disabled=ro)
    _btn_est_mais = ft.IconButton("add_rounded", icon_color=VERD, icon_size=18,
        on_click=lambda e: _ajustar(+1),
        style=ft.ButtonStyle(bgcolor="#0D1C12", shape=ft.RoundedRectangleBorder(radius=8)),
        disabled=ro)
    ctrl_est = ft.Row([
        _btn_est_menos, f_est, _btn_est_mais,
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
    btn_add_foto.visible = not ro

    btn_add_receita = criar_btn_seletor_foto(
        page=page,
        on_arquivo=_on_foto_receita,
        titulo_menu="Foto da receita",
        label_btn="Adicionar receita",
    )
    btn_add_receita.visible = not ro

    _rebuild_galerias()

    # ── Switch ativo ──────────────────────────────────────
    sw_ativo = ft.Switch(label="Ativo",
        value=bool(remedio.get("ativo",1)) if remedio else True,
        active_color=VERD, label_style=ft.TextStyle(color=SEC, size=13),
        disabled=ro)

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

        data_fim_val = "continuo" if sw_continuo.value else (_norm_data(f_fim.value.strip()) or None)

        # Auto-cadastra medico digitado mas nao selecionado da lista
        if sw_prescrito.value and not med_id_sel[0] and (f_medico.value or "").strip():
            novo_mid = salvar_medico({"nome": f_medico.value.strip()})
            med_id_sel[0] = novo_mid

        dados = {
            "id": remedio["id"] if remedio else None,
            "nome": f_nome.value.strip(),
            "dosagem": f_dos.value.strip() or None,
            "frequencia": f_freq.value.strip() or None,
            "data_inicio": _norm_data(f_ini.value.strip()) or None,
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

        _modo_edicao[0] = False
        _status_banco[0] = "em_edicao"
        _sync(voltar_fn)

    # ── Layout da ficha ───────────────────────────────────
    titulo = "Nova Medicacao" if is_novo else "Medicacao"
    lay    = Layout(page)

    btn_editar = ft.Container(
        content=ft.Row([
            ft.Icon("edit_rounded", size=13, color=AMAR),
            ft.Text("Editar", size=12, color=AMAR),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        border_radius=8, bgcolor=ft.Colors.with_opacity(0.12, AMAR), ink=True,
        visible=not is_novo,
    )

    btn_salvar_cab = ft.Container(
        content=ft.Row([
            ft.Icon("check_rounded", size=14, color=VERD),
            ft.Text("Salvar", size=13, color=VERD, weight=ft.FontWeight.W_600),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        border_radius=8, ink=True,
        visible=_modo_edicao[0],
    )
    btn_salvar_cab.on_click = _salvar

    cabecalho = lay.criar_cabecalho(
        titulo, lambda e=None: _sair(voltar_fn),
        icone_titulo="medication_rounded",
        cor_titulo=AMAR,
        acoes=[btn_editar, btn_salvar_cab],
    )

    # botão de fundo removido — salvar fica só no cabeçalho
    btn_salvar_fundo = ft.Container(visible=False)

    def _ativar_edicao(e=None):
        _modo_edicao[0] = True
        for campo in (f_nome, f_pa, f_dos, f_freq, f_hora_inicio,
                      f_horarios, f_ini, f_fim, f_obs, f_est, f_min, f_medico):
            campo.read_only = False
        for sw in (sw_tipo, sw_prescrito, sw_continuo, sw_ativo):
            sw.disabled = False
        _btn_est_menos.disabled = False
        _btn_est_mais.disabled = False
        btn_add_foto.visible = True
        btn_add_receita.visible = True
        btn_editar.visible    = False
        btn_salvar_cab.visible = True
        try: page.update()
        except Exception: pass

    btn_editar.on_click = _ativar_edicao

    # ── Abas ─────────────────────────────────────────────
    ABAS_FICHA = [
        (0, "medication_rounded",   "Geral",        AMAR),
        (1, "person_rounded",       "Medicos",      ROXO),
        (2, "swap_vert_rounded",    "Movimentacao", AZUL),
    ]
    aba_ativa  = [0]
    barra_abas = ft.Row(spacing=0)
    area_abas  = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

    # ── Bloco Tabela Nutricional do Rótulo ───────────────
    _rid_atual    = remedio["id"] if remedio and remedio.get("id") else None
    _calculando_r = [False]
    nutr_col_rem  = ft.Column(spacing=3, tight=True)
    lbl_claudia_r = ft.Text("Extrair tabela do rótulo com Claudia", size=12, color=ROXO)
    _foto_rotulo  = [None]   # path absoluto da foto do rótulo

    def _refresh_nutr_rem():
        nutr_col_rem.controls.clear()
        if not _rid_atual:
            return
        from dados.model_prontuario import carregar_nutricao as _cn
        n = _cn("remedio", _rid_atual)
        if not n:
            return
        import json as _json

        def _row(lbl, val, unid, cor=TXT, bold=False):
            return ft.Row([
                ft.Text(lbl, size=11, color=SEC, expand=True),
                ft.Text(f"{val:.1f}" if val is not None else "—",
                        size=11, color=cor,
                        weight=ft.FontWeight.W_700 if bold else ft.FontWeight.NORMAL),
                ft.Text(f" {unid}", size=10, color=MUT),
            ], spacing=2)

        # monta título com porção real do rótulo
        por_g = n.get("por_100g") or 100.0
        vits_pre = {}
        try:
            import json as _json2
            vits_pre = _json2.loads(n.get("vitaminas_json") or "{}")
        except Exception:
            pass
        porcao_info = vits_pre.pop("_porcao", None)  # ex: "2g = 4 unid x 0.5g"

        if por_g and float(por_g) != 100.0:
            titulo_tab = f"TABELA NUTRICIONAL / PORÇÃO ({float(por_g):.1f}g)"
        else:
            titulo_tab = "TABELA NUTRICIONAL / PORÇÃO"

        linhas = [
            ft.Text(titulo_tab, size=9, color=ROXO, weight=ft.FontWeight.W_700),
            ft.Divider(height=1, color=ROXO),
            _row("Valor Energético", n.get("kcal"),          "kcal", LAR, True),
            _row("Carboidratos",     n.get("carboidratos"),  "g"),
            _row("Proteínas",        n.get("proteinas"),     "g",  VERD, True),
            _row("Gorduras Totais",  n.get("gorduras"),      "g"),
            _row("Fibra Alimentar",  n.get("fibras"),        "g"),
            _row("Sódio",            n.get("sodio"),         "mg"),
        ]
        # info de unidade (ex: "2g = 4 unid x 0.5g")
        if porcao_info:
            linhas.append(ft.Container(
                content=ft.Row([
                    ft.Icon("medication_rounded", size=11, color=ROXO),
                    ft.Text(porcao_info, size=10, color=ROXO),
                ], spacing=4),
                padding=ft.padding.only(top=4),
            ))

        if vits_pre:
            linhas.append(ft.Divider(height=1, color=BD2))
            linhas.append(ft.Text("Ativos / Vitaminas / Minerais", size=9,
                                  color=SEC, weight=ft.FontWeight.W_600))
            for kv, vv in list(vits_pre.items())[:10]:
                linhas.append(ft.Row([
                    ft.Text(kv.replace("_", " ").title(), size=10,
                            color=MUT, expand=True),
                    ft.Text(str(vv), size=10, color=SEC),
                ], spacing=4))

        nutr_col_rem.controls.append(ft.Container(
            content=ft.Column(linhas, spacing=3, tight=True),
            bgcolor=CARD, border_radius=10, padding=ft.padding.all(12),
            border=ft.Border(
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                left=ft.BorderSide(3, ROXO), right=ft.BorderSide(1, BD)),
        ))
        try: page.update()
        except Exception: pass

    def _calcular_nutr_rotulo(e=None):
        if _calculando_r[0]: return
        if not _foto_rotulo[0] and not _rid_atual:
            page.snack_bar = ft.SnackBar(
                ft.Text("Tire uma foto do rótulo primeiro.", color=AMAR), open=True)
            try: page.update()
            except Exception: pass
            return
        _calculando_r[0] = True
        lbl_claudia_r.value = "Extraindo..."
        try: page.update()
        except Exception: pass

        def _run():
            try:
                import base64, json as _json
                from utils.claudia_engine import get_client, _MODELO
                client = get_client()

                # monta mensagem com imagem se disponível
                if _foto_rotulo[0]:
                    with open(_foto_rotulo[0], "rb") as f:
                        img_b64 = base64.b64encode(f.read()).decode()
                    ext = _foto_rotulo[0].rsplit(".", 1)[-1].lower()
                    media_type = f"image/{'jpeg' if ext in ('jpg','jpeg') else ext}"
                    content = [
                        {
                            "type": "image",
                            "source": {"type": "base64",
                                       "media_type": media_type,
                                       "data": img_b64},
                        },
                        {
                            "type": "text",
                            "text": (
                                "Extraia TODOS os dados nutricionais deste rotulo "
                                "de suplemento ou medicamento. "
                                "Se houver multiplas faixas etarias, use SEMPRE os valores "
                                "de Adultos (>=19 anos). "
                                "Se o rotulo indicar 'nao contem quantidades significativas' "
                                "de algum nutriente, coloque 0 para esse campo. "
                                "Coloque vitaminas, minerais e ativos especificos do produto "
                                "(ex: Colageno, Curcumina, Vitamina D, Calcio, Omega 3, etc.) "
                                "no campo 'vitaminas' com nome_unidade e valor numerico exato. "
                                "Inclua tambem 'unidades_por_porcao' (ex: 4 capsulas = 4, "
                                "1 pastilha = 1, 1 comprimido = 1) e "
                                "'peso_por_unidade_g' (peso de cada capsula/comprimido/unidade em gramas). "
                                "Retorne SOMENTE JSON valido:\n"
                                '{"por_porcao_g":6.5,"unidades_por_porcao":1,"peso_por_unidade_g":6.5,'
                                '"kcal":0,"kj":0,"carboidratos":0,'
                                '"acucares":0,"proteinas":0,"gorduras":0,"saturadas":0,'
                                '"trans":0,"fibras":0,"sodio":0,'
                                '"vitaminas":{"Vitamina_D_mcg":0,"Calcio_mg":0}}'
                                "\nUse os valores exatos do rotulo, nao estime."
                            ),
                        },
                    ]
                else:
                    nome_rem = remedio.get("nome","") if remedio else ""
                    content = (
                        f"Tabela nutricional do suplemento '{nome_rem}' "
                        "conforme rotulo tipico. "
                        "Retorne SOMENTE JSON valido:\n"
                        '{"por_porcao_g":30,"kcal":0,"kj":0,"carboidratos":0,'
                        '"acucares":0,"proteinas":0,"gorduras":0,"saturadas":0,'
                        '"trans":0,"fibras":0,"sodio":0,'
                        '"vitaminas":{}}'
                    )

                resp = client.messages.create(
                    model=_MODELO, max_tokens=1024,
                    system="Voce e um nutricionista. Retorne SOMENTE JSON valido.",
                    messages=[{"role": "user", "content": content}],
                )
                raw = "".join(b.text for b in resp.content
                              if hasattr(b, "text")).strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"): raw = raw[4:]
                dados = _json.loads(raw)
                vits              = dados.pop("vitaminas", {})
                por_g             = dados.pop("por_porcao_g", 100)
                unid_por_porcao   = dados.pop("unidades_por_porcao", 1)
                peso_por_unid     = dados.pop("peso_por_unidade_g", None)

                # adiciona info de unidade nas vitaminas para exibição
                if unid_por_porcao and peso_por_unid:
                    vits["_porcao"] = f"{por_g}g = {int(unid_por_porcao)} unid x {peso_por_unid}g"

                rid = _rid_atual
                if not rid and remedio:
                    rid = remedio.get("id")

                if rid:
                    from dados.model_prontuario import salvar_nutricao as _sn
                    _sn({
                        "entidade_tipo": "remedio",
                        "entidade_id":   rid,
                        "por_100g":      por_g,
                        **{k: dados.get(k) for k in
                           ["kcal","kj","carboidratos","acucares","proteinas",
                            "gorduras","saturadas","trans","fibras","sodio"]},
                        "vitaminas_json": _json.dumps(vits, ensure_ascii=False)
                                          if vits else None,
                    })
                    from backup.drive_backup import fazer_backup
                    fazer_backup(forcar=True)
            except Exception as ex:
                logger.warning("[REMEDIO] nutr rotulo: %s", ex)
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Erro: {str(ex)[:80]}", color=VERM), open=True)
            finally:
                _calculando_r[0] = False
                lbl_claudia_r.value = "Recalcular tabela do rótulo"
                _refresh_nutr_rem()
                try: page.update()
                except Exception: pass

        threading.Thread(target=_run, daemon=True, name="NutrRotulo").start()

    def _on_foto_rotulo(path_abs):
        _foto_rotulo[0] = path_abs
        lbl_claudia_r.value = "Extrair tabela do rótulo com Claudia"
        try: page.update()
        except Exception: pass
        # dispara extração automaticamente
        _calcular_nutr_rotulo()

    btn_foto_rotulo = criar_btn_seletor_foto(
        page=page,
        on_arquivo=_on_foto_rotulo,
        titulo_menu="Foto do rótulo nutricional",
        label_btn="Foto do rótulo",
    )

    btn_claudia_rot = ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Text("C", size=10, color=BG, weight=ft.FontWeight.W_700),
                width=20, height=20, border_radius=10, bgcolor=ROXO,
                alignment=ft.Alignment(0, 0)),
            lbl_claudia_r,
        ], spacing=8, tight=True),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border_radius=10, ink=True,
        border=ft.Border(
            top=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO)),
            bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO)),
            left=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO)),
            right=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ROXO))),
    )
    btn_claudia_rot.on_click = _calcular_nutr_rotulo

    # carrega tabela existente se remedio ja tem
    if _rid_atual:
        _refresh_nutr_rem()

    # ── Conteúdo Aba 0 — Geral ────────────────────────────
    def _conteudo_geral():
        return [
            _label_sec("IDENTIFICACAO"),
            f_nome,
            f_pa,
            ft.Row([sw_tipo], spacing=8),
            ft.Container(height=4),
            _label_sec("DOSAGEM"),
            ft.Column([f_dos, sug_dos], spacing=0),
            ft.Container(height=4),
            _label_sec("FREQUENCIA DE USO"),
            ft.Column([f_freq, sug_freq], spacing=0),
            bloco_horarios,
            ft.Container(height=4),
            _label_sec("PERIODO DE USO"),
            ft.Row([sw_continuo], spacing=8),
            row_ini,
            row_data_fim,
            ft.Container(height=4),
            _label_sec("VALIDADE DA ULTIMA RECEITA"),
            chips_validade,
            txt_data_validade,
            ft.Container(height=4),
            _label_sec("FOTO DO REMEDIO / CAIXA"),
            btn_add_foto,
            galeria_rem,
            ft.Container(height=4),
            _label_sec("TABELA NUTRICIONAL DO ROTULO", ROXO),
            btn_foto_rotulo,
            btn_claudia_rot,
            nutr_col_rem,
            ft.Container(height=4),
            _label_sec("OBSERVACOES"),
            f_obs,
            ft.Container(height=8),
            sw_ativo,
            txt_erro,
            ft.Container(height=16),
        ]

    # ── Conteúdo Aba 2 — Movimentação ────────────────────
    def _conteudo_movimentacao():
        from dados.model_prontuario import listar_mov_remedio, listar_itens_compra
        items = [_label_sec("MOVIMENTAÇÃO DE ESTOQUE", AZUL)]

        if not remedio or not remedio.get("id"):
            items.append(ft.Text("Salve o remédio primeiro.", size=12, color=MUT))
            return items

        movs = listar_mov_remedio(remedio["id"], limit=50)
        if not movs:
            items.append(ft.Container(
                content=ft.Column([
                    ft.Icon("swap_vert_rounded", size=32, color=MUT),
                    ft.Text("Nenhuma movimentação registrada.", size=12, color=SEC),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                padding=ft.padding.symmetric(vertical=24),
                alignment=ft.alignment.center,
            ))
            return items

        # Cores e ícones por tipo
        _TIPO = {
            "compra":      (VERD,  "shopping_cart_rounded",       "Compra"),
            "inicio_uso":  (AZUL,  "play_circle_outline_rounded", "Início uso"),
            "tomada":      (ROXO,  "medication_rounded",          "Tomada"),
            "estorno":     (AMAR,  "undo_rounded",                "Estorno"),
            "vencimento":  (VERM,  "event_busy_rounded",          "Vencimento"),
            "ajuste":      (MUT,   "tune_rounded",                "Ajuste"),
        }

        def _abrir_detalhe_mov(m):
            """Overlay com detalhes completos da movimentação."""
            tipo     = m.get("tipo", "ajuste")
            cor, icone, label = _TIPO.get(tipo, (MUT, "swap_vert_rounded", tipo.title()))
            qtd      = m.get("quantidade", 0)
            sinal    = "+" if qtd > 0 else ""
            est_apos = m.get("estoque_apos")
            farm     = m.get("farmacia_nome") or ""
            obs      = m.get("observacoes") or ""
            data     = m.get("data") or ""
            origem   = m.get("origem") or ""
            preco_u  = m.get("preco_unitario")
            preco_t  = m.get("preco_total")

            linhas = [
                ft.Row([
                    ft.Container(
                        content=ft.Icon(icone, size=18, color=cor),
                        bgcolor=ft.Colors.with_opacity(0.12, cor),
                        border_radius=8, width=36, height=36,
                        alignment=ft.alignment.center,
                    ),
                    ft.Column([
                        ft.Text(label, size=15, color=cor, weight=ft.FontWeight.W_700),
                        ft.Text(data, size=11, color=MUT),
                    ], spacing=2, tight=True, expand=True),
                    ft.Text(f"{sinal}{qtd} cpr", size=16, color=cor,
                            weight=ft.FontWeight.W_700),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(height=1, bgcolor=BD),
            ]

            def _linha_det(titulo, valor, cor_val=SEC):
                return ft.Row([
                    ft.Text(titulo, size=11, color=MUT, expand=True),
                    ft.Text(str(valor), size=12, color=cor_val,
                            weight=ft.FontWeight.W_600),
                ], spacing=8)

            if est_apos is not None:
                linhas.append(_linha_det("Estoque após", f"{est_apos} cpr", AZUL))
            if farm:
                linhas.append(_linha_det("Fornecedor", farm, ROXO))
            if preco_u:
                linhas.append(_linha_det("Preço unitário", f"R$ {preco_u:.2f}"))
            if preco_t:
                linhas.append(_linha_det("Preço total", f"R$ {preco_t:.2f}", VERD))

            # Detalhe NF
            if origem == "nota_fiscal" and tipo == "compra":
                try:
                    import sqlite3 as _sql
                    from dados.model_prontuario import DB_PATH as _DB
                    with _sql.connect(_DB, timeout=5) as _c:
                        row = _c.execute("""
                            SELECT c.id, c.total,
                                   COALESCE(NULLIF(f.nome,''), f.razao_social) as farm_nome,
                                   ci.comprimidos_emb, ci.preco_total as item_total
                            FROM compras c
                            LEFT JOIN farmacias f ON f.id = c.farmacia_id
                            JOIN compra_itens ci ON ci.compra_id = c.id
                            WHERE ci.remedio_id = ? AND c.data = ?
                            LIMIT 1
                        """, (remedio["id"], data)).fetchone()
                    if row:
                        linhas.append(ft.Container(height=1, bgcolor=BD))
                        linhas.append(_linha_det("Nota fiscal", f"NF #{row[0]}"))
                        if row[2]:
                            linhas.append(_linha_det("Farmácia NF", row[2], ROXO))
                        if row[3]:
                            linhas.append(_linha_det("Comprimidos/emb", f"{row[3]} cpr"))
                        if row[4]:
                            linhas.append(_linha_det("Valor item", f"R$ {row[4]:.2f}", VERD))
                        linhas.append(_linha_det("Total nota", f"R$ {row[1]:.2f}", VERD))
                except Exception:
                    pass

            if obs:
                linhas.append(ft.Container(height=1, bgcolor=BD))
                linhas.append(ft.Text(obs, size=10, color=MUT, max_lines=3))

            ov = [None]
            def _fechar(e=None):
                if ov[0] in page.overlay: page.overlay.remove(ov[0])
                try: page.update()
                except Exception: pass

            ov[0] = ft.Container(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("Detalhes", size=14, color=TXT,
                                    weight=ft.FontWeight.W_700, expand=True),
                            ft.Container(
                                content=ft.Icon("close_rounded", size=16, color=SEC),
                                width=28, height=28, border_radius=6,
                                alignment=ft.alignment.center, ink=True,
                                on_click=_fechar,
                            ),
                        ]),
                        ft.Container(height=4),
                        *linhas,
                    ], spacing=8, tight=True),
                    bgcolor=CARD, border_radius=14,
                    padding=ft.padding.all(20), width=340,
                    border=ft.border.all(1, BD2),
                ),
                bgcolor="#CC000000", expand=True,
                alignment=ft.Alignment(0, 0), on_click=_fechar,
            )
            page.overlay.append(ov[0])
            try: page.update()
            except Exception: pass

        for m in movs:
            tipo     = m.get("tipo", "ajuste")
            cor, icone, label = _TIPO.get(tipo, (MUT, "swap_vert_rounded", tipo.title()))
            qtd      = m.get("quantidade", 0)
            sinal    = "+" if qtd > 0 else ""
            est_apos = m.get("estoque_apos")
            farm     = m.get("farmacia_nome") or ""
            data     = m.get("data") or ""

            # Comprimidos/embalagem para compras via NF
            cpr_txt = ""
            if m.get("origem") == "nota_fiscal" and tipo == "compra":
                try:
                    import sqlite3 as _sql
                    from dados.model_prontuario import DB_PATH as _DB
                    with _sql.connect(_DB, timeout=5) as _c:
                        row = _c.execute("""
                            SELECT ci.comprimidos_emb, ci.quantidade_emb
                            FROM compra_itens ci
                            JOIN compras c ON c.id = ci.compra_id
                            WHERE ci.remedio_id = ? AND c.data = ?
                            LIMIT 1
                        """, (remedio["id"], data)).fetchone()
                    if row and row[0]:
                        cpr_txt = f"{row[0]} cpr/emb"
                    elif row and row[1]:
                        cpr_txt = f"{row[1]} emb"
                except Exception:
                    pass

            card = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(icone, size=13, color=cor),
                        bgcolor=ft.Colors.with_opacity(0.12, cor),
                        border_radius=5, width=24, height=24,
                        alignment=ft.alignment.center,
                    ),
                    ft.Text(label, size=12, color=cor,
                            weight=ft.FontWeight.W_600),
                    ft.Text(farm, size=11, color=ROXO, max_lines=1)
                        if farm else ft.Container(),
                    ft.Text(cpr_txt, size=11, color=MUT)
                        if cpr_txt else ft.Container(),
                    ft.Container(expand=True),
                    ft.Text(data, size=10, color=MUT),
                    ft.Text(f"{sinal}{qtd}", size=12, color=cor,
                            weight=ft.FontWeight.W_700),
                    ft.Text(
                        f"| {est_apos} cpr" if est_apos is not None else "",
                        size=10, color=SEC,
                    ),
                    ft.Icon("chevron_right_rounded", size=14, color=MUT),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD, border_radius=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                border=ft.Border(
                    left=ft.BorderSide(2, cor),
                    top=ft.BorderSide(1, BD),
                    bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
                ink=True,
                on_click=lambda e, mov=m: _abrir_detalhe_mov(mov),
            )
            items.append(card)

        return items

    # ── Conteúdo Aba 1 — Médicos ──────────────────────────
    def _conteudo_medicos():
        items = [
            _label_sec("HISTORICO DE PRESCRICOES", ROXO),
            ft.Text("Medicos que prescreveram este remedio via consultas.",
                    size=11, color=MUT),
            ft.Container(height=8),
        ]
        if not remedio or not remedio.get("id"):
            items.append(ft.Text("Salve o remedio primeiro para ver o historico.",
                                 size=12, color=MUT))
            return items

        try:
            from dados.model_prontuario import listar_mov_remedio
            movs = [m for m in listar_mov_remedio(remedio["id"], limit=50)
                    if m.get("tipo") == "inicio_uso" and m.get("consulta_id")]
        except Exception:
            movs = []

        if not movs:
            items.append(ft.Container(
                content=ft.Column([
                    ft.Icon("person_off_rounded", size=36, color=MUT),
                    ft.Text("Nenhuma prescricao registrada ainda.",
                            size=13, color=MUT, text_align=ft.TextAlign.CENTER),
                    ft.Text("Prescricoes aparecem ao importar receitas nas consultas.",
                            size=11, color=MUT, text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                padding=ft.padding.symmetric(vertical=32),
                alignment=ft.Alignment(0, 0),
            ))
            return items

        for m in movs:
            data_str = m.get("data", "")
            obs      = m.get("observacoes", "") or ""
            # Tenta extrair medico da consulta vinculada
            medico_nome = ""
            try:
                from dados.model_prontuario import get_config
                import sqlite3 as _sql
                from dados.model_prontuario import DB_PATH as _DB
                with _sql.connect(_DB, timeout=5) as _c:
                    row = _c.execute("""
                        SELECT m.nome FROM consultas c
                        LEFT JOIN medicos m ON m.id = c.medico_id
                        WHERE c.id = ?
                    """, (m["consulta_id"],)).fetchone()
                    if row and row[0]:
                        medico_nome = row[0]
            except Exception:
                pass

            # Status: nova = primeira vez, continuada = já existia antes
            status     = "Nova"
            cor_status = VERD
            try:
                movs_ant = [x for x in listar_mov_remedio(remedio["id"], limit=50)
                            if x.get("tipo") == "inicio_uso"
                            and x.get("id", 0) < m.get("id", 0)]
                if movs_ant:
                    status     = "Continuada"
                    cor_status = AZUL
            except Exception:
                pass

            items.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("person_rounded", size=14, color=ROXO),
                        ft.Text(medico_nome or "Medico nao identificado",
                                size=13, color=TXT, weight=ft.FontWeight.W_600,
                                expand=True),
                        ft.Container(
                            content=ft.Text(status, size=10, color=cor_status,
                                            weight=ft.FontWeight.W_700),
                            bgcolor=ft.Colors.with_opacity(0.12, cor_status),
                            border_radius=4,
                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                        ),
                    ], spacing=8),
                    ft.Row([
                        ft.Icon("calendar_today_rounded", size=11, color=MUT),
                        ft.Text(_para_display(data_str), size=11, color=MUT),
                    ], spacing=4) if data_str else ft.Container(),
                    ft.Text(obs, size=11, color=SEC) if obs else ft.Container(),
                ], spacing=4),
                bgcolor=CARD, border_radius=8,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                border=ft.Border(
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    left=ft.BorderSide(3, ROXO), right=ft.BorderSide(1, BD),
                ),
            ))

        return items

    # ── Rebuild abas ──────────────────────────────────────
    def _rebuild_abas():
        barra_abas.controls.clear()
        for idx, icone, label, cor in ABAS_FICHA:
            ativo = idx == aba_ativa[0]
            def _click(e, i=idx):
                aba_ativa[0] = i
                _rebuild_abas()
                _rebuild_conteudo()
            barra_abas.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon(icone, size=15, color=cor if ativo else SEC),
                    ft.Text(label, size=9,
                            color=cor if ativo else SEC,
                            weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.W_400),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=2, tight=True),
                expand=True,
                padding=ft.padding.symmetric(vertical=8),
                border=ft.Border(bottom=ft.BorderSide(2, cor if ativo else "#00000000")),
                on_click=_click, ink=True,
            ))
        try: page.update()
        except Exception: pass

    def _rebuild_conteudo():
        area_abas.controls.clear()
        if aba_ativa[0] == 0:
            area_abas.controls.extend(_conteudo_geral())
        elif aba_ativa[0] == 1:
            area_abas.controls.extend(_conteudo_medicos())
        else:
            area_abas.controls.extend(_conteudo_movimentacao())
        try: page.update()
        except Exception: pass

    _rebuild_abas()
    _rebuild_conteudo()

    corpo_ficha = ft.Column([
        ft.Container(height=lay.spacer_topo, bgcolor=BG),
        cabecalho,
        ft.Container(
            content=barra_abas,
            border=ft.Border(bottom=ft.BorderSide(1, BD)),
        ),
        ft.Container(
            content=area_abas,
            padding=ft.padding.all(16),
            expand=True,
        ),
    ], expand=True, spacing=0)

    _registrar_voltar_hw()
    return lay.wrap(ft.Container(bgcolor=BG, expand=True, content=corpo_ficha))


# ══════════════════════════════════════════════════════════════
# ABA 2 — LISTA DE REMÉDIOS
# ══════════════════════════════════════════════════════════════

def _lista_remedios(page, abrir_ficha_fn, readonly=False):
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

        # chips de filtro + switch dentro do overlay
        chips_ov = ft.Row(spacing=6, wrap=False)
        def _rebuild_chips_ov():
            chips_ov.controls.clear()
            for tp, label in _TIPOS:
                ativo = tipo_sel[0] == tp
                cor   = AZUL if ativo else MUT
                def _sel_tp(e, t=tp):
                    tipo_sel[0] = t
                    _rebuild_chips_ov()
                    _rebuild_chips()
                    _carregar()
                    try: page.update()
                    except Exception: pass
                chips_ov.controls.append(ft.Container(
                    content=ft.Text(label, size=11, color=cor,
                                    weight=ft.FontWeight.W_600),
                    bgcolor=f"{AZUL}22" if ativo else BD,
                    border_radius=12,
                    padding=ft.padding.symmetric(horizontal=10, vertical=5),
                    border=ft.Border(
                        top=ft.BorderSide(1, cor), bottom=ft.BorderSide(1, cor),
                        left=ft.BorderSide(1, cor), right=ft.BorderSide(1, cor)),
                    ink=True, on_click=_sel_tp,
                ))
        _rebuild_chips_ov()

        sw_ov = ft.Switch(label="So ativos", value=so_ativos[0],
                          active_color=VERD,
                          label_style=ft.TextStyle(color=SEC, size=12))
        def _toggle_ov(e):
            so_ativos[0] = sw_ov.value
            sw.value = sw_ov.value
            _carregar()
        sw_ov.on_change = _toggle_ov

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
                        ft.Row([chips_ov, ft.Container(expand=True), sw_ov],
                               vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        f_search,
                        ft.Container(height=8),
                        resultado,
                    ], spacing=8, expand=True),
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
        visible=not readonly,
    )
    _btn_novo_rem.on_click = lambda e: abrir_ficha_fn(None)

    return [
        ft.Container(
            content=ft.Row([
                ft.Container(expand=True),
                _btn_busca,
                ft.Container(width=6),
                _btn_novo_rem,
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.only(bottom=8)),
        lista,
    ]


# ══════════════════════════════════════════════════════════════
# ABA 3 — COMPRAS (nota fiscal → IA → registra compra)
# ══════════════════════════════════════════════════════════════

def _form_edicao_compra(page, nota: dict, on_voltar):
    """Tela de edição de compra — fornecedor, data, obs e devoluções por item."""
    from dados.model_prontuario import (
        listar_farmacias, atualizar_compra_nf,
        listar_itens_compra, devolver_item_compra, salvar_farmacia,
    )

    BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
    TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
    AZUL = "#58A6FF"; VERD = "#3FB950"; AMAR = "#D29922"; VERM = "#DA3633"

    area_ref = [None]  # referência ao Column pai — preenchida no retorno

    def _label_sec(texto, cor=MUT):
        return ft.Text(texto, size=10, color=cor, weight=ft.FontWeight.W_700)

    def _tf(label, valor, **kw):
        return ft.TextField(
            label=label, value=valor or "",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=10),
            text_style=ft.TextStyle(color=TXT, size=12),
            border_radius=6, expand=True, **kw,
        )

    farmas     = listar_farmacias(so_ativas=False)
    farm_id    = [nota.get("farmacia_id")]

    # ── Picker fornecedor ────────────────────────────
    # Painel info fornecedor selecionado
    farm_info_col = ft.Column(spacing=2, visible=False)

    def _atualizar_info_farm():
        """Mostra nome fantasia + razão social do fornecedor selecionado."""
        farm_info_col.controls.clear()
        fid = farm_id[0]
        if not fid:
            farm_info_col.visible = False
            return
        farm_data = next((f for f in farmas if f["id"] == fid), None)
        if not farm_data:
            farm_info_col.visible = False
            return
        nome_f  = farm_data.get("nome") or ""
        razao   = farm_data.get("razao_social") or ""
        # Principal: fantasia se preenchido, senão razão
        nome_principal  = nome_f or razao
        nome_secundario = razao if nome_f and razao and razao != nome_f else ""

        def _abrir_ficha_farm(e):
            from telas.tela_fornecedores import abrir_ficha_fornecedor

            def _voltar_para_edicao():
                farmas.clear()
                farmas.extend(listar_farmacias(so_ativas=False))
                from dados.model_prontuario import listar_compras_nf as _lcnf
                nota_atualizada = next(
                    (n for n in _lcnf(incluir_canceladas=True)
                     if n["id"] == nota["id"]), nota
                )
                area_ref[0].controls.clear()
                area_ref[0].controls.extend(
                    _form_edicao_compra(page, nota_atualizada, on_voltar)
                )
                try: page.update()
                except Exception: pass

            fid = farm_id[0]
            if not fid:
                return
            ficha = abrir_ficha_fornecedor(page, fid, _voltar_para_edicao)
            area_ref[0].controls.clear()
            area_ref[0].controls.append(ficha)
            try: page.update()
            except Exception: pass

        farm_info_col.controls.extend([
            ft.Row([
                ft.Icon("storefront_rounded", size=13, color=AZUL),
                ft.Column([
                    ft.Text(nome_principal, size=13, color=TXT,
                            weight=ft.FontWeight.W_600),
                    ft.Text(razao if nome_secundario else "", size=10, color=MUT)
                        if nome_secundario else ft.Container(),
                ], spacing=1, expand=True, tight=True),
                ft.Container(
                    content=ft.Row([
                        ft.Icon("open_in_new_rounded", size=12, color=AZUL),
                        ft.Text("Ver ficha", size=11, color=AZUL),
                    ], spacing=4, tight=True),
                    bgcolor=ft.Colors.with_opacity(0.10, AZUL),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.3, AZUL)),
                    border_radius=6, ink=True,
                    padding=ft.padding.symmetric(horizontal=8, vertical=5),
                    on_click=_abrir_ficha_farm,
                ),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ])
        farm_info_col.visible = True

    farm_chip = ft.Container(
        content=ft.Row([
            ft.Icon("storefront_rounded", size=12, color=AZUL),
            ft.Text(nota.get("farmacia_nome") or "", size=12, color=AZUL,
                    weight=ft.FontWeight.W_600),
            ft.Icon("close_rounded", size=11, color=AZUL),
        ], spacing=4, tight=True),
        bgcolor=ft.Colors.with_opacity(0.12, AZUL), border_radius=12,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        visible=bool(nota.get("farmacia_nome")),
    )
    tf_farm = ft.TextField(
        hint_text="Razão social ou nome fantasia...",
        prefix_icon="search_rounded",
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        hint_style=ft.TextStyle(color=MUT, size=11),
        text_style=ft.TextStyle(color=TXT, size=12),
        border_radius=6, expand=True, height=40,
        visible=not bool(nota.get("farmacia_nome")),
    )
    farm_sugs = ft.Column(spacing=2, visible=False)

    def _mostrar_chip(nome):
        farm_chip.content.controls[1].value = nome
        farm_chip.visible = True
        tf_farm.visible   = False
        farm_sugs.controls.clear(); farm_sugs.visible = False
        _atualizar_info_farm()
        try: page.update()
        except Exception: pass

    def _limpar_farm(e=None):
        farm_id[0] = None
        farm_chip.visible = False
        tf_farm.value = ""; tf_farm.visible = True
        farm_sugs.controls.clear(); farm_sugs.visible = False
        farm_info_col.controls.clear(); farm_info_col.visible = False
        try: page.update()
        except Exception: pass

    farm_chip.on_click = _limpar_farm

    def _filtrar_farm(e):
        termo = (tf_farm.value or "").strip().upper()
        farm_sugs.controls.clear()
        if not termo:
            farm_sugs.visible = False
            try: page.update()
            except Exception: pass
            return
        matches = [f for f in farmas
                   if termo in (f.get("nome_exibicao") or f["nome"]).upper()
                   or termo in (f.get("razao_social") or "").upper()][:6]
        for f in matches:
            nome_exib = f.get("nome_exibicao") or f["nome"]
            razao     = f.get("razao_social") or ""
            def _sel(e, ff=f, ne=nome_exib):
                farm_id[0] = ff["id"]
                _mostrar_chip(ne)
            farm_sugs.controls.append(ft.Container(
                content=ft.Column([
                    ft.Text(nome_exib, size=12, color=TXT, weight=ft.FontWeight.W_600),
                    ft.Text(razao, size=10, color=MUT)
                        if razao and razao != nome_exib else ft.Container(),
                ], spacing=1, tight=True),
                bgcolor=CARD, border_radius=6,
                padding=ft.padding.symmetric(horizontal=8, vertical=6),
                border=ft.border.all(1, BD), on_click=_sel, ink=True,
            ))
        if not matches:
            def _cad(e, nome=termo.title()):
                nid = salvar_farmacia({"id": None, "nome": nome, "ativo": 1})
                farmas.append({"id": nid, "nome": nome, "nome_exibicao": nome})
                farm_id[0] = nid
                _mostrar_chip(nome)
            farm_sugs.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("add_circle_outline_rounded", size=12, color=VERD),
                    ft.Text(f'Cadastrar "{termo.title()}"', size=12, color=VERD),
                ], spacing=4),
                bgcolor=ft.Colors.with_opacity(0.08, VERD), border_radius=6,
                padding=ft.padding.symmetric(horizontal=8, vertical=6),
                border=ft.border.all(1, ft.Colors.with_opacity(0.3, VERD)),
                on_click=_cad, ink=True,
            ))
        farm_sugs.visible = True
        try: page.update()
        except Exception: pass

    tf_farm.on_change = _filtrar_farm

    from shared.date_field import campo_data as _campo_data
    row_data, f_data = _campo_data(
        page, label="Data",
        value=nota.get("data") or "",
        obrigatorio=False, cor_acento=AZUL, largura=None,
    )
    f_obs  = _tf("Observações", nota.get("observacoes") or "",
                 multiline=True, min_lines=2)

    # ── Itens com devolução ──────────────────────────
    itens_col = ft.Column(spacing=6)

    def _rebuild_itens():
        itens_col.controls.clear()
        itens = listar_itens_compra(nota["id"])
        if not itens:
            itens_col.controls.append(ft.Text("Nenhum item.", size=12, color=MUT))
            try: page.update()
            except Exception: pass
            return
        for it in itens:
            iid      = it["id"]
            qtd_orig = it.get("quantidade_emb") or 1
            qtd_dev  = it.get("quantidade_devolvida") or 0
            qtd_disp = qtd_orig - qtd_dev
            nome_r   = it.get("remedio_nome") or it.get("nome_nf") or ""
            nome_nf  = it.get("nome_nf") or ""
            preco    = it.get("preco_total") or 0.0
            cor      = MUT if qtd_disp == 0 else TXT

            status_txt = ""
            status_cor = MUT
            if qtd_dev > 0 and qtd_disp > 0:
                status_txt = f"Dev parcial: {qtd_dev}"
                status_cor = AMAR
            elif qtd_disp == 0:
                status_txt = "Devolvido"
                status_cor = VERM

            f_dev = ft.TextField(
                value="", label="Qtd devolver",
                bgcolor=CARD, border_color=BD2, focused_border_color=VERM,
                label_style=ft.TextStyle(color=SEC, size=9),
                text_style=ft.TextStyle(color=TXT, size=12),
                border_radius=6, width=110,
                keyboard_type=ft.KeyboardType.NUMBER,
            )

            def _dev(e, ii=iid, fd=f_dev):
                try: qtd_d = int(fd.value or 0)
                except Exception: qtd_d = 0
                if qtd_d > 0:
                    devolver_item_compra(ii, qtd_d)
                    _rebuild_itens()

            btn_dev = ft.Container(
                content=ft.Row([
                    ft.Icon("undo_rounded", size=13, color=VERM),
                    ft.Text("Devolver", size=11, color=VERM),
                ], spacing=4, tight=True),
                bgcolor=ft.Colors.with_opacity(0.08, VERM),
                border=ft.border.all(1, ft.Colors.with_opacity(0.3, VERM)),
                border_radius=6, ink=True,
                padding=ft.padding.symmetric(horizontal=8, vertical=6),
                on_click=_dev, visible=qtd_disp > 0,
            )

            itens_col.controls.append(ft.Container(
                content=ft.Column([
                    ft.Text(nome_r, size=13, color=cor, weight=ft.FontWeight.W_600),
                    ft.Text(f"NF: {nome_nf}", size=10, color=MUT)
                        if nome_nf != nome_r else ft.Container(),
                    ft.Row([
                        ft.Text(f"Qtd: {qtd_orig}", size=10, color=SEC),
                        ft.Text(f"R$ {preco:.2f}", size=10, color=SEC),
                        ft.Text(status_txt, size=10, color=status_cor,
                                weight=ft.FontWeight.W_600)
                            if status_txt else ft.Container(),
                    ], spacing=8),
                    ft.Row([f_dev, btn_dev], spacing=8,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER)
                        if qtd_disp > 0 else ft.Container(),
                ], spacing=4),
                bgcolor=CARD, border_radius=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                border=ft.Border(
                    left=ft.BorderSide(2, VERM if qtd_disp == 0 else VERD),
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
            ))
        try: page.update()
        except Exception: pass

    _rebuild_itens()

    # ── Salvar ───────────────────────────────────────
    def _salvar(e):
        atualizar_compra_nf(nota["id"], {
            "farmacia_id": farm_id[0],
            "data":        f_data.value.strip() or nota.get("data"),
            "observacoes": f_obs.value.strip() or None,
        })
        import threading as _thr
        def _sync():
            try:
                from backup.drive_backup import fazer_backup
                fazer_backup(forcar=True)
            except Exception as ex:
                import logging; logging.getLogger(__name__).warning("[COMPRAS] sync: %s", ex)
        _thr.Thread(target=_sync, daemon=True).start()
        on_voltar()

    btn_salvar = ft.Container(
        content=ft.Row([
            ft.Icon("save_rounded", size=14, color=BG),
            ft.Text("Salvar", size=13, color=BG, weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        bgcolor=AZUL, border_radius=8, ink=True,
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        on_click=_salvar,
    )

    lay = Layout(page)
    cab = lay.criar_cabecalho(
        "Editar Compra", on_voltar,
        icone_titulo="edit_rounded", cor_titulo=AZUL,
    )
    conteudo = ft.Column([
        _label_sec("FORNECEDOR"),
        ft.Text("Vincule a razão social da NF-e ao fornecedor cadastrado (nome fantasia)",
                size=10, color=MUT),
        farm_info_col,
        farm_chip, tf_farm, farm_sugs,
        ft.Container(height=2),
        row_data, f_obs,
        ft.Container(height=4),
        _label_sec("ITENS DA COMPRA", VERD),
        ft.Text("Registre devoluções parciais por item", size=10, color=MUT),
        itens_col,
        ft.Container(height=12),
        btn_salvar,
        ft.Container(height=20),
    ], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    wrapper = ft.Container(
        bgcolor=BG, expand=True,
        content=ft.Column([
            ft.Container(height=lay.spacer_topo, bgcolor=BG),
            cab,
            ft.Container(content=conteudo, padding=ft.padding.all(16), expand=True),
        ], expand=True, spacing=0),
    )
    area_ref[0] = ft.Column([wrapper], expand=True, spacing=0)

    # Atualiza info do fornecedor inicial
    _atualizar_info_farm()

    return [area_ref[0]]


def _lista_notas_fiscais(page, on_nova, on_editar=None):
    """View de lista de notas fiscais registradas."""
    from dados.model_prontuario import listar_compras_nf as _listar_nf
    from utils.foto_picker import criar_thumb_drive

    notas = _listar_nf(limit=50)
    col   = ft.Column(spacing=8)

    btn_nova = ft.Container(
        content=ft.Row([
            ft.Icon("add_rounded", size=16, color=BG),
            ft.Text("Nova nota fiscal", size=13, color=BG, weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        bgcolor=VERD, border_radius=10, ink=True,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
    )
    btn_nova.on_click = lambda e: on_nova()

    col.controls.append(ft.Row([
        ft.Text("COMPRAS", size=10, color=MUT, weight=ft.FontWeight.W_700, expand=True),
        btn_nova,
    ]))

    if not notas:
        col.controls.append(ft.Container(
            content=ft.Column([
                ft.Icon("receipt_long_rounded", size=40, color=MUT),
                ft.Text("Nenhuma compra registrada.", size=13, color=SEC),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            padding=ft.padding.symmetric(vertical=40),
            alignment=ft.alignment.center,
        ))
        return col.controls

    for n in notas:
        farm   = n.get("farmacia_nome") or "Fornecedor não informado"
        data   = n.get("data") or ""
        total  = n.get("total") or 0.0
        itens  = n.get("nomes_itens") or ""
        num    = n.get("num_itens") or 0
        foto   = n.get("foto_path") or ""
        did    = n.get("foto_drive_id") or ""
        qr     = n.get("qr_nfe") or ""

        thumb = criar_thumb_drive(
            page, foto, did,
            largura=52, altura=68, border_radius=6,
            icone_vazio="receipt_long_rounded", cor_vazio=VERD,
        )

        itens_txt = itens[:60] + ("..." if len(itens) > 60 else "") if itens else ""

        def _editar(e, nota=n):
            if on_editar:
                on_editar(nota)

        def _cancelar(e, cid=n["id"], farm_nome=farm):
            ov = [None]
            def _fechar(e=None):
                if ov[0] in page.overlay: page.overlay.remove(ov[0])
                try: page.update()
                except Exception: pass

            def _confirmar_cancel(e):
                from dados.model_prontuario import cancelar_compra_nf
                _fechar()
                ok = cancelar_compra_nf(cid)
                if ok:
                    col.controls.clear()
                    col.controls.extend(
                        _lista_notas_fiscais(page, on_nova=on_nova))
                    import threading as _thr_can
                    def _sync_can():
                        try:
                            from backup.drive_backup import fazer_backup
                            fazer_backup(forcar=True)
                        except Exception as ex:
                            logger.warning("[COMPRAS] sync cancel: %s", ex)
                    _thr_can.Thread(target=_sync_can, daemon=True).start()
                try: page.update()
                except Exception: pass

            btn_sim = ft.Container(
                content=ft.Text("Cancelar compra", size=13, color=VERM,
                                weight=ft.FontWeight.W_600),
                bgcolor=ft.Colors.with_opacity(0.10, VERM), border_radius=8,
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
                ink=True, on_click=_confirmar_cancel,
                border=ft.border.all(1, ft.Colors.with_opacity(0.4, VERM)),
            )
            btn_nao = ft.Container(
                content=ft.Text("Manter", size=13, color=SEC),
                bgcolor=BD, border_radius=8,
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
                ink=True, on_click=_fechar,
            )
            ov[0] = ft.Container(
                content=ft.Container(
                    content=ft.Column([
                        ft.Icon("cancel_outlined_rounded", size=32, color=VERM),
                        ft.Container(height=8),
                        ft.Text("Cancelar compra?", size=15, color=TXT,
                                weight=ft.FontWeight.W_700,
                                text_align=ft.TextAlign.CENTER),
                        ft.Text(f"{farm_nome}\nR$ {total:.2f}",
                                size=12, color=SEC,
                                text_align=ft.TextAlign.CENTER),
                        ft.Text("O estoque será revertido.",
                                size=11, color=MUT,
                                text_align=ft.TextAlign.CENTER),
                        ft.Container(height=16),
                        ft.Row([btn_nao, btn_sim], spacing=8,
                               alignment=ft.MainAxisAlignment.CENTER),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                       tight=True, spacing=4),
                    bgcolor=CARD, border_radius=14,
                    padding=ft.padding.all(24), width=300,
                    border=ft.border.all(1, BD2),
                ),
                bgcolor="#CC000000", expand=True,
                alignment=ft.Alignment(0, 0), on_click=_fechar,
            )
            page.overlay.append(ov[0])
            try: page.update()
            except Exception: pass

        btn_menu = ft.PopupMenuButton(
            icon="more_vert_rounded", icon_color=MUT, icon_size=18,
            items=[
                ft.PopupMenuItem(text="Editar", on_click=_editar),
                ft.PopupMenuItem(text="Cancelar compra", on_click=_cancelar),
            ],
        )

        card = ft.Container(
            content=ft.Row([
                thumb,
                ft.Column([
                    ft.Row([
                        ft.Text(farm, size=13, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True),
                        ft.Text(f"R$ {total:.2f}", size=13, color=VERD,
                                weight=ft.FontWeight.W_700),
                        btn_menu,
                    ]),
                    ft.Row([
                        ft.Icon("calendar_today_rounded", size=11, color=MUT),
                        ft.Text(data, size=11, color=SEC),
                        ft.Container(width=8),
                        ft.Icon("medication_rounded", size=11, color=MUT),
                        ft.Text(f"{num} item(s)", size=11, color=SEC),
                    ], spacing=4),
                    ft.Text(itens_txt, size=10, color=MUT, max_lines=1),
                    *([ ft.Row([
                        ft.Icon("qr_code_rounded", size=10, color=AZUL),
                        ft.Text("NF-e vinculada", size=10, color=AZUL),
                    ], spacing=4) ] if qr else []),
                ], spacing=3, expand=True, tight=True),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=CARD, border_radius=10,
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border=ft.Border(
                left=ft.BorderSide(2, VERD),
                top=ft.BorderSide(1, BD),
                bottom=ft.BorderSide(1, BD),
                right=ft.BorderSide(1, BD),
            ),
        )
        col.controls.append(card)

    return col.controls


def _conteudo_compras(page, on_concluido=None):
    """Aba Compras: importa nota fiscal via foto, IA interpreta, registra compra."""
    import os as _os
    area = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    _modo = ["lista"]  # "lista" ou "nova"

    def _mostrar_lista():
        _modo[0] = "lista"
        area.controls.clear()
        area.controls.extend(
            _lista_notas_fiscais(page, on_nova=_mostrar_nova, on_editar=_mostrar_edicao)
        )
        try: page.update()
        except Exception: pass

    def _mostrar_nova():
        _modo[0] = "nova"
        area.controls.clear()
        area.controls.extend(_form_nova_nota(page, on_concluido=_mostrar_lista))
        try: page.update()
        except Exception: pass

    def _mostrar_edicao(nota):
        _modo[0] = "edicao"
        area.controls.clear()
        area.controls.extend(_form_edicao_compra(page, nota, on_voltar=_mostrar_lista))
        try: page.update()
        except Exception: pass

    _mostrar_lista()
    return [area]


def _form_nova_nota(page, on_concluido=None):
    """Formulário de nova nota fiscal. Retorna lista de controles."""
    import os as _os
    area = ft.Column(spacing=10)
    _foto_nf          = [""]   # path local da nota fiscal processada
    _drive_id         = [""]   # drive_file_id após upload
    _remedios_extraidos = [[]] # lista de dicts extraídos pela IA
    _farmacia_id_sel  = [None] # farmacia selecionada

    from dados.model_prontuario import listar_farmacias as _listar_farm
    _farmacias = _listar_farm(so_ativas=False)

    txt_status = ft.Text("", size=12, color=VERD)
    progress   = ft.ProgressBar(visible=False, color=VERD, bgcolor=BD, height=3)

    # ── Picker de farmácia ───────────────────────────────
    farm_chip = ft.Container(
        content=ft.Row([
            ft.Icon("local_pharmacy_rounded", size=13, color=AZUL),
            ft.Text("", size=12, color=AZUL, weight=ft.FontWeight.W_600),
            ft.Icon("close_rounded", size=12, color=AZUL),
        ], spacing=5, tight=True),
        bgcolor=ft.Colors.with_opacity(0.12, AZUL), border_radius=14,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        visible=False,
    )
    tf_farm = ft.TextField(
        hint_text="Buscar farmácia / fornecedor...",
        prefix_icon="search_rounded",
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        hint_style=ft.TextStyle(color=MUT, size=11),
        text_style=ft.TextStyle(color=TXT, size=12),
        border_radius=6, expand=True, height=42,
    )
    farm_sugs = ft.Column(spacing=2, visible=False)

    def _mostrar_farm_chip(nome):
        farm_chip.content.controls[1].value = nome
        farm_chip.visible = True
        tf_farm.visible   = False
        farm_sugs.controls.clear(); farm_sugs.visible = False
        try: page.update()
        except Exception: pass

    def _limpar_farm(e=None):
        _farmacia_id_sel[0] = None
        farm_chip.visible = False
        tf_farm.value = ""; tf_farm.visible = True
        farm_sugs.controls.clear(); farm_sugs.visible = False
        try: page.update()
        except Exception: pass

    farm_chip.on_click = _limpar_farm

    def _filtrar_farm(e):
        termo = (tf_farm.value or "").strip().upper()
        farm_sugs.controls.clear()
        if not termo:
            farm_sugs.visible = False
            try: page.update()
            except Exception: pass
            return
        matches = [f for f in _farmacias
                   if termo in (f.get("nome_exibicao") or f["nome"]).upper()
                   or termo in (f.get("razao_social") or "").upper()
                   or termo in (f.get("endereco") or "").upper()][:6]
        for f in matches:
            nome_exib = f.get("nome_exibicao") or f["nome"]
            razao_    = f.get("razao_social") or ""
            def _sel(e, farm=f, ne=nome_exib):
                _farmacia_id_sel[0] = farm["id"]
                _mostrar_farm_chip(ne)
            farm_sugs.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("storefront_rounded", size=13, color=AZUL),
                    ft.Column([
                        ft.Text(nome_exib, size=12, color=TXT,
                                weight=ft.FontWeight.W_600),
                        ft.Text(razao_, size=10, color=MUT)
                            if razao_ and razao_ != nome_exib else ft.Container(),
                    ], spacing=1, expand=True, tight=True),
                ], spacing=6),
                bgcolor=CARD, border_radius=6,
                padding=ft.padding.symmetric(horizontal=8, vertical=6),
                border=ft.border.all(1, BD), on_click=_sel, ink=True,
            ))
        if matches:
            farm_sugs.visible = True
        else:
            # Nenhum resultado — oferece cadastrar com o nome digitado
            def _cadastrar_novo(e, nome=termo.title()):
                from dados.model_prontuario import salvar_farmacia
                novo_id = salvar_farmacia({
                    "id": None, "nome": nome, "ativo": 1,
                })
                _farmacias.append({"id": novo_id, "nome": nome, "endereco": ""})
                _farmacia_id_sel[0] = novo_id
                _mostrar_farm_chip(nome)

            farm_sugs.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("add_circle_outline_rounded", size=13, color=VERD),
                    ft.Text(f'Cadastrar "{termo.title()}"', size=12, color=VERD),
                ], spacing=6),
                bgcolor=ft.Colors.with_opacity(0.08, VERD), border_radius=6,
                padding=ft.padding.symmetric(horizontal=8, vertical=6),
                border=ft.border.all(1, ft.Colors.with_opacity(0.3, VERD)),
                on_click=_cadastrar_novo, ink=True,
            ))
            farm_sugs.visible = True
        try: page.update()
        except Exception: pass

    tf_farm.on_change = _filtrar_farm

    secao_farmacia = ft.Column([
        ft.Text("FARMÁCIA / FORNECEDOR", size=10, color=MUT,
                weight=ft.FontWeight.W_700),
        farm_chip, tf_farm, farm_sugs,
    ], spacing=4)

    # ── Preview da nota ──────────────────────────────────
    preview_box = ft.Container(
        width=320, height=220, border_radius=10,
        bgcolor=BD,
        border=ft.border.all(1, BD2),
        alignment=ft.Alignment(0, 0),
        content=ft.Column([
            ft.Icon("receipt_long_rounded", size=40, color=MUT),
            ft.Text("Nenhuma nota selecionada", size=12, color=MUT),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.CENTER, spacing=8),
    )

    # ── Chave / URL NF-e ─────────────────────────────────
    _qr_nfe = [""]

    tf_chave = ft.TextField(
        hint_text="Chave NF-e ou URL SEFAZ (preenchido automaticamente ou edite)",
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        hint_style=ft.TextStyle(color=MUT, size=10),
        text_style=ft.TextStyle(color=TXT, size=11),
        border_radius=6, expand=True,
        prefix_icon="qr_code_rounded",
    )

    btn_consultar_nfe = ft.Container(
        content=ft.Row([
            ft.Icon("travel_explore_rounded", size=14, color=AZUL),
            ft.Text("Consultar SEFAZ", size=12, color=AZUL, weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        bgcolor=ft.Colors.with_opacity(0.12, AZUL),
        border=ft.border.all(1, ft.Colors.with_opacity(0.4, AZUL)),
        border_radius=8, ink=True, visible=False,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
    )

    secao_qr = ft.Column([
        ft.Text("CHAVE / URL NF-e", size=9, color=MUT, weight=ft.FontWeight.W_700),
        tf_chave,
        btn_consultar_nfe,
    ], spacing=6, visible=False)

    def _set_chave(url: str, readonly: bool = False):
        """Atualiza campo de chave. Formata em blocos se forem dígitos puros."""
        _qr_nfe[0] = url
        # Formata se forem só dígitos (chave extraída pela IA)
        if url and not url.startswith("http"):
            import re as _re
            digitos = _re.sub(r'\D', '', url)[:44]
            display = ' '.join(digitos[i:i+4] for i in range(0, len(digitos), 4))
        else:
            display = url
        tf_chave.value = display
        tf_chave.read_only = readonly
        tf_chave.border_color = VERD if readonly else BD2
        btn_consultar_nfe.visible = bool(url)
        secao_qr.visible = True
        if url:
            btn_extrair.visible = False
        try: page.update()
        except Exception: pass

    def _formatar_chave(valor: str) -> str:
        """Formata chave em blocos de 4 dígitos: XXXX XXXX XXXX ..."""
        import re as _re
        digitos = _re.sub(r'\D', '', valor)[:44]
        return ' '.join(digitos[i:i+4] for i in range(0, len(digitos), 4))

    def tf_chave_on_change(e):
        raw = tf_chave.value or ""
        # Só formata se não for URL
        if not raw.strip().startswith("http"):
            import re as _re
            digitos = _re.sub(r'\D', '', raw)[:44]
            formatado = ' '.join(digitos[i:i+4] for i in range(0, len(digitos), 4))
            if formatado != raw:
                tf_chave.value = formatado
        _qr_nfe[0] = tf_chave.value or ""
        btn_consultar_nfe.visible = bool(_qr_nfe[0].strip())
        if not _qr_nfe[0].strip() and _foto_nf[0]:
            btn_extrair.visible = True
        try: page.update()
        except Exception: pass

    tf_chave.on_change = tf_chave_on_change

    def _detectar_qr(path_foto: str):
        """
        Tenta detectar QR na foto.
        Se falhar, usa IA para extrair a chave de acesso impressa (44 dígitos).
        Se IA também falhar, deixa campo editável para digitação manual.
        """
        def _run():
            # Passo 1: QR code
            try:
                from utils.image_processor import detectar_qr_nfe
                url = detectar_qr_nfe(path_foto)
                if url:
                    _set_chave(url, readonly=True)
                    logger.info("[COMPRAS] QR detectado: %s", url[:60])
                    return
            except Exception as ex:
                logger.warning("[COMPRAS] detectar QR: %s", ex)

            # Passo 2: IA extrai chave impressa na nota
            logger.info("[COMPRAS] QR não detectado — tentando extrair chave via IA")
            try:
                import base64, json as _json
                from utils.claudia_engine import get_client
                with open(path_foto, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                ext  = path_foto.rsplit(".", 1)[-1].lower()
                mime = {"jpg":"image/jpeg","jpeg":"image/jpeg",
                        "png":"image/png","webp":"image/webp"}.get(ext, "image/jpeg")
                client = get_client()
                resp = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=200,
                    messages=[{"role": "user", "content": [
                        {"type": "image", "source": {
                            "type": "base64", "media_type": mime, "data": img_b64}},
                        {"type": "text", "text": (
                            "Nesta nota fiscal brasileira, encontre a CHAVE DE ACESSO "
                            "(44 dígitos numéricos, normalmente impressa abaixo do QR code "
                            "em grupos separados por espaço).\n"
                            "Retorne APENAS os 44 dígitos sem espaços, sem nenhum outro texto.\n"
                            "Se não encontrar, retorne exatamente: NAO_ENCONTRADO"
                        )},
                    ]}],
                )
                raw = "".join(b.text for b in resp.content
                              if hasattr(b, "text")).strip()
                import re as _re
                digitos = _re.sub(r'\D', '', raw)
                if len(digitos) == 44:
                    _set_chave(digitos)
                    logger.info("[COMPRAS] chave extraída via IA: %s...", digitos[:8])
                else:
                    logger.info("[COMPRAS] IA não encontrou chave válida: %r", raw[:40])
                    # Passo 3: campo fica editável com hint
                    txt_status.value = "Chave não detectada — digite os 44 dígitos manualmente"
                    txt_status.color = AMAR
                    try: page.update()
                    except Exception: pass
            except Exception as ex:
                logger.warning("[COMPRAS] extrair chave IA: %s", ex)
                txt_status.value = "Digite a chave de acesso (44 dígitos)"
                txt_status.color = AMAR
                try: page.update()
                except Exception: pass

        import threading as _thr
        _thr.Thread(target=_run, daemon=True).start()

    # Mapa de URLs de consulta NFC-e por código de UF (posições 0-1 da chave)
    _SEFAZ_URL = {
        "11": "https://www.sefin.ro.gov.br/nfce/consulta",
        "12": "https://www.sefaz.ac.gov.br/nfce/consulta",
        "13": "https://systems.sefaz.am.gov.br/nfce/consulta",
        "14": "https://www.sefaz.rr.gov.br/nfce/consulta",
        "15": "https://app.sefa.pa.gov.br/nfce/consulta",
        "16": "https://www.sefaz.ap.gov.br/nfce/consulta",
        "17": "https://www.sefaz.to.gov.br/nfce/consulta",
        "21": "https://www.nfce.sefaz.ma.gov.br/portal/consulta",
        "22": "https://www.sefaz.pi.gov.br/nfce/consulta",
        "23": "https://nfce.sefaz.ce.gov.br/pages/consultaNFe.jsf",
        "24": "https://nfce.set.rn.gov.br/portalDFe/NFCe/ConsultaNFCe.aspx",
        "25": "https://www.sefaz.pb.gov.br/nfce/consulta",
        "26": "https://nfce.sefa.pe.gov.br/p/consulta",
        "27": "https://www.sefaz.al.gov.br/nfce/consulta",
        "28": "https://nfce.sefaz.se.gov.br/portal/consulta",
        "29": "https://www.nfe.ba.gov.br/portalnfce/sistema/consultanfce.aspx",
        "31": "https://nfce.fazenda.mg.gov.br/portalnfce",
        "32": "http://app.sefaz.es.gov.br/ConsultaNFCe",
        "33": "https://www.nfce.fazenda.rj.gov.br/consulta",
        "35": "https://www.nfce.fazenda.sp.gov.br/consulta",
        "41": "https://www.nfce.fazenda.pr.gov.br/nfce/consulta",
        "42": "https://www.sef.sc.gov.br/nfce/consulta",
        "43": "https://www.nfe.sefaz.rs.gov.br/NFCE/consulta",
        "50": "https://www.nfce.fazenda.ms.gov.br/consulta",
        "51": "https://www.sefaz.mt.gov.br/nfce/consultanfce",
        "52": "https://www.nfce.go.gov.br/post/ver_nfce_nacional",
        "53": "https://www.nfe.fazenda.df.gov.br/nfce/consulta",
    }

    def _resolver_url_nfe(valor: str) -> tuple:
        """
        Recebe URL completa ou chave (44 dígitos).
        Retorna (url, erro) — erro é None se OK, string descritiva se inválido.
        """
        import re as _re
        valor = valor.strip()

        # Já é URL válida
        if valor.startswith("http"):
            return valor, None

        # Extrai só dígitos
        chave = _re.sub(r'\D', '', valor)

        if len(chave) == 0:
            return "", "Campo vazio — cole a URL do QR ou os 44 dígitos da chave de acesso"

        if len(chave) < 44:
            faltam = 44 - len(chave)
            return "", (f"Chave incompleta: {len(chave)} dígitos (faltam {faltam}). "
                        f"A chave de acesso tem 44 dígitos — verifique a nota fiscal")

        chave    = chave[:44]
        cod_uf   = chave[:2]
        base     = _SEFAZ_URL.get(cod_uf, "")
        if base:
            return f"{base}?p={chave}|2|1|1", None
        # UF não mapeada — tenta portal nacional
        return (f"https://www.nfe.fazenda.gov.br/portal/consultaRecaptcha.aspx"
                f"?tipoConsulta=completa&tipoConteudo=7PhJ+gAVw2g=&nfe={chave}"), None

    def _consultar_nfe(e):
        valor = (tf_chave.value or _qr_nfe[0] or "").strip()
        if not valor:
            txt_status.value = "Informe a chave de acesso (44 dígitos) ou URL do QR"
            txt_status.color = AMAR
            try: page.update()
            except Exception: pass
            return

        url, erro_resolucao = _resolver_url_nfe(valor)
        if erro_resolucao:
            txt_status.value = erro_resolucao
            txt_status.color = VERM
            tf_chave.border_color = VERM
            try: page.update()
            except Exception: pass
            return

        tf_chave.border_color = VERD
        txt_status.value = "Consultando SEFAZ..."
        txt_status.color = AZUL
        progress.visible = True
        btn_consultar_nfe.disabled = True
        try: page.update()
        except Exception: pass

        def _run():
            try:
                import urllib.request, json
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "pt-BR,pt;q=0.9",
                    }
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    html = resp.read().decode("utf-8", errors="replace")

                from utils.claudia_engine import get_client
                client = get_client()
                resp_ia = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": (
                        "Este é o HTML de uma página de consulta NFC-e/NF-e da SEFAZ brasileira.\n"
                        "Extraia com precisão:\n"
                        "1. Razão social e CNPJ do EMITENTE (farmácia/loja)\n"
                        "2. Endereço do emitente\n"
                        "3. TODOS os itens da nota com: descrição exata, quantidade, "
                        "valor unitário, valor total\n"
                        "4. Total da nota\n\n"
                        "Retorne APENAS JSON válido sem markdown:\n"
                        '{"emitente":{"nome":"","cnpj":"","endereco":""},'
                        '"itens":[{"nome":"descrição do produto","quantidade":1,'
                        '"preco_unitario":0.00,"preco_total":0.00,'
                        '"dosagem":null,"comprimidos_embalagem":null}],'
                        '"total":0.00}\n\n'
                        "IMPORTANTE: extraia TODOS os itens da nota, não resuma.\n\n"
                        f"HTML:\n{html[:15000]}"
                    )}],
                )
                raw = "".join(b.text for b in resp_ia.content if hasattr(b, "text")).strip()
                import re as _re2
                m = _re2.search(r'\{.*\}', raw, _re2.DOTALL)
                dados = json.loads(m.group()) if m else {}
                _on_nfe_resultado(dados=dados)
            except Exception as ex:
                logger.error("[COMPRAS] consultar NF-e: %s", ex)
                _on_nfe_resultado(erro=str(ex)[:120])
            finally:
                progress.visible = False
                btn_consultar_nfe.disabled = False

        def _on_nfe_resultado(dados=None, erro=None):
            if erro:
                txt_status.value = f"Erro NF-e: {erro}"
                txt_status.color = VERM
                try: page.update()
                except Exception: pass
                return
            emit = (dados or {}).get("emitente", {})
            if emit.get("nome"):
                from dados.model_prontuario import listar_farmacias, salvar_farmacia
                farmas = listar_farmacias(so_ativas=False)
                match = next((f for f in farmas
                              if emit["nome"].upper() in f["nome"].upper()
                              or f["nome"].upper() in emit["nome"].upper()), None)
                if match:
                    _farmacia_id_sel[0] = match["id"]
                    _mostrar_farm_chip(match["nome"])
                else:
                    novo_id = salvar_farmacia({
                        "id": None, "nome": emit["nome"],
                        "endereco": emit.get("endereco", ""), "ativo": 1,
                    })
                    _farmacia_id_sel[0] = novo_id
                    _mostrar_farm_chip(emit["nome"])
                    _farmacias.append({"id": novo_id, "nome": emit["nome"],
                                       "endereco": emit.get("endereco", "")})
            itens = (dados or {}).get("itens", [])
            if itens:
                _remedios_extraidos[0] = itens
                _rebuild_tabela(itens)
                txt_status.value = f"✓ NF-e SEFAZ: {len(itens)} item(s)"
                txt_status.color = VERD
                btn_confirmar.visible = True
                try: page.update()
                except Exception: pass
            else:
                # SEFAZ não retornou itens (JS dinâmico) — extrai da foto automaticamente
                if _foto_nf[0]:
                    txt_status.value = "SEFAZ sem itens — extraindo da foto com IA..."
                    txt_status.color = AZUL
                    try: page.update()
                    except Exception: pass
                    _extrair_ia(None)
                else:
                    txt_status.value = "SEFAZ consultada — adicione a foto para extrair os itens"
                    txt_status.color = AMAR
                    btn_extrair.visible = True
                    try: page.update()
                    except Exception: pass

        import threading as _thr
        _thr.Thread(target=_run, daemon=True).start()

    btn_consultar_nfe.on_click = _consultar_nfe

    # ── Tabela de itens extraídos ────────────────────────
    tabela_itens = ft.Column(spacing=6, visible=False)

    from dados.model_prontuario import listar_remedios as _listar_rems
    _rems_cadastrados = _listar_rems(so_ativos=False)

    def _campo_rem(label, valor, largura=None, keyboard=ft.KeyboardType.TEXT):
        kw = dict(
            value=valor, label=label,
            bgcolor=CARD, border_color=BD2, focused_border_color=VERD,
            label_style=ft.TextStyle(color=SEC, size=10),
            text_style=ft.TextStyle(color=TXT, size=12),
            border_radius=6,
        )
        if largura:
            kw["width"] = largura
        else:
            kw["expand"] = True
        if keyboard != ft.KeyboardType.TEXT:
            kw["keyboard_type"] = keyboard
        return ft.TextField(**kw)

    def _picker_remedio(page, rems, id_sel, chip_ctrl, tf_ctrl):
        """Autocomplete inline para vincular ao remédio cadastrado."""
        sugs = ft.Column(spacing=2, visible=False)

        def _mostrar_chip(nome):
            chip_ctrl.content.controls[1].value = nome
            chip_ctrl.visible = True
            tf_ctrl.visible   = False
            sugs.controls.clear(); sugs.visible = False
            try: page.update()
            except Exception: pass

        def _limpar(e=None):
            id_sel[0] = None
            chip_ctrl.visible = False
            tf_ctrl.value     = ""
            tf_ctrl.visible   = True
            sugs.controls.clear(); sugs.visible = False
            try: page.update()
            except Exception: pass

        chip_ctrl.on_click = _limpar

        def _filtrar(e):
            termo = (tf_ctrl.value or "").strip().upper()
            sugs.controls.clear()
            if not termo:
                sugs.visible = False
                try: page.update()
                except Exception: pass
                return
            matches = [r for r in rems
                       if termo in r["nome"].upper()
                       or termo in (r.get("principio_ativo") or "").upper()][:6]
            for r in matches:
                def _sel(e, rem=r):
                    id_sel[0] = rem["id"]
                    _mostrar_chip(rem["nome"])
                sub = ft.Text(r.get("principio_ativo") or "", size=10, color=MUT)
                sugs.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Icon("medication_rounded", size=13, color=VERD),
                        ft.Column([
                            ft.Text(r["nome"], size=12, color=TXT),
                            sub if sub.value else ft.Container(),
                        ], spacing=1, expand=True, tight=True),
                    ], spacing=6),
                    bgcolor=CARD, border_radius=6,
                    padding=ft.padding.symmetric(horizontal=8, vertical=6),
                    border=ft.border.all(1, BD), on_click=_sel, ink=True,
                ))
            sugs.visible = bool(matches)
            try: page.update()
            except Exception: pass

        tf_ctrl.on_change = _filtrar
        return sugs

    def _rebuild_tabela(itens):
        tabela_itens.controls.clear()
        if not itens:
            tabela_itens.visible = False
            btn_confirmar.visible = False
            try: page.update()
            except Exception: pass
            return

        def _deletar_item(idx):
            del _remedios_extraidos[0][idx]
            _rebuild_tabela(_remedios_extraidos[0])
            btn_confirmar.visible = bool(_remedios_extraidos[0])
            try: page.update()
            except Exception: pass

        def _adicionar_item(e=None):
            _remedios_extraidos[0].append({
                "nome": "", "dosagem": "", "quantidade": 1,
                "preco_unitario": "", "comprimidos_embalagem": "",
            })
            _rebuild_tabela(_remedios_extraidos[0])
            btn_confirmar.visible = True
            try: page.update()
            except Exception: pass

        # Cabeçalho com contagem, reprocessar e adicionar item
        btn_reprocessar = ft.Container(
            content=ft.Row([
                ft.Icon("refresh_rounded", size=13, color=ROXO),
                ft.Text("Reprocessar", size=11, color=ROXO),
            ], spacing=4, tight=True),
            bgcolor=ft.Colors.with_opacity(0.10, ROXO),
            border=ft.border.all(1, ft.Colors.with_opacity(0.3, ROXO)),
            border_radius=6, ink=True,
            padding=ft.padding.symmetric(horizontal=8, vertical=5),
            on_click=lambda e: _extrair_ia(e) if _foto_nf[0] else None,
            visible=bool(_foto_nf[0]),
        )
        btn_add_item = ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=13, color=VERD),
                ft.Text("Adicionar", size=11, color=VERD),
            ], spacing=4, tight=True),
            bgcolor=ft.Colors.with_opacity(0.10, VERD),
            border=ft.border.all(1, ft.Colors.with_opacity(0.3, VERD)),
            border_radius=6, ink=True,
            padding=ft.padding.symmetric(horizontal=8, vertical=5),
            on_click=_adicionar_item,
        )
        tabela_itens.controls.append(ft.Row([
            ft.Icon("check_circle_outline_rounded", size=13, color=VERD),
            ft.Text(f"{len(itens)} item(s) extraído(s)", size=12, color=VERD,
                    weight=ft.FontWeight.W_600, expand=True),
            btn_reprocessar,
            btn_add_item,
        ], spacing=8))

        for idx, it in enumerate(itens):
            sel = ft.Checkbox(value=True, active_color=VERD)

            f_nome_nf = _campo_rem("Nome na nota (generico/marca)", it.get("nome", ""))

            rem_id_sel = [None]
            chip_rem = ft.Container(
                content=ft.Row([
                    ft.Icon("medication_rounded", size=13, color=VERD),
                    ft.Text("", size=12, color=VERD, weight=ft.FontWeight.W_600),
                    ft.Icon("close_rounded", size=12, color=VERD),
                ], spacing=5, tight=True),
                bgcolor=ft.Colors.with_opacity(0.12, VERD), border_radius=14,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                visible=False,
            )
            tf_rem = ft.TextField(
                hint_text="Vincular ao remédio cadastrado...",
                prefix_icon="search_rounded",
                bgcolor=CARD, border_color=BD2, focused_border_color=VERD,
                hint_style=ft.TextStyle(color=MUT, size=11),
                text_style=ft.TextStyle(color=TXT, size=12),
                border_radius=6, expand=True, height=40,
            )
            sugs_col = _picker_remedio(page, _rems_cadastrados, rem_id_sel, chip_rem, tf_rem)

            f_dosagem = _campo_rem("Dosagem", it.get("dosagem") or "", largura=100)
            f_comprim = _campo_rem("Comprim/emb", str(it.get("comprimidos_embalagem") or ""),
                                   largura=90, keyboard=ft.KeyboardType.NUMBER)
            f_qtd     = _campo_rem("Qtd emb", str(it.get("quantidade", 1)),
                                   largura=70, keyboard=ft.KeyboardType.NUMBER)
            f_preco   = _campo_rem("R$ unit", str(it.get("preco_unitario", "")),
                                   largura=80, keyboard=ft.KeyboardType.NUMBER)

            it["_sel"]        = sel
            it["_f_nome_nf"]  = f_nome_nf
            it["_rem_id_sel"] = rem_id_sel
            it["_f_dosagem"]  = f_dosagem
            it["_f_comprim"]  = f_comprim
            it["_f_qtd"]      = f_qtd
            it["_f_preco"]    = f_preco

            btn_del = ft.Container(
                content=ft.Icon("delete_outline_rounded", size=16, color=VERM),
                width=30, height=30, border_radius=6,
                alignment=ft.alignment.center, ink=True,
                on_click=lambda e, i=idx: _deletar_item(i),
                tooltip="Remover item",
            )

            tabela_itens.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([sel, f_nome_nf, btn_del], spacing=6,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row([
                        ft.Column([
                            ft.Text("REMÉDIO CADASTRADO", size=9, color=MUT,
                                    weight=ft.FontWeight.W_700),
                            chip_rem, tf_rem, sugs_col,
                        ], spacing=3, expand=True),
                    ], spacing=6),
                    ft.Row([f_dosagem, f_comprim, f_qtd, f_preco], spacing=6),
                ], spacing=6),
                bgcolor=CARD, border_radius=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=10),
                border=ft.border.all(1, BD2),
            ))

        tabela_itens.visible = True
        try: page.update()
        except Exception: pass

    # ── Helper de seleção de arquivo com callback direto ─
    def _abrir_picker(titulo, on_caminho, on_erro=None):
        def _picker():
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk(); root.withdraw()
                root.attributes("-topmost", True)
                caminho = filedialog.askopenfilename(
                    title=titulo,
                    filetypes=[("Imagens", "*.jpg *.jpeg *.png *.webp")],
                )
                root.destroy()
                if caminho:
                    on_caminho(caminho)
            except Exception as ex:
                if on_erro:
                    on_erro(str(ex))
        import threading
        threading.Thread(target=_picker, daemon=True).start()

    # ── Selecionar foto da nota fiscal ──────────────────
    def _selecionar_nf(e):
        def _on_caminho(caminho):
            try:
                from utils.image_processor import confirmar_processamento_documento
                pasta_tmp = _os.path.join(_os.path.dirname(
                    _os.path.abspath(__file__)), "..", "assets", "notas_fiscais")
                resultado = confirmar_processamento_documento(caminho, pasta_tmp)
                if resultado is None:
                    return
                _foto_nf[0] = resultado
            except Exception:
                _foto_nf[0] = caminho

            preview_box.content = ft.Image(
                src=_foto_nf[0], width=320, height=220,
                fit=ft.ImageFit.CONTAIN, border_radius=10,
            )
            preview_box.bgcolor = None
            txt_status.value = "Nota carregada — detectando chave NF-e..."
            txt_status.color = SEC
            # Mostra Extrair com IA como fallback; QR pode ocultá-lo
            btn_extrair.visible = True
            tf_chave.value = ""
            tf_chave.read_only = False
            tf_chave.border_color = BD2
            _qr_nfe[0] = ""
            btn_consultar_nfe.visible = False
            secao_qr.visible = True
            _detectar_qr(_foto_nf[0])
            try: page.update()
            except Exception: pass

        def _on_erro(msg):
            txt_status.value = f"Erro: {msg}"
            txt_status.color = VERM
            try: page.update()
            except Exception: pass

        _abrir_picker("Foto da nota fiscal", _on_caminho, _on_erro)


    btn_selecionar = ft.Container(
        content=ft.Row([
            ft.Icon("add_photo_alternate_rounded", size=16, color=BG),
            ft.Text("Nota fiscal", size=13, color=BG, weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=VERD, border_radius=10, ink=True,
        padding=ft.padding.symmetric(horizontal=14, vertical=12),
    )
    btn_selecionar.on_click = _selecionar_nf

    # ── Extrair com IA ───────────────────────────────────
    btn_extrair = ft.Container(
        content=ft.Row([
            ft.Icon("auto_awesome_rounded", size=15, color=ROXO),
            ft.Text("Extrair com IA", size=13, color=ROXO,
                    weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        bgcolor=ft.Colors.with_opacity(0.12, ROXO),
        border=ft.border.all(1, ft.Colors.with_opacity(0.4, ROXO)),
        border_radius=8, ink=True, visible=False,
        padding=ft.padding.symmetric(horizontal=12, vertical=9),
    )

    def _extrair_ia(e):
        if not _foto_nf[0]:
            return
        txt_status.value = "Analisando nota com IA..."
        txt_status.color = AZUL
        btn_extrair.disabled = True
        progress.visible = True
        try: page.update()
        except Exception: pass

        def _analisar():
            try:
                import base64, json, urllib.request
                from dados.model_prontuario import get_config
                api_key = get_config("anthropic_api_key", "")
                with open(_foto_nf[0], "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                ext  = _foto_nf[0].rsplit(".", 1)[-1].lower()
                mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                        "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
                prompt = (
                    "Esta e uma nota fiscal ou cupom de farmacia brasileira.\n"
                    "Extraia as seguintes informacoes e retorne APENAS JSON valido sem markdown:\n"
                    "{\n"
                    '  "emitente": {"nome": "razao social ou null", "cnpj": "so numeros ou null", "endereco": "ou null"},\n'
                    '  "chave_nfe": "44 digitos da chave de acesso ou URL do QR code ou null",\n'
                    '  "total": 0.0,\n'
                    '  "itens": [\n'
                    '    {"nome": "nome exato na nota", "quantidade": 1,\n'
                    '     "preco_unitario": 0.0, "preco_total": 0.0,\n'
                    '     "dosagem": "500mg ou null", "comprimidos_embalagem": 30}\n'
                    "  ]\n"
                    "}\n"
                    "IMPORTANTE: extraia a chave de acesso (44 digitos) ou URL do QR code se visivel na nota."
                )
                headers = {"Content-Type": "application/json",
                           "anthropic-version": "2023-06-01"}
                if api_key:
                    headers["x-api-key"] = api_key
                payload = json.dumps({
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": [
                        {"type": "image", "source": {
                            "type": "base64", "media_type": mime, "data": img_b64}},
                        {"type": "text", "text": prompt},
                    ]}],
                }).encode()
                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=payload, headers=headers, method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read())
                raw = "".join(
                    b.get("text", "") for b in data.get("content", [])
                    if b.get("type") == "text"
                ).strip()
                import re as _re, json as _json2
                # Tenta parsear como objeto {emitente, chave_nfe, itens}
                m_obj = _re.search(r'\{.*\}', raw, _re.DOTALL)
                dados = {}
                if m_obj:
                    try: dados = _json2.loads(m_obj.group())
                    except Exception: pass
                itens = dados.get("itens") or []
                # fallback: tenta array direto
                if not itens:
                    m_arr = _re.search(r'\[.*\]', raw, _re.DOTALL)
                    if m_arr:
                        try: itens = _json2.loads(m_arr.group())
                        except Exception: pass
                _on_ia_resultado(dados=dados, itens=itens)
            except Exception as ex:
                logger.error("[COMPRAS] extrair IA: %s", ex)
                _on_ia_resultado(erro=str(ex)[:80])
            finally:
                btn_extrair.disabled = False
                progress.visible = False
                try: page.update()
                except Exception: pass

        def _on_ia_resultado(dados=None, itens=None, erro=None):
            if erro:
                txt_status.value = f"Erro IA: {erro}"
                txt_status.color = VERM
                try: page.update()
                except Exception: pass
                return

            dados = dados or {}
            itens = itens or []

            # Preenche chave NF-e só se campo ainda vazio (QR tem prioridade)
            chave = dados.get("chave_nfe") or ""
            if chave and not tf_chave.value.strip():
                _set_chave(chave)
                return  # tem URL → não preenche itens, aguarda Consultar SEFAZ

            # Preenche emitente se campo de farmácia ainda vazio
            emit = dados.get("emitente") or {}
            if emit.get("nome") and not _farmacia_id_sel[0]:
                from dados.model_prontuario import listar_farmacias, salvar_farmacia
                farmas = listar_farmacias(so_ativas=False)
                match = next((f for f in farmas
                              if emit["nome"].upper() in f["nome"].upper()
                              or f["nome"].upper() in emit["nome"].upper()), None)
                if match:
                    _farmacia_id_sel[0] = match["id"]
                    _mostrar_farm_chip(match["nome"])
                else:
                    novo_id = salvar_farmacia({
                        "id": None, "nome": emit["nome"],
                        "endereco": emit.get("endereco", ""), "ativo": 1,
                    })
                    _farmacia_id_sel[0] = novo_id
                    _mostrar_farm_chip(emit["nome"])
                    _farmacias.append({"id": novo_id, "nome": emit["nome"],
                                       "endereco": emit.get("endereco", "")})

            _remedios_extraidos[0] = itens
            _rebuild_tabela(itens)
            txt_status.value = (f"✓ {len(itens)} item(s) extraído(s)" if itens
                                else "Nenhum item identificado — edite manualmente")
            txt_status.color = VERD if itens else AMAR
            btn_confirmar.visible = bool(itens)
            try: page.update()
            except Exception: pass

        import threading
        threading.Thread(target=_analisar, daemon=True).start()

    btn_extrair.on_click = _extrair_ia

    # ── Confirmar compra ─────────────────────────────────
    btn_confirmar = ft.Container(
        content=ft.Row([
            ft.Icon("check_rounded", size=16, color=BG),
            ft.Text("Registrar compra", size=13, color=BG,
                    weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=AZUL, border_radius=10, ink=True, visible=False,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
    )

    txt_resultado = ft.Text("", size=12, color=VERD)

    def _confirmar(e):
        from dados.model_prontuario import (
            listar_remedios, salvar_remedio, salvar_compra_nf,
        )
        import datetime as _dt
        hoje      = _dt.date.today().isoformat()
        itens_ui  = _remedios_extraidos[0]
        nao_enc   = []

        existentes = {r["nome"].strip().upper(): r
                      for r in listar_remedios(so_ativos=False)}

        # ── Monta lista de itens para salvar ─────────────
        itens_salvar = []
        for it in itens_ui:
            if not it.get("_sel") or not it["_sel"].value:
                continue
            nome_nf = (it["_f_nome_nf"].value or "").strip()
            if not nome_nf:
                continue

            rem_id_sel = it.get("_rem_id_sel", [None])
            rid = rem_id_sel[0] if rem_id_sel[0] else None

            if not rid:
                chave = nome_nf.upper()
                if chave in existentes:
                    rid = existentes[chave]["id"]
                else:
                    dosagem = (it["_f_dosagem"].value or "").strip() or it.get("dosagem")
                    rid = salvar_remedio({
                        "id": None, "nome": nome_nf,
                        "dosagem": dosagem,
                        "estoque_atual": 0, "estoque_minimo": 5,
                        "ativo": 1, "tipo": "remedio", "prescrito": 0,
                    })
                    nao_enc.append(nome_nf)

            try:
                qtd     = int(it["_f_qtd"].value or 1)
                comprim = int(it["_f_comprim"].value or 0) or None
                preco   = float((it["_f_preco"].value or "0").replace(",", "."))
            except Exception:
                qtd = 1; comprim = None; preco = 0.0

            itens_salvar.append({
                "remedio_id":     rid,
                "nome_nf":        nome_nf,
                "dosagem":        (it["_f_dosagem"].value or "").strip() or None,
                "quantidade_emb": qtd,
                "comprimidos_emb": comprim,
                "preco_unitario": preco,
                "preco_total":    qtd * preco,
            })

        if not itens_salvar:
            txt_resultado.value = "Nenhum item selecionado."
            txt_resultado.color = AMAR
            try: page.update()
            except Exception: pass
            return

        total_nf = sum(it["preco_total"] for it in itens_salvar)

        # ── Move foto para pasta definitiva ──────────────
        foto_final = _foto_nf[0] or None
        if foto_final:
            import shutil as _sh
            _root_dir = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
            pasta_tmp = _os.path.join(_root_dir, "assets", "compras", "tmp")
            _os.makedirs(pasta_tmp, exist_ok=True)
            nome_foto = _os.path.basename(foto_final)
            dest_tmp  = _os.path.join(pasta_tmp, nome_foto)
            try:
                if _os.path.abspath(foto_final) != _os.path.abspath(dest_tmp):
                    _sh.copy2(foto_final, dest_tmp)
                foto_final = dest_tmp
            except Exception as ex:
                logger.warning("[COMPRAS] copiar foto: %s", ex)

        # ── Salva cabeçalho + itens ───────────────────────
        compra_id = salvar_compra_nf(
            cabecalho={
                "farmacia_id":  _farmacia_id_sel[0],
                "data":         hoje,
                "total":        total_nf,
                "foto_path":    foto_final,
                "foto_drive_id": _drive_id[0] or None,
                "qr_nfe":       _qr_nfe[0] or None,
            },
            itens=itens_salvar,
        )

        # ── Renomeia pasta para id definitivo e faz upload Drive ──
        if foto_final and compra_id:
            _root_dir = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
            pasta_def = _os.path.join(_root_dir, "assets", "compras", str(compra_id))
            _os.makedirs(pasta_def, exist_ok=True)
            nome_foto = _os.path.basename(foto_final)
            novo_path = _os.path.join(pasta_def, nome_foto)
            try:
                import shutil as _sh2
                _sh2.move(foto_final, novo_path)
                import sqlite3 as _sql
                from dados.model_prontuario import DB_PATH as _DB
                with _sql.connect(_DB, timeout=10) as _c:
                    _c.execute("UPDATE compras SET foto_path=? WHERE id=?",
                               (novo_path, compra_id))
                import threading as _thr
                def _up(path=novo_path, cid=compra_id):
                    try:
                        from utils.drive_prontuario import upload_nota_fiscal
                        fid, _ = upload_nota_fiscal(path, mov_id=cid)
                        with _sql.connect(_DB, timeout=10) as _c2:
                            _c2.execute("UPDATE compras SET foto_drive_id=? WHERE id=?",
                                        (fid, cid))
                    except Exception as ex:
                        logger.warning("[COMPRAS] upload Drive: %s", ex)
                _thr.Thread(target=_up, daemon=True).start()
            except Exception as ex:
                logger.warning("[COMPRAS] mover foto final: %s", ex)

        salvos = len(itens_salvar)

        # Sincroniza com Drive em background
        def _sync():
            try:
                from backup.drive_backup import fazer_backup
                fazer_backup(forcar=True)
            except Exception as ex:
                logger.warning("[COMPRAS] sync Drive: %s", ex)
        import threading as _thr2
        _thr2.Thread(target=_sync, daemon=True).start()

        partes = [f"✓ {salvos} compra(s) registrada(s)"]
        if nao_enc:
            partes.append(f"{len(nao_enc)} remedio(s) novo(s) cadastrado(s)")
        txt_resultado.value = " — ".join(partes)
        txt_resultado.color = VERD

        # Limpa tela para nova nota
        _foto_nf[0]  = ""
        _drive_id[0] = ""
        _remedios_extraidos[0] = []
        _limpar_farm()
        _qr_nfe[0] = ""
        tf_chave.value = ""
        tf_chave.read_only = False
        tf_chave.border_color = BD2
        btn_consultar_nfe.visible = False
        secao_qr.visible = False
        preview_box.content = ft.Column([
            ft.Icon("receipt_long_rounded", size=40, color=MUT),
            ft.Text("Nenhuma nota selecionada", size=12, color=MUT),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.CENTER, spacing=8)
        preview_box.bgcolor = BD
        tabela_itens.visible = False
        btn_extrair.visible  = False
        btn_confirmar.visible = False
        txt_status.value = ""
        try: page.update()
        except Exception: pass

        # Volta para lista após 1.5s para o usuário ver o resultado
        if on_concluido:
            import threading as _thr
            _thr.Timer(1.5, on_concluido).start()

    btn_confirmar.on_click = _confirmar

    # botão Cancelar / Voltar para lista
    btn_voltar = ft.Container(
        content=ft.Row([
            ft.Icon("arrow_back_rounded", size=14, color=SEC),
            ft.Text("Voltar", size=12, color=SEC),
        ], spacing=6, tight=True),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        border_radius=8, bgcolor=BD, ink=True,
    )
    if on_concluido:
        btn_voltar.on_click = lambda e: on_concluido()

    area.controls.extend([
        ft.Row([
            btn_voltar,
            ft.Container(expand=True),
        ]),
        _label_sec("NOVA NOTA FISCAL", VERD),
        ft.Text("Fotografe a nota e o QR Code separado para melhor leitura.",
                size=11, color=MUT),
        ft.Container(height=4),
        secao_farmacia,
        ft.Container(height=8),
        preview_box,
        secao_qr,
        ft.Container(height=8),
        ft.Row([btn_selecionar, btn_extrair], spacing=8, wrap=True),
        progress,
        txt_status,
        ft.Container(height=8),
        tabela_itens,
        ft.Container(height=8),
        btn_confirmar,
        txt_resultado,
    ])

    return area.controls


# ══════════════════════════════════════════════════════════════
# ABA 3 — FARMÁCIAS + ORÇAMENTO WHATSAPP (mantida, não exibida)
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

def criar_tela_remedios(page: ft.Page, voltar_fn, readonly=False):
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
        (0, "today_rounded",        "Hoje",     AZUL),
        (1, "medication_rounded",   "Remedios", AMAR),
        (2, "shopping_cart_rounded","Compras",  VERD),
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
                controles = _lista_remedios(page, _ir_ficha, readonly=readonly)
                area.controls.extend(controles)
            else:
                controles = _conteudo_compras(page)
                area.controls.extend(controles)
            logger.info("[REMEDIOS] %s controles carregados na area", len(area.controls))
        except Exception as ex:
            logger.error("[REMEDIOS] erro _rebuild_conteudo: %s", ex, exc_info=True)
            area.controls.append(ft.Text(f"Erro interno: {ex}", color=VERM, size=12))

    # ── Montar estrutura principal ────────────────────────────
    _rebuild_abas()
    _rebuild_conteudo()

    lay = Layout(page)
    titulo_tela = "Medicação" if readonly else "Remedio / Suplemento"
    cabecalho = lay.criar_cabecalho(
        titulo_tela, voltar_fn,
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
