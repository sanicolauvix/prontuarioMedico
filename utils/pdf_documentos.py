# -*- coding: utf-8 -*-
# Prestanista v1.0 | gerado: 2026-03-16 | utils/pdf_documentos.py
"""
utils/pdf_documentos.py
Geração de PDF para documentos de venda:
  - Carnê completo (todas as parcelas, otimizado para 58mm térmico)
  - Promissória individual (padrão Lei 7.357, com assinatura digital)

Formatos suportados:
  - 58mm térmico  (largura ~162pt, altura variável)
  - A4 padrão     (595 x 842pt)

Dependências:
    pip install reportlab pillow
"""

import logging
import os
from typing import Optional

log = logging.getLogger(__name__)

_HERE    = os.path.dirname(os.path.abspath(__file__))
_ROOT    = os.path.dirname(_HERE)
_DOCS    = os.path.join(_ROOT, "docs")
_ASSETS  = os.path.join(_ROOT, "assets")

# Largura do papel 58mm em pontos (1mm  2.835pt)
_LARG_58MM  = 162.0   # pt
_MARGEM_58  = 8.0     # pt

# Largura til
_UTIL_58    = _LARG_58MM - _MARGEM_58 * 2


def _fmt_moeda(v) -> str:
    try:
        return f"R$ {float(v or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def _valor_por_extenso(valor: float) -> str:
    """Converte valor numérico para extenso em português (até milhões)."""
    try:
        import math
        if valor <= 0:
            return "zero reais"

        centavos = round((valor % 1) * 100)
        reais    = int(valor)

        unidades  = ["", "um", "dois", "três", "quatro", "cinco",
                     "seis", "sete", "oito", "nove", "dez",
                     "onze", "doze", "treze", "quatorze", "quinze",
                     "dezesseis", "dezessete", "dezoito", "dezenove"]
        dezenas   = ["", "", "vinte", "trinta", "quarenta", "cinquenta",
                     "sessenta", "setenta", "oitenta", "noventa"]
        centenas  = ["", "cento", "duzentos", "trezentos", "quatrocentos",
                     "quinhentos", "seiscentos", "setecentos", "oitocentos", "novecentos"]

        def _grupo(n: int) -> str:
            if n == 0:
                return ""
            if n == 100:
                return "cem"
            c = n // 100
            d = (n % 100) // 10
            u = n % 10
            partes = []
            if c:
                partes.append(centenas[c])
            if d >= 2:
                partes.append(dezenas[d])
                if u:
                    partes.append(unidades[u])
            elif (d * 10 + u) > 0:
                partes.append(unidades[d * 10 + u])
            return " e ".join(partes)

        partes = []
        if reais >= 1_000_000:
            m = reais // 1_000_000
            partes.append(f"{_grupo(m)} {'milhão' if m == 1 else 'milhões'}")
            reais %= 1_000_000
        if reais >= 1_000:
            m = reais // 1_000
            partes.append(f"{_grupo(m)} mil")
            reais %= 1_000
        if reais > 0:
            g = _grupo(reais)
            if g:
                partes.append(f"{g} {'real' if reais == 1 else 'reais'}")

        extenso = " e ".join(partes) if partes else "zero reais"

        if centavos > 0:
            ext_cent = f"{_grupo(centavos)} {'centavo' if centavos == 1 else 'centavos'}"
            extenso  = f"{extenso} e {ext_cent}" if partes else ext_cent

        return extenso.capitalize()

    except Exception as exc:
        log.warning("[PDF] valor_por_extenso: %s", exc)
        return f"{valor:.2f}".replace(".", ",")


def _linha_tracejada(canvas, y: float, larg: float, margem: float) -> None:
    """Desenha linha tracejada de corte."""
    from reportlab.lib import colors
    canvas.setDash(3, 3)
    canvas.setStrokeColor(colors.HexColor("#484F58"))
    canvas.setLineWidth(0.5)
    canvas.line(margem, y, larg - margem, y)
    canvas.setDash()


def _logo_ou_nome(canvas, nome_negocio: str, larg: float, y: float,
                  margem: float, fonte: str = "Helvetica-Bold",
                  tamanho: int = 9) -> float:
    """Escreve nome do negócio centrado. Retorna y após o texto."""
    from reportlab.lib import colors
    canvas.setFont(fonte, tamanho)
    canvas.setFillColor(colors.HexColor("#E6EDF3"))
    canvas.drawCentredString(larg / 2, y, nome_negocio.upper())
    return y - tamanho - 4


# 
# CARN 58mm
# 

def gerar_carne_58mm(
    venda_id: int,
    cliente_nome: str,
    parcelas: list[dict],
    nome_negocio: str = "Prestanista",
    vendedor_nome: str = "",
    assinatura_path: Optional[str] = None,
) -> Optional[str]:
    """
    Gera carnê com todas as parcelas otimizado para papel térmico 58mm.

    Cada parcela = um cupom separado por linha tracejada de corte.

    parcelas: lista de dicts com chaves:
        numero, total_parcelas, valor, vencimento, status

    Returns:
        Caminho absoluto do PDF gerado, ou None em erro.
    """
    try:
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib import colors
        from reportlab.lib.units import mm

        os.makedirs(_DOCS, exist_ok=True)
        nome_arquivo = f"carne_venda_{venda_id}.pdf"
        caminho      = os.path.join(_DOCS, nome_arquivo)

        # Altura: cada parcela ~90pt + 10pt separador
        alt_parcela = 95.0
        alt_total   = alt_parcela * len(parcelas) + 20

        c = rl_canvas.Canvas(caminho, pagesize=(_LARG_58MM, alt_total))
        c.setTitle(f"Carnê — {cliente_nome}")

        y = alt_total - 10

        for i, parc in enumerate(parcelas):
            y_inicio = y

            # Cabealho do cupom
            y = _logo_ou_nome(c, nome_negocio, _LARG_58MM, y, _MARGEM_58, tamanho=8)

            # Nmero da parcela
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(colors.HexColor("#58A6FF"))
            c.drawCentredString(
                _LARG_58MM / 2, y,
                f"PARCELA {parc['numero']}/{parc['total_parcelas']}"
            )
            y -= 14

            # Valor
            c.setFont("Helvetica-Bold", 14)
            c.setFillColor(colors.HexColor("#3FB950"))
            c.drawCentredString(_LARG_58MM / 2, y, _fmt_moeda(parc["valor"]))
            y -= 16

            # Vencimento
            c.setFont("Helvetica", 8)
            c.setFillColor(colors.HexColor("#E6EDF3"))
            c.drawCentredString(_LARG_58MM / 2, y, f"Vence: {parc['vencimento']}")
            y -= 11

            # Cliente
            c.setFont("Helvetica", 7)
            c.setFillColor(colors.HexColor("#8B949E"))
            # Trunca nome se muito longo para 58mm
            nome_exib = cliente_nome[:28] + "..." if len(cliente_nome) > 28 else cliente_nome
            c.drawCentredString(_LARG_58MM / 2, y, nome_exib)
            y -= 11

            # Assinatura (s na primeira parcela)
            if i == 0 and assinatura_path:
                try:
                    abs_sig = os.path.join(_ASSETS, assinatura_path.lstrip("/"))
                    if os.path.exists(abs_sig) and os.path.getsize(abs_sig) > 0:
                        sig_larg = min(80, _UTIL_58)
                        sig_alt  = 20
                        sig_x    = (_LARG_58MM - sig_larg) / 2
                        c.drawImage(abs_sig, sig_x, y - sig_alt,
                                    sig_larg, sig_alt,
                                    preserveAspectRatio=True, mask="auto")
                        y -= sig_alt + 2
                        c.setFont("Helvetica", 6)
                        c.setFillColor(colors.HexColor("#484F58"))
                        c.drawCentredString(_LARG_58MM / 2, y, "Assinatura do cliente")
                        y -= 8
                except Exception as exc:
                    log.warning("[PDF] Erro ao incluir assinatura no carnê: %s", exc)

            y -= 4

            # Linha de corte (exceto aps ltima parcela)
            if i < len(parcelas) - 1:
                _linha_tracejada(c, y, _LARG_58MM, _MARGEM_58)
                c.setFont("Helvetica", 5)
                c.setFillColor(colors.HexColor("#484F58"))
                c.drawCentredString(_LARG_58MM / 2, y - 5, "✂ RECORTE AQUI ✂")
                y -= 14

        c.save()
        log.info("[PDF] Carnê gerado: %s", caminho)
        return caminho

    except Exception as exc:
        log.exception("[PDF] Erro ao gerar carnê: %s", exc)
        return None


# 
# PROMISSRIA  A4 (padro Lei 7.357)
# 

def gerar_promissoria_a4(
    venda_id: int,
    parcela_num: int,
    valor: float,
    vencimento: str,
    cliente_nome: str,
    cliente_cpf: str,
    cliente_endereco: str,
    credor_nome: str,
    credor_cpf_cnpj: str,
    cidade: str,
    data_emissao: str,
    assinatura_path: Optional[str] = None,
) -> Optional[str]:
    """
    Gera promissória no padrão brasileiro (Lei 7.357).
    Formato A4 com campo de assinatura digital.

    Returns:
        Caminho absoluto do PDF gerado, ou None em erro.
    """
    try:
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm

        os.makedirs(_DOCS, exist_ok=True)
        nome_arquivo = f"promissoria_venda_{venda_id}_parc{parcela_num}.pdf"
        caminho      = os.path.join(_DOCS, nome_arquivo)

        LARG, ALT = A4
        c = rl_canvas.Canvas(caminho, pagesize=A4)
        c.setTitle(f"Promissória — {cliente_nome} — Parcela {parcela_num}")

        mg   = 2 * cm
        util = LARG - mg * 2

        #  Borda externa 
        c.setStrokeColor(colors.HexColor("#30363D"))
        c.setLineWidth(1)
        c.rect(mg - 4, mg - 4, util + 8, ALT - mg * 2 + 8)

        y = ALT - mg - 10

        #  Cabealho 
        c.setFont("Helvetica-Bold", 18)
        c.setFillColor(colors.HexColor("#0D1117"))
        c.drawCentredString(LARG / 2, y, "NOTA PROMISSÓRIA")
        y -= 6

        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#484F58"))
        c.drawCentredString(LARG / 2, y, f"Nº {venda_id:05d}-{parcela_num:02d}")
        y -= 20

        #  Linha divisria 
        c.setStrokeColor(colors.HexColor("#21262D"))
        c.setLineWidth(0.5)
        c.line(mg, y, LARG - mg, y)
        y -= 16

        #  Valor em destaque 
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.HexColor("#0D1117"))
        c.drawString(mg, y, "Valor:")
        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(colors.HexColor("#238636"))
        c.drawString(mg + 50, y, _fmt_moeda(valor))

        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#484F58"))
        c.drawRightString(LARG - mg, y, f"Vencimento: {vencimento}")
        y -= 20

        #  Valor por extenso 
        extenso = _valor_por_extenso(valor)
        c.setFont("Helvetica-Oblique", 10)
        c.setFillColor(colors.HexColor("#21262D"))
        c.drawString(mg, y, f"({extenso})")
        y -= 24

        #  Linha divisria 
        c.setStrokeColor(colors.HexColor("#21262D"))
        c.line(mg, y, LARG - mg, y)
        y -= 18

        #  Corpo do texto legal 
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.HexColor("#0D1117"))
        c.drawString(mg, y, "AO(S) PORTADOR(ES):")
        y -= 14

        c.setFont("Helvetica", 10)
        c.setFillColor(colors.HexColor("#0D1117"))

        texto_principal = (
            f"No dia {vencimento}, pagarei por esta única via de NOTA PROMISSÓRIA "
            f"a {credor_nome} (CPF/CNPJ: {credor_cpf_cnpj}), ou à sua ordem, "
            f"a importância de {_fmt_moeda(valor)} ({extenso}), "
            f"em moeda corrente deste País."
        )

        # Quebra de linha manual para caber na largura
        _escrever_paragrafo(c, texto_principal, mg, y, util, 10, "#0D1117")
        y -= _altura_paragrafo(texto_principal, util, 10) + 10

        c.setFont("Helvetica", 10)
        c.setFillColor(colors.HexColor("#0D1117"))
        texto_cond = (
            f"Esta nota promissória refere-se à PARCELA {parcela_num} "
            f"da venda Nº {venda_id:05d}, realizada em {data_emissao}."
        )
        _escrever_paragrafo(c, texto_cond, mg, y, util, 10, "#0D1117")
        y -= _altura_paragrafo(texto_cond, util, 10) + 20

        #  Dados do devedor 
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.HexColor("#0D1117"))
        c.drawString(mg, y, "EMITENTE (DEVEDOR):")
        y -= 14

        _campo(c, mg, y, util * 0.6, "Nome:", cliente_nome)
        _campo(c, mg + util * 0.62, y, util * 0.36, "CPF:", cliente_cpf)
        y -= 28

        _campo(c, mg, y, util, "Endereço:", cliente_endereco)
        y -= 28

        #  Local e data 
        _campo(c, mg, y, util * 0.45, "Local de emissão:", cidade)
        _campo(c, mg + util * 0.47, y, util * 0.51, "Data de emissão:", data_emissao)
        y -= 40

        #  Linha divisria 
        c.setStrokeColor(colors.HexColor("#21262D"))
        c.line(mg, y, LARG - mg, y)
        y -= 30

        #  Campo de assinatura 
        sig_larg = util * 0.55
        sig_alt  = 70
        sig_x    = (LARG - sig_larg) / 2
        sig_y    = y - sig_alt

        # Caixa de assinatura
        c.setStrokeColor(colors.HexColor("#30363D"))
        c.setLineWidth(0.5)
        c.rect(sig_x, sig_y, sig_larg, sig_alt)

        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#8B949E"))
        c.drawCentredString(LARG / 2, sig_y - 12, "Assinatura do Emitente")
        c.drawCentredString(LARG / 2, sig_y - 22, cliente_nome)

        # Imagem da assinatura digital
        if assinatura_path:
            try:
                abs_sig = os.path.join(_ASSETS, assinatura_path.lstrip("/"))
                if os.path.exists(abs_sig) and os.path.getsize(abs_sig) > 0:
                    c.drawImage(
                        abs_sig,
                        sig_x + 10, sig_y + 5,
                        sig_larg - 20, sig_alt - 10,
                        preserveAspectRatio=True,
                        mask="auto",
                    )
            except Exception as exc:
                log.warning("[PDF] Erro ao inserir assinatura: %s", exc)

        y = sig_y - 40

        #  Rodap 
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#484F58"))
        c.drawCentredString(
            LARG / 2, mg,
            "Documento gerado pelo Prestanista — Gestão de Crediário Próprio"
        )

        c.save()
        log.info("[PDF] Promissória gerada: %s", caminho)
        return caminho

    except Exception as exc:
        log.exception("[PDF] Erro ao gerar promissória: %s", exc)
        return None


# 
# PROMISSRIA 58mm (verso compacta para impressora porttil)
# 

def gerar_promissoria_58mm(
    venda_id: int,
    parcela_num: int,
    valor: float,
    vencimento: str,
    cliente_nome: str,
    credor_nome: str,
    cidade: str,
    data_emissao: str,
    assinatura_path: Optional[str] = None,
) -> Optional[str]:
    """
    Versão compacta da promissória para papel térmico 58mm.
    Inclui todos os campos essenciais em formato vertical.
    """
    try:
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib import colors

        os.makedirs(_DOCS, exist_ok=True)
        nome_arquivo = f"promissoria_58_venda_{venda_id}_parc{parcela_num}.pdf"
        caminho      = os.path.join(_DOCS, nome_arquivo)

        extenso = _valor_por_extenso(valor)
        alt = 220 + (len(extenso) // 30) * 10

        c = rl_canvas.Canvas(caminho, pagesize=(_LARG_58MM, float(alt)))
        c.setTitle(f"Promissória — Parcela {parcela_num}")

        y = float(alt) - 8

        # Ttulo
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#0D1117"))
        c.drawCentredString(_LARG_58MM / 2, y, "NOTA PROMISSÓRIA")
        y -= 12

        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#484F58"))
        c.drawCentredString(_LARG_58MM / 2, y, f"Nº {venda_id:05d}-{parcela_num:02d}")
        y -= 10

        _linha_tracejada(c, y, _LARG_58MM, _MARGEM_58)
        y -= 8

        # Valor
        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(colors.HexColor("#238636"))
        c.drawCentredString(_LARG_58MM / 2, y, _fmt_moeda(valor))
        y -= 11

        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#0D1117"))
        # Extenso em at 2 linhas de 28 chars
        linhas_ext = _quebrar_texto(extenso, 28)
        for linha in linhas_ext[:2]:
            c.drawCentredString(_LARG_58MM / 2, y, f"({linha})")
            y -= 9
        y -= 4

        # Dados
        itens = [
            ("Vencimento:", vencimento),
            ("Devedor:", cliente_nome[:26]),
            ("Credor:", credor_nome[:26]),
            ("Emissão:", f"{cidade[:14]}, {data_emissao}"),
            ("Referente:", f"Parcela {parcela_num} — Venda {venda_id:05d}"),
        ]
        for label, valor_item in itens:
            c.setFont("Helvetica-Bold", 7)
            c.setFillColor(colors.HexColor("#484F58"))
            c.drawString(_MARGEM_58, y, label)
            c.setFont("Helvetica", 7)
            c.setFillColor(colors.HexColor("#0D1117"))
            c.drawString(_MARGEM_58 + 40, y, valor_item)
            y -= 10

        y -= 6
        _linha_tracejada(c, y, _LARG_58MM, _MARGEM_58)
        y -= 10

        # Assinatura
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#484F58"))
        c.drawCentredString(_LARG_58MM / 2, y, "Assinatura do devedor:")
        y -= 4

        sig_alt = 35
        if assinatura_path:
            try:
                abs_sig = os.path.join(_ASSETS, assinatura_path.lstrip("/"))
                if os.path.exists(abs_sig) and os.path.getsize(abs_sig) > 0:
                    sig_larg = _UTIL_58 * 0.8
                    sig_x    = (_LARG_58MM - sig_larg) / 2
                    c.drawImage(abs_sig, sig_x, y - sig_alt,
                                sig_larg, sig_alt,
                                preserveAspectRatio=True, mask="auto")
            except Exception as exc:
                log.warning("[PDF] Assinatura 58mm: %s", exc)
        else:
            # Linha de assinatura vazia
            c.setStrokeColor(colors.HexColor("#21262D"))
            c.setLineWidth(0.5)
            x0 = _MARGEM_58 + 10
            y_sig = y - sig_alt + 10
            c.line(x0, y_sig, _LARG_58MM - _MARGEM_58 - 10, y_sig)

        y -= sig_alt + 6
        c.setFont("Helvetica", 6)
        c.setFillColor(colors.HexColor("#484F58"))
        c.drawCentredString(_LARG_58MM / 2, y, cliente_nome[:30])

        c.save()
        log.info("[PDF] Promissória 58mm gerada: %s", caminho)
        return caminho

    except Exception as exc:
        log.exception("[PDF] Erro ao gerar promissória 58mm: %s", exc)
        return None


#  Helpers de texto 

def _quebrar_texto(texto: str, largura_chars: int) -> list[str]:
    """Quebra texto em linhas com no máximo largura_chars caracteres."""
    palavras = texto.split()
    linhas, atual = [], ""
    for palavra in palavras:
        if len(atual) + len(palavra) + 1 <= largura_chars:
            atual = (atual + " " + palavra).strip()
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def _escrever_paragrafo(canvas, texto: str, x: float, y: float,
                        larg: float, tamanho: int, cor: str) -> None:
    """Escreve parágrafo com quebra de linha automática."""
    from reportlab.lib import colors as rl_colors
    chars_por_linha = int(larg / (tamanho * 0.55))
    linhas = _quebrar_texto(texto, chars_por_linha)
    canvas.setFont("Helvetica", tamanho)
    canvas.setFillColor(rl_colors.HexColor(cor))
    for linha in linhas:
        canvas.drawString(x, y, linha)
        y -= tamanho + 2


def _altura_paragrafo(texto: str, larg: float, tamanho: int) -> float:
    chars_por_linha = int(larg / (tamanho * 0.55))
    linhas = _quebrar_texto(texto, chars_por_linha)
    return len(linhas) * (tamanho + 2)


def _campo(canvas, x: float, y: float, larg: float,
           label: str, valor: str) -> None:
    """Desenha campo com label e valor, com linha inferior."""
    from reportlab.lib import colors as rl_colors
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(rl_colors.HexColor("#484F58"))
    canvas.drawString(x, y, label)

    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(rl_colors.HexColor("#0D1117"))
    canvas.drawString(x + len(label) * 5.5 + 2, y, valor)

    canvas.setStrokeColor(rl_colors.HexColor("#30363D"))
    canvas.setLineWidth(0.3)
    canvas.line(x, y - 3, x + larg, y - 3)
