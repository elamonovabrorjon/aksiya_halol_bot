      import telebot
from telebot import types
import yfinance as yf
import html
from functools import lru_cache
import threading
from flask import Flask
import time

# ===================== VEB-SERVER (RENDER LIVE STATUS) =====================
app = Flask('')

@app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlamoqda!"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# ===================== SOZLAMALAR VA ASLIY TOKEN =====================
TOKEN = '8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8'
bot = telebot.TeleBot(TOKEN)

@lru_cache(maxsize=150)
def get_stock_data(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")
        return stock, info, hist
    except:
        return None, None, None

# ===================== TEXNIK INDIKATORLAR =====================
def hisobla_rsi(closes, period=14):
    try:
        if closes is None or len(closes) < period:
            return "—", "HOLD ↕️"
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period-1, adjust=False).mean()
        avg_loss = loss.ewm(com=period-1, adjust=False).mean()
        rs = avg_gain / avg_loss.where(avg_loss != 0, 1)
        rsi = 100 - (100 / (1 + rs))
        current_rsi = round(rsi.iloc[-1], 2)
        
        if current_rsi >= 70: return current_rsi, "SELL 📉"
        elif current_rsi <= 30: return current_rsi, "BUY 📈"
        else: return current_rsi, "HOLD ↕️"
    except:
        return "—", "HOLD ↕️"

# ===================== ASOSIY PROFESSIONAL TAHLIL KODI =====================
def aksiya_tahlil(tiker: str):
    try:
        tiker_clean = tiker.strip().upper()
        stock, info, hist = get_stock_data(tiker_clean)
        
        if info is None or hist is None or hist.empty:
            return f"❌ <b>{tiker_clean}</b> bo'yicha ma'lumot topilmadi.", None

        # 1. Umumiy va Profil Ma'lumotlari
        narx = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 0)
        valyuta = info.get('currency', 'USD')
        long_name = info.get('longName') or info.get('shortName') or tiker_clean
        sector = info.get('sector', 'Noma\'lum')
        country = info.get('country', 'Noma\'lum')
        summary = info.get('longBusinessSummary', 'Kompaniya haqida ma\'lumot mavjud emas.')
        if len(summary) > 180:
            summary = summary[:180] + "..."

        # Ishchilar soni
        employees = info.get('fullTimeEmployees')
        employees_str = f"{employees:,}" if employees else "—"
        
        # Narx o'zgarishlari
        closes = hist['Close']
        if len(closes) >= 22:
            change_1d = round(((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2]) * 100, 2)
            change_1w = round(((closes.iloc[-1] - closes.iloc[-6]) / closes.iloc[-6]) * 100, 2)
            change_1m = round(((closes.iloc[-1] - closes.iloc[-21]) / closes.iloc[-21]) * 100, 2)
        else:
            change_1d = change_1w = change_1m = 0

        # Texnik trend tahlili
        rsi, rsi_signal = hisobla_rsi(closes)
        ma50 = closes.iloc[-50:].mean() if len(closes) >= 50 else narx
        ma200 = closes.iloc[-200:].mean() if len(closes) >= 200 else narx
        
        if narx > ma50 and ma50 > ma200:
            trend_status = "O'sish (Bullish) 📈"
            trend_score = 1
        elif narx < ma50 and ma50 < ma200:
            trend_status = "Tushish (Bearish) 📉"
            trend_score = -1
        else:
            trend_status = "Yassilanish (Side/Flat) ↕️"
            trend_score = 0

        recommendation = info.get('recommendationKey', 'Noma\'lum').upper().replace('_', ' ')

        # Shariat filtri (AAOIFI)
        qarz = info.get('totalDebt', 0)
        market_cap = info.get('marketCap', 1)
        daromad = info.get('totalRevenue', 0)
        debt_ratio = (qarz / market_cap) * 100 if market_cap else 0
        
        if debt_ratio < 30: halal_status = "🟢 HALOL"
        elif debt_ratio <= 40: halal_status = "🟡 SHUBHALI"
        else: halal_status = "🔴 HAROM"

        # Katta sonlarni Trillion
