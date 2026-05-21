import telebot
from telebot import types
import yfinance as yf
from datetime import datetime
import zoneinfo
import matplotlib.pyplot as plt
import os

TOKEN = "8781183838:AAGkxCEkz4gYxDycD3jB8dXiBQ59OXg73uY"
bot = telebot.TeleBot(TOKEN)


# ==================== PROFESSIONAL TAHLIL + WALL STREET ====================
def get_professional_analysis(ticker: str):
    try:
        ticker = ticker.strip().upper()
        stock = yf.Ticker(ticker)
        i = stock.info

        def safe_get(key, default=None):
            val = i.get(key)
            return val if val is not None else default

        price = safe_get('currentPrice')
        market_cap = safe_get('marketCap', 0) / 1e9
        roe = safe_get('returnOnEquity', 0) * 100
        margin = safe_get('profitMargins', 0) * 100
        debt = safe_get('totalDebt', 0) / 1e9
        cash = safe_get('totalCash', 0) / 1e9
        employees = safe_get('fullTimeEmployees')

        # Wall Street Analyst ma'lumotlari
        target_mean = safe_get('targetMeanPrice')
        target_high = safe_get('targetHighPrice')
        target_low = safe_get('targetLowPrice')
        num_analysts = safe_get('numberOfAnalystOpinions')
        recommendation = safe_get('recommendationKey', 'N/A').upper()

        # Signal
        if recommendation in ['STRONG BUY', 'BUY']:
            signal = "🟢 STRONG BUY"
        elif recommendation == 'HOLD':
            signal = "⚪ HOLD"
        else:
            signal = "🔴 SELL / CAREFUL"

        msg = f"""🚨 <b>Professional Tahlil: {ticker}</b>
━━━━━━━━━━━━━━━━━━━━
🏢 <b>Kompaniya:</b> {safe_get('longName', ticker)}
├ Market Cap: <b>{market_cap:.2f}B</b>
├ IPO: {safe_get('ipoDate', 'N/A')}
└ Ishchilar: <b>{employees:,}</b> nafar

💰 <b>Moliyaviy Holat:</b>
├ Naqd pul: <b>{cash:.2f}B</b> | Qarz: <b>{debt:.2f}B</b>
├ ROE: <b>{roe:.1f}%</b> | Margin: <b>{margin:.1f}%</b>
└ P/E: <b>{safe_get('trailingPE', 'N/A')}</b>

🏗 <b>SMC & Likvidlik:</b>
├ BSL: <b>{(price * 1.05):.2f}$</b>
├ SSL: <b>{(price * 0.95):.2f}$</b>
└ Order Block: <b>{(price * 0.97):.2f}$</b>

🐋 <b>Kitlar (Institutsiyalar):</b>
• BlackRock ≈ {safe_get('heldPercentInstitutions', 0)*0.4:.2f}%
• Vanguard ≈ {safe_get('heldPercentInstitutions', 0)*0.35:.2f}%
• State Street ≈ {safe_get('heldPercentInstitutions', 0)*0.15:.2f}%

📊 <b>Wall Street Analyst Tahlili:</b>
├ Analystlar soni: <b>{num_analysts}</b>
├ O‘rtacha Target: <b>{target_mean:.2f}$</b> ({((target_mean/price)-1)*100:+.1f}%)
├ Yuqori Target: <b>{target_high:.2f}$</b>
├ Pastki Target: <b>{target_low:.2f}$</b>
└ Umumiy Tavsiya: <b>{recommendation}</b>

━━━━━━━━━━━━━━━━━━━━
🎯 <b>BOT SIGNAL:</b> <b>{signal}</b>

💡 <b>Xulosa:</b> {"Wall Street analystlari ham ijobiy fikrda." if target_mean and target_mean > price else "Ehtiyotkorlik bilan kuzatish tavsiya etiladi."}"""

        return msg

    except Exception as e:
        return f"❌ Tahlilni yuklashda xatolik.\nTo‘g‘ri tiker yuboring (masalan: AAPL, NKE, BTC-USD)."


# ==================== BOOKMAP GRAFIKASI ====================
def send_bookmap_chart(message, ticker: str):
    try:
        ticker = ticker.strip().upper()
        data = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if data.empty:
            bot.reply_to(message, "❌ Ma'lumot topilmadi.")
            return

        plt.figure(figsize=(12, 8))
        plt.subplot(2, 1, 1)
        plt.plot(data.index, data['Close'], label='Close Price', color='blue', linewidth=2.5)
        plt.title(f"{ticker} - Narx Grafigi (1 Oy)")
        plt.legend()
        plt.grid(True)

        plt.subplot(2, 1, 2)
        plt.bar(data.index, data['Volume'], color='purple', alpha=0.8)
        plt.title("Savdo Hajmi (Volume)")
        plt.grid(True)

        plt.tight_layout()
        
        filename = f"{ticker}_chart.png"
        plt.savefig(filename)
        plt.close()

        with open(filename, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=f"📊 {ticker} — Bookmap uslubidagi tahlil")
        os.remove(filename)

    except:
        pass  # Grafika muammosi bo'lsa ham tahlil chiqsin


# ==================== START VA HANDLER ====================
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📈 Fond bozori", "₿ Crypto")
    markup.add("🌍 Forex", "🛢 Xomashyo")
    markup.add("⚔️ Raqobat tahlili", "🐳 Kitlar & Siyosat")
    markup.add("⏰ Bozor vaqti", "📰 Yangiliklar")
    markup.add("📖 Lug'at", "📊 Bookmap")
    markup.add("🆘 Adminlik (Yordam)")

    bot.send_message(message.chat.id, "👋 <b>Aksiya Halol Bot</b> ga xush kelibsiz!\n\nTahlil qilish uchun ticker yuboring yoki menyudan tanlang.", 
                     reply_markup=markup, parse_mode="HTML")


@bot.message_handler(func=lambda m: True)
def handle_buttons(message):
    text = message.text.strip()

    if text == "📊 Bookmap":
        bot.reply_to(message, "📊 Bookmap rejimi yoqildi!\nEndi ticker yuboring (AAPL, NKE, BTC-USD...)", parse_mode="HTML")
        return

    elif text in ["📖 Lug'at", "⏰ Bozor vaqti", "📰 Yangiliklar", "🐳 Kitlar & Siyosat", "⚔️ Raqobat tahlili", "🆘 Adminlik (Yordam)"]:
        bot.reply_to(message, f"{text} bo‘limi tez orada to‘liq ishga tushadi.", parse_mode="HTML")
        return

    # Asosiy tahlil
    send_bookmap_chart(message, text)          # Grafika (agar muvaffaqiyatli bo'lsa)
    analysis = get_professional_analysis(text)
    bot.reply_to(message, analysis, parse_mode="HTML")


if __name__ == "__main__":
    print("🚀 Aksiya Halol Bot ishga tushdi...")
    bot.infinity_polling(none_stop=True, interval=0)
