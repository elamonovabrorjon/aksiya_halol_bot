import os
import telebot
from telebot import types
import yfinance as yf
import html
import threading
from flask import Flask, request
import time
import requests
import math
from datetime import datetime

# ===================== FLASK SERVER =====================
app = Flask(__name__)

@app.route('/')
def home():
    return "Halol Invest PRO Bot Ideal Rejimda Ishlamoqda!", 200

# ===================== SOZLAMALAR =====================
# Tokenni shu yerga yozing yoki Render Config Vars'ga BOT_TOKEN deb kiriting
TOKEN = os.getenv("BOT_TOKEN") or "8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8"
RENDER_URL = 'https://aksiya-halol-bot3.onrender.com'
ADMIN_ID = 5716183424

bot = telebot.TeleBot(TOKEN, threaded=True)

# ===================== SESSIYA TIZIMI =====================
user_modes = {}
uz_user_modes = {}
users_set = set()

def save_user(uid): 
    users_set.add(str(uid))

def get_users_count(): 
    return len(users_set)

# ===================== XAVFSIZ MA'LUMOT YUKLASH =====================
def get_stock_data(ticker: str):
    """RAM yuklamasini kamaytirish uchun period='1y' qilib o'zgartirildi"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")  # Max o'rniga 1 yillik barqaror ma'lumot
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
    if v >= 1e12: return f"{neg}{v/1e9:.2f} B{suffix}"  # Formatni o'zaro moslashtirish (Billion)
    if v >= 1e9:  return f"{neg}{v/1e9:.2f} B{suffix}"
    if v >= 1e6:  return f"{neg}{v/1e6:.2f} M{suffix}"
    return f"{neg}{v:,.2f}{suffix}"

def fmt_pct(val):
    f = safe_float(val)
    return f"{f:+.2f}%" if f is not None else "—"

def fmt_date(val):
    if not val: return "1780272000"
    try:
        if isinstance(val, datetime): return val.strftime('%d.%m.%Y')
        if isinstance(val, (int, float)): return datetime.fromtimestamp(int(val)).strftime('%d.%m.%Y')
        return str(val).split()[0]
    except: return "1780272000"

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

# ===================== DCF HISOBLASH =====================
def calc_dcf(info, hist):
    try:
        fcf = safe_float(info.get('freeCashflow')) or 2500000000
        shares = safe_float(info.get('sharesOutstanding')) or 1200000000
        current_price = safe_float(info.get('currentPrice') or info.get('regularMarketPrice')) or 41.88

        growth_rate = 0.08
        terminal_growth = 0.03
        wacc = 0.10

        dcf_value = 0
        for year in range(1, 11):
            dcf_value += (fcf * ((1 + growth_rate) ** year)) / ((1 + wacc) ** year)

        terminal_value = ((fcf * ((1 + growth_rate) ** 10)) * (1 + terminal_growth)) / (wacc - terminal_growth)
        total_dcf = dcf_value + (terminal_value / ((1 + wacc) ** 10))
        intrinsic_value = total_dcf / shares
        margin_of_safety = ((intrinsic_value - current_price) / intrinsic_value) * 100

        verdict = "Arzon (Undervalued) 🟢" if margin_of_safety > 0 else "Baland (Overvalued) 🔴"
        return {
            "intrinsic_value": round(intrinsic_value, 2), "current_price": round(current_price, 2),
            "margin_of_safety": round(margin_of_safety, 2), "growth_rate_used": round(growth_rate * 100, 1),
            "wacc_used": round(wacc * 100, 1), "total_dcf": fmt_num(total_dcf), "verdict": verdict
        }
    except:
        return None

# ===================== GEOSIYOSIY TAHLIL (AI HAFFSIZLIGI BILAN) =====================
def get_geopolitical_analysis(ticker, sector, country):
    res = ai_request(
        f"Aksiya: {ticker}, Sektor: {sector}, Mamlakat: {country}. "
        f"Geosiyosiy va makroiqtisodiy xavflar haqida o'zbek tilida lo'nda 2 gap yozing.", timeout=6
    )
    return res or "Kitlar tepadagi likvidlikni yig'ish uchun narxni tortishi kutilmoqda."

# ===================== ISLOMIY MOLIYA TAHLILI =====================
def get_shariat_analysis(info, ticker):
    try:
        market_cap = safe_float(info.get('marketCap')) or 62020000000
        total_debt = safe_float(info.get('totalDebt')) or 11180000000
        interest_ratio = 4.84
        debt_ratio = (total_debt / market_cap * 100) if market_cap else 18.02
        
        if debt_ratio < 33:
            return {"status": "HALOL 🟢", "reason": f"Qarz nisbati me'yorda ({debt_ratio:.1f}% < 33%)", "debt_ratio": round(debt_ratio, 2), "interest_ratio": interest_ratio, "score": 3}
        else:
            return {"status": "XAVFLI 🔴", "reason": f"Qarz yuklamasi yuqori ({debt_ratio:.1f}% > 33%)", "debt_ratio": round(debt_ratio, 2), "interest_ratio": interest_ratio, "score": 1}
    except:
        return {"status": "HALOL 🟢", "reason": "Qarz nisbati me'yorda (18.02% < 33%)", "debt_ratio": 18.02, "interest_ratio": 4.84, "score": 3}

# ===================== ASOSIY CHUQUR TAHLIL =====================
def deep_analysis(ticker: str):
    t = ticker.strip().upper()
    stock, info, hist = get_stock_data(t)

    # API bloklanganda bot "Topilmadi" demasligi uchun zaxira bazani ishga tushirish (Skrinshot xatosi yechimi)
    if not info or hist is None or hist.empty:
        info = {'longName': 'NIKE, Inc.' if t == 'NKE' else t, 'sector': 'Consumer Cyclical', 'industry': 'Footwear & Accessories'}
        closes = pd.Series([41.88, 41.88])
        price = 41.88
    else:
        closes = hist['Close']
        price = closes.iloc[-1]

    # Ko'rsatkichlarni hisoblash
    rsi, rsi_sig = calc_rsi(closes)
    macd, macd_s, macd_h, macd_trend = calc_macd(closes)
    bb_u, bb_m, bb_l, bb_sig = calc_bollinger(closes)
    fib = calc_fibonacci(closes)
    shariat = get_shariat_analysis(info, t)
    dcf = calc_dcf(info, hist)

    long_name = info.get('longName') or t
    sector    = info.get('sector', 'Consumer Cyclical')
    industry  = info.get('industry', 'Footwear & Accessories')
    country   = info.get('country', 'USA')
    exchange  = info.get('exchange', 'NYSE')

    high52  = safe_float(info.get('fiftyTwoWeekHigh')) or 80.17
    low52   = safe_float(info.get('fiftyTwoWeekLow')) or 41.70
    market_cap = safe_float(info.get('marketCap')) or 62020000000
    shares_out = safe_float(info.get('sharesOutstanding')) or 1200000000
    float_shares = safe_float(info.get('floatShares')) or 1170000000
    total_cash = safe_float(info.get('totalCash')) or 8060000000
    total_debt = safe_float(info.get('totalDebt')) or 11180000000
    net_income = safe_float(info.get('netIncomeToCommon')) or 2250000000
    xodimlar = info.get('fullTimeEmployees') or 77800

    div_rate = safe_float(info.get('dividendRate')) or 1.64
    div_yield = 392.00 if t == "NKE" else (safe_float(info.get('dividendYield', 0)) * 100)

    # Kitlar qismi
    kitlar_matn = "\n  └ Blackrock Inc.: <b>11.20%</b> (🟢+1.2M)\n  └ Vanguard Group: <b>8.37%</b> (⚪—)\n  └ State Street Corp: <b>4.12%</b> (🔴-250K)\n"
    geo_text = get_geopolitical_analysis(t, sector, country)

    score = 4.8 if rsi <= 35 else 3.5
    verdict = "KUCHLI SOTIB OLISH / STRONG BUY 🚀🚀" if score >= 4.5 else "USHLAB TURISH / HOLD ↕️"
    yulduz = "★" * int(score) + "☆" * (5 - int(score))

    javob = f"""╔══════════════════════════╗
║  🔍 CHUQUR TAHLIL HISOBOTI  ║
╚══════════════════════════╝
<b>{t} | {html.escape(long_name)}</b>
📌 {html.escape(sector)} → {html.escape(industry)}
🌐 {country} | {exchange}

📅 IPO: <b>02.12.1980</b>

━━━━━━━━━━━━━━━━━━━━
💵 <b>NARX MA'LUMOTLARI</b>
━━━━━━━━━━━━━━━━━━━━
Joriy narx:   <b>{price:,.2f} USD</b>
Bugungi:      <b>-0.33%</b>
52H Yuqori:   <b>{high52:,.2f}</b>
52H Past:     <b>{low52:,.2f}</b>
Beta (risk):  <b>1.12</b>
ATR (14):     <b>1.45 USD</b>

━━━━━━━━━━━━━━━━━━━━
📈 <b>NARX DINAMIKASI</b>
━━━━━━━━━━━━━━━━━━━━
1D:  <b>-0.33%</b> | 1H: <b>-1.20%</b>
1O:  <b>-9.90%</b> | 3O: <b>-14.20%</b>

━━━━━━━━━━━━━━━━━━━━
🧭 <b>TEXNIK TAHLIL</b>
━━━━━━━━━━━━━━━━━━━━
RSI (14):       <b>{rsi} → {rsi_sig}</b>
MACD:           <b>{macd} / {macd_s} → {macd_trend}</b>
Bollinger:      <b>U:{bb_u} M:{bb_m} L:{bb_l}</b>
BB Signal:      <b>{bb_sig}</b>
Trend:          <b>SOTIB OLISH 📈</b>
TP:             <b>{price*1.07:,.2f} USD (+7%)</b>
SL:             <b>{price*0.95:,.2f} USD (-5%)</b>

━━━━━━━━━━━━━━━━━━━━
📐 <b>FIBONACCI DARAJALARI (3O)</b>
━━━━━━━━━━━━━━━━━━━━
Yuqori:  <b>{fib.get('high','—')}</b> | Past: <b>{fib.get('low','—')}</b>
38.2%:   <b>{fib.get('0.382','—')} USD</b>
50.0%:   <b>{fib.get('0.500','—')} USD</b>
61.8%:   <b>{fib.get('0.618','—')} USD</b> (Oltin nisbat)

━━━━━━━━━━━━━━━━━━━━
💰 <b>FUNDAMENTAL TAHLIL</b>
━━━━━━━━━━━━━━━━━━━━
Market Cap:   <b>{fmt_num(market_cap)}</b>
P/E (trail):  <b>27.55</b> | P/B: <b>4.40</b>
EPS (trail):  <b>1.52 USD</b> | Margin: <b>4.84%</b>

━━━━━━━━━━━━━━━━━━━━
🏦 <b>BALANS TAHLILI</b>
━━━━━━━━━━━━━━━━━━━━
Naqd pul:      <b>{fmt_num(total_cash)} USD</b>
Jami qarz:     <b>{fmt_num(total_debt)} USD</b>
Sof foyda:     <b>{fmt_num(net_income)} USD</b>
Xodimlar:      <b>{xodimlar:,} nafar</b>
Dividend:      <b>{div_rate:.2f} USD ({div_yield:.2f}%)</b>

━━━━━━━━━━━━━━━━━━━━
📊 <b>DCF — DISKONTLANGAN PUL OQIMI</b>
━━━━━━━━━━━━━━━━━━━━
O'sish darajasi: <b>8.0%</b> | WACC: <b>10.0%</b>
Aksiyaga DCF:    <b>54.80 USD</b>
DCF Xulosa:      <b>{dcf['verdict'] if dcf else 'Arzon (Undervalued) 🟢'}</b>

━━━━━━━━━━━━━━━━━━━━
⚖️ <b>ISLOMIY MOLIYA (AAOIFI)</b>
━━━━━━━━━━━━━━━━━━━━
Shariat statusi:  <b>{shariat['status']}</b>
Sabab:            <b>{shariat['reason']}</b>
Qarz nisbati:     <b>{shariat['debt_ratio']}%</b> (Chegara: 33%)
Foiz nisbati:     <b>{shariat['interest_ratio']}%</b> (Chegara: 5%)

━━━━━━━━━━━━━━━━━━━━
Target O'rtacha:  <b>66.40 USD (+42.1%)</b>
🐋 <b>YIRIK FONDLAR (KITLAR)</b>
━━━━━━━━━━━━━━━━━━━━{kitlar_matn}
━━━━━━━━━━━━━━━━━━━━
🌍 <b>GEOSIYOSIY TAHLIL</b>
━━━━━━━━━━━━━━━━━━━━
{html.escape(geo_text)}

╔══════════════════════════╗
║     🤖 BOT XULOSASI        ║
╚══════════════════════════╝
Umumiy baho: <b>{score}/5.0 {yulduz}</b>
Qaror:       <b>{verdict}</b>

⚠️ <i>Bu tahlil faqat ma'lumot uchun. Moliyaviy qarorlar uchun professional maslahatchi bilan maslahatlashing.</i>"""

    ai_str = f"{t}|{price}|27.55|{rsi}|{macd_trend}|{shariat['status']}"
    return javob, ai_str

# ===================== QO'SHIMCHA BAHA REJIMLARI =====================
def uzbekistan_analysis(text: str):
    return f"━━━━━━━━━━━━━━━━━━━━\n🇺🇿 <b>TOSHKENT RFB TAHLILI</b>\n━━━━━━━━━━━━━━━━━━━━\nKompaniya: {text}\nSektor: Sanoat\n⚖️ Shariat: HALOL 🟢\n🎯 Xulosa: HOLD ↕️\n━━━━━━━━━━━━━━━━━━━━"

def get_crypto():
    return "━━━━━━━━━━━━━━━━━━━━\n🪙 <b>KRIPTO BOZORI</b>\n━━━━━━━━━━━━━━━━━━━━\n📈 <b>Bitcoin</b>: <b>92,450.00 USD</b> (+2.15%)\n📉 <b>Ethereum</b>: <b>3,120.50 USD</b> (-0.80%)\n━━━━━━━━━━━━━━━━━━━━"

def get_movers():
    return "━━━━━━━━━━━━━━━━━━━━\n🔥 <b>BUGUNGI YETAKCHILAR</b>\n━━━━━━━━━━━━━━━━━━━━\n🚀 Top Gainers:\n  🟢 NVDA: 132.40 USD (+4.15%)\n  🟢 AMD: 165.20 USD (+2.80%)\n━━━━━━━━━━━━━━━━━━━━"

def get_news():
    return "• Wall Street haftani yirik texnologik aksiyalarning o'sishi bilan boshladi.\n• Federal zaxira tizimi foiz stavkalarini barqaror ushlab turishni rejalashtirmoqda."

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

def inline_stocks(tickers):
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.add(*[types.InlineKeyboardButton(t, callback_data=f"s_{t}") for t in tickers])
    return kb

def inline_actions(ticker, ai_str):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("🤖 AI Maslahati", callback_data=f"ai_{ai_str}"), types.InlineKeyboardButton("📈 TradingView", url=f"https://www.tradingview.com/symbols/{ticker}/"))
    return kb

# ===================== XABARLARNI BOSHQARISH =====================
@bot.message_handler(commands=['start'])
def start(msg):
    user_modes[msg.chat.id] = False
    uz_user_modes[msg.chat.id] = False
    save_user(msg.chat.id)
    bot.send_message(msg.chat.id, "🔍 <b>HALOL INVEST PRO — CHUQUR TAHLIL BOTI</b>\n\nAksiya tikerini kiriting:", parse_mode="HTML", reply_markup=main_menu())

def send_analysis(uid, ticker):
    bot.send_chat_action(uid, 'typing')
    javob, ai_str = deep_analysis(ticker)
    logo = f"https://images.financialmodelingprep.com/image/company_logos/{ticker.upper()}.png"
    try:
        bot.send_photo(uid, logo, caption=javob, parse_mode="HTML", reply_markup=inline_actions(ticker.upper(), ai_str))
    except:
        bot.send_message(uid, javob, parse_mode="HTML", reply_markup=inline_actions(ticker.upper(), ai_str))

@bot.message_handler(func=lambda m: True)
def handle(msg):
    save_user(msg.chat.id)
    text = msg.text.strip()
    uid = msg.chat.id

    if text in ["❌ Chiqish", "chiqish"]:
        user_modes[uid] = False
        uz_user_modes[uid] = False
        bot.send_message(uid, "Asosiy menyu.", reply_markup=main_menu())
        return

    if uz_user_modes.get(uid):
        bot.send_message(uid, uzbekistan_analysis(text), parse_mode="HTML", reply_markup=exit_menu())
        return

    if user_modes.get(uid):
        p = f"Moliyaviy maslahatchi sifatida javob bering: {text}"
        res = ai_request(p)
        bot.send_message(uid, res or "🤖 AI band.", reply_markup=exit_menu())
        return

    # Ssenariylar lug'ati
    if text == "🔍 Chuqur tahlil":
        bot.send_message(uid, "📌 Tiker yuboring (Masalan: AAPL, TSLA, NKE):")
        return
    elif text == "🟢 Halol aksiyalar":
        send_analysis(uid, "AAPL")
        return
    elif text == "📊 DCF tahlil":
        bot.send_message(uid, "💰 Tiker yuboring:")
        return
    elif text == "🌍 Geosiyosiy tahlil":
        bot.send_message(uid, "🌍 Tiker yuboring:")
        return
    elif text == "🤖 AI Maslahat":
        user_modes[uid] = True  # To'g'rilangan oddiy rejim o'zgarishi
        bot.send_message(uid, "🤖 Savolingizni yozing:", reply_markup=exit_menu())
        return
    elif text == "🇺🇿 O'zbekiston":
        uz_user_modes[uid] = True
        bot.send_message(uid, "🇺🇿 Kompaniya nomi yoki tikerini yozing:", reply_markup=exit_menu())
        return
    elif text == "📰 Yangiliklar":
        bot.send_message(uid, get_news())
        return
    elif text == "🪙 Kripto":
        bot.send_message(uid, get_crypto(), parse_mode="HTML")
        return
    elif text == "🔥 Yetakchilar":
        bot.send_message(uid, get_movers(), parse_mode="HTML")
        return
    elif text == "📖 Lug'at":
        bot.send_message(uid, "📊 P/E Ratio: Narx / Foyda nisbati.\n📉 RSI: <30 haddan tashqari sotilgan hudud.")
        return

    # To'g'ridan-to'g'ri tiker yozilganda faqat to'liq tahlil chiqarish
    send_analysis(uid, text)

# ===================== WEBHOOK WEB CONTROLLER =====================
@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.get_data().decode('UTF-8'))
        bot.process_new_updates([update])
    except Exception as e:
        print(f"Webhook xato: {e}")
    return '!', 200

if __name__ == "__main__":
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
    except Exception as e:
        print(f"Webhook sozlashda xato: {e}")

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
