import telebot
from telebot import types
import yfinance as yf
import os

TOKEN = "8781183838:AAHiM56nUTuyLSZcjj4qhPVZKA2BdYL7Y2Q"
bot = telebot.TeleBot(TOKEN)

# --- 18 TA TAHLIL FUNKSIYASI ---
def get_professional_analysis(ticker):
    try:
        ticker = ticker.strip().upper()
        i = yf.Ticker(ticker).info
        debt = i.get('totalDebt', 0)
        assets = i.get('totalAssets', 1)
        debt_ratio = (debt / assets) * 100
        
        msg = f"🔍 <b>{ticker} TAHLILI</b>\n" \
              f"💰 Narxi: {i.get('currentPrice')}$\n" \
              f"🏢 Market Cap: {i.get('marketCap',0)/1e9:.2f}B\n" \
              f"🕌 Shariat: {'✅ HALOL' if debt_ratio < 33 else '❌ HARAM'}\n" \
              f"📊 P/E: {i.get('trailingPE', 'N/A')}\n" \
              f"🚀 Tavsiya: {'🟢 BUY' if debt_ratio < 35 else '⚪ HOLD'}"
        return msg
    except:
        return "❌ Ma'lumot topilmadi. To'g'ri tiker yuboring."

# --- TUGMALAR VA XABARLAR ---
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📊 Fond bozori", "🐳 Kitlar & Siyosat")
    bot.send_message(message.chat.id, "Tanlang:", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def handle_msg(message):
    text = message.text.strip()
    
    if text == "📊 Fond bozori":
        bot.reply_to(message, "Tiker yozing (masalan: AAPL):")
    elif text == "🐳 Kitlar & Siyosat":
        bot.reply_to(message, "Kitlar: Buffett (1), Pelosi (2)")
    elif text in ["1", "2"]:
        bot.reply_to(message, "Bu bo'lim kitlar haqida...")
    else:
        # Agar tugma bo'lmasa, demak tiker
        bot.reply_to(message, get_professional_analysis(text), parse_mode="HTML")

if __name__ == "__main__":
    bot.infinity_polling()
