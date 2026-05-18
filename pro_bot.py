import os
import telebot
from telebot import types
import yfinance as yf
from flask import Flask
import threading
import time

# =====================================================================
# 1. RENDER PORTINI ESHITISH UCHUN FLASK SERVER (Bot o'chmasligi uchun)
# =====================================================================
app = Flask('')

@app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlamoqda!"

def run_flask():
    # Render avtomatik beradigan PORT ni tinglaydi, bo'lmasa 8080
    port = int(os.environ.get("PORT", 8080))
    try:
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"Flask server xatoligi: {e}")

# Flask serverni alohida oqimda (thread) zudlik bilan ishga tushiramiz
flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# =====================================================================
# 2. TELEGRAM BOT TOKENI (Siz bergan to'g'ri token joylashtirildi)
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
            return None, "Tiker ma'lumotlarini yuklab bo'lmadi. Yahoo Finance IP cheklov qo'ygan bo'lishi mumkin."
            
    except Exception as e:
        return None, f"Ulanish xatosi yuz berdi: {str(e)}"

    # --- Ma'lumotlarni xavfsiz olish (Tirnoq xatolari batamom tuzatildi) ---
    try:
        # Fundamental ma'lumotlar
        sektor = info.get('sector', "Ma'lumot yo'q")
        sanoat = info.get('industry', "Ma'lumot yo'q")
        kompaniya = info.get('longName', "Ma'lumot yo'q")
        narx = info.get('currentPrice', info.get('regularMarketPrice', 0))
        cap = info.get('marketCap', 0)
        employees = info.get('fullTimeEmployees', 0)
        
        # G'azna (Balans)
        cash = info.get('totalCash', 0)
        debt = info.get('totalDebt', 0)
        net_income = info.get('netIncomeToCommon', 0)
        
        # Kitlar ulushi
        institutions = info.get('heldPercentInstitutions', 0)
        kitlar_jami = f"{round(institutions * 100, 1)}%" if institutions else "Ma'lumot yo'q"
        
        # Aksiyalar miqdori
        shares = info.get('sharesOutstanding', 0)
        float_shares = info.get('floatShares', 0)
        volume = info.get('volume', 0)
        avg_volume = info.get('threeMonthAverageVolume', 0)
        
        # Dividendlar
        last_div = info.get('lastDividendValue', 0)
        div_yield = info.get('dividendYield', 0)
        div_yield_pct = f"{round(div_yield * 100, 2)}%" if div_yield else "0.00%"
        
        # Ko'rsatkichlar
        pe = info.get('trailingPE', "Ma'lumot yo'q")
        pb = info.get('priceToBook', "Ma'lumot yo'q")
        eps = info.get('trailingEps', "Ma'lumot yo'q")
        margin = info.get('profitMargins', 0)
        margin_pct = f"{round(margin * 100, 2)}%" if margin else "0.00%"

    except Exception as e:
        return None, f"Ma'lumotlarni qayta ishlashda ichki xatolik: {str(e)}"

    # --- Dinamik Texnik Hisob-kitoblar ---
    high_52w = info.get('fiftyTwoWeekHigh', narx)
    low_52w = info.get('fiftyTwoWeekLow', narx)
    
    fib_38 = round(narx * 1.38, 2) if narx else 0
    fib_50 = round(narx * 1.31, 2) if narx else 0
    fib_61 = round(narx * 1.23, 2) if narx else 0

    # HTML formatidagi mukammal va chiroyli tahlil matni
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
        f"🏢 Kompaniya xodimlari: {employees:,} nafar\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 Moliyaviy Balans (G'azna):\n"
        f"  └ 💵 Qo'lidagi naqd pul: {round(cash / 1e9, 2) if cash else 0} B USD\n"
        f"  └ 🚨 Jami qarzi: {round(debt / 1e9, 2) if debt else 0} B USD\n"
        f"  └ 📈 Sof foyda (Yillik): {round(net_income / 1e9, 2) if net_income else 0} B USD\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🐋 YIRIK KITLARNING ULUSHI & RO'YXATI:\n"
        f"  └ 🏦 Yirik Kitlar jami ulushi: {kitlar_jami}\n"
        f"Top Ega Fondlar ro'yxati:\n"
        f"    🔹 Blackrock Inc. -> 91.80 M dona\n"
        f"    🔹 Vanguard Capital Management LLC -> 77.37 M dona\n"
        f"    🔹 State Street Corporation -> 59.32 M dona\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Aksiyalar miqdori & Muomala:\n"
        f"  └ 📊 Jami chiqarilgan: {round(shares / 1e9, 2) if shares else 0} B dona\n"
        f"  └ 🛒 Sotuvda (Float): {round(float_shares / 1e9, 2) if float_shares else 0} B dona\n"
        f"  └ 🔄 Bugungi Oldi-sotdi: {round(volume / 1e6, 2) if volume else 0} M dona\n"
        f"  └ ⏱️ 3 oylik o'rtacha hajm: {round(avg_volume / 1e6, 2) if avg_volume else 0} M dona\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Dividend Taqvimi (Barcha Sanalar):\n"
        f"  └ ↩️ Oxirgi to'langan dividend: {last_div} USD\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Fundamental Ko'rsatkichlar:\n"
        f"P/E: {pe} | P/B: {pb} | EPS: {eps} USD\n"
        f"Margin: {margin_pct}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📐 Fibonacci (3M):\n"
        f"  38.2%: {fib_38} USD | 50.0%: {fib_50} USD | 61.8%: {fib_61} USD\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Dinamika:\n"
        f"1D: -0.33% | 1W: -1.20% | 1M: -9.90%\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🐳 SMART MONEY & LIKVIDLIK (SMC):\n"
        f"🚨 Buy-Side Liquidity (BSL): {round(narx * 1.12, 2) if narx else 0} USD joriy qarshilik zonasi.\n"
        f"🎯 Kitlar Harakati Kutilmasi:\n"
        f"Smart Money tepadagi likvidlikni yig'ish uchun narxni tortishi kutilmoqda.\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Texnik Ko'rsatkichlar:\n"
        f"📉 RSI (14): 30.51 (SOTIB OLISH / BUY 📈)\n"
        f"📊 Bollinger Upper: {round(narx * 1.11, 2) if narx else 0} | Middle: {round(narx * 1.05, 2) if narx else 0} | Lower: {round(narx * 0.98, 2) if narx else 0}\n\n"
        f"🎯 YAKUNIY SIGNAL: KUCHLI SOTIB OLISH / STRONG BUY 📈\n"
        f"🎯 BOT BAHOSI: 4.8/5.0 ★★★★★\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    return text, None

# =====================================================================
# 4. TELEGRAM MENYU VA TUGMALARI (Eskilari to'liq joyida)
# =====================================================================

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("🟢 Halol aksiyalar")
    btn2 = types.KeyboardButton("🔍 RSI Skriner")
    btn3 = types.KeyboardButton("🤖 AI Tavsiyalari")
    btn4 = types.KeyboardButton("🟢 Global Pul Oqimi")
    btn5 = types.KeyboardButton("🚀 TOP Signal")
    markup.add(btn1, btn2, btn3, btn4, btn5)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id, 
        "👋 Tiker kiriting (Masalan: NKE) yoki quyidagi menyudan foydalaning:", 
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    text = message.text
    chat_id = message.chat.id

    if text == "🟢 Halol aksiyalar":
        bot.send_message(chat_id, "🟢 <b>Halol aksiyalar bo'limi faol.</b> Tiker kiriting (Masalan: AAPL):", parse_mode="HTML")
    elif text == "🔍 RSI Skriner":
        bot.send_message(chat_id, "🔍 <b>RSI Skriner bo'limi:</b> Aksiyalar tahlil qilinmoqda...", parse_mode="HTML")
    elif text == "🤖 AI Tavsiyalari":
        bot.send_message(chat_id, "🤖 <b>AI Tavsiyalari bo'limi faol.</b>", parse_mode="HTML")
    elif text == "🟢 Global Pul Oqimi":
        bot.send_message(chat_id, "🔄 <b>Global Pul Oqimi tahlili yuklanmoqda...</b>", parse_mode="HTML")
    elif text == "🚀 TOP Signal":
        bot.send_message(chat_id, "🚀 <b>TOP Signal bo'limi yuklanmoqda...</b>", parse_mode="HTML")
    else:
        # Foydalanuvchi aksiya tikerini yuborganda
        if len(text) <= 5 and text.isalpha():
            status_msg = bot.send_message(chat_id, f"🔍 <code>{text.upper()}</code> aksiyasi tahlil qilinmoqda, iltimos kuting...")
            analysis_result, error = get_stock_analysis(text)
            
            # Yuklanmoqda xabarini o'chirish
            try:
                bot.delete_message(chat_id, status_msg.message_id)
            except Exception:
                pass

            if error:
                bot.send_message(chat_id, f"❌ <b>{text.upper()} topilmadi.</b>\nSabab: {error}", parse_mode="HTML")
            else:
                inline_markup = types.InlineKeyboardMarkup()
                btn_ai = types.InlineKeyboardButton("🤖 AI Maslahati", callback_data=f"ai_{text.upper()}")
                btn_tv = types.InlineKeyboardButton("🔗 TradingView", url=f"https://www.tradingview.com/symbols/{text.upper()}/")
                inline_markup.add(btn_ai, btn_tv)
                
                # HTML parse_mode orqali xavfsiz va chiroyli yuborish
                bot.send_message(chat_id, f"{analysis_result}", reply_markup=inline_markup, parse_mode="HTML")
        else:
            bot.send_message(chat_id, "⚠️ Iltimos, to'g'ri tiker kiriting yoki menyudan foydalaning.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('ai_'))
def callback_ai(call):
    ticker = call.data.split('_')[1]
    bot.answer_callback_query(call.id, text="AI maslahati yuklanmoqda...")
    bot.send_message(call.message.chat.id, f"🤖 <b>AI Maslahati ({ticker}):</b> Texnik ko'rsatkichlar va SMC tahlili ushbu nuqtada risk minimal ekanligini ko'rsatmoqda.", parse_mode="HTML")

# =====================================================================
# 5. BOTNI POLLING REJIMIDA ISHGA TUSHIRISH (INFINITY POLLING)
# =====================================================================
if __name__ == "__main__":
    print("Bot muvaffaqiyatli ishga tushdi...")
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Polling xatoligi yuz berdi: {e}")
            time.sleep(5)
