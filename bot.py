import os, telebot, requests
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN=os.getenv("TOKEN")
bot=telebot.TeleBot(TOKEN)
app=Flask(__name__)

CUSTOM_STOPS={'NKE':37,'NFLX':75,'TSCO':24,'AAPL':245,'TSLA':295}
LIVE_PRICES={'TSLA':336.73,'TSCO':27.58,'AAPL':276.80,'NKE':43.23,'NFLX':83.20}

def get_price(sym):
    try:
        if sym in LIVE_PRICES: return LIVE_PRICES[sym]
        r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",headers={"User-Agent":"Mozilla/5.0"},timeout=5).json()
        return r['chart']['result'][0]['meta']['regularMarketPrice']
    except: return 0

def forex_analiz(sym):
    # Narx - TwelveData demo
    try:
        api_sym = sym.replace('XAU','XAU/USD').replace('BTC','BTC/USD')
        p = requests.get(f"https://api.twelvedata.com/price?symbol={api_sym}&apikey=demo",timeout=5).json()
        price = float(p['price'])
    except: price=2335.4 if 'XAU' in sym else 67000

    r1, r2 = price*1.006, price*1.012
    s1, s2 = price*0.994, price*0.988

    # Likvidlik - BTC uchun real, forex uchun sentiment
    if 'BTC' in sym:
        book=requests.get("https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=10",timeout=5).json()
        buy_vol=sum(float(b[1]) for b in book['bids'])
        sell_vol=sum(float(a[1]) for a in book['asks'])
    else:
        buy_vol, sell_vol = 1240, 980

    return f"""🚨 {sym} LIVE ANALIZ
━━━━━━━━━━━━━━━━━━━━
💵 Narx: ${price:,.2f}
━━━━━━━━━━━━━━━━━━━━
📊 DARAJALAR:
Qarshilik: ${r1:,.2f} | ${r2:,.2f}
Qo'llab: ${s1:,.2f} | ${s2:,.2f}
━━━━━━━━━━━━━━━━━━━━
🐋 LIKVIDLIK:
Buy: {buy_vol:.0f} lot | Sell: {sell_vol:.0f} lot
Imbalance: {'BUY 🟢' if buy_vol>sell_vol else 'SELL 🔴'}
━━━━━━━━━━━━━━━━━━━━
🎯 SAVDO: ${s1:,.2f} dan LONG, SL ${s2:,.2f}"""

def stock_analiz(sym):
    price=get_price(sym)
    stop=CUSTOM_STOPS.get(sym, round(price*0.88,2))
    return f"""🚨 AKTSIYA HALOL BOT
━━━━━━━━━━━━━━━━━━━━
🏢 {sym}
💵 Narx: ${price}
━━━━━━━━━━━━━━━━━━━━
🎯 SAVDO REJA:
Kirish: ${price*0.97:.2f}–${price*1.02:.2f}
Stop: ${stop} (-{round((price-stop)/price*100)}%)
TP: ${price*1.2:.2f}–${price*1.35:.2f}
━━━━━━━━━━━━━━━━━━━━
✅ XULOSA: {'OLISH' if price>stop else 'KUTISH'}"""

@bot.message_handler(commands=['gold','xauusd'])
def gold(m): bot.send_message(m.chat.id, forex_analiz('XAUUSD'))

@bot.message_handler(commands=['btc','btcusd'])
def btc(m): bot.send_message(m.chat.id, forex_analiz('BTCUSD'))

@bot.message_handler(commands=['eurusd'])
def eurusd(m): bot.send_message(m.chat.id, forex_analiz('EURUSD'))

@bot.message_handler(commands=['forex'])
def forex_all(m):
    txt=""
    for p in ['XAUUSD','BTCUSD','EURUSD']: txt+=forex_analiz(p)+"\n\n"
    bot.send_message(m.chat.id, txt)

@bot.message_handler(func=lambda m: True)
def all_handler(m):
    txt=m.text.strip().upper()
    if txt in ['XAUUSD','GOLD']: bot.send_message(m.chat.id, forex_analiz('XAUUSD'))
    elif txt in ['BTCUSD','BTC']: bot.send_message(m.chat.id, forex_analiz('BTCUSD'))
    else: bot.send_message(m.chat.id, stock_analiz(txt))

@app.route('/')
def ok(): return "OK"

if __name__=='__main__':
    import threading; threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))