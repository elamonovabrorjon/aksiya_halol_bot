import telebot
import yfinance as yf
import pandas as pd
import ta
from concurrent.futures import ThreadPoolExecutor

TOKEN = "8781183838:AAFmgLoz6Bb8LlA-50lVAdAbNvhBCWO3sm0"
CHAT_ID = 745170275

bot = telebot.TeleBot(TOKEN)

# ================= LIST =================
def get_stock_list():
    url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
    df = pd.read_csv(url)
    return df["Symbol"].tolist()

# ================= ANALIZ =================
def analyze_stock(symbol):
    try:
        df = yf.download(symbol, period="1mo", interval="1d", progress=False)
        if df.empty:
            return None

        # RSI
        df["rsi"] = ta.momentum.RSIIndicator(df["Close"]).rsi()

        # MACD
        macd = ta.trend.MACD(df["Close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()

        rsi = df["rsi"].iloc[-1]
        macd_val = df["macd"].iloc[-1]
        macd_sig = df["macd_signal"].iloc[-1]

        volume = df["Volume"].iloc[-1]

        if volume < 1000000:
            return None

        score = 0

        # RSI score
        if rsi < 30:
            score += 2
        elif rsi > 70:
            score -= 2

        # MACD score
        if macd_val > macd_sig:
            score += 1
        else:
            score -= 1

        # SIGNAL
        if score >= 2:
            signal = "🟢 STRONG BUY"
        elif score == 1:
            signal = "🟢 BUY"
        elif score == -1:
            signal = "🔴 SELL"
        elif score <= -2:
            signal = "🔴 STRONG SELL"
        else:
            return None

        return {
            "symbol": symbol,
            "text": f"{signal} | {symbol}\nRSI: {round(rsi,1)} | Vol: {int(volume/1_000_000)}M",
            "score": score
        }

    except:
        return None

# ================= SCAN =================
@bot.message_handler(commands=['scan'])
def scan(message):
    bot.send_message(message.chat.id, "🚀 PRO analiz boshlanmoqda (30-60s)...")

    symbols = get_stock_list()
    results = []

    with ThreadPoolExecutor(max_workers=15) as executor:
        data = executor.map(analyze_stock, symbols)

    for r in data:
        if r:
            results.append(r)

    # ENG KUCHLILARNI SARALASH
    results = sorted(results, key=lambda x: x["score"], reverse=True)
    top = results[:20]

    if top:
        text = "🔥 TOP SIGNAL:\n\n"
        for i in top:
            text += i["text"] + "\n\n"
    else:
        text = "❌ Signal topilmadi"

    bot.send_message(message.chat.id, text)

    # Adminga ham yuborish
    if message.chat.id != CHAT_ID:
        try:
            bot.send_message(CHAT_ID, text)
        except:
            pass

# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 
        "🤖 PRO ANALIZ BOT V2\n\n"
        "/scan - kuchli signal topadi\n"
        "RSI + MACD asosida"
    )

print("Bot ishlayapti...")
bot.polling()