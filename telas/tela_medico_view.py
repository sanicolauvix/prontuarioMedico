"""
tela_medico_view.py
Painel do médico — acesso somente leitura ao prontuário.
Abas: Exames | Remédios | Rotinas | Receitas | Procedimentos | Diagnósticos
"""

import flet as ft
import sqlite3
import logging
from ..dados.model_prontuario import (
    DB_PATH, carregar_perfil,
    listar_remedios, listar_receitas, salvar_receita,
    listar_rotina, listar_medicos,
)

logger = logging.getLogger(__name__)

# ── Paleta ────────────────────────────────────────────────────
BG   = "#0D1117";  CARD = "#161B22";  BD  = "#21262D";  BD2 = "#30363D"
TXT  = "#E6EDF3";  SEC  = "#8B949E";  MUT = "#484F58"
AZUL = "#58A6FF";  VERD = "#3FB950";  LAR = "#F0883E"
ROXO = "#BC8CFF";  AMAR = "#D29922";  VERM = "#F85149"
CORAL = "#FF7B72"

CORES_NIVEL = {
    "critico_baixo": VERM,  "baixo": LAR,    "otimo": VERD,
    "alto": LAR,            "critico_alto": VERM,
    "sem_referencia": AZUL, "nao_identificado": SEC,
}
LABELS_NIVEL = {
    "critico_baixo": "Crítico ↓", "baixo": "Baixo ↓", "otimo": "Ótimo ✓",
    "alto": "Alto ↑",             "critico_alto": "Crítico ↑",
    "sem_referencia": "—",        "nao_identificado": "?",
}


def _badge(texto, cor):
    return ft.Container(
        content=ft.Text(texto, size=9, color=cor),
        bgcolor=f"{cor}22", border_radius=4,
        padding=ft.padding.symmetric(horizontal=6, vertical=2),
    )


def _label_sec(txt):
    return ft.Text(txt, size=9, color=MUT, weight=ft.FontWeight.W_700)


def _card_vazio(msg):
    return ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.INBOX_ROUNDED, size=32, color=MUT),
            ft.Text(msg, size=12, color=MUT),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
        padding=40, alignment=ft.alignment.center,
    )


# ══════════════════════════════════════════════════════════════
# ABA 1 — EXAMES (abre tela_consulta completa)
# ══════════════════════════════════════════════════════════════

def _conteudo_exames(ir_consulta_fn) -> list:
    return [ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.SCIENCE_ROUNDED, size=44, color=ROXO),
            ft.Text("Consulta de Exames", size=16, color=TXT,
                    weight=ft.FontWeight.W_700),
            ft.Text(
                "Acesse os exames com gráficos, histórico e busca\n"
                "por médico, especialidade, classificação e mais.",
                size=12, color=SEC, text_align=ft.TextAlign.CENTER),
            ft.Container(height=8),
            ft.FilledButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.OPEN_IN_NEW_ROUNDED, size=16),
                    ft.Text("Abrir Consulta de Exames", size=13,
                            weight=ft.FontWeight.W_600),
                ], spacing=6, tight=True),
                style=ft.ButtonStyle(
                    bgcolor=ROXO,
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=20, vertical=14),
                ),
                on_click=lambda e: ir_consulta_fn(),
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
        padding=60, alignment=ft.alignment.center,
    )]


# ══════════════════════════════════════════════════════════════
# ABA 2 — REMÉDIOS (somente leitura)
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# ABA 2 — REMÉDIOS + RECEITA (leitura + nova receita + anotação)
# ══════════════════════════════════════════════════════════════

def _conteudo_remedios(page: ft.Page, medico_id: int, nome_medico: str) -> list:
    import re as _re
    from datetime import date

    # ── Lista de remédios (somente leitura) ───────────────────
    meds    = listar_remedios(so_ativos=False)
    ativos  = [m for m in meds if m.get("ativo")]
    inativos= [m for m in meds if not m.get("ativo")]

    lista_meds = ft.Column(spacing=6)
    for grupo, titulo, cor in [(ativos, "Em uso", VERD), (inativos, "Histórico", MUT)]:
        if not grupo:
            continue
        lista_meds.controls.append(
            ft.Text(titulo.upper(), size=10, color=cor, weight=ft.FontWeight.W_700))
        for m in grupo:
            est   = m.get("estoque_atual") or 0
            mn    = m.get("estoque_minimo") or 0
            cor_e = VERM if est <= 0 else (LAR if est <= mn else VERD)
            lista_meds.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(m["nome"], size=13, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True),
                        ft.Text(m.get("dosagem") or "", size=11, color=SEC),
                    ]),
                    ft.Row([
                        ft.Icon(ft.Icons.SCHEDULE, size=12, color=MUT),
                        ft.Text(m.get("frequencia") or "—", size=11, color=MUT),
                        ft.Container(width=8),
                        ft.Icon(ft.Icons.PERSON, size=12, color=AZUL),
                        ft.Text(m.get("medico") or "—", size=11, color=AZUL),
                    ], spacing=4),
                    ft.Row([
                        ft.Text(
                            f"{m.get('data_inicio','') or ''}  →  "
                            f"{m.get('data_fim','') or 'em uso'}",
                            size=10, color=MUT),
                        ft.Container(expand=True),
                        ft.Text(f"Estoque: {est}", size=11, color=cor_e,
                                weight=ft.FontWeight.W_600),
                    ]),
                ], spacing=4),
                bgcolor=CARD, border_radius=8, padding=12,
                border=ft.Border(
                    left=ft.BorderSide(2, cor if m.get("ativo") else MUT),
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
                opacity=1.0 if m.get("ativo") else 0.5,
            ))

    if not meds:
        lista_meds.controls.append(_card_vazio("Nenhum medicamento registrado."))

    # ── Formulário nova receita ───────────────────────────────
    txt_status = ft.Text("", size=12, color=VERD)

    f_data = ft.TextField(
        label="Data", hint_text="DD/MM/AAAA",
        value=date.today().strftime("%d/%m/%Y"),
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, width=140,
    )
    def _mask_data(e):
        raw = _re.sub(r"\D", "", f_data.value or "")[:8]
        novo = (raw[:2]+"/"+raw[2:4]+"/"+raw[4:] if len(raw) >= 5
                else raw[:2]+"/"+raw[2:] if len(raw) >= 3 else raw)
        if f_data.value != novo:
            f_data.value = novo
            try: f_data.update()
            except Exception: pass
    f_data.on_change = _mask_data

    f_obs = ft.TextField(
        label="Medicamentos / observações",
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, expand=True, multiline=True, min_lines=2,
    )

    # ── Lista de receitas com campo de anotação ───────────────
    lista_receitas_col = ft.Column(spacing=6)

    def _carregar_receitas():
        lista_receitas_col.controls.clear()
        receitas = listar_receitas()
        if not receitas:
            lista_receitas_col.controls.append(
                _card_vazio("Nenhuma receita registrada."))
        else:
            for r in receitas:
                rid      = r.get("id")
                obs_atual= r.get("observacoes") or ""
                f_anot   = ft.TextField(
                    value=obs_atual,
                    hint_text="Adicionar anotação…",
                    bgcolor=BG, border_color=BD, focused_border_color=AZUL,
                    text_style=ft.TextStyle(color=TXT, size=11),
                    border_radius=6, multiline=True, min_lines=1,
                    expand=True,
                )
                txt_anot_status = ft.Text("", size=10, color=VERD)

                def _salvar_anot(e, fld=f_anot, st=txt_anot_status, r=r):
                    try:
                        import sqlite3 as _sq
                        conn = _sq.connect(DB_PATH, timeout=30)
                        conn.execute(
                            "UPDATE receitas SET observacoes=? WHERE id=?",
                            (fld.value or "", r["id"]))
                        conn.commit(); conn.close()
                        st.value = "✓ Salvo"
                        st.color = VERD
                    except Exception as ex:
                        st.value = f"Erro: {ex}"
                        st.color = VERM
                    try: page.update()
                    except Exception: pass

                lista_receitas_col.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.RECEIPT_LONG_ROUNDED,
                                    size=14, color=LAR),
                            ft.Column([
                                ft.Text(r.get("nome_arquivo") or "Receita",
                                        size=12, color=TXT,
                                        weight=ft.FontWeight.W_600),
                                ft.Row([
                                    ft.Text(r.get("data","")[:10] or "—",
                                            size=10, color=MUT),
                                    ft.Text("·", size=10, color=BD),
                                    ft.Text(r.get("medico") or "—",
                                            size=10, color=AZUL),
                                ], spacing=4),
                            ], spacing=1, expand=True),
                        ], spacing=8),
                        ft.Row([
                            f_anot,
                            ft.Column([
                                ft.IconButton(
                                    icon=ft.Icons.SAVE_ROUNDED,
                                    icon_size=16, icon_color=AZUL,
                                    on_click=_salvar_anot,
                                ),
                                txt_anot_status,
                            ], spacing=2,
                               horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        ], spacing=6,
                           vertical_alignment=ft.CrossAxisAlignment.START),
                    ], spacing=6),
                    bgcolor=CARD, border_radius=8, padding=10,
                    border=ft.Border(
                        left=ft.BorderSide(2, LAR),
                        top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                        right=ft.BorderSide(1, BD),
                    ),
                ))
        try: page.update()
        except Exception: pass

    def _salvar_receita(e):
        obs = (f_obs.value or "").strip()
        if not obs:
            txt_status.value = "Informe os medicamentos/observações."
            txt_status.color = VERM
            try: page.update()
            except Exception: pass
            return
        try:
            salvar_receita({
                "medico_id":    medico_id,
                "data":         f_data.value or date.today().strftime("%d/%m/%Y"),
                "nome_arquivo": f"Receita — {nome_medico}",
                "observacoes":  obs,
            })
            txt_status.value = "✓ Receita registrada."
            txt_status.color = VERD
            f_obs.value  = ""
            f_data.value = date.today().strftime("%d/%m/%Y")
            _carregar_receitas()
        except Exception as ex:
            logger.error("[MEDICO] salvar_receita: %s", ex, exc_info=True)
            txt_status.value = f"Erro: {ex}"
            txt_status.color = VERM
            try: page.update()
            except Exception: pass

    form_receita = ft.Container(
        content=ft.Column([
            _label_sec("NOVA RECEITA"),
            f_data,
            f_obs,
            ft.Row([
                ft.FilledButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.ADD_ROUNDED, size=16),
                        ft.Text("Registrar Receita", size=13,
                                weight=ft.FontWeight.W_600),
                    ], spacing=6, tight=True),
                    style=ft.ButtonStyle(
                        bgcolor=LAR,
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=16, vertical=12),
                    ),
                    on_click=_salvar_receita,
                ),
                txt_status,
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=8),
        bgcolor=CARD, border_radius=10, padding=14,
        border=ft.Border(
            left=ft.BorderSide(2, LAR),
            top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
            right=ft.BorderSide(1, BD),
        ),
    )

    _carregar_receitas()

    return [
        _label_sec("MEDICAMENTOS"),
        lista_meds,
        ft.Container(height=1, bgcolor=BD, margin=ft.margin.symmetric(vertical=8)),
        form_receita,
        ft.Container(height=1, bgcolor=BD, margin=ft.margin.symmetric(vertical=4)),
        _label_sec("RECEITAS EXISTENTES"),
        lista_receitas_col,
    ]


# ══════════════════════════════════════════════════════════════
# ABA 3 — DIETA E ROTINAS (navega para tela_dieta)
# ══════════════════════════════════════════════════════════════

def _conteudo_dieta(ir_dieta_fn) -> list:
    return [ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.TODAY_ROUNDED, size=44, color=VERD),
            ft.Text("Dieta e Rotinas", size=16, color=TXT,
                    weight=ft.FontWeight.W_700),
            ft.Text("Rotina diária, dieta e suplementos do paciente.",
                    size=12, color=SEC, text_align=ft.TextAlign.CENTER),
            ft.Container(height=8),
            ft.FilledButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.OPEN_IN_NEW_ROUNDED, size=16),
                    ft.Text("Abrir Dieta e Rotinas", size=13,
                            weight=ft.FontWeight.W_600),
                ], spacing=6, tight=True),
                style=ft.ButtonStyle(
                    bgcolor=VERD,
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=20, vertical=14),
                ),
                on_click=lambda e: ir_dieta_fn(),
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
        padding=60, alignment=ft.alignment.center,
    )]


# ══════════════════════════════════════════════════════════════
# ABA 4 — RECEITAS (mantida apenas para assinatura interna)
# ══════════════════════════════════════════════════════════════

def _conteudo_receitas(page: ft.Page, medico_id: int, nome_medico: str) -> list:
    lista_col  = ft.Column(spacing=6)
    txt_status = ft.Text("", size=12, color=VERD)

    def _carregar():
        lista_col.controls.clear()
        receitas = listar_receitas()
        if not receitas:
            lista_col.controls.append(_card_vazio("Nenhuma receita registrada."))
        else:
            for r in receitas:
                lista_col.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.RECEIPT_LONG_ROUNDED,
                                size=16, color=AZUL),
                        ft.Column([
                            ft.Text(r.get("nome_arquivo") or "Receita",
                                    size=12, color=TXT,
                                    weight=ft.FontWeight.W_600),
                            ft.Row([
                                ft.Text(r.get("data", "")[:10] or "—",
                                        size=10, color=MUT),
                                ft.Text("·", size=10, color=BD2),
                                ft.Text(r.get("medico") or "—",
                                        size=10, color=AZUL),
                            ], spacing=4),
                            ft.Text(r.get("observacoes") or "",
                                    size=10, color=MUT),
                        ], spacing=2, expand=True),
                    ], spacing=10,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=CARD, border_radius=8, padding=10,
                    border=ft.Border(
                        left=ft.BorderSide(2, AZUL),
                        top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                        right=ft.BorderSide(1, BD),
                    ),
                ))
        try: page.update()
        except Exception: pass

    # ── Formulário nova receita ──────────────────────────────
    import re
    f_data = ft.TextField(
        label="Data", hint_text="DD/MM/AAAA",
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, width=140,
    )
    def _mask_data(e):
        raw = re.sub(r"\D", "", f_data.value or "")[:8]
        novo = (raw[:2]+"/"+raw[2:4]+"/"+raw[4:] if len(raw) >= 5
                else raw[:2]+"/"+raw[2:] if len(raw) >= 3 else raw)
        if f_data.value != novo:
            f_data.value = novo
            try: f_data.update()
            except Exception: pass
    f_data.on_change = _mask_data

    f_obs = ft.TextField(
        label="Observações / medicamentos",
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, expand=True, multiline=True, min_lines=2,
    )

    def _salvar_receita(e):
        obs = (f_obs.value or "").strip()
        if not obs:
            txt_status.value = "Informe os medicamentos/observações."
            txt_status.color = VERM
            try: page.update()
            except Exception: pass
            return
        from datetime import date
        data_val = f_data.value.strip() if f_data.value else date.today().strftime("%d/%m/%Y")
        try:
            salvar_receita({
                "medico_id":    medico_id,
                "data":         data_val,
                "nome_arquivo": f"Receita — {nome_medico}",
                "observacoes":  obs,
            })
            txt_status.value = "✓ Receita registrada."
            txt_status.color = VERD
            f_obs.value  = ""
            f_data.value = ""
            _carregar()
        except Exception as ex:
            logger.error("[MEDICO] salvar_receita: %s", ex, exc_info=True)
            txt_status.value = f"Erro ao salvar: {ex}"
            txt_status.color = VERM
            try: page.update()
            except Exception: pass

    form = ft.Container(
        content=ft.Column([
            _label_sec("NOVA RECEITA"),
            ft.Row([f_data], spacing=8),
            f_obs,
            ft.Row([
                ft.FilledButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.ADD_ROUNDED, size=16),
                        ft.Text("Registrar Receita", size=13,
                                weight=ft.FontWeight.W_600),
                    ], spacing=6, tight=True),
                    style=ft.ButtonStyle(
                        bgcolor=AZUL,
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=16, vertical=12),
                    ),
                    on_click=_salvar_receita,
                ),
                txt_status,
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=8),
        bgcolor=CARD, border_radius=10, padding=14,
        border=ft.Border(
            left=ft.BorderSide(2, AZUL),
            top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
            right=ft.BorderSide(1, BD),
        ),
    )

    _carregar()
    return [
        form,
        ft.Container(height=1, bgcolor=BD,
                     margin=ft.margin.symmetric(vertical=8)),
        ft.Text("RECEITAS EXISTENTES", size=10, color=MUT,
                weight=ft.FontWeight.W_700),
        lista_col,
    ]


# ══════════════════════════════════════════════════════════════
# ABA 5 — PROCEDIMENTOS (em breve)
# ══════════════════════════════════════════════════════════════

def _conteudo_em_breve(titulo: str) -> list:
    return [ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.CONSTRUCTION_ROUNDED, size=40, color=MUT),
            ft.Text(titulo, size=15, color=TXT, weight=ft.FontWeight.W_700),
            ft.Text("Esta seção será implantada em breve.",
                    size=12, color=MUT),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
        padding=60, alignment=ft.alignment.center,
    )]


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL
# ══════════════════════════════════════════════════════════════

def criar_tela_medico(page: ft.Page, on_logout):
    sessao     = page.session.get("sessao") or {}
    nome       = sessao.get("nome", "Médico")
    medico_id  = sessao.get("medico_id", 0)

    perfil     = carregar_perfil() or {}
    paciente   = perfil.get("nome", "Paciente")
    nasc       = perfil.get("data_nasc", "")
    sexo_txt   = "Masculino" if perfil.get("sexo") == "M" else "Feminino"

    ABAS = [
        (0, ft.Icons.SCIENCE_ROUNDED,       "Exames",        ROXO),
        (1, ft.Icons.MEDICATION_ROUNDED,    "Remédios",      AZUL),
        (2, ft.Icons.TODAY_ROUNDED,         "Dieta/Rotinas", VERD),
        (3, ft.Icons.MEDICAL_SERVICES,      "Procedimentos", AMAR),
        (4, ft.Icons.MONITOR_HEART_ROUNDED, "Diagnósticos",  CORAL),
    ]
    aba_ativa     = [0]
    barra_abas    = ft.Row(spacing=0)
    area_conteudo = ft.Column(spacing=8, expand=True,
                              scroll=ft.ScrollMode.AUTO)

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
                    ft.Icon(icone, size=15,
                            color=cor if ativo else MUT),
                    ft.Text(label, size=9,
                            color=cor if ativo else MUT,
                            weight=ft.FontWeight.W_600 if ativo
                                   else ft.FontWeight.W_400),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=2, tight=True),
                expand=True,
                padding=ft.padding.symmetric(vertical=8),
                border=ft.Border(
                    bottom=ft.BorderSide(2, cor if ativo else "#00000000")),
                on_click=_click,
            ))
        try: page.update()
        except Exception: pass

    def _ir_consulta_exames():
        from .tela_exames import criar_tela_consulta
        tela = criar_tela_consulta(page, voltar_fn=_voltar_painel)
        page.controls.clear()
        page.controls.append(tela)
        try: page.update()
        except Exception: pass

    def _ir_dieta():
        from .tela_dieta import criar_tela_dieta
        tela = criar_tela_dieta(page, voltar_fn=_voltar_painel)
        page.controls.clear()
        page.controls.append(tela)
        try: page.update()
        except Exception: pass

    def _voltar_painel():
        page.controls.clear()
        page.controls.append(wrapper)
        aba_ativa[0] = 0
        _rebuild_abas()
        _rebuild_conteudo()
        try: page.update()
        except Exception: pass

    def _rebuild_conteudo():
        area_conteudo.controls.clear()
        i = aba_ativa[0]
        if i == 0:
            area_conteudo.controls.extend(_conteudo_exames(_ir_consulta_exames))
        elif i == 1:
            area_conteudo.controls.extend(
                _conteudo_remedios(page, medico_id, nome))
        elif i == 2:
            area_conteudo.controls.extend(_conteudo_dieta(_ir_dieta))
        elif i == 3:
            area_conteudo.controls.extend(_conteudo_em_breve("Procedimentos"))
        elif i == 4:
            area_conteudo.controls.extend(_conteudo_em_breve("Diagnósticos"))
        try: page.update()
        except Exception: pass

    _rebuild_abas()
    _rebuild_conteudo()

    # ── Cabeçalho ─────────────────────────────────────────────
    # Espaço para foto (placeholder — será implantado)
    foto_placeholder = ft.Container(
        width=48, height=48,
        bgcolor=BD2, border_radius=24,
        content=ft.Icon(ft.Icons.PERSON_ROUNDED, size=24, color=MUT),
        alignment=ft.alignment.center,
        tooltip="Foto do paciente (em breve)",
    )

    cabecalho = ft.Container(
        content=ft.Row([
            foto_placeholder,
            ft.Column([
                ft.Text(paciente, size=15, color=TXT,
                        weight=ft.FontWeight.W_700),
                ft.Row([
                    ft.Text(nasc, size=10, color=MUT),
                    ft.Text("·", size=10, color=BD2),
                    ft.Text(sexo_txt, size=10, color=MUT),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.VISIBILITY_ROUNDED,
                                    size=10, color=MUT),
                            ft.Text("Somente leitura", size=9, color=MUT),
                        ], spacing=3, tight=True),
                        bgcolor=BD, border_radius=4,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    ),
                ], spacing=6),
            ], spacing=2, expand=True),
            ft.Column([
                ft.Text(f"Dr(a). {nome}", size=11, color=SEC),
                ft.TextButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.LOGOUT_ROUNDED,
                                size=13, color=VERM),
                        ft.Text("Sair", size=11, color=VERM),
                    ], spacing=4, tight=True),
                    on_click=lambda e: on_logout(),
                ),
            ], spacing=0,
               horizontal_alignment=ft.CrossAxisAlignment.END),
        ], spacing=12,
           vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        bgcolor=CARD,
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
    )

    corpo = ft.Column([
        cabecalho,
        ft.Container(
            content=barra_abas,
            bgcolor=CARD,
            border=ft.Border(bottom=ft.BorderSide(1, BD)),
        ),
        ft.Container(
            content=area_conteudo,
            padding=ft.padding.all(16),
            expand=True,
        ),
    ], expand=True)

    try:
        larg = page.width or 0
    except Exception:
        larg = 0

    if larg > 500:
        conteudo_final = ft.Row([
            ft.Container(expand=True),
            ft.Container(content=corpo, width=560),
            ft.Container(expand=True),
        ], expand=True)
    else:
        conteudo_final = corpo

    wrapper = ft.Column(expand=True)
    wrapper.controls.append(
        ft.Container(bgcolor=BG, expand=True, content=conteudo_final))
    return wrapper
