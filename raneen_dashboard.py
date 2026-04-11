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
                changes.append({"SKU":sku,"Product":name,"Category":attr,
                    "Date":row["Purchase Date"].strftime("%b %d"),
                    "Price Before":prev,"Price After":row["Item Price"],
                    "Change":round(row["Item Price"]-prev,2)})
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
    uploaded = st.file_uploader("ارفع شيت ماجينتو (CSV)", type=["csv"])
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
st.markdown("---")

col_dr1, col_dr2, col_dr3 = st.columns([2,2,3])
with col_dr1:
    date_from = st.selectbox("من يوم", options=all_days, index=0, key="date_from")
with col_dr2:
    # Filter options to only days >= date_from
    from_idx = all_days.index(date_from)
    days_to_options = all_days[from_idx:]
    date_to = st.selectbox("إلى يوم", options=days_to_options, index=len(days_to_options)-1, key="date_to")
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

st.caption(f"عرض {len(cat_ch)} من {len(cat_all)} قسم — الشارت بيعرض أعلى 12 من النتايج")

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

cat_display = cat_ch[["Attribute Set","Channel","raneen","MP","Total"]].copy()
cat_display["Raneen %"] = (cat_ch["raneen"]/cat_ch["Total"]*100).round(1).astype(str)+"%"
cat_display["MP %"]     = (cat_ch["MP"]    /cat_ch["Total"]*100).round(1).astype(str)+"%"
cat_display["raneen"]   = cat_display["raneen"].apply(lambda v: f"{v:,.0f}")
cat_display["MP"]       = cat_display["MP"].apply(lambda v: f"{v:,.0f}")
cat_display["Total"]    = cat_display["Total"].apply(lambda v: f"{v:,.0f}")
cat_display.index = range(1, len(cat_display)+1)
st.dataframe(cat_display.rename(columns={"Attribute Set":"القسم","raneen":"Raneen","Total":"الإجمالي"}),
    use_container_width=True)

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
    st.caption(f"{n_prods} منتج · {len(pc_show)} تغيير")
    pc_show = pc_show.copy()
    pc_show["Change"] = pc_show["Change"].apply(lambda v: f"+{v:,.0f}" if v>0 else f"{v:,.0f}")
    st.dataframe(pc_show[["Category","SKU","Product","Date","Price Before","Price After","Change","# Changes"]].rename(
        columns={"Category":"القسم","Product":"المنتج","Date":"التاريخ",
                 "Price Before":"قبل","Price After":"بعد","Change":"الفرق","# Changes":"# تغييرات"}
    ), use_container_width=True, hide_index=True)
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

# ── TOP PRODUCTS ──────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">أعلى المنتجات طلبًا</p>', unsafe_allow_html=True)

top_prod = df.groupby("Name").agg(
    Qty=("Qty Ordered","sum"),
    Revenue=("Value After Discounts","sum"),
    Days=("Day","nunique")
).sort_values("Qty", ascending=False).head(15).reset_index()
top_prod["Revenue"] = top_prod["Revenue"].apply(lambda v: f"{v:,.0f} ج")
top_prod.index = range(1, len(top_prod)+1)
st.dataframe(top_prod.rename(columns={"Name":"المنتج","Qty":"الكمية","Revenue":"المبيعات","Days":"أيام ظهور"}),
    use_container_width=True)

# ── COUPONS ───────────────────────────────────────────────────────────────────
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
    coup["% من الإجمالي"] = (coup["Total_Discount"]/coup_total*100).round(1).astype(str)+"%"
    coup["متوسط / أوردر"] = (coup["Total_Discount"]/coup["Orders"]).round(0).apply(lambda v: f"{v:,.0f} ج")
    coup["Total_Discount"] = coup["Total_Discount"].apply(lambda v: f"{v:,.0f} ج")
    coup.index = range(1, len(coup)+1)
    st.dataframe(coup.rename(columns={"Coupon":"الكوبون","Total_Discount":"إجمالي الخصم","Orders":"الأوردرات"}),
        use_container_width=True)

# ── SELLERS ANALYSIS ──────────────────────────────────────────────────────────
st.markdown('<p class="section-title">تحليل الـ Marketplace Sellers</p>', unsafe_allow_html=True)

# Use Seller_Raw column (real seller names) from df which comes from process()
# For default data loaded from CSV, Seller_Raw is already stored in the file
df_for_sellers = df.copy()
if "Seller_Raw" not in df_for_sellers.columns:
    df_for_sellers["Seller_Raw"] = df_for_sellers["Marketplace Seller"]
df_mp2 = df_for_sellers[df_for_sellers["Seller_Raw"] != "raneen"].copy()
df_mp2["Seller"] = df_mp2["Seller_Raw"]
# Sellers always show full period heatmap (all days in sheet)
all_days_full = sorted(df["Day"].unique(), key=lambda d: pd.to_datetime(d+" 2026"))
total_days_n = len(all_days_full)
last_day = all_days_full[-1]

# Seller summary
seller_summary = df_mp2.groupby("Seller").agg(
    total_revenue=("Value After Discounts","sum"),
    total_qty=("Qty Ordered","sum"),
    orders=("Order #","nunique"),
    days_active=("Day","nunique")
).sort_values("total_revenue", ascending=False).reset_index()

# Daily per seller
seller_daily_raw = df_mp2.groupby(["Seller","Day"])["Value After Discounts"].sum().reset_index()

# Compute last sale, gap, status, warning
def seller_stats(seller):
    sd = seller_daily_raw[seller_daily_raw["Seller"]==seller]
    active = sd["Day"].tolist()
    if not active: return None
    active_sorted = sorted(active, key=lambda d: all_days_full.index(d) if d in all_days_full else 0)
    last = active_sorted[-1]
    first = active_sorted[0]
    last_idx = all_days_full.index(last) if last in all_days_full else 0
    gap = (total_days_n - 1) - last_idx
    first3 = all_days_full[:3]
    last3 = all_days_full[-3:]
    rev_map = dict(zip(sd["Day"], sd["Value After Discounts"]))
    a_first3 = sum(1 for d in first3 if d in rev_map and rev_map[d]>0)
    a_last3 = sum(1 for d in last3 if d in rev_map and rev_map[d]>0)
    if gap == 0: status = "نشط"
    elif gap == 1: status = "توقف مؤخراً"
    elif gap <= 3: status = "توقف 2-3 أيام"
    else: status = "توقف فترة"
    warn = a_first3 >= 2 and a_last3 == 0
    daily = [round(rev_map.get(d, 0)) for d in all_days_full]
    return {"first":first,"last":last,"gap":gap,"status":status,"warn":warn,"daily":daily}

stats_list = []
for _, row in seller_summary.iterrows():
    st_data = seller_stats(row["Seller"])
    if st_data:
        stats_list.append({**row.to_dict(), **st_data})

stats_df = pd.DataFrame(stats_list)

# Metrics
n_active  = (stats_df["status"]=="نشط").sum()
n_recent  = (stats_df["status"]=="توقف مؤخراً").sum()
n_mid     = (stats_df["status"]=="توقف 2-3 أيام").sum()
n_long    = (stats_df["status"]=="توقف فترة").sum()
n_warn    = stats_df["warn"].sum()

c1,c2,c3,c4,c5 = st.columns(5)
with c1: st.markdown(f'<div class="metric-card" style="border-left:4px solid #2a9e75"><p class="metric-label">نشط</p><p class="metric-value" style="color:#2a9e75">{n_active}</p></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="metric-card" style="border-left:4px solid #ba7517"><p class="metric-label">توقف مؤخراً</p><p class="metric-value" style="color:#ba7517">{n_recent}</p></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="metric-card" style="border-left:4px solid #d85a30"><p class="metric-label">توقف 2-3 أيام</p><p class="metric-value" style="color:#d85a30">{n_mid}</p></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="metric-card" style="border-left:4px solid #7f77dd"><p class="metric-label">توقف فترة</p><p class="metric-value" style="color:#7f77dd">{n_long}</p></div>', unsafe_allow_html=True)
with c5: st.markdown(f'<div class="metric-card" style="border-left:4px solid #e24b4a"><p class="metric-label">⚠️ تنبيه مخزون</p><p class="metric-value" style="color:#e24b4a">{n_warn}</p></div>', unsafe_allow_html=True)

# Heatmap HTML helper
def make_heatmap(daily, days):
    mx = max(daily) if max(daily)>0 else 1
    colors = ["#b5d4f4","#85b7eb","#378add","#185fa5","#3266ad"]
    cells = ""
    for v,d in zip(daily,days):
        if v==0:
            cells += f'<span title="{d}: 0 ج" style="display:inline-block;width:14px;height:14px;border-radius:2px;background:#e0e0e0;margin:1px"></span>'
        else:
            idx = min(int(v/mx*4), 4)
            cells += f'<span title="{d}: {v:,.0f} ج" style="display:inline-block;width:14px;height:14px;border-radius:2px;background:{colors[idx]};margin:1px"></span>'
    return cells

status_colors = {"نشط":"#2a9e75","توقف مؤخراً":"#ba7517","توقف 2-3 أيام":"#d85a30","توقف فترة":"#7f77dd"}
status_bg     = {"نشط":"#e1f5ee","توقف مؤخراً":"#faeeda","توقف 2-3 أيام":"#fcebeb","توقف فترة":"#eeedfe"}

# Warning sellers table
st.markdown("**⚠️ Sellers كانوا نشطين وتوقفوا فجأة — محتمل نفاد مخزون**")
warn_df = stats_df[stats_df["warn"]==True].sort_values("total_revenue", ascending=False)
if not warn_df.empty:
    warn_html = '<table style="width:100%;border-collapse:collapse;font-size:12px">'
    warn_html += '<tr style="border-bottom:1px solid #eee"><th style="text-align:left;padding:6px 8px;color:#888;font-size:11px">Seller</th><th style="text-align:right;padding:6px 8px;color:#888;font-size:11px">المبيعات</th><th style="padding:6px 8px;color:#888;font-size:11px">أول بيع</th><th style="padding:6px 8px;color:#888;font-size:11px">آخر بيع</th><th style="text-align:right;padding:6px 8px;color:#888;font-size:11px">أيام توقف</th><th style="padding:6px 8px;color:#888;font-size:11px">الحالة</th><th style="padding:6px 8px;color:#888;font-size:11px">نشاط الأيام</th></tr>'
    for _, r in warn_df.head(20).iterrows():
        sc = status_colors.get(r["status"],"#888")
        sb = status_bg.get(r["status"],"#f5f5f5")
        hm = make_heatmap(r["daily"], all_days_full)
        warn_html += f'<tr style="border-bottom:.5px solid #f0f0f0"><td style="padding:5px 8px;font-weight:500">⚠️ {r["Seller"]}</td><td style="text-align:right;padding:5px 8px">{r["total_revenue"]:,.0f}</td><td style="padding:5px 8px">{r["first"]}</td><td style="padding:5px 8px">{r["last"]}</td><td style="text-align:right;padding:5px 8px;color:#d85a30;font-weight:500">{r["gap"]}</td><td style="padding:5px 8px"><span style="background:{sb};color:{sc};font-size:10px;padding:2px 7px;border-radius:8px;font-weight:500">{r["status"]}</span></td><td style="padding:5px 8px">{hm}</td></tr>'
    warn_html += '</table>'
    st.markdown(warn_html, unsafe_allow_html=True)

# Full sellers table with filters
st.markdown("**كل الـ Sellers**")
# Add category column to stats_df
cat_by_seller = df_mp2.groupby("Seller")["Attribute Set"].agg(lambda x: x.value_counts().index[0] if len(x)>0 else "").reset_index()
cat_by_seller.columns = ["Seller","top_category"]
if "top_category" not in stats_df.columns:
    stats_df = stats_df.merge(cat_by_seller, on="Seller", how="left")
    stats_df["top_category"] = stats_df["top_category"].fillna("")

col_sf1, col_sf2, col_sf3 = st.columns([2,2,1])
with col_sf1:
    seller_search = st.text_input("ابحث باسم seller", placeholder="مثال: goldena", label_visibility="collapsed")
with col_sf2:
    all_cats_sel = ["كل الأقسام"] + sorted(stats_df["top_category"].unique().tolist())
    cat_filter = st.selectbox("فلتر بالقسم", all_cats_sel, label_visibility="collapsed", key="sel_cat")
with col_sf3:
    status_filter = st.selectbox("الحالة", ["كل الحالات","نشط","توقف مؤخراً","توقف 2-3 أيام","توقف فترة"], label_visibility="collapsed")

disp = stats_df.copy()
if cat_filter != "كل الأقسام":
    disp = disp[disp["top_category"]==cat_filter]
if seller_search:
    disp = disp[disp["Seller"].str.lower().str.contains(seller_search.lower())]
if status_filter != "كل الحالات":
    disp = disp[disp["status"]==status_filter]

st.caption(f"عرض {len(disp)} من {len(stats_df)} seller")

table_html = '<table style="width:100%;border-collapse:collapse;font-size:12px">'
table_html += '<tr style="border-bottom:1px solid #eee"><th style="text-align:left;padding:6px 8px;color:#888;font-size:11px">#</th><th style="text-align:left;padding:6px 8px;color:#888;font-size:11px">Seller</th><th style="text-align:left;padding:6px 8px;color:#888;font-size:11px">القسم</th><th style="text-align:right;padding:6px 8px;color:#888;font-size:11px">المبيعات (ج)</th><th style="text-align:right;padding:6px 8px;color:#888;font-size:11px">الكمية</th><th style="text-align:right;padding:6px 8px;color:#888;font-size:11px">الأوردرات</th><th style="padding:6px 8px;color:#888;font-size:11px">آخر بيع</th><th style="text-align:right;padding:6px 8px;color:#888;font-size:11px">أيام توقف</th><th style="padding:6px 8px;color:#888;font-size:11px">الحالة</th><th style="padding:6px 8px;color:#888;font-size:11px">نشاط الأيام</th></tr>'
for i, r in enumerate(disp.itertuples(), 1):
    sc = status_colors.get(r.status, "#888")
    sb = status_bg.get(r.status, "#f5f5f5")
    hm = make_heatmap(r.daily, all_days_full)
    gap_color = "#d85a30" if r.gap>3 else "#ba7517" if r.gap>0 else "#2a9e75"
    warn_icon = " ⚠️" if r.warn else ""
    cat_badge = f'<span style="font-size:10px;background:#e6f1fb;color:#0c447c;padding:1px 5px;border-radius:4px">{r.top_category}</span>' if hasattr(r, "top_category") and r.top_category else ""
    table_html += f'<tr style="border-bottom:.5px solid #f5f5f5"><td style="padding:5px 8px;color:#aaa">{i}</td><td style="padding:5px 8px;font-weight:500">{r.Seller}{warn_icon}</td><td style="padding:5px 8px">{cat_badge}</td><td style="text-align:right;padding:5px 8px">{r.total_revenue:,.0f}</td><td style="text-align:right;padding:5px 8px">{int(r.total_qty):,}</td><td style="text-align:right;padding:5px 8px">{int(r.orders):,}</td><td style="padding:5px 8px">{r.last}</td><td style="text-align:right;padding:5px 8px;color:{gap_color};font-weight:500">{r.gap}</td><td style="padding:5px 8px"><span style="background:{sb};color:{sc};font-size:10px;padding:2px 7px;border-radius:8px;font-weight:500">{r.status}</span></td><td style="padding:5px 8px">{hm}</td></tr>'
table_html += '</table>'
st.markdown(table_html, unsafe_allow_html=True)

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

region_disp = region_df.copy()
region_disp["revenue_fmt"] = region_disp["revenue"].apply(lambda v: f"{v:,.0f}")
region_disp["aov_fmt"]     = region_disp["aov"].apply(lambda v: f"{v:,.0f}")
region_disp["pct_fmt"]     = region_disp["pct"].astype(str)+"%"
region_disp.index = range(1, len(region_disp)+1)
st.dataframe(
    region_disp[["Region","revenue_fmt","orders","items","aov_fmt","pct_fmt"]].rename(
        columns={"Region":"المحافظة","revenue_fmt":"المبيعات (ج)","orders":"الأوردرات","items":"القطع","aov_fmt":"AOV (ج)","pct_fmt":"النسبة"}
    ), use_container_width=True
)

# ── PAYMENT METHOD ─────────────────────────────────────────────────────────────
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

pay_disp = pay_df.copy()
pay_disp["revenue_fmt"] = pay_disp["revenue"].apply(lambda v: f"{v:,.0f}")
pay_disp["aov_fmt"]     = pay_disp["aov"].apply(lambda v: f"{v:,.0f}")
pay_disp["pct_fmt"]     = pay_disp["pct"].astype(str)+"%"
pay_disp.index = range(1, len(pay_disp)+1)
st.dataframe(
    pay_disp[["Payment Method","revenue_fmt","orders","aov_fmt","pct_fmt"]].rename(
        columns={"Payment Method":"طريقة الدفع","revenue_fmt":"المبيعات (ج)","orders":"الأوردرات","aov_fmt":"AOV (ج)","pct_fmt":"النسبة"}
    ), use_container_width=True
)

st.markdown("---")
st.markdown(f"<p style='text-align:center;color:#aaa;font-size:11px'>Raneen Analytics · {date_min} → {date_max}</p>", unsafe_allow_html=True)
