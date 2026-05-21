import telebot
from telebot import types
import yfinance as yf
import ccxt

TOKEN = '8781183838:AAGkxCEkz4gYxDycD3jB8dXiBQ59OXg73uY'
bot = telebot.TeleBot(TOKEN)
exchange = ccxt.binance()

# --- 1. LUG'AT ---
def get_dictionary():
    return ("📖 <b>MOLIYAVIY LUG'AT:</b>\n\n"
            "• <b>P/E:</b> Narx/Foyda nisbati.\n"
            "• <b>BSL/SSL:</b> Yuqori/Pastki likvidlik zonalari.\n"
            "• <b>FVG:</b> Narx bo'shlig'i (Smart Money izi).\n"
            "• <b>Order Block:</b> Yirik kitlar xarid/sotish zonasi.\n"
            "• <b>Market Cap:</b> Kompaniyaning umumiy bozor qiymati.\n"
            "• <b>ROE:</b> Kapital rentabelligi.")

# --- 2. BOOKMAP (REAL TIME) ---
def get_bookmap_data(ticker):
    try:
        symbol = f"{ticker.upper()}/USDT"
        orderbook = exchange.fetch_order_book(symbol, limit=5)
        msg = f"📊 <b>BOOKMAP: {ticker.upper()} (Real-Time)</b>\n\n🔴 <b>Sotuv devorlari (Ask):</b>\n"
        for p, v in orderbook['asks']: msg += f"  {p}$ -> {v:.2f} lot\n"
        msg += "\n🟢 <b>Xarid devorlari (Bid):</b>\n"
        for p, v in orderbook['bids']: msg += f"  {p}$ -> {v:.2f} lot\n"
        return msg
    except: return "❌ Bookmap ma'lumotini olishda xatolik."

# --- 3. PROFESSIONAL TAHLIL ---
def get_full_pro_analysis(ticker):
    try:
        t = yf.Ticker(ticker.upper())
        info = t.info
        holders = t.institutional_holders
        def f(n): return f"{n/1e9:.2f}B" if n and n >= 1e9 else f"{n/1e6:.2f}M"
        
        holders_text = "".join([f"    🔹 {r['Holder']}: {r['pctHeld']:.2f}%\n" for i, r in holders.head(3).iterrows()])
        
        msg = (f"🚨 <b>Professional Tahlil: {ticker.upper()}</b>\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               f"🏢 <b>Kompaniya:</b> {info.get('longName', 'N/A')}\n"
               f"├ Market Cap: {f(info.get('marketCap'))} | IPO: {info.get('ipoDate', 'N/A')}\n"
               f"└ Ishchilar: {info.get('fullTimeEmployees', 'N/A')} nafar\n\n"
               f"💰 <b>Moliyaviy Holat:</b>\n"
               f"├ Naqd pul: {f(info.get('totalCash'))} | Qarz: {f(info.get('totalDebt'))}\n"
               f"└ ROE: {info.get('returnOnEquity', 0)*100:.1f}% | Margin: {info.get('profitMargins', 0)*100:.1f}%\n\n"
               f"🏗 <b>SMC & Likvidlik:</b>\n"
               f"├ BSL: {info.get('currentPrice',0)*1.05:.2f}$ | SSL: {info.get('currentPrice',0)*0.95:.2f}$\n"
               f"└ Order Block: {info.get('currentPrice',0)*0.98:.2f}$ | FVG: {info.get('currentPrice',0)*0.99:.2f}$\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               f"🐋 <b>Kitlar (Top 3):</b>\n{holders_text}\n"
               f"🎯 <b>SIGNAL: KUTISH (HOLD)</b>")
        return msg
    except: return "❌ Tahlil xatosi: Tiker nomini tekshiring."

# --- 4. ASOSIY MENYU VA HANDLE ---
@bot.message_handler(commands=['start'])
def start(message):
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btns = ["📈 Fond bozori", "₿ Crypto", "💱 Forex", "🛢 Xomashyo", "⚔️ Raqobat tahlili", 
            "🐳 Kitlar & Siyosat", "🕒 Bozor vaqti", "📊 Bookmap", "📖 Lug'at", "🆘 Adminlik (Yordam)"]
    kb.add(*[types.KeyboardButton(text=b) for b in btns])
    bot.send_message(message.chat.id, "📊 <b>Wall Street Intelligence</b> tizimiga xush kelibsiz!", reply_markup=kb, parse_mode="HTML")

@bot.message_handler(func=lambda message: True)
def handle(message):
    text = message.text.strip()
    if text == "📖 Lug'at": 
        bot.reply_to(message, get_dictionary(), parse_mode="HTML")
    elif text == "📊 Bookmap": 
        msg = bot.reply_to(message, "Tiker kiriting (masalan: BTC, ETH):")
        bot.register_next_step_handler(msg, lambda m: bot.reply_to(m, get_bookmap_data(m.text), parse_mode="HTML"))
    elif text == "🆘 Adminlik (Yordam)": 
        bot.reply_to(message, "Admin: @EAA_7879")
    elif len(text) <= 10: 
        bot.reply_to(message, get_full_pro_analysis(text), parse_mode="HTML")
    else: 
        bot.reply_to(message, "Tiker yozing yoki menyudan foydalaning.")

bot.polling(none_stop=True)
