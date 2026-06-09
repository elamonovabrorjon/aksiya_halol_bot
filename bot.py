import os, requests, telebot
from flask import Flask
from threading import Thread
import time
from bs4 import BeautifulSoup

TOKEN = os.getenv("TELEGRAM_TOKEN")
FMP_KEY = os.getenv("FMP_API_KEY")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# UZSE ~120 ta ticker
UZBEK_TICKERS = ["URTS","SQBN","HMKB","IPKY","QZSM","UZMK","AGMK","ALKB","ASBU","TRSB","KSCM","UTSY","KUMZ","KVTS","CHSM","DORI","GLTR","ITLV","OTSU","QAME","QMBN","QZSS","SCDS","SFTS","SREV","TEPS","TKVK","TSMK","UGSU","UYPL","UZCR","UZDA","UZEX","UZPS","UZTL","VKTP","XNFS","ZLTK","A007800","A028100","A054500","A067820","A074300","A091920","A096740","A102460","A105560","A110820","A114450","A121140"]

GLOBAL_SCREEN = ["NKE","AAPL","MSFT","KO","PEP","JNJ","PG","TSLA","NVDA","AMD","INTC","WMT"]

def svetofor(val, good, medium, reverse=False):
    """reverse=True bo'lsa kichik yaxshi (P/E, qarz)"""
    if reverse:
        if val <= good: return "🟢"
        elif val <= medium: return "🟡"
        else: return "🔴"
    else:
        if val >= good: return "🟢"
        elif val >= medium: return "🟡"
        else: return "🔴"

def get_fmp_deep(symbol):
    base = "https://financialmodelingprep.com/api/v3"
    try:
        p = requests.get(f"{base}/profile/{symbol}?apikey={FMP_KEY}", timeout=10).json()[0]
        r = requests.get(f"{base}/ratios-ttm/{symbol}?apikey={FMP_KEY}", timeout=10).json()[0]
        m = requests.get(f"{base}/key-metrics-ttm/{symbol}?apikey={FMP_KEY}", timeout=10).json()[0]
        inc = requests.get(f"{base}/income-statement/{symbol}?limit=1&apikey={FMP_KEY}", timeout=10).json()[0]
        bal = requests.get(f"{base}/balance-sheet-statement/{symbol}?limit=1&apikey={FMP_KEY}", timeout=10).json()[0]
        cf = requests.get(f"{base}/cash-flow-statement/{symbol}?limit=1&apikey={FMP_KEY}", timeout=10).json()[0]

        # Qarz
        short_debt = bal.get('shortTermDebt', 0)
        long_debt = bal.get('longTermDebt', 0)
        total_debt = bal.get('totalDebt', short_debt + long_debt)
        short_pct = (short_debt/total_debt*100) if total_debt else 0
        long_pct = (long_debt/total_debt*100) if total_debt else 0

        # Svetofor
        pe = r.get('peRatioTTM',0)
        pe_c = svetofor(pe, 20, 30, True)
        roe = r.get('returnOnEquityTTM',0)*100
        roe_c = svetofor(roe, 20, 15)
        roa = r.get('returnOnAssetsTTM',0)*100
        roa_c = svetofor(roa, 10, 5)
        pm = r.get('netProfitMarginTTM',0)*100
        pm_c = svetofor(pm, 15, 8)
        de = r.get('debtEquityRatioTTM',0)
        de_c = svetofor(de, 0.5, 1.0, True)
        cr = r.get('currentRatioTTM',0)
        cr_c = svetofor(cr, 2, 1.5)

        return f"""📊 CHUQUR TAHLIL: {symbol} {p.get('companyName','')}
━━━━━━━━━━━━━━━━━━━━
💰 FOYDALILIK:
- Sof foyda marjasi: {pm:.2f}% {pm_c}
- Operatsion marja: {r.get('operatingProfitMarginTTM',0)*100:.2f}%

👔 BOSHQARUV:
- ROA: {roa:.2f}% {roa_c}
- ROE: {roe:.2f}% {roe_c}

📈 DAROMAD:
- Tushum (yillik): {inc.get('revenue',0)/1e9:.2f} mlrd $
- EPS: {m.get('netIncomePerShareTTM',0):.2f} $
- P/E: {pe:.1f} {pe_c}

🏦 BALANS:
- Naqd: {bal.get('cashAndCashEquivalents',0)/1e9:.2f} mlrd $
- JAMI QARZ: {total_debt/1e9:.2f} mlrd $
  ├─ Qisqa (<1y): {short_debt/1e9:.2f} ({short_pct:.0f}%)
  └─ Uzoq (>1y): {long_debt/1e9:.2f} ({long_pct:.0f}%)
- Qarz/Kapital: {de:.2f} {de_c}
- Joriy nisbat: {cr:.2f} {cr_c}

💸 DIVIDEND:
- Daromad: {p.get('lastDiv',0)*100/p.get('price',1):.2f}%
- Payout: {r.get('payoutRatioTTM',0)*100:.1f}%"""
    except Exception as e:
        return f"❌ Xato: {e}"

def get_uzse_price(symbol):
    try:
        url = f"https://uzse.uz/trade_results?search={symbol}"
        html = requests.get(url, timeout=10).text
        return f"🇺🇿 {symbol} | UZSE\nMa'lumot uzse.uz dan olinmoqda..."
    except:
        return f"🇺🇿 {symbol} | UZSE\nXato"

def screen_stocks(criteria):
    results = []
    for sym in GLOBAL_SCREEN:
        try:
            base = "https://financialmodelingprep.com/api/v3"
            p = requests.get(f"{base}/profile/{sym}?apikey={FMP_KEY}", timeout=5).json()[0]
            r = requests.get(f"{base}/ratios-ttm/{sym}?apikey={FMP_KEY}", timeout=5).json()[0]
            pe = r.get('peRatioTTM', 999)
            roe = r.get('returnOnEquityTTM', 0)*100
            dy = p.get('lastDiv',0)*100/p.get('price',1)
            de = r.get('debtEquityRatioTTM', 999)
            sector = p.get('sector','')
            haram = any(x in sector for x in ["Banks","Tobacco"])
            ok = True
            if criteria=="halol" and haram: ok=False
            if criteria=="pe20" and pe>20: ok=False
            if criteria=="roe15" and roe<15: ok=False
            if criteria=="div3" and dy<3: ok=False
            if criteria=="lowdebt" and de>0.5: ok=False
            if ok:
                results.append(f"{svetofor(roe,20,15)} {sym} | P/E:{pe:.1f} ROE:{roe:.1f}%")
        except: pass
    return results[:10]

LUGAT = """📖 LUG'AT:

🟢 Yashil = Yaxshi
🟡 Sariq = O'rtacha
🔴 Qizil = Yomon

P/E — Narx/Foyda. Qancha past bo'lsa arzon.
• Texnologiya: 25-35 🟡
• Bank: 8-12 🟢

ROE — Kapitaldan foyda. >20% 🟢
Qarz/Kapital — <0.5 🟢, >1 🔴
Joriy nisbat — >2 🟢 (qarzni to'lay oladi)
"""

@bot.message_handler(commands=['start'])
def start(m):
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📈 Aksiya", "🇺🇿 UZSE", "📊 Raqobat", "📖 Lug'at")
    bot.send_message(m.chat.id, "Ticker yozing: NKE, AAPL, URTS, SQBN", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text=="📖 Lug'at")
def lugat(m): bot.send_message(m.chat.id, LUGAT)

@bot.message_handler(func=lambda m: m.text=="📊 Raqobat")
def competition(m):
    kb = telebot.types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        telebot.types.InlineKeyboardButton("🟢 Halol", callback_data="scr_halol"),
        telebot.types.InlineKeyboardButton("💰 P/E<20", callback_data="scr_pe20"),
        telebot.types.InlineKeyboardButton("📈 ROE>15%", callback_data="scr_roe15"),
        telebot.types.InlineKeyboardButton("💵 Div>3%", callback_data="scr_div3"),
        telebot.types.InlineKeyboardButton("🛡️ Qarz kam", callback_data="scr_lowdebt")
    )
    bot.send_message(m.chat.id, "Qaysi talab?", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("scr_"))
def screen_cb(c):
    crit = c.data[4:]
    bot.answer_callback_query(c.id, "Tekshirilmoqda...")
    res = screen_stocks(crit)
    txt = f"🏆 {crit}:\n" + ("\n".join(res) if res else "Topilmadi")
    bot.send_message(c.message.chat.id, txt)

@bot.message_handler(func=lambda m: True)
def handle(m):
    txt = m.text.strip().upper()
    if txt in ["📈 AKSIYA","🇺🇿 UZSE","📊 RAQOBAT","📖 LUG'AT"]: return
    if txt in UZBEK_TICKERS:
        res = get_uzse_price(txt)
    else:
        try:
            p = requests.get(f"https://financialmodelingprep.com/api/v3/profile/{txt}?apikey={FMP_KEY}", timeout=5).json()[0]
            res = f"🚨 {txt} | ${p.get('price',0)}\n{p.get('companyName','')}"
        except: res = f"🚨 {txt} topilmadi"
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("📊 Davom etish", callback_data=f"deep_{txt}"))
    bot.send_message(m.chat.id, res, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("deep_"))
def deep(c):
    sym = c.data[5:]
    bot.answer_callback_query(c.id, "Yuklanmoqda...")
    txt = get_uzse_price(sym) if sym in UZBEK_TICKERS else get_fmp_deep(sym)
    bot.send_message(c.message.chat.id, txt)

@app.route('/')
def home(): return "OK"
def run_flask(): app.run(host="0.0.0.0", port=10000)
def run_bot():
    while True:
        try: bot.polling(none_stop=True)
        except: time.sleep(5)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    run_bot()