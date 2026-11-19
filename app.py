import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
REQUIRED_MODULES = ("kagglehub", "pandas", "sklearn", "streamlit", "joblib")


def check_dependencies() -> None:
    missing = [name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None]
    if missing:
        packages = ", ".join(missing)
        raise SystemExit(
            f"Dependências ausentes: {packages}. Instale-as no ambiente ativo com:\n"
            f'  "{sys.executable}" -m pip install -r "{ROOT_DIR / "requirements.txt"}"'
        )


def main() -> None:
    check_dependencies()

    from src.get_dataset import baixar_csvs
    from src.load_database import save_tables
    from src.train_model import train_sentiment_model
    from src.transform import transform_all

    print("\nBaixando o dataset...", flush=True)
    baixar_csvs()
    print("\nTransformando os dados...", flush=True)
    tables = transform_all()
    print("\nCarregando as tabelas no SQLite...", flush=True)
    save_tables(tables)
    print(f"Banco SQLite atualizado: {ROOT_DIR / 'data' / 'database' / 'olist.db'}")
    print("\nTreinando e avaliando o modelo de sentimento...", flush=True)
    train_sentiment_model()

    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(ROOT_DIR / "src" / "dashboard" / "index.py"),
            "--server.headless=true",
            "--server.showEmailPrompt=false",
        ],
        cwd=ROOT_DIR,
        check=True,
    )


if __name__ == "__main__":
    main()
