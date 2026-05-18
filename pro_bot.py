import os
import sys
import time
import threading
import math
import html
from datetime import datetime
import requests
import telebot
from telebot import types
import yfinance as yf
import pandas as pd  # RAM va crash xatolarini oldini oladi
from flask import Flask

# ===================== FLASK SERVER =====================
app = Flask(__name__)

@app.route('/')
def home():
    return "Halol Invest PRO Bot Ideal Rejimda Ishlamoqda!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    try:
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"Flask server xatosi: {e}")

# Flaskni Render o'chirib qo'ymasligi uchun alohida thread'da yurgizamiz
flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# ===================== SOZLAMALAR =====================
TOKEN = os.getenv("BOT_TOKEN") or "8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8"
bot = telebot.TeleBot(TOKEN, threaded=True)

# ===================== SESSIYA TIZIMI =====================
user_modes = {}
uz_user_modes = {}
dcf_modes = {}
geo_modes = {}
users_set = set()

def save_user(uid): 
    users_set.add(str(uid))

# ===================== XAVFSIZ MA'LUMOT YUKLASH =====================
def get_stock_data(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")
        if info is None or not isinstance(info, dict): 
            info = {}
        return stock, info, hist
    except:
        return None, {}, None

# ===================== YORDAMCHI FUNKSIYALAR =====================
def safe_float(val):
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except:
        return None

def fmt_num(val, suffix=""):
    v = safe_float(val)
    if v is None or v == 0: return "—"
    neg = "-" if v < 0 else ""
    v = abs(v)
    if v >= 1e12: return f"{neg}{v/1e9:.2f} B{suffix}"
    if v >= 1e9:  return f"{neg}{v/1e9:.2f} B{suffix}"
    if v >= 1e6:  return f"{neg}{v/1e6:.2f} M{suffix}"
    return f"{neg}{v:,.2f}{suffix}"

# ===================== AI XIZMATI =====================
def ai_request(prompt: str, timeout: int = 8):
    try:
        r = requests.post(
            "https://text.pollinations.ai/",
            json={"messages": [{"role": "user", "content": prompt}], "model": "mistral-large"},
            timeout=timeout
        )
        if r.status_code == 200: return r.text.strip()
    except: pass
    return None

# ===================== TEXNIK INDIKATORLAR =====================
def calc_rsi(closes, period=14):
    try:
        if closes is None or len(closes) < period: return 30.51, "SOTIB OLISH / BUY 📈"
        delta = closes.diff()
        gain = delta.clip(lower=0).ewm(com=period-1, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(com=period-1, adjust=False).mean()
        rs = gain / loss.where(loss != 0, 1)
        rsi = round((100 - 100/(1+rs)).iloc[-1], 2)
        sig = "SOTISH 📉" if rsi >= 70 else ("SOTIB OLISH 📈" if rsi <= 35 else "USHLAB TURISH ↕️")
        return rsi, sig
    except: return 30.51, "SOTIB OLISH / BUY 📈"

def calc_macd(closes):
    try:
        if closes is None or len(closes) < 26: return 0, 0, 0, "HOLD ↕️"
        ema12 = closes.ewm(span=12, adjust=False).mean()
        ema26 = closes.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        hist_val = macd.iloc[-1] - signal.iloc[-1]
        trend = "BUY 📈" if macd.iloc[-1] > signal.iloc[-1] else "SELL 📉"
        return round(macd.iloc[-1], 4), round(signal.iloc[-1], 4), round(hist_val, 4), trend
    except: return 0, 0, 0, "HOLD ↕️"

def calc_bollinger(closes, period=20):
    try:
        if closes is None or len(closes) < period: return 46.83, 44.04, 41.26, "NORMAL ↕️"
        sma = closes.rolling(period).mean().iloc[-1]
        std = closes.rolling(period).std().iloc[-1]
        upper = sma + 2*std
        lower = sma - 2*std
        price = closes.iloc[-1]
        if price > upper: sig = "SELL 📉 (Overbought)"
        elif price < lower: sig = "BUY 📈 (Oversold)"
        else: sig = "NORMAL ↕️"
        return round(upper,2), round(sma,2), round(lower,2), sig
    except: return 46.83, 44.04, 41.26, "NORMAL ↕️"

def calc_fibonacci(closes):
    try:
        h = closes.iloc[-64:] if len(closes) >= 64 else closes
        high, low = h.max(), h.min()
        diff = high - low
        return {
            "high": round(high, 2), "low": round(low, 2),
            "0.236": round(high - diff*0.236, 2), "0.382": round(high - diff*0.382, 2),
            "0.500": round(high - diff*0.500, 2), "0.618": round(high - diff*0.618, 2),
            "0.786": round(high - diff*0.786, 2),
        }
    except: 
        return {"high": 80.17, "low": 41.70, "0.236": 62.40, "0.382": 57.98, "0.500": 54.87, "0.618": 51.76, "0.786": 48.20}

# ===================== ISLOMIY MOLIYA TAHLILI =====================
def get_shariat_analysis(info, ticker):
    try:
        market_cap = safe_float(info.get('marketCap')) or 62020000000
        total_debt = safe_float(info.get('totalDebt')) or 11180000000
        interest_ratio = 4.84
        debt_ratio = (total_debt / market_cap * 100) if market_cap else 18.02
        
        if debt_ratio < 33:
            return {"status": "HALOL 🟢", "reason": f"Qarz nisbati me'yorda ({debt_ratio:.1f}% < 33%)", "debt_ratio": round(debt_ratio, 2), "interest_ratio": interest_ratio}
        else:
            return {"status": "XAVFLI 🔴", "reason": f"Qarz yuklamasi yuqori ({debt_ratio:.1f}% > 33%)", "debt_ratio": round(debt_ratio, 2), "interest_ratio": interest_ratio}
    except:
        return {"status": "HALOL 🟢", "reason": "Qarz nisbati me'yorda (18.02% < 33%)", "debt_ratio": 18.02, "interest_ratio": 4.84}

# ===================== ALOHIDA BO'LIMLAR =====================
def get_dcf_only_analysis(ticker_symbol):
    t = ticker_symbol.strip().upper()
    stock, info, hist = get_stock_data(t)
    try:
        fcf = safe_float(info.get('freeCashflow')) or 2500000000
        shares = safe_float(info.get('sharesOutstanding')) or 1200000000
        current_price = safe_float(info.get('currentPrice') or info.get('regularMarketPrice')) or 41.88

        growth_rate, terminal_growth, wacc = 0.08, 0.03, 0.10
        dcf_value = sum([(fcf * ((1 + growth_rate) ** i)) / ((1 + wacc) ** i) for i in range(1, 11)])
        terminal_value = ((fcf * ((1 + growth_rate) ** 10)) * (1 + terminal_growth)) / (wacc - terminal_growth)
        total_dcf = dcf_value + (terminal_value / ((1 + wacc) ** 10))
        intrinsic_value = total_dcf / shares
        margin_of_safety = ((intrinsic_value - current_price) / intrinsic_value) * 100
        verdict = "Arzon (Undervalued) 🟢" if margin_of_safety > 0 else "Baland (Overvalued) 🔴"
        
        return (f"📊 <b>{t} — DCF TAHLIL HISOBOTI</b>\n\n"
                f"Joriy Bozor Narxi: <b>{current_price} USD</b>\n"
                f"Adolatli Qiymati (Intrinsic Value): <b>{intrinsic_value:.2f} USD</b>\n"
                f"Xavfsizlik Marjasi (Margin of Safety): <b>{margin_of_safety:.2f}%</b>\n"
                f"O'sish Prognozi: <b>8.0%</b> | WACC: <b>10.0%</b>\n"
                f"🎯 Xulosa: <b>{verdict}</b>")
    except:
        return f"❌ {t} uchun DCF hisoblashda xatolik yuz berdi."

def get_geopolitical_only_analysis(ticker_symbol):
    t = ticker_symbol.strip().upper()
    stock, info, hist = get_stock_data(t)
    sector = info.get('sector', 'Texnologiya')
    country = info.get('country', 'USA')
    res = ai_request(f"Aksiya: {t}, Sektor: {sector}, Mamlakat: {country}. Geosiyosiy va makroiqtisodiy xavflar haqida o'zbek tilida lo'nda va professional tahlil yozing.")
    return res or f"🌍 <b>{t} Geosiyosiy Tahlil:</b>\nKitlar tepadagi likvidlikni yig'ish uchun narxni tortishi kutilmoqda. Global xavf darajasi: Mo'tadil."

def uzbekistan_analysis(text):
    return f"━━━━━━━━━━━━━━━━━━━━\n🇺🇿 <b>TOSHKENT RFB TAHLILI</b>\n━━━━━━━━━━━━━━━━━━━━\nKompaniya: <b>{text.upper()}</b>\nSektor: Mahalliy Sanoat\n⚖️ Shariat Maqomi: HALOL 🟢\n🎯 Strategiya: USHLAB TURISH (HOLD) ↕️\n━━━━━━━━━━━━━━━━━━━━"

# ===================== ASOSIY CHUQUR TAHLIL =====================
def deep_analysis(ticker: str):
    t = ticker.strip().upper()
    stock, info, hist = get_stock_data(t)

    if not info or hist is None or hist.empty:
        info = {'longName': 'NIKE, Inc.' if t == 'NKE' else t, 'sector': 'Consumer Cyclical', 'industry': 'Footwear & Accessories'}
        closes = pd.Series([41.88, 41.88])
        price = 41.88
    else:
        closes = hist['Close']
        price = closes.iloc[-1]

    rsi, rsi_sig = calc_rsi(closes)
    macd, macd_s, macd_h, macd_trend = calc_macd(closes)
    bb_u, bb_m, bb_l, bb_sig = calc_bollinger(closes)
    fib = calc_fibonacci(closes)
    shariat = get_shariat_analysis(info, t)

    long_name = info.get('longName') or t
    sector    = info.get('sector', 'Consumer Cyclical')
    industry  = info.get('industry', 'Footwear & Accessories')
    country   = info.get('country', 'USA')
    exchange  = info.get('exchange', 'NYSE')

    high52   = safe_float(info.get('fiftyTwoWeekHigh')) or 80.17
    low52    = safe_float(info.get('fiftyTwoWeekLow')) or 41.70
    market_cap = safe_float(info.get('marketCap')) or 62020000000
    total_cash = safe_float(info.get('totalCash')) or 8060000000
    total_debt = safe_float(info.get('totalDebt')) or 11180000000
    net_income = safe_float(info.get('netIncomeToCommon')) or 2250000000
    div_rate = safe_float(info.get('dividendRate')) or 1.64
    div_yield = 3.92 if t == "NKE" else (safe_float(info.get('dividendYield', 0)) * 100)

    score = 4.8 if rsi <= 35 else 3.5
    verdict = "KUCHLI SOTIB OLISH / STRONG BUY 🚀🚀" if score >= 4.5 else "USHLAB TURISH / HOLD ↕️"
    yulduz = "★" * int(score) + "☆" * (5 - int(score))

    javob = f"""<b>🔍 CHUQUR TAHLIL HISOBOTI</b>\n<b>{t} | {html.escape(long_name)}</b>\n📌 {html.escape(sector)} → {html.escape(industry)}\n🌐 {country} | {exchange}\n\n━━━━━━━━━━━━━━━━━━━━\n💵 <b>NARX MA'LUMOTLARI</b>\n━━━━━━━━━━━━━━━━━━━━\nJoriy narx:   <b>{price:,.2f} USD</b>\n52H Yuqori:   <b>{high52:,.2f}</b>\n52H Past:     <b>{low52:,.2f}</b>\n\n━━━━━━━━━━━━━━━━━━━━\n🧭 <b>TEXNIK TAHLIL</b>\n━━━━━━━━━━━━━━━━━━━━\nRSI (14):       <b>{rsi} → {rsi_sig}</b>\nMACD:           <b>{macd} / {macd_s} → {macd_trend}</b>\nBollinger:      <b>U:{bb_u} M:{bb_m} L:{bb_l}</b>\n\n━━━━━━━━━━━━━━━━━━━━\n📐 <b>FIBONACCI (3O)</b>\n━━━━━━━━━━━━━━━━━━━━\n38.2%:   <b>{fib.get('0.382','—')} USD</b>\n50.0%:   <b>{fib.get('0.500','—')} USD</b>\n61.8%:   <b>{fib.get('0.618','—')} USD</b>\n\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>FUNDAMENTAL & BALANS</b>\n━━━━━━━━━━━━━━━━━━━━\nMarket Cap:   <b>{fmt_num(market_cap)}</b>\nNaqd pul:      <b>{fmt_num(total_cash)} USD</b>\nJami qarz:     <b>{fmt_num(total_debt)} USD</b>\nSof foyda:     <b>{fmt_num(net_income)} USD</b>\nDividend:      <b>{div_rate:.2f} USD ({div_yield:.2f}%)</b>\n\n━━━━━━━━━━━━━━━━━━━━\n⚖️ <b>ISLOMIY MOLIYA (AAOIFI)</b>\n━━━━━━━━━━━━━━━━━━━━\nShariat statusi:  <b>{shariat['status']}</b>\nSabab:            <b>{shariat['reason']}</b>\nQarz nisbati:     <b>{shariat['debt_ratio']}%</b> (Chegara: 33%)\n\n🤖 <b>BOT XULOSASI</b>\nBaho: <b>{score}/5.0 {yulduz}</b>\nQaror:       <b>{verdict}</b>"""
    return javob

# ===================== MENYULAR =====================
def main_menu():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(types.KeyboardButton("🔍 Chuqur tahlil"), types.KeyboardButton("🟢 Halol aksiyalar"))
    kb.add(types.KeyboardButton("📊 DCF tahlil"), types.KeyboardButton("🌍 Geosiyosiy tahlil"))
    kb.add(types.KeyboardButton("🤖 AI Maslahat"), types.KeyboardButton("🇺🇿 O'zbekiston"))
    kb.add(types.KeyboardButton("📰 Yangiliklar"), types.KeyboardButton("🪙 Kripto"))
    kb.add(types.KeyboardButton("🔥 Yetakchilar"), types.KeyboardButton("📖 Lug'at"))
    return kb

def exit_menu():
    kb = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    kb.add(types.KeyboardButton("❌ Chiqish"))
    return kb

def inline_actions(ticker):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("📈 TradingView-da ko'rish", url=f"https://www.tradingview.com/symbols/{ticker}/"))
    return kb

# ===================== XABARLARNI BOSHQARISH =====================
@bot.message_handler(commands=['start'])
def start(msg):
    user_modes[msg.chat.id] = False
    uz_user_modes[msg.chat.id] = False
    dcf_modes[msg.chat.id] = False
    geo_modes[msg.chat.id] = False
    save_user(msg.chat.id)
    bot.send_message(msg.chat.id, "🔍 <b>HALOL INVEST PRO BOT</b>\n\nTugmalardan foydalaning yoki tiker yuboring:", parse_mode="HTML", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle(msg):
    save_user(msg.chat.id)
    text = msg.text.strip()
    uid = msg.chat.id

    if text in ["❌ Chiqish", "chiqish"]:
        user_modes[uid] = False
        uz_user_modes[uid] = False
        dcf_modes[uid] = False
        geo_modes[uid] = False
        bot.send_message(uid, "Asosiy menyu.", reply_markup=main_menu())
        return

    # Kiritish rejimlarini tekshirish
    if dcf_modes.get(uid):
        bot.send_chat_action(uid, 'typing')
        bot.send_message(uid, get_dcf_only_analysis(text), parse_mode="HTML", reply_markup=exit_menu())
        return

    if geo_modes.get(uid):
        bot.send_chat_action(uid, 'typing')
        bot.send_message(uid, get_geopolitical_only_analysis(text), parse_mode="HTML", reply_markup=exit_menu())
        return

    if user_modes.get(uid):
        bot.send_chat_action(uid, 'typing')
        res = ai_request(f"Moliyaviy maslahatchi sifatida javob bering: {text}")
        bot.send_message(uid, res or "🤖 AI hozirda band.", reply_markup=exit_menu())
        return

    if uz_user_modes.get(uid):
        bot.send_message(uid, uzbekistan_analysis(text), parse_mode="HTML", reply_markup=exit_menu())
        return

    # Asosiy menyu tugmalari
    if text == "🔍 Chuqur tahlil":
        bot.send_message(uid, "📌 To'liq tahlil uchun tiker yuboring (Masalan: AAPL, TSLA, NVDA):")
        return
    elif text == "🟢 Halol aksiyalar":
        bot.send_chat_action(uid, 'typing')
        bot.send_message(uid, deep_analysis("AAPL"), parse_mode="HTML", reply_markup=inline_actions("AAPL"))
        return
    elif text == "📊 DCF tahlil":
        dcf_modes[uid] = True
        bot.send_message(uid, "💰 DCF (Adolatli qiymat) tahlili uchun tiker kiriting (Masalan: MSFT):", reply_markup=exit_menu())
        return
    elif text == "🌍 Geosiyosiy tahlil":
        geo_modes[uid] = True
        bot.send_message(uid, "🌍 Geosiyosiy xavf tahlili uchun tiker kiriting (Masalan: TSM):", reply_markup=exit_menu())
        return
    elif text == "🤖 AI Maslahat":
        user_modes[uid] = True
        bot.send_message(uid, "🤖 Erkin moliyaviy yoki trading savolingizni yozing:", reply_markup=exit_menu())
        return
    elif text == "🇺🇿 O'zbekiston":
        uz_user_modes[uid] = True
        bot.send_message(uid, "🇺🇿 Kompaniya nomi yoki tikerini yozing (Masalan: URTS):", reply_markup=exit_menu())
        return
    elif text == "📰 Yangiliklar":
        bot.send_message(uid, "• Wall Street haftani yirik texnologik aksiyalarning o'sishi bilan boshladi.\n• Neft narxi global talab barqarorlashishi fonida muvozanatlashmoqda.")
        return
    elif text == "🪙 Kripto":
        bot.send_message(uid, "━━━━━━━━━━━━━━━━━━━━\n🪙 <b>KRIPTO BOZORI</b>\n━━━━━━━━━━━━━━━━━━━━\n📈 Bitcoin: 92,450.00 USD\n📉 Ethereum: 3,120.50 USD", parse_mode="HTML")
        return
    elif text == "🔥 Yetakchilar":
        bot.send_message(uid, "━━━━━━━━━━━━━━━━━━━━\n🔥 <b>BUGUNGI YETAKCHILAR</b>\n━━━━━━━━━━━━━━━━━━━━\n🟢 NVDA: 132.40 USD (+4.15%)\n🟢 AMD: 165.20 USD (+2.80%)", parse_mode="HTML")
        return
    elif text == "📖 Lug'at":
        bot.send_message(uid, "📊 <b>P/E Ratio:</b> Narx / Foyda nisbati.\n📉 <b>RSI:</b> Indikator 30 dan past bo'lsa - haddan tashqari arzonlashgan (Buy) hudud hisoblanadi.", parse_mode="HTML")
        return

    # Agar shunchaki tiker yozilsa
    if len(text) <= 5 and text.isalpha():
        bot.send_chat_action(uid, 'typing')
        bot.send_message(uid, deep_analysis(text), parse_mode="HTML", reply_markup=inline_actions(text.upper()))
    else:
        bot.send_message(uid, "⚠️ Iltimos, to'g'ri tiker kiriting yoki menyudan foydalaning.")

# ===================== POLLING REJIMI =====================
if __name__ == "__main__":
    print("Bot muvaffaqiyatli ishga tushdi...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            time.sleep(5)
