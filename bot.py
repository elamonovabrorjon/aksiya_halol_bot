import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
import yfinance as yf

# TOKENINGIZNI SHU YERGA (YANGILANGANINI) QO'YING
TOKEN = "8781183838:AAFmgLoz6Bb8LlA-50lVAdAbNvhBCWO3sm0" 
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Logger
logging.basicConfig(level=logging.INFO)

# --- Professional Tahlil Servisi (Barcha bozorlar uchun) ---
async def get_market_data(ticker_symbol: str):
    try:
        data = yf.Ticker(ticker_symbol)
        hist = data.history(period="1d")
        if hist.empty: return None
        return data.info
    except: return None

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    # Professional menyu (Inline tugmalar)
    builder = types.InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📊 Forex", callback_data="market_forex"),
                types.InlineKeyboardButton(text="💰 Kripto", callback_data="market_crypto"))
    builder.row(types.InlineKeyboardButton(text="📈 Fond bozori", callback_data="market_stock"))
    
    await message.answer("Xush kelibsiz! Bozor turini tanlang:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("market_"))
async def market_choice(callback: types.CallbackQuery):
    market = callback.data.split("_")[1]
    await callback.message.answer(f"Siz {market.upper()} tanladingiz. Ticker nomini yozing:")
    # Bu yerda state (holat)ni saqlash mantiqini ishlatish kerak

# --- Botni ishga tushirish ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
