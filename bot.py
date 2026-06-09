import os, requests, telebot, time
from flask import Flask

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FMP_KEY = os.getenv("FMP_API_KEY")
CHAT_ID = os.getenv("CHAT_ID")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
# 409 conflict ni oldini oladi
bot.remove_webhook()
time.sleep(2)

app = Flask(__name__)

UZBEK_TICKERS = ["URTS","SQBN","HMKB","UZMK","QZSM"]

def get_uzse_price(symbol):
    try:
        r = requests.get(f"https://uzse.uz/api/trades/{symbol}", timeout=10)
        return f"🇺🇿 {symbol} | {r.json().get('last_price','N/A')} so'm"
    except: return "UZSE xato"

def get_fmp_deep(symbol):
    base = "https://financialmodelingprep.com/api/v3"
    try:
        # 1. Profile
        pr = requests.get(f"{base}/profile/{symbol}?apikey={FMP_KEY}", timeout=10)
        if pr.status_code!= 200:
            return f"❌ FMP {pr.status_code}. Key tekshiring."
        data = pr.json()
        if not data or isinstance(data, dict) and "Error" in str(data):
            return f"❌ FMP javob: {data}"
        p = data[0]

        # 2. Ratios
        rat = requests.get(f"{base}/ratios-ttm/{symbol}?apikey={FMP_KEY}", timeout=10).json()
        r = rat[0] if rat else {}

        pe = r.get('peRatioTTM',0)
        roe = r.get('returnOnEquityTTM',0)*100
        debt_eq = r.get('debtEquityRatioTTM',0)
        curr = r.get('currentRatioTTM',0)

        def col(v, good, bad): return "🟢" if v>=good else "🔴" if v<=bad else "🟡"

        txt = f"📊 {symbol} | ${p.get('price',0)}\n{p.get('companyName','')}\n\n"
        txt += f"P/E {pe:.1f} {col(30-pe,10,0)}\n"
        txt += f"ROE {roe:.1f}% {col(roe,20,10)}\n"
        txt += f"Qarz/Kap {debt_eq:.2f} {col(0.5-debt_eq,0,-0.5)}\n"
        txt += f"Joriy {curr:.1f} {col(curr,2,1)}\n"
        return txt
    except Exception as e:
        return f"❌ Xato: {str(e)[:80]}"

@bot.message_handler(commands=['start'])
def start(m):
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📈 Aksiya","🇺🇿 UZSE")
    kb.add("📊 Raqobat","📖 Lug'at")
    bot.send_message(m.chat.id, "Aksiya Halol Bot ✅", reply_markup=kb)

@bot.message_handler(func=lambda m: True)
def handle(m):
    txt = m.text.strip().upper()
    if txt in ["📈 AKSIYA","🇺🇿 UZSE","📊 RAQOBAT","📖 LUG'AT"]: return

    if txt in UZBEK_TICKERS:
        res = get_uzse_price(txt)
    else:
        try:
            url = f"https://financialmodelingprep.com/api/v3/profile/{txt}?apikey={FMP_KEY}"
            r = requests.get(url, timeout=10)
            if r.status_code!= 200:
                res = f"❌ FMP {r.status_code}"
            else:
                data = r.json()
                if not data:
                    res = f"🚨 {txt} topilmadi"
                else:
                    p = data[0]
                    res = f"🚨 {p['symbol']} | ${p.get('price',0)}\n{p.get('companyName','')}"
        except Exception as e:
            res = f"❌ Xato: {str(e)[:60]}"

    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("📊 Davom etish", callback_data=f"deep_{txt}"))
    bot.send_message(m.chat.id, res, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("deep_"))
def deep(c):
    sym = c.data.split("_")[1]
    res = get_fmp_deep(sym)
    bot.send_message(c.message.chat.id, res)

@app.route('/')
def home(): return "Bot ishlayapti"

if __name__ == "__main__":
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=10000)).start()
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f"Polling xato: {e}")
            time.sleep(5)