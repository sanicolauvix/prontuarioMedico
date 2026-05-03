# -*- coding: utf-8 -*-
# KOIOS v1.0 | gerado: 2026-03-12 07:53 | model.py
"""
model.py - Banco de dados SQLite
Módulos:
  - Exames (numérico / laudo / imagem)
  - Médicos + Especialidades
  - Consultas + Receitas
  - Remédios
"""

import sqlite3
import os as _os

# ── Banco de dados no Google Drive ───────────────────────────────────────────
# Estrutura no Drive:
#   Google Drive/
#   └── Koios/
#       ├── koios.db          ← banco de dados
#       └── SISTEMA_SAUDE/    ← PDFs dos exames
#
# O app detecta automaticamente o caminho do Google Drive no Windows.
# Se não encontrar o Drive, usa pasta local database/ como fallback.
# ─────────────────────────────────────────────────────────────────────────────

# Banco de dados sempre local — sincronizado com Drive via API
# Fluxo: main.py baixa koios.db do Drive ao iniciar → app usa local
#         main.py faz upload do koios.db ao encerrar
# Ver: database/drive_sync.py
_HERE_MODEL = _os.path.dirname(_os.path.abspath(__file__))  # prontuario/dados/
_KOIOS_ROOT = _os.path.dirname(_os.path.dirname(_HERE_MODEL))  # Koios/
_DB_DIR     = _os.path.join(_KOIOS_ROOT, "database")
_os.makedirs(_DB_DIR, exist_ok=True)

# Banco CORE (compartilhado entre módulos): perfil, auth, sessões
CORE_DB = _os.path.join(_DB_DIR, "koios.db")              # Koios/database/koios.db

# Banco do MÓDULO Prontuário: fica junto ao módulo em prontuario/dados/
DB_PATH = _os.path.join(_HERE_MODEL, "prontuario.db")     # prontuario/dados/prontuario.db


# ── Backup auto-notify ───────────────────────────────────────────────────────
# Qualquer conn.commit() em DB_PATH chama _notify() automaticamente.
# notify_db_changed() e no-op se o watcher nao estiver rodando (startup).

def _notify() -> None:
    try:
        from backup.backup_watcher import notify_db_changed
        notify_db_changed()
    except Exception:
        pass


class _ProntuarioConn(sqlite3.Connection):
    def commit(self):
        super().commit()
        _notify()


_orig_sqlite3_connect = sqlite3.connect


def _prontuario_connect(*args, **kwargs):
    db = args[0] if args else kwargs.get("database", "")
    if db == DB_PATH and "factory" not in kwargs:
        kwargs["factory"] = _ProntuarioConn
    return _orig_sqlite3_connect(*args, **kwargs)


sqlite3.connect = _prontuario_connect
# ─────────────────────────────────────────────────────────────────────────────


def _migrar_medicos():
    """Adiciona colunas 'especialidade' e 'medico_solicit' se não existirem."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        cur  = conn.cursor()
        cur.execute("PRAGMA table_info(medicos)")
        colunas = [row[1] for row in cur.fetchall()]
        if "especialidade" not in colunas:
            cur.execute("ALTER TABLE medicos ADD COLUMN especialidade TEXT")
            print("[MODEL] coluna medicos.especialidade adicionada")
        if "medico_solicit" not in colunas:
            cur.execute("ALTER TABLE medicos ADD COLUMN medico_solicit TEXT")
            print("[MODEL] coluna medicos.medico_solicit adicionada")
        conn.commit()
        conn.close()
    except Exception as ex:
        print(f"[MODEL] _migrar_medicos: {ex}")


def _migrar_status_exames():
    """Adiciona coluna status na tabela exames se não existir."""
    try:
        with sqlite3.connect(DB_PATH) as _c:
            cols = [r[1] for r in _c.execute("PRAGMA table_info(exames)").fetchall()]
            if "status" not in cols:
                _c.execute("ALTER TABLE exames ADD COLUMN status TEXT DEFAULT 'ativo'")
                print("[MODEL] coluna 'status' adicionada em exames")
    except Exception as _ex:
        print(f"[MODEL] aviso migrar status: {_ex}")


def _migrar_campos_perfil():
    """Adiciona novos campos ao perfil_usuario em bancos existentes."""
    novos = [
        ('peso',               'REAL'),
        ('altura',             'REAL'),
        ('tipo_sanguineo',     'TEXT'),
        ('condicoes_cronicas', 'TEXT'),
        ('contato_emergencia', 'TEXT'),
        ('tel_emergencia',     'TEXT'),
        ("tema",               "TEXT DEFAULT 'dark'"),
        ("accent_color",       "TEXT DEFAULT '#58A6FF'"),
        ("tamanho_fonte",      "TEXT DEFAULT 'medio'"),
    ]
    conn = None
    try:
        conn = sqlite3.connect(CORE_DB, timeout=30)
        cur  = conn.cursor()
        cols = [r[1] for r in cur.execute('PRAGMA table_info(perfil_usuario)').fetchall()]
        for col, tipo in novos:
            if col not in cols:
                try:
                    cur.execute(f'ALTER TABLE perfil_usuario ADD COLUMN {col} {tipo}')
                    print(f'[PERFIL] coluna {col} adicionada')
                except Exception as ex:
                    print(f'[PERFIL] erro ao adicionar {col}: {ex}')
        conn.commit()
    except Exception as ex:
        print(f'[PERFIL] _migrar_campos_perfil: {ex}')
    finally:
        if conn:
            conn.close()


def _migrar_principio_ativo():
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(remedios)").fetchall()]
            if "principio_ativo" not in cols:
                conn.execute("ALTER TABLE remedios ADD COLUMN principio_ativo TEXT")
                print("[MODEL] coluna principio_ativo adicionada em remedios")
    except Exception as ex:
        print(f"[MODEL] _migrar_principio_ativo: {ex}")


def _migrar_marcadores():
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS marcadores_leituras (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    parametro    TEXT NOT NULL,
                    categoria    TEXT,
                    valor        REAL,
                    valor_txt    TEXT,
                    unidade      TEXT,
                    referencia   TEXT,
                    data_medicao TEXT NOT NULL,
                    hora_medicao TEXT,
                    fonte        TEXT DEFAULT 'manual',
                    dispositivo  TEXT,
                    observacoes  TEXT,
                    criado_em    TEXT DEFAULT (datetime('now'))
                )
            """)
    except Exception as ex:
        print(f"[MODEL] _migrar_marcadores: {ex}")


def _migrar_marcadores_contexto():
    """Adiciona coluna contexto em marcadores_leituras (captura de contexto Claudia)."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute(
                "PRAGMA table_info(marcadores_leituras)").fetchall()]
            if "contexto" not in cols:
                conn.execute(
                    "ALTER TABLE marcadores_leituras ADD COLUMN contexto TEXT")
    except Exception as ex:
        print(f"[MODEL] _migrar_marcadores_contexto: {ex}")


def _migrar_tipo_prescrito():
    """Adiciona tipo (remedio/suplemento) e prescrito (0/1) em remedios."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(remedios)").fetchall()]
            if "tipo" not in cols:
                conn.execute("ALTER TABLE remedios ADD COLUMN tipo TEXT DEFAULT 'remedio'")
                print("[MODEL] coluna tipo adicionada em remedios")
            if "prescrito" not in cols:
                conn.execute("ALTER TABLE remedios ADD COLUMN prescrito INTEGER DEFAULT 0")
                print("[MODEL] coluna prescrito adicionada em remedios")
    except Exception as ex:
        print(f"[MODEL] _migrar_tipo_prescrito: {ex}")


def _migrar_remedio_fotos():
    """Adiciona tipo (remedio/receita) e data_validade em remedio_fotos."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(remedio_fotos)").fetchall()]
            if "tipo" not in cols:
                conn.execute("ALTER TABLE remedio_fotos ADD COLUMN tipo TEXT DEFAULT 'remedio'")
                print("[MODEL] coluna tipo adicionada em remedio_fotos")
            if "data_validade" not in cols:
                conn.execute("ALTER TABLE remedio_fotos ADD COLUMN data_validade TEXT")
                print("[MODEL] coluna data_validade adicionada em remedio_fotos")
    except Exception as ex:
        print(f"[MODEL] _migrar_remedio_fotos: {ex}")


def _migrar_consulta_pauta():
    """Adiciona coluna pauta (JSON) em consultas para itens a tratar."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(consultas)").fetchall()]
            if "pauta" not in cols:
                conn.execute("ALTER TABLE consultas ADD COLUMN pauta TEXT")
                print("[MODEL] coluna pauta adicionada em consultas")
    except Exception as ex:
        print(f"[MODEL] _migrar_consulta_pauta: {ex}")


def _migrar_compromisso():
    """Adiciona tipo_compromisso e clinica_id em consultas (renomeada para compromissos)."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(consultas)").fetchall()]
            if "tipo_compromisso" not in cols:
                conn.execute(
                    "ALTER TABLE consultas ADD COLUMN tipo_compromisso TEXT DEFAULT 'consulta'"
                )
                print("[MODEL] coluna tipo_compromisso adicionada em consultas")
            if "clinica_id" not in cols:
                conn.execute("ALTER TABLE consultas ADD COLUMN clinica_id INTEGER")
                print("[MODEL] coluna clinica_id adicionada em consultas")
    except Exception as ex:
        print(f"[MODEL] _migrar_compromisso: {ex}")


def _criar_rotinas():
    """Cria tabelas de rotinas diarias (templates, momentos, itens)."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS rotinas_templates (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome      TEXT NOT NULL,
                    icone     TEXT DEFAULT 'today_rounded',
                    cor       TEXT DEFAULT '#58A6FF',
                    padrao    INTEGER DEFAULT 0,
                    ativo     INTEGER DEFAULT 1,
                    criado_em TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS momentos_rotina (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id INTEGER NOT NULL REFERENCES rotinas_templates(id) ON DELETE CASCADE,
                    nome        TEXT NOT NULL,
                    tipo        TEXT DEFAULT 'outro',
                    horario     TEXT,
                    ordem       INTEGER DEFAULT 0,
                    criado_em   TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS itens_momento (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    momento_id INTEGER NOT NULL REFERENCES momentos_rotina(id) ON DELETE CASCADE,
                    tipo       TEXT NOT NULL DEFAULT 'alimento',
                    descricao  TEXT NOT NULL,
                    detalhe    TEXT,
                    horario    TEXT,
                    remedio_id INTEGER REFERENCES remedios(id),
                    ordem      INTEGER DEFAULT 0,
                    criado_em  TEXT DEFAULT (datetime('now'))
                );
            """)
    except Exception as ex:
        print(f"[MODEL] _criar_rotinas: {ex}")


def _migrar_pai_id():
    """Adiciona pai_id em resultados_estruturados para sub-resultados (ex: eRFG filho de Creatinina)."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            cols = [r[1] for r in conn.execute('PRAGMA table_info(resultados_estruturados)').fetchall()]
            if 'pai_id' not in cols:
                conn.execute('ALTER TABLE resultados_estruturados ADD COLUMN pai_id INTEGER REFERENCES resultados_estruturados(id)')
                print('[MODEL] coluna pai_id adicionada em resultados_estruturados')
    except Exception as ex:
        print(f'[MODEL] _migrar_pai_id: {ex}')


def _migrar_referencias_padrao():
    """Adiciona colunas novas em referencias_padrao e exames_padrao para bancos existentes."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        cur  = conn.cursor()
        # referencias_padrao
        cols_ref = [r[1] for r in cur.execute('PRAGMA table_info(referencias_padrao)').fetchall()]
        if 'criado_em' not in cols_ref:
            cur.execute("ALTER TABLE referencias_padrao ADD COLUMN criado_em TEXT DEFAULT (datetime('now'))")
            print('[REF] criado_em adicionada em referencias_padrao')
        if 'observacoes' not in cols_ref:
            cur.execute("ALTER TABLE referencias_padrao ADD COLUMN observacoes TEXT")
            print('[REF] observacoes adicionada em referencias_padrao')
        # exames_padrao
        cols_ep = [r[1] for r in cur.execute('PRAGMA table_info(exames_padrao)').fetchall()]
        if 'observacoes' not in cols_ep:
            cur.execute("ALTER TABLE exames_padrao ADD COLUMN observacoes TEXT")
            print('[REF] observacoes adicionada em exames_padrao')
        conn.commit()
    except Exception as ex:
        print(f'[REF] _migrar_referencias_padrao: {ex}')
    finally:
        if conn:
            conn.close()


_ESPECIALIDADES_PADRAO = [
    ("Acupuntura",                              "Técnica terapêutica baseada na medicina tradicional chinesa"),
    ("Alergia e Imunologia",                    "Doenças alérgicas e distúrbios do sistema imunológico"),
    ("Anestesiologia",                          "Anestesia, sedação e controle da dor"),
    ("Angiologia",                              "Doenças dos vasos sanguíneos e linfáticos"),
    ("Cancerologia / Oncologia",                "Diagnóstico e tratamento do câncer"),
    ("Cardiologia",                             "Doenças do coração e sistema cardiovascular"),
    ("Cirurgia Cardiovascular",                 "Cirurgias do coração e grandes vasos"),
    ("Cirurgia da Mão",                         "Cirurgias da mão e punho"),
    ("Cirurgia do Aparelho Digestivo",          "Cirurgias do esôfago, estômago e intestinos"),
    ("Cirurgia Geral",                          "Cirurgias abdominais e de tecidos moles"),
    ("Cirurgia Pediátrica",                     "Cirurgias em crianças e adolescentes"),
    ("Cirurgia Plástica",                       "Cirurgias reconstrutoras e estéticas"),
    ("Cirurgia Torácica",                       "Cirurgias do tórax e pulmões"),
    ("Cirurgia Vascular",                       "Cirurgias dos vasos sanguíneos"),
    ("Clínica Médica",                          "Medicina interna e cuidados gerais do adulto"),
    ("Coloproctologia",                         "Doenças do cólon, reto e ânus"),
    ("Dermatologia",                            "Doenças da pele, cabelos e unhas"),
    ("Endocrinologia e Metabologia",            "Doenças hormonais e metabólicas"),
    ("Endoscopia",                              "Diagnóstico e tratamento endoscópico"),
    ("Gastroenterologia",                       "Doenças do sistema digestivo"),
    ("Geriatria",                               "Saúde do idoso"),
    ("Ginecologia e Obstetrícia",               "Saúde da mulher e gestação"),
    ("Hematologia e Hemoterapia",               "Doenças do sangue"),
    ("Infectologia",                            "Doenças infecciosas e parasitárias"),
    ("Mastologia",                              "Doenças da mama"),
    ("Medicina de Emergência",                  "Atendimento em urgência e emergência"),
    ("Medicina de Família e Comunidade",        "Atenção primária à saúde"),
    ("Medicina do Trabalho",                    "Saúde ocupacional"),
    ("Medicina Esportiva",                      "Saúde e desempenho no esporte"),
    ("Medicina Física e Reabilitação",          "Reabilitação motora e funcional"),
    ("Medicina Intensiva",                      "Tratamento de pacientes graves em UTI"),
    ("Medicina Nuclear",                        "Diagnóstico e tratamento com radionuclídeos"),
    ("Nefrologia",                              "Doenças dos rins"),
    ("Neurocirurgia",                           "Cirurgias do sistema nervoso"),
    ("Neurologia",                              "Doenças do sistema nervoso"),
    ("Nutrologia",                              "Nutrição clínica e distúrbios nutricionais"),
    ("Oftalmologia",                            "Doenças dos olhos"),
    ("Oncologia Clínica",                       "Tratamento clínico do câncer"),
    ("Ortopedia e Traumatologia",               "Doenças dos ossos, articulações e músculos"),
    ("Otorrinolaringologia",                    "Doenças do ouvido, nariz e garganta"),
    ("Patologia",                               "Diagnóstico por análise de tecidos"),
    ("Patologia Clínica / Medicina Laboratorial", "Exames laboratoriais e diagnóstico clínico"),
    ("Pediatria",                               "Saúde da criança e do adolescente"),
    ("Pneumologia",                             "Doenças do pulmão e vias aéreas"),
    ("Psiquiatria",                             "Doenças mentais e transtornos psiquiátricos"),
    ("Radiologia e Diagnóstico por Imagem",     "Diagnóstico por imagem (raio-X, TC, RM, ultrassom)"),
    ("Radioterapia",                            "Tratamento do câncer por radiação"),
    ("Reumatologia",                            "Doenças das articulações, músculos e ossos"),
    ("Urologia",                                "Doenças do sistema urinário e reprodutor masculino"),
]


def seed_especialidades():
    """Popula tabela especialidades com lista pré-configurada (INSERT OR IGNORE)."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            for nome, desc in _ESPECIALIDADES_PADRAO:
                conn.execute(
                    "INSERT OR IGNORE INTO especialidades (nome, descricao) VALUES (?,?)",
                    (nome, desc),
                )
        print(f"[MODEL] seed especialidades: {len(_ESPECIALIDADES_PADRAO)} registros verificados")
    except Exception as ex:
        print(f"[MODEL] seed_especialidades: {ex}")


def criar_tabelas():
    # ══════════════════════════════════════════════════════════
    # BANCO CORE (koios.db) — perfil, auth, sessões
    # ══════════════════════════════════════════════════════════
    conn_core = sqlite3.connect(CORE_DB, timeout=30)
    try:
        conn_core.executescript("""

        CREATE TABLE IF NOT EXISTS perfil_usuario (
            id          INTEGER PRIMARY KEY CHECK (id = 1),
            nome        TEXT,
            email       TEXT,
            data_nasc   TEXT,
            sexo        TEXT,
            foto_url    TEXT,
            criado_em   TEXT DEFAULT (datetime('now')),
            atualizado_em TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS usuarios (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            senha_hash  TEXT,
            perfil      TEXT DEFAULT 'medico',
            nome        TEXT,
            email       TEXT,
            ativo       INTEGER DEFAULT 1,
            ultimo_acesso TEXT,
            criado_em   TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sessoes (
            token       TEXT PRIMARY KEY,
            usuario_id  INTEGER REFERENCES usuarios(id),
            perfil      TEXT,
            criado_em   TEXT DEFAULT (datetime('now')),
            expira_em   TEXT,
            ip          TEXT
        );

        CREATE TABLE IF NOT EXISTS modulos_instalados (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT UNIQUE NOT NULL,
            versao      TEXT,
            db_arquivo  TEXT,
            ativo       INTEGER DEFAULT 1,
            instalado_em TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS config (
            chave TEXT PRIMARY KEY,
            valor TEXT
        );

        """)
        conn_core.commit()
    finally:
        conn_core.close()
    print("[OK] Tabelas CORE criadas (koios.db)")

    # ══════════════════════════════════════════════════════════
    # BANCO MÓDULO (prontuario.db) — exames, médicos, remédios
    # ══════════════════════════════════════════════════════════
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cursor = conn.cursor()

        cursor.executescript("""

        -- ────────────────────────────────────────────────────────
        -- PACIENTES
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS pacientes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT,
            cpf         TEXT UNIQUE,
            data_nasc   TEXT,
            sexo        TEXT,
            criado_em   TEXT DEFAULT (datetime('now'))
        );

        -- ────────────────────────────────────────────────────────
        -- ESPECIALIDADES
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS especialidades (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nome      TEXT UNIQUE NOT NULL,
            descricao TEXT,
            ativo     INTEGER DEFAULT 1,
            criado_em TEXT DEFAULT (datetime('now'))
        );

        -- ────────────────────────────────────────────────────────
        -- MÉDICOS
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS medicos (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            nome              TEXT NOT NULL,
            crm               TEXT,
            uf                TEXT,
            especialidade_id  INTEGER REFERENCES especialidades(id),
            especialidade     TEXT,   -- texto livre (além da FK)
            telefone          TEXT,
            email             TEXT,
            endereco          TEXT,
            site              TEXT,
            redes_sociais     TEXT,   -- JSON {instagram, facebook, ...}
            foto_drive_id     TEXT,   -- ID da foto no Drive
            observacoes       TEXT,
            medico_solicit    TEXT,   -- nome como aparece no PDF (para match)
            ativo             INTEGER DEFAULT 1,
            criado_em         TEXT DEFAULT (datetime('now'))
        );

        -- ────────────────────────────────────────────────────────
        -- EXAMES
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS exames (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id     INTEGER REFERENCES pacientes(id),
            medico_id       INTEGER REFERENCES medicos(id),
            tipo            TEXT DEFAULT 'numerico',
            tipo_exame      TEXT,
            data_exame      TEXT,
            laboratorio     TEXT,
            medico_solicit  TEXT,
            resultado_texto TEXT,
            arquivo_origem  TEXT,
            drive_file_id   TEXT,
            importado_em    TEXT DEFAULT (datetime('now'))
        );

        -- ────────────────────────────────────────────────────────
        -- RESULTADOS NUMÉRICOS
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS resultados_estruturados (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            exame_id            INTEGER REFERENCES exames(id),
            pai_id              INTEGER REFERENCES resultados_estruturados(id),
            parametro           TEXT,
            valor               TEXT,
            unidade             TEXT,
            referencia          TEXT,
            exame_padrao_id     INTEGER REFERENCES exames_padrao(id),
            nivel_interpretacao TEXT
        );

        -- ────────────────────────────────────────────────────────
        -- LAUDOS TEXTUAIS
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS laudos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            exame_id        INTEGER REFERENCES exames(id),
            texto_completo  TEXT,
            resumo          TEXT,
            conclusao       TEXT
        );

        -- ────────────────────────────────────────────────────────
        -- ANEXOS DE IMAGEM
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS exame_anexos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            exame_id        INTEGER REFERENCES exames(id),
            drive_file_id   TEXT,
            nome_arquivo    TEXT,
            ordem           INTEGER DEFAULT 0,
            criado_em       TEXT DEFAULT (datetime('now'))
        );

        -- ────────────────────────────────────────────────────────
        -- DICIONÁRIO PADRÃO
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS exames_padrao (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_oficial TEXT UNIQUE,
            sinonimos    TEXT,
            categoria    TEXT,
            tipo         TEXT DEFAULT 'numerico',
            unidade      TEXT,
            observacoes  TEXT,
            ativo        INTEGER DEFAULT 1,
            criado_em    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS referencias_padrao (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            exame_padrao_id INTEGER REFERENCES exames_padrao(id),
            sexo            TEXT,
            idade_min       INTEGER,
            idade_max       INTEGER,
            critico_baixo   REAL,
            limite_baixo    REAL,
            otimo_min       REAL,
            otimo_max       REAL,
            limite_alto     REAL,
            critico_alto    REAL,
            observacoes     TEXT,
            criado_em       TEXT DEFAULT (datetime('now'))
        );

        -- ────────────────────────────────────────────────────────
        -- CONSULTAS
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS consultas (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            medico_id    INTEGER REFERENCES medicos(id),
            paciente_id  INTEGER REFERENCES pacientes(id),
            data         TEXT NOT NULL,
            hora         TEXT,
            tipo         TEXT DEFAULT 'agendada',  -- agendada | realizada | cancelada
            local        TEXT,
            observacoes  TEXT,
            criado_em    TEXT DEFAULT (datetime('now'))
        );

        -- ────────────────────────────────────────────────────────
        -- RECEITAS
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS receitas (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            consulta_id   INTEGER REFERENCES consultas(id),
            medico_id     INTEGER REFERENCES medicos(id),
            drive_file_id TEXT,
            nome_arquivo  TEXT,
            data          TEXT,
            observacoes   TEXT,
            criado_em     TEXT DEFAULT (datetime('now'))
        );

        -- ────────────────────────────────────────────────────────
        -- REMÉDIOS
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS remedios (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome            TEXT NOT NULL,
            dosagem         TEXT,
            frequencia      TEXT,
            data_inicio     TEXT,
            data_fim        TEXT,
            medico_id       INTEGER REFERENCES medicos(id),
            receita_id      INTEGER REFERENCES receitas(id),
            estoque_atual   INTEGER DEFAULT 0,
            estoque_minimo  INTEGER DEFAULT 5,
            foto_path       TEXT,
            ativo           INTEGER DEFAULT 1,
            observacoes     TEXT,
            criado_em       TEXT DEFAULT (datetime('now'))
        );

        -- ────────────────────────────────────────────────────────
        -- REMÉDIOS: GALERIA DE FOTOS
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS remedio_fotos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            remedio_id  INTEGER NOT NULL,
            path        TEXT NOT NULL,
            legenda     TEXT,
            criado_em   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (remedio_id) REFERENCES remedios(id) ON DELETE CASCADE
        );

        -- ────────────────────────────────────────────────────────
        -- REMÉDIOS: HORÁRIOS, TOMADAS, FARMÁCIAS, COMPRAS
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS remedios_horarios (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            remedio_id  INTEGER NOT NULL,
            hora        TEXT NOT NULL,
            FOREIGN KEY (remedio_id) REFERENCES remedios(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS remedios_tomadas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            remedio_id      INTEGER NOT NULL,
            horario_id      INTEGER,
            data            TEXT NOT NULL,
            hora            TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'pendente',
            registrado_em   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (remedio_id) REFERENCES remedios(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS farmacias (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT NOT NULL,
            endereco    TEXT,
            telefone    TEXT,
            whatsapp    TEXT,
            site        TEXT,
            app         TEXT,
            delivery    INTEGER DEFAULT 0,
            preferida   INTEGER DEFAULT 0,
            observacoes TEXT,
            ativo       INTEGER DEFAULT 1,
            criado_em   TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS remedios_compras (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            remedio_id      INTEGER NOT NULL,
            farmacia_id     INTEGER,
            data_compra     TEXT NOT NULL,
            quantidade      INTEGER NOT NULL DEFAULT 1,
            preco_unitario  REAL,
            preco_total     REAL,
            foto_cupom      TEXT,
            observacoes     TEXT,
            criado_em       TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (remedio_id) REFERENCES remedios(id) ON DELETE CASCADE,
            FOREIGN KEY (farmacia_id) REFERENCES farmacias(id)
        );

        CREATE TABLE IF NOT EXISTS remedios_orcamentos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            farmacia_id     INTEGER NOT NULL,
            data_envio      TEXT NOT NULL,
            mensagem_envio  TEXT,
            resposta_bruta  TEXT,
            resposta_ia     TEXT,
            status          TEXT DEFAULT 'enviado',
            criado_em       TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (farmacia_id) REFERENCES farmacias(id)
        );

        CREATE TABLE IF NOT EXISTS orcamento_itens (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            orcamento_id    INTEGER NOT NULL,
            remedio_id      INTEGER,
            nome_pedido     TEXT NOT NULL,
            dosagem_pedido  TEXT,
            quantidade      INTEGER DEFAULT 1,
            preco_informado REAL,
            disponivel      INTEGER DEFAULT 1,
            observacao      TEXT,
            FOREIGN KEY (orcamento_id) REFERENCES remedios_orcamentos(id) ON DELETE CASCADE,
            FOREIGN KEY (remedio_id) REFERENCES remedios(id)
        );

        -- ────────────────────────────────────────────────────────
        -- CLÍNICAS / LOCAIS DE ATENDIMENTO
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS clinicas (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nome          TEXT NOT NULL,
            tipo          TEXT DEFAULT 'clinica',
            telefone      TEXT,
            email         TEXT,
            website       TEXT,
            endereco_json TEXT,
            observacoes   TEXT,
            ativo         INTEGER DEFAULT 1,
            criado_em     TEXT DEFAULT (datetime('now'))
        );

        -- ────────────────────────────────────────────────────────
        -- LINKS DE ACESSO MÉDICO
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS links_medico (
            token       TEXT PRIMARY KEY,
            medico_id   INTEGER REFERENCES medicos(id),
            nome_medico TEXT NOT NULL,
            criado_em   TEXT DEFAULT (datetime('now')),
            ultimo_acesso TEXT,
            acessos     INTEGER DEFAULT 0,
            ativo       INTEGER DEFAULT 1
        );

        -- ────────────────────────────────────────────────────────
        -- COMPARTILHAMENTOS (LGPD - auditoria)
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS compartilhamentos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            destinatario    TEXT NOT NULL,     -- nome do médico
            email_dest      TEXT,              -- email se informado
            finalidade      TEXT NOT NULL,     -- ex: "Consulta cardiologista"
            conteudo_desc   TEXT,              -- o que foi compartilhado
            drive_file_id   TEXT,              -- ID do PDF no Drive
            drive_link      TEXT,              -- link de acesso
            data_criacao    TEXT DEFAULT (datetime('now')),
            data_revogacao  TEXT,              -- NULL = ainda ativo
            ativo           INTEGER DEFAULT 1
        );

        -- ────────────────────────────────────────────────────────
        -- LOG DE IMPORTAÇÕES
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS pdfs_incompativeis (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_arquivo TEXT NOT NULL,
            drive_file_id TEXT,
            motivo       TEXT,
            tamanho_kb   INTEGER,
            registrado_em TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS importacoes_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            arquivo     TEXT,
            status      TEXT,
            mensagem    TEXT,
            data_import TEXT DEFAULT (datetime('now'))
        );

        -- ────────────────────────────────────────────────────────
        -- EXTRATORES DE LABORATÓRIO (auto-evolutivo via IA)
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS lab_extratores (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            laboratorio     TEXT NOT NULL,
            versao          INTEGER DEFAULT 1,
            tipo            TEXT DEFAULT 'ia',
            prompt_extracao TEXT,
            regex_nome      TEXT,
            regex_resultado TEXT,
            exemplo_entrada TEXT,
            exemplo_saida   TEXT,
            taxa_acerto     REAL DEFAULT 0,
            total_usos      INTEGER DEFAULT 0,
            custo_acumulado REAL DEFAULT 0,
            ativo           INTEGER DEFAULT 1,
            criado_em       TEXT DEFAULT (datetime('now')),
            atualizado_em   TEXT DEFAULT (datetime('now'))
        );

        -- ROTINA DIÁRIA (dieta, suplementos, refeições)
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS rotina_itens (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo        TEXT NOT NULL DEFAULT 'refeicao',
            -- 'refeicao' | 'medicamento' | 'suplemento' | 'atividade' | 'outro'
            nome        TEXT NOT NULL,
            horario     TEXT,          -- HH:MM
            dias_semana TEXT,          -- '1,2,3,4,5' (1=seg…7=dom), NULL=todos
            descricao   TEXT,
            quantidade  TEXT,          -- "1 comprimido", "200g", etc.
            ativo       INTEGER DEFAULT 1,
            criado_em   TEXT DEFAULT (datetime('now'))
        );

        -- DIÁRIO DE SAÚDE (relatos diários)
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS diario_saude (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            data        TEXT NOT NULL,           -- YYYY-MM-DD
            hora        TEXT,                    -- HH:MM
            humor       INTEGER,                 -- 1-5
            energia     INTEGER,                 -- 1-5
            sono_horas  REAL,
            peso        REAL,
            pressao     TEXT,                    -- "120/80"
            relato      TEXT NOT NULL,
            tags        TEXT,                    -- "gripe,dor_cabeca"
            remedio_tomado TEXT,                 -- nome do remédio se relevante
            criado_em   TEXT DEFAULT (datetime('now'))
        );

        -- ────────────────────────────────────────────────────────
        -- MARCADORES DE SAUDE (leituras manuais e bluetooth)
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS marcadores_leituras (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            parametro    TEXT NOT NULL,
            categoria    TEXT,
            valor        REAL,
            valor_txt    TEXT,
            unidade      TEXT,
            referencia   TEXT,
            data_medicao TEXT NOT NULL,
            hora_medicao TEXT,
            fonte        TEXT DEFAULT 'manual',
            dispositivo  TEXT,
            observacoes  TEXT,
            criado_em    TEXT DEFAULT (datetime('now'))
        );

    """)

        conn.commit()
    finally:
        conn.close()
    print("[OK] Tabelas MÓDULO criadas (prontuario.db)")
    _migrar_campos_perfil()
    _migrar_pai_id()
    _migrar_referencias_padrao()
    _migrar_medicos()
    _migrar_principio_ativo()
    _migrar_marcadores()
    _migrar_marcadores_contexto()
    _migrar_tipo_prescrito()
    _migrar_remedio_fotos()
    _migrar_consulta_pauta()
    _migrar_compromisso()
    _criar_rotinas()
    # Registrar módulo no core
    try:
        _conn = sqlite3.connect(CORE_DB, timeout=30)
        _conn.execute("""INSERT OR IGNORE INTO modulos_instalados (nome, versao, db_arquivo)
                         VALUES ('prontuario', '1.0', 'prontuario.db')""")
        _conn.commit(); _conn.close()
    except Exception:
        pass
    # Popular base de exames padrão (135 exames com categorias e referências)
    try:
        from .exames_padrao_dados import popular_banco
        popular_banco()
    except Exception as _ex:
        try:
            from exames_padrao_dados import popular_banco
            popular_banco()
        except Exception:
            print(f"[AVISO] popular_banco: {_ex}")
    # Popular especialidades médicas pré-configuradas
    seed_especialidades()


# ══════════════════════════════════════════════════════════════
# HELPERS — CONFIG (chave/valor no CORE_DB)
# ══════════════════════════════════════════════════════════════

def get_config(chave: str, padrao: str = "") -> str:
    try:
        with sqlite3.connect(CORE_DB, timeout=10) as _c:
            row = _c.execute(
                "SELECT valor FROM config WHERE chave = ?", (chave,)
            ).fetchone()
            return row[0] if row else padrao
    except Exception:
        return padrao


def set_config(chave: str, valor: str) -> None:
    try:
        with sqlite3.connect(CORE_DB, timeout=10) as _c:
            _c.execute(
                "INSERT OR REPLACE INTO config (chave, valor) VALUES (?, ?)",
                (chave, valor),
            )
    except Exception as _ex:
        print(f"[MODEL] set_config: {_ex}")


# ══════════════════════════════════════════════════════════════
# HELPERS — EXAMES
# ══════════════════════════════════════════════════════════════


def buscar_referencia(exame_padrao_id: int, sexo: str = None, idade: int = None) -> dict | None:
    """
    Retorna a referência mais recente para um exame_padrao_id,
    filtrando por sexo e faixa etária quando informados.

    Ordem de prioridade:
      1. Registro com sexo + faixa etária correspondente (mais específico)
      2. Registro com apenas sexo correspondente
      3. Registro sem filtro (sexo NULL e sem faixa etária)
    Dentro de cada nível, retorna sempre o mais recente (criado_em DESC).

    Retorna dict com: id, limite_baixo, limite_alto, critico_baixo, critico_alto,
                      otimo_min, otimo_max, sexo, idade_min, idade_max, criado_em
    """
    with sqlite3.connect(DB_PATH, timeout=10) as _c:
        base = """
            SELECT id, limite_baixo, limite_alto,
                   critico_baixo, critico_alto,
                   otimo_min, otimo_max,
                   sexo, idade_min, idade_max, criado_em
            FROM referencias_padrao
            WHERE exame_padrao_id = ?
        """
        # Nível 1: sexo + faixa etária
        if sexo and idade is not None:
            row = _c.execute(base + """
                AND (sexo = ? OR sexo IS NULL)
                AND (idade_min IS NULL OR idade_min <= ?)
                AND (idade_max IS NULL OR idade_max >= ?)
                AND sexo IS NOT NULL
                AND idade_min IS NOT NULL
                ORDER BY criado_em DESC LIMIT 1
            """, (exame_padrao_id, sexo, idade, idade)).fetchone()
            if row:
                return _row_to_ref(row)

        # Nível 2: só sexo
        if sexo:
            row = _c.execute(base + """
                AND sexo = ?
                ORDER BY criado_em DESC LIMIT 1
            """, (exame_padrao_id, sexo)).fetchone()
            if row:
                return _row_to_ref(row)

        # Nível 3: referência genérica (sem filtro)
        row = _c.execute(base + """
            ORDER BY criado_em DESC LIMIT 1
        """, (exame_padrao_id,)).fetchone()
        return _row_to_ref(row) if row else None


def _row_to_ref(row) -> dict:
    cols = ["id", "limite_baixo", "limite_alto", "critico_baixo", "critico_alto",
            "otimo_min", "otimo_max", "sexo", "idade_min", "idade_max", "criado_em"]
    return dict(zip(cols, row))


def salvar_referencia(exame_padrao_id: int, dados: dict) -> int:
    """
    Insere uma nova versão de referência para um exame padrão.
    Não sobrescreve registros anteriores — mantém histórico completo.

    dados: {
        sexo         : 'M' | 'F' | None,
        idade_min    : int | None,
        idade_max    : int | None,
        limite_baixo : float,
        limite_alto  : float,
        critico_baixo: float | None,
        critico_alto : float | None,
        otimo_min    : float | None,
        otimo_max    : float | None,
    }
    Retorna id do novo registro.
    """
    with sqlite3.connect(DB_PATH, timeout=10) as _c:
        cur = _c.execute("""
            INSERT INTO referencias_padrao
                (exame_padrao_id, sexo, idade_min, idade_max,
                 critico_baixo, limite_baixo, otimo_min, otimo_max,
                 limite_alto, critico_alto, criado_em)
            VALUES (?,?,?,?,?,?,?,?,?,?, datetime('now'))
        """, (
            exame_padrao_id,
            dados.get("sexo"),
            dados.get("idade_min"),
            dados.get("idade_max"),
            dados.get("critico_baixo"),
            dados.get("limite_baixo"),
            dados.get("otimo_min"),
            dados.get("otimo_max"),
            dados.get("limite_alto"),
            dados.get("critico_alto"),
        ))
        _c.commit()
        print(f"[REF] Nova referência salva — exame_padrao_id={exame_padrao_id} id={cur.lastrowid}")
        return cur.lastrowid



def registrar_pdf_incompativel(nome_arquivo: str, drive_file_id: str, motivo: str, tamanho_kb: int = 0):
    """Registra PDF com layout incompativel para revisao manual."""
    import sqlite3
    with sqlite3.connect(DB_PATH) as conn:
        # Evita duplicata pelo nome
        existe = conn.execute(
            "SELECT id FROM pdfs_incompativeis WHERE nome_arquivo = ?",
            (nome_arquivo,)
        ).fetchone()
        if not existe:
            conn.execute(
                "INSERT INTO pdfs_incompativeis (nome_arquivo, drive_file_id, motivo, tamanho_kb) VALUES (?,?,?,?)",
                (nome_arquivo, drive_file_id, motivo, tamanho_kb)
            )
            conn.commit()


def listar_pdfs_incompativeis() -> list:
    import sqlite3
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT id, nome_arquivo, drive_file_id, motivo, tamanho_kb, registrado_em "
            "FROM pdfs_incompativeis ORDER BY registrado_em DESC"
        ).fetchall()
    return [
        {"id": r[0], "nome": r[1], "drive_id": r[2],
         "motivo": r[3], "tamanho_kb": r[4], "data": r[5]}
        for r in rows
    ]


def registrar_log(arquivo: str, status: str, mensagem: str = ""):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute(
            "INSERT INTO importacoes_log (arquivo, status, mensagem) VALUES (?,?,?)",
            (arquivo, status, mensagem),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _normalizar_para_busca(s: str) -> str:
    """Normaliza nome para busca no índice de exames_padrao."""
    import unicodedata
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    import re as _re
    s = _re.sub(r"[.\-,;:()/?!]", " ", s)
    s = _re.sub(r"\s+", " ", s).strip().upper()
    return s


def _carregar_indice_padrao(cur) -> dict:
    """Carrega índice normalizado de exames_padrao: nome_norm → id."""
    idx = {}
    try:
        rows = cur.execute("SELECT id, nome_oficial, sinonimos FROM exames_padrao WHERE ativo=1").fetchall()
    except Exception:
        return idx
    for row_id, nome_oficial, sinonimos in rows:
        idx[_normalizar_para_busca(nome_oficial)] = row_id
        if sinonimos:
            for s in sinonimos.split("|"):
                s = s.strip()
                if s:
                    idx[_normalizar_para_busca(s)] = row_id
    return idx


def _buscar_padrao_id(indice: dict, parametro: str):
    """Busca exame_padrao_id pelo nome normalizado."""
    if not parametro or not indice:
        return None
    norm = _normalizar_para_busca(parametro)
    return indice.get(norm)


def salvar_exame(dados: dict, status: str = "ativo") -> int:
    """
    Grava exame diretamente como ativo (padrão).
    Aceita status='rascunho' para compatibilidade legada — mas o fluxo
    novo não usa mais rascunho: grava tudo em memória até confirmar.
    Vincula automaticamente exame_padrao_id por nome normalizado.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur  = conn.cursor()

        # Carregar índice de exames_padrao para vínculo automático
        _padrao_idx = _carregar_indice_padrao(cur)

        # Upsert paciente
        cpf  = dados.get("paciente_cpf")
        nome = dados.get("paciente_nome")
        if cpf:
            cur.execute("INSERT OR IGNORE INTO pacientes (nome, cpf) VALUES (?,?)", (nome, cpf))
            cur.execute("SELECT id FROM pacientes WHERE cpf = ?", (cpf,))
        else:
            cur.execute("INSERT OR IGNORE INTO pacientes (nome, cpf) VALUES (?,?)", (nome, None))
            cur.execute("SELECT id FROM pacientes WHERE nome = ?", (nome,))
        row = cur.fetchone()
        paciente_id = row[0] if row else None

        # Auto-cadastro do médico solicitante
        medico_id = None
        nome_medico = dados.get("medico_solicit")
        if nome_medico:
            medico_id = upsert_medico_simples(cur, nome_medico)

        # Inserir exame
        cur.execute("""
            INSERT INTO exames
            (paciente_id, medico_id, tipo, tipo_exame, data_exame, laboratorio,
             medico_solicit, resultado_texto, arquivo_origem, drive_file_id, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            paciente_id,
            medico_id,
            dados.get("tipo", "numerico"),
            dados.get("tipo_exame"),
            dados.get("data_exame"),
            dados.get("laboratorio"),
            dados.get("medico_solicit"),
            dados.get("resultado_texto"),
            dados.get("arquivo_origem"),
            dados.get("drive_file_id"),
            status,
        ))
        exame_id = cur.lastrowid

        # Resultados numéricos (com sub-resultados opcionais e vínculo automático)
        for r in dados.get("resultados", []):
            padrao_id = _buscar_padrao_id(_padrao_idx, r.get("parametro"))
            cur.execute("""
                INSERT INTO resultados_estruturados
                (exame_id, pai_id, parametro, valor, unidade, referencia, exame_padrao_id)
                VALUES (?,?,?,?,?,?,?)
            """, (exame_id, None, r.get("parametro"), r.get("valor"),
                  r.get("unidade"), r.get("referencia"), padrao_id))
            pai_id = cur.lastrowid
            for sub in r.get("sub_resultados", []):
                sub_padrao_id = _buscar_padrao_id(_padrao_idx, sub.get("parametro"))
                cur.execute("""
                    INSERT INTO resultados_estruturados
                    (exame_id, pai_id, parametro, valor, unidade, referencia, exame_padrao_id)
                    VALUES (?,?,?,?,?,?,?)
                """, (exame_id, pai_id, sub.get("parametro"), sub.get("valor"),
                      sub.get("unidade"), sub.get("referencia"), sub_padrao_id))

        # Laudo textual
        laudo = dados.get("laudo")
        if laudo:
            cur.execute("""
                INSERT INTO laudos (exame_id, texto_completo, resumo, conclusao)
                VALUES (?,?,?,?)
            """, (exame_id, laudo.get("texto_completo"),
                  laudo.get("resumo"), laudo.get("conclusao")))

        # Anexos imagem
        for i, anexo in enumerate(dados.get("anexos", [])):
            cur.execute("""
                INSERT INTO exame_anexos (exame_id, drive_file_id, nome_arquivo, ordem)
                VALUES (?,?,?,?)
            """, (exame_id, anexo.get("drive_file_id"),
                  anexo.get("nome_arquivo"), anexo.get("ordem", i)))

        conn.commit()
        return exame_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def salvar_rascunho(dados: dict) -> int:
    """Grava exame com status='rascunho' — sem drive_file_id ainda."""
    dados_tmp = dict(dados)
    dados_tmp["drive_file_id"] = None
    dados_tmp["status"] = "rascunho"
    return salvar_exame(dados_tmp)

def verificar_duplicata(nome_arquivo: str) -> dict:
    """
    Verifica se já existe um exame com o mesmo nome de arquivo.
    Retorna dict rico com contexto para a UI decidir o que fazer:
      {
        "duplicado": bool,
        "status": "ativo"|"rascunho"|None,
        "exame_id": int|None,
        "importado_em": str|None,
        "qtd_parametros": int,
        "tipo_exame": str|None,
        "motivo": str,
      }
    """
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        row = conn.execute(
            "SELECT id, importado_em, status, tipo_exame FROM exames "
            "WHERE arquivo_origem=? ORDER BY importado_em DESC LIMIT 1",
            (nome_arquivo,)
        ).fetchone()
        if not row:
            return {"duplicado": False}
        exame_id, importado_em, status, tipo_exame = row
        qtd = conn.execute(
            "SELECT COUNT(*) FROM resultados_estruturados WHERE exame_id=?",
            (exame_id,)
        ).fetchone()[0]
        return {
            "duplicado": True,
            "status": status,
            "exame_id": exame_id,
            "importado_em": importado_em,
            "qtd_parametros": qtd,
            "tipo_exame": tipo_exame or "",
            "motivo": f"importado em {importado_em} · {qtd} parâmetro(s)",
        }
    finally:
        conn.close()


def substituir_exame(exame_id_antigo: int, dados: dict) -> int:
    """
    Remove exame antigo (e seus resultados) e grava o novo como ativo,
    tudo em uma única transação. Retorna o id do novo exame.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur  = conn.cursor()
    try:
        # Remove antigo
        cur.execute("DELETE FROM resultados_estruturados WHERE exame_id=?", (exame_id_antigo,))
        cur.execute("DELETE FROM exames WHERE id=?", (exame_id_antigo,))

        # Insere novo (reutiliza lógica de salvar_exame inline)
        cpf  = dados.get("paciente_cpf")
        nome = dados.get("paciente_nome")
        if cpf:
            cur.execute("INSERT OR IGNORE INTO pacientes (nome, cpf) VALUES (?,?)", (nome, cpf))
            cur.execute("SELECT id FROM pacientes WHERE cpf=?", (cpf,))
        else:
            cur.execute("INSERT OR IGNORE INTO pacientes (nome, cpf) VALUES (?,?)", (nome, None))
            cur.execute("SELECT id FROM pacientes WHERE nome=?", (nome,))
        row = cur.fetchone()
        paciente_id = row[0] if row else None

        medico_id = None
        nome_med = dados.get("medico_solicit")
        if nome_med:
            medico_id = upsert_medico_simples(cur, nome_med)

        cur.execute("""
            INSERT INTO exames
            (paciente_id, medico_id, tipo, tipo_exame, data_exame, laboratorio,
             medico_solicit, resultado_texto, arquivo_origem, drive_file_id, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,'ativo')
        """, (
            paciente_id, medico_id,
            dados.get("tipo", "numerico"), dados.get("tipo_exame"),
            dados.get("data_exame"), dados.get("laboratorio"),
            dados.get("medico_solicit"), dados.get("resultado_texto"),
            dados.get("arquivo_origem"), dados.get("drive_file_id"),
        ))
        novo_id = cur.lastrowid

        for r in dados.get("resultados", []):
            cur.execute("""
                INSERT INTO resultados_estruturados
                (exame_id, pai_id, parametro, valor, unidade, referencia)
                VALUES (?,?,?,?,?,?)
            """, (novo_id, None, r.get("parametro"), r.get("valor"),
                  r.get("unidade"), r.get("referencia")))
            pai_id = cur.lastrowid
            for sub in r.get("sub_resultados", []):
                cur.execute("""
                    INSERT INTO resultados_estruturados
                    (exame_id, pai_id, parametro, valor, unidade, referencia)
                    VALUES (?,?,?,?,?,?)
                """, (novo_id, pai_id, sub.get("parametro"), sub.get("valor"),
                      sub.get("unidade"), sub.get("referencia")))

        conn.commit()
        return novo_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def registrar_ignorado(nome_arquivo: str, motivo: str = "cancelado pelo usuário"):
    """Registra no log de importações que o arquivo foi ignorado/cancelado."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute(
            "INSERT INTO importacoes_log (arquivo, status, mensagem) VALUES (?,?,?)",
            (nome_arquivo, "ignorado", motivo)
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def buscar_vinculos_parametros(parametros: list) -> dict:
    """
    Para cada parâmetro da lista, verifica se existe em exames_padrao (por nome_oficial ou sinonimos).
    Retorna {"vinculados": [{"parametro": str, "exame_padrao_id": int}], "nao_vinculados": [str]}
    """
    if not parametros:
        return {"vinculados": [], "nao_vinculados": []}

    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        rows = conn.execute(
            "SELECT id, nome_oficial, sinonimos FROM exames_padrao WHERE ativo=1"
        ).fetchall()
    finally:
        conn.close()

    def _norm(s):
        import re as _re
        s = s.strip().lower()
        s = _re.sub(r"\s*\(.*?\)", "", s)
        s = s.rstrip(".")
        s = _re.sub(r"\s+", " ", s).strip()
        return s

    indice = {}
    for row_id, nome_oficial, sinonimos in rows:
        indice[_norm(nome_oficial)] = row_id
        indice[_norm(nome_oficial).replace(".", "")] = row_id
        if sinonimos:
            for s in sinonimos.split("|"):
                s = s.strip()
                if s:
                    indice[_norm(s)] = row_id

    vinculados     = []
    nao_vinculados = []
    for p in parametros:
        chave = _norm(p)
        pid = indice.get(chave) or indice.get(chave.replace(".", ""))
        if pid:
            vinculados.append({"parametro": p, "exame_padrao_id": pid})
        else:
            nao_vinculados.append(p)

    return {"vinculados": vinculados, "nao_vinculados": nao_vinculados}


def validar_paciente_pdf(paciente_nome_pdf: str) -> dict:
    """
    Compara o nome do paciente extraído do PDF com o perfil do usuário logado.
    Retorna {"valido": True/False, "motivo": str}
    Aceita se as primeiras 2 palavras do nome baterem (case-insensitive).
    """
    import unicodedata

    def _normalizar(s: str) -> str:
        s = unicodedata.normalize("NFD", s or "")
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        return s.upper().strip()

    perfil = carregar_perfil()
    if not perfil or not perfil.get("nome"):
        # Sem perfil cadastrado — deixa passar
        return {"valido": True, "motivo": "perfil sem nome cadastrado"}

    nome_usuario = _normalizar(perfil["nome"])
    nome_pdf     = _normalizar(paciente_nome_pdf or "")

    if not nome_pdf:
        return {"valido": False, "motivo": "PDF não contém nome do paciente"}

    # Compara as 2 primeiras palavras
    palavras_usuario = nome_usuario.split()[:2]
    palavras_pdf     = nome_pdf.split()[:2]

    if palavras_usuario == palavras_pdf:
        return {"valido": True, "motivo": ""}

    # Tenta verificar se pelo menos o primeiro nome e sobrenome principal batem
    set_usuario = set(nome_usuario.split())
    set_pdf     = set(nome_pdf.split())
    comuns = set_usuario & set_pdf
    if len(comuns) >= 2:
        return {"valido": True, "motivo": ""}

    return {
        "valido": False,
        "motivo": f"Paciente do PDF ({paciente_nome_pdf}) não corresponde ao usuário ({perfil.get('nome')})"
    }



def listar_exames_padrao(so_ativos: bool = False) -> list:
    """Retorna exames_padrao com id, nome, categoria, unidade, ref_min, ref_max."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        # detecta colunas disponíveis (ref_min/ref_max podem não existir)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(exames_padrao)").fetchall()}
        extras = ", ".join(c for c in ("ref_min", "ref_max") if c in cols)
        sel = f"id, nome_oficial, categoria, unidade{', ' + extras if extras else ''}"
        where = "WHERE ativo=1" if so_ativos else ""
        rows = conn.execute(
            f"SELECT {sel} FROM exames_padrao {where} ORDER BY categoria, nome_oficial"
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        import logging as _lg
        _lg.getLogger(__name__).error("listar_exames_padrao: %s", str(e), exc_info=True)
        return []
    finally:
        conn.close()


def salvar_exame_padrao(dados: dict, exame_id: int | None = None) -> int | None:
    """
    Cria ou atualiza um exame_padrao.
    Retorna o id (novo ou existente) em caso de sucesso, None em caso de erro.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(exames_padrao)").fetchall()}
        campos = ["nome_oficial", "categoria", "unidade"]
        vals   = [dados["nome"], dados.get("categoria", "Geral"), dados.get("unidade", "")]
        if "ref_min" in cols:
            campos.append("ref_min"); vals.append(dados.get("ref_min"))
        if "ref_max" in cols:
            campos.append("ref_max"); vals.append(dados.get("ref_max"))
        if exame_id is None:
            ph = ", ".join(["?"] * len(campos))
            cur = conn.execute(
                f"INSERT OR IGNORE INTO exames_padrao ({', '.join(campos)}) VALUES ({ph})",
                vals,
            )
            conn.commit()
            if cur.lastrowid:
                return cur.lastrowid
            # já existia — retorna o id existente
            row = conn.execute(
                "SELECT id FROM exames_padrao WHERE nome_oficial = ?", (dados["nome"],)
            ).fetchone()
            return row[0] if row else None
        else:
            sets = ", ".join(f"{c}=?" for c in campos)
            conn.execute(f"UPDATE exames_padrao SET {sets} WHERE id=?", vals + [exame_id])
            conn.commit()
            return exame_id
    except Exception as e:
        import logging as _lg
        _lg.getLogger(__name__).error("salvar_exame_padrao: %s", str(e), exc_info=True)
        conn.rollback()
        return None
    finally:
        conn.close()


def excluir_exame_padrao(exame_id: int) -> bool:
    """Remove o exame_padrao e seus sinônimos. Retorna True em caso de sucesso."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        tbls = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if "parametros_sinonimos" in tbls:
            conn.execute(
                "DELETE FROM parametros_sinonimos WHERE exame_padrao_id=?", (exame_id,))
        conn.execute("DELETE FROM exames_padrao WHERE id=?", (exame_id,))
        conn.commit()
        return True
    except Exception as e:
        import logging as _lg
        _lg.getLogger(__name__).error("excluir_exame_padrao: %s", str(e), exc_info=True)
        conn.rollback()
        return False
    finally:
        conn.close()


def listar_laboratorios() -> list:
    """Lista laboratórios detectados nos exames importados com estatísticas."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        rows = conn.execute("""
            SELECT laboratorio,
                   COUNT(*)            AS total_exames,
                   MIN(data_exame)     AS primeiro,
                   MAX(data_exame)     AS ultimo,
                   COUNT(DISTINCT tipo) AS tipos
            FROM exames
            WHERE laboratorio IS NOT NULL AND laboratorio != ''
            GROUP BY UPPER(laboratorio)
            ORDER BY total_exames DESC
        """).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        import logging as _lg
        _lg.getLogger(__name__).error("listar_laboratorios: %s", str(e), exc_info=True)
        return []
    finally:
        conn.close()


def vincular_parametro(nome_parametro: str, exame_padrao_id: int):
    """
    Vincula um nome de parâmetro a um exame_padrao adicionando como sinônimo.
    Assim na próxima extração ele já será reconhecido.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        row = conn.execute(
            "SELECT sinonimos FROM exames_padrao WHERE id=?", (exame_padrao_id,)
        ).fetchone()
        if row is None:
            return
        sinonimos_atual = row[0] or ""
        lista = [s.strip() for s in sinonimos_atual.split("|") if s.strip()]
        if nome_parametro.strip() not in lista:
            lista.append(nome_parametro.strip())
        conn.execute(
            "UPDATE exames_padrao SET sinonimos=? WHERE id=?",
            ("|".join(lista), exame_padrao_id)
        )
        conn.commit()
    finally:
        conn.close()


def apagar_rascunho(exame_id: int):
    """Remove rascunho e seus resultados do banco."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("DELETE FROM resultados_estruturados WHERE exame_id=?", (exame_id,))
        conn.execute("DELETE FROM laudos WHERE exame_id=?", (exame_id,))
        conn.execute("DELETE FROM exame_anexos WHERE exame_id=?", (exame_id,))
        conn.execute("DELETE FROM exames WHERE id=? AND status='rascunho'", (exame_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def confirmar_exame(exame_id: int, dados: dict):
    """Atualiza rascunho para status='ativo' com drive_file_id."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("""
            UPDATE exames
            SET drive_file_id=?, status='ativo'
            WHERE id=?
        """, (dados.get("drive_file_id"), exame_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def salvar_sync_pendente(exame_id: int):
    """Marca exame para sincronização com planilha Drive."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("""
            INSERT OR IGNORE INTO sync_pendentes (exame_id, criado_em)
            VALUES (?, datetime('now'))
        """, (exame_id,))
        conn.commit()
    except Exception:
        pass  # tabela pode não existir ainda
    finally:
        conn.close()


def _limpar_nome_medico(nome: str) -> str:
    """Remove lixo de PDF do nome do médico. Retorna nome + CRM se tiver."""
    import re
    nome = nome.strip()

    if re.search(r"sem\s+solicit", nome, re.IGNORECASE):
        return "Sem solicitação médica"

    # Extrai CRM/CIRM e UF antes de cortar
    crm_match = re.search(r"(?:CIRM|CRM)\s*:?\s*(\d+)", nome, re.IGNORECASE)
    uf_match  = re.search(r"UF\s*:?\s*([A-Z]{2})", nome, re.IGNORECASE)
    crm_str   = crm_match.group(1) if crm_match else None
    uf_str    = uf_match.group(1)  if uf_match  else None

    # Corta onde começa CIRM: ou CRM: (colado ou não)
    m = re.search(r"(?:CIRM|CRM)\s*[:\d]", nome, re.IGNORECASE)
    if m:
        nome = nome[:m.start()].strip()

    # Remove outros lixos comuns do PDF
    padroes = [
        r"\s+Data\s+Nascimento.*",
        r"\s+Dt\.?\s*Atend.*",
        r"\s+\d{2}/\d{2}/\d{4}.*",
        r"\s+-\s+\d{2}:\d{2}.*",
        r"\s+\d{2}:\d{2}:\d{2}.*",
        r"\s+UF\s*:.*",
    ]
    for p in padroes:
        nome = re.sub(p, "", nome, flags=re.IGNORECASE).strip()

    nome = re.sub(r"[\s:,\-\.]+$", "", nome).strip()
    nome = re.sub(r"\s+", " ", nome).strip()

    if crm_str:
        uf_part = f"/{uf_str}" if uf_str else ""
        nome = f"{nome} (CRM {crm_str}{uf_part})"

    return nome

def upsert_medico_simples(cur, nome: str) -> int:
    """Busca médico pelo nome (limpo) ou cria com dados mínimos. Retorna id."""
    nome_limpo = _limpar_nome_medico(nome)
    if not nome_limpo:
        nome_limpo = nome.strip()
    # Busca pelo nome limpo OU pelo nome original (compatibilidade)
    cur.execute("""
        SELECT id FROM medicos
        WHERE UPPER(TRIM(nome)) = UPPER(?)
           OR UPPER(TRIM(nome)) = UPPER(?)
    """, (nome_limpo, nome.strip()))
    row = cur.fetchone()
    if row:
        # Atualiza nome se estava sujo
        cur.execute("UPDATE medicos SET nome=? WHERE id=? AND nome != ?",
                    (nome_limpo, row[0], nome_limpo))
        return row[0]
    cur.execute("INSERT INTO medicos (nome) VALUES (?)", (nome_limpo,))
    return cur.lastrowid


# ══════════════════════════════════════════════════════════════
# HELPERS — MÉDICOS
# ══════════════════════════════════════════════════════════════

def listar_medicos(so_ativos=True) -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur  = conn.cursor()
        where = "WHERE m.ativo = 1" if so_ativos else ""
        cur.execute(f"""
            SELECT m.id, m.nome, m.crm, m.uf, m.telefone, m.email,
                   m.endereco, m.site, m.redes_sociais, m.foto_drive_id,
                   m.observacoes, m.ativo,
                   e.nome as especialidade
            FROM medicos m
            LEFT JOIN especialidades e ON e.id = m.especialidade_id
            {where}
            ORDER BY m.nome
        """)
        cols = ["id","nome","crm","uf","telefone","email","endereco",
                "site","redes_sociais","foto_drive_id","observacoes","ativo","especialidade"]
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def salvar_medico(dados: dict) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur  = conn.cursor()
        if dados.get("id"):
            cur.execute("""
                UPDATE medicos SET nome=?, crm=?, uf=?, especialidade_id=?,
                telefone=?, email=?, endereco=?, site=?, redes_sociais=?,
                foto_drive_id=?, observacoes=?, ativo=?
                WHERE id=?
            """, (dados["nome"], dados.get("crm"), dados.get("uf"),
                  dados.get("especialidade_id"), dados.get("telefone"),
                  dados.get("email"), dados.get("endereco"), dados.get("site"),
                  dados.get("redes_sociais"), dados.get("foto_drive_id"),
                  dados.get("observacoes"), dados.get("ativo", 1), dados["id"]))
            mid = dados["id"]
        else:
            cur.execute("""
                INSERT INTO medicos (nome, crm, uf, especialidade_id, telefone,
                email, endereco, site, redes_sociais, foto_drive_id, observacoes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (dados["nome"], dados.get("crm"), dados.get("uf"),
                  dados.get("especialidade_id"), dados.get("telefone"),
                  dados.get("email"), dados.get("endereco"), dados.get("site"),
                  dados.get("redes_sociais"), dados.get("foto_drive_id"),
                  dados.get("observacoes")))
            mid = cur.lastrowid
        conn.commit()
        return mid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def exames_do_medico(medico_id: int) -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur  = conn.cursor()
        cur.execute("""
            SELECT id, tipo, tipo_exame, data_exame, laboratorio, arquivo_origem, drive_file_id
            FROM exames WHERE medico_id = ?
            ORDER BY data_exame DESC
        """, (medico_id,))
        cols = ["id","tipo","tipo_exame","data_exame","laboratorio","arquivo_origem","drive_file_id"]
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# HELPERS — ESPECIALIDADES
# ══════════════════════════════════════════════════════════════

def listar_especialidades(so_ativas=True) -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur  = conn.cursor()
        where = "WHERE ativo = 1" if so_ativas else ""
        cur.execute(f"SELECT id, nome, descricao, ativo FROM especialidades {where} ORDER BY nome")
        rows = cur.fetchall()
        return [{"id": r[0], "nome": r[1], "descricao": r[2], "ativo": r[3]} for r in rows]
    finally:
        conn.close()


def salvar_especialidade(dados: dict) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur  = conn.cursor()
        if dados.get("id"):
            cur.execute("UPDATE especialidades SET nome=?, descricao=?, ativo=? WHERE id=?",
                        (dados["nome"], dados.get("descricao"), dados.get("ativo", 1), dados["id"]))
            eid = dados["id"]
        else:
            cur.execute("INSERT OR IGNORE INTO especialidades (nome, descricao) VALUES (?,?)",
                        (dados["nome"], dados.get("descricao")))
            eid = cur.lastrowid
        conn.commit()
        return eid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def excluir_especialidade(esp_id: int) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.execute("DELETE FROM especialidades WHERE id = ?", (esp_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════
# HELPERS — CONSULTAS
# ══════════════════════════════════════════════════════════════

def listar_consultas(tipo: str = None, tipo_compromisso: str = None) -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur    = conn.cursor()
        wheres = []
        if tipo:
            wheres.append(f"c.tipo = '{tipo}'")
        if tipo_compromisso:
            wheres.append(f"COALESCE(c.tipo_compromisso,'consulta') = '{tipo_compromisso}'")
        where = ("WHERE " + " AND ".join(wheres)) if wheres else ""
        cur.execute(f"""
            SELECT c.id, c.data, c.hora, c.tipo, c.local, c.observacoes,
                   m.nome as medico, e.nome as especialidade,
                   c.medico_id, COALESCE(c.pauta,'[]') as pauta,
                   COALESCE(c.tipo_compromisso,'consulta') as tipo_compromisso,
                   c.clinica_id, cl.nome as clinica_nome, cl.tipo as clinica_tipo
            FROM consultas c
            LEFT JOIN medicos m ON m.id = c.medico_id
            LEFT JOIN especialidades e ON e.id = m.especialidade_id
            LEFT JOIN clinicas cl ON cl.id = c.clinica_id
            {where}
            ORDER BY c.data DESC, c.hora DESC
        """)
        cols = ["id","data","hora","tipo","local","observacoes","medico","especialidade",
                "medico_id","pauta","tipo_compromisso","clinica_id","clinica_nome","clinica_tipo"]
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def salvar_consulta(dados: dict) -> int:
    import json as _json
    pauta_json = _json.dumps(dados.get("pauta") or [], ensure_ascii=False)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur  = conn.cursor()
        if dados.get("id"):
            cur.execute("""
                UPDATE consultas SET medico_id=?, data=?, hora=?, tipo=?,
                local=?, observacoes=?, pauta=?, tipo_compromisso=?, clinica_id=?
                WHERE id=?
            """, (dados.get("medico_id"), dados["data"], dados.get("hora"),
                  dados.get("tipo","agendada"), dados.get("local"),
                  dados.get("observacoes"), pauta_json,
                  dados.get("tipo_compromisso","consulta"), dados.get("clinica_id"),
                  dados["id"]))
            cid = dados["id"]
        else:
            cur.execute("""
                INSERT INTO consultas
                    (medico_id, paciente_id, data, hora, tipo, local, observacoes,
                     pauta, tipo_compromisso, clinica_id)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (dados.get("medico_id"), dados.get("paciente_id"),
                  dados["data"], dados.get("hora"),
                  dados.get("tipo","agendada"), dados.get("local"),
                  dados.get("observacoes"), pauta_json,
                  dados.get("tipo_compromisso","consulta"), dados.get("clinica_id")))
            cid = cur.lastrowid
        conn.commit()
        return cid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# HELPERS — CLÍNICAS
# ══════════════════════════════════════════════════════════════

def listar_clinicas(so_ativas: bool = True) -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur   = conn.cursor()
        where = "WHERE ativo = 1" if so_ativas else ""
        cur.execute(f"""
            SELECT id, nome, tipo, telefone, email, website,
                   endereco_json, observacoes, ativo, criado_em
            FROM clinicas {where} ORDER BY nome
        """)
        cols = ["id","nome","tipo","telefone","email","website",
                "endereco_json","observacoes","ativo","criado_em"]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        conn.close()


def salvar_clinica(dados: dict) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur = conn.cursor()
        if dados.get("id"):
            cur.execute("""
                UPDATE clinicas SET nome=?, tipo=?, telefone=?, email=?,
                website=?, endereco_json=?, observacoes=?, ativo=? WHERE id=?
            """, (dados["nome"], dados.get("tipo","clinica"),
                  dados.get("telefone"), dados.get("email"),
                  dados.get("website"), dados.get("endereco_json"),
                  dados.get("observacoes"), dados.get("ativo",1), dados["id"]))
            cid = dados["id"]
        else:
            cur.execute("""
                INSERT INTO clinicas (nome, tipo, telefone, email, website,
                                      endereco_json, observacoes)
                VALUES (?,?,?,?,?,?,?)
            """, (dados["nome"], dados.get("tipo","clinica"),
                  dados.get("telefone"), dados.get("email"),
                  dados.get("website"), dados.get("endereco_json"),
                  dados.get("observacoes")))
            cid = cur.lastrowid
        conn.commit()
        return cid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def excluir_clinica(clinica_id: int) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("UPDATE clinicas SET ativo = 0 WHERE id = ?", (clinica_id,))
        conn.commit()
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# HELPERS — RECEITAS
# ══════════════════════════════════════════════════════════════

def salvar_receita(dados: dict) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO receitas (consulta_id, medico_id, drive_file_id, nome_arquivo, data, observacoes)
            VALUES (?,?,?,?,?,?)
        """, (dados.get("consulta_id"), dados.get("medico_id"),
              dados.get("drive_file_id"), dados.get("nome_arquivo"),
              dados.get("data"), dados.get("observacoes")))
        rid = cur.lastrowid
        conn.commit()
        return rid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def listar_receitas(consulta_id: int = None) -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur  = conn.cursor()
        where = f"WHERE r.consulta_id = {consulta_id}" if consulta_id else ""
        cur.execute(f"""
            SELECT r.id, r.data, r.nome_arquivo, r.drive_file_id,
                   r.observacoes, m.nome as medico
            FROM receitas r
            LEFT JOIN medicos m ON m.id = r.medico_id
            {where}
            ORDER BY r.data DESC
        """)
        cols = ["id","data","nome_arquivo","drive_file_id","observacoes","medico"]
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# HELPERS — REMÉDIOS
# ══════════════════════════════════════════════════════════════

def listar_remedios(so_ativos=True, tipo=None) -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur  = conn.cursor()
        clausulas = []
        if so_ativos:
            clausulas.append("r.ativo = 1")
        if tipo:
            clausulas.append(f"COALESCE(r.tipo,'remedio') = '{tipo}'")
        where = ("WHERE " + " AND ".join(clausulas)) if clausulas else ""
        cur.execute(f"""
            SELECT r.id, r.nome, r.dosagem, r.frequencia, r.data_inicio, r.data_fim,
                   r.estoque_atual, r.estoque_minimo, r.observacoes, r.ativo,
                   m.nome as medico, r.medico_id,
                   COALESCE(r.principio_ativo, '') as principio_ativo,
                   COALESCE(r.tipo, 'remedio') as tipo,
                   COALESCE(r.prescrito, 0) as prescrito,
                   (SELECT path FROM remedio_fotos
                    WHERE remedio_id = r.id AND COALESCE(tipo,'remedio') = 'remedio'
                    ORDER BY criado_em LIMIT 1) as foto_thumb
            FROM remedios r
            LEFT JOIN medicos m ON m.id = r.medico_id
            {where}
            ORDER BY r.nome
        """)
        cols = ["id","nome","dosagem","frequencia","data_inicio","data_fim",
                "estoque_atual","estoque_minimo","observacoes","ativo","medico",
                "medico_id","principio_ativo","tipo","prescrito","foto_thumb"]
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def salvar_remedio(dados: dict) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur  = conn.cursor()
        if dados.get("id"):
            cur.execute("""
                UPDATE remedios SET nome=?, dosagem=?, frequencia=?, data_inicio=?,
                data_fim=?, medico_id=?, receita_id=?, estoque_atual=?,
                estoque_minimo=?, ativo=?, observacoes=?, principio_ativo=?,
                tipo=?, prescrito=? WHERE id=?
            """, (dados["nome"], dados.get("dosagem"), dados.get("frequencia"),
                  dados.get("data_inicio"), dados.get("data_fim"),
                  dados.get("medico_id"), dados.get("receita_id"),
                  dados.get("estoque_atual", 0), dados.get("estoque_minimo", 5),
                  dados.get("ativo", 1), dados.get("observacoes"),
                  dados.get("principio_ativo"),
                  dados.get("tipo", "remedio"), dados.get("prescrito", 0),
                  dados["id"]))
            rid = dados["id"]
        else:
            cur.execute("""
                INSERT INTO remedios (nome, dosagem, frequencia, data_inicio, data_fim,
                medico_id, receita_id, estoque_atual, estoque_minimo, observacoes,
                principio_ativo, tipo, prescrito)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (dados["nome"], dados.get("dosagem"), dados.get("frequencia"),
                  dados.get("data_inicio"), dados.get("data_fim"),
                  dados.get("medico_id"), dados.get("receita_id"),
                  dados.get("estoque_atual", 0), dados.get("estoque_minimo", 5),
                  dados.get("observacoes"), dados.get("principio_ativo"),
                  dados.get("tipo", "remedio"), dados.get("prescrito", 0)))
            rid = cur.lastrowid
        conn.commit()
        return rid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def remedios_estoque_baixo() -> list[dict]:
    """Retorna remédios onde estoque_atual <= estoque_minimo."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur  = conn.cursor()
        cur.execute("""
            SELECT id, nome, dosagem, estoque_atual, estoque_minimo
            FROM remedios
            WHERE ativo = 1 AND estoque_atual <= estoque_minimo
            ORDER BY nome
        """)
        rows = cur.fetchall()
        return [{"id": r[0], "nome": r[1], "dosagem": r[2],
                 "estoque_atual": r[3], "estoque_minimo": r[4]} for r in rows]
    finally:
        conn.close()


# ── HORÁRIOS DE REMÉDIOS ─────────────────────────────────────

def salvar_horarios_remedio(remedio_id, horarios):
    """Substitui horários. horarios = ["08:00", "14:00", "22:00"]"""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM remedios_horarios WHERE remedio_id = ?", (remedio_id,))
        for h in horarios:
            h = h.strip()
            if h:
                cur.execute("INSERT INTO remedios_horarios (remedio_id, hora) VALUES (?,?)",
                            (remedio_id, h))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()


def listar_horarios_remedio(remedio_id):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        rows = conn.execute(
            "SELECT id, hora FROM remedios_horarios WHERE remedio_id=? ORDER BY hora",
            (remedio_id,)).fetchall()
        return [{"id": r[0], "hora": r[1]} for r in rows]
    finally:
        conn.close()


# ── TOMADAS (tomou / não tomou) ──────────────────────────────

def registrar_tomada(remedio_id, data, hora, status, horario_id=None):
    """status: 'tomou', 'nao_tomou', 'pendente'"""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, status FROM remedios_tomadas WHERE remedio_id=? AND data=? AND hora=?",
                    (remedio_id, data, hora))
        row = cur.fetchone()
        old_status = row[1] if row else None

        if row:
            cur.execute("UPDATE remedios_tomadas SET status=?, registrado_em=datetime('now') WHERE id=?",
                        (status, row[0]))
            tid = row[0]
        else:
            cur.execute("""INSERT INTO remedios_tomadas (remedio_id, horario_id, data, hora, status)
                           VALUES (?,?,?,?,?)""",
                        (remedio_id, horario_id, data, hora, status))
            tid = cur.lastrowid

        # Ajustar estoque
        if status == "tomou" and old_status != "tomou":
            cur.execute("UPDATE remedios SET estoque_atual = MAX(0, estoque_atual - 1) WHERE id=?",
                        (remedio_id,))
        elif status != "tomou" and old_status == "tomou":
            cur.execute("UPDATE remedios SET estoque_atual = estoque_atual + 1 WHERE id=?",
                        (remedio_id,))

        conn.commit()
        return tid
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()


def listar_tomadas_hoje(data=None):
    """Retorna tomadas de hoje com info do remédio, agrupáveis por hora."""
    if not data:
        from datetime import date as _d
        data = _d.today().isoformat()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        rows = conn.execute("""
            SELECT r.id, r.nome, r.dosagem, r.frequencia,
                   r.estoque_atual, r.estoque_minimo, r.foto_path,
                   rh.id, rh.hora,
                   COALESCE(rt.status, 'pendente'), rt.id
            FROM remedios r
            JOIN remedios_horarios rh ON rh.remedio_id = r.id
            LEFT JOIN remedios_tomadas rt ON rt.remedio_id = r.id AND rt.hora = rh.hora AND rt.data = ?
            WHERE r.ativo = 1
            ORDER BY rh.hora, r.nome
        """, (data,)).fetchall()
        cols = ["remedio_id","nome","dosagem","frequencia","estoque_atual",
                "estoque_minimo","foto_path","horario_id","hora","status","tomada_id"]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def resumo_adesao(remedio_id, dias=30):
    """Resumo de adesão dos últimos N dias."""
    from datetime import date as _d, timedelta
    dt_ini = (_d.today() - timedelta(days=dias)).isoformat()
    dt_fim = _d.today().isoformat()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        rows = conn.execute("""
            SELECT status, COUNT(*) FROM remedios_tomadas
            WHERE remedio_id=? AND data BETWEEN ? AND ?
            GROUP BY status
        """, (remedio_id, dt_ini, dt_fim)).fetchall()
        r = {"tomou": 0, "nao_tomou": 0, "pendente": 0, "total": 0}
        for st, qtd in rows:
            r[st] = qtd; r["total"] += qtd
        r["percentual"] = round(r["tomou"] / r["total"] * 100, 1) if r["total"] > 0 else 0
        return r
    finally:
        conn.close()


def atualizar_foto_remedio(remedio_id, foto_path):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("UPDATE remedios SET foto_path=? WHERE id=?", (foto_path, remedio_id))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()


# ── REMÉDIO: GALERIA DE FOTOS ─────────────────────────────────

def listar_fotos_remedio(remedio_id: int, tipo: str = None) -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        where = "AND COALESCE(tipo,'remedio') = ?" if tipo else ""
        params = (remedio_id, tipo) if tipo else (remedio_id,)
        rows = conn.execute(
            f"SELECT id, path, legenda, COALESCE(tipo,'remedio') as tipo, "
            f"data_validade, criado_em FROM remedio_fotos "
            f"WHERE remedio_id=? {where} ORDER BY criado_em",
            params
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        import logging; logging.getLogger(__name__).error("listar_fotos_remedio: %s", e, exc_info=True)
        return []
    finally:
        conn.close()


def adicionar_foto_remedio(remedio_id: int, path: str, legenda: str = "",
                           tipo: str = "remedio", data_validade: str = None) -> int | None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur = conn.execute(
            "INSERT INTO remedio_fotos (remedio_id, path, legenda, tipo, data_validade) "
            "VALUES (?,?,?,?,?)",
            (remedio_id, path, legenda or "", tipo, data_validade)
        )
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        import logging; logging.getLogger(__name__).error("adicionar_foto_remedio: %s", e, exc_info=True)
        conn.rollback(); return None
    finally:
        conn.close()


def excluir_foto_remedio(foto_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("DELETE FROM remedio_fotos WHERE id=?", (foto_id,))
        conn.commit()
        return True
    except Exception as e:
        import logging; logging.getLogger(__name__).error("excluir_foto_remedio: %s", e, exc_info=True)
        conn.rollback(); return False
    finally:
        conn.close()


# ── FARMÁCIAS ────────────────────────────────────────────────

def listar_farmacias(so_ativas=True):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        where = "WHERE ativo=1" if so_ativas else ""
        rows = conn.execute(f"""
            SELECT id, nome, endereco, telefone, whatsapp, site, app,
                   delivery, preferida, observacoes, ativo
            FROM farmacias {where} ORDER BY preferida DESC, nome
        """).fetchall()
        cols = ["id","nome","endereco","telefone","whatsapp","site","app",
                "delivery","preferida","observacoes","ativo"]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def salvar_farmacia(dados):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur = conn.cursor()
        if dados.get("id"):
            cur.execute("""UPDATE farmacias SET nome=?, endereco=?, telefone=?, whatsapp=?,
                           site=?, app=?, delivery=?, preferida=?, observacoes=?, ativo=? WHERE id=?""",
                        (dados["nome"], dados.get("endereco"), dados.get("telefone"),
                         dados.get("whatsapp"), dados.get("site"), dados.get("app"),
                         dados.get("delivery", 0), dados.get("preferida", 0),
                         dados.get("observacoes"), dados.get("ativo", 1), dados["id"]))
            fid = dados["id"]
        else:
            cur.execute("""INSERT INTO farmacias (nome, endereco, telefone, whatsapp, site, app,
                           delivery, preferida, observacoes) VALUES (?,?,?,?,?,?,?,?,?)""",
                        (dados["nome"], dados.get("endereco"), dados.get("telefone"),
                         dados.get("whatsapp"), dados.get("site"), dados.get("app"),
                         dados.get("delivery", 0), dados.get("preferida", 0),
                         dados.get("observacoes")))
            fid = cur.lastrowid
        conn.commit()
        return fid
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()


# ── COMPRAS ──────────────────────────────────────────────────

def salvar_compra(dados):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur = conn.cursor()
        cur.execute("""INSERT INTO remedios_compras
                       (remedio_id, farmacia_id, data_compra, quantidade,
                        preco_unitario, preco_total, foto_cupom, observacoes)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (dados["remedio_id"], dados.get("farmacia_id"),
                     dados["data_compra"], dados.get("quantidade", 1),
                     dados.get("preco_unitario"), dados.get("preco_total"),
                     dados.get("foto_cupom"), dados.get("observacoes")))
        cid = cur.lastrowid
        if dados.get("quantidade"):
            cur.execute("UPDATE remedios SET estoque_atual = estoque_atual + ? WHERE id=?",
                        (dados["quantidade"], dados["remedio_id"]))
        conn.commit()
        return cid
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()


def listar_compras_remedio(remedio_id):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        rows = conn.execute("""
            SELECT c.id, c.data_compra, c.quantidade, c.preco_unitario, c.preco_total,
                   c.foto_cupom, c.observacoes, f.nome as farmacia, f.id as farmacia_id
            FROM remedios_compras c
            LEFT JOIN farmacias f ON f.id = c.farmacia_id
            WHERE c.remedio_id = ?
            ORDER BY c.data_compra DESC
        """, (remedio_id,)).fetchall()
        cols = ["id","data_compra","quantidade","preco_unitario","preco_total",
                "foto_cupom","observacoes","farmacia","farmacia_id"]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def estatisticas_preco_remedio(remedio_id):
    """Retorna preco_medio, melhor_preco, melhor_farmacia, ultimo_preco."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        r = conn.execute("""
            SELECT AVG(preco_unitario), MIN(preco_unitario), MAX(preco_unitario)
            FROM remedios_compras WHERE remedio_id=? AND preco_unitario > 0
        """, (remedio_id,)).fetchone()
        melhor = conn.execute("""
            SELECT c.preco_unitario, f.nome FROM remedios_compras c
            LEFT JOIN farmacias f ON f.id = c.farmacia_id
            WHERE c.remedio_id=? AND c.preco_unitario > 0
            ORDER BY c.preco_unitario ASC LIMIT 1
        """, (remedio_id,)).fetchone()
        ultimo = conn.execute("""
            SELECT c.preco_unitario, c.preco_total, f.nome, c.data_compra
            FROM remedios_compras c LEFT JOIN farmacias f ON f.id = c.farmacia_id
            WHERE c.remedio_id=? ORDER BY c.data_compra DESC LIMIT 1
        """, (remedio_id,)).fetchone()
        return {
            "preco_medio": round(r[0], 2) if r and r[0] else None,
            "menor_preco": round(r[1], 2) if r and r[1] else None,
            "maior_preco": round(r[2], 2) if r and r[2] else None,
            "melhor_farmacia": melhor[1] if melhor else None,
            "melhor_preco_valor": round(melhor[0], 2) if melhor else None,
            "ultimo_preco": round(ultimo[0], 2) if ultimo else None,
            "ultima_farmacia": ultimo[2] if ultimo else None,
            "ultima_data": ultimo[3] if ultimo else None,
        }
    finally:
        conn.close()


# ── ORÇAMENTOS (WhatsApp) ────────────────────────────────────

def criar_orcamento(farmacia_id, mensagem, itens):
    """Cria solicitação. itens = [{"remedio_id", "nome", "dosagem", "quantidade"}]"""
    from datetime import date as _d
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur = conn.cursor()
        cur.execute("""INSERT INTO remedios_orcamentos (farmacia_id, data_envio, mensagem_envio, status)
                       VALUES (?,?,?,?)""", (farmacia_id, _d.today().isoformat(), mensagem, "enviado"))
        oid = cur.lastrowid
        for item in itens:
            cur.execute("""INSERT INTO orcamento_itens (orcamento_id, remedio_id, nome_pedido, dosagem_pedido, quantidade)
                           VALUES (?,?,?,?,?)""",
                        (oid, item.get("remedio_id"), item["nome"],
                         item.get("dosagem"), item.get("quantidade", 1)))
        conn.commit()
        return oid
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()


def salvar_resposta_orcamento(orcamento_id, resposta_bruta, itens_ia):
    """Salva resposta da farmácia (texto bruto + itens extraídos pela IA)."""
    import json as _json
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur = conn.cursor()
        cur.execute("""UPDATE remedios_orcamentos SET resposta_bruta=?, resposta_ia=?, status='respondido'
                       WHERE id=?""", (resposta_bruta, _json.dumps(itens_ia, ensure_ascii=False), orcamento_id))
        for item in itens_ia:
            if item.get("preco") and item.get("nome_pedido"):
                cur.execute("""UPDATE orcamento_itens SET preco_informado=?, disponivel=?, observacao=?
                               WHERE orcamento_id=? AND nome_pedido=?""",
                            (item["preco"], item.get("disponivel", 1),
                             item.get("observacao"), orcamento_id, item["nome_pedido"]))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()


def listar_orcamentos(farmacia_id=None):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        if farmacia_id:
            rows = conn.execute("""SELECT o.id, o.data_envio, o.status, f.nome, o.farmacia_id
                FROM remedios_orcamentos o LEFT JOIN farmacias f ON f.id = o.farmacia_id
                WHERE o.farmacia_id=? ORDER BY o.data_envio DESC""", (farmacia_id,)).fetchall()
        else:
            rows = conn.execute("""SELECT o.id, o.data_envio, o.status, f.nome, o.farmacia_id
                FROM remedios_orcamentos o LEFT JOIN farmacias f ON f.id = o.farmacia_id
                ORDER BY o.data_envio DESC""").fetchall()
        cols = ["id","data_envio","status","farmacia","farmacia_id"]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def gerar_mensagem_orcamento(remedios_ids=None):
    """Gera texto formatado para enviar via WhatsApp."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        if remedios_ids:
            ph = ",".join("?" * len(remedios_ids))
            rows = conn.execute(f"""SELECT nome, dosagem, estoque_atual, estoque_minimo
                FROM remedios WHERE id IN ({ph}) AND ativo=1""", remedios_ids).fetchall()
        else:
            rows = conn.execute("""SELECT nome, dosagem, estoque_atual, estoque_minimo
                FROM remedios WHERE ativo=1 AND estoque_atual <= estoque_minimo ORDER BY nome""").fetchall()
        if not rows:
            return None, []
        linhas = ["Olá! Gostaria de um orçamento para os seguintes medicamentos:\n"]
        itens = []
        for i, (nome, dosagem, est, mn) in enumerate(rows, 1):
            qtd = max(1, (mn or 5) * 2 - (est or 0))
            desc = f"{nome}" + (f" {dosagem}" if dosagem else "")
            linhas.append(f"{i}. {desc} — {qtd} unidades")
            itens.append({"nome": nome, "dosagem": dosagem, "quantidade": qtd})
        linhas.append("\nAgradeço o retorno! 🙏")
        return "\n".join(linhas), itens
    finally:
        conn.close()


def link_whatsapp(numero, texto):
    """Gera link wa.me para abrir WhatsApp com mensagem."""
    import urllib.parse
    num = "".join(c for c in (numero or "") if c.isdigit())
    if not num:
        return None
    if len(num) <= 11:
        num = "55" + num
    return f"https://wa.me/{num}?text={urllib.parse.quote(texto)}"


def analisar_resposta_orcamento_ia(texto_resposta, itens_pedidos):
    """Usa Claude API para extrair preços da resposta da farmácia."""
    try:
        import anthropic, json as _json
        nomes = ", ".join(f'"{i["nome"]}"' for i in itens_pedidos)
        prompt = f"""Analise a resposta de uma farmácia sobre um orçamento de medicamentos.
Extraia o preço de cada medicamento mencionado.
Medicamentos solicitados: {nomes}
Resposta da farmácia:
\"\"\"{texto_resposta}\"\"\"
Responda APENAS com um JSON array, sem markdown. Cada item:
{{"nome_pedido": "nome", "preco": 12.90, "disponivel": true, "observacao": ""}}
Se não encontrar preço, coloque preco: null e disponivel: false."""
        client = anthropic.Anthropic()
        resp = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=1000,
            messages=[{"role": "user", "content": prompt}])
        texto = resp.content[0].text.strip()
        if texto.startswith("```"):
            texto = texto.split("\n", 1)[1].rsplit("```", 1)[0]
        return _json.loads(texto)
    except Exception as ex:
        return [{"nome_pedido": i["nome"], "preco": None,
                 "disponivel": False, "observacao": f"Erro IA: {ex}"}
                for i in itens_pedidos]


# ══════════════════════════════════════════════════════════════
# HELPERS — PERFIL DO USUÁRIO
# ══════════════════════════════════════════════════════════════

def salvar_perfil(dados: dict):
    """Upsert do perfil (sempre id=1)."""
    import json as _json
    conn = sqlite3.connect(CORE_DB, timeout=30)
    try:
        conn.execute("""
        INSERT INTO perfil_usuario (
            id, nome, email, data_nasc, sexo, foto_url,
            peso, altura, tipo_sanguineo, condicoes_cronicas,
            contato_emergencia, tel_emergencia,
            tema, accent_color, tamanho_fonte, atualizado_em
        )
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(id) DO UPDATE SET
            nome               = excluded.nome,
            email              = excluded.email,
            data_nasc          = excluded.data_nasc,
            sexo               = excluded.sexo,
            foto_url           = excluded.foto_url,
            peso               = excluded.peso,
            altura             = excluded.altura,
            tipo_sanguineo     = excluded.tipo_sanguineo,
            condicoes_cronicas = excluded.condicoes_cronicas,
            contato_emergencia = excluded.contato_emergencia,
            tel_emergencia     = excluded.tel_emergencia,
            tema               = excluded.tema,
            accent_color       = excluded.accent_color,
            tamanho_fonte      = excluded.tamanho_fonte,
            atualizado_em      = datetime('now')
    """, (
        dados.get("nome"),
        dados.get("email"),
        dados.get("data_nasc"),
        dados.get("sexo"),
        dados.get("foto_url"),
        dados.get("peso"),
        dados.get("altura"),
        dados.get("tipo_sanguineo"),
        _json.dumps(dados.get("condicoes_cronicas") or [], ensure_ascii=False),
        dados.get("contato_emergencia"),
        dados.get("tel_emergencia"),
        dados.get("tema", "dark"),
        dados.get("accent_color", "#58A6FF"),
        dados.get("tamanho_fonte", "medio"),
    ))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def carregar_perfil() -> dict | None:
    """Retorna o perfil ou None se ainda não cadastrado."""
    import json as _json
    _migrar_campos_perfil()  # garante colunas novas no banco existente
    _migrar_status_exames()   # garante coluna status em exames
    conn = sqlite3.connect(CORE_DB, timeout=30)
    try:
        cur  = conn.cursor()
        cur.execute("""
            SELECT nome, email, data_nasc, sexo, foto_url,
                   peso, altura, tipo_sanguineo, condicoes_cronicas,
                   contato_emergencia, tel_emergencia,
                   tema, accent_color, tamanho_fonte
            FROM perfil_usuario WHERE id = 1
        """)
        row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    try:
        condicoes = _json.loads(row[8] or "[]")
    except Exception:
        condicoes = []
    return {
        "nome":               row[0],
        "email":              row[1],
        "data_nasc":          row[2],
        "sexo":               row[3],
        "foto_url":           row[4],
        "peso":               row[5],
        "altura":             row[6],
        "tipo_sanguineo":     row[7],
        "condicoes_cronicas": condicoes,
        "contato_emergencia": row[9],
        "tel_emergencia":     row[10],
        "tema":               row[11] or "dark",
        "accent_color":       row[12] or "#58A6FF",
        "tamanho_fonte":      row[13] or "medio",
    }


def perfil_completo() -> bool:
    """True se nome, data_nasc e sexo estão preenchidos."""
    p = carregar_perfil()
    if not p:
        return False
    return bool(p.get("nome") and p.get("data_nasc") and p.get("sexo"))


# ══════════════════════════════════════════════════════════════
# HELPERS — LINKS DE MÉDICO
# ══════════════════════════════════════════════════════════════

def criar_link_medico(medico_id: int, nome_medico: str) -> str:
    """Gera token único e salva. Retorna o token."""
    import secrets
    # Remove link anterior se existir
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("DELETE FROM links_medico WHERE medico_id = ?", (medico_id,))
        token = secrets.token_urlsafe(32)
        conn.execute("""
            INSERT INTO links_medico (token, medico_id, nome_medico)
            VALUES (?, ?, ?)
        """, (token, medico_id, nome_medico))
        conn.commit()
        return token
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def buscar_link_medico_por_token(token: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur  = conn.cursor()
        cur.execute("""
            SELECT token, medico_id, nome_medico, criado_em,
                   ultimo_acesso, acessos, ativo
            FROM links_medico WHERE token = ? AND ativo = 1
        """, (token,))
        row = cur.fetchone()
        if row:
            # Registra acesso
            conn.execute("""
                UPDATE links_medico
                SET acessos = acessos + 1,
                    ultimo_acesso = datetime('now')
                WHERE token = ?
            """, (token,))
            conn.commit()
    finally:
        conn.close()
    if not row:
        return None
    return dict(zip(
        ["token","medico_id","nome_medico","criado_em",
         "ultimo_acesso","acessos","ativo"], row
    ))


def listar_links_medicos() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur  = conn.cursor()
        cur.execute("""
            SELECT l.token, l.medico_id, l.nome_medico,
                   l.criado_em, l.ultimo_acesso, l.acessos, l.ativo
            FROM links_medico l
            ORDER BY l.criado_em DESC
        """)
        cols = ["token","medico_id","nome_medico","criado_em",
                "ultimo_acesso","acessos","ativo"]
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def revogar_link_medico(token: str):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("UPDATE links_medico SET ativo = 0 WHERE token = ?", (token,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# HELPERS — USUÁRIOS E SESSÕES
# ══════════════════════════════════════════════════════════════

def criar_usuario_medico(username: str, senha_hash: str,
                          nome: str, email: str = None) -> int:
    conn = sqlite3.connect(CORE_DB, timeout=30)
    try:
        cur  = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO usuarios (username, senha_hash, perfil, nome, email)
            VALUES (?, ?, 'medico', ?, ?)
        """, (username, senha_hash, nome, email))
        uid = cur.lastrowid
        conn.commit()
        return uid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def buscar_usuario(username: str) -> dict | None:
    conn = sqlite3.connect(CORE_DB, timeout=30)
    try:
        cur  = conn.cursor()
        cur.execute("""
            SELECT id, username, senha_hash, perfil, nome, email, ativo
            FROM usuarios WHERE username = ?
        """, (username,))
        row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return dict(zip(
        ["id","username","senha_hash","perfil","nome","email","ativo"], row
    ))


def salvar_sessao(token: str, usuario_id: int, perfil: str,
                   expira_em: str, ip: str = None):
    conn = sqlite3.connect(CORE_DB, timeout=30)
    try:
        conn.execute("""
            INSERT OR REPLACE INTO sessoes (token, usuario_id, perfil, expira_em, ip)
            VALUES (?,?,?,?,?)
        """, (token, usuario_id, perfil, expira_em, ip))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def buscar_sessao(token: str) -> dict | None:
    conn = sqlite3.connect(CORE_DB, timeout=30)
    try:
        cur  = conn.cursor()
        cur.execute("""
            SELECT s.token, s.usuario_id, s.perfil, s.expira_em,
                   u.nome, u.username
            FROM sessoes s
            JOIN usuarios u ON u.id = s.usuario_id
            WHERE s.token = ? AND datetime('now') < s.expira_em
        """, (token,))
        row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return dict(zip(
        ["token","usuario_id","perfil","expira_em","nome","username"], row
    ))


def revogar_sessao(token: str):
    conn = sqlite3.connect(CORE_DB, timeout=30)
    try:
        conn.execute("DELETE FROM sessoes WHERE token = ?", (token,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def atualizar_ultimo_acesso(usuario_id: int):
    conn = sqlite3.connect(CORE_DB, timeout=30)
    try:
        conn.execute("""
            UPDATE usuarios SET ultimo_acesso = datetime('now')
            WHERE id = ?
        """, (usuario_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# HELPERS — COMPARTILHAMENTOS
# ══════════════════════════════════════════════════════════════

def salvar_compartilhamento(dados: dict) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO compartilhamentos
            (destinatario, email_dest, finalidade, conteudo_desc,
             drive_file_id, drive_link)
            VALUES (?,?,?,?,?,?)
        """, (
            dados["destinatario"],
            dados.get("email_dest"),
            dados["finalidade"],
            dados.get("conteudo_desc"),
            dados.get("drive_file_id"),
            dados.get("drive_link"),
        ))
        cid = cur.lastrowid
        conn.commit()
        return cid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def listar_compartilhamentos(so_ativos=True) -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur  = conn.cursor()
        where = "WHERE ativo = 1" if so_ativos else ""
        cur.execute(f"""
            SELECT id, destinatario, email_dest, finalidade, conteudo_desc,
                   drive_file_id, drive_link, data_criacao, data_revogacao, ativo
            FROM compartilhamentos {where}
            ORDER BY data_criacao DESC
        """)
        cols = ["id","destinatario","email_dest","finalidade","conteudo_desc",
                "drive_file_id","drive_link","data_criacao","data_revogacao","ativo"]
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def revogar_compartilhamento(cid: int):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("""
            UPDATE compartilhamentos
            SET ativo = 0, data_revogacao = datetime('now')
            WHERE id = ?
        """, (cid,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# HELPERS — EXTRATORES DE LABORATÓRIO (auto-evolutivo)
# ══════════════════════════════════════════════════════════════

def listar_lab_extratores(so_ativos=True):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        where = "WHERE ativo=1" if so_ativos else ""
        rows = conn.execute(f"""
            SELECT id, laboratorio, versao, tipo, regex_nome,
                   taxa_acerto, total_usos, custo_acumulado, ativo,
                   criado_em, atualizado_em
            FROM lab_extratores {where}
            ORDER BY total_usos DESC, laboratorio
        """).fetchall()
        cols = ["id","laboratorio","versao","tipo","regex_nome",
                "taxa_acerto","total_usos","custo_acumulado","ativo",
                "criado_em","atualizado_em"]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def buscar_extrator_por_lab(laboratorio):
    """Busca extrator ativo para um laboratório (por nome)."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        row = conn.execute("""
            SELECT id, laboratorio, versao, tipo, prompt_extracao,
                   regex_nome, regex_resultado, exemplo_entrada, exemplo_saida,
                   taxa_acerto, total_usos
            FROM lab_extratores
            WHERE UPPER(laboratorio) = UPPER(?) AND ativo = 1
            ORDER BY versao DESC LIMIT 1
        """, (laboratorio,)).fetchone()
        if not row:
            return None
        cols = ["id","laboratorio","versao","tipo","prompt_extracao",
                "regex_nome","regex_resultado","exemplo_entrada","exemplo_saida",
                "taxa_acerto","total_usos"]
        return dict(zip(cols, row))
    finally:
        conn.close()


def salvar_lab_extrator(dados):
    """Cria ou atualiza extrator de laboratório."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur = conn.cursor()
        if dados.get("id"):
            cur.execute("""
                UPDATE lab_extratores SET
                    laboratorio=?, versao=versao+1, tipo=?, prompt_extracao=?,
                    regex_nome=?, regex_resultado=?, exemplo_entrada=?, exemplo_saida=?,
                    atualizado_em=datetime('now')
                WHERE id=?
            """, (dados["laboratorio"], dados.get("tipo","ia"),
                  dados.get("prompt_extracao"), dados.get("regex_nome"),
                  dados.get("regex_resultado"), dados.get("exemplo_entrada"),
                  dados.get("exemplo_saida"), dados["id"]))
            eid = dados["id"]
        else:
            cur.execute("""
                INSERT INTO lab_extratores
                    (laboratorio, tipo, prompt_extracao, regex_nome, regex_resultado,
                     exemplo_entrada, exemplo_saida)
                VALUES (?,?,?,?,?,?,?)
            """, (dados["laboratorio"], dados.get("tipo","ia"),
                  dados.get("prompt_extracao"), dados.get("regex_nome"),
                  dados.get("regex_resultado"), dados.get("exemplo_entrada"),
                  dados.get("exemplo_saida")))
            eid = cur.lastrowid
        conn.commit()
        return eid
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()


def registrar_uso_extrator(extrator_id, acertou=True, custo=0.0):
    """Incrementa contadores de uso e acerto do extrator."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("""
            UPDATE lab_extratores SET
                total_usos = total_usos + 1,
                custo_acumulado = custo_acumulado + ?,
                taxa_acerto = CASE
                    WHEN total_usos = 0 THEN ?
                    ELSE (taxa_acerto * total_usos + ?) / (total_usos + 1)
                END,
                atualizado_em = datetime('now')
            WHERE id = ?
        """, (custo, 100.0 if acertou else 0.0,
              100.0 if acertou else 0.0, extrator_id))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# ROTINA DIÁRIA
# ══════════════════════════════════════════════════════════════

import logging as _logging
_logger_model = _logging.getLogger(__name__)


def listar_rotina(so_ativos=True):
    """Retorna itens da rotina diária ordenados por horário."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        where = "WHERE ativo=1" if so_ativos else ""
        rows = conn.execute(
            f"SELECT * FROM rotina_itens {where} ORDER BY horario, tipo, nome"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as ex:
        _logger_model.error("listar_rotina: %s", str(ex), exc_info=True)
        return []


def salvar_rotina_item(dados: dict) -> int | None:
    """INSERT ou UPDATE de item da rotina. Retorna id."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        with conn:
            if dados.get("id"):
                conn.execute("""
                    UPDATE rotina_itens SET
                        tipo=?, nome=?, horario=?, dias_semana=?,
                        descricao=?, quantidade=?, ativo=?
                    WHERE id=?
                """, (
                    dados.get("tipo","refeicao"), dados["nome"],
                    dados.get("horario"), dados.get("dias_semana"),
                    dados.get("descricao"), dados.get("quantidade"),
                    dados.get("ativo", 1), dados["id"],
                ))
                return dados["id"]
            else:
                cur = conn.execute("""
                    INSERT INTO rotina_itens
                        (tipo, nome, horario, dias_semana, descricao, quantidade, ativo)
                    VALUES (?,?,?,?,?,?,?)
                """, (
                    dados.get("tipo","refeicao"), dados["nome"],
                    dados.get("horario"), dados.get("dias_semana"),
                    dados.get("descricao"), dados.get("quantidade"),
                    dados.get("ativo", 1),
                ))
                return cur.lastrowid
    except Exception as ex:
        _logger_model.error("salvar_rotina_item: %s", str(ex), exc_info=True)
        return None
    finally:
        conn.close()


def excluir_rotina_item(item_id: int) -> bool:
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("DELETE FROM rotina_itens WHERE id=?", (item_id,))
        return True
    except Exception as ex:
        _logger_model.error("excluir_rotina_item: %s", str(ex), exc_info=True)
        return False


# ══════════════════════════════════════════════════════════════
# DIÁRIO DE SAÚDE
# ══════════════════════════════════════════════════════════════

def listar_diario(limite=90, offset=0):
    """Retorna registros do diário mais recentes primeiro."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        rows = conn.execute(
            "SELECT * FROM diario_saude ORDER BY data DESC, hora DESC LIMIT ? OFFSET ?",
            (limite, offset),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as ex:
        _logger_model.error("listar_diario: %s", str(ex), exc_info=True)
        return []


def salvar_diario_entrada(dados: dict) -> int | None:
    """INSERT ou UPDATE de entrada do diário. Retorna id."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        with conn:
            if dados.get("id"):
                conn.execute("""
                    UPDATE diario_saude SET
                        data=?, hora=?, humor=?, energia=?, sono_horas=?,
                        peso=?, pressao=?, relato=?, tags=?, remedio_tomado=?
                    WHERE id=?
                """, (
                    dados["data"], dados.get("hora"),
                    dados.get("humor"), dados.get("energia"),
                    dados.get("sono_horas"), dados.get("peso"),
                    dados.get("pressao"), dados["relato"],
                    dados.get("tags"), dados.get("remedio_tomado"),
                    dados["id"],
                ))
                return dados["id"]
            else:
                cur = conn.execute("""
                    INSERT INTO diario_saude
                        (data, hora, humor, energia, sono_horas,
                         peso, pressao, relato, tags, remedio_tomado)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (
                    dados["data"], dados.get("hora"),
                    dados.get("humor"), dados.get("energia"),
                    dados.get("sono_horas"), dados.get("peso"),
                    dados.get("pressao"), dados["relato"],
                    dados.get("tags"), dados.get("remedio_tomado"),
                ))
                return cur.lastrowid
    except Exception as ex:
        _logger_model.error("salvar_diario_entrada: %s", str(ex), exc_info=True)
        return None
    finally:
        conn.close()


def excluir_diario_entrada(entrada_id: int) -> bool:
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("DELETE FROM diario_saude WHERE id=?", (entrada_id,))
        return True
    except Exception as ex:
        _logger_model.error("excluir_diario_entrada: %s", str(ex), exc_info=True)
        return False


def tendencias_diario(dias=30):
    """Retorna médias de humor, energia e sono dos últimos N dias."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        row = conn.execute("""
            SELECT
                ROUND(AVG(humor),1)     AS avg_humor,
                ROUND(AVG(energia),1)   AS avg_energia,
                ROUND(AVG(sono_horas),1) AS avg_sono,
                ROUND(AVG(peso),1)      AS avg_peso,
                COUNT(*)                AS total
            FROM diario_saude
            WHERE data >= date('now', ? || ' days')
        """, (f"-{dias}",)).fetchone()
        conn.close()
        return dict(row) if row else {}
    except Exception as ex:
        _logger_model.error("tendencias_diario: %s", str(ex), exc_info=True)
        return {}


def tags_frequentes(dias=90, top=10):
    """Retorna tags mais frequentes no diário."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        rows = conn.execute("""
            SELECT tags FROM diario_saude
            WHERE tags IS NOT NULL AND tags != ''
              AND data >= date('now', ? || ' days')
        """, (f"-{dias}",)).fetchall()
        conn.close()
        from collections import Counter
        contagem: Counter = Counter()
        for (tags_str,) in rows:
            for t in tags_str.split(","):
                t = t.strip()
                if t:
                    contagem[t] += 1
        return contagem.most_common(top)
    except Exception as ex:
        _logger_model.error("tags_frequentes: %s", str(ex), exc_info=True)
        return []


# ══════════════════════════════════════════════════════════════
# HELPERS — ROTINAS DIARIAS
# ══════════════════════════════════════════════════════════════

def listar_templates(so_ativos=True) -> list[dict]:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            where = "WHERE ativo=1" if so_ativos else ""
            rows = conn.execute(f"""
                SELECT t.id, t.nome, t.icone, t.cor, t.padrao, t.ativo,
                       COUNT(m.id) as total_momentos
                FROM rotinas_templates t
                LEFT JOIN momentos_rotina m ON m.template_id = t.id
                {where}
                GROUP BY t.id ORDER BY t.padrao DESC, t.nome
            """).fetchall()
            cols = ["id","nome","icone","cor","padrao","ativo","total_momentos"]
            return [dict(zip(cols, r)) for r in rows]
    except Exception as ex:
        print(f"[MODEL] listar_templates: {ex}")
        return []


def salvar_template(dados: dict) -> int:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            if dados.get("id"):
                conn.execute("""UPDATE rotinas_templates SET nome=?, icone=?, cor=?, padrao=?, ativo=?
                    WHERE id=?""",
                    (dados["nome"], dados.get("icone","today_rounded"),
                     dados.get("cor","#58A6FF"), 1 if dados.get("padrao") else 0,
                     1 if dados.get("ativo", True) else 0, dados["id"]))
                return dados["id"]
            else:
                cur = conn.execute("""INSERT INTO rotinas_templates (nome,icone,cor,padrao,ativo)
                    VALUES (?,?,?,?,?)""",
                    (dados["nome"], dados.get("icone","today_rounded"),
                     dados.get("cor","#58A6FF"), 1 if dados.get("padrao") else 0, 1))
                return cur.lastrowid
    except Exception as ex:
        print(f"[MODEL] salvar_template: {ex}")
        return 0


def excluir_template(tid: int) -> None:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("DELETE FROM rotinas_templates WHERE id=?", (tid,))
    except Exception as ex:
        print(f"[MODEL] excluir_template: {ex}")


def listar_momentos(template_id: int) -> list[dict]:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            rows = conn.execute("""
                SELECT m.id, m.nome, m.tipo, m.horario, m.ordem,
                       COUNT(i.id) as total_itens
                FROM momentos_rotina m
                LEFT JOIN itens_momento i ON i.momento_id = m.id
                WHERE m.template_id=?
                GROUP BY m.id ORDER BY m.ordem, m.horario
            """, (template_id,)).fetchall()
            cols = ["id","nome","tipo","horario","ordem","total_itens"]
            return [dict(zip(cols, r)) for r in rows]
    except Exception as ex:
        print(f"[MODEL] listar_momentos: {ex}")
        return []


def salvar_momento(dados: dict) -> int:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            if dados.get("id"):
                conn.execute("""UPDATE momentos_rotina SET nome=?, tipo=?, horario=?, ordem=?
                    WHERE id=?""",
                    (dados["nome"], dados.get("tipo","outro"),
                     dados.get("horario"), dados.get("ordem", 0), dados["id"]))
                return dados["id"]
            else:
                cur = conn.execute("""INSERT INTO momentos_rotina (template_id,nome,tipo,horario,ordem)
                    VALUES (?,?,?,?,?)""",
                    (dados["template_id"], dados["nome"], dados.get("tipo","outro"),
                     dados.get("horario"), dados.get("ordem", 0)))
                return cur.lastrowid
    except Exception as ex:
        print(f"[MODEL] salvar_momento: {ex}")
        return 0


def excluir_momento(mid: int) -> None:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("DELETE FROM momentos_rotina WHERE id=?", (mid,))
    except Exception as ex:
        print(f"[MODEL] excluir_momento: {ex}")


def listar_itens(momento_id: int) -> list[dict]:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            rows = conn.execute("""
                SELECT i.id, i.tipo, i.descricao, i.detalhe, i.horario, i.ordem,
                       r.nome as remedio_nome, r.dosagem as remedio_dosagem
                FROM itens_momento i
                LEFT JOIN remedios r ON r.id = i.remedio_id
                WHERE i.momento_id=? ORDER BY i.ordem, i.id
            """, (momento_id,)).fetchall()
            cols = ["id","tipo","descricao","detalhe","horario","ordem",
                    "remedio_nome","remedio_dosagem"]
            return [dict(zip(cols, r)) for r in rows]
    except Exception as ex:
        print(f"[MODEL] listar_itens: {ex}")
        return []


def salvar_item(dados: dict) -> int:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            if dados.get("id"):
                conn.execute("""UPDATE itens_momento SET tipo=?, descricao=?, detalhe=?,
                    horario=?, remedio_id=?, ordem=? WHERE id=?""",
                    (dados.get("tipo","alimento"), dados["descricao"],
                     dados.get("detalhe"), dados.get("horario"),
                     dados.get("remedio_id"), dados.get("ordem", 0), dados["id"]))
                return dados["id"]
            else:
                cur = conn.execute("""INSERT INTO itens_momento
                    (momento_id,tipo,descricao,detalhe,horario,remedio_id,ordem)
                    VALUES (?,?,?,?,?,?,?)""",
                    (dados["momento_id"], dados.get("tipo","alimento"), dados["descricao"],
                     dados.get("detalhe"), dados.get("horario"),
                     dados.get("remedio_id"), dados.get("ordem", 0)))
                return cur.lastrowid
    except Exception as ex:
        print(f"[MODEL] salvar_item: {ex}")
        return 0


def excluir_item(iid: int) -> None:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("DELETE FROM itens_momento WHERE id=?", (iid,))
    except Exception as ex:
        print(f"[MODEL] excluir_item: {ex}")


if __name__ == "__main__":
    criar_tabelas()
    print("Banco de dados iniciado com sucesso!")
