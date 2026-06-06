# -*- coding: utf-8 -*-
"""
exames_padrao_dados.py
Tabela pré-populada com 100+ exames laboratoriais mais comuns no Brasil.
"""

import sqlite3
import json

EXAMES_PADRAO = [

    # ══════════════════════════════════════════════════════
    # GLICEMIA
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Glicose em Jejum",
        "sinonimos": ["GLICOSE", "GLICEMIA", "GLICEMIA DE JEJUM", "GLICOSE JEJUM",
                      "GLICEMIA JEJUM", "GLUCOSE", "GLICOSE RESULT", "GLICOSE RESULTADO",
                      "GLICEMIA BASAL", "Glicemia de Jejum"],
        "categoria": "Glicemia", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 50, "limite_baixo": 70, "otimo_min": 75,
            "otimo_max": 90, "limite_alto": 100, "critico_alto": 126}]
    },
    {
        "nome_oficial": "Hemoglobina Glicada (HbA1c)",
        "sinonimos": ["HEMOGLOBINA GLICADA", "HBA1C", "GLICOHEMOGLOBINA",
                      "HEMOGLOBINA GLICOSILADA", "HB GLICADA", "A1C"],
        "categoria": "Glicemia", "unidade": "%",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 3.0, "limite_baixo": 4.0, "otimo_min": 4.5,
            "otimo_max": 5.6, "limite_alto": 6.4, "critico_alto": 8.0}]
    },
    {
        "nome_oficial": "Insulina",
        "sinonimos": ["INSULINA", "INSULINA BASAL", "INSULINA DE JEJUM", "INSULINA RESULT",
                      "Insulinemia de Jejum (Basal)", "Insulina Basal"],
        "categoria": "Glicemia", "unidade": "µUI/mL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 1.0, "limite_baixo": 2.0, "otimo_min": 3.0,
            "otimo_max": 10.0, "limite_alto": 15.0, "critico_alto": 30.0}]
    },

    # ══════════════════════════════════════════════════════
    # LIPÍDIOS
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Colesterol Total",
        "sinonimos": ["COLESTEROL TOTAL", "COLESTEROL", "CT",
                      "Dosagem de Colesterol Total"],
        "categoria": "Lipídios", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 100, "limite_baixo": 130, "otimo_min": 150,
            "otimo_max": 190, "limite_alto": 240, "critico_alto": 300}]
    },
    {
        "nome_oficial": "Colesterol HDL",
        "sinonimos": ["COLESTEROL HDL", "HDL", "HDL COLESTEROL", "COLESTEROL - HDL",
                      "COLESTEROL -HDL", "HDL-C", "COLESTEROL HDL M", "Colesterol HDL"],
        "categoria": "Lipídios", "unidade": "mg/dL",
        "referencias": [
            {"sexo": "M", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 20, "limite_baixo": 40, "otimo_min": 50,
             "otimo_max": 80, "limite_alto": 100, "critico_alto": 120},
            {"sexo": "F", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 25, "limite_baixo": 50, "otimo_min": 60,
             "otimo_max": 90, "limite_alto": 110, "critico_alto": 130},
        ]
    },
    {
        "nome_oficial": "Colesterol LDL",
        "sinonimos": ["COLESTEROL LDL", "LDL", "LDL COLESTEROL", "COLESTEROL - LDL",
                      "COLESTEROL -LDL", "LDL-C", "COLESTEROL LDL M"],
        "categoria": "Lipídios", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 30, "limite_baixo": 70, "otimo_min": 80,
            "otimo_max": 100, "limite_alto": 130, "critico_alto": 190}]
    },
    {
        "nome_oficial": "Triglicerídeos",
        "sinonimos": ["TRIGLICERIDEOS", "TRIGLICERÍDEOS", "TRIGLICÉRIDES",
                      "DOSAGEM DE TRIGLICERIDEOS", "TG"],
        "categoria": "Lipídios", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 20, "limite_baixo": 50, "otimo_min": 60,
            "otimo_max": 150, "limite_alto": 200, "critico_alto": 500}]
    },
    {
        "nome_oficial": "Colesterol VLDL",
        "sinonimos": ["VLDL", "COLESTEROL VLDL", "COLESTEROL - VLDL",
                      "COLESTEROL NAO-HDL", "COLESTEROL NÃO-HDL"],
        "categoria": "Lipídios", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 2, "limite_baixo": 5, "otimo_min": 5,
            "otimo_max": 30, "limite_alto": 40, "critico_alto": 100}]
    },

    # ══════════════════════════════════════════════════════
    # HEMOGRAMA
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Hemoglobina",
        "sinonimos": ["HEMOGLOBINA", "HB", "HGB", "HEMOGLOBINA TOTAL"],
        "categoria": "Hemograma", "unidade": "g/dL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 7.0, "limite_baixo": 13.0, "otimo_min": 14.0,
             "otimo_max": 16.5, "limite_alto": 17.5, "critico_alto": 20.0},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 7.0, "limite_baixo": 12.0, "otimo_min": 12.5,
             "otimo_max": 15.5, "limite_alto": 16.0, "critico_alto": 19.0},
        ]
    },
    {
        "nome_oficial": "Hematócrito",
        "sinonimos": ["HEMATOCRITO", "HEMATÓCRITO", "HCT", "HT"],
        "categoria": "Hemograma", "unidade": "%",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 21, "limite_baixo": 39, "otimo_min": 41,
             "otimo_max": 50, "limite_alto": 52, "critico_alto": 60},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 21, "limite_baixo": 35, "otimo_min": 36,
             "otimo_max": 46, "limite_alto": 48, "critico_alto": 56},
        ]
    },
    {
        "nome_oficial": "Hemácias",
        "sinonimos": ["HEMACIAS", "HEMÁCIAS", "ERITROCITOS", "ERITRÓCITOS",
                      "GLOBULOS VERMELHOS", "RBC", "Hem?cias", "Hemacias"],
        "categoria": "Hemograma", "unidade": "milhões/mm³",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 2.5, "limite_baixo": 4.3, "otimo_min": 4.5,
             "otimo_max": 5.5, "limite_alto": 5.9, "critico_alto": 7.0},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 2.5, "limite_baixo": 3.8, "otimo_min": 4.0,
             "otimo_max": 5.0, "limite_alto": 5.2, "critico_alto": 6.5},
        ]
    },
    {
        "nome_oficial": "Leucócitos",
        "sinonimos": ["LEUCOCITOS", "LEUCÓCITOS", "GLOBULOS BRANCOS", "WBC",
                      "CONTAGEM DE LEUCOCITOS", "LEUCOCITOS TOTAIS"],
        "categoria": "Hemograma", "unidade": "/mm³",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 2000, "limite_baixo": 4000, "otimo_min": 5000,
            "otimo_max": 8000, "limite_alto": 10000, "critico_alto": 30000}]
    },
    {
        "nome_oficial": "Plaquetas",
        "sinonimos": ["PLAQUETAS", "TROMBOCITOS", "TROMBÓCITOS", "PLT"],
        "categoria": "Hemograma", "unidade": "/mm³",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 50000, "limite_baixo": 150000, "otimo_min": 180000,
            "otimo_max": 350000, "limite_alto": 400000, "critico_alto": 1000000}]
    },
    {
        "nome_oficial": "VCM",
        "sinonimos": ["VCM", "VOLUME CORPUSCULAR MEDIO", "VOLUME CORPUSCULAR MÉDIO", "MCV"],
        "categoria": "Hemograma", "unidade": "fL",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 60, "limite_baixo": 80, "otimo_min": 83,
            "otimo_max": 95, "limite_alto": 100, "critico_alto": 120}]
    },
    {
        "nome_oficial": "HCM",
        "sinonimos": ["HCM", "HEMOGLOBINA CORPUSCULAR MEDIA",
                      "HEMOGLOBINA CORPUSCULAR MÉDIA", "MCH", "H.C.M", "H.C.M."],
        "categoria": "Hemograma", "unidade": "pg",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 15, "limite_baixo": 26, "otimo_min": 27,
            "otimo_max": 33, "limite_alto": 35, "critico_alto": 45}]
    },
    {
        "nome_oficial": "CHCM",
        "sinonimos": ["CHCM", "CONCENTRACAO DE HEMOGLOBINA CORPUSCULAR", "MCHC",
                      "C.H.C.M", "C.H.C.M."],
        "categoria": "Hemograma", "unidade": "g/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 28, "limite_baixo": 31, "otimo_min": 32,
            "otimo_max": 36, "limite_alto": 37, "critico_alto": 40}]
    },
    {
        "nome_oficial": "RDW",
        "sinonimos": ["RDW", "INDICE DE ANISOCITOSE", "AMPLITUDE DE DISTRIBUICAO",
                      "R.D.W", "R.D.W.", "R.D.W. (SD)"],
        "categoria": "Hemograma", "unidade": "%",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 10, "limite_baixo": 11, "otimo_min": 11.5,
            "otimo_max": 14, "limite_alto": 14.5, "critico_alto": 20}]
    },
    {
        "nome_oficial": "Neutrófilos",
        "sinonimos": ["NEUTROFILOS", "NEUTRÓFILOS", "SEGMENTADOS",
                      "NEUTROFILOS SEGMENTADOS", "NEUTROFILOS TOTAIS",
                      "Neutrófilos Segmentados"],
        "categoria": "Hemograma", "unidade": "/mm³",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 500, "limite_baixo": 1800, "otimo_min": 2500,
            "otimo_max": 6000, "limite_alto": 7500, "critico_alto": 20000}]
    },
    {
        "nome_oficial": "Linfócitos",
        "sinonimos": ["LINFOCITOS", "LINFÓCITOS", "LYMPHOCYTES",
                      "Linfócitos típicos", "Linf?citos t?picos"],
        "categoria": "Hemograma", "unidade": "/mm³",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 200, "limite_baixo": 1000, "otimo_min": 1500,
            "otimo_max": 3500, "limite_alto": 4000, "critico_alto": 10000}]
    },
    {
        "nome_oficial": "Monócitos",
        "sinonimos": ["MONOCITOS", "MONÓCITOS", "MONOCYTES"],
        "categoria": "Hemograma", "unidade": "/mm³",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 100, "otimo_min": 200,
            "otimo_max": 800, "limite_alto": 1000, "critico_alto": 3000}]
    },
    {
        "nome_oficial": "Eosinófilos",
        "sinonimos": ["EOSINOFILOS", "EOSINÓFILOS", "EOSINOPHILS"],
        "categoria": "Hemograma", "unidade": "/mm³",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 400, "limite_alto": 500, "critico_alto": 5000}]
    },
    {
        "nome_oficial": "Basófilos",
        "sinonimos": ["BASOFILOS", "BASÓFILOS", "BASOPHILS"],
        "categoria": "Hemograma", "unidade": "/mm³",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 100, "limite_alto": 200, "critico_alto": 500}]
    },
    {
        "nome_oficial": "Blastos",
        "sinonimos": ["BLASTOS", "BLASTOS 0,00", "MIELOBLASTOS"],
        "categoria": "Hemograma", "unidade": "%",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 0, "limite_alto": 1, "critico_alto": 5}]
    },

    # ══════════════════════════════════════════════════════
    # FERRO
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Ferritina",
        "sinonimos": ["FERRITINA", "FERRITINA SERICA", "FERRITINA SÉRICA",
                      "DOSAGEM DE FERRITINA", "FERRITINA RESULT", "FERRITINA RESULTADO",
                      "Ferritina Sérica"],
        "categoria": "Ferro", "unidade": "ng/mL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 5, "limite_baixo": 20, "otimo_min": 40,
             "otimo_max": 150, "limite_alto": 200, "critico_alto": 400},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 5, "limite_baixo": 15, "otimo_min": 30,
             "otimo_max": 100, "limite_alto": 150, "critico_alto": 300},
        ]
    },
    {
        "nome_oficial": "Ferro Sérico",
        "sinonimos": ["FERRO SERICO", "FERRO SÉRICO", "DOSAGEM DE FERRO SERICO",
                      "FERRO", "IRON", "Dosagem de Ferro", "Ferro Sérico"],
        "categoria": "Ferro", "unidade": "µg/dL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 30, "limite_baixo": 65, "otimo_min": 80,
             "otimo_max": 150, "limite_alto": 170, "critico_alto": 300},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 30, "limite_baixo": 50, "otimo_min": 65,
             "otimo_max": 130, "limite_alto": 170, "critico_alto": 300},
        ]
    },
    {
        "nome_oficial": "Transferrina",
        "sinonimos": ["TRANSFERRINA", "DOSAGEM DE TRANSFERRINA", "SIDEROFILIA",
                      "Dosagem de Transferrina"],
        "categoria": "Ferro", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 100, "limite_baixo": 200, "otimo_min": 220,
            "otimo_max": 360, "limite_alto": 400, "critico_alto": 600}]
    },
    {
        "nome_oficial": "Saturação de Transferrina",
        "sinonimos": ["SATURACAO DE TRANSFERRINA", "SATURAÇÃO DE TRANSFERRINA",
                      "INDICE DE SATURACAO DE TRANSFERRINA",
                      "Índice de Saturação de Transferrina", "ÍNDICE DE SATURAÇÃO", "IST"],
        "categoria": "Ferro", "unidade": "%",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 5, "limite_baixo": 20, "otimo_min": 25,
            "otimo_max": 45, "limite_alto": 50, "critico_alto": 70}]
    },

    # ══════════════════════════════════════════════════════
    # TIREOIDE
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "TSH",
        "sinonimos": ["TSH", "HORMONIO ESTIMULANTE DA TIREOIDE",
                      "HORMÔNIO ESTIMULANTE DA TIREOIDE",
                      "TSH ULTRASSENSIVEL", "TSH ULTRASENSIVEL",
                      "TSH ULTRA SENSIVEL", "TSH ultra sensivel",
                      "TSH Ultrassensível (Hormônio Tireoestimulante)"],
        "categoria": "Tireoide", "unidade": "mUI/L",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 0.1, "limite_baixo": 0.4, "otimo_min": 1.0,
            "otimo_max": 2.5, "limite_alto": 4.5, "critico_alto": 10.0}]
    },
    {
        "nome_oficial": "T4 Livre",
        "sinonimos": ["T4 LIVRE", "T4L", "TIROXINA LIVRE", "FT4", "T4 FREE",
                      "TIROXINA LIVRE - T4 LIVRE", "T4 (Tiroxina) Livre"],
        "categoria": "Tireoide", "unidade": "ng/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 0.4, "limite_baixo": 0.7, "otimo_min": 0.9,
            "otimo_max": 1.5, "limite_alto": 1.8, "critico_alto": 3.0}]
    },
    {
        "nome_oficial": "T3 Livre",
        "sinonimos": ["T3 LIVRE", "T3L", "TRIIODOTIRONINA LIVRE", "FT3"],
        "categoria": "Tireoide", "unidade": "pg/mL",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 1.0, "limite_baixo": 2.0, "otimo_min": 2.5,
            "otimo_max": 4.0, "limite_alto": 4.4, "critico_alto": 7.0}]
    },
    {
        "nome_oficial": "T4 Total",
        "sinonimos": ["T4 TOTAL", "T4", "TIROXINA TOTAL"],
        "categoria": "Tireoide", "unidade": "µg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 2.0, "limite_baixo": 5.1, "otimo_min": 6.0,
            "otimo_max": 11.0, "limite_alto": 12.0, "critico_alto": 20.0}]
    },
    {
        "nome_oficial": "T3 Total",
        "sinonimos": ["T3 TOTAL", "T3", "TRIIODOTIRONINA TOTAL"],
        "categoria": "Tireoide", "unidade": "ng/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 40, "limite_baixo": 80, "otimo_min": 100,
            "otimo_max": 175, "limite_alto": 200, "critico_alto": 300}]
    },
    {
        "nome_oficial": "Anti-TPO",
        "sinonimos": ["ANTI-TPO", "ANTI TPO", "ANTICORPO ANTITIREOPEROXIDASE", "TPO"],
        "categoria": "Tireoide", "unidade": "UI/mL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 34, "limite_alto": 35, "critico_alto": 500}]
    },
    {
        "nome_oficial": "Anti-Tireoglobulina",
        "sinonimos": ["ANTI-TIREOGLOBULINA", "ANTI TIREOGLOBULINA",
                      "ANTICORPO ANTITIREOGLOBULINA", "ATGL"],
        "categoria": "Tireoide", "unidade": "UI/mL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 115, "limite_alto": 116, "critico_alto": 1000}]
    },

    # ══════════════════════════════════════════════════════
    # FUNÇÃO RENAL
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Creatinina",
        "sinonimos": ["CREATININA", "CREATININA SERICA", "CREATININA SÉRICA",
                      "DOSAGEM DE CREATININA", "CREATININA RESULT",
                      "Creatinina Sérica"],
        "categoria": "Função Renal", "unidade": "mg/dL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 0.4, "limite_baixo": 0.7, "otimo_min": 0.8,
             "otimo_max": 1.1, "limite_alto": 1.3, "critico_alto": 4.0},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 0.3, "limite_baixo": 0.5, "otimo_min": 0.6,
             "otimo_max": 1.0, "limite_alto": 1.1, "critico_alto": 3.0},
        ]
    },
    {
        "nome_oficial": "Ureia",
        "sinonimos": ["UREIA", "URÉIA", "UREIA SERICA", "BUN", "DOSAGEM DE UREIA"],
        "categoria": "Função Renal", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 5, "limite_baixo": 15, "otimo_min": 20,
            "otimo_max": 40, "limite_alto": 50, "critico_alto": 100}]
    },
    {
        "nome_oficial": "Ácido Úrico",
        "sinonimos": ["ACIDO URICO", "ÁCIDO ÚRICO", "URICEMIA",
                      "DOSAGEM DE ACIDO URICO"],
        "categoria": "Função Renal", "unidade": "mg/dL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 1.5, "limite_baixo": 3.5, "otimo_min": 3.5,
             "otimo_max": 6.0, "limite_alto": 7.0, "critico_alto": 10.0},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 1.5, "limite_baixo": 2.6, "otimo_min": 2.6,
             "otimo_max": 5.0, "limite_alto": 6.0, "critico_alto": 9.0},
        ]
    },

    # ══════════════════════════════════════════════════════
    # FUNÇÃO HEPÁTICA
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "TGO (AST)",
        "sinonimos": ["TGO", "AST", "ASPARTATO AMINOTRANSFERASE",
                      "TRANSAMINASE OXALACETICA", "TGO AST",
                      "ASPARTATO AMINOTRANSFERASE (TGO, AST)",
                      "Transaminase Glutâmico-Oxaloacética (TGO/AST)",
                      "TGO (AST)"],
        "categoria": "Função Hepática", "unidade": "U/L",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 5, "limite_baixo": 10, "otimo_min": 10,
             "otimo_max": 35, "limite_alto": 40, "critico_alto": 200},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 5, "limite_baixo": 10, "otimo_min": 10,
             "otimo_max": 31, "limite_alto": 35, "critico_alto": 200},
        ]
    },
    {
        "nome_oficial": "TGP (ALT)",
        "sinonimos": ["TGP", "ALT", "ALANINA AMINOTRANSFERASE",
                      "TRANSAMINASE PIRUVICA", "TGP ALT",
                      "ALANINA AMINOTRANSFERASE (TGP, ALT)",
                      "Transaminase Glutâmico-Pirúvica (TGP/ALT)",
                      "TGP (ALT)"],
        "categoria": "Função Hepática", "unidade": "U/L",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 5, "limite_baixo": 10, "otimo_min": 10,
             "otimo_max": 40, "limite_alto": 45, "critico_alto": 200},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 5, "limite_baixo": 10, "otimo_min": 10,
             "otimo_max": 34, "limite_alto": 38, "critico_alto": 200},
        ]
    },
    {
        "nome_oficial": "Gama GT",
        "sinonimos": ["GAMA GT", "GGT", "GAMA GLUTAMILTRANSFERASE",
                      "GAMA-GT", "GAMAGLUTAMIL TRANSFERASE",
                      "GAMA - GLUTAMIL TRANSFERASE",
                      "Gama Glutamil-Transferase (GGT)"],
        "categoria": "Função Hepática", "unidade": "U/L",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 3, "limite_baixo": 8, "otimo_min": 8,
             "otimo_max": 55, "limite_alto": 78, "critico_alto": 300},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 3, "limite_baixo": 5, "otimo_min": 5,
             "otimo_max": 38, "limite_alto": 50, "critico_alto": 200},
        ]
    },
    {
        "nome_oficial": "Fosfatase Alcalina",
        "sinonimos": ["FOSFATASE ALCALINA", "FA", "ALP"],
        "categoria": "Função Hepática", "unidade": "U/L",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 20, "limite_baixo": 40, "otimo_min": 44,
            "otimo_max": 120, "limite_alto": 147, "critico_alto": 500}]
    },
    {
        "nome_oficial": "Bilirrubina Total",
        "sinonimos": ["BILIRRUBINA TOTAL", "BT", "BILIRRUBINAS TOTAIS"],
        "categoria": "Função Hepática", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 0.1, "limite_baixo": 0.2, "otimo_min": 0.3,
            "otimo_max": 1.0, "limite_alto": 1.2, "critico_alto": 3.0}]
    },
    {
        "nome_oficial": "Bilirrubina Direta",
        "sinonimos": ["BILIRRUBINA DIRETA", "BD", "BILIRRUBINA CONJUGADA",
                      "BILIRRUBINA DIRETA (CONJUGADA)"],
        "categoria": "Função Hepática", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 0.3, "limite_alto": 0.4, "critico_alto": 2.0}]
    },
    {
        "nome_oficial": "Bilirrubina Indireta",
        "sinonimos": ["BILIRRUBINA INDIRETA", "BI", "BILIRRUBINA NAO CONJUGADA",
                      "BILIRRUBINA INDIRETA (NÃO-CONJUGADA)"],
        "categoria": "Função Hepática", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 0.8, "limite_alto": 1.0, "critico_alto": 2.5}]
    },
    {
        "nome_oficial": "Albumina",
        "sinonimos": ["ALBUMINA", "ALBUMINA SERICA", "ALBUMINA SÉRICA",
                      "ALBUMINAS", "ALBUMINA RESULTADO", "Albuminas"],
        "categoria": "Proteínas", "unidade": "g/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 2.0, "limite_baixo": 3.5, "otimo_min": 4.0,
            "otimo_max": 5.0, "limite_alto": 5.5, "critico_alto": 6.5}]
    },

    # ══════════════════════════════════════════════════════
    # PROTEÍNAS
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Proteínas Totais",
        "sinonimos": ["PROTEINAS TOTAIS", "PROTEÍNAS TOTAIS", "PT"],
        "categoria": "Proteínas", "unidade": "g/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 4.0, "limite_baixo": 6.0, "otimo_min": 6.5,
            "otimo_max": 8.0, "limite_alto": 8.5, "critico_alto": 10.0}]
    },
    {
        "nome_oficial": "Fibrinogênio",
        "sinonimos": ["FIBRINOGENIO", "FIBRINOGÊNIO", "DOSAGEM DE FIBRINOGENIO"],
        "categoria": "Coagulação", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 100, "limite_baixo": 200, "otimo_min": 250,
            "otimo_max": 400, "limite_alto": 450, "critico_alto": 800}]
    },

    # ══════════════════════════════════════════════════════
    # COAGULAÇÃO
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "INR",
        "sinonimos": ["INR", "RELACAO NORMATIZADA INTERNACIONAL",
                      "RAZAO NORMALIZADA INTERNACIONAL"],
        "categoria": "Coagulação", "unidade": "",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 0.5, "limite_baixo": 0.8, "otimo_min": 0.9,
            "otimo_max": 1.1, "limite_alto": 1.3, "critico_alto": 4.0}]
    },
    {
        "nome_oficial": "Tempo de Protrombina",
        "sinonimos": ["TP", "TEMPO DE PROTROMBINA", "PROTROMBINA", "TAP",
                      "TAP - Tempo", "TAP TEMPO"],
        "categoria": "Coagulação", "unidade": "seg",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 5, "limite_baixo": 10, "otimo_min": 10,
            "otimo_max": 14, "limite_alto": 16, "critico_alto": 30}]
    },

    # ══════════════════════════════════════════════════════
    # VITAMINAS E MINERAIS
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Vitamina D",
        "sinonimos": ["VITAMINA D", "25-OH VITAMINA D", "25 OH VITAMINA D",
                      "VITAMINA D3", "COLECALCIFEROL", "25-HIDROXIVITAMINA D",
                      "VITAMINA D (25-OH-COLECALCIFEROL)",
                      "VITAMINA D 25-HIDROXI", "Vitamina D (25-OH)"],
        "categoria": "Vitaminas", "unidade": "ng/mL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 10, "limite_baixo": 20, "otimo_min": 40,
            "otimo_max": 80, "limite_alto": 100, "critico_alto": 150}]
    },
    {
        "nome_oficial": "Vitamina B12",
        "sinonimos": ["VITAMINA B12", "COBALAMINA", "B12", "CIANOCOBALAMINA",
                      "VITAMINA B12 (COBALAMINA)", "Dosagem de Vitamina B12 (Cobalamina)",
                      "Dosagem de Vitamina B12"],
        "categoria": "Vitaminas", "unidade": "pg/mL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 100, "limite_baixo": 200, "otimo_min": 400,
            "otimo_max": 900, "limite_alto": 1000, "critico_alto": 2000}]
    },
    {
        "nome_oficial": "Ácido Fólico",
        "sinonimos": ["ACIDO FOLICO", "ÁCIDO FÓLICO", "FOLATO", "VITAMINA B9",
                      "FOLATO SERICO", "ACIDO FOLICO BASAL",
                      "Ácido Fólico (Vitamina B9)"],
        "categoria": "Vitaminas", "unidade": "ng/mL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 2.0, "limite_baixo": 3.0, "otimo_min": 5.0,
            "otimo_max": 15.0, "limite_alto": 20.0, "critico_alto": 40.0}]
    },
    {
        "nome_oficial": "Cálcio",
        "sinonimos": ["CALCIO", "CÁLCIO", "CALCIO TOTAL", "CALCIO SERICO",
                      "CALCIO RESULTADO", "Cálcio Total",
                      "Cálcio Sérico Total (CaT)"],
        "categoria": "Minerais", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 6.0, "limite_baixo": 8.5, "otimo_min": 9.0,
            "otimo_max": 10.0, "limite_alto": 10.5, "critico_alto": 13.0}]
    },
    {
        "nome_oficial": "Potássio",
        "sinonimos": ["POTASSIO", "POTÁSSIO", "K", "POTASSIO SERICO"],
        "categoria": "Minerais", "unidade": "mEq/L",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 2.5, "limite_baixo": 3.5, "otimo_min": 4.0,
            "otimo_max": 4.5, "limite_alto": 5.0, "critico_alto": 6.5}]
    },
    {
        "nome_oficial": "Sódio",
        "sinonimos": ["SODIO", "SÓDIO", "NA", "SODIO SERICO"],
        "categoria": "Minerais", "unidade": "mEq/L",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 120, "limite_baixo": 135, "otimo_min": 138,
            "otimo_max": 142, "limite_alto": 145, "critico_alto": 160}]
    },
    {
        "nome_oficial": "Magnésio",
        "sinonimos": ["MAGNESIO", "MAGNÉSIO", "MG", "MAGNESIO SERICO"],
        "categoria": "Minerais", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0.8, "limite_baixo": 1.6, "otimo_min": 1.9,
            "otimo_max": 2.5, "limite_alto": 2.6, "critico_alto": 4.0}]
    },
    {
        "nome_oficial": "Fósforo",
        "sinonimos": ["FOSFORO", "FÓSFORO", "P", "FOSFORO SERICO", "FOSFATO"],
        "categoria": "Minerais", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 1.0, "limite_baixo": 2.5, "otimo_min": 2.7,
            "otimo_max": 4.0, "limite_alto": 4.5, "critico_alto": 7.0}]
    },
    {
        "nome_oficial": "Zinco",
        "sinonimos": ["ZINCO", "ZN", "ZINCO SERICO", "DOSAGEM DE ZINCO"],
        "categoria": "Minerais", "unidade": "µg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 40, "limite_baixo": 70, "otimo_min": 80,
            "otimo_max": 120, "limite_alto": 130, "critico_alto": 200}]
    },

    # ══════════════════════════════════════════════════════
    # INFLAMAÇÃO / INFECÇÃO
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "PCR",
        "sinonimos": ["PCR", "PROTEINA C REATIVA", "PROTEÍNA C REATIVA",
                      "PCR ULTRASSENSIVEL", "PCR US", "CRP",
                      "PROTEINA C REATIVA ULTRASSENSIVEL"],
        "categoria": "Inflamação", "unidade": "mg/L",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 3.0, "limite_alto": 10.0, "critico_alto": 100.0}]
    },
    {
        "nome_oficial": "VHS",
        "sinonimos": ["VHS", "VELOCIDADE DE HEMOSSEDIMENTACAO",
                      "VELOCIDADE DE HEMOSSEDIMENTAÇÃO", "ESR",
                      "VHS (Velocidade de hemossedimentação/1h)"],
        "categoria": "Inflamação", "unidade": "mm/h",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 15, "limite_alto": 20, "critico_alto": 60},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 20, "limite_alto": 30, "critico_alto": 60},
        ]
    },

    # ══════════════════════════════════════════════════════
    # ENZIMAS
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "CPK Total",
        "sinonimos": ["CPK", "CK", "CREATINOFOSFOQUINASE", "CREATINAQUINASE",
                      "CPK TOTAL", "CK TOTAL", "CPK CREATINO FOSFOQUINASE",
                      "CREATINOFOSFOQUINASE (CPK-TOTAL)",
                      "CREATINO FOSFOQUINASE", "Creatinofosfoquinase (CPK-Total)"],
        "categoria": "Enzimas", "unidade": "U/L",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 10, "limite_baixo": 39, "otimo_min": 39,
             "otimo_max": 200, "limite_alto": 308, "critico_alto": 1000},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 10, "limite_baixo": 26, "otimo_min": 26,
             "otimo_max": 170, "limite_alto": 192, "critico_alto": 800},
        ]
    },
    {
        "nome_oficial": "CPK-MB",
        "sinonimos": ["CPK-MB", "CK-MB", "CREATINOFOSFOQUINASE FRACAO MB",
                      "CREATINOFOSFOQUINASE - FRAÇÃO MB (CK-MB)",
                      "Creatinafosfoquinase - Fração MB (CK-MB)"],
        "categoria": "Enzimas", "unidade": "U/L",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 24, "limite_alto": 25, "critico_alto": 100}]
    },
    {
        "nome_oficial": "Amilase",
        "sinonimos": ["AMILASE", "AMILASE SERICA", "AMILASE SÉRICA"],
        "categoria": "Enzimas", "unidade": "U/L",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 10, "limite_baixo": 28, "otimo_min": 28,
            "otimo_max": 100, "limite_alto": 100, "critico_alto": 300}]
    },
    {
        "nome_oficial": "Lipase",
        "sinonimos": ["LIPASE", "LIPASE SERICA", "LIPASE PANCREATICA"],
        "categoria": "Enzimas", "unidade": "U/L",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 5, "limite_baixo": 13, "otimo_min": 13,
            "otimo_max": 60, "limite_alto": 60, "critico_alto": 300}]
    },
    {
        "nome_oficial": "DHL",
        "sinonimos": ["DHL", "LDH", "DESIDROGENASE LACTICA", "DESIDROGENASE LÁTICA",
                      "LACTATO DESIDROGENASE", "Lactato Desidrogenase (LDH)"],
        "categoria": "Enzimas", "unidade": "U/L",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 50, "limite_baixo": 120, "otimo_min": 135,
            "otimo_max": 225, "limite_alto": 240, "critico_alto": 600}]
    },

    # ══════════════════════════════════════════════════════
    # HORMÔNIOS
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Testosterona Total",
        "sinonimos": ["TESTOSTERONA TOTAL", "TESTOSTERONA", "TESTOSTERONE",
                      "TESTOSTERONA TOTAL M", "TESTOSTERONA TOTAL RESULTADO"],
        "categoria": "Hormônios", "unidade": "ng/dL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 100, "limite_baixo": 300, "otimo_min": 500,
             "otimo_max": 800, "limite_alto": 900, "critico_alto": 1500},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 5, "limite_baixo": 15, "otimo_min": 20,
             "otimo_max": 70, "limite_alto": 80, "critico_alto": 200},
        ]
    },
    {
        "nome_oficial": "DHT",
        "sinonimos": ["DHT", "DI-HIDROTESTOSTERONA", "DIIDROTESTOSTERONA",
                      "DHT - DEHIDROTESTOSTERONA", "DEHIDROTESTOSTERONA",
                      "DHT (Di-Hidrotestosterona)"],
        "categoria": "Hormônios", "unidade": "pg/mL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 50, "limite_baixo": 112, "otimo_min": 150,
             "otimo_max": 250, "limite_alto": 300, "critico_alto": 600},
        ]
    },
    {
        "nome_oficial": "Estradiol",
        "sinonimos": ["ESTRADIOL", "E2", "17-BETA ESTRADIOL", "ESTRONA",
                      "ESTRADIOL, 17 BETA", "Estradiol (E2)"],
        "categoria": "Hormônios", "unidade": "pg/mL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 5, "limite_baixo": 10, "otimo_min": 20,
             "otimo_max": 40, "limite_alto": 55, "critico_alto": 100},
            {"sexo": "F", "idade_min": 18, "idade_max": 50,
             "critico_baixo": 10, "limite_baixo": 30, "otimo_min": 50,
             "otimo_max": 300, "limite_alto": 400, "critico_alto": 1000},
        ]
    },
    {
        "nome_oficial": "FSH",
        "sinonimos": ["FSH", "HORMONIO FOLICULO ESTIMULANTE",
                      "HORMÔNIO FOLÍCULO ESTIMULANTE",
                      "FSH (HORMÔNIO FOLÍCULO ESTIMULANTE)"],
        "categoria": "Hormônios", "unidade": "mUI/mL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 0.5, "limite_baixo": 1.0, "otimo_min": 1.5,
             "otimo_max": 8.0, "limite_alto": 12.0, "critico_alto": 30.0},
        ]
    },
    {
        "nome_oficial": "LH",
        "sinonimos": ["LH", "HORMONIO LUTEINIZANTE", "HORMÔNIO LUTEINIZANTE"],
        "categoria": "Hormônios", "unidade": "mUI/mL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 0.5, "limite_baixo": 1.0, "otimo_min": 1.5,
             "otimo_max": 9.0, "limite_alto": 12.0, "critico_alto": 30.0},
        ]
    },
    {
        "nome_oficial": "Prolactina",
        "sinonimos": ["PROLACTINA", "PRL"],
        "categoria": "Hormônios", "unidade": "ng/mL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 1, "limite_baixo": 2, "otimo_min": 3,
             "otimo_max": 15, "limite_alto": 20, "critico_alto": 50},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 1, "limite_baixo": 2, "otimo_min": 3,
             "otimo_max": 25, "limite_alto": 30, "critico_alto": 100},
        ]
    },
    {
        "nome_oficial": "PSA Total",
        "sinonimos": ["PSA TOTAL", "PSA", "ANTIGENO PROSTATICO",
                      "ANTÍGENO PROSTÁTICO ESPECÍFICO"],
        "categoria": "Hormônios", "unidade": "ng/mL",
        "referencias": [
            {"sexo": "M", "idade_min": 40, "idade_max": 50,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 2.5, "limite_alto": 2.5, "critico_alto": 10.0},
            {"sexo": "M", "idade_min": 51, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 4.0, "limite_alto": 4.0, "critico_alto": 10.0},
        ]
    },
    {
        "nome_oficial": "Cortisol",
        "sinonimos": ["CORTISOL", "CORTISOL BASAL", "CORTISOL MATINAL"],
        "categoria": "Hormônios", "unidade": "µg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 3, "limite_baixo": 5, "otimo_min": 7,
            "otimo_max": 20, "limite_alto": 25, "critico_alto": 50}]
    },
    {
        "nome_oficial": "DHEA-S",
        "sinonimos": ["DHEA-S", "DHEAS", "DEIDROEPIANDROSTERONA SULFATO",
                      "SULFATO DE DHEA", "DEHIDROEPIANDROSTERONA"],
        "categoria": "Hormônios", "unidade": "µg/dL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 50, "limite_baixo": 100, "otimo_min": 200,
             "otimo_max": 450, "limite_alto": 500, "critico_alto": 800},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 30, "limite_baixo": 65, "otimo_min": 100,
             "otimo_max": 380, "limite_alto": 430, "critico_alto": 700},
        ]
    },
    {
        "nome_oficial": "SHBG",
        "sinonimos": ["SHBG", "GLOBULINA LIGADORA DE HORMONIOS SEXUAIS",
                      "GLOBULINA LIGADORA DE HORMÔNIOS SEXUAIS",
                      "SHBG (GLOBULINA LIGADORA DOS HORMONIOS SEXUAIS)"],
        "categoria": "Hormônios", "unidade": "nmol/L",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 5, "limite_baixo": 13, "otimo_min": 20,
             "otimo_max": 50, "limite_alto": 71, "critico_alto": 120},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 10, "limite_baixo": 30, "otimo_min": 40,
             "otimo_max": 120, "limite_alto": 150, "critico_alto": 300},
        ]
    },
    {
        "nome_oficial": "Paratormônio (PTH)",
        "sinonimos": ["PTH", "PARATORMONIO", "PARATORMÔNIO",
                      "HORMONIO PARATIREOIDEO", "HORMÔNIO PARATIREOIDIANO",
                      "PARATORMÔNIO PTH INTACTO (MOLÉCULA INTEIRA)",
                      "PTH (Paratormônio) Intacto", "PTH (Paratormônio)"],
        "categoria": "Hormônios", "unidade": "pg/mL",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 5, "limite_baixo": 10, "otimo_min": 15,
            "otimo_max": 65, "limite_alto": 80, "critico_alto": 200}]
    },
    {
        "nome_oficial": "Insulina-like Growth Factor (IGF-1)",
        "sinonimos": ["IGF-1", "IGF1", "SOMATOMEDINA C", "FATOR DE CRESCIMENTO"],
        "categoria": "Hormônios", "unidade": "ng/mL",
        "referencias": [
            {"sexo": "ambos", "idade_min": 18, "idade_max": 30,
             "critico_baixo": 50, "limite_baixo": 100, "otimo_min": 150,
             "otimo_max": 400, "limite_alto": 450, "critico_alto": 700},
            {"sexo": "ambos", "idade_min": 31, "idade_max": 120,
             "critico_baixo": 40, "limite_baixo": 80, "otimo_min": 100,
             "otimo_max": 250, "limite_alto": 300, "critico_alto": 500},
        ]
    },

    # ══════════════════════════════════════════════════════
    # IMUNOLOGIA / AUTOIMUNIDADE
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Anti-Transglutaminase IgA",
        "sinonimos": ["ANTI TRANSGLUTAMINASE IGA", "ANTI-TRANSGLUTAMINASE IGA",
                      "ANTI TRANSGLUTAMINASE IGA", "ANTITRANSGLUTAMINASE"],
        "categoria": "Imunologia", "unidade": "U/mL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 10, "limite_alto": 11, "critico_alto": 100}]
    },
    {
        "nome_oficial": "Fator Reumatoide",
        "sinonimos": ["FATOR REUMATOIDE", "FR", "WAALER-ROSE", "FATOR REUMATÓIDE"],
        "categoria": "Imunologia", "unidade": "UI/mL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 14, "limite_alto": 15, "critico_alto": 200}]
    },
    {
        "nome_oficial": "FAN (ANA)",
        "sinonimos": ["FAN", "ANA", "FATOR ANTINUCLEAR", "ANTICORPO ANTINUCLEAR"],
        "categoria": "Imunologia", "unidade": "",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 0, "limite_alto": 0, "critico_alto": 0}]
    },
    {
        "nome_oficial": "Célula Parietal (Anti-IgG)",
        "sinonimos": ["CELULA PARIETAL", "ANTICORPOS ANTI CELULA PARIETAL",
                      "CELULA PARIETAL, ANTICORPOS ANTI"],
        "categoria": "Imunologia", "unidade": "",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 0, "limite_alto": 0, "critico_alto": 0}]
    },

    # ══════════════════════════════════════════════════════
    # URINA
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Microalbuminúria",
        "sinonimos": ["MICROALBUMINURIA", "MICROALBUMINÚRIA", "ALBUMINA NA URINA",
                      "RELACAO ALBUMINA CREATININA"],
        "categoria": "Urina", "unidade": "mg/L",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 20, "limite_alto": 30, "critico_alto": 300}]
    },

    # ══════════════════════════════════════════════════════
    # INFECTOLOGIA
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Anti-HIV",
        "sinonimos": ["ANTI-HIV", "ANTI HIV", "HIV", "TESTE HIV"],
        "categoria": "Infectologia", "unidade": "",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 0, "limite_alto": 0, "critico_alto": 0}]
    },
    {
        "nome_oficial": "HBsAg (Hepatite B)",
        "sinonimos": ["HBSAG", "ANTIGENO DE SUPERFICIE HEPATITE B",
                      "HEPATITE B ANTIGENIO"],
        "categoria": "Infectologia", "unidade": "",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 0, "limite_alto": 0, "critico_alto": 0}]
    },
    {
        "nome_oficial": "Anti-HCV (Hepatite C)",
        "sinonimos": ["ANTI-HCV", "ANTI HCV", "HEPATITE C", "HCV"],
        "categoria": "Infectologia", "unidade": "",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 0, "limite_alto": 0, "critico_alto": 0}]
    },

    # ══════════════════════════════════════════════════════
    # EXAMES ADICIONAIS (encontrados nos PDFs Tommasi/Cremasco)
    # ══════════════════════════════════════════════════════

    # -- Hematologia extras --
    {
        "nome_oficial": "MPV",
        "sinonimos": ["MPV", "VOLUME PLAQUETARIO MEDIO", "M.P.V", "M.P.V."],
        "categoria": "Hemograma", "unidade": "fL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 5.0, "limite_baixo": 7.0, "otimo_min": 7.5,
            "otimo_max": 11.0, "limite_alto": 12.0, "critico_alto": 15.0}]
    },
    {
        "nome_oficial": "Neutrófilos Bastonetes",
        "sinonimos": ["BASTONETES", "NEUTROFILOS BASTONETES",
                      "NEUTRÓFILOS BASTONETES", "Neutr?filos Bastonetes"],
        "categoria": "Hemograma", "unidade": "%",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 3, "limite_alto": 5, "critico_alto": 10}]
    },
    {
        "nome_oficial": "NLR",
        "sinonimos": ["NLR", "RAZAO NEUTROFILOS LINFOCITOS",
                      "Razão Neutrófilos/Linfócitos (NLR)",
                      "Raz?o Neutr?filos/Linf?citos (NLR)"],
        "categoria": "Hemograma", "unidade": "",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0.5, "limite_baixo": 1.0, "otimo_min": 1.0,
            "otimo_max": 3.0, "limite_alto": 6.0, "critico_alto": 20.0}]
    },
    {
        "nome_oficial": "Reticulócitos",
        "sinonimos": ["RETICULOCITOS", "RETICULÓCITOS"],
        "categoria": "Hemograma", "unidade": "%",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0.1, "limite_baixo": 0.5, "otimo_min": 0.5,
            "otimo_max": 1.5, "limite_alto": 2.0, "critico_alto": 5.0}]
    },

    # -- Coagulação extras --
    {
        "nome_oficial": "TTPA",
        "sinonimos": ["TTPA", "PTTK", "P.T.T.K", "PLASMA TESTADO",
                      "TEMPO TROMBOPLASTIA PARCIAL ATIVADA"],
        "categoria": "Coagulação", "unidade": "s",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 15, "limite_baixo": 25, "otimo_min": 28,
            "otimo_max": 40, "limite_alto": 43, "critico_alto": 70}]
    },
    {
        "nome_oficial": "Atividade de Protrombina",
        "sinonimos": ["ATIVIDADE PROTROMBINA (QUICK)", "QUICK",
                      "ATIVIDADE DE PROTROMBINA"],
        "categoria": "Coagulação", "unidade": "%",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 30, "limite_baixo": 60, "otimo_min": 70,
            "otimo_max": 100, "limite_alto": 100, "critico_alto": 100}]
    },
    {
        "nome_oficial": "D-Dímero",
        "sinonimos": ["D-DIMERO", "DIMERO D", "D DIMERO"],
        "categoria": "Coagulação", "unidade": "ng/mL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
            "otimo_max": 250, "limite_alto": 500, "critico_alto": 2000}]
    },

    # -- Bioquímica extras --
    {
        "nome_oficial": "Glicemia Média Estimada",
        "sinonimos": ["GME", "GLICEMIA MEDIA ESTIMADA",
                      "Glicemia MÉDIA Estimada (GME)"],
        "categoria": "Glicemia", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 50, "limite_baixo": 70, "otimo_min": 80,
            "otimo_max": 117, "limite_alto": 140, "critico_alto": 250}]
    },
    {
        "nome_oficial": "Frutosamina",
        "sinonimos": ["FRUTOSAMINA", "PROTEINAS GLICOSILADAS",
                      "Frutosamina (Proteínas Glicosiladas)"],
        "categoria": "Glicemia", "unidade": "µmol/L",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 150, "limite_baixo": 190, "otimo_min": 205,
            "otimo_max": 270, "limite_alto": 285, "critico_alto": 400}]
    },
    {
        "nome_oficial": "Glicemia 1h Pós-Dextrosol",
        "sinonimos": ["GLICEMIA 1 HORA POS DEXTROSOL", "GLICEMIA 1H"],
        "categoria": "Glicemia", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 30, "limite_baixo": 50, "otimo_min": 60,
            "otimo_max": 140, "limite_alto": 180, "critico_alto": 300}]
    },
    {
        "nome_oficial": "Glicemia 2h Pós-Dextrosol",
        "sinonimos": ["GLICEMIA 2 HORAS APOS DEXTROSOL", "GLICEMIA 2H"],
        "categoria": "Glicemia", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 30, "limite_baixo": 50, "otimo_min": 60,
            "otimo_max": 120, "limite_alto": 140, "critico_alto": 300}]
    },
    {
        "nome_oficial": "HOMA-IR",
        "sinonimos": ["HOMA-IR", "HOMA IR", "INDICE HOMA"],
        "categoria": "Glicemia", "unidade": "",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0.5,
            "otimo_max": 2.0, "limite_alto": 2.5, "critico_alto": 10.0}]
    },

    # -- Função Renal extras --
    {
        "nome_oficial": "eRFG",
        "sinonimos": ["ERFG", "ETFG", "RITMO DE FILTRACAO GLOMERULAR",
                      "TAXA DE FILTRACAO GLOMERULAR"],
        "categoria": "Função Renal", "unidade": "mL/min/1.73m²",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 15, "limite_baixo": 60, "otimo_min": 90,
            "otimo_max": 120, "limite_alto": 150, "critico_alto": 200}]
    },
    {
        "nome_oficial": "BUN (Nitrogênio Ureico)",
        "sinonimos": ["BUN", "NITROGENIO UREICO", "NITROGÊNIO UREICO",
                      "Nitrogênio Ureico (BUN)"],
        "categoria": "Função Renal", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 2, "limite_baixo": 7, "otimo_min": 9,
            "otimo_max": 20, "limite_alto": 23, "critico_alto": 50}]
    },

    # -- Hormônios extras --
    {
        "nome_oficial": "Testosterona Livre",
        "sinonimos": ["TESTOSTERONA LIVRE", "TESTOSTERONE FREE",
                      "TESTOSTERONA LIVRE RESULTADO"],
        "categoria": "Hormônios", "unidade": "pg/mL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 50,
             "critico_baixo": 2, "limite_baixo": 8, "otimo_min": 15,
             "otimo_max": 40, "limite_alto": 55, "critico_alto": 100},
            {"sexo": "M", "idade_min": 51, "idade_max": 120,
             "critico_baixo": 2, "limite_baixo": 7, "otimo_min": 10,
             "otimo_max": 25, "limite_alto": 34, "critico_alto": 80},
        ]
    },
    {
        "nome_oficial": "T3 Reverso",
        "sinonimos": ["T3 REVERSO", "RT3", "REVERSE T3",
                      "Dosagem de T3 Reverso"],
        "categoria": "Tireoide", "unidade": "ng/mL",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 0.02, "limite_baixo": 0.09, "otimo_min": 0.10,
            "otimo_max": 0.25, "limite_alto": 0.35, "critico_alto": 0.80}]
    },

    # -- Vitaminas extras --
    {
        "nome_oficial": "Vitamina A (Retinol)",
        "sinonimos": ["VITAMINA A", "RETINOL", "DOSAGEM DE VITAMINA A",
                      "Dosagem de Vitamina A (Retinol)"],
        "categoria": "Vitaminas", "unidade": "mg/L",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0.1, "limite_baixo": 0.2, "otimo_min": 0.3,
            "otimo_max": 0.6, "limite_alto": 0.7, "critico_alto": 1.5}]
    },
    {
        "nome_oficial": "Homocisteína",
        "sinonimos": ["HOMOCISTEINA", "HOMOCISTEÍNA", "HOMOCISTEINA (PLASMA)",
                      "Dosagem de Homocisteína"],
        "categoria": "Marcadores Cardíacos", "unidade": "µmol/L",
        "referencias": [
            {"sexo": "M", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 2, "limite_baixo": 5, "otimo_min": 5,
             "otimo_max": 12, "limite_alto": 16, "critico_alto": 50},
            {"sexo": "F", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 2, "limite_baixo": 4, "otimo_min": 4,
             "otimo_max": 10, "limite_alto": 14, "critico_alto": 50},
        ]
    },
    {
        "nome_oficial": "Serotonina",
        "sinonimos": ["SEROTONINA", "5-HT", "5-HIDROXITRIPTAMINA",
                      "Dosagem de Serotonina Sérica"],
        "categoria": "Vitaminas", "unidade": "ng/mL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 50, "limite_baixo": 80, "otimo_min": 100,
            "otimo_max": 200, "limite_alto": 230, "critico_alto": 400}]
    },

    # -- Minerais extras --
    {
        "nome_oficial": "Cálcio Ionizado (mg/dL)",
        "sinonimos": ["CALCIO IONIZADO", "CÁLCIO IONIZADO",
                      "Cálcio Ionizado (Ca++) (em mg/dL)"],
        "categoria": "Minerais", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 3.0, "limite_baixo": 4.0, "otimo_min": 4.4,
            "otimo_max": 5.0, "limite_alto": 5.2, "critico_alto": 6.5}]
    },
    {
        "nome_oficial": "Cálcio Ionizado (mmol/L)",
        "sinonimos": ["Cálcio Ionizado (Ca++) (em mmol/L)"],
        "categoria": "Minerais", "unidade": "mmol/L",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 0.8, "limite_baixo": 1.0, "otimo_min": 1.1,
            "otimo_max": 1.25, "limite_alto": 1.3, "critico_alto": 1.6}]
    },
    {
        "nome_oficial": "Cálcio Ionizado (mEq/L)",
        "sinonimos": ["Cálcio Ionizado (Ca++) (em mEq/L)"],
        "categoria": "Minerais", "unidade": "mEq/L",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 1.5, "limite_baixo": 2.0, "otimo_min": 2.1,
            "otimo_max": 2.5, "limite_alto": 2.6, "critico_alto": 3.5}]
    },
    {
        "nome_oficial": "Reserva Alcalina",
        "sinonimos": ["RESERVA ALCALINA", "BICARBONATO", "HCO3",
                      "RESERVA ALCALINA - BICARBONATO"],
        "categoria": "Minerais", "unidade": "mEq/L",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 10, "limite_baixo": 18, "otimo_min": 22,
            "otimo_max": 27, "limite_alto": 29, "critico_alto": 40}]
    },
    {
        "nome_oficial": "Cloro",
        "sinonimos": ["CLORO", "CLORETO", "CL"],
        "categoria": "Minerais", "unidade": "mEq/L",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 85, "limite_baixo": 96, "otimo_min": 98,
            "otimo_max": 104, "limite_alto": 106, "critico_alto": 115}]
    },

    # -- Ferro extras --
    {
        "nome_oficial": "Capacidade Total de Fixação do Ferro",
        "sinonimos": ["TIBC", "CAPACIDADE TOTAL DE FIXAÇÃO",
                      "CAPACIDADE TOTAL DE FIXACAO DO FERRO",
                      "CTFF", "CAPACIDADE TOTAL DE FIXAÇÃO DO FERRO"],
        "categoria": "Ferro", "unidade": "µg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 150, "limite_baixo": 220, "otimo_min": 250,
            "otimo_max": 380, "limite_alto": 425, "critico_alto": 600}]
    },

    # -- Proteínas extras --
    {
        "nome_oficial": "Globulinas",
        "sinonimos": ["GLOBULINAS", "GLOBULINA"],
        "categoria": "Proteínas", "unidade": "g/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 1.5, "limite_baixo": 2.0, "otimo_min": 2.3,
            "otimo_max": 3.5, "limite_alto": 4.0, "critico_alto": 6.0}]
    },

    # -- Imunologia extras --
    {
        "nome_oficial": "Imunoglobulina A (IgA)",
        "sinonimos": ["IGA", "IMUNOGLOBULINA A", "IMUNOGLOBULINA A - IGA"],
        "categoria": "Imunologia", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 30, "limite_baixo": 70, "otimo_min": 103,
            "otimo_max": 500, "limite_alto": 591, "critico_alto": 800}]
    },
    {
        "nome_oficial": "Imunoglobulina G (IgG)",
        "sinonimos": ["IGG", "IMUNOGLOBULINA G", "IMUNOGLOBULINA G - IGG"],
        "categoria": "Imunologia", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 18, "idade_max": 120,
            "critico_baixo": 200, "limite_baixo": 600, "otimo_min": 700,
            "otimo_max": 1400, "limite_alto": 1600, "critico_alto": 3000}]
    },
    {
        "nome_oficial": "Imunoglobulina M (IgM)",
        "sinonimos": ["IGM", "IMUNOGLOBULINA M", "IMUNOGLOBULINA M - IGM"],
        "categoria": "Imunologia", "unidade": "mg/dL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 10, "limite_baixo": 40, "otimo_min": 50,
             "otimo_max": 200, "limite_alto": 230, "critico_alto": 500},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 10, "limite_baixo": 40, "otimo_min": 50,
             "otimo_max": 240, "limite_alto": 280, "critico_alto": 500},
        ]
    },
    {
        "nome_oficial": "Colesterol Não-HDL",
        "sinonimos": ["COLESTEROL NAO-HDL", "COLESTEROL NÃO-HDL",
                      "Colesterol Não-HDL", "NAO-HDL"],
        "categoria": "Lipídios", "unidade": "mg/dL",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 30, "limite_baixo": 80, "otimo_min": 90,
            "otimo_max": 130, "limite_alto": 145, "critico_alto": 250}]
    },

    # ══════════════════════════════════════════════════════
    # MARCADORES TUMORAIS
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "PSA Livre",
        "sinonimos": ["PSA LIVRE", "ANTIGENO PROSTATICO LIVRE",
                      "ANTÍGENO PROSTÁTICO ESPECÍFICO LIVRE",
                      "PSA LIVRE RESULTADO"],
        "categoria": "Marcadores Tumorais", "unidade": "ng/mL",
        "referencias": [
            {"sexo": "M", "idade_min": 40, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 1.5, "limite_alto": 2.0, "critico_alto": 5.0},
        ]
    },
    {
        "nome_oficial": "PSA Livre/Total (%)",
        "sinonimos": ["PSA LIVRE/TOTAL", "RELACAO PSA LIVRE TOTAL",
                      "PORCENTAGEM PSA LIVRE", "% PSA LIVRE"],
        "categoria": "Marcadores Tumorais", "unidade": "%",
        "referencias": [
            {"sexo": "M", "idade_min": 40, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 15, "otimo_min": 20,
             "otimo_max": 100, "limite_alto": 100, "critico_alto": 100},
        ]
    },
    {
        "nome_oficial": "CEA",
        "sinonimos": ["CEA", "ANTIGENO CARCINOEMBRIONARIO",
                      "ANTÍGENO CARCINOEMBRIÔNICO", "CEA RESULTADO"],
        "categoria": "Marcadores Tumorais", "unidade": "ng/mL",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 3.4, "limite_alto": 5.0, "critico_alto": 20.0},
        ]
    },
    {
        "nome_oficial": "CA 19-9",
        "sinonimos": ["CA 19-9", "CA19-9", "CA-19-9",
                      "ANTIGENO CARBOIDRATO 19-9"],
        "categoria": "Marcadores Tumorais", "unidade": "U/mL",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 37.0, "limite_alto": 37.0, "critico_alto": 200.0},
        ]
    },
    {
        "nome_oficial": "AFP (Alfa-fetoproteína)",
        "sinonimos": ["AFP", "ALFA FETOPROTEINA", "ALFA-FETOPROTEÍNA",
                      "ALFAFETOPROTEINA", "AFP RESULTADO"],
        "categoria": "Marcadores Tumorais", "unidade": "ng/mL",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 7.0, "limite_alto": 10.0, "critico_alto": 400.0},
        ]
    },
    {
        "nome_oficial": "Beta-HCG",
        "sinonimos": ["BETA-HCG", "BETA HCG", "HCG", "GONADOTROFINA CORIONICA",
                      "GONADOTROFINA CORIÔNICA HUMANA", "B-HCG"],
        "categoria": "Marcadores Tumorais", "unidade": "mUI/mL",
        "referencias": [
            {"sexo": "M", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 2.5, "limite_alto": 5.0, "critico_alto": 50.0},
            {"sexo": "F", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 5.0, "limite_alto": 5.0, "critico_alto": 50.0},
        ]
    },
    {
        "nome_oficial": "CA 125",
        "sinonimos": ["CA 125", "CA-125", "CA125",
                      "ANTIGENO CARBOIDRATO 125"],
        "categoria": "Marcadores Tumorais", "unidade": "U/mL",
        "referencias": [
            {"sexo": "F", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 35.0, "limite_alto": 35.0, "critico_alto": 200.0},
        ]
    },
    {
        "nome_oficial": "CA 15-3",
        "sinonimos": ["CA 15-3", "CA-15-3", "CA15-3",
                      "ANTIGENO CARBOIDRATO 15-3"],
        "categoria": "Marcadores Tumorais", "unidade": "U/mL",
        "referencias": [
            {"sexo": "F", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 30.0, "limite_alto": 31.5, "critico_alto": 100.0},
        ]
    },
    {
        "nome_oficial": "Tireoglobulina",
        "sinonimos": ["TIREOGLOBULINA", "THYROGLOBULIN", "TG"],
        "categoria": "Tireoide", "unidade": "ng/mL",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 55.0, "limite_alto": 55.0, "critico_alto": 300.0},
        ]
    },

    # ══════════════════════════════════════════════════════
    # MARCADORES CARDÍACOS
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Troponina I",
        "sinonimos": ["TROPONINA I", "TROPONINA", "TROPONINA I CARDIACA",
                      "TROPONINA I CARDÍACA", "cTnI"],
        "categoria": "Marcadores Cardíacos", "unidade": "ng/mL",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 0.04, "limite_alto": 0.04, "critico_alto": 0.5},
        ]
    },
    {
        "nome_oficial": "Troponina I Ultrassensível",
        "sinonimos": ["TROPONINA I ULTRASSENSIVEL", "TROPONINA I US",
                      "TROPONINA I ULTRA SENSIVEL", "hs-cTnI",
                      "TROPONINA I ALTA SENSIBILIDADE"],
        "categoria": "Marcadores Cardíacos", "unidade": "ng/L",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 34.0, "limite_alto": 34.0, "critico_alto": 500.0},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 16.0, "limite_alto": 16.0, "critico_alto": 500.0},
        ]
    },
    {
        "nome_oficial": "Troponina T",
        "sinonimos": ["TROPONINA T", "TROPONINA T CARDIACA",
                      "TROPONINA T CARDÍACA", "cTnT", "TROPONINA T US",
                      "TROPONINA T ULTRASSENSIVEL"],
        "categoria": "Marcadores Cardíacos", "unidade": "ng/L",
        "referencias": [
            {"sexo": "ambos", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 14.0, "limite_alto": 14.0, "critico_alto": 300.0},
        ]
    },
    {
        "nome_oficial": "BNP",
        "sinonimos": ["BNP", "PEPTIDEO NATRIURETICO CEREBRAL",
                      "PEPTÍDEO NATRIURÉTICO TIPO B",
                      "BRAIN NATRIURETIC PEPTIDE"],
        "categoria": "Marcadores Cardíacos", "unidade": "pg/mL",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 75,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 35.0, "limite_alto": 100.0, "critico_alto": 400.0},
            {"sexo": "ambos", "idade_min": 76, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 35.0, "limite_alto": 125.0, "critico_alto": 400.0},
        ]
    },
    {
        "nome_oficial": "NT-proBNP",
        "sinonimos": ["NT-PROBNP", "NT PROBNP", "PRO-BNP",
                      "N-TERMINAL PRO-BNP", "NT-PRO-BNP"],
        "categoria": "Marcadores Cardíacos", "unidade": "pg/mL",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 50,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 125.0, "limite_alto": 300.0, "critico_alto": 1800.0},
            {"sexo": "ambos", "idade_min": 51, "idade_max": 75,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 125.0, "limite_alto": 900.0, "critico_alto": 5000.0},
            {"sexo": "ambos", "idade_min": 76, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 125.0, "limite_alto": 1800.0, "critico_alto": 10000.0},
        ]
    },
    {
        "nome_oficial": "Mioglobina",
        "sinonimos": ["MIOGLOBINA", "MYOGLOBIN"],
        "categoria": "Marcadores Cardíacos", "unidade": "ng/mL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 72.0, "limite_alto": 90.0, "critico_alto": 500.0},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 58.0, "limite_alto": 70.0, "critico_alto": 400.0},
        ]
    },
    {
        "nome_oficial": "PCR Ultrassensível",
        "sinonimos": ["PCR ULTRASSENSIVEL", "PCR US", "PCR ALTA SENSIBILIDADE",
                      "PROTEINA C REATIVA ULTRASSENSIVEL",
                      "PROTEÍNA C REATIVA ULTRASSENSÍVEL",
                      "hs-CRP", "PCR-US"],
        "categoria": "Marcadores Cardíacos", "unidade": "mg/L",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 1.0, "limite_alto": 3.0, "critico_alto": 10.0},
        ]
    },
    # ══════════════════════════════════════════════════════
    # HORMÔNIOS — COMPLEMENTARES
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Progesterona",
        "sinonimos": ["PROGESTERONA", "PROGESTERONA SERICA",
                      "PROGESTERONA SÉRICA", "Progesterona"],
        "categoria": "Hormônios", "unidade": "ng/mL",
        "referencias": [
            {"sexo": "F", "idade_min": 18, "idade_max": 50,
             "critico_baixo": 0.1, "limite_baixo": 0.2, "otimo_min": 0.5,
             "otimo_max": 1.5, "limite_alto": 1.5, "critico_alto": 5.0,
             "obs": "Fase folicular"},
            {"sexo": "F", "idade_min": 18, "idade_max": 50,
             "critico_baixo": 5.0, "limite_baixo": 5.0, "otimo_min": 7.0,
             "otimo_max": 25.0, "limite_alto": 30.0, "critico_alto": 60.0,
             "obs": "Fase lútea"},
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0.1, "otimo_min": 0.2,
             "otimo_max": 1.4, "limite_alto": 1.5, "critico_alto": 5.0},
        ]
    },
    {
        "nome_oficial": "Androstenediona",
        "sinonimos": ["ANDROSTENEDIONA", "ANDROSTENEDIONE",
                      "ANDROSTENEDIONA RESULTADO"],
        "categoria": "Hormônios", "unidade": "ng/mL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 0.3, "limite_baixo": 0.7, "otimo_min": 0.8,
             "otimo_max": 2.5, "limite_alto": 3.1, "critico_alto": 6.0},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 0.2, "limite_baixo": 0.5, "otimo_min": 0.8,
             "otimo_max": 3.0, "limite_alto": 3.4, "critico_alto": 7.0},
        ]
    },

    # ══════════════════════════════════════════════════════
    # FUNÇÃO RENAL — AVANÇADA
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Cistatina C",
        "sinonimos": ["CISTATINA C", "CYSTATIN C", "CISTATINA"],
        "categoria": "Função Renal", "unidade": "mg/L",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 1,
             "critico_baixo": 0, "limite_baixo": 0.8, "otimo_min": 0.8,
             "otimo_max": 2.3, "limite_alto": 2.5, "critico_alto": 5.0,
             "obs": "0-12 meses"},
            {"sexo": "ambos", "idade_min": 1, "idade_max": 18,
             "critico_baixo": 0, "limite_baixo": 0.5, "otimo_min": 0.5,
             "otimo_max": 1.0, "limite_alto": 1.1, "critico_alto": 3.0,
             "obs": "1-18 anos"},
            {"sexo": "ambos", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0.56, "otimo_min": 0.6,
             "otimo_max": 0.98, "limite_alto": 1.2, "critico_alto": 3.0,
             "obs": "adultos"},
        ]
    },
    {
        "nome_oficial": "Microalbuminúria 24h",
        "sinonimos": ["MICROALBUMINURIA 24H", "MICROALBUMINÚRIA 24 HORAS",
                      "ALBUMINA URINA 24H", "PROTEINURIA 24H"],
        "categoria": "Função Renal", "unidade": "mg/24h",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 30.0, "limite_alto": 300.0, "critico_alto": 3000.0},
        ]
    },
    {
        "nome_oficial": "Relação Albumina/Creatinina (urina)",
        "sinonimos": ["RELACAO ALBUMINA CREATININA URINA",
                      "RAZAO ALBUMINA CREATININA",
                      "ACR URINA", "ALBUMINA/CREATININA URINARIA"],
        "categoria": "Função Renal", "unidade": "mg/g",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 30.0, "limite_alto": 300.0, "critico_alto": 3000.0},
        ]
    },
    {
        "nome_oficial": "Creatinina Urinária",
        "sinonimos": ["CREATININA URINARIA", "CREATININA NA URINA",
                      "CREATININA URINA 24H"],
        "categoria": "Função Renal", "unidade": "mg/dL",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 20, "limite_baixo": 40, "otimo_min": 60,
             "otimo_max": 200, "limite_alto": 300, "critico_alto": 400},
        ]
    },

    # ══════════════════════════════════════════════════════
    # LIPÍDIOS — COMPLEMENTARES
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Apolipoproteína B",
        "sinonimos": ["APOLIPOPROTEINA B", "APOLIPOPROTEÍNA B",
                      "APO B", "APOB"],
        "categoria": "Lipídios", "unidade": "mg/dL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 20, "limite_baixo": 55, "otimo_min": 60,
             "otimo_max": 100, "limite_alto": 130, "critico_alto": 200},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 20, "limite_baixo": 55, "otimo_min": 60,
             "otimo_max": 100, "limite_alto": 130, "critico_alto": 200},
        ]
    },
    {
        "nome_oficial": "Apolipoproteína A-I",
        "sinonimos": ["APOLIPOPROTEINA A1", "APOLIPOPROTEÍNA A-I",
                      "APO A", "APOA1"],
        "categoria": "Lipídios", "unidade": "mg/dL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 50, "limite_baixo": 94, "otimo_min": 120,
             "otimo_max": 180, "limite_alto": 200, "critico_alto": 300},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 50, "limite_baixo": 101, "otimo_min": 120,
             "otimo_max": 200, "limite_alto": 220, "critico_alto": 300},
        ]
    },
    {
        "nome_oficial": "Lipoproteína (a)",
        "sinonimos": ["LPA", "LIPOPROTEINA A", "LIPOPROTEÍNA (A)",
                      "Lp(a)"],
        "categoria": "Lipídios", "unidade": "mg/dL",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 0,
             "otimo_max": 30.0, "limite_alto": 50.0, "critico_alto": 100.0},
        ]
    },

    # ══════════════════════════════════════════════════════
    # VITAMINAS — COMPLEMENTARES
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Vitamina E (alfa-tocoferol)",
        "sinonimos": ["VITAMINA E", "ALFA TOCOFEROL",
                      "DOSAGEM DE VITAMINA E",
                      "Dosagem de Vitamina E (alfa-tocoferol)"],
        "categoria": "Vitaminas", "unidade": "mg/L",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 3.0, "limite_baixo": 5.0, "otimo_min": 7.0,
             "otimo_max": 18.0, "limite_alto": 20.0, "critico_alto": 40.0},
        ]
    },

    # ══════════════════════════════════════════════════════
    # MINERAIS — COMPLEMENTARES
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Cobre",
        "sinonimos": ["COBRE", "COPPER", "COBRE SERICO",
                      "DOSAGEM DE COBRE"],
        "categoria": "Minerais", "unidade": "µg/dL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 40, "limite_baixo": 70, "otimo_min": 80,
             "otimo_max": 130, "limite_alto": 140, "critico_alto": 250},
            {"sexo": "F", "idade_min": 18, "idade_max": 120,
             "critico_baixo": 50, "limite_baixo": 80, "otimo_min": 85,
             "otimo_max": 155, "limite_alto": 170, "critico_alto": 300},
        ]
    },
    {
        "nome_oficial": "Selênio",
        "sinonimos": ["SELENIO", "SELÊNIO", "SELENIUM",
                      "DOSAGEM DE SELENIO"],
        "categoria": "Minerais", "unidade": "µg/L",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 40, "limite_baixo": 70, "otimo_min": 100,
             "otimo_max": 160, "limite_alto": 200, "critico_alto": 400},
        ]
    },

    # ══════════════════════════════════════════════════════
    # HEMOGRAMA PEDIÁTRICO — FAIXAS ETÁRIAS EXPANDIDAS
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Hemoglobina (RN)",
        "sinonimos": ["HEMOGLOBINA RN", "HB RECEM NASCIDO"],
        "categoria": "Hemograma Pediátrico", "unidade": "g/dL",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 0,
             "critico_baixo": 10.0, "limite_baixo": 14.0, "otimo_min": 16.0,
             "otimo_max": 19.0, "limite_alto": 22.0, "critico_alto": 24.0,
             "obs": "RN 0-28 dias"},
            {"sexo": "ambos", "idade_min": 0, "idade_max": 2,
             "critico_baixo": 7.0, "limite_baixo": 9.5, "otimo_min": 10.0,
             "otimo_max": 14.0, "limite_alto": 15.0, "critico_alto": 20.0,
             "obs": "1-2 meses"},
            {"sexo": "ambos", "idade_min": 2, "idade_max": 6,
             "critico_baixo": 7.0, "limite_baixo": 9.5, "otimo_min": 10.0,
             "otimo_max": 13.5, "limite_alto": 14.0, "critico_alto": 18.0,
             "obs": "2-6 meses"},
            {"sexo": "ambos", "idade_min": 6, "idade_max": 24,
             "critico_baixo": 7.0, "limite_baixo": 10.5, "otimo_min": 11.0,
             "otimo_max": 13.5, "limite_alto": 14.0, "critico_alto": 18.0,
             "obs": "6m-2 anos"},
            {"sexo": "ambos", "idade_min": 2, "idade_max": 6,
             "critico_baixo": 7.0, "limite_baixo": 11.0, "otimo_min": 11.5,
             "otimo_max": 13.5, "limite_alto": 14.0, "critico_alto": 18.0,
             "obs": "2-6 anos"},
            {"sexo": "ambos", "idade_min": 6, "idade_max": 12,
             "critico_baixo": 7.0, "limite_baixo": 11.5, "otimo_min": 12.0,
             "otimo_max": 14.5, "limite_alto": 15.5, "critico_alto": 18.0,
             "obs": "6-12 anos"},
            {"sexo": "M", "idade_min": 12, "idade_max": 18,
             "critico_baixo": 7.0, "limite_baixo": 13.0, "otimo_min": 14.0,
             "otimo_max": 16.0, "limite_alto": 16.5, "critico_alto": 20.0,
             "obs": "12-18 anos M"},
            {"sexo": "F", "idade_min": 12, "idade_max": 18,
             "critico_baixo": 7.0, "limite_baixo": 12.0, "otimo_min": 12.5,
             "otimo_max": 15.0, "limite_alto": 16.0, "critico_alto": 19.0,
             "obs": "12-18 anos F"},
        ]
    },
    {
        "nome_oficial": "Leucócitos (Pediátrico)",
        "sinonimos": ["LEUCOCITOS PEDIATRICO", "WBC PEDIATRICO",
                      "LEUCOCITOS CRIANCA"],
        "categoria": "Hemograma Pediátrico", "unidade": "/mm³",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 0,
             "critico_baixo": 5000, "limite_baixo": 9000, "otimo_min": 10000,
             "otimo_max": 26000, "limite_alto": 30000, "critico_alto": 50000,
             "obs": "RN 0-28 dias"},
            {"sexo": "ambos", "idade_min": 0, "idade_max": 1,
             "critico_baixo": 4000, "limite_baixo": 6000, "otimo_min": 8000,
             "otimo_max": 17000, "limite_alto": 20000, "critico_alto": 40000,
             "obs": "1-12 meses"},
            {"sexo": "ambos", "idade_min": 1, "idade_max": 6,
             "critico_baixo": 3000, "limite_baixo": 5000, "otimo_min": 6000,
             "otimo_max": 15000, "limite_alto": 17000, "critico_alto": 30000,
             "obs": "1-6 anos"},
            {"sexo": "ambos", "idade_min": 6, "idade_max": 12,
             "critico_baixo": 2500, "limite_baixo": 4500, "otimo_min": 5000,
             "otimo_max": 13000, "limite_alto": 15000, "critico_alto": 30000,
             "obs": "6-12 anos"},
            {"sexo": "ambos", "idade_min": 12, "idade_max": 18,
             "critico_baixo": 2000, "limite_baixo": 4000, "otimo_min": 4500,
             "otimo_max": 11000, "limite_alto": 13000, "critico_alto": 30000,
             "obs": "12-18 anos"},
        ]
    },
    {
        "nome_oficial": "TSH (Pediátrico)",
        "sinonimos": ["TSH PEDIATRICO", "TSH RECEM NASCIDO", "TSH CRIANCA"],
        "categoria": "Tireoide Pediátrica", "unidade": "mUI/L",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 0,
             "critico_baixo": 0.2, "limite_baixo": 0.7, "otimo_min": 1.0,
             "otimo_max": 10.0, "limite_alto": 15.2, "critico_alto": 30.0,
             "obs": "RN 0-5 dias"},
            {"sexo": "ambos", "idade_min": 0, "idade_max": 3,
             "critico_baixo": 0.2, "limite_baixo": 0.72, "otimo_min": 1.0,
             "otimo_max": 8.0, "limite_alto": 11.0, "critico_alto": 20.0,
             "obs": "6-90 dias"},
            {"sexo": "ambos", "idade_min": 3, "idade_max": 12,
             "critico_baixo": 0.2, "limite_baixo": 0.73, "otimo_min": 1.0,
             "otimo_max": 6.0, "limite_alto": 8.35, "critico_alto": 15.0,
             "obs": "4-12 meses"},
            {"sexo": "ambos", "idade_min": 1, "idade_max": 6,
             "critico_baixo": 0.2, "limite_baixo": 0.7, "otimo_min": 1.0,
             "otimo_max": 5.0, "limite_alto": 5.97, "critico_alto": 12.0,
             "obs": "1-6 anos"},
            {"sexo": "ambos", "idade_min": 7, "idade_max": 11,
             "critico_baixo": 0.2, "limite_baixo": 0.6, "otimo_min": 1.0,
             "otimo_max": 4.0, "limite_alto": 4.84, "critico_alto": 10.0,
             "obs": "7-11 anos"},
            {"sexo": "ambos", "idade_min": 12, "idade_max": 20,
             "critico_baixo": 0.1, "limite_baixo": 0.51, "otimo_min": 1.0,
             "otimo_max": 3.5, "limite_alto": 4.3, "critico_alto": 10.0,
             "obs": "12-20 anos"},
        ]
    },
    {
        "nome_oficial": "Creatinina (Pediátrica)",
        "sinonimos": ["CREATININA PEDIATRICA", "CREATININA CRIANCA"],
        "categoria": "Função Renal Pediátrica", "unidade": "mg/dL",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 0,
             "critico_baixo": 0.2, "limite_baixo": 0.3, "otimo_min": 0.4,
             "otimo_max": 0.9, "limite_alto": 1.0, "critico_alto": 2.0,
             "obs": "RN"},
            {"sexo": "ambos", "idade_min": 0, "idade_max": 1,
             "critico_baixo": 0.1, "limite_baixo": 0.2, "otimo_min": 0.2,
             "otimo_max": 0.5, "limite_alto": 0.6, "critico_alto": 1.5,
             "obs": "1-12 meses"},
            {"sexo": "ambos", "idade_min": 1, "idade_max": 3,
             "critico_baixo": 0.1, "limite_baixo": 0.2, "otimo_min": 0.3,
             "otimo_max": 0.6, "limite_alto": 0.7, "critico_alto": 1.5,
             "obs": "1-3 anos"},
            {"sexo": "ambos", "idade_min": 3, "idade_max": 7,
             "critico_baixo": 0.1, "limite_baixo": 0.25, "otimo_min": 0.3,
             "otimo_max": 0.7, "limite_alto": 0.8, "critico_alto": 1.5,
             "obs": "3-7 anos"},
            {"sexo": "ambos", "idade_min": 7, "idade_max": 10,
             "critico_baixo": 0.1, "limite_baixo": 0.3, "otimo_min": 0.4,
             "otimo_max": 0.8, "limite_alto": 0.9, "critico_alto": 2.0,
             "obs": "7-10 anos"},
            {"sexo": "ambos", "idade_min": 10, "idade_max": 14,
             "critico_baixo": 0.1, "limite_baixo": 0.4, "otimo_min": 0.5,
             "otimo_max": 0.9, "limite_alto": 1.0, "critico_alto": 2.5,
             "obs": "10-14 anos"},
            {"sexo": "M", "idade_min": 14, "idade_max": 18,
             "critico_baixo": 0.2, "limite_baixo": 0.5, "otimo_min": 0.6,
             "otimo_max": 1.1, "limite_alto": 1.2, "critico_alto": 2.5,
             "obs": "14-18 anos M"},
            {"sexo": "F", "idade_min": 14, "idade_max": 18,
             "critico_baixo": 0.2, "limite_baixo": 0.4, "otimo_min": 0.5,
             "otimo_max": 1.0, "limite_alto": 1.1, "critico_alto": 2.0,
             "obs": "14-18 anos F"},
        ]
    },
    {
        "nome_oficial": "Fosfatase Alcalina (Pediátrica)",
        "sinonimos": ["FOSFATASE ALCALINA PEDIATRICA", "ALP PEDIATRICA"],
        "categoria": "Função Hepática Pediátrica", "unidade": "U/L",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 1,
             "critico_baixo": 50, "limite_baixo": 100, "otimo_min": 150,
             "otimo_max": 450, "limite_alto": 500, "critico_alto": 1000,
             "obs": "0-12 meses"},
            {"sexo": "ambos", "idade_min": 1, "idade_max": 10,
             "critico_baixo": 50, "limite_baixo": 100, "otimo_min": 150,
             "otimo_max": 350, "limite_alto": 400, "critico_alto": 800,
             "obs": "1-10 anos"},
            {"sexo": "M", "idade_min": 10, "idade_max": 18,
             "critico_baixo": 50, "limite_baixo": 100, "otimo_min": 150,
             "otimo_max": 500, "limite_alto": 700, "critico_alto": 1200,
             "obs": "10-18 anos M (pico pubertário)"},
            {"sexo": "F", "idade_min": 10, "idade_max": 18,
             "critico_baixo": 50, "limite_baixo": 100, "otimo_min": 130,
             "otimo_max": 400, "limite_alto": 500, "critico_alto": 900,
             "obs": "10-18 anos F"},
        ]
    },
    {
        "nome_oficial": "Cálcio (Pediátrico)",
        "sinonimos": ["CALCIO PEDIATRICO", "CALCIO CRIANCA"],
        "categoria": "Minerais Pediátricos", "unidade": "mg/dL",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 0,
             "critico_baixo": 5.0, "limite_baixo": 7.5, "otimo_min": 8.0,
             "otimo_max": 10.5, "limite_alto": 11.0, "critico_alto": 13.0,
             "obs": "RN"},
            {"sexo": "ambos", "idade_min": 0, "idade_max": 1,
             "critico_baixo": 6.0, "limite_baixo": 8.5, "otimo_min": 9.0,
             "otimo_max": 11.0, "limite_alto": 11.5, "critico_alto": 14.0,
             "obs": "1-12 meses"},
            {"sexo": "ambos", "idade_min": 1, "idade_max": 12,
             "critico_baixo": 6.5, "limite_baixo": 8.8, "otimo_min": 9.2,
             "otimo_max": 10.8, "limite_alto": 11.0, "critico_alto": 13.5,
             "obs": "1-12 anos"},
        ]
    },
    {
        "nome_oficial": "Fósforo (Pediátrico)",
        "sinonimos": ["FOSFORO PEDIATRICO", "FOSFATO PEDIATRICO"],
        "categoria": "Minerais Pediátricos", "unidade": "mg/dL",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 0,
             "critico_baixo": 2.5, "limite_baixo": 4.0, "otimo_min": 4.5,
             "otimo_max": 9.0, "limite_alto": 9.5, "critico_alto": 12.0,
             "obs": "RN"},
            {"sexo": "ambos", "idade_min": 0, "idade_max": 1,
             "critico_baixo": 2.0, "limite_baixo": 3.8, "otimo_min": 4.5,
             "otimo_max": 7.5, "limite_alto": 8.0, "critico_alto": 10.0,
             "obs": "1-12 meses"},
            {"sexo": "ambos", "idade_min": 1, "idade_max": 6,
             "critico_baixo": 1.5, "limite_baixo": 3.5, "otimo_min": 4.0,
             "otimo_max": 6.5, "limite_alto": 7.0, "critico_alto": 9.0,
             "obs": "1-6 anos"},
            {"sexo": "ambos", "idade_min": 6, "idade_max": 12,
             "critico_baixo": 1.0, "limite_baixo": 3.0, "otimo_min": 3.5,
             "otimo_max": 5.5, "limite_alto": 6.0, "critico_alto": 8.0,
             "obs": "6-12 anos"},
        ]
    },
    {
        "nome_oficial": "Ureia (Pediátrica)",
        "sinonimos": ["UREIA PEDIATRICA", "UREIA CRIANCA", "BUN PEDIATRICO"],
        "categoria": "Função Renal Pediátrica", "unidade": "mg/dL",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 0,
             "critico_baixo": 2, "limite_baixo": 3, "otimo_min": 5,
             "otimo_max": 15, "limite_alto": 18, "critico_alto": 50,
             "obs": "RN"},
            {"sexo": "ambos", "idade_min": 0, "idade_max": 1,
             "critico_baixo": 2, "limite_baixo": 5, "otimo_min": 7,
             "otimo_max": 17, "limite_alto": 20, "critico_alto": 50,
             "obs": "1-12 meses"},
            {"sexo": "ambos", "idade_min": 1, "idade_max": 18,
             "critico_baixo": 2, "limite_baixo": 7, "otimo_min": 10,
             "otimo_max": 17, "limite_alto": 20, "critico_alto": 60,
             "obs": "1-18 anos"},
        ]
    },
    {
        "nome_oficial": "Ácido Úrico (Pediátrico)",
        "sinonimos": ["ACIDO URICO PEDIATRICO", "ACIDO URICO CRIANCA"],
        "categoria": "Função Renal Pediátrica", "unidade": "mg/dL",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 12,
             "critico_baixo": 0.5, "limite_baixo": 1.5, "otimo_min": 2.0,
             "otimo_max": 4.5, "limite_alto": 5.0, "critico_alto": 8.0,
             "obs": "crianças até 12 anos"},
            {"sexo": "M", "idade_min": 13, "idade_max": 18,
             "critico_baixo": 1.0, "limite_baixo": 3.0, "otimo_min": 3.5,
             "otimo_max": 6.0, "limite_alto": 7.0, "critico_alto": 10.0,
             "obs": "13-18 anos M"},
            {"sexo": "F", "idade_min": 13, "idade_max": 18,
             "critico_baixo": 1.0, "limite_baixo": 2.5, "otimo_min": 3.0,
             "otimo_max": 5.5, "limite_alto": 6.0, "critico_alto": 9.0,
             "obs": "13-18 anos F"},
        ]
    },
    {
        "nome_oficial": "Ferritina (Pediátrica)",
        "sinonimos": ["FERRITINA PEDIATRICA", "FERRITINA RECEM NASCIDO"],
        "categoria": "Ferro Pediátrico", "unidade": "ng/mL",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 0,
             "critico_baixo": 50, "limite_baixo": 100, "otimo_min": 200,
             "otimo_max": 600, "limite_alto": 700, "critico_alto": 1500,
             "obs": "RN"},
            {"sexo": "ambos", "idade_min": 0, "idade_max": 2,
             "critico_baixo": 20, "limite_baixo": 50, "otimo_min": 100,
             "otimo_max": 400, "limite_alto": 500, "critico_alto": 1000,
             "obs": "1-2 meses"},
            {"sexo": "ambos", "idade_min": 2, "idade_max": 5,
             "critico_baixo": 5, "limite_baixo": 7, "otimo_min": 10,
             "otimo_max": 80, "limite_alto": 100, "critico_alto": 500,
             "obs": "2-5 meses"},
            {"sexo": "ambos", "idade_min": 5, "idade_max": 12,
             "critico_baixo": 5, "limite_baixo": 7, "otimo_min": 10,
             "otimo_max": 140, "limite_alto": 160, "critico_alto": 500,
             "obs": "6 meses-12 anos"},
            {"sexo": "M", "idade_min": 12, "idade_max": 18,
             "critico_baixo": 5, "limite_baixo": 12, "otimo_min": 25,
             "otimo_max": 150, "limite_alto": 200, "critico_alto": 500,
             "obs": "12-18 anos M"},
            {"sexo": "F", "idade_min": 12, "idade_max": 18,
             "critico_baixo": 5, "limite_baixo": 10, "otimo_min": 20,
             "otimo_max": 100, "limite_alto": 130, "critico_alto": 400,
             "obs": "12-18 anos F"},
        ]
    },
    {
        "nome_oficial": "FSH (com fases)",
        "sinonimos": ["FSH FEMININO", "FSH FASES", "FSH FASE FOLICULAR",
                      "FSH FOLICULO ESTIMULANTE FEMININO"],
        "categoria": "Hormônios", "unidade": "mUI/mL",
        "referencias": [
            {"sexo": "F", "idade_min": 18, "idade_max": 50,
             "critico_baixo": 0.5, "limite_baixo": 2.8, "otimo_min": 3.0,
             "otimo_max": 11.3, "limite_alto": 12.0, "critico_alto": 20.0,
             "obs": "Fase folicular"},
            {"sexo": "F", "idade_min": 18, "idade_max": 50,
             "critico_baixo": 5.0, "limite_baixo": 12.0, "otimo_min": 14.0,
             "otimo_max": 24.0, "limite_alto": 25.0, "critico_alto": 40.0,
             "obs": "Pico ovulatório"},
            {"sexo": "F", "idade_min": 18, "idade_max": 50,
             "critico_baixo": 0.5, "limite_baixo": 1.2, "otimo_min": 2.0,
             "otimo_max": 9.0, "limite_alto": 12.0, "critico_alto": 20.0,
             "obs": "Fase lútea"},
            {"sexo": "F", "idade_min": 50, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 25.8, "otimo_min": 30.0,
             "otimo_max": 100.0, "limite_alto": 134.8, "critico_alto": 300.0,
             "obs": "Pós-menopausa"},
        ]
    },
    {
        "nome_oficial": "LH (com fases)",
        "sinonimos": ["LH FEMININO", "LH FASES", "LH FASE FOLICULAR"],
        "categoria": "Hormônios", "unidade": "mUI/mL",
        "referencias": [
            {"sexo": "F", "idade_min": 18, "idade_max": 50,
             "critico_baixo": 0.5, "limite_baixo": 1.1, "otimo_min": 2.0,
             "otimo_max": 11.6, "limite_alto": 12.0, "critico_alto": 20.0,
             "obs": "Fase folicular"},
            {"sexo": "F", "idade_min": 18, "idade_max": 50,
             "critico_baixo": 10.0, "limite_baixo": 17.0, "otimo_min": 20.0,
             "otimo_max": 77.0, "limite_alto": 80.0, "critico_alto": 150.0,
             "obs": "Pico ovulatório"},
            {"sexo": "F", "idade_min": 18, "idade_max": 50,
             "critico_baixo": 0.5, "limite_baixo": 1.0, "otimo_min": 1.5,
             "otimo_max": 14.7, "limite_alto": 15.0, "critico_alto": 30.0,
             "obs": "Fase lútea"},
            {"sexo": "F", "idade_min": 50, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 11.3, "otimo_min": 15.0,
             "otimo_max": 50.0, "limite_alto": 75.0, "critico_alto": 200.0,
             "obs": "Pós-menopausa"},
        ]
    },
    {
        "nome_oficial": "Estradiol (com fases)",
        "sinonimos": ["ESTRADIOL FEMININO", "ESTRADIOL FASES",
                      "E2 FEMININO", "ESTRADIOL FASE FOLICULAR"],
        "categoria": "Hormônios", "unidade": "pg/mL",
        "referencias": [
            {"sexo": "F", "idade_min": 18, "idade_max": 50,
             "critico_baixo": 10, "limite_baixo": 30, "otimo_min": 40,
             "otimo_max": 100, "limite_alto": 150, "critico_alto": 300,
             "obs": "Fase folicular precoce"},
            {"sexo": "F", "idade_min": 18, "idade_max": 50,
             "critico_baixo": 50, "limite_baixo": 100, "otimo_min": 150,
             "otimo_max": 500, "limite_alto": 700, "critico_alto": 1500,
             "obs": "Pico pré-ovulatório"},
            {"sexo": "F", "idade_min": 18, "idade_max": 50,
             "critico_baixo": 20, "limite_baixo": 70, "otimo_min": 80,
             "otimo_max": 300, "limite_alto": 400, "critico_alto": 800,
             "obs": "Fase lútea"},
            {"sexo": "F", "idade_min": 50, "idade_max": 120,
             "critico_baixo": 0, "limite_baixo": 0, "otimo_min": 5,
             "otimo_max": 30, "limite_alto": 40, "critico_alto": 100,
             "obs": "Pós-menopausa"},
        ]
    },
    {
        "nome_oficial": "DHEA-S (com faixas etárias)",
        "sinonimos": ["DHEA-S FAIXAS", "DHEAS ETARIO"],
        "categoria": "Hormônios", "unidade": "µg/dL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 30,
             "critico_baixo": 100, "limite_baixo": 160, "otimo_min": 250,
             "otimo_max": 500, "limite_alto": 560, "critico_alto": 800,
             "obs": "18-30 anos M"},
            {"sexo": "M", "idade_min": 31, "idade_max": 40,
             "critico_baixo": 80, "limite_baixo": 120, "otimo_min": 200,
             "otimo_max": 440, "limite_alto": 500, "critico_alto": 750,
             "obs": "31-40 anos M"},
            {"sexo": "M", "idade_min": 41, "idade_max": 50,
             "critico_baixo": 60, "limite_baixo": 90, "otimo_min": 150,
             "otimo_max": 350, "limite_alto": 400, "critico_alto": 700,
             "obs": "41-50 anos M"},
            {"sexo": "M", "idade_min": 51, "idade_max": 120,
             "critico_baixo": 30, "limite_baixo": 60, "otimo_min": 100,
             "otimo_max": 250, "limite_alto": 310, "critico_alto": 600,
             "obs": ">50 anos M"},
            {"sexo": "F", "idade_min": 18, "idade_max": 30,
             "critico_baixo": 60, "limite_baixo": 95, "otimo_min": 150,
             "otimo_max": 380, "limite_alto": 430, "critico_alto": 700,
             "obs": "18-30 anos F"},
            {"sexo": "F", "idade_min": 31, "idade_max": 50,
             "critico_baixo": 40, "limite_baixo": 65, "otimo_min": 100,
             "otimo_max": 340, "limite_alto": 380, "critico_alto": 650,
             "obs": "31-50 anos F"},
            {"sexo": "F", "idade_min": 51, "idade_max": 120,
             "critico_baixo": 20, "limite_baixo": 30, "otimo_min": 60,
             "otimo_max": 230, "limite_alto": 260, "critico_alto": 500,
             "obs": ">50 anos F"},
        ]
    },
    {
        "nome_oficial": "Testosterona Total (com faixas etárias)",
        "sinonimos": ["TESTOSTERONA TOTAL ETARIA", "TESTOSTERONA FAIXAS"],
        "categoria": "Hormônios", "unidade": "ng/dL",
        "referencias": [
            {"sexo": "M", "idade_min": 18, "idade_max": 40,
             "critico_baixo": 100, "limite_baixo": 300, "otimo_min": 500,
             "otimo_max": 900, "limite_alto": 1000, "critico_alto": 1500,
             "obs": "18-40 anos M"},
            {"sexo": "M", "idade_min": 41, "idade_max": 60,
             "critico_baixo": 100, "limite_baixo": 280, "otimo_min": 400,
             "otimo_max": 800, "limite_alto": 900, "critico_alto": 1300,
             "obs": "41-60 anos M"},
            {"sexo": "M", "idade_min": 61, "idade_max": 120,
             "critico_baixo": 80, "limite_baixo": 200, "otimo_min": 350,
             "otimo_max": 700, "limite_alto": 800, "critico_alto": 1200,
             "obs": ">60 anos M"},
            {"sexo": "F", "idade_min": 18, "idade_max": 50,
             "critico_baixo": 5, "limite_baixo": 15, "otimo_min": 20,
             "otimo_max": 70, "limite_alto": 80, "critico_alto": 200,
             "obs": "18-50 anos F"},
            {"sexo": "F", "idade_min": 51, "idade_max": 120,
             "critico_baixo": 2, "limite_baixo": 10, "otimo_min": 15,
             "otimo_max": 55, "limite_alto": 70, "critico_alto": 150,
             "obs": ">50 anos F (pós-menopausa)"},
        ]
    },

    # ══════════════════════════════════════════════════════
    # COAGULAÇÃO — COMPLEMENTAR
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Tempo de Trombina",
        "sinonimos": ["TEMPO DE TROMBINA", "TT", "TROMBINA TIME"],
        "categoria": "Coagulação", "unidade": "seg",
        "referencias": [
            {"sexo": "ambos", "idade_min": 0, "idade_max": 120,
             "critico_baixo": 5, "limite_baixo": 12, "otimo_min": 14,
             "otimo_max": 19, "limite_alto": 21, "critico_alto": 40},
        ]
    },

    # ══════════════════════════════════════════════════════
    # EXAMES DE IMAGEM (laudos — sem valores numéricos)
    # ══════════════════════════════════════════════════════
    {
        "nome_oficial": "Ecocardiograma",
        "sinonimos": ["ECOCARDIOGRAMA", "ECOCARDIOGRAMA COM ESTRESSE",
                      "ECOCARDIOGRAMA COM ESTRESSE FARMACOLÓGICO",
                      "ECOCARDIOGRAMA TRANSTORÁCICO", "ECO DOPPLER"],
        "categoria": "Cardiologia", "unidade": "",
        "referencias": []
    },
    {
        "nome_oficial": "MAPA",
        "sinonimos": ["MAPA", "M.A.P.A.", "MAPEAMENTO AMBULATORIAL",
                      "MONITORIZAÇÃO AMBULATORIAL DA PRESSÃO ARTERIAL"],
        "categoria": "Cardiologia", "unidade": "",
        "referencias": []
    },
    {
        "nome_oficial": "Holter 24h",
        "sinonimos": ["HOLTER", "HOLTER 24H", "HOLTER 24 HORAS",
                      "MONITORIZAÇÃO ELETROCARDIOGRÁFICA"],
        "categoria": "Cardiologia", "unidade": "",
        "referencias": []
    },
    {
        "nome_oficial": "Eletrocardiograma",
        "sinonimos": ["ECG", "ELETROCARDIOGRAMA", "ECG REPOUSO"],
        "categoria": "Cardiologia", "unidade": "",
        "referencias": []
    },
    {
        "nome_oficial": "Teste Ergométrico",
        "sinonimos": ["TESTE ERGOMETRICO", "TESTE DE ESFORÇO",
                      "ERGOMETRIA"],
        "categoria": "Cardiologia", "unidade": "",
        "referencias": []
    },
    {
        "nome_oficial": "Doppler de Carótidas e Vertebrais",
        "sinonimos": ["DOPPLER DE CARÓTIDAS", "DOPPLER CAROTIDAS",
                      "DOPPLER DE CARÓTIDAS E VERTEBRAIS",
                      "ECODOPPLER DE CARÓTIDAS"],
        "categoria": "Vascular", "unidade": "",
        "referencias": []
    },
    {
        "nome_oficial": "Doppler Venoso de Membros Inferiores",
        "sinonimos": ["DOPPLER VENOSO MMII", "DOPPLER VENOSO",
                      "ECODOPPLER VENOSO DE MEMBROS INFERIORES"],
        "categoria": "Vascular", "unidade": "",
        "referencias": []
    },
    {
        "nome_oficial": "USG Rins e Vias Urinárias",
        "sinonimos": ["ULTRASSONOGRAFIA DOS RINS", "USG RENAL",
                      "ULTRASSONOGRAFIA: RINS, VIAS URINÁRIAS",
                      "ULTRASSONOGRAFIA DOS RINS E VIAS URINÁRIAS"],
        "categoria": "Imagem", "unidade": "",
        "referencias": []
    },
    {
        "nome_oficial": "USG Próstata",
        "sinonimos": ["ULTRASSONOGRAFIA DA PRÓSTATA",
                      "ULTRASSONOGRAFIA DA PRÓSTATA VIA ABDOMINAL",
                      "USG PROSTATA", "USG PROSTATA VIA ABDOMINAL"],
        "categoria": "Imagem", "unidade": "",
        "referencias": []
    },
    {
        "nome_oficial": "USG Abdome Total",
        "sinonimos": ["ULTRASSONOGRAFIA ABDOME TOTAL", "USG ABDOME",
                      "ULTRASSONOGRAFIA ABDOMINAL"],
        "categoria": "Imagem", "unidade": "",
        "referencias": []
    },
    {
        "nome_oficial": "USG Tireoide",
        "sinonimos": ["ULTRASSONOGRAFIA DA TIREOIDE", "USG TIREOIDE",
                      "ECOGRAFIA DA TIREOIDE"],
        "categoria": "Imagem", "unidade": "",
        "referencias": []
    },
    {
        "nome_oficial": "Campo Visual (Campimetria)",
        "sinonimos": ["CAMPO VISUAL", "CAMPIMETRIA", "PERIMETRIA",
                      "ANÁLISE DE CAMPO ÚNICO", "TESTE DE LIMIAR",
                      "Análise de Campo Único Central 24-2"],
        "categoria": "Oftalmologia", "unidade": "",
        "referencias": []
    },
    {
        "nome_oficial": "Retinografia",
        "sinonimos": ["RETINOGRAFIA", "RETINOGRAFIA COLORIDA",
                      "FOTO DE FUNDO DE OLHO"],
        "categoria": "Oftalmologia", "unidade": "",
        "referencias": []
    },
    {
        "nome_oficial": "Tomografia de Coerência Óptica (OCT)",
        "sinonimos": ["OCT", "TOMOGRAFIA COERÊNCIA ÓPTICA",
                      "OCT MACULAR", "OCT NERVO ÓPTICO"],
        "categoria": "Oftalmologia", "unidade": "",
        "referencias": []
    },
    {
        "nome_oficial": "Paquimetria",
        "sinonimos": ["PAQUIMETRIA", "PAQUIMETRIA ULTRASSÔNICA",
                      "ESPESSURA CORNEANA"],
        "categoria": "Oftalmologia", "unidade": "",
        "referencias": []
    },
    {
        "nome_oficial": "Tonometria",
        "sinonimos": ["TONOMETRIA", "PRESSÃO INTRAOCULAR", "PIO"],
        "categoria": "Oftalmologia", "unidade": "mmHg",
        "referencias": [{"sexo": "ambos", "idade_min": 0, "idade_max": 120,
            "critico_baixo": 5, "limite_baixo": 10, "otimo_min": 10,
            "otimo_max": 18, "limite_alto": 21, "critico_alto": 40}]
    },
    {
        "nome_oficial": "Histopatológico",
        "sinonimos": ["HISTOPATOLOGICO", "HISTOPATOLÓGICO",
                      "BIOPSIA", "BIÓPSIA", "ANATOMOPATOLÓGICO"],
        "categoria": "Anatomia Patológica", "unidade": "",
        "referencias": []
    },
    {
        "nome_oficial": "Endoscopia Digestiva Alta",
        "sinonimos": ["ENDOSCOPIA", "EDA", "ENDOSCOPIA DIGESTIVA ALTA",
                      "ESOFAGOGASTRODUODENOSCOPIA"],
        "categoria": "Endoscopia", "unidade": "",
        "referencias": []
    },
    {
        "nome_oficial": "Colonoscopia",
        "sinonimos": ["COLONOSCOPIA", "VIDEOCOLONOSCOPIA"],
        "categoria": "Endoscopia", "unidade": "",
        "referencias": []
    },
    {
        "nome_oficial": "Densitometria Óssea",
        "sinonimos": ["DENSITOMETRIA", "DENSITOMETRIA OSSEA",
                      "DENSITOMETRIA ÓSSEA", "DEXA"],
        "categoria": "Imagem", "unidade": "",
        "referencias": []
    },
]


# ══════════════════════════════════════════════════════════════
# POPULAR BANCO
# ══════════════════════════════════════════════════════════════

def popular_banco():
    """Insere os exames padrão no banco. Ignora os que já existem."""
    from .model_prontuario import DB_PATH
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()

    inseridos = 0
    ignorados = 0

    import time as _t
    for exame in EXAMES_PADRAO:
        _t.sleep(0.001)   # cede GIL para thread de UI renderizar
        cur.execute("SELECT id FROM exames_padrao WHERE nome_oficial = ?",
                    (exame["nome_oficial"],))
        if cur.fetchone():
            ignorados += 1
            continue

        cur.execute("""
            INSERT INTO exames_padrao (nome_oficial, sinonimos, categoria, unidade)
            VALUES (?, ?, ?, ?)
        """, (
            exame["nome_oficial"],
            json.dumps(exame["sinonimos"], ensure_ascii=False),
            exame["categoria"],
            exame["unidade"],
        ))
        exame_id = cur.lastrowid

        for ref in exame.get("referencias", []):
            cur.execute("""
                INSERT INTO referencias_padrao
                (exame_padrao_id, sexo, idade_min, idade_max,
                 critico_baixo, limite_baixo, otimo_min, otimo_max,
                 limite_alto, critico_alto, observacoes, fonte)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exame_id, ref.get("sexo", "ambos"), ref["idade_min"], ref["idade_max"],
                ref["critico_baixo"], ref["limite_baixo"],
                ref["otimo_min"], ref["otimo_max"],
                ref["limite_alto"], ref["critico_alto"],
                ref.get("obs", None), ref.get("fonte", None),
            ))
        inseridos += 1

    conn.commit()
    conn.close()
    print(f"✅ {inseridos} exames inseridos | {ignorados} já existiam.")
    return inseridos, ignorados


if __name__ == "__main__":
    popular_banco()
