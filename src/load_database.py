import sqlite3
from contextlib import closing
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT_DIR / "data" / "database" / "olist.db"


def save_tables(tables: dict) -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        for name, dataframe in tables.items():
            dataframe.to_sql(name, connection, if_exists="replace", index=False)
        for table, column in (
            ("reviews", "review_score"),
            ("reviews_clean", "order_id"),
            ("review_product", "categoria"),
            ("review_delivery", "order_id"),
        ):
            connection.execute(
                f'CREATE INDEX "idx_{table}_{column}" ON "{table}" ("{column}")'
            )
        connection.commit()


