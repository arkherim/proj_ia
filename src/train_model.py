import sqlite3
import re
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import (
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)
from sklearn.pipeline import Pipeline


ROOT_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT_DIR / "data" / "database" / "olist.db"
MODEL_PATH = ROOT_DIR / "models" / "sentiment_model.joblib"
RANDOM_STATE = 42
TEST_SIZE = 0.20
CLASS_LABELS = ("negativo", "neutro", "positivo")
SCORE_TO_SENTIMENT = {
    1: "negativo",
    2: "negativo",
    3: "neutro",
    4: "positivo",
    5: "positivo",
}


def load_training_data() -> tuple[pd.Series, pd.Series]:
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(
            f"Banco não encontrado: {DATABASE_PATH}. Execute primeiro o app.py."
        )

    with sqlite3.connect(DATABASE_PATH) as connection:
        data = pd.read_sql_query(
            "SELECT texto_limpo, review_score FROM reviews_clean", connection
        )

    data["texto_limpo"] = data["texto_limpo"].fillna("").astype(str).str.strip()
    data = data.loc[data["texto_limpo"].ne("")].copy()
    data["sentimento"] = data["review_score"].map(SCORE_TO_SENTIMENT)
    data = data.dropna(subset=["sentimento"])

    counts = data["sentimento"].value_counts()
    missing = [label for label in CLASS_LABELS if label not in counts]
    if missing:
        raise ValueError(f"Classes sem exemplos para treinamento: {', '.join(missing)}")

    return data["texto_limpo"], data["sentimento"]


def normalize_training_text(text: object) -> str:
    """Normaliza rótulos manuais da tabela de testes como os textos do Olist."""
    normalized = str(text).casefold()
    normalized = re.sub(r"https?://\S+|www\.\S+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def load_manual_training_data() -> tuple[pd.Series, pd.Series]:
    """Lê somente testes com sentimento correto informado manualmente."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        try:
            data = pd.read_sql_query(
                """
                SELECT comment_text, sentimento_correto
                FROM comment_tests
                WHERE sentimento_correto IS NOT NULL
                """,
                connection,
            )
        except sqlite3.OperationalError as error:
            if "no such table: comment_tests" in str(error).lower():
                return pd.Series(dtype="string"), pd.Series(dtype="string")
            raise

    data["texto"] = data["comment_text"].map(normalize_training_text)
    data["sentimento"] = data["sentimento_correto"].str.casefold().str.strip()
    data = data.loc[
        data["texto"].ne("") & data["sentimento"].isin(CLASS_LABELS)
    ].copy()
    if data.empty:
        return pd.Series(dtype="string"), pd.Series(dtype="string")

    labels_per_text = data.groupby("texto")["sentimento"].nunique()
    ambiguous_texts = labels_per_text.loc[labels_per_text.gt(1)].index
    if len(ambiguous_texts):
        print(
            f"Rótulos manuais conflitantes ignorados: {len(ambiguous_texts)} textos."
        )
        data = data.loc[~data["texto"].isin(ambiguous_texts)]
    data = data.drop_duplicates("texto", keep="last")
    return data["texto"].reset_index(drop=True), data["sentimento"].reset_index(drop=True)


def merge_manual_examples(
    base_texts: pd.Series,
    base_labels: pd.Series,
    manual_texts: pd.Series,
    manual_labels: pd.Series,
    protected_texts: pd.Series | None = None,
) -> tuple[pd.Series, pd.Series, int, int]:
    """Acrescenta rótulos manuais, removendo conflitos e vazamento para teste."""
    base = pd.DataFrame({"texto": base_texts, "sentimento": base_labels})
    base["normalizado"] = base["texto"].map(normalize_training_text)
    manual = pd.DataFrame({"texto": manual_texts, "sentimento": manual_labels})
    if manual.empty:
        return base["texto"], base["sentimento"], 0, 0
    manual["normalizado"] = manual["texto"].map(normalize_training_text)

    protected = set()
    if protected_texts is not None:
        protected = set(protected_texts.map(normalize_training_text))
    excluded = manual["normalizado"].isin(protected)
    excluded_count = int(excluded.sum())
    manual = manual.loc[~excluded]

    added = 0
    for row in manual.itertuples(index=False):
        existing = base["normalizado"].eq(row.normalizado)
        if existing.any():
            current_labels = set(base.loc[existing, "sentimento"])
            if current_labels == {row.sentimento}:
                continue
            base = base.loc[~existing].reset_index(drop=True)
        base.loc[len(base)] = [row.texto, row.sentimento, row.normalizado]
        added += 1

    return base["texto"].reset_index(drop=True), base["sentimento"].reset_index(drop=True), added, excluded_count


def build_pipeline(classifier: object) -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=2,
                    max_features=50_000,
                    sublinear_tf=True,
                ),
            ),
            ("classifier", classifier),
        ]
    )


def save_evaluation_metrics(
    cv_macro_f1: float,
    selected_name: str,
    test_macro_f1: float,
    report: dict[str, object],
    matrix: object,
) -> None:
    generated_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, object]] = []
    rows.append(
        {
            "tipo": "resumo",
            "modelo": selected_name,
            "classe": None,
            "classe_prevista": None,
            "precisao": None,
            "recall": None,
            "f1": None,
            "suporte": None,
            "quantidade": None,
            "cv_macro_f1": cv_macro_f1,
            "test_macro_f1": test_macro_f1,
            "acuracia": report["accuracy"],
            "avaliado_em": generated_at,
        }
    )

    for label in CLASS_LABELS:
        class_report = report[label]
        rows.append(
            {
                "tipo": "classe",
                "modelo": selected_name,
                "classe": label,
                "classe_prevista": None,
                "precisao": class_report["precision"],
                "recall": class_report["recall"],
                "f1": class_report["f1-score"],
                "suporte": class_report["support"],
                "quantidade": None,
                "cv_macro_f1": None,
                "test_macro_f1": None,
                "acuracia": None,
                "avaliado_em": generated_at,
            }
        )

    for actual_index, actual_label in enumerate(CLASS_LABELS):
        for predicted_index, predicted_label in enumerate(CLASS_LABELS):
            rows.append(
                {
                    "tipo": "confusao",
                    "modelo": selected_name,
                    "classe": actual_label,
                    "classe_prevista": predicted_label,
                    "precisao": None,
                    "recall": None,
                    "f1": None,
                    "suporte": None,
                    "quantidade": int(matrix[actual_index][predicted_index]),
                    "cv_macro_f1": None,
                    "test_macro_f1": None,
                    "acuracia": None,
                    "avaliado_em": generated_at,
                }
            )

    metrics = pd.DataFrame(rows)
    with sqlite3.connect(DATABASE_PATH) as connection:
        metrics.to_sql("model_metrics", connection, if_exists="replace", index=False)


def save_review_predictions(model: Pipeline) -> int:
    """Aplica o modelo a todas as avaliações com texto e salva as previsões."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        data = pd.read_sql_query(
            "SELECT review_id, review_score, texto_limpo FROM reviews_clean",
            connection,
        )

    data["texto_limpo"] = data["texto_limpo"].fillna("").astype(str).str.strip()
    data = data.loc[data["texto_limpo"].ne("")].copy()
    data["sentimento_nota"] = data["review_score"].map(SCORE_TO_SENTIMENT)
    data["sentimento_previsto"] = model.predict(data["texto_limpo"])
    if hasattr(model, "predict_proba"):
        data["confianca"] = model.predict_proba(data["texto_limpo"]).max(axis=1)
    else:
        data["confianca"] = None

    predictions = data[
        ["review_id", "sentimento_nota", "sentimento_previsto", "confianca"]
    ]
    with sqlite3.connect(DATABASE_PATH) as connection:
        predictions.to_sql("model_predictions", connection, if_exists="replace", index=False)
        connection.execute(
            'CREATE UNIQUE INDEX "idx_model_predictions_review_id" '
            'ON "model_predictions" ("review_id")'
        )
        connection.commit()
    return len(predictions)


def train_sentiment_model() -> Path:
    texts, labels = load_training_data()
    manual_texts, manual_labels = load_manual_training_data()
    x_train, x_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=labels,
    )
    x_train, y_train, manual_added, manual_excluded = merge_manual_examples(
        x_train,
        y_train,
        manual_texts,
        manual_labels,
        protected_texts=x_test,
    )
    if len(manual_texts):
        print(
            f"Rótulos manuais integrados ao treino: {manual_added}; "
            f"ignorados por coincidirem com o conjunto de teste: {manual_excluded}."
        )
    train_counts = y_train.value_counts()
    if any(train_counts.get(label, 0) < 5 for label in CLASS_LABELS):
        raise ValueError(
            "São necessários pelo menos cinco exemplos de cada classe no treino "
            "para a validação cruzada."
        )
    cross_validation = StratifiedKFold(
        n_splits=5, shuffle=True, random_state=RANDOM_STATE
    )
    selected_name = "LogisticRegression"
    classifier = LogisticRegression(max_iter=1000, class_weight="balanced")
    selected_pipeline = build_pipeline(classifier)
    fold_scores = cross_val_score(
        selected_pipeline,
        x_train,
        y_train,
        cv=cross_validation,
        scoring="f1_macro",
        n_jobs=1,
    )
    cv_macro_f1 = float(fold_scores.mean())
    print(f"{selected_name} - macro-F1 CV: {cv_macro_f1:.4f}")
    selected_pipeline.fit(x_train, y_train)
    predictions = selected_pipeline.predict(x_test)
    report = classification_report(
        y_test,
        predictions,
        labels=CLASS_LABELS,
        target_names=CLASS_LABELS,
        zero_division=0,
        digits=4,
        output_dict=True,
    )
    matrix = confusion_matrix(y_test, predictions, labels=CLASS_LABELS)
    test_macro_f1 = float(f1_score(y_test, predictions, average="macro"))

    print(f"\nModelo selecionado: {selected_name}")
    print(f"Macro-F1 no teste: {test_macro_f1:.4f}")
    print(
        "\nRelatório por classe:\n"
        + classification_report(
            y_test,
            predictions,
            labels=CLASS_LABELS,
            target_names=CLASS_LABELS,
            zero_division=0,
            digits=4,
        )
    )
    print("Matriz de confusão (negativo, neutro, positivo):")
    print(matrix)

    save_evaluation_metrics(cv_macro_f1, selected_name, test_macro_f1, report, matrix)

    final_texts, final_labels, _, _ = merge_manual_examples(
        texts, labels, manual_texts, manual_labels
    )
    final_pipeline = build_pipeline(
        LogisticRegression(max_iter=1000, class_weight="balanced")
    )
    final_pipeline.fit(final_texts, final_labels)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_pipeline, MODEL_PATH)
    prediction_count = save_review_predictions(final_pipeline)
    print(f"Modelo salvo em: {MODEL_PATH}")
    print(
        f"Sentimentos previstos e atualizados para {prediction_count:,} avaliações "
        "na tabela model_predictions."
    )
    return MODEL_PATH
