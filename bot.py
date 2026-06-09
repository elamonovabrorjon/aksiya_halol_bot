import os, requests, telebot, time, yfinance as yf
from flask import Flask

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TELEGRAM_TOKEN)
bot.remove_webhook()
time.sleep(2)

app = Flask(__name__)
UZBEK = ["URTS","SQBN","HMKB"]

def uzse(s):
    try: 
        r = requests.get(f"https://uzse.uz/api/trades/{s}", timeout=5).json()
        return f"🇺🇿 {s} | {r.get('last_price','N/A')} so'm"
    except: return "UZSE xato"

def deep_yahoo(sym):
    try:
        t = yf.Ticker(sym)
        info = t.info
        price = info.get('currentPrice',0)
        name = info.get('shortName','')
        pe = info.get('trailingPE',0) or 0
        roe = (info.get('returnOnEquity',0) or 0)*100
        debt_eq = info.get('debtToEquity',0)/100 if info.get('debtToEquity') else 0
        curr = info.get('currentRatio',0) or 0
        
        def c(v,g,b): return "🟢" if v>=g else "🔴" if v<=b else "🟡"
        
        return f"📊 {sym} | ${price}\n{name}\n\nP/E {pe:.1f} {c(30-pe,10,0)}\nROE {roe:.1f}% {c(roe,20,10)}\nQarz {debt_eq:.2f} {c(0.5-debt_eq,0,-0.5)}\nJoriy {curr:.1f} {c(curr,2,1)}"
    except Exception as e:
        return f"❌ {str(e)[:60]}"

@bot.message_handler(commands=['start'])
def s(m):
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📈 Aksiya","🇺🇿 UZSE")
    bot.send_message(m.chat.id, "Bot tayyor ✅", reply_markup=kb)

@bot.message_handler(func=lambda m: True)
def h(m):
    txt = m.text.strip().upper()
    if txt in UZBEK:
        res = uzse(txt)
    else:
        try:
            t = yf.Ticker(txt)
            p = t.info.get('currentPrice')
            n = t.info.get('shortName','')
            res = f"🚨 {txt} | ${p}\n{n}" if p else f"🚨 {txt} topilmadi"
        except:
            res = f"🚨 {txt} topilmadi"
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("📊 Davom etish", callback_data=f"d_{txt}"))
    bot.send_message(m.chat.id, res, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("d_"))
def d(c):
    bot.send_message(c.message.chat.id, deep_yahoo(c.data[2:]))

@app.route('/')
def home(): return "OK"

if __name__ == "__main__":
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=10000)).start()
    while True:
        try: bot.infinity_polling()
        except: time.sleep(5)