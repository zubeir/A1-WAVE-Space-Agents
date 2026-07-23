import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

# ---------------------------------------------------------
# 1. CONFIGURATION & BASKET SETUP
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
    page_title="Space Sector Decision & Execution Engine", layout="wide"
)
st.title("🚀 A1-WAVE : Space Sector Momentum & Execution Engine")
st.caption(
    "Daily Technical Filter, Relative Strength vs. Sector ETFs, Volume Accumulation & ATR Risk Engine"
)


# ---------------------------------------------------------
# 2. HELPER CALCULATIONS (RSI & ATR)
# ---------------------------------------------------------
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_atr(df_high, df_low, df_close, period=14):
    tr1 = df_high - df_low
    tr2 = (df_high - df_close.shift(1)).abs()
    tr3 = (df_low - df_close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


# ---------------------------------------------------------
# 3. DATA FETCHING
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_market_data(tickers, benchmark_tickers):
    all_tickers = list(set(tickers + list(benchmark_tickers.keys())))
    data = yf.download(all_tickers, period="1y", interval="1d", progress=False)
    return data


data = fetch_market_data(SPACE_BASKET, BENCHMARKS)

# ---------------------------------------------------------
# 4. BENCHMARK HEALTH BANNER
# ---------------------------------------------------------
st.subheader("🌐 Sector Benchmark Macro Health")


def analyze_benchmark(symbol, df_close):
    series = df_close[symbol].dropna()
    current = series.iloc[-1]
    sma_50 = series.rolling(50).mean().iloc[-1]
    sma_200 = series.rolling(200).mean().iloc[-1]
    ret_3m = ((current - series.iloc[-63]) / series.iloc[-63]) * 100

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
        "vs 50-SMA": f"{round(((current - sma_50)/sma_50)*100, 2)}%",
        "3M Return": round(ret_3m, 2),
    }


etf_cols = st.columns(3)
etf_returns = {}

for idx, (symbol, name) in enumerate(BENCHMARKS.items()):
    metrics = analyze_benchmark(symbol, data["Close"])
    etf_returns[symbol] = metrics["3M Return"]

    with etf_cols[idx]:
        st.metric(
            label=f"{symbol} ({name})",
            value=f"${metrics['Price']} | {metrics['Status']}",
            delta=f"3M Return: {metrics['3M Return']}% (vs 50-SMA: {metrics['vs 50-SMA']})",
        )

st.divider()


# ---------------------------------------------------------
# 5. ENHANCED STOCK ANALYSIS ENGINE
# ---------------------------------------------------------
def analyze_space_stock(ticker, df_data, etf_rets):
    df_close = df_data["Close"][ticker].dropna()
    df_high = df_data["High"][ticker].dropna()
    df_low = df_data["Low"][ticker].dropna()
    df_vol = df_data["Volume"][ticker].dropna()

    current_price = df_close.iloc[-1]

    # Moving Averages
    sma_50 = df_close.rolling(50).mean().iloc[-1]
    sma_200 = df_close.rolling(200).mean().iloc[-1]

    # Proximity metrics
    dist_50_pct = ((current_price - sma_50) / sma_50) * 100
    dist_200_pct = ((current_price - sma_200) / sma_200) * 100

    # Phase 1 Evaluation (Price > 50-SMA AND Price > 200-SMA AND 50-SMA > 200-SMA)
    above_50 = current_price > sma_50
    above_200 = current_price > sma_200
    golden_cross = sma_50 > sma_200

    if above_50 and above_200 and golden_cross:
        phase1 = "PASS 🟢"
    elif above_200 and not above_50:
        phase1 = "NEUTRAL 🟡"
    else:
        phase1 = "FAIL 🔴"

    # Volume Surge (vs 20-Day Avg Volume)
    avg_vol_20 = df_vol.rolling(20).mean().iloc[-1]
    curr_vol = df_vol.iloc[-1]
    vol_ratio = (
        (curr_vol / avg_vol_20) * 100 if avg_vol_20 > 0 else 100
    )  # % of 20D Avg

    # RSI Calculation
    rsi_series = calculate_rsi(df_close)
    rsi_val = rsi_series.iloc[-1]

    # ATR & Risk Calculations
    atr_series = calculate_atr(df_high, df_low, df_close)
    atr_val = atr_series.iloc[-1]
    stop_loss_suggested = current_price - (2 * atr_val)

    # 3-Month Performance & Relative Alpha
    ret_3m = ((current_price - df_close.iloc[-63]) / df_close.iloc[-63]) * 100
    alpha_arkx = ret_3m - etf_rets.get("ARKX", 0)
    alpha_ita = ret_3m - etf_rets.get("ITA", 0)
    alpha_spy = ret_3m - etf_rets.get("SPY", 0)

    # ACTIONABLE ENTRY SIGNAL DECISION ENGINE
    if phase1 == "PASS 🟢":
        if rsi_val > 70:
            signal = "EXTENDED (Wait for Dip) ⚠️"
        elif dist_50_pct <= 4.0 and vol_ratio >= 110:
            signal = "BUY - PRIME ENTRY ⚡"
        elif dist_50_pct <= 6.0:
            signal = "BUY - NEAR SUPPORT 🎯"
        else:
            signal = "HOLD / TRAIL STOP 🛡️"
    elif phase1 == "NEUTRAL 🟡":
        signal = "CONSOLIDATING ⏳"
    else:
        signal = "NO TRADE ❌"

    return {
        "Ticker": ticker,
        "Action Signal": signal,
        "Phase 1": phase1,
        "Price ($)": round(current_price, 2),
        "50-SMA ($)": round(sma_50, 2),
        "Dist to 50-SMA (%)": round(dist_50_pct, 2),
        "Vol vs 20D Avg (%)": round(vol_ratio, 1),
        "RSI (14)": round(rsi_val, 1),
        "ATR 14 ($)": round(atr_val, 2),
        "Stop Loss ($)": round(stop_loss_suggested, 2),
        "3M Return (%)": round(ret_3m, 2),
        "vs ARKX Alpha (%)": round(alpha_arkx, 2),
        "vs ITA Alpha (%)": round(alpha_ita, 2),
    }


# Run analysis for all stocks
stock_results = []
for ticker in SPACE_BASKET:
    try:
        stock_results.append(
            analyze_space_stock(ticker, data, etf_returns)
        )
    except Exception:
        continue

df_stocks = pd.DataFrame(stock_results)

# ---------------------------------------------------------
# 6. ACTIONABLE ENTRY SIGNALS
# ---------------------------------------------------------
st.subheader("⚡ High-Conviction Tranche Entry Signals")

prime_entries = df_stocks[
    df_stocks["Action Signal"].isin(
        ["BUY - PRIME ENTRY ⚡", "BUY - NEAR SUPPORT 🎯"]
    )
]

if not prime_entries.empty:
    st.success(
        f"**BUY SIGNALS CONFIRMED:** {len(prime_entries)} stock(s) pass Phase 1 and are sitting in low-risk entry zones:"
    )
    st.dataframe(prime_entries, use_container_width=True)
else:
    st.info(
        "**NO IMMEDIATE ENTRY SIGNALS:** No stocks currently meet the combined Phase 1 + Volume + Support proximity criteria. Keep capital in cash reserve."
    )

st.divider()

# ---------------------------------------------------------
# 7. FULL MATRIX WITH DECISION FILTERS
# ---------------------------------------------------------
st.subheader("📊 Full Basket Decision Matrix")

col_f1, col_f2 = st.columns(2)
with col_f1:
    signal_filter = st.selectbox(
        "Filter by Action Signal:",
        [
            "All Signals",
            "BUY SIGNALS ONLY",
            "Phase 1 Passes Only",
            "CONSOLIDATING",
            "NO TRADE",
        ],
    )

if signal_filter == "BUY SIGNALS ONLY":
    filtered_df = df_stocks[df_stocks["Action Signal"].str.contains("BUY")]
elif signal_filter == "Phase 1 Passes Only":
    filtered_df = df_stocks[df_stocks["Phase 1"] == "PASS 🟢"]
elif signal_filter == "CONSOLIDATING":
    filtered_df = df_stocks[df_stocks["Phase 1"] == "NEUTRAL 🟡"]
elif signal_filter == "NO TRADE":
    filtered_df = df_stocks[df_stocks["Phase 1"] == "FAIL 🔴"]
else:
    filtered_df = df_stocks

st.dataframe(filtered_df, use_container_width=True)