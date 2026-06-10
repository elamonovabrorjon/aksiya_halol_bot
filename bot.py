import telebot
import requests
import pandas as pd
import numpy as np
import time
import threading
from datetime import datetime

# ===================== CONFIG =====================
TOKEN = "8781183838:AAFmgLoz6Bb8LlA-50lVAdAbNvhBCWO3sm0"
CHAT_ID = 745170275
FINNHUB = "d842bj1r01qkm5c9vr70d842bj1r01qkm5c9vr7g"

bot = telebot.TeleBot(TOKEN)
AUTO_ON = True

# ===================== FINNHUB DATA =====================
def get_data(symbol, resolution="1"):
    # symbol: XAUUSD -> OANDA:XAU_USD
    if symbol == "XAUUSD": fin = "OANDA:XAU_USD"
    elif symbol == "EURUSD": fin = "OANDA:EUR_USD"
    elif symbol == "BTC": fin = "BINANCE:BTCUSDT"
    else: fin = symbol

    url = f"https://finnhub.io/api/v1/candle?symbol={fin}&resolution={resolution}&from={int(time.time())-86400*5}&to={int(time.time())}&token={FINNHUB}"
    r = requests.get(url).json()

    if r.get('s')!= 'ok': return None

    df = pd.DataFrame({
        'time': pd.to_datetime(r['t'], unit='s'),
        'Open': r['o'], 'High': r['h'], 'Low': r['l'], 'Close': r['c']
    })
    return df

# ===================== INDICATORS =====================
def ema(s, n): return s.ewm(span=n).mean()
def rsi(s, n=14):
    d = s.diff()
    u = d.clip(lower=0).ewm(alpha=1/n).mean()
    dn = -d.clip(upper=0).ewm(alpha=1/n).mean()
    return 100 - 100/(1 + u/dn)

def atr(df, n=14):
    tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n).mean()

# ===================== SMC =====================
def trend(df):
    e50, e200 = ema(df['Close'],50), ema(df['Close'],200)
    if e50.iloc[-1] > e200.iloc[-1] and e50.iloc[-2] <= e200.iloc[-2]: return "UP"
    if e50.iloc[-1] < e200.iloc[-1] and e50.iloc[-2] >= e200.iloc[-2]: return "DOWN"
    return "UP" if e50.iloc[-1] > e200.iloc[-1] else "DOWN"

def liquidity(df):
    swing_h = df['High'].rolling(5, center=True).max().iloc[-3]
    swing_l = df['Low'].rolling(5, center=True).min().iloc[-3]
    last = df['Close'].iloc[-1]
    if abs(last - swing_h)/last < 0.001: return "ABOVE"
    if abs(last - swing_l)/last < 0.001: return "BELOW"
    return "NONE"

def order_block(df):
    # FVG detection
    for i in range(len(df)-3, len(df)-1):
        if df['Low'].iloc[i+1] > df['High'].iloc[i-1]: return "BULLISH"
        if df['High'].iloc[i+1] < df['Low'].iloc[i-1]: return "BEARISH"
    return "NONE"

def pattern(df):
    last, prev = df.iloc[-1], df.iloc[-2]
    body = abs(last['Close']-last['Open'])
    if last['Close'] > last['Open'] and prev['Close'] < prev['Open'] and body > (last['High']-last['Low'])*0.6:
        return "BULLISH"
    if last['Close'] < last['Open'] and prev['Close'] > prev['Open'] and body > (last['High']-last['Low'])*0.6:
        return "BEARISH"
    return "NONE"

# ===================== AI SCORE =====================
def ai_score(df):
    last = df.iloc[-1]
    r = rsi(df['Close']).iloc[-1]
    t = trend(df)
    liq = liquidity(df)
    ob = order_block(df)
    pat = pattern(df)
    a = atr(df).iloc[-1]

    score = 0
    if r < 35 or r > 65: score += 1
    if t == "UP" and last['Close'] > ema(df['Close'],50).iloc[-1]: score += 1
    if t == "DOWN" and last['Close'] < ema(df['Close'],50).iloc[-1]: score += 1
    if liq!= "NONE": score += 1
    if ob!= "NONE": score += 1
    if pat!= "NONE": score += 1
    if a > 0: score += 1

    return min(score, 6), r, t, liq, ob, pat, a

# ===================== SIGNAL =====================
def signal(symbol):
    df = get_data(symbol, "1")
    if df is None or len(df) < 60: return None

    score, r, t, liq, ob, pat, a = ai_score(df)
    last = df.iloc[-1]

    # News filter 14-16 UTC
    if 14 <= datetime.utcnow().hour <= 16: return None

    sig, sl, tp1, tp2 = "KUTING ⚠️", 0, 0, 0

    if score >= 4 and ob == "BULLISH" and t == "UP":
        sig = "BUY 🟢"
        sl = last['Close'] - a*1.5
        tp1 = last['Close'] + a*2.25
        tp2 = last['Close'] + a*4.5
    elif score >= 4 and ob == "BEARISH" and t == "DOWN":
        sig = "SELL 🔴"
        sl = last['Close'] + a*1.5
        tp1 = last['Close'] - a*2.25
        tp2 = last['Close'] - a*4.5

    return f"""📊 {symbol} [1m]

Trend: {t}
Liquidity: {liq}
OB: {ob}
Pattern: {pat}

RSI: {round(r,1)}
ATR: {round(a,2)}
AI Score: {score}/6

Signal: {sig}
{f"SL: {round(sl,2)} | TP1: {round(tp1,2)} | TP2: {round(tp2,2)}" if sig!="KUTING ⚠️" else ""}

⏰ {datetime.utcnow().strftime('%H:%M')} UTC"""

# ===================== HALOL =====================
def halol(symbol):
    try:
        r = requests.get(f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol}&token={FINNHUB}").json()
        sector = r.get('finnhubIndustry','').lower()
        haram = ['bank','insurance','alcohol','tobacco','gambling','casino']
        if any(h in sector for h in haram): return "❌ HARAM"

        f = requests.get(f"https://finnhub.io/api/v1/stock/metric?symbol={symbol}&metric=all&token={FINNHUB}").json()
        debt = f.get('metric',{}).get('totalDebt/totalEquityAnnual',0)
        if debt and debt > 0.33: return "⚠️ SHUBHALI"
        return "✅ HALOL"
    except: return "❓ NOMA'LUM"

# ===================== COMMANDS =====================
@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "🤖 SMC Bot tayyor!\n/gold - Oltin\n/eur - EURUSD\n/btc - Bitcoin\n/stock AAPL - Aksiya\n/auto on|off")

@bot.message_handler(commands=['gold'])
def g(m): bot.reply_to(m, signal("XAUUSD") or "Ma'lumot yo'q")

@bot.message_handler(commands=['eur'])
def e(m): bot.reply_to(m, signal("EURUSD") or "Ma'lumot yo'q")

@bot.message_handler(commands=['btc'])
def b(m): bot.reply_to(m, signal("BTC") or "Ma'lumot yo'q")

@bot.message_handler(commands=['stock'])
def s(m):
    try:
        sym = m.text.split()[1].upper()
        df = get_data(sym, "60")
        if df is None: return bot.reply_to(m, "Topilmadi")
        score, r, t, liq, ob, pat, a = ai_score(df)
        h = halol(sym)
        bot.reply_to(m, f"🏦 {sym}\nTrend: {t} | RSI: {round(r,1)}\nAI: {score}/6 | {h}\nNarx: {round(df['Close'].iloc[-1],2)}")
    except: bot.reply_to(m, "Masalan: /stock AAPL")

@bot.message_handler(commands=['auto'])
def au(m):
    global AUTO_ON
    txt = m.text.lower()
    if 'off' in txt: AUTO_ON = False
    elif 'on' in txt: AUTO_ON = True
    bot.reply_to(m, f"Auto: {'ON' if AUTO_ON else 'OFF'}")

# ===================== AUTO =====================
def auto_loop():
    while True:
        if AUTO_ON:
            for sym in ["XAUUSD","EURUSD","BTC"]:
                try:
                    s = signal(sym)
                    if s and ("BUY 🟢" in s or "SELL 🔴" in s):
                        bot.send_message(CHAT_ID, s)
                except: pass
        time.sleep(300)

threading.Thread(target=auto_loop, daemon=True).start()
print(f"Bot started for chat {CHAT_ID}")
bot.infinity_polling()