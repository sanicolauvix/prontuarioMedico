# -*- coding: utf-8 -*-
# KOIOS v1.0 | gerado: 2026-03-12 21:46 | processador_exame.py
"""
processador_exame.py — Koios Prontuário
Módulo reutilizável de processamento e conferência de exames PDF.

Usado por:
  - tela_incluir_exame.py  → faz upload Drive + grava definitivo
  - tela_reprocessamento.py → só regrava no banco, sem upload (PDF já está no Drive)

Exports públicos:
  - executar_processamento(caminho, set_status_fn, on_concluido, on_erro)
  - construir_painel_conferencia(page, dados, pendencias, exame_id, on_liberar, on_cancelar,
                                  fazer_upload=True)
"""

import logging
import sqlite3
import threading
from pathlib import Path

# ── Paleta (espelha as telas) ──────────────────────────────────────────────────
BG   = "#0D1117"
CARD = "#161B22"
BD   = "#21262D"
TXT  = "#E6EDF3"
SEC  = "#8B949E"
MUT  = "#484F58"
AZUL = "#58A6FF"
VERD = "#3FB950"
VERM = "#DA3633"
AMAR = "#D29922"


def _log(msg: str):
    logging.info(msg)
    print(msg)


# ══════════════════════════════════════════════════════════════════════════════
# 1. PROCESSAMENTO — extração + vínculos + rascunho
#    Reutilizável por qualquer tela que precise processar um PDF local.
# ══════════════════════════════════════════════════════════════════════════════

def executar_processamento(
    caminho: str,
    set_status_fn,       # fn(msg, cor, prog, detalhe, force) → atualiza UI
    on_concluido,        # fn(dados, pendencias, exame_id) → chamado ao final
    on_erro,             # fn(msg) → chamado em caso de exceção
    verificar_duplicata: bool = True,
):
    """
    Executa em thread separada: lê PDF → extrai → verifica vínculos → salva rascunho.
    Ao concluir chama on_concluido(dados, pendencias, exame_id).
    Ao falhar chama on_erro(msg).

    Parâmetros:
        caminho            : caminho local do PDF
        set_status_fn      : fn(msg, cor=AZUL, prog=None, detalhe="", force=False)
        on_concluido       : fn(dados: dict, pendencias: list, exame_id: int)
        on_erro            : fn(msg: str)
        verificar_duplicata: se False pula verificação (útil em reprocessamento)
    """
    def _run():
        import time as _time
        _time.sleep(0.15)   # aguarda UI montar antes dos primeiros callbacks
        from .extrator_pdf import extrair_pdf_bytes
        from dados.model_prontuario        import salvar_rascunho, registrar_log, DB_PATH

        nome = Path(caminho).name
        _watchdog_ativo = [False]   # inicializado aqui — seguro no except

        try:
            # ── Duplicata ─────────────────────────────────────────
            _log(f"[PROCESSAR] ▶ INÍCIO — arquivo: {nome}")
            if verificar_duplicata:
                set_status_fn("Verificando duplicata...", AZUL, 0.05, "", True)
                try:
                    with sqlite3.connect(DB_PATH, timeout=10) as _c:
                        row = _c.execute(
                            "SELECT id FROM exames "
                            "WHERE arquivo_origem = ? AND status != 'rascunho'",
                            (nome,)
                        ).fetchone()
                    if row:
                        _log(f"[PROCESSAR] ✗ DUPLICATA — id={row[0]}")
                        on_erro(f"Exame já importado: {nome}")
                        return
                    _log(f"[PROCESSAR] ✔ Sem duplicata")
                except Exception as _ex:
                    _log(f"[PROCESSAR] ⚠ Verificação de duplicata falhou (ignorando): {_ex}")

            # ── Ler bytes ─────────────────────────────────────────
            set_status_fn("Lendo arquivo...", AZUL, 0.08, "carregando PDF...", True)
            conteudo = Path(caminho).read_bytes()
            _log(f"[PROCESSAR] ✔ Arquivo lido: {len(conteudo)//1024} KB")

            # ── Callback de progresso ─────────────────────────────
            def _on_prog(info):
                fase_e     = info.get("fase", "")
                pag        = info.get("pagina", 0)
                tot        = info.get("total_pags", 0)
                lins       = info.get("linhas", 0)
                itens      = info.get("itens", 0)
                total_lins = info.get("total_linhas", 0)

                if fase_e == "contando":
                    prog = (pag / tot * 0.30) if tot else None
                    det  = (f"PDF aberto — {tot} página(s) encontrada(s)" if pag == 0
                            else f"mapeando página {pag}/{tot} · {lins} linha(s)")
                    set_status_fn("Mapeando PDF...", AZUL, prog, det, True)

                elif fase_e == "lendo":
                    if total_lins > 0:
                        prog = 0.30 + min(lins / total_lins * 0.40, 0.40)
                        det  = f"processando página {pag}/{tot} · {lins}/{total_lins} linhas"
                    else:
                        prog = None
                        det  = f"processando página {pag}/{tot}"
                    set_status_fn("Processando PDF...", AZUL, prog, det, False)

                elif fase_e == "analisando":
                    set_status_fn("Analisando conteúdo...", AZUL, 0.75,
                                  f"{lins} linhas · identificando parâmetros...", True)

                elif fase_e == "extraindo":
                    set_status_fn("Extraindo resultados...", AZUL, 0.85,
                                  f"{lins} linhas processadas", True)

                elif fase_e == "concluido":
                    set_status_fn("Extração concluída!", VERD, 1.0,
                                  f"{itens} parâmetro(s) encontrado(s)", True)

            # ── Watchdog — heartbeat ativo (verifica a cada 1s) ──
            # Dispara após 5s de silêncio. Mantém percentual atual.
            # Anima pontos + contador de tempo para mostrar que não travou.
            import time as _time

            _ultimo_prog       = [_time.monotonic()]
            _prog_atual        = [0.85]
            _watchdog_ativo[0] = True

            _on_prog_orig = _on_prog
            def _on_prog(info):
                _ultimo_prog[0] = _time.monotonic()
                _on_prog_orig(info)

            _status_txt_orig = set_status_fn
            _msg_atual  = ["Extraindo resultados..."]
            _cor_atual  = [AZUL]
            def set_status_fn(msg, cor=AZUL, prog=None, detalhe="", force=False):
                if prog is not None:
                    _prog_atual[0] = prog
                _msg_atual[0]   = msg
                _cor_atual[0]   = cor
                _ultimo_prog[0] = _time.monotonic()
                _status_txt_orig(msg, cor, prog, detalhe, force)

            _pontos  = ["", ".", "..", "..."]
            _dot_idx = [0]

            def _watchdog():
                while _watchdog_ativo[0]:
                    _time.sleep(1)
                    if not _watchdog_ativo[0]:
                        break
                    silencio = _time.monotonic() - _ultimo_prog[0]
                    if silencio < 5:
                        continue
                    _dot_idx[0] = (_dot_idx[0] + 1) % 4
                    pontos   = _pontos[_dot_idx[0]]
                    segundos = int(silencio)
                    if segundos < 30:
                        detalhe = f"processando{pontos} ({segundos}s)"
                    elif segundos < 60:
                        detalhe = f"análise demorada — aguarde{pontos} ({segundos}s)"
                    elif segundos < 120:
                        detalhe = f"PDF complexo — processando{pontos} ({segundos}s)"
                    else:
                        mins = segundos // 60
                        detalhe = f"processamento longo ({mins}min {segundos%60}s){pontos}"
                    _status_txt_orig(
                        _msg_atual[0], _cor_atual[0],
                        _prog_atual[0],   # mantém o % — não regride
                        detalhe, True,
                    )

            threading.Thread(target=_watchdog, daemon=True).start()

            # ── Extração ──────────────────────────────────────────
            _log(f"[PROCESSAR] ▶ Iniciando extração PDF")
            dados = extrair_pdf_bytes(conteudo, nome, None, on_progress=_on_prog, caminho_pdf=caminho)
            _watchdog_ativo[0] = False   # para o watchdog
            _log(f"[PROCESSAR] ✔ Extração concluída — "
                 f"lab={dados.get('laboratorio')} tipo={dados.get('tipo')} "
                 f"resultados={len(dados.get('resultados', []))}")

            dados["arquivo_origem"] = nome
            dados["arquivo_path"]   = caminho

            # ── Vínculos ──────────────────────────────────────────
            set_status_fn("Verificando parâmetros...", AZUL, 0.92, "", True)
            params  = [r.get("parametro") for r in dados.get("resultados", [])
                       if r.get("parametro")]
            _log(f"[PROCESSAR] ✔ {len(params)} parâmetro(s) extraídos")

            vinc_ok = set()
            try:
                with sqlite3.connect(DB_PATH, timeout=10) as _c:
                    for p in params:
                        row = _c.execute(
                            "SELECT id FROM exames_padrao "
                            "WHERE UPPER(nome_oficial)=UPPER(?) "
                            "OR UPPER(sinonimos) LIKE UPPER(?)",
                            (p, f"%{p}%")
                        ).fetchone()
                        if row:
                            vinc_ok.add(p)
            except Exception as _ex:
                _log(f"[PROCESSAR] ⚠ Verificação de vínculos falhou (ignorando): {_ex}")

            pends = [{"parametro": p} for p in params if p not in vinc_ok]
            _log(f"[PROCESSAR] ✔ Vínculos: {len(vinc_ok)} ok · {len(pends)} pendente(s)")

            # ── Rascunho ──────────────────────────────────────────
            set_status_fn("Salvando rascunho...", AZUL, 0.96, "", True)
            eid = salvar_rascunho(dados)
            _log(f"[PROCESSAR] ✔ Rascunho salvo — exame_id={eid}")
            _log(f"[PROCESSAR] ■ FIM — chamando on_concluido")

            on_concluido(dados, pends, eid)

        except Exception as ex:
            _watchdog_ativo[0] = False   # para o watchdog em caso de erro
            logging.exception(f"[PROCESSAR] ✗ ERRO: {ex}")
            try:
                from dados.model_prontuario import registrar_log
                registrar_log(Path(caminho).name, "erro", str(ex))
            except Exception:
                pass
            on_erro(str(ex))

    threading.Thread(target=_run, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# 2. PAINEL DE CONFERÊNCIA — exibe dados extraídos + resolve pendências
#    Reutilizável: recebe on_liberar que decide o que fazer (upload ou não).
# ══════════════════════════════════════════════════════════════════════════════

def construir_painel_conferencia(
    page,
    dados: dict,
    pendencias_init: list,
    exame_id: int = None,   # None no novo fluxo (sem rascunho no banco)
    on_liberar  = None,     # fn() → chamado ao confirmar (sem pendências)
    on_cancelar = None,     # fn() → chamado ao cancelar
    label_confirmar: str = "Confirmar e Enviar",
    icone_confirmar = None,
):
    """
    Retorna uma lista de controles Flet com o painel de conferência completo.

    Parâmetros:
        page             : ft.Page
        dados            : dict retornado pelo extrator
        pendencias_init  : lista de {"parametro": str}  (pode ser mutada internamente)
        exame_id         : id do rascunho no banco
        on_liberar       : chamado quando botão Confirmar é clicado (sem pendências)
        on_cancelar      : chamado quando botão Cancelar é clicado
        label_confirmar  : texto do botão de confirmação
        icone_confirmar  : ícone Flet (None = CLOUD_UPLOAD_OUTLINED)
    """
    import flet as ft

    if icone_confirmar is None:
        icone_confirmar = "cloud_upload_outlined_rounded"

    results     = dados.get("resultados", [])
    pendencias  = list(pendencias_init)   # cópia local mutável
    params_pend = {p.get("parametro") for p in pendencias}

    lista_pend = [r for r in results if r.get("parametro") in params_pend]
    # Preview mostra TODOS os resultados — não filtra por vínculo
    # (na 1ª importação todos são pendências mas o usuário precisa ver os valores)
    lista_ok   = results

    tem_pend = [len(lista_pend) > 0]

    # ── Botão confirmar ────────────────────────────────────────────────────────
    btn_confirmar = ft.FilledButton(
        content=ft.Row([
            ft.Icon(icone_confirmar, size=16),
            ft.Text(label_confirmar, size=13, weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        style=ft.ButtonStyle(
            bgcolor=MUT if tem_pend[0] else VERD,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.Padding(left=20, right=20, top=12, bottom=12),
        ),
        disabled=tem_pend[0],
        on_click=lambda e: on_liberar(),
    )

    aviso_pend = ft.Container(
        visible=tem_pend[0],
        content=ft.Row([
            ft.Icon("lock_outlined_rounded", size=14, color=VERM),
            ft.Text(
                f"{len(lista_pend)} pendência(s) — resolva antes de enviar",
                size=11, color=VERM, weight=ft.FontWeight.W_600, expand=True,
            ),
        ], spacing=6),
        bgcolor=f"{VERM}14", border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border=ft.Border(
            left=ft.BorderSide(3, VERM),
            top=ft.BorderSide(1, f"{VERM}44"),
            bottom=ft.BorderSide(1, f"{VERM}44"),
            right=ft.BorderSide(1, f"{VERM}44"),
        ),
    )

    lista_pend_col = ft.Column(spacing=6)

    def _atualizar_botao():
        restam = len(pendencias)
        tem_pend[0] = restam > 0
        btn_confirmar.disabled = tem_pend[0]
        btn_confirmar.style.bgcolor = MUT if tem_pend[0] else VERD
        aviso_pend.visible = tem_pend[0]
        if tem_pend[0]:
            aviso_pend.content.controls[1].value = (
                f"{restam} pendência(s) — resolva antes de enviar"
            )
        # Atualizar label do preview se visível
        try:
            n = len(results)
            if corpo_preview.visible:
                _prev_label.value   = f"Ocultar {n} resultado(s)"
                _prev_chevron.value = "▲"
            else:
                _prev_label.value   = f"Ver {n} resultado(s) extraído(s)"
                _prev_chevron.value = "▼"
        except Exception:
            pass
        page.update()

    # ── Linha de resultado vinculado ──────────────────────────────────────────
    def _linha_resultado(r, cor):
        def _on_val(e): r["valor"]   = e.control.value
        def _on_uni(e): r["unidade"] = e.control.value
        return ft.Container(
            content=ft.Row([
                ft.Icon(
                    "check_circle_rounded" if cor == VERD else "warning_rounded",
                    size=14, color=cor,
                ),
                ft.Text(r.get("parametro", ""), size=12, color=TXT,
                        width=130, no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS),
                ft.TextField(
                    value=str(r.get("valor", "")),
                    hint_text="valor",
                    hint_style=ft.TextStyle(color=MUT),
                    bgcolor=BG, border_color=BD, focused_border_color=AZUL,
                    text_style=ft.TextStyle(color=TXT, size=12),
                    border_radius=6,
                    content_padding=ft.padding.symmetric(horizontal=8, vertical=6),
                    width=88, on_change=_on_val,
                ),
                ft.TextField(
                    value=r.get("unidade", ""),
                    hint_text="unid.",
                    hint_style=ft.TextStyle(color=MUT),
                    bgcolor=BG, border_color=BD, focused_border_color=AZUL,
                    text_style=ft.TextStyle(color=TXT, size=12),
                    border_radius=6,
                    content_padding=ft.padding.symmetric(horizontal=8, vertical=6),
                    width=68, on_change=_on_uni,
                ),
                ft.Text(r.get("referencia", ""), size=11, color=MUT,
                        expand=True, no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS),
            ], spacing=6),
            bgcolor=CARD, border_radius=6,
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border=ft.Border(left=ft.BorderSide(2, cor)),
        )

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _parsear_referencia(ref_str):
        """Extrai (min_str, max_str) de texto de referência do PDF."""
        import re
        s = ref_str.strip()
        nums = re.findall(r'[0-9]+(?:[,.][0-9]+)?', s)
        if len(nums) >= 2:
            return (nums[0].replace(",","."), nums[1].replace(",","."))
        if len(nums) == 1:
            return ("", nums[0].replace(",","."))
        return ("", "")

    # ── Card de pendência com formulário inline ───────────────────────────────
    def _card_pendencia(r):
        param = r.get("parametro", "").strip().replace("\n", " ").replace("\r", "")

        def _tf(label, value="", hint="", width=None, expand=False):
            return ft.TextField(
                value=value, label=label,
                hint_text=hint,
                hint_style=ft.TextStyle(color=MUT),
                bgcolor=BG, border_color=BD, focused_border_color=AZUL,
                label_style=ft.TextStyle(color=SEC, size=11),
                text_style=ft.TextStyle(color=TXT, size=12),
                border_radius=6,
                content_padding=ft.padding.symmetric(horizontal=8, vertical=6),
                width=width, expand=expand,
            )

        # Auto-preenche referência a partir do texto já extraído do PDF
        ref_raw       = r.get("referencia", "")
        ref_min_auto, ref_max_auto = _parsear_referencia(ref_raw)

        f_nome      = _tf("Nome oficial *", param, expand=True)
        f_unidade   = _tf("Unidade *",  r.get("unidade", ""), width=90)
        f_valor_form = _tf("Valor",     str(r.get("valor", "")), width=90)
        f_categoria = ft.Dropdown(
            label="Categoria",
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT, size=12),
            bgcolor=BG, border_color=BD, focused_border_color=AZUL,
            border_radius=6,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
            expand=True,
            options=[
                ft.dropdown.Option("Bioquímica"),
                ft.dropdown.Option("Hematologia"),
                ft.dropdown.Option("Hormônios"),
                ft.dropdown.Option("Vitaminas e Minerais"),
                ft.dropdown.Option("Inflamatórios"),
                ft.dropdown.Option("Marcadores Cardíacos"),
                ft.dropdown.Option("Marcadores Tumorais"),
                ft.dropdown.Option("Função Renal/Hepática"),
                ft.dropdown.Option("Coagulação"),
                ft.dropdown.Option("Urinálise"),
                ft.dropdown.Option("Microbiologia"),
                ft.dropdown.Option("Imunologia"),
            ],
        )
        f_ref_min   = _tf("Ref. mín *", ref_min_auto, width=80)
        f_ref_max   = _tf("Ref. máx *", ref_max_auto, width=80)
        f_obs_ref   = _tf("Obs. desta referência",
                          hint="ex: Normal > 60 | DRC < 60 | IR < 15  (mL/min/1,73m²)",
                          expand=True)
        f_obs_exame = _tf("Obs. do exame",
                          hint="ex: Calculado pela fórmula CKD-EPI. Válido > 18 anos.",
                          expand=True)
        ref_hint    = ft.Text(
            f"PDF: {ref_raw[:60]}" if ref_raw else "sem referência no PDF",
            size=10, color=MUT, italic=True,
        )

        msg_form       = ft.Text("", size=11, color=VERM)
        form_container = ft.Container(visible=False)

        def _mostrar_form(e=None):
            form_container.visible = True
            page.update()

        def _fechar_form(e=None):
            form_container.visible = False
            msg_form.value = ""
            page.update()

        def _salvar_padrao(e=None):
            nome_of  = f_nome.value.strip()
            unidade  = f_unidade.value.strip()
            ref_min  = f_ref_min.value.strip()
            ref_max  = f_ref_max.value.strip()
            # Atualiza valor em memória se foi editado no form
            if f_valor_form.value.strip():
                r["valor"] = f_valor_form.value.strip()

            # Validação obrigatória
            erros = []
            if not nome_of: erros.append("Nome oficial")
            if not unidade: erros.append("Unidade")
            if not ref_min: erros.append("Ref. mín")
            if not ref_max: erros.append("Ref. máx")
            if erros:
                msg_form.value = f"Obrigatório: {', '.join(erros)}"
                page.update()
                return

            try:
                ref_min_f = float(ref_min.replace(",", "."))
                ref_max_f = float(ref_max.replace(",", "."))
            except ValueError:
                msg_form.value = "Ref. mín e máx devem ser números."
                page.update()
                return



            try:
                with sqlite3.connect(DB_PATH, timeout=10) as _c:
                    # Cria ou busca exame_padrao
                    row = _c.execute(
                        "SELECT id FROM exames_padrao WHERE UPPER(nome_oficial)=UPPER(?)",
                        (nome_of,)
                    ).fetchone()
                    if row:
                        padrao_id = row[0]
                        # Atualiza unidade/categoria/obs se estava vazio
                        _obs_ep  = f_obs_exame.value.strip() or None
                        _cat_val = f_categoria.value or ""
                        _c.execute(
                            "UPDATE exames_padrao SET unidade=COALESCE(NULLIF(unidade,''),?), "
                            "categoria=COALESCE(NULLIF(categoria,''),?), "
                            "observacoes=COALESCE(NULLIF(observacoes,''),?) WHERE id=?",
                            (unidade, _cat_val, _obs_ep, padrao_id)
                        )
                    else:
                        _obs_ep  = f_obs_exame.value.strip() or None
                        _cat_val = f_categoria.value or ""
                        cur = _c.execute(
                            "INSERT INTO exames_padrao "
                            "(nome_oficial, sinonimos, categoria, unidade, tipo, observacoes) "
                            "VALUES (?,?,?,?,'numerico',?)",
                            (nome_of, param, _cat_val, unidade, _obs_ep)
                        )
                        padrao_id = cur.lastrowid

                    # Salva nova versão de referência (mantém histórico)
                    _obs_ref = f_obs_ref.value.strip() or None
                    _c.execute("""
                        INSERT INTO referencias_padrao
                            (exame_padrao_id, sexo, limite_baixo, limite_alto,
                             observacoes, criado_em)
                        VALUES (?,?,?,?,?, datetime('now'))
                    """, (padrao_id, None, ref_min_f, ref_max_f, _obs_ref))  # sexo vem do perfil na consulta

                    # Vincula em memória nos dados (sem banco ainda — gravação só ao confirmar)
                    for _r in results:
                        if _r.get("parametro", "").upper() == param.upper():
                            _r["exame_padrao_id"] = padrao_id
                            break
                    _c.commit()   # commit só do exame_padrao + referencias_padrao

                # Remove da lista de pendências
                for i, p in enumerate(pendencias):
                    if p.get("parametro") == param:
                        pendencias.pop(i)
                        break

                lista_pend_col.controls = [
                    c for c in lista_pend_col.controls
                    if getattr(c, "_param_pend", None) != param
                ]
                _log(f"[CONFERENCIA] ✔ Padrão '{nome_of}' salvo "
                     f"ref=[{ref_min_f},{ref_max_f}] — pendências: {len(pendencias)}")
                _atualizar_botao()

                page.snack_bar = ft.SnackBar(
                    ft.Text(f"'{nome_of}' cadastrado com referência.", color=TXT),
                    bgcolor=VERD)
                page.snack_bar.open = True
                page.update()

            except Exception as ex:
                _log(f"[CONFERENCIA] ✗ Erro ao salvar padrão: {ex}")
                msg_form.value = f"Erro: {str(ex)[:60]}"
                page.update()

        form_container.content = ft.Container(
            content=ft.Column([
                ft.Row([f_nome], spacing=0),
                ft.Row([f_unidade, f_valor_form], spacing=8),
                ft.Row([f_categoria], spacing=0),
                ft.Row([
                    ft.Icon("info_outline_rounded", size=12, color=MUT),
                    ref_hint,
                ], spacing=4) if ref_raw else ft.Container(height=0),
                ft.Row([
                    ft.Text("Referência:", size=11, color=SEC),
                    f_ref_min,
                    ft.Text("até", size=11, color=MUT),
                    f_ref_max,
                    ft.Container(expand=True),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([f_obs_ref], spacing=0),
                ft.Row([f_obs_exame], spacing=0),
                ft.Row([
                    msg_form,
                    ft.Container(expand=True),
                    ft.Container(
                        content=ft.Text("Cancelar", size=13, color=SEC),
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        border_radius=8, ink=True,
                        on_click=_fechar_form,
                    ),
                    ft.FilledButton(
                        content=ft.Row([
                            ft.Icon("save_outlined_rounded", size=14),
                            ft.Text("Salvar padrão", size=12,
                                    weight=ft.FontWeight.W_600),
                        ], spacing=4, tight=True),
                        style=ft.ButtonStyle(
                            bgcolor=VERD,
                            shape=ft.RoundedRectangleBorder(radius=7),
                            padding=ft.padding.symmetric(horizontal=14, vertical=8),
                        ),
                        on_click=_salvar_padrao,
                    ),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=8),
            bgcolor=f"{VERD}0A", border_radius=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=10),
            border=ft.Border(
                left=ft.BorderSide(2, VERD),
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                right=ft.BorderSide(1, BD),
            ),
        )

        def _abrir_pdf(e=None):
            import subprocess, sys
            arq = dados.get("arquivo_path", "")
            if not arq:
                return
            try:
                if sys.platform == "win32":
                    import os as _os
                    _os.startfile(arq)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", arq])
                else:
                    subprocess.Popen(["xdg-open", arq])
            except Exception as ex:
                _log(f"[PDF] Erro ao abrir: {ex}")

        def _on_val_pend(e): r["valor"]   = e.control.value
        def _on_uni_pend(e): r["unidade"] = e.control.value

        tf_valor = ft.TextField(
            value=str(r.get("valor", "")),
            hint_text="valor",
            hint_style=ft.TextStyle(color=MUT),
            bgcolor=BG, border_color=BD, focused_border_color=AZUL,
            text_style=ft.TextStyle(color=TXT, size=12),
            border_radius=6,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
            width=80, on_change=_on_val_pend,
        )
        tf_unidade = ft.TextField(
            value=r.get("unidade", ""),
            hint_text="unid.",
            hint_style=ft.TextStyle(color=MUT),
            bgcolor=BG, border_color=BD, focused_border_color=AZUL,
            text_style=ft.TextStyle(color=TXT, size=12),
            border_radius=6,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
            width=68, on_change=_on_uni_pend,
        )

        # Sub-resultados como linhas indentadas (ex: eRFG filho de Creatinina)
        sub_rows = []
        for sub in r.get("sub_resultados", []):
            def _mk_sub(s):
                def _on_sv(e): s["valor"]   = e.control.value
                def _on_su(e): s["unidade"] = e.control.value
                return ft.Container(
                    content=ft.Row([
                        ft.Container(width=18),
                        ft.Icon("subdirectory_arrow_right_rounded", size=12, color=MUT),
                        ft.Text(s.get("parametro",""), size=11, color=MUT, width=110,
                                no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.TextField(
                            value=str(s.get("valor","")), hint_text="valor",
                            hint_style=ft.TextStyle(color=MUT),
                            bgcolor=BG, border_color=BD,
                            text_style=ft.TextStyle(color=TXT, size=11),
                            border_radius=6,
                            content_padding=ft.padding.symmetric(horizontal=6, vertical=3),
                            width=72, on_change=_on_sv,
                        ),
                        ft.TextField(
                            value=s.get("unidade",""), hint_text="unid.",
                            hint_style=ft.TextStyle(color=MUT),
                            bgcolor=BG, border_color=BD,
                            text_style=ft.TextStyle(color=TXT, size=11),
                            border_radius=6,
                            content_padding=ft.padding.symmetric(horizontal=6, vertical=3),
                            width=60, on_change=_on_su,
                        ),
                        ft.Text(s.get("referencia",""), size=10, color=MUT,
                                expand=True, no_wrap=True,
                                overflow=ft.TextOverflow.ELLIPSIS),
                    ], spacing=4),
                    padding=ft.padding.only(top=2),
                )
            sub_rows.append(_mk_sub(sub))

        card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon("warning_rounded", size=14, color=AMAR),
                    ft.Text(param, size=12, color=TXT, weight=ft.FontWeight.W_600,
                            expand=True, no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS),
                    ft.IconButton(
                        icon="picture_as_pdf_outlined_rounded",
                        icon_color=VERM,
                        icon_size=18,
                        tooltip="Abrir PDF para consultar referências",
                        on_click=_abrir_pdf,
                    ),
                    ft.FilledButton(
                        content=ft.Row([
                            ft.Icon("add_outlined_rounded", size=14),
                            ft.Text("Incluir padrão", size=12,
                                    weight=ft.FontWeight.W_600),
                        ], spacing=4, tight=True),
                        style=ft.ButtonStyle(
                            bgcolor=AMAR,
                            shape=ft.RoundedRectangleBorder(radius=7),
                            padding=ft.padding.symmetric(horizontal=12, vertical=6),
                        ),
                        on_click=_mostrar_form,
                    ),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                *sub_rows,
                form_container,
            ], spacing=6),
            bgcolor=CARD, border_radius=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=10),
            border=ft.Border(
                left=ft.BorderSide(3, AMAR),
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                right=ft.BorderSide(1, BD),
            ),
        )
        card._param_pend = param
        return card

    # Montar lista de pendências
    for r in lista_pend:
        lista_pend_col.controls.append(_card_pendencia(r))

    # ── Montar controles do painel ─────────────────────────────────────────────
    controles = [
        ft.Row([
            ft.Icon("assignment_turned_in_rounded", size=18, color=AZUL),
            ft.Text("Conferência dos dados extraídos", size=15,
                    weight=ft.FontWeight.W_700, color=TXT),
        ], spacing=8),
        ft.Container(height=4),
        ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Tipo:",     size=12, color=SEC),
                    ft.Text(dados.get("tipo_exame") or "—",    size=12, color=TXT),
                    ft.Container(width=16),
                    ft.Text("Data:",     size=12, color=SEC),
                    ft.Text(dados.get("data_exame") or "—",    size=12, color=TXT),
                ], spacing=4, wrap=True),
                ft.Row([
                    ft.Text("Lab:",      size=12, color=SEC),
                    ft.Text(dados.get("laboratorio") or "—",   size=12, color=TXT),
                    ft.Container(width=16),
                    ft.Text("Paciente:", size=12, color=SEC),
                    ft.Text(dados.get("paciente_nome") or "—", size=12, color=TXT),
                ], spacing=4, wrap=True),
            ], spacing=6),
            bgcolor=CARD, border_radius=8, padding=12,
            border=ft.Border(
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                left=ft.BorderSide(1, BD), right=ft.BorderSide(1, BD),
            ),
        ),
        ft.Container(height=8),
    ]

    # ── Botão abrir PDF local ──────────────────────────────────────────────────
    _arquivo_path = dados.get("arquivo_path") or dados.get("arquivo_origem") or ""
    if _arquivo_path:
        import os as _os
        _nome_pdf = _os.path.basename(_arquivo_path)

        def _abrir_pdf_local(e=None):
            try:
                import webbrowser, pathlib
                uri = pathlib.Path(_arquivo_path).resolve().as_uri()
                webbrowser.open(uri)
            except Exception as _ex:
                _log(f"[PAINEL] abrir PDF: {_ex}")

        _btn_pdf = ft.Container(
            content=ft.Row([
                ft.Icon("picture_as_pdf_rounded", size=14, color=VERM),
                ft.Text(_nome_pdf, size=12, color=AZUL, expand=True,
                        no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Icon("open_in_new_rounded", size=13, color=SEC),
            ], spacing=6),
            bgcolor=f"{VERM}10", border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border=ft.Border(
                left=ft.BorderSide(2, VERM),
                top=ft.BorderSide(1, f"{VERM}33"),
                bottom=ft.BorderSide(1, f"{VERM}33"),
                right=ft.BorderSide(1, f"{VERM}33"),
            ),
            ink=True,
        )
        _btn_pdf.on_click = _abrir_pdf_local
        controles += [_btn_pdf, ft.Container(height=8)]

    if lista_pend:
        controles += [
            aviso_pend,
            ft.Container(height=6),
            lista_pend_col,
            ft.Container(height=8),
        ]

    # ── Painel colapsável de prévia dos resultados ────────────────────────────
    if lista_ok or lista_pend:
        todos_resultados = lista_ok + lista_pend  # pend já aparece acima, ok aparece aqui

        # Cabeçalho da tabela
        def _cabecalho_tabela():
            return ft.Container(
                content=ft.Row([
                    ft.Text("Parâmetro",  size=10, color=MUT, weight=ft.FontWeight.W_600, width=160),
                    ft.Text("Valor",      size=10, color=MUT, weight=ft.FontWeight.W_600, width=70),
                    ft.Text("Unidade",    size=10, color=MUT, weight=ft.FontWeight.W_600, width=80),
                    ft.Text("Referência", size=10, color=MUT, weight=ft.FontWeight.W_600, expand=True),
                ], spacing=0),
                bgcolor=f"{MUT}18",
                border_radius=ft.BorderRadius(6, 6, 0, 0),
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
            )

        def _linha_tabela(r, idx):
            """Linha zebrada da tabela de prévia."""
            is_pend  = r.get("parametro") in params_pend
            cor_txt  = VERM if is_pend else TXT
            cor_val  = VERM if is_pend else AZUL
            bg_linha = f"{VERM}0A" if is_pend else (f"{BG}CC" if idx % 2 == 0 else CARD)

            linhas = [ft.Container(
                content=ft.Row([
                    ft.Row([
                        ft.Icon(
                            "warning_rounded" if is_pend else "check_circle_outline_rounded",
                            size=11,
                            color=VERM if is_pend else VERD,
                        ),
                        ft.Text(
                            r.get("parametro", ""),
                            size=11, color=cor_txt, width=143,
                            no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ], spacing=4, width=160),
                    ft.Text(
                        str(r.get("valor", "—")),
                        size=11, color=cor_val, weight=ft.FontWeight.W_600, width=70,
                    ),
                    ft.Text(
                        r.get("unidade", ""),
                        size=11, color=SEC, width=80,
                    ),
                    ft.Text(
                        r.get("referencia", ""),
                        size=10, color=MUT, expand=True,
                        no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ], spacing=0),
                bgcolor=bg_linha,
                padding=ft.padding.symmetric(horizontal=10, vertical=5),
            )]

            # Sub-resultados (ex: eRFG)
            for sub in r.get("sub_resultados", []):
                linhas.append(ft.Container(
                    content=ft.Row([
                        ft.Row([
                            ft.Container(width=14),
                            ft.Icon("subdirectory_arrow_right_rounded", size=10, color=MUT),
                            ft.Text(sub.get("parametro", ""), size=10, color=MUT,
                                    width=130, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                        ], spacing=3, width=160),
                        ft.Text(str(sub.get("valor", "—")), size=10, color=AZUL,
                                weight=ft.FontWeight.W_600, width=70),
                        ft.Text(sub.get("unidade", ""), size=10, color=MUT, width=80),
                        ft.Text(sub.get("referencia", ""), size=10, color=MUT, expand=True,
                                no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                    ], spacing=0),
                    bgcolor=bg_linha,
                    padding=ft.padding.symmetric(horizontal=10, vertical=3),
                ))
            return linhas

        # Montar linhas da tabela
        linhas_tabela = []
        for idx, r in enumerate(lista_ok):
            linhas_tabela += _linha_tabela(r, idx)

        tabela_col = ft.Column(
            controls=linhas_tabela,
            spacing=0,
        )

        _preview_aberto = len(lista_pend) == 0   # abre por padrao se sem pendencias

        corpo_preview = ft.Container(
            content=ft.Column([
                _cabecalho_tabela(),
                ft.Container(
                    content=tabela_col,
                    border=ft.Border(
                        left=ft.BorderSide(1, BD), right=ft.BorderSide(1, BD),
                        bottom=ft.BorderSide(1, BD),
                    ),
                    border_radius=ft.BorderRadius(0, 0, 6, 6),
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                ),
            ], spacing=0),
            visible=_preview_aberto,
        )

        _n_prev = len(lista_ok)
        _prev_label   = ft.Text(
            value=(f"Ocultar {_n_prev} resultado(s)"
                   if _preview_aberto
                   else f"Ver {_n_prev} resultado(s) extraído(s)"),
            size=12, color=AZUL, weight=ft.FontWeight.W_600,
        )
        _prev_chevron = ft.Text("▲" if _preview_aberto else "▼", size=12, color=AZUL)

        def _toggle_preview(e=None):
            corpo_preview.visible = not corpo_preview.visible
            n = len(lista_ok)
            if corpo_preview.visible:
                _prev_chevron.value = "▲"
                _prev_label.value   = f"Ocultar {n} resultado(s)"
            else:
                _prev_chevron.value = "▼"
                _prev_label.value   = f"Ver {n} resultado(s) extraído(s)"
            page.update()

        btn_preview = ft.Container(
            content=ft.Row([
                ft.Icon("table_rows_outlined_rounded", size=14, color=AZUL),
                _prev_label,
                ft.Container(expand=True),
                _prev_chevron,
            ], spacing=6),
            bgcolor=f"{AZUL}12",
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border=ft.Border(
                left=ft.BorderSide(2, AZUL),
                top=ft.BorderSide(1, f"{AZUL}33"),
                bottom=ft.BorderSide(1, f"{AZUL}33"),
                right=ft.BorderSide(1, f"{AZUL}33"),
            ),
            on_click=_toggle_preview,
            ink=True,
        )

        controles += [
            btn_preview,
            corpo_preview,
            ft.Container(height=8),
        ]

    # ── Seção editável de laudo (para qualquer tipo que tenha laudo_dict) ────────
    laudo_dict = dados.get("laudo") or {}
    if laudo_dict and any(laudo_dict.get(k) for k in ("resumo", "conclusao", "texto_completo")):
        tf_resumo = ft.TextField(
            label="Resumo / Achados",
            value=laudo_dict.get("resumo", ""),
            multiline=True, min_lines=3, max_lines=8,
            bgcolor=BG, border_color=BD, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT, size=12),
            border_radius=6,
        )
        tf_conclusao = ft.TextField(
            label="Conclusao / Diagnostico",
            value=laudo_dict.get("conclusao", ""),
            multiline=True, min_lines=2, max_lines=5,
            bgcolor=BG, border_color=BD, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT, size=12),
            border_radius=6,
        )

        def _on_resumo(e):
            dados["laudo"]["resumo"] = e.control.value

        def _on_conclusao(e):
            dados["laudo"]["conclusao"] = e.control.value

        tf_resumo.on_change    = _on_resumo
        tf_conclusao.on_change = _on_conclusao

        laudo_expandido = [False]
        laudo_body = ft.Column([tf_resumo, tf_conclusao], spacing=8, visible=False)
        laudo_chev = ft.Text("▼", size=12, color=AZUL)

        def _toggle_laudo(e=None):
            laudo_expandido[0] = not laudo_expandido[0]
            laudo_body.visible = laudo_expandido[0]
            laudo_chev.value   = "▲" if laudo_expandido[0] else "▼"
            page.update()

        btn_laudo = ft.Container(
            content=ft.Row([
                ft.Icon("description_rounded", size=14, color=AZUL),
                ft.Text("Editar Laudo Extraido", size=12, color=AZUL,
                        weight=ft.FontWeight.W_600),
                ft.Container(expand=True),
                laudo_chev,
            ], spacing=6),
            bgcolor=f"{AZUL}12", border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border=ft.Border(
                left=ft.BorderSide(2, AZUL),
                top=ft.BorderSide(1, f"{AZUL}33"),
                bottom=ft.BorderSide(1, f"{AZUL}33"),
                right=ft.BorderSide(1, f"{AZUL}33"),
            ),
            ink=True,
        )
        btn_laudo.on_click = _toggle_laudo

        controles += [ft.Container(height=4), btn_laudo, laudo_body, ft.Container(height=4)]

    # ── Galeria de preview das imagens extraidas ───────────────────────────────
    imagens = dados.get("imagens_extraidas", [])
    _imagens_selecionadas = list(imagens)   # cópia mutável (exclui imagens indesejadas)

    if imagens:
        grade_imgs = ft.Row(wrap=True, spacing=8, run_spacing=8)

        def _rebuild_grade():
            grade_imgs.controls.clear()
            for img_info in list(_imagens_selecionadas):
                def _excluir(e, info=img_info):
                    _imagens_selecionadas.remove(info)
                    _rebuild_grade()
                    page.update()

                miniatura = ft.Stack([
                    ft.Container(
                        content=ft.Image(
                            src=img_info["arquivo_local"].replace("\\", "/"),
                            width=120, height=90,
                            fit=ft.ImageFit.COVER,
                            error_content=ft.Icon("broken_image_rounded", size=20, color=MUT),
                        ),
                        width=120, height=90, border_radius=8,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        border=ft.Border(
                            top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                            left=ft.BorderSide(1, BD), right=ft.BorderSide(1, BD),
                        ),
                    ),
                    ft.Container(
                        content=ft.Icon("close_rounded", size=12, color=TXT),
                        bgcolor="#CC000000",
                        border_radius=ft.BorderRadius(0, 6, 0, 6),
                        padding=3, right=0, top=0,
                        ink=True,
                        on_click=_excluir,
                    ),
                ])
                grade_imgs.controls.append(miniatura)

        _rebuild_grade()

        corpo_imgs = ft.Container(content=grade_imgs, visible=False)
        imgs_chev  = ft.Text("▼", size=12, color=VERD)
        imgs_label = ft.Text(
            f"Ver {len(imagens)} foto(s) extraida(s)",
            size=12, color=VERD, weight=ft.FontWeight.W_600,
        )

        def _toggle_imgs(e=None):
            corpo_imgs.visible = not corpo_imgs.visible
            imgs_chev.value = "▲" if corpo_imgs.visible else "▼"
            page.update()

        btn_imgs = ft.Container(
            content=ft.Row([
                ft.Icon("photo_library_rounded", size=14, color=VERD),
                imgs_label,
                ft.Container(expand=True),
                imgs_chev,
            ], spacing=6),
            bgcolor=f"{VERD}12", border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border=ft.Border(
                left=ft.BorderSide(2, VERD),
                top=ft.BorderSide(1, f"{VERD}33"),
                bottom=ft.BorderSide(1, f"{VERD}33"),
                right=ft.BorderSide(1, f"{VERD}33"),
            ),
            ink=True,
        )
        btn_imgs.on_click = _toggle_imgs

        controles += [ft.Container(height=4), btn_imgs, corpo_imgs, ft.Container(height=8)]

    # ── Fallback: texto bruto quando não há resultados nem laudo ──────────────
    _tem_conteudo = bool(results) or bool(laudo_dict)
    _texto_bruto  = (dados.get("resultado_texto") or "").strip()
    if not _tem_conteudo and _texto_bruto:
        _txt_bruto_label  = ft.Text("Ver texto extraído do PDF", size=12, color=AMAR,
                                    weight=ft.FontWeight.W_600)
        _txt_bruto_chev   = ft.Text("▼", size=12, color=AMAR)
        _txt_bruto_corpo  = ft.Container(
            content=ft.Text(
                _texto_bruto[:4000] + ("…" if len(_texto_bruto) > 4000 else ""),
                size=11, color=SEC, selectable=True,
            ),
            bgcolor=BG, border_radius=6, padding=10,
            border=ft.Border(
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                left=ft.BorderSide(1, BD), right=ft.BorderSide(1, BD),
            ),
            visible=False,
        )

        def _toggle_bruto(e=None):
            _txt_bruto_corpo.visible = not _txt_bruto_corpo.visible
            _txt_bruto_chev.value   = "▲" if _txt_bruto_corpo.visible else "▼"
            page.update()

        _btn_bruto = ft.Container(
            content=ft.Row([
                ft.Icon("text_snippet_rounded", size=14, color=AMAR),
                _txt_bruto_label,
                ft.Container(expand=True),
                _txt_bruto_chev,
            ], spacing=6),
            bgcolor=f"{AMAR}12", border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border=ft.Border(
                left=ft.BorderSide(2, AMAR),
                top=ft.BorderSide(1, f"{AMAR}33"),
                bottom=ft.BorderSide(1, f"{AMAR}33"),
                right=ft.BorderSide(1, f"{AMAR}33"),
            ),
            ink=True,
        )
        _btn_bruto.on_click = _toggle_bruto
        controles += [ft.Container(height=4), _btn_bruto, _txt_bruto_corpo, ft.Container(height=8)]

    # ── Wrap de on_liberar para upload Drive de imagens ───────────────────────
    _on_liberar_orig = on_liberar

    def _on_liberar_com_imgs():
        if not _imagens_selecionadas:
            _on_liberar_orig()
            return

        # Tentar upload no Drive; se falhar, salvar local com pendente_sync=1
        try:
            from utils.drive_sync import _get_creds, garantir_pasta, upload_foto as _up_foto
            import os as _os
            creds    = _get_creds()
            pasta_id = garantir_pasta("EXAME_IMAGENS", creds=creds)
            anexos = []
            for img_info in _imagens_selecionadas:
                try:
                    drive_id = _up_foto(
                        img_info["arquivo_local"],
                        img_info["nome_arquivo"],
                        pasta_id, creds,
                    )
                    _os.remove(img_info["arquivo_local"])
                    anexos.append({
                        "drive_file_id": drive_id,
                        "nome_arquivo":  img_info["nome_arquivo"],
                        "ordem":         img_info["ordem"],
                    })
                    _log(f"[IMG] upload OK: {img_info['nome_arquivo']} → {drive_id}")
                except Exception as ex_up:
                    _log(f"[IMG] upload falhou ({img_info['nome_arquivo']}): {ex_up}")
                    anexos.append({
                        "arquivo_local": img_info["arquivo_local"],
                        "nome_arquivo":  img_info["nome_arquivo"],
                        "ordem":         img_info["ordem"],
                        "pendente_sync": 1,
                    })
        except Exception as ex_drive:
            _log(f"[IMG] Drive indisponivel — salvando local: {ex_drive}")
            anexos = [
                {
                    "arquivo_local": img["arquivo_local"],
                    "nome_arquivo":  img["nome_arquivo"],
                    "ordem":         img["ordem"],
                    "pendente_sync": 1,
                }
                for img in _imagens_selecionadas
            ]

        dados["anexos"] = dados.get("anexos", []) + anexos
        _on_liberar_orig()

    on_liberar = _on_liberar_com_imgs

    controles += [
        ft.Divider(color=BD, height=1),
        ft.Container(height=8),
        ft.Row([
            ft.FilledButton(
                content=ft.Row([
                    ft.Icon("close_rounded", size=16),
                    ft.Text("Cancelar", size=13, weight=ft.FontWeight.W_600),
                ], spacing=6, tight=True),
                style=ft.ButtonStyle(
                    bgcolor=MUT, shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.Padding(left=20, right=20, top=12, bottom=12),
                ),
                on_click=lambda e: on_cancelar(),
            ),
            btn_confirmar,
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
        ft.Container(height=16),
    ]

    return controles