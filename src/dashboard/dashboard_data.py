import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = ROOT_DIR / "data" / "database" / "olist.db"
MODEL_PATH = ROOT_DIR / "models" / "sentiment_model.joblib"
SCORE_TO_SENTIMENT = {1: "Negativo", 2: "Negativo", 3: "Neutro", 4: "Positivo", 5: "Positivo"}


def load_reviews(database_path: str, modified_at: float) -> pd.DataFrame:
    """Carrega avaliações com comentário e seus dados de data e produto."""
    query = """
        SELECT clean.review_id, clean.order_id, clean.review_score AS nota,
               clean.comentario, clean.texto_limpo,
               original.review_creation_date AS data,
               product.categoria, product.seller_id
        FROM reviews_clean AS clean
        LEFT JOIN (
            SELECT review_id, MAX(review_creation_date) AS review_creation_date
            FROM reviews GROUP BY review_id
        ) AS original ON original.review_id = clean.review_id
        LEFT JOIN review_product AS product ON product.review_id = clean.review_id
    """
    with sqlite3.connect(database_path) as connection:
        reviews = pd.read_sql_query(query, connection)
    reviews["data"] = pd.to_datetime(reviews["data"], errors="coerce")
    reviews["sentimento_nota"] = reviews["nota"].map(SCORE_TO_SENTIMENT)
    return reviews


@st.cache_data
def load_model_metrics(database_path: str, modified_at: float) -> pd.DataFrame:
    """Carrega as métricas agregadas registradas durante o treinamento."""
    with sqlite3.connect(database_path) as connection:
        try:
            return pd.read_sql_query("SELECT * FROM model_metrics", connection)
        except sqlite3.OperationalError as error:
            if "no such table" in str(error).lower():
                return pd.DataFrame()
            raise


def filtered_reviews(reviews: pd.DataFrame) -> pd.DataFrame:
    """Aplica os filtros comuns de período e categoria."""
    result = reviews
    period = st.session_state.get("periodo") or "Todos"
    category = st.session_state.get("categoria") or "Todas"
    if period != "Todos":
        result = result.loc[result["data"].dt.year.eq(int(period))]
    if category != "Todas":
        result = result.loc[result["categoria"].eq(category)]
    return result.copy()


def load_current_reviews() -> pd.DataFrame:
    """Valida o banco e devolve avaliações com os filtros globais."""
    if not DATABASE_PATH.is_file():
        st.error("Banco SQLite não encontrado. Execute `python app.py` para preparar os dados.")
        st.stop()
    try:
        reviews = load_reviews(str(DATABASE_PATH), DATABASE_PATH.stat().st_mtime)
        with sqlite3.connect(DATABASE_PATH) as connection:
            try:
                prediction_columns = {
                    row[1]
                    for row in connection.execute(
                        "PRAGMA table_info(model_predictions)"
                    ).fetchall()
                }
                if "confianca" in prediction_columns:
                    predictions = pd.read_sql_query(
                        "SELECT review_id, sentimento_previsto, confianca FROM model_predictions",
                        connection,
                    )
                else:
                    predictions = pd.read_sql_query(
                        "SELECT review_id, sentimento_previsto FROM model_predictions",
                        connection,
                    )
                    predictions["confianca"] = pd.NA
            except sqlite3.OperationalError as error:
                if "no such table: model_predictions" not in str(error).lower():
                    raise
                predictions = pd.DataFrame(
                    columns=["review_id", "sentimento_previsto", "confianca"]
                )
    except (sqlite3.Error, pd.errors.DatabaseError) as error:
        st.error(f"Não foi possível consultar as tabelas do banco: {error}")
        st.stop()
    predictions = predictions.drop_duplicates("review_id", keep="last")
    reviews = reviews.drop(columns="sentimento_previsto", errors="ignore").merge(
        predictions,
        on="review_id",
        how="left",
        validate="one_to_one",
    )
    if "confianca" not in reviews.columns:
        reviews["confianca"] = pd.NA
    reviews["sentimento_nota"] = reviews["nota"].map(SCORE_TO_SENTIMENT)
    if "sentimento_previsto" not in reviews.columns:
        reviews["sentimento_previsto"] = pd.NA
    return filtered_reviews(reviews)
