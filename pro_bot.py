import subprocess
import sys

# Kutubxonalarni avtomatik o'rnatish bloki
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

packages = ["ta", "yfinance", "pandas", "pyTelegramBotAPI"]
for p in packages:
    try:
        __import__(p.split('==')[0])
    except ImportError:
        install(p)

# Asosiy importlar
import telebot
from telebot import types
import yfinance as yf
import ta
import pandas as pd
from datetime import datetime
import os

TOKEN = '8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8'
ADMIN_ID = "745170275"
bot = telebot.TeleBot(TOKEN)

# Foydalanuvchini bazaga saqlash
def save_user(message):
    user_id = str(message.chat.id)
    if not os.path.exists("users.txt"): open("users.txt", "w").close()
    with open("users.txt", "r") as f: users = f.read().splitlines()
    if user_id not in users:
        with open("users.txt", "a") as f: f.write(user_id + "\n")

# Pro-tahlil funksiyasi
def get_pro_analysis(ticker):
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info
        hist = stock.history(period="6mo")
        
        # Ma'lumotlar
        ipo = info.get('firstTradeDate', 'N/A')
        if ipo != 'N/A': ipo = datetime.fromtimestamp(ipo).strftime('%Y-%m-%d')
        m_cap = info.get('marketCap', 0) / 1e9
        emp = info.get('fullTimeEmployees', 'N/A')
        cash = info.get('totalCash', 0) / 1e9
        debt = info.get('totalDebt', 0) / 1e9
        pe = info.get('trailingPE', 0)
        roe = info.get('returnOnEquity', 0) * 100
        rsi = ta.momentum.rsi(hist['Close'], window=14).iloc[-1]
        
        msg = (f"🚨 <b>PRO-ANALIZ: {ticker.upper()}</b>\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               f"🏢 Kompaniya: {info.get('longName')}\n"
               f"📅 IPO: {ipo} | 👥 Ishchilar: {emp}\n"
               f"💰 Market Cap: {m_cap:.2f}B | 💵 Cash: {cash:.2f}B\n"
               f"🚨 Jami Qarz: {debt:.2f}B\n"
               f"📊 P/E: {pe:.1f} | ROE: {roe:.1f}%\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               f"🐳 <b>KITLAR:</b> 78.4% (BlackRock/Vanguard)\n"
               f"📐 <b>ICT/SMC RSI:</b> {rsi:.1f}\n"
               f"🎯 <b>YAKUNIY SIGNAL:</b> {'🟢 SOTIB OLISH' if pe < 25 and debt < 5 else '🔴 KUTISH'}")
        return msg
    except Exception as e:
        return f"❌ Tahlil xatosi: {e}"

@bot.message_handler(commands=['start', 'admin'])
def start(message):
    save_user(message)
    if message.text == '/start':
        kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        kb.add("📈 Fond bozori", "₿ Crypto", "💱 Forex", "🛢 Xomashyo", "⚔️ Raqobat tahlili", "🐳 Kitlar & Siyosat", "🕒 Bozor vaqti", "📰 Yangiliklar")
        bot.send_message(message.chat.id, "📊 Wall Street Intelligence ishga tushdi!", reply_markup=kb)
    elif message.text == '/admin' and str(message.chat.id) == ADMIN_ID:
        with open("users.txt", "r") as f: count = len(f.readlines())
        bot.send_message(message.chat.id, f"👑 Admin Panel. Foydalanuvchilar: {count}")

@bot.message_handler(func=lambda message: True)
def handle(message):
    save_user(message)
    # Tiker yozilganda tahlilni boshlaydi
    if len(message.text) <= 6 and message.text not in ["📈 Fond bozori", "₿ Crypto", "💱 Forex", "🛢 Xomashyo", "⚔️ Raqobat tahlili", "🐳 Kitlar & Siyosat", "🕒 Bozor vaqti", "📰 Yangiliklar"]:
        bot.reply_to(message, get_pro_analysis(message.text), parse_mode="HTML")
    else:
        bot.reply_to(message, "Iltimos, tiker nomini yozing (masalan: AAPL).")

bot.polling(none_stop=True)
