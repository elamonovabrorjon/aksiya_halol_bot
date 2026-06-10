# bot.py - Halol Alpha Universal Bot
import telebot, requests, datetime, threading, time
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from flask import Flask

TOKEN = "8781183838:AAFmgLoz6Bb8LlA-50lVAdAbNvhBCWO3sm0"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def tsk():
    return (datetime.datetime.utcnow()+datetime.timedelta(hours=5)).strftime('%H:%M %d.%m')

def get_data(symbol):
    s = symbol.upper()
    # CRYPTO real
    if s in ['BTC','ETH','SOL','XRP','DOGE']:
        try:
            ids = {'BTC':'bitcoin','ETH':'ethereum','SOL':'solana','XRP':'ripple','DOGE':'dogecoin'}
            r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={ids[s]}&vs_currencies=usd&include_24hr_change=true", timeout=6).json()
            d = r[ids[s]]
            return {"t":"CRYPTO","p":d['usd'],"c":d['usd_24h_change'],"n":s}
        except: pass
    # STOCKS
    st = {'TSLA':295.5,'AAPL':245.2,'NVDA':120.8,'MSFT':420.1,'AMZN':180.3,'GOOGL':175.4,'META':500.2,'NFLX':650.5,'TSCO':27.1,'NKE':75.6,'SPY':523}
    if s in st: return {"t":"STOCK","p":st[s],"c":0.8,"n":s}
    # FOREX/GOLD
    if s in ['EURUSD','GOLD','XAUUSD','USDJPY']:
        p = 1.085 if 'EUR' in s else 2345 if 'GOLD' in s or 'XAU' in s else 157.2
        return {"t":"FOREX","p":p,"c":0.2,"n":s}
    return None

def halol(s):
    if s in ['JPM','BAC','V','MA']: return "🔴 Harom (riba)"
    if s in ['TSLA','AAPL','META','MSFT','GOOGL']: return "🟡 Shubhali (qarz)"
    if s in ['BTC','ETH','SOL']: return "🟡 Kripto (ixtilofli)"
    return "🟢 Halolga yaqin"

def analiz(sym):
    d = get_data(sym)
    if not d: return "Yozing: BTC, ETH, TSLA, AAPL, NVDA, GOLD, EURUSD, SPY"
    p,c = d['p'], d['c']
    rsi = int(50 + c*3)
    prob = max(30, min(90, int(55 + c*4)))
    sig = '🟢 KIRISH' if prob>68 else '🟡 KUT' if prob>50 else '🔴 CHET'
    tr = "📈" if c>0.5 else "📉" if c<-0.5 else "➡️"
    return f"""🧠 HALOL ALPHA
{d['n']} | {d['t']}
💰 ${p:,.2f} ({c:+.2f}%)
{tr} RSI {rsi} | {halol(sym)}

🎯 {sig} | {prob}%
🕐 {tsk()}"""

def kb():
    k = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    k.add(KeyboardButton("₿ BTC"),KeyboardButton("Ξ ETH"),KeyboardButton("🏦 TSLA"))
    k.add(KeyboardButton("🍎 AAPL"),KeyboardButton("📊 NVDA"),KeyboardButton("🥇 GOLD"))
    k.add(KeyboardButton("💶 EURUSD"),KeyboardButton("📈 SPY"),KeyboardButton("🚜 TSCO"))
    return k

@bot.message_handler(commands=['start'])
def s(m): bot.send_message(m.chat.id, "Halol Alpha tayyor. Tanlang:", reply_markup=kb())

@bot.message_handler(func=lambda m: True)
def h(m):
    t = m.text.upper()
    sym = ''.join([c for c in t if c.isalnum()])[:6]
    bot.send_message(m.chat.id, analiz(sym), reply_markup=kb())

@app.route('/')
def home(): return "OK"

def poll():
    while True:
        try: bot.infinity_polling()
        except: time.sleep(3)

threading.Thread(target=poll, daemon=True).start()
app.run(host='0.0.0.0', port=10000)