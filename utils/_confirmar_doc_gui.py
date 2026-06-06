# -*- coding: utf-8 -*-
"""
_confirmar_doc_gui.py — executado como subprocess isolado pelo image_processor.
Recebe via sys.argv:
  argv[1] = path_origem
  argv[2] = pasta_destino
Imprime na stdout o path do arquivo resultado, ou nada se cancelado.
Roda no processo filho — tkinter no processo principal, sem conflito com Flet.
"""
import sys
import os
import time
import shutil
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

def main():
    if len(sys.argv) < 3:
        sys.exit(1)

    path_origem   = sys.argv[1]
    pasta_destino = sys.argv[2]

    # Adicionar raiz do projeto ao path para importar image_processor
    _here = os.path.dirname(os.path.abspath(__file__))
    _root = os.path.dirname(_here)
    sys.path.insert(0, _root)

    import cv2
    import numpy as np
    import tkinter as tk
    from PIL import Image as _PILImage, ImageTk as _ImageTk, ImageDraw as _ImageDraw

    from utils.image_processor import (
        _importar_cv2, _detectar_documento, _ordenar_cantos,
        _perspective_transform, _remover_sombra, gerar_thumbnail,
        processar_foto_documento,
    )

    cv2_, np_ = _importar_cv2()

    # ── Constantes ────────────────────────────────────────────────────────────
    PREV_W = 380; PREV_H = 500
    CANVAS_W = 700; CANVAS_H = 560
    BG = "#0D1117"; CARD = "#161B22"; BD = "#21262D"
    AZUL = "#58A6FF"; VERD = "#3FB950"; TXT = "#E6EDF3"; SEC = "#8B949E"

    resultado_final = [None]

    # ── Detecção automática ───────────────────────────────────────────────────
    img_orig_cv2 = cv2_.imread(path_origem)
    if img_orig_cv2 is None:
        sys.exit(1)

    h_orig, w_orig = img_orig_cv2.shape[:2]
    esc_det = min(1200 / max(h_orig, w_orig), 1.0)
    img_det = cv2_.resize(img_orig_cv2,
                          (int(w_orig * esc_det), int(h_orig * esc_det)),
                          interpolation=cv2_.INTER_AREA) if esc_det < 1.0 else img_orig_cv2.copy()
    cantos_auto = _detectar_documento(img_det, cv2_, np_)
    if cantos_auto is not None and esc_det < 1.0:
        cantos_auto = cantos_auto / esc_det

    tmp_dir   = tempfile.mkdtemp()
    path_proc = None
    if cantos_auto is not None:
        try:
            path_proc = processar_foto_documento(path_origem, tmp_dir)
        except Exception:
            pass

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _fit(img_pil, max_w, max_h):
        w, h = img_pil.size
        e = min(max_w / w, max_h / h, 1.0)
        return img_pil.resize((int(w * e), int(h * e)), _PILImage.LANCZOS), e

    def _salvar_original():
        ext  = path_origem.rsplit(".", 1)[-1].lower() or "jpg"
        dest = os.path.join(pasta_destino, f"orig_{int(time.time()*1000)}.{ext}")
        os.makedirs(pasta_destino, exist_ok=True)
        shutil.copy2(path_origem, dest)
        try: gerar_thumbnail(dest)
        except Exception: pass
        return dest

    def _salvar_processada(img_cv2_final):
        os.makedirs(pasta_destino, exist_ok=True)
        nome = f"doc_{int(time.time()*1000)}.jpg"
        dest = os.path.join(pasta_destino, nome)
        cv2_.imwrite(dest, img_cv2_final, [cv2_.IMWRITE_JPEG_QUALITY, 92])
        try: gerar_thumbnail(dest)
        except Exception: pass
        return dest

    def _aplicar_manual(pontos_canvas, esc_canvas):
        cantos = np_.array(pontos_canvas, dtype="float32") / esc_canvas
        cantos_ord = _ordenar_cantos(cantos)
        warped = _perspective_transform(img_orig_cv2, cantos_ord, cv2_, np_)
        sem_s  = _remover_sombra(warped, cv2_, np_)
        cinza  = cv2_.cvtColor(sem_s, cv2_.COLOR_BGR2GRAY)
        doc    = cv2_.adaptiveThreshold(cinza, 255,
                     cv2_.ADAPTIVE_THRESH_GAUSSIAN_C, cv2_.THRESH_BINARY, 21, 10)
        return cv2_.medianBlur(doc, 3)

    # ── Janela tkinter ────────────────────────────────────────────────────────
    root = tk.Tk()
    root.configure(bg=BG)
    root.attributes("-topmost", True)
    root.resizable(True, True)
    root.lift()
    root.focus_force()

    def _fechar():
        try:
            root.quit()
            root.update()
            root.destroy()
        except Exception:
            pass

    def _centralizar(w_min=600):
        root.update_idletasks()
        sw = root.winfo_screenwidth(); sh = root.winfo_screenheight()
        w_win = max(w_min, root.winfo_reqwidth())
        h_win = min(root.winfo_reqheight() + 24, sh - 60)
        root.geometry(f"{w_win}x{h_win}+{(sw-w_win)//2}+{(sh-h_win)//2}")
        # Reforça topmost após centralizar (Flet pode ter tomado o foco)
        root.attributes("-topmost", True)
        root.lift()
        root.focus_force()

    modo = ["auto" if cantos_auto is not None else "manual"]
    pontos_manual = []
    esc_canvas    = [1.0]

    # ── MODO AUTO ─────────────────────────────────────────────────────────────
    def _construir_auto():
        for w in root.winfo_children(): w.destroy()
        root.title("Recorte de documento — automático")

        tk.Label(root, text="Recorte detectado automaticamente",
                 font=("Segoe UI", 12, "bold"), fg=TXT, bg=BG).pack(pady=(14, 2))
        tk.Label(root, text="Verifique. Se estiver errado, clique em 'Marcar manualmente'.",
                 font=("Segoe UI", 9), fg=SEC, bg=BG).pack(pady=(0, 10))

        fi = tk.Frame(root, bg=BG); fi.pack(padx=16)

        pnl_o = tk.Frame(fi, bg=CARD, bd=2, relief="groove"); pnl_o.grid(row=0, column=0, padx=(0, 8))
        tk.Label(pnl_o, text="ORIGINAL + CONTORNO", font=("Segoe UI", 8, "bold"), fg=SEC, bg=CARD).pack(pady=(6,2))
        img_o_pil = _PILImage.open(path_origem).convert("RGB")
        img_o_fit, _ = _fit(img_o_pil, PREV_W, PREV_H)
        if cantos_auto is not None:
            ep = img_o_fit.width / img_o_pil.width
            d  = _ImageDraw.Draw(img_o_fit)
            pts = [(int(x*ep), int(y*ep)) for x, y in cantos_auto]
            for i in range(4):
                d.line([pts[i], pts[(i+1)%4]], fill=VERD, width=2)
            cores = ["#FF6B6B","#FFD93D","#6BCB77","#4D96FF"]
            for i,(px,py) in enumerate(pts):
                d.ellipse([px-6,py-6,px+6,py+6], fill=cores[i], outline="white")
                d.text((px+8,py-6), str(i+1), fill=VERD)
        tk_o = _ImageTk.PhotoImage(img_o_fit)
        lbl_o = tk.Label(pnl_o, image=tk_o, bg=CARD, width=PREV_W, height=PREV_H)
        lbl_o.image = tk_o; lbl_o.pack(padx=4, pady=(0,6))

        pnl_p = tk.Frame(fi, bg=CARD, bd=2, relief="groove"); pnl_p.grid(row=0, column=1, padx=(8,0))
        tk.Label(pnl_p, text="RESULTADO PROCESSADO", font=("Segoe UI", 8, "bold"), fg=AZUL, bg=CARD).pack(pady=(6,2))
        if path_proc and os.path.exists(path_proc):
            img_p_pil = _PILImage.open(path_proc).convert("RGB")
            img_p_fit, _ = _fit(img_p_pil, PREV_W, PREV_H)
            tk_p = _ImageTk.PhotoImage(img_p_fit)
            lbl_p = tk.Label(pnl_p, image=tk_p, bg=CARD, width=PREV_W, height=PREV_H)
            lbl_p.image = tk_p; lbl_p.pack(padx=4, pady=(0,6))
        else:
            tk.Label(pnl_p, text="Falha no processamento", fg="#DA3633", bg=CARD,
                     width=PREV_W//7, height=4).pack(expand=True)

        fb = tk.Frame(root, bg=BG); fb.pack(pady=14)
        bst = {"font":("Segoe UI",10,"bold"),"height":2,"relief":"flat","cursor":"hand2","bd":0}

        def _cancelar():   resultado_final[0] = None;                  _fechar()
        def _original():   resultado_final[0] = _salvar_original();    _fechar()
        def _manual():     _construir_manual()
        def _confirmar():
            if path_proc and os.path.exists(path_proc):
                nome = os.path.basename(path_proc)
                dest = os.path.join(pasta_destino, nome)
                os.makedirs(pasta_destino, exist_ok=True)
                shutil.move(path_proc, dest)
                try: gerar_thumbnail(dest)
                except Exception: pass
                resultado_final[0] = dest
            else:
                resultado_final[0] = _salvar_original()
            _fechar()

        tk.Button(fb, text="Cancelar",           command=_cancelar,  bg=BD,       fg=SEC, width=14, **bst).grid(row=0,column=0,padx=5)
        tk.Button(fb, text="Marcar manualmente", command=_manual,    bg="#30363D", fg=TXT, width=18, **bst).grid(row=0,column=1,padx=5)
        tk.Button(fb, text="Usar original",      command=_original,  bg="#30363D", fg=TXT, width=14, **bst).grid(row=0,column=2,padx=5)
        tk.Button(fb, text="✓  Confirmar",       command=_confirmar, bg="#1F6FEB", fg="#FFFFFF", width=14, **bst).grid(row=0,column=3,padx=5)

        root.bind("<Escape>", lambda e: _cancelar())
        root.protocol("WM_DELETE_WINDOW", _fechar)
        _centralizar(PREV_W * 2 + 80)

    # ── MODO MANUAL ───────────────────────────────────────────────────────────
    def _construir_manual(res_cv2=None):
        for w in root.winfo_children(): w.destroy()
        pontos_manual.clear()

        if res_cv2 is None:
            root.title("Recorte manual — clique nos 4 cantos do documento")
            tk.Label(root, text="Clique nos 4 cantos do documento em sentido horário",
                     font=("Segoe UI", 12, "bold"), fg=TXT, bg=BG).pack(pady=(14,2))
            lbl_inst = tk.Label(root, text="1° clique: canto superior-esquerdo",
                                font=("Segoe UI", 9), fg=AZUL, bg=BG)
            lbl_inst.pack(pady=(0,8))

            img_pil = _PILImage.open(path_origem).convert("RGB")
            img_fit, esc = _fit(img_pil, CANVAS_W, CANVAS_H)
            esc_canvas[0] = esc

            canvas = tk.Canvas(root, width=img_fit.width, height=img_fit.height,
                               bg=CARD, cursor="crosshair", highlightthickness=0)
            canvas.pack(padx=16, pady=4)
            tk_img = _ImageTk.PhotoImage(img_fit)
            canvas.create_image(0, 0, anchor="nw", image=tk_img)
            canvas._tk_img = tk_img

            instrucoes = [
                "1° clique: canto superior-esquerdo",
                "2° clique: canto superior-direito",
                "3° clique: canto inferior-direito",
                "4° clique: canto inferior-esquerdo",
            ]
            cores_pt = ["#FF6B6B","#FFD93D","#6BCB77","#4D96FF"]

            def _on_click(event):
                idx = len(pontos_manual)
                if idx >= 4: return
                px, py = event.x, event.y
                pontos_manual.append((px, py))
                canvas.create_oval(px-7,py-7,px+7,py+7, fill=cores_pt[idx], outline="white", width=2)
                canvas.create_text(px+12, py, text=str(idx+1), fill="white", font=("Segoe UI",9,"bold"))
                if idx > 0:
                    x0,y0 = pontos_manual[idx-1]
                    canvas.create_line(x0,y0,px,py, fill=AZUL, width=2)
                if idx == 3:
                    x0,y0 = pontos_manual[0]
                    canvas.create_line(px,py,x0,y0, fill=AZUL, width=2)
                    lbl_inst.config(text="Processando...")
                    root.after(300, lambda: _processar_manual())
                elif idx < 3:
                    lbl_inst.config(text=instrucoes[idx+1])

            canvas.bind("<Button-1>", _on_click)

            fb = tk.Frame(root, bg=BG); fb.pack(pady=10)
            bst = {"font":("Segoe UI",10,"bold"),"height":2,"relief":"flat","cursor":"hand2","bd":0}

            def _cancelar():  resultado_final[0] = None;               _fechar()
            def _original():  resultado_final[0] = _salvar_original(); _fechar()
            def _refazer():   _construir_manual()

            tk.Button(fb, text="Cancelar",     command=_cancelar, bg=BD,        fg=SEC, width=14, **bst).grid(row=0,column=0,padx=5)
            tk.Button(fb, text="Recomeçar",    command=_refazer,  bg="#30363D", fg=TXT, width=14, **bst).grid(row=0,column=1,padx=5)
            tk.Button(fb, text="Usar original",command=_original, bg="#30363D", fg=TXT, width=14, **bst).grid(row=0,column=2,padx=5)

            root.bind("<Escape>", lambda e: _cancelar())
            root.protocol("WM_DELETE_WINDOW", _fechar)
            _centralizar(max(CANVAS_W + 32, 600))

        else:
            root.title("Recorte manual — resultado")
            tk.Label(root, text="Resultado do recorte manual",
                     font=("Segoe UI", 12, "bold"), fg=TXT, bg=BG).pack(pady=(14,2))
            tk.Label(root, text="Confirme ou refaça a marcação.",
                     font=("Segoe UI", 9), fg=SEC, bg=BG).pack(pady=(0,10))

            fi = tk.Frame(root, bg=BG); fi.pack(padx=16)

            # Original com pontos
            pnl_o = tk.Frame(fi, bg=CARD, bd=2, relief="groove"); pnl_o.grid(row=0,column=0,padx=(0,8))
            tk.Label(pnl_o, text="SELEÇÃO", font=("Segoe UI",8,"bold"), fg=SEC, bg=CARD).pack(pady=(6,2))
            img_o_pil = _PILImage.open(path_origem).convert("RGB")
            img_o_fit, esc_prev = _fit(img_o_pil, PREV_W, PREV_H)
            d = _ImageDraw.Draw(img_o_fit)
            fator = esc_prev / esc_canvas[0]
            pts = [(int(x*fator), int(y*fator)) for x,y in pontos_manual]
            cores_pt = ["#FF6B6B","#FFD93D","#6BCB77","#4D96FF"]
            for i in range(len(pts)):
                d.line([pts[i], pts[(i+1)%len(pts)]], fill=VERD, width=2)
            for i,(px,py) in enumerate(pts):
                d.ellipse([px-7,py-7,px+7,py+7], fill=cores_pt[i], outline="white")
                d.text((px+10,py-7), str(i+1), fill="white")
            tk_o = _ImageTk.PhotoImage(img_o_fit)
            lbl_o = tk.Label(pnl_o, image=tk_o, bg=CARD, width=PREV_W, height=PREV_H)
            lbl_o.image = tk_o; lbl_o.pack(padx=4, pady=(0,6))

            # Resultado
            pnl_p = tk.Frame(fi, bg=CARD, bd=2, relief="groove"); pnl_p.grid(row=0,column=1,padx=(8,0))
            tk.Label(pnl_p, text="RESULTADO", font=("Segoe UI",8,"bold"), fg=AZUL, bg=CARD).pack(pady=(6,2))
            if len(res_cv2.shape) == 2:
                res_pil = _PILImage.fromarray(res_cv2, mode="L").convert("RGB")
            else:
                res_pil = _PILImage.fromarray(cv2_.cvtColor(res_cv2, cv2_.COLOR_BGR2RGB))
            res_fit, _ = _fit(res_pil, PREV_W, PREV_H)
            tk_p = _ImageTk.PhotoImage(res_fit)
            lbl_p = tk.Label(pnl_p, image=tk_p, bg=CARD, width=PREV_W, height=PREV_H)
            lbl_p.image = tk_p; lbl_p.pack(padx=4, pady=(0,6))

            fb = tk.Frame(root, bg=BG); fb.pack(pady=14)
            bst = {"font":("Segoe UI",10,"bold"),"height":2,"relief":"flat","cursor":"hand2","bd":0}

            def _cancelar():  resultado_final[0] = None;               _fechar()
            def _original():  resultado_final[0] = _salvar_original(); _fechar()
            def _refazer():   _construir_manual()
            def _confirmar(): resultado_final[0] = _salvar_processada(res_cv2); _fechar()

            tk.Button(fb, text="Cancelar",     command=_cancelar,  bg=BD,        fg=SEC,      width=14, **bst).grid(row=0,column=0,padx=5)
            tk.Button(fb, text="Refazer",      command=_refazer,   bg="#30363D", fg=TXT,      width=14, **bst).grid(row=0,column=1,padx=5)
            tk.Button(fb, text="Usar original",command=_original,  bg="#30363D", fg=TXT,      width=14, **bst).grid(row=0,column=2,padx=5)
            tk.Button(fb, text="✓  Confirmar", command=_confirmar, bg="#1F6FEB", fg="#FFFFFF", width=14, **bst).grid(row=0,column=3,padx=5)

            root.bind("<Escape>", lambda e: _cancelar())
            root.protocol("WM_DELETE_WINDOW", _fechar)
            _centralizar(PREV_W * 2 + 80)

    def _processar_manual():
        try:
            res = _aplicar_manual(pontos_manual, esc_canvas[0])
            _construir_manual(res_cv2=res)
        except Exception as ex:
            print(f"[GUI] transform falhou: {ex}", file=sys.stderr)
            _construir_manual()

    # Iniciar
    if modo[0] == "auto":
        _construir_auto()
    else:
        _construir_manual()

    root.mainloop()

    if resultado_final[0]:
        print(resultado_final[0], flush=True)


if __name__ == "__main__":
    main()
