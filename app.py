import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

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
        font-size: 2.8rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
        color: #1f2937;
    }
    .subtitle {
        font-size: 1.05rem;
        color: #6b7280;
        margin-bottom: 1.5rem;
    }
    .card {
        background-color: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 1.2rem 1.2rem 1rem 1.2rem;
        margin-bottom: 1rem;
    }
    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 0.7rem;
    }
    .small-note {
        font-size: 0.9rem;
        color: #6b7280;
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


@st.cache_data(ttl=900)
def get_fx_rate_to_usd(currency: str):
    """
    Devuelve cuántos USD vale 1 unidad de la moneda local.
    Ejemplos:
    - EUR -> USD usando EURUSD=X
    - MXN -> USD usando MXNUSD=X
    """
    if not currency or currency.upper() == "USD":
        return 1.0

    currency = currency.upper().strip()

    try:
        fx_symbol = f"{currency}USD=X"
        fx_ticker = yf.Ticker(fx_symbol)
        fx_hist = fx_ticker.history(period="5d", auto_adjust=False)

        if fx_hist.empty:
            return None

        fx_rate = float(fx_hist["Close"].dropna().iloc[-1])
        return fx_rate
    except Exception:
        return None


@st.cache_data(ttl=900)
def get_market_data(ticker_symbol: str):
    """
    Descarga datos históricos y calcula métricas de mercado.
    Usa history() para reducir problemas de rate limit.
    Intenta obtener moneda con fast_info y convierte a USD.
    """
    ticker_symbol = ticker_symbol.strip().upper()
    if not ticker_symbol:
        return None

    stock = yf.Ticker(ticker_symbol)

    hist = stock.history(period="1y", auto_adjust=False)

    if hist.empty or len(hist) < 6:
        return None

    hist = hist.dropna().copy()

    # Precios base
    last_close = float(hist["Close"].iloc[-1])
    prev_close = float(hist["Close"].iloc[-2])
    today_open = float(hist["Open"].iloc[-1])
    today_high = float(hist["High"].iloc[-1])
    today_low = float(hist["Low"].iloc[-1])

    # Rendimientos
    daily_return = safe_pct_change(last_close, prev_close)

    if len(hist) >= 6:
        close_5d_ago = float(hist["Close"].iloc[-6])
        five_day_return = safe_pct_change(last_close, close_5d_ago)
    else:
        five_day_return = np.nan

    if len(hist) >= 22:
        close_1m_ago = float(hist["Close"].iloc[-22])
        one_month_return = safe_pct_change(last_close, close_1m_ago)
    else:
        one_month_return = np.nan

    # 52W range
    high_52 = float(hist["High"].max())
    low_52 = float(hist["Low"].min())

    # Volumen
    today_volume = float(hist["Volume"].iloc[-1])
    avg_20d_volume = float(hist["Volume"].tail(20).mean()) if len(hist) >= 20 else float(hist["Volume"].mean())

    # Volatilidad histórica anualizada
    daily_returns_series = hist["Close"].pct_change().dropna()
    volatility_annual = float(daily_returns_series.std() * np.sqrt(252) * 100) if not daily_returns_series.empty else np.nan

    # Moneda local
    currency = "USD"
    try:
        fast_info = stock.fast_info
        currency = fast_info.get("currency", "USD")
        if currency is None:
            currency = "USD"
    except Exception:
        currency = "USD"

    # Conversión a USD
    fx_rate_to_usd = get_fx_rate_to_usd(currency)
    if fx_rate_to_usd is None:
        price_usd = None
    else:
        price_usd = last_close * fx_rate_to_usd

    chart_data = hist[["Close"]].copy().tail(120)

    return {
        "ticker": ticker_symbol,
        "currency": currency,
        "fx_rate_to_usd": fx_rate_to_usd,
        "last_close": last_close,
        "price_usd": price_usd,
        "today_open": today_open,
        "today_high": today_high,
        "today_low": today_low,
        "daily_return": daily_return,
        "five_day_return": five_day_return,
        "one_month_return": one_month_return,
        "high_52": high_52,
        "low_52": low_52,
        "today_volume": today_volume,
        "avg_20d_volume": avg_20d_volume,
        "volatility_annual": volatility_annual,
        "chart_data": chart_data,
    }


# ---------------------------
# SIDEBAR
# ---------------------------
with st.sidebar:
    st.header("Inputs")

    ticker = st.text_input(
        "Ticker",
        value="AAPL",
        placeholder="Ej. AAPL"
    ).upper().strip()

    notional = st.number_input(
        "Investment Amount (USD)",
        min_value=100000,
        value=100000,
        step=5000
    )

    tenor = st.selectbox(
        "Tenor",
        ["3 Months", "4 Months", "5 Months", "6 Months"]
    )

    strategy_family = st.selectbox(
        "Strategy Family",
        [
            "Directional",
            "Volatility",
            "Protection / Hedging",
            "Range Structures",
            "Single Option"
        ]
    )

    strategy_options = {
        "Directional": ["Long Stock", "Short Stock", "Long Call", "Short Put", "Long Put", "Short Call"],
        "Volatility": ["Straddle", "Strangle", "Cono Largo", "Cono Corto"],
        "Protection / Hedging": ["Collar"],
        "Range Structures": ["Butterfly", "Condor"],
        "Single Option": ["Call", "Put"]
    }

    strategy = st.selectbox(
        "Strategy",
        strategy_options[strategy_family]
    )

    load_data = st.button("Load Market Data", use_container_width=True)

# ---------------------------
# HEADER
# ---------------------------
st.markdown('<div class="main-title">Structured Notes Builder</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Visual prototype for equity-linked strategy analysis and structured product design.</div>',
    unsafe_allow_html=True
)

# ---------------------------
# MÉTRICAS SUPERIORES
# ---------------------------
top1, top2, top3, top4 = st.columns(4)
top1.metric("Ticker", ticker if ticker else "—")
top2.metric("Notional", f"${notional:,.0f}")
top3.metric("Tenor", tenor)
top4.metric("Strategy", strategy)

st.markdown("")

# ---------------------------
# CARGA DE DATOS
# ---------------------------
data = None

if load_data:
    try:
        data = get_market_data(ticker)
        if data is None:
            st.error("No se encontró información suficiente para ese ticker.")
    except Exception as e:
        st.error(f"Error al obtener datos de mercado: {e}")
else:
    st.info("Primero carga los datos de mercado para mostrar métricas del subyacente.")

# ---------------------------
# RESUMEN + DESCRIPCIÓN
# ---------------------------
left, right = st.columns([1.25, 1])

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Product Summary</div>', unsafe_allow_html=True)
    st.write(f"**Underlying:** {ticker if ticker else '—'}")
    st.write(f"**Investment Amount:** ${notional:,.0f}")
    st.write(f"**Tenor:** {tenor}")
    st.write(f"**Strategy Family:** {strategy_family}")
    st.write(f"**Selected Strategy:** {strategy}")
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Strategy Description</div>', unsafe_allow_html=True)
    st.write(strategy_description(strategy))
    st.markdown(
        '<div class="small-note">Later we can connect this section with payoff logic, option legs, breakeven and scenario analysis.</div>',
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------
# TABS
# ---------------------------
tab1, tab2, tab3 = st.tabs(["Market Snapshot", "Chart", "Comments"])

with tab1:
    if data:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Pricing and Currency</div>', unsafe_allow_html=True)

        row0 = st.columns(4)
        row0[0].metric("Local Currency", data["currency"] if data["currency"] else "—")
        row0[1].metric("Price (Local)", format_number(data["last_close"], prefix=f"{data['currency']} "))
        row0[2].metric("FX to USD", format_number(data["fx_rate_to_usd"], decimals=4))
        row0[3].metric("Price (USD)", format_number(data["price_usd"], prefix="$"))

        st.markdown('</div>', unsafe_allow_html=True)

        row1 = st.columns(5)
        row1[0].metric("1D Return", format_number(data["daily_return"], suffix="%"))
        row1[1].metric("5D Return", format_number(data["five_day_return"], suffix="%"))
        row1[2].metric("1M Return", format_number(data["one_month_return"], suffix="%"))
        row1[3].metric("Annual Vol", format_number(data["volatility_annual"], suffix="%"))
        row1[4].metric("Open", format_number(data["today_open"], prefix=f"{data['currency']} "))

        row2 = st.columns(5)
        row2[0].metric("52W High", format_number(data["high_52"], prefix=f"{data['currency']} "))
        row2[1].metric("52W Low", format_number(data["low_52"], prefix=f"{data['currency']} "))
        row2[2].metric("Day High", format_number(data["today_high"], prefix=f"{data['currency']} "))
        row2[3].metric("Day Low", format_number(data["today_low"], prefix=f"{data['currency']} "))
        row2[4].metric("Today Volume", format_number(data["today_volume"], decimals=0))

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Additional Market Context</div>', unsafe_allow_html=True)
        st.write(f"**20D Average Volume:** {format_number(data['avg_20d_volume'], decimals=0)}")
        st.write("These metrics are computed mainly from historical market data to keep the app lighter and more stable.")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning("No market data loaded yet.")

with tab2:
    if data:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Recent Price History</div>', unsafe_allow_html=True)
        st.line_chart(data["chart_data"])
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("The price chart will appear once market data is loaded.")

with tab3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Analyst Comments</div>', unsafe_allow_html=True)

    if data:
        comment = (
            f"The selected underlying is {ticker}. The asset trades in {data['currency']} and the app "
            f"also converts the reference price into USD to align with the project requirement. "
            f"The next step is to connect this market snapshot with the selected structure: {strategy}."
        )
        st.write(comment)
    else:
        st.write(
            "The interface is already prepared to display market data, local currency, USD conversion, "
            "and selected strategy context. Next we can connect this with payoff diagrams and financial logic."
        )

    st.markdown('</div>', unsafe_allow_html=True)
