@st.cache_data(ttl=900)
def get_market_data(ticker_symbol: str):
    stock = yf.Ticker(ticker_symbol)

    hist = stock.history(period="1y")

    if hist.empty:
        return None

    last_close = float(hist["Close"].iloc[-1])
    prev_close = float(hist["Close"].iloc[-2])

    daily_return = (last_close / prev_close - 1) * 100

    five_day_return = (
        last_close / float(hist["Close"].iloc[-6]) - 1
    ) * 100 if len(hist) > 6 else 0

    high_52 = float(hist["Close"].max())
    low_52 = float(hist["Close"].min())

    return {
        "last_close": last_close,
        "daily_return": daily_return,
        "five_day_return": five_day_return,
        "high_52": high_52,
        "low_52": low_52
    }
