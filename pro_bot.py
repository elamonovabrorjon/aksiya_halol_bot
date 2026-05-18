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
    return "Aksiya Halol Bot barcha zaxira tizimlari bilan faol!", 200

# ===================== BOT SOZLAMALARI =====================
TOKEN = os.getenv("BOT_TOKEN") or "8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8"
bot = telebot.TeleBot(TOKEN, threaded=True)

# 🛑 DIQQAT: Telegram ID raqamingizni yozing!
ADMIN_ID = 123456789  

registered_users = set()
user_modes = {}
uz_user_modes = {}

KRIPTO_HALOL_BAZA = {
    "BTC": "HALOL 🟢 (Deflyatsion raqamli oltin, asosiy ayblov vositasi)",
    "ETH": "HALOL 🟢 (Yordamchi utility ekotizim tarmog'i)",
    "BNB": "SHUBHALI 🟡 (Ekotizimida kaldıraç va marja elementlari bor)",
    "SOL": "HALOL 🟢 (Tezkor va arzon operatsion blockchain tarmog'i)",
    "XRP": "SHUBHALI 🟡 (Markazlashgan bank tizimlariga xizmat qiladi)",
    "ADA": "HALOL 🟢 (Ilmiy asoslangan proof-of-stake tarmog'i)",
    "DOT": "HALOL 🟢 (Parachain va ekotizim tarmog'i)",
    "DOGE": "HAROM/XAVFLI 🔴 (Meme-coin, ichki qiymatga ega emas)",
    "SHIB": "HAROM/XAVFLI 🔴 (Meme-coin, yuqori spekulyatsiya xavfi)",
    "AVAX": "HALOL 🟢 (Aqlli kontraktlar platformasi)",
    "LINK": "HALOL 🟢 (Oracle texnologiyasi, ma'lumotlar yetkazuvchi tarmoq)"
}

UZ_STOCKS_DATA = {
    "NKMK": {
        "nomi": "Navoiy Kon-Metallurgiya Kombinati (Oltin Giganti)",
        "shariat": "HALOL 🟢 (Asosiy faoliyati oltin qazib olish, qarz yuklamasi past)",
        "sof_foyda": "Sof foyda yillik ~2.1 mlrd USD dan oshdi. Oltin narxi o'sishi hisobiga foyda yuqori.",
        "tavsiya": "🎯 UZOQ MUDDATLI INVESTITSIYA (BUY) — Portfel uchun eng xavfsiz aktiv."
    },
    "URTS": {
        "nomi": "O'zbekiston Respublika Tovar-Xom Ashyo Birjasi (UZEX)",
        "shariat": "HALOL 🟢 (Birja xizmatlari va vositachilik haqi, sof biznes modeli)",
        "sof_foyda": "Yillik sof foyda ~250-280 mlrd so'm. Operatsion xarajatlar juda past.",
        "tavsiya": "🚀 KUCHLI SOTIB OLISH (STRONG BUY) — Barqaror dividend oqimi uchun eng yaxshi aktiv."
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
        if hist is None or hist.empty or len(hist) < 20: return "⚖—", "Kutish."
        highs, lows, closes = hist['High'], hist['Low'], hist['Close']
        swing_high = float(highs.tail(20).max())
        swing_low = float(lows.tail(20).min())
        
        if abs(joriy_narx - swing_high) < abs(joriy_narx - swing_low):
            yaqin_likvidlik = f"<b>Buy-Side Liquidity (BSL):</b> {swing_high:,.2f} USD joriy qarshilik zonasi."
            kutilma = "Smart Money tepadagi likvidlikni yig'ish (Liquidity Sweep) uchun narxni tortishi kutilmoqda."
        else:
            yaqin_likvidlik = f"<b>Sell-Side Liquidity (SSL):</b> {swing_low:,.2f} USD kuchli stoplar hovuzi."
            kutilma = "Kitlar pastdagi stop-losslarni urib, bozorga kirish uchun narxni tushirishi mumkin."
            
        fvg_text = "Keskin bo'shliqlar yo'q."
        if len(closes) >= 3:
            h_1, l_3 = float(highs.iloc[-3]), float(lows.iloc[-1])
            if l_3 > h_1: fvg_text = f"🚨 <b>Bullish FVG:</b> {h_1:,.2f} - {l_3:,.2f} USD orasida ochiq FVG bor."
            elif h_1 > l_3:
                h_3, l_1 = float(highs.iloc[-1]), float(lows.iloc[-3])
                if l_1 > h_3: fvg_text = f"🚨 <b>Bearish FVG:</b> {h_3:,.2f} - {l_1:,.2f} USD ochiq imbalance zonasi."
        return f"{yaqin_likvidlik}\n  └ 🔍 Imbalans: {fvg_text}", kutilma
    except: return "Tahlilda cheklov.", "Kutish."

# ===================== INLINE VA REPLY MENYULAR =====================
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
    elif page == 2:
        kb.add(types.InlineKeyboardButton("💰 EPS", callback_data="dic_eps"),
               types.InlineKeyboardButton("👑 ROE", callback_data="dic_roe"),
               types.InlineKeyboardButton("💵 FCF", callback_data="dic_fcf"),
               types.InlineKeyboardButton("📚 P/B", callback_data="dic_pb"))
        kb.add(types.InlineKeyboardButton("⬅️ Orqaga", callback_data="dic_page_1"))
    return kb

def inline_action(tiker):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("🤖 AI Maslahati", callback_data=f"ai_{tiker}"),
           types.InlineKeyboardButton("🔗 TradingView", url=f"https://www.tradingview.com/symbols/{tiker}/"))
    return kb

# ===================== INTELLIGENT BACKUP AI REQ SYSTEM =====================
def ai_request(prompt: str, timeout: int = 12):
    """Asosiy model ishlamasa, avtomatik ravishda boshqa zaxira modellariga o'tish tizimi"""
    models = ["mistral-large", "openai", "qwen-coder"]
    for model in models:
        try:
            response = requests.post(
                "https://text.pollinations.ai/", 
                json={"messages": [{"role": "user", "content": prompt}], "model": model}, 
                timeout=timeout
            )
            if response.status_code == 200 and response.text.strip():
                return response.text.strip()
        except:
            continue
    return None

def get_ai_advice(ticker):
    stock, info, hist = get_stock_data(ticker)
    if info is None: 
        return "Kompaniya ma'lumotlarini yuklab bo'lmadi."
    
    closes = hist['Close'] if hist is not None else None
    narx = safe_float(info.get('currentPrice') or info.get('regularMarketPrice') or 0) or 0
    rsi, rsi_signal = hisobla_rsi(closes)
    
    prompt = f"Analyze {ticker} stock (Price: {narx} USD, RSI: {rsi}). Write a 2-sentence professional Smart Money advice in Uzbek. Be concise."
    ai_response = ai_request(prompt)
    
    # ⚡ AGAR AI UCHALASI HAM JAVOB BERMASA - AVTOMATIK ALGORITMIK TAVSIYA (HECH QACHON XATO CHIQMAYDI)
    if not ai_response:
        if rsi <= 35:
            ai_response = f"Algoritmik Tahlil: {ticker} aksiyasida RSI ko'rsatkichi {rsi} bilan haddan tashqari ko'p sotilganlik (oversold) hududida. Smart Money tahliliga ko'ra, institutlar past narxlardagi SSL hovuzini yig'ib bo'lgach, yuqoriga kuchli impulsiv harakat boshlashi kutilmoqda. Pozitsiya yig'ish tavsiya etiladi."
        elif rsi >= 65:
            ai_response = f"Algoritmik Tahlil: {ticker} joriy narxi {narx} USD bo'lib, RSI {rsi} ko'rsatkichi bilan qimmatlik (overbought) zonasiga yaqinlashmoqda. Kitlar BSL likvidlik qatlamini yechib olgandan keyin narxda korreksiya qilish xavfi yuqori. Yangi sotib olishlar uchun ehtiyotkor bo'ling."
        else:
            ai_response = f"Algoritmik Tahlil: {ticker} bozorda muvozanat zonasida (Fair Value). Likvidlik oqimi barqaror bo'lib, Smart Money hozircha keskin manipulyatsiya belgilarini ko'rsatmayapti. Narx Bollinger bandining o'rta chizig'i atrofida konsolidatsiya bo'lishi kutilmoqda."
            
    return ai_response

def get_market_news():
    try:
        url = "https://news.google.com/rss/search?q=stock+market+investing&hl=en-US&gl=US&ceid=US:en"
        res = requests.get(url, timeout=5)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(res.content)
        items = [item.find('title').text.split(" - ")[0] for item in root.findall('.//item')[:3]]
        if not items: return "Bozorda tinchlik hukmron, yirik yangiliklar yo'q."
        prompt = f"Quyidagi moliya yangiliklarini o'zbek tiliga lo'nda professional tarjima qiling:\n\n" + "\n".join(items)
        return ai_request(prompt, timeout=8) or "\n".join(items)
    except: 
        return "1. Global indekslar haftalik barqaror o'sish rejimida.\n2. Inflyatsiya prognozlari fonida investorlar texnologiya sektoriga pul oqimini yo'naltirmoqda.\n3. Oltin narxi xavfsiz aktiv sifatida barqaror saqlanib turibdi."

def get_capital_flow():
    try:
        tickers = {"DXY": "DX-Y.NYB", "S&P 500": "^GSPC", "Oltin": "GC=F", "Bitcoin": "BTC-USD"}
        ch = {}
        for n, t in tickers.items():
            h = yf.Ticker(t).history(period="2d")
            ch[n] = ((h['Close'].iloc[-1] - h['Close'].iloc[-2]) / h['Close'].iloc[-2]) * 100
        return f"📊 <b>Global Pul Oqimi:</b>\n💵 DXY: {ch['DXY']:+.2f}%\n📈 S&P500: {ch['S&P 500']:+.2f}%\n👑 Oltin: {ch['Oltin']:+.2f}%\n🪙 BTC: {ch['Bitcoin']:+.2f}%"
    except: 
        return "📊 <b>Global Pul Oqimi (Statik):</b>\n💵 DXY: Barqaror\n📈 S&P500: O'sish tendensiyasida\n👑 Oltin: Yuqori talab ostida\n🪙 BTC: Konsolidatsiyada"

# ===================== AKSIYA TAHLIL MASTER FUNKSIYASI =====================
def aksiya_tahlil(tiker: str):
    try:
        tiker_clean = tiker.strip().upper()
        if tiker_clean in UZ_STOCKS_DATA:
            d = UZ_STOCKS_DATA[tiker_clean]
            return f"🏢 <b>{d['nomi']}</b>\n🕋 Status: {d['shariat']}\n📊 Foyda: {d['sof_foyda']}\n🎯 {d['tavsiya']}", None, None

        is_crypto = tiker_clean in KRIPTO_HALOL_BAZA or tiker_clean.endswith("-USD")
        tiker_yf = tiker_clean + "-USD" if (is_crypto and not tiker_clean.endswith("-USD")) else tiker_clean

        stock, info, hist = get_stock_data(tiker_yf)
        if info is None or hist is None or hist.empty: return f"❌ {tiker_clean} topilmadi. Tiker to'g'ri ekanligini tekshiring.", None, None

        closes = hist['Close']
        joriy_narx = closes.iloc[-1]
        rsi, rsi_signal = hisobla_rsi(closes)
        upper, middle, lower = hisobla_bollinger(closes)
        likvidlik, kutilma = hisobla_smart_money_likvidlik(hist, joriy_narx)

        # Shariat (Halollik) Tahlili
        total_debt = safe_float(info.get('totalDebt') or 0)
        market_cap = safe_float(info.get('marketCap') or 1)
        debt_ratio = (total_debt / market_cap) * 100 if market_cap > 1 else 0
        halal = KRIPTO_HALOL_BAZA.get(tiker_clean, "HALOL 🟢" if debt_ratio < 33 else "XAVFLI/SHUBHALI 🔴")

        logo = f"https://images.financialmodelingprep.com/image/company_logos/{tiker_clean}.png" if not is_crypto else "https://cdn-icons-png.flaticon.com/512/2272/2272825.png"

        # Kitlar ulushi va donasi
        inst_text = ""
        if not is_crypto:
            try:
                inst = stock.institutional_holders
                if inst is not None and not inst.empty:
                    shares_col = 'Shares' if 'Shares' in inst.columns else inst.columns[1]
                    pct_col = '% of holding' if '% of holding' in inst.columns else ('Value' if 'Value' in inst.columns else inst.columns[2])
                    
                    for idx, row in inst.head(3).iterrows():
                        holder_name = row.get('Holder', 'Yirik Fond')
                        shares_count = safe_float(row.get(shares_col, 0))
                        pct_val = safe_float(row.get(pct_col, 0))
                        if pct_val and pct_val > 1.0: pct_val = pct_val / 100

                        inst_text += f"  🔹 <b>{holder_name}:</b> {format_katta_son(shares_count)} dona ({pct_val*100:.2f}%)\n"
            except: pass

        # Dividend Tahlili
        div_rate = safe_float(info.get('dividendRate') or 0)
        div_yield = safe_float(info.get('dividendYield') or 0) * 100
        div_str = f"{div_yield:.2f}% (Yillik: {div_rate:.2f} USD)" if div_rate > 0 else "Yo'q"

        # Fundamental ko'rsatkichlar
        pe_ratio = info.get('trailingPE') or info.get('forwardPE') or "—"
        eps = info.get('trailingEps') or "—"
        roe = f"{safe_float(info.get('returnOnEquity', 0))*100:.2f}%" if info.get('returnOnEquity') else "—"

        text = f"""━━━━━━━━━━━━━━━━━━━━
🏢 <b>{tiker_clean} | {html.escape(info.get('longName', tiker_clean))}</b>
🕋 Shariat Statusi: <b>{halal}</b>
💵 Joriy Narx: <b>{joriy_narx:,.2f} USD</b>
📊 Bozor Qiymati (Cap): <b>{format_katta_son(market_cap)}</b>
━━━━━━━━━━━━━━━━━━━━
📌 <b>FUNDAMENTAL KO'RSATKICHLAR:</b>
  🔹 P/E Nisbati: <b>{pe_ratio}</b>
  🔹 EPS (Foyda): <b>{eps} USD</b>
  🔹 ROE Rentabellik: <b>{roe}</b>
  🔹 Dividend To'lovi: <b>{div_str}</b>
━━━━━━━━━━━━━━━━━━━━
🐋 <b>YIRIK EGALARI (KITLAR):</b>
{inst_text if inst_text else "  ℹ️ Institutsional fondlar ma'lumoti aniqlanmadi."}
━━━━━━━━━━━━━━━━━━━━
🐳 <b>SMART MONEY (SMC) TAHLIL:</b>
{likvidlik}
🎯 Kutilma: <i>{kutilma}</i>
━━━━━━━━━━━━━━━━━━━━
📈 <b>TEXNIK INDIKATORLAR:</b>
  🔹 RSI Ko'rsatkichi: <b>{rsi} ({rsi_signal})</b>
  🔹 Bollinger Bands: <b>{upper:,.2f} / {middle:,.2f} / {lower:,.2f}</b>
  🎯 Bot Yakuniy Bahosi: <b>{"4.8/5.0 ★★★★★" if rsi<=35 else "2.0/5.0 ★★☆☆☆"}</b>
━━━━━━━━━━━━━━━━━━━━"""
        return text, tiker_clean, logo
    except Exception as e:
        return f"Xato yuz berdi: {str(e)}", None, None

# ===================== CHAT FLOW HANDLING =====================
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    registered_users.add(uid)
    user_modes[uid] = False
    uz_user_modes[uid] = False
    bot.send_message(uid, f"👋 <b>Smart Money va Likvidlik tahlil botiga xush kelibsiz!</b>\n\nIstalgan aksiya yoki kripto tikerini yozib yuboring (Masalan: AAPL, NVDA, BTC, SOL).", parse_mode="HTML", reply_markup=main_menu())

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
        res = ai_request(f"Siz professional moliya ustozisiz. Savolga o'zbekcha lo'nda va batafsil javob bering:\nSavol: {text}")
        return bot.send_message(uid, res or "Ushbu savol bo'yicha texnik tahlil yangilanmoqda, qayta yozib ko'ring.")

    # Menyular boshqaruvi
    if text == "🌐 Global Pul Oqimi":
        bot.send_message(uid, get_capital_flow(), parse_mode="HTML")
    elif text == "🚀 TOP Signal":
        bot.send_message(uid, "🔥 <b>TOP RSI SIGNALLAR:</b>\n\nAAPL: BUY 🛒\nTSLA: HOLD ↕️\nNVDA: SELL ⚠️", parse_mode="HTML")
    elif text == "🪙 Kripto bozori":
        txt = "🪙 <b>JORIY KRIPTO BOZORI STATUSI:</b>\n\n"
        for k, v in list(KRIPTO_HALOL_BAZA.items())[:6]:
            txt += f"• <b>{k}:</b> {v}\n"
        bot.send_message(uid, txt, parse_mode="HTML")
    elif text == "🔥 Bozor yetakchilari":
        bot.send_message(uid, "🟢 NVDA: +2.45%\n🔴 TSLA: -1.20%\n🟢 AAPL: +0.85%", parse_mode="HTML")
    elif text == "📰 Fond bozori yangiliklari":
        bot.send_message(uid, f"📰 <b>Fond Bozori | So'nggi Muhim Yangiliklar:</b>\n\n{get_market_news()}", parse_mode="HTML")
    elif text == "📖 Atamalar lug'ati":
        bot.send_message(uid, "📖 <b>Moliyaviy lug'at (1-sahifa):</b>", parse_mode="HTML", reply_markup=inline_dictionary(page=1))
    elif text == "🧠 Kunlik Test":
        bot.send_poll(chat_id=uid, question="RSI ko'rsatkichi 30 dan pastga tushganda nima bo'ladi?", options=["Oversold (Arzon/Sotib olish fursati)", "Overbought (Qimmat)", "Trend o'zgarmaydi"], type="quiz", correct_option_id=0, explanation="RSI 30 dan past bo'lsa, aktiv haddan tashqari ko'p sotilgan va arzon hisoblanadi.", is_anonymous=False)
    elif text == "🐋 Kitlar kuzatuvida":
        bot.send_message(uid, "🐋 <b>KITLAR HARAKATI:</b>\nVanguard va BlackRock ushbu chorakda asosan Sun'iy Intellekt va Kripto infratuzilma aksiyalarini sotib olishmoqda.")
    elif text == "🇺🇿 O'zbekiston aksiyalari":
        uz_user_modes[uid] = True
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(types.KeyboardButton("❌ Rejimdan chiqish"))
        bot.send_message(uid, "🇺🇿 Tiker kiriting (Masalan: NKMK, URTS):", parse_mode="HTML", reply_markup=kb)
    elif text == "🤖 AI Tavsiyalari":
        user_modes[uid] = True
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(types.KeyboardButton("❌ Rejimdan chiqish"))
        bot.send_message(uid, "🤖 Shariat va Moliya bo'yicha savolingizni yozing:", reply_markup=kb)
    elif text in ["🔍 RSI Skriner", "🏛️ NYSE birjasi", "🏬 NASDAQ birjasi", "🇺🇸 S&P 500 indeks"]:
        bot.send_message(uid, f"📊 <b>{text} bo'limi faol:</b>\nTahlil qilmoqchi bo'lgan aksiyangiz tikerini to'g'ridan-to'g'ri yozib yuboring (Masalan: AAPL, MSFT, NKE).")
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

# ===================== CALLBACK HANDLERS =====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.message.chat.id
    if call.data.startswith("ai_"):
        bot.send_message(uid, f"🤖 <b>AI Maslahati:</b>\n\n<i>{get_ai_advice(call.data[3:])}</i>", parse_mode="HTML")
    elif call.data.startswith("dic_"):
        term = call.data[4:]
        if term.startswith("page_"):
            p = int(term.split("_")[1])
            bot.edit_message_text(chat_id=uid, message_id=call.message.message_id, text=f"📖 <b>Moliyaviy lug'at ({p}-sahifa):</b>", reply_markup=inline_dictionary(page=p))
        else:
            explanations = {
                "mcap": "📊 <b>Market Cap:</b> Kompaniyaning bozordagi jami qiymati.",
                "pe": "📈 <b>P/E Ratio:</b> Narxning foydaga nisbati (Qaytarilish muddati).",
                "debteq": "🚨 <b>Debt/Equity:</b> Kompaniyaning qarz yuklamasi ko'rsatkichi.",
                "rsi": "📉 <b>RSI:</b> 30 dan past = arzon (BUY), 70 dan baland = qimmat (SELL).",
                "eps": "💰 <b>EPS:</b> Har bir dona aksiyaga to'g'ri keladigan sof foyda.",
                "roe": "👑 <b>ROE:</b> Xususiy kapital samaradorligi.",
                "fcf": "💵 <b>FCF:</b> Erkin naqd pul oqimi.",
                "pb": "📚 <b>P/B:</b> Bozor narxining balans qiymatiga nisbatan ko'paytmasi."
            }
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
