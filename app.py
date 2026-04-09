import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Structured Notes Builder", layout="wide")

st.title("Structured Notes Builder")

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

    load_data = st.button("Load Market Data")

if load_data:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")

        if hist.empty:
            st.error("No se encontró información para ese ticker.")
        else:
            last_price = hist["Close"].iloc[-1]
            st.success(f"Ticker cargado correctamente: {ticker}")
            st.write(f"Último cierre disponible: ${last_price:,.2f}")
            st.write(f"Estrategia seleccionada: {strategy}")

    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
