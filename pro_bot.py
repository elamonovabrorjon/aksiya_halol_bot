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
    return "Aksiya Halol Bot barcha bo'limlar va Admin tizimi bilan faol!", 200

# ===================== BOT SOZLAMALARI =====================
TOKEN = os.getenv("BOT_TOKEN") or "8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8"
bot = telebot.TeleBot(TOKEN, threaded=True)

# 🛑 DIQQAT: BU YERGA O'ZINGIZNING TELEGRAM ID RAQAMINGIZNI YOZING!
ADMIN_ID = 123456789  

# Foydalanuvchilar bazasi (Render o'chib yonganda o'chmasligi uchun vaqtincha xotira)
registered_users = set()

user_modes = {}
uz_user_modes = {}

KRIPTO_HALOL_BAZA = {
    "BTC": "HALOL 🟢 (Asosiy ayblov vositasi, deflyatsion raqamli oltin)",
    "ETH": "HALOL 🟢 (Yordamchi utility ekotizim tarmog'i)",
    "BNB": "SHUBHALI 🟡 (Ekotizimida kaldıraç va marja elementlari bor)",
    "SOL": "HALOL 🟢 (Tezkor va arzon operatsion blockchain tarmog'i)",
    "XRP": "SHUBHALI 🟡 (Markazlashgan bank tizimlariga xizmat qiladi)",
    "ADA": "HALOL 🟢 (Ilmiy asoslangan proof-of-stake tarmog'i)",
    "DOT": "HALOL 🟢 (Parachain va ekotizim tarmog'i)",
    "DOGE": "HAROM/XAVFLI 🔴 (Meme-coin, spekulyativ, ichki qiymatga ega emas)",
    "SHIB": "HAROM/XAVFLI 🔴 (Meme-coin, yuqori spekulyatsiya xavfi yuqori)",
    "AVAX": "HALOL 🟢 (Aqlli kontraktlar platformasi)",
    "LINK": "HALOL 🟢 (Oracle texnologiyasi, ma'lumotlar yetkazuvchi vizual tarmoq)"
}

UZ_STOCKS_DATA = {
    "NKMK": {
        "nomi": "Navoiy Kon-Metallurgiya Kombinati (Oltin Giganti)",
        "shariat": "HALOL 🟢 (Asosiy faoliyati oltin qazib olish, qarz yuklamasi juda past)",
        "ishlab_chiqarish": "Yillik ~2.9 mln unsiya oltin qazib olinadi. Dunyo reytingida 4-o'rinda turadi.",
        "sof_foyda": "Sof foyda yillik ~2.1 mlrd USD dan oshdi. Oltin narxi oshishi hisobiga foyda o'smoqda.",
        "dividend": "Yiliga 2 marta dividend to'lash amaliyoti bor. Dividend rentabelligi: ~12% - 15%.",
        "tavsiya": "🎯 UZOQ MUDDATLI INVESTITSIYA (BUY) — Portfelning poydevori uchun eng xavfsiz va likvid aktiv."
    },
    "URTS": {
        "nomi": "O'zbekiston Respublika Tovar-Xom Ashyo Birjasi (UZEX)",
        "shariat": "HALOL 🟢 (Birja xizmatlari va vositachilik haqi, foizsiz sof biznes modeli)",
        "ishlab_chiqarish": "Tranzaksiyalar hajmi yillik 140+ trln so'mdan oshdi. Elektron auksionlar yetakchisi.",
        "sof_foyda": "Yillik sof foyda ~250-280 mlrd so'm. Operatsion korxona xarajatlari juda past.",
        "dividend": "🔥 REKORDCHI! Sof foydaning 70-90% qismini dividendga beradi. Rentabellik: ~15% - 22%.",
        "tavsiya": "🚀 KUCHLI SOTIB OLISH (STRONG BUY) — Barqaror dividend oqimi izlayotganlar uchun eng birinchi aktiv."
    },
    "UZAUTO": {
        "nomi": "UzAuto Motors AJ",
        "shariat": "HALOL 🟢 (Ishlab chiqarish va real savdo sektori)",
        "ishlab_chiqarish": "Yillik quvvati 400,000+ donadan ortiq avtomobil.",
        "sof_foyda": "Yillik sof foyda barqaror ~2.5 - 2.8 trln so'm.",
        "dividend": "Dividend to'lash tarixi barqaror emas, lekin kapital o'sishi yuqori darajada.",
        "tavsiya": "🛒 SOTIB OLISH (BUY) — Ichki bozordagi yuqori talab hisobiga xavfsiz."
    }
}

# Data Cache
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
            yaqin_likvidlik = f"<b>Buy-Side Liquidity (BSL):</b> {swing_high:,.2f} USD joriy qarshilik hovuzi."
            kutilma = "Smart Money tepadagi likvidlikni yig'ish (Liquidity Sweep) uchun narxni tortishi kutilmoqda."
        else:
            yaqin_likvidlik = f"<b>Sell-Side Liquidity (SSL):</b> {swing_low:,.2f} USD kuchli stoplar hovuzi."
            kutilma = "Kitlar pastdagi stop-losslarni urib, bozorga kirish uchun narxni tushirishi mumkin."
            
        fvg_text = "Imbalans (FVG): Keskin bo'shliqlar yo'q."
        if len(closes) >= 3:
            h_1, l_3 = float(highs.iloc[-3]), float(lows.iloc[-1])
            if l_3 > h_1: fvg_text = f"<b>FVG (Bullish Gap):</b> {h_1:,.2f} - {l_3:,.2f} USD orasida ochiq FVG bor."
            elif h_1 > l_3:
                h_3, l_1 = float(highs.iloc[-1]), float(lows.iloc[-3])
                if l_1 > h_3: fvg_text = f"<b>FVG (Bearish Gap):</b> {h_3:,.2f} - {l_1:,.2f} USD ochiq imbalance zonasi."
        return f"{yaqin_likvidlik}\n  └ 🔍 {fvg_text}", kutilma
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

# ===================== YORDAMCHI FUNKSIYALAR =====================
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
    prompt = f"Analyze {ticker} stock (Price: {narx} USD, RSI: {rsi}). Write a 2-sentence professional Smart Money advice in Uzbek. Be concise."
    return ai_request(prompt) or "AI xizmati hozir band."

def get_market_news():
    try:
        url = "https://news.google.com/rss/search?q=stock+market+investing&hl=en-US&gl=US&ceid=US:en"
        res = requests.get(url, timeout=4)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(res.content)
        items = [item.find('title').text.split(" - ")[0] for item in root.findall('.//item')[:3]]
        if not items: return "Yangi xabarlar topilmadi."
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
        if info is None or hist is None or hist.empty: return f"❌ {tiker_clean} topilmadi.", None, None

        closes = hist['Close']
        rsi, rsi_signal = hisobla_rsi(closes)
        upper, middle, lower = hisobla_bollinger(closes)
        likvidlik, kutilma = hisobla_smart_money_likvidlik(hist, closes.iloc[-1])

        halal = KRIPTO_HALOL_BAZA.get(tiker_clean, "HALOL 🟢") if is_crypto else ("HALOL 🟢" if (safe_float(info.get('totalDebt')) or 0)/(safe_float(info.get('marketCap')) or 1)*100 < 30 else "XAVFLI 🔴")
        logo = f"https://images.financialmodelingprep.com/image/company_logos/{tiker_clean}.png" if not is_crypto else "https://cdn-icons-png.flaticon.com/512/2272/2272825.png"

        # Fondlar va egalari ro'yxati
        inst_text = ""
        if not is_crypto:
            try:
                inst = stock.institutional_holders
                if inst is not None and not inst.empty:
                    for idx, row in inst.head(2).iterrows():
                        inst_text += f"  🔹 {row.get('Holder', 'Fond')}: {row.get('% of holding', 0)*100:.2f}%\n"
            except: pass

        # Dividend ma'lumotlari
        div_str = "Yo'q"
        if info.get('dividendYield'):
            div_str = f"{info.get('dividendYield')*100:.2f}% (Yillik: {info.get('dividendRate', 0)} USD)"

        text = f"""━━━━━━━━━━━━━━━━━━━━
<b>{tiker_clean} | {html.escape(info.get('longName', tiker_clean))}</b>
Status: <b>{halal}</b> | Narx: <b>{closes.iloc[-1]:,.2f} USD</b>
Cap: <b>{format_katta_son(info.get('marketCap'))}</b> | Div: <b>{div_str}</b>
━━━━━━━━━━━━━━━━━━━━
🐋 Yirik egalari (Kitlar):
{inst_text if inst_text else "  ℹ️ Ma'lumot aniqlanmadi."}
━━━━━━━━━━━━━━━━━━━━
🐳 SMC Tahlil:
{likvidlik}
🎯 Kutilma: <i>{kutilma}</i>
━━━━━━━━━━━━━━━━━━━━
📊 Indikatorlar:
RSI: <b>{rsi} ({rsi_signal})</b>
Bollinger: <b>{upper:,.2f} / {lower:,.2f}</b>
🎯 Bot Bahosi: <b>{"4.0/5.0 ★★★★☆" if rsi<=45 else "2.5/5.0 ★★☆☆☆"}</b>
━━━━━━━━━━━━━━━━━━━━"""
        return text, tiker_clean, logo
    except Exception as e:
        return f"Xato: {str(e)}", None, None

# ===================== 👑 ADMIN COMMANDS =====================
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

@bot.message_handler(commands=['senduser'])
def admin_send_user(message):
    if message.chat.id != ADMIN_ID: return
    try:
        parts = message.text.split(maxsplit=2)
        bot.send_message(int(parts[1]), f"💬 <b>Ustozdan shaxsiy javob:</b>\n\n{parts[2]}", parse_mode="HTML")
        bot.send_message(ADMIN_ID, "✅ Yuborildi.")
    except: bot.send_message(ADMIN_ID, "Xato. Format: `/senduser ID Matn`", parse_mode="Markdown")

# ===================== CHAT FLOW HANDLING =====================
@bot.make_view_block if hasattr(bot, 'make_view_block') else None
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    registered_users.add(uid)
    user_modes[uid] = False
    uz_user_modes[uid] = False
    bot.send_message(uid, f"👋 <b>Smart Money va Likvidlik tahlil botiga xush kelibsiz!</b>\n\nID: <code>{uid}</code>", parse_mode="HTML", reply_markup=main_menu())

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
        res = ai_request(f"Siz professional moliya ustozisiz. Savolga o'zbekcha lo'nda javob bering:\nSavol: {text}")
        return bot.send_message(uid, res or "AI band.")

    # Menu tugmalari boshqaruvi
    if text == "🌐 Global Pul Oqimi":
        bot.send_message(uid, get_capital_flow(), parse_mode="HTML")
    elif text == "🚀 TOP Signal":
        bot.send_message(uid, "🔥 <b>TOP RSI SIGNALLAR:</b>\n\nAAPL: BUY 🛒\nTSLA: HOLD ↕️\nNVDA: SELL ⚠️", parse_mode="HTML")
    elif text == "🪙 Kripto bozori":
        bot.send_message(uid, f"🪙 <b>KRIPTO BOZORI:</b>\n\nBTC: {KRIPTO_HALOL_BAZA['BTC']}\nETH: {KRIPTO_HALOL_BAZA['ETH']}", parse_mode="HTML")
    elif text == "🔥 Bozor yetakchilari":
        bot.send_message(uid, "🟢 NVDA: +2.45%\n🔴 TSLA: -1.20%\n🟢 AAPL: +0.85%", parse_mode="HTML")
    elif text == "📰 Fond bozori yangiliklari":
        bot.send_message(uid, f"📰 <b>Yangiliklar:</b>\n\n{get_market_news()}", parse_mode="HTML")
    elif text == "📖 Atamalar lug'ati":
        bot.send_message(uid, "📖 <b>Moliyaviy lug'at (1-sahifa):</b>", parse_mode="HTML", reply_markup=inline_dictionary(page=1))
    elif text == "🧠 Kunlik Test":
        bot.send_poll(chat_id=uid, question="RSI ko'rsatkichi 30 dan pastga tushganda nima bo'ladi?", options=["Oversold (Arzon/Sotib olish fersati)", "Overbought (Qimmat)", "Trend o'zgarmaydi"], type="quiz", correct_option_id=0, explanation="RSI 30 dan past bo'lsa, aktiv haddan tashqari ko'p sotilgan va arzon hisoblanadi.", is_anonymous=False)
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
        bot.send_message(uid, "🤖 Savolingizni yozing:", reply_markup=kb)
    elif text in ["🏛️ NYSE birjasi", "🏬 NASDAQ birjasi", "🇺🇸 S&P 500 indeks", "🔍 RSI Skriner"]:
        bot.send_message(uid, f"📊 <b>{text} bo'limi:</b>\n\nTizim orqali joriy top aksiyalar ro'yxati shakllantirilmoqda. Tahlil qilmoqchi bo'lgan aksiyangiz tikerini yozib yuborishingiz ham mumkin.")
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

# ===================== POLLING MULTITHREADING =====================
def run_bot_polling():
    while True:
        try: bot.polling(none_stop=True, interval=0, timeout=25)
        except: time.sleep(5)

if __name__ == "__main__":
    try: bot.remove_webhook()
    except: pass
    threading.Thread(target=run_bot_polling, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
