import pandas as pd
import streamlit as st

from src.dashboard.dashboard_data import load_current_reviews
from src.dashboard.review_relabel import (
    load_review_reclassifications,
    save_review_reclassification,
)


LABELS = ["Negativo", "Neutro", "Positivo"]
PAGE_SIZE = 100


def main() -> None:
    st.title("Revisar previsões divergentes")
    st.caption(
        "Compare a previsão do modelo com o sentimento indicado pela nota. "
        "A correção será salva para apoiar o próximo treinamento; ela não altera a previsão original."
    )

    reviews = load_current_reviews()
    if "confianca" not in reviews.columns:
        reviews = reviews.copy()
        reviews["confianca"] = pd.NA
    if "sentimento_revisado" not in reviews.columns:
        reviews = reviews.copy()
        reviews["sentimento_revisado"] = pd.NA
    predicted = reviews["sentimento_previsto"].str.capitalize()
    divergent = reviews.loc[
        predicted.notna() & predicted.ne(reviews["sentimento_nota"])
    ].copy()
    divergent["sentimento_previsto"] = predicted.loc[divergent.index]
    labels = load_review_reclassifications(divergent["review_id"].astype(str).tolist())
    divergent["review_id"] = divergent["review_id"].astype(str)
    divergent = divergent.merge(
        labels.rename(columns={"sentimento_correto": "sentimento_revisado"}),
        left_on="review_id",
        right_on="source_review_id",
        how="left",
        validate="one_to_one",
    )
    if "confianca" not in divergent.columns:
        divergent["confianca"] = pd.NA
    divergent["sentimento_revisado"] = divergent["sentimento_revisado"].str.capitalize()

    total = len(divergent)
    reviewed = int(divergent["sentimento_revisado"].notna().sum())
    first, second, third = st.columns(3)
    first.metric("Previsões divergentes", f"{total:,}")
    second.metric("Reclassificadas", f"{reviewed:,}")
    third.metric("Pendentes", f"{total - reviewed:,}")

    search = st.text_input("Buscar nos comentários", placeholder="Digite para filtrar")
    status = st.segmented_control(
        "Status da revisão",
        ["Todas", "Pendentes", "Reclassificadas"],
        default="Pendentes",
    ) or "Pendentes"
    if status == "Pendentes":
        divergent = divergent.loc[divergent["sentimento_revisado"].isna()]
    elif status == "Reclassificadas":
        divergent = divergent.loc[divergent["sentimento_revisado"].notna()]
    if search.strip():
        divergent = divergent.loc[
            divergent["comentario"].str.contains(search.strip(), case=False, na=False)
        ]
    divergent = divergent.sort_values("data", ascending=False, na_position="last")
    st.caption(f"{len(divergent):,} divergências neste filtro")
    if divergent.empty:
        st.info("Nenhuma divergência encontrada com esses filtros.")
        return

    total_pages = max(1, (len(divergent) + PAGE_SIZE - 1) // PAGE_SIZE)
    filter_state = (status, search.strip(), st.session_state.get("periodo"), st.session_state.get("categoria"))
    if st.session_state.get("divergencias_filtros") != filter_state:
        st.session_state["divergencias_filtros"] = filter_state
        st.session_state["divergencias_pagina"] = 1
    page = min(max(int(st.session_state.get("divergencias_pagina", 1)), 1), total_pages)
    st.session_state["divergencias_pagina"] = page
    start = (page - 1) * PAGE_SIZE
    visible = divergent.iloc[start : start + PAGE_SIZE].copy()
    if "confianca" not in visible.columns:
        visible["confianca"] = pd.NA

    table = visible[["data", "nota", "sentimento_nota", "sentimento_previsto", "confianca", "sentimento_revisado", "comentario"]].rename(
        columns={
            "data": "Data", "nota": "Nota", "sentimento_nota": "Sentimento pela nota",
            "sentimento_previsto": "Previsto", "confianca": "Confiança",
            "sentimento_revisado": "Reclassificado como", "comentario": "Comentário",
        }
    )
    table["Data"] = table["Data"].dt.strftime("%d/%m/%Y")
    table["Confiança"] = table["Confiança"].map(lambda value: f"{value:.1%}" if pd.notna(value) else "—")
    st.table(
        table.style.set_table_styles([
            {"selector": "table", "props": [("width", "100%"), ("table-layout", "fixed")]},
            {"selector": "th", "props": [("white-space", "normal"), ("word-break", "break-word")]},
            {"selector": "td", "props": [("white-space", "normal"), ("overflow-wrap", "anywhere"), ("vertical-align", "top")]},
        ]).set_properties(subset=["Comentário"], **{"width": "42%", "max-width": "540px"})
    )
    previous, page_label, next_page = st.columns([1, 2, 1], vertical_alignment="center")
    with previous:
        if st.button("← Anterior", disabled=page <= 1, use_container_width=True):
            st.session_state["divergencias_pagina"] = page - 1
            st.rerun()
    with page_label:
        st.caption(f"Página {page} de {total_pages} · {start + 1}–{start + len(visible)} de {len(divergent):,}")
    with next_page:
        if st.button("Próxima →", disabled=page >= total_pages, use_container_width=True):
            st.session_state["divergencias_pagina"] = page + 1
            st.rerun()

    st.divider()
    st.subheader("Reclassificar comentário")
    options = visible["review_id"].tolist()
    selected_id = st.selectbox(
        "Escolha uma avaliação desta página",
        options,
        format_func=lambda review_id: _review_option(visible, review_id),
    )
    selected = visible.loc[visible["review_id"].eq(selected_id)].iloc[0]
    st.markdown(f"**Comentário:** {selected['comentario']}")
    st.caption(
        f"Nota: {selected['nota']} ({selected['sentimento_nota']}) · "
        f"Previsão: {selected['sentimento_previsto']} · "
        f"Confiança: {selected['confianca']:.1%}" if pd.notna(selected["confianca"])
        else f"Nota: {selected['nota']} ({selected['sentimento_nota']}) · Previsão: {selected['sentimento_previsto']} · Confiança indisponível"
    )
    current_label = selected["sentimento_revisado"]
    default_index = LABELS.index(current_label) if current_label in LABELS else 0
    correct_label = st.selectbox(
        "Sentimento correto do comentário", LABELS, index=default_index,
        key=f"rotulo_divergencia_{selected_id}",
    )
    if st.button("Salvar reclassificação", type="primary"):
        confidence = float(selected["confianca"]) if pd.notna(selected["confianca"]) else None
        try:
            save_review_reclassification(
                str(selected_id), str(selected["comentario"]),
                str(selected["sentimento_previsto"]).lower(), confidence,
                correct_label.lower(),
            )
            st.success("Reclassificação salva e disponível para o próximo treinamento.")
            st.rerun()
        except Exception as error:
            st.error(f"Não foi possível salvar a reclassificação: {error}")


def _review_option(reviews: pd.DataFrame, review_id: str) -> str:
    row = reviews.loc[reviews["review_id"].eq(review_id)].iloc[0]
    snippet = str(row["comentario"]).replace("\n", " ")[:70]
    return f"{row['sentimento_previsto']} ≠ {row['sentimento_nota']} · {snippet}"


main()
