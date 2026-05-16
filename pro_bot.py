[16.05.2026 19:40] Эламонов Аброржон ФСБ: import telebot
from telebot import types
import yfinance as yf
import finnhub
import os
import time
from flask import Flask, request

# ===================== SOZLAMALAR =====================
TOKEN = '8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8'  # Tokeningiz
FINNHUB_KEY = 'ctv22h9r01qg80atc9vg'
RENDER_URL = 'https://aksiya-halol-bot.onrender.com'  # Render URL (keyin o'zgartiramiz)

app = Flask(name)
bot = telebot.TeleBot(TOKEN)

try:
    finnhub_client = finnhub.Client(api_key=FINNHUB_KEY)
except:
    finnhub_client = None

# ===================== MA'LUMOTLAR =====================
HALOLLIK = {
    "AAPL": {"holat": "🟢 HALOL", "sabab": "Apple — texnologiya. Halol."},
    "MSFT": {"holat": "🟢 HALOL", "sabab": "Microsoft — dasturiy ta'minot. Halol."},
    "GOOGL": {"holat": "🟢 HALOL", "sabab": "Alphabet (Google) — qidiruv. Halol."},
    "AMZN": {"holat": "🟡 SHUBHALI", "sabab": "Amazon — spirt va ba'zi harom kontent sotadi."},
    "TSLA": {"holat": "🟢 HALOL", "sabab": "Tesla — elektr avtomobil. Halol."},
    "NVDA": {"holat": "🟢 HALOL", "sabab": "NVIDIA — chip va AI. Halol."},
    "META": {"holat": "🟡 SHUBHALI", "sabab": "Meta — ba'zi harom kontent bor."},
    "NFLX": {"holat": "🔴 XAROM", "sabab": "Netflix — harom kontentni tarqatadi."},
    "JPM":  {"holat": "🔴 XAROM", "sabab": "JPMorgan — bank, ribo asosida."},
    "BAC":  {"holat": "🔴 XAROM", "sabab": "Bank of America — ribo asosida."},
    "V":    {"holat": "🟡 SHUBHALI", "sabab": "Visa — ribo tizimiga xizmat qiladi."},
    "MCD":  {"holat": "🔴 XAROM", "sabab": "McDonald's — harom go'sht va spirt."},
    "INTC": {"holat": "🟢 HALOL", "sabab": "Intel — chip. Halol."},
    "AMD":  {"holat": "🟢 HALOL", "sabab": "AMD — chip. Halol."},
    "JNJ":  {"holat": "🟢 HALOL", "sabab": "Johnson & Johnson — tibbiyot. Halol."},
    "PFE":  {"holat": "🟢 HALOL", "sabab": "Pfizer — dori-darmon. Halol."},
    "UZAUTO":     {"holat": "🟢 HALOL", "sabab": "UzAuto Motors — avtomobil. Halol."},
    "NAVOIYAZOT": {"holat": "🟢 HALOL", "sabab": "Navoiyazot — o'g'it. Halol."},
    "ALMALYK":    {"holat": "🟢 HALOL", "sabab": "Olmaliq KMK — konchilik. Halol."},
    "HAMKORBANK": {"holat": "🔴 XAROM", "sabab": "Hamkorbank — ribo asosida. Xarom."},
    "KAPITALBANK":{"holat": "🔴 XAROM", "sabab": "Kapital Bank — ribo asosida. Xarom."},
}

def main_menu():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton("🟢 Halol aksiyalar"),
        types.KeyboardButton("🔴 Harom aksiyalar"),
        types.KeyboardButton("🟡 Shubhali aksiyalar"),
        types.KeyboardButton("🇺🇸 S&P 500"),
        types.KeyboardButton("🏛️ NASDAQ"),
        types.KeyboardButton("🇺🇿 O'zbekiston aksiyalari"),
        types.KeyboardButton("❓ Yordam"),
    )
    return kb

def hisобла_rsi(closes, period=14):
    try:
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period-1, adjust=False).mean()
        avg_loss = loss.ewm(com=period-1, adjust=False).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs.iloc[-1]))
        if rsi >= 70: signal = "SELL 📉"
        elif rsi <= 30: signal = "BUY 📈"
        else: signal = "WAIT ↕️"
        return round(rsi, 2), signal
    except:
        return 50.0, "WAIT ↕️"

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
        "🔥 *PRO Shariat Filtri Botiga xush kelibsiz!*\n\nAksiya tickerini kiriting:",
        parse_mode="Markdown", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    text = message.text.strip()

    if text == "🟢 Halol aksiyalar":
        bot.reply_to(message, "🟢 *Halol:* AAPL, TSLA, NVDA, MSFT, JNJ, PFE", parse_mode="Markdown")
[16.05.2026 19:40] Эламонов Аброржон ФСБ: return
    elif text == "🔴 Harom aksiyalar":
        bot.reply_to(message, "🔴 *Harom:* JPM, BAC, NFLX, MCD, HAMKORBANK", parse_mode="Markdown")
        return
    elif text == "🟡 Shubhali aksiyalar":
        bot.reply_to(message, "🟡 *Shubhali:* AMZN, META, V, MA", parse_mode="Markdown")
        return
    elif text == "🇺🇸 S&P 500":
        bot.reply_to(message, "🇺🇸 *S&P 500:* Amerikaning eng yirik 500 ta kompaniyasi indeksi.", parse_mode="Markdown")
        return
    elif text == "🏛️ NASDAQ":
        bot.reply_to(message, "🏛️ *NASDAQ:* Texnologiya kompaniyalari birjasi.", parse_mode="Markdown")
        return
    elif text == "🇺🇿 O'zbekiston aksiyalari":
        matn = "🇺🇿 *O'zbekiston aksiyalari:*\n\n"
        for t in ["UZAUTO", "NAVOIYAZOT", "ALMALYK", "HAMKORBANK", "KAPITALBANK"]:
            d = HALOLLIK.get(t, {})
            matn += f"*{t}* — {d.get('holat','')}\n{d.get('sabab','')}\n\n"
        bot.reply_to(message, matn, parse_mode="Markdown")
        return
    elif text == "❓ Yordam":
        bot.reply_to(message, "❓ Ticker yozing: AAPL, TSLA, NVDA, UZAUTO", parse_mode="Markdown")
        return

    try:
        tiker = text.upper()
        bot.send_chat_action(message.chat.id, 'typing')
        stock = yf.Ticker(tiker)
        info = stock.info

        if not info or 'currentPrice' not in info:
            bot.reply_to(message, "❌ Aksiya topilmadi.")
            return

        narx = info.get('currentPrice', 0)
        valyuta = info.get('currency', 'USD')
        market_cap_raw = info.get('marketCap', 0)
        pe = info.get('trailingPE', "—")

        if market_cap_raw >= 1e12: mc = f"{market_cap_raw/1e12:.2f}T"
        elif market_cap_raw >= 1e9: mc = f"{market_cap_raw/1e9:.2f}B"
        else: mc = f"{market_cap_raw/1e6:.2f}M"

        tarix = stock.history(period="1y")
        cl = tarix['Close']
        n = len(cl)

        def pct(d):
            if n > d: return ((cl.iloc[-1] - cl.iloc[-(d+1)]) / cl.iloc[-(d+1)]) * 100
            return 0.0

        rsi, rsi_sig = hisобла_rsi(cl)
        tp = narx * 1.05
        sl = narx * 0.97

        qarz = info.get('totalDebt', 0)
        nisbat = (qarz / market_cap_raw) * 100 if market_cap_raw else 0
        if nisbat < 30: h_auto = f"🟢 HALOL ({nisbat:.1f}%)"
        elif nisbat <= 33: h_auto = f"🟡 SHUBHALI ({nisbat:.1f}%)"
        else: h_auto = f"🔴 XAROM ({nisbat:.1f}%)"

        hd = HALOLLIK.get(tiker, {})
        h_text = hd.get('holat', h_auto)
        h_sabab = hd.get('sabab', f"Qarz nisbati: {nisbat:.1f}%")

        news_text = ""
        if finnhub_client:
            try:
                news = finnhub_client.company_news(tiker, _from="2024-01-01", to="2099-01-01")
                for n_item in (news or [])[:3]:
                    news_text += f"• [{n_item['headline'][:55]}...]({n_item['url']})\n"
            except: pass

        javob = f"""📊 *{tiker}* | {info.get('longName', tiker)}
💎 {mc} | P/E: {f'{pe:.1f}' if isinstance(pe, float) else pe}

💰 *Narx:* {narx} {valyuta}

📈 *O'zgarish:*
└ 1D: {pct(1):+.2f}% | 1W: {pct(5):+.2f}%
└ 1M: {pct(22):+.2f}% | 1Y: {pct(252):+.2f}%

🧭 RSI: {rsi} → {rsi_sig}
🎯 TP: {tp:.2f} | 🛑 SL: {sl:.2f}

⚖️ *Shariat:* {h_text}
📝 {h_sabab}"""

        if news_text:
            javob += f"\n\n📰 *Yangiliklar:*\n{news_text}"

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📈 TradingView", url=f"https://www.tradingview.com/symbols/{tiker}/"))
        bot.reply_to(message, javob, parse_mode="Markdown", reply_markup=kb, disable_web_page_preview=True)

    except Exception as e:
        bot.reply_to(message, "❌ Xatolik yuz berdi. Qayta urining.")
        print(f"Xato: {e}")

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode('UTF-8'))
    bot.process_new_updates([update])
    return '!', 200

@app.route('/')
def index():
    return 'Bot ishlayapti! ✅', 200
[16.05.2026 19:40] Эламонов Аброржон ФСБ: if name == 'main':
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=RENDER_URL + '/' + TOKEN)
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
