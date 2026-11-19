import re
from pathlib import Path

import pandas as pd


DIRETORIO_RAIZ = Path(__file__).resolve().parents[1]
DIRETORIO_CSV = DIRETORIO_RAIZ / "data" / "csv"


def read_csv(nome_arquivo: str) -> pd.DataFrame:
    caminho_csv = DIRETORIO_CSV / nome_arquivo
    if not caminho_csv.is_file():
        raise FileNotFoundError(
            f"CSV não encontrado: {caminho_csv}. "
            "Execute primeiro: python src/get_dataset.py"
        )
    return pd.read_csv(caminho_csv)


def limpar_texto(texto: object) -> str:
    texto_limpo = str(texto).lower()
    texto_limpo = re.sub(r"https?://\S+|www\.\S+", " ", texto_limpo)
    return re.sub(r"\s+", " ", texto_limpo).strip()


def transform_reviews(avaliacoes_originais: pd.DataFrame) -> pd.DataFrame:
    registros = [f"Avaliações no CSV: {len(avaliacoes_originais):,}"]

    avaliacoes = avaliacoes_originais.dropna(
        subset=["review_comment_message"]
    ).copy()
    avaliacoes.loc[:, "texto_limpo"] = avaliacoes[
        "review_comment_message"
    ].map(limpar_texto)
    avaliacoes = avaliacoes.loc[avaliacoes["texto_limpo"].ne("")].copy()
    registros.append(f"Com comentário não vazio: {len(avaliacoes):,}")

    avaliacoes["_data_resposta"] = pd.to_datetime(
        avaliacoes["review_answer_timestamp"],
        errors="coerce",
        utc=True,
    )
    avaliacoes = avaliacoes.sort_values(
        "_data_resposta", na_position="first", kind="stable"
    )
    avaliacoes = avaliacoes.drop_duplicates("review_id", keep="last")
    avaliacoes = avaliacoes.drop_duplicates("order_id", keep="last")
    registros.append(f"Após deduplicar (uma por pedido): {len(avaliacoes):,}")

    avaliacoes = avaliacoes.rename(
        columns={"review_comment_message": "comentario"}
    )
    avaliacoes = avaliacoes[
        [
            "review_id",
            "order_id",
            "review_score",
            "comentario",
            "texto_limpo",
        ]
    ].copy()

    print("\n".join(registros))
    return avaliacoes


def transform_deliveries(avaliacoes: pd.DataFrame) -> pd.DataFrame:
    pedidos = read_csv("olist_orders_dataset.csv")
    colunas_entrega = [
        "order_id",
        "order_status",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    entregas = pedidos.loc[
        pedidos["order_id"].isin(avaliacoes["order_id"]), colunas_entrega
    ].copy()
    data_entrega = pd.to_datetime(
        entregas["order_delivered_customer_date"], errors="coerce", utc=True
    )
    data_prevista = pd.to_datetime(
        entregas["order_estimated_delivery_date"], errors="coerce", utc=True
    )
    entregas["dias_atraso"] = (data_entrega - data_prevista).dt.days
    entregas["entregue_atrasado"] = entregas["dias_atraso"].gt(0).astype("Int64")
    entregas.loc[entregas["dias_atraso"].isna(), "entregue_atrasado"] = pd.NA
    return entregas


def transform_review_products(
    avaliacoes: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    itens = read_csv("olist_order_items_dataset.csv")
    produtos = read_csv("olist_products_dataset.csv")
    traducao = read_csv("product_category_name_translation.csv")

    quantidade_produtos = itens.groupby("order_id")["product_id"].nunique()
    pedidos_unicos = quantidade_produtos[quantidade_produtos.eq(1)].index
    pedidos_com_varios = quantidade_produtos[quantidade_produtos.gt(1)].index
    quantidade_excluida = int(
        avaliacoes["order_id"].isin(pedidos_com_varios).sum()
    )

    categorias = (
        itens.loc[itens["order_id"].isin(pedidos_unicos)]
        .drop_duplicates("order_id")
        [["order_id", "product_id", "seller_id"]]
        .merge(
            produtos[["product_id", "product_category_name"]],
            on="product_id",
            how="left",
        )
        .merge(traducao, on="product_category_name", how="left")
    )
    categorias["categoria"] = categorias[
        "product_category_name_english"
    ].fillna(categorias["product_category_name"])

    avaliacoes_produtos = avaliacoes.merge(
        categorias, on="order_id", how="inner"
    )
    avaliacoes_produtos = avaliacoes_produtos[
        [
            "review_id",
            "order_id",
            "product_id",
            "seller_id",
            "categoria",
            "review_score",
        ]
    ]
    return avaliacoes_produtos, quantidade_excluida


def transform_all() -> dict[str, pd.DataFrame]:
    reviews = read_csv("olist_order_reviews_dataset.csv")
    avaliacoes = transform_reviews(reviews)
    entregas = transform_deliveries(avaliacoes)
    avaliacoes_produtos, quantidade_excluida = transform_review_products(
        avaliacoes
    )
    dados = {
        "reviews": reviews,
        "reviews_clean": avaliacoes,
        "review_product": avaliacoes_produtos,
        "review_delivery": entregas,
    }

    print(
        "Pedidos com vários produtos fora da análise por categoria: "
        f"{quantidade_excluida:,}"
    )
    print("\nTransform concluído!")
    for tabela, df in dados.items():
        print(f"  {tabela}: {df.shape[0]:,} linhas, {df.shape[1]} colunas")
    return dados
