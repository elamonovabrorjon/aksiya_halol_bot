import subprocess
import sys
import time
import os

# 1. Kutubxonalarni avtomatik o'rnatish
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

packages = ["ta", "yfinance", "pandas", "pyTelegramBotAPI"]
for p in packages:
    try:
        __import__(p.split('==')[0])
    except ImportError:
        install(p)

# 2. Asosiy importlar
import telebot
from telebot import types
import yfinance as yf
import ta
import pandas as pd
from datetime import datetime

TOKEN = '8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8'
ADMIN_ID = "745170275"
bot = telebot.TeleBot(TOKEN)

# 3. Foydalanuvchini bazaga saqlash
def save_user(message):
    user_id = str(message.chat.id)
    if not os.path.exists("users.txt"): open("users.txt", "w").close()
    with open("users.txt", "r") as f: users = f.read().splitlines()
    if user_id not in users:
        with open("users.txt", "a") as f: f.write(user_id + "\n")

# 4. Pro-tahlil funksiyasi (Rate limit himoyasi bilan)
def get_pro_analysis(ticker):
    try:
        time.sleep(1.5) # Server yuklamasini kamaytirish
        stock = yf.Ticker(ticker.upper())
        info = stock.info
        hist = stock.history(period="1mo")
        
        if hist.empty: return "❌ Bunday tiker topilmadi."

        ipo = info.get('firstTradeDate', 'N/A')
        if ipo != 'N/A': ipo = datetime.fromtimestamp(ipo).strftime('%Y-%m-%d')
        m_cap = info.get('marketCap', 0) / 1e9
        pe = info.get('trailingPE', 0)
        rsi = ta.momentum.rsi(hist['Close'], window=14).iloc[-1]
        
        msg = (f"🚨 <b>PRO-ANALIZ: {ticker.upper()}</b>\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               f"🏢 Kompaniya: {info.get('longName', 'N/A')}\n"
               f"📅 IPO: {ipo}\n"
               f"💰 Market Cap: {m_cap:.2f}B\n"
               f"📊 P/E: {pe:.1f}\n"
               f"📐 <b>RSI:</b> {rsi:.1f}\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               f"🎯 <b>SIGNAL:</b> {'🟢 SOTIB OLISH' if pe < 25 else '🔴 KUTISH'}")
        return msg
    except Exception as e:
        if "429" in str(e): return "⏳ Server band, 1 daqiqa kuting."
        return f"❌ Tahlil xatosi."

# 5. Menyu va xabar boshqaruvi
@bot.message_handler(commands=['start'])
def start(message):
    save_user(message)
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📈 Halol aksiyalar", "🔍 RSI Skriner", "🏛 NYSE birjasi", "💻 NASDAQ birjasi", "🇺🇸 S&P 500 indeks", "🤖 AI Tavsiyalari", "🕒 Bozor vaqti")
    bot.send_message(message.chat.id, "🇺🇿 UFinanz Terminaliga xush kelibsiz! Tiker kiriting:", reply_markup=markup, parse_mode="HTML")

@bot.message_handler(func=lambda message: True)
def handle(message):
    if message.text in ["📈 Halol aksiyalar", "🔍 RSI Skriner", "🏛 NYSE birjasi", "💻 NASDAQ birjasi", "🇺🇸 S&P 500 indeks", "🤖 AI Tavsiyalari", "🕒 Bozor vaqti"]:
        bot.reply_to(message, "Bu bo'lim tez orada ishga tushadi. Tiker nomini yozing (masalan: AAPL):")
    else:
        bot.reply_to(message, get_pro_analysis(message.text), parse_mode="HTML")

# 6. Botni ishga tushirish (Konfliktga qarshi himoya)
if __name__ == '__main__':
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
