import streamlit as st


def apply_dashboard_styles() -> None:
    """Aplica os elementos visuais do protótipo ao dashboard Streamlit."""
    st.markdown(
        """
        <style>
        .block-container {max-width:1180px; padding-top:1.25rem; padding-bottom:3rem;}
        [data-testid="stHeader"] {background:transparent;}
        h1 {font-size:26px !important; line-height:1.2; letter-spacing:-.01em;}
        h2, [data-testid="stSubheader"] {font-size:16px !important; font-weight:600;}
        [data-testid="stCaptionContainer"] {color:#9bb0ba;}
        [data-testid="stMetric"] {background:#17262e; border:1px solid #2a3d47; border-radius:8px; padding:12px 14px;}
        [data-testid="stMetricLabel"] {color:#9bb0ba; font-size:13px;}
        [data-testid="stMetricValue"] {font-size:26px; font-weight:700;}
        [data-testid="stVerticalBlockBorderWrapper"] {background:#17262e; border-color:#2a3d47; border-radius:8px;}
        [data-testid="stSelectbox"] [data-baseweb="select"] > div,
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {background:#17262e; border-color:#2a3d47; border-radius:8px;}
        [data-testid="stSegmentedControl"] {background:#17262e; border:1px solid #2a3d47; border-radius:8px;}
        [data-testid="stSegmentedControl"] button[aria-pressed="true"] {background:#93b4ff; color:#0f1a20;}
        [data-testid="stPageLink-NavLink"] {border-radius:8px;}
        [data-testid="stPageLink-NavLink"] a[aria-current="page"] {background:#93b4ff; color:#0f1a20; border-radius:8px;}
        div.stButton > button {border-radius:8px;}
        [data-testid="stDataFrame"] {border:1px solid #2a3d47; border-radius:8px; overflow:hidden;}
        @media(max-width:860px) {
          .block-container {padding-left:1rem; padding-right:1rem;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
