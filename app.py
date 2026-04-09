import streamlit as st

st.set_page_config(page_title="Structured Notes Builder", layout="wide")

st.title("Structured Notes Builder")
st.subheader("Versión inicial de la app")

col1, col2 = st.columns(2)

with col1:
    ticker = st.selectbox("Ticker", ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"])
    notional = st.number_input("Monto de inversión (USD)", min_value=100000, value=100000, step=1000)

with col2:
    tenor = st.selectbox("Plazo", ["3 meses", "4 meses", "5 meses", "6 meses"])
    strategy = st.selectbox(
        "Estrategia",
        ["Capital Protected Note", "Yield Enhancement Note", "Reverse Convertible"]
    )

st.markdown("### Resumen")
st.write(f"**Ticker:** {ticker}")
st.write(f"**Monto:** ${notional:,.0f}")
st.write(f"**Plazo:** {tenor}")
st.write(f"**Estrategia:** {strategy}")

if st.button("Calcular"):
    st.success("La app ya está funcionando. El siguiente paso será conectar la lógica financiera.")
