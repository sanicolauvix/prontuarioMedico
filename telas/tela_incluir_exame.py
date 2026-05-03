# -*- coding: utf-8 -*-
# KOIOS v1.0 | gerado: 2026-03-13 | tela_incluir_exame.py
"""
tela_incluir_exame.py
Fluxo:
  1. Seleciona PDF
  2. Cache hit? → pula extração (usa JSON em temp/cache_extracao/<md5>.json)
     Cache miss? → extrai localmente → salva cache → conferência
  3. Conferência → resolve pendências → confirmar
  4. Liberação: upload Drive → grava banco → sync

Cache de extração:
  - Localização: <projeto>/temp/cache_extracao/<hash_md5>.json
  - Válido enquanto o PDF não mudar (hash MD5 do conteúdo)
  - Botão "Reprocessar" na tela força novo processamento apagando o cache
"""

import flet as ft
import threading
import logging
import os
import time
import json
import hashlib
from pathlib import Path

BG   = "#0D1117"
CARD = "#161B22"
BD   = "#21262D"
BD2  = "#30363D"
TXT  = "#E6EDF3"
SEC  = "#8B949E"
MUT  = "#484F58"
AZUL = "#58A6FF"
VERD = "#3FB950"
VERM = "#DA3633"
LAR  = "#F0883E"
AMAR = "#D29922"

# ══════════════════════════════════════════════════════════════════════════════
# CACHE DE EXTRAÇÃO — evita reprocessar PDFs já extraídos durante testes
# ══════════════════════════════════════════════════════════════════════════════

_CACHE_DIR = Path(__file__).parent.parent / "temp" / "cache_extracao"

def _cache_path(conteudo_bytes: bytes) -> Path:
    """Retorna o caminho do arquivo de cache para este PDF (baseado no MD5)."""
    md5 = hashlib.md5(conteudo_bytes).hexdigest()
    return _CACHE_DIR / f"{md5}.json"

def _cache_ler(conteudo_bytes: bytes) -> dict | None:
    """Lê cache se existir. Retorna dict ou None."""
    try:
        p = _cache_path(conteudo_bytes)
        if p.exists():
            dados = json.loads(p.read_text(encoding="utf-8"))
            logging.info(f"[CACHE] HIT — {p.name}")
            return dados
    except Exception as ex:
        logging.warning(f"[CACHE] Erro ao ler cache: {ex}")
    return None

def _cache_salvar(conteudo_bytes: bytes, dados: dict):
    """Salva resultado da extração em cache JSON."""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        p = _cache_path(conteudo_bytes)
        # Não salvar bytes no cache — apenas dados serializáveis
        dados_clean = {k: v for k, v in dados.items()
                       if k not in ("arquivo_path", "arquivo_origem")}
        p.write_text(json.dumps(dados_clean, ensure_ascii=False, indent=2),
                     encoding="utf-8")
        logging.info(f"[CACHE] SALVO — {p.name} ({p.stat().st_size//1024}KB)")
    except Exception as ex:
        logging.warning(f"[CACHE] Erro ao salvar cache: {ex}")

def _cache_apagar(conteudo_bytes: bytes):
    """Apaga cache de um PDF específico (para forçar reprocessamento)."""
    try:
        p = _cache_path(conteudo_bytes)
        if p.exists():
            p.unlink()
            logging.info(f"[CACHE] APAGADO — {p.name}")
            return True
    except Exception as ex:
        logging.warning(f"[CACHE] Erro ao apagar cache: {ex}")
    return False

def _cache_info(conteudo_bytes: bytes) -> str | None:
    """Retorna string com info do cache se existir (data de criação)."""
    try:
        import datetime
        p = _cache_path(conteudo_bytes)
        if p.exists():
            ts = datetime.datetime.fromtimestamp(p.stat().st_mtime)
            return ts.strftime("%d/%m %H:%M")
    except Exception:
        pass
    return None


def criar_tela_incluir_exame(page: ft.Page, voltar_fn):
    import logging as _log
    _log.info("[INCLUIR] *** ARQUIVO NOVO CARREGADO — versão com progresso ***")
    print("[INCLUIR] *** ARQUIVO NOVO CARREGADO — versão com progresso ***")

    try:
        larg = page.width or 800
    except Exception:
        larg = 800

    # ── Estado ────────────────────────────────────────────────
    fase         = ["selecao"]   # selecao | processando | conferencia | liberando
    caminho_sel  = [""]
    dados_extra  = [None]        # dados extraídos do PDF — fica em memória até confirmar
    pendencias   = [[]]          # parâmetros sem vínculo
    _dup_info    = [None]        # contexto de duplicata detectada (dict rico)

    area = ft.Column(
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    def _rebuild():
        area.controls.clear()
        {
            "selecao":     lambda: area.controls.extend(_tela_selecao()),
            "processando": lambda: area.controls.extend(_tela_processando()),
            "conferencia": lambda: area.controls.extend(_tela_conferencia()),
            "liberando":   lambda: area.controls.extend(_tela_liberando()),
            "drive_falhou":          lambda: area.controls.extend(_tela_drive_falhou()),
            "modelo_nao_configurado": lambda: area.controls.extend(_tela_modelo_nao_configurado()),
        }.get(fase[0], lambda: None)()
        page.update()
        # _dup_info é renderizado inline na _tela_selecao

    def _voltar_selecao(e=None):
        fase[0]        = "selecao"
        caminho_sel[0] = ""
        dados_extra[0] = None
        _dup_info[0]   = None
        pendencias[0]    = []
        f_path.value     = ""
        nome_txt.value   = ""
        card_arq.visible          = False
        _cache_badge.visible      = False
        _btn_limpar_cache.visible = False
        _rebuild()

    # ── Seleção de arquivo ────────────────────────────────────
    def _set_arquivo(caminho):
        if not caminho: return
        caminho_sel[0]      = caminho
        f_path.value        = caminho
        nome_txt.value      = os.path.basename(caminho)
        card_arq.visible    = True
        # Preview — mostra botão para abrir PDF no browser
        _preview_status.value   = "PDF selecionado — abra para conferir antes de analisar."
        _preview_btn.visible    = True
        preview_pdf.visible     = True
        # Checar cache
        try:
            _conteudo_tmp = Path(caminho).read_bytes()
            _info = _cache_info(_conteudo_tmp)
            if _info:
                _cache_badge.value   = f"⚡ Cache disponível ({_info}) — análise será instantânea"
                _cache_badge.color   = VERD
                _cache_badge.visible = True
                _btn_limpar_cache.visible = True
            else:
                _cache_badge.visible      = False
                _btn_limpar_cache.visible = False
        except Exception:
            _cache_badge.visible      = False
            _btn_limpar_cache.visible = False
        try:
            page.update()
        except Exception:
            pass

    def _limpar(e=None):
        caminho_sel[0]          = ""
        f_path.value            = ""
        nome_txt.value          = ""
        card_arq.visible        = False
        preview_pdf.visible     = False
        _preview_btn.visible    = False
        _preview_status.value   = ""
        try:
            page.update()
        except Exception:
            pass

    def _abrir_tkinter(e):
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk(); root.withdraw()
            root.wm_attributes("-topmost", True)
            caminho = filedialog.askopenfilename(
                title="Selecione um PDF",
                filetypes=[("PDF files", "*.pdf")],
            )
            root.destroy()
            if caminho:
                _set_arquivo(caminho)
        except Exception as ex:
            logging.exception(f"[TKINTER] {ex}")

    f_path = ft.TextField(
        label="Caminho completo do PDF",
        hint_text="Ex: C:/Users/usuario/Downloads/exame.pdf",
        hint_style=ft.TextStyle(color=MUT),
        bgcolor=CARD, border_color=BD, focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, expand=True,
    )
    f_path.on_change = lambda e: _set_arquivo(e.control.value or "")

    nome_txt = ft.Text("", size=13, color=TXT, expand=True, no_wrap=True,
                       overflow=ft.TextOverflow.ELLIPSIS)
    card_arq = ft.Container(
        visible=False,
        content=ft.Row([
            ft.Icon("picture_as_pdf_rounded", size=18, color=VERM),
            nome_txt,
            ft.IconButton("close_rounded", icon_size=14, icon_color=SEC,
                          on_click=_limpar),
        ], spacing=10),
        bgcolor=CARD, border_radius=8, padding=10,
        border=ft.Border(
            left=ft.BorderSide(2, VERM),
            top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
            right=ft.BorderSide(1, BD),
        ),
    )

    # ── Badge de cache ───────────────────────────────────────
    _cache_badge = ft.Text("", size=11, color=VERD, visible=False,
                           italic=True)

    def _limpar_cache_click(e):
        try:
            conteudo_tmp = Path(caminho_sel[0]).read_bytes()
            _cache_apagar(conteudo_tmp)
            _cache_badge.visible      = False
            _btn_limpar_cache.visible = False
            _cache_badge.value        = ""
            page.update()
        except Exception as _ex:
            logging.warning(f"[CACHE] limpar_cache_click: {_ex}")

    _btn_limpar_cache = ft.Container(
        content=ft.Row([
            ft.Icon("refresh_outlined_rounded", size=12, color=AMAR),
            ft.Text("Reprocessar do zero", size=11, color=AMAR),
        ], spacing=4, tight=True),
        visible=False,
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        ink=True,
        on_click=_limpar_cache_click,
    )

    # ── Preview inline do PDF ─────────────────────────────────
    # ft.WebView não existe no Flet 0.82.0 — solução: converter PDF
    # para base64 e embutir via ft.Column com indicador de carregamento.
    # O preview abre o PDF no browser via webbrowser.open_new_tab().
    # Documentado: Flet 0.82.0 / Flutter 3.41.4 / Pyodide 0.27.7
    _preview_status = ft.Text("", size=12, color=MUT, italic=True)
    _preview_btn    = ft.OutlinedButton(
        content=ft.Row([
            ft.Icon("picture_as_pdf_rounded", size=15, color=VERM),
            ft.Text("Abrir PDF para conferir", size=13, color=TXT),
        ], spacing=6, tight=True),
        style=ft.ButtonStyle(
            side=ft.BorderSide(1, BD2),
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.Padding(left=14, right=14, top=10, bottom=10),
        ),
        visible=False,
        on_click=lambda e: _abrir_pdf_preview(),
    )
    preview_pdf = ft.Container(
        visible=False,
        content=ft.Column([
            _preview_status,
            _preview_btn,
        ], spacing=6, horizontal_alignment=ft.CrossAxisAlignment.START),
        padding=ft.padding.symmetric(vertical=6),
    )

    def _abrir_pdf_preview():
        caminho = caminho_sel[0]
        if not caminho:
            return
        try:
            import webbrowser
            uri = Path(caminho).resolve().as_uri()
            webbrowser.open_new_tab(uri)
        except Exception as ex:
            logging.warning(f"[PREVIEW] {ex}")

    # ── Status / progresso ────────────────────────────────────
    status_txt      = ft.Text("", size=14, color=AZUL,
                               weight=ft.FontWeight.W_600)
    status_detalhe  = ft.Text("", size=12, color=SEC)
    status_pct      = ft.Text("", size=28, color=AZUL,
                               weight=ft.FontWeight.W_700)
    status_fase_ico = ft.Icon("hourglass_top_rounded",
                               size=22, color=AZUL)
    status_pb       = ft.ProgressBar(value=0.0, bgcolor=BD, color=AZUL,
                                      height=6, border_radius=3)
    status_eta      = ft.Text("", size=10, color=MUT, italic=True)

    # Mapa de fases → ícone + label amigável
    _FASES = {
        "contando":   ("find_in_page_outlined_rounded",    "Mapeando páginas",      AZUL),
        "lendo":      ("menu_book_outlined_rounded",        "Lendo conteúdo",        AZUL),
        "analisando": ("psychology_outlined_rounded",       "Analisando parâmetros", "#BC8CFF"),
        "extraindo":  ("science_outlined_rounded",          "Extraindo resultados",  "#BC8CFF"),
        "validando":  ("verified_outlined_rounded",         "Validando dados",       VERD),
        "salvando":   ("save_outlined_rounded",             "Salvando rascunho",     VERD),
        "concluido":  ("check_circle_outline_rounded",      "Concluído!",            VERD),
    }

    def _set_status(msg, cor=AZUL, prog=None, detalhe="", fase_key=""):
        # Percentual
        if prog is not None:
            pct = int(prog * 100)
            status_pct.value = f"{pct}%"
            status_pct.color = cor
            status_pb.value  = prog
        else:
            status_pct.value = "—"
            status_pct.color = MUT
            status_pb.value  = None   # indeterminado

        # Fase
        if fase_key and fase_key in _FASES:
            ico, lbl, c = _FASES[fase_key]
            status_fase_ico.name  = ico
            status_fase_ico.color = c
            status_txt.value      = lbl
            status_txt.color      = c
        else:
            status_txt.value = msg
            status_txt.color = cor

        status_detalhe.value = detalhe
        status_eta.value     = ""
        try:
            page.update()
        except Exception:
            pass

    # ── Helper visual — chip de etapa ────────────────────────
    def _etapa_chip(label, icon):
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, size=11, color=MUT),
                ft.Text(label, size=10, color=MUT),
            ], spacing=4, tight=True),
            bgcolor=BG, border_radius=20,
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border=ft.Border(
                top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                left=ft.BorderSide(1, BD), right=ft.BorderSide(1, BD),
            ),
        )

    # ══════════════════════════════════════════════════════════
    # FASE 1 — SELEÇÃO
    # ══════════════════════════════════════════════════════════
    def _tela_selecao():
        itens = [
            ft.Text("Selecione um PDF de exame para processar.",
                    size=13, color=SEC),
            ft.Container(height=8),
            ft.FilledButton(
                content=ft.Row([
                    ft.Icon("folder_open_rounded", size=16),
                    ft.Text("Procurar arquivo", size=13, weight=ft.FontWeight.W_600),
                ], spacing=6, tight=True),
                style=ft.ButtonStyle(
                    bgcolor=MUT, shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.Padding(left=16, right=16, top=10, bottom=10),
                ),
                on_click=_abrir_tkinter,
            ),
            ft.Row([f_path], spacing=8),
            card_arq,
            ft.Row([_cache_badge, _btn_limpar_cache], spacing=8,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            preview_pdf,
            ft.Container(height=12),
        ]

        # Card de duplicata — aparece inline quando PDF já foi importado
        if _dup_info[0] is not None:
            dup  = _dup_info[0]
            qtd  = dup.get("qtd_parametros", 0)
            data = (dup.get("importado_em") or "?")[:16]
            tipo = dup.get("tipo_exame") or "sem tipo"
            eid  = dup.get("exame_id")
            nome = os.path.basename(caminho_sel[0])

            def _reprocessar(e):
                if dados_extra[0] is None:
                    dados_extra[0] = {}
                dados_extra[0]["_reprocessar_id"] = eid
                _dup_info[0] = None
                fase[0] = "processando"
                _rebuild()
                import threading
                threading.Thread(target=_processar_reprocessando,
                                 args=(caminho_sel[0], eid), daemon=True).start()

            def _cancelar_dup(e):
                nome_arq = os.path.basename(caminho_sel[0])
                try:
                    registrar_ignorado(nome_arq, motivo="duplicata — cancelado pelo usuário")
                except Exception:
                    pass
                _dup_info[0] = None
                _voltar_selecao()

            itens.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("warning_amber_rounded", color=AMAR, size=18),
                        ft.Text("PDF já importado", size=13,
                                weight=ft.FontWeight.W_700, color=TXT),
                    ], spacing=8),
                    ft.Container(height=4),
                    ft.Text(f"Arquivo: {nome}", size=11, color=SEC),
                    ft.Text(f"Importado em: {data}  ·  Tipo: {tipo}  ·  {qtd} parâmetro(s)",
                            size=11, color=MUT),
                    ft.Container(height=8),
                    ft.Text("Deseja reprocessar e substituir os dados gravados?",
                            size=12, color=SEC, italic=True),
                    ft.Container(height=8),
                    ft.Row([
                        ft.Container(
                            content=ft.Text("Cancelar", size=13, color=SEC),
                            padding=ft.padding.symmetric(horizontal=12, vertical=8),
                            border_radius=8, ink=True,
                            on_click=_cancelar_dup,
                        ),
                        ft.FilledButton(
                            content=ft.Row([
                                ft.Icon("refresh_outlined_rounded", size=14),
                                ft.Text("Reprocessar", size=12,
                                        weight=ft.FontWeight.W_600),
                            ], spacing=4, tight=True),
                            style=ft.ButtonStyle(
                                bgcolor=AMAR,
                                shape=ft.RoundedRectangleBorder(radius=7),
                                padding=ft.padding.symmetric(horizontal=14, vertical=8),
                            ),
                            on_click=_reprocessar,
                        ),
                    ], spacing=8),
                ], spacing=2),
                bgcolor=f"{AMAR}18",
                border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                border=ft.Border(
                    left=ft.BorderSide(3, AMAR),
                    top=ft.BorderSide(1, BD),
                    bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
            ))
        else:
            itens.append(ft.Row([
                ft.FilledButton(
                    content=ft.Row([
                        ft.Icon("science_outlined_rounded", size=18),
                        ft.Text("Analisar PDF", size=14, weight=ft.FontWeight.W_600),
                    ], spacing=8, tight=True),
                    style=ft.ButtonStyle(
                        bgcolor=AZUL, shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.Padding(left=32, right=32, top=14, bottom=14),
                    ),
                    on_click=_iniciar,
                ),
            ], alignment=ft.MainAxisAlignment.CENTER))

        return itens

    # ══════════════════════════════════════════════════════════
    # FASE 2 — PROCESSANDO (extração local)
    # ══════════════════════════════════════════════════════════
    def _tela_processando():
        nome_arq = os.path.basename(caminho_sel[0]) if caminho_sel[0] else "—"
        # estado inicial
        status_txt.value      = "Mapeando páginas"
        status_txt.color      = AZUL
        status_detalhe.value  = "iniciando leitura..."
        status_pct.value      = "0%"
        status_pct.color      = AZUL
        status_pb.value       = 0.0
        status_eta.value      = ""
        return [
            ft.Container(height=20),
            ft.Container(
                content=ft.Column([
                    # ── Cabeçalho ──────────────────────────────
                    ft.Row([
                        ft.Icon("picture_as_pdf_rounded", size=16, color=VERM),
                        ft.Text(nome_arq, size=12, color=SEC, expand=True,
                                no_wrap=True,
                                overflow=ft.TextOverflow.ELLIPSIS),
                    ], spacing=8),
                    ft.Divider(color=BD, height=1),
                    ft.Container(height=4),

                    # ── Percentual em destaque + spinner ───────
                    ft.Row([
                        ft.ProgressRing(
                            width=44, height=44, stroke_width=4, color=AZUL),
                        ft.Container(width=12),
                        ft.Column([
                            ft.Row([
                                status_fase_ico,
                                ft.Container(width=4),
                                status_txt,
                            ], spacing=0,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            status_detalhe,
                        ], spacing=4, expand=True),
                        ft.Container(
                            content=status_pct,
                            width=72,
                            alignment=ft.alignment.Alignment(1, 0),
                        ),
                    ], spacing=0,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),

                    ft.Container(height=12),

                    # ── Barra de progresso com label ───────────
                    status_pb,
                    ft.Container(height=4),
                    ft.Row([
                        status_eta,
                        ft.Container(expand=True),
                        ft.Text("Não feche esta janela", size=10,
                                color=MUT, italic=True),
                    ]),

                    ft.Container(height=8),

                    # ── Etapas visuais ─────────────────────────
                    ft.Row([
                        _etapa_chip("1 · Mapear",   "find_in_page_outlined_rounded"),
                        ft.Container(width=4),
                        _etapa_chip("2 · Ler",      "menu_book_outlined_rounded"),
                        ft.Container(width=4),
                        _etapa_chip("3 · Analisar", "psychology_outlined_rounded"),
                        ft.Container(width=4),
                        _etapa_chip("4 · Salvar",   "save_outlined_rounded"),
                    ], spacing=0, wrap=True),

                ], spacing=6),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.all(16),
                border=ft.Border(
                    left=ft.BorderSide(3, AZUL),
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
            ),
            ft.Container(height=20),
        ]

    # ══════════════════════════════════════════════════════════
    # FASE 3 — CONFERÊNCIA
    # ══════════════════════════════════════════════════════════
    def _tela_conferencia():
        from extratores.processador_exame import construir_painel_conferencia
        dados = dados_extra[0] or {}

        def _on_liberar():
            threading.Thread(target=_liberar, daemon=True).start()

        return construir_painel_conferencia(
            page            = page,
            dados           = dados,
            pendencias_init = pendencias[0],
            exame_id        = None,   # sem rascunho no banco — gravação só ao confirmar
            on_liberar      = _on_liberar,
            on_cancelar     = _cancelar_rascunho,
            label_confirmar = "Confirmar e Enviar",
        )
    def _tela_liberando():
        status_txt.value     = "Preparando envio..."
        status_txt.color     = VERD
        status_detalhe.value = ""
        status_pb.value      = None
        return [
            ft.Container(height=32),
            ft.Row([
                ft.ProgressRing(width=28, height=28, stroke_width=3, color=VERD),
                ft.Column([status_txt, status_detalhe], spacing=2, tight=True),
            ], spacing=16, alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=12),
            status_pb,
            ft.Container(height=32),
        ]

    # ══════════════════════════════════════════════════════════
    # LÓGICA
    # ══════════════════════════════════════════════════════════

    def _iniciar(e):
        caminho = caminho_sel[0].strip()
        if not caminho:
            _snack("Selecione um arquivo PDF.", VERM); return
        if not os.path.exists(caminho):
            _snack("Arquivo não encontrado.", VERM); return
        fase[0] = "processando"
        _rebuild()
        threading.Thread(target=_processar, args=(caminho,), daemon=True).start()

    def _mostrar_dialogo_duplicata(dup: dict):
        """Diálogo rico quando PDF já foi importado — sempre pergunta ao usuário."""
        qtd   = dup.get("qtd_parametros", 0)
        data  = dup.get("importado_em", "")[:16] if dup.get("importado_em") else "?"
        tipo  = dup.get("tipo_exame", "") or "sem tipo"
        eid   = dup.get("exame_id")
        nome  = os.path.basename(caminho_sel[0])

        def _reprocessar(e):
            dlg.open = False; page.update()
            # Marca nos dados que é reprocessamento — _liberar vai usar substituir_exame
            if dados_extra[0] is None:
                dados_extra[0] = {}
            dados_extra[0]["_reprocessar_id"] = eid
            # Inicia processamento normalmente
            fase[0] = "processando"
            _rebuild()
            import threading
            threading.Thread(target=_processar_reprocessando,
                             args=(caminho_sel[0], eid), daemon=True).start()

        ref_dup = [None]

        def _fechar_dup(e=None):
            if ref_dup[0] and ref_dup[0] in page.overlay:
                page.overlay.remove(ref_dup[0])
            try: page.update()
            except Exception: pass

        def _cancelar_dup(e=None):
            _fechar_dup()
            nome_arq = os.path.basename(caminho_sel[0])
            try:
                registrar_ignorado(nome_arq,
                                   motivo="duplicata — cancelado pelo usuario")
            except Exception:
                pass
            _voltar_selecao()

        def _reprocessar_dup(e):
            _fechar_dup()
            _reprocessar(e)

        btn_cancel_dup = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=8, bgcolor=f"{SEC}22", ink=True,
        )
        btn_cancel_dup.on_click = _cancelar_dup

        btn_reprocessar = ft.Container(
            content=ft.Row([
                ft.Icon("refresh_rounded", size=14, color=AMAR),
                ft.Text("Reprocessar", size=12, color=AMAR,
                        weight=ft.FontWeight.W_600),
            ], spacing=4, tight=True),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=8, bgcolor=f"{AMAR}22", ink=True,
        )
        btn_reprocessar.on_click = _reprocessar_dup

        ref_dup[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("warning_amber_rounded", color=AMAR, size=20),
                        ft.Text("PDF ja importado", size=15,
                                weight=ft.FontWeight.W_700, color=TXT),
                    ], spacing=8),
                    ft.Container(height=8),
                    ft.Text(f"Arquivo: {nome}", size=12, color=SEC),
                    ft.Container(
                        content=ft.Column([
                            ft.Row([ft.Icon("calendar_today_rounded", size=13,
                                           color=MUT),
                                   ft.Text(f"Importado em: {data}", size=12,
                                           color=TXT)], spacing=6),
                            ft.Row([ft.Icon("science_rounded", size=13, color=MUT),
                                   ft.Text(f"Tipo: {tipo}", size=12,
                                           color=TXT)], spacing=6),
                            ft.Row([ft.Icon("numbers_rounded", size=13, color=MUT),
                                   ft.Text(f"Parametros: {qtd}", size=12,
                                           color=TXT)], spacing=6),
                        ], spacing=6),
                        bgcolor=f"{AZUL}15", border_radius=8,
                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    ),
                    ft.Text("Deseja reprocessar e substituir os dados?",
                            size=12, color=SEC),
                    ft.Container(height=8),
                    ft.Row([btn_cancel_dup, btn_reprocessar], spacing=8,
                           alignment=ft.MainAxisAlignment.END),
                ], spacing=6, tight=True),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(16), width=320,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref_dup[0].on_click = _fechar_dup
        page.overlay.append(ref_dup[0])
        try: page.update()
        except Exception: pass

    def _processar_reprocessando(caminho, exame_id_antigo):
        """Igual a _processar mas pula a verificação de duplicata."""
        import traceback, datetime
        _log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "..", "logs", "erro_processar.log")
        os.makedirs(os.path.dirname(_log_path), exist_ok=True)

        def _log_erro(msg):
            try:
                os.makedirs(os.path.dirname(_log_path), exist_ok=True)
                with open(_log_path, "w", encoding="utf-8") as _f:
                    _f.write(f"{datetime.datetime.now()} {msg}\n")
                    _f.write(traceback.format_exc())
            except Exception as _le:
                print(f"[LOG_ERRO] falha ao gravar log: {_le} | msg={msg}")
                logging.error(f"[LOG_ERRO] falha ao gravar log: {_le} | msg={msg}")

        try:
            from extratores.extrator_pdf import extrair_pdf_bytes
            from dados.model_prontuario        import buscar_vinculos_parametros, validar_paciente_pdf
        except Exception as ex_imp:
            _log_erro(f"IMPORT ERROR: {ex_imp}")
            fase[0] = "selecao"; _rebuild(); return

        nome = os.path.basename(caminho)
        try:
            _set_status("Lendo e extraindo dados do PDF...", AZUL, detalhe="iniciando...")
            conteudo = Path(caminho).read_bytes()

            def _on_prog(info):
                fase_e = info.get("fase", "")
                pag = info.get("pagina", 0); tot = info.get("total_pags", 0)
                lins = info.get("linhas", 0); itens = info.get("itens", 0)
                total_lins = info.get("total_linhas", 0)
                if fase_e == "contando":
                    prog = pag / tot * 0.25 if (tot and pag) else (0.05 if tot else None)
                    det  = f"página {pag} de {tot}" if pag else "detectando estrutura..."
                    _set_status("", AZUL, prog, det, "contando")
                elif fase_e == "lendo":
                    prog = 0.25 + min(lins / total_lins * 0.45, 0.45) if total_lins > 0 else 0.30
                    _set_status("", AZUL, prog, f"linha {lins} de {total_lins}", "lendo")
                elif fase_e == "analisando":
                    _set_status("", "#BC8CFF", 0.75, f"{lins} linha(s)...", "analisando")
                elif fase_e == "extraindo":
                    _set_status("", "#BC8CFF", 0.85, f"{itens} parâmetro(s)...", "extraindo")
                elif fase_e == "concluido":
                    _set_status("", VERD, 0.95, f"{itens} parâmetro(s) — finalizando...", "concluido")

            dados = extrair_pdf_bytes(conteudo, nome, None, on_progress=_on_prog, caminho_pdf=caminho)
            dados["arquivo_origem"]   = nome
            dados["arquivo_path"]     = caminho
            dados["_reprocessar_id"]  = exame_id_antigo   # sinaliza substituição no _liberar
            dados_extra[0] = dados

            _set_status("", AZUL, 0.96, "verificando paciente...", "validando")
            v = validar_paciente_pdf(dados.get("paciente_nome"))
            if not v["valido"]:
                try: _snack(f"⚠ {v['motivo']}", VERM)
                except Exception: pass
                fase[0] = "selecao"; _rebuild(); return

            _set_status("", AZUL, 0.97, "verificando vínculos...", "validando")
            params   = [r.get("parametro") for r in dados.get("resultados", []) if r.get("parametro")]
            vinculos = buscar_vinculos_parametros(params)
            vinc_ok  = {v["parametro"] for v in vinculos.get("vinculados", [])}
            pendencias[0] = [{"parametro": p} for p in params if p not in vinc_ok]

            fase[0] = "conferencia"
            try: _rebuild()
            except Exception: pass

        except Exception as ex:
            _log_erro(f"REPROCESSAR ERROR: {ex}")
            logging.exception(f"[REPROCESSAR] {ex}")
            fase[0] = "selecao"
            try: _rebuild()
            except Exception: pass
            try: _snack(f"Erro: {str(ex)[:80]}", VERM)
            except Exception: pass


    # ══════════════════════════════════════════════════════════
    # FASE — MODELO NÃO CONFIGURADO
    # ══════════════════════════════════════════════════════════
    def _tela_modelo_nao_configurado():
        info     = _modelo_info[0]
        lab      = info.get("laboratorio", "Desconhecido")
        tipo_det = info.get("tipo", "desconhecido")
        nome_arq = os.path.basename(caminho_sel[0]) if caminho_sel[0] else "—"

        def _importar_laudo(e):
            """Força importação como laudo genérico."""
            if dados_extra[0]:
                dados_extra[0]["tipo"] = "laudo"
                if not dados_extra[0].get("laudo"):
                    dados_extra[0]["laudo"] = {
                        "texto_completo": dados_extra[0].get("resultado_texto", ""),
                        "resumo":         f"Exame importado de modelo não catalogado. Laboratório: {lab}.",
                        "conclusao":      "",
                    }
                dados_extra[0]["tipo_exame"] = dados_extra[0].get("tipo_exame") or f"Exame ({lab})"
                dados_extra[0]["resultados"] = dados_extra[0].get("resultados") or []
            fase[0] = "conferencia"
            _rebuild()

        def _cancelar_modelo(e):
            _voltar_selecao()

        return [
            ft.Container(height=16),
            ft.Container(
                content=ft.Column([
                    # ── Ícone + título ──────────────────────────
                    ft.Row([
                        ft.Container(
                            content=ft.Icon("extension_off_outlined_rounded",
                                            size=28, color=AMAR),
                            bgcolor=f"{AMAR}18", border_radius=8,
                            padding=ft.padding.all(10),
                        ),
                        ft.Container(width=12),
                        ft.Column([
                            ft.Text("Modelo não configurado",
                                    size=15, weight=ft.FontWeight.W_700, color=TXT),
                            ft.Text("Este formato de exame ainda não tem extrator definido.",
                                    size=12, color=SEC),
                        ], spacing=2, tight=True, expand=True),
                    ], spacing=0,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),

                    ft.Container(height=10),
                    ft.Divider(color=BD, height=1),
                    ft.Container(height=8),

                    # ── Detalhes detectados ──────────────────────
                    ft.Text("O que foi detectado:", size=12,
                            color=SEC, weight=ft.FontWeight.W_600),
                    ft.Container(height=4),
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon("insert_drive_file_outlined_rounded",
                                        size=13, color=MUT),
                                ft.Text(f"Arquivo: {nome_arq}", size=12, color=TXT),
                            ], spacing=6),
                            ft.Row([
                                ft.Icon("business_outlined_rounded",
                                        size=13, color=MUT),
                                ft.Text(f"Laboratório/Equipamento: {lab}", size=12, color=TXT),
                            ], spacing=6),
                            ft.Row([
                                ft.Icon("category_outlined_rounded",
                                        size=13, color=MUT),
                                ft.Text(f"Tipo detectado: {tipo_det}", size=12, color=TXT),
                            ], spacing=6),
                        ], spacing=6),
                        bgcolor=f"{AZUL}10", border_radius=8,
                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    ),

                    ft.Container(height=10),
                    ft.Divider(color=BD, height=1),
                    ft.Container(height=8),

                    # ── Informativo ──────────────────────────────
                    ft.Container(
                        content=ft.Row([
                            ft.Icon("info_outline_rounded", size=13, color=SEC),
                            ft.Container(width=6),
                            ft.Text(
                                "Você pode importar como laudo genérico (sem extração de valores) "
                                "ou cancelar para registrar este modelo para configuração futura.",
                                size=11, color=SEC, expand=True,
                            ),
                        ], spacing=0,
                           vertical_alignment=ft.CrossAxisAlignment.START),
                        bgcolor=f"{BD}80", border_radius=6,
                        padding=ft.padding.symmetric(horizontal=10, vertical=8),
                    ),

                    ft.Container(height=14),

                    # ── Botões ───────────────────────────────────
                    ft.Row([
                        ft.Container(
                            content=ft.Row([
                                ft.Icon("close_rounded", size=14, color=SEC),
                                ft.Text("Cancelar", size=12, color=SEC),
                            ], spacing=4, tight=True),
                            padding=ft.padding.symmetric(horizontal=8, vertical=8),
                            ink=True,
                            on_click=_cancelar_modelo,
                        ),
                        ft.Container(expand=True),
                        ft.FilledButton(
                            content=ft.Row([
                                ft.Icon("upload_file_outlined_rounded", size=15),
                                ft.Text("Importar como laudo",
                                        size=13, weight=ft.FontWeight.W_600),
                            ], spacing=6, tight=True),
                            style=ft.ButtonStyle(
                                bgcolor=AMAR,
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.Padding(left=20, right=20, top=12, bottom=12),
                            ),
                            on_click=_importar_laudo,
                        ),
                    ], spacing=8),
                ], spacing=0),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.all(18),
                border=ft.Border(
                    left=ft.BorderSide(3, AMAR),
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
            ),
        ]

    def _processar(caminho):
        """Extração local — sem Drive."""
        import traceback, datetime
        _log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs", "erro_processar.log")
        os.makedirs(os.path.dirname(_log_path), exist_ok=True)

        def _log_erro(msg):
            try:
                os.makedirs(os.path.dirname(_log_path), exist_ok=True)
                with open(_log_path, "w", encoding="utf-8") as _f:
                    _f.write(f"{datetime.datetime.now()} {msg}\n")
                    _f.write(traceback.format_exc())
            except Exception as _le:
                print(f"[LOG_ERRO] falha ao gravar log: {_le} | msg={msg}")
                logging.error(f"[LOG_ERRO] falha ao gravar log: {_le} | msg={msg}")

        try:
            from extratores.extrator_pdf import extrair_pdf_bytes
            from dados.model_prontuario        import verificar_duplicata, buscar_vinculos_parametros, salvar_exame, validar_paciente_pdf, registrar_ignorado, substituir_exame
        except Exception as ex_imp:
            _log_erro(f"IMPORT ERROR: {ex_imp}")
            fase[0] = "selecao"
            try: _rebuild()
            except Exception: pass
            return

        nome = os.path.basename(caminho)
        try:
            _set_status("Verificando duplicata...", AZUL, 0.15)
            dup = verificar_duplicata(nome_arquivo=nome)
            if dup.get("duplicado"):
                # Para a thread e aciona o diálogo de reprocessar na thread principal
                _dup_info[0] = dup
                fase[0] = "selecao"
                try: _rebuild()          # _rebuild detecta _dup_info e abre o diálogo
                except Exception: pass
                return

            _set_status("Lendo e extraindo dados do PDF...", AZUL, detalhe="iniciando...")
            conteudo = Path(caminho).read_bytes()

            logging.info(f"[INCLUIR] _on_prog registrado, iniciando extracao")
            print(f"[INCLUIR] _on_prog registrado, iniciando extracao")

            def _on_prog(info):
                fase_e     = info.get("fase", "")
                pag        = info.get("pagina", 0)
                tot        = info.get("total_pags", 0)
                lins       = info.get("linhas", 0)
                itens      = info.get("itens", 0)
                total_lins = info.get("total_linhas", 0)

                if fase_e == "contando":
                    if tot and pag:
                        prog = pag / tot * 0.25
                        det  = f"página {pag} de {tot} · {lins} linha(s) encontrada(s)"
                    elif tot:
                        prog = 0.05
                        det  = f"{tot} página(s) detectada(s) — iniciando leitura..."
                    else:
                        prog = None
                        det  = "detectando estrutura do PDF..."
                    _set_status("", AZUL, prog, det, "contando")

                elif fase_e == "lendo":
                    if total_lins > 0:
                        prog = 0.25 + min(lins / total_lins * 0.45, 0.45)
                        det  = f"linha {lins} de {total_lins} · página {pag}/{tot}"
                    else:
                        prog = 0.30
                        det  = f"página {pag} de {tot}"
                    _set_status("", AZUL, prog, det, "lendo")

                elif fase_e == "analisando":
                    det = f"{lins} linha(s) · identificando parâmetros e valores..."
                    _set_status("", "#BC8CFF", 0.75, det, "analisando")

                elif fase_e == "extraindo":
                    det = f"{itens} parâmetro(s) extraído(s) até agora..."
                    _set_status("", "#BC8CFF", 0.85, det, "extraindo")

                elif fase_e == "concluido":
                    det = f"{itens} parâmetro(s) encontrado(s) — finalizando..."
                    _set_status("", VERD, 0.95, det, "concluido")

            # ── Cache de extração ─────────────────────────────
            print(f"[DIAG] iniciando extracao do PDF: {nome}")
            logging.info(f"[DIAG] iniciando extracao: {nome}")
            cache_hit = _cache_ler(conteudo)
            if cache_hit:
                _set_status("Cache encontrado!", VERD, 0.90,
                            f"extraído em {_cache_info(conteudo) or '?'} — pulando reprocessamento", True)
                time.sleep(0.6)
                dados = cache_hit
                logging.info(f"[INCLUIR] cache hit — pulando extrair_pdf_bytes")
            else:
                logging.info(f"[INCLUIR] chamando extrair_pdf_bytes com on_progress")
                dados = extrair_pdf_bytes(conteudo, nome, None, on_progress=_on_prog, caminho_pdf=caminho)
                logging.info(f"[INCLUIR] extrair_pdf_bytes concluido")
                _cache_salvar(conteudo, dados)

            dados["arquivo_origem"] = nome
            dados["arquivo_path"]   = caminho
            dados_extra[0] = dados
            print(f"[DIAG] extracao OK — lab={dados.get('laboratorio')} tipo={dados.get('tipo')} modelo_nc={dados.get('modelo_nao_configurado')} paciente={dados.get('paciente_nome')}")
            logging.info(f"[DIAG] extracao OK — lab={dados.get('laboratorio')} tipo={dados.get('tipo')} modelo_nc={dados.get('modelo_nao_configurado')} paciente={dados.get('paciente_nome')}")

            # ── Validar paciente ──────────────────────────────
            # ── Modelo não configurado? ───────────────────────────────
            if dados.get("modelo_nao_configurado"):
                _modelo_info[0] = {
                    "laboratorio": dados.get("laboratorio", "Desconhecido"),
                    "tipo":        dados.get("tipo", "desconhecido"),
                }
                dados_extra[0] = dados
                fase[0] = "modelo_nao_configurado"
                try:
                    _rebuild()
                except Exception as _rb_ex:
                    _log_erro(f"REBUILD MODELO_NAO_CONFIGURADO ERROR: {_rb_ex}")
                    fase[0] = "selecao"
                    try: _rebuild()
                    except Exception: pass
                    import time as _t; _t.sleep(0.15)
                    try: _snack(f"Modelo não reconhecido: {dados.get('laboratorio','?')}", AMAR)
                    except Exception: pass
                return

            _set_status("", AZUL, 0.96, "verificando paciente no banco...", "validando")
            v = validar_paciente_pdf(dados.get("paciente_nome"))
            if not v["valido"]:
                _log_erro(f"PACIENTE INVALIDO: {v['motivo']}")
                fase[0] = "selecao"
                try: _rebuild()
                except Exception: pass
                import time as _time
                _time.sleep(0.15)
                try: _snack(f"⚠ Exame rejeitado: {v['motivo']}", VERM)
                except Exception: pass
                return

            _set_status("", AZUL, 0.97, "verificando vínculos de parâmetros...", "validando")
            params   = [r.get("parametro") for r in dados.get("resultados", []) if r.get("parametro")]
            vinculos = buscar_vinculos_parametros(params)
            vinc_ok  = {v["parametro"] for v in vinculos.get("vinculados", [])}
            pendencias[0] = [{"parametro": p} for p in params if p not in vinc_ok]

            # Nada é gravado no banco aqui — tudo fica em memória até confirmar
            fase[0] = "conferencia"
            try:
                _rebuild()
            except Exception as _rb_ex:
                logging.exception(f"[INCLUIR] ERRO no _rebuild conferencia: {_rb_ex}")
                _log_erro(f"REBUILD CONFERENCIA ERROR: {_rb_ex}")
                # Fallback: mostrar mensagem de erro na tela
                try:
                    fase[0] = "selecao"
                    _rebuild()
                    _snack(f"Erro ao montar conferência: {str(_rb_ex)[:80]}", VERM)
                except Exception:
                    pass

        except Exception as ex:
            _log_erro(f"PROCESSAR ERROR: {ex}")
            logging.exception(f"[PROCESSAR] {ex}")
            print(f"[PROCESSAR] ERRO: {ex}")
            fase[0] = "selecao"
            try: _rebuild()
            except Exception: pass
            import time as _tex; _tex.sleep(0.15)
            try: _snack(f"Erro ao processar: {str(ex)[:80]}", VERM)
            except Exception: pass

    def _cancelar_rascunho(e=None):
        # Nada para apagar no banco (dados só estavam em memória)
        # Registra no log de importações que o arquivo foi ignorado
        nome = os.path.basename(caminho_sel[0]) if caminho_sel[0] else ""
        if nome:
            try:
                registrar_ignorado(nome, motivo="cancelado na conferência pelo usuário")
            except Exception:
                pass
        _voltar_selecao()

    def _verificar_drive():
        """Testa credenciais do Drive. Retorna (ok, drive_ou_erro)."""
        try:
            from shared.drive_connector import autenticar_drive
            drive = autenticar_drive()
            return True, drive
        except Exception as ex:
            return False, str(ex)

    def _salvar_sem_drive(dados, exame_id_antigo=None):
        """Grava exame no banco sem upload pro Drive."""
        from dados.model_prontuario import salvar_exame, substituir_exame
        dados["drive_file_id"] = None
        if exame_id_antigo:
            return substituir_exame(exame_id_antigo, dados)
        return salvar_exame(dados, status="ativo")

    def _liberar():
        """Upload Drive + gravação definitiva. Trata credenciais expiradas."""
        from dados.model_prontuario import salvar_sync_pendente, salvar_exame, substituir_exame
        dados = dados_extra[0]

        def _log_erro(msg):
            from datetime import datetime as _dt
            try:
                log_path = Path(__file__).parent.parent.parent / "logs" / "erro_processar.log"
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"{_dt.now()} {msg}\n")
            except Exception:
                pass

        try:
            fase[0] = "liberando"; _rebuild()

            # ── Testar credenciais Drive ANTES de tudo ─────────
            _set_status("Verificando credenciais do Drive...", AZUL, 0.05)
            logging.info("[LIBERAR] verificando credenciais Drive...")
            drive_ok, drive_ou_erro = _verificar_drive()

            if not drive_ok:
                logging.warning(f"[LIBERAR] Drive indisponível: {drive_ou_erro}")
                # Mostrar opções ao usuário
                fase[0] = "drive_falhou"; _rebuild()
                return

            # ── Upload Drive ──────────────────────────────────
            from shared.drive_connector import garantir_pasta_base, upload_arquivo
            drive = drive_ou_erro  # é o objeto drive autenticado

            _set_status("Verificando pasta no Drive...", VERD, 0.25)
            garantir_pasta_base(drive)

            _set_status("Enviando arquivo...", VERD, 0.50)
            caminho  = dados.get("arquivo_path", "")
            logging.info(f"[LIBERAR] upload: {caminho}")
            drive_id = upload_arquivo(caminho, drive) if os.path.exists(caminho) else None
            if drive_id:
                dados["drive_file_id"] = drive_id
                logging.info(f"[LIBERAR] upload OK: {drive_id}")
            else:
                logging.warning(f"[LIBERAR] arquivo nao encontrado para upload: {caminho}")

            # ── Gravar banco ──────────────────────────────────
            _set_status("Gravando no banco...", VERD, 0.75)
            logging.info("[LIBERAR] gravando no banco...")
            exame_id_antigo = dados.pop("_reprocessar_id", None)
            if exame_id_antigo:
                eid = substituir_exame(exame_id_antigo, dados)
            else:
                eid = salvar_exame(dados, status="ativo")
            logging.info(f"[LIBERAR] banco OK: exame_id={eid}")

            # ── Sync pendente ─────────────────────────────────
            _set_status("Finalizando...", VERD, 0.90)
            try:
                salvar_sync_pendente(eid)
            except Exception as _se:
                logging.warning(f"[LIBERAR] sync_pendente falhou (ignorado): {_se}")

            # ── Apagar cache ──────────────────────────────────
            try:
                _conteudo_tmp = Path(caminho).read_bytes()
                _cache_apagar(_conteudo_tmp)
                logging.info("[LIBERAR] cache apagado")
            except Exception as _ce:
                logging.warning(f"[LIBERAR] nao foi possivel apagar cache: {_ce}")

            # ── Concluído ─────────────────────────────────────
            _set_status("Concluído!", VERD, 1.0)
            logging.info("[LIBERAR] concluido — voltando para selecao")
            time.sleep(1.0)
            _voltar_selecao()
            _snack(f"Exame incluído com sucesso! (id={eid})", VERD)

        except Exception as ex:
            logging.exception(f"[LIBERAR] ERRO: {ex}")
            _log_erro(f"LIBERAR ERROR: {ex}")
            try:
                fase[0] = "conferencia"
                _rebuild()
                _snack(f"Erro ao salvar: {str(ex)[:80]}", VERM)
            except Exception:
                pass

    def _tela_drive_falhou():
        """Tela exibida quando Drive está indisponível — oferece opções."""

        def _reautenticar(e):
            """Apaga credenciais do Drive e volta pra conferência."""
            import os as _os
            raiz = _os.path.dirname(_os.path.dirname(_os.path.dirname(
                _os.path.abspath(__file__))))  # Koios/
            removidos = []
            for nome_cred in ["mycreds.txt", "mycreds.json"]:
                cred_path = _os.path.join(raiz, nome_cred)
                try:
                    if _os.path.exists(cred_path):
                        _os.remove(cred_path)
                        removidos.append(nome_cred)
                        logging.info(f"[DRIVE] {nome_cred} removido")
                except Exception:
                    pass
            # Volta pra conferência — ao clicar Finalizar de novo, OAuth abre no browser
            fase[0] = "conferencia"
            _rebuild()
            if removidos:
                _snack("Credenciais removidas! Clique em Finalizar novamente.", AZUL)
            else:
                _snack("Nenhuma credencial encontrada. Configure o client_secrets.json.", AMAR)

        def _salvar_local(e):
            """Grava no banco sem Drive."""
            try:
                dados = dados_extra[0]
                fase[0] = "liberando"; _rebuild()
                _set_status("Gravando no banco (sem Drive)...", AMAR, 0.50)
                exame_id_antigo = dados.pop("_reprocessar_id", None)
                eid = _salvar_sem_drive(dados, exame_id_antigo)
                logging.info(f"[LIBERAR] salvo SEM Drive: exame_id={eid}")

                # Apagar cache
                try:
                    caminho = dados.get("arquivo_path", "")
                    if caminho and os.path.exists(caminho):
                        _cache_apagar(Path(caminho).read_bytes())
                except Exception:
                    pass

                _set_status("Salvo no banco! (sem Drive)", VERD, 1.0)
                time.sleep(1.0)
                _voltar_selecao()
                _snack(f"Exame salvo localmente (id={eid}). Upload Drive pendente.", AMAR)
            except Exception as ex:
                logging.exception(f"[LIBERAR] erro salvar local: {ex}")
                fase[0] = "conferencia"; _rebuild()
                _snack(f"Erro ao salvar: {str(ex)[:60]}", VERM)

        def _voltar_conf(e):
            fase[0] = "conferencia"; _rebuild()

        return [
            ft.Container(height=24),
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("cloud_off_rounded", size=32, color=AMAR),
                        ft.Text("Google Drive indisponível", size=16,
                                weight=ft.FontWeight.W_700, color=TXT),
                    ], spacing=12),
                    ft.Container(height=4),
                    ft.Text("As credenciais do Drive expiraram ou não foram configuradas.",
                            size=12, color=SEC),
                    ft.Text("Escolha uma opção:", size=12, color=SEC),
                    ft.Container(height=8),
                    ft.Container(
                        content=ft.Text(
                            "Ao limpar credenciais, clique Finalizar novamente. "
                            "O Google abrirá no navegador para autorizar.",
                            size=11, color=MUT),
                        bgcolor=f"{AZUL}0D", border_radius=6,
                        padding=ft.padding.all(8)),
                    ft.Container(height=12),
                    ft.FilledButton(
                        content=ft.Row([
                            ft.Icon("refresh_rounded", size=16),
                            ft.Text("Limpar credenciais e re-autenticar", size=13,
                                    weight=ft.FontWeight.W_600),
                        ], spacing=8, tight=True),
                        style=ft.ButtonStyle(
                            bgcolor=AZUL,
                            shape=ft.RoundedRectangleBorder(radius=8),
                            padding=ft.padding.symmetric(horizontal=20, vertical=12),
                        ),
                        on_click=_reautenticar,
                    ),
                    ft.Container(height=6),
                    ft.FilledButton(
                        content=ft.Row([
                            ft.Icon("save_rounded", size=16, color="#0D1117"),
                            ft.Text("Salvar só no banco (sem Drive)", size=13,
                                    color="#0D1117", weight=ft.FontWeight.W_600),
                        ], spacing=8, tight=True),
                        style=ft.ButtonStyle(
                            bgcolor=VERD,
                            color="#0D1117",
                            shape=ft.RoundedRectangleBorder(radius=8),
                            padding=ft.padding.symmetric(horizontal=20, vertical=12),
                        ),
                        on_click=_salvar_local,
                    ),
                    ft.Container(height=6),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon("arrow_back_rounded", size=14, color=SEC),
                            ft.Text("Voltar para conferência", size=12, color=SEC),
                        ], spacing=4, tight=True),
                        padding=ft.padding.symmetric(horizontal=8, vertical=8),
                        ink=True,
                        on_click=_voltar_conf,
                    ),
                ], spacing=4),
                bgcolor=CARD, border_radius=12,
                padding=ft.padding.all(20),
                border=ft.Border(
                    left=ft.BorderSide(3, AMAR),
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
            ),
        ]

    def _snack(msg, cor):
        page.snack_bar = ft.SnackBar(ft.Text(msg, color=TXT), bgcolor=cor)
        page.snack_bar.open = True
        page.update()

    # ══════════════════════════════════════════════════════════
    # LAYOUT
    # ══════════════════════════════════════════════════════════
    area.controls.extend(_tela_selecao())

    from shared.layout import Layout
    lay = Layout(page)
    cabecalho = lay.criar_cabecalho(
        "Incluir Exame", voltar_fn,
        icone_titulo="upload_file_rounded",
        cor_titulo=AZUL,
    )
    corpo = ft.Column([
        ft.Container(height=lay.spacer_topo, bgcolor=BG),
        cabecalho,
        ft.Container(content=area, padding=ft.padding.all(16), expand=True),
    ], expand=True, spacing=0)

    return ft.Container(bgcolor=BG, expand=True, content=lay.wrap(corpo))
# Alias para compatibilidade com código legado
tela_incluir_exame = criar_tela_incluir_exame