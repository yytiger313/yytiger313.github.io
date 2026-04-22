import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="股東紀念品股票分析", page_icon="📊", layout="wide")

@st.cache_data
def load_data():
    revenue_2024 = pd.read_excel("分年分營收.xlsx", sheet_name="2024")
    revenue_2025 = pd.read_excel("分年分營收.xlsx", sheet_name="2025")

    sh_raw_2024 = pd.read_excel("股東完成版.xlsx", sheet_name="2024", header=None)
    sh_raw_2025 = pd.read_excel("股東完成版.xlsx", sheet_name="2025", header=None)

    price_raw_2024 = pd.read_excel("股票收盤價.xlsx", sheet_name="2024", header=None)
    price_raw_2025 = pd.read_excel("股票收盤價.xlsx", sheet_name="2025", header=None)

    gift_2024 = pd.read_excel("股東紀念品清單.xlsx", sheet_name="2024")
    gift_2025 = pd.read_excel("股東紀念品清單.xlsx", sheet_name="2025")

    return {
        "revenue": {"2024": revenue_2024, "2025": revenue_2025},
        "shareholders_raw": {"2024": sh_raw_2024, "2025": sh_raw_2025},
        "price_raw": {"2024": price_raw_2024, "2025": price_raw_2025},
        "gift": {"2024": gift_2024, "2025": gift_2025},
    }

def parse_wide_table(raw_df):
    stock_codes = raw_df.iloc[0, 1:].astype(str).tolist()
    stock_names = raw_df.iloc[1, 1:].astype(str).tolist()
    code_to_name = {c: n for c, n in zip(stock_codes, stock_names)}

    data_rows = raw_df.iloc[2:].copy()
    dates = pd.to_datetime(data_rows.iloc[:, 0], errors='coerce')
    data_rows = data_rows.iloc[:, 1:]
    data_rows.columns = stock_codes
    data_rows.index = dates
    data_rows = data_rows.apply(pd.to_numeric, errors='coerce')

    return data_rows, code_to_name

def get_stock_list(data):
    gift_2024 = data["gift"]["2024"]
    gift_2025 = data["gift"]["2025"]

    all_stocks = {}

    for _, row in gift_2024.iterrows():
        code = str(row["股票代號"]).strip()
        name = str(row["股票名稱"]).strip()
        all_stocks[code] = name

    for _, row in gift_2025.iterrows():
        code = str(row["股票代號"]).strip()
        name = str(row["股票名稱"]).strip()
        if code not in all_stocks:
            all_stocks[code] = name

    return all_stocks

def get_multi_record_codes(data):
    multi = set()
    for year in ["2024", "2025"]:
        gift = data["gift"][year]
        counts = gift.groupby("股票代號").size()
        multi_year = counts[counts >= 2].index.astype(str).tolist()
        multi.update(multi_year)
    return multi

def get_gift_info(data, code, year):
    gift = data["gift"][year]
    rows = gift[gift["股票代號"].astype(str) == str(code)]
    return rows

def get_last_buy_dates(data, code, year):
    rows = get_gift_info(data, code, year)
    if rows.empty:
        return []
    dates = pd.to_datetime(rows["最後買進日"], errors='coerce').dropna().tolist()
    return dates

def make_revenue_chart(data, code, year):
    rev = data["revenue"][year]
    row = rev[rev["股號"].astype(str) == str(code)]
    if row.empty:
        return None
    months = list(range(1, 13))
    values = [row.iloc[0].get(m, None) for m in months]
    name = row.iloc[0]["股名"]
    valid = [(m, v) for m, v in zip(months, values) if pd.notna(v) and v > 0]
    if not valid:
        return None
    x_months, y_vals = zip(*valid)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[f"{m}月" for m in x_months],
        y=y_vals,
        marker_color="#4A90D9",
        name="月營收",
    ))
    fig.update_layout(
        title=f"{name} ({code}) {year}年月營收",
        xaxis_title="月份",
        yaxis_title="營收 (元)",
        height=350,
        margin=dict(t=50, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig

def make_shareholder_chart(data, code, year, last_buy_dates):
    sh_df, code_to_name = parse_wide_table(data["shareholders_raw"][year])
    str_code = str(code)
    if str_code not in sh_df.columns:
        return None
    series = sh_df[str_code].dropna()
    if series.empty:
        return None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=series.index, y=series.values,
        mode="lines+markers",
        line=dict(color="#2ECC71", width=2),
        marker=dict(size=4),
        name="股東人數",
    ))
    for d in last_buy_dates:
        if series.index.empty:
            continue
        closest_idx = np.abs(series.index - d).argmin()
        closest_date = series.index[closest_idx]
        closest_val = series.iloc[closest_idx]
        fig.add_trace(go.Scatter(
            x=[closest_date], y=[closest_val],
            mode="markers+text",
            marker=dict(size=14, color="#E74C3C", symbol="star"),
            text=["最後買進日"],
            textposition="top center",
            name=f"最後買進日 {d.strftime('%Y-%m-%d')}",
            showlegend=True,
        ))

    name = code_to_name.get(str_code, code)
    fig.update_layout(
        title=f"{name} ({code}) {year}年股東人數",
        xaxis_title="日期",
        yaxis_title="股東人數",
        height=350,
        margin=dict(t=50, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig

def make_price_chart(data, code, year, last_buy_dates):
    pr_df, code_to_name = parse_wide_table(data["price_raw"][year])
    str_code = str(code)
    if str_code not in pr_df.columns:
        return None
    series = pr_df[str_code].dropna()
    series = series[series > 0]
    if series.empty:
        return None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=series.index, y=series.values,
        mode="lines",
        line=dict(color="#9B59B6", width=2),
        name="收盤價",
    ))
    for d in last_buy_dates:
        if series.index.empty:
            continue
        closest_idx = np.abs(series.index - d).argmin()
        closest_date = series.index[closest_idx]
        closest_val = series.iloc[closest_idx]
        fig.add_trace(go.Scatter(
            x=[closest_date], y=[closest_val],
            mode="markers+text",
            marker=dict(size=14, color="#E74C3C", symbol="star"),
            text=["最後買進日"],
            textposition="top center",
            name=f"最後買進日 {d.strftime('%Y-%m-%d')}",
            showlegend=True,
        ))

    name = code_to_name.get(str_code, code)
    fig.update_layout(
        title=f"{name} ({code}) {year}年股價走勢",
        xaxis_title="日期",
        yaxis_title="收盤價 (元)",
        height=350,
        margin=dict(t=50, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig

# ---- Main App ----
st.markdown("""
<style>
.big-title { font-size: 2rem; font-weight: bold; color: #2C3E50; }

/* ── Info cards ── */
.info-card {
    background: #F8F9FA;
    border-radius: 10px;
    padding: 10px 14px;
    border-left: 4px solid #4A90D9;
    height: 100%;
    box-sizing: border-box;
}
.info-card .ic-label {
    font-size: 0.67rem;
    color: #999;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 4px;
}
.info-card .ic-code {
    font-size: 0.78rem;
    color: #666;
    font-weight: 500;
    line-height: 1.4;
}
.info-card .ic-name {
    font-size: 1.05rem;
    font-weight: 700;
    color: #1a252f;
    line-height: 1.3;
}
.info-card .ic-value {
    font-size: 0.84rem;
    font-weight: 500;
    color: #2C3E50;
    word-break: break-word;
    white-space: pre-line;
    line-height: 1.6;
}

/* ── Last-buy-date panel ── */
.buy-panel {
    background: #FFFBF0;
    border-radius: 10px;
    padding: 12px 14px;
    border-left: 4px solid #F39C12;
    box-sizing: border-box;
}
.buy-panel .bp-label {
    font-size: 0.67rem;
    color: #B7770D;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 8px;
}
.buy-panel .bp-date {
    font-size: 0.92rem;
    font-weight: 600;
    color: #7B3F00;
    margin-bottom: 5px;
}

.badge-multi {
    background: #E74C3C;
    color: white;
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 0.68rem;
    font-weight: bold;
    margin-left: 5px;
    vertical-align: middle;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">📊 股東紀念品股票分析平台</div>', unsafe_allow_html=True)
st.markdown("---")

with st.spinner("載入資料中..."):
    data = load_data()

all_stocks = get_stock_list(data)
multi_codes = get_multi_record_codes(data)

# Top controls
col_select, col_year, col_filter = st.columns([3, 1, 1])

with col_filter:
    show_multi_only = st.checkbox("僅顯示發放兩次以上", value=False)

if show_multi_only:
    filtered_stocks = {k: v for k, v in all_stocks.items() if k in multi_codes}
else:
    filtered_stocks = all_stocks

options = [f"{k} - {v}" for k, v in sorted(filtered_stocks.items(), key=lambda x: x[0])]

with col_select:
    selected_option = st.selectbox("選擇股票", options, key="stock_select")

with col_year:
    year = st.radio("年份", ["2024", "2025"], horizontal=True)

if selected_option:
    selected_code = selected_option.split(" - ")[0].strip()
    selected_name = all_stocks.get(selected_code, "")
    is_multi = selected_code in multi_codes

    gift_rows = get_gift_info(data, selected_code, year)
    last_buy_dates = get_last_buy_dates(data, selected_code, year)

    st.markdown("---")

    # ── Info row: 代號名稱(窄) | 紀念品類別 | 股東紀念品(寬) ──────────
    info_c1, info_c2, info_c3 = st.columns([1, 1.3, 2.4])

    with info_c1:
        multi_badge = '<span class="badge-multi">2次以上</span>' if is_multi else ""
        st.markdown(f"""
        <div class="info-card">
            <div class="ic-label">股票代號 / 名稱</div>
            <div class="ic-code">{selected_code}{multi_badge}</div>
            <div class="ic-name">{selected_name}</div>
        </div>
        """, unsafe_allow_html=True)

    with info_c2:
        if not gift_rows.empty:
            cats = gift_rows["紀念品類別名稱"].dropna().tolist()
            cats_str = "\n".join(f"• {c}" for c in cats) if cats else f"—（{year}無資料）"
        else:
            cats_str = f"—（{year}無資料）"
        st.markdown(f"""
        <div class="info-card">
            <div class="ic-label">股東紀念品類別</div>
            <div class="ic-value">{cats_str}</div>
        </div>
        """, unsafe_allow_html=True)

    with info_c3:
        if not gift_rows.empty:
            gifts_list = gift_rows["紀念品"].dropna().tolist()
            batches = gift_rows["發放批次"].tolist() if "發放批次" in gift_rows.columns else [""] * len(gifts_list)
            lines = []
            for g, b in zip(gifts_list, batches):
                batch_str = f"（第{b}批）" if pd.notna(b) and str(b).strip() not in ["", "nan"] else ""
                lines.append(f"• {g}{batch_str}")
            gifts_str = "\n".join(lines) if lines else f"—（{year}無資料）"
        else:
            gifts_str = f"—（{year}無資料）"
        st.markdown(f"""
        <div class="info-card" style="border-left-color:#27AE60;">
            <div class="ic-label">股東紀念品</div>
            <div class="ic-value">{gifts_str}</div>
        </div>
        """, unsafe_allow_html=True)

    if is_multi:
        st.info("⚠️ 此股票在 2024 或 2025 年中，**發放紀念品兩次以上**")

    st.markdown("---")
    st.subheader(f"📈 {selected_name}（{selected_code}）{year}年數據圖表")

    # ── Row 1: 最後買進日(左側面板) + 月營收圖 ──────────────────────
    date_col, rev_col = st.columns([1, 2.5])

    with date_col:
        if last_buy_dates:
            dates_html = "".join(
                f'<div class="bp-date">📅 {d.strftime("%Y-%m-%d")}</div>'
                for d in last_buy_dates
            )
        else:
            dates_html = f'<div style="color:#aaa;font-size:0.85rem;">—（{year}無資料）</div>'
        st.markdown(f"""
        <div class="buy-panel" style="margin-top:6px;">
            <div class="bp-label">📌 最後買進日</div>
            {dates_html}
        </div>
        """, unsafe_allow_html=True)

    with rev_col:
        rev_fig = make_revenue_chart(data, selected_code, year)
        if rev_fig:
            st.plotly_chart(rev_fig, use_container_width=True)
        else:
            st.info(f"⚠️ {year}年無營收資料")

    # ── Row 2: 股東人數 + 股價走勢 ──────────────────────────────────
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        sh_fig = make_shareholder_chart(data, selected_code, year, last_buy_dates)
        if sh_fig:
            st.plotly_chart(sh_fig, use_container_width=True)
        else:
            st.info(f"⚠️ {year}年無股東人數資料")

    with chart_col2:
        pr_fig = make_price_chart(data, selected_code, year, last_buy_dates)
        if pr_fig:
            st.plotly_chart(pr_fig, use_container_width=True)
        else:
            st.info(f"⚠️ {year}年無股價資料")

    # ── Detailed gift table — no index column ───────────────────────
    if not gift_rows.empty:
        st.markdown("---")
        st.subheader(f"📋 {year}年股東紀念品詳細資料")
        display_cols = ["股票代號", "股票名稱", "最後買進日", "股東會日期", "紀念品", "紀念品類別名稱", "發放批次", "平台收購價"]
        available_cols = [c for c in display_cols if c in gift_rows.columns]
        st.dataframe(
            gift_rows[available_cols].reset_index(drop=True).style.hide(axis="index"),
            use_container_width=True,
        )
