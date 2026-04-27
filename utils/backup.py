# -*- coding: utf-8 -*-
# Prestanista v1.0 | gerado: 2026-03-13 | utils/backup.py
import sqlite3, csv, pathlib, zipfile, datetime
from app_log import debug, erro, info

DB_PATH  = pathlib.Path(__file__).parent.parent / "database" / "app.db"
BCK_DIR  = pathlib.Path(__file__).parent.parent / "backups"


def exportar_csv(destino: pathlib.Path = None) -> pathlib.Path:
    """Exporta todas as tabelas para CSV individuais e compacta em ZIP."""
    try:
        BCK_DIR.mkdir(exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        pasta_exp = BCK_DIR / f"backup_{timestamp}"
        pasta_exp.mkdir(exist_ok=True)

        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        tabelas = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

        for t in tabelas:
            nome = t[0]
            rows = conn.execute(f"SELECT * FROM {nome}").fetchall()
            if not rows:
                continue
            csv_path = pasta_exp / f"{nome}.csv"
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows([dict(r) for r in rows])
        conn.close()

        # Compacta
        zip_path = destino or (BCK_DIR / f"prestanista_backup_{timestamp}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for arq in pasta_exp.iterdir():
                zf.write(arq, arq.name)

        # Remove pasta temporria
        import shutil
        shutil.rmtree(pasta_exp)

        info("backup", f"backup gerado: {zip_path}")
        return zip_path
    except Exception as ex:
        erro("backup", "exportar_csv", ex)
        return None


def listar_backups() -> list:
    """Retorna lista de backups disponíveis."""
    try:
        BCK_DIR.mkdir(exist_ok=True)
        return sorted(BCK_DIR.glob("*.zip"), reverse=True)
    except Exception as ex:
        erro("backup", "listar_backups", ex)
        return []
