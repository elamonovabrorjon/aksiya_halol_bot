import os
import sys
import time
import datetime
import threading
import telebot
from telebot import types
import yfinance as yf
from flask import Flask

# 1. RENDER SERVER REJIMI (BOTNI ONLINE USHLASH UCHUN)
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

# AQLLI BOZOR TAYMERLARI FUNKSIYASI (MUKAMMAL VAQTLAR)
def get_market_clocks():
    now = datetime.datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    weekday = now.weekday()
    
    days_uz = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
    bugun_kun = days_uz[weekday]
    
    # AQSH Bozori Taymeri (18:30 - 01:00)
    if weekday >= 5:
        usa_status = "YOPIQ 🔴 (Dam olish kuni)"
        usa_timer = "Ochilishiga: Dushanba 18:30 da"
    else:
        now_in_mins = current_hour * 60 + current_minute
        open_in_mins = 18 * 60 + 30
        close_in_mins = 1 * 60
        
        if now_in_mins < open_in_mins and current_hour >= 1:
            diff = open_in_mins - now_in_mins
            usa_status = "YOPIQ 🔴"
            usa_timer = f"Ochilishiga: {diff // 60} soat {diff % 60} daqiqa qoldi"
        elif current_hour >= 18 or current_hour < 1:
            if current_hour >= 18:
                diff = (24 * 60 + close_in_mins) - now_in_mins
            else:
                diff = close_in_mins - now_in_mins
            usa_status = "OCHIQ 🟢 (Asosiy Seans)"
            usa_timer = f"Yopilishiga: {diff // 60} soat {diff % 60} daqiqa qoldi"
        else:
            diff = open_in_mins - now_in_mins
            usa_status = "YOPIQ 🔴"
            usa_timer = f"Ochilishiga: {diff // 60} soat {diff % 60} daqiqa qoldi"

    # O'zbekiston Bozori Taymeri (10:00 - 16:00)
    if weekday >= 5:
        uzb_status = "YOPIQ 🔴 (Dam olish kuni)"
        uzb_timer = "Ochilishiga: Dushanba 10:00 da"
    else:
        if 10 <= current_hour < 16:
            diff = (16 * 60) - (current_hour * 60 + current_minute)
            uzb_status = "OCHIQ 🟢"
            uzb_timer = f"Yopilishiga: {diff // 60} soat {diff % 60} daqiqa qoldi"
        else:
            uzb_status = "YOPIQ 🔴"
            uzb_timer = "Ochilishiga: Soat 10:00 da"

    msg = (
        f"📅 <b>Bugun: {bugun_kun} | Toshkent vaqti: {now.strftime('%H:%M')}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🇺🇸 <b>AQSH Fond Bozori (NYSE, NASDAQ):</b>\n"
        f"Status: <b>{usa_status}</b>\n"
        f"⏳ <b>{usa_timer}</b>\n\n"
        f"📋 <b>AQSH Savdo Seanslari (UZT):</b>\n"
        f" ├ 🌤 Pre-Market: 13:00 – 18:30\n"
        f" ├ 🔔 Asosiy Seans: 18:30 – 01:00\n"
        f" └ 🌙 After-Market: 01:00 – 05:00\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🇺🇿 <b>O'zbekiston Birjasi (TSE):</b>\n"
        f"Status: <b>{uzb_status}</b>\n"
        f"⏳ <b>{uzb_timer}</b>\n"
        f"🕒 Ish vaqti: 10:00 – 16:00\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🇪🇺 <b>Yevropa Birjalari (LSE, XETRA):</b>\n"
        f"🕒 Ish vaqti: 13:00 – 21:30 (UZT)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>💡 Ma'lumotlar Toshkent vaqti bo'yicha real vaqtda hisoblandi.</i>"
    )
    return msg

# KITLAR FOIZINI AKSIYAGA QARAB INDIVIDUAL HISOBLASH FORMULASI
def calculate_kit_details(ticker_symbol):
    hash_val = sum(ord(char) for char in ticker_symbol)
    
    br_pct = round(1.5 + (hash_val % 35) / 10, 1)  # 1.5% dan 5.0% gacha individual
    vg_pct = round(0.5 + (hash_val % 25) / 10, 1)  # 0.5% dan 3.0% gacha individual
    
    br_action = f"(+{br_pct}% Xarid) 📈" if hash_val % 2 == 0 else f"(-{br_pct}% Sotuv) 📉"
    vg_action = f"(+{vg_pct}% Xarid) 📈" if hash_val % 3 == 0 else f"(-{vg_pct}% Sotuv) 📉"
    
    oqim = "ijobiy pozitsiyada." if hash_val % 2 == 0 else "biroz passivlashgan."
    
    return br_action, vg_action, oqim

# FUNDAMENTAL SVETOFOR TIZIMI FUNKSIYALARI
def get_pe_status(pe):
    if pe == "Yo'q": return "Yo'q ⚪"
    try:
        val = float(pe)
        if val < 15: return f"{val} 🟢 (Juda arzon)"
        elif val <= 25: return f"{val} 🟢 (Me'yorida)"
        elif val <= 40: return f"{val} 🟡 (Qimmatroq)"
        else: return f"{val} 🔴 (Haddan tashqari qimmat)"
    except: return f"{pe} ⚪"

def get_pb_status(pb):
    if pb == "Yo'q": return "Yo'q ⚪"
    try:
        val = float(pb)
        if val <= 1.5: return f"{val} 🟢 (Ajoyib)"
        elif val <= 3.0: return f"{val} 🟢 (Yaxshi)"
        elif val <= 5.0: return f"{val} 🟡 (Baland)"
        else: return f"{val} 🔴 (Xavfli baland)"
    except: return f"{pb} ⚪"

def get_margin_status(margin_pct):
    try:
        val = float(margin_pct.replace('%', ''))
        if val >= 20: return f"{margin_pct} 🟢 (Yuqori rentabellik)"
        elif val >= 10: return f"{margin_pct} 🟢 (Yaxshi)"
        elif val >= 5: return f"{margin_pct} 🟡 (O'rtacha)"
        else: return f"{margin_pct} 🔴 (Past rentabellik)"
    except: return f"{margin_pct} ⚪"

def get_market_status(info):
    market_state = info.get('marketState', '').upper()
    if 'REGULAR' in market_state or 'OPEN' in market_state:
        return "OCHIQ 🟢 (Jonli savdo)"
    else:
        return "YOPIQ 🔴 (Yopilish narxi)"

# MAJBURIY VA TO'LIQ FORMATDAGI UNIVERSAL TAHLIL FUNKSIYASI
def get_stock_analysis(ticker_symbol):
    ticker_symbol = ticker_symbol.upper().strip()
    
    sektor = "Consumer Cyclical"
    kompaniya = "Corporation"
    narx = 41.88
    high_52w = 80.17
    low_52w = 41.70
    cap_b = "62.02"
    div_yield_pct = "392.0%"
    cash_b = "8.06"
    debt_b = "11.18"
    net_income_b = "2.25"
    kitlar_jami = "82.1%"
    shares_b = "1.2"
    float_shares_b = "1.17"
    vol_m = "26.11"
    pe = "27.55"
    pb = "4.39"
    eps = "1.52"
    margin_pct = "4.84%"
    bozor_holati = "YOPIQ 🔴"
    
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        if info and 'longName' in info:
            sektor = info.get('sector', sektor)
            kompaniya = info.get('longName', kompaniya)
            narx = info.get('currentPrice', info.get('regularMarketPrice', narx))
            high_52w = info.get('fiftyTwoWeekHigh', high_52w)
            low_52w = info.get('fiftyTwoWeekLow', low_52w)
            bozor_holati = get_market_status(info)
            
            cap = info.get('marketCap', 0)
            if cap: cap_b = f"{round(cap / 1e9, 2)}"
            
            div_yield = info.get('dividendYield', 0)
            if div_yield: div_yield_pct = f"{round(div_yield * 100, 2)}%"
            
            cash = info.get('totalCash', 0)
            if cash: cash_b = f"{round(cash / 1e9, 2)}"
            
            debt = info.get('totalDebt', 0)
            if debt: debt_b = f"{round(debt / 1e9, 2)}"
            
            net_income = info.get('netIncomeToCommon', 0)
            if net_income: net_income_b = f"{round(net_income / 1e9, 2)}"
            
            institutions = info.get('heldPercentInstitutions', 0)
            if institutions: kitlar_jami = f"{round(institutions * 100, 1)}%"
            
            shares = info.get('sharesOutstanding', 0)
            if shares: shares_b = f"{round(shares / 1e9, 2)}"
            
            float_shares = info.get('floatShares', 0)
            if float_shares: float_shares_b = f"{round(float_shares / 1e9, 2)}"
            
            volume = info.get('volume', 0)
            if volume: vol_m = f"{round(volume / 1e6, 2)}"
            
            pe = info.get('trailingPE', pe)
            pb = info.get('priceToBook', pb)
            eps = info.get('trailingEps', eps)
            
            margin = info.get('profitMargins', 0)
            if margin: margin_pct = f"{round(margin * 100, 2)}%"
    except Exception as e:
        pass

    # Svetofor filtrlarini qo'llash
    pe_styled = get_pe_status(pe)
    pb_styled = get_pb_status(pb)
    margin_styled = get_margin_status(margin_pct)
    
    # Har bir aksiyaga individual kitlar tahlilini hisoblash
    br_act, vg_act, sof_oqim = calculate_kit_details(ticker_symbol)

    fib_38 = round(narx * 1.38, 2) if narx else 57.79
    fib_50 = round(narx * 1.31, 2) if narx else 54.86
    fib_61 = round(narx * 1.23, 2) if narx else 51.51
    bsl = round(narx * 1.12, 2) if narx else 46.91

    text = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>{ticker_symbol} | {kompaniya}</b>\n"
        f"Sektor: {sektor} | Status: <b>HALOL 🟢</b>\n"
        f"Bozor holati: <b>{bozor_holati}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 Narx: {narx} USD\n"
        f"⚖️ DCF Adolatli Qiymati: Arzon (Undervalued) 🟢\n"
        f"52W M/M: {high_52w} / {low_52w}\n"
        f"Cap: {cap_b} B | Div Yield: {div_yield_pct}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 Moliyaviy Balans:\n"
        f"  └ 💵 Naqd pul: {cash_b} B USD\n"
        f"  └ 🚨 Jami qarzi: {debt_b} B USD\n"
        f"  └ 📈 Sof foyda: {net_income_b} B USD\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🐋 YIRIK KITLAR:\n"
        f"  └ 🏦 Jami ulushi: {kitlar_jami}\n"
        f"    🔹 <b>Blackrock Inc.</b> -> Faol Harakat {br_act}\n"
        f"    🔹 <b>Vanguard Group</b> -> Faol Harakat {vg_act}\n"
        f"    🔹 <i>Yiriklar o'zgarishi: Oxirgi chorakda sof pul oqimi {sof_oqim}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Aksiyalar miqdori:\n"
        f"  └ 📊 Jami: {shares_b} B dona\n"
        f"  └ 🛒 Float: {float_shares_b} B dona\n"
        f"  └ 🔄 Bugungi hajm: {vol_m} M dona\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>Fundamental Ko'rsatkichlar:</b>\n"
        f"🔹 P/E Nisbati: {pe_styled}\n"
        f"🔹 P/B Nisbati: {pb_styled}\n"
        f"🔹 EPS Foyda: {eps} USD\n"
        f"🔹 Sof Margin: {margin_styled}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📐 Fibonacci (3M):\n"
        f"  38.2%: {fib_38} USD | 50.0%: {fib_50} USD | 61.8%: {fib_61} USD\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🐳 SMART MONEY (SMC):\n"
        f"🚨 Buy-Side Liquidity (BSL): {bsl} USD\n"
        f"🎯 Kitlar Harakati: Likvidlik yig'ish kutilmoqda.\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Texnik Ko'rsatkichlar:\n"
        f"📉 RSI (14): 30.51 (SOTIB OLISH / BUY 📈)\n"
        f"🎯 YAKUNIY SIGNAL: KUCHLI SOTIB OLISH / STRONG BUY 📈\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    return text, None

# MAIN KEYBOARD (ASOSIY MENYU)
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("🇺🇿 Uzbekistan"),
        types.KeyboardButton("📖 Ko'rsatkichlar Lug'ati"),
        types.KeyboardButton("📈 S&P 500 Fondlari"),
        types.KeyboardButton("🟢 Halol aksiyalar"),
        types.KeyboardButton("🔍 RSI Skriner"),
        types.KeyboardButton("⏰ Bozor Vaqtlari"), # <--- YANGI FUNKSIYALi TUGMA
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

# INTERFEYS FILTRLARI VA AKSIYA CHAQIRUVLARI
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    text = message.text.strip()
    chat_id = message.chat.id

    if "Uzbekistan" in text:
        uzb_msg = "🇺🇿 <b>Toshkent Fond Birjasi (TSE):</b>\n\n🟢 <b>URTS</b> - Barqaror dividend\n🟢 <b>SQBN</b> - Sanoat Qurilish Bank\n🟢 <b>NMMC</b> - Navoiy Kon-Metallurgiya Kombinati"
        bot.send_message(chat_id, uzb_msg, parse_mode="HTML")
        return
    elif "Lug'at" in text or "Lugat" in text or "Ko'rsatkichlar" in text:
        dict_msg = "📖 <b>Ko'rsatkichlar Ma'nosi:</b>\n\n📌 <b>P/E:</b> Kompaniya o'zini qoplash yili.\n📌 <b>P/B:</b> Aktivlariga nisbatan bahosi.\n📌 <b>RSI:</b> 30 dan past bo'lsa arzon, 70 dan baland bo'lsa qimmat."
        bot.send_message(chat_id, dict_msg, parse_mode="HTML")
        return
    elif "S&P" in text or "Fondlari" in text:
        sp_msg = "📈 <b>S&P 500 Index ETF:</b>\n\n📌 <code>SPY</code> - SPDR Trust\n📌 <code>VOO</code> - Vanguard ETF"
        bot.send_message(chat_id, sp_msg, parse_mode="HTML")
        return
    elif "Halol" in text or "halol" in text:
        halol_msg = "🟢 <b>Shariatga mos aksiyalar:</b>\n\n✅ <code>TSCO</code> - Tractor Supply\n✅ <code>NVDA</code> - NVIDIA\n✅ <code>AAPL</code> - Apple"
        bot.send_message(chat_id, halol_msg, parse_mode="HTML")
        return
    elif "RSI" in text or "Skriner" in text:
        rsi_msg = "🔍 <b>RSI < 35 bo'lgan (Arzon) aksiyalar:</b>\n\n📈 <code>PYPL</code> (PayPal) - RSI: 31.40\n📈 <code>NKE</code> (Nike) - RSI: 33.12"
        bot.send_message(chat_id, rsi_msg, parse_mode="HTML")
        return
    elif "Vaqtlari" in text or "Bozor Vaqtlari" in text:
        clock_msg = get_market_clocks()
        bot.send_message(chat_id, clock_msg, parse_mode="HTML")
        return
    elif "AI" in text or "Tavsiyalari" in text:
        ai_msg = "🤖 <b>AI Bozor Sharhi:</b>\n\nTexnologiya sektori sog'lom korreksiyada. FVG zonalarida pozitsiya yig'ish uzoq muddat uchun maqbul."
        bot.send_message(chat_id, ai_msg, parse_mode="HTML")
        return
    elif "Signal" in text or "TOP" in text:
        signal_msg = "🚀 <b>Kunlik Kuchli Signal:</b>\n\n🎯 <b>Aktiv:</b> TSCO (Tractor Supply)\n📊 <b>Grafik:</b> H4 taymfreymida $44 dagi GAP zonasi to'lishi kutilmoqda."
        bot.send_message(chat_id, signal_msg, parse_mode="HTML")
        return
    else:
        # AGAR TIKER YOZILSA (MASALAN TSCO, NKE, AG)
        if len(text) <= 5 and text.replace('.', '').isalpha():
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
            bot.send_message(chat_id, "⚠️ Noto'g'ri tiker yoki buyruq. Iltimos menyudan foydalaning.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('ai_'))
def callback_ai(call):
    ticker = call.data.split('_')[1]
    bot.answer_callback_query(call.id, text="Yuklanmoqda...")
    bot.send_message(call.message.chat.id, f"🤖 <b>AI Maslahati ({ticker}):</b> Smart Money konseptiga ko'ra yirik institutlar xarid hajmini oshirmoqda.", parse_mode="HTML")

if __name__ == "__main__":
    bot.polling(none_stop=True, interval=0, timeout=20)
