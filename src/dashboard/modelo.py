import sqlite3

import pandas as pd
import streamlit as st

from src.dashboard.dashboard_data import DATABASE_PATH, load_model_metrics


def main() -> None:
    st.title("Desempenho do modelo")
    st.caption("Métricas do conjunto de teste e validação cruzada salvas no treinamento. Estes resultados são agregados e não mudam com os filtros globais.")
    if not DATABASE_PATH.is_file():
        st.error("Banco SQLite não encontrado. Execute `python app.py` para preparar os dados.")
        return
    try:
        metrics = load_model_metrics(str(DATABASE_PATH), DATABASE_PATH.stat().st_mtime)
    except (sqlite3.Error, pd.errors.DatabaseError) as error:
        st.error(f"Não foi possível consultar as métricas do modelo: {error}")
        return
    if metrics.empty:
        st.info("Métricas não encontradas. Execute `python app.py` para treinar e avaliar o modelo.")
        return

    summary = metrics.loc[metrics["tipo"].eq("resumo")]
    if summary.empty:
        st.warning("A tabela de métricas não contém o resumo do treinamento.")
        return
    summary = summary.iloc[0]
    with st.container(border=True):
        cards = st.columns(4)
        cards[0].metric("Modelo", summary["modelo"])
        cards[1].metric("Macro-F1 (validação cruzada)", f"{summary['cv_macro_f1']:.3f}")
        cards[2].metric("Macro-F1 (teste)", f"{summary['test_macro_f1']:.3f}")
        cards[3].metric("Acurácia (teste)", f"{summary['acuracia']:.3f}")

    classes = metrics.loc[metrics["tipo"].eq("classe"), ["classe", "precisao", "recall", "f1", "suporte"]]
    confusion = metrics.loc[metrics["tipo"].eq("confusao"), ["classe", "classe_prevista", "quantidade"]]
    matrix = None
    if not confusion.empty:
        matrix = confusion.pivot(index="classe", columns="classe_prevista", values="quantidade").fillna(0).astype(int)
    if not classes.empty or matrix is not None:
        left, right = st.columns(2)
    if not classes.empty:
        with left, st.container(border=True):
            st.subheader("Desempenho por classe")
            st.dataframe(classes.rename(columns={"classe": "Classe", "precisao": "Precisão", "recall": "Recall", "f1": "F1", "suporte": "Avaliações"}), hide_index=True, use_container_width=True)
    if matrix is not None:
        with right, st.container(border=True):
            st.subheader("Matriz de confusão")
            st.caption("Linhas indicam o sentimento real; colunas indicam a previsão.")
            st.dataframe(matrix, use_container_width=True)
    with st.container(border=True):
        st.caption("As métricas são agregadas; não há previsões individuais de teste ligadas a data, nota ou categoria.")


main()
