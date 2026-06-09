import telebot, yfinance as yf, os, numpy as np
from datetime import datetime
import pytz
from flask import Flask
import threading

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
UZ = pytz.timezone('Asia/Tashkent')

KNOWN_SPLITS = {'NKE':2.0,'AAPL':4.0,'TSLA':3.0}
FOREX = {'EURUSD':'EURUSD=X','XAUUSD':'GC=F','BTCUSD':'BTC-USD'}

def norm(t): return FOREX.get(t.upper(), t.upper())

def dcf(ticker):
    try:
        s=yf.Ticker(ticker); cf=s.cashflow; i=s.info
        fcf=cf.loc['Free Cash Flow'].dropna()[:4][::-1]
        if len(fcf)<2: return 0,"Yo'q ⚪",0
        last=fcf.iloc[-1]; g=max(min(fcf.pct_change().mean(),0.15),0.03)
        val=sum([last*(1+g)**y/1.1**y for y in range(1,6)])
        val+=last*(1+g)**5*1.02/0.08/1.1**5
        per=val/i.get('sharesOutstanding',1); price=i.get('currentPrice',0)
        diff=(per-price)/price*100 if price else 0
        status="ARZON 🟢" if diff>20 else "QIMMAT 🔴" if diff<-20 else "ADOLATLI 🟡"
        return per,status,diff
    except: return 0,"Hisoblanmadi ⚪",0

def analyze(ticker):
    t=norm(ticker); s=yf.Ticker(t); i=s.info; h=s.history('1y')
    if h.empty: return "❌ Topilmadi"
    price=h['Close'].iloc[-1]
    if t in KNOWN_SPLITS and price>150: price/=KNOWN_SPLITS[t]
    name=i.get('longName',t); sector=i.get('sector','N/A'); cur=i.get('currency','USD')
    mcap=i.get('marketCap',1); debt=i.get('totalDebt',0); cash=i.get('totalCash',0)
    debt_r=debt/mcap*100; halal="HALOL 🟢" if debt_r<33 and cash/mcap*100<33 else "SHUBHALI 🟡"
    long_d=i.get('longTermDebt',0); de=i.get('debtToEquity',0)/100
    dcf_p,dcf_s,dcf_d=dcf(t)
    pe=i.get('trailingPE',0); pb=i.get('priceToBook',0); roe=i.get('returnOnEquity',0)*100
    pm=i.get('profitMargins',0)*100; dy=i.get('dividendYield',0)*100; beta=i.get('beta',0)
    fcf=i.get('freeCashflow',0)/1e9
    delta=h['Close'].diff(); rsi=100-(100/(1+delta.clip(lower=0).rolling(14).mean()/-delta.clip(upper=0).rolling(14).mean())); rsi_v=rsi.iloc[-1]
    high,low=h['High'].max(),h['Low'].min()
    f38=high-(high-low)*0.382; f50=high-(high-low)*0.5; f62=high-(high-low)*0.618
    score=sum([halal=="HALOL 🟢",pe<25 and pe>0,dy>2,debt_r<33])
    strat="🟢 SOTIB OLISH" if score==4 else "🟡 KUZAT" if score==3 else "🔴 O'TKAZ"
    sig="SELL 📉" if rsi_v>70 else "BUY 📈" if rsi_v<30 else "HOLD ⚪"
    return f"""🚨 Aksiya Halol Bot:
━━━━━━━━━━━━━━━━━━━━
🏢 {t} | {name}
{sector} | {halal}
━━━━━━━━━━━━━━━━━━━━
💵 {price:.2f} {cur} | DCF:{dcf_p:.2f} {dcf_s} ({dcf_d:+.0f}%)
52W:{high:.1f}/{low:.1f} | Cap:{mcap/1e12:.2f}T
━━━━━━━━━━━━━━━━━━━━
👑 QARZ: {debt/1e9:.2f}B ({debt_r:.1f}%) | D/E:{de:.2f}
💰 Naqd:{cash/1e9:.2f}B | FCF:{fcf:.2f}B | Div:{dy:.1f}%
━━━━━━━━━━━━━━━━━━━━
📊 P/E:{pe:.1f} P/B:{pb:.1f} ROE:{roe:.1f}% PM:{pm:.1f}%
RSI:{rsi_v:.1f} Beta:{beta:.2f}
━━━━━━━━━━━━━━━━━━━━
📐 Fib:{f38:.1f}|{f50:.1f}|{f62:.1f}
━━━━━━━━━━━━━━━━━━━━
💎 4/4:{score}/4 → {strat}
🎯 {sig}
🕐 {datetime.now(UZ).strftime('%H:%M')}"""

@bot.message_handler(commands=['start'])
def start(m): bot.reply_to(m,"Ticker: AAPL, NKE, BTC-USD")

@bot.message_handler(func=lambda m:True)
def all(m):
    try: bot.send_message(m.chat.id, analyze(m.text))
    except Exception as e: bot.send_message(m.chat.id,f"Xato:{e}")

# Render uchun port
app=Flask('')
@app.route('/')
def home(): return "Bot ishlayapti!"
def run(): app.run(host='0.0.0.0',port=int(os.environ.get('PORT',10000)))
threading.Thread(target=run).start()

print("Bot ishga tushdi...")
bot.infinity_polling()