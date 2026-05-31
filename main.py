 import telebot
from telebot import types
import yfinance as yf
from datetime import datetime
import zoneinfo
import matplotlib.pyplot as plt
import os

TOKEN = "8781183838:AAHiM56nUTuyLSZcjj4qhPVZKA2BdYL7Y2Q"
bot = telebot.TeleBot(TOKEN)


# ==================== 18 TA TAHLIL ====================
def get_18_point_analysis(ticker: str):
    try:
        ticker = ticker.strip().upper()
        stock = yf.Ticker(ticker)
        i = stock.info

        def safe_get(key, default=0):
            val = i.get(key)
            return val if val is not None else default

        debt_ratio = (safe_get('totalDebt') / safe_get('totalAssets', 1)) * 100
        fcf = safe_get('freeCashflow')
        price = safe_get('currentPrice')
        dcf = (fcf * 1.05) / 0.10 if fcf > 0 else 0

        rec = "✅ SOTIB OL" if dcf > price * 1.1 else "⚠️ SOTISH YOKI KUTING"

        return f"""🔍 <b>{ticker} - 18 TA MOLIYAVIY TAHLIL</b>
━━━━━━━━━━━━━━━━━━━━
1. Narx: <b>{price:.2f}$</b>
2. Market Cap: <b>{safe_get('marketCap',0)/1e9:.2f}B</b>
3. P/E: <b>{safe_get('trailingPE', 'N/A')}</b>
4. P/S: <b>{safe_get('priceToSalesTrailing12Months', 'N/A')}</b>
5. ROE: <b>{safe_get('returnOnEquity',0)*100:.1f}%</b>
6. ROA: <b>{safe_get('returnOnAssets',0)*100:.1f}%</b>
7. Debt/Assets: <b>{debt_ratio:.1f}%</b>
8. FCF: <b>{fcf/1e9:.2f}B</b>
9. Rev. Growth: <b>{safe_get('revenueGrowth',0)*100:.1f}%</b>
10. Margin: <b>{safe_get('profitMargins',0)*100:.1f}%</b>
11. Book Value: <b>{safe_get('bookValue','N/A')}</b>
12. Div Yield: <b>{safe_get('dividendYield',0)*100:.1f}%</b>
13. Beta: <b>{safe_get('beta','N/A')}</b>
14. Institutsiyalar: <b>{safe_get('heldPercentInstitutions',0)*100:.1f}%</b>
15. Ishchilar: <b>{safe_get('fullTimeEmployees','N/A')}</b>
16. DCF Bahosi: <b>{dcf/1e9:.2f}B $</b>
17. Xulosa: <b>{rec}</b>
🕌 <b>Halollik:</b> {'✅ HALOL' if debt_ratio < 33 else '❌ HARAM'}"""
    except Exception as e:
        return f"❌ Xatolik: {str(e)[:120]}
Ticker to‘g‘riligini tekshiring."


# ==================== BOOKMAP GRAFIKASI ====================
def send_bookmap_chart(message, ticker: str):
    try:
        ticker = ticker.strip().upper()
        data = yf.download(ticker, period="1mo", interval="1d", progress=False)
        
        if data.empty:
            bot.reply_to(message, "❌ Ma'lumot topilmadi.")
            return

        plt.figure(figsize=(12, 8))

        # Narx grafigi
        plt.subplot(2, 1, 1)
        plt.plot(data.index, data['Close'], label='Close Price', color='blue', linewidth=2.5)
        plt.title(f"{ticker} - Narx Grafigi (1 Oy)")
        plt.legend()
        plt.grid(True)

        # Volume
        plt.subplot(2, 1, 2)
        plt.bar(data.index, data['Volume'], color='purple', alpha=0.8)
        plt.title("Savdo Hajmi (Volume)")
        plt.grid(True)

        plt.tight_layout()
        
        filename = f"{ticker}_bookmap.png"
        plt.savefig(filename)
        plt.close()

        with open(filename, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, 
                         caption=f"📊 {ticker} — Bookmap uslubidagi tahlil")
        
        os.remove(filename)

    except Exception as e:
        bot.reply_to(message, f"❌ Grafika yaratishda xatolik: {str(e)[:100]}")


# ==================== START ====================
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📈 Fond bozori", "₿ Crypto")
    markup.add("🌍 Forex", "🛢 Xomashyo")
    markup.add("⚔️ Raqobat tahlili", "🐳 Kitlar & Siyosat")
    markup.add("⏰ Bozor vaqti", "📰 Yangiliklar")
    markup.add("📖 Lug'at", "📊 Bookmap")
    markup.add("🆘 Adminlik (Yordam)")

    bot.send_message(
        message.chat.id,
        "👋 <b>Aksiya Halol Bot</b> ga xush kelibsiz!

Kerakli bo‘limni tanlang yoki tiker yuboring.",
        reply_markup=markup,
        parse_mode="HTML"
    )


# ==================== ASOSIY HANDLER ====================
@bot.message_handler(func=lambda m: True)
def handle_buttons(message):
    text = message.text.strip()

    if text == "📖 Lug'at":
        bot.reply_to(message, "📖 Lug'at bo‘limi tez orada to‘liq ishga tushadi.", parse_mode="HTML")

    elif text == "⏰ Bozor vaqti":
        bot.reply_to(message, "⏰ Bozor vaqti bo‘limi tez orada yangilanadi.", parse_mode="HTML")

    elif text == "📰 Yangiliklar":
        bot.reply_to(message, "📰 Yangiliklar bo‘limi tayyorlanmoqda...", parse_mode="HTML")

    elif text == "📊 Bookmap":
        bot.reply_to(message, """📊 <b>Bookmap rejimi yoqildi!</b>

Endi istalgan ticker yuboring:
• AAPL
• BTC-USD
• TSLA
• GC=F (Oltin)

Bot sizga grafika + tahlil yuboradi.""", parse_mode="HTML")

    elif text == "🐳 Kitlar & Siyosat":
        bot.reply_to(message, "🐳 Kitlar & Siyosat bo‘limi tayyorlanmoqda...", parse_mode="HTML")

    elif text == "⚔️ Raqobat tahlili":
        bot.reply_to(message, "⚔️ Raqobat tahlili uchun 2-5 ta tiker yozing (masalan: AAPL MSFT NVDA)", parse_mode="HTML")

    elif text in ["📈 Fond bozori", "₿ Crypto", "🌍 Forex", "🛢 Xomashyo"]:
        bot.reply_to(message, "✅ Tahlil qilmoqchi bo‘lgan tiker yuboring.", parse_mode="HTML")

    elif text == "🆘 Adminlik (Yordam)":
        bot.reply_to(message, "🆘 Yordam kerak bo‘lsa savolingizni yozing.", parse_mode="HTML")

    else:
        if len(text) <= 12 and text.replace('-','').replace('=','').isalnum():
            send_bookmap_chart(message, text)
            analysis = get_18_point_analysis(text)
            bot.reply_to(message, analysis, parse_mode="HTML")
        else:
            analysis = get_18_point_analysis(text)
            bot.reply_to(message, analysis, parse_mode="HTML")


if __name__ == "__main__":
    print("🚀 Aksiya Halol Bot ishga tushdi...")
    bot.infinity_polling(none_stop=True, interval=0)