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
RENDER_URL = 'https://aksiya-halol-bot3.onrender.com'
ADMIN_ID = 5716183424

# bot.polling xatolik tufayli to'xtab qolmasligi uchun threaded=True qilamiz
bot = telebot.TeleBot(TOKEN, threaded=True)

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
            return 50.0, "USHLAB TURISH / HOLD ↕️"
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
        avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
        rs = avg_gain / avg_loss.where(avg_loss != 0, 1)
        rsi = 100 - (100 / (1 + rs))
        current_rsi = round(rsi.iloc[-1], 2)
        if current_rsi >= 70: return current_rsi, "SOTISH / SELL 📉"
        elif current_rsi <= 30: return current_rsi, "SOTIB OLISH / BUY 📈"
        else: return current_rsi, "USHLAB TURISH / HOLD ↕️"
    except:
        return 50.0, "USHLAB TURISH / HOLD ↕️"

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
def ai_request(prompt: str, timeout: int = 7):
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
        result = ai_request(prompt, timeout=8)
        return result if result else "🤖 AI xizmati hozir band. Keyinroq qayta urinib ko'ring."
    except:
        return "🤖 AI xizmati hozir band. Keyinroq qayta urinib ko'ring."

# ===================== UZBEKISTAN STOCK (UZSE API & PARSING) =====================
def uzbek_stock_price(symbol):
    try:
        url = "https://uzse.uz/api/v1/quotes.json"
        res = requests.get(url, timeout=7)
        if res.status_code == 200:
            data = res.json()
            for item in data.get('data', []):
                ticker_name = str(item.get('ticker', '')).strip().upper()
                if symbol.strip().upper() == ticker_name:
                    price = str(item.get('price', '0')).replace(" ", "").replace(",", ".")
                    return float(price)
        
        # Zaxira HTML Parser
        url_html = "https://uzse.uz/quotes"
        res_html = requests.get(url_html, timeout=7, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res_html.text, "html.parser")
        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) > 1:
                name = cols[0].text.strip().upper()
                if symbol.strip().upper() in name or name in symbol.strip().upper():
                    price = cols[1].text.strip().replace(" ", "").replace(",", ".")
                    return float(price)
        return None
    except:
        return None

def uzbekistan_stock_analysis(text_input: str):
    symbol = text_input.strip().upper()
    uz_price = uzbek_stock_price(symbol)
    
    if uz_price:
        price_str = f"<b>{uz_price:,.2f} UZS</b>"
    else:
        price_str = "⚠️ Birja serveri band (Narxni aniqlab bo'lmadi)"
    
    prompt = (
        f"Siz Toshkent Respublika Fond Birjasi (UZSE) bo'yicha professional moliya expertisiz.\n"
        f"Foydalanuvchi: '{symbol}' kompaniyasini so'radi. Narxi: {uz_price if uz_price else 'Noma`lum'} UZS.\n\n"
        f"Ushbu kompaniya haqida qisqa va aniq islomiy moliya tahlilini bering:\n"
        f"🇺🇿 Kompaniya nomi: [To'liq nomi]\n"
        f"🟢 Shariat Statusi: [Halol/Xavfli/Xarom]\n"
        f"📊 Fundamental holati: [Qisqa baho]\n"
        f"🎯 YAKUNIY QAROR: [BUY, HOLD yoki AVOID]\n\n"
        f"Faqat o'zbek tilida, chiroyli va lo'nda javob bering."
    )
    res = ai_request(prompt, timeout=9)
    if res:
        return f"━━━━━━━━━━━━━━━━━━━━\n🇺🇿 <b>TOSHKENT RFB TAHLILI ({symbol})</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 Birja narxi: {price_str}\n\n{res}\n━━━━━━━━━━━━━━━━━━━━"
    
    return f"━━━━━━━━━━━━━━━━━━━━\n🇺🇿 <b>TOSHKENT RFB TAHLILI ({symbol})</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 Birja narxi: {price_str}\n\n⚠️ UZSE birjasi yoki AI serverlarida yuklama yuqori. Birozdan so'ng qayta urinib ko'ring.\n━━━━━━━━━━━━━━━━━━━━"

# ===================== YANGILIKLAR =====================
def get_market_news():
    try:
        url = "https://news.google.com/rss/search?q=stock+market+investing+news&hl=en-US&gl=US&ceid=US:en"
        res = requests.get(url, timeout=6)
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
        uz_news = ai_request(prompt, timeout=7)
        return uz_news if uz_news else combined + "\n\n⚠️ <i>(Tarjimon xizmati bandligi sababli inglizcha ko'rsatildi)</i>"
    except:
        return "🌐 Global yangiliklar serveri band. Birozdan so'ng qayta urinib ko'ring."

# ===================== KRIPTO BOZORI =====================
def get_crypto_market_summary():
    cryptos = {"BTC-USD": "Bitcoin (BTC)", "ETH-USD": "Ethereum (ETH)", "BNB-USD": "BNB", "SOL-USD": "Solana (SOL)", "XRP-USD": "Ripple (XRP)"}
    matn = "━━━━━━━━━━━━━━━━━━━━\n🪙 <b>JORIY KRIPTO BOZORI</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    has_data = False
    for ticker, name in cryptos.items():
        try:
            coin = yf.Ticker(ticker)
            hist = coin.history(period="2d")
            if hist is not None and len(hist) >= 2:
                narx = hist['Close'].iloc[-1]
                old_narx = hist['Close'].iloc[-2]
                ozgarish = ((narx - old_narx) / old_narx) * 100
                belgi = "📈" if ozgarish >= 0 else "📉"
                matn += f"{belgi} <b>{name}</b>\n  └ {narx:,.2f} USD | {ozgarish:+.2f}%\n\n"
                has_data = True
            else:
                matn += f"❌ <b>{name}</b>: Ma'lumot yo'q\n\n"
        except:
            matn += f"❌ <b>{name}</b> yuklanmadi.\n\n"
    if not has_data:
        return "❌ Kripto bozorini yuklashda Yahoo Finance xatoligi berdi. Qayta urinib ko'ring."
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

# ===================== GLOBAL AKSIYA TAHLILI (MUKAMMAL VA BIRLASHTIRILGAN VARIANT) =====================
def aksiya_tahlil(tiker: str):
    try:
        tiker_clean = tiker.strip().upper()
        if tiker_clean in ["BTC", "ETH", "BNB", "SOL", "XRP"]:
            tiker_clean += "-USD"

        # UZSE Tekshirish
        uz_price = uzbek_stock_price(tiker_clean)
        if uz_price:
            return uzbekistan_stock_analysis(tiker_clean), None, None

        # Ma'lumotlarni yuklash
        stock = yf.Ticker(tiker_clean)
        info = stock.info
        hist = stock.history(period="3mo")
        
        if info is None or hist is None or hist.empty:
            return f"❌ <b>{tiker_clean}</b> bo'yicha global birjada ma'lumot topilmadi.", None, None

        long_name = info.get('longName') or info.get('shortName') or tiker_clean
        sector = info.get('sector', 'Noma\'lum')
        narx = safe_float(info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0) or 0
        logo_url = f"https://images.financialmodelingprep.com/image/company_logos/{tiker_clean}.png"

        # ℹ️ Kompaniya haqida tarjima
        desc_en = info.get('longBusinessSummary', '')
        summary_uz = "— Ma'lumot vaqtincha yuklanmadi —"
        if desc_en:
            prompt_desc = f"Quyidagi kompaniya tavsifini o'zbek tiliga lo'nda va tushunarli qilib 2 ta gapda tarjima qiling. Faqat tarjimani qaytaring:\n\n{desc_en[:400]}"
            summary_uz = ai_request(prompt_desc, timeout=8) or "— Tarjima yuklanmadi (AI band) —"

        # Xodimlar
        employees = info.get('fullTimeEmployees', '—')
        employees_str = f"{employees:,} nafar" if isinstance(employees, int) else "—"

        # Narx va 52 haftalik diapazon
        high_52 = safe_float(info.get('fiftyTwoWeekHigh')) or narx
        low_52 = safe_float(info.get('fiftyTwoWeekLow')) or narx
        market_cap = safe_float(info.get('marketCap')) or 0
        cap_str = format_katta_son(market_cap)
        div_yield = safe_float(info.get('dividendYield'))
        div_str = f"{div_yield * 100:.2f}%" if div_yield else "0.0%"

        # ⚖️ DCF Adolatli Qiymat
        target_narx = safe_float(info.get('targetMeanPrice'))
        if target_narx and target_narx > narx:
            diff_pct = ((target_narx - narx) / narx) * 100
            dcf_status = f"Arzon (Undervalued) 🟢 ({diff_pct:+.2f}%)"
        elif target_narx and target_narx < narx:
            diff_pct = ((narx - target_narx) / narx) * 100
            dcf_status = f"Qimmat (Overvalued) 🔴 (-{diff_pct:.2f}%)"
        else:
            dcf_status = "Adolatli narxda 🟡"

        # 👑 Moliyaviy Balans (G'azna)
        naqd_pul = safe_float(info.get('totalCash')) or 0
        qarz = safe_float(info.get('totalDebt')) or 0
        sof_foyda = safe_float(info.get('netIncomeToCommon')) or safe_float(info.get('netIncome')) or 0
        
        naqd_str = format_katta_son(naqd_pul) + " USD" if naqd_pul else "—"
        qarz_str = format_katta_son(qarz) + " USD" if qarz else "—"
        sof_foyda_str = format_katta_son(sof_foyda) + " USD" if sof_foyda else "—"

        # 🐋 Egalik tarkibi
        inst_percent = safe_float(info.get('heldPercentInstitutions', 0)) * 100 or 0
        insider_percent = safe_float(info.get('heldPercentInsiders', 0)) * 100 or 0
        retail_percent = max(0, 100 - inst_percent - insider_percent)

        # 📦 Aksiyalar miqdori & Muomala
        shares_out = safe_float(info.get('sharesOutstanding'))
        shares_float = safe_float(info.get('floatShares'))
        day_volume = safe_float(info.get('volume'))
        avg_volume = safe_float(info.get('averageVolume'))

        out_str = format_katta_son(shares_out) + " dona" if shares_out else "—"
        float_str = format_katta_son(shares_float) + " dona" if shares_float else "—"
        vol_str = format_katta_son(day_volume) + " dona" if day_volume else "—"
        avg_vol_str = format_katta_son(avg_volume) + " dona" if avg_volume else "—"

        # 💰 Dividend Sanasi
        last_div = safe_float(info.get('lastDividendValue'))
        last_div_str = f"{last_div:.2f} USD" if last_div else "—"

        # Fundamental Ko'rsatkichlar
        pe_val = safe_float(info.get('trailingPE'))
        pb_val = safe_float(info.get('priceToBook'))
        eps_val = safe_float(info.get('trailingEps'))
        fcf_val = safe_float(info.get('freeCashflow'))
        
        pe_str = f"{pe_val:.2f}" if pe_val else "—"
        pb_str = f"{pb_val:.2f}" if pb_val else "—"
        eps_str = f"{eps_val:.2f}" if eps_val else "—"
        fcf_str = format_katta_son(fcf_val) + " USD" if fcf_val else "—"

        # 📐 Fibonacci Darajalari
        closes = hist['Close']
        high_3m = closes.max()
        low_3m = closes.min()
        diff_3m = high_3m - low_3m
        fib_382 = high_3m - (diff_3m * 0.382)
        fib_500 = high_3m - (diff_3m * 0.500)
        fib_618 = high_3m - (diff_3m * 0.618)

        # 📊 Dinamika hisoblash
        if len(closes) >= 20:
            pct_1d = ((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2]) * 100
            pct_1w = ((closes.iloc[-1] - closes.iloc[-6]) / closes.iloc[-6]) * 100
            pct_1m = ((closes.iloc[-1] - closes.iloc[-21]) / closes.iloc[-21]) * 100
        else:
            pct_1d = pct_1w = pct_1m = 0.0

        # Texnik Indikatorlar (RSI + Bollinger)
        rsi, rsi_signal = hisobla_rsi(closes)
        upper, middle, lower = hisobla_bollinger(closes)

        # Status va Qaror strategiyasi (IKKI TILLI)
        debt_ratio = (qarz / market_cap * 100) if market_cap else 0
        halal_status = "KRIPTO 🪙" if "-USD" in tiker_clean else ("HALOL 🟢" if debt_ratio < 30 else "HAROM 🔴")

        signal = "USHLAB TURISH / HOLD ↕️"
        bot_baho = "2.5/5.0 ★★☆☆☆"
        if rsi <= 30 and narx < lower: 
            signal = "KUCHLI SOTIB OLISH / STRONG BUY 🚀"; bot_baho = "4.5/5.0 ★★★★☆"
        elif rsi <= 40: 
            signal = "SOTIB OLISH / BUY 🛒"; bot_baho = "4.0/5.0 ★★★★☆"
        elif rsi >= 70 and narx > upper: 
            signal = "KUCHLI SOTISH / STRONG SELL 📉"; bot_baho = "1.5/5.0 ★☆☆☆☆"
        elif rsi >= 60: 
            signal = "SOTISH / SELL ⚠️"; bot_baho = "2.0/5.0 ★★☆☆☆"

        javob = f"""━━━━━━━━━━━━━━━━━━━━
<b>{tiker_clean} | {html.escape(long_name)}</b>
Sektor: <b>{html.escape(sector)}</b> | Status: <b>{halal_status}</b>
━━━━━━━━━━━━━━━━━━━━
ℹ️ <b>Kompaniya haqida:</b>
<i>{html.escape(summary_uz)}</i>
━━━━━━━━━━━━━━━━━━━━
💵 Narx: <b>{narx:,.2f} USD</b>
⚖️ DCF Adolatli Qiymati: <b>{dcf_status}</b>
52W M/M: <b>{high_52:,.2f} / {low_52:,.2f}</b>
Cap: <b>{cap_str}</b> | Div Yield: <b>{div_str}</b>
━━━━━━━━━━━━━━━━━━━━
🏢 Kompaniya xodimlari: <b>{employees_str}</b>
━━━━━━━━━━━━━━━━━━━━
👑 <b>Moliyaviy Balans (G'azna):</b>
  └ 💵 Qo'lidagi naqd pul: <b>{naqd_str}</b>
  └ 🚨 Jami qarzi: <b>{qarz_str}</b>
  └ 📈 Sof foyda (Yillik): <b>{sof_foyda_str}</b>
━━━━━━━━━━━━━━━━━━━━
🐋 <b>YIRIK KITLARNING ULUSHI:</b>
  └ 🐳 BlackRock Inc.: <b>~9.6% ulush</b>
  └ 🐳 State Street Corp: <b>~3.1% ulush</b>
━━━━━━━━━━━━━━━━━━━━
🐋 <b>Egalik tarkibi (Umumiy):</b>
  └ 🐳 Kitlar (Yirik Fondlar): <b>{inst_percent:.1f}%</b>
  └ 👔 Egalari (Insayderlar): <b>{insider_percent:.1f}%</b>
  └ 🛒 Chakana treyderlar: <b>{retail_percent:.1f}%</b>
━━━━━━━━━━━━━━━━━━━━
📦 <b>Aksiyalar miqdori & Muomala:</b>
  └ 📊 Jami chiqarilgan: <b>{out_str}</b>
  └ 🛒 Sotuvda (Float): <b>{float_str}</b>
  └ 🔄 Bugungi Oldi-sotdi: <b>{vol_str}</b>
  └ ⏱️ 3 oylik o'rtacha hajm: <b>{avg_vol_str}</b>
━━━━━━━━━━━━━━━━━━━━
💰 <b>Dividend Taqvimi (Faqat Aksiyalar):</b>
  └ ↩️ Oxirgi ajratilgan: <b>{last_div_str}</b>
━━━━━━━━━━━━━━━━━━━━
<b>Fundamental Ko'rsatkichlar:</b>
P/E: <b>{pe_str}</b> | P/B: <b>{pb_str}</b> | EPS: <b>{eps_str}</b>
FCF: <b>{fcf_str}</b>
━━━━━━━━━━━━━━━━━━━━
📐 <b>Fibonacci (3M):</b>
  38.2%: <b>{fib_382:,.2f} USD</b> | 50.0%: <b>{fib_500:,.2f} USD</b> | 61.8%: <b>{fib_618:,.2f} USD</b>
━━━━━━━━━━━━━━━━━━━━
📊 <b>Dinamika:</b>
1D: <b>{pct_1d:+.2f}%</b> | 1W: <b>{pct_1w:+.2f}%</b> | 1M: <b>{pct_1m:+.2f}%</b>
━━━━━━━━━━━━━━━━━━━━
📊 <b>Texnik Ko'rsatkichlar:</b>
📉 RSI (14): <b>{rsi}</b> → <b>{rsi_signal}</b>
📊 Bollinger Upper: <b>{upper:,.2f}</b>
📊 Bollinger Middle: <b>{middle:,.2f}</b>
📊 Bollinger Lower: <b>{lower:,.2f}</b>

🎯 <b>YAKUNIY SIGNAL: {signal}</b>
🎯 <b>BOT BAHOSI: {bot_baho}</b>
━━━━━━━━━━━━━━━━━━━━"""
        return javob, tiker_clean, logo_url
    except Exception as e:
        return f"❌ {tiker.upper()} tahlilida xatolik yuz berdi.", None, None

# ===================== KUNLIK TOP SIGNAL (IKKI TILLI VARIANT) =====================
def top_signal():
    watch = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN"]
    text = "🔥 <b>TOP SIGNAL (RSI + BOLLINGER)</b>\n\n"
    for s in watch:
        try:
            stock, info, hist = get_stock_data(s)
            if hist is None or hist.empty: continue
            closes = hist['Close']
            narx = closes.iloc[-1]
            rsi, _ = hisobla_rsi(closes)
            upper, _, lower = hisobla_bollinger(closes)
            
            if rsi <= 30 and narx < lower: sig = "🚀 KUCHLI SOTIB OLISH / STRONG BUY"
            elif rsi <= 40: sig = "🛒 SOTIB OLISH / BUY"
            elif rsi >= 70 and narx > upper: sig = "📉 KUCHLI SOTISH / STRONG SELL"
            elif rsi >= 60: sig = "⚠️ SOTISH / SELL"
            else: sig = "↕️ USHLAB TURISH / HOLD"
            
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

    elif text == "🧠 Kunlik Test":
        bot.send_chat_action(uid, 'typing')
        zaxira_quizlar = [
            {"question": "Islomiy moliya qoidalariga ko'ra, kompaniyaning jami qarzining (Total Debt) uning kapitallashuviga (Market Cap) nisbati necha foizdan oshmasligi kerak?", "options": ["30%", "50%", "10%", "70%"], "explanation": "Shariat standartlariga ko'ra, qarz yuklamasi 30% dan oshmagan kompaniya aksiyalari halol hisoblanishi mumkin."},
            {"question": "RSI ko'rsatkichi 30 dan pastga tushganda, bu bozordagi qanday holatni anglatadi?", "options": ["Oversold (Haddan tashqari sotilgan/Arzon)", "Overbought (Haddan tashqari sotib olingan)", "Trend o'zgarmas holatda", "Kompaniya bankrot bo'lmoqda"], "explanation": "RSI 30 dan past bo'lsa, aksiya haddan tashqari ko'p sotilgan va narx texnik jihatdan arzon zonaga kirgan bo'ladi."},
            {"question": "Bollinger Bands indikatorida narx pastki chiziqdan (Lower Band) ham pastga tushib ketsa, qanday signal hisoblanadi?", "options": ["Potensial sotib olish (BUY)", "Kuchli sotish (STRONG SELL)", "Hech qanday o'zgarish yo'q", "Kripto narxi tushishi"], "explanation": "Narx pastki Bollinger chizig'idan chiqib ketganda, ko'pincha orqaga (o'rtacha qiymatga) qaytish tendensiyasi kuzatiladi."}
        ]
        quiz_prompt = (
            "You are a finance teacher. Create 1 random multiple-choice quiz question about stocks, technical analysis (RSI, Bollinger) or Islamic finance in Uzbek.\n"
            "Return ONLY a raw valid JSON object. No explanations outside JSON. No markdown blocks.\n"
            "Format:\n"
            "{\n  \"question\": \"Question text here?\",\n  \"options\": [\"Correct Answer\", \"Wrong 1\", \"Wrong 2\", \"Wrong 3\"],\n  \"explanation\": \"Short explanation (max 200 chars).\"\n}\n"
            "Crucial: The correct answer MUST always be at index 0 in the options array."
        )
        raw_quiz = ai_request(quiz_prompt, timeout=8)
        quiz_parsed = None
        if raw_quiz:
            try:
                clean_json = raw_quiz.strip().replace("```json", "").replace("```", "").strip()
                start_idx = clean_json.find('{')
                end_idx = clean_json.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    clean_json = clean_json[start_idx:end_idx]
                quiz_parsed = json.loads(clean_json)
            except: quiz_parsed = None

        if not quiz_parsed or "question" not in quiz_parsed or "options" not in quiz_parsed:
            quiz_parsed = random.choice(zaxira_quizlar)

        try:
            shuffled_options = list(quiz_parsed["options"])
            togri_javob = quiz_parsed["options"][0]
            random.shuffle(shuffled_options)
            correct_index = shuffled_options.index(togri_javob)
            bot.send_poll(chat_id=uid, question=quiz_parsed["question"], options=shuffled_options, type="quiz",
                          correct_option_id=correct_index, explanation=quiz_parsed["explanation"][:200], is_anonymous=False)
        except:
            bot.send_message(uid, "❌ Viktorina tizimida vaqtinchalik texnik muammo. Qayta urinib ko'ring.")

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

def run_bot_polling():
    while True:
        try:
            print("Bot polling boshlandi...")
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Polling ichki xatosi: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        bot.remove_webhook()
        time.sleep(1)
    except: pass

    threading.Thread(target=run_bot_polling, daemon=True).start()
    run_web()
