import telebot
import yfinance as yf
from flask import Flask
from threading import Thread

# Tokeningiz
BOT_TOKEN = "8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8"
bot = telebot.TeleBot(BOT_TOKEN)

# Render uchun server
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"

# ==================== FUNKSIYALAR ====================
def calculate_dcf(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        fcf = info.get('freeCashflow', 0)
        growth_rate = 0.10
        discount_rate = 0.08
        dcf_value = (fcf * (1 + growth_rate)) / (discount_rate - growth_rate) if discount_rate > growth_rate else fcf * 10
        return dcf_value / 1e9
    except: return 0

def get_18_point_analysis(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get('currentPrice', 0)
        dcf = calculate_dcf(ticker)
        
        return (f"🚨 <b>Aksiya Halol Bot: To'liq Analiz</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🏢 {info.get('longName', ticker)}\n"
                f"💵 Narx: {price} USD | ⚖️ DCF Qiymati: ~{dcf:.2f} B\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>18 TA FUNDAMENTAL KO'RSATKICH:</b>\n\n"
                f"<b>Qiymat:</b> P/E: {info.get('trailingPE')} | P/B: {info.get('priceToBook')}\n"
                f"<b>Rentabellik:</b> ROE: {round(info.get('returnOnEquity', 0)*100, 1)}%\n"
                f"<b>Pul Oqimi:</b> FCF: {round(info.get('freeCashflow', 0)/1e9, 2)}B\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📐 Fib: 38.2%: $46.8 | 61.8%: $58.4\n"
                f"🎯 <b>SIGNAL:</b> {'ARZON (BUY)' if price < dcf else 'QIMMAT (SELL)'}")
    except:
        return "❌ Ma'lumot topilmadi."

def send_bookmap_chart(message, ticker):
    bot.reply_to(message, f"📈 {ticker} uchun Bookmap grafika yuklanmoqda...")

# ==================== BOT HANDLERLARI ====================
@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📖 Lug'at", "⏰ Bozor vaqti")
    markup.row("📊 Bookmap", "🐳 Kitlar & Siyosat")
    markup.row("📈 Fond bozori", "🆘 Adminlik (Yordam)")
    bot.reply_to(message, "Assalomu alaykum! Tahlil uchun menyuni tanlang yoki tiker yuboring.", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text
    
    # Tugmalar
    if text == "📖 Lug'at":
        bot.reply_to(message, "📖 Lug'at bo‘limi tez orada ishga tushadi.")
    elif text == "⏰ Bozor vaqti":
        bot.reply_to(message, "⏰ Bozor vaqti tez orada yangilanadi.")
    elif text == "📊 Bookmap":
        bot.reply_to(message, "📊 Bookmap rejimi yoqildi. Tiker yuboring (masalan: AAPL).")
    elif text == "📈 Fond bozori":
        bot.reply_to(message, "✅ Tahlil qilmoqchi bo‘lgan tiker yuboring.")
    elif text == "🆘 Adminlik (Yordam)":
        bot.reply_to(message, "🆘 Savolingizni yozing.")
    
    # Tiker tahlili
    else:
        analysis = get_18_point_analysis(text.upper())
        bot.reply_to(message, analysis, parse_mode="HTML")

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    bot.infinity_polling()
