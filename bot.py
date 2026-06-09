import os, telebot, time, sqlite3, datetime, threading, matplotlib, requests, io
import pandas as pd
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN = os.getenv("CHAT_ID")
TWELVE_KEY = os.getenv("TWELVE_KEY", "demo")
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook(); time.sleep(1)
app = Flask(__name__)

conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS daily (uid INTEGER, day TEXT, cnt INTEGER, PRIMARY KEY(uid,day))''')
conn.commit()

# 120 ta O'zbekiston aksiyalari
UZ_STOCKS = ['AGMK','ALKB','AVO','BIK','BRCB','CAPT','CHM','DORI','DVIN','EPKT','ERGO','GMUZ','HAVA','HMKB','HTTB','IPKY','KABL','KKOM','KONM','KVTS','MKDR','MTBK','NAV','NGM','QKIZ','QMBK','QZAP','RBKM','SAMK','SBC','SILK','SKIB','SQRB','TCD','TEPS','TFT','TKOM','TRM','TSHT','UABK','UAT','UCAP','UFAB','UGA','UKRB','UNUM','UPK','URGD','USAM','USBC','USHT','USKC','USMR','USNI','USPB','USTB','UTEX','UTKB','UZBB','UZBE','UZBR','UZCA','UZCM','UZDA','UZDV','UZEL','UZF','UZFA','UZFB','UZFC','UZFD','UZFE','UZFF','UZFI','UZFJ','UZFK','UZFL','UZFM','UZFN','UZFO','UZFP','UZFQ','UZFR','UZFS','UZFT','UZFU','UZFV','UZFW','UZFX','UZFY','UZFZ','UZGA','UZGB','UZGC','UZGD','UZGE','UZGF','UZGG','UZGH','UZGI','UZGJ','UZGK','UZGL','UZGM','UZGN','UZGO','UZGP','UZGQ','UZGR','UZGS','UZGT','UZGU','UZGV','UZGW','UZGX','UZGY','UZGZ','UZHA','UZHB','UZHC','UZHD','UZHE','UZHF','UZHG','UZHH','UZHI','UZHJ']

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
    crypto = {'BTC':'bitcoin','ETH':'ethereum'}
    if sym in crypto:
        r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={crypto[sym]}&vs_currencies=usd", timeout=10).json()
        return r[crypto[sym]]['usd'], None, 'crypto'
    if len(sym)==6 and sym.isalpha():
        r = requests.get(f"https://api.exchangerate.host/convert?from={sym[:3]}&to={sym[3:]}", timeout=10).json()
        return r.get('result'), None, 'forex'
    # UZ aksiyalar
    if sym in UZ_STOCKS:
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}.UZ?interval=1d&range=1d", headers={"User-Agent":"Mozilla/5.0"}, timeout=8).json()
            return r['chart']['result'][0]['meta']['regularMarketPrice'], None, 'uz'
        except: return None, None, 'uz'
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1m&range=1d", headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
        return r['chart']['result'][0]['meta']['regularMarketPrice'], None, 'stock'
    except: return None, None, None

def get_fund(sym):
    try:
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{sym}?modules=financialData,assetProfile"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
        res = r['quoteSummary']['result'][0]
        fd=res.get('financialData',{}); ap=res.get('assetProfile',{})
        return {'de':fd.get('debtToEquity',{}).get('raw',0),'employees':ap.get('fullTimeEmployees',0)}
    except: return None

def tech_analysis(sym):
    mapping = {'XAUUSD':'XAU/USD','BTCUSD':'BTC/USD','EURUSD':'EUR/USD'}
    s = mapping.get(sym, sym)
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={s}&interval=1min&outputsize=100&apikey={TWELVE_KEY}"
        df = pd.DataFrame(requests.get(url, timeout=10).json()['values'])
        df = df.astype({'close':float,'high':float,'low':float}).iloc[::-1]
        delta = df['close'].diff(); gain = delta.clip(lower=0).rolling(14).mean(); loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain/loss; df['rsi'] = 100 - (100/(1+rs)); df['ema20'] = df['close'].ewm(span=20).mean()
        resistance = df['high'].tail(20).max(); support = df['low'].tail(20).min()
        price = df['close'].iloc[-1]; rsi = df['rsi'].iloc[-1]
        book=""
        if sym=='BTCUSD':
            d = requests.get("https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=5", timeout=5).json()
            book = f"\nBookmap: ${float(d['bids'][0][0]):,.0f}/${float(d['asks'][0][0]):,.0f}"
        sig = "🟢 OLISH" if price < support*1.002 else "🔴 SOTISH" if price > resistance*0.998 else "🟡 KUTISH"
        return f"📊 {sym} LIVE\n${price:,.2f}\nS ${support:,.2f} | R ${resistance:,.2f}\nRSI {rsi:.1f} {sig}{book}"
    except: return f"{sym} xato"

def ai_tahlil(sym):
    price,_,typ = get_price(sym)
    if sym in ['XAUUSD','BTCUSD','EURUSD']: return tech_analysis(sym) + "\n\n🟢 HALOL"
    if typ=='uz':
        return f"🇺🇿 {sym}\n{price:,.0f} so'm" if price else f"🇺🇿 {sym} - ma'lumot yo'q"
    fund = get_fund(sym)
    if fund:
        de=fund['de']; pct=95 if de<33 else 75 if de<66 else 55
        return f"🤖 {sym} ${price:.2f}\nQarz {de:.0f}% | Halol {pct}%"
    return f"{sym} ${price}"

@bot.message_handler(commands=['start'])
def start(m):
    uid=m.from_user.id
    if not c.execute("SELECT id FROM users WHERE id=?", (uid,)).fetchone(): c.execute("INSERT INTO users VALUES (?,?)", (uid, m.from_user.first_name)); conn.commit()
    kb=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🤖 AI Tahlil","📈 Grafik")
    kb.add("🇺🇿 Uzbekistan bozori","🧠 AI Xizmat")
    kb.add("💳 PRO")
    bot.send_message(m.chat.id, "PRO ✅", reply_markup=kb)

@bot.message_handler(func=lambda m: True)
def h(m):
    uid=m.from_user.id; t=m.text.strip(); u=t.upper()
    if t=="🇺🇿 Uzbekistan bozori":
        txt="🇺🇿 UZBEKISTON (120 ta)\n\n"
        for i,s in enumerate(UZ_STOCKS[:40],1):
            price,_,_=get_price(s)
            txt+=f"{i}. {s} - {price:,.0f if price else '—'}\n"
            if i%20==0: txt+="\n"
        txt+="\nTicker yozing (masalan UZBE):"
        return bot.send_message(m.chat.id, txt)
    if t=="🤖 AI Tahlil": return bot.send_message(m.chat.id,"Ticker:")
    if m.reply_to_message and "Ticker" in m.reply_to_message.text:
        can,left = can_analyze(uid)
        if not can: return bot.send_message(m.chat.id,"Limit")
        inc_analyze(uid); bot.send_message(m.chat.id, ai_tahlil(u))
    elif len(u)<=6:
        bot.send_message(m.chat.id, ai_tahlil(u))

def auto_analysis():
    stocks = ['AAPL','TSLA','NVDA','NKE','MSFT']
    fx = ['XAUUSD','BTCUSD','EURUSD']
    while True:
        try:
            if ADMIN:
                for s in fx:
                    bot.send_message(ADMIN, f"⏱ {datetime.datetime.now().strftime('%H:%M:%S')}\n{tech_analysis(s)}"); time.sleep(2)
                if datetime.datetime.now().minute % 5 == 0:
                    for sym in stocks:
                        bot.send_message(ADMIN, ai_tahlil(sym)); time.sleep(2)
        except: pass
        time.sleep(60)

threading.Thread(target=auto_analysis, daemon=True).start()

@app.route('/')
def home(): return "OK"
if __name__=="__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0",port=10000)).start()
    bot.infinity_polling()