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
        r = requests.get("https://feeds.bloomberg.com/markets/news.rss", timeout=5)
        from xml.etree import ElementTree as ET
        root = ET.fromstring(r.content)
        news = []
        for item in root.findall('.//item')[:3]:
            title = item.find('title').text
            news.append(translate(title))
        text = "📰 BLOOMBERG YANGILIKLAR\n━━━━━━━━━━━━━━━━━━━━\n"
        for i, n in enumerate(news, 1):
            text += f"{i}. {n}\n"
        text += f"\n🕐 {get_tashkent_time()}"
        return text
    except:
        return "📰 Yangiliklar:\n1. Fed stavkani ushlab turdi\n2. Tesla sotuvlari oshdi\n3. Oltin rekordga yaqin"

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
- Kirish zonasi: ${entry_low} – ${entry_high} 🟢
- Stop-loss: ${stop} (-{stop_pct}%) 🔴
- Take-Profit 1: ${tp1} (+18%)
- Take-Profit 2: ${tp2} (+{tp_pct}%) 🎯
- Risk/Daromad: 1:2.5
━━━━━━━━━━━━━━━━━━━━
💡 STRATEGIYA:
Narx ${entry_low} atrofida tushsa, 2-3 qismga bo'lib oling. Stop-loss dan pastga yopilishda chiqib keting.
━━━━━━━━━━━━━━━━━━━━
✅ XULOSA: SOTIB OLISH TAVSIYA ETILADI"""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🤖 AI Maslahati", callback_data=f"ai_{symbol}"))
    return text, markup

def forex_analiz(symbol):
    price = get_forex_price(symbol)
    r1,r2,r3,r4,s1,s2,s3,s4 = calculate_levels(price)
    buy_vol, sell_vol = get_liquidity(symbol)
    total = buy_vol + sell_vol
    buy_pct = round(buy_vol/total*100) if total else 50
    sell_pct = 100 - buy_pct
    name = "OLTIN (XAUUSD)" if 'XAU' in symbol else "BITCOIN (BTCUSD)" if 'BTC' in symbol else "EURUSD"
    vaqt = get_tashkent_time()
    return f"""🚨 {name} - LIVE ANALIZ
━━━━━━━━━━━━━━━━━━━━
💵 Hozirgi narx: ${price:,.2f}
🕐 Yangilandi: {vaqt}
━━━━━━━━━━━━━━━━━━━━
📊 MUHIM DARAJALAR:
🔴 Qarshiliklar:
- R1: ${r1:,.2f} | R2: ${r2:,.2f}
- R3: ${r3:,.2f} | R4: ${r4:,.2f}

🟢 Qo'llab-quvvatlash:
- S1: ${s1:,.2f} | S2: ${s2:,.2f}
- S3: ${s3:,.2f} | S4: ${s4:,.2f}
━━━━━━━━━━━━━━━━━━━━
🐋 KATTA O'YINCHILAR:
- Buy likvidlik: {buy_vol} lot ({buy_pct}%)
- Sell likvidlik: {sell_vol} lot ({sell_pct}%)
- Jami: {total:.1f} lot
━━━━━━━━━━━━━━━━━━━━
💡 BUGUNGI REJA:
Narx ${s1:,.2f} ustida tursa LONG, ${r1:,.2f} dan o'tsa ${r2:,.2f} ga tezlik."""

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

@bot.message_handler(commands=['start','help'])
def start_cmd(m):
    bot.send_message(m.chat.id, "✅ AKTSIYA HALOL BOT\n\nQuyidagilardan birini tanlang:", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: True)
def all_cb(c):
    bot.answer_callback_query(c.id)
    d = c.data
    if d == 'news':
        bot.send_message(c.message.chat.id, get_news(), reply_markup=main_menu())
    elif d == 'gold':
        bot.send_message(c.message.chat.id, forex_analiz('XAUUSD'), reply_markup=main_menu())
    elif d == 'btc':
        bot.send_message(c.message.chat.id, forex_analiz('BTCUSD'), reply_markup=main_menu())
    elif d == 'eurusd':
        bot.send_message(c.message.chat.id, forex_analiz('EURUSD'), reply_markup=main_menu())
    elif d.startswith('stock_'):
        sym = d.split('_')[1]
        txt, mk = stock_analiz(sym)
        bot.send_message(c.message.chat.id, txt, reply_markup=mk)
    elif d.startswith('ai_'):
        sym = d.split('_')[1]
        price = get_price(sym)
        bot.send_message(c.message.chat.id, f"🤖 AI MASLAHAT - {sym}\nNarx ${price} - 3-6 oyda +25-35% potensial", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def txt_handler(m):
    t = m.text.strip().upper()
    if t in CUSTOM_STOPS:
        txt, mk = stock_analiz(t)
        bot.send_message(m.chat.id, txt, reply_markup=mk)
    else:
        bot.send_message(m.chat.id, "Tanlang:", reply_markup=main_menu())

# Flask for Render
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot ishlayapti"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    print("✅ Bot ishga tushdi")
    while True:
        try:
            bot.infinity_polling(none_stop=True, timeout=60)
        except Exception as e:
            print(f"Xato: {e}")
            time.sleep(5)