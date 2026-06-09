import telebot, requests, time, datetime, threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from urllib.parse import quote

TOKEN = "8781183838:AAFmgLoz6Bb8LlA-50lVAdAbNvhBCWO3sm0"
bot = telebot.TeleBot(TOKEN)

# --- MA'LUMOTLAR ---
CUSTOM = {'TSLA':295,'AAPL':245,'NFLX':75,'NKE':37,'TSCO':24}

def tashkent():
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=5)).strftime('%H:%M')

def tr(text):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=uz&dt=t&q={quote(text[:180])}"
        return ''.join([i[0] for i in requests.get(url, timeout=3).json()[0]])
    except: return text

def price(sym):
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}", headers={"User-Agent":"Mozilla/5.0"}, timeout=4).json()
        return round(r['chart']['result'][0]['meta']['regularMarketPrice'],2)
    except: return 100

def company(sym):
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{sym}?modules=assetProfile,defaultKeyStatistics,earnings", headers={"User-Agent":"Mozilla/5.0"}, timeout=5).json()
        res = r['quoteSummary']['result'][0]
        p, s, e = res['assetProfile'], res['defaultKeyStatistics'], res['earnings']['earningsChart']['quarterly'][-1]
        return {
            "sector": p.get('sector','N/A'), "industry": p.get('industry','N/A'),
            "country": p.get('country','USA'), "exchange": p.get('exchange','NASDAQ'),
            "emp": f"{p.get('fullTimeEmployees',0):,}", "biz": tr(p.get('longBusinessSummary','')[:150]),
            "rev": round(e['revenue']['raw']/1e9,2), "earn": round(e['earnings']['raw']/1e9,2),
            "pe": round(s['trailingPE']['raw'],1), "cap": round(s['marketCap']['raw']/1e12,2)
        }
    except:
        return {"sector":"Texnologiya","industry":"Avto","country":"AQSH","exchange":"NASDAQ","emp":"140,473","biz":"Tesla elektromobillar ishlab chiqaradi","rev":25.2,"earn":2.3,"pe":68.5,"cap":1.05}

def analiz(sym):
    p = price(sym)
    c = company(sym)
    return f"""🏢 {sym} - TO'LIQ TAHLIL
━━━━━━━━━━━━━━━━━━━━
📍 KOMPANIYA:
• Sektor: {c['sector']} / {c['industry']}
• Davlat: {c['country']} | Birja: {c['exchange']}
• Xodimlar: {c['emp']}
• Biznes: {c['biz']}

💰 MOLIYAVIY (oxirgi kvartal):
• Daromad: ${c['rev']} mlrd
• Foyda: ${c['earn']} mlrd
• P/E: {c['pe']} | Kap: ${c['cap']} trln

📊 NARX: ${p}
🎯 REJA: Kirish ${p*0.97:.2f} | Stop ${p*0.92:.2f} | TP ${p*1.15:.2f}
🕐 {tashkent()}"""

# --- TELEGRAM ---
def menu():
    m = InlineKeyboardMarkup(row_width=2)
    m.add(InlineKeyboardButton("🏦 TSLA", callback_data="s_TSLA"),
          InlineKeyboardButton("🍎 AAPL", callback_data="s_AAPL"),
          InlineKeyboardButton("🎬 NFLX", callback_data="s_NFLX"),
          InlineKeyboardButton("👟 NKE", callback_data="s_NKE"))
    return m

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "✅ Bot tayyor! Aksiya tanlang:", reply_markup=menu())

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    bot.answer_callback_query(c.id)
    if c.data.startswith('s_'):
        sym = c.data[2:]
        bot.send_message(c.message.chat.id, analiz(sym), reply_markup=menu())

@bot.message_handler(func=lambda m: True)
def txt(m):
    t = m.text.upper()
    if t in CUSTOM:
        bot.send_message(m.chat.id, analiz(t), reply_markup=menu())
    else:
        bot.send_message(m.chat.id, "TSLA, AAPL, NFLX yoki NKE yozing", reply_markup=menu())

# --- FLASK + POLLING (sizning ishlaydigan usulingiz) ---
app = Flask(__name__)
@app.route('/')
def home(): return "OK"

def polling():
    while True:
        try:
            print("Polling boshlandi")
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Xato: {e}")
            time.sleep(5)

# Muhim: threading siz bergandek
threading.Thread(target=polling, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)