# -*- coding: utf-8 -*-
# SHARED | utils/foto_picker.py -- gerenciado por flet_shared/sync_shared.py
"""
utils/foto_picker.py  -- Padrao definitivo Flet -- Flet 0.28.2

COMPORTAMENTO POR PLATAFORMA:

  Windows  ->  Botao "Buscar foto"
               -> tkinter.filedialog abre explorador de arquivos
               -> Seleciona -> preview atualiza

  Android  ->  Botao "Buscar foto"
               -> Bottom sheet com opcoes:
                    Camera   -> abre camera nativa (via image_picker Flutter)
                    Galeria  -> ft.FilePicker nativo (galeria)
                    Cancelar

CAMERA ANDROID:
  Flet 0.28.2 nao expoe camera nativa pelo FilePicker.
  Solucao: comunicacao via arquivo com o Dart (main.dart).
  Python escreve _camera_request.json -> Dart detecta ->
  abre camera via image_picker -> escreve _camera_result.json ->
  Python le resultado e processa a foto.

DETECCAO DE PLATAFORMA:
  sys.platform == 'android' SEMPRE retorna 'linux' no Flet Android.
  NUNCA usar para detectar plataforma.
  Usar try/except tkinter -- unico metodo confiavel.
"""

import json
import logging
import os
import shutil
import threading
import time

import flet as ft

log = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

#  Paleta
_CARD  = "#161B22"; _BORDA = "#21262D"; _BRD2  = "#30363D"
_TXT   = "#E6EDF3"; _SEC   = "#8B949E"; _DIS   = "#484F58"
_AZUL  = "#58A6FF"; _VERD  = "#3FB950"; _BG    = "#0D1117"
_AMAR  = "#D29922"; _VERM  = "#FF4444"


# ─────────────────────────────────────────────
#  Deteccao de plataforma
# ─────────────────────────────────────────────

def _is_android() -> bool:
    """tkinter so existe no desktop -- forma confiavel de detectar Android."""
    try:
        import tkinter  # noqa
        return False
    except ModuleNotFoundError:
        return True

_ASSETS_ROOT = os.path.join(_ROOT, "assets")
# Dir persistente fora do dir de extracao do Flet (sobrevive ao update do APK).
# No Android: .../files/app/ -> .../files/user_photos/
# No desktop: igual ao assets (nao necessario)
_PERSIST_ROOT = os.path.join(os.path.dirname(_ROOT), "user_photos") if _is_android() \
                else _ASSETS_ROOT


# ─────────────────────────────────────────────
#  Processamento (copia do arquivo)
# ─────────────────────────────────────────────

def processar_foto(path_origem: str, pasta_destino: str) -> str | None:
    """Copia foto para assets/<pasta_destino>/ e retorna caminho relativo.
    No Android tambem salva copia em user_photos/ (persistente apos update)."""
    if not path_origem or not path_origem.strip():
        return None
    try:
        pasta_abs = os.path.join(_ASSETS_ROOT, pasta_destino)
        os.makedirs(pasta_abs, exist_ok=True)
        nome    = os.path.basename(path_origem.strip())
        destino = os.path.join(pasta_abs, nome)
        if os.path.abspath(path_origem) != os.path.abspath(destino):
            shutil.copy2(path_origem.strip(), destino)
        # Backup persistente no Android
        if _is_android() and _PERSIST_ROOT != _ASSETS_ROOT:
            try:
                persist_pasta = os.path.join(_PERSIST_ROOT, pasta_destino)
                os.makedirs(persist_pasta, exist_ok=True)
                shutil.copy2(path_origem.strip(), os.path.join(persist_pasta, nome))
            except Exception as bex:
                log.warning("[FotoPicker] backup persistente falhou: %s", bex)
        path_rel = f"{pasta_destino}/{nome}"
        log.info("[FotoPicker] salva: %s", path_rel)
        return path_rel
    except Exception as ex:
        log.exception("[FotoPicker] processar_foto: %s", ex)
        return None


# ─────────────────────────────────────────────
#  Camera Android via image_picker (Dart)
# ─────────────────────────────────────────────

_CAMERA_REQ = os.path.join(_ROOT, "_camera_request.json")
_CAMERA_RES = os.path.join(_ROOT, "_camera_result.json")


_DEBUG_CAM = "/sdcard/app_cam_debug.txt"


def _dbg_cam(msg: str) -> None:
    """Diagnostico temporario: escreve em /sdcard acessivel pelo adb."""
    try:
        with open(_DEBUG_CAM, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass


def _mostrar_erro_camera(page: ft.Page, motivo: str) -> None:
    """Envia erro da camera via pubsub topic (thread-safe, nao substitui handler global)."""
    try:
        page.pubsub.send_all_on_topic("_camera_erro", motivo)
    except Exception:
        pass


def _capturar_camera_android(page: ft.Page, callback) -> None:
    """
    Solicita captura via camera nativa Android.
    Escreve _camera_request.json -> Dart (main.dart) detecta ->
    abre camera via image_picker -> escreve _camera_result.json.
    """
    try:
        _dbg_cam(f"_capturar chamado. ROOT={_ROOT}")
        _dbg_cam(f"REQ={_CAMERA_REQ}  RES={_CAMERA_RES}")

        # Limpa resultado anterior
        if os.path.exists(_CAMERA_RES):
            os.remove(_CAMERA_RES)

        # Envia solicitacao para o Dart
        with open(_CAMERA_REQ, "w", encoding="utf-8") as f:
            json.dump({"action": "take_photo"}, f)
        _dbg_cam("camera_request.json escrito OK")
        log.info("[FotoPicker] camera request enviado")

        # Aguarda resultado em thread separada (nao bloqueia UI)
        def _poll():
            for i in range(180):  # 180 * 0.5s = 90s timeout
                time.sleep(0.5)
                if i % 10 == 0:
                    _dbg_cam(f"poll tick {i} -- aguardando result...")
                if os.path.exists(_CAMERA_RES):
                    try:
                        with open(_CAMERA_RES, "r", encoding="utf-8") as f:
                            result = json.load(f)
                        os.remove(_CAMERA_RES)
                        _dbg_cam(f"result lido: {result}")
                        if result.get("ok") and result.get("path"):
                            _dbg_cam(f"foto capturada: {result['path']}")
                            log.info("[FotoPicker] foto capturada: %s", result["path"])
                            callback(result["path"])
                        else:
                            motivo = result.get("reason", "cancelado")
                            _dbg_cam(f"camera nao OK: motivo={motivo}")
                            log.info("[FotoPicker] camara: %s", motivo)
                            if motivo not in ("cancelled", "cancelado"):
                                _mostrar_erro_camera(page, motivo)
                    except Exception as ex:
                        _dbg_cam(f"erro ao ler result: {ex}")
                        log.exception("[FotoPicker] erro ao ler resultado camera: %s", ex)
                    return
            _dbg_cam("TIMEOUT esperando camera_result.json")
            log.warning("[FotoPicker] timeout esperando resultado da camera")
            _mostrar_erro_camera(page, "Timeout: Dart nao respondeu ao camera_request.json")

        threading.Thread(target=_poll, daemon=True).start()
    except Exception as ex:
        _dbg_cam(f"EXCECAO: {ex}")
        log.exception("[FotoPicker] camera request falhou: %s", ex)
        _mostrar_erro_camera(page, str(ex))


# ─────────────────────────────────────────────
#  Bottom sheet Android -- camera ou galeria
# ─────────────────────────────────────────────

def _mostrar_menu_android(
    page: ft.Page,
    titulo: str,
    on_galeria,
    on_camera,
) -> None:
    """Exibe bottom sheet com opcoes Camera / Galeria."""
    ref = [None]

    def _fechar(e=None):
        if ref[0] and ref[0] in page.overlay:
            page.overlay.remove(ref[0])
        try:
            page.update()
        except Exception:
            pass

    def _clicou_galeria(e):
        _fechar()
        on_galeria()

    def _clicou_camera(e):
        _fechar()
        on_camera()

    def _item(icone, texto, on_click):
        return ft.Container(
            content=ft.Row(
                [ft.Icon(icone, size=22, color=_AZUL),
                 ft.Text(texto, size=15, color=_TXT)],
                spacing=18,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=24, vertical=16),
            on_click=on_click, ink=True,
        )

    sheet = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Text(titulo, size=13, color=_SEC,
                                    weight=ft.FontWeight.W_600),
                    padding=ft.padding.symmetric(horizontal=24, vertical=14),
                ),
                ft.Container(height=1, bgcolor=_BORDA),
                _item("photo_camera_rounded",  "Camera",  _clicou_camera),
                ft.Container(height=1, bgcolor=_BORDA),
                _item("photo_library_rounded", "Galeria", _clicou_galeria),
                ft.Container(height=1, bgcolor=_BORDA),
                ft.Container(
                    content=ft.Text("Cancelar", size=14, color=_SEC,
                                    text_align="center"),
                    padding=ft.padding.symmetric(horizontal=24, vertical=16),
                    on_click=_fechar, ink=True,
                    alignment=ft.Alignment(0, 0),
                    expand=True,
                ),
            ],
            spacing=0, tight=True,
        ),
        bgcolor=_CARD,
        border_radius=ft.BorderRadius(top_left=16, top_right=16,
                                      bottom_left=0, bottom_right=0),
    )

    ref[0] = ft.Container(
        content=ft.Column(
            [ft.Container(expand=True, on_click=_fechar), sheet],
            spacing=0,
        ),
        bgcolor="#CC000000", expand=True,
    )
    page.overlay.append(ref[0])
    try:
        page.update()
    except Exception:
        pass


# ─────────────────────────────────────────────
#  API publica -- criar_painel_foto
# ─────────────────────────────────────────────

def criar_painel_foto(
    page: ft.Page,
    foto_atual: str = "",
    pasta_destino: str = "fotos_clientes",
    tamanho: int = 80,
    on_foto=None,
    icone_vazio=None,
    titulo_menu: str = "Foto",
) -> tuple:
    """
    Retorna (painel, preview_widget).

    Windows : Buscar -> tkinter filedialog -> copia -> preview
    Android : Buscar -> bottom sheet (Camera / Galeria) -> copia -> preview
    """
    if icone_vazio is None:
        icone_vazio = "person_rounded"
    raio = tamanho // 2

    #  Preview circular
    preview = ft.Container(
        content=ft.Icon(icone_vazio, size=tamanho // 2, color=_DIS),
        width=tamanho, height=tamanho, border_radius=raio,
        bgcolor=f"{_DIS}22", alignment=ft.Alignment(0, 0),
    )
    label = ft.Text("Sem foto", size=10, color=_DIS)

    # Flag: False durante construcao, True apos retorno -- evita page.update()
    # antes da tela estar em page.controls (causa freeze no Android)
    _montado = [False]

    def _atualizar_preview(path_rel: str) -> None:
        preview.content = ft.Container(
            content=ft.Image(
                src=str(path_rel).replace("\\", "/"),
                width=tamanho, height=tamanho, fit="cover",
            ),
            width=tamanho, height=tamanho, border_radius=raio,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )
        label.value = str(path_rel).split("/")[-1]
        if _montado[0]:
            try:
                page.update()
            except Exception:
                pass

    if foto_atual:
        _atualizar_preview(foto_atual)

    _montado[0] = True  # Construcao concluida -- page.update() liberado

    def _processar(path_abs: str) -> None:
        path_rel = processar_foto(path_abs, pasta_destino)
        if path_rel:
            _atualizar_preview(path_rel)
            if on_foto:
                try:
                    on_foto(path_rel)
                except Exception as ex:
                    log.exception("[FotoPicker] on_foto: %s", ex)

    #  FilePicker -- galeria (Android)
    # Lazy: registrado so no primeiro clique, nao na criacao da tela
    # page.overlay.append + page.update() na criacao bloqueiam navegacao no Android
    _fp_galeria = [None]

    def _resultado_galeria(e: ft.FilePickerResultEvent) -> None:
        if e.files and len(e.files) > 0:
            path = e.files[0].path
            if path:
                _processar(path)
            else:
                log.warning("[FotoPicker] path vazio no resultado da galeria")
        else:
            log.info("[FotoPicker] galeria cancelada")

    def _get_fp_galeria():
        if _fp_galeria[0] is None:
            _fp_galeria[0] = ft.FilePicker(on_result=_resultado_galeria)
            page.overlay.append(_fp_galeria[0])
            try:
                page.update()
            except Exception:
                pass
        return _fp_galeria[0]

    #  Botao
    btn_buscar = ft.Container(
        content=ft.Row([
            ft.Icon("add_photo_alternate_rounded", size=16, color=_AZUL),
            ft.Text("Buscar foto", size=13, color=_AZUL,
                    weight=ft.FontWeight.W_600),
        ], spacing=8, tight=True),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border_radius=8, bgcolor=_CARD, ink=True,
        border=ft.Border(
            top=ft.BorderSide(1, _BRD2), bottom=ft.BorderSide(1, _BRD2),
            left=ft.BorderSide(1, _BRD2), right=ft.BorderSide(1, _BRD2),
        ),
    )

    def _abrir(e):
        if not _is_android():
            # Windows -- explorador de arquivos via tkinter
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.wm_attributes("-topmost", True)
                caminho = filedialog.askopenfilename(
                    title="Selecione uma foto",
                    filetypes=[("Imagens", "*.jpg *.jpeg *.png *.webp *.gif"),
                               ("Todos os arquivos", "*.*")],
                )
                root.destroy()
                if caminho:
                    _processar(caminho)
            except Exception as ex:
                log.exception("[FotoPicker] filedialog: %s", ex)
        else:
            # Android -- bottom sheet com camera ou galeria
            _mostrar_menu_android(
                page   = page,
                titulo = titulo_menu,
                on_galeria = lambda: _get_fp_galeria().pick_files(
                    allow_multiple=False,
                    file_type=ft.FilePickerFileType.IMAGE,
                ),
                on_camera = lambda: _capturar_camera_android(page, _processar),
            )

    btn_buscar.on_click = _abrir

    painel = ft.Column([
        ft.Row([
            preview,
            ft.Container(width=12),
            ft.Column([label, ft.Container(height=6), btn_buscar],
                      spacing=0, tight=True),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
    ], spacing=6, tight=True)

    return painel, preview, _atualizar_preview


# ─────────────────────────────────────────────
#  API publica -- criar_btn_seletor_foto
# ─────────────────────────────────────────────

def criar_btn_seletor_foto(
    page: ft.Page,
    on_arquivo=None,
    titulo_menu: str = "Foto",
    label_btn: str = "Buscar",
) -> ft.Column:
    """
    Retorna Column com botao de selecao (sem preview).
    Usado no catalogo para multiplas fotos de produto.

    Windows : tkinter filedialog
    Android : bottom sheet (Camera / Galeria)
    """
    def _resultado_galeria(e: ft.FilePickerResultEvent) -> None:
        if e.files and len(e.files) > 0:
            path = e.files[0].path
            if path and on_arquivo:
                try:
                    on_arquivo(path)
                except Exception as ex:
                    log.exception("[FotoPicker] seletor on_arquivo: %s", ex)
        else:
            log.info("[FotoPicker] seletor galeria cancelada")

    # Lazy: registrado so no primeiro clique
    _fp_galeria = [None]

    def _get_fp_galeria():
        if _fp_galeria[0] is None:
            _fp_galeria[0] = ft.FilePicker(on_result=_resultado_galeria)
            page.overlay.append(_fp_galeria[0])
            try:
                page.update()
            except Exception:
                pass
        return _fp_galeria[0]

    btn = ft.Container(
        content=ft.Row([
            ft.Icon("folder_open_rounded", size=14, color=_SEC),
            ft.Text(label_btn, size=12, color=_SEC),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border_radius=8, bgcolor=_CARD, ink=True,
        border=ft.Border(
            top=ft.BorderSide(1, _BRD2), bottom=ft.BorderSide(1, _BRD2),
            left=ft.BorderSide(1, _BRD2), right=ft.BorderSide(1, _BRD2),
        ),
    )

    def _abrir(e):
        if not _is_android():
            # Windows -- explorador de arquivos via tkinter
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.wm_attributes("-topmost", True)
                caminho = filedialog.askopenfilename(
                    title="Selecione uma foto",
                    filetypes=[("Imagens", "*.jpg *.jpeg *.png *.webp *.gif"),
                               ("Todos os arquivos", "*.*")],
                )
                root.destroy()
                if caminho and on_arquivo:
                    try:
                        on_arquivo(caminho)
                    except Exception as ex:
                        log.exception("[FotoPicker] seletor btn: %s", ex)
            except Exception as ex:
                log.exception("[FotoPicker] filedialog: %s", ex)
        else:
            # Android -- bottom sheet com camera ou galeria
            def _on_camera_result(path_abs):
                if on_arquivo:
                    try:
                        on_arquivo(path_abs)
                    except Exception as ex:
                        log.exception("[FotoPicker] seletor camera: %s", ex)

            _mostrar_menu_android(
                page   = page,
                titulo = titulo_menu,
                on_galeria = lambda: _get_fp_galeria().pick_files(
                    allow_multiple=False,
                    file_type=ft.FilePickerFileType.IMAGE,
                ),
                on_camera = lambda: _capturar_camera_android(page, _on_camera_result),
            )

    btn.on_click = _abrir

    return ft.Column([
        ft.Row([btn], spacing=8),
    ], spacing=6, tight=True)


# ─────────────────────────────────────────────
#  Edicao de foto (girar/espelhar) via Pillow
# ─────────────────────────────────────────────

def foto_abs_path(path_rel: str) -> str:
    """
    Converte path relativo (ex: 'fotos_clientes/foto.jpg') para absoluto.
    Prefere a copia persistente (_PERSIST_ROOT) para upload ao Drive.
    """
    if not path_rel:
        return ""
    persist = os.path.join(_PERSIST_ROOT, path_rel.replace("/", os.sep))
    if os.path.exists(persist):
        return persist
    assets = os.path.join(_ASSETS_ROOT, path_rel.replace("/", os.sep))
    return assets if os.path.exists(assets) else persist


def resolver_foto(
    path_rel: str,
    foto_drive_id: str = "",
    on_baixado=None,
) -> str:
    """
    Resolve o caminho local usavel para exibir a foto.

    1. Verifica em _ASSETS_ROOT e _PERSIST_ROOT.
    2. Se nao encontrar mas houver foto_drive_id:
       - Verifica cache em _PERSIST_ROOT/cache_fotos/
       - Se nao ha cache, baixa em background e chama on_baixado(path) ao concluir.
    3. Retorna o path local disponivel agora (pode ser '' se ainda nao baixado).
    """
    if path_rel:
        for base in [_ASSETS_ROOT, _PERSIST_ROOT]:
            candidato = os.path.join(base, path_rel.replace("/", os.sep))
            if os.path.exists(candidato):
                return candidato if base == _PERSIST_ROOT else path_rel

    if not foto_drive_id:
        return ""

    # Verifica cache local
    nome_cache = os.path.basename(path_rel) if path_rel else f"foto_{foto_drive_id[:8]}.jpg"
    pasta_cache = os.path.join(_PERSIST_ROOT, "cache_fotos")
    dest_cache  = os.path.join(pasta_cache, nome_cache)
    if os.path.exists(dest_cache):
        return dest_cache

    # Baixa em background
    if on_baixado:
        def _dl():
            try:
                from utils.drive_sync import baixar_foto
                ok = baixar_foto(foto_drive_id, dest_cache)
                if ok and on_baixado:
                    on_baixado(dest_cache)
                    log.info("[FotoPicker] cache baixado: %s", dest_cache)
            except Exception as ex:
                log.warning("[FotoPicker] download cache: %s", ex)
        threading.Thread(target=_dl, daemon=True).start()

    return ""


def editar_foto(path_rel: str, operacao: str) -> str:
    """
    Aplica operacao na foto, salva com novo nome (evita cache Flutter)
    e atualiza o backup persistente no Android.

    operacoes: 'rotate_cw', 'rotate_ccw', 'flip_h', 'flip_v'

    Retorna novo path_rel ou "" em caso de erro.
    """
    import re
    import time as _time
    try:
        from PIL import Image as _Image
    except ImportError:
        log.error("[FotoPicker] Pillow nao disponivel -- editar_foto nao suportado")
        return ""
    try:
        path_abs = os.path.join(_ASSETS_ROOT, path_rel)
        if not os.path.exists(path_abs):
            log.error("[FotoPicker] editar_foto: arquivo nao existe: %s", path_abs)
            return ""
        img = _Image.open(path_abs)
        # Converte para RGB: necessario para salvar como JPEG (RGBA nao suportado)
        if img.mode != "RGB":
            img = img.convert("RGB")
        if operacao == "rotate_cw":
            img = img.rotate(-90, expand=True)
        elif operacao == "rotate_ccw":
            img = img.rotate(90, expand=True)
        elif operacao == "flip_h":
            img = img.transpose(0)   # FLIP_LEFT_RIGHT = 0
        elif operacao == "flip_v":
            img = img.transpose(1)   # FLIP_TOP_BOTTOM = 1
        else:
            log.warning("[FotoPicker] editar_foto: operacao desconhecida: %s", operacao)
            return ""
        # Novo nome: remove sufixo _e\d+ anterior e adiciona timestamp
        pasta   = path_rel.rsplit("/", 1)[0] if "/" in path_rel else ""
        nome_b  = os.path.basename(path_rel)
        stem, ext = os.path.splitext(nome_b)
        ext = ext if ext else ".jpg"
        stem_clean  = re.sub(r"_e\d+$", "", stem)
        novo_nome   = f"{stem_clean}_e{int(_time.time())}{ext}"
        nova_rel    = f"{pasta}/{novo_nome}" if pasta else novo_nome
        novo_abs    = os.path.join(_ASSETS_ROOT, nova_rel)
        os.makedirs(os.path.dirname(novo_abs), exist_ok=True)
        img.save(novo_abs)
        # Remove arquivo anterior
        try:
            if os.path.abspath(path_abs) != os.path.abspath(novo_abs):
                os.remove(path_abs)
        except Exception:
            pass
        # Atualiza backup persistente no Android
        if _is_android() and _PERSIST_ROOT != _ASSETS_ROOT:
            try:
                old_bk = os.path.join(_PERSIST_ROOT, path_rel)
                if os.path.exists(old_bk):
                    os.remove(old_bk)
                new_bk = os.path.join(_PERSIST_ROOT, nova_rel)
                os.makedirs(os.path.dirname(new_bk), exist_ok=True)
                shutil.copy2(novo_abs, new_bk)
            except Exception as bex:
                log.warning("[FotoPicker] editar_foto backup: %s", bex)
        log.info("[FotoPicker] editada: %s -> %s", path_rel, nova_rel)
        return nova_rel
    except Exception as ex:
        log.exception("[FotoPicker] editar_foto: %s", ex)
        return ""
