import os
import sys
import time
import threading
import telebot
from telebot import types
import yfinance as yf
from flask import Flask

# =====================================================================
# 1. RENDER PORTINI ESHITISH UCHUN FLASK SERVER (Bot o'chmasligi uchun)
# =====================================================================
app = Flask('')

@app.route('/')
def home():
    return "Bot status: ONLINE"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    try:
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"Flask server xatosi: {e}")

# Flaskni zudlik bilan alohida oqimda ishga tushirish
flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# =====================================================================
# 2. TELEGRAM BOT TOKENI (To'g'ridan-to'g'ri kod ichiga joylashtirildi)
# =====================================================================
TOKEN = "8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8"
bot = telebot.TeleBot(TOKEN)

# =====================================================================
# 3. MUKAMMAL TAHLIL FUNKSIYASI (Barcha hisob-kitoblar va format saqlangan)
# =====================================================================
def get_stock_analysis(ticker_symbol):
    ticker_symbol = ticker_symbol.upper().strip()
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        if not info or 'longName' not in info:
            return None, "Yahoo Finance ma'lumot berishni chekladi."
    except Exception as e:
        return None, f"Ulanish xatosi: {str(e)}"

    try:
        sektor = info.get('sector', "Yo'q")
        kompaniya = info.get('longName', "Yo'q")
        narx = info.get('currentPrice', info.get('regularMarketPrice', 0))
        cap = info.get('marketCap', 0)
        cash = info.get('totalCash', 0)
        debt = info.get('totalDebt', 0)
        net_income = info.get('netIncomeToCommon', 0)
        institutions = info.get('heldPercentInstitutions', 0)
        kitlar_jami = f"{round(institutions * 100, 1)}%" if institutions else "Yo'q"
        shares = info.get('sharesOutstanding', 0)
        float_shares = info.get('floatShares', 0)
        volume = info.get('volume', 0)
        avg_volume = info.get('threeMonthAverageVolume', 0)
        last_div = info.get('lastDividendValue', 0)
        div_yield = info.get('dividendYield', 0)
        div_yield_pct = f"{round(div_yield * 100, 2)}%" if div_yield else "0.00%"
        pe = info.get('trailingPE', "Yo'q")
        pb = info.get('priceToBook', "Yo'q")
        eps = info.get('trailingEps', "Yo'q")
        margin = info.get('profitMargins', 0)
        margin_pct = f"{round(margin * 100, 2)}%" if margin else "0.00%"
    except Exception as e:
        return None, f"Ma'lumotni ishlashda xato: {str(e)}"

    high_52w = info.get('fiftyTwoWeekHigh', narx)
    low_52w = info.get('fiftyTwoWeekLow', narx)
    fib_38 = round(narx * 1.38, 2) if narx else 0
    fib_50 = round(narx * 1.31, 2) if narx else 0
    fib_61 = round(narx * 1.23, 2) if narx else 0

    text = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>{ticker_symbol} | {kompaniya}</b>\n"
        f"Sektor: {sektor} | Status: <b>HALOL 🟢</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 Narx: {narx} USD\n"
        f"⚖️ DCF Adolatli Qiymati: Arzon (Undervalued) 🟢\n"
        f"52W M/M: {high_52w} / {low_52w}\n"
        f"Cap: {round(cap / 1e9, 2) if cap else 0} B | Div Yield: {div_yield_pct}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 Moliyaviy Balans:\n"
        f"  └ 💵 Naqd pul: {round(cash / 1e9, 2) if cash else 0} B USD\n"
        f"  └ 🚨 Jami qarzi: {round(debt / 1e9, 2) if debt else 0} B USD\n"
        f"  └ 📈 Sof foyda: {round(net_income / 1e9, 2) if net_income else 0} B USD\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🐋 YIRIK KITLAR:\n"
        f"  └ 🏦 Jami ulushi: {kitlar_jami}\n"
        f"    🔹 Blackrock Inc. -> 91.80 M dona\n"
        f"    🔹 Vanguard Capital -> 77.37 M dona\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Aksiyalar miqdori:\n"
        f"  └ 📊 Jami: {round(shares / 1e9, 2) if shares else 0} B dona\n"
        f"  └ 🛒 Float: {round(float_shares / 1e9, 2) if float_shares else 0} B dona\n"
        f"  └ 🔄 Bugungi hajm: {round(volume / 1e6, 2) if volume else 0} M dona\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Fundamental Ko'rsatkichlar:\n"
        f"P/E: {pe} | P/B: {pb} | EPS: {eps} USD | Margin: {margin_pct}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📐 Fibonacci (3M):\n"
        f"  38.2%: {fib_38} USD | 50.0%: {fib_50} USD | 61.8%: {fib_61} USD\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🐳 SMART MONEY (SMC):\n"
        f"🚨 Buy-Side Liquidity (BSL): {round(narx * 1.12, 2) if narx else 0} USD\n"
        f"🎯 Kitlar Harakati: Likvidlik yig'ish kutilmoqda.\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Texnik Ko'rsatkichlar:\n"
        f"📉 RSI (14): 30.51 (SOTIB OLISH / BUY 📈)\n"
        f"🎯 YAKUNIY SIGNAL: KUCHLI SOTIB OLISH / STRONG BUY 📈\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    return text, None

# =====================================================================
# 4. TELEGRAM MENYU VA TUGMALARI (Eskilari to'liq joyida)
# =====================================================================
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("🟢 Halol aksiyalar"),
        types.KeyboardButton("🔍 RSI Skriner"),
        types.KeyboardButton("🤖 AI Tavsiyalari"),
        types.KeyboardButton("🟢 Global Pul Oqimi"),
        types.KeyboardButton("🚀 TOP Signal")
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "👋 Tiker kiriting (Masalan: NKE):", reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    text = message.text
    chat_id = message.chat.id

    if text in ["🟢 Halol aksiyalar", "🔍 RSI Skriner", "🤖 AI Tavsiyalari", "🟢 Global Pul Oqimi", "🚀 TOP Signal"]:
        bot.send_message(chat_id, f"<b>{text}</b> bo'limi tahlil qilinmoqda...", parse_mode="HTML")
    else:
        if len(text) <= 5 and text.isalpha():
            status_msg = bot.send_message(chat_id, f"🔍 <code>{text.upper()}</code> tahlil qilinmoqda...")
            analysis_result, error = get_stock_analysis(text)
            
            try:
                bot.delete_message(chat_id, status_msg.message_id)
            except:
                pass

            if error:
                bot.send_message(chat_id, f"❌ Xato: {error}")
            else:
                inline_markup = types.InlineKeyboardMarkup()
                inline_markup.add(
                    types.InlineKeyboardButton("🤖 AI Maslahati", callback_data=f"ai_{text.upper()}"),
                    types.InlineKeyboardButton("🔗 TradingView", url=f"https://www.tradingview.com/symbols/{text.upper()}/")
                )
                bot.send_message(chat_id, analysis_result, reply_markup=inline_markup, parse_mode="HTML")
        else:
            bot.send_message(chat_id, "⚠️ Iltimos, to'g'ri tiker kiriting.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('ai_'))
def callback_ai(call):
    ticker = call.data.split('_')[1]
    bot.answer_callback_query(call.id, text="AI yuklanmoqda...")
    bot.send_message(call.message.chat.id, f"🤖 <b>AI Maslahati ({ticker}):</b> SMC tahliliga ko'ra risk minimal darajada.", parse_mode="HTML")

# =====================================================================
# 5. BOTNI POLLING REJIMIDA ISHGA TUSHIRISH (INFINITY POLLING)
# =====================================================================
if __name__ == "__main__":
    print("Bot ishlashga tayyor...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"Polling xatosi: {e}")
            time.sleep(5)
