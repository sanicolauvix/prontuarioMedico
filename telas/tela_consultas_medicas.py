# -*- coding: utf-8 -*-
"""
tela_consultas_medicas.py — Koios Prontuário
Consultas médicas: lista, cadastro, alarme Windows e receitas via IA.
Padrão visual: idêntico a tela_exames.py (header + barra de abas + área de conteúdo)
"""
import logging
import re
import threading
import datetime
import flet as ft
from shared.auth import IS_ANDROID
from dados.model_prontuario import (
    listar_consultas, salvar_consulta, listar_medicos,
    salvar_receita, listar_receitas_laudos as listar_receitas,
    salvar_remedio, listar_remedios,
    registrar_receita_remedios,
)

logger = logging.getLogger(__name__)

# ── Paleta ────────────────────────────────────────────────────
BG   = "#0D1117";  CARD = "#161B22";  BD  = "#21262D";  BD2 = "#30363D"
TXT  = "#E6EDF3";  SEC  = "#8B949E";  MUT = "#484F58"
AZUL = "#58A6FF";  VERD = "#3FB950";  LAR = "#F0883E"
AMAR = "#D29922";  VERM = "#DA3633";  ROXO = "#BC8CFF"


def _flex_parse(s: str) -> "datetime.datetime | None":
    """Parse de data aceita YYYY-MM-DD e DD/MM/YYYY."""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime((s or "")[:10], fmt)
        except ValueError:
            pass
    return None


def _para_display(s: str | None) -> str:
    """Converte YYYY-MM-DD para DD/MM/YYYY para exibicao. DD/MM/YYYY passa sem alteracao."""
    if not s:
        return ""
    s = str(s).strip()
    if len(s) >= 10 and s[4] == "-":
        try:
            return datetime.datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            pass
    return s


CORES_TIPO = {
    "agendada":  (AZUL, "calendar_today_rounded"),
    "realizada": (VERD, "check_circle_outline_rounded"),
    "cancelada": (MUT,  "cancel_outlined_rounded"),
}


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _campo(label, valor="", largura=None, multiline=False, min_lines=1, hint=None,
           keyboard=ft.KeyboardType.TEXT):
    kw = dict(
        label=label, value=valor or "",
        bgcolor=CARD, border_color=BD2,
        focused_border_color=AZUL,
        label_style=ft.TextStyle(color=SEC),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8, multiline=multiline,
        min_lines=min_lines, keyboard_type=keyboard,
    )
    if hint:
        kw["hint_text"] = hint
        kw["hint_style"] = ft.TextStyle(color=MUT, size=11)
    if largura:
        kw["width"] = largura
    else:
        kw["expand"] = True
    return ft.TextField(**kw)


def _label_sec(texto, cor=MUT):
    return ft.Text(texto, size=10, color=cor, weight=ft.FontWeight.W_700)


def _badge(tipo):
    cor, icone = CORES_TIPO.get(tipo, (SEC, "help_outline_rounded"))
    return ft.Container(
        content=ft.Row([
            ft.Icon(icone, size=11, color=cor),
            ft.Text(tipo.capitalize(), size=10, color=cor,
                    weight=ft.FontWeight.W_600),
        ], spacing=4, tight=True),
        bgcolor=f"{cor}18", border_radius=10,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
    )


def _chip_tipo(tipo, selecionado, on_click):
    cor, icone = CORES_TIPO.get(tipo, (SEC, "help_outline_rounded"))
    ativo = tipo == selecionado
    return ft.Container(
        content=ft.Row([
            ft.Icon(icone, size=13, color=cor if ativo else MUT),
            ft.Text(tipo.capitalize(), size=12,
                    color=cor if ativo else MUT,
                    weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.W_400),
        ], spacing=5, tight=True),
        bgcolor=f"{cor}22" if ativo else BD,
        border_radius=20,
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        border=ft.Border(
            top=ft.BorderSide(1, cor if ativo else BD2),
            bottom=ft.BorderSide(1, cor if ativo else BD2),
            left=ft.BorderSide(1, cor if ativo else BD2),
            right=ft.BorderSide(1, cor if ativo else BD2),
        ),
        on_click=on_click,
    )


def _centralizar(corpo, page):
    try:
        larg = page.width or 800
    except Exception:
        larg = 800
    if larg > 500:
        return ft.Container(bgcolor=BG, expand=True, content=ft.Row([
            ft.Container(expand=True),
            ft.Container(content=corpo, width=480),
            ft.Container(expand=True),
        ], expand=True))
    return ft.Container(bgcolor=BG, expand=True, content=corpo)


def _agendar_alarme_windows(data_str, hora_str, descricao):
    import subprocess
    try:
        d = _flex_parse(data_str)
        if d is None:
            return False, "data invalida"
        data_win = d.strftime("%Y-%m-%d")
        hora_win = hora_str or "08:00"
        nome_tarefa = f"Koios_Consulta_{data_win}_{hora_win.replace(':','')}"
        cmd = (
            f'schtasks /create /tn "{nome_tarefa}" /tr '
            f'"msg * Consulta: {descricao}" '
            f'/sc once /d {data_win} /st {hora_win} /f'
        )
        subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return True, nome_tarefa
    except Exception as ex:
        return False, str(ex)


# ══════════════════════════════════════════════════════════════
# CAMPO MÉDICO — padrão Koios de busca
# ══════════════════════════════════════════════════════════════

def _campo_medico(page, medicos, med_id_sel, valor_ini="", read_only=False):
    """Retorna (coluna_com_busca, chip) para uso na ficha."""

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
        hint_text="Buscar médico...",
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

    if not read_only:
        med_chip.on_click = _limpar

    if valor_ini:
        _mostrar_chip(valor_ini)

    if read_only:
        tf.visible = False
        sugestoes.visible = False

    def _filtrar(e):
        if read_only:
            return
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
                content=ft.Text("Nenhum médico encontrado.", size=12, color=MUT),
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            ))
            sugestoes.visible = True
            try: page.update()
            except Exception: pass
            return
        for m in matches:
            esp = m.get("especialidade") or ""
            def make_sel(med=m):
                def sel(e):
                    med_id_sel[0] = str(med["id"])
                    _mostrar_chip(med["nome"])
                return sel
            sugestoes.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("person_rounded", size=13, color=AZUL),
                    ft.Column([
                        ft.Text(m["nome"], size=13, color=TXT),
                        ft.Text(esp, size=10, color=MUT) if esp else ft.Container(),
                    ], spacing=1, expand=True, tight=True),
                    ft.Icon("add_circle_outline_rounded", size=14, color=AZUL),
                ], spacing=8),
                bgcolor=CARD, border_radius=6,
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                border=ft.Border(
                    left=ft.BorderSide(2, AZUL),
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
                on_click=make_sel(), ink=True,
            ))
        sugestoes.visible = True
        try: page.update()
        except Exception: pass

    tf.on_change = _filtrar

    col = ft.Column([
        _label_sec("MÉDICO"),
        med_chip,
        tf,
        sugestoes,
    ], spacing=4)

    col._tf_medico   = tf
    col._chip_medico = med_chip
    col._limpar_fn   = _limpar
    return col


# ══════════════════════════════════════════════════════════════
# TELA DE RECEITA
# ══════════════════════════════════════════════════════════════

def _parsear_remedios_texto(texto: str) -> list[dict]:
    """Converte texto livre da IA em lista de dicts com nome/dosagem/frequencia/obs."""
    remedios = []
    for linha in texto.splitlines():
        linha = linha.strip().lstrip("•-*·").strip()
        if not linha:
            continue
        # Tenta separar "Nome dosagem — instrucoes" ou "Nome dosagem : instrucoes"
        partes = re.split(r"\s*[—–-]{1,2}\s*|\s*:\s*", linha, maxsplit=1)
        cabecalho = partes[0].strip()
        instrucoes = partes[1].strip() if len(partes) > 1 else ""
        # Extrai dosagem do cabecalho (ex: "Amoxicilina 500mg")
        m = re.search(r"(\d+\s*(?:mg|mcg|g|ml|UI|ui|cp|comp|cap|cáp|gotas?|%)[^\s]*)", cabecalho, re.I)
        if m:
            dosagem = m.group(1)
            nome = cabecalho[:m.start()].strip()
        else:
            dosagem = ""
            nome = cabecalho
        if not nome:
            continue
        # Tenta extrair frequência das instruções (ex: "de 8 em 8h", "2x ao dia")
        freq = ""
        mf = re.search(
            r"(\d+x?\s*(?:ao\s*dia|por\s*dia|vezes?\s*ao\s*dia)|de\s*\d+\s*em\s*\d+\s*h(?:oras?)?|a\s*cada\s*\d+\s*h(?:oras?)?|\d+\s*[×x]\s*ao\s*dia)",
            instrucoes, re.I)
        if mf:
            freq = mf.group(1)
        remedios.append({
            "nome": nome,
            "dosagem": dosagem,
            "frequencia": freq,
            "observacoes": instrucoes,
        })
    return remedios


def _tela_receita(page, consulta, voltar_fn):
    lista_rec       = ft.Column(spacing=8)
    txt_status_ia   = ft.Text("", size=12, color=SEC)
    txt_instrucoes  = _campo("Instruções de uso extraídas",
                             multiline=True, min_lines=4)
    foto_path       = [""]
    _receita_id_sal = [None]   # id da receita salva (para vincular remédios)

    def _carregar_lista():
        lista_rec.controls.clear()
        recs = listar_receitas(consulta["id"])
        if not recs:
            lista_rec.controls.append(ft.Container(
                content=ft.Text("Nenhuma receita cadastrada.", color=SEC, size=13),
                padding=ft.padding.symmetric(vertical=12),
            ))
        for r in recs:
            lista_rec.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("receipt_long_rounded", size=20, color=ROXO),
                    ft.Column([
                        ft.Text(r.get("nome_arquivo") or "Receita", size=13,
                                color=TXT, weight=ft.FontWeight.W_600),
                        ft.Text(r.get("observacoes") or "", size=11, color=SEC,
                                max_lines=2),
                    ], spacing=2, expand=True),
                    ft.Text(r.get("data") or "", size=11, color=MUT),
                ], spacing=10),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                border=ft.Border(
                    left=ft.BorderSide(2, ROXO),
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
            ))
        try: page.update()
        except Exception: pass

    btn_extrair = ft.FilledButton(
        content=ft.Row([
            ft.Icon("auto_awesome_rounded", size=15),
            ft.Text("Extrair com IA", size=13, weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        style=ft.ButtonStyle(
            bgcolor=ROXO,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
        ),
        visible=False,
    )

    def _selecionar_foto(e):
        def _picker():
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk(); root.withdraw()
                root.attributes("-topmost", True)
                caminho = filedialog.askopenfilename(
                    title="Selecionar foto da receita",
                    filetypes=[("Imagens", "*.jpg *.jpeg *.png *.webp")],
                )
                root.destroy()
                if not caminho:
                    return
                foto_path[0] = caminho
                nome = caminho.replace("\\", "/").split("/")[-1]
                page.pubsub.send_all({"_tipo": "receita_foto", "nome": nome})
            except Exception as ex:
                logger.error("_selecionar_foto: %s", str(ex), exc_info=True)
                page.pubsub.send_all({"_tipo": "receita_foto", "erro": str(ex)})

        _sub = [False]
        def _on_msg(msg):
            if not isinstance(msg, dict) or msg.get("_tipo") != "receita_foto":
                return
            if "erro" in msg:
                txt_status_ia.value = f"Erro: {msg['erro']}"
                txt_status_ia.color = VERM
            else:
                txt_status_ia.value = msg["nome"]
                txt_status_ia.color = SEC
                btn_extrair.visible = True
            try: page.update()
            except Exception: pass

        if not _sub[0]:
            page.pubsub.subscribe(_on_msg)
            _sub[0] = True
        threading.Thread(target=_picker, daemon=True).start()

    # resultado da IA fica aqui para o callback acessar
    _ia_resultado = [None]  # {"remedios": [...], "texto": "..."}

    def _on_ia_resultado(msg):
        """Subscriber permanente — processa resultado da extração de receita."""
        if not isinstance(msg, dict) or msg.get("_tipo") != "receita_ia":
            return
        btn_extrair.disabled = False
        if "erro" in msg:
            txt_status_ia.value = f"Erro na IA: {msg['erro']}"
            txt_status_ia.color = VERM
            try: page.update()
            except Exception: pass
            return
        raw      = msg.get("texto", "")
        remedios = msg.get("remedios") or []
        if not remedios:
            remedios = _parsear_remedios_texto(raw)
        txt_instrucoes.value = raw
        if remedios:
            txt_status_ia.value = f"✓ {len(remedios)} medicamento(s) — revise e confirme"
            txt_status_ia.color = VERD
            try: page.update()
            except Exception: pass
            _abrir_overlay_remedios_dados(remedios)
        else:
            txt_status_ia.value = "Nenhum medicamento identificado"
            txt_status_ia.color = AMAR
            btn_salvar_remedios.visible = False
            try: page.update()
            except Exception: pass

    page.pubsub.subscribe(_on_ia_resultado)

    def _extrair_ia(e):
        if not foto_path[0]:
            txt_status_ia.value = "Selecione uma foto primeiro."
            try: page.update()
            except Exception: pass
            return
        txt_status_ia.value = "Analisando receita com IA..."
        txt_status_ia.color = AZUL
        btn_extrair.disabled = True
        try: page.update()
        except Exception: pass

        def _analisar():
            try:
                import base64, json, urllib.request
                from dados.model_prontuario import get_config
                api_key = get_config("anthropic_api_key", "")
                with open(foto_path[0], "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                ext  = foto_path[0].rsplit(".", 1)[-1].lower()
                mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                        "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
                prompt = (
                    "Esta é uma foto de uma receita médica brasileira com letra possivelmente ilegível.\n\n"
                    "REGRAS CRÍTICAS:\n"
                    "1. Use o contexto clínico para inferir nomes de medicamentos com grafia ruim.\n"
                    "   Ex: 'Rimina', 'Litmine', 'Ritaline' -> provavelmente 'Ritalina' (metilfenidato).\n"
                    "2. Considere a especialidade do medico e outros remedios para inferir nomes.\n"
                    "3. NUNCA descarte um item por nao reconhecer — inclua com sua melhor interpretacao.\n\n"
                    "Extraia TODOS os medicamentos e retorne APENAS um JSON array valido, sem markdown:\n"
                    '[{"nome":"nome correto","nome_original":"como esta escrito",'
                    '"dosagem":"10mg ou null","frequencia":"1cp 2x/dia ou null",'
                    '"observacoes":"instrucoes ou null","confianca":"alta|media|baixa"}]'
                )
                headers = {
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                }
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
                try:
                    import re as _re
                    m = _re.search(r'\[.*\]', raw, _re.DOTALL)
                    remedios_json = json.loads(m.group()) if m else []
                except Exception:
                    remedios_json = []
                page.pubsub.send_all({
                    "_tipo": "receita_ia",
                    "texto": raw,
                    "remedios": remedios_json,
                })
            except Exception as ex:
                logger.error("_extrair_ia: %s", str(ex), exc_info=True)
                page.pubsub.send_all({"_tipo": "receita_ia", "erro": str(ex)[:80]})

        threading.Thread(target=_analisar, daemon=True).start()

    btn_extrair.on_click = _extrair_ia

    def _abrir_overlay_remedios(e):
        remedios_parsed = _parsear_remedios_texto(txt_instrucoes.value or "")
        if not remedios_parsed:
            txt_status_ia.value = "Nenhum medicamento encontrado no texto."
            txt_status_ia.color = AMAR
            try: page.update()
            except Exception: pass
            return
        _abrir_overlay_remedios_dados(remedios_parsed)

    def _abrir_overlay_remedios_dados(remedios_parsed):

        ref_ov = [None]

        def _fechar(e=None):
            if ref_ov[0] in page.overlay:
                page.overlay.remove(ref_ov[0])
            try: page.update()
            except Exception: pass

        # Campos editáveis + checkbox por medicamento
        itens_ui = []
        for r in remedios_parsed:
            confianca    = r.get("confianca", "alta")
            nome_orig    = r.get("nome_original", "")
            cor_conf     = VERD if confianca == "alta" else AMAR if confianca == "media" else VERM
            label_conf   = {"alta": "✓ leitura segura", "media": "⚠ inferido", "baixa": "⚠ incerto"}.get(confianca, "")

            sel = ft.Checkbox(value=True, active_color=VERD)
            fn  = ft.TextField(
                value=r.get("nome") or nome_orig,
                label="Medicamento (edite se necessário)",
                bgcolor="#0D1117", border_color=BD2, focused_border_color=VERD,
                label_style=ft.TextStyle(color=SEC, size=10),
                text_style=ft.TextStyle(color=TXT, size=13),
                border_radius=6, expand=True,
            )
            fd  = ft.TextField(
                value=r.get("dosagem") or "",
                label="Dosagem",
                bgcolor="#0D1117", border_color=BD2, focused_border_color=VERD,
                label_style=ft.TextStyle(color=SEC, size=10),
                text_style=ft.TextStyle(color=TXT, size=12),
                border_radius=6, width=110,
            )
            ff  = ft.TextField(
                value=r.get("frequencia") or "",
                label="Frequência",
                bgcolor="#0D1117", border_color=BD2, focused_border_color=VERD,
                label_style=ft.TextStyle(color=SEC, size=10),
                text_style=ft.TextStyle(color=TXT, size=12),
                border_radius=6, expand=True,
            )
            itens_ui.append({
                "sel": sel, "fn": fn, "fd": fd, "ff": ff,
                "obs": r.get("observacoes"),
                "nome_orig": nome_orig,
                "cor_conf": cor_conf,
                "label_conf": label_conf,
            })

        cards_col = ft.Column(spacing=8)
        for it in itens_ui:
            # Linha de aviso se nome foi inferido
            aviso = []
            if it["nome_orig"] and it["nome_orig"] != (it["fn"].value or ""):
                aviso.append(ft.Row([
                    ft.Icon("warning_amber_rounded", size=12, color=it["cor_conf"]),
                    ft.Text(
                        f"Escrito na receita: \"{it['nome_orig']}\" — {it['label_conf']}",
                        size=10, color=it["cor_conf"], italic=True,
                    ),
                ], spacing=4))

            cards_col.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        it["sel"],
                        it["fn"],
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    *aviso,
                    ft.Row([it["fd"], it["ff"]], spacing=6),
                ], spacing=4),
                bgcolor=BD, border_radius=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=10),
                border=ft.Border(
                    top=ft.BorderSide(1, BD2), bottom=ft.BorderSide(1, BD2),
                    left=ft.BorderSide(2, it["cor_conf"]), right=ft.BorderSide(1, BD2),
                ),
            ))

        txt_result = ft.Text("", size=12, color=VERD)

        def _confirmar(e):
            medico_id  = consulta.get("medico_id")
            data_ini   = consulta.get("data") or datetime.date.today().isoformat()
            rid_rec    = _receita_id_sal[0]
            consulta_id = consulta.get("id")

            # Monta lista apenas dos selecionados com dados editados
            selecionados = []
            for it in itens_ui:
                if not it["sel"].value:
                    continue
                nome_val = (it["fn"].value or "").strip()
                if not nome_val:
                    continue
                selecionados.append({
                    "nome":        nome_val,
                    "dosagem":     (it["fd"].value or "").strip() or None,
                    "frequencia":  (it["ff"].value or "").strip() or None,
                    "observacoes": it.get("obs"),
                })

            if not selecionados:
                txt_result.value = "Nenhum medicamento selecionado."
                txt_result.color = AMAR
                try: page.update()
                except Exception: pass
                return

            resultado = registrar_receita_remedios(
                remedios_extraidos=selecionados,
                receita_id=rid_rec,
                consulta_id=consulta_id,
                medico_id=medico_id,
                data_consulta=data_ini,
            )

            novos     = sum(1 for r in resultado if not r["ja_existia"])
            atualizados = sum(1 for r in resultado if r["ja_existia"])
            partes = []
            if novos:       partes.append(f"{novos} cadastrado(s)")
            if atualizados: partes.append(f"{atualizados} atualizado(s) + mov. registrada")
            txt_result.value = "✓ " + ", ".join(partes)
            txt_result.color = VERD
            try: page.update()
            except Exception: pass

            import threading as _thr
            def _bkp():
                try:
                    from backup.drive_backup import fazer_backup
                    fazer_backup(forcar=True)
                except Exception: pass
            _thr.Thread(target=_bkp, daemon=True).start()

            import threading as _thr2
            def _fechar_delay():
                import time; time.sleep(1.5)
                _fechar()
            _thr2.Thread(target=_fechar_delay, daemon=True).start()

        btn_conf = ft.Container(
            content=ft.Row([
                ft.Icon("medication_rounded", size=14, color=BG),
                ft.Text("Salvar selecionados", size=13, color=BG,
                        weight=ft.FontWeight.W_600),
            ], spacing=6, tight=True, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=VERD, border_radius=10, ink=True,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            expand=True, alignment=ft.alignment.Alignment(0, 0),
        )
        btn_conf.on_click = _confirmar

        btn_cancel = ft.Container(
            content=ft.Text("Cancelar", size=13, color=SEC),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border_radius=10, bgcolor=BD, ink=True,
        )
        btn_cancel.on_click = _fechar

        ref_ov[0] = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("medication_rounded", size=16, color=VERD),
                        ft.Text("Salvar em Remédios", size=15, color=TXT,
                                weight=ft.FontWeight.W_700, expand=True),
                    ], spacing=8),
                    ft.Text("Revise, desmarque o que não quer salvar e confirme.",
                            size=11, color=SEC),
                    ft.Container(height=4),
                    cards_col,
                    txt_result,
                    ft.Container(height=8),
                    ft.Row([btn_cancel, btn_conf], spacing=8),
                ], spacing=8, tight=True,
                   scroll=ft.ScrollMode.AUTO),
                bgcolor=CARD, border_radius=14,
                padding=ft.padding.all(20), width=380,
            ),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ref_ov[0].on_click = _fechar
        page.overlay.append(ref_ov[0])
        try: page.update()
        except Exception: pass

    btn_salvar_remedios = ft.Container(
        content=ft.Row([
            ft.Icon("medication_rounded", size=14, color=VERD),
            ft.Text("Salvar em Remédios", size=12, color=VERD,
                    weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        border_radius=8,
        bgcolor=ft.Colors.with_opacity(0.12, VERD),
        border=ft.Border(
            top=ft.BorderSide(1, ft.Colors.with_opacity(0.40, VERD)),
            bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.40, VERD)),
            left=ft.BorderSide(1, ft.Colors.with_opacity(0.40, VERD)),
            right=ft.BorderSide(1, ft.Colors.with_opacity(0.40, VERD)),
        ),
        ink=True, visible=False,
    )
    btn_salvar_remedios.on_click = _abrir_overlay_remedios

    def _salvar_receita(e):
        if not foto_path[0] and not txt_instrucoes.value.strip():
            txt_status_ia.value = "Adicione uma foto ou instruções."
            try: page.update()
            except Exception: pass
            return

        txt_status_ia.value = "Salvando receita..."
        txt_status_ia.color = AZUL
        try: page.update()
        except Exception: pass

        def _run():
            drive_id = None
            nome_arq = ""
            foto_local = foto_path[0]
            if foto_local:
                try:
                    from utils.drive_sync import upload_receita
                    drive_id, nome_arq = upload_receita(
                        foto_local, consulta["id"])
                except Exception as ex:
                    logger.error("upload receita Drive: %s", ex, exc_info=True)
                    nome_arq = foto_local.replace("\\", "/").split("/")[-1]

            rid = salvar_receita({
                "consulta_id":   consulta["id"],
                "medico_id":     consulta.get("medico_id"),
                "drive_file_id": drive_id,
                "nome_arquivo":  nome_arq,
                "data":          datetime.date.today().isoformat(),
                "observacoes":   txt_instrucoes.value.strip() or None,
            })
            _receita_id_sal[0] = rid
            foto_path[0]       = ""

            page.pubsub.send_all({"_tipo": "receita_salva", "rid": rid,
                                  "nome": nome_arq})

        def _on_salva(msg):
            if not isinstance(msg, dict) or msg.get("_tipo") != "receita_salva":
                return
            txt_status_ia.value = "✓ Receita salva! Agora salve os remédios →"
            txt_status_ia.color = VERD
            btn_extrair.visible = False
            btn_salvar_remedios.visible = bool(
                _parsear_remedios_texto(txt_instrucoes.value or ""))
            _carregar_lista()

        page.pubsub.subscribe(_on_salva)
        threading.Thread(target=_run, daemon=True).start()

    _carregar_lista()

    medico_txt = consulta.get("medico") or "Médico não informado"
    data_txt   = consulta.get("data") or ""
    hora_txt   = consulta.get("hora") or ""

    cabecalho = ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Row([
                    ft.Icon("arrow_back_rounded", size=16),
                    ft.Text("Voltar", size=13),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                ink=True,
                on_click=lambda e: voltar_fn(),
            ),
            ft.Column([
                ft.Text("Receitas", size=18, weight=ft.FontWeight.W_700, color=TXT),
                ft.Text(f"{medico_txt}  ·  {data_txt} {hora_txt}",
                        size=11, color=SEC),
            ], spacing=1, expand=True),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=16, vertical=14),
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
    )

    corpo = ft.Column([
        cabecalho,
        ft.Container(
            content=ft.Column([
                _label_sec("RECEITAS CADASTRADAS"),
                lista_rec,
                ft.Container(height=1, bgcolor=BD,
                             margin=ft.margin.symmetric(vertical=8)),
                _label_sec("ADICIONAR RECEITA", ROXO),
                ft.Row([
                    ft.OutlinedButton(
                        content=ft.Row([
                            ft.Icon("camera_alt_outlined_rounded", size=15, color=ROXO),
                            ft.Text("Foto da receita", size=12, color=ROXO),
                        ], spacing=6, tight=True),
                        style=ft.ButtonStyle(
                            side=ft.BorderSide(1, ROXO),
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                        on_click=_selecionar_foto,
                    ),
                    btn_extrair,
                ], spacing=8),
                txt_status_ia,
                txt_instrucoes,
                ft.Row([
                    ft.FilledButton(
                        content=ft.Row([
                            ft.Icon("save_rounded", size=15),
                            ft.Text("Salvar Receita", size=13, weight=ft.FontWeight.W_600),
                        ], spacing=6, tight=True),
                        style=ft.ButtonStyle(
                            bgcolor=AZUL,
                            shape=ft.RoundedRectangleBorder(radius=8),
                            padding=ft.padding.symmetric(horizontal=16, vertical=12),
                        ),
                        on_click=_salvar_receita,
                    ),
                    btn_salvar_remedios,
                ], spacing=8, wrap=True),
                ft.Container(height=20),
            ], spacing=10, scroll=ft.ScrollMode.AUTO),
            padding=ft.padding.all(16),
            expand=True,
        ),
    ], expand=True, spacing=0)

    return _centralizar(corpo, page)


# ══════════════════════════════════════════════════════════════
# TELA DE CADASTRO / EDIÇÃO DE CONSULTA
# ══════════════════════════════════════════════════════════════

def _tela_ficha_consulta(page, consulta, voltar_fn, medicos):
    is_novo      = consulta is None
    _modo_edicao = [is_novo]
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
                bgcolor=CARD, border_radius=14, padding=ft.padding.all(24), width=240,
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
                logger.warning("[consultas] sync erro: %s", ex)
            finally:
                _status_banco[0] = "normal"
                if ov in page.overlay: page.overlay.remove(ov)
                try: page.update()
                except Exception: pass
                if apos_sync_fn: apos_sync_fn()
        threading.Thread(target=_run, daemon=True).start()

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
            if e.key == "Escape": _sair(voltar_fn)
        page.on_keyboard_event = _on_hw

    def _desregistrar_voltar_hw():
        page.on_keyboard_event = _handler_ant[0]

    titulo = "Nova Consulta" if is_novo else "Consulta"

    from shared.date_field import campo_data as _campo_data
    from dados.model_prontuario import normalizar_data as _norm_data

    ro = not _modo_edicao[0]

    med_map    = {str(m["id"]): m["nome"] for m in medicos}
    med_id_sel = [str(consulta["medico_id"])
                  if consulta and consulta.get("medico_id") else None]
    valor_ini  = med_map.get(med_id_sel[0], "") if med_id_sel[0] else ""

    col_medico = _campo_medico(page, medicos, med_id_sel, valor_ini, read_only=ro)

    row_data, f_data = _campo_data(
        page,
        label="Data",
        value=consulta["data"] if consulta else "",
        obrigatorio=True,
        cor_acento=AZUL,
        largura=160,
    )
    f_hora = _campo("Hora", consulta.get("hora", "") if consulta else "",
                    hint="HH:MM", largura=90)
    def _mask_hora_consulta(e):
        raw = "".join(c for c in (f_hora.value or "") if c.isdigit())[:4]
        out = (raw[:2] + ":" + raw[2:]) if len(raw) >= 3 else raw
        if f_hora.value != out:
            f_hora.value = out
            try: f_hora.update()
            except Exception: pass
    f_hora.on_change = _mask_hora_consulta

    f_local = _campo("Local / Clínica",
                     consulta.get("local", "") if consulta else "")
    f_obs   = _campo("Observações",
                     consulta.get("observacoes", "") if consulta else "",
                     multiline=True, min_lines=3)
    for _f in [f_hora, f_local, f_obs]:
        _f.read_only = ro
    f_data.read_only = ro

    # ── Pauta (itens a tratar) ────────────────────────────
    import json as _json
    _pauta_raw = consulta.get("pauta", "[]") if consulta else "[]"
    try:
        _pauta_lista = _json.loads(_pauta_raw) if isinstance(_pauta_raw, str) else (_pauta_raw or [])
    except Exception:
        _pauta_lista = []
    pauta_itens = list(_pauta_lista)   # copia mutavel

    f_novo_item = _campo("Adicionar item à pauta...", largura=None)
    pauta_col   = ft.Column(spacing=6)

    def _rebuild_pauta():
        pauta_col.controls.clear()
        em_ro = not _modo_edicao[0]
        for idx, item in enumerate(pauta_itens):
            def _rm(e, i=idx):
                del pauta_itens[i]
                _rebuild_pauta()
            btn_rm = ft.Container(
                content=ft.Icon("close_rounded", size=13, color=MUT),
                padding=4, border_radius=4, ink=True,
                on_click=_rm,
                visible=not em_ro,
            )
            pauta_col.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon("check_circle_outline_rounded", size=14, color=AZUL),
                    ft.Text(item, size=12, color=TXT, expand=True),
                    btn_rm,
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD,
                border=ft.border.all(1, BD),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
            ))
        if not pauta_itens:
            pauta_col.controls.append(
                ft.Text("Nenhum item adicionado.", size=11, color=MUT)
            )
        try: page.update()
        except Exception: pass

    def _add_item(e=None):
        txt = f_novo_item.value.strip()
        if not txt:
            return
        pauta_itens.append(txt)
        f_novo_item.value = ""
        _rebuild_pauta()

    f_novo_item.on_submit = _add_item

    btn_add_item = ft.Container(
        content=ft.Row([
            ft.Icon("add_rounded", size=14, color=AZUL),
            ft.Text("Adicionar", size=12, color=AZUL),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8, bgcolor=ft.Colors.with_opacity(0.12, AZUL),
        border=ft.border.all(1, ft.Colors.with_opacity(0.3, AZUL)),
        ink=True,
    )
    btn_add_item.on_click = _add_item

    row_nova_pauta = ft.Row([f_novo_item, btn_add_item], spacing=8,
                             visible=not ro)

    _rebuild_pauta()

    tipo_sel  = [consulta.get("tipo", "agendada") if consulta else "agendada"]
    chips_row = ft.Row(spacing=8)
    txt_erro  = ft.Text("", color=VERM, size=12)
    txt_alarme= ft.Text("", size=11, color=VERD)

    def _rebuild_chips():
        chips_row.controls.clear()
        for t in ["agendada", "realizada", "cancelada"]:
            def _on(e, tp=t):
                if not _modo_edicao[0]:
                    return
                tipo_sel[0] = tp
                _rebuild_chips()
            chips_row.controls.append(_chip_tipo(t, tipo_sel[0], _on))
        try: page.update()
        except Exception: pass

    btn_agendar_alarme = ft.Container(
        content=ft.Row([
            ft.Icon("alarm_add_rounded", size=16, color=AMAR),
            ft.Text("Agendar Alarme", size=13, color=AMAR),
        ], spacing=6, tight=True),
        bgcolor=ft.Colors.with_opacity(0.12, AMAR),
        border=ft.border.all(1, ft.Colors.with_opacity(0.4, AMAR)),
        border_radius=8, ink=True,
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        visible=not IS_ANDROID,
    )

    def _agendar(e):
        data = f_data.value.strip()
        if not data:
            txt_alarme.value = "Informe a data primeiro."
            try: page.update()
            except Exception: pass
            return
        hora = f_hora.value.strip() or "08:00"
        med_nome = med_map.get(med_id_sel[0], "") if med_id_sel[0] else ""
        desc = med_nome or "Consulta médica"
        ok, info = _agendar_alarme_windows(data, hora, desc)
        txt_alarme.value = (f"Alarme: {data} as {hora}" if ok
                            else f"Erro no alarme: {info}")
        txt_alarme.color = VERD if ok else LAR
        try: page.update()
        except Exception: pass

    btn_agendar_alarme.on_click = _agendar

    def _salvar(e):
        if not f_data.value.strip():
            txt_erro.value = "Data é obrigatória."
            try: page.update()
            except Exception: pass
            return
        salvar_consulta({
            "id":          consulta["id"] if consulta else None,
            "medico_id":   int(med_id_sel[0]) if med_id_sel[0] else None,
            "data":        _norm_data(f_data.value.strip()),
            "hora":        f_hora.value.strip() or None,
            "tipo":        tipo_sel[0],
            "local":       f_local.value.strip() or None,
            "observacoes": f_obs.value.strip() or None,
            "pauta":       pauta_itens,
        })
        _status_banco[0] = "em_edicao"
        _sync(voltar_fn)

    def _ativar_edicao(e=None):
        _modo_edicao[0] = True
        for _f in [f_hora, f_local, f_obs]:
            _f.read_only = False
        f_data.read_only = False
        # reativa médico
        col_medico._tf_medico.visible   = not bool(med_id_sel[0])
        col_medico._chip_medico.on_click = col_medico._limpar_fn
        # reativa pauta
        row_nova_pauta.visible = True
        _rebuild_pauta()
        btn_salvar_hdr.visible = True
        btn_editar.visible = False
        try: page.update()
        except Exception: pass

    _rebuild_chips()

    btn_salvar_hdr = ft.Container(
        content=ft.Row([
            ft.Icon("save_rounded", size=15, color=AZUL),
            ft.Text("Salvar", size=13, color=AZUL),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        border_radius=8, ink=True, visible=is_novo,
    )
    btn_salvar_hdr.on_click = _salvar

    btn_editar = ft.Container(
        content=ft.Row([
            ft.Icon("edit_rounded", size=15, color=AZUL),
            ft.Text("Editar", size=13, color=AZUL),
        ], spacing=5, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=8, bgcolor=ft.Colors.with_opacity(0.12, AZUL), ink=True,
        visible=not is_novo,
    )
    btn_editar.on_click = _ativar_edicao

    cabecalho = ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Row([
                    ft.Icon("arrow_back_rounded", size=16),
                    ft.Text("Voltar", size=13),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                ink=True,
                on_click=lambda e: _sair(voltar_fn),
            ),
            ft.Row([
                ft.Icon("event_note_rounded", size=18, color=AZUL),
                ft.Text(titulo, size=18, weight=ft.FontWeight.W_700, color=TXT),
            ], spacing=8, tight=True),
            ft.Container(expand=True),
            btn_editar,
            btn_salvar_hdr,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=16, vertical=14),
        border=ft.Border(bottom=ft.BorderSide(1, BD)),
    )

    corpo = ft.Column([
        cabecalho,
        ft.Container(
            content=ft.Column([
                col_medico,
                ft.Container(height=4),
                _label_sec("DATA E HORA"),
                ft.Row([row_data, f_hora], spacing=8),
                ft.Container(height=4),
                _label_sec("STATUS"),
                chips_row,
                ft.Container(height=4),
                _label_sec("LOCAL"),
                f_local,
                ft.Container(height=4),
                _label_sec("ITENS A TRATAR"),
                row_nova_pauta,
                pauta_col,
                ft.Container(height=4),
                _label_sec("OBSERVAÇÕES"),
                f_obs,
                ft.Container(height=8),
                btn_agendar_alarme,
                txt_alarme,
                txt_erro,
                ft.Container(height=20),
            ], spacing=8, scroll=ft.ScrollMode.AUTO),
            padding=ft.padding.all(16),
            expand=True,
        ),
    ], expand=True, spacing=0)

    _registrar_voltar_hw()
    return _centralizar(corpo, page)


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL
# ══════════════════════════════════════════════════════════════

def criar_tela_consultas_medicas(page: ft.Page, voltar_fn):
    from shared.layout import Layout
    lay     = Layout(page)
    medicos = listar_medicos(so_ativos=True)

    ABAS = [
        (0, "event_note_rounded",         "Consultas",  AZUL),
        (1, "calendar_today_rounded",     "Agendadas",  AZUL),
        (2, "check_circle_outline_rounded", "Realizadas", VERD),
        (3, "cancel_outlined_rounded",    "Canceladas", MUT),
    ]
    FILTROS = [None, "agendada", "realizada", "cancelada"]
    aba_ativa = [0]

    barra_abas    = ft.Row(spacing=0)
    area_conteudo = ft.Column(spacing=8, expand=True, scroll=ft.ScrollMode.AUTO)
    wrapper       = ft.Column(expand=True, spacing=0)

    lista = ft.Column(spacing=8)

    def _rebuild_abas():
        barra_abas.controls.clear()
        for idx, icone, label, cor in ABAS:
            ativo = idx == aba_ativa[0]
            def _click(e, i=idx):
                aba_ativa[0] = i
                _rebuild_abas()
                _carregar()
                _rebuild_conteudo()
            barra_abas.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon(icone, size=16, color=cor if ativo else SEC),
                    ft.Text(label, size=10,
                            color=cor if ativo else SEC,
                            weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.W_400),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=2, tight=True),
                expand=True,
                padding=ft.padding.symmetric(vertical=10),
                border=ft.Border(bottom=ft.BorderSide(2, cor if ativo else "#00000000")),
                on_click=_click,
            ))
        try: page.update()
        except Exception: pass

    hoje = datetime.date.today()

    def _carregar():
        lista.controls.clear()
        filtro = FILTROS[aba_ativa[0]]
        consultas = listar_consultas(filtro)

        if not consultas:
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("event_busy_rounded", size=40, color=MUT),
                    ft.Text("Nenhuma consulta cadastrada.", color=SEC, size=13),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=40, alignment=ft.alignment.Alignment(0, 0),
            ))
            try: page.update()
            except Exception: pass
            return

        for c in consultas:
            cor_tipo, icone_tipo = CORES_TIPO.get(
                c["tipo"], (SEC, "help_outline_rounded"))

            info_data = ""
            try:
                _dt = _flex_parse(c["data"])
                dt = _dt.date() if _dt else None
                if dt is None:
                    raise ValueError("data invalida")
                delta = (dt - hoje).days
                if c["tipo"] == "agendada":
                    if delta == 0:   info_data = "Hoje!"
                    elif delta == 1: info_data = "Amanhã"
                    elif delta > 0:  info_data = f"Em {delta} dias"
                    else:            info_data = f"Há {abs(delta)} dias"
            except Exception:
                pass

            def _make_ficha(cons):
                def _click(e): _abrir_ficha(cons)
                return _click

            def _make_rec(cons):
                def _click(e): _abrir_receitas(cons)
                return _click

            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            content=ft.Icon(icone_tipo, size=20, color=cor_tipo),
                            bgcolor=f"{cor_tipo}18", border_radius=10,
                            width=40, height=40,
                            alignment=ft.alignment.Alignment(0, 0)),
                        ft.Column([
                            ft.Text(c.get("medico") or "Médico não informado",
                                    size=14, color=TXT, weight=ft.FontWeight.W_600),
                            ft.Text(c.get("especialidade") or "",
                                    size=11, color=ROXO),
                        ], spacing=1, expand=True),
                        _badge(c["tipo"]),
                    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row([
                        ft.Icon("calendar_today_rounded", size=12, color=MUT),
                        ft.Text(f"{c['data']}  {c.get('hora') or ''}", size=12, color=SEC),
                        ft.Container(expand=True),
                        ft.Text(info_data, size=11,
                                color=AMAR if info_data in ("Hoje!", "Amanhã") else MUT),
                    ], spacing=6),
                    ft.Row([
                        ft.Icon("location_on_outlined_rounded", size=12, color=MUT),
                        ft.Text(c.get("local") or "Local não informado",
                                size=11, color=SEC, expand=True),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon("receipt_long_rounded", size=13, color=ROXO),
                                ft.Text("Receitas", size=11, color=ROXO),
                            ], spacing=4, tight=True),
                            padding=ft.padding.symmetric(horizontal=8, vertical=8),
                            ink=True,
                            on_click=_make_rec(c),
                        ),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon("edit_rounded", size=13, color=MUT),
                                ft.Text("Editar", size=11, color=MUT),
                            ], spacing=4, tight=True),
                            padding=ft.padding.symmetric(horizontal=8, vertical=8),
                            ink=True,
                            on_click=_make_ficha(c),
                        ),
                    ], spacing=4),
                ], spacing=8),
                bgcolor=CARD, border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                border=ft.Border(
                    left=ft.BorderSide(2, cor_tipo),
                    top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                    right=ft.BorderSide(1, BD),
                ),
            ))
        try: page.update()
        except Exception: pass

    def _rebuild_conteudo():
        area_conteudo.controls.clear()
        area_conteudo.controls.append(lista)
        try: page.update()
        except Exception: pass

    def _abrir_ficha(consulta):
        def _voltar():
            _carregar()
            _mostrar_principal()
        wrapper.controls.clear()
        wrapper.controls.append(
            _tela_ficha_consulta(page, consulta, _voltar, medicos))
        try: page.update()
        except Exception: pass

    def _abrir_receitas(consulta):
        def _voltar():
            _carregar()
            _mostrar_principal()
        wrapper.controls.clear()
        wrapper.controls.append(_tela_receita(page, consulta, _voltar))
        try: page.update()
        except Exception: pass

    def _mostrar_principal():
        btn_nova = ft.Container(
            content=ft.Row([
                ft.Icon("add_rounded", size=16, color=BG),
                ft.Text("+ Nova", size=13, color=BG, weight=ft.FontWeight.W_600),
            ], spacing=6, tight=True),
            bgcolor=AZUL, border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            ink=True,
        )
        btn_nova.on_click = lambda e: _abrir_ficha(None)

        cabecalho = lay.criar_cabecalho(
            "Consultas", voltar_fn,
            icone_titulo="event_note_rounded",
            cor_titulo=AZUL,
            acoes=[btn_nova],
        )

        corpo = ft.Column([
            ft.Container(height=lay.spacer_topo, bgcolor=BG),
            cabecalho,
            ft.Container(content=barra_abas,
                         border=ft.Border(bottom=ft.BorderSide(1, BD))),
            ft.Container(
                content=area_conteudo,
                padding=ft.padding.all(16),
                expand=True,
            ),
        ], expand=True, spacing=0)

        wrapper.controls.clear()
        wrapper.controls.append(
            ft.Container(bgcolor=BG, expand=True, content=corpo))
        try: page.update()
        except Exception: pass

    _rebuild_abas()
    _carregar()
    _rebuild_conteudo()
    _mostrar_principal()

    return wrapper
