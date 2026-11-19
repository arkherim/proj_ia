from pathlib import Path
import shutil

import kagglehub

DIRETORIO_RAIZ = Path(__file__).resolve().parents[1]
DIRETORIO_CSV = DIRETORIO_RAIZ / "data" / "csv"
CONJUNTO_DADOS = "olistbr/brazilian-ecommerce"

CSVS_ESPERADOS = (
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
)


def baixar_csvs() -> None:
    DIRETORIO_CSV.mkdir(parents=True, exist_ok=True)
    diretorio_baixado = Path(
        kagglehub.dataset_download(CONJUNTO_DADOS, force_download=True)
    )
    arquivos_baixados = {}
    for nome in CSVS_ESPERADOS:
        candidatos = list(diretorio_baixado.rglob(nome))
        if not candidatos:
            raise FileNotFoundError(
                f"O KaggleHub não encontrou {nome} em {diretorio_baixado}"
            )
        arquivos_baixados[nome] = candidatos[0]

    for nome, origem in arquivos_baixados.items():
        destino = DIRETORIO_CSV / nome
        destino.unlink(missing_ok=True)
        shutil.copy2(origem, destino)

    disponiveis = [
        nome
        for nome in CSVS_ESPERADOS
        if (DIRETORIO_CSV / nome).is_file()
    ]
    ausentes = [
        nome
        for nome in CSVS_ESPERADOS
        if nome not in disponiveis
    ]
    print(
        f"CSV disponíveis em {DIRETORIO_CSV}: "
        f"{len(disponiveis)}/{len(CSVS_ESPERADOS)}"
    )
    for nome in disponiveis:
        print(f"  OK: {nome}")
    if ausentes:
        raise FileNotFoundError(f"CSV(s) ausentes: {', '.join(ausentes)}")


