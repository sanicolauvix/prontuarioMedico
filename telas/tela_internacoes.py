# -*- coding: utf-8 -*-
# KOIOS v1.0 | telas/tela_internacoes.py
"""
Internacoes hospitalares e procedimentos medicos.
Duas abas: Internacoes | Procedimentos.
Formularios via overlay.
"""
import flet as ft
import logging
import datetime
import os
import subprocess
import threading
import webbrowser

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; LAR = "#F0883E"
AMAR = "#D29922"; VERM = "#DA3633"; ROXO = "#BC8CFF"


def _flex_parse(s: str) -> "datetime.datetime | None":
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime((s or "")[:10], fmt)
        except ValueError:
            pass
    return None


def _para_display(s: str | None) -> str:
    if not s:
        return ""
    s = str(s).strip()
    if len(s) >= 10 and s[4] == "-":
        try:
            return datetime.datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            pass
    return s

_TIPO_INTER = [
    ("eletiva",    "Eletiva",    VERD),
    ("urgencia",   "Urgencia",   AMAR),
    ("emergencia", "Emergencia", VERM),
]

_GATILHO_INTER = [
    ("estresse",       "Estresse"),
    ("esforcofisico",  "Esforco fisico"),
    ("espontaneo",     "Espontaneo"),
    ("posoperatorio",  "Pos-operatorio"),
    ("outro",          "Outro"),
]

_TIPO_PROC = [
    ("cirurgico",    "Cirurgico",    VERM),
    ("diagnostico",  "Diagnostico",  AZUL),
    ("terapeutico",  "Terapeutico",  VERD),
    ("ambulatorial", "Ambulatorial", AMAR),
]

_ANESTESIA = [
    ("sem",      "Sem"),
    ("local",    "Local"),
    ("sedacao",  "Sedacao"),
    ("epidural", "Epidural"),
    ("geral",    "Geral"),
]


def _cor_tipo_inter(tipo):
    return next((c for k, _, c in _TIPO_INTER if k == tipo), SEC)


def _label_tipo_inter(tipo):
    return next((l for k, l, _ in _TIPO_INTER if k == tipo), tipo)


def _cor_tipo_proc(tipo):
    return next((c for k, _, c in _TIPO_PROC if k == tipo), SEC)


def _label_tipo_proc(tipo):
    return next((l for k, l, _ in _TIPO_PROC if k == tipo), tipo)


def _duracao(entrada: str, saida: str | None) -> str:
    if not entrada:
        return ""
    try:
        d0 = _flex_parse(entrada)
        d1 = _flex_parse(saida) if saida else datetime.datetime.today()
        if d0 is None:
            return ""
        dias = (d1 - d0).days
        return f"{dias} dia{'s' if dias != 1 else ''}"
    except Exception:
        return ""


def _campo_medico(page, medicos, med_id_sel, valor_ini=""):
    """Campo de busca de medico com chip. med_id_sel e lista mutavel [str|None]."""
    med_chip = ft.Container(
        content=ft.Row([
            ft.Icon("person_rounded", size=13, color=AZUL),
            ft.Text("", size=12, color=AZUL, weight=ft.FontWeight.W_600),
            ft.Icon("close_rounded", size=13, color=AZUL),
        ], spacing=6, tight=True),
        bgcolor=f"{AZUL}18", border_radius=16,
        padding=ft.padding.symmetric(horizontal=10, vertical=5),
        visible=False,
    )
    tf = ft.TextField(
        hint_text="Buscar medico...",
        prefix_icon="search_rounded",
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        hint_style=ft.TextStyle(color=MUT),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, expand=True, height=42,
        visible=not bool(valor_ini),
    )
    sugestoes = ft.Column(spacing=4, visible=False)

    def _mostrar_chip(nome):
        med_chip.content.controls[1].value = nome
        med_chip.visible = True
        tf.visible = False
        sugestoes.controls.clear()
        sugestoes.visible = False
        try: page.update()
        except Exception: pass

    def _limpar(e=None):
        med_id_sel[0] = None
        med_chip.visible = False
        tf.value = ""
        tf.visible = True
        sugestoes.controls.clear()
        sugestoes.visible = False
        try: page.update()
        except Exception: pass

    med_chip.on_click = _limpar

    if valor_ini:
        _mostrar_chip(valor_ini)

    def _filtrar(e):
        termo = (tf.value or "").strip().upper()
        sugestoes.controls.clear()
        if not termo:
            sugestoes.visible = False
            try: page.update()
            except Exception: pass
            return
        matches = [m for m in medicos if termo in m["nome"].upper()][:8]
        if not matches:
            sugestoes.controls.append(ft.Container(
                content=ft.Text("Nenhum medico encontrado.", size=12, color=MUT),
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            ))
            sugestoes.visible = True
            try: page.update()
            except Exception: pass
            return
        for m in matches:
            esp = m.get("especialidade") or ""
            def _make_sel(med=m):
                def sel(e):
                    med_id_sel[0] = str(med["id"])
                    _mostrar_chip(med["nome"])
                return sel
            item = ft.Container(
                content=ft.Row([
                    ft.Icon("person_rounded", size=13, color=AZUL),
                    ft.Column([
                        ft.Text(m["nome"], size=13, color=TXT),
                        ft.Text(esp, size=10, color=MUT) if esp else ft.Container(height=0),
                    ], spacing=0, tight=True),
                ], spacing=8),
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                bgcolor=CARD, border_radius=8, ink=True,
            )
            item.on_click = _make_sel()
            sugestoes.controls.append(item)
        sugestoes.visible = True
        try: page.update()
        except Exception: pass

    tf.on_change = _filtrar

    col = ft.Column([
        ft.Row([med_chip, tf], spacing=6),
        sugestoes,
    ], spacing=4)
    return col


def _chip_seletor(opcoes, sel_ref, cor_ativa=AZUL):
    """Grupo de chips mutualmente exclusivos. opcoes = [(valor, label)]. sel_ref=[valor]."""
    row = ft.Row(spacing=6, wrap=True)

    def _render():
        row.controls.clear()
        for val, label in opcoes:
            ativo = sel_ref[0] == val
            chip = ft.Container(
                content=ft.Text(label, size=11,
                                color=cor_ativa if ativo else SEC,
                                weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.NORMAL),
                bgcolor=f"{cor_ativa}22" if ativo else CARD,
                border=ft.border.all(1, cor_ativa if ativo else BD),
                border_radius=14,
                padding=ft.padding.symmetric(horizontal=10, vertical=5),
                ink=True,
            )
            def _click(e, v=val):
                sel_ref[0] = v
                _render()
            chip.on_click = _click
            row.controls.append(chip)

    _render()
    return row


def _tf(label, valor="", hint="", multiline=False, expand=False, altura=None):
    kw = {}
    if altura:
        kw["min_lines"] = 3
        kw["max_lines"] = 6
    return ft.TextField(
        label=label, value=valor, hint_text=hint,
        bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC, size=11),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, expand=expand,
        multiline=multiline or bool(altura),
        **kw,
    )


def criar_tela_internacoes(page: ft.Page, voltar_fn, navegar_fn=None) -> ft.Container:
    import threading as _thr
    from shared.layout import Layout
    from dados.model_prontuario import (
        listar_internacoes, salvar_internacao, excluir_internacao,
        listar_procedimentos, salvar_procedimento, excluir_procedimento,
        listar_medicos,
    )

    lay           = Layout(page)
    _montado      = [False]
    _status_banco = ["normal"]
    _handler_ant  = [None]

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
                log.warning("[INTER] sync: %s", ex)
            finally:
                _status_banco[0] = "normal"
                if ov in page.overlay:
                    page.overlay.remove(ov)
                try: page.update()
                except Exception: pass
                if apos_sync_fn:
                    apos_sync_fn()

        _thr.Thread(target=_run, daemon=True).start()

    def _sair(destino_fn):
        _desregistrar_voltar_hw()
        if _status_banco[0] == "em_edicao":
            _sync(destino_fn)
        else:
            destino_fn()

    def _registrar_voltar_hw():
        _handler_ant[0] = page.on_keyboard_event
        def _on_hw(e):
            if e.key == "Escape":
                _sair(voltar_fn)
        page.on_keyboard_event = _on_hw

    def _desregistrar_voltar_hw():
        page.on_keyboard_event = _handler_ant[0]

    # cache
    _internacoes  = [listar_internacoes()]
    _procedimentos = [listar_procedimentos()]
    _medicos       = [listar_medicos()]

    # ── filepicker para importar PDF ─────────────────────────────

    _picker = ft.FilePicker()
    page.overlay.append(_picker)

    def _mesclar_pdfs(caminhos: list[str]) -> tuple[bytes, str]:
        """Mescla PDFs ordenados por nome. Retorna (bytes_merged, nome_base)."""
        import io as _io
        from pypdf import PdfWriter, PdfReader

        ordenados = sorted(caminhos, key=lambda p: os.path.basename(p).lower())
        writer = PdfWriter()
        for path in ordenados:
            with open(path, "rb") as f:
                reader = PdfReader(f)
                for pag in reader.pages:
                    writer.add_page(pag)
        buf = _io.BytesIO()
        writer.write(buf)
        nome_base = os.path.splitext(os.path.basename(ordenados[0]))[0]
        return buf.getvalue(), nome_base

    def _dividir_e_enviar_drive(pdf_bytes: bytes, internacoes: list,
                                 nome_base: str, on_progress=None) -> dict:
        """Divide PDF mesclado por internacao e faz upload no Drive.

        Usa a Claudia para mapear paginas -> internacao por data/hospital.
        Retorna dict {(hospital, data_entrada): drive_file_id}.
        """
        import io as _io
        from pypdf import PdfWriter, PdfReader

        def _prog(msg):
            if on_progress: on_progress(msg)

        # ── descobrir quais paginas pertencem a cada internacao ──────
        _prog("Mapeando paginas por internacao...")
        mapa = {}   # {idx_internacao: [paginas]}
        try:
            from extratores.extrator_prontuario import _pdf_para_imagens_b64, _chamar_visao_generica

            # monta descricao das internacoes para o prompt
            descricoes = []
            for i, inter in enumerate(internacoes):
                d = inter.get("data_entrada") or "?"
                h = inter.get("hospital") or "?"
                descricoes.append(f"{i}: {h} entrada={d}")
            desc_txt = "\n".join(descricoes)

            prompt_mapa = f"""
Voce esta analisando paginas de um prontuario hospitalar que contem {len(internacoes)} internacao(oes):
{desc_txt}

Para cada pagina visivel, indique a qual internacao ela pertence pelo indice (0, 1, 2...).
Se uma pagina pertence a mais de uma internacao, use a mais relevante.
Se nao pertence a nenhuma, use -1.

Retorne SOMENTE JSON valido:
{{"paginas": [indice_internacao_da_pag_1, indice_internacao_da_pag_2, ...]}}

O array deve ter exatamente uma entrada por pagina, na ordem das paginas.
NUNCA invente — se nao souber, use -1.
"""
            imgs = _pdf_para_imagens_b64(pdf_bytes)
            total_pags = len(imgs)

            # processa em lotes de 6 para mapear paginas
            LOTE = 6
            paginas_mapa = []
            n_lotes = (total_pags + LOTE - 1) // LOTE
            for li in range(n_lotes):
                ini = li * LOTE
                fim = min(ini + LOTE, total_pags)
                _prog(f"Mapeando paginas {ini+1}-{fim}/{total_pags}...")
                try:
                    r = _chamar_visao_generica(imgs[ini:fim], prompt_mapa)
                    paginas_mapa.extend(r.get("paginas") or [-1] * (fim - ini))
                except Exception:
                    paginas_mapa.extend([-1] * (fim - ini))

            # agrupa indices de pagina por internacao
            reader = PdfReader(_io.BytesIO(pdf_bytes))
            for idx_inter in range(len(internacoes)):
                mapa[idx_inter] = []
            for pag_idx, inter_idx in enumerate(paginas_mapa):
                if 0 <= inter_idx < len(internacoes):
                    mapa[inter_idx].append(pag_idx)

        except Exception as ex:
            _prog(f"Mapeamento falhou ({ex}) — usando PDF completo para cada internacao.")
            # fallback: todas as paginas para todas as internacoes
            reader = PdfReader(_io.BytesIO(pdf_bytes))
            for idx_inter in range(len(internacoes)):
                mapa[idx_inter] = list(range(len(reader.pages)))

        # ── upload de cada sub-PDF ───────────────────────────────────
        resultado = {}
        try:
            from utils.drive_sync import _INTERNACOES_PDF_ID, upload_foto as _upload_foto, _get_creds
            creds     = _get_creds()
            pasta_int = _INTERNACOES_PDF_ID
        except Exception as ex:
            import traceback
            log.warning("[DRIVE] credenciais: %s\n%s", ex, traceback.format_exc())
            _prog(f"Drive indisponivel: {ex}")
            return resultado

        pasta_temp = os.path.join(os.path.dirname(__file__), "..", "temp")
        os.makedirs(pasta_temp, exist_ok=True)

        for idx_inter, inter in enumerate(internacoes):
            pags_inter = mapa.get(idx_inter) or list(range(len(reader.pages)))
            if not pags_inter:
                continue

            import unicodedata, re as _re
            _hosp_raw = (inter.get("hospital") or "internacao")[:40]
            _hosp_ascii = unicodedata.normalize("NFKD", _hosp_raw).encode("ascii", "ignore").decode("ascii")
            hosp  = _re.sub(r"[^\w\-]", "_", _hosp_ascii)[:25].strip("_")
            d_ent = (inter.get("data_entrada") or "sem_data").replace("-", "")
            nome_pdf = f"INT_{d_ent}_{hosp}.pdf"

            _prog(f"Enviando PDF da internacao {idx_inter+1}/{len(internacoes)}...")

            writer = PdfWriter()
            for p in pags_inter:
                if p < len(reader.pages):
                    writer.add_page(reader.pages[p])

            tmp_path = os.path.join(pasta_temp, nome_pdf)
            try:
                buf2 = _io.BytesIO()
                writer.write(buf2)
                with open(tmp_path, "wb") as f:
                    f.write(buf2.getvalue())
                drive_id = _upload_foto(tmp_path, nome_pdf, pasta_int, creds)
                from dados.model_prontuario import normalizar_data as _nd
                chave = (
                    (inter.get("hospital") or "").strip(),
                    _nd((inter.get("data_entrada") or "").strip()),
                )
                resultado[chave] = drive_id
                _prog(f"Drive OK: {nome_pdf}")
            except Exception as ex:
                import traceback
                _err2 = traceback.format_exc()
                log.warning("[DRIVE] upload %s: %s", nome_pdf, _err2)
                _prog(f"Upload falhou ({nome_pdf}): {ex}")
                try:
                    _log_path2 = os.path.join(os.path.dirname(__file__), "..", "logs", "drive_upload_erro.txt")
                    with open(_log_path2, "a", encoding="utf-8") as _lf2:
                        _lf2.write(f"\n--- {nome_pdf} ---\n{_err2}\n")
                except Exception:
                    pass
            finally:
                try: os.remove(tmp_path)
                except Exception: pass

        return resultado

    def _importar_pdf():
        """
        FASE 1 — Puramente local, sem rede.
        Seleciona PDF(s), mescla se necessario, quebra em paginas,
        salva JPEG+PDF de cada pagina em temp/ingestao/.
        Ao final mostra resumo e oferece continuar (fase 2).
        """
        def _on_picked(e: ft.FilePickerResultEvent):
            if not e.files:
                return
            caminhos = [f.path for f in e.files if f.path]
            if not caminhos:
                return

            n = len(caminhos)
            prog_txt = ft.Text(
                f"Preparando {n} arquivo(s)..." if n > 1 else "Separando paginas...",
                size=12, color=SEC, text_align=ft.TextAlign.CENTER,
            )
            _mostrar_overlay(ft.Column([
                ft.ProgressRing(width=32, height=32, stroke_width=3, color=AZUL),
                ft.Container(height=8),
                ft.Text("Fase 1 — Separando paginas", size=13, color=TXT,
                        weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
                ft.Text("Sem rede — apenas leitura local do PDF",
                        size=11, color=MUT, text_align=ft.TextAlign.CENTER),
                ft.Container(height=4),
                prog_txt,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True, spacing=4))

            def _prog(msg):
                prog_txt.value = msg
                try: page.update()
                except Exception: pass

            def _fase1():
                try:
                    from utils.processador_pdf import separar_pdf
                    from dados.model_prontuario import DB_PATH

                    # mesclar se multiplos arquivos
                    if len(caminhos) > 1:
                        _prog(f"Mesclando {len(caminhos)} PDFs...")
                        pdf_bytes, nome_base = _mesclar_pdfs(caminhos)
                        arquivo_local = ""
                    else:
                        arquivo_local = caminhos[0]
                        nome_base = os.path.splitext(os.path.basename(arquivo_local))[0]
                        with open(arquivo_local, "rb") as f:
                            pdf_bytes = f.read()

                    _prog("Separando paginas...")
                    # internacao_ids=[0] temporario — sera definido na fase 2
                    r = separar_pdf(
                        pdf_bytes if not arquivo_local else arquivo_local,
                        internacao_ids=[0],
                        db_path=DB_PATH,
                        on_progress=lambda p, t, m: _prog(f"Pag {p}/{t}"),
                    )

                    imp_id = r["importacao_id"]
                    total  = r["total"]

                    # verificar que os arquivos foram salvos
                    import sqlite3 as _sq
                    with _sq.connect(DB_PATH) as _c:
                        salvos = _c.execute(
                            "SELECT COUNT(*) FROM pdf_paginas WHERE importacao_id=? AND jpeg_local IS NOT NULL",
                            (imp_id,)
                        ).fetchone()[0]

                    _fechar_overlay()
                    _mostrar_resultado_fase1(imp_id, total, salvos, nome_base, arquivo_local)

                except Exception as ex:
                    import traceback
                    log.error("[FASE1] %s\n%s", ex, traceback.format_exc())
                    _fechar_overlay()
                    btn_fechar = ft.Container(
                        content=ft.Text("Fechar", size=13, color=SEC),
                        border_radius=8, ink=True,
                        padding=ft.padding.symmetric(horizontal=16, vertical=10),
                        border=ft.border.all(1, BD),
                    )
                    btn_fechar.on_click = lambda _: _fechar_overlay()
                    _mostrar_overlay(ft.Column([
                        ft.Icon("error_outline_rounded", size=36, color=VERM),
                        ft.Container(height=6),
                        ft.Text("Erro na separacao", size=14, color=TXT,
                                weight=ft.FontWeight.W_700),
                        ft.Text(str(ex)[:250], size=12, color=SEC,
                                text_align=ft.TextAlign.CENTER),
                        ft.Container(height=12),
                        btn_fechar,
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                       tight=True, spacing=4))

            threading.Thread(target=_fase1, daemon=True).start()

        _picker.on_result = _on_picked
        _picker.pick_files(allowed_extensions=["pdf"], allow_multiple=True)

    def _mostrar_resultado_fase1(imp_id: int, total: int, salvos: int,
                                  nome_base: str, arquivo_local: str):
        """Exibe resumo da fase 1 e botao para continuar para fase 2."""
        import sqlite3 as _sq
        from dados.model_prontuario import DB_PATH

        # verificar pasta onde foram salvos
        with _sq.connect(DB_PATH) as _c:
            row = _c.execute(
                "SELECT jpeg_local FROM pdf_paginas WHERE importacao_id=? LIMIT 1",
                (imp_id,)
            ).fetchone()
        pasta = os.path.dirname(row[0]) if row and row[0] else "?"

        btn_continuar = ft.Container(
            content=ft.Row([
                ft.Icon("play_arrow_rounded", size=15, color=BG),
                ft.Text("Continuar — Fase 2", size=12, color=BG,
                        weight=ft.FontWeight.W_600),
            ], spacing=4, tight=True),
            bgcolor=VERD, border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
        )
        btn_fechar = ft.Container(
            content=ft.Text("Fechar", size=12, color=SEC),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.all(1, BD),
        )

        def _ao_continuar(_):
            _fechar_overlay()
            _iniciar_fase2(imp_id)

        btn_continuar.on_click = _ao_continuar
        btn_fechar.on_click    = lambda _: _fechar_overlay()

        _mostrar_overlay(ft.Column([
            ft.Icon("check_circle_outline_rounded", size=36, color=VERD),
            ft.Container(height=6),
            ft.Text("Fase 1 concluida", size=14, color=TXT,
                    weight=ft.FontWeight.W_700),
            ft.Container(height=4),
            ft.Text(f"{salvos}/{total} paginas salvas localmente",
                    size=13, color=TXT, text_align=ft.TextAlign.CENTER),
            ft.Text(nome_base[:40], size=11, color=SEC,
                    text_align=ft.TextAlign.CENTER),
            ft.Container(height=2),
            ft.Text(pasta[:50], size=10, color=MUT,
                    text_align=ft.TextAlign.CENTER),
            ft.Container(height=14),
            ft.Text("Proxima etapa: Claudia identifica internacoes e classifica paginas",
                    size=11, color=MUT, text_align=ft.TextAlign.CENTER),
            ft.Container(height=10),
            ft.Row([btn_fechar, btn_continuar], spacing=8,
                   alignment=ft.MainAxisAlignment.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           tight=True, spacing=4, width=320))

    def _iniciar_fase2(imp_id: int):
        """Fase 2: Claude identifica internacoes + classifica + grava cada pagina."""
        import sqlite3 as _sq
        from dados.model_prontuario import DB_PATH

        with _sq.connect(DB_PATH) as _c:
            info = _c.execute(
                "SELECT nome_arquivo, arquivo_local, total_paginas FROM importacoes_pdf WHERE id=?",
                (imp_id,)
            ).fetchone()
            pag_rows = _c.execute(
                "SELECT id, jpeg_local, pagina_num FROM pdf_paginas WHERE importacao_id=? ORDER BY pagina_num",
                (imp_id,)
            ).fetchall()

        nome_arq   = info[0] if info else "?"
        arq_local  = info[1] if info else ""
        total_pags = info[2] if info else len(pag_rows)

        prog_txt = ft.Text("Iniciando...", size=12, color=SEC,
                           text_align=ft.TextAlign.CENTER)
        _mostrar_overlay(ft.Column([
            ft.ProgressRing(width=32, height=32, stroke_width=3, color=ROXO),
            ft.Container(height=8),
            ft.Text("Fase 2 — Identificando internacoes", size=13, color=TXT,
                    weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
            ft.Text(nome_arq[:36], size=11, color=MUT,
                    text_align=ft.TextAlign.CENTER),
            ft.Container(height=4),
            prog_txt,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True, spacing=4))

        def _prog(msg):
            prog_txt.value = msg
            try: page.update()
            except Exception: pass

        def _run():
            try:
                from utils.claudia_engine import get_client
                from dados.model_prontuario import DB_PATH
                import sqlite3 as _sq, shutil, base64 as _b64, json as _json

                client = get_client()

                pasta_base = os.path.dirname(pag_rows[0][1]) if pag_rows else ""
                datas_paginas = {}   # {pagina_num: "YYYY-MM-DD" ou None}

                PROMPT_DATA = """Pagina de prontuario hospitalar brasileiro.
Extraia as informacoes abaixo.
- plano: muitos hospitais pertencem ao mesmo grupo; retorne o nome COMERCIAL do plano (ex: "MedSenior"), nao o CNPJ nem razao social.
- resumo: identifique o tipo e conteudo principal da pagina em ate 8 palavras (ex: "Prescricao medica - antibiotico e analgesia", "Resultado hemograma completo", "Evolucao enfermagem turno manha", "ECG repouso", "Alta hospitalar"). Se for pagina administrativa sem valor clinico, diga "Documento administrativo".
Retorne SOMENTE JSON:
{"data": "YYYY-MM-DD ou null", "hospital": "nome ou null", "plano": "nome comercial ou null", "resumo": "texto curto ou null"}"""

                todos = list(pag_rows)  # [(id, jpeg_local, pagina_num)]
                sem_data_dir = os.path.join(pasta_base, "sem_data")
                _hospitais = []   # coleta por pagina para votar no mais frequente
                _planos    = []

                # buscar pdf_local de cada pagina para guardar em prontuario_paginas
                with _sq.connect(DB_PATH) as _c:
                    pdf_local_map = {
                        r[0]: r[1]
                        for r in _c.execute(
                            "SELECT id, pdf_local FROM pdf_paginas WHERE importacao_id=?",
                            (imp_id,)
                        ).fetchall()
                    }

                # criar registro pai em prontuarios (ou reusar se ja existe)
                with _sq.connect(DB_PATH) as _c:
                    imp_row = _c.execute(
                        "SELECT nome_arquivo, hash_pdf, total_paginas FROM importacoes_pdf WHERE id=?",
                        (imp_id,)
                    ).fetchone()
                    pron_row = _c.execute(
                        "SELECT id FROM prontuarios WHERE importacao_id=?", (imp_id,)
                    ).fetchone()
                    if pron_row:
                        pron_id = pron_row[0]
                        # mover JEPGs de subpastas de volta para a raiz antes de reprocessar
                        pags_ant = _c.execute(
                            "SELECT jpeg_local FROM prontuario_paginas WHERE prontuario_id=? AND jpeg_local IS NOT NULL",
                            (pron_id,)
                        ).fetchall()
                        for (jpeg_ant,) in pags_ant:
                            if jpeg_ant and os.path.exists(jpeg_ant):
                                dest_raiz = os.path.join(pasta_base, os.path.basename(jpeg_ant))
                                if jpeg_ant != dest_raiz:
                                    shutil.move(jpeg_ant, dest_raiz)
                        # limpar paginas anteriores do banco
                        _c.execute("DELETE FROM prontuario_paginas WHERE prontuario_id=?", (pron_id,))
                    else:
                        cur = _c.cursor()
                        cur.execute(
                            """INSERT INTO prontuarios (importacao_id, nome_arquivo, hash_pdf, total_paginas)
                               VALUES (?,?,?,?)""",
                            (imp_id,
                             imp_row[0] if imp_row else None,
                             imp_row[1] if imp_row else None,
                             imp_row[2] if imp_row else len(todos))
                        )
                        pron_id = cur.lastrowid

                # resetar jpeg_local e dados_json em pdf_paginas para estado pós-fase1
                with _sq.connect(DB_PATH) as _c:
                    for pid, jpeg_local, num in todos:
                        jpeg_raiz = os.path.join(pasta_base, os.path.basename(jpeg_local))
                        _c.execute(
                            "UPDATE pdf_paginas SET jpeg_local=?, dados_json=NULL WHERE id=?",
                            (jpeg_raiz, pid)
                        )
                # atualizar todos para usar caminhos na raiz
                todos = [
                    (pid, os.path.join(pasta_base, os.path.basename(jl)), num)
                    for pid, jl, num in todos
                ]

                now = datetime.datetime.now().isoformat(timespec="seconds")

                erros_fatais = 0

                for pid, jpeg_local, num in todos:
                    _prog(f"Pag {num}/{total_pags} — identificando data...")
                    data = resumo = hosp = plan = None
                    try:
                        with open(jpeg_local, "rb") as f:
                            img_b64 = _b64.b64encode(f.read()).decode()
                        resp = client.messages.create(
                            model="claude-haiku-4-5-20251001",
                            max_tokens=200,
                            messages=[{"role": "user", "content": [
                                {"type": "image", "source": {
                                    "type": "base64", "media_type": "image/jpeg",
                                    "data": img_b64}},
                                {"type": "text", "text": PROMPT_DATA},
                            ]}],
                            timeout=30,
                        )
                        txt = resp.content[0].text.strip()
                        if txt.startswith("```"):
                            txt = txt.split("```")[1].lstrip("json").strip()
                        parsed = _json.loads(txt)
                        data = parsed.get("data")
                        if data and len(data) != 10:
                            data = None
                        hosp   = (parsed.get("hospital") or "").strip() or None
                        plan   = (parsed.get("plano") or "").strip() or None
                        resumo = (parsed.get("resumo") or "").strip() or None
                        if hosp: _hospitais.append(hosp)
                        if plan: _planos.append(plan)
                        erros_fatais = 0
                    except Exception as _ex:
                        log.warning("[FASE2] pag %d: %s", num, _ex)
                        _ex_str = str(_ex).lower()
                        if "credit" in _ex_str or "401" in _ex_str or "403" in _ex_str or "balance" in _ex_str:
                            _fechar_overlay()
                            _snack(f"Erro API: {str(_ex)[:120]}", VERM)
                            return
                        erros_fatais += 1
                        if erros_fatais >= 5:
                            _fechar_overlay()
                            _snack(f"Muitos erros consecutivos: {str(_ex)[:100]}", VERM)
                            return
                        data = resumo = None

                    datas_paginas[num] = data

                    # mover JPEG para subpasta imediatamente
                    if data:
                        dest_dir = os.path.join(pasta_base, data)
                        _prog(f"Pag {num}/{total_pags} → {data}/")
                    else:
                        dest_dir = sem_data_dir
                        _prog(f"Pag {num}/{total_pags} → sem_data/")
                    os.makedirs(dest_dir, exist_ok=True)

                    nome_arq_pag = os.path.basename(jpeg_local)
                    dest_jpeg = os.path.join(dest_dir, nome_arq_pag)
                    if jpeg_local != dest_jpeg:
                        shutil.move(jpeg_local, dest_jpeg)

                    pdf_pag = pdf_local_map.get(pid)

                    # gravar no banco imediatamente: pdf_paginas + prontuario_paginas
                    with _sq.connect(DB_PATH) as _c:
                        _c.execute(
                            "UPDATE pdf_paginas SET jpeg_local=?, dados_json=json_patch(COALESCE(dados_json,'{}'), ?) WHERE id=?",
                            (dest_jpeg, _json.dumps({"data_pagina": data}), pid)
                        )
                        _c.execute(
                            """INSERT INTO prontuario_paginas
                               (prontuario_id, pdf_pagina_id, pagina_num, data_pagina, resumo, dados_json, pdf_local, jpeg_local)
                               VALUES (?,?,?,?,?,?,?,?)""",
                            (pron_id, pid, num, data, resumo,
                             _json.dumps(parsed) if parsed else None,
                             pdf_pag, dest_jpeg)
                        )

                # consolidar hospital e plano — valor mais frequente entre as paginas
                def _mais_frequente(lst):
                    if not lst: return None
                    return max(set(lst), key=lst.count)

                hospital_final = _mais_frequente(_hospitais)
                plano_final    = _mais_frequente(_planos)

                # atualizar prontuario pai com datas, hospital e plano
                datas_validas = sorted(d for d in datas_paginas.values() if d)
                with _sq.connect(DB_PATH) as _c:
                    _c.execute(
                        """UPDATE prontuarios
                           SET data_inicio=?, data_fim=?, total_paginas=?,
                               hospital=?, plano=?
                           WHERE id=?""",
                        (datas_validas[0] if datas_validas else None,
                         datas_validas[-1] if datas_validas else None,
                         len(todos),
                         hospital_final, plano_final,
                         pron_id)
                    )
                    _c.execute(
                        "UPDATE importacoes_pdf SET fase_atual=2, atualizado_em=? WHERE id=?",
                        (now, imp_id)
                    )

                # ── resumo por data ────────────────────────────────────────────
                contagem_datas = {}
                for num, data in datas_paginas.items():
                    chave = data if (data and len(data) == 10) else "sem_data"
                    contagem_datas[chave] = contagem_datas.get(chave, 0) + 1

                _fechar_overlay()
                _mostrar_resultado_fase2(imp_id, pasta_base, contagem_datas)

            except Exception as ex:
                import traceback
                log.error("[FASE2-ID] %s\n%s", ex, traceback.format_exc())
                _fechar_overlay()
                _snack(str(ex)[:200], VERM)

        threading.Thread(target=_run, daemon=True).start()

    def _mostrar_resultado_fase2(imp_id: int, pasta_base: str, contagem_datas: dict):
        """Exibe resumo da fase 2: datas encontradas e paginas por data."""
        datas_ordenadas = sorted(
            [(d, n) for d, n in contagem_datas.items() if d != "sem_data"]
        )
        sem_data = contagem_datas.get("sem_data", 0)
        total = sum(contagem_datas.values())

        linhas = []
        for data, n in datas_ordenadas:
            linhas.append(ft.Row([
                ft.Icon("folder_rounded", size=14, color=AZUL),
                ft.Text(data, size=12, color=TXT, expand=True),
                ft.Text(f"{n} pag{'s' if n > 1 else ''}", size=11, color=SEC),
            ], spacing=6))
        if sem_data:
            linhas.append(ft.Row([
                ft.Icon("help_outline_rounded", size=14, color=MUT),
                ft.Text("sem data", size=12, color=MUT, expand=True),
                ft.Text(f"{sem_data} pags", size=11, color=MUT),
            ], spacing=6))

        btn_fechar = ft.Container(
            content=ft.Text("Fechar", size=12, color=SEC),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.all(1, BD),
        )
        btn_continuar = ft.Container(
            content=ft.Row([
                ft.Icon("play_arrow_rounded", size=15, color=BG),
                ft.Text("Continuar — Fase 3", size=12, color=BG,
                        weight=ft.FontWeight.W_600),
            ], spacing=4, tight=True),
            bgcolor=VERD, border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
        )

        btn_fechar.on_click    = lambda _: _fechar_overlay()
        btn_continuar.on_click = lambda _: (_fechar_overlay(), _iniciar_fase3(imp_id))

        _mostrar_overlay(ft.Column([
            ft.Icon("event_available_rounded", size=32, color=VERD),
            ft.Container(height=6),
            ft.Text("Fase 2 concluida", size=14, color=TXT,
                    weight=ft.FontWeight.W_700),
            ft.Text(f"{total} paginas organizadas por data",
                    size=12, color=SEC, text_align=ft.TextAlign.CENTER),
            ft.Container(height=8),
            ft.Column(linhas, spacing=4, scroll=ft.ScrollMode.AUTO,
                      height=min(len(linhas) * 28, 200)),
            ft.Container(height=4),
            ft.Text(pasta_base[:50], size=10, color=MUT,
                    text_align=ft.TextAlign.CENTER),
            ft.Container(height=12),
            ft.Row([btn_fechar, btn_continuar], spacing=8,
                   alignment=ft.MainAxisAlignment.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           tight=True, spacing=4, width=300))

    def _iniciar_fase3(imp_id: int):
        """Fase 3: insere uma linha em linha_do_tempo para cada data encontrada."""
        import sqlite3 as _sq
        from dados.model_prontuario import DB_PATH

        prog_txt = ft.Text("Criando linha do tempo...", size=12, color=SEC,
                           text_align=ft.TextAlign.CENTER)
        _mostrar_overlay(ft.Column([
            ft.ProgressRing(width=32, height=32, stroke_width=3, color=AZUL),
            ft.Container(height=8),
            ft.Text("Fase 3 — Linha do tempo", size=13, color=TXT,
                    weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
            ft.Container(height=4),
            prog_txt,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True, spacing=4))

        def _prog(msg):
            prog_txt.value = msg
            try: page.update()
            except Exception: pass

        def _run():
            try:
                import os as _os, json as _json

                _prog("Lendo datas do banco...")
                with _sq.connect(DB_PATH) as _c:
                    # buscar todas as datas distintas desta importacao
                    rows = _c.execute("""
                        SELECT dados_json, pagina_num
                        FROM pdf_paginas
                        WHERE importacao_id=?
                          AND dados_json IS NOT NULL
                        ORDER BY pagina_num
                    """, (imp_id,)).fetchall()

                    imp_row = _c.execute(
                        "SELECT arquivo_local FROM importacoes_pdf WHERE id=?",
                        (imp_id,)
                    ).fetchone()
                    arq_local = imp_row[0] if imp_row else ""

                # agrupar paginas por data
                datas = {}  # {data: contagem}
                for dados_json, num in rows:
                    try:
                        d = _json.loads(dados_json).get("data_pagina")
                    except Exception:
                        d = None
                    chave = d if (d and len(d) == 10) else None
                    if chave:
                        datas[chave] = datas.get(chave, 0) + 1

                if not datas:
                    _fechar_overlay()
                    _snack("Nenhuma data encontrada para criar linha do tempo.", AMAR)
                    return

                # pasta base da importacao
                pasta_imp = _os.path.join(
                    _os.path.dirname(_os.path.abspath(__file__)),
                    "..", "temp", "ingestao", str(imp_id)
                )

                _prog(f"Inserindo {len(datas)} data(s) na linha do tempo...")
                now = datetime.datetime.now().isoformat(timespec="seconds")

                with _sq.connect(DB_PATH) as _c:
                    # limpar entradas anteriores desta importacao
                    _c.execute(
                        "DELETE FROM linha_do_tempo WHERE importacao_id=?", (imp_id,)
                    )
                    for data_doc in sorted(datas.keys()):
                        pasta_data = _os.path.join(pasta_imp, data_doc)
                        total_pags = datas[data_doc]
                        _c.execute("""
                            INSERT INTO linha_do_tempo
                            (importacao_id, data_doc, pasta_local, total_paginas, criado_em)
                            VALUES (?,?,?,?,?)
                        """, (imp_id, data_doc, pasta_data, total_pags, now))

                    _c.execute(
                        "UPDATE importacoes_pdf SET fase_atual=3, atualizado_em=? WHERE id=?",
                        (now, imp_id)
                    )

                # ler o que foi inserido para mostrar
                with _sq.connect(DB_PATH) as _c:
                    linhas_ldt = _c.execute("""
                        SELECT data_doc, total_paginas
                        FROM linha_do_tempo
                        WHERE importacao_id=?
                        ORDER BY data_doc
                    """, (imp_id,)).fetchall()

                _fechar_overlay()
                _mostrar_resultado_fase3(imp_id, linhas_ldt)

            except Exception as ex:
                import traceback
                log.error("[FASE3] %s\n%s", ex, traceback.format_exc())
                _fechar_overlay()
                _snack(str(ex)[:200], VERM)

        threading.Thread(target=_run, daemon=True).start()

    def _mostrar_resultado_fase3(imp_id: int, linhas: list):
        """Exibe as linhas criadas na linha_do_tempo."""
        itens = []
        for data_doc, total_pags in linhas:
            itens.append(ft.Row([
                ft.Icon("calendar_today_rounded", size=13, color=ROXO),
                ft.Text(data_doc, size=12, color=TXT, expand=True),
                ft.Text(f"{total_pags} pag{'s' if total_pags > 1 else ''}",
                        size=11, color=SEC),
            ], spacing=6))

        btn_fechar = ft.Container(
            content=ft.Text("Fechar", size=12, color=SEC),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.all(1, BD),
        )
        btn_fechar.on_click = lambda _: _fechar_overlay()

        _mostrar_overlay(ft.Column([
            ft.Icon("timeline_rounded", size=32, color=ROXO),
            ft.Container(height=6),
            ft.Text("Fase 3 concluida", size=14, color=TXT,
                    weight=ft.FontWeight.W_700),
            ft.Text(f"{len(linhas)} data(s) na linha do tempo",
                    size=12, color=SEC, text_align=ft.TextAlign.CENTER),
            ft.Container(height=8),
            ft.Column(itens, spacing=4, scroll=ft.ScrollMode.AUTO,
                      height=min(len(itens) * 28, 220)),
            ft.Container(height=12),
            btn_fechar,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           tight=True, spacing=4, width=280))

    # ── Revisao pos-extracao (Fase 1: internacoes) ─────────────────

    def _detectar_mesmo_evento(internacoes: list) -> list[tuple[int, int]]:
        """Retorna pares (i, j) da lista que parecem ser o mesmo evento hospitalar.

        Regras (qualquer uma satisfeita + mesma localidade):
          1. data_entrada de ambos dentro de ±2 dias entre si
          2. Um sem entrada e com saída dentro de ±2 dias da entrada do outro
             (caso PS → UTI onde o doc de alta não tem data de entrada)
        """
        pares = []
        n = len(internacoes)

        def _datas_proximas(d1, d2, max_dias=2):
            if d1 and d2:
                return abs((d1 - d2).days) <= max_dias
            return False

        def _mesma_localidade(a, b):
            import unicodedata as _ud
            def _norm(s):
                s = _ud.normalize("NFKD", (s or "")).encode("ascii", "ignore").decode()
                return s.strip().lower()
            cid_a = _norm(a.get("cidade") or "")
            cid_b = _norm(b.get("cidade") or "")
            uf_a  = (a.get("uf") or "").strip().upper()
            uf_b  = (b.get("uf") or "").strip().upper()
            return (cid_a and cid_b and cid_a == cid_b) or (uf_a and uf_b and uf_a == uf_b)

        for i in range(n):
            for j in range(i + 1, n):
                a, b = internacoes[i], internacoes[j]
                ent_a = _flex_parse(a.get("data_entrada") or "")
                ent_b = _flex_parse(b.get("data_entrada") or "")
                sai_a = _flex_parse(a.get("data_saida") or "")
                sai_b = _flex_parse(b.get("data_saida") or "")

                candidato = False
                # regra 1: ambos têm entrada próxima
                if _datas_proximas(ent_a, ent_b):
                    candidato = True
                # regra 2: b sem entrada, saída de b próxima da entrada de a
                elif ent_b is None and sai_b and _datas_proximas(ent_a, sai_b):
                    candidato = True
                # regra 2 inversa: a sem entrada, saída de a próxima da entrada de b
                elif ent_a is None and sai_a and _datas_proximas(sai_a, ent_b):
                    candidato = True

                if candidato and _mesma_localidade(a, b):
                    pares.append((i, j))

        return pares

    def _mesclar_dois(a: dict, b: dict) -> dict:
        """Mescla dois dicts de internacao: prioriza campos não-nulos; usa data_saida mais tardia."""
        import datetime as _dt
        merged = dict(a)
        for k, v in b.items():
            if not merged.get(k) and v:
                merged[k] = v
        # data_saida: usar a mais tardia
        ds_a = _flex_parse(a.get("data_saida") or "")
        ds_b = _flex_parse(b.get("data_saida") or "")
        if ds_a and ds_b:
            merged["data_saida"] = max(ds_a, ds_b).strftime("%Y-%m-%d")
        elif ds_b:
            merged["data_saida"] = b["data_saida"]
        # hospital: manter o mais completo (mais longo)
        hosp_a = (a.get("hospital") or "")
        hosp_b = (b.get("hospital") or "")
        merged["hospital"] = hosp_a if len(hosp_a) >= len(hosp_b) else hosp_b
        # drive_file_id: principal = primeiro
        drv_a = (a.get("drive_file_id") or "")
        drv_b = (b.get("drive_file_id") or "")
        if drv_a and drv_b and drv_a != drv_b:
            merged["drive_file_id"] = drv_a
            merged["drive_file_id_complemento"] = drv_b
        # modalidade: se um é ps e outro é internacao → ps_internacao
        mod_a = (a.get("modalidade") or "")
        mod_b = (b.get("modalidade") or "")
        mods  = {mod_a, mod_b} - {""}
        if "ps" in mods and "internacao" in mods:
            merged["modalidade"] = "ps_internacao"
        elif mods:
            merged["modalidade"] = mods.pop()
        else:
            merged["modalidade"] = "ps_internacao"  # fusão sem info = assumir ps→internacao
        return merged

    def _revisar_internacoes(resultado: dict, drive_map: dict = None,
                              importacao_id: int = None):
        """Mostra overlay com as internacoes encontradas para o usuario confirmar."""
        internacoes_orig = list(resultado.get("internacoes") or [])
        internacoes      = [dict(i) for i in internacoes_orig]
        pac_nome    = resultado.get("paciente_nome") or ""
        doc_local   = resultado.get("documento_local", "")
        n_pags      = resultado.get("paginas_processadas", 0)
        drive_map   = drive_map or {}
        _imp_id     = importacao_id  # importacao_id da fase 1, se ja foi feita

        # estado mutável da lista (fusões alteram)
        lista_ref   = [internacoes]
        conteudo_ref = [None]  # referência ao Column do overlay para rebuild

        def _chip_info(label, valor, cor=SEC):
            if not valor:
                return None
            return ft.Container(
                content=ft.Row([
                    ft.Text(label + ": ", size=10, color=MUT),
                    ft.Text(str(valor), size=10, color=cor, weight=ft.FontWeight.W_600),
                ], tight=True, spacing=2),
            )

        def _rebuild_revisao():
            internacoes = lista_ref[0]
            pares_fusao = _detectar_mesmo_evento(internacoes)
            indices_em_par = {i for par in pares_fusao for i in par}

            cards = []

            # aviso de fusão no topo
            for (i, j) in pares_fusao:
                a, b = internacoes[i], internacoes[j]
                def _fazer_fusao(e, _i=i, _j=j):
                    lst = lista_ref[0]
                    merged = _mesclar_dois(lst[_i], lst[_j])
                    # remover os dois e inserir o mesclado na posição do primeiro
                    nova = [x for k, x in enumerate(lst) if k not in (_i, _j)]
                    nova.insert(min(_i, _j), merged)
                    lista_ref[0] = nova
                    _rebuild_revisao()

                aviso = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon("merge_rounded", size=14, color=AMAR),
                            ft.Text("Possível mesmo evento", size=12, color=AMAR,
                                    weight=ft.FontWeight.W_700),
                        ], spacing=6, tight=True),
                        ft.Text(
                            f"• {a.get('hospital','?')[:40]}  ({a.get('data_entrada','?')})\n"
                            f"• {b.get('hospital','?')[:40]}  ({b.get('data_entrada','?')})\n"
                            "Mesma data e cidade — podem ser PS + UTI da mesma internação.",
                            size=10, color=SEC),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon("merge_type_rounded", size=12, color=AMAR),
                                ft.Text("Mesclar em 1 internação", size=11,
                                        color=AMAR, weight=ft.FontWeight.W_600),
                            ], spacing=4, tight=True),
                            bgcolor=f"{AMAR}22",
                            border=ft.border.all(1, f"{AMAR}55"),
                            border_radius=6, ink=True,
                            padding=ft.padding.symmetric(horizontal=12, vertical=6),
                            on_click=_fazer_fusao,
                        ),
                    ], spacing=6, tight=True),
                    bgcolor=f"{AMAR}11",
                    border=ft.border.all(1, f"{AMAR}44"),
                    border_radius=8,
                    padding=ft.padding.all(10),
                )
                cards.append(aviso)

            # cards normais
            for idx, inter in enumerate(internacoes):
                em_par = idx in indices_em_par
                cid_e   = (inter.get("cid_entrada") or "")
                cid_d   = (inter.get("cid_entrada_desc") or "")
                cid_txt = cid_e + (" — " + cid_d if cid_d and cid_d != cid_e else "")
                chips = [w for w in [
                    _chip_info("Hospital", inter.get("hospital"), AZUL),
                    _chip_info("Entrada",  _para_display(inter.get("data_entrada"))),
                    _chip_info("Saida",    _para_display(inter.get("data_saida"))),
                    _chip_info("Tipo",     inter.get("tipo")),
                    _chip_info("CID",      cid_txt, AMAR) if cid_txt else None,
                    _chip_info("Medico",   inter.get("medico_nome")),
                ] if w]
                if inter.get("motivo"):
                    chips.append(ft.Text(inter["motivo"], size=10, color=SEC, italic=True))
                borda_cor = f"{AMAR}55" if em_par else f"{AZUL}33"
                bg_cor    = f"{AMAR}0A" if em_par else f"{AZUL}11"
                cards.append(ft.Container(
                    content=ft.Column(
                        chips or [ft.Text("Sem dados", size=10, color=MUT)],
                        spacing=4, tight=True),
                    bgcolor=bg_cor,
                    border=ft.border.all(1, borda_cor),
                    border_radius=8,
                    padding=ft.padding.all(10),
                ))

            n = len(internacoes)
            label_btn = (f"Salvar {n} internação" if n == 1 else f"Salvar {n} internações")
            if n == 0:
                label_btn = "Nenhuma para salvar"

            _cor_btn = VERD if n > 0 else MUT

            def _salvar_tudo(e):
                _fechar_overlay()
                _salvar_internacoes_fase1(lista_ref[0], doc_local, pac_nome, drive_map)

            btn_salvar = ft.Container(
                content=ft.Row([
                    ft.Icon("save_rounded", size=14, color=_cor_btn),
                    ft.Text(label_btn, size=13, color=_cor_btn, weight=ft.FontWeight.W_600),
                ], spacing=6, tight=True),
                bgcolor=f"{_cor_btn}22",
                border=ft.border.all(1, f"{_cor_btn}55"),
                border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
            )
            if n > 0:
                btn_salvar.on_click = _salvar_tudo

            btn_cancelar = ft.Container(
                content=ft.Text("Cancelar", size=13, color=SEC),
                border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                bgcolor=f"{SEC}22",
            )
            btn_cancelar.on_click = lambda _: _fechar_overlay()

            btn_x_rev = ft.Container(
                content=ft.Icon("close_rounded", size=20, color=SEC),
                border_radius=8, ink=True, padding=ft.padding.all(6),
            )
            btn_x_rev.on_click = lambda e: _fechar_overlay()

            cabecalho_rev = ft.Column([
                ft.Row([
                    ft.Icon("local_hospital_rounded", size=16, color=AZUL),
                    ft.Text("Internações encontradas", size=15, color=TXT,
                            weight=ft.FontWeight.W_700, expand=True),
                    btn_x_rev,
                ], spacing=8),
                ft.Text(
                    f"{n_pags} páginas analisadas"
                    + (f"  •  Paciente: {pac_nome}" if pac_nome else "")
                    + (f"  •  {n} internação(ões)"
                       + (f"  •  ⚠ {len(pares_fusao)} possível fusão" if pares_fusao else "")),
                    size=10, color=MUT),
            ], spacing=2, tight=True)

            if conteudo_ref[0] is not None:
                conteudo_ref[0].controls = (
                    [cabecalho_rev, ft.Divider(color=BD2, height=1)]
                    + (cards if cards else [ft.Text(
                        "Nenhuma internação identificada.", size=12, color=MUT,
                        text_align=ft.TextAlign.CENTER)])
                    + [ft.Row([btn_cancelar, btn_salvar], spacing=8,
                               alignment=ft.MainAxisAlignment.CENTER)]
                )
                try: page.update()
                except Exception: pass
            else:
                col = ft.Column(
                    [cabecalho_rev, ft.Divider(color=BD2, height=1)]
                    + (cards if cards else [ft.Text(
                        "Nenhuma internação identificada.", size=12, color=MUT,
                        text_align=ft.TextAlign.CENTER)])
                    + [ft.Row([btn_cancelar, btn_salvar], spacing=8,
                               alignment=ft.MainAxisAlignment.CENTER)],
                    spacing=10, tight=True,
                    scroll=ft.ScrollMode.AUTO,
                    height=480,
                )
                conteudo_ref[0] = col
                _mostrar_overlay(col)

        _rebuild_revisao()
        return

    def _salvar_internacoes_fase1(internacoes: list, doc_local: str,
                                  pac_nome: str, drive_map: dict = None):
        """Salva lista de internacoes extraidas; pula duplicatas."""
        from dados.model_prontuario import buscar_internacao_similar, normalizar_data
        drive_map = drive_map or {}

        salvos = 0
        duplicatas = 0
        ids_salvos = []
        for inter in internacoes:
            hosp  = (inter.get("hospital") or "").strip()
            d_ent = normalizar_data((inter.get("data_entrada") or "").strip())
            if not hosp:
                continue

            similares = []
            if d_ent:
                try:
                    similares = buscar_internacao_similar(
                        hosp, d_ent,
                        cidade=inter.get("cidade") or "",
                        uf=inter.get("uf") or "",
                    )
                except Exception:
                    pass

            # drive_file_id para esta internacao
            chave_drive = (hosp, d_ent)
            drive_id  = drive_map.get(chave_drive)
            log.warning("[DRIVE] busca chave=%s -> drive_id=%s | chaves_map=%s", chave_drive, drive_id, list(drive_map.keys()))
            drive_lnk = (f"https://drive.google.com/file/d/{drive_id}/view"
                         if drive_id else None)

            if similares:
                duplicatas += 1
                ids_salvos.append(similares[0]["id"])
                # atualiza drive_file_id se ainda nao tinha
                if drive_id:
                    try:
                        salvar_internacao(dict(similares[0],
                                              drive_file_id=drive_id,
                                              drive_link=drive_lnk))
                    except Exception:
                        pass
                continue

            cid_e   = (inter.get("cid_entrada") or "")
            cid_d   = (inter.get("cid_entrada_desc") or "")
            cid_txt = cid_e + (" — " + cid_d if cid_d and cid_d != cid_e else "")

            try:
                novo_id = salvar_internacao({
                    "hospital":          hosp,
                    "data_entrada":      d_ent,
                    "data_saida":        normalizar_data(inter.get("data_saida") or ""),
                    "tipo":              inter.get("tipo") or "eletiva",
                    "objetivo":          inter.get("objetivo") or "tratamento",
                    "cidade":            inter.get("cidade") or None,
                    "uf":                (inter.get("uf") or "").upper() or None,
                    "motivo":            inter.get("motivo") or None,
                    "cid_entrada":       cid_txt or None,
                    "diagnostico_saida": inter.get("diagnostico_saida") or None,
                    "cid_saida":         inter.get("cid_saida") or None,
                    "observacoes":       inter.get("observacoes") or None,
                    "documento_local":   doc_local or None,
                    "drive_file_id":     drive_id,
                    "drive_link":        drive_lnk,
                })
                salvos += 1
                ids_salvos.append(novo_id)
            except Exception as ex:
                log.warning("[IMPORTAR] erro ao salvar internacao '%s': %s", hosp, ex)

        _internacoes[0] = listar_internacoes()
        _rebuild_lista()

        if duplicatas:
            msg = f"{salvos} salva(s), {duplicatas} duplicata(s) ignorada(s)."
        else:
            msg = f"{salvos} internacao(oes) salva(s)."
        _snack(msg, VERD if salvos else AMAR)

        # Se fase 1 ja foi feita (importacao_id existe), pular direto para classificar
        # Se nao, oferecer fase 2 somente se o PDF existe localmente
        if _imp_id and ids_salvos:
            _oferecer_fase2(doc_local, ids_salvos, importacao_id=_imp_id)
        elif doc_local and os.path.exists(doc_local) and ids_salvos:
            _oferecer_fase2(doc_local, ids_salvos)

    def _oferecer_fase2(doc_local: str, internacao_ids: list, importacao_id: int = None):
        """
        Classifica e grava paginas (fase 2), depois sobe Drive (fase 3).
        Se importacao_id for passado, a fase 1 (separar local) ja foi feita.
        Caso contrario, faz separar_pdf primeiro.
        """
        _mapa_ids = {i["id"]: i for i in _internacoes[0] if i["id"] in internacao_ids}

        prog_txt = ft.Text("Iniciando...", size=12, color=SEC,
                           text_align=ft.TextAlign.CENTER)
        _mostrar_overlay(ft.Column([
            ft.ProgressRing(width=32, height=32, stroke_width=3, color=ROXO),
            ft.Container(height=8),
            ft.Text("Processando prontuario", size=13, color=TXT,
                    weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
            ft.Text("Separando paginas...", size=11, color=MUT,
                    text_align=ft.TextAlign.CENTER),
            ft.Container(height=4),
            prog_txt,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True, spacing=4))

        def _prog(msg):
            prog_txt.value = msg
            try: page.update()
            except Exception: pass

        def _run():
            try:
                from utils.processador_pdf import (
                    separar_pdf, enviar_drive,
                    classificar_pagina, gravar_pagina,
                )
                from utils.drive_sync import _get_creds
                from dados.model_prontuario import DB_PATH
                import sqlite3 as _sq

                total_ga = total_gb = total_gc = total_erros = 0

                if importacao_id:
                    # ── fase 1 ja foi feita — apenas reatribuir internacao_ids ────
                    # atualizar internacao_id nas paginas (fase 1 usou 0 provisorio)
                    _prog("Vinculando paginas as internacoes...")
                    import json as _json

                    # se uma internacao: todas as paginas vao para ela
                    if len(internacao_ids) == 1:
                        with _sq.connect(DB_PATH) as _c:
                            _c.execute(
                                "UPDATE pdf_paginas SET internacao_id=? WHERE importacao_id=?",
                                (internacao_ids[0], importacao_id)
                            )
                            _c.execute(
                                "UPDATE importacoes_pdf SET internacao_ids=? WHERE id=?",
                                (_json.dumps(internacao_ids), importacao_id)
                            )
                        imp_ids = [importacao_id]
                    else:
                        # multiplas: mapeamento via Claude Vision usando JEPGs locais
                        with _sq.connect(DB_PATH) as _c:
                            jpeg_rows = _c.execute(
                                "SELECT id, jpeg_local FROM pdf_paginas WHERE importacao_id=? ORDER BY pagina_num",
                                (importacao_id,)
                            ).fetchall()
                        mapa_pags = _mapear_paginas_por_internacao_local(
                            jpeg_rows, _mapa_ids, internacao_ids, _prog
                        )
                        with _sq.connect(DB_PATH) as _c:
                            for iid, pag_ids_list in mapa_pags.items():
                                for pid in pag_ids_list:
                                    _c.execute(
                                        "UPDATE pdf_paginas SET internacao_id=? WHERE id=?",
                                        (iid, pid)
                                    )
                            _c.execute(
                                "UPDATE importacoes_pdf SET internacao_ids=? WHERE id=?",
                                (_json.dumps(internacao_ids), importacao_id)
                            )
                        imp_ids = [importacao_id]
                else:
                    # ── fase 1 nao foi feita — separar agora ─────────────────────
                    with open(doc_local, "rb") as f:
                        pdf_bytes = f.read()

                    if len(internacao_ids) == 1:
                        mapa_pags = {internacao_ids[0]: None}
                    else:
                        mapa_pags = _mapear_paginas_por_internacao(
                            pdf_bytes, _mapa_ids, internacao_ids, _prog
                        )

                    imp_ids = []
                    for idx_intern, iid in enumerate(internacao_ids):
                        pags = mapa_pags.get(iid)
                        if pags is not None and len(pags) == 0:
                            continue
                        _prog(f"Int {idx_intern+1}/{len(internacao_ids)}: separando...")
                        if pags is not None:
                            import io as _io, pypdfium2 as _pdfium
                            doc_orig = _pdfium.PdfDocument(pdf_bytes)
                            novo     = _pdfium.PdfDocument.new()
                            novo.import_pages(doc_orig, pages=pags)
                            buf = _io.BytesIO()
                            novo.save(buf); novo.close(); doc_orig.close()
                            pdf_input = buf.getvalue()
                        else:
                            pdf_input = doc_local
                        r1 = separar_pdf(
                            pdf_input, [iid], DB_PATH,
                            on_progress=lambda p, t, m, _i=iid: _prog(f"Int{_i} sep {p}/{t}"),
                        )
                        imp_ids.append(r1["importacao_id"])

                # ── FASE 2: classificar + gravar (usa JPEG local) ─────────────────
                creds = _get_creds()
                for imp_id in imp_ids:
                    with _sq.connect(DB_PATH) as _c:
                        pag_ids = [r[0] for r in _c.execute(
                            "SELECT id FROM pdf_paginas WHERE importacao_id=? ORDER BY pagina_num",
                            (imp_id,)
                        ).fetchall()]

                    for i, pid in enumerate(pag_ids):
                        try:
                            info  = classificar_pagina(pid, DB_PATH, creds)
                            tipo  = info["tipo"]
                            grupo = info["grupo"]
                            icone = {"A": "🔬", "B": "📋", "C": "🗑"}.get(grupo, "")
                            _prog(f"Pag {i+1}/{len(pag_ids)} {icone} {tipo}")
                            gravar_pagina(pid, DB_PATH, creds)
                            if grupo == "A":   total_ga += 1
                            elif grupo == "B": total_gb += 1
                            else:              total_gc += 1
                        except Exception as ex:
                            log.error("[FASE2] pid=%d: %s", pid, ex)
                            total_erros += 1

                    with _sq.connect(DB_PATH) as _c:
                        _c.execute(
                            "UPDATE importacoes_pdf SET fase_atual=2, atualizado_em=? WHERE id=?",
                            (datetime.datetime.now().isoformat(timespec="seconds"), imp_id)
                        )

                # ── FASE 3: subir Drive (backup/visualizacao) ─────────────────────
                for imp_id in imp_ids:
                    _prog("Enviando paginas ao Drive...")
                    enviar_drive(
                        imp_id, DB_PATH,
                        on_progress=lambda p, t, m: _prog(m),
                        creds=creds,
                    )
                    with _sq.connect(DB_PATH) as _c:
                        _c.execute(
                            "UPDATE importacoes_pdf SET fase_atual=4, atualizado_em=? WHERE id=?",
                            (datetime.datetime.now().isoformat(timespec="seconds"), imp_id)
                        )

                _fechar_overlay()
                partes = []
                if total_ga:     partes.append(f"{total_ga} exame(s)")
                if total_gb:     partes.append(f"{total_gb} dado(s) clinico(s)")
                if total_gc:     partes.append(f"{total_gc} descartado(s)")
                if total_erros:  partes.append(f"{total_erros} erro(s)")
                msg = ("Processado: " + " | ".join(partes)) if partes else "Nenhum dado novo."
                _snack(msg, VERD if (total_ga + total_gb) > 0 else AMAR)
                _internacoes[0] = listar_internacoes()
                _rebuild_lista()

            except Exception as ex:
                import traceback
                log.error("[FASE2] %s\n%s", ex, traceback.format_exc())
                _fechar_overlay()
                _snack(str(ex)[:200], VERM)

        threading.Thread(target=_run, daemon=True).start()

    def _mapear_paginas_por_internacao(
        pdf_bytes: bytes, mapa_ids: dict, internacao_ids: list, on_progress=None
    ) -> dict:
        """
        Usa Claude Vision para descobrir quais paginas pertencem a cada internacao.
        Retorna {internacao_id: [lista de indices 0-based]}.
        """
        import io as _io
        import pypdfium2 as _pdfium

        def _prog(msg):
            if on_progress: on_progress(msg)

        try:
            from extratores.extrator_prontuario import _pdf_para_imagens_b64, _chamar_visao_generica

            descricoes = []
            for i, iid in enumerate(internacao_ids):
                inter = mapa_ids.get(iid, {})
                d = inter.get("data_entrada") or "?"
                h = inter.get("hospital") or "?"
                descricoes.append(f"{i}: {h} entrada={d}")
            desc_txt = "\n".join(descricoes)

            prompt_mapa = f"""Prontuario hospitalar com {len(internacao_ids)} internacao(oes):
{desc_txt}

Para cada pagina indique o indice da internacao (0, 1, ...) ou -1 se nao pertencer a nenhuma.
Retorne SOMENTE JSON: {{"paginas": [indice_pag1, indice_pag2, ...]}}
Array com exatamente uma entrada por pagina na ordem das paginas."""

            imgs = _pdf_para_imagens_b64(pdf_bytes)
            total_pags = len(imgs)
            LOTE = 6
            paginas_mapa = []
            for li in range((total_pags + LOTE - 1) // LOTE):
                ini = li * LOTE
                fim = min(ini + LOTE, total_pags)
                _prog(f"Mapeando paginas {ini+1}-{fim}/{total_pags}...")
                try:
                    r = _chamar_visao_generica(imgs[ini:fim], prompt_mapa)
                    paginas_mapa.extend(r.get("paginas") or [-1] * (fim - ini))
                except Exception:
                    paginas_mapa.extend([-1] * (fim - ini))

        except Exception as ex:
            _prog(f"Mapeamento falhou ({ex}) — dividindo paginas igualmente")
            doc = _pdfium.PdfDocument(pdf_bytes)
            total_pags = len(doc)
            doc.close()
            paginas_mapa = []
            n = len(internacao_ids)
            tamanho = total_pags // n
            for i in range(n):
                ini = i * tamanho
                fim = ini + tamanho if i < n - 1 else total_pags
                paginas_mapa.extend([i] * (fim - ini))

        resultado = {iid: [] for iid in internacao_ids}
        for pag_idx, inter_idx in enumerate(paginas_mapa):
            if 0 <= inter_idx < len(internacao_ids):
                iid = internacao_ids[inter_idx]
                resultado[iid].append(pag_idx)
            else:
                resultado[internacao_ids[0]].append(pag_idx)

        return resultado

    def _mapear_paginas_por_internacao_local(
        jpeg_rows: list, mapa_ids: dict, internacao_ids: list, on_progress=None
    ) -> dict:
        """
        Versao que usa JEPGs ja salvos localmente (fase 1 concluida).
        Retorna {internacao_id: [lista de pdf_paginas.id]}.
        """
        import base64 as _b64

        def _prog(msg):
            if on_progress: on_progress(msg)

        try:
            from extratores.extrator_prontuario import _chamar_visao_generica

            descricoes = []
            for i, iid in enumerate(internacao_ids):
                inter = mapa_ids.get(iid, {})
                d = inter.get("data_entrada") or "?"
                h = inter.get("hospital") or "?"
                descricoes.append(f"{i}: {h} entrada={d}")
            desc_txt = "\n".join(descricoes)

            prompt_mapa = f"""Prontuario hospitalar com {len(internacao_ids)} internacao(oes):
{desc_txt}

Para cada pagina indique o indice da internacao (0, 1, ...) ou -1 se nao pertencer.
Retorne SOMENTE JSON: {{"paginas": [indice_pag1, indice_pag2, ...]}}
Array com exatamente uma entrada por pagina na ordem das paginas."""

            total_pags = len(jpeg_rows)
            LOTE = 6
            paginas_mapa = []
            for li in range((total_pags + LOTE - 1) // LOTE):
                ini = li * LOTE
                fim = min(ini + LOTE, total_pags)
                _prog(f"Mapeando paginas {ini+1}-{fim}/{total_pags}...")
                lote_imgs = []
                for pid, jpeg_local in jpeg_rows[ini:fim]:
                    try:
                        with open(jpeg_local, "rb") as f:
                            lote_imgs.append(_b64.b64encode(f.read()).decode())
                    except Exception:
                        lote_imgs.append("")
                lote_imgs = [img for img in lote_imgs if img]
                try:
                    r = _chamar_visao_generica(lote_imgs, prompt_mapa)
                    paginas_mapa.extend(r.get("paginas") or [-1] * (fim - ini))
                except Exception:
                    paginas_mapa.extend([-1] * (fim - ini))

        except Exception as ex:
            _prog(f"Mapeamento falhou ({ex}) — dividindo igualmente")
            n = len(internacao_ids)
            tamanho = len(jpeg_rows) // n
            paginas_mapa = []
            for i in range(n):
                ini = i * tamanho
                fim = ini + tamanho if i < n - 1 else len(jpeg_rows)
                paginas_mapa.extend([i] * (fim - ini))

        # retorna {iid: [pdf_paginas.id]}
        resultado = {iid: [] for iid in internacao_ids}
        for idx, (pid, _) in enumerate(jpeg_rows):
            inter_idx = paginas_mapa[idx] if idx < len(paginas_mapa) else -1
            if 0 <= inter_idx < len(internacao_ids):
                resultado[internacao_ids[inter_idx]].append(pid)
            else:
                resultado[internacao_ids[0]].append(pid)

        return resultado

    def _salvar_fase2(resultado: dict, internacao_id: int):
        """Salva procedimentos, exames e medicamentos da internacao.

        Medicamentos: tabela remedios nao tem internacao_id, entao sao
        appendados como texto nas observacoes da internacao em vez de criar
        registros globais desvinculados.
        """
        from dados.model_prontuario import normalizar_data, salvar_exame

        procs_salvos  = 0
        exames_salvos = 0

        # ── procedimentos ────────────────────────────────────────
        procs_existentes = {
            p["nome"].strip().lower()
            for p in _procedimentos[0]
            if p.get("internacao_id") == internacao_id
        }
        for p in resultado.get("procedimentos") or []:
            nome = (p.get("nome") or "").strip()
            if not nome or nome.lower() in procs_existentes:
                continue
            try:
                salvar_procedimento({
                    "internacao_id": internacao_id,
                    "nome":          nome,
                    "tipo":          p.get("tipo") or "cirurgico",
                    "data":          normalizar_data(p.get("data") or "") or None,
                    "hora":          p.get("hora") or None,
                    "local":         p.get("local") or None,
                    "anestesia":     p.get("anestesia") or "sem",
                    "resultado":     p.get("resultado") or None,
                    "observacoes":   p.get("observacoes") or None,
                })
                procs_existentes.add(nome.lower())
                procs_salvos += 1
            except Exception as ex:
                log.warning("[FASE2] proc '%s': %s", nome, ex)

        # ── exames ───────────────────────────────────────────────
        import sqlite3 as _sq
        from dados.model_prontuario import DB_PATH
        try:
            with _sq.connect(DB_PATH, timeout=15) as _c:
                exames_existentes = {
                    (r[0] or "").strip().lower()
                    for r in _c.execute(
                        "SELECT tipo_exame FROM exames WHERE internacao_id=?",
                        (internacao_id,)
                    )
                }
        except Exception:
            exames_existentes = set()

        for ex in resultado.get("exames") or []:
            tipo = (ex.get("tipo") or ex.get("nome") or "").strip()
            if not tipo or tipo.lower() in exames_existentes:
                continue
            try:
                salvar_exame({
                    "internacao_id":   internacao_id,
                    "tipo":            "laudo",
                    "tipo_exame":      tipo,
                    "data_exame":      normalizar_data(ex.get("data") or "") or None,
                    "laboratorio":     ex.get("laboratorio") or None,
                    "medico_solicit":  ex.get("medico") or None,
                    "resultado_texto": ex.get("resultado") or ex.get("valor") or None,
                })
                exames_existentes.add(tipo.lower())
                exames_salvos += 1
            except Exception as ex_err:
                log.warning("[FASE2] exame '%s': %s", tipo, ex_err)

        # ── medicamentos -> observacoes da internacao ─────────────
        # remedios nao tem internacao_id: registrar como texto na internacao
        meds_lista = resultado.get("medicamentos") or []
        meds_texto = ""
        if meds_lista:
            linhas = []
            for med in meds_lista:
                nome = (med.get("nome") or "").strip()
                if not nome:
                    continue
                partes_med = [nome]
                dose = (med.get("dose") or med.get("dosagem") or "").strip()
                freq = (med.get("frequencia") or "").strip()
                if dose: partes_med.append(dose)
                if freq: partes_med.append(freq)
                linhas.append("- " + " | ".join(partes_med))
            if linhas:
                meds_texto = "MEDICAMENTOS DA INTERNACAO:\n" + "\n".join(linhas)

        if meds_texto:
            try:
                with _sq.connect(DB_PATH, timeout=15) as _c:
                    row = _c.execute(
                        "SELECT observacoes FROM internacoes WHERE id=?",
                        (internacao_id,)
                    ).fetchone()
                obs_atual = (row[0] or "").strip() if row else ""
                # evita duplicar bloco se ja foi appendado antes
                if "MEDICAMENTOS DA INTERNACAO:" not in obs_atual:
                    nova_obs = (obs_atual + "\n\n" + meds_texto).strip()
                    with _sq.connect(DB_PATH, timeout=15) as _c:
                        _c.execute(
                            "UPDATE internacoes SET observacoes=? WHERE id=?",
                            (nova_obs, internacao_id)
                        )
                    _internacoes[0] = [
                        dict(i, observacoes=nova_obs) if i["id"] == internacao_id else i
                        for i in _internacoes[0]
                    ]
            except Exception as ex_obs:
                log.warning("[FASE2] obs medicamentos: %s", ex_obs)

        _procedimentos[0] = listar_procedimentos()
        _rebuild_lista()

        partes = []
        if procs_salvos:  partes.append(f"{procs_salvos} procedimento(s)")
        if exames_salvos: partes.append(f"{exames_salvos} exame(s)")
        if meds_texto:    partes.append("medicamentos nas observacoes")
        msg = ("Extraido: " + ", ".join(partes)) if partes else "Nenhum detalhe novo encontrado."
        _snack(msg, VERD if partes else AMAR)

    # ── revisao de itens ignorados ───────────────────────────────

    def _revisar_ignorados(inter: dict, doc_local: str, drive_link: str = None):
        """Segunda checagem: mostra o que o PDF contem alem do que ja foi registrado."""
        import sqlite3 as _sq
        from dados.model_prontuario import DB_PATH

        internacao_id = inter["id"]

        # monta resumo do que ja existe para esta internacao
        ja_procs = [p["nome"] for p in _procedimentos[0]
                    if p.get("internacao_id") == internacao_id]
        try:
            with _sq.connect(DB_PATH, timeout=10) as _c:
                ja_exames = [r[0] for r in _c.execute(
                    "SELECT tipo_exame FROM exames WHERE internacao_id=?",
                    (internacao_id,)).fetchall()]
        except Exception:
            ja_exames = []
        obs = inter.get("observacoes") or ""
        ja_meds = []
        if "MEDICAMENTOS DA INTERNACAO:" in obs:
            for l in obs.splitlines():
                if l.strip().startswith("-"):
                    ja_meds.append(l.lstrip("- ").split("|")[0].strip())

        ja_registrado = {
            "procedimentos": ja_procs,
            "exames":        ja_exames,
            "medicamentos":  ja_meds,
        }

        # tenta obter bytes do PDF: Drive primeiro, local como fallback
        prog_txt = ft.Text("Iniciando revisao...", size=12, color=SEC,
                            text_align=ft.TextAlign.CENTER)
        _mostrar_overlay(ft.Column([
            ft.ProgressRing(width=32, height=32, stroke_width=3, color=ROXO),
            ft.Container(height=8),
            ft.Text("Claudia revisando PDF", size=13, color=TXT,
                    weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
            prog_txt,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True, spacing=4))

        def _prog(msg):
            prog_txt.value = msg
            try: page.update()
            except Exception: pass

        def _run():
            try:
                pdf_bytes = None
                drv_id = inter.get("drive_file_id")
                if drv_id:
                    _prog("Baixando PDF do Drive...")
                    try:
                        from utils.drive_sync import baixar_foto as _baixar
                        from shared.auth import _get_creds
                        import tempfile, io as _io
                        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
                        tmp.close()
                        if _baixar(drv_id, tmp.name, creds=_get_creds()):
                            with open(tmp.name, "rb") as f:
                                pdf_bytes = f.read()
                        try: os.remove(tmp.name)
                        except Exception: pass
                    except Exception as ex_drv:
                        _prog(f"Drive falhou ({ex_drv}), tentando local...")

                if not pdf_bytes and doc_local and os.path.exists(doc_local):
                    _prog("Lendo PDF local...")
                    with open(doc_local, "rb") as f:
                        pdf_bytes = f.read()

                if not pdf_bytes:
                    _fechar_overlay()
                    _snack("PDF nao disponivel para revisao.", VERM)
                    return

                from extratores.extrator_prontuario import extrair_ignorados
                ignorados = extrair_ignorados(pdf_bytes, ja_registrado, on_progress=_prog)
                _fechar_overlay()
                _mostrar_checklist_ignorados(ignorados, internacao_id)

            except Exception as ex:
                _fechar_overlay()
                _snack(str(ex)[:200], VERM)

        threading.Thread(target=_run, daemon=True).start()

    def _mostrar_checklist_ignorados(ignorados: list, internacao_id: int):
        """Mostra overlay com checklist dos itens ignorados para o usuario escolher."""
        if not ignorados:
            _snack("Nenhum item ignorado encontrado.", AMAR)
            return

        selecionados = {i: [True] for i in range(len(ignorados))}

        def _cor_cat(cat):
            return {
                "procedimento": LAR, "exame": AZUL,
                "medicamento": VERD, "observacao": SEC,
            }.get(cat, MUT)

        itens_ui = []
        for i, item in enumerate(ignorados):
            cat  = item.get("categoria","outro")
            cor  = _cor_cat(cat)
            chk  = ft.Checkbox(value=True, fill_color=cor, check_color=BG)
            def _on_chk(e, idx=i, c=chk):
                selecionados[idx][0] = c.value
            chk.on_change = _on_chk
            itens_ui.append(ft.Container(
                content=ft.Row([
                    chk,
                    ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Text(cat, size=9, color=cor,
                                                weight=ft.FontWeight.W_600),
                                bgcolor=f"{cor}22", border_radius=6,
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            ),
                            ft.Text(item.get("data","") or "", size=10, color=MUT),
                        ], spacing=6),
                        ft.Text(item.get("titulo",""), size=12, color=TXT,
                                weight=ft.FontWeight.W_600),
                        ft.Text(item.get("descricao","") or "", size=11, color=SEC,
                                max_lines=3, overflow=ft.TextOverflow.ELLIPSIS),
                    ], spacing=2, expand=True),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.all(10),
                border=ft.border.all(1, BD),
            ))

        def _incluir_selecionados(e):
            _fechar_overlay()
            import sqlite3 as _sq
            from dados.model_prontuario import DB_PATH, normalizar_data
            obs_extras = []
            for i, item in enumerate(ignorados):
                if not selecionados[i][0]:
                    continue
                cat       = item.get("categoria","outro")
                titulo    = item.get("titulo","")
                descricao = item.get("descricao","") or ""
                data      = normalizar_data(item.get("data") or "") or None
                sugestao  = item.get("sugestao_campo","observacoes_internacao")

                if cat == "procedimento" or sugestao == "procedimentos":
                    try:
                        salvar_procedimento({
                            "internacao_id": internacao_id,
                            "nome":          titulo,
                            "tipo":          "terapeutico",
                            "data":          data or datetime.date.today().isoformat(),
                            "observacoes":   descricao or None,
                        })
                    except Exception as ex:
                        log.warning("[REVISAO] proc: %s", ex)
                elif cat == "exame" or sugestao == "exames":
                    try:
                        from dados.model_prontuario import salvar_exame
                        salvar_exame({
                            "internacao_id":   internacao_id,
                            "tipo":            "laudo",
                            "tipo_exame":      titulo,
                            "data_exame":      data,
                            "resultado_texto": descricao or None,
                        })
                    except Exception as ex:
                        log.warning("[REVISAO] exame: %s", ex)
                else:
                    obs_extras.append(f"- {titulo}: {descricao}" if descricao else f"- {titulo}")

            if obs_extras:
                try:
                    with _sq.connect(DB_PATH, timeout=15) as _c:
                        row = _c.execute(
                            "SELECT observacoes FROM internacoes WHERE id=?",
                            (internacao_id,)).fetchone()
                    obs_atual = (row[0] or "").strip() if row else ""
                    bloco = "ITENS ADICIONAIS (revisao PDF):\n" + "\n".join(obs_extras)
                    nova_obs = (obs_atual + "\n\n" + bloco).strip()
                    with _sq.connect(DB_PATH, timeout=15) as _c:
                        _c.execute("UPDATE internacoes SET observacoes=? WHERE id=?",
                                   (nova_obs, internacao_id))
                    _internacoes[0] = [
                        dict(i, observacoes=nova_obs) if i["id"] == internacao_id else i
                        for i in _internacoes[0]
                    ]
                except Exception as ex:
                    log.warning("[REVISAO] obs: %s", ex)

            _procedimentos[0] = listar_procedimentos()
            _rebuild_lista()
            _snack("Itens incluidos.", VERD)

        btn_incluir = ft.Container(
            content=ft.Row([
                ft.Icon("check_circle_rounded", size=14, color=VERD),
                ft.Text("Incluir selecionados", size=13, color=VERD,
                        weight=ft.FontWeight.W_600),
            ], spacing=6, tight=True),
            bgcolor=f"{VERD}22",
            border=ft.border.all(1, f"{VERD}55"),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
        )
        btn_incluir.on_click = _incluir_selecionados

        btn_fechar_rev = ft.Container(
            content=ft.Text("Fechar", size=13, color=SEC),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
        )
        btn_fechar_rev.on_click = lambda _: _fechar_overlay()

        n = len(ignorados)
        _mostrar_overlay(ft.Column([
            ft.Row([
                ft.Icon("manage_search_rounded", size=20, color=ROXO),
                ft.Text(f"{n} item(ns) nao registrado(s)", size=14, color=TXT,
                        weight=ft.FontWeight.W_700),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Icon("close_rounded", size=18, color=SEC),
                    border_radius=6, ink=True, padding=ft.padding.all(4),
                    on_click=lambda _: _fechar_overlay(),
                ),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Text("Selecione o que deseja incluir no prontuario:",
                    size=12, color=SEC),
            ft.Container(height=4),
            ft.Column(itens_ui, spacing=6, scroll=ft.ScrollMode.AUTO,
                      expand=True),
            ft.Container(height=8),
            ft.Row([btn_fechar_rev, btn_incluir], spacing=8,
                   alignment=ft.MainAxisAlignment.END),
        ], spacing=8, expand=True))

    # ── helpers de medico ────────────────────────────────────────

    def _nome_medico(med_id):
        if not med_id:
            return ""
        for m in _medicos[0]:
            if str(m["id"]) == str(med_id):
                return m["nome"]
        return ""

    # ── area principal ───────────────────────────────────────────

    area_lista = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    def _contar_paginas_internacao(internacao_id: int) -> int:
        import sqlite3 as _sq
        from dados.model_prontuario import DB_PATH
        try:
            with _sq.connect(DB_PATH, timeout=10) as _c:
                return _c.execute(
                    "SELECT COUNT(*) FROM prontuario_paginas WHERE internacao_id=?",
                    (internacao_id,)
                ).fetchone()[0]
        except Exception:
            return 0

    def _mostrar_paginas_internacao(internacao_id: int):
        """Overlay com lista de páginas do prontuário vinculadas a esta internação."""
        import sqlite3 as _sq
        from dados.model_prontuario import DB_PATH

        try:
            with _sq.connect(DB_PATH, timeout=10) as _c:
                rows = _c.execute("""
                    SELECT id, pagina_num, data_pagina, resumo,
                           jpeg_local, jpeg_drive_id
                    FROM prontuario_paginas
                    WHERE internacao_id=?
                    ORDER BY pagina_num
                """, (internacao_id,)).fetchall()
        except Exception as ex:
            _snack(f"Erro ao carregar paginas: {ex}"[:100], VERM)
            return

        if not rows:
            _snack("Nenhuma pagina vinculada a esta internacao.", AMAR)
            return

        def _para_disp(s):
            if not s: return "sem data"
            try:
                return datetime.datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                return s

        def _abrir_pag_img(pag_id, jpeg_local, jpeg_drive_id, pagina_num):
            """Abre imagem da página — local ou baixa do Drive."""
            tem_local = bool(jpeg_local and os.path.exists(jpeg_local))
            if tem_local:
                try:
                    page.launch_url(f"file:///{jpeg_local.replace(os.sep, '/')}")
                except Exception:
                    webbrowser.open(jpeg_local)
                return
            if jpeg_drive_id:
                _snack(f"Baixando pagina {pagina_num} do Drive...", None)
                def _baixar():
                    try:
                        from utils.drive_sync import baixar_foto
                        _HERE = os.path.dirname(os.path.abspath(__file__))
                        cache_path = os.path.join(_HERE, "..", "temp", "cache", f"{pag_id}.jpg")
                        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                        if not os.path.exists(cache_path):
                            baixar_foto(jpeg_drive_id, cache_path)
                        try:
                            page.launch_url(f"file:///{cache_path.replace(os.sep, '/')}")
                        except Exception:
                            webbrowser.open(cache_path)
                    except Exception as ex:
                        _snack(f"Erro ao baixar: {ex}"[:100], VERM)
                threading.Thread(target=_baixar, daemon=True).start()
            else:
                _snack("Imagem nao disponivel.", AMAR)

        itens = []
        for pag_id, num, data_str, resumo, jpeg_local, drive_id in rows:
            tem_img = bool((jpeg_local and os.path.exists(jpeg_local)) or drive_id)
            ico     = "image_rounded" if tem_img else "image_not_supported_rounded"
            cor_ico = AZUL if tem_img else MUT

            item = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(ico, size=13, color=cor_ico),
                        bgcolor=ft.Colors.with_opacity(0.12, cor_ico),
                        border_radius=6, width=28, height=28,
                        alignment=ft.alignment.center,
                    ),
                    ft.Column([
                        ft.Text(
                            f"Pag {num}  —  {_para_disp(data_str)}",
                            size=12, color=TXT, weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(
                            (resumo or "sem identificacao")[:55],
                            size=10, color=SEC, italic=not bool(resumo),
                        ),
                    ], spacing=1, tight=True, expand=True),
                    ft.Icon("open_in_new_rounded", size=13, color=MUT if not tem_img else AZUL),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=BD, border_radius=8, ink=tem_img,
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
            )
            if tem_img:
                def _click_pag(e, _id=pag_id, _jl=jpeg_local, _did=drive_id, _n=num):
                    _abrir_pag_img(_id, _jl, _did, _n)
                item.on_click = _click_pag
            itens.append(item)

        btn_fechar_pags = ft.Container(
            content=ft.Text("Fechar", size=12, color=SEC),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border=ft.border.all(1, BD),
        )
        btn_fechar_pags.on_click = lambda e: _fechar_overlay()

        _mostrar_overlay(ft.Column([
            ft.Row([
                ft.Icon("article_rounded", size=16, color=ROXO),
                ft.Text(f"Paginas do prontuario ({len(rows)})",
                        size=13, color=TXT, weight=ft.FontWeight.W_700, expand=True),
            ], spacing=6),
            ft.Container(height=6),
            ft.Column(itens, spacing=4, scroll=ft.ScrollMode.AUTO,
                      height=min(len(itens) * 54, 320)),
            ft.Container(height=10),
            ft.Row([btn_fechar_pags], alignment=ft.MainAxisAlignment.CENTER),
        ], tight=True, spacing=4, width=320))

    # ── overlay helpers ──────────────────────────────────────────

    def _fechar_overlay():
        # preserva FilePicker(s) — overlay.clear() os removeria e quebra pick_files
        pickers = [o for o in page.overlay if isinstance(o, ft.FilePicker)]
        page.overlay.clear()
        page.overlay.extend(pickers)
        try: page.update()
        except Exception: pass

    def _mostrar_overlay(conteudo):
        ov = ft.Container(
            content=ft.Container(
                content=conteudo,
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20),
                width=min(page.width or 400, 440),
            ),
            bgcolor="#CC000011", expand=True,
            alignment=ft.alignment.Alignment(0, 0),
        )
        # preserva FilePicker(s) ao trocar overlay
        pickers = [o for o in page.overlay if isinstance(o, ft.FilePicker)]
        page.overlay.clear()
        page.overlay.extend(pickers)
        page.overlay.append(ov)
        try: page.update()
        except Exception: pass

    # ── confirmacao generica ─────────────────────────────────────

    def _confirmar_acao(label, fn_sim, btn_label="Confirmar", btn_cor=None):
        btn_cor = btn_cor or AZUL
        def _sim(e):
            _fechar_overlay()
            fn_sim()
        btn_sim = ft.Container(
            content=ft.Text(btn_label, size=13, color=btn_cor, weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            border_radius=8, bgcolor=f"{btn_cor}22",
            border=ft.border.all(1, f"{btn_cor}66"), ink=True,
        )
        btn_nao = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            border_radius=8, bgcolor=CARD,
            border=ft.border.all(1, BD), ink=True,
        )
        btn_sim.on_click = _sim
        btn_nao.on_click = lambda e: _fechar_overlay()
        _mostrar_overlay(ft.Column([
            ft.Container(height=4),
            ft.Text(label, size=12, color=SEC, text_align="center"),
            ft.Container(height=12),
            ft.Row([btn_nao, btn_sim], spacing=10,
                   alignment=ft.MainAxisAlignment.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True, spacing=4))

    # ── confirmacao excluir ──────────────────────────────────────

    def _confirmar_excluir(label, fn_sim):
        def _sim(e):
            _fechar_overlay()
            fn_sim()
        btn_sim = ft.Container(
            content=ft.Text("Excluir", size=13, color=VERM, weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            border_radius=8, bgcolor=f"{VERM}22",
            border=ft.border.all(1, f"{VERM}66"), ink=True,
        )
        btn_nao = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            border_radius=8, bgcolor=CARD,
            border=ft.border.all(1, BD), ink=True,
        )
        btn_sim.on_click = _sim
        btn_nao.on_click = lambda e: _fechar_overlay()
        _mostrar_overlay(ft.Column([
            ft.Icon("warning_amber_rounded", size=36, color=VERM),
            ft.Container(height=6),
            ft.Text("Confirmar exclusao", size=14, color=TXT, weight=ft.FontWeight.W_700,
                    text_align="center"),
            ft.Text(label, size=12, color=SEC, text_align="center"),
            ft.Container(height=12),
            ft.Row([btn_nao, btn_sim], spacing=10,
                   alignment=ft.MainAxisAlignment.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True, spacing=4))

    # ── snack de notificacao ─────────────────────────────────────

    def _snack(msg: str, cor=None):
        cor = cor or AZUL
        page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, color=BG, size=13),
            bgcolor=cor,
            duration=3000,
        )
        page.snack_bar.open = True
        try: page.update()
        except Exception: pass

    # ── rebuild lista ─────────────────────────────────────────────

    def _rebuild_lista():
        area_lista.controls.clear()
        _render_internacoes()
        if _montado[0]:
            try: page.update()
            except Exception: pass

    # ── abrir PDF externo ─────────────────────────────────────────

    _PASTA_EXAMES = os.path.join(os.path.dirname(__file__), "..", "exames")

    def _resolver_doc(nome_ou_caminho: str) -> str:
        """Resolve caminho completo do PDF a partir do nome_base ou caminho absoluto.
        Tenta: caminho direto, + .pdf, pasta exames/, pasta exames/ + .pdf."""
        if not nome_ou_caminho:
            return ""
        candidatos = [
            nome_ou_caminho,
            nome_ou_caminho + ".pdf",
            os.path.join(_PASTA_EXAMES, os.path.basename(nome_ou_caminho)),
            os.path.join(_PASTA_EXAMES, os.path.basename(nome_ou_caminho) + ".pdf"),
        ]
        for c in candidatos:
            if os.path.exists(c):
                return c
        return ""

    def _abrir_doc(drive_link: str, doc_nome: str):
        """Abre Drive link no browser ou PDF local."""
        if drive_link:
            try:
                page.launch_url(drive_link)
            except Exception:
                try:
                    webbrowser.open(drive_link)
                except Exception as ex:
                    _snack(f"Erro ao abrir Drive: {ex}", VERM)
            return
        caminho = _resolver_doc(doc_nome or "")
        if not caminho:
            # tenta tambem na pasta temp/pdfs (internacoes reimportadas)
            _pasta_pdfs = os.path.join(os.path.dirname(__file__), "..", "temp", "pdfs")
            nome_base   = os.path.basename(doc_nome or "")
            candidato   = os.path.join(_pasta_pdfs, nome_base)
            if os.path.exists(candidato):
                caminho = candidato
        if caminho:
            try:
                page.launch_url("file:///" + caminho.replace("\\", "/"))
            except Exception:
                try:
                    webbrowser.open("file:///" + caminho.replace("\\", "/"))
                except Exception as ex:
                    _snack(f"Erro ao abrir PDF: {ex}", VERM)
        else:
            _snack("Sem documento vinculado a esta internacao.", AMAR)

    def _tem_doc(drive_link: str, doc_nome: str) -> bool:
        return bool(drive_link or _resolver_doc(doc_nome or ""))

    def _btn_abrir_doc(caminho: str, drive_link: str = None):
        """Abre PDF: prefere Drive (browser), fallback local."""
        def _abrir(e):
            try:
                if drive_link:
                    page.launch_url(drive_link)
                elif caminho and os.path.exists(caminho):
                    page.launch_url("file:///" + caminho.replace("\\", "/"))
            except Exception as ex:
                log.warning(f"[INTER] abrir doc: {ex}")
        cor = VERD if drive_link else AZUL
        icone = "cloud_done_rounded" if drive_link else "open_in_new_rounded"
        btn = ft.Container(
            content=ft.Icon(icone, size=14, color=cor),
            border_radius=6, ink=True,
            padding=ft.padding.all(4),
            bgcolor=f"{cor}18",
            tooltip="Abrir no Drive" if drive_link else "Abrir PDF local",
        )
        btn.on_click = _abrir
        return btn

    # ── estado de filtro ─────────────────────────────────────────

    _filtro = {
        "hospital":   "",   # texto livre, busca parcial
        "data_ini":   "",   # YYYY-MM-DD
        "data_fim":   "",   # YYYY-MM-DD
        "em_curso":   False,
    }

    def _filtro_ativo():
        return any([
            _filtro["hospital"].strip(),
            _filtro["data_ini"].strip(),
            _filtro["data_fim"].strip(),
            _filtro["em_curso"],
        ])

    def _aplicar_filtro(lista: list) -> list:
        from dados.model_prontuario import normalizar_data
        hosp    = _filtro["hospital"].strip().lower()
        d_ini   = _filtro["data_ini"].strip()
        d_fim   = _filtro["data_fim"].strip()
        em_cur  = _filtro["em_curso"]
        result  = []
        for it in lista:
            if hosp and hosp not in (it.get("hospital") or "").lower():
                continue
            d_ent = (it.get("data_entrada") or "")
            if d_ini and d_ent and d_ent < d_ini:
                continue
            if d_fim and d_ent and d_ent > d_fim:
                continue
            if em_cur and it.get("data_saida"):
                continue
            result.append(it)
        return result

    def _abrir_filtro():
        from dados.model_prontuario import normalizar_data

        f_hosp = ft.TextField(
            label="Hospital", value=_filtro["hospital"],
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, hint_text="parte do nome...",
            hint_style=ft.TextStyle(color=MUT),
        )
        f_ini = ft.TextField(
            label="De", value=_para_display(_filtro["data_ini"]),
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, hint_text="DD/MM/AAAA",
            hint_style=ft.TextStyle(color=MUT),
            expand=True,
        )
        f_fim = ft.TextField(
            label="Ate", value=_para_display(_filtro["data_fim"]),
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, hint_text="DD/MM/AAAA",
            hint_style=ft.TextStyle(color=MUT),
            expand=True,
        )
        chk_cur = ft.Checkbox(
            label="Somente em curso (sem alta)",
            value=_filtro["em_curso"],
            fill_color=LAR, check_color=BG,
            label_style=ft.TextStyle(color=SEC, size=12),
        )

        def _aplicar(e):
            _filtro["hospital"]  = f_hosp.value.strip()
            _filtro["data_ini"]  = normalizar_data(f_ini.value.strip()) or ""
            _filtro["data_fim"]  = normalizar_data(f_fim.value.strip()) or ""
            _filtro["em_curso"]  = chk_cur.value or False
            _fechar_overlay()
            _rebuild_lista()
            _atualizar_btn_filtro()

        def _limpar(e):
            _filtro["hospital"]  = ""
            _filtro["data_ini"]  = ""
            _filtro["data_fim"]  = ""
            _filtro["em_curso"]  = False
            _fechar_overlay()
            _rebuild_lista()
            _atualizar_btn_filtro()

        btn_aplicar = ft.Container(
            content=ft.Row([
                ft.Icon("filter_alt_rounded", size=14, color=AZUL),
                ft.Text("Filtrar", size=13, color=AZUL, weight=ft.FontWeight.W_600),
            ], spacing=6, tight=True),
            bgcolor=f"{AZUL}22",
            border=ft.border.all(1, f"{AZUL}55"),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
        )
        btn_aplicar.on_click = _aplicar

        btn_limpar = ft.Container(
            content=ft.Text("Limpar", size=13, color=SEC),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
        )
        btn_limpar.on_click = _limpar

        lbl_data = ft.Text("Data de entrada", size=11, color=SEC)
        _mostrar_overlay(ft.Column([
            ft.Row([
                ft.Icon("filter_alt_rounded", size=18, color=AZUL),
                ft.Text("Filtrar internacoes", size=14, color=TXT,
                        weight=ft.FontWeight.W_700, expand=True),
                ft.Container(
                    content=ft.Icon("close_rounded", size=18, color=SEC),
                    border_radius=6, ink=True, padding=ft.padding.all(4),
                    on_click=lambda _: _fechar_overlay(),
                ),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(height=4),
            f_hosp,
            lbl_data,
            ft.Row([f_ini, f_fim], spacing=8, expand=True),
            chk_cur,
            ft.Container(height=8),
            ft.Row([btn_limpar, btn_aplicar], spacing=8,
                   alignment=ft.MainAxisAlignment.END),
        ], spacing=8, tight=True))

    def _atualizar_btn_filtro():
        ativo = _filtro_ativo()
        btn_filtro.bgcolor    = f"{AZUL}22" if ativo else "transparent"
        btn_filtro.border     = ft.border.all(1, AZUL) if ativo else None
        icone_filtro.color    = AZUL if ativo else SEC
        txt_filtro.color      = AZUL if ativo else SEC
        txt_filtro.value      = "Filtro ativo" if ativo else "Filtro"
        txt_filtro.weight     = ft.FontWeight.W_600 if ativo else ft.FontWeight.NORMAL
        if _montado[0]:
            try: page.update()
            except Exception: pass

    # ── render internacoes ────────────────────────────────────────

    def _render_internacoes():
        lista = _aplicar_filtro(_internacoes[0])
        # ordena por data_entrada mais recente; sem data vai ao final
        lista.sort(key=lambda x: x.get("data_entrada") or "0000", reverse=True)
        if not lista:
            area_lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("local_hospital_rounded", size=40, color=MUT),
                    ft.Text("Nenhuma internacao registrada", size=13, color=MUT),
                    ft.Text("Use o botao + para adicionar", size=11, color=MUT),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6, tight=True),
                alignment=ft.alignment.Alignment(0, 0),
                expand=True, padding=ft.padding.symmetric(vertical=40),
            ))
            return
        for item in lista:
            cor        = _cor_tipo_inter(item.get("tipo", "eletiva"))
            label_tipo = _label_tipo_inter(item.get("tipo", "eletiva"))
            em_curso   = not item.get("data_saida")
            duracao    = _duracao(item.get("data_entrada", ""), item.get("data_saida"))

            # linha 1 — data + status + botao fechar (se em curso)
            data_txt = _para_display(item.get("data_entrada", ""))
            if item.get("data_saida"):
                data_txt += f" — {_para_display(item['data_saida'])}"

            status_chip = ft.Container(
                content=ft.Text(
                    "em curso" if em_curso else duracao,
                    size=9, color=LAR if em_curso else MUT,
                    weight=ft.FontWeight.W_600 if em_curso else ft.FontWeight.NORMAL,
                ),
                bgcolor=f"{LAR}18" if em_curso else "transparent",
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=6, vertical=2),
            )

            btn_fechar_alta = ft.Container(
                content=ft.Row([
                    ft.Icon("logout_rounded", size=11, color=VERD),
                    ft.Text("Alta", size=10, color=VERD, weight=ft.FontWeight.W_600),
                ], spacing=3, tight=True),
                bgcolor=f"{VERD}18",
                border=ft.border.all(1, f"{VERD}44"),
                border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=7, vertical=3),
                visible=em_curso,
            )

            def _fechar_alta(e, it=item):
                e.control.page  # evita propagacao para o card
                import datetime
                hoje = datetime.date.today().isoformat()
                def _confirmar_alta():
                    dados_upd = dict(it)
                    dados_upd["data_saida"] = hoje
                    try:
                        salvar_internacao(dados_upd)
                        _internacoes[0] = listar_internacoes()
                        _rebuild_lista()
                        _snack("Alta registrada.", VERD)
                    except Exception as ex:
                        _snack(str(ex)[:120], VERM)
                _confirmar_acao(
                    f"Registrar alta hoje ({_para_display(hoje)})\npara {it['hospital']}?",
                    _confirmar_alta,
                    btn_label="Registrar Alta", btn_cor=VERD,
                )

            btn_fechar_alta.on_click = _fechar_alta

            # linha 2 — hospital
            # linha 3 — motivo: prefere descrição da CID (parte após "—"); fallback motivo longo
            _cid_raw = (item.get("cid_entrada") or "").strip()
            if " — " in _cid_raw:
                _cid_desc = _cid_raw.split(" — ", 1)[1].strip()
            elif _cid_raw:
                _cid_desc = _cid_raw
            else:
                _cid_desc = ""
            motivo_txt = (_cid_desc or item.get("motivo") or "").strip()
            if len(motivo_txt) > 55:
                motivo_txt = motivo_txt[:52] + "..."

            procs   = [p for p in _procedimentos[0] if p.get("internacao_id") == item["id"]]
            n_procs = len(procs)

            linha1 = ft.Row([
                ft.Container(
                    content=ft.Text(label_tipo, size=9, color=cor, weight=ft.FontWeight.W_600),
                    bgcolor=f"{cor}18", border_radius=8,
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                ),
                ft.Text(data_txt, size=10, color=SEC),
                ft.Container(expand=True),
                status_chip,
            ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER)

            linha2 = ft.Text(
                item["hospital"], size=12, color=TXT,
                weight=ft.FontWeight.W_600,
                overflow=ft.TextOverflow.ELLIPSIS, max_lines=1,
            )

            cid_txt_card = (item.get("cid_entrada") or "").strip()

            linha3_items = []
            if cid_txt_card:
                linha3_items.append(ft.Container(
                    content=ft.Text(cid_txt_card, size=9, color=AMAR,
                                    overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                    bgcolor=f"{AMAR}18", border_radius=6,
                    padding=ft.padding.symmetric(horizontal=5, vertical=2),
                ))
            if n_procs:
                linha3_items.append(ft.Row([
                    ft.Icon("medical_services_rounded", size=10, color=AZUL),
                    ft.Text(str(n_procs), size=10, color=AZUL),
                ], spacing=2, tight=True))

            linhas_card = [linha1, linha2]
            if motivo_txt:
                linhas_card.append(ft.Text(
                    motivo_txt, size=10, color=SEC, italic=True,
                    overflow=ft.TextOverflow.ELLIPSIS, max_lines=2,
                ))
            if linha3_items:
                linhas_card.append(ft.Row(linha3_items, spacing=6))

            card_content = ft.Column(linhas_card, spacing=3, tight=True)

            card = ft.Container(
                content=card_content,
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border=ft.border.all(1, f"{LAR}55" if em_curso else BD),
                ink=True, expand=True,
            )
            def _abrir_edit_inter(e, it=item):
                _ir_detalhe(it)
            card.on_click = _abrir_edit_inter

            # botao de documento fora do card — sempre visivel para indicar rastreabilidade
            doc_item      = item.get("documento_local")
            drv_link_item = item.get("drive_link")
            tem_doc       = _tem_doc(drv_link_item, doc_item)
            if tem_doc:
                cor_doc_item = VERD if drv_link_item else AZUL
                ico_doc_item = "cloud_done_rounded" if drv_link_item else "picture_as_pdf_rounded"
                btn_doc_card = ft.Container(
                    content=ft.Icon(ico_doc_item, size=18, color=cor_doc_item),
                    border_radius=8, ink=True,
                    padding=ft.padding.all(8),
                    bgcolor=CARD,
                    border=ft.border.all(1, f"{cor_doc_item}55"),
                    tooltip="Abrir prontuario",
                )
                btn_doc_card.on_click = lambda e, dl=drv_link_item, d=doc_item: _abrir_doc(dl, d)
            else:
                btn_doc_card = ft.Container(
                    content=ft.Icon("help_outline_rounded", size=18, color=MUT),
                    border_radius=8,
                    padding=ft.padding.all(8),
                    tooltip="Sem documento fonte — dados nao verificados",
                )

            btn_docs_brutos = ft.Container(
                content=ft.Icon("folder_copy_rounded", size=18, color=AMAR),
                border_radius=8, ink=True,
                padding=ft.padding.all(8),
                bgcolor=CARD,
                border=ft.border.all(1, f"{AMAR}55"),
                tooltip="Documentos brutos",
            )
            btn_docs_brutos.on_click = lambda e, iid=item["id"]: _ir_docs(iid)

            n_pags_card = _contar_paginas_internacao(item["id"])
            botoes_direita = [card]
            if n_pags_card > 0:
                btn_pags_card = ft.Container(
                    content=ft.Column([
                        ft.Icon("article_rounded", size=16, color=ROXO),
                        ft.Text(str(n_pags_card), size=8, color=ROXO,
                                weight=ft.FontWeight.W_600,
                                text_align=ft.TextAlign.CENTER),
                    ], spacing=1, tight=True,
                       horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    border_radius=8, ink=True,
                    padding=ft.padding.all(6),
                    bgcolor=CARD,
                    border=ft.border.all(1, f"{ROXO}55"),
                    tooltip="Ver paginas do prontuario",
                )
                btn_pags_card.on_click = lambda e, iid=item["id"]: _mostrar_paginas_internacao(iid)
                botoes_direita.append(btn_pags_card)
            botoes_direita.append(btn_docs_brutos)

            area_lista.controls.append(
                ft.Row(botoes_direita,
                       spacing=4,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER)
            )

    # ── form internacao ───────────────────────────────────────────

    # ── navegacao lista <-> detalhe ──────────────────────────────

    _tela_wrapper = ft.Column(expand=True)

    def _ir_lista():
        _tela_wrapper.controls.clear()
        _rebuild_lista()
        _tela_wrapper.controls.append(_corpo_lista[0])
        if _montado[0]:
            try: page.update()
            except Exception: pass

    def _ir_detalhe(item):
        try:
            det = _criar_detalhe(item["id"])
        except Exception as ex:
            log.exception("[DETALHE] erro ao criar detalhe id=%s: %s", item.get("id"), ex)
            _snack(f"Erro ao abrir detalhe: {ex}"[:120], VERM)
            return
        _tela_wrapper.controls.clear()
        _tela_wrapper.controls.append(det)
        if _montado[0]:
            try: page.update()
            except Exception: pass

    def _ir_docs(internacao_id: int):
        from telas.tela_docs_brutos import criar_tela_docs_brutos
        tela_docs = criar_tela_docs_brutos(page, _ir_lista, internacao_id=internacao_id)
        _tela_wrapper.controls.clear()
        _tela_wrapper.controls.append(tela_docs)
        if _montado[0]:
            try: page.update()
            except Exception: pass

    # ── tela detalhe de internacao ───────────────────────────────

    def _criar_detalhe(internacao_id: int) -> ft.Container:
        _aba_det = [0]
        area_det  = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        barra_det_l1 = ft.Row(spacing=0)
        barra_det_l2 = ft.Row(spacing=0)
        barra_det    = ft.Column([
            barra_det_l1,
            ft.Divider(height=1, color=BD),
            barra_det_l2,
        ], spacing=0)

        # picker de laudo criado uma vez por detalhe (evita duplicar no overlay)
        _laudo_picker    = ft.FilePicker()
        _laudo_exame_id  = [None]
        page.overlay.append(_laudo_picker)

        def _on_laudo_status_det(msg):
            if not isinstance(msg, dict): return
            if msg.get("ok"):
                _snack("Laudo vinculado com sucesso!", VERD)
                # recarrega exames do banco para atualizar icones
                from dados.model_prontuario import listar_exames_internacao
                try:
                    _exames_det_cache[:] = listar_exames_internacao(internacao_id)
                except Exception:
                    pass
                if _aba_det[0] == 2:
                    _render_aba_det()
            else:
                _snack(f"Erro: {msg.get('msg','')}", VERM)

        _exames_det_cache = []
        page.pubsub.subscribe_topic("_laudo_status", _on_laudo_status_det)

        def _get_inter():
            return next((x for x in _internacoes[0] if x["id"] == internacao_id), None)

        def _reload_detalhe():
            _internacoes[0]   = listar_internacoes()
            _procedimentos[0] = listar_procedimentos()
            _render_aba_det()

        ABAS_DET = [
            (0, "info_rounded",             "Info",          AZUL),
            (1, "medical_services_rounded", "Procedimentos", LAR),
            (2, "biotech_rounded",          "Exames",        VERD),
            (3, "medication_rounded",       "Remedios",      ROXO),
            (4, "analytics_rounded",        "Diagnosticos",  AMAR),
            (5, "vital_signs_rounded",      "Sinais",        "#4ECDC4"),
            (6, "folder_open_rounded",      "Brutos",        SEC),
            (7, "description_rounded",      "Evolucao",      ROXO),
        ]

        def _rebuild_abas_det():
            barra_det_l1.controls.clear()
            barra_det_l2.controls.clear()
            for idx, icone, label, cor in ABAS_DET:
                ativo = _aba_det[0] == idx
                tab = ft.Container(
                    content=ft.Column([
                        ft.Icon(icone, size=14, color=cor if ativo else SEC),
                        ft.Text(label, size=9,
                                color=cor if ativo else SEC,
                                weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.NORMAL),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                       spacing=2, tight=True),
                    expand=True,
                    padding=ft.padding.symmetric(vertical=8),
                    border=ft.Border(bottom=ft.BorderSide(2, cor if ativo else "#00000000")),
                    ink=True,
                )
                tab.on_click = lambda e, i=idx: _trocar_aba_det(i)
                if idx < 4:
                    barra_det_l1.controls.append(tab)
                else:
                    barra_det_l2.controls.append(tab)
            if _montado[0]:
                try: page.update()
                except Exception: pass

        def _trocar_aba_det(idx):
            _aba_det[0] = idx
            _rebuild_abas_det()
            _render_aba_det()

        def _render_info():
            inter = _get_inter()
            if not inter:
                return
            from dados.model_prontuario import normalizar_data, salvar_internacao

            # ── chip de rastreabilidade ──────────────────────────────
            doc_info     = inter.get("documento_local")
            drv_info     = inter.get("drive_link")
            tem_doc_info = _tem_doc(drv_info, doc_info)
            fonte        = inter.get("fonte_dados") or ("importado" if tem_doc_info else "manual")
            if tem_doc_info:
                _ico_fonte = "verified_rounded"
                _cor_fonte = VERD
                _nome_doc  = (os.path.basename(doc_info) if doc_info
                              else ("Drive" if drv_info else ""))
                _txt_fonte = f"Importado de PDF  —  {_nome_doc}" if _nome_doc else "Importado de PDF"
            else:
                _ico_fonte = "warning_amber_rounded"
                _cor_fonte = LAR
                _txt_fonte = "Dados inseridos manualmente — nenhum PDF vinculado a esta internacao"
            chip_fonte = ft.Container(
                content=ft.Row([
                    ft.Icon(_ico_fonte, size=13, color=_cor_fonte),
                    ft.Text(_txt_fonte, size=11, color=_cor_fonte, expand=True),
                    ft.Icon("open_in_new_rounded", size=12, color=_cor_fonte,
                            visible=tem_doc_info),
                ], spacing=6),
                bgcolor=CARD, border_radius=8, padding=ft.padding.all(10),
                border=ft.border.all(1, f"{_cor_fonte}55"),
                ink=tem_doc_info,
                tooltip="Abrir documento fonte" if tem_doc_info else None,
            )
            if tem_doc_info:
                chip_fonte.on_click = lambda e: _abrir_doc(drv_info, doc_info)
            area_det.controls.append(chip_fonte)

            # ── páginas do prontuário vinculadas ─────────────────────
            n_pags_det = _contar_paginas_internacao(internacao_id)
            if n_pags_det > 0:
                btn_pags_det = ft.Container(
                    content=ft.Row([
                        ft.Icon("article_rounded", size=14, color=ROXO),
                        ft.Text(f"Ver {n_pags_det} pagina{'s' if n_pags_det != 1 else ''} do prontuario",
                                size=12, color=ROXO, weight=ft.FontWeight.W_600, expand=True),
                        ft.Icon("chevron_right_rounded", size=14, color=MUT),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=ft.Colors.with_opacity(0.08, ROXO),
                    border_radius=8, ink=True,
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.35, ROXO)),
                )
                btn_pags_det.on_click = lambda e: _mostrar_paginas_internacao(internacao_id)
                area_det.controls.append(btn_pags_det)

            def _row_kv(label, valor, cor=TXT):
                if not valor: return None
                return ft.Row([
                    ft.Text(f"{label}:", size=11, color=MUT, width=90),
                    ft.Text(str(valor), size=12, color=cor, expand=True),
                ], spacing=8)

            loc = (inter.get("cidade") or "") + (" — " + inter.get("uf") if inter.get("uf") else "")
            infos = [w for w in [
                _row_kv("Tipo",     _label_tipo_inter(inter.get("tipo","eletiva")),
                                    _cor_tipo_inter(inter.get("tipo","eletiva"))),
                _row_kv("Objetivo", (inter.get("objetivo") or "").capitalize()),
                _row_kv("Local",    loc or None),
                _row_kv("Medico",   inter.get("medico_nome") or inter.get("medico_responsavel")),
                _row_kv("CID",      inter.get("cid_entrada"), AMAR),
                _row_kv("CID alta", inter.get("cid_saida")),
            ] if w]
            if infos:
                area_det.controls.append(ft.Container(
                    content=ft.Column(infos, spacing=6),
                    bgcolor=CARD, border_radius=10,
                    padding=ft.padding.all(12), border=ft.border.all(1, BD),
                ))

            # ── bloco de alta (so leitura — edicao fica no form) ────
            em_curso_info = not inter.get("data_saida")

            def _alta_rapida(e):
                dados_upd = dict(inter)
                dados_upd["data_saida"] = datetime.date.today().isoformat()
                try:
                    salvar_internacao(dados_upd)
                    _internacoes[0] = listar_internacoes()
                    _reload_detalhe()
                    _snack("Alta registrada.", VERD)
                except Exception as ex:
                    _snack(str(ex)[:100], VERM)

            btn_alta_hoje = ft.Container(
                content=ft.Row([
                    ft.Icon("logout_rounded", size=13, color=VERD),
                    ft.Text("Alta hoje", size=11, color=VERD, weight=ft.FontWeight.W_600),
                ], spacing=4, tight=True),
                border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                bgcolor=f"{VERD}22",
                border=ft.border.all(1, f"{VERD}55"),
                visible=em_curso_info,
                tooltip="Registrar alta com a data de hoje",
            )
            btn_alta_hoje.on_click = _alta_rapida

            doc      = inter.get("documento_local")
            drv_link = inter.get("drive_link")
            drv_id   = inter.get("drive_file_id")
            tem_pdf  = _tem_doc(drv_link, doc)

            cor_alta   = LAR if em_curso_info else VERD
            label_alta = "Em curso — sem alta" if em_curso_info else (
                f"Alta: {_para_display(inter.get('data_saida'))}")
            area_det.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("logout_rounded", size=14, color=cor_alta),
                    ft.Text(label_alta, size=12, color=cor_alta,
                            weight=ft.FontWeight.W_600, expand=True),
                    btn_alta_hoje,
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.all(12),
                border=ft.border.all(1, f"{LAR}55" if em_curso_info else f"{VERD}44"),
            ))

            # Motivo, diagnostico_saida e observacoes foram migrados para
            # diagnosticos_internacao e internacao_dados_brutos — ver abas proprias.

            # botao revisar PDF (Claudia — itens ignorados)
            if tem_pdf or drv_id:
                btn_rev = ft.Container(
                    content=ft.Row([
                        ft.Icon("manage_search_rounded", size=14, color=ROXO),
                        ft.Text("Revisar PDF — itens ignorados", size=12, color=ROXO),
                    ], spacing=6, tight=True),
                    border_radius=8, ink=True,
                    bgcolor=CARD,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    border=ft.border.all(1, ROXO),
                )
                btn_rev.on_click = lambda e, i=inter, d=_resolver_doc(doc or ""), dl=drv_link: _revisar_ignorados(i, d, dl)
                area_det.controls.append(btn_rev)

        def _render_procs():
            inter = _get_inter()
            if not inter: return
            procs_int = [p for p in _procedimentos[0]
                         if p.get("internacao_id") == inter["id"]]

            # banner de fonte (mesmo documento da internacao)
            _doc_p  = inter.get("documento_local")
            _drv_p  = inter.get("drive_link")
            _tem_p  = _tem_doc(_drv_p, _doc_p)
            _cor_p  = VERD if _tem_p else LAR
            _ico_p  = "verified_rounded" if _tem_p else "warning_amber_rounded"
            _nome_p = (os.path.basename(_doc_p) if _doc_p
                       else ("Drive" if _drv_p else "")) if _tem_p else ""
            _txt_p  = (f"Fonte: {_nome_p}" if _nome_p else "Fonte: PDF importado") if _tem_p \
                      else "Inserido manualmente — sem documento vinculado"
            _banner_p = ft.Container(
                content=ft.Row([
                    ft.Icon(_ico_p, size=12, color=_cor_p),
                    ft.Text(_txt_p, size=10, color=_cor_p, expand=True),
                    ft.Icon("open_in_new_rounded", size=11, color=_cor_p, visible=_tem_p),
                ], spacing=5),
                bgcolor=f"{_cor_p}11", border_radius=6,
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                border=ft.border.all(1, f"{_cor_p}44"),
                ink=_tem_p,
                tooltip="Abrir documento fonte" if _tem_p else None,
            )
            if _tem_p:
                _banner_p.on_click = lambda e: _abrir_doc(_drv_p, _doc_p)
            area_det.controls.append(_banner_p)

            btn_add = ft.Container(
                content=ft.Row([
                    ft.Icon("add_rounded", size=14, color=LAR),
                    ft.Text("Novo procedimento", size=12, color=LAR),
                ], spacing=4, tight=True),
                border_radius=8, ink=True, bgcolor=f"{LAR}18",
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
            )
            btn_add.on_click = lambda e: _form_procedimento(
                {"internacao_id": inter["id"]}, on_salvo=_reload_detalhe)
            area_det.controls.append(btn_add)
            if not procs_int:
                area_det.controls.append(ft.Container(
                    content=ft.Text("Nenhum procedimento vinculado.", size=12, color=MUT),
                    padding=ft.padding.symmetric(vertical=16),
                ))
                return
            for p in procs_int:
                cor = _cor_tipo_proc(p.get("tipo","cirurgico"))
                card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Text(_label_tipo_proc(p.get("tipo","cirurgico")),
                                                size=10, color=cor, weight=ft.FontWeight.W_600),
                                bgcolor=f"{cor}22", border_radius=10,
                                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            ),
                            ft.Container(expand=True),
                            ft.Text(_para_display(p.get("data","")), size=11, color=SEC),
                        ]),
                        ft.Text(p["nome"], size=13, color=TXT, weight=ft.FontWeight.W_600),
                        ft.Text(p.get("resultado",""), size=11, color=MUT,
                                ) if p.get("resultado") else ft.Container(height=0),
                    ], spacing=5),
                    bgcolor=CARD, border_radius=12, padding=ft.padding.all(12),
                    border=ft.border.all(1, BD), ink=True,
                )
                def _edit_p(e, proc=p):
                    _form_procedimento(proc, on_salvo=_reload_detalhe)
                card.on_click = _edit_p
                area_det.controls.append(card)

        def _render_exames():
            inter = _get_inter()
            if not inter: return
            try:
                from dados.model_prontuario import listar_exames_internacao
                exames_int = listar_exames_internacao(inter["id"])
                _exames_det_cache[:] = exames_int
            except Exception:
                exames_int = _exames_det_cache or []
            if not exames_int:
                area_det.controls.append(ft.Container(
                    content=ft.Text("Nenhum exame vinculado a esta internacao.", size=12, color=MUT),
                    padding=ft.padding.symmetric(vertical=16),
                ))
                return

            def _on_laudo_picked(e: ft.FilePickerResultEvent):
                if not e.files or not _laudo_exame_id[0]:
                    return
                caminho = e.files[0].path
                if not caminho or not os.path.exists(caminho):
                    _snack("Arquivo nao encontrado.", VERM)
                    return
                exame_id = _laudo_exame_id[0]
                _snack("Enviando laudo...", AZUL)

                def _enviar():
                    try:
                        from utils.drive_sync import _EXAMES_PDF_ID, upload_foto as _upload
                        from utils.drive_sync import _get_creds
                        creds = _get_creds()
                        nome_arq = os.path.basename(caminho)
                        drive_id = _upload(caminho, nome_arq, _EXAMES_PDF_ID, creds)
                        if not drive_id:
                            page.pubsub.send_all_on_topic("_laudo_status",
                                {"ok": False, "msg": "Upload falhou."})
                            return
                        from dados.model_prontuario import vincular_laudo_exame
                        vincular_laudo_exame(exame_id, drive_id)
                        page.pubsub.send_all_on_topic("_laudo_status",
                            {"ok": True, "exame_id": exame_id, "drive_id": drive_id})
                    except Exception as ex:
                        page.pubsub.send_all_on_topic("_laudo_status",
                            {"ok": False, "msg": str(ex)[:120]})

                threading.Thread(target=_enviar, daemon=True).start()

            _laudo_picker.on_result = _on_laudo_picked

            for ex in exames_int:
                dfid      = ex.get("drive_file_id") or ""
                tem_laudo = bool(dfid)
                resultado = (ex.get("resultado_texto") or "").strip()

                def _ver_laudo(e, fid=dfid):
                    if fid:
                        url = f"https://drive.google.com/file/d/{fid}/view"
                        page.launch_url(url)

                def _anexar_laudo(e, eid=ex["id"]):
                    _laudo_exame_id[0] = eid
                    _laudo_picker.pick_files(allowed_extensions=["pdf"])

                btn_laudo = ft.Container(
                    content=ft.Row([
                        ft.Icon(
                            "description_rounded" if tem_laudo else "attach_file_rounded",
                            size=13,
                            color=VERD if tem_laudo else MUT,
                        ),
                        ft.Text(
                            "Laudo" if tem_laudo else "Anexar",
                            size=10,
                            color=VERD if tem_laudo else MUT,
                        ),
                    ], spacing=3, tight=True),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=6,
                    border=ft.border.all(1, VERD if tem_laudo else BD2),
                    ink=True,
                    tooltip="Ver laudo no Drive" if tem_laudo else "Anexar laudo PDF",
                )
                btn_laudo.on_click = _ver_laudo if tem_laudo else _anexar_laudo

                # chip de status do resultado
                if resultado:
                    chip_res = None  # resultado mostrado inline abaixo
                elif tem_laudo:
                    chip_res = ft.Container(
                        content=ft.Row([
                            ft.Icon("picture_as_pdf_rounded", size=11, color=VERD),
                            ft.Text("Resultado no laudo", size=10, color=VERD),
                        ], spacing=3, tight=True),
                        bgcolor=f"{VERD}18", border_radius=6,
                        padding=ft.padding.symmetric(horizontal=8, vertical=3),
                        border=ft.border.all(1, f"{VERD}44"),
                        ink=True, tooltip="Abrir laudo no Drive",
                    )
                    chip_res.on_click = _ver_laudo
                else:
                    chip_res = ft.Container(
                        content=ft.Row([
                            ft.Icon("help_outline_rounded", size=11, color=LAR),
                            ft.Text("Sem resultado registrado", size=10, color=LAR),
                        ], spacing=3, tight=True),
                        bgcolor=f"{LAR}18", border_radius=6,
                        padding=ft.padding.symmetric(horizontal=8, vertical=3),
                        border=ft.border.all(1, f"{LAR}44"),
                    )

                linhas_card = [
                    ft.Row([
                        ft.Text(ex.get("tipo_exame","?"), size=13, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True),
                        ft.Text(_para_display(ex.get("data_exame","")), size=11, color=SEC),
                    ]),
                    ft.Row([
                        ft.Text(ex.get("laboratorio","") or "", size=11, color=MUT,
                                expand=True) if ex.get("laboratorio") else ft.Container(expand=True),
                        btn_laudo,
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ]
                if resultado:
                    linhas_card.append(ft.Text(
                        resultado, size=11, color=SEC, max_lines=4,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ))
                elif chip_res:
                    linhas_card.append(chip_res)

                card = ft.Container(
                    content=ft.Column(linhas_card, spacing=4),
                    bgcolor=CARD, border_radius=12, padding=ft.padding.all(12),
                    border=ft.border.all(1, BD),
                )
                area_det.controls.append(card)

        def _render_remedios():
            inter = _get_inter()
            if not inter: return
            # medicamentos ficam no bloco de texto das observacoes da internacao
            obs = inter.get("observacoes") or ""
            bloco = ""
            if "MEDICAMENTOS DA INTERNACAO:" in obs:
                idx = obs.index("MEDICAMENTOS DA INTERNACAO:")
                bloco = obs[idx:]
            if not bloco:
                area_det.controls.append(ft.Container(
                    content=ft.Text("Nenhum medicamento registrado para esta internacao.", size=12, color=MUT),
                    padding=ft.padding.symmetric(vertical=16),
                ))
                return
            linhas = [l.lstrip("- ").strip() for l in bloco.splitlines()
                      if l.strip().startswith("-")]
            if not linhas:
                area_det.controls.append(ft.Container(
                    content=ft.Text(bloco, size=12, color=SEC),
                    padding=ft.padding.all(12),
                ))
                return
            for linha in linhas:
                partes = [p.strip() for p in linha.split("|")]
                nome = partes[0] if partes else linha
                detalhes = "  •  ".join(partes[1:]) if len(partes) > 1 else ""
                area_det.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Text(nome, size=13, color=TXT, weight=ft.FontWeight.W_600),
                        ft.Text(detalhes, size=11, color=SEC,
                                ) if detalhes else ft.Container(height=0),
                    ], spacing=4),
                    bgcolor=CARD, border_radius=12, padding=ft.padding.all(12),
                    border=ft.border.all(1, BD),
                ))

        def _render_diagnosticos():
            inter = _get_inter()
            if not inter:
                return
            from dados.model_prontuario import (listar_exames_internacao,
                                                 listar_procedimentos,
                                                 listar_marcadores_internacao,
                                                 listar_diagnosticos_internacao,
                                                 salvar_diagnostico_internacao,
                                                 excluir_diagnostico_internacao)

            tem_algo = False

            # ── A: Diagnosticos estruturados (tabela diagnosticos_internacao) ──
            _TIPO_DIAG = [
                ("entrada",    "Entrada",    AZUL),
                ("saida",      "Alta",       VERD),
                ("secundario", "Secundario", SEC),
            ]
            _CERTEZA_DIAG = [
                ("confirmado", "Confirmado", VERD),
                ("suspeita",   "Suspeita",   AMAR),
                ("descartado", "Descartado", MUT),
            ]

            def _label_tipo_d(t):
                return next((l for k,l,_ in _TIPO_DIAG if k==t), t or "—")
            def _cor_tipo_d(t):
                return next((c for k,_,c in _TIPO_DIAG if k==t), SEC)
            def _label_cert(c):
                return next((l for k,l,_ in _CERTEZA_DIAG if k==c), c or "—")
            def _cor_cert(c):
                return next((cr for k,_,cr in _CERTEZA_DIAG if k==c), MUT)

            try:
                diags = listar_diagnosticos_internacao(inter["id"])
            except Exception:
                diags = []

            def _form_diagnostico(diag=None):
                """Overlay simples para adicionar/editar diagnostico."""
                _d = diag or {}
                tipo_s   = [_d.get("tipo","saida")]
                cert_s   = [_d.get("certeza","confirmado")]
                f_cid    = ft.TextField(
                    label="CID", value=_d.get("cid",""),
                    bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
                    label_style=ft.TextStyle(color=SEC, size=11),
                    text_style=ft.TextStyle(color=TXT), border_radius=8,
                    width=120,
                )
                f_desc   = ft.TextField(
                    label="Descricao", value=_d.get("descricao",""),
                    bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
                    label_style=ft.TextStyle(color=SEC, size=11),
                    text_style=ft.TextStyle(color=TXT), border_radius=8,
                    multiline=True, min_lines=2, expand=True,
                )
                chips_tipo = _chip_seletor([(k,l) for k,l,_ in _TIPO_DIAG], tipo_s, cor_ativa=AZUL)
                chips_cert = _chip_seletor([(k,l) for k,l,_ in _CERTEZA_DIAG], cert_s, cor_ativa=VERD)
                txt_err = ft.Text("", size=11, color=VERM, visible=False)

                def _salvar_d(e=None):
                    dados_d = {
                        "internacao_id": inter["id"],
                        "cid":           f_cid.value.strip().upper() or None,
                        "descricao":     f_desc.value.strip() or None,
                        "tipo":          tipo_s[0] or "saida",
                        "certeza":       cert_s[0] or "confirmado",
                        "fonte":         "manual",
                    }
                    if _d.get("id"):
                        dados_d["id"] = _d["id"]
                    if not dados_d["cid"] and not dados_d["descricao"]:
                        txt_err.value = "Informe CID ou descricao."
                        txt_err.visible = True
                        try: page.update()
                        except Exception: pass
                        return
                    salvar_diagnostico_internacao(dados_d)
                    _fechar_overlay()
                    _render_aba_det()

                def _excluir_d(e=None):
                    def _exec():
                        excluir_diagnostico_internacao(_d["id"])
                        _render_aba_det()
                    _confirmar_acao("Remover este diagnostico*",
                                    fn_sim=_exec,
                                    btn_label="Remover", btn_cor=VERM)

                btn_ok = ft.Container(
                    content=ft.Row([ft.Icon("check_rounded",size=13,color=BG),
                                    ft.Text("Salvar",size=12,color=BG)],
                                   spacing=4, tight=True),
                    bgcolor=AZUL, border_radius=8, ink=True,
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                )
                btn_ok.on_click = _salvar_d
                btns_row = [ft.Container(expand=True), btn_ok]
                if _d.get("id"):
                    btn_del = ft.Container(
                        content=ft.Icon("delete_outline_rounded",size=16,color=VERM),
                        ink=True, border_radius=6,
                        padding=ft.padding.symmetric(horizontal=6, vertical=6),
                        tooltip="Excluir",
                    )
                    btn_del.on_click = _excluir_d
                    btns_row.insert(0, btn_del)

                form_col = ft.Column([
                    ft.Text("Diagnostico", size=14, color=TXT, weight=ft.FontWeight.W_600),
                    ft.Container(height=4),
                    ft.Row([f_cid, f_desc], spacing=8),
                    ft.Text("Tipo", size=11, color=SEC), chips_tipo,
                    ft.Text("Certeza", size=11, color=SEC), chips_cert,
                    txt_err,
                    ft.Container(height=4),
                    ft.Row(btns_row),
                ], spacing=8, tight=True)
                _mostrar_overlay(form_col)

            # botao de adicionar diagnostico
            btn_add_d = ft.Container(
                content=ft.Row([
                    ft.Icon("add_rounded", size=13, color=AMAR),
                    ft.Text("Adicionar diagnostico", size=11, color=AMAR),
                ], spacing=4, tight=True),
                border_radius=8, ink=True, bgcolor=f"{AMAR}18",
                padding=ft.padding.symmetric(horizontal=10, vertical=7),
                border=ft.border.all(1, f"{AMAR}44"),
            )
            btn_add_d.on_click = lambda e: _form_diagnostico()
            area_det.controls.append(btn_add_d)

            if diags:
                tem_algo = True
                area_det.controls.append(ft.Text(
                    "Diagnosticos", size=11, color=MUT, weight=ft.FontWeight.W_600))
                for d in diags:
                    cor_t = _cor_tipo_d(d.get("tipo"))
                    cor_c = _cor_cert(d.get("certeza"))
                    card_d = ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Container(
                                    content=ft.Text(_label_tipo_d(d.get("tipo")),
                                                    size=10, color=cor_t,
                                                    weight=ft.FontWeight.W_600),
                                    bgcolor=f"{cor_t}22", border_radius=8,
                                    padding=ft.padding.symmetric(horizontal=7, vertical=3),
                                ),
                                ft.Container(
                                    content=ft.Text(d.get("cid") or "",
                                                    size=10, color=AMAR),
                                    bgcolor=f"{AMAR}22", border_radius=6,
                                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                    visible=bool(d.get("cid")),
                                ),
                                ft.Container(expand=True),
                                ft.Container(
                                    content=ft.Text(_label_cert(d.get("certeza")),
                                                    size=10, color=cor_c),
                                    bgcolor=f"{cor_c}18", border_radius=6,
                                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                ),
                            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            ft.Text(d.get("descricao") or "—", size=12, color=TXT),
                            ft.Text(f"Fonte: {d.get('fonte','')}", size=10, color=MUT,
                                    ) if d.get("fonte") else ft.Container(height=0),
                        ], spacing=5),
                        bgcolor=CARD, border_radius=10,
                        padding=ft.padding.all(12),
                        border=ft.border.all(1, f"{cor_t}44"),
                        ink=True,
                    )
                    def _editar_d(e, dd=d):
                        _form_diagnostico(dd)
                    card_d.on_click = _editar_d
                    area_det.controls.append(card_d)

            # ── B: Escalas clinicas (exames com laboratorio='Enfermagem') ──
            try:
                escalas = [e for e in listar_exames_internacao(inter["id"])
                           if (e.get("laboratorio") or "").lower() == "enfermagem"]
            except Exception:
                escalas = []
            if escalas:
                tem_algo = True
                area_det.controls.append(ft.Text(
                    "Escalas Clinicas", size=11, color=MUT, weight=ft.FontWeight.W_600))
                # agrupar por tipo_exame para mostrar evolucao entrada->saida
                grupos: dict[str, list] = {}
                for esc in sorted(escalas, key=lambda x: x.get("data_exame") or ""):
                    nome_esc = (esc.get("tipo_exame") or "?").strip()
                    grupos.setdefault(nome_esc, []).append(esc)
                for nome_esc, registros in grupos.items():
                    chips = []
                    for i, reg in enumerate(registros):
                        data_txt = _para_display(reg.get("data_exame",""))
                        valor_txt = (reg.get("resultado_texto") or "—").strip()
                        # primeiro = entrada (azul), ultimo = alta (verde)
                        cor_chip = AZUL if i == 0 else (VERD if i == len(registros)-1 else SEC)
                        chips.append(ft.Column([
                            ft.Text("Entrada" if i == 0 else ("Alta" if i == len(registros)-1 else data_txt),
                                    size=9, color=MUT),
                            ft.Container(
                                content=ft.Text(valor_txt, size=11, color=cor_chip,
                                                weight=ft.FontWeight.W_600),
                                bgcolor=f"{cor_chip}22", border_radius=6,
                                padding=ft.padding.symmetric(horizontal=6, vertical=3),
                            ),
                        ], spacing=2, tight=True))
                        if i < len(registros) - 1:
                            chips.append(ft.Icon("arrow_forward_rounded", size=12, color=MUT))
                    area_det.controls.append(ft.Container(
                        content=ft.Column([
                            ft.Text(nome_esc, size=12, color=TXT, weight=ft.FontWeight.W_600),
                            ft.Row(chips, spacing=6,
                                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ], spacing=6),
                        bgcolor=CARD, border_radius=10, padding=ft.padding.all(12),
                        border=ft.border.all(1, BD),
                    ))

            # ── C: Diagnosticos de enfermagem ────────────────────────
            try:
                diags_enf = [p for p in listar_procedimentos(inter["id"])
                             if p.get("tipo") == "enfermagem"]
            except Exception:
                diags_enf = []
            if diags_enf:
                tem_algo = True
                area_det.controls.append(ft.Text(
                    "Diagnosticos de Enfermagem", size=11, color=MUT,
                    weight=ft.FontWeight.W_600))
                for diag in diags_enf:
                    area_det.controls.append(ft.Container(
                        content=ft.Column([
                            ft.Text(diag["nome"], size=12, color=TXT,
                                    weight=ft.FontWeight.W_600),
                            ft.Text(diag.get("observacoes") or "", size=11, color=SEC,
                                    ) if diag.get("observacoes") else ft.Container(height=0),
                            ft.Text(_para_display(diag.get("data","")), size=10, color=MUT,
                                    ) if diag.get("data") else ft.Container(height=0),
                        ], spacing=3),
                        bgcolor=CARD, border_radius=10, padding=ft.padding.all(12),
                        border=ft.border.all(1, BD),
                    ))

            # ── D: Indicadores vitais monitorados ────────────────────
            try:
                marcadores = listar_marcadores_internacao(
                    inter["id"], inter.get("data_entrada",""), inter.get("data_saida"))
            except Exception:
                marcadores = []
            if marcadores:
                tem_algo = True
                area_det.controls.append(ft.Text(
                    "Indicadores Vitais", size=11, color=MUT, weight=ft.FontWeight.W_600))
                # agrupar por parametro — primeiro=entrada, ultimo=saida
                grupos_vital: dict[str, list] = {}
                for m in marcadores:
                    param = (m.get("parametro") or "?").strip()
                    grupos_vital.setdefault(param, []).append(m)

                def _fora_range(valor_txt, referencia):
                    """Heuristica simples: verifica se valor numerico esta fora do range 'a-b'."""
                    if not valor_txt or not referencia: return False
                    try:
                        v = float(str(valor_txt).replace(",","."))
                        ref = str(referencia).strip()
                        if "-" in ref:
                            partes = ref.split("-")
                            lo, hi = float(partes[0].strip()), float(partes[-1].strip())
                            return not (lo <= v <= hi)
                        if ref.startswith("<"):
                            return v >= float(ref[1:].strip())
                        if ref.startswith(">"):
                            return v <= float(ref[1:].strip())
                    except Exception:
                        pass
                    return False

                rows_vitais = []
                for param, leituras in grupos_vital.items():
                    primeiro = leituras[0]
                    ultimo   = leituras[-1]
                    val_ini  = (primeiro.get("valor_txt") or str(primeiro.get("valor") or "")).strip()
                    val_fim  = (ultimo.get("valor_txt") or str(ultimo.get("valor") or "")).strip()
                    unidade  = (ultimo.get("unidade") or "").strip()
                    refere   = (ultimo.get("referencia") or "").strip()
                    cor_val  = VERM if _fora_range(val_fim, refere) else VERD
                    rows_vitais.append(ft.Row([
                        ft.Text(param, size=11, color=TXT, expand=True),
                        ft.Text(val_ini or "—", size=11, color=SEC),
                        ft.Icon("arrow_forward_rounded", size=10, color=MUT),
                        ft.Text(val_fim or "—", size=11, color=cor_val,
                                weight=ft.FontWeight.W_600),
                        ft.Text(unidade, size=10, color=MUT, width=40),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER))
                area_det.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("Parametro", size=10, color=MUT, expand=True),
                            ft.Text("Entrada → Alta", size=10, color=MUT),
                            ft.Container(width=40),
                        ]),
                        ft.Divider(height=1, color=BD),
                    ] + rows_vitais, spacing=6),
                    bgcolor=CARD, border_radius=10, padding=ft.padding.all(12),
                    border=ft.border.all(1, BD),
                ))

            if not tem_algo:
                area_det.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Icon("analytics_rounded", size=32, color=MUT),
                        ft.Text("Nenhum dado clinico estruturado.", size=13, color=MUT,
                                text_align=ft.TextAlign.CENTER),
                        ft.Text("Importe o PDF desta internacao para\nextrair escalas e indicadores.",
                                size=11, color=MUT, text_align=ft.TextAlign.CENTER),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                       spacing=8, tight=True),
                    padding=ft.padding.symmetric(vertical=32),
                    alignment=ft.alignment.Alignment(0, 0),
                ))

        def _render_sinais():
            inter = _get_inter()
            if not inter: return
            from dados.model_prontuario import listar_sinais_internacao, salvar_sinal_internacao, excluir_sinal_internacao

            COR_SINAIS = "#4ECDC4"
            sinais = listar_sinais_internacao(inter["id"])

            # ── cabecalho + botao adicionar ─────────────────────
            btn_add = ft.Container(
                content=ft.Row([
                    ft.Icon("add_rounded", size=14, color=COR_SINAIS),
                    ft.Text("Adicionar sinal", size=12, color=COR_SINAIS),
                ], spacing=4, tight=True),
                border_radius=8, ink=True,
                bgcolor=f"{COR_SINAIS}18",
                border=ft.border.all(1, f"{COR_SINAIS}55"),
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            )
            btn_add.on_click = lambda e: _form_sinal()
            area_det.controls.append(btn_add)

            if not sinais:
                area_det.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Icon("vital_signs_rounded", size=32, color=MUT),
                        ft.Text("Nenhum sinal clinico registrado", size=13, color=MUT,
                                text_align="center"),
                        ft.Text("Use o script temp/extrair_sinais.py para importar do PDF",
                                size=10, color=MUT, text_align="center"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                       spacing=6, tight=True),
                    alignment=ft.alignment.center,
                    padding=ft.padding.only(top=40),
                ))
                return

            # ── agrupar por sinal para tabela entrada vs saida ──
            _COR_MOMENTO = {
                "entrada":  AZUL,
                "saida":    VERD,
                "evolucao": AMAR,
            }

            # agrupa: sinal -> {momento: [registros]}
            grupos: dict = {}
            for s in sinais:
                nome = s["sinal"]
                mom  = s["momento"] or "entrada"
                grupos.setdefault(nome, {}).setdefault(mom, []).append(s)

            # cabecalho da tabela
            def _th(txt, cor=SEC, w=None):
                return ft.Container(
                    content=ft.Text(txt, size=10, color=cor,
                                    weight=ft.FontWeight.W_600),
                    width=w,
                    padding=ft.padding.symmetric(horizontal=6, vertical=4),
                )

            area_det.controls.append(ft.Container(
                content=ft.Row([
                    _th("Sinal", TXT, w=130),
                    _th("Entrada", AZUL, w=100),
                    _th("Saida", VERD, w=100),
                    _th("Evol.", AMAR),
                ], spacing=0),
                bgcolor=BD, border_radius=ft.border_radius.only(
                    top_left=8, top_right=8),
                padding=ft.padding.symmetric(horizontal=4),
            ))

            # linhas da tabela
            for i, (nome_sinal, momentos) in enumerate(sorted(grupos.items())):
                bg_linha = CARD if i % 2 == 0 else f"{BD}88"

                def _celula(mom):
                    regs = momentos.get(mom, [])
                    if not regs:
                        return ft.Container(
                            content=ft.Text("—", size=11, color=MUT),
                            width=100,
                            padding=ft.padding.symmetric(horizontal=6, vertical=6),
                        )
                    r = regs[0]
                    partes = []
                    if r.get("valor"):
                        u = r.get("unidade") or ""
                        partes.append(f"{r['valor']} {u}".strip())
                    if r.get("interpretacao"):
                        partes.append(r["interpretacao"])
                    txt = " · ".join(partes) if partes else "—"
                    cor = _COR_MOMENTO.get(mom, SEC)
                    return ft.Container(
                        content=ft.Text(txt, size=11, color=cor,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                        max_lines=2),
                        width=100,
                        padding=ft.padding.symmetric(horizontal=6, vertical=6),
                        tooltip=txt if len(txt) > 20 else None,
                    )

                linha = ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Text(nome_sinal, size=11, color=TXT,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                            max_lines=1),
                            width=130,
                            padding=ft.padding.symmetric(horizontal=6, vertical=6),
                        ),
                        _celula("entrada"),
                        _celula("saida"),
                        _celula("evolucao"),
                    ], spacing=0),
                    bgcolor=bg_linha,
                    border=ft.border.all(1, BD),
                    ink=True,
                )
                linha.on_click = lambda e, n=nome_sinal, m=momentos: _form_sinal(nome=n, momentos=m)
                area_det.controls.append(linha)

            # ── formulario de adicionar/editar sinal ────────────
            def _form_sinal(nome: str = "", momentos: dict = None, sinal_id: int = None):
                f_sinal  = ft.TextField(
                    label="Sinal (ex: Pressao arterial, Temperatura)",
                    value=nome,
                    bgcolor=CARD, border_color=BD2, focused_border_color=COR_SINAIS,
                    label_style=ft.TextStyle(color=SEC, size=11),
                    text_style=ft.TextStyle(color=TXT), border_radius=8,
                )
                momento_sel = [None]
                chips_mom = ft.Row(spacing=6, wrap=True)

                def _sel_mom(m):
                    momento_sel[0] = m
                    for c in chips_mom.controls:
                        ativo = getattr(c, "_mom_val", None) == m
                        c.bgcolor = f"{COR_SINAIS}33" if ativo else CARD
                        c.border  = ft.border.all(1, COR_SINAIS if ativo else BD2)
                    try: page.update()
                    except Exception: pass

                for mom_val, mom_label in [("entrada","Entrada"),("saida","Alta/Saida"),("evolucao","Evolucao")]:
                    chip = ft.Container(
                        content=ft.Text(mom_label, size=11, color=TXT),
                        bgcolor=CARD, border=ft.border.all(1, BD2),
                        border_radius=16, padding=ft.padding.symmetric(horizontal=10, vertical=5),
                        ink=True,
                    )
                    chip._mom_val = mom_val
                    chip.on_click = lambda e, m=mom_val: _sel_mom(m)
                    chips_mom.controls.append(chip)

                f_valor  = ft.TextField(
                    label="Valor (ex: 120/80, 36.5, ausente)",
                    bgcolor=CARD, border_color=BD2, focused_border_color=COR_SINAIS,
                    label_style=ft.TextStyle(color=SEC, size=11),
                    text_style=ft.TextStyle(color=TXT), border_radius=8,
                )
                f_unid   = ft.TextField(
                    label="Unidade (ex: mmHg, bpm, %)",
                    bgcolor=CARD, border_color=BD2, focused_border_color=COR_SINAIS,
                    label_style=ft.TextStyle(color=SEC, size=11),
                    text_style=ft.TextStyle(color=TXT), border_radius=8,
                )
                f_interp = ft.TextField(
                    label="Interpretacao (ex: normotenso, afebril)",
                    bgcolor=CARD, border_color=BD2, focused_border_color=COR_SINAIS,
                    label_style=ft.TextStyle(color=SEC, size=11),
                    text_style=ft.TextStyle(color=TXT), border_radius=8,
                )

                def _salvar_form(e):
                    sn = (f_sinal.value or "").strip()
                    if not sn or not momento_sel[0]:
                        _snack("Preencha o sinal e selecione o momento.", VERM)
                        return
                    salvar_sinal_internacao({
                        "id":            sinal_id,
                        "internacao_id": inter["id"],
                        "sinal":         sn,
                        "momento":       momento_sel[0],
                        "valor":         (f_valor.value or "").strip() or None,
                        "unidade":       (f_unid.value or "").strip() or None,
                        "interpretacao": (f_interp.value or "").strip() or None,
                        "fonte":         "manual",
                    })
                    _fechar_overlay()
                    _render_aba_det()
                    _snack("Sinal salvo.", VERD)

                btn_sal = ft.Container(
                    content=ft.Text("Salvar", size=13, color=VERD, weight=ft.FontWeight.W_600),
                    padding=ft.padding.symmetric(horizontal=20, vertical=10),
                    border_radius=8, bgcolor=f"{VERD}22",
                    border=ft.border.all(1, f"{VERD}66"), ink=True,
                )
                btn_sal.on_click = _salvar_form

                form_col = ft.Column([
                    ft.Text("Sinal Clinico", size=14, color=TXT, weight=ft.FontWeight.W_700),
                    f_sinal,
                    ft.Text("Momento:", size=11, color=SEC),
                    chips_mom,
                    f_valor, f_unid, f_interp,
                    ft.Row([btn_sal], alignment=ft.MainAxisAlignment.END),
                ], spacing=10, tight=True, scroll=ft.ScrollMode.AUTO)

                _mostrar_overlay(form_col)

        def _render_brutos():
            inter = _get_inter()
            if not inter: return
            from telas.tela_docs_brutos import criar_tela_docs_brutos

            def _voltar_brutos():
                _render_aba_det()

            tela_docs = criar_tela_docs_brutos(
                page, _voltar_brutos, internacao_id=inter["id"], embutido=True
            )
            area_det.controls.append(
                ft.Container(content=tela_docs, expand=True,
                             margin=ft.margin.only(left=-16, right=-16, bottom=-12))
            )
            return

            # ---- código legado abaixo (não executado) ----
            from dados.model_prontuario import (listar_dados_brutos_internacao,
                                                 salvar_dado_bruto_internacao,
                                                 excluir_dado_bruto_internacao)

            _CATS_BRUTOS = [
                ("evolucao",       "Evolucao"),
                ("administrativo", "Administrativo"),
                ("outro",          "Outro"),
            ]

            try:
                brutos = listar_dados_brutos_internacao(inter["id"])
            except Exception:
                brutos = []

            def _form_bruto(b=None):
                _b = b or {}
                cat_s  = [_b.get("categoria","outro")]
                f_pag  = ft.TextField(
                    label="Pagina (opcional)", value=str(_b.get("pagina_origem","") or ""),
                    bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
                    label_style=ft.TextStyle(color=SEC, size=11),
                    text_style=ft.TextStyle(color=TXT), border_radius=8,
                    width=100, keyboard_type=ft.KeyboardType.NUMBER,
                )
                f_cont = ft.TextField(
                    label="Conteudo", value=_b.get("conteudo",""),
                    bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
                    label_style=ft.TextStyle(color=SEC, size=11),
                    text_style=ft.TextStyle(color=TXT), border_radius=8,
                    multiline=True, min_lines=3, expand=True,
                )
                chips_cat = _chip_seletor(_CATS_BRUTOS, cat_s, cor_ativa=SEC)
                txt_err   = ft.Text("", size=11, color=VERM, visible=False)

                def _salvar_b(e=None):
                    cont = f_cont.value.strip()
                    if not cont:
                        txt_err.value = "Informe o conteudo."
                        txt_err.visible = True
                        try: page.update()
                        except Exception: pass
                        return
                    pag = None
                    try: pag = int(f_pag.value.strip()) if f_pag.value.strip() else None
                    except Exception: pass
                    dados_b = {
                        "internacao_id": inter["id"],
                        "categoria":     cat_s[0] or "outro",
                        "conteudo":      cont,
                        "pagina_origem": pag,
                        "fonte":         "manual",
                    }
                    if _b.get("id"):
                        dados_b["id"] = _b["id"]
                    salvar_dado_bruto_internacao(dados_b)
                    _fechar_overlay()
                    _render_aba_det()

                def _excluir_b(e=None):
                    def _exec():
                        excluir_dado_bruto_internacao(_b["id"])
                        _render_aba_det()
                    _confirmar_acao("Remover este registro*", fn_sim=_exec,
                                    btn_label="Remover", btn_cor=VERM)

                btn_ok_b = ft.Container(
                    content=ft.Row([ft.Icon("check_rounded",size=13,color=BG),
                                    ft.Text("Salvar",size=12,color=BG)],
                                   spacing=4, tight=True),
                    bgcolor=SEC, border_radius=8, ink=True,
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                )
                btn_ok_b.on_click = _salvar_b
                btns_b = [ft.Container(expand=True), btn_ok_b]
                if _b.get("id"):
                    btn_del_b = ft.Container(
                        content=ft.Icon("delete_outline_rounded",size=16,color=VERM),
                        ink=True, border_radius=6,
                        padding=ft.padding.symmetric(horizontal=6, vertical=6),
                    )
                    btn_del_b.on_click = _excluir_b
                    btns_b.insert(0, btn_del_b)

                form_b = ft.Column([
                    ft.Text("Dado nao classificado", size=14, color=TXT,
                            weight=ft.FontWeight.W_600),
                    ft.Container(height=4),
                    ft.Row([f_pag, ft.Container(expand=True)]),
                    ft.Text("Categoria", size=11, color=SEC), chips_cat,
                    f_cont,
                    txt_err,
                    ft.Container(height=4),
                    ft.Row(btns_b),
                ], spacing=8, tight=True)
                _mostrar_overlay(form_b)

            btn_add_b = ft.Container(
                content=ft.Row([
                    ft.Icon("add_rounded", size=13, color=SEC),
                    ft.Text("Adicionar registro", size=11, color=SEC),
                ], spacing=4, tight=True),
                border_radius=8, ink=True, bgcolor=f"{SEC}18",
                padding=ft.padding.symmetric(horizontal=10, vertical=7),
                border=ft.border.all(1, f"{SEC}44"),
            )
            btn_add_b.on_click = lambda e: _form_bruto()
            area_det.controls.append(btn_add_b)

            if not brutos:
                area_det.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Icon("folder_open_rounded", size=32, color=MUT),
                        ft.Text("Nenhum dado adicional registrado.", size=13, color=MUT,
                                text_align=ft.TextAlign.CENTER),
                        ft.Text("Aqui ficam informacoes do prontuario\n"
                                "que nao se encaixam nas outras categorias.",
                                size=11, color=MUT, text_align=ft.TextAlign.CENTER),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                       spacing=8, tight=True),
                    padding=ft.padding.symmetric(vertical=32),
                    alignment=ft.alignment.Alignment(0, 0),
                ))
                return

            _LABEL_CAT = dict(_CATS_BRUTOS)
            for b in brutos:
                cat_txt = _LABEL_CAT.get(b.get("categoria","outro"), b.get("categoria",""))
                pag_txt = f"  pag. {b['pagina_origem']}" if b.get("pagina_origem") else ""
                fonte_txt = b.get("fonte","")
                card_b = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Text(cat_txt, size=10, color=SEC,
                                                weight=ft.FontWeight.W_600),
                                bgcolor=f"{SEC}22", border_radius=6,
                                padding=ft.padding.symmetric(horizontal=7, vertical=3),
                            ),
                            ft.Text(pag_txt, size=10, color=MUT),
                            ft.Container(expand=True),
                            ft.Text(fonte_txt, size=10, color=MUT),
                        ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Text(b.get("conteudo",""), size=12, color=TXT,
                                max_lines=5, overflow=ft.TextOverflow.ELLIPSIS),
                    ], spacing=5),
                    bgcolor=CARD, border_radius=10,
                    padding=ft.padding.all(12), border=ft.border.all(1, BD),
                    ink=True,
                )
                def _editar_b(e, bb=b):
                    _form_bruto(bb)
                card_b.on_click = _editar_b
                area_det.controls.append(card_b)

        def _render_evolucao():
            inter = _get_inter()
            if not inter:
                return
            import json as _json, sqlite3 as _sq3
            from dados.model_prontuario import DB_PATH

            conn = _sq3.connect(DB_PATH, timeout=20)
            rows = conn.execute("""
                SELECT id, tipo, data_registro, hora_registro, profissional,
                       quadro_clinico, observacoes, intercorrencias,
                       dispositivos, sinais_vitais, dados_extras
                FROM registros_clinicos
                WHERE internacao_id=?
                ORDER BY data_registro, hora_registro
            """, (inter["id"],)).fetchall()
            conn.close()

            _COLS = ["id","tipo","data_registro","hora_registro","profissional",
                     "quadro_clinico","observacoes","intercorrencias",
                     "dispositivos","sinais_vitais","dados_extras"]

            if not rows:
                area_det.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Icon("description_rounded", size=32, color=MUT),
                        ft.Text("Nenhum registro clinico.", size=13, color=MUT,
                                text_align=ft.TextAlign.CENTER),
                        ft.Text("Importe e processe os PDFs para ver\nevoluções e prescrições.",
                                size=11, color=MUT, text_align=ft.TextAlign.CENTER),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                       spacing=8, tight=True),
                    padding=ft.padding.symmetric(vertical=32),
                    alignment=ft.alignment.center,
                ))
                return

            _COR_TIPO = {
                "prescricao_enfermagem":        AZUL,
                "prescricao_medica":            AMAR,
                "evolucao_medica":              ROXO,
                "evolucao_enfermagem":          SEC,
                "avaliacao_riscos_enfermagem":  VERM,
                "avaliacao_riscos":             VERM,
                "ficha_admissao":               VERD,
                "ficha_transporte":             AMAR,
                "alta":                         VERD,
            }
            _LABEL_TIPO = {
                "prescricao_enfermagem":        "Prescrição Enfermagem",
                "prescricao_medica":            "Prescrição Médica",
                "evolucao_medica":              "Evolução Médica",
                "evolucao_enfermagem":          "Evolução Enfermagem",
                "avaliacao_riscos_enfermagem":  "Avaliação Riscos",
                "avaliacao_riscos":             "Avaliação Riscos",
                "ficha_admissao":               "Ficha Admissão",
                "ficha_transporte":             "Transporte",
                "alta":                         "Alta",
            }

            def _secao(icone, label, cor, controles):
                """Bloco de seção com título e conteúdo."""
                return ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(icone, size=11, color=cor),
                            ft.Text(label, size=10, color=cor,
                                    weight=ft.FontWeight.W_700),
                        ], spacing=4, tight=True),
                        ft.Container(
                            content=ft.Column(controles, spacing=4),
                            padding=ft.padding.only(left=8, top=4),
                        ),
                    ], spacing=4),
                    bgcolor=f"{cor}0D", border_radius=8,
                    padding=ft.padding.symmetric(horizontal=10, vertical=8),
                )

            def _txt(valor, cor=TXT):
                return ft.Text(str(valor), size=11, color=cor,
                               no_wrap=False, selectable=True)

            for row in rows:
                r = dict(zip(_COLS, row))
                tipo      = r["tipo"]
                cor_tipo  = _COR_TIPO.get(tipo, SEC)
                lbl_tipo  = _LABEL_TIPO.get(tipo, tipo.replace("_"," ").title())
                data_hora = f"{r['data_registro'] or ''}  {r['hora_registro'] or ''}".strip()

                secoes = []

                # a) Profissional
                if r["profissional"]:
                    secoes.append(_secao(
                        "person_rounded", "Profissional", SEC,
                        [_txt(r["profissional"], SEC)],
                    ))

                # b) Quadro clínico
                if r["quadro_clinico"]:
                    secoes.append(_secao(
                        "medical_information_rounded", "Quadro Clínico", AZUL,
                        [_txt(r["quadro_clinico"])],
                    ))

                # c) Sinais vitais
                try:
                    sv = _json.loads(r["sinais_vitais"] or "{}")
                except Exception:
                    sv = {}
                sv_items = [(k.upper(), v) for k, v in sv.items() if v and str(v) not in ("null","None")]
                if sv_items:
                    chips = [ft.Container(
                        content=ft.Column([
                            ft.Text(k, size=8, color=SEC),
                            ft.Text(str(v), size=12, color=VERM, weight=ft.FontWeight.W_700),
                        ], spacing=1, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor=f"{VERM}0D", border_radius=8,
                        padding=ft.padding.symmetric(horizontal=10, vertical=6),
                        border=ft.border.all(1, f"{VERM}33"),
                    ) for k, v in sv_items]
                    secoes.append(_secao(
                        "favorite_rounded", "Sinais Vitais", VERM,
                        [ft.Row(chips, spacing=6, wrap=True)],
                    ))

                # d) Dispositivos
                try:
                    disp = _json.loads(r["dispositivos"] or "[]")
                except Exception:
                    disp = []
                if isinstance(disp, list) and disp:
                    chips_disp = [ft.Container(
                        content=ft.Text(str(d), size=11, color=LAR),
                        bgcolor=f"{LAR}0D", border_radius=6,
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        border=ft.border.all(1, f"{LAR}33"),
                    ) for d in disp]
                    secoes.append(_secao(
                        "cable_rounded", "Dispositivos", LAR,
                        [ft.Row(chips_disp, spacing=6, wrap=True)],
                    ))

                # e) Observações
                if r["observacoes"]:
                    secoes.append(_secao(
                        "notes_rounded", "Observações", AMAR,
                        [_txt(r["observacoes"])],
                    ))

                # intercorrências
                if r["intercorrencias"] and r["intercorrencias"] not in ("None","null"):
                    secoes.append(_secao(
                        "warning_rounded", "Intercorrências", VERM,
                        [_txt(r["intercorrencias"], VERM)],
                    ))

                if not secoes:
                    secoes.append(_txt("(sem dados extraídos)", MUT))

                card_ev = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Text(lbl_tipo, size=10, color=cor_tipo,
                                                weight=ft.FontWeight.W_700),
                                bgcolor=f"{cor_tipo}22", border_radius=6,
                                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            ),
                            ft.Container(expand=True),
                            ft.Text(data_hora, size=10, color=MUT),
                        ], spacing=6),
                        ft.Divider(height=1, color=BD),
                        ft.Column(secoes, spacing=6),
                    ], spacing=8),
                    bgcolor=CARD, border_radius=12,
                    padding=ft.padding.all(12),
                    border=ft.border.all(1, f"{cor_tipo}33"),
                )
                area_det.controls.append(card_ev)

        def _render_aba_det():
            area_det.controls.clear()
            try:
                {0: _render_info, 1: _render_procs,
                 2: _render_exames, 3: _render_remedios,
                 4: _render_diagnosticos,
                 5: _render_sinais,
                 6: _render_brutos,
                 7: _render_evolucao}[_aba_det[0]]()
            except Exception as _ex_aba:
                log.exception("[DETALHE] erro render aba %d: %s", _aba_det[0], _ex_aba)
                area_det.controls.append(
                    ft.Text(f"Erro: {_ex_aba}"[:120], size=11, color=VERM))
            if _montado[0]:
                try: page.update()
                except Exception: pass

        # ── header do detalhe ────────────────────────────────────
        inter_ini = _get_inter() or {}
        dur       = _duracao(inter_ini.get("data_entrada",""), inter_ini.get("data_saida"))
        periodo   = _para_display(inter_ini.get("data_entrada",""))
        if inter_ini.get("data_saida"):
            periodo += f" — {_para_display(inter_ini['data_saida'])}"
        else:
            periodo += " — em curso"
        sub = periodo + (f"  •  {dur}" if dur else "")
        loc = (inter_ini.get("cidade") or "") + (" — " + inter_ini.get("uf") if inter_ini.get("uf") else "")
        if loc: sub += f"  •  {loc}"

        btn_voltar_det = ft.Container(
            content=ft.Row([
                ft.Icon("arrow_back", size=16, color=AZUL),
                ft.Text("Voltar", size=13, color=AZUL),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            border_radius=8, ink=True,
        )
        btn_voltar_det.on_click = lambda e: _sair(_ir_lista)

        btn_editar_det = ft.Container(
            content=ft.Icon("edit_rounded", size=18, color=AMAR),
            padding=ft.padding.all(8),
            border_radius=8, ink=True,
        )
        def _editar_det(e):
            inter = _get_inter()
            if inter:
                _form_internacao(inter, on_salvo=_reload_detalhe)
        btn_editar_det.on_click = _editar_det

        btn_excluir_det = ft.Container(
            content=ft.Icon("delete_outline_rounded", size=18, color=VERM),
            padding=ft.padding.all(8),
            border_radius=8, ink=True,
            border=ft.border.all(1, f"{VERM}44"),
        )
        def _excluir_det(e):
            inter = _get_inter()
            if not inter: return
            def _sim():
                excluir_internacao(inter["id"])
                _internacoes[0] = listar_internacoes()
                _procedimentos[0] = listar_procedimentos()
                _ir_lista()
            _confirmar_excluir(f"Excluir internacao em {inter['hospital']}?", _sim)
        btn_excluir_det.on_click = _excluir_det

        # botao de prontuario no header — Drive (verde) ou local (azul) ou ausente
        _drv_link_ini = inter_ini.get("drive_link")
        _doc_ini      = inter_ini.get("documento_local")
        _tem_doc_ini  = _tem_doc(_drv_link_ini, _doc_ini)
        _cor_doc      = VERD if _drv_link_ini else AZUL
        _ico_doc      = "cloud_done_rounded" if _drv_link_ini else "picture_as_pdf_rounded"
        btn_doc_det   = ft.Container(
            content=ft.Icon(_ico_doc, size=18, color=_cor_doc if _tem_doc_ini else MUT),
            padding=ft.padding.all(8),
            border_radius=8, ink=True,
            bgcolor=f"{_cor_doc}18" if _tem_doc_ini else "transparent",
            border=ft.border.all(1, f"{_cor_doc}44") if _tem_doc_ini else None,
            tooltip="Abrir prontuario no Drive" if _drv_link_ini
                    else ("Abrir PDF local" if _tem_doc_ini else "Sem prontuario vinculado"),
        )
        def _abrir_doc_det(e):
            inter = _get_inter()
            if not inter: return
            _abrir_doc(inter.get("drive_link"), inter.get("documento_local"))
        btn_doc_det.on_click = _abrir_doc_det

        # titulo com expand para nao empurrar botoes para fora da tela
        titulo_det = ft.Container(
            content=ft.Column([
                ft.Text(inter_ini.get("hospital",""), size=13, weight=ft.FontWeight.W_700,
                        color=TXT, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                ft.Text(sub, size=9, color=SEC, overflow=ft.TextOverflow.ELLIPSIS,
                        max_lines=1),
            ], spacing=1, tight=True),
            expand=True,
            padding=ft.padding.symmetric(horizontal=8),
        )

        # ── chat Claudia sobre esta internacao ──────────────────
        _chat_hist = []   # lista de {"role": "user"|"assistant", "text": str}

        def _montar_contexto_internacao():
            """Agrega dados do banco numa string para contexto da Claudia."""
            inter = _get_inter()
            if not inter:
                return ""
            from dados.model_prontuario import (
                listar_procedimentos, listar_exames_internacao,
                listar_diagnosticos_internacao, listar_dados_brutos_internacao,
            )
            linhas = [
                f"INTERNACAO #{inter['id']}",
                f"Hospital: {inter.get('hospital','')}",
                f"Entrada: {_para_display(inter.get('data_entrada',''))}",
                f"Alta: {_para_display(inter.get('data_saida','')) or 'Em curso'}",
                f"Tipo: {_label_tipo_inter(inter.get('tipo',''))}",
                f"Motivo: {inter.get('motivo','') or '—'}",
                f"CID entrada: {inter.get('cid_entrada','') or '—'}",
                f"Diagnostico alta: {inter.get('diagnostico_saida','') or '—'}",
                f"CID alta: {inter.get('cid_saida','') or '—'}",
                f"Observacoes: {inter.get('observacoes','') or '—'}",
                "",
            ]
            try:
                diags = listar_diagnosticos_internacao(inter["id"])
                if diags:
                    linhas.append("DIAGNOSTICOS ESTRUTURADOS:")
                    for d in diags:
                        linhas.append(f"  [{d.get('tipo','').upper()}] CID:{d.get('cid','')} — {d.get('descricao','')} ({d.get('certeza','')})")
                    linhas.append("")
            except Exception:
                pass
            try:
                procs = listar_procedimentos(inter["id"])
                if procs:
                    linhas.append("PROCEDIMENTOS:")
                    for p in procs:
                        linhas.append(f"  {_para_display(p.get('data',''))} — {p.get('nome','')} ({p.get('tipo','')})")
                        if p.get("resultado"):
                            linhas.append(f"    Resultado: {p['resultado']}")
                    linhas.append("")
            except Exception:
                pass
            try:
                exames = listar_exames_internacao(inter["id"])
                if exames:
                    linhas.append("EXAMES:")
                    for ex in exames:
                        linhas.append(f"  {_para_display(ex.get('data_exame',''))} — {ex.get('tipo_exame','')} ({ex.get('laboratorio','')})")
                        if ex.get("resultado_texto"):
                            linhas.append(f"    Resultado: {ex['resultado_texto'][:300]}")
                    linhas.append("")
            except Exception:
                pass
            try:
                brutos = listar_dados_brutos_internacao(inter["id"])
                if brutos:
                    linhas.append("DADOS ADICIONAIS:")
                    for b in brutos:
                        cat = b.get("categoria","outro")
                        pag = f" (pag.{b['pagina_origem']})" if b.get("pagina_origem") else ""
                        linhas.append(f"  [{cat.upper()}{pag}] {b.get('conteudo','')[:400]}")
                    linhas.append("")
            except Exception:
                pass
            return "\n".join(linhas)

        def _abrir_chat_claudia(e=None):
            _chat_hist.clear()
            chat_col   = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
            f_pergunta = ft.TextField(
                hint_text="Pergunte sobre esta internacao...",
                bgcolor=CARD, border_color=BD2, focused_border_color=ROXO,
                hint_style=ft.TextStyle(color=MUT, size=12),
                text_style=ft.TextStyle(color=TXT, size=13),
                border_radius=10, multiline=True, min_lines=1, max_lines=4,
                expand=True,
            )
            enviando = [False]

            def _bubble(texto, role):
                cor_bg = f"{ROXO}22" if role == "assistant" else f"{AZUL}22"
                cor_tx = TXT if role == "assistant" else TXT
                alinha = ft.CrossAxisAlignment.START if role == "assistant" else ft.CrossAxisAlignment.END
                return ft.Container(
                    content=ft.Column([
                        ft.Text("Claudia" if role == "assistant" else "Voce",
                                size=9, color=ROXO if role == "assistant" else AZUL,
                                weight=ft.FontWeight.W_600),
                        ft.Text(texto, size=12, color=cor_tx, selectable=True),
                    ], spacing=2, tight=True, horizontal_alignment=alinha),
                    bgcolor=cor_bg, border_radius=10,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    border=ft.border.all(1, f"{ROXO}44" if role == "assistant" else f"{AZUL}33"),
                )

            def _enviar_pergunta(e=None):
                pergunta = f_pergunta.value.strip()
                if not pergunta or enviando[0]:
                    return
                enviando[0] = True
                f_pergunta.value = ""
                _chat_hist.append({"role": "user", "text": pergunta})
                chat_col.controls.append(_bubble(pergunta, "user"))
                indicador = ft.Container(
                    content=ft.Row([
                        ft.ProgressRing(width=12, height=12, stroke_width=2, color=ROXO),
                        ft.Text("Claudia pensando...", size=11, color=MUT),
                    ], spacing=6, tight=True),
                    padding=ft.padding.symmetric(vertical=4),
                )
                chat_col.controls.append(indicador)
                try: page.update()
                except Exception: pass

                def _chamar():
                    try:
                        from utils.claudia_engine import get_client
                        client = get_client()
                        contexto = _montar_contexto_internacao()
                        system_msg = (
                            "Voce e Claudia, assistente medica do app Prontuario. "
                            "Responda perguntas sobre a internacao abaixo de forma clara e objetiva. "
                            "Use os dados fornecidos — nunca invente informacoes nao presentes. "
                            "Se um dado nao estiver disponivel, diga isso claramente.\n\n"
                            f"DADOS DA INTERNACAO:\n{contexto}"
                        )
                        msgs = []
                        for h in _chat_hist[:-1]:
                            msgs.append({"role": h["role"],
                                         "content": h["text"]})
                        msgs.append({"role": "user", "content": pergunta})
                        resp = client.messages.create(
                            model="claude-sonnet-4-6",
                            max_tokens=1024,
                            system=system_msg,
                            messages=msgs,
                        )
                        resposta = resp.content[0].text.strip()
                    except Exception as ex:
                        resposta = f"Erro ao consultar Claudia: {ex}"
                    page.pubsub.send_all_on_topic("_claudia_chat_resp", resposta)

                threading.Thread(target=_chamar, daemon=True).start()

            def _on_resp(resposta):
                if indicador in chat_col.controls:
                    chat_col.controls.remove(indicador)
                _chat_hist.append({"role": "assistant", "text": resposta})
                chat_col.controls.append(_bubble(resposta, "assistant"))
                enviando[0] = False
                try: page.update()
                except Exception: pass

            page.pubsub.subscribe_topic("_claudia_chat_resp", _on_resp)

            btn_env = ft.Container(
                content=ft.Icon("send_rounded", size=18, color=ROXO),
                padding=ft.padding.all(10), border_radius=10,
                bgcolor=f"{ROXO}22", ink=True,
                border=ft.border.all(1, f"{ROXO}44"),
            )
            btn_env.on_click = _enviar_pergunta
            f_pergunta.on_submit = _enviar_pergunta

            btn_fechar = ft.Container(
                content=ft.Icon("close_rounded", size=16, color=MUT),
                padding=ft.padding.all(6), border_radius=8, ink=True,
            )
            btn_fechar.on_click = lambda e: _fechar_overlay()

            inter = _get_inter()
            hosp_chat = (inter.get("hospital","") or "")[:30] if inter else ""
            overlay_chat = ft.Column([
                ft.Row([
                    ft.Icon("auto_awesome_rounded", size=16, color=ROXO),
                    ft.Text(f"Claudia — {hosp_chat}", size=13, color=TXT,
                            weight=ft.FontWeight.W_600, expand=True),
                    btn_fechar,
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Divider(height=1, color=BD),
                ft.Container(content=chat_col, expand=True, height=340),
                ft.Divider(height=1, color=BD),
                ft.Row([f_pergunta, btn_env], spacing=8,
                       vertical_alignment=ft.CrossAxisAlignment.END),
            ], spacing=8, tight=True)
            _mostrar_overlay(overlay_chat)

        btn_claudia_det = ft.Container(
            content=ft.Icon("auto_awesome_rounded", size=18, color=ROXO),
            padding=ft.padding.all(8), border_radius=8, ink=True,
            tooltip="Perguntar a Claudia sobre esta internacao",
        )
        btn_claudia_det.on_click = _abrir_chat_claudia

        header_det = ft.Container(
            content=ft.Row(
                [btn_voltar_det, titulo_det,
                 ft.Row([btn_claudia_det, btn_excluir_det, btn_editar_det],
                        spacing=4, tight=True)],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=lay.cabecalho_padding(),
            border=ft.Border(bottom=ft.BorderSide(1, BD)),
        )

        corpo_det = ft.Column([
            ft.Container(height=lay.spacer_topo, bgcolor=BG),
            header_det,
            ft.Container(content=barra_det, border=ft.Border(bottom=ft.BorderSide(1, BD))),
            ft.Container(content=area_det, padding=ft.padding.all(16), expand=True),
        ], expand=True, spacing=0)

        _montado_orig = _montado[0]
        _montado[0] = False   # evita page.update() antes de montar na arvore
        _rebuild_abas_det()
        _render_aba_det()
        _montado[0] = _montado_orig

        return ft.Container(bgcolor=BG, expand=True, content=corpo_det)

    # ── referencia ao corpo principal (para _ir_lista) ───────────
    _corpo_lista = [None]

    _OBJETIVO_INTER = [
        ("tratamento",   "Tratamento"),
        ("procedimento", "Procedimento"),
        ("diagnostico",  "Diagnostico"),
        ("emergencia",   "Emergencia"),
    ]

    def _form_internacao(internacao=None, novo_de_extracao=False, on_salvo=None):
        editando  = internacao is not None and not novo_de_extracao
        doc_local = [""]
        if internacao:
            doc_local[0] = internacao.get("documento_local", "") or ""

        # pre-preencher usando `internacao` (tanto edicao quanto extracao)
        _v = lambda key, fallback="": (internacao.get(key) or fallback) if internacao else fallback

        med_id_sel = [str(internacao["medico_id"]) if (internacao and internacao.get("medico_id")) else None]
        valor_med  = _nome_medico(internacao.get("medico_id")) if internacao else ""
        tipo_sel    = [_v("tipo", "eletiva")]
        obj_sel     = [_v("objetivo", "tratamento")]

        from shared.date_field import campo_data
        from dados.model_prontuario import normalizar_data

        f_hospital  = _tf("Hospital / Unidade *", _v("hospital"), expand=True)
        row_entrada, f_entrada = campo_data(
            page, "Data de entrada", value=_v("data_entrada"),
            obrigatorio=True, cor_acento=AZUL)
        row_saida, f_saida = campo_data(
            page, "Data de saida", value=_v("data_saida"),
            obrigatorio=False, cor_acento=VERD)
        f_cidade    = _tf("Cidade", _v("cidade"), expand=True)
        f_uf        = _tf("UF", _v("uf"), hint="ES / SP / RJ...", expand=True)
        f_motivo    = _tf("Motivo da internacao", _v("motivo"),
                          multiline=True, altura=True)
        f_cid_ent   = _tf("CID de entrada", _v("cid_entrada"),
                          hint="Ex: K35 - Apendicite")
        f_diag_saida = _tf("Diagnostico de saida", _v("diagnostico_saida"),
                           multiline=True, altura=True)
        f_cid_saida  = _tf("CID de saida", _v("cid_saida"),
                           hint="Ex: K37 - Apendicite cronica")
        f_obs        = _tf("Observacoes", _v("observacoes"),
                           multiline=True, altura=True)

        col_medico  = _campo_medico(page, _medicos[0], med_id_sel, valor_med)
        chips_tipo    = _chip_seletor([(v, l) for v, l, _ in _TIPO_INTER], tipo_sel)
        chips_obj     = _chip_seletor(_OBJETIVO_INTER, obj_sel, cor_ativa=ROXO)

        txt_erro = ft.Text("", size=11, color=VERM, visible=False)

        def _salvar(e):
            if not f_hospital.value.strip():
                txt_erro.value = "Hospital obrigatorio."
                txt_erro.visible = True
                try: page.update()
                except Exception: pass
                return
            if not f_entrada.value.strip():
                txt_erro.value = "Data de entrada obrigatoria."
                txt_erro.visible = True
                try: page.update()
                except Exception: pass
                return
            dados = {
                "hospital":          f_hospital.value.strip(),
                "medico_id":         int(med_id_sel[0]) if med_id_sel[0] else None,
                "data_entrada":      normalizar_data(f_entrada.value.strip()) or f_entrada.value.strip(),
                "data_saida":        normalizar_data(f_saida.value.strip()) or None,
                "tipo":              tipo_sel[0],
                "objetivo":          obj_sel[0],
                "cidade":            f_cidade.value.strip() or None,
                "uf":                f_uf.value.strip().upper() or None,
                "motivo":            f_motivo.value.strip() or None,
                "cid_entrada":       f_cid_ent.value.strip() or None,
                "diagnostico_saida": f_diag_saida.value.strip() or None,
                "cid_saida":         f_cid_saida.value.strip() or None,
                "observacoes":       f_obs.value.strip() or None,
                "documento_local":   doc_local[0] or None,
            }
            if internacao and internacao.get("id"):
                dados["id"] = internacao["id"]
            try:
                salvar_internacao(dados)
                _internacoes[0] = listar_internacoes()
                _fechar_overlay()
                _rebuild_lista()
                if on_salvo:
                    on_salvo()
                _status_banco[0] = "em_edicao"
                _sync()
            except Exception as ex:
                txt_erro.value = str(ex)
                txt_erro.visible = True
                try: page.update()
                except Exception: pass

        # Linha do documento PDF vinculado
        doc_nome = os.path.basename(doc_local[0]) if doc_local[0] else ""
        linha_doc = ft.Row([
            ft.Icon("attach_file_rounded", size=13, color=AZUL if doc_nome else MUT),
            ft.Text(doc_nome if doc_nome else "Sem documento vinculado",
                    size=11, color=AZUL if doc_nome else MUT,
                    overflow=ft.TextOverflow.ELLIPSIS, expand=True),
        ], spacing=6) if (doc_local[0] or novo_de_extracao) else ft.Container(height=0)

        titulo = ("Nova Internacao (Claudia)" if novo_de_extracao
                  else "Nova Internacao" if not editando
                  else "Editar Internacao")

        # ── cabecalho: Voltar | Titulo | Claudia ──────────────────
        btn_voltar_form = ft.Container(
            content=ft.Row([
                ft.Icon("arrow_back", size=16, color=AZUL),
                ft.Text("Voltar", size=13, color=AZUL),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            border_radius=8, ink=True,
        )
        btn_voltar_form.on_click = lambda e: _fechar_overlay()

        # botao de prontuario no cabecalho do form (so se existe documento)
        _drv_link_form = internacao.get("drive_link") if internacao else None
        _doc_form      = internacao.get("documento_local") if internacao else None
        _tem_doc_form  = _tem_doc(_drv_link_form, _doc_form)
        _cor_doc_form  = VERD if _drv_link_form else AZUL
        _ico_doc_form  = "cloud_done_rounded" if _drv_link_form else "picture_as_pdf_rounded"
        btn_doc_form   = ft.Container(
            content=ft.Icon(_ico_doc_form, size=18,
                            color=_cor_doc_form if _tem_doc_form else MUT),
            padding=ft.padding.all(8),
            border_radius=8, ink=True,
            bgcolor=CARD if _tem_doc_form else "transparent",
            border=ft.border.all(1, f"{_cor_doc_form}55") if _tem_doc_form else None,
            tooltip="Abrir prontuario no Drive" if _drv_link_form
                    else ("Abrir PDF local" if _tem_doc_form else "Sem prontuario vinculado"),
            visible=editando and _tem_doc_form,
        )
        btn_doc_form.on_click = lambda e: _abrir_doc(_drv_link_form, _doc_form)

        cabecalho_items = [
            btn_voltar_form,
            ft.Container(
                content=ft.Text(titulo, size=14, color=TXT, weight=ft.FontWeight.W_700,
                                overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                expand=True,
                padding=ft.padding.symmetric(horizontal=4),
            ),
            btn_doc_form,
        ]

        btn_salvar_bottom = ft.Container(
            content=ft.Row([
                ft.Icon("save_rounded", size=14, color=AZUL),
                ft.Text("Salvar", size=13, color=AZUL, weight=ft.FontWeight.W_600),
            ], spacing=6, tight=True),
            bgcolor=f"{AZUL}22",
            border=ft.border.all(1, f"{AZUL}55"),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
        )
        btn_salvar_bottom.on_click = _salvar

        # UF fica pequeno (80px) ao lado de Cidade que expande
        f_uf.expand   = False
        f_uf.width    = 80
        f_cidade.expand = True

        form = ft.Column([
            ft.Row(cabecalho_items,
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Divider(height=1, color=BD),
            ft.Text("Tipo", size=11, color=SEC),
            chips_tipo,
            ft.Text("Objetivo", size=11, color=SEC),
            chips_obj,
            ft.Container(height=4),
            f_hospital,
            ft.Row([f_cidade, f_uf], spacing=8),
            row_entrada,
            row_saida,
            ft.Text("Medico responsavel", size=11, color=SEC),
            col_medico,
            f_motivo,
            f_obs,
            ft.Divider(height=1, color=BD),
            f_cid_ent,
            f_diag_saida,
            f_cid_saida,
            linha_doc,
            txt_erro,
            ft.Container(height=6),
            ft.Row([btn_salvar_bottom], spacing=8, alignment=ft.MainAxisAlignment.END),
        ], spacing=10, scroll=ft.ScrollMode.AUTO)

        _mostrar_overlay(form)

    # ── form procedimento ─────────────────────────────────────────

    def _form_procedimento(procedimento=None, on_salvo=None):
        editando = procedimento is not None and bool(procedimento.get("id"))

        # captura a tela anterior para o botao Voltar restaurar
        _prev = list(_tela_wrapper.controls)

        def _voltar_proc():
            _tela_wrapper.controls.clear()
            _tela_wrapper.controls.extend(_prev)
            if _montado[0]:
                try: page.update()
                except Exception: pass

        med_id_sel   = [str(procedimento["medico_id"]) if (procedimento and procedimento.get("medico_id")) else None]
        valor_med    = _nome_medico(procedimento.get("medico_id")) if procedimento else ""
        tipo_sel     = [procedimento.get("tipo","cirurgico") if procedimento else "cirurgico"]
        anest_sel    = [procedimento.get("anestesia","sem") if procedimento else "sem"]
        inter_id_sel = [procedimento.get("internacao_id") if procedimento else None]

        f_nome      = _tf("Nome do procedimento *",
                          procedimento.get("nome","") if procedimento else "")
        f_data      = _tf("Data *",
                          procedimento.get("data","") if procedimento else "",
                          hint="DD/MM/AAAA")
        f_hora      = _tf("Hora",
                          procedimento.get("hora","") if procedimento else "",
                          hint="HH:MM")
        f_local     = _tf("Local / Hospital",
                          procedimento.get("local","") if procedimento else "")
        f_cid       = _tf("CID / Codigo",
                          procedimento.get("cid","") if procedimento else "")
        f_resultado = _tf("Resultado / Relatorio",
                          procedimento.get("resultado","") if procedimento else "",
                          multiline=True, altura=True)
        f_obs       = _tf("Observacoes",
                          procedimento.get("observacoes","") if procedimento else "",
                          multiline=True, altura=True)

        col_medico  = _campo_medico(page, _medicos[0], med_id_sel, valor_med)
        chips_tipo  = _chip_seletor([(v, l) for v, l, _ in _TIPO_PROC], tipo_sel)
        chips_anest = _chip_seletor(_ANESTESIA, anest_sel)

        inter_options = [ft.dropdown.Option(key="", text="Nenhuma (ambulatorial)")]
        for it in _internacoes[0]:
            inter_options.append(ft.dropdown.Option(
                key=str(it["id"]),
                text=f"{it['hospital']} ({it.get('data_entrada','')})",
            ))
        dd_inter = ft.Dropdown(
            label="Internacao vinculada",
            bgcolor=CARD, border_color=BD2, focused_border_color=AZUL,
            label_style=ft.TextStyle(color=SEC, size=11),
            text_style=ft.TextStyle(color=TXT),
            border_radius=8,
            value=str(inter_id_sel[0]) if inter_id_sel[0] else "",
            options=inter_options,
        )
        def _dd_inter_change(e):
            v = dd_inter.value
            inter_id_sel[0] = int(v) if v else None
        dd_inter.on_change = _dd_inter_change

        txt_erro = ft.Text("", size=11, color=VERM, visible=False)

        def _salvar(e):
            if not f_nome.value.strip():
                txt_erro.value = "Nome do procedimento obrigatorio."
                txt_erro.visible = True
                try: page.update()
                except Exception: pass
                return
            if not f_data.value.strip():
                txt_erro.value = "Data obrigatoria."
                txt_erro.visible = True
                try: page.update()
                except Exception: pass
                return
            dados = {
                "internacao_id": inter_id_sel[0],
                "medico_id":     int(med_id_sel[0]) if med_id_sel[0] else None,
                "nome":          f_nome.value.strip(),
                "tipo":          tipo_sel[0],
                "data":          f_data.value.strip(),
                "hora":          f_hora.value.strip() or None,
                "local":         f_local.value.strip() or None,
                "anestesia":     anest_sel[0],
                "cid":           f_cid.value.strip() or None,
                "resultado":     f_resultado.value.strip() or None,
                "observacoes":   f_obs.value.strip() or None,
            }
            if editando:
                dados["id"] = procedimento["id"]
            try:
                salvar_procedimento(dados)
                _procedimentos[0] = listar_procedimentos()
                _voltar_proc()
                if on_salvo:
                    on_salvo()
                else:
                    _rebuild_lista()
                _status_banco[0] = "em_edicao"
                _sync()
            except Exception as ex:
                txt_erro.value = str(ex)
                txt_erro.visible = True
                try: page.update()
                except Exception: pass

        def _excluir(e):
            def _sim():
                excluir_procedimento(procedimento["id"])
                _procedimentos[0] = listar_procedimentos()
                _voltar_proc()
                if on_salvo:
                    on_salvo()
                else:
                    _rebuild_lista()
            _confirmar_excluir(f"Excluir procedimento '{procedimento['nome']}'?", _sim)

        # ── cabecalho padrao ← Voltar | Titulo | Acoes ──────────────
        titulo_proc = "Procedimento" if not editando else "Editar Procedimento"

        btn_voltar_proc = ft.Container(
            content=ft.Row([
                ft.Icon("arrow_back", size=16, color=AZUL),
                ft.Text("Voltar", size=13, color=AZUL),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            border_radius=8, ink=True,
        )
        btn_voltar_proc.on_click = lambda e: _sair(_voltar_proc)

        btn_salvar_cab = ft.Container(
            content=ft.Row([
                ft.Icon("save_rounded", size=14, color=AZUL),
                ft.Text("Salvar", size=13, color=AZUL, weight=ft.FontWeight.W_600),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            border_radius=8, ink=True,
        )
        btn_salvar_cab.on_click = _salvar

        acoes_cab = [btn_salvar_cab]
        if editando:
            btn_del_cab = ft.Container(
                content=ft.Icon("delete_outline_rounded", size=18, color=VERM),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                border_radius=8, ink=True,
                border=ft.border.all(1, f"{VERM}44"),
            )
            btn_del_cab.on_click = _excluir
            acoes_cab = [btn_del_cab, btn_salvar_cab]

        titulo_col = ft.Column([
            ft.Text(titulo_proc, size=14, weight=ft.FontWeight.W_700, color=TXT),
        ], spacing=0, tight=True)

        header_proc = ft.Container(
            content=ft.Row(
                [btn_voltar_proc, titulo_col,
                 ft.Row(acoes_cab, spacing=4, tight=True)],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=lay.cabecalho_padding(),
            border=ft.Border(bottom=ft.BorderSide(1, BD)),
        )

        area_proc = ft.Column([
            f_nome,
            ft.Text("Tipo", size=11, color=SEC),
            chips_tipo,
            ft.Row([f_data, f_hora], spacing=8),
            f_local,
            ft.Text("Anestesia", size=11, color=SEC),
            chips_anest,
            ft.Text("Medico executor", size=11, color=SEC),
            col_medico,
            dd_inter,
            f_cid,
            f_resultado,
            f_obs,
            txt_erro,
        ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

        corpo_proc = ft.Column([
            ft.Container(height=lay.spacer_topo, bgcolor=BG),
            header_proc,
            ft.Container(content=area_proc,
                         padding=ft.padding.all(16), expand=True),
        ], expand=True, spacing=0)

        _tela_wrapper.controls.clear()
        _tela_wrapper.controls.append(ft.Container(bgcolor=BG, expand=True,
                                                    content=corpo_proc))
        if _montado[0]:
            try: page.update()
            except Exception: pass

    # ── botoes de acao ────────────────────────────────────────────

    btn_novo = ft.Container(
        content=ft.Row([
            ft.Icon("add_rounded", size=16, color=VERD),
            ft.Text("Novo", size=13, color=VERD),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        border_radius=8, ink=True,
    )

    icone_filtro = ft.Icon("filter_list_rounded", size=15, color=SEC)
    txt_filtro   = ft.Text("Filtro", size=12, color=SEC)
    btn_filtro   = ft.Container(
        content=ft.Row([icone_filtro, txt_filtro], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        border_radius=8, ink=True,
        tooltip="Filtrar internacoes",
    )

    btn_novo.on_click   = lambda e: _form_internacao()
    btn_filtro.on_click = lambda e: _abrir_filtro()

    # ── layout ────────────────────────────────────────────────────

    _btn_voltar = ft.Container(
        content=ft.Row([
            ft.Icon("arrow_back", size=16, color=AZUL),
            ft.Text("Voltar", size=13, color=AZUL),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        border_radius=8, ink=True,
    )
    _btn_voltar.on_click = lambda e: _sair(voltar_fn)

    _titulo_cab = ft.Row([
        ft.Icon("local_hospital_rounded", size=15, color=AZUL),
        ft.Text("Internacoes", size=14, weight=ft.FontWeight.W_700, color=TXT),
    ], spacing=6, tight=True)

    cabecalho = ft.Container(
        content=ft.Row(
            [_btn_voltar, _titulo_cab, ft.Row([btn_filtro, btn_novo], spacing=4, tight=True)],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=lay.cabecalho_padding(),
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
    )

    # ── banner de importacoes pendentes ──────────────────────────
    _banner_pend = ft.Container(visible=False)

    def _mostrar_banner_pendente(pendentes: list):
        if not pendentes:
            _banner_pend.visible = False
            try: page.update()
            except Exception: pass
            return

        p = pendentes[0]  # mostra o mais recente
        fase_label = {
            0: "registrado",
            1: "paginas salvas — aguarda identificar datas",
            2: "datas identificadas — aguarda linha do tempo",
            3: "linha do tempo criada",
        }.get(p["fase_atual"], f"fase {p['fase_atual']}")
        txt_nome  = (p["nome_arquivo"] or "")[:28]
        pend_loc  = p["pendente_local"]
        pend_drv  = p["pendente_drive"]
        pend_cls  = p["classificado"]
        n_outros  = len(pendentes) - 1

        msg_detalhe = []
        if pend_loc:  msg_detalhe.append(f"{pend_loc} aguard. Drive")
        if pend_drv:  msg_detalhe.append(f"{pend_drv} aguard. classif.")
        if pend_cls:  msg_detalhe.append(f"{pend_cls} aguard. gravar")
        detalhe_txt = " · ".join(msg_detalhe) if msg_detalhe else fase_label

        btn_continuar = ft.Container(
            content=ft.Text("Continuar", size=11, color=BG, weight=ft.FontWeight.W_600),
            bgcolor=AMAR, border_radius=6,
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            ink=True,
        )
        btn_reiniciar = ft.Container(
            content=ft.Text("Reiniciar", size=11, color=SEC),
            border_radius=6,
            padding=ft.padding.symmetric(horizontal=8, vertical=5),
            ink=True,
        )
        btn_ignorar = ft.Container(
            content=ft.Icon("close", size=14, color=MUT),
            padding=ft.padding.all(4), ink=True, border_radius=4,
        )

        def _ao_continuar(_):
            _banner_pend.visible = False
            try: page.update()
            except Exception: pass
            _retomar_importacao(p)

        def _ao_reiniciar(_):
            _banner_pend.visible = False
            try: page.update()
            except Exception: pass
            _cancelar_importacao(p["id"])
            _snack("Importacao reiniciada — selecione o PDF novamente.", AMAR)

        def _ao_ignorar(_):
            _banner_pend.visible = False
            try: page.update()
            except Exception: pass

        btn_continuar.on_click = _ao_continuar
        btn_reiniciar.on_click = _ao_reiniciar
        btn_ignorar.on_click   = _ao_ignorar

        linha_extra = []
        if n_outros > 0:
            linha_extra.append(ft.Text(f"+ {n_outros} outra(s)", size=10, color=MUT))

        _banner_pend.content = ft.Column([
            ft.Row([
                ft.Icon("hourglass_top_rounded", size=14, color=AMAR),
                ft.Column([
                    ft.Text(txt_nome, size=12, color=TXT, weight=ft.FontWeight.W_600),
                    ft.Text(detalhe_txt, size=10, color=SEC),
                ] + linha_extra, spacing=1, tight=True),
                ft.Row([btn_continuar, btn_reiniciar, btn_ignorar], spacing=4, tight=True),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=0)
        _banner_pend.bgcolor   = "#1C2128"
        _banner_pend.border    = ft.border.all(1, AMAR)
        _banner_pend.border_radius = 8
        _banner_pend.padding   = ft.padding.symmetric(horizontal=12, vertical=8)
        _banner_pend.visible   = True
        try: page.update()
        except Exception: pass

    def _retomar_importacao(p: dict):
        """Continua uma importacao do ponto onde parou, baseado em fase_atual."""
        imp_id = p["id"]
        fase   = p["fase_atual"]

        _banner_pend.visible = False
        try: page.update()
        except Exception: pass

        # fase 1 concluida → retomar na fase 2
        if fase == 1:
            _iniciar_fase2(imp_id)
        # fase 2 concluida → retomar na fase 3
        elif fase == 2:
            _iniciar_fase3(imp_id)
        # fase 3 concluida → mostrar resultado (proxima fase ainda nao implementada)
        elif fase == 3:
            import sqlite3 as _sq
            from dados.model_prontuario import DB_PATH
            with _sq.connect(DB_PATH) as _c:
                linhas = _c.execute("""
                    SELECT data_doc, total_paginas FROM linha_do_tempo
                    WHERE importacao_id=? ORDER BY data_doc
                """, (imp_id,)).fetchall()
            _mostrar_resultado_fase3(imp_id, linhas)
        else:
            _snack(f"Importacao fase={fase} sem proxima acao definida.", AMAR)

    def _cancelar_importacao(importacao_id: int):
        """Remove registros desta importacao do banco para poder reimportar."""
        try:
            import sqlite3 as _sq
            from dados.model_prontuario import DB_PATH
            with _sq.connect(DB_PATH) as _c:
                _c.execute("DELETE FROM pdf_paginas WHERE importacao_id=?", (importacao_id,))
                _c.execute("DELETE FROM importacoes_pdf WHERE id=?", (importacao_id,))
        except Exception as ex:
            log.warning("[CANCELAR] %s", ex)

    area_scroll = ft.Container(
        content=area_lista,
        padding=lay.padding_tela() if hasattr(lay, "padding_tela") else ft.padding.all(16),
        expand=True,
    )

    corpo = ft.Column([
        ft.Container(height=lay.spacer_topo, bgcolor=BG),
        cabecalho,
        _banner_pend,
        area_scroll,
    ], expand=True, spacing=0)

    _rebuild_lista()

    _montado[0] = True

    # verificar importacoes pendentes ao montar a tela
    def _checar_pendentes_async():
        try:
            from utils.processador_pdf import importacoes_pendentes
            pend = importacoes_pendentes()
            if pend:
                _mostrar_banner_pendente(pend)
        except Exception:
            pass
    threading.Thread(target=_checar_pendentes_async, daemon=True).start()

    _corpo_lista[0] = ft.Container(bgcolor=BG, expand=True, content=corpo)
    _tela_wrapper.controls.append(_corpo_lista[0])
    _registrar_voltar_hw()

    return lay.wrap(_tela_wrapper) if hasattr(lay, "wrap") else _tela_wrapper


def _verificar_pendentes():
    """Nao faz nada visualmente — apenas log. A UI chama explicitamente quando necessario."""
    try:
        from utils.processador_pdf import importacoes_pendentes
        pend = importacoes_pendentes()
        if pend:
            import logging
            logging.getLogger(__name__).info(
                "[PENDENTES] %d importacao(oes) aguardando continuacao: %s",
                len(pend),
                [f"{p['nome_arquivo']} fase={p['fase_atual']}" for p in pend],
            )
    except Exception:
        pass
