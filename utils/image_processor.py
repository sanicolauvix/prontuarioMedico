# -*- coding: utf-8 -*-
"""
image_processor.py — Koios Prontuario
Processamento de imagem com tres perfis:
  1. processar_foto_produto   — RGB, recorte suave, uso visual (produtos, pessoas)
  2. processar_foto_documento — perspective transform + grayscale + threshold (OCR/IA)
  3. gerar_thumbnail          — miniatura padrao para listas (sempre chamado apos os dois acima)

REGRA DO PROJETO: toda foto salva DEVE ter um thumbnail correspondente.
  - Foto principal:  assets/fotos_remedios/rec_1234567890.jpg
  - Thumbnail:       assets/fotos_remedios/thumbs/rec_1234567890.jpg
  - Convencao:       subpasta "thumbs/" dentro da mesma pasta da foto
  - Tamanho:         200x200px, JPEG 75%, crop centralizado (cover)
"""
import os
import time
import logging

logger = logging.getLogger(__name__)

# Tamanho padrao dos thumbnails em pixels (lado)
THUMB_SIZE = 200


def _importar_cv2():
    try:
        import cv2
        import numpy as np
        return cv2, np
    except ImportError:
        raise RuntimeError(
            "opencv-python-headless nao instalado. Execute: pip install opencv-python-headless numpy"
        )


# ── Utilitarios internos ───────────────────────────────────────────────────────

def _ordenar_cantos(pts):
    import numpy as np
    pts = pts.reshape(4, 2).astype("float32")
    soma = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    tl = pts[soma.argmin()]
    br = pts[soma.argmax()]
    tr = pts[diff.argmin()]
    bl = pts[diff.argmax()]
    return np.array([tl, tr, br, bl], dtype="float32")


def _detectar_documento(img, cv2, np):
    """Detecta contorno retangular do documento. Retorna array (4,2) ou None."""
    h, w = img.shape[:2]
    cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cinza = cv2.GaussianBlur(cinza, (5, 5), 0)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cinza = clahe.apply(cinza)

    bordas = cv2.Canny(cinza, 30, 100)
    bordas = cv2.dilate(bordas, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), iterations=2)

    contornos, _ = cv2.findContours(bordas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contornos = sorted(contornos, key=cv2.contourArea, reverse=True)

    area_min = w * h * 0.10

    for cnt in contornos[:10]:
        if cv2.contourArea(cnt) < area_min:
            continue
        peri   = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4:
            return _ordenar_cantos(approx)

    return None


def _perspective_transform(img, cantos, cv2, np):
    tl, tr, br, bl = cantos
    W = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    H = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    if W < 50 or H < 50:
        return img
    destino = np.array([[0, 0], [W-1, 0], [W-1, H-1], [0, H-1]], dtype="float32")
    M = cv2.getPerspectiveTransform(cantos, destino)
    return cv2.warpPerspective(img, M, (W, H))


def _remover_sombra(img, cv2, np):
    resultado = np.zeros_like(img)
    for i in range(3):
        canal = img[:, :, i]
        fundo = cv2.GaussianBlur(canal, (21, 21), 0)
        resultado[:, :, i] = cv2.divide(canal, fundo, scale=255)
    return resultado


def _thumb_path(path_foto: str) -> str:
    """Retorna o path do thumbnail correspondente a uma foto.
    Convencao: thumbs/ dentro da mesma pasta.
    Ex: assets/fotos_remedios/abc.jpg -> assets/fotos_remedios/thumbs/abc.jpg
    """
    pasta = os.path.dirname(path_foto)
    nome  = os.path.basename(path_foto)
    return os.path.join(pasta, "thumbs", nome)


# ── Perfil 3: Thumbnail (chamado internamente e pela foto_picker) ─────────────

def gerar_thumbnail(path_foto: str, tamanho: int = THUMB_SIZE) -> str:
    """
    Gera miniatura quadrada (cover crop) de qualquer foto ja processada.
    Salva em <mesma_pasta>/thumbs/<mesmo_nome>.jpg
    Retorna path absoluto do thumbnail gerado.
    """
    cv2, np = _importar_cv2()

    img = cv2.imread(path_foto)
    if img is None:
        raise ValueError(f"Nao foi possivel ler a imagem para thumbnail: {path_foto}")

    h, w = img.shape[:2]
    lado = min(h, w)
    y0 = (h - lado) // 2
    x0 = (w - lado) // 2
    img_sq = img[y0:y0+lado, x0:x0+lado]
    img_thumb = cv2.resize(img_sq, (tamanho, tamanho), interpolation=cv2.INTER_AREA)

    dest = _thumb_path(path_foto)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    cv2.imwrite(dest, img_thumb, [cv2.IMWRITE_JPEG_QUALITY, 75])
    logger.info("[IMG] thumbnail: %s", dest)
    return dest


def thumb_path_de(path_foto: str) -> str:
    """Retorna o path esperado do thumbnail sem gerar. Util para verificar existencia."""
    return _thumb_path(path_foto)


def thumb_ou_foto(path_foto: str) -> str:
    """Retorna thumbnail se existir, senao retorna a foto original.
    Uso seguro em listas: nunca quebra mesmo sem thumbnail gerado."""
    tp = _thumb_path(path_foto)
    return tp if os.path.exists(tp) else path_foto


# ── Perfil 1: Produtos / Pessoas ──────────────────────────────────────────────

def processar_foto_produto(path_origem: str, pasta_destino: str) -> str:
    """
    Perfil visual: mantém cores RGB, recorte suave, uso em listas e galeria.
    Gera thumbnail automaticamente apos processar.
    """
    cv2, np = _importar_cv2()

    img = cv2.imread(path_origem)
    if img is None:
        raise ValueError(f"Nao foi possivel ler a imagem: {path_origem}")

    h, w = img.shape[:2]
    margem_h = int(h * 0.05)
    margem_w = int(w * 0.05)
    img_crop = img[margem_h:h-margem_h, margem_w:w-margem_w]

    hc, wc = img_crop.shape[:2]
    escala = min(1600 / max(hc, wc), 1.0)
    if escala < 1.0:
        img_crop = cv2.resize(img_crop, (int(wc*escala), int(hc*escala)), interpolation=cv2.INTER_AREA)

    nome    = f"prod_{int(time.time()*1000)}.jpg"
    destino = os.path.join(pasta_destino, nome)
    os.makedirs(pasta_destino, exist_ok=True)
    cv2.imwrite(destino, img_crop, [cv2.IMWRITE_JPEG_QUALITY, 88])
    logger.info("[IMG] produto: %s", destino)

    try:
        gerar_thumbnail(destino)
    except Exception as ex:
        logger.warning("[IMG] thumbnail de produto falhou: %s", ex)

    return destino


# ── Perfil 2: Documentos para OCR / IA ───────────────────────────────────────

def processar_foto_documento(path_origem: str, pasta_destino: str) -> str:
    """
    Perfil OCR: perspective transform + remocao de sombra + grayscale + threshold adaptativo.
    Gera thumbnail automaticamente apos processar.
    """
    cv2, np = _importar_cv2()

    img = cv2.imread(path_origem)
    if img is None:
        raise ValueError(f"Nao foi possivel ler a imagem: {path_origem}")

    h, w = img.shape[:2]
    escala_proc = min(1200 / max(h, w), 1.0)
    img_proc = cv2.resize(img, (int(w*escala_proc), int(h*escala_proc)), interpolation=cv2.INTER_AREA) \
               if escala_proc < 1.0 else img.copy()

    cantos = _detectar_documento(img_proc, cv2, np)

    if cantos is not None:
        if escala_proc < 1.0:
            cantos = cantos / escala_proc
        img_warp = _perspective_transform(img, cantos, cv2, np)
    else:
        logger.warning("[IMG] documento nao detectado, usando original")
        img_warp = img

    img_sem_sombra = _remover_sombra(img_warp, cv2, np)
    cinza = cv2.cvtColor(img_sem_sombra, cv2.COLOR_BGR2GRAY)
    doc_final = cv2.adaptiveThreshold(
        cinza, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=21,
        C=10
    )
    doc_final = cv2.medianBlur(doc_final, 3)

    nome    = f"doc_{int(time.time()*1000)}.jpg"
    destino = os.path.join(pasta_destino, nome)
    os.makedirs(pasta_destino, exist_ok=True)
    cv2.imwrite(destino, doc_final, [cv2.IMWRITE_JPEG_QUALITY, 92])
    logger.info("[IMG] documento: %s", destino)

    try:
        gerar_thumbnail(destino)
    except Exception as ex:
        logger.warning("[IMG] thumbnail de documento falhou: %s", ex)

    return destino


# ── Confirmação visual (subprocess isolado — evita Tcl_AsyncDelete com Flet) ──

def confirmar_processamento_documento(path_origem: str, pasta_destino: str) -> "str | None":
    """
    Abre janela de confirmação/recorte em processo filho separado.
    Roda _confirmar_doc_gui.py via subprocess — tkinter completamente isolado do Flet.

    Retorna path do arquivo salvo em pasta_destino, ou None se cancelado.
    Deve ser chamada dentro de thread daemon (fora da UI Flet).
    """
    import subprocess, sys

    script = os.path.join(os.path.dirname(__file__), "_confirmar_doc_gui.py")
    try:
        proc = subprocess.run(
            [sys.executable, script, path_origem, pasta_destino],
            capture_output=True,
            text=True,
            timeout=300,  # 5 min máximo para o usuário interagir
        )
        saida = proc.stdout.strip()
        if saida and os.path.exists(saida):
            logger.info("[IMG] confirmado: %s", saida)
            return saida
        if proc.returncode != 0 and proc.stderr:
            logger.warning("[IMG] gui stderr: %s", proc.stderr[:200])
        return None
    except subprocess.TimeoutExpired:
        logger.warning("[IMG] janela de confirmacao expirou (5 min)")
        return None
    except Exception as ex:
        logger.warning("[IMG] subprocess falhou: %s", ex)
        return None
