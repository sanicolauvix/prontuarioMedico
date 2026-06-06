# -*- coding: utf-8 -*-
"""
tela_pendencias.py — Koios Prontuário
2 abas: Parâmetros (nao_identificado) e PDFs Incompatíveis
"""

import flet as ft
import sqlite3
import webbrowser

BG    = "#0D1117"
CARD  = "#161B22"
HOVER = "#21262D"
BD    = "#21262D"
TXT   = "#E6EDF3"
SEC   = "#8B949E"
MUT   = "#484F58"
AZUL  = "#58A6FF"
VERD  = "#3FB950"
LAR   = "#F0883E"
AMAR  = "#D29922"
VERM  = "#DA3633"
SALM  = "#FF7B72"


def _borda_esq(cor):
    return ft.Border(
        left=ft.BorderSide(3, cor),
        top=ft.BorderSide(1, BD),
        bottom=ft.BorderSide(1, BD),
        right=ft.BorderSide(1, BD),
    )


# ══════════════════════════════════════════════════════════════
# ABA PARÂMETROS
# ══════════════════════════════════════════════════════════════

def _aba_parametros(page, voltar_fn):
    from dados.limpeza import buscar_nao_identificados, ignorar_parametro, executar_limpeza
    from dados.model_prontuario import DB_PATH

    lista    = ft.Column(spacing=6)
    txt_info = ft.Text("", size=12, color=SEC)

    def _snack(msg, cor=VERD):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, color=TXT), bgcolor=CARD)
        page.snack_bar.open = True
        page.update()

    def _recarregar():
        nova = criar_tela_pendencias(page, voltar_fn=voltar_fn)
        page.controls.clear()
        page.controls.append(nova)
        page.update()

    def _visualizar(parametro):
        conn = sqlite3.connect(DB_PATH, timeout=30)
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(exames)").fetchall()]
            order_col = next(
                (c for c in ["data_exame", "data_coleta", "data", "created_at", "id"] if c in cols), "id")
            row = conn.execute(f"""
                SELECT e.drive_file_id
                FROM exame_resultados r
                JOIN exames e ON r.exame_id = e.id
                WHERE r.parametro = ?
                  AND e.drive_file_id IS NOT NULL
                  AND e.drive_file_id != ''
                ORDER BY e.{order_col} DESC LIMIT 1
            """, (parametro,)).fetchone()
        finally:
            conn.close()
        if row and row[0]:
            webbrowser.open(f"https://drive.google.com/file/d/{row[0]}/view")
        else:
            _snack("PDF não encontrado no banco.", AMAR)

    def _ignorar(parametro):
        ignorar_parametro(parametro)
        _snack("Ignorado.", SEC)
        _recarregar()

    def _incluir(parametro):
        from .tela_incluir_exame_padrao import criar_tela_incluir_exame_padrao
        nova = criar_tela_incluir_exame_padrao(page, parametro=parametro, voltar_fn=_recarregar)
        page.controls.clear()
        page.controls.append(nova)
        page.update()

    def carregar():
        lista.controls.clear()
        pendentes = buscar_nao_identificados()

        if not pendentes:
            txt_info.value = ""
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("check_circle_outline_rounded", size=44, color=VERD),
                    ft.Text("Nenhuma pendência!", size=15, color=VERD,
                            weight=ft.FontWeight.W_600),
                    ft.Text("Todos os parâmetros identificados.", size=12, color=SEC),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                alignment=ft.alignment.Alignment(0, 0), padding=40,
            ))
            page.update()
            return

        txt_info.value = f"{len(pendentes)} parâmetro(s) pendente(s)"

        for item in pendentes:
            param = item["parametro"]
            ocorr = item["ocorrencias"]

            conf = ft.Container(visible=False)

            def _faz_visualizar(p):
                return lambda e: _visualizar(p)

            def _faz_mostrar_conf(p, c):
                def _click(e):
                    c[0].visible = True
                    page.update()
                return _click

            def _faz_cancelar(c):
                def _click(e):
                    c[0].visible = False
                    page.update()
                return _click

            def _faz_ignorar_ok(p):
                return lambda e: _ignorar(p)

            def _faz_incluir(p):
                return lambda e: _incluir(p)

            conf = ft.Container(
                visible=False,
                content=ft.Row([
                    ft.Icon("warning_amber_outlined_rounded", size=14, color=SALM),
                    ft.Text("Confirmar ignorar?", size=12, color=SALM, expand=True),
                    ft.Container(
                        content=ft.Text("Cancelar", size=13, color=SEC),
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        border_radius=8, ink=True,
                        on_click=None,
                    ),
                    ft.FilledButton("Ignorar",
                        style=ft.ButtonStyle(
                            bgcolor=SALM,
                            shape=ft.RoundedRectangleBorder(radius=7),
                            padding=ft.padding.symmetric(horizontal=12, vertical=6),
                        ),
                        on_click=None),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=f"{SALM}11", border_radius=6,
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
            )
            conf_ref = [conf]
            conf.content.controls[2].on_click = _faz_cancelar(conf_ref)
            conf.content.controls[3].on_click = _faz_ignorar_ok(param)

            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("help_outline_rounded", size=14, color=LAR),
                        ft.Text(param, size=13, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True),
                        ft.Container(
                            content=ft.Text(f"{ocorr}x", size=10, color=LAR,
                                            weight=ft.FontWeight.W_700),
                            bgcolor=f"{LAR}22", border_radius=10,
                            padding=ft.padding.symmetric(horizontal=7, vertical=2),
                        ),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row([
                        ft.OutlinedButton(
                            content=ft.Row([ft.Icon("picture_as_pdf_outlined_rounded", size=14),
                                            ft.Text("Visualizar", size=12)], spacing=4, tight=True),
                            style=ft.ButtonStyle(color=AZUL, side=ft.BorderSide(1, AZUL),
                                shape=ft.RoundedRectangleBorder(radius=7),
                                padding=ft.padding.symmetric(horizontal=12, vertical=6)),
                            on_click=_faz_visualizar(param),
                        ),
                        ft.OutlinedButton(
                            content=ft.Row([ft.Icon("block_outlined_rounded", size=14),
                                            ft.Text("Ignorar", size=12)], spacing=4, tight=True),
                            style=ft.ButtonStyle(color=SALM, side=ft.BorderSide(1, SALM),
                                shape=ft.RoundedRectangleBorder(radius=7),
                                padding=ft.padding.symmetric(horizontal=12, vertical=6)),
                            on_click=_faz_mostrar_conf(param, conf_ref),
                        ),
                        ft.FilledButton(
                            content=ft.Row([ft.Icon("add_outlined_rounded", size=14),
                                            ft.Text("Incluir", size=12,
                                                    weight=ft.FontWeight.W_600)], spacing=4, tight=True),
                            style=ft.ButtonStyle(bgcolor=VERD,
                                shape=ft.RoundedRectangleBorder(radius=7),
                                padding=ft.padding.symmetric(horizontal=12, vertical=6)),
                            on_click=_faz_incluir(param),
                        ),
                    ], spacing=8),
                    conf,
                ], spacing=8),
                bgcolor=CARD, border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=12),
                border=_borda_esq(LAR),
            ))

        page.update()

    carregar()

    return ft.Column([
        ft.Row([
            txt_info,
            ft.Container(expand=True),
            ft.FilledButton(
                content=ft.Row([
                    ft.Icon("refresh_rounded", size=16, color=TXT),
                    ft.Text("Reprocessar", size=13, weight=ft.FontWeight.W_600, color=TXT),
                ], spacing=6, tight=True),
                style=ft.ButtonStyle(
                    bgcolor=AZUL,
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=16, vertical=10),
                ),
                on_click=lambda e: (executar_limpeza(), _recarregar()),
            ),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        lista,
    ], spacing=8, expand=True)


# ══════════════════════════════════════════════════════════════
# ABA PDFs INCOMPATÍVEIS
# ══════════════════════════════════════════════════════════════

def _aba_incompativeis(page, voltar_fn):
    from dados.model_prontuario import DB_PATH

    lista = ft.Column(spacing=6)
    txt_info = ft.Text("", size=12, color=SEC)

    def _snack(msg, cor=VERD):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, color=TXT), bgcolor=CARD)
        page.snack_bar.open = True
        page.update()

    def _recarregar():
        nova = criar_tela_pendencias(page, voltar_fn=voltar_fn)
        page.controls.clear()
        page.controls.append(nova)
        page.update()

    def _visualizar(drive_file_id):
        if drive_file_id:
            webbrowser.open(f"https://drive.google.com/file/d/{drive_file_id}/view")
        else:
            _snack("Drive ID não encontrado.", AMAR)

    def _excluir(pid, nome):
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.execute("DELETE FROM pdfs_incompativeis WHERE id = ?", (pid,))
        conn.commit()
        conn.close()
        _snack(f"'{nome}' removido.", SEC)
        _recarregar()

    def carregar():
        lista.controls.clear()
        conn = sqlite3.connect(DB_PATH, timeout=30)
        rows = conn.execute("""
            SELECT id, nome_arquivo, drive_file_id, motivo,
                   tamanho_kb, registrado_em
            FROM pdfs_incompativeis
            ORDER BY registrado_em DESC
        """).fetchall()
        conn.close()

        if not rows:
            txt_info.value = ""
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("check_circle_outline_rounded", size=44, color=VERD),
                    ft.Text("Nenhum PDF incompatível!", size=15, color=VERD,
                            weight=ft.FontWeight.W_600),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                alignment=ft.alignment.Alignment(0, 0), padding=40,
            ))
            page.update()
            return

        txt_info.value = f"{len(rows)} PDF(s) incompatível(is)"

        for row in rows:
            pid, nome, drive_id, motivo, tam, data = row

            conf = ft.Container(visible=False)

            def _faz_visualizar(did):
                return lambda e: _visualizar(did)

            def _faz_mostrar_conf(c):
                def _click(e):
                    c[0].visible = True
                    page.update()
                return _click

            def _faz_cancelar(c):
                def _click(e):
                    c[0].visible = False
                    page.update()
                return _click

            def _faz_excluir(i, n):
                return lambda e: _excluir(i, n)

            conf = ft.Container(
                visible=False,
                content=ft.Row([
                    ft.Icon("warning_amber_outlined_rounded", size=14, color=VERM),
                    ft.Text("Confirmar exclusão?", size=12, color=VERM, expand=True),
                    ft.Container(
                        content=ft.Text("Cancelar", size=13, color=SEC),
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        border_radius=8, ink=True,
                        on_click=None,
                    ),
                    ft.FilledButton("Excluir",
                        style=ft.ButtonStyle(
                            bgcolor=VERM,
                            shape=ft.RoundedRectangleBorder(radius=7),
                            padding=ft.padding.symmetric(horizontal=12, vertical=6),
                        ),
                        on_click=None),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=f"{VERM}11", border_radius=6,
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
            )
            conf_ref = [conf]
            conf.content.controls[2].on_click = _faz_cancelar(conf_ref)
            conf.content.controls[3].on_click = _faz_excluir(pid, nome)

            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("picture_as_pdf_rounded", size=14, color=SALM),
                        ft.Text(nome or "sem nome", size=13, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True),
                        ft.Text(f"{tam or '?'} KB", size=10, color=MUT),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(motivo or "", size=11, color=AMAR),
                    ft.Text(str(data or "")[:16], size=10, color=MUT),
                    ft.Row([
                        ft.OutlinedButton(
                            content=ft.Row([ft.Icon("open_in_new_rounded", size=14),
                                            ft.Text("Visualizar", size=12)], spacing=4, tight=True),
                            style=ft.ButtonStyle(color=AZUL, side=ft.BorderSide(1, AZUL),
                                shape=ft.RoundedRectangleBorder(radius=7),
                                padding=ft.padding.symmetric(horizontal=12, vertical=6)),
                            on_click=_faz_visualizar(drive_id),
                        ),
                        ft.OutlinedButton(
                            content=ft.Row([ft.Icon("delete_outline_rounded", size=14),
                                            ft.Text("Excluir", size=12)], spacing=4, tight=True),
                            style=ft.ButtonStyle(color=VERM, side=ft.BorderSide(1, VERM),
                                shape=ft.RoundedRectangleBorder(radius=7),
                                padding=ft.padding.symmetric(horizontal=12, vertical=6)),
                            on_click=_faz_mostrar_conf(conf_ref),
                        ),
                    ], spacing=8),
                    conf,
                ], spacing=6),
                bgcolor=CARD, border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=12),
                border=_borda_esq(SALM),
            ))

        page.update()

    carregar()
    return ft.Column([
        ft.Row([txt_info], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        lista,
    ], spacing=8, expand=True)


# ══════════════════════════════════════════════════════════════
# ABA CONFERÊNCIA
# ══════════════════════════════════════════════════════════════

def _aba_conferencia(page, voltar_fn):
    from dados.model_prontuario import DB_PATH
    import webbrowser

    lista = ft.Column(spacing=12)
    txt_status = ft.Text("", size=12, color=SEC)

    def _snack(msg, cor=VERD):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, color=TXT), bgcolor=CARD)
        page.snack_bar.open = True
        page.update()

    def _recarregar():
        nova = criar_tela_pendencias(page, voltar_fn=voltar_fn)
        page.controls.clear()
        page.controls.append(nova)
        page.update()

    def _excluir_exame(eid):
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.execute("DELETE FROM exames WHERE id = ?", (eid,))
        conn.commit()
        conn.close()
        _snack(f"Exame #{eid} removido.", SEC)
        _recarregar()

    def _ignorar_param(parametro):
        from dados.limpeza import ignorar_parametro
        ignorar_parametro(parametro)
        _snack(f"Ignorado.", SEC)
        _recarregar()

    def _incluir_padrao(parametro):
        from .tela_incluir_exame_padrao import criar_tela_incluir_exame_padrao
        nova = criar_tela_incluir_exame_padrao(page, parametro=parametro,
                                               voltar_fn=_recarregar)
        page.controls.clear()
        page.controls.append(nova)
        page.update()

    def _ir_exames_padrao():
        from .tela_exames_padrao import criar_tela_exames_padrao
        nova = criar_tela_exames_padrao(page, voltar_fn=_recarregar)
        page.controls.clear()
        page.controls.append(nova)
        page.update()

    def _conf_inline(msg, cor, on_ok):
        conf = ft.Container(visible=False)
        def _mostrar(c): c[0].visible = True; page.update()
        def _cancelar(c): c[0].visible = False; page.update()
        conf = ft.Container(
            visible=False,
            content=ft.Row([
                ft.Icon("warning_amber_outlined_rounded", size=14, color=cor),
                ft.Text(msg, size=12, color=cor, expand=True),
                ft.Container(
                    content=ft.Text("Cancelar", size=13, color=SEC),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    border_radius=8, ink=True,
                ),
                ft.FilledButton("Confirmar",
                    style=ft.ButtonStyle(bgcolor=cor,
                        shape=ft.RoundedRectangleBorder(radius=7),
                        padding=ft.padding.symmetric(horizontal=12, vertical=6)),
                    on_click=lambda e: on_ok()),
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=f"{cor}11", border_radius=6,
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
        )
        conf_ref = [conf]
        conf.content.controls[2].on_click = lambda e: _cancelar(conf_ref)
        return conf, conf_ref, lambda: _mostrar(conf_ref)

    def carregar():
        lista.controls.clear()

        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row

        sem_res = conn.execute("""
            SELECT e.id, e.tipo_exame, e.data_exame, e.laboratorio,
                   e.drive_file_id, p.nome as paciente
            FROM exames e
            LEFT JOIN pacientes p ON e.paciente_id = p.id
            WHERE e.tipo = 'numerico'
              AND NOT EXISTS (
                  SELECT 1 FROM exame_resultados r WHERE r.exame_id = e.id)
            ORDER BY e.data_exame DESC
        """).fetchall()

        nao_vinc = conn.execute("""
            SELECT r.parametro, COUNT(*) as ocorrencias,
                   COUNT(DISTINCT r.exame_id) as exames,
                   MAX(r.unidade) as unidade
            FROM exame_resultados r
            WHERE (r.exame_padrao_id IS NULL OR r.exame_padrao_id = 0)
              AND (r.nivel_interpretacao IS NULL
                   OR r.nivel_interpretacao NOT IN ('ignorado'))
            GROUP BY r.parametro ORDER BY ocorrencias DESC
        """).fetchall()

        sem_ref = conn.execute("""
            SELECT ep.id, ep.nome_oficial, ep.categoria, ep.unidade,
                   COUNT(re.id) as usos
            FROM exames_padrao ep
            LEFT JOIN referencias_padrao r ON ep.id = r.exame_padrao_id
            LEFT JOIN exame_resultados re ON ep.id = re.exame_padrao_id
            WHERE ep.ativo = 1
            GROUP BY ep.id HAVING COUNT(r.id) = 0
            ORDER BY usos DESC
        """).fetchall()

        conn.close()

        total = len(sem_res) + len(nao_vinc) + len(sem_ref)
        txt_status.value = "Banco íntegro ✓" if total == 0 else f"{total} problema(s) encontrado(s)"

        if total == 0:
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("verified_outlined_rounded", size=48, color=VERD),
                    ft.Text("Tudo em ordem!", size=15, color=VERD,
                            weight=ft.FontWeight.W_700),
                    ft.Text("Nenhum problema encontrado.", size=12, color=SEC),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                alignment=ft.alignment.Alignment(0, 0), padding=50,
            ))
            page.update()
            return

        # ── Seção 1: Exames sem resultados ────────────────────
        cards1 = ft.Column(spacing=6)
        for item in sem_res:
            item = dict(item)
            conf, conf_ref, mostrar = _conf_inline(
                "Confirmar exclusão?", VERM,
                lambda eid=item["id"]: _excluir_exame(eid))
            cards1.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("description_outlined_rounded", size=14, color=AMAR),
                        ft.Text(item["tipo_exame"] or "Sem tipo", size=13,
                                color=TXT, weight=ft.FontWeight.W_600, expand=True),
                        ft.Text(str(item["data_exame"] or "")[:10], size=11, color=MUT),
                    ], spacing=8),
                    ft.Text(item["paciente"] or "Paciente desconhecido",
                            size=11, color=SEC),
                    ft.Row([
                        ft.OutlinedButton(
                            content=ft.Row([ft.Icon("open_in_new_rounded", size=14),
                                            ft.Text("Ver PDF", size=12)],
                                           spacing=4, tight=True),
                            style=ft.ButtonStyle(color=AZUL, side=ft.BorderSide(1, AZUL),
                                shape=ft.RoundedRectangleBorder(radius=7),
                                padding=ft.padding.symmetric(horizontal=12, vertical=6)),
                            on_click=lambda e, d=item["drive_file_id"]: webbrowser.open(
                                f"https://drive.google.com/file/d/{d}/view") if d else None,
                            visible=bool(item.get("drive_file_id")),
                        ),
                        ft.OutlinedButton(
                            content=ft.Row([ft.Icon("delete_outline_rounded", size=14),
                                            ft.Text("Excluir", size=12)],
                                           spacing=4, tight=True),
                            style=ft.ButtonStyle(color=VERM, side=ft.BorderSide(1, VERM),
                                shape=ft.RoundedRectangleBorder(radius=7),
                                padding=ft.padding.symmetric(horizontal=12, vertical=6)),
                            on_click=lambda e, m=mostrar: m(),
                        ),
                    ], spacing=8),
                    conf,
                ], spacing=6),
                bgcolor=CARD, border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=12),
                border=ft.Border(left=ft.BorderSide(3, AMAR),
                                 top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                                 right=ft.BorderSide(1, BD)),
            ))

        lista.controls.append(_bloco_secao(
            "description_outlined_rounded", "Exames sem resultados",
            len(sem_res), AMAR, cards1))

        # ── Seção 2: Não vinculados ───────────────────────────
        cards2 = ft.Column(spacing=6)
        for item in nao_vinc:
            item = dict(item)
            conf, conf_ref, mostrar = _conf_inline(
                "Confirmar ignorar?", SALM,
                lambda p=item["parametro"]: _ignorar_param(p))
            cards2.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("link_off_rounded", size=14, color=LAR),
                        ft.Text(item["parametro"], size=13, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True),
                        ft.Container(
                            content=ft.Text(f"{item['ocorrencias']}x", size=10,
                                            color=LAR, weight=ft.FontWeight.W_700),
                            bgcolor=f"{LAR}22", border_radius=10,
                            padding=ft.padding.symmetric(horizontal=7, vertical=2)),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(f"{item['exames']} exame(s) · {item['unidade'] or 'sem unidade'}",
                            size=11, color=SEC),
                    ft.Row([
                        ft.OutlinedButton(
                            content=ft.Row([ft.Icon("block_outlined_rounded", size=14),
                                            ft.Text("Ignorar", size=12)],
                                           spacing=4, tight=True),
                            style=ft.ButtonStyle(color=SALM, side=ft.BorderSide(1, SALM),
                                shape=ft.RoundedRectangleBorder(radius=7),
                                padding=ft.padding.symmetric(horizontal=12, vertical=6)),
                            on_click=lambda e, m=mostrar: m(),
                        ),
                        ft.FilledButton(
                            content=ft.Row([ft.Icon("add_outlined_rounded", size=14),
                                            ft.Text("Incluir Padrão", size=12,
                                                    weight=ft.FontWeight.W_600)],
                                           spacing=4, tight=True),
                            style=ft.ButtonStyle(bgcolor=VERD,
                                shape=ft.RoundedRectangleBorder(radius=7),
                                padding=ft.padding.symmetric(horizontal=12, vertical=6)),
                            on_click=lambda e, p=item["parametro"]: _incluir_padrao(p),
                        ),
                    ], spacing=8),
                    conf,
                ], spacing=6),
                bgcolor=CARD, border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=12),
                border=ft.Border(left=ft.BorderSide(3, LAR),
                                 top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                                 right=ft.BorderSide(1, BD)),
            ))

        lista.controls.append(_bloco_secao(
            "link_off_rounded", "Resultados não vinculados",
            len(nao_vinc), LAR, cards2))

        # ── Seção 3: Sem referências ──────────────────────────
        cards3 = ft.Column(spacing=6)
        for item in sem_ref:
            item = dict(item)
            cards3.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("rule_outlined_rounded", size=14, color=AZUL),
                        ft.Text(item["nome_oficial"], size=13, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True),
                        ft.Container(
                            content=ft.Text(f"{item['usos']} uso(s)", size=10,
                                            color=AZUL, weight=ft.FontWeight.W_700),
                            bgcolor=f"{AZUL}22", border_radius=10,
                            padding=ft.padding.symmetric(horizontal=7, vertical=2)),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(f"{item['categoria'] or 'Sem categoria'} · {item['unidade'] or 'sem unidade'}",
                            size=11, color=SEC),
                    ft.FilledButton(
                        content=ft.Row([ft.Icon("edit_outlined_rounded", size=14),
                                        ft.Text("Adicionar Referências", size=12,
                                                weight=ft.FontWeight.W_600)],
                                       spacing=4, tight=True),
                        style=ft.ButtonStyle(bgcolor=AZUL,
                            shape=ft.RoundedRectangleBorder(radius=7),
                            padding=ft.padding.symmetric(horizontal=12, vertical=6)),
                        on_click=lambda e: _ir_exames_padrao(),
                    ),
                ], spacing=6),
                bgcolor=CARD, border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=12),
                border=ft.Border(left=ft.BorderSide(3, AZUL),
                                 top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                                 right=ft.BorderSide(1, BD)),
            ))

        lista.controls.append(_bloco_secao(
            "rule_outlined_rounded", "Exames padrão sem referências",
            len(sem_ref), AZUL, cards3))

        page.update()

    carregar()
    return ft.Column([
        ft.Row([txt_status, ft.Container(expand=True),
                ft.Container(
                    content=ft.Row([ft.Icon("refresh_rounded", size=13),
                                    ft.Text("Atualizar", size=12)],
                                   spacing=4, tight=True),
                    padding=ft.padding.symmetric(horizontal=8, vertical=8),
                    ink=True,
                    on_click=lambda e: _recarregar(),
                )], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        lista,
    ], spacing=8, expand=True)


def _bloco_secao(icone, titulo, n, cor, conteudo_col):
    badge = ft.Container(
        content=ft.Text(str(n), size=10, color=cor if n > 0 else VERD,
                        weight=ft.FontWeight.W_700),
        bgcolor=f"{(cor if n > 0 else VERD)}22", border_radius=10,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
    )
    return ft.Container(
        content=ft.Column([
            ft.Row([ft.Icon(icone, size=16, color=cor),
                    ft.Text(titulo, size=14, color=TXT, weight=ft.FontWeight.W_700),
                    badge], spacing=8),
            ft.Container(height=4),
            conteudo_col if n > 0 else ft.Text("Nenhum problema.", size=12, color=VERD),
        ], spacing=6),
        bgcolor=f"{cor}08", border_radius=10, padding=ft.padding.all(14),
        border=ft.Border(left=ft.BorderSide(2, cor),
                         top=ft.BorderSide(1, BD), bottom=ft.BorderSide(1, BD),
                         right=ft.BorderSide(1, BD)),
    )


# ══════════════════════════════════════════════════════════════
# ABA ESPECIALIDADES DOS MÉDICOS
# ══════════════════════════════════════════════════════════════

def _aba_especialidades(page, voltar_fn):
    from dados.model_prontuario import DB_PATH

    lista    = ft.Column(spacing=6)
    txt_info = ft.Text("", size=12, color=SEC)

    def _snack(msg, cor=VERD):
        page.snack_bar = ft.SnackBar(ft.Text(msg, color=TXT), bgcolor=CARD)
        page.snack_bar.open = True
        page.update()

    def _recarregar():
        nova = criar_tela_pendencias(page, voltar_fn=voltar_fn)
        page.controls.clear()
        page.controls.append(nova)
        page.update()

    def _salvar_especialidade(medico_id, dd, txt_esp):
        esp = dd.value or txt_esp.value.strip()
        if not esp:
            _snack("Informe a especialidade.", AMAR)
            return
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.execute(
            "UPDATE medicos SET especialidade=? WHERE id=?",
            (esp, medico_id)
        )
        conn.commit()
        conn.close()
        _snack(f"Especialidade salva: {esp}", VERD)
        _recarregar()

    def carregar():
        lista.controls.clear()
        conn = sqlite3.connect(DB_PATH, timeout=30)
        rows = conn.execute("""
            SELECT m.id, m.nome, m.crm,
                   COUNT(DISTINCT c.id) as consultas,
                   COUNT(DISTINCT e.id) as exames
            FROM medicos m
            LEFT JOIN consultas c  ON c.medico_id  = m.id
            LEFT JOIN exames    e  ON e.medico_id  = m.id
            WHERE m.ativo = 1
              AND (m.especialidade IS NULL OR m.especialidade = '')
              AND (m.especialidade_id IS NULL)
            GROUP BY m.id
            ORDER BY (consultas + exames) DESC, m.nome
        """).fetchall()

        especialidades_opcoes = conn.execute(
            "SELECT nome FROM especialidades ORDER BY nome"
        ).fetchall()
        conn.close()

        opcoes = [ft.dropdown.Option(r[0]) for r in especialidades_opcoes]

        txt_info.value = (
            f"{len(rows)} médico(s) sem especialidade" if rows
            else "Todos os médicos com especialidade ✓"
        )

        if not rows:
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("check_circle_outline_rounded", size=44, color=VERD),
                    ft.Text("Todos os médicos classificados!", size=15,
                            color=VERD, weight=ft.FontWeight.W_600),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                alignment=ft.alignment.Alignment(0, 0), padding=40,
            ))
            page.update()
            return

        for mid, nome, crm, consultas, exames in rows:
            dd = ft.Dropdown(
                label="Especialidade",
                label_style=ft.TextStyle(color=SEC, size=11),
                text_style=ft.TextStyle(color=TXT, size=12),
                bgcolor=BG, border_color=BD, focused_border_color=AZUL,
                border_radius=6,
                content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
                options=opcoes,
                expand=True,
            )
            txt_esp = ft.TextField(
                label="Ou digitar",
                label_style=ft.TextStyle(color=SEC, size=11),
                text_style=ft.TextStyle(color=TXT, size=12),
                bgcolor=BG, border_color=BD, focused_border_color=AZUL,
                border_radius=6,
                content_padding=ft.padding.symmetric(horizontal=8, vertical=6),
                width=160,
            )
            btn = ft.Container(
                content=ft.Row([
                    ft.Icon("save_outlined_rounded", size=14, color=BG),
                    ft.Text("Salvar", size=12, color=BG, weight=ft.FontWeight.W_600),
                ], spacing=4, tight=True),
                bgcolor=AZUL, border_radius=7, ink=True,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            )
            btn.on_click = lambda e, m=mid, d=dd, t=txt_esp: _salvar_especialidade(m, d, t)

            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("person_outlined_rounded", size=14, color=AZUL),
                        ft.Text(nome, size=13, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True),
                        ft.Text(f"CRM {crm}" if crm else "", size=10, color=MUT),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(
                        f"{consultas} consulta(s) · {exames} exame(s) associado(s)",
                        size=11, color=SEC,
                    ),
                    ft.Row([dd, txt_esp, btn], spacing=8,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ], spacing=8),
                bgcolor=CARD, border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=12),
                border=_borda_esq(AZUL),
            ))

        page.update()

    carregar()
    return ft.Column([
        ft.Row([txt_info], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        lista,
    ], spacing=8, expand=True)


# ══════════════════════════════════════════════════════════════
# ABA CLASSIFICAÇÃO DE EXAMES
# ══════════════════════════════════════════════════════════════

def _aba_classificacao(page, voltar_fn):
    from dados.model_prontuario import DB_PATH

    lista    = ft.Column(spacing=6)
    txt_info = ft.Text("", size=12, color=SEC)

    def _snack(msg, cor=VERD):
        page.snack_bar = ft.SnackBar(ft.Text(msg, color=TXT), bgcolor=CARD)
        page.snack_bar.open = True
        page.update()

    def _recarregar():
        nova = criar_tela_pendencias(page, voltar_fn=voltar_fn)
        page.controls.clear()
        page.controls.append(nova)
        page.update()

    def _salvar_grupo(exame_id, dd):
        gid = dd.value
        if not gid:
            _snack("Selecione um grupo.", AMAR)
            return
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.execute("UPDATE exames SET grupo_id=? WHERE id=?", (int(gid), exame_id))
        conn.commit()
        conn.close()
        _snack("Grupo salvo.", VERD)
        _recarregar()

    def carregar():
        lista.controls.clear()
        conn = sqlite3.connect(DB_PATH, timeout=30)

        rows = conn.execute("""
            SELECT e.id, e.tipo_exame, e.laboratorio, e.data_exame,
                   e.tipo, p.nome as paciente
            FROM exames e
            LEFT JOIN pacientes p ON e.paciente_id = p.id
            WHERE e.grupo_id IS NULL
            ORDER BY e.data_exame DESC
        """).fetchall()

        grupos = conn.execute(
            "SELECT id, nome, tipo FROM grupos_exame WHERE ativo=1 ORDER BY tipo, ordem"
        ).fetchall()
        conn.close()

        txt_info.value = (
            f"{len(rows)} exame(s) sem classificação" if rows
            else "Todos os exames classificados ✓"
        )

        if not rows:
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("check_circle_outline_rounded", size=44, color=VERD),
                    ft.Text("Todos os exames classificados!", size=15,
                            color=VERD, weight=ft.FontWeight.W_600),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                alignment=ft.alignment.Alignment(0, 0), padding=40,
            ))
            page.update()
            return

        # Organiza opções por tipo
        _icone_tipo = {"sangue": "bloodtype_rounded",
                       "imagem": "image_search_rounded",
                       "outros": "more_horiz_rounded"}
        opcoes = []
        tipo_atual = ""
        for gid, gnome, gtipo in grupos:
            if gtipo != tipo_atual:
                opcoes.append(ft.dropdown.Option(
                    key=f"__{gtipo}",
                    text=f"── {gtipo.upper()} ──",
                    disabled=True,
                ))
                tipo_atual = gtipo
            opcoes.append(ft.dropdown.Option(key=str(gid), text=gnome))

        for eid, tipo_exame, lab, data, tipo, paciente in rows:
            cor_tipo = AZUL if tipo == "numerico" else LAR
            icone_tipo = "science_rounded" if tipo == "numerico" else "description_rounded"

            dd = ft.Dropdown(
                label="Selecionar grupo",
                label_style=ft.TextStyle(color=SEC, size=11),
                text_style=ft.TextStyle(color=TXT, size=12),
                bgcolor=BG, border_color=BD, focused_border_color=AZUL,
                border_radius=6,
                content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
                options=opcoes,
                expand=True,
            )
            btn = ft.Container(
                content=ft.Row([
                    ft.Icon("save_outlined_rounded", size=14, color=BG),
                    ft.Text("Salvar", size=12, color=BG, weight=ft.FontWeight.W_600),
                ], spacing=4, tight=True),
                bgcolor=VERD, border_radius=7, ink=True,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            )
            btn.on_click = lambda e, m=eid, d=dd: _salvar_grupo(m, d)

            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(icone_tipo, size=14, color=cor_tipo),
                        ft.Text(tipo_exame or "Sem tipo", size=13, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True),
                        ft.Text(str(data or "")[:10], size=10, color=MUT),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row([
                        ft.Text(lab or "Lab desconhecido", size=11, color=SEC),
                        ft.Text("·", size=11, color=MUT),
                        ft.Text(paciente or "Paciente desconhecido", size=11, color=SEC),
                    ], spacing=4),
                    ft.Row([dd, btn], spacing=8,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ], spacing=8),
                bgcolor=CARD, border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=12),
                border=_borda_esq(AMAR),
            ))

        page.update()

    carregar()
    return ft.Column([
        ft.Row([txt_info], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        lista,
    ], spacing=8, expand=True)


# ══════════════════════════════════════════════════════════════
# ABA 5 — SISTEMA (exames_padrao sem sistema)
# ══════════════════════════════════════════════════════════════

def _aba_sistema(page, voltar_fn):
    from dados.model_prontuario import DB_PATH

    lista    = ft.Column(spacing=6)
    txt_info = ft.Text("", size=12, color=SEC)

    _SISTEMAS_OPCOES = [
        "Cardiaco", "Visceral", "Psiquiatria",
        "Ortopedia", "Sangue", "Visao & Audicao",
    ]

    def _snack(msg, cor=VERD):
        page.snack_bar = ft.SnackBar(ft.Text(msg, color=TXT), bgcolor=CARD)
        page.snack_bar.open = True
        page.update()

    def _recarregar():
        nova = criar_tela_pendencias(page, voltar_fn=voltar_fn)
        page.controls.clear()
        page.controls.append(nova)
        page.update()

    def _salvar_sistema(ep_id, dd):
        val = dd.value
        if not val:
            _snack("Selecione um sistema.", AMAR)
            return
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.execute("UPDATE exames_padrao SET sistema=? WHERE id=?", (val, ep_id))
        conn.commit()
        conn.close()
        _snack("Sistema salvo.", VERD)
        _recarregar()

    def carregar():
        lista.controls.clear()
        conn = sqlite3.connect(DB_PATH, timeout=30)
        rows = conn.execute("""
            SELECT ep.id, ep.nome_oficial, ep.categoria, ep.grupo_id,
                   g.nome as grupo_nome
            FROM exames_padrao ep
            LEFT JOIN grupos_exame g ON g.id = ep.grupo_id
            WHERE ep.sistema IS NULL AND ep.ativo = 1
            ORDER BY ep.nome_oficial
        """).fetchall()
        conn.close()

        txt_info.value = (
            f"{len(rows)} exame(s) sem sistema definido" if rows
            else "Todos os exames com sistema definido ✓"
        )

        if not rows:
            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("check_circle_outline_rounded", size=44, color=VERD),
                    ft.Text("Todos os exames com sistema!", size=15,
                            color=VERD, weight=ft.FontWeight.W_600),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                alignment=ft.alignment.Alignment(0, 0), padding=40,
            ))
            page.update()
            return

        opcoes = [ft.dropdown.Option(s) for s in _SISTEMAS_OPCOES]

        for ep_id, nome, categoria, grupo_id, grupo_nome in rows:
            dd = ft.Dropdown(
                label="Selecionar sistema",
                label_style=ft.TextStyle(color=SEC, size=11),
                text_style=ft.TextStyle(color=TXT, size=12),
                bgcolor=BG, border_color=BD, focused_border_color=ROXO,
                border_radius=6,
                content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
                options=opcoes,
                expand=True,
            )
            btn = ft.Container(
                content=ft.Row([
                    ft.Icon("save_outlined_rounded", size=14, color=BG),
                    ft.Text("Salvar", size=12, color=BG, weight=ft.FontWeight.W_600),
                ], spacing=4, tight=True),
                bgcolor=ROXO, border_radius=7, ink=True,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            )
            btn.on_click = lambda e, m=ep_id, d=dd: _salvar_sistema(m, d)

            lista.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("biotech_rounded", size=14, color=ROXO),
                        ft.Text(nome or "Sem nome", size=13, color=TXT,
                                weight=ft.FontWeight.W_600, expand=True),
                    ], spacing=8),
                    ft.Text(grupo_nome or categoria or "Sem grupo", size=11, color=SEC),
                    ft.Row([dd, btn], spacing=8,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ], spacing=8),
                bgcolor=CARD, border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=12),
                border=_borda_esq(ROXO),
            ))

        page.update()

    carregar()
    return ft.Column([
        ft.Row([txt_info], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        lista,
    ], spacing=8, expand=True)


# ══════════════════════════════════════════════════════════════
# TELA PRINCIPAL COM ABAS
# ══════════════════════════════════════════════════════════════

def criar_tela_pendencias(page: ft.Page, voltar_fn=None):
    from dados.limpeza import executar_limpeza

    aba_ativa = [0]
    conteudo  = ft.Column(spacing=0, expand=True)
    abas_row  = ft.Row(spacing=0)

    _ABAS = [
        ("Parâmetros",      LAR),
        ("PDFs",            SALM),
        ("Conferência",     AMAR),
        ("Especialidades",  AZUL),
        ("Classificação",   VERD),
        ("Sistema",         ROXO),
    ]

    def _contar_pendencias():
        """Conta pendências de cada aba para exibir badges."""
        from dados.model_prontuario import DB_PATH
        from dados.limpeza import buscar_nao_identificados
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            n_pdfs   = conn.execute("SELECT COUNT(*) FROM pdfs_incompativeis").fetchone()[0]
            n_conf   = conn.execute("""
                SELECT COUNT(*) FROM exames WHERE tipo='numerico'
                AND NOT EXISTS (SELECT 1 FROM exame_resultados r WHERE r.exame_id=exames.id)
            """).fetchone()[0]
            n_esp    = conn.execute("""
                SELECT COUNT(*) FROM medicos
                WHERE ativo=1 AND (especialidade IS NULL OR especialidade='')
                AND especialidade_id IS NULL
            """).fetchone()[0]
            n_class  = conn.execute(
                "SELECT COUNT(*) FROM exames WHERE grupo_id IS NULL"
            ).fetchone()[0]
            n_sis    = conn.execute(
                "SELECT COUNT(*) FROM exames_padrao WHERE sistema IS NULL AND ativo=1"
            ).fetchone()[0]
            conn.close()
            n_param = len(buscar_nao_identificados())
        except Exception:
            n_param = n_pdfs = n_conf = n_esp = n_class = n_sis = 0
        return [n_param, n_pdfs, n_conf, n_esp, n_class, n_sis]

    _counts = _contar_pendencias()

    def _renderizar_abas():
        abas_row.controls.clear()
        for i, (label, cor) in enumerate(_ABAS):
            ativo = aba_ativa[0] == i
            n     = _counts[i]
            def _click(e, idx=i):
                aba_ativa[0] = idx
                _renderizar_abas()
                _carregar_aba()

            badge = ft.Container(
                content=ft.Text(str(n), size=9, color=cor if n > 0 else VERD,
                                weight=ft.FontWeight.W_700),
                bgcolor=ft.Colors.with_opacity(0.18, cor if n > 0 else VERD),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=5, vertical=1),
                visible=True,
            ) if n > 0 else ft.Container(width=0)

            abas_row.controls.append(
                ft.GestureDetector(
                    content=ft.Container(
                        content=ft.Row([
                            ft.Text(
                                label, size=13,
                                color=TXT if ativo else SEC,
                                weight=ft.FontWeight.W_600 if ativo else ft.FontWeight.W_400,
                            ),
                            badge,
                        ], spacing=4, tight=True),
                        padding=ft.padding.symmetric(horizontal=14, vertical=10),
                        border=ft.Border(
                            bottom=ft.BorderSide(2, cor if ativo else "transparent")
                        ),
                    ),
                    on_tap=_click,
                )
            )
        page.update()

    def _carregar_aba():
        conteudo.controls.clear()
        idx = aba_ativa[0]
        if idx == 0:
            conteudo.controls.append(_aba_parametros(page, voltar_fn))
        elif idx == 1:
            conteudo.controls.append(_aba_incompativeis(page, voltar_fn))
        elif idx == 2:
            conteudo.controls.append(_aba_conferencia(page, voltar_fn))
        elif idx == 3:
            conteudo.controls.append(_aba_especialidades(page, voltar_fn))
        elif idx == 4:
            conteudo.controls.append(_aba_classificacao(page, voltar_fn))
        elif idx == 5:
            conteudo.controls.append(_aba_sistema(page, voltar_fn))
        page.update()

    _renderizar_abas()
    _carregar_aba()

    return ft.Column([
        # Cabeçalho
        ft.Row([
            ft.Container(
                content=ft.Row([
                    ft.Icon("arrow_back_rounded", size=14, color=SEC),
                    ft.Text("Voltar", size=12, color=SEC),
                ], spacing=4, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                ink=True,
                on_click=lambda e: voltar_fn() if voltar_fn else None,
            ),
            ft.Container(expand=True),
            ft.Text("Pendências", size=20,
                    weight=ft.FontWeight.W_700, color=TXT),
            ft.Container(expand=True),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),

        ft.Container(
            content=abas_row,
            border=ft.Border(bottom=ft.BorderSide(1, BD)),
        ),

        ft.Container(height=4),
        ft.Container(content=conteudo, expand=True),

    ], spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)