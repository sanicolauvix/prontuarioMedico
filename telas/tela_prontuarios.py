# -*- coding: utf-8 -*-
# KOIOS v1.0 | telas/tela_prontuarios.py
"""
Lista de prontuarios importados.
Click no prontuario → lista de paginas com data e thumbnail.
Importacao de PDF (Fase 1 → 2 → 3) feita aqui.
"""
import flet as ft
import sqlite3
import os
import logging
import datetime
import threading

log = logging.getLogger(__name__)

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"; BD2 = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"
AZUL = "#58A6FF"; VERD = "#3FB950"; LAR = "#F0883E"
AMAR = "#D29922"; VERM = "#DA3633"; ROXO = "#BC8CFF"


def _para_display(s: str | None) -> str:
    if not s:
        return "—"
    try:
        return datetime.datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return s


def _listar_prontuarios(db_path: str) -> list:
    with sqlite3.connect(db_path, timeout=30) as con:
        rows = con.execute("""
            SELECT p.id, p.nome_arquivo, p.total_paginas,
                   p.data_inicio, p.data_fim, p.criado_em,
                   i.fase_atual, p.hospital, p.plano,
                   (SELECT COUNT(*) FROM prontuario_paginas pp
                    WHERE pp.prontuario_id = p.id
                      AND pp.ignorado = 0
                      AND (pp.status = 'pendente'
                           OR (pp.status IS NULL AND pp.data_pagina IS NULL))) AS n_pendentes
            FROM prontuarios p
            LEFT JOIN importacoes_pdf i ON i.id = p.importacao_id
            ORDER BY p.criado_em DESC
        """).fetchall()
    return [
        {
            "id": r[0], "nome": r[1] or "sem nome",
            "total": r[2] or 0,
            "data_inicio": r[3], "data_fim": r[4],
            "criado_em": r[5], "fase": r[6],
            "hospital": r[7], "plano": r[8],
            "n_pendentes": r[9] or 0,
        }
        for r in rows
    ]


def _listar_paginas(db_path: str, prontuario_id: int) -> list:
    with sqlite3.connect(db_path, timeout=30) as con:
        rows = con.execute("""
            SELECT id, pagina_num, data_pagina, jpeg_local, pdf_local,
                   resumo, pdf_pagina_id, dados_json, ignorado,
                   COALESCE(status, CASE WHEN ignorado=1 THEN 'ignorado'
                                         WHEN data_pagina IS NOT NULL THEN 'ok'
                                         ELSE 'pendente' END) AS status,
                   jpeg_drive_id, internacao_id
            FROM prontuario_paginas
            WHERE prontuario_id=?
            ORDER BY pagina_num
        """, (prontuario_id,)).fetchall()
    return [
        {
            "id": r[0], "num": r[1], "data": r[2],
            "jpeg": r[3], "pdf": r[4], "resumo": r[5],
            "pdf_pagina_id": r[6], "dados_json": r[7],
            "ignorado": bool(r[8]), "status": r[9],
            "jpeg_drive_id": r[10], "internacao_id": r[11],
        }
        for r in rows
    ]


# ══════════════════════════════════════════════════════════════════════════════

def criar_tela_prontuarios(page: ft.Page, voltar_fn=None):
    from dados.model_prontuario import DB_PATH

    _vista = ["lista"]          # "lista" | "paginas"
    _pron_sel = [None]          # prontuario dict selecionado

    # ── overlay ──────────────────────────────────────────────────────────────
    _overlay = ft.Container(
        visible=False, expand=True,
        bgcolor="#0D1117EE",
        alignment=ft.alignment.center,
    )

    def _mostrar_overlay(conteudo):
        _overlay.content = ft.Container(
            content=conteudo,
            bgcolor=CARD, border_radius=16,
            padding=ft.padding.symmetric(horizontal=20, vertical=24),
            width=320,
            border=ft.border.all(1, BD2),
        )
        _overlay.visible = True
        try: page.update()
        except Exception: pass

    def _fechar_overlay():
        _overlay.visible = False
        try: page.update()
        except Exception: pass

    def _snack(msg, cor=None):
        page.snack_bar = ft.SnackBar(
            ft.Text(msg, color=BG if cor else TXT),
            bgcolor=cor or CARD,
        )
        page.snack_bar.open = True
        try: page.update()
        except Exception: pass

    # ── FilePicker ────────────────────────────────────────────────────────────
    _picker = ft.FilePicker()
    page.overlay.append(_picker)

    # ── importação PDF ────────────────────────────────────────────────────────
    def _mesclar_pdfs(caminhos: list) -> tuple:
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

    def _importar_pdf():
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
                    import sqlite3 as _sq

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
                    r = separar_pdf(
                        pdf_bytes if not arquivo_local else arquivo_local,
                        internacao_ids=[0],
                        db_path=DB_PATH,
                        on_progress=lambda p, t, m: _prog(f"Pag {p}/{t}"),
                    )
                    imp_id = r["importacao_id"]
                    total  = r["total"]

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
                    btn_f = ft.Container(
                        content=ft.Text("Fechar", size=13, color=SEC),
                        border_radius=8, ink=True,
                        padding=ft.padding.symmetric(horizontal=16, vertical=10),
                        border=ft.border.all(1, BD),
                    )
                    btn_f.on_click = lambda _: _fechar_overlay()
                    _mostrar_overlay(ft.Column([
                        ft.Icon("error_outline_rounded", size=36, color=VERM),
                        ft.Container(height=6),
                        ft.Text("Erro na separacao", size=14, color=TXT,
                                weight=ft.FontWeight.W_700),
                        ft.Text(str(ex)[:250], size=12, color=SEC,
                                text_align=ft.TextAlign.CENTER),
                        ft.Container(height=12),
                        btn_f,
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                       tight=True, spacing=4))

            threading.Thread(target=_fase1, daemon=True).start()

        _picker.on_result = _on_picked
        _picker.pick_files(allowed_extensions=["pdf"], allow_multiple=True)

    def _mostrar_resultado_fase1(imp_id, total, salvos, nome_base, arquivo_local):
        import sqlite3 as _sq
        with _sq.connect(DB_PATH) as _c:
            row = _c.execute(
                "SELECT jpeg_local FROM pdf_paginas WHERE importacao_id=? LIMIT 1",
                (imp_id,)
            ).fetchone()
        pasta = os.path.dirname(row[0]) if row and row[0] else "?"

        btn_fechar = ft.Container(
            content=ft.Text("Fechar", size=12, color=SEC),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.all(1, BD),
        )
        btn_continuar = ft.Container(
            content=ft.Row([
                ft.Icon("play_arrow_rounded", size=15, color=BG),
                ft.Text("Continuar — Fase 2", size=12, color=BG,
                        weight=ft.FontWeight.W_600),
            ], spacing=4, tight=True),
            bgcolor=AZUL, border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
        )
        btn_fechar.on_click    = lambda _: _fechar_overlay()
        btn_continuar.on_click = lambda _: (_fechar_overlay(), _iniciar_fase2(imp_id))

        _mostrar_overlay(ft.Column([
            ft.Icon("check_circle_outline_rounded", size=32, color=VERD),
            ft.Container(height=6),
            ft.Text("Fase 1 concluida", size=14, color=TXT,
                    weight=ft.FontWeight.W_700),
            ft.Text(f"{salvos} de {total} paginas salvas", size=12, color=SEC,
                    text_align=ft.TextAlign.CENTER),
            ft.Text(pasta[:48], size=10, color=MUT, text_align=ft.TextAlign.CENTER),
            ft.Container(height=12),
            ft.Row([btn_fechar, btn_continuar], spacing=8,
                   alignment=ft.MainAxisAlignment.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True, spacing=4, width=280))

    def _excluir_prontuario(pron_id: int):
        import sqlite3 as _sq
        try:
            with _sq.connect(DB_PATH) as _c:
                # buscar importacao_id para limpar tabelas relacionadas
                row = _c.execute(
                    "SELECT importacao_id FROM prontuarios WHERE id=?", (pron_id,)
                ).fetchone()
                imp_id = row[0] if row else None

                _c.execute("DELETE FROM prontuario_paginas WHERE prontuario_id=?", (pron_id,))
                _c.execute("DELETE FROM prontuarios WHERE id=?", (pron_id,))
                if imp_id:
                    _c.execute("DELETE FROM linha_do_tempo WHERE importacao_id=?", (imp_id,))
                    _c.execute("DELETE FROM pdf_paginas WHERE importacao_id=?", (imp_id,))
                    _c.execute("DELETE FROM importacoes_pdf WHERE id=?", (imp_id,))

            _snack("Prontuario excluido.", VERM)
        except Exception as ex:
            log.error("[DELETE_PRON] %s", ex)
            _snack(str(ex)[:120], VERM)
        _rebuild()

    def _iniciar_fase2(imp_id: int):
        import sqlite3 as _sq
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
        total_pags = info[2] if info else len(pag_rows)

        prog_txt = ft.Text("Iniciando...", size=12, color=SEC,
                           text_align=ft.TextAlign.CENTER)
        _mostrar_overlay(ft.Column([
            ft.ProgressRing(width=32, height=32, stroke_width=3, color=ROXO),
            ft.Container(height=8),
            ft.Text("Fase 2 — Identificando datas", size=13, color=TXT,
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
                import sqlite3 as _sq2, shutil, base64 as _b64, json as _json

                client = get_client()
                pasta_base = os.path.dirname(pag_rows[0][1]) if pag_rows else ""
                datas_paginas = {}
                _hospitais = []
                _planos    = []

                PROMPT_DATA = """Pagina de prontuario hospitalar brasileiro.
Extraia as informacoes abaixo.
- plano: muitos hospitais pertencem ao mesmo grupo; retorne o nome COMERCIAL do plano (ex: "MedSenior"), nao o CNPJ nem razao social.
- resumo: identifique o tipo e conteudo principal da pagina em ate 8 palavras (ex: "Prescricao medica - antibiotico e analgesia", "Resultado hemograma completo", "Evolucao enfermagem turno manha", "ECG repouso", "Alta hospitalar"). Se for pagina administrativa sem valor clinico, diga "Documento administrativo".
Retorne SOMENTE JSON:
{"data": "YYYY-MM-DD ou null", "hospital": "nome ou null", "plano": "nome comercial ou null", "resumo": "texto curto ou null"}"""

                sem_data_dir = os.path.join(pasta_base, "sem_data")
                todos = list(pag_rows)

                with _sq2.connect(DB_PATH) as _c:
                    pdf_local_map = {
                        r[0]: r[1]
                        for r in _c.execute(
                            "SELECT id, pdf_local FROM pdf_paginas WHERE importacao_id=?",
                            (imp_id,)
                        ).fetchall()
                    }

                with _sq2.connect(DB_PATH) as _c:
                    imp_row = _c.execute(
                        "SELECT nome_arquivo, hash_pdf, total_paginas FROM importacoes_pdf WHERE id=?",
                        (imp_id,)
                    ).fetchone()
                    pron_row = _c.execute(
                        "SELECT id FROM prontuarios WHERE importacao_id=?", (imp_id,)
                    ).fetchone()
                    if pron_row:
                        pron_id = pron_row[0]
                        pags_ant = _c.execute(
                            "SELECT jpeg_local FROM prontuario_paginas WHERE prontuario_id=? AND jpeg_local IS NOT NULL",
                            (pron_id,)
                        ).fetchall()
                        for (jpeg_ant,) in pags_ant:
                            if jpeg_ant and os.path.exists(jpeg_ant):
                                dest_raiz = os.path.join(pasta_base, os.path.basename(jpeg_ant))
                                if jpeg_ant != dest_raiz:
                                    shutil.move(jpeg_ant, dest_raiz)
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

                with _sq2.connect(DB_PATH) as _c:
                    for pid, jpeg_local, num in todos:
                        jpeg_raiz = os.path.join(pasta_base, os.path.basename(jpeg_local))
                        _c.execute(
                            "UPDATE pdf_paginas SET jpeg_local=?, dados_json=NULL WHERE id=?",
                            (jpeg_raiz, pid)
                        )
                todos = [
                    (pid, os.path.join(pasta_base, os.path.basename(jl)), num)
                    for pid, jl, num in todos
                ]

                now = datetime.datetime.now().isoformat(timespec="seconds")

                erros_fatais = 0

                for pid, jpeg_local, num in todos:
                    _prog(f"Pag {num}/{total_pags} — identificando data...")
                    data = resumo = hosp = plan = parsed = None
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
                        data   = parsed.get("data")
                        if data and len(data) != 10: data = None
                        hosp   = (parsed.get("hospital") or "").strip() or None
                        plan   = (parsed.get("plano") or "").strip() or None
                        resumo = (parsed.get("resumo") or "").strip() or None
                        if hosp: _hospitais.append(hosp)
                        if plan: _planos.append(plan)
                        erros_fatais = 0
                    except Exception as _ex:
                        log.warning("[FASE2] pag %d: %s", num, _ex)
                        # erros de credito/auth: interrompe imediatamente
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

                    datas_paginas[num] = data
                    dest_dir = os.path.join(pasta_base, data) if data else sem_data_dir
                    _prog(f"Pag {num}/{total_pags} → {data or 'sem_data'}/")
                    os.makedirs(dest_dir, exist_ok=True)
                    nome_pag = os.path.basename(jpeg_local)
                    dest_jpeg = os.path.join(dest_dir, nome_pag)
                    if jpeg_local != dest_jpeg:
                        shutil.move(jpeg_local, dest_jpeg)
                    pdf_pag = pdf_local_map.get(pid)
                    with _sq2.connect(DB_PATH) as _c:
                        _c.execute(
                            "UPDATE pdf_paginas SET jpeg_local=?, dados_json=json_patch(COALESCE(dados_json,'{}'), ?) WHERE id=?",
                            (dest_jpeg, _json.dumps({"data_pagina": data}), pid)
                        )
                        _adm = resumo and "administrativo" in resumo.lower()
                        _ignorado = 1 if _adm else 0
                        _st = "ignorado" if _adm else ("ok" if data else "pendente")
                        _c.execute(
                            """INSERT INTO prontuario_paginas
                               (prontuario_id, pdf_pagina_id, pagina_num, data_pagina, resumo, dados_json, pdf_local, jpeg_local, ignorado, status)
                               VALUES (?,?,?,?,?,?,?,?,?,?)""",
                            (pron_id, pid, num, data, resumo,
                             _json.dumps(parsed) if parsed else None,
                             pdf_pag, dest_jpeg, _ignorado, _st)
                        )

                def _mais_frequente(lst):
                    if not lst: return None
                    return max(set(lst), key=lst.count)

                datas_validas = sorted(d for d in datas_paginas.values() if d)
                with _sq2.connect(DB_PATH) as _c:
                    _c.execute(
                        """UPDATE prontuarios
                           SET data_inicio=?, data_fim=?, total_paginas=?, hospital=?, plano=?
                           WHERE id=?""",
                        (datas_validas[0] if datas_validas else None,
                         datas_validas[-1] if datas_validas else None,
                         len(todos),
                         _mais_frequente(_hospitais), _mais_frequente(_planos),
                         pron_id)
                    )
                    _c.execute(
                        "UPDATE importacoes_pdf SET fase_atual=2, atualizado_em=? WHERE id=?",
                        (now, imp_id)
                    )

                contagem_datas = {}
                for num, data in datas_paginas.items():
                    chave = data if (data and len(data) == 10) else "sem_data"
                    contagem_datas[chave] = contagem_datas.get(chave, 0) + 1

                _fechar_overlay()
                _mostrar_resultado_fase2(imp_id, pasta_base, contagem_datas)

            except Exception as ex:
                import traceback
                log.error("[FASE2] %s\n%s", ex, traceback.format_exc())
                _fechar_overlay()
                _snack(str(ex)[:200], VERM)

        threading.Thread(target=_run, daemon=True).start()

    def _mostrar_resultado_fase2(imp_id, pasta_base, contagem_datas):
        datas_ord = sorted([(d, n) for d, n in contagem_datas.items() if d != "sem_data"])
        sem_data  = contagem_datas.get("sem_data", 0)
        total     = sum(contagem_datas.values())
        linhas = []
        for data, n in datas_ord:
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

        btn_fechar    = ft.Container(
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
            ft.Text("Fase 2 concluida", size=14, color=TXT, weight=ft.FontWeight.W_700),
            ft.Text(f"{total} paginas organizadas", size=12, color=SEC,
                    text_align=ft.TextAlign.CENTER),
            ft.Container(height=8),
            ft.Column(linhas, spacing=4, scroll=ft.ScrollMode.AUTO,
                      height=min(len(linhas) * 28, 200)),
            ft.Container(height=12),
            ft.Row([btn_fechar, btn_continuar], spacing=8,
                   alignment=ft.MainAxisAlignment.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           tight=True, spacing=4, width=300))

    def _iniciar_fase3(imp_id: int):
        import sqlite3 as _sq, json as _json
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
                _prog("Lendo datas do banco...")
                with _sq.connect(DB_PATH) as _c:
                    rows = _c.execute("""
                        SELECT dados_json, pagina_num FROM pdf_paginas
                        WHERE importacao_id=? AND dados_json IS NOT NULL
                        ORDER BY pagina_num
                    """, (imp_id,)).fetchall()

                datas = {}
                for dados_json, num in rows:
                    try: d = _json.loads(dados_json).get("data_pagina")
                    except Exception: d = None
                    if d and len(d) == 10:
                        datas[d] = datas.get(d, 0) + 1

                if not datas:
                    _fechar_overlay()
                    _snack("Nenhuma data encontrada para criar linha do tempo.", AMAR)
                    return

                pasta_imp = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "..", "temp", "ingestao", str(imp_id)
                )
                now = datetime.datetime.now().isoformat(timespec="seconds")

                with _sq.connect(DB_PATH) as _c:
                    _c.execute("DELETE FROM linha_do_tempo WHERE importacao_id=?", (imp_id,))
                    for data_doc in sorted(datas.keys()):
                        _c.execute("""
                            INSERT INTO linha_do_tempo
                            (importacao_id, data_doc, pasta_local, total_paginas, criado_em)
                            VALUES (?,?,?,?,?)
                        """, (imp_id, data_doc,
                              os.path.join(pasta_imp, data_doc),
                              datas[data_doc], now))
                    _c.execute(
                        "UPDATE importacoes_pdf SET fase_atual=3, atualizado_em=? WHERE id=?",
                        (now, imp_id)
                    )

                with _sq.connect(DB_PATH) as _c:
                    linhas_ldt = _c.execute("""
                        SELECT data_doc, total_paginas FROM linha_do_tempo
                        WHERE importacao_id=? ORDER BY data_doc
                    """, (imp_id,)).fetchall()

                _fechar_overlay()
                _mostrar_resultado_fase3(imp_id, linhas_ldt)

            except Exception as ex:
                import traceback
                log.error("[FASE3] %s\n%s", ex, traceback.format_exc())
                _fechar_overlay()
                _snack(str(ex)[:200], VERM)

        threading.Thread(target=_run, daemon=True).start()

    def _iniciar_fase35(pron_id: int):
        import sqlite3 as _sq35
        with _sq35.connect(DB_PATH) as _c:
            paginas_drive = _c.execute(
                "SELECT id, jpeg_local, pagina_num FROM prontuario_paginas "
                "WHERE prontuario_id=? AND ignorado=0 ORDER BY pagina_num",
                (pron_id,)
            ).fetchall()

        total = len(paginas_drive)
        prog_txt = ft.Text("Conectando ao Drive...", size=12, color=SEC,
                           text_align=ft.TextAlign.CENTER)
        prog_bar = ft.ProgressBar(value=0, bgcolor=BD2, color=AZUL, width=260)
        _mostrar_overlay(ft.Column([
            ft.Icon("cloud_upload_rounded", size=32, color=AZUL),
            ft.Container(height=6),
            ft.Text("Subindo para o Drive", size=14, color=TXT,
                    weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
            ft.Text(f"{total} paginas a enviar", size=11, color=SEC,
                    text_align=ft.TextAlign.CENTER),
            ft.Container(height=8),
            prog_bar,
            ft.Container(height=4),
            prog_txt,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           tight=True, spacing=4, width=280))

        def _prog(msg, frac=None):
            prog_txt.value = msg
            if frac is not None:
                prog_bar.value = frac
            try: page.update()
            except Exception: pass

        def _run():
            try:
                from utils.drive_sync import garantir_pasta_prontuario_medico, upload_foto, _get_creds
                import sqlite3 as _sq35r

                _prog("Autenticando...")
                creds = _get_creds()
                _prog("Criando pasta no Drive...")
                pasta_id = garantir_pasta_prontuario_medico(pron_id, creds=creds)

                enviados = 0
                erros    = 0
                for pag_id, jpeg_local, num in paginas_drive:
                    if not jpeg_local or not os.path.exists(jpeg_local):
                        _prog(f"Pag {num} — arquivo local nao encontrado, pulando")
                        erros += 1
                        enviados += 1
                        prog_bar.value = enviados / total
                        try: page.update()
                        except Exception: pass
                        continue

                    _prog(f"Pag {num}/{total} — enviando...", enviados / total)
                    try:
                        drive_id = upload_foto(jpeg_local, f"{pag_id}.jpg", pasta_id, creds=creds)
                        with _sq35r.connect(DB_PATH) as _c:
                            _c.execute(
                                "UPDATE prontuario_paginas SET jpeg_drive_id=? WHERE id=?",
                                (drive_id, pag_id)
                            )
                        erros = 0
                    except Exception as _ex:
                        log.warning("[FASE35] pag %d: %s", num, _ex)
                        _ex_str = str(_ex).lower()
                        if "401" in _ex_str or "403" in _ex_str or "invalid_grant" in _ex_str:
                            _fechar_overlay()
                            _snack(f"Erro autenticacao Drive: {str(_ex)[:100]}", VERM)
                            return
                        erros += 1
                        if erros >= 5:
                            _fechar_overlay()
                            _snack("Muitos erros consecutivos no Drive.", VERM)
                            return

                    enviados += 1
                    prog_bar.value = enviados / total
                    try: page.update()
                    except Exception: pass

                now = datetime.datetime.now().isoformat(timespec="seconds")
                with _sq35r.connect(DB_PATH) as _c:
                    imp_row = _c.execute(
                        "SELECT importacao_id FROM prontuarios WHERE id=?", (pron_id,)
                    ).fetchone()
                    if imp_row:
                        _c.execute(
                            "UPDATE importacoes_pdf SET fase_atual=4, atualizado_em=? WHERE id=?",
                            (now, imp_row[0])
                        )
                _fechar_overlay()
                _mostrar_resultado_fase35(enviados, erros)

            except Exception as ex:
                import traceback
                log.error("[FASE35] %s\n%s", ex, traceback.format_exc())
                _fechar_overlay()
                _snack(str(ex)[:200], VERM)

        threading.Thread(target=_run, daemon=True).start()

    def _iniciar_fase4(pron_id: int):
        """Agrupa páginas por períodos contíguos e mostra grupos para revisão."""
        import sqlite3 as _sq4

        with _sq4.connect(DB_PATH) as _c:
            rows = _c.execute(
                "SELECT id, pagina_num, data_pagina, resumo, dados_json, "
                "       jpeg_local, jpeg_drive_id "
                "FROM prontuario_paginas "
                "WHERE prontuario_id=? AND ignorado=0 AND status='ok' "
                "ORDER BY data_pagina, pagina_num",
                (pron_id,)
            ).fetchall()

        if not rows:
            _snack("Nenhuma pagina identificada para criar internacoes.", AMAR)
            return

        # agrupar por datas contíguas (gap ≤ 1 dia entre datas consecutivas)
        grupos = []
        grupo_atual = []
        ultima_data = None

        for pag_id, num, data_str, resumo, dados_json, jpeg_local, jpeg_drive_id in rows:
            data = datetime.date.fromisoformat(data_str)
            pag_dict = {
                "id": pag_id, "num": num, "data": data_str,
                "resumo": resumo or "", "dados_json": dados_json,
                "jpeg": jpeg_local, "jpeg_drive_id": jpeg_drive_id,
            }
            if ultima_data is None or (data - ultima_data).days <= 1:
                grupo_atual.append(pag_dict)
                ultima_data = data
            else:
                if grupo_atual:
                    grupos.append(grupo_atual)
                grupo_atual = [pag_dict]
                ultima_data = data
        if grupo_atual:
            grupos.append(grupo_atual)

        _mostrar_revisao_grupos(pron_id, grupos)

    def _mostrar_revisao_grupos(pron_id: int, grupos: list):
        """Mostra grupos propostos; usuário confirma antes de ir ao Claude."""

        def _data_range(grp):
            datas = sorted(set(p["data"] for p in grp if p["data"]))
            if not datas:
                return "sem data"
            d0 = _para_display(datas[0])
            d1 = _para_display(datas[-1])
            return d0 if d0 == d1 else f"{d0} → {d1}"

        def _ver_paginas_grupo(grp, idx):
            """Sub-overlay com as páginas do grupo; Voltar retorna à lista de grupos."""

            def _abrir_imagem_grupo(pag):
                jpeg = pag.get("jpeg")
                drive_id = pag.get("jpeg_drive_id")
                tem_local = bool(jpeg and os.path.exists(jpeg))
                if tem_local:
                    try:
                        page.launch_url(f"file:///{jpeg.replace(os.sep, '/')}")
                    except Exception:
                        import webbrowser
                        webbrowser.open(jpeg)
                    return
                if drive_id:
                    _snack(f"Baixando pag {pag['num']} do Drive...", None)
                    def _baixar():
                        try:
                            from utils.drive_sync import baixar_foto
                            _CACHE = os.path.join(
                                os.path.dirname(os.path.abspath(__file__)),
                                "..", "temp", "cache"
                            )
                            cache_path = os.path.join(_CACHE, f"{pag['id']}.jpg")
                            os.makedirs(_CACHE, exist_ok=True)
                            if not os.path.exists(cache_path):
                                baixar_foto(drive_id, cache_path)
                            try:
                                page.launch_url(f"file:///{cache_path.replace(os.sep, '/')}")
                            except Exception:
                                import webbrowser
                                webbrowser.open(cache_path)
                        except Exception as ex:
                            _snack(f"Erro ao baixar: {ex}"[:80], VERM)
                    threading.Thread(target=_baixar, daemon=True).start()
                else:
                    _snack("Imagem nao disponivel.", AMAR)

            linhas_pag = []
            for pag in grp:
                jpeg = pag.get("jpeg")
                drive_id = pag.get("jpeg_drive_id")
                tem_img = bool((jpeg and os.path.exists(jpeg)) or drive_id)
                cor_ico = AZUL if tem_img else MUT
                linha_p = ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Icon(
                                "image_rounded" if tem_img else "image_not_supported_rounded",
                                size=13, color=cor_ico,
                            ),
                            bgcolor=ft.Colors.with_opacity(0.12, cor_ico),
                            border_radius=6, width=28, height=28,
                            alignment=ft.alignment.center,
                        ),
                        ft.Column([
                            ft.Text(
                                f"Pag {pag['num']}  —  {_para_display(pag['data']) if pag['data'] else 'sem data'}",
                                size=12, color=TXT, weight=ft.FontWeight.W_600,
                            ),
                            ft.Text(
                                (pag.get("resumo") or "sem identificacao")[:55],
                                size=10, color=SEC,
                                italic=not bool(pag.get("resumo")),
                            ),
                        ], spacing=1, tight=True, expand=True),
                        ft.Icon(
                            "open_in_new_rounded" if tem_img else "block_rounded",
                            size=13, color=AZUL if tem_img else MUT,
                        ),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=BD, border_radius=8,
                    padding=ft.padding.symmetric(horizontal=10, vertical=8),
                    ink=tem_img,
                )
                if tem_img:
                    def _click_img(e, _p=pag):
                        _abrir_imagem_grupo(_p)
                    linha_p.on_click = _click_img
                linhas_pag.append(linha_p)

            btn_voltar_grp = ft.Container(
                content=ft.Row([
                    ft.Icon("arrow_back_rounded", size=14, color=AZUL),
                    ft.Text("Grupos", size=12, color=AZUL),
                ], spacing=4, tight=True),
                border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border=ft.border.all(1, BD),
            )
            btn_voltar_grp.on_click = lambda _: _mostrar_revisao_grupos(pron_id, grupos)

            _mostrar_overlay(ft.Column([
                ft.Row([
                    btn_voltar_grp,
                    ft.Column([
                        ft.Text(f"Grupo {idx + 1} — {_data_range(grp)}",
                                size=13, color=TXT, weight=ft.FontWeight.W_700),
                        ft.Text(f"{len(grp)} pagina{'s' if len(grp) != 1 else ''}",
                                size=10, color=SEC),
                    ], spacing=1, tight=True, expand=True),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(height=6),
                ft.Text("Clique numa pagina para ver a imagem",
                        size=10, color=MUT, italic=True),
                ft.Container(height=4),
                ft.Column(linhas_pag, spacing=4,
                          scroll=ft.ScrollMode.AUTO,
                          height=min(len(linhas_pag) * 54, 340)),
                ft.Container(height=8),
            ], tight=True, spacing=4, width=310))

        itens_grupos = []
        for i, grp in enumerate(grupos):
            periodo = _data_range(grp)
            n_pags  = len(grp)
            resumos = list({p["resumo"] for p in grp if p["resumo"]})[:3]

            item_grp = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            content=ft.Text(str(i + 1), size=11, color=BG,
                                            weight=ft.FontWeight.W_700),
                            bgcolor=ROXO, border_radius=10,
                            width=22, height=22, alignment=ft.alignment.center,
                        ),
                        ft.Column([
                            ft.Text(periodo, size=12, color=TXT,
                                    weight=ft.FontWeight.W_600),
                            ft.Text(f"{n_pags} pagina{'s' if n_pags != 1 else ''}",
                                    size=10, color=SEC),
                        ], spacing=1, tight=True, expand=True),
                        ft.Icon("chevron_right_rounded", size=14, color=MUT),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(
                        " · ".join(r[:40] for r in resumos) if resumos else "sem resumo",
                        size=10, color=MUT, italic=True,
                    ),
                ], spacing=4, tight=True),
                bgcolor=BD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                ink=True,
            )
            def _click_grp(e, _g=grp, _i=i):
                _ver_paginas_grupo(_g, _i)
            item_grp.on_click = _click_grp
            itens_grupos.append(item_grp)

        btn_cancelar = ft.Container(
            content=ft.Text("Cancelar", size=12, color=SEC),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.all(1, BD),
        )
        btn_cancelar.on_click = lambda _: _fechar_overlay()

        btn_confirmar = ft.Container(
            content=ft.Row([
                ft.Icon("check_rounded", size=14, color=BG),
                ft.Text("Confirmar e extrair", size=12, color=BG,
                        weight=ft.FontWeight.W_600),
            ], spacing=4, tight=True),
            bgcolor=ROXO, border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
        )
        btn_confirmar.on_click = lambda _: (
            _fechar_overlay(),
            _executar_extracao_fase4(pron_id, grupos),
        )

        _mostrar_overlay(ft.Column([
            ft.Icon("local_hospital_rounded", size=28, color=ROXO),
            ft.Container(height=4),
            ft.Text("Grupos de internacao", size=14, color=TXT,
                    weight=ft.FontWeight.W_700),
            ft.Text(
                f"{len(grupos)} internacao(s) — toque para ver paginas",
                size=11, color=SEC, text_align=ft.TextAlign.CENTER,
            ),
            ft.Container(height=8),
            ft.Column(itens_grupos, spacing=6,
                      scroll=ft.ScrollMode.AUTO,
                      height=min(len(itens_grupos) * 72, 300)),
            ft.Container(height=10),
            ft.Row([btn_cancelar, btn_confirmar], spacing=8,
                   alignment=ft.MainAxisAlignment.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           tight=True, spacing=4, width=310))

    def _executar_extracao_fase4(pron_id: int, grupos: list):
        """Deleta internações antigas, extrai via Claude, grava no banco."""
        import sqlite3 as _sq4e
        import json as _j4e

        prog_txt = ft.Text("Iniciando...", size=12, color=SEC,
                           text_align=ft.TextAlign.CENTER)
        prog_bar = ft.ProgressBar(value=0, bgcolor=BD2, color=ROXO, width=260)
        _mostrar_overlay(ft.Column([
            ft.Icon("local_hospital_rounded", size=32, color=ROXO),
            ft.Container(height=6),
            ft.Text("Fase 4 — Identificando internacoes", size=13, color=TXT,
                    weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
            ft.Container(height=8),
            prog_bar,
            ft.Container(height=4),
            prog_txt,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           tight=True, spacing=4, width=280))

        def _prog(msg, frac=None):
            prog_txt.value = msg
            if frac is not None:
                prog_bar.value = frac
            try: page.update()
            except Exception: pass

        PROMPT_INTERNACAO = """Voce recebe um conjunto de paginas de prontuario hospitalar brasileiro.
Cada pagina tem: data, resumo e dados_json extraidos anteriormente.
Identifique os dados desta internacao hospitalar.

Retorne SOMENTE JSON (sem markdown):
{
  "hospital": "nome do hospital ou null",
  "modalidade": "internacao | ps | ps_internacao",
  "tipo": "eletiva | urgencia | emergencia",
  "data_entrada": "YYYY-MM-DD ou null",
  "data_saida": "YYYY-MM-DD ou null",
  "motivo": "motivo resumido em 1-2 frases ou null",
  "cid_entrada": "codigo CID ou null",
  "diagnostico_saida": "diagnostico de alta ou null",
  "cid_saida": "codigo CID de saida ou null",
  "medico_responsavel": "nome do medico responsavel ou null",
  "observacoes": "comorbidades ou intercorrencias relevantes ou null"
}"""

        def _run():
            try:
                from utils.claudia_engine import get_client
                import sqlite3 as _sq4r

                # buscar importacao_id para vincular
                with _sq4r.connect(DB_PATH) as _c:
                    imp_row = _c.execute(
                        "SELECT importacao_id FROM prontuarios WHERE id=?", (pron_id,)
                    ).fetchone()
                imp_id = imp_row[0] if imp_row else None

                # deletar internações existentes vinculadas a este prontuário
                _prog("Limpando internacoes anteriores...")
                if imp_id:
                    with _sq4r.connect(DB_PATH) as _c:
                        ids_ant = [r[0] for r in _c.execute(
                            "SELECT id FROM internacoes WHERE fonte_dados='importado' "
                            "AND id IN ("
                            "  SELECT DISTINCT internacao_id FROM prontuario_paginas "
                            "  WHERE prontuario_id=? AND internacao_id IS NOT NULL"
                            ")", (pron_id,)
                        ).fetchall()]
                        for iid in ids_ant:
                            _c.execute("DELETE FROM diagnosticos_internacao WHERE internacao_id=?", (iid,))
                            _c.execute("DELETE FROM sinais_internacao WHERE internacao_id=?", (iid,))
                            _c.execute("DELETE FROM registros_clinicos WHERE internacao_id=?", (iid,))
                            _c.execute("DELETE FROM procedimentos WHERE internacao_id=?", (iid,))
                            _c.execute("DELETE FROM internacoes WHERE id=?", (iid,))
                        _c.execute(
                            "UPDATE prontuario_paginas SET internacao_id=NULL WHERE prontuario_id=?",
                            (pron_id,)
                        )

                client = get_client()
                total  = len(grupos)
                internacoes_criadas = []

                for i, grp in enumerate(grupos):
                    _prog(f"Grupo {i+1}/{total} — enviando ao Claude...", i / total)

                    # monta contexto: lista das páginas do grupo
                    linhas_ctx = []
                    for p in grp:
                        jd = {}
                        if p.get("dados_json"):
                            try: jd = _j4e.loads(p["dados_json"])
                            except Exception: pass
                        linhas_ctx.append(
                            f"- Data: {p['data']} | Resumo: {p['resumo'] or 'n/d'} | "
                            f"JSON: {_j4e.dumps(jd, ensure_ascii=False)}"
                        )
                    contexto = "\n".join(linhas_ctx)

                    try:
                        resp = client.messages.create(
                            model="claude-haiku-4-5-20251001",
                            max_tokens=400,
                            messages=[{"role": "user", "content":
                                f"{PROMPT_INTERNACAO}\n\nPaginas:\n{contexto}"}],
                            timeout=30,
                        )
                        txt = resp.content[0].text.strip()
                        if txt.startswith("```"):
                            txt = txt.split("```")[1].lstrip("json").strip()
                        dados = _j4e.loads(txt)
                    except Exception as _ex:
                        log.warning("[FASE4] grupo %d: %s", i + 1, _ex)
                        _ex_str = str(_ex).lower()
                        if "credit" in _ex_str or "401" in _ex_str or "403" in _ex_str:
                            _fechar_overlay()
                            _snack(f"Erro API: {str(_ex)[:120]}", VERM)
                            return
                        # fallback: usar dados das páginas diretamente
                        datas = sorted(p["data"] for p in grp if p["data"])
                        dados = {
                            "hospital": None, "modalidade": "internacao",
                            "tipo": "urgencia",
                            "data_entrada": datas[0] if datas else None,
                            "data_saida": datas[-1] if datas else None,
                            "motivo": None, "cid_entrada": None,
                            "diagnostico_saida": None, "cid_saida": None,
                            "medico_responsavel": None, "observacoes": None,
                        }

                    # gravar internação
                    _prog(f"Grupo {i+1}/{total} — gravando internacao...", (i + 0.8) / total)
                    datas_grp = sorted(p["data"] for p in grp if p["data"])
                    hospital = (dados.get("hospital") or "").strip() or None

                    with _sq4r.connect(DB_PATH) as _c:
                        cur = _c.cursor()
                        cur.execute("""
                            INSERT INTO internacoes
                              (hospital, data_entrada, data_saida, tipo, motivo,
                               cid_entrada, diagnostico_saida, cid_saida,
                               medico_responsavel, modalidade, observacoes,
                               fonte_dados, criado_em)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,'importado',datetime('now'))
                        """, (
                            hospital or (datas_grp[0] if datas_grp else "Desconhecido"),
                            dados.get("data_entrada") or (datas_grp[0] if datas_grp else None),
                            dados.get("data_saida") or (datas_grp[-1] if datas_grp else None),
                            dados.get("tipo") or "urgencia",
                            dados.get("motivo"),
                            dados.get("cid_entrada"),
                            dados.get("diagnostico_saida"),
                            dados.get("cid_saida"),
                            dados.get("medico_responsavel"),
                            dados.get("modalidade") or "internacao",
                            dados.get("observacoes"),
                        ))
                        int_id = cur.lastrowid

                        # vincular páginas do grupo à internação
                        for p in grp:
                            _c.execute(
                                "UPDATE prontuario_paginas SET internacao_id=? WHERE id=?",
                                (int_id, p["id"])
                            )

                    internacoes_criadas.append({
                        "id": int_id,
                        "hospital": hospital or "?",
                        "data_entrada": dados.get("data_entrada") or (datas_grp[0] if datas_grp else "?"),
                        "data_saida": dados.get("data_saida") or (datas_grp[-1] if datas_grp else "?"),
                        "n_pags": len(grp),
                    })

                # atualizar fase no banco
                now = datetime.datetime.now().isoformat(timespec="seconds")
                if imp_id:
                    with _sq4r.connect(DB_PATH) as _c:
                        _c.execute(
                            "UPDATE importacoes_pdf SET fase_atual=5, atualizado_em=? WHERE id=?",
                            (now, imp_id)
                        )

                _fechar_overlay()
                _mostrar_resultado_fase4(internacoes_criadas)

            except Exception as ex:
                import traceback
                log.error("[FASE4] %s\n%s", ex, traceback.format_exc())
                _fechar_overlay()
                _snack(str(ex)[:200], VERM)

        threading.Thread(target=_run, daemon=True).start()

    def _mostrar_resultado_fase4(internacoes: list):
        itens = []
        for it in internacoes:
            itens.append(ft.Row([
                ft.Icon("local_hospital_rounded", size=13, color=ROXO),
                ft.Column([
                    ft.Text(it["hospital"][:32], size=12, color=TXT,
                            weight=ft.FontWeight.W_600),
                    ft.Text(
                        f"{_para_display(it['data_entrada'])} → {_para_display(it['data_saida'])} "
                        f"· {it['n_pags']} pags",
                        size=10, color=SEC,
                    ),
                ], spacing=1, tight=True, expand=True),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER))

        btn_ok = ft.Container(
            content=ft.Text("Fechar", size=12, color=SEC),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.all(1, BD),
        )
        btn_ok.on_click = lambda _: (_fechar_overlay(), _rebuild())

        _mostrar_overlay(ft.Column([
            ft.Icon("check_circle_rounded", size=36, color=VERD),
            ft.Container(height=6),
            ft.Text("Internacoes criadas!", size=14, color=TXT,
                    weight=ft.FontWeight.W_700),
            ft.Text(f"{len(internacoes)} internacao(s) no banco",
                    size=12, color=SEC, text_align=ft.TextAlign.CENTER),
            ft.Container(height=8),
            ft.Column(itens, spacing=6, scroll=ft.ScrollMode.AUTO,
                      height=min(len(itens) * 48, 250)),
            ft.Container(height=12),
            btn_ok,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           tight=True, spacing=4, width=300))

    def _mostrar_resultado_fase35(enviados, erros):
        btn_ok = ft.Container(
            content=ft.Text("Fechar", size=12, color=SEC),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.all(1, BD),
        )
        btn_ok.on_click = lambda _: (_fechar_overlay(), _rebuild())
        _mostrar_overlay(ft.Column([
            ft.Icon("cloud_done_rounded", size=36, color=VERD),
            ft.Container(height=6),
            ft.Text("Drive atualizado!", size=14, color=TXT,
                    weight=ft.FontWeight.W_700),
            ft.Text(f"{enviados} paginas enviadas" +
                    (f" — {erros} com erro" if erros else ""),
                    size=12, color=SEC, text_align=ft.TextAlign.CENTER),
            ft.Container(height=12),
            btn_ok,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           tight=True, spacing=4, width=260))

    def _mostrar_resultado_fase3(imp_id, linhas):
        import sqlite3 as _sq3r
        with _sq3r.connect(DB_PATH) as _c:
            _pron_row = _c.execute(
                "SELECT id FROM prontuarios WHERE importacao_id=?", (imp_id,)
            ).fetchone()
        pron_id_f3 = _pron_row[0] if _pron_row else None

        # verifica se há pendências antes de oferecer a subida
        n_pend_f3 = 0
        if pron_id_f3:
            with _sq3r.connect(DB_PATH) as _c:
                n_pend_f3 = _c.execute(
                    "SELECT COUNT(*) FROM prontuario_paginas "
                    "WHERE prontuario_id=? AND ignorado=0 "
                    "AND (status='pendente' OR (status IS NULL AND data_pagina IS NULL))",
                    (pron_id_f3,)
                ).fetchone()[0]

        itens = [ft.Row([
            ft.Icon("calendar_today_rounded", size=13, color=ROXO),
            ft.Text(d, size=12, color=TXT, expand=True),
            ft.Text(f"{n} pag{'s' if n > 1 else ''}", size=11, color=SEC),
        ], spacing=6) for d, n in linhas]

        btn_fechar = ft.Container(
            content=ft.Text("Fechar", size=12, color=SEC),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.all(1, BD),
        )
        btn_fechar.on_click = lambda _: (_fechar_overlay(), _rebuild())

        botoes_f3 = [btn_fechar]

        if pron_id_f3 and n_pend_f3 == 0:
            btn_subir = ft.Container(
                content=ft.Row([
                    ft.Icon("cloud_upload_rounded", size=15, color=BG),
                    ft.Text("Subir para Drive", size=12, color=BG,
                            weight=ft.FontWeight.W_600),
                ], spacing=4, tight=True),
                bgcolor=AZUL, border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
            )
            def _subir_f3(_):
                _fechar_overlay()
                _iniciar_fase35(pron_id_f3)
            btn_subir.on_click = _subir_f3
            botoes_f3.append(btn_subir)
        elif pron_id_f3 and n_pend_f3 > 0:
            btn_ver = ft.Container(
                content=ft.Row([
                    ft.Icon("warning_amber_rounded", size=15, color=BG),
                    ft.Text(f"{n_pend_f3} pendente{'s' if n_pend_f3 != 1 else ''}", size=12,
                            color=BG, weight=ft.FontWeight.W_600),
                ], spacing=4, tight=True),
                bgcolor=AMAR, border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
            )
            def _ver_pag_f3(_):
                _fechar_overlay()
                # abre a vista de páginas do prontuário para acertar pendências
                import sqlite3 as _sqv
                with _sqv.connect(DB_PATH) as _c:
                    pron_data = _c.execute(
                        "SELECT id, nome_arquivo, total_paginas, data_inicio, data_fim, "
                        "hospital, plano FROM prontuarios WHERE id=?", (pron_id_f3,)
                    ).fetchone()
                if pron_data:
                    _pron_sel[0] = {
                        "id": pron_data[0], "nome": pron_data[1], "total": pron_data[2],
                        "data_inicio": pron_data[3], "data_fim": pron_data[4],
                        "hospital": pron_data[5], "plano": pron_data[6],
                    }
                    _vista[0] = "paginas"
                    _rebuild()
            btn_ver.on_click = _ver_pag_f3
            botoes_f3.append(btn_ver)

        _mostrar_overlay(ft.Column([
            ft.Icon("timeline_rounded", size=32, color=ROXO),
            ft.Container(height=6),
            ft.Text("Fase 3 concluida", size=14, color=TXT, weight=ft.FontWeight.W_700),
            ft.Text(f"{len(linhas)} data(s) na linha do tempo", size=12, color=SEC,
                    text_align=ft.TextAlign.CENTER),
            ft.Container(height=8),
            ft.Column(itens, spacing=4, scroll=ft.ScrollMode.AUTO,
                      height=min(len(itens) * 28, 220)),
            ft.Container(height=12),
            ft.Row(botoes_f3, spacing=8, alignment=ft.MainAxisAlignment.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           tight=True, spacing=4, width=280))

    # ── banner de importações pendentes ──────────────────────────────────────
    _banner_pend = ft.Container(visible=False)

    def _checar_pendentes():
        try:
            from utils.processador_pdf import importacoes_pendentes
            pend = importacoes_pendentes()
            if not pend:
                return
            p = pend[0]
            fase_label = {
                1: "paginas salvas — aguarda identificar datas",
                2: "datas identificadas — aguarda linha do tempo",
                3: "linha do tempo criada",
            }.get(p["fase_atual"], f"fase {p['fase_atual']}")

            btn_c = ft.Container(
                content=ft.Text("Continuar", size=11, color=BG,
                                weight=ft.FontWeight.W_600),
                bgcolor=AMAR, border_radius=6,
                padding=ft.padding.symmetric(horizontal=10, vertical=5), ink=True,
            )
            btn_x = ft.Container(
                content=ft.Icon("close", size=14, color=MUT),
                padding=ft.padding.all(4), ink=True, border_radius=4,
            )

            def _retomar(_):
                _banner_pend.visible = False
                try: page.update()
                except Exception: pass
                fase = p["fase_atual"]
                if fase == 1:   _iniciar_fase2(p["id"])
                elif fase == 2: _iniciar_fase3(p["id"])
                elif fase == 3:
                    import sqlite3 as _sq
                    with _sq.connect(DB_PATH) as _c:
                        lins = _c.execute(
                            "SELECT data_doc, total_paginas FROM linha_do_tempo WHERE importacao_id=? ORDER BY data_doc",
                            (p["id"],)
                        ).fetchall()
                    _mostrar_resultado_fase3(p["id"], lins)

            btn_c.on_click = _retomar
            btn_x.on_click = lambda _: (setattr(_banner_pend, "visible", False),
                                        page.update())

            _banner_pend.content = ft.Row([
                ft.Icon("hourglass_top_rounded", size=14, color=AMAR),
                ft.Column([
                    ft.Text((p["nome_arquivo"] or "")[:28], size=12, color=TXT,
                            weight=ft.FontWeight.W_600),
                    ft.Text(fase_label, size=10, color=SEC),
                ], spacing=1, tight=True, expand=True),
                ft.Row([btn_c, btn_x], spacing=4, tight=True),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            _banner_pend.bgcolor      = "#1C2128"
            _banner_pend.border       = ft.border.all(1, AMAR)
            _banner_pend.border_radius = 8
            _banner_pend.padding      = ft.padding.symmetric(horizontal=12, vertical=8)
            _banner_pend.visible      = True
            try: page.update()
            except Exception: pass
        except Exception:
            pass

    threading.Thread(target=_checar_pendentes, daemon=True).start()

    # ── área de conteúdo ─────────────────────────────────────────────────────
    area = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=0)

    def _rebuild():
        area.controls.clear()
        if _vista[0] == "lista":
            _render_lista()
        else:
            _render_paginas()
        try: page.update()
        except Exception: pass

    # ── VISTA: lista de prontuarios ───────────────────────────────────────────
    def _render_lista():
        prons = _listar_prontuarios(DB_PATH)

        if not prons:
            btn_imp_vazio = ft.Container(
                content=ft.Row([
                    ft.Icon("upload_file_rounded", size=15, color=BG),
                    ft.Text("Importar PDF", size=12, color=BG,
                            weight=ft.FontWeight.W_600),
                ], spacing=6, tight=True),
                bgcolor=AZUL, border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
            )
            btn_imp_vazio.on_click = lambda _: _importar_pdf()
            area.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("folder_open_rounded", size=40, color=MUT),
                    ft.Text("Nenhum prontuario importado", size=13, color=SEC,
                            text_align=ft.TextAlign.CENTER),
                    ft.Container(height=4),
                    btn_imp_vazio,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=8, tight=True),
                alignment=ft.alignment.center,
                expand=True, padding=40,
            ))
            return

        area.controls.append(ft.Container(height=8))
        for p in prons:
            fase = p["fase"]
            if fase is None or fase < 3:
                badge_txt  = f"Fase {fase or 0}"
                badge_cor  = AMAR
            else:
                badge_txt = "OK"
                badge_cor = VERD

            periodo = ""
            if p["data_inicio"] and p["data_fim"]:
                if p["data_inicio"] == p["data_fim"]:
                    periodo = _para_display(p["data_inicio"])
                else:
                    periodo = f"{_para_display(p['data_inicio'])} → {_para_display(p['data_fim'])}"
            elif p["data_inicio"]:
                periodo = _para_display(p["data_inicio"])

            btn_del = ft.Container(
                content=ft.Icon("delete_outline_rounded", size=17, color=VERM),
                padding=ft.padding.all(6), ink=True, border_radius=8,
                tooltip="Excluir prontuario",
            )

            def _confirmar_delete(e, pron=p):
                btn_sim = ft.Container(
                    content=ft.Text("Excluir", size=12, color=BG,
                                    weight=ft.FontWeight.W_600),
                    bgcolor=VERM, border_radius=8, ink=True,
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                )
                btn_nao = ft.Container(
                    content=ft.Text("Cancelar", size=12, color=SEC),
                    border_radius=8, ink=True,
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    border=ft.border.all(1, BD),
                )
                btn_nao.on_click = lambda _: _fechar_overlay()
                def _deletar(_):
                    _fechar_overlay()
                    _excluir_prontuario(pron["id"])
                btn_sim.on_click = _deletar
                _mostrar_overlay(ft.Column([
                    ft.Icon("delete_outline_rounded", size=32, color=VERM),
                    ft.Container(height=6),
                    ft.Text("Excluir prontuario?", size=14, color=TXT,
                            weight=ft.FontWeight.W_700),
                    ft.Text(pron["hospital"] or pron["nome"][:32],
                            size=12, color=SEC, text_align=ft.TextAlign.CENTER),
                    ft.Text("Todas as paginas e linha do tempo\nserao removidas.",
                            size=11, color=MUT, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=12),
                    ft.Row([btn_nao, btn_sim], spacing=8,
                           alignment=ft.MainAxisAlignment.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   tight=True, spacing=4, width=280))

            btn_del.on_click = _confirmar_delete

            n_pend_card = p["n_pendentes"]

            # corpo clicável do card
            corpo_card = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon("description_rounded", size=20, color=AZUL),
                        bgcolor=ft.Colors.with_opacity(0.12, AZUL), border_radius=10,
                        width=40, height=40,
                        alignment=ft.alignment.center,
                    ),
                    ft.Column([
                        ft.Row([
                            ft.Text(p["hospital"] or p["nome"][:32], size=13, color=TXT,
                                    weight=ft.FontWeight.W_600, expand=True),
                            ft.Container(
                                content=ft.Text(badge_txt, size=9,
                                                color=BG, weight=ft.FontWeight.W_700),
                                bgcolor=badge_cor, border_radius=6,
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            ),
                        ], spacing=6),
                        ft.Row([
                            ft.Icon("verified_rounded", size=11, color=ROXO),
                            ft.Text(p["plano"] or "plano nao identificado",
                                    size=11, color=ROXO if p["plano"] else MUT),
                        ], spacing=4),
                        ft.Row([
                            ft.Icon("layers_rounded", size=11, color=MUT),
                            ft.Text(f"{p['total']} pags", size=11, color=SEC),
                            ft.Container(width=6),
                            ft.Icon("calendar_today_rounded", size=11, color=MUT),
                            ft.Text(periodo or "sem data", size=11, color=SEC),
                        ], spacing=4),
                    ], spacing=2, tight=True, expand=True),
                    btn_del,
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ink=True, border_radius=ft.border_radius.only(12, 12, 0, 0),
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
            )

            def _abrir(e, pron=p):
                _pron_sel[0] = pron
                _vista[0] = "paginas"
                _rebuild()

            corpo_card.on_click = _abrir

            # rodapé do card: botão Identificar Internações
            if n_pend_card == 0:
                def _fase4_card(e, pron=p):
                    _iniciar_fase4(pron["id"])
                rodape = ft.Container(
                    content=ft.Row([
                        ft.Icon("local_hospital_rounded", size=13, color=ROXO),
                        ft.Text("Identificar Internacoes", size=11, color=ROXO,
                                weight=ft.FontWeight.W_600, expand=True),
                        ft.Icon("chevron_right_rounded", size=13, color=MUT),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ink=True, border_radius=ft.border_radius.only(0, 0, 12, 12),
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                    border=ft.Border(top=ft.BorderSide(1, BD)),
                    on_click=_fase4_card,
                )
            else:
                rodape = ft.Container(
                    content=ft.Row([
                        ft.Icon("warning_amber_rounded", size=13, color=AMAR),
                        ft.Text(
                            f"{n_pend_card} pendente{'s' if n_pend_card != 1 else ''} — corrija para identificar internacoes",
                            size=11, color=AMAR, expand=True,
                        ),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                    border=ft.Border(top=ft.BorderSide(1, BD)),
                )

            card = ft.Container(
                content=ft.Column([corpo_card, rodape], spacing=0, tight=True),
                bgcolor=CARD,
                border_radius=12,
                border=ft.border.all(1, BD),
                margin=ft.margin.symmetric(horizontal=16, vertical=4),
            )

            area.controls.append(card)

        area.controls.append(ft.Container(height=16))

    _filtro_paginas = ["todos"]   # estado persistente do filtro entre rebuilds

    # ── VISTA: paginas do prontuario ──────────────────────────────────────────
    def _render_paginas():
        p = _pron_sel[0]
        if not p:
            _vista[0] = "lista"
            _rebuild()
            return

        paginas = _listar_paginas(DB_PATH, p["id"])

        area.controls.append(ft.Container(height=8))

        if not paginas:
            area.controls.append(ft.Container(
                content=ft.Text("Nenhuma pagina encontrada.", size=12, color=SEC),
                padding=ft.padding.all(20),
            ))
            return

        # ── banner de pendências ──────────────────────────────────────────────
        pendentes = [pg for pg in paginas if pg["status"] == "pendente"]
        n_pend    = len(pendentes)
        n_ok      = sum(1 for pg in paginas if pg["status"] == "ok")
        n_ign     = sum(1 for pg in paginas if pg["status"] == "ignorado")
        total_ativo = n_pend + n_ok  # ignoradas não contam para avançar

        if n_pend > 0:
            area.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("warning_amber_rounded", size=15, color=VERM),
                    ft.Text(
                        f"{n_pend} pendente{'s' if n_pend > 1 else ''} sem data — corrija antes de avancar",
                        size=11, color=VERM, expand=True,
                    ),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor="#2D1117",
                border=ft.border.all(1, ft.Colors.with_opacity(0.53, VERM)),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                margin=ft.margin.symmetric(horizontal=16, vertical=4),
            ))
        else:
            area.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("check_circle_outline_rounded", size=15, color=VERD),
                    ft.Text(
                        f"Todas as paginas identificadas ({n_ok} com data, {n_ign} ignorada{'s' if n_ign != 1 else ''})",
                        size=11, color=VERD, expand=True,
                    ),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor="#0D2117",
                border=ft.border.all(1, ft.Colors.with_opacity(0.53, VERD)),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                margin=ft.margin.symmetric(horizontal=16, vertical=4),
            ))

        # ── classificação por tipo (a partir do resumo) ──────────────────────
        _EXAME_KW    = ["exame", "hemograma", "glicemia", "colesterol", "triglicerides",
                        "creatinina", "ureia", "sodio", "potassio", "magnesio", "calcio",
                        "resultado", "laudo", "laboratorio", "rx ", "raio", "tomografia",
                        "ressonancia", "ultrassom", "ecografia", "ecocardiograma", "ecg",
                        "eletrocardiograma", "espirometria", "holter", "mapa", "densitometria",
                        "sorologia", "cultura", "urina", "sangue", "sangue", "biopsia",
                        "citologia", "patopatologia", "bioquimica", "coagulograma",
                        "gasometria", "proteina", "albumina", "enzima"]
        _REMEDIO_KW  = ["prescricao", "prescri", "medicacao", "medicamento", "antibiotico",
                        "analgesico", "diuretico", "anticoagulante", "insulina", "heparina",
                        "dipirona", "morfina", "fentanil", "omeprazol", "losartana",
                        "metformina", "amoxicilina", "ceftriaxona", "vancomicina",
                        "noradrenalina", "dobutamina", "solucao", "soro", "infusao",
                        "droga", "farmaco", "remedio", "periodo 24h", "periodo 12h"]
        _PROCED_KW   = ["procedimento", "cirurgia", "cirurgico", "cateterismo",
                        "endoscopia", "colonoscopia", "intubacao", "traqueostomia",
                        "dialise", "hemofiltracao", "desfibrilacao", "cardioversao",
                        "puncao", "biopsia", "dreno", "drena", "cateter", "sonda",
                        "transferencia", "checklist", "anestesia", "operatorio",
                        "pos-operatorio", "trans-operatorio", "sala de cirurgia",
                        "implante", "stent", "by-pass", "bypass", "revascularizacao"]

        def _classificar(resumo: str) -> str:
            r = resumo.lower()
            if any(k in r for k in _EXAME_KW):    return "exames"
            if any(k in r for k in _REMEDIO_KW):  return "remedios"
            if any(k in r for k in _PROCED_KW):   return "procedimentos"
            return "outros"

        # conta por categoria para os chips
        _contagens = {"todos": 0, "exames": 0, "remedios": 0, "procedimentos": 0, "outros": 0}
        for pg in paginas:
            if not pg.get("ignorado"):
                _contagens["todos"] += 1
                _contagens[_classificar(pg.get("resumo") or "")] += 1

        # ── barra de filtros ──────────────────────────────────────────────────
        CHIPS = [
            ("todos",          "Todos",          TXT,  "layers_rounded"),
            ("exames",         "Exames",         VERD, "biotech_rounded"),
            ("remedios",       "Remedios",       AZUL, "medication_rounded"),
            ("procedimentos",  "Procedimentos",  LAR,  "medical_services_rounded"),
            ("outros",         "Outros",         MUT,  "help_outline_rounded"),
        ]

        chips_row = ft.Row(spacing=6, scroll=ft.ScrollMode.AUTO)

        def _aplicar_filtro(novo_filtro):
            _filtro_paginas[0] = novo_filtro
            _rebuild()

        for val, label, cor, ico in CHIPS:
            cnt = _contagens[val]
            ativo = _filtro_paginas[0] == val
            chip = ft.Container(
                content=ft.Row([
                    ft.Icon(ico, size=11, color=cor if ativo else MUT),
                    ft.Text(label, size=11,
                            color=cor if ativo else SEC,
                            weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.NORMAL),
                    ft.Container(
                        content=ft.Text(str(cnt), size=9,
                                        color=BG if ativo else MUT,
                                        weight=ft.FontWeight.W_700),
                        bgcolor=cor if ativo else BD2,
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=5, vertical=1),
                    ),
                ], spacing=4, tight=True),
                bgcolor=ft.Colors.with_opacity(0.15, cor) if ativo else CARD,
                border=ft.border.all(1, cor if ativo else BD),
                border_radius=16,
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                ink=True,
            )
            def _click_chip(e, v=val):
                _aplicar_filtro(v)
            chip.on_click = _click_chip
            chips_row.controls.append(chip)

        area.controls.append(ft.Container(
            content=chips_row,
            padding=ft.padding.symmetric(horizontal=16, vertical=6),
        ))

        # ── ordenar e filtrar ─────────────────────────────────────────────────
        paginas_ord = sorted(
            paginas,
            key=lambda p: (p["data"] is None, p["data"] or "", p["num"]),
            reverse=True,
        )
        paginas_ord = (
            [p for p in paginas_ord if p["data"]] +
            [p for p in paginas_ord if not p["data"]]
        )

        filtro_ativo = _filtro_paginas[0]
        if filtro_ativo != "todos":
            paginas_ord = [
                pg for pg in paginas_ord
                if not pg.get("ignorado") and _classificar(pg.get("resumo") or "") == filtro_ativo
            ]

        if not paginas_ord:
            area.controls.append(ft.Container(
                content=ft.Text("Nenhuma pagina nesta categoria.", size=12, color=MUT,
                                text_align=ft.TextAlign.CENTER),
                padding=ft.padding.symmetric(vertical=24),
                alignment=ft.alignment.center,
            ))

        for pag in paginas_ord:
            jpeg      = pag["jpeg"]
            tem_img   = jpeg and os.path.exists(jpeg)
            ignorado  = pag.get("ignorado", False)
            resumo_txt = pag.get("resumo") or ""
            label_data = _para_display(pag["data"]) if pag["data"] else "Sem data"

            st        = pag.get("status", "pendente")
            cor_data  = MUT if ignorado else (TXT if pag["data"] else VERM)
            cor_icone = MUT if ignorado else (AZUL if tem_img else MUT)
            cor_bg    = BD  if ignorado else (ft.Colors.with_opacity(0.12, AZUL) if tem_img else BD)
            icone_pag = "do_not_disturb_on_rounded" if ignorado else (
                "image_rounded" if tem_img else "image_not_supported_rounded"
            )

            # badge de categoria (só quando filtro = todos)
            cat = _classificar(resumo_txt) if resumo_txt and not ignorado else None
            _CAT_COR = {"exames": VERD, "remedios": AZUL, "procedimentos": LAR}
            _CAT_ICO = {"exames": "biotech_rounded", "remedios": "medication_rounded",
                        "procedimentos": "medical_services_rounded"}

            st_cor  = {"ok": VERD, "ignorado": MUT, "pendente": VERM}.get(st, MUT)
            st_icon = {"ok": "check_circle_rounded", "ignorado": "remove_circle_outline_rounded",
                       "pendente": "error_outline_rounded"}.get(st, "help_outline_rounded")

            # badge de categoria visível apenas no filtro "todos"
            badge_cat = ft.Container(visible=False)
            if filtro_ativo == "todos" and cat in _CAT_COR:
                badge_cat = ft.Container(
                    content=ft.Icon(_CAT_ICO[cat], size=10, color=_CAT_COR[cat]),
                    bgcolor=ft.Colors.with_opacity(0.15, _CAT_COR[cat]),
                    border_radius=6, width=20, height=20,
                    alignment=ft.alignment.center,
                    tooltip=cat.capitalize(),
                )

            linha = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(icone_pag, size=15, color=cor_icone),
                        bgcolor=cor_bg, border_radius=6,
                        width=30, height=30, alignment=ft.alignment.center,
                    ),
                    ft.Column([
                        ft.Text(label_data, size=13, color=cor_data,
                                weight=ft.FontWeight.W_600),
                        ft.Text(
                            ("ignorado — " if ignorado else "") +
                            (resumo_txt[:55] if resumo_txt else "sem identificacao"),
                            size=11,
                            color=MUT if ignorado else (SEC if resumo_txt else MUT),
                            italic=ignorado or not bool(resumo_txt),
                        ),
                    ], spacing=1, tight=True, expand=True),
                    badge_cat,
                    ft.Icon(st_icon, size=14, color=st_cor),
                    ft.Icon("chevron_right_rounded", size=14, color=MUT),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD,
                border_radius=10,
                border=ft.border.all(1, BD if not ignorado else ft.Colors.with_opacity(0.27, MUT)),
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                margin=ft.margin.symmetric(horizontal=16, vertical=3),
                ink=True,
                opacity=0.5 if ignorado else 1.0,
            )

            def _abrir_pag(e, pg=pag):
                _mostrar_imagem_pagina(pg)

            linha.on_click = _abrir_pag
            area.controls.append(linha)

        area.controls.append(ft.Container(height=16))

        # ── botão Subir Drive / gate de pendências ────────────────────────────
        pron_atual = _pron_sel[0]

        # verifica se já foi subido (todas as páginas não-ignoradas têm jpeg_drive_id)
        import sqlite3 as _sq_chk
        with _sq_chk.connect(DB_PATH) as _cc:
            _n_sem_drive = _cc.execute(
                "SELECT COUNT(*) FROM prontuario_paginas "
                "WHERE prontuario_id=? AND ignorado=0 AND (jpeg_drive_id IS NULL OR jpeg_drive_id='')",
                (pron_atual["id"],)
            ).fetchone()[0]
        _ja_subido = (_n_sem_drive == 0 and n_pend == 0)

        def _avancar(_):
            import sqlite3 as _sq4
            with _sq4.connect(DB_PATH) as _c4:
                pend_rows = _c4.execute(
                    "SELECT id, pagina_num, data_pagina, jpeg_local, pdf_local, resumo, "
                    "pdf_pagina_id, dados_json, ignorado, "
                    "COALESCE(status, CASE WHEN ignorado=1 THEN 'ignorado' "
                    "                      WHEN data_pagina IS NOT NULL THEN 'ok' "
                    "                      ELSE 'pendente' END) "
                    "FROM prontuario_paginas WHERE prontuario_id=? AND "
                    "(status='pendente' OR (status IS NULL AND data_pagina IS NULL AND "
                    "(ignorado IS NULL OR ignorado=0)))",
                    (pron_atual["id"],)
                ).fetchall()
            if pend_rows:
                pend_list = [
                    {"id": r[0], "num": r[1], "data": r[2], "jpeg": r[3], "pdf": r[4],
                     "resumo": r[5], "pdf_pagina_id": r[6], "dados_json": r[7],
                     "ignorado": bool(r[8]), "status": r[9]}
                    for r in pend_rows
                ]
                _mostrar_pendentes(pend_list)
            else:
                _iniciar_fase35(pron_atual["id"])

        def _mostrar_pendentes(pend_list):
            itens_pend = []
            for pg in pend_list:
                def _ir(e, _pg=pg):
                    _fechar_overlay()
                    _mostrar_imagem_pagina(_pg)
                linha_p = ft.Container(
                    content=ft.Row([
                        ft.Icon("error_outline_rounded", size=13, color=VERM),
                        ft.Text(
                            f"Pag {pg['num']} — {_para_display(pg['data']) if pg['data'] else 'sem data'}",
                            size=12, color=TXT, expand=True,
                        ),
                        ft.Text(pg.get("resumo", "")[:30] or "sem identificacao",
                                size=10, color=SEC),
                        ft.Icon("chevron_right_rounded", size=12, color=MUT),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=BD, border_radius=8, ink=True,
                    padding=ft.padding.symmetric(horizontal=10, vertical=8),
                )
                linha_p.on_click = _ir
                itens_pend.append(linha_p)

            btn_fechar_p = ft.Container(
                content=ft.Text("Fechar", size=12, color=SEC),
                border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                border=ft.border.all(1, BD),
            )
            btn_fechar_p.on_click = lambda _: _fechar_overlay()

            _mostrar_overlay(ft.Column([
                ft.Icon("pending_actions_rounded", size=28, color=VERM),
                ft.Container(height=4),
                ft.Text("Paginas pendentes", size=14, color=TXT,
                        weight=ft.FontWeight.W_700),
                ft.Text(
                    f"{len(pend_list)} pagina(s) sem data — corrija para avancar",
                    size=11, color=SEC, text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=8),
                ft.Column(itens_pend, spacing=4,
                          scroll=ft.ScrollMode.AUTO,
                          height=min(len(itens_pend) * 46, 250)),
                ft.Container(height=10),
                btn_fechar_p,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               tight=True, spacing=4, width=300))

        if _ja_subido:
            _btn_icone = "cloud_done_rounded"
            _btn_label = "Drive atualizado — re-enviar"
            _btn_cor   = VERD
            _btn_tcor  = BG
        elif n_pend == 0:
            _btn_icone = "cloud_upload_rounded"
            _btn_label = "Subir para o Drive"
            _btn_cor   = AZUL
            _btn_tcor  = BG
        else:
            _btn_icone = "lock_rounded"
            _btn_label = f"Subir ({n_pend} pendente{'s' if n_pend != 1 else ''})"
            _btn_cor   = MUT
            _btn_tcor  = SEC

        area.controls.append(ft.Container(
            content=ft.Row([
                ft.Icon(_btn_icone, size=14, color=_btn_tcor),
                ft.Text(_btn_label, size=12, color=_btn_tcor, weight=ft.FontWeight.W_600),
            ], spacing=6, tight=True, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=_btn_cor,
            border_radius=10, ink=True,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            margin=ft.margin.symmetric(horizontal=16, vertical=4),
            on_click=_avancar,
        ))

        # ── botão Fase 4 — Identificar Internações ───────────────────────────
        # disponível quando não há pendências (independente do Drive)
        if n_pend == 0:
            area.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("local_hospital_rounded", size=14, color=BG),
                    ft.Text("Identificar Internacoes", size=12, color=BG,
                            weight=ft.FontWeight.W_600),
                ], spacing=6, tight=True, alignment=ft.MainAxisAlignment.CENTER),
                bgcolor=ROXO,
                border_radius=10, ink=True,
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                margin=ft.margin.symmetric(horizontal=16, vertical=4),
                on_click=lambda _: _iniciar_fase4(pron_atual["id"]),
            ))

        area.controls.append(ft.Container(height=24))

    # ── overlay com imagem + edição de data ──────────────────────────────────
    def _mostrar_imagem_pagina(pag: dict):
        import sqlite3 as _sq
        jpeg        = pag.get("jpeg")
        drive_id    = pag.get("jpeg_drive_id")
        tem_local   = bool(jpeg and os.path.exists(jpeg))

        # pasta de cache local para imagens vindas do Drive
        _HERE_TELA = os.path.dirname(os.path.abspath(__file__))
        _CACHE_DIR = os.path.join(_HERE_TELA, "..", "temp", "cache")

        # placeholder enquanto baixa (substituído após download)
        img_ctrl = ft.Image(src="", width=270, fit=ft.ImageFit.CONTAIN,
                            border_radius=ft.border_radius.all(8))
        img_placeholder = ft.Container(
            content=ft.Column([
                ft.ProgressRing(width=24, height=24, stroke_width=2, color=AZUL),
                ft.Text("Carregando...", size=11, color=SEC),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               spacing=6, tight=True),
            width=270, height=160, bgcolor=BD, border_radius=8,
            alignment=ft.alignment.center,
        )
        img_erro = ft.Container(
            content=ft.Column([
                ft.Icon("image_not_supported_rounded", size=32, color=MUT),
                ft.Text("Imagem nao encontrada", size=11, color=MUT),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               spacing=6, tight=True),
            width=270, height=160, bgcolor=BD, border_radius=8,
            alignment=ft.alignment.center,
        )

        # container que troca entre placeholder → imagem ou erro
        img_wrap = ft.Container(content=img_placeholder, width=270)

        def _carregar_imagem():
            """Resolve local ou baixa do Drive; atualiza img_wrap."""
            if tem_local:
                img_wrap.content = ft.Image(
                    src=jpeg, width=270,
                    fit=ft.ImageFit.CONTAIN,
                    border_radius=ft.border_radius.all(8),
                )
                try: page.update()
                except Exception: pass
                return

            if drive_id:
                cache_path = os.path.join(_CACHE_DIR, f"{pag['id']}.jpg")
                if not os.path.exists(cache_path):
                    try:
                        from utils.drive_sync import baixar_foto
                        os.makedirs(_CACHE_DIR, exist_ok=True)
                        baixar_foto(drive_id, cache_path)
                    except Exception as _ex:
                        log.warning("[IMG] download Drive pag %d: %s", pag["id"], _ex)
                        img_wrap.content = img_erro
                        try: page.update()
                        except Exception: pass
                        return
                # atualiza jpeg local em memória para o botão "Abrir" funcionar
                pag["jpeg"] = cache_path
                img_wrap.content = ft.Image(
                    src=cache_path, width=270,
                    fit=ft.ImageFit.CONTAIN,
                    border_radius=ft.border_radius.all(8),
                )
                try: page.update()
                except Exception: pass
                return

            img_wrap.content = img_erro
            try: page.update()
            except Exception: pass

        threading.Thread(target=_carregar_imagem, daemon=True).start()
        tem_img = tem_local or bool(drive_id)

        # campo de data editável
        data_atual = pag["data"] or ""
        tf_data = ft.TextField(
            value=_para_display(data_atual) if data_atual else "",
            hint_text="DD/MM/AAAA",
            bgcolor=BD, border_color=BD2, focused_border_color=AZUL,
            hint_style=ft.TextStyle(color=MUT),
            text_style=ft.TextStyle(color=TXT, size=13),
            border_radius=8, height=40, expand=True,
            prefix_icon="calendar_today_rounded",
        )

        # campo de resumo editável
        tf_resumo = ft.TextField(
            value=pag.get("resumo") or "",
            hint_text="Tipo do documento (ex: Alta hospitalar)",
            bgcolor=BD, border_color=BD2, focused_border_color=AZUL,
            hint_style=ft.TextStyle(color=MUT),
            text_style=ft.TextStyle(color=TXT, size=12),
            border_radius=8, height=40, expand=True,
            prefix_icon="label_outline_rounded",
        )
        msg_data = ft.Text("", size=11, color=VERM)

        def _salvar_data(_):
            import json as _j
            val = (tf_data.value or "").strip()
            # aceita DD/MM/AAAA ou YYYY-MM-DD
            nova_iso = None
            for fmt, src in [("%d/%m/%Y", val), ("%Y-%m-%d", val)]:
                try:
                    nova_iso = datetime.datetime.strptime(src[:10], fmt).strftime("%Y-%m-%d")
                    break
                except ValueError:
                    pass
            if not nova_iso and val:
                msg_data.value = "Use DD/MM/AAAA"
                try: page.update()
                except Exception: pass
                return

            novo_resumo = (tf_resumo.value or "").strip() or None

            try:
                novo_status = "ok" if nova_iso else "pendente"
                with _sq.connect(DB_PATH) as _c:
                    _c.execute(
                        "UPDATE prontuario_paginas SET data_pagina=?, resumo=?, status=? WHERE id=?",
                        (nova_iso, novo_resumo, novo_status, pag["id"])
                    )
                    # atualizar dados_json: corrigir data e resumo dentro do JSON armazenado
                    raw = pag.get("dados_json") or "{}"
                    try:
                        jd = _j.loads(raw)
                    except Exception:
                        jd = {}
                    if nova_iso:
                        jd["data"] = nova_iso
                    if novo_resumo is not None:
                        jd["resumo"] = novo_resumo
                    novo_json = _j.dumps(jd, ensure_ascii=False)
                    _c.execute(
                        "UPDATE prontuario_paginas SET dados_json=? WHERE id=?",
                        (novo_json, pag["id"])
                    )
                    # atualizar também pdf_paginas.dados_json
                    patch = {}
                    if nova_iso:   patch["data_pagina"] = nova_iso
                    if novo_resumo is not None: patch["resumo"] = novo_resumo
                    _c.execute(
                        "UPDATE pdf_paginas SET dados_json=json_patch(COALESCE(dados_json,'{}'), ?) WHERE id=?",
                        (_j.dumps(patch),
                         pag["pdf_pagina_id"] if pag.get("pdf_pagina_id") else -1)
                    )
                pag["data"]      = nova_iso
                pag["resumo"]    = novo_resumo
                pag["status"]    = novo_status
                pag["dados_json"] = novo_json
                msg_data.value = "Salvo!"
                msg_data.color = VERD
                try: page.update()
                except Exception: pass
            except Exception as ex:
                msg_data.value = str(ex)[:80]
                try: page.update()
                except Exception: pass

        btn_salvar = ft.Container(
            content=ft.Icon("check_rounded", size=16, color=BG),
            bgcolor=VERD, border_radius=8, ink=True,
            padding=ft.padding.all(8),
            tooltip="Salvar data",
        )
        btn_salvar.on_click = _salvar_data

        ignorado_state = [pag.get("ignorado", False)]

        btn_fechar = ft.Container(
            content=ft.Text("Fechar", size=12, color=SEC),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border=ft.border.all(1, BD),
        )
        btn_fechar.on_click = lambda _: (_fechar_overlay(), _rebuild())

        # botão ignorar / restaurar
        lbl_ignorar = ft.Text(
            "Restaurar" if ignorado_state[0] else "Ignorar",
            size=12, color=AMAR,
        )
        btn_ignorar = ft.Container(
            content=ft.Row([
                ft.Icon("do_not_disturb_on_rounded", size=14, color=AMAR),
                lbl_ignorar,
            ], spacing=4, tight=True),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border=ft.border.all(1, ft.Colors.with_opacity(0.40, AMAR)),
        )

        def _toggle_ignorar(_):
            novo = not ignorado_state[0]
            novo_status = "ignorado" if novo else ("ok" if pag.get("data") else "pendente")
            try:
                with _sq.connect(DB_PATH) as _c:
                    _c.execute(
                        "UPDATE prontuario_paginas SET ignorado=?, status=? WHERE id=?",
                        (1 if novo else 0, novo_status, pag["id"])
                    )
                ignorado_state[0] = novo
                pag["ignorado"] = novo
                pag["status"] = novo_status
                lbl_ignorar.value = "Restaurar" if novo else "Ignorar"
                try: page.update()
                except Exception: pass
            except Exception as ex:
                msg_data.value = str(ex)[:80]
                try: page.update()
                except Exception: pass

        btn_ignorar.on_click = _toggle_ignorar

        # botão ver JSON
        json_area = ft.Container(visible=False)

        def _ver_json(_):
            raw = pag.get("dados_json")
            if not raw:
                json_area.content = ft.Text("Sem JSON disponivel.", size=11, color=MUT)
            else:
                try:
                    import json as _j
                    pretty = _j.dumps(_j.loads(raw), ensure_ascii=False, indent=2)
                except Exception:
                    pretty = raw
                json_area.content = ft.Container(
                    content=ft.Text(pretty, size=10, color=TXT,
                                    selectable=True, font_family="monospace"),
                    bgcolor=BD, border_radius=8,
                    padding=ft.padding.all(10),
                    width=270,
                )
            json_area.visible = not json_area.visible
            try: page.update()
            except Exception: pass

        btn_json = ft.Container(
            content=ft.Row([
                ft.Icon("data_object_rounded", size=14, color=ROXO),
                ft.Text("JSON", size=12, color=ROXO),
            ], spacing=4, tight=True),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border=ft.border.all(1, ft.Colors.with_opacity(0.40, ROXO)),
        )
        btn_json.on_click = _ver_json

        botoes_linha2 = [btn_ignorar, btn_json]

        if tem_img:
            btn_abrir = ft.Container(
                content=ft.Row([
                    ft.Icon("open_in_new_rounded", size=14, color=BG),
                    ft.Text("Abrir", size=12, color=BG,
                            weight=ft.FontWeight.W_600),
                ], spacing=4, tight=True),
                bgcolor=AZUL, border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
            )
            def _abrir_browser(_):
                _src = pag.get("jpeg") or ""
                if not _src:
                    _snack("Imagem ainda nao carregada.", AMAR)
                    return
                try:
                    page.launch_url(f"file:///{_src.replace(os.sep, '/')}")
                except Exception:
                    import webbrowser
                    webbrowser.open(_src)
            btn_abrir.on_click = _abrir_browser
            botoes_linha2.insert(0, btn_abrir)

        # ── botão Transferir para Exame ──────────────────────────────
        _ja_exportado = "→ exame" in (pag.get("resumo") or "").lower()
        btn_exame = ft.Container(
            content=ft.Row([
                ft.Icon("biotech_rounded", size=14, color=VERD),
                ft.Text("Reprocessar" if _ja_exportado else "→ Exame",
                        size=12, color=VERD, weight=ft.FontWeight.W_600),
            ], spacing=4, tight=True),
            border_radius=8, ink=True,
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border=ft.border.all(1, ft.Colors.with_opacity(0.40, VERD)),
            tooltip="Reprocessar e salvar novo resultado de exame" if _ja_exportado else "Extrair resultado e transferir para tabela de exames",
            opacity=0.75 if _ja_exportado else 1.0,
        )

        PROMPT_EXAME = """Voce recebe a imagem de um resultado de exame de laboratorio ou de imagem de um prontuario hospitalar brasileiro.
Extraia os dados abaixo. Se nao for resultado de exame, retorne {"nao_exame": true}.

Retorne SOMENTE JSON (sem markdown):
{
  "tipo_exame": "nome do exame (ex: Hemograma completo, Glicemia, Ecocardiograma)",
  "data_exame": "YYYY-MM-DD ou null",
  "laboratorio": "nome do laboratorio ou clinica ou null",
  "medico_solicit": "nome do medico solicitante ou null",
  "resultado_texto": "texto completo do resultado/laudo em ate 800 chars ou null",
  "conclusao": "conclusao ou impressao diagnostica em ate 200 chars ou null",
  "resultados": [
    {"parametro": "nome", "valor": "valor numerico ou texto", "unidade": "unidade ou null", "referencia": "faixa de referencia ou null"}
  ]
}
Se nao houver resultados numericos estruturados, retorne resultados=[].
"""

        def _iniciar_extracao_exame(_):
            if not tem_img:
                _snack("Sem imagem para processar.", AMAR)
                return

            # spinner enquanto processa
            _mostrar_overlay(ft.Column([
                ft.ProgressRing(width=28, height=28, stroke_width=3, color=VERD),
                ft.Container(height=8),
                ft.Text("Extraindo dados do exame...", size=12, color=TXT,
                        text_align=ft.TextAlign.CENTER),
                ft.Text("Aguarde — Claude Haiku analisando a imagem",
                        size=10, color=MUT, text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               tight=True, spacing=4, width=260))

            def _run():
                try:
                    import base64 as _b64, json as _j
                    from utils.claudia_engine import get_client

                    # resolve caminho da imagem (local ou cache Drive)
                    src_jpeg = pag.get("jpeg") or ""
                    if not (src_jpeg and os.path.exists(src_jpeg)):
                        _fechar_overlay()
                        _snack("Imagem nao disponivel localmente.", AMAR)
                        return

                    with open(src_jpeg, "rb") as f:
                        img_b64 = _b64.b64encode(f.read()).decode()

                    client = get_client()
                    resp = client.messages.create(
                        model="claude-haiku-4-5-20251001",
                        max_tokens=1000,
                        messages=[{"role": "user", "content": [
                            {"type": "image", "source": {
                                "type": "base64", "media_type": "image/jpeg",
                                "data": img_b64}},
                            {"type": "text", "text": PROMPT_EXAME},
                        ]}],
                        timeout=40,
                    )
                    txt = resp.content[0].text.strip()
                    if txt.startswith("```"):
                        txt = txt.split("```")[1].lstrip("json").strip()
                    dados = _j.loads(txt)

                    if dados.get("nao_exame"):
                        _fechar_overlay()
                        _snack("Esta pagina nao parece ser um resultado de exame.", AMAR)
                        return

                    _mostrar_confirmacao_exame(dados)

                except Exception as ex:
                    import traceback
                    log.error("[EXAME] %s\n%s", ex, traceback.format_exc())
                    _fechar_overlay()
                    _snack(f"Erro ao extrair: {str(ex)[:100]}", VERM)

            threading.Thread(target=_run, daemon=True).start()

        btn_exame.on_click = _iniciar_extracao_exame

        def _mostrar_confirmacao_exame(dados: dict):
            """Overlay de confirmação com campos editáveis antes de gravar."""
            import json as _j

            tf_tipo = ft.TextField(
                value=dados.get("tipo_exame") or "",
                label="Tipo de exame", bgcolor=BD, border_color=BD2,
                focused_border_color=VERD, label_style=ft.TextStyle(color=SEC, size=10),
                text_style=ft.TextStyle(color=TXT, size=12), border_radius=8, height=40,
            )
            tf_data_ex = ft.TextField(
                value=_para_display(dados.get("data_exame")) or _para_display(pag.get("data")) or "",
                label="Data do exame", bgcolor=BD, border_color=BD2,
                focused_border_color=VERD, label_style=ft.TextStyle(color=SEC, size=10),
                text_style=ft.TextStyle(color=TXT, size=12), border_radius=8, height=40,
            )
            tf_lab = ft.TextField(
                value=dados.get("laboratorio") or "",
                label="Laboratorio / clinica", bgcolor=BD, border_color=BD2,
                focused_border_color=VERD, label_style=ft.TextStyle(color=SEC, size=10),
                text_style=ft.TextStyle(color=TXT, size=12), border_radius=8, height=40,
            )
            tf_medico = ft.TextField(
                value=dados.get("medico_solicit") or "",
                label="Medico solicitante", bgcolor=BD, border_color=BD2,
                focused_border_color=VERD, label_style=ft.TextStyle(color=SEC, size=10),
                text_style=ft.TextStyle(color=TXT, size=12), border_radius=8, height=40,
            )
            tf_conclusao = ft.TextField(
                value=dados.get("conclusao") or "",
                label="Conclusao / impressao", bgcolor=BD, border_color=BD2,
                focused_border_color=VERD, label_style=ft.TextStyle(color=SEC, size=10),
                text_style=ft.TextStyle(color=TXT, size=12), border_radius=8,
                multiline=True, min_lines=2, max_lines=4,
            )

            resultados = dados.get("resultados") or []
            n_res = len(resultados)
            resumo_res = ft.Text(
                f"{n_res} resultado{'s' if n_res != 1 else ''} estruturado{'s' if n_res != 1 else ''} extraido{'s' if n_res != 1 else ''}",
                size=10, color=VERD if n_res else MUT, italic=True,
            )

            msg_conf = ft.Text("", size=11, color=VERM)

            btn_cancelar_conf = ft.Container(
                content=ft.Text("Cancelar", size=12, color=SEC),
                border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                border=ft.border.all(1, BD),
            )
            btn_cancelar_conf.on_click = lambda _: _mostrar_imagem_pagina(pag)

            btn_gravar = ft.Container(
                content=ft.Row([
                    ft.Icon("save_rounded", size=14, color=BG),
                    ft.Text("Gravar exame", size=12, color=BG,
                            weight=ft.FontWeight.W_600),
                ], spacing=4, tight=True),
                bgcolor=VERD, border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
            )

            def _gravar(_):
                import sqlite3 as _sq2
                # parse data
                val_data = (tf_data_ex.value or "").strip()
                data_iso = None
                for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        data_iso = datetime.datetime.strptime(val_data[:10], fmt).strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        pass

                tipo_exame = (tf_tipo.value or "").strip() or "Exame"

                dados_gravar = {
                    "tipo": "numerico" if resultados else "laudo",
                    "tipo_exame": tipo_exame,
                    "data_exame": data_iso or pag.get("data"),
                    "laboratorio": (tf_lab.value or "").strip() or None,
                    "medico_solicit": (tf_medico.value or "").strip() or None,
                    "resultado_texto": dados.get("resultado_texto"),
                    "drive_file_id": pag.get("jpeg_drive_id") or None,
                    "arquivo_origem": pag.get("jpeg") or None,
                    "internacao_id": pag.get("internacao_id"),
                    "resultados": resultados,
                    "laudo": {
                        "texto_completo": dados.get("resultado_texto"),
                        "conclusao": (tf_conclusao.value or "").strip() or None,
                        "resumo": tipo_exame,
                    } if (dados.get("resultado_texto") or tf_conclusao.value) else None,
                }

                try:
                    from dados.model_prontuario import salvar_exame
                    exame_id = salvar_exame(dados_gravar)

                    # se tem drive_id da página, registra também em exame_anexos
                    drive_id_pag = pag.get("jpeg_drive_id")
                    if drive_id_pag and exame_id:
                        with _sq2.connect(DB_PATH) as _c:
                            _c.execute(
                                "INSERT INTO exame_anexos (exame_id, drive_file_id, nome_arquivo, ordem) "
                                "VALUES (?,?,?,0)",
                                (exame_id, drive_id_pag, f"{pag['id']}.jpg")
                            )

                    # atualiza resumo da página para registrar a exportação
                    novo_resumo = f"{tipo_exame} → exame #{exame_id}"
                    with _sq2.connect(DB_PATH) as _c:
                        _c.execute(
                            "UPDATE prontuario_paginas SET resumo=? WHERE id=?",
                            (novo_resumo, pag["id"])
                        )
                    pag["resumo"] = novo_resumo

                    _fechar_overlay()
                    _snack(f"Exame #{exame_id} gravado com sucesso!", VERD)
                    _rebuild()

                except Exception as ex:
                    log.error("[EXAME_GRAVAR] %s", ex)
                    msg_conf.value = str(ex)[:120]
                    try: page.update()
                    except Exception: pass

            btn_gravar.on_click = _gravar

            _mostrar_overlay(ft.Column([
                ft.Row([
                    ft.Icon("biotech_rounded", size=16, color=VERD),
                    ft.Text("Confirmar exame", size=13, color=TXT,
                            weight=ft.FontWeight.W_700, expand=True),
                ], spacing=6),
                ft.Container(height=6),
                tf_tipo,
                ft.Container(height=4),
                ft.Row([tf_data_ex, tf_lab], spacing=8),
                ft.Container(height=4),
                tf_medico,
                ft.Container(height=4),
                tf_conclusao,
                ft.Container(height=4),
                resumo_res,
                msg_conf,
                ft.Container(height=8),
                ft.Row([btn_cancelar_conf, btn_gravar], spacing=8,
                       alignment=ft.MainAxisAlignment.CENTER),
            ], tight=True, spacing=4, width=300, scroll=ft.ScrollMode.AUTO))

        _mostrar_overlay(ft.Column([
            ft.Row([
                ft.Icon("description_rounded", size=14, color=AZUL),
                ft.Text(f"Pagina {pag['num']}", size=13, color=TXT,
                        weight=ft.FontWeight.W_600, expand=True),
            ], spacing=6),
            ft.Container(height=4),
            img_wrap,
            ft.Container(height=10),
            ft.Row([tf_data, btn_salvar], spacing=6,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(height=4),
            tf_resumo,
            msg_data,
            ft.Container(height=6),
            ft.Row(botoes_linha2, spacing=6, alignment=ft.MainAxisAlignment.CENTER,
                   wrap=True),
            ft.Container(
                content=ft.Row([
                    ft.Icon("biotech_rounded", size=13, color=VERD),
                    ft.Text("→ Exame", size=11, color=VERD, weight=ft.FontWeight.W_600,
                            expand=True),
                    ft.Text("reprocessar" if _ja_exportado else "transferir para exames",
                            size=10, color=MUT, italic=True),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=ft.Colors.with_opacity(0.07, VERD),
                border_radius=8, ink=True,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border=ft.border.all(1, ft.Colors.with_opacity(0.30, VERD)),
                on_click=_iniciar_extracao_exame,
            ),
            json_area,
            ft.Container(height=6),
            ft.Row([btn_fechar], alignment=ft.MainAxisAlignment.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           tight=True, spacing=4, width=300,
           scroll=ft.ScrollMode.AUTO))

    # ── cabeçalho padrão Koios ────────────────────────────────────────────────
    from shared.layout import Layout
    lay = Layout(page)

    titulo_txt = ft.Text("Prontuarios", size=14, color=TXT,
                         weight=ft.FontWeight.W_700)
    sub_txt    = ft.Text("", size=11, color=SEC)

    _titulo_col = ft.Row([
        ft.Icon("folder_open_rounded", size=15, color=AZUL),
        ft.Column([titulo_txt, sub_txt], spacing=0, tight=True),
    ], spacing=6, tight=True)

    btn_importar_cab = ft.Container(
        content=ft.Row([
            ft.Icon("upload_file_rounded", size=14, color=AZUL),
            ft.Text("PDF", size=12, color=AZUL),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        border_radius=8, ink=True,
        tooltip="Importar prontuario PDF",
    )
    btn_importar_cab.on_click = lambda _: _importar_pdf()

    btn_voltar_cab = ft.Container(
        content=ft.Row([
            ft.Icon("arrow_back", size=16, color=AZUL),
            ft.Text("Voltar", size=13, color=AZUL),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        border_radius=8, ink=True,
    )

    def _atualizar_cabecalho():
        if _vista[0] == "lista":
            titulo_txt.value = "Prontuarios"
            sub_txt.value    = ""
        else:
            p = _pron_sel[0]
            titulo_txt.value = (p["hospital"] or p["nome"] or "")[:28]
            sub_txt.value    = f"{p['total']} paginas"
        try: page.update()
        except Exception: pass

    def _voltar_ou_hub():
        if _vista[0] == "paginas":
            _vista[0] = "lista"
            _pron_sel[0] = None
            _atualizar_cabecalho()
            _rebuild()
        elif voltar_fn:
            voltar_fn()

    btn_voltar_cab.on_click = lambda _: _voltar_ou_hub()

    cabecalho = ft.Container(
        content=ft.Row(
            [btn_voltar_cab, _titulo_col, btn_importar_cab],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=lay.cabecalho_padding(),
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
    )

    corpo = ft.Stack([
        ft.Column([
            cabecalho,
            _banner_pend,
            ft.Container(
                content=area,
                expand=True,
            ),
        ], expand=True, spacing=0),
        _overlay,
    ], expand=True)

    _rebuild()
    return ft.Container(content=corpo, bgcolor=BG, expand=True)
