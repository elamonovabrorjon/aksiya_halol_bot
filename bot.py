import telebot, requests, os
from flask import Flask
import threading

TOKEN = os.getenv("TOKEN")
FINNHUB = os.getenv("FINNHUB")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

FOREX = {'XAUUSD':'OANDA:XAU_USD','XAGUSD':'OANDA:XAG_USD','EURUSD':'OANDA:EUR_USD',
         'BTCUSD':'BINANCE:BTCUSDT','ETHUSD':'BINANCE:ETHUSDT'}
STOCKS = ['LLY','AAPL','NVDA','TSLA','MSFT','AMZN','GOOGL','META','JPM','JNJ']

HALOL = {'LLY':'🟡 Shubhali','AAPL':'🟢 Halol','NVDA':'🟢 Halol',
         'TSLA':'🟡 Shubhali','MSFT':'🟢 Halol','JPM':'🔴 Harom'}

def q(sym):
    try:
        if 'BTC' in sym or 'ETH' in sym:
            c='bitcoin' if 'BTC' in sym else 'ethereum'
            p=requests.get(f'https://api.coingecko.com/api/v3/simple/price?ids={c}&vs_currencies=usd',timeout=5).json()[c]['usd']
            return {'c':p,'dp':0,'h':p*1.01,'l':p*0.99}
        return requests.get(f'https://finnhub.io/api/v1/quote?symbol={sym}&token={FINNHUB}',timeout=5).json()
    except: return {}

def snr(sym):
    try: return sorted(requests.get(f'https://finnhub.io/api/v1/scan/support-resistance?symbol={sym}&token={FINNHUB}',timeout=5).json().get('levels',[]))
    except: return []

@bot.message_handler(commands=['start'])
def s(m): bot.send_message(m.chat.id,"Yoz: LLY, AAPL, XAUUSD")

@bot.message_handler(func=lambda m:True)
def h(m):
    t=m.text.strip().upper()
    if t in FOREX:
        sym=FOREX[t]; d=q(sym); p=d.get('c',0); ch=d.get('dp',0)
        lv=snr(sym); s=[x for x in lv if x<p][-2:]; r=[x for x in lv if x>p][:2]
        s1=s[0] if s else p*0.98; r1=r[0] if r else p*1.02
        txt=f"{t} ${p:.2f} ({ch:+.2f}%)\nLONG ${s1*1.01:.0f} TP${r1:.0f} SL${s1*0.97:.0f}\nSHORT ${r1*0.99:.0f} TP${s1:.0f} SL${r1*1.03:.0f}"
    elif t in STOCKS:
        d=q(t); p=d.get('c',0); ch=d.get('dp',0)
        lv=snr(t); s=[x for x in lv if x<p][-1:] or [p*0.95]; r=[x for x in lv if x>p][:1] or [p*1.05]
        s1=s[0]; r1=r[0]; hal=HALOL.get(t,'⚪')
        txt=f"HALOL ALPHA - {t}\n${p:.2f} ({ch:+.2f}%)\nHALOL: {hal}\nLONG ${s1*1.01:.0f} TP${r1:.0f} SL${s1*0.96:.0f}\nSHORT ${r1*0.99:.0f} TP${s1:.0f} SL${r1*1.04:.0f}"
    else: txt="LLY, AAPL, XAUUSD yoz"
    bot.send_message(m.chat.id,txt)

@app.route('/')
def home(): return "OK"

threading.Thread(target=lambda: bot.infinity_polling(),daemon=True).start()
app.run(host='0.0.0.0',port=int(os.environ.get('PORT',10000)))