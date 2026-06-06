# -*- coding: utf-8 -*-
"""
dados/sistema_resolver.py
Resolve exames_padrao.sistema a partir de exame_conhecimento.sistema_orgao.
Nomes de sistema devem coincidir com as chaves de _SISTEMAS no hub.
"""
import sqlite3
import re

# Mapa: fragmento de sistema_orgao (lowercase) -> nome do sistema no hub
_MAPA = [
    # Cardiaco
    ("coracao",              "Cardiaco"),
    ("cardiovascular",       "Cardiaco"),
    ("musculo cardiaco",     "Cardiaco"),
    ("ventriculo",           "Cardiaco"),
    ("coagulacao",           "Cardiaco"),
    ("coagulacao",           "Cardiaco"),
    # Visceral — renal/urinario
    ("rim",                  "Visceral"),
    ("adrenal",              "Visceral"),
    ("prostata",             "Visceral"),
    ("figado",               "Visceral"),
    ("vias biliares",        "Visceral"),
    ("pancreas",             "Visceral"),
    ("colon",                "Visceral"),
    ("peritonio",            "Visceral"),
    # Psiquiatria
    ("nervoso",              "Psiquiatria"),
    ("hipofise",             "Psiquiatria"),
    # Ortopedia
    ("osso",                 "Ortopedia"),
    ("musculo esqueletico",  "Ortopedia"),
    # Sangue
    ("sangue",               "Sangue"),
    ("hematopoi",            "Sangue"),
    ("medula ossea",         "Sangue"),
    ("imunologico",          "Sangue"),
    ("imunol",               "Sangue"),
    # Hormônios — Visceral (endocrino sem sistema proprio ainda)
    ("tireoide",             "Visceral"),
    ("gônadas",              "Visceral"),
    ("gonadas",              "Visceral"),
    ("testiculos",           "Visceral"),
    ("ovario",               "Visceral"),
    ("placenta",             "Visceral"),
    ("mama",                 "Visceral"),
    ("metabolismo",          "Sangue"),
    ("adiposo",              "Sangue"),
    ("musculo",              "Ortopedia"),
    ("pulm",                 "Visceral"),
    ("multiplos",            None),   # ambiguo — deixa NULL
]

_STRIP = re.compile(r'[^a-z0-9 /]')


def _normalizar(s: str) -> str:
    s = s.lower()
    # remove acentos basicos
    for a, b in [("ã","a"),("â","a"),("á","a"),("à","a"),
                 ("ê","e"),("é","e"),("è","e"),
                 ("í","i"),("î","i"),
                 ("õ","o"),("ô","o"),("ó","o"),
                 ("ú","u"),("û","u"),
                 ("ç","c")]:
        s = s.replace(a, b)
    return s


def _resolver(sistema_orgao: str) -> str | None:
    if not sistema_orgao:
        return None
    norm = _normalizar(sistema_orgao)
    for fragmento, sistema in _MAPA:
        if fragmento in norm:
            return sistema
    return None


def resolver_sistemas(db_path: str):
    """Percorre exames_padrao sem sistema e tenta resolver via exame_conhecimento."""
    conn = sqlite3.connect(db_path, timeout=10)

    rows = conn.execute("""
        SELECT ep.id, ek.sistema_orgao
        FROM exames_padrao ep
        JOIN exame_conhecimento ek ON ek.exame_padrao_id = ep.id
        WHERE ep.sistema IS NULL AND ek.sistema_orgao IS NOT NULL
    """).fetchall()

    resolvidos = 0
    for ep_id, sistema_orgao in rows:
        sistema = _resolver(sistema_orgao)
        if sistema:
            conn.execute(
                "UPDATE exames_padrao SET sistema = ? WHERE id = ?",
                (sistema, ep_id)
            )
            resolvidos += 1

    conn.commit()

    # pendencias: exames_padrao sem sistema (para tela_pendencias)
    sem_sistema = conn.execute(
        "SELECT COUNT(*) FROM exames_padrao WHERE sistema IS NULL AND ativo = 1"
    ).fetchone()[0]

    conn.close()
    return resolvidos, sem_sistema


def inserir_pendencia_sistema(conn, exame_padrao_id: int):
    """
    Chamado em criar_tabelas() apos INSERT em exames_padrao sem sistema.
    Registra na tabela pendencias (se existir) ou simplesmente deixa sistema=NULL
    — tela_pendencias detecta automaticamente via query.
    """
    pass   # tela_pendencias ja filtra WHERE sistema IS NULL


if __name__ == "__main__":
    import os, sys
    db = os.path.join(os.path.dirname(__file__), "prontuario.db")
    resolvidos, pendentes = resolver_sistemas(db)
    print(f"Resolvidos: {resolvidos} | Pendentes (sem sistema): {pendentes}")
