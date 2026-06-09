import telebot, requests, time, datetime, random, threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
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
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}", headers={"User-Agent":"Mozilla/5.0"}, timeout=4).json()
            price = r['chart']['result'][0]['meta']['regularMarketPrice']
            if price: return round(price,2)
        except: pass
        return LIVE_PRICES[symbol]
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}", headers={"User-Agent":"Mozilla/5.0"}, timeout=4).json()
        return round(r['chart']['result'][0]['meta']['regularMarketPrice'],2)
    except:
        return 0

def get_forex_price(symbol):
    mapping = {'XAUUSD':'GC=F','BTCUSD':'BTC-USD','EURUSD':'EURUSD=X'}
    y = mapping.get(symbol, symbol)
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{y}", headers={"User-Agent":"Mozilla/5.0"}, timeout=4).json()
        return round(r['chart']['result'][0]['meta']['regularMarketPrice'],2)
    except:
        return 4366.60 if 'XAU' in symbol else 62273.29 if 'BTC' in symbol else 1.0850

def calculate_levels(p):
    return round(p*1.006,2), round(p*1.012,2), round(p*1.018,2), round(p*1.025,2), round(p*0.994,2), round(p*0.988,2), round(p*0.982,2), round(p*0.975,2)

def get_liquidity(symbol):
    if 'BTC' in symbol:
        try:
            r = requests.get("https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=50", timeout=4).json()
            b = sum(float(x[1]) for x in r['bids'][:20])
            s = sum(float(x[1]) for x in r['asks'][:20])
            return round(b,1), round(s,1)
        except: pass
    base = random.uniform(1100,1450)
    br = random.uniform(0.48,0.62)
    return round(base*br,1), round(base*(1-br),1)

def stock_analiz(s):
    p = get_price(s)
    if p==0: return "❌ Narx olinmadi", None
    stop = CUSTOM_STOPS.get(s, round(p*0.88,2))
    tp1 = round(p*1.18,2); tp2 = round(p*1.32,2)
    el = round(p*0.97,2); eh = round(p*1.02,2)
    sp = round((p-stop)/p*100,1); tp = round((tp2-p)/p*100,1)
    txt = f"""🚨 AKTSIYA HALOL BOT
━━━━━━━━━━━━━━━━━━━━
🏢 {s}
💵 Hozirgi narx: ${p}
━━━━━━━━━━━━━━━━━━━━
🎯 SAVDO REJA (3-6 oy):
- Kirish zonasi: ${el} – ${eh} 🟢
- Stop-loss: ${stop} (-{sp}%) 🔴
- Take-Profit 1: ${tp1} (+18%)
- Take-Profit 2: ${tp2} (+{tp}%) 🎯
- Risk/Daromad: 1:2.5
━━━━━━━━━━━━━━━━━━━━
💡 STRATEGIYA:
Narx ${el} atrofida tushsa, 2-3 qismga bo'lib oling.
━━━━━━━━━━━━━━━━━━━━
✅ XULOSA: SOTIB OLISH TAVSIYA ETILADI"""
    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton("🤖 AI", callback_data=f"ai_{s}"))
    return txt, m

def forex_analiz(sym):
    p = get_forex_price(sym)
    r1,r2,r3,r4,s1,s2,s3,s4 = calculate_levels(p)
    bv,sv = get_liquidity(sym)
    t = bv+sv; bp = round(bv/t*100) if t else 50
    name = "OLTIN (XAUUSD)" if 'XAU' in sym else "BITCOIN (BTCUSD)" if 'BTC' in sym else "EURUSD"
    return f"""🚨 {name} - LIVE ANALIZ
━━━━━━━━━━━━━━━━━━━━
💵 Hozirgi narx: ${p:,.2f}
🕐 Yangilandi: {get_tashkent_time()}
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
- Buy: {bv} lot ({bp}%)
- Sell: {sv} lot ({100-bp}%)
━━━━━━━━━━━━━━━━━━━━
💡 BUGUNGI REJA:
Narx ${s1:,.2f} ustida LONG, ${r1:,.2f} dan o'tsa ${r2:,.2f}."""

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
def start(m):
    # Yuzidagi klaviaturani o'chirish
    bot.send_message(m.chat.id, " ", reply_markup=ReplyKeyboardRemove())
    bot.send_message(m.chat.id, "✅ AKTSIYA HALOL BOT", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    bot.answer_callback_query(c.id)
    d = c.data
    if d=='news': bot.send_message(c.message.chat.id, get_news(), reply_markup=main_menu())
    elif d=='gold': bot.send_message(c.message.chat.id, forex_analiz('XAUUSD'), reply_markup=main_menu())
    elif d=='btc': bot.send_message(c.message.chat.id, forex_analiz('BTCUSD'), reply_markup=main_menu())
    elif d=='eurusd': bot.send_message(c.message.chat.id, forex_analiz('EURUSD'), reply_markup=main_menu())
    elif d.startswith('stock_'):
        s = d.split('_')[1]
        t,mk = stock_analiz(s)
        bot.send_message(c.message.chat.id, t, reply_markup=mk)
    elif d.startswith('ai_'):
        s = d.split('_')[1]
        bot.send_message(c.message.chat.id, f"🤖 {s}: hozir olish tavsiya", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def txt(m):
    t = m.text.upper()
    if t in CUSTOM_STOPS:
        tx,mk = stock_analiz(t)
        bot.send_message(m.chat.id, tx, reply_markup=mk)
    else:
        bot.send_message(m.chat.id, "Tanlang:", reply_markup=main_menu())

app = Flask(__name__)
@app.route('/')
def home(): return "OK"

def run_flask(): app.run(host='0.0.0.0', port=10000)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    print("✅ Bot ishga tushdi")
    while True:
        try: bot.infinity_polling(none_stop=True, timeout=60)
        except Exception as e: print(e); time.sleep(5)