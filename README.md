# Preparação dos dados Olist

Este projeto baixa o Brazilian E-Commerce Public Dataset by Olist, salva os
CSV originais em `data/csv/` e prepara tabelas de análise no banco
`data/database/olist.db`.

## Requisitos

Python 3.10 ou superior. Instale as dependências:

```powershell
python -m pip install -r requirements.txt
```

O download usa KaggleHub e a autenticação Kaggle configurada no ambiente.
Não salve credenciais no código ou no repositório.

As transformações das avaliações, entregas e produtos ficam em
`src/transform.py`. `src/prepare_data.py` executa essas transformações e grava
as tabelas diretamente em `data/database/olist.db`, sem arquivos intermediários.

## Executar as etapas

Na raiz do repositório, execute o pipeline e abra o painel:

```powershell
python app.py
```

O `app.py` executa download e preparação com gravação no SQLite, depois inicia
o Streamlit. Para abrir apenas o painel depois de já ter preparado o banco:

```powershell
python -m streamlit run src/dashboard.py
```

O download baixa novamente o conjunto do Kaggle e substitui os CSVs existentes
em `data/csv/`. Execute `prepare_data.py` sempre que quiser recalcular os dados
tratados; as tabelas gerenciadas no SQLite são substituídas a cada execução,
evitando duplicações.

O painel exibe a quantidade de avaliações por nota usando a tabela
`reviews_clean` no SQLite.
