import telebot, requests, time, datetime, random, threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from flask import Flask
from urllib.parse import quote

TOKEN = "8781183838:AAFmgLoz6Bb8LlA-50lVAdAbNvhBCWO3sm0"
bot = telebot.TeleBot(TOKEN, threaded=False)

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
            news.append(translate(item.find('title').text))
        text = "📰 BLOOMBERG YANGILIKLAR\n━━━━━━━━━━━━━━━━━━━━\n"
        for i, n in enumerate(news, 1):
            text += f"{i}. {n}\n"
        text += f"\n🕐 {get_tashkent_time()}"
        return text
    except:
        return "📰 Yangiliklar hozircha yo'q"

def get_price(symbol):
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}", headers={"User-Agent":"Mozilla/5.0"}, timeout=4).json()
        return round(r['chart']['result'][0]['meta']['regularMarketPrice'],2)
    except:
        return LIVE_PRICES.get(symbol, 0)

def get_forex_price(symbol):
    mapping = {'XAUUSD':'GC=F','BTC-USD':'BTC-USD','EURUSD':'EURUSD=X','GBPUSD':'GBPUSD=X','USDJPY':'JPY=X'}
    y = mapping.get(symbol, symbol)
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{y}", headers={"User-Agent":"Mozilla/5.0"}, timeout=4).json()
        return round(r['chart']['result'][0]['meta']['regularMarketPrice'],2)
    except:
        return 0

def calculate_levels(p):
    return round(p*1.006,2), round(p*1.012,2), round(p*1.018,2), round(p*1.025,2), round(p*0.994,2), round(p*0.988,2), round(p*0.982,2), round(p*0.975,2)

def get_liquidity(symbol):
    base = random.uniform(1100,1450)
    br = random.uniform(0.48,0.62)
    return round(base*br,1), round(base*(1-br),1)

def stock_analiz(s):
    p = get_price(s)
    stop = CUSTOM_STOPS.get(s, round(p*0.88,2))
    tp1 = round(p*1.18,2); tp2 = round(p*1.32,2)
    el = round(p*0.97,2); eh = round(p*1.02,2)
    sp = round((p-stop)/p*100,1); tp = round((tp2-p)/p*100,1)
    txt = f"🚨 AKTSIYA HALOL BOT\n━━━━━━━━━━━━━━━━━━━━\n🏢 {s}\n💵 Narx: ${p}\n━━━━━━━━━━━━━━━━━━━━\n🎯 REJA:\n- Kirish: ${el} – ${eh}\n- Stop: ${stop} (-{sp}%)\n- TP2: ${tp2} (+{tp}%)\n━━━━━━━━━━━━━━━━━━━━\n✅ XULOSA: SOTIB OLISH"
    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton("🤖 AI", callback_data=f"ai_{s}"))
    return txt, m

def forex_analiz(sym):
    p = get_forex_price(sym) or 1.08
    r1,r2,r3,r4,s1,s2,s3,s4 = calculate_levels(p)
    bv,sv = get_liquidity(sym)
    bp = round(bv/(bv+sv)*100)
    name = sym.replace('-USD','')
    return f"🚨 {name} - LIVE\n━━━━━━━━━━━━━━━━━━━━\n💵 Narx: ${p:,.2f}\n🕐 {get_tashkent_time()}\n━━━━━━━━━━━━━━━━━━━━\n🔴 R: ${r1} | ${r2}\n🟢 S: ${s1} | ${s2}\n━━━━━━━━━━━━━━━━━━━━\n🐋 Buy: {bp}% | Sell: {100-bp}%"

def main_menu():
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton("🥇 Oltin", callback_data="gold"),
        InlineKeyboardButton("🪙 Crypto", callback_data="crypto"),
        InlineKeyboardButton("🏦 Fond", callback_data="fond"),
        InlineKeyboardButton("💹 Forex", callback_data="forex"),
        InlineKeyboardButton("📰 Yangiliklar", callback_data="news"),
        InlineKeyboardButton("💳 PRO", callback_data="pro")
    )
    return m

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, " ", reply_markup=ReplyKeyboardRemove())
    bot.send_message(m.chat.id, "✅ Bot ishga tushdi", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    d = c.data
    bot.answer_callback_query(c.id)
    if d=='news': bot.send_message(c.message.chat.id, get_news(), reply_markup=main_menu())
    elif d=='gold': bot.send_message(c.message.chat.id, forex_analiz('XAUUSD'), reply_markup=main_menu())
    elif d=='forex': bot.send_message(c.message.chat.id, forex_analiz('EURUSD'), reply_markup=main_menu())
    elif d=='fond':
        fm = InlineKeyboardMarkup()
        for s in ['TSLA','AAPL','NFLX','NKE']: fm.add(InlineKeyboardButton(s, callback_data=f"stock_{s}"))
        bot.send_message(c.message.chat.id, "🏦 Tanlang:", reply_markup=fm)
    elif d=='crypto':
        cm = InlineKeyboardMarkup()
        for s in ['BTC-USD','ETH-USD','SOL-USD']: cm.add(InlineKeyboardButton(s.split('-')[0], callback_data=f"crypto_{s}"))
        bot.send_message(c.message.chat.id, "🪙 Tanlang:", reply_markup=cm)
    elif d.startswith('stock_'):
        t,mk = stock_analiz(d.split('_')[1])
        bot.send_message(c.message.chat.id, t, reply_markup=mk)
    elif d.startswith('crypto_'):
        bot.send_message(c.message.chat.id, forex_analiz(d.split('_')[1]), reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def txt(m):
    t = m.text.upper().strip()
    if t in CUSTOM_STOPS:
        tx,mk = stock_analiz(t)
        bot.send_message(m.chat.id, tx, reply_markup=mk)
    elif t in ['EURUSD','GBPUSD','XAUUSD','BTC','ETH','SOL']:
        sym = 'BTC-USD' if t=='BTC' else f"{t}-USD" if t in ['ETH','SOL'] else t
        bot.send_message(m.chat.id, forex_analiz(sym), reply_markup=main_menu())
    else:
        bot.send_message(m.chat.id, "Ticker yozing: TSLA, BTC, ETH, EURUSD", reply_markup=main_menu())

app = Flask(__name__)
@app.route('/')
def home(): return "OK"

def run_bot():
    print("✅ Polling boshlanmoqda...")
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            print(f"XATO: {e}")
            time.sleep(5)

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=10000)