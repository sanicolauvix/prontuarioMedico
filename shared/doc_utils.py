# -*- coding: utf-8 -*-
# SHARED | shared/doc_utils.py -- gerenciado por flet_shared/sync_shared.py
"""Validacao e formatacao de CPF e CNPJ.

Funcoes puras, sem dependencia de Flet. Importar em qualquer tela.
"""


# ── Formatacao (mascara ao digitar) ───────────────────────────────────────────

def fmt_cpf_cnpj(v: str) -> str:
    """Aplica mascara CPF (000.000.000-00) ou CNPJ (00.000.000/0000-00) conforme
    o comprimento. Usado no on_change do campo."""
    n = "".join(c for c in v if c.isdigit())
    if len(n) <= 11:
        n = n[:11]
        if len(n) > 9:  return f"{n[:3]}.{n[3:6]}.{n[6:9]}-{n[9:]}"
        if len(n) > 6:  return f"{n[:3]}.{n[3:6]}.{n[6:]}"
        if len(n) > 3:  return f"{n[:3]}.{n[3:]}"
        return n
    else:
        n = n[:14]
        if len(n) > 12: return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:]}"
        if len(n) > 8:  return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:]}"
        if len(n) > 5:  return f"{n[:2]}.{n[2:5]}.{n[5:]}"
        if len(n) > 2:  return f"{n[:2]}.{n[2:]}"
        return n


# ── Validacao CPF ─────────────────────────────────────────────────────────────

def validar_cpf(v: str) -> bool:
    """Retorna True se o CPF for valido (digitos verificadores corretos).
    Aceita formatado (000.000.000-00) ou so digitos.
    Retorna True para strings vazias (campo opcional)."""
    n = "".join(c for c in v if c.isdigit())
    if not n:
        return True
    if len(n) != 11:
        return False
    if len(set(n)) == 1:
        return False
    # 1o digito
    s = sum(int(n[i]) * (10 - i) for i in range(9)) % 11
    d1 = 0 if s < 2 else 11 - s
    if int(n[9]) != d1:
        return False
    # 2o digito
    s = sum(int(n[i]) * (11 - i) for i in range(10)) % 11
    d2 = 0 if s < 2 else 11 - s
    return int(n[10]) == d2


# ── Validacao CNPJ ────────────────────────────────────────────────────────────

def validar_cnpj(v: str) -> bool:
    """Retorna True se o CNPJ for valido (digitos verificadores corretos).
    Aceita formatado (00.000.000/0000-00) ou so digitos.
    Retorna True para strings vazias (campo opcional)."""
    n = "".join(c for c in v if c.isdigit())
    if not n:
        return True
    if len(n) != 14:
        return False
    if len(set(n)) == 1:
        return False
    # 1o digito -- pesos 5,4,3,2,9,8,7,6,5,4,3,2
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    s = sum(int(n[i]) * pesos1[i] for i in range(12)) % 11
    d1 = 0 if s < 2 else 11 - s
    if int(n[12]) != d1:
        return False
    # 2o digito -- pesos 6,5,4,3,2,9,8,7,6,5,4,3,2
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    s = sum(int(n[i]) * pesos2[i] for i in range(13)) % 11
    d2 = 0 if s < 2 else 11 - s
    return int(n[13]) == d2


# ── Validacao unificada (CPF ou CNPJ conforme comprimento) ───────────────────

def validar_cpf_cnpj(v: str) -> tuple:
    """Valida CPF ou CNPJ conforme o numero de digitos.

    Retorna (ok: bool, tipo: str, msg: str).
      ok=True, tipo="cpf"|"cnpj"|"vazio", msg=""
      ok=False, tipo="cpf"|"cnpj"|"invalido", msg="mensagem para o usuario"
    """
    n = "".join(c for c in v if c.isdigit())
    if not n:
        return True, "vazio", ""
    if len(n) == 11:
        if validar_cpf(n):
            return True, "cpf", ""
        return False, "cpf", "CPF invalido -- verifique os digitos"
    if len(n) == 14:
        if validar_cnpj(n):
            return True, "cnpj", ""
        return False, "cnpj", "CNPJ invalido -- verifique os digitos"
    if len(n) < 11:
        return False, "invalido", "CPF incompleto (11 digitos)"
    if len(n) < 14:
        return False, "invalido", "CNPJ incompleto (14 digitos)"
    return False, "invalido", "Documento invalido"
