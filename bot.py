import asyncio
import sqlite3
import os
import yfinance as yf
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# --- SOZLAMALAR ---
# API_TOKEN Render muhit o'zgaruvchisidan olinadi
API_TOKEN = os.environ.get('API_TOKEN')
ADMIN_ID = 745170275

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- BAZA ---
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

# --- TAHLIL ---
def analyze_stock(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period="1y")
        
        if hist.empty: return None

        # Fundamental tahlil (3 ball)
        score = 0
        pe = info.get('trailingPE') or info.get('forwardPE', 21)
        debt_eq = info.get('debtToEquity', 1.5)
        div_yield = info.get('dividendYield', 0) or 0
        
        if pe < 20: score += 1
        if debt_eq < 1.0: score += 1
        if div_yield > 0.02: score += 1

        # Bollinger Bands tahlili (2 ball)
        sma20 = hist['Close'].rolling(window=20).mean()
        std20 = hist['Close'].rolling(window=20).std()
        upper = sma20 + (std20 * 2)
        lower = sma20 - (std20 * 2)
        
        price = hist['Close'].iloc[-1]
        if price < lower.iloc[-1] * 1.05: score += 1
        if price > ((upper.iloc[-1] + lower.iloc[-1]) / 2): score += 1
        
        # Kitlar ulushi
        whale = 0
        try:
            whale = ticker.institutional_holders['% Shares'].sum()
        except: whale = 0
        
        news_title = ticker.news[0]['title'] if ticker.news else "Yangilik topilmadi"
        
        return {"score": score, "price": price, "pe": pe, "debt": debt_eq, "whale": whale, "news": news_title}
    except Exception as e:
        print(f"DEBUG Error: {e}")
        return None

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start(message: types.Message):
    add_user(message.from_user.id)
    await message.answer("Assalamu Alaykum! Ticker yozing (masalan: AAPL):")

@dp.message()
async def process(message: types.Message):
    symbol = message.text.upper()
    data = analyze_stock(symbol)
    
    if not data:
        await message.answer(f"{symbol} uchun ma'lumot topilmadi. Boshqa ticker yozib ko'ring.")
        return
    
    report = (f"📊 **{symbol} Tahlili**\n\n"
              f"⭐ **Baho: {data['score']}/5**\n"
              f"💰 **Narxi:** ${data['price']:.2f}\n\n"
              f"🏢 **Fund:** P/E={data['pe']}, D/E={data['debt']}\n"
              f"🐳 **Kitlar:** {data['whale']:.2f}%\n"
              f"📰 **Yangilik:** {data['news']}")
    await message.answer(report, parse_mode="Markdown")

# --- WEB SERVER (RENDER UCHUN) ---
async def handle(request): return web.Response(text="Bot is running!")

async def main():
    init_db()
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080)))
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
