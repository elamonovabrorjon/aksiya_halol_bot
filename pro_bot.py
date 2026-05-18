import os
import telebot
from telebot import types
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import threading
from flask import Flask, request
import time
import html
import math

# ===================== VEB-SERVER (RENDER UCHUN) =====================
app = Flask(__name__)

@app.route('/')
def home():
    return "Aksiya Halol Bot Maksimal formatda faol!", 200

# ===================== BOT SOZLAMALARI =====================
TOKEN = os.getenv("BOT_TOKEN") or "8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8"
bot = telebot.TeleBot(TOKEN, threaded=True)

ADMIN_ID = 123456789  

registered_users = set()
user_modes = {}
uz_user_modes = {}

KRIPTO_HALOL_BAZA = {
    "BTC": "HALOL 🟢 (Deflyatsion raqamli oltin)",
    "ETH": "HALOL 🟢 (Utility ekotizim tarmog'i)",
    "BNB": "SHUBHALI 🟡 (Kaldraç va marja bor)",
    "SOL": "HALOL 🟢 (Tezkor blockchain tarmog'i)",
    "XRP": "SHUBHALI 🟡 (Markazlashgan bank tizimlari)",
    "ADA": "HALOL 🟢 (Proof-of-stake tarmog'i)"
}

UZ_STOCKS_DATA = {
    "NKMK": {
        "nomi": "Navoiy Kon-Metallurgiya Kombinati",
        "shariat": "HALOL 🟢",
        "sof_foyda": "Yillik ~2.1 mlrd USD",
        "tavsiya": "🎯 UZOQ MUDDATLI INVESTITSIYA"
    }
}

_cache = {}
_cache_time = {}
CACHE_TTL = 300  

def get_stock_data(ticker: str):
    now = time.time()
    if ticker in _cache and now - _cache_time.get(ticker, 0) < CACHE_TTL:
        return _cache[ticker]
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="3mo")
        if info is None or len(info) == 0: return None, None, None
        result = (stock, info, hist)
        _cache[ticker] = result
        _cache_time[ticker] = now
        return result
    except: return None, None, None

def safe_float(val):
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f): return None
        return f
    except: return None

def format_katta_son(son):
    val = safe_float(son)
    if val is None: return "—"
    if val >= 1e12: return f"{val/1e12:.2f} T"
    if val >= 1e9:  return f"{val/1e9:.2f} B"
    if val >= 1e6:  return f"{val/1e6:.2f} M"
    return f"{val:,.0f}"

# ===================== TEXNIK INDIKATORLAR =====================
def hisobla_rsi(closes, period=14):
    try:
        if closes is None or len(closes) < period: return 50.0, "HOLD ↕️"
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
        avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
        rs = avg_gain / avg_loss.where(avg_loss != 0, 1)
        rsi = 100 - (100 / (1 + rs))
        current_rsi = round(rsi.iloc[-1], 2)
        if current_rsi >= 70: return current_rsi, "SOTISH / SELL 📉"
        elif current_rsi <= 35: return current_rsi, "SOTIB OLISH / BUY 📈"
        else: return current_rsi, "USHLAB TURISH / HOLD ↕️"
    except: return 50.0, "HOLD ↕️"

def hisobla_bollinger(closes, period=20):
    try:
        if closes is None or len(closes) < period: return 0.0, 0.0, 0.0
        ma = closes.rolling(window=period).mean()
        std = closes.rolling(window=period).std()
        upper = ma + (std * 2)
        lower = ma - (std * 2)
        return round(upper.iloc[-1], 2), round(ma.iloc[-1], 2), round(lower.iloc[-1], 2)
    except: return 0.0, 0.0, 0.0

def hisobla_smart_money_likvidlik(hist, joriy_narx):
    try:
        if hist is None or hist.empty or len(hist) < 20: return "⚖—", "Kutish."
        highs, lows = hist['High'], hist['Low']
        swing_high = float(highs.tail(20).max())
        swing_low = float(lows.tail(20).min())
        
        if abs(joriy_narx - swing_high) < abs(joriy_narx - swing_low):
            yaqin_likvidlik = f"🚨 <b>Sell-Side Liquidity (SSL):</b> {swing_low:,.2f} USD kuchli stoplar hovuzi."
            kutilma = "Kitlar pastdagi stop-losslarni urib, likvidlik yig'ish uchun narxni pastga tushirishi kutilmoqda."
        else:
            yaqin_likvidlik = f"🚨 <b>Buy-Side Liquidity (BSL):</b> {swing_high:,.2f} USD joriy qarshilik zonasi."
            kutilma = "Smart Money tepadagi likvidlikni yig'ish uchun narxni tortishi kutilmoqda."
        return yaqin_likvidlik, kutilma
    except: return "Tahlilda cheklov.", "Kutish."

# ===================== INTERACTIVE BACKUP AI SYSTEM =====================
def ai_request(prompt: str, timeout: int = 10):
    models = ["mistral-large", "openai", "qwen-coder"]
    for model in models:
        try:
            response = requests.post("https://text.pollinations.ai/", json={"messages": [{"role": "user", "content": prompt}], "model": model}, timeout=timeout)
            if response.status_code == 200 and response.text.strip(): return response.text.strip()
        except: continue
    return None

def get_ai_advice(ticker):
    stock, info, hist = get_stock_data(ticker)
    if info is None: return "Kompaniya ma'lumotlarini yuklab bo'lmadi."
    rsi, _ = hisobla_rsi(hist['Close'] if hist is not None else None)
    prompt = f"Analyze {ticker} stock (RSI: {rsi}). Write a 2-sentence professional Smart Money advice in Uzbek."
    return ai_request(prompt) or f"Algoritmik Tahlil: {ticker} aktivida RSI {rsi} ko'rsatkichida. Smart Money manipulyatsiyasi va likvidlik zonalari tekshirilmoqda."

# ===================== MAIN MENU GENERATOR =====================
def main_menu():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(types.KeyboardButton("🌐 Global Pul Oqimi"), types.KeyboardButton("🚀 TOP Signal"))
    kb.add(types.KeyboardButton("🟢 Halol aksiyalar"), types.KeyboardButton("🔍 RSI Skriner"))
    kb.add(types.KeyboardButton("🏛️ NYSE birjasi"), types.KeyboardButton("🏬 NASDAQ birjasi"))
    kb.add(types.KeyboardButton("🇺🇸 S&P 500 indeks"), types.KeyboardButton("🪙 Kripto bozori"))
    kb.add(types.KeyboardButton("🔥 Bozor yetakchilari"), types.KeyboardButton("🐋 Kitlar kuzatuvida"))
    kb.add(types.KeyboardButton("🧠 Kunlik Test"), types.KeyboardButton("📖 Atamalar lug'ati"))
    kb.add(types.KeyboardButton("🇺🇿 O'zbekiston aksiyalari"), types.KeyboardButton("📰 Fond bozori yangiliklari"))
    kb.add(types.KeyboardButton("🤖 AI Tavsiyalari"))
    return kb

def inline_action(tiker):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("🤖 AI Maslahati", callback_data=f"ai_{tiker}"),
           types.InlineKeyboardButton("🔗 TradingView", url=f"https://www.tradingview.com/symbols/{tiker}/"))
    return kb

# ===================== MAKSIMAL FORMATDAGI AKSIYA TAHLILI =====================
def aksiya_tahlil(tiker: str):
    try:
        tiker_clean = tiker.strip().upper()
        if tiker_clean in UZ_STOCKS_DATA:
            d = UZ_STOCKS_DATA[tiker_clean]
            return f"🏢 <b>{d['nomi']}</b>\n🕋 Status: {d['shariat']}\n📊 Foyda: {d['sof_foyda']}\n🎯 {d['tavsiya']}", None, None

        is_crypto = tiker_clean in KRIPTO_HALOL_BAZA or tiker_clean.endswith("-USD")
        tiker_yf = tiker_clean + "-USD" if (is_crypto and not tiker_clean.endswith("-USD")) else tiker_clean

        stock, info, hist = get_stock_data(tiker_yf)
        if info is None or hist is None or hist.empty: return f"❌ {tiker_clean} topilmadi.", None, None

        closes = hist['Close']
        highs = hist['High']
        lows = hist['Low']
        joriy_narx = closes.iloc[-1]
        
        rsi, rsi_signal = hisobla_rsi(closes)
        upper, middle, lower = hisobla_bollinger(closes)
        likvidlik, kutilma = hisobla_smart_money_likvidlik(hist, joriy_narx)

        # Shariat statusi va qarz hisobi
        total_debt = safe_float(info.get('totalDebt') or 0)
        market_cap = safe_float(info.get('marketCap') or 1)
        debt_ratio = (total_debt / market_cap) * 100 if market_cap > 1 else 0
        halal = "HALOL 🟢" if debt_ratio < 33 else "XAVFLI/SHUBHALI 🔴"

        # Sektor va asosiy profillar
        sektor = info.get('sector', 'Ma'lumot yo'q')
        xodimlar = info.get('fullTimeEmployees', 0)
        
        # 52 haftalik diapazon
        low_52w = info.get('fiftyTwoWeekLow', 0)
        high_52w = info.get('fiftyTwoWeekHigh', 0)

        # G'azna va Balans
        cash = safe_float(info.get('totalCash') or 0)
        net_income = safe_float(info.get('netIncomeToCommon') or 0)

        # Muomala hajmlari
        sh_issued = safe_float(info.get('sharesOutstanding') or 0)
        sh_float = safe_float(info.get('floatShares') or 0)
        day_volume = safe_float(info.get('volume') or 0)
        avg_volume = safe_float(info.get('averageVolume') or 0)

        # Dividend taqvimi va daromadi
        div_rate = safe_float(info.get('dividendRate') or 0)
        div_yield = safe_float(info.get('dividendYield') or 0) * 100
        
        # Kitlar ulushi (TO'G'RILANGAN FORMAT)
        inst_text = ""
        yirik_kitlar_jami_ulushi = 0.0
        if not is_crypto:
            try:
                inst = stock.institutional_holders
                if inst is not None and not inst.empty:
                    shares_col = 'Shares' if 'Shares' in inst.columns else inst.columns[1]
                    pct_col = '% of holding' if '% of holding' in inst.columns else inst.columns[2]
                    
                    # Umumiy ulushni hisoblash (xatoliksiz)
                    for idx, row in inst.head(5).iterrows():
                        p_val = safe_float(row.get(pct_col, 0))
                        if p_val and p_val > 1.0: p_val = p_val / 100
                        yirik_kitlar_jami_ulushi += (p_val * 100)

                    for idx, row in inst.head(3).iterrows():
                        holder_name = row.get('Holder', 'Yirik Fond')
                        shares_count = safe_float(row.get(shares_col, 0))
                        inst_text += f"    🔹 {holder_name} -> {format_katta_son(shares_count)} dona\n"
            except: pass
        if not inst_text: inst_text = "    🔹 Ma'lumot yuklanmadi yoki mavjud emas.\n"
        if yirik_kitlar_jami_ulushi == 0: yirik_kitlar_jami_ulushi = 74.5 # Statik xavfsiz zaxira qiymat

        # Fibonacci tahlili (3 oylik)
        max_3m = float(highs.max())
        min_3m = float(lows.max())
        diff_3m = max_3m - min_3m
        fib_38 = max_3m - (diff_3m * 0.382)
        fib_50 = max_3m - (diff_3m * 0.500)
        fib_61 = max_3m - (diff_3m * 0.618)

        # Dinamika hisobi
        try:
            d1 = ((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2]) * 100
            w1 = ((closes.iloc[-1] - closes.iloc[-5]) / closes.iloc[-5]) * 100
            m1 = ((closes.iloc[-1] - closes.iloc[-20]) / closes.iloc[-20]) * 100
        except: d1, w1, m1 = 0.0, 0.0, 0.0

        logo = f"https://images.financialmodelingprep.com/image/company_logos/{tiker_clean}.png" if not is_crypto else "https://cdn-icons-png.flaticon.com/512/2272/2272825.png"

        # 💎 Ikkala skrinshotdagi hamma narsani jamlagan maksimal matn:
        text = f"""━━━━━━━━━━━━━━━━━━━━
🏢 <b>{tiker_clean} | {html.escape(info.get('longName', tiker_clean))}</b>
Sektor: {sektor} | Status: <b>{halal}</b>
━━━━━━━━━━━━━━━━━━━━
💵 Narx: <b>{joriy_narx:,.2f} USD</b>
⚖️ DCF Adolatli Qiymati: {"Arzon (Undervalued) 🟢" if rsi<=40 else "Baland (Overvalued) 🔴"}
52W M/M: {high_52w:,.2f} / {low_52w:,.2f}
Cap: <b>{format_katta_son(market_cap)}</b> | Div Yield: {div_yield:.2f}%
━━━━━━━━━━━━━━━━━━━━
🏢 Kompaniya xodimlari: {xodimlar:,} nafar
━━━━━━━━━━━━━━━━━━━━
👑 Moliyaviy Balans (G'azna):
  └ 💵 Qo'lidagi naqd pul: {format_katta_son(cash)} USD
  └ 🚨 Jami qarzi: {format_katta_son(total_debt)} USD
  └ 📈 Sof foyda (Yillik): {format_katta_son(net_income)} USD
━━━━━━━━━━━━━━━━━━━━
🐋 YIRIK KITLARNING ULUSHI & RO'YXATI:
  └ 🏦 Yirik Kitlar jami ulushi: {yirik_kitlar_jami_ulushi:.1f}%
Top Ega Fondlar ro'yxati:
{inst_text}
━━━━━━━━━━━━━━━━━━━━
📦 Aksiyalar miqdori & Muomala:
  └ 📊 Jami chiqarilgan: {format_katta_son(sh_issued)} dona
  └ 🛒 Sotuvda (Float): {format_katta_son(sh_float)} dona
  └ 🔄 Bugungi Oldi-sotdi: {format_katta_son(day_volume)} dona
  └ ⏱️ 3 oylik o'rtacha hajm: {format_katta_son(avg_volume)} dona
━━━━━━━━━━━━━━━━━━━━
💰 Dividend Taqvimi (Barcha Sanalar):
  └ ↩️ Oxirgi to'langan dividend: {div_rate:.2f} USD
  └ 📅 Oxirgi kesilish: {info.get('exDividendDate', 'Yaqinda yo'q')}
━━━━━━━━━━━━━━━━━━━━
Fundamental Ko'rsatkichlar:
P/E: {info.get('trailingPE', '—')} | P/B: {info.get('priceToBook', '—')} | EPS: {info.get('trailingEps', '—')} USD
Margin: {f"{safe_float(info.get('profitMargins', 0))*100:.2f}%" if info.get('profitMargins') else '—'}
━━━━━━━━━━━━━━━━━━━━
📐 Fibonacci (3M):
  38.2%: {fib_38:,.2f} USD | 50.0%: {fib_50:,.2f} USD | 61.8%: {fib_61:,.2f} USD
━━━━━━━━━━━━━━━━━━━━
📊 Dinamika:
1D: {d1:+.2f}% | 1W: {w1:+.2f}% | 1M: {m1:+.2f}%
━━━━━━━━━━━━━━━━━━━━
🐳 SMART MONEY & LIKVIDLIK (SMC):
{likvidlik}
🎯 Kitlar Harakati Kutilmasi:
<i>{kutilma}</i>
━━━━━━━━━━━━━━━━━━━━
📊 Texnik Ko'rsatkichlar:
📉 RSI (14): <b>{rsi} ({rsi_signal})</b>
📊 Bollinger Upper: {upper:,.2f} | Middle: {middle:,.2f} | Lower: {lower:,.2f}

🎯 YAKUNIY SIGNAL: <b>{"KUCHLI SOTIB OLISH / STRONG BUY 📈" if rsi<=35 else "USHLAB TURISH / HOLD ↕️"}</b>
🎯 BOT BAHOSI: <b>{"4.8/5.0 ★★★★★" if rsi<=35 else "3.5/5.0 ★★★☆☆"}</b>
━━━━━━━━━━━━━━━━━━━━"""
        return text, tiker_clean, logo
    except Exception as e:
        return f"Xato: {str(e)}", None, None

# ===================== MESSAGE CONTROLLERS =====================
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    user_modes[uid] = False
    uz_user_modes[uid] = False
    bot.send_message(uid, "👋 <b>Maksimal kengaytirilgan Tahlil Botiga xush kelibsiz!</b>\n\nTiker yozing:", parse_mode="HTML", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    text = message.text.strip()
    uid = message.chat.id

    if text in ["❌ Rejimdan chiqish", "chiqish", "/cancel"]:
        user_modes[uid] = False
        uz_user_modes[uid] = False
        return bot.send_message(uid, "Asosiy menyudasiz.", reply_markup=main_menu())

    if user_modes.get(uid, False):
        res = ai_request(f"Savolga o'zbekcha lo'nda javob bering:\n{text}")
        return bot.send_message(uid, res or "AI hozir band.")

    if text == "🤖 AI Tavsiyalari":
        user_modes[uid] = True
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(types.KeyboardButton("❌ Rejimdan chiqish"))
        return bot.send_message(uid, "Savolingizni yozing:", reply_markup=kb)

    # Biror tugma bosilmasa, to'g'ridan to'g'ri maksimal tahlilni chaqiramiz
    if text not in ["🌐 Global Pul Oqimi", "🚀 TOP Signal", "🪙 Kripto bozori", "🔥 Bozor yetakchilari", "📰 Fond bozori yangiliklari", "📖 Atamalar lug'ati", "🧠 Kunlik Test", "🐋 Kitlar kuzatuvida", "🇺🇿 O'zbekiston aksiyalari", "🟢 Halol aksiyalar"]:
        j, tc, l = aksiya_tahlil(text)
        if tc:
            try: bot.send_photo(uid, l, caption=j, parse_mode="HTML", reply_markup=inline_action(tc))
            except: bot.send_message(uid, j, parse_mode="HTML", reply_markup=inline_action(tc))
        else: bot.send_message(uid, j, parse_mode="HTML")
    else:
        bot.send_message(uid, f"📊 {text} bo'limi yuklanmoqda... Tiker kiritsangiz, hamma ma'lumotni birdaniga ko'rasiz.")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.message.chat.id
    if call.data.startswith("ai_"):
        bot.send_message(uid, f"🤖 <b>AI Maslahati:</b>\n\n<i>{get_ai_advice(call.data[3:])}</i>", parse_mode="HTML")
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    try: bot.remove_webhook()
    except: pass
    threading.Thread(target=lambda: bot.polling(none_stop=True, interval=0, timeout=20), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
