import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Structured Notes Builder", page_icon="📈", layout="wide")

st.title("Structured Notes Builder")
st.subheader("Visual prototype for structured strategies")

with st.sidebar:
    st.header("Inputs")

    ticker = st.text_input("Ticker", value="AAPL", placeholder="Ej. AAPL").upper()

    strategy = st.selectbox(
        "Strategy",
        [
            "Long Call",
            "Short Call",
            "Long Put",
            "Short Put",
            "Collar",
            "Straddle",
            "Strangle",
            "Butterfly",
            "Condor"
        ]
    )

    notional = st.number_input(
        "Investment Amount (USD)",
        min_value=100000,
        value=100000,
        step=5000
    )

    tenor = st.selectbox("Tenor", ["3 Months", "4 Months", "5 Months", "6 Months"])

    load_data = st.button("Load Market Data")


@st.cache_data(ttl=900)
def get_market_data(ticker_symbol: str):
    stock = yf.Ticker(ticker_symbol)
    hist = stock.history(period="5d")

    if hist.empty:
        return None

    last_close = float(hist["Close"].iloc[-1])
    return {
        "ticker": ticker_symbol,
        "last_close": last_close
    }


col1, col2, col3 = st.columns(3)
col1.metric("Ticker", ticker if ticker else "—")
col2.metric("Notional", f"${notional:,.0f}")
col3.metric("Tenor", tenor)

st.markdown("### Product Summary")
st.write(f"**Selected Strategy:** {strategy}")

if load_data:
    try:
        data = get_market_data(ticker)

        if data is None:
            st.error("No se encontró información para ese ticker.")
        else:
            st.success("Datos cargados correctamente.")
            st.metric("Last Close", f"${data['last_close']:,.2f}")

    except Exception:
        st.error("Yahoo Finance está limitando temporalmente las consultas. Espera unos minutos y vuelve a intentar.")
else:
    st.info("Carga primero los datos de mercado para continuar.")
