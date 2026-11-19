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
`src/transform.py`. `app.py` coordena o download, as transformações e a gravação
direta das tabelas em `data/database/olist.db`.

O banco contém `reviews`, com todas as linhas e colunas do CSV original, e
`reviews_clean`, com comentários não vazios preparados para análise textual,
e `model_predictions`, com previsões do classificador associadas a cada
`review_id`. O sentimento pela nota e o sentimento previsto pelo texto ficam
em campos separados.

## Executar as etapas

Na raiz do repositório, execute o pipeline e abra o painel:

```powershell
python app.py
```

O `app.py` executa download, transformação e carga no SQLite, depois inicia o
Streamlit. Para abrir apenas o dashboard depois de já ter preparado o banco e
o modelo:

```powershell
python -m streamlit run src/dashboard/index.py
```

O download baixa novamente o conjunto do Kaggle e substitui os CSVs existentes
em `data/csv/`. As tabelas gerenciadas no SQLite são substituídas a cada
execução do `app.py`, evitando duplicações.

Os arquivos do dashboard ficam em `src/dashboard/`. Ele tem quatro páginas:
Painel, Desempenho do modelo, Comentários e
Testar comentário. Os filtros de período e categoria ficam no topo. As telas
usam comentários de `reviews_clean`, datas originais de `reviews`, categorias
de `review_product` e previsões de `model_predictions`. As métricas formais de
avaliação do modelo são agregadas e não se recalculam pelos filtros. O dataset
não possui motivos de reclamação, então eles não são apresentados como dados
reais.

A página Testar comentário salva as classificações em `comment_tests`, no
mesmo SQLite. O sentimento correto fica inicialmente vazio e pode ser
informado depois para comparar com a previsão. Ao executar `python app.py`,
somente os testes com sentimento correto preenchido entram como exemplos
manuais no treino; testes sem rótulo são ignorados. Exemplos iguais ao texto do
conjunto de teste reservado são excluídos do treino usado para avaliação.
O treinamento usa somente LogisticRegression.
