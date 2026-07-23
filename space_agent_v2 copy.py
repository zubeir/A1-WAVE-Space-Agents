import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

# ---------------------------------------------------------
# 1. CONFIGURATION & BENCHMARKS
# ---------------------------------------------------------
BENCHMARKS = {
    "ARKX": "ARK Space Innovation ETF",
    "ITA": "iShares US Aerospace & Defense ETF",
    "SPY": "S&P 500 Index",
}

SPACE_BASKET = [
    "BA",
    "NOC",
    "PL",
    "LMT",
    "RTX",
    "LDOS",
    "VLD",
    "MOG-A",
    "IRDM",
    "RKLB",
    "RDW",
    "HEI",
    "SATL",
    "KTOS",
    "SPIR",
    "ASTR",
    "LUNR",
    "ASTS",
    "GSAT",
    "VSAT",
    "MNTS",
    "BKSY",
    "LLAP",
    "SIDU",
    "SPCE",
]

st.set_page_config(
    page_title="Space Sector & ETF Momentum Agent", layout="wide"
)
st.title("🚀 Space Sector Momentum Agent & ETF Benchmark Matrix")
st.caption("Daily Stock Analysis vs. Sector ETFs (ARKX, ITA) & S&P 500 (SPY)")


# ---------------------------------------------------------
# 2. DATA PROCESSING ENGINE
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_data(tickers, benchmark_tickers):
    all_tickers = list(set(tickers + list(benchmark_tickers.keys())))
    data = yf.download(all_tickers, period="1y", interval="1d", progress=False)[
        "Close"
    ]
    return data


data = fetch_data(SPACE_BASKET, BENCHMARKS)

# ---------------------------------------------------------
# 3. SECTOR & ETF HEALTH MONITOR
# ---------------------------------------------------------
st.subheader("🌐 Sector & Benchmark Macro Health")


def get_etf_status(df_series):
    current = df_series.iloc[-1]
    sma_50 = df_series.rolling(50).mean().iloc[-1]
    sma_200 = df_series.rolling(200).mean().iloc[-1]

    # Calculate 3-month return
    three_month_ret = (
        (current - df_series.iloc[-63]) / df_series.iloc[-63]
    ) * 100

    above_50 = current > sma_50
    above_200 = current > sma_200

    if above_50 and above_200:
        status = "BULLISH 🟢"
    elif above_200 and not above_50:
        status = "NEUTRAL / COOLING 🟡"
    else:
        status = "BEARISH 🔴"

    return {
        "Price": round(current, 2),
        "Status": status,
        "vs 50-SMA": f"{round(((current - sma_50) / sma_50) * 100, 2)}%",
        "3M Return": round(three_month_ret, 2),
    }


etf_cols = st.columns(3)
etf_perf = {}

for idx, (symbol, name) in enumerate(BENCHMARKS.items()):
    metrics = get_etf_status(data[symbol].dropna())
    etf_perf[symbol] = metrics["3M Return"]

    with etf_cols[idx]:
        st.metric(
            label=f"{symbol} ({name})",
            value=f"${metrics['Price']} | {metrics['Status']}",
            delta=f"3M Return: {metrics['3M Return']}% (vs 50-SMA: {metrics['vs 50-SMA']})",
        )

st.divider()


# ---------------------------------------------------------
# 4. STOCK MATRIX VS ETF BENCHMARKS
# ---------------------------------------------------------
def analyze_stocks(tickers, df_all, etf_returns):
    results = []

    for ticker in tickers:
        try:
            df = df_all[ticker].dropna()
            current_price = df.iloc[-1]

            # Moving Averages
            sma_50 = df.rolling(50).mean().iloc[-1]
            sma_200 = df.rolling(200).mean().iloc[-1]

            # 3-Month Performance
            ret_3m = ((current_price - df.iloc[-63]) / df.iloc[-63]) * 100

            # Relative Strength vs ETFs
            alpha_arkx = ret_3m - etf_returns.get("ARKX", 0)
            alpha_ita = ret_3m - etf_returns.get("ITA", 0)
            alpha_spy = ret_3m - etf_returns.get("SPY", 0)

            # Phase 1 Evaluation
            above_50 = current_price > sma_50
            above_200 = current_price > sma_200
            golden_cross = sma_50 > sma_200

            if above_50 and above_200 and golden_cross:
                phase1 = "PASS 🟢"
            elif above_200 and not above_50:
                phase1 = "NEUTRAL 🟡"
            else:
                phase1 = "FAIL 🔴"

            # Sector Strength Rating
            beats_sector = alpha_arkx > 0 and alpha_ita > 0
            beats_market = alpha_spy > 0

            if beats_sector and beats_market:
                sec_strength = "LEADER 🔥"
            elif beats_sector:
                sec_strength = "OUTPERFORMING SECTOR 📈"
            else:
                sec_strength = "LAGGARD ❄️"

            results.append(
                {
                    "Ticker": ticker,
                    "Phase 1 Status": phase1,
                    "Sector Strength": sec_strength,
                    "Price ($)": round(current_price, 2),
                    "50-SMA ($)": round(sma_50, 2),
                    "3M Return (%)": round(ret_3m, 2),
                    "vs ARKX Alpha (%)": round(alpha_arkx, 2),
                    "vs ITA Alpha (%)": round(alpha_ita, 2),
                    "vs SPY Alpha (%)": round(alpha_spy, 2),
                }
            )
        except Exception:
            continue

    return pd.DataFrame(results)


df_matrix = analyze_stocks(SPACE_BASKET, data, etf_perf)

# ---------------------------------------------------------
# 5. ACTIONABLE BUY SIGNALS & RELATIVE LEADERS
# ---------------------------------------------------------
st.subheader("🎯 Actionable Tranche Candidates")

# Filter for stocks that pass Phase 1 AND beat the sector ETF
ideal_buys = df_matrix[
    (df_matrix["Phase 1 Status"] == "PASS 🟢")
    & (df_matrix["Sector Strength"] == "LEADER 🔥")
]

if not ideal_buys.empty:
    st.success(
        f"**STRONG CONVICTION SIGNALS:** {len(ideal_buys)} stock(s) pass Phase 1 AND show Alpha over both ETFs:"
    )
    st.dataframe(ideal_buys, use_container_width=True)
else:
    st.info(
        "**NO CONVICTION SIGNALS:** No individual stocks currently pass Phase 1 while outperforming both ETFs. Keep capital in cash reserve."
    )

st.divider()

# ---------------------------------------------------------
# 6. FULL RELATIVE PERFORMANCE MATRIX
# ---------------------------------------------------------
st.subheader("📊 Full Basket Relative Strength Matrix")

status_filter = st.selectbox(
    "Filter Matrix by Sector Strength:",
    [
        "All Stocks",
        "LEADER 🔥 (Beats ETFs & SPY)",
        "Phase 1 Passes Only",
        "LAGGARDS ❄️",
    ],
)

if status_filter == "LEADER 🔥 (Beats ETFs & SPY)":
    filtered_df = df_matrix[df_matrix["Sector Strength"] == "LEADER 🔥"]
elif status_filter == "Phase 1 Passes Only":
    filtered_df = df_matrix[df_matrix["Phase 1 Status"] == "PASS 🟢"]
elif status_filter == "LAGGARDS ❄️":
    filtered_df = df_matrix[df_matrix["Sector Strength"] == "LAGGARD ❄️"]
else:
    filtered_df = df_matrix

st.dataframe(filtered_df, use_container_width=True)