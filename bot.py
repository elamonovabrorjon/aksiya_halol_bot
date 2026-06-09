import os, telebot, time, sqlite3, datetime, threading, matplotlib, requests, io
import pandas as pd
import xml.etree.ElementTree as ET
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN = os.getenv("CHAT_ID")
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook(); time.sleep(1)
app = Flask(__name__)

conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS daily (uid INTEGER, day TEXT, cnt INTEGER, PRIMARY KEY(uid,day))''')
c.execute('''CREATE TABLE IF NOT EXISTS alerts (uid INTEGER, sym TEXT, price REAL)''')
conn.commit()

def check_pro(uid): return str(uid) == ADMIN
def can_analyze(uid):
    if check_pro(uid): return True, 999
    today = datetime.date.today().isoformat()
    cnt = c.execute("SELECT cnt FROM daily WHERE uid=? AND day=?", (uid, today)).fetchone()
    cnt = cnt[0] if cnt else 0
    return cnt < 10, 10 - cnt
def inc_analyze(uid):
    today = datetime.date.today().isoformat()
    c.execute("INSERT INTO daily VALUES(?,?,1) ON CONFLICT(uid,day) DO UPDATE SET cnt=cnt+1", (uid, today)); conn.commit()

def get_price(sym):
    sym = sym.upper()
    crypto = {'BTC':'bitcoin','ETH':'ethereum','SOL':'solana','BNB':'binancecoin','XRP':'ripple','ADA':'cardano','DOGE':'dogecoin','TON':'the-open-network'}
    if sym in crypto:
        try:
            r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={crypto[sym]}&vs_currencies=usd", timeout=10).json()
            return r[crypto[sym]]['usd'], None, 'crypto'
        except: pass
    if len(sym)==6:
        try:
            r = requests.get(f"https://api.exchangerate.host/convert?from={sym[:3]}&to={sym[3:]}", timeout=10).json()
            return r['result'], None, 'forex'
        except: pass
    if sym in ['GOLD','SILVER','OIL']: sym = {'GOLD':'GC=F','SILVER':'SI=F','OIL':'CL=F'}[sym]
    try:
        for s in [f"{sym.lower()}.us", sym.lower()]:
            r = requests.get(f"https://stooq.com/q/d/l/?s={s}&i=d", timeout=10)
            if 'Date' in r.text:
                df = pd.read_csv(io.StringIO(r.text))
                if len(df)>5: return float(df['Close'].iloc[-1]), df, 'stock'
    except: pass
    return None, None, None

def get_fund(sym):
    try:
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{sym}?modules=financialData,defaultKeyStatistics,assetProfile"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
        res = r['quoteSummary']['result'][0]
        fd = res.get('financialData',{}); ks = res.get('defaultKeyStatistics',{}); ap = res.get('assetProfile',{})
        ipo = ks.get('firstTradeDateEpochUtc',{}).get('raw',0)
        ipo_date = datetime.datetime.fromtimestamp(ipo).strftime('%Y-%m-%d') if ipo else "N/A"
        return {
            'pm': fd.get('profitMargins',{}).get('raw',0)*100,
            'roe': fd.get('returnOnEquity',{}).get('raw',0)*100,
            'de': fd.get('debtToEquity',{}).get('raw',0),
            'debt': fd.get('totalDebt',{}).get('raw',0)/1e9,
            'fcf': fd.get('freeCashflow',{}).get('raw',0)/1e9,
            'employees': ap.get('fullTimeEmployees',0),
            'ipo': ipo_date
        }
    except: return None

def get_earnings(sym):
    try:
        r = requests.get(f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{sym}?modules=earnings", headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
        q = r['quoteSummary']['result'][0]['earnings']['financialsChart']['quarterly'][-1]
        return f"Q: ${q['revenue']['raw']/1e9:.1f}B | EPS ${q['earnings']['raw']:.2f}"
    except: return ""

def get_news(sym):
    try:
        r = requests.get(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={sym}&region=US&lang=en-US", timeout=10)
        root = ET.fromstring(r.content)
        return "\n".join([f"• {i.find('title').text}" for i in root.findall('.//item')[:3]])
    except: return "Yo'q"

def ai_tahlil(sym):
    price, df, typ = get_price(sym)
    if not price: return f"❌ {sym} topilmadi"
    if typ=='crypto':
        halol = {'BTC':'🟢 HALOL','ETH':'🟢 HALOL'}.get(sym,'🟡 SHUBHALI')
        return f"₿ {sym} | ${price:,.0f}\n\n{halol}"
    if typ=='forex': return f"💱 {sym} | {price:.4f}\n\n🟡 SHUBHALI"
    if typ=='stock':
        fund = get_fund(sym); earn = get_earnings(sym)
        if fund:
            de = fund['de']
            halal_pct = 95 if de<33 else 75 if de<66 else 55 if de<100 else 35
            halol = "🟢 HALOL" if halal_pct>=80 else "🟡 SHUBHALI" if halal_pct>=60 else "🔴 HARAMGA YAQIN"
            return f"""🤖 {sym} | ${price:.2f}
{earn}
PM {fund['pm']:.1f}% | ROE {fund['roe']:.1f}%
Qarz: ${fund['debt']:.1f}B ({de:.0f}%)
Erkin pul: ${fund['fcf']:.1f}B
Xodim: {fund['employees']:,}
IPO: {fund['ipo']}

{halol} ({halal_pct}%)"""
        return f"🤖 {sym} | ${price:.2f}"
    return f"{sym} | {price}"

@bot.message_handler(commands=['start'])
def start(m):
    uid=m.from_user.id
    if not c.execute("SELECT id FROM users WHERE id=?", (uid,)).fetchone(): c.execute("INSERT INTO users VALUES (?,?)", (uid, m.from_user.first_name)); conn.commit()
    kb=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🤖 AI Tahlil","📈 Grafik"); kb.add("🔔 Signal","💼 Portfel"); kb.add("⚔️ Solishtir","📰 Yangilik"); kb.add("🧠 AI Xizmat","💳 PRO")
    bot.send_message(m.chat.id, f"Aksiya Halol PRO ✅\n{'👑 SIZ ADMIN' if check_pro(uid) else 'Bepul: 10 ta/kun'}", reply_markup=kb)

@bot.message_handler(func=lambda m: True)
def h(m):
    uid=m.from_user.id; t=m.text.strip(); u=t.upper()

    if t=="🤖 AI Tahlil": return bot.send_message(m.chat.id,"Ticker:")
    if t=="🧠 AI Xizmat": return bot.send_message(m.chat.id,"Savolingizni yozing:")
    if t=="📰 Yangilik": return bot.send_message(m.chat.id,"Yangilik ticker:")
    if t=="📈 Grafik":
        if not check_pro(uid): return bot.send_message(m.chat.id,"PRO kerak")
        return bot.send_message(m.chat.id,"Grafik ticker:")
    if t=="💳 PRO": return bot.send_message(m.chat.id, "✅ Siz ADMINSIZ" if check_pro(uid) else "25,000 so'm")

    if m.reply_to_message:
        txt = m.reply_to_message.text
        if "Ticker" in txt:
            can,left = can_analyze(uid)
            if not can: return bot.send_message(m.chat.id,"10 ta tugadi")
            inc_analyze(uid)
            analysis = ai_tahlil(u)
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("🧠 AI Maslahat", callback_data=f"advice_{u}"))
            bot.send_message(m.chat.id, analysis + (f"\n\nQoldi {left-1}" if not check_pro(uid) else ""), reply_markup=markup)
            # TradingView D1
            try:
                tv = f"https://image.thum.io/get/width/1000/crop/700/noanimate/https://www.tradingview.com/chart/?symbol={u}"
                bot.send_photo(m.chat.id, tv, caption=f"📊 {u} D1 TradingView")
            except: pass
            return
        if "Savolingizni" in txt:
            return bot.send_message(m.chat.id, f"🧠 AI: '{t}' — hozir bozorda ehtiyot bo'ling, fundamentalni tekshiring.")
        if "Yangilik" in txt:
            return bot.send_message(m.chat.id, f"📰 {u}\n\n{get_news(u)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("advice_"))
def advice(call):
    sym = call.data.split("_")[1]
    fund = get_fund(sym)
    if not fund: return bot.answer_callback_query(call.id, "Yo'q")
    pm, roe, de, fcf = fund['pm'], fund['roe'], fund['de'], fund['fcf']
    if de > 100: mas = "🔴 Qimmat va qarzdor — Soting"
    elif pm < 10: mas = "🟡 Kuchsiz — Kuting"
    elif fcf < 0: mas = "🔴 Pul yo'qotmoqda — Xavfli"
    elif de < 33 and pm > 20: mas = "🟢 Zo'r — Ushlab turing"
    else: mas = "🟡 O'rtacha — Kuzating"
    bot.send_message(call.message.chat.id, f"🧠 AI Maslahat: {sym}\n\n{mas}\n\nPM {pm:.1f}%\nROE {roe:.1f}%\nQarz {de:.0f}%")
    bot.answer_callback_query(call.id)

@app.route('/')
def home(): return "OK"
if __name__=="__main__":
    from threading import Thread; Thread(target=lambda: app.run(host="0.0.0.0",port=10000)).start()
    bot.infinity_polling()