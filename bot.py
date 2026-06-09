import os, io, pytz, feedparser
import pandas as pd, numpy as np
from datetime import datetime
from flask import Flask
from curl_cffi import requests as crequests
import telebot
from telebot import types
from apscheduler.schedulers.background import BackgroundScheduler
from googletrans import Translator

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID", "0"))
tz = pytz.timezone('Asia/Tashkent')
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)
session = crequests.Session(impersonate="chrome")
tr = Translator()

SECTORS = {
 "🏦 Banklar": ["JPM","BAC","WFC","C","GS"],
 "💻 Texno": ["AAPL","MSFT","NVDA","TSLA","GOOGL","META","AMZN"],
 "🛢 Energetika": ["XOM","CVX","COP"],
 "🥇 Tilla/Kon": ["GLD","GOLD","NEM"],
 "💊 Sog'liq": ["JNJ","PFE","UNH"],
 "🛒 Savdo": ["WMT","COST","HD"]
}
CRYPTO_FATWA = {
 "BTC": ("✅ Muboh","Markazlashmagan, foiz yo'q"),
 "ETH": ("⚠️ Shubhali","Staking foizga o'xshaydi"),
 "USDT": ("❌ Haromga yaqin","Dollar foiz tizimi"),
 "BNB": ("⚠️ Shubhali","Birja tokeni"),
 "SOL": ("✅ Muboh","Texnologiya"),
 "XRP": ("✅ Muboh","To'lov"),
 "DOGE": ("❌ Harom","Meme qimor"),
 "SHIB": ("❌ Harom","Spekulyatsiya")
}
ECON = {
 "NFP":"1-juma 17:30 Toshkent — USD, tilla",
 "CPI":"12-15 kun 17:30 — inflyatsiya",
 "FOMC":"Yilda 8 marta — foiz"
}

def get_data(t, days=100):
    t=t.lower()
    if '.' not in t and len(t)<=5: t+='.us'
    url=f"https://stooq.com/q/d/l/?s={t}&i=d"
    df=pd.read_csv(io.StringIO(session.get(url,timeout=15).text))
    df.columns=[c.lower() for c in df.columns]
    return df.tail(days), t.upper(), df['close'].iloc[-1]

def get_crypto(coin):
    try:
        r=session.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin.lower()}&vs_currencies=usd&include_24hr_change=true",timeout=10).json()
        p=list(r.values())[0]; return p['usd'], p.get('usd_24h_change',0)
    except: return 0,0

def get_gold():
    try: return session.get("https://api.metals.live/v1/spot/gold",timeout=10).json()['price']
    except: return 4328.0

def ai_signal(df, price):
    df['m20']=df['close'].rolling(20).mean(); df['m50']=df['close'].rolling(50).mean()
    sup=df['close'].tail(20).min(); res=df['close'].tail(20).max()
    if price>df['m20'].iloc[-1]>df['m50'].iloc[-1]:
        sig="🟢 SOTIB OLISH"; e=price*0.99; t1=price*1.05; t2=price*1.10
    elif price<df['m20'].iloc[-1]:
        sig="🔴 SOTISH"; e=sup*0.98; t1=price*0.95; t2=sup
    else:
        sig="🟡 KUTISH"; e=df['m50'].iloc[-1]; t1=res; t2=res*1.03
    return sig, round(e,2), round(t1,2), round(t2,2), sup, res

def translate_news():
    try:
        feed=feedparser.parse("https://feeds.bloomberg.com/markets/news.rss")
        out=[]
        for e in feed.entries[:3]:
            uz=tr.translate(e.title, src='en', dest='uz').text
            out.append(f"• {uz}")
        return "\n".join(out)
    except: return "Yangilik yo'q"

def menu():
    m=types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("📈 Fond bozori","🪙 Crypto Halol")
    m.add("📰 Yangiliklar","📅 Bugungi voqealar")
    return m

@bot.message_handler(commands=['start'])
def start(m): bot.send_message(m.chat.id,"Assalomu alaykum! Tanlang:",reply_markup=menu())

@bot.message_handler(func=lambda m: m.text=="📈 Fond bozori")
def fond(m):
    kb=types.InlineKeyboardMarkup(row_width=2)
    kb.add(*[types.InlineKeyboardButton(s,callback_data=f"S_{s}") for s in SECTORS])
    bot.send_message(m.chat.id,"Sektorni tanlang:",reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("S_"))
def sec(c):
    name=c.data[2:]; txt=f"{name}\n\n"
    for t in SECTORS[name]:
        try:
            df,_,p=get_data(t,5); ch=(p-df['close'].iloc[-2])/df['close'].iloc[-2]*100
            txt+=f"{t} ${p:.2f} ({ch:+.1f}%)\n"
        except: txt+=f"{t} —\n"
    bot.send_message(c.message.chat.id, txt)

@bot.message_handler(func=lambda m: m.text=="🪙 Crypto Halol")
def crypto(m):
    kb=types.InlineKeyboardMarkup(row_width=4)
    kb.add(*[types.InlineKeyboardButton(c,callback_data=f"F_{c}") for c in CRYPTO_FATWA])
    bot.send_message(m.chat.id,"Kriptoni tanlang:",reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("F_"))
def fat(c):
    coin=c.data[2:]; status,reason=CRYPTO_FATWA[coin]; p,ch=get_crypto(coin)
    txt=f"🪙 {coin}\n${p:.4f} ({ch:+.1f}%)\n\n{status}\nSabab: {reason}"
    bot.send_message(c.message.chat.id, txt)

@bot.message_handler(func=lambda m: m.text=="📰 Yangiliklar")
def news(m): bot.send_message(m.chat.id,"📰 Bloomberg (UZ):\n"+translate_news())

@bot.message_handler(func=lambda m: m.text=="📅 Bugungi voqealar")
def ev(m):
    txt="📅 Muhim:\n"+ "\n".join([f"{k}: {v}" for k,v in ECON.items()])
    bot.send_message(m.chat.id, txt)

@bot.message_handler(func=lambda m: True)
def single(m):
    t=m.text.strip().upper()
    if t in ['XAUUSD','GOLD','TILLA']:
        p=get_gold(); df,_,_=get_data('GLD',100); s,e,t1,t2,_,_=ai_signal(df,p)
        bot.send_message(m.chat.id,f"🥇 TILLA ${p:.2f}\n{s}\nKirish ${e}\nTP ${t1}/${t2}",reply_markup=menu()); return
    if t in CRYPTO_FATWA:
        p,ch=get_crypto(t); bot.send_message(m.chat.id,f"🪙 {t} ${p:.4f}",reply_markup=menu()); return
    try:
        df,name,price=get_data(t); s,e,t1,t2,_,_=ai_signal(df,price)
        news=translate_news()
        txt=f"💹 {name} ${price:.2f}\n{s}\n💰 ${e} | 🎯 ${t1}/${t2}\n\n📰 {news[:250]}"
        bot.send_message(m.chat.id, txt, reply_markup=menu())
    except: bot.send_message(m.chat.id,"Topilmadi",reply_markup=menu())

def daily():
    if not CHAT_ID: return
    data=[]
    for t in ['NVDA','TSLA','AAPL','MSFT','AMZN']:
        try: df,_,p=get_data(t,2); ch=(p-df['close'].iloc[-2])/df['close'].iloc[-2]*100; data.append((t,ch))
        except: pass
    data.sort(key=lambda x:x[1],reverse=True)
    msg="📊 TOP-5\n"+ "\n".join([f"{t} {c:+.1f}%" for t,c in data])
    bot.send_message(CHAT_ID, msg)

sched=BackgroundScheduler(timezone=tz)
sched.add_job(daily,'cron',hour=9,minute=0)
sched.start()

@app.route('/')
def home(): return "OK"

if __name__=="__main__":
    import threading; threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True),daemon=True).start()
    app.run(host='0.0.0.0',port=int(os.getenv("PORT",10000)))