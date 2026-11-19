
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT_DIR / "data" / "database" / "olist.db"


@st.cache_data
def carregar_avaliacoes_por_nota(caminho_banco: str) -> pd.DataFrame:
    """Consulta no SQLite a quantidade de avaliações em cada nota."""
    with sqlite3.connect(caminho_banco) as conexao:
        contagens = pd.read_sql_query(
            "SELECT review_score AS nota, COUNT(*) AS avaliacoes "
            "FROM reviews_clean GROUP BY review_score",
            conexao,
        )
    return (
        contagens.set_index("nota")
        .reindex([1, 2, 3, 4, 5], fill_value=0)
        .rename_axis("Nota")
    )


def main() -> None:

    st.set_page_config(page_title="Avaliações Olist", page_icon="⭐")
    st.title("Avaliações por nota")
    st.caption("Quantidade de avaliações em cada nota, de 1 a 5 estrelas.")

    if not DATABASE_PATH.is_file():
        st.error("Banco SQLite não encontrado. Execute `python app.py` para preparar os dados.")
        st.stop()

    try:
        dados = carregar_avaliacoes_por_nota(str(DATABASE_PATH))
    except sqlite3.Error as erro:
        st.error(f"Não foi possível consultar a tabela reviews_clean: {erro}")
        st.stop()

    st.bar_chart(dados, x_label="Nota", y_label="Número de avaliações")
    st.metric("Total de avaliações", f"{int(dados['avaliacoes'].sum()):,}")


if __name__ == "__main__":
    main()
