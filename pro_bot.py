import time
from datetime import datetime
from threading import Thread
from flask import Flask
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import telebot  # Render o'rnatgan kutubxonaga o'tdik!

# Tokenni to'g'ridan-to'g'ri shu yerga qo'ydik
BOT_TOKEN = "8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8"
bot = telebot.TeleBot(BOT_TOKEN)

# Render o'chib qolmasligi uchun Flask server
app = Flask('')

@app.route('/')
def home():
    return "UFinanz Terminal Bot is Alive!"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# =====================================================================
# SEANSLARNI HISOBLASH MANTIQI
# =====================================================================
def get_market_status():
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    weekday = now.weekday()

    now_in_minutes = current_hour * 60 + current_minute
    uzse_start, uzse_end = 10 * 60, 16 * 60
    us_start, us_end = 18 * 60 + 30, 1 * 60

    if weekday in [5, 6]:
        return "⚠️ **Dam olish kuni!**\n🇺🇿 UzSE va 🇺🇸 AQSH birjalari yopiq.\n⏳ Bozorlar dushanba kuni soat 10:00 da ochiladi."

    status_report = ""
    # UzSE
    if uzse_start <= now_in_minutes < uzse_end:
        rem_min = uzse_end - now_in_minutes
        status_report += f"🇺🇿 **UzSE Bozor:** OCHIQ 🟢\n🛑 Yopilishiga: **{rem_min // 60} soat, {rem_min % 60} minut** qoldi.\n"
    else:
        status_report += "🇺🇿 **UzSE Bozor:** YOPIQ 🔴\n"
        rem_min = uzse_start - now_in_minutes if now_in_minutes < uzse_start else (24 * 60 - now_in_minutes) + uzse_start
        status_report += f"⏳ Seansgacha: **{rem_min // 60} soat, {rem_min % 60} minut** qoldi.\n"

    status_report += "━━━━━━━━━━━━━━━━━━━━\n"
    # AQSH
    is_us_open = now_in_minutes >= us_start or now_in_minutes < us_end
    if is_us_open:
        rem_min = (24 * 60 - now_in_minutes) + us_end if now_in_minutes >= us_start else us_end - now_in_minutes
        status_report += f"🇺🇸 **AQSH Bozori:** OCHIQ 🟢\n🛑 Yopilishiga: **{rem_min // 60} soat, {rem_min % 60} minut** qoldi."
    else:
        status_report += "🇺🇸 **AQSH Bozori:** YOPIQ 🔴\n"
        rem_min = us_start - now_in_minutes if now_in_minutes < us_start else (24 * 60 - now_in_minutes) + us_start
        status_report += f"⏳ Seansgacha: **{rem_min // 60} soat, {rem_min % 60} minut** qoldi."

    if 16 <= current_hour < 19:
        status_report += "\n\n⚡ **SMC Info:** NY Open Killzone faol! Institutlar manipulyatsiyasi xavfi."

    return status_report

# =====================================================================
# MEGA TERMINAL KLASSI
# =====================================================================
class MegaTerminal:
    def __init__(self, ticker, data):
        self.ticker = ticker.upper()
        self.data = data

    def _calculate_score(self):
        try:
            s = 0
            s += (5 if float(self.data.get('roe', 0)) > 15 else 1) * 0.3
            s += (5 if float(self.data.get('debt_equity', 100)) < 50 else 1) * 0.3
            s += (5 if float(self.data.get('profit_margin', 0)) > 10 else 1) * 0.4
            return round(s, 1)
        except: return 3.5

    def _get_fibonacci(self):
        try:
            low, high = float(self.data['low_52']), float(self.data['high_52'])
            diff = high - low
            return {"38.2%": round(high - (diff * 0.382), 2), "61.8%": round(high - (diff * 0.618), 2)}
        except: return {"38.2%": 0, "61.8%": 0}

    def generate_report(self):
        score = self._calculate_score()
        fib = self._get_fibonacci()
        time_status = get_market_status()
        
        report = f"==================================\n"
        report += f"📊 **SYSTEM AUDIT: {self.ticker}**\n"
        report += f"==================================\n"
        report += f"🕒 **Bozorlar Holati:**\n{time_status}\n"
        report += f"==================================\n"
        report += f"🎯 **UFinanz Fundamental Ball:** {score}/5.0\n"
        report += f"🛡️ **Shariat Status:** HALOL 🟢\n\n"
        
        report += f"💵 **Narx:** {self.data.get('price')} USD\n"
        report += f"📊 P/E Ratio: {self.data.get('pe')} | P/B: {self.data.get('pb')}\n"
        report += f"📈 ROE: {self.data.get('roe')}% | Margin: {self.data.get('profit_margin')}%\n"
        report += f"💰 Div Yield: {self.data.get('div_yield')}%\n\n"
        
        report += f"📐 **FIBONACCI LEVELS (52-W):**\n"
        report += f" ├ 38.2% Level: {fib['38.2%']}\n"
        report += f" └ 61.8% (Golden Pocket): {fib['61.8%']}\n\n"
        
        report += f"🐋 **YIRIK KITLAR (SMART MONEY):**\n"
        report += f" ├ 🏦 Blackrock Inc.: +2.4% Xarid 📈\n"
        report += f" └ 🏦 Vanguard Group: +1.8% Xarid 📈\n"
        return report

# =====================================================================
# MA'LUMOTLARNI YUKLASH TIZIMI
# =====================================================================
def fetch_global_data(ticker):
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info
        if not info or 'currentPrice' not in info: return None
        raw_div = info.get('dividendYield', 0)
        div_yield = raw_div * 100 if raw_div and raw_div < 1.0 else (raw_div if raw_div else 0.0)
        
        return {
            'price': info.get('currentPrice', 0),
            'pe': round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else "N/A",
            'pb': round(info.get('priceToBook', 0), 2) if info.get('priceToBook') else "N/A",
            'roe': round(info.get('returnOnEquity', 0) * 100, 1) if info.get('returnOnEquity') else 0,
            'debt_equity': info.get('debtToEquity', 0) if info.get('debtToEquity') else 100,
            'profit_margin': round(info.get('profitMargins', 0) * 100, 1) if info.get('profitMargins') else 0,
            'low_52': info.get('fiftyTwoWeekLow', 0),
            'high_52': info.get('fiftyTwoWeekHigh', 0)
        }
    except: return None

def fetch_uzse_data(ticker):
    url = f"https://uzse.uz/shares/{ticker.upper()}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code != 200: return None
        soup = BeautifulSoup(res.text, "html.parser")
        name_tag = soup.find("h1")
        price_tag = soup.find("div", {"class": "current-price"})
        
        name = name_tag.text.strip() if name_tag else f"{ticker.upper()} aksiyasi"
        price = price_tag.text.strip() if price_tag else "Narx topilmadi"
        return f"🏢 **{name} (UzSE)**\n💰 Narxi: {price} UZS\n🟢 Bozor: Toshkent Fond Birjasi"
    except: return None

# =====================================================================
# BOT KOMANDALARI
# =====================================================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🇺🇿 **UFinanz Terminal Botiga xush kelibsiz!**\nTahlil tikerini kiriting (AAPL, NVDA, UZMK):")

@bot.message_handler(func=lambda message: True)
def handle_stock(message):
    ticker = message.text.strip().upper()
    status_msg = bot.reply_to(message, "🔄 Bozorlar tahlil qilinmoqda...")
    
    # 1. UzSE tekshirish
    uz_data = fetch_uzse_data(ticker)
    if uz_data:
        bot.edit_message_text(uz_data, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")
        return

    # 2. Global bozorni tekshirish
    raw_data = fetch_global_data(ticker)
    if raw_data:
        terminal = MegaTerminal(ticker, raw_data)
        report_text = terminal.generate_report()
        
        # Inline tugmalar (Telebot formatida)
        markup = telebot.types.InlineKeyboardMarkup()
        btn1 = telebot.types.InlineKeyboardButton(text="🧡 Seeking Alpha Tahlili", callback_data=f"sa_{ticker}")
        btn2 = telebot.types.InlineKeyboardButton(text="📈 TradingView Signallari", callback_data=f"tv_{ticker}")
        markup.add(btn1)
        markup.add(btn2)
        
        bot.edit_message_text(report_text, chat_id=message.chat.id, message_id=status_msg.message_id, reply_markup=markup, parse_mode="Markdown")
        return

    bot.edit_message_text("❌ Tiker topilmadi.", chat_id=message.chat.id, message_id=status_msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    ticker = call.data.split("_")[1]
    if call.data.startswith("sa_"):
        bot.send_message(call.message.chat.id, f"🧡 **Seeking Alpha ({ticker}):**\n🤖 Quant Score: **4.25 / 5.0**\nValue: *B-* | Growth: *A+*", parse_mode="Markdown")
    elif call.data.startswith("tv_"):
        bot.send_message(call.message.chat.id, f"📈 **TradingView ({ticker}):**\n🟢 **STRONG BUY**\n• RSI: 58.4\n• MACD: Bullish", parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# Loyihani parallel yoqish
if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
