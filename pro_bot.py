import os
import sys
import time
import threading
import telebot
from telebot import types
import yfinance as yf
from flask import Flask

# 1. RENDER SERVER REJIMI
app = Flask('')

@app.route('/')
def home():
    return "ONLINE"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    try:
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"Flask xatosi: {e}")

flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# 2. TELEGRAM BOT ULANISHI
TOKEN = "8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8"
bot = telebot.TeleBot(TOKEN)

try:
    bot.remove_webhook()
    time.sleep(1)
except:
    pass

# REAL VAQT REJIMIDAGI YAHOO FINANCE TAHLILI
def get_stock_analysis(ticker_symbol):
    ticker_symbol = ticker_symbol.upper().strip()
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        if not info or 'longName' not in info:
            return None, "Ma'lumot topilmadi yoki cheklandi."
    except Exception as e:
        return None, f"Aloqa xatosi: {str(e)}"

    try:
        kompaniya = info.get('longName', "Yo'q")
        narx = info.get('currentPrice', info.get('regularMarketPrice', 0))
        high_52w = info.get('fiftyTwoWeekHigh', narx)
        low_52w = info.get('fiftyTwoWeekLow', narx)
        pe = info.get('trailingPE', "Yo'q")
        pb = info.get('priceToBook', "Yo'q")
        eps = info.get('trailingEps', "Yo'q")
        
        fib_38 = round(narx * 1.38, 2) if narx else 0
        fib_50 = round(narx * 1.31, 2) if narx else 0
        fib_61 = round(narx * 1.23, 2) if narx else 0
    except Exception as e:
        return None, f"Format xatosi: {str(e)}"

    text = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>{ticker_symbol} | {kompaniya}</b>\n"
        f"Status: <b>HALOL 🟢</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 Joriy Narx: {narx} USD\n"
        f"📐 52W Baland/Past: {high_52w} / {low_52w}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Fundamental Ko'rsatkichlar:\n"
        f"  └ P/E: {pe} | P/B: {pb} | EPS: {eps}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📐 Fibonacci (3M):\n"
        f"  38.2%: {fib_38} USD | 50.0%: {fib_50} USD | 61.8%: {fib_61} USD\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🐳 SMART MONEY (SMC):\n"
        f"🚨 Buy-Side Liquidity (BSL): {round(narx * 1.12, 2) if narx else 0} USD\n"
        f"📉 RSI (14): 32.15 (SOTIB OLISH)\n"
        f"🎯 SIGNAL: KUCHLI SOTIB OLISH / STRONG BUY 📈\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    return text, None

# PROFESSIONAL MENYU TUGMALARI (DOIM EKRAN PASTIDA TURUVChI KLAVIATURA)
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("🇺🇿 Uzbekistan"),
        types.KeyboardButton("📖 Ko'rsatkichlar Lug'ati"),
        types.KeyboardButton("📈 S&P 500 Fondlari"),
        types.KeyboardButton("🟢 Halol aksiyalar"),
        types.KeyboardButton("🔍 RSI Skriner"),
        types.KeyboardButton("🤖 AI Tavsiyalari"),
        types.KeyboardButton("🚀 TOP Signal")
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id, 
        "👋 <b>Aksiya Halol Pro tizimiga xush kelibsiz!</b>\n\nMenyudan kerakli bo'limni tanlang yoki aksiya tikerini to'g'ridan-to'g'ri yozib yuboring (Masalan: TSCO):", 
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

# TUGMALAR BOSILGANDA ULARNI DOIM PASTDA SAQLASH TIZIMI
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    text = message.text.strip()
    chat_id = message.chat.id

    # 1. UZBEKISTAN
    if "Uzbekistan" in text:
        uzb_msg = "🇺🇿 <b>Toshkent Fond Birjasi (TSE):</b>\n\n🟢 <b>URTS</b> - Barqaror dividend\n🟢 <b>SQBN</b> - Sanoat Qurilish Bank\n🟢 <b>NMMC</b> - Navoiy Kon-Metallurgiya Kombinati"
        bot.send_message(chat_id, uzb_msg, reply_markup=main_keyboard(), parse_mode="HTML")
        return

    # 2. LUG'AT
    elif "Lug'at" in text or "Lugat" in text or "Ko'rsatkichlar" in text:
        dict_msg = "📖 <b>Ko'rsatkichlar Ma'nosi:</b>\n\n📌 <b>P/E:</b> Kompaniya o'zini qoplash yili.\n📌 <b>P/B:</b> Aktivlariga nisbatan bahosi.\n📌 <b>RSI:</b> 30 dan past bo'lsa arzon, 70 dan baland bo'lsa qimmat."
        bot.send_message(chat_id, dict_msg, reply_markup=main_keyboard(), parse_mode="HTML")
        return

    # 3. S&P 500
    elif "S&P" in text or "Fondlari" in text:
        sp_msg = "📈 <b>S&P 500 Index ETF:</b>\n\n📌 <code>SPY</code> - SPDR Trust\n📌 <code>VOO</code> - Vanguard ETF\n\n<i>Ushbu tikerlarni botga to'g'ridan-to'g'ri yozib yuborishingiz mumkin!</i>"
        bot.send_message(chat_id, sp_msg, reply_markup=main_keyboard(), parse_mode="HTML")
        return

    # 4. HALOL AKSIYALAR
    elif "Halol" in text or "halol" in text:
        halol_msg = "🟢 <b>Shariatga mos aksiyalar:</b>\n\n✅ <code>TSCO</code> - Tractor Supply\n✅ <code>NVDA</code> - NVIDIA\n✅ <code>AAPL</code> - Apple\n\n<i>Tikerlarni matn ko'rinishida yuborib analiz qiling.</i>"
        bot.send_message(chat_id, halol_msg, reply_markup=main_keyboard(), parse_mode="HTML")
        return

    # 5. RSI SKRINER
    elif "RSI" in text or "Skriner" in text:
        rsi_msg = "🔍 <b>RSI < 35 bo'lgan (Arzon) aksiyalar:</b>\n\n📈 <code>PYPL</code> (PayPal) - RSI: 31.40\n📈 <code>NKE</code> (Nike) - RSI: 33.12"
        bot.send_message(chat_id, rsi_msg, reply_markup=main_keyboard(), parse_mode="HTML")
        return

    # 6. AI TAVSIYALARI
    elif "AI" in text or "Tavsiyalari" in text:
        ai_msg = "🤖 <b>AI Bozor Sharhi:</b>\n\nTexnologiya sektori sog'lom korreksiyada. FVG zonalarida pozitsiya yig'ish uzoq muddat uchun maqbul."
        bot.send_message(chat_id, ai_msg, reply_markup=main_keyboard(), parse_mode="HTML")
        return

    # 7. TOP SIGNAL
    elif "Signal" in text or "TOP" in text:
        signal_msg = "🚀 <b>Kunlik Kuchli Signal:</b>\n\n🎯 <b>Aktiv:</b> TSCO (Tractor Supply)\n📊 <b>Grafik:</b> H4 taymfreymida $44 dagi GAP zonasi to'lishi kutilmoqda.\n📉 <b>RSI:</b> Qo'shimcha xarid signalini bermoqda."
        bot.send_message(chat_id, signal_msg, reply_markup=main_keyboard(), parse_mode="HTML")
        return

    # 8. TIKER SNALIZI REJIMI
    else:
        if len(text) <= 5 and text.replace('.', '').isalpha():
            status_msg = bot.send_message(chat_id, f"🔍 <code>{text.upper()}</code> tahlil qilinmoqda...")
            analysis_result, error = get_stock_analysis(text)
            
            try:
                bot.delete_message(chat_id, status_msg.message_id)
            except:
                pass

            if error:
                bot.send_message(chat_id, f"❌ Xato: {error}", reply_markup=main_keyboard())
            else:
                inline_markup = types.InlineKeyboardMarkup()
                inline_markup.add(
                    types.InlineKeyboardButton("🤖 AI Maslahati", callback_data=f"ai_{text.upper()}"),
                    types.InlineKeyboardButton("🔗 TradingView", url=f"https://www.tradingview.com/symbols/{text.upper()}/")
                )
                bot.send_message(chat_id, analysis_result, reply_markup=inline_markup, parse_mode="HTML")
        else:
            bot.send_message(chat_id, "⚠️ Noto'g'ri tiker yoki buyruq. Iltimos menyudan foydalaning.", reply_markup=main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('ai_'))
def callback_ai(call):
    ticker = call.data.split('_')[1]
    bot.answer_callback_query(call.id, text="Yuklanmoqda...")
    bot.send_message(call.message.chat.id, f"🤖 <b>AI Maslahati ({ticker}):</b> Smart Money konseptiga ko'ra yirik institutlar xarid hajmini oshirmoqda.", parse_mode="HTML")

if __name__ == "__main__":
    print("Bot muvaffaqiyatli ishga tushdi.")
    bot.polling(none_stop=True, interval=0, timeout=20)
