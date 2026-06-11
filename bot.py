import telebot
from telebot import types
import yfinance as yf
import os
import threading
from flask import Flask
from datetime import datetime

# --- CONFIG ---
TOKEN = '8781183838:AAFmgLoz6Bb8LlA-50lVAdAbNvhBCWO3sm0'
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- BAZA ---
CUSTOM_STOPS = ['TSLA', 'AAPL', 'NFLX', 'NKE']

def get_company_info(symbol):
    fallback = {
        'NFLX': {"sector":"Aloqa","industry":"Streaming","country":"AQSH","exchange":"NASDAQ","employees":"13,000","business":"Netflix streaming","revenue_q":9.37,"earnings_q":2.33,"pe":45.2,"market_cap":0.35},
        'NKE': {"sector":"Iste'mol","industry":"Kiyim","country":"AQSH","exchange":"NYSE","employees":"79,100","business":"Nike sport kiyim","revenue_q":12.43,"earnings_q":1.5,"pe":22.1,"market_cap":0.13}
    }
    return fallback.get(symbol.upper(), {"sector":"N/A","industry":"N/A","country":"N/A","exchange":"N/A","employees":"N/A","business":"Ma'lumot yo'q","revenue_q":0,"earnings_q":0,"pe":0,"market_cap":0})

def get_technical(symbol):
    try:
        df = yf.download(symbol, period="1mo", interval="1d", progress=False)
        p = df['Close'].iloc[-1]
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        return {'rsi': 50, 'trend': 'Bullish' if p > ma20 else 'Bearish', 'ma20': round(ma20,2), 'ma50': round(ma20*0.95,2), 'change': 1.2}
    except: return {'rsi': 50, 'trend': 'N/A', 'ma20': 0, 'ma50': 0, 'change': 0}

# --- ANALIZ FUNKSIYASI ---
def professional_analiz(symbol):
    try:
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info
        tech = get_technical(symbol)
        p = info.get('currentPrice', 100)
        
        return f"""🏢 {symbol.upper()} - PROFESSIONAL ANALIZ
━━━━━━━━━━━━━━━━━━━━━━
📍 KOMPANIYA:
• Sektor: {info.get('sector', 'N/A')}
• Faoliyat: {info.get('longBusinessSummary', 'Ma\'lumot yo\'q')[:100]}...

💰 MOLIYAVIY:
• P/E Ratio: {info.get('trailingPE', 0)}
• Bozor qiymati: ${info.get('marketCap', 0)/1e9:.2f} mlrd

📊 TEXNIK:
• Narx: ${p}
• Trend: {tech['trend']}
• RSI: {tech['rsi']}

🎯 SAVDO REJA:
• Kirish: ${p*0.98:.2f}
• Stop: ${p*0.92:.2f}
• TP1: ${p*1.10:.2f}
━━━━━━━━━━━━━━━━━━━━━━
⏳ {datetime.now().strftime('%H:%M')}"""
    except: return "❌ Tahlil qilishda xatolik."

# --- BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def start(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📈 Fondlar", callback_data="fond"),
           types.InlineKeyboardButton("👤 Admin", url="https://t.me/EAA_7879"))
    bot.send_message(m.chat.id, "✅ Professional Analiz Botiga xush kelibsiz!", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    if c.data == 'fond':
        kb = types.InlineKeyboardMarkup()
        for s in CUSTOM_STOPS: kb.add(types.InlineKeyboardButton(s, callback_data=f"s_{s}"))
        bot.edit_message_text("Aksiyani tanlang:", c.message.chat.id, c.message.message_id, reply_markup=kb)
    elif c.data.startswith('s_'):
        sym = c.data.split('_')[1]
        bot.send_message(c.message.chat.id, professional_analiz(sym))

# --- SERVER ---
@app.route('/')
def home(): return "Bot ishlamoqda!"

if __name__ == '__main__':
    # Flask serverini alohida thread'da ishga tushiramiz
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    # Botni ishga tushiramiz
    bot.infinity_polling()
