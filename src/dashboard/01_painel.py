import pandas as pd
import streamlit as st

from src.dashboard.dashboard_data import load_current_reviews


def main() -> None:
    reviews = load_current_reviews()
    if "sentimento_nota" not in reviews.columns:
        reviews = reviews.copy()
        reviews["sentimento_nota"] = reviews["nota"].map(
            {1: "Negativo", 2: "Negativo", 3: "Neutro", 4: "Positivo", 5: "Positivo"}
        )
    if "sentimento_previsto" not in reviews.columns:
        reviews = reviews.copy()
        reviews["sentimento_previsto"] = pd.NA
    if reviews.empty:
        st.info("Não há avaliações com os filtros selecionados.")
        return

    total = len(reviews)
    positive = int(reviews["sentimento_nota"].eq("Positivo").sum())
    negative = int(reviews["sentimento_nota"].eq("Negativo").sum())
    positive_predicted = int(reviews["sentimento_previsto"].eq("positivo").sum())
    negative_predicted = int(reviews["sentimento_previsto"].eq("negativo").sum())
    predicted = reviews["sentimento_previsto"].str.capitalize()
    predicted_total = int(predicted.notna().sum())
    kpis = st.columns(6)
    kpis[0].metric("Avaliações com comentário", f"{total:,}")
    kpis[1].metric("Positivas pela nota", f"{positive / total:.1%}")
    kpis[2].metric("Negativas pela nota", f"{negative / total:.1%}")
    kpis[3].metric("Positivas previstas", f"{positive_predicted / predicted_total:.1%}" if predicted_total else "—")
    kpis[4].metric("Negativas previstas", f"{negative_predicted / predicted_total:.1%}" if predicted_total else "—")
    kpis[5].metric("Nota média", f"{reviews['nota'].mean():.2f} / 5")

    monthly = reviews.dropna(subset=["data"]).copy()
    if not monthly.empty:
        monthly["mês"] = monthly["data"].dt.to_period("M").astype(str)
        monthly_counts = monthly.groupby(["mês", "sentimento_nota"]).size().unstack(fill_value=0)
        monthly_counts = monthly_counts.reindex(columns=["Positivo", "Neutro", "Negativo"], fill_value=0)

    categories = reviews.dropna(subset=["categoria"])
    if not categories.empty:
        category_distribution = pd.crosstab(categories["categoria"], categories["sentimento_nota"], normalize="index") * 100
        category_distribution = category_distribution.reindex(columns=["Positivo", "Neutro", "Negativo"], fill_value=0)
        category_distribution = category_distribution.sort_values("Negativo", ascending=False)

    with st.container(border=True):
        st.subheader("Sentimento por mês")
        if not monthly.empty:
            st.bar_chart(monthly_counts, stack="normalize", color=["#2dd4bf", "#6b7f89", "#fb7185"])
        else:
            st.info("Sem datas para o período selecionado.")

    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        st.subheader("Distribuição das notas")
        notes = reviews["nota"].value_counts(normalize=True).reindex([5, 4, 3, 2, 1], fill_value=0) * 100
        st.bar_chart(notes.rename_axis("Nota").to_frame("Percentual"), color="#93b4ff")
    with right, st.container(border=True):
        st.subheader("Sentimento por categoria")
        if not categories.empty:
            st.bar_chart(category_distribution, stack="normalize", color=["#2dd4bf", "#6b7f89", "#fb7185"])
        else:
            st.info("Sem categorias para os filtros selecionados.")

    with st.container(border=True):
        st.subheader("Sentimento pela nota e pelo modelo")
        if predicted_total:
            comparison = pd.DataFrame(
                {
                    "Sentimento pela nota": reviews["sentimento_nota"].value_counts(normalize=True),
                    "Sentimento previsto": predicted.value_counts(normalize=True),
                }
            ).T.reindex(columns=["Positivo", "Neutro", "Negativo"], fill_value=0)
            st.bar_chart(comparison, stack="normalize", color=["#2dd4bf", "#6b7f89", "#fb7185"])
        else:
            st.info("As previsões ainda não foram geradas. Execute `python app.py` para atualizar o modelo e classificar os comentários.")


main()
