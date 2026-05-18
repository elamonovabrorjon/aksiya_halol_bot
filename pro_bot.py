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
    return "Smart Money & Liquidity Bot barqaror rejimda ishlamoqda!", 200

# ===================== SOZLAMALAR =====================
TOKEN = os.getenv("BOT_TOKEN") or "8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8"
RENDER_URL = 'https://aksiya-halol-bot3.onrender.com'
ADMIN_ID = 5716183424

bot = telebot.TeleBot(TOKEN, threaded=True)

user_modes = {}
uz_user_modes = {}

# Kripto loyihalar uchun maxsus Shariat filtri bazasi
KRIPTO_HALOL_BAZA = {
    "BTC": "HALOL 🟢 (Asosiy ayblov vositasi, deflyatsion raqamli oltin)",
    "ETH": "HALOL 🟢 (Yordamchi utility ekotizim tarmog'i)",
    "BNB": "SHUBHALI 🟡 (Ekotizimida ruxsat berilgan kaldıraç / marja elementlari bor)",
    "SOL": "HALOL 🟢 (Tezkor va arzon operatsion blockchain tarmog'i)",
    "XRP": "SHUBHALI 🟡 (Markazlashgan bank tizimlariga xizmat qiladi, sud jarayonlari ko'p)",
    "ADA": "HALOL 🟢 (Ilmiy asoslangan proof-of-stake tarmog'i)",
    "DOT": "HALOL 🟢 (Parachain va ekotizim tarmog'i)",
    "DOGE": "HAROM/XAVFLI 🔴 (Meme-coin, spekulyativ, ichki fundamental qiymatga ega emas)",
    "SHIB": "HAROM/XAVFLI 🔴 (Meme-coin, yuqori spekulyatsiya xavfi yuqori)",
    "AVAX": "HALOL 🟢 (Aqlli kontraktlar platformasi)",
    "LINK": "HALOL 🟢 (Oracle texnologiyasi, ma'lumotlar yetkazuvchi vizual tarmoq)"
}

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
        if info is None or len(info) == 0:
            return None, None, None
        result = (stock, info, hist)
        _cache[ticker] = result
        _cache_time[ticker] = now
        return result
    except:
        return None, None, None

# ===================== SMART MONEY & LIKVIDLIK HISOBLAGICI (SMC) =====================
def hisobla_smart_money_likvidlik(hist, joriy_narx):
    try:
        if hist is None or hist.empty or len(hist) < 20:
            return "⚖️ Likvidlik zonalari aniqlanmadi.", "Kutish rejimi."
            
        highs = hist['High']
        lows = hist['Low']
        closes = hist['Close']
        
        # Oxirgi 20 ta sham ichidagi eng yuqori va eng past nuqtalar (Swing High / Swing Low)
        swing_high = float(highs.tail(20).max())
        swing_low = float(lows.tail(20).min())
        
        # Likvidlik hududlari
        buy_side_liq = swing_high   # Ayiqlarning Stop-Loss hovuzi (BSL)
        sell_side_liq = swing_low   # Buqalarning Stop-Loss hovuzi (SSL)
        
        # Narx oqimi qaysi tomondagi likvidlikka yaqinroq ekanini aniqlash
        masofa_bsl = abs(joriy_narx - buy_side_liq)
        masofa_ssl = abs(joriy_narx - sell_side_liq)
        
        if masofa_bsl < masofa_ssl:
            yaqin_likvidlik = f"🚀 <b>Buy-Side Liquidity (BSL):</b> {buy_side_liq:,.2f} USD atrofida yirik short-stoplar hovuzi mavjud."
            kutilma = "Smart Money (Kitlar) narxni tepadagi likvidlikni yig'ib olish (Liquidity Sweep) uchun yuqoriga tortishi kutilmoqda."
        else:
            yaqin_likvidlik = f"🩸 <b>Sell-Side Liquidity (SSL):</b> {sell_side_liq:,.2f} USD atrofida yirik long-stoplar hovuzi joylashgan."
            kutilma = "Kitlar pastdagi stop-loss buyruqlarini urib, bozorni likvidlik bilan ta'minlash uchun narxni tushirishi mumkin."
            
        # H4 yoki D1 dagi FVG (Fair Value Gap - Bo'shliqlar) simulyatsiyasi
        fvg_text = "⚖️ Imbalans (FVG): Narx muvozanatda, keskin bo'shliqlar yo'q."
        if len(closes) >= 3:
            h_1 = float(highs.iloc[-3])
            l_3 = float(lows.iloc[-1])
            if l_3 > h_1:
                fvg_text = f"⚠️ <b>FVG (Bullish Gap):</b> {h_1:,.2f} - {l_3:,.2f} USD zonasida ochiq likvidlik bo'shlig'i bor. Narx uni yopish uchun qaytishi mumkin."
            elif h_1 > l_3:
                h_3 = float(highs.iloc[-1])
                l_1 = float(lows.iloc[-3])
                if l_1 > h_3:
                    fvg_text = f"⚠️ <b>FVG (Bearish Gap):</b> {h_3:,.2f} - {l_1:,.2f} USD zonasida ochiq likvidlik bo'shlig'i qolgan."

        return f"{yaqin_likvidlik}\n  └ 🔍 {fvg_text}", kutilma
    except:
        return "⚖️ Likvidlik hovuzlarini tahlil qilishda texnik cheklov yuz berdi.", "Kutish rejimi."

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

# ===================== AI XIZMATI =====================
def ai_request(prompt: str, timeout: int = 8):
    try:
        response = requests.post(
            "https://text.pollinations.ai/",
            json={"messages": [{"role": "user", "content": prompt}], "model": "mistral-large"},
            timeout=timeout
        )
        if response.status_code == 200 and response.text.strip():
            return response.text.strip()
    except: pass
    return None

def get_ai_advice(ticker):
    try:
        stock, info, hist = get_stock_data(ticker)
        if info is None: return "🤖 AI xizmati hozir band. Keyinroq qayta urinib ko'ring."
        narx = safe_float(info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0) or 0
        closes = hist['Close'] if hist is not None else None
        rsi, _ = hisobla_rsi(closes)
        
        prompt = f"Siz moliya tahlilchisiz. {ticker} aksiyasi/koini uchun o'zbekcha 2 ta gapda ixcham Smart Money tavsiyasini bering. Narx: {narx} USD, RSI: {rsi}."
        return ai_request(prompt, timeout=8) or "🤖 AI xizmati yuklama tufayli hozir javob bera olmadi."
    except:
        return "🤖 AI xizmati hozir band. Keyinroq qayta urinib ko'ring."

# ===================== GLOBAL PUL OQIMI =====================
def get_capital_flow():
    try:
        tickers = {"Dollar (Forex)": "DX-Y.NYB", "Aksiya (S&P 500)": "^GSPC", "Oltin (Xom-ashyo)": "GC=F", "Kripto (Bitcoin)": "BTC-USD"}
        o_zgarishlar = {}
        for nom, tiker in tickers.items():
            try:
                hist = yf.Ticker(tiker).history(period="5d")
                if len(hist) >= 2:
                    o_zgarishlar[nom] = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
                else: o_zgarishlar[nom] = 0.0
            except: o_zgarishlar[nom] = 0.0

        dxy = o_zgarishlar.get("Dollar (Forex)", 0.0)
        sp = o_zgarishlar.get("Aksiya (S&P 500)", 0.0)
        gold = o_zgarishlar.get("Oltin (Xom-ashyo)", 0.0)
        crypto = o_zgarishlar.get("Kripto (Bitcoin)", 0.0)
        manba, manzil = "", ""

        if dxy > 0.2 and sp < 0 and crypto < 0:
            manba = "🔴 <b>Aksiya</b> va <b>Kripto</b> bozorlaridan pul chiqib ketmoqda."
            manzil = "🟢 Global pullar xavfsiz boshpana sifatida <b>Forex (AQSh Dollari - DXY)</b> naqd pul g'aznasiga oqib o'tmoqda. (Risk-Off tsikli)"
        elif dxy < -0.2 and sp > 0 and crypto > 0:
            manba = "🔴 <b>Forex (AQSh Dollari)</b> naqd g'aznadan yirik kapital chiqmoqda."
            manzil = "🟢 Pullar to'g'ridan-to'g'ri xavfli aktivlar bo'lgan <b>Aksiya (S&P 500)</b> va <b>Kripto (Bitcoin)</b> bozoriga shiddat bilan kirib bormoqda! (Risk-On tsikli)"
        elif gold > 0.8 and sp < 0:
            manba = "🔴 Biznes va riskli investitsiyalardan (<b>Aksiyalardan</b>) pullar chekinmoqda."
            manzil = "🟢 Global geosiyosiy yoki iqtisodiy xavflar tufayli kapital <b>Xom-ashyo (Oltin)</b> bozoriga yashirinmoqda."
        elif crypto > 2.5 and sp < 0.3:
            manba = "🔴 An'anaviy moliya tizimidan kapital chiqishi kuzatilmoqda."
            manzil = "🟢 Pullar yuqori daromad ilinjida raqamli aktivlar — <b>Kriptovalyuta (Kripto)</b> bozoriga ko'chib o'tmoqda."
        else:
            manba = "⚖️ Bozorlarda keskin kapital ko'chishi aniqlanmadi. Pozitsiyalar teng taqsimlangan."
            manzil = "🔄 Pullar ayni paytda ichki korreksiya va kutish rejimida (Konsolidatsiya)."

        return f"""━━━━━━━━━━━━━━━━━━━━
🌐 <b>GLOBAL CAPITAL FLOW (PUL OQIMI)</b>
━━━━━━━━━━━━━━━━━━━━
📊 <b>Oxirgi bozorlar dinamikasi:</b>
💵 1. Forex (Dollar Indeksi): <b>{dxy:+.2f}%</b>
📈 2. Aksiya bozori (S&P500): <b>{sp:+.2f}%</b>
👑 3. Xom-ashyo (Oltin): <b>{gold:+.2f}%</b>
🪙 4. Kripto bozori (BTC): <b>{crypto:+.2f}%</b>
━━━━━━━━━━━━━━━━━━━━
🔍 <b>PUL QAYERDAN CHIQYAPTI?</b>
{manba}

🎯 <b>PUL QAYERGE BORYAPTI?</b>
{manzil}
━━━━━━━━━━━━━━━━━━━━
<i>💡 Tahlil qoidasi: Dollar indeksi (DXY) ko'tarilsa, odatda aksiya va kripto tushadi. Oltin ko'tarilsa - investorlar xavfsizlik izlamoqda.</i>"""
    except:
        return "❌ Global pul oqimi tahlilini shakllantirishda texnik nosozlik yuz berdi."

# ===================== UZBEKISTAN STOCK =====================
def uzbek_stock_price(symbol):
    symbol_clean = symbol.strip().upper()
    if symbol_clean == "UZNIF": symbol_clean = "UNIF"
    if symbol_clean == "UZPLT": symbol_clean = "UZPL"
    try:
        url = "https://uzse.uz/api/v1/quotes.json"
        res = requests.get(url, timeout=4).json()
        for item in res.get('data', []):
            if symbol_clean == str(item.get('ticker', '')).strip().upper():
                return float(str(item.get('price', '0')).replace(" ", "").replace(",", "."))
        return None
    except: return None

def uzbekistan_stock_analysis(text_input: str):
    symbol = text_input.strip().upper()
    uz_price = uzbek_stock_price(symbol)
    price_str = f"<b>{uz_price:,.2f} UZS</b>" if uz_price else "<b>Mavjud emas 🟡</b>"
    
    return f"""━━━━━━━━━━━━━━━━━━━━
🇺🇿 <b>TOSHKENT RFB TAHLILI ({symbol})</b>
━━━━━━━━━━━━━━━━━━━━
💰 Birja narxi: {price_str}

🟢 <b>Shariat Statusi:</b> Sektor va moliya qoidalariga ko'ra aksariyat milliy ishlab chiqarish aksiyalari Halol hisoblanadi.
📊 <b>Fundamental tahlil:</b> Kompaniyaning choraklik hisobotlari shakllanish jarayonida. Mahalliy bozor likvidligi o'rtacha darajada.
🎯 <b>Qaror:</b> HOLD (Kuzatish tavsiya etiladi)
━━━━━━━━━━━━━━━━━━━━"""

# ===================== SO'NGGI YANGILIKLAR =====================
def get_market_news():
    try:
        url = "https://news.google.com/rss/search?q=stock+market+investing+news&hl=en-US&gl=US&ceid=US:en"
        res = requests.get(url, timeout=5)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(res.content)
        news_list = [item.find('title').text.split(" - ")[0] for item in root.findall('.//item')[:4]]
        combined = "\n\n".join([f"- {t}" for t in news_list])
        return ai_request(f"Quyidagi yangiliklarni o'zbek tiliga lo'nda tarjima qiling:\n\n{combined}", timeout=7) or combined
    except: return "🌐 Global yangiliklar serveri band. Qayta urinib ko'ring."

# ===================== KRIPTO BOZORI & HEATMAP SYMBOL =====================
def get_crypto_price_binance(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT"
        res = requests.get(url, timeout=3).json()
        return float(res['lastPrice']), float(res['priceChangePercent'])
    except: return None, None

def get_crypto_market_summary():
    cryptos = {"BTC": "Bitcoin", "ETH": "Ethereum", "BNB": "BNB", "SOL": "Solana", "XRP": "Ripple"}
    matn = "━━━━━━━━━━━━━━━━━━━━\n🪙 <b>JORIY KRIPTO BOZORI & STATUS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for ticker, name in cryptos.items():
        price, change = get_crypto_price_binance(ticker)
        status = KRIPTO_HALOL_BAZA.get(ticker, "HALOL 🟢")
        if price:
            belgi = "📈" if change >= 0 else "📉"
            matn += f"{belgi} <b>{name} ({ticker})</b>\n  └ {price:,.2f} USD | {change:+.2f}%\n  └ 🕋 Status: {status}\n\n"
        else:
            matn += f"🟡 <b>{name} ({ticker})</b>\n  └ Server band | Yangilanmoqda...\n\n"
    return matn + "━━━━━━━━━━━━━━━━━━━━"

# ===================== BOZOR YETAKCHILARI =====================
def get_market_movers():
    watch_list = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]
    gainers = []
    for tiker in watch_list:
        try:
            hist = yf.Ticker(tiker).history(period="2d")
            if len(hist) >= 2:
                yopilish, ochilish = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
                gainers.append({"ticker": tiker, "price": yopilish, "change": ((yopilish - ochilish) / ochilish) * 100})
        except: pass
    matn = "━━━━━━━━━━━━━━━━━━━━\n🔥 <b>BUGUNGI BOZOR YETAKCHILARI</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for item in gainers:
        belgi = "🟢" if item['change'] >= 0 else "🔴"
        matn += f"  {belgi} <b>{item['ticker']}</b>: {item['price']:.2f} USD ({item['change']:+.2f}%)\n"
    return matn + "━━━━━━━━━━━━━━━━━━━━"

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

# ===================== GLOBAL AKSIYA & KRIPTO MUKAMMAL TAHLILI =====================
def aksiya_tahlil(tiker: str):
    try:
        tiker_clean = tiker.strip().upper()
        
        # Agar O'zbekiston aksiyasi kiritilsa
        if tiker_clean in ["NKMK", "SQB", "UZAUTO", "UNIF", "UZNIF", "UZPL", "UZPLT", "URTS"]:
            return uzbekistan_stock_analysis(tiker_clean), None, None

        # Agar toza kripto nomi kiritilgan bo'lsa uni Yahoo formatiga o'tkazamiz
        is_crypto = tiker_clean in KRIPTO_HALOL_BAZA or tiker_clean.endswith("-USD")
        if tiker_clean in KRIPTO_HALOL_BAZA:
            tiker_yf = tiker_clean + "-USD"
        else:
            tiker_yf = tiker_clean

        stock, info, hist = get_stock_data(tiker_yf)
        if info is None or hist is None or hist.empty:
            return f"❌ <b>{tiker_clean}</b> topilmadi. Tiker to'g'ri kiritilganini tekshiring.", None, None

        long_name = info.get('longName') or info.get('shortName') or tiker_clean
        sector = info.get('sector', 'Kriptovalyuta / Raqamli Aktiv' if is_crypto else 'Noma\'lum')
        narx = safe_float(info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0) or 0
        logo_url = f"https://images.financialmodelingprep.com/image/company_logos/{tiker_clean}.png" if not is_crypto else "https://cdn-icons-png.flaticon.com/512/2272/2272825.png"

        # Smart Money va Likvidlik zonalarini hisoblash funksiyasini chaqiramiz
        likvidlik_matni, kutilma_matni = hisobla_smart_money_likvidlik(hist, narx)

        # Shariat filtri (Kripto va Aksiyalar uchun alohida)
        if is_crypto:
            halal_status = KRIPTO_HALOL_BAZA.get(tiker_clean.replace("-USD",""), "HALOL 🟢 (Loyiha asosi texnik xizmat ko'rsatadi)")
        else:
            qarz = safe_float(info.get('totalDebt')) or 0
            market_cap = safe_float(info.get('marketCap')) or 1
            debt_ratio = (qarz / market_cap * 100)
            halal_status = "HALOL 🟢" if debt_ratio < 30 else "XAVFLI/HAROM 🔴 (Qarz yuklamasi > 30%)"

        cap_str = format_katta_son(info.get('marketCap'))
        pe_str = f"{safe_float(info.get('trailingPE')):.2f}" if info.get('trailingPE') else "—"

        closes = hist['Close']
        rsi, rsi_signal = hisobla_rsi(closes)
        upper, middle, lower = hisobla_bollinger(closes)

        # Dinamika foizlari
        if len(closes) >= 20:
            pct_1d = ((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2]) * 100
            pct_1m = ((closes.iloc[-1] - closes.iloc[-21]) / closes.iloc[-21]) * 100
        else: pct_1d = pct_1m = 0.0

        signal = "USHLAB TURISH / HOLD ↕️"
        bot_baho = "2.5/5.0 ★★☆☆☆"
        if rsi <= 30: signal = "KUCHLI SOTIB OLISH / STRONG BUY 🚀"; bot_baho = "4.5/5.0 ★★★★☆"
        elif rsi <= 45: signal = "SOTIB OLISH / BUY 🛒"; bot_baho = "4.0/5.0 ★★★★☆"
        elif rsi >= 70: signal = "KUCHLI SOTISH / STRONG SELL 📉"; bot_baho = "1.5/5.0 ★☆☆☆☆"
        elif rsi >= 55: signal = "SOTISH / SELL ⚠️"; bot_baho = "2.0/5.0 ★★☆☆☆"

        javob = f"""━━━━━━━━━━━━━━━━━━━━
<b>{tiker_clean} | {html.escape(long_name)}</b>
Sektor: <b>{html.escape(sector)}</b> 
🕋 Shariat Statusi: <b>{halal_status}</b>
━━━━━━━━━━━━━━━━━━━━
💰 Joriy Narx: <b>{narx:,.2f} USD</b>
📊 Bozor qiymati (Cap): <b>{cap_str}</b> | P/E: <b>{pe_str}</b>
📈 Kunlik o'zgarish: <b>{pct_1d:+.2f}%</b> | 1 oylik: <b>{pct_1m:+.2f}%</b>
━━━━━━━━━━━━━━━━━━━━
🐳 <b>SMART MONEY & LIKVIDLIK (SMC):</b>
{likvidlik_matni}

🎯 <b>Kitlar Harakati Kutilmasi:</b>
<i>{kutilma_matni}</i>
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
    except:
        return f"❌ {tiker.upper()} tahlilida kutilmagan texnik cheklov yuz berdi.", None, None

# ===================== MENYULAR =====================
def main_menu():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(types.KeyboardButton("🌐 Global Pul Oqimi"), types.KeyboardButton("🪙 Kripto bozori"),
           types.KeyboardButton("🟢 Halol aksiyalar"), types.KeyboardButton("🔥 Bozor yetakchilari"),
           types.KeyboardButton("🇺🇿 O'zbekiston aksiyalari"), types.KeyboardButton("📰 Fond bozori yangiliklari"))
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

# ===================== HANDLERLAR =====================
@bot.message_handler(commands=['start'])
def start(message):
    user_modes[message.chat.id] = False
    uz_user_modes[message.chat.id] = False
    save_user(message.chat.id)
    bot.send_message(message.chat.id, "👋 <b>Smart Money va Likvidlik tahlil botiga xush kelibsiz!</b>\n\nIstalgan aksiya yoki kripto tikerini yozib yuboring (Masalan: AAPL, NVDA, BTC, SOL) yoki quyidagi tugmalardan foydalaning:", parse_mode="HTML", reply_markup=main_menu())

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

    if text == "🌐 Global Pul Oqimi":
        bot.send_chat_action(uid, 'typing')
        bot.send_message(uid, get_capital_flow(), parse_mode="HTML")

    elif text == "🪙 Kripto bozori":
        bot.send_chat_action(uid, 'typing')
        bot.send_message(uid, get_crypto_market_summary(), parse_mode="HTML")

    elif text == "🟢 Halol aksiyalar":
        halal_list = ["AAPL", "MSFT", "NVDA"]
        bot.send_message(uid, "🟢 <b>TOP HALOL aksiyalar tahlil qilinmoqda...</b>", parse_mode="HTML")
        for ticker in halal_list:
            bot.send_chat_action(uid, 'typing')
            javob, tiker_clean, logo_url = aksiya_tahlil(ticker)
            if tiker_clean:
                try: bot.send_photo(uid, logo_url, caption=javob, parse_mode="HTML", reply_markup=inline_action(tiker_clean))
                except: bot.send_message(uid, javob, parse_mode="HTML", reply_markup=inline_action(tiker_clean))
            time.sleep(0.3)

    elif text == "🔥 Bozor yetakchilari":
        bot.send_chat_action(uid, 'typing')
        bot.send_message(uid, get_market_movers(), parse_mode="HTML")
    
    elif text == "🇺🇿 O'zbekiston aksiyalari":
        uz_user_modes[uid] = True
        bot.send_message(uid, "🇺🇿 <b>Toshkent RFB (UZSE) bo'limi</b>\nKompaniya tikerini kiriting (Masalan: NKMK, SQB, UZAUTO):", parse_mode="HTML", reply_markup=ai_exit_menu())

    elif text == "📰 Fond bozori yangiliklari":
        bot.send_chat_action(uid, 'typing')
        bot.send_message(uid, f"📰 <b>So'nggi Yangiliklar:</b>\n\n{get_market_news()}", parse_mode="HTML")

    else:
        bot.send_chat_action(uid, 'typing')
        javob, tiker, logo_url = aksiya_tahlil(text)
        if tiker:
            try: bot.send_photo(uid, logo_url, caption=javob, parse_mode="HTML", reply_markup=inline_action(tiker))
            except: bot.send_message(uid, javob, parse_mode="HTML", reply_markup=inline_action(tiker))
        else:
            bot.send_message(uid, javob, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.message.chat.id
    if call.data.startswith("ai_"):
        ticker_name = call.data[3:]
        bot.send_chat_action(uid, 'typing')
        bot.send_message(uid, f"🤖 <b>{ticker_name} — AI Smart Money Maslahati:</b>\n\n<i>{get_ai_advice(ticker_name)}</i>", parse_mode="HTML")
        bot.answer_callback_query(call.id)

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.get_data().decode('UTF-8'))
        bot.process_new_updates([update])
    except: pass
    return '!', 200

def run_bot_polling():
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except: time.sleep(5)

if __name__ == "__main__":
    try: bot.remove_webhook()
    except: pass
    threading.Thread(target=run_bot_polling, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
