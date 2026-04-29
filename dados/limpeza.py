# -*- coding: utf-8 -*-
"""
limpeza.py - 2ª etapa de processamento
Compara resultados importados com tabela padrão de exames.
- Se encontrar match → vincula ao exame padrão e calcula nível de interpretação
- Se não encontrar → marca como 'nao_identificado' para revisão
"""

import sqlite3
import json
import re
from .model_prontuario import DB_PATH


# ══════════════════════════════════════════════════════════════
# MATCHING
# ══════════════════════════════════════════════════════════════

def _normalizar(texto: str) -> str:
    """Normaliza texto para comparação: maiúsculo, sem acentos, sem lixo."""
    import unicodedata
    texto = texto.upper().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"\s+", " ", texto)
    # Remove sufixos de sexo do PDF: " M", " F", " MF"
    texto = re.sub(r"\s+[MF]{1,2}$", "", texto)
    # Remove prefixos comuns: "Dosagem de ", "Exame de "
    texto = re.sub(r"^(DOSAGEM\s+DE\s+|DOSAGEM\s+|EXAME\s+DE\s+)", "", texto)
    # Remove "RESULTADO" e valor numérico do final
    texto = re.sub(r"\s+RESULTADO(\s+[\d,\.]+.*)?$", "", texto)
    texto = re.sub(r"\s+RESULT(\s+[\d,\.]+.*)?$", "", texto)
    texto = re.sub(r"\s+[\d,\.]+\s*(MG/DL|NG/ML|U/L|MMOL/L|MEQ/L|G/DL)?$", "", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def carregar_exames_padrao() -> list[dict]:
    """Carrega todos os exames padrão com seus sinônimos normalizados."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()
    cur.execute("SELECT id, nome_oficial, sinonimos FROM exames_padrao WHERE ativo=1")
    rows = cur.fetchall()
    conn.close()

    exames = []
    for row in rows:
        sinonimos_raw = json.loads(row[2]) if row[2] else []
        sinonimos_norm = [_normalizar(s) for s in sinonimos_raw]
        sinonimos_norm.append(_normalizar(row[1]))  # inclui o nome oficial
        exames.append({
            "id":            row[0],
            "nome_oficial":  row[1],
            "sinonimos_norm": sinonimos_norm,
        })
    return exames


def encontrar_exame_padrao(parametro: str, exames_padrao: list[dict]) -> dict | None:
    """
    Tenta encontrar o exame padrão correspondente ao parâmetro importado.
    Estratégia:
    1. Match exato após normalização
    2. Match parcial (parâmetro contém o sinônimo ou vice-versa)
    """
    param_norm = _normalizar(parametro)

    # 1. Match exato
    for exame in exames_padrao:
        if param_norm in exame["sinonimos_norm"]:
            return exame

    # 2. Match parcial — o parâmetro normalizado contém o sinônimo
    melhor = None
    melhor_len = 0
    for exame in exames_padrao:
        for sinonimo in exame["sinonimos_norm"]:
            if len(sinonimo) < 4:
                continue
            if sinonimo in param_norm or param_norm in sinonimo:
                if len(sinonimo) > melhor_len:
                    melhor = exame
                    melhor_len = len(sinonimo)

    return melhor


# ══════════════════════════════════════════════════════════════
# INTERPRETAÇÃO
# ══════════════════════════════════════════════════════════════

def calcular_nivel(valor_str: str, exame_padrao_id: int,
                   sexo: str = "ambos", idade: int = 30) -> str:
    """
    Retorna o nível de interpretação:
    critico_baixo | baixo | otimo | alto | critico_alto | sem_referencia
    """
    try:
        valor = float(valor_str.replace(",", ".").strip())
    except Exception:
        return "sem_referencia"

    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()

    # Busca referência mais específica para sexo/idade
    cur.execute("""
        SELECT critico_baixo, limite_baixo, otimo_min, otimo_max, limite_alto, critico_alto
        FROM referencias_padrao
        WHERE exame_padrao_id = ?
          AND (sexo = ? OR sexo = 'ambos')
          AND idade_min <= ? AND idade_max >= ?
        ORDER BY
          CASE WHEN sexo = ? THEN 0 ELSE 1 END,
          (idade_max - idade_min) ASC
        LIMIT 1
    """, (exame_padrao_id, sexo, idade, idade, sexo))
    ref = cur.fetchone()
    conn.close()

    if not ref:
        return "sem_referencia"

    critico_baixo, limite_baixo, otimo_min, otimo_max, limite_alto, critico_alto = ref

    if valor <= critico_baixo:
        return "critico_baixo"
    elif valor < limite_baixo:
        return "baixo"
    elif otimo_min <= valor <= otimo_max:
        return "otimo"
    elif valor <= limite_alto:
        return "alto"
    else:
        return "critico_alto"


# ══════════════════════════════════════════════════════════════
# EXECUTAR LIMPEZA
# ══════════════════════════════════════════════════════════════

def _buscar_perfil_paciente() -> tuple[str, int]:
    """Retorna (sexo, idade) do perfil do paciente para calcular níveis."""
    import datetime
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur  = conn.cursor()
    cur.execute("SELECT sexo, data_nasc FROM perfil_usuario WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    if not row:
        return "ambos", 30
    sexo   = row[0] or "ambos"
    data_nasc = row[1] or ""
    idade  = 30
    if data_nasc:
        try:
            from datetime import date
            partes = data_nasc.replace("/", "-").split("-")
            if len(partes) == 3:
                d, m, a = int(partes[0]), int(partes[1]), int(partes[2])
                hoje = date.today()
                nascimento = date(a, m, d)
                idade = (hoje - nascimento).days // 365
        except Exception:
            pass
    return sexo, max(0, min(120, idade))


def executar_limpeza(callback_log=None) -> dict:
    """
    Percorre todos os resultados sem exame_padrao_id e tenta fazer o matching.
    Também recalcula nivel_interpretacao de resultados já vinculados
    mas com sem_referencia (pode ter mudado com novo perfil de paciente).
    Retorna estatísticas do processamento.
    """
    def log(msg):
        if callback_log:
            callback_log(msg)
        else:
            print(msg)

    sexo, idade = _buscar_perfil_paciente()
    log(f"Perfil: sexo={sexo}, idade={idade}")

    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()

    # Busca resultados não vinculados OU com nivel sem_referencia/nao_identificado
    cur.execute("""
        SELECT id, parametro, valor, exame_padrao_id
        FROM resultados_estruturados
        WHERE (
            exame_padrao_id IS NULL
            OR nivel_interpretacao IN ('sem_referencia', 'nao_identificado', NULL)
        )
          AND parametro IS NOT NULL
          AND LENGTH(TRIM(parametro)) > 2
    """)
    pendentes = cur.fetchall()
    conn.close()

    if not pendentes:
        log("Nenhum resultado pendente.")
        return {"vinculados": 0, "nao_identificados": 0, "total": 0}

    log(f"{len(pendentes)} resultados para processar...")

    exames_padrao = carregar_exames_padrao()
    vinculados        = 0
    nao_identificados = 0
    recalculados      = 0

    import time as _t
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur  = conn.cursor()

    for resultado_id, parametro, valor, padrao_id_atual in pendentes:
        _t.sleep(0.001)

        if padrao_id_atual:
            # Já vinculado — só recalcula o nível com sexo/idade corretos
            nivel = calcular_nivel(valor or "", padrao_id_atual, sexo, idade)
            cur.execute("""
                UPDATE resultados_estruturados
                SET nivel_interpretacao = ?
                WHERE id = ?
            """, (nivel, resultado_id))
            recalculados += 1
        else:
            exame = encontrar_exame_padrao(parametro, exames_padrao)
            if exame:
                nivel = calcular_nivel(valor or "", exame["id"], sexo, idade)
                cur.execute("""
                    UPDATE resultados_estruturados
                    SET exame_padrao_id = ?,
                        nivel_interpretacao = ?
                    WHERE id = ?
                """, (exame["id"], nivel, resultado_id))
                vinculados += 1
            else:
                cur.execute("""
                    UPDATE resultados_estruturados
                    SET nivel_interpretacao = 'nao_identificado'
                    WHERE id = ?
                """, (resultado_id,))
                nao_identificados += 1

    conn.commit()
    conn.close()

    log(f"✅ Vinculados: {vinculados} | ⚠️ Não identificados: {nao_identificados}")
    return {
        "vinculados":          vinculados,
        "nao_identificados":   nao_identificados,
        "total":               len(pendentes),
    }


def buscar_nao_identificados() -> list[dict]:
    """Retorna lista de resultados não identificados para revisão."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT r.parametro, COUNT(*) as ocorrencias
        FROM resultados_estruturados r
        WHERE r.nivel_interpretacao = 'nao_identificado'
          AND r.parametro IS NOT NULL
        GROUP BY UPPER(TRIM(r.parametro))
        ORDER BY ocorrencias DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [{"parametro": row[0], "ocorrencias": row[1]} for row in rows]


def vincular_manualmente(parametro_original: str, exame_padrao_id: int):
    """
    Vincula manualmente um parâmetro a um exame padrão.
    Também adiciona o parâmetro como sinônimo no exame padrão.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()

    # Atualiza todos os resultados com este parâmetro
    cur.execute("""
        UPDATE resultados_estruturados
        SET exame_padrao_id = ?,
            nivel_interpretacao = NULL
        WHERE UPPER(TRIM(parametro)) = UPPER(TRIM(?))
    """, (exame_padrao_id, parametro_original))

    # Recalcula o nível de interpretação
    cur.execute("""
        SELECT id, valor FROM resultados_estruturados
        WHERE exame_padrao_id = ? AND nivel_interpretacao IS NULL
    """, (exame_padrao_id,))
    pendentes = cur.fetchall()

    for res_id, valor in pendentes:
        nivel = calcular_nivel(valor or "", exame_padrao_id)
        cur.execute("UPDATE resultados_estruturados SET nivel_interpretacao = ? WHERE id = ?",
                    (nivel, res_id))

    # Adiciona como sinônimo no exame padrão
    cur.execute("SELECT sinonimos FROM exames_padrao WHERE id = ?", (exame_padrao_id,))
    row = cur.fetchone()
    if row:
        sinonimos = json.loads(row[0]) if row[0] else []
        novo_sin = parametro_original.upper().strip()
        if novo_sin not in [s.upper() for s in sinonimos]:
            sinonimos.append(novo_sin)
            cur.execute("UPDATE exames_padrao SET sinonimos = ? WHERE id = ?",
                        (json.dumps(sinonimos, ensure_ascii=False), exame_padrao_id))

    conn.commit()
    conn.close()


def criar_novo_exame_padrao(nome_oficial: str, sinonimos: list[str],
                             categoria: str, unidade: str) -> int:
    """Cria um novo exame padrão e vincula os resultados pendentes a ele."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO exames_padrao (nome_oficial, sinonimos, categoria, unidade)
        VALUES (?, ?, ?, ?)
    """, (
        nome_oficial,
        json.dumps(sinonimos, ensure_ascii=False),
        categoria,
        unidade,
    ))
    exame_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Vincula os resultados pendentes
    for sinonimo in sinonimos:
        vincular_manualmente(sinonimo, exame_id)

    return exame_id


def ignorar_parametro(parametro: str):
    """Marca um parâmetro como lixo (ignorado)."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()
    cur.execute("""
        UPDATE resultados_estruturados
        SET nivel_interpretacao = 'ignorado'
        WHERE UPPER(TRIM(parametro)) = UPPER(TRIM(?))
    """, (parametro,))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    executar_limpeza()
