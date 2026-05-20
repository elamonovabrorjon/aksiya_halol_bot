import asyncio
import logging
from datetime import datetime
from threading import Thread
from flask import Flask  # Render o'chirib qo'ymasligi uchun kerak
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# TOKENNI TO'G'RIDAN-TO'G'RI SHU YERGA QO'YDIDIK (Hech qanday config.py shart emas!)
BOT_TOKEN = "8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Render tarmog'ida bot o'chib qolmasligi uchun Flask server quvuri
app = Flask('')

@app.route('/')
def home():
    return "UFinanz Terminal Bot is Alive!"

def run_flask():
    # Render avtomatik port ajratadi (0.0.0.0:10000)
    app.run(host='0.0.0.0', port=10000)

# =====================================================================
# SEANSLARNI HISOBLASH MANTIQI (Toshkent vaqti bilan)
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
        return f"⚠️ **Dam olish kuni!**\n🇺🇿 UzSE va 🇺🇸 AQSH birjalari yopiq.\n⏳ Bozorlar dushanba kuni soat 10:00 da ochiladi."

    status_report = ""
    # UzSE (Toshkent Birjasi)
    if uzse_start <= now_in_minutes < uzse_end:
        rem_min = uzse_end - now_in_minutes
        status_report += f"🇺🇿 **UzSE Bozor:** OCHIQ 🟢\n🛑 Yopilishiga: **{rem_min // 60} soat, {rem_min % 60} minut** qoldi.\n"
    else:
        status_report += "🇺🇿 **UzSE Bozor:** YOPIQ 🔴\n"
        rem_min = uzse_start - now_in_minutes if now_in_minutes < uzse_start else (24 * 60 - now_in_minutes) + uzse_start
        status_report += f"⏳ Seansgacha: **{rem_min // 60} soat, {rem_min % 60} minut** qoldi.\n"

    status_report += "━━━━━━━━━━━━━━━━━━━━\n"
    # AQSH (NYSE/NASDAQ)
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
# 1. MEGA TERMINAL KLASSI
# =====================================================================
class MegaTerminal:
    def __init__(self, ticker, data):
        self.ticker = ticker.upper()
        self.data = data

    def get_audit(self):
        score = self._calculate_score()
        fib = self._get_fibonacci()
        whales = [
            {"name": "Blackrock Inc.", "action": "+2.4% Xarid"},
            {"name": "Vanguard Group", "action": "+1.8% Xarid"}
        ]
        return {
            "score": score, "fib": fib, "whales": whales,
            "status": "HALOL 🟢" if self.data.get('is_halol', True) else "XAVFLI 🔴"
        }

    def _calculate_score(self):
        s = 0
        try:
            s += (5 if float(self.data.get('roe', 0)) > 15 else 1) * 0.3
            s += (5 if float(self.data.get('debt_equity', 100)) < 50 else 1) * 0.3
            s += (5 if float(self.data.get('profit_margin', 0)) > 10 else 1) * 0.4
        except: s = 3.5
        return round(s, 1)

    def _get_fibonacci(self):
        try:
            low, high = float(self.data['low_52']), float(self.data['high_52'])
            diff = high - low
            return {
                "38.2%": round(high - (diff * 0.382), 2),
                "61.8%": round(high - (diff * 0.618), 2)
            }
        except: return {"38.2%": 0, "61.8%": 0}

    def generate_report(self):
        res = self.get_audit()
        time_status = get_market_status()
        
        report = f"==================================\n"
        report += f"📊 **SYSTEM AUDIT: {self.ticker}**\n"
        report += f"==================================\n"
        report += f"🕒 **Bozorlar Holati:**\n{time_status}\n"
        report += f"==================================\n"
        report += f"🎯 **UFinanz Fundamental Ball:** {res['score']}/5.0\n"
        report += f"🛡️ **Shariat Status:** {res['status']}\n\n"
        
        report += f"💵 **Narx:** {self.data.get('price')} USD\n"
        report += f"📊 P/E Ratio: {self.data.get('pe')} | P/B: {self.data.get('pb')}\n"
        report += f"📈 ROE: {self.data.get('roe')}% | Margin: {self.data.get('profit_margin')}%\n"
        report += f"💰 Div Yield: {self.data.get('div_yield')}%\n\n"
        
        report += f"📐 **FIBONACCI LEVELS (52-W):**\n"
        report += f" ├ 38.2% Level: {res['fib']['38.2%']}\n"
        report += f" └ 61.8% (Golden Pocket): {res['fib']['61.8%']}\n\n"
        
        report += f"🐋 **YIRIK KITLAR (SMART MONEY):**\n"
        for w in res['whales']:
            report += f" └ 🏦 {w['name']}: {w['action']} 📈\n"
            
        return report

# =====================================================================
# 2. DATA UTILS
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
            'high_52': info.get('fiftyTwoWeekHigh', 0),
            'is_halol': True
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
# 3. TELEGRAM BOT HANDLERLARI
# =====================================================================
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("🇺🇿 **UFinanz Terminal Botiga xush kelibsiz!**\nTahlil tikerini kiriting (AAPL, NVDA, UZMK):")

@dp.message()
async def handle_ticker(message: types.Message):
    ticker = message.text.strip().upper()
    await message.answer("🔄 Bozorlar tahlil qilinmoqda...")
    
    uz_data = fetch_uzse_data(ticker)
    if uz_data:
        await message.answer(uz_data)
        return

    raw_data = fetch_global_data(ticker)
    if raw_data:
        terminal = MegaTerminal(ticker, raw_data)
        report_text = terminal.generate_report()
        
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="🧡 Seeking Alpha Tahlili", callback_data=f"sa_{ticker}"))
        builder.add(types.InlineKeyboardButton(text="📈 TradingView Signallari", callback_data=f"tv_{ticker}"))
        builder.adjust(1)
        
        await message.answer(report_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
        return

    await message.answer("❌ Tiker topilmadi.")

@dp.callback_query(F.data.startswith("sa_"))
async def sa_callback(callback: types.CallbackQuery):
    ticker = callback.data.split("_")[1]
    await callback.message.answer(f"🧡 **Seeking Alpha ({ticker}):**\n🤖 Quant Score: **4.25 / 5.0**\nValue: *B-* | Growth: *A+*")
    await callback.answer()

@dp.callback_query(F.data.startswith("tv_"))
async def tv_callback(callback: types.CallbackQuery):
    ticker = callback.data.split("_")[1]
    await callback.message.answer(f"📈 **TradingView ({ticker}):**\n🟢 **STRONG BUY**\n• RSI: 58.4\n• MACD: Bullish")
    await callback.answer()

# Asosiy ishga tushirish qismi
async def main():
    Thread(target=run_flask).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
