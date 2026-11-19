"""Executa a ingestão de dados e inicia o painel Streamlit."""

import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
ETL_SCRIPTS = (
    "src/get_dataset.py",
    "src/prepare_data.py",
)
REQUIRED_MODULES = ("kagglehub", "pandas", "streamlit")


def check_dependencies() -> None:
    """Confere dependências antes de iniciar o download do dataset."""
    missing = [name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None]
    if missing:
        packages = ", ".join(missing)
        raise SystemExit(
            f"Dependências ausentes: {packages}. Instale-as no ambiente ativo com:\n"
            f'  "{sys.executable}" -m pip install -r "{ROOT_DIR / "requirements.txt"}"'
        )


def main() -> None:
    """Executa as etapas do pipeline e abre o painel de avaliações."""
    check_dependencies()
    for script in ETL_SCRIPTS:
        print(f"\nExecutando {script}...", flush=True)
        try:
            subprocess.run(
                [sys.executable, str(ROOT_DIR / script)], cwd=ROOT_DIR, check=True
            )
        except subprocess.CalledProcessError as erro:
            raise SystemExit(f"A etapa {script} falhou (código {erro.returncode}).") from None

    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(ROOT_DIR / "src" / "dashboard.py"),
            "--server.headless=true",
            "--server.showEmailPrompt=false",
        ],
        cwd=ROOT_DIR,
        check=True,
    )


if __name__ == "__main__":
    main()
