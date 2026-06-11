import asyncio
import sqlite3
import os
import yfinance as yf
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# --- SOZLAMALAR ---
# Tokenni Render'ning Environment Variables qismida 'API_TOKEN' deb saqlang
API_TOKEN = os.environ.get('API_TOKEN')
ADMIN_ID = 745170275

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- BAZA BILAN ISHLASH ---
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

def get_all_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users')
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

# --- TAHLIL FUNKSIYASI ---
def analyze_stock(symbol):
    ticker = yf.Ticker(symbol)
    info = ticker.info
    hist = ticker.history(period="1y")
    if hist.empty: return None

    # Fundamental (3 ball)
    score = 0
    pe = info.get('trailingPE', 21)
    debt_eq = info.get('debtToEquity', 1.5)
    div_yield = info.get('dividendYield', 0) or 0
    if pe < 20: score += 1
    if debt_eq < 1.0: score += 1
    if div_yield > 0.02: score += 1

    # Bollinger Bands (2 ball)
    # Oddiy pandas yordamida BB hisoblash (pandas_ta muammosiz)
    sma20 = hist['Close'].rolling(window=20).mean()
    std20 = hist['Close'].rolling(window=20).std()
    upper = sma20 + (std20 * 2)
    lower = sma20 - (std20 * 2)
    
    price = hist['Close'].iloc[-1]
    bb_lower = lower.iloc[-1]
    bb_upper = upper.iloc[-1]
    
    if price < bb_lower * 1.05: score += 1
    if price > (bb_upper + bb_lower) / 2: score += 1
    
    holders = ticker.institutional_holders
    whale_percent = holders['% Shares'].sum() if holders is not None else 0
    
    return {"score": score, "price": price, "pe": pe, "debt": debt_eq, "whale_percent": whale_percent, "news": ticker.news[:1]}

# --- BOT HANDLERS ---
@dp.message(Command("start"))
async def start(message: types.Message):
    add_user(message.from_user.id)
    await message.answer("Assalamu Alaykum! Ticker yozing (masalan: AAPL):")

@dp.message(Command("broadcast"))
async def broadcast(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        text = message.text.replace("/broadcast ", "")
        users = get_all_users()
        for user_id in users:
            try: await bot.send_message(user_id, text)
            except: continue
        await message.answer("Xabar yuborildi.")

@dp.message()
async def process(message: types.Message):
    data = analyze_stock(message.text.upper())
    if not data:
        await message.answer("Topilmadi.")
        return
    report = (f"📊 **{message.text.upper()} Tahlili**\n\n⭐ **Baho: {data['score']}/5**\n"
              f"💰 **Narxi:** ${data['price']:.2f}\n\n🏢 **Fundamental:** P/E={data['pe']}, D/E={data['debt']}\n"
              f"🐳 **Kitlar:** {data['whale_percent']:.2f}%\n"
              f"📰 **Yangilik:** {data['news'][0]['title'] if data['news'] else 'Yo\'q'}")
    await message.answer(report, parse_mode="Markdown")

# --- RENDER PORT BINDING ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def main():
    init_db()
    # Web server
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080)))
    await site.start()
    # Bot polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
