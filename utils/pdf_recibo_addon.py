# -*- coding: utf-8 -*-
# Prestanista v1.0 | gerado: 2026-03-17 | utils/pdf_recibo_addon.py
"""
Função para adicionar ao utils/pdf_documentos.py

Cole ao final do arquivo pdf_documentos.py.
"""


def gerar_recibo_pagamento_58mm(
    parcela_id: int,
    parcela_num: int,
    total_parcelas: int,
    valor_pago: float,
    data_pgto: str,
    cliente_nome: str,
    venda_id: int,
    nome_negocio: str = "Prestanista",
    vendedor_nome: str = "",
    assinatura_vendedor_path: Optional[str] = None,
) -> Optional[str]:
    """
    Gera recibo de pagamento de parcela otimizado para papel térmico 58mm.
    Assinado pelo vendedor (prestanista).

    Returns:
        Caminho absoluto do PDF gerado, ou None em erro.
    """
    try:
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib import colors

        os.makedirs(_DOCS, exist_ok=True)
        nome_arquivo = f"recibo_venda{venda_id}_p{parcela_num}.pdf"
        caminho      = os.path.join(_DOCS, nome_arquivo)

        alt = 190.0
        c   = rl_canvas.Canvas(caminho, pagesize=(_LARG_58MM, alt))
        c.setTitle(f"Recibo — {cliente_nome}")

        y = alt - 8

        #  Cabealho 
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#0D1117"))
        c.drawCentredString(_LARG_58MM / 2, y, nome_negocio.upper())
        y -= 11

        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.HexColor("#0D1117"))
        c.drawCentredString(_LARG_58MM / 2, y, "RECIBO DE PAGAMENTO")
        y -= 8

        _linha_tracejada(c, y, _LARG_58MM, _MARGEM_58)
        y -= 8

        #  Valor 
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.HexColor("#238636"))
        c.drawCentredString(_LARG_58MM / 2, y, _fmt_moeda(valor_pago))
        y -= 12

        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#484F58"))
        c.drawCentredString(
            _LARG_58MM / 2, y,
            f"({_valor_por_extenso(valor_pago)})"[:38],
        )
        y -= 12

        #  Dados 
        itens = [
            ("Parcela:",   f"{parcela_num}/{total_parcelas}"),
            ("Cliente:",   cliente_nome[:26]),
            ("Venda:",     f"#{venda_id:05d}"),
            ("Data:",      data_pgto),
        ]
        for label, valor_item in itens:
            c.setFont("Helvetica-Bold", 7)
            c.setFillColor(colors.HexColor("#484F58"))
            c.drawString(_MARGEM_58, y, label)
            c.setFont("Helvetica", 7)
            c.setFillColor(colors.HexColor("#0D1117"))
            c.drawString(_MARGEM_58 + 36, y, str(valor_item))
            y -= 10

        y -= 4
        _linha_tracejada(c, y, _LARG_58MM, _MARGEM_58)
        y -= 10

        #  Assinatura do vendedor 
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#484F58"))
        c.drawCentredString(_LARG_58MM / 2, y, "Recebido por:")
        y -= 4

        sig_alt = 35
        if assinatura_vendedor_path:
            try:
                abs_sig = os.path.join(_ASSETS, assinatura_vendedor_path.lstrip("/"))
                if os.path.exists(abs_sig) and os.path.getsize(abs_sig) > 0:
                    sig_larg = _UTIL_58 * 0.75
                    sig_x    = (_LARG_58MM - sig_larg) / 2
                    c.drawImage(
                        abs_sig, sig_x, y - sig_alt,
                        sig_larg, sig_alt,
                        preserveAspectRatio=True, mask="auto",
                    )
            except Exception as exc:
                log.warning("[PDF] Assinatura recibo: %s", exc)
        else:
            # Linha vazia
            c.setStrokeColor(colors.HexColor("#21262D"))
            c.setLineWidth(0.5)
            x0 = _MARGEM_58 + 10
            c.line(x0, y - sig_alt + 10, _LARG_58MM - _MARGEM_58 - 10, y - sig_alt + 10)

        y -= sig_alt + 4

        # Nome do vendedor
        c.setFont("Helvetica", 6)
        c.setFillColor(colors.HexColor("#484F58"))
        nome_exib = vendedor_nome[:30] if vendedor_nome else nome_negocio[:30]
        c.drawCentredString(_LARG_58MM / 2, y, nome_exib)
        y -= 8

        c.setFont("Helvetica", 6)
        c.drawCentredString(_LARG_58MM / 2, y, "Vendedor / Prestanista")

        c.save()
        log.info("[PDF] Recibo gerado: %s", caminho)
        return caminho

    except Exception as exc:
        log.exception("[PDF] Erro ao gerar recibo: %s", exc)
        return None
