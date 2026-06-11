import telebot
import yfinance as yf
import pandas as pd
import numpy as np
import ta

TOKEN = "8781183838:AAFmgLoz6Bb8LlA-50lVAdAbNvhBCWO3sm0"
bot = telebot.TeleBot(TOKEN)

# ===================== TEXNIK ANALIZ =====================
def texnik_analiz(symbol):
    try:
        data = yf.download(symbol, period="1mo", interval="1h", progress=False)
        if data.empty: return "❌ Ma'lumot topilmadi."

        # RSI
        data['rsi'] = ta.momentum.RSIIndicator(data['Close']).rsi()

        # Bollinger Bands
        bb = ta.volatility.BollingerBands(data['Close'])
        data['bb_high'] = bb.bollinger_hband()
        data['bb_low'] = bb.bollinger_lband()

        last = data.iloc[-1]
        signal = "NO SIGNAL ❌"
        sl, tp = 0, 0

        if last['rsi'] < 30 and last['Close'] < last['bb_low']:
            signal = "BUY 🟢"
            sl, tp = last['Close'] * 0.995, last['Close'] * 1.010
        elif last['rsi'] > 70 and last['Close'] > last['bb_high']:
            signal = "SELL 🔴"
            sl, tp = last['Close'] * 1.005, last['Close'] * 0.990

        return f"📊 {symbol} TEXNIK ANALIZ\n\nRSI: {round(last['rsi'],2)}\nNarx: {round(last['Close'],2)}\n\nSignal: {signal}\n\nSL: {round(sl,2)}\nTP: {round(tp,2)}"
    except Exception as e:
        return f"❌ Xatolik: {str(e)}"

# ===================== GOLD STRATEGIYA =====================
def gold_strategy():
    try:
        data = yf.download("XAUUSD=X", period="1mo", interval="15m", progress=False)
        data['rsi'] = ta.momentum.RSIIndicator(data['Close']).rsi()
        last = data.iloc[-1]
        
        if last['rsi'] < 25:
            return f"🥇 GOLD (BUY) 🟢\nNarx: {round(last['Close'],2)}\nRSI: {round(last['rsi'],2)}"
        elif last['rsi'] > 75:
            return f"🥇 GOLD (SELL) 🔴\nNarx: {round(last['Close'],2)}\nRSI: {round(last['rsi'],2)}"
        return "🥇 GOLD: Hozircha signal yo'q."
    except: return "❌ Gold ma'lumotlari yuklanmadi."

# ===================== COMMANDLAR =====================
@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, "🤖 PRO TRADING BOT ISHLAMOQDA\n\nBuyruqlar:\n/gold - GOLD signal\n/forex EURUSD=X\n/crypto BTC-USD\n/stock AAPL")

@bot.message_handler(commands=['gold'])
def gold(msg): bot.reply_to(msg, gold_strategy())

@bot.message_handler(commands=['forex', 'crypto', 'stock'])
def handle_market(msg):
    try:
        symbol = msg.text.split()[1]
        bot.reply_to(msg, texnik_analiz(symbol))
    except:
        bot.reply_to(msg, "Masalan: /stock AAPL yoki /forex EURUSD=X")

print("Bot ishga tushdi...")
bot.infinity_polling()
