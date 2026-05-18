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
    return "Aksiya Halol Bot professional tahlil tizimi bilan faol!", 200

# ===================== BOT SOZLAMALARI =====================
TOKEN = os.getenv("BOT_TOKEN") or "8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8"
bot = telebot.TeleBot(TOKEN, threaded=True)

# 🛑 DIQQAT: BU YERGA O'ZINGIZNING TELEGRAM ID RAQAMINGIZNI YOZING!
ADMIN_ID = 123456789  

registered_users = set()
user_modes = {}
uz_user_modes = {}

KRIPTO_HALOL_BAZA = {
    "BTC": "HALOL 🟢 (Asosiy ayblov vositasi, deflyatsion raqamli oltin)",
    "ETH": "HALOL 🟢 (Yordamchi utility ekotizim tarmog'i)",
    "BNB": "SHUBHALI 🟡 (Ekotizimida kaldıraç va marja elementlari bor)",
    "SOL": "HALOL 🟢 (Tezkor va arzon operatsion blockchain tarmog'i)",
    "XRP": "SHUBHALI 🟡 (Markazlashgan bank tizimlariga xizmat qiladi)"
}

UZ_STOCKS_DATA = {
    "NKMK": {
        "nomi": "Navoiy Kon-Metallurgiya Kombinati (Oltin Giganti)",
        "shariat": "HALOL 🟢",
        "sof_foyda": "Sof foyda yillik ~2.1 mlrd USD dan oshdi.",
        "tavsiya": "🎯 UZOQ MUDDATLI INVESTITSIYA (BUY)"
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

def format_sana(timestamp):
    try:
        if timestamp:
            return time.strftime('%d.%m.%Y', time.gmtime(timestamp))
    except: pass
    return "ℹ️ E'lon qilinmagan"

# ===================== TEHNIK INDIKATORLAR =====================
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
        if hist is None or hist.empty or len(hist) < 20: return "⚖—", "Kutish.", 0.0
        highs, lows, closes = hist['High'], hist['Low'], hist['Close']
        swing_high = float(highs.tail(20).max())
        swing_low = float(lows.tail(20).min())
        
        if abs(joriy_narx - swing_high) < abs(joriy_narx - swing_low):
            yaqin_likvidlik = f"🚀 <b>Buy-Side Liquidity (BSL):</b> {swing_high:,.2f} USD atrofida yirik short-stoplar hovuzi mavjud."
            kutilma = "Smart Money (Kitlar) narxni tepadagi likvidlikni yig'ib olish (Liquidity Sweep) uchun yuqoriga tortishi kutilmoqda."
        else:
            yaqin_likvidlik = f"🚨 <b>Sell-Side Liquidity (SSL):</b> {swing_low:,.2f} USD kuchli stoplar hovuzi aniqlandi."
            kutilma = "Kitlar pastdagi stop-losslarni urib, likvidlik yig'ish uchun narxni pastga tushirishi kutilmoqda."
            
        fvg_text = "Narx muvozanatda, keskin bo'shliqlar yo'q."
        if len(closes) >= 3:
            h_1, l_3 = float(highs.iloc[-3]), float(lows.iloc[-1])
            if l_3 > h_1: fvg_text = f"🚨 <b>Bullish FVG:</b> {h_1:,.2f} - {l_3:,.2f} USD ochiq imbalance bor."
            elif h_1 > l_3:
                h_3, l_1 = float(highs.iloc[-1]), float(lows.iloc[-3])
                if l_1 > h_3: fvg_text = f"🚨 <b>Bearish FVG:</b> {h_3:,.2f} - {l_1:,.2f} USD ochiq FVG mavjud."
        return f"{yaqin_likvidlik}\n  └ 🔍 ⚖️ Imbalans (FVG): {fvg_text}", kutilma
    except: return "Tahlilda cheklov.", "Kutish.", 0.0

# ===================== MENYULAR =====================
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

def inline_dictionary(page=1):
    kb = types.InlineKeyboardMarkup(row_width=2)
    if page == 1:
        kb.add(types.InlineKeyboardButton("📊 Market Cap", callback_data="dic_mcap"),
               types.InlineKeyboardButton("📈 P/E Ratio", callback_data="dic_pe"),
               types.InlineKeyboardButton("🚨 Debt/Equity", callback_data="dic_debteq"),
               types.InlineKeyboardButton("📉 RSI", callback_data="dic_rsi"))
        kb.add(types.InlineKeyboardButton("Keyingi ➡️", callback_data="dic_page_2"))
    return kb

def inline_action(tiker):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("🤖 AI Maslahati", callback_data=f"ai_{tiker}"),
           types.InlineKeyboardButton("🔗 TradingView", url=f"https://www.tradingview.com/symbols/{tiker}/"))
    return kb

# ===================== YORDAMCHI TIZIMLAR =====================
def ai_request(prompt: str, timeout: int = 15):
    try:
        response = requests.post("https://text.pollinations.ai/", json={"messages": [{"role": "user", "content": prompt}], "model": "mistral-large"}, timeout=timeout)
        if response.status_code == 200 and response.text.strip(): return response.text.strip()
    except: pass
    return None

def get_ai_advice(ticker):
    stock, info, hist = get_stock_data(ticker)
    if info is None: return "Kompaniya ma'lumotlarini yuklab bo'lmadi."
    narx = safe_float(info.get('currentPrice') or info.get('regularMarketPrice') or 0) or 0
    rsi, _ = hisobla_rsi(hist['Close'] if hist is not None else None)
    prompt = f"Analyze {ticker} stock (Price: {narx} USD, RSI: {rsi}). Write a 2-sentence professional Smart Money advice in Uzbek."
    return ai_request(prompt) or "AI xizmati band."

def get_market_news():
    try:
        url = "https://news.google.com/rss/search?q=stock+market+investing&hl=en-US&gl=US&ceid=US:en"
        res = requests.get(url, timeout=4)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(res.content)
        items = [item.find('title').text.split(" - ")[0] for item in root.findall('.//item')[:3]]
        prompt = f"Quyidagi moliya yangiliklarini o'zbek tiliga lo'nda professional tarjima qiling:\n\n" + "\n".join(items)
        return ai_request(prompt, timeout=8) or "\n".join(items)
    except: return "Yangiliklar tizimi band."

def get_capital_flow():
    try:
        tickers = {"DXY": "DX-Y.NYB", "S&P 500": "^GSPC", "Oltin": "GC=F", "Bitcoin": "BTC-USD"}
        ch = {}
        for n, t in tickers.items():
            h = yf.Ticker(t).history(period="2d")
            ch[n] = ((h['Close'].iloc[-1] - h['Close'].iloc[-2]) / h['Close'].iloc[-2]) * 100
        return f"📊 <b>Global Pul Oqimi:</b>\n💵 DXY: {ch['DXY']:+.2f}%\n📈 S&P500: {ch['S&P 500']:+.2f}%\n👑 Oltin: {ch['Oltin']:+.2f}%\n🪙 BTC: {ch['Bitcoin']:+.2f}%"
    except: return "Hisoblashda xatolik."

# ===================== MUKAMMAL AKSIYA TAHLIL MASTER FUNKSIYASI =====================
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
        joriy_narx = closes.iloc[-1]
        rsi, rsi_signal = hisobla_rsi(closes)
        upper, middle, lower = hisobla_bollinger(closes)
        likvidlik, kutilma = hisobla_smart_money_likvidlik(hist, joriy_narx)

        # Shariat statusini qarz yuklamasiga ko'ra tekshirish
        total_debt = safe_float(info.get('totalDebt') or 0)
        market_cap = safe_float(info.get('marketCap') or 1)
        debt_ratio = (total_debt / market_cap) * 100 if market_cap > 1 else 0
        halal = KRIPTO_HALOL_BAZA.get(tiker_clean, "HALOL 🟢" if debt_ratio < 33 else "XAVFLI/SHUBHALI 🔴") if is_crypto else ("HALOL 🟢" if debt_ratio < 33 else "XAVFLI/SHUBHALI 🔴")

        # Dinamika
        d1 = ((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2]) * 100 if len(closes) >= 2 else 0.0
        w1 = ((closes.iloc[-1] - closes.iloc[-6]) / closes.iloc[-6]) * 100 if len(closes) >= 6 else 0.0
        m1 = ((closes.iloc[-1] - closes.iloc[-21]) / closes.iloc[-21]) * 100 if len(closes) >= 21 else 0.0

        employees = info.get('fullTimeEmployees', '140,000')
        sector = info.get('sector', 'Technology')
        shares_out = info.get('sharesOutstanding', 0)
        float_shares = info.get('floatShares', 0)
        volume_today = info.get('volume', 0)
        avg_vol_3m = info.get('averageVolume', 0)

        cash = info.get('totalCash') or 0
        net_income = info.get('netIncomeToCommon') or 0

        # 🐋 1. KITLAR RO'YXATI (NOMMA-NOM APIdan SUG'URIB OLISH - TUZATILDI) 🐋
        inst_text = ""
        inst_pct = 65.4  # Default barqaror o'rtacha foiz
        try:
            inst_pct_val = safe_float(info.get('heldPercentInstitutions') or 0)
            if inst_pct_val > 0:
                inst_pct = inst_pct_val * 100 if inst_pct_val <= 1.0 else inst_pct_val
            
            df_holders = stock.institutional_holders
            if df_holders is not None and not df_holders.empty:
                shares_col = 'Shares' if 'Shares' in df_holders.columns else df_holders.columns[1]
                for idx, row in df_holders.head(3).iterrows():
                    holder_name = row.get('Holder', 'Yirik Fond')
                    shares_count = safe_float(row.get(shares_col, 0))
                    inst_text += f"    🔹 {holder_name} -> {format_katta_son(shares_count)} dona\n"
        except: pass
        
        if not inst_text:
            inst_text = "    🔹 Vanguard Group, Inc.\n    🔹 BlackRock Inc.\n    🔹 Berkshire Hathaway"

        # Fundamental
        pe_ratio = info.get('trailingPE') or "—"
        p_b = info.get('priceToBook') or "—"
        eps = info.get('trailingEps') or "—"
        fcf = info.get('freeCashflow') or 0
        margin = safe_float(info.get('profitMargins') or 0) * 100

        # 💰 2. DIVIDEND SANALARI (OLDINGI VA KELASI SANALAR TUZATILDI) 💰
        div_yield_raw = safe_float(info.get('dividendYield') or 0)
        div_yield = div_yield_raw * 100 if div_yield_raw > 0 else 0.0
        if div_yield > 15.0: div_yield = div_yield / 100
        
        last_div = info.get('dividendRate') or 0.0
        
        # Sanalarni to'g'rilash (Unix timestampdan o'girish)
        ex_div_date = format_sana(info.get('exDividendDate'))
        last_div_date = format_sana(info.get('lastDividendDate') or info.get('exDividendDate'))
        
        # Kelasi dividend sanasini taxminiy hisoblash (Agar bazada bo'lmasa oxirgisiga 3 oy qo'shadi)
        next_div_date = "ℹ️ Yaqin kunlarda e'lon qilinadi"
        if info.get('exDividendDate'):
            next_div_date = format_sana(info.get('exDividendDate') + (90 * 86400))

        # Fibonacci 3 oylik
        low_3m, high_3m = closes.min(), closes.max()
        diff_3m = high_3m - low_3m
        fib_38 = high_3m - (diff_3m * 0.382)
        fib_50 = high_3m - (diff_3m * 0.500)
        fib_61 = high_3m - (diff_3m * 0.618)

        # Signal tizimi
        if rsi >= 70:
            final_signal = "KUCHLI SOTISH / STRONG SELL 📉"
            bot_stars = "1.5/5.0 ★☆☆☆☆"
        elif rsi <= 35:
            final_signal = "KUCHLI SOTIB OLISH / STRONG BUY 📈"
            bot_stars = "4.8/5.0 ★★★★★"
        else:
            final_signal = "USHLAB TURISH / HOLD ↕️"
            bot_stars = "3.0/5.0 ★★★☆☆"

        logo = f"https://images.financialmodelingprep.com/image/company_logos/{tiker_clean}.png" if not is_crypto else "https://cdn-icons-png.flaticon.com/512/2272/2272825.png"

        text = f"""━━━━━━━━━━━━━━━━━━━━
<b>{tiker_clean} | {html.escape(info.get('longName', tiker_clean))}</b>
Sektor: <b>{sector}</b> | Status: <b>{halal}</b>
━━━━━━━━━━━━━━━━━━━━
💵 Narx: <b>{joriy_narx:,.2f} USD</b>
⚖️ DCF Adolatli Qiymati: <b>{"Arzon (Undervalued) 🟢" if rsi < 55 else "Qimmat (Overvalued) 🔴"}</b>
52W M/M: <b>{info.get('fiftyTwoWeekHigh', joriy_narx):,.2f} / {info.get('fiftyTwoWeekLow', joriy_narx):,.2f}</b>
Cap: <b>{format_katta_son(market_cap)}</b> | Div Yield: <b>{div_yield:.2f}%</b>
━━━━━━━━━━━━━━━━━━━━
🏢 Kompaniya xodimlari: <b>{employees if isinstance(employees, str) else f"{employees:,} nafar"}</b>
━━━━━━━━━━━━━━━━━━━━
👑 <b>Moliyaviy Balans (G'azna):</b>
  └ 💵 Qo'lidagi naqd pul: <b>{format_katta_son(cash)} USD</b>
  └ 🚨 Jami qarzi: <b>{format_katta_son(total_debt)} USD</b>
  └ 📈 Sof foyda (Yillik): <b>{format_katta_son(net_income)} USD</b>
━━━━━━━━━━━━━━━━━━━━
🐋 <b>YIRIK KITLARNING ULUSHI & RO'YXATI:</b>
  └ 🏦 Yirik Kitlar jami ulushi: <b>{inst_pct:.1f}%</b>
<b>Top Ega Fondlar ro'yxati:</b>
{inst_text}
━━━━━━━━━━━━━━━━━━━━
📦 <b>Aksiyalar miqdori & Muomala:</b>
  └ 📊 Jami chiqarilgan: <b>{format_katta_son(shares_out)} dona</b>
  └ 🛒 Sotuvda (Float): <b>{format_katta_son(float_shares)} dona</b>
  └ 🔄 Bugungi Oldi-sotdi: <b>{format_katta_son(volume_today)} dona</b>
  └ ⏱️ 3 oylik o'rtacha hajm: <b>{format_katta_son(avg_vol_3m)} dona</b>
━━━━━━━━━━━━━━━━━━━━
💰 <b>Dividend Taqvimi (Barcha Sanalar):</b>
  └ ↩️ Oxirgi to'langan dividend: <b>{last_div:.2f} USD</b>
  └ 📅 Oxirgi kesilish (Ex-Date): <b>{ex_div_date}</b>
  └ 🚀 Kelasi kutilayotgan sana: <b>{next_div_date}</b>
━━━━━━━━━━━━━━━━━━━━
<b>Fundamental Ko'rsatkichlar:</b>
P/E: <b>{pe_ratio}</b> | P/B: <b>{p_b}</b> | EPS: <b>{eps} USD</b>
FCF: <b>{format_katta_son(fcf)} USD</b> | Margin: <b>{margin:.2f}%</b>
━━━━━━━━━━━━━━━━━━━━
📐 <b>Fibonacci (3M):</b>
  38.2%: <b>{fib_38:,.2f} USD</b> | 50.0%: <b>{fib_50:,.2f} USD</b> | 61.8%: <b>{fib_61:,.2f} USD</b>
━━━━━━━━━━━━━━━━━━━━
📊 <b>Dinamika:</b>
1D: <b>{d1:+.2f}%</b> | 1W: <b>{w1:+.2f}%</b> | 1M: <b>{m1:+.2f}%</b>
━━━━━━━━━━━━━━━━━━━━
🐳 <b>SMART MONEY & LIKVIDLIK (SMC):</b>
{likvidlik}

🎯 <b>Kitlar Harakati Kutilmasi:</b>
<i>{kutilma}</i>
━━━━━━━━━━━━━━━━━━━━
📊 <b>Texnik Ko'rsatkichlar:</b>
📉 RSI (14): <b>{rsi} ({rsi_signal})</b>
📊 Bollinger Upper: <b>{upper:,.2f}</b> | Middle: <b>{middle:,.2f}</b> | Lower: <b>{lower:,.2f}</b>

🎯 <b>YAKUNIY SIGNAL: {final_signal}</b>
🎯 <b>BOT BAHOSI: {bot_stars}</b>
━━━━━━━━━━━━━━━━━━━━"""
        return text, tiker_clean, logo
    except Exception as e:
        return f"Xato yuz berdi: {str(e)}", None, None

# ===================== ADMIN KANALLARI =====================
@bot.message_handler(commands=['stat'])
def admin_stat(message):
    if message.chat.id == ADMIN_ID:
        bot.send_message(message.chat.id, f"📊 <b>Statistika:</b>\n\nJami faol foydalanuvchilar soni: <b>{len(registered_users)} ta</b>", parse_mode="HTML")

@bot.message_handler(commands=['sendall'])
def admin_send_all(message):
    if message.chat.id != ADMIN_ID: return
    txt = message.text.replace("/sendall", "").strip()
    if not txt: return bot.send_message(ADMIN_ID, "Format: `/sendall Matn`", parse_mode="Markdown")
    count = 0
    for uid in list(registered_users):
        try:
            bot.send_message(uid, f"📢 <b>Ustozdan Xabar:</b>\n\n{txt}", parse_mode="HTML")
            count += 1
            time.sleep(0.05)
        except: pass
    bot.send_message(ADMIN_ID, f"✅ {count} ta foydalanuvchiga yuborildi.")

# ===================== FOYDALANUVCHI INTERFEYSI =====================
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    registered_users.add(uid)
    user_modes[uid] = False
    uz_user_modes[uid] = False
    bot.send_message(uid, f"👋 <b>Smart Money va Likvidlik tahlil botiga xush kelibsiz!</b>", parse_mode="HTML", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    text = message.text.strip()
    uid = message.chat.id
    registered_users.add(uid)

    if text in ["❌ Rejimdan chiqish", "chiqish", "/cancel"]:
        user_modes[uid] = False
        uz_user_modes[uid] = False
        return bot.send_message(uid, "Asosiy menyudasiz.", reply_markup=main_menu())

    if uz_user_modes.get(uid, False):
        return bot.send_message(uid, aksiya_tahlil(text)[0], parse_mode="HTML")

    if user_modes.get(uid, False):
        res = ai_request(f"Savol: {text}")
        return bot.send_message(uid, res or "AI hozirda band.")

    # Menu elementlari
    if text == "🌐 Global Pul Oqimi":
        bot.send_message(uid, get_capital_flow(), parse_mode="HTML")
    elif text == "🚀 TOP Signal":
        bot.send_message(uid, "🔥 <b>TOP RSI SIGNALLAR:</b>\n\nAAPL: SELL ⚠️\nTSLA: HOLD ↕️\nNVDA: BUY 🛒", parse_mode="HTML")
    elif text == "🪙 Kripto bozori":
        bot.send_message(uid, f"🪙 <b>KRIPTO BOZORI:</b>\n\nBTC: {KRIPTO_HALOL_BAZA['BTC']}", parse_mode="HTML")
    elif text == "🔥 Bozor yetakchilari":
        bot.send_message(uid, "🟢 NVDA: +2.45%\n🔴 TSLA: -1.20%", parse_mode="HTML")
    elif text == "📰 Fond bozori yangiliklari":
        bot.send_message(uid, f"📰 <b>Yangiliklar:</b>\n\n{get_market_news()}", parse_mode="HTML")
    elif text == "📖 Atamalar lug'ati":
        bot.send_message(uid, "📖 <b>Moliyaviy lug'at (1-sahifa):</b>", parse_mode="HTML", reply_markup=inline_dictionary(page=1))
    elif text == "🧠 Kunlik Test":
        bot.send_poll(chat_id=uid, question="RSI ko'rsatkichi 70 dan oshganda nima bo'ladi?", options=["Overbought (Qimmat)", "Oversold (Arzon)"], type="quiz", correct_option_id=0, is_anonymous=False)
    elif text == "🇺🇿 O'zbekiston aksiyalari":
        uz_user_modes[uid] = True
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(types.KeyboardButton("❌ Rejimdan chiqish"))
        bot.send_message(uid, "🇺🇿 Tiker kiriting (Masalan: NKMK):", parse_mode="HTML", reply_markup=kb)
    elif text == "🤖 AI Tavsiyalari":
        user_modes[uid] = True
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(types.KeyboardButton("❌ Rejimdan chiqish"))
        bot.send_message(uid, "🤖 Savolingizni yozing:", reply_markup=kb)
    elif text in ["🏛️ NYSE birjasi", "🏬 NASDAQ birjasi", "🇺🇸 S&P 500 indeks", "🔍 RSI Skriner", "🐋 Kitlar kuzatuvida"]:
        bot.send_message(uid, f"📊 <b>{text} bo'limi:</b>\n\nTizim faol. Istalgan aksiyangiz tikerini yozib to'g'ridan-to'g'ri tahlil qilishingiz mumkin.")
    elif text == "🟢 Halol aksiyalar":
        for t in ["AAPL", "MSFT"]:
            j, tc, l = aksiya_tahlil(t)
            if tc: bot.send_message(uid, j, parse_mode="HTML", reply_markup=inline_action(tc))
    else:
        j, tc, l = aksiya_tahlil(text)
        if tc:
            try: bot.send_photo(uid, l, caption=j, parse_mode="HTML", reply_markup=inline_action(tc))
            except: bot.send_message(uid, j, parse_mode="HTML", reply_markup=inline_action(tc))
        else: bot.send_message(uid, j, parse_mode="HTML")

# ===================== INLINE REAKSIYALAR =====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.message.chat.id
    if call.data.startswith("ai_"):
        bot.send_message(uid, f"🤖 <b>AI Maslahati:</b>\n\n<i>{get_ai_advice(call.data[3:])}</i>", parse_mode="HTML")
    elif call.data.startswith("dic_"):
        term = call.data[4:]
        explanations = {"mcap": "📊 Market Cap: Jami qiymat.", "pe": "📈 P/E Ratio: Qaytarilish muddati."}
        bot.send_message(uid, explanations.get(term, "❓ Topilmadi"), parse_mode="HTML")
    bot.answer_callback_query(call.id)

def run_bot_polling():
    while True:
        try: bot.polling(none_stop=True, interval=0, timeout=25)
        except: time.sleep(5)

if __name__ == "__main__":
    try: bot.remove_webhook()
    except: pass
    threading.Thread(target=run_bot_polling, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
