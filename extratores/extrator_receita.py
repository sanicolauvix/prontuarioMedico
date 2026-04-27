"""
extrator_receita.py
Extrai medicamentos de receitas médicas em PDF usando a API do Claude.
Retorna lista estruturada pronta para salvar em remedios.
"""

import io
import re
import json
import pdfplumber


# ══════════════════════════════════════════════════════════════
# 1. EXTRAÇÃO DE TEXTO DO PDF
# ══════════════════════════════════════════════════════════════

def extrair_texto_receita(conteudo_bytes: bytes) -> str:
    texto = ""
    with pdfplumber.open(io.BytesIO(conteudo_bytes)) as pdf:
        for pagina in pdf.pages:
            t = pagina.extract_text()
            if t:
                texto += t + "\n"
    return texto.strip()


# ══════════════════════════════════════════════════════════════
# 2. INTERPRETAÇÃO VIA CLAUDE API
# ══════════════════════════════════════════════════════════════

def interpretar_receita_com_ia(texto: str) -> list[dict]:
    """
    Envia o texto da receita para a Claude API e retorna
    lista de medicamentos estruturados.
    """
    try:
        import anthropic
        client = anthropic.Anthropic()

        prompt = f"""Você é um assistente médico especializado em interpretar receitas médicas brasileiras.

Analise o texto da receita abaixo e extraia TODOS os medicamentos prescritos.

Para cada medicamento, retorne um objeto JSON com os campos:
- nome: nome do medicamento (string)
- dosagem: concentração/dose (ex: "500mg", "10mg/mL") (string ou null)
- frequencia: como tomar (ex: "1 comprimido de 8 em 8 horas", "2x ao dia") (string ou null)
- data_inicio: data de início se mencionada no formato DD/MM/AAAA (string ou null)
- data_fim: data de fim ou duração convertida (ex: "por 7 dias" → calcule a partir da data da receita) (string ou null)
- medico: nome do médico que prescreveu (string ou null)
- intervalo_horas: número inteiro de horas entre doses se identificável (ex: 8, 12, 24) (integer ou null)
- observacoes: instruções especiais (ex: "tomar com alimento", "não partir") (string ou null)

Retorne SOMENTE um array JSON válido, sem texto adicional, sem markdown, sem explicações.
Exemplo: [{{"nome": "Amoxicilina", "dosagem": "500mg", "frequencia": "1 cápsula de 8 em 8 horas", ...}}]

TEXTO DA RECEITA:
{texto}"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip()
        # Remove possíveis marcadores markdown
        raw = re.sub(r"```json|```", "", raw).strip()
        medicamentos = json.loads(raw)
        return medicamentos if isinstance(medicamentos, list) else []

    except Exception as e:
        print(f"[extrator_receita] Erro na IA: {e}")
        return extrair_receita_regex(texto)


# ══════════════════════════════════════════════════════════════
# 3. FALLBACK: EXTRAÇÃO POR REGEX
# ══════════════════════════════════════════════════════════════

def extrair_receita_regex(texto: str) -> list[dict]:
    """
    Extração heurística quando a API não está disponível.
    Captura padrões comuns de receitas brasileiras.
    """
    medicamentos = []

    # Tenta extrair médico do cabeçalho
    medico = None
    m = re.search(
        r"(?:Dr\.?|Dra\.?)\s+([A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][^\n,]{5,60})",
        texto, re.IGNORECASE
    )
    if m:
        medico = m.group(0).strip()

    # Data da receita
    data_receita = None
    m_data = re.search(r"(\d{2}/\d{2}/\d{4})", texto)
    if m_data:
        data_receita = m_data.group(1)

    # Padrões de medicamentos:
    # 1. "1- Amoxicilina 500mg" ou "1) Amoxicilina 500mg"
    # 2. "Amoxicilina 500mg\n1 cápsula de 8/8h"
    linhas = texto.splitlines()

    # Detecta linhas numeradas como itens de receita
    re_item = re.compile(
        r"^\s*\d+[\.\)]\s*([A-Za-zÀ-ú][^\n]{3,80})"
    )
    re_dose = re.compile(
        r"(\d+(?:[,\.]\d+)?\s*(?:mg|mcg|ml|mL|g|UI|UI/mL|comprimido|cápsula|gota))",
        re.IGNORECASE
    )
    re_freq = re.compile(
        r"(\d+\s*(?:x|vez(?:es)?)\s*(?:ao\s*dia|por\s*dia)|"
        r"de\s*\d+\s*(?:em\s*\d+\s*)?horas?|"
        r"a\s*cada\s*\d+\s*horas?|"
        r"\d+/\d+\s*h)",
        re.IGNORECASE
    )

    i = 0
    while i < len(linhas):
        linha = linhas[i].strip()
        m_item = re_item.match(linha)
        if m_item:
            nome_raw = m_item.group(1).strip()

            # Separa nome da dosagem se estiver na mesma linha
            m_d = re_dose.search(nome_raw)
            dosagem = m_d.group(1) if m_d else None
            nome = nome_raw[:m_d.start()].strip() if m_d else nome_raw

            # Busca frequência nas próximas 3 linhas
            frequencia = None
            intervalo  = None
            for j in range(i + 1, min(i + 4, len(linhas))):
                m_f = re_freq.search(linhas[j])
                if m_f:
                    frequencia = linhas[j].strip()
                    # Tenta extrair intervalo numérico
                    m_int = re.search(r"(\d+)\s*(?:em\s*\d+\s*)?horas?|(\d+)/(\d+)\s*h", frequencia)
                    if m_int:
                        try:
                            intervalo = int(m_int.group(1) or m_int.group(3))
                        except Exception:
                            pass
                    break

            if len(nome) > 2:
                medicamentos.append({
                    "nome":           nome,
                    "dosagem":        dosagem,
                    "frequencia":     frequencia,
                    "data_inicio":    data_receita,
                    "data_fim":       None,
                    "medico":         medico,
                    "intervalo_horas":intervalo,
                    "observacoes":    None,
                })
        i += 1

    return medicamentos


# ══════════════════════════════════════════════════════════════
# 4. FUNÇÃO PRINCIPAL
# ══════════════════════════════════════════════════════════════

def processar_receita_pdf(conteudo_bytes: bytes, nome_arquivo: str) -> dict:
    """
    Processa um PDF de receita médica.
    Retorna dict com:
      - texto:        texto bruto extraído
      - medicamentos: lista de dicts prontos para salvar_remedio()
      - medico:       nome do médico detectado
      - data:         data da receita
    """
    texto = extrair_texto_receita(conteudo_bytes)
    if not texto:
        return {"texto": "", "medicamentos": [], "medico": None, "data": None}

    # Tenta via IA, com fallback regex
    medicamentos = interpretar_receita_com_ia(texto)

    # Extrai data e médico do texto para garantir
    medico = None
    data   = None
    m = re.search(r"(?:Dr\.?|Dra\.?)\s+([A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][^\n,]{5,60})",
                  texto, re.IGNORECASE)
    if m:
        medico = m.group(0).strip()

    m_data = re.search(r"(\d{2}/\d{2}/\d{4})", texto)
    if m_data:
        data = m_data.group(1)

    # Garante que todo item tenha médico e data preenchidos
    for med in medicamentos:
        if not med.get("medico") and medico:
            med["medico"] = medico
        if not med.get("data_inicio") and data:
            med["data_inicio"] = data

    return {
        "texto":        texto,
        "medicamentos": medicamentos,
        "medico":       medico,
        "data":         data,
    }


if __name__ == "__main__":
    import sys
    from pathlib import Path
    arq = sys.argv[1] if len(sys.argv) > 1 else "receita.pdf"
    resultado = processar_receita_pdf(Path(arq).read_bytes(), arq)
    print(json.dumps(resultado["medicamentos"], ensure_ascii=False, indent=2))