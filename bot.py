import telebot
import os
import yfinance as yf
import pandas as pd
import ta
import requests
from concurrent.futures import ThreadPoolExecutor

# TOKEN ENV orqali olinadi
TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

# ===== HALOL FILTER =====
HARAM = ["bank","finance","insurance","casino","bet","alcohol"]

def is_halal(info):
    name = str(info.get("longName","")).lower()
    return not any(h in name for h in HARAM)

# ===== ANALIZ =====
def analyze_stock(symbol):
    try:
        df = yf.download(symbol, period="3mo", interval="1d", progress=False)
        if df.empty:
            return None

        info = yf.Ticker(symbol).info

        if not is_halal(info):
            return None

        df["rsi"] = ta.momentum.RSIIndicator(df["Close"]).rsi()
        rsi = df["rsi"].iloc[-1]

        df["ema"] = df["Close"].ewm(span=50).mean()
        price = df["Close"].iloc[-1]
        ema = df["ema"].iloc[-1]

        volume = df["Volume"].iloc[-1]
        if volume < 1_000_000:
            return None

        score = 0
        if rsi < 35:
            score += 2
        elif rsi > 70:
            score -= 2

        score += 1 if price > ema else -1

        if score >= 2:
            signal = "🟢 STRONG BUY"
        elif score == 1:
            signal = "🟢 BUY"
        elif score == -1:
            signal = "🔴 SELL"
        else:
            return None

        return f"{signal} | {symbol} | RSI:{round(rsi,1)}"

    except:
        return None

# ===== SCAN =====
@bot.message_handler(commands=['scan'])
def scan(message):
    bot.send_message(message.chat.id, "🚀 Scan...")

    symbols = pd.read_csv(
        "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
    )["Symbol"].tolist()

    results = []

    with ThreadPoolExecutor(max_workers=20) as executor:
        data = executor.map(analyze_stock, symbols)

    for r in data:
        if r:
            results.append(r)

    text = "\n".join(results[:20]) if results else "Signal yo‘q"

    bot.send_message(message.chat.id, text)

# ===== START =====
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🤖 ELITE BOT ishlayapti\n/scan")

bot.polling()
