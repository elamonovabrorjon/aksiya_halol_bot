"""
╔══════════════════════════════════════════════════════════╗
║          AKSIYA HALOL BOT — ULTIMATE EDITION            ║
║  Fundamental + Texnik + Siyosiy tahlil                  ║
║  O'zbekiston + Xalqaro bozor                            ║
╚══════════════════════════════════════════════════════════╝

O'rnatish:
    pip install pyTelegramBotAPI yfinance matplotlib pandas numpy requests

Ishga tushirish:
    python aksiya_halol_bot_ultimate.py
"""

import telebot
from telebot import types
import yfinance as yf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import requests
import os
import time
import logging
from datetime import datetime, timedelta
import zoneinfo

# ──────────────────────────────────────────────
#  SOZLAMALAR
# ──────────────────────────────────────────────
TOKEN          = "8781183838:AAFmgLoz6Bb8LlA-50lVAdAbNvhBCWO3sm0"
QUIVER_API_KEY = "YOUR_QUIVER_API_KEY"   # quiverquant.com dan oling (bepul)
ADMIN_ID       = 0                        # O'z Telegram ID raqamingiz

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
log = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ──────────────────────────────────────────────
#  O'ZBEKISTON BOZORI MA'LUMOTLAR BAZASI
#  Manba: TRFB.UZ ochiq hisobotlar (har chorak yangilang)
# ──────────────────────────────────────────────
UZ_STOCKS = {
    "UZAUTO": {
        "name": "UzAuto Motors", "sector": "Avtomobilsozlik",
        "price": 18500, "shares": 120_000_000,
        "revenue": 42_000_000_000_000, "net_income": 3_100_000_000_000,
        "total_assets": 28_000_000_000_000, "total_debt": 6_500_000_000_000,
        "equity": 21_500_000_000_000, "fcf": 1_200_000_000_000,
        "dividend": 500, "employees": 9500, "revenue_growth": 0.15,
        "description": "O'zbekistondagi eng yirik avtomobil ishlab chiqaruvchi"
    },
    "UZKIMYOSANOAT": {
        "name": "O'zkimyosanoat", "sector": "Kimyo",
        "price": 2150, "shares": 350_000_000,
        "revenue": 8_500_000_000_000, "net_income": 420_000_000_000,
        "total_assets": 12_000_000_000_000, "total_debt": 3_200_000_000_000,
        "equity": 8_800_000_000_000, "fcf": 180_000_000_000,
        "dividend": 0, "employees": 12000, "revenue_growth": 0.08,
        "description": "Kimyo sanoati davlat konglomerati"
    },
    "ALGM": {
        "name": "Alg'am-Rosti", "sector": "Qurilish materiallari",
        "price": 4200, "shares": 80_000_000,
        "revenue": 1_200_000_000_000, "net_income": 95_000_000_000,
        "total_assets": 2_100_000_000_000, "total_debt": 480_000_000_000,
        "equity": 1_620_000_000_000, "fcf": 45_000_000_000,
        "dividend": 120, "employees": 2100, "revenue_growth": 0.05,
        "description": "Qurilish materiallari ishlab chiqarish"
    },
    "UTGAP": {
        "name": "Toshkent Yog'-Moy", "sector": "Oziq-ovqat",
        "price": 3100, "shares": 60_000_000,
        "revenue": 980_000_000_000, "net_income": 62_000_000_000,
        "total_assets": 1_400_000_000_000, "total_debt": 310_000_000_000,
        "equity": 1_090_000_000_000, "fcf": 28_000_000_000,
        "dividend": 80, "employees": 850, "revenue_growth": 0.04,
        "description": "O'simlik yog'i va moy mahsulotlari"
    },
    "ATSZ": {
        "name": "Andijon Trikotaj", "sector": "To'qimachilik",
        "price": 1850, "shares": 45_000_000,
        "revenue": 420_000_000_000, "net_income": 28_000_000_000,
        "total_assets": 680_000_000_000, "total_debt": 95_000_000_000,
        "equity": 585_000_000_000, "fcf": 12_000_000_000,
        "dividend": 50, "employees": 1200, "revenue_growth": 0.06,
        "description": "Trikotaj mahsulotlari ishlab chiqarish"
    },
    "KSPI": {
        "name": "Kaspi Bank O'zbekiston", "sector": "Bank",
        "price": 9800, "shares": 200_000_000,
        "revenue": 5_600_000_000_000, "net_income": 780_000_000_000,
        "total_assets": 38_000_000_000_000, "total_debt": 29_000_000_000_000,
        "equity": 9_000_000_000_000, "fcf": 0,
        "dividend": 200, "employees": 3800, "revenue_growth": 0.22,
        "description": "Raqamli bank va to'lov xizmatlari"
    },
    "UZMK": {
        "name": "O'zmetkombinat", "sector": "Metallurgiya",
        "price": 5400, "shares": 95_000_000,
        "revenue": 6_200_000_000_000, "net_income": 510_000_000_000,
        "total_assets": 9_800_000_000_000, "total_debt": 2_800_000_000_000,
        "equity": 7_000_000_000_000, "fcf": 220_000_000_000,
        "dividend": 150, "employees": 15000, "revenue_growth": 0.07,
        "description": "Qora metallurgiya va po'lat ishlab chiqarish"
    },
    "NAVOIYAZOT": {
        "name": "Navoiyazot", "sector": "Kimyo",
        "price": 3750, "shares": 70_000_000,
        "revenue": 2_100_000_000_000, "net_income": 180_000_000_000,
        "total_assets": 3_500_000_000_000, "total_debt": 820_000_000_000,
        "equity": 2_680_000_000_000, "fcf": 75_000_000_000,
        "dividend": 90, "employees": 5200, "revenue_growth": 0.09,
        "description": "Azot o'g'itlari va kimyo mahsulotlari"
    },
}

# ──────────────────────────────────────────────
#  YORDAMCHI FUNKSIYALAR
# ──────────────────────────────────────────────
def fmt_som(n: float) -> str:
    """Katta sonlarni o'qilishi oson formatda ko'rsatish"""
    if abs(n) >= 1e12: return f"{n/1e12:.2f} trl so'm"
    if abs(n) >= 1e9:  return f"{n/1e9:.2f} mlrd so'm"
    if abs(n) >= 1e6:  return f"{n/1e6:.2f} mln so'm"
    return f"{n:,.0f} so'm"

def fmt_usd(n: float) -> str:
    if abs(n) >= 1e12: return f"${n/1e12:.2f}T"
    if abs(n) >= 1e9:  return f"${n/1e9:.2f}B"
    if abs(n) >= 1e6:  return f"${n/1e6:.2f}M"
    return f"${n:,.2f}"

def safe_div(a, b, default=0):
    try:
        return a / b if b and b != 0 else default
    except:
        return default

# ──────────────────────────────────────────────
#  TEXNIK INDIKATORLAR (numpy bilan)
# ──────────────────────────────────────────────
def calc_rsi(prices: pd.Series, period: int = 14) -> float:
    delta = prices.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 1) if not rsi.empty else 50.0

def calc_macd(prices: pd.Series):
    ema12 = prices.ewm(span=12).mean()
    ema26 = prices.ewm(span=26).mean()
    macd  = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    hist   = macd - signal
    return round(float(macd.iloc[-1]), 4), round(float(signal.iloc[-1]), 4), round(float(hist.iloc[-1]), 4)

def calc_bollinger(prices: pd.Series, period: int = 20):
    ma  = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    upper = ma + 2 * std
    lower = ma - 2 * std
    return round(float(upper.iloc[-1]), 2), round(float(ma.iloc[-1]), 2), round(float(lower.iloc[-1]), 2)

def calc_ema(prices: pd.Series, period: int) -> float:
    return round(float(prices.ewm(span=period).mean().iloc[-1]), 2)

def calc_sma(prices: pd.Series, period: int) -> float:
    return round(float(prices.rolling(period).mean().iloc[-1]), 2)

def calc_stochastic(high, low, close, period=14):
    lowest  = low.rolling(period).min()
    highest = high.rolling(period).max()
    k = 100 * (close - lowest) / (highest - lowest + 1e-10)
    d = k.rolling(3).mean()
    return round(float(k.iloc[-1]), 1), round(float(d.iloc[-1]), 1)

def calc_atr(high, low, close, period=14) -> float:
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    return round(float(tr.rolling(period).mean().iloc[-1]), 4)

def calc_obv(close, volume) -> str:
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    trend = "📈 O'sish" if obv.iloc[-1] > obv.iloc[-5] else "📉 Pasayish"
    return trend

def get_support_resistance(prices: pd.Series):
    recent = prices.tail(60)
    support    = round(float(recent.min()), 2)
    resistance = round(float(recent.max()), 2)
    pivot = round((float(recent.iloc[-1]) + support + resistance) / 3, 2)
    return support, resistance, pivot

# ──────────────────────────────────────────────
#  TEXNIK TAHLIL NATIJASI
# ──────────────────────────────────────────────
def get_technical_analysis(ticker: str) -> str:
    try:
        data = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if data.empty:
            return f"❌ {ticker} uchun ma'lumot topilmadi."

        if hasattr(data.columns, 'levels'):
            data.columns = data.columns.get_level_values(0)

        close  = data['Close'].dropna()
        high   = data['High'].dropna()
        low    = data['Low'].dropna()
        volume = data['Volume'].dropna()
        price  = float(close.iloc[-1])

        # Indikatorlar
        rsi               = calc_rsi(close)
        macd, signal, hist = calc_macd(close)
        bb_up, bb_mid, bb_lo = calc_bollinger(close)
        ema20  = calc_ema(close, 20)
        ema50  = calc_ema(close, 50)
        ema200 = calc_ema(close, 200)
        sma50  = calc_sma(close, 50)
        stoch_k, stoch_d = calc_stochastic(high, low, close)
        atr    = calc_atr(high, low, close)
        obv_tr = calc_obv(close, volume)
        sup, res, pivot = get_support_resistance(close)

        # RSI signali
        if rsi < 30:
            rsi_sig = "🟢 OVERSOLD — Sotib olish imkoni"
        elif rsi > 70:
            rsi_sig = "🔴 OVERBOUGHT — Sotish imkoni"
        else:
            rsi_sig = "🟡 NEYTRAL zona"

        # MACD signali
        macd_sig = "🟢 BUY signal" if hist > 0 and macd > signal else "🔴 SELL signal"

        # Bollinger signali
        if price <= bb_lo:
            bb_sig = "🟢 Pastki chiziq — Qaytish mumkin"
        elif price >= bb_up:
            bb_sig = "🔴 Yuqori chiziq — Tushish mumkin"
        else:
            bb_sig = "🟡 Kanal ichida"

        # Trend (EMA)
        if price > ema20 > ema50 > ema200:
            trend_sig = "🟢 KUCHLI YUQORI TREND"
        elif price > ema50 > ema200:
            trend_sig = "🟢 YUQORI TREND"
        elif price < ema20 < ema50 < ema200:
            trend_sig = "🔴 KUCHLI PASTKI TREND"
        elif price < ema50:
            trend_sig = "🔴 PASTKI TREND"
        else:
            trend_sig = "🟡 YON TREND (Sideways)"

        # Stochastic
        if stoch_k < 20:
            stoch_sig = "🟢 OVERSOLD"
        elif stoch_k > 80:
            stoch_sig = "🔴 OVERBOUGHT"
        else:
            stoch_sig = "🟡 Neytral"

        # Umumiy signal
        buy_signals  = sum([rsi < 40, hist > 0, price < bb_mid,
                            price > ema50, stoch_k < 40])
        sell_signals = sum([rsi > 60, hist < 0, price > bb_up,
                            price < ema50, stoch_k > 60])

        if buy_signals >= 4:
            overall = "🟢 KUCHLI SOTIB OLISH"
        elif buy_signals >= 3:
            overall = "🟢 SOTIB OLISH"
        elif sell_signals >= 4:
            overall = "🔴 KUCHLI SOTISH"
        elif sell_signals >= 3:
            overall = "🔴 SOTISH"
        else:
            overall = "🟡 KUTING / NEYTRAL"

        return f"""📊 <b>{ticker} — TEXNIK TAHLIL</b>
━━━━━━━━━━━━━━━━━━━━

💹 <b>JORIY NARX: {price:.4f}</b>

📈 <b>TREND TAHLILI</b>
• EMA 20: <b>{ema20}</b>
• EMA 50: <b>{ema50}</b>
• EMA 200: <b>{ema200}</b>
• SMA 50: <b>{sma50}</b>
• Trend: <b>{trend_sig}</b>

⚡ <b>MOMENTUM INDIKATORLARI</b>
• RSI(14): <b>{rsi}</b> — {rsi_sig}
• MACD: <b>{macd:.4f}</b> | Signal: <b>{signal:.4f}</b>
• MACD Histogram: <b>{hist:.4f}</b> — {macd_sig}
• Stochastic %K: <b>{stoch_k}</b> | %D: <b>{stoch_d}</b> — {stoch_sig}

📉 <b>BOLLINGER BANDS</b>
• Yuqori: <b>{bb_up}</b>
• O'rta: <b>{bb_mid}</b>
• Pastki: <b>{bb_lo}</b>
• Signal: {bb_sig}

🎯 <b>SUPPORT & RESISTANCE</b>
• Qarshilik (Resistance): <b>{res}</b>
• Pivot: <b>{pivot}</b>
• Tayanch (Support): <b>{sup}</b>

📦 <b>BOSHQA</b>
• ATR (Volatillik): <b>{atr}</b>
• OBV Trendi: <b>{obv_tr}</b>

━━━━━━━━━━━━━━━━━━━━
🎯 <b>UMUMIY SIGNAL: {overall}</b>
⚠️ <i>Texnik tahlil — kelajakni kafolatlamaydi!</i>"""

    except Exception as e:
        log.error(f"Technical analysis error for {ticker}: {e}")
        return f"❌ Texnik tahlil xatoligi: {str(e)[:120]}"

# ──────────────────────────────────────────────
#  XALQARO FUNDAMENTAL TAHLIL
# ──────────────────────────────────────────────
def get_fundamental_analysis(ticker: str) -> str:
    try:
        ticker = ticker.strip().upper()
        stock  = yf.Ticker(ticker)
        i      = stock.info

        if not i or (not i.get('currentPrice') and not i.get('regularMarketPrice')):
            return f"❌ <b>{ticker}</b> topilmadi yoki ma'lumot yo'q."

        def s(key, default=0):
            v = i.get(key)
            return v if v is not None else default

        price      = s('currentPrice') or s('regularMarketPrice', 0)
        mkt_cap    = s('marketCap', 0)
        assets     = s('totalAssets', 1) or 1
        debt       = s('totalDebt', 0)
        equity     = s('totalStockholderEquity', 1) or 1
        fcf        = s('freeCashflow', 0)
        revenue    = s('totalRevenue', 0) or 1
        net_income = s('netIncomeToCommon', 0)

        debt_ratio  = (debt / assets) * 100
        roe         = s('returnOnEquity', 0) * 100
        roa         = s('returnOnAssets', 0) * 100
        margin      = s('profitMargins', 0) * 100
        rev_growth  = s('revenueGrowth', 0) * 100
        earn_growth = s('earningsGrowth', 0) * 100

        pe  = s('trailingPE', 'N/A')
        fpe = s('forwardPE', 'N/A')
        pb  = s('priceToBook', 'N/A')
        ps  = s('priceToSalesTrailing12Months', 'N/A')
        peg = s('pegRatio', 'N/A')
        ev_ebitda = s('enterpriseToEbitda', 'N/A')

        # DCF
        if fcf > 0:
            dcf   = (fcf * 1.07) / 0.10
            shares_out = s('sharesOutstanding', 1) or 1
            dcf_ps = dcf / shares_out
            if dcf_ps > price * 1.2:
                dcf_sig = f"✅ ARZON — DCF: {fmt_usd(dcf_ps)}/aksiya"
            elif dcf_ps < price * 0.8:
                dcf_sig = f"🔴 QIMMAT — DCF: {fmt_usd(dcf_ps)}/aksiya"
            else:
                dcf_sig = f"🟡 ADOLATLI — DCF: {fmt_usd(dcf_ps)}/aksiya"
        else:
            dcf_sig = "⚠️ FCF manfiy yoki nol"

        # Piotroski F-Score (soddalashtirilgan)
        f_score = 0
        if net_income > 0:  f_score += 1
        if roa > 0:         f_score += 1
        if fcf > 0:         f_score += 1
        if fcf > net_income: f_score += 1
        if debt_ratio < 33: f_score += 1
        if margin > 10:     f_score += 1
        if rev_growth > 5:  f_score += 1
        if roe > 15:        f_score += 1
        if earn_growth > 0: f_score += 1

        f_score_sig = (
            "🟢 KUCHLI (7-9)" if f_score >= 7 else
            "🟡 O'RTA (4-6)"  if f_score >= 4 else
            "🔴 ZAIF (0-3)"
        )

        # Halollik (AAOIFI)
        if "bank" in str(i.get('sector', '')).lower() or "financial" in str(i.get('sector', '')).lower():
            halol = "⚠️ SHUBHALI — Moliya sektori (bank/sug'urta)"
        elif debt_ratio < 33:
            halol = f"✅ HALOL — Qarz {debt_ratio:.1f}% (AAOIFI < 33%)"
        else:
            halol = f"❌ HARAM — Qarz {debt_ratio:.1f}% (AAOIFI chegarasi oshgan)"

        # Umumiy baholash
        score = sum([
            isinstance(pe, float) and 0 < pe < 20,
            isinstance(pb, float) and 0 < pb < 3,
            isinstance(peg, float) and 0 < peg < 1.5,
            roe > 15, roa > 5, margin > 10,
            rev_growth > 5, debt_ratio < 40,
            earn_growth > 0, f_score >= 7
        ])

        xulosa = (
            "🟢 KUCHLI — Sotib olish ko'rib chiqilsin" if score >= 8 else
            "🟢 IJOBIY — Yaxshi ko'rsatkichlar"       if score >= 6 else
            "🟡 O'RTA — Ehtiyotkorlik bilan"          if score >= 4 else
            "🔴 ZAIF — Risk yuqori"
        )

        return f"""🌍 <b>{ticker} — {i.get('shortName', ticker)}</b>
<b>{i.get('sector','?')} | {i.get('exchange','?')}</b>
━━━━━━━━━━━━━━━━━━━━

💰 <b>NARX VA BOZOR</b>
• Narx: <b>{fmt_usd(price)}</b>
• Bozor qiymati: <b>{fmt_usd(mkt_cap)}</b>
• 52h Yuqori: <b>{fmt_usd(s('fiftyTwoWeekHigh'))}</b>
• 52h Pastki: <b>{fmt_usd(s('fiftyTwoWeekLow'))}</b>
• Beta: <b>{s('beta','N/A')}</b>

📊 <b>BAHOLASH KOEFFITSIENTLARI</b>
• P/E (joriy): <b>{pe}</b>
• P/E (kelajak): <b>{fpe}</b>
• P/B: <b>{pb}</b>
• P/S: <b>{ps}</b>
• PEG: <b>{peg}</b>
• EV/EBITDA: <b>{ev_ebitda}</b>

📈 <b>RENTABELLIK</b>
• ROE: <b>{roe:.1f}%</b>
• ROA: <b>{roa:.1f}%</b>
• Foyda marjasi: <b>{margin:.1f}%</b>
• Daromad o'sishi: <b>{rev_growth:.1f}%</b>
• Foyda o'sishi: <b>{earn_growth:.1f}%</b>

🏦 <b>MOLIYAVIY MUSTAHKAMLIK</b>
• Jami aktivlar: <b>{fmt_usd(assets)}</b>
• Jami qarz: <b>{fmt_usd(debt)}</b>
• Qarz/Aktiv: <b>{debt_ratio:.1f}%</b>
• FCF: <b>{fmt_usd(fcf)}</b>
• Current Ratio: <b>{s('currentRatio','N/A')}</b>

💵 <b>DIVIDEND</b>
• Dividend yield: <b>{s('dividendYield',0)*100:.2f}%</b>
• Payout Ratio: <b>{s('payoutRatio',0)*100:.1f}%</b>

🧮 <b>BAHOLASH MODELLARI</b>
• DCF Tahlil: {dcf_sig}
• Piotroski F-Score: <b>{f_score}/9</b> — {f_score_sig}

👥 Xodimlar: <b>{s('fullTimeEmployees','N/A'):,}</b> | Mamlakat: <b>{i.get('country','N/A')}</b>

🕌 <b>HALOLLIK (AAOIFI):</b> {halol}
━━━━━━━━━━━━━━━━━━━━
📌 <b>XULOSA: {xulosa}</b>
⚠️ <i>Investitsiya maslahat emas!</i>"""

    except Exception as e:
        log.error(f"Fundamental error {ticker}: {e}")
        return f"❌ Xatolik: {str(e)[:150]}"

# ──────────────────────────────────────────────
#  O'ZBEKISTON FUNDAMENTAL TAHLIL
# ──────────────────────────────────────────────
def get_uz_fundamental(ticker: str) -> str:
    ticker = ticker.strip().upper()
    d = UZ_STOCKS.get(ticker)
    if not d:
        return (
            f"❌ <b>{ticker}</b> topilmadi.\n\n"
            f"📋 <b>Mavjud aksiyalar:</b>\n"
            + "\n".join([f"• <code>{k}</code> — {v['name']}" for k, v in UZ_STOCKS.items()])
        )

    price = d['price']; shares = d['shares']
    mkt_cap = price * shares
    rev = d['revenue']; ni = d['net_income']
    assets = d['total_assets']; debt = d['total_debt']
    equity = d['equity']; fcf = d['fcf']; div = d['dividend']

    pe  = round(safe_div(mkt_cap, ni), 2) if ni > 0 else "N/A"
    pb  = round(safe_div(mkt_cap, equity), 2)
    ps  = round(safe_div(mkt_cap, rev), 2)
    roe = round(safe_div(ni, equity) * 100, 1)
    roa = round(safe_div(ni, assets) * 100, 1)
    debt_ratio = round(safe_div(debt, assets) * 100, 1)
    margin     = round(safe_div(ni, rev) * 100, 1)
    div_yield  = round(safe_div(div, price) * 100, 1)
    rev_growth = round(d['revenue_growth'] * 100, 1)

    # DCF
    if fcf > 0:
        dcf_val = (fcf * 1.07) / 0.12
        dcf_ps  = round(dcf_val / shares)
        if dcf_ps > price * 1.15:
            dcf_sig = f"✅ ARZON — DCF: {dcf_ps:,} so'm"
        elif dcf_ps < price * 0.85:
            dcf_sig = f"🔴 QIMMAT — DCF: {dcf_ps:,} so'm"
        else:
            dcf_sig = f"🟡 ADOLATLI — DCF: {dcf_ps:,} so'm"
    else:
        dcf_sig = "⚠️ FCF yo'q (hisoblash imkonsiz)"

    # Piotroski F-Score
    f_score = sum([
        ni > 0, roa > 0, fcf > 0,
        fcf > ni, debt_ratio < 33,
        margin > 10, rev_growth > 5, roe > 15
    ])
    f_sig = ("🟢 KUCHLI" if f_score >= 6 else "🟡 O'RTA" if f_score >= 4 else "🔴 ZAIF")

    # Halollik
    is_bank = "bank" in d['sector'].lower()
    if is_bank:
        halol = "⚠️ SHUBHALI — Bank aksiyasi (fiqhchilar orasida ixtilof)"
    elif debt_ratio < 33:
        halol = f"✅ HALOL — Qarz {debt_ratio}% (AAOIFI < 33%)"
    else:
        halol = f"❌ HARAM — Qarz {debt_ratio}% (AAOIFI chegarasi oshgan)"

    # Score
    sc = sum([
        isinstance(pe, float) and pe < 15,
        isinstance(pb, float) and pb < 2,
        roe > 15, margin > 10,
        debt_ratio < 33, rev_growth > 5, f_score >= 6
    ])
    xulosa = ("🟢 KUCHLI" if sc >= 6 else "🟡 O'RTA" if sc >= 4 else "🔴 ZAIF")

    return f"""🇺🇿 <b>{ticker} — {d['name']}</b>
<b>{d['sector']} | TRFB (O'zbekiston)</b>
━━━━━━━━━━━━━━━━━━━━
📝 {d['description']}

💰 <b>NARX VA BOZOR</b>
• Narx: <b>{price:,} so'm</b>
• Bozor qiymati: <b>{fmt_som(mkt_cap)}</b>
• Dividend: <b>{div:,} so'm ({div_yield}%)</b>

📊 <b>BAHOLASH</b>
• P/E: <b>{pe}</b>  |  P/B: <b>{pb}</b>  |  P/S: <b>{ps}</b>

📈 <b>RENTABELLIK</b>
• ROE: <b>{roe}%</b>  |  ROA: <b>{roa}%</b>
• Foyda marjasi: <b>{margin}%</b>
• Daromad o'sishi: <b>{rev_growth}%</b>

🏦 <b>MOLIYAVIY HOLAT</b>
• Aktivlar: <b>{fmt_som(assets)}</b>
• Qarz: <b>{fmt_som(debt)}</b>
• Qarz/Aktiv: <b>{debt_ratio}%</b>
• Kapital: <b>{fmt_som(equity)}</b>
• FCF: <b>{fmt_som(fcf) if fcf > 0 else 'N/A'}</b>

🧮 <b>BAHOLASH MODELLARI</b>
• DCF: {dcf_sig}
• Piotroski F-Score: <b>{f_score}/8</b> — {f_sig}

👥 Xodimlar: <b>{d['employees']:,}</b>

🕌 <b>HALOLLIK (AAOIFI):</b> {halol}
━━━━━━━━━━━━━━━━━━━━
📌 <b>XULOSA: {xulosa}</b>
⚠️ <i>Ma'lumotlar ommaviy hisobotlardan. Investitsiya maslahat emas!</i>"""

# ──────────────────────────────────────────────
#  TO'LIQ TAHLIL (FUNDAMENTAL + TEXNIK)
# ──────────────────────────────────────────────
def get_full_analysis(ticker: str) -> str:
    fund = get_fundamental_analysis(ticker)
    tech = get_technical_analysis(ticker)
    return fund + "\n\n" + "━" * 20 + "\n\n" + tech

# ──────────────────────────────────────────────
#  GRAFIKA (Professional Dark Theme)
# ──────────────────────────────────────────────
def send_advanced_chart(message, ticker: str):
    try:
        ticker = ticker.strip().upper()
        data = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if data.empty:
            bot.reply_to(message, f"❌ {ticker} grafik ma'lumoti topilmadi.")
            return

        if hasattr(data.columns, 'levels'):
            data.columns = data.columns.get_level_values(0)

        close  = data['Close']
        high   = data['High']
        low    = data['Low']
        volume = data['Volume']

        # Indikatorlar
        ema20  = close.ewm(span=20).mean()
        ema50  = close.ewm(span=50).mean()
        sma20  = close.rolling(20).mean()
        std20  = close.rolling(20).std()
        bb_up  = sma20 + 2 * std20
        bb_lo  = sma20 - 2 * std20

        delta  = close.diff()
        gain   = delta.clip(lower=0).rolling(14).mean()
        loss   = (-delta.clip(upper=0)).rolling(14).mean()
        rsi    = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

        ema12  = close.ewm(span=12).mean()
        ema26  = close.ewm(span=26).mean()
        macd   = ema12 - ema26
        macd_s = macd.ewm(span=9).mean()
        macd_h = macd - macd_s

        # ── LAYOUT ──
        BG = '#0d1117'
        fig = plt.figure(figsize=(14, 12), facecolor=BG)
        gs  = gridspec.GridSpec(4, 1, height_ratios=[4, 1, 1.2, 1], hspace=0.08)
        ax1 = fig.add_subplot(gs[0])   # Narx + Bollinger + EMA
        ax2 = fig.add_subplot(gs[1], sharex=ax1)   # Volume
        ax3 = fig.add_subplot(gs[2], sharex=ax1)   # MACD
        ax4 = fig.add_subplot(gs[3], sharex=ax1)   # RSI

        def style_ax(ax):
            ax.set_facecolor(BG)
            ax.tick_params(colors='#8b949e', labelsize=8)
            ax.spines['bottom'].set_color('#30363d')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#30363d')
            ax.grid(True, alpha=0.15, color='#444', linestyle='--')
            ax.yaxis.set_label_coords(-0.06, 0.5)

        for ax in [ax1, ax2, ax3, ax4]:
            style_ax(ax)

        dates = data.index

        # ── NARX ──
        ax1.plot(dates, close, color='#58a6ff', linewidth=1.5, label='Narx', zorder=5)
        ax1.plot(dates, ema20, color='#ffa657', linewidth=1, linestyle='--', label='EMA20')
        ax1.plot(dates, ema50, color='#ff7b72', linewidth=1, linestyle='--', label='EMA50')
        ax1.fill_between(dates, bb_up, bb_lo, alpha=0.08, color='#58a6ff')
        ax1.plot(dates, bb_up, color='#3fb950', linewidth=0.6, linestyle=':')
        ax1.plot(dates, bb_lo, color='#3fb950', linewidth=0.6, linestyle=':')
        ax1.set_title(f"  {ticker} — Professional Tahlil (3 Oy)", color='white', fontsize=13,
                      loc='left', pad=10, fontweight='bold')
        ax1.legend(loc='upper left', fontsize=8, facecolor='#161b22',
                   edgecolor='#30363d', labelcolor='white')
        ax1.tick_params(labelbottom=False)

        # ── VOLUME ──
        cl_list = list(close)
        bar_colors = ['#3fb950' if i == 0 or cl_list[i] >= cl_list[i-1] else '#ff7b72'
                      for i in range(len(cl_list))]
        ax2.bar(dates, volume, color=bar_colors, alpha=0.7, width=0.8)
        ax2.set_ylabel('Vol', color='#8b949e', fontsize=8)
        ax2.tick_params(labelbottom=False)
        ax2.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K')
        )

        # ── MACD ──
        macd_colors = ['#3fb950' if v >= 0 else '#ff7b72' for v in macd_h]
        ax3.bar(dates, macd_h, color=macd_colors, alpha=0.7, width=0.8)
        ax3.plot(dates, macd,   color='#58a6ff', linewidth=1, label='MACD')
        ax3.plot(dates, macd_s, color='#ffa657', linewidth=1, label='Signal')
        ax3.axhline(0, color='#30363d', linewidth=0.8)
        ax3.set_ylabel('MACD', color='#8b949e', fontsize=8)
        ax3.legend(loc='upper left', fontsize=7, facecolor='#161b22',
                   edgecolor='#30363d', labelcolor='white')
        ax3.tick_params(labelbottom=False)

        # ── RSI ──
        ax4.plot(dates, rsi, color='#d2a8ff', linewidth=1.5)
        ax4.axhline(70, color='#ff7b72', linewidth=0.8, linestyle='--', alpha=0.7)
        ax4.axhline(30, color='#3fb950', linewidth=0.8, linestyle='--', alpha=0.7)
        ax4.fill_between(dates, rsi, 70, where=(rsi >= 70), alpha=0.15, color='#ff7b72')
        ax4.fill_between(dates, rsi, 30, where=(rsi <= 30), alpha=0.15, color='#3fb950')
        ax4.set_ylim(0, 100)
        ax4.set_ylabel('RSI', color='#8b949e', fontsize=8)
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
        ax4.tick_params(axis='x', colors='#8b949e', labelsize=7, rotation=30)

        plt.setp(ax1.get_xticklabels(), visible=False)
        plt.setp(ax2.get_xticklabels(), visible=False)
        plt.setp(ax3.get_xticklabels(), visible=False)

        fig.text(0.99, 0.01, 'Aksiya Halol Bot', ha='right', va='bottom',
                 color='#444', fontsize=7)

        fname = f"{ticker}_advanced.png"
        plt.savefig(fname, dpi=130, bbox_inches='tight', facecolor=BG)
        plt.close()

        with open(fname, 'rb') as f:
            bot.send_photo(
                message.chat.id, f,
                caption=f"📊 <b>{ticker}</b> — EMA + Bollinger + MACD + RSI | 3 oy",
                parse_mode="HTML"
            )
        os.remove(fname)

    except Exception as e:
        log.error(f"Chart error {ticker}: {e}")
        bot.reply_to(message, f"❌ Grafik xatolik: {str(e)[:120]}")

# ──────────────────────────────────────────────
#  SIYOSIY SAVDOLAR
# ──────────────────────────────────────────────
QUIVER_HEADERS = {"Authorization": f"Token {QUIVER_API_KEY}"}
QUIVER_BASE    = "https://api.quiverquant.com/beta"

def get_congress_trades(name_filter: str = None) -> str:
    try:
        url  = f"{QUIVER_BASE}/live/congresstrading"
        resp = requests.get(url, headers=QUIVER_HEADERS, timeout=10)
        if resp.status_code == 401:
            return ("❌ Quiverquant API kaliti noto'g'ri.\n\n"
                    "1️⃣ quiverquant.com ga kiring\n"
                    "2️⃣ Bepul ro'yxatdan o'ting\n"
                    "3️⃣ Fayldagi QUIVER_API_KEY ni almashtiring")
        if resp.status_code != 200:
            return f"❌ API xatosi: {resp.status_code}"

        trades = resp.json()
        if name_filter:
            trades = [t for t in trades
                      if name_filter.lower() in str(t.get('Representative','')).lower()
                      or name_filter.lower() in str(t.get('Senator','')).lower()]

        trades = trades[:12]
        if not trades:
            return f"📭 {''+name_filter+' uchun' if name_filter else ''} savdo topilmadi."

        msg = f"🏛 <b>KONGRESS A'ZOLARI SAVDOLARI</b>\n"
        if name_filter:
            msg += f"🔍 Filtr: <b>{name_filter.title()}</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

        for t in trades:
            name   = t.get('Representative', t.get('Senator', 'Noma\'lum'))
            ticker = t.get('Ticker', '?')
            txn    = t.get('Transaction', '?')
            amount = t.get('Range', t.get('Amount', '?'))
            date   = t.get('TransactionDate', t.get('Date', '?'))
            party  = t.get('Party', '')

            p_icon  = "🔵" if party == "D" else "🔴" if party == "R" else "⚪"
            tx_icon = "📈" if any(w in str(txn) for w in ["Purchase", "Buy"]) else "📉"
            msg += f"{p_icon} <b>{name}</b>\n   {tx_icon} {txn} | <code>{ticker}</code> | {amount} | {date}\n\n"

        msg += "🔗 <i>Manba: quiverquant.com</i>"
        return msg

    except Exception as e:
        return f"❌ Xatolik: {str(e)[:120]}"

def get_trump_trades() -> str:
    try:
        url  = f"{QUIVER_BASE}/live/senatetrading"
        resp = requests.get(url, headers=QUIVER_HEADERS, timeout=10)
        if resp.status_code == 401:
            return ("❌ Quiverquant API kaliti kerak.\n"
                    "quiverquant.com — bepul ro'yxatdan o'ting.")

        trades = resp.json()[:10] if resp.status_code == 200 else []

        msg = "🇺🇸 <b>SIYOSIY SHAXSLAR SAVDOLARI</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        if not trades:
            msg += "📭 Hozircha ma'lumot yo'q."
            return msg

        for t in trades:
            name   = t.get('Senator', t.get('Representative', 'N/A'))
            ticker = t.get('Ticker', '?')
            txn    = t.get('Transaction', '?')
            amount = t.get('Amount', t.get('Range', '?'))
            date   = t.get('Date', t.get('TransactionDate', '?'))
            tx_icon = "📈" if any(w in str(txn) for w in ["Purchase","Buy"]) else "📉"
            msg += f"👤 <b>{name}</b>\n   {tx_icon} {txn} | <code>{ticker}</code> | {amount} | {date}\n\n"

        msg += "⚠️ <i>Manfaatlar to'qnashuvi xavfi bo'lgan savdolar!</i>"
        return msg
    except Exception as e:
        return f"❌ Xatolik: {str(e)[:120]}"

# ──────────────────────────────────────────────
#  RAQOBAT TAHLILI
# ──────────────────────────────────────────────
def get_competition_analysis(tickers: list) -> str:
    results = []
    for t in tickers:
        try:
            inf = yf.Ticker(t).info
            pe     = inf.get('trailingPE', 'N/A')
            pb     = inf.get('priceToBook', 'N/A')
            roe    = round((inf.get('returnOnEquity') or 0) * 100, 1)
            margin = round((inf.get('profitMargins') or 0) * 100, 1)
            rev_g  = round((inf.get('revenueGrowth') or 0) * 100, 1)
            dr     = round(((inf.get('totalDebt') or 0) / max(inf.get('totalAssets') or 1, 1)) * 100, 1)
            div    = round((inf.get('dividendYield') or 0) * 100, 2)
            halol  = "✅" if dr < 33 else "❌"
            results.append((t, pe, pb, roe, margin, rev_g, dr, div, halol))
        except:
            results.append((t, 'N/A','N/A',0,0,0,0,0,'?'))

    msg = "⚔️ <b>RAQOBAT TAHLILI</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    headers = "Ticker     | P/E   | P/B  | ROE%  | Margin | O'sish | Qarz% | Div%  | Halol"
    msg += f"<code>{headers}\n" + "-"*70 + "\n"
    for r in results:
        t, pe, pb, roe, mg, rg, dr, dv, hl = r
        pe_s = f"{pe:.1f}" if isinstance(pe, float) else str(pe)
        pb_s = f"{pb:.1f}" if isinstance(pb, float) else str(pb)
        msg += f"{t:<10} | {pe_s:<5} | {pb_s:<4} | {roe:<5} | {mg:<6} | {rg:<6} | {dr:<5} | {dv:<5} | {hl}\n"
    msg += "</code>\n"

    # Eng yaxshi topish
    valid = [(r[0], r[3]) for r in results if isinstance(r[3], float)]
    if valid:
        best = max(valid, key=lambda x: x[1])
        msg += f"\n🏆 Eng yuqori ROE: <b>{best[0]}</b> ({best[1]}%)"

    msg += "\n⚠️ <i>Investitsiya maslahat emas!</i>"
    return msg

# ──────────────────────────────────────────────
#  BOZOR VAQTI
# ──────────────────────────────────────────────
def get_market_times() -> str:
    MARKETS = {
        "🗽 NYSE (New York)":       ("America/New_York",   "09:30", "16:00"),
        "🇬🇧 LSE (London)":         ("Europe/London",      "08:00", "16:30"),
        "🇩🇪 XETRA (Frankfurt)":    ("Europe/Berlin",      "09:00", "17:30"),
        "🇯🇵 TSE (Tokyo)":          ("Asia/Tokyo",         "09:00", "15:30"),
        "🇭🇰 HKEX (Hong Kong)":     ("Asia/Hong_Kong",     "09:30", "16:00"),
        "🇺🇿 TRFB (Toshkent)":      ("Asia/Tashkent",      "10:00", "16:00"),
    }
    msg = "⏰ <b>BOZOR VAQTLARI</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for name, (tz, open_t, close_t) in MARKETS.items():
        now   = datetime.now(zoneinfo.ZoneInfo(tz))
        t_now = now.strftime('%H:%M')
        open_dt  = datetime.strptime(open_t, '%H:%M').replace(tzinfo=None)
        close_dt = datetime.strptime(close_t, '%H:%M').replace(tzinfo=None)
        now_naive = now.replace(tzinfo=None)
        t_only = now_naive.replace(year=2000, month=1, day=1,
                                   hour=now.hour, minute=now.minute, second=0)
        open_c  = open_dt.replace(year=2000, month=1, day=1)
        close_c = close_dt.replace(year=2000, month=1, day=1)
        is_open  = open_c <= t_only <= close_c and now.weekday() < 5
        status   = "🟢 OCHIQ" if is_open else "🔴 YOPIQ"
        msg += f"{name}\n   🕐 {t_now} | {open_t}–{close_t} | {status}\n\n"
    return msg

# ──────────────────────────────────────────────
#  LUG'AT
# ──────────────────────────────────────────────
GLOSSARY = {
    "P/E":       "Narx / Yillik foyda nisbati. Past bo'lsa arzonroq.",
    "P/B":       "Narx / Balans qiymati. 1 dan past = aktivlardan arzon.",
    "P/S":       "Narx / Daromad nisbati.",
    "PEG":       "P/E / Foyda o'sishi. 1 dan past = arzon o'sayotgan kompaniya.",
    "ROE":       "Kapital rentabelligi. Yuqori bo'lsa yaxshi (>15%).",
    "ROA":       "Aktiv rentabelligi. Yuqori bo'lsa yaxshi (>5%).",
    "FCF":       "Erkin pul oqimi — kapital xarajatlardan keyin qolgan pul.",
    "DCF":       "Kelajak pul oqimini hozirgi narxga qaytarish usuli.",
    "EV/EBITDA": "Korxona qiymati / EBITDA. Qarzni ham hisobga olgan baho.",
    "Beta":      "Bozor bilan korrelyatsiya. >1 = ko'proq o'zgaruvchan.",
    "RSI":       "Kuch indeksi. <30 = oversold (arzon), >70 = overbought (qimmat).",
    "MACD":      "Harakatlanuvchi o'rtacha konvergensiyasi/divergensiyasi.",
    "Bollinger": "Narx kanali. Pastki = sotib olish, yuqori = sotish imkoni.",
    "EMA":       "Eksponensial harakatlanuvchi o'rtacha.",
    "ATR":       "O'rtacha haqiqiy diapazon — volatillik o'lchovi.",
    "OBV":       "Hajm-narx munosabati indikatori.",
    "AAOIFI":    "Islomiy moliya va sarmoya standartlari tashkiloti.",
    "Halollik":  "AAOIFI: qarz/aktiv < 33%, asosiy biznes halol bo'lsa HALOL.",
    "F-Score":   "Piotroski: 0-9 ball, >7 = moliyaviy sog'lom kompaniya.",
    "Dividend":  "Kompaniya foydasi aksiyadorlarga to'lanadigan ulushi.",
    "Insider":   "Kompaniya ichki xodimlari amalga oshirgan savdolar.",
}

def get_glossary(term: str = None) -> str:
    if term and term.upper() in GLOSSARY:
        return f"📖 <b>{term.upper()}</b>\n\n{GLOSSARY[term.upper()]}"
    msg = "📖 <b>MOLIYAVIY LUG'AT</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for k, v in GLOSSARY.items():
        msg += f"• <b>{k}</b> — {v}\n\n"
    return msg

# ──────────────────────────────────────────────
#  KLAVIATURA
# ──────────────────────────────────────────────
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        "📈 Xalqaro bozor",    "🇺🇿 O'zbek bozori",
        "₿ Crypto",             "🌍 Forex",
        "🛢 Xomashyo",          "⚔️ Raqobat",
        "🏛 Kongress savdolari","🇺🇸 Siyosiy savdolar",
        "⏰ Bozor vaqti",       "📖 Lug'at",
        "📊 Grafik",            "🆘 Yordam"
    )
    return markup

def analysis_keyboard(ticker: str):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Fundamental", callback_data=f"fund:{ticker}"),
        types.InlineKeyboardButton("📈 Texnik",       callback_data=f"tech:{ticker}"),
        types.InlineKeyboardButton("🔄 To'liq tahlil", callback_data=f"full:{ticker}"),
        types.InlineKeyboardButton("📉 Grafik",        callback_data=f"chart:{ticker}"),
    )
    return markup

# ──────────────────────────────────────────────
#  HANDLERLAR
# ──────────────────────────────────────────────
@bot.message_handler(commands=['start', 'menu'])
def cmd_start(message):
    name = message.from_user.first_name or "foydalanuvchi"
    bot.send_message(
        message.chat.id,
        f"👋 Salom, <b>{name}</b>!\n\n"
        f"🤖 <b>Aksiya Halol Bot — Ultimate Edition</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Fundamental tahlil (P/E, ROE, DCF, F-Score)\n"
        f"✅ Texnik tahlil (RSI, MACD, Bollinger, EMA)\n"
        f"✅ O'zbekiston bozori (TRFB)\n"
        f"✅ Xalqaro bozor (NYSE, NASDAQ)\n"
        f"✅ Halollik tekshiruvi (AAOIFI)\n"
        f"✅ Siyosiy savdolar (Kongress, Senat)\n\n"
        f"💡 <b>Qanday foydalanish:</b>\n"
        f"• Tiker yuboring: <code>AAPL</code>, <code>TSLA</code>\n"
        f"• O'zbek: <code>UZAUTO</code>, <code>UTGAP</code>\n"
        f"• Crypto: <code>BTC-USD</code>, <code>ETH-USD</code>\n"
        f"• Oltin: <code>GC=F</code> | Forex: <code>EURUSD=X</code>",
        reply_markup=main_keyboard()
    )

@bot.message_handler(commands=['help'])
def cmd_help(message):
    bot.send_message(
        message.chat.id,
        "🆘 <b>YORDAM</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>Tiker misollari:</b>\n"
        "• Aksiya: <code>AAPL MSFT GOOGL TSLA NVDA AMZN</code>\n"
        "• O'zbek: <code>UZAUTO UTGAP ATSZ ALGM UZMK</code>\n"
        "• Crypto: <code>BTC-USD ETH-USD BNB-USD</code>\n"
        "• Oltin: <code>GC=F</code> | Kumush: <code>SI=F</code>\n"
        "• Forex: <code>EURUSD=X USDJPY=X</code>\n\n"
        "<b>Siyosatchilar:</b>\n"
        "<code>pelosi</code> | <code>trump</code> | <code>tuberville</code>\n\n"
        "<b>Raqobat (2-4 tiker):</b>\n"
        "<code>AAPL MSFT GOOGL</code>\n\n"
        "Savol: @admin"
    )

# Inline callback handler
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    parts  = call.data.split(":", 1)
    action = parts[0]
    ticker = parts[1] if len(parts) > 1 else ""

    bot.answer_callback_query(call.id, f"⏳ {ticker} tahlil qilinmoqda...")

    if action == "fund":
        if ticker in UZ_STOCKS:
            text = get_uz_fundamental(ticker)
        else:
            text = get_fundamental_analysis(ticker)
        bot.send_message(call.message.chat.id, text)

    elif action == "tech":
        text = get_technical_analysis(ticker)
        bot.send_message(call.message.chat.id, text)

    elif action == "full":
        if ticker in UZ_STOCKS:
            fund_text = get_uz_fundamental(ticker)
            tech_text = get_technical_analysis(ticker)
            bot.send_message(call.message.chat.id, fund_text)
            bot.send_message(call.message.chat.id, tech_text)
        else:
            bot.send_message(call.message.chat.id, get_full_analysis(ticker))

    elif action == "chart":
        msg_obj = call.message
        send_advanced_chart(msg_obj, ticker)

# Asosiy handler
@bot.message_handler(func=lambda m: True)
def handle_all(message):
    if not message.text:
        return
    text = message.text.strip()
    low  = text.lower()

    # ── TUGMALAR ──
    if text in ["📈 Xalqaro bozor", "₿ Crypto", "🌍 Forex", "🛢 Xomashyo"]:
        hints = {
            "📈 Xalqaro bozor": "AAPL, MSFT, GOOGL, TSLA, NVDA, AMZN",
            "₿ Crypto":         "BTC-USD, ETH-USD, BNB-USD, SOL-USD",
            "🌍 Forex":          "EURUSD=X, USDJPY=X, GBPUSD=X",
            "🛢 Xomashyo":       "GC=F (Oltin), CL=F (Neft), SI=F (Kumush)",
        }
        bot.reply_to(message, f"✅ Tikerni yuboring.\nMisol: <code>{hints[text]}</code>")

    elif text == "🇺🇿 O'zbek bozori":
        stocks_list = "\n".join([f"• <code>{k}</code> — {v['name']} ({v['sector']})"
                                  for k, v in UZ_STOCKS.items()])
        bot.reply_to(message,
            f"🇺🇿 <b>O'zbekiston Fond Birjasi (TRFB)</b>\n\n{stocks_list}\n\n"
            f"💡 Tiker yuboring: <code>UZAUTO</code>")

    elif text == "⚔️ Raqobat":
        bot.reply_to(message,
            "⚔️ 2–4 ta tikerni bo'sh joy bilan yozing:\n"
            "<code>AAPL MSFT NVDA GOOGL</code>")

    elif text == "🏛 Kongress savdolari":
        bot.send_chat_action(message.chat.id, 'typing')
        bot.reply_to(message, get_congress_trades())

    elif text == "🇺🇸 Siyosiy savdolar":
        bot.send_chat_action(message.chat.id, 'typing')
        bot.reply_to(message, get_trump_trades())

    elif text == "⏰ Bozor vaqti":
        bot.reply_to(message, get_market_times())

    elif text == "📖 Lug'at":
        bot.reply_to(message, get_glossary())

    elif text == "📊 Grafik":
        bot.reply_to(message,
            "📊 Tiker yuboring (grafik + tahlil):\n"
            "<code>AAPL</code> | <code>BTC-USD</code> | <code>GC=F</code> | <code>UZAUTO</code>")

    elif text == "🆘 Yordam":
        cmd_help(message)

    # ── SIYOSATCHI ISMI ──
    elif low in ["pelosi", "trump", "tuberville", "warren", "mccarthy"]:
        bot.send_chat_action(message.chat.id, 'typing')
        bot.reply_to(message, get_congress_trades(low))

    # ── RAQOBAT (bir necha tiker) ──
    elif " " in text and 2 <= len(text.split()) <= 4:
        parts = text.split()
        if all(t.replace('-','').replace('=','').replace('.','').isalnum() for t in parts):
            bot.send_chat_action(message.chat.id, 'typing')
            bot.reply_to(message, get_competition_analysis(parts))
        else:
            bot.reply_to(message, "❓ Tushunmadim. Misol: <code>AAPL MSFT NVDA</code>")

    # ── O'ZBEKISTON TIKERI ──
    elif text in UZ_STOCKS:
        bot.send_chat_action(message.chat.id, 'typing')
        # Inline tugmalar bilan menyu
        bot.reply_to(
            message,
            f"🇺🇿 <b>{UZ_STOCKS[text]['name']}</b> uchun qaysi tahlil kerak?",
            reply_markup=analysis_keyboard(text)
        )

    # ── XALQARO TIKER ──
    elif len(text) <= 12 and text.replace('-','').replace('=','').replace('.','').isalnum():
        bot.send_chat_action(message.chat.id, 'typing')
        bot.reply_to(
            message,
            f"🌍 <b>{text}</b> uchun qaysi tahlil kerak?",
            reply_markup=analysis_keyboard(text)
        )

    else:
        bot.reply_to(message,
            "❓ Tushunmadim.\n\nMisol: <code>AAPL</code> yoki <code>UZAUTO</code>\n"
            "Yordam: /help")

# ──────────────────────────────────────────────
#  ISHGA TUSHIRISH
# ──────────────────────────────────────────────
if __name__ == "__main__":
    log.info("=" * 55)
    log.info("  AKSIYA HALOL BOT — ULTIMATE EDITION")
    log.info("=" * 55)
    log.info("Bot ishga tushdi. To'xtatish: Ctrl+C")

    while True:
        try:
            bot.infinity_polling(none_stop=True, interval=0, timeout=30)
        except Exception as e:
            log.error(f"Polling xatosi: {e}")
            time.sleep(5)
            log.info("Qayta ulanilmoqda...")
