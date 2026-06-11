import telebot
from telebot import types
import yfinance as yf
import os

# YANGI TOKEN VA ADMIN
TOKEN = '8781183838:AAFmgLoz6Bb8LlA-50lVAdAbNvhBCWO3sm0'
ADMIN_ID = "745170275"
bot = telebot.TeleBot(TOKEN)

# Sektorlar uchun benchmarklar
BENCHMARKS = {
    "Technology": {"pe": 30, "roe": 0.20, "debt": 0.5},
    "Financial":  {"pe": 15, "roe": 0.12, "debt": 8.0},
    "Energy":     {"pe": 12, "roe": 0.15, "debt": 0.7},
    "Healthcare": {"pe": 25, "roe": 0.18, "debt": 0.6},
    "default":    {"pe": 20, "roe": 0.15, "debt": 1.0}
}

def save_user(message):
    user_id = str(message.chat.id)
    if not os.path.exists("users.txt"):
        with open("users.txt", "w") as f: f.write("")
    with open("users.txt", "r") as f:
        users = f.read().splitlines()
    if user_id not in users:
        with open("users.txt", "a") as f: f.write(user_id + "\n")

def get_badge(value, metric, sector):
    rule = BENCHMARKS.get(sector, BENCHMARKS["default"])
    try:
        val = float(value)
        if metric == 'pe': return "🟢" if val < rule['pe'] else ("🟡" if val < rule['pe']*1.5 else "🔴")
        if metric == 'roe': return "🟢" if val >= rule['roe'] else ("🟡" if val > rule['roe']*0.5 else "🔴")
        if metric == 'debt': return "🟢" if val <= rule['debt'] else ("🟡" if val < rule['debt']*2 else "🔴")
    except: return "⚪"
    return "⚪"

def aksiya_tahlil(ticker):
    stock = yf.Ticker(ticker.upper())
    info = stock.info
    # Agar info bo'sh kelsa, xatolikni tutish
    if not info or 'sector' not in info:
        raise ValueError("Ma'lumot topilmadi")
        
    sector = info.get('sector', 'default')
    price = info.get('currentPrice', 0)
    pe = info.get('trailingPE', 0)
    roe = info.get('returnOnEquity', 0) or 0
    debt = info.get('debtToEquity', 0) or 0
    
    msg = (f"📊 <b>{ticker.upper()} Analizi</b>\n"
           f"🏢 Sektor: {sector}\n"
           f"━━━━━━━━━━━━━━━━━━━━\n"
           f"• P/E Ratio: {pe} {get_badge(pe, 'pe', sector)}\n"
           f"• ROE: {roe*100:.1f}% {get_badge(roe, 'roe', sector)}\n"
           f"• Debt/Equity: {debt} {get_badge(debt, 'debt', sector)}\n"
           f"━━━━━━━━━━━━━━━━━━━━\n"
           f"🚨 BSL: {price*1.05:.2f} | 🛡 SSL: {price*0.95:.2f}\n"
           f"🐳 Kitlar: BlackRock/Vanguard (Accumulation)\n"
           f"🎯 <b>BOT XULOSASI:</b> {'🟢 SOTIB OLISH' if pe < 20 else '🔴 KUTISH'}")
    return msg

@bot.message_handler(commands=['start', 'admin'])
def main_commands(message):
    save_user(message)
    if message.text == '/start':
        kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        kb.add("📈 Fond bozori", "₿ Crypto", "💱 Forex", "🛢 Xomashyo", "⚔️ Raqobat tahlili", "🐳 Kitlar & Siyosat")
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("👤 Admin bilan bog'lanish", url="https://t.me/EAA_7879"))
        bot.send_message(message.chat.id, "👋 Xush kelibsiz! Kerakli bo‘limni tanlang:", reply_markup=kb)
        bot.send_message(message.chat.id, "❓ Savollar bo'lsa:", reply_markup=btn)
    elif message.text == '/admin' and str(message.chat.id) == ADMIN_ID:
        if os.path.exists("users.txt"):
            with open("users.txt", "r") as f: users = f.readlines()
            bot.reply_to(message, f"📊 <b>Statistika:</b>\n👥 Foydalanuvchilar soni: {len(users)} ta.")
        else:
            bot.reply_to(message, "Foydalanuvchilar bazasi bo'sh.")

@bot.message_handler(func=lambda message: True)
def handle(message):
    save_user(message)
    if message.text in ["📈 Fond bozori", "₿ Crypto", "💱 Forex", "🛢 Xomashyo"]:
        bot.reply_to(message, "Tiker nomini yozing (masalan: AAPL, BTC-USD):")
    elif len(message.text) <= 6:
        try: 
            bot.reply_to(message, aksiya_tahlil(message.text), parse_mode="HTML")
        except Exception as e: 
            bot.reply_to(message, "❌ Tiker topilmadi yoki ma'lumot olishda xatolik yuz berdi.")

print("Bot ishga tushdi...")
bot.infinity_polling()
