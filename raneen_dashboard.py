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
    # Keep raw seller name before converting to MP/raneen
    df["Seller_Raw"] = df["Marketplace Seller"].apply(
        lambda x: "raneen" if pd.isna(x) or str(x).strip()=="" else str(x).strip()
    )
    df["Marketplace Seller"] = df["Marketplace Seller"].apply(
        lambda x: "raneen" if pd.isna(x) or str(x).strip()==""  else "MP"
    )
    df["Purchase Date"] = pd.to_datetime(df["Purchase Date"], format="%b %d, %Y, %I:%M:%S %p", errors="coerce")
    df["Day"] = df["Purchase Date"].dt.strftime("%b %d")
    return df

def get_price_changes(df):
    df_s = df.sort_values("Purchase Date")
    results = []
    for sku, grp in df_s.groupby("SKU"):
        grp = grp.sort_values("Purchase Date")
        prev, name, attr = None, grp.iloc[0]["Name"], grp.iloc[0]["Attribute Set"]
        changes = []
        for _, row in grp.iterrows():
            if prev is None: prev = row["Item Price"]; continue
            if row["Item Price"] != prev:
                change_date = row["Purchase Date"].strftime("%b %d")
                # حساب الكمية المباعة من هذا المنتج في يوم التغيير
                day_qty = grp[grp["Day"] == change_date]["Qty Ordered"].sum()
                changes.append({"SKU":sku,"Product":name,"Category":attr,
                    "Date":change_date,
                    "Price Before":prev,"Price After":row["Item Price"],
                    "Change":round(row["Item Price"]-prev,2),
                    "Qty on Day":int(day_qty)})
                prev = row["Item Price"]
        if len(changes)>=3:
            for c in changes: c["# Changes"]=len(changes)
            results.extend(changes)
    return pd.DataFrame(results) if results else pd.DataFrame()

# ── DEFAULT DATA URL ─────────────────────────────────────────────────────────
DEFAULT_DATA_URL = "https://raw.githubusercontent.com/gawadyahmed2018-web/raneen-dashboard/main/raneen_default_data.csv"

@st.cache_data(ttl=3600)
def load_default():
    return pd.read_csv(DEFAULT_DATA_URL)

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Raneen Analytics")
    st.markdown("---")
    st.markdown("""
    <div style="background:linear-gradient(135deg,#d85a30,#e87a50);border-radius:10px;padding:1rem 1rem;text-align:center;margin-bottom:.75rem;box-shadow:0 3px 10px rgba(216,90,48,.35)">
      <p style="color:white;font-size:15px;font-weight:800;margin:0 0 4px;letter-spacing:.02em">⬆️ أضف الشيت المحدَّث هنا</p>
      <p style="color:rgba(255,255,255,.85);font-size:11px;margin:0">CSV من ماجينتو ← الداشبورد يتحدث فوراً</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <style>
    [data-testid="stFileUploader"] {
        border: 2px dashed #d85a30 !important;
        border-radius: 8px !important;
        background: rgba(216,90,48,.06) !important;
    }
    [data-testid="stFileUploader"] label { color: #d85a30 !important; font-weight: 600 !important; }
    [data-testid="stFileUploaderDropzone"] { background: transparent !important; }
    [data-testid="stFileUploaderDropzoneInstructions"] svg { fill: #d85a30 !important; }
    [data-testid="stFileUploaderDropzoneInstructions"] span { color: #d85a30 !important; font-weight:600 !important; }
    </style>
    """, unsafe_allow_html=True)
    uploaded = st.file_uploader("", type=["csv"], label_visibility="collapsed")

    # Auto-save processed CSV to GitHub when file uploaded
    if uploaded is not None:
        import base64, requests, io
        try:
            token = st.secrets["GITHUB_TOKEN"]
            repo = "gawadyahmed2018-web/raneen-dashboard"
            path = "raneen_default_data.csv"
            api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
            headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

            # Process the uploaded file first then save processed version
            uploaded.seek(0)
            df_processed = process(uploaded)
            # Convert processed df to CSV bytes
            csv_buffer = io.StringIO()
            df_processed.to_csv(csv_buffer, index=False)
            raw_bytes = csv_buffer.getvalue().encode("utf-8")

            # Get current file SHA (needed for update)
            r_get = requests.get(api_url, headers=headers)
            sha = r_get.json().get("sha", "") if r_get.status_code == 200 else ""

            # Upload processed CSV
            encoded = base64.b64encode(raw_bytes).decode()
            payload = {"message": "Auto-update default data", "content": encoded, "sha": sha}
            r_put = requests.put(api_url, headers=headers, json=payload)

            if r_put.status_code in [200, 201]:
                st.success("✅ اتحفظ كـ Default أوتوماتيك!")
            else:
                st.warning("⚠️ الداشبورد شغال بس التحديث التلقائي فشل")
            uploaded.seek(0)
        except Exception:
            uploaded.seek(0)

    st.markdown("---")
    st.markdown("**كيفية الاستخدام:**")
    st.markdown("1. نزّل الشيت من ماجينتو\n2. ارفعه هنا\n3. الداشبورد بيظهر فوراً")

# ── MAIN ─────────────────────────────────────────────────────────────────────
using_default = uploaded is None

if using_default:
    try:
        df_full = load_default()
        # Make sure Purchase Date is parsed
        df_full["Purchase Date"] = pd.to_datetime(df_full["Purchase Date"], errors="coerce")
        if "Day" not in df_full.columns:
            df_full["Day"] = df_full["Purchase Date"].dt.strftime("%b %d")
        # Show update button at top
        st.markdown("""
        <div style="background:#1F3864;border-radius:10px;padding:1rem 1.5rem;margin-bottom:1rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px">
          <div>
            <p style="color:#85b7eb;font-size:12px;margin:0">📊 عارض داتا آخر شيت محفوظ — 1 إلى 10 أبريل 2026</p>
            <p style="color:#fff;font-size:11px;margin:4px 0 0;opacity:.7">لتحديث البيانات ارفع شيت ماجينتو الجديد من القايمة الجانبية</p>
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.sidebar.markdown("""
        <div style="background:#d85a30;border-radius:8px;padding:.75rem 1rem;text-align:center;margin-bottom:.5rem">
          <p style="color:white;font-size:13px;font-weight:600;margin:0">⬆️ أضف الشيت المحدَّث هنا</p>
          <p style="color:rgba(255,255,255,.8);font-size:11px;margin:4px 0 0">لتحديث بيانات الداشبورد</p>
        </div>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"تعذّر تحميل البيانات الافتراضية: {e}")
        st.stop()
else:
    df_full = process(uploaded)
all_days = sorted(df_full["Day"].unique(), key=lambda d: pd.to_datetime(d+" 2026"))
all_dates = sorted(df_full["Purchase Date"].dt.date.unique())

# ── DATE RANGE FILTER ────────────────────────────────────────────────────────
st.markdown("# 📊 Raneen Sales Dashboard")
st.markdown('<p style="color:#3266ad;font-size:16px;font-weight:600;margin-top:-10px;letter-spacing:.01em">✦ Created by / Ahmed Khamis</p>', unsafe_allow_html=True)
st.markdown("---")

col_dr1, col_dr2, col_dr3 = st.columns([2,2,3])
with col_dr1:
    date_from = st.selectbox("من يوم", options=all_days, index=0, key="date_from")
with col_dr2:
    from_idx = all_days.index(date_from)
    days_to_options = all_days[from_idx:]
    # Always default to last available day
    default_to_idx = len(days_to_options) - 1
    date_to = st.selectbox("إلى يوم", options=days_to_options, index=default_to_idx, key="date_to")
with col_dr3:
    st.markdown("")
    st.markdown("")
    n_days_selected = all_days.index(date_to) - all_days.index(date_from) + 1
    st.info(f"📅 **{date_from}  →  {date_to}**  ·  {n_days_selected} يوم")

st.markdown("---")

# Filter dataframe based on selected date range
days_range = all_days[all_days.index(date_from): all_days.index(date_to)+1]
df = df_full[df_full["Day"].isin(days_range)].copy()

date_min = df["Purchase Date"].dt.date.min()
date_max = df["Purchase Date"].dt.date.max()

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

aov_total  = total  / total_orders  if total_orders  else 0
aov_raneen = raneen / raneen_orders if raneen_orders else 0
aov_mp     = mp     / mp_orders     if mp_orders     else 0

days_sorted = days_range

# ── METRICS ROW 1: Sales ──────────────────────────────────────────────────────
st.markdown('<p class="section-title">المبيعات الإجمالية</p>', unsafe_allow_html=True)
c1,c2,c3 = st.columns(3)
with c1:
    st.markdown(f'<div class="metric-card"><p class="metric-label">إجمالي المبيعات</p><p class="metric-value">{total/1e6:.2f}M ج</p><p class="metric-sub">{total_orders:,} أوردر</p></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card" style="border-left:4px solid #3266ad"><p class="metric-label">مبيعات Raneen</p><p class="metric-value" style="color:#3266ad">{raneen/1e6:.2f}M ج</p><p class="metric-sub">{raneen/total*100:.1f}% · {raneen_orders:,} أوردر</p></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-card" style="border-left:4px solid #d85a30"><p class="metric-label">مبيعات MP</p><p class="metric-value" style="color:#d85a30">{mp/1e6:.2f}M ج</p><p class="metric-sub">{mp/total*100:.1f}% · {mp_orders:,} أوردر</p></div>', unsafe_allow_html=True)

# ── METRICS ROW 2: AOV ────────────────────────────────────────────────────────
c4,c5,c6 = st.columns(3)
with c4:
    st.markdown(f'<div class="metric-card"><p class="metric-label">AOV الإجمالي</p><p class="metric-value">{aov_total:,.0f} ج</p><p class="metric-sub">متوسط قيمة الأوردر</p></div>', unsafe_allow_html=True)
with c5:
    st.markdown(f'<div class="metric-card" style="border-left:4px solid #3266ad"><p class="metric-label">AOV — Raneen</p><p class="metric-value" style="color:#3266ad">{aov_raneen:,.0f} ج</p></div>', unsafe_allow_html=True)
with c6:
    st.markdown(f'<div class="metric-card" style="border-left:4px solid #d85a30"><p class="metric-label">AOV — MP</p><p class="metric-value" style="color:#d85a30">{aov_mp:,.0f} ج</p></div>', unsafe_allow_html=True)

# ── METRICS ROW 3: Qty ────────────────────────────────────────────────────────
c7,c8,c9 = st.columns(3)
with c7:
    st.markdown(f'<div class="metric-card"><p class="metric-label">إجمالي القطع المباعة</p><p class="metric-value">{total_qty:,}</p><p class="metric-sub">Qty Ordered</p></div>', unsafe_allow_html=True)
with c8:
    st.markdown(f'<div class="metric-card" style="border-left:4px solid #3266ad"><p class="metric-label">قطع Raneen</p><p class="metric-value" style="color:#3266ad">{raneen_qty:,}</p><p class="metric-sub">{raneen_qty/total_qty*100:.1f}% من الإجمالي</p></div>', unsafe_allow_html=True)
with c9:
    st.markdown(f'<div class="metric-card" style="border-left:4px solid #d85a30"><p class="metric-label">قطع MP</p><p class="metric-value" style="color:#d85a30">{mp_qty:,}</p><p class="metric-sub">{mp_qty/total_qty*100:.1f}% من الإجمالي</p></div>', unsafe_allow_html=True)

# ── RANEEN VS MP ──────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">Raneen vs MP — مبيعات يومية</p>', unsafe_allow_html=True)

daily_r   = df[df["Marketplace Seller"]=="raneen"].groupby("Day")["Value After Discounts"].sum()
daily_mp  = df[df["Marketplace Seller"]=="MP"].groupby("Day")["Value After Discounts"].sum()
daily_tot = df.groupby("Day")["Value After Discounts"].sum()

r_vals   = [daily_r.get(d, 0)  for d in days_sorted]
mp_vals  = [daily_mp.get(d, 0) for d in days_sorted]
tot_vals = [daily_tot.get(d, 0) for d in days_sorted]

fig_ts = go.Figure()
fig_ts.add_trace(go.Scatter(
    x=days_sorted, y=r_vals, name="Raneen",
    mode="lines+markers", line=dict(color="#3266ad", width=2.5),
    marker=dict(size=6),
    hovertemplate="<b>%{x}</b><br>Raneen: %{y:,.0f} ج<extra></extra>"
))
fig_ts.add_trace(go.Scatter(
    x=days_sorted, y=mp_vals, name="MP",
    mode="lines+markers", line=dict(color="#d85a30", width=2.5),
    marker=dict(size=6),
    hovertemplate="<b>%{x}</b><br>MP: %{y:,.0f} ج<extra></extra>"
))
fig_ts.add_trace(go.Scatter(
    x=days_sorted, y=tot_vals, name="الإجمالي",
    mode="lines+markers", line=dict(color="#2a9e75", width=2, dash="dot"),
    marker=dict(size=5),
    hovertemplate="<b>%{x}</b><br>الإجمالي: %{y:,.0f} ج<extra></extra>"
))

# Add percentage annotations on hover
for i, day in enumerate(days_sorted):
    tot = tot_vals[i]
    if tot > 0:
        r_pct = r_vals[i] / tot * 100
        mp_pct = mp_vals[i] / tot * 100

fig_ts.update_layout(
    height=320,
    margin=dict(t=20, b=20, l=10, r=10),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    yaxis=dict(tickformat=",.0f", gridcolor="rgba(128,128,128,0.1)"),
    xaxis=dict(showgrid=False),
    hovermode="x unified"
)
st.plotly_chart(fig_ts, use_container_width=True)

# Summary row below chart
col_ts1, col_ts2, col_ts3 = st.columns(3)
with col_ts1:
    st.markdown(f'<div class="metric-card"><p class="metric-label">إجمالي الفترة</p><p class="metric-value">{total/1e6:.2f}M ج</p><p class="metric-sub">{total_orders:,} أوردر</p></div>', unsafe_allow_html=True)
with col_ts2:
    st.markdown(f'<div class="metric-card" style="border-left:4px solid #3266ad"><p class="metric-label">Raneen</p><p class="metric-value" style="color:#3266ad">{raneen/1e6:.2f}M ج</p><p class="metric-sub">{raneen/total*100:.1f}% من الإجمالي</p></div>', unsafe_allow_html=True)
with col_ts3:
    st.markdown(f'<div class="metric-card" style="border-left:4px solid #d85a30"><p class="metric-label">MP</p><p class="metric-value" style="color:#d85a30">{mp/1e6:.2f}M ج</p><p class="metric-sub">{mp/total*100:.1f}% من الإجمالي</p></div>', unsafe_allow_html=True)

# ── BY CATEGORY ───────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">مبيعات كل قسم — Raneen vs MP</p>', unsafe_allow_html=True)

cat_all = df.groupby(["Attribute Set","Marketplace Seller"])["Value After Discounts"].sum().unstack(fill_value=0).reset_index()
if "MP" not in cat_all.columns: cat_all["MP"]=0
if "raneen" not in cat_all.columns: cat_all["raneen"]=0
cat_all["Total"] = cat_all["MP"] + cat_all["raneen"]
cat_all["Channel"] = cat_all.apply(lambda r: "Raneen Only" if r["MP"]==0 else ("MP Only" if r["raneen"]==0 else "Both"), axis=1)
cat_all = cat_all.sort_values("Total", ascending=False)
cat_all["Attribute Set"] = cat_all["Attribute Set"].str.replace("&amp;","&")

col_f1, col_f2 = st.columns([2,1])
with col_f1:
    search_cat = st.text_input("ابحث باسم القسم", placeholder="مثال: Air Conditioner", label_visibility="collapsed")
with col_f2:
    channel_filter = st.selectbox("فلتر القسم", ["كل الأقسام","Raneen + MP معاً","Raneen فقط","MP فقط"], label_visibility="collapsed")

cat_ch = cat_all.copy()
if search_cat:
    cat_ch = cat_ch[cat_ch["Attribute Set"].str.lower().str.contains(search_cat.lower())]
if channel_filter == "Raneen + MP معاً":
    cat_ch = cat_ch[(cat_ch["raneen"]>0) & (cat_ch["MP"]>0)]
elif channel_filter == "Raneen فقط":
    cat_ch = cat_ch[(cat_ch["raneen"]>0) & (cat_ch["MP"]==0)]
elif channel_filter == "MP فقط":
    cat_ch = cat_ch[(cat_ch["MP"]>0) & (cat_ch["raneen"]==0)]

_dl_col1, _dl_col2 = st.columns([3,1])
with _dl_col1:
    st.caption(f"عرض {len(cat_ch)} من {len(cat_all)} قسم — الشارت بيعرض أعلى 12 من النتايج")
with _dl_col2:
    _cat_csv = cat_ch[["Attribute Set","Channel","raneen","MP","Total"]].rename(columns={"Attribute Set":"القسم","raneen":"Raneen (ج)","MP":"MP (ج)","Total":"الإجمالي (ج)","Channel":"Channel"})
    st.download_button("⬇ تحميل CSV", _cat_csv.to_csv(index=False, encoding="utf-8-sig"), "مبيعات_الأقسام.csv", "text/csv", use_container_width=True)

fig_cat = go.Figure()
chart_data = cat_ch.head(12)
fig_cat.add_trace(go.Bar(name="Raneen", y=chart_data["Attribute Set"], x=chart_data["raneen"],
    orientation="h", marker_color="#3266ad", hovertemplate="%{x:,.0f} ج<extra>Raneen</extra>"))
fig_cat.add_trace(go.Bar(name="MP", y=chart_data["Attribute Set"], x=chart_data["MP"],
    orientation="h", marker_color="#d85a30", hovertemplate="%{x:,.0f} ج<extra>MP</extra>"))
fig_cat.update_layout(barmode="group", height=max(320, len(chart_data)*38),
    margin=dict(t=10,b=10,l=10,r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02), xaxis=dict(tickformat=",.0f"))
st.plotly_chart(fig_cat, use_container_width=True)

# Category table with heatmap bars
max_total = cat_ch["Total"].max() if len(cat_ch) > 0 else 1
cat_html = """<div style='max-height:520px;overflow-y:auto'><table style='width:100%;border-collapse:collapse;font-size:12px'>
<tr style='border-bottom:1.5px solid #e0e0e0;position:sticky;top:0;background:white;z-index:2'>
<th style='padding:7px 8px;text-align:left;color:#555;font-size:11px'>#</th>
<th style='padding:7px 8px;text-align:left;color:#555;font-size:11px'>القسم</th>
<th style='padding:7px 8px;text-align:left;color:#555;font-size:11px'>Channel</th>
<th style='padding:7px 8px;text-align:right;color:#3266ad;font-size:11px'>Raneen (ج)</th>
<th style='padding:7px 8px;text-align:right;color:#d85a30;font-size:11px'>MP (ج)</th>
<th style='padding:7px 8px;text-align:right;color:#555;font-size:11px'>الإجمالي (ج)</th>
<th style='padding:7px 8px;color:#555;font-size:11px;min-width:160px'>Raneen vs MP</th>
</tr>"""
for i, (_, row) in enumerate(cat_ch.iterrows(), 1):
    tot = row["Total"] if row["Total"] > 0 else 1
    r_pct = row["raneen"] / tot * 100
    m_pct = row["MP"] / tot * 100
    bar_w = row["Total"] / max_total * 100
    ch = row["Channel"]
    ch_color = "#3266ad" if ch=="Raneen Only" else "#d85a30" if ch=="MP Only" else "#2a9e75"
    ch_bg    = "#e6f1fb" if ch=="Raneen Only" else "#fcebeb" if ch=="MP Only" else "#e1f5ee"
    # Split bar: raneen blue, mp orange
    split_bar = f"""<div style='display:flex;height:8px;border-radius:4px;overflow:hidden;width:{bar_w:.0f}%;min-width:4px'>
<div style='width:{r_pct:.0f}%;background:#3266ad'></div>
<div style='width:{m_pct:.0f}%;background:#d85a30'></div>
</div>
<div style='font-size:10px;color:#aaa;margin-top:2px'>{r_pct:.0f}% Raneen · {m_pct:.0f}% MP</div>"""
    cat_html += f"""<tr style='border-bottom:.5px solid #f0f0f0'>
<td style='padding:6px 8px;color:#aaa'>{i}</td>
<td style='padding:6px 8px;font-weight:{"500" if i<=5 else "400"}'>{row["Attribute Set"]}</td>
<td style='padding:6px 8px'><span style='background:{ch_bg};color:{ch_color};font-size:10px;padding:1px 6px;border-radius:6px;font-weight:500'>{ch}</span></td>
<td style='padding:6px 8px;text-align:right;color:#3266ad'>{row["raneen"]:,.0f}</td>
<td style='padding:6px 8px;text-align:right;color:#d85a30'>{row["MP"]:,.0f}</td>
<td style='padding:6px 8px;text-align:right;font-weight:500'>{row["Total"]:,.0f}</td>
<td style='padding:6px 8px'>{split_bar}</td>
</tr>"""
cat_html += "</table></div>"
st.markdown(cat_html, unsafe_allow_html=True)

# ── PRICE CHANGES with category dropdown ──────────────────────────────────────
st.markdown('<p class="section-title">المنتجات التي تغير سعرها أكثر من 3 مرات</p>', unsafe_allow_html=True)

pc = get_price_changes(df)
if not pc.empty:
    pc["Category"] = pc["Category"].str.replace("&amp;","&")
    cats_available = ["الكل"] + sorted(pc["Category"].unique().tolist())
    selected_cat = st.selectbox("فلتر بالقسم", cats_available, key="pc_cat")
    pc_show = pc if selected_cat=="الكل" else pc[pc["Category"]==selected_cat]
    pc_show = pc_show.sort_values(["# Changes","SKU"], ascending=[False,True])
    n_prods = pc_show["SKU"].nunique()
    _pc_col1, _pc_col2 = st.columns([3,1])
    with _pc_col1:
        st.caption(f"{n_prods} منتج · {len(pc_show)} تغيير")
    with _pc_col2:
        st.download_button("⬇ تحميل CSV", pc_show.to_csv(index=False, encoding="utf-8-sig"), "تغييرات_السعر.csv", "text/csv", use_container_width=True)
    # Build grouped HTML table - product name appears once, changes listed below
    pc_show = pc_show.copy()
    pc_html = """<table style='width:100%;border-collapse:collapse;font-size:12px'>
<tr style='border-bottom:1.5px solid #e0e0e0;background:var(--color-background-secondary,#f8f9fa)'>
<th style='padding:7px 10px;text-align:left;color:#555;font-size:11px;width:30%'>المنتج</th>
<th style='padding:7px 10px;text-align:left;color:#555;font-size:11px;width:12%'>التاريخ</th>
<th style='padding:7px 10px;text-align:right;color:#555;font-size:11px'>قبل (ج)</th>
<th style='padding:7px 10px;text-align:right;color:#555;font-size:11px'>بعد (ج)</th>
<th style='padding:7px 10px;text-align:right;color:#555;font-size:11px'>الفرق</th>
<th style='padding:7px 10px;text-align:right;color:#555;font-size:11px'>كمية اليوم</th>
<th style='padding:7px 10px;text-align:center;color:#555;font-size:11px'># تغييرات</th>
</tr>"""
    last_sku = None
    for _, row in pc_show.iterrows():
        is_new = row["SKU"] != last_sku
        if is_new:
            last_sku = row["SKU"]
            n = int(row["# Changes"])
            nbg = "#faeeda" if n>=7 else "#e1f5ee" if n>=6 else "#e6f1fb" if n>=5 else "#fcebeb" if n>=4 else "#f5f5f5"
            nc  = "#633806" if n>=7 else "#085041" if n>=6 else "#0c447c" if n>=5 else "#501313" if n>=4 else "#555"
            name_short = str(row["Product"])[:55] + ("..." if len(str(row["Product"]))>55 else "")
            pc_html += f"""<tr style='border-top:2px solid #d0d0d0;background:#fafafa'>
<td colspan='5' style='padding:7px 10px;font-weight:600;font-size:12px;color:#1F3864'>{name_short}<br>
<span style='font-family:monospace;font-size:10px;color:#888'>{row["SKU"]}</span>
<span style='font-size:10px;color:#888;margin-right:6px'>· {row["Category"]}</span></td>
<td style='padding:7px 10px;text-align:center'><span style='background:{nbg};color:{nc};padding:2px 7px;border-radius:8px;font-size:11px;font-weight:600'>{n}x</span></td>
</tr>"""
        change_val = row["Change"]
        chg_color = "#2a9e75" if change_val > 0 else "#d85a30"
        chg_str   = f'+{change_val:,.0f}' if change_val > 0 else f'{change_val:,.0f}'
        qty_day   = int(row.get("Qty on Day", 0))
        pc_html += f"""<tr style='border-bottom:.5px solid #eee'>
<td style='padding:5px 10px;color:var(--color-text-tertiary,#aaa);font-size:11px;padding-right:20px'>↳</td>
<td style='padding:5px 10px;color:#555'>{row["Date"]}</td>
<td style='padding:5px 10px;text-align:right;color:#555'>{row["Price Before"]:,.0f}</td>
<td style='padding:5px 10px;text-align:right;font-weight:500'>{row["Price After"]:,.0f}</td>
<td style='padding:5px 10px;text-align:right;font-weight:600;color:{chg_color}'>{chg_str}</td>
<td style='padding:5px 10px;text-align:right;font-weight:600;color:#533ab7'>{qty_day:,}</td>
<td></td>
</tr>"""
    pc_html += "</table>"
    st.markdown(pc_html, unsafe_allow_html=True)
else:
    st.info("لا توجد منتجات بأكثر من 3 تغييرات في السعر")
st.markdown('<p class="section-title">مبيعات يومية — أعلى 6 أقسام</p>', unsafe_allow_html=True)

top6_cats = df.groupby("Attribute Set")["Value After Discounts"].sum().nlargest(6).index.tolist()
fig_line = go.Figure()
for i, cat in enumerate(top6_cats):
    cat_data = df[df["Attribute Set"]==cat].groupby("Day")["Value After Discounts"].sum()
    vals = [cat_data.get(d,0) for d in days_sorted]
    fig_line.add_trace(go.Scatter(x=days_sorted, y=vals, name=cat.replace("&amp;","&"),
        mode="lines+markers", line=dict(color=PAL[i], width=2),
        marker=dict(size=5), hovertemplate="%{y:,.0f} ج<extra>"+cat.replace("&amp;","&")+"</extra>"))
fig_line.update_layout(height=320, margin=dict(t=10,b=10,l=10,r=10),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    yaxis=dict(tickformat=",.0f"), xaxis=dict(showgrid=False))
st.plotly_chart(fig_line, use_container_width=True)

# ── TOP PRODUCTS with heatbar ────────────────────────────────────────────────
st.markdown('<p class="section-title">أعلى المنتجات طلبًا</p>', unsafe_allow_html=True)

# فلاتر: بالقسم + بعدد أيام النشاط + بمعيار الأداء
_col_tp1, _col_tp2, _col_tp3 = st.columns([1,1,1])
with _col_tp1:
    _all_cats_tp = ["كل الأقسام"] + sorted(df["Attribute Set"].dropna().unique().tolist())
    _sel_cat_tp = st.selectbox("فلتر بالقسم", _all_cats_tp, key="tp_cat_filter", label_visibility="collapsed")
with _col_tp2:
    _max_days_tp = len(days_sorted)
    _days_options = ["كل الأيام"] + [str(d) for d in range(1, _max_days_tp + 1)]
    _sel_days_tp = st.selectbox(
        "فلتر بعدد أيام النشاط (على الأقل)",
        _days_options, key="tp_days_filter", label_visibility="collapsed"
    )
with _col_tp3:
    _perf_options = ["كل المنتجات", "⭐ ممتاز (90%+)", "✅ جيد (80–90%)", "🔶 متوسط (70–80%)", "🔴 ضعيف (أقل من 70%)"]
    _sel_perf_tp = st.selectbox("فلتر بمعيار الأداء", _perf_options, key="tp_perf_filter", label_visibility="collapsed")

_df_tp = df.copy()
if _sel_cat_tp != "كل الأقسام":
    _df_tp = _df_tp[_df_tp["Attribute Set"] == _sel_cat_tp]

top_prod = _df_tp.groupby("Name").agg(
    Qty=("Qty Ordered","sum"),
    Revenue=("Value After Discounts","sum"),
    Days=("Day","nunique")
).sort_values("Qty", ascending=False)

if _sel_days_tp != "كل الأيام":
    _min_days = int(_sel_days_tp)
    top_prod = top_prod[top_prod["Days"] >= _min_days]

total_d = len(days_sorted)
top_prod["Pct"] = (top_prod["Days"] / total_d * 100).round(1) if total_d > 0 else 0

# فلتر الأداء
if _sel_perf_tp == "⭐ ممتاز (90%+)":
    top_prod = top_prod[top_prod["Pct"] >= 90]
elif _sel_perf_tp == "✅ جيد (80–90%)":
    top_prod = top_prod[(top_prod["Pct"] >= 80) & (top_prod["Pct"] < 90)]
elif _sel_perf_tp == "🔶 متوسط (70–80%)":
    top_prod = top_prod[(top_prod["Pct"] >= 70) & (top_prod["Pct"] < 80)]
elif _sel_perf_tp == "🔴 ضعيف (أقل من 70%)":
    top_prod = top_prod[top_prod["Pct"] < 70]

top_prod = top_prod.head(30).reset_index()

def _perf_style(pct):
    if pct >= 90:
        return {"bg": "#e6f9f0", "color": "#0a7a4e", "badge_bg": "#0a7a4e", "label": "ممتاز ⭐"}
    elif pct >= 80:
        return {"bg": "#e8f4fd", "color": "#1a5fa8", "badge_bg": "#1a5fa8", "label": "جيد ✅"}
    elif pct >= 70:
        return {"bg": "#fff8e6", "color": "#9a6400", "badge_bg": "#ba7517", "label": "متوسط 🔶"}
    else:
        return {"bg": "#fdf0f0", "color": "#b91c1c", "badge_bg": "#d85a30", "label": "ضعيف 🔴"}

max_qty_p = top_prod["Qty"].max() if len(top_prod) > 0 else 1
max_rev_p = top_prod["Revenue"].max() if len(top_prod) > 0 else 1

prod_rows = ""
for idx_p, row_p in top_prod.iterrows():
    qty_w = int(row_p["Qty"] / max_qty_p * 80) if max_qty_p > 0 else 0
    rev_w = int(row_p["Revenue"] / max_rev_p * 80) if max_rev_p > 0 else 0
    days_act = int(row_p["Days"])
    pct_val  = row_p["Pct"]
    ps       = _perf_style(pct_val)
    heat_cells = "".join([
        '<span style="display:inline-block;width:10px;height:10px;border-radius:2px;margin:1px;background:%s"></span>' % (ps["badge_bg"] if j < days_act else "#e0e0e0")
        for j in range(total_d)
    ])
    name_s = str(row_p["Name"])[:50] + ("..." if len(str(row_p["Name"])) > 50 else "")
    pct_cell = (
        f'<div style="background:{ps["bg"]};border-radius:6px;padding:3px 7px;display:inline-block;min-width:90px;text-align:center">'
        f'<span style="font-weight:700;color:{ps["color"]};font-size:13px">{pct_val:.0f}%</span><br>'
        f'<span style="font-size:10px;color:{ps["color"]};opacity:.85">{ps["label"]}</span>'
        f'</div>'
    )
    prod_rows += (
        '<tr style="border-bottom:.5px solid #f0f0f0">' +
        '<td style="padding:5px 8px;color:#aaa">' + str(idx_p+1) + '</td>' +
        '<td style="padding:5px 8px;max-width:200px" title="' + str(row_p["Name"]) + '">' + name_s + '</td>' +
        '<td style="padding:5px 8px;text-align:right"><span style="font-weight:600">' + f'{int(row_p["Qty"]):,}' + '</span>' +
        '<div style="background:#e8f0fb;border-radius:2px;height:4px;margin-top:3px"><div style="width:' + str(qty_w) + '%;background:#3266ad;height:4px;border-radius:2px"></div></div></td>' +
        '<td style="padding:5px 8px;text-align:right">' + f'{row_p["Revenue"]:,.0f}' +
        '<div style="background:#fde8e0;border-radius:2px;height:4px;margin-top:3px"><div style="width:' + str(rev_w) + '%;background:#d85a30;height:4px;border-radius:2px"></div></div></td>' +
        '<td style="padding:5px 8px">' + heat_cells + '<span style="font-size:10px;color:#aaa;margin-right:4px">' + str(days_act) + '/' + str(total_d) + '</span></td>' +
        '<td style="padding:5px 8px;text-align:center">' + pct_cell + '</td></tr>'
    )

prod_html = (
    '<div style="max-height:500px;overflow-y:auto">' +
    '<table style="width:100%;border-collapse:collapse;font-size:12px">' +
    '<tr style="border-bottom:1.5px solid #e0e0e0;position:sticky;top:0;background:white;z-index:2">' +
    '<th style="padding:7px 8px;text-align:left;color:#555;font-size:11px">#</th>' +
    '<th style="padding:7px 8px;text-align:left;color:#555;font-size:11px">المنتج</th>' +
    '<th style="padding:7px 8px;text-align:right;color:#555;font-size:11px">الكمية</th>' +
    '<th style="padding:7px 8px;text-align:right;color:#555;font-size:11px">المبيعات (ج)</th>' +
    '<th style="padding:7px 8px;color:#555;font-size:11px">أيام الظهور</th>' +
    '<th style="padding:7px 8px;text-align:center;color:#555;font-size:11px">نسبة الأداء</th></tr>' +
    prod_rows + '</table></div>'
)
st.markdown(prod_html, unsafe_allow_html=True)
_tp_dl = top_prod[["Name","Qty","Revenue","Days","Pct"]].rename(columns={"Name":"المنتج","Qty":"الكمية","Revenue":"المبيعات (ج)","Days":"أيام الظهور","Pct":"نسبة الأداء %"})
st.download_button("⬇ تحميل CSV — أعلى المنتجات", _tp_dl.to_csv(index=False, encoding="utf-8-sig"), "أعلى_المنتجات.csv", "text/csv")
st.markdown('<p class="section-title">خصومات الكوبونات</p>', unsafe_allow_html=True)

c_df = df[df["Coupon Code"].notna() & (df["Coupon Code"].astype(str).str.strip()!="")].copy()
c_df["Coupon"] = c_df["Coupon Code"].str.strip().str.upper()
coup = c_df.groupby("Coupon").agg(
    Total_Discount=("Discount Amount","sum"),
    Orders=("Order #","nunique")
).sort_values("Total_Discount", ascending=False).reset_index()
coup = coup[coup["Total_Discount"]>0]
coup_total = coup["Total_Discount"].sum()

col1, col2 = st.columns([1,1])
with col1:
    fig_coup = px.bar(coup, x="Coupon", y="Total_Discount",
        color="Coupon", color_discrete_sequence=PAL,
        text_auto=".3s")
    fig_coup.update_layout(showlegend=False, height=300,
        margin=dict(t=10,b=10,l=10,r=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="", yaxis_title="", yaxis=dict(tickformat=",.0f"))
    fig_coup.update_traces(textposition="outside")
    st.plotly_chart(fig_coup, use_container_width=True)

with col2:
    max_disc_c = coup["Total_Discount"].max()
    coup_rows = ""
    for idx_c, (_, cr) in enumerate(coup.iterrows()):
        pct_c = cr["Total_Discount"]/coup_total*100
        bw_c = int(cr["Total_Discount"]/max_disc_c*100) if max_disc_c > 0 else 0
        col_c = PAL[idx_c % len(PAL)]
        coup_rows += (
            '<tr style="border-bottom:.5px solid #f0f0f0">' +
            '<td style="padding:5px 8px;font-weight:600;color:' + col_c + ';font-family:monospace">' + str(cr["Coupon"]) + '</td>' +
            '<td style="padding:5px 8px;text-align:right;font-weight:500">' + f'{cr["Total_Discount"]:,.0f}' + '</td>' +
            '<td style="padding:5px 8px;text-align:right;color:#555">' + str(cr["Orders"]) + '</td>' +
            '<td style="padding:5px 8px;min-width:90px"><div style="background:#eee;border-radius:3px;height:6px"><div style="width:' + str(bw_c) + '%;background:' + col_c + ';height:6px;border-radius:3px"></div></div>' +
            '<span style="font-size:10px;color:#aaa">' + f'{pct_c:.1f}%' + '</span></td></tr>'
        )
    coup_html = (
        '<table style="width:100%;border-collapse:collapse;font-size:12px">' +
        '<tr style="border-bottom:1.5px solid #e0e0e0">' +
        '<th style="padding:6px 8px;text-align:left;color:#555;font-size:11px">الكوبون</th>' +
        '<th style="padding:6px 8px;text-align:right;color:#555;font-size:11px">الخصم</th>' +
        '<th style="padding:6px 8px;text-align:right;color:#555;font-size:11px">أوردرات</th>' +
        '<th style="padding:6px 8px;color:#555;font-size:11px">النسبة</th></tr>' +
        coup_rows + '</table>'
    )
    st.markdown(coup_html, unsafe_allow_html=True)

# ── CUSTOMER REGION ───────────────────────────────────────────────────────────
st.markdown('<p class="section-title">مبيعات كل محافظة</p>', unsafe_allow_html=True)

region_map = {
    'Cairo':'القاهرة','Giza':'الجيزة','Alexandria':'الأسكندرية',
    'Qalyubia':'القليوبية','Al Sharqia':'الشرقية','Sohag':'سوهاج',
    'Al Monufia':'المنوفية','Al Minufiya':'المنوفية','Al Beheira':'البحيرة',
    'Al Daqahliya':'الدقهلية','Asyut':'أسيوط','Al Gharbia':'الغربية',
    'Red Sea':'البحر الأحمر','Ismailia':'الأسماعيلية','Suez':'السويس',
    'Al Fayoum':'الفيوم','Damietta':'دمياط','Qena':'قنا',
    'Port Said':'بور سعيد','Al Meniya':'المنيا','Luxor':'الأقصر',
    'Aswan':'أسوان','Bani Souaif':'بني سويف','Kafr El-Sheikh':'كفر الشيخ',
    'North Coast':'الساحل الشمالي'
}
df_reg = df.copy()
df_reg["Region"] = df_reg["Customer Region"].map(region_map).fillna(df_reg["Customer Region"])
region_df = df_reg.groupby("Region").agg(
    revenue=("Value After Discounts","sum"),
    orders=("Order #","nunique"),
    items=("Qty Ordered","sum")
).sort_values("revenue",ascending=False).reset_index()
region_df["pct"] = (region_df["revenue"]/region_df["revenue"].sum()*100).round(1)
region_df["aov"] = (region_df["revenue"]/region_df["orders"]).round(0)

REG_PAL = ["#3266ad","#185fa5","#378add","#85b7eb","#b5d4f4","#d85a30","#ba7517","#2a9e75","#0f6e56","#533ab7","#3c3489","#993556","#639922","#854f0b","#888780"]

fig_reg = go.Figure()
fig_reg.add_trace(go.Bar(
    y=region_df["Region"], x=region_df["revenue"],
    orientation="h",
    marker_color=[REG_PAL[min(i,len(REG_PAL)-1)] for i in range(len(region_df))],
    hovertemplate="%{y}: %{x:,.0f} ج<extra></extra>",
    text=region_df["pct"].astype(str)+"%",
    textposition="outside"
))
fig_reg.update_layout(
    height=max(400, len(region_df)*22),
    margin=dict(t=10,b=10,l=10,r=60),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(tickformat=",.0f"),
    yaxis=dict(ticks="", tickfont=dict(size=11)),
    showlegend=False
)
st.plotly_chart(fig_reg, use_container_width=True)

max_rev_reg = region_df["revenue"].max()
reg_rows = ""
for i2, (_, rr) in enumerate(region_df.iterrows(), 1):
    bw_r = int(rr["revenue"]/max_rev_reg*100) if max_rev_reg > 0 else 0
    col_r2 = REG_PAL[min(i2-1, len(REG_PAL)-1)]
    fw_r = "600" if i2 <= 3 else "400"
    reg_rows += (
        '<tr style="border-bottom:.5px solid #f0f0f0">' +
        '<td style="padding:5px 8px;color:#aaa">' + str(i2) + '</td>' +
        '<td style="padding:5px 8px;font-weight:' + fw_r + '">' + str(rr["Region"]) + '</td>' +
        '<td style="padding:5px 8px;text-align:right;font-weight:500">' + f'{rr["revenue"]:,.0f}' + '</td>' +
        '<td style="padding:5px 8px;text-align:right;color:#555">' + f'{rr["orders"]:,}' + '</td>' +
        '<td style="padding:5px 8px;text-align:right;color:#555">' + f'{rr["aov"]:,.0f}' + '</td>' +
        '<td style="padding:5px 8px;min-width:120px"><div style="background:#eee;border-radius:3px;height:6px"><div style="width:' + str(bw_r) + '%;background:' + col_r2 + ';height:6px;border-radius:3px"></div></div>' +
        '<span style="font-size:10px;color:#aaa">' + str(rr["pct"]) + '%</span></td></tr>'
    )
reg_html = (
    '<div style="max-height:520px;overflow-y:auto">' +
    '<table style="width:100%;border-collapse:collapse;font-size:12px">' +
    '<tr style="border-bottom:1.5px solid #e0e0e0;position:sticky;top:0;background:white">' +
    '<th style="padding:7px 8px;text-align:left;color:#555;font-size:11px">#</th>' +
    '<th style="padding:7px 8px;text-align:left;color:#555;font-size:11px">المحافظة</th>' +
    '<th style="padding:7px 8px;text-align:right;color:#555;font-size:11px">المبيعات (ج)</th>' +
    '<th style="padding:7px 8px;text-align:right;color:#555;font-size:11px">الأوردرات</th>' +
    '<th style="padding:7px 8px;text-align:right;color:#555;font-size:11px">AOV (ج)</th>' +
    '<th style="padding:7px 8px;color:#555;font-size:11px;min-width:120px">النسبة</th></tr>' +
    reg_rows + '</table></div>'
)
st.markdown(reg_html, unsafe_allow_html=True)
_reg_dl = region_df[["Region","revenue","orders","aov","pct"]].rename(columns={"Region":"المحافظة","revenue":"المبيعات (ج)","orders":"الأوردرات","aov":"AOV (ج)","pct":"النسبة %"})
st.download_button("⬇ تحميل CSV — المحافظات", _reg_dl.to_csv(index=False, encoding="utf-8-sig"), "مبيعات_المحافظات.csv", "text/csv")
st.markdown('<p class="section-title">طرق الدفع</p>', unsafe_allow_html=True)

pay_df = df.groupby("Payment Method").agg(
    revenue=("Value After Discounts","sum"),
    orders=("Order #","nunique")
).sort_values("revenue",ascending=False).reset_index()
pay_df["pct"] = (pay_df["revenue"]/pay_df["revenue"].sum()*100).round(1)
pay_df["aov"] = (pay_df["revenue"]/pay_df["orders"]).round(0)

PAY_PAL = ["#3266ad","#d85a30","#2a9e75","#ba7517","#993556","#533ab7","#639922","#854f0b","#888780"]

col_pay1, col_pay2 = st.columns([1,1])
with col_pay1:
    fig_pay_donut = go.Figure(go.Pie(
        labels=pay_df["Payment Method"],
        values=pay_df["revenue"],
        hole=.6,
        marker_colors=PAY_PAL,
        textinfo="label+percent",
        hovertemplate="%{label}: %{value:,.0f} ج (%{percent})<extra></extra>"
    ))
    fig_pay_donut.update_layout(
        height=300, margin=dict(t=10,b=10,l=10,r=10),
        paper_bgcolor="rgba(0,0,0,0)", showlegend=False
    )
    st.plotly_chart(fig_pay_donut, use_container_width=True)

with col_pay2:
    fig_pay_bar = px.bar(
        pay_df, x="Payment Method", y="revenue",
        color="Payment Method", color_discrete_sequence=PAY_PAL,
        text=pay_df["pct"].astype(str)+"%"
    )
    fig_pay_bar.update_layout(
        showlegend=False, height=300,
        margin=dict(t=10,b=10,l=10,r=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="", tickfont=dict(size=9)),
        yaxis=dict(title="", tickformat=",.0f")
    )
    fig_pay_bar.update_traces(textposition="outside")
    st.plotly_chart(fig_pay_bar, use_container_width=True)

max_rev_pay = pay_df["revenue"].max()
pay_rows = ""
for i3, (_, pr) in enumerate(pay_df.iterrows(), 1):
    bw_p = int(pr["revenue"]/max_rev_pay*100) if max_rev_pay > 0 else 0
    col_p2 = PAY_PAL[min(i3-1, len(PAY_PAL)-1)]
    fw_p = "600" if i3 == 1 else "400"
    pay_rows += (
        '<tr style="border-bottom:.5px solid #f0f0f0">' +
        '<td style="padding:5px 8px;color:#aaa">' + str(i3) + '</td>' +
        '<td style="padding:5px 8px;font-weight:' + fw_p + '">' + str(pr["Payment Method"]) + '</td>' +
        '<td style="padding:5px 8px;text-align:right;font-weight:' + fw_p + '">' + f'{pr["revenue"]:,.0f}' + '</td>' +
        '<td style="padding:5px 8px;text-align:right;color:#555">' + f'{pr["orders"]:,}' + '</td>' +
        '<td style="padding:5px 8px;text-align:right;color:#555">' + f'{pr["aov"]:,.0f}' + '</td>' +
        '<td style="padding:5px 8px;min-width:120px"><div style="background:#eee;border-radius:3px;height:6px"><div style="width:' + str(bw_p) + '%;background:' + col_p2 + ';height:6px;border-radius:3px"></div></div>' +
        '<span style="font-size:10px;color:#aaa">' + str(pr["pct"]) + '%</span></td></tr>'
    )
pay_html = (
    '<table style="width:100%;border-collapse:collapse;font-size:12px">' +
    '<tr style="border-bottom:1.5px solid #e0e0e0">' +
    '<th style="padding:7px 8px;text-align:left;color:#555;font-size:11px">#</th>' +
    '<th style="padding:7px 8px;text-align:left;color:#555;font-size:11px">طريقة الدفع</th>' +
    '<th style="padding:7px 8px;text-align:right;color:#555;font-size:11px">المبيعات (ج)</th>' +
    '<th style="padding:7px 8px;text-align:right;color:#555;font-size:11px">الأوردرات</th>' +
    '<th style="padding:7px 8px;text-align:right;color:#555;font-size:11px">AOV (ج)</th>' +
    '<th style="padding:7px 8px;color:#555;font-size:11px;min-width:120px">النسبة</th></tr>' +
    pay_rows + '</table>'
)
st.markdown(pay_html, unsafe_allow_html=True)
_pay_dl = pay_df[["Payment Method","revenue","orders","aov","pct"]].rename(columns={"Payment Method":"طريقة الدفع","revenue":"المبيعات (ج)","orders":"الأوردرات","aov":"AOV (ج)","pct":"النسبة %"})
st.download_button("⬇ تحميل CSV — طرق الدفع", _pay_dl.to_csv(index=False, encoding="utf-8-sig"), "طرق_الدفع.csv", "text/csv")
st.markdown(f"<p style='text-align:center;color:#aaa;font-size:11px'>Raneen Analytics · {date_min} → {date_max}</p>", unsafe_allow_html=True)
