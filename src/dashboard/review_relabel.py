import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = ROOT_DIR / "data" / "database" / "olist.db"


def ensure_relabel_schema() -> None:
    """Garante suporte a rótulos manuais ligados a avaliações Olist."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS comment_tests (
                test_id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_text TEXT NOT NULL,
                source_review_id TEXT,
                sentimento_previsto TEXT NOT NULL,
                confianca REAL,
                sentimento_correto TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(comment_tests)").fetchall()
        }
        if "source_review_id" not in columns:
            connection.execute(
                "ALTER TABLE comment_tests ADD COLUMN source_review_id TEXT"
            )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_comment_tests_source_review "
            "ON comment_tests(source_review_id) WHERE source_review_id IS NOT NULL"
        )
        connection.commit()


def load_review_reclassifications(
    review_ids: list[str] | None = None,
) -> pd.DataFrame:
    """Carrega rótulos manuais, opcionalmente limitados a alguns reviews."""
    ensure_relabel_schema()
    with sqlite3.connect(DATABASE_PATH) as connection:
        if review_ids is None:
            return pd.read_sql_query(
                """
                SELECT source_review_id, sentimento_correto
                FROM comment_tests
                WHERE source_review_id IS NOT NULL
                """,
                connection,
            )
        if not review_ids:
            return pd.DataFrame(columns=["source_review_id", "sentimento_correto"])
        placeholders = ",".join("?" for _ in review_ids)
        return pd.read_sql_query(
            f"""
            SELECT source_review_id, sentimento_correto
            FROM comment_tests
            WHERE source_review_id IN ({placeholders})
            """,
            connection,
            params=review_ids,
        )


def save_review_reclassification(
    review_id: str,
    comment_text: str,
    sentimento_previsto: str,
    confianca: float | None,
    sentimento_correto: str,
) -> None:
    """Salva ou atualiza o rótulo manual associado à avaliação Olist."""
    ensure_relabel_schema()
    timestamp = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DATABASE_PATH) as connection:
        existing = connection.execute(
            "SELECT test_id FROM comment_tests WHERE source_review_id = ?",
            (review_id,),
        ).fetchone()
        if existing:
            connection.execute(
                """
                UPDATE comment_tests
                SET comment_text = ?, sentimento_previsto = ?, confianca = ?,
                    sentimento_correto = ?, created_at = ?
                WHERE test_id = ?
                """,
                (
                    comment_text,
                    sentimento_previsto,
                    confianca,
                    sentimento_correto,
                    timestamp,
                    existing[0],
                ),
            )
        else:
            connection.execute(
                """
                INSERT INTO comment_tests (
                    comment_text, source_review_id, sentimento_previsto,
                    confianca, sentimento_correto, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    comment_text,
                    review_id,
                    sentimento_previsto,
                    confianca,
                    sentimento_correto,
                    timestamp,
                ),
            )
        connection.commit()
