import sqlite3

import pandas as pd
import streamlit as st

from src.dashboard.dashboard_data import DATABASE_PATH, load_reviews
from src.dashboard.styles import apply_dashboard_styles


st.set_page_config(page_title="Avaliações de clientes Olist", page_icon="⭐", layout="wide")
apply_dashboard_styles()

if not DATABASE_PATH.is_file():
    st.error("Banco SQLite não encontrado. Execute `python app.py` para preparar os dados.")
    st.stop()

try:
    all_reviews = load_reviews(str(DATABASE_PATH), DATABASE_PATH.stat().st_mtime)
except (sqlite3.Error, pd.errors.DatabaseError) as error:
    st.error(f"Não foi possível consultar as tabelas do banco: {error}")
    st.stop()

periods = ["Todos", *[str(year) for year in sorted(all_reviews["data"].dropna().dt.year.unique())]]
categories = ["Todas", *sorted(all_reviews["categoria"].dropna().unique().tolist())]
st.title("Avaliações de clientes")
category_filter, period_filter = st.columns([2, 3], vertical_alignment="bottom")
with category_filter:
    st.selectbox("Categoria", categories, key="categoria", label_visibility="collapsed", format_func=lambda value: "Todas as categorias" if value == "Todas" else value)
with period_filter:
    st.segmented_control("Período", periods, default=periods[0], key="periodo", label_visibility="collapsed", format_func=lambda value: "Tudo" if value == "Todos" else value)

pages = [
    st.Page("painel.py", title="Painel", icon="📊", default=True),
    st.Page("modelo.py", title="Desempenho do modelo", icon="🧪"),
    st.Page("comentarios.py", title="Comentários", icon="💬"),
    st.Page("testar.py", title="Testar comentário", icon="✍️"),
    st.Page("divergencias.py", title="Revisar divergências", icon="🔎"),
]
page = st.navigation(pages, position="sidebar")
page.run()
