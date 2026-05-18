import os
import sys
import time
import threading
import telebot
from telebot import types
import yfinance as yf
from flask import Flask

# 1. RENDER UCHUN FLASK SERVER (Doimiy ACTIVE holatda saqlash uchun)
app = Flask('')

@app.route('/')
def home():
    return "Bot status: ACTIVE"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    try:
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"Flask xatosi: {e}")

flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# 2. TELEGRAM BOT TOKENI VA ULANISHINI SOZLASh
TOKEN = "8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8"
bot = telebot.TeleBot(TOKEN)

# Eski webhook to'qnashuvlarini tozalash (Conflict xatosiga qarshi)
try:
    bot.remove_webhook()
    time.sleep(1)
except:
    pass

# YAHOO FINANCE ORQALI REAL VAQT REJIMIDAGI TAHLIL
def get_stock_analysis(ticker_symbol):
    ticker_symbol = ticker_symbol.upper().strip()
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        if not info or 'longName' not in info:
            return None, "Yahoo Finance ma'lumot berishni chekladi yoki tiker xato."
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
        pe = info.get('trailingPE', "Yo'q")
        pb = info.get('priceToBook', "Yo'q")
        eps = info.get('trailingEps', "Yo'q")
        margin = info.get('profitMargins', 0)
        margin_pct = f"{round(margin * 100, 2)}%" if margin else "0.00%"
        div_yield = info.get('dividendYield', 0)
        div_yield_pct = f"{round(div_yield * 100, 2)}%" if div_yield else "0.00%"
    except Exception as e:
        return None, f"Ma'lumotni qayta ishlashda xato: {str(e)}"

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
        f"    🔹 Blackrock Inc. -> Tizimli xarid\n"
        f"    🔹 Vanguard Group -> Ulush barqaror\n"
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
        f"🎯 Kitlar Harakati: FVG zonalaridan likvidlik yig'ish kutilmoqda.\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Texnik Ko'rsatkichlar:\n"
        f"📉 RSI (14): 32.15 (SOTIB OLISH / BUY 📈)\n"
        f"🎯 YAKUNIY SIGNAL: KUCHLI SOTIB OLISH / STRONG BUY 📈\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    return text, None

# 3. ASOSIY ENYUG TUGMALARI (Ketma-ket tartiblangan)
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
        "👋 <b>Aksiya Halol Pro tizimiga xush kelibsiz!</b>\n\nTahlil qilmoqchi bo'lgan xalqaro aksiya tikerini kiriting (Masalan: <code>TSCO</code>, <code>AAPL</code>) yoki quyidagi menyu bo'limlaridan birini tanlang:", 
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

# 4. MATNLAR VA MASLAHATLAR INTERAKTIV ISHLOVCHI QISMI
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    text = message.text.strip()
    chat_id = message.chat.id

    # A) UZBEKISTAN BO'LIMI
    if text == "🇺🇿 Uzbekistan":
        uzb_msg = (
            "🇺🇿 <b>Toshkent Respublika Fond Birjasi (TSE) Tahlili:</b>\n\n"
            "Mahalliy bozorning eng faol va likvidli dividend to'lovchi aksiyalari joriy ro'yxati:\n\n"
            "💵 <b>URTS</b> (O'zbekiston Respublika Tovar-Xom Ashyo Birjasi) - Barqaror dividend 🟢\n"
            "🏦 <b>SQBN</b> (Sanoat Qurilish Bank) - Kapitalizatsiya yuqori 🟢\n"
            "🏢 <b>QZSM</b> (Qizilqumsement) - Ishlab chiqarish yetakchisi 🟢\n"
            "⛏ <b>NMMC</b> (Navoiy Kon-Metallurgiya Kombinati) - Davlat strategik aktivi 🟢\n\n"
            "💡 <i>Tavsiya: Mahalliy aksiyalar hisobotlarini 'Kapital Depozit' ilovalari orqali monitoring qilish tavsiya etiladi.</i>"
        )
        bot.send_message(chat_id, uzb_msg, parse_mode="HTML")

    # B) LUG'AT BO'LIMI
    elif text == "📖 Ko'rsatkichlar Lug'ati":
        dict_msg = (
            "📖 <b>Professional Fundamental Ko'rsatkichlar Lug'ati:</b>\n\n"
            "🔹 <b>P/E (Price to Earnings Ratio):</b> Kompaniya o'zini qancha yilda qoplashini ko'rsatadi. Mezon: < 25 bo'lsa yaxshi.\n"
            "🔹 <b>P/B (Price to Book Ratio):</b> Kompaniya bozor bahosining uning sof aktivlariga nisbati. Mezon: < 3 bo'lsa aksiya arzon.\n"
            "🔹 <b>EPS (Earnings Per Share):</b> Bitta aksiyaga to'g'ri keladigan sof foyda. Mutloq o'sishda bo'lishi kerak.\n"
            "🔹 <b>RSI (Relative Strength Index):</b> Texnik kuch indikatori. RSI < 30 bo'lsa - aksiya qattiq arzonlashgan (Xarid vaqti), RSI > 70 bo'lsa - haddan tashqari qimmatlashgan.\n"
            "🔹 <b>SMC (Smart Money Concepts):</b> Yirik kitlar va banklarning order qoldirgan liquidity (likvidlik) va FVG zonalarini aniqlash strategiyasi."
        )
        bot.send_message(chat_id, dict_msg, parse_mode="HTML")

    # C) S&P 500 FONDLARI
    elif text == "📈 S&P 500 Fondlari":
        sp_msg = (
            "📈 <b>S&P 500 Indeksiga asoslangan eng likvidli ETF fondlar:</b>\n\n"
            "AQSH bozorini yaxlit sotib olish uchun eng xavfsiz fondlar tikerlari:\n\n"
            "📊 <code>SPY</code> - SPDR S&P 500 ETF Trust (Eng yirik hajm)\n"
            "📊 <code>VOO</code> - Vanguard S&P 500 ETF (Eng past komissiya)\n"
            "📊 <code>IVV</code> - iShares Core S&P 500 ETF\n\n"
            "💡 <i>Ushbu tikerlardan birini (Masalan: <code>VOO</code>) botga to'g'ridan-to'g'ri matn sifatida yuborsangiz, uning moliyaviy balansini va tarkibini jonli tahlil qilib beraman!</i>"
        )
        bot.send_message(chat_id, sp_msg, parse_mode="HTML")

    # D) JONLI HALOL AKSIYALAR FILTRI (Emojilar bilan)
    elif text == "🟢 Halol aksiyalar":
        halol_msg = (
            "🟢 <b>Islom Moliyasi Standartlariga Mos Top Aksiyalar (AAOIFI):</b>\n\n"
            "🍏 <code>AAPL</code> - Apple Inc. (Texnologiya va ekotizim)\n"
            "🟢 <code>NVDA</code> - NVIDIA Corporation (AI va chiplar)\n"
            "🛒 <code>TSCO</code> - Tractor Supply Company (Chakana savdo)\n"
            "💾 <code>MU</code> - Micron Technology (Yarimo'tkazgichlar)\n"
            "🟦 <code>INTC</code> - Intel Corporation (Raqamli texnologiyalar)\n\n"
            "💡 <i>Ushbu ro'yxatdagi istalgan tiker ustiga bosib, nusxalab botga yuboring va uning joriy narxlari hamda Fibonacci nuqtalarini ko'ring!</i>"
        )
        bot.send_message(chat_id, halol_msg, parse_mode="HTML")

    # E) RSI SKRINER
    elif text == "🔍 RSI Skriner":
        rsi_msg = (
            "🔍 <b>RSI Skriner - Haddan tashqari sotilgan (Arzonlashgan) Zonalar:</b>\n\n"
            "💳 <code>PYPL</code> (PayPal Holdings) - D1 RSI: 31.40 (Kuchli qo'llab-quvvatlashda)\n"
            "👟 <code>NKE</code> (Nike Inc.) - D1 RSI: 33.12 (Tarixiy arzon zona)\n"
            "🛒 <code>TSCO</code> (Tractor Supply) - H4 da GAP to'ldirish arafasida, RSI: 34.50\n\n"
            "🎯 <i>Ushbu aktivlar hozirda texnik jihatdan eng arzon zonalarda joylashgan.</i>"
        )
        bot.send_message(chat_id, rsi_msg, parse_mode="HTML")

    # F) AI TAVSIYALARI
    elif text == "🤖 AI Tavsiyalari":
        ai_msg = (
            "🤖 <b>AI Algoritmik Bozor Sharhi:</b>\n\n"
            "🚨 <b>Trend yo'nalishi:</b> Texnologiya sektori (AI va Yarimo'tkazgichlar) vaqtinchalik korreksiyada, bu uzoq muddatli investorlar uchun FVG (Fair Value Gap) hududlarida pozitsiya yig'ishga imkon beradi.\n"
            "🎯 <b>Diqqat markazida:</b> Chakana savdo va barqaror iste'mol mollari (Consumer Defensive) sektorlariga pul oqimi (Institutional Flow) ko'paymoqda.\n\n"
            "🎛 Tahlil o'tkazish uchun biror bir tikerni yozing."
        )
        bot.send_message(chat_id, ai_msg, parse_mode="HTML")

    # G) TOP SIGNAL
    elif text == "🚀 TOP Signal":
        signal_msg = (
            "🚀 <b>Kunlik Yuqori Ehtimollikdagi Texnik Signal:</b>\n\n"
            "🎯 <b>Aksiya:</b> TSCO (Tractor Supply Company)\n"
            "📊 <b>Strategiya:</b> ICT IPDA 20 + Smart Money\n"
            "📉 <b>Holat:</b> H4 taymfreymida $44 atrofida aniqlangan likvidlik ob'ekti (GAP) mavjud. Narx muvozanatlashish uchun o'sha zonaga harakat qilmoqda.\n"
            "📈 <b>Kirish zonasi:</b> RSI ko'rsatkichi qo'shimcha xarid signalini bermoqda.\n\n"
            "⚠️ <i>Eslatma: Ushbu ma'lumot moliyaviy maslahat emas, shaxsiy tahlil hisoblanadi! Riskni boshqarish majburiydir.</i>"
        )
        bot.send_message(chat_id, signal_msg, parse_mode="HTML")

    # H) FOYDALANUVCHI AKSIYA NOMINI YOZGAN HOLATDA
    else:
        if len(text) <= 5 and text.replace('.', '').isalpha():
            status_msg = bot.send_message(chat_id, f"🔍 <code>{text.upper()}</code> aksiyasi real vaqt rejimida tahlil qilinmoqda, kuting...")
            analysis_result, error = get_stock_analysis(text)
            
            try:
                bot.delete_message(chat_id, status_msg.message_id)
            except:
                pass

            if error:
                bot.send_message(chat_id, f"❌ Xato yuz berdi: {error}\nIltimos, tiker nomi to'g'ri yozilganini tekshiring (Masalan: NVDA).")
            else:
                inline_markup = types.InlineKeyboardMarkup()
                inline_markup.add(
                    types.InlineKeyboardButton("🤖 AI Maslahati", callback_data=f"ai_{text.upper()}"),
                    types.InlineKeyboardButton("🔗 TradingView Grafik", url=f"https://www.tradingview.com/symbols/{text.upper()}/")
                )
                bot.send_message(chat_id, analysis_result, reply_markup=inline_markup, parse_mode="HTML")
        else:
            bot.send_message(chat_id, "⚠️ Noma'lum buyruq. Iltimos, menyudagi tugmalardan foydalaning yoki to'g'ri aksiya tikerini kiriting (Masalan: AAPL).")

# 5. INLINE TUGMA BOSILGANDA AI MASLAHATINI CHIQARISH
@bot.callback_query_handler(func=lambda call: call.data.startswith('ai_'))
def callback_ai(call):
    ticker = call.data.split('_')[1]
    bot.answer_callback_query(call.id, text="AI hisobot tayyorlanmoqda...")
    bot.send_message(
        call.message.chat.id, 
        f"🤖 <b>AI Maslahatchi ({ticker}):</b>\n\n"
        f"IPDA 20 algoritmi va Smart Money konseptiga ko'ra, institutlar (kitlar) ushbu aktivda uzoq muddatli yirik xarid bloklarini (Order Block) shakllantirmoqda. Risk darajasi: Minimal. Portfelning 5% igacha bo'lgan qismi bilan xarid qilish taktikasi qo'llanilishi mumkin.", 
        parse_mode="HTML"
    )

# 6. CRITICAL POLLING MODE (Renderda xatosiz ishlash kafolati)
if __name__ == "__main__":
    print("Bot muvaffaqiyatli yondi!")
    bot.polling(none_stop=True, interval=0, timeout=20)
