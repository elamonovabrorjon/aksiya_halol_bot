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


def get_macd(closes):
    try:
        ema12 = closes.ewm(span=12, adjust=False).mean()
        ema26 = closes.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        if macd.iloc[-1] > signal.iloc[-1]:
            return "BUY"
        return "SELL"
    except:
        return "WAIT"


def get_bollinger(closes):
    try:
        sma = closes.rolling(20).mean().iloc[-1]
        std = closes.rolling(20).std().iloc[-1]
        upper = sma + 2 * std
        lower = sma - 2 * std
        joriy = closes.iloc[-1]
        if joriy > upper:
            return "SELL (Yuqori)"
        elif joriy < lower:
            return "BUY (Quyi)"
        return "NORMAL"
    except:
        return "NORMAL"


def get_fibonacci(closes):
    try:
        high = closes.tail(66).max()
        low = closes.tail(66).min()
        diff = high - low
        f382 = round(high - 0.382 * diff, 2)
        f500 = round(high - 0.500 * diff, 2)
        f618 = round(high - 0.618 * diff, 2)
        return f382, f500, f618
    except:
        return 0, 0, 0


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
        pb = info.get('priceToBook', 0)
        roe = info.get('returnOnEquity', 0)
        eps = info.get('trailingEps', 0)
        fcf = info.get('freeCashflow', 0)
        div = info.get('dividendYield', 0)
        week52_high = info.get('fiftyTwoWeekHigh', 0)
        week52_low = info.get('fiftyTwoWeekLow', 0)
        sektor = info.get('sector', 'Noma\'lum')
        nom = info.get('longName', tiker)

        if market_cap_raw >= 1e12:
            mc = str(round(market_cap_raw / 1e12, 2)) + " T"
        elif market_cap_raw >= 1e9:
            mc = str(round(market_cap_raw / 1e9, 2)) + " B"
        else:
            mc = str(round(market_cap_raw / 1e6, 2)) + " M"

        if fcf >= 1e9:
            fcf_text = str(round(fcf / 1e9, 2)) + " B"
        elif fcf >= 1e6:
            fcf_text = str(round(fcf / 1e6, 2)) + " M"
        else:
            fcf_text = str(fcf)

        div_text = str(round(div * 100, 2)) + "%" if div else "Tolmaydi"

        tarix = stock.history(period="1y")
        cl = tarix['Close']
        n = len(cl)

        def pct(d):
            if n > d:
                return round(((cl.iloc[-1] - cl.iloc[-(d + 1)]) / cl.iloc[-(d + 1)]) * 100, 2)
            return 0.0

        rsi, rsi_sig = get_rsi(cl)
        macd_sig = get_macd(cl)
        bb_sig = get_bollinger(cl)
        f382, f500, f618 = get_fibonacci(cl)

        tp = round(narx * 1.05, 2)
        sl = round(narx * 0.97, 2)

        qarz = info.get('totalDebt', 0)
        nisbat = round((qarz / market_cap_raw) * 100, 1) if market_cap_raw else 0

        if nisbat < 30:
            h_auto = "HALOL (" + str(nisbat) + "%)"
            halol_emoji = "HALOL"
        elif nisbat <= 33:
            h_auto = "SHUBHALI (" + str(nisbat) + "%)"
            halol_emoji = "SHUBHALI"
        else:
            h_auto = "XAROM (" + str(nisbat) + "%)"
            halol_emoji = "XAROM"

        hd = HALOLLIK.get(tiker, {})
        h_text = hd.get('holat', halol_emoji)
        h_sabab = hd.get('sabab', "Qarz nisbati: " + str(nisbat) + "%")

        try:
            income = stock.financials.iloc[0, 0]
            income_text = "Foyda" if income > 0 else "Zarar"
        except:
            income_text = "Noma'lum"

        ball = 3.0
        izoh = ""
        if h_text == "XAROM":
            ball -= 1.5
            izoh += "Qarz yuklamasi yuqori. "
        else:
            ball += 0.5
            izoh += "Qarz yuklamasi me'yorda (Halol). "
        if rsi <= 35:
            ball += 1.0
            izoh += "RSI oversold - texnik arzon. "
        elif rsi >= 65:
            ball -= 0.5
            izoh += "RSI (" + str(rsi) + "): Narx muvozanatda. "
        else:
            izoh += "RSI (" + str(rsi) + "): Narx muvozanatda. "
        if pe and pe < 15:
            ball += 0.5
            izoh += "P/E past - fundamental arzon. "
        elif pe and pe > 35:
            ball -= 0.5
            izoh += "P/E baland. "
        if income_text == "Foyda":
            ball += 0.5
        else:
            ball -= 0.5

        ball = max(1.0, min(5.0, ball))
        yulduzlar = "★" * int(round(ball))

        if ball >= 4.0:
            baho_text = "ACCUMULATE"
        elif ball >= 3.0:
            baho_text = "HOLD"
        else:
            baho_text = "AVOID"

        # Wall Street target
        ws_target = ""
        try:
            ws = info.get('targetMeanPrice', 0)
            if ws:
                ws_change = round(((ws - narx) / narx) * 100, 2)
                ws_target = "Wall Street Prognoz: " + str(round(ws, 2)) + " USD (" + str(ws_change) + "%)\n"
        except:
            pass

        # Yirik fondlar
        fondlar_text = ""
        try:
            holders = stock.institutional_holders
            if holders is not None and not holders.empty:
                fondlar_text = "Yirik Fondlar:\n"
                for i, row in holders.head(3).iterrows():
                    nom_f = str(row.get('Holder', ''))
                    shares = row.get('Shares', 0)
                    if shares >= 1e6:
                        shares_text = str(round(shares / 1e6, 2)) + " M"
                    else:
                        shares_text = str(shares)
                    fondlar_text += "  " + nom_f + ": " + shares_text + "\n"
        except:
            pass

        # Insayderlar
        insayder_text = "Insayderlar: Barqaror\n"
        try:
            insider = stock.insider_transactions
            if insider is not None and not insider.empty:
                insayder_text = "Insayderlar: " + str(len(insider)) + " ta oxirgi tranzaksiya\n"
        except:
            pass

        # Yangiliklar
        news_text = "Yangiliklar: Topilmadi\n"
        if finnhub_client:
            try:
                news = finnhub_client.company_news(tiker, _from="2024-01-01", to="2099-01-01")
                if news:
                    news_text = "Yangiliklar:\n"
                    for n_item in news[:3]:
                        news_text += "  - " + n_item['headline'][:60] + "\n"
            except:
                pass

        javob = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            + tiker + " | " + nom + "\n"
            "Sektor: " + sektor + " | Shariat: " + h_text + " (" + str(nisbat) + "%)\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Narx: " + str(narx) + " " + valyuta + "\n"
            "52W M/M: " + str(week52_high) + " / " + str(week52_low) + "\n"
            "Cap: " + mc + " | Div: " + div_text + "\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Fundamental Tahlil:\n"
            "P/E: " + str(round(pe, 2) if pe else "—") + " | " + income_text + "\n"
            "P/B: " + str(round(pb, 2) if pb else "—") + " | ROE: " + str(round(roe * 100, 2) if roe else "—") + "% | EPS: " + str(round(eps, 2) if eps else "—") + "\n"
            "FCF: " + fcf_text + "\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Fibonacci (3M):\n"
            "  38.2%: " + str(f382) + " USD\n"
            "  50.0%: " + str(f500) + " USD\n"
            "  61.8%: " + str(f618) + " USD\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Dinamika:\n"
            "1D: " + str(pct(1)) + "% | 1W: " + str(pct(5)) + "% | 1M: " + str(pct(22)) + "%\n"
            "3M: " + str(pct(66)) + "% | 6M: " + str(pct(132)) + "% | 1Y: " + str(pct(252)) + "%\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Indikatorlar:\n"
            "RSI (14): " + str(rsi) + " -> " + rsi_sig + "\n"
            "MACD: " + macd_sig + " | Bollinger: " + bb_sig + "\n"
            "TP: " + str(tp) + " | SL: " + str(sl) + "\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            + ws_target
            + "━━━━━━━━━━━━━━━━━━━━\n"
            + insayder_text
            + "━━━━━━━━━━━━━━━━━━━━\n"
            + fondlar_text
            + "━━━━━━━━━━━━━━━━━━━━\n"
            + news_text
            + "━━━━━━━━━━━━━━━━━━━━\n"
            "BOT BAHOSI: " + str(round(ball, 1)) + "/5.0 " + yulduzlar + " -> " + baho_text + "\n"
            "Izoh: " + izoh
        )

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
