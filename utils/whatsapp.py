# -*- coding: utf-8 -*-
# Prestanista v1.0 | gerado: 2026-03-13 | utils/whatsapp.py
import urllib.parse
from database.model import get_config, registrar_msg_wa
from app_log import debug, erro

TEMPLATES = {
    "lembrete": (
        "Olá {nome}! Lembrando que sua parcela {n} de {valor} vence em {data}. "
        "Qualquer dúvida estou à disposição!"
    ),
    "cobranca": (
        "Olá {nome}, a parcela {n} de {valor} venceu em {data} e ainda está em aberto. "
        "Podemos acertar hoje?"
    ),
    "confirmacao": (
        "{nome}, recebi sua parcela {n} de {valor} com sucesso! Obrigado."
    ),
    "carne": (
        "Olá {nome}! Segue o carnê das suas parcelas. Qualquer dúvida pode me chamar!"
    ),
}


def _limpar_telefone(tel: str) -> str:
    return "".join(c for c in tel if c.isdigit())


def montar_url(telefone: str, texto: str) -> str:
    tel = _limpar_telefone(telefone)
    if not tel.startswith("55"):
        tel = "55" + tel
    texto_enc = urllib.parse.quote(texto)
    return f"https://wa.me/{tel}?text={texto_enc}"


def montar_mensagem(tipo: str, **kwargs) -> str:
    tpl = TEMPLATES.get(tipo, TEMPLATES["lembrete"])
    return tpl.format(**{k: kwargs.get(k, "") for k in ("nome","n","valor","data")})


def abrir_whatsapp(page, cliente_id: int, telefone: str, tipo: str, texto: str):
    """Abre o WhatsApp com a mensagem pré-preenchida e registra no histórico."""
    try:
        url = montar_url(telefone, texto)
        debug("whatsapp", f"abrir_whatsapp cliente={cliente_id} tipo={tipo}")
        page.launch_url(url)
        registrar_msg_wa(cliente_id, tipo, texto)
    except Exception as ex:
        erro("whatsapp", "abrir_whatsapp", ex)
