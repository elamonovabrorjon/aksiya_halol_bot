import telebot, requests
from flask import Flask
import threading
from datetime import datetime

TOKEN = "8781183838:AAFmgLoz6Bb8LlA-50lVAdAbNvhBCWO3sm0"
FINNHUB = "d842bj1r01qkm5c9vr70d842bj1r01qkm5c9vr7g"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Bozorlar
FOREX = {'XAUUSD':'OANDA:XAU_USD','XAGUSD':'OANDA:XAG_USD','EURUSD':'OANDA:EUR_USD',
         'BTCUSD':'BINANCE:BTCUSDT','ETHUSD':'BINANCE:ETHUSDT'}
STOCKS = ['LLY','AAPL','NVDA','TSLA','MSFT','AMZN','GOOGL','META','JPM','JNJ']

HALOL_DB = {
    'LLY':{'status':'🟡 Shubhali','sabab':'Mounjaro/Zepbound halol, lekin qarz bor'},
    'AAPL':{'status':'🟢 Halol','sabab':'Texnologiya, foiz <5%'},
    'NVDA':{'status':'🟢 Halol','sabab':'Chip, AI'},
    'TSLA':{'status':'🟡 Shubhali','sabab':'Qarz yuqori'},
    'MSFT':{'status':'🟢 Halol','sabab':'Software'},
    'JPM':{'status':'🔴 Harom','sabab':'Bank, foiz'},
}

def get_quote(sym):
    try:
        if 'BTC' in sym or 'ETH' in sym:
            coin = 'bitcoin' if 'BTC' in sym else 'ethereum'
            r = requests.get(f'https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd', timeout=5).json()
            return {'c':r['usd'],'dp':0,'h':r['usd']*1.01,'l':r['usd']*0.99}
        url = f'https://finnhub.io/api/v1/quote?symbol={sym}&token={FINNHUB}'
        return requests.get(url, timeout=5).json()
    except: return {}

def get_snr(sym):
    try:
        url = f'https://finnhub.io/api/v1/scan/support-resistance?symbol={sym}&token={FINNHUB}'
        r = requests.get(url, timeout=5).json()
        return sorted(r.get('levels',[]))
    except: return []

def forex_tahlil(t):
    sym = FOREX[t]
    q = get_quote(sym)
    p = q.get('c',0); ch = q.get('dp',0)
    levels = get_snr(sym)
    sup = [x for x in levels if x<p][-3:][::-1]
    res = [x for x in levels if x>p][:3]
    s1 = sup[0] if sup else p*0.98
    r1 = res[0] if res else p*1.02
    return f"""🧠 SNR - {t}
💰 ${p:,.2f} ({ch:+.2f}%)
📉 S: {', '.join(f'${x:.0f}' for x in sup)}
📈 R: {', '.join(f'${x:.0f}' for x in res)}
🎯 LONG ${s1*1.01:.0f} → TP ${r1:.0f} | SL ${s1*0.97:.0f}
🎯 SHORT ${r1*0.99:.0f} → TP ${s1:.0f} | SL ${r1*1.03:.0f}"""

def stock_tahlil(t):
    q = get_quote(t)
    p = q.get('c',0); h = q.get('h',p); l = q.get('l',p); ch = q.get('dp',0)
    levels = get_snr(t)
    sup = [x for x in levels if x<p][-2:][::-1] or [p*0.95,p*0.90]
    res = [x for x in levels if x>p][:2] or [p*1.05,p*1.10]
    halol = HALOL_DB.get(t,{'status':'⚪ Noma\'lum','sabab':'Tekshirilmagan'})

    s1,r1 = sup[0],res[0]
    return f"""🧠 HALOL ALPHA - {t}
━━━━━━━━━━━━━━━━━━━━
💰 ${p:,.2f} ({ch:+.2f}%) | H:${h:.2f} L:${l:.2f}

🕌 HALOL: {halol['status']}
{halol['sabab']}

📊 TEXNIK:
Support ${s1:.0f}, Resistance ${r1:.0f}

🎯 SIGNAL:
- LONG: ${s1*1.01:.0f}-${s1*1.02:.0f}
  TP1 ${r1:.0f} | TP2 ${r1*1.05:.0f}
  SL ${s1*0.96:.0f}
- SHORT: ${r1*0.98:.0f}-${r1:.0f}
  TP ${s1:.0f} | SL ${r1*1.04:.0f}

⏰ {datetime.now().strftime('%H:%M')}"""

@bot.message_handler(commands=['start'])
def start(m): bot.send_message(m.chat.id,"Yozing: LLY, AAPL, XAUUSD, BTCUSD")

@bot.message_handler(func=lambda m:True)
def h(m):
    t = m.text.strip().upper()
    if t in FOREX: txt = forex_tahlil(t)
    elif t in STOCKS: txt = stock_tahlil(t)
    else: txt = "Topilmadi. LLY, AAPL, XAUUSD yozing"
    bot.send_message(m.chat.id, txt)

@app.route('/')
def home(): return "OK"
threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
app.run(host='0.0.0.0',port=10000)