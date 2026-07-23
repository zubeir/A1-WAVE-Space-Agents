import json
import os
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

# ---------------------------------------------------------
# 1. FILE & WATCHLIST MANAGEMENT (PERSISTENCE)
# ---------------------------------------------------------
WATCHLIST_FILE = "watchlist.json"

DEFAULT_BASKET = [
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

BENCHMARKS = {
    "ARKX": "ARK Space Innovation ETF",
    "ITA": "iShares US Aerospace & Defense ETF",
    "SPY": "S&P 500 Index",
}


def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return [t.upper().strip() for t in data]
        except Exception:
            pass
    # Save default if file doesn't exist
    save_watchlist(DEFAULT_BASKET)
    return DEFAULT_BASKET


def save_watchlist(tickers):
    # Unique tickers while preserving order
    clean_tickers = list(
        dict.fromkeys([t.upper().strip() for t in tickers if t])
    )
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(clean_tickers, f, indent=4)
    return clean_tickers


# Load active watchlist from saved file
active_basket = load_watchlist()

# ---------------------------------------------------------
# 2. STREAMLIT APP CONFIG & SIDEBAR MANAGEMENT
# ---------------------------------------------------------
st.set_page_config(
    page_title="Space Sector Decision & Execution Engine", layout="wide"
)

# Sidebar: File Uploader and Watchlist Controls
st.sidebar.title("⚙️ Watchlist Manager")
st.sidebar.caption(
    f"Currently tracking **{len(active_basket)} tickers** saved in `{WATCHLIST_FILE}`."
)

uploaded_file = st.sidebar.file_uploader(
    "Upload Tickers File (.txt, .csv, .json)", type=["txt", "csv", "json"]
)

if uploaded_file is not None:
    try:
        content = uploaded_file.getvalue().decode("utf-8")
        new_tickers = []

        if uploaded_file.name.endswith(".json"):
            new_tickers = json.loads(content)
        elif uploaded_file.name.endswith(".csv") or uploaded_file.name.endswith(
            ".txt"
        ):
            # Parse commas, newlines, or spaces
            raw_list = content.replace(",", "\n").replace(" ", "\n").split("\n")
            new_tickers = [t.strip() for t in raw_list if t.strip()]

        if new_tickers:
            active_basket = save_watchlist(new_tickers)
            st.sidebar.success(
                f"Saved {len(active_basket)} tickers from file!"
            )
            st.cache_data.clear()
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"Error parsing file: {e}")

# Sidebar Manual Add / Reset
new_symbol = st.sidebar.text_input(
    "Add Single Ticker:", placeholder="e.g. LMT"
).upper()
if st.sidebar.button("Add Ticker"):
    if new_symbol and new_symbol not in active_basket:
        active_basket.append(new_symbol)
        save_watchlist(active_basket)
        st.sidebar.success(f"Added {new_symbol}")
        st.cache_data.clear()
        st.rerun()

if st.sidebar.button("Reset to Default 25 Basket"):
    active_basket = save_watchlist(DEFAULT_BASKET)
    st.sidebar.info("Reset to initial 25 space stocks.")
    st.cache_data.clear()
    st.rerun()

st.title("🚀 A1-WAVE : Space Sector Momentum & Execution Engine")
st.caption(
    "Daily Technical Filter, Relative Strength vs. Sector ETFs, Volume Accumulation & ATR Risk Engine"
)


# ---------------------------------------------------------
# 3. HELPER CALCULATIONS
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
# 4. DATA FETCHING
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_market_data(tickers, benchmark_tickers):
    all_tickers = list(set(tickers + list(benchmark_tickers.keys())))
    data = yf.download(all_tickers, period="1y", interval="1d", progress=False)
    return data


data = fetch_market_data(active_basket, BENCHMARKS)

# ---------------------------------------------------------
# 5. BENCHMARK HEALTH BANNER (WITH HOVER HELP)
# ---------------------------------------------------------
st.subheader("🌐 Sector Benchmark Macro Health")

# Specific decision context per benchmark
BENCHMARK_HELP = {
    "ARKX": "Pure-play, high-beta Space Innovation ETF. Tracks high-growth, speculative space tech. Use this to gauge overall risk-on sentiment in space tech.",
    "ITA": "iShares Aerospace & Defense ETF. Tracks established prime defense contractors (Lockheed, Raytheon, GE). Use this to see if legacy defense capital is strong.",
    "SPY": "S&P 500 Broad Market Index. Measures overall market macro health and systemic market regime risk.",
}


def analyze_benchmark(symbol, df_close):
    series = df_close[symbol].dropna()
    current = series.iloc[-1]
    sma_50 = series.rolling(50).mean().iloc[-1]
    sma_200 = series.rolling(200).mean().iloc[-1]
    ret_3m = ((current - series.iloc[-63]) / series.iloc[-63]) * 100

    vs_50_sma_pct = ((current - sma_50) / sma_50) * 100
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
        "vs 50-SMA": round(vs_50_sma_pct, 2),
        "3M Return": round(ret_3m, 2),
    }


etf_cols = st.columns(3)
etf_returns = {}

for idx, (symbol, name) in enumerate(BENCHMARKS.items()):
    metrics = analyze_benchmark(symbol, data["Close"])
    etf_returns[symbol] = metrics["3M Return"]

    # Dynamic tooltip explanation per benchmark metric card
    metric_help_text = (
        f"**{symbol} ({name})**\n\n"
        f"• **{BENCHMARK_HELP[symbol]}**\n\n"
        f"• **Status ({metrics['Status']}):** Macro health alignment based on 50-SMA & 200-SMA.\n"
        f"• **3M Return ({metrics['3M Return']}%):** Total gain/loss over the past 63 trading days (~3 months).\n"
        f"• **vs 50-SMA ({metrics['vs 50-SMA']}%):** Distance above/below the 50-day dynamic support line. Positive means trading above support."
    )

    with etf_cols[idx]:
        st.metric(
            label=f"{symbol} ({name})",
            value=f"${metrics['Price']} | {metrics['Status']}",
            delta=f"3M Return: {metrics['3M Return']}% (vs 50-SMA: {metrics['vs 50-SMA']}%)",
            help=metric_help_text,  # Enables hover tooltip on header card!
        )

st.divider()

# ---------------------------------------------------------
# 6. ENHANCED STOCK ANALYSIS ENGINE
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

    dist_50_pct = ((current_price - sma_50) / sma_50) * 100
    dist_200_pct = ((current_price - sma_200) / sma_200) * 100

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

    # Volume Ratio vs 20-Day Avg
    avg_vol_20 = df_vol.rolling(20).mean().iloc[-1]
    curr_vol = df_vol.iloc[-1]
    vol_ratio = (curr_vol / avg_vol_20) * 100 if avg_vol_20 > 0 else 100

    # RSI Calculation
    rsi_series = calculate_rsi(df_close)
    rsi_val = rsi_series.iloc[-1]

    # ATR & Stop Loss
    atr_series = calculate_atr(df_high, df_low, df_close)
    atr_val = atr_series.iloc[-1]
    stop_loss_suggested = current_price - (2 * atr_val)

    # Performance
    ret_3m = ((current_price - df_close.iloc[-63]) / df_close.iloc[-63]) * 100
    alpha_arkx = ret_3m - etf_rets.get("ARKX", 0)
    alpha_ita = ret_3m - etf_rets.get("ITA", 0)

    # Signal Engine
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


# Run analysis across active basket
stock_results = []
for ticker in active_basket:
    try:
        stock_results.append(analyze_space_stock(ticker, data, etf_returns))
    except Exception:
        continue

df_stocks = pd.DataFrame(stock_results)
# ---------------------------------------------------------
# COLUMN CONFIGURATION & HOVER HELP TOOLTIPS
# ---------------------------------------------------------
column_tooltips = {
    "Ticker": st.column_config.Column(
        label="Ticker",
        help="Stock ticker symbol.",
    ),
    "Action Signal": st.column_config.Column(
        label="Action Signal",
        help="⚡ Execution Decision: BUY PRIME = near 50-SMA + high volume; HOLD = riding trend; EXTENDED = wait for pullbacks; NO TRADE = trend broken.",
    ),
    "Phase 1": st.column_config.Column(
        label="Phase 1",
        help="🟢 PASS: Price > 50-SMA > 200-SMA (Healthy Uptrend). 🔴 FAIL: Below key moving averages. Must PASS to trade.",
    ),
    "Price ($)": st.column_config.NumberColumn(
        label="Price ($)",
        help="Latest closing price.",
        format="$%.2f",
    ),
    "50-SMA ($)": st.column_config.NumberColumn(
        label="50-SMA ($)",
        help="50-Day Simple Moving Average. Acts as institutional dynamic support line.",
        format="$%.2f",
    ),
    "Dist to 50-SMA (%)": st.column_config.NumberColumn(
        label="Dist to 50-SMA (%)",
        help="Distance to 50-day average. 0% to 4% is prime entry zone. >10% is extended.",
        format="%.2f%%",
    ),
    "Vol vs 20D Avg (%)": st.column_config.NumberColumn(
        label="Vol vs 20D Avg (%)",
        help="Current volume relative to 20-day average volume. >100% indicates institutional buying.",
        format="%.1f%%",
    ),
    "RSI (14)": st.column_config.NumberColumn(
        label="RSI (14)",
        help="14-Day Relative Strength Index. <30 = Oversold, 30-50 = Consolidation (Good), >70 = Extended/Overbought.",
        format="%.1f",
    ),
    "ATR 14 ($)": st.column_config.NumberColumn(
        label="ATR 14 ($)",
        help="Average True Range over 14 days (Volatility measure). Used to calculate position stop loss.",
        format="$%.2f",
    ),
    "Stop Loss ($)": st.column_config.NumberColumn(
        label="Stop Loss ($)",
        help="Suggested hard risk stop level set at 2x ATR below current price.",
        format="$%.2f",
    ),
    "3M Return (%)": st.column_config.NumberColumn(
        label="3M Return (%)",
        help="Total price return over the past 63 trading days (~3 months).",
        format="%.2f%%",
    ),
    "vs ARKX Alpha (%)": st.column_config.NumberColumn(
        label="vs ARKX Alpha (%)",
        help="Outperformance relative to ARK Space Innovation ETF (ARKX). Example: +33.19% means this stock outperformed ARKX by 33.19% over 3 months.",
        format="%.2f%%",
    ),
    "vs ITA Alpha (%)": st.column_config.NumberColumn(
        label="vs ITA Alpha (%)",
        help="Outperformance relative to iShares US Aerospace & Defense ETF (ITA) over 3 months.",
        format="%.2f%%",
    ),
}
# ---------------------------------------------------------
# CUSTOM HTML/CSS MATRIX RENDERER (DYNAMIC HEIGHT & TOOLTIPS)
# ---------------------------------------------------------
HEADER_HELP = {
    "Ticker": "Stock ticker symbol.",
    "Action Signal": "Execution Decision: BUY PRIME = near 50-SMA + high volume; HOLD = riding trend; EXTENDED = wait for pullbacks; NO TRADE = trend broken.",
    "Phase 1": "PASS: Price > 50-SMA > 200-SMA (Healthy Uptrend). FAIL: Below key moving averages.",
    "Price ($)": "Latest closing price.",
    "50-SMA ($)": "50-Day Simple Moving Average dynamic support line.",
    "Dist 50-SMA (%)": "Distance to 50-day average. 0% to 4% is prime entry zone.",
    "Vol vs 20D Avg (%)": "Volume relative to 20-day average. >100% indicates institutional buying.",
    "RSI (14)": "14-Day Relative Strength Index. <30 = Oversold, 30-50 = Dip Buy, >70 = Extended.",
    "Stop Loss ($)": "Suggested hard risk stop level set at 2x ATR below entry price.",
    "3M Return (%)": "Total price return over the past 63 trading days (~3 months).",
    "vs ARKX Alpha (%)": "Outperformance relative to ARK Space Innovation ETF (ARKX) over 3 months.",
    "vs ITA Alpha (%)": "Outperformance relative to iShares US Aerospace & Defense ETF (ITA) over 3 months.",
}


# ---------------------------------------------------------
# CUSTOM HTML/CSS MATRIX RENDERER (FIXED TOOLTIP CLIPPING)
# ---------------------------------------------------------
HEADER_HELP = {
    "Ticker": "Stock ticker symbol.",
    "Action Signal": "Execution Decision: BUY PRIME = near 50-SMA + high volume; HOLD = riding trend; EXTENDED = wait for pullbacks; NO TRADE = trend broken.",
    "Phase 1": "PASS: Price > 50-SMA > 200-SMA (Healthy Uptrend). FAIL: Below key moving averages.",
    "Price ($)": "Latest closing price.",
    "50-SMA ($)": "50-Day Simple Moving Average dynamic support line.",
    "Dist 50-SMA (%)": "Distance to 50-day average. 0% to 4% is prime entry zone.",
    "Vol vs 20D Avg (%)": "Volume relative to 20-day average. >100% indicates institutional buying.",
    "RSI (14)": "14-Day Relative Strength Index. <30 = Oversold, 30-50 = Dip Buy, >70 = Extended.",
    "Stop Loss ($)": "Suggested hard risk stop level set at 2x ATR below entry price.",
    "3M Return (%)": "Total price return over the past 63 trading days (~3 months).",
    "vs ARKX Alpha (%)": "Outperformance relative to ARK Space Innovation ETF (ARKX) over 3 months.",
    "vs ITA Alpha (%)": "Outperformance relative to iShares US Aerospace & Defense ETF (ITA) over 3 months.",
}

# ---------------------------------------------------------
# CUSTOM HTML/CSS MATRIX RENDERER (COMPACT & UNCLUTTERED)
# ---------------------------------------------------------
HEADER_HELP = {
    "Ticker": "Stock ticker symbol.",
    "Action Signal": "Execution Decision: BUY PRIME = near 50-SMA + high volume; HOLD = riding trend; EXTENDED = wait for pullbacks; NO TRADE = trend broken.",
    "Phase 1": "PASS: Price > 50-SMA > 200-SMA (Healthy Uptrend). FAIL: Below key moving averages.",
    "Price ($)": "Latest closing price.",
    "50-SMA ($)": "50-Day Simple Moving Average dynamic support line.",
    "Dist 50-SMA (%)": "Distance to 50-day average. 0% to 4% is prime entry zone.",
    "Vol vs 20D Avg (%)": "Volume relative to 20-day average. >100% indicates institutional buying.",
    "RSI (14)": "14-Day Relative Strength Index. <30 = Oversold, 30-50 = Dip Buy, >70 = Extended.",
    "Stop Loss ($)": "Suggested hard risk stop level set at 2x ATR below entry price.",
    "3M Return (%)": "Total price return over the past 63 trading days (~3 months).",
    "vs ARKX Alpha (%)": "Outperformance relative to ARK Space Innovation ETF (ARKX) over 3 months.",
    "vs ITA Alpha (%)": "Outperformance relative to iShares US Aerospace & Defense ETF (ITA) over 3 months.",
}


def render_interactive_matrix(df):
    if df.empty:
        st.info("No data available for the selected filter.")
        return

    # Compact, tight height formula: Header (40px) + 38px per row + subtle border padding
    calculated_height = (len(df) * 38) + 48

    custom_css = """
    <style>
    html, body {
        margin: 0;
        padding: 0;
        background-color: transparent;
        overflow: hidden;
    }
    .matrix-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 13px;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
    }
    .matrix-table th {
        background-color: #f8fafc;
        color: #334155;
        padding: 8px;
        text-align: left;
        border-bottom: 2px solid #e2e8f0;
        font-weight: 600;
        white-space: nowrap;
        position: relative;
    }
    .matrix-table td {
        padding: 8px;
        border-bottom: 1px solid #f1f5f9;
        background-color: #ffffff;
        color: #0f172a;
        position: relative;
        white-space: nowrap;
    }
    .matrix-table tr:last-child td {
        border-bottom: none;
    }
    .matrix-table tr:hover td {
        background-color: #f8fafc;
    }

    /* Tooltip Core Styling */
    .has-tooltip {
        cursor: help;
    }
    .has-tooltip .tooltip-text {
        visibility: hidden;
        width: 210px;
        background-color: #0f172a;
        color: #f8fafc;
        text-align: left;
        border-radius: 6px;
        padding: 8px 10px;
        position: absolute;
        z-index: 99999;
        left: 50%;
        transform: translateX(-50%);
        opacity: 0;
        transition: opacity 0.15s ease-in-out;
        font-size: 11px;
        line-height: 1.35;
        font-weight: normal;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.2);
        pointer-events: none;
        white-space: normal;
    }

    /* Header Tooltips open downwards */
    .matrix-table th.has-tooltip .tooltip-text {
        top: 100%;
        bottom: auto;
    }

    /* Cell Tooltips open upwards */
    .matrix-table td.has-tooltip .tooltip-text {
        bottom: 100%;
        top: auto;
    }

    .has-tooltip:hover .tooltip-text {
        visibility: visible;
        opacity: 1;
    }
    .help-icon {
        display: inline-block;
        margin-left: 2px;
        font-size: 10px;
        color: #64748b;
    }
    </style>
    """

    table_html = custom_css + '<table class="matrix-table"><thead><tr>'

    headers = [
        "Ticker",
        "Action Signal",
        "Phase 1",
        "Price ($)",
        "50-SMA ($)",
        "Dist 50-SMA (%)",
        "Vol vs 20D Avg (%)",
        "RSI (14)",
        "Stop Loss ($)",
        "3M Return (%)",
        "vs ARKX Alpha (%)",
        "vs ITA Alpha (%)",
    ]

    for h in headers:
        tooltip = HEADER_HELP.get(h, "")
        table_html += f"""
        <th class="has-tooltip">
            {h} <span class="help-icon">❓</span>
            <span class="tooltip-text"><b>{h}:</b><br>{tooltip}</span>
        </th>
        """

    table_html += "</tr></thead><tbody>"

    for _, row in df.iterrows():
        ticker = row["Ticker"]

        help_price = f"Latest closing price for {ticker} is ${row['Price ($)']:.2f}."
        help_dist = (
            f"{ticker} is {row['Dist to 50-SMA (%)']:.2f}% from its 50-SMA line. "
            + (
                "Sitting in prime buy zone!"
                if row["Dist to 50-SMA (%)"] <= 4
                else "Extended from support."
            )
        )
        help_vol = f"{ticker} volume is {row['Vol vs 20D Avg (%)']:.1f}% of its 20-day average. " + (
            "Institutional buying confirmed!"
            if row["Vol vs 20D Avg (%)"] >= 110
            else "Standard volume."
        )
        help_rsi = f"RSI is {row['RSI (14)']:.1f}. " + (
            "Overbought (>70) - wait for dip."
            if row["RSI (14)"] > 70
            else (
                "Oversold/Consolidating - good entry setup."
                if row["RSI (14)"] < 50
                else "Neutral trend."
            )
        )
        help_stop = f"Suggested risk stop at ${row['Stop Loss ($)']:.2f} (2x ATR below entry)."
        help_arkx = f"{ticker} outperformed ARKX space ETF by {row['vs ARKX Alpha (%)']:+.2f}% over 3 months."
        help_ita = f"{ticker} outperformed ITA defense ETF by {row['vs ITA Alpha (%)']:+.2f}% over 3 months."

        table_html += f"""
        <tr>
            <td class="has-tooltip"><b>{ticker}</b><span class="tooltip-text">Ticker symbol: {ticker}</span></td>
            <td class="has-tooltip">{row['Action Signal']}<span class="tooltip-text">{row['Action Signal']} trigger.</span></td>
            <td class="has-tooltip">{row['Phase 1']}<span class="tooltip-text">Phase 1 Status: {row['Phase 1']}</span></td>
            <td class="has-tooltip">${row['Price ($)']:.2f}<span class="tooltip-text">{help_price}</span></td>
            <td class="has-tooltip">${row['50-SMA ($)']:.2f}<span class="tooltip-text">50-Day Moving Average support level.</span></td>
            <td class="has-tooltip">{row['Dist to 50-SMA (%)']:.2f}%<span class="tooltip-text">{help_dist}</span></td>
            <td class="has-tooltip">{row['Vol vs 20D Avg (%)']:.1f}%<span class="tooltip-text">{help_vol}</span></td>
            <td class="has-tooltip">{row['RSI (14)']:.1f}<span class="tooltip-text">{help_rsi}</span></td>
            <td class="has-tooltip">${row['Stop Loss ($)']:.2f}<span class="tooltip-text">{help_stop}</span></td>
            <td class="has-tooltip">{row['3M Return (%)']:.2f}%<span class="tooltip-text">Past 63-day cumulative return.</span></td>
            <td class="has-tooltip">{row['vs ARKX Alpha (%)']:+.2f}%<span class="tooltip-text">{help_arkx}</span></td>
            <td class="has-tooltip">{row['vs ITA Alpha (%)']:+.2f}%<span class="tooltip-text">{help_ita}</span></td>
        </tr>
        """

    table_html += "</tbody></table>"

    st.components.v1.html(table_html, height=calculated_height, scrolling=False)

    
# ---------------------------------------------------------
# 7. ACTIONABLE ENTRY SIGNALS
# ---------------------------------------------------------
st.subheader("⚡ High-Conviction Tranche Entry Signals")

if not df_stocks.empty:
    prime_entries = df_stocks[
        df_stocks["Action Signal"].isin(
            ["BUY - PRIME ENTRY ⚡", "BUY - NEAR SUPPORT 🎯"]
        )
    ]

    if not prime_entries.empty:
        st.success(
            f"**BUY SIGNALS CONFIRMED:** {len(prime_entries)} stock(s) pass Phase 1 and are sitting in low-risk entry zones:"
        )
        render_interactive_matrix(prime_entries)
    else:
        st.info(
            "**NO IMMEDIATE ENTRY SIGNALS:** No stocks currently meet the combined Phase 1 + Volume + Support proximity criteria."
        )

st.divider()

# ---------------------------------------------------------
# 8. FULL MATRIX WITH DECISION FILTERS
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

if signal_filter == "BUY SIGNALS ONLY" and not df_stocks.empty:
    filtered_df = df_stocks[df_stocks["Action Signal"].str.contains("BUY")]
elif signal_filter == "Phase 1 Passes Only" and not df_stocks.empty:
    filtered_df = df_stocks[df_stocks["Phase 1"] == "PASS 🟢"]
elif signal_filter == "CONSOLIDATING" and not df_stocks.empty:
    filtered_df = df_stocks[df_stocks["Phase 1"] == "NEUTRAL 🟡"]
elif signal_filter == "NO TRADE" and not df_stocks.empty:
    filtered_df = df_stocks[df_stocks["Phase 1"] == "FAIL 🔴"]
else:
    filtered_df = df_stocks

render_interactive_matrix(filtered_df)