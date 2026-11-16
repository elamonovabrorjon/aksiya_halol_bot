import os
import logging
from fastapi import FastAPI, FileResponse
from fastapi.staticfiles import StaticFiles
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI ilovasi
app = FastAPI()

# Statik fayllar uchun papka
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Asosiy sahifa - Mini App uchun
@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

# Sektor gigantlari lug'ati
SECTOR_PEERS = {
    "Technology": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AVGO", "ORCL"],
}

# Bot komandalari
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        f"Salom {user.mention_html()}! Botimizga xush kelibsiz.",
    )

def main():
    # Tokeningizni shu yerga qo'ying yoki muhit o'zgaruvchisidan oling
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    
    # Render uchun polling yoki webhook ishlatishingiz mumkin
    application.run_polling()

if __name__ == "__main__":
    main()
