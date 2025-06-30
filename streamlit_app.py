import streamlit as st
import pandas as pd
import requests
import openai
import pandas_ta as ta

st.set_page_config(layout="wide")
st.title("📈 비트코인 단기 분석 대시보드 (스윙용)")

api_key = st.text_input("🔑 OpenAI API 키를 입력하세요", type="password")
if not api_key:
    st.warning("API 키 입력 후 GPT 기능 활성화")
else:
    openai.api_key = api_key

timeframes = {"1분봉": ("1m",1000), "5분봉": ("5m",500), "15분봉": ("15m",100), "1시간봉": ("1h",100), "4시간봉": ("4h",100)}

def get_ohlcv(symbol="BTCUSDT", interval="1m", limit=100):
    res = requests.get("https://api.binance.com/api/v3/klines", params={"symbol":symbol,"interval":interval,"limit":limit})
    df = pd.DataFrame(res.json(), columns=["t","o","h","l","c","v"]+["_"]*6)
    df["c"]=df["c"].astype(float); df["v"]=df["v"].astype(float)
    return df

def analyze(df):
    df["RSI"]=ta.rsi(df["c"],14)
    df["StochRSI"]=ta.stochrsi(df["c"])["STOCHRSIk_14_14_3_3"]
    df["EMA20"]=ta.ema(df["c"],20); df["EMA50"]=ta.ema(df["c"],50); df["EMA200"]=ta.ema(df["c"],200)
    return df.dropna()

def gpt_summary(results):
    prompt="각 시간봉 지표 상태:\n"
    for tf,m in results.items():
        prompt+=f"[{tf}] 가격:{m['close']:.2f}, RSI:{m['RSI']:.2f}, StochRSI:{m['StochRSI']:.2f}, 거래량:{m['volume']:.2f}\n"
    prompt+="\n스윙포지션 관점에서 단기전망 요약해주세요."
    r=openai.ChatCompletion.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], max_tokens=200)
    return r.choices[0].message.content.strip()

results={}
for label,(tf,limit) in timeframes.items():
    df=get_ohlcv(interval=tf,limit=limit)
    df2=analyze(df)
    latest=df2.iloc[-1]
    st.subheader(label)
    st.write(f"가격:{latest['c']:.2f}, RSI:{latest['RSI']:.2f}, StochRSI:{latest['StochRSI']:.2f}, 거래량:{latest['v']:.2f}")
    results[label]={"close":latest["c"],"RSI":latest["RSI"],"StochRSI":latest["StochRSI"],"volume":latest["v"]}

st.markdown("---")
if api_key and st.button("GPT 단기전망 요청"):
    st.write(gpt_summary(results))
