import telebot
import yfinance as yf
import pandas as pd
import numpy as np
import ta

TOKEN = "SIZNING_TOKEN"
bot = telebot.TeleBot(TOKEN)

# ===================== TEXNIK ANALIZ =====================
def texnik_analiz(symbol):
    data = yf.download(symbol, period="1mo", interval="1h")

    # RSI
    data['rsi'] = ta.momentum.RSIIndicator(data['Close']).rsi()

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(data['Close'])
    data['bb_high'] = bb.bollinger_hband()
    data['bb_low'] = bb.bollinger_lband()

    # Moving Average
    data['ma'] = data['Close'].rolling(20).mean()

    last = data.iloc[-1]

    signal = "NO SIGNAL ❌"
    sl = 0
    tp = 0

    # STRATEGIYA
    if last['rsi'] < 30 and last['Close'] < last['bb_low']:
        signal = "BUY 🟢"
        sl = last['Close'] * 0.995
        tp = last['Close'] * 1.010

    elif last['rsi'] > 70 and last['Close'] > last['bb_high']:
        signal = "SELL 🔴"
        sl = last['Close'] * 1.005
        tp = last['Close'] * 0.990

    return f"""
📊 {symbol} TEXNIK ANALIZ

RSI: {round(last['rsi'],2)}
Narx: {round(last['Close'],2)}

Signal: {signal}

SL: {round(sl,2)}
TP: {round(tp,2)}
"""

# ===================== GOLD MAXSUS STRATEGIYA =====================
def gold_strategy():
    data = yf.download("XAUUSD=X", period="1mo", interval="15m")

    data['rsi'] = ta.momentum.RSIIndicator(data['Close']).rsi()

    last = data.iloc[-1]

    signal = "NO SIGNAL ❌"

    # GOLD SCALPING STRATEGIYA 🔥
    if last['rsi'] < 25:
        signal = "BUY GOLD 🟢"
        sl = last['Close'] - 5
        tp = last['Close'] + 10

    elif last['rsi'] > 75:
        signal = "SELL GOLD 🔴"
        sl = last['Close'] + 5
        tp = last['Close'] - 10
    else:
        sl, tp = 0, 0

    return f"""
🥇 GOLD (XAUUSD)

RSI: {round(last['rsi'],2)}
Narx: {round(last['Close'],2)}

Signal: {signal}

SL: {sl}
TP: {tp}
"""

# ===================== FUNDAMENTAL ANALIZ =====================
def fundamental(symbol):
    stock = yf.Ticker(symbol)
    info = stock.info

    return f"""
📊 {symbol} FUNDAMENTAL

Company: {info.get('longName')}
Sector: {info.get('sector')}

P/E: {info.get('trailingPE')}
EPS: {info.get('trailingEps')}

Revenue: {info.get('totalRevenue')}
Profit: {info.get('netIncomeToCommon')}

Debt: {info.get('totalDebt')}
Cash: {info.get('totalCash')}
"""

# ===================== COMMANDLAR =====================
@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, """
🤖 PRO TRADING BOT

Buyruqlar:

/gold - GOLD signal
/forex EURUSD=X
/crypto BTC-USD
/stock AAPL (fundamental + texnik)
""")

@bot.message_handler(commands=['gold'])
def gold(msg):
    bot.reply_to(msg, gold_strategy())

@bot.message_handler(commands=['forex'])
def forex(msg):
    try:
        symbol = msg.text.split()[1]
        bot.reply_to(msg, texnik_analiz(symbol))
    except:
        bot.reply_to(msg, "Masalan: /forex EURUSD=X")

@bot.message_handler(commands=['crypto'])
def crypto(msg):
    try:
        symbol = msg.text.split()[1]
        bot.reply_to(msg, texnik_analiz(symbol))
    except:
        bot.reply_to(msg, "Masalan: /crypto BTC-USD")

@bot.message_handler(commands=['stock'])
def stock(msg):
    try:
        symbol = msg.text.split()[1]
        text = texnik_analiz(symbol) + "\n" + fundamental(symbol)
        bot.reply_to(msg, text)
    except:
        bot.reply_to(msg, "Masalan: /stock AAPL")

bot.polling()
