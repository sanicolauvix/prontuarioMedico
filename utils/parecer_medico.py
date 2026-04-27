"""
parecer_medico.py
Gera parecer clínico de análise temporal de exames laboratoriais
usando a Claude API. Considera idade, sexo, tendências e correlações.
"""

import json
import re
import logging
from datetime import date


# ══════════════════════════════════════════════════════════════
# DADOS DO PACIENTE — lidos do banco (perfil_usuario)
# ══════════════════════════════════════════════════════════════

def _carregar_paciente() -> dict:
    """Carrega perfil do banco. Fallback se não cadastrado."""
    try:
        from ..dados.model_prontuario import carregar_perfil
        p = carregar_perfil()
        if p and p.get("data_nasc") and p.get("sexo"):
            return p
    except Exception as ex:
        logging.warning(f"[PARECER] Perfil não carregado: {ex}")
    # Fallback — não deve chegar aqui se o fluxo estiver correto
    return {"nome": "Paciente", "data_nasc": "01/01/1970", "sexo": "M"}


def idade_atual() -> int:
    p    = _carregar_paciente()
    nasc_str = p.get("data_nasc", "01/01/1970")
    try:
        d, m, a = nasc_str.split("/")
        nasc = date(int(a), int(m), int(d))
    except Exception:
        return 0
    hoje = date.today()
    return hoje.year - nasc.year - (
        (hoje.month, hoje.day) < (nasc.month, nasc.day)
    )


def sexo_extenso() -> str:
    p = _carregar_paciente()
    return "feminino" if p.get("sexo") == "F" else "masculino"


def nome_paciente() -> str:
    p = _carregar_paciente()
    return (p.get("nome") or "Paciente").split()[0]   # primeiro nome


# ══════════════════════════════════════════════════════════════
# MONTA CONTEXTO ESTRUTURADO PARA A IA
# ══════════════════════════════════════════════════════════════

LABELS_NIVEL = {
    "critico_baixo":    "Crítico (muito baixo)",
    "baixo":            "Baixo",
    "otimo":            "Ótimo / Normal",
    "alto":             "Alto",
    "critico_alto":     "Crítico (muito alto)",
    "sem_referencia":   "Sem referência cadastrada",
    "nao_identificado": "Não identificado",
}


def montar_contexto(exames_selecionados: list[dict]) -> str:
    """
    Transforma os exames selecionados em texto estruturado para a IA.
    exames_selecionados: lista de dicts com nome_oficial, unidade, historico
    historico: [{data, valor, unidade, nivel, laboratorio}, ...]
    """
    linhas = []
    for ex in exames_selecionados:
        nome    = ex["nome_oficial"]
        unidade = ex.get("unidade", "")
        hist    = ex.get("historico", [])

        if not hist:
            linhas.append(f"- {nome}: sem resultados disponíveis")
            continue

        linhas.append(f"\n### {nome} ({unidade})")
        for h in hist:
            data  = (h.get("data") or "")[:10]
            valor = h.get("valor", "?")
            nivel = LABELS_NIVEL.get(h.get("nivel",""), "?")
            lab   = h.get("laboratorio", "")
            linhas.append(f"  {data}: {valor} {unidade} — {nivel}  [{lab}]")

    return "\n".join(linhas)


# ══════════════════════════════════════════════════════════════
# PROMPT PRINCIPAL
# ══════════════════════════════════════════════════════════════

PROMPT_SISTEMA = """Você é um assistente médico especializado em análise laboratorial clínica.
Você analisa resultados de exames de laboratório e fornece pareceres técnicos claros,
baseados em evidências, considerando a faixa etária e sexo do paciente.

IMPORTANTE: Seus pareceres são auxiliares e educacionais. Sempre oriente que o paciente
consulte seu médico para avaliação e conduta clínica definitiva.

Responda SEMPRE em JSON com exatamente esta estrutura:
{
  "tendencias": [
    {
      "exame": "nome do exame",
      "tendencia": "subindo|descendo|estavel|unico_ponto",
      "descricao": "análise objetiva da evolução temporal",
      "alerta": true|false
    }
  ],
  "correlacoes": [
    {
      "exames": ["exame A", "exame B"],
      "descricao": "como esses exames se relacionam clinicamente",
      "relevancia": "alta|media|baixa"
    }
  ],
  "riscos": [
    {
      "categoria": "Cardiovascular|Metabólico|Renal|Hepático|Outro",
      "nivel": "alto|moderado|baixo|sem_risco",
      "descricao": "descrição objetiva do risco identificado"
    }
  ],
  "recomendacoes": [
    "recomendação 1",
    "recomendação 2"
  ],
  "resumo_geral": "parágrafo único com síntese geral do quadro laboratorial"
}

Retorne SOMENTE o JSON, sem texto adicional, sem markdown, sem explicações fora do JSON."""


def gerar_parecer(exames_selecionados: list[dict]) -> dict:
    """
    Chama a Claude API e retorna o parecer estruturado.
    Retorna dict com as chaves: tendencias, correlacoes, riscos, recomendacoes, resumo_geral
    """
    contexto = montar_contexto(exames_selecionados)
    idade    = idade_atual()
    sexo     = PACIENTE["sexo"]
    nasc_str = PACIENTE["nascimento"].strftime("%d/%m/%Y")

    sexo = sexo_extenso()
    nome = nome_paciente()

    prompt = f"""Analise os seguintes resultados laboratoriais do paciente:

PACIENTE:
- Nome: {nome}
- Idade atual: {idade} anos
- Sexo biológico: {sexo}

EXAMES (ordem cronológica):
{contexto}

Forneça:
1. Tendência temporal de cada exame (subindo, descendo, estável)
2. Correlações clínicas relevantes entre os exames apresentados
3. Riscos cardiovasculares e metabólicos considerando {idade} anos, sexo {sexo}
4. Recomendações práticas baseadas nos achados
5. Resumo geral do quadro

Use diretrizes clínicas atuais (ACC/AHA, SBC, SBD) e considere os valores
de referência específicos para {sexo} de {idade} anos."""

    try:
        import anthropic
        client = anthropic.Anthropic()

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=PROMPT_SISTEMA,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        resultado = json.loads(raw)
        logging.info("[PARECER] Gerado com sucesso via API")
        return resultado

    except Exception as ex:
        logging.exception(f"[PARECER] Erro na API: {ex}")
        return {"erro": str(ex)}
