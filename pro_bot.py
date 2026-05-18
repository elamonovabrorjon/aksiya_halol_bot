import os
import telebot
from telebot import types
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import threading
from flask import Flask, request
from bs4 import BeautifulSoup
import time
import html
from datetime import datetime
import math
import json
import random

# ===================== VEB-SERVER =====================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot barqaror rejimda ishlamoqda!", 200

# ===================== SOZLAMALAR =====================
TOKEN = os.getenv("BOT_TOKEN") or "8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8"
RENDER_URL = 'https://aksiya-halol-bot3.onrender.com'  # O'zingizning Render URL manzilingiz
ADMIN_ID = 5716183424

bot = telebot.TeleBot(TOKEN)

user_modes = {}
uz_user_modes = {}

# ===================== FOYDALANUVCHILAR BAZASI =====================
DB_FILE = "users.txt"

def save_user(user_id):
    try:
        if not os.path.exists(DB_FILE):
            with open(DB_FILE, "w") as f: pass
        with open(DB_FILE, "r") as f:
            users = f.read().splitlines()
        if str(user_id) not in users:
            with open(DB_FILE, "a") as f:
                f.write(f"{user_id}\n")
    except:
        pass

def get_users_count():
    try:
        if not os.path.exists(DB_FILE): return 0
        with open(DB_FILE, "r") as f:
            return len(f.read().splitlines())
    except:
        return 0

# ===================== STOCK DATA CACHE =====================
_cache = {}
_cache_time = {}
CACHE_TTL = 300  # 5 daqiqa

def get_stock_data(ticker: str):
    now = time.time()
    if ticker in _cache and now - _cache_time.get(ticker, 0) < CACHE_TTL:
        return _cache[ticker]
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="3mo")
        result = (stock, info, hist)
        _cache[ticker] = result
        _cache_time[ticker] = now
        return result
    except:
        return None, None, None

# ===================== MATHEMATICAL INDICATORS =====================
def hisobla_rsi(closes, period=14):
    try:
        if closes is None or len(closes) < period:
            return 50.0, "HOLD ↕️"
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
        avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
        rs = avg_gain / avg_loss.where(avg_loss != 0, 1)
        rsi = 100 - (100 / (1 + rs))
        current_rsi = round(rsi.iloc[-1], 2)
        if current_rsi >= 70: return current_rsi, "SELL 📉"
        elif current_rsi <= 30: return current_rsi, "BUY 📈"
        else: return current_rsi, "HOLD ↕️"
    except:
        return 50.0, "HOLD ↕️"

def hisobla_bollinger(closes, period=20):
    try:
        if closes is None or len(closes) < period:
            return 0.0, 0.0, 0.0
        ma = closes.rolling(window=period).mean()
        std = closes.rolling(window=period).std()
        upper = ma + (std * 2)
        lower = ma - (std * 2)
        return round(upper.iloc[-1], 2), round(ma.iloc[-1], 2), round(lower.iloc[-1], 2)
    except:
        return 0.0, 0.0, 0.0

# ===================== AI XIZMATI (MISTRAL MODEL) =====================
def ai_request(prompt: str, timeout: int = 5):
    try:
        response = requests.post(
            "https://text.pollinations.ai/",
            json={
                "messages": [{"role": "user", "content": prompt}],
                "model": "mistral-large"
            },
            timeout=timeout
        )
        if response.status_code == 200:
            return response.text.strip()
    except:
        pass
    return None

def get_ai_advice(ticker):
    try:
        stock, info, hist = get_stock_data(ticker)
        if info is None: return "🤖 AI xizmati hozir band. Keyinroq qayta urinib ko'ring."
        
        narx = safe_float(info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0) or 0
        pe_val = safe_float(info.get('trailingPE'))
        pe_str = f"{pe_val:.2f}" if pe_val else "—"
        market_cap = safe_float(info.get('marketCap')) or 0
        qarz = safe_float(info.get('totalDebt')) or 0
        debt_ratio = (qarz / market_cap * 100) if market_cap else 0
        halal_status = "HALOL 🟢" if debt_ratio < 30 else "XAVFLI/HAROM 🔴"
        
        closes = hist['Close'] if hist is not None else None
        rsi, _ = hisobla_rsi(closes)
        upper, middle, lower = hisobla_bollinger(closes)

        prompt = (
            f"Siz professional moliya tahlilchisiz. {ticker} aksiyasi uchun o'zbek tilida "
            f"2-3 ta gapdan iborat ixcham tavsiya bering. "
            f"Narx: {narx} USD, P/E: {pe_str}, RSI: {rsi}, Bollinger Upper: {upper}, Lower: {lower}, Shariat: {halal_status}. "
            f"Xolis fikr bering."
        )
        result = ai_request(prompt, timeout=6)
        return result if result else "🤖 AI xizmati hozir band. Keyinroq qayta urinib ko'ring."
    except:
        return "🤖 AI xizmati hozir band. Keyinroq qayta urinib ko'ring."

# ===================== UZBEKISTAN STOCK (UZSE PARSING & AI) =====================
def uzbek_stock_price(symbol):
    try:
        url = "https://uzse.uz/quotes"
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) > 1:
                name = cols[0].text.strip().upper()
                price = cols[1].text.strip().replace(" ", "").replace(",", ".")
                if symbol == name:
                    return float(price)
        return None
    except:
        return None

def uzbekistan_stock_analysis(text_input: str):
    symbol = text_input.strip().upper()
    uz_price = uzbek_stock_price(symbol)
    
    price_str = f"<b>{uz_price:,.2f} UZS</b>" if uz_price else "🔄 Saytdan joriy narx yuklanmadi (tahlil fundamental)"
    
    prompt = (
        f"Siz Toshkent Respublika Fond Birjasi (UZSE) bo'yicha professional moliya expertisiz.\n"
        f"Foydalanuvchi: '{symbol}' kompaniyasini so'radi. Narxi: {uz_price} UZS.\n\n"
        f"Islomiy moliya qoidalari bo'yicha qisqa tahlil bering:\n"
        f"🇺🇿 Kompaniya nomi: [nomi]\n"
        f"🟢 Shariat Statusi: [Halol/Xarom]\n"
        f"📊 Fundamental holati: [qisqa baho]\n"
        f"🎯 YAKUNIY QAROR: [BUY yoki AVOID]\n\n"
        f"Faqat o'zbek tilida, pul birligi UZS bo'lsin."
    )
    res = ai_request(prompt, timeout=8)
    if res:
        return f"━━━━━━━━━━━━━━━━━━━━\n🇺🇿 <b>TOSHKENT RFB TAHLILI ({symbol})</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 Birja narxi: {price_str}\n\n{res}\n━━━━━━━━━━━━━━━━━━━━"
    return f"❌ Tahlilda xatolik. Birja narxi: {price_str}"

# ===================== YANGILIKLAR =====================
def get_market_news():
    try:
        url = "https://news.google.com/rss/search?q=stock+market+investing+news&hl=en-US&gl=US&ceid=US:en"
        res = requests.get(url, timeout=5)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(res.content)
        news_list = []
        for item in root.findall('.//item')[:4]:
            title = item.find('title').text
            if " - " in title:
                title = title.split(" - ")[0]
            news_list.append(title)
        if not news_list:
            return "❌ Hozircha yangiliklar topilmadi."
        combined = "\n\n".join([f"- {t}" for t in news_list])
        prompt = f"Quyidagi yangiliklar sarlavhalarini o'zbek tiliga lo'nda tarjima qiling:\n\n{combined}"
        uz_news = ai_request(prompt, timeout=6)
        return uz_news if uz_news else combined + "\n\n⚠️ <i>(AI bandligi sababli vaqtincha inglizcha tilda ko'rsatildi)</i>"
    except:
        return "🌐 Yangiliklar yuklanmadi. Birozdan so'ng qayta urinib ko'ring."

# ===================== KRIPTO BOZORI =====================
def get_crypto_market_summary():
    cryptos = {"BTC-USD": "Bitcoin (BTC)", "ETH-USD": "Ethereum (ETH)", "BNB-USD": "BNB", "SOL-USD": "Solana (SOL)", "XRP-USD": "Ripple (XRP)"}
    matn = "━━━━━━━━━━━━━━━━━━━━\n🪙 <b>JORIY KRIPTO BOZORI</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for ticker, name in cryptos.items():
        try:
            coin = yf.Ticker(ticker)
            hist = coin.history(period="2d")
            if len(hist) >= 2:
                narx = hist['Close'].iloc[-1]
                old_narx = hist['Close'].iloc[-2]
                ozgarish = ((narx - old_narx) / old_narx) * 100
                belgi = "📈" if ozgarish >= 0 else "📉"
                matn += f"{belgi} <b>{name}</b>\n  └ {narx:,.2f} USD | {ozgarish:+.2f}%\n\n"
        except:
            matn += f"❌ <b>{name}</b> yuklanmadi.\n\n"
    return matn + "━━━━━━━━━━━━━━━━━━━━"

# ===================== BOZOR YETAKCHILARI =====================
def get_market_movers():
    watch_list = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "AMD", "NFLX", "JPM"]
    gainers, losers = [], []
    for tiker in watch_list:
        try:
            hist = yf.Ticker(tiker).history(period="2d")
            if len(hist) >= 2:
                yopilish = hist['Close'].iloc[-1]
                ochilish = hist['Close'].iloc[-2]
                change = ((yopilish - ochilish) / ochilish) * 100
                item = {"ticker": tiker, "price": yopilish, "change": change}
                if change >= 0: gainers.append(item)
                else: losers.append(item)
        except: pass
    gainers = sorted(gainers, key=lambda x: x['change'], reverse=True)[:3]
    losers = sorted(losers, key=lambda x: x['change'])[:3]

    matn = "━━━━━━━━━━━━━━━━━━━━\n🔥 <b>BUGUNGI BOZOR YETAKCHILARI</b>\n━━━━━━━━━━━━━━━━━━━━\n 🚀 <b>Eng ko'p o'sganlar:</b>\n"
    for item in gainers: matn += f"  🟢 <b>{item['ticker']}</b>: {item['price']:.2f} USD ({item['change']:+.2f}%)\n"
    matn += "\n📉 <b>Eng ko'p tushganlar:</b>\n"
    for item in losers: matn += f"  🔴 <b>{item['ticker']}</b>: {item['price']:.2f} USD ({item['change']:+.2f}%)\n"
    return matn + "━━━━━━━━━━━━━━━━━━━━"

# ===================== FORMATLASH FUNKSIYALARI =====================
def safe_float(val):
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f): return None
        return f
    except: return None

def format_katta_son(son):
    val = safe_float(son)
    if val is None: return "—"
    minus = "-" if val < 0 else ""
    val = abs(val)
    if val >= 1e12: return f"{minus}{val/1e12:.2f} T"
    if val >= 1e9:  return f"{minus}{val/1e9:.2f} B"
    if val >= 1e6:  return f"{minus}{val/1e6:.2f} M"
    return f"{minus}{val:,.0f}"

def check_valid_pct(val):
    f = safe_float(val)
    if f is None: return "—"
    return f"{f:+.2f}%"

# ===================== GLOBAL AKSIYA TAHLILI =====================
def aksiya_tahlil(tiker: str):
    try:
        tiker_clean = tiker.strip().upper()
        if tiker_clean in ["BTC", "ETH", "BNB", "SOL", "XRP"]:
            tiker_clean += "-USD"

        # Agar o'zbek aksiyasi bo'lsa jonli narx tekshiriladi
        uz_price = uzbek_stock_price(tiker_clean)
        if uz_price:
            return uzbekistan_stock_analysis(tiker_clean), None, None

        stock, info, hist = get_stock_data(tiker_clean)
        if info is None or hist is None or hist.empty:
            return f"❌ <b>{tiker_clean}</b> bo'yicha global birjada ma'lumot topilmadi.", None, None

        long_name = info.get('longName') or info.get('shortName') or tiker_clean
        sector = info.get('sector', 'Noma\'lum')
        narx = safe_float(info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0) or 0
        logo_url = f"https://images.financialmodelingprep.com/image/company_logos/{tiker_clean}.png"

        desc_en = info.get('longBusinessSummary', '')
        summary_uz = "— Ma'lumot yo'q —"
        if desc_en:
            prompt_desc = f"Quyidagi ma'lumotni o'zbek tiliga 2 gapda tarjima qiling:\n\n{desc_en[:400]}"
            summary_uz = ai_request(prompt_desc, timeout=5) or "— Tarjima yuklanmadi —"

        high_52 = safe_float(info.get('fiftyTwoWeekHigh')) or narx
        low_52 = safe_float(info.get('fiftyTwoWeekLow')) or narx
        market_cap = safe_float(info.get('marketCap')) or 0
        cap_str = format_katta_son(market_cap)
        div_yield = safe_float(info.get('dividendYield'))
        div_str = f"{div_yield * 100:.2f}%" if div_yield else "0.0%"

        qarz = safe_float(info.get('totalDebt')) or 0
        sof_foyda = safe_float(info.get('netIncomeToCommon')) or safe_float(info.get('netIncome')) or 0
        sof_foyda_str = format_katta_son(sof_foyda) + " USD" if sof_foyda else "—"

        inst_percent = safe_float(info.get('heldPercentInstitutions', 0)) * 100 or 0
        insider_percent = safe_float(info.get('heldPercentInsiders', 0)) * 100 or 0
        retail_percent = max(0, 100 - inst_percent - insider_percent)

        pe_val = safe_float(info.get('trailingPE'))
        pb_val = safe_float(info.get('priceToBook'))
        eps_val = safe_float(info.get('trailingEps'))
        pe_str = f"{pe_val:.2f}" if pe_val else "—"
        pb_str = f"{pb_val:.2f}" if pb_val else "—"
        eps_str = f"{eps_val:.2f}" if eps_val else "—"

        closes = hist['Close']
        rsi, rsi_signal = hisobla_rsi(closes)
        upper, middle, lower = hisobla_bollinger(closes)

        # Signal Strategiyasi (RSI + Bollinger Bands)
        signal = "HOLD ↕️"
        if rsi <= 30 and narx < lower: signal = "STRONG BUY 🚀"
        elif rsi <= 40: signal = "BUY 🛒"
        elif rsi >= 70 and narx > upper: signal = "STRONG SELL 📉"
        elif rsi >= 60: signal = "SELL ⚠️"

        debt_ratio = (qarz / market_cap * 100) if market_cap else 0
        halal_status = "KRIPTO 🪙" if "-USD" in tiker_clean else ("HALOL 🟢" if debt_ratio < 30 else "HAROM 🔴")

        javob = f"""━━━━━━━━━━━━━━━━━━━━
<b>{tiker_clean} | {html.escape(long_name)}</b>
Sektor: <b>{html.escape(sector)}</b> | Status: <b>{halal_status}</b>
━━━━━━━━━━━━━━━━━━━━
ℹ️ <b>Kompaniya haqida:</b>
<i>{html.escape(summary_uz)}</i>
━━━━━━━━━━━━━━━━━━━━
💰 Narx: <b>{narx:,.2f} USD</b>
52W M/M: <b>{high_52:,.2f} / {low_52:,.2f}</b>
Cap: <b>{cap_str}</b> | Div: <b>{div_str}</b> | Foyda: <b>{sof_foyda_str}</b>
━━━━━━━━━━━━━━━━━━━━
🐋 <b>Egalik tarkibi:</b>
  └ 🐳 Fondlar: <b>{inst_percent:.1f}%</b> | Chakana: <b>{retail_percent:.1f}%</b>
━━━━━━━━━━━━━━━━━━━━
<b>Fundamental:</b>
P/E: <b>{pe_str}</b> | P/B: <b>{pb_str}</b> | EPS: <b>{eps_str}</b>
━━━━━━━━━━━━━━━━━━━━
<b>Texnik Ko'rsatkichlar:</b>
📉 RSI (14): <b>{rsi}</b> → <b>{rsi_signal}</b>
📊 Bollinger Upper: <b>{upper:,.2f}</b>
📊 Bollinger Middle: <b>{middle:,.2f}</b>
📊 Bollinger Lower: <b>{lower:,.2f}</b>

🎯 <b>YAKUNIY SIGNAL: {signal}</b>"""
        return javob, tiker_clean, logo_url
    except Exception as e:
        return f"❌ {tiker.upper()} tahlilida xatolik yuz berdi.", None, None

# ===================== KUNLIK TOP SIGNAL =====================
def top_signal():
    watch = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN"]
    text = "🔥 <b>TOP SIGNAL (RSI + BOLLINGER)</b>\n\n"
    for s in watch:
        try:
            stock, info, hist = get_stock_data(s)
            closes = hist['Close']
            narx = closes.iloc[-1]
            rsi, _ = hisobla_rsi(closes)
            upper, _, lower = hisobla_bollinger(closes)
            
            if rsi <= 30 and narx < lower: sig = "🚀 STRONG BUY"
            elif rsi <= 40: sig = "🛒 BUY"
            elif rsi >= 70 and narx > upper: sig = "📉 STRONG SELL"
            elif rsi >= 60: sig = "⚠️ SELL"
            else: sig = "↕️ HOLD"
            
            text += f"<b>{s}</b>: {narx:,.2f}$ → <b>{sig}</b> (RSI: {rsi})\n"
        except: pass
    return text

# ===================== LUG'AT JAVOBLARI =====================
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

# ===================== MENYULAR =====================
def main_menu():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(types.KeyboardButton("🟢 Halol aksiyalar"), types.KeyboardButton("🧠 Kunlik Test"),
           types.KeyboardButton("🚀 TOP Signal"), types.KeyboardButton("🏛️ NYSE birjasi"),
           types.KeyboardButton("💻 NASDAQ birjasi"), types.KeyboardButton("🇺🇸 S&P 500 indeks"),
           types.KeyboardButton("🤖 AI Tavsiyalari"), types.KeyboardButton("🇺🇿 O'zbekiston aksiyalari"),
           types.KeyboardButton("📰 Fond bozori yangiliklari"), types.KeyboardButton("🪙 Kripto bozori"),
           types.KeyboardButton("🔥 Bozor yetakchilari"), types.KeyboardButton("🐋 Kitlar kuzatuvida"),
           types.KeyboardButton("📖 Atamalar lug'ati"))
    return kb

def ai_exit_menu():
    kb = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    kb.add(types.KeyboardButton("❌ Rejimdan chiqish"))
    return kb

def inline_action(tiker):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("🤖 AI Maslahati", callback_data=f"ai_{tiker}"),
           types.InlineKeyboardButton("🔗 TradingView", url=f"https://www.tradingview.com/symbols/{tiker}/"))
    return kb

def inline_aksiyalar(tikerlar):
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.add(*[types.InlineKeyboardButton(text=t, callback_data=f"anz_{t}") for t in tikerlar])
    return kb

# ===================== HANDLERLAR =====================
@bot.message_handler(commands=['start'])
def start(message):
    user_modes[message.chat.id] = False
    uz_user_modes[message.chat.id] = False
    save_user(message.chat.id)
    bot.send_message(message.chat.id, "👋 <b>Aksiyalar va Kripto tahlil botiga xush kelibsiz!</b>\nTiker yozing yoki menyudan tanlang:", parse_mode="HTML", reply_markup=main_menu())

@bot.message_handler(commands=['stat'])
def show_stats(message):
    if message.chat.id == ADMIN_ID:
        bot.send_message(message.chat.id, f"📊 <b>Statistika:</b>\n\nFoydalanuvchilar: <b>{get_users_count()} ta</b>", parse_mode="HTML")

# ===================== XABARLAR FILTRATSIYASI =====================
@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    save_user(message.chat.id)
    text = message.text.strip()
    uid = message.chat.id

    if text in ["❌ Rejimdan chiqish", "chiqish"]:
        user_modes[uid] = False
        uz_user_modes[uid] = False
        bot.send_message(uid, "Asosiy menyuga qaytdingiz.", reply_markup=main_menu())
        return

    if uz_user_modes.get(uid, False):
        bot.send_chat_action(uid, 'typing')
        bot.send_message(uid, uzbekistan_stock_analysis(text), parse_mode="HTML", reply_markup=ai_exit_menu())
        return

    if user_modes.get(uid, False):
        bot.send_chat_action(uid, 'typing')
        prompt = f"Siz professional moliyaviy mentor va har qanday sohada yordam beradigan ChatGPT muqobilisiz. O'zbek tilida lo'nda javob bering:\nSavol: {text}"
        res = ai_request(prompt, timeout=12)
        bot.send_message(uid, res or "🤖 Tizim band. Qayta urinib ko'ring.", reply_markup=ai_exit_menu())
        return

    if text == "🚀 TOP Signal":
        bot.send_message(uid, top_signal(), parse_mode="HTML")

    elif text == "🟢 Halol aksiyalar":
        halal_list = ["AAPL", "MSFT", "NVDA", "GOOGL", "TSLA"]
        bot.send_message(uid, "🟢 <b>TOP HALOL aksiyalar (RSI + Bollinger) tahlil qilinmoqda...</b>", parse_mode="HTML")
        for ticker in halal_list:
            bot.send_chat_action(uid, 'typing')
            javob, tiker_clean, logo_url = aksiya_tahlil(ticker)
            if tiker_clean:
                try: bot.send_photo(uid, logo_url, caption=javob, parse_mode="HTML", reply_markup=inline_action(tiker_clean))
                except: bot.send_message(uid, javob, parse_mode="HTML", reply_markup=inline_action(tiker_clean))
            time.sleep(0.5)

    # 🧠 INTERAKTIV KUNLIK TEST (QUIZ) FUNKSIYASI
    elif text == "🧠 Kunlik Test":
        bot.send_chat_action(uid, 'typing')
        quiz_prompt = (
            "Siz moliya va trading ustozisiz. Aksiya bozori, texnik tahlil (RSI, Bollinger Bands, trend, Fib) "
            "yoki fundamental tahlil mavzusida o'zbek tilida 1 ta qiziqarli professional savol tuzing.\n"
            "Menga ma'lumotni faqat JSON formatida qaytaring, boshqa gap qo'shmang:\n"
            "{\n"
            "  \"question\": \"Savol matni?\",\n"
            "  \"options\": [\"To'g'ri javob\", \"Xato 1\", \"Xato 2\", \"Xato 3\"],\n"
            "  \"explanation\": \"Savolning qisqa ilmiy izohi (max 200 belgi).\"\n"
            "}\n"
            "To'g'ri javob doim 0-indeksda (birinchi variantda) joylashsin."
        )
        raw_quiz = ai_request(quiz_prompt, timeout=10)
        try:
            clean_json = raw_quiz.strip().replace("```json", "").replace("```", "").strip()
            quiz_data = json.loads(clean_json)
            shuffled_options = list(quiz_data["options"])
            random.shuffle(shuffled_options)
            correct_index = shuffled_options.index(quiz_data["options"][0])
            
            bot.send_poll(chat_id=uid, question=quiz_data["question"], options=shuffled_options, type="quiz",
                          correct_option_id=correct_index, explanation=quiz_data["explanation"], is_anonymous=False)
        except:
            bot.send_message(uid, "❌ Yangi savol yuklashda texnik uzilish. Qayta bosing.")

    elif text == "🐋 Kitlar kuzatuvida":
        bot.send_chat_action(uid, 'typing')
        res = ai_request("Vanguard, BlackRock va Buffett hozirgi chorakda qaysi sektorlarni sotib olayotgani haqida qisqa o'zbekcha tahlil bering.", timeout=8)
        bot.send_message(uid, f"━━━━━━━━━━━━━━━━━━━━\n🐋 <b>KITLAR KUZATUVIDA</b>\n━━━━━━━━━━━━━━━━━━━━\n{res}\n━━━━━━━━━━━━━━━━━━━━", parse_mode="HTML")

    elif "NYSE" in text: bot.send_message(uid, "🏛️ <b>NYSE top kompaniyalari:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["WMT", "KO", "XOM", "JPM", "NKE"]))
    elif "NASDAQ" in text: bot.send_message(uid, "💻 <b>NASDAQ top kompaniyalari:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["AAPL", "MSFT", "NVDA", "AMZN", "TSLA"]))
    elif "S&P 500" in text: bot.send_message(uid, "🇺🇸 <b>S&P 500 aksiyalari:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["SPY", "VOO", "AAPL", "MSFT", "TSLA"]))
    elif text == "📰 Fond bozori yangiliklari": bot.send_chat_action(uid, 'typing'); bot.send_message(uid, f"📰 <b>So'nggi Yangiliklar:</b>\n\n{get_market_news()}", parse_mode="HTML")
    elif text == "🪙 Kripto bozori": bot.send_chat_action(uid, 'typing'); bot.send_message(uid, get_crypto_market_summary(), parse_mode="HTML")
    elif text == "🔥 Bozor yetakchilari": bot.send_chat_action(uid, 'typing'); bot.send_message(uid, get_market_movers(), parse_mode="HTML")
    elif text == "📖 Atamalar lug'ati": bot.send_message(uid, "📖 <b>Moliyaviy tahlil lug'ati (1-sahifa):</b>", parse_mode="HTML", reply_markup=inline_dictionary(page=1))
    
    elif text == "🇺🇿 O'zbekiston aksiyalari":
        uz_user_modes[uid] = True; user_modes[uid] = False
        bot.send_message(uid, "🇺🇿 <b>Toshkent RFB (UZSE) bo'limi</b>\nKompaniya tikerini kiriting (Masalan: NKMK, SQB, UZAUTO):", parse_mode="HTML", reply_markup=ai_exit_menu())

    elif text == "🤖 AI Tavsiyalari":
        user_modes[uid] = True; uz_user_modes[uid] = False
        bot.send_message(uid, "🤖 <b>Umumiy AI Mentor Yoqildi!</b>\nMenga xohlagan savolingizni (Trading, Moliya, Tarix va h.k.) yozishingiz mumkin:", parse_mode="HTML", reply_markup=ai_exit_menu())

    else:
        bot.send_chat_action(uid, 'typing')
        javob, tiker, logo_url = aksiya_tahlil(text)
        if tiker:
            try: bot.send_photo(uid, logo_url, caption=javob, parse_mode="HTML", reply_markup=inline_action(tiker))
            except: bot.send_message(uid, javob, parse_mode="HTML", reply_markup=inline_action(tiker))
        else:
            bot.send_message(uid, uzbekistan_stock_analysis(text), parse_mode="HTML")

# ===================== CALLBACK CONTROL =====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.message.chat.id
    if call.data.startswith("anz_"):
        ticker = call.data.split("_")[1]
        bot.send_chat_action(uid, 'typing')
        javob, tiker_clean, logo_url = aksiya_tahlil(ticker)
        if tiker_clean:
            try: bot.send_photo(uid, logo_url, caption=javob, parse_mode="HTML", reply_markup=inline_action(tiker_clean))
            except: bot.send_message(uid, javob, parse_mode="HTML", reply_markup=inline_action(tiker_clean))
        bot.answer_callback_query(call.id)

    elif call.data.startswith("ai_"):
        ticker_name = call.data[3:]
        bot.send_chat_action(uid, 'typing')
        bot.send_message(uid, f"🤖 <b>{ticker_name} — AI Maslahati:</b>\n\n<i>{get_ai_advice(ticker_name)}</i>", parse_mode="HTML")
        bot.answer_callback_query(call.id)

    elif call.data.startswith("dic_"):
        term = call.data[4:]
        if term.startswith("page_"):
            p = int(term.split("_")[1])
            bot.edit_message_text(chat_id=uid, message_id=call.message.message_id, text=f"📖 <b>Moliyaviy lug'at ({p}-sahifa):</b>", parse_mode="HTML", reply_markup=inline_dictionary(page=p))
        else:
            explanations = {
                "mcap": "📊 <b>Market Cap:</b> Kompaniyaning bozordagi barcha aksiyalarining umumiy qiymati. Formula: Aksiya narxi × Jami aksiyalar soni.",
                "pe": "📈 <b>P/E Ratio:</b> Aksiya narxi yillik foydasidan necha barobar qimmatligini ko'rsatadi. Past P/E = Arzonroq.",
                "debteq": "🚨 <b>Debt/Equity:</b> Kompaniyaning o'z kapitaliga nisbatan qarz yuklamasi. 33% dan past = Islomiy moliya bo'yicha xavfsiz.",
                "rsi": "📉 <b>RSI:</b> 0-100 oralig'ida. 30 dan past = Oversold (Arzon). 70 dan yuqori = Overbought (Qimmat).",
                "eps": "💰 <b>EPS:</b> Har bir aksiyaga to'g'ri keladigan sof foyda. Yuqori EPS = Yaxshi.",
                "roe": "👑 <b>ROE:</b> Kompaniya o'z kapitalidan qancha foyda olayotgani. 15%+ = Yaxshi darajada.",
                "fcf": "💵 <b>FCF:</b> Barcha xarajatlardan keyin qolgan erkin naqd pul. Musbat FCF = Sog'lom kompaniya.",
                "pb": "📚 <b>P/B Ratio:</b> Aksiya narxining kitobiy qiymatiga nisbati. 1 dan past = Potensial arzon."
            }
            bot.send_message(uid, explanations.get(term, "❓ Ma'lumot topilmadi."), parse_mode="HTML")
        bot.answer_callback_query(call.id)

# ===================== WEBHOOK GATEWAY =====================
@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.get_data().decode('UTF-8'))
        bot.process_new_updates([update])
    except Exception as e: print(f"Webhook xato: {e}")
    return '!', 200

# ===================== ENGINE RUNNER =====================
def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    print("Bot ishga tushmoqda...")
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
        print(f"Webhook o'rnatildi: {RENDER_URL}")
    except Exception as e: print(f"Webhook xatosi: {e}")

    # Render uchun Flask va Bot parallel xavfsiz ishga tushiriladi
    threading.Thread(target=run_web).start()
