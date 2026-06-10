import telebot
import requests
import time
import threading
from datetime import datetime

# ===================== CONFIG =====================
TOKEN = "8781183838:AAFmgLoz6Bb8LlA-50lVAdAbNvhBCWO3sm0"
CHAT_ID = 745170275
FINNHUB = "d842bj1r01qkm5c9vr70d842bj1r01qkm5c9vr7g"

bot = telebot.TeleBot(TOKEN)
AUTO_ON = True

# ===================== FINNHUB =====================
def get_candles(symbol):
    mapping = {"XAUUSD": "OANDA:XAU_USD", "EURUSD": "OANDA:EUR_USD", "BTC": "BINANCE:BTCUSDT"}
    fin = mapping.get(symbol, symbol)

    url = f"https://finnhub.io/api/v1/candle?symbol={fin}&resolution=1&from={int(time.time())-3600*5}&to={int(time.time())}&token={FINNHUB}"
    r = requests.get(url, timeout=10).json()

    if r.get('s')!= 'ok' or len(r['c']) < 30:
        return None

    return {
        'close': r['c'][-60:],
        'high': r['h'][-60:],
        'low': r['l'][-60:],
        'open': r['o'][-60:]
    }

# ===================== INDICATORS (no pandas) =====================
def ema(data, n):
    k = 2/(n+1)
    ema_vals = [data[0]]
    for price in data[1:]:
        ema_vals.append(price*k + ema_vals[-1]*(1-k))
    return ema_vals

def rsi(data, n=14):
    gains, losses = [], []
    for i in range(1, len(data)):
        diff = data[i] - data[i-1]
        gains.append(max(diff,0))
        losses.append(max(-diff,0))

    avg_gain = sum(gains[:n])/n
    avg_loss = sum(losses[:n])/n

    rsis = [50]
    for i in range(n, len(gains)):
        avg_gain = (avg_gain*(n-1) + gains[i])/n
        avg_loss = (avg_loss*(n-1) + losses[i])/n
        rs = avg_gain/(avg_loss+0.0001)
        rsis.append(100 - 100/(1+rs))
    return rsis[-1] if rsis else 50

def atr(high, low, close, n=14):
    trs = []
    for i in range(1, len(high)):
        tr = max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1]))
        trs.append(tr)
    return sum(trs[-n:])/n if len(trs)>=n else trs[-1]

# ===================== SMC =====================
def analyze(symbol):
    d = get_candles(symbol)
    if not d: return None

    c, h, l = d['close'], d['high'], d['low']
    last = c[-1]

    e50 = ema(c, 50)[-1]
    e200 = ema(c, 200)[-1] if len(c) >= 200 else ema(c, 30)[-1]

    trend = "UP" if e50 > e200 else "DOWN"
    r = rsi(c)
    a = atr(h, l, c)

    # Liquidity - swing
    swing_h = max(h[-10:-2])
    swing_l = min(l[-10:-2])
    liq = "ABOVE" if abs(last-swing_h)/last < 0.001 else "BELOW" if abs(last-swing_l)/last < 0.001 else "NONE"

    # OB - simple FVG
    ob = "NONE"
    if l[-1] > h[-3]: ob = "BULLISH"
    elif h[-1] < l[-3]: ob = "BEARISH"

    # Pattern
    body = abs(c[-1]-d['open'][-1])
    rng = h[-1]-l[-1]
    pat = "BULLISH" if c[-1] > d['open'][-1] and body > rng*0.6 else "BEARISH" if c[-1] < d['open'][-1] and body > rng*0.6 else "NONE"

    # Score
    score = 0
    if r < 35 or r > 65: score += 1
    if (trend=="UP" and last>e50) or (trend=="DOWN" and last<e50): score += 1
    if liq!= "NONE": score += 1
    if ob!= "NONE": score += 1
    if pat!= "NONE": score += 1
    if a > 0: score += 1

    # Signal
    sig = "KUTING ⚠️"
    sl = tp1 = tp2 = 0

    if datetime.utcnow().hour not in [14,15,16]: # news filter
        if score >= 4 and ob == "BULLISH" and trend == "UP":
            sig = "BUY 🟢"
            sl = last - a*1.5
            tp1 = last + a*2.25
            tp2 = last + a*4.5
        elif score >= 4 and ob == "BEARISH" and trend == "DOWN":
            sig = "SELL 🔴"
            sl = last + a*1.5
            tp1 = last - a*2.25
            tp2 = last - a*4.5

    return {
        'symbol': symbol, 'price': last, 'trend': trend, 'rsi': r,
        'liq': liq, 'ob': ob, 'pat': pat, 'score': score, 'atr': a,
        'signal': sig, 'sl': sl, 'tp1': tp1, 'tp2': tp2
    }

# ===================== FORMAT =====================
def format_msg(a):
    if not a: return "Ma'lumot yo'q"
    extra = f"\nSL: {a['sl']:.2f} | TP1: {a['tp1']:.2f} | TP2: {a['tp2']:.2f}" if "BUY" in a['signal'] or "SELL" in a['signal'] else ""
    return f"""📊 {a['symbol']} [1m]

Trend: {a['trend']}
Liquidity: {a['liq']}
OB: {a['ob']}
Pattern: {a['pat']}

RSI: {a['rsi']:.1f}
ATR: {a['atr']:.2f}
AI Score: {a['score']}/6

Signal: {a['signal']}{extra}

⏰ {datetime.utcnow().strftime('%H:%M')} UTC"""

# ===================== BOT =====================
@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "🤖 SMC Bot\n/gold\n/eur\n/btc\n/auto on|off")

@bot.message_handler(commands=['gold'])
def gold(m):
    bot.reply_to(m, format_msg(analyze("XAUUSD")))

@bot.message_handler(commands=['eur'])
def eur(m):
    bot.reply_to(m, format_msg(analyze("EURUSD")))

@bot.message_handler(commands=['btc'])
def btc(m):
    bot.reply_to(m, format_msg(analyze("BTC")))

@bot.message_handler(commands=['auto'])
def auto_cmd(m):
    global AUTO_ON
    if 'off' in m.text.lower(): AUTO_ON = False
    else: AUTO_ON = True
    bot.reply_to(m, f"Auto: {'ON' if AUTO_ON else 'OFF'}")

def auto_loop():
    while True:
        if AUTO_ON:
            for s in ["XAUUSD","EURUSD","BTC"]:
                try:
                    a = analyze(s)
                    if a and ("BUY" in a['signal'] or "SELL" in a['signal']):
                        bot.send_message(CHAT_ID, format_msg(a))
                except Exception as e:
                    print(f"Error {s}: {e}")
        time.sleep(300)

threading.Thread(target=auto_loop, daemon=True).start()
print("Bot running...")
bot.infinity_polling()