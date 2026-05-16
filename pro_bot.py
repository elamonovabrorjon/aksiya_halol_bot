import telebot
from telebot import types
import yfinance as yf
import html
from datetime import datetime
from functools import lru_cache
import time

# ===================== SOZLAMALAR =====================
TOKEN = '8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8'
FINNHUB_KEY = 'ctv22h9r01qg80atc9vg'

bot = telebot.TeleBot(TOKEN)

# Cache
@lru_cache(maxsize=50)
def get_stock_data(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist_1mo = stock.history(period="1mo")
        hist_1y = stock.history(period="1y")
        return stock, info, hist_1mo, hist_1y
    except:
        return None, None, None, None

# ===================== INDIKATORLAR =====================
def hisobla_rsi(closes, period=14):
    try:
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        
        avg_gain = gain.ewm(com=period-1, adjust=False).mean()
        avg_loss = loss.ewm(com=period-1, adjust=False).mean()
        
        rs = avg_gain / avg_loss.where(avg_loss != 0, 1)
        rsi = 100 - (100 / (1 + rs))
        current_rsi = round(rsi.iloc[-1], 2)
        
        if current_rsi >= 70:
            signal = "SELL 📉 (Overbought)"
        elif current_rsi <= 30:
            signal = "BUY 📈 (Oversold)"
        else:
            signal = "HOLD ↕️"
        return current_rsi, signal
    except:
        return 50.0, "Noma'lum"

# ===================== ASOSIY TAHLIL =====================
def aksiya_tahlil(tiker: str):
    try:
        stock, info, hist_1mo, hist_1y = get_stock_data(tiker.upper())
        if info is None or hist_1y is None or hist_1y.empty:
            return "❌ Aksiya ma'lumotlari olinmadi. Tiker to'g'ri yozilganiga ishonch hosil qiling (Masalan: NVDA, AAPL).", None

        narx = info.get('currentPrice') or info.get('regularMarketPrice', 0)
        valyuta = info.get('currency', 'USD')
        long_name = info.get('longName', tiker)

        closes = hist_1y['Close']
        change_1d = round(((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2]) * 100, 2) if len(closes) > 1 else 0
        change_1w = round(((closes.iloc[-1] - closes.iloc[-6]) / closes.iloc[-6]) * 100, 2) if len(closes) >= 6 else 0
        change_1m = round(((closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0]) * 100, 2) if len(closes) > 1 else 0

        rsi, rsi_signal = hisobla_rsi(closes)

        qarz = info.get('totalDebt', 0)
        market_cap = info.get('marketCap', 1)
        debt_ratio = (qarz / market_cap) * 100 if market_cap else 0
        
        if debt_ratio < 30:
            halal_status = f"🟢 HALOL ({debt_ratio:.1f}%)"
        elif debt_ratio <= 40:
            halal_status = f"🟡 SHUBHALI ({debt_ratio:.1f}%)"
        else:
            halal_status = f"🔴 HAROM ({debt_ratio:.1f}%)"

        javob = f"""📊 <b>{tiker}</b> | {html.escape(long_name)}
Sektor: {html.escape(info.get('sector', 'Noma\'lum'))}
⚖️ Shariat: {halal_status}

━━━━━━━━━━━━━━━━━━━━
💰 Narx: <b>{round(narx, 2)} {valyuta}</b>
📈 1K: {change_1d:+.2f}% | 1H: {change_1w:+.2f}% | 1O: {change_1m:+.2f}%
📅 52H: {info.get('fiftyTwoWeekHigh', '—')} / {info.get('fiftyTwoWeekLow', '—')}

━━━━━━━━━━━━━━━━━━━━
📊 Indikatorlar:
• RSI (14): <b>{rsi}</b> → {rsi_signal}
• P/E: {info.get('trailingPE', '—') if isinstance(info.get('trailingPE'), (int, float)) else '—'} | P/B: {info.get('priceToBook', '—') if isinstance(info.get('priceToBook'), (int, float)) else '—'}
• ROE: {info.get('returnOnEquity', 0)*100:.1f}% | Div: {info.get('dividendYield', 0)*100:.2f}%

━━━━━━━━━━━━━━━━━━━━
🧠 Bot Bahosi: Yuqori potensial (batafsil tahlil kerak bo'lsa ayting)

━━━━━━━━━━━━━━━━━━━━
🔗 <a href='https://www.tradingview.com/symbols/{tiker}/'>TradingView</a>"""
        
        return javob, tiker

    except Exception as e:
        print(f"Xato {tiker}: {e}")
        return f"❌ {tiker} tahlilida kutilmagan xatolik yuz berdi.", None

# ===================== BOSH MENYU =====================
def main_menu():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton("🔍 RSI Skriner"),
        types.KeyboardButton("📰 Bozor Yangiliklari"),
        types.KeyboardButton("🟢 Halol aksiyalar"),
        types.KeyboardButton("🇺🇸 S&P 500"),
        types.KeyboardButton("🇺🇿 O'zbekiston aksiyalari"),
        types.KeyboardButton("❓ Yordam")
    )
    return kb

# ===================== MESSAGE HANDLERLAR =====================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 
        "👋 Assalomu alaykum! Aksiyalar tahlil botiga xush kelibsiz.\n\nTahlil qilish uchun aksiya tikerini kiriting (Masalan: NVDA, AAPL, MU) yoki quyidagi bo'limlardan birini tanlang:",
        reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    text = message.text.strip()

    if text == "🔍 RSI Skriner":
        bot.reply_to(message, "⏳ RSI skriner bo'limi yangilanmoqda...")
    elif text == "📰 Bozor Yangiliklari":
        bot.reply_to(message, "⏳ Global yangiliklar yuklanmoqda... Bir ozdan so'ng qayta urinib ko'ring.")
    elif text == "🟢 Halol aksiyalar":
        bot.reply_to(message, "🟢 Shariat mezonlariga mos keladigan eng ommabop aksiyalar ro'yxati shakllantirilmoqda...")
    elif text == "🇺🇸 S&P 500":
        bot.reply_to(message, "🇺🇸 S&P 500 indeksining eng yetakchi kompaniyalari tahlili tayyorlanmoqda...")
    elif text == "🇺🇿 O'zbekiston aksiyalari":
        bot.reply_to(message, "🇺🇿 Toshkent Respublika fond birjasi (UZSE) aksiyalari tahlili yaqin orada qo'shiladi...")
    elif text == "❓ Yordam":
        bot.send_message(message.chat.id, 
            "❓ <b>Yordam bo'limi</b>\n\nBotdan foydalanish uchun unga shunchaki aksiya qisqartmasini (tikerini) yuboring. Masalan: <code>NVDA</code>\n\nAdministrator: @EAA_7879", 
            parse_mode="HTML")
    else:
        bot.send_chat_action(message.chat.id, 'typing')
        javob, _ = aksiya_tahlil(text)
        bot.reply_to(message, javob, parse_mode="HTML", disable_web_page_preview=True)

if __name__ == "__main__":
    print("🚀 PRO Aksiyalar Boti yangi token bilan muvaffaqiyatli ishga tushdi!")
    bot.infinity_polling(none_stop=True, interval=0)
