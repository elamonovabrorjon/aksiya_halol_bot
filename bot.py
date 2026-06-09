import os, telebot, time, sqlite3, datetime, threading, matplotlib, requests, io
import pandas as pd
import pandas_ta as ta
import xml.etree.ElementTree as ET
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
    # stocks
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1m&range=1d", headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
        return r['chart']['result'][0]['meta']['regularMarketPrice'], None, 'stock'
    except: return None, None, None

def get_fund(sym):
    try:
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{sym}?modules=financialData,defaultKeyStatistics,assetProfile"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
        res = r['quoteSummary']['result'][0]
        fd=res.get('financialData',{}); ks=res.get('defaultKeyStatistics',{}); ap=res.get('assetProfile',{})
        return {'de':fd.get('debtToEquity',{}).get('raw',0),'employees':ap.get('fullTimeEmployees',0)}
    except: return None

def tech_analysis(sym):
    mapping = {'XAUUSD':'XAU/USD','BTCUSD':'BTC/USD','EURUSD':'EUR/USD'}
    s = mapping.get(sym, sym)
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={s}&interval=1min&outputsize=100&apikey={TWELVE_KEY}"
        df = pd.DataFrame(requests.get(url, timeout=10).json()['values'])
        df = df.astype({'close':float,'high':float,'low':float}).iloc[::-1]
        df['rsi'] = ta.rsi(df['close'],14); df['ema20'] = ta.ema(df['close'],20)
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
    if sym in ['XAUUSD','BTCUSD','EURUSD']: return tech_analysis(sym) + "\n\n🟢 HALOL"
    price,_,_ = get_price(sym)
    fund = get_fund(sym)
    if fund:
        de=fund['de']; pct=95 if de<33 else 75 if de<66 else 55 if de<100 else 35
        return f"🤖 {sym} ${price:.2f}\nQarz {de:.0f}% | Halol {pct}%\nXodim {fund['employees']:,}"
    return f"{sym} ${price}"

@bot.message_handler(commands=['start'])
def start(m):
    uid=m.from_user.id
    if not c.execute("SELECT id FROM users WHERE id=?", (uid,)).fetchone(): c.execute("INSERT INTO users VALUES (?,?)", (uid, m.from_user.first_name)); conn.commit()
    kb=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🤖 AI Tahlil","📈 Grafik"); kb.add("🧠 AI Xizmat","💳 PRO")
    bot.send_message(m.chat.id, f"PRO ✅", reply_markup=kb)

@bot.message_handler(func=lambda m: True)
def h(m):
    uid=m.from_user.id; t=m.text.strip(); u=t.upper()
    if t=="🤖 AI Tahlil": return bot.send_message(m.chat.id,"Ticker:")
    if m.reply_to_message and "Ticker" in m.reply_to_message.text:
        can,left = can_analyze(uid)
        if not can: return bot.send_message(m.chat.id,"Limit")
        inc_analyze(uid)
        bot.send_message(m.chat.id, ai_tahlil(u))

def auto_analysis():
    stocks = ['AAPL','TSLA','NVDA','NKE','MSFT']
    fx = ['XAUUSD','BTCUSD','EURUSD']
    while True:
        try:
            if ADMIN:
                for s in fx:
                    bot.send_message(ADMIN, f"⏱ {datetime.datetime.now().strftime('%H:%M:%S')}\n{tech_analysis(s)}")
                    time.sleep(2)
                if datetime.datetime.now().minute % 5 == 0:
                    for sym in stocks:
                        bot.send_message(ADMIN, ai_tahlil(sym))
                        time.sleep(2)
        except: pass
        time.sleep(60)

threading.Thread(target=auto_analysis, daemon=True).start()

@app.route('/')
def home(): return "OK"
if __name__=="__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0",port=10000)).start()
    bot.infinity_polling()