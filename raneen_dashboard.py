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

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Raneen Analytics")
    st.markdown("---")
    uploaded = st.file_uploader("ارفع شيت ماجينتو (CSV)", type=["csv"])
    st.markdown("---")
    st.markdown("**كيفية الاستخدام:**")
    st.markdown("1. نزّل الشيت من ماجينتو\n2. ارفعه هنا\n3. الداشبورد بيظهر فوراً")

# ── MAIN ─────────────────────────────────────────────────────────────────────
if uploaded is None:
    st.markdown("## 👈 ارفع الشيت من القايمة الجانبية")
    st.info("بترفع CSV من ماجينتو وبيظهر الداشبورد فوراً")
    st.stop()

df = process(uploaded)
date_min = df["Purchase Date"].dt.date.min()
date_max = df["Purchase Date"].dt.date.max()

total   = df["Value After Discounts"].sum()
raneen  = df[df["Marketplace Seller"]=="raneen"]["Value After Discounts"].sum()
mp      = df[df["Marketplace Seller"]=="MP"]["Value After Discounts"].sum()

days_sorted = sorted(df["Day"].unique(), key=lambda d: pd.to_datetime(d+" 2026"))

# ── HEADER ───────────────────────────────────────────────────────────────────
st.markdown(f"# 📊 Raneen Sales Dashboard")
st.markdown(f"**الفترة:** {date_min} → {date_max}")
st.markdown("---")

# ── METRICS ──────────────────────────────────────────────────────────────────
c1,c2,c3,c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-card"><p class="metric-label">إجمالي المبيعات</p><p class="metric-value">{total/1e6:.2f}M ج</p></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><p class="metric-label">مبيعات Raneen</p><p class="metric-value">{raneen/1e6:.2f}M ج</p><p class="metric-sub">{raneen/total*100:.1f}% من الإجمالي</p></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-card"><p class="metric-label">مبيعات MP</p><p class="metric-value">{mp/1e6:.2f}M ج</p><p class="metric-sub">{mp/total*100:.1f}% من الإجمالي</p></div>', unsafe_allow_html=True)
with c4:
    n_cats = df["Attribute Set"].nunique()
    st.markdown(f'<div class="metric-card"><p class="metric-label">عدد الأقسام</p><p class="metric-value">{n_cats}</p></div>', unsafe_allow_html=True)

# ── RANEEN VS MP ──────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">Raneen vs MP</p>', unsafe_allow_html=True)
col_l, col_r = st.columns([1,2])

with col_l:
    fig_donut = go.Figure(go.Pie(
        labels=["Raneen","MP"], values=[raneen,mp],
        hole=.65, marker_colors=["#3266ad","#d85a30"],
        textinfo="label+percent", hovertemplate="%{label}: %{value:,.0f} ج<extra></extra>"
    ))
    fig_donut.update_layout(margin=dict(t=20,b=20,l=20,r=20), height=260,
        showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_donut, use_container_width=True)

with col_r:
    ch_df = df.groupby("Marketplace Seller")["Value After Discounts"].sum().reset_index()
    fig_bar = px.bar(ch_df, x="Marketplace Seller", y="Value After Discounts",
        color="Marketplace Seller", color_discrete_map=COLORS,
        text_auto=".3s")
    fig_bar.update_layout(showlegend=False, margin=dict(t=20,b=20,l=10,r=10),
        height=260, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="", yaxis_title="")
    fig_bar.update_traces(textposition="outside")
    st.plotly_chart(fig_bar, use_container_width=True)

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

# ── DAILY ─────────────────────────────────────────────────────────────────────
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

# ── PRICE CHANGES ─────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">المنتجات التي تغير سعرها أكثر من 3 مرات</p>', unsafe_allow_html=True)

pc = get_price_changes(df)
if not pc.empty:
    cats_available = ["الكل"] + sorted(pc["Category"].str.replace("&amp;","&").unique().tolist())
    selected_cat = st.selectbox("فلتر بالقسم", cats_available)
    if selected_cat != "الكل":
        pc_show = pc[pc["Category"].str.replace("&amp;","&")==selected_cat]
    else:
        pc_show = pc
    pc_show = pc_show.sort_values(["# Changes","SKU"], ascending=[False,True])
    pc_show["Change"] = pc_show["Change"].apply(lambda v: f"+{v:,.0f}" if v>0 else f"{v:,.0f}")
    st.dataframe(pc_show[["Category","SKU","Product","Date","Price Before","Price After","Change","# Changes"]].rename(
        columns={"Category":"القسم","Product":"المنتج","Date":"التاريخ",
                 "Price Before":"قبل","Price After":"بعد","Change":"الفرق","# Changes":"# تغييرات"}
    ), use_container_width=True, hide_index=True)
else:
    st.info("لا توجد منتجات بأكثر من 3 تغييرات في السعر")

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

st.markdown("---")
st.markdown(f"<p style='text-align:center;color:#aaa;font-size:11px'>Raneen Analytics · {date_min} → {date_max}</p>", unsafe_allow_html=True)
