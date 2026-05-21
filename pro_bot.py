import telebot
from telebot import types
import yfinance as yf

# Tokeningiz
TOKEN = "8781183838:AAGkxCEkz4gYxDycD3jB8dXiBQ59OXg73uY"
bot = telebot.TeleBot(TOKEN)

# 18 TA PARAMETRNI HISOBLASH FUNKSIYASI
def get_18_point_analysis(ticker):
    try:
        stock = yf.Ticker(ticker)
        i = stock.info
        
        # DCF va Fundamental hisoblar
        debt_ratio = (i.get('totalDebt', 0) / i.get('totalAssets', 1)) * 100
        dcf = (i.get('freeCashflow', 0) * 1.05) / 0.10
        rec = "✅ SOTIB OL" if dcf > i.get('currentPrice', 0) else "⚠️ SOT/KUT"
        
        msg = f"🔍 <b>{ticker.upper()} - 18 TA MOLIYAVIY ANALIZ</b>\n" \
              f"━━━━━━━━━━━━━━━━━━━━\n" \
              f"1. Narx: {i.get('currentPrice')}$ | 2. Market Cap: {i.get('marketCap',0)/1e9:.2f}B\n" \
              f"3. P/E: {i.get('trailingPE')} | 4. P/S: {i.get('priceToSalesTrailing12Months')}\n" \
              f"5. ROE: {i.get('returnOnEquity', 0)*100:.1f}% | 6. ROA: {i.get('returnOnAssets', 0)*100:.1f}%\n" \
              f"7. Debt/Equity: {debt_ratio:.1f}% | 8. FCF: {i.get('freeCashflow', 0)}\n" \
              f"9. Revenue Growth: {i.get('revenueGrowth', 0)*100:.1f}% | 10. Margin: {i.get('profitMargins', 0)*100:.1f}%\n" \
              f"11. Book Value: {i.get('bookValue')} | 12. Div Yield: {i.get('dividendYield', 0)*100:.1f}%\n" \
              f"13. Beta: {i.get('beta')} | 14. Kitlar (Inst.): {i.get('heldPercentInstitutions', 0)*100:.1f}%\n" \
              f"15. IPO: {i.get('ipoDate')} | 16. Ishchilar: {i.get('fullTimeEmployees')}\n" \
              f"17. DCF Bahosi: {dcf/1e9:.2f}B $ | 18. Xulosa: <b>{rec}</b>\n" \
              f"🕌 <b>Halollik Statusi:</b> {'✅ HALOL' if debt_ratio < 33 else '❌ HARAM'}"
        return msg
    except Exception as e:
        return f"❌ Analiz uchun yetarli ma'lumot topilmadi: {e}"

# MENYU TUGMALARI
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("📊 Fond bozori"),
        types.KeyboardButton("₿ Crypto"),
        types.KeyboardButton("📊 Bookmap"),
        types.KeyboardButton("🆘 Adminlik (Yordam)")
    )
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Assalomu alaykum! Tahlil uchun tiker kiriting.", reply_markup=main_menu())

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text
    if text in ["📊 Fond bozori", "₿ Crypto", "📊 Bookmap", "🆘 Adminlik (Yordam)"]:
        bot.reply_to(message, "Tiker kiriting (Masalan: AAPL, BTC):")
    else:
        bot.reply_to(message, get_18_point_analysis(text), parse_mode="HTML")

if __name__ == "__main__":
    print("Bot muvaffaqiyatli ishga tushdi...")
    bot.polling(none_stop=True)
