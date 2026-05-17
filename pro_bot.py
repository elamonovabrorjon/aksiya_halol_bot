import telebot
from telebot import types
import yfinance as yf
import html
from functools import lru_cache
import threading
from flask import Flask

# ===================== SINOV UCHUN VEB-SERVER (RENDER TEKSHIRUVI UCHUN) =====================
app = Flask('')

@app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlamoqda!"

def run_flask():
    # Render avtomatik taqdim etadigan 10000-portni tinglaydi
    app.run(host='0.0.0.0', port=10000)

# ===================== SOZLAMALAR =====================
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
        
        if current_rsi >= 70: signal = "SELL 📉"
        elif current_rsi <= 30: signal = "BUY 📈"
        else: signal = "HOLD ↕️"
        return current_rsi, signal
    except:
        return "—", "HOLD ↕️"

def aksiya_tahlil(tiker: str):
    try:
        tiker_clean = tiker.strip().upper()
        stock, info, hist = get_stock_data(tiker_clean)
        
        if info is None or hist is None or hist.empty:
            return f"❌ <b>{tiker_clean}</b> bo'yicha ma'lumot topilmadi.", None

        narx = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 0)
        valyuta = info.get('currency', 'USD')
        long_name = info.get('longName') or info.get('shortName') or tiker_clean
        closes = hist['Close']
        change_1d = round(((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2]) * 100, 2) if len(closes) > 1 else 0

        rsi, rsi_signal = hisobla_rsi(closes)
        qarz = info.get('totalDebt', 0)
        market_cap = info.get('marketCap', 1)
        debt_ratio = (qarz / market_cap) * 100 if market_cap else 0
        
        if debt_ratio < 30: halal_status = f"🟢 HALOL ({debt_ratio:.1f}%)"
        elif debt_ratio <= 40: halal_status = f"🟡 SHUBHALI ({debt_ratio:.1f}%)"
        else: halal_status = f"🔴 HAROM ({debt_ratio:.1f}%)"

        def safe_num(val, mode=None):
            if val is None or isinstance(val, str): return "—"
            try:
                if mode == "percent": return f"{round(float(val) * 100, 2)}%"
                return f"{round(float(val), 2)}"
            except: return "—"

        high_52 = safe_num(info.get('fiftyTwoWeekHigh'))
        low_52 = safe_num(info.get('fiftyTwoWeekLow'))

        javob = f"""📊 <b>{tiker_clean}</b> | {html.escape(long_name)}
Sektor: {html.escape(info.get('sector', 'Noma\'lum'))}
⚖️ Shariat: {halal_status}

━━━━━━━━━━━━━━━━━━━━
💰 Narx: <b>{safe_num(narx)} {valyuta}</b> ({change_1d:+.2f}%)
📅 52H: {high_52} / {low_52}

━━━━━━━━━━━━━━━━━━━━
📊 Indikatorlar:
• RSI (14): <b>{rsi}</b> → {rsi_signal}
• P/E: {safe_num(info.get('trailingPE'))} | P/B: {safe_num(info.get('priceToBook'))}
• ROE: {safe_num(info.get('returnOnEquity'), 'percent')} | Div: {safe_num(info.get('dividendYield'), 'percent')}

━━━━━━━━━━━━━━━━━━━━
🔗 <a href='https://www.tradingview.com/symbols/{tiker_clean}/'>TradingView tabli</a>"""
        
        return javob, tiker_clean
    except:
        return f"❌ {tiker.upper()} tahlilida xatolik yuz berdi.", None

def main_menu():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton("🔍 RSI Skriner"), types.KeyboardButton("📰 Bozor Yangiliklari"),
        types.KeyboardButton("🟢 Halol aksiyalar"), types.KeyboardButton("🟡 Shubhali aksiyalar"),
        types.KeyboardButton("🇺🇸 S&P 500"), types.KeyboardButton("🇺🇿 O'zbekiston aksiyalari")
    )
    return kb

def inline_aksiyalar(tikerlar):
    kb = types.InlineKeyboardMarkup(row_width=3)
    buttons = [types.InlineKeyboardButton(text=t, callback_data=f"anz_{t}") for t in tikerlar]
    kb.add(*buttons)
    return kb

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 Assalomu alaykum! Aksiyalar tahlil botiga xush kelibsiz.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    text = message.text.strip()
    if text == "🔍 RSI Skriner":
        bot.reply_to(message, "🔍 <b>RSI Skriner:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["NVDA", "AAPL", "MSFT", "TSLA", "AMD", "AMZN"]))
    elif text == "📰 Bozor Yangiliklari":
        bot.reply_to(message, "📰 <b>Bozor Yangiliklari:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["AAPL", "GOOGL", "MSFT", "AMZN"]))
    elif text == "🟢 Halol aksiyalar":
        bot.reply_to(message, "🟢 <b>Halol aksiyalar ro'yxati:</b>", reply_markup=inline_aksiyalar(["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN"]))
    elif text == "🟡 Shubhali aksiyalar":
        bot.reply_to(message, "🟡 <b>Shubhali aksiyalar ro'yxati:</b>", reply_markup=inline_aksiyalar(["AMZN", "META", "V", "PYPL"]))
    elif text == "🇺🇸 S&P 500":
        bot.reply_to(message, "🇺🇸 <b>S&P 500 indeksidagi yetakchilar:</b>", reply_markup=inline_aksiyalar(["AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META"]))
    elif text == "🇺🇿 O'zbekiston aksiyalari":
        bot.reply_to(message, "🇺🇿 <b>Toshkent Respublika fond birjasi (UZSE):</b>\nTez orada ishga tushadi.")
    else:
        bot.send_chat_action(message.chat.id, 'typing')
        javob, _ = aksiya_tahlil(text)
        bot.reply_to(message, javob, parse_mode="HTML", disable_web_page_preview=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("anz_"))
def callback_handler(call):
    ticker = call.data.split("_")[1]
    bot.send_chat_action(call.message.chat.id, 'typing')
    javob, _ = aksiya_tahlil(ticker)
    bot.send_message(call.message.chat.id, javob, parse_mode="HTML", disable_web_page_preview=True)
    bot.answer_callback_query(call.id)

# ===================== PROTOKOL ISHGA TUSHISHI =====================
if __name__ == "__main__":
    # 1. Server tekshiruvi uchun fon rejimida Flask veb-sahifasini yoqamiz
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    # 2. Botning o'zini yoqamiz
    bot.polling(none_stop=True, skip_pending=True)
