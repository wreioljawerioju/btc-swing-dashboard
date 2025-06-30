import streamlit as st
import pandas as pd
import requests
import openai

# ---------------------------
# 🔐 사용자 API 키 입력
# ---------------------------
st.set_page_config(layout="wide")
st.title("📈 비트코인 단기 분석 대시보드 (pandas_ta 없이)")

api_key = st.text_input("🔑 OpenAI API 키를 입력하세요", type="password")
if not api_key:
    st.warning("API 키를 입력해야 GPT 해석 기능이 작동합니다.")
else:
    openai.api_key = api_key

# ---------------------------
# 🕒 타임프레임 구성
# ---------------------------
timeframes = {
    "1분봉": ("1m", 100),
    "5분봉": ("5m", 200),
    "15분봉": ("15m", 100),
    "1시간봉": ("1h", 100),
    "4시간봉": ("4h", 100)
}

# ---------------------------
# 📦 바이낭스 OHLCV 데이터 요청
# ---------------------------
def get_ohlcv(symbol="BTCUSDT", interval="1m", limit=100):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        if isinstance(data, list) and len(data) > 0:
            df = pd.DataFrame(data, columns=["time", "open", "high", "low", "close", "volume"] + ["_"]*6)
            df["close"] = df["close"].astype(float)
            df["volume"] = df["volume"].astype(float)
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ {interval} OHLCV 요청 오류: {e}")
        return pd.DataFrame()

# ---------------------------
# 📀 RSI 계산 함수
# ---------------------------
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ---------------------------
# 🧠 GPT 해석 함수
# ---------------------------
def gpt_summary(results):
    prompt = "비트코인의 각 시간봉 지표 상태는 다음과 같아:\n\n"
    for tf, m in results.items():
        prompt += f"[{tf}] 가격: {m['close']:.2f}, RSI: {m['RSI']:.2f}, 거래량: {m['volume']:.2f}\n"
    prompt += "\n스윗 트레이딩 관점에서 단기 가격 전략을 한국어로 요약해줘."

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200
    )
    return response.choices[0].message.content.strip()

# ---------------------------
# 📊 메인 분석
# ---------------------------
results = {}
for label, (tf, limit) in timeframes.items():
    df = get_ohlcv(interval=tf, limit=limit)
    if df.empty or len(df) < 50:
        st.warning(f"⚠️ {label} 데이터가 부족하거나 오류가 발생했습니다.")
        continue

    df["EMA20"] = df["close"].ewm(span=20).mean()
    df["EMA50"] = df["close"].ewm(span=50).mean()
    df["EMA200"] = df["close"].ewm(span=200).mean()
    df["RSI"] = compute_rsi(df["close"])
    df = df.dropna()

    if df.empty:
        st.warning(f"⚠️ {label} 지표 계산 후 데이터가 없습니다.")
        continue

    latest = df.iloc[-1]

    st.subheader(f"✅ {label} 분석")
    st.write(f"""
    - 현재가: {latest['close']:.2f} USDT  
    - RSI: {latest['RSI']:.2f}  
    - 거래량: {latest['volume']:.2f}  
    - EMA20: {latest['EMA20']:.2f}  
    - EMA50: {latest['EMA50']:.2f}  
    - EMA200: {latest['EMA200']:.2f}
    """)
    results[label] = {
        "close": latest["close"],
        "RSI": latest["RSI"],
        "volume": latest["volume"]
    }

# ---------------------------
# 🧠 GPT 종합 해석
# ---------------------------
st.markdown("---")
st.subheader("🧠 GPT 종합 해석")
if api_key and st.button("GPT에게 단기 전략 요청하기"):
    with st.spinner("GPT 분석 중..."):
        summary = gpt_summary(results)
    st.success(summary)
