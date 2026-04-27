"""
tela_incluir_exame_padrao.py — Koios Prontuário
Tela exclusiva para incluir exame padrão a partir de uma pendência.

Ao confirmar:
  1. INSERT em exames_padrao
  2. INSERT em referencias_padrao (se preenchido)
  3. vincular_manualmente() — vincula + sinônimo + recalcula nível
"""

import flet as ft
import sqlite3
import re

CARD  = "#161B22"
HOVER = "#21262D"
BD    = "#21262D"
TXT   = "#E6EDF3"
SEC   = "#8B949E"
MUT   = "#484F58"
AZUL  = "#58A6FF"
VERD  = "#3FB950"
LAR   = "#F0883E"
SALM  = "#FF7B72"


def _tf(label, value="", hint=None, expand=False, width=None, read_only=False):
    tf = ft.TextField(
        label=label,
        value=str(value) if value else "",
        hint_text=hint,
        read_only=read_only,
        bgcolor="#0D1117" if read_only else HOVER,
        border_color=BD,
        focused_border_color=AZUL,
        color=TXT,
        label_style=ft.TextStyle(color=SEC, size=11),
        border_radius=8,
        text_size=13,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
    )
    if expand:
        tf.expand = True
    if width:
        tf.width = width
    return tf


def criar_tela_incluir_exame_padrao(page: ft.Page,
                                     parametro: str,
                                     voltar_fn=None):
    from ..dados.model_prontuario import DB_PATH
    from ..dados.limpeza import vincular_manualmente, executar_limpeza

    # Separar nome e valor numérico
    match = re.match(r'^(.*?)\s+([\d]+[,.][\d]+|[\d]+)\s*$', parametro.strip())
    nome_pre = match.group(1).strip() if match else parametro.strip()
    unid_pre = match.group(2).strip() if match else ""

    # Buscar dados do resultado mais recente
    conn = sqlite3.connect(DB_PATH, timeout=30)
    row = conn.execute("""
        SELECT r.valor, r.unidade, r.referencia
        FROM resultados_estruturados r
        JOIN exames e ON r.exame_id = e.id
        WHERE r.parametro = ?
          AND r.nivel_interpretacao = 'nao_identificado'
        ORDER BY e.data_exame DESC
        LIMIT 1
    """, (parametro,)).fetchone()
    conn.close()

    valor_pre = row[0] if row else ""
    if not unid_pre and row and row[1]:
        unid_pre = row[1]
    ref_pre = row[2] if row else ""

    # Campos
    tf_nome      = _tf("Nome oficial *", nome_pre,  expand=True)
    tf_valor     = _tf("Valor",          valor_pre, width=120, read_only=True)
    tf_unidade   = _tf("Unidade",        unid_pre,  width=130)
    tf_referencia= _tf("Referência",     ref_pre,   expand=True)
    tf_categoria = _tf("Categoria", hint="ex: Hematologia", expand=True)
    tf_lim_baixo = _tf("Limite baixo",  hint="ex: 3.5",  width=110)
    tf_lim_alto  = _tf("Limite alto",   hint="ex: 10.0", width=110)
    tf_otimo_min = _tf("Ótimo mín",     hint="ex: 4.0",  width=110)
    tf_otimo_max = _tf("Ótimo máx",     hint="ex: 9.0",  width=110)
    txt_erro     = ft.Text("", size=11, color=SALM)

    def _to_float(v):
        try:
            return float(v.replace(",", ".")) if v and v.strip() else None
        except ValueError:
            return None

    def _salvar(e):
        nome = tf_nome.value.strip()
        if not nome:
            txt_erro.value = "Nome oficial é obrigatório."
            page.update()
            return

        conn = sqlite3.connect(DB_PATH, timeout=30)
        try:
            # 1. INSERT em exames_padrao
            conn.execute("""
                INSERT OR IGNORE INTO exames_padrao
                    (nome_oficial, categoria, unidade)
                VALUES (?, ?, ?)
            """, (nome,
                  tf_categoria.value.strip() or "Geral",
                  tf_unidade.value.strip()))
            conn.commit()

            ep = conn.execute(
                "SELECT id FROM exames_padrao WHERE nome_oficial = ?",
                (nome,)
            ).fetchone()
            if not ep:
                txt_erro.value = "Erro ao criar exame padrão."
                page.update()
                return
            ep_id = ep[0]

            # 2. INSERT em referencias_padrao
            lim_baixo = _to_float(tf_lim_baixo.value)
            lim_alto  = _to_float(tf_lim_alto.value)
            otimo_min = _to_float(tf_otimo_min.value)
            otimo_max = _to_float(tf_otimo_max.value)
            if any(v is not None for v in [lim_baixo, lim_alto, otimo_min, otimo_max]):
                conn.execute("""
                    INSERT INTO referencias_padrao
                        (exame_padrao_id, limite_baixo, limite_alto,
                         otimo_min, otimo_max)
                    VALUES (?, ?, ?, ?, ?)
                """, (ep_id, lim_baixo, lim_alto, otimo_min, otimo_max))
                conn.commit()

            # Atualiza unidade/referencia nos resultados existentes
            unid = tf_unidade.value.strip()
            ref  = tf_referencia.value.strip()
            if unid or ref:
                conn.execute("""
                    UPDATE resultados_estruturados
                    SET unidade    = CASE WHEN ? != '' THEN ? ELSE unidade END,
                        referencia = CASE WHEN ? != '' THEN ? ELSE referencia END
                    WHERE parametro = ?
                """, (unid, unid, ref, ref, parametro))
                conn.commit()

        finally:
            conn.close()

        # 3. Vincula + sinônimo + recalcula nível
        vincular_manualmente(parametro, ep_id)
        try:
            executar_limpeza()
        except Exception:
            pass

        page.snack_bar = ft.SnackBar(
            content=ft.Text(f"'{nome}' criado e vinculado!", color=TXT),
            bgcolor=CARD)
        page.snack_bar.open = True
        page.update()

        if voltar_fn:
            voltar_fn()

    def _bloco(titulo, cor, controles):
        return ft.Container(
            content=ft.Column([
                ft.Text(titulo, size=10, color=cor, weight=ft.FontWeight.W_700),
                ft.Container(height=4),
                *controles,
            ], spacing=8),
            bgcolor=f"{cor}0D",
            border_radius=10,
            padding=ft.padding.all(14),
            border=ft.Border(
                left=ft.BorderSide(3, cor),
                top=ft.BorderSide(1, BD),
                bottom=ft.BorderSide(1, BD),
                right=ft.BorderSide(1, BD),
            ),
        )

    return ft.Column([
        # Cabeçalho
        ft.Row([
            ft.TextButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.ARROW_BACK, size=14, color=SEC),
                    ft.Text("Voltar", size=12, color=SEC),
                ], spacing=4, tight=True),
                on_click=lambda e: voltar_fn() if voltar_fn else None,
            ),
            ft.Container(expand=True),
            ft.Text("Incluir Exame Padrão", size=18,
                    weight=ft.FontWeight.W_700, color=TXT),
            ft.Container(expand=True),
        ]),

        ft.Container(height=4),

        _bloco("DADOS DO RESULTADO", LAR, [
            ft.Row([tf_nome, tf_valor], spacing=8),
            ft.Row([tf_referencia, tf_unidade], spacing=8),
        ]),

        ft.Container(height=4),

        _bloco("EXAME PADRÃO", AZUL, [
            tf_categoria,
        ]),

        ft.Container(height=4),

        _bloco("REFERÊNCIAS  (opcional)", VERD, [
            ft.Row([tf_lim_baixo, tf_otimo_min, tf_otimo_max, tf_lim_alto], spacing=8),
            ft.Text("Deixe em branco se não souber os limites.", size=11, color=MUT),
        ]),

        txt_erro,
        ft.Container(height=8),

        ft.Row([
            ft.TextButton(
                "Cancelar",
                style=ft.ButtonStyle(color=SEC),
                on_click=lambda e: voltar_fn() if voltar_fn else None,
            ),
            ft.Container(expand=True),
            ft.FilledButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.SAVE_OUTLINED, size=16),
                    ft.Text("Confirmar", size=13, weight=ft.FontWeight.W_600),
                ], spacing=6, tight=True),
                style=ft.ButtonStyle(
                    bgcolor=VERD,
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=20, vertical=12),
                ),
                on_click=_salvar,
            ),
        ]),

    ], spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)