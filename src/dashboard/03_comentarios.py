import pandas as pd
import streamlit as st

from src.dashboard.dashboard_data import load_current_reviews


def main() -> None:
    reviews = load_current_reviews()
    if "sentimento_previsto" not in reviews.columns:
        reviews = reviews.copy()
        reviews["sentimento_previsto"] = pd.NA
    if "sentimento_nota" not in reviews.columns:
        reviews = reviews.copy()
        reviews["sentimento_nota"] = reviews["nota"].map(
            {1: "Negativo", 2: "Negativo", 3: "Neutro", 4: "Positivo", 5: "Positivo"}
        )
    with st.container(border=True):
        st.subheader("Resumo das avaliações")
        total = len(reviews)
        if total:
            kpis = st.columns(3)
            predicted = reviews["sentimento_previsto"].str.capitalize()
            predicted_total = int(predicted.notna().sum())
            if not predicted_total:
                st.info("Previsões não encontradas no banco. Execute `python app.py` para atualizar os sentimentos previstos.")
            for column, label in zip(kpis, ["Negativo", "Neutro", "Positivo"]):
                count = int(reviews["sentimento_nota"].eq(label).sum())
                column.metric(f"{label} pela nota", f"{count / total:.0%}", f"{count:,} avaliações")
                predicted_count = int(predicted.eq(label).sum())
                column.metric(
                    f"{label} previsto",
                    f"{predicted_count / predicted_total:.0%}" if predicted_total else "—",
                    f"{predicted_count:,} previsões",
                )
        else:
            st.info("Nenhuma avaliação corresponde aos filtros globais.")

    with st.container(border=True):
        st.subheader("Comentários")
        search_column, sentiment_column = st.columns([2, 3], vertical_alignment="bottom")
        with search_column:
            query = st.text_input(
                "Buscar nos comentários",
                label_visibility="collapsed",
                placeholder="Buscar nos comentários",
            )
        with sentiment_column:
            note_sentiment = st.segmented_control(
                "Sentimento pela nota",
                ["Todos", "Negativo", "Neutro", "Positivo"],
                default="Todos",
                label_visibility="collapsed",
            ) or "Todos"
        predicted_sentiment = st.segmented_control(
            "Sentimento previsto pelo modelo",
            ["Todos", "Negativo", "Neutro", "Positivo"],
            default="Todos",
            label_visibility="collapsed",
        ) or "Todos"
        comparison_filter = st.selectbox(
            "Comparação entre nota e previsão",
            ["Todas", "Difere da nota", "Igual à nota", "Sem previsão"],
        ) or "Todas"

        filters = (
            note_sentiment,
            predicted_sentiment,
            comparison_filter,
            query.strip().casefold(),
            st.session_state.get("periodo", "Todos"),
            st.session_state.get("categoria", "Todas"),
        )
        if st.session_state.get("comentarios_filtros") != filters:
            st.session_state["comentarios_filtros"] = filters
            st.session_state["comentarios_pagina"] = 1
        if note_sentiment != "Todos":
            reviews = reviews.loc[reviews["sentimento_nota"].eq(note_sentiment)]
        if predicted_sentiment != "Todos":
            reviews = reviews.loc[
                reviews["sentimento_previsto"].str.capitalize().eq(predicted_sentiment)
            ]
        predicted = reviews["sentimento_previsto"].str.capitalize()
        if comparison_filter == "Difere da nota":
            reviews = reviews.loc[predicted.notna() & predicted.ne(reviews["sentimento_nota"])]
        elif comparison_filter == "Igual à nota":
            reviews = reviews.loc[predicted.notna() & predicted.eq(reviews["sentimento_nota"])]
        elif comparison_filter == "Sem previsão":
            reviews = reviews.loc[predicted.isna()]
        if query.strip():
            reviews = reviews.loc[
                reviews["comentario"].str.contains(query.strip(), case=False, na=False)
            ]
        reviews = reviews.sort_values("data", ascending=False, na_position="last")
        st.caption(f"{len(reviews):,} comentários encontrados")
        if reviews.empty:
            st.info("Nenhum comentário encontrado com esses filtros.")
            return

        page_size = 100
        total_pages = max(1, (len(reviews) + page_size - 1) // page_size)
        page = min(max(int(st.session_state.get("comentarios_pagina", 1)), 1), total_pages)
        st.session_state["comentarios_pagina"] = page
        start = (page - 1) * page_size
        visible = reviews.iloc[start : start + page_size].copy()
        visible["Comparação"] = "Sem previsão"
        has_prediction = visible["sentimento_previsto"].notna()
        predicted_visible = visible["sentimento_previsto"].str.capitalize()
        visible.loc[has_prediction & predicted_visible.eq(visible["sentimento_nota"]), "Comparação"] = "Igual à nota"
        visible.loc[has_prediction & predicted_visible.ne(visible["sentimento_nota"]), "Comparação"] = "Difere da nota"
        view = visible[["data", "nota", "sentimento_nota", "sentimento_previsto", "Comparação", "categoria", "comentario"]].rename(
            columns={
                "data": "Data",
                "nota": "Nota",
                "sentimento_nota": "Sentimento pela nota",
                "sentimento_previsto": "Sentimento previsto",
                "categoria": "Categoria",
                "comentario": "Comentário",
            }
        )
        view["Sentimento previsto"] = view["Sentimento previsto"].str.capitalize()
        view["Data"] = view["Data"].dt.strftime("%d/%m/%Y")
        wrapped_view = (
            view.style.set_table_styles(
                [
                    {"selector": "table", "props": [("width", "100%"), ("table-layout", "fixed")]},
                    {"selector": "th", "props": [("white-space", "normal"), ("word-break", "break-word")]},
                    {"selector": "td", "props": [("white-space", "normal"), ("overflow-wrap", "anywhere"), ("word-break", "break-word"), ("vertical-align", "top")]},
                ]
            )
            .set_properties(
                subset=["Comentário"],
                **{"width": "38%", "max-width": "520px"},
            )
        )
        st.table(wrapped_view)
        previous, page_label, next_page = st.columns([1, 2, 1], vertical_alignment="center")
        with previous:
            if st.button("← Anterior", disabled=page <= 1, use_container_width=True):
                st.session_state["comentarios_pagina"] = page - 1
                st.rerun()
        with page_label:
            st.caption(f"Página {page} de {total_pages} · {start + 1}–{start + len(visible)} de {len(reviews):,} comentários")
        with next_page:
            if st.button("Próxima →", disabled=page >= total_pages, use_container_width=True):
                st.session_state["comentarios_pagina"] = page + 1
                st.rerun()


main()
