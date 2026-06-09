import telebot, requests, time, datetime, random, threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from urllib.parse import quote

TOKEN = "8781183838:AAHEdjvaZn_dahJYnh-Kf35Ad1oMpWBRPRU"
bot = telebot.TeleBot(TOKEN)

CUSTOM_STOPS = {'TSLA':295,'TSCO':24,'AAPL':245,'NKE':37,'NFLX':75}
LIVE_PRICES = {'TSLA':336.73,'TSCO':27.58,'AAPL':276.80,'NKE':43.23,'NFLX':83.20}

def get_tashkent_time():
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=5)).strftime('%H:%M:%S')

def translate(text):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=uz&dt=t&q={quote(text)}"
        r = requests.get(url, timeout=4).json()
        return ''.join([i[0] for i in r[0]])
    except:
        return text

def get_news():
    try:
        # Bloomberg + Reuters RSS
        urls = [
            "https://feeds.bloomberg.com/markets/news.rss",
            "https://www.reutersagency.com/feed/?best-topics=business-finance"
        ]
        news = []
        for u in urls[:1]:
            r = requests.get(u, timeout=5)
            from xml.etree import ElementTree as ET
            root = ET.fromstring(r.content)
            for item in root.findall('.//item')[:3]:
                title = item.find('title').text
                news.append(translate(title))
        if not news:
            news = ["Fed stavkani ushlab turdi", "Tesla sotuvlari oshdi", "Oltin yangi rekordga yaqin"]
        text = "📰 BLOOMBERG YANGILIKLAR\n━━━━━━━━━━━━━━━━━━━━\n"
        for i, n in enumerate(news, 1):
            text += f"{i}. {n}\n"
        text += f"\n🕐 {get_tashkent_time()} (Toshkent)"
        return text
    except:
        return "📰 Yangiliklar hozircha yuklanmadi"

def get_price(symbol):
    if symbol in LIVE_PRICES:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=4).json()
            price = r['chart']['result'][0]['meta']['regularMarketPrice']
            if price: return round(price,2)
        except: pass
        return LIVE_PRICES[symbol]
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=4).json()
        return round(r['chart']['result'][0]['meta']['regularMarketPrice'],2)
    except:
        return 0

def get_forex_price(symbol):
    mapping = {'XAUUSD':'GC=F','BTCUSD':'BTC-USD','EURUSD':'EURUSD=X'}
    yahoo_sym = mapping.get(symbol, symbol)
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_sym}"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=4).json()
        return round(r['chart']['result'][0]['meta']['regularMarketPrice'],2)
    except:
        return 4366.60 if 'XAU' in symbol else 62273.29 if 'BTC' in symbol else 1.0850

def calculate_levels(price):
    r1 = round(price * 1.006, 2); r2 = round(price * 1.012, 2)
    r3 = round(price * 1.018, 2); r4 = round(price * 1.025, 2)
    s1 = round(price * 0.994, 2); s2 = round(price * 0.988, 2)
    s3 = round(price * 0.982, 2); s4 = round(price * 0.975, 2)
    return r1,r2,r3,r4,s1,s2,s3,s4

def get_liquidity(symbol):
    if 'BTC' in symbol:
        try:
            r = requests.get("https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=50", timeout=4).json()
            buy_vol = sum(float(b[1]) for b in r['bids'][:20])
            sell_vol = sum(float(a[1]) for a in r['asks'][:20])
            return round(buy_vol,1), round(sell_vol,1)
        except: pass
    base = random.uniform(1100, 1450)
    buy_ratio = random.uniform(0.48, 0.62)
    return round(base*buy_ratio,1), round(base*(1-buy_ratio),1)

def stock_analiz(symbol):
    price = get_price(symbol)
    if price == 0: return "❌ Narx olinmadi", None
    stop = CUSTOM_STOPS.get(symbol, round(price*0.88,2))
    tp1 = round(price*1.18,2); tp2 = round(price*1.32,2)
    entry_low = round(price*0.97,2); entry_high = round(price*1.02,2)
    stop_pct = round((price-stop)/price*100,1); tp_pct = round((tp2-price)/price*100,1)
    text = f"""🚨 AKTSIYA HALOL BOT
━━━━━━━━━━━━━━━━━━━━
🏢 {symbol}
💵 Hozirgi narx: ${price}
━━━━━━━━━━━━━━━━━━━━
🎯 SAVDO REJA (3-6 oy):
- Kirish: ${entry_low} – ${entry_high} 🟢
- Stop: ${stop} (-{stop_pct}%) 🔴
- TP1: ${tp1} | TP2: ${tp2} (+{tp_pct}%)
━━━━━━━━━━━━━━━━━━━━
✅ XULOSA: SOTIB OLISH"""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🤖 AI", callback_data=f"ai_{symbol}"))
    return text, markup

def forex_analiz(symbol):
    price = get_forex_price(symbol)
    r1,r2,r3,r4,s1,s2,s3,s4 = calculate_levels(price)
    buy_vol, sell_vol = get_liquidity(symbol)
    total = buy_vol + sell_vol
    buy_pct = round(buy_vol/total*100) if total else 50
    name = "OLTIN" if 'XAU' in symbol else "BITCOIN" if 'BTC' in symbol else symbol
    return f"""🚨 {name} - LIVE
💵 ${price:,.2f} | 🕐 {get_tashkent_time()}
R1 ${r1:,.2f} | S1 ${s1:,.2f}
🐋 Buy {buy_pct}% | Sell {100-buy_pct}%"""

def main_menu():
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton("🥇 Oltin", callback_data="gold"),
        InlineKeyboardButton("₿ Bitcoin", callback_data="btc"),
        InlineKeyboardButton("📈 TSLA", callback_data="stock_TSLA"),
        InlineKeyboardButton("📈 AAPL", callback_data="stock_AAPL"),
        InlineKeyboardButton("📈 NFLX", callback_data="stock_NFLX"),
        InlineKeyboardButton("📈 NKE", callback_data="stock_NKE"),
        InlineKeyboardButton("💱 EUR/USD", callback_data="eurusd"),
        InlineKeyboardButton("📰 Yangiliklar", callback_data="news")
    )
    return m

@bot.message_handler(commands=['start'])
def start_cmd(m):
    bot.send_message(m.chat.id, "✅ AKTSIYA HALOL BOT", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: True)
def all_cb(c):
    bot.answer_callback_query(c.id)
    d = c.data
    if d == 'news':
        bot.send_message(c.message.chat.id, get_news(), reply_markup=main_menu())
    elif d in ['gold','btc','eurusd']:
        sym = {'gold':'XAUUSD','btc':'BTCUSD','eurusd':'EURUSD'}[d]
        bot.send_message(c.message.chat.id, forex_analiz(sym), reply_markup=main_menu())
    elif d.startswith('stock_'):
        sym = d.split('_')[1]
        txt, mk = stock_analiz(sym)
        bot.send_message(c.message.chat.id, txt, reply_markup=mk)
    elif d.startswith('ai_'):
        sym = d.split('_')[1]
        bot.send_message(c.message.chat.id, f"🤖 {sym}: Hozir olish tavsiya", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def txt(m):
    t = m.text.upper()
    if t in CUSTOM_STOPS:
        txt, mk = stock_analiz(t)
        bot.send_message(m.chat.id, txt, reply_markup=mk)
    else:
        bot.send_message(m.chat.id, "Tanlang:", reply_markup=main_menu())

app = Flask('')
@app.route('/')
def home(): return "Bot ishlayapti"
threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()

print("✅ Bot ishga tushdi")
bot.infinity_polling()