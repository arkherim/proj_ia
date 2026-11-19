import pandas as pd
import streamlit as st

from src.dashboard.dashboard_data import (
    MODEL_PATH,
)
from src.dashboard.test_storage import (
    load_comment_tests,
    save_comment_test,
    update_comment_test_label,
)


@st.cache_resource
def load_model(path: str):
    import joblib

    return joblib.load(path)


def main() -> None:
    _, center, _ = st.columns([1, 2, 1])
    with center, st.container(border=True):
        st.subheader("Testar um comentário")
        comment_text = st.text_area(
            "Comentário",
            placeholder="Escreva um comentário em português",
            height=160,
            key="texto_teste_comentario",
        )
        if st.button("Classificar e salvar teste", type="primary", use_container_width=True):
            if not comment_text.strip():
                st.warning("Escreva um comentário para classificar.")
            elif not MODEL_PATH.is_file():
                st.error("Modelo não encontrado. Execute `python app.py` para treinar o modelo.")
            else:
                try:
                    model = load_model(str(MODEL_PATH))
                    prediction = str(model.predict([comment_text.strip()])[0])
                    confidence = None
                    if hasattr(model, "predict_proba"):
                        confidence = float(model.predict_proba([comment_text.strip()])[0].max())
                    test_id = save_comment_test(comment_text.strip(), prediction, confidence)
                    st.session_state["ultimo_teste_comentario"] = {
                        "test_id": test_id,
                        "texto": comment_text.strip(),
                        "previsto": prediction,
                        "confianca": confidence,
                    }
                except Exception as error:
                    st.error(f"Não foi possível classificar e salvar o comentário: {error}")

        last_test = st.session_state.get("ultimo_teste_comentario")
        if last_test:
            st.markdown(f"### {last_test['previsto'].capitalize()}")
            if last_test["confianca"] is not None:
                st.caption(f"Confiança estimada: {last_test['confianca']:.1%}")
            st.caption(f"Teste salvo com ID {last_test['test_id']}.")
            st.selectbox(
                "Sentimento correto para este comentário",
                ["Selecione...", "Negativo", "Neutro", "Positivo"],
                key=f"sentimento_correto_{last_test['test_id']}",
            )
            if st.button("Salvar sentimento correto", key=f"salvar_rotulo_{last_test['test_id']}"):
                correct_label = st.session_state[f"sentimento_correto_{last_test['test_id']}"]
                if correct_label == "Selecione...":
                    st.warning("Selecione o sentimento correto antes de salvar.")
                else:
                    update_comment_test_label(last_test["test_id"], correct_label.lower())
                    st.success("Sentimento correto salvo.")

    st.subheader("Histórico de testes")
    try:
        tests = load_comment_tests()
    except Exception as error:
        st.error(f"Não foi possível carregar o histórico de testes: {error}")
        return
    if tests.empty:
        st.info("Nenhum teste salvo ainda.")
        return

    tests["created_at"] = pd.to_datetime(tests["created_at"], errors="coerce", utc=True)
    tests["created_at"] = tests["created_at"].dt.strftime("%d/%m/%Y %H:%M")
    tests["sentimento_previsto"] = tests["sentimento_previsto"].str.capitalize()
    tests["sentimento_correto"] = tests["sentimento_correto"].str.capitalize()
    tests = tests.rename(
        columns={
            "test_id": "ID",
            "comment_text": "Comentário",
            "sentimento_previsto": "Sentimento previsto",
            "confianca": "Confiança",
            "sentimento_correto": "Sentimento correto",
            "created_at": "Data do teste",
        }
    )
    st.dataframe(tests, hide_index=True, use_container_width=True)


main()
