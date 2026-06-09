import os, io, time, re
from flask import Flask
import telebot
from telebot.types import ReplyKeyboardMarkup
from curl_cffi import requests
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
import pytz

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
session = requests.Session(impersonate="chrome")

cache = {}
HALAL_DICT = {"AAPL":"✅ Halol","MSFT":"✅ Halol","TSLA":"✅ Halol","NVDA":"✅ Halol","NKE":"✅ Halol","JPM":"❌ Harom","AMZN":"⚠️ Shubhali","GOOGL":"✅ Halol"}

def get_data(ticker, days=200):
    if ticker in cache and time.time() - cache[ticker]['t'] < 120:
        return cache[ticker]['df'], cache[ticker]['name'], cache[ticker]['price']

    t = ticker.lower().replace('-','.')
    if '.' not in t: t += '.us'
    url = f"https://stooq.com/q/d/l/?s={t}&i=d"
    r = session.get(url, timeout=15)
    df = pd.read_csv(io.StringIO(r.text))
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.set_index('Date').sort_index().tail(days)
    df = df.rename(columns={'Close':'close'})[['close']].dropna()
    price = float(df['close'].iloc[-1])
    name = ticker.upper()
    cache[ticker] = {'df':df,'name':name,'price':price,'t':time.time()}
    return df, name, price

def ai_analysis(df):
    df['MA50'] = df['close'].rolling(50, min_periods=1).mean()
    df['MA200'] = df['close'].rolling(200, min_periods=1).mean()
    last = df.iloc[-1]
    score = 0
    if last['MA50'] > last['MA200']: score += 2
    if df['close'].iloc[-1] > df['close'].iloc[-20]: score += 1
    ret_1m = (df['close'].iloc[-1] / df['close'].iloc[-22] - 1) * 100 if len(df)>22 else 0
    vol = df['close'].pct_change().std() * 100
    return score, ret_1m, vol, df

def plot_competition(tickers, dfs):
    plt.figure(figsize=(10,6))
    for t in tickers:
        df = dfs[t] / dfs[t].iloc[0] * 100
        plt.plot(df.index, df['close'], label=t, linewidth=2.5)
    plt.title("🏆 Raqobat - 6 oylik natija (%)", fontsize=14)
    plt.legend()
    plt.grid(alpha=0.3)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return buf

def menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 Bozor tahlili","🕒 Bozor vaqtlari")
    kb.add("📖 Lug'at","📈 Fond bozori")
    kb.add("🐳 Kitlar & Siyosat")
    kb.row("🏆 Raqobat: AAPL vs TSLA vs NVDA")
    return kb

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Xush kelibsiz! Ticker yozing yoki:\n• 3-4 aksiya: AAPL, TSLA, MSFT\n• Raqobat uchun: AAPL vs TSLA vs NVDA", reply_markup=menu())

@bot.message_handler(func=lambda m: "vs" in m.text.lower() or (',' in m.text and len(m.text.split(','))<=4))
def competition(m):
    text = re.split(r'vs|,| ', m.text.upper())
    tickers = [t.strip() for t in text if t.strip().isalnum()][:4]
    if len(tickers) < 2: return

    bot.send_message(m.chat.id, f"⏳ {', '.join(tickers)} solishtirilmoqda...")
    results = {}; dfs = {}
    for t in tickers:
        try:
            df,name,price = get_data(t)
            score, ret, vol, df = ai_analysis(df)
            results[t] = {'price':price,'ret':ret,'vol':vol,'score':score,'name':name}
            dfs[t] = df
            time.sleep(0.5)
        except: pass

    if not results: return bot.send_message(m.chat.id,"❌ Ma'lumot topilmadi")

    winner = max(results.items(), key=lambda x: (x[1]['score'], x[1]['ret']))[0]
    txt = "🏆 RAQOBAT NATIJASI\n\n"
    for t,r in sorted(results.items(), key=lambda x: x[1]['ret'], reverse=True):
        txt += f"{t}: ${r['price']:.2f} | 1oy: {r['ret']:+.1f}% | Vol: {r['vol']:.1f}%\n"
    txt += f"\n🥇 G'OLIB: {winner} ({results[winner]['name']})"

    chart = plot_competition(tickers, dfs)
    bot.send_photo(m.chat.id, chart, caption=txt)

@bot.message_handler(func=lambda m: m.text=="📈 Fond bozori")
def fond(m):
    indices = {"SPY":"S&P500","QQQ":"Nasdaq","DIA":"Dow Jones","IWM":"Russell2000"}
    txt="📈 FOND BOZORI\n\n"
    for t,n in indices.items():
        try:
            df,_,p = get_data(t,30)
            ch = (p/df['close'].iloc[-2]-1)*100
            txt += f"{n}: ${p:.2f} ({ch:+.2f}%)\n"
        except: pass
    bot.send_message(m.chat.id, txt)

@bot.message_handler(func=lambda m: m.text=="🐳 Kitlar & Siyosat")
def whales(m):
    # Soddalashtirilgan - yirik hajmli aksiyalar
    txt = "🐳 KITLAR FAOLIYATI (oxirgi kun)\n\n"
    watch = ["AAPL","TSLA","NVDA","AMZN"]
    for t in watch:
        try:
            df,_,p = get_data(t,5)
            vol_ch = (df['close'].iloc[-1]/df['close'].iloc[-2]-1)*100
            emoji = "🟢" if vol_ch>2 else "🔴" if vol_ch<-2 else "⚪"
            txt += f"{emoji} {t}: {vol_ch:+.1f}% - {'Sotib olish' if vol_ch>2 else 'Sotish' if vol_ch<-2 else 'Kuzatish'}\n"
        except: pass
    txt += "\n💡 Siyosat: Fed stavkasi kutilmoqda - texnologiya ustun"
    bot.send_message(m.chat.id, txt)

@bot.message_handler(func=lambda m: m.text=="🕒 Bozor vaqtlari")
def times(m):
    zones={"🇺🇸 NYSE":("America/New_York",9,30,16,0)}
    now=datetime.now(pytz.timezone("America/New_York"))
    st="🟢 OCHIQ" if 9.5<=now.hour+now.minute/60<=16 and now.weekday()<5 else "🔴 YOPIQ"
    bot.send_message(m.chat.id,f"🕒 NYSE: {st}\nVaqt: {now.strftime('%H:%M')}")

@bot.message_handler(func=lambda m: m.text=="📖 Lug'at")
def lugat(m):
    txt="\n".join([f"{k}: {v}" for k,v in HALAL_DICT.items()])
    bot.send_message(m.chat.id,"📖 "+txt)

@bot.message_handler(func=lambda m: m.text=="📊 Bozor tahlili")
def market(m):
    df,_,p = get_data("SPY")
    score,ret,vol,df = ai_analysis(df)
    sig = "SOTIB OL" if score>=2 else "KUT"
    bot.send_message(m.chat.id,f"📊 S&P500: ${p:.2f}\n1oy: {ret:+.1f}%\nAI: {sig}")

@bot.message_handler(func=lambda m: True)
def single(m):
    t=m.text.strip().upper()
    if not t.isalnum() or len(t)>6: return
    try:
        df,name,price = get_data(t)
        score,ret,vol,df = ai_analysis(df)
        halal = HALAL_DICT.get(t,"ℹ️")
        plt.figure(figsize=(9,4)); plt.plot(df.index, df['close']); plt.title(t); buf=io.BytesIO(); plt.savefig(buf,format='png'); plt.close(); buf.seek(0)
        cap = f"💹 {name} ${price:.2f}\n{halal}\n1oy: {ret:+.1f}% | AI ball: {score}/3"
        bot.send_photo(m.chat.id, buf, caption=cap)
    except: bot.send_message(m.chat.id,"❌ Topilmadi")

@app.route('/')
def health(): return "OK"

if __name__=="__main__":
    import threading
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))