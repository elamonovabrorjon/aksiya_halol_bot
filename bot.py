import os, telebot, time, sqlite3, datetime, threading, requests
import pandas as pd
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN = os.getenv("CHAT_ID")
TWELVE_KEY = "ce7a9fd8d4734250861ac7f09406a9bf" # SIZNING KALIT
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook(); time.sleep(1)
app = Flask(__name__)

conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)''')
conn.commit()

UZ_STOCKS = ['AGMK','ALKB','AVO','BIK','BRCB','CAPT','CHM','DORI','DVIN','EPKT','ERGO','GMUZ','HAVA','HMKB','HTTB','IPKY','KABL','KKOM','KONM','KVTS','MKDR','MTBK','NAV','NGM','QKIZ','QMBK','QZAP','RBKM','SAMK','SBC','SILK','SKIB','SQRB','TCD','TEPS','TFT','TKOM','TRM','TSHT','UABK','UAT','UCAP','UFAB','UGA','UKRB','UNUM','UPK','URGD','USAM','USBC','USHT','USKC','USMR','USNI','USPB','USTB','UTEX','UTKB','UZBB','UZBE','UZBR','UZCA','UZCM','UZDA','UZDV','UZEL']

def get_price(sym):
    sym = sym.upper()
    if sym in ['BTC']:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=10).json()
        return r['bitcoin']['usd']
    if sym in UZ_STOCKS:
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}.UZ?interval=1d&range=1d", headers={"User-Agent":"Mozilla/5.0"}, timeout=8).json()
            return r['chart']['result'][0]['meta']['regularMarketPrice']
        except: return None
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1m&range=1d", headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
        return r['chart']['result'][0]['meta']['regularMarketPrice']
    except: return None

def tech_analysis(sym):
    mapping = {'XAUUSD':'XAU/USD','BTCUSD':'BTC/USD','EURUSD':'EUR/USD','AAPL':'AAPL'}
    s = mapping.get(sym, sym)
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={s}&interval=1min&outputsize=100&apikey={TWELVE_KEY}"
        df = pd.DataFrame(requests.get(url, timeout=10).json()['values'])
        df = df.astype({'close':float,'high':float,'low':float}).iloc[::-1]
        delta = df['close'].diff(); gain = delta.clip(lower=0).rolling(14).mean(); loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain/loss; rsi = 100 - (100/(1+rs.iloc[-1]))
        support = df['low'].tail(20).min(); resistance = df['high'].tail(20).max(); price = df['close'].iloc[-1]
        sig = "🟢 OLISH" if price < support*1.002 else "🔴 SOTISH" if price > resistance*0.998 else "🟡 KUTISH"
        book = ""
        if sym=='BTCUSD':
            d = requests.get("https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=5", timeout=5).json()
            book = f"\nBookmap: ${float(d['bids'][0][0]):,.0f}/${float(d['asks'][0][0]):,.0f}"
        return f"📊 {sym} LIVE\n${price:,.2f}\nS ${support:,.2f} | R ${resistance:,.2f}\nRSI {rsi:.1f} {sig}{book}"
    except Exception as e: return f"{sym} xato: {str(e)[:30]}"

@bot.message_handler(commands=['start'])
def start(m):
    kb=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🤖 AI Tahlil","📈 Grafik")
    kb.add("🧠 AI Xizmat","💰 Valyuta")
    kb.add("🇺🇿 Uzbekistan bozori","📰 Yangiliklar")
    kb.add("💳 PRO","⚙️ Sozlamalar")
    bot.send_message(m.chat.id, "PRO ✅", reply_markup=kb)

@bot.message_handler(func=lambda m: True)
def h(m):
    t=m.text.strip(); u=t.upper()
    if t=="🤖 AI Tahlil": return bot.send_message(m.chat.id,"Ticker yozing (XAUUSD, BTCUSD, AAPL):")
    if t=="🇺🇿 Uzbekistan bozori":
        txt="🇺🇿 UZ AKSIYALAR\n"
        for s in UZ_STOCKS[:20]: txt+=f"{s}\n"
        return bot.send_message(m.chat.id, txt)
    if t in ["XAUUSD","BTCUSD","EURUSD","AAPL","TSLA","NVDA"] or len(u)<=6:
        # FAQAT SIZ SO'RAGANDA LIVE
        bot.send_chat_action(m.chat.id, 'typing')
        if u in ['XAUUSD','BTCUSD','EURUSD']:
            bot.send_message(m.chat.id, tech_analysis(u))
        else:
            price = get_price(u)
            bot.send_message(m.chat.id, f"{u} ${price:.2f}" if price else f"{u} topilmadi")

@app.route('/')
def home(): return "OK"
if __name__=="__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0",port=10000)).start()
    bot.infinity_polling()