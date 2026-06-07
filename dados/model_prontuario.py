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

# Banco do MÓDULO Prontuário: fica junto ao módulo em prontuario/dados/
DB_PATH = _os.path.join(_HERE_MODEL, "prontuario.db")     # prontuario/dados/prontuario.db
CORE_DB = DB_PATH  # alias — tudo no mesmo banco
_os.makedirs(_HERE_MODEL, exist_ok=True)


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

import datetime as _datetime


def normalizar_data(s):
    """Converte DD/MM/YYYY para YYYY-MM-DD. Datas ja em ISO passam sem alteracao."""
    if not s:
        return s
    s = str(s).strip()
    if len(s) == 10 and s[2] == '/' and s[5] == '/':
        try:
            return _datetime.datetime.strptime(s, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            pass
    return s


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
        ("foto_url",           "TEXT"),
    ]
    for _db in (DB_PATH, CORE_DB):
        conn = None
        try:
            conn = sqlite3.connect(_db, timeout=30)
            cur  = conn.cursor()
            # garante que a tabela existe em prontuario.db
            cur.execute("""
                CREATE TABLE IF NOT EXISTS perfil_usuario (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    nome TEXT, email TEXT, data_nasc TEXT, sexo TEXT,
                    foto_url TEXT, criado_em TEXT DEFAULT (datetime('now')),
                    atualizado_em TEXT DEFAULT (datetime('now'))
                )
            """)
            cols = [r[1] for r in cur.execute('PRAGMA table_info(perfil_usuario)').fetchall()]
            for col, tipo in novos:
                if col not in cols:
                    try:
                        cur.execute(f'ALTER TABLE perfil_usuario ADD COLUMN {col} {tipo}')
                    except Exception:
                        pass
            conn.commit()
        except Exception as ex:
            print(f'[PERFIL] _migrar_campos_perfil {_db}: {ex}')
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


def _migrar_farmacia_razao_social():
    """Adiciona razao_social em farmacias (nome fantasia fica em nome)."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(farmacias)").fetchall()]
            if "razao_social" not in cols:
                conn.execute("ALTER TABLE farmacias ADD COLUMN razao_social TEXT")
                print("[MODEL] coluna razao_social adicionada em farmacias")
    except Exception as ex:
        print(f"[MODEL] _migrar_farmacia_razao_social: {ex}")


def _migrar_medico_endereco_clinica():
    """Adiciona endereco_json, clinica_id e clinica_nome em medicos."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(medicos)").fetchall()]
            if "endereco_json" not in cols:
                conn.execute("ALTER TABLE medicos ADD COLUMN endereco_json TEXT")
                print("[MODEL] coluna endereco_json adicionada em medicos")
            if "clinica_id" not in cols:
                conn.execute("ALTER TABLE medicos ADD COLUMN clinica_id INTEGER REFERENCES clinicas(id)")
                print("[MODEL] coluna clinica_id adicionada em medicos")
            if "clinica_nome" not in cols:
                conn.execute("ALTER TABLE medicos ADD COLUMN clinica_nome TEXT")
                print("[MODEL] coluna clinica_nome adicionada em medicos")
    except Exception as ex:
        print(f"[MODEL] _migrar_medico_endereco_clinica: {ex}")


def _criar_tabelas_compras():
    """Cria tabelas compras (cabeçalho NF) e compra_itens (remédios da nota)."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compras (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    farmacia_id     INTEGER REFERENCES farmacias(id),
                    data            TEXT NOT NULL,
                    total           REAL DEFAULT 0,
                    foto_path       TEXT,
                    foto_drive_id   TEXT,
                    qr_nfe          TEXT,
                    observacoes     TEXT,
                    status          TEXT DEFAULT 'ativa',
                    criado_em       TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compra_itens (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    compra_id           INTEGER NOT NULL REFERENCES compras(id) ON DELETE CASCADE,
                    remedio_id          INTEGER REFERENCES remedios(id),
                    nome_nf             TEXT NOT NULL,
                    dosagem             TEXT,
                    quantidade_emb      INTEGER DEFAULT 1,
                    comprimidos_emb     INTEGER,
                    preco_unitario      REAL DEFAULT 0,
                    preco_total         REAL DEFAULT 0,
                    quantidade_devolvida INTEGER DEFAULT 0,
                    criado_em           TEXT DEFAULT (datetime('now'))
                )
            """)
            # Migration para compras já existentes
            cols = [r[1] for r in conn.execute("PRAGMA table_info(compras)").fetchall()]
            if "status" not in cols:
                conn.execute("ALTER TABLE compras ADD COLUMN status TEXT DEFAULT 'ativa'")
            cols_i = [r[1] for r in conn.execute("PRAGMA table_info(compra_itens)").fetchall()]
            if "quantidade_devolvida" not in cols_i:
                conn.execute("ALTER TABLE compra_itens ADD COLUMN quantidade_devolvida INTEGER DEFAULT 0")
    except Exception as ex:
        print(f"[MODEL] _criar_tabelas_compras: {ex}")


def _migrar_mov_foto_nf():
    """Adiciona colunas foto_nf_path, foto_nf_drive_id e qr_nfe em remedios_mov."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(remedios_mov)").fetchall()]
            if "foto_nf_path" not in cols:
                conn.execute("ALTER TABLE remedios_mov ADD COLUMN foto_nf_path TEXT")
                print("[MODEL] coluna foto_nf_path adicionada em remedios_mov")
            if "foto_nf_drive_id" not in cols:
                conn.execute("ALTER TABLE remedios_mov ADD COLUMN foto_nf_drive_id TEXT")
                print("[MODEL] coluna foto_nf_drive_id adicionada em remedios_mov")
            if "qr_nfe" not in cols:
                conn.execute("ALTER TABLE remedios_mov ADD COLUMN qr_nfe TEXT")
                print("[MODEL] coluna qr_nfe adicionada em remedios_mov")
    except Exception as ex:
        print(f"[MODEL] _migrar_mov_foto_nf: {ex}")


def _renomear_receitas_para_laudos():
    """Garante que receitas (laudos) vira receitas_laudos e receitas (culinaria) tem schema correto."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if "receitas" in tables:
                cols = [r[1] for r in conn.execute("PRAGMA table_info(receitas)").fetchall()]
                if "consulta_id" in cols:
                    # schema antigo de laudos — mover para receitas_laudos
                    if "receitas_laudos" not in tables:
                        conn.execute("ALTER TABLE receitas RENAME TO receitas_laudos")
                        print("[MODEL] receitas renomeada para receitas_laudos")
                    else:
                        # receitas_laudos ja existe — copiar dados novos e dropar
                        ids_existentes = {r[0] for r in conn.execute(
                            "SELECT id FROM receitas_laudos").fetchall()}
                        for row in conn.execute(
                            "SELECT id,consulta_id,medico_id,drive_file_id,nome_arquivo,"
                            "data,observacoes,criado_em,foto_path FROM receitas").fetchall():
                            if row[0] not in ids_existentes:
                                conn.execute(
                                    "INSERT INTO receitas_laudos VALUES (?,?,?,?,?,?,?,?,?)", row)
                        conn.execute("DROP TABLE receitas")
                        print("[MODEL] receitas (laudos) mesclada em receitas_laudos e dropada")
    except Exception as ex:
        print(f"[MODEL] _renomear_receitas_para_laudos: {ex}")


def _migrar_receita_foto_path():
    """Adiciona coluna foto_path em receitas_laudos para caminho local da imagem."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(receitas_laudos)").fetchall()]
            if "foto_path" not in cols:
                conn.execute("ALTER TABLE receitas_laudos ADD COLUMN foto_path TEXT")
                print("[MODEL] coluna foto_path adicionada em receitas_laudos")
    except Exception as ex:
        print(f"[MODEL] _migrar_receita_foto_path: {ex}")


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


def _migrar_exames_internacao_id():
    """Adiciona internacao_id em exames para vincular exames realizados durante internacao."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(exames)").fetchall()]
            if "internacao_id" not in cols:
                conn.execute(
                    "ALTER TABLE exames ADD COLUMN internacao_id INTEGER REFERENCES internacoes(id)")
                print("[MODEL] coluna internacao_id adicionada em exames")
    except Exception as ex:
        print(f"[MODEL] _migrar_exames_internacao_id: {ex}")


def _migrar_fonte_dados():
    """Adiciona fonte_dados em internacoes para rastreabilidade (importado|manual)."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(internacoes)").fetchall()]
            if "fonte_dados" not in cols:
                conn.execute(
                    "ALTER TABLE internacoes ADD COLUMN fonte_dados TEXT DEFAULT 'importado'")
                print("[MODEL] coluna fonte_dados adicionada em internacoes")
    except Exception as ex:
        print(f"[MODEL] _migrar_fonte_dados: {ex}")


def _migrar_internacoes_gatilho():
    """Adiciona campo gatilho em internacoes para categorizar causa do evento."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(internacoes)").fetchall()]
            if "gatilho" not in cols:
                conn.execute(
                    "ALTER TABLE internacoes ADD COLUMN gatilho TEXT")
                print("[MODEL] coluna gatilho adicionada em internacoes")
    except Exception as ex:
        print(f"[MODEL] _migrar_internacoes_gatilho: {ex}")


def _migrar_internacoes_modalidade():
    """Adiciona campo modalidade em internacoes: ps | internacao | ps_internacao."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(internacoes)").fetchall()]
            if "modalidade" not in cols:
                conn.execute(
                    "ALTER TABLE internacoes ADD COLUMN modalidade TEXT DEFAULT 'internacao'")
                print("[MODEL] coluna modalidade adicionada em internacoes")
    except Exception as ex:
        print(f"[MODEL] _migrar_internacoes_modalidade: {ex}")


def _migrar_marcadores_internacao_id():
    """Adiciona internacao_id em marcadores_leituras para vincular leituras a internacoes."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute(
                "PRAGMA table_info(marcadores_leituras)").fetchall()]
            if "internacao_id" not in cols:
                conn.execute(
                    "ALTER TABLE marcadores_leituras "
                    "ADD COLUMN internacao_id INTEGER REFERENCES internacoes(id)")
                print("[MODEL] coluna internacao_id adicionada em marcadores_leituras")
    except Exception as ex:
        print(f"[MODEL] _migrar_marcadores_internacao_id: {ex}")


def _migrar_diagnosticos_internacao():
    """Popula diagnosticos_internacao com dados existentes em internacoes (migracao unica)."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            rows = conn.execute(
                "SELECT id, cid_entrada, motivo, cid_saida, diagnostico_saida FROM internacoes"
            ).fetchall()
            for iid, cid_ent, motivo, cid_sai, diag_sai in rows:
                count = conn.execute(
                    "SELECT COUNT(*) FROM diagnosticos_internacao WHERE internacao_id=?",
                    (iid,)
                ).fetchone()[0]
                if count > 0:
                    continue
                if cid_ent or motivo:
                    conn.execute(
                        "INSERT INTO diagnosticos_internacao "
                        "(internacao_id, cid, descricao, tipo, certeza, fonte) VALUES (?,?,?,?,?,?)",
                        (iid, cid_ent or None, motivo or None,
                         "entrada", "confirmado", "importado")
                    )
                if cid_sai or diag_sai:
                    conn.execute(
                        "INSERT INTO diagnosticos_internacao "
                        "(internacao_id, cid, descricao, tipo, certeza, fonte) VALUES (?,?,?,?,?,?)",
                        (iid, cid_sai or None, diag_sai or None,
                         "saida", "confirmado", "importado")
                    )
    except Exception as ex:
        print(f"[MODEL] _migrar_diagnosticos_internacao: {ex}")


def _migrar_diagnosticos_especialidade():
    """Adiciona colunas especialidade e refinado em diagnosticos_internacao."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute(
                "PRAGMA table_info(diagnosticos_internacao)").fetchall()]
            if "especialidade" not in cols:
                conn.execute(
                    "ALTER TABLE diagnosticos_internacao ADD COLUMN especialidade TEXT")
                print("[MODEL] coluna especialidade adicionada em diagnosticos_internacao")
            if "refinado" not in cols:
                conn.execute(
                    "ALTER TABLE diagnosticos_internacao ADD COLUMN refinado INTEGER DEFAULT 0")
                print("[MODEL] coluna refinado adicionada em diagnosticos_internacao")
    except Exception as ex:
        print(f"[MODEL] _migrar_diagnosticos_especialidade: {ex}")


def _migrar_pdf_paginas():
    """Cria tabela pdf_paginas e importacoes_pdf; adiciona colunas novas se necessario."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            # tabela de controle de importacoes (uma row por PDF importado)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS importacoes_pdf (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    arquivo_local   TEXT NOT NULL,   -- caminho completo do PDF original
                    nome_arquivo    TEXT,            -- nome base para exibicao
                    hash_pdf        TEXT,            -- SHA1 do arquivo para detectar duplicatas
                    fase_atual      INTEGER DEFAULT 0,
                    -- 0=registrado  1=separado(local)  2=drive_ok  3=classificado  4=concluido
                    total_paginas   INTEGER DEFAULT 0,
                    internacao_ids  TEXT,            -- JSON array de internacao_ids vinculados
                    criado_em       TEXT DEFAULT (datetime('now')),
                    atualizado_em   TEXT DEFAULT (datetime('now'))
                )
            """)
            # tabela de paginas
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pdf_paginas (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    importacao_id   INTEGER REFERENCES importacoes_pdf(id),
                    internacao_id   INTEGER REFERENCES internacoes(id),
                    pdf_origem      TEXT,
                    pagina_num      INTEGER,
                    jpeg_local      TEXT,            -- caminho local do JPEG (fase 1)
                    pdf_local       TEXT,            -- caminho local do PDF da pagina (fase 1)
                    drive_img_id    TEXT,            -- ID do JPEG no Drive (fase 2)
                    drive_pdf_id    TEXT,            -- ID do PDF no Drive (fase 2)
                    tipo            TEXT,            -- classificacao Claude
                    grupo           TEXT,            -- A | B | C
                    dados_json      TEXT,            -- JSON extraido pelo Claude
                    status          TEXT DEFAULT 'pendente_local',
                    -- pendente_local | pendente_drive | classificado | gravado | descartado
                    exame_id        INTEGER,
                    dado_bruto_id   INTEGER,
                    criado_em       TEXT DEFAULT (datetime('now'))
                )
            """)
            # adicionar colunas novas em pdf_paginas se banco antigo
            _cols_pag = [r[1] for r in conn.execute("PRAGMA table_info(pdf_paginas)").fetchall()]
            for col, dfn in [
                ("importacao_id", "INTEGER"),
                ("jpeg_local",    "TEXT"),
                ("pdf_local",     "TEXT"),
            ]:
                if col not in _cols_pag:
                    conn.execute(f"ALTER TABLE pdf_paginas ADD COLUMN {col} {dfn}")
            # migrar status antigo 'pendente' -> 'pendente_local' se houver
            conn.execute(
                "UPDATE pdf_paginas SET status='pendente_local' WHERE status='pendente'"
            )
    except Exception as ex:
        print(f"[MODEL] _migrar_pdf_paginas: {ex}")


def _criar_periodos_uso_remedio():
    """Cria tabela periodos_uso_remedio — histórico de períodos de uso por remédio."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS periodos_uso_remedio (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    remedio_id    INTEGER NOT NULL REFERENCES remedios(id) ON DELETE CASCADE,
                    receita_id    INTEGER REFERENCES receitas_laudos(id),
                    data_inicio   TEXT NOT NULL,
                    data_fim      TEXT,
                    ativo         INTEGER DEFAULT 1,
                    motivo_fim    TEXT,
                    observacoes   TEXT,
                    criado_em     TEXT DEFAULT (datetime('now','localtime'))
                )
            """)
            # Índices para busca rápida
            conn.execute("CREATE INDEX IF NOT EXISTS idx_periodo_remedio ON periodos_uso_remedio(remedio_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_periodo_ativo   ON periodos_uso_remedio(remedio_id, ativo)")
    except Exception as ex:
        print(f"[MODEL] _criar_periodos_uso_remedio: {ex}")


def iniciar_periodo_uso(remedio_id: int, data_inicio: str, receita_id: int = None, observacoes: str = None) -> int:
    """Inicia novo período de uso para um remédio. Encerra período ativo anterior se existir."""
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        # Encerra período ativo anterior sem data_fim
        conn.execute("""
            UPDATE periodos_uso_remedio SET ativo=0, data_fim=?
            WHERE remedio_id=? AND ativo=1 AND data_fim IS NULL
        """, (data_inicio, remedio_id))
        cur = conn.execute("""
            INSERT INTO periodos_uso_remedio (remedio_id, receita_id, data_inicio, ativo, observacoes)
            VALUES (?, ?, ?, 1, ?)
        """, (remedio_id, receita_id, data_inicio, observacoes))
        return cur.lastrowid


def encerrar_periodo_uso(remedio_id: int, data_fim: str, motivo: str = None) -> bool:
    """Encerra o período de uso ativo de um remédio (suspensão ou alta)."""
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        cur = conn.execute("""
            UPDATE periodos_uso_remedio
            SET ativo=0, data_fim=?, motivo_fim=?
            WHERE remedio_id=? AND ativo=1
        """, (data_fim, motivo, remedio_id))
        return cur.rowcount > 0


def listar_periodos_uso(remedio_id: int) -> list:
    """Retorna todos os períodos de uso de um remédio, mais recente primeiro."""
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT p.*, r.data as receita_data, r.observacoes as receita_obs,
                   r.foto_path as receita_foto,
                   m.nome as medico_nome
            FROM periodos_uso_remedio p
            LEFT JOIN receitas_laudos r ON r.id = p.receita_id
            LEFT JOIN medicos m  ON m.id = (SELECT medico_id FROM receitas_laudos WHERE id=p.receita_id)
            WHERE p.remedio_id = ?
            ORDER BY p.data_inicio DESC
        """, (remedio_id,)).fetchall()
        resultado = []
        hoje = __import__("datetime").date.today().isoformat()
        for r in rows:
            d = dict(r)
            # Calcular dias de uso
            try:
                import datetime as _dt
                ini = _dt.date.fromisoformat(d["data_inicio"])
                fim = _dt.date.fromisoformat(d["data_fim"]) if d["data_fim"] else _dt.date.today()
                d["dias_uso"] = (fim - ini).days
            except Exception:
                d["dias_uso"] = 0
            resultado.append(d)
        return resultado


def total_dias_uso(remedio_id: int) -> int:
    """Soma todos os dias de uso em todos os períodos de um remédio."""
    periodos = listar_periodos_uso(remedio_id)
    return sum(p["dias_uso"] for p in periodos)


def vincular_receita_remedio(receita_id: int, remedio_id: int, data_inicio: str) -> None:
    """Associa uma receita a um remédio e inicia novo período de uso."""
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        conn.execute("UPDATE remedios SET receita_id=? WHERE id=?", (receita_id, remedio_id))
    iniciar_periodo_uso(remedio_id, data_inicio, receita_id=receita_id)


def _migrar_linha_do_tempo():
    """Cria tabela linha_do_tempo — uma linha por data encontrada em uma importacao."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS linha_do_tempo (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    importacao_id  INTEGER REFERENCES importacoes_pdf(id),
                    data_doc       TEXT NOT NULL,        -- YYYY-MM-DD extraida das paginas
                    pasta_local    TEXT,                 -- caminho temp/ingestao/{id}/{data}/
                    total_paginas  INTEGER DEFAULT 0,
                    internacao_id  INTEGER REFERENCES internacoes(id),  -- vinculo apos fase 4
                    criado_em      TEXT DEFAULT (datetime('now'))
                )
            """)
    except Exception as ex:
        print(f"[MODEL] _migrar_linha_do_tempo: {ex}")


def _migrar_prontuarios():
    """
    Cria tabelas prontuarios (pai) e prontuario_paginas (filho).

    prontuarios      — um registro por PDF importado; dados gerais do documento.
    prontuario_paginas — uma linha por pagina; data extraida + caminho do PDF da pagina.
    """
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prontuarios (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    importacao_id   INTEGER REFERENCES importacoes_pdf(id),
                    nome_arquivo    TEXT,            -- nome exibido ao usuario
                    hash_pdf        TEXT,            -- SHA1 para detectar duplicatas
                    total_paginas   INTEGER DEFAULT 0,
                    data_inicio     TEXT,            -- menor data encontrada nas paginas
                    data_fim        TEXT,            -- maior data encontrada nas paginas
                    hospital        TEXT,            -- nome do hospital/clinica extraido das paginas
                    plano           TEXT,            -- nome do plano de saude extraido das paginas
                    criado_em       TEXT DEFAULT (datetime('now'))
                )
            """)
            # adicionar colunas em bancos antigos que ja tem a tabela
            _cols = [r[1] for r in conn.execute("PRAGMA table_info(prontuarios)").fetchall()]
            for col, dfn in [("hospital", "TEXT"), ("plano", "TEXT")]:
                if col not in _cols:
                    conn.execute(f"ALTER TABLE prontuarios ADD COLUMN {col} {dfn}")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prontuario_paginas (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    prontuario_id   INTEGER NOT NULL REFERENCES prontuarios(id),
                    pdf_pagina_id   INTEGER REFERENCES pdf_paginas(id),
                    pagina_num      INTEGER,
                    data_pagina     TEXT,            -- YYYY-MM-DD extraida pelo Claude
                    resumo          TEXT,            -- identificacao curta do conteudo
                    dados_json      TEXT,            -- JSON completo retornado pelo Claude
                    ignorado        INTEGER DEFAULT 0, -- 1 = pagina ignorada nas proximas fases
                    pdf_local       TEXT,            -- caminho local do PDF desta pagina
                    jpeg_local      TEXT,            -- caminho local do JPEG desta pagina
                    criado_em       TEXT DEFAULT (datetime('now'))
                )
            """)
            # adicionar colunas em bancos antigos
            _cols_pp = [r[1] for r in conn.execute("PRAGMA table_info(prontuario_paginas)").fetchall()]
            if "resumo" not in _cols_pp:
                conn.execute("ALTER TABLE prontuario_paginas ADD COLUMN resumo TEXT")
            if "dados_json" not in _cols_pp:
                conn.execute("ALTER TABLE prontuario_paginas ADD COLUMN dados_json TEXT")
            if "ignorado" not in _cols_pp:
                conn.execute("ALTER TABLE prontuario_paginas ADD COLUMN ignorado INTEGER DEFAULT 0")
            if "status" not in _cols_pp:
                conn.execute("ALTER TABLE prontuario_paginas ADD COLUMN status TEXT DEFAULT 'pendente'")
                # retroativamente: paginas com data → ok, ignorado=1 → ignorado
                conn.execute(
                    "UPDATE prontuario_paginas SET status='ok' "
                    "WHERE data_pagina IS NOT NULL AND (ignorado IS NULL OR ignorado=0)")
                conn.execute(
                    "UPDATE prontuario_paginas SET status='ignorado' WHERE ignorado=1")
                print("[MODEL] coluna status adicionada em prontuario_paginas")
            if "jpeg_drive_id" not in _cols_pp:
                conn.execute("ALTER TABLE prontuario_paginas ADD COLUMN jpeg_drive_id TEXT")
                print("[MODEL] coluna jpeg_drive_id adicionada em prontuario_paginas")
            if "internacao_id" not in _cols_pp:
                conn.execute(
                    "ALTER TABLE prontuario_paginas ADD COLUMN internacao_id INTEGER REFERENCES internacoes(id)")
                print("[MODEL] coluna internacao_id adicionada em prontuario_paginas")
            # sempre: marcar documentos administrativos como ignorado se ainda nao estiverem
            n = conn.execute("""
                UPDATE prontuario_paginas
                SET ignorado=1, status='ignorado'
                WHERE ignorado=0
                  AND resumo IS NOT NULL
                  AND lower(resumo) LIKE '%administrativo%'
            """).rowcount
            if n:
                print(f"[MODEL] {n} pagina(s) administrativa(s) marcadas como ignorado")
    except Exception as ex:
        print(f"[MODEL] _migrar_prontuarios: {ex}")


def _migrar_internacoes_medico_responsavel():
    """Adiciona coluna medico_responsavel em internacoes (nome livre, vindo da ficha de admissao)."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute("ALTER TABLE internacoes ADD COLUMN medico_responsavel TEXT")
    except Exception:
        pass  # coluna já existe


def _migrar_registros_clinicos():
    """Cria tabela registros_clinicos — evolucoes e prescricoes estruturadas por internacao."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS registros_clinicos (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    internacao_id   INTEGER REFERENCES internacoes(id),
                    tipo            TEXT NOT NULL,   -- prescricao_enfermagem | evolucao_medica | ...
                    data_registro   TEXT,
                    hora_registro   TEXT,
                    profissional    TEXT,
                    quadro_clinico  TEXT,
                    observacoes     TEXT,
                    intercorrencias TEXT,
                    dispositivos    TEXT,            -- JSON array
                    sinais_vitais   TEXT,            -- JSON dict {pa, fc, temp, spo2, glasgow}
                    dados_extras    TEXT,            -- JSON com campos adicionais do tipo
                    pdf_pagina_id   INTEGER REFERENCES pdf_paginas(id),
                    criado_em       TEXT DEFAULT (datetime('now'))
                )
            """)
    except Exception as ex:
        print(f"[MODEL] _migrar_registros_clinicos: {ex}")


def _migrar_sinais_internacao():
    """Cria tabela sinais_internacao em bancos antigos que nao a tem."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sinais_internacao (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    internacao_id   INTEGER REFERENCES internacoes(id),
                    sinal           TEXT NOT NULL,
                    momento         TEXT DEFAULT 'entrada',
                    valor           TEXT,
                    unidade         TEXT,
                    interpretacao   TEXT,
                    fonte           TEXT DEFAULT 'manual',
                    criado_em       TEXT DEFAULT (datetime('now'))
                )
            """)
    except Exception as ex:
        print(f"[MODEL] _migrar_sinais_internacao: {ex}")


def listar_sinais_internacao(internacao_id: int) -> list[dict]:
    """Retorna sinais clinicos de uma internacao, ordenados por sinal e momento."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            rows = conn.execute("""
                SELECT id, internacao_id, sinal, momento, valor, unidade, interpretacao, fonte, criado_em
                FROM sinais_internacao
                WHERE internacao_id = ?
                ORDER BY sinal ASC, momento ASC
            """, (internacao_id,)).fetchall()
        cols = ["id","internacao_id","sinal","momento","valor","unidade","interpretacao","fonte","criado_em"]
        return [dict(zip(cols, r)) for r in rows]
    except Exception as ex:
        print(f"[MODEL] listar_sinais_internacao: {ex}")
        return []


def salvar_sinal_internacao(dados: dict) -> int:
    """Cria ou atualiza um sinal clinico. Retorna id."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            sid = dados.get("id")
            if sid:
                conn.execute("""
                    UPDATE sinais_internacao
                    SET sinal=?, momento=?, valor=?, unidade=?, interpretacao=?, fonte=?
                    WHERE id=?
                """, (
                    dados.get("sinal"), dados.get("momento","entrada"),
                    dados.get("valor"), dados.get("unidade"),
                    dados.get("interpretacao"), dados.get("fonte","manual"),
                    sid,
                ))
                return sid
            cur = conn.execute("""
                INSERT INTO sinais_internacao
                  (internacao_id, sinal, momento, valor, unidade, interpretacao, fonte)
                VALUES (?,?,?,?,?,?,?)
            """, (
                dados["internacao_id"], dados["sinal"],
                dados.get("momento","entrada"), dados.get("valor"),
                dados.get("unidade"), dados.get("interpretacao"),
                dados.get("fonte","manual"),
            ))
            return cur.lastrowid
    except Exception as ex:
        print(f"[MODEL] salvar_sinal_internacao: {ex}")
        return 0


def excluir_sinal_internacao(sinal_id: int) -> bool:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("DELETE FROM sinais_internacao WHERE id=?", (sinal_id,))
        return True
    except Exception as ex:
        print(f"[MODEL] excluir_sinal_internacao: {ex}")
        return False


def _migrar_remedios_internacao_id():
    """Adiciona internacao_id em remedios para vincular medicamentos de internacao."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(remedios)").fetchall()]
            if "internacao_id" not in cols:
                conn.execute(
                    "ALTER TABLE remedios ADD COLUMN internacao_id INTEGER REFERENCES internacoes(id)")
                print("[MODEL] coluna internacao_id adicionada em remedios")
    except Exception as ex:
        print(f"[MODEL] _migrar_remedios_internacao_id: {ex}")


def _migrar_internacoes_documento():
    """Adiciona campos de localizacao, objetivo e drive em internacoes."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(internacoes)").fetchall()]
            novos = [
                ("documento_local", "TEXT"),
                ("cidade",          "TEXT"),
                ("uf",              "TEXT"),
                ("objetivo",        "TEXT DEFAULT 'tratamento'"),
                ("drive_file_id",   "TEXT"),
                ("drive_link",      "TEXT"),
            ]
            for col, tipo in novos:
                if col not in cols:
                    conn.execute(f"ALTER TABLE internacoes ADD COLUMN {col} {tipo}")
                    print(f"[MODEL] coluna {col} adicionada em internacoes")
    except Exception as ex:
        print(f"[MODEL] _migrar_internacoes_documento: {ex}")


def _migrar_datas_iso():
    """Converte datas em formato DD/MM/YYYY para YYYY-MM-DD em todas as tabelas."""
    tabelas_campos = [
        ("consultas",          ["data"]),
        ("receitas_laudos",    ["data"]),
        ("remedios",           ["data_inicio", "data_fim"]),
        ("internacoes",        ["data_entrada", "data_saida"]),
        ("exames",             ["data_exame"]),
        ("marcadores_leituras", ["data_medicao"]),
    ]
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            total = 0
            for tabela, campos in tabelas_campos:
                for campo in campos:
                    try:
                        rows = conn.execute(
                            f"SELECT id, {campo} FROM {tabela} "
                            f"WHERE {campo} LIKE '__/__/____'").fetchall()
                        for row_id, val in rows:
                            if not val:
                                continue
                            try:
                                novo = _datetime.datetime.strptime(
                                    val[:10], "%d/%m/%Y").strftime("%Y-%m-%d")
                                conn.execute(
                                    f"UPDATE {tabela} SET {campo}=? WHERE id=?",
                                    (novo, row_id))
                                total += 1
                            except Exception:
                                pass
                    except Exception:
                        pass
            if total:
                print(f"[MODEL] _migrar_datas_iso: {total} datas convertidas para ISO")
    except Exception as ex:
        print(f"[MODEL] _migrar_datas_iso: {ex}")


def _migrar_exame_anexos_imagens():
    """Adiciona arquivo_local e pendente_sync em exame_anexos para sync Drive de imagens."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(exame_anexos)").fetchall()]
            if "arquivo_local" not in cols:
                conn.execute("ALTER TABLE exame_anexos ADD COLUMN arquivo_local TEXT")
                print("[MODEL] coluna arquivo_local adicionada em exame_anexos")
            if "pendente_sync" not in cols:
                conn.execute(
                    "ALTER TABLE exame_anexos ADD COLUMN pendente_sync INTEGER DEFAULT 0"
                )
                print("[MODEL] coluna pendente_sync adicionada em exame_anexos")
    except Exception as ex:
        print(f"[MODEL] _migrar_exame_anexos_imagens: {ex}")


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
                    tipo      TEXT DEFAULT 'alimentacao',
                    horario   TEXT,
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
                    quantidade TEXT,
                    unidade    TEXT DEFAULT 'Unidade',
                    detalhe    TEXT,
                    horario    TEXT,
                    frequencia TEXT DEFAULT 'diario',
                    calorias   REAL,
                    proteinas  REAL,
                    vitaminas  TEXT,
                    remedio_id INTEGER REFERENCES remedios(id),
                    ordem      INTEGER DEFAULT 0,
                    criado_em  TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS receitas (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome         TEXT NOT NULL,
                    descricao    TEXT,
                    modo_preparo TEXT,
                    rendimento_qtd  TEXT,
                    rendimento_unid TEXT DEFAULT 'Porcao',
                    calorias_total  REAL,
                    proteinas_total REAL,
                    vitaminas       TEXT,
                    ativo        INTEGER DEFAULT 1,
                    criado_em    TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS receita_ingredientes (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    receita_id     INTEGER NOT NULL REFERENCES receitas(id) ON DELETE CASCADE,
                    tipo           TEXT NOT NULL DEFAULT 'item',
                    descricao      TEXT,
                    sub_receita_id INTEGER REFERENCES receitas(id),
                    quantidade     TEXT,
                    unidade        TEXT DEFAULT 'Unidade',
                    calorias       REAL,
                    proteinas      REAL,
                    ordem          INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS item_ingredientes (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id        INTEGER NOT NULL REFERENCES itens_momento(id) ON DELETE CASCADE,
                    tipo           TEXT NOT NULL DEFAULT 'item',
                    descricao      TEXT,
                    sub_receita_id INTEGER REFERENCES receitas(id),
                    quantidade     TEXT,
                    unidade        TEXT DEFAULT 'Unidade',
                    calorias       REAL,
                    proteinas      REAL,
                    ordem          INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS rotina_diario (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    data        TEXT NOT NULL,
                    item_id     INTEGER REFERENCES itens_momento(id) ON DELETE SET NULL,
                    item_nome   TEXT,
                    tipo        TEXT NOT NULL,
                    descricao   TEXT NOT NULL,
                    motivo      TEXT,
                    data_fim    TEXT,
                    criado_em   TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_rotina_diario_data
                    ON rotina_diario(data DESC);
            """)
        # Migrações para bancos antigos
        for sql in [
            "ALTER TABLE rotinas_templates ADD COLUMN tipo               TEXT DEFAULT 'alimentacao'",
            "ALTER TABLE rotinas_templates ADD COLUMN horario            TEXT",
            "ALTER TABLE rotinas_templates ADD COLUMN hora_inicio        TEXT",
            "ALTER TABLE rotinas_templates ADD COLUMN hora_fim           TEXT",
            "ALTER TABLE rotinas_templates ADD COLUMN intensidade_fisica TEXT",
            "ALTER TABLE rotinas_templates ADD COLUMN intensidade_mental TEXT",
            "ALTER TABLE itens_momento     ADD COLUMN frequencia          TEXT DEFAULT 'diario'",
            "ALTER TABLE itens_momento     ADD COLUMN quantidade          TEXT",
            "ALTER TABLE itens_momento     ADD COLUMN unidade             TEXT DEFAULT 'Unidade'",
            "ALTER TABLE itens_momento     ADD COLUMN calorias            REAL",
            "ALTER TABLE itens_momento     ADD COLUMN proteinas           REAL",
            "ALTER TABLE itens_momento     ADD COLUMN vitaminas           TEXT",
            "ALTER TABLE itens_momento     ADD COLUMN hora_inicio         TEXT",
            "ALTER TABLE itens_momento     ADD COLUMN hora_fim            TEXT",
            "ALTER TABLE itens_momento     ADD COLUMN intensidade_fisica  TEXT",
            "ALTER TABLE itens_momento     ADD COLUMN intensidade_mental  TEXT",
        ]:
            try: conn.execute(sql)
            except Exception: pass
    except Exception as ex:
        print(f"[MODEL] _criar_rotinas: {ex}")


def _migrar_renomear_exame_resultados():
    """Renomeia resultados_estruturados para exame_resultados em bancos existentes."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            tabelas = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if 'resultados_estruturados' in tabelas and 'exame_resultados' not in tabelas:
                conn.execute('ALTER TABLE resultados_estruturados RENAME TO exame_resultados')
                print('[MODEL] tabela resultados_estruturados renomeada para exame_resultados')
    except Exception as ex:
        print(f'[MODEL] _migrar_renomear_exame_resultados: {ex}')


def _migrar_pai_id():
    """Adiciona pai_id em exame_resultados para sub-resultados (ex: eRFG filho de Creatinina)."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            cols = [r[1] for r in conn.execute('PRAGMA table_info(exame_resultados)').fetchall()]
            if 'pai_id' not in cols:
                conn.execute('ALTER TABLE exame_resultados ADD COLUMN pai_id INTEGER REFERENCES exame_resultados(id)')
                print('[MODEL] coluna pai_id adicionada em exame_resultados')
    except Exception as ex:
        print(f'[MODEL] _migrar_pai_id: {ex}')


def _migrar_sinonimos_exames_padrao():
    """
    Garante que exames_padrao com sinônimos incompletos sejam corrigidos.
    Roda no startup — idempotente: só atualiza se o sinônimo novo não constar.
    Também remove duplicatas ruins (ex: id=137 POTASSIO vs id=54 Potássio).
    """
    import json as _j
    _CORRECOES = [
        # (nome_oficial_canônico, sinônimos_completos, unidade, categoria)
        ("Potássio",
         ["POTASSIO", "POTÁSSIO", "K", "POTASSIO SERICO", "K+",
          "POTÁSSIO SÉRICO", "POTASSIO IONICO"],
         "mEq/L", "Minerais"),
        ("Sódio",
         ["SODIO", "SÓDIO", "NA", "SODIO SERICO", "NA+",
          "SÓDIO SÉRICO", "SODIO IONICO"],
         "mEq/L", "Minerais"),
        ("Magnésio",
         ["MAGNESIO", "MAGNÉSIO", "MG", "MAGNESIO SERICO",
          "MAGNÉSIO SÉRICO", "MG2+"],
         "mg/dL", "Minerais"),
        ("Cálcio",
         ["CALCIO", "CÁLCIO", "CALCIO TOTAL", "CALCIO SERICO",
          "CALCIO RESULTADO", "CÁlcio Total", "Cálcio Sérico Total (CaT)",
          "CA", "CA TOTAL"],
         "mg/dL", "Minerais"),
        ("Cálcio Ionizado (mmol/L)",
         ["CÁLCIO IÔNICO", "CALCIO IONICO", "CALCIO IONIZADO MMOL",
          "CÁlcio Ionizado (Ca++) (em mmol/L)", "CA IONICO", "CA++",
          "CÁLCIO IONIZADO MMOL/L", "CALCIO IONICO MMOL"],
         "mmol/L", "Minerais"),
        ("Cálcio Ionizado (mg/dL)",
         ["CALCIO IONIZADO", "CÁLCIO IONIZADO",
          "CÁlcio Ionizado (Ca++) (em mg/dL)", "CA IONIZADO MG"],
         "mg/dL", "Minerais"),
        ("Fósforo",
         ["FOSFORO", "FÓSFORO", "P", "FOSFORO SERICO", "FOSFATO",
          "FOSFORO INORGANICO", "FÓSFORO SÉRICO"],
         "mg/dL", "Minerais"),
        ("Cloro",
         ["CLORO", "CLORETO", "CL", "CL-", "CLORETOS"],
         "mEq/L", "Minerais"),
        # ── Hemograma ──────────────────────────────────────────────
        ("Hemoglobina",
         ["HEMOGLOBINA", "HB", "HGB", "HEMOGLOBINA TOTAL", "Hb", "Hgb"],
         "g/dL", "Hemograma"),
        ("Hematócrito",
         ["HEMATOCRITO", "HEMATÓCRITO", "HCT", "HT", "Hematocrito",
          "HEMATOCRITO %"],
         "%", "Hemograma"),
        ("Hemácias",
         ["HEMACIAS", "HEMÁCIAS", "ERITROCITOS", "ERITRÓCITOS",
          "GLOBULOS VERMELHOS", "RBC", "HEMACIAS MILHOES",
          "Eritrócitos", "Eritrocitos"],
         "milhões/mm³", "Hemograma"),
        ("Leucócitos",
         ["LEUCOCITOS", "LEUCÓCITOS", "GLOBULOS BRANCOS", "WBC",
          "CONTAGEM DE LEUCOCITOS", "LEUCOCITOS TOTAIS",
          "Leucócitos Totais", "Leucocitos Totais"],
         "/mm³", "Hemograma"),
        ("Plaquetas",
         ["PLAQUETAS", "TROMBOCITOS", "TROMBÓCITOS", "PLT",
          "CONTAGEM DE PLAQUETAS", "Plaquetas (PLT)"],
         "/mm³", "Hemograma"),
        ("VCM",
         ["VCM", "VOLUME CORPUSCULAR MEDIO", "VOLUME CORPUSCULAR MÉDIO",
          "MCV", "V.C.M", "V.C.M."],
         "fL", "Hemograma"),
        ("HCM",
         ["HCM", "HEMOGLOBINA CORPUSCULAR MEDIA", "HEMOGLOBINA CORPUSCULAR MÉDIA",
          "MCH", "H.C.M", "H.C.M."],
         "pg", "Hemograma"),
        ("CHCM",
         ["CHCM", "CONCENTRACAO DE HEMOGLOBINA CORPUSCULAR", "MCHC",
          "C.H.C.M", "C.H.C.M.", "CONCENTRAÇÃO HEMOGLOBINA CORPUSCULAR"],
         "g/dL", "Hemograma"),
        ("RDW",
         ["RDW", "INDICE DE ANISOCITOSE", "AMPLITUDE DE DISTRIBUICAO",
          "R.D.W", "R.D.W.", "R.D.W. (SD)", "RDW-CV", "RDW-SD"],
         "%", "Hemograma"),
        ("Neutrófilos",
         ["NEUTROFILOS", "NEUTRÓFILOS", "SEGMENTADOS", "NEUTROFILOS SEGMENTADOS",
          "NEUTROFILOS TOTAIS", "Neutrófilos Segmentados", "Neutrofilos",
          "GRAN", "Granulócitos"],
         "%", "Hemograma"),
        ("Linfócitos",
         ["LINFOCITOS", "LINFÓCITOS", "LYMPHOCYTES", "Linfócitos típicos",
          "LINFOCITOS TIPICOS", "Linfócitos Atípicos", "LINFOCITOS ATIPICOS"],
         "%", "Hemograma"),
        ("Monócitos",
         ["MONOCITOS", "MONÓCITOS", "MONOCYTES", "Monócitos"],
         "%", "Hemograma"),
        ("Eosinófilos",
         ["EOSINOFILOS", "EOSINÓFILOS", "EOSINOPHILS", "Eosinófilos"],
         "%", "Hemograma"),
        ("Basófilos",
         ["BASOFILOS", "BASÓFILOS", "BASOPHILS", "Basófilos"],
         "%", "Hemograma"),
        ("Neutrófilos Bastonetes",
         ["BASTONETES", "NEUTROFILOS BASTONETES", "NEUTRÓFILOS BASTONETES",
          "Bastões", "BASTOS", "BAND"],
         "%", "Hemograma"),
        ("Reticulócitos",
         ["RETICULOCITOS", "RETICULÓCITOS", "RETICULOCITOS %",
          "RETICULOS", "RET"],
         "%", "Hemograma"),
        ("MPV",
         ["MPV", "VOLUME PLAQUETARIO MEDIO", "M.P.V", "M.P.V.",
          "VOLUME MÉDIO DE PLAQUETAS"],
         "fL", "Hemograma"),
    ]
    _DUPLICATAS_REMOVER = [
        # IDs que são duplicatas ruins — migra resultados para o canônico e deleta
        # (id_ruim, nome_oficial_canonico)
        (137, "Potássio"),
        (139, "Fósforo"),
        (147, "Cálcio"),
        (136, "Hematócrito"),   # duplicata sem acento
    ]

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        cur  = conn.cursor()

        # 1. Corrigir sinônimos dos canônicos
        for nome, sinonimos, unidade, categoria in _CORRECOES:
            row = cur.execute(
                "SELECT id, sinonimos FROM exames_padrao WHERE nome_oficial=?", (nome,)
            ).fetchone()
            if not row:
                continue
            ep_id, sin_raw = row
            try:
                sin_atual = _j.loads(sin_raw) if sin_raw else []
            except Exception:
                sin_atual = [sin_raw] if sin_raw else []
            sin_set = set(s.upper() for s in sin_atual)
            novos = [s for s in sinonimos if s.upper() not in sin_set]
            if novos:
                sin_novo = sin_atual + novos
                cur.execute(
                    "UPDATE exames_padrao SET sinonimos=?, unidade=?, categoria=? WHERE id=?",
                    (_j.dumps(sin_novo, ensure_ascii=False), unidade, categoria, ep_id)
                )
                print(f"[MIGR] exames_padrao id={ep_id} ({nome}): +{len(novos)} sinônimos")

        # 2. Remover duplicatas — migrar resultados para o canônico primeiro
        for id_ruim, nome_canonico in _DUPLICATAS_REMOVER:
            row_ruim = cur.execute(
                "SELECT id FROM exames_padrao WHERE id=?", (id_ruim,)
            ).fetchone()
            if not row_ruim:
                continue
            row_can = cur.execute(
                "SELECT id FROM exames_padrao WHERE nome_oficial=?", (nome_canonico,)
            ).fetchone()
            if not row_can:
                continue
            id_can = row_can[0]
            if id_ruim == id_can:
                continue
            # migrar exame_resultados
            n = cur.execute(
                "UPDATE exame_resultados SET exame_padrao_id=? WHERE exame_padrao_id=?",
                (id_can, id_ruim)
            ).rowcount
            # migrar referencias_padrao
            cur.execute(
                "UPDATE referencias_padrao SET exame_padrao_id=? WHERE exame_padrao_id=?",
                (id_can, id_ruim)
            )
            cur.execute("DELETE FROM exames_padrao WHERE id=?", (id_ruim,))
            if n > 0:
                print(f"[MIGR] duplicata id={id_ruim} removida → canônico id={id_can} ({nome_canonico}), {n} resultado(s) migrado(s)")
            else:
                print(f"[MIGR] duplicata id={id_ruim} removida → canônico id={id_can} ({nome_canonico})")

        # 3. Reparar exame_resultados com exame_padrao_id=NULL
        #    Para cada linha sem padrao_id, tenta casar o parametro com os sinônimos atualizados
        rows_sem = cur.execute(
            "SELECT id, parametro FROM exame_resultados WHERE exame_padrao_id IS NULL"
        ).fetchall()
        if rows_sem:
            # Recarregar mapeamento sinonimo→id após as correções acima
            ep_rows = cur.execute(
                "SELECT id, nome_oficial, sinonimos FROM exames_padrao"
            ).fetchall()
            sin_map = {}  # sinonimo_upper → ep_id
            for ep_id, nome_of, sin_raw in ep_rows:
                sin_map[nome_of.upper()] = ep_id
                try:
                    sins = _j.loads(sin_raw) if sin_raw else []
                except Exception:
                    sins = [sin_raw] if sin_raw else []
                for s in sins:
                    sin_map[s.upper()] = ep_id
            consertados = 0
            for res_id, param in rows_sem:
                if not param:
                    continue
                ep_id_match = sin_map.get(param.upper())
                if ep_id_match:
                    cur.execute(
                        "UPDATE exame_resultados SET exame_padrao_id=? WHERE id=?",
                        (ep_id_match, res_id)
                    )
                    consertados += 1
            if consertados:
                print(f"[MIGR] {consertados} resultado(s) sem exame_padrao_id reparado(s)")

        conn.commit()
    except Exception as ex:
        print(f"[MIGR] _migrar_sinonimos_exames_padrao: {ex}")
    finally:
        if conn:
            conn.close()


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
        if 'fonte' not in cols_ref:
            cur.execute("ALTER TABLE referencias_padrao ADD COLUMN fonte TEXT")
            print('[REF] fonte adicionada em referencias_padrao')
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
    # isolation_level=None necessario para executescript funcionar corretamente
    conn_core = _orig_sqlite3_connect(CORE_DB, timeout=30, isolation_level=None)
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

        CREATE TABLE IF NOT EXISTS codigos_acesso_medico (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo      TEXT UNIQUE NOT NULL,
            nome_medico TEXT NOT NULL,
            criado_em   TEXT DEFAULT (datetime('now')),
            ativo       INTEGER DEFAULT 1
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
            grupo_id        INTEGER REFERENCES grupos_exame(id),
            importado_em    TEXT DEFAULT (datetime('now'))
        );

        -- ────────────────────────────────────────────────────────
        -- RESULTADOS NUMÉRICOS
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS exame_resultados (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            exame_id            INTEGER REFERENCES exames(id),
            pai_id              INTEGER REFERENCES exame_resultados(id),
            parametro           TEXT,
            valor               TEXT,
            unidade             TEXT,
            referencia          TEXT,
            exame_padrao_id     INTEGER REFERENCES exames_padrao(id),
            grupo_id            INTEGER REFERENCES grupos_exame(id),
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
        -- DIAGNÓSTICOS ESTRUTURADOS POR INTERNAÇÃO
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS diagnosticos_internacao (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            internacao_id   INTEGER REFERENCES internacoes(id),
            cid             TEXT,
            descricao       TEXT,
            tipo            TEXT DEFAULT 'saida',
            certeza         TEXT DEFAULT 'confirmado',
            fonte           TEXT DEFAULT 'manual',
            criado_em       TEXT DEFAULT (datetime('now'))
        );

        -- ────────────────────────────────────────────────────────
        -- DADOS BRUTOS / SEM CLASSIFICAÇÃO POR INTERNAÇÃO
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS internacao_dados_brutos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            internacao_id   INTEGER REFERENCES internacoes(id),
            categoria       TEXT DEFAULT 'outro',
            conteudo        TEXT,
            pagina_origem   INTEGER,
            fonte           TEXT DEFAULT 'importado',
            criado_em       TEXT DEFAULT (datetime('now'))
        );

        -- ────────────────────────────────────────────────────────
        -- SINAIS CLÍNICOS POR INTERNAÇÃO
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS sinais_internacao (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            internacao_id   INTEGER REFERENCES internacoes(id),
            sinal           TEXT NOT NULL,
            momento         TEXT DEFAULT 'entrada',  -- 'entrada' | 'saida' | 'evolucao'
            valor           TEXT,
            unidade         TEXT,
            interpretacao   TEXT,
            fonte           TEXT DEFAULT 'manual',   -- 'manual' | 'importado' | 'claude_refinado'
            criado_em       TEXT DEFAULT (datetime('now'))
        );

        -- ────────────────────────────────────────────────────────
        -- GRUPOS DE EXAMES
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS grupos_exame (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nome      TEXT UNIQUE NOT NULL,
            descricao TEXT,
            tipo      TEXT NOT NULL,  -- 'sangue' | 'imagem' | 'outros'
            icone     TEXT,
            ordem     INTEGER DEFAULT 0,
            ativo     INTEGER DEFAULT 1
        );

        -- ────────────────────────────────────────────────────────
        -- DICIONÁRIO PADRÃO
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS exames_padrao (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_oficial TEXT UNIQUE,
            sinonimos    TEXT,
            categoria    TEXT,
            subcategoria TEXT,
            tipo         TEXT DEFAULT 'numerico',
            unidade      TEXT,
            observacoes  TEXT,
            grupo_id     INTEGER REFERENCES grupos_exame(id),
            ativo        INTEGER DEFAULT 1,
            criado_em    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS referencias_padrao (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            exame_padrao_id INTEGER REFERENCES exames_padrao(id),
            sexo            TEXT,           -- 'M' | 'F' | NULL (ambos)
            idade_min       INTEGER,        -- anos (0 = neonato/lactente via obs)
            idade_max       INTEGER,        -- 999 = sem limite superior
            critico_baixo   REAL,           -- valor abaixo = risco de vida
            limite_baixo    REAL,           -- limite inferior do normal
            otimo_min       REAL,           -- início da faixa ideal
            otimo_max       REAL,           -- fim da faixa ideal
            limite_alto     REAL,           -- limite superior do normal
            critico_alto    REAL,           -- valor acima = risco de vida
            observacoes     TEXT,           -- ex: "Adulto", "Grávida", "RN"
            fonte           TEXT,           -- ex: "SBPC/ML 2023", "SBD 2024"
            criado_em       TEXT DEFAULT (datetime('now'))
        );

        -- ────────────────────────────────────────────────────────
        -- CONHECIMENTO DE EXAMES
        -- Tabela rica: o que o exame é, representa e indica
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS exame_conhecimento (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            exame_padrao_id     INTEGER UNIQUE REFERENCES exames_padrao(id) ON DELETE CASCADE,

            -- Identidade clínica
            o_que_mede          TEXT,   -- descrição do que o exame mede biologicamente
            marcadores          TEXT,   -- JSON array: ["diabetes","metabolismo glicídico"]
            sistema_orgao       TEXT,   -- ex: "Pâncreas / Metabolismo"

            -- Interpretação clínica
            alterado_alto       TEXT,   -- o que indica quando ALTO
            alterado_baixo      TEXT,   -- o que indica quando BAIXO
            faixa_alerta        TEXT,   -- zona de atenção antes do patológico

            -- Quem pede e por quê
            quem_solicita       TEXT,   -- "Clínico Geral, Endocrinologista"
            especialidades      TEXT,   -- JSON array de especialidades
            frequencia          TEXT,   -- 'rotina' | 'monitoramento' | 'investigacao' | 'urgencia'

            -- Contexto de uso
            indicacoes          TEXT,   -- quando é solicitado
            interferentes       TEXT,   -- o que interfere no resultado (medicamentos, alimentos)
            preparo_paciente    TEXT,   -- jejum, repouso, fase do ciclo, etc.
            curiosidade_clinica TEXT,   -- fato relevante para o paciente entender

            -- Metadados
            fonte               TEXT,   -- referência bibliográfica principal
            atualizado_em       TEXT DEFAULT (datetime('now'))
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
        CREATE TABLE IF NOT EXISTS receitas_laudos (
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
            receita_id      INTEGER REFERENCES receitas_laudos(id),
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

        CREATE TABLE IF NOT EXISTS remedios_mov (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            remedio_id      INTEGER NOT NULL,
            tipo            TEXT NOT NULL,
            -- tipos: 'compra' | 'inicio_uso' | 'tomada' | 'ajuste' | 'vencimento'
            data            TEXT NOT NULL,
            quantidade      INTEGER DEFAULT 0,
            -- positivo = entrada (compra), negativo = saida (tomada/ajuste)
            estoque_apos    INTEGER,
            preco_unitario  REAL,
            preco_total     REAL,
            farmacia_id     INTEGER,
            receita_id      INTEGER,
            consulta_id     INTEGER,
            origem          TEXT,
            -- 'receita' | 'manual' | 'automatico'
            observacoes     TEXT,
            criado_em       TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (remedio_id)  REFERENCES remedios(id) ON DELETE CASCADE,
            FOREIGN KEY (farmacia_id) REFERENCES farmacias(id),
            FOREIGN KEY (receita_id)  REFERENCES receitas(id),
            FOREIGN KEY (consulta_id) REFERENCES consultas(id)
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
        -- OBSERVACOES DO MEDICO (via hub_medico)
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS observacoes_medico (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            medico_id     INTEGER REFERENCES medicos(id),
            nome_medico   TEXT,
            data          TEXT,
            texto         TEXT NOT NULL,
            drive_file_id TEXT,
            nome_arquivo  TEXT,
            lida_paciente INTEGER DEFAULT 0,
            criado_em     TEXT DEFAULT (datetime('now'))
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

        -- HISTÓRICO MÉDICO PESSOAL (declarado pelo paciente)
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS historico_medico (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            data_aprox    TEXT,          -- YYYY, YYYY-MM ou YYYY-MM-DD
            tipo          TEXT NOT NULL, -- 'evento_cardiaco'|'cirurgia'|'internacao'|'diagnostico'|'procedimento'|'condicao_cronica'|'alergia'|'infancia'
            titulo        TEXT NOT NULL,
            descricao     TEXT,
            local         TEXT,          -- hospital / cidade
            medico        TEXT,
            sequela       TEXT,          -- consequências permanentes
            alerta        INTEGER DEFAULT 0,  -- 1 = mostrar no topo da ficha
            fonte         TEXT DEFAULT 'paciente',  -- 'paciente'|'documento'|'exame'
            internacao_id INTEGER REFERENCES internacoes(id),
            exame_id      INTEGER REFERENCES exames(id),
            criado_em     TEXT DEFAULT (datetime('now'))
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

        -- ────────────────────────────────────────────────────────
        -- DIAGNOSTICOS
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS diagnosticos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo          TEXT NOT NULL,
            cid             TEXT,
            descricao       TEXT,
            sistema         TEXT,
            data_diagnostico TEXT,
            data_resolucao  TEXT,
            status          TEXT DEFAULT 'ativo',
            certeza         TEXT DEFAULT 'confirmado',
            medico_id       INTEGER REFERENCES medicos(id),
            internacao_id   INTEGER REFERENCES internacoes(id),
            observacoes     TEXT,
            ativo           INTEGER DEFAULT 1,
            criado_em       TEXT DEFAULT (datetime('now')),
            atualizado_em   TEXT DEFAULT (datetime('now'))
        );

        -- tratamento por diagnostico (funciona para historico_medico e diagnosticos)
        CREATE TABLE IF NOT EXISTS diagnostico_tratamento (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            origem          TEXT NOT NULL,
            origem_id       INTEGER NOT NULL,
            medico_id       INTEGER REFERENCES medicos(id),
            observacoes     TEXT,
            data_revisao    TEXT,
            criado_em       TEXT DEFAULT (datetime('now')),
            atualizado_em   TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS diagnostico_tratamento_remedios (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tratamento_id   INTEGER NOT NULL REFERENCES diagnostico_tratamento(id),
            remedio_id      INTEGER NOT NULL REFERENCES remedios(id),
            dosagem         TEXT,
            frequencia      TEXT
        );

        -- ────────────────────────────────────────────────────────
        -- INTERNACOES
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS internacoes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital      TEXT NOT NULL,
            clinica_id    INTEGER REFERENCES clinicas(id),
            medico_id     INTEGER REFERENCES medicos(id),
            data_entrada  TEXT NOT NULL,
            data_saida    TEXT,
            tipo          TEXT DEFAULT 'eletiva',
            motivo        TEXT,
            cid_entrada   TEXT,
            diagnostico_saida TEXT,
            cid_saida     TEXT,
            observacoes   TEXT,
            documento_local TEXT,
            criado_em     TEXT DEFAULT (datetime('now'))
        );

        -- ────────────────────────────────────────────────────────
        -- PROCEDIMENTOS
        -- ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS procedimentos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            internacao_id INTEGER REFERENCES internacoes(id),
            medico_id     INTEGER REFERENCES medicos(id),
            nome          TEXT NOT NULL,
            tipo          TEXT DEFAULT 'cirurgico',
            data          TEXT NOT NULL,
            hora          TEXT,
            local         TEXT,
            anestesia     TEXT DEFAULT 'sem',
            cid           TEXT,
            resultado     TEXT,
            observacoes   TEXT,
            criado_em     TEXT DEFAULT (datetime('now'))
        );

    """)

        conn.commit()
    finally:
        conn.close()
    print("[OK] Tabelas MÓDULO criadas (prontuario.db)")
    _migrar_campos_perfil()
    _migrar_renomear_exame_resultados()
    _migrar_pai_id()
    _migrar_referencias_padrao()
    _migrar_sinonimos_exames_padrao()
    _migrar_medicos()
    _migrar_principio_ativo()
    _migrar_marcadores()
    _migrar_marcadores_contexto()
    _migrar_tipo_prescrito()
    _migrar_remedio_fotos()
    _migrar_farmacia_razao_social()
    _migrar_medico_endereco_clinica()
    _migrar_mov_foto_nf()
    _criar_tabelas_compras()
    _renomear_receitas_para_laudos()
    _criar_tabela_nutricao()
    _migrar_ingrediente_peso_unitario()
    _migrar_receitas_porcao()
    _migrar_receita_foto_path()
    _migrar_consulta_pauta()
    _migrar_compromisso()
    _criar_rotinas()
    _migrar_exame_anexos_imagens()
    _migrar_exames_internacao_id()
    _migrar_internacoes_documento()
    _migrar_datas_iso()
    _migrar_remedios_internacao_id()
    _migrar_fonte_dados()
    _migrar_internacoes_gatilho()
    _migrar_internacoes_modalidade()
    _migrar_marcadores_internacao_id()
    _migrar_diagnosticos_internacao()
    _migrar_diagnosticos_especialidade()
    _migrar_sinais_internacao()
    _migrar_pdf_paginas()
    _migrar_linha_do_tempo()
    _migrar_prontuarios()
    _migrar_internacoes_medico_responsavel()
    _migrar_registros_clinicos()
    _migrar_desafios()
    _criar_periodos_uso_remedio()
    # Registrar módulo no core
    try:
        _conn = sqlite3.connect(CORE_DB, timeout=30)
        _conn.execute("""INSERT OR IGNORE INTO modulos_instalados (nome, versao, db_arquivo)
                         VALUES ('prontuario', '1.0', 'prontuario.db')""")
        _conn.commit(); _conn.close()
    except Exception:
        pass
    # Popular base de exames padrão (179 exames com categorias e referências)
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
    # Seeds pesados — so rodam quando a versao do seed muda
    _SEED_VER = "seed_v3"
    try:
        import sqlite3 as _sq_seed
        with _sq_seed.connect(DB_PATH, timeout=10) as _cs:
            _cs.execute("ALTER TABLE exames_padrao ADD COLUMN sistema TEXT")
    except Exception:
        pass  # coluna ja existe
    try:
        import sqlite3 as _sq_seed2
        with _sq_seed2.connect(DB_PATH, timeout=10) as _cs2:
            _row = _cs2.execute(
                "SELECT valor FROM config WHERE chave='seed_versao'"
            ).fetchone()
            _seed_ok = _row and _row[0] == _SEED_VER
    except Exception:
        _seed_ok = False

    if not _seed_ok:
        try:
            from .popular_conhecimento import popular_conhecimento as _pop_con
            _pop_con(DB_PATH)
        except Exception as _ex2:
            try:
                from popular_conhecimento import popular_conhecimento as _pop_con
                _pop_con(DB_PATH)
            except Exception:
                print(f"[AVISO] popular_conhecimento: {_ex2}")
        try:
            from .grupos_exame_seed import popular_grupos as _pop_grp
            _pop_grp(DB_PATH)
        except Exception as _ex3:
            try:
                from grupos_exame_seed import popular_grupos as _pop_grp
                _pop_grp(DB_PATH)
            except Exception:
                print(f"[AVISO] popular_grupos: {_ex3}")
        try:
            from .sistema_resolver import resolver_sistemas as _res_sis
            _res_sis(DB_PATH)
        except Exception as _ex4:
            try:
                from sistema_resolver import resolver_sistemas as _res_sis
                _res_sis(DB_PATH)
            except Exception:
                print(f"[AVISO] sistema_resolver: {_ex4}")
        # Marca seed como concluido
        try:
            import sqlite3 as _sq_seed3
            with _sq_seed3.connect(DB_PATH, timeout=10) as _cs3:
                _cs3.execute("""
                    INSERT INTO config(chave, valor) VALUES(?,?)
                    ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor
                """, ("seed_versao", _SEED_VER))
        except Exception:
            pass


    # migração segura: data_revisao em diagnostico_tratamento
    try:
        import sqlite3 as _sq_mig
        with _sq_mig.connect(DB_PATH, timeout=10) as _cm:
            _cm.execute(
                "ALTER TABLE diagnostico_tratamento ADD COLUMN data_revisao TEXT")
    except Exception:
        pass  # coluna já existe


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

        # status_sugerido='revisao' quando extrator nao conseguiu extrair data
        status_final = status
        if status == "ativo" and dados.get("status_sugerido") == "revisao":
            status_final = "revisao"

        # Inserir exame
        cur.execute("""
            INSERT INTO exames
            (paciente_id, medico_id, internacao_id, tipo, tipo_exame, data_exame, laboratorio,
             medico_solicit, resultado_texto, arquivo_origem, drive_file_id, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            paciente_id,
            medico_id,
            dados.get("internacao_id"),
            dados.get("tipo", "numerico"),
            dados.get("tipo_exame"),
            dados.get("data_exame"),
            dados.get("laboratorio"),
            dados.get("medico_solicit"),
            dados.get("resultado_texto"),
            dados.get("arquivo_origem"),
            dados.get("drive_file_id"),
            status_final,
        ))
        exame_id = cur.lastrowid

        # Resultados numéricos (com sub-resultados, vínculo automático e grupo)
        try:
            from .grupo_resolver import resolver_grupo_parametro as _res_grp
        except ImportError:
            from grupo_resolver import resolver_grupo_parametro as _res_grp

        votos_grupo: dict = {}   # grupo_id → contagem de votos

        for r in dados.get("resultados", []):
            padrao_id = r.get("exame_padrao_id") or _buscar_padrao_id(_padrao_idx, r.get("parametro"))
            grupo_id  = _res_grp(conn, padrao_id, r.get("categoria"), r.get("parametro"))
            if grupo_id:
                votos_grupo[grupo_id] = votos_grupo.get(grupo_id, 0) + 1
            cur.execute("""
                INSERT INTO exame_resultados
                (exame_id, pai_id, parametro, valor, unidade, referencia, exame_padrao_id, grupo_id)
                VALUES (?,?,?,?,?,?,?,?)
            """, (exame_id, None, r.get("parametro"), r.get("valor"),
                  r.get("unidade"), r.get("referencia"), padrao_id, grupo_id))
            pai_id = cur.lastrowid
            for sub in r.get("sub_resultados", []):
                sub_padrao_id = r.get("exame_padrao_id") or _buscar_padrao_id(_padrao_idx, sub.get("parametro"))
                sub_grupo_id  = _res_grp(conn, sub_padrao_id, None, sub.get("parametro"))
                cur.execute("""
                    INSERT INTO exame_resultados
                    (exame_id, pai_id, parametro, valor, unidade, referencia, exame_padrao_id, grupo_id)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (exame_id, pai_id, sub.get("parametro"), sub.get("valor"),
                      sub.get("unidade"), sub.get("referencia"), sub_padrao_id, sub_grupo_id))

        # Grupo predominante do exame (maioria dos votos)
        if votos_grupo:
            grupo_exame = max(votos_grupo, key=lambda g: votos_grupo[g])
            cur.execute("UPDATE exames SET grupo_id=? WHERE id=?", (grupo_exame, exame_id))
        elif dados.get("tipo_exame"):
            # Fallback por tipo_exame (laudo sem resultados numéricos)
            try:
                from .grupo_resolver import resolver_grupo_por_categoria as _res_cat
            except ImportError:
                from grupo_resolver import resolver_grupo_por_categoria as _res_cat
            gid = _res_cat(dados.get("tipo_exame", ""))
            if gid:
                cur.execute("UPDATE exames SET grupo_id=? WHERE id=?", (gid, exame_id))

        # Laudo textual
        laudo = dados.get("laudo")
        if laudo:
            cur.execute("""
                INSERT INTO laudos (exame_id, texto_completo, resumo, conclusao)
                VALUES (?,?,?,?)
            """, (exame_id, laudo.get("texto_completo"),
                  laudo.get("resumo"), laudo.get("conclusao")))

        # Anexos imagem (suporta drive_file_id e/ou arquivo_local + pendente_sync)
        for i, anexo in enumerate(dados.get("anexos", [])):
            cur.execute("""
                INSERT INTO exame_anexos
                    (exame_id, drive_file_id, nome_arquivo, ordem, arquivo_local, pendente_sync)
                VALUES (?,?,?,?,?,?)
            """, (
                exame_id,
                anexo.get("drive_file_id"),
                anexo.get("nome_arquivo"),
                anexo.get("ordem", i),
                anexo.get("arquivo_local"),
                1 if anexo.get("pendente_sync") else 0,
            ))

        conn.commit()
        return exame_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def listar_anexos_exame(exame_id: int) -> list:
    """Retorna lista de anexos (imagens) de um exame ordenados por ordem."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            rows = conn.execute(
                "SELECT id, drive_file_id, nome_arquivo, ordem, arquivo_local, pendente_sync "
                "FROM exame_anexos WHERE exame_id=? ORDER BY ordem",
                (exame_id,),
            ).fetchall()
        return [
            {
                "id":            r[0],
                "drive_file_id": r[1],
                "nome_arquivo":  r[2],
                "ordem":         r[3],
                "arquivo_local": r[4],
                "pendente_sync": r[5],
            }
            for r in rows
        ]
    except Exception as ex:
        print(f"[MODEL] listar_anexos_exame: {ex}")
        return []


def sincronizar_anexos_pendentes() -> int:
    """
    Tenta fazer upload no Drive de todos os anexos com pendente_sync=1.
    Retorna numero de anexos sincronizados com sucesso.
    """
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            rows = conn.execute(
                "SELECT id, nome_arquivo, arquivo_local FROM exame_anexos "
                "WHERE pendente_sync=1 AND arquivo_local IS NOT NULL"
            ).fetchall()
    except Exception as ex:
        print(f"[MODEL] sincronizar_anexos_pendentes (leitura): {ex}")
        return 0

    if not rows:
        return 0

    try:
        from utils.drive_sync import _get_creds, _EXAME_IMAGENS_ID, upload_foto
        creds    = _get_creds()
        pasta_id = _EXAME_IMAGENS_ID
    except Exception as ex:
        print(f"[MODEL] sincronizar_anexos_pendentes (drive): {ex}")
        return 0

    import os as _os
    sincronizados = 0
    for row_id, nome_arquivo, arquivo_local in rows:
        try:
            if not _os.path.exists(arquivo_local or ""):
                continue
            drive_id = upload_foto(arquivo_local, nome_arquivo, pasta_id, creds)
            with sqlite3.connect(DB_PATH, timeout=30) as conn:
                conn.execute(
                    "UPDATE exame_anexos SET drive_file_id=?, arquivo_local=NULL, "
                    "pendente_sync=0 WHERE id=?",
                    (drive_id, row_id),
                )
            try:
                _os.remove(arquivo_local)
            except Exception:
                pass
            sincronizados += 1
        except Exception as ex:
            print(f"[MODEL] sync_anexo id={row_id}: {ex}")

    return sincronizados


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
            "SELECT COUNT(*) FROM exame_resultados WHERE exame_id=?",
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
        cur.execute("DELETE FROM exame_resultados WHERE exame_id=?", (exame_id_antigo,))
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
                INSERT INTO exame_resultados
                (exame_id, pai_id, parametro, valor, unidade, referencia)
                VALUES (?,?,?,?,?,?)
            """, (novo_id, None, r.get("parametro"), r.get("valor"),
                  r.get("unidade"), r.get("referencia")))
            pai_id = cur.lastrowid
            for sub in r.get("sub_resultados", []):
                cur.execute("""
                    INSERT INTO exame_resultados
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
        conn.execute("DELETE FROM exame_resultados WHERE exame_id=?", (exame_id,))
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
                   m.endereco, m.endereco_json, m.site, m.redes_sociais,
                   m.foto_drive_id, m.observacoes, m.ativo,
                   e.nome as especialidade, m.especialidade_id,
                   m.clinica_id, m.clinica_nome,
                   c.nome as clinica_nome_join
            FROM medicos m
            LEFT JOIN especialidades e ON e.id = m.especialidade_id
            LEFT JOIN clinicas c ON c.id = m.clinica_id
            {where}
            ORDER BY m.nome
        """)
        cols = ["id","nome","crm","uf","telefone","email","endereco","endereco_json",
                "site","redes_sociais","foto_drive_id","observacoes","ativo",
                "especialidade","especialidade_id","clinica_id","clinica_nome",
                "clinica_nome_join"]
        rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(zip(cols, r))
            # clinica_nome_join prevalece sobre clinica_nome (texto livre)
            d["clinica_nome"] = d["clinica_nome_join"] or d["clinica_nome"] or ""
            del d["clinica_nome_join"]
            result.append(d)
        return result
    finally:
        conn.close()


def salvar_medico(dados: dict) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur  = conn.cursor()
        if dados.get("id"):
            cur.execute("""
                UPDATE medicos SET nome=?, crm=?, uf=?, especialidade_id=?,
                telefone=?, email=?, endereco=?, endereco_json=?, site=?,
                redes_sociais=?, foto_drive_id=?, observacoes=?, ativo=?,
                clinica_id=?, clinica_nome=?
                WHERE id=?
            """, (dados["nome"], dados.get("crm"), dados.get("uf"),
                  dados.get("especialidade_id"), dados.get("telefone"),
                  dados.get("email"), dados.get("endereco"),
                  dados.get("endereco_json"), dados.get("site"),
                  dados.get("redes_sociais"), dados.get("foto_drive_id"),
                  dados.get("observacoes"), dados.get("ativo", 1),
                  dados.get("clinica_id"), dados.get("clinica_nome"),
                  dados["id"]))
            mid = dados["id"]
        else:
            cur.execute("""
                INSERT INTO medicos (nome, crm, uf, especialidade_id, telefone,
                email, endereco, endereco_json, site, redes_sociais,
                foto_drive_id, observacoes, clinica_id, clinica_nome)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (dados["nome"], dados.get("crm"), dados.get("uf"),
                  dados.get("especialidade_id"), dados.get("telefone"),
                  dados.get("email"), dados.get("endereco"),
                  dados.get("endereco_json"), dados.get("site"),
                  dados.get("redes_sociais"), dados.get("foto_drive_id"),
                  dados.get("observacoes"), dados.get("clinica_id"),
                  dados.get("clinica_nome")))
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
        _data = normalizar_data(dados["data"])
        if dados.get("id"):
            cur.execute("""
                UPDATE consultas SET medico_id=?, data=?, hora=?, tipo=?,
                local=?, observacoes=?, pauta=?, tipo_compromisso=?, clinica_id=?
                WHERE id=?
            """, (dados.get("medico_id"), _data, dados.get("hora"),
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
                  _data, dados.get("hora"),
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
            INSERT INTO receitas_laudos (consulta_id, medico_id, drive_file_id, nome_arquivo, data, observacoes, foto_path)
            VALUES (?,?,?,?,?,?,?)
        """, (dados.get("consulta_id"), dados.get("medico_id"),
              dados.get("drive_file_id"), dados.get("nome_arquivo"),
              normalizar_data(dados.get("data")), dados.get("observacoes"),
              dados.get("foto_path")))
        rid = cur.lastrowid
        conn.commit()
        return rid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def excluir_receita(receita_id: int) -> bool:
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute("DELETE FROM receitas_laudos WHERE id=?", (receita_id,))
        return True
    except Exception as ex:
        import logging as _log
        _log.getLogger(__name__).exception("[MODEL] excluir_receita: %s", ex)
        return False


def listar_receitas_laudos(consulta_id: int = None) -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur  = conn.cursor()
        where = f"WHERE r.consulta_id = {consulta_id}" if consulta_id else ""
        cur.execute(f"""
            SELECT r.id, r.data, r.nome_arquivo, r.drive_file_id,
                   r.observacoes, m.nome as medico, r.foto_path
            FROM receitas_laudos r
            LEFT JOIN medicos m ON m.id = r.medico_id
            {where}
            ORDER BY r.data DESC
        """)
        cols = ["id","data","nome_arquivo","drive_file_id","observacoes","medico","foto_path"]
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
        _di = normalizar_data(dados.get("data_inicio"))
        _df = dados.get("data_fim")
        if _df and _df != "continuo":
            _df = normalizar_data(_df)
        if dados.get("id"):
            cur.execute("""
                UPDATE remedios SET nome=?, dosagem=?, frequencia=?, data_inicio=?,
                data_fim=?, medico_id=?, receita_id=?, estoque_atual=?,
                estoque_minimo=?, ativo=?, observacoes=?, principio_ativo=?,
                tipo=?, prescrito=?, internacao_id=? WHERE id=?
            """, (dados["nome"], dados.get("dosagem"), dados.get("frequencia"),
                  _di, _df,
                  dados.get("medico_id"), dados.get("receita_id"),
                  dados.get("estoque_atual", 0), dados.get("estoque_minimo", 5),
                  dados.get("ativo", 1), dados.get("observacoes"),
                  dados.get("principio_ativo"),
                  dados.get("tipo", "remedio"), dados.get("prescrito", 0),
                  dados.get("internacao_id"),
                  dados["id"]))
            rid = dados["id"]
        else:
            cur.execute("""
                INSERT INTO remedios (nome, dosagem, frequencia, data_inicio, data_fim,
                medico_id, receita_id, estoque_atual, estoque_minimo, observacoes,
                principio_ativo, tipo, prescrito, internacao_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (dados["nome"], dados.get("dosagem"), dados.get("frequencia"),
                  _di, _df,
                  dados.get("medico_id"), dados.get("receita_id"),
                  dados.get("estoque_atual", 0), dados.get("estoque_minimo", 5),
                  dados.get("observacoes"), dados.get("principio_ativo"),
                  dados.get("tipo", "remedio"), dados.get("prescrito", 0),
                  dados.get("internacao_id")))
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
            SELECT id, nome, razao_social, endereco, telefone, whatsapp, site, app,
                   delivery, preferida, observacoes, ativo
            FROM farmacias {where} ORDER BY preferida DESC, nome
        """).fetchall()
        cols = ["id","nome","razao_social","endereco","telefone","whatsapp","site","app",
                "delivery","preferida","observacoes","ativo"]
        result = []
        for r in [dict(zip(cols, row)) for row in rows]:
            # nome_exibicao: fantasia se preenchido, senão razao_social
            r["nome_exibicao"] = r["nome"] or r.get("razao_social") or ""
            result.append(r)
        return result
    finally:
        conn.close()


def salvar_farmacia(dados):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur = conn.cursor()
        if dados.get("id"):
            cur.execute("""UPDATE farmacias SET nome=?, razao_social=?, endereco=?,
                           telefone=?, whatsapp=?, site=?, app=?,
                           delivery=?, preferida=?, observacoes=?, ativo=? WHERE id=?""",
                        (dados.get("nome") or "", dados.get("razao_social"),
                         dados.get("endereco"), dados.get("telefone"),
                         dados.get("whatsapp"), dados.get("site"), dados.get("app"),
                         dados.get("delivery", 0), dados.get("preferida", 0),
                         dados.get("observacoes"), dados.get("ativo", 1), dados["id"]))
            fid = dados["id"]
        else:
            cur.execute("""INSERT INTO farmacias (nome, razao_social, endereco,
                           telefone, whatsapp, site, app, delivery, preferida, observacoes)
                           VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (dados.get("nome") or "", dados.get("razao_social"),
                         dados.get("endereco"), dados.get("telefone"),
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


def registrar_mov(dados: dict) -> int:
    """
    Registra uma movimentacao em remedios_mov e atualiza estoque em remedios.

    dados obrigatorios:
      remedio_id, tipo ('compra'|'inicio_uso'|'tomada'|'ajuste'|'vencimento'),
      data (YYYY-MM-DD), quantidade (positivo=entrada, negativo=saida)

    dados opcionais:
      preco_unitario, preco_total, farmacia_id, receita_id, consulta_id,
      origem ('receita'|'manual'|'automatico'), observacoes
    """
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            # Calcula estoque apos movimentacao
            row = conn.execute(
                "SELECT estoque_atual FROM remedios WHERE id=?",
                (dados["remedio_id"],)
            ).fetchone()
            estoque_atual = row[0] if row else 0
            qtd = dados.get("quantidade", 0)
            estoque_apos = estoque_atual + qtd

            conn.execute("""
                INSERT INTO remedios_mov
                    (remedio_id, tipo, data, quantidade, estoque_apos,
                     preco_unitario, preco_total, farmacia_id, receita_id,
                     consulta_id, origem, observacoes,
                     foto_nf_path, foto_nf_drive_id, qr_nfe)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                dados["remedio_id"],
                dados["tipo"],
                dados["data"],
                qtd,
                estoque_apos,
                dados.get("preco_unitario"),
                dados.get("preco_total"),
                dados.get("farmacia_id"),
                dados.get("receita_id"),
                dados.get("consulta_id"),
                dados.get("origem", "manual"),
                dados.get("observacoes"),
                dados.get("foto_nf_path"),
                dados.get("foto_nf_drive_id"),
                dados.get("qr_nfe"),
            ))
            mid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Atualiza estoque se movimento altera quantidade
            if qtd != 0:
                conn.execute(
                    "UPDATE remedios SET estoque_atual = estoque_atual + ? WHERE id=?",
                    (qtd, dados["remedio_id"])
                )
            return mid
    except Exception as ex:
        import logging as _log
        _log.getLogger(__name__).exception("[MODEL] registrar_mov: %s", ex)
        return -1


def salvar_compra_nf(cabecalho: dict, itens: list[dict]) -> int:
    """
    Salva uma nota fiscal com seus itens.

    cabecalho: {farmacia_id, data, total, foto_path, foto_drive_id, qr_nfe, observacoes}
    itens: [{remedio_id, nome_nf, dosagem, quantidade_emb, comprimidos_emb,
              preco_unitario, preco_total}]

    Também registra movimentação de estoque em remedios_mov para cada item.
    Retorna compra_id.
    """
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO compras
                    (farmacia_id, data, total, foto_path, foto_drive_id, qr_nfe, observacoes)
                VALUES (?,?,?,?,?,?,?)
            """, (
                cabecalho.get("farmacia_id"),
                cabecalho.get("data"),
                cabecalho.get("total", 0),
                cabecalho.get("foto_path"),
                cabecalho.get("foto_drive_id"),
                cabecalho.get("qr_nfe"),
                cabecalho.get("observacoes"),
            ))
            compra_id = cur.lastrowid

            for it in itens:
                cur.execute("""
                    INSERT INTO compra_itens
                        (compra_id, remedio_id, nome_nf, dosagem,
                         quantidade_emb, comprimidos_emb, preco_unitario, preco_total)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (
                    compra_id,
                    it.get("remedio_id"),
                    it.get("nome_nf") or "",
                    it.get("dosagem"),
                    it.get("quantidade_emb", 1),
                    it.get("comprimidos_emb"),
                    it.get("preco_unitario", 0),
                    it.get("preco_total", 0),
                ))

                # Atualiza estoque se tiver remedio_id
                rid = it.get("remedio_id")
                qtd = it.get("quantidade_emb", 1) or 1
                if rid:
                    cur.execute("""
                        INSERT INTO remedios_mov
                            (remedio_id, tipo, data, quantidade, estoque_apos,
                             preco_unitario, preco_total, farmacia_id, origem, observacoes,
                             foto_nf_path, foto_nf_drive_id, qr_nfe)
                        SELECT
                            ?, 'compra', ?, ?,
                            COALESCE(estoque_atual, 0) + ?,
                            ?, ?, ?, 'nota_fiscal', ?,
                            ?, ?, ?
                        FROM remedios WHERE id=?
                    """, (
                        rid,
                        cabecalho.get("data"),
                        qtd, qtd,
                        it.get("preco_unitario", 0),
                        it.get("preco_total", 0),
                        cabecalho.get("farmacia_id"),
                        it.get("nome_nf"),
                        cabecalho.get("foto_path"),
                        cabecalho.get("foto_drive_id"),
                        cabecalho.get("qr_nfe"),
                        rid,
                    ))
                    cur.execute(
                        "UPDATE remedios SET estoque_atual = estoque_atual + ? WHERE id=?",
                        (qtd, rid)
                    )

            return compra_id
    except Exception as ex:
        import logging as _log
        _log.getLogger(__name__).exception("[MODEL] salvar_compra_nf: %s", ex)
        raise


def listar_compras_nf(limit: int = 50, incluir_canceladas: bool = False) -> list[dict]:
    """Lista notas fiscais (cabeçalho) com totais e farmácia, mais recentes primeiro."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            where = "" if incluir_canceladas else "WHERE c.status != 'cancelada'"
            rows = conn.execute(f"""
                SELECT c.id, c.data, c.total, c.foto_path, c.foto_drive_id, c.qr_nfe,
                       c.observacoes, c.criado_em, c.status,
                       COALESCE(NULLIF(f.nome,''), f.razao_social) as farmacia_nome,
                       f.id    as farmacia_id,
                       COUNT(ci.id)                        as num_itens,
                       GROUP_CONCAT(ci.nome_nf, ' | ')     as nomes_itens
                FROM compras c
                LEFT JOIN farmacias    f  ON f.id  = c.farmacia_id
                LEFT JOIN compra_itens ci ON ci.compra_id = c.id
                {where}
                GROUP BY c.id
                ORDER BY c.data DESC, c.id DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]
    except Exception as ex:
        import logging as _log
        _log.getLogger(__name__).exception("[MODEL] listar_compras_nf: %s", ex)
        return []


def listar_itens_compra(compra_id: int) -> list[dict]:
    """Lista itens de uma nota fiscal específica."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT ci.*, r.nome as remedio_nome
                FROM compra_itens ci
                LEFT JOIN remedios r ON r.id = ci.remedio_id
                WHERE ci.compra_id = ?
                ORDER BY ci.id
            """, (compra_id,)).fetchall()
            return [dict(r) for r in rows]
    except Exception as ex:
        import logging as _log
        _log.getLogger(__name__).exception("[MODEL] listar_itens_compra: %s", ex)
        return []


def atualizar_compra_nf(compra_id: int, dados: dict) -> bool:
    """Atualiza cabeçalho da compra (farmacia_id, data, observacoes)."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("""
                UPDATE compras SET farmacia_id=?, data=?, observacoes=?
                WHERE id=?
            """, (dados.get("farmacia_id"), dados.get("data"),
                  dados.get("observacoes"), compra_id))
        return True
    except Exception as ex:
        import logging as _log
        _log.getLogger(__name__).exception("[MODEL] atualizar_compra_nf: %s", ex)
        return False


def cancelar_compra_nf(compra_id: int, motivo: str = "") -> bool:
    """
    Cancela uma nota fiscal inteira.
    - Marca compra como 'cancelada'
    - Reverte estoque de cada item em remedios
    - Registra movimentação de estorno em remedios_mov
    """
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.row_factory = sqlite3.Row
            compra = conn.execute(
                "SELECT * FROM compras WHERE id=?", (compra_id,)
            ).fetchone()
            if not compra or compra["status"] == "cancelada":
                return False

            itens = conn.execute(
                "SELECT * FROM compra_itens WHERE compra_id=?", (compra_id,)
            ).fetchall()

            for it in itens:
                rid = it["remedio_id"]
                qtd_orig     = it["quantidade_emb"] or 0
                qtd_devolvida = it["quantidade_devolvida"] or 0
                qtd_estornar  = qtd_orig - qtd_devolvida
                if rid and qtd_estornar > 0:
                    row = conn.execute(
                        "SELECT estoque_atual FROM remedios WHERE id=?", (rid,)
                    ).fetchone()
                    est_atual = row["estoque_atual"] if row else 0
                    est_apos  = est_atual - qtd_estornar
                    conn.execute("""
                        INSERT INTO remedios_mov
                            (remedio_id, tipo, data, quantidade, estoque_apos,
                             farmacia_id, origem, observacoes)
                        VALUES (?,?,date('now'),?,?,?,'cancelamento',?)
                    """, (rid, "estorno", -qtd_estornar, est_apos,
                          compra["farmacia_id"],
                          motivo or f"Cancelamento NF #{compra_id}"))
                    conn.execute(
                        "UPDATE remedios SET estoque_atual = estoque_atual - ? WHERE id=?",
                        (qtd_estornar, rid)
                    )

            conn.execute(
                "UPDATE compras SET status=?, observacoes=? WHERE id=?",
                ("cancelada",
                 (compra["observacoes"] or "") + f" | Cancelado: {motivo}" if motivo else compra["observacoes"],
                 compra_id)
            )
        return True
    except Exception as ex:
        import logging as _log
        _log.getLogger(__name__).exception("[MODEL] cancelar_compra_nf: %s", ex)
        return False


def devolver_item_compra(item_id: int, quantidade: int, motivo: str = "") -> bool:
    """
    Registra devolução parcial de um item.
    - Incrementa quantidade_devolvida
    - Reverte estoque proporcional
    - Registra movimentação de estorno
    """
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.row_factory = sqlite3.Row
            it = conn.execute(
                """SELECT ci.*, c.farmacia_id FROM compra_itens ci
                   JOIN compras c ON c.id = ci.compra_id WHERE ci.id=?""",
                (item_id,)
            ).fetchone()
            if not it:
                return False

            qtd_disp = (it["quantidade_emb"] or 0) - (it["quantidade_devolvida"] or 0)
            qtd_dev  = min(quantidade, qtd_disp)
            if qtd_dev <= 0:
                return False

            rid = it["remedio_id"]
            if rid:
                row = conn.execute(
                    "SELECT estoque_atual FROM remedios WHERE id=?", (rid,)
                ).fetchone()
                est_atual = row["estoque_atual"] if row else 0
                est_apos  = est_atual - qtd_dev
                conn.execute("""
                    INSERT INTO remedios_mov
                        (remedio_id, tipo, data, quantidade, estoque_apos,
                         farmacia_id, origem, observacoes)
                    VALUES (?,?,date('now'),?,?,?,'devolucao',?)
                """, (rid, "estorno", -qtd_dev, est_apos,
                      it["farmacia_id"],
                      motivo or f"Devolução item #{item_id}"))
                conn.execute(
                    "UPDATE remedios SET estoque_atual = estoque_atual - ? WHERE id=?",
                    (qtd_dev, rid)
                )

            conn.execute(
                "UPDATE compra_itens SET quantidade_devolvida = quantidade_devolvida + ? WHERE id=?",
                (qtd_dev, item_id)
            )
        return True
    except Exception as ex:
        import logging as _log
        _log.getLogger(__name__).exception("[MODEL] devolver_item_compra: %s", ex)
        return False


def listar_notas_fiscais(limit: int = 50) -> list[dict]:
    """
    Lista compras via nota fiscal agrupadas por nota.
    Agrupa por (data, farmacia_id, foto_nf_path) — cada grupo é uma NF.
    Retorna lista com total da nota, farmácia, data, itens e foto.
    """
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT
                    m.data,
                    m.farmacia_id,
                    f.nome  as farmacia_nome,
                    m.foto_nf_path,
                    m.foto_nf_drive_id,
                    m.qr_nfe,
                    SUM(m.preco_total)  as total_nota,
                    COUNT(*)            as num_itens,
                    GROUP_CONCAT(r.nome, ' | ') as nomes_remedios,
                    MIN(m.id)           as id_ref
                FROM remedios_mov m
                LEFT JOIN farmacias f ON f.id = m.farmacia_id
                LEFT JOIN remedios  r ON r.id = m.remedio_id
                WHERE m.origem = 'nota_fiscal'
                GROUP BY m.data, m.farmacia_id, COALESCE(m.foto_nf_path, m.id)
                ORDER BY m.data DESC, id_ref DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]
    except Exception as ex:
        import logging as _log
        _log.getLogger(__name__).exception("[MODEL] listar_notas_fiscais: %s", ex)
        return []


def listar_mov_remedio(remedio_id: int, limit: int = 50) -> list[dict]:
    """Retorna movimentacoes de um remedio, mais recentes primeiro."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT m.*, f.nome as farmacia_nome
                FROM remedios_mov m
                LEFT JOIN farmacias f ON f.id = m.farmacia_id
                WHERE m.remedio_id = ?
                ORDER BY m.data DESC, m.id DESC
                LIMIT ?
            """, (remedio_id, limit)).fetchall()
            return [dict(r) for r in rows]
    except Exception as ex:
        import logging as _log
        _log.getLogger(__name__).exception("[MODEL] listar_mov_remedio: %s", ex)
        return []


def registrar_receita_remedios(
    remedios_extraidos: list[dict],
    receita_id: int | None,
    consulta_id: int | None,
    medico_id: int | None,
    data_consulta: str,
) -> list[dict]:
    """
    Processa lista de remedios extraidos da receita:
    - Remedio ja cadastrado  -> registrar_mov tipo='compra' + 'inicio_uso'
    - Remedio novo           -> salvar_remedio + registrar_mov tipo='inicio_uso'

    Retorna lista de dicts com resultado por remedio:
      {nome, acao: 'cadastrado'|'atualizado', remedio_id, mov_id}
    """
    existentes = {
        r["nome"].strip().upper(): r
        for r in listar_remedios(so_ativos=False)
    }
    resultado = []

    for med in remedios_extraidos:
        nome = (med.get("nome") or "").strip()
        if not nome:
            continue
        chave = nome.upper()

        if chave in existentes:
            rem = existentes[chave]
            rid = rem["id"]
            # Atualiza dados da prescricao
            salvar_remedio({
                "id":          rid,
                "nome":        rem["nome"],
                "dosagem":     med.get("dosagem") or rem.get("dosagem"),
                "frequencia":  med.get("frequencia") or rem.get("frequencia"),
                "data_inicio": data_consulta,
                "data_fim":    rem.get("data_fim"),
                "medico_id":   medico_id or rem.get("medico_id"),
                "receita_id":  receita_id or rem.get("receita_id"),
                "estoque_atual":  rem.get("estoque_atual", 0),
                "estoque_minimo": rem.get("estoque_minimo", 5),
                "observacoes": med.get("observacoes") or rem.get("observacoes"),
                "ativo":       rem.get("ativo", 1),
                "principio_ativo": rem.get("principio_ativo"),
                "tipo":        rem.get("tipo", "remedio"),
                "prescrito":   1,
            })
            # Registra inicio de uso na movimentacao (sem alterar estoque)
            mid = registrar_mov({
                "remedio_id":  rid,
                "tipo":        "inicio_uso",
                "data":        data_consulta,
                "quantidade":  0,
                "receita_id":  receita_id,
                "consulta_id": consulta_id,
                "origem":      "receita",
                "observacoes": (
                    f"Receita: {med.get('dosagem','')} {med.get('frequencia','')}".strip()
                ),
            })
            resultado.append({
                "nome": nome,
                "acao": "atualizado",
                "remedio_id": rid,
                "mov_id": mid,
                "ja_existia": True,
            })
        else:
            # Cadastra remedio novo
            rid = salvar_remedio({
                "id":          None,
                "nome":        nome,
                "dosagem":     med.get("dosagem"),
                "frequencia":  med.get("frequencia"),
                "data_inicio": data_consulta,
                "data_fim":    None,
                "medico_id":   medico_id,
                "receita_id":  receita_id,
                "estoque_atual":  0,
                "estoque_minimo": 5,
                "observacoes": med.get("observacoes"),
                "ativo":       1,
                "principio_ativo": None,
                "tipo":        "remedio",
                "prescrito":   1,
            })
            # Registra inicio de uso
            mid = registrar_mov({
                "remedio_id":  rid,
                "tipo":        "inicio_uso",
                "data":        data_consulta,
                "quantidade":  0,
                "receita_id":  receita_id,
                "consulta_id": consulta_id,
                "origem":      "receita",
                "observacoes": (
                    f"Primeiro uso. {med.get('dosagem','')} {med.get('frequencia','')}".strip()
                ),
            })
            resultado.append({
                "nome": nome,
                "acao": "cadastrado",
                "remedio_id": rid,
                "mov_id": mid,
                "ja_existia": False,
            })

    return resultado


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
    """Upsert do perfil (sempre id=1). Salva em prontuario.db (backup) e espelha em koios.db."""
    import json as _json
    _migrar_campos_perfil()

    _SQL = """
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
    """
    _params = (
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
    )

    # salva em prontuario.db (fonte do backup)
    with _ProntuarioConn(DB_PATH, timeout=30) as conn:
        conn.execute(_SQL, _params)

    # espelha em koios.db para compatibilidade
    try:
        conn2 = sqlite3.connect(CORE_DB, timeout=30)
        conn2.execute(_SQL, _params)
        conn2.commit()
        conn2.close()
    except Exception as ex:
        print(f"[PERFIL] espelho koios.db: {ex}")


def carregar_perfil() -> dict | None:
    """Retorna o perfil ou None se ainda não cadastrado.
    Le de prontuario.db primeiro (fonte do backup); fallback para koios.db."""
    import json as _json
    _migrar_campos_perfil()
    _migrar_status_exames()

    _SQL_SEL = """
        SELECT nome, email, data_nasc, sexo, foto_url,
               peso, altura, tipo_sanguineo, condicoes_cronicas,
               contato_emergencia, tel_emergencia,
               tema, accent_color, tamanho_fonte
        FROM perfil_usuario WHERE id = 1
    """
    row = None
    for _db in (DB_PATH, CORE_DB):
        try:
            conn = sqlite3.connect(_db, timeout=30)
            row  = conn.execute(_SQL_SEL).fetchone()
            conn.close()
            if row and row[0]:   # tem nome preenchido
                break
        except Exception:
            pass
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
# HELPERS — OBSERVACOES MEDICO
# ══════════════════════════════════════════════════════════════

def salvar_observacao_medico(dados: dict) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO observacoes_medico
            (medico_id, nome_medico, data, texto, drive_file_id, nome_arquivo)
            VALUES (?,?,?,?,?,?)
        """, (
            dados.get("medico_id"),
            dados.get("nome_medico"),
            dados.get("data"),
            dados["texto"],
            dados.get("drive_file_id"),
            dados.get("nome_arquivo"),
        ))
        oid = cur.lastrowid
        conn.commit()
        return oid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def listar_observacoes_medico(medico_id: int = None) -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur = conn.cursor()
        if medico_id:
            cur.execute("""
                SELECT id, medico_id, nome_medico, data, texto,
                       drive_file_id, nome_arquivo, lida_paciente, criado_em
                FROM observacoes_medico
                WHERE medico_id = ?
                ORDER BY data DESC, criado_em DESC
            """, (medico_id,))
        else:
            cur.execute("""
                SELECT id, medico_id, nome_medico, data, texto,
                       drive_file_id, nome_arquivo, lida_paciente, criado_em
                FROM observacoes_medico
                ORDER BY data DESC, criado_em DESC
            """)
        cols = ["id","medico_id","nome_medico","data","texto",
                "drive_file_id","nome_arquivo","lida_paciente","criado_em"]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        conn.close()


def marcar_observacao_lida(obs_id: int):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute(
            "UPDATE observacoes_medico SET lida_paciente = 1 WHERE id = ?",
            (obs_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def contar_observacoes_nao_lidas() -> int:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM observacoes_medico WHERE lida_paciente = 0")
        row = cur.fetchone()
        return row[0] if row else 0
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
                SELECT t.id, t.nome, t.icone, t.cor, t.tipo, t.horario, t.padrao, t.ativo,
                       COUNT(m.id) as total_momentos,
                       t.hora_inicio, t.hora_fim,
                       t.intensidade_fisica, t.intensidade_mental
                FROM rotinas_templates t
                LEFT JOIN momentos_rotina m ON m.template_id = t.id
                {where}
                GROUP BY t.id ORDER BY COALESCE(t.horario, t.hora_inicio) NULLS LAST, t.nome
            """).fetchall()
            cols = ["id","nome","icone","cor","tipo","horario","padrao","ativo",
                    "total_momentos","hora_inicio","hora_fim",
                    "intensidade_fisica","intensidade_mental"]
            return [dict(zip(cols, r)) for r in rows]
    except Exception as ex:
        print(f"[MODEL] listar_templates: {ex}")
        return []


def salvar_template(dados: dict) -> int:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            if dados.get("id"):
                conn.execute("""UPDATE rotinas_templates
                    SET nome=?, tipo=?, horario=?, padrao=?, ativo=?,
                        hora_inicio=?, hora_fim=?,
                        intensidade_fisica=?, intensidade_mental=?
                    WHERE id=?""",
                    (dados["nome"], dados.get("tipo","alimentacao"),
                     dados.get("horario") or None,
                     1 if dados.get("padrao") else 0,
                     1 if dados.get("ativo", True) else 0,
                     dados.get("hora_inicio") or None,
                     dados.get("hora_fim") or None,
                     dados.get("intensidade_fisica") or None,
                     dados.get("intensidade_mental") or None,
                     dados["id"]))
                return dados["id"]
            else:
                cur = conn.execute("""INSERT INTO rotinas_templates
                    (nome, tipo, horario, padrao, ativo,
                     hora_inicio, hora_fim, intensidade_fisica, intensidade_mental)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (dados["nome"], dados.get("tipo","alimentacao"),
                     dados.get("horario") or None,
                     1 if dados.get("padrao") else 0, 1,
                     dados.get("hora_inicio") or None,
                     dados.get("hora_fim") or None,
                     dados.get("intensidade_fisica") or None,
                     dados.get("intensidade_mental") or None))
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
                SELECT i.id, i.tipo, i.descricao, i.quantidade, i.unidade,
                       i.detalhe, i.horario, i.frequencia,
                       i.calorias, i.proteinas, i.vitaminas, i.ordem,
                       r.nome as remedio_nome, r.dosagem as remedio_dosagem,
                       i.hora_inicio, i.hora_fim,
                       i.intensidade_fisica, i.intensidade_mental,
                       i.remedio_id
                FROM itens_momento i
                LEFT JOIN remedios r ON r.id = i.remedio_id
                WHERE i.momento_id=? ORDER BY i.ordem, i.id
            """, (momento_id,)).fetchall()
            cols = ["id","tipo","descricao","quantidade","unidade",
                    "detalhe","horario","frequencia",
                    "calorias","proteinas","vitaminas","ordem",
                    "remedio_nome","remedio_dosagem",
                    "hora_inicio","hora_fim",
                    "intensidade_fisica","intensidade_mental",
                    "remedio_id"]
            return [dict(zip(cols, r)) for r in rows]
    except Exception as ex:
        print(f"[MODEL] listar_itens: {ex}")
        return []


def salvar_item(dados: dict) -> int:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            if dados.get("id"):
                conn.execute("""UPDATE itens_momento SET
                    tipo=?, descricao=?, quantidade=?, unidade=?, detalhe=?,
                    horario=?, frequencia=?, remedio_id=?, ordem=?,
                    hora_inicio=?, hora_fim=?,
                    intensidade_fisica=?, intensidade_mental=?
                    WHERE id=?""",
                    (dados.get("tipo","alimento"), dados.get("descricao",""),
                     dados.get("quantidade"), dados.get("unidade","Unidade"),
                     dados.get("detalhe"), dados.get("horario"),
                     dados.get("frequencia","diario"),
                     dados.get("remedio_id"), dados.get("ordem", 0),
                     dados.get("hora_inicio"), dados.get("hora_fim"),
                     dados.get("intensidade_fisica"), dados.get("intensidade_mental"),
                     dados["id"]))
                return dados["id"]
            else:
                cur = conn.execute("""INSERT INTO itens_momento
                    (momento_id, tipo, descricao, quantidade, unidade,
                     detalhe, horario, frequencia, remedio_id, ordem,
                     hora_inicio, hora_fim, intensidade_fisica, intensidade_mental)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (dados["momento_id"], dados.get("tipo","alimento"),
                     dados.get("descricao",""),
                     dados.get("quantidade"), dados.get("unidade","Unidade"),
                     dados.get("detalhe"), dados.get("horario"),
                     dados.get("frequencia","diario"),
                     dados.get("remedio_id"), dados.get("ordem", 0),
                     dados.get("hora_inicio"), dados.get("hora_fim"),
                     dados.get("intensidade_fisica"), dados.get("intensidade_mental")))
                return cur.lastrowid
    except Exception as ex:
        print(f"[MODEL] salvar_item: {ex}")
        return 0


def listar_nutricao_por_template() -> dict:
    """Retorna {template_id: {calorias, proteinas, vitaminas_set}} para todos os templates ativos."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            rows = conn.execute("""
                SELECT t.id,
                       SUM(COALESCE(i.calorias,  0)) AS cal,
                       SUM(COALESCE(i.proteinas, 0)) AS prot,
                       GROUP_CONCAT(i.vitaminas, ',')  AS vits
                FROM rotinas_templates t
                LEFT JOIN momentos_rotina m ON m.template_id = t.id
                LEFT JOIN itens_momento   i ON i.momento_id  = m.id
                WHERE t.ativo = 1
                GROUP BY t.id
            """).fetchall()
        resultado = {}
        for tid, cal, prot, vits_raw in rows:
            vits = sorted(set(
                v.strip()
                for v in (vits_raw or "").split(",")
                if v.strip()
            ))
            resultado[tid] = {"calorias": cal or 0, "proteinas": prot or 0, "vitaminas": vits}
        return resultado
    except Exception as ex:
        print(f"[MODEL] listar_nutricao_por_template: {ex}")
        return {}


def salvar_nutricao_item(item_id: int, calorias, proteinas, vitaminas: str) -> None:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute(
                "UPDATE itens_momento SET calorias=?, proteinas=?, vitaminas=? WHERE id=?",
                (calorias, proteinas, vitaminas, item_id))
    except Exception as ex:
        print(f"[MODEL] salvar_nutricao_item: {ex}")


def excluir_item(iid: int) -> None:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("DELETE FROM itens_momento WHERE id=?", (iid,))
    except Exception as ex:
        print(f"[MODEL] excluir_item: {ex}")


# ── Ingredientes do item ───────────────────────────────────────────────

def listar_ingredientes_item(item_id: int) -> list[dict]:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            rows = conn.execute("""
                SELECT ii.id, ii.tipo, ii.descricao, ii.sub_receita_id,
                       r.nome as receita_nome,
                       ii.quantidade, ii.unidade, ii.calorias, ii.proteinas,
                       ii.peso_unitario_g, ii.ordem
                FROM item_ingredientes ii
                LEFT JOIN receitas r ON r.id = ii.sub_receita_id
                WHERE ii.item_id = ? ORDER BY ii.ordem, ii.id
            """, (item_id,)).fetchall()
            cols = ["id","tipo","descricao","sub_receita_id","receita_nome",
                    "quantidade","unidade","calorias","proteinas","peso_unitario_g","ordem"]
            return [dict(zip(cols, r)) for r in rows]
    except Exception as ex:
        print(f"[MODEL] listar_ingredientes_item: {ex}")
        return []


def salvar_ingrediente_item(dados: dict) -> int:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            if dados.get("id"):
                conn.execute("""UPDATE item_ingredientes
                    SET tipo=?, descricao=?, sub_receita_id=?,
                        quantidade=?, unidade=?, calorias=?, proteinas=?,
                        peso_unitario_g=?, ordem=?
                    WHERE id=?""",
                    (dados.get("tipo","item"), dados.get("descricao"),
                     dados.get("sub_receita_id"),
                     dados.get("quantidade"), dados.get("unidade","Unidade"),
                     dados.get("calorias"), dados.get("proteinas"),
                     dados.get("peso_unitario_g"),
                     dados.get("ordem", 0), dados["id"]))
                return dados["id"]
            else:
                cur = conn.execute("""INSERT INTO item_ingredientes
                    (item_id, tipo, descricao, sub_receita_id,
                     quantidade, unidade, calorias, proteinas, peso_unitario_g, ordem)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (dados["item_id"], dados.get("tipo","item"),
                     dados.get("descricao"), dados.get("sub_receita_id"),
                     dados.get("quantidade"), dados.get("unidade","Unidade"),
                     dados.get("calorias"), dados.get("proteinas"),
                     dados.get("peso_unitario_g"),
                     dados.get("ordem", 0)))
                return cur.lastrowid
    except Exception as ex:
        print(f"[MODEL] salvar_ingrediente_item: {ex}")
        return 0


def excluir_ingrediente_item(ingr_id: int) -> None:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("DELETE FROM item_ingredientes WHERE id=?", (ingr_id,))
    except Exception as ex:
        print(f"[MODEL] excluir_ingrediente_item: {ex}")


def listar_receitas(so_ativas: bool = True) -> list[dict]:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            filtro = "WHERE r.ativo=1" if so_ativas else ""
            rows = conn.execute(f"""
                SELECT r.id, r.nome, r.descricao, r.rendimento_qtd, r.rendimento_unid,
                       r.calorias_total, r.proteinas_total, r.ativo,
                       COUNT(ri.id) as total_ingredientes
                FROM receitas r
                LEFT JOIN receita_ingredientes ri ON ri.receita_id = r.id
                {filtro}
                GROUP BY r.id ORDER BY r.nome
            """).fetchall()
            cols = ["id","nome","descricao","rendimento_qtd","rendimento_unid",
                    "calorias_total","proteinas_total","ativo","total_ingredientes"]
            return [dict(zip(cols, r)) for r in rows]
    except Exception as ex:
        print(f"[MODEL] listar_receitas: {ex}")
        return []


def salvar_receita_culinaria(dados: dict) -> int:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            if dados.get("id"):
                conn.execute("""UPDATE receitas SET nome=?, descricao=?, modo_preparo=?,
                    rendimento_qtd=?, rendimento_unid=?, porcao_qtd=?, porcao_unid=?, ativo=?
                    WHERE id=?""",
                    (dados["nome"], dados.get("descricao"), dados.get("modo_preparo"),
                     dados.get("rendimento_qtd"), dados.get("rendimento_unid","Porcao"),
                     dados.get("porcao_qtd"), dados.get("porcao_unid"),
                     dados.get("ativo", 1), dados["id"]))
                return dados["id"]
            else:
                cur = conn.execute("""INSERT INTO receitas
                    (nome, descricao, modo_preparo, rendimento_qtd, rendimento_unid,
                     porcao_qtd, porcao_unid, ativo)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (dados["nome"], dados.get("descricao"), dados.get("modo_preparo"),
                     dados.get("rendimento_qtd"), dados.get("rendimento_unid","Porcao"),
                     dados.get("porcao_qtd"), dados.get("porcao_unid"),
                     dados.get("ativo", 1)))
                return cur.lastrowid
    except Exception as ex:
        print(f"[MODEL] salvar_receita_culinaria: {ex}")
        return 0


def excluir_receita_culinaria(rid: int) -> None:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("DELETE FROM receitas WHERE id=?", (rid,))
    except Exception as ex:
        print(f"[MODEL] excluir_receita_culinaria: {ex}")


def listar_ingredientes_receita(receita_id: int) -> list[dict]:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            rows = conn.execute("""
                SELECT ri.id, ri.tipo, ri.descricao, ri.sub_receita_id,
                       r2.nome as sub_nome,
                       ri.quantidade, ri.unidade, ri.calorias, ri.proteinas, ri.ordem
                FROM receita_ingredientes ri
                LEFT JOIN receitas r2 ON r2.id = ri.sub_receita_id
                WHERE ri.receita_id=? ORDER BY ri.ordem, ri.id
            """, (receita_id,)).fetchall()
            cols = ["id","tipo","descricao","sub_receita_id","sub_nome",
                    "quantidade","unidade","calorias","proteinas","ordem"]
            return [dict(zip(cols, r)) for r in rows]
    except Exception as ex:
        print(f"[MODEL] listar_ingredientes_receita: {ex}")
        return []


def salvar_ingrediente_receita(dados: dict) -> int:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            if dados.get("id"):
                conn.execute("""UPDATE receita_ingredientes
                    SET tipo=?, descricao=?, sub_receita_id=?,
                        quantidade=?, unidade=?, calorias=?, proteinas=?, ordem=?
                    WHERE id=?""",
                    (dados.get("tipo","item"), dados.get("descricao"),
                     dados.get("sub_receita_id"),
                     dados.get("quantidade"), dados.get("unidade","Unidade"),
                     dados.get("calorias"), dados.get("proteinas"),
                     dados.get("ordem",0), dados["id"]))
                return dados["id"]
            else:
                cur = conn.execute("""INSERT INTO receita_ingredientes
                    (receita_id, tipo, descricao, sub_receita_id,
                     quantidade, unidade, calorias, proteinas, ordem)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (dados["receita_id"], dados.get("tipo","item"),
                     dados.get("descricao"), dados.get("sub_receita_id"),
                     dados.get("quantidade"), dados.get("unidade","Unidade"),
                     dados.get("calorias"), dados.get("proteinas"),
                     dados.get("ordem",0)))
                return cur.lastrowid
    except Exception as ex:
        print(f"[MODEL] salvar_ingrediente_receita: {ex}")
        return 0


def excluir_ingrediente_receita(iid: int) -> None:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("DELETE FROM receita_ingredientes WHERE id=?", (iid,))
    except Exception as ex:
        print(f"[MODEL] excluir_ingrediente_receita: {ex}")


def salvar_nutricao(dados: dict) -> int:
    """Salva ou atualiza tabela nutricional de uma entidade (receita, ingrediente, item)."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            existing = conn.execute(
                "SELECT id FROM nutricao WHERE entidade_tipo=? AND entidade_id=?",
                (dados["entidade_tipo"], dados["entidade_id"])).fetchone()
            if existing:
                conn.execute("""UPDATE nutricao SET
                    por_100g=?, kcal=?, kj=?, carboidratos=?, acucares=?,
                    proteinas=?, gorduras=?, saturadas=?, trans=?,
                    fibras=?, sodio=?, vitaminas_json=?, atualizado_em=datetime('now')
                    WHERE entidade_tipo=? AND entidade_id=?""",
                    (dados.get("por_100g",100), dados.get("kcal"),
                     dados.get("kj"), dados.get("carboidratos"), dados.get("acucares"),
                     dados.get("proteinas"), dados.get("gorduras"), dados.get("saturadas"),
                     dados.get("trans"), dados.get("fibras"), dados.get("sodio"),
                     dados.get("vitaminas_json"),
                     dados["entidade_tipo"], dados["entidade_id"]))
                return existing[0]
            else:
                cur = conn.execute("""INSERT INTO nutricao
                    (entidade_tipo, entidade_id, por_100g, kcal, kj,
                     carboidratos, acucares, proteinas, gorduras, saturadas,
                     trans, fibras, sodio, vitaminas_json)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (dados["entidade_tipo"], dados["entidade_id"],
                     dados.get("por_100g",100), dados.get("kcal"),
                     dados.get("kj"), dados.get("carboidratos"), dados.get("acucares"),
                     dados.get("proteinas"), dados.get("gorduras"), dados.get("saturadas"),
                     dados.get("trans"), dados.get("fibras"), dados.get("sodio"),
                     dados.get("vitaminas_json")))
                return cur.lastrowid
    except Exception as ex:
        print(f"[MODEL] salvar_nutricao: {ex}")
        return 0


def carregar_nutricao(entidade_tipo: str, entidade_id: int) -> dict | None:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            row = conn.execute("""
                SELECT por_100g, kcal, kj, carboidratos, acucares,
                       proteinas, gorduras, saturadas, trans, fibras, sodio, vitaminas_json
                FROM nutricao WHERE entidade_tipo=? AND entidade_id=?
            """, (entidade_tipo, entidade_id)).fetchone()
            if not row:
                return None
            cols = ["por_100g","kcal","kj","carboidratos","acucares",
                    "proteinas","gorduras","saturadas","trans","fibras","sodio","vitaminas_json"]
            return dict(zip(cols, row))
    except Exception as ex:
        print(f"[MODEL] carregar_nutricao: {ex}")
        return None


def _criar_tabela_nutricao():
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nutricao (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    entidade_tipo  TEXT NOT NULL,
                    entidade_id    INTEGER NOT NULL,
                    por_100g       REAL DEFAULT 100,
                    kcal           REAL,
                    kj             REAL,
                    carboidratos   REAL,
                    acucares       REAL,
                    proteinas      REAL,
                    gorduras       REAL,
                    saturadas      REAL,
                    trans          REAL,
                    fibras         REAL,
                    sodio          REAL,
                    vitaminas_json TEXT,
                    atualizado_em  TEXT DEFAULT (datetime('now')),
                    UNIQUE(entidade_tipo, entidade_id)
                )
            """)
    except Exception as ex:
        print(f"[MODEL] _criar_tabela_nutricao: {ex}")


# ── Tabela de conversao medidas caseiras → gramas (padrao TACO/IBGE) ──────
_MEDIDAS_GRAMAS: dict[str, float] = {
    "C.Sopa":  15.0,
    "C.Cha":    5.0,
    "Scoop":   30.0,
    "Xicara": 240.0,
    "Porcao": 100.0,
    "Fatia":   30.0,
    "Unidade": 100.0,
    "g":         1.0,
    "kg":     1000.0,
    "ml":        1.0,
    "Litro":  1000.0,
    "Pitada":    0.5,
    "Ramo":      5.0,
}


def _porcao_em_gramas(qtd_str: str, unid: str) -> float:
    """Converte quantidade + unidade em gramas/ml equivalentes."""
    try:
        qtd = float((qtd_str or "1").strip())
    except (ValueError, TypeError):
        qtd = 1.0
    fator = _MEDIDAS_GRAMAS.get(unid, 100.0)
    return qtd * fator


def _nutricao_proporcional(n: dict, gramas: float) -> dict:
    """Retorna valores nutricionais proporcionais a `gramas` a partir de tabela por 100g."""
    if not n:
        return {}
    base = n.get("por_100g") or 100.0
    fator = gramas / base
    campos = ["kcal","kj","carboidratos","acucares","proteinas",
              "gorduras","saturadas","trans","fibras","sodio"]
    return {c: (n[c] * fator if n.get(c) is not None else None) for c in campos}


def calcular_tmb() -> dict:
    """
    Calcula TMB (Taxa Metabolica Basal) pelo metodo Mifflin-St Jeor.
    Retorna {"tmb": float, "peso": float, "altura": float,
             "idade": int, "sexo": str, "completo": bool}
    """
    try:
        from datetime import date as _date
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            row = conn.execute(
                "SELECT peso, altura, data_nasc, sexo FROM perfil_usuario LIMIT 1"
            ).fetchone()
        if not row or not row[0] or not row[1] or not row[2]:
            return {"tmb": None, "completo": False}
        peso, altura, data_nasc, sexo = row
        # calcula idade
        try:
            nasc = _date.fromisoformat(str(data_nasc)[:10])
            hoje = _date.today()
            idade = hoje.year - nasc.year - (
                (hoje.month, hoje.day) < (nasc.month, nasc.day))
        except Exception:
            return {"tmb": None, "completo": False}
        # Mifflin-St Jeor
        base = 10 * float(peso) + 6.25 * float(altura) - 5 * idade
        tmb = base + 5 if str(sexo).lower() in ("m", "masculino", "masc") else base - 161
        return {
            "tmb":     round(tmb, 0),
            "peso":    float(peso),
            "altura":  float(altura),
            "idade":   idade,
            "sexo":    sexo,
            "completo": True,
        }
    except Exception as ex:
        print(f"[MODEL] calcular_tmb: {ex}")
        return {"tmb": None, "completo": False}


# MET (Metabolic Equivalent of Task) por tipo e intensidade
_MET_FISICO = {
    "leve":     2.5,   # alongamento, caminhada lenta
    "moderado": 5.0,   # musculacao, caminhada rapida, bike leve
    "intenso":  9.0,   # corrida, HIIT, natacao rapida
}
_MET_MENTAL = {
    "leve":     1.3,   # leitura casual, reuniao passiva
    "moderado": 1.6,   # estudo, escrita, reuniao ativa
    "intenso":  1.9,   # programacao concentrada, resolucao de problemas complexos
}


def calcular_gasto_item(hora_inicio: str, hora_fim: str,
                        intensidade_fisica: str = None,
                        intensidade_mental: str = None,
                        peso_kg: float = 80.0) -> dict:
    """
    Calcula gasto calorico de um item de atividade/trabalho.
    Retorna {'kcal_gasto': float, 'duracao_min': int, 'met': float}
    """
    try:
        from datetime import datetime as _dt
        fmt = "%H:%M"
        hi = _dt.strptime((hora_inicio or "").strip(), fmt)
        hf = _dt.strptime((hora_fim or "").strip(), fmt)
        duracao_min = (hf - hi).seconds // 60
        if duracao_min <= 0:
            return {}
        duracao_h = duracao_min / 60.0
        met = 0.0
        if intensidade_fisica:
            met = _MET_FISICO.get(intensidade_fisica.lower(), 2.5)
        elif intensidade_mental:
            met = _MET_MENTAL.get(intensidade_mental.lower(), 1.6)
        else:
            met = 1.3
        kcal = met * peso_kg * duracao_h
        return {"kcal_gasto": round(kcal, 1), "duracao_min": duracao_min, "met": met}
    except Exception:
        return {}


def calcular_gasto_template(template_id: int, peso_kg: float = 80.0) -> float:
    """Soma o gasto calorico de todos os itens de atividade/trabalho de um template."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            rows = conn.execute("""
                SELECT im.hora_inicio, im.hora_fim,
                       im.intensidade_fisica, im.intensidade_mental
                FROM itens_momento im
                JOIN momentos_rotina mr ON mr.id = im.momento_id
                WHERE mr.template_id = ?
                  AND (im.hora_inicio IS NOT NULL AND im.hora_fim IS NOT NULL)
            """, (template_id,)).fetchall()
        total = 0.0
        for hi, hf, if_, im in rows:
            r = calcular_gasto_item(hi, hf, if_, im, peso_kg)
            total += r.get("kcal_gasto", 0.0)
        return round(total, 1)
    except Exception:
        return 0.0


def _somar_nutricao(lista: list[dict]) -> dict:
    """Soma uma lista de dicts nutricionais, ignorando None."""
    resultado: dict[str, float] = {}
    campos = ["kcal","kj","carboidratos","acucares","proteinas",
              "gorduras","saturadas","trans","fibras","sodio"]
    for n in lista:
        for c in campos:
            if n.get(c) is not None:
                resultado[c] = resultado.get(c, 0.0) + n[c]
    return resultado


def calcular_nutricao_item(item_id: int) -> dict:
    """
    Calcula a nutricao total de um item da rotina somando seus ingredientes.
    Ingrediente simples: usa tabela nutricao(entidade_tipo='ingrediente_item').
    Ingrediente receita: usa tabela nutricao(entidade_tipo='receita') proporcional a porcao.
    Retorna dict com campos nutricionais ou {} se sem dados.
    """
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            ings = conn.execute("""
                SELECT id, tipo, descricao, sub_receita_id, quantidade, unidade,
                       calorias, proteinas, peso_unitario_g
                FROM item_ingredientes WHERE item_id=?
            """, (item_id,)).fetchall()

        partes = []
        for iid, tipo, desc, sub_rid, qty, unid, cal_manual, prot_manual, peso_unit in ings:
            # Se unidade=Unidade e tem peso_unitario_g, usa peso real
            if (unid or "").strip() == "Unidade" and peso_unit:
                try:
                    gramas = float(qty or 1) * peso_unit
                except (TypeError, ValueError):
                    gramas = peso_unit
            else:
                gramas = _porcao_em_gramas(qty, unid or "g")

            if tipo == "receita" and sub_rid:
                n = carregar_nutricao("receita", sub_rid)
                if n:
                    partes.append(_nutricao_proporcional(n, gramas))
                elif cal_manual:
                    partes.append({"kcal": cal_manual * gramas / 100,
                                   "proteinas": (prot_manual or 0) * gramas / 100})
            else:
                n = carregar_nutricao("ingrediente_item", iid)
                if n:
                    partes.append(_nutricao_proporcional(n, gramas))
                elif cal_manual:
                    partes.append({"kcal": cal_manual * gramas / 100,
                                   "proteinas": (prot_manual or 0) * gramas / 100})
        return _somar_nutricao(partes)
    except Exception as ex:
        print(f"[MODEL] calcular_nutricao_item: {ex}")
        return {}


def calcular_nutricao_momento(momento_id: int) -> dict:
    """Soma a nutricao de todos os itens de um momento da rotina."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            ids = [r[0] for r in conn.execute(
                "SELECT id FROM itens_momento WHERE momento_id=?",
                (momento_id,)).fetchall()]
        return _somar_nutricao([calcular_nutricao_item(i) for i in ids])
    except Exception as ex:
        print(f"[MODEL] calcular_nutricao_momento: {ex}")
        return {}


# Mapeamento de nomes variantes → chave canonica
_VITS_CANON = {
    # vitaminas
    "vit a": ("vitamina_a", "mcg"), "vitamina a": ("vitamina_a", "mcg"),
    "vitamina_a": ("vitamina_a", "mcg"), "vitamina_a_mcg": ("vitamina_a", "mcg"),
    "retinol": ("vitamina_a", "mcg"),
    "vit b1": ("vitamina_b1", "mg"), "vitamina b1": ("vitamina_b1", "mg"),
    "tiamina": ("vitamina_b1", "mg"), "tiamina_mg": ("vitamina_b1", "mg"),
    "vit b2": ("vitamina_b2", "mg"), "vitamina b2": ("vitamina_b2", "mg"),
    "riboflavina": ("vitamina_b2", "mg"),
    "vit b2 (riboflavina)": ("vitamina_b2", "mg"), "vitamina_b2_mg": ("vitamina_b2", "mg"),
    "vit b3": ("vitamina_b3", "mg"), "vitamina b3": ("vitamina_b3", "mg"),
    "niacina": ("vitamina_b3", "mg"), "niacina_mg": ("vitamina_b3", "mg"),
    "vit b6": ("vitamina_b6", "mg"), "vitamina b6": ("vitamina_b6", "mg"),
    "vitamina_b6_mg": ("vitamina_b6", "mg"), "vitamina_b6": ("vitamina_b6", "mg"),
    "vit b9 (folato)": ("folato", "mcg"), "folato": ("folato", "mcg"),
    "folato_mcg": ("folato", "mcg"), "acido folico": ("folato", "mcg"),
    "vit b12": ("vitamina_b12", "mcg"), "vitamina b12": ("vitamina_b12", "mcg"),
    "vitamina_b12": ("vitamina_b12", "mcg"), "vitamina_b12_mcg": ("vitamina_b12", "mcg"),
    "vit c": ("vitamina_c", "mg"), "vitamina c": ("vitamina_c", "mg"),
    "vitamina_c_mg": ("vitamina_c", "mg"),
    "vit d": ("vitamina_d", "mcg"), "vitamina d": ("vitamina_d", "mcg"),
    "vitamina_d": ("vitamina_d", "mcg"), "vitamina_d_mcg": ("vitamina_d", "mcg"),
    "vit e": ("vitamina_e", "mg"), "vitamina e": ("vitamina_e", "mg"),
    "vitamina_e_mg": ("vitamina_e", "mg"),
    "vit k": ("vitamina_k", "mcg"), "vitamina k": ("vitamina_k", "mcg"),
    "vitamina_k_mcg": ("vitamina_k", "mcg"),
    "colina": ("colina", "mg"),
    "omega-3": ("omega3", "mg"), "omega3": ("omega3", "mg"),
    # minerais
    "calcio": ("calcio", "mg"), "cálcio": ("calcio", "mg"),
    "calcio_mg": ("calcio", "mg"),
    "ferro": ("ferro", "mg"), "ferro_mg": ("ferro", "mg"),
    "magnesio": ("magnesio", "mg"), "magnésio": ("magnesio", "mg"),
    "magnesio_mg": ("magnesio", "mg"),
    "fosforo": ("fosforo", "mg"), "fósforo": ("fosforo", "mg"),
    "fosforo_mg": ("fosforo", "mg"),
    "potassio": ("potassio", "mg"), "potássio": ("potassio", "mg"),
    "potassio_mg": ("potassio", "mg"),
    "zinco": ("zinco", "mg"), "zinco_mg": ("zinco", "mg"),
    "sodio": ("sodio", "mg"), "sódio": ("sodio", "mg"), "sodio_mg": ("sodio", "mg"),
    "selenio": ("selenio", "mcg"), "selênio": ("selenio", "mcg"),
    "selenio_mcg": ("selenio", "mcg"),
    "cobre": ("cobre", "mg"), "cobre_mg": ("cobre", "mg"),
    "manganes": ("manganes", "mg"), "manganês": ("manganes", "mg"),
    "manganes_mg": ("manganes", "mg"),
}

_VITAMINAS_KEYS = {"vitamina_a","vitamina_b1","vitamina_b2","vitamina_b3","vitamina_b6",
                   "folato","vitamina_b12","vitamina_c","vitamina_d","vitamina_e",
                   "vitamina_k","colina","omega3"}
_MINERAIS_KEYS  = {"calcio","ferro","magnesio","fosforo","potassio","zinco",
                   "sodio","selenio","cobre","manganes"}

_VITS_LABEL = {
    "vitamina_a": "Vitamina A", "vitamina_b1": "Vitamina B1",
    "vitamina_b2": "Vitamina B2", "vitamina_b3": "Vitamina B3",
    "vitamina_b6": "Vitamina B6", "folato": "Folato (B9)",
    "vitamina_b12": "Vitamina B12", "vitamina_c": "Vitamina C",
    "vitamina_d": "Vitamina D", "vitamina_e": "Vitamina E",
    "vitamina_k": "Vitamina K", "colina": "Colina", "omega3": "Ômega-3",
    "calcio": "Cálcio", "ferro": "Ferro", "magnesio": "Magnésio",
    "fosforo": "Fósforo", "potassio": "Potássio", "zinco": "Zinco",
    "sodio": "Sódio", "selenio": "Selênio", "cobre": "Cobre",
    "manganes": "Manganês",
}


def _parse_vit_valor(v) -> float:
    """Extrai numero de '4.2mg', '98', 2.5 etc."""
    import re as _re
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", ".")
    m = _re.match(r"[-+]?(\d+\.?\d*)", s)
    return float(m.group(1)) if m else 0.0


def calcular_vitaminas_minerais_rotina() -> tuple[dict, dict]:
    """
    Soma vitaminas_json de todos os ingredientes dos templates ativos.
    Retorna (vitaminas_dict, minerais_dict) — chaves canonicas, valores float.
    ex: ({"vitamina_d": 3.2, "vitamina_b12": 2.4}, {"calcio": 900.0, "ferro": 18.5})
    """
    import json as _json
    totais: dict[str, float] = {}
    unids:  dict[str, str]   = {}
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            # ingredientes simples
            rows_ing = conn.execute("""
                SELECT n.vitaminas_json
                FROM item_ingredientes ii
                JOIN itens_momento im ON im.id = ii.item_id
                JOIN momentos_rotina mr ON mr.id = im.momento_id
                JOIN rotinas_templates t ON t.id = mr.template_id
                JOIN nutricao n ON n.entidade_tipo='ingrediente_item' AND n.entidade_id=ii.id
                WHERE t.ativo=1 AND n.vitaminas_json IS NOT NULL AND n.vitaminas_json != ''
            """).fetchall()
            # receitas como ingrediente
            rows_rec = conn.execute("""
                SELECT n.vitaminas_json
                FROM item_ingredientes ii
                JOIN itens_momento im ON im.id = ii.item_id
                JOIN momentos_rotina mr ON mr.id = im.momento_id
                JOIN rotinas_templates t ON t.id = mr.template_id
                JOIN nutricao n ON n.entidade_tipo='receita' AND n.entidade_id=ii.sub_receita_id
                WHERE t.ativo=1 AND ii.sub_receita_id IS NOT NULL
                  AND n.vitaminas_json IS NOT NULL AND n.vitaminas_json != ''
            """).fetchall()

        for (vjson,) in rows_ing + rows_rec:
            try:
                d = _json.loads(vjson)
            except Exception:
                continue
            for k, v in d.items():
                canon = _VITS_CANON.get(k.lower().strip())
                if not canon:
                    continue
                chave, unid = canon
                totais[chave] = totais.get(chave, 0.0) + _parse_vit_valor(v)
                unids[chave]  = unid
    except Exception as ex:
        print(f"[MODEL] calcular_vitaminas_minerais_rotina: {ex}")

    vitaminas = {k: (round(totais[k], 1), unids.get(k, ""))
                 for k in sorted(totais) if k in _VITAMINAS_KEYS}
    minerais  = {k: (round(totais[k], 1), unids.get(k, ""))
                 for k in sorted(totais) if k in _MINERAIS_KEYS}
    return vitaminas, minerais


# RDA (Ingestão Diária Recomendada) — homem adulto 50+, fontes IOM/DRI 2023
# formato: chave_canonica → (rda, unidade, descricao)
_RDA = {
    # vitaminas
    "vitamina_a":   (900,  "mcg", "Vitamina A"),
    "vitamina_b1":  (1.2,  "mg",  "Vitamina B1"),
    "vitamina_b2":  (1.3,  "mg",  "Vitamina B2"),
    "vitamina_b3":  (16.0, "mg",  "Vitamina B3"),
    "vitamina_b6":  (1.7,  "mg",  "Vitamina B6"),
    "folato":       (400,  "mcg", "Folato (B9)"),
    "vitamina_b12": (2.4,  "mcg", "Vitamina B12"),
    "vitamina_c":   (90.0, "mg",  "Vitamina C"),
    "vitamina_d":   (15.0, "mcg", "Vitamina D"),
    "vitamina_e":   (15.0, "mg",  "Vitamina E"),
    "vitamina_k":   (120,  "mcg", "Vitamina K"),
    "colina":       (550,  "mg",  "Colina"),
    "omega3":       (1600, "mg",  "Ômega-3"),
    # minerais
    "calcio":    (1200, "mg",  "Cálcio"),
    "ferro":     (8.0,  "mg",  "Ferro"),
    "magnesio":  (420,  "mg",  "Magnésio"),
    "fosforo":   (700,  "mg",  "Fósforo"),
    "potassio":  (4700, "mg",  "Potássio"),
    "zinco":     (11.0, "mg",  "Zinco"),
    "sodio":     (1300, "mg",  "Sódio"),
    "selenio":   (55.0, "mcg", "Selênio"),
    "cobre":     (0.9,  "mg",  "Cobre"),
    "manganes":  (2.3,  "mg",  "Manganês"),
}

# mapa: substring do nome_oficial do exame → chave_canonica da dieta
_EXAME_PARA_NUTRIENTE = {
    "vitamina a":       "vitamina_a",
    "retinol":          "vitamina_a",
    "vitamina b12":     "vitamina_b12",
    "vitamina b1":      "vitamina_b1",
    "vitamina b2":      "vitamina_b2",
    "vitamina b3":      "vitamina_b3",
    "vitamina b6":      "vitamina_b6",
    "acido folico":     "folato",
    "ácido fólico":     "folato",
    "folato":           "folato",
    "vitamina c":       "vitamina_c",
    "vitamina d":       "vitamina_d",
    "25-hidroxi":       "vitamina_d",
    "vitamina e":       "vitamina_e",
    "vitamina k":       "vitamina_k",
    "ferro serico":     "ferro",
    "ferro sérico":     "ferro",
    "ferritina":        "ferro",
    "magnesio":         "magnesio",
    "magnésio":         "magnesio",
    "calcio":           "calcio",
    "cálcio":           "calcio",
    "zinco":            "zinco",
    "selenio":          "selenio",
    "selênio":          "selenio",
    "cobre":            "cobre",
    "manganes":         "manganes",
    "manganês":         "manganes",
    "potassio":         "potassio",
    "potássio":         "potassio",
    "fosforo":          "fosforo",
    "fósforo":          "fosforo",
}


def ingestao_diaria_nutriente(nome_oficial_exame: str) -> dict | None:
    """
    Dado o nome_oficial de um exame, retorna a ingestao diaria do nutriente
    correspondente nas rotinas ativas, comparando com a RDA.
    Retorna None se nao houver correspondencia.
    Retorna dict:
      {
        "nutriente": "ferro",
        "label": "Ferro",
        "ingestao": 19.0, "unidade": "mg",
        "rda": 8.0,
        "pct_rda": 237.5,   # % da RDA atingida
        "status": "adequada"|"insuficiente"|"excessiva",
        "msg": "Ingere 19mg/dia (RDA: 8mg) — problema pode ser de absorção"
      }
    """
    import unicodedata as _ud
    def _norm(s):
        return _ud.normalize("NFD", s.lower()).encode("ascii","ignore").decode()
    n = _norm(nome_oficial_exame or "")
    chave = None
    for substr, ck in _EXAME_PARA_NUTRIENTE.items():
        if _norm(substr) in n:
            chave = ck
            break
    if not chave:
        return None

    vits, mins = calcular_vitaminas_minerais_rotina()
    dados_dieta = {**vits, **mins}
    if chave not in dados_dieta:
        return None

    val, unid = dados_dieta[chave]
    rda_info = _RDA.get(chave)
    if not rda_info:
        return None

    rda, rda_unid, label = rda_info
    pct = round(val / rda * 100, 0) if rda else 0

    # verificar se ha suplemento cadastrado com este nutriente
    _SUPL_KEYWORDS = {
        "vitamina_d":   ["vitamina d","colecalciferol","vit d","vitd"],
        "vitamina_b12": ["vitamina b12","b12","cobalamina","cobalanina","cianocobalamina","metilcobalamina","cobi"],
        "vitamina_c":   ["vitamina c","ascorbico","ascorbate"],
        "vitamina_e":   ["vitamina e","tocoferol"],
        "vitamina_a":   ["vitamina a","retinol"],
        "folato":       ["acido folico","folato","folate"],
        "ferro":        ["ferro","sulfato ferroso","fumarato ferroso"],
        "magnesio":     ["magnesio","magnésio","citrato de magnesio"],
        "calcio":       ["calcio","cálcio","carbonato de calcio","citrato de calcio"],
        "zinco":        ["zinco","quelado"],
        "omega3":       ["omega","omacor","epa","dha"],
        "selenio":      ["selenio","selenometionina"],
    }
    tem_suplemento = False
    nomes_supl = []
    try:
        kws = _SUPL_KEYWORDS.get(chave, [])
        if kws:
            with sqlite3.connect(DB_PATH, timeout=5) as _cs:
                rem = _cs.execute("""
                    SELECT nome, dosagem FROM remedios
                    WHERE ativo=1
                    AND (tipo='suplemento' OR tipo='remedio')
                """).fetchall()
            for rnome, rdos in rem:
                rn = _norm((rnome or "") + " " + (rdos or ""))
                if any(_norm(kw) in rn for kw in kws):
                    tem_suplemento = True
                    nomes_supl.append(rnome)
            # verificar tambem itens de rotina tipo remedio com esse nutriente
            with sqlite3.connect(DB_PATH, timeout=5) as _cs:
                rot = _cs.execute("""
                    SELECT im.descricao FROM itens_momento im
                    JOIN momentos_rotina mr ON mr.id = im.momento_id
                    JOIN rotinas_templates t ON t.id = mr.template_id
                    WHERE t.ativo=1 AND im.tipo IN ('remedio','suplemento','medicamento')
                """).fetchall()
            for (rdesc,) in rot:
                rn = _norm(rdesc or "")
                if any(_norm(kw) in rn for kw in kws):
                    tem_suplemento = True
                    if rdesc not in nomes_supl:
                        nomes_supl.append(rdesc)
    except Exception:
        pass

    if pct >= 150:
        status = "excessiva"
        msg = f"Ingere {val}{unid}/dia (RDA: {rda}{rda_unid}) — excesso na dieta"
    elif pct >= 80:
        status = "adequada"
        msg = f"Ingere {val}{unid}/dia (RDA: {rda}{rda_unid}) — ingestão adequada"
    else:
        status = "insuficiente"
        msg = f"Ingere {val}{unid}/dia (RDA: {rda}{rda_unid}) — só dieta, sem suplemento cadastrado"

    return {
        "nutriente": chave, "label": label,
        "ingestao": val, "unidade": unid,
        "rda": rda, "rda_unid": rda_unid,
        "pct_rda": pct, "status": status, "msg": msg,
        "tem_suplemento": tem_suplemento,
        "nomes_suplemento": nomes_supl,
    }


def _migrar_ingrediente_peso_unitario():
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            cols = [r[1] for r in conn.execute(
                "PRAGMA table_info(item_ingredientes)").fetchall()]
            if "peso_unitario_g" not in cols:
                conn.execute(
                    "ALTER TABLE item_ingredientes ADD COLUMN peso_unitario_g REAL")
    except Exception as ex:
        print(f"[MODEL] _migrar_ingrediente_peso_unitario: {ex}")


def _migrar_receitas_porcao():
    """Adiciona colunas porcao_qtd e porcao_unid em receitas se nao existirem."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(receitas)").fetchall()]
            if "porcao_qtd" not in cols:
                conn.execute("ALTER TABLE receitas ADD COLUMN porcao_qtd TEXT")
            if "porcao_unid" not in cols:
                conn.execute("ALTER TABLE receitas ADD COLUMN porcao_unid TEXT")
    except Exception as ex:
        print(f"[MODEL] _migrar_receitas_porcao: {ex}")


# ══════════════════════════════════════════════════════════════
# MARCADORES — leituras manuais / BLE
# ══════════════════════════════════════════════════════════════

def listar_leituras_marcador(termos: list[str], limite: int = 200) -> list[dict]:
    """Retorna leituras de marcadores_leituras que contenham qualquer dos termos."""
    condicoes = " OR ".join(["LOWER(parametro) LIKE ?" for _ in termos])
    params    = [f"%{t.lower()}%" for t in termos]
    params.append(limite)
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cur = conn.execute(f"""
                SELECT id, parametro, valor, valor_txt, unidade, referencia,
                       data_medicao, hora_medicao, fonte, observacoes
                FROM marcadores_leituras
                WHERE {condicoes}
                ORDER BY data_medicao DESC, hora_medicao DESC
                LIMIT ?
            """, params)
            cols = ["id","parametro","valor","valor_txt","unidade","referencia",
                    "data_medicao","hora_medicao","fonte","observacoes"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as ex:
        print(f"[MODEL] listar_leituras_marcador: {ex}")
        return []


def salvar_leitura_marcador(dados: dict) -> int:
    """Insere ou atualiza uma leitura em marcadores_leituras. Retorna o id."""
    try:
        _dm = normalizar_data(dados.get("data_medicao"))
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            if dados.get("id"):
                conn.execute("""
                    UPDATE marcadores_leituras
                    SET parametro=?, categoria=?, valor=?, valor_txt=?,
                        unidade=?, referencia=?, data_medicao=?, hora_medicao=?,
                        fonte=?, observacoes=?
                    WHERE id=?
                """, (dados["parametro"], dados.get("categoria"),
                      dados.get("valor"), dados.get("valor_txt"),
                      dados.get("unidade"), dados.get("referencia"),
                      _dm, dados.get("hora_medicao"),
                      dados.get("fonte","manual"), dados.get("observacoes"),
                      dados["id"]))
                return dados["id"]
            else:
                cur = conn.execute("""
                    INSERT INTO marcadores_leituras
                        (parametro, categoria, valor, valor_txt, unidade,
                         referencia, data_medicao, hora_medicao, fonte, observacoes)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (dados["parametro"], dados.get("categoria"),
                      dados.get("valor"), dados.get("valor_txt"),
                      dados.get("unidade","mg/dL"), dados.get("referencia"),
                      _dm, dados.get("hora_medicao"),
                      dados.get("fonte","manual"), dados.get("observacoes")))
                _notify()
                return cur.lastrowid
    except Exception as ex:
        print(f"[MODEL] salvar_leitura_marcador: {ex}")
        return 0


def excluir_leitura_marcador(leitura_id: int) -> None:
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute("DELETE FROM marcadores_leituras WHERE id=?", (leitura_id,))
            _notify()
    except Exception as ex:
        print(f"[MODEL] excluir_leitura_marcador: {ex}")


def listar_exames_glicemia(termos: list[str], limite: int = 100) -> list[dict]:
    """Retorna resultados de lab vinculados a glicemia.
    Busca pelo nome_oficial/categoria do exame_padrao OU pelo parametro direto em exame_resultados.
    Usa LEFT JOIN para incluir resultados sem exame_padrao_id.
    """
    like = [f"%{t.lower()}%" for t in termos]
    conds_nome  = " OR ".join(["LOWER(ep.nome_oficial) LIKE ?" for _ in termos])
    conds_cat   = " OR ".join(["LOWER(ep.categoria)    LIKE ?" for _ in termos])
    conds_param = " OR ".join(["LOWER(r.parametro)     LIKE ?" for _ in termos])
    params = like + like + like + [limite]
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cur = conn.execute(f"""
                SELECT r.id, r.exame_padrao_id,
                       COALESCE(ep.nome_oficial, r.parametro) AS parametro,
                       r.valor, r.unidade, r.referencia, r.nivel_interpretacao,
                       e.data_exame, e.arquivo_origem, e.laboratorio,
                       e.drive_file_id, e.id AS exame_id
                FROM exame_resultados r
                JOIN exames e ON r.exame_id = e.id
                LEFT JOIN exames_padrao ep ON r.exame_padrao_id = ep.id
                WHERE ({conds_nome} OR {conds_cat} OR {conds_param})
                  AND r.valor IS NOT NULL AND r.valor != ''
                ORDER BY e.data_exame DESC
                LIMIT ?
            """, params)
            cols = ["id","exame_padrao_id","parametro","valor","unidade",
                    "referencia","nivel","data_exame","arquivo_origem",
                    "laboratorio","drive_id","exame_id"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as ex:
        print(f"[MODEL] listar_exames_glicemia: {ex}")
        return []


# ══════════════════════════════════════════════════════════════
# ÁGUA DIÁRIA
# ══════════════════════════════════════════════════════════════

def registrar_agua(ml: int, data: str = None) -> int:
    """Registra um copo/dose de água em marcadores_leituras. Retorna id."""
    import datetime as _dt
    data = data or _dt.date.today().isoformat()
    dados = {
        "parametro":    "Agua Ingerida",
        "categoria":    "Hidratacao",
        "valor":        float(ml),
        "valor_txt":    str(ml),
        "unidade":      "ml",
        "referencia":   "2500",
        "data_medicao": data,
        "fonte":        "manual",
        "observacoes":  "[agua]",
    }
    return salvar_leitura_marcador(dados)


def total_agua_dia(data: str = None) -> int:
    """Retorna o total de ml de água registrados em uma data."""
    import datetime as _dt
    data = data or _dt.date.today().isoformat()
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            row = conn.execute("""
                SELECT COALESCE(SUM(valor), 0)
                FROM marcadores_leituras
                WHERE LOWER(parametro) LIKE '%agua%'
                  AND LOWER(observacoes) LIKE '%[agua]%'
                  AND data_medicao = ?
            """, (data,)).fetchone()
            return int(row[0]) if row else 0
    except Exception:
        return 0


def definir_total_agua_dia(ml: int, data: str = None) -> None:
    """Substitui todos os registros de agua do dia por um unico com o total informado."""
    import datetime as _dt
    data = data or _dt.date.today().isoformat()
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute("""
                DELETE FROM marcadores_leituras
                WHERE LOWER(parametro) LIKE '%agua%'
                  AND LOWER(observacoes) LIKE '%[agua]%'
                  AND data_medicao = ?
            """, (data,))
        _notify()
    except Exception:
        pass
    if ml > 0:
        registrar_agua(ml, data)


def meta_agua_template() -> int:
    """Retorna a meta diária de água do template padrão (ml). Padrão 2500."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            row = conn.execute("""
                SELECT meta_agua_ml FROM rotinas_templates
                WHERE padrao = 1 AND ativo = 1 LIMIT 1
            """).fetchone()
            if row and row[0]:
                return int(row[0])
    except Exception:
        pass
    return 2500


def salvar_meta_agua(ml: int, template_id: int = None):
    """Salva meta de água no template padrão ou no template_id dado."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            if template_id:
                conn.execute("UPDATE rotinas_templates SET meta_agua_ml=? WHERE id=?",
                             (ml, template_id))
            else:
                conn.execute("""UPDATE rotinas_templates SET meta_agua_ml=?
                                WHERE padrao=1 AND ativo=1""", (ml,))
            conn.commit()
    except Exception as ex:
        print(f"[MODEL] salvar_meta_agua: {ex}")


# ══════════════════════════════════════════════════════════════
# DESAFIOS DE SUSPENSÃO
# ══════════════════════════════════════════════════════════════

def _migrar_desafios():
    """Cria tabela desafios_ativos e adiciona meta_agua_ml em rotinas_templates."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS desafios_ativos (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome            TEXT NOT NULL,
                    tipo            TEXT DEFAULT 'suspensao',
                    descricao       TEXT,
                    motivo_marcador TEXT,
                    data_inicio     TEXT NOT NULL,
                    data_fim        TEXT,
                    ativo           INTEGER DEFAULT 1,
                    criado_em       TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_desafios_ativo
                    ON desafios_ativos(ativo, data_inicio DESC);
            """)
            # migração segura
            for sql in [
                "ALTER TABLE rotinas_templates ADD COLUMN meta_agua_ml INTEGER DEFAULT 2500",
            ]:
                try: conn.execute(sql)
                except Exception: pass
            conn.commit()
    except Exception as ex:
        print(f"[MODEL] _migrar_desafios: {ex}")


def listar_desafios_ativos() -> list[dict]:
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM desafios_ativos
                WHERE ativo = 1
                ORDER BY data_inicio DESC
            """).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def salvar_desafio(dados: dict) -> int:
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            if dados.get("id"):
                conn.execute("""
                    UPDATE desafios_ativos
                    SET nome=?, tipo=?, descricao=?, motivo_marcador=?,
                        data_inicio=?, data_fim=?, ativo=?
                    WHERE id=?
                """, (dados["nome"], dados.get("tipo","suspensao"),
                      dados.get("descricao"), dados.get("motivo_marcador"),
                      dados["data_inicio"], dados.get("data_fim"),
                      int(dados.get("ativo", 1)), dados["id"]))
                conn.commit()
                return dados["id"]
            else:
                cur = conn.execute("""
                    INSERT INTO desafios_ativos
                        (nome, tipo, descricao, motivo_marcador, data_inicio, data_fim, ativo)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (dados["nome"], dados.get("tipo","suspensao"),
                      dados.get("descricao"), dados.get("motivo_marcador"),
                      dados["data_inicio"], dados.get("data_fim")))
                conn.commit()
                return cur.lastrowid
    except Exception as ex:
        print(f"[MODEL] salvar_desafio: {ex}")
        return 0


def encerrar_desafio(desafio_id: int):
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute("UPDATE desafios_ativos SET ativo=0 WHERE id=?",
                         (desafio_id,))
            conn.commit()
    except Exception as ex:
        print(f"[MODEL] encerrar_desafio: {ex}")


# ══════════════════════════════════════════════════════════════
# HELPERS — INTERNACOES
# ══════════════════════════════════════════════════════════════

def listar_internacoes() -> list[dict]:
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cur = conn.execute("""
                SELECT i.id, i.hospital, i.data_entrada, i.data_saida, i.tipo,
                       i.motivo, i.cid_entrada, i.diagnostico_saida, i.cid_saida,
                       i.observacoes, i.medico_id, i.clinica_id, i.criado_em,
                       i.documento_local, m.nome AS medico_nome,
                       i.cidade, i.uf, i.objetivo,
                       i.drive_file_id, i.drive_link, i.fonte_dados, i.gatilho,
                       i.medico_responsavel
                FROM internacoes i
                LEFT JOIN medicos m ON m.id = i.medico_id
                ORDER BY i.data_entrada DESC, i.criado_em DESC
            """)
            cols = ["id","hospital","data_entrada","data_saida","tipo","motivo",
                    "cid_entrada","diagnostico_saida","cid_saida","observacoes",
                    "medico_id","clinica_id","criado_em","documento_local","medico_nome",
                    "cidade","uf","objetivo","drive_file_id","drive_link","fonte_dados","gatilho",
                    "medico_responsavel"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as ex:
        print(f"[MODEL] listar_internacoes: {ex}")
        return []


def listar_marcadores_internacao(internacao_id: int,
                                  data_entrada: str, data_saida: str) -> list[dict]:
    """Retorna marcadores vinculados a uma internacao.
    Prioriza registros com internacao_id explícito; fallback por intervalo de datas."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            data_fim = data_saida or _datetime.date.today().isoformat()
            rows = conn.execute("""
                SELECT id, parametro, categoria, valor, valor_txt, unidade, referencia,
                       data_medicao, hora_medicao, fonte, observacoes
                FROM marcadores_leituras
                WHERE internacao_id = ?
                   OR (internacao_id IS NULL AND data_medicao BETWEEN ? AND ?)
                ORDER BY data_medicao ASC, hora_medicao ASC
            """, (internacao_id, data_entrada, data_fim)).fetchall()
            cols = ["id","parametro","categoria","valor","valor_txt","unidade","referencia",
                    "data_medicao","hora_medicao","fonte","observacoes"]
            return [dict(zip(cols, r)) for r in rows]
    except Exception as ex:
        print(f"[MODEL] listar_marcadores_internacao: {ex}")
        return []


def buscar_internacao_similar(hospital: str, data_entrada: str,
                              cidade: str = "", uf: str = "") -> list[dict]:
    """Retorna internacoes com mesmo hospital (fuzzy) e mesma data de entrada.

    Estrategia em camadas para tolerar variacoes de nome entre reprocessamentos:
      1. Primeiros 6 chars do hospital (ex: "SAMED" cobre "SAMEDIL..." e "SAMEDIL-SERVICOS...")
      2. Se nao achar: mesma data + mesma cidade + mesmo UF (quando preenchidos)
    """
    import unicodedata, re as _re

    def _norm6(s: str) -> str:
        s = unicodedata.normalize("NFKD", (s or "")).encode("ascii", "ignore").decode()
        s = _re.sub(r"[^a-z0-9]+", "", s.lower())
        return s[:6]

    d = normalizar_data(data_entrada)
    cols = ["id","hospital","data_entrada","data_saida","motivo","objetivo","cidade","uf"]
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            # camada 1: data + primeiros 6 chars normalizados do hospital
            rows = conn.execute(
                "SELECT id,hospital,data_entrada,data_saida,motivo,objetivo,cidade,uf "
                "FROM internacoes WHERE data_entrada = ?", (d,)
            ).fetchall()
            h6 = _norm6(hospital)
            matches = [r for r in rows if _norm6(r[1])[:6] == h6]
            if matches:
                return [dict(zip(cols, r)) for r in matches]
            # camada 2: mesma data + cidade + uf quando informados
            if cidade and uf:
                matches2 = [
                    r for r in rows
                    if (r[6] or "").strip().lower() == cidade.strip().lower()
                    and (r[7] or "").strip().upper() == uf.strip().upper()
                ]
                if matches2:
                    return [dict(zip(cols, r)) for r in matches2]
        return []
    except Exception as ex:
        print(f"[MODEL] buscar_internacao_similar: {ex}")
        return []


def buscar_exame_similar(tipo_exame: str, data_exame: str, laboratorio: str = "") -> bool:
    """Retorna True se ja existe exame com mesmo tipo/data/laboratorio."""
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            row = conn.execute("""
                SELECT id FROM exames
                WHERE LOWER(tipo_exame) = ? AND data_exame = ?
                  AND LOWER(COALESCE(laboratorio,'')) = ?
            """, (tipo_exame.lower(), normalizar_data(data_exame),
                  (laboratorio or "").lower())).fetchone()
            return row is not None
    except Exception as ex:
        print(f"[MODEL] buscar_exame_similar: {ex}")
        return False


def listar_exames_internacao(internacao_id: int) -> list[dict]:
    """Retorna exames vinculados a uma internacao, ordenados por data."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            rows = conn.execute("""
                SELECT id, tipo_exame, data_exame, laboratorio, medico_solicit, status,
                       drive_file_id, resultado_texto
                FROM exames WHERE internacao_id = ? ORDER BY data_exame DESC
            """, (internacao_id,)).fetchall()
        cols = ["id","tipo_exame","data_exame","laboratorio","medico_solicit","status",
                "drive_file_id","resultado_texto"]
        return [dict(zip(cols, r)) for r in rows]
    except Exception as ex:
        print(f"[MODEL] listar_exames_internacao: {ex}")
        return []


def vincular_laudo_exame(exame_id: int, drive_file_id: str, arquivo_local: str = None) -> bool:
    """Salva drive_file_id (laudo) no registro de exame. Retorna True se OK."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute(
                "UPDATE exames SET drive_file_id=? WHERE id=?",
                (drive_file_id, exame_id)
            )
        return True
    except Exception as ex:
        print(f"[MODEL] vincular_laudo_exame: {ex}")
        return False


def listar_diagnosticos_internacao(internacao_id: int) -> list[dict]:
    """Retorna diagnosticos estruturados vinculados a uma internacao."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            rows = conn.execute("""
                SELECT id, internacao_id, cid, descricao, tipo, certeza, fonte, criado_em
                FROM diagnosticos_internacao
                WHERE internacao_id = ?
                ORDER BY tipo DESC, criado_em ASC
            """, (internacao_id,)).fetchall()
        cols = ["id","internacao_id","cid","descricao","tipo","certeza","fonte","criado_em"]
        return [dict(zip(cols, r)) for r in rows]
    except Exception as ex:
        print(f"[MODEL] listar_diagnosticos_internacao: {ex}")
        return []


def salvar_diagnostico_internacao(dados: dict) -> int:
    """Cria ou atualiza um diagnostico de internacao. Retorna id."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            did = dados.get("id")
            if did:
                conn.execute("""
                    UPDATE diagnosticos_internacao
                    SET cid=?, descricao=?, tipo=?, certeza=?, fonte=?
                    WHERE id=?
                """, (
                    dados.get("cid"), dados.get("descricao"),
                    dados.get("tipo","saida"), dados.get("certeza","confirmado"),
                    dados.get("fonte","manual"), did
                ))
                return did
            else:
                cur = conn.execute("""
                    INSERT INTO diagnosticos_internacao
                    (internacao_id, cid, descricao, tipo, certeza, fonte)
                    VALUES (?,?,?,?,?,?)
                """, (
                    dados["internacao_id"], dados.get("cid"), dados.get("descricao"),
                    dados.get("tipo","saida"), dados.get("certeza","confirmado"),
                    dados.get("fonte","manual")
                ))
                return cur.lastrowid
    except Exception as ex:
        print(f"[MODEL] salvar_diagnostico_internacao: {ex}")
        return 0


def excluir_diagnostico_internacao(diagnostico_id: int) -> bool:
    """Remove um diagnostico de internacao."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute(
                "DELETE FROM diagnosticos_internacao WHERE id=?", (diagnostico_id,))
        return True
    except Exception as ex:
        print(f"[MODEL] excluir_diagnostico_internacao: {ex}")
        return False


def listar_dados_brutos_internacao(internacao_id: int) -> list[dict]:
    """Retorna dados brutos/nao-classificados vinculados a uma internacao."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            rows = conn.execute("""
                SELECT id, internacao_id, categoria, conteudo, pagina_origem, fonte, criado_em
                FROM internacao_dados_brutos
                WHERE internacao_id = ?
                ORDER BY pagina_origem ASC, criado_em ASC
            """, (internacao_id,)).fetchall()
        cols = ["id","internacao_id","categoria","conteudo","pagina_origem","fonte","criado_em"]
        return [dict(zip(cols, r)) for r in rows]
    except Exception as ex:
        print(f"[MODEL] listar_dados_brutos_internacao: {ex}")
        return []


def salvar_dado_bruto_internacao(dados: dict) -> int:
    """Grava dado bruto vinculado a internacao. Retorna id."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            did = dados.get("id")
            if did:
                conn.execute("""
                    UPDATE internacao_dados_brutos
                    SET categoria=?, conteudo=?, pagina_origem=?, fonte=?
                    WHERE id=?
                """, (
                    dados.get("categoria","outro"), dados.get("conteudo"),
                    dados.get("pagina_origem"), dados.get("fonte","manual"), did
                ))
                return did
            else:
                cur = conn.execute("""
                    INSERT INTO internacao_dados_brutos
                    (internacao_id, categoria, conteudo, pagina_origem, fonte)
                    VALUES (?,?,?,?,?)
                """, (
                    dados["internacao_id"], dados.get("categoria","outro"),
                    dados.get("conteudo"), dados.get("pagina_origem"),
                    dados.get("fonte","manual")
                ))
                return cur.lastrowid
    except Exception as ex:
        print(f"[MODEL] salvar_dado_bruto_internacao: {ex}")
        return 0


def excluir_dado_bruto_internacao(dado_id: int) -> bool:
    """Remove dado bruto."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute(
                "DELETE FROM internacao_dados_brutos WHERE id=?", (dado_id,))
        return True
    except Exception as ex:
        print(f"[MODEL] excluir_dado_bruto_internacao: {ex}")
        return False


def listar_remedios_internacao(hospital: str) -> list[dict]:
    """Retorna remedios com ativo=0 vinculados a internacao pelo nome do hospital."""
    try:
        prefixo = f"[Internacao: {hospital}]"
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            rows = conn.execute("""
                SELECT id, nome, dosagem, frequencia, principio_ativo,
                       data_inicio, data_fim, observacoes
                FROM remedios
                WHERE observacoes LIKE ? AND ativo = 0
                ORDER BY nome
            """, (prefixo + "%",)).fetchall()
        cols = ["id","nome","dosagem","frequencia","principio_ativo",
                "data_inicio","data_fim","observacoes"]
        return [dict(zip(cols, r)) for r in rows]
    except Exception as ex:
        print(f"[MODEL] listar_remedios_internacao: {ex}")
        return []


def _inferir_modalidade(data_entrada: str, data_saida: str) -> str:
    """Infere modalidade pelo número de dias: ps=mesmo dia, internacao=pernoite."""
    if not data_entrada or not data_saida:
        return "internacao"
    try:
        import datetime as _dt
        de = _dt.date.fromisoformat(data_entrada[:10])
        ds = _dt.date.fromisoformat(data_saida[:10])
        return "ps" if (ds - de).days == 0 else "internacao"
    except Exception:
        return "internacao"


def salvar_internacao(dados: dict) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur = conn.cursor()
        _de = normalizar_data(dados["data_entrada"])
        _ds = normalizar_data(dados.get("data_saida"))
        _fonte = dados.get("fonte_dados") or (
            "importado" if (dados.get("documento_local") or dados.get("drive_link")) else "manual")
        _modalidade = dados.get("modalidade") or _inferir_modalidade(_de, _ds)
        if dados.get("id"):
            cur.execute("""
                UPDATE internacoes SET hospital=?, medico_id=?, clinica_id=?,
                data_entrada=?, data_saida=?, tipo=?, motivo=?, cid_entrada=?,
                diagnostico_saida=?, cid_saida=?, observacoes=?, documento_local=?,
                cidade=?, uf=?, objetivo=?, drive_file_id=?, drive_link=?, fonte_dados=?,
                gatilho=?, modalidade=?
                WHERE id=?
            """, (dados["hospital"], dados.get("medico_id"), dados.get("clinica_id"),
                  _de, _ds, dados.get("tipo","eletiva"),
                  dados.get("motivo"), dados.get("cid_entrada"), dados.get("diagnostico_saida"),
                  dados.get("cid_saida"), dados.get("observacoes"), dados.get("documento_local"),
                  dados.get("cidade"), dados.get("uf"), dados.get("objetivo","tratamento"),
                  dados.get("drive_file_id"), dados.get("drive_link"), _fonte,
                  dados.get("gatilho"), _modalidade,
                  dados["id"]))
            rid = dados["id"]
        else:
            cur.execute("""
                INSERT INTO internacoes (hospital, medico_id, clinica_id, data_entrada,
                data_saida, tipo, motivo, cid_entrada, diagnostico_saida, cid_saida,
                observacoes, documento_local, cidade, uf, objetivo, drive_file_id, drive_link,
                fonte_dados, gatilho, modalidade)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (dados["hospital"], dados.get("medico_id"), dados.get("clinica_id"),
                  _de, _ds, dados.get("tipo","eletiva"),
                  dados.get("motivo"), dados.get("cid_entrada"), dados.get("diagnostico_saida"),
                  dados.get("cid_saida"), dados.get("observacoes"), dados.get("documento_local"),
                  dados.get("cidade"), dados.get("uf"), dados.get("objetivo","tratamento"),
                  dados.get("drive_file_id"), dados.get("drive_link"), _fonte,
                  dados.get("gatilho"), _modalidade))
            rid = cur.lastrowid
        conn.commit()
        return rid
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()


def excluir_internacao(internacao_id: int) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("UPDATE procedimentos SET internacao_id=NULL WHERE internacao_id=?",
                     (internacao_id,))
        conn.execute("DELETE FROM internacoes WHERE id=?", (internacao_id,))
        conn.commit()
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# HELPERS — PROCEDIMENTOS
# ══════════════════════════════════════════════════════════════

def listar_procedimentos(internacao_id: int = None) -> list[dict]:
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            where = "WHERE p.internacao_id = ?" if internacao_id else ""
            params = (internacao_id,) if internacao_id else ()
            cur = conn.execute(f"""
                SELECT p.id, p.internacao_id, p.medico_id, p.nome, p.tipo,
                       p.data, p.hora, p.local, p.anestesia, p.cid,
                       p.resultado, p.observacoes, p.criado_em,
                       m.nome AS medico_nome,
                       i.hospital AS internacao_hospital
                FROM procedimentos p
                LEFT JOIN medicos m ON m.id = p.medico_id
                LEFT JOIN internacoes i ON i.id = p.internacao_id
                {where}
                ORDER BY p.data DESC, p.hora DESC
            """, params)
            cols = ["id","internacao_id","medico_id","nome","tipo","data","hora","local",
                    "anestesia","cid","resultado","observacoes","criado_em",
                    "medico_nome","internacao_hospital"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as ex:
        print(f"[MODEL] listar_procedimentos: {ex}")
        return []


def salvar_procedimento(dados: dict) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur = conn.cursor()
        if dados.get("id"):
            cur.execute("""
                UPDATE procedimentos SET internacao_id=?, medico_id=?, nome=?, tipo=?,
                data=?, hora=?, local=?, anestesia=?, cid=?, resultado=?, observacoes=?
                WHERE id=?
            """, (dados.get("internacao_id"), dados.get("medico_id"), dados["nome"],
                  dados.get("tipo","cirurgico"), dados["data"], dados.get("hora"),
                  dados.get("local"), dados.get("anestesia","sem"), dados.get("cid"),
                  dados.get("resultado"), dados.get("observacoes"), dados["id"]))
            rid = dados["id"]
        else:
            cur.execute("""
                INSERT INTO procedimentos (internacao_id, medico_id, nome, tipo, data,
                hora, local, anestesia, cid, resultado, observacoes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (dados.get("internacao_id"), dados.get("medico_id"), dados["nome"],
                  dados.get("tipo","cirurgico"), dados["data"], dados.get("hora"),
                  dados.get("local"), dados.get("anestesia","sem"), dados.get("cid"),
                  dados.get("resultado"), dados.get("observacoes")))
            rid = cur.lastrowid
        conn.commit()
        return rid
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()


def excluir_procedimento(proc_id: int) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("DELETE FROM procedimentos WHERE id=?", (proc_id,))
        conn.commit()
    finally:
        conn.close()


# ── Rotina Diario (log de excecoes e observacoes) ─────────────────────────────

def listar_rotina_diario(limite: int = 60) -> list[dict]:
    """Historico de alteracoes/observacoes, mais recentes primeiro."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT rd.*, im.descricao as item_descricao_fk
                FROM rotina_diario rd
                LEFT JOIN itens_momento im ON im.id = rd.item_id
                ORDER BY rd.data DESC, rd.criado_em DESC
                LIMIT ?
            """, (limite,)).fetchall()
            return [dict(r) for r in rows]
    except Exception as ex:
        print(f"[MODEL] listar_rotina_diario: {ex}")
        return []


def listar_alteracoes_ativas(data_ref: str) -> list[dict]:
    """Retorna alteracoes cujo data_fim >= data_ref ou data_fim IS NULL (ainda ativas)."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM rotina_diario
                WHERE (data_fim IS NULL OR data_fim >= ?)
                  AND tipo IN ('suspensao','reducao','adicao')
                ORDER BY data DESC
            """, (data_ref,)).fetchall()
            return [dict(r) for r in rows]
    except Exception as ex:
        print(f"[MODEL] listar_alteracoes_ativas: {ex}")
        return []


def salvar_rotina_diario(dados: dict) -> int | None:
    """INSERT ou UPDATE de registro no diario de rotina. Retorna id."""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            if dados.get("id"):
                conn.execute("""
                    UPDATE rotina_diario
                    SET data=?, item_id=?, item_nome=?, tipo=?, descricao=?, motivo=?, data_fim=?
                    WHERE id=?
                """, (
                    dados.get("data"), dados.get("item_id"), dados.get("item_nome"),
                    dados.get("tipo"), dados.get("descricao"), dados.get("motivo"),
                    dados.get("data_fim"), dados["id"],
                ))
                return dados["id"]
            else:
                cur = conn.execute("""
                    INSERT INTO rotina_diario (data, item_id, item_nome, tipo, descricao, motivo, data_fim)
                    VALUES (?,?,?,?,?,?,?)
                """, (
                    dados.get("data"), dados.get("item_id"), dados.get("item_nome"),
                    dados.get("tipo"), dados.get("descricao"), dados.get("motivo"),
                    dados.get("data_fim"),
                ))
                return cur.lastrowid
    except Exception as ex:
        print(f"[MODEL] salvar_rotina_diario: {ex}")
        return None


def excluir_rotina_diario(registro_id: int) -> bool:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("DELETE FROM rotina_diario WHERE id=?", (registro_id,))
        return True
    except Exception as ex:
        print(f"[MODEL] excluir_rotina_diario: {ex}")
        return False


# ══════════════════════════════════════════════════════════════
# DIAGNOSTICOS
# ══════════════════════════════════════════════════════════════

def listar_diagnosticos(sistema: str = None, so_ativos: bool = True) -> list[dict]:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            # tabela diagnosticos (formal)
            sql = """
                SELECT d.id, d.titulo, d.cid, d.descricao, d.sistema,
                       d.data_diagnostico, d.data_resolucao, d.status,
                       d.certeza, d.observacoes, d.ativo,
                       m.nome as medico_nome,
                       'diagnosticos' as origem
                FROM diagnosticos d
                LEFT JOIN medicos m ON m.id = d.medico_id
                WHERE 1=1
            """
            params = []
            if so_ativos:
                sql += " AND d.ativo = 1"
            if sistema:
                sql += " AND d.sistema = ?"
                params.append(sistema)

            rows = conn.execute(sql, params).fetchall()
            cols = ["id","titulo","cid","descricao","sistema","data_diagnostico",
                    "data_resolucao","status","certeza","observacoes","ativo",
                    "medico_nome","origem"]
            resultado = [dict(zip(cols, r)) for r in rows]

            # historico_medico com tipo diagnostico/condicao_cronica
            # so inclui se nao filtrar por sistema (historico nao tem sistema)
            if not sistema:
                sql_hist = """
                    SELECT id, titulo, NULL, descricao, NULL,
                           data_aprox, NULL, tipo,
                           NULL, sequela, 1,
                           medico, 'historico_medico'
                    FROM historico_medico
                    WHERE tipo IN ('diagnostico', 'condicao_cronica', 'alergia_risco')
                    ORDER BY data_aprox DESC
                """
                rows_hist = conn.execute(sql_hist).fetchall()
                for r in rows_hist:
                    d = dict(zip(cols, r))
                    # mapear tipo para status legivel
                    tipo_map = {
                        "diagnostico":     "ativo",
                        "condicao_cronica": "cronico",
                        "alergia_risco":   "ativo",
                    }
                    d["status"] = tipo_map.get(d["status"], d["status"])
                    resultado.append(d)

            # ordenar: status primeiro, depois data
            resultado.sort(key=lambda x: (
                {"cronico": 0, "ativo": 1, "suspeito": 2, "resolvido": 3}.get(
                    x.get("status", ""), 9),
                -(int(str(x.get("data_diagnostico") or "0")[:4] or 0))
            ))
            return resultado
    except Exception as ex:
        print(f"[MODEL] listar_diagnosticos: {ex}")
        return []


def salvar_diagnostico(dados: dict) -> int | None:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            did = dados.get("id")
            if did:
                conn.execute("""
                    UPDATE diagnosticos SET
                        titulo=?, cid=?, descricao=?, sistema=?,
                        data_diagnostico=?, data_resolucao=?, status=?,
                        certeza=?, medico_id=?, observacoes=?,
                        atualizado_em=datetime('now')
                    WHERE id=?
                """, (
                    dados.get("titulo"), dados.get("cid"), dados.get("descricao"),
                    dados.get("sistema"), dados.get("data_diagnostico"),
                    dados.get("data_resolucao"), dados.get("status","ativo"),
                    dados.get("certeza","confirmado"), dados.get("medico_id"),
                    dados.get("observacoes"), did,
                ))
                _notify()
                return did
            else:
                cur = conn.execute("""
                    INSERT INTO diagnosticos
                        (titulo, cid, descricao, sistema, data_diagnostico,
                         data_resolucao, status, certeza, medico_id, observacoes)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (
                    dados.get("titulo"), dados.get("cid"), dados.get("descricao"),
                    dados.get("sistema"), dados.get("data_diagnostico"),
                    dados.get("data_resolucao"), dados.get("status","ativo"),
                    dados.get("certeza","confirmado"), dados.get("medico_id"),
                    dados.get("observacoes"),
                ))
                _notify()
                return cur.lastrowid
    except Exception as ex:
        print(f"[MODEL] salvar_diagnostico: {ex}")
        return None


def excluir_diagnostico(did: int) -> bool:
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("UPDATE diagnosticos SET ativo=0 WHERE id=?", (did,))
        _notify()
        return True
    except Exception as ex:
        print(f"[MODEL] excluir_diagnostico: {ex}")
        return False


# ── Tratamento por diagnóstico ───────────────────────────────────────────────

def salvar_tratamento_diagnostico(origem: str, origem_id: int,
                                   medico_id=None, observacoes=None,
                                   remedios=None, data_revisao=None) -> bool:
    """
    Salva ou atualiza o plano de tratamento de um diagnóstico.
    remedios: lista de {"remedio_id": int, "dosagem": str, "frequencia": str}
    """
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            row = conn.execute(
                "SELECT id FROM diagnostico_tratamento WHERE origem=? AND origem_id=?",
                (origem, origem_id)
            ).fetchone()
            if row:
                tid = row[0]
                conn.execute("""
                    UPDATE diagnostico_tratamento
                    SET medico_id=?, observacoes=?, data_revisao=?, atualizado_em=datetime('now')
                    WHERE id=?
                """, (medico_id, observacoes, data_revisao, tid))
                conn.execute(
                    "DELETE FROM diagnostico_tratamento_remedios WHERE tratamento_id=?",
                    (tid,))
            else:
                cur = conn.execute("""
                    INSERT INTO diagnostico_tratamento
                        (origem, origem_id, medico_id, observacoes, data_revisao)
                    VALUES (?, ?, ?, ?, ?)
                """, (origem, origem_id, medico_id, observacoes, data_revisao))
                tid = cur.lastrowid
            for rem in (remedios or []):
                conn.execute("""
                    INSERT INTO diagnostico_tratamento_remedios
                        (tratamento_id, remedio_id, dosagem, frequencia)
                    VALUES (?, ?, ?, ?)
                """, (tid, rem["remedio_id"], rem.get("dosagem"), rem.get("frequencia")))

            # criar compromisso de revisão se data_revisao informada
            if data_revisao:
                # buscar titulo do diagnostico para a observacao
                try:
                    if origem == "diagnosticos":
                        row_d = conn.execute(
                            "SELECT titulo FROM diagnosticos WHERE id=?",
                            (origem_id,)).fetchone()
                    else:
                        row_d = conn.execute(
                            "SELECT titulo FROM historico_medico WHERE id=?",
                            (origem_id,)).fetchone()
                    titulo_diag = row_d[0] if row_d else "Diagnóstico"
                except Exception:
                    titulo_diag = "Diagnóstico"

                obs_comp = f"Revisão: {titulo_diag}"
                # verificar se já existe compromisso de revisão para este tratamento
                comp_exist = conn.execute("""
                    SELECT id FROM consultas
                    WHERE observacoes=? AND data=? AND tipo='agendada'
                """, (obs_comp, data_revisao)).fetchone()

                if not comp_exist:
                    conn.execute("""
                        INSERT INTO consultas
                            (medico_id, data, tipo, observacoes,
                             tipo_compromisso, criado_em)
                        VALUES (?, ?, 'agendada', ?, 'consulta', datetime('now'))
                    """, (medico_id, data_revisao, obs_comp))

        _notify()
        return True
    except Exception as ex:
        print(f"[MODEL] salvar_tratamento_diagnostico: {ex}")
        return False


def carregar_tratamento_diagnostico(origem: str, origem_id: int) -> dict:
    """
    Retorna {"medico_id", "observacoes", "remedios": [{"remedio_id","nome","dosagem","frequencia"}]}
    """
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            row = conn.execute(
                "SELECT id, medico_id, observacoes, data_revisao FROM diagnostico_tratamento WHERE origem=? AND origem_id=?",
                (origem, origem_id)
            ).fetchone()
            if not row:
                return {"medico_id": None, "observacoes": "", "data_revisao": "", "remedios": []}
            tid, medico_id, obs, data_revisao = row
            rems = conn.execute("""
                SELECT r.id, r.nome, dtr.dosagem, dtr.frequencia
                FROM diagnostico_tratamento_remedios dtr
                JOIN remedios r ON r.id = dtr.remedio_id
                WHERE dtr.tratamento_id=?
            """, (tid,)).fetchall()
            return {
                "medico_id": medico_id,
                "observacoes": obs or "",
                "remedios": [
                    {"remedio_id": r[0], "nome": r[1],
                     "dosagem": r[2] or "", "frequencia": r[3] or ""}
                    for r in rems
                ],
            }
    except Exception as ex:
        print(f"[MODEL] carregar_tratamento_diagnostico: {ex}")
        return {"medico_id": None, "observacoes": "", "remedios": []}


# ── Códigos de acesso médico ─────────────────────────────────────────────────

def _gerar_codigo_unico() -> str:
    import random, string
    chars = string.ascii_uppercase + string.digits
    while True:
        codigo = "".join(random.choices(chars, k=4)) + "-" + "".join(random.choices(chars, k=4))
        conn = sqlite3.connect(CORE_DB, timeout=10)
        existe = conn.execute(
            "SELECT 1 FROM codigos_acesso_medico WHERE codigo=?", (codigo,)
        ).fetchone()
        conn.close()
        if not existe:
            return codigo


def listar_codigos_acesso() -> list:
    try:
        with sqlite3.connect(CORE_DB, timeout=10) as conn:
            rows = conn.execute(
                "SELECT id, codigo, nome_medico, criado_em, ativo "
                "FROM codigos_acesso_medico ORDER BY criado_em DESC"
            ).fetchall()
        return [{"id": r[0], "codigo": r[1], "nome_medico": r[2],
                 "criado_em": r[3], "ativo": r[4]} for r in rows]
    except Exception as ex:
        print(f"[MODEL] listar_codigos_acesso: {ex}")
        return []


def gerar_codigo_acesso(nome_medico: str) -> str | None:
    try:
        codigo = _gerar_codigo_unico()
        with sqlite3.connect(CORE_DB, timeout=10) as conn:
            conn.execute(
                "INSERT INTO codigos_acesso_medico (codigo, nome_medico) VALUES (?, ?)",
                (codigo, nome_medico)
            )
            conn.commit()
        return codigo
    except Exception as ex:
        print(f"[MODEL] gerar_codigo_acesso: {ex}")
        return None


def revogar_codigo_acesso(codigo_id: int) -> bool:
    try:
        with sqlite3.connect(CORE_DB, timeout=10) as conn:
            conn.execute(
                "UPDATE codigos_acesso_medico SET ativo=0 WHERE id=?", (codigo_id,)
            )
            conn.commit()
        return True
    except Exception as ex:
        print(f"[MODEL] revogar_codigo_acesso: {ex}")
        return False


def validar_codigo_acesso(codigo: str) -> dict | None:
    """Retorna dados do médico se código válido e ativo, None caso contrário."""
    try:
        with sqlite3.connect(CORE_DB, timeout=10) as conn:
            row = conn.execute(
                "SELECT id, nome_medico FROM codigos_acesso_medico "
                "WHERE codigo=? AND ativo=1", (codigo,)
            ).fetchone()
        if row:
            return {"id": row[0], "nome_medico": row[1]}
        return None
    except Exception as ex:
        print(f"[MODEL] validar_codigo_acesso: {ex}")
        return None


if __name__ == "__main__":
    criar_tabelas()
    print("Banco de dados iniciado com sucesso!")
