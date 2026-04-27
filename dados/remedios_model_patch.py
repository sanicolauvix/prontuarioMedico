"""
remedios_model_patch.py — Koios
=================================
SQL + funções para o módulo completo de remédios.

COMO USAR:
1. Copiar blocos SQL para dentro de criar_tabelas() no model.py
2. Copiar funções para o final do model.py
3. Deletar banco e recriar

Tabelas:
  remedios (atualizada - campo foto_path)
  remedios_horarios
  remedios_tomadas
  farmacias (com whatsapp)
  remedios_compras
  remedios_orcamentos (solicitações via WhatsApp/web)
"""

# ══════════════════════════════════════════════════════════════
# PARTE 1 — SQL para criar_tabelas()
# ══════════════════════════════════════════════════════════════

SQL_REMEDIOS = """
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


# ══════════════════════════════════════════════════════════════
# PARTE 2 — Funções model.py
# ══════════════════════════════════════════════════════════════

# --- HORÁRIOS ---

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


# --- TOMADAS ---

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
            # Desfez tomada — devolver ao estoque
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
        for status, qtd in rows:
            r[status] = qtd; r["total"] += qtd
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


# --- FARMÁCIAS ---

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


# --- COMPRAS ---

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
        # Atualizar estoque
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
            SELECT c.preco_unitario, f.nome
            FROM remedios_compras c
            LEFT JOIN farmacias f ON f.id = c.farmacia_id
            WHERE c.remedio_id=? AND c.preco_unitario > 0
            ORDER BY c.preco_unitario ASC LIMIT 1
        """, (remedio_id,)).fetchone()

        ultimo = conn.execute("""
            SELECT c.preco_unitario, c.preco_total, f.nome, c.data_compra
            FROM remedios_compras c
            LEFT JOIN farmacias f ON f.id = c.farmacia_id
            WHERE c.remedio_id=?
            ORDER BY c.data_compra DESC LIMIT 1
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


# --- ORÇAMENTOS ---

def criar_orcamento(farmacia_id, mensagem, itens):
    """Cria solicitação de orçamento. itens = [{"remedio_id", "nome", "dosagem", "quantidade"}]"""
    from datetime import date as _d
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur = conn.cursor()
        cur.execute("""INSERT INTO remedios_orcamentos
                       (farmacia_id, data_envio, mensagem_envio, status)
                       VALUES (?,?,?,?)""",
                    (farmacia_id, _d.today().isoformat(), mensagem, "enviado"))
        oid = cur.lastrowid
        for item in itens:
            cur.execute("""INSERT INTO orcamento_itens
                           (orcamento_id, remedio_id, nome_pedido, dosagem_pedido, quantidade)
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
    """Salva resposta da farmácia (texto bruto + itens extraídos pela IA).
    itens_ia = [{"nome", "preco", "disponivel", "observacao"}]"""
    import json as _json
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        cur = conn.cursor()
        cur.execute("""UPDATE remedios_orcamentos
                       SET resposta_bruta=?, resposta_ia=?, status='respondido'
                       WHERE id=?""",
                    (resposta_bruta, _json.dumps(itens_ia, ensure_ascii=False), orcamento_id))
        # Atualizar preços nos itens
        for item in itens_ia:
            if item.get("preco") and item.get("nome_pedido"):
                cur.execute("""UPDATE orcamento_itens
                               SET preco_informado=?, disponivel=?, observacao=?
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
            rows = conn.execute("""
                SELECT o.id, o.data_envio, o.status, f.nome, o.farmacia_id
                FROM remedios_orcamentos o
                LEFT JOIN farmacias f ON f.id = o.farmacia_id
                WHERE o.farmacia_id=? ORDER BY o.data_envio DESC
            """, (farmacia_id,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT o.id, o.data_envio, o.status, f.nome, o.farmacia_id
                FROM remedios_orcamentos o
                LEFT JOIN farmacias f ON f.id = o.farmacia_id
                ORDER BY o.data_envio DESC
            """).fetchall()
        cols = ["id","data_envio","status","farmacia","farmacia_id"]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def gerar_mensagem_orcamento(remedios_ids=None):
    """Gera texto formatado para enviar via WhatsApp solicitando orçamento."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        if remedios_ids:
            placeholders = ",".join("?" * len(remedios_ids))
            rows = conn.execute(f"""
                SELECT nome, dosagem, estoque_atual, estoque_minimo
                FROM remedios WHERE id IN ({placeholders}) AND ativo=1
            """, remedios_ids).fetchall()
        else:
            rows = conn.execute("""
                SELECT nome, dosagem, estoque_atual, estoque_minimo
                FROM remedios WHERE ativo=1 AND estoque_atual <= estoque_minimo
                ORDER BY nome
            """).fetchall()

        if not rows:
            return None, []

        linhas = ["Olá! Gostaria de um orçamento para os seguintes medicamentos:\n"]
        itens = []
        for i, (nome, dosagem, est, mn) in enumerate(rows, 1):
            qtd = max(1, (mn or 5) * 2 - (est or 0))  # Sugere comprar o dobro do mínimo
            desc = f"{nome}"
            if dosagem:
                desc += f" {dosagem}"
            linhas.append(f"{i}. {desc} — {qtd} unidades")
            itens.append({"nome": nome, "dosagem": dosagem, "quantidade": qtd})

        linhas.append("\nAgradeço o retorno! 🙏")
        return "\n".join(linhas), itens
    finally:
        conn.close()


def link_whatsapp(numero, texto):
    """Gera link wa.me para abrir WhatsApp com mensagem."""
    import urllib.parse
    # Limpar número: só dígitos
    num = "".join(c for c in (numero or "") if c.isdigit())
    if not num:
        return None
    # Adicionar 55 se não tem código de país
    if len(num) <= 11:
        num = "55" + num
    texto_enc = urllib.parse.quote(texto)
    return f"https://wa.me/{num}?text={texto_enc}"


def analisar_resposta_orcamento_ia(texto_resposta, itens_pedidos):
    """Usa Claude API para extrair preços da resposta da farmácia.
    Retorna lista de dicts: [{nome_pedido, preco, disponivel, observacao}]"""
    try:
        import anthropic
        import json as _json

        nomes = ", ".join(f'"{i["nome"]}"' for i in itens_pedidos)

        prompt = f"""Analise a resposta de uma farmácia sobre um orçamento de medicamentos.
Extraia o preço de cada medicamento mencionado.

Medicamentos solicitados: {nomes}

Resposta da farmácia:
\"\"\"
{texto_resposta}
\"\"\"

Responda APENAS com um JSON array, sem markdown. Cada item:
{{"nome_pedido": "nome do medicamento", "preco": 12.90, "disponivel": true, "observacao": ""}}

Se não encontrar preço para algum, coloque preco: null e disponivel: false.
"""
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        texto = resp.content[0].text.strip()
        # Limpar possíveis backticks
        if texto.startswith("```"):
            texto = texto.split("\n", 1)[1].rsplit("```", 1)[0]
        return _json.loads(texto)
    except Exception as ex:
        # Fallback: retornar itens sem preço
        return [{"nome_pedido": i["nome"], "preco": None,
                 "disponivel": False, "observacao": f"Erro IA: {ex}"}
                for i in itens_pedidos]
