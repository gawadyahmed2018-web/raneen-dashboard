import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Raneen Sales Dashboard", layout="wide", page_icon="📊")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #f8f9fa; }
[data-testid="stSidebar"] { background: #1F3864; }
[data-testid="stSidebar"] * { color: white !important; }

.metric-card {
    background: white; border-radius: 10px; padding: 1rem 1.25rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: .5rem;
}

.metric-label { font-size: 12px; color: #888; margin: 0 0 4px; }
.metric-value { font-size: 22px; font-weight: 600; color: #1F3864; margin: 0; }
.metric-sub { font-size: 11px; color: #aaa; margin: 2px 0 0; }

.section-title {
    font-size: 13px; font-weight: 600; color: #1F3864;
    text-transform: uppercase; letter-spacing: .06em;
    border-bottom: 2px solid #1F3864; padding-bottom: 6px;
    margin: 2rem 0 1rem;
}

/* 🔥 Download Button Styling */
div.stDownloadButton > button {
    background: linear-gradient(135deg, #d85a30, #ff7a45);
    color: white;
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 600;
    border: none;
    transition: all 0.2s ease-in-out;
    width: 100%;
}

div.stDownloadButton > button:hover {
    background: linear-gradient(135deg, #ba4c28, #e56735);
    transform: scale(1.03);
    box-shadow: 0 3px 8px rgba(0,0,0,0.15);
}

div.stDownloadButton > button:active {
    transform: scale(0.97);
}
</style>
""", unsafe_allow_html=True)

COLORS = {"raneen": "#3266ad", "MP": "#d85a30"}
PAL = ["#3266ad","#185fa5","#378add","#85b7eb","#d85a30","#ba7517","#2a9e75","#533ab7","#993556","#2c2c2a"]

def clean_money(s):
    return pd.to_numeric(
        s.astype(str).str.replace("EGP","",regex=False).str.replace(",","",regex=False).str.strip(),
        errors="coerce"
    ).fillna(0)

@st.cache_data
def process(file):
    df = pd.read_csv(file)
    df = df[df["Purchase Point"].str.contains("Raneen", na=False)].copy()
    df = df[~df["Order Status"].isin(["Canceled","Failed Payment"])].copy()
    for col in ["Item Price","Discount Amount","Marketing Discount","Commercial Discount","Row Total"]:
        df[col] = clean_money(df[col])
    df["Value After Discounts"] = df["Row Total"] - df["Discount Amount"]
    df["Seller_Raw"] = df["Marketplace Seller"].apply(
        lambda x: "raneen" if pd.isna(x) or str(x).strip()=="" else str(x).strip()
    )
    df["Marketplace Seller"] = df["Marketplace Seller"].apply(
        lambda x: "raneen" if pd.isna(x) or str(x).strip()==""  else "MP"
    )
    df["Purchase Date"] = pd.to_datetime(df["Purchase Date"], errors="coerce")
    df["Day"] = df["Purchase Date"].dt.strftime("%b %d")
    return df

# ── DEFAULT DATA ──
DEFAULT_DATA_URL = "https://raw.githubusercontent.com/gawadyahmed2018-web/raneen-dashboard/main/raneen_default_data.csv"

@st.cache_data(ttl=3600)
def load_default():
    return pd.read_csv(DEFAULT_DATA_URL)

# ── SIDEBAR ──
with st.sidebar:
    st.markdown("## 📊 Raneen Analytics")
    uploaded = st.file_uploader("", type=["csv"], label_visibility="collapsed")

# ── MAIN ──
using_default = uploaded is None

if using_default:
    df_full = load_default()
    df_full["Purchase Date"] = pd.to_datetime(df_full["Purchase Date"], errors="coerce")
    df_full["Day"] = df_full["Purchase Date"].dt.strftime("%b %d")
else:
    df_full = process(uploaded)

all_days = sorted(df_full["Day"].dropna().unique())
df = df_full.copy()

st.markdown("# 📊 Raneen Sales Dashboard")
st.markdown("---")

# مثال زر تحميل
st.download_button(
    "📥 تحميل البيانات",
    df.to_csv(index=False).encode("utf-8"),
    "data.csv",
    "text/csv"
)
