# -*- coding: utf-8 -*-
# Prontuario | extratores/extrator_prontuario.py
"""
Extrai TUDO de um prontuario hospitalar escaneado:
  internacao (com cidade/uf/objetivo), procedimentos e exames.
Processa em multiplos lotes via Claude Vision com checkpoint para retomada.
"""
import base64
import hashlib
import io
import json
import logging
import os
import threading

log = logging.getLogger(__name__)

_MODELO          = "claude-sonnet-4-6"
_BATCH_SIZE      = 6    # paginas por chamada Vision (6 e o limite seguro para tokens)
_MAX_PAGS        = 48   # limite para extracao completa (Fase 2)
_MAX_PAGS_FASE1  = 200  # Fase 1: varre todo o documento para nao perder internacoes
_API_TIMEOUT     = 60   # segundos max por lote — acima disso é sinal de erro de crédito ou rede

_SYSTEM = (
    "Voce e um extrator especializado em prontuarios hospitalares brasileiros. "
    "Analise imagens escaneadas e retorne SOMENTE JSON valido, sem markdown, sem explicacoes."
)

# ── Fase 1: apenas internacoes ────────────────────────────────────────────────

_PROMPT_FASE1 = """
Analise estas paginas de prontuario hospitalar brasileiro escaneado.
Identifique APENAS as internacoes (admissoes hospitalares) presentes neste trecho.
Retorne SOMENTE JSON valido — sem code fences, sem texto extra.

{
  "paciente_nome": "nome completo do paciente ou null",
  "internacoes": [
    {
      "hospital":          "nome do hospital (somente o hospital, sem laboratorio)",
      "cidade":            "cidade onde fica o hospital ou null",
      "uf":                "sigla do estado (SP/RJ/MG/etc) ou null",
      "data_entrada":      "YYYY-MM-DD ou null",
      "data_saida":        "YYYY-MM-DD ou null",
      "tipo":              "eletiva|urgencia|emergencia",
      "objetivo":          "tratamento|procedimento|diagnostico|emergencia",
      "leito":             "null ou numero/nome",
      "unidade":           "null ou UTI/Enfermaria/Semi-intensiva/etc",
      "convenio":          "null ou nome do plano",
      "medico_nome":       "nome completo do medico responsavel ou null",
      "medico_crm":        "null ou CRM",
      "especialidade":     "null ou especialidade",
      "cid_entrada":       "null ou codigo CID",
      "cid_entrada_desc":  "null ou descricao do CID",
      "motivo":            "motivo em 1-2 frases ou null",
      "diagnostico_saida": "null ou diagnostico de alta",
      "cid_saida":         "null ou CID de saida",
      "observacoes":       "null ou comorbidades/historico relevante"
    }
  ]
}

REGRAS GERAIS:
- Internacao = evento de ADMISSAO HOSPITALAR com ficha/boletim de entrada registrando
  data de entrada, nome do hospital e motivo/CID da internacao.
- Pode haver mais de uma internacao DIFERENTE no mesmo documento — liste todas.
- "objetivo": tratamento=internado por doenca/condicao; procedimento=internado para cirurgia/cateterismo/etc
- "tipo": eletiva=programada; urgencia=necessidade rapida mas nao imediata; emergencia=risco de vida imediato

REGRAS — data_saida (MUITO IMPORTANTE):
A data de alta raramente aparece na ficha de admissao. Procure em TODAS as fontes abaixo:
- Sumario de alta / Carta de alta / Relatorio de alta medica (campo "Data da Alta" ou "Data Saida")
- Orientacoes de pos-operatorio assinadas pelo paciente (campo "Data:" proximo a assinatura)
- Ultima evolucao medica ou de enfermagem do prontuario (data do ultimo registro)
- Guia de solicitacao de internacao preenchida (campo "Data Saida" ou "Hora Saida")
- Termo de responsabilidade de alta (data da assinatura)
- Nota fiscal ou recibo hospitalar (data de saida)
- Qualquer documento que mencione "alta hospitalar" com uma data
Use a data mais tardia encontrada entre todas essas fontes — ela representa quando o paciente
realmente saiu. Se encontrar apenas hora de saida sem data, use a data do documento mais recente.
Se nao encontrar absolutamente nenhuma indicacao de alta, retorne null.

IGNORAR COMPLETAMENTE (NAO sao internacoes):
- Resultados de exames laboratoriais (mesmo que tenham data e nome de hospital/laboratorio).
  Ex: laudo de CPK, hemograma, gasometria, troponina, creatinina — sao exames, nao admissoes.
- Laudos de laboratorio como "Carlos Chagas Laboratorio", "Laboratorio X" — sao exames.
- Notas/evolucoes de UTI ou enfermaria que descrevem o estado do paciente em datas subsequentes
  durante a MESMA internacao — nao criam uma nova internacao, apenas descrevem continuidade.
- Autorizacoes de plano/seguradora para procedimentos, diarias ou exames durante a internacao.
- Prescricoes medicas, anotacoes de enfermagem, relatorios de alta parcial.
- Se o documento mostra exames (CPK, CK-MB, creatinina, etc.) feitos em dias sequenciais
  dentro do mesmo periodo de internacao, isso e UMA internacao com varios exames, nao varias internacoes.

QUANDO RETORNAR internacoes=[]:
- Se nestas paginas nao houver nenhuma ficha/boletim de ADMISSAO hospitalar nova.
- Se so houver exames, laudos, evolucoes ou notas de continuidade de internacao existente.

NUNCA invente dados. Campo ilegivel ou ausente = null.
"""

_PROMPT = """
Analise estas paginas de prontuario hospitalar brasileiro escaneado.
Extraia TUDO que encontrar em 4 categorias.
Retorne SOMENTE JSON valido — sem code fences, sem texto extra.

{
  "paciente_nome": "nome completo do paciente ou null",
  "internacao": {
    "hospital":          "nome do hospital",
    "cidade":            "cidade onde fica o hospital ou null",
    "uf":                "sigla do estado (SP / RJ / MG / etc) ou null",
    "data_entrada":      "YYYY-MM-DD ou null",
    "data_saida":        "YYYY-MM-DD ou null",
    "objetivo":          "tratamento|procedimento|diagnostico|emergencia",
    "tipo":              "eletiva|urgencia|emergencia",
    "leito":             "null ou numero/nome",
    "unidade":           "null ou UTI/Enfermaria/Semi-intensiva/etc",
    "convenio":          "null ou nome",
    "medico_nome":       "nome completo do medico responsavel ou null",
    "medico_crm":        "null ou CRM",
    "especialidade":     "null ou especialidade",
    "cid_entrada":       "null ou codigo CID",
    "cid_entrada_desc":  "null ou descricao",
    "motivo":            "motivo em 1-2 frases ou null",
    "diagnostico_saida": "null ou diagnostico de alta",
    "cid_saida":         "null ou CID de saida",
    "observacoes":       "null ou comorbidades/historico relevante"
  },
  "procedimentos": [
    {
      "nome":        "nome do procedimento",
      "tipo":        "cirurgico|diagnostico|terapeutico|ambulatorial",
      "data":        "YYYY-MM-DD ou null",
      "hora":        "HH:MM ou null",
      "local":       "nome do hospital/sala onde foi realizado ou null",
      "anestesia":   "sem|local|sedacao|epidural|geral",
      "resultado":   "null ou descricao breve do resultado/evolucao",
      "observacoes": "null ou resumo das prescricoes de enfermagem, materiais cirurgicos utilizados e orientacoes pos-operatorias relacionadas a este procedimento"
    }
  ],
  "exames": [
    {
      "tipo_exame":    "Hemograma|Bioquimica|Coagulograma|Gasometria|ECG|Ecocardiograma|Radiografia|Urinalise|Microbiologia|Anatomia-Patologica|outro",
      "laboratorio":   "null ou nome do setor/laboratorio",
      "data_exame":    "YYYY-MM-DD ou null",
      "medico_solicit":"null ou medico solicitante",
      "resultados": [
        {
          "parametro":  "nome do parametro",
          "valor":      "valor em texto",
          "unidade":    "null ou unidade",
          "referencia": "null ou faixa de referencia"
        }
      ]
    }
  ],
  "medicamentos": [
    {
      "nome":           "nome comercial ou generico do medicamento",
      "principio_ativo":"null ou principio ativo",
      "dose":           "null ou dose (ex: 20mg, 500mg/100mL)",
      "via":            "null ou via de administracao (oral|IV|IM|SC|topica|inalatoria)",
      "frequencia":     "null ou frequencia (ex: 8/8h, 1x/dia, SOS)",
      "inicio":         "YYYY-MM-DD ou null",
      "fim":            "YYYY-MM-DD ou null",
      "indicacao":      "null ou motivo/indicacao clinica"
    }
  ],
  "outros": [
    {
      "categoria":  "evolucao|administrativo|enfermagem|dieta|orientacao|outro",
      "conteudo":   "transcricao fiel ou resumo do texto encontrado",
      "pagina":     null
    }
  ]
}

REGRAS GERAIS:
- "objetivo": tratamento=internado por doenca/condicao; procedimento=internado para fazer cirurgia/cateterismo/etc
- internacao: null se nao houver boletim/ficha de admissao nestas paginas
- NUNCA invente dados. Campo ilegivel ou ausente = null.

REGRAS — data_saida da internacao (MUITO IMPORTANTE):
A data de alta raramente aparece na ficha de admissao. Procure em TODAS as fontes:
- Sumario/carta/relatorio de alta medica (campo "Data da Alta" ou "Data Saida")
- Orientacoes de pos-operatorio assinadas pelo paciente (data proximo a assinatura)
- Ultima evolucao medica ou de enfermagem (data do ultimo registro cronologico)
- Guia de internacao preenchida (campo "Data Saida" ou "Hora Saida")
- Termo de responsabilidade de alta (data da assinatura do paciente)
- Qualquer documento que mencione "alta hospitalar" com uma data
Use a data mais tardia encontrada — representa quando o paciente realmente saiu.
Se nao encontrar nenhuma indicacao de alta, retorne null.

REGRAS — procedimentos:
- INCLUIR: cirurgias (inclusive pequenas), cateterismos, angioplastias, angiografias, endoscopias,
  colonoscopias, RTU (resseccao transuretral), drenagens, cardioversoes, ablacoes, implantes
  (marca-passo/stent/protese), biopsia cirurgica, traqueostomia, intubacao orotraqueal de
  emergencia, cardioversao eletrica.
- No campo "observacoes" do procedimento, resumir (em texto livre):
    * Prescricoes de enfermagem diretamente relacionadas ao procedimento (ex: cuidados com SVD
      pos-RTU, controle de diurese, curativo da ferida operatoria, orientacoes de pós-operatorio).
    * Materiais estereis utilizados na sala cirurgica listados em etiquetas de rastreabilidade
      (ex: Evacuador de Ellik, Uromaster, alca de resseccao — indicam tipo e porte do procedimento).
    * Orientacoes de alta cirurgica assinadas pelo paciente.
    * Diagnosticos de enfermagem registrados no pos-operatorio imediato.
- IGNORAR como procedimento separado: monitoramento continuo (ECG rotina, oximetria, PANI),
  puncao venosa periferica, coleta de sangue, banho, higiene oral/intima, curativo rotineiro,
  mobilizacao, mudanca de decubito, fisioterapia respiratoria, nebulizacao, dieta enteral,
  administracao de medicamentos (vai em medicamentos), plantao/visita medica.
  EXCECAO: sondagem vesical de demora (SVD) instalada como parte de procedimento cirurgico
  nao e um procedimento separado — vai em observacoes do procedimento principal.
- ECG isolado e exames complementares (radiografia, laboratorio, ecocardiograma) vao em
  "exames", NAO em procedimentos.

REGRAS — exames:
- [] se nao houver resultados de laboratorio, ECG, eco, rx, cultura, patologia.
- Agrupe MESMA data + MESMO tipo num unico objeto exame.

REGRAS — medicamentos:
- Liste todos os remedios prescritos ou administrados durante a internacao.
- Inclua antibioticos, anticoagulantes, vasoativos, analgesicos, etc.
- Ignore solucoes de lavagem/limpeza sem principio ativo (ex: SF para curativo).

REGRAS — outros (captura tudo que nao se encaixa nas categorias acima):
- evolucao: anotacoes de evolucao medica ou de enfermagem (relatos de turno, avaliacao clinica diaria).
- administrativo: guias de internacao, termos de consentimento, dados de convenio, autorizacoes.
- enfermagem: prescricoes de enfermagem nao ligadas a um procedimento especifico, escalas (Braden, Fugulin, Glasgow, Morse), diagnosticos de enfermagem.
- dieta: prescricoes dieticas, nutricao enteral/parenteral, restricoes alimentares.
- orientacao: orientacoes de alta (medicamentos para casa, retorno, restricoes), orientacoes ao paciente/familiar.
- outro: qualquer conteudo nao classificavel nas categorias acima que tenha valor clinico ou historico.
- Se uma pagina contem apenas carimbos, assinaturas ou dados identicos ao que ja foi capturado, pode omitir.
- Mantenha o conteudo fiel ao original — nao resuma desnecessariamente.
- [] se absolutamente nada restar apos classificar nas 4 categorias principais.
"""


# ── Prompt de revisao (segunda checagem) ──────────────────────────────────────

_PROMPT_REVISAO = """
Voce esta revisando um prontuario hospitalar brasileiro ja parcialmente processado.
Os itens abaixo JA FORAM registrados no sistema — NAO os repita.

JA REGISTRADO:
{ja_registrado}

Analise TODAS as paginas do documento e liste APENAS o que NAO foi registrado acima
e que tenha relevancia clinica para o historico do paciente.

Retorne SOMENTE JSON valido — sem code fences, sem texto extra.

{{
  "ignorados": [
    {{
      "categoria":   "procedimento|exame|medicamento|observacao|outro",
      "titulo":      "nome curto do item (max 60 chars)",
      "descricao":   "detalhes do item — data, valor, dose, etc. (max 200 chars)",
      "data":        "YYYY-MM-DD ou null",
      "sugestao_campo": "onde incluir no sistema: procedimentos|exames|medicamentos|observacoes_internacao"
    }}
  ]
}}

INCLUIR como ignorado:
- Procedimentos, cirurgias ou intervencoes nao listadas acima
- Exames com resultados nao listados acima
- Medicamentos prescritos ou administrados nao listados acima
- Diagnosticos de enfermagem relevantes nao capturados
- Complicacoes, intercorrencias ou eventos clinicos nao registrados
- Orientacoes de alta relevantes nao capturadas

NAO INCLUIR:
- Itens administrativos (autorizacoes de plano, termos de responsabilidade)
- Itens de rastreabilidade de materiais cirurgicos ja cobertos pelo procedimento
- Rotinas de monitoramento sem resultado (pressao de horario, saturacao, etc.)
- Itens ilegíveis ou sem informacao clinica util
- Qualquer item ja presente em JA REGISTRADO

Se nao houver nada novo, retorne: {{"ignorados": []}}
NUNCA invente dados. Campo ilegivel ou ausente = null.
"""


_PROMPT_RECLASSIFICAR = """
Voce recebeu o conteudo dos campos "motivo" e "observacoes" de uma internacao hospitalar
brasileira. Esses campos foram preenchidos de forma livre e misturam informacoes de
categorias diferentes. Sua tarefa e separar e organizar esses dados em 6 categorias.

TEXTO RECEBIDO:
---
{texto}
---

Retorne SOMENTE JSON valido — sem code fences, sem texto extra.

{{
  "motivo":            "1-2 frases descrevendo o motivo clinico da internacao, sem medicamentos nem escalas",
  "cid_entrada":       "codigo CID principal de entrada (ex: I10) ou null",
  "cid_entrada_desc":  "descricao do CID de entrada ou null",
  "diagnostico_saida": "diagnostico de alta em texto livre ou null",
  "cid_saida":         "codigo CID de saida ou null",
  "observacoes":       "comorbidades e historico clinico relevante (HAS, DM, DPOC, etc.) — SEM medicamentos, SEM escalas, SEM dados administrativos",
  "medicamentos": [
    {{
      "nome":       "nome do medicamento (comercial ou generico)",
      "dose":       "dose e unidade ou null",
      "frequencia": "frequencia de uso ou null",
      "via":        "oral|IV|IM|SC|topica|inalatoria ou null"
    }}
  ],
  "escalas": [
    {{
      "nome":  "Braden|Fugulin|Glasgow|Morse|Waterlow|Risco de Queda|Risco de Flebite|Risco de Tromboembolismo|outro",
      "valor": "pontuacao numerica ou classificacao textual (ex: 14 pontos, Alto Risco)",
      "data":  "YYYY-MM-DD ou null"
    }}
  ],
  "diagnosticos_enfermagem": [
    {{
      "nome":      "nome do diagnostico de enfermagem (ex: Integridade da pele prejudicada)",
      "descricao": "descricao ou contexto adicional ou null",
      "data":      "YYYY-MM-DD ou null"
    }}
  ]
}}

REGRAS:
- "motivo": apenas o motivo imediato da internacao (ex: "Urgencia hipertensiva com cefaleia intensa")
- "observacoes": so comorbidades e historico clinico — jamais medicamentos, escalas ou dados administrativos
- "medicamentos": TODA medicacao citada — mesmo que ja esteja em outro campo. Inclui antibioticos, anticoagulantes, diureticos, anti-hipertensivos, analgésicos, suplementos
- "escalas": classificacoes clinicas/risco com pontuacao — Braden (pele), Fugulin (carga enfermagem), Glasgow (consciencia), Morse/risco de queda, risco de flebite, risco de TVP/tromboembolismo, etc.
- "diagnosticos_enfermagem": diagnosticos NANDA ou similares registrados pela equipe de enfermagem
- IGNORAR completamente: numero de prontuario, matricula, CPF, COREN, registro hospitalar, dados administrativos
- CIDs: extraia so se mencionado explicitamente; nunca invente
- Se um campo nao tem informacao: retorne null (listas: [])
- NUNCA repita a mesma informacao em dois campos
"""


def reclassificar_texto_internacao(texto: str) -> dict:
    """
    Recebe texto livre dos campos motivo+observacoes de uma internacao
    e retorna dict com campos separados: motivo, cid_entrada, diagnostico_saida,
    observacoes (limpas), medicamentos (lista).
    """
    try:
        from utils.claudia_engine import get_client
    except Exception as ex:
        raise RuntimeError(f"Cliente Claude indisponivel: {ex}") from ex

    client = get_client()
    prompt = _PROMPT_RECLASSIFICAR.format(texto=texto.strip())

    resp = client.messages.create(
        model=_MODELO,
        max_tokens=1024,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        timeout=60,
    )
    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        partes = raw.split("```")
        raw    = partes[1] if len(partes) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log.error("[RECLASSIFICAR] JSON invalido: %s", raw[:300])
        return {}


def extrair_ignorados(
    pdf_bytes: bytes,
    ja_registrado: dict,
    on_progress=None,
    batch_size: int = _BATCH_SIZE,
) -> list[dict]:
    """
    Segunda checagem: extrai itens clinicamente relevantes que nao foram
    capturados na primeira extracao.

    ja_registrado: dict com chaves 'procedimentos', 'exames', 'medicamentos'
                   cada uma lista de strings descrevendo o que ja existe.

    Retorna lista de dicts: [{categoria, titulo, descricao, data, sugestao_campo}]
    """
    def _prog(msg):
        if on_progress:
            on_progress(msg)

    _prog("Convertendo PDF...")
    imgs = _pdf_para_imagens_b64(pdf_bytes, max_pags=_MAX_PAGS)
    total = len(imgs)
    _prog(f"{total} paginas carregadas.")

    # monta texto descritivo do que ja foi registrado
    linhas = []
    for proc in ja_registrado.get("procedimentos") or []:
        linhas.append(f"  PROCEDIMENTO: {proc}")
    for ex in ja_registrado.get("exames") or []:
        linhas.append(f"  EXAME: {ex}")
    for med in ja_registrado.get("medicamentos") or []:
        linhas.append(f"  MEDICAMENTO: {med}")
    if not linhas:
        linhas.append("  (nenhum item registrado ainda)")
    ja_txt = "\n".join(linhas)

    prompt = _PROMPT_REVISAO.format(ja_registrado=ja_txt)

    ignorados = []
    n_lotes = (total + batch_size - 1) // batch_size

    for lote_idx in range(n_lotes):
        ini  = lote_idx * batch_size
        fim  = min(ini + batch_size, total)
        imgs_lote = imgs[ini:fim]
        _prog(f"Revisando lote {lote_idx+1}/{n_lotes} (pags {ini+1}-{fim})...")

        try:
            resultado = _chamar_visao_generica(imgs_lote, prompt, max_tokens=2048)
            for item in resultado.get("ignorados") or []:
                titulo = (item.get("titulo") or "").strip()
                if titulo:
                    ignorados.append(item)
        except Exception as err:
            log.warning("[REVISAO] lote %d falhou: %s", lote_idx+1, err)
            continue

    # dedup por titulo
    vistos = set()
    unicos = []
    for item in ignorados:
        t = item.get("titulo","").strip().lower()
        if t and t not in vistos:
            vistos.add(t)
            unicos.append(item)

    _prog(f"Revisao concluida: {len(unicos)} item(ns) encontrado(s).")
    return unicos


def _chamar_visao_generica(imagens_b64: list[str], prompt: str,
                            max_tokens: int = 2048) -> dict:
    """Chama Claude Vision com prompt customizado. Retorna dict do JSON."""
    try:
        from utils.claudia_engine import get_client
    except Exception as ex:
        raise RuntimeError(f"Cliente Claude indisponivel: {ex}") from ex

    client  = get_client()
    content = [
        {"type": "image",
         "source": {"type": "base64", "media_type": "image/jpeg", "data": img}}
        for img in imagens_b64
    ]
    content.append({"type": "text", "text": prompt})

    resp = client.messages.create(
        model=_MODELO,
        max_tokens=max_tokens,
        system=_SYSTEM,
        messages=[{"role": "user", "content": content}],
        timeout=_API_TIMEOUT,
    )
    texto = resp.content[0].text.strip()
    if texto.startswith("```"):
        partes = texto.split("```")
        texto  = partes[1] if len(partes) > 1 else texto
        if texto.startswith("json"):
            texto = texto[4:]
    texto = texto.strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        log.error("[REVISAO] JSON invalido: %s", texto[:300])
        return {}


# ── Checkpoint ─────────────────────────────────────────────────────────────────

def _hash_pdf(pdf_bytes: bytes) -> str:
    return hashlib.md5(pdf_bytes).hexdigest()[:12]


def _checkpoint_path(pdf_hash: str) -> str:
    pasta = os.path.join(os.path.dirname(__file__), "..", "temp")
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, f"extracao_{pdf_hash}.json")


def verificar_checkpoint(pdf_bytes: bytes) -> dict | None:
    """Retorna checkpoint salvo para este PDF, ou None se nao houver."""
    cp = _checkpoint_path(_hash_pdf(pdf_bytes))
    if os.path.exists(cp):
        try:
            with open(cp, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def limpar_checkpoint(pdf_bytes: bytes):
    cp = _checkpoint_path(_hash_pdf(pdf_bytes))
    try:
        os.remove(cp)
    except Exception:
        pass


def _salvar_checkpoint(pdf_hash: str, estado: dict):
    with open(_checkpoint_path(pdf_hash), "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


# ── Erro de credito com checkpoint ────────────────────────────────────────────

class SemCreditosError(Exception):
    def __init__(self, msg: str, checkpoint_path: str = ""):
        super().__init__(msg)
        self.checkpoint_path = checkpoint_path


# ── Fase 1: extrair apenas internacoes ────────────────────────────────────────

def extrair_internacoes_pdf(
    pdf_bytes: bytes,
    nome_arquivo: str = "",
    on_progress=None,
    max_pags: int = _MAX_PAGS_FASE1,
    batch_size: int = _BATCH_SIZE,
) -> dict:
    """
    Fase 1: le o PDF e localiza TODAS as internacoes.
    Nao extrai procedimentos, exames ou medicamentos.

    Retorna:
    {
        "paciente_nome":       str | None,
        "internacoes":         list[dict],   # pode ser mais de uma
        "paginas_processadas": int,
        "documento_local":     str,
    }
    """
    def _prog(msg):
        if on_progress:
            on_progress(msg)

    _prog("Convertendo PDF em imagens...")
    todas_imgs = _pdf_para_imagens_b64(pdf_bytes, max_pags=max_pags)
    total      = len(todas_imgs)
    _prog(f"{total} paginas carregadas.")

    n_lotes       = (total + batch_size - 1) // batch_size
    paciente_nome = None
    internacoes   = []
    _chaves_vistas = set()   # (hospital_key, data_entrada) para dedup entre lotes

    for lote_idx in range(n_lotes):
        ini  = lote_idx * batch_size
        fim  = min(ini + batch_size, total)
        imgs = todas_imgs[ini:fim]
        _prog(f"Lote {lote_idx+1}/{n_lotes}  —  pags {ini+1}-{fim}...")

        try:
            resultado = _chamar_visao_fase1(imgs, on_progress=on_progress)
        except SemCreditosError:
            raise  # sem crédito — para imediatamente
        except TimeoutError:
            raise  # timeout — avisa a tela, não tenta mais lotes
        except Exception as err:
            log.warning("[FASE1] lote %d falhou: %s", lote_idx+1, err)
            continue

        if paciente_nome is None and resultado.get("paciente_nome"):
            paciente_nome = resultado["paciente_nome"]

        for inter in resultado.get("internacoes") or []:
            hosp  = _normalizar_hospital(inter.get("hospital") or "")
            d_ent = (inter.get("data_entrada") or "").strip()
            if not hosp:
                continue
            chave = (hosp, d_ent)
            if chave in _chaves_vistas:
                # Mesmo hospital+data ja visto — mescla campos nulos com dados novos
                for i, ex in enumerate(internacoes):
                    ex_chave = (
                        _normalizar_hospital(ex.get("hospital") or ""),
                        (ex.get("data_entrada") or "").strip(),
                    )
                    if ex_chave == chave:
                        internacoes[i] = _mesclar_internacao(ex, inter)
                        break
            else:
                _chaves_vistas.add(chave)
                internacoes.append(inter)

    _prog("Extracao de internacoes concluida.")
    return {
        "paciente_nome":       paciente_nome,
        "internacoes":         internacoes,
        "paginas_processadas": total,
        "documento_local":     nome_arquivo,
    }


def _normalizar_hospital(nome: str) -> str:
    """Normaliza nome de hospital para comparacao fuzzy entre lotes."""
    import unicodedata, re
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    s = s.lower()
    # remove sufixos juridicos e siglas comuns
    for rem in (" sa", " s/a", " ltda", " me", " eireli", " hospital"):
        s = s.replace(rem, "")
    # remove laboratorio do nome (pode aparecer como "Hospital SA / Carlos Chagas Lab")
    s = re.sub(r"/?\s*carlos chagas laboratorio.*", "", s)
    s = re.sub(r"/?\s*laboratorio\s+\w+", "", s)
    # compacta espacos e pontuacao
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s[:30]


def _mesclar_internacao(base: dict, nova: dict) -> dict:
    """Preenche campos nulos de 'base' com valores de 'nova'.
    Para data_saida: usa a mais tardia entre as duas (a alta real pode
    aparecer em lote posterior ao da ficha de admissao).
    """
    result = dict(base)
    for k, v in nova.items():
        if k == "data_saida":
            # prefere a data mais tardia
            d_base = result.get("data_saida")
            if v and (not d_base or str(v) > str(d_base)):
                result["data_saida"] = v
        elif result.get(k) is None and v is not None:
            result[k] = v
    return result


def _chamar_visao_fase1(imagens_b64: list[str], on_progress=None) -> dict:
    """Chama Claude Vision com o prompt de Fase 1 (so internacoes)."""
    try:
        from utils.claudia_engine import get_client
    except Exception as ex:
        raise RuntimeError(f"Cliente Claude indisponivel: {ex}") from ex

    try:
        from utils.api_checker import exigir_creditos as _exigir_cred
        _exigir_cred(get_client)
    except Exception as _ex_cred:
        if type(_ex_cred).__name__ == "SemCreditosError":
            raise SemCreditosError(str(_ex_cred)) from _ex_cred

    client  = get_client()
    content = [
        {"type": "image",
         "source": {"type": "base64", "media_type": "image/jpeg", "data": img}}
        for img in imagens_b64
    ]
    content.append({"type": "text", "text": _PROMPT_FASE1})

    _stop_hb  = threading.Event()
    _segundos = [0]
    def _heartbeat():
        while not _stop_hb.wait(15):
            _segundos[0] += 15
            if on_progress:
                on_progress(f"Aguardando Claude Vision... {_segundos[0]}s")
    hb = threading.Thread(target=_heartbeat, daemon=True)
    hb.start()

    try:
        resp = client.messages.create(
            model=_MODELO,
            max_tokens=2048,
            system=_SYSTEM,
            messages=[{"role": "user", "content": content}],
            timeout=_API_TIMEOUT,
        )
    except Exception as ex:
        _stop_hb.set()
        ex_str = str(ex).lower()
        if "credit balance" in ex_str or "insufficient" in ex_str:
            try:
                from utils.api_checker import invalidar_cache
                invalidar_cache()
            except Exception:
                pass
            raise SemCreditosError("Sem creditos na API Claude") from ex
        if "request too large" in ex_str or "max 32mb" in ex_str or "413" in ex_str:
            raise RuntimeError(
                "PDF com imagens muito grandes para a API.\n"
                "Tente um PDF menor ou com menos paginas por vez."
            ) from ex
        if "timeout" in ex_str or "timed out" in ex_str:
            raise TimeoutError(
                f"API Claude nao respondeu em {_API_TIMEOUT}s."
            ) from ex
        raise
    finally:
        _stop_hb.set()

    texto = resp.content[0].text.strip()
    if texto.startswith("```"):
        partes = texto.split("```")
        texto  = partes[1] if len(partes) > 1 else texto
        if texto.startswith("json"):
            texto = texto[4:]
    texto = texto.strip()

    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as ex:
        log.error("[FASE1] JSON invalido: %s", texto[:300])
        dados = {}

    dados.setdefault("paciente_nome", None)
    dados.setdefault("internacoes",   [])
    return dados


# ── Extrator principal ────────────────────────────────────────────────────────

def extrair_prontuario_completo(
    pdf_bytes: bytes,
    nome_arquivo: str = "",
    on_progress=None,
    max_pags: int = _MAX_PAGS,
    batch_size: int = _BATCH_SIZE,
    retomar_checkpoint: dict | None = None,
) -> dict:
    """
    Extrai internacao + procedimentos + exames de prontuario hospitalar escaneado.

    - Salva checkpoint apos cada lote para retomada se credito acabar.
    - Se retomar_checkpoint for passado, continua de onde parou.
    - Levanta SemCreditosError (com .checkpoint_path) se credito acabar no meio.

    Retorna:
    {
        "internacao":          dict (ou {}),
        "procedimentos":       list[dict],
        "exames":              list[dict],
        "paciente_nome":       str|None,
        "documento_local":     str,
        "paginas_processadas": int,
    }
    """
    def _prog(msg):
        if on_progress:
            on_progress(msg)

    pdf_hash = _hash_pdf(pdf_bytes)

    # ── Restaurar estado do checkpoint (retomada) ──────────────────
    if retomar_checkpoint:
        internacao    = retomar_checkpoint.get("internacao")
        paciente_nome = retomar_checkpoint.get("paciente_nome")
        procedimentos = retomar_checkpoint.get("procedimentos", [])
        exames        = retomar_checkpoint.get("exames", [])
        medicamentos  = retomar_checkpoint.get("medicamentos", [])
        _proc_nomes   = set(retomar_checkpoint.get("proc_nomes", []))
        _med_nomes    = set(retomar_checkpoint.get("med_nomes", []))
        proximo_lote  = retomar_checkpoint.get("proximo_lote", 0)
        _prog(f"Retomando do lote {proximo_lote + 1}...")
    else:
        internacao    = None
        paciente_nome = None
        procedimentos = []
        exames        = []
        medicamentos  = []
        _proc_nomes   = set()
        _med_nomes    = set()
        proximo_lote  = 0

    # ── Converter PDF em imagens ───────────────────────────────────
    _prog("Convertendo PDF em imagens...")
    todas_imgs = _pdf_para_imagens_b64(pdf_bytes, max_pags=max_pags)
    total      = len(todas_imgs)
    _prog(f"{total} paginas carregadas.")

    n_lotes = (total + batch_size - 1) // batch_size

    for lote_idx in range(proximo_lote, n_lotes):
        ini  = lote_idx * batch_size
        fim  = min(ini + batch_size, total)
        imgs = todas_imgs[ini:fim]
        _prog(f"Lote {lote_idx+1}/{n_lotes}  —  pags {ini+1}-{fim}...")

        try:
            resultado = _chamar_visao(imgs, on_progress=on_progress)
        except SemCreditosError as ex:
            # Salvar checkpoint e re-propagar com path
            _salvar_checkpoint(pdf_hash, {
                "internacao":    internacao,
                "paciente_nome": paciente_nome,
                "procedimentos": procedimentos,
                "exames":        exames,
                "medicamentos":  medicamentos,
                "proc_nomes":    list(_proc_nomes),
                "med_nomes":     list(_med_nomes),
                "proximo_lote":  lote_idx,
                "total_paginas": total,
                "batch_size":    batch_size,
                "nome_arquivo":  nome_arquivo,
                "criado_em":     _agora(),
            })
            cp = _checkpoint_path(pdf_hash)
            _prog(f"Credito insuficiente. Progresso salvo — lote {lote_idx+1}/{n_lotes}.")
            raise SemCreditosError(str(ex), checkpoint_path=cp) from ex
        except Exception as err:
            log.warning("[PRONTUARIO] lote %d falhou: %s", lote_idx+1, err)
            continue

        # paciente
        if paciente_nome is None and resultado.get("paciente_nome"):
            paciente_nome = resultado["paciente_nome"]

        # internacao — primeiro lote com dados concretos
        if internacao is None:
            ri = resultado.get("internacao")
            if ri and (ri.get("hospital") or ri.get("data_entrada") or ri.get("motivo")):
                internacao = ri

        # procedimentos — dedup por nome
        for p in resultado.get("procedimentos") or []:
            nome_p = (p.get("nome") or "").strip().lower()
            if nome_p and nome_p not in _proc_nomes:
                _proc_nomes.add(nome_p)
                procedimentos.append(p)

        # exames
        for ex in resultado.get("exames") or []:
            if ex.get("resultados"):
                exames.append(ex)

        # medicamentos — dedup por nome
        for med in resultado.get("medicamentos") or []:
            nome_m = (med.get("nome") or "").strip().lower()
            if nome_m and nome_m not in _med_nomes:
                _med_nomes.add(nome_m)
                medicamentos.append(med)

        # Salvar checkpoint apos cada lote (progresso incremental)
        _salvar_checkpoint(pdf_hash, {
            "internacao":    internacao,
            "paciente_nome": paciente_nome,
            "procedimentos": procedimentos,
            "exames":        exames,
            "medicamentos":  medicamentos,
            "proc_nomes":    list(_proc_nomes),
            "med_nomes":     list(_med_nomes),
            "proximo_lote":  lote_idx + 1,
            "total_paginas": total,
            "batch_size":    batch_size,
            "nome_arquivo":  nome_arquivo,
            "criado_em":     _agora(),
        })

    _prog("Extracao concluida.")
    # Checkpoint cumprido — pode ser limpo pelo chamador apos salvar no banco
    return {
        "internacao":          internacao or {},
        "procedimentos":       procedimentos,
        "exames":              exames,
        "medicamentos":        medicamentos,
        "paciente_nome":       paciente_nome,
        "documento_local":     nome_arquivo,
        "paginas_processadas": total,
        "_pdf_hash":           pdf_hash,
    }


# ── Helpers internos ───────────────────────────────────────────────────────────

def _agora() -> str:
    import datetime
    return datetime.datetime.now().isoformat(timespec="seconds")


_IMG_MAX_SIDE  = 1568   # pixels -- Claude Vision aceita ate 1568px no lado maior
_IMG_QUALITY   = 72    # JPEG quality -- suficiente para OCR de texto impresso
_IMG_MAX_BYTES = 4_500_000  # 4.5 MB por imagem (base64 ~6 MB) -- margem para 6 imgs/lote

def _pdf_para_imagens_b64(pdf_bytes: bytes, max_pags: int = _MAX_PAGS) -> list[str]:
    try:
        import pypdfium2 as _pdfium
    except ImportError:
        raise RuntimeError("pypdfium2 nao instalado — execute: pip install pypdfium2")

    doc  = _pdfium.PdfDocument(pdf_bytes)
    imgs = []
    try:
        for i in range(min(max_pags, len(doc))):
            bitmap  = doc[i].render(scale=1.5)
            pil_img = bitmap.to_pil()

            # Redimensiona se necessario para nao exceder o limite da API
            w, h = pil_img.size
            lado_maior = max(w, h)
            if lado_maior > _IMG_MAX_SIDE:
                fator   = _IMG_MAX_SIDE / lado_maior
                pil_img = pil_img.resize(
                    (int(w * fator), int(h * fator)),
                    resample=pil_img.Resampling.LANCZOS
                    if hasattr(pil_img, "Resampling") else 1,
                )

            # Comprime com qualidade reduzida; se ainda grande, comprime mais
            qualidade = _IMG_QUALITY
            for _ in range(3):
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=qualidade, optimize=True)
                if buf.tell() <= _IMG_MAX_BYTES or qualidade <= 40:
                    break
                qualidade -= 15

            imgs.append(base64.b64encode(buf.getvalue()).decode())
    finally:
        doc.close()
    return imgs


def _chamar_visao(imagens_b64: list[str], on_progress=None) -> dict:
    try:
        from utils.claudia_engine import get_client
    except Exception as ex:
        raise RuntimeError(f"Cliente Claude indisponivel: {ex}") from ex

    try:
        from utils.api_checker import exigir_creditos as _exigir_cred
        _exigir_cred(get_client)
    except Exception as _ex_cred:
        if type(_ex_cred).__name__ == "SemCreditosError":
            raise SemCreditosError(str(_ex_cred)) from _ex_cred

    client  = get_client()
    content = [
        {"type": "image",
         "source": {"type": "base64", "media_type": "image/jpeg", "data": img}}
        for img in imagens_b64
    ]
    content.append({"type": "text", "text": _PROMPT})

    # heartbeat: atualiza progresso a cada 15s enquanto API processa
    _stop_hb  = threading.Event()
    _segundos = [0]
    def _heartbeat():
        while not _stop_hb.wait(15):
            _segundos[0] += 15
            if on_progress:
                on_progress(f"Aguardando Claude Vision... {_segundos[0]}s")
    hb = threading.Thread(target=_heartbeat, daemon=True)
    hb.start()

    try:
        resp = client.messages.create(
            model=_MODELO,
            max_tokens=4096,
            system=_SYSTEM,
            messages=[{"role": "user", "content": content}],
            timeout=_API_TIMEOUT,
        )
    except Exception as ex:
        _stop_hb.set()
        ex_str = str(ex).lower()
        if "credit balance" in ex_str:
            raise SemCreditosError("Sem creditos na API Claude") from ex
        if "request too large" in ex_str or "max 32mb" in ex_str or "413" in ex_str:
            raise RuntimeError(
                "PDF com imagens muito grandes para a API.\n"
                "Tente um PDF menor ou com menos paginas por vez."
            ) from ex
        if "timeout" in ex_str or "timed out" in ex_str:
            raise TimeoutError(
                f"API Claude nao respondeu em {_API_TIMEOUT}s. "
                "Verifique a conexao e tente novamente."
            ) from ex
        raise
    finally:
        _stop_hb.set()

    texto = resp.content[0].text.strip()
    if texto.startswith("```"):
        partes = texto.split("```")
        texto  = partes[1] if len(partes) > 1 else texto
        if texto.startswith("json"):
            texto = texto[4:]
    texto = texto.strip()

    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as ex:
        log.error("[PRONTUARIO] JSON invalido: %s", texto[:300])
        raise ValueError(f"Claude retornou JSON invalido: {ex}") from ex

    dados.setdefault("paciente_nome", None)
    dados.setdefault("internacao",    None)
    dados.setdefault("procedimentos", [])
    dados.setdefault("exames",        [])
    dados.setdefault("medicamentos",  [])
    return dados
