"""
db_helper.py — Acesso ao prontuario.db para a skill Claudia.

Helpers prontos para as consultas mais comuns, já com filtro por paciente_id,
context manager, linhas retornadas como dicts e pequenas conveniências.

Uso:
    from claudia.scripts.db_helper import ClaudiaDB

    with ClaudiaDB(paciente_id=1) as db:
        exames = db.exames_ultimos(limite=10)
        hb = db.resultados_de_exame("Hemoglobina", ultimos=5)
        ativos = db.remedios_ativos()

Convenções:
- Todas as escritas exigem confirmação do chamador (parâmetro confirm=True).
- Datas são strings ISO (YYYY-MM-DD).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable


DB_PATH_PADRAO = Path(__file__).resolve().parents[2] / "dados" / "prontuario.db"


@dataclass
class ClaudiaDB:
    """Wrapper fino sobre o prontuario.db com filtros por paciente."""

    paciente_id: int
    db_path: Path = DB_PATH_PADRAO
    _conn: sqlite3.Connection | None = None

    # ------------------- infra -------------------

    def __enter__(self) -> "ClaudiaDB":
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._conn is not None:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
            self._conn.close()
            self._conn = None

    def _cursor(self) -> sqlite3.Cursor:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn.cursor()

    def _rows(self, sql: str, params: Iterable[Any] = ()) -> list[dict]:
        cur = self._cursor()
        cur.execute(sql, tuple(params))
        return [dict(r) for r in cur.fetchall()]

    def _one(self, sql: str, params: Iterable[Any] = ()) -> dict | None:
        cur = self._cursor()
        cur.execute(sql, tuple(params))
        row = cur.fetchone()
        return dict(row) if row else None

    # ------------------- paciente -------------------

    def paciente(self) -> dict | None:
        return self._one(
            "SELECT id, nome, cpf, data_nasc, sexo FROM pacientes WHERE id=?",
            (self.paciente_id,),
        )

    def idade(self) -> int | None:
        p = self.paciente()
        if not p or not p.get("data_nasc"):
            return None
        try:
            nasc = datetime.strptime(p["data_nasc"], "%Y-%m-%d").date()
        except ValueError:
            return None
        hoje = date.today()
        return hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))

    # ------------------- exames -------------------

    def exames_ultimos(self, limite: int = 10) -> list[dict]:
        return self._rows(
            """
            SELECT id, tipo_exame, data_exame, laboratorio, medico_solicit, resultado_texto
            FROM exames
            WHERE paciente_id=? AND (status IS NULL OR status='ativo')
            ORDER BY data_exame DESC
            LIMIT ?
            """,
            (self.paciente_id, limite),
        )

    def resultados_de_exame(self, nome_parametro: str, ultimos: int = 10) -> list[dict]:
        """Retorna valores de um parâmetro (ex: 'Hemoglobina') ao longo do tempo."""
        return self._rows(
            """
            SELECT e.data_exame, r.parametro, r.valor, r.unidade,
                   r.referencia, r.nivel_interpretacao
            FROM resultados_estruturados r
            JOIN exames e ON e.id = r.exame_id
            LEFT JOIN exames_padrao ep ON ep.id = r.exame_padrao_id
            WHERE e.paciente_id=?
              AND (LOWER(ep.nome_oficial)=LOWER(?) OR LOWER(r.parametro)=LOWER(?))
            ORDER BY e.data_exame DESC
            LIMIT ?
            """,
            (self.paciente_id, nome_parametro, nome_parametro, ultimos),
        )

    def referencia_parametro(self, nome_parametro: str) -> dict | None:
        """Faixa de referência personalizada para o paciente (por sexo/idade)."""
        p = self.paciente()
        sexo = (p or {}).get("sexo") or ""
        idade = self.idade() or 0
        return self._one(
            """
            SELECT rp.*, ep.nome_oficial, ep.unidade
            FROM referencias_padrao rp
            JOIN exames_padrao ep ON ep.id = rp.exame_padrao_id
            WHERE LOWER(ep.nome_oficial)=LOWER(?)
              AND (rp.sexo IS NULL OR rp.sexo='' OR rp.sexo=?)
              AND (rp.idade_min IS NULL OR rp.idade_min<=?)
              AND (rp.idade_max IS NULL OR rp.idade_max>=?)
            ORDER BY rp.criado_em DESC
            LIMIT 1
            """,
            (nome_parametro, sexo, idade, idade),
        )

    # ------------------- medicação -------------------

    def remedios_ativos(self) -> list[dict]:
        return self._rows(
            """
            SELECT r.id, r.nome, r.dosagem, r.frequencia, r.data_inicio, r.data_fim,
                   r.estoque_atual, r.estoque_minimo, r.observacoes
            FROM remedios r
            JOIN receitas rc ON rc.id = r.receita_id
            JOIN consultas c ON c.id = rc.consulta_id
            WHERE c.paciente_id=? AND r.ativo=1
              AND (r.data_fim IS NULL OR r.data_fim >= date('now'))
            ORDER BY r.nome
            """,
            (self.paciente_id,),
        )

    def adesao_remedio(self, remedio_id: int, dias: int = 30) -> dict:
        """Retorna adesão dos últimos N dias (% tomado sobre planejado)."""
        rows = self._rows(
            """
            SELECT status, COUNT(*) AS n
            FROM remedios_tomadas
            WHERE remedio_id=? AND data >= date('now', ?)
            GROUP BY status
            """,
            (remedio_id, f"-{int(dias)} day"),
        )
        total = sum(r["n"] for r in rows) or 0
        tomado = sum(r["n"] for r in rows if r["status"] == "tomado")
        pct = round((tomado / total) * 100, 1) if total else None
        return {"total_doses": total, "tomadas": tomado, "adesao_pct": pct, "por_status": rows}

    def interacoes_suspeitas(self) -> list[dict]:
        """Lista combinações dos remédios ativos que valem checagem manual."""
        ativos = [r["nome"].lower() for r in self.remedios_ativos()]
        # Heurística leve — a análise clínica é feita pela Claudia, aqui só sinalizamos pares.
        pares_criticos = [
            ({"varfarina", "warfarin"}, {"aas", "aspirina", "ibuprofeno", "naproxeno"}),
            ({"losartana", "enalapril", "ramipril"}, {"espironolactona", "potassio"}),
            ({"sildenafil", "tadalafil"}, {"nitrato", "isordil", "monocordil"}),
            ({"metformina"}, {"contraste iodado"}),
            ({"sinvastatina", "atorvastatina"}, {"claritromicina", "eritromicina"}),
            ({"fluoxetina", "sertralina", "escitalopram"}, {"tramadol", "sumatriptano"}),
        ]
        achados = []
        for a, b in pares_criticos:
            ta = [n for n in ativos if any(k in n for k in a)]
            tb = [n for n in ativos if any(k in n for k in b)]
            if ta and tb:
                achados.append({"grupo_a": ta, "grupo_b": tb})
        return achados

    # ------------------- diário / rotina -------------------

    def diario_ultimos(self, dias: int = 30) -> list[dict]:
        return self._rows(
            """
            SELECT data, hora, humor, energia, sono_horas, peso, pressao, relato, tags, remedio_tomado
            FROM diario_saude
            WHERE date(data) >= date('now', ?)
            ORDER BY data DESC, hora DESC
            """,
            (f"-{int(dias)} day",),
        )

    def rotina_ativa(self) -> list[dict]:
        return self._rows(
            "SELECT tipo, nome, horario, dias_semana, quantidade, descricao FROM rotina_itens WHERE ativo=1 ORDER BY horario",
            (),
        )

    # ------------------- escritas -------------------

    def registrar_diario(
        self,
        relato: str,
        *,
        humor: int | None = None,
        energia: int | None = None,
        sono_horas: float | None = None,
        peso: float | None = None,
        pressao: str | None = None,
        tags: str | None = None,
        remedio_tomado: str | None = None,
        data: str | None = None,
        hora: str | None = None,
        confirm: bool = False,
    ) -> int:
        if not confirm:
            raise PermissionError("Passe confirm=True após confirmar com o usuário.")
        if data is None:
            data = date.today().isoformat()
        if hora is None:
            hora = datetime.now().strftime("%H:%M")
        cur = self._cursor()
        cur.execute(
            """
            INSERT INTO diario_saude
                (data, hora, humor, energia, sono_horas, peso, pressao, relato, tags, remedio_tomado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (data, hora, humor, energia, sono_horas, peso, pressao, relato, tags, remedio_tomado),
        )
        return cur.lastrowid

    def marcar_dose(
        self, remedio_id: int, status: str = "tomado", *,
        horario_id: int | None = None,
        data: str | None = None, hora: str | None = None,
        confirm: bool = False,
    ) -> int:
        if not confirm:
            raise PermissionError("Passe confirm=True após confirmar com o usuário.")
        if status not in {"pendente", "tomado", "pulado", "atrasado"}:
            raise ValueError("status inválido")
        if data is None:
            data = date.today().isoformat()
        if hora is None:
            hora = datetime.now().strftime("%H:%M")
        cur = self._cursor()
        cur.execute(
            """
            INSERT INTO remedios_tomadas (remedio_id, horario_id, data, hora, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (remedio_id, horario_id, data, hora, status),
        )
        return cur.lastrowid

    def criar_rotina_item(
        self, tipo: str, nome: str, *,
        horario: str | None = None, dias_semana: str | None = None,
        descricao: str | None = None, quantidade: str | None = None,
        confirm: bool = False,
    ) -> int:
        if not confirm:
            raise PermissionError("Passe confirm=True após confirmar com o usuário.")
        if tipo not in {"refeicao", "medicamento", "suplemento", "atividade", "outro"}:
            raise ValueError("tipo inválido")
        cur = self._cursor()
        cur.execute(
            """
            INSERT INTO rotina_itens (tipo, nome, horario, dias_semana, descricao, quantidade, ativo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (tipo, nome, horario, dias_semana, descricao, quantidade),
        )
        return cur.lastrowid

    # ------------------- agregados -------------------

    def resumo_clinico(self, dias: int = 90) -> dict:
        """Pacote com o essencial para um sumário pré-consulta."""
        return {
            "paciente": self.paciente(),
            "idade": self.idade(),
            "exames_recentes": self.exames_ultimos(limite=15),
            "remedios_ativos": self.remedios_ativos(),
            "diario": self.diario_ultimos(dias=dias),
            "rotina": self.rotina_ativa(),
            "interacoes_suspeitas": self.interacoes_suspeitas(),
        }


# ----- helper rápido para uso fora de context manager -----

@contextmanager
def abrir(paciente_id: int, db_path: Path = DB_PATH_PADRAO):
    db = ClaudiaDB(paciente_id=paciente_id, db_path=db_path)
    try:
        with db:
            yield db
    finally:
        pass


if __name__ == "__main__":
    # Smoke test — só lista tabelas para verificar se o path está correto.
    conn = sqlite3.connect(DB_PATH_PADRAO)
    conn.row_factory = sqlite3.Row
    tabelas = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )]
    print(f"DB: {DB_PATH_PADRAO}")
    print(f"Tabelas: {len(tabelas)}")
    for t in tabelas:
        print(f"  - {t}")
    conn.close()
