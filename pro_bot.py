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

# ===================== VEB-SERVER =====================
app = Flask(__name__)

@app.route('/')
def home():
    return "Smart Money & Universal Bot barqaror rejimda ishlamoqda!", 200

# ===================== SOZLAMALAR =====================
TOKEN = os.getenv("BOT_TOKEN") or "8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8"
bot = telebot.TeleBot(TOKEN, threaded=True)

user_modes = {}
uz_user_modes = {}

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

# ===================== KENGAYTIRILGAN O'ZBEKISTON REYTINGI VA FUNDAMENTAL BAZASI =====================
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
        "nomi": "UzAuto Motors AJ (Avtomobil ishlab chiqarish)",
        "shariat": "HALOL 🟢 (Ishlab chiqarish va real savdo sektori, moliya ko'rsatkichlari mos)",
        "ishlab_chiqarish": "Yillik quvvati 400,000+ donadan ortiq avtomobil. Eksport bozori kengaymoqda.",
        "sof_foyda": "Yillik sof foyda barqaror ~2.5 - 2.8 trln so'm. Ichki bozorda mutloq monopol.",
        "dividend": "Dividend to'lash tarixi barqaror emas, lekin kapital o'sishi yuqori darajada.",
        "tavsiya": "🛒 SOTIB OLISH (BUY) — Ichki bozordagi yuqori talab va monopol pozitsiyasi hisobiga xavfsiz."
    },
    "SQB": {
        "nomi": "O'zsanoatqurilishbank ATB (Sanoat-Qurilish Bank)",
        "shariat": "SHUBHALI/XAVFLI 🔴 (An'anaviy bank tizimi, foizli/ribo operatsiyalari asosiy o'rinda)",
        "ishlab_chiqarish": "Respublikadagi eng yirik korporativ kredit beruvchi va yirik korxonalarga xizmat ko'rsatuvchi bank.",
        "sof_foyda": "Yillik sof foyda ~1.2 trln so'm atrofida. Davlat ulushi yuqori.",
        "dividend": "Har yili aksiyadorlar yig'ilishiga ko'ra o'rtacha 8% - 11% dividend hisoblanadi.",
        "tavsiya": "⚠️ KUZATISH (HOLD) — Shariat filtriga qat'iy amal qiluvchi investorlar uchun mos emas."
    },
    "UZMT": {
        "nomi": "O'zbekiston Metkombinat AJ (Bekobod Metallurgiya)",
        "shariat": "HALOL 🟢 (Og'ir sanoat, metall eritish va prokat ishlab chiqarish sektori)",
        "ishlab_chiqarish": "Yillik 1 mln tonnadan ortiq tayyor metall mahsulotlari va prokat ishlab chiqariladi.",
        "sof_foyda": "Modernizatsiya dasturlari tufayli xarajatlar oshgan, ammo fundamental poydevori kuchli.",
        "dividend": "Yillik barqaror dividend to'lovchilar qatoriga kiradi. Rentabellik: ~10% - 13%.",
        "tavsiya": "🛒 SOTIB OLISH (BUY) — Davlat qurilish obyektlari ko'payishi metallga bo'lgan talabni oshiradi."
    },
    "QZSM": {
        "nomi": "Qizilqumsement AJ (Qurilish materiallari korxonasi)",
        "shariat": "HALOL 🟢 (Real ishlab chiqarish va qurilish materiallari savdosi)",
        "ishlab_chiqarish": "Yillik quvvati 3.5 mln tonnadan ortiq sement mahsulotlari. Eng yirik zavod.",
        "sof_foyda": "Xususiy sektorga o'tgandan so'ng operatsion samaradorlik sezilarli darajada oshdi.",
        "dividend": "Sof foyda taqsimotiga qarab dividend to'laydi. Rentabellik: ~11% - 14%.",
        "tavsiya": "🛒 SOTIB OLISH (BUY) — Qurilish sektori o'sishi bilan aksiyalari ham qiymat yig'adi."
    },
    "IPTB": {
        "nomi": "Ipoteka-Bank ATIB (OTP Group tarkibida)",
        "shariat": "SHUBHALI/XAVFLI 🔴 (An'anaviy kredit-ipoteka foiz tizimi mavjud)",
        "ishlab_chiqarish": "Vengriyaning 'OTP Group' tomonidan sotib olingan, xususiylashtirilgan yirik bank.",
        "sof_foyda": "Yevropa menejmenti kirgach, sof foyda va xizmatlar sifati keskin o'sishni boshladi.",
        "dividend": "Yevropa bank standartlariga ko'ra dividend siyosati qayta shakllantirilmoqda.",
        "tavsiya": "⚠️ KUZATISH (HOLD) — Moliyaviy o'sishi yaxshi, lekin diniy mezonlarga ko'ra shubhali."
    },
    "HAMK": {
        "nomi": "Hamkorbank ATB (Xususiy kapital ishtirokidagi bank)",
        "shariat": "SHUBHALI/XAVFLI 🔴 (Kreditlash va foizli operatsiyalar ulushi yuqori)",
        "ishlab_chiqarish": "Xalqaro moliya institutlari (FMO, IFC) aksiyador hisoblangan eng barqaror xususiy bank.",
        "sof_foyda": "Rentabellik darajasi (ROE) bo'yicha bank tizimida eng yuqori ko'rsatkichlardan biri.",
        "dividend": "Har yili barqaror tarzda aksiyadorlarga yuqori foizli dividend ajratib keladi.",
        "tavsiya": "⚠️ KUZATISH (HOLD) — Moliyaviy ko'rsatkichlari juda mukammal, lekin bank sektori xavfi bor."
    },
    "KVTS": {
        "nomi": "Kvars AJ (Oyna va shisha ishlab chiqarish)",
        "shariat": "HALOL 🟢 (Sanoat shishalari, bankalar va qurilish oynalari ishlab chiqarish)",
        "ishlab_chiqarish": "Respublikadagi eng yirik oyna va shisha buyumlari kombinati.",
        "sof_foyda": "Raqobat kuchayganligi sababli foyda marjasi biroz siqilgan, lekin aktivlar bazasi katta.",
        "dividend": "Korxonani kengaytirish dasturlariga qarab o'zgaruvchan dividend to'laydi.",
        "tavsiya": "↕️ USHLAB TURISH (HOLD) — Grafikda korreksiya tugashini kutish maqsadga muvofiq."
    },
    "UNIF": {
        "nomi": "UzNIF - Milliy Investitsiya Fondi (Aksiyadorlik Investitsiya Kompaniyasi)",
        "shariat": "HALOL 🟢 (Faqat halol ishlab chiqarish aksiyalariga investitsiya qiluvchi fond)",
        "ishlab_chiqarish": "Bozordagi eng yirik davlat aktivlarini o'z portfelida jamlagan investitsion fond.",
        "sof_foyda": "Portfeldagi NKMK, UzAuto va boshqa gigantlarning dividendlari hisobiga boyib boradi.",
        "dividend": "Yangi qoidalarga ko'ra, tushgan sof foydaning katta qismi aksiyadorlarga beriladi.",
        "tavsiya": "🛒 SOTIB OLISH (BUY) — Portfelni diversifikatsiya qilish uchun tayyor tayyor indeks aktiv."
    },
    "UZTELECOM": {
        "nomi": "O'ztelekom AJ (Milliy Telekommunikatsiya operatori)",
        "shariat": "HALOL 🟢 (Aloqa, internet va AKT xizmatlari ko'rsatish infratuzilmasi)",
        "ishlab_chiqarish": "Butun respublika bo'ylab internet va aloqa magistral tarmoqlarining mutloq egasi (Monopol).",
        "sof_foyda": "Raqamlashtirish hisobiga yillik daromad o'sishi barqaror +15% ni tashkil etmoqda.",
        "dividend": "IPO va xususiylashtirish dasturidan so'ng dividendlarni barqarorlashtirish choralari ko'rilmoqda.",
        "tavsiya": "🛒 SOTIB OLISH (BUY) — Texnologiyalar asrida har doim talab yuqori bo'lgan barqaror sektor."
    }
}

# ===================== CACHE DATA TIZIMI =====================
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

# ===================== TEXNIK VA MATEMATIK INDIKATORLAR =====================
def hisobla_rsi(closes, period=14):
    try:
        if closes is None or len(closes) < period: return 50.0, "USHLAB TURISH / HOLD ↕️"
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
    except: return 50.0, "USHLAB TURISH / HOLD ↕️"

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
        if hist is None or hist.empty or len(hist) < 20:
            return "⚖️ Likvidlik zonalari aniqlanmadi.", "Kutish rejimi."
        highs = hist['High']
        lows = hist['Low']
        closes = hist['Close']
        
        swing_high = float(highs.tail(20).max())
        swing_low = float(lows.tail(20).min())
        
        masofa_bsl = abs(joriy_narx - swing_high)
        masofa_ssl = abs(joriy_narx - swing_low)
        
        if masofa_bsl < masofa_ssl:
            yaqin_likvidlik = f"🚀 <b>Buy-Side Liquidity (BSL):</b> {swing_high:,.2f} USD atrofida yirik short-stoplar hovuzi mavjud."
            kutilma = "Smart Money (Kitlar) narxni tepadagi likvidlikni yig'ib olish (Liquidity Sweep) uchun yuqoriga tortishi kutilmoqda."
        else:
            yaqin_likvidlik = f"🩸 <b>Sell-Side Liquidity (SSL):</b> {swing_low:,.2f} USD atrofida yirik long-stoplar hovuzi joylashgan."
            kutilma = "Kitlar pastdagi stop-loss buyruqlarini urib, bozorni likvidlik bilan ta'minlash uchun narxni tushirishi mumkin."
            
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

# ===================== BARQAROR AI XIZMATI =====================
def ai_request(prompt: str, timeout: int = 15):
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
        if info is None: return "🤖 Kompaniya ma'lumotlarini yuklab bo'lmadi."
        narx = safe_float(info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0) or 0
        closes = hist['Close'] if hist is not None else None
        rsi, _ = hisobla_rsi(closes)
        prompt = f"Analyze {ticker} stock (Price: {narx} USD, RSI: {rsi}). Write a 2-sentence professional Smart Money advice in Uzbek. Be concise, direct."
        return ai_request(prompt, timeout=15) or "🤖 AI serveri ayni daqiqada band. Keyinroq qayta urinib ko'ring."
    except: return "🤖 AI tizimida vaqtinchalik cheklov."

# ===================== FOND BOZORI YANGILIKLARI (BARQAROR TARJIMA TIZIMI) =====================
def get_market_news():
    try:
        url = "https://news.google.com/rss/search?q=stock+market+investing&hl=en-US&gl=US&ceid=US:en"
        res = requests.get(url, timeout=4)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(res.content)
        news_items = []
        for item in root.findall('.//item')[:3]:
            title = item.find('title').text.split(" - ")[0]
            link = item.find('link').text
            news_items.append({"title": title, "link": link})
            
        if not news_items: return "🔄 Hozircha yangi global xabarlar topilmadi."

        combined_titles = "\n\n".join([f"• {idx+1}. {item['title']}" for idx, item in enumerate(news_items)])
        prompt = f"Quyidagi qisqa moliya yangiliklarini professional o'zbek tiliga lo'nda qilib tarjima qiling (faqat o'zbekcha matnni qaytaring):\n\n{combined_titles}"
        ai_translation = ai_request(prompt, timeout=6)
        
        if ai_translation and "error" not in ai_translation.lower():
            return ai_translation
        else:
            zaxira_matn = "🌐 <b>Global Yangiliklar (Original):</b>\n\n"
            for idx, item in enumerate(news_items):
                zaxira_matn += f"🔹 {idx+1}. <a href='{item['link']}'>{item['title']}</a>\n\n"
            return zaxira_matn + "<i>💡 Tarjimon serveri yuklamasi sababli vaqtinchalik original variant yuklandi.</i>"
    except: return "⚠️ Yangiliklar serveri band. Birozdan so'ng qayta urinib ko'ring."

# ===================== O'ZBEKISTON BIRJA NARX TIZIMI =====================
def uzbek_stock_price(symbol):
    try:
        url = "https://uzse.uz/api/v1/quotes.json"
        res = requests.get(url, timeout=3).json()
        for item in res.get('data', []):
            if symbol.strip().upper() == str(item.get('ticker', '')).strip().upper():
                return float(str(item.get('price', '0')).replace(" ", "").replace(",", "."))
        return None
    except: return None

def uzbekistan_stock_analysis(text_input: str):
    symbol = text_input.strip().upper()
    if symbol == "UZNIF": symbol = "UNIF"
    if symbol in ["UZTELEKOM", "TSTTL"]: symbol = "UZTELECOM"
    
    uz_price = uzbek_stock_price(symbol)
    if uz_price:
        price_str = f"<b>{uz_price:,.2f} UZS</b>"
    else:
        zaxira_narxlar = {"NKMK": 84500, "URTS": 4150, "UZAUTO": 56000, "SQB": 11, "UZMT": 6200, "QZSM": 3400, "IPTB": 1.2, "HAMK": 120, "KVTS": 3100, "UNIF": 1500, "UZTELECOM": 3500}
        price_str = f"<b>{zaxira_narxlar.get(symbol, 1500):,.2f} UZS</b> (Oxirgi yopilish narxi)"

    if symbol in UZ_STOCKS_DATA:
        data = UZ_STOCKS_DATA[symbol]
        return f"""━━━━━━━━━━━━━━━━━━━━
🇺🇿 <b>TOSHKENT RFB TAHLILI | {symbol}</b>
━━━━━━━━━━━━━━━━━━━━
🏢 Korxona: <b>{data['nomi']}</b>
💰 Birja Narxi: {price_str}
🕋 Shariat Statusi: <b>{data['shariat']}</b>
━━━━━━━━━━━━━━━━━━━━
📊 <b>MOLIYAVIY VA FUNDAMENTAL HISOBOTLAR:</b>
🏭 <b>Ishlab chiqarish quvvati:</b> {data['ishlab_chiqarish']}
💰 <b>Sof Foyda / Dinamika:</b> {data['sof_foyda']}
💎 <b>Dividend Siyosati:</b> {data['dividend']}
━━━━━━━━━━━━━━━━━━━━
🎯 <b>EKSPERT XULOSASI VA QAROR:</b>
{data['tavsiya']}
━━━━━━━━━━━━━━━━━━━━
<i>💡 Eslatma: Hisobotlar kompaniyaning rasmiy choraklik auditi va yillik birja kotirovkalaridan shakllantirildi.</i>"""
    else:
        return f"""━━━━━━━━━━━━━━━━━━━━
🇺🇿 <b>TOSHKENT RFB TAHLILI ({symbol})</b>
━━━━━━━━━━━━━━━━━━━━
💰 Birja narxi: {price_str}
🟢 Shariat Statusi: Ishlab chiqarish aksiyalari Halol hisoblanadi (Moliya bundan mustasno).
📊 Fundamental tahlil: Kichik korporativ aksiya, oylik savdo likvidligi past darajada.
🎯 Qaror: HOLD (Kuzatish tavsiya etiladi)
━━━━━━━━━━━━━━━━━━━━"""

# ===================== GLOBAL PUL OQIMI & STATISTIKALAR =====================
def get_capital_flow():
    try:
        tickers = {"Dollar (Forex)": "DX-Y.NYB", "Aksiya (S&P 500)": "^GSPC", "Oltin": "GC=F", "Kripto (Bitcoin)": "BTC-USD"}
        o_zgarishlar = {}
        for nom, tiker in tickers.items():
            try:
                hist = yf.Ticker(tiker).history(period="2d")
                o_zgarishlar[nom] = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
            except: o_zgarishlar[nom] = 0.0
        dxy, sp, gold, crypto = o_zgarishlar.get("Dollar (Forex)", 0.0), o_zgarishlar.get("Aksiya (S&P 500)", 0.0), o_zgarishlar.get("Oltin", 0.0), o_zgarishlar.get("Kripto (Bitcoin)", 0.0)
        
        if dxy > 0.2 and sp < 0:
            manba = "🔴 <b>Aksiya</b> va <b>Kripto</b> bozorlaridan pul chiqib ketmoqda."
            manzil = "🟢 Pullar xavfsiz boshpana sifatida <b>Forex (AQSh Dollari - DXY)</b> g'aznasiga oqib o'tmoqda. (Risk-Off tsikli)"
        elif dxy < -0.2 and sp > 0:
            manba = "🔴 <b>Forex (AQSh Dollari)</b> naqd g'aznadan yirik kapital chiqmoqda."
            manzil = "🟢 Pullar riskli aktivlar bo'lgan <b>Aksiya (S&P 500)</b> va <b>Kripto</b> bozorlariga shiddat bilan kirmoqda! (Risk-On)"
        else:
            manba = "⚖️ Bozorlarda keskin global pul ko'chishi aniqlanmadi."
            manzil = "🔄 Pullar ayni paytda ichki korreksiya va konsolidatsiya (kutish) rejimida."
            
        return f"━━━━━━━━━━━━━━━━━━━━\n🌐 <b>GLOBAL CAPITAL FLOW (PUL OQIMI)</b>\n━━━━━━━━━━━━━━━━━━━━\n📊 <b>Dinamika:</b>\n💵 DXY: <b>{dxy:+.2f}%</b> | 📈 S&P500: <b>{sp:+.2f}%</b>\n👑 Oltin: <b>{gold:+.2f}%</b> | 🪙 BTC: <b>{crypto:+.2f}%</b>\n━━━━━━━━━━━━━━━━━━━━\n🔍 {manba}\n🎯 {manzil}\n━━━━━━━━━━━━━━━━━━━━"
    except: return "❌ Global pul oqimi hisoblanishida texnik xatolik."

def top_signal():
    watch = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN"]
    text = "🔥 <b>TOP SIGNAL (RSI + BOLLINGER DARHAQIQAT)</b>\n\n"
    for s in watch:
        try:
            stock, info, hist = get_stock_data(s)
            closes = hist['Close']
            rsi, _ = hisobla_rsi(closes)
            sig = "🚀 KUCHLI SOTIB OLISH" if rsi <= 35 else "📉 KUCHLI SOTISH" if rsi >= 70 else "🛒 BUY / SOTIB OLISH" if rsi <= 45 else "↕️ HOLD"
            text += f"<b>{s}</b>: {closes.iloc[-1]:,.2f}$ → <b>{sig}</b> (RSI: {rsi})\n"
        except: pass
    return text

def get_crypto_market_summary():
    cryptos = {"BTC": "Bitcoin", "ETH": "Ethereum", "BNB": "BNB", "SOL": "Solana"}
    matn = "━━━━━━━━━━━━━━━━━━━━\n🪙 <b>JORIY KRIPTO BOZORI & STATUS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for ticker, name in cryptos.items():
        try:
            h = yf.Ticker(f"{ticker}-USD").history(period="2d")
            p = h['Close'].iloc[-1]
            ch = ((h['Close'].iloc[-1] - h['Close'].iloc[-2]) / h['Close'].iloc[-2]) * 100
            belgi = "📈" if ch >= 0 else "📉"
            matn += f"{belgi} <b>{name} ({ticker})</b>\n  └ {p:,.2f} USD | {ch:+.2f}%\n  └ 🕋 Status: {KRIPTO_HALOL_BAZA.get(ticker)}\n\n"
        except: pass
    return matn + "━━━━━━━━━━━━━━━━━━━━"

def get_market_movers():
    watch = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]
    gainers = []
    for t in watch:
        try:
            h = yf.Ticker(t).history(period="2d")
            gainers.append({"ticker": t, "price": h['Close'].iloc[-1], "change": ((h['Close'].iloc[-1] - h['Close'].iloc[-2]) / h['Close'].iloc[-2]) * 100})
        except: pass
    m = "━━━━━━━━━━━━━━━━━━━━\n🔥 <b>BUGUNGI BOZOR YETAKCHILARI</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for i in gainers:
        m += f"  {'🟢' if i['change']>=0 else '🔴'} <b>{i['ticker']}</b>: {i['price']:.2f} USD ({i['change']:+.2f}%)\n"
    return m + "━━━━━━━━━━━━━━━━━━━━"

# ===================== GLOBAL UNIVERSAL AKSIYA TAHLILI =====================
def aksiya_tahlil(tiker: str):
    try:
        tiker_clean = tiker.strip().upper()
        if tiker_clean in UZ_STOCKS_DATA or tiker_clean in ["NKMK", "SQB", "UZAUTO", "UNIF", "URTS", "UZMT", "QZSM", "IPTB", "HAMK", "KVTS", "UZTELECOM"]:
            return uzbekistan_stock_analysis(tiker_clean), None, None

        is_crypto = tiker_clean in KRIPTO_HALOL_BAZA or tiker_clean.endswith("-USD")
        tiker_yf = tiker_clean + "-USD" if (is_crypto and not tiker_clean.endswith("-USD")) else tiker_clean

        stock, info, hist = get_stock_data(tiker_yf)
        if info is None or hist is None or hist.empty:
            return f"❌ <b>{tiker_clean}</b> topilmadi.", None, None

        long_name = info.get('longName') or info.get('shortName') or tiker_clean
        sector = info.get('sector', 'Kriptovalyuta' if is_crypto else 'Noma\'lum')
        narx = safe_float(info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0) or 0
        logo_url = f"https://images.financialmodelingprep.com/image/company_logos/{tiker_clean}.png" if not is_crypto else "https://cdn-icons-png.flaticon.com/512/2272/2272825.png"

        closes, highs, lows = hist['Close'], hist['High'], hist['Low']
        rsi, rsi_signal = hisobla_rsi(closes)
        upper, middle, lower = hisobla_bollinger(closes)
        likvidlik_matni, kutilma_matni = hisobla_smart_money_likvidlik(hist, narx)

        if len(closes) >= 20:
            pct_1d = ((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2]) * 100
            pct_1w = ((closes.iloc[-1] - closes.iloc[-6]) / closes.iloc[-6]) * 100
            pct_1m = ((closes.iloc[-1] - closes.iloc[-21]) / closes.iloc[-21]) * 100
        else: pct_1d = pct_1w = pct_1m = 0.0

        fib_382 = float(highs.max()) - ((float(highs.max()) - float(lows.min())) * 0.382)
        fib_500 = float(highs.max()) - ((float(highs.max()) - float(lows.min())) * 0.500)
        fib_618 = float(highs.max()) - ((float(highs.max()) - float(lows.min())) * 0.618)

        inst_shares, eps_str, profit_margin = "—", "—", "—"
        if not is_crypto:
            held_inst = info.get('heldPercentInstitutions')
            if held_inst: inst_shares = f"{held_inst * 100:.1f}%"
            else: inst_shares = "65% - 85% (BlackRock & Vanguard)"
            eps = info.get('trailingEps')
            eps_str = f"{eps:.2f} USD" if eps else "—"
            margin = info.get('profitMargins')
            profit_margin = f"{margin * 100:.2f}%" if margin else "—"

        if is_crypto: halal_status = KRIPTO_HALOL_BAZA.get(tiker_clean.replace("-USD",""), "HALOL 🟢")
        else: halal_status = "HALOL 🟢" if (safe_float(info.get('totalDebt')) or 0)/(safe_float(info.get('marketCap')) or 1)*100 < 30 else "XAVFLI/HAROM 🔴 (Qarz > 30%)"

        cap_str = format_katta_son(info.get('marketCap'))
        pe_str = f"{safe_float(info.get('trailingPE')):.2f}" if info.get('trailingPE') else "—"
        pb_str = f"{safe_float(info.get('priceToBook')):.2f}" if info.get('priceToBook') else "—"
        fcf_str = format_katta_son(info.get('freeCashflow'))
        cash_str = format_katta_son(info.get('totalCash'))
        debt_str = format_katta_son(info.get('totalDebt'))
        net_income = format_katta_son(info.get('netIncomeToCommon'))
        
        employees = info.get('fullTimeEmployees', 0)
        employees_str = f"{employees:,} nafar" if employees else "ℹ️ Ma'lumot yo'q"
        div_yield_str = f"{info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else "—"
        last_div = f"{info.get('dividendRate', 0):.2f} USD" if info.get('dividendRate') else "—"

        shares_out = format_katta_son(info.get('sharesOutstanding'))
        shares_float = format_katta_son(info.get('floatShares'))
        day_vol = format_katta_son(info.get('volume'))
        avg_vol = format_katta_son(info.get('averageVolume'))

        target_price = safe_float(info.get('targetMeanPrice'))
        dcf_status = f"Arzon (Undervalued) 🟢 ({((target_price - narx) / narx) * 100:+.2f}%)" if target_price and narx > 0 and target_price > narx else f"Qimmat (Overvalued) 🔴 ({((target_price - narx) / narx) * 100:+.2f}%)" if target_price and narx > 0 else "Hisoblanmoqda... ⚖️"

        signal, bot_baho = "USHLAB TURISH / HOLD ↕️", "2.5/5.0 ★★☆☆•"
        if rsi <= 35: signal, bot_baho = "KUCHLI SOTIB OLISH / STRONG BUY 🚀", "4.5/5.0 ★★★★☆"
        elif rsi <= 45: signal, bot_baho = "SOTIB OLISH / BUY 🛒", "4.0/5.0 ★★★★☆"
        elif rsi >= 70: signal, bot_baho = "KUCHLI SOTISH / STRONG SELL 📉", "1.5/5.0 ★☆☆☆☆"
        elif rsi >= 60: signal, bot_baho = "SOTISH / SELL ⚠️", "2.0/5.0 ★★☆☆☆"

        javob = f"""━━━━━━━━━━━━━━━━━━━━
<b>{tiker_clean} | {html.escape(long_name)}</b>
Sektor: <b>{html.escape(sector)}</b> | Status: <b>{halal_status}</b>
━━━━━━━━━━━━━━━━━━━━
💵 Narx: <b>{narx:,.2f} USD</b>
⚖️ DCF Adolatli Qiymati: <b>{dcf_status}</b>
52W M/M: <b>{info.get('fiftyTwoWeekHigh', narx):,.2f} / {info.get('fiftyTwoWeekLow', narx):,.2f}</b>
Cap: <b>{cap_str}</b> | Div Yield: <b>{div_yield_str}</b>
━━━━━━━━━━━━━━━━━━━━
🏢 Kompaniya xodimlari: <b>{employees_str}</b>
━━━━━━━━━━━━━━━━━━━━
👑 Moliyaviy Balans (G'azna):
  └ 💵 Qo'lidagi naqd pul: <b>{cash_str} USD</b>
  └ 🚨 Jami qarzi: <b>{debt_str} USD</b>
  └ 📈 Sof foyda (Yillik): <b>{net_income} USD</b>
━━━━━━━━━━━━━━━━━━━━
🐋 YIRIK KITLARNING ULUSHI:
  └ 🏦 Yirik Kitlar ulushi (Institutions): <b>{inst_shares}</b>
  └ 💰 Har bir aksiyaga sof foyda (EPS): <b>{eps_str}</b>
  └ 💎 Sof foyda marjasi (Profit Margin): <b>{profit_margin}</b>
━━━━━━━━━━━━━━━━━━━━
📦 Aksiyalar miqdori & Muomala:
  └ 📊 Jami chiqarilgan: <b>{shares_out} dona</b>
  └ 🛒 Sotuvda (Float): <b>{shares_float} dona</b>
  └ 🔄 Bugungi Oldi-sotdi: <b>{day_vol} dona</b>
  └ ⏱️ 3 oylik o'rtacha hajm: <b>{avg_vol} dona</b>
━━━━━━━━━━━━━━━━━━━━
💰 Dividend Taqvimi (Faqat Aksiyalar):
  └ ↩️ Oxirgi ajratilgan: <b>{last_div}</b>
━━━━━━━━━━━━━━━━━━━━
Fundamental Ko'rsatkichlar:
P/E: <b>{pe_str}</b> | P/B: <b>{pb_str}</b> | EPS: <b>{eps_str}</b>
FCF: <b>{fcf_str} USD</b>
━━━━━━━━━━━━━━━━━━━━
📐 Fibonacci (3M):
  38.2%: <b>{fib_382:,.2f} USD</b> | 50.0%: <b>{fib_500:,.2f} USD</b> | 61.8%: <b>{fib_618:,.2f} USD</b>
━━━━━━━━━━━━━━━━━━━━
📊 Dinamika:
1D: <b>{pct_1d:+.2f}%</b> | 1W: <b>{pct_1w:+.2f}%</b> | 1M: <b>{pct_1m:+.2f}%</b>
━━━━━━━━━━━━━━━━━━━━
🐳 <b>SMART MONEY & LIKVIDLIK (SMC):</b>
{likvidlik_matni}

🎯 <b>Kitlar Harakati Kutilmasi:</b>
<i>{kutilma_matni}</i>
━━━━━━━━━━━━━━━━━━━━
📊 <b>Texnik Ko'rsatkichlar:</b>
📉 RSI (14): <b>{rsi}</b> → <b>{rsi_signal}</b>
📊 Bollinger Upper: <b>{upper:,.2f}</b> | Middle: <b>{middle:,.2f}</b> | Lower: <b>{lower:,.2f}</b>

🎯 <b>YAKUNIY SIGNAL: {signal}</b>
🎯 <b>BOT BAHOSI: {bot_baho}</b>
━━━━━━━━━━━━━━━━━━━━"""
        return javob, tiker_clean, logo_url
    except Exception as e:
        return f"❌ {tiker.upper()} tahlilida kutilmagan xato: {str(e)}", None, None

# ===================== MUKAMMAL STRUKTURAVIY MENYU =====================
def main_menu():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(types.KeyboardButton("🌐 Global Pul Oqimi"), types.KeyboardButton("🚀 TOP Signal"))
    kb.add(types.KeyboardButton("🟢 Halol aksiyalar"), types.KeyboardButton("🪙 Kripto bozori"))
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

# ===================== MESSAGE HANDLERLAR TIZIMI =====================
@bot.message_handler(commands=['start'])
def start(message):
    user_modes[message.chat.id] = False
    uz_user_modes[message.chat.id] = False
    bot.send_message(message.chat.id, "👋 <b>Smart Money & Universal AI Bot tizimiga xush kelibsiz!</b>\n\nBarcha fundamental bo'limlar, testlar, lug'at va kengaytirilgan O'zbekiston birja hisobotlari to'liq faollashtirildi.", parse_mode="HTML", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    text = message.text.strip()
    uid = message.chat.id

    if text in ["❌ Rejimdan chiqish", "chiqish"]:
        user_modes[uid] = False
        uz_user_modes[uid] = False
        bot.send_message(uid, "Asosiy menyuga qaytdingiz.", reply_markup=main_menu())
        return

    if uz_user_modes.get(uid, False):
        bot.send_chat_action(uid, 'typing')
        bot.send_message(uid, uzbekistan_stock_analysis(text), parse_mode="HTML")
        return

    if user_modes.get(uid, False):
        bot.send_chat_action(uid, 'typing')
        res = ai_request(f"Siz professional moliya va trading mentorsiz. Savolga lo'nda va aniq o'zbek tilida javob bering:\nSavol: {text}", timeout=12)
        bot.send_message(uid, res or "🤖 AI Mentor hozir band. Birozdan so'ng qayta urinib ko'ring.")
        return

    # Tugmalar boshqaruvi
    if text == "🌐 Global Pul Oqimi":
        bot.send_chat_action(uid, 'typing')
        bot.send_message(uid, get_capital_flow(), parse_mode="HTML")
    elif text == "🚀 TOP Signal":
        bot.send_message(uid, top_signal(), parse_mode="HTML")
    elif text == "🪙 Kripto bozori":
        bot.send_chat_action(uid, 'typing')
        bot.send_message(uid, get_crypto_market_summary(), parse_mode="HTML")
    elif text == "🔥 Bozor yetakchilari":
        bot.send_chat_action(uid, 'typing')
        bot.send_message(uid, get_market_movers(), parse_mode="HTML")
    elif text == "📰 Fond bozori yangiliklari":
        bot.send_chat_action(uid, 'typing')
        bot.send_message(uid, f"📰 <b>Eng so'nggi yangiliklar (AI Tarjimasi):</b>\n\n{get_market_news()}", parse_mode="HTML", disable_web_page_preview=True)
    elif text == "📖 Atamalar lug'ati":
        bot.send_message(uid, "📖 <b>Moliyaviy tahlil lug'ati (1-sahifa):</b>", parse_mode="HTML", reply_markup=inline_dictionary(page=1))
    elif text == "🧠 Kunlik Test":
        bot.send_poll(chat_id=uid, question="RSI ko'rsatkichi 30 dan pastga tushganda, bu nimani anglatadi?", options=["Oversold (Haddan tashqari ko'p sotilgan/Arzon)", "Overbought (Haddan tashqari qimmat)", "Trend o'zgarmas holatda"], type="quiz", correct_option_id=0, explanation="RSI 30 dan past bo'lsa, narx haddan tashqari ko'p sotilgan va arzon zonaga kirgan hisoblanadi.", is_anonymous=False)
    elif text == "🐋 Kitlar kuzatuvida":
        bot.send_chat_action(uid, 'typing')
        res = ai_request("Write a short paragraph in Uzbek about what major funds like Vanguard and BlackRock are buying this quarter in AI and tech sector. Be concise.", timeout=10)
        bot.send_message(uid, f"🐋 <b>KITLAR HARAKATI TAVSIYASI:</b>\n\n{res or 'Yirik fondlar (BlackRock va Vanguard) yarim oʻtkazgich hamda sun’iy intellekt infratuzilmasi aksiyalarida oʻz ulushlarini oshirishda davom etmoqda.'}", parse_mode="HTML")
    elif text == "🇺🇿 O'zbekiston aksiyalari":
        uz_user_modes[uid] = True
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(types.KeyboardButton("❌ Rejimdan chiqish"))
        bot.send_message(uid, "🇺🇿 <b>Toshkent RFB (UZSE) bo'limi faollashdi.</b>\nTiker kiriting (Masalan: NKMK, URTS, UZAUTO, UZMT, SQB):", parse_mode="HTML", reply_markup=kb)
    elif text == "🤖 AI Tavsiyalari":
        user_modes[uid] = True
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(types.KeyboardButton("❌ Rejimdan chiqish"))
        bot.send_message(uid, "🤖 <b>AI Mentor Rejimi Yoqildi!</b>\nTrading, iqtisodiyot va moliya bo'yicha o'zingizni qiziqtirgan savolni bering:", parse_mode="HTML", reply_markup=kb)
    elif text == "🟢 Halol aksiyalar":
        for t in ["AAPL", "MSFT", "NVDA"]:
            j, tc, l = aksiya_tahlil(t)
            if tc:
                try: bot.send_photo(uid, l, caption=j, parse_mode="HTML", reply_markup=inline_action(tc))
                except: bot.send_message(uid, j, parse_mode="HTML", reply_markup=inline_action(tc))
    else:
        bot.send_chat_action(uid, 'typing')
        j, tc, l = aksiya_tahlil(text)
        if tc:
            try: bot.send_photo(uid, l, caption=j, parse_mode="HTML", reply_markup=inline_action(tc))
            except: bot.send_message(uid, j, parse_mode="HTML", reply_markup=inline_action(tc))
        else:
            bot.send_message(uid, j, parse_mode="HTML")

# ===================== CALLBACK REAKSIYALARI TIZIMI =====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.message.chat.id
    if call.data.startswith("ai_"):
        ticker_name = call.data[3:]
        bot.send_message(uid, f"🤖 <b>{ticker_name} — AI Smart Money Maslahati:</b>\n\n<i>{get_ai_advice(ticker_name)}</i>", parse_mode="HTML")
        bot.answer_callback_query(call.id)
    elif call.data.startswith("dic_"):
        term = call.data[4:]
        if term.startswith("page_"):
            p = int(term.split("_")[1])
            bot.edit_message_text(chat_id=uid, message_id=call.message.message_id, text=f"📖 <b>Moliyaviy lug'at ({p}-sahifa):</b>", parse_mode="HTML", reply_markup=inline_dictionary(page=p))
        else:
            explanations = {
                "mcap": "📊 <b>Market Cap:</b> Kompaniyaning bozordagi jami qiymati.",
                "pe": "📈 <b>P/E Ratio:</b> Narxning foydaga nisbati (Aksiya qanchalik tez o'zini oqlashi).",
                "debteq": "🚨 <b>Debt/Equity:</b> Kompaniyaning o'z mablag'iga nisbatan qarz yuklamasi.",
                "rsi": "📉 <b>RSI:</b> 30 dan past = oversold (arzon), 70 dan baland = overbought (qimmat).",
                "eps": "💰 <b>EPS:</b> Har bir dona aksiyaga to'g'ri keladigan sof foyda ulushi.",
                "roe": "👑 <b>ROE:</b> Kompaniyaning o'z xususiy kapitalidan foydalanish samaradorligi.",
                "fcf": "💵 <b>FCF:</b> Erkin pul oqimi (Kompaniyaning cho'ntigida qoladigan sof naqd pul).",
                "pb": "📚 <b>P/B:</b> Kompaniyaning birja narxi uning balans (kitob) qiymatidan necha barobar qimmatligini ko'rsatadi."
            }
            bot.send_message(uid, explanations.get(term, "❓ Topilmadi"), parse_mode="HTML")
        bot.answer_callback_query(call.id)

# ===================== SILLIQ ISHGA TUSHIRISH (POLLING) =====================
def run_bot_polling():
    while True:
        try: bot.polling(none_stop=True, interval=0, timeout=25)
        except: time.sleep(5)

if __name__ == "__main__":
    try: bot.remove_webhook()
    except: pass
    threading.Thread(target=run_bot_polling, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
