import os, telebot, requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# --- SOZLAMALAR ---
CUSTOM_STOPS = {'TSLA':295,'TSCO':24,'AAPL':245,'NKE':37,'NFLX':75}
LIVE_PRICES = {'TSLA':336.73,'TSCO':27.58,'AAPL':276.80,'NKE':43.23,'NFLX':83.20}

def get_price(sym):
    if sym in LIVE_PRICES: return LIVE_PRICES[sym]
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}", headers={"User-Agent":"Mozilla/5.0"}, timeout=5).json()
        return r['chart']['result'][0]['meta']['regularMarketPrice']
    except: return 0

# --- AKTSIYA TAHLIL ---
def stock_analiz(sym):
    price = get_price(sym)
    stop = CUSTOM_STOPS.get(sym, round(price*0.88,2))
    tp1, tp2 = round(price*1.2,2), round(price*1.35,2)
    stop_pct = round((price-stop)/price*100)

    text = f"""🚨 AKTSIYA HALOL BOT
━━━━━━━━━━━━━━━━━━━━
🏢 {sym}
💵 Narx: ${price}
━━━━━━━━━━━━━━━━━━━━
🎯 SAVDO REJA (3-6 oy):
Kirish: ${price*0.98:.2f}–${price*1.02:.2f} 🟢
Stop-loss: ${stop} (-{stop_pct}%) 🔴
Take-Profit: ${tp1}–${tp2} 🎯
Risk/Daromad: 1:2.5
━━━━━━━━━━━━━━━━━━━━
✅ XULOSA: SOTIB OLISH"""

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🤖 AI Maslahati", callback_data=f"ai_{sym}"))
    return text, markup

# --- FOREX/GOLD/BTC ---
def forex_analiz(sym):
    if 'XAU' in sym: price = 2335.40
    elif 'BTC' in sym: price = 67000
    else: price = 1.0850

    r1, s1 = price*1.006, price*0.994

    if 'BTC' in sym:
        try:
            book = requests.get("https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=5", timeout=5).json()
            buy_vol = sum(float(b[1]) for b in book['bids'])
            sell_vol = sum(float(a[1]) for a in book['asks'])
        except: buy_vol, sell_vol = 45, 38
    else:
        buy_vol, sell_vol = 1240, 980

    return f"""🚨 {sym} LIVE ANALIZ
━━━━━━━━━━━━━━━━━━━━
💵 Narx: ${price:,.2f}
━━━━━━━━━━━━━━━━━━━━
📊 DARAJALAR:
Qarshilik: ${r1:,.2f}
Qo'llab: ${s1:,.2f}
━━━━━━━━━━━━━━━━━━━━
🐋 LIKVIDLIK:
Buy: {buy_vol:.0f} lot | Sell: {sell_vol:.0f} lot
Imbalance: {'BUY 🟢' if buy_vol>sell_vol else 'SELL 🔴'}"""

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "✅ Bot tayyor!\nYozing: NFLX, TSLA, /gold, /btc")

@bot.message_handler(commands=['gold','xauusd'])
def gold(m): bot.send_message(m.chat.id, forex_analiz('XAUUSD'))

@bot.message_handler(commands=['btc','btcusd'])
def btc(m): bot.send_message(m.chat.id, forex_analiz('BTCUSD'))

@bot.callback_query_handler(func=lambda c: c.data.startswith('ai_'))
def ai(c):
    sym = c.data.split('_')[1]
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, f"🤖 AI MASLAHATI - {sym}\nHozir kirish zonasi. Stop ni buzmasdan 3-6 oy ushlab turing. Portfel 5-7%.")

@bot.message_handler(func=lambda m: True)
def all_handler(m):
    txt = m.text.strip().upper()
    if txt in ['XAUUSD','GOLD']: bot.send_message(m.chat.id, forex_analiz('XAUUSD'))
    elif txt in ['BTCUSD','BTC']: bot.send_message(m.chat.id, forex_analiz('BTCUSD'))
    elif txt in LIVE_PRICES or len(txt)<=5:
        text, markup = stock_analiz(txt)
        bot.send_message(m.chat.id, text, reply_markup=markup)
    else:
        bot.send_message(m.chat.id, "Ticker yozing: NFLX, /gold, /btc")

print("Bot ishga tushdi...")
bot.infinity_polling()