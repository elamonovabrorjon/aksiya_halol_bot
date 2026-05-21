import subprocess
import sys
import time
import os
from threading import Thread
from flask import Flask

# 1. Kutubxonalarni o'rnatish
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

packages = ["ta", "yfinance", "pandas", "pyTelegramBotAPI", "flask"]
for p in packages:
    try:
        __import__(p.split('==')[0])
    except ImportError:
        install(p)

import telebot
from telebot import types
import yfinance as yf
import ta
import pandas as pd
from datetime import datetime

TOKEN = '8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8'
ADMIN_ID = "745170275"
bot = telebot.TeleBot(TOKEN)

# --- Render uchun Web Server ---
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

t = Thread(target=run_web)
t.start()

# --- Funksiyalar ---
def save_user(message):
    user_id = str(message.chat.id)
    if not os.path.exists("users.txt"): open("users.txt", "w").close()
    with open("users.txt", "r") as f: users = f.read().splitlines()
    if user_id not in users:
        with open("users.txt", "a") as f: f.write(user_id + "\n")

def get_pro_analysis(ticker):
    try:
        time.sleep(1.5)
        stock = yf.Ticker(ticker.upper())
        info = stock.info
        hist = stock.history(period="1mo")
        if hist.empty: return "❌ Bunday tiker topilmadi."
        
        ipo = info.get('firstTradeDate', 'N/A')
        if ipo != 'N/A': ipo = datetime.fromtimestamp(ipo).strftime('%Y-%m-%d')
        m_cap = info.get('marketCap', 0) / 1e9
        pe = info.get('trailingPE', 0)
        rsi = ta.momentum.rsi(hist['Close'], window=14).iloc[-1]
        
        return (f"🚨 <b>PRO-ANALIZ: {ticker.upper()}</b>\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               f"🏢 Kompaniya: {info.get('longName', 'N/A')}\n"
               f"💰 Market Cap: {m_cap:.2f}B | 📊 P/E: {pe:.1f}\n"
               f"📐 <b>RSI:</b> {rsi:.1f}\n"
               f"🎯 <b>SIGNAL:</b> {'🟢 SOTIB OLISH' if pe < 25 else '🔴 KUTISH'}")
    except: return "❌ Tahlil xatosi."

# --- Admin Buyruqlari ---
@bot.message_handler(commands=['stat'])
def stats(message):
    if str(message.chat.id) == ADMIN_ID:
        if os.path.exists("users.txt"):
            with open("users.txt", "r") as f: count = len(f.readlines())
            bot.reply_to(message, f"👥 Foydalanuvchilar soni: {count}")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if str(message.chat.id) == ADMIN_ID:
        text = message.text.replace("/broadcast ", "")
        if os.path.exists("users.txt"):
            with open("users.txt", "r") as f:
                for line in f:
                    try: bot.send_message(line.strip(), text)
                    except: continue
            bot.reply_to(message, "✅ Xabar yuborildi.")

@bot.message_handler(commands=['ban'])
def ban(message):
    if str(message.chat.id) == ADMIN_ID:
        target_id = message.text.split()[1]
        with open("banned.txt", "a") as f: f.write(target_id + "\n")
        bot.reply_to(message, f"🚫 Foydalanuvchi {target_id} bloklandi.")

# --- Asosiy Handler ---
@bot.message_handler(commands=['start'])
def start(message):
    # Bloklanganmi tekshirish
    if os.path.exists("banned.txt"):
        with open("banned.txt", "r") as f:
            if str(message.chat.id) in f.read().splitlines(): return
            
    save_user(message)
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📈 Halol aksiyalar", "🔍 RSI Skriner", "🤖 AI Tavsiyalari")
    bot.send_message(message.chat.id, "🇺🇿 UFinanz Terminaliga xush kelibsiz!", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle(message):
    bot.reply_to(message, get_pro_analysis(message.text), parse_mode="HTML")

if __name__ == '__main__':
    bot.infinity_polling(skip_pending=True)
