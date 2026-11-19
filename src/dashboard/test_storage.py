import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = ROOT_DIR / "data" / "database" / "olist.db"


def ensure_comment_tests_table() -> None:
    """Cria a tabela local para registrar testes e rótulos revisados."""
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


def save_comment_test(
    comment_text: str, sentimento_previsto: str, confianca: float | None
) -> int:
    """Persiste uma classificação de comentário e devolve seu identificador."""
    ensure_comment_tests_table()
    with sqlite3.connect(DATABASE_PATH) as connection:
        cursor = connection.execute(
            """
            INSERT INTO comment_tests (
                comment_text, sentimento_previsto, confianca,
                sentimento_correto, created_at
            ) VALUES (?, ?, ?, NULL, ?)
            """,
            (
                comment_text,
                sentimento_previsto,
                confianca,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def update_comment_test_label(test_id: int, sentimento_correto: str) -> None:
    """Salva o sentimento correto informado para um teste."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            "UPDATE comment_tests SET sentimento_correto = ? WHERE test_id = ?",
            (sentimento_correto, test_id),
        )
        connection.commit()


def load_comment_tests(limit: int = 100) -> pd.DataFrame:
    """Carrega os testes mais recentes para exibição no dashboard."""
    ensure_comment_tests_table()
    with sqlite3.connect(DATABASE_PATH) as connection:
        return pd.read_sql_query(
            """
            SELECT test_id, comment_text, sentimento_previsto, confianca,
                   sentimento_correto, created_at
            FROM comment_tests
            ORDER BY test_id DESC
            LIMIT ?
            """,
            connection,
            params=(limit,),
        )
