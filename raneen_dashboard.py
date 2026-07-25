import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io, gc

st.set_page_config(page_title="Raneen Dashboard", layout="wide", page_icon="📊")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #f8f9fa; }
[data-testid="stSidebar"] { background: #1F3864; }
[data-testid="stSidebar"] * { color: white !important; }
.metric-card { background:white;border-radius:10px;padding:.9rem 1.1rem;box-shadow:0 1px 4px rgba(0,0,0,0.08);margin-bottom:.5rem; }
.metric-label { font-size:12px;color:#888;margin:0 0 4px; }
.metric-value { font-size:22px;font-weight:600;color:#1F3864;margin:0; }
.metric-sub { font-size:11px;color:#aaa;margin:2px 0 0; }
.section-title { font-size:13px;font-weight:600;color:#1F3864;text-transform:uppercase;letter-spacing:.06em;border-bottom:2px solid #1F3864;padding-bottom:6px;margin:2rem 0 1rem; }
[data-testid="stDownloadButton"] > button { background:#1F3864!important;color:white!important;border:none!important;border-radius:8px!important;font-weight:600!important;font-size:12px!important; }
</style>
""", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────────────────
def to_excel(df_e):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df_e.to_excel(w, index=False)
    return buf.getvalue()

PAL = ["#3266ad","#d85a30","#2a9e75","#ba7517","#533ab7","#993556","#185fa5","#639922","#854f0b","#2c2c2a"]

DEFAULT_URL  = "https://raw.githubusercontent.com/gawadyahmed2018-web/raneen-dashboard/main/raneen_default_data.csv"
MAPPING_URL  = "https://raw.githubusercontent.com/gawadyahmed2018-web/raneen-dashboard/main/category_mapping.csv"
NEEDED_COLS = ["Order #","Purchase Date","Day","Marketplace Seller","Seller_Raw",
               "Attribute Set","Name","SKU","Qty Ordered","Item Price","Row Total",
               "Discount Amount","Value After Discounts","Coupon Code","Customer Region","Payment Method"]


def optimize(df):
    for c in ["Value After Discounts","Qty Ordered","Item Price","Row Total","Discount Amount"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("float32").fillna(0)
    for c in ["Attribute Set","Marketplace Seller","Customer Region","Payment Method"]:
        if c in df.columns:
            df[c] = df[c].astype("category")
    if "Attribute Set" in df.columns:
        _map = load_mapping()
        if _map:
            df["Main Category"] = df["Attribute Set"].astype(str).map(_map).fillna("Other")
            df["Main Category"] = df["Main Category"].astype("category")
    return df


MONTHLY_TARGETS = {
    1:  {"budget": 6_038_416,  "spend_pct": 3.60, "total": 168_716_207, "mp": 56_605_296,  "retail": 112_110_911},
    2:  {"budget": 3_533_095,  "spend_pct": 3.20, "total": 111_789_600, "mp": 45_003_367,  "retail":  66_786_233},
    3:  {"budget": 4_214_038,  "spend_pct": 3.00, "total": 140_954_260, "mp": 50_164_513,  "retail":  90_789_747},
    4:  {"budget": 4_124_552,  "spend_pct": 3.20, "total": 127_069_401, "mp": 54_536_761,  "retail":  72_532_640},
    5:  {"budget": 4_916_567,  "spend_pct": 3.30, "total": 147_585_977, "mp": 56_404_107,  "retail":  91_181_870},
    6:  {"budget": 7_583_190,  "spend_pct": 3.60, "total": 211_373_442, "mp": 90_894_279,  "retail": 120_479_163},
    7:  {"budget": 5_966_908,  "spend_pct": 3.40, "total": 174_637_356, "mp": 69_000_867,  "retail": 105_636_489},
    8:  {"budget": 5_489_475,  "spend_pct": 3.30, "total": 166_923_634, "mp": 63_342_181,  "retail": 103_581_453},
    9:  {"budget": 4_981_784,  "spend_pct": 3.40, "total": 145_805_090, "mp": 62_152_786,  "retail":  83_652_304},
    10: {"budget": 4_365_925,  "spend_pct": 3.10, "total": 141_978_168, "mp": 59_902_368,  "retail":  82_075_800},
    11: {"budget":14_731_264,  "spend_pct": 4.35, "total": 338_156_399, "mp":148_855_992,  "retail": 189_300_407},
    12: {"budget": 3_871_710,  "spend_pct": 3.10, "total": 125_906_478, "mp": 52_929_212,  "retail":  72_977_266},
}

GSHEET_SPEND_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTvCm7gn0G_PlQTKLV-gIRkuCXbfkQ956kNrK6jmUdgqRfL5LfI6x5IhJKs6l0a0g/pub?gid=1982732416&single=true&output=csv"

def get_period_targets(month, n_days, total_days_in_month):
    t = MONTHLY_TARGETS.get(month, {})
    if not t: return 0, 0, 0, 0, 0
    ratio = n_days / total_days_in_month
    return (round(t["total"]*ratio), round(t["retail"]*ratio),
            round(t["mp"]*ratio), round(t["budget"]*ratio), t["spend_pct"])

@st.cache_data(ttl=300, max_entries=1, show_spinner=False)
def load_spend():
    try:
        import io as _io2, datetime as _dt2
        df_raw = pd.read_csv(GSHEET_SPEND_URL, header=None)
        rows, cur_year = [], _dt2.date.today().year
        for _, row in df_raw.iterrows():
            date_val  = str(row.iloc[1]).strip()
            spend_val = str(row.iloc[12]).strip()
            if not date_val or date_val in ["nan","B"] or not spend_val or spend_val in ["nan","M"]:
                continue
            try:
                dt = pd.to_datetime(date_val + f" {cur_year}", format="%d-%b %Y", errors="coerce")
                if pd.isna(dt): continue
                spend = float(spend_val.replace(",",""))
                rows.append({"Date": dt.date(), "Total_Spend": spend, "Day": dt.strftime("%b %d")})
            except Exception:
                continue
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Date","Total_Spend","Day"])
    except Exception:
        return pd.DataFrame(columns=["Date","Total_Spend","Day"])

def _ach_color(pct):
    if pct >= 100: return "#0a7a4e"
    if pct >= 80:  return "#1a5fa8"
    if pct >= 60:  return "#9a6400"
    return "#b91c1c"

def _make_gauge(pct, label, value_str, target_str, color):
    bar_color = _ach_color(pct)
    bar_w = min(pct, 100)
    icon = "✅" if pct >= 100 else "🔶" if pct >= 80 else "🔴"
    return (
        '<div style="background:#f8f9fa;border-radius:10px;padding:.8rem 1rem;margin-bottom:4px">'
        + f'<p style="font-size:11px;color:#888;margin:0 0 4px">{label}</p>'
        + f'<p style="font-size:20px;font-weight:600;color:{bar_color};margin:0">{value_str}</p>'
        + f'<p style="font-size:10px;color:#aaa;margin:2px 0 6px">تارجت: {target_str}</p>'
        + '<div style="background:#e0e0e0;border-radius:4px;height:8px">'
        + f'<div style="width:{bar_w:.0f}%;background:{bar_color};height:8px;border-radius:4px"></div></div>'
        + f'<p style="font-size:12px;font-weight:700;color:{bar_color};margin:4px 0 0">{icon} {pct:.1f}%</p>'
        + '</div>'
    )

@st.cache_data(max_entries=1, show_spinner=False)
def process(file):
    df = pd.read_csv(file)
    df = df[df["Purchase Point"].str.contains("Raneen", na=False)].copy()
    df = df[~df["Order Status"].isin(["Canceled","Failed Payment"])].copy()
    for col in ["Item Price","Discount Amount","Row Total"]:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace("EGP","",regex=False).str.replace(",","",regex=False), errors="coerce").fillna(0)
    df["Value After Discounts"] = df["Row Total"] - df["Discount Amount"]
    df["Seller_Raw"] = df["Marketplace Seller"].apply(lambda x: "raneen" if pd.isna(x) or str(x).strip()==""  else str(x).strip())
    df["Marketplace Seller"] = df["Marketplace Seller"].apply(lambda x: "raneen" if pd.isna(x) or str(x).strip()==""  else "MP")
    df["Purchase Date"] = pd.to_datetime(df["Purchase Date"], errors="coerce")
    df["Day"] = df["Purchase Date"].dt.strftime("%b %d")
    df = df[[c for c in NEEDED_COLS if c in df.columns]].copy()
    return optimize(df)

def load_default():
    import requests as _r, io as _io
    try:
        r = _r.get(DEFAULT_URL, timeout=20)
        if r.status_code == 200 and len(r.content) > 200:
            return optimize(pd.read_csv(_io.StringIO(r.text)))
    except Exception as e:
        st.sidebar.error(f"خطأ في تحميل البيانات: {e}")
    return None

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Raneen Analytics")
    st.markdown("---")
    st.markdown("""<div style="background:linear-gradient(135deg,#d85a30,#e87a50);border-radius:10px;padding:1rem;text-align:center;margin-bottom:.75rem">
      <p style="color:white;font-size:15px;font-weight:800;margin:0 0 4px">⬆️ أضف الشيت المحدَّث هنا</p>
      <p style="color:rgba(255,255,255,.85);font-size:11px;margin:0">CSV من ماجينتو</p></div>""", unsafe_allow_html=True)
    uploaded = st.file_uploader("", type=["csv"], label_visibility="collapsed")

    if uploaded is not None:
        import base64, requests as _gr, io as _gio
        try:
            token = st.secrets["GITHUB_TOKEN"]
            repo  = "gawadyahmed2018-web/raneen-dashboard"
            gh_h  = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
            uploaded.seek(0)
            df_p = process(uploaded)

            def _put(path, df_s, label):
                buf = _gio.StringIO(); df_s.to_csv(buf, index=False)
                enc = base64.b64encode(buf.getvalue().encode()).decode()
                url = f"https://api.github.com/repos/{repo}/contents/{path}"
                sha = _gr.get(url, headers=gh_h).json().get("sha","")
                return _gr.put(url, headers=gh_h, json={"message":f"Auto-update {label}","content":enc,"sha":sha}).status_code in [200,201]

            ok = _put("raneen_default_data.csv", df_p, "default")
            df_p["_dt"] = pd.to_datetime(df_p["Purchase Date"], errors="coerce")
            df_p["_ym"] = df_p["_dt"].dt.to_period("M").astype(str)
            saved = []
            for ym in df_p["_ym"].dropna().unique():
                if _put(f"archive/raneen_{ym.replace('-','_')}.csv", df_p[df_p["_ym"]==ym].drop(columns=["_dt","_ym"],errors="ignore"), ym):
                    saved.append(ym)
            df_p.drop(columns=["_dt","_ym"], errors="ignore", inplace=True)
            if ok:
                st.success(f"✅ اتحفظ! أرشيف: {', '.join(saved)}" if saved else "✅ اتحفظ!")
            st.cache_data.clear()
            uploaded.seek(0)
        except Exception:
            uploaded.seek(0)

    st.markdown("---")
    _archives = {
        "الشهر الحالي": None,
        "مايو 2026":    "archive/raneen_2026_05.csv",
        "أبريل 2026":   "archive/raneen_2026_04.csv",
    }
    _sel = st.selectbox("اختار شهر", list(_archives.keys()), label_visibility="collapsed")
    _merge = st.checkbox("📅 ضم الشهر السابق", value=False)
    st.markdown("---")
    st.markdown("**كيفية الاستخدام:**")
    st.markdown("1. نزّل الشيت من ماجينتو\n2. ارفعه هنا\n3. الداشبورد بيتحدث فوراً")

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
if uploaded is not None:
    df_full = process(uploaded)
else:
    _arc_path = _archives.get(_sel)
    if _arc_path:
        @st.cache_data(ttl=3600, max_entries=1, show_spinner=False)
        def _load_arc(path):
            import requests as _r2, io as _i2, base64 as _b2
            try:
                tok = st.secrets.get("GITHUB_TOKEN","")
                api = f"https://api.github.com/repos/gawadyahmed2018-web/raneen-dashboard/contents/{path}"
                res = _r2.get(api, headers={"Authorization":f"token {tok}","Accept":"application/vnd.github.v3+json"}, timeout=15)
                if res.status_code == 200:
                    return pd.read_csv(_i2.BytesIO(_b2.b64decode(res.json()["content"].replace("\n",""))))
            except Exception:
                pass
            return None
        df_full = _load_arc(_arc_path)
        if df_full is None:
            st.warning("⚠️ مش لاقي الأرشيف"); st.stop()
        st.sidebar.success(f"📁 {_sel}")
    else:
        df_full = load_default()
        if df_full is None:
            st.warning("⚠️ لا توجد بيانات — ارفع شيت ماجينتو"); st.stop()

df_full["Purchase Date"] = pd.to_datetime(df_full["Purchase Date"], errors="coerce")
if "Day" not in df_full.columns:
    df_full["Day"] = df_full["Purchase Date"].dt.strftime("%b %d")
# Add Main Category
if "Attribute Set" in df_full.columns and "Main Category" not in df_full.columns:
    _cat_map = load_mapping()
    if _cat_map:
        df_full["Main Category"] = df_full["Attribute Set"].astype(str).map(_cat_map).fillna("Other")

if _merge and _sel == "الشهر الحالي" and uploaded is None:
    import requests as _r3, io as _i3
    try:
        cm = int(df_full["Purchase Date"].dt.month.mode()[0])
        cy = int(df_full["Purchase Date"].dt.year.mode()[0])
        if cm > 1:
            url = f"https://raw.githubusercontent.com/gawadyahmed2018-web/raneen-dashboard/main/archive/raneen_{cy}_{str(cm-1).zfill(2)}.csv"
            tok = st.secrets.get("GITHUB_TOKEN","")
            rp = _r3.get(url, headers={"Authorization":f"token {tok}"}, timeout=15)
            if rp.status_code == 200:
                dp = pd.read_csv(_i3.StringIO(rp.text))
                dp["Purchase Date"] = pd.to_datetime(dp["Purchase Date"], errors="coerce")
                if "Day" not in dp.columns: dp["Day"] = dp["Purchase Date"].dt.strftime("%b %d")
                df_full = pd.concat([dp, df_full], ignore_index=True).sort_values("Purchase Date").reset_index(drop=True)
                del dp; gc.collect()
                st.sidebar.success("✅ تم دمج الشهر السابق")
    except Exception:
        pass

all_days  = sorted(df_full["Day"].unique(), key=lambda d: pd.to_datetime(d+" 2026"))
all_dates = sorted(df_full["Purchase Date"].dt.date.unique())

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("# 📊 Raneen Sales Dashboard")
st.markdown('<p style="background:linear-gradient(90deg,#1F3864,#3266ad);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:18px;font-weight:800;margin-top:-8px">✦ Created by Ahmed Khamis</p>', unsafe_allow_html=True)
st.markdown("---")

# Channel filter
_ch = st.radio("القناة", ["📊 الكل","🏪 Retail","🏬 Marketplace (MP)"], horizontal=True, label_visibility="collapsed")

# Date filter
c1,c2,c3 = st.columns([2,2,3])
with c1: date_from = st.date_input("من", value=all_dates[0], min_value=all_dates[0], max_value=all_dates[-1], key="df")
with c2: date_to   = st.date_input("إلى", value=all_dates[-1], min_value=all_dates[0], max_value=all_dates[-1], key="dt")
with c3:
    st.markdown(""); st.markdown("")
    st.info(f"📅 **{date_from.strftime('%b %d')} → {date_to.strftime('%b %d')}** · {(date_to-date_from).days+1} يوم")
st.markdown("---")

days_range = [d for d in all_days if date_from <= pd.to_datetime(d+" 2026").date() <= date_to]
df = df_full[df_full["Day"].isin(days_range)].copy()
if _ch == "🏪 Retail":       df = df[df["Marketplace Seller"]=="raneen"].copy()
elif _ch == "🏬 Marketplace (MP)": df = df[df["Marketplace Seller"]=="MP"].copy()

days_sorted = days_range
total   = df["Value After Discounts"].sum()
df_r    = df[df["Marketplace Seller"]=="raneen"]
df_mp   = df[df["Marketplace Seller"]=="MP"]
raneen  = df_r["Value After Discounts"].sum()
mp      = df_mp["Value After Discounts"].sum()
total_orders  = df["Order #"].nunique()
raneen_orders = df_r["Order #"].nunique()
mp_orders     = df_mp["Order #"].nunique()
total_qty  = df["Qty Ordered"].sum()
raneen_qty = df_r["Qty Ordered"].sum()
mp_qty     = df_mp["Qty Ordered"].sum()
aov_total  = total/total_orders   if total_orders  else 0
aov_raneen = raneen/raneen_orders if raneen_orders else 0
aov_mp     = mp/mp_orders         if mp_orders     else 0

# ── METRICS ───────────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">المبيعات الإجمالية</p>', unsafe_allow_html=True)
m1,m2,m3 = st.columns(3)
with m1: st.markdown(f'<div class="metric-card"><p class="metric-label">إجمالي المبيعات</p><p class="metric-value">{total/1e6:.2f}M ج</p><p class="metric-sub">{total_orders:,} أوردر</p></div>', unsafe_allow_html=True)
with m2: st.markdown(f'<div class="metric-card" style="border-left:4px solid #3266ad"><p class="metric-label">Raneen</p><p class="metric-value" style="color:#3266ad">{raneen/1e6:.2f}M ج</p><p class="metric-sub">{raneen/total*100:.1f}% · {raneen_orders:,} أوردر</p></div>', unsafe_allow_html=True)
with m3: st.markdown(f'<div class="metric-card" style="border-left:4px solid #d85a30"><p class="metric-label">MP</p><p class="metric-value" style="color:#d85a30">{mp/1e6:.2f}M ج</p><p class="metric-sub">{mp/total*100:.1f}% · {mp_orders:,} أوردر</p></div>', unsafe_allow_html=True)

m4,m5,m6 = st.columns(3)
with m4: st.markdown(f'<div class="metric-card"><p class="metric-label">AOV الإجمالي</p><p class="metric-value">{aov_total:,.0f} ج</p></div>', unsafe_allow_html=True)
with m5: st.markdown(f'<div class="metric-card" style="border-left:4px solid #3266ad"><p class="metric-label">AOV — Raneen</p><p class="metric-value" style="color:#3266ad">{aov_raneen:,.0f} ج</p></div>', unsafe_allow_html=True)
with m6: st.markdown(f'<div class="metric-card" style="border-left:4px solid #d85a30"><p class="metric-label">AOV — MP</p><p class="metric-value" style="color:#d85a30">{aov_mp:,.0f} ج</p></div>', unsafe_allow_html=True)

m7,m8,m9 = st.columns(3)
with m7: st.markdown(f'<div class="metric-card"><p class="metric-label">إجمالي القطع</p><p class="metric-value">{total_qty:,}</p></div>', unsafe_allow_html=True)
with m8: st.markdown(f'<div class="metric-card" style="border-left:4px solid #3266ad"><p class="metric-label">قطع Raneen</p><p class="metric-value" style="color:#3266ad">{raneen_qty:,}</p></div>', unsafe_allow_html=True)
with m9: st.markdown(f'<div class="metric-card" style="border-left:4px solid #d85a30"><p class="metric-label">قطع MP</p><p class="metric-value" style="color:#d85a30">{mp_qty:,}</p></div>', unsafe_allow_html=True)


# ── TARGETS & ACHIEVEMENT ─────────────────────────────────────────────────────
import calendar as _cal
_sel_month = date_from.month
_n_sel_days = (date_to - date_from).days + 1
_tdim = _cal.monthrange(date_from.year, _sel_month)[1]
_tgt_total, _tgt_retail, _tgt_mp, _tgt_budget, _tgt_spend_pct = get_period_targets(_sel_month, _n_sel_days, _tdim)

if _tgt_total > 0:
    st.markdown('<p class="section-title">نسبة تحقيق التارجت</p>', unsafe_allow_html=True)
    _ach_total  = total  / _tgt_total  * 100 if _tgt_total  > 0 else 0
    _ach_raneen = raneen / _tgt_retail * 100 if _tgt_retail > 0 else 0
    _ach_mp     = mp     / _tgt_mp    * 100 if _tgt_mp    > 0 else 0
    gc1, gc2, gc3 = st.columns(3)
    with gc1: st.markdown(_make_gauge(_ach_total,  "إجمالي المبيعات", f"{total/1e6:.2f}M ج",  f"{_tgt_total/1e6:.2f}M ج",  "#1F3864"), unsafe_allow_html=True)
    with gc2: st.markdown(_make_gauge(_ach_raneen, "Raneen",           f"{raneen/1e6:.2f}M ج", f"{_tgt_retail/1e6:.2f}M ج", "#3266ad"), unsafe_allow_html=True)
    with gc3: st.markdown(_make_gauge(_ach_mp,     "MP",               f"{mp/1e6:.2f}M ج",     f"{_tgt_mp/1e6:.2f}M ج",     "#d85a30"), unsafe_allow_html=True)
    try:
        df_spend = load_spend()
        if not df_spend.empty:
            total_spend = df_spend[df_spend["Day"].isin(days_sorted)]["Total_Spend"].sum()
            if total_spend > 0:
                sc1,sc2,sc3,sc4 = st.columns(4)
                with sc1: st.markdown(f'<div class="metric-card"><p class="metric-label">إجمالي الإنفاق</p><p class="metric-value">{total_spend:,.0f} ج</p></div>', unsafe_allow_html=True)
                with sc2: st.markdown(f'<div class="metric-card"><p class="metric-label">البادجت المحدد</p><p class="metric-value">{_tgt_budget:,.0f} ج</p></div>', unsafe_allow_html=True)
                with sc3: st.markdown(f'<div class="metric-card"><p class="metric-label">نسبة الإنفاق الفعلية</p><p class="metric-value">{total_spend/total*100:.2f}%</p></div>', unsafe_allow_html=True)
                with sc4: st.markdown(f'<div class="metric-card"><p class="metric-label">التارجت المسموح</p><p class="metric-value">{_tgt_spend_pct:.1f}%</p></div>', unsafe_allow_html=True)
    except Exception:
        pass

# ── TARGETS & ACHIEVEMENT ─────────────────────────────────────────────────────
import calendar as _cal
_sel_month = date_from.month
_n_sel_days = (date_to - date_from).days + 1
_tdim = _cal.monthrange(date_from.year, _sel_month)[1]
_tgt_total, _tgt_retail, _tgt_mp, _tgt_budget, _tgt_spend_pct = get_period_targets(_sel_month, _n_sel_days, _tdim)

if _tgt_total > 0:
    st.markdown('<p class="section-title">نسبة تحقيق التارجت</p>', unsafe_allow_html=True)
    _ach_total  = total  / _tgt_total  * 100 if _tgt_total  > 0 else 0
    _ach_raneen = raneen / _tgt_retail * 100 if _tgt_retail > 0 else 0
    _ach_mp     = mp     / _tgt_mp     * 100 if _tgt_mp     > 0 else 0
    gc1, gc2, gc3 = st.columns(3)
    with gc1: st.markdown(_make_gauge(_ach_total,  "إجمالي المبيعات", f"{total/1e6:.2f}M ج",  f"{_tgt_total/1e6:.2f}M ج",  "#1F3864"), unsafe_allow_html=True)
    with gc2: st.markdown(_make_gauge(_ach_raneen, "Raneen",           f"{raneen/1e6:.2f}M ج", f"{_tgt_retail/1e6:.2f}M ج", "#3266ad"), unsafe_allow_html=True)
    with gc3: st.markdown(_make_gauge(_ach_mp,     "MP",               f"{mp/1e6:.2f}M ج",     f"{_tgt_mp/1e6:.2f}M ج",     "#d85a30"), unsafe_allow_html=True)
    try:
        df_spend = load_spend()
        if not df_spend.empty:
            total_spend = df_spend[df_spend["Day"].isin(days_sorted)]["Total_Spend"].sum()
            if total_spend > 0:
                sc1,sc2,sc3,sc4 = st.columns(4)
                with sc1: st.markdown(f'<div class="metric-card"><p class="metric-label">إجمالي الإنفاق</p><p class="metric-value">{total_spend:,.0f} ج</p></div>', unsafe_allow_html=True)
                with sc2: st.markdown(f'<div class="metric-card"><p class="metric-label">البادجت المحدد</p><p class="metric-value">{_tgt_budget:,.0f} ج</p></div>', unsafe_allow_html=True)
                with sc3: st.markdown(f'<div class="metric-card"><p class="metric-label">نسبة الإنفاق الفعلية</p><p class="metric-value">{total_spend/total*100:.2f}%</p></div>', unsafe_allow_html=True)
                with sc4: st.markdown(f'<div class="metric-card"><p class="metric-label">التارجت المسموح</p><p class="metric-value">{_tgt_spend_pct:.1f}%</p></div>', unsafe_allow_html=True)
    except Exception:
        pass

# ── DAILY CHART ───────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">Raneen vs MP — مبيعات يومية</p>', unsafe_allow_html=True)
daily_r   = df[df["Marketplace Seller"]=="raneen"].groupby("Day")["Value After Discounts"].sum()
daily_mp  = df[df["Marketplace Seller"]=="MP"].groupby("Day")["Value After Discounts"].sum()
daily_tot = df.groupby("Day")["Value After Discounts"].sum()
r_vals   = [daily_r.get(d,0)   for d in days_sorted]
mp_vals  = [daily_mp.get(d,0)  for d in days_sorted]
tot_vals = [daily_tot.get(d,0) for d in days_sorted]

fig_ts = go.Figure()
fig_ts.add_trace(go.Scatter(x=days_sorted, y=r_vals,   name="Raneen",    mode="lines+markers", line=dict(color="#3266ad",width=2.5), marker=dict(size=5), hovertemplate="<b>%{x}</b><br>Raneen: %{y:,.0f} ج<extra></extra>"))
fig_ts.add_trace(go.Scatter(x=days_sorted, y=mp_vals,  name="MP",        mode="lines+markers", line=dict(color="#d85a30",width=2.5), marker=dict(size=5), hovertemplate="<b>%{x}</b><br>MP: %{y:,.0f} ج<extra></extra>"))
fig_ts.add_trace(go.Scatter(x=days_sorted, y=tot_vals, name="الإجمالي",  mode="lines+markers", line=dict(color="#2a9e75",width=2,dash="dot"), marker=dict(size=4), hovertemplate="<b>%{x}</b><br>الإجمالي: %{y:,.0f} ج<extra></extra>"))
fig_ts.update_layout(height=300, margin=dict(t=10,b=10,l=10,r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h",yanchor="bottom",y=1.02), yaxis=dict(tickformat=",.0f",gridcolor="rgba(128,128,128,0.1)"), xaxis=dict(showgrid=False), hovermode="x unified")
st.plotly_chart(fig_ts, use_container_width=True, config={"displayModeBar":False})

# ── CATEGORY CHART ────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">مبيعات كل قسم — Raneen vs MP</p>', unsafe_allow_html=True)

# Filters row
_mc_list = sorted(df["Main Category"].dropna().unique().tolist()) if "Main Category" in df.columns else []
cf0,cf1,cf2 = st.columns([2,2,1])
with cf0:
    _sel_main_cat = st.selectbox("فلتر بـ Main Category", ["كل الأقسام"] + _mc_list, label_visibility="collapsed", key="main_cat_filter")
with cf1:
    search_cat = st.text_input("ابحث بالقسم", placeholder="Air Conditioner...", label_visibility="collapsed")
with cf2:
    ch_f = st.selectbox("فلتر", ["الكل","Raneen + MP","Raneen فقط","MP فقط"], label_visibility="collapsed")

# Apply Main Category filter
_df_for_cat = df.copy()
if _sel_main_cat != "كل الأقسام" and "Main Category" in _df_for_cat.columns:
    _df_for_cat = _df_for_cat[_df_for_cat["Main Category"] == _sel_main_cat]

cat_all = _df_for_cat.groupby(["Attribute Set","Marketplace Seller"])["Value After Discounts"].sum().unstack(fill_value=0).reset_index()
if "MP"     not in cat_all.columns: cat_all["MP"]     = 0
if "raneen" not in cat_all.columns: cat_all["raneen"] = 0
cat_all["Total"] = cat_all["MP"] + cat_all["raneen"]
cat_all = cat_all.sort_values("Total", ascending=False)

cat_ch = cat_all.copy()
if search_cat: cat_ch = cat_ch[cat_ch["Attribute Set"].astype(str).str.lower().str.contains(search_cat.lower())]
if ch_f=="Raneen + MP":  cat_ch = cat_ch[(cat_ch["raneen"]>0)&(cat_ch["MP"]>0)]
elif ch_f=="Raneen فقط": cat_ch = cat_ch[(cat_ch["raneen"]>0)&(cat_ch["MP"]==0)]
elif ch_f=="MP فقط":     cat_ch = cat_ch[(cat_ch["MP"]>0)&(cat_ch["raneen"]==0)]

# ── TOP PRODUCTS ──────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">أعلى المنتجات طلباً</p>', unsafe_allow_html=True)
tp_c0,tp_c1,tp_c2 = st.columns([2,2,1])
with tp_c0:
    _mc_tp_list = ["كل الأقسام"] + (sorted(df["Main Category"].dropna().unique().tolist()) if "Main Category" in df.columns else [])
    _sel_mc_tp = st.selectbox("Main Category", _mc_tp_list, label_visibility="collapsed", key="mc_tp")
with tp_c1:
    _df_tp_src = df[df["Main Category"]==_sel_mc_tp] if (_sel_mc_tp != "كل الأقسام" and "Main Category" in df.columns) else df
    _sel_cat_tp = st.selectbox("القسم", ["كل الأقسام"]+sorted(_df_tp_src["Attribute Set"].dropna().astype(str).unique().tolist()), label_visibility="collapsed", key="cat_tp")
with tp_c2: _sel_perf = st.selectbox("الأداء", ["كل المنتجات","⭐ ممتاز (90%+)","✅ جيد (80-90%)","🔴 ضعيف (<70%)"], label_visibility="collapsed")

_df_tp = df.copy()
if _sel_mc_tp != "كل الأقسام" and "Main Category" in _df_tp.columns:
    _df_tp = _df_tp[_df_tp["Main Category"] == _sel_mc_tp]
if _sel_cat_tp != "كل الأقسام":
    _df_tp = _df_tp[_df_tp["Attribute Set"].astype(str) == _sel_cat_tp]
top_prod = _df_tp.groupby("Name").agg(SKU=("SKU","first"), Qty=("Qty Ordered","sum"), Revenue=("Value After Discounts","sum"), Days=("Day","nunique")).sort_values("Qty",ascending=False).reset_index()
total_d = len(days_sorted)
top_prod["Pct"] = (top_prod["Days"]/total_d*100).round(1) if total_d > 0 else 0
if _sel_perf=="⭐ ممتاز (90%+)":   top_prod=top_prod[top_prod["Pct"]>=90]
elif _sel_perf=="✅ جيد (80-90%)": top_prod=top_prod[(top_prod["Pct"]>=80)&(top_prod["Pct"]<90)]
elif _sel_perf=="🔴 ضعيف (<70%)": top_prod=top_prod[top_prod["Pct"]<70]
top_prod = top_prod.head(20).reset_index(drop=True)

_dl1,_dl2 = st.columns([3,1])
with _dl1: st.caption(f"عرض {len(top_prod)} منتج")
with _dl2: st.download_button("⬇ Excel", to_excel(top_prod[["SKU","Name","Qty","Revenue","Days","Pct"]]), "منتجات.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

mx_q = top_prod["Qty"].max() or 1; mx_r = top_prod["Revenue"].max() or 1
p_rows = ""
for _,rp in top_prod.iterrows():
    pct=rp["Pct"]; icon="⭐" if pct>=90 else "✅" if pct>=80 else "🔶" if pct>=70 else "🔴"
    col="#0a7a4e" if pct>=90 else "#1a5fa8" if pct>=80 else "#9a6400" if pct>=70 else "#b91c1c"
    p_rows += f"""<tr style="border-bottom:.5px solid #f0f0f0">
<td style="padding:4px 6px;font-family:monospace;font-size:10px;color:#666;max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{rp['SKU']}">{str(rp['SKU'])[:14]}</td>
<td style="padding:4px 6px;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{rp['Name']}">{str(rp['Name'])[:45]}{'…' if len(str(rp['Name']))>45 else ''}</td>
<td style="padding:4px 6px;text-align:right;font-weight:600">{int(rp['Qty']):,}<div style="background:#e8f0fb;border-radius:2px;height:3px;margin-top:2px"><div style="width:{int(rp['Qty']/mx_q*80)}%;background:#3266ad;height:3px"></div></div></td>
<td style="padding:4px 6px;text-align:right">{rp['Revenue']:,.0f}<div style="background:#fde8e0;border-radius:2px;height:3px;margin-top:2px"><div style="width:{int(rp['Revenue']/mx_r*80)}%;background:#d85a30;height:3px"></div></div></td>
<td style="padding:4px 6px;text-align:center"><span style="background:{'#e6f9f0' if pct>=90 else '#e8f4fd' if pct>=80 else '#fff8e6' if pct>=70 else '#fdf0f0'};color:{col};padding:2px 7px;border-radius:6px;font-size:11px;font-weight:700">{icon} {pct:.0f}%</span></td>
</tr>"""
st.markdown(f"""<div style="max-height:480px;overflow-y:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">
<tr style="border-bottom:1.5px solid #1F3864;background:#1F3864;position:sticky;top:0">
<th style="padding:7px 6px;color:#b5d4f4;font-size:11px">SKU</th>
<th style="padding:7px 6px;color:white;font-size:11px;text-align:left">المنتج</th>
<th style="padding:7px 6px;color:#b5d4f4;font-size:11px;text-align:right">الكمية</th>
<th style="padding:7px 6px;color:#f0997b;font-size:11px;text-align:right">المبيعات (ج)</th>
<th style="padding:7px 6px;color:#9fe1cb;font-size:11px;text-align:center">نسبة الأداء</th>
</tr>{p_rows}</table></div>""", unsafe_allow_html=True)

# ── COUPONS ───────────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">خصومات الكوبونات</p>', unsafe_allow_html=True)
c_df = df[df["Coupon Code"].notna()].copy()
c_df["Coupon"] = c_df["Coupon Code"].astype(str).str.strip().str.upper()
coup = c_df.groupby("Coupon").agg(Total_Discount=("Discount Amount","sum"), Orders=("Order #","nunique")).sort_values("Total_Discount",ascending=False).head(15).reset_index()
coup = coup[coup["Total_Discount"]>0]
if len(coup)>0:
    coup_total = coup["Total_Discount"].sum()
    fig_coup = go.Figure(go.Bar(x=coup["Coupon"], y=coup["Total_Discount"], marker_color=PAL[:len(coup)], text=coup["Total_Discount"].apply(lambda x:f"{x/1000:.0f}K"), textposition="outside"))
    fig_coup.update_layout(showlegend=False, height=260, margin=dict(t=10,b=10,l=10,r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(title=""), yaxis=dict(tickformat=",.0f"))
    st.plotly_chart(fig_coup, use_container_width=True, config={"displayModeBar":False})

# ── REGIONS ───────────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">مبيعات كل محافظة</p>', unsafe_allow_html=True)
region_map = {'Cairo':'القاهرة','Giza':'الجيزة','Alexandria':'الأسكندرية','Qalyubia':'القليوبية','Al Sharqia':'الشرقية','Sohag':'سوهاج','Al Monufia':'المنوفية','Al Minufiya':'المنوفية','Al Beheira':'البحيرة','Al Daqahliya':'الدقهلية','Asyut':'أسيوط','Al Gharbia':'الغربية','Red Sea':'البحر الأحمر','Ismailia':'الأسماعيلية','Suez':'السويس','Al Fayoum':'الفيوم','Damietta':'دمياط','Qena':'قنا','Port Said':'بور سعيد','Al Meniya':'المنيا','Luxor':'الأقصر','Aswan':'أسوان','Bani Souaif':'بني سويف','Kafr El-Sheikh':'كفر الشيخ','North Coast':'الساحل الشمالي'}
df_reg = df[["Customer Region","Value After Discounts","Order #","Qty Ordered"]].copy()
df_reg["Region"] = df_reg["Customer Region"].map(region_map).fillna(df_reg["Customer Region"])
reg_df = df_reg.groupby("Region").agg(revenue=("Value After Discounts","sum"), orders=("Order #","nunique")).sort_values("revenue",ascending=False).head(20).reset_index()
reg_df["pct"] = (reg_df["revenue"]/reg_df["revenue"].sum()*100).round(1)
REG_PAL = ["#3266ad","#185fa5","#378add","#85b7eb","#b5d4f4","#d85a30","#ba7517","#2a9e75","#0f6e56","#533ab7","#3c3489","#993556","#639922","#854f0b","#888780"]
fig_reg = go.Figure(go.Bar(y=reg_df["Region"], x=reg_df["revenue"], orientation="h", marker_color=[REG_PAL[min(i,14)] for i in range(len(reg_df))], text=reg_df["pct"].astype(str)+"%", textposition="outside", hovertemplate="%{y}: %{x:,.0f} ج<extra></extra>"))
fig_reg.update_layout(height=380, margin=dict(t=10,b=10,l=10,r=60), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(tickformat=",.0f"), yaxis=dict(tickfont=dict(size=11)), showlegend=False)
st.plotly_chart(fig_reg, use_container_width=True, config={"displayModeBar":False})
st.download_button("⬇ Excel — المحافظات", to_excel(reg_df), "محافظات.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ── PAYMENT ───────────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">طرق الدفع</p>', unsafe_allow_html=True)
pay_df = df.groupby("Payment Method").agg(revenue=("Value After Discounts","sum"), orders=("Order #","nunique")).sort_values("revenue",ascending=False).reset_index()
pay_df["pct"] = (pay_df["revenue"]/pay_df["revenue"].sum()*100).round(1)
pa1,pa2 = st.columns(2)
with pa1:
    fig_donut = go.Figure(go.Pie(labels=pay_df["Payment Method"], values=pay_df["revenue"], hole=.55, marker_colors=PAL, textinfo="label+percent", hovertemplate="%{label}: %{value:,.0f} ج<extra></extra>"))
    fig_donut.update_layout(height=280, margin=dict(t=10,b=10,l=10,r=10), paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
    st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar":False})
with pa2:
    fig_pb = go.Figure(go.Bar(x=pay_df["Payment Method"], y=pay_df["revenue"], marker_color=PAL[:len(pay_df)], text=pay_df["pct"].astype(str)+"%", textposition="outside"))
    fig_pb.update_layout(showlegend=False, height=280, margin=dict(t=10,b=10,l=10,r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(tickfont=dict(size=9)), yaxis=dict(tickformat=",.0f"))
    st.plotly_chart(fig_pb, use_container_width=True, config={"displayModeBar":False})

st.markdown(f"<p style='text-align:center;color:#aaa;font-size:11px'>Raneen Analytics · {date_from} → {date_to}</p>", unsafe_allow_html=True)
