# -*- coding: utf-8 -*-
"""
criar_tabelas_remedios_snippet.sql
===================================
COLAR este SQL dentro da função criar_tabelas() do model.py,
logo após os CREATE TABLE existentes.

NOTA: A tabela 'remedios' existente NÃO tem o campo 'foto_path'.
Substituir o CREATE TABLE IF NOT EXISTS remedios antigo por este novo.
"""

# ── SUBSTITUIR o CREATE TABLE remedios existente por este: ──

"""
    CREATE TABLE IF NOT EXISTS remedios (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        nome            TEXT NOT NULL,
        dosagem         TEXT,
        frequencia      TEXT,
        data_inicio     TEXT,
        data_fim        TEXT,
        medico_id       INTEGER,
        receita_id      INTEGER,
        estoque_atual   INTEGER DEFAULT 0,
        estoque_minimo  INTEGER DEFAULT 5,
        foto_path       TEXT,
        ativo           INTEGER DEFAULT 1,
        observacoes     TEXT,
        criado_em       TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (medico_id) REFERENCES medicos(id)
    );
"""

# ── ADICIONAR estas tabelas novas (após remedios): ──

"""
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
"""
