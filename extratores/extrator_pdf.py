# -*- coding: utf-8 -*-
# KOIOS v1.0 | gerado: 2026-03-12 07:18 | extrator_pdf.py
"""
extrator_pdf.py - Extrator universal para múltiplos laboratórios
Suporta: Laboratório Pretti, Cremasco, Tommasi, Virchow (e similares)

Tipos de retorno:
  tipo = "numerico" → resultados com valor numérico → salvar em resultados_estruturados
  tipo = "laudo"    → texto descritivo              → salvar em laudos
"""

import re
import io
import logging


# Sufixos que não fazem parte do nome (sexo, abreviações soltas ex: "COLESTEROL M")
re_sufixo_lixo = re.compile(r"\s+[MF]$")


# ══════════════════════════════════════════════════════════════
# 0. ENCODING CUSTOMIZADO — Dyna-MAPA (Cardio Sistemas)
# ══════════════════════════════════════════════════════════════

def _detectar_encoding_dyna_mapa(texto: str) -> bool:
    """Detecta PDF com encoding customizado Dyna-MAPA (shift +0x1D).
    O gerador usa \x03 como espaço e desloca todos os caracteres -0x1D."""
    if not texto or len(texto) < 20:
        return False
    return texto.count("\x03") > len(texto) * 0.04

def _decodificar_dyna_mapa(texto: str) -> str:
    """Decodifica texto com encoding customizado Dyna-MAPA (shift +0x1D)."""
    result = []
    for ch in texto:
        code = ord(ch)
        if code == 0x03:
            result.append(" ")
        else:
            decoded = code + 0x1D
            if 0x20 <= decoded <= 0x7E:
                result.append(chr(decoded))
            elif 0x80 <= decoded <= 0xFF:
                try:
                    result.append(bytes([decoded]).decode("cp1252"))
                except (ValueError, UnicodeDecodeError):
                    result.append("?")
            else:
                result.append(ch)
    return "".join(result)

# ══════════════════════════════════════════════════════════════
# 1. DETECÇÃO DO LABORATÓRIO
# ══════════════════════════════════════════════════════════════

def detectar_laboratorio(texto: str) -> str:
    t = texto.lower()
    if "pretti"   in t: return "Pretti"
    if "cremasco" in t: return "Cremasco"
    if "tommasi"  in t: return "Tommasi"
    if "virchow"  in t: return "Virchow"
    if "topcon"   in t: return "Topcon"
    if "cardio sistemas" in t: return "DynaMapa"
    if "dyna-mapa"  in t: return "DynaMapa"
    if "dyna mapa"  in t: return "DynaMapa"
    if "medsenior"  in t: return "DynaMapa"
    if "zeiss"      in t: return "Zeiss"
    if "heidelberg" in t: return "Heidelberg"
    # Marcadores alternativos (quando o nome do lab está só em imagem)
    if "id lamina:" in t or "no.exames:" in t: return "Cremasco"
    return "Desconhecido"


# ══════════════════════════════════════════════════════════════
# 2. DETECÇÃO DO TIPO (numérico x laudo)
# ══════════════════════════════════════════════════════════════

PALAVRAS_MAPA = [
    "mapeamento ambulatorial da press",
    "monitorizacao ambulatorial da press",
    "monitoriza",
    "carga press",
    "descenso noturno",
    "pa sist",
    "dyna-mapa",
    "cardio sistemas",
]

PALAVRAS_IMAGEM = [
    "patient name", "patient id", "od(r)", "os(l)",
    "procedure : color", "procedure : red free",
    "fundus", "retinography", "oct ", "angiography",
    "field angle", "print date",
]

PALAVRAS_LAUDO = [
    "laudo de exame", "histopatológico", "histopatologico",
    "impressão diagnóstica", "impressao diagnostica",
    "macroscopia", "procedimento:", "rtu da prostata",
    "anatomia patológica", "anatomia patologica",
    "citologia", "biópsia", "biopsia",
    "parasitológico", "parasitologico",
    "urocultura", "hemocultura",
    "laudo de urina", "exame de urina",
]

PALAVRAS_ENDOSCOPIA = [
    "endoscopia digestiva", "colonoscopia", "esofago:", "estomago:",
    "colo ascendente", "mucosa bulbar", "laudo de video endoscopia",
    "laudo de video colonoscopia", "iage", "fujinon",
    "relatorio de video endoscopia", "relatorio de video colonoscopia",
    "esofago", "estomago", "duodeno", "reto", "sigmoidea",
]

_EDA_KEYS = {"endoscopia digestiva", "esofago:", "estomago:", "mucosa bulbar", "eda"}
_COLO_KEYS = {"colonoscopia", "colo ascendente", "sigmoidea", "reto", "laudo de video colonoscopia"}


def detectar_tipo(texto: str) -> str:
    """Retorna 'laudo', 'imagem', 'mapa' ou 'numerico' baseado no conteúdo do PDF."""
    t = texto.lower()
    for palavra in PALAVRAS_LAUDO:
        if palavra in t:
            return "laudo"
    # Endoscopia / colonoscopia também são laudos
    n_endo = sum(1 for k in PALAVRAS_ENDOSCOPIA if k in t)
    if n_endo >= 2:
        return "laudo"
    for palavra in PALAVRAS_MAPA:
        if palavra in t:
            return "mapa"
    for palavra in PALAVRAS_IMAGEM:
        if palavra in t:
            return "imagem"
    return "numerico"


def detectar_subtipo_laudo(texto: str) -> str:
    """Para laudos, retorna 'endoscopia', 'colonoscopia', 'eda' ou '' (generico)."""
    t = texto.lower()
    n_endo = sum(1 for k in PALAVRAS_ENDOSCOPIA if k in t)
    if n_endo < 2:
        return ""
    n_colo = sum(1 for k in _COLO_KEYS if k in t)
    n_eda  = sum(1 for k in _EDA_KEYS  if k in t)
    if n_colo > n_eda:
        return "colonoscopia"
    if n_eda > 0:
        return "eda"
    return "endoscopia"


# ══════════════════════════════════════════════════════════════
# 3. EXTRAÇÃO DE CABEÇALHO
# ══════════════════════════════════════════════════════════════

def _buscar(texto, padroes):
    for p in padroes:
        m = re.search(p, texto, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return None


def extrair_cabecalho(texto: str, laboratorio: str) -> dict:
    d = {}

    d["paciente_nome"] = _buscar(texto, [
        r"CLIENTE:\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][^\n]{3,50}?)(?:\s+DN:|\s*$)",
        r"PACIENTE:\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][^\n]{3,50}?)(?:\s+DN:|\s*$)",
        r"Sr\.\s*\(a\)\s*:\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][^\n]{3,50})",
        r"Nome\s*:\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][^\n]{3,50}?)(?:\s+Sexo:|\s+C[oó]digo|\s*$)",
        r"Nome[=\s]+([A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][A-ZÁÀÃÂÉÊÍÓÔÕÚÇ\s]{3,60}?)(?:[=\n]|Idade|Sexo|$)",
        r"Paciente[=\s]+([A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][A-ZÁÀÃÂÉÊÍÓÔÕÚÇ\s]{3,60}?)(?:[=\n]|C[oó]digo|$)",
        r"Patient\s+Name\s*:\s*([A-Z][^\n]{3,60})",
        r"Patient\s+Name\s*[:\-]\s*([A-Z][^\n]{3,60})",
    ])

    d["paciente_cpf"] = _buscar(texto, [
        r"CPF:\s*([\d]{3}\.[\d]{3}\.[\d]{3}-[\d]{2})",
        r"CPF\s*:\s*([\d]{3}\.[\d]{3}\.[\d]{3}-[\d]{2})",
    ])

    d["paciente_dn"] = _buscar(texto, [
        r"DN:\s*([\d]{2}/[\d]{2}/[\d]{4})",
        r"Data\s+Nascimento\s*:\s*([\d]{2}/[\d]{2}/[\d]{4})",
    ])

    d["data_exame"] = _buscar(texto, [
        r"Data/Hora\s+Coleta:\s*([\d]{2}/[\d]{2}/[\d]{4})",
        r"Data\s+Coleta:\s*([\d]{2}/[\d]{2}/[\d]{4})",
        r"DATA\s+ENTRADA:\s*([\d]{2}/[\d]{2}/[\d]{4})",
        r"Entrada:\s*([\d]{2}/[\d]{2}/[\d]{4})",
        r"Libera[cç][aã]o:\s*([\d]{2}/[\d]{2}/[\d]{4})",
        r"Create\s+Date\s*:\s*([\d]{2}/[\d]{2}/[\d]{4})",
        r"Exam\s+Date\s*:\s*([\d]{2}/[\d]{2}/[\d]{4})",
    ])

    d["medico_solicit"] = _buscar(texto, [
        r"NOME\s+M[EÉ]DICO:\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][^\n]{3,60}?)(?:\s+CRM|\s*$)",
        r"M[EÉ]DICO:\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][^\n]{3,60}?)(?:\s+CRM|\s*$)",
        r"Solicitante\s*:\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][^\n]{3,60})",
        r"M[eé]dico:\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][^\n]{3,60}?)(?:\s+RM:|\s*$)",
    ])

    d["laboratorio"] = laboratorio
    return d


# ══════════════════════════════════════════════════════════════
# 4. EXTRAÇÃO DE LAUDO TEXTUAL
# ══════════════════════════════════════════════════════════════

def extrair_laudo_virchow(texto: str) -> dict:
    """
    Extrai campos estruturados de laudos Virchow.
    Retorna dict com: tipo_exame, texto_completo, resumo, conclusao
    """
    # Tipo/procedimento
    tipo_exame = _buscar(texto, [
        r"Procedimento:\s*([^\n]+)",
        r"Material:\s*([^\n]+)",
    ]) or "Laudo Histopatológico"

    # Macroscopia → resumo
    resumo = _buscar(texto, [
        r"Macroscopia:\s*(.+?)(?:Impress[aã]o|Dados cl[ií]nicos:|$)",
    ])
    if resumo:
        resumo = " ".join(resumo.split())[:500]

    # Impressão diagnóstica → pega TODAS as ocorrências, a última é o diagnóstico final
    conclusao = None
    matches = list(re.finditer(
        r"Impress[aã]o\s+diagn[oó]stica:\s*([A-ZÁÀÃÂÉÊÍÓÔÕÚÇ\(][^\n]{10,})",
        texto, re.IGNORECASE
    ))
    if matches:
        # A última é sempre o diagnóstico final resumido (ex: HIPERPLASIA BENIGNA...)
        conclusao = matches[-1].group(1).strip()[:400]
    else:
        m = re.search(
            r"Impress[aã]o\s+diagn[oó]stica:\s*(.+?)(?:Procedimento\s+realizado|ASSINATURA|OBS\.|$)",
            texto, re.DOTALL | re.IGNORECASE
        )
        if m:
            conclusao = " ".join(m.group(1).split())[:400]

    return {
        "tipo_exame":     tipo_exame.strip(),
        "texto_completo": texto.strip(),
        "resumo":         resumo or "",
        "conclusao":      conclusao or "",
    }


def extrair_laudo_endoscopia(texto: str) -> dict:
    """Extrai campos de laudos de EDA / Colonoscopia (IAGE e similares)."""
    t = texto.lower()

    if "colonoscopia" in t or "colo ascendente" in t or "sigmoidea" in t:
        tipo_exame = "Colonoscopia"
    elif "endoscopia digestiva" in t or "esofago" in t or "estomago" in t:
        tipo_exame = "EDA - Endoscopia Digestiva Alta"
    else:
        tipo_exame = "Endoscopia"

    # Número do laudo (ex: "Laudo Nº 26176")
    m_num = re.search(r"laudo\s+n[º°o]?\s*\.?\s*(\d+)", texto, re.IGNORECASE)
    if m_num:
        tipo_exame += f" ({m_num.group(1)})"

    # Resumo: texto antes de "Impressão" ou "Diagnóstico" ou fim
    resumo = ""
    m_res = re.search(
        r"(?:EXAME|PROCEDIMENTO|ACHADOS?)[:\s]*(.+?)(?:IMPRESS[AÃ]O|DIAGN[OÓ]STICO|CONCLUS[AÃ]O|$)",
        texto, re.DOTALL | re.IGNORECASE,
    )
    if m_res:
        resumo = " ".join(m_res.group(1).split())[:600]
    else:
        resumo = " ".join(texto.split())[:400]

    # Conclusão / Impressão diagnóstica
    conclusao = ""
    m_conc = re.search(
        r"(?:IMPRESS[AÃ]O\s+DIAGN[OÓ]STICA|CONCLUS[AÃ]O|DIAGN[OÓ]STICO)[:\s]*(.+?)(?:\n\n|$)",
        texto, re.DOTALL | re.IGNORECASE,
    )
    if m_conc:
        conclusao = " ".join(m_conc.group(1).split())[:400]

    return {
        "tipo_exame":     tipo_exame,
        "texto_completo": texto.strip(),
        "resumo":         resumo,
        "conclusao":      conclusao,
    }


def extrair_imagens_pdf(conteudo_bytes: bytes, prefixo: str, pasta_dest: str) -> list:
    """
    Extrai imagens embutidas de paginas de fotos endoscopicas.
    Identifica paginas que contenham 'Relatorio de Video' no texto.
    Retorna lista de {"nome_arquivo": str, "arquivo_local": str, "ordem": int}.
    """
    import io as _io
    import os as _os
    try:
        import pdfplumber
    except ImportError:
        logging.warning("[IMG] pdfplumber nao instalado — sem extracao de imagens")
        return []

    _os.makedirs(pasta_dest, exist_ok=True)
    resultado = []
    seq = 0

    try:
        with pdfplumber.open(_io.BytesIO(conteudo_bytes)) as pdf:
            for page in pdf.pages:
                texto_pag = (page.extract_text() or "").lower()
                # Paginas de fotos contêm "relatorio de video" ou "video endoscopia"
                eh_pag_fotos = (
                    ("relat" in texto_pag and "video" in texto_pag)
                    or "relatorio de video" in texto_pag
                )
                if not eh_pag_fotos:
                    continue

                for img in page.images:
                    try:
                        stream = img.get("stream")
                        if stream is None:
                            continue
                        raw_data = stream.get_data()
                        if not raw_data or len(raw_data) < 200:
                            continue

                        nome = f"{prefixo}_{seq + 1:03d}.jpg"
                        caminho = _os.path.join(pasta_dest, nome)
                        with open(caminho, "wb") as f:
                            f.write(raw_data)

                        resultado.append({
                            "nome_arquivo": nome,
                            "arquivo_local": caminho,
                            "ordem": seq,
                        })
                        seq += 1
                    except Exception as ex_img:
                        logging.warning(f"[IMG] imagem seq={seq}: {ex_img}")
    except Exception as ex:
        logging.warning(f"[IMG] extrair_imagens_pdf: {ex}")

    logging.info(f"[IMG] {len(resultado)} imagem(ns) extraida(s) com prefixo={prefixo}")
    return resultado


def extrair_laudo_generico(texto: str) -> dict:
    """Extrai laudo de laboratórios sem parser específico."""
    # Tentar extrair tipo do exame
    tipo_exame = _buscar(texto, [
        r"^(HISTOPATOL[OÓ]GICO)\b",
        r"Procedimento:\s*([^\n]+)",
        r"TIPO DE PROCEDIMENTO\s+([^\n]+)",
    ]) or "Laudo"

    # Tentar extrair conclusão
    conclusao = ""
    m = re.search(
        r"(?:CONCLUS[AÃ]O|Impressão diagnóstica)[:\s]*\n?(.+?)(?:Data/Hora|ASSINATURA|LAUDO ASSINADO|$)",
        texto, re.DOTALL | re.IGNORECASE
    )
    if m:
        conclusao = " ".join(m.group(1).split())[:400]

    # Macroscopia como resumo
    resumo = _buscar(texto, [
        r"MACROSCOPIA\s*\n(.+?)(?:CONCLUS|Impress[aã]o|Data/Hora|$)",
    ])
    if resumo:
        resumo = " ".join(resumo.split())[:500]
    else:
        resumo = texto[:300].strip()

    return {
        "tipo_exame":     tipo_exame.strip(),
        "texto_completo": texto.strip(),
        "resumo":         resumo,
        "conclusao":      conclusao,
    }


# ══════════════════════════════════════════════════════════════
# 5. EXTRAÇÃO DOS RESULTADOS NUMÉRICOS
# ══════════════════════════════════════════════════════════════

def extrair_resultados(texto: str, laboratorio: str, on_progress=None) -> list[dict]:

    resultados = []

    # ── Pretti ────────────────────────────────────────────────
    if laboratorio == "Pretti":
        # Pretti requer caminho do arquivo — passado via prefixo especial
        if texto.startswith("__PRETTI_PATH__:"):
            resultados += extrair_pretti(texto, on_progress=on_progress)
        # fallback: sem caminho, retorna vazio (será tratado como incompatível)

    # ── Cremasco ──────────────────────────────────────────────
    elif laboratorio == "Cremasco":
        resultados += extrair_cremasco(texto, on_progress=on_progress)

    # ── Tommasi ───────────────────────────────────────────────
    elif laboratorio == "Tommasi":
        resultados += extrair_tommasi(texto)

    # Limpar nomes de quebras de linha, espaços e sufixos de sexo soltos (ex: "COLESTEROL M")
    for _r in resultados:
        nome = _r.get("parametro", "").strip().replace("\n", " ").replace("\r", "")
        nome = re_sufixo_lixo.sub("", nome).strip()
        nome = _normalizar_nome_parametro(nome)
        _r["parametro"] = nome
        for _s in _r.get("sub_resultados", []):
            snome = _s.get("parametro", "").strip().replace("\n", " ").replace("\r", "")
            snome = re_sufixo_lixo.sub("", snome).strip()
            snome = _normalizar_nome_parametro(snome)
            _s["parametro"] = snome
    return resultados


# ── Normalização de nomes de parâmetros ──────────────────────
# Remove prefixos redundantes, reticências, pontos soltos etc.
# Ex: "Dosagem de Ferro ........" → "Ferro Sérico"
#     "Dosagem de Colesterol Total..." → "Colesterol Total"

_MAPA_NOMES = {
    # Formato "Dosagem de X ..." do Tommasi
    "Dosagem de Ferro":                "Ferro Sérico",
    "Dosagem de Homocisteína":         "Homocisteína",
    "Dosagem de Potássio":             "Potássio",
    "Dosagem de Sódio":                "Sódio",
    "Dosagem de T3 Reverso":           "T3 Reverso",
    "Dosagem de Transferrina":         "Transferrina",
    "Dosagem de Triglicerídeos":       "Triglicerídeos",
    "Dosagem de Vitamina A (Retinol)": "Vitamina A (Retinol)",
    "Dosagem de Vitamina B12 (Cobalamina)": "Vitamina B12",
    "Dosagem de Vitamina B12":         "Vitamina B12",
    "Dosagem de Vitamina C (Ácido Ascórbico)": "Vitamina C",
    "Dosagem de Zinco":                "Zinco",
    "Dosagem de Ácido Úrico":          "Ácido Úrico",
    "Dosagem de Serotonina Sérica":    "Serotonina",
    "Dosagem de Colesterol Total":     "Colesterol Total",
    "Dosagem de Estradiol (E2)":       "Estradiol (E2)",
    "Dosagem de Prolactina":           "Prolactina",
    "Dosagem de Progesterona":         "Progesterona",
    # Nomes longos do Tommasi
    "Creatinofosfoquinase (CPK-Total)": "CPK Total",
    "Creatinafosfoquinase - Fração MB (CK-MB)": "CK-MB",
    "Cálcio Sérico Total (CaT)":      "Cálcio Total",
    "Cálcio Ionizado (Ca++) (em mg/dL)":  "Cálcio Ionizado (mg/dL)",
    "Cálcio Ionizado (Ca++) (em mmol/L)": "Cálcio Ionizado (mmol/L)",
    "Cálcio Ionizado (Ca++) (em mEq/L)": "Cálcio Ionizado (mEq/L)",
    "Gama Glutamil-Transferase (GGT)": "GGT",
    "Transaminase Glutâmico-Pirúvica (TGP/ALT)": "TGP (ALT)",
    "Transaminase Glutâmico-Oxaloacética (TGO/AST)": "TGO (AST)",
    "Fosfatase Alcalina Sérica":       "Fosfatase Alcalina",
    "Lactato Desidrogenase (LDH)":     "LDH",
    "VHS (Velocidade de hemossedimentação/1h)": "VHS",
    "Frutosamina (Proteínas Glicosiladas)": "Frutosamina",
    "Insulinemia de Jejum (Basal)":    "Insulina Basal",
    "Glicemia de Jejum":               "Glicemia de Jejum",
    "Glicemia MÉDIA Estimada (GME)":   "Glicemia Média Estimada",
    "Hemoglobina Glicada (HbA1c)":     "Hemoglobina Glicada (HbA1c)",
    "Nitrogênio Ureico (BUN)":         "BUN (Nitrogênio Ureico)",
    "TSH Ultrassensível (Hormônio Tireoestimulante)": "TSH",
    "T4 (Tiroxina) Livre":             "T4 Livre",
    "PTH (Paratormônio) Intacto":      "PTH (Paratormônio)",
    "25 - Hidroxi - Vitamina D (25(OH)D)": "Vitamina D (25-OH)",
    "Linfócitos típicos":              "Linfócitos",
    "Fibrinogênio":                    "Fibrinogênio",
    "Razão Neutrófilos/Linfócitos (NLR)": "NLR",
    "Ferritina Sérica":                "Ferritina",
    # Nomes Cremasco (MAIÚSCULAS)
    "DOSAGEM DE FERRO SERICO":         "Ferro Sérico",
    "HOMOCISTEINA (PLASMA)":           "Homocisteína",
    "ANTI TRANSGLUTAMINASE IGA":       "Anti-Transglutaminase IgA",
    "IMUNOGLOBULINA A - IGA":          "Imunoglobulina A (IgA)",
    "VITAMINA B12 (COBALAMINA)":       "Vitamina B12",
    "SHBG (GLOBULINA LIGADORA DOS HORMONIOS SEXUAIS)": "SHBG",
    "DHT - DEHIDROTESTOSTERONA":       "DHT (Di-Hidrotestosterona)",
    "ESTRADIOL, 17 BETA":              "Estradiol (E2)",
    "GAMA - GLUTAMIL TRANSFERASE":     "GGT",
    "ALANINA AMINOTRANSFERASE (TGP, ALT)": "TGP (ALT)",
    "ASPARTATO AMINOTRANSFERASE (TGO, AST)": "TGO (AST)",
    "AMILASE SERICA":                  "Amilase",
    "ACIDO URICO":                     "Ácido Úrico",
    "ACIDO FOLICO BASAL":              "Ácido Fólico (Vitamina B9)",
    "HEMOGLOBINA GLICADA (A1C)":       "Hemoglobina Glicada (HbA1c)",
    "GLICEMIA BASAL":                  "Glicemia de Jejum",
    "CREATININA SERICA":               "Creatinina",
    "CREATINO FOSFOQUINASE":           "CPK Total",
    "CPK CREATINO FOSFOQUINASE":       "CPK Total",
    "VITAMINA D 25-HIDROXI":           "Vitamina D (25-OH)",
    "25-HIDROXIVITAMINA D":            "Vitamina D (25-OH)",
    "TIROXINA LIVRE - T4 LIVRE":       "T4 Livre",
    "T3 REVERSO":                      "T3 Reverso",
    "TSH ULTRA SENSIVEL":              "TSH",
    "TSH ultra sensivel":              "TSH",
    "GLICEMIA 1 HORA POS DEXTROSOL":   "Glicemia 1h Pós-Dextrosol",
    "GLICEMIA 2 HORAS APOS DEXTROSOL": "Glicemia 2h Pós-Dextrosol",
    "COLESTEROL -LDL":                 "Colesterol LDL",
    "INSULINA BASAL":                  "Insulina Basal",
    "FERRITINA":                       "Ferritina",
    "TESTOSTERONA TOTAL":              "Testosterona Total",
    "TESTOSTERONA LIVRE":              "Testosterona Livre",
    "CALCIO":                          "Cálcio Total",
    "ALBUMINA":                        "Albumina",
    "COLESTEROL":                      "Colesterol Total",
    "COLESTEROL TOTAL":                "Colesterol Total",
    "COLESTEROL HDL":                  "Colesterol HDL",
    "COLESTEROL LDL":                  "Colesterol LDL",
    "CREATININA":                      "Creatinina",
    "TRIGLICERIDEOS":                  "Triglicerídeos",
    "GLICOSE":                         "Glicemia de Jejum",
    "Colesterol - HDL":                "Colesterol HDL",
    "Colesterol - LDL":                "Colesterol LDL",
    "Colesterol - VLDL":               "Colesterol VLDL",
    "Albuminas":                       "Albumina",
    "Bilirrubina Direta (Conjugada)":  "Bilirrubina Direta",
    "Bilirrubina Indireta (Não-Conjugada)": "Bilirrubina Indireta",
}

def _normalizar_nome_parametro(nome: str) -> str:
    """Normaliza nome do parâmetro removendo prefixos, reticências e mapeando nomes conhecidos."""
    if not nome:
        return nome

    # 1. Remover reticências no final: "Ferritina Sérica............:"  →  "Ferritina Sérica"
    nome = re.sub(r'\.{2,}:?\s*$', '', nome).strip()

    # 2. Buscar no mapa de nomes conhecidos (match exato)
    if nome in _MAPA_NOMES:
        return _MAPA_NOMES[nome]

    # 3. Buscar sem reticências internas: "Dosagem de Ferro ........" → "Dosagem de Ferro"
    nome_limpo = re.sub(r'\s*\.{2,}\s*', ' ', nome).strip()
    if nome_limpo in _MAPA_NOMES:
        return _MAPA_NOMES[nome_limpo]

    # 4. Remover prefixo "Dosagem de" genérico se sobrou
    m = re.match(r'^Dosagem\s+de\s+(.+)', nome_limpo, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # 5. Remover reticências residuais
    nome_limpo = re.sub(r'\.{2,}', '', nome_limpo).strip()

    return nome_limpo


def extrair_pretti(texto: str, on_progress=None) -> list[dict]:
    """
    Extrator Laboratório Pretti usando pdfplumber (coordenadas espaciais).
    Recebe o caminho do PDF via dados["arquivo_path"] — mas como a assinatura
    da função só recebe texto, o caminho é passado via texto com prefixo especial
    "__PRETTI_PATH__:caminho".
    """
    import re as _re
    import pdfplumber as _plumber

    # Suporte a caminho direto (chamado via extrair_pretti_path)
    caminho = None
    if texto.startswith("__PRETTI_PATH__:"):
        caminho = texto[len("__PRETTI_PATH__:"):]
    else:
        return []  # Pretti requer pdfplumber com caminho

    resultados = []

    re_result_inline = _re.compile(
        r"RESULTADO[:\s]+([0-9,\.]+)\s+([a-zA-Zµ/%]+(?:/[a-zA-Z\d,\.m²³ ]+)?)",
        _re.IGNORECASE
    )
    re_hemog_linha = _re.compile(
        r"^([A-ZÁÀÃÂÉÊÍÓÔÕÚÇa-záàãâéêíóôõúç\.\'\s\-]+?)\s+"
        r"([0-9,\.]+)\s+"
        r"([a-zA-Zµ/%³]+(?:/[a-zA-Z\d,\.m²³]+)?)\s+"
        r"([0-9,\.]+)\s*[-–a]\s*([0-9,\.]+)"
    )
    re_lixo_nome = _re.compile(
        r"^(Material|Metodo|Método|Soro|Sangue|Urina|Recente|Data|Liberacao|"
        r"Liberação|Assinatura|RESPONSÁVEL|Resultado\s+conf|A\s+interp|depende|"
        r"COLETA|__+|1[A-F0-9]{15}|NOME|CLIENTE|MÉDICO|CPF|CONVÊNIO|UNIDADE|"
        r"Especif|Coefic|Erro|FONTE|Fonte|VR\s*:|Vr\s*:|Valor\s+de|Referencia|"
        r"NOTA|Nota|Para\s+|Com\s+ou|Categoria|Risco|EXAME\s+FÍSICO|"
        r"SEDIMENTO|LEUCOGRAMA|Relativo|Valores\s+de\s+ref|Adultos\s+>|"
        r"Inferior|Superior|ADULTOS|CRIANCAS|MASCULINO|FEMININO|RECÉM|"
        r"De\s+[0-9]|Tempo\s+de\s+Jejum)",
        _re.IGNORECASE
    )

    def _buscar_ref(bloco):
        """Busca ref numérica no bloco, evitando datas e assinaturas digitais."""
        for bl in bloco:
            if _re.search(r"(Data|data|CPF|CRM|conf|ASSINATURA|[0-9]{4}\s*-\s*[0-9]{2}\s*-\s*[0-9]{2})", bl):
                continue
            # Hex de assinatura digital (string longa hex)
            if _re.match(r"^[0-9A-F]{20,}", bl):
                continue
            # Prioridade MASCULINO
            m = _re.search(r"MASCULINO\s*:\s*De\s+([0-9,\.]+)\s+[Aa]\s+([0-9,\.]+)\s*([a-zA-Zµ/%/m²³]+)?", bl, _re.IGNORECASE)
            if m: return f"IR:{m.group(1)} a {m.group(2)} {m.group(3) or ''}".strip()
        for bl in bloco:
            if _re.search(r"(Data|data|CPF|CRM|conf|ASSINATURA|[0-9]{4}\s*-\s*[0-9]{2})", bl):
                continue
            if _re.match(r"^[0-9A-F]{20,}", bl): continue
            m = _re.search(r"ADULTO[S]?\s*[:\.]?\s*([0-9,\.]+)\s*[aA]\s*([0-9,\.]+)\s*([a-zA-Zµ/%/m²³]+)?", bl)
            if m: return f"IR:{m.group(1)} a {m.group(2)} {m.group(3) or ''}".strip()
            m = _re.search(r"VR\s*:.*?([0-9,\.]+)\s*[aA]\s*([0-9,\.]+)\s*([a-zA-Zµ/%/m²³]+)?", bl)
            if m: return f"IR:{m.group(1)} a {m.group(2)} {m.group(3) or ''}".strip()
            m = _re.search(r"^([0-9,\.]+)\s+[aA]\s+([0-9,\.]+)\s*([a-zA-Zµ/%/m²³]+)?$", bl.strip())
            if m: return f"IR:{m.group(1)} a {m.group(2)} {m.group(3) or ''}".strip()
        return ""

    try:
        with _plumber.open(caminho) as pdf:
            total_pg = len(pdf.pages)
            for pg_num, page in enumerate(pdf.pages):
                if on_progress:
                    try:
                        on_progress({"fase": "extraindo", "pagina": pg_num+1,
                                     "total_pags": total_pg, "itens": len(resultados)})
                    except Exception:
                        pass

                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                linhas_dict = {}
                for w in words:
                    y = round(w["top"] / 4) * 4
                    linhas_dict.setdefault(y, []).append(w)
                linhas = []
                for y in sorted(linhas_dict.keys()):
                    txt = " ".join(w["text"] for w in sorted(linhas_dict[y], key=lambda x: x["x0"]))
                    linhas.append((y, txt.strip()))

                i = 0
                while i < len(linhas):
                    y, linha = linhas[i]

                    # ── RESULTADO inline ──────────────────────────
                    m_res = re_result_inline.search(linha)
                    if m_res and "Resultado conf" not in linha:
                        valor   = m_res.group(1)
                        unidade = m_res.group(2)

                        nome = ""
                        for j in range(i-1, max(i-10, -1), -1):
                            _, cand = linhas[j]
                            if cand and not re_lixo_nome.match(cand) and len(cand) > 2:
                                if not _re.match(r"^[0-9,\.]+$", cand):
                                    nome = cand
                                    break

                        if not nome or re_lixo_nome.match(nome):
                            i += 1
                            continue

                        bloco = [bl for _, bl in linhas[i+1:i+15]]
                        ref  = _buscar_ref(bloco)
                        sub  = []

                        for bl in bloco:
                            m_rfg = _re.search(r"^Resultado\s+([0-9,\.]+)\s+([a-zA-Z/\d,\.m²³]+)", bl)
                            if m_rfg:
                                sub.append({
                                    "parametro": "eRFG",
                                    "valor": m_rfg.group(1),
                                    "unidade": m_rfg.group(2),
                                    "referencia": "IR:90 a 999 mL/min/1,73m2",
                                    "sub_resultados": [],
                                })
                                break

                        resultados.append({
                            "parametro":      nome.strip(),
                            "valor":          valor,
                            "unidade":        unidade,
                            "referencia":     ref,
                            "sub_resultados": sub,
                        })
                        i += 1
                        continue

                    # ── Hemograma: "Hemoglobina 14,1 g/dL 13,5 - 17,5" ──
                    m_h = re_hemog_linha.match(linha)
                    if m_h:
                        nome_h = m_h.group(1).strip()
                        if (not re_lixo_nome.match(nome_h) and len(nome_h) > 2
                                and not _re.match(r"^(Horas|Tempo|Categoria|Risco|Inferior|Para\s)", nome_h, _re.IGNORECASE)):
                            resultados.append({
                                "parametro":      nome_h,
                                "valor":          m_h.group(2),
                                "unidade":        m_h.group(3),
                                "referencia":     f"IR:{m_h.group(4)} a {m_h.group(5)}",
                                "sub_resultados": [],
                            })

                    i += 1

    except Exception as ex:
        import logging as _log
        _log.warning(f"[PRETTI] Erro ao extrair: {ex}")

    # Deduplicar e remover RITMO (já é sub de CREATININA)
    vistos = set()
    dedup  = []
    for r in resultados:
        k = r["parametro"].upper()
        if "RITMO" in k or "GLOMERULAR" in k:
            continue
        if k not in vistos:
            vistos.add(k)
            dedup.append(r)

    return dedup




# ══════════════════════════════════════════════════════════════
# 5b. MAPA — Mapeamento Ambulatorial da Pressão Arterial
# ══════════════════════════════════════════════════════════════

def extrair_mapa(texto: str) -> dict:
    """Extrai dados estruturados de relatório MAPA (Dyna-MAPA / MedSênior).
    Retorna dict com tipo_exame, resultados (valores numéricos), texto_completo,
    resumo e conclusao.
    """
    def _buscar_mapa(padroes):
        for p in padroes:
            m = re.search(p, texto, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    # ── Valores médios (Total / Vigília / Sono) ─────────────────
    pa_total   = _buscar_mapa([r"Per[í|i]odo\s+Total[\s=]+([\d]+)\s*/\s*([\d]+)\s*mmHg"])
    pa_vigilia = _buscar_mapa([r"Per[í|i]odo\s+da\s+Vig[í|i]lia[\s=]+([\d]+)\s*/\s*([\d]+)\s*mmHg"])
    pa_sono    = _buscar_mapa([r"Per[í|i]odo\s+do\s+Sono[\s=]+([\d]+)\s*/\s*([\d]+)\s*mmHg"])

    def _extrair_par(padrao):
        m = re.search(padrao, texto, re.IGNORECASE)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return None, None

    sist_total,  dias_total   = _extrair_par(r"Per[í|i]odo\s+Total[\s=]+(\d+)\s*/\s*(\d+)\s*mmHg")
    sist_vig,    dias_vig     = _extrair_par(r"Per[í|i]odo\s+da\s+Vig[í|i]lia[\s=]+(\d+)\s*/\s*(\d+)\s*mmHg")
    sist_sono,   dias_sono    = _extrair_par(r"Per[í|i]odo\s+do\s+Sono[\s=]+(\d+)\s*/\s*(\d+)\s*mmHg")

    # ── Carga pressórica total ──────────────────────────────────
    carga_sist, carga_dias = _extrair_par(
        r"Carga\s+Press[ó|o]rica[\s=]*Total[\s=]+(\d+)%\s*/\s*(\d+)%"
    )

    # ── Descenso noturno ────────────────────────────────────────
    desc_sist, desc_dias = _extrair_par(
        r"Descenso\s+Noturno[\s=]+(\d+)%\s*/\s*(\d+)%"
    )

    # ── Conclusão ───────────────────────────────────────────────
    conclusao = ""
    m_conc = re.search(
        r"ConclusŠo[\s=\-]+(.*?)(?:©20|$)",
        texto, re.DOTALL | re.IGNORECASE
    )
    if not m_conc:
        m_conc = re.search(
            r"Conclus[ã|a]o[\s:\-]+(.*?)(?:©20|Atenciosamente|$)",
            texto, re.DOTALL | re.IGNORECASE
        )
    if m_conc:
        conclusao = " ".join(m_conc.group(1).split())[:600]

    # ── Montar resultados numéricos ─────────────────────────────
    resultados = []

    def _add_res(parametro, valor, unidade, referencia=""):
        if valor:
            resultados.append({
                "parametro": parametro,
                "valor": valor,
                "unidade": unidade,
                "referencia": referencia,
                "sub_resultados": [],
            })

    _add_res("PA Sistólica Média (MAPA)",        sist_total,  "mmHg", "IR:0 a 130 mmHg")
    _add_res("PA Diastólica Média (MAPA)",       dias_total,  "mmHg", "IR:0 a 80 mmHg")
    _add_res("PA Sistólica Vigília (MAPA)",      sist_vig,    "mmHg", "IR:0 a 135 mmHg")
    _add_res("PA Diastólica Vigília (MAPA)",     dias_vig,    "mmHg", "IR:0 a 85 mmHg")
    _add_res("PA Sistólica Sono (MAPA)",         sist_sono,   "mmHg", "IR:0 a 120 mmHg")
    _add_res("PA Diastólica Sono (MAPA)",        dias_sono,   "mmHg", "IR:0 a 70 mmHg")
    _add_res("Carga Pressórica Sistólica (MAPA)", carga_sist, "%",    "IR:0 a 50 %")
    _add_res("Carga Pressórica Diastólica (MAPA)", carga_dias, "%",   "IR:0 a 50 %")
    _add_res("Descenso Noturno Sistólica (MAPA)", desc_sist,  "%",    "IR:10 a 20 %")
    _add_res("Descenso Noturno Diastólica (MAPA)", desc_dias, "%",    "IR:10 a 20 %")

    # ── Resumo legível ──────────────────────────────────────────
    resumo_parts = []
    if sist_total and dias_total:
        resumo_parts.append(f"PA média total: {sist_total}/{dias_total} mmHg")
    if sist_vig and dias_vig:
        resumo_parts.append(f"Vigília: {sist_vig}/{dias_vig} mmHg")
    if sist_sono and dias_sono:
        resumo_parts.append(f"Sono: {sist_sono}/{dias_sono} mmHg")
    if carga_sist and carga_dias:
        resumo_parts.append(f"Carga pressórica: {carga_sist}%/{carga_dias}%")
    if desc_sist and desc_dias:
        resumo_parts.append(f"Descenso noturno: {desc_sist}%/{desc_dias}%")

    # ── Extrair nome do paciente (Dyna-MAPA usa "Nome=" como separador) ──
    paciente_nome = None
    m_pac = re.search(
        r"Nome[=\s]+([A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][A-ZÁÀÃÂÉÊÍÓÔÕÚÇ\s]{3,60}?)(?:[=\n]|Idade|Sexo|$)",
        texto, re.IGNORECASE
    )
    if m_pac:
        paciente_nome = m_pac.group(1).strip()

    return {
        "tipo_exame":     "MAPA - Mapeamento Ambulatorial da Pressão Arterial",
        "resultados":     resultados,
        "texto_completo": texto.strip(),
        "resumo":         " | ".join(resumo_parts),
        "conclusao":      conclusao,
        "paciente_nome":  paciente_nome,
    }

# ══════════════════════════════════════════════════════════════
# 6. CREMASCO — extração linha a linha
# ══════════════════════════════════════════════════════════════

def extrair_cremasco(texto: str, on_progress=None) -> list[dict]:
    """
    Trata dois padrões do PDF Cremasco:

    Padrão A — valor inline com pontos:
        ACIDO URICO
        RESULTADO..............: 7.4    mg/dL
        IR:3.2 a 7.2 mg/dL

    Padrão B — valor em linha separada após RESULTADO + Vr::
        ASPARTATO AMINOTRANSFERASE (TGO, AST)
        RESULTADO
        Vr:  13,0 A 39,0 U/L
        37,0  U/L

    Padrão C — valor antes do RESULTADO (layout colunar):
        33  mg/dL          ← valor
        RESULTADO          ← cabeçalho
        Vr: INFERIOR A...

    Padrão HEMOGRAMA — tratado por extrair_hemograma_cremasco.
    """
    resultados = []
    linhas = [l.strip() for l in texto.splitlines()]
    total  = max(len(linhas), 1)
    i = 0

    # Padrão A: RESULTADO.....: valor unidade
    re_pad_a = re.compile(
        r"^RESULTADO\.+:\s*([\d,\.]+)\s+([a-zA-Zµ/%]+(?:/[a-zA-Z]+)?)",
        re.IGNORECASE
    )
    # Padrão A2: RESULTADO  valor  unidade (sem pontos/dois-pontos — layout Cremasco)
    re_pad_a2 = re.compile(
        r"^RESULTADO\s+([\d,\.]+)\s+([a-zA-Zµ/%³]+(?:/[a-zA-Z³]+)?)\s*$",
        re.IGNORECASE
    )
    # Padrão B/C: valor   unidade (espaço duplo separando)
    re_valor_unidade = re.compile(
        r"^([\d,\.]+)\s{2,}([a-zA-Zµ/%³]+(?:/[a-zA-Z³]+)?)$"
    )
    # Nome válido de exame — aceita maiúsculas e minúsculas
    re_nome = re.compile(
        r"^[A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][A-ZÁÀÃÂÉÊÍÓÔÕÚÇa-záàãâéêíóôõúç\s\-,\.\(\)/0-9]{3,70}$"
    )
    # Linhas de cabeçalho a ignorar
    re_cabecalho = re.compile(
        r"^(PACIENTE|MÉDICO|NOME|DATA|CONVÊNIO|UNIDADE|CÓDIGO|CPF|CRM|"
        r"RESPONSÁVEL|ASSINATURA|LAUDO|CENTRO|CREMASCO FRAGA|"
        r"MATERIAL|MÉTODO|METODO|SORO|EDTA|HPLC|A interpretação)",
        re.IGNORECASE
    )
    # Linhas de sub-referência a ignorar (aparecem dentro de VR de Ferritina, Estradiol etc.)
    re_sub_referencia = re.compile(
        r"^(Rec[eé]m[\s\-]*natos?|1\s*m[eê]s|2\s*a\s*5\s*meses|6\s*meses|"
        r"Crian[cç]as|Homens|Mulheres|Feminino|Masculino|"
        r"Negativo|Fracamente|Positivo|Triagem|"
        r"Fase\s+(folicular|l[uú]tea|Lutea|lutea)|Pico\s+(ovulat[oó]rio|medio|m[eé]dio)|"
        r"Meninas|Meninos|Menor\s+que|Crian[cç]as|"
        r"Sem\s+reposi[cç][aã]o|Com\s+reposi[cç][aã]o|Contraceptivo|"
        r"Acima\s+de\s+\d|6\s+a\s+9\s+anos|9\s+a\s+14|15\s+a\s+50|"
        r"P[oó]s[\s\-]*menopausa|Pre[\s\-]*puberdade|"
        r"Gestantes|Lactentes|Adultos|Idosos|"
        r"Sangue\s+do\s+cord[aã]o|"
        r"Baixo|Intermedi[aá]rio|Alto|Muito\s+Alto|Extremo|"
        r"Normal|Pr[eé][\s\-]*Diabetes|Diabetes)",
        re.IGNORECASE
    )

    def _nome_antes(idx):
        """Busca o nome do exame antes da linha idx, pulando linhas vazias.
        Olha até 15 linhas para trás para cobrir layouts com cabeçalho no meio."""
        for back in range(1, 16):
            if idx - back < 0:
                break
            candidato = linhas[idx - back].strip()
            if not candidato:
                continue
            if re_nome.match(candidato) and not re_cabecalho.match(candidato):
                return candidato
            # linha não-vazia que não é nome — mas pode ser lixo de cabeçalho,
            # continuar procurando se for claramente lixo
            if re_cabecalho.match(candidato):
                continue
            if re.match(r"^\d{2}/\d{2}/\d{4}", candidato):  # data
                continue
            if re.match(r"^(DN:|CRM|O\.S:|UNIDADE|CPF|RG|IR:|eRFG|Data|Método|Material|Metodo)", candidato, re.IGNORECASE):
                continue
            if re.match(r"^\d{3}[\-\.\d]+", candidato):  # número de OS
                continue
            break  # linha não-vazia não reconhecida — parar
        return ""

    while i < len(linhas):
        linha = linhas[i]

        if on_progress and i % 10 == 0:
            try:
                on_progress({
                    "fase": "extraindo", "pagina": i, "total_pags": total,
                    "linhas": i, "total_linhas": total, "itens": len(resultados),
                })
            except Exception:
                pass

        if not linha or len(linha) < 3:
            i += 1
            continue

        if re_cabecalho.match(linha):
            i += 1
            continue

        # HEMOGRAMA — bloco dedicado
        if "HEMOGRAMA" in linha.upper():
            bloco_hemo = []
            j = i
            while j < len(linhas) and j < i + 80:
                lj = linhas[j].strip()
                # Parar o bloco quando encontrar um novo exame ou seção
                if j > i + 5 and (
                    re.match(r"^(DOSAGEM|ANTI\s|IMUNOGLOBULINA|VITAMINA|FERRITINA|CELULA|PSA|TSH|GLICEMIA|COLESTEROL|CREATININA|RESULTADO)", lj, re.IGNORECASE)
                    or re.match(r"^Data/Hora\s+Coleta:", lj, re.IGNORECASE)
                ):
                    break
                bloco_hemo.append(lj)
                j += 1
            resultados += extrair_hemograma_cremasco("\n".join(bloco_hemo))
            i = j
            continue

        # Padrão A: RESULTADO.....: valor unidade
        m_a = re_pad_a.match(linha)
        if m_a:
            nome = _nome_antes(i)
            if nome:
                ref = ""
                # próxima linha não-vazia pode ser IR: ou Valores de Referencia
                for _k in range(1, 4):
                    if i + _k >= len(linhas): break
                    _lk = linhas[i + _k].strip()
                    if not _lk: continue
                    if re.match(r"^(IR:|Valores\s+de\s+Refer)", _lk, re.IGNORECASE):
                        ref = _lk
                    break
                resultados.append({
                    "parametro":      nome,
                    "valor":          m_a.group(1),
                    "unidade":        m_a.group(2),
                    "referencia":     ref,
                    "sub_resultados": [],
                })
            i += 1
            continue

        # Padrão A2: RESULTADO  valor  unidade (Cremasco sem pontos)
        m_a2 = re_pad_a2.match(linha)
        if m_a2:
            nome = _nome_antes(i)
            if nome:
                ref = ""
                for _k in range(1, 8):
                    if i + _k >= len(linhas): break
                    _lk = linhas[i + _k].strip()
                    if not _lk: continue
                    if re.match(r"^(VR:|V\.R\.|IR:|Valores\s+de\s+Refer)", _lk, re.IGNORECASE):
                        ref = _lk
                    break
                resultados.append({
                    "parametro":      nome,
                    "valor":          m_a2.group(1),
                    "unidade":        m_a2.group(2),
                    "referencia":     ref,
                    "sub_resultados": [],
                })
            i += 1
            continue

        # Padrão B: nome → RESULTADO → Vr: → valor  unidade
        # Detecta "RESULTADO" sozinho
        if linha.upper() == "RESULTADO":
            nome = _nome_antes(i)
            ref = ""
            valor = ""
            unidade = ""
            for offset in range(1, 13):  # até 12 linhas à frente
                if i + offset >= len(linhas):
                    break
                prox = linhas[i + offset].strip()
                # referência
                if re.match(r"^(Vr:|VR:|V\.R\.|Valores?\s+de\s+Refer)", prox, re.IGNORECASE) and not ref:
                    ref = prox
                    continue
                # valor  unidade
                m_v = re_valor_unidade.match(prox)
                if m_v:
                    valor   = m_v.group(1)
                    unidade = m_v.group(2)
                    break
                # valor sozinho (ex: "6,00" seguido de "%" numa linha separada)
                if re.match(r"^[\d,\.]+$", prox) and not valor:
                    valor = prox
                    # unidade pode estar nas próximas 12 linhas
                    for off2 in range(1, 13):
                        if i + offset + off2 < len(linhas):
                            prox2 = linhas[i + offset + off2].strip()
                            if re.match(r"^[a-zA-Zµ/%³]+$", prox2):
                                unidade = prox2
                                break
                            # notas explicativas (começam com - ou *) — ignorar e continuar
                            if prox2.startswith(("-", "*", "Risco", "Nota", "Atenção")):
                                continue
                            if len(prox2) > 30:  # texto explicativo — parar
                                break
                    break

            _nomes_filtrar = re.compile(r"^(eRFG|eRFGem|Bastonetes|Segmentados)", re.IGNORECASE)
            if valor and nome and not _nomes_filtrar.match(nome):
                resultados.append({
                    "parametro":      nome,
                    "valor":          valor,
                    "unidade":        unidade,
                    "referencia":     ref,
                    "sub_resultados": [],
                })
            i += 1
            continue

        # Padrão C: valor  unidade ANTES do RESULTADO (layout colunar)
        m_c = re_valor_unidade.match(linha)
        if m_c:
            for offset in range(1, 4):
                if i + offset >= len(linhas):
                    break
                prox = linhas[i + offset].strip()
                if not prox:
                    continue
                if prox.upper() == "RESULTADO":
                    nome = _nome_antes(i)
                    if nome:
                        resultados.append({
                            "parametro":      nome,
                            "valor":          m_c.group(1),
                            "unidade":        m_c.group(2),
                            "referencia":     "",
                            "sub_resultados": [],
                        })
                break
            i += 1
            continue

        # Padrão D: NOME......: valor unidade (ex: CREATININA SERICA......: 1.15 mg/dL)
        # Sub-resultados como eRFG são capturados como filhos do pai
        re_ir = re.compile(r"^IR:\s*([\d,\. ]+[a-zA-Zµ/%/\.]+.*)", re.IGNORECASE)
        m_d = re.match(r"^([A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][A-ZÁÀÃÂÉÊÍÓÔÕÚÇ\s]+?)\.{3,}:\s*([\d,\.]+)\s+([a-zA-Zµ/%][a-zA-Zµ/%0-9\.]*(?:/[a-zA-Z0-9\.]+)*)", linha, re.IGNORECASE)
        if m_d:
            nome_inline = m_d.group(1).strip()

            # Filtrar linhas de sub-referência (ex: "Recém natos......: 25,0 a 200,0 ng/mL")
            if re_sub_referencia.match(nome_inline):
                i += 1
                continue

            nome_antes  = _nome_antes(i)
            nome        = nome_antes if nome_antes else nome_inline

            # Capturar referência IR: na linha seguinte não-vazia
            ref_d = ""
            for _k in range(1, 4):
                if i + _k >= len(linhas): break
                _lk = linhas[i + _k].strip()
                if not _lk: continue
                if re_ir.match(_lk): ref_d = _lk
                break

            # Sub-resultados: linhas seguintes que também são padrão D (ex: eRFG)
            sub_results = []
            _j = i + 1
            while _j < len(linhas) and _j < i + 8:
                _lj = linhas[_j].strip()
                _ms = re.match(r"^([a-zA-ZÀ-ú][a-zA-ZÀ-ú\s]+?)\.{3,}:\s*([\d,\.]+)\s+([a-zA-Zµ/%][a-zA-Zµ/%0-9\.]*(?:/[a-zA-Z0-9\.]+)*)", _lj)
                if _ms:
                    _sub_ref = ""
                    for _k2 in range(1, 4):
                        if _j + _k2 >= len(linhas): break
                        _lk2 = linhas[_j + _k2].strip()
                        if not _lk2: continue
                        if re_ir.match(_lk2): _sub_ref = _lk2
                        break
                    sub_results.append({
                        "parametro":  _ms.group(1).strip(),
                        "valor":      _ms.group(2),
                        "unidade":    _ms.group(3),
                        "referencia": _sub_ref,
                    })
                _j += 1

            _filtrar_d = re.compile(r"^(eRFG|Bastonetes|Segmentados)", re.IGNORECASE)
            if not _filtrar_d.match(nome_inline):
                resultados.append({
                    "parametro":      nome,
                    "valor":          m_d.group(2),
                    "unidade":        m_d.group(3),
                    "referencia":     ref_d,
                    "sub_resultados": sub_results,
                })
            i += 1
            continue

        i += 1

    return resultados


def _extrair_referencia(bloco: str) -> str:
    m = re.search(
        r"(?:VR|V\.R\.|Valor\s+de\s+refer[eê]ncia)[:\s]*(.{5,200}?)(?:Especifica|Nota:|Data/Hora|Material:|$)",
        bloco, re.DOTALL | re.IGNORECASE
    )
    if m:
        return " ".join(m.group(1).split())[:250]
    return ""


def extrair_hemograma_cremasco(bloco: str) -> list[dict]:
    resultados = []
    padrao = re.compile(
        r"^([A-Za-zÀ-ú][A-Za-zÀ-ú\s]+?)\s{2,}"
        r"([\d,\.]+)\s+"
        r"([a-zA-Zµ/%³]+(?:/[a-zA-Z³]+)?)\s*"
        r"(.*)$"
    )
    for linha in bloco.splitlines():
        m = padrao.match(linha.strip())
        if m and len(m.group(1)) > 2:
            resultados.append({
                "parametro":  m.group(1).strip(),
                "valor":      m.group(2),
                "unidade":    m.group(3),
                "referencia": m.group(4).strip(),
            })
    return resultados


def extrair_hemograma_tommasi(texto: str) -> list[dict]:
    """Mantido por compatibilidade — chama extrair_tommasi."""
    return extrair_tommasi(texto)


def extrair_tommasi(texto: str) -> list[dict]:
    """
    Extrator completo para Laboratório Tommasi.
    Cobre 3 formatos presentes nos PDFs:

    Formato A — Hemograma (SÉRIE VERMELHA / SÉRIE BRANCA / PLAQUETAS):
        Hemácias  5,800  milhões/mm3  4,5 a 5,9 milhões/mm3
        Hematócrito  51,80  %  41,0 a 53,0 %
        Razão Neutrófilos/Linfócitos (NLR)  2,33  1,00 a 3,00

    Formato B — Exame isolado com pontos e VR na linha seguinte:
        Ferritina Sérica............:  25,7  ng/mL
        V.R.:  23,9 a 336,2 ng/mL

    Formato C — Exame com nome longo e dois-pontos:
        Dosagem de Vitamina B12 (Cobalamina):  374,0  pg/mL
    """
    resultados = []
    linhas = [l.rstrip() for l in texto.splitlines()]
    total  = len(linhas)

    # ── Ignorar linhas de cabeçalho / lixo ───────────────────
    re_lixo = re.compile(
        r"^(Sr\.\s*\(a\)|Solicitante|Código|Unidade|Convenio|Convênio|"
        r"A interpretação|atos médicos|Av\.|Tommasi|CNPJ|CNES|CRF|CPF|"
        r"Data/Hora|Legenda|Pag\.|ASSINATURA|[0-9A-F]{20,}|"
        r"Material\s*:|Método\s*:|Metodo\s*:|Análise realizada|Padronizações|"
        r"ICSH|Recomendations|Int\. Jnl|EXAME LIBERADO|Ref\.:|\*Análise|"
        r"Importante:|Fonte:|Anteriores:|Literatura|Ref\. David|"
        r"Deficiência|Limítrofe|Desejável|Elevado|Muito elevado|"
        r"←|→|[0-9]{3,4}\s*→|←\s*[0-9])",
        re.IGNORECASE
    )

    # ── Nomes de parâmetros a ignorar no hemograma ────────────
    re_ignorar_param = re.compile(
        r"^(Blastos|Pro-mielócitos|Mielócitos|Metamielócitos|"
        r"Linfócitos atípicos|Células Indiferenciadas|LEUCÓCITOS|"
        r"SÉRIE VERMELHA|SÉRIE BRANCA|Valores de referência|"
        r"Hemograma Completo)",
        re.IGNORECASE
    )

    # ── Regex Formato A — linha columnar do hemograma ─────────
    # Caso normal: Nome  valor  unidade  referencia
    re_hemo_normal = re.compile(
        r"^([A-Za-zÀ-ú][A-Za-zÀ-ú\s\.\(\)/\-]+?)\s{2,}"
        r"([\d,\.]+)\s+"
        r"([A-Za-zÀ-úµ/%³]+(?:[/\.][A-Za-zÀ-ú³\d]+)?)\s+"
        r"(.+)$"
    )
    # Caso sem unidade (ex: NLR): Nome  valor  referencia_numerica
    re_hemo_sem_unidade = re.compile(
        r"^([A-Za-zÀ-ú][A-Za-zÀ-ú\s\.\(\)/\-]+?)\s{2,}"
        r"([\d,\.]+)\s+"
        r"([\d,][\d,\.\s]+[aA][\d,\.\s]+[\d,\.]+)\s*$"
    )
    # Leucócitos diferencial: Nome  %  abs  referencia (tem 2 valores numéricos)
    re_hemo_leucoc = re.compile(
        r"^([A-Za-zÀ-ú][A-Za-zÀ-ú\s]+?)\s+"
        r"([\d,\.]+)\s+"          # %
        r"([\d,\.]+)\s+"          # absoluto
        r"(.+)$"
    )

    # ── Regex Formato B — Exame.....: valor  unidade ──────────
    re_fmt_b = re.compile(
        r"^([A-Za-zÀ-ú][^\n:]{3,60}?)[\.\s]*:{1,2}\s*([\d,\.]+)\s+([a-zA-Zµ/%³]+(?:[/\.][a-zA-Zm²³\d]+)?)\s*$"
    )

    # ── Regex Formato C — Dosagem/nome longo: valor unidade ───
    re_fmt_c = re.compile(
        r"^(Dosagem\s+de\s+[^\n:]{3,80}?)\s*:\s*([\d,\.]+)\s+([a-zA-Zµ/%³]+(?:[/\.][a-zA-Z³\d]+)?)\s*$",
        re.IGNORECASE
    )

    # ── Regex VR — referência na linha seguinte ───────────────
    re_vr = re.compile(
        r"^V\.?R\.?:?\s*(.{5,100})",
        re.IGNORECASE
    )

    # ── Parâmetros do leucograma que queremos (% apenas) ──────
    LEUCOCITOS_OK = {
        "neutrófilos bastonetes", "neutrófilos segmentados",
        "eosinófilos", "basófilos", "linfócitos típicos", "monócitos",
        "razão neutrófilos/linfócitos (nlr)", "nlr",
    }

    em_hemograma = False
    vistos = set()

    # ── Rastreamento de título da seção ──────────────────────
    # Para substituir nomes genéricos como "Resultado (em mg/dL)"
    # pelo nome real do exame (ex: "Cálcio Ionizado (em mg/dL)")
    titulo_secao = ""
    re_titulo_secao = re.compile(
        r"^(Determinação\s+de\s+.+|Dosagem\s+de\s+.+|"
        r"Proteínas\s+Totais.+|Hemoglobina\s+Glicada.+|"
        r"Frutosamina.+|Insulinemia.+|Creatinofosfoquinase.+|"
        r"Fibrinogênio|VHS\s*\(.+|Lactato\s+Desidrogenase.+|"
        r"Testosterona\s+Livre.+|PSA\s+Livre.+|"
        r"[A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][A-Za-zÀ-ú\s\-,\.\(\)/0-9]{5,70})\s*$",
        re.IGNORECASE
    )
    re_resultado_generico = re.compile(
        r"^Resultado\b",
        re.IGNORECASE
    )

    def _resolver_nome_generico(nome_raw: str) -> str:
        """Se o nome começa com 'Resultado', substitui pelo título da seção."""
        if not re_resultado_generico.match(nome_raw):
            return nome_raw
        if not titulo_secao:
            return nome_raw
        # Extrair qualificador: "Resultado (em mg/dL)" → "(em mg/dL)"
        m_qual = re.match(r"Resultado\s*(\(.+\))?", nome_raw, re.IGNORECASE)
        qualif = m_qual.group(1) if m_qual and m_qual.group(1) else ""
        # Montar nome: "Cálcio Ionizado" + " (em mg/dL)" ou só o título
        base = titulo_secao
        # Remover prefixo "Determinação de" / "Dosagem de" se presente
        base = re.sub(r"^Determina[cç][aã]o\s+de\s+", "", base, flags=re.IGNORECASE)
        base = re.sub(r"^Dosagem\s+de\s+", "", base, flags=re.IGNORECASE)
        if qualif:
            return f"{base} {qualif}"
        return base

    def _add(param, valor, unidade, ref):
        param = _resolver_nome_generico(param)
        k = param.upper().strip()
        if k in vistos or len(k) < 2:
            return
        vistos.add(k)
        resultados.append({
            "parametro":      param.strip(),
            "valor":          valor.strip(),
            "unidade":        unidade.strip(),
            "referencia":     ref.strip(),
            "sub_resultados": [],
        })

    i = 0
    while i < total:
        linha = linhas[i].strip()

        # ── Rastrear título de seção (ex: "Determinação de Cálcio Ionizado")
        if (re_titulo_secao.match(linha)
                and not re_lixo.match(linha)
                and not re_ignorar_param.match(linha)
                and ":" not in linha
                and len(linha) > 5
                and not re.match(r"^\d", linha)):
            titulo_secao = linha.strip()

        # Detecta início do hemograma
        if re.search(r"SÉRIE VERMELHA|SÉRIE BRANCA", linha):
            em_hemograma = True
            i += 1
            continue

        # Fim do hemograma (seção de texto longo)
        if em_hemograma and len(linha) > 120:
            em_hemograma = False

        if not linha or re_lixo.match(linha):
            i += 1
            continue

        # ── FORMATO A: hemograma ──────────────────────────────
        if em_hemograma:
            if re_ignorar_param.match(linha):
                i += 1
                continue

            # Leucócitos diferencial (% + absoluto)
            m = re_hemo_leucoc.match(linha)
            if m:
                nome = m.group(1).strip()
                if nome.lower() in LEUCOCITOS_OK:
                    pct   = m.group(2)
                    ref   = m.group(4).strip()
                    # referência pode ter formato "0 a 3 % (Até 830/mm3)" — pegar só até o %
                    ref_clean = re.sub(r"\s*\(.*\)", "", ref).strip()
                    _add(nome, pct, "%", ref_clean)
                    i += 1
                    continue

            # NLR — sem unidade
            m = re_hemo_sem_unidade.match(linha)
            if m:
                nome = m.group(1).strip()
                if not re_ignorar_param.match(nome):
                    _add(nome, m.group(2), "", m.group(3).strip())
                i += 1
                continue

            # Linha normal hemograma
            m = re_hemo_normal.match(linha)
            if m:
                nome = m.group(1).strip()
                if not re_ignorar_param.match(nome) and len(nome) > 2:
                    ref = m.group(4).strip()
                    # Remover parte da unidade duplicada na ref: "41,0 a 53,0 %" → ok
                    _add(nome, m.group(2), m.group(3), ref)
                i += 1
                continue

        # ── FORMATO C: Dosagem de X: valor unidade ────────────
        m = re_fmt_c.match(linha)
        if m:
            ref = ""
            # Procura VR nas próximas 3 linhas não-vazias
            for offset in range(1, 8):
                if i + offset >= total: break
                prox = linhas[i + offset].strip()
                if not prox: continue
                mv = re_vr.match(prox)
                if mv:
                    ref = mv.group(1).strip()
                break
            _add(m.group(1).strip(), m.group(2), m.group(3), ref)
            i += 1
            continue

        # ── FORMATO B: Nome.....: valor unidade ───────────────
        m = re_fmt_b.match(linha)
        if m:
            nome = m.group(1).strip().rstrip(".")
            if not re_lixo.match(nome) and len(nome) > 3:
                ref = ""
                for offset in range(1, 8):
                    if i + offset >= total: break
                    prox = linhas[i + offset].strip()
                    if not prox: continue
                    mv = re_vr.match(prox)
                    if mv:
                        ref = mv.group(1).strip()
                    break
                _add(nome, m.group(2), m.group(3), ref)
            i += 1
            continue

        i += 1

    return resultados


# ══════════════════════════════════════════════════════════════
# 7. FUNÇÃO PRINCIPAL
# ══════════════════════════════════════════════════════════════

def extrair_pdf_bytes(conteudo_bytes: bytes, nome_arquivo: str,
                      drive_file_id: str = None, on_progress=None,
                      caminho_pdf: str = None) -> dict:
    """
    on_progress(info: dict) — callback opcional chamado durante a extração.
    info = {"pagina": int, "total_pags": int, "linhas": int, "itens": int, "fase": str}
    """
    def _prog(fase, pagina=0, total_pags=0, linhas=0, itens=0, total_linhas=0):
        logging.info(f"[EXTRATOR] _prog fase={fase} pag={pagina}/{total_pags} linhas={linhas}/{total_linhas} itens={itens}")
        print(f"[EXTRATOR] _prog fase={fase} pag={pagina}/{total_pags} linhas={linhas}/{total_linhas} itens={itens}")
        if on_progress:
            try:
                on_progress({"fase": fase, "pagina": pagina,
                             "total_pags": total_pags, "linhas": linhas,
                             "itens": itens, "total_linhas": total_linhas})
            except Exception as _ex:
                logging.warning(f"[EXTRATOR] on_progress erro: {_ex}")
                print(f"[EXTRATOR] on_progress erro: {_ex}")
        else:
            print(f"[EXTRATOR] on_progress=None, callback nao registrado")

    texto_completo = ""
    MAX_PAGINAS    = 30
    MAX_CHARS      = 150_000

    # ── Passagem 1: extrair todo o texto para saber total de linhas ──
    with pdfplumber.open(io.BytesIO(conteudo_bytes)) as pdf:
        total_pags = len(pdf.pages)
        print(f"[EXTRATOR] iniciando mapeamento: {total_pags} páginas")
        logging.info(f"[EXTRATOR] iniciando mapeamento: {total_pags} páginas")
        _prog("contando", 0, total_pags)
        textos_por_pag = []
        linhas_mapeadas = 0
        for idx, pagina in enumerate(pdf.pages[:MAX_PAGINAS]):
            try:
                t = pagina.extract_text(x_tolerance=3, y_tolerance=3) or ""
                textos_por_pag.append(t)
                linhas_mapeadas += t.count("\n") + (1 if t else 0)
                pagina.flush_cache()
            except Exception as e_pag:
                logging.warning(f"[EXTRATOR] Página {idx+1}/{total_pags} erro: {e_pag}")
                textos_por_pag.append("")
            print(f"[EXTRATOR] pag {idx+1}/{total_pags} · {linhas_mapeadas} linhas")
            logging.info(f"[EXTRATOR] pag {idx+1}/{total_pags} · {linhas_mapeadas} linhas")
            _prog("contando", idx + 1, total_pags, linhas_mapeadas)

    # Total real de linhas conhecido antes de começar a "processar"
    total_linhas_real = sum(t.count("\n") + (1 if t else 0) for t in textos_por_pag)
    _prog("lendo", 0, total_pags, 0, 0, total_linhas_real)

    # ── Passagem 2: montar texto_completo emitindo progresso por linha ──
    # Detectar e decodificar encoding Dyna-MAPA (shift +0x1D)
    amostra = "".join(textos_por_pag[:2])
    if _detectar_encoding_dyna_mapa(amostra):
        logging.info(f"[EXTRATOR] Encoding Dyna-MAPA detectado — decodificando {nome_arquivo}")
        textos_por_pag = [_decodificar_dyna_mapa(t) for t in textos_por_pag]

    linhas_acum = 0
    for idx, t in enumerate(textos_por_pag):
        if t:
            texto_completo += t + "\n"
            linhas_acum += t.count("\n") + 1
        _prog("lendo", idx + 1, total_pags, linhas_acum, 0, total_linhas_real)
        if len(texto_completo) >= MAX_CHARS:
            logging.warning(f"[EXTRATOR] Limite de chars atingido em {nome_arquivo}")
            break

    laboratorio = detectar_laboratorio(texto_completo)
    cabecalho   = extrair_cabecalho(texto_completo, laboratorio)
    tipo        = detectar_tipo(texto_completo)

    dados = {
        "arquivo_origem":  nome_arquivo,
        "drive_file_id":   drive_file_id,
        "resultado_texto": texto_completo,
        "tipo":            tipo,
        "paciente_nome":   cabecalho.get("paciente_nome"),
        "paciente_cpf":    cabecalho.get("paciente_cpf"),
        "data_exame":      cabecalho.get("data_exame"),
        "laboratorio":     cabecalho.get("laboratorio"),
        "medico_solicit":  cabecalho.get("medico_solicit"),
    }

    total_linhas = texto_completo.count("\n")
    _prog("analisando", total_pags, total_pags, total_linhas, 0, total_linhas)

    if tipo == "mapa":
        # ── MAPA — Dyna-MAPA / Cardio Sistemas ────────────────
        _prog("analisando", total_pags, total_pags, total_linhas, 0, total_linhas)
        mapa = extrair_mapa(texto_completo)
        dados["tipo_exame"] = mapa["tipo_exame"]
        dados["resultados"] = mapa["resultados"]
        dados["laudo"] = {
            "texto_completo": mapa["texto_completo"],
            "resumo":         mapa["resumo"],
            "conclusao":      mapa["conclusao"],
        }
        # Propagar paciente_nome do MAPA (sobrescreve None do cabecalho genérico)
        if mapa.get("paciente_nome"):
            dados["paciente_nome"] = mapa["paciente_nome"]
        dados["modelo_nao_configurado"] = False
        _prog("concluido", total_pags, total_pags, total_linhas, len(mapa["resultados"]))

    elif tipo == "imagem":
        # ── Exame de imagem (fundoscopia, OCT, etc.) ───────────
        procedimento = _buscar(texto_completo, [
            r"Procedure\s*:\s*([^\n]+)",
            r"Exame\s*:\s*([^\n]+)",
        ]) or "Exame de Imagem"
        equipamento = laboratorio if laboratorio != "Desconhecido" else "Equipamento de Imagem"
        dados["tipo_exame"] = f"{procedimento.strip()} ({equipamento})"
        dados["resultados"] = []
        dados["laudo"] = {
            "texto_completo": texto_completo.strip(),
            "resumo":         f"Exame de imagem — {procedimento.strip()}. Equipamento: {equipamento}.",
            "conclusao":      "",
        }
        dados["modelo_nao_configurado"] = False

    elif tipo == "laudo":
        # ── Laudo textual ──────────────────────────────────────
        subtipo = detectar_subtipo_laudo(texto_completo)
        if subtipo in ("eda", "colonoscopia", "endoscopia"):
            laudo = extrair_laudo_endoscopia(texto_completo)
        elif laboratorio == "Virchow":
            laudo = extrair_laudo_virchow(texto_completo)
        else:
            laudo = extrair_laudo_generico(texto_completo)

        dados["tipo_exame"] = laudo["tipo_exame"]
        dados["subtipo"]    = subtipo
        dados["resultados"] = []
        dados["laudo"] = {
            "texto_completo": laudo["texto_completo"],
            "resumo":         laudo["resumo"],
            "conclusao":      laudo["conclusao"],
        }
        dados["modelo_nao_configurado"] = False

        # Extrair imagens embutidas (paginas de fotos endoscopicas)
        if subtipo in ("eda", "colonoscopia", "endoscopia"):
            import os as _os, hashlib as _hs
            _hash  = _hs.md5(conteudo_bytes[:4096]).hexdigest()[:8]
            _pasta = _os.path.join(
                _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                "dados", "imagens",
            )
            _prefixo = f"{_hash}_{subtipo}"
            dados["imagens_extraidas"] = extrair_imagens_pdf(
                conteudo_bytes, _prefixo, _pasta
            )

    else:
        # ── Numérico ───────────────────────────────────────────
        def _prog_raw(info):
            if on_progress:
                try: on_progress(info)
                except Exception: pass

        _prog("extraindo", total_linhas, total_linhas)
        # Pretti requer caminho do arquivo para usar pdfplumber com coordenadas
        texto_para_extrator = texto_completo
        if laboratorio == "Pretti" and caminho_pdf:
            texto_para_extrator = f"__PRETTI_PATH__:{caminho_pdf}"
        resultados = extrair_resultados(texto_para_extrator, laboratorio, on_progress=_prog_raw)
        tipos = list({r["parametro"] for r in resultados if r.get("parametro")})
        dados["tipo_exame"] = ", ".join(tipos[:5]) if tipos else "Outros"
        dados["resultados"] = resultados
        dados["laudo"]      = None
        _prog("concluido", total_linhas, total_linhas, total_linhas, len(resultados))
        # Sinalizar modelo não configurado quando lab desconhecido e sem resultados
        dados["modelo_nao_configurado"] = (
            laboratorio == "Desconhecido" and len(resultados) == 0
        )

    return dados


def extrair_pdf(caminho_pdf: str) -> dict:
    from pathlib import Path
    return extrair_pdf_bytes(Path(caminho_pdf).read_bytes(), Path(caminho_pdf).name)


if __name__ == "__main__":
    import sys, json
    arquivo = sys.argv[1] if len(sys.argv) > 1 else "teste.pdf"
    r = extrair_pdf(arquivo)
    r.pop("resultado_texto")
    print(json.dumps(r, ensure_ascii=False, indent=2))