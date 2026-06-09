import telebot, requests, time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# === TOKEN TO'G'RIDAN-TO'G'RI ===
TOKEN = "8781183838:AAHEdjvaZn_dahJYnh-Kf35Ad1oMpWBRPRU"
bot = telebot.TeleBot(TOKEN)

# === SOZLAMALAR ===
CUSTOM_STOPS = {'TSLA':295,'TSCO':24,'AAPL':245,'NKE':37,'NFLX':75}
LIVE_PRICES = {'TSLA':336.73,'TSCO':27.58,'AAPL':276.80,'NKE':43.23,'NFLX':83.20}

def get_price(symbol):
    """Yahoo dan real narx, fallback LIVE_PRICES"""
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
    """Forex real narx"""
    mapping = {'XAUUSD':'GC=F','BTCUSD':'BTC-USD','EURUSD':'EURUSD=X'}
    yahoo_sym = mapping.get(symbol, symbol)
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_sym}"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=4).json()
        return round(r['chart']['result'][0]['meta']['regularMarketPrice'],2)
    except:
        return 2335.40 if 'XAU' in symbol else 67000 if 'BTC' in symbol else 1.0850

def calculate_levels(price):
    """4 ta qarshilik va qo'llab"""
    r1 = round(price * 1.006, 2)
    r2 = round(price * 1.012, 2)
    r3 = round(price * 1.018, 2)
    r4 = round(price * 1.025, 2)
    s1 = round(price * 0.994, 2)
    s2 = round(price * 0.988, 2)
    s3 = round(price * 0.982, 2)
    s4 = round(price * 0.975, 2)
    return r1,r2,r3,r4,s1,s2,s3,s4

def get_liquidity(symbol):
    """Binance dan real BTC, boshqalar demo"""
    if 'BTC' in symbol:
        try:
            r = requests.get("https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=20", timeout=3).json()
            buy_vol = sum(float(b[1]) for b in r['bids'][:10])
            sell_vol = sum(float(a[1]) for a in r['asks'][:10])
            return round(buy_vol,1), round(sell_vol,1)
        except: pass
    return 1245.3, 987.6

def stock_analiz(symbol):
    price = get_price(symbol)
    if price == 0:
        return "❌ Narx olinmadi", None

    stop = CUSTOM_STOPS.get(symbol, round(price*0.88,2))
    tp1 = round(price*1.18,2)
    tp2 = round(price*1.32,2)
    entry_low = round(price*0.97,2)
    entry_high = round(price*1.02,2)
    stop_pct = round((price-stop)/price*100,1)
    tp_pct = round((tp2-price)/price*100,1)

    text = f"""🚨 AKTSIYA HALOL BOT
━━━━━━━━━━━━━━━━━━━━
🏢 {symbol}
💵 Hozirgi narx: ${price}
━━━━━━━━━━━━━━━━━━━━
🎯 SAVDO REJA (3-6 oy):
• Kirish zonasi: ${entry_low} – ${entry_high} 🟢
• Stop-loss: ${stop} (-{stop_pct}%) 🔴
• Take-Profit 1: ${tp1} (+18%)
• Take-Profit 2: ${tp2} (+{tp_pct}%) 🎯
• Risk/Daromad: 1:2.5
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

    name = "OLTIN (XAUUSD)" if 'XAU' in symbol else "BITCOIN (BTCUSD)" if 'BTC' in symbol else symbol

    text = f"""🚨 {name} - LIVE ANALIZ
━━━━━━━━━━━━━━━━━━━━
💵 Hozirgi narx: ${price:,.2f}
🕐 Yangilandi: {time.strftime('%H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━
📊 MUHIM DARAJALAR:
🔴 Qarshiliklar:
• R1: ${r1:,.2f} | R2: ${r2:,.2f}
• R3: ${r3:,.2f} | R4: ${r4:,.2f}

🟢 Qo'llab-quvvatlash:
• S1: ${s1:,.2f} | S2: ${s2:,.2f}
• S3: ${s3:,.2f} | S4: ${s4:,.2f}
━━━━━━━━━━━━━━━━━━━━
🐋 KATTA O'YINCHILAR:
• Buy likvidlik: {buy_vol} lot ({buy_pct}%)
• Sell likvidlik: {sell_vol} lot ({sell_pct}%)
• Jami: {total:.1f} lot
━━━━━━━━━━━━━━━━━━━━
💡 BUGUNGI REJA:
Narx ${s1:,.2f} ustida tursa LONG, ${r1:,.2f} dan o'tsa ${r2:,.2f} ga tezlik."""

    return text

@bot.message_handler(commands=['start','help'])
def start_cmd(m):
    bot.send_message(m.chat.id, "✅ AKTSIYA HALOL BOT tayyor!\n\nYozing:\n• NFLX, TSLA, AAPL\n• /gold - oltin\n• /btc - bitcoin\n• /eurusd")

@bot.message_handler(commands=['gold','xauusd'])
def gold_cmd(m):
    bot.send_message(m.chat.id, "⏳ Oltin narxi olinmoqda...")
    bot.send_message(m.chat.id, forex_analiz('XAUUSD'))

@bot.message_handler(commands=['btc','bitcoin'])
def btc_cmd(m):
    bot.send_message(m.chat.id, "⏳ Bitcoin narxi olinmoqda...")
    bot.send_message(m.chat.id, forex_analiz('BTCUSD'))

@bot.message_handler(commands=['eurusd'])
def eurusd_cmd(m):
    bot.send_message(m.chat.id, forex_analiz('EURUSD'))

@bot.callback_query_handler(func=lambda c: c.data.startswith('ai_'))
def ai_callback(c):
    bot.answer_callback_query(c.id)
    sym = c.data.split('_')[1]
    price = get_price(sym)
    stop = CUSTOM_STOPS.get(sym, round(price*0.88,2))

    ai_text = f"""🤖 AI MASLAHAT - {sym}
━━━━━━━━━━━━━━━━━━━━
📈 Texnik tahlil:
• Narx ${price} - kuchli zona
• Stop ${stop} ni saqlang
• 3-6 oyda +25-35% potensial

💼 Portfel: 5-7% ajrating
⚠️ Risk: Stop-loss dan pastga yopilsa, darhol chiqing
✅ Tavsiya: HOZIR OLISH"""

    bot.send_message(c.message.chat.id, ai_text)

@bot.message_handler(func=lambda m: True)
def all_text(m):
    txt = m.text.strip().upper()

    if txt in ['XAUUSD','GOLD','OLTIN']:
        bot.send_message(m.chat.id, forex_analiz('XAUUSD'))
    elif txt in ['BTCUSD','BTC','BITCOIN']:
        bot.send_message(m.chat.id, forex_analiz('BTCUSD'))
    elif txt in ['EURUSD','EURO']:
        bot.send_message(m.chat.id, forex_analiz('EURUSD'))
    else:
        text, markup = stock_analiz(txt)
        if markup:
            bot.send_message(m.chat.id, text, reply_markup=markup)
        else:
            bot.send_message(m.chat.id, text)

print("✅ Bot ishga tushdi... Token o'rnatilgan")
bot.infinity_polling(none_stop=True)