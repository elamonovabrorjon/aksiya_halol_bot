import os
import telebot
from telebot import types
import yfinance as yf
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x]

bot = telebot.TeleBot(TOKEN)
tz_tashkent = pytz.timezone('Asia/Tashkent')

KNOWN_SPLITS = {
    'NKE': {'ratio': 2, 'date': '2026-05-28'},
    'NVDA': {'ratio': 10, 'date': '2024-06-07'},
    'TSLA': {'ratio': 3, 'date': '2022-08-25'},
    'AMZN': {'ratio': 20, 'date': '2022-06-06'},
}

def is_admin(uid): return uid in ADMIN_IDS
def normalize_ticker(t): return {'APPLE':'AAPL','NIKE':'NKE','TESLA':'TSLA'}.get(t.upper().strip(), t.upper().strip())

def get_price_split_corrected(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="5d")
    if hist.empty: return None
    price = hist['Close'].iloc[-1]
    split_info = ""
    splits = stock.splits
    if not splits.empty:
        recent = splits[splits.index > datetime.now() - timedelta(days=90)]
        if not recent.empty:
            ratio = recent.iloc[-1]
            price = price / ratio
            split_info = f"⚡ Split {int(ratio)}:1"
    if ticker in KNOWN_SPLITS and not split_info:
        ks = KNOWN_SPLITS[ticker]
        if datetime.now() > datetime.strptime(ks['date'], '%Y-%m-%d'):
            price = stock.info.get('regularMarketPrice', price) / ks['ratio']
            split_info = f"⚡ Split {ks['ratio']}:1"
    return round(price,2), split_info, stock

# ===== YENGI: HALOLLIK TEKSHIRUVI =====
def halal_screen(stock):
    info = stock.info
    mcap = info.get('marketCap', 1)
    debt = info.get('totalDebt', 0)
    cash = info.get('totalCash', 0) + info.get('shortTermInvestments', 0)
    recv = info.get('netReceivables', 0)

    debt_r = debt / mcap * 100
    cash_r = cash / mcap * 100
    recv_r = recv / mcap * 100

    # 33% va 30% qoidasi
    c1 = debt_r < 33
    c2 = cash_r < 33
    c3 = recv_r < 30

    score = (c1 + c2 + c3) / 3 * 100 # 3 ta mezondan nechtasi o'tdi
    return {
        'score': score,
        'debt': debt_r,
        'cash': cash_r,
        'recv': recv_r,
        'pass': [c1, c2, c3]
    }

def get_full_analysis(ticker):
    ticker = normalize_ticker(ticker)
    data = get_price_split_corrected(ticker)
    if not data: return "❌ Topilmadi"
    price, split_info, stock = data
    info = stock.info
    name = info.get('longName', ticker)
    time_now = datetime.now(tz_tashkent).strftime('%H:%M')

    text = f"🏢 <b>{name} ({ticker})</b>\n"
    text += f"💰 <b>{price:,.2f} USD</b> {split_info}\n"
    text += f"🕐 {time_now} Toshkent\n{'='*28}\n\n"

    # Likvidlik
    try:
        bid, ask = info.get('bid',0), info.get('ask',0)
        spread = ((ask-bid)/ask*100) if ask else 0
        vol, avg = info.get('volume',0), info.get('averageVolume',1)
        text += f"📕 Likvidlik: {'Yuqori ✅' if spread<0.05 else 'O‘rtacha ⚠️'}\n"
    except: pass

    # Kitlar
    try:
        holders = stock.institutional_holders
        if holders is not None:
            pct = holders['Shares'].sum() / info.get('sharesOutstanding',1) * 100
            text += f"🐋 Kitlar: {pct:.1f}%\n"
    except: pass

    # ===== HALOLLIK BLOKI =====
    try:
        h = halal_screen(stock)
        halol = h['score']
        harom = 100 - halol
        text += f"\n☪️ <b>Halollik: {halol:.0f}% Halol / {harom:.0f}% Shubhali</b>\n"
        text += f"• Qarz/MCap: {h['debt']:.1f}% {'✅' if h['pass'][0] else '❌'} (<33%)\n"
        text += f"• Naqd/MCap: {h['cash']:.1f}% {'✅' if h['pass'][1] else '❌'} (<33%)\n"
        text += f"• Debitorlik: {h['recv']:.1f}% {'✅' if h['pass'][2] else '❌'} (<30%)\n"
        if halol >= 66: text += "Xulosa: Halol deb hisoblash mumkin ✅\n"
        elif halol >= 33: text += "Xulosa: Shubhali ⚠️\n"
        else: text += "Xulosa: Haromga yaqin ❌\n"
    except: pass

    return text

@bot.message_handler(commands=['start'])
def start(m): bot.send_message(m.chat.id, "Tiker yuboring: NKE, AAPL")

@bot.message_handler(func=lambda m: True)
def handle(m):
    if m.text.startswith('/'): return
    bot.send_chat_action(m.chat.id, 'typing')
    txt = get_full_analysis(m.text)
    bot.send_message(m.chat.id, txt, parse_mode='HTML')

print("Bot ishga tushdi...")
bot.infinity_polling()