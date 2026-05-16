import telebot
from telebot import types
import yfinance as yf
import finnhub
import os
import time
from flask import Flask, request

TOKEN = '8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8'
FINNHUB_KEY = 'ctv22h9r01qg80atc9vg'
RENDER_URL = 'https://aksiya-halol-bot3.onrender.com'

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)

try:
    finnhub_client = finnhub.Client(api_key=FINNHUB_KEY)
except:
    finnhub_client = None

HALOLLIK = {
    "AAPL": {"holat": "HALOL", "sabab": "Apple texnologiya kompaniyasi. Halol."},
    "MSFT": {"holat": "HALOL", "sabab": "Microsoft dasturiy taminot. Halol."},
    "GOOGL": {"holat": "HALOL", "sabab": "Google qidiruv. Halol."},
    "AMZN": {"holat": "SHUBHALI", "sabab": "Amazon spirt va harom kontent sotadi."},
    "TSLA": {"holat": "HALOL", "sabab": "Tesla elektr avtomobil. Halol."},
    "NVDA": {"holat": "HALOL", "sabab": "NVIDIA chip va AI. Halol."},
    "META": {"holat": "SHUBHALI", "sabab": "Meta harom kontent bor."},
    "NFLX": {"holat": "XAROM", "sabab": "Netflix harom kontentni tarqatadi."},
    "JPM": {"holat": "XAROM", "sabab": "JPMorgan bank ribo asosida."},
    "BAC": {"holat": "XAROM", "sabab": "Bank of America ribo asosida."},
    "V": {"holat": "SHUBHALI", "sabab": "Visa ribo tizimiga xizmat qiladi."},
    "MCD": {"holat": "XAROM", "sabab": "McDonalds harom gusht va spirt."},
    "INTC": {"holat": "HALOL", "sabab": "Intel chip ishlab chiqaradi. Halol."},
    "AMD": {"holat": "HALOL", "sabab": "AMD chip va protsessor. Halol."},
    "JNJ": {"holat": "HALOL", "sabab": "Johnson tibbiyot. Halol."},
    "PFE": {"holat": "HALOL", "sabab": "Pfizer dori-darmon. Halol."},
    "UZAUTO": {"holat": "HALOL", "sabab": "UzAuto Motors avtomobil. Halol."},
    "NAVOIYAZOT": {"holat": "HALOL", "sabab": "Navoiyazot ugit. Halol."},
    "ALMALYK": {"holat": "HALOL", "sabab": "Olmaliq KMK konchilik. Halol."},
    "HAMKORBANK": {"holat": "XAROM", "sabab": "Hamkorbank ribo asosida."},
    "KAPITALBANK": {"holat": "XAROM", "sabab": "Kapital Bank ribo asosida."},
}


def main_menu():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton("Halol aksiyalar"),
        types.KeyboardButton("Harom aksiyalar"),
        types.KeyboardButton("Shubhali aksiyalar"),
        types.KeyboardButton("SP500"),
        types.KeyboardButton("NASDAQ"),
        types.KeyboardButton("Ozbekiston aksiyalari"),
        types.KeyboardButton("Yordam"),
    )
    return kb


def get_rsi(closes, period=14):
    try:
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
        avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs.iloc[-1]))
        if rsi >= 70:
            signal = "SELL"
        elif rsi <= 30:
            signal = "BUY"
        else:
            signal = "WAIT"
        return round(rsi, 2), signal
    except:
        return 50.0, "WAIT"


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "PRO Shariat Filtri Botiga xush kelibsiz!\n\nAksiya tickerini kiriting (AAPL, TSLA, NVDA):",
        reply_markup=main_menu()
    )


@bot.message_handler(func=lambda m: True)
def handle_all(message):
    text = message.text.strip()

    if text == "Halol aksiyalar":
        bot.reply_to(message, "HALOL: AAPL, TSLA, NVDA, MSFT, JNJ, PFE, INTC, AMD")
        return

    if text == "Harom aksiyalar":
        bot.reply_to(message, "XAROM: JPM, BAC, NFLX, MCD, HAMKORBANK, KAPITALBANK")
        return

    if text == "Shubhali aksiyalar":
        bot.reply_to(message, "SHUBHALI: AMZN, META, V")
        return

    if text == "SP500":
        bot.reply_to(message, "S&P 500: Amerikaning eng yirik 500 ta kompaniyasi indeksi.")
        return

    if text == "NASDAQ":
        bot.reply_to(message, "NASDAQ: Texnologiya kompaniyalari birjasi.")
        return

    if text == "Ozbekiston aksiyalari":
        uzse = ["UZAUTO", "NAVOIYAZOT", "ALMALYK", "HAMKORBANK", "KAPITALBANK"]
        matn = "Ozbekiston aksiyalari:\n\n"
        for t in uzse:
            d = HALOLLIK.get(t, {})
            matn = matn + t + " - " + d.get('holat', '') + "\n" + d.get('sabab', '') + "\n\n"
        bot.reply_to(message, matn)
        return

    if text == "Yordam":
        bot.reply_to(message, "Ticker yozing: AAPL, TSLA, NVDA, UZAUTO")
        return

    try:
        tiker = text.upper()
        bot.send_chat_action(message.chat.id, 'typing')
        stock = yf.Ticker(tiker)
        info = stock.info

        if not info or 'currentPrice' not in info:
            bot.reply_to(message, "Aksiya topilmadi. Togri ticker kiriting.")
            return

        narx = info.get('currentPrice', 0)
        valyuta = info.get('currency', 'USD')
        market_cap_raw = info.get('marketCap', 0)
        pe = info.get('trailingPE', 0)

        if market_cap_raw >= 1e12:
            mc = str(round(market_cap_raw / 1e12, 2)) + "T"
        elif market_cap_raw >= 1e9:
            mc = str(round(market_cap_raw / 1e9, 2)) + "B"
        else:
            mc = str(round(market_cap_raw / 1e6, 2)) + "M"

        tarix = stock.history(period="1y")
        cl = tarix['Close']
        n = len(cl)

        def pct(d):
            if n > d:
                return round(((cl.iloc[-1] - cl.iloc[-(d + 1)]) / cl.iloc[-(d + 1)]) * 100, 2)
            return 0.0

        rsi, rsi_sig = get_rsi(cl)
        tp = round(narx * 1.05, 2)
        sl = round(narx * 0.97, 2)

        qarz = info.get('totalDebt', 0)
        nisbat = round((qarz / market_cap_raw) * 100, 1) if market_cap_raw else 0

        if nisbat < 30:
            h_auto = "HALOL (" + str(nisbat) + "%)"
        elif nisbat <= 33:
            h_auto = "SHUBHALI (" + str(nisbat) + "%)"
        else:
            h_auto = "XAROM (" + str(nisbat) + "%)"

        hd = HALOLLIK.get(tiker, {})
        h_text = hd.get('holat', h_auto)
        h_sabab = hd.get('sabab', "Qarz nisbati: " + str(nisbat) + "%")

        nom = info.get('longName', tiker)
        pe_text = str(round(pe, 1)) if pe else "—"

        javob = (
            tiker + " | " + nom + "\n"
            "Market Cap: " + mc + " | P/E: " + pe_text + "\n\n"
            "Narx: " + str(narx) + " " + valyuta + "\n\n"
            "Ozgarish:\n"
            "1D: " + str(pct(1)) + "% | 1W: " + str(pct(5)) + "%\n"
            "1M: " + str(pct(22)) + "% | 1Y: " + str(pct(252)) + "%\n\n"
            "RSI: " + str(rsi) + " -> " + rsi_sig + "\n"
            "TP: " + str(tp) + " | SL: " + str(sl) + "\n\n"
            "Shariat: " + h_text + "\n"
            + h_sabab
        )

        news_text = ""
        if finnhub_client:
            try:
                news = finnhub_client.company_news(tiker, _from="2024-01-01", to="2099-01-01")
                if news:
                    javob = javob + "\n\nYangiliklar:\n"
                    for n_item in news[:3]:
                        javob = javob + "- " + n_item['headline'][:60] + "\n"
            except:
                pass

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("TradingView", url="https://www.tradingview.com/symbols/" + tiker + "/"))
        bot.reply_to(message, javob, reply_markup=kb)

    except Exception as e:
        bot.reply_to(message, "Xatolik yuz berdi. Qayta urining.")
        print("Xato: " + str(e))


@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode('UTF-8'))
    bot.process_new_updates([update])
    return '!', 200


@app.route('/')
def index():
    return 'Bot ishlayapti!', 200


if __name__ == '__main__':
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=RENDER_URL + '/' + TOKEN)
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
