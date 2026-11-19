import hashlib
import textwrap

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

    table = visible[["review_id", "data", "nota", "sentimento_nota", "sentimento_previsto", "confianca", "comentario", "sentimento_revisado"]].rename(
        columns={
            "review_id": "review_id", "data": "Data", "nota": "Nota", "sentimento_nota": "Sentimento pela nota",
            "sentimento_previsto": "Previsto", "confianca": "Confiança",
            "sentimento_revisado": "Sentimento correto", "comentario": "Comentário",
        }
    )
    table["Data"] = table["Data"].dt.strftime("%d/%m/%Y")
    table["Confiança"] = table["Confiança"].map(lambda value: f"{value:.1%}" if pd.notna(value) else "—")
    table["Comentário"] = table["Comentário"].fillna("").map(
        lambda comment: textwrap.fill(
            str(comment).replace("\r", " ").replace("\n", " "),
            width=48,
            break_long_words=True,
            break_on_hyphens=False,
        )
    )
    table["Sentimento correto"] = table["Sentimento correto"].fillna("")
    max_comment_lines = max(
        1, int(table["Comentário"].map(lambda comment: comment.count("\n") + 1).max())
    )
    row_height = max(72, max_comment_lines * 21 + 18)
    editor_rows = "|".join(visible["review_id"].astype(str))
    editor_suffix = hashlib.sha1(editor_rows.encode("utf-8")).hexdigest()[:12]
    with st.form("form_reclassificar_divergencias"):
        edited_table = st.data_editor(
            table,
            hide_index=True,
            use_container_width=True,
            row_height=row_height,
            disabled=[
                "review_id", "Data", "Nota", "Sentimento pela nota", "Previsto",
                "Confiança", "Comentário",
            ],
            column_config={
                "review_id": None,
                "Sentimento correto": st.column_config.SelectboxColumn(
                    "Sentimento correto",
                    options=["", *LABELS],
                    required=False,
                    help="Selecione o rótulo correto para esta avaliação.",
                    width="medium",
                ),
                "Comentário": st.column_config.TextColumn(width="large"),
            },
            key=f"editor_reclassificacoes_{page}_{editor_suffix}",
        )
        save_changes = st.form_submit_button("Salvar reclassificações", type="primary")

    if save_changes:
        original_labels = visible.set_index("review_id")["sentimento_revisado"]
        saved = 0
        errors = []
        for row in edited_table.to_dict("records"):
            correct_label = str(row["Sentimento correto"]).strip()
            if not correct_label:
                continue
            review_id = str(row["review_id"])
            current_label = original_labels.get(review_id)
            current_label = current_label.capitalize() if isinstance(current_label, str) else ""
            if correct_label == current_label:
                continue
            selected = visible.loc[visible["review_id"].eq(review_id)].iloc[0]
            confidence = float(selected["confianca"]) if pd.notna(selected["confianca"]) else None
            try:
                save_review_reclassification(
                    review_id,
                    str(selected["comentario"]),
                    str(selected["sentimento_previsto"]).lower(),
                    confidence,
                    correct_label.lower(),
                )
                saved += 1
            except Exception as error:
                errors.append(f"{review_id}: {error}")
        if errors:
            st.error("Algumas reclassificações não foram salvas: " + "; ".join(errors))
        elif saved:
            st.toast(f"{saved} reclassificação(ões) salva(s).")
            st.rerun()
        else:
            st.info("Nenhuma alteração nova para salvar.")
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

main()
