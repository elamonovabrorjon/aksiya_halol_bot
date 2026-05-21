import telebot
from telebot import types
import yfinance as yf
from datetime import datetime
import os

TOKEN = "8781183838:AAHllgXbYStME1ZLm7nbAx1BF8Qy8Zc5JQw"
bot = telebot.TeleBot(TOKEN)


# ==================== KITLAR & SIYOSATCHILAR ====================
def get_whale_portfolio(query: str):
    q = query.lower().strip()
    
    if any(x in q for x in ["berkshire", "buffett", "1"]):
        return """🐳 <b>1. Berkshire Hathaway (Warren Buffett)</b>

📊 Portfel qiymati: \~$263 milliard

<b>Top Holdinglar:</b>
• AAPL (Apple)
• AXP (American Express)
• KO (Coca-Cola)
• BAC (Bank of America)
• CVX (Chevron)

<b>Oxirgi o‘zgarishlar:</b>
✅ Alphabet (GOOGL) pozitsiyasini oshirgan
❌ Ba’zi energiya kompaniyalaridan chiqqan

<b>Xulosa:</b> Klassik uzun muddatli qiymat investori."""

    elif any(x in q for x in ["pelosi", "nancy", "2"]):
        return """👩‍💼 <b>2. Nancy Pelosi (va eri Paul Pelosi)</b>

Eng mashhur va muvaffaqiyatli siyosatchi trader.

<b>Oxirgi savdolar:</b>
• NVDA, MSFT, AMZN kabi texnologiya aksiyalari
• 2025 yilda portfolio \~ +129% o‘sish ko‘rsatgan

<b>Xulosa:</b> Bozor harakatini juda yaxshi his qiladi. Ko‘pchilik kuzatadi."""

    elif any(x in q for x in ["blackrock", "3"]):
        return """🏦 <b>3. BlackRock</b>

Dunyo eng katta aktiv boshqaruvchisi (\~$10 trillion).

Asosan passiv investitsiya (indeks fondlari) orqali ishlaydi. AAPL, MSFT, NVDA eng katta holdinglari."""

    else:
        return """🐳 <b>Kitlar & Siyosatchilar Ro‘yxati</b>

<b>Mashhur Kitlar:</b>
1. Berkshire Hathaway (Warren Buffett)
3. BlackRock
4. Vanguard Group

<b>AQSh Siyosatchilari:</b>
2. Nancy Pelosi
5. Richard Blumenthal
6. Josh Gottheimer
7. Michael McCaul

Raqam yoki ism yozing (masalan: Pelosi yoki 2)"""

# ==================== PROFESSIONAL TAHLIL (oldingi versiya) ====================
def get_professional_analysis(ticker: str):
    try:
        ticker = ticker.strip().upper()
        stock = yf.Ticker(ticker)
        i = stock.info

        def safe_get(key, default=None):
            val = i.get(key)
            return val if val is not None else default

        debt_ratio = (safe_get('totalDebt', 0) / safe_get('totalAssets', 1)) * 100

        msg = f"""🚨 <b>Professional Tahlil: {ticker}</b>
━━━━━━━━━━━━━━━━━━━━
🏢 <b>{safe_get('longName', ticker)}</b>
├ Sector: {safe_get('sector', 'N/A')}
├ Market Cap: <b>{safe_get('marketCap', 0)/1e9:.2f}B</b>

💰 Moliyaviy Holat:
├ Debt/Assets: <b>{debt_ratio:.1f}%</b>
├ ROE: <b>{safe_get('returnOnEquity',0)*100:.1f}%</b>
└ P/E: <b>{safe_get('trailingPE', 'N/A')}</b>

🕌 <b>Halollik:</b> {'✅ HALOL' if debt_ratio < 33 else '❌ HARAM'}

📊 Wall Street Target: <b>{safe_get('targetMeanPrice', 'N/A')}</b>$

🎯 <b>BOT SIGNAL:</b> {'🟢 BUY' if debt_ratio < 35 else '⚪ HOLD'}"""

        return msg
    except:
        return "❌ Tahlil yuklanmadi. Ticker to‘g‘riligini tekshiring."


# ==================== START ====================
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📈 Fond bozori", "₿ Crypto")
    markup.add("🌍 Forex", "🛢 Xomashyo")
    markup.add("⚔️ Raqobat tahlili", "🐳 Kitlar & Siyosat")
    markup.add("⏰ Bozor vaqti", "📊 Bookmap")
    markup.add("📖 Lug'at", "🆘 Yordam")

    bot.send_message(message.chat.id, 
        "👋 <b>Aksiya Halol Bot</b> ga xush kelibsiz!\n\nMenyudan tanlang yoki tiker yuboring.",
        reply_markup=markup, parse_mode="HTML")


# ==================== HANDLER ====================
@bot.message_handler(func=lambda m: True)
def handle_buttons(message):
    text = message.text.strip()

    if text == "🐳 Kitlar & Siyosat":
        bot.reply_to(message, get_whale_portfolio(text), parse_mode="HTML")

    elif text == "⏰ Bozor vaqti":
        bot.reply_to(message, "⏰ Bozor vaqti bo‘limi ishlamoqda...", parse_mode="HTML")  # oldingi funksiyani qo‘shsa bo‘ladi

    elif text == "📊 Bookmap":
        bot.reply_to(message, "📊 Bookmap rejimi yoqildi! Ticker yuboring.", parse_mode="HTML")

    else:
        # Kitlar yoki siyosatchi ism/raqam bo‘lsa
        if any(x in text.lower() for x in ["pelosi", "buffett", "berkshire", "blackrock", "vanguard"]):
            bot.reply_to(message, get_whale_portfolio(text), parse_mode="HTML")
        else:
            # Oddiy tahlil
            analysis = get_professional_analysis(text)
            bot.reply_to(message, analysis, parse_mode="HTML")


if __name__ == "__main__":
    print("🚀 Bot ishga tushdi...")
    bot.infinity_polling(none_stop=True, interval=0)
