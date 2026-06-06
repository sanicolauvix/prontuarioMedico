# -*- coding: utf-8 -*-
"""
grupos_exame_seed.py
Cria os 20 grupos de exames e vincula os 209 exames existentes.

Executar: python dados/grupos_exame_seed.py
Ou chamar: from dados.grupos_exame_seed import popular_grupos; popular_grupos()
"""

import sqlite3
import logging
from pathlib import Path

DB_PATH = Path(__file__).parent / "prontuario.db"

# ══════════════════════════════════════════════════════════════════════════════
# GRUPOS — 20 grupos em 3 tipos
# ══════════════════════════════════════════════════════════════════════════════

GRUPOS = [
    # ── SANGUE ────────────────────────────────────────────────────────────────
    (1,  "Hematologia",               "Células do sangue — hemograma, série vermelha, branca e plaquetas",         "sangue",  "bloodtype_rounded",             1),
    (2,  "Bioquímica Metabólica",     "Metabolismo de glicose, lipídios e proteínas",                              "sangue",  "science_rounded",               2),
    (3,  "Função de Órgãos",          "Marcadores de função renal, hepática, pancreática e cardíaca",              "sangue",  "favorite_rounded",              3),
    (4,  "Imunidade e Inflamação",    "PCR, VHS, sorologias e marcadores de infecção e resposta imune",            "sangue",  "shield_rounded",                4),
    (5,  "Hormônios e Endocrinologia","Tireoide, hormônios sexuais, adrenais e hipofisários",                      "sangue",  "psychology_rounded",            5),
    (6,  "Vitaminas e Micronutrientes","Vitaminas (D, B12, folato) e minerais (ferro, zinco, magnésio)",           "sangue",  "nutrition_rounded",             6),
    (7,  "Coagulação e Hemostasia",   "TAP, INR, TTPa, D-Dímero e fatores de coagulação",                         "sangue",  "water_drop_rounded",            7),
    (8,  "Marcadores Tumorais",       "PSA, CEA, CA 19-9, AFP e outros marcadores oncológicos",                    "sangue",  "biotech_rounded",               8),
    (9,  "Urina e Líquidos Corporais","EAS, proteinúria, microalbuminúria, LCR e líquido pleural",                 "sangue",  "opacity_rounded",               9),
    # ── IMAGEM ────────────────────────────────────────────────────────────────
    (10, "Radiologia Convencional",   "Radiografias (RX) de tórax, ossos e abdômen",                              "imagem",  "x_ray_rounded",                10),
    (11, "Ultrassonografia",          "US abdominal, pélvica, tireoide, vascular (Doppler)",                       "imagem",  "sensors_rounded",              11),
    (12, "Tomografia Computadorizada","TC de crânio, tórax, abdômen e pelve",                                      "imagem",  "computer_rounded",             12),
    (13, "Ressonância Magnética",     "RM de crânio, coluna, articulações e abdômen",                              "imagem",  "radio_button_checked_rounded", 13),
    (14, "Medicina Nuclear",          "Cintilografia óssea, tireoidiana e PET-CT",                                 "imagem",  "blur_circular_rounded",        14),
    (15, "Cardiologia de Imagem",     "Ecocardiograma, MAPA de pressão, Holter e cintilografia cardíaca",          "imagem",  "monitor_heart_rounded",        15),
    (16, "Endoscopia",                "EDA, colonoscopia, retossigmoidoscopia e broncoscopia",                     "imagem",  "visibility_rounded",           16),
    # ── OUTROS ────────────────────────────────────────────────────────────────
    (17, "Funcionais",                "ECG, espirometria, polissonografia e testes funcionais",                    "outros",  "timeline_rounded",             17),
    (18, "Anatomopatológico",         "Biópsia, histopatológico, citologia e imuno-histoquímica",                  "outros",  "microscope_rounded",           18),
    (19, "Microbiologia",             "Culturas, antibiograma, PCR microbiológico e parasitologia",                "outros",  "coronavirus_rounded",          19),
    (20, "Genética",                  "Cariótipo, painel genético, teste BRCA e sequenciamento",                   "outros",  "dna_rounded",                  20),
]

# ══════════════════════════════════════════════════════════════════════════════
# VÍNCULO — nome_oficial → grupo_id
# Cobre os 209 exames do banco
# ══════════════════════════════════════════════════════════════════════════════

VINCULOS = {
    # ── 1. HEMATOLOGIA ────────────────────────────────────────────────────────
    1: [
        "Hemácias", "Hemoglobina", "Hematócrito", "VCM", "HCM", "CHCM", "RDW",
        "Leucócitos", "Neutrófilos Segmentados", "Neutrófilos Bastonetes",
        "Linfócitos Típicos", "Eosinófilos", "Basófilos", "Monócitos",
        "Plaquetas", "VPM", "Volume Plaquetário Médio (MPV)", "MPV",
        "Reticulócitos", "VHS",
        # nomes antigos / alternativos
        "Hemacias", "Leucocitos", "Linfocitos tipicos", "Eosinofilos",
        "Basofilos", "Monocitos", "Bastonetes", "Segmentados",
        "V.C.M", "H.C.M", "C.H.C.M", "R.D.W", "M.P.V",
        # nomes gerados pelo seed expandido
        "Eritrocitos", "Hematocrito",
        "Volume Corpuscular Medio (VCM)", "Volume Corpuscular Médio (VCM)",
        "Hemoglobina Corpuscular Media (HCM)", "Hemoglobina Corpuscular Média (HCM)",
        "Concentracao de Hemoglobina Corpuscular Media (CHCM)",
        "Concentração de Hemoglobina Corpuscular Média (CHCM)",
        "Razão Neutrófilos/Linfócitos (NLR)", "NLR",
        "Linfócitos Atípicos",
        "Velocidade de Hemossedimentação (VHS)",
        "Hemograma Completo - Eritrócitos", "Leucócitos Totais",
        "Capacidade Total de Ligação do Ferro", "Capacidade Total de Fixação do Ferro",
    ],

    # ── 2. BIOQUÍMICA METABÓLICA ──────────────────────────────────────────────
    2: [
        "Glicemia de Jejum", "Glicose em Jejum", "Glicemia Basal",
        "Hemoglobina Glicada (HbA1c)", "Insulina Basal", "Insulina",
        "Frutosamina", "HOMA-IR", "Glicemia 1h Pós-Dextrosol",
        "Glicemia 2h Pós-Dextrosol", "Glicemia Média Estimada",
        "Colesterol Total", "Colesterol HDL", "Colesterol LDL",
        "Colesterol VLDL", "Colesterol Não-HDL", "Triglicerídeos",
        "Apolipoproteína B", "Apolipoproteína A-I", "Lipoproteína (a)",
        "Proteínas Totais", "Albumina", "Globulinas",
        # nomes alternativos
        "GLICOSE", "GLICEMIA", "TRIGLICERIDEOS",
        "COLESTEROL TOTAL", "COLESTEROL HDL", "COLESTEROL LDL",
        "COLESTEROL - HDL", "COLESTEROL -LDL", "COLESTEROL VLDL",
        "HDL-Colesterol", "LDL-Colesterol", "VLDL-Colesterol",
        "Hemoglobina Glicada", "Glicemia Pós-Prandial",
    ],

    # ── 3. FUNÇÃO DE ÓRGÃOS ───────────────────────────────────────────────────
    3: [
        # Renal
        "Creatinina", "Ureia", "Ácido Úrico", "eRFG (CKD-EPI)", "eRFG",
        "Cistatina C", "Microalbuminúria 24h", "Relação Albumina/Creatinina",
        "BUN (Nitrogênio Ureico)",
        # Hepático
        "TGO (AST)", "TGP (ALT)", "GGT", "Fosfatase Alcalina",
        "Bilirrubina Total", "Bilirrubina Direta", "Bilirrubina Indireta",
        "LDH", "Gama GT",
        # Pancreático
        "Amilase", "Lipase",
        # Cardíaco
        "CPK Total", "CK-MB", "Troponina I", "Troponina T",
        "Troponina I Ultrassensível", "Mioglobina", "BNP", "NT-proBNP",
        "Homocisteína",
        # nomes alternativos
        "CREATININA", "CREATININA SERICA", "ACIDO URICO",
        "TGO", "TGP", "AST", "ALT",
        "GAMA - GLUTAMIL TRANSFERASE", "GAMA GT",
        "ASPARTATO AMINOTRANSFERASE (TGO, AST)",
        "ALANINA AMINOTRANSFERASE (TGP, ALT)",
        "Creatinafosfoquinase - Fração MB (CK-MB)",
        "Creatinofosfoquinase (CPK-Total)",
        "CREATINO FOSFOQUINASE", "CPK CREATINO FOSFOQUINASE",
        "Lactato Desidrogenase (LDH)",
        "AMILASE SERICA",
        # nomes alternativos do seed expandido
        "ALT (TGP)", "AST (TGO)", "Albumina Sérica", "Gama-GT",
        "Creatinina Sérica", "Taxa de Filtração Glomerular Estimada",
        "Troponina I de Alta Sensibilidade",
        "Creatinofosfoquinase Total (CPK)",
    ],

    # ── 4. IMUNIDADE E INFLAMAÇÃO ─────────────────────────────────────────────
    4: [
        "PCR (Proteína C-Reativa)", "PCR", "PCR (Proteína C Reativa)",
        "PCR Ultrassensível", "PCR Ultrasensível",
        "Fibrinogênio",
        "Anti-TPO", "Anti-Tireoglobulina",
        "Anti-Transglutaminase IgA", "Imunoglobulina A (IgA)",
        "Complemento C3", "Complemento C4",
        "FAN", "Fator Reumatoide",
        # sorologias
        "HIV Ag/Ac", "HBsAg", "Anti-HBs", "Anti-HCV",
        "VDRL", "FTA-ABS", "Toxoplasmose IgG", "Toxoplasmose IgM",
        "CMV IgG", "CMV IgM", "EBV", "Dengue NS1",
        "Dengue IgG", "Dengue IgM",
        # nomes alternativos
        "ANTI TRANSGLUTAMINASE IGA", "IMUNOGLOBULINA A - IGA",
        "Anti-HIV", "Fibrinogênio (Marcador Inflamatório)", "Interleucina-6",
        "Imunoglobulina G (IgG)", "Imunoglobulina M (IgM)",
        "Célula Parietal (Anti-IgG)",
    ],

    # ── 5. HORMÔNIOS E ENDOCRINOLOGIA ─────────────────────────────────────────
    5: [
        # Tireoide
        "TSH", "T4 Livre", "T3 Total", "T4 Total", "T3 Livre",
        "Tireoglobulina",
        # Sexuais masculinos
        "Testosterona Total", "Testosterona Livre", "SHBG",
        "DHT (Di-Hidrotestosterona)", "Androstenediona",
        "PSA Total", "PSA Livre",
        # Sexuais femininos
        "Estradiol (E2)", "FSH", "LH", "Prolactina", "Progesterona",
        # Adrenal
        "Cortisol Basal", "DHEA-S", "Aldosterona", "Renina",
        "17-Hidroxiprogesterona",
        # Hipófise/outros
        "GH (Hormônio do Crescimento)", "IGF-1", "PTH (Paratormônio)",
        "Insulina Basal",
        # nomes alternativos
        "TSH ULTRA SENSIVEL", "TSH ultra sensivel",
        "TIROXINA LIVRE - T4 LIVRE", "T3 REVERSO",
        "TESTOSTERONA TOTAL", "TESTOSTERONA LIVRE",
        "SHBG (GLOBULINA LIGADORA DOS HORMONIOS SEXUAIS)",
        "SHBG - GLOBULINA LIGADORA DE HORMÔNIOS SEXUAIS",
        "DHT - DEHIDROTESTOSTERONA",
        "ESTRADIOL, 17 BETA",
        "TSH Ultrassensível (Hormônio Tireoestimulante)",
        "T4 (Tiroxina) Livre",
        "PTH (Paratormônio) Intacto",
        "Cortisol",
    ],

    # ── 6. VITAMINAS E MICRONUTRIENTES ────────────────────────────────────────
    6: [
        "Vitamina D (25-OH)", "Vitamina B12", "Ácido Fólico (Vitamina B9)",
        "Vitamina A (Retinol)", "Vitamina E", "Vitamina C",
        "Ferro Sérico", "Ferritina", "Transferrina", "Saturação de Transferrina",
        "TIBC (Capacidade de Ligação do Ferro)",
        "Zinco", "Magnésio", "Cálcio Total", "Cálcio Ionizado (mg/dL)",
        "Cálcio Ionizado (mmol/L)", "Fósforo", "Cobre", "Selênio",
        "Ácido Fólico (Vitamina B9)",
        # nomes alternativos
        "25-HIDROXIVITAMINA D", "VITAMINA D 25-HIDROXI",
        "VITAMINA B12 (COBALAMINA)", "ACIDO FOLICO BASAL",
        "FERRITINA", "Ferritina Sérica",
        "DOSAGEM DE FERRO SERICO", "HOMOCISTEINA (PLASMA)",
        "25 - Hidroxi - Vitamina D (25(OH)D)",
        "Dosagem de Vitamina B12 (Cobalamina)", "Dosagem de Vitamina B12",
        "Dosagem de Zinco", "Dosagem de Ferro",
        "Dosagem de Homocisteína", "Dosagem de Vitamina A (Retinol)",
        "25-Hidroxi-Vitamina D (25(OH)D)",
        "Cálcio Iônico", "Cálcio Sérico Total", "Cálcio Ionizado",
        "Cálcio Ionizado (mEq/L)", "Cálcio", "Zinco Sérico", "Magnésio Sérico",
        "Sódio", "Sodio", "Potassio", "Potássio", "Cloro", "Bicarbonato", "Reserva Alcalina",
        "Serotonina",
    ],

    # ── 7. COAGULAÇÃO E HEMOSTASIA ────────────────────────────────────────────
    7: [
        "TP/TAP (%)", "Tempo de Protrombina (TAP/TP)", "Tempo de Protrombina",
        "Atividade de Protrombina", "INR", "TTPa",
        "D-Dímero", "Fibrinogênio", "Tempo de Trombina",
        "Antitrombina III", "Proteína C", "Proteína S",
        "Fibrinogênio",
    ],

    # ── 8. MARCADORES TUMORAIS ────────────────────────────────────────────────
    8: [
        "PSA Total", "PSA Livre", "CEA", "CA 19-9", "AFP",
        "Beta-HCG", "CA 125", "CA 15-3", "Tireoglobulina",
        "Cromogranina A", "Enolase Neurônio-Específica (NSE)",
    ],

    # ── 9. URINA E LÍQUIDOS CORPORAIS ─────────────────────────────────────────
    9: [
        "EAS (Urina Tipo 1)", "Proteinúria 24h", "Microalbuminúria 24h",
        "Relação Albumina/Creatinina", "Creatinina Urinária",
        "Urocultura", "Urina Rotina", "Microalbuminúria",
    ],

    # ── 10. RADIOLOGIA ────────────────────────────────────────────────────────
    10: [],

    # ── 11. ULTRASSONOGRAFIA ──────────────────────────────────────────────────
    11: [
        "USG Abdome Total", "USG Próstata",
        "USG Rins e Vias Urinárias", "USG Tireoide",
        "Doppler Venoso de Membros Inferiores",
        "Doppler de Carótidas e Vertebrais",
    ],

    # ── 12. TOMOGRAFIA ────────────────────────────────────────────────────────
    12: [],

    # ── 13. RESSONÂNCIA ───────────────────────────────────────────────────────
    13: [],

    # ── 14. MEDICINA NUCLEAR ──────────────────────────────────────────────────
    14: [],

    # ── 15. CARDIOLOGIA DE IMAGEM ─────────────────────────────────────────────
    15: [
        "Ecocardiograma", "Holter 24h", "MAPA",
        "Teste Ergométrico", "Densitometria Óssea",
    ],

    # ── 16. ENDOSCOPIA ────────────────────────────────────────────────────────
    16: [
        "Endoscopia Digestiva Alta", "Colonoscopia",
    ],

    # ── 18. ANATOMOPATOLÓGICO ─────────────────────────────────────────────────
    18: [
        "Histopatológico",
    ],

    # ── 19. MICROBIOLOGIA ─────────────────────────────────────────────────────
    19: [],

    # ── OFTALMOLOGIA → Imagem (grupo 13 Ressonância não cabe — usar 11 USG) ──
    # Oftalmologia vai para grupo 17 Funcionais ou criamos subgrupo
    # Por ora: Funcionais
    # ── 17. FUNCIONAIS — oftalmologia ─────────────────────────────────────────
    # Os exames de imagem normalmente entram como laudos — não têm valores numéricos
    # Grupos criados para quando o usuário cadastrar manualmente

    17: [
        "PA Sistólica Média (MAPA)", "PA Diastólica Média (MAPA)",
        "PA Sistólica Vigília (MAPA)", "PA Diastólica Vigília (MAPA)",
        "PA Sistólica Sono (MAPA)", "PA Diastólica Sono (MAPA)",
        "Carga Pressórica Sistólica (MAPA)", "Carga Pressórica Diastólica (MAPA)",
        "Descenso Noturno Sistólica (MAPA)", "Descenso Noturno Diastólica (MAPA)",
        "MAPA - Mapeamento Ambulatorial da Pressão Arterial",
        "Eletrocardiograma",
        # Oftalmologia — sem grupo próprio, entra em Funcionais
        "Campo Visual (Campimetria)", "Paquimetria",
        "Retinografia", "Tomografia de Coerência Óptica (OCT)", "Tonometria",
    ],
}


# ══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES
# ══════════════════════════════════════════════════════════════════════════════

def _migrar(conn: sqlite3.Connection):
    cur = conn.cursor()
    # grupos_exame
    cur.execute("""
        CREATE TABLE IF NOT EXISTS grupos_exame (
            id        INTEGER PRIMARY KEY,
            nome      TEXT UNIQUE NOT NULL,
            descricao TEXT,
            tipo      TEXT NOT NULL,
            icone     TEXT,
            ordem     INTEGER DEFAULT 0,
            ativo     INTEGER DEFAULT 1
        )
    """)
    # grupo_id em exames_padrao
    try:
        cur.execute("ALTER TABLE exames_padrao ADD COLUMN grupo_id INTEGER REFERENCES grupos_exame(id)")
        logging.info("[MIGRAR] exames_padrao.grupo_id adicionada")
    except sqlite3.OperationalError:
        pass
    conn.commit()


def _seed_grupos(conn: sqlite3.Connection):
    cur = conn.cursor()
    for gid, nome, desc, tipo, icone, ordem in GRUPOS:
        cur.execute("""
            INSERT INTO grupos_exame (id, nome, descricao, tipo, icone, ordem)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(nome) DO UPDATE SET
                descricao=excluded.descricao,
                tipo=excluded.tipo,
                icone=excluded.icone,
                ordem=excluded.ordem
        """, (gid, nome, desc, tipo, icone, ordem))
    conn.commit()
    logging.info(f"[GRUPOS] {len(GRUPOS)} grupos inseridos/atualizados")


def _vincular_exames(conn: sqlite3.Connection):
    cur = conn.cursor()
    ok = 0
    nf = 0
    for grupo_id, nomes in VINCULOS.items():
        for nome in nomes:
            # busca exato
            row = cur.execute(
                "SELECT id FROM exames_padrao WHERE UPPER(nome_oficial)=UPPER(?)",
                (nome,)
            ).fetchone()
            if not row:
                # busca por sinônimo
                row = cur.execute(
                    "SELECT id FROM exames_padrao WHERE UPPER(sinonimos) LIKE UPPER(?)",
                    (f"%{nome}%",)
                ).fetchone()
            if row:
                cur.execute(
                    "UPDATE exames_padrao SET grupo_id=? WHERE id=? AND (grupo_id IS NULL OR grupo_id=?)",
                    (grupo_id, row[0], grupo_id)
                )
                ok += 1
            else:
                nf += 1
                logging.debug(f"[VINCULOS] não encontrado: {nome}")

    conn.commit()

    # Relatório
    total_vinculados = cur.execute(
        "SELECT COUNT(*) FROM exames_padrao WHERE grupo_id IS NOT NULL"
    ).fetchone()[0]
    total = cur.execute("SELECT COUNT(*) FROM exames_padrao").fetchone()[0]
    sem_grupo = total - total_vinculados

    logging.info(f"[VINCULOS] {total_vinculados}/{total} exames vinculados | {sem_grupo} sem grupo")
    if sem_grupo > 0:
        rows = cur.execute(
            "SELECT nome_oficial FROM exames_padrao WHERE grupo_id IS NULL ORDER BY nome_oficial"
        ).fetchall()
        for r in rows:
            logging.debug(f"[SEM GRUPO] {r[0]}")
    return total_vinculados, sem_grupo


def popular_grupos(db_path=None):
    path = Path(db_path) if db_path else DB_PATH
    conn = sqlite3.connect(str(path))
    try:
        _migrar(conn)
        _seed_grupos(conn)
        vinc, sem = _vincular_exames(conn)
        return {"grupos": len(GRUPOS), "vinculados": vinc, "sem_grupo": sem}
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print("=" * 60)
    print("  PRONTUÁRIO — Grupos de Exames")
    print("=" * 60)
    r = popular_grupos()
    print(f"\n  Grupos criados    : {r['grupos']}")
    print(f"  Exames vinculados : {r['vinculados']}")
    print(f"  Sem grupo         : {r['sem_grupo']}")
    print("\n  Concluído.")
