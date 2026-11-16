import os
import logging
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import yfinance as yf
import pandas as pd
import numpy as np
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI ilovasi
app = FastAPI()

# Statik fayllar (Mini App HTML) uchun papka
try:
    os.makedirs("static")
except FileExistsError:
    pass
app.mount("/static", StaticFiles(directory="static"), name="static")

# Asosiy sahifa - Mini App ochilganda yuklanadi
@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

# Sektor gigantlari lug'ati (Raqobatchilar solishtiruvi uchun)
SECTOR_PEERS = {
    "Technology": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AVGO", "ORCL"],
    "Consumer Cyclical": ["AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX"],
    "Financial Services": ["BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS"],
    "Healthcare": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "PFE"],
    "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "TMUS", "VZ", "T"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX"],
    "Industrials": ["GE", "CAT", "UNP", "HON", "BA", "UPS", "RTX"],
}

def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(data, window=14):
    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift())
    low_close = np.abs(data['Low'] - data['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(window=window).mean()

@app.get("/api/stock/{ticker}")
async def get_stock_analysis(ticker: str):
    ticker = ticker.upper().strip()
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if not info or 'regularMarketPrice' not in info and 'currentPrice' not in info:
            raise HTTPException(status_code=404, detail="Aksiya topilmadi")

        # Tarixiy ma'lumotlar (RSI va ATR uchun)
        hist = stock.history(period="3mo")
        rsi_val = round(calculate_rsi(hist).iloc[-1], 2) if not hist.empty else None
        atr_val = round(calculate_atr(hist).iloc[-1], 2) if not hist.empty else None

        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        
        # 1. Fundamental va Texnik ko'rsatkichlar
        fundamentals = {
            "name": info.get("longName", ticker),
            "symbol": ticker,
            "sector": info.get("sector", "Noma'lum"),
            "industry": info.get("industry", "Noma'lum"),
            "price": current_price,
            "currency": info.get("currency", "USD"),
            "marketCap": info.get("marketCap"),
            "peRatio": info.get("trailingPE"),
            "forwardPE": info.get("forwardPE"),
            "eps": info.get("trailingEps"),
            "roe": round(info.get("returnOnEquity", 0) * 100, 2) if info.get("returnOnEquity") else None,
            "roa": round(info.get("returnOnAssets", 0) * 100, 2) if info.get("returnOnAssets") else None,
            "debtToEquity": info.get("debtToEquity"),
            "freeCashFlow": info.get("freeCashflow"),
            "profitMargin": round(info.get("profitMargins", 0) * 100, 2) if info.get("profitMargins") else None,
            "shortPercent": round(info.get("shortPercentOfFloat", 0) * 100, 2) if info.get("shortPercentOfFloat") else None,
            "rsi": rsi_val,
            "atr": atr_val,
            "targetMeanPrice": info.get("targetMeanPrice"),
            "recommendation": info.get("recommendationKey", "none").upper()
        }

        # 2. Top 20 Institutsional Investorlar va Fondlar
        holders_list = []
        try:
            inst_holders = stock.institutional_holders
            if inst_holders is not None and not inst_holders.empty:
                for _, row in inst_holders.head(20).iterrows():
                    holders_list.append({
                        "holder": str(row.get("Holder", "Noma'lum")),
                        "shares": int(row.get("Shares", 0)),
                        "dateReported": str(row.get("Date Reported", ""))[:10],
                        "pctHeld": round(float(row.get("% Out", 0)) * 100, 2) if "% Out" in row else None,
                        "value": int(row.get("Value", 0))
                    })
        except Exception as e:
            logger.warning(f"Holders olishda xatolik: {e}")

        # 3. Sektor gigantlari bilan solishtirish va 1-5 ballik reyting
        sector = info.get("sector", "Technology")
        peers_tickers = SECTOR_PEERS.get(sector, ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"])
        if ticker not in peers_tickers:
            peers_tickers = [ticker] + peers_tickers[:5]
        else:
            peers_tickers = peers_tickers[:6]

        peers_data = []
        for p_sym in peers_tickers:
            try:
                p_info = yf.Ticker(p_sym).info
                p_pe = p_info.get("trailingPE")
                p_roe = round(p_info.get("returnOnEquity", 0) * 100, 2) if p_info.get("returnOnEquity") else 0
                p_debt = p_info.get("debtToEquity", 100)
                p_margin = round(p_info.get("profitMargins", 0) * 100, 2) if p_info.get("profitMargins") else 0
                
                # 1 dan 5 ballgacha avtomatik baholash algoritmi
                score = 3.0
                if p_roe > 20: score += 0.7
                elif p_roe < 5: score -= 0.5
                if p_margin > 15: score += 0.6
                if p_debt is not None and p_debt < 80: score += 0.4
                elif p_debt is not None and p_debt > 200: score -= 0.6
                if p_pe is not None and 0 < p_pe < 25: score += 0.3
                
                score = max(1.0, min(5.0, round(score, 1)))

                peers_data.append({
                    "symbol": p_sym,
                    "name": p_info.get("shortName", p_sym),
                    "price": p_info.get("currentPrice") or p_info.get("regularMarketPrice"),
                    "marketCap": p_info.get("marketCap"),
                    "pe": round(p_pe, 2) if p_pe else None,
                    "roe": p_roe,
                    "debtToEquity": round(p_debt, 1) if p_debt else None,
                    "margin": p_margin,
                    "score": score
                })
            except:
                continue

        # Eng yaxshi raqobatchini aniqlash
        best_peer = max(peers_data, key=lambda x: x["score"]) if peers_data else None

        return {
            "fundamentals": fundamentals,
            "holders": holders_list,
            "peers": peers_data,
            "bestPeer": best_peer
        }

    except Exception as e:
        logger.error(f"Xatolik {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Telegram Bot qismi
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL") # Render bergan HTTPS manzil

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Aksiya Tahlil Mini App'ni Ochish", web_app=WebAppInfo(url=WEBAPP_URL))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Assalomu alaykum! Professional Aksiya Tahlili va Smart Money tizimiga xush kelibsiz.\n\n"
        "Quyidagi tugma orqali Mini App ilovasini ishga tushiring:",
        reply_markup=reply_markup
    )

@app.on_event("startup")
async def on_startup():
    if BOT_TOKEN and WEBAPP_URL:
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start_command))
        await application.initialize()
        await application.start()
        asyncio.create_task(application.updater.start_polling())
        logger.info("Telegram bot muvaffaqiyatli ishga tushdi!")
