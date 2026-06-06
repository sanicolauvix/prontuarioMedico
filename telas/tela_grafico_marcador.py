# -*- coding: utf-8 -*-
# Prontuario | telas/tela_grafico_marcador.py
"""
Tela de gráfico de um marcador específico.
Usa shared.grafico.renderizar_grafico_combinado — rotina única do app.
"""
import flet as ft
import logging
import sqlite3

from shared.layout import Layout
from shared.grafico import renderizar_grafico_combinado
from dados.model_prontuario import DB_PATH

BG   = "#0D1117"; CARD = "#161B22"; BD  = "#21262D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"; MUT = "#484F58"

log = logging.getLogger(__name__)


def criar_tela_grafico_marcador(
    page: ft.Page,
    voltar_fn,
    label: str,
    termos: list,
    cor: str,
) -> ft.Container:
    """
    Tela completa com cabeçalho + gráfico de um marcador.
    Usa renderizar_grafico_combinado de shared/grafico.py.
    """
    lay = Layout(page)

    # Busca histórico do parâmetro no banco
    def _buscar_historico() -> list:
        pontos = []
        try:
            conn = sqlite3.connect(DB_PATH, timeout=30)
            for termo in termos:
                rows = conn.execute("""
                    SELECT r.valor, r.unidade, e.data_exame,
                           r.referencia, r.nivel_interpretacao,
                           e.laboratorio, e.drive_file_id
                    FROM exame_resultados r
                    JOIN exames e ON r.exame_id = e.id
                    WHERE LOWER(COALESCE(r.parametro,'')) LIKE ?
                      AND r.valor IS NOT NULL AND r.valor != ''
                    ORDER BY e.data_exame ASC
                """, (f"%{termo.lower()}%",)).fetchall()
                for valor, uni, data, ref, nivel, lab, did in rows:
                    pontos.append({
                        "valor":       valor,
                        "unidade":     uni or "",
                        "data":        data or "",
                        "referencia":  ref or "",
                        "nivel":       nivel or "sem_referencia",
                        "laboratorio": lab or "",
                        "drive_id":    did or "",
                    })
                # Também busca em marcadores_leituras
                try:
                    rows2 = conn.execute("""
                        SELECT CAST(valor AS TEXT), unidade, data_medicao,
                               '', '', '', ''
                        FROM marcadores_leituras
                        WHERE LOWER(parametro) LIKE ?
                        ORDER BY data_medicao ASC
                    """, (f"%{termo.lower()}%",)).fetchall()
                    for valor, uni, data, ref, nivel, lab, did in rows2:
                        pontos.append({
                            "valor": valor, "unidade": uni or "",
                            "data": data or "", "referencia": "",
                            "nivel": "sem_referencia",
                            "laboratorio": "", "drive_id": "",
                        })
                except Exception:
                    pass
                if pontos:
                    break
            conn.close()
        except Exception as ex:
            log.warning("[GRAFICO %s] %s", label, ex)
        pontos.sort(key=lambda x: x["data"])
        return pontos[-30:]

    historico = _buscar_historico()

    exame_sel = {
        "nome_oficial": label,
        "unidade":      historico[0]["unidade"] if historico else "",
        "historico":    historico,
    }

    grafico = renderizar_grafico_combinado(page, [exame_sel])

    area = ft.Column(
        [grafico],
        spacing=12, scroll=ft.ScrollMode.AUTO, expand=True,
    )

    cabecalho = lay.criar_cabecalho(
        label, voltar_fn,
        icone_titulo="bar_chart_rounded",
        cor_titulo=cor,
    )
    corpo = lay.criar_corpo(cabecalho, area)
    return ft.Container(bgcolor=BG, expand=True, content=corpo)
