import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(
    page_title="Structured Notes Builder",
    page_icon="📈",
    layout="wide"
)

# ---------------------------
# ESTILO
# ---------------------------
st.markdown("""
<style>
    .main-title {
        font-size: 2.35rem;
        font-weight: 800;
        margin-bottom: 0.1rem;
        color: #1f2937;
    }
    .subtitle {
        font-size: 0.95rem;
        color: #6b7280;
        margin-bottom: 1.2rem;
    }
    .card {
        background-color: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 0.95rem 1rem 0.85rem 1rem;
        margin-bottom: 0.9rem;
    }
    .section-title {
        font-size: 1rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 0.6rem;
    }
    .small-note {
        font-size: 0.84rem;
        color: #6b7280;
    }
    div[data-testid="metric-container"] {
        padding: 0.45rem 0.2rem 0.35rem 0.2rem;
    }
    div[data-testid="metric-container"] label {
        font-size: 0.78rem !important;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        font-size: 0.95rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# FUNCIONES AUXILIARES
# ---------------------------
def format_number(value, decimals=2, prefix="", suffix=""):
    if value is None:
        return "—"
    try:
        if pd.isna(value):
            return "—"
    except Exception:
        pass
    return f"{prefix}{value:,.{decimals}f}{suffix}"


def safe_pct_change(current_value, previous_value):
    if previous_value in [None, 0]:
        return np.nan
    return ((current_value / previous_value) - 1) * 100


def tenor_to_years(tenor: str) -> float:
    mapping = {
        "3 Months": 3 / 12,
        "4 Months": 4 / 12,
        "5 Months": 5 / 12,
        "6 Months": 6 / 12,
    }
    return mapping.get(tenor, 0.25)


def strategy_description(strategy_name: str):
    descriptions = {
        "Long Stock": "Directional bullish exposure through the underlying stock.",
        "Short Stock": "Directional bearish exposure through the underlying stock.",
        "Long Call": "Bullish view with limited downside equal to the premium paid and upside participation above strike.",
        "Short Call": "Income-oriented bearish to neutral view, with limited premium received and potentially large upside risk.",
        "Long Put": "Bearish view with limited downside equal to the premium paid and upside in declining markets.",
        "Short Put": "Bullish to neutral income strategy, with premium received but downside exposure if the stock falls.",
        "Collar": "Protective structure that combines downside hedge and upside cap, often used for risk control.",
        "Straddle": "Long volatility strategy using ATM call and put; benefits from large moves in either direction.",
        "Strangle": "Long volatility strategy with different strikes; lower cost than a straddle but needs a larger move.",
        "Butterfly": "Limited-risk and limited-return strategy often used when the stock is expected to stay near a target level.",
        "Condor": "Defined-risk range strategy used when moderate price stability is expected.",
        "Call": "Single call option exposure for bullish participation.",
        "Put": "Single put option exposure for bearish participation or downside hedging.",
        "Cono Largo": "Equivalent to a long straddle: buy call and buy put, typically ATM.",
        "Cono Corto": "Equivalent to a short straddle: sell call and sell put, typically ATM and high risk."
    }
    return descriptions.get(strategy_name, "No description available.")


def get_period_config(selected_period: str):
    configs = {
        "1D": {"period": "1d", "interval": "5m"},
        "5D": {"period": "5d", "interval": "30m"},
        "1M": {"period": "1mo", "interval": "1d"},
        "3M": {"period": "3mo", "interval": "1d"},
        "6M": {"period": "6mo", "interval": "1d"},
        "YTD": {"period": "ytd", "interval": "1d"},
        "1Y": {"period": "1y", "interval": "1d"},
    }
    return configs[selected_period]


def get_return_window_days(selected_period: str):
    mapping = {
        "1D": 1,
        "5D": 5,
        "1M": 21,
        "3M": 63,
        "6M": 126,
        "1Y": 252,
    }
    return mapping.get(selected_period, None)


# ---------------------------
# DATA FUNCTIONS
# ---------------------------
@st.cache_data(ttl=900)
def get_fx_rate_to_usd(currency: str):
    if not currency or currency.upper() == "USD":
        return 1.0

    currency = currency.upper().strip()

    try:
        fx_symbol = f"{currency}USD=X"
        fx_ticker = yf.Ticker(fx_symbol)
        fx_hist = fx_ticker.history(period="5d", auto_adjust=False)

        if fx_hist.empty:
            return None

        return float(fx_hist["Close"].dropna().iloc[-1])
    except Exception:
        return None


@st.cache_data(ttl=900)
def get_full_market_data(ticker_symbol: str):
    ticker_symbol = ticker_symbol.strip().upper()
    if not ticker_symbol:
        return None

    stock = yf.Ticker(ticker_symbol)
    hist_1y = stock.history(period="1y", interval="1d", auto_adjust=False)

    if hist_1y.empty or len(hist_1y) < 30:
        return None

    hist_1y = hist_1y.dropna().copy()

    last_close = float(hist_1y["Close"].iloc[-1])
    prev_close = float(hist_1y["Close"].iloc[-2])
    today_open = float(hist_1y["Open"].iloc[-1])
    today_high = float(hist_1y["High"].iloc[-1])
    today_low = float(hist_1y["Low"].iloc[-1])
    today_volume = float(hist_1y["Volume"].iloc[-1])

    currency = "USD"
    try:
        fast_info = stock.fast_info
        currency = fast_info.get("currency", "USD") or "USD"
    except Exception:
        currency = "USD"

    fx_rate_to_usd = get_fx_rate_to_usd(currency)
    price_usd = last_close * fx_rate_to_usd if fx_rate_to_usd is not None else None

    high_52 = float(hist_1y["High"].max())
    low_52 = float(hist_1y["Low"].min())

    current_year = datetime.now().year
    hist_ytd = hist_1y[hist_1y.index.year == current_year].copy()
    ytd_return = np.nan
    if not hist_ytd.empty and len(hist_ytd) >= 2:
        ytd_start = float(hist_ytd["Close"].iloc[0])
        ytd_return = safe_pct_change(last_close, ytd_start)

    one_month_return = np.nan
    three_month_return = np.nan
    six_month_return = np.nan
    one_year_return = np.nan

    if len(hist_1y) >= 22:
        one_month_return = safe_pct_change(last_close, float(hist_1y["Close"].iloc[-22]))
    if len(hist_1y) >= 64:
        three_month_return = safe_pct_change(last_close, float(hist_1y["Close"].iloc[-64]))
    if len(hist_1y) >= 127:
        six_month_return = safe_pct_change(last_close, float(hist_1y["Close"].iloc[-127]))
    if len(hist_1y) >= 252:
        one_year_return = safe_pct_change(last_close, float(hist_1y["Close"].iloc[0]))

    return {
        "ticker": ticker_symbol,
        "currency": currency,
        "fx_rate_to_usd": fx_rate_to_usd,
        "last_close": last_close,
        "price_usd": price_usd,
        "today_open": today_open,
        "today_high": today_high,
        "today_low": today_low,
        "today_volume": today_volume,
        "high_52": high_52,
        "low_52": low_52,
        "one_month_return": one_month_return,
        "three_month_return": three_month_return,
        "six_month_return": six_month_return,
        "one_year_return": one_year_return,
        "ytd_return": ytd_return,
        "hist_1y": hist_1y,
    }


@st.cache_data(ttl=900)
def get_chart_data(ticker_symbol: str, selected_period: str):
    config = get_period_config(selected_period)
    stock = yf.Ticker(ticker_symbol)
    hist = stock.history(
        period=config["period"],
        interval=config["interval"],
        auto_adjust=False
    )

    if hist.empty:
        return None

    return hist.dropna().copy()


def calculate_selected_return(hist_1y: pd.DataFrame, selected_period: str):
    if hist_1y is None or hist_1y.empty:
        return np.nan

    last_close = float(hist_1y["Close"].iloc[-1])

    if selected_period == "YTD":
        current_year = datetime.now().year
        hist_ytd = hist_1y[hist_1y.index.year == current_year].copy()
        if hist_ytd.empty or len(hist_ytd) < 2:
            return np.nan
        start_price = float(hist_ytd["Close"].iloc[0])
        return safe_pct_change(last_close, start_price)

    window_days = get_return_window_days(selected_period)
    if window_days is None or len(hist_1y) <= window_days:
        return np.nan

    start_price = float(hist_1y["Close"].iloc[-(window_days + 1)])
    return safe_pct_change(last_close, start_price)


def calculate_volatility(hist_1y: pd.DataFrame, vol_window_label: str):
    if hist_1y is None or hist_1y.empty:
        return np.nan

    mapping = {
        "20D": 20,
        "30D": 30,
        "60D": 60,
        "90D": 90,
        "1Y": 252,
    }

    days = mapping[vol_window_label]
    if len(hist_1y) < days + 1:
        return np.nan

    subset = hist_1y.tail(days).copy()
    returns = subset["Close"].pct_change().dropna()
    if returns.empty:
        return np.nan

    return float(returns.std() * np.sqrt(252) * 100)


def calculate_average_volume(hist_1y: pd.DataFrame, volume_window_label: str):
    if hist_1y is None or hist_1y.empty:
        return np.nan

    mapping = {
        "1D": 1,
        "5D": 5,
        "20D": 20,
        "30D": 30,
        "60D": 60,
    }

    days = mapping[volume_window_label]
    if len(hist_1y) < days:
        return np.nan

    subset = hist_1y.tail(days).copy()
    return float(subset["Volume"].mean())


def build_price_chart(chart_df: pd.DataFrame, ticker: str, currency: str, selected_period: str):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=chart_df.index,
            y=chart_df["Close"],
            mode="lines",
            name=ticker,
            line=dict(width=2),
            hovertemplate="%{x}<br>Close: %{y:.2f} " + currency + "<extra></extra>"
        )
    )

    fig.update_layout(
        title=f"{ticker} Price Chart ({selected_period})",
        xaxis_title="Date",
        yaxis_title=f"Price ({currency})",
        template="plotly_white",
        height=420,
        margin=dict(l=20, r=20, t=55, b=20),
        hovermode="x unified",
        showlegend=False
    )

    return fig


# ---------------------------
# SESSION STATE
# ---------------------------
if "market_data" not in st.session_state:
    st.session_state.market_data = None

if "loaded_ticker" not in st.session_state:
    st.session_state.loaded_ticker = None

# ---------------------------
# SIDEBAR
# ---------------------------
with st.sidebar:
    st.header("Global Inputs")

    ticker = st.text_input(
        "Ticker",
        value=st.session_state.loaded_ticker or "AAPL",
        placeholder="Ej. AAPL"
    ).upper().strip()

    total_note_notional = st.number_input(
        "Total Note Notional (USD)",
        min_value=100000,
        value=100000,
        step=5000
    )

    st.markdown("---")
    load_data = st.button("Load / Refresh Ticker Data", use_container_width=True)

# ---------------------------
# LOAD DATA
# ---------------------------
if load_data or (st.session_state.market_data is None and ticker):
    try:
        data = get_full_market_data(ticker)
        if data is None:
            st.session_state.market_data = None
            st.session_state.loaded_ticker = None
            st.error("No se encontró información suficiente para ese ticker.")
        else:
            st.session_state.market_data = data
            st.session_state.loaded_ticker = ticker
    except Exception as e:
        st.session_state.market_data = None
        st.error(f"Error al obtener datos de mercado: {e}")

data = st.session_state.market_data
loaded_ticker = st.session_state.loaded_ticker or ticker

# ---------------------------
# HEADER
# ---------------------------
st.markdown('<div class="main-title">Structured Notes Builder</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Visual prototype for equity-linked strategy analysis and structured product design.</div>',
    unsafe_allow_html=True
)

# Strategy defaults for top header
default_tenor = "6 Months"
default_strategy = "Long Stock"

top1, top2, top3, top4 = st.columns(4)
top1.metric("Ticker", loaded_ticker if loaded_ticker else "—")
top2.metric("Total Note Notional", f"${total_note_notional:,.0f}")
top3.metric("Tenor", default_tenor)
top4.metric("Strategy", default_strategy)

# ---------------------------
# TABS
# ---------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "Market Snapshot",
    "Strategy Builder",
    "Scenario Analysis",
    "Executive Summary"
])

# ===========================
# TAB 1 - MARKET SNAPSHOT
# ===========================
with tab1:
    if data:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Pricing and Currency</div>', unsafe_allow_html=True)

        row0 = st.columns(5)
        row0[0].metric("Local Currency", data["currency"])
        row0[1].metric("Price (Local)", format_number(data["last_close"], prefix=f"{data['currency']} "))
        row0[2].metric("FX to USD", format_number(data["fx_rate_to_usd"], decimals=4))
        row0[3].metric("Price (USD)", format_number(data["price_usd"], prefix="$"))
        row0[4].metric("52W Range", f"{format_number(data['low_52'], prefix='')} - {format_number(data['high_52'])} {data['currency']}")

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Snapshot Controls</div>', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        selected_period = c1.selectbox(
            "Return & Chart Period",
            ["1D", "5D", "1M", "3M", "6M", "YTD", "1Y"],
            index=2,
            key="selected_period"
        )
        vol_window = c2.selectbox(
            "Volatility Window",
            ["20D", "30D", "60D", "90D", "1Y"],
            index=1,
            key="vol_window"
        )
        volume_window = c3.selectbox(
            "Average Volume Window",
            ["1D", "5D", "20D", "30D", "60D"],
            index=2,
            key="volume_window"
        )

        st.markdown('</div>', unsafe_allow_html=True)

        selected_return = calculate_selected_return(data["hist_1y"], selected_period)
        selected_vol = calculate_volatility(data["hist_1y"], vol_window)
        selected_avg_volume = calculate_average_volume(data["hist_1y"], volume_window)

        row1 = st.columns(5)
        row1[0].metric(f"{selected_period} Return", format_number(selected_return, suffix="%"))
        row1[1].metric(f"{vol_window} Volatility", format_number(selected_vol, suffix="%"))
        row1[2].metric(f"{volume_window} Avg Volume", format_number(selected_avg_volume, decimals=0))
        row1[3].metric("Day High", format_number(data["today_high"], prefix=f"{data['currency']} "))
        row1[4].metric("Day Low", format_number(data["today_low"], prefix=f"{data['currency']} "))

        row2 = st.columns(5)
        row2[0].metric("1M Return", format_number(data["one_month_return"], suffix="%"))
        row2[1].metric("3M Return", format_number(data["three_month_return"], suffix="%"))
        row2[2].metric("6M Return", format_number(data["six_month_return"], suffix="%"))
        row2[3].metric("YTD Return", format_number(data["ytd_return"], suffix="%"))
        row2[4].metric("1Y Return", format_number(data["one_year_return"], suffix="%"))

        chart_df = get_chart_data(loaded_ticker, selected_period)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Interactive Price Chart</div>', unsafe_allow_html=True)

        if chart_df is not None and not chart_df.empty:
            fig = build_price_chart(chart_df, loaded_ticker, data["currency"], selected_period)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No chart data available for the selected period.")

        st.markdown(
            '<div class="small-note">The chart and dynamic metrics update automatically when you change the snapshot controls.</div>',
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning("Load a ticker first to view the market snapshot.")

# ===========================
# TAB 2 - STRATEGY BUILDER
# ===========================
with tab2:
    sb1, sb2, sb3 = st.columns(3)

    tenor = sb1.selectbox(
        "Tenor",
        ["3 Months", "4 Months", "5 Months", "6 Months"],
        index=3,
        key="builder_tenor"
    )

    strategy_family = sb2.selectbox(
        "Strategy Family",
        [
            "Directional",
            "Volatility",
            "Protection / Hedging",
            "Range Structures",
            "Single Option"
        ],
        key="builder_family"
    )

    strategy_options = {
        "Directional": ["Long Stock", "Short Stock", "Long Call", "Short Put", "Long Put", "Short Call"],
        "Volatility": ["Straddle", "Strangle", "Cono Largo", "Cono Corto"],
        "Protection / Hedging": ["Collar"],
        "Range Structures": ["Butterfly", "Condor"],
        "Single Option": ["Call", "Put"]
    }

    strategy = sb3.selectbox(
        "Strategy",
        strategy_options[strategy_family],
        key="builder_strategy"
    )

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Strategy Overview</div>', unsafe_allow_html=True)

    left, right = st.columns([1.15, 1])

    with left:
        st.write(f"**Total Note Notional:** ${total_note_notional:,.0f}")
        st.write(f"**Tenor:** {tenor}")
        st.write(f"**Tenor in Years:** {tenor_to_years(tenor):.4f}")
        st.write(f"**Strategy Family:** {strategy_family}")
        st.write(f"**Selected Strategy:** {strategy}")

        if data:
            st.write(f"**Underlying:** {loaded_ticker}")
            st.write(f"**Spot (Local):** {data['currency']} {data['last_close']:,.2f}")
            st.write(f"**Spot (USD):** {format_number(data['price_usd'], prefix='$')}")
            st.write(f"**Indicative ATM Strike (Local):** {data['currency']} {data['last_close']:,.2f}")
            if data["price_usd"] and data["price_usd"] > 0:
                units = total_note_notional / data["price_usd"]
                st.write(f"**Indicative Units at Spot:** {units:,.2f}")

    with right:
        st.write("**Description**")
        st.write(strategy_description(strategy))
        st.write("**Builder Scope**")
        st.write(
            "This is the module where we will later add option legs, ATM logic, premiums, break-even, "
            "max gain, max loss and indicative payoff diagrams."
        )

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Indicative Legs</div>', unsafe_allow_html=True)

    if strategy in ["Long Call", "Call"]:
        st.write("- Long 1 ATM Call")
    elif strategy == "Short Call":
        st.write("- Short 1 ATM Call")
    elif strategy in ["Long Put", "Put"]:
        st.write("- Long 1 ATM Put")
    elif strategy == "Short Put":
        st.write("- Short 1 ATM Put")
    elif strategy in ["Straddle", "Cono Largo"]:
        st.write("- Long 1 ATM Call")
        st.write("- Long 1 ATM Put")
    elif strategy == "Cono Corto":
        st.write("- Short 1 ATM Call")
        st.write("- Short 1 ATM Put")
    elif strategy == "Strangle":
        st.write("- Long 1 OTM Call")
        st.write("- Long 1 OTM Put")
    elif strategy == "Collar":
        st.write("- Long Underlying")
        st.write("- Long Protective Put")
        st.write("- Short Covered Call")
    elif strategy == "Butterfly":
        st.write("- Long 1 Call K1")
        st.write("- Short 2 Calls K2")
        st.write("- Long 1 Call K3")
    elif strategy == "Condor":
        st.write("- Long Wing")
        st.write("- Short Inner Spread")
        st.write("- Long Wing")
    elif strategy == "Long Stock":
        st.write("- Long Underlying")
    elif strategy == "Short Stock":
        st.write("- Short Underlying")
    else:
        st.write("- Strategy legs to be defined")

    st.markdown('</div>', unsafe_allow_html=True)

# ===========================
# TAB 3 - SCENARIO ANALYSIS
# ===========================
with tab3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Scenario Analysis</div>', unsafe_allow_html=True)

    st.write("This tab will evaluate how the selected strategy behaves under different market conditions.")
    st.write("Indicative scenarios to include:")
    st.write("- Bullish scenario")
    st.write("- Base scenario")
    st.write("- Bearish scenario")
    st.write("- Sideways scenario")
    st.write("- High volatility scenario")
    st.write("- Low volatility scenario")

    if data:
        base_spot = data["last_close"]
        scenario_df = pd.DataFrame({
            "Scenario": ["Bullish", "Base", "Bearish"],
            "Indicative Underlying Price": [
                round(base_spot * 1.10, 2),
                round(base_spot, 2),
                round(base_spot * 0.90, 2)
            ]
        })
        st.dataframe(scenario_df, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ===========================
# TAB 4 - EXECUTIVE SUMMARY
# ===========================
with tab4:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Executive Summary</div>', unsafe_allow_html=True)

    if data:
        st.write(
            f"The selected underlying is **{loaded_ticker}**, currently trading in **{data['currency']}**, "
            f"with an indicative USD reference price of **{format_number(data['price_usd'], prefix='$')}**. "
            f"The total note notional is **${total_note_notional:,.0f}**."
        )
        st.write(
            "This interface is designed to separate market analysis, strategy construction, scenario evaluation "
            "and executive communication into distinct modules."
        )
    else:
        st.write(
            "Once ticker data is loaded, this section will summarize the underlying, note notional and strategic rationale."
        )

    st.markdown('</div>', unsafe_allow_html=True)
